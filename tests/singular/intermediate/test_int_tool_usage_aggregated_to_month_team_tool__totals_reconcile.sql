WITH

source_usage_totals AS (
    SELECT
        sum(session_count) AS source_sessions_total,
        sum(prompt_count) AS source_prompts_total,
        sum(input_tokens_total) AS source_input_tokens_total,
        sum(output_tokens_total) AS source_output_tokens_total
    FROM {{ ref('fct_tool_usage_daily') }}
),

aggregated_usage_totals AS (
    SELECT
        sum(total_sessions) AS aggregated_sessions_total,
        sum(total_prompts) AS aggregated_prompts_total,
        sum(input_tokens_total) AS aggregated_input_tokens_total,
        sum(output_tokens_total) AS aggregated_output_tokens_total
    FROM {{ ref('int_tool_usage_aggregated_to_month_team_tool') }}
)

SELECT
    source_usage_totals.source_sessions_total,
    aggregated_usage_totals.aggregated_sessions_total,
    source_usage_totals.source_prompts_total,
    aggregated_usage_totals.aggregated_prompts_total,
    source_usage_totals.source_input_tokens_total,
    aggregated_usage_totals.aggregated_input_tokens_total,
    source_usage_totals.source_output_tokens_total,
    aggregated_usage_totals.aggregated_output_tokens_total
FROM source_usage_totals
CROSS JOIN aggregated_usage_totals
-- Both CTEs return exactly one aggregate row, so this CROSS JOIN
-- combines source totals and aggregated totals into a single comparison row.
WHERE
    source_usage_totals.source_sessions_total != aggregated_usage_totals.aggregated_sessions_total
    OR source_usage_totals.source_prompts_total != aggregated_usage_totals.aggregated_prompts_total
    OR source_usage_totals.source_input_tokens_total != aggregated_usage_totals.aggregated_input_tokens_total
    OR source_usage_totals.source_output_tokens_total != aggregated_usage_totals.aggregated_output_tokens_total
