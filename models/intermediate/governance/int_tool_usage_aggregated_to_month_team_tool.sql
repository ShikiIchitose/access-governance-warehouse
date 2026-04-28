WITH

usage_daily AS (
    SELECT
        usage_date,
        usage_month AS reporting_month,
        user_id,
        tool_code,
        session_count,
        prompt_count,
        input_tokens_total,
        output_tokens_total,
        has_usage_activity
    FROM {{ ref('fct_tool_usage_daily') }}
),

users AS (
    SELECT
        user_id,
        team_name,
        department_name
    FROM {{ ref('dim_user') }}
),

usage_joined_to_users AS (
    SELECT
        usage_daily.reporting_month,
        users.team_name,
        users.department_name,
        usage_daily.user_id,
        usage_daily.tool_code,
        usage_daily.session_count,
        usage_daily.prompt_count,
        usage_daily.input_tokens_total,
        usage_daily.output_tokens_total,
        usage_daily.has_usage_activity
    FROM usage_daily
    INNER JOIN users
        ON usage_daily.user_id = users.user_id
),

usage_aggregated_to_month_team_tool AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code,
        count(DISTINCT CASE
            WHEN has_usage_activity THEN user_id
        END) AS active_users_total,
        sum(session_count) AS total_sessions,
        sum(prompt_count) AS total_prompts,
        sum(input_tokens_total) AS input_tokens_total,
        sum(output_tokens_total) AS output_tokens_total
    FROM usage_joined_to_users
    GROUP BY
        reporting_month,
        team_name,
        department_name,
        tool_code
),

final AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code,
        active_users_total,
        total_sessions,
        total_prompts,
        input_tokens_total,
        output_tokens_total
    FROM usage_aggregated_to_month_team_tool
)

SELECT
    reporting_month,
    team_name,
    department_name,
    tool_code,
    active_users_total,
    total_sessions,
    total_prompts,
    input_tokens_total,
    output_tokens_total
FROM final
