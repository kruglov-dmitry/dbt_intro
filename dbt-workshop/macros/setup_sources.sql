{% macro setup_sources() %}

    {% set raw_bucket = var('raw_bucket') %}

    {% if not raw_bucket or raw_bucket == 'YOUR_WORKSHOP_DATA_BUCKET' %}
        {{ exceptions.raise_compiler_error("Set vars.raw_bucket in dbt_project.yml") }}
    {% endif %}

    {% set gcs_path = 'gs://' ~ raw_bucket ~ '/instrument_revisions' %}

    {{ log("GCS prefix: " ~ gcs_path, info=True) }}

    {{
        create_external_table(
            dataset=target.dataset,
            table_name='instrument_revisions_external',
            gcs_path=gcs_path,
            partitions='dt DATE',
        )
    }}

{% endmacro %}
