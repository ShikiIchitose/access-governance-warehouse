from __future__ import annotations

import hashlib
from datetime import date
from typing import Any, cast

import pandas as pd

from generator.types import OrgSeed, RuntimeConfig, ToolSeed


def _month_sequence(anchor_month: date, n_months: int) -> tuple[date, ...]:
    anchor_total_month = anchor_month.year * 12 + (anchor_month.month - 1)
    start_total_month = anchor_total_month - (n_months - 1)

    months: list[date] = []
    for offset in range(n_months):
        total_month = start_total_month + offset
        year = total_month // 12
        month = (total_month % 12) + 1
        months.append(date(year, month, 1))
    return tuple(months)


def _month_start(value: object) -> date:
    timestamp = pd.Timestamp(value)
    return date(timestamp.year, timestamp.month, 1)


def _stable_hash_int(seed: int, *parts: object) -> int:
    payload = "||".join(str(part) for part in (seed, *parts)).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:16], 16)


def _build_monthly_approved_user_totals(
    request_df: pd.DataFrame,
    user_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    approved_df = request_df.loc[
        request_df["request_status"] == "approved",
        ["requester_user_id", "tool_code", "reviewed_at"],
    ].copy()

    if approved_df.empty:
        return pd.DataFrame(
            columns=[
                "billing_month",
                "team_name",
                "department_name",
                "tool_code",
                "approved_users_total",
            ]
        )

    first_approved_df = (
        approved_df.groupby(["requester_user_id", "tool_code"], sort=False)[
            "reviewed_at"
        ]
        .min()
        .reset_index()
    )

    user_meta_df = user_df.loc[
        :,
        ["user_id", "team_name", "department_name"],
    ].rename(columns={"user_id": "requester_user_id"})

    first_approved_df = first_approved_df.merge(
        user_meta_df,
        on="requester_user_id",
        how="left",
        validate="many_to_one",
    )

    month_sequence = _month_sequence(config.anchor_month, config.n_months)
    month_to_index = {
        month: index for index, month in enumerate(month_sequence, start=1)
    }

    expanded_rows: list[dict[str, object]] = []
    for row in first_approved_df.itertuples(index=False):
        first_approved_month = _month_start(row.reviewed_at)
        first_month_index = month_to_index.get(first_approved_month)
        if first_month_index is None:
            continue

        for month_index in range(first_month_index, config.n_months + 1):
            expanded_rows.append(
                {
                    "billing_month": month_sequence[month_index - 1],
                    "team_name": str(row.team_name),
                    "department_name": str(row.department_name),
                    "tool_code": str(row.tool_code),
                    "requester_user_id": str(row.requester_user_id),
                }
            )

    if not expanded_rows:
        return pd.DataFrame(
            columns=[
                "billing_month",
                "team_name",
                "department_name",
                "tool_code",
                "approved_users_total",
            ]
        )

    expanded_df = pd.DataFrame(expanded_rows)
    approved_totals_df = (
        expanded_df.groupby(
            ["billing_month", "team_name", "department_name", "tool_code"],
            sort=False,
        )["requester_user_id"]
        .nunique()
        .reset_index(name="approved_users_total")
    )

    return approved_totals_df


def _build_monthly_usage_totals(
    usage_df: pd.DataFrame,
    user_df: pd.DataFrame,
) -> pd.DataFrame:
    if usage_df.empty:
        return pd.DataFrame(
            columns=[
                "billing_month",
                "team_name",
                "department_name",
                "tool_code",
                "active_users_total",
                "total_sessions",
                "total_prompts",
            ]
        )

    usage_work_df = usage_df.copy()
    usage_work_df["billing_month"] = usage_work_df["usage_date"].map(_month_start)

    user_meta_df = user_df.loc[:, ["user_id", "team_name", "department_name"]].copy()

    usage_work_df = usage_work_df.merge(
        user_meta_df,
        on="user_id",
        how="left",
        validate="many_to_one",
    )

    usage_totals_df = (
        usage_work_df.groupby(
            ["billing_month", "team_name", "department_name", "tool_code"],
            sort=False,
        )
        .agg(
            active_users_total=("user_id", "nunique"),
            total_sessions=("session_count", "sum"),
            total_prompts=("prompt_count", "sum"),
        )
        .reset_index()
    )

    return usage_totals_df


def build_spend_monthly_inputs(
    request_df: pd.DataFrame,
    usage_df: pd.DataFrame,
    user_df: pd.DataFrame,
    org_seed: OrgSeed,
    tool_seed: ToolSeed,
    config: RuntimeConfig,
) -> pd.DataFrame:
    month_sequence = _month_sequence(config.anchor_month, config.n_months)

    spine_rows: list[dict[str, object]] = []
    for month_index, billing_month in enumerate(month_sequence, start=1):
        for team in org_seed.teams:
            for tool in tool_seed.tools:
                spine_rows.append(
                    {
                        "billing_month": billing_month,
                        "month_index": month_index,
                        "team_name": team.team_name,
                        "department_name": team.department_name,
                        "team_order": team.team_order,
                        "team_size": team.size,
                        "tool_code": tool.tool_code,
                        "tool_order": tool.tool_order,
                        "tool_category": tool.tool_category,
                        "risk_tier": tool.risk_tier,
                    }
                )

    spend_input_df = pd.DataFrame(spine_rows)

    approved_totals_df = _build_monthly_approved_user_totals(
        request_df=request_df,
        user_df=user_df,
        config=config,
    )
    usage_totals_df = _build_monthly_usage_totals(
        usage_df=usage_df,
        user_df=user_df,
    )

    spend_input_df = spend_input_df.merge(
        approved_totals_df,
        on=["billing_month", "team_name", "department_name", "tool_code"],
        how="left",
        validate="one_to_one",
    )
    spend_input_df = spend_input_df.merge(
        usage_totals_df,
        on=["billing_month", "team_name", "department_name", "tool_code"],
        how="left",
        validate="one_to_one",
    )

    numeric_columns = [
        "approved_users_total",
        "active_users_total",
        "total_sessions",
        "total_prompts",
    ]
    for column in numeric_columns:
        spend_input_df[column] = spend_input_df[column].fillna(0).astype(int)

    spend_input_df = spend_input_df.sort_values(
        by=["month_index", "team_order", "tool_order"],
        kind="stable",
    ).reset_index(drop=True)

    return spend_input_df


def _row_contribution(start_month_index: int, n_months: int) -> int:
    return max(0, n_months - start_month_index + 1)


def _apply_billed_row_target_correction(
    candidates_df: pd.DataFrame,
    *,
    target_total_rows: int,
    n_months: int,
) -> pd.DataFrame:
    corrected_df = candidates_df.copy()

    def current_total() -> int:
        return int(
            corrected_df["adjusted_start_month_index"]
            .map(lambda value: _row_contribution(int(value), n_months))
            .sum()
        )

    current_total_rows = current_total()

    if current_total_rows == target_total_rows:
        return corrected_df

    if current_total_rows > target_total_rows:
        while current_total_rows > target_total_rows:
            eligible_df = corrected_df.loc[
                corrected_df["adjusted_start_month_index"] <= n_months,
                :,
            ].copy()
            if eligible_df.empty:
                raise RuntimeError(
                    "Could not delay billed contract starts enough to hit the exact spend-row target."
                )

            eligible_df = eligible_df.sort_values(
                by=[
                    "peak_approved_users_total",
                    "peak_active_users_total",
                    "peak_total_sessions",
                    "peak_total_prompts",
                    "priority_hash",
                ],
                ascending=[True, True, True, True, True],
                kind="stable",
            )
            target_index = eligible_df.index[0]
            corrected_df.loc[target_index, "adjusted_start_month_index"] = (
                int(corrected_df.loc[target_index, "adjusted_start_month_index"]) + 1
            )
            current_total_rows -= 1
    else:
        while current_total_rows < target_total_rows:
            eligible_df = corrected_df.loc[
                corrected_df["adjusted_start_month_index"] > 1,
                :,
            ].copy()
            if eligible_df.empty:
                raise RuntimeError(
                    "Could not advance billed contract starts enough to hit the exact spend-row target."
                )

            eligible_df = eligible_df.sort_values(
                by=[
                    "peak_approved_users_total",
                    "peak_active_users_total",
                    "peak_total_sessions",
                    "peak_total_prompts",
                    "priority_hash",
                ],
                ascending=[False, False, False, False, True],
                kind="stable",
            )
            target_index = eligible_df.index[0]
            corrected_df.loc[target_index, "adjusted_start_month_index"] = (
                int(corrected_df.loc[target_index, "adjusted_start_month_index"]) - 1
            )
            current_total_rows += 1

    return corrected_df


def _coerce_billed_column_to_int_list(
    df: pd.DataFrame,
    column_name: str,
) -> list[int]:
    raw_values = cast(Any, df.loc[:, column_name]).tolist()

    coerced_values: list[int] = []
    for value in raw_values:
        if pd.isna(value):
            raise RuntimeError(
                f"{column_name} contains null after billed-row filtering."
            )
        coerced_values.append(int(value))

    return coerced_values


def plan_billed_rows(
    spend_input_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    contract_config = config.spend_generation_config["contract_activation"]

    activation_thresholds = contract_config["activation_thresholds_by_tool_category"]
    procurement_lag_by_risk = contract_config["procurement_lag_months_by_risk_tier"]
    target_total_rows = int(config.raw_targets["raw_tool_spend_monthly_rows"])

    def is_signal_row(row: pd.Series) -> bool:
        threshold = activation_thresholds[str(row["tool_category"])]
        return int(row["approved_users_total"]) >= int(
            threshold["approved_users_total_min"]
        ) and int(row["active_users_total"]) >= int(threshold["active_users_total_min"])

    signal_df = spend_input_df.loc[
        spend_input_df.apply(is_signal_row, axis=1),
        :,
    ].copy()

    if signal_df.empty:
        raise RuntimeError(
            "No spend contract signal rows were produced; raw_tool_spend_monthly cannot be realized."
        )

    first_signal_df = (
        signal_df.sort_values(
            by=["month_index", "team_order", "tool_order"],
            kind="stable",
        )
        .groupby(["team_name", "tool_code"], sort=False)
        .first()
        .reset_index()
    )

    peak_metrics_df = (
        spend_input_df.groupby(["team_name", "tool_code"], sort=False)
        .agg(
            peak_approved_users_total=("approved_users_total", "max"),
            peak_active_users_total=("active_users_total", "max"),
            peak_total_sessions=("total_sessions", "max"),
            peak_total_prompts=("total_prompts", "max"),
        )
        .reset_index()
    )

    candidates_df = first_signal_df.merge(
        peak_metrics_df,
        on=["team_name", "tool_code"],
        how="left",
        validate="one_to_one",
    )

    candidates_df["signal_month_index"] = candidates_df["month_index"].astype(int)
    candidates_df["base_start_month_index"] = candidates_df.apply(
        lambda row: min(
            config.n_months + 1,
            int(row["signal_month_index"])
            + int(procurement_lag_by_risk[str(row["risk_tier"])]),
        ),
        axis=1,
    )
    candidates_df["adjusted_start_month_index"] = candidates_df[
        "base_start_month_index"
    ]
    candidates_df["priority_hash"] = candidates_df.apply(
        lambda row: _stable_hash_int(
            config.seed,
            row["team_name"],
            row["tool_code"],
            row["signal_month_index"],
        ),
        axis=1,
    )

    candidates_df = _apply_billed_row_target_correction(
        candidates_df,
        target_total_rows=target_total_rows,
        n_months=config.n_months,
    )

    merged_df = spend_input_df.merge(
        candidates_df[
            [
                "team_name",
                "tool_code",
                "signal_month_index",
                "base_start_month_index",
                "adjusted_start_month_index",
            ]
        ],
        on=["team_name", "tool_code"],
        how="left",
        validate="many_to_one",
    )

    adjusted_start_month_index = cast(
        Any,
        merged_df.loc[:, "adjusted_start_month_index"],
    )
    month_index = cast(
        Any,
        merged_df.loc[:, "month_index"],
    )

    billed_mask = adjusted_start_month_index.notna()
    billed_mask = billed_mask & (month_index >= adjusted_start_month_index)
    billed_mask = billed_mask & (adjusted_start_month_index <= config.n_months)

    billed_df = merged_df.loc[billed_mask, :].copy()

    billed_df.loc[:, "signal_month_index"] = _coerce_billed_column_to_int_list(
        billed_df,
        "signal_month_index",
    )
    billed_df.loc[:, "base_start_month_index"] = _coerce_billed_column_to_int_list(
        billed_df,
        "base_start_month_index",
    )
    billed_df.loc[:, "adjusted_start_month_index"] = _coerce_billed_column_to_int_list(
        billed_df,
        "adjusted_start_month_index",
    )

    billed_df = billed_df.sort_values(
        by=["month_index", "team_order", "tool_order"],
        kind="stable",
    ).reset_index(drop=True)

    if len(billed_df) != target_total_rows:
        raise RuntimeError(
            "Billed-row correction failed to reach the exact spend-row target; "
            f"expected={target_total_rows}, got={len(billed_df)}."
        )

    return billed_df
