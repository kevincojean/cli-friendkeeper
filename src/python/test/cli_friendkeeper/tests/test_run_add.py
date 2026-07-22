"""Tests for the ``add`` subcommand (run_add.py)."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from typing import Any

from cli_friendkeeper.clock import FixedClock
from cli_friendkeeper.config import Config, DEFAULT_CADENCE
from cli_friendkeeper.models import ContactState
from cli_friendkeeper.repository import ContactRepo, LogRepo, StateRepo
from conftest import FakeStore


class FakeContext:
    """Duck-typed Context that accepts injected repos and clock."""

    def __init__(
        self,
        contacts: ContactRepo,
        log: LogRepo,
        clock: Any,
        config: Config | None = None,
        states: StateRepo | None = None,
    ) -> None:
        self.contacts = contacts
        self.log = log
        self.clock = clock
        self.config = config or Config(cadence=DEFAULT_CADENCE)
        self.states = states


def test_given_valid_contact_when_adding_then_returns_zero(tmp_path: Path) -> None:
    """given valid contact when adding then returns 0 and stores contact."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 1, 1))
    ctx = FakeContext(contacts, log, clock)

    from cli_friendkeeper.ccli.task.run_add import run

    rc = run(["Alice Smith", "--email", "alice@example.com"], ctx)

    assert rc == 0
    result = contacts.all()
    assert len(result) == 1
    assert result[0].name == "Alice Smith"
    assert result[0].email == "alice@example.com"
    assert uuid.UUID(result[0].id)


def test_given_no_name_when_adding_then_returns_one(tmp_path: Path) -> None:
    """given no name when adding then returns 1 and no contact stored."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 1, 1))
    ctx = FakeContext(contacts, log, clock)

    from cli_friendkeeper.ccli.task.run_add import run

    rc = run(["--email", "alice@example.com"], ctx)

    assert rc == 1
    assert contacts.all() == []


def test_given_no_email_and_no_phone_when_adding_then_returns_zero(
    tmp_path: Path,
) -> None:
    """given no email and no phone when adding then returns 0 and stores contact."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 1, 1))
    ctx = FakeContext(contacts, log, clock)

    from cli_friendkeeper.ccli.task.run_add import run

    rc = run(["Alice Smith"], ctx)

    assert rc == 0
    result = contacts.all()
    assert len(result) == 1
    assert result[0].name == "Alice Smith"
    assert result[0].email is None
    assert result[0].phone is None


def test_given_positional_name_when_adding_then_returns_zero(
    tmp_path: Path,
) -> None:
    """given positional name when adding then returns 0 and stores contact."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 1, 1))
    ctx = FakeContext(contacts, log, clock)

    from cli_friendkeeper.ccli.task.run_add import run

    rc = run(["Alice Smith", "--email", "alice@example.com", "--note", "some note"], ctx)

    assert rc == 0
    result = contacts.all()
    assert len(result) == 1
    assert result[0].name == "Alice Smith"
    assert result[0].email == "alice@example.com"
    assert result[0].notes == "some note"


def test_given_same_name_when_adding_twice_then_both_succeed(
    tmp_path: Path,
) -> None:
    """given same name when adding twice then both succeed (different UUIDs)."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 1, 1))
    ctx = FakeContext(contacts, log, clock)

    from cli_friendkeeper.ccli.task.run_add import run

    rc1 = run(["--name", "Alice Smith", "--email", "alice@example.com"], ctx)
    assert rc1 == 0

    rc2 = run(["--name", "Alice Smith", "--email", "alice@other.com"], ctx)
    assert rc2 == 0
    assert len(contacts.all()) == 2


def test_given_invalid_email_when_adding_then_returns_one(tmp_path: Path) -> None:
    """given invalid email when adding then returns 1."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 1, 1))
    ctx = FakeContext(contacts, log, clock)

    from cli_friendkeeper.ccli.task.run_add import run

    rc = run(["--name", "Alice Smith", "--email", "not-an-email"], ctx)

    assert rc == 1
    assert contacts.all() == []


def test_given_all_fields_when_adding_then_returns_zero(tmp_path: Path) -> None:
    """given all optional fields when adding then returns 0 and stores full contact."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 1, 1))
    ctx = FakeContext(contacts, log, clock)

    from cli_friendkeeper.ccli.task.run_add import run

    rc = run(
        [
            "--name",
            "Bob Jones",
            "--email",
            "bob@example.com",
            "--phone",
            "555-0100",
            "--priority",
            "deep",
            "--cadence-days",
            "14",
            "--note",
            "Met at conference",
        ],
        ctx,
    )

    assert rc == 0
    result = contacts.all()
    assert len(result) == 1
    assert result[0].name == "Bob Jones"
    assert result[0].priority == "deep"
    assert result[0].cadence_days == 14
    assert result[0].notes == "Met at conference"
    assert result[0].phone == "555-0100"


class TestAddWarmUp:
    def test_given_acquaintance_when_add_then_state_created_with_warm_up_consumed_false(
        self, capsys: Any, tmp_path: Path
    ) -> None:
        """given `friend add --priority acquaintance` when add then ContactState has warm_up_consumed=False, snooze_count=0"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 1, 1))
        ctx = FakeContext(contacts, log, clock, states=states)

        from cli_friendkeeper.ccli.task.run_add import run

        rc = run(["Alice Smith", "--priority", "acquaintance"], ctx)

        assert rc == 0
        all_contacts = contacts.all()
        assert len(all_contacts) == 1
        contact_id = all_contacts[0].id
        state_result = states.get(contact_id)
        assert not state_result.is_left()
        state = state_result.value
        assert state.warm_up_consumed is False
        assert state.snooze_count == 0

    def test_given_casual_when_add_then_state_created_with_warm_up_consumed_false(
        self, capsys: Any, tmp_path: Path
    ) -> None:
        """given `friend add --priority casual` when add then ContactState has warm_up_consumed=False, snooze_count=0"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 1, 1))
        ctx = FakeContext(contacts, log, clock, states=states)

        from cli_friendkeeper.ccli.task.run_add import run

        rc = run(["Bob", "--priority", "casual"], ctx)

        assert rc == 0
        all_contacts = contacts.all()
        assert len(all_contacts) == 1
        contact_id = all_contacts[0].id
        state_result = states.get(contact_id)
        assert not state_result.is_left()
        state = state_result.value
        assert state.warm_up_consumed is False
        assert state.snooze_count == 0

    def test_given_deep_when_add_then_state_created_with_warm_up_consumed_true(
        self, capsys: Any, tmp_path: Path
    ) -> None:
        """given `friend add --priority deep` when add then ContactState has warm_up_consumed=True (no warm-up for deep)"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 1, 1))
        ctx = FakeContext(contacts, log, clock, states=states)

        from cli_friendkeeper.ccli.task.run_add import run

        rc = run(["Carol", "--priority", "deep"], ctx)

        assert rc == 0
        all_contacts = contacts.all()
        assert len(all_contacts) == 1
        contact_id = all_contacts[0].id
        state_result = states.get(contact_id)
        assert not state_result.is_left()
        state = state_result.value
        assert state.warm_up_consumed is True
        assert state.snooze_count == 0

    def test_given_network_when_add_then_state_created_with_warm_up_consumed_true(
        self, capsys: Any, tmp_path: Path
    ) -> None:
        """given `friend add --priority network` when add then ContactState has warm_up_consumed=True (no warm-up for network)"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 1, 1))
        ctx = FakeContext(contacts, log, clock, states=states)

        from cli_friendkeeper.ccli.task.run_add import run

        rc = run(["Dave", "--priority", "network"], ctx)

        assert rc == 0
        all_contacts = contacts.all()
        assert len(all_contacts) == 1
        contact_id = all_contacts[0].id
        state_result = states.get(contact_id)
        assert not state_result.is_left()
        state = state_result.value
        assert state.warm_up_consumed is True
        assert state.snooze_count == 0
