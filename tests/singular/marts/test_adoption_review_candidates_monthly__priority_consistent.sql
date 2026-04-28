SELECT
    reporting_month,
    team_name,
    tool_code,
    risk_tier,
    review_status,
    review_priority
FROM {{ ref('adoption_review_candidates_monthly') }}
WHERE
    review_priority != CASE
        WHEN
            review_status IN (
                'governance_review_usage_without_approval',
                'finance_review_active_without_billing'
            )
            AND risk_tier = 'high'
            THEN 'high'
        WHEN review_status != 'aligned'
            THEN 'medium'
        ELSE 'low'
    END
