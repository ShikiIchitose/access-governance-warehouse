WITH

approved_as_of AS (
    SELECT
        reporting_month,
        user_id,
        tool_code,
        first_approved_at,
        cast(
            date_trunc('month', reporting_month)
            + INTERVAL 1 MONTH
            - INTERVAL 1 SECOND
            AS TIMESTAMP
        ) AS month_end
    FROM {{ ref('int_user_tool_approved_as_of_month_end') }}
)

SELECT
    reporting_month,
    user_id,
    tool_code,
    first_approved_at,
    month_end
FROM approved_as_of
WHERE
    first_approved_at IS null
    OR first_approved_at > month_end
