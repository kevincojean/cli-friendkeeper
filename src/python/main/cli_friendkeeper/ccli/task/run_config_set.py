"""config-set subcommand: set a configuration key and persist."""

from __future__ import annotations

import typer

from cli_friendkeeper.ccli.ccli import Context
from cli_friendkeeper.config import VALID_PRIORITIES, load_config, save_config


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend config-set <key> <value>",
        err=True,
    )


def run(args: list[str], ctx: Context) -> int:
    """Set a config key to an integer value and persist to disk.

    Supports keys of the form ``cadence.<priority>`` where ``priority``
    is one of ``VALID_PRIORITIES``.
    """
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0

    if args and args[0].startswith("--") and args[0] not in ("--help", "-h"):
        typer.echo(f"Unknown flag: {args[0]}", err=True)
        return 1

    if len(args) != 2:
        typer.echo("Error: usage: friend config-set <key> <value>", err=True)
        return 1

    key, value = args

    parts = key.split(".")
    if len(parts) != 2 or parts[0] != "cadence" or parts[1] not in VALID_PRIORITIES:
        typer.echo(f"Error: Unknown config key: {key}", err=True)
        return 1

    try:
        int_val = int(value)
    except ValueError:
        typer.echo(f"Error: {value} is not a valid integer", err=True)
        return 1

    cfg = load_config()
    cfg.cadence[parts[1]] = int_val
    save_config(cfg)

    typer.echo(f"Set {key} = {int_val}")
    return 0
