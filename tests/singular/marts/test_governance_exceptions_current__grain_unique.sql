SELECT
    user_id,
    tool_code,
    count(*) AS row_count
FROM {{ ref('governance_exceptions_current') }}
GROUP BY
    user_id,
    tool_code
HAVING count(*) > 1
