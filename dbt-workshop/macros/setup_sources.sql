{% macro setup_sources() %}

    {% set raw_bucket = var('raw_bucket') %}

    {% if not raw_bucket or raw_bucket == 'YOUR_WORKSHOP_DATA_BUCKET' %}
        {{ exceptions.raise_compiler_error("Set vars.raw_bucket in dbt_project.yml") }}
    {% endif %}

    {% set s3_path = 'gs://' ~ raw_bucket ~ '/events' %}

    {{ log("S3 prefix: " ~ s3_path, info=True) }}

    {{
        create_external_table(
            dataset=target.dataset,
            table_name='events_external',
            s3_path=s3_path,
            partitions='dt DATE',
        )
    }}

{% endmacro %}
