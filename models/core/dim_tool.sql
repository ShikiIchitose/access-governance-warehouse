WITH

source AS (
    SELECT
        tool_code,
        tool_name,
        vendor_name,
        tool_category,
        deployment_scope,
        risk_tier,
        is_active,
        homepage_url
    FROM {{ ref('stg_access_governance__tool_catalog') }}
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
    FROM source
)

SELECT * FROM final
