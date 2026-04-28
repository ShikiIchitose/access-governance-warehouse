SELECT
    reporting_month,
    team_name,
    tool_code,
    count(*) AS row_count
FROM {{ ref('int_tool_usage_aggregated_to_month_team_tool') }}
GROUP BY
    reporting_month,
    team_name,
    tool_code
HAVING count(*) > 1
