SELECT
    reporting_month,
    request_id,
    count(*) AS row_count
FROM {{ ref('int_access_requests_open_at_month_end') }}
GROUP BY
    reporting_month,
    request_id
HAVING count(*) > 1
