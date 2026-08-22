#!/usr/bin/env python3
"""Display the physical schema and sample rows of a local Parquet file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import pyarrow.parquet as pq
import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def inspect(
    file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Local .parquet file to inspect.",
        ),
    ],
    limit: Annotated[
        int, typer.Option(min=1, help="Maximum number of rows to display.")
    ] = 5,
) -> None:
    """Print a Parquet file's schema and first rows."""
    parquet_file = pq.ParquetFile(file)
    table = parquet_file.read()

    typer.echo(f"File: {file}")
    typer.echo(f"Rows: {table.num_rows}")
    typer.echo("\nSchema:")
    typer.echo(str(table.schema))
    typer.echo(f"\nFirst {min(limit, table.num_rows)} row(s):")

    for row in table.slice(0, limit).to_pylist():
        typer.echo(json.dumps(row, default=str, sort_keys=True))


if __name__ == "__main__":
    app()
