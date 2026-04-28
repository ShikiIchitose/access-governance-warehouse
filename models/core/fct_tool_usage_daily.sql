WITH

usage_daily AS (
    SELECT
        usage_date,
        user_id,
        tool_code,
        session_count,
        prompt_count,
        input_tokens_total,
        output_tokens_total,
        has_usage_activity
    FROM {{ ref('stg_access_governance__usage_events_daily') }}
),

enriched AS (
    SELECT
        usage_date,
        cast(date_trunc('month', usage_date) AS DATE) AS usage_month,
        user_id,
        tool_code,
        session_count,
        prompt_count,
        input_tokens_total,
        output_tokens_total,
        has_usage_activity
    FROM usage_daily
),

final AS (
    SELECT
        usage_date,
        usage_month,
        user_id,
        tool_code,
        session_count,
        prompt_count,
        input_tokens_total,
        output_tokens_total,
        has_usage_activity
    FROM enriched
)

SELECT * FROM final
