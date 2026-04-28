SELECT
    reporting_month,
    team_name,
    tool_code,
    approval_present_flag,
    usage_present_flag,
    spend_present_flag,
    review_status
FROM {{ ref('adoption_review_candidates_monthly') }}
WHERE
    review_status != CASE
        WHEN
            usage_present_flag
            AND NOT approval_present_flag
            THEN 'governance_review_usage_without_approval'
        WHEN
            usage_present_flag
            AND approval_present_flag
            AND NOT spend_present_flag
            THEN 'finance_review_active_without_billing'
        WHEN
            spend_present_flag
            AND NOT usage_present_flag
            THEN 'cost_review_billed_without_usage'
        WHEN
            approval_present_flag
            AND NOT usage_present_flag
            AND NOT spend_present_flag
            THEN 'adoption_review_approved_not_used'
        ELSE 'aligned'
    END
