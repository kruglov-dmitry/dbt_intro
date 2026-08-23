{% macro setup_sources() %}

    {% set raw_bucket = var('raw_bucket') %}

    {% if not raw_bucket or raw_bucket == 'REPLACE_ME' %}
        {{ exceptions.raise_compiler_error("Set vars.raw_bucket in dbt_project.yml") }}
    {% endif %}

    {% set gcs_path = 'gs://' ~ raw_bucket ~ '/instruments' %}

    {{ log("GCS prefix: " ~ gcs_path, info=True) }}

    {{
        create_external_table(
            dataset=target.dataset,
            table_name='instruments_external',
            gcs_path=gcs_path,
            partitions='dt DATE',
        )
    }}

{% endmacro %}
