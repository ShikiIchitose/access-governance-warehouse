WITH

usage_daily AS (
    SELECT
        usage_date,
        user_id,
        tool_code,
        session_count,
        prompt_count
    FROM {{ ref('fct_tool_usage_daily') }}
),

window_bounds AS (
    SELECT
        max(usage_date) AS window_end_date,
        cast(max(usage_date) - INTERVAL 29 DAY AS DATE) AS window_start_date
    FROM usage_daily
),

usage_in_window AS (
    SELECT
        usage_daily.usage_date,
        usage_daily.user_id,
        usage_daily.tool_code,
        usage_daily.session_count,
        usage_daily.prompt_count,
        window_bounds.window_start_date,
        window_bounds.window_end_date
    FROM usage_daily
    CROSS JOIN window_bounds
    WHERE
        usage_daily.usage_date BETWEEN
        window_bounds.window_start_date
        AND window_bounds.window_end_date
        AND (
            usage_daily.session_count > 0
            OR usage_daily.prompt_count > 0
        )
),

usage_grouped_to_user_tool AS (
    SELECT
        user_id,
        tool_code,
        window_start_date,
        window_end_date,
        max(usage_date) AS last_usage_date,
        sum(session_count) AS recent_30d_sessions_total,
        sum(prompt_count) AS recent_30d_prompts_total
    FROM usage_in_window
    GROUP BY
        user_id,
        tool_code,
        window_start_date,
        window_end_date
),

final AS (
    SELECT
        user_id,
        tool_code,
        window_start_date,
        window_end_date,
        last_usage_date,
        recent_30d_sessions_total,
        recent_30d_prompts_total,
        true AS has_recent_usage_30d_flag
    FROM usage_grouped_to_user_tool
)

SELECT * FROM final
