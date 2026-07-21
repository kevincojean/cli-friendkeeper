"""config-show subcommand: display current configuration."""

from __future__ import annotations

import json as json_lib

import typer

from cli_friendkeeper.ccli.ccli import Context
from cli_friendkeeper.config import DEFAULT_CADENCE, DEFAULT_SNOOZE, VALID_PRIORITIES
from cli_friendkeeper.paths import config_file


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend config-show",
        err=True,
    )


def _show(key: str, value: object) -> None:
    typer.echo(f"  {key} = {value}")


def run(args: list[str], ctx: Context) -> int:
    """Show current config: file path, effective settings, and defaults."""
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0

    if args:
        typer.echo(f"Unknown flag: {args[0]}", err=True)
        return 1

    cfg = ctx.config

    typer.echo(f"Config file: {config_file()}")
    typer.echo("")

    # Effective settings in flat format
    typer.echo("Effective settings (flat dot-format keys):")
    for prio in sorted(VALID_PRIORITIES, key=lambda p: (
        ("deep", "casual", "network", "acquaintance").index(p) if p in ("deep", "casual", "network", "acquaintance") else 9
    )):
        _show(f"cadence.{prio}", cfg.cadence.get(prio, DEFAULT_CADENCE.get(prio)))
    for prio in sorted(VALID_PRIORITIES, key=lambda p: (
        ("deep", "casual", "network", "acquaintance").index(p) if p in ("deep", "casual", "network", "acquaintance") else 9
    )):
        snooze_val = (cfg.snooze or DEFAULT_SNOOZE).get(prio, DEFAULT_SNOOZE.get(prio))
        if snooze_val is not None:
            _show(f"snooze.{prio}", snooze_val)
    _show("default_priority", cfg.default_priority)
    _show("default_subcommand", cfg.default_subcommand)
    _show("list.hide_acquaintances", cfg.list_hide_acquaintances)
    _show("list.sort_priority", cfg.list_sort_priority)
    _show("list.sort_due_date", cfg.list_sort_due_date)
    _show("list.columns", cfg.list_columns)
    _show("list.priority_order", cfg.priority_order)

    typer.echo("")

    # Raw file contents if present
    cf = config_file()
    if cf.exists():
        try:
            raw = json_lib.loads(cf.read_text())
            typer.echo("Raw config file:")
            typer.echo(json_lib.dumps(raw, indent=2))
        except Exception:
            pass
    else:
        typer.echo("(no config file — all defaults active)")

    return 0
