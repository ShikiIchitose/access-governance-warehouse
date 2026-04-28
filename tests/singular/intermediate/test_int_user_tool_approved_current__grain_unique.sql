SELECT
    user_id,
    tool_code,
    count(*) AS row_count
FROM {{ ref('int_user_tool_approved_current') }}
GROUP BY
    user_id,
    tool_code
HAVING count(*) > 1
