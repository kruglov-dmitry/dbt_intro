#!/usr/bin/env python3
"""Generate deterministic, date-partitioned event data for the dbt workshop.

The output layout is compatible with a BigQuery external table using hive
partitioning:

    output/events/dt=2026-08-18/data.parquet
    output/events/dt=2026-08-19/data.parquet

Example:

    python scripts/generate_events.py --output-dir data/events
    gsutil -m cp -r data/events gs://dbt-workshop-data/
"""

from __future__ import annotations

import argparse
import random
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

INSTRUMENTS = (
    (1001, "EQUITY"),
    (1002, "BOND"),
    (1003, "ETF"),
    (1004, "EQUITY"),
    (1005, "ETF"),
)
EVENT_TYPES = ("TRADE", "QUOTE", "CORRECTION")


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Expected an ISO date, e.g. 2026-08-18"
        ) from error


def rows_for_day(day: date, rows_per_day: int, seed: int) -> list[dict[str, object]]:
    """Create a stable yet varied set of events for one date partition."""
    randomizer = random.Random(f"{seed}:{day.isoformat()}")
    day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    rows: list[dict[str, object]] = []

    for sequence in range(1, rows_per_day + 1):
        instrument_id, _instrument_type = randomizer.choice(INSTRUMENTS)
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
                "dt": day,
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
            pa.field("dt", pa.date32(), nullable=False),
        ]
    )
    partition_dir = output_dir / f"dt={day.isoformat()}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    output_file = partition_dir / "data.parquet"
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, output_file, compression="snappy")
    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/events"),
        help=(
            "Directory that will contain dt=YYYY-MM-DD partitions "
            "(default: data/events)"
        ),
    )
    parser.add_argument(
        "--start-date",
        type=parse_date,
        default=date(2026, 8, 18),
        help="First partition date (default: 2026-08-18)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=3,
        help="Number of daily partitions to create (default: 3)",
    )
    parser.add_argument(
        "--rows-per-day",
        type=int,
        default=100,
        help="Number of event rows per partition (default: 100)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed for deterministic output (default: 42)",
    )
    arguments = parser.parse_args()

    if arguments.days < 1:
        parser.error("--days must be at least 1")
    if arguments.rows_per_day < 1:
        parser.error("--rows-per-day must be at least 1")

    for offset in range(arguments.days):
        partition_date = arguments.start_date + timedelta(days=offset)
        output_file = write_partition(
            arguments.output_dir,
            partition_date,
            rows_for_day(partition_date, arguments.rows_per_day, arguments.seed),
        )
        print(f"Wrote {arguments.rows_per_day} rows to {output_file}")


if __name__ == "__main__":
    main()
