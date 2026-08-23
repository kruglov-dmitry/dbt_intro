{{ config(alias='instruments_quarantine', materialized='view', tags=['bronze']) }}

WITH parsed AS (
    SELECT
        instrumentId AS raw_instrument_id,
        instrumentName AS raw_instrument_name,
        currencyCode AS raw_currency_code,
        exchangeCode AS raw_exchange_code,
        effectiveAt AS raw_effective_at,
        sourceUpdatedAt AS raw_source_updated_at,
        dt AS load_date,
        SAFE_CAST(NULLIF(TRIM(instrumentId), '') AS INT64) AS instrument_id,
        NULLIF(TRIM(instrumentName), '') AS instrument_name,
        NULLIF(TRIM(currencyCode), '') AS currency_code,
        NULLIF(TRIM(exchangeCode), '') AS exchange_code,
        SAFE_CAST(NULLIF(TRIM(effectiveAt), '') AS TIMESTAMP) AS effective_at,
        SAFE_CAST(NULLIF(TRIM(sourceUpdatedAt), '') AS TIMESTAMP)
            AS source_updated_at
    FROM {{ source('raw', 'instruments') }}
)

SELECT
    raw_instrument_id,
    raw_instrument_name,
    raw_currency_code,
    raw_exchange_code,
    raw_effective_at,
    raw_source_updated_at,
    load_date,
    CASE
        WHEN instrument_id IS NULL THEN 'instrumentId cannot be cast to INT64'
        WHEN instrument_name IS NULL THEN 'instrumentName is blank'
        WHEN currency_code IS NULL THEN 'currencyCode is blank'
        WHEN exchange_code IS NULL THEN 'exchangeCode is blank'
        WHEN effective_at IS NULL THEN 'effectiveAt cannot be cast to TIMESTAMP'
        WHEN
            source_updated_at IS NULL
            THEN 'sourceUpdatedAt cannot be cast to TIMESTAMP'
    END AS rejection_reason
FROM parsed
WHERE
    instrument_id IS NULL
    OR instrument_name IS NULL
    OR currency_code IS NULL
    OR exchange_code IS NULL
    OR effective_at IS NULL
    OR source_updated_at IS NULL
