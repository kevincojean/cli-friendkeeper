"""Remove a contact.

Usage:
    friend remove <id> [--force]

Removes *contact* from friends.jsonl and records a tombstone in state.jsonl.
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
        "Usage: friend remove <id> [--force]",
        err=True,
    )


def run(args: list[str], ctx: object) -> int:
    """Parse *args* and remove the named contact through *ctx*.

    Returns 0 on success, 1 on any error (missing id, not found,
    already removed, etc.).
    """
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0

    contact_id: str | None = None
    force = False

    i = 0
    while i < len(args):
        if args[i] == "--force":
            force = True
            i += 1
        elif contact_id is None:
            contact_id = args[i]
            i += 1
        else:
            typer.echo(f"Unexpected argument: {args[i]}", err=True)
            return 1

    if not contact_id:
        typer.echo("Error: contact id is required", err=True)
        return 1

    contact_result = ctx.contacts.get(contact_id)  # type: ignore[attr-defined]
    if contact_result.is_left():
        err = contact_result.monoid[0]
        if isinstance(err, ContactNotFoundError):
            typer.echo(f"Error: contact '{contact_id}' not found", err=True)
        else:
            typer.echo(f"Error: {err}", err=True)
        return 1

    contact = contact_result.value

    if not force:
        answer = input(f"Remove '{contact.name}' (id: {contact_id})? [y/N] ").strip().lower()
        if answer != "y":
            typer.echo("Cancelled.")
            return 0

    with flock_exclusive(ctx.data_dir / "state.lock"):  # type: ignore[attr-defined]
        state_result = ctx.states.get(contact_id)  # type: ignore[attr-defined]
        if state_result.is_right() and state_result.value.removed:
            typer.echo(f"Error: contact '{contact.name}' already removed", err=True)
            return 1

        remove_result = ctx.contacts.remove(contact_id)  # type: ignore[attr-defined]
        if remove_result.is_left():
            err = remove_result.monoid[0]
            typer.echo(f"Error: {err}", err=True)
            return 1

        tombstone = ContactState(
            id=contact_id,
            name=contact.name,
            removed=True,
            removed_at=ctx.clock.today(),  # type: ignore[attr-defined]
        )
        ctx.states.upsert(tombstone)  # type: ignore[attr-defined]

    entry = LogEntry(
        timestamp=ctx.clock.now(),  # type: ignore[attr-defined]
        action="remove",
        id=contact_id,
        name=contact.name,
    )
    ctx.log.append(entry)  # type: ignore[attr-defined]

    typer.echo(f"Removed: {contact.name} (id: {contact_id})")
    return 0
