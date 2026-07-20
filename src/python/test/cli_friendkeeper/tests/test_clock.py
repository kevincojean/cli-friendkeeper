"""Tests for the clock module."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from cli_friendkeeper.clock import Clock, FixedClock, SystemClock


class TestSystemClock:
    """Tests for the real-time SystemClock."""

    def test_given_system_clock_when_calling_today_then_returns_real_date(
        self: TestSystemClock,
    ) -> None:
        """SystemClock.today() should return the real current date."""
        clock: Clock = SystemClock()
        result: date = clock.today()
        assert result == date.today()

    def test_given_system_clock_when_calling_now_then_returns_utc_aware_datetime(
        self: TestSystemClock,
    ) -> None:
        """SystemClock.now() should be timezone-aware and in UTC."""
        clock: Clock = SystemClock()
        result: datetime = clock.now()
        assert result.tzinfo is timezone.utc


class TestFixedClock:
    """Tests for the deterministic FixedClock."""

    def test_given_fixed_clock_with_date_when_calling_today_then_returns_pinned_date(
        self: TestFixedClock,
    ) -> None:
        """FixedClock(date).today() should return the pinned date."""
        pinned: date = date(2026, 1, 1)
        clock: Clock = FixedClock(pinned)
        assert clock.today() == pinned

    def test_given_fixed_clock_with_date_only_when_calling_now_then_returns_midnight_utc(
        self: TestFixedClock,
    ) -> None:
        """FixedClock(date).now() should return midnight UTC of the pinned date."""
        pinned: date = date(2026, 1, 1)
        clock: Clock = FixedClock(pinned)
        expected: datetime = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert clock.now() == expected

    def test_given_fixed_clock_with_explicit_datetime_when_calling_now_then_returns_that_datetime(
        self: TestFixedClock,
    ) -> None:
        """FixedClock(date, datetime).now() should return the explicit pinned datetime."""
        pinned_date: date = date(2026, 6, 15)
        pinned_dt: datetime = datetime(2026, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        clock: Clock = FixedClock(pinned_date, pinned_dt)
        assert clock.now() == pinned_dt

    def test_given_fixed_clock_when_calling_today_then_date_matches_pinned_datetime(
        self: TestFixedClock,
    ) -> None:
        """FixedClock.today() should return the date portion of the pinned datetime."""
        pinned_dt: datetime = datetime(2026, 12, 25, 10, 0, 0, tzinfo=timezone.utc)
        clock: Clock = FixedClock(pinned_dt.date(), pinned_dt)
        assert clock.today() == pinned_dt.date()

    def test_given_fixed_clock_when_now_returns_datetime_then_timezone_is_utc(
        self: TestFixedClock,
    ) -> None:
        """FixedClock.now() should always be UTC-aware."""
        clock: Clock = FixedClock(date(2026, 3, 14))
        assert clock.now().tzinfo is timezone.utc


class TestClockProtocol:
    """Tests that both clock implementations satisfy the Clock protocol."""

    def test_given_system_clock_when_used_as_protocol_then_isinstance_check_succeeds(
        self: TestClockProtocol,
    ) -> None:
        """SystemClock should satisfy the Clock protocol structurally."""
        clock: Clock = SystemClock()
        _verify_clock(clock)

    def test_given_fixed_clock_when_used_as_protocol_then_isinstance_check_succeeds(
        self: TestClockProtocol,
    ) -> None:
        """FixedClock should satisfy the Clock protocol structurally."""
        clock: Clock = FixedClock(date(2026, 1, 1))
        _verify_clock(clock)


def _verify_clock(clock: Clock) -> None:
    """Helper: verify a value satisfies the Clock protocol at runtime."""
    assert callable(clock.today)
    assert callable(clock.now)
    # Verify return types
    t: date = clock.today()
    n: datetime = clock.now()
    assert isinstance(t, date)
    assert isinstance(n, datetime)
