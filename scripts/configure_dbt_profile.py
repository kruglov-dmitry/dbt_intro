#!/usr/bin/env python3
"""Create a participant-local dbt profile for the workshop."""

from __future__ import annotations

import re
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)

DATASET_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,1023}$")


@app.command()
def configure(
    project_id: str = typer.Option(
        ..., help="GCP project that contains workshop resources."
    ),
    dataset: str = typer.Option(
        ..., help="Participant-owned BigQuery dataset, e.g. workshop_alice."
    ),
    location: str = typer.Option("EU", help="BigQuery location."),
    force: bool = typer.Option(False, help="Replace an existing local profiles.yml."),
) -> None:
    """Write dbt-workshop/profiles.yml from the committed template."""
    if not DATASET_PATTERN.fullmatch(dataset):
        typer.echo(
            "Dataset must start with a letter or underscore and contain only "
            "letters, numbers, and underscores.",
            err=True,
        )
        raise typer.Exit(code=2)

    project_root = Path(__file__).resolve().parents[1]
    template_path = project_root / "dbt-workshop" / "profiles.yml.example"
    output_path = project_root / "dbt-workshop" / "profiles.yml"

    if not template_path.is_file():
        typer.echo(f"Profile template not found: {template_path}", err=True)
        raise typer.Exit(code=1)

    if output_path.exists() and not force:
        typer.echo(
            f"Profile already exists: {output_path} (use --force to replace it)",
            err=True,
        )
        raise typer.Exit(code=1)

    contents = template_path.read_text()
    for placeholder, value in {
        "__GCP_PROJECT_ID__": project_id,
        "__BQ_DATASET__": dataset,
        "__BQ_LOCATION__": location,
    }.items():
        contents = contents.replace(placeholder, value)

    output_path.write_text(contents)
    typer.echo(f"Wrote {output_path}")
    typer.echo("\nNext steps:")
    typer.echo(f"  cd {project_root / 'dbt-workshop'}")
    typer.echo("  python3 -m pip install -r requirements.txt")
    typer.echo("  dbt run-operation create_workshop_dataset --profiles-dir .")
    typer.echo("  dbt debug --profiles-dir .")


if __name__ == "__main__":
    app()
