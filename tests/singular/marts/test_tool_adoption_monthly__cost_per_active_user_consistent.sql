SELECT
    reporting_month,
    team_name,
    tool_code,
    active_users_total,
    spend_usd,
    cost_per_active_user
FROM {{ ref('tool_adoption_monthly') }}
WHERE
    (
        active_users_total = 0
        AND cost_per_active_user IS NOT null
    )
    OR (
        spend_usd IS null
        AND cost_per_active_user IS NOT null
    )
    OR (
        active_users_total > 0
        AND spend_usd IS NOT null
        AND cost_per_active_user IS null
    )
    OR (
        active_users_total > 0
        AND spend_usd IS NOT null
        AND cost_per_active_user != spend_usd / active_users_total
    )
