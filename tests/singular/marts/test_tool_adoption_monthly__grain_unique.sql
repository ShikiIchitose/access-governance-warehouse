SELECT
    reporting_month,
    team_name,
    tool_code,
    count(*) AS row_count
FROM {{ ref('tool_adoption_monthly') }}
GROUP BY
    reporting_month,
    team_name,
    tool_code
HAVING count(*) > 1
