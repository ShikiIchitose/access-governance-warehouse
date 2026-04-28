SELECT
    user_id,
    tool_code,
    first_approved_at,
    has_approved_request_flag
FROM {{ ref('int_user_tool_approved_current') }}
WHERE
    first_approved_at IS null
    OR NOT has_approved_request_flag
