SELECT
    reporting_month,
    team_name,
    tool_code,
    approved_users_total,
    active_users_total,
    spend_usd,
    approval_present_flag,
    usage_present_flag,
    spend_present_flag
FROM {{ ref('adoption_review_candidates_monthly') }}
WHERE
    approval_present_flag != (approved_users_total > 0)
    OR usage_present_flag != (active_users_total > 0)
    OR spend_present_flag != (spend_usd IS NOT null)
