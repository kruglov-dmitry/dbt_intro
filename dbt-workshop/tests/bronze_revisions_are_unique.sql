SELECT
    instrument_id,
    effective_at
FROM {{ ref('bronze_instruments_qualified') }}
GROUP BY 1, 2
HAVING COUNT(*) > 1
