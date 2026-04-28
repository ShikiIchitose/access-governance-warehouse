WITH

raw_access_requests AS (
    SELECT
        request_id,
        requested_at,
        requester_user_id,
        tool_code,
        request_purpose,
        data_classification,
        business_justification_text,
        request_status,
        reviewed_at,
        reviewed_by_user_id,
        review_comment_text
    FROM {{ source('access_governance', 'raw_access_requests') }}
),

normalized AS (
    SELECT
        trim(request_id) AS request_id,

        requested_at,
        timezone('UTC', requested_at) AS requested_at_utc,
        cast(timezone('UTC', requested_at) AS DATE) AS requested_date_utc,

        trim(requester_user_id) AS requester_user_id,
        trim(tool_code) AS tool_code,
        lower(trim(request_purpose)) AS request_purpose,
        lower(trim(data_classification)) AS data_classification,
        trim(business_justification_text) AS business_justification_text,
        lower(trim(request_status)) AS request_status,

        reviewed_at,
        CASE
            WHEN reviewed_at IS NOT NULL THEN timezone('UTC', reviewed_at)
        END AS reviewed_at_utc,
        CASE
            WHEN reviewed_at IS NOT NULL THEN cast(timezone('UTC', reviewed_at) AS DATE)
        END AS reviewed_date_utc,

        CASE
            WHEN reviewed_by_user_id IS NOT NULL THEN trim(reviewed_by_user_id)
        END AS reviewed_by_user_id,

        CASE
            WHEN review_comment_text IS NOT NULL THEN trim(review_comment_text)
        END AS review_comment_text
    FROM raw_access_requests
),

derived_flags AS (
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

        (request_status = 'pending') AS is_pending,
        (request_status = 'approved') AS is_approved,
        (request_status = 'rejected') AS is_rejected,

        CASE
            WHEN request_status = 'approved' AND reviewed_at IS NOT NULL
                THEN epoch(reviewed_at - requested_at) / 3600.0
        END AS approval_lead_time_hours
    FROM normalized
),

final AS (
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
    FROM derived_flags
)

SELECT * FROM final
