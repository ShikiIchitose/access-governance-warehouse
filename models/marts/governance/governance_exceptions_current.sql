WITH

approved_current AS (
    SELECT
        user_id,
        tool_code,
        first_approved_at,
        has_approved_request_flag
    FROM {{ ref('int_user_tool_approved_current') }}
),

recent_usage_30d AS (
    SELECT
        user_id,
        tool_code,
        window_start_date,
        window_end_date,
        last_usage_date,
        recent_30d_sessions_total,
        recent_30d_prompts_total,
        has_recent_usage_30d_flag
    FROM {{ ref('int_user_tool_recent_usage_30d') }}
),

users AS (
    SELECT
        user_id,
        user_name,
        user_email,
        team_name,
        department_name
    FROM {{ ref('dim_user') }}
),

tools AS (
    SELECT
        tool_code,
        tool_name,
        vendor_name,
        risk_tier
    FROM {{ ref('dim_tool') }}
),

user_tool_spine AS (
    SELECT
        user_id,
        tool_code
    FROM approved_current

    UNION DISTINCT

    SELECT
        user_id,
        tool_code
    FROM recent_usage_30d
),

user_tool_states AS (
    SELECT
        user_tool_spine.user_id,
        user_tool_spine.tool_code,
        coalesce(
            approved_current.has_approved_request_flag,
            false
        ) AS has_approved_request_flag,
        coalesce(
            recent_usage_30d.has_recent_usage_30d_flag,
            false
        ) AS has_recent_usage_30d_flag
    FROM user_tool_spine
    LEFT JOIN approved_current
        ON
            user_tool_spine.user_id = approved_current.user_id
            AND user_tool_spine.tool_code = approved_current.tool_code
    LEFT JOIN recent_usage_30d
        ON
            user_tool_spine.user_id = recent_usage_30d.user_id
            AND user_tool_spine.tool_code = recent_usage_30d.tool_code
),

exception_flags AS (
    SELECT
        user_id,
        tool_code,
        has_approved_request_flag,
        has_recent_usage_30d_flag,
        (
            has_recent_usage_30d_flag
            AND NOT has_approved_request_flag
        ) AS used_without_approval_flag,
        (
            has_approved_request_flag
            AND NOT has_recent_usage_30d_flag
        ) AS approved_but_inactive_flag
    FROM user_tool_states
),

final AS (
    SELECT
        exception_flags.user_id,
        users.user_name,
        users.user_email,
        users.team_name,
        users.department_name,
        exception_flags.tool_code,
        tools.tool_name,
        tools.vendor_name,
        tools.risk_tier,
        exception_flags.has_approved_request_flag,
        exception_flags.has_recent_usage_30d_flag,
        exception_flags.used_without_approval_flag,
        exception_flags.approved_but_inactive_flag
    FROM exception_flags
    LEFT JOIN users
        ON exception_flags.user_id = users.user_id
    LEFT JOIN tools
        ON exception_flags.tool_code = tools.tool_code
)

SELECT
    user_id,
    user_name,
    user_email,
    team_name,
    department_name,
    tool_code,
    tool_name,
    vendor_name,
    risk_tier,
    has_approved_request_flag,
    has_recent_usage_30d_flag,
    used_without_approval_flag,
    approved_but_inactive_flag
FROM final
ORDER BY
    team_name,
    user_id,
    tool_code
