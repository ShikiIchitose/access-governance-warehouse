SELECT
    reporting_month,
    team_name,
    tool_code,
    licensed_seats,
    approved_users_total,
    active_users_total,
    total_sessions,
    total_prompts,
    spend_usd,
    cost_per_active_user
FROM {{ ref('tool_adoption_monthly') }}
WHERE
    coalesce(licensed_seats, 0) < 0
    OR approved_users_total < 0
    OR active_users_total < 0
    OR total_sessions < 0
    OR total_prompts < 0
    OR coalesce(spend_usd, 0) < 0
    OR cost_per_active_user < 0
