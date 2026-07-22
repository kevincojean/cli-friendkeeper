# ruff: noqa: F841
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


# ── Acquaintance auto-upgrade on touch ────────────────────

class TestCatchUpAcquaintanceAutoUpgrade:
    def test_given_acquaintance_in_warm_up_zero_snoozes_when_touch_then_upgraded_to_casual(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance snooze_count=0, warm_up_consumed=False when touch in catch-up then priority upgraded to casual"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        contact_result = contacts.get("uuid-alice")
        assert contact_result.is_right()
        assert contact_result.value.priority == "casual"

    def test_given_acquaintance_in_warm_up_zero_snoozes_when_touch_then_warm_up_consumed(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance touched when auto-upgrade then warm_up_consumed=True on new casual state"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.warm_up_consumed is True

    def test_given_acquaintance_in_warm_up_zero_snoozes_when_touch_then_stdout_logs_upgrade(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance auto-upgraded when touch then stdout contains 'Upgraded Alice from acquaintance → casual'"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "Upgraded" in captured.out
        assert "Alice" in captured.out
        assert "acquaintance" in captured.out
        assert "casual" in captured.out

    def test_given_acquaintance_auto_upgrade_disabled_when_touch_then_no_upgrade(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance.auto_upgrade=False when touch then priority stays acquaintance, no upgrade message"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance", auto_upgrade=False),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        contact_result = contacts.get("uuid-alice")
        assert contact_result.is_right()
        assert contact_result.value.priority == "acquaintance"
        assert "Upgraded" not in captured.out

    def test_given_acquaintance_snooze_count_exceeds_max_when_touch_then_no_upgrade(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance snooze_count=3, max=2 when touch then no upgrade, just logs touch"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=3, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        contact_result = contacts.get("uuid-alice")
        assert contact_result.is_right()
        assert contact_result.value.priority == "acquaintance"
        assert "Alice — touched" in captured.out

    def test_given_acquaintance_snooze_count_exceeds_max_when_touch_then_warm_up_consumed(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance snooze_count>max when touch then warm_up_consumed=True"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=3, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.warm_up_consumed is True

    def test_given_acquaintance_upgraded_when_touch_then_enters_casual_warm_up(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance upgraded to casual when touch then new state has warm_up_consumed=False (enters casual warm-up 15d)"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.warm_up_consumed is False

    def test_given_acquaintance_upgraded_when_touch_then_log_entry_records_upgrade(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance upgraded when touch then LogEntry action='upgrade' with from/to in payload"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        log_entries = log.all()
        upgrade_entries = [e for e in log_entries if e.action == "upgrade"]
        assert len(upgrade_entries) == 1
        assert upgrade_entries[0].name == "Alice"
        assert upgrade_entries[0].payload.get("from") == "acquaintance"
        assert upgrade_entries[0].payload.get("to") == "casual"


# ── Acquaintance snooze counter & relegation ──────────────

class TestCatchUpAcquaintanceSnoozeRelegation:
    def test_given_acquaintance_first_snooze_when_snooze_then_snooze_count_increments(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance snooze_count=0 when snooze then snooze_count=1"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 1

    def test_given_acquaintance_second_snooze_when_snooze_then_snooze_count_increments(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance snooze_count=1 when snooze then snooze_count=2"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=1, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 2

    def test_given_acquaintance_snooze_count_at_max_when_snooze_then_relegated(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance snooze_count=2, max=2 when snooze (3rd) then count=3 > max=2 → relegated"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=2, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 3
        assert state_result.value.warm_up_consumed is True

    def test_given_acquaintance_relegated_when_snooze_then_warm_up_consumed(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance relegated when snooze then warm_up_consumed=True"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=2, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.warm_up_consumed is True

    def test_given_acquaintance_relegated_when_snooze_then_stdout_logs_relegation(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance relegated when snooze then stdout contains 'relegated' and 'cadence=0' or 'no-due'"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=2, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "relegated" in captured.out.lower()
        assert "cadence" in captured.out.lower() or "no-due" in captured.out.lower()

    def test_given_acquaintance_relegated_when_snooze_then_log_entry_records_relegation(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance relegated when snooze then LogEntry action='relegate' with payload"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=2, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        log_entries = log.all()
        relegate_entries = [e for e in log_entries if e.action == "relegate"]
        assert len(relegate_entries) == 1
        assert relegate_entries[0].name == "Alice"

    def test_given_acquaintance_relegated_when_next_due_then_not_due(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance relegated (warm_up_consumed=True) when next catch-up then not in due list"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=0, warm_up_consumed=True).to_dict()],
        )

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "Nothing to catch up on" in captured.out or "Alice" not in captured.out

    def test_given_acquaintance_snooze_count_persists_across_sessions(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance snoozed once in session 1 when session 2 and snoozed again then snooze_count=2"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        # Session 1: snooze once
        responses1: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses1.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc1 = run([], ctx)
        assert rc1 == 0

        # Session 2: snooze again (same clock)
        responses2: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses2.pop(0))

        rc2 = run([], ctx)
        captured2 = capsys.readouterr()

        assert rc2 == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 2


# ── Casual warm-up consumption ────────────────────────────

class TestCatchUpCasualWarmUp:
    def test_given_casual_in_warm_up_when_touch_then_warm_up_consumed(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given casual warm_up_consumed=False when touch then warm_up_consumed=True"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="casual"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.warm_up_consumed is True

    def test_given_casual_in_warm_up_when_touch_then_stdout_logs_warm_up_complete(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given casual warm-up consumed when touch then stdout contains 'warm-up complete' and 'regular cadence (45d)'"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="casual"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "warm-up" in captured.out.lower()
        assert "regular cadence" in captured.out.lower() or "45d" in captured.out

    def test_given_casual_warm_up_consumed_when_next_due_then_uses_regular_cadence(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given casual warm_up_consumed=True when next catch-up then due based on regular cadence 45d"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        # Last touched 40 days ago, warm-up consumed → not due (casual cadence=45)
        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="casual"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 6, 10), snooze_count=0, warm_up_consumed=True).to_dict()],
        )

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "Nothing to catch up on" in captured.out

    def test_given_casual_snooze_count_at_max_when_snooze_then_warm_up_consumed(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given casual snooze_count=3, max=3 when snooze (4th) then count=4 > max=3 → warm_up_consumed=True"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="casual"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=3, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 4
        assert state_result.value.warm_up_consumed is True

    def test_given_casual_snooze_count_exceeds_max_when_snooze_then_stdout_logs_warm_up_complete(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given casual snooze exceeds max when snooze then stdout contains 'warm-up complete' and 'regular cadence (45d)'"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="casual"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=3, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "warm-up" in captured.out.lower()
        assert "regular cadence" in captured.out.lower() or "45d" in captured.out

    def test_given_casual_snooze_below_max_when_snooze_then_still_in_warm_up(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given casual snooze_count=1, max=3 when snooze then warm_up_consumed=False, still uses warm-up cadence"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="casual"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=1, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 2
        assert state_result.value.warm_up_consumed is False

    def test_given_casual_snooze_counter_increments(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given casual snooze_count=0 when snooze then snooze_count=1"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="casual"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 1


# ── Snooze counter does NOT reset on touch ────────────────

class TestSnoozeCounterNoReset:
    def test_given_acquaintance_snoozed_once_then_touched_then_snooze_count_unchanged(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance snooze_count=1 when touch then snooze_count stays 1 (no reset)"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=1, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 1

    def test_given_casual_snoozed_twice_then_touched_then_snooze_count_unchanged(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given casual snooze_count=2 when touch then snooze_count stays 2 (no reset)"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="casual"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=2, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 2


# ── Nope increments snooze counter ────────────────────────

class TestNopeIncrementsSnoozeCounter:
    def test_given_acquaintance_when_nope_then_snooze_count_increments(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance snooze_count=0 when nope (1d snooze) then snooze_count=1"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["n"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 1

    def test_given_casual_when_nope_then_snooze_count_increments(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given casual snooze_count=0 when nope then snooze_count=1"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="casual"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["n"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 1

    def test_given_acquaintance_noped_twice_then_snoozed_once_then_relegated(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance nope×2 then snooze (3rd) when snooze_count=3 > max=2 then relegated"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=True,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 5), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        # First session: nope
        responses1: list[str] = ["n"]
        monkeypatch.setattr("builtins.input", lambda _: responses1.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc1 = run([], ctx)
        assert rc1 == 0

        # Second session: nope
        responses2: list[str] = ["n"]
        monkeypatch.setattr("builtins.input", lambda _: responses2.pop(0))

        rc2 = run([], ctx)
        assert rc2 == 0

        # Third session: snooze → relegated (snooze_count=3 > max=2)
        responses3: list[str] = ["s", ""]
        monkeypatch.setattr("builtins.input", lambda _: responses3.pop(0))

        rc3 = run([], ctx)
        captured3 = capsys.readouterr()

        assert rc3 == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.snooze_count == 3
        assert state_result.value.warm_up_consumed is True


# ── Config toggle: auto_upgrade=false ────────────────────

class TestAutoUpgradeToggle:
    def test_given_auto_upgrade_false_when_acquaintance_touch_then_stays_acquaintance(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance.auto_upgrade=False when touch in catch-up then priority stays acquaintance"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=False,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        contact_result = contacts.get("uuid-alice")
        assert contact_result.is_right()
        assert contact_result.value.priority == "acquaintance"

    def test_given_auto_upgrade_false_when_acquaintance_touch_then_warm_up_consumed(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance.auto_upgrade=False when touch then warm_up_consumed=True (no warm-up anymore)"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=False,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        state_result = states.get("uuid-alice")
        assert state_result.is_right()
        assert state_result.value.warm_up_consumed is True

    def test_given_auto_upgrade_false_when_acquaintance_touch_then_no_upgrade_message(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance.auto_upgrade=False when touch then stdout has no 'Upgraded' message"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=False,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "Upgraded" not in captured.out

    def test_given_auto_upgrade_false_when_acquaintance_touch_then_logs_touch_normally(
        self, monkeypatch: Any, capsys: Any, tmp_path: Path
    ) -> None:
        """given acquaintance.auto_upgrade=False when touch then 'Alice — touched' still printed"""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        states = StateRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        clock = FixedClock(date(2026, 7, 20))
        config = Config(
            cadence=DEFAULT_CADENCE,
            warm_up={"acquaintance": 30, "casual": 15},
            warm_up_max_snoozes={"acquaintance": 2, "casual": 3},
            acquaintance_auto_upgrade=False,
        )
        ctx = FakeContext(contacts, states, log, clock, config, data_dir)

        contacts._write_contacts([
            Contact(id="uuid-alice", name="Alice", priority="acquaintance"),
        ])
        store.write_jsonl_atomic(
            data_dir / "state.jsonl",
            [ContactState(id="uuid-alice", name="Alice", last_touched=date(2026, 7, 6), snooze_count=0, warm_up_consumed=False).to_dict()],
        )

        responses: list[str] = ["y", "Caught up!"]
        monkeypatch.setattr("builtins.input", lambda _: responses.pop(0))

        from cli_friendkeeper.ccli.task.run_catch_up import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "Alice" in captured.out
        assert "touched" in captured.out
