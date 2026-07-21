from __future__ import annotations

from datetime import date, timedelta

from cli_friendkeeper.config import Config, effective_cadence
from cli_friendkeeper.models import Contact, ContactState


def due_date(state: ContactState, contact: Contact, today: date, cadence: int) -> date | None:
    """Return the ISO date this contact is (or was) due for a message, or ``None``.

    Returns ``None`` when the contact is never due (cadence <= 0 or removed).
    For never-touched contacts the due date is their ``added_at`` (perpetually
    overdue since the day they were added).  For touched contacts it is
    ``last_touched + cadence``.
    """
    if cadence <= 0:
        return None
    if state.removed:
        return None
    if state.last_touched is not None:
        return state.last_touched + timedelta(days=cadence)
    # Never touched — due since added
    return contact.added_at if contact.added_at is not None else today


def is_due(state: ContactState, contact: Contact, today: date, cadence: int) -> bool:
    if cadence <= 0:
        return False
    if state.removed:
        return False
    if state.last_touched is None:
        return True
    return (today - state.last_touched).days >= cadence


def days_since_touched(state: ContactState, today: date) -> int | None:
    if state.last_touched is None:
        return None
    return (today - state.last_touched).days


def select_due(
    contacts: list[Contact],
    states: dict[str, ContactState],
    today: date,
    config: Config,
) -> list[Contact]:
    result = []
    for c in contacts:
        state = states.get(c.id, ContactState(id=c.id, name=c.name))
        cadence = effective_cadence(config, c.priority, c.cadence_days)
        if is_due(state, c, today, cadence):
            result.append(c)
    result.sort(
        key=lambda c: days_since_touched(
            states.get(c.id, ContactState(id=c.id, name=c.name)), today
        )
        or 9999,
        reverse=True,
    )
    return result
