WITH

mart_totals AS (
    SELECT
        count(*) FILTER (
            WHERE spend_usd IS NOT null
        ) AS mart_billed_rows,
        coalesce(sum(spend_usd), 0) AS mart_spend_usd
    FROM {{ ref('tool_adoption_monthly') }}
),

spend_totals AS (
    SELECT
        count(*) AS spend_billed_rows,
        coalesce(sum(spend_usd), 0) AS spend_spend_usd
    FROM {{ ref('fct_tool_spend_monthly') }}
)

SELECT
    mart_totals.mart_billed_rows,
    spend_totals.spend_billed_rows,
    mart_totals.mart_spend_usd,
    spend_totals.spend_spend_usd
FROM mart_totals
CROSS JOIN spend_totals
WHERE
    mart_totals.mart_billed_rows != spend_totals.spend_billed_rows
    OR mart_totals.mart_spend_usd != spend_totals.spend_spend_usd
