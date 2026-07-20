"""Add a new contact.

Usage:
    friend add --name <display-name> [--email <email>] [--phone <number>]
               [--priority <deep|casual|network>] [--cadence-days <n>]
               [--notes <text>]
"""

from __future__ import annotations

from typing import Any

import typer

from cli_friendkeeper.errors import ContactAlreadyExistsError, InvalidEmailError
from cli_friendkeeper.models import Contact, LogEntry


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend add --name <display-name> [--email <email>] [--phone <number>]"
        " [--priority <deep|casual|network>] [--cadence-days <n>] [--notes <text>]",
        err=True,
    )


def run(args: list[str], ctx: Any) -> int:
    """Parse *args* and add a new contact through *ctx*.

    Returns 0 on success, 1 on any error (missing required fields,
    validation failure, duplicate contact, etc.).
    """
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0

    name_val: str | None = None
    display_name_val: str | None = None
    email_val: str | None = None
    phone_val: str | None = None
    priority_val: str = "casual"
    cadence_days_val: int | None = None
    notes_val: str = ""

    i = 0
    while i < len(args):
        if args[i] == "--name" and i + 1 < len(args):
            display_name_val = args[i + 1]
            # Keep spaces through the filter so .replace(" ", "-") works
            name_val = "".join(
                c.lower() for c in display_name_val if c.isalnum() or c in "-_ "
            ).replace(" ", "-")
            i += 2
        elif args[i] == "--email" and i + 1 < len(args):
            email_val = args[i + 1]
            i += 2
        elif args[i] == "--phone" and i + 1 < len(args):
            phone_val = args[i + 1]
            i += 2
        elif args[i] == "--priority" and i + 1 < len(args):
            priority_val = args[i + 1]
            i += 2
        elif args[i] == "--cadence-days" and i + 1 < len(args):
            cadence_days_val = int(args[i + 1])
            i += 2
        elif args[i] == "--notes" and i + 1 < len(args):
            notes_val = args[i + 1]
            i += 2
        elif args[i].startswith("--"):
            typer.echo(f"Unknown flag: {args[i]}", err=True)
            return 1
        else:
            i += 1

    if not name_val:
        typer.echo("Error: --name is required", err=True)
        return 1

    if not email_val and not phone_val:
        typer.echo("Error: at least one of --email or --phone is required", err=True)
        return 1

    contact = Contact(
        name=name_val,
        display_name=display_name_val or name_val,
        email=email_val,
        phone=phone_val,
        priority=priority_val,  # type: ignore[arg-type]
        cadence_days=cadence_days_val,
        notes=notes_val,
        added_at=ctx.clock.today(),
    )

    try:
        contact.validate()
    except InvalidEmailError as e:
        typer.echo(f"Error: invalid email: {e}", err=True)
        return 1

    result = ctx.contacts.add(contact)
    if result.is_left():
        err = result.monoid[0]
        if isinstance(err, ContactAlreadyExistsError):
            typer.echo(f"Error: contact '{name_val}' already exists", err=True)
        else:
            typer.echo(f"Error: {err}", err=True)
        return 1

    entry = LogEntry(
        timestamp=ctx.clock.now(),
        action="add",
        name=name_val,
        payload={
            "email": email_val,
            "phone": phone_val,
            "priority": priority_val,
        },
    )
    ctx.log.append(entry)

    typer.echo(f"Added: {name_val} ({display_name_val or name_val})")
    return 0
