from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from cli_friendkeeper.clock import FixedClock
from cli_friendkeeper.models import Contact
from cli_friendkeeper.repository import ContactRepo, LogRepo, StateRepo
from cli_friendkeeper.ccli.task.run_remove import _resolve_id
from conftest import FakeStore


class FakeContext:
    def __init__(
        self,
        contacts: ContactRepo,
        states: StateRepo,
        log: LogRepo,
        clock: Any,
        data_dir: Path,
    ) -> None:
        self.contacts = contacts
        self.states = states
        self.log = log
        self.clock = clock
        self.data_dir = data_dir


def test_given_contact_exists_when_remove_with_force_then_removes_contact(
    capsys: Any, tmp_path: Path
) -> None:
    """given a contact exists when remove with --force then contact is removed and state tombstoned."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    ctx = FakeContext(contacts, states, log, clock, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", email="alice@example.com"),
    ])

    from cli_friendkeeper.ccli.task.run_remove import run

    rc = run(["uuid-alice", "--force"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Removed: Alice" in captured.out
    assert contacts.all() == []

    state_result = states.get("uuid-alice")
    assert state_result.is_right()
    state = state_result.value
    assert state.removed is True
    assert state.removed_at == date(2026, 7, 20)

    log_entries = log.all()
    assert len(log_entries) == 1
    assert log_entries[0].action == "remove"
    assert log_entries[0].id == "uuid-alice"
    assert log_entries[0].name == "Alice"


def test_given_contact_exists_when_remove_without_force_and_yes_then_removes(
    capsys: Any, tmp_path: Path, monkeypatch: Any
) -> None:
    """given a contact exists when remove without --force and user types 'y' then contact is removed."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    ctx = FakeContext(contacts, states, log, clock, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", email="alice@example.com"),
    ])

    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    from cli_friendkeeper.ccli.task.run_remove import run

    rc = run(["uuid-alice"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Removed: Alice" in captured.out
    assert contacts.all() == []


def test_given_contact_exists_when_remove_without_force_and_no_then_cancelled(
    capsys: Any, tmp_path: Path, monkeypatch: Any
) -> None:
    """given a contact exists when remove without --force and user types 'n' then cancelled and contact remains."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    ctx = FakeContext(contacts, states, log, clock, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", email="alice@example.com"),
    ])

    monkeypatch.setattr("builtins.input", lambda prompt="": "n")

    from cli_friendkeeper.ccli.task.run_remove import run

    rc = run(["uuid-alice"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Cancelled." in captured.out
    assert len(contacts.all()) == 1

    state_result = states.get("uuid-alice")
    assert state_result.is_left()


def test_given_non_existent_contact_when_remove_then_returns_one(
    capsys: Any, tmp_path: Path
) -> None:
    """given a non-existent contact when remove with --force then returns 1 and prints error."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    ctx = FakeContext(contacts, states, log, clock, data_dir)

    from cli_friendkeeper.ccli.task.run_remove import run

    rc = run(["nonexistent-id", "--force"], ctx)
    captured = capsys.readouterr()

    assert rc == 1
    assert "not found" in captured.err


def test_given_already_removed_contact_when_remove_then_returns_one(
    capsys: Any, tmp_path: Path
) -> None:
    """given a contact already removed when remove again then returns 1."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    ctx = FakeContext(contacts, states, log, clock, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", email="alice@example.com"),
    ])

    from cli_friendkeeper.ccli.task.run_remove import run

    rc1 = run(["uuid-alice", "--force"], ctx)
    assert rc1 == 0
    capsys.readouterr()

    rc2 = run(["uuid-alice", "--force"], ctx)
    captured2 = capsys.readouterr()

    assert rc2 == 1
    assert "not found" in captured2.err


def test_given_partial_id_when_exact_match_then_resolves_to_that_contact() -> None:
    """given partial id that is an exact match when _resolve_id then returns that contact."""
    contacts = [
        Contact(id="uuid-alice-long", name="Alice"),
        Contact(id="uuid-bob", name="Bob"),
    ]
    result = _resolve_id("uuid-bob", contacts)

    assert result.is_right()
    contact, resolved = result.value
    assert contact.name == "Bob"
    assert resolved == "uuid-bob"


def test_given_partial_id_when_unique_prefix_then_resolves() -> None:
    """given partial id that is a unique prefix when _resolve_id then resolves to the full id."""
    contacts = [
        Contact(id="aaa-bbb-ccc", name="Alice"),
        Contact(id="ddd-eee-fff", name="Bob"),
    ]
    result = _resolve_id("aaa", contacts)

    assert result.is_right()
    contact, resolved = result.value
    assert contact.name == "Alice"
    assert resolved == "aaa-bbb-ccc"


def test_given_partial_id_when_ambiguous_prefix_then_returns_error(capsys: Any, tmp_path: Path) -> None:
    """given partial id matching multiple contacts when remove then returns 1 with ambiguity message."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    ctx = FakeContext(contacts, states, log, clock, data_dir)

    contacts._write_contacts([
        Contact(id="aaa-bbb-ccc", name="Alice"),
        Contact(id="aaa-eee-fff", name="Aaron"),
    ])

    from cli_friendkeeper.ccli.task.run_remove import run

    rc = run(["aaa", "--force"], ctx)
    captured = capsys.readouterr()

    assert rc == 1
    assert "matches 2 contacts" in captured.err
    assert "Alice" in captured.err
    assert "Aaron" in captured.err
    assert "Specify more digits" in captured.err


def test_given_partial_id_when_no_match_then_returns_not_found(capsys: Any, tmp_path: Path) -> None:
    """given partial id matching no contacts when remove then returns 1 with not found."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    ctx = FakeContext(contacts, states, log, clock, data_dir)

    contacts._write_contacts([
        Contact(id="aaa-bbb-ccc", name="Alice"),
    ])

    from cli_friendkeeper.ccli.task.run_remove import run

    rc = run(["zzz", "--force"], ctx)
    captured = capsys.readouterr()

    assert rc == 1
    assert "not found" in captured.err


def test_given_partial_id_unique_when_remove_with_force_then_removes_contact(capsys: Any, tmp_path: Path) -> None:
    """given unique partial id when remove with --force then contact is removed."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    ctx = FakeContext(contacts, states, log, clock, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", email="alice@example.com"),
    ])

    from cli_friendkeeper.ccli.task.run_remove import run

    rc = run(["uuid-al", "--force"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice" in captured.out
    assert contacts.all() == []

    state_result = states.get("uuid-alice")
    assert state_result.is_right()
    state = state_result.value
    assert state.removed is True
