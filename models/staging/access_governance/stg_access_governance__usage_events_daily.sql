WITH

raw_usage_events_daily AS (
    SELECT
        usage_date,
        user_id,
        tool_code,
        session_count,
        prompt_count,
        input_tokens_total,
        output_tokens_total
    FROM {{ source('access_governance', 'raw_usage_events_daily') }}
),

normalized AS (
    SELECT
        usage_date,
        trim(user_id) AS user_id,
        trim(tool_code) AS tool_code,
        session_count,
        prompt_count,
        input_tokens_total,
        output_tokens_total,
        (session_count > 0 OR prompt_count > 0) AS has_usage_activity
    FROM raw_usage_events_daily
),

final AS (
    SELECT
        usage_date,
        user_id,
        tool_code,
        session_count,
        prompt_count,
        input_tokens_total,
        output_tokens_total,
        has_usage_activity
    FROM normalized
)

SELECT * FROM final
