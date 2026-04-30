WITH

access_requests AS (
    SELECT
        request_id,
        requested_at,
        requested_at_utc,
        requested_date_utc,
        requester_user_id,
        tool_code,
        request_purpose,
        data_classification,
        business_justification_text,
        request_status,
        reviewed_at,
        reviewed_at_utc,
        reviewed_date_utc,
        reviewed_by_user_id,
        review_comment_text,
        is_pending,
        is_approved,
        is_rejected,
        approval_lead_time_hours
    FROM {{ ref('stg_access_governance__access_requests') }}
),

enriched AS (
    SELECT
        request_id,
        requested_at,
        requested_at_utc,
        requested_date_utc,
        {{ month_start_date('requested_date_utc') }} AS requested_month,
        requester_user_id,
        tool_code,
        request_purpose,
        data_classification,
        business_justification_text,
        request_status,
        reviewed_at,
        reviewed_at_utc,
        reviewed_date_utc,
        CASE
            WHEN reviewed_date_utc IS NOT null
                THEN {{ month_start_date('reviewed_date_utc') }}
        END AS reviewed_month,
        reviewed_by_user_id,
        review_comment_text,
        is_pending,
        is_approved,
        is_rejected,
        approval_lead_time_hours
    FROM access_requests
),

final AS (
    SELECT
        request_id,
        requested_at,
        requested_at_utc,
        requested_date_utc,
        requested_month,
        requester_user_id,
        tool_code,
        request_purpose,
        data_classification,
        business_justification_text,
        request_status,
        reviewed_at,
        reviewed_at_utc,
        reviewed_date_utc,
        reviewed_month,
        reviewed_by_user_id,
        review_comment_text,
        is_pending,
        is_approved,
        is_rejected,
        approval_lead_time_hours
    FROM enriched
)

SELECT * FROM final
