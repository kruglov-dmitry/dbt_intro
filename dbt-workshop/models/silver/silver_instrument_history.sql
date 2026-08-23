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

-- TODO: On incremental runs, use a load_date window to identify affected
-- instruments, then rebuild the full history for those instruments.
-- Derive scd_version, valid_from, valid_to, and is_current from state changes.
select *
from {{ ref('bronze_instruments_qualified') }}
