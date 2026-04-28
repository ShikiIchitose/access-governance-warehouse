WITH

mart_backlog AS (
    SELECT coalesce(sum(pending_total), 0) AS mart_pending_total
    FROM {{ ref('access_requests_monthly') }}
),

intermediate_backlog AS (
    SELECT count(*) AS intermediate_open_request_total
    FROM {{ ref('int_access_requests_open_at_month_end') }}
)

SELECT
    mart_backlog.mart_pending_total,
    intermediate_backlog.intermediate_open_request_total
FROM mart_backlog
CROSS JOIN intermediate_backlog
WHERE mart_backlog.mart_pending_total != intermediate_backlog.intermediate_open_request_total
