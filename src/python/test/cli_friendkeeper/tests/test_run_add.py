"""Tests for the ``add`` subcommand (run_add.py)."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from typing import Any

from cli_friendkeeper.clock import FixedClock
from cli_friendkeeper.repository import ContactRepo, LogRepo
from conftest import FakeStore


class FakeContext:
    """Duck-typed Context that accepts injected repos and clock."""

    def __init__(
        self,
        contacts: ContactRepo,
        log: LogRepo,
        clock: Any,
    ) -> None:
        self.contacts = contacts
        self.log = log
        self.clock = clock


def test_given_valid_contact_when_adding_then_returns_zero(tmp_path: Path) -> None:
    """given valid contact when adding then returns 0 and stores contact."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 1, 1))
    ctx = FakeContext(contacts, log, clock)

    from cli_friendkeeper.ccli.task.run_add import run

    rc = run(["--name", "Alice Smith", "--email", "alice@example.com"], ctx)

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


def test_given_no_email_and_no_phone_when_adding_then_returns_one(
    tmp_path: Path,
) -> None:
    """given no email and no phone when adding then returns 1."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 1, 1))
    ctx = FakeContext(contacts, log, clock)

    from cli_friendkeeper.ccli.task.run_add import run

    rc = run(["--name", "Alice Smith"], ctx)

    assert rc == 1
    assert contacts.all() == []


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
            "--notes",
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
