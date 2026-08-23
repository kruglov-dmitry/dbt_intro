{{ config(alias='instrument_changes', materialized='view', tags=['silver']) }}

-- TODO: Compare each SCD2 version with its preceding version and list changes.
select *
from {{ ref('silver_instrument_history') }}
