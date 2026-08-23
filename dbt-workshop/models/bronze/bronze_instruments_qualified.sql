{{ config(alias='instruments', materialized='view', tags=['bronze']) }}

SELECT
    *
-- TODO: Select raw revisions from the source, sanitize column names and values,
-- cast them to the Bronze contract, and retain only valid records.
FROM
    {{ source('raw', 'instruments') }}
