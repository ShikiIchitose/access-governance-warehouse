from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from generator.helpers.dates import (
    iter_dates_in_month,
    month_difference,
    month_sequence,
    month_start,
)
from generator.helpers.deterministic import make_deterministic_jitter, make_hash_int
from generator.helpers.validation import ValidationError
from generator.types import RuntimeConfig


@dataclass(frozen=True, slots=True)
class _AllocationRow:
    index: int
    min_required: int
    max_allowed: int
    provisional: float
    priority_hash: int


def _months_since_approval_bucket(
    first_approved_at: pd.Timestamp,
    month_value,
) -> str:
    first_month = month_start(first_approved_at.date())
    delta = month_difference(first_month, month_value)
    if delta <= 0:
        return "0"
    if delta <= 2:
        return "1_2"
    if delta <= 5:
        return "3_5"
    return "6_plus"


def _approved_month_score(row: pd.Series, month_value, config: RuntimeConfig) -> float:
    cfg = config.usage_generation_config["approved_monthly_activity"]
    months_bucket = _months_since_approval_bucket(
        pd.Timestamp(row["first_approved_at"]),
        month_value,
    )
    score = (
        float(cfg["purpose_base_weight"][str(row["request_purpose"])])
        * float(cfg["classification_multipliers"][str(row["data_classification"])])
        * float(cfg["risk_tier_multipliers"][str(row["risk_tier"])])
        * float(cfg["tool_category_multipliers"][str(row["tool_category"])])
        * float(cfg["months_since_approval_bucket_multipliers"][months_bucket])
    )
    low, high = cfg["deterministic_jitter_range"]
    score *= make_deterministic_jitter(
        row["user_id"],
        row["tool_code"],
        month_value.isoformat(),
        "approved_month_score",
        low=float(low),
        high=float(high),
        seed=config.seed,
        namespace="approved_month_score",
    )
    return score


def _candidate_date_capacity_for_pair_month(
    *,
    pair_type: str,
    first_approved_at: pd.Timestamp | None,
    month_value,
) -> int:
    candidate_dates = iter_dates_in_month(month_value)

    if pair_type == "approved_normal" and pd.notna(first_approved_at):
        first_allowed_date = pd.Timestamp(first_approved_at).date()
        candidate_dates = [
            value_date
            for value_date in candidate_dates
            if value_date >= first_allowed_date
        ]

    return len(candidate_dates)


def _build_provisional_pair_month_rows(
    approved_active_pairs_df: pd.DataFrame,
    anomaly_pairs_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    daily_cfg = config.usage_generation_config["daily_activity_intensity"]
    months = month_sequence(config.anchor_month, config.n_months)

    rows: list[dict[str, object]] = []

    for row in approved_active_pairs_df.itertuples(index=False):
        first_approved_month = month_start(pd.Timestamp(row.first_approved_at).date())
        for month_value in months:
            if month_value < first_approved_month:
                continue

            month_score = _approved_month_score(
                pd.Series(row._asdict()),
                month_value,
                config,
            )
            base_days = float(
                daily_cfg["base_active_days_by_pair_type"]["approved_normal"]
            )
            pair_type_mult = float(
                daily_cfg["pair_type_multipliers"]["approved_normal"]
            )
            tool_mult = float(
                daily_cfg["tool_category_multipliers"][str(row.tool_category)]
            )
            class_mult = float(
                daily_cfg["classification_multipliers"][str(row.data_classification)]
            )
            low, high = daily_cfg["deterministic_jitter_range"]
            jitter = make_deterministic_jitter(
                row.user_id,
                row.tool_code,
                month_value.isoformat(),
                "approved_pair_month_days",
                low=float(low),
                high=float(high),
                seed=config.seed,
                namespace="approved_pair_month_days",
            )
            provisional_days = (
                base_days
                * pair_type_mult
                * tool_mult
                * class_mult
                * month_score
                * jitter
            )

            candidate_day_capacity = _candidate_date_capacity_for_pair_month(
                pair_type="approved_normal",
                first_approved_at=pd.Timestamp(row.first_approved_at),
                month_value=month_value,
            )

            configured_max_allowed = int(
                daily_cfg["active_days_bounds"]["approved_normal"]["max"]
            )
            max_allowed = min(configured_max_allowed, candidate_day_capacity)

            min_required = (
                1 if month_value == config.anchor_month and max_allowed >= 1 else 0
            )
            provisional_days = min(provisional_days, float(max_allowed))

            rows.append(
                {
                    "usage_month": month_value,
                    "user_id": str(row.user_id),
                    "tool_code": str(row.tool_code),
                    "team_name": str(row.team_name),
                    "department_name": str(row.department_name),
                    "request_purpose": str(row.request_purpose),
                    "data_classification": str(row.data_classification),
                    "tool_category": str(row.tool_category),
                    "risk_tier": str(row.risk_tier),
                    "pair_type": "approved_normal",
                    "first_approved_at": pd.Timestamp(row.first_approved_at),
                    "min_required_active_days": min_required,
                    "max_allowed_active_days": max_allowed,
                    "provisional_active_days": provisional_days,
                }
            )

    for row in anomaly_pairs_df.itertuples(index=False):
        month_value = config.anchor_month
        base_days = float(
            daily_cfg["base_active_days_by_pair_type"]["unapproved_anomaly"]
        )
        pair_type_mult = float(daily_cfg["pair_type_multipliers"]["unapproved_anomaly"])
        tool_mult = float(
            daily_cfg["tool_category_multipliers"][str(row.tool_category)]
        )
        class_mult = float(
            daily_cfg["classification_multipliers"][str(row.data_classification)]
        )
        low, high = daily_cfg["deterministic_jitter_range"]
        jitter = make_deterministic_jitter(
            row.user_id,
            row.tool_code,
            month_value.isoformat(),
            "anomaly_pair_month_days",
            low=float(low),
            high=float(high),
            seed=config.seed,
            namespace="anomaly_pair_month_days",
        )
        provisional_days = base_days * pair_type_mult * tool_mult * class_mult * jitter

        candidate_day_capacity = _candidate_date_capacity_for_pair_month(
            pair_type="unapproved_anomaly",
            first_approved_at=None,
            month_value=month_value,
        )
        configured_max_allowed = int(
            daily_cfg["active_days_bounds"]["unapproved_anomaly"]["max"]
        )
        max_allowed = min(configured_max_allowed, candidate_day_capacity)
        provisional_days = min(provisional_days, float(max_allowed))

        rows.append(
            {
                "usage_month": month_value,
                "user_id": str(row.user_id),
                "tool_code": str(row.tool_code),
                "team_name": str(row.team_name),
                "department_name": str(row.department_name),
                "request_purpose": str(row.request_purpose),
                "data_classification": str(row.data_classification),
                "tool_category": str(row.tool_category),
                "risk_tier": str(row.risk_tier),
                "pair_type": "unapproved_anomaly",
                "first_approved_at": pd.NaT,
                "min_required_active_days": 1,
                "max_allowed_active_days": max_allowed,
                "provisional_active_days": provisional_days,
            }
        )

    pair_month_df = pd.DataFrame(rows)
    if pair_month_df.empty:
        raise ValidationError("pair-month activity planning produced no rows.")

    return pair_month_df


def _scale_active_days_to_row_target(
    pair_month_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    row_target = int(
        config.usage_generation_config["daily_activity_intensity"]["row_target"]
    )

    allocation_rows: list[_AllocationRow] = []
    base_total = 0
    headroom_total = 0.0

    for index, row in enumerate(pair_month_df.itertuples(index=False)):
        min_required = int(row.min_required_active_days)
        max_allowed = int(row.max_allowed_active_days)
        provisional = max(float(row.provisional_active_days), float(min_required))
        priority_hash = make_hash_int(
            row.user_id,
            row.tool_code,
            row.usage_month.isoformat(),
            "usage_row_scaling",
            seed=config.seed,
            namespace="usage_row_scaling",
        )
        allocation_rows.append(
            _AllocationRow(
                index=index,
                min_required=min_required,
                max_allowed=max_allowed,
                provisional=provisional,
                priority_hash=priority_hash,
            )
        )
        base_total += min_required
        headroom_total += max(provisional - min_required, 0.0)

    if base_total > row_target:
        raise ValidationError(
            "usage row target is smaller than the sum of required minimum active-day rows."
        )

    desired_additional = row_target - base_total
    if desired_additional < 0:
        desired_additional = 0

    if headroom_total <= 0:
        pair_month_df["active_days_in_month"] = pair_month_df[
            "min_required_active_days"
        ]
        return pair_month_df

    floors: list[int] = []
    remainders: list[tuple[float, int, int]] = []
    additional_total = 0

    for item in allocation_rows:
        provisional_additional = max(item.provisional - item.min_required, 0.0)
        scaled = provisional_additional * desired_additional / headroom_total
        floor_value = int(scaled)
        cap = item.max_allowed - item.min_required
        floor_value = min(floor_value, cap)
        remainder = scaled - floor_value
        floors.append(floor_value)
        additional_total += floor_value
        remainders.append((remainder, item.priority_hash, item.index))

    remaining = desired_additional - additional_total
    if remaining > 0:
        remainders.sort(key=lambda x: (-x[0], x[1], x[2]))
        for _, _, index in remainders:
            if remaining == 0:
                break
            cap = (
                allocation_rows[index].max_allowed - allocation_rows[index].min_required
            )
            if floors[index] < cap:
                floors[index] += 1
                remaining -= 1

    final_counts = []
    for item in allocation_rows:
        final_count = item.min_required + floors[item.index]
        final_count = max(item.min_required, min(final_count, item.max_allowed))
        final_counts.append(final_count)

    pair_month_df = pair_month_df.copy()

    active_days_series = pd.Series(
        final_counts,
        index=pair_month_df.index,
        dtype="int64",
    )
    pair_month_df["active_days_in_month"] = active_days_series

    active_days_mask = active_days_series.gt(0)
    active_days_index = pair_month_df.index[active_days_mask]
    pair_month_df = pair_month_df.loc[active_days_index, :].copy()

    return pair_month_df.reset_index(drop=True)


def build_pair_month_activity(
    approved_active_pairs_df: pd.DataFrame,
    anomaly_pairs_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    pair_month_df = _build_provisional_pair_month_rows(
        approved_active_pairs_df=approved_active_pairs_df,
        anomaly_pairs_df=anomaly_pairs_df,
        config=config,
    )
    pair_month_df = _scale_active_days_to_row_target(pair_month_df, config)

    pair_month_df = pair_month_df.sort_values(
        by=["usage_month", "user_id", "tool_code", "pair_type"],
        kind="stable",
    ).reset_index(drop=True)

    return pair_month_df
