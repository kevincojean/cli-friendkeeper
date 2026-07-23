"""Remove a contact.

Usage:
    friend remove <id> [--force]

Removes *contact* from friends.jsonl and records a tombstone in state.jsonl.
Without ``--force`` the user is prompted for confirmation.

The *id* argument accepts a unique ID prefix — if the prefix matches exactly
one contact it is resolved automatically; otherwise the command refuses and
asks for more digits.
"""

from __future__ import annotations

from pymonad.either import Either, Left, Right

import typer

from cli_friendkeeper.errors import ContactNotFoundError, FriendError
from cli_friendkeeper.models import Contact, ContactState, LogEntry
from cli_friendkeeper.store import flock_exclusive


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend remove <id> [--force]",
        err=True,
    )


def _resolve_id(raw: str, contacts: list[Contact]) -> Either[FriendError, tuple[Contact, str]]:
    """Resolve *raw* to a ``(contact, full_id)`` pair.

    Exact match is tried first; if that fails the input is treated as a
    prefix.  Returns ``Right`` only when the prefix matches **exactly one**
    contact, otherwise a descriptive error.
    """
    for c in contacts:
        if c.id == raw:
            return Right((c, c.id))
    matches = [c for c in contacts if c.id.startswith(raw)]
    if len(matches) == 1:
        c = matches[0]
        return Right((c, c.id))
    if not matches:
        return Left(ContactNotFoundError(f"Contact '{raw}' not found", contact_id=raw))
    names = ", ".join(f"'{c.name}' ({c.id[:8]})" for c in matches)
    return Left(
        FriendError(f"'{raw}' matches {len(matches)} contacts: {names}. Specify more digits.")
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

    resolution = _resolve_id(contact_id, ctx.contacts.all())  # type: ignore[attr-defined]
    if resolution.is_left():
        err = resolution.monoid[0]
        typer.echo(f"Error: {err}", err=True)
        return 1

    contact, contact_id = resolution.value

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
