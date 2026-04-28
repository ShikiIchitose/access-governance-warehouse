WITH

access_requests AS (
    SELECT
        request_id,
        requested_month,
        requester_user_id,
        tool_code,
        request_status,
        reviewed_month,
        is_approved,
        is_rejected,
        approval_lead_time_hours
    FROM {{ ref('fct_access_request') }}
),

open_requests_at_month_end AS (
    SELECT
        reporting_month,
        request_id,
        requester_user_id,
        tool_code
    FROM {{ ref('int_access_requests_open_at_month_end') }}
),

users AS (
    SELECT
        user_id,
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

access_requests_joined_to_users AS (
    SELECT
        access_requests.request_id,
        access_requests.requested_month,
        access_requests.requester_user_id,
        users.team_name,
        users.department_name,
        access_requests.tool_code,
        access_requests.request_status,
        access_requests.reviewed_month,
        access_requests.is_approved,
        access_requests.is_rejected,
        access_requests.approval_lead_time_hours
    FROM access_requests
    LEFT JOIN users
        ON access_requests.requester_user_id = users.user_id
),

request_inflow_grouped AS (
    SELECT
        requested_month AS reporting_month,
        team_name,
        department_name,
        tool_code,
        count(*) AS requests_total
    FROM access_requests_joined_to_users
    GROUP BY
        requested_month,
        team_name,
        department_name,
        tool_code
),

decision_flow_grouped AS (
    SELECT
        reviewed_month AS reporting_month,
        team_name,
        department_name,
        tool_code,
        sum(CASE WHEN is_approved THEN 1 ELSE 0 END) AS approvals_total,
        sum(CASE WHEN is_rejected THEN 1 ELSE 0 END) AS rejections_total,
        avg(
            CASE
                WHEN is_approved THEN approval_lead_time_hours
            END
        ) AS avg_approval_lead_time_hours
    FROM access_requests_joined_to_users
    WHERE reviewed_month IS NOT null
    GROUP BY
        reviewed_month,
        team_name,
        department_name,
        tool_code
),

open_requests_joined_to_users AS (
    SELECT
        open_requests_at_month_end.reporting_month,
        open_requests_at_month_end.request_id,
        open_requests_at_month_end.requester_user_id,
        users.team_name,
        users.department_name,
        open_requests_at_month_end.tool_code
    FROM open_requests_at_month_end
    LEFT JOIN users
        ON open_requests_at_month_end.requester_user_id = users.user_id
),

backlog_grouped AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code,
        count(*) AS pending_total
    FROM open_requests_joined_to_users
    GROUP BY
        reporting_month,
        team_name,
        department_name,
        tool_code
),

reporting_spine AS (
    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code
    FROM request_inflow_grouped

    UNION

    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code
    FROM decision_flow_grouped

    UNION

    SELECT
        reporting_month,
        team_name,
        department_name,
        tool_code
    FROM backlog_grouped
),

final AS (
    SELECT
        reporting_spine.reporting_month,
        reporting_spine.team_name,
        reporting_spine.department_name,
        reporting_spine.tool_code,
        tools.tool_name,
        tools.vendor_name,
        tools.risk_tier,
        coalesce(request_inflow_grouped.requests_total, 0)
            AS requests_total,
        coalesce(decision_flow_grouped.approvals_total, 0)
            AS approvals_total,
        coalesce(decision_flow_grouped.rejections_total, 0)
            AS rejections_total,
        coalesce(backlog_grouped.pending_total, 0)
            AS pending_total,
        decision_flow_grouped.avg_approval_lead_time_hours
    FROM reporting_spine
    LEFT JOIN request_inflow_grouped
        ON
            reporting_spine.reporting_month
            = request_inflow_grouped.reporting_month
            AND reporting_spine.team_name
            = request_inflow_grouped.team_name
            AND reporting_spine.tool_code
            = request_inflow_grouped.tool_code
    LEFT JOIN decision_flow_grouped
        ON
            reporting_spine.reporting_month
            = decision_flow_grouped.reporting_month
            AND reporting_spine.team_name
            = decision_flow_grouped.team_name
            AND reporting_spine.tool_code
            = decision_flow_grouped.tool_code
    LEFT JOIN backlog_grouped
        ON
            reporting_spine.reporting_month
            = backlog_grouped.reporting_month
            AND reporting_spine.team_name
            = backlog_grouped.team_name
            AND reporting_spine.tool_code
            = backlog_grouped.tool_code
    LEFT JOIN tools
        ON reporting_spine.tool_code = tools.tool_code
)

SELECT
    reporting_month,
    team_name,
    department_name,
    tool_code,
    tool_name,
    vendor_name,
    risk_tier,
    requests_total,
    approvals_total,
    rejections_total,
    pending_total,
    avg_approval_lead_time_hours
FROM final
ORDER BY
    reporting_month,
    team_name,
    tool_code
