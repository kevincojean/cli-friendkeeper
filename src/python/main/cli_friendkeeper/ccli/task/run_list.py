"""List subcommand — list all contacts with optional filtering.

Usage:
    friend list [--priority <prio>] [--all] [--json]

Parses flags, retrieves contacts, and prints a table (or JSON) sorted by
days-since-touched descending (most overdue first), then name ascending.
"""

from __future__ import annotations

import json

import typer

from cli_friendkeeper.ccli.ccli import Context
from cli_friendkeeper.check_logic import days_since_touched, is_due
from cli_friendkeeper.config import effective_cadence
from cli_friendkeeper.models import Contact, ContactState


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend list [--priority <prio>] [--all] [--json]",
        err=True,
    )


def run(args: list[str], ctx: Context) -> int:
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0
    priority_filter: str | None = None
    show_all = False
    as_json = False

    i = 0
    while i < len(args):
        if args[i] == "--priority" and i + 1 < len(args):
            priority_filter = args[i + 1]
            i += 2
        elif args[i] == "--all":
            show_all = True
            i += 1
        elif args[i] == "--json":
            as_json = True
            i += 1
        else:
            typer.echo(f"Unknown flag: {args[i]}", err=True)
            return 1

    contacts = ctx.contacts.all()
    raw_states = ctx.states.all()
    states = {s.name: s for s in raw_states}
    today = ctx.clock.today()

    if not contacts:
        typer.echo("No contacts yet.")
        return 0

    # Default: exclude removed contacts unless --all
    if not show_all:
        contacts = [
            c
            for c in contacts
            if not states.get(c.name, ContactState(name=c.name)).removed
        ]

    if not contacts:
        typer.echo("No contacts yet.")
        return 0

    if priority_filter is not None:
        contacts = [c for c in contacts if c.priority == priority_filter]

    if not contacts:
        typer.echo("No contacts yet.")
        return 0

    # Sort: days_since_touched desc (None = 9999), then name asc
    contacts = sorted(
        contacts,
        key=lambda c: (
            -(days_since_touched(
                states.get(c.name, ContactState(name=c.name)), today
            )
            or 9999),
            c.name.lower(),
        ),
    )

    if as_json:
        output: list[dict[str, object]] = []
        for c in contacts:
            state = states.get(c.name, ContactState(name=c.name))
            ds = days_since_touched(state, today)
            cadence = effective_cadence(ctx.config, c.priority, c.cadence_days)
            d: dict[str, object] = {
                "name": c.name,
                "display_name": c.display_name,
                "priority": c.priority,
                "days_since_touched": ds,
                "last_touched": (
                    state.last_touched.isoformat()
                    if state.last_touched
                    else None
                ),
                "cadence": cadence,
                "due": is_due(state, c, today, cadence),
                "removed": state.removed,
            }
            output.append(d)
        typer.echo(json.dumps(output, indent=2))
    else:
        _print_table(contacts, states, today, ctx)

    return 0


def _print_table(
    contacts: list[Contact],
    states: dict[str, ContactState],
    today: object,
    ctx: Context,
) -> None:
    date_fmt = "%Y-%m-%d"
    header = (
        f"{'Name':<20} {'Display Name':<25} {'Priority':<10} "
        f"{'Days Since':<12} {'Last Touched':<15} {'Cadence':<8} {'Due?':<6}"
    )
    sep = "-" * len(header)

    typer.echo(header)
    typer.echo(sep)

    for c in contacts:
        state = states.get(c.name, ContactState(name=c.name))
        ds = days_since_touched(state, today)
        cadence = effective_cadence(ctx.config, c.priority, c.cadence_days)
        due = is_due(state, c, today, cadence)

        days_str = f"{ds}" if ds is not None else "Never"
        last_str = (
            state.last_touched.strftime(date_fmt)
            if state.last_touched
            else "—"
        )
        due_str = "Y" if due else "N"

        typer.echo(
            f"{c.name:<20} {c.display_name:<25} {c.priority:<10} "
            f"{days_str:<12} {last_str:<15} {cadence:<8} {due_str:<6}"
        )
