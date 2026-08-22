# dbt workshop data

This project generates deterministic, Hive-partitioned Parquet event data for
the dbt Core and BigQuery workshop. The output is intended for upload to GCS
and querying through a BigQuery external table.

## Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/)
- `make`

For the optional upload step, install and authenticate the Google Cloud CLI:

```bash
gcloud auth login
gcloud auth application-default login
```

## Install dependencies

From the repository root, create the local environment and install the locked
runtime and development dependencies:

```bash
make install
```

This installs `pyarrow` for Parquet generation and Ruff for formatting and
linting. The local `.venv` directory is ignored by Git.

## Generate the default workshop dataset

```bash
make generate
```

The default command creates three daily partitions beginning on 2026-08-18,
with 100 rows per partition:

```text
data/events/
├── dt=2026-08-18/data.parquet
├── dt=2026-08-19/data.parquet
└── dt=2026-08-20/data.parquet
```

Every partition contains these columns:

| Column | Parquet type | Description |
|---|---|---|
| `event_id` | string | Stable event identifier: `evt-YYYYMMDD-NNNNN`. |
| `instrument_id` | int64 | Identifier from the small, fixed instrument set. |
| `event_type` | string | One of `TRADE`, `QUOTE`, or `CORRECTION`. |
| `value` | float64 | Deterministic pseudo-random event value. |
| `updated_at` | UTC timestamp | Timestamp within the partition date. |
| `dt` | date | Event date; also encoded in the directory name. |

## Customise a generation run

Pass Make variables to override the defaults:

```bash
make generate START_DATE=2026-09-01 DAYS=5 ROWS_PER_DAY=250 SEED=7
```

Available variables:

| Variable | Default | Meaning |
|---|---|---|
| `OUTPUT_DIR` | `data/events` | Parent directory for the `dt=YYYY-MM-DD` partitions. |
| `START_DATE` | `2026-08-18` | First partition date, in ISO `YYYY-MM-DD` format. |
| `DAYS` | `3` | Number of daily partitions to create. |
| `ROWS_PER_DAY` | `100` | Number of events in each partition. |
| `SEED` | `42` | Random seed used to make output reproducible. |

For example, write data outside the repository:

```bash
make generate OUTPUT_DIR=/tmp/workshop-events DAYS=2 ROWS_PER_DAY=10
```

The same `START_DATE`, `DAYS`, `ROWS_PER_DAY`, and `SEED` always produce the
same rows. Re-running with the same output directory overwrites each generated
`data.parquet` file for those dates.

## Upload to GCS

After generation, copy the **contents** of the event directory to the intended
bucket prefix. This preserves the Hive-style `dt=...` directories:

```bash
gcloud storage cp --recursive data/events gs://dbt-workshop-data/events
```

The resulting object paths are:

```text
gs://dbt-workshop-data/events/dt=2026-08-18/data.parquet
gs://dbt-workshop-data/events/dt=2026-08-19/data.parquet
gs://dbt-workshop-data/events/dt=2026-08-20/data.parquet
```

## Developer commands

```bash
make help    # list all targets
make format  # apply Ruff formatting
make lint    # run Ruff lint checks
make check   # verify formatting and linting without changes
make clean   # remove data/events (or OUTPUT_DIR if supplied)
```

Run `make check` before committing changes to the generator.

## dbt participant project

The `dbt-workshop` directory is a separately runnable participant starter
project. Create its local BigQuery profile with:

```bash
uv run python scripts/configure_dbt_profile.py \
  --project-id YOUR_GCP_PROJECT \
  --dataset workshop_your_name \
  --location EU
```

Then use `dbt run-operation create_workshop_dataset --profiles-dir .` from the
participant project to provision the configured target dataset. See
[dbt-workshop/README.md](dbt-workshop/README.md) for the complete dbt command
sequence and exercise flow.
