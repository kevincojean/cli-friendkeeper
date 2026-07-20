from __future__ import annotations

from datetime import date, timedelta

from cli_friendkeeper.check_logic import days_since_touched, is_due, select_due
from cli_friendkeeper.config import Config
from cli_friendkeeper.models import Contact, ContactState


class TestIsDue:
    def test_given_never_touched_when_checking_due_then_returns_true(self) -> None:
        state = ContactState(name="alice")
        contact = Contact(name="alice", display_name="Alice")
        today = date(2026, 7, 20)
        assert is_due(state, contact, today, cadence=30) is True

    def test_given_touched_within_cadence_when_checking_due_then_returns_false(self) -> None:
        state = ContactState(name="alice", last_touched=date(2026, 7, 15))
        contact = Contact(name="alice", display_name="Alice")
        today = date(2026, 7, 20)
        assert is_due(state, contact, today, cadence=30) is False

    def test_given_touched_beyond_cadence_when_checking_due_then_returns_true(self) -> None:
        state = ContactState(name="alice", last_touched=date(2026, 6, 1))
        contact = Contact(name="alice", display_name="Alice")
        today = date(2026, 7, 20)
        assert is_due(state, contact, today, cadence=30) is True

    def test_given_removed_contact_when_checking_due_then_returns_false(self) -> None:
        state = ContactState(
            name="alice",
            last_touched=date(2026, 1, 1),
            removed=True,
            removed_at=date(2026, 6, 1),
        )
        contact = Contact(name="alice", display_name="Alice")
        today = date(2026, 7, 20)
        assert is_due(state, contact, today, cadence=30) is False


class TestDaysSinceTouched:
    def test_given_never_touched_when_calculating_days_since_then_returns_none(self) -> None:
        state = ContactState(name="alice")
        today = date(2026, 7, 20)
        assert days_since_touched(state, today) is None

    def test_given_touched_yesterday_when_calculating_days_since_then_returns_1(self) -> None:
        state = ContactState(name="alice", last_touched=date(2026, 7, 19))
        today = date(2026, 7, 20)
        assert days_since_touched(state, today) == 1


class TestSelectDue:
    def test_given_no_contacts_when_selecting_due_then_returns_empty_list(self) -> None:
        config = Config(cadence={"deep": 15, "casual": 45, "network": 180})
        today = date(2026, 7, 20)
        assert select_due([], {}, today, config) == []

    def test_given_due_contacts_when_selecting_due_then_sorts_by_most_overdue_first(self) -> None:
        config = Config(cadence={"deep": 15, "casual": 45, "network": 180})
        today = date(2026, 7, 20)

        alice = Contact(name="alice", display_name="Alice", priority="casual")
        bob = Contact(name="bob", display_name="Bob", priority="casual")

        states = {
            "alice": ContactState(name="alice", last_touched=today - timedelta(days=60)),
            "bob": ContactState(name="bob", last_touched=today - timedelta(days=50)),
        }

        result = select_due([bob, alice], states, today, config)
        assert [c.name for c in result] == ["alice", "bob"]

    def test_given_never_touched_and_overdue_contacts_when_selecting_due_then_never_touched_first(self) -> None:
        config = Config(cadence={"deep": 15, "casual": 45, "network": 180})
        today = date(2026, 7, 20)

        alice = Contact(name="alice", display_name="Alice", priority="casual")
        bob = Contact(name="bob", display_name="Bob", priority="casual")

        states = {
            "alice": ContactState(name="alice", last_touched=today - timedelta(days=60)),
        }

        result = select_due([bob, alice], states, today, config)
        assert [c.name for c in result] == ["bob", "alice"]
