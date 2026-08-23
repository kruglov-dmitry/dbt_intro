{{ config(alias='instruments_quarantine', materialized='view', tags=['bronze']) }}

-- TODO: Surface the invalid raw records and a human-readable rejection reason.
SELECT
    *
FROM
    {{ source('raw', 'instrument_revisions') }}
