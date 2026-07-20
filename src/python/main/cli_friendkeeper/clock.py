from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Protocol


class Clock(Protocol):
    """Protocol for providing the current date and time."""

    def today(self) -> date: ...
    def now(self) -> datetime: ...


class SystemClock:
    """Clock that returns the real system date and time."""

    def today(self) -> date:
        return date.today()

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock:
    """Clock pinned to a specific date and optional datetime."""

    def __init__(self, fixed_date: date, fixed_datetime: datetime | None = None) -> None:
        self._date = fixed_date
        self._datetime = fixed_datetime or datetime.combine(
            fixed_date, time(0, 0), tzinfo=timezone.utc
        )

    def today(self) -> date:
        return self._date

    def now(self) -> datetime:
        return self._datetime
