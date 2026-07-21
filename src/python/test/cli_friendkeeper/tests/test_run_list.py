"""Tests for the ``run_list`` subcommand."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from cli_friendkeeper.config import Config, DEFAULT_CADENCE
from cli_friendkeeper.models import Contact, ContactState
from cli_friendkeeper.repository import ContactRepo, StateRepo
from conftest import FakeStore


class FakeContext:
    """Duck-typed Context that accepts injected repos and clock."""

    def __init__(
        self,
        contacts: ContactRepo,
        states: StateRepo,
        clock: Any,
        config: Config,
    ) -> None:
        self.contacts = contacts
        self.states = states
        self.clock = clock
        self.config = config


def test_given_no_contacts_when_run_list_then_prints_no_contacts_yet(capsys: Any, tmp_path: Path) -> None:
    """given no contacts when run_list then prints 'No contacts yet.'"""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    clock = _clock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, clock, config)

    from cli_friendkeeper.ccli.task.run_list import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "No contacts yet." in captured.out


def test_given_two_active_contacts_when_run_list_then_table_shows_both(capsys: Any, tmp_path: Path) -> None:
    """given two active contacts when run_list then table shows both."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    clock = _clock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, clock, config)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="casual"),
        Contact(id="uuid-bob", name="Bob", priority="deep"),
    ])
    store.write_jsonl_atomic(
        data_dir / "state.jsonl",
        [
            ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 6, 1)).to_dict(),
            ContactState(id="uuid-bob", name="Bob", last_touched=date(2026, 7, 1)).to_dict(),
        ],
    )

    from cli_friendkeeper.ccli.task.run_list import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice" in captured.out
    assert "Bob" in captured.out


def test_given_priority_deep_when_run_list_then_only_deep_contacts_shown(capsys: Any, tmp_path: Path) -> None:
    """given --priority deep when run_list then only deep contacts shown."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    clock = _clock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, clock, config)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="deep"),
        Contact(id="uuid-bob", name="Bob", priority="casual"),
        Contact(id="uuid-carol", name="Carol", priority="network"),
    ])

    from cli_friendkeeper.ccli.task.run_list import run

    rc = run(["--priority", "deep"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice" in captured.out
    assert "Bob" not in captured.out
    assert "Carol" not in captured.out


def test_given_all_flag_when_run_list_then_removed_contacts_are_shown(capsys: Any, tmp_path: Path) -> None:
    """given --all when run_list then removed contacts are shown."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    clock = _clock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, clock, config)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="casual"),
        Contact(id="uuid-bob", name="Bob", priority="deep"),
    ])
    store.write_jsonl_atomic(
        data_dir / "state.jsonl",
        [
            ContactState(id="uuid-alice", name="Alice").to_dict(),
            ContactState(id="uuid-bob", name="Bob", removed=True).to_dict(),
        ],
    )

    from cli_friendkeeper.ccli.task.run_list import run

    rc = run(["--all"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice" in captured.out
    assert "Bob" in captured.out


def test_given_json_flag_when_run_list_then_returns_valid_json_with_expected_fields(capsys: Any, tmp_path: Path) -> None:
    """given --json when run_list then valid JSON with expected fields."""
    import json

    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    clock = _clock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, clock, config)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="deep"),
    ])
    store.write_jsonl_atomic(
        data_dir / "state.jsonl",
        [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 6, 1)).to_dict()],
    )

    from cli_friendkeeper.ccli.task.run_list import run

    rc = run(["--json"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "uuid-alice"
    assert data[0]["name"] == "Alice"
    assert "display_name" not in data[0]
    assert data[0]["priority"] == "deep"
    assert data[0]["days_since_touched"] == 49
    assert data[0]["last_touched"] == "2026-06-01"
    assert data[0]["cadence"] == 15
    assert data[0]["due"] is True
    assert data[0]["removed"] is False


def test_given_removed_contact_without_all_when_run_list_then_prints_no_contacts_yet(capsys: Any, tmp_path: Path) -> None:
    """given a removed contact without --all then prints 'No contacts yet.'"""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    clock = _clock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, clock, config)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="casual"),
    ])
    store.write_jsonl_atomic(
        data_dir / "state.jsonl",
        [ContactState(id="uuid-alice", name="Alice", removed=True).to_dict()],
    )

    from cli_friendkeeper.ccli.task.run_list import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "No contacts yet." in captured.out


def _clock(fixed_date: date) -> Any:
    from cli_friendkeeper.clock import FixedClock

    return FixedClock(fixed_date)
