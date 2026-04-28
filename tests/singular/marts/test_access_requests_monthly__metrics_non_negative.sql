SELECT
    reporting_month,
    team_name,
    tool_code,
    requests_total,
    approvals_total,
    rejections_total,
    pending_total,
    avg_approval_lead_time_hours
FROM {{ ref('access_requests_monthly') }}
WHERE
    requests_total < 0
    OR approvals_total < 0
    OR rejections_total < 0
    OR pending_total < 0
    OR avg_approval_lead_time_hours < 0
