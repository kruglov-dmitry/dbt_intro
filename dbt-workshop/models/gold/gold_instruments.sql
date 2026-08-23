{{ config(alias='instruments', materialized='table', tags=['gold']) }}

SELECT
    *
-- enrich CURRENT state of instrument with
-- enriched details about exchanges
FROM {{ ref('silver_instrument_history') }}
