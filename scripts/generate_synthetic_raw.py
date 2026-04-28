from __future__ import annotations

import argparse
import logging

import pandas as pd

from generator.artifacts.parquet_writer import write_raw_parquet_outputs
from generator.artifacts.report_writer import write_validation_artifacts
from generator.assemble.raw_tables import assemble_raw_tables
from generator.config import build_runtime_config
from generator.helpers.validation import (
    validate_fixed_seeds,
    validate_request_duplicate_policy,
    validate_request_review_state,
    validate_request_skeletons,
    validate_request_submission_side,
    validate_request_volume,
    validate_review_detail_fields,
    validate_tool_spend_monthly,
    validate_usage_events_daily,
    validate_user_directory,
)
from generator.paths import ensure_output_directories, get_output_paths
from generator.qa.cross_table import run_cross_table_qa
from generator.qa.schema_realization import (
    run_schema_realization_postwrite_qa,
    run_schema_realization_prewrite_qa,
)
from generator.qa.summary import build_validation_summary
from generator.qa.table_local import run_table_local_qa
from generator.requests.context import (
    assign_data_classification,
    assign_request_purpose,
    generate_business_justification_text,
)
from generator.requests.duplicate_policy import reconcile_duplicate_request_policy
from generator.requests.requester_assignment import assign_requesters
from generator.requests.review_details import (
    apply_status_aware_nullability,
    assign_reviewers,
    generate_review_comments,
)
from generator.requests.review_status import realize_review_queue_state
from generator.requests.skeletons import (
    assign_request_ids,
    build_request_skeleton_df,
    expand_request_skeletons,
)
from generator.requests.timestamps import (
    assign_requested_at,
    assign_reviewed_at,
)
from generator.requests.volume import (
    allocate_team_month_counts,
    allocate_team_month_tool_counts,
)
from generator.seeds.org import build_org_seed
from generator.seeds.tools import build_tool_seed
from generator.seeds.users import build_user_directory
from generator.spend.billing import build_spend_monthly_inputs, plan_billed_rows
from generator.spend.contracts import assign_licensed_seats
from generator.spend.costs import build_raw_tool_spend_monthly
from generator.usage.activity import build_pair_month_activity
from generator.usage.approved_pairs import (
    derive_approved_current_pairs,
    select_anomaly_usage_pairs,
    select_approved_pair_activity_partitions,
)
from generator.usage.daily_rows import build_raw_usage_events_daily

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_synthetic_raw",
        description=(
            "Bootstrap and later orchestrate the synthetic raw generator "
            "for access-governance-warehouse."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Initialize the scaffold and print canonical output paths "
            "without writing raw data files."
        ),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity.",
    )
    return parser


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(levelname)s %(message)s",
    )


def run_generator(*, dry_run: bool) -> None:
    output_paths = get_output_paths()
    ensure_output_directories(output_paths)
    runtime_config = build_runtime_config()

    LOGGER.info("Generator scaffold initialized.")
    LOGGER.info("Repository root: %s", output_paths.repo_root)
    LOGGER.info("Raw output directory: %s", output_paths.raw.root)
    LOGGER.info("Validation artifact directory: %s", output_paths.validation.root)
    LOGGER.info("Runtime config loaded.")
    LOGGER.info("Seed: %s", runtime_config.seed)
    LOGGER.info("Anchor month: %s", runtime_config.anchor_month.isoformat())
    LOGGER.info("Window months: %s", runtime_config.n_months)

    org_seed = build_org_seed(runtime_config)
    tool_seed = build_tool_seed(runtime_config)
    validate_fixed_seeds(org_seed, tool_seed)

    LOGGER.info("Fixed seeds realized.")
    LOGGER.info(
        "Org seed: departments=%d teams=%d total_users=%d",
        len(org_seed.departments),
        len(org_seed.teams),
        org_seed.total_users,
    )
    LOGGER.info(
        "Tool seed: tools=%d active_tools=%d",
        len(tool_seed.tools),
        len(tool_seed.active_tool_codes),
    )

    user_df, user_universes = build_user_directory(org_seed, runtime_config)
    validate_user_directory(user_df, user_universes, org_seed, runtime_config)

    LOGGER.info("User directory realized.")
    LOGGER.info(
        "User directory: rows=%d active_users=%d inactive_users=%d reviewer_eligible=%d",
        len(user_df),
        len(user_universes.active_user_ids),
        len(user_universes.inactive_user_ids),
        len(user_universes.reviewer_eligible_user_ids),
    )

    team_month_df = allocate_team_month_counts(runtime_config, org_seed)
    team_month_tool_df = allocate_team_month_tool_counts(team_month_df, runtime_config)
    validate_request_volume(team_month_df, team_month_tool_df, org_seed, runtime_config)

    request_skeletons = expand_request_skeletons(team_month_tool_df)
    request_skeletons = assign_request_ids(request_skeletons, runtime_config)
    request_skeleton_df = build_request_skeleton_df(request_skeletons)
    validate_request_skeletons(
        request_skeleton_df,
        team_month_tool_df,
        runtime_config,
    )

    LOGGER.info("Request skeletons realized.")
    LOGGER.info(
        "Request planning: month_team_rows=%d month_team_tool_rows=%d request_rows=%d",
        len(team_month_df),
        len(team_month_tool_df),
        len(request_skeleton_df),
    )
    LOGGER.info(
        "Request skeleton window: first_month=%s last_month=%s",
        team_month_df.iloc[0]["request_month"].isoformat(),
        team_month_df.iloc[-1]["request_month"].isoformat(),
    )
    LOGGER.info(
        "Request IDs: first=%s last=%s",
        request_skeleton_df.iloc[0]["request_id"],
        request_skeleton_df.iloc[-1]["request_id"],
    )

    request_submission_df = assign_requesters(
        request_skeleton_df,
        user_df,
        user_universes,
        runtime_config,
    )
    request_submission_df = assign_requested_at(
        request_submission_df,
        runtime_config,
    )
    request_submission_df = assign_request_purpose(
        request_submission_df,
        runtime_config,
    )
    request_submission_df = assign_data_classification(
        request_submission_df,
        runtime_config,
    )
    request_submission_df = generate_business_justification_text(
        request_submission_df,
        tool_seed,
        runtime_config,
    )
    request_submission_columns = [
        "request_id",
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "tool_code",
        "requester_user_id",
        "requested_at",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "within_group_request_index",
        "global_request_rank",
        "team_order",
        "tool_order",
    ]

    request_submission_df: pd.DataFrame = request_submission_df.loc[
        :, request_submission_columns
    ].copy()
    validate_request_submission_side(
        request_submission_df,
        user_df,
        runtime_config,
    )

    LOGGER.info("Request submission-side fields realized.")
    LOGGER.info(
        "Request submission snapshot: rows=%d unique_requesters=%d requested_at_min=%s requested_at_max=%s",
        len(request_submission_df),
        request_submission_df["requester_user_id"].nunique(),
        request_submission_df["requested_at"].min().isoformat(),
        request_submission_df["requested_at"].max().isoformat(),
    )

    request_review_df = realize_review_queue_state(
        request_submission_df,
        runtime_config,
    )

    request_review_columns = [
        "request_id",
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "tool_code",
        "requester_user_id",
        "requested_at",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "request_status",
        "review_month",
        "review_month_index",
        "within_group_request_index",
        "global_request_rank",
        "team_order",
        "tool_order",
    ]

    request_review_df: pd.DataFrame = request_review_df.loc[
        :, request_review_columns
    ].copy()
    validate_request_review_state(
        request_review_df,
        runtime_config,
    )

    status_counts = (
        request_review_df["request_status"]
        .value_counts()
        .reindex(["approved", "rejected", "pending"], fill_value=0)
    )

    LOGGER.info("Request review-state fields realized.")
    LOGGER.info(
        "Request status counts: approved=%d rejected=%d pending=%d",
        int(status_counts["approved"]),
        int(status_counts["rejected"]),
        int(status_counts["pending"]),
    )

    request_review_df = reconcile_duplicate_request_policy(
        request_review_df,
        user_df,
        user_universes,
        runtime_config,
    )
    validate_request_duplicate_policy(
        request_review_df,
        user_df,
        runtime_config,
    )

    duplicate_policy_reassignment_count = int(
        request_review_df.attrs.get("duplicate_policy_reassignment_count", 0)
    )

    LOGGER.info("Duplicate-request policy reconciled.")
    LOGGER.info(
        "Duplicate-policy reconciliation: requester_reassignments=%d",
        duplicate_policy_reassignment_count,
    )

    request_review_detail_df = assign_reviewed_at(
        request_review_df,
        runtime_config,
    )
    request_review_detail_df = assign_reviewers(
        request_review_detail_df,
        user_df,
        runtime_config,
    )
    request_review_detail_df = generate_review_comments(
        request_review_detail_df,
        runtime_config,
    )
    request_review_detail_df = apply_status_aware_nullability(
        request_review_detail_df,
    )

    request_review_detail_columns = [
        "request_id",
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "tool_code",
        "requester_user_id",
        "requested_at",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "request_status",
        "review_month",
        "review_month_index",
        "reviewed_at",
        "reviewed_by_user_id",
        "review_comment_text",
        "within_group_request_index",
        "global_request_rank",
        "team_order",
        "tool_order",
    ]

    request_review_detail_df = request_review_detail_df.loc[
        :, request_review_detail_columns
    ].copy()

    validate_review_detail_fields(
        request_review_detail_df,
        user_df,
        runtime_config,
    )

    reviewed_mask = request_review_detail_df["request_status"].isin(
        ["approved", "rejected"]
    )
    comment_present_count = int(
        request_review_detail_df["review_comment_text"].notna().sum()
    )

    LOGGER.info("Request review-detail fields realized.")
    LOGGER.info(
        "Review detail snapshot: reviewed_rows=%d pending_rows=%d comment_present=%d",
        int(reviewed_mask.sum()),
        int((request_review_detail_df["request_status"] == "pending").sum()),
        comment_present_count,
    )

    approved_current_pairs_df = derive_approved_current_pairs(
        request_review_detail_df,
        runtime_config,
    )
    approved_active_pairs_df, approved_inactive_pairs_df = (
        select_approved_pair_activity_partitions(
            approved_current_pairs_df,
            runtime_config,
        )
    )
    anomaly_pairs_df = select_anomaly_usage_pairs(
        request_review_detail_df,
        user_df,
        runtime_config,
    )

    pair_month_activity_df = build_pair_month_activity(
        approved_active_pairs_df=approved_active_pairs_df,
        anomaly_pairs_df=anomaly_pairs_df,
        config=runtime_config,
    )

    raw_usage_events_daily_df = build_raw_usage_events_daily(
        pair_month_activity_df,
        runtime_config,
    )

    validate_usage_events_daily(
        raw_usage_events_daily_df,
        user_df,
        approved_active_pairs_df,
        approved_inactive_pairs_df,
        anomaly_pairs_df,
        runtime_config,
    )

    LOGGER.info("Usage events daily realized.")
    LOGGER.info(
        "Usage current-state snapshot: approved_current_pairs=%d approved_active_pairs=%d "
        "approved_inactive_pairs=%d anomaly_pairs=%d usage_rows=%d",
        len(approved_current_pairs_df),
        len(approved_active_pairs_df),
        len(approved_inactive_pairs_df),
        len(anomaly_pairs_df),
        len(raw_usage_events_daily_df),
    )

    spend_monthly_input_df = build_spend_monthly_inputs(
        request_df=request_review_detail_df,
        usage_df=raw_usage_events_daily_df,
        user_df=user_df,
        org_seed=org_seed,
        tool_seed=tool_seed,
        config=runtime_config,
    )

    billed_spend_df = plan_billed_rows(
        spend_input_df=spend_monthly_input_df,
        config=runtime_config,
    )
    billed_spend_df = assign_licensed_seats(
        billed_df=billed_spend_df,
        config=runtime_config,
    )

    raw_tool_spend_monthly_df = build_raw_tool_spend_monthly(
        billed_df=billed_spend_df,
        config=runtime_config,
    )

    validate_tool_spend_monthly(
        raw_tool_spend_monthly_df,
        org_seed,
        tool_seed,
        runtime_config,
    )

    zero_variable_cost_rows = int(
        (raw_tool_spend_monthly_df["variable_usage_cost_usd"].map(str) == "0.00").sum()
    )

    LOGGER.info("Tool spend monthly realized.")
    LOGGER.info(
        "Spend snapshot: spend_rows=%d zero_variable_cost_rows=%d billed_team_tool_pairs=%d",
        len(raw_tool_spend_monthly_df),
        zero_variable_cost_rows,
        raw_tool_spend_monthly_df[["team_name", "tool_code"]]
        .drop_duplicates()
        .shape[0],
    )

    raw_tables = assemble_raw_tables(
        tool_seed=tool_seed,
        org_seed=org_seed,
        user_df=user_df,
        request_review_detail_df=request_review_detail_df,
        usage_df=raw_usage_events_daily_df,
        spend_df=raw_tool_spend_monthly_df,
    )

    table_local_results = run_table_local_qa(
        raw_tables=raw_tables,
        org_seed=org_seed,
        tool_seed=tool_seed,
        user_universes=user_universes,
        approved_active_pairs_df=approved_active_pairs_df,
        approved_inactive_pairs_df=approved_inactive_pairs_df,
        anomaly_pairs_df=anomaly_pairs_df,
        config=runtime_config,
    )
    cross_table_results = run_cross_table_qa(
        raw_tables=raw_tables,
        org_seed=org_seed,
    )
    schema_prewrite_results = run_schema_realization_prewrite_qa(
        raw_tables=raw_tables,
        output_paths=output_paths,
    )

    prewrite_summary = build_validation_summary(
        raw_tables=raw_tables,
        table_local_results=table_local_results,
        cross_table_results=cross_table_results,
        schema_prewrite_results=schema_prewrite_results,
        config=runtime_config,
        output_paths=output_paths,
        dry_run=dry_run,
    )

    LOGGER.info("Final raw-table assembly completed.")
    LOGGER.info(
        "Pre-write QA passed: check_count=%d all_checks_passed=%s",
        prewrite_summary["check_count"],
        prewrite_summary["all_checks_passed"],
    )
    LOGGER.info(
        "Final raw row counts: tool_catalog=%d user_directory=%d access_requests=%d "
        "usage_events_daily=%d tool_spend_monthly=%d",
        len(raw_tables["raw_tool_catalog"]),
        len(raw_tables["raw_user_directory"]),
        len(raw_tables["raw_access_requests"]),
        len(raw_tables["raw_usage_events_daily"]),
        len(raw_tables["raw_tool_spend_monthly"]),
    )

    for name, path in output_paths.raw.named_items():
        LOGGER.info("Raw target [%s]: %s", name, path)

    for name, path in output_paths.validation.named_items():
        LOGGER.info("Artifact target [%s]: %s", name, path)

    if dry_run:
        LOGGER.info(
            "Dry run requested. No raw data files or validation artifacts were written."
        )
        return

    write_raw_parquet_outputs(
        raw_tables=raw_tables,
        output_paths=output_paths,
    )
    write_validation_artifacts(
        summary=prewrite_summary,
        output_paths=output_paths,
    )

    schema_postwrite_results = run_schema_realization_postwrite_qa(
        output_paths=output_paths,
    )
    final_summary = build_validation_summary(
        raw_tables=raw_tables,
        table_local_results=table_local_results,
        cross_table_results=cross_table_results,
        schema_prewrite_results=schema_prewrite_results,
        schema_postwrite_results=schema_postwrite_results,
        config=runtime_config,
        output_paths=output_paths,
        dry_run=False,
    )
    write_validation_artifacts(
        summary=final_summary,
        output_paths=output_paths,
    )

    LOGGER.info("Generation completed.")
    LOGGER.info(
        "Validation artifacts written: markdown=%s json=%s",
        output_paths.validation.summary_markdown,
        output_paths.validation.summary_json,
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)

    try:
        run_generator(dry_run=args.dry_run)
    except Exception:
        LOGGER.exception("Synthetic generator bootstrap failed.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
