"""Tests for the ``run_due`` subcommand."""

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


def test_given_no_contacts_when_run_due_then_prints_nothing_due(capsys: Any, tmp_path: Path) -> None:
    """given no contacts when run_due then prints 'Nothing due.'"""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    clock = _clock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, clock, config)

    from cli_friendkeeper.ccli.task.run_due import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Nothing due." in captured.out


def test_given_contact_never_touched_when_run_due_then_shows_as_due(capsys: Any, tmp_path: Path) -> None:
    """given a contact never touched when run_due then shows as due."""
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

    from cli_friendkeeper.ccli.task.run_due import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice" in captured.out
    assert "Never" in captured.out


def test_given_priority_deep_when_run_due_then_only_deep_contacts_shown(capsys: Any, tmp_path: Path) -> None:
    """given --priority deep when run_due then only deep contacts shown."""
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
    store.write_jsonl_atomic(
        data_dir / "state.jsonl",
        [
            ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 6, 1)).to_dict(),
            ContactState(id="uuid-bob", name="Bob", last_touched=date(2026, 6, 1)).to_dict(),
            ContactState(id="uuid-carol", name="Carol", last_touched=date(2026, 6, 1)).to_dict(),
        ],
    )

    from cli_friendkeeper.ccli.task.run_due import run

    rc = run(["--priority", "deep"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice" in captured.out
    assert "Bob" not in captured.out
    assert "Carol" not in captured.out


def test_given_limit_one_when_run_due_then_only_one_contact_shown(capsys: Any, tmp_path: Path) -> None:
    """given --limit 1 when run_due then only one contact shown."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    clock = _clock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, clock, config)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="casual"),
        Contact(id="uuid-bob", name="Bob", priority="casual"),
    ])

    from cli_friendkeeper.ccli.task.run_due import run

    rc = run(["--limit", "1"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice" in captured.out or "Bob" in captured.out
    lines = [l for l in captured.out.split("\n") if "Alice" in l or "Bob" in l]
    assert len(lines) == 1


def test_given_json_flag_when_run_due_then_valid_json_printed(capsys: Any, tmp_path: Path) -> None:
    """given --json when run_due then valid JSON is printed."""
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

    from cli_friendkeeper.ccli.task.run_due import run

    rc = run(["--json"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "uuid-alice"
    assert data[0]["name"] == "Alice"
    assert data[0]["days_since_touched"] == 49


def _clock(fixed_date: date) -> Any:
    from cli_friendkeeper.clock import FixedClock

    return FixedClock(fixed_date)
