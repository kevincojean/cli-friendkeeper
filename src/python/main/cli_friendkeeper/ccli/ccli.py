"""CLI facade — dispatches to subcommand modules via lazy import.

Usage:
    friend <subcommand> [args]

Subcommands are loaded lazily from ``cli_friendkeeper.ccli.task.run_<verb>``,
each of which must export a ``run(args: list[str], ctx: Context) -> int``
function.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import typer

from cli_friendkeeper.clock import SystemClock
from cli_friendkeeper.config import load_config
from cli_friendkeeper.paths import data_dir
from cli_friendkeeper.repository import ContactRepo, LogRepo, StateRepo


class Context:
    """Holds application context: repos, clock, config."""

    def __init__(self, data_dir: Path) -> None:
        import cli_friendkeeper.store as store_module

        self.contacts = ContactRepo(store_module, data_dir)
        self.states = StateRepo(store_module, data_dir)
        self.log = LogRepo(store_module, data_dir)
        self.clock = SystemClock()
        self.config = load_config()
        self.data_dir = data_dir


def build_context(data_dir_override: Path | None = None) -> Context:
    """Build application context with optional override for data dir."""
    return Context(data_dir_override or data_dir())


def _print_help() -> None:
    """Print usage help to stderr."""
    typer.echo("Usage: friend <subcommand> [args]\n", err=True)
    typer.echo("Subcommands:", err=True)
    typer.echo("  add       Add a new contact", err=True)
    typer.echo("  list      List all contacts", err=True)
    typer.echo("  due       Show contacts that are due", err=True)
    typer.echo("  touch     Mark a contact as touched", err=True)
    typer.echo("  remove    Remove a contact", err=True)
    typer.echo("  rebuild-state  Rebuild state.jsonl from log.jsonl", err=True)
    typer.echo("  config-show    Show current config", err=True)
    typer.echo("  config-set     Set a config key", err=True)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns exit code."""
    if argv is None:
        argv = sys.argv[1:]

    if not argv or argv[0] in ("--help", "-h"):
        _print_help()
        return 0

    verb = argv[0]
    sub_args = argv[1:]

    try:
        module = importlib.import_module(
            f"cli_friendkeeper.ccli.task.run_{verb.replace('-', '_')}"
        )
    except ImportError:
        typer.echo(f"Unknown subcommand: {verb}", err=True)
        typer.echo("", err=True)
        _print_help()
        return 1

    ctx = build_context()
    return module.run(sub_args, ctx)
