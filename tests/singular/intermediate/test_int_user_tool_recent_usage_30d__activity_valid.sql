SELECT
    user_id,
    tool_code,
    recent_30d_sessions_total,
    recent_30d_prompts_total,
    has_recent_usage_30d_flag
FROM {{ ref('int_user_tool_recent_usage_30d') }}
WHERE
    NOT has_recent_usage_30d_flag
    OR (
        recent_30d_sessions_total <= 0
        AND recent_30d_prompts_total <= 0
    )
