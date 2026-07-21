from __future__ import annotations


class FriendError(Exception):
    """Base error for the friendkeeper domain."""


class ConfigError(FriendError):
    """Invalid configuration."""


class InvalidPriorityError(FriendError):
    """Unknown priority value."""


class StorageError(FriendError):
    """File-system level storage failure."""


class ContactAlreadyExistsError(FriendError):
    """Contact already exists on insert."""


class ContactNotFoundError(FriendError):
    """Contact not found by id."""

    def __init__(self, message: str, contact_id: str) -> None:
        self.contact_id = contact_id
        super().__init__(message)


class InvalidEmailError(FriendError):
    """Email validation failed."""

    def __init__(self, message: str, email: str | None = None) -> None:
        self.email = email
        super().__init__(message)


class LockError(FriendError):
    """File lock acquisition failure."""
