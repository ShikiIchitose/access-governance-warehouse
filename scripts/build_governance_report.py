"""Build the static governance report from dbt mart outputs.

This script reads the business-facing mart tables from the local DuckDB
warehouse and writes a recruiter-facing Markdown report artifact.

The script intentionally acts as a mart consumer. It does not read raw,
staging, core, or intermediate models directly, and it does not recreate
business classification logic already owned by dbt marts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

import duckdb
import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

WAREHOUSE_PATH = REPOSITORY_ROOT / "data" / "warehouse" / "access_governance.duckdb"

REPORT_PATH = REPOSITORY_ROOT / "artifacts" / "reports" / "governance_report_v0_1_0.md"

MART_SCHEMA = "main"

ACCESS_REQUESTS_MONTHLY = f"{MART_SCHEMA}.access_requests_monthly"
TOOL_ADOPTION_MONTHLY = f"{MART_SCHEMA}.tool_adoption_monthly"
ADOPTION_REVIEW_CANDIDATES_MONTHLY = f"{MART_SCHEMA}.adoption_review_candidates_monthly"
GOVERNANCE_EXCEPTIONS_CURRENT = f"{MART_SCHEMA}.governance_exceptions_current"

REQUIRED_MART_TABLES = {
    "access_requests_monthly",
    "tool_adoption_monthly",
    "adoption_review_candidates_monthly",
    "governance_exceptions_current",
}

QUERY_REQUIRED_MART_TABLES = f"""
SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema = '{MART_SCHEMA}'
    AND table_name IN (
        'access_requests_monthly',
        'tool_adoption_monthly',
        'adoption_review_candidates_monthly',
        'governance_exceptions_current'
    )
ORDER BY
    table_name;
"""

QUERY_REPORTING_METADATA = f"""
WITH

request_months AS (
    SELECT
        reporting_month,
        team_name,
        tool_code
    FROM {ACCESS_REQUESTS_MONTHLY}
),

adoption_months AS (
    SELECT
        reporting_month,
        team_name,
        tool_code
    FROM {TOOL_ADOPTION_MONTHLY}
),

combined_reporting_keys AS (
    SELECT
        reporting_month,
        team_name,
        tool_code
    FROM request_months

    UNION

    SELECT
        reporting_month,
        team_name,
        tool_code
    FROM adoption_months
),

final AS (
    SELECT
        min(reporting_month) AS first_reporting_month,
        max(reporting_month) AS latest_reporting_month,
        count(DISTINCT reporting_month) AS reporting_month_count,
        count(DISTINCT team_name) AS team_count,
        count(DISTINCT tool_code) AS tool_count
    FROM combined_reporting_keys
)

SELECT
    first_reporting_month,
    latest_reporting_month,
    reporting_month_count,
    team_count,
    tool_count
FROM final;
"""


QUERY_EXECUTIVE_REQUEST_SUMMARY = f"""
WITH

request_summary AS (
    SELECT
        sum(requests_total) AS total_requests,
        sum(approvals_total) AS total_approvals,
        sum(rejections_total) AS total_rejections,
        (
            sum(approvals_total)
            / nullif(
                sum(approvals_total) + sum(rejections_total),
                0
            )
        ) AS decision_approval_rate,
        (
            sum(
                CASE
                    WHEN avg_approval_lead_time_hours IS NOT null
                        THEN avg_approval_lead_time_hours * approvals_total
                    ELSE 0
                END
            )
            / nullif(
                sum(
                    CASE
                        WHEN avg_approval_lead_time_hours IS NOT null
                            THEN approvals_total
                        ELSE 0
                    END
                ),
                0
            )
        ) AS avg_approval_lead_time_hours
    FROM {ACCESS_REQUESTS_MONTHLY}
),

latest_month AS (
    SELECT
        max(reporting_month) AS latest_reporting_month
    FROM {ACCESS_REQUESTS_MONTHLY}
),

latest_pending AS (
    SELECT
        sum({ACCESS_REQUESTS_MONTHLY}.pending_total) AS latest_pending_total
    FROM {ACCESS_REQUESTS_MONTHLY}
    INNER JOIN latest_month
        ON
            {ACCESS_REQUESTS_MONTHLY}.reporting_month
            = latest_month.latest_reporting_month
),

final AS (
    SELECT
        request_summary.total_requests,
        request_summary.total_approvals,
        request_summary.total_rejections,
        request_summary.decision_approval_rate,
        latest_pending.latest_pending_total,
        request_summary.avg_approval_lead_time_hours
    FROM request_summary
    CROSS JOIN latest_pending
)

SELECT
    total_requests,
    total_approvals,
    total_rejections,
    decision_approval_rate,
    latest_pending_total,
    avg_approval_lead_time_hours
FROM final;
"""


QUERY_EXECUTIVE_ADOPTION_SUMMARY = f"""
WITH

latest_month AS (
    SELECT
        max(reporting_month) AS latest_reporting_month
    FROM {TOOL_ADOPTION_MONTHLY}
),

latest_adoption AS (
    SELECT
        sum(approved_users_total) AS latest_approved_users_total,
        sum(active_users_total) AS latest_active_users_total
    FROM {TOOL_ADOPTION_MONTHLY}
    INNER JOIN latest_month
        ON
            {TOOL_ADOPTION_MONTHLY}.reporting_month
            = latest_month.latest_reporting_month
),

overall_adoption AS (
    SELECT
        sum(total_sessions) AS total_sessions,
        sum(total_prompts) AS total_prompts,
        sum(spend_usd) AS total_spend_usd,
        count(
            CASE
                WHEN spend_usd IS NOT null THEN 1
            END
        ) AS spend_row_count,
        avg(cost_per_active_user) AS avg_cost_per_active_user,
        max(cost_per_active_user) AS max_cost_per_active_user
    FROM {TOOL_ADOPTION_MONTHLY}
),

final AS (
    SELECT
        latest_adoption.latest_approved_users_total,
        latest_adoption.latest_active_users_total,
        overall_adoption.total_sessions,
        overall_adoption.total_prompts,
        overall_adoption.total_spend_usd,
        overall_adoption.spend_row_count,
        overall_adoption.avg_cost_per_active_user,
        overall_adoption.max_cost_per_active_user
    FROM latest_adoption
    CROSS JOIN overall_adoption
)

SELECT
    latest_approved_users_total,
    latest_active_users_total,
    total_sessions,
    total_prompts,
    total_spend_usd,
    spend_row_count,
    avg_cost_per_active_user,
    max_cost_per_active_user
FROM final;
"""


QUERY_EXECUTIVE_REVIEW_CANDIDATE_SUMMARY = f"""
WITH

review_candidate_summary AS (
    SELECT
        count(*) AS review_candidate_rows,
        sum(
            CASE
                WHEN review_status != 'aligned' THEN 1
                ELSE 0
            END
        ) AS non_aligned_rows,
        sum(
            CASE
                WHEN review_priority = 'high' THEN 1
                ELSE 0
            END
        ) AS high_priority_review_candidate_total,
        sum(
            CASE
                WHEN review_status = 'finance_review_active_without_billing'
                    THEN 1
                ELSE 0
            END
        ) AS finance_review_active_without_billing_total,
        sum(
            CASE
                WHEN review_status = 'cost_review_billed_without_usage'
                    THEN 1
                ELSE 0
            END
        ) AS cost_review_billed_without_usage_total,
        sum(
            CASE
                WHEN review_status = 'governance_review_usage_without_approval'
                    THEN 1
                ELSE 0
            END
        ) AS governance_review_usage_without_approval_total,
        sum(
            CASE
                WHEN review_status = 'adoption_review_approved_not_used'
                    THEN 1
                ELSE 0
            END
        ) AS adoption_review_approved_not_used_total
    FROM {ADOPTION_REVIEW_CANDIDATES_MONTHLY}
)

SELECT
    review_candidate_rows,
    non_aligned_rows,
    high_priority_review_candidate_total,
    finance_review_active_without_billing_total,
    cost_review_billed_without_usage_total,
    governance_review_usage_without_approval_total,
    adoption_review_approved_not_used_total
FROM review_candidate_summary;
"""


QUERY_EXECUTIVE_CURRENT_EXCEPTION_SUMMARY = f"""
WITH

current_exception_summary AS (
    SELECT
        count(*) AS current_exception_surface_rows,
        sum(
            CASE
                WHEN has_approved_request_flag THEN 1
                ELSE 0
            END
        ) AS current_approved_rows,
        sum(
            CASE
                WHEN has_recent_usage_30d_flag THEN 1
                ELSE 0
            END
        ) AS current_recent_usage_rows,
        sum(
            CASE
                WHEN used_without_approval_flag THEN 1
                ELSE 0
            END
        ) AS used_without_approval_total,
        sum(
            CASE
                WHEN approved_but_inactive_flag THEN 1
                ELSE 0
            END
        ) AS approved_but_inactive_total
    FROM {GOVERNANCE_EXCEPTIONS_CURRENT}
)

SELECT
    current_exception_surface_rows,
    current_approved_rows,
    current_recent_usage_rows,
    used_without_approval_total,
    approved_but_inactive_total
FROM current_exception_summary;
"""

QUERY_REQUEST_MONTHLY_TREND = f"""
WITH

monthly_trend AS (
    SELECT
        reporting_month,
        sum(requests_total) AS requests_total,
        sum(approvals_total) AS approvals_total,
        sum(rejections_total) AS rejections_total,
        sum(pending_total) AS pending_total,
        (
            sum(
                CASE
                    WHEN avg_approval_lead_time_hours IS NOT null
                        THEN avg_approval_lead_time_hours * approvals_total
                    ELSE 0
                END
            )
            / nullif(
                sum(
                    CASE
                        WHEN avg_approval_lead_time_hours IS NOT null
                            THEN approvals_total
                        ELSE 0
                    END
                ),
                0
            )
        ) AS avg_approval_lead_time_hours
    FROM {ACCESS_REQUESTS_MONTHLY}
    GROUP BY
        reporting_month
)

SELECT
    reporting_month,
    requests_total,
    approvals_total,
    rejections_total,
    pending_total,
    avg_approval_lead_time_hours
FROM monthly_trend
ORDER BY
    reporting_month;
"""


QUERY_REQUEST_TOP_TEAMS = f"""
WITH

latest_month AS (
    SELECT
        max(reporting_month) AS latest_reporting_month
    FROM {ACCESS_REQUESTS_MONTHLY}
),

team_request_totals AS (
    SELECT
        team_name,
        department_name,
        sum(requests_total) AS requests_total,
        sum(approvals_total) AS approvals_total,
        sum(rejections_total) AS rejections_total
    FROM {ACCESS_REQUESTS_MONTHLY}
    GROUP BY
        team_name,
        department_name
),

team_latest_pending AS (
    SELECT
        {ACCESS_REQUESTS_MONTHLY}.team_name,
        {ACCESS_REQUESTS_MONTHLY}.department_name,
        sum({ACCESS_REQUESTS_MONTHLY}.pending_total) AS latest_pending_total
    FROM {ACCESS_REQUESTS_MONTHLY}
    INNER JOIN latest_month
        ON
            {ACCESS_REQUESTS_MONTHLY}.reporting_month
            = latest_month.latest_reporting_month
    GROUP BY
        {ACCESS_REQUESTS_MONTHLY}.team_name,
        {ACCESS_REQUESTS_MONTHLY}.department_name
),

team_summary AS (
    SELECT
        team_request_totals.team_name,
        team_request_totals.department_name,
        team_request_totals.requests_total,
        team_request_totals.approvals_total,
        team_request_totals.rejections_total,
        coalesce(
            team_latest_pending.latest_pending_total,
            0
        ) AS latest_pending_total
    FROM team_request_totals
    LEFT JOIN team_latest_pending
        ON
            team_request_totals.team_name
            = team_latest_pending.team_name
            AND team_request_totals.department_name
            = team_latest_pending.department_name
)

SELECT
    team_name,
    department_name,
    requests_total,
    approvals_total,
    rejections_total,
    latest_pending_total
FROM team_summary
ORDER BY
    requests_total DESC,
    team_name
LIMIT 5;
"""


QUERY_REQUEST_TOP_TOOLS = f"""
WITH

tool_request_totals AS (
    SELECT
        tool_code,
        tool_name,
        vendor_name,
        risk_tier,
        sum(requests_total) AS requests_total,
        sum(approvals_total) AS approvals_total,
        sum(rejections_total) AS rejections_total
    FROM {ACCESS_REQUESTS_MONTHLY}
    GROUP BY
        tool_code,
        tool_name,
        vendor_name,
        risk_tier
)

SELECT
    tool_code,
    tool_name,
    vendor_name,
    risk_tier,
    requests_total,
    approvals_total,
    rejections_total
FROM tool_request_totals
ORDER BY
    requests_total DESC,
    tool_code
LIMIT 5;
"""

QUERY_ADOPTION_TOP_TOOLS = f"""
WITH

latest_month AS (
    SELECT
        max(reporting_month) AS latest_reporting_month
    FROM {TOOL_ADOPTION_MONTHLY}
),

tool_usage_totals AS (
    SELECT
        tool_code,
        tool_name,
        vendor_name,
        risk_tier,
        sum(active_users_total) AS active_users_total,
        sum(total_sessions) AS total_sessions,
        sum(total_prompts) AS total_prompts
    FROM {TOOL_ADOPTION_MONTHLY}
    GROUP BY
        tool_code,
        tool_name,
        vendor_name,
        risk_tier
),

tool_latest_approved AS (
    SELECT
        {TOOL_ADOPTION_MONTHLY}.tool_code,
        sum({TOOL_ADOPTION_MONTHLY}.approved_users_total)
            AS latest_approved_users_total
    FROM {TOOL_ADOPTION_MONTHLY}
    INNER JOIN latest_month
        ON
            {TOOL_ADOPTION_MONTHLY}.reporting_month
            = latest_month.latest_reporting_month
    GROUP BY
        {TOOL_ADOPTION_MONTHLY}.tool_code
),

tool_adoption_summary AS (
    SELECT
        tool_usage_totals.tool_code,
        tool_usage_totals.tool_name,
        tool_usage_totals.vendor_name,
        tool_usage_totals.risk_tier,
        coalesce(
            tool_latest_approved.latest_approved_users_total,
            0
        ) AS latest_approved_users_total,
        tool_usage_totals.active_users_total,
        tool_usage_totals.total_sessions,
        tool_usage_totals.total_prompts
    FROM tool_usage_totals
    LEFT JOIN tool_latest_approved
        ON
            tool_usage_totals.tool_code
            = tool_latest_approved.tool_code
)

SELECT
    tool_code,
    tool_name,
    vendor_name,
    risk_tier,
    latest_approved_users_total,
    active_users_total,
    total_sessions,
    total_prompts
FROM tool_adoption_summary
ORDER BY
    active_users_total DESC,
    total_sessions DESC,
    tool_code
LIMIT 5;
"""


QUERY_ADOPTION_TOP_TEAMS = f"""
WITH

latest_month AS (
    SELECT
        max(reporting_month) AS latest_reporting_month
    FROM {TOOL_ADOPTION_MONTHLY}
),

team_usage_totals AS (
    SELECT
        team_name,
        department_name,
        sum(active_users_total) AS active_users_total,
        sum(total_sessions) AS total_sessions,
        sum(total_prompts) AS total_prompts
    FROM {TOOL_ADOPTION_MONTHLY}
    GROUP BY
        team_name,
        department_name
),

team_latest_approved AS (
    SELECT
        {TOOL_ADOPTION_MONTHLY}.team_name,
        {TOOL_ADOPTION_MONTHLY}.department_name,
        sum({TOOL_ADOPTION_MONTHLY}.approved_users_total)
            AS latest_approved_users_total
    FROM {TOOL_ADOPTION_MONTHLY}
    INNER JOIN latest_month
        ON
            {TOOL_ADOPTION_MONTHLY}.reporting_month
            = latest_month.latest_reporting_month
    GROUP BY
        {TOOL_ADOPTION_MONTHLY}.team_name,
        {TOOL_ADOPTION_MONTHLY}.department_name
),

team_adoption_summary AS (
    SELECT
        team_usage_totals.team_name,
        team_usage_totals.department_name,
        coalesce(
            team_latest_approved.latest_approved_users_total,
            0
        ) AS latest_approved_users_total,
        team_usage_totals.active_users_total,
        team_usage_totals.total_sessions,
        team_usage_totals.total_prompts
    FROM team_usage_totals
    LEFT JOIN team_latest_approved
        ON
            team_usage_totals.team_name
            = team_latest_approved.team_name
            AND team_usage_totals.department_name
            = team_latest_approved.department_name
)

SELECT
    team_name,
    department_name,
    latest_approved_users_total,
    active_users_total,
    total_sessions,
    total_prompts
FROM team_adoption_summary
ORDER BY
    active_users_total DESC,
    total_sessions DESC,
    team_name
LIMIT 5;
"""

QUERY_SPEND_SUMMARY = f"""
WITH

spend_summary AS (
    SELECT
        sum(spend_usd) AS total_spend_usd,
        count(
            CASE
                WHEN spend_usd IS NOT null THEN 1
            END
        ) AS spend_row_count,
        sum(
            CASE
                WHEN active_users_total > 0 AND spend_usd IS NOT null
                    THEN 1
                ELSE 0
            END
        ) AS rows_with_usage_and_spend,
        sum(
            CASE
                WHEN active_users_total = 0 AND spend_usd IS NOT null
                    THEN 1
                ELSE 0
            END
        ) AS rows_with_spend_without_usage,
        sum(
            CASE
                WHEN active_users_total > 0 AND spend_usd IS null
                    THEN 1
                ELSE 0
            END
        ) AS rows_with_usage_without_spend,
        avg(cost_per_active_user) AS avg_cost_per_active_user,
        max(cost_per_active_user) AS max_cost_per_active_user
    FROM {TOOL_ADOPTION_MONTHLY}
)

SELECT
    total_spend_usd,
    spend_row_count,
    rows_with_usage_and_spend,
    rows_with_spend_without_usage,
    rows_with_usage_without_spend,
    avg_cost_per_active_user,
    max_cost_per_active_user
FROM spend_summary;
"""


QUERY_SPEND_TOP_TOOLS = f"""
WITH

tool_spend_summary AS (
    SELECT
        tool_code,
        tool_name,
        vendor_name,
        risk_tier,
        sum(spend_usd) AS spend_usd,
        sum(active_users_total) AS active_user_months,
        (
            sum(spend_usd)
            / nullif(sum(active_users_total), 0)
        ) AS cost_per_active_user_month
    FROM {TOOL_ADOPTION_MONTHLY}
    WHERE spend_usd IS NOT null
    GROUP BY
        tool_code,
        tool_name,
        vendor_name,
        risk_tier
)

SELECT
    tool_code,
    tool_name,
    vendor_name,
    risk_tier,
    spend_usd,
    active_user_months,
    cost_per_active_user_month
FROM tool_spend_summary
ORDER BY
    spend_usd DESC,
    tool_code
LIMIT 5;
"""


QUERY_SPEND_TOP_TEAMS = f"""
WITH

team_spend_summary AS (
    SELECT
        team_name,
        department_name,
        sum(spend_usd) AS spend_usd,
        sum(active_users_total) AS active_user_months,
        (
            sum(spend_usd)
            / nullif(sum(active_users_total), 0)
        ) AS cost_per_active_user_month
    FROM {TOOL_ADOPTION_MONTHLY}
    WHERE spend_usd IS NOT null
    GROUP BY
        team_name,
        department_name
)

SELECT
    team_name,
    department_name,
    spend_usd,
    active_user_months,
    cost_per_active_user_month
FROM team_spend_summary
ORDER BY
    spend_usd DESC,
    team_name
LIMIT 5;
"""

QUERY_REVIEW_STATUS_SUMMARY = f"""
WITH

review_status_summary AS (
    SELECT
        review_status,
        count(*) AS rows_total,
        sum(
            CASE
                WHEN review_priority = 'high' THEN 1
                ELSE 0
            END
        ) AS high_priority_rows,
        sum(
            CASE
                WHEN review_priority = 'medium' THEN 1
                ELSE 0
            END
        ) AS medium_priority_rows,
        sum(
            CASE
                WHEN review_priority = 'low' THEN 1
                ELSE 0
            END
        ) AS low_priority_rows
    FROM {ADOPTION_REVIEW_CANDIDATES_MONTHLY}
    GROUP BY
        review_status
)

SELECT
    review_status,
    rows_total,
    high_priority_rows,
    medium_priority_rows,
    low_priority_rows
FROM review_status_summary
ORDER BY
    rows_total DESC,
    review_status;
"""


QUERY_REVIEW_OWNER_SUMMARY = f"""
WITH

review_owner_summary AS (
    SELECT
        review_owner_hint,
        count(*) AS rows_total,
        sum(
            CASE
                WHEN review_priority = 'high' THEN 1
                ELSE 0
            END
        ) AS high_priority_rows,
        sum(
            CASE
                WHEN review_status != 'aligned' THEN 1
                ELSE 0
            END
        ) AS non_aligned_rows
    FROM {ADOPTION_REVIEW_CANDIDATES_MONTHLY}
    GROUP BY
        review_owner_hint
)

SELECT
    review_owner_hint,
    rows_total,
    high_priority_rows,
    non_aligned_rows
FROM review_owner_summary
ORDER BY
    non_aligned_rows DESC,
    review_owner_hint;
"""


QUERY_REVIEW_TOP_HIGH_PRIORITY = f"""
WITH

high_priority_candidates AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code,
        tool_name,
        vendor_name,
        risk_tier,
        approved_users_total,
        active_users_total,
        total_sessions,
        total_prompts,
        spend_usd,
        cost_per_active_user,
        review_status,
        review_owner_hint,
        review_priority,
        CASE
            WHEN risk_tier = 'high' THEN 3
            WHEN risk_tier = 'medium' THEN 2
            WHEN risk_tier = 'low' THEN 1
            ELSE 0
        END AS risk_tier_sort_order
    FROM {ADOPTION_REVIEW_CANDIDATES_MONTHLY}
    WHERE review_priority = 'high'
)

SELECT
    reporting_month,
    team_name,
    department_name,
    tool_code,
    tool_name,
    vendor_name,
    risk_tier,
    approved_users_total,
    active_users_total,
    total_sessions,
    total_prompts,
    spend_usd,
    cost_per_active_user,
    review_status,
    review_owner_hint,
    review_priority
FROM high_priority_candidates
ORDER BY
    reporting_month DESC,
    risk_tier_sort_order DESC,
    review_status,
    team_name,
    tool_code
LIMIT 10;
"""

QUERY_CURRENT_EXCEPTION_SECTION_SUMMARY = f"""
WITH

exception_summary AS (
    SELECT
        count(*) AS current_exception_surface_rows,
        sum(
            CASE
                WHEN has_approved_request_flag THEN 1
                ELSE 0
            END
        ) AS approved_rows,
        sum(
            CASE
                WHEN has_recent_usage_30d_flag THEN 1
                ELSE 0
            END
        ) AS recent_usage_rows,
        sum(
            CASE
                WHEN used_without_approval_flag THEN 1
                ELSE 0
            END
        ) AS used_without_approval_rows,
        sum(
            CASE
                WHEN approved_but_inactive_flag THEN 1
                ELSE 0
            END
        ) AS approved_but_inactive_rows
    FROM {GOVERNANCE_EXCEPTIONS_CURRENT}
)

SELECT
    current_exception_surface_rows,
    approved_rows,
    recent_usage_rows,
    used_without_approval_rows,
    approved_but_inactive_rows
FROM exception_summary;
"""


QUERY_EXCEPTION_BY_TEAM = f"""
WITH

exception_by_team AS (
    SELECT
        team_name,
        department_name,
        sum(
            CASE
                WHEN used_without_approval_flag THEN 1
                ELSE 0
            END
        ) AS used_without_approval_rows,
        sum(
            CASE
                WHEN approved_but_inactive_flag THEN 1
                ELSE 0
            END
        ) AS approved_but_inactive_rows
    FROM {GOVERNANCE_EXCEPTIONS_CURRENT}
    GROUP BY
        team_name,
        department_name
)

SELECT
    team_name,
    department_name,
    used_without_approval_rows,
    approved_but_inactive_rows
FROM exception_by_team
ORDER BY
    used_without_approval_rows DESC,
    approved_but_inactive_rows DESC,
    team_name;
"""


QUERY_EXCEPTION_BY_TOOL = f"""
WITH

exception_by_tool AS (
    SELECT
        tool_code,
        tool_name,
        vendor_name,
        risk_tier,
        sum(
            CASE
                WHEN used_without_approval_flag THEN 1
                ELSE 0
            END
        ) AS used_without_approval_rows,
        sum(
            CASE
                WHEN approved_but_inactive_flag THEN 1
                ELSE 0
            END
        ) AS approved_but_inactive_rows
    FROM {GOVERNANCE_EXCEPTIONS_CURRENT}
    GROUP BY
        tool_code,
        tool_name,
        vendor_name,
        risk_tier
)

SELECT
    tool_code,
    tool_name,
    vendor_name,
    risk_tier,
    used_without_approval_rows,
    approved_but_inactive_rows
FROM exception_by_tool
ORDER BY
    used_without_approval_rows DESC,
    approved_but_inactive_rows DESC,
    tool_code;
"""


QUERY_EXCEPTION_SAMPLE_USED_WITHOUT_APPROVAL = f"""
WITH

used_without_approval AS (
    SELECT
        user_id,
        user_name,
        user_email,
        team_name,
        department_name,
        tool_code,
        tool_name,
        vendor_name,
        risk_tier,
        has_approved_request_flag,
        has_recent_usage_30d_flag,
        used_without_approval_flag,
        approved_but_inactive_flag,
        CASE
            WHEN risk_tier = 'high' THEN 3
            WHEN risk_tier = 'medium' THEN 2
            WHEN risk_tier = 'low' THEN 1
            ELSE 0
        END AS risk_tier_sort_order
    FROM {GOVERNANCE_EXCEPTIONS_CURRENT}
    WHERE used_without_approval_flag
)

SELECT
    user_id,
    user_name,
    user_email,
    team_name,
    department_name,
    tool_code,
    tool_name,
    vendor_name,
    risk_tier,
    has_approved_request_flag,
    has_recent_usage_30d_flag,
    used_without_approval_flag,
    approved_but_inactive_flag
FROM used_without_approval
ORDER BY
    risk_tier_sort_order DESC,
    team_name,
    user_id,
    tool_code
LIMIT 10;
"""

ColumnFormatter = Callable[[Any], str]


def connect_warehouse() -> duckdb.DuckDBPyConnection:
    """Connect to the local DuckDB warehouse in read-only mode."""
    if not WAREHOUSE_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB warehouse file was not found: {WAREHOUSE_PATH}"
        )

    return duckdb.connect(str(WAREHOUSE_PATH), read_only=True)


def fetch_dataframe(
    connection: duckdb.DuckDBPyConnection,
    query: str,
) -> pd.DataFrame:
    """Execute a SQL query and return the result as a pandas DataFrame."""
    return connection.sql(query).df()


def fetch_one(
    connection: duckdb.DuckDBPyConnection,
    query: str,
) -> dict[str, Any]:
    """Execute a SQL query that must return exactly one row."""
    dataframe = fetch_dataframe(connection, query)

    if dataframe.empty:
        raise ValueError("Expected one row, but the query returned no rows.")

    if len(dataframe.index) != 1:
        raise ValueError(
            f"Expected one row, but the query returned {len(dataframe.index)} rows."
        )

    return dataframe.iloc[0].to_dict()


def validate_required_mart_tables(connection: duckdb.DuckDBPyConnection) -> None:
    """Validate that all required mart tables exist in the DuckDB warehouse."""
    table_df = fetch_dataframe(connection, QUERY_REQUIRED_MART_TABLES)
    found_tables = set(table_df["table_name"].to_list())
    missing_tables = sorted(REQUIRED_MART_TABLES - found_tables)

    if missing_tables:
        missing_text = ", ".join(f"{MART_SCHEMA}.{name}" for name in missing_tables)
        raise RuntimeError(
            "Required mart tables were not found. "
            "Run `uv run dbt run --select marts` first. "
            f"Missing: {missing_text}"
        )


def format_int(value: Any) -> str:
    """Format an integer-like value for the report."""
    if pd.isna(value):
        return "N/A"

    return f"{int(value):,}"


def format_float(value: Any, digits: int = 1) -> str:
    """Format a float-like value for the report."""
    if pd.isna(value):
        return "N/A"

    return f"{float(value):,.{digits}f}"


def format_pct(value: Any, digits: int = 1) -> str:
    """Format a ratio as a percentage."""
    if pd.isna(value):
        return "N/A"

    return f"{float(value) * 100:.{digits}f}%"


def format_usd(value: Any) -> str:
    """Format a USD value.

    Important:
        Null spend is rendered as N/A, not $0.00.
    """
    if pd.isna(value):
        return "N/A"

    return f"${float(value):,.2f}"


def format_bool(value: Any) -> str:
    """Format a boolean value for human-readable report tables."""
    if pd.isna(value):
        return "N/A"

    return "Yes" if bool(value) else "No"


def format_date(value: Any) -> str:
    """Format a date-like value as ISO date text."""
    if pd.isna(value):
        return "N/A"

    return pd.to_datetime(value).date().isoformat()


def add_rank_column(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add a 1-based rank column for display tables."""
    ranked = dataframe.copy()
    ranked.insert(0, "Rank", range(1, len(ranked.index) + 1))
    return ranked


def dataframe_to_markdown(
    dataframe: pd.DataFrame,
    column_formatters: dict[str, ColumnFormatter] | None = None,
) -> str:
    """Render a DataFrame as a GitHub-friendly Markdown table."""
    if dataframe.empty:
        return "_No rows returned._"

    formatted = dataframe.copy()
    column_formatters = column_formatters or {}

    for column_name, formatter in column_formatters.items():
        if column_name in formatted.columns:
            formatted[column_name] = formatted[column_name].map(formatter)

    return formatted.to_markdown(
        index=False,
        tablefmt="github",
    )


def render_title(metadata: dict[str, Any]) -> str:
    """Render the report title and reporting window."""
    first_month = format_date(metadata["first_reporting_month"])
    latest_month = format_date(metadata["latest_reporting_month"])

    return "\n".join(
        [
            "# Access Governance Warehouse Report v0.1.0",
            "",
            "Generated from `access-governance-warehouse` mart outputs.",
            "",
            f"Reporting window: `{first_month}` to `{latest_month}`.",
        ]
    )


def render_executive_summary(
    metadata: dict[str, Any],
    request_summary: dict[str, Any],
    adoption_summary: dict[str, Any],
    review_candidate_summary: dict[str, Any],
    exception_summary: dict[str, Any],
) -> str:
    """Render the Executive Summary section."""
    key_metrics_df = pd.DataFrame(
        [
            {
                "Metric": "Reporting months",
                "Value": format_int(metadata["reporting_month_count"]),
            },
            {
                "Metric": "Teams",
                "Value": format_int(metadata["team_count"]),
            },
            {
                "Metric": "Tools",
                "Value": format_int(metadata["tool_count"]),
            },
            {
                "Metric": "Total access requests",
                "Value": format_int(request_summary["total_requests"]),
            },
            {
                "Metric": "Total approvals",
                "Value": format_int(request_summary["total_approvals"]),
            },
            {
                "Metric": "Total rejections",
                "Value": format_int(request_summary["total_rejections"]),
            },
            {
                "Metric": "Decision approval rate",
                "Value": format_pct(request_summary["decision_approval_rate"]),
            },
            {
                "Metric": "Latest month-end pending requests",
                "Value": format_int(request_summary["latest_pending_total"]),
            },
            {
                "Metric": "Average approval lead time",
                "Value": (
                    f"{format_float(request_summary['avg_approval_lead_time_hours'])} "
                    "hours"
                ),
            },
            {
                "Metric": "Approved users summed across latest month team-tool rows",
                "Value": format_int(adoption_summary["latest_approved_users_total"]),
            },
            {
                "Metric": "Active users summed across latest month team-tool rows",
                "Value": format_int(adoption_summary["latest_active_users_total"]),
            },
            {
                "Metric": "Total sessions",
                "Value": format_int(adoption_summary["total_sessions"]),
            },
            {
                "Metric": "Total prompts",
                "Value": format_int(adoption_summary["total_prompts"]),
            },
            {
                "Metric": "Total spend",
                "Value": format_usd(adoption_summary["total_spend_usd"]),
            },
            {
                "Metric": "Spend rows",
                "Value": format_int(adoption_summary["spend_row_count"]),
            },
            {
                "Metric": "High-priority monthly review candidates",
                "Value": format_int(
                    review_candidate_summary["high_priority_review_candidate_total"]
                ),
            },
            {
                "Metric": "Current used-without-approval exceptions",
                "Value": format_int(exception_summary["used_without_approval_total"]),
            },
            {
                "Metric": "Current approved-but-inactive cases",
                "Value": format_int(exception_summary["approved_but_inactive_total"]),
            },
        ]
    )

    return "\n".join(
        [
            "## 1. Executive Summary",
            "",
            "This report summarizes synthetic enterprise AI tool access "
            "governance signals generated by the `access-governance-warehouse` "
            "dbt project.",
            "",
            "The warehouse models access requests, approved access stock, daily "
            "usage, monthly spend, and review candidates for enterprise AI tools. "
            "The report is generated from the business-facing mart layer, not "
            "directly from raw source files.",
            "",
            "### Key metrics",
            "",
            dataframe_to_markdown(key_metrics_df),
            "",
            "### Interpretation",
            "",
            "The report should be read as a portfolio-facing analytical summary. "
            "It demonstrates how the dbt warehouse turns raw access, usage, and "
            "spend data into reviewer-facing governance outputs.",
            "",
            "Business review candidates are analytical signals. They are not "
            "treated as dbt pipeline failures by themselves.",
        ]
    )


def render_request_trends(
    request_summary: dict[str, Any],
    monthly_trend_df: pd.DataFrame,
    top_teams_df: pd.DataFrame,
    top_tools_df: pd.DataFrame,
) -> str:
    """Render the Request Trends section."""
    request_summary_df = pd.DataFrame(
        [
            {
                "Metric": "Total requests",
                "Value": format_int(request_summary["total_requests"]),
            },
            {
                "Metric": "Total approvals",
                "Value": format_int(request_summary["total_approvals"]),
            },
            {
                "Metric": "Total rejections",
                "Value": format_int(request_summary["total_rejections"]),
            },
            {
                "Metric": "Decision approval rate",
                "Value": format_pct(request_summary["decision_approval_rate"]),
            },
            {
                "Metric": "Latest month-end pending requests",
                "Value": format_int(request_summary["latest_pending_total"]),
            },
            {
                "Metric": "Average approval lead time",
                "Value": (
                    f"{format_float(request_summary['avg_approval_lead_time_hours'])} "
                    "hours"
                ),
            },
        ]
    )

    monthly_trend_display = monthly_trend_df.rename(
        columns={
            "reporting_month": "Reporting month",
            "requests_total": "Requests",
            "approvals_total": "Approvals",
            "rejections_total": "Rejections",
            "pending_total": "Pending at month end",
            "avg_approval_lead_time_hours": "Average approval lead time hours",
        }
    )

    top_teams_display = add_rank_column(
        top_teams_df.rename(
            columns={
                "team_name": "Team",
                "department_name": "Department",
                "requests_total": "Requests",
                "approvals_total": "Approvals",
                "rejections_total": "Rejections",
                "latest_pending_total": "Latest pending",
            }
        )
    )

    top_tools_display = add_rank_column(
        top_tools_df.rename(
            columns={
                "tool_code": "Tool code",
                "tool_name": "Tool",
                "vendor_name": "Vendor",
                "risk_tier": "Risk tier",
                "requests_total": "Requests",
                "approvals_total": "Approvals",
                "rejections_total": "Rejections",
            }
        )
    )

    return "\n".join(
        [
            "## 2. Request Trends",
            "",
            "Source mart: `access_requests_monthly`",
            "",
            "This section summarizes request inflow, review outcomes, and "
            "month-end backlog by reporting month, team, and tool.",
            "",
            "### Request summary",
            "",
            dataframe_to_markdown(request_summary_df),
            "",
            "### Monthly request trend",
            "",
            dataframe_to_markdown(
                monthly_trend_display,
                column_formatters={
                    "Reporting month": format_date,
                    "Requests": format_int,
                    "Approvals": format_int,
                    "Rejections": format_int,
                    "Pending at month end": format_int,
                    "Average approval lead time hours": lambda value: format_float(
                        value,
                        digits=1,
                    ),
                },
            ),
            "",
            "### Top teams by request volume",
            "",
            dataframe_to_markdown(
                top_teams_display,
                column_formatters={
                    "Rank": format_int,
                    "Requests": format_int,
                    "Approvals": format_int,
                    "Rejections": format_int,
                    "Latest pending": format_int,
                },
            ),
            "",
            "### Top tools by request volume",
            "",
            dataframe_to_markdown(
                top_tools_display,
                column_formatters={
                    "Rank": format_int,
                    "Requests": format_int,
                    "Approvals": format_int,
                    "Rejections": format_int,
                },
            ),
            "",
            "### Request trend notes",
            "",
            "- `requests_total` is grouped by request submission month.",
            "- `approvals_total` and `rejections_total` are grouped by review "
            "decision month.",
            "- `pending_total` is a month-end backlog stock metric, not a count "
            "of pending requests submitted during the month.",
            "- Team and department attribution uses the current-state user directory.",
        ]
    )


def render_tool_adoption_overview(
    metadata: dict[str, Any],
    adoption_summary: dict[str, Any],
    top_tools_df: pd.DataFrame,
    top_teams_df: pd.DataFrame,
) -> str:
    """Render the Tool Adoption Overview section."""
    adoption_summary_df = pd.DataFrame(
        [
            {
                "Metric": "Latest reporting month",
                "Value": format_date(metadata["latest_reporting_month"]),
            },
            {
                "Metric": "Approved users summed across latest month team-tool rows",
                "Value": format_int(adoption_summary["latest_approved_users_total"]),
            },
            {
                "Metric": "Active users summed across latest month team-tool rows",
                "Value": format_int(adoption_summary["latest_active_users_total"]),
            },
            {
                "Metric": "Total sessions",
                "Value": format_int(adoption_summary["total_sessions"]),
            },
            {
                "Metric": "Total prompts",
                "Value": format_int(adoption_summary["total_prompts"]),
            },
            {
                "Metric": "Total spend",
                "Value": format_usd(adoption_summary["total_spend_usd"]),
            },
            {
                "Metric": "Average row-level cost per active user-month",
                "Value": format_usd(adoption_summary["avg_cost_per_active_user"]),
            },
            {
                "Metric": "Maximum row-level cost per active user-month",
                "Value": format_usd(adoption_summary["max_cost_per_active_user"]),
            },
        ]
    )

    top_tools_display = add_rank_column(
        top_tools_df.rename(
            columns={
                "tool_code": "Tool code",
                "tool_name": "Tool",
                "vendor_name": "Vendor",
                "risk_tier": "Risk tier",
                "latest_approved_users_total": "Latest approved users",
                "active_users_total": "Active user-months",
                "total_sessions": "Sessions",
                "total_prompts": "Prompts",
            }
        )
    )

    top_teams_display = add_rank_column(
        top_teams_df.rename(
            columns={
                "team_name": "Team",
                "department_name": "Department",
                "latest_approved_users_total": "Latest approved users",
                "active_users_total": "Active user-months",
                "total_sessions": "Sessions",
                "total_prompts": "Prompts",
            }
        )
    )

    return "\n".join(
        [
            "## 3. Tool Adoption Overview",
            "",
            "Source mart: `tool_adoption_monthly`",
            "",
            "This section summarizes approved-access stock, monthly active usage, "
            "and usage volume by reporting month, team, and tool.",
            "",
            "### Adoption summary",
            "",
            dataframe_to_markdown(adoption_summary_df),
            "",
            "### Top tools by active user-month total",
            "",
            dataframe_to_markdown(
                top_tools_display,
                column_formatters={
                    "Rank": format_int,
                    "Latest approved users": format_int,
                    "Active users summed": format_int,
                    "Sessions": format_int,
                    "Prompts": format_int,
                },
            ),
            "",
            "### Top teams by active user-month total",
            "",
            dataframe_to_markdown(
                top_teams_display,
                column_formatters={
                    "Rank": format_int,
                    "Latest approved users": format_int,
                    "Active users summed": format_int,
                    "Sessions": format_int,
                    "Prompts": format_int,
                },
            ),
            "",
            "### Adoption notes",
            "",
            "- `approved_users_total` is a month-end stock metric.",
            "- `active_users_total`, `total_sessions`, and `total_prompts` are "
            "monthly flow metrics.",
            "- `Active user-months` are summed monthly active-user counts across reporting month, "
            "team, and tool rows; they should not be read as global distinct user counts.",
            "- Adoption in this project means approved tool access becoming "
            "observable as team-level usage.",
            "- Adoption does not directly measure productivity, user satisfaction, "
            "feature proficiency, or cost savings.",
        ]
    )


def render_spend_overview(
    spend_summary: dict[str, Any],
    top_tools_df: pd.DataFrame,
    top_teams_df: pd.DataFrame,
) -> str:
    """Render the Spend Overview section."""
    spend_summary_df = pd.DataFrame(
        [
            {
                "Metric": "Total spend",
                "Value": format_usd(spend_summary["total_spend_usd"]),
            },
            {
                "Metric": "Spend rows",
                "Value": format_int(spend_summary["spend_row_count"]),
            },
            {
                "Metric": "Rows with usage and spend",
                "Value": format_int(spend_summary["rows_with_usage_and_spend"]),
            },
            {
                "Metric": "Rows with spend but no usage",
                "Value": format_int(spend_summary["rows_with_spend_without_usage"]),
            },
            {
                "Metric": "Rows with usage but no spend",
                "Value": format_int(spend_summary["rows_with_usage_without_spend"]),
            },
            {
                "Metric": "Average row-level cost per active user-month",
                "Value": format_usd(spend_summary["avg_cost_per_active_user"]),
            },
            {
                "Metric": "Maximum row-level cost per active user-month",
                "Value": format_usd(spend_summary["max_cost_per_active_user"]),
            },
        ]
    )

    top_tools_display = add_rank_column(
        top_tools_df.rename(
            columns={
                "tool_code": "Tool code",
                "tool_name": "Tool",
                "vendor_name": "Vendor",
                "risk_tier": "Risk tier",
                "spend_usd": "Spend",
                "active_user_months": "Active user-months",
                "cost_per_active_user_month": "Cost per active user-month",
            }
        )
    )

    top_teams_display = add_rank_column(
        top_teams_df.rename(
            columns={
                "team_name": "Team",
                "department_name": "Department",
                "spend_usd": "Spend",
                "active_user_months": "Active user-months",
                "cost_per_active_user_month": "Cost per active user-month",
            }
        )
    )

    return "\n".join(
        [
            "## 4. Spend Overview",
            "",
            "Source mart: `tool_adoption_monthly`",
            "",
            "This section summarizes monthly team-tool spend and "
            "cost-per-active-user-month signals.",
            "",
            "### Spend summary",
            "",
            dataframe_to_markdown(spend_summary_df),
            "",
            "### Top tools by spend",
            "",
            dataframe_to_markdown(
                top_tools_display,
                column_formatters={
                    "Rank": format_int,
                    "Spend": format_usd,
                    "Active user-months": format_int,
                    "Cost per active user-month": format_usd,
                },
            ),
            "",
            "### Top teams by spend",
            "",
            dataframe_to_markdown(
                top_teams_display,
                column_formatters={
                    "Rank": format_int,
                    "Spend": format_usd,
                    "Active user-months": format_int,
                    "Cost per active user-month": format_usd,
                },
            ),
            "",
            "### Spend interpretation notes",
            "",
            "- Spend is modeled at monthly team-tool grain.",
            "- A null `spend_usd` value in mart outputs means no billing row "
            "joined to the reporting spine.",
            "- Null spend should not be automatically interpreted as zero spend.",
            "- `Active user-months` are summed monthly active-user counts across "
            "reporting month, team, and tool rows.",
            "- `Cost per active user-month` in the top spend tables is computed as "
            "total spend divided by active user-months for the grouped tool or team.",
            "- Spend-usage mismatches are review candidates, not confirmed billing "
            "errors.",
        ]
    )


def render_review_candidates(
    review_status_summary_df: pd.DataFrame,
    review_owner_summary_df: pd.DataFrame,
    top_high_priority_df: pd.DataFrame,
) -> str:
    """Render the Review Candidates section."""
    review_status_display = review_status_summary_df.rename(
        columns={
            "review_status": "Review status",
            "rows_total": "Rows",
            "high_priority_rows": "High priority",
            "medium_priority_rows": "Medium priority",
            "low_priority_rows": "Low priority",
        }
    )

    review_owner_display = review_owner_summary_df.rename(
        columns={
            "review_owner_hint": "Review owner hint",
            "rows_total": "Rows",
            "high_priority_rows": "High priority",
            "non_aligned_rows": "Non-aligned rows",
        }
    )

    top_high_priority_display = top_high_priority_df.rename(
        columns={
            "reporting_month": "Reporting month",
            "team_name": "Team",
            "department_name": "Department",
            "tool_code": "Tool code",
            "tool_name": "Tool",
            "vendor_name": "Vendor",
            "risk_tier": "Risk tier",
            "approved_users_total": "Approved users",
            "active_users_total": "Active user-months",
            "total_sessions": "Sessions",
            "total_prompts": "Prompts",
            "spend_usd": "Spend",
            "cost_per_active_user": "Cost per active user",
            "review_status": "Review status",
            "review_owner_hint": "Owner hint",
            "review_priority": "Priority",
        }
    )

    top_high_priority_columns = [
        "Reporting month",
        "Team",
        "Tool",
        "Vendor",
        "Risk tier",
        "Review status",
        "Owner hint",
        "Priority",
        "Approved users",
        "Active user-months",
        "Sessions",
        "Prompts",
        "Spend",
        "Cost per active user",
    ]

    top_high_priority_display = cast(
        pd.DataFrame,
        top_high_priority_display.loc[:, top_high_priority_columns].copy(),
    )

    review_status_definitions_df = pd.DataFrame(
        [
            {
                "Review status": "governance_review_usage_without_approval",
                "Meaning": "Usage exists, but approved access is not present.",
            },
            {
                "Review status": "finance_review_active_without_billing",
                "Meaning": "Usage and approved access exist, but no billing row is present.",
            },
            {
                "Review status": "cost_review_billed_without_usage",
                "Meaning": "Billing exists, but usage is not present.",
            },
            {
                "Review status": "adoption_review_approved_not_used",
                "Meaning": "Approved access exists, but usage and spend are not present.",
            },
            {
                "Review status": "aligned",
                "Meaning": "No review condition was classified by the current mart logic.",
            },
        ]
    )

    return "\n".join(
        [
            "## 5. Review Candidates",
            "",
            "Source mart: `adoption_review_candidates_monthly`",
            "",
            "This section summarizes monthly review candidates derived from "
            "approval, usage, and spend alignment signals.",
            "",
            "### Review candidate summary",
            "",
            dataframe_to_markdown(
                review_status_display,
                column_formatters={
                    "Rows": format_int,
                    "High priority": format_int,
                    "Medium priority": format_int,
                    "Low priority": format_int,
                },
            ),
            "",
            "### Review candidates by owner hint",
            "",
            dataframe_to_markdown(
                review_owner_display,
                column_formatters={
                    "Rows": format_int,
                    "High priority": format_int,
                    "Non-aligned rows": format_int,
                },
            ),
            "",
            "### Top high-priority review candidates",
            "",
            dataframe_to_markdown(
                top_high_priority_display,
                column_formatters={
                    "Reporting month": format_date,
                    "Approved users": format_int,
                    "Active user-months": format_int,
                    "Sessions": format_int,
                    "Prompts": format_int,
                    "Spend": format_usd,
                    "Cost per active user": format_usd,
                },
            ),
            "",
            "### Review status definitions",
            "",
            dataframe_to_markdown(review_status_definitions_df),
            "",
            "### Review candidate notes",
            "",
            "- `review_status`, `review_owner_hint`, and `review_priority` are "
            "defined in the mart layer.",
            "- The report script summarizes these fields but does not recompute "
            "their classification logic in Python.",
            "- `finance_review_active_without_billing` indicates usage and "
            "approved access with no joined billing row.",
            "- `cost_review_billed_without_usage` indicates a billing row with no "
            "monthly active usage in the same reporting row.",
            "- `review_owner_hint` is a likely routing surface, not a workflow "
            "assignment.",
            "- `review_priority` is a triage signal, not a policy enforcement action.",
            "- Business review candidates are expected analytical outputs, not dbt "
            "test failures.",
        ]
    )


def render_current_governance_exceptions(
    exception_summary: dict[str, Any],
    exception_by_team_df: pd.DataFrame,
    exception_by_tool_df: pd.DataFrame,
    used_without_approval_sample_df: pd.DataFrame,
) -> str:
    """Render the Current Governance Exceptions section."""
    exception_summary_df = pd.DataFrame(
        [
            {
                "Metric": "User-tool rows in current exception surface",
                "Value": format_int(
                    exception_summary["current_exception_surface_rows"]
                ),
            },
            {
                "Metric": "Rows with approved access",
                "Value": format_int(exception_summary["approved_rows"]),
            },
            {
                "Metric": "Rows with recent 30-day usage",
                "Value": format_int(exception_summary["recent_usage_rows"]),
            },
            {
                "Metric": "Used without approval",
                "Value": format_int(exception_summary["used_without_approval_rows"]),
            },
            {
                "Metric": "Approved but inactive",
                "Value": format_int(exception_summary["approved_but_inactive_rows"]),
            },
        ]
    )

    exception_by_team_display = exception_by_team_df.rename(
        columns={
            "team_name": "Team",
            "department_name": "Department",
            "used_without_approval_rows": "Used without approval",
            "approved_but_inactive_rows": "Approved but inactive",
        }
    )

    exception_by_tool_display = exception_by_tool_df.rename(
        columns={
            "tool_code": "Tool code",
            "tool_name": "Tool",
            "vendor_name": "Vendor",
            "risk_tier": "Risk tier",
            "used_without_approval_rows": "Used without approval",
            "approved_but_inactive_rows": "Approved but inactive",
        }
    )

    sample_display = used_without_approval_sample_df.rename(
        columns={
            "user_id": "User ID",
            "user_name": "User",
            "user_email": "User email",
            "team_name": "Team",
            "department_name": "Department",
            "tool_code": "Tool code",
            "tool_name": "Tool",
            "vendor_name": "Vendor",
            "risk_tier": "Risk tier",
            "has_approved_request_flag": "Approved?",
            "has_recent_usage_30d_flag": "Recent usage?",
            "used_without_approval_flag": "Used without approval?",
            "approved_but_inactive_flag": "Approved but inactive?",
        }
    )

    sample_columns: list[str] = [
        "User",
        "Team",
        "Tool",
        "Vendor",
        "Risk tier",
        "Approved?",
        "Recent usage?",
        "Used without approval?",
    ]

    sample_display = cast(
        pd.DataFrame,
        sample_display.loc[:, sample_columns].copy(),
    )

    return "\n".join(
        [
            "## 6. Current Governance Exceptions",
            "",
            "Source mart: `governance_exceptions_current`",
            "",
            "This section summarizes current user-tool exception states based "
            "on approved access and recent 30-day usage.",
            "",
            "### Current exception summary",
            "",
            dataframe_to_markdown(exception_summary_df),
            "",
            "### Exceptions by team",
            "",
            dataframe_to_markdown(
                exception_by_team_display,
                column_formatters={
                    "Used without approval": format_int,
                    "Approved but inactive": format_int,
                },
            ),
            "",
            "### Exceptions by tool",
            "",
            dataframe_to_markdown(
                exception_by_tool_display,
                column_formatters={
                    "Used without approval": format_int,
                    "Approved but inactive": format_int,
                },
            ),
            "",
            "### Sample used-without-approval rows",
            "",
            dataframe_to_markdown(
                sample_display,
                column_formatters={
                    "Approved?": format_bool,
                    "Recent usage?": format_bool,
                    "Used without approval?": format_bool,
                },
            ),
            "",
            "### Current exception notes",
            "",
            "- The current 30-day usage window is anchored to the maximum "
            "available `usage_date`, not the system clock.",
            "- `used_without_approval_flag` indicates recent usage without "
            "approved access.",
            "- `approved_but_inactive_flag` indicates approved access without "
            "recent 30-day usage.",
            "- These flags are summarized from the mart output and are not "
            "recomputed in Python.",
            "- These flags are review signals, not proof of policy violation.",
        ]
    )


def render_interpretation_notes() -> str:
    """Render fixed interpretation notes for the report."""
    return "\n".join(
        [
            "## 7. Interpretation Notes",
            "",
            "### 7.1 Current-state attribution",
            "",
            "Team and department grouping uses the current-state user directory. "
            "The report does not reconstruct historical organization membership.",
            "",
            "### 7.2 Approval persistence",
            "",
            "Access revocation is not modeled in v0.1.0. Once a user-tool pair "
            "has approved access, approved access is treated as persistent in "
            "downstream stock logic.",
            "",
            "### 7.3 Usage grain",
            "",
            "Usage is modeled at daily aggregated grain. The warehouse does not "
            "model individual usage events or prompt-level telemetry.",
            "",
            "### 7.4 Spend grain",
            "",
            "Spend is modeled at monthly team-tool grain. Spend rows represent "
            "billed combinations only.",
            "",
            "### 7.5 Adoption interpretation",
            "",
            "Tool adoption is treated as an operational proxy. In this project, "
            "adoption means that approved tool access becomes observable as "
            "team-level usage, with spend reviewed as supporting context.",
            "",
            "This report does not measure productivity improvement, feature "
            "proficiency, user satisfaction, or cost savings.",
            "",
            "### 7.6 Business review signals",
            "",
            "Business review candidates are valid analytical outputs. They should "
            "not be interpreted as dbt failures by themselves.",
            "",
            "The guiding distinction is:",
            "",
            "```text",
            "Business exceptions are outputs. Transformation inconsistencies are failures.",
            "```",
            "",
            "### 7.7 Mart grain and user-level interpretation",
            "",
            "`tool_adoption_monthly` is summarized at one row per reporting "
            "month, team, and tool. Summed approved-user or active-user counts "
            "across multiple tools or teams should be read as row-level "
            "aggregate counts, not as global distinct user counts.",
            "",
            "User-level interpretation should use a user-level mart, such as "
            "`governance_exceptions_current`, or a future monthly user-tool "
            "adoption mart.",
        ]
    )


def render_source_mart_references() -> str:
    """Render source mart references for the report."""
    source_marts_df = pd.DataFrame(
        [
            {
                "Mart": "`access_requests_monthly`",
                "Grain": "One row per reporting month, team, and tool",
                "Purpose": (
                    "Monthly request inflow, decision flow, and month-end backlog"
                ),
            },
            {
                "Mart": "`tool_adoption_monthly`",
                "Grain": "One row per reporting month, team, and tool",
                "Purpose": (
                    "Approved access stock, monthly usage, spend, and "
                    "cost-per-active-user"
                ),
            },
            {
                "Mart": "`adoption_review_candidates_monthly`",
                "Grain": "One row per reporting month, team, and tool",
                "Purpose": (
                    "Monthly approval, usage, and spend alignment review candidates"
                ),
            },
            {
                "Mart": "`governance_exceptions_current`",
                "Grain": "One row per user and tool",
                "Purpose": (
                    "Current approved-access versus recent-usage exception surface"
                ),
            },
        ]
    )

    return "\n".join(
        [
            "## 8. Source Mart References",
            "",
            "This report is generated from the following mart models.",
            "",
            dataframe_to_markdown(source_marts_df),
            "",
            "Related documentation:",
            "",
            "- `docs/domain-modeling-and-assumptions.md`",
            "- `docs/testing-strategy.md`",
            "- `models/marts/governance/schema.yml`",
            "",
            "Generated artifact:",
            "",
            "- `artifacts/reports/governance_report_v0_1_0.md`",
            "",
            "Generation command:",
            "",
            "```bash",
            "uv run python scripts/build_governance_report.py",
            "```",
        ]
    )


def build_report(connection: duckdb.DuckDBPyConnection) -> str:
    """Build the governance report Markdown."""
    validate_required_mart_tables(connection)

    metadata = fetch_one(connection, QUERY_REPORTING_METADATA)

    request_summary = fetch_one(
        connection,
        QUERY_EXECUTIVE_REQUEST_SUMMARY,
    )
    adoption_summary = fetch_one(
        connection,
        QUERY_EXECUTIVE_ADOPTION_SUMMARY,
    )
    review_candidate_summary = fetch_one(
        connection,
        QUERY_EXECUTIVE_REVIEW_CANDIDATE_SUMMARY,
    )
    executive_exception_summary = fetch_one(
        connection,
        QUERY_EXECUTIVE_CURRENT_EXCEPTION_SUMMARY,
    )

    monthly_trend_df = fetch_dataframe(
        connection,
        QUERY_REQUEST_MONTHLY_TREND,
    )
    request_top_teams_df = fetch_dataframe(
        connection,
        QUERY_REQUEST_TOP_TEAMS,
    )
    request_top_tools_df = fetch_dataframe(
        connection,
        QUERY_REQUEST_TOP_TOOLS,
    )

    adoption_top_tools_df = fetch_dataframe(
        connection,
        QUERY_ADOPTION_TOP_TOOLS,
    )
    adoption_top_teams_df = fetch_dataframe(
        connection,
        QUERY_ADOPTION_TOP_TEAMS,
    )

    spend_summary = fetch_one(
        connection,
        QUERY_SPEND_SUMMARY,
    )
    spend_top_tools_df = fetch_dataframe(
        connection,
        QUERY_SPEND_TOP_TOOLS,
    )
    spend_top_teams_df = fetch_dataframe(
        connection,
        QUERY_SPEND_TOP_TEAMS,
    )

    review_status_summary_df = fetch_dataframe(
        connection,
        QUERY_REVIEW_STATUS_SUMMARY,
    )
    review_owner_summary_df = fetch_dataframe(
        connection,
        QUERY_REVIEW_OWNER_SUMMARY,
    )
    review_top_high_priority_df = fetch_dataframe(
        connection,
        QUERY_REVIEW_TOP_HIGH_PRIORITY,
    )

    current_exception_summary = fetch_one(
        connection,
        QUERY_CURRENT_EXCEPTION_SECTION_SUMMARY,
    )
    exception_by_team_df = fetch_dataframe(
        connection,
        QUERY_EXCEPTION_BY_TEAM,
    )
    exception_by_tool_df = fetch_dataframe(
        connection,
        QUERY_EXCEPTION_BY_TOOL,
    )
    exception_sample_df = fetch_dataframe(
        connection,
        QUERY_EXCEPTION_SAMPLE_USED_WITHOUT_APPROVAL,
    )

    sections = [
        render_title(metadata),
        render_executive_summary(
            metadata=metadata,
            request_summary=request_summary,
            adoption_summary=adoption_summary,
            review_candidate_summary=review_candidate_summary,
            exception_summary=executive_exception_summary,
        ),
        render_request_trends(
            request_summary=request_summary,
            monthly_trend_df=monthly_trend_df,
            top_teams_df=request_top_teams_df,
            top_tools_df=request_top_tools_df,
        ),
        render_tool_adoption_overview(
            metadata=metadata,
            adoption_summary=adoption_summary,
            top_tools_df=adoption_top_tools_df,
            top_teams_df=adoption_top_teams_df,
        ),
        render_spend_overview(
            spend_summary=spend_summary,
            top_tools_df=spend_top_tools_df,
            top_teams_df=spend_top_teams_df,
        ),
        render_review_candidates(
            review_status_summary_df=review_status_summary_df,
            review_owner_summary_df=review_owner_summary_df,
            top_high_priority_df=review_top_high_priority_df,
        ),
        render_current_governance_exceptions(
            exception_summary=current_exception_summary,
            exception_by_team_df=exception_by_team_df,
            exception_by_tool_df=exception_by_tool_df,
            used_without_approval_sample_df=exception_sample_df,
        ),
        render_interpretation_notes(),
        render_source_mart_references(),
    ]

    return "\n\n".join(sections).rstrip() + "\n"


def write_report(report_markdown: str) -> None:
    """Write the generated report Markdown to the artifact path."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_markdown, encoding="utf-8")


def main() -> None:
    """Generate the governance report artifact."""
    with connect_warehouse() as connection:
        report_markdown = build_report(connection)

    write_report(report_markdown)
    print(f"Governance report generated: {REPORT_PATH}")


if __name__ == "__main__":
    main()
