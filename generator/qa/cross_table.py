from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from generator.helpers.validation import ValidationError
from generator.types import OrgSeed


def _passed(name: str, details: str) -> dict[str, Any]:
    return {
        "name": name,
        "passed": True,
        "details": details,
    }


def _validate_access_request_relationships(
    raw_tables: Mapping[str, pd.DataFrame],
) -> None:
    user_ids = set(raw_tables["raw_user_directory"]["user_id"].tolist())
    tool_codes = set(raw_tables["raw_tool_catalog"]["tool_code"].tolist())
    request_df = raw_tables["raw_access_requests"]

    missing_requesters = sorted(
        set(request_df["requester_user_id"].tolist()) - user_ids
    )
    if missing_requesters:
        raise ValidationError(
            "raw_access_requests.requester_user_id contains unresolved users; "
            f"missing={missing_requesters}"
        )

    reviewed_by_user_ids = set(request_df["reviewed_by_user_id"].dropna().tolist())
    missing_reviewers = sorted(reviewed_by_user_ids - user_ids)
    if missing_reviewers:
        raise ValidationError(
            "raw_access_requests.reviewed_by_user_id contains unresolved users; "
            f"missing={missing_reviewers}"
        )

    missing_tool_codes = sorted(set(request_df["tool_code"].tolist()) - tool_codes)
    if missing_tool_codes:
        raise ValidationError(
            "raw_access_requests.tool_code contains unresolved tools; "
            f"missing={missing_tool_codes}"
        )


def _validate_usage_relationships(
    raw_tables: Mapping[str, pd.DataFrame],
) -> None:
    user_ids = set(raw_tables["raw_user_directory"]["user_id"].tolist())
    tool_codes = set(raw_tables["raw_tool_catalog"]["tool_code"].tolist())
    usage_df = raw_tables["raw_usage_events_daily"]

    missing_user_ids = sorted(set(usage_df["user_id"].tolist()) - user_ids)
    if missing_user_ids:
        raise ValidationError(
            "raw_usage_events_daily.user_id contains unresolved users; "
            f"missing={missing_user_ids}"
        )

    missing_tool_codes = sorted(set(usage_df["tool_code"].tolist()) - tool_codes)
    if missing_tool_codes:
        raise ValidationError(
            "raw_usage_events_daily.tool_code contains unresolved tools; "
            f"missing={missing_tool_codes}"
        )


def _validate_spend_relationships(
    raw_tables: Mapping[str, pd.DataFrame],
    org_seed: OrgSeed,
) -> None:
    tool_codes = set(raw_tables["raw_tool_catalog"]["tool_code"].tolist())
    spend_df = raw_tables["raw_tool_spend_monthly"]
    team_to_department = dict(org_seed.team_to_department_lookup)

    missing_tool_codes = sorted(set(spend_df["tool_code"].tolist()) - tool_codes)
    if missing_tool_codes:
        raise ValidationError(
            "raw_tool_spend_monthly.tool_code contains unresolved tools; "
            f"missing={missing_tool_codes}"
        )

    expected_departments = spend_df["team_name"].map(team_to_department)
    invalid_department_df = spend_df.loc[
        spend_df["department_name"] != expected_departments
    ].copy()
    if not invalid_department_df.empty:
        raise ValidationError(
            "raw_tool_spend_monthly has rows where department_name does not match the fixed team lookup."
        )


def _validate_inactive_user_exclusion(
    raw_tables: Mapping[str, pd.DataFrame],
) -> None:
    user_df = raw_tables["raw_user_directory"]
    request_df = raw_tables["raw_access_requests"]
    usage_df = raw_tables["raw_usage_events_daily"]

    inactive_user_ids = set(
        user_df.loc[user_df["employment_status"] == "inactive", "user_id"].tolist()
    )

    inactive_requesters = sorted(
        set(request_df["requester_user_id"].tolist()) & inactive_user_ids
    )
    if inactive_requesters:
        raise ValidationError(
            "Inactive users must not appear as requesters in final raw_access_requests; "
            f"user_ids={inactive_requesters}"
        )

    inactive_reviewers = sorted(
        set(request_df["reviewed_by_user_id"].dropna().tolist()) & inactive_user_ids
    )
    if inactive_reviewers:
        raise ValidationError(
            "Inactive users must not appear as reviewers in final raw_access_requests; "
            f"user_ids={inactive_reviewers}"
        )

    inactive_usage_users = sorted(set(usage_df["user_id"].tolist()) & inactive_user_ids)
    if inactive_usage_users:
        raise ValidationError(
            "Inactive users must not appear in final raw_usage_events_daily; "
            f"user_ids={inactive_usage_users}"
        )


def run_cross_table_qa(
    *,
    raw_tables: Mapping[str, pd.DataFrame],
    org_seed: OrgSeed,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    _validate_access_request_relationships(raw_tables)
    results.append(
        _passed(
            "access_request_cross_table_relationships",
            "Access-request requester, reviewer, and tool references resolve against final raw dimension seeds.",
        )
    )

    _validate_usage_relationships(raw_tables)
    results.append(
        _passed(
            "usage_cross_table_relationships",
            "Usage user and tool references resolve against final raw dimension seeds.",
        )
    )

    _validate_spend_relationships(raw_tables, org_seed)
    results.append(
        _passed(
            "spend_cross_table_relationships",
            "Spend tool references and team-to-department mappings are consistent with final raw seeds.",
        )
    )

    _validate_inactive_user_exclusion(raw_tables)
    results.append(
        _passed(
            "inactive_user_exclusion",
            "Inactive users are excluded from final requester, reviewer, and usage records.",
        )
    )

    return results
