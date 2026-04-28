WITH

monthly_counts AS (
    SELECT
        reporting_month,
        count(*) AS approved_user_tool_total
    FROM {{ ref('int_user_tool_approved_as_of_month_end') }}
    GROUP BY reporting_month
),

with_previous AS (
    SELECT
        reporting_month,
        approved_user_tool_total,
        lag(approved_user_tool_total) OVER (
            ORDER BY reporting_month
        ) AS previous_approved_user_tool_total
    FROM monthly_counts
)

SELECT
    reporting_month,
    approved_user_tool_total,
    previous_approved_user_tool_total
FROM with_previous
WHERE
    previous_approved_user_tool_total IS NOT null
    AND approved_user_tool_total < previous_approved_user_tool_total
