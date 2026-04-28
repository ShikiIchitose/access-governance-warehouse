WITH

mart_totals AS (
    SELECT
        coalesce(sum(requests_total), 0) AS mart_requests_total,
        coalesce(sum(approvals_total), 0) AS mart_approvals_total,
        coalesce(sum(rejections_total), 0) AS mart_rejections_total
    FROM {{ ref('access_requests_monthly') }}
),

fact_totals AS (
    SELECT
        count(*) AS fact_requests_total,
        coalesce(
            sum(CASE WHEN is_approved THEN 1 ELSE 0 END),
            0
        ) AS fact_approvals_total,
        coalesce(
            sum(CASE WHEN is_rejected THEN 1 ELSE 0 END),
            0
        ) AS fact_rejections_total
    FROM {{ ref('fct_access_request') }}
)

SELECT
    mart_totals.mart_requests_total,
    fact_totals.fact_requests_total,
    mart_totals.mart_approvals_total,
    fact_totals.fact_approvals_total,
    mart_totals.mart_rejections_total,
    fact_totals.fact_rejections_total
FROM mart_totals
CROSS JOIN fact_totals
WHERE
    mart_totals.mart_requests_total != fact_totals.fact_requests_total
    OR mart_totals.mart_approvals_total != fact_totals.fact_approvals_total
    OR mart_totals.mart_rejections_total != fact_totals.fact_rejections_total
