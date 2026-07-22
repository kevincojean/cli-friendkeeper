from __future__ import annotations

from datetime import timedelta

import typer

from cli_friendkeeper.check_logic import days_since_touched, select_due_catch_up
from cli_friendkeeper.ccli.ccli import Context
from cli_friendkeeper.config import effective_cadence, effective_snooze
from cli_friendkeeper.models import Contact, ContactState, LogEntry
from cli_friendkeeper.store import flock_exclusive


def _prompt(text: str) -> str:
    try:
        return input(text)
    except (EOFError, KeyboardInterrupt):
        return "q"


def _maybe_upgrade_acquaintance(
    ctx: Context, contact: Contact, state: ContactState, note: str, today: object
) -> bool:
    max_snoozes = (ctx.config.warm_up_max_snoozes or {}).get("acquaintance", 0)
    can_upgrade = (
        ctx.config.acquaintance_auto_upgrade
        and contact.auto_upgrade
        and state.snooze_count <= max_snoozes
    )
    if not can_upgrade:
        return False

    old_priority = contact.priority
    contact.priority = "casual"
    with flock_exclusive(ctx.data_dir / "state.lock"):
        ctx.contacts.update(contact)
        state.warm_up_consumed = True
        state.last_touched = today
        state.touch_count += 1
        ctx.states.upsert(state)

    entry = LogEntry(
        timestamp=ctx.clock.now(),
        action="upgrade",
        id=contact.id,
        name=contact.name,
        payload={"from": old_priority, "to": "casual", "note": note} if note else {"from": old_priority, "to": "casual"},
    )
    ctx.log.append(entry)
    return True


def _do_touch(ctx: Context, contact: Contact, state: ContactState, note: str, today: object) -> dict:
    warm_up_just_consumed = state.warm_up_consumed is False
    with flock_exclusive(ctx.data_dir / "state.lock"):
        state.last_touched = today
        state.touch_count += 1
        if warm_up_just_consumed:
            state.warm_up_consumed = True
        ctx.states.upsert(state)
    entry = LogEntry(
        timestamp=ctx.clock.now(),
        action="touch",
        id=contact.id,
        name=contact.name,
        payload={"note": note} if note else {},
    )
    ctx.log.append(entry)
    return {"warm_up_just_consumed": warm_up_just_consumed}


def _do_snooze(ctx: Context, contact: Contact, state: ContactState, days: int, today: object) -> dict:
    with flock_exclusive(ctx.data_dir / "state.lock"):
        state.last_touched = today + timedelta(days=days)
        state.snooze_count += 1
        max_snoozes = (ctx.config.warm_up_max_snoozes or {}).get(contact.priority, 999)
        relegated = state.snooze_count > max_snoozes
        if relegated:
            state.warm_up_consumed = True
        ctx.states.upsert(state)
    if relegated:
        entry = LogEntry(
            timestamp=ctx.clock.now(),
            action="relegate",
            id=contact.id,
            name=contact.name,
            payload={"snooze_count": state.snooze_count},
        )
        ctx.log.append(entry)
    return {
        "relegated": relegated and contact.priority == "acquaintance",
        "warm_up_consumed": relegated and contact.priority == "casual",
    }


def _print_usage() -> None:
    typer.echo("Usage: friend catch-up [N]", err=True)


def run(args: list[str], ctx: Context) -> int:
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0

    limit: int | None = None
    if args:
        try:
            limit = int(args[0])
        except ValueError:
            typer.echo(f"Invalid argument: {args[0]}", err=True)
            return 1

    contacts = ctx.contacts.all()
    raw_states = ctx.states.all()
    states = {s.id: s for s in raw_states}
    today = ctx.clock.today()

    due = select_due_catch_up(contacts, states, today, ctx.config)

    if limit is not None and limit > 0:
        due = due[:limit]

    if not due:
        typer.echo("Nothing to catch up on.")
        return 0

    touched = 0
    snoozed = 0

    for i, c in enumerate(due, 1):
        state = states.get(c.id, ContactState(id=c.id, name=c.name))
        ds = days_since_touched(state, today)
        days_str = f"{ds}d" if ds is not None else "never"
        note_text = c.notes if c.notes else "—"

        typer.echo("")
        typer.echo(f"[{i}/{len(due)}] {c.name:<20} {c.priority:<10} {days_str}  id={c.id[:8]}")
        typer.echo(f"       Notes: {note_text}")

        snooze_default = effective_snooze(ctx.config, c.priority)
        typer.echo("")
        typer.echo("  Have you caught up yet ?")
        typer.echo("  (y) Yes  (n) Nope  (s) Snooze  (q) Quit")

        quit_session = False
        while True:
            choice = _prompt("> ").strip().lower()

            if choice == "y":
                note = _prompt("Note: ").strip()
                if c.priority == "acquaintance" and state.warm_up_consumed is False:
                    upgraded = _maybe_upgrade_acquaintance(ctx, c, state, note, today)
                    if upgraded:
                        touched += 1
                        cadence = effective_cadence(ctx.config, "casual", c.cadence_days)
                        typer.echo(f"✓ {c.name} — upgraded from acquaintance to casual (warm-up cadence {cadence}d)")
                        typer.echo(f"  Upgraded {c.name} from acquaintance → casual")
                        break

                result = _do_touch(ctx, c, state, note, today)
                touched += 1
                if result["warm_up_just_consumed"] and c.priority == "casual":
                    cadence = effective_cadence(ctx.config, c.priority, c.cadence_days)
                    typer.echo(f"✓ {c.name} — touched (warm-up complete, regular cadence {cadence}d)")
                else:
                    typer.echo(f"✓ {c.name} — touched")
                break

            elif choice == "n":
                result = _do_snooze(ctx, c, state, 1, today)
                snoozed += 1
                if result["relegated"]:
                    typer.echo(f"✓ {c.name} — noped (1d) — relegated, cadence=0 (no-due)")
                elif result["warm_up_consumed"]:
                    cadence = effective_cadence(ctx.config, c.priority, c.cadence_days)
                    typer.echo(f"✓ {c.name} — noped (1d) — warm-up complete, regular cadence {cadence}d)")
                else:
                    typer.echo(f"✓ {c.name} — noped (1d)")
                break

            elif choice == "s":
                snooze_days = snooze_default
                while True:
                    raw = _prompt(f"Days [{snooze_default}]: ").strip()
                    if not raw:
                        break
                    try:
                        snooze_days = int(raw)
                        break
                    except ValueError:
                        typer.echo("Invalid number.", err=True)
                result = _do_snooze(ctx, c, state, snooze_days, today)
                snoozed += 1
                if result["relegated"]:
                    typer.echo(f"✓ {c.name} — snoozed {snooze_days}d — relegated, cadence=0 (no-due)")
                elif result["warm_up_consumed"]:
                    cadence = effective_cadence(ctx.config, c.priority, c.cadence_days)
                    typer.echo(f"✓ {c.name} — snoozed {snooze_days}d — warm-up complete, regular cadence {cadence}d)")
                else:
                    typer.echo(f"✓ {c.name} — snoozed {snooze_days}d")
                break

            elif choice == "q":
                quit_session = True
                break

            else:
                typer.echo("Invalid choice. Use y, n, s, or q.", err=True)

        if quit_session:
            break

    total_processed = touched + snoozed
    pending = len(due) - total_processed

    typer.echo("")
    typer.echo("─── Summary ───")
    summary_parts = []
    if touched:
        summary_parts.append(f"Touched: {touched}")
    if snoozed:
        summary_parts.append(f"Snoozed: {snoozed}")
    if pending:
        summary_parts.append(f"Pending: {pending}")
    if summary_parts:
        typer.echo("  ".join(summary_parts))

    return 0
