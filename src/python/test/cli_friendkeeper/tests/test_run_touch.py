"""Tests for the ``touch`` subcommand (run_touch.py)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from cli_friendkeeper.config import Config, DEFAULT_CADENCE
from cli_friendkeeper.models import Contact, ContactState
from cli_friendkeeper.repository import ContactRepo, LogRepo, StateRepo
from conftest import FakeStore


class FakeContext:
    """Duck-typed Context that accepts injected repos and clock."""

    def __init__(
        self,
        contacts: ContactRepo,
        states: StateRepo,
        log: LogRepo,
        clock: Any,
        config: Config,
        data_dir: Path,
    ) -> None:
        self.contacts = contacts
        self.states = states
        self.log = log
        self.clock = clock
        self.config = config
        self.data_dir = data_dir


def test_given_existing_contact_when_touched_then_updates_state_and_appends_log(capsys: Any, tmp_path: Path) -> None:
    """given an existing contact when touched then updates state and appends log."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = _clock(date(2026, 1, 1))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="deep"),
    ])

    from cli_friendkeeper.ccli.task.run_touch import run

    rc = run(["uuid-alice"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Touched: Alice" in captured.out
    assert "uuid-alice" in captured.out

    state_result = states.get("uuid-alice")
    assert not state_result.is_left()
    state = state_result.value
    assert state.last_touched == date(2026, 1, 1)
    assert state.touch_count == 1

    entries = log.all()
    assert len(entries) == 1
    assert entries[0].action == "touch"
    assert entries[0].id == "uuid-alice"
    assert entries[0].name == "Alice"
    assert entries[0].payload == {"note": ""}


def test_given_nonexistent_contact_when_touched_then_returns_one_with_not_found(capsys: Any, tmp_path: Path) -> None:
    """given a nonexistent contact when touched then returns rc=1 with not found."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = _clock(date(2026, 1, 1))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    from cli_friendkeeper.ccli.task.run_touch import run

    rc = run(["unknown-id"], ctx)
    captured = capsys.readouterr()

    assert rc == 1
    assert "not found" in captured.err.lower()


def test_given_removed_contact_when_touched_then_returns_one_with_removed(capsys: Any, tmp_path: Path) -> None:
    """given a removed contact when touched then returns rc=1 with removed."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = _clock(date(2026, 1, 1))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="deep"),
    ])
    store.write_jsonl_atomic(
        data_dir / "state.jsonl",
        [
            ContactState(
                id="uuid-alice", name="Alice", removed=True, removed_at=date(2026, 1, 1)
            ).to_dict()
        ],
    )

    from cli_friendkeeper.ccli.task.run_touch import run

    rc = run(["uuid-alice"], ctx)
    captured = capsys.readouterr()

    assert rc == 1
    assert "removed" in captured.err.lower()


def test_given_existing_contact_when_touched_twice_then_touch_count_equals_two(capsys: Any, tmp_path: Path) -> None:
    """given an existing contact touched twice then touch_count == 2."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = _clock(date(2026, 1, 1))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="deep"),
    ])

    from cli_friendkeeper.ccli.task.run_touch import run

    rc1 = run(["uuid-alice"], ctx)
    assert rc1 == 0
    capsys.readouterr()

    rc2 = run(["uuid-alice"], ctx)
    assert rc2 == 0

    state_result = states.get("uuid-alice")
    assert not state_result.is_left()
    state = state_result.value
    assert state.touch_count == 2


def test_given_note_flag_when_touched_then_log_payload_contains_note(capsys: Any, tmp_path: Path) -> None:
    """given --note when touched then log payload contains the note."""
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = _clock(date(2026, 1, 1))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="deep"),
    ])

    from cli_friendkeeper.ccli.task.run_touch import run

    rc = run(["uuid-alice", "--note", "Sent birthday wishes"], ctx)
    assert rc == 0

    entries = log.all()
    assert len(entries) == 1
    assert entries[0].payload == {"note": "Sent birthday wishes"}


def _clock(fixed_date: date) -> Any:
    from cli_friendkeeper.clock import FixedClock

    return FixedClock(fixed_date)
