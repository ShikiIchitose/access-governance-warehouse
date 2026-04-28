SELECT
    reporting_month,
    user_id,
    tool_code,
    count(*) AS row_count
FROM {{ ref('int_user_tool_approved_as_of_month_end') }}
GROUP BY
    reporting_month,
    user_id,
    tool_code
HAVING count(*) > 1
