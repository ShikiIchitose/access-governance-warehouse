WITH

mart_totals AS (
    SELECT
        coalesce(sum(active_users_total), 0) AS mart_active_users_total,
        coalesce(sum(total_sessions), 0) AS mart_total_sessions,
        coalesce(sum(total_prompts), 0) AS mart_total_prompts
    FROM {{ ref('tool_adoption_monthly') }}
),

usage_totals AS (
    SELECT
        coalesce(sum(active_users_total), 0) AS usage_active_users_total,
        coalesce(sum(total_sessions), 0) AS usage_total_sessions,
        coalesce(sum(total_prompts), 0) AS usage_total_prompts
    FROM {{ ref('int_tool_usage_aggregated_to_month_team_tool') }}
)

SELECT
    mart_totals.mart_active_users_total,
    usage_totals.usage_active_users_total,
    mart_totals.mart_total_sessions,
    usage_totals.usage_total_sessions,
    mart_totals.mart_total_prompts,
    usage_totals.usage_total_prompts
FROM mart_totals
CROSS JOIN usage_totals
WHERE
    mart_totals.mart_active_users_total != usage_totals.usage_active_users_total
    OR mart_totals.mart_total_sessions != usage_totals.usage_total_sessions
    OR mart_totals.mart_total_prompts != usage_totals.usage_total_prompts
