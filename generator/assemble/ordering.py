from __future__ import annotations

import pandas as pd

from generator.types import OrgSeed, ToolSeed

RAW_TABLE_COLUMN_ORDERS: dict[str, tuple[str, ...]] = {
    "raw_tool_catalog": (
        "tool_code",
        "tool_name",
        "vendor_name",
        "tool_category",
        "deployment_scope",
        "risk_tier",
        "is_active",
        "homepage_url",
    ),
    "raw_user_directory": (
        "user_id",
        "user_name",
        "user_email",
        "team_name",
        "department_name",
        "job_level",
        "employment_status",
    ),
    "raw_access_requests": (
        "request_id",
        "requested_at",
        "requester_user_id",
        "tool_code",
        "request_purpose",
        "data_classification",
        "business_justification_text",
        "request_status",
        "reviewed_at",
        "reviewed_by_user_id",
        "review_comment_text",
    ),
    "raw_usage_events_daily": (
        "usage_date",
        "user_id",
        "tool_code",
        "session_count",
        "prompt_count",
        "input_tokens_total",
        "output_tokens_total",
    ),
    "raw_tool_spend_monthly": (
        "billing_month",
        "team_name",
        "department_name",
        "tool_code",
        "licensed_seats",
        "fixed_license_cost_usd",
        "variable_usage_cost_usd",
        "spend_usd",
    ),
}


def get_canonical_column_order(table_name: str) -> tuple[str, ...]:
    try:
        return RAW_TABLE_COLUMN_ORDERS[table_name]
    except KeyError as exc:
        raise ValueError(f"Unknown raw table name: {table_name!r}") from exc


def enforce_column_order(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    expected_columns = get_canonical_column_order(table_name)
    missing_columns = [
        column for column in expected_columns if column not in df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"{table_name} is missing required columns for final assembly: {missing_columns}"
        )
    return df.loc[:, list(expected_columns)].copy()


def sort_raw_tool_catalog(
    df: pd.DataFrame,
    tool_seed: ToolSeed,
) -> pd.DataFrame:
    return (
        df.assign(_tool_order=df["tool_code"].map(dict(tool_seed.tool_order_lookup)))
        .sort_values(by=["_tool_order"], kind="stable")
        .drop(columns="_tool_order")
        .reset_index(drop=True)
    )


def sort_raw_user_directory(
    df: pd.DataFrame,
    org_seed: OrgSeed,
) -> pd.DataFrame:
    return (
        df.assign(_team_order=df["team_name"].map(dict(org_seed.team_order_lookup)))
        .sort_values(by=["_team_order", "user_id"], kind="stable")
        .drop(columns="_team_order")
        .reset_index(drop=True)
    )


def sort_raw_access_requests(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(by=["requested_at", "request_id"], kind="stable").reset_index(
        drop=True
    )


def sort_raw_usage_events_daily(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(
        by=["usage_date", "user_id", "tool_code"], kind="stable"
    ).reset_index(drop=True)


def sort_raw_tool_spend_monthly(
    df: pd.DataFrame,
    org_seed: OrgSeed,
    tool_seed: ToolSeed,
) -> pd.DataFrame:
    return (
        df.assign(
            _team_order=df["team_name"].map(dict(org_seed.team_order_lookup)),
            _tool_order=df["tool_code"].map(dict(tool_seed.tool_order_lookup)),
        )
        .sort_values(
            by=["billing_month", "_team_order", "_tool_order"],
            kind="stable",
        )
        .drop(columns=["_team_order", "_tool_order"])
        .reset_index(drop=True)
    )


def sort_raw_table(
    table_name: str,
    df: pd.DataFrame,
    *,
    org_seed: OrgSeed | None = None,
    tool_seed: ToolSeed | None = None,
) -> pd.DataFrame:
    if table_name == "raw_tool_catalog":
        if tool_seed is None:
            raise ValueError("tool_seed is required to sort raw_tool_catalog.")
        return sort_raw_tool_catalog(df, tool_seed)

    if table_name == "raw_user_directory":
        if org_seed is None:
            raise ValueError("org_seed is required to sort raw_user_directory.")
        return sort_raw_user_directory(df, org_seed)

    if table_name == "raw_access_requests":
        return sort_raw_access_requests(df)

    if table_name == "raw_usage_events_daily":
        return sort_raw_usage_events_daily(df)

    if table_name == "raw_tool_spend_monthly":
        if org_seed is None or tool_seed is None:
            raise ValueError(
                "org_seed and tool_seed are required to sort raw_tool_spend_monthly."
            )
        return sort_raw_tool_spend_monthly(df, org_seed, tool_seed)

    raise ValueError(f"Unknown raw table name: {table_name!r}")
