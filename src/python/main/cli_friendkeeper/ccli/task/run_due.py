"""Due subcommand — show contacts that are overdue for contact.

Usage:
    friend due [--priority <prio>] [--limit <N>] [--json]

Parses flags, calls ``check_logic.select_due``, and prints a table
(or JSON) of the due contacts sorted by days-since-touched descending.
"""

from __future__ import annotations

import json

import typer

from cli_friendkeeper.check_logic import days_since_touched, select_due
from cli_friendkeeper.ccli.ccli import Context


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend due [--priority <prio>] [--limit <N>] [--json]",
        err=True,
    )


def run(args: list[str], ctx: Context) -> int:
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0
    priority_filter: str | None = None
    limit: int | None = None
    as_json = False

    i = 0
    while i < len(args):
        if args[i] == "--priority" and i + 1 < len(args):
            priority_filter = args[i + 1]
            i += 2
        elif args[i] == "--limit" and i + 1 < len(args):
            try:
                limit = int(args[i + 1])
            except ValueError:
                typer.echo(f"Invalid limit value: {args[i + 1]}", err=True)
                return 1
            i += 2
        elif args[i] == "--json":
            as_json = True
            i += 1
        else:
            typer.echo(f"Unknown flag: {args[i]}", err=True)
            return 1

    contacts = ctx.contacts.all()
    raw_states = ctx.states.all()
    states = {s.id: s for s in raw_states}
    today = ctx.clock.today()

    due = select_due(contacts, states, today, ctx.config)

    if priority_filter is not None:
        due = [c for c in due if c.priority == priority_filter]

    if limit is not None and limit > 0:
        due = due[:limit]

    if not due:
        typer.echo("Nothing due.")
        return 0

    if as_json:
        output: list[dict[str, object]] = []
        for c in due:
            state = states.get(c.id)
            d: dict[str, object] = {
                "id": c.id,
                "name": c.name,
                "priority": c.priority,
            }
            if state is not None:
                d["days_since_touched"] = days_since_touched(state, today)
                d["last_touched"] = (
                    state.last_touched.isoformat()
                    if state.last_touched
                    else None
                )
            else:
                d["days_since_touched"] = None
                d["last_touched"] = None
            output.append(d)
        typer.echo(json.dumps(output, indent=2))
    else:
        _print_table(due, states, today)

    return 0


def _print_table(
    due: list,
    states: dict[str, object],
    today: object,
) -> None:
    from cli_friendkeeper.models import Contact, ContactState

    date_fmt = "%Y-%m-%d"
    header = f"{'ID':<10} {'Name':<20} {'Priority':<10} {'Days Since':<12} {'Last Touched':<15}"
    sep = "-" * len(header)

    typer.echo(header)
    typer.echo(sep)

    for c in due:
        assert isinstance(c, Contact)
        state = states.get(c.id)
        if state is not None:
            assert isinstance(state, ContactState)
            ds = days_since_touched(state, today)
            days_str = f"{ds}" if ds is not None else "Never"
            last_str = (
                state.last_touched.strftime(date_fmt)
                if state.last_touched
                else "—"
            )
        else:
            days_str = "Never"
            last_str = "—"

        typer.echo(
            f"{c.id[:8]:<10} {c.name:<20} {c.priority:<10} {days_str:<12} {last_str:<15}"
        )
