SELECT *
FROM {{ ref('silver_instruments_changes') }}
WHERE changed_columns = ''
