from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from generator.helpers.validation import (
    validate_raw_access_requests,
    validate_raw_tool_catalog,
    validate_tool_spend_monthly,
    validate_usage_events_daily,
    validate_user_directory,
)
from generator.types import OrgSeed, RuntimeConfig, ToolSeed, UserUniverses


def _passed(name: str, details: str) -> dict[str, Any]:
    return {
        "name": name,
        "passed": True,
        "details": details,
    }


def run_table_local_qa(
    *,
    raw_tables: Mapping[str, pd.DataFrame],
    org_seed: OrgSeed,
    tool_seed: ToolSeed,
    user_universes: UserUniverses,
    approved_active_pairs_df: pd.DataFrame,
    approved_inactive_pairs_df: pd.DataFrame,
    anomaly_pairs_df: pd.DataFrame,
    config: RuntimeConfig,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    tool_df = raw_tables["raw_tool_catalog"]
    user_df = raw_tables["raw_user_directory"]
    access_request_df = raw_tables["raw_access_requests"]
    usage_df = raw_tables["raw_usage_events_daily"]
    spend_df = raw_tables["raw_tool_spend_monthly"]

    validate_raw_tool_catalog(tool_df, tool_seed, config)
    results.append(
        _passed(
            "raw_tool_catalog_local_contract",
            "Canonical schema, seed-order, and allowed-value checks passed.",
        )
    )

    validate_user_directory(user_df, user_universes, org_seed, config)
    results.append(
        _passed(
            "raw_user_directory_local_contract",
            "Canonical schema, quotas, ordering, and user-universe checks passed.",
        )
    )

    validate_raw_access_requests(
        access_request_df,
        user_df,
        tool_seed,
        config,
    )
    results.append(
        _passed(
            "raw_access_requests_local_contract",
            "Canonical schema, workflow nullability, references, and ordering checks passed.",
        )
    )

    validate_usage_events_daily(
        usage_df,
        user_df,
        approved_active_pairs_df,
        approved_inactive_pairs_df,
        anomaly_pairs_df,
        config,
    )
    results.append(
        _passed(
            "raw_usage_events_daily_local_contract",
            "Canonical schema, row-range, pair-state, metric, and ordering checks passed.",
        )
    )

    validate_tool_spend_monthly(
        spend_df,
        org_seed,
        tool_seed,
        config,
    )
    results.append(
        _passed(
            "raw_tool_spend_monthly_local_contract",
            "Canonical schema, spend math, seat constraints, and ordering checks passed.",
        )
    )

    return results
