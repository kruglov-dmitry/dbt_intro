SELECT *
FROM {{ ref('silver_instruments_history') }}
WHERE valid_to IS NOT NULL AND valid_to <= valid_from
