from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from cli_friendkeeper.clock import FixedClock
from cli_friendkeeper.config import Config, DEFAULT_CADENCE
from cli_friendkeeper.models import Contact, ContactState
from cli_friendkeeper.repository import ContactRepo, StateRepo, LogRepo
from conftest import FakeStore


class FakeContext:
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


def test_given_no_contacts_when_catch_up_then_nothing_to_catch_up(capsys: Any, tmp_path: Path) -> None:
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    from cli_friendkeeper.ccli.task.run_catch_up import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Nothing to catch up on." in captured.out


def test_given_no_due_contacts_when_catch_up_then_nothing_to_catch_up(capsys: Any, tmp_path: Path) -> None:
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="casual"),
    ])
    store.write_jsonl_atomic(
        data_dir / "state.jsonl",
        [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 19)).to_dict()],
    )

    from cli_friendkeeper.ccli.task.run_catch_up import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Nothing to catch up on." in captured.out


def test_given_due_contact_when_touch_then_state_updated_and_logged(monkeypatch: Any, capsys: Any, tmp_path: Path) -> None:
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="casual"),
    ])

    responses: list[str] = ["y", "Caught up over coffee"]
    monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

    from cli_friendkeeper.ccli.task.run_catch_up import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice — touched" in captured.out

    state_result = states.get("uuid-alice")
    assert state_result.is_right()
    assert state_result.value.last_touched == date(2026, 7, 20)
    assert state_result.value.touch_count == 1

    log_entries = log.all()
    assert len(log_entries) == 1
    assert log_entries[0].action == "touch"
    assert log_entries[0].payload == {"note": "Caught up over coffee"}


def test_given_due_contact_when_nope_then_snoozed_one_day(monkeypatch: Any, capsys: Any, tmp_path: Path) -> None:
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="casual"),
    ])

    responses: list[str] = ["n"]
    monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

    from cli_friendkeeper.ccli.task.run_catch_up import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice — noped (1d)" in captured.out

    state_result = states.get("uuid-alice")
    assert state_result.is_right()
    assert state_result.value.last_touched == date(2026, 7, 21)
    assert state_result.value.touch_count == 0

    log_entries = log.all()
    assert len(log_entries) == 0


def test_given_due_contact_when_snooze_then_last_touched_in_future(monkeypatch: Any, capsys: Any, tmp_path: Path) -> None:
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="casual"),
    ])

    responses: list[str] = ["s", "30"]
    monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

    from cli_friendkeeper.ccli.task.run_catch_up import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice — snoozed 30d" in captured.out

    state_result = states.get("uuid-alice")
    assert state_result.is_right()
    assert state_result.value.last_touched == date(2026, 8, 19)

    log_entries = log.all()
    assert len(log_entries) == 0


def test_given_due_contact_when_snooze_with_default_then_uses_priority_default(monkeypatch: Any, capsys: Any, tmp_path: Path) -> None:
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="deep"),
    ])

    responses: list[str] = ["s", ""]
    monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

    from cli_friendkeeper.ccli.task.run_catch_up import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice — snoozed 7d" in captured.out


def test_given_multiple_due_contacts_when_quit_mid_session_then_partial_processing(monkeypatch: Any, capsys: Any, tmp_path: Path) -> None:
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="casual"),
        Contact(id="uuid-bob", name="Bob", priority="casual"),
    ])

    responses: list[str] = ["y", "Coffee", "q"]
    monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

    from cli_friendkeeper.ccli.task.run_catch_up import run

    rc = run([], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "Alice — touched" in captured.out
    assert "Pending: 1" in captured.out

    state_alice = states.get("uuid-alice")
    assert state_alice.is_right()
    assert state_alice.value.last_touched == date(2026, 7, 20)

    all_states = states.all()
    assert len(all_states) == 1
    assert all_states[0].id == "uuid-alice"


def test_given_limit_one_when_catch_up_then_only_one_contact_shown(monkeypatch: Any, capsys: Any, tmp_path: Path) -> None:
    store = FakeStore()
    data_dir = tmp_path
    contacts = ContactRepo(store, data_dir)
    states = StateRepo(store, data_dir)
    log = LogRepo(store, data_dir)
    clock = FixedClock(date(2026, 7, 20))
    config = Config(cadence=DEFAULT_CADENCE)
    ctx = FakeContext(contacts, states, log, clock, config, data_dir)

    contacts._write_contacts([
        Contact(id="uuid-alice", name="Alice", priority="casual"),
        Contact(id="uuid-bob", name="Bob", priority="casual"),
    ])

    responses: list[str] = ["y", "", "q"]
    monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

    from cli_friendkeeper.ccli.task.run_catch_up import run

    rc = run(["1"], ctx)
    captured = capsys.readouterr()

    assert rc == 0
    assert "[1/1]" in captured.out
