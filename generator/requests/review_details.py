from __future__ import annotations

from collections import defaultdict

import pandas as pd

from generator.helpers.deterministic import (
    deterministic_weighted_choice,
    make_deterministic_int,
    make_deterministic_jitter,
)
from generator.types import RuntimeConfig


def _review_config(config: RuntimeConfig) -> dict:
    return dict(config.request_review_config)


def _tool_meta_lookup(config: RuntimeConfig) -> dict[str, dict[str, str]]:
    return {
        str(tool["tool_code"]): {
            "tool_category": str(tool["tool_category"]),
            "risk_tier": str(tool["risk_tier"]),
        }
        for tool in config.tool_config
    }


def _build_user_lookup(user_df: pd.DataFrame) -> dict[str, dict[str, str]]:
    return {
        str(row.user_id): {
            "team_name": str(row.team_name),
            "department_name": str(row.department_name),
            "job_level": str(row.job_level),
            "employment_status": str(row.employment_status),
        }
        for row in user_df.itertuples(index=False)
    }


def _build_reviewer_pool_user_ids(
    user_df: pd.DataFrame,
    config: RuntimeConfig,
) -> tuple[str, ...]:
    review_config = _review_config(config)
    reviewer_pool_config = review_config["reviewer_pool"]
    reviewer_pool_by_team = reviewer_pool_config["reviewer_pool_by_team"]
    required_status = str(
        reviewer_pool_config["eligibility_rules"]["employment_status_must_be"]
    )

    eligible_df = user_df.loc[user_df["employment_status"] == required_status].copy()
    reviewer_ids: list[str] = []

    for team_name, reviewer_count in reviewer_pool_by_team.items():
        team_df = eligible_df.loc[eligible_df["team_name"] == team_name].copy()

        if len(team_df) < int(reviewer_count):
            raise ValueError(
                f"Reviewer pool for team {team_name!r} is infeasible: "
                f"required={reviewer_count}, available={len(team_df)}."
            )

        team_df["reviewer_pool_rank"] = team_df["user_id"].map(
            lambda user_id: make_deterministic_int(
                team_name,
                str(user_id),
                "reviewer_pool_rank",
                low=0,
                high=10_000_000,
                seed=config.seed,
                namespace="reviewer_pool_rank",
            )
        )
        team_df = team_df.sort_values(
            by=["reviewer_pool_rank", "user_id"],
            kind="stable",
        )

        reviewer_ids.extend(
            team_df.head(int(reviewer_count))["user_id"].astype(str).tolist()
        )

    expected_total = int(reviewer_pool_config["total_reviewers"])
    if len(reviewer_ids) != expected_total:
        raise ValueError(
            f"Reviewer pool total mismatch: expected={expected_total}, got={len(reviewer_ids)}."
        )

    return tuple(reviewer_ids)


def _reviewer_relation(
    *,
    requester_user_id: str,
    requester_team_name: str,
    requester_department_name: str,
    reviewer_user_id: str,
    reviewer_team_name: str,
    reviewer_department_name: str,
) -> str:
    if reviewer_user_id == requester_user_id:
        return "self"
    if reviewer_team_name == requester_team_name:
        return "same_team"
    if reviewer_department_name == requester_department_name:
        return "same_department"
    return "different_department"


def assign_reviewers(
    request_df: pd.DataFrame,
    user_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    review_config = _review_config(config)
    reviewer_ids = _build_reviewer_pool_user_ids(user_df, config)
    user_lookup = _build_user_lookup(user_df)
    tool_lookup = _tool_meta_lookup(config)

    team_base_weights = review_config["reviewer_team_base_weights"]
    tool_category_multipliers = review_config["reviewer_tool_category_multipliers"]
    classification_multipliers = review_config["reviewer_classification_multipliers"]
    risk_tier_multipliers = review_config["reviewer_risk_tier_multipliers"]
    relationship_multipliers = review_config["reviewer_relationship_multipliers"]
    load_balancing_config = review_config["reviewer_load_balancing"]

    monthly_load_alpha = float(load_balancing_config["monthly_load_alpha"])
    annual_load_beta = float(load_balancing_config["annual_load_beta"])
    jitter_low, jitter_high = load_balancing_config["deterministic_jitter_range"]

    monthly_review_counts: defaultdict[tuple[int, str], int] = defaultdict(int)
    annual_review_counts: defaultdict[str, int] = defaultdict(int)

    reviewed_by_values: list[str | None] = []

    for row in request_df.itertuples(index=False):
        request_status = str(row.request_status)
        if request_status == "pending":
            reviewed_by_values.append(None)
            continue

        requester_user_id = str(row.requester_user_id)
        requester_team_name = str(row.team_name)
        requester_department_name = str(row.department_name)
        tool_meta = tool_lookup[str(row.tool_code)]
        tool_category = tool_meta["tool_category"]
        risk_tier = tool_meta["risk_tier"]
        review_month_index = int(row.review_month_index)

        candidate_ids: list[str] = []
        candidate_weights: list[float] = []

        for reviewer_user_id in reviewer_ids:
            if reviewer_user_id == requester_user_id:
                continue

            reviewer_meta = user_lookup[reviewer_user_id]
            reviewer_team_name = reviewer_meta["team_name"]
            reviewer_department_name = reviewer_meta["department_name"]

            relation = _reviewer_relation(
                requester_user_id=requester_user_id,
                requester_team_name=requester_team_name,
                requester_department_name=requester_department_name,
                reviewer_user_id=reviewer_user_id,
                reviewer_team_name=reviewer_team_name,
                reviewer_department_name=reviewer_department_name,
            )

            team_weight = float(team_base_weights[reviewer_team_name])
            category_weight = float(
                tool_category_multipliers[reviewer_team_name][tool_category]
            )
            classification_weight = float(
                classification_multipliers[reviewer_team_name][
                    str(row.data_classification)
                ]
            )
            risk_weight = float(risk_tier_multipliers[reviewer_team_name][risk_tier])
            relation_weight = float(relationship_multipliers[relation])

            monthly_count = monthly_review_counts[
                (review_month_index, reviewer_user_id)
            ]
            annual_count = annual_review_counts[reviewer_user_id]
            load_factor = 1.0 / (
                1.0
                + (monthly_load_alpha * monthly_count)
                + (annual_load_beta * annual_count)
            )

            jitter = make_deterministic_jitter(
                str(row.request_id),
                reviewer_user_id,
                review_month_index,
                low=jitter_low,
                high=jitter_high,
                seed=config.seed,
                namespace="reviewer_assignment_jitter",
            )

            score = (
                team_weight
                * category_weight
                * classification_weight
                * risk_weight
                * relation_weight
                * load_factor
                * jitter
            )

            candidate_ids.append(reviewer_user_id)
            candidate_weights.append(score)

        if not candidate_ids:
            raise ValueError(
                f"No eligible reviewer candidates remain after exclusions; request_id={row.request_id!r}."
            )

        chosen_reviewer = str(
            deterministic_weighted_choice(
                candidate_ids,
                candidate_weights,
                str(row.request_id),
                requester_user_id,
                review_month_index,
                seed=config.seed,
                namespace="reviewer_assignment_choice",
            )
        )
        reviewed_by_values.append(chosen_reviewer)
        monthly_review_counts[(review_month_index, chosen_reviewer)] += 1
        annual_review_counts[chosen_reviewer] += 1

    enriched_df = request_df.copy()
    enriched_df["reviewed_by_user_id"] = reviewed_by_values
    return enriched_df


def _approved_comment_is_present(
    *,
    request_id: str,
    data_classification: str,
    risk_tier: str,
    config: RuntimeConfig,
) -> bool:
    review_config = _review_config(config)
    probability = float(
        review_config["review_comment_presence"]["approved_comment_probability"][
            data_classification
        ][risk_tier]
    )
    threshold = int(round(probability * 10_000))
    draw = make_deterministic_int(
        request_id,
        data_classification,
        risk_tier,
        "approved_comment_presence",
        low=1,
        high=10_000,
        seed=config.seed,
        namespace="approved_comment_presence_draw",
    )
    return int(draw) <= threshold


def _select_comment_family(
    *,
    request_id: str,
    data_classification: str,
    risk_tier: str,
    family_weights: dict[str, float],
    config: RuntimeConfig,
    namespace: str,
) -> str:
    families = tuple(family_weights.keys())
    weights = [float(family_weights[family]) for family in families]

    return str(
        deterministic_weighted_choice(
            families,
            weights,
            request_id,
            data_classification,
            risk_tier,
            seed=config.seed,
            namespace=namespace,
        )
    )


def _select_comment_template(
    *,
    request_id: str,
    family_name: str,
    templates: list[str],
    config: RuntimeConfig,
    namespace: str,
) -> str:
    template_index = make_deterministic_int(
        request_id,
        family_name,
        "review_comment_template",
        low=0,
        high=len(templates) - 1,
        seed=config.seed,
        namespace=namespace,
    )
    return str(templates[int(template_index)])


def generate_review_comments(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    review_config = _review_config(config)
    tool_lookup = _tool_meta_lookup(config)

    approved_comment_config = review_config["approved_review_comment"]
    rejected_comment_config = review_config["rejected_review_comment"]

    review_comment_values: list[str | None] = []

    for row in request_df.itertuples(index=False):
        request_status = str(row.request_status)
        data_classification = str(row.data_classification)
        risk_tier = tool_lookup[str(row.tool_code)]["risk_tier"]
        request_id = str(row.request_id)

        if request_status == "pending":
            review_comment_values.append(None)
            continue

        if request_status == "approved":
            should_have_comment = _approved_comment_is_present(
                request_id=request_id,
                data_classification=data_classification,
                risk_tier=risk_tier,
                config=config,
            )
            if not should_have_comment:
                review_comment_values.append(None)
                continue

            family_name = _select_comment_family(
                request_id=request_id,
                data_classification=data_classification,
                risk_tier=risk_tier,
                family_weights=approved_comment_config["family_weights"][
                    data_classification
                ][risk_tier],
                config=config,
                namespace="approved_review_comment_family",
            )
            template = _select_comment_template(
                request_id=request_id,
                family_name=family_name,
                templates=list(approved_comment_config["templates"][family_name]),
                config=config,
                namespace="approved_review_comment_template",
            )
            review_comment_values.append(template)
            continue

        if request_status == "rejected":
            family_name = _select_comment_family(
                request_id=request_id,
                data_classification=data_classification,
                risk_tier=risk_tier,
                family_weights=rejected_comment_config["family_weights"][
                    data_classification
                ][risk_tier],
                config=config,
                namespace="rejected_review_comment_family",
            )
            template = _select_comment_template(
                request_id=request_id,
                family_name=family_name,
                templates=list(rejected_comment_config["templates"][family_name]),
                config=config,
                namespace="rejected_review_comment_template",
            )
            review_comment_values.append(template)
            continue

        raise ValueError(
            f"Unexpected request_status for review comment generation: {request_status!r}"
        )

    enriched_df = request_df.copy()
    enriched_df["review_comment_text"] = review_comment_values
    return enriched_df


def apply_status_aware_nullability(
    request_df: pd.DataFrame,
) -> pd.DataFrame:
    enriched_df = request_df.copy()

    pending_mask = enriched_df["request_status"] == "pending"

    enriched_df.loc[pending_mask, "reviewed_at"] = pd.NaT
    enriched_df.loc[pending_mask, "reviewed_by_user_id"] = None
    enriched_df.loc[pending_mask, "review_comment_text"] = None

    return enriched_df
