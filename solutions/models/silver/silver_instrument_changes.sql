{{ config(alias='instrument_changes', materialized='view', tags=['silver']) }}

WITH history_with_previous AS (
    SELECT
        *,
        LAG(scd_version) OVER version_order AS previous_scd_version,
        LAG(valid_from) OVER version_order AS previous_valid_from,
        LAG(instrument_name) OVER version_order AS previous_instrument_name,
        LAG(currency_code) OVER version_order AS previous_currency_code,
        LAG(exchange_code) OVER version_order AS previous_exchange_code
    FROM {{ ref('silver_instrument_history') }}
    WINDOW version_order AS (PARTITION BY instrument_id ORDER BY valid_from, scd_version)
)

SELECT
    instrument_id,
    previous_scd_version,
    scd_version,
    valid_from AS changed_at,
    previous_instrument_name,
    instrument_name,
    previous_currency_code,
    currency_code,
    previous_exchange_code,
    exchange_code,
    ARRAY_TO_STRING(
        ARRAY(
            SELECT changed_column
            FROM
                UNNEST([
                    IF(previous_instrument_name != instrument_name, 'instrument_name', NULL),
                    IF(previous_currency_code != currency_code, 'currency_code', NULL),
                    IF(previous_exchange_code != exchange_code, 'exchange_code', NULL)
                ]) AS changed_column
            WHERE changed_column IS NOT NULL
        ),
        ', '
    ) AS changed_columns
FROM history_with_previous
WHERE previous_valid_from IS NOT NULL
