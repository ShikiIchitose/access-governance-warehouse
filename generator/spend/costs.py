from __future__ import annotations

from decimal import Decimal

import pandas as pd

from generator.helpers.rounding import finalize_spend_total, quantize_usd, to_decimal
from generator.types import RuntimeConfig


def calculate_fixed_license_cost(
    billed_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    pricing_config = config.spend_generation_config["fixed_license_pricing"]
    seat_price_lookup = pricing_config["synthetic_monthly_seat_price_usd_by_tool_code"]
    discount_lookup = pricing_config["team_contract_discount_multipliers"]

    fixed_costs: list[Decimal] = []
    for row in billed_df.itertuples(index=False):
        seat_price = to_decimal(seat_price_lookup[str(row.tool_code)])
        team_discount = to_decimal(discount_lookup[str(row.team_name)])
        licensed_seats = to_decimal(int(row.licensed_seats))

        fixed_cost = quantize_usd(licensed_seats * seat_price * team_discount)
        fixed_costs.append(fixed_cost)

    result_df = billed_df.copy()
    result_df["fixed_license_cost_usd"] = pd.Series(fixed_costs, index=result_df.index)
    return result_df


def calculate_variable_usage_cost(
    billed_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    variable_config = config.spend_generation_config["variable_usage_pricing"]

    per_session_lookup = variable_config["per_session_rate_usd_by_tool_code"]
    per_prompt_lookup = variable_config["per_prompt_rate_usd_by_tool_code"]
    overage_lookup = variable_config["active_user_overage_rate_usd_by_tool_code"]
    floor_value = quantize_usd(variable_config["variable_cost_floor_if_zero_usage"])

    variable_costs: list[Decimal] = []
    for row in billed_df.itertuples(index=False):
        tool_code = str(row.tool_code)
        total_sessions = int(row.total_sessions)
        total_prompts = int(row.total_prompts)
        active_users_total = int(row.active_users_total)
        licensed_seats = int(row.licensed_seats)

        overage_count = max(0, active_users_total - licensed_seats)

        raw_variable_cost = (
            to_decimal(per_session_lookup[tool_code]) * to_decimal(total_sessions)
            + to_decimal(per_prompt_lookup[tool_code]) * to_decimal(total_prompts)
            + to_decimal(overage_lookup[tool_code]) * to_decimal(overage_count)
        )

        variable_cost = quantize_usd(raw_variable_cost)
        if total_sessions == 0 and total_prompts == 0:
            variable_cost = floor_value

        variable_costs.append(variable_cost)

    result_df = billed_df.copy()
    result_df["variable_usage_cost_usd"] = pd.Series(
        variable_costs,
        index=result_df.index,
    )
    return result_df


def derive_spend_usd(
    billed_df: pd.DataFrame,
) -> pd.DataFrame:
    spend_totals: list[Decimal] = []
    for row in billed_df.itertuples(index=False):
        spend_total = finalize_spend_total(
            row.fixed_license_cost_usd,
            row.variable_usage_cost_usd,
        )
        spend_totals.append(spend_total)

    result_df = billed_df.copy()
    result_df["spend_usd"] = pd.Series(spend_totals, index=result_df.index)
    return result_df


def apply_spend_rounding(
    billed_df: pd.DataFrame,
) -> pd.DataFrame:
    result_df = billed_df.copy()

    result_df["fixed_license_cost_usd"] = result_df["fixed_license_cost_usd"].map(
        quantize_usd
    )
    result_df["variable_usage_cost_usd"] = result_df["variable_usage_cost_usd"].map(
        quantize_usd
    )
    result_df["spend_usd"] = [
        finalize_spend_total(fixed_cost, variable_cost)
        for fixed_cost, variable_cost in zip(
            result_df["fixed_license_cost_usd"],
            result_df["variable_usage_cost_usd"],
            strict=True,
        )
    ]

    return result_df


def build_raw_tool_spend_monthly(
    billed_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    spend_df = calculate_fixed_license_cost(
        billed_df=billed_df,
        config=config,
    )

    if billed_df.empty:
        raise RuntimeError(
            "billed_df is empty; raw_tool_spend_monthly cannot be built."
        )

    spend_df = calculate_variable_usage_cost(
        billed_df=spend_df,
        config=config,
    )
    spend_df = derive_spend_usd(spend_df)
    spend_df = apply_spend_rounding(spend_df)

    spend_df = spend_df.sort_values(
        by=["billing_month", "team_order", "tool_order"],
        kind="stable",
    ).reset_index(drop=True)

    final_columns = [
        "billing_month",
        "team_name",
        "department_name",
        "tool_code",
        "licensed_seats",
        "fixed_license_cost_usd",
        "variable_usage_cost_usd",
        "spend_usd",
    ]

    return spend_df.loc[:, final_columns].copy()
