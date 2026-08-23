# Participant dbt project

This project builds a contracted medallion pipeline over shared Parquet
instrument revisions. Each participant creates only an external-table definition
and dbt relations in their own BigQuery dataset.

## Set up

```bash
cd dbt-workshop
python -m venv VENV
source VENV/bin/activate
pip install -r requirements.txt
cp profiles.yml.example profiles.yml
```

Edit `profiles.yml` with your GCP project, workshop dataset, and location. In
`dbt_project.yml`, set `vars.raw_bucket` to the existing shared GCS bucket name,
without `gs://`.

Check the connection and create the participant-local external table:

```bash
dbt debug
dbt run-operation setup_sources
```

The macro creates `instrument_revisions_external` over:

```text
gs://<raw_bucket>/instrument_revisions/dt=YYYY-MM-DD/data.parquet
```

## Build the medallion pipeline

```bash
dbt seed
dbt build
```

The resulting lineage is:

```text
raw.instrument_revisions (external table)
  → bronze_instrument_revisions (view)
  → silver_instrument_history (incremental SCD2 table)
  → silver_instrument_changes (view)
  → gold_current_instruments (table)
```

`bronze_rejected_instrument_revisions` is a parallel Bronze audit view. It shows
the deliberately malformed source record and its rejection reason; the valid
Bronze view feeds Silver.

## What to inspect

```sql
-- Type enforcement and column-name normalization
select * from bronze_instrument_revisions order by instrument_id, revision_id;

-- The quarantined malformed upstream row
select * from bronze_rejected_instrument_revisions;

-- SCD2 validity ranges and the current record
select * from silver_instrument_history order by instrument_id, valid_from;

-- Exactly which attributes changed between SCD2 versions
select * from silver_instrument_changes order by instrument_id, changed_at;

-- Current records enriched from the exchange seed
select * from gold_current_instruments order by instrument_id;
```

Every model has an enforced dbt contract. Bronze and the Silver diff stay views:
their contracts preflight all output names and data types, while dbt data tests
validate nullability and business rules. The Silver SCD2 model uses an
incremental merge table with `on_schema_change: fail`.
