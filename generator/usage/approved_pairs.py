from __future__ import annotations

from itertools import product

import pandas as pd

from generator.helpers.dates import month_difference, month_start
from generator.helpers.deterministic import make_deterministic_jitter, make_hash_int
from generator.helpers.validation import ValidationError
from generator.types import RuntimeConfig


def _build_tool_lookup(config: RuntimeConfig) -> dict[str, dict[str, object]]:
    return {
        str(tool["tool_code"]): {
            "tool_category": str(tool["tool_category"]),
            "risk_tier": str(tool["risk_tier"]),
            "is_active": bool(tool["is_active"]),
        }
        for tool in config.tool_config
    }


def _approval_age_bucket(first_approved_at: pd.Timestamp, config: RuntimeConfig) -> str:
    first_month = month_start(first_approved_at.date())
    delta = month_difference(first_month, config.anchor_month)
    if delta <= 1:
        return "0_1_months"
    if delta <= 4:
        return "2_4_months"
    return "5_plus_months"


def derive_approved_current_pairs(
    request_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    approved_mask = request_df["request_status"] == "approved"
    approved_df: pd.DataFrame = request_df.loc[approved_mask, :].copy()
    if approved_df.empty:
        raise ValidationError("Approved request rows are required before STEP9.")

    approved_df = approved_df.sort_values(
        by=["reviewed_at", "request_id"],
        kind="stable",
    ).copy()

    first_approved_df: pd.DataFrame = approved_df.drop_duplicates(
        subset=["requester_user_id", "tool_code"],
        keep="first",
    ).copy()

    tool_lookup = _build_tool_lookup(config)

    first_approved_df["user_id"] = first_approved_df["requester_user_id"]

    reviewed_at_values = [
        pd.Timestamp(value)
        for value in first_approved_df.loc[:, "reviewed_at"].tolist()
    ]
    first_approved_at_series = pd.Series(
        reviewed_at_values,
        index=first_approved_df.index,
        dtype="datetime64[ns, UTC]",
    )
    first_approved_df["first_approved_at"] = first_approved_at_series

    first_approved_df["tool_category"] = first_approved_df["tool_code"].map(
        lambda value: str(tool_lookup[str(value)]["tool_category"])
    )
    first_approved_df["risk_tier"] = first_approved_df["tool_code"].map(
        lambda value: str(tool_lookup[str(value)]["risk_tier"])
    )
    first_approved_df["approval_age_bucket"] = [
        _approval_age_bucket(pd.Timestamp(value), config)
        for value in first_approved_at_series.tolist()
    ]
    first_approved_df["pair_type"] = "approved_normal"
    first_approved_df["has_approved_request_flag"] = True

    pair_columns = [
        "user_id",
        "tool_code",
        "team_name",
        "department_name",
        "request_purpose",
        "data_classification",
        "tool_category",
        "risk_tier",
        "first_approved_at",
        "approval_age_bucket",
        "pair_type",
        "has_approved_request_flag",
    ]
    pair_df: pd.DataFrame = first_approved_df.loc[:, pair_columns].copy()

    pair_df = pair_df.sort_values(
        by=["user_id", "tool_code", "first_approved_at"],
        kind="stable",
    ).reset_index(drop=True)

    return pair_df


def select_approved_pair_activity_partitions(
    approved_current_pairs_df: pd.DataFrame,
    config: RuntimeConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = config.usage_generation_config["approved_pair_recent_activity"]
    inactive_target = int(cfg["approved_but_inactive_pairs_current_exact_target"])

    if len(approved_current_pairs_df) <= inactive_target:
        raise ValidationError(
            "approved_current pair count must exceed approved_but_inactive target."
        )

    scored_df: pd.DataFrame = approved_current_pairs_df.copy()

    def score_row(row: pd.Series) -> float:
        score = (
            float(cfg["purpose_base_weight"][str(row["request_purpose"])])
            * float(cfg["classification_multipliers"][str(row["data_classification"])])
            * float(cfg["risk_tier_multipliers"][str(row["risk_tier"])])
            * float(cfg["tool_category_multipliers"][str(row["tool_category"])])
            * float(
                cfg["approval_age_bucket_multipliers"][str(row["approval_age_bucket"])]
            )
        )
        low, high = cfg["deterministic_jitter_range"]
        score *= make_deterministic_jitter(
            row["user_id"],
            row["tool_code"],
            "approved_pair_recent_activity",
            low=float(low),
            high=float(high),
            seed=config.seed,
            namespace="approved_pair_recent_activity",
        )
        return score

    scored_df["recent_activity_score"] = scored_df.apply(score_row, axis=1)
    scored_df["stable_tie_break"] = scored_df.apply(
        lambda row: make_hash_int(
            row["user_id"],
            row["tool_code"],
            "approved_pair_recent_activity_tie",
            seed=config.seed,
            namespace="approved_pair_recent_activity_tie",
        ),
        axis=1,
    )

    scored_df = scored_df.sort_values(
        by=["recent_activity_score", "stable_tie_break", "user_id", "tool_code"],
        ascending=[False, True, True, True],
        kind="stable",
    ).reset_index(drop=True)

    active_count = len(scored_df) - inactive_target
    active_index = scored_df.index[:active_count]
    inactive_index = scored_df.index[active_count:]

    approved_active_pairs_df = scored_df.loc[active_index, :].copy()
    approved_inactive_pairs_df = scored_df.loc[inactive_index, :].copy()

    approved_active_pairs_df["has_recent_usage_30d_flag"] = True
    approved_inactive_pairs_df["has_recent_usage_30d_flag"] = False

    return (
        approved_active_pairs_df.reset_index(drop=True),
        approved_inactive_pairs_df.reset_index(drop=True),
    )


_DEFAULT_PURPOSE_BY_TOOL_CATEGORY = {
    "chat_assistant": "analysis",
    "coding_assistant": "engineering",
    "search_assistant": "research",
    "multimodal_assistant": "analysis",
}

_DEFAULT_CLASSIFICATION_BY_TEAM = {
    "Data Platform": "internal",
    "Analytics": "internal",
    "Backend": "internal",
    "Product Engineering": "internal",
    "Security": "confidential",
    "Business Operations": "internal",
}


def select_anomaly_usage_pairs(
    request_df: pd.DataFrame,
    user_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    cfg = config.usage_generation_config["unapproved_pair_anomaly_usage"]
    target = int(cfg["used_without_approval_exact_target"])
    priority_order = tuple(cfg["candidate_universe_priority"])
    priority_rank = {name: index for index, name in enumerate(priority_order)}

    tool_lookup = _build_tool_lookup(config)
    active_tool_codes = [
        tool_code for tool_code, meta in tool_lookup.items() if bool(meta["is_active"])
    ]

    active_user_df = user_df.loc[
        user_df["employment_status"] == "active",
        [
            "user_id",
            "team_name",
            "department_name",
        ],
    ].copy()

    universe_rows = []
    for user_row, tool_code in product(
        active_user_df.itertuples(index=False),
        active_tool_codes,
    ):
        universe_rows.append(
            {
                "user_id": str(user_row.user_id),
                "team_name": str(user_row.team_name),
                "department_name": str(user_row.department_name),
                "tool_code": str(tool_code),
            }
        )

    candidate_df = pd.DataFrame(universe_rows)
    if candidate_df.empty:
        raise ValidationError("Anomaly candidate universe is empty.")

    approved_current_pairs_df = derive_approved_current_pairs(request_df, config)
    approved_pair_keys = {
        (str(row.user_id), str(row.tool_code))
        for row in approved_current_pairs_df.itertuples(index=False)
    }
    candidate_df = candidate_df.loc[
        [
            (str(row.user_id), str(row.tool_code)) not in approved_pair_keys
            for row in candidate_df.itertuples(index=False)
        ]
    ].copy()

    history_df = request_df.sort_values(
        by=["requested_at", "request_id"],
        kind="stable",
    ).copy()
    history_df["user_id"] = history_df["requester_user_id"]

    history_state_df = (
        history_df.groupby(["user_id", "tool_code"], sort=False)["request_status"]
        .agg(
            has_rejected=lambda s: bool((s == "rejected").any()),
            has_pending=lambda s: bool((s == "pending").any()),
            has_approved=lambda s: bool((s == "approved").any()),
        )
        .reset_index()
    )

    latest_history_df = history_df.drop_duplicates(
        subset=["user_id", "tool_code"],
        keep="last",
    )[
        [
            "user_id",
            "tool_code",
            "request_purpose",
            "data_classification",
        ]
    ].copy()

    candidate_df = candidate_df.merge(
        history_state_df,
        on=["user_id", "tool_code"],
        how="left",
    )
    candidate_df = candidate_df.merge(
        latest_history_df,
        on=["user_id", "tool_code"],
        how="left",
    )

    candidate_df["has_rejected"] = candidate_df["has_rejected"].fillna(False)
    candidate_df["has_pending"] = candidate_df["has_pending"].fillna(False)
    candidate_df["has_approved"] = candidate_df["has_approved"].fillna(False)

    def history_state(row: pd.Series) -> str:
        if bool(row["has_rejected"]):
            return "rejected_request_exists"
        if bool(row["has_pending"]):
            return "pending_request_exists"
        return "no_request_history"

    candidate_df["request_history_state"] = candidate_df.apply(history_state, axis=1)
    candidate_df["tool_category"] = candidate_df["tool_code"].map(
        lambda value: str(tool_lookup[str(value)]["tool_category"])
    )
    candidate_df["risk_tier"] = candidate_df["tool_code"].map(
        lambda value: str(tool_lookup[str(value)]["risk_tier"])
    )

    candidate_df["request_purpose"] = candidate_df["request_purpose"].fillna(
        candidate_df["tool_category"].map(_DEFAULT_PURPOSE_BY_TOOL_CATEGORY)
    )
    candidate_df["data_classification"] = candidate_df["data_classification"].fillna(
        candidate_df["team_name"].map(_DEFAULT_CLASSIFICATION_BY_TEAM)
    )
    candidate_df["pair_type"] = "unapproved_anomaly"

    def score_row(row: pd.Series) -> float:
        score = (
            float(cfg["tool_category_base_weight"][str(row["tool_category"])])
            * float(cfg["classification_multipliers"][str(row["data_classification"])])
            * float(cfg["risk_tier_multipliers"][str(row["risk_tier"])])
            * float(
                cfg["request_history_state_multipliers"][
                    str(row["request_history_state"])
                ]
            )
        )
        low, high = cfg["deterministic_jitter_range"]
        score *= make_deterministic_jitter(
            row["user_id"],
            row["tool_code"],
            "anomaly_usage_pair",
            low=float(low),
            high=float(high),
            seed=config.seed,
            namespace="anomaly_usage_pair",
        )
        return score

    candidate_df["anomaly_usage_score"] = candidate_df.apply(score_row, axis=1)
    candidate_df["priority_rank"] = candidate_df["request_history_state"].map(
        priority_rank
    )
    candidate_df["stable_tie_break"] = candidate_df.apply(
        lambda row: make_hash_int(
            row["user_id"],
            row["tool_code"],
            "anomaly_usage_pair_tie",
            seed=config.seed,
            namespace="anomaly_usage_pair_tie",
        ),
        axis=1,
    )

    candidate_df = candidate_df.sort_values(
        by=[
            "priority_rank",
            "anomaly_usage_score",
            "stable_tie_break",
            "user_id",
            "tool_code",
        ],
        ascending=[True, False, True, True, True],
        kind="stable",
    ).reset_index(drop=True)

    if len(candidate_df) < target:
        raise ValidationError(
            "Anomaly candidate universe is smaller than the configured exact target."
        )

    selected_df = candidate_df.iloc[:target].copy()
    selected_df["first_approved_at"] = pd.NaT
    selected_df["has_approved_request_flag"] = False
    selected_df["has_recent_usage_30d_flag"] = True

    output_columns = [
        "user_id",
        "tool_code",
        "team_name",
        "department_name",
        "request_purpose",
        "data_classification",
        "tool_category",
        "risk_tier",
        "request_history_state",
        "pair_type",
        "first_approved_at",
        "has_approved_request_flag",
        "has_recent_usage_30d_flag",
    ]
    return selected_df.loc[:, output_columns].reset_index(drop=True)
