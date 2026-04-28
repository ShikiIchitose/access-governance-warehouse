from __future__ import annotations

from datetime import date
from typing import Any, cast

import pandas as pd

from generator.helpers.deterministic import (
    make_deterministic_float,
    make_deterministic_jitter,
    make_hash_int,
)
from generator.types import RuntimeConfig

_CANONICAL_REQUEST_ORDER = [
    "request_month",
    "month_index",
    "team_order",
    "tool_order",
    "within_group_request_index",
    "request_id",
]


def _canonicalize_request_df(request_df: pd.DataFrame) -> pd.DataFrame:
    return (
        request_df.sort_values(by=_CANONICAL_REQUEST_ORDER, kind="stable")
        .reset_index(drop=True)
        .copy()
    )


def _build_tool_risk_lookup(config: RuntimeConfig) -> dict[str, str]:
    return {
        str(tool["tool_code"]): str(tool["risk_tier"]) for tool in config.tool_config
    }


def _review_month_lookup(request_df: pd.DataFrame) -> dict[int, date]:
    lookup: dict[int, date] = {}
    distinct_months = (
        request_df.loc[:, ["month_index", "request_month"]]
        .drop_duplicates()
        .sort_values(["month_index"], kind="stable")
    )
    for row in distinct_months.itertuples(index=False):
        lookup[int(row.month_index)] = row.request_month
    return lookup


def _pending_priority_score(
    row: Any,
    *,
    decision_month_index: int,
    risk_tier: str,
    config: RuntimeConfig,
) -> float:
    pending_cfg = config.request_review_config["pending_priority_multipliers"]

    age_decay_map = pending_cfg["age_decay_by_months_open"]
    max_age_bucket = max(int(key) for key in age_decay_map)
    open_age_months = decision_month_index - int(row.month_index)
    age_bucket = min(open_age_months, max_age_bucket)

    jitter_low, jitter_high = pending_cfg["deterministic_jitter_range"]
    jitter = make_deterministic_jitter(
        row.request_id,
        decision_month_index,
        low=float(jitter_low),
        high=float(jitter_high),
        seed=config.seed,
        namespace="pending_backlog_priority",
    )

    return (
        float(pending_cfg["team"][row.team_name])
        * float(pending_cfg["purpose"][row.request_purpose])
        * float(pending_cfg["classification"][row.data_classification])
        * float(pending_cfg["risk_tier"][risk_tier])
        * float(age_decay_map[age_bucket])
        * float(jitter)
    )


def assign_pending_backlog_state(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    df = _canonicalize_request_df(request_df)
    risk_lookup = _build_tool_risk_lookup(config)

    backlog_cfg = config.request_review_config["pending_backlog"]
    month_end_targets = list(backlog_cfg["month_end_open_targets_oldest_to_anchor"])

    if len(month_end_targets) != config.n_months:
        raise ValueError(
            "pending backlog month_end_open_targets_oldest_to_anchor must have "
            f"length {config.n_months}."
        )

    df["is_pending_final"] = False
    df["review_month_index"] = pd.Series([pd.NA] * len(df), dtype="Int64")

    row_index_by_request_id = {
        str(request_id): int(index)
        for index, request_id in enumerate(df["request_id"].tolist())
    }

    open_request_ids: list[str] = []

    for decision_month_index in range(1, config.n_months + 1):
        arrivals = df.loc[
            df["month_index"] == decision_month_index,
            "request_id",
        ].tolist()
        open_request_ids.extend(str(request_id) for request_id in arrivals)

        target_open = int(month_end_targets[decision_month_index - 1])
        if target_open > len(open_request_ids):
            raise ValueError(
                "Pending backlog target exceeds currently open requests; "
                f"month_index={decision_month_index}, "
                f"target_open={target_open}, "
                f"open_requests={len(open_request_ids)}."
            )

        scored_open_requests: list[tuple[str, float, int]] = []
        for request_id in open_request_ids:
            row = df.iloc[row_index_by_request_id[request_id]]
            risk_tier = risk_lookup[str(row.tool_code)]
            score = _pending_priority_score(
                row,
                decision_month_index=decision_month_index,
                risk_tier=risk_tier,
                config=config,
            )
            tie_break = make_hash_int(
                request_id,
                decision_month_index,
                seed=config.seed,
                namespace="pending_backlog_tie_break",
                digest_size=8,
            )
            scored_open_requests.append((request_id, score, tie_break))

        ranked_open_requests = sorted(
            scored_open_requests,
            key=lambda item: (-item[1], item[2], item[0]),
        )

        keep_open_ids = {
            request_id for request_id, _, _ in ranked_open_requests[:target_open]
        }

        review_now_ids = [
            request_id
            for request_id in open_request_ids
            if request_id not in keep_open_ids
        ]

        for request_id in review_now_ids:
            row_index = row_index_by_request_id[request_id]
            df.at[row_index, "review_month_index"] = decision_month_index

        open_request_ids = [
            request_id for request_id in open_request_ids if request_id in keep_open_ids
        ]

    for request_id in open_request_ids:
        row_index = row_index_by_request_id[request_id]
        df.at[row_index, "is_pending_final"] = True

    final_pending_target = int(backlog_cfg["final_pending_exact_target"])
    pending_flags = cast(pd.Series, df["is_pending_final"])
    actual_pending = int(pending_flags.sum())
    if actual_pending != final_pending_target:
        raise ValueError(
            "Final pending count does not match final_pending_exact_target; "
            f"expected={final_pending_target}, got={actual_pending}."
        )

    return df


def assign_review_month_state(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    df = _canonicalize_request_df(request_df)
    month_lookup = _review_month_lookup(df)

    review_month_values: list[date | None] = []
    for review_month_index in df["review_month_index"].tolist():
        if pd.isna(review_month_index):
            review_month_values.append(None)
        else:
            review_month_values.append(month_lookup[int(review_month_index)])

    df["review_month"] = review_month_values
    return df


def apply_approval_model(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    df = _canonicalize_request_df(request_df)
    risk_lookup = _build_tool_risk_lookup(config)
    approval_cfg = config.request_review_config["approval_model"]

    df["approval_probability"] = 0.0
    df["request_status"] = "pending"

    reviewed_mask = ~df["is_pending_final"]

    for row in df.loc[reviewed_mask].itertuples(index=True):
        risk_tier = risk_lookup[str(row.tool_code)]
        probability = (
            float(
                approval_cfg["purpose_base_approval_probability"][row.request_purpose]
            )
            * float(
                approval_cfg["classification_approval_multipliers"][
                    row.data_classification
                ]
            )
            * float(approval_cfg["risk_tier_approval_multipliers"][risk_tier])
        )

        if probability < 0.0 or probability > 1.0:
            raise ValueError(
                "Approval probability must remain inside [0, 1]; "
                f"request_id={row.request_id!r}, probability={probability}."
            )

        draw = make_deterministic_float(
            row.request_id,
            low=0.0,
            high=1.0,
            seed=config.seed,
            namespace="approval_model_draw",
        )

        df.at[row.Index, "approval_probability"] = probability
        df.at[row.Index, "request_status"] = (
            "approved" if draw <= probability else "rejected"
        )

    df.loc[df["is_pending_final"], "request_status"] = "pending"
    return df


def _rank_for_status_correction(
    candidate_df: pd.DataFrame,
    *,
    promote: bool,
    config: RuntimeConfig,
) -> list[str]:
    ranking_rows: list[tuple[str, float, int]] = []

    for row in candidate_df.itertuples(index=False):
        tie_break = make_hash_int(
            row.request_id,
            seed=config.seed,
            namespace=(
                "approval_exact_count_promote_tie_break"
                if promote
                else "approval_exact_count_demote_tie_break"
            ),
            digest_size=8,
        )
        ranking_rows.append(
            (
                str(row.request_id),
                float(row.approval_probability),
                int(tie_break),
            )
        )

    ranked = sorted(
        ranking_rows,
        key=(
            (lambda item: (-item[1], item[2], item[0]))
            if promote
            else (lambda item: (item[1], item[2], item[0]))
        ),
    )
    return [request_id for request_id, _, _ in ranked]


def apply_status_exact_count_correction(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    df = _canonicalize_request_df(request_df)
    target_cfg = config.request_review_config["request_status_targets"]

    target_pending = int(target_cfg["pending"])
    target_approved = int(target_cfg["approved"])
    target_rejected = int(target_cfg["rejected"])

    actual_pending = int((df["request_status"] == "pending").sum())
    if actual_pending != target_pending:
        raise ValueError(
            "Pending count must already match the exact target before approval correction; "
            f"expected={target_pending}, got={actual_pending}."
        )

    actual_approved = int((df["request_status"] == "approved").sum())

    if actual_approved < target_approved:
        promote_count = target_approved - actual_approved
        candidate_df = df.loc[
            df["request_status"] == "rejected",
            ["request_id", "approval_probability"],
        ].copy()

        ranked_request_ids = _rank_for_status_correction(
            candidate_df,
            promote=True,
            config=config,
        )
        promote_ids = set(ranked_request_ids[:promote_count])
        df.loc[df["request_id"].isin(promote_ids), "request_status"] = "approved"

    elif actual_approved > target_approved:
        demote_count = actual_approved - target_approved
        candidate_df = df.loc[
            df["request_status"] == "approved",
            ["request_id", "approval_probability"],
        ].copy()

        ranked_request_ids = _rank_for_status_correction(
            candidate_df,
            promote=False,
            config=config,
        )
        demote_ids = set(ranked_request_ids[:demote_count])
        df.loc[df["request_id"].isin(demote_ids), "request_status"] = "rejected"

    final_counts = df["request_status"].value_counts(dropna=False).to_dict()
    if int(final_counts.get("approved", 0)) != target_approved:
        raise ValueError(
            "Final approved count does not match exact target after correction."
        )
    if int(final_counts.get("rejected", 0)) != target_rejected:
        raise ValueError(
            "Final rejected count does not match exact target after correction."
        )
    if int(final_counts.get("pending", 0)) != target_pending:
        raise ValueError(
            "Final pending count does not match exact target after correction."
        )

    return df.drop(columns=["approval_probability"])


def realize_review_queue_state(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    df = assign_pending_backlog_state(request_df, config)
    df = assign_review_month_state(df, config)
    df = apply_approval_model(df, config)
    df = apply_status_exact_count_correction(df, config)

    return _canonicalize_request_df(
        df.loc[
            :,
            [
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
            ],
        ].copy()
    )
