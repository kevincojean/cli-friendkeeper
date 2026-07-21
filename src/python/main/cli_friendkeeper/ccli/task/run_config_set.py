"""config-set subcommand: set a configuration key and persist."""

from __future__ import annotations

import typer

from cli_friendkeeper.ccli.ccli import Context
from cli_friendkeeper.config import VALID_PRIORITIES, VALID_SUBCOMMANDS, load_config, save_config


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend config-set <key> <value>",
        err=True,
    )


def run(args: list[str], ctx: Context) -> int:
    """Set a config key and persist to disk.

    Supports keys:
      - ``cadence.<priority>`` — set cadence days for a priority
      - ``default_priority`` — set the default priority for new contacts
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

    # default_priority (no sub-key)
    if len(parts) == 1 and parts[0] == "default_priority":
        if value not in VALID_PRIORITIES:
            typer.echo(
                f"Error: {value!r} is not a valid priority; "
                f"choose from {', '.join(sorted(VALID_PRIORITIES))}",
                err=True,
            )
            return 1
        cfg = load_config()
        cfg.default_priority = value
        save_config(cfg)
        typer.echo(f"Set default_priority = {value}")
        return 0

    # default_subcommand
    if len(parts) == 1 and parts[0] == "default_subcommand":
        if value not in VALID_SUBCOMMANDS:
            typer.echo(
                f"Error: {value!r} is not a valid subcommand; "
                f"choose from {', '.join(sorted(VALID_SUBCOMMANDS))}",
                err=True,
            )
            return 1
        cfg = load_config()
        cfg.default_subcommand = value
        save_config(cfg)
        typer.echo(f"Set default_subcommand = {value}")
        return 0

    # cadence.<priority>
    if len(parts) == 2 and parts[0] == "cadence" and parts[1] in VALID_PRIORITIES:
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

    # snooze.<priority>
    if len(parts) == 2 and parts[0] == "snooze" and parts[1] in VALID_PRIORITIES:
        try:
            int_val = int(value)
        except ValueError:
            typer.echo(f"Error: {value} is not a valid integer", err=True)
            return 1

        cfg = load_config()
        if cfg.snooze is None:
            from cli_friendkeeper.config import DEFAULT_SNOOZE
            cfg.snooze = dict(DEFAULT_SNOOZE)
        cfg.snooze[parts[1]] = int_val
        save_config(cfg)
        typer.echo(f"Set {key} = {int_val}")
        return 0

    typer.echo(f"Error: Unknown config key: {key}", err=True)
    return 1
