# Tldr;

Dbt-intro:
- external table
- medallion architecture
- dbt core concepts: macros, seed, models, data contract, incremental SCD2

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

Edit `profiles.yml`
```bash
project: __GCP_PROJECT_ID__
dataset: __BQ_DATASET__
location: __BQ_LOCATION__
```

In
`dbt_project.yml`, set `vars.raw_bucket` to the existing shared GCS bucket name,
without `gs://`.



```bash
dbt debug
dbt run-operation setup_sources
```

The macro creates `instrument_revisions_external` over:

```text
gs://<raw_bucket>/instrument_revisions/dt=YYYY-MM-DD/data.parquet
```

## Create a couple of views on top of external table 

```bash
dbt select --select bronze_instruments_qualified
dbt build --select bronze_instruments_qualified
dbt select --select bronze_instruments_quarantine
dbt build --select bronze_instruments_quarantine
```

## Build an incremental SCD2 history and diff between versions

```bash
dbt run --select silver_instrument_history
dbt build --select silver_instrument_history
dbt run --select silver_instrument_changes
dbt build --select silver_instrument_changes
```

## Create a static table with csv content
```bash
dbt seed --select gold_instruments
```

## Finally create a gold table
```bash
dbt build --select exchanges
```

## Task is to build full bronze/golden/layer views/table

The resulting lineage is:

```text
raw.instruments (external table)
  → bronze_instruments (view)
  → silver_instruments_history (incremental SCD2 table)
  → silver_instruments_changes (view)
  → gold_instruments (table)
```

`bronze_instrument_quarantine` - contain rows that break data contracts

## What to inspect

```sql
-- Type enforcement and column-name normalization
select * from bronze_instruments_qualified order by instrument_id, effective_at;

-- The quarantined malformed upstream row
select * from bronze_instrument_quarantine;

-- SCD2 validity ranges and the current record
select * from silver_instruments_history order by instrument_id, valid_from;

-- Exactly which attributes changed between SCD2 versions
select * from silver_instruments_changes order by instrument_id, changed_at;

-- Current records enriched from the exchange seed
select * from gold_instruments order by instrument_id;
```
