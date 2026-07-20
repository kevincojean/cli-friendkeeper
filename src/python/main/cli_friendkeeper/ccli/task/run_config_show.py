"""config-show subcommand: display current configuration."""

from __future__ import annotations

import json

import typer

from cli_friendkeeper.ccli.ccli import Context
from cli_friendkeeper.config import DEFAULT_CADENCE, VALID_PRIORITIES
from cli_friendkeeper.paths import config_file


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend config-show",
        err=True,
    )


def run(args: list[str], ctx: Context) -> int:
    """Show current config: file path, JSON, defaults, effective cadences."""
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0

    if args:
        typer.echo(f"Unknown flag: {args[0]}", err=True)
        return 1

    typer.echo(f"Config file: {config_file()}")
    typer.echo("")

    typer.echo("Current cadence configuration:")
    typer.echo(json.dumps(ctx.config.cadence, indent=2))
    typer.echo("")

    typer.echo("Default cadence values:")
    typer.echo(json.dumps(DEFAULT_CADENCE, indent=2))
    typer.echo("")

    typer.echo("Effective cadence per priority:")
    for priority in sorted(VALID_PRIORITIES):
        effective = ctx.config.cadence.get(priority, DEFAULT_CADENCE[priority])
        typer.echo(f"  {priority}: {effective} days")

    return 0
