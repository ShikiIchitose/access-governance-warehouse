WITH

approved_as_of AS (
    SELECT
        reporting_month,
        user_id,
        tool_code,
        first_approved_at,
        {{ month_end_timestamp('reporting_month') }} AS month_end
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
