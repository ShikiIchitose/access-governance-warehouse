SELECT
    user_id,
    tool_code,
    has_approved_request_flag,
    has_recent_usage_30d_flag,
    used_without_approval_flag,
    approved_but_inactive_flag
FROM {{ ref('governance_exceptions_current') }}
WHERE
    used_without_approval_flag
    != (
        has_recent_usage_30d_flag
        AND NOT has_approved_request_flag
    )
    OR approved_but_inactive_flag
    != (
        has_approved_request_flag
        AND NOT has_recent_usage_30d_flag
    )
