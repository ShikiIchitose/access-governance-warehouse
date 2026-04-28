SELECT
    billing_month,
    team_name,
    tool_code,
    licensed_seats,
    fixed_license_cost_usd,
    variable_usage_cost_usd,
    spend_usd
FROM {{ ref('fct_tool_spend_monthly') }}
WHERE
    licensed_seats < 0
    OR fixed_license_cost_usd < 0
    OR variable_usage_cost_usd < 0
    OR spend_usd < 0
