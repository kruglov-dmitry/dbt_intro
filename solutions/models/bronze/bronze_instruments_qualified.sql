{{ config(alias='instruments', materialized='view', tags=['bronze']) }}

WITH parsed AS (
    SELECT
        dt AS load_date,
        SAFE_CAST(NULLIF(TRIM(instrumentId), '') AS INT64) AS instrument_id,
        NULLIF(TRIM(instrumentName), '') AS instrument_name,
        UPPER(NULLIF(TRIM(currencyCode), '')) AS currency_code,
        UPPER(NULLIF(TRIM(exchangeCode), '')) AS exchange_code,
        SAFE_CAST(NULLIF(TRIM(effectiveAt), '') AS TIMESTAMP) AS effective_at,
        SAFE_CAST(NULLIF(TRIM(sourceUpdatedAt), '') AS TIMESTAMP)
            AS source_updated_at
    FROM {{ source('raw', 'instruments') }}
),

validated AS (
    SELECT
        *,
        CASE
            WHEN
                instrument_id IS NULL
                THEN 'instrumentId cannot be cast to INT64'
            WHEN instrument_name IS NULL THEN 'instrumentName is blank'
            WHEN currency_code IS NULL THEN 'currencyCode is blank'
            WHEN exchange_code IS NULL THEN 'exchangeCode is blank'
            WHEN
                effective_at IS NULL
                THEN 'effectiveAt cannot be cast to TIMESTAMP'
            WHEN
                source_updated_at IS NULL
                THEN 'sourceUpdatedAt cannot be cast to TIMESTAMP'
        END AS rejection_reason
    FROM parsed
)

SELECT
    instrument_id,
    instrument_name,
    currency_code,
    exchange_code,
    effective_at,
    source_updated_at,
    load_date
FROM validated
WHERE rejection_reason IS NULL
