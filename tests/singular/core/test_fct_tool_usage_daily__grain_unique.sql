SELECT
    usage_date,
    user_id,
    tool_code,
    count(*) AS row_count
FROM {{ ref('fct_tool_usage_daily') }}
GROUP BY
    usage_date,
    user_id,
    tool_code
HAVING count(*) > 1
