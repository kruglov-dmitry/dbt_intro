{{ config(alias='instruments', materialized='table', tags=['gold']) }}

SELECT
    history.instrument_id,
    history.instrument_name,
    history.currency_code,
    history.exchange_code,
    exchanges.market_region,
    exchanges.trading_calendar,
    history.valid_from AS current_since
FROM {{ ref('silver_instruments_history') }} AS history
LEFT JOIN {{ ref('exchanges') }} AS exchanges
    ON history.exchange_code = exchanges.exchange_code
WHERE history.is_current
