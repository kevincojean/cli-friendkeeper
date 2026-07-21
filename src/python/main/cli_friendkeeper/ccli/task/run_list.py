"""List subcommand — list all contacts with optional filtering.

Usage:
    friend list [--priority <prio>] [--all] [--acquaintances] [--json]

Parses flags, retrieves contacts, and prints a table (or JSON) sorted by
priority group (configurable order/direction), then due date, then name.
Acquaintance-priority contacts are hidden by default.
"""

from __future__ import annotations

import json
from datetime import date

import typer

from cli_friendkeeper.ccli.ccli import Context
from cli_friendkeeper.check_logic import days_since_touched, due_date
from cli_friendkeeper.config import DEFAULT_PRIORITY_ORDER, effective_cadence
from cli_friendkeeper.models import Contact, ContactState


def _due_sort_key(dd: date | None, direction: str) -> int:
    """Return a numeric sort key for due date.

    For ``asc``: earliest date first (ordinal, None at end).
    For ``desc``: latest date first (negated ordinal, None at end).
    """
    if dd is not None:
        return dd.toordinal() if direction == "asc" else -dd.toordinal()
    # None — always at the end
    return date.max.toordinal() if direction == "asc" else 0


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend list [--priority <prio>] [--all] [--acquaintances] [--json]",
        err=True,
    )


def run(args: list[str], ctx: Context) -> int:
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0
    priority_filter: str | None = None
    show_all = False
    as_json = False
    show_acquaintances = False

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
        elif args[i] == "--acquaintances":
            show_acquaintances = True
            i += 1
        else:
            typer.echo(f"Unknown flag: {args[i]}", err=True)
            return 1

    contacts = ctx.contacts.all()
    raw_states = ctx.states.all()
    states = {s.id: s for s in raw_states}
    today = ctx.clock.today()

    if not contacts:
        typer.echo("No contacts yet.")
        return 0

    # Default: exclude removed contacts unless --all
    if not show_all:
        contacts = [
            c
            for c in contacts
            if not states.get(c.id, ContactState(id=c.id, name=c.name)).removed
        ]

    if not contacts:
        typer.echo("No contacts yet.")
        return 0

    # Default: hide acquaintances unless --acquaintances or config override
    if not show_acquaintances and ctx.config.list_hide_acquaintances:
        contacts = [c for c in contacts if c.priority != "acquaintance"]

    if not contacts:
        typer.echo("No contacts yet.")
        return 0

    if priority_filter is not None:
        contacts = [c for c in contacts if c.priority == priority_filter]

    if not contacts:
        typer.echo("No contacts yet.")
        return 0

    # Sort: by priority order (configurable direction), then due date, then name
    priority_order = list(ctx.config.priority_order or DEFAULT_PRIORITY_ORDER)
    priority_idx = {p: i for i, p in enumerate(priority_order)}
    pri_dir = ctx.config.list_sort_priority or "asc"
    due_dir = ctx.config.list_sort_due_date or "desc"

    contacts = sorted(
        contacts,
        key=lambda c: (
            # Priority key: index in priority_order, negated for DESC
            (priority_idx.get(c.priority, len(priority_order)))
            if pri_dir == "asc"
            else -(priority_idx.get(c.priority, len(priority_order))),
            # Due date key
            _due_sort_key(
                due_date(
                    states.get(c.id, ContactState(id=c.id, name=c.name)),
                    c,
                    today,
                    effective_cadence(ctx.config, c.priority, c.cadence_days),
                ),
                due_dir,
            ),
            c.name.lower(),
        ),
    )

    if as_json:
        output: list[dict[str, object]] = []
        for c in contacts:
            state = states.get(c.id, ContactState(id=c.id, name=c.name))
            ds = days_since_touched(state, today)
            cadence = effective_cadence(ctx.config, c.priority, c.cadence_days)
            dd = due_date(state, c, today, cadence)
            d: dict[str, object] = {
                "id": c.id,
                "name": c.name,
                "priority": c.priority,
                "days_since_touched": ds,
                "last_touched": (
                    state.last_touched.isoformat()
                    if state.last_touched
                    else None
                ),
                "cadence": cadence,
                "due_date": dd.isoformat() if dd is not None else None,
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
        f"{'ID':<10} {'Name':<20} {'Priority':<10} "
        f"{'Days Since':<12} {'Last Touched':<15} {'Cadence':<8} {'Due Date':<12}"
    )
    sep = "-" * len(header)

    typer.echo(header)
    typer.echo(sep)

    for c in contacts:
        state = states.get(c.id, ContactState(id=c.id, name=c.name))
        ds = days_since_touched(state, today)
        cadence = effective_cadence(ctx.config, c.priority, c.cadence_days)
        dd = due_date(state, c, today, cadence)

        days_str = f"{ds}" if ds is not None else "Never"
        last_str = (
            state.last_touched.strftime(date_fmt)
            if state.last_touched
            else "—"
        )
        due_str = dd.strftime(date_fmt) if dd is not None else "—"

        typer.echo(
            f"{c.id[:8]:<10} {c.name:<20} {c.priority:<10} "
            f"{days_str:<12} {last_str:<15} {cadence:<8} {due_str:<12}"
        )
