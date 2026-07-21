from __future__ import annotations

from cli_friendkeeper.errors import (
    ConfigError,
    ContactAlreadyExistsError,
    ContactNotFoundError,
    FriendError,
    InvalidEmailError,
    InvalidPriorityError,
    LockError,
    StorageError,
)


def test_given_friend_error_when_raised_then_is_exception() -> None:
    e = FriendError("domain error")

    assert isinstance(e, Exception)
    assert str(e) == "domain error"


def test_given_config_error_when_raised_then_is_friend_error() -> None:
    e = ConfigError("bad config")

    assert isinstance(e, FriendError)
    assert isinstance(e, Exception)
    assert str(e)


def test_given_invalid_priority_error_when_raised_then_is_friend_error() -> None:
    e = InvalidPriorityError("unknown priority: foo")

    assert isinstance(e, FriendError)
    assert isinstance(e, Exception)
    assert str(e)


def test_given_storage_error_when_raised_then_is_friend_error() -> None:
    e = StorageError("disk full")

    assert isinstance(e, FriendError)
    assert isinstance(e, Exception)
    assert str(e)


def test_given_contact_not_found_error_when_raised_then_has_contact_id_attr() -> None:
    e = ContactNotFoundError("not found", contact_id="some-id")

    assert isinstance(e, FriendError)
    assert isinstance(e, Exception)
    assert e.contact_id == "some-id"
    assert str(e)


def test_given_contact_already_exists_error_when_raised_then_is_friend_error() -> None:
    e = ContactAlreadyExistsError("already exists")

    assert isinstance(e, FriendError)
    assert isinstance(e, Exception)
    assert str(e)


def test_given_invalid_email_error_when_raised_then_has_email_attr() -> None:
    e = InvalidEmailError("bad email", email="foo")

    assert isinstance(e, FriendError)
    assert isinstance(e, Exception)
    assert e.email == "foo"
    assert str(e)


def test_given_lock_error_when_raised_then_is_friend_error() -> None:
    e = LockError("could not acquire lock")

    assert isinstance(e, FriendError)
    assert isinstance(e, Exception)
    assert str(e)
