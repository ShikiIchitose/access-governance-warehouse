WITH

open_requests AS (
    SELECT
        reporting_month,
        request_id,
        requested_at,
        reviewed_at,
        {{ month_end_timestamp('reporting_month') }} AS month_end
    FROM {{ ref('int_access_requests_open_at_month_end') }}
)

SELECT
    reporting_month,
    request_id,
    requested_at,
    reviewed_at,
    month_end
FROM open_requests
WHERE
    requested_at > month_end
    OR (
        reviewed_at IS NOT null
        AND reviewed_at <= month_end
    )
