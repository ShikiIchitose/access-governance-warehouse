WITH

mart_totals AS (
    SELECT coalesce(sum(approved_users_total), 0) AS mart_approved_users_total
    FROM {{ ref('tool_adoption_monthly') }}
),

approved_stock_totals AS (
    SELECT count(*) AS approved_user_tool_month_total
    FROM {{ ref('int_user_tool_approved_as_of_month_end') }}
)

SELECT
    mart_totals.mart_approved_users_total,
    approved_stock_totals.approved_user_tool_month_total
FROM mart_totals
CROSS JOIN approved_stock_totals
WHERE mart_totals.mart_approved_users_total != approved_stock_totals.approved_user_tool_month_total
