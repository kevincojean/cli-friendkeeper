from __future__ import annotations

from datetime import date, timedelta

from cli_friendkeeper.check_logic import days_since_touched, due_date, is_due, select_due
from cli_friendkeeper.config import Config
from cli_friendkeeper.models import Contact, ContactState


class TestIsDue:
    def test_given_never_touched_when_checking_due_then_returns_true(self) -> None:
        state = ContactState(id="uuid-alice", name="Alice")
        contact = Contact(id="uuid-alice", name="Alice")
        today = date(2026, 7, 20)
        assert is_due(state, contact, today, cadence=30) is True

    def test_given_touched_within_cadence_when_checking_due_then_returns_false(self) -> None:
        state = ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 15))
        contact = Contact(id="uuid-alice", name="Alice")
        today = date(2026, 7, 20)
        assert is_due(state, contact, today, cadence=30) is False

    def test_given_touched_beyond_cadence_when_checking_due_then_returns_true(self) -> None:
        state = ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 6, 1))
        contact = Contact(id="uuid-alice", name="Alice")
        today = date(2026, 7, 20)
        assert is_due(state, contact, today, cadence=30) is True

    def test_given_removed_contact_when_checking_due_then_returns_false(self) -> None:
        state = ContactState(
            id="uuid-alice",
            name="Alice",
            last_touched=date(2026, 1, 1),
            removed=True,
            removed_at=date(2026, 6, 1),
        )
        contact = Contact(id="uuid-alice", name="Alice")
        today = date(2026, 7, 20)
        assert is_due(state, contact, today, cadence=30) is False

    def test_given_acquaintance_cadence_zero_when_checking_due_then_returns_false(self) -> None:
        """given acquaintance priority (cadence=0) when checking due then never due"""
        state = ContactState(id="uuid-alice", name="Alice")
        contact = Contact(id="uuid-alice", name="Alice")
        today = date(2026, 7, 20)
        assert is_due(state, contact, today, cadence=0) is False

    def test_given_acquaintance_with_explicit_cadence_when_checking_due_then_uses_cadence(self) -> None:
        """given acquaintance with explicit --cadence-days when checking due then normal logic applies"""
        state = ContactState(
            id="uuid-alice", name="Alice",
            last_touched=date(2026, 7, 1),
        )
        contact = Contact(id="uuid-alice", name="Alice")
        today = date(2026, 7, 20)
        # Explicit cadence of 30 means not yet due
        assert is_due(state, contact, today, cadence=30) is False
        # Explicit cadence of 10 means overdue
        assert is_due(state, contact, today, cadence=10) is True


class TestDaysSinceTouched:
    def test_given_never_touched_when_calculating_days_since_then_returns_none(self) -> None:
        state = ContactState(id="uuid-alice", name="Alice")
        today = date(2026, 7, 20)
        assert days_since_touched(state, today) is None

    def test_given_touched_yesterday_when_calculating_days_since_then_returns_1(self) -> None:
        state = ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 19))
        today = date(2026, 7, 20)
        assert days_since_touched(state, today) == 1


class TestDueDate:
    def test_given_never_touched_when_due_date_then_returns_added_at(self) -> None:
        """given never touched when due_date then returns added_at (perpetually overdue)"""
        contact = Contact(id="uuid-alice", name="Alice", added_at=date(2026, 1, 1))
        state = ContactState(id="uuid-alice", name="Alice")
        today = date(2026, 7, 20)
        assert due_date(state, contact, today, cadence=30) == date(2026, 1, 1)

    def test_given_touched_contact_when_due_date_then_returns_last_touched_plus_cadence(self) -> None:
        """given touched contact when due_date then returns last_touched + cadence"""
        contact = Contact(id="uuid-alice", name="Alice")
        state = ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 6, 1))
        today = date(2026, 7, 20)
        assert due_date(state, contact, today, cadence=30) == date(2026, 7, 1)

    def test_given_cadence_zero_when_due_date_then_returns_none(self) -> None:
        """given cadence=0 when due_date then returns None"""
        contact = Contact(id="uuid-alice", name="Alice")
        state = ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 6, 1))
        today = date(2026, 7, 20)
        assert due_date(state, contact, today, cadence=0) is None

    def test_given_removed_contact_when_due_date_then_returns_none(self) -> None:
        """given removed contact when due_date then returns None"""
        contact = Contact(id="uuid-alice", name="Alice")
        state = ContactState(
            id="uuid-alice", name="Alice",
            last_touched=date(2026, 1, 1),
            removed=True, removed_at=date(2026, 6, 1),
        )
        today = date(2026, 7, 20)
        assert due_date(state, contact, today, cadence=30) is None


class TestSelectDue:
    def test_given_no_contacts_when_selecting_due_then_returns_empty_list(self) -> None:
        config = Config(cadence={"deep": 15, "casual": 45, "network": 180})
        today = date(2026, 7, 20)
        assert select_due([], {}, today, config) == []

    def test_given_due_contacts_when_selecting_due_then_sorts_by_most_overdue_first(self) -> None:
        config = Config(cadence={"deep": 15, "casual": 45, "network": 180})
        today = date(2026, 7, 20)

        alice = Contact(id="uuid-alice", name="Alice", priority="casual")
        bob = Contact(id="uuid-bob", name="Bob", priority="casual")

        states = {
            "uuid-alice": ContactState(id="uuid-alice", name="Alice", last_touched=today - timedelta(days=60)),
            "uuid-bob": ContactState(id="uuid-bob", name="Bob", last_touched=today - timedelta(days=50)),
        }

        result = select_due([bob, alice], states, today, config)
        assert [c.name for c in result] == ["Alice", "Bob"]

    def test_given_never_touched_and_overdue_contacts_when_selecting_due_then_never_touched_first(self) -> None:
        config = Config(cadence={"deep": 15, "casual": 45, "network": 180})
        today = date(2026, 7, 20)

        alice = Contact(id="uuid-alice", name="Alice", priority="casual")
        bob = Contact(id="uuid-bob", name="Bob", priority="casual")

        states = {
            "uuid-alice": ContactState(id="uuid-alice", name="Alice", last_touched=today - timedelta(days=60)),
        }

        result = select_due([bob, alice], states, today, config)
        assert [c.name for c in result] == ["Bob", "Alice"]
