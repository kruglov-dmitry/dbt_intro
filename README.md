# dbt Core + BigQuery medallion workshop

This repository provides deterministic Parquet fixtures and a dbt starter project
for a Bronze → Silver → Gold workshop. The shared infrastructure is assumed to
exist already.

```text
Hive-partitioned Parquet → BigQuery external table → Bronze view
  → Silver incremental SCD2 history + change view → Gold current-instruments table
```

## Generate source fixtures

Install the local generator dependencies, then create five dated change batches:

```bash
make install
make generate START_DATE=2026-08-13
```

The output layout is compatible with BigQuery Hive partitioning:

```text
data/instruments/
└── dt=YYYY-MM-DD/data.parquet
```

The Parquet payload uses BigQuery-compatible camelCase fields, but intentionally
stores identifiers and timestamps as strings. It includes unchanged records and
tracked-attribute changes. Defects are opt-in so the default fixture is a clean
happy path.

Inspect a local fixture with:

```bash
uv run python scripts/inspect_parquet.py \
  data/instruments/dt=2026-08-13/data.parquet
```

Upload the *contents* of the generated directory to the already-provisioned
bucket prefix:

```bash
gcloud storage cp --recursive \
  data/instruments \
  gs://YOUR_WORKSHOP_DATA_BUCKET/instruments

## Add defects by partition date

Pass one or more `--defect DATE:KIND` options to inject a deliberately bad row
into a chosen Hive partition. The date must be within the generated range.

| Kind | Result | Expected dbt outcome |
|---|---|---|
| `unsupported-code` | Validly typed row with unsupported currency and exchange codes | Bronze `accepted_values` tests fail. |
| `duplicate` | Duplicate `(instrument_id, effective_at)` row | Bronze uniqueness test fails. |
| `blank-required` | Blank instrument name | Bronze sends the row to its quarantine view. |

For example:

```bash
uv run python scripts/generate_events.py \
  --start-date 2026-08-13 \
  --days 5 \
  --defect 2026-08-15:blank-required \
  --defect 2026-08-16:duplicate

make generate START_DATE=2026-08-13 DAYS=5 \
  DEFECTS='2026-08-15:unsupported-code 2026-08-16:duplicate'
```
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
