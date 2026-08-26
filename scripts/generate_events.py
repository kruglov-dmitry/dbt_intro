#!/usr/bin/env python3
"""Generate deterministic, Hive-partitioned instrument change Parquet data.

The payload intentionally uses BigQuery-compatible camelCase field names and
stores business values as strings. dbt Bronze models rename and type this data.
The layout is compatible with a BigQuery external table using Hive partitioning:

    output/instruments/dt=YYYY-MM-DD/data.parquet
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
DEFECT_KINDS = frozenset({"unsupported-code", "duplicate", "blank-required"})


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise typer.BadParameter("Expected an ISO date, e.g. 2026-08-18") from error


def parse_defects(
    values: list[str], partition_start: date, days: int
) -> dict[date, set[str]]:
    """Validate repeated DATE:KIND options and group them by partition date."""
    partition_end = partition_start + timedelta(days=days - 1)
    defects: dict[date, set[str]] = {}

    for value in values:
        date_text, separator, kind = value.partition(":")
        if not separator:
            raise typer.BadParameter(
                "Expected DATE:KIND, e.g. 2026-08-15:duplicate.",
                param_hint="--defect",
            )

        defect_date = parse_date(date_text)
        if kind not in DEFECT_KINDS:
            allowed_kinds = ", ".join(sorted(DEFECT_KINDS))
            raise typer.BadParameter(
                f"Unknown defect kind '{kind}'. Choose one of: {allowed_kinds}.",
                param_hint="--defect",
            )
        if not partition_start <= defect_date <= partition_end:
            raise typer.BadParameter(
                "Defect date must be within "
                f"{partition_start} through {partition_end}.",
                param_hint="--defect",
            )

        defects.setdefault(defect_date, set()).add(kind)

    return defects


def state_for_change(
    instrument_id: int, name: str, currency: str, exchange: str, offset: int
) -> tuple[str, str, str]:
    """Return deterministic SCD changes while leaving other records unchanged."""
    if instrument_id == 1001 and offset >= 1:
        return "Acme Holdings", currency, exchange
    if instrument_id == 1002 and offset >= 2:
        return "Northwind Global Bond", "USD", "XNYS"
    if instrument_id == 1004 and offset >= 3:
        return name, currency, "XLON"
    if instrument_id == 1003 and offset >= 4:
        return "Global Innovation ETF", currency, exchange
    return name, currency, exchange


def rows_for_day(
    day: date, rows_per_day: int, offset: int, defects: set[str]
) -> list[dict[str, str]]:
    """Create an upstream-style instrument change batch for one partition."""
    day_start = datetime.combine(day, time(hour=10), tzinfo=timezone.utc)
    rows: list[dict[str, str]] = []

    for instrument_id, name, currency, exchange in INSTRUMENTS[:rows_per_day]:
        instrument_name, currency_code, exchange_code = state_for_change(
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
                "sourceUpdatedAt": (effective_at + timedelta(minutes=5))
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )

    if "unsupported-code" in defects:
        rows.append(
            {
                "instrumentId": " 9001 ",
                "instrumentName": " Unsupported market instrument ",
                "currencyCode": "zzz",
                "exchangeCode": "xbad",
                "effectiveAt": (day_start + timedelta(minutes=45))
                .isoformat()
                .replace("+00:00", "Z"),
                "sourceUpdatedAt": (day_start + timedelta(minutes=50))
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )

    if "duplicate" in defects:
        rows.append(rows[0].copy())

    if "blank-required" in defects:
        rows.append(
            {
                "instrumentId": " 9002 ",
                "instrumentName": " ",
                "currencyCode": "usd",
                "exchangeCode": "xnas",
                "effectiveAt": (day_start + timedelta(minutes=46))
                .isoformat()
                .replace("+00:00", "Z"),
                "sourceUpdatedAt": (day_start + timedelta(minutes=51))
                .isoformat()
                .replace("+00:00", "Z"),
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
                "(default: data/instruments)"
            )
        ),
    ] = Path("data/instruments"),
    start_date: Annotated[
        str, typer.Option(help="First partition date in ISO YYYY-MM-DD format.")
    ] = DEFAULT_START_DATE,
    days: Annotated[
        int, typer.Option(help="Number of daily change batches to create.")
    ] = DEFAULT_DAYS,
    rows_per_day: Annotated[
        int, typer.Option(help="Number of valid instrument records per batch.")
    ] = DEFAULT_ROWS_PER_DAY,
    seed: Annotated[
        int,
        typer.Option(help="Retained for CLI compatibility; fixture values are fixed."),
    ] = 42,
    defect: Annotated[
        list[str] | None,
        typer.Option(
            "--defect",
            help=(
                "Add DATE:KIND defect; repeat as needed. KIND is unsupported-code, "
                "duplicate, or blank-required."
            ),
        ),
    ] = None,
) -> None:
    """Generate deterministic instrument change Parquet files."""
    partition_start = parse_date(start_date)

    if days < 1:
        raise typer.BadParameter("Must be at least 1.", param_hint="--days")
    if rows_per_day < 1:
        raise typer.BadParameter("Must be at least 1.", param_hint="--rows-per-day")
    if rows_per_day > len(INSTRUMENTS):
        raise typer.BadParameter(
            f"Must be at most {len(INSTRUMENTS)} for one record per instrument/batch.",
            param_hint="--rows-per-day",
        )
    del seed
    defects_by_date = parse_defects(defect or [], partition_start, days)

    for offset in range(days):
        partition_date = partition_start + timedelta(days=offset)
        rows = rows_for_day(
            partition_date,
            rows_per_day,
            offset,
            defects_by_date.get(partition_date, set()),
        )
        output_file = write_partition(output_dir, partition_date, rows)
        typer.echo(f"Wrote {len(rows)} rows to {output_file}")


if __name__ == "__main__":
    app()
