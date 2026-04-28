SELECT
    request_id,
    request_status,
    requested_at,
    reviewed_at,
    approval_lead_time_hours
FROM {{ ref('fct_access_request') }}
WHERE approval_lead_time_hours < 0
