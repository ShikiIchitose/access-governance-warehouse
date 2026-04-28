SELECT
    billing_month,
    team_name,
    tool_code,
    fixed_license_cost_usd,
    variable_usage_cost_usd,
    spend_usd,
    fixed_license_cost_usd + variable_usage_cost_usd AS expected_spend_usd
FROM {{ ref('fct_tool_spend_monthly') }}
WHERE spend_usd != fixed_license_cost_usd + variable_usage_cost_usd
