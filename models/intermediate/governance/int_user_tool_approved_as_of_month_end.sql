WITH

access_requests AS (
    SELECT
        request_id,
        requester_user_id,
        tool_code,
        reviewed_at_utc,
        is_approved,
        requested_month
    FROM {{ ref('fct_access_request') }}
),

approved_requests AS (
    SELECT
        request_id,
        requester_user_id,
        tool_code,
        reviewed_at_utc
    FROM access_requests
    WHERE is_approved = true
),

reporting_months AS (
    SELECT DISTINCT
        requested_month AS reporting_month,
        {{ month_end_timestamp('requested_month') }} AS month_end
    FROM access_requests
),

approved_requests_grouped_to_user_tool AS (
    SELECT
        requester_user_id AS user_id,
        tool_code,
        min(reviewed_at_utc) AS first_approved_at
    FROM approved_requests
    GROUP BY
        requester_user_id,
        tool_code
),

approved_user_tools_crossed_to_reporting_months AS (
    SELECT
        reporting_months.reporting_month,
        reporting_months.month_end,
        approved_requests_grouped_to_user_tool.user_id,
        approved_requests_grouped_to_user_tool.tool_code,
        approved_requests_grouped_to_user_tool.first_approved_at
    FROM approved_requests_grouped_to_user_tool
    CROSS JOIN reporting_months
    WHERE
        reporting_months.month_end
        >= approved_requests_grouped_to_user_tool.first_approved_at
),

approved_as_of_month_end AS (
    SELECT
        reporting_month,
        user_id,
        tool_code,
        first_approved_at,
        true AS has_approved_request_as_of_month_end_flag
    FROM approved_user_tools_crossed_to_reporting_months
),

final AS (
    SELECT
        reporting_month,
        user_id,
        tool_code,
        first_approved_at,
        has_approved_request_as_of_month_end_flag
    FROM approved_as_of_month_end
)

SELECT * FROM final
