#!/usr/bin/env python3
"""Generate deterministic, Hive-partitioned instrument revision Parquet data.

The payload intentionally uses BigQuery-compatible camelCase field names and
stores business values as strings. dbt Bronze models rename and type this data.
The layout is compatible with a BigQuery external table using Hive partitioning:

    output/instrument_revisions/dt=YYYY-MM-DD/data.parquet
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)

INSTRUMENTS = (
    (1001, "Acme Corporation", "USD", "XNAS"),
    (1002, "Northwind Government Bond", "EUR", "XPAR"),
    (1003, "Global Technology ETF", "USD", "XNYS"),
    (1004, "Contoso Manufacturing", "EUR", "XETR"),
    (1005, "Fabrikam Dividend ETF", "GBP", "XLON"),
)
DEFAULT_START_DATE = (date.today() - timedelta(days=10)).isoformat()
DEFAULT_DAYS = 5
DEFAULT_ROWS_PER_DAY = len(INSTRUMENTS)


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise typer.BadParameter("Expected an ISO date, e.g. 2026-08-18") from error


def state_for_revision(
    instrument_id: int, name: str, currency: str, exchange: str, offset: int
) -> tuple[str, str, str]:
    """Return deterministic SCD changes while leaving other revisions unchanged."""
    if instrument_id == 1001 and offset >= 1:
        return "Acme Holdings", currency, exchange
    if instrument_id == 1002 and offset >= 2:
        return "Northwind Global Bond", "USD", "XNYS"
    if instrument_id == 1004 and offset >= 3:
        return name, currency, "XLON"
    if instrument_id == 1003 and offset >= 4:
        return "Global Innovation ETF", currency, exchange
    return name, currency, exchange


def rows_for_day(day: date, rows_per_day: int, offset: int) -> list[dict[str, str]]:
    """Create an upstream-style instrument revision batch for one partition."""
    day_start = datetime.combine(day, time(hour=10), tzinfo=timezone.utc)
    rows: list[dict[str, str]] = []

    for instrument_id, name, currency, exchange in INSTRUMENTS[:rows_per_day]:
        instrument_name, currency_code, exchange_code = state_for_revision(
            instrument_id, name, currency, exchange, offset
        )
        effective_at = day_start + timedelta(minutes=instrument_id % 10)
        rows.append(
            {
                "instrumentId": f" {instrument_id} ",
                "instrumentName": f" {instrument_name} ",
                "currencyCode": currency_code.lower(),
                "exchangeCode": exchange_code.lower(),
                "effectiveAt": effective_at.isoformat().replace("+00:00", "Z"),
                "revisionId": str(int(day.strftime("%Y%m%d"))),
                "sourceUpdatedAt": (effective_at + timedelta(minutes=5))
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )

    if offset == 2:
        rows.append(
            {
                "instrumentId": "not-an-integer",
                "instrumentName": "Malformed input",
                "currencyCode": "usd",
                "exchangeCode": "xnas",
                "effectiveAt": "not-a-timestamp",
                "revisionId": "not-a-revision",
                "sourceUpdatedAt": day_start.isoformat().replace("+00:00", "Z"),
            }
        )

    return rows


def write_partition(output_dir: Path, day: date, rows: list[dict[str, str]]) -> Path:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as error:  # pragma: no cover - depends on local installation
        raise SystemExit(
            "Missing dependency: run `make install` to create the project environment"
        ) from error

    schema = pa.schema(
        [
            pa.field("instrumentId", pa.string(), nullable=False),
            pa.field("instrumentName", pa.string(), nullable=False),
            pa.field("currencyCode", pa.string(), nullable=False),
            pa.field("exchangeCode", pa.string(), nullable=False),
            pa.field("effectiveAt", pa.string(), nullable=False),
            pa.field("revisionId", pa.string(), nullable=False),
            pa.field("sourceUpdatedAt", pa.string(), nullable=False),
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
                "(default: data/instrument_revisions)"
            )
        ),
    ] = Path("data/instrument_revisions"),
    start_date: Annotated[
        str, typer.Option(help="First partition date in ISO YYYY-MM-DD format.")
    ] = DEFAULT_START_DATE,
    days: Annotated[
        int, typer.Option(help="Number of daily revision batches to create.")
    ] = DEFAULT_DAYS,
    rows_per_day: Annotated[
        int, typer.Option(help="Number of valid instrument revisions per batch.")
    ] = DEFAULT_ROWS_PER_DAY,
    seed: Annotated[
        int,
        typer.Option(help="Retained for CLI compatibility; fixture values are fixed."),
    ] = 42,
) -> None:
    """Generate deterministic instrument revision Parquet files."""
    partition_start = parse_date(start_date)

    if days < 1:
        raise typer.BadParameter("Must be at least 1.", param_hint="--days")
    if rows_per_day < 1:
        raise typer.BadParameter("Must be at least 1.", param_hint="--rows-per-day")
    if rows_per_day > len(INSTRUMENTS):
        raise typer.BadParameter(
            "Must be at most "
            f"{len(INSTRUMENTS)} for one revision per instrument/batch.",
            param_hint="--rows-per-day",
        )
    del seed

    for offset in range(days):
        partition_date = partition_start + timedelta(days=offset)
        rows = rows_for_day(partition_date, rows_per_day, offset)
        output_file = write_partition(output_dir, partition_date, rows)
        typer.echo(f"Wrote {len(rows)} rows to {output_file}")


if __name__ == "__main__":
    app()
