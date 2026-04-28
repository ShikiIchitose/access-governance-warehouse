WITH

tool_spend_monthly AS (
    SELECT
        billing_month,
        team_name,
        department_name,
        tool_code,
        licensed_seats,
        fixed_license_cost_usd,
        variable_usage_cost_usd,
        spend_usd
    FROM {{ ref('stg_access_governance__tool_spend_monthly') }}
),

final AS (
    SELECT
        billing_month,
        team_name,
        department_name,
        tool_code,
        licensed_seats,
        fixed_license_cost_usd,
        variable_usage_cost_usd,
        spend_usd
    FROM tool_spend_monthly
)

SELECT * FROM final
