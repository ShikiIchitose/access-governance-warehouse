WITH

raw_tool_spend_monthly AS (
    SELECT
        billing_month,
        team_name,
        department_name,
        tool_code,
        licensed_seats,
        fixed_license_cost_usd,
        variable_usage_cost_usd,
        spend_usd
    FROM {{ source('access_governance', 'raw_tool_spend_monthly') }}
),

normalized AS (
    SELECT
        billing_month,
        trim(team_name) AS team_name,
        trim(department_name) AS department_name,
        trim(tool_code) AS tool_code,
        licensed_seats,
        fixed_license_cost_usd,
        variable_usage_cost_usd,
        spend_usd
    FROM raw_tool_spend_monthly
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
    FROM normalized
)

SELECT * FROM final
