SELECT
    usage_date,
    user_id,
    tool_code,
    session_count,
    prompt_count,
    input_tokens_total,
    output_tokens_total
FROM {{ ref('fct_tool_usage_daily') }}
WHERE
    session_count < 0
    OR prompt_count < 0
    OR input_tokens_total < 0
    OR output_tokens_total < 0
