from __future__ import annotations

from datetime import date

import pandas as pd

from generator.helpers.allocation import largest_remainder_allocate
from generator.types import OrgSeed, RuntimeConfig


def _month_sequence(anchor_month: date, n_months: int) -> tuple[date, ...]:
    if n_months < 1:
        raise ValueError("n_months must be >= 1.")

    anchor_total_month = anchor_month.year * 12 + (anchor_month.month - 1)
    start_total_month = anchor_total_month - (n_months - 1)

    months: list[date] = []
    for offset in range(n_months):
        total_month = start_total_month + offset
        year = total_month // 12
        month = (total_month % 12) + 1
        months.append(date(year, month, 1))

    return tuple(months)


def _validate_request_volume_config(
    config: RuntimeConfig,
    org_seed: OrgSeed,
) -> None:
    annual_team_targets = config.request_volume_config["annual_team_targets"]
    month_seasonality = tuple(config.request_volume_config["month_seasonality"])
    team_tool_weights = config.request_volume_config["team_tool_weights"]

    configured_team_names = tuple(team.team_name for team in org_seed.teams)
    configured_tool_codes = tuple(str(tool["tool_code"]) for tool in config.tool_config)

    if tuple(annual_team_targets.keys()) != configured_team_names:
        raise ValueError(
            "annual_team_targets keys must match configured team order exactly."
        )

    if len(month_seasonality) != config.n_months:
        raise ValueError(
            "month_seasonality length must match RuntimeConfig.n_months exactly."
        )

    if any(value <= 0.0 for value in month_seasonality):
        raise ValueError("month_seasonality values must all be > 0.")

    seasonality_sum = sum(float(value) for value in month_seasonality)
    if abs(seasonality_sum - float(config.n_months)) > 1e-9:
        raise ValueError(
            "month_seasonality must sum to RuntimeConfig.n_months exactly."
        )

    if tuple(team_tool_weights.keys()) != configured_team_names:
        raise ValueError(
            "team_tool_weights keys must match configured team order exactly."
        )

    for team_name in configured_team_names:
        tool_weights = team_tool_weights[team_name]
        if tuple(tool_weights.keys()) != configured_tool_codes:
            raise ValueError(
                "team_tool_weights must preserve TOOL_CONFIG order exactly; "
                f"team={team_name!r}."
            )
        if any(float(weight) < 0.0 for weight in tool_weights.values()):
            raise ValueError(
                f"team_tool_weights must be non-negative; team={team_name!r}."
            )
        if sum(float(weight) for weight in tool_weights.values()) <= 0.0:
            raise ValueError(f"team_tool_weights must sum to > 0; team={team_name!r}.")

    annual_total = sum(int(value) for value in annual_team_targets.values())
    expected_total = int(config.raw_targets["raw_access_requests_rows"])
    if annual_total != expected_total:
        raise ValueError(
            "annual_team_targets total must equal raw_access_requests_rows; "
            f"expected {expected_total}, got {annual_total}."
        )


def allocate_team_month_counts(
    config: RuntimeConfig,
    org_seed: OrgSeed,
) -> pd.DataFrame:
    _validate_request_volume_config(config, org_seed)

    annual_team_targets = config.request_volume_config["annual_team_targets"]
    month_seasonality = tuple(config.request_volume_config["month_seasonality"])
    months = _month_sequence(config.anchor_month, config.n_months)
    month_keys = tuple(month.isoformat() for month in months)
    seasonality_weights = {
        month_key: float(month_seasonality[index])
        for index, month_key in enumerate(month_keys)
    }

    allocations_by_team: dict[str, dict[str, int]] = {}
    for team in org_seed.teams:
        allocations_by_team[team.team_name] = largest_remainder_allocate(
            seasonality_weights,
            int(annual_team_targets[team.team_name]),
            seed=config.seed,
            namespace=f"request_team_month:{team.team_name}",
        )

    rows: list[dict[str, object]] = []
    for month_index, request_month in enumerate(months, start=1):
        month_key = request_month.isoformat()
        for team in org_seed.teams:
            rows.append(
                {
                    "request_month": request_month,
                    "month_index": month_index,
                    "team_name": team.team_name,
                    "department_name": team.department_name,
                    "team_order": team.team_order,
                    "request_count": allocations_by_team[team.team_name][month_key],
                }
            )

    return pd.DataFrame.from_records(
        rows,
        columns=(
            "request_month",
            "month_index",
            "team_name",
            "department_name",
            "team_order",
            "request_count",
        ),
    )


def allocate_team_month_tool_counts(
    team_month_df: pd.DataFrame,
    config: RuntimeConfig,
) -> pd.DataFrame:
    required_columns = (
        "request_month",
        "month_index",
        "team_name",
        "department_name",
        "team_order",
        "request_count",
    )
    missing_columns = [
        column for column in required_columns if column not in team_month_df
    ]
    if missing_columns:
        raise ValueError(
            f"team_month_df is missing required columns: {missing_columns}"
        )

    team_tool_weights = config.request_volume_config["team_tool_weights"]
    tool_ordered_records = tuple(config.tool_config)

    rows: list[dict[str, object]] = []
    for row in team_month_df.itertuples(index=False):
        per_tool_counts = largest_remainder_allocate(
            team_tool_weights[row.team_name],
            int(row.request_count),
            seed=config.seed,
            namespace=(
                "request_team_month_tool:"
                f"{row.team_name}:{row.request_month.isoformat()}"
            ),
        )

        for tool_order, tool_record in enumerate(tool_ordered_records, start=1):
            tool_code = str(tool_record["tool_code"])
            rows.append(
                {
                    "request_month": row.request_month,
                    "month_index": int(row.month_index),
                    "team_name": row.team_name,
                    "department_name": row.department_name,
                    "team_order": int(row.team_order),
                    "tool_code": tool_code,
                    "tool_order": tool_order,
                    "request_count": per_tool_counts[tool_code],
                }
            )

    return pd.DataFrame.from_records(
        rows,
        columns=(
            "request_month",
            "month_index",
            "team_name",
            "department_name",
            "team_order",
            "tool_code",
            "tool_order",
            "request_count",
        ),
    )
