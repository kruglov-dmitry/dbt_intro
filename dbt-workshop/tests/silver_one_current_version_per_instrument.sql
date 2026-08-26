SELECT instrument_id
FROM {{ ref('silver_instruments_history') }}
GROUP BY 1
HAVING COUNTIF(is_current) != 1
