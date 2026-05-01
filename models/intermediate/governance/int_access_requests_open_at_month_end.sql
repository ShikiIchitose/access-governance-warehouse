WITH

access_requests AS (
    SELECT
        request_id,
        requester_user_id,
        tool_code,
        requested_at_utc AS requested_at,
        reviewed_at_utc AS reviewed_at,
        requested_month
    FROM {{ ref('fct_access_request') }}
),

reporting_months AS (
    SELECT DISTINCT
        requested_month AS reporting_month,
        {{ month_end_timestamp('requested_month') }} AS month_end
    FROM access_requests
),

requests_crossed_to_reporting_months AS (
    SELECT
        reporting_months.reporting_month,
        reporting_months.month_end,
        access_requests.request_id,
        access_requests.requester_user_id,
        access_requests.tool_code,
        access_requests.requested_at,
        access_requests.reviewed_at
    FROM access_requests
    CROSS JOIN reporting_months
    WHERE reporting_months.reporting_month >= access_requests.requested_month
),

open_requests_at_month_end AS (
    SELECT
        reporting_month,
        request_id,
        requester_user_id,
        tool_code,
        requested_at,
        reviewed_at
    FROM requests_crossed_to_reporting_months
    WHERE
        requested_at <= month_end
        AND (
            reviewed_at IS null
            OR reviewed_at > month_end
        )
),

final AS (
    SELECT
        reporting_month,
        request_id,
        requester_user_id,
        tool_code,
        requested_at,
        reviewed_at
    FROM open_requests_at_month_end
)

SELECT * FROM final
