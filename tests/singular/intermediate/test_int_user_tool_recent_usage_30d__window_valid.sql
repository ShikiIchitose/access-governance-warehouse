SELECT
    user_id,
    tool_code,
    window_start_date,
    window_end_date,
    last_usage_date
FROM {{ ref('int_user_tool_recent_usage_30d') }}
WHERE
    window_start_date != window_end_date - INTERVAL 29 DAY
    OR last_usage_date < window_start_date
    OR last_usage_date > window_end_date
