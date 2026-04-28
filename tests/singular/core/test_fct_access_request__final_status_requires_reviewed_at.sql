SELECT
    request_id,
    request_status,
    requested_at,
    reviewed_at,
    reviewed_at_utc,
    reviewed_date_utc,
    reviewed_month,
    reviewed_by_user_id
FROM {{ ref('fct_access_request') }}
WHERE
    request_status IN ('approved', 'rejected')
    AND (
        reviewed_at IS null
        OR reviewed_at_utc IS null
        OR reviewed_date_utc IS null
        OR reviewed_month IS null
        OR reviewed_by_user_id IS null
    )
