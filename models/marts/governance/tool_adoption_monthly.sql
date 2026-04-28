WITH

usage_monthly AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code,
        active_users_total,
        total_sessions,
        total_prompts
    FROM {{ ref('int_tool_usage_aggregated_to_month_team_tool') }}
),

approved_user_tools_as_of_month_end AS (
    SELECT
        reporting_month,
        user_id,
        tool_code,
        has_approved_request_as_of_month_end_flag
    FROM {{ ref('int_user_tool_approved_as_of_month_end') }}
),

users AS (
    SELECT
        user_id,
        team_name,
        department_name
    FROM {{ ref('dim_user') }}
),

spend_monthly AS (
    SELECT
        billing_month AS reporting_month,
        team_name,
        department_name,
        tool_code,
        licensed_seats,
        spend_usd
    FROM {{ ref('fct_tool_spend_monthly') }}
),

tools AS (
    SELECT
        tool_code,
        tool_name,
        vendor_name,
        risk_tier
    FROM {{ ref('dim_tool') }}
),

approved_user_tools_joined_to_users AS (
    SELECT
        approved_user_tools_as_of_month_end.reporting_month,
        approved_user_tools_as_of_month_end.user_id,
        users.team_name,
        users.department_name,
        approved_user_tools_as_of_month_end.tool_code,
        approved_user_tools_as_of_month_end.has_approved_request_as_of_month_end_flag
    FROM approved_user_tools_as_of_month_end
    LEFT JOIN users
        ON approved_user_tools_as_of_month_end.user_id = users.user_id
),

approved_stock_grouped AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code,
        count(DISTINCT user_id) AS approved_users_total
    FROM approved_user_tools_joined_to_users
    WHERE has_approved_request_as_of_month_end_flag
    GROUP BY
        reporting_month,
        team_name,
        department_name,
        tool_code
),

reporting_spine AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code
    FROM usage_monthly

    UNION

    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code
    FROM spend_monthly

    UNION

    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code
    FROM approved_stock_grouped
),

final AS (
    SELECT
        reporting_spine.reporting_month,
        reporting_spine.team_name,
        reporting_spine.department_name,
        reporting_spine.tool_code,
        tools.tool_name,
        tools.vendor_name,
        tools.risk_tier,
        spend_monthly.licensed_seats,
        coalesce(approved_stock_grouped.approved_users_total, 0)
            AS approved_users_total,
        coalesce(usage_monthly.active_users_total, 0)
            AS active_users_total,
        coalesce(usage_monthly.total_sessions, 0)
            AS total_sessions,
        coalesce(usage_monthly.total_prompts, 0)
            AS total_prompts,
        spend_monthly.spend_usd,
        CASE
            WHEN
                coalesce(usage_monthly.active_users_total, 0) > 0
                AND spend_monthly.spend_usd IS NOT null
                THEN (
                    spend_monthly.spend_usd
                    / usage_monthly.active_users_total
                )
        END AS cost_per_active_user
    FROM reporting_spine
    LEFT JOIN usage_monthly
        ON
            reporting_spine.reporting_month
            = usage_monthly.reporting_month
            AND reporting_spine.team_name
            = usage_monthly.team_name
            AND reporting_spine.tool_code
            = usage_monthly.tool_code
    LEFT JOIN spend_monthly
        ON
            reporting_spine.reporting_month
            = spend_monthly.reporting_month
            AND reporting_spine.team_name
            = spend_monthly.team_name
            AND reporting_spine.tool_code
            = spend_monthly.tool_code
    LEFT JOIN approved_stock_grouped
        ON
            reporting_spine.reporting_month
            = approved_stock_grouped.reporting_month
            AND reporting_spine.team_name
            = approved_stock_grouped.team_name
            AND reporting_spine.tool_code
            = approved_stock_grouped.tool_code
    LEFT JOIN tools
        ON reporting_spine.tool_code = tools.tool_code
)

SELECT
    reporting_month,
    team_name,
    department_name,
    tool_code,
    tool_name,
    vendor_name,
    risk_tier,
    licensed_seats,
    approved_users_total,
    active_users_total,
    total_sessions,
    total_prompts,
    spend_usd,
    cost_per_active_user
FROM final
ORDER BY
    reporting_month,
    team_name,
    tool_code
