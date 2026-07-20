"""Rebuild state.jsonl from log.jsonl by replaying all log entries.

Usage:
    friend rebuild-state [--dry-run]

Replays the full audit log to reconstruct the current state of every
contact, ignoring any existing (possibly corrupted) state.jsonl file.
"""

from __future__ import annotations

import typer

from cli_friendkeeper.ccli.ccli import Context
from cli_friendkeeper.models import ContactState
from cli_friendkeeper.store import write_jsonl_atomic


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend rebuild-state [--dry-run]",
        err=True,
    )


def run(args: list[str], ctx: Context) -> int:
    """Parse *args* and rebuild state from log through *ctx*.

    Returns 0 on success.
    """
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0

    dry_run = False
    i = 0
    while i < len(args):
        if args[i] == "--dry-run":
            dry_run = True
            i += 1
        elif args[i].startswith("--"):
            typer.echo(f"Unknown flag: {args[i]}", err=True)
            return 1
        else:
            i += 1

    entries = ctx.log.all()
    ctx.contacts.all()

    state_by_name: dict[str, ContactState] = {}

    for entry in entries:
        name = entry.name
        if entry.action == "add":
            if name not in state_by_name:
                state_by_name[name] = ContactState(
                    name=name,
                    last_touched=None,
                    touch_count=0,
                )
        elif entry.action == "touch":
            if name in state_by_name:
                state_by_name[name].last_touched = entry.timestamp.date()
                state_by_name[name].touch_count += 1
        elif entry.action == "remove":
            if name in state_by_name:
                state_by_name[name].removed = True
                state_by_name[name].removed_at = entry.timestamp.date()
        elif entry.action == "rebuild-state":
            pass

    if dry_run:
        typer.echo(f"Dry run: would rebuild state from {len(entries)} log entries.")
        return 0

    write_jsonl_atomic(
        ctx.data_dir / "state.jsonl",
        [s.to_dict() for s in state_by_name.values()],
    )
    typer.echo(f"Rebuilt state from {len(entries)} log entries.")
    return 0
