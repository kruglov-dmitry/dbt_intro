{% macro create_external_table(dataset, table_name, s3_path, partitions) %}

{% set dataset_sql %}
    create schema if not exists `{{ target.project }}.{{ dataset }}`
    options ( location = '{{ target.location }}' );
{% endset %}

{% set table_sql %}
    create or replace external table `{{ target.project }}.{{ dataset }}.{{ table_name }}`
    {% if partitions %}
        with partition columns ( {{ partitions }} )
    {% endif %}
    options ( format = 'PARQUET', uris = ['{{ s3_path }}/*']
    {% if partitions %}
        , hive_partition_uri_prefix = '{{ s3_path }}'
        , require_hive_partition_filter = false
    {% endif %} );
{% endset %}

    {% do log("Creating dataset if not exists: " ~ dataset, info=True) %}
    {% do run_query(dataset_sql) %}
    {% do log("Creating external table " ~ dataset ~ "." ~ table_name, info=True) %}

    {% do run_query(table_sql) %}
    {% do log("External table created", info=True) %}

{% endmacro %}
