WITH

source AS (
    SELECT
        user_id,
        user_name,
        user_email,
        team_name,
        department_name,
        job_level,
        employment_status
    FROM {{ ref('stg_access_governance__user_directory') }}
),

final AS (
    SELECT
        user_id,
        user_name,
        user_email,
        team_name,
        department_name,
        job_level,
        employment_status
    FROM source
)

SELECT * FROM final
