SELECT
    user_id,
    tool_code,
    count(*) AS row_count
FROM {{ ref('int_user_tool_recent_usage_30d') }}
GROUP BY
    user_id,
    tool_code
HAVING count(*) > 1
