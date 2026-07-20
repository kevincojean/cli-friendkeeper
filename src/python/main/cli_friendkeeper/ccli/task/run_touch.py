"""Touch subcommand — mark a contact as contacted.

Usage:
    friend touch <name> [--note <text>]

Updates the contact state (last_touched, touch_count) and appends a log entry,
all within an exclusive flock on ``state.lock`` for read-modify-write safety.
"""

from __future__ import annotations

import typer

from cli_friendkeeper.errors import ContactNotFoundError
from cli_friendkeeper.models import ContactState, LogEntry
from cli_friendkeeper.store import flock_exclusive


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend touch <name> [--note <text>]",
        err=True,
    )


def run(args: list[str], ctx: object) -> int:
    """Parse *args* and touch the named contact.

    Returns 0 on success, 1 on any error (contact not found, removed
    contact, invalid flags, etc.).
    """
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0

    name: str | None = None
    note: str = ""

    i = 0
    while i < len(args):
        if args[i] == "--note" and i + 1 < len(args):
            note = args[i + 1]
            i += 2
        elif args[i].startswith("--"):
            typer.echo(f"Unknown flag: {args[i]}", err=True)
            return 1
        else:
            if name is None:
                name = args[i]
                i += 1
            else:
                typer.echo(f"Unexpected argument: {args[i]}", err=True)
                return 1

    if not name:
        typer.echo("Error: contact name is required", err=True)
        return 1

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
        if state_result.is_left():
            err = state_result.monoid[0]
            if isinstance(err, ContactNotFoundError):
                state = ContactState(name=name)
            else:
                typer.echo(f"Error: {err}", err=True)
                return 1
        else:
            state = state_result.value

        if state.removed:
            typer.echo(
                f"Error: contact '{name}' has been removed",
                err=True,
            )
            return 1

        state.last_touched = ctx.clock.today()  # type: ignore[attr-defined]
        state.touch_count += 1
        ctx.states.upsert(state)  # type: ignore[attr-defined]

    entry = LogEntry(
        timestamp=ctx.clock.now(),  # type: ignore[attr-defined]
        action="touch",
        name=name,
        payload={"note": note},
    )
    ctx.log.append(entry)  # type: ignore[attr-defined]

    last_touched_str = (
        state.last_touched.isoformat() if state.last_touched else "never"
    )
    typer.echo(
        f"Touched: {name} "
        f"(last_touched: {last_touched_str}, "
        f"total: {state.touch_count})"
    )
    return 0
