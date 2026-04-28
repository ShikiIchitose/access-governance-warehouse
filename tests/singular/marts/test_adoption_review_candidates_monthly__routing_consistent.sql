SELECT
    reporting_month,
    team_name,
    tool_code,
    review_status,
    review_owner_hint
FROM {{ ref('adoption_review_candidates_monthly') }}
WHERE
    review_owner_hint != CASE
        WHEN review_status = 'governance_review_usage_without_approval'
            THEN 'access_governance'
        WHEN review_status = 'finance_review_active_without_billing'
            THEN 'finance_procurement'
        WHEN review_status = 'cost_review_billed_without_usage'
            THEN 'finance_procurement'
        WHEN review_status = 'adoption_review_approved_not_used'
            THEN 'team_manager_or_enablement'
        WHEN review_status = 'aligned'
            THEN 'none'
    END
