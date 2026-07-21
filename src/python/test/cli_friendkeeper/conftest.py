"""Test configuration: ensure the main package is importable and provide shared fixtures."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import sys

# The main ``cli_friendkeeper`` package lives under ``src/python/main``.
# When pytest discovers tests under ``src/python/test``, the test-directory
# ``cli_friendkeeper`` package (which has no sub-modules) can shadow the
# real one.  Insert the main source tree first so imports resolve correctly.
_main_src = str(Path(__file__).resolve().parent.parent.parent / "main")
if _main_src not in sys.path:
    sys.path.insert(0, _main_src)

import pytest

from cli_friendkeeper.clock import FixedClock
from cli_friendkeeper.config import Config, DEFAULT_CADENCE
from cli_friendkeeper.models import Contact, ContactState
from cli_friendkeeper.repository import ContactRepo, LogRepo, StateRepo


class FakeStore:
    """In-memory store that implements the store module's protocol (append_jsonl, read_jsonl, write_jsonl_atomic)."""

    def __init__(self) -> None:
        self._files: dict[str, list[dict[str, Any]]] = {}

    def append_jsonl(self, path: Path, obj: dict[str, Any]) -> None:
        key = str(path)
        self._files.setdefault(key, [])
        self._files[key].append(obj)

    def read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        return list(self._files.get(str(path), []))

    def write_jsonl_atomic(self, path: Path, objects: list[dict[str, Any]]) -> None:
        self._files[str(path)] = list(objects)


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def fake_store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(date(2026, 1, 1))


@pytest.fixture
def clock_march_1() -> FixedClock:
    return FixedClock(date(2026, 3, 1))


@pytest.fixture
def default_config() -> Config:
    return Config(cadence=DEFAULT_CADENCE)


@pytest.fixture
def contact_repo(fake_store: FakeStore, tmp_data_dir: Path) -> ContactRepo:
    return ContactRepo(fake_store, tmp_data_dir)


@pytest.fixture
def state_repo(fake_store: FakeStore, tmp_data_dir: Path) -> StateRepo:
    return StateRepo(fake_store, tmp_data_dir)


@pytest.fixture
def log_repo(fake_store: FakeStore, tmp_data_dir: Path) -> LogRepo:
    return LogRepo(fake_store, tmp_data_dir)


@pytest.fixture
def sample_contact() -> Contact:
    return Contact(
        id="test-uuid-alice",
        name="Alice Smith",
        email="alice@example.com",
        priority="deep",
        cadence_days=7,
        notes="",
        added_at=date(2026, 1, 1),
    )


@pytest.fixture
def sample_state() -> ContactState:
    return ContactState(
        id="test-uuid-alice",
        name="Alice Smith",
        last_touched=date(2026, 1, 1),
        touch_count=1,
        removed=False,
        removed_at=None,
    )
