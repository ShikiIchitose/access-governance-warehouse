WITH

candidate_rows AS (
    SELECT count(*) AS candidate_row_count
    FROM {{ ref('adoption_review_candidates_monthly') }}
),

adoption_rows AS (
    SELECT count(*) AS adoption_row_count
    FROM {{ ref('tool_adoption_monthly') }}
)

SELECT
    candidate_rows.candidate_row_count,
    adoption_rows.adoption_row_count
FROM candidate_rows
CROSS JOIN adoption_rows
WHERE candidate_rows.candidate_row_count != adoption_rows.adoption_row_count
