"""Tests for the rebuild-state subcommand (run_rebuild_state.py)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from cli_friendkeeper.models import ContactState, LogEntry
from cli_friendkeeper.repository import ContactRepo, LogRepo
from cli_friendkeeper.store import read_jsonl
from conftest import FakeStore


class FakeContext:
    """Duck-typed Context for testing rebuild-state."""

    def __init__(
        self,
        contacts: ContactRepo,
        log: LogRepo,
        data_dir: Path,
    ) -> None:
        self.contacts = contacts
        self.log = log
        self.data_dir = data_dir


def _log_entry(
    action: str,
    name: str,
    year: int = 2026,
    month: int = 1,
    day: int = 1,
    hour: int = 12,
    minute: int = 0,
) -> LogEntry:
    return LogEntry(
        timestamp=datetime(year, month, day, hour, minute, tzinfo=timezone.utc),
        action=action,  # type: ignore[arg-type]
        name=name,
    )


def _read_state(path: Path) -> list[ContactState]:
    return [ContactState.from_dict(d) for d in read_jsonl(path / "state.jsonl")]


class TestRebuildState:
    def test_given_add_touch_log_when_rebuild_then_state_has_last_touched_and_count(
        self, capsys: Any, tmp_path: Path
    ) -> None:
        """given add+touch log entries when rebuild then state has last_touched and touch_count=1."""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        ctx = FakeContext(contacts, log, data_dir)

        log.append(_log_entry("add", "alice"))
        log.append(_log_entry("touch", "alice", day=15))

        from cli_friendkeeper.ccli.task.run_rebuild_state import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "Rebuilt state from 2 log entries." in captured.out

        rebuilt = _read_state(data_dir)
        assert len(rebuilt) == 1
        alice = rebuilt[0]
        assert alice.name == "alice"
        assert alice.last_touched == date(2026, 1, 15)
        assert alice.touch_count == 1
        assert alice.removed is False

    def test_given_add_touch_remove_log_when_rebuild_then_state_removed(
        self, capsys: Any, tmp_path: Path
    ) -> None:
        """given add+touch+remove log entries when rebuild then state has removed=True."""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        ctx = FakeContext(contacts, log, data_dir)

        log.append(_log_entry("add", "bob"))
        log.append(_log_entry("touch", "bob", day=10))
        log.append(_log_entry("remove", "bob", day=20))

        from cli_friendkeeper.ccli.task.run_rebuild_state import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "Rebuilt state from 3 log entries." in captured.out

        rebuilt = _read_state(data_dir)
        assert len(rebuilt) == 1
        bob = rebuilt[0]
        assert bob.name == "bob"
        assert bob.removed is True
        assert bob.removed_at == date(2026, 1, 20)
        assert bob.last_touched == date(2026, 1, 10)
        assert bob.touch_count == 1

    def test_given_dry_run_when_rebuild_then_state_not_written(
        self, capsys: Any, tmp_path: Path
    ) -> None:
        """given --dry-run when rebuild then prints dry-run message and no state is written."""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        ctx = FakeContext(contacts, log, data_dir)

        log.append(_log_entry("add", "carol"))

        from cli_friendkeeper.ccli.task.run_rebuild_state import run

        rc = run(["--dry-run"], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "Dry run:" in captured.out

        rebuilt = _read_state(data_dir)
        assert len(rebuilt) == 0

    def test_given_empty_log_when_rebuild_then_empty_state(
        self, capsys: Any, tmp_path: Path
    ) -> None:
        """given empty log when rebuild then prints message and state file has no entries."""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        ctx = FakeContext(contacts, log, data_dir)

        from cli_friendkeeper.ccli.task.run_rebuild_state import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "Rebuilt state from 0 log entries." in captured.out

        rebuilt = _read_state(data_dir)
        assert len(rebuilt) == 0

    def test_given_multiple_touches_when_rebuild_then_touch_count_accumulates(
        self, capsys: Any, tmp_path: Path
    ) -> None:
        """given multiple touch log entries when rebuild then touch_count reflects all touches."""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        ctx = FakeContext(contacts, log, data_dir)

        log.append(_log_entry("add", "dave"))
        log.append(_log_entry("touch", "dave", day=5))
        log.append(_log_entry("touch", "dave", day=12))
        log.append(_log_entry("touch", "dave", day=19))

        from cli_friendkeeper.ccli.task.run_rebuild_state import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "Rebuilt state from 4 log entries." in captured.out

        rebuilt = _read_state(data_dir)
        assert len(rebuilt) == 1
        dave = rebuilt[0]
        assert dave.name == "dave"
        assert dave.touch_count == 3
        assert dave.last_touched == date(2026, 1, 19)

    def test_given_rebuild_state_entries_when_rebuild_then_ignored(
        self, capsys: Any, tmp_path: Path
    ) -> None:
        """given rebuild-state log entries when rebuild then they are ignored."""
        store = FakeStore()
        data_dir = tmp_path
        contacts = ContactRepo(store, data_dir)
        log = LogRepo(store, data_dir)
        ctx = FakeContext(contacts, log, data_dir)

        log.append(_log_entry("add", "eve"))
        log.append(_log_entry("rebuild-state", "eve"))

        from cli_friendkeeper.ccli.task.run_rebuild_state import run

        rc = run([], ctx)
        captured = capsys.readouterr()

        assert rc == 0
        assert "Rebuilt state from 2 log entries." in captured.out

        rebuilt = _read_state(data_dir)
        assert len(rebuilt) == 1
        eve = rebuilt[0]
        assert eve.name == "eve"
        assert eve.last_touched is None
        assert eve.touch_count == 0
