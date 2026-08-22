#!/usr/bin/env python3
"""Generate deterministic, date-partitioned event data for the dbt workshop.

The default output is a clean SCD2 recovery happy path: every instrument emits
exactly one state event per day, so (instrument_id, dt) is unique. The output
layout is compatible with a BigQuery external table using hive partitioning:

    output/events/dt=YYYY-MM-DD/data.parquet

Example:

    python scripts/generate_events.py --output-dir data/events
    gsutil -m cp -r data/events gs://dbt-workshop-data/
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)

INSTRUMENTS = (
    (1001, "EQUITY"),
    (1002, "BOND"),
    (1003, "ETF"),
    (1004, "EQUITY"),
    (1005, "ETF"),
)
EVENT_TYPES = ("TRADE", "QUOTE", "CORRECTION")
DEFAULT_START_DATE = (date.today() - timedelta(days=10)).isoformat()
DEFAULT_DAYS = 5
DEFAULT_ROWS_PER_DAY = len(INSTRUMENTS)


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise typer.BadParameter("Expected an ISO date, e.g. 2026-08-18") from error


def rows_for_day(day: date, rows_per_day: int, seed: int) -> list[dict[str, object]]:
    """Create a stable yet varied set of events for one date partition."""
    randomizer = random.Random(f"{seed}:{day.isoformat()}")
    day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    rows: list[dict[str, object]] = []

    selected_instruments = randomizer.sample(INSTRUMENTS, rows_per_day)

    for sequence, (instrument_id, _instrument_type) in enumerate(
        selected_instruments, start=1
    ):
        event_type = randomizer.choices(EVENT_TYPES, weights=(75, 20, 5), k=1)[0]
        updated_at = day_start + timedelta(
            seconds=randomizer.randrange(0, 24 * 60 * 60),
            microseconds=randomizer.randrange(0, 1_000_000),
        )
        rows.append(
            {
                "event_id": f"evt-{day:%Y%m%d}-{sequence:05d}",
                "instrument_id": instrument_id,
                "event_type": event_type,
                "value": round(randomizer.uniform(10, 500), 4),
                "updated_at": updated_at,
            }
        )

    return rows


def write_partition(output_dir: Path, day: date, rows: list[dict[str, object]]) -> Path:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as error:  # pragma: no cover - depends on local installation
        raise SystemExit(
            "Missing dependency: run `make install` to create the project environment"
        ) from error

    schema = pa.schema(
        [
            pa.field("event_id", pa.string(), nullable=False),
            pa.field("instrument_id", pa.int64(), nullable=False),
            pa.field("event_type", pa.string(), nullable=False),
            pa.field("value", pa.float64(), nullable=False),
            pa.field("updated_at", pa.timestamp("us", tz="UTC"), nullable=False),
        ]
    )
    partition_dir = output_dir / f"dt={day.isoformat()}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    output_file = partition_dir / "data.parquet"
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, output_file, compression="snappy")
    return output_file


@app.command()
def generate(
    output_dir: Annotated[
        Path,
        typer.Option(
            help=(
                "Directory that will contain dt=YYYY-MM-DD partitions "
                "(default: data/events)"
            )
        ),
    ] = Path("data/events"),
    start_date: Annotated[
        str, typer.Option(help="First partition date in ISO YYYY-MM-DD format.")
    ] = DEFAULT_START_DATE,
    days: Annotated[
        int, typer.Option(help="Number of daily partitions to create.")
    ] = DEFAULT_DAYS,
    rows_per_day: Annotated[
        int, typer.Option(help="Number of event rows per partition.")
    ] = DEFAULT_ROWS_PER_DAY,
    seed: Annotated[
        int, typer.Option(help="Seed for deterministic output (default: 42)")
    ] = 42,
) -> None:
    """Generate deterministic, date-partitioned event Parquet files."""
    partition_start = parse_date(start_date)

    if days < 1:
        raise typer.BadParameter("Must be at least 1.", param_hint="--days")
    if rows_per_day < 1:
        raise typer.BadParameter("Must be at least 1.", param_hint="--rows-per-day")
    if rows_per_day > len(INSTRUMENTS):
        raise typer.BadParameter(
            f"Must be at most {len(INSTRUMENTS)} for unique instrument/day pairs.",
            param_hint="--rows-per-day",
        )

    for offset in range(days):
        partition_date = partition_start + timedelta(days=offset)
        output_file = write_partition(
            output_dir,
            partition_date,
            rows_for_day(partition_date, rows_per_day, seed),
        )
        typer.echo(f"Wrote {rows_per_day} rows to {output_file}")


if __name__ == "__main__":
    app()
