from __future__ import annotations

from datetime import date

from cli_friendkeeper.config import Config, effective_cadence
from cli_friendkeeper.models import Contact, ContactState


def is_due(state: ContactState, contact: Contact, today: date, cadence: int) -> bool:
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
        state = states.get(c.name, ContactState(name=c.name))
        cadence = effective_cadence(config, c.priority, c.cadence_days)
        if is_due(state, c, today, cadence):
            result.append(c)
    result.sort(
        key=lambda c: days_since_touched(
            states.get(c.name, ContactState(name=c.name)), today
        )
        or 9999,
        reverse=True,
    )
    return result
