{{ config(materialized='view', tags=['bronze']) }}

SELECT
    *
-- TODO: Tag every invalid raw records by errors reason
FROM
    {{ source('raw', 'instruments') }}
