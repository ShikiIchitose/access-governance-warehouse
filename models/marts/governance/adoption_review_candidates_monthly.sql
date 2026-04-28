WITH

tool_adoption AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code,
        tool_name,
        vendor_name,
        risk_tier,
        licensed_seats,
        approved_users_total,
        active_users_total,
        total_sessions,
        total_prompts,
        spend_usd,
        cost_per_active_user
    FROM {{ ref('tool_adoption_monthly') }}
),

alignment_flags AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code,
        tool_name,
        vendor_name,
        risk_tier,
        licensed_seats,
        approved_users_total,
        active_users_total,
        total_sessions,
        total_prompts,
        spend_usd,
        cost_per_active_user,
        approved_users_total > 0 AS approval_present_flag,
        active_users_total > 0 AS usage_present_flag,
        spend_usd IS NOT null AS spend_present_flag
    FROM tool_adoption
),

review_status_classified AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code,
        tool_name,
        vendor_name,
        risk_tier,
        licensed_seats,
        approved_users_total,
        active_users_total,
        total_sessions,
        total_prompts,
        spend_usd,
        cost_per_active_user,
        approval_present_flag,
        usage_present_flag,
        spend_present_flag,
        CASE
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
        END AS review_status
    FROM alignment_flags
),

review_routing AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code,
        tool_name,
        vendor_name,
        risk_tier,
        licensed_seats,
        approved_users_total,
        active_users_total,
        total_sessions,
        total_prompts,
        spend_usd,
        cost_per_active_user,
        approval_present_flag,
        usage_present_flag,
        spend_present_flag,
        review_status,
        CASE
            WHEN
                review_status
                = 'governance_review_usage_without_approval'
                THEN 'access_governance'
            WHEN
                review_status IN (
                    'finance_review_active_without_billing',
                    'cost_review_billed_without_usage'
                )
                THEN 'finance_procurement'
            WHEN
                review_status
                = 'adoption_review_approved_not_used'
                THEN 'team_manager_or_enablement'
            ELSE 'none'
        END AS review_owner_hint,
        CASE
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
        END AS review_priority
    FROM review_status_classified
),

final AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code,
        tool_name,
        vendor_name,
        risk_tier,
        licensed_seats,
        approved_users_total,
        active_users_total,
        total_sessions,
        total_prompts,
        spend_usd,
        cost_per_active_user,
        approval_present_flag,
        usage_present_flag,
        spend_present_flag,
        review_status,
        review_owner_hint,
        review_priority
    FROM review_routing
)

SELECT
    reporting_month,
    team_name,
    department_name,
    tool_code,
    tool_name,
    vendor_name,
    risk_tier,
    licensed_seats,
    approved_users_total,
    active_users_total,
    total_sessions,
    total_prompts,
    spend_usd,
    cost_per_active_user,
    approval_present_flag,
    usage_present_flag,
    spend_present_flag,
    review_status,
    review_owner_hint,
    review_priority
FROM final
ORDER BY
    reporting_month,
    team_name,
    tool_code
