from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pymonad.either import Right

from cli_friendkeeper.errors import ContactNotFoundError
from cli_friendkeeper.models import Contact, ContactState, LogEntry
from cli_friendkeeper.repository import ContactRepo, LogRepo, StateRepo


class FakeStore:
    def __init__(self):
        self._files: dict[str, list[dict]] = {}

    def append_jsonl(self, path, obj):
        key = str(path)
        self._files.setdefault(key, [])
        self._files[key].append(obj)

    def read_jsonl(self, path):
        return list(self._files.get(str(path), []))

    def write_jsonl_atomic(self, path, objects):
        self._files[str(path)] = list(objects)


class TestContactRepo:
    def test_given_empty_repo_when_adding_contact_then_can_get_by_id(self) -> None:
        store = FakeStore()
        repo = ContactRepo(store, Path("/tmp"))
        contact = Contact(id="test-uuid-jdoe", name="Jane Doe")

        result = repo.add(contact)

        assert result == Right(None)
        assert repo.get("test-uuid-jdoe") == Right(contact)

    def test_given_empty_repo_when_getting_non_existent_then_returns_left(
        self,
    ) -> None:
        store = FakeStore()
        repo = ContactRepo(store, Path("/tmp"))

        result = repo.get("nonexistent-id")

        assert result.is_left()
        err = result.monoid[0]
        assert isinstance(err, ContactNotFoundError)
        assert err.contact_id == "nonexistent-id"

    def test_given_multiple_contacts_when_all_then_sorted_by_name(
        self,
    ) -> None:
        store = FakeStore()
        repo = ContactRepo(store, Path("/tmp"))
        repo.add(Contact(id="uuid-zed", name="Zed"))
        repo.add(Contact(id="uuid-alice", name="Alice"))
        repo.add(Contact(id="uuid-bob", name="Bob"))

        contacts = repo.all()

        assert [c.name for c in contacts] == ["Alice", "Bob", "Zed"]

    def test_given_existing_contact_when_removing_then_gone(self) -> None:
        store = FakeStore()
        repo = ContactRepo(store, Path("/tmp"))
        contact = Contact(id="test-uuid-jdoe", name="Jane Doe")
        repo.add(contact)

        result = repo.remove(contact.id)

        assert result == Right(None)
        assert repo.get(contact.id).is_left()

    def test_given_empty_repo_when_removing_non_existent_then_returns_left(
        self,
    ) -> None:
        store = FakeStore()
        repo = ContactRepo(store, Path("/tmp"))

        result = repo.remove("nonexistent-id")

        assert result.is_left()
        err = result.monoid[0]
        assert isinstance(err, ContactNotFoundError)
        assert err.contact_id == "nonexistent-id"


class TestStateRepo:
    def test_given_empty_repo_when_upserting_then_can_get_by_id(self) -> None:
        store = FakeStore()
        repo = StateRepo(store, Path("/tmp"))
        state = ContactState(id="test-uuid-jdoe", name="jdoe", touch_count=1)

        result = repo.upsert(state)

        assert result == Right(None)
        assert repo.get("test-uuid-jdoe") == Right(state)

    def test_given_existing_state_when_upserting_then_updates(self) -> None:
        store = FakeStore()
        repo = StateRepo(store, Path("/tmp"))
        repo.upsert(ContactState(id="test-uuid-jdoe", name="jdoe", touch_count=1))

        updated = ContactState(id="test-uuid-jdoe", name="jdoe", touch_count=5)
        result = repo.upsert(updated)

        assert result == Right(None)
        assert repo.get("test-uuid-jdoe") == Right(updated)

    def test_given_empty_repo_when_getting_non_existent_then_returns_left(
        self,
    ) -> None:
        store = FakeStore()
        repo = StateRepo(store, Path("/tmp"))

        result = repo.get("nonexistent-id")

        assert result.is_left()
        err = result.monoid[0]
        assert isinstance(err, ContactNotFoundError)
        assert err.contact_id == "nonexistent-id"

    def test_given_multiple_states_when_all_then_sorted_by_name(self) -> None:
        store = FakeStore()
        repo = StateRepo(store, Path("/tmp"))
        repo.upsert(ContactState(id="uuid-zed", name="Zed"))
        repo.upsert(ContactState(id="uuid-alice", name="Alice"))
        repo.upsert(ContactState(id="uuid-bob", name="Bob"))

        states = repo.all()

        assert [s.name for s in states] == ["Alice", "Bob", "Zed"]


class TestLogRepo:
    def test_given_log_entries_when_all_then_sorted_by_timestamp(self) -> None:
        store = FakeStore()
        repo = LogRepo(store, Path("/tmp"))
        entry1 = LogEntry(
            timestamp=datetime(2025, 6, 1, 12, 0, 0),
            action="add",
            id="test-uuid-jdoe",
            name="jdoe",
        )
        entry2 = LogEntry(
            timestamp=datetime(2025, 6, 2, 12, 0, 0),
            action="touch",
            id="test-uuid-jdoe",
            name="jdoe",
        )

        repo.append(entry1)
        repo.append(entry2)

        assert repo.all() == [entry1, entry2]

    def test_given_empty_log_when_all_then_empty_list(self) -> None:
        store = FakeStore()
        repo = LogRepo(store, Path("/tmp"))

        assert repo.all() == []


class TestStateRepoWarmUp:
    def test_given_state_with_snooze_count_when_upsert_then_persisted(
        self, fake_store: Any, tmp_data_dir: Path
    ) -> None:
        """given ContactState(snooze_count=2) when upsert then get returns snooze_count=2"""
        repo = StateRepo(fake_store, tmp_data_dir)

        state = ContactState(id="uuid-snooze", name="Snoozy", snooze_count=2)
        result = repo.upsert(state)

        assert result == Right(None)
        got = repo.get("uuid-snooze")
        assert got == Right(state)

    def test_given_state_with_warm_up_consumed_when_upsert_then_persisted(
        self, fake_store: Any, tmp_data_dir: Path
    ) -> None:
        """given ContactState(warm_up_consumed=True) when upsert then get returns warm_up_consumed=True"""
        repo = StateRepo(fake_store, tmp_data_dir)

        state = ContactState(id="uuid-warm", name="Warmy", warm_up_consumed=True)
        result = repo.upsert(state)

        assert result == Right(None)
        got = repo.get("uuid-warm")
        assert got == Right(state)

    def test_given_old_state_without_new_fields_when_read_then_defaults_applied(
        self, fake_store: Any, tmp_data_dir: Path
    ) -> None:
        """given state.jsonl without snooze_count/warm_up_consumed when read then defaults (0, False) applied"""
        from datetime import date

        repo = StateRepo(fake_store, tmp_data_dir)

        fake_store.write_jsonl_atomic(
            tmp_data_dir / "state.jsonl",
            [
                {
                    "id": "uuid-old",
                    "name": "Oldie",
                    "last_touched": "2026-01-01",
                    "touch_count": 1,
                    "removed": False,
                }
            ],
        )

        got = repo.get("uuid-old")
        assert not got.is_left()
        state = got.value
        assert state.snooze_count == 0
        assert state.warm_up_consumed is False
