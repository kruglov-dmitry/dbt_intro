SELECT *
FROM {{ ref('silver_instrument_changes') }}
WHERE changed_columns = ''
