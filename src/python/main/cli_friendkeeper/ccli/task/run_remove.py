"""Remove a contact.

Usage:
    friend remove <name> [--force]

Removes *name* from friends.jsonl and records a tombstone in state.jsonl.
Without ``--force`` the user is prompted for confirmation.
"""

from __future__ import annotations

import typer

from cli_friendkeeper.errors import ContactNotFoundError
from cli_friendkeeper.models import ContactState, LogEntry
from cli_friendkeeper.store import flock_exclusive


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend remove <name> [--force]",
        err=True,
    )


def run(args: list[str], ctx: object) -> int:
    """Parse *args* and remove the named contact through *ctx*.

    Returns 0 on success, 1 on any error (missing name, not found,
    already removed, etc.).
    """
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0

    name: str | None = None
    force = False

    i = 0
    while i < len(args):
        if args[i] == "--force":
            force = True
            i += 1
        elif name is None:
            name = args[i]
            i += 1
        else:
            typer.echo(f"Unexpected argument: {args[i]}", err=True)
            return 1

    if not name:
        typer.echo("Error: contact name is required", err=True)
        return 1

    if not force:
        answer = input(f"Remove '{name}'? [y/N] ").strip().lower()
        if answer != "y":
            typer.echo("Cancelled.")
            return 0

    contact_result = ctx.contacts.get(name)  # type: ignore[attr-defined]
    if contact_result.is_left():
        err = contact_result.monoid[0]
        if isinstance(err, ContactNotFoundError):
            typer.echo(f"Error: contact '{name}' not found", err=True)
        else:
            typer.echo(f"Error: {err}", err=True)
        return 1

    with flock_exclusive(ctx.data_dir / "state.lock"):  # type: ignore[attr-defined]
        state_result = ctx.states.get(name)  # type: ignore[attr-defined]
        if state_result.is_right() and state_result.value.removed:
            typer.echo(f"Error: contact '{name}' already removed", err=True)
            return 1

        remove_result = ctx.contacts.remove(name)  # type: ignore[attr-defined]
        if remove_result.is_left():
            err = remove_result.monoid[0]
            typer.echo(f"Error: {err}", err=True)
            return 1

        tombstone = ContactState(
            name=name,
            removed=True,
            removed_at=ctx.clock.today(),  # type: ignore[attr-defined]
        )
        ctx.states.upsert(tombstone)  # type: ignore[attr-defined]

    entry = LogEntry(
        timestamp=ctx.clock.now(),  # type: ignore[attr-defined]
        action="remove",
        name=name,
    )
    ctx.log.append(entry)  # type: ignore[attr-defined]

    typer.echo(f"Removed: {name}")
    return 0
