-- ============================================================
-- Quick inspection script for generated raw Parquet outputs
-- access-governance-warehouse / synthetic generator
-- Run example:
--   -f scripts/inspect_generated_raw_parquet.sql
-- ============================================================

-- --------------------------------
-- 0. Load Parquet files as temp views
-- --------------------------------
CREATE OR REPLACE TEMP VIEW raw_tool_catalog AS
SELECT
    tool_code,
    tool_name,
    vendor_name,
    tool_category,
    deployment_scope,
    risk_tier,
    is_active,
    homepage_url
FROM read_parquet('data/raw/raw_tool_catalog.parquet');

CREATE OR REPLACE TEMP VIEW raw_user_directory AS
SELECT
    user_id,
    user_name,
    user_email,
    team_name,
    department_name,
    job_level,
    employment_status
FROM read_parquet('data/raw/raw_user_directory.parquet');

CREATE OR REPLACE TEMP VIEW raw_access_requests AS
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
FROM read_parquet('data/raw/raw_access_requests.parquet');

CREATE OR REPLACE TEMP VIEW raw_usage_events_daily AS
SELECT
    usage_date,
    user_id,
    tool_code,
    session_count,
    prompt_count,
    input_tokens_total,
    output_tokens_total
FROM read_parquet('data/raw/raw_usage_events_daily.parquet');

CREATE OR REPLACE TEMP VIEW raw_tool_spend_monthly AS
SELECT
    billing_month,
    team_name,
    department_name,
    tool_code,
    licensed_seats,
    fixed_license_cost_usd,
    variable_usage_cost_usd,
    spend_usd
FROM read_parquet('data/raw/raw_tool_spend_monthly.parquet');

-- --------------------------------
-- 1. Row counts
-- --------------------------------
SELECT
    'raw_tool_catalog' AS table_name,
    count(*) AS row_count
FROM raw_tool_catalog

UNION ALL

SELECT
    'raw_user_directory' AS table_name,
    count(*) AS row_count
FROM raw_user_directory

UNION ALL

SELECT
    'raw_access_requests' AS table_name,
    count(*) AS row_count
FROM raw_access_requests

UNION ALL

SELECT
    'raw_usage_events_daily' AS table_name,
    count(*) AS row_count
FROM raw_usage_events_daily

UNION ALL

SELECT
    'raw_tool_spend_monthly' AS table_name,
    count(*) AS row_count
FROM raw_tool_spend_monthly
ORDER BY table_name;

-- --------------------------------
-- 2. Schema checks
-- --------------------------------
DESCRIBE raw_tool_catalog;
DESCRIBE raw_user_directory;
DESCRIBE raw_access_requests;
DESCRIBE raw_usage_events_daily;
DESCRIBE raw_tool_spend_monthly;

-- --------------------------------
-- 3. Summary statistics
-- --------------------------------
SUMMARIZE raw_tool_catalog;
SUMMARIZE raw_user_directory;
SUMMARIZE raw_access_requests;
SUMMARIZE raw_usage_events_daily;
SUMMARIZE raw_tool_spend_monthly;

-- --------------------------------
-- 4. Preview first rows
-- --------------------------------
SELECT
    tool_code,
    tool_name,
    vendor_name,
    tool_category,
    deployment_scope,
    risk_tier,
    is_active,
    homepage_url
FROM raw_tool_catalog
ORDER BY tool_code
LIMIT 10;

SELECT
    user_id,
    user_name,
    user_email,
    team_name,
    department_name,
    job_level,
    employment_status
FROM raw_user_directory
ORDER BY user_id
LIMIT 10;

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
FROM raw_access_requests
ORDER BY requested_at, request_id
LIMIT 10;

SELECT
    usage_date,
    user_id,
    tool_code,
    session_count,
    prompt_count,
    input_tokens_total,
    output_tokens_total
FROM raw_usage_events_daily
ORDER BY usage_date, user_id, tool_code
LIMIT 10;

SELECT
    billing_month,
    team_name,
    department_name,
    tool_code,
    licensed_seats,
    fixed_license_cost_usd,
    variable_usage_cost_usd,
    spend_usd
FROM raw_tool_spend_monthly
ORDER BY billing_month, team_name, tool_code
LIMIT 10;

-- --------------------------------
-- 5. Tool catalog sanity
-- --------------------------------
SELECT
    tool_category,
    count(*) AS tool_count
FROM raw_tool_catalog
GROUP BY tool_category
ORDER BY tool_category;

SELECT
    risk_tier,
    count(*) AS tool_count
FROM raw_tool_catalog
GROUP BY risk_tier
ORDER BY risk_tier;

-- --------------------------------
-- 6. User directory sanity
-- --------------------------------
SELECT
    department_name,
    team_name,
    count(*) AS user_count
FROM raw_user_directory
GROUP BY department_name, team_name
ORDER BY department_name, team_name;

SELECT
    employment_status,
    count(*) AS user_count
FROM raw_user_directory
GROUP BY employment_status
ORDER BY employment_status;

SELECT
    job_level,
    count(*) AS user_count
FROM raw_user_directory
GROUP BY job_level
ORDER BY job_level;

-- --------------------------------
-- 7. Access request sanity
-- --------------------------------
SELECT
    request_status,
    count(*) AS request_count
FROM raw_access_requests
GROUP BY request_status
ORDER BY request_status;

SELECT
    tool_code,
    request_status,
    count(*) AS request_count
FROM raw_access_requests
GROUP BY tool_code, request_status
ORDER BY tool_code, request_status;

SELECT
    date_trunc('month', requested_at)::DATE AS requested_month,
    count(*) AS request_count
FROM raw_access_requests
GROUP BY requested_month
ORDER BY requested_month;

SELECT
    min(requested_at) AS min_requested_at,
    max(requested_at) AS max_requested_at,
    min(reviewed_at) AS min_reviewed_at,
    max(reviewed_at) AS max_reviewed_at
FROM raw_access_requests;

SELECT
    request_status,
    count(*) FILTER (WHERE reviewed_at IS NULL) AS reviewed_at_null_count,
    count(*) FILTER (WHERE reviewed_by_user_id IS NULL) AS reviewed_by_null_count,
    count(*) FILTER (WHERE review_comment_text IS NULL) AS review_comment_null_count
FROM raw_access_requests
GROUP BY request_status
ORDER BY request_status;

-- duplicate glimpse
SELECT
    requester_user_id,
    tool_code,
    count(*) AS request_count
FROM raw_access_requests
GROUP BY requester_user_id, tool_code
HAVING count(*) > 1
ORDER BY request_count DESC, requester_user_id ASC, tool_code ASC
LIMIT 20;

-- --------------------------------
-- 8. Usage sanity
-- --------------------------------
SELECT
    min(usage_date) AS min_usage_date,
    max(usage_date) AS max_usage_date,
    count(*) AS usage_rows
FROM raw_usage_events_daily;

SELECT
    tool_code,
    count(*) AS usage_rows,
    count(DISTINCT user_id) AS distinct_users,
    sum(session_count) AS total_sessions,
    sum(prompt_count) AS total_prompts
FROM raw_usage_events_daily
GROUP BY tool_code
ORDER BY tool_code;

SELECT
    date_trunc('month', usage_date)::DATE AS usage_month,
    count(*) AS usage_rows,
    count(DISTINCT user_id) AS active_users
FROM raw_usage_events_daily
GROUP BY usage_month
ORDER BY usage_month;

-- composite uniqueness smoke check
SELECT
    usage_date,
    user_id,
    tool_code,
    count(*) AS duplicate_count
FROM raw_usage_events_daily
GROUP BY usage_date, user_id, tool_code
HAVING count(*) > 1
ORDER BY duplicate_count DESC, usage_date ASC, user_id ASC, tool_code ASC
LIMIT 20;

-- --------------------------------
-- 9. Spend sanity
-- --------------------------------
SELECT
    min(billing_month) AS min_billing_month,
    max(billing_month) AS max_billing_month,
    count(*) AS spend_rows
FROM raw_tool_spend_monthly;

SELECT
    billing_month,
    count(*) AS row_count,
    sum(licensed_seats) AS total_licensed_seats,
    sum(fixed_license_cost_usd) AS total_fixed_cost_usd,
    sum(variable_usage_cost_usd) AS total_variable_cost_usd,
    sum(spend_usd) AS total_spend_usd
FROM raw_tool_spend_monthly
GROUP BY billing_month
ORDER BY billing_month;

SELECT
    team_name,
    tool_code,
    count(*) AS billed_months,
    sum(licensed_seats) AS total_licensed_seats,
    sum(spend_usd) AS total_spend_usd
FROM raw_tool_spend_monthly
GROUP BY team_name, tool_code
ORDER BY total_spend_usd DESC, team_name ASC, tool_code ASC
LIMIT 30;

-- spend math smoke check
SELECT
    billing_month,
    team_name,
    tool_code,
    fixed_license_cost_usd,
    variable_usage_cost_usd,
    spend_usd,
    fixed_license_cost_usd + variable_usage_cost_usd AS expected_spend_usd
FROM raw_tool_spend_monthly
WHERE spend_usd <> fixed_license_cost_usd + variable_usage_cost_usd
ORDER BY billing_month
LIMIT 20;

-- --------------------------------
-- 10. Cross-table quick glimpse
-- --------------------------------
SELECT
    request.tool_code,
    request.request_status,
    count(*) AS request_count,
    count(DISTINCT request.requester_user_id) AS distinct_requesters
FROM raw_access_requests AS request
GROUP BY request.tool_code, request.request_status
ORDER BY request.tool_code, request.request_status;

SELECT
    usage_events.tool_code,
    count(DISTINCT usage_events.user_id) AS usage_users,
    sum(usage_events.prompt_count) AS total_prompts
FROM raw_usage_events_daily AS usage_events
GROUP BY usage_events.tool_code
ORDER BY usage_events.tool_code;

SELECT
    spend.tool_code,
    sum(spend.spend_usd) AS total_spend_usd
FROM raw_tool_spend_monthly AS spend
GROUP BY spend.tool_code
ORDER BY spend.tool_code;
