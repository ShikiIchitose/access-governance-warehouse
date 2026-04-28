SELECT
    billing_month,
    team_name,
    tool_code,
    count(*) AS row_count
FROM {{ ref('fct_tool_spend_monthly') }}
GROUP BY
    billing_month,
    team_name,
    tool_code
HAVING count(*) > 1
