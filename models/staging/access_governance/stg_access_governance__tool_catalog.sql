WITH

raw_tool_catalog AS (
    SELECT
        tool_code,
        tool_name,
        vendor_name,
        tool_category,
        deployment_scope,
        risk_tier,
        is_active,
        homepage_url
    FROM {{ source('access_governance', 'raw_tool_catalog') }}
),

normalized AS (
    SELECT
        trim(tool_code) AS tool_code,
        trim(tool_name) AS tool_name,
        trim(vendor_name) AS vendor_name,
        lower(trim(tool_category)) AS tool_category,
        lower(trim(deployment_scope)) AS deployment_scope,
        lower(trim(risk_tier)) AS risk_tier,
        is_active,
        CASE
            WHEN homepage_url IS NULL THEN NULL
            ELSE trim(homepage_url)
        END AS homepage_url
    FROM raw_tool_catalog
),

final AS (
    SELECT
        tool_code,
        tool_name,
        vendor_name,
        tool_category,
        deployment_scope,
        risk_tier,
        is_active,
        homepage_url
    FROM normalized
)

SELECT * FROM final
