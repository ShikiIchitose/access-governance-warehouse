WITH

raw_user_directory AS (
    SELECT
        user_id,
        user_name,
        user_email,
        team_name,
        department_name,
        job_level,
        employment_status
    FROM {{ source('access_governance', 'raw_user_directory') }}
),

normalized AS (
    SELECT
        trim(user_id) AS user_id,
        trim(user_name) AS user_name,
        lower(trim(user_email)) AS user_email,
        trim(team_name) AS team_name,
        trim(department_name) AS department_name,
        lower(trim(job_level)) AS job_level,
        lower(trim(employment_status)) AS employment_status
    FROM raw_user_directory
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
    FROM normalized
)

SELECT * FROM final
