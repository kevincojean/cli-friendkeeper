from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pymonad.either import Right

from cli_friendkeeper.errors import ContactAlreadyExistsError, ContactNotFoundError
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
    def test_given_empty_repo_when_adding_contact_then_can_get_by_name(self) -> None:
        store = FakeStore()
        repo = ContactRepo(store, Path("/tmp"))
        contact = Contact(name="jdoe", display_name="Jane Doe")

        result = repo.add(contact)

        assert result == Right(None)
        assert repo.get("jdoe") == Right(contact)

    def test_given_existing_contact_when_adding_duplicate_name_then_returns_left(
        self,
    ) -> None:
        store = FakeStore()
        repo = ContactRepo(store, Path("/tmp"))
        repo.add(Contact(name="jdoe", display_name="Jane Doe"))

        result = repo.add(Contact(name="JDOE", display_name="Jane Roe"))

        assert result.is_left()
        assert isinstance(result.monoid[0], ContactAlreadyExistsError)

    def test_given_empty_repo_when_getting_non_existent_then_returns_left(
        self,
    ) -> None:
        store = FakeStore()
        repo = ContactRepo(store, Path("/tmp"))

        result = repo.get("nobody")

        assert result.is_left()
        err = result.monoid[0]
        assert isinstance(err, ContactNotFoundError)
        assert err.name == "nobody"

    def test_given_multiple_contacts_when_all_then_sorted_by_name(
        self,
    ) -> None:
        store = FakeStore()
        repo = ContactRepo(store, Path("/tmp"))
        repo.add(Contact(name="zed", display_name="Zed"))
        repo.add(Contact(name="alice", display_name="Alice"))
        repo.add(Contact(name="bob", display_name="Bob"))

        contacts = repo.all()

        assert [c.name for c in contacts] == ["alice", "bob", "zed"]

    def test_given_existing_contact_when_removing_then_gone(self) -> None:
        store = FakeStore()
        repo = ContactRepo(store, Path("/tmp"))
        repo.add(Contact(name="jdoe", display_name="Jane Doe"))

        result = repo.remove("jdoe")

        assert result == Right(None)
        assert repo.get("jdoe").is_left()

    def test_given_empty_repo_when_removing_non_existent_then_returns_left(
        self,
    ) -> None:
        store = FakeStore()
        repo = ContactRepo(store, Path("/tmp"))

        result = repo.remove("nobody")

        assert result.is_left()
        err = result.monoid[0]
        assert isinstance(err, ContactNotFoundError)
        assert err.name == "nobody"


class TestStateRepo:
    def test_given_empty_repo_when_upserting_then_can_get_by_name(self) -> None:
        store = FakeStore()
        repo = StateRepo(store, Path("/tmp"))
        state = ContactState(name="jdoe", touch_count=1)

        result = repo.upsert(state)

        assert result == Right(None)
        assert repo.get("jdoe") == Right(state)

    def test_given_existing_state_when_upserting_then_updates(self) -> None:
        store = FakeStore()
        repo = StateRepo(store, Path("/tmp"))
        repo.upsert(ContactState(name="jdoe", touch_count=1))

        updated = ContactState(name="jdoe", touch_count=5)
        result = repo.upsert(updated)

        assert result == Right(None)
        assert repo.get("jdoe") == Right(updated)

    def test_given_empty_repo_when_getting_non_existent_then_returns_left(
        self,
    ) -> None:
        store = FakeStore()
        repo = StateRepo(store, Path("/tmp"))

        result = repo.get("nobody")

        assert result.is_left()
        err = result.monoid[0]
        assert isinstance(err, ContactNotFoundError)
        assert err.name == "nobody"

    def test_given_multiple_states_when_all_then_sorted_by_name(self) -> None:
        store = FakeStore()
        repo = StateRepo(store, Path("/tmp"))
        repo.upsert(ContactState(name="zed"))
        repo.upsert(ContactState(name="alice"))
        repo.upsert(ContactState(name="bob"))

        states = repo.all()

        assert [s.name for s in states] == ["alice", "bob", "zed"]


class TestLogRepo:
    def test_given_log_entries_when_all_then_sorted_by_timestamp(self) -> None:
        store = FakeStore()
        repo = LogRepo(store, Path("/tmp"))
        entry1 = LogEntry(
            timestamp=datetime(2025, 6, 1, 12, 0, 0),
            action="add",
            name="jdoe",
        )
        entry2 = LogEntry(
            timestamp=datetime(2025, 6, 2, 12, 0, 0),
            action="touch",
            name="jdoe",
        )

        repo.append(entry1)
        repo.append(entry2)

        assert repo.all() == [entry1, entry2]

    def test_given_empty_log_when_all_then_empty_list(self) -> None:
        store = FakeStore()
        repo = LogRepo(store, Path("/tmp"))

        assert repo.all() == []
