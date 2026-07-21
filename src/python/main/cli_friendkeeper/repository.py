"""Repository layer for Contact, ContactState, and LogEntry persistence.

Each repository takes a duck-typed *store* (any object with
``append_jsonl``, ``read_jsonl``, and ``write_jsonl_atomic`` methods) and a
``data_dir`` path, avoiding direct imports from the ``store`` module so that
callers may inject a fake for testing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pymonad.either import Either, Left, Right

from cli_friendkeeper.errors import (
    ContactNotFoundError,
    FriendError,
)
from cli_friendkeeper.models import Contact, ContactState, LogEntry


class ContactRepo:
    def __init__(self, store: Any, data_dir: Path) -> None:
        self._store = store
        self._data_dir = data_dir

    @property
    def _contacts_path(self) -> Path:
        return self._data_dir / "friends.jsonl"

    def _read_contacts(self) -> list[Contact]:
        raw = self._store.read_jsonl(self._contacts_path)
        return [Contact.from_dict(d) for d in raw]

    def _write_contacts(self, contacts: list[Contact]) -> None:
        self._store.write_jsonl_atomic(
            self._contacts_path, [c.to_dict() for c in contacts]
        )

    def add(self, contact: Contact) -> Either[FriendError, None]:
        self._store.append_jsonl(self._contacts_path, contact.to_dict())
        return Right(None)

    def get(self, contact_id: str) -> Either[FriendError, Contact]:
        for c in self._read_contacts():
            if c.id == contact_id:
                return Right(c)
        return Left(
            ContactNotFoundError(f"Contact '{contact_id}' not found", contact_id=contact_id)
        )

    def all(self) -> list[Contact]:
        contacts = self._read_contacts()
        contacts.sort(key=lambda c: c.name.lower())
        return contacts

    def remove(self, contact_id: str) -> Either[FriendError, None]:
        existing = self._read_contacts()
        filtered = [c for c in existing if c.id != contact_id]
        if len(filtered) == len(existing):
            return Left(
                ContactNotFoundError(
                    f"Contact '{contact_id}' not found", contact_id=contact_id
                )
            )
        self._write_contacts(filtered)
        return Right(None)


class StateRepo:
    def __init__(self, store: Any, data_dir: Path) -> None:
        self._store = store
        self._data_dir = data_dir

    @property
    def _state_path(self) -> Path:
        return self._data_dir / "state.jsonl"

    def _read_states(self) -> list[ContactState]:
        raw = self._store.read_jsonl(self._state_path)
        return [ContactState.from_dict(d) for d in raw]

    def get(self, contact_id: str) -> Either[FriendError, ContactState]:
        for s in self._read_states():
            if s.id == contact_id:
                return Right(s)
        return Left(
            ContactNotFoundError(f"State for '{contact_id}' not found", contact_id=contact_id)
        )

    def upsert(self, state: ContactState) -> Either[FriendError, None]:
        existing = self._read_states()
        new_list = [
            state if s.id == state.id else s
            for s in existing
        ]
        if all(s.id != state.id for s in existing):
            new_list.append(state)
        self._store.write_jsonl_atomic(
            self._state_path, [s.to_dict() for s in new_list]
        )
        return Right(None)

    def all(self) -> list[ContactState]:
        states = self._read_states()
        states.sort(key=lambda s: s.name.lower())
        return states


class LogRepo:
    def __init__(self, store: Any, data_dir: Path) -> None:
        self._store = store
        self._data_dir = data_dir

    @property
    def _log_path(self) -> Path:
        return self._data_dir / "log.jsonl"

    def append(self, entry: LogEntry) -> Either[FriendError, None]:
        self._store.append_jsonl(self._log_path, entry.to_dict())
        return Right(None)

    def all(self) -> list[LogEntry]:
        raw = self._store.read_jsonl(self._log_path)
        entries = [LogEntry.from_dict(d) for d in raw]
        entries.sort(key=lambda e: e.timestamp)
        return entries
