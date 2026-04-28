from __future__ import annotations

import pandas as pd

from generator.assemble.ordering import enforce_column_order, sort_raw_table
from generator.types import OrgSeed, ToolSeed

RAW_ACCESS_REQUEST_COLUMNS = (
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
)


def build_raw_tool_catalog_df(tool_seed: ToolSeed) -> pd.DataFrame:
    rows = [
        {
            "tool_code": tool.tool_code,
            "tool_name": tool.tool_name,
            "vendor_name": tool.vendor_name,
            "tool_category": tool.tool_category,
            "deployment_scope": tool.deployment_scope,
            "risk_tier": tool.risk_tier,
            "is_active": tool.is_active,
            "homepage_url": tool.homepage_url,
        }
        for tool in tool_seed.tools
    ]
    return pd.DataFrame.from_records(rows)


def build_raw_access_requests_df(
    request_review_detail_df: pd.DataFrame,
) -> pd.DataFrame:
    return request_review_detail_df.loc[:, list(RAW_ACCESS_REQUEST_COLUMNS)].copy()


def assemble_raw_tables(
    *,
    tool_seed: ToolSeed,
    org_seed: OrgSeed,
    user_df: pd.DataFrame,
    request_review_detail_df: pd.DataFrame,
    usage_df: pd.DataFrame,
    spend_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    raw_tables: dict[str, pd.DataFrame] = {
        "raw_tool_catalog": build_raw_tool_catalog_df(tool_seed),
        "raw_user_directory": user_df.copy(),
        "raw_access_requests": build_raw_access_requests_df(request_review_detail_df),
        "raw_usage_events_daily": usage_df.copy(),
        "raw_tool_spend_monthly": spend_df.copy(),
    }

    final_tables: dict[str, pd.DataFrame] = {}
    for table_name, df in raw_tables.items():
        ordered_df = enforce_column_order(df, table_name)
        sorted_df = sort_raw_table(
            table_name,
            ordered_df,
            org_seed=org_seed,
            tool_seed=tool_seed,
        )
        final_tables[table_name] = sorted_df

    return final_tables
