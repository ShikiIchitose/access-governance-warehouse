WITH

access_requests AS (
    SELECT
        request_id,
        requester_user_id,
        tool_code,
        reviewed_at_utc,
        is_approved
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

approved_grouped_to_user_tool AS (
    SELECT
        requester_user_id AS user_id,
        tool_code,
        min(reviewed_at_utc) AS first_approved_at
    FROM approved_requests
    GROUP BY
        requester_user_id,
        tool_code
),

final AS (
    SELECT
        user_id,
        tool_code,
        first_approved_at,
        true AS has_approved_request_flag
    FROM approved_grouped_to_user_tool
)

SELECT * FROM final
