{{
    config(
        alias='instruments',
        materialized='incremental',
        incremental_strategy='merge',
        unique_key=['instrument_id', 'valid_from'],
        on_schema_change='fail',
        tags=['silver', 'scd2']
    )
}}

WITH affected_instruments AS (
    SELECT DISTINCT instrument_id
    FROM {{ ref('bronze_instruments_qualified') }} AS src
    {% if is_incremental() %}
        WHERE src.load_date >= COALESCE(
            DATE_SUB(
                (
                    SELECT MAX(trg.load_date)
                    FROM {{ this }} AS trg
                ),
                INTERVAL 2 DAY
            ),
            src.load_date
        )
    {% endif %}
),

revisions AS (
    SELECT
        instrument_id,
        instrument_name,
        currency_code,
        exchange_code,
        effective_at,
        source_updated_at,
        load_date,
        TO_HEX(
            SHA256(
                CONCAT(
                    CAST(instrument_id AS STRING), '|',
                    COALESCE(instrument_name, '∅'), '|',
                    COALESCE(currency_code, '∅'), '|',
                    COALESCE(exchange_code, '∅')
                )
            )
        ) AS content_hash
    FROM {{ ref('bronze_instruments_qualified') }}
    WHERE instrument_id IN (SELECT ai.instrument_id FROM affected_instruments AS ai)
),

with_previous_hash AS (
    SELECT
        *,
        LAG(content_hash) OVER (
            PARTITION BY instrument_id
            ORDER BY effective_at, source_updated_at, load_date
        ) AS previous_content_hash
    FROM revisions
),

changed_revisions AS (
    SELECT *
    FROM with_previous_hash
    WHERE previous_content_hash IS NULL OR content_hash != previous_content_hash
),

version_boundaries AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY instrument_id
            ORDER BY effective_at, source_updated_at, load_date
        ) AS scd_version,
        LEAD(effective_at) OVER (
            PARTITION BY instrument_id
            ORDER BY effective_at, source_updated_at, load_date
        ) AS valid_to
    FROM changed_revisions
)

SELECT
    instrument_id,
    instrument_name,
    currency_code,
    exchange_code,
    content_hash,
    scd_version,
    effective_at AS valid_from,
    valid_to,
    source_updated_at,
    load_date,
    valid_to IS NULL AS is_current
FROM version_boundaries
