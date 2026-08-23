# dbt Core + BigQuery medallion workshop

This repository provides deterministic Parquet fixtures and a dbt starter project
for a Bronze → Silver → Gold workshop. The shared infrastructure is assumed to
exist already.

```text
Hive-partitioned Parquet → BigQuery external table → Bronze view
  → Silver incremental SCD2 history + change view → Gold current-instruments table
```

## Generate source fixtures

Install the local generator dependencies, then create five dated revision batches:

```bash
make install
make generate START_DATE=2026-08-13
```

The output layout is compatible with BigQuery Hive partitioning:

```text
data/instrument_revisions/
└── dt=YYYY-MM-DD/data.parquet
```

The Parquet payload uses BigQuery-compatible camelCase fields, but intentionally
stores identifiers and timestamps as strings. It includes unchanged revisions,
changed attributes, and one malformed record. Bronze normalizes the valid values
and retains the malformed record in a rejection view.

Inspect a local fixture with:

```bash
uv run python scripts/inspect_parquet.py \
  data/instrument_revisions/dt=2026-08-13/data.parquet
```

Upload the *contents* of the generated directory to the already-provisioned
bucket prefix:

```bash
gcloud storage cp --recursive \
  data/instrument_revisions \
  gs://YOUR_WORKSHOP_DATA_BUCKET/instrument_revisions
```

## Run the participant dbt project

See [the participant instructions](dbt-workshop/README.md). In short: configure
the profile and `raw_bucket` variable, create the external table, load the seed,
and run `dbt build`.

## Local checks

```bash
make format
make check
```