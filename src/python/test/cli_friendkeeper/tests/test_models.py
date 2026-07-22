from __future__ import annotations

from datetime import date, datetime

import pytest

from cli_friendkeeper.errors import InvalidEmailError
from cli_friendkeeper.models import Contact, ContactState, LogEntry, Priority


class TestContact:
    def test_given_contact_with_all_fields_when_to_dict_and_from_dict_then_round_trips(self) -> None:
        """given a Contact with all fields when to_dict then from_dict returns equal instance"""
        contact = Contact(
            id="test-uuid-jdoe",
            name="Jane Doe",
            email="jane@example.com",
            phone="+1-555-0100",
            priority="deep",
            cadence_days=14,
            notes="College buddy",
            added_at=date(2025, 6, 1),
        )
        d = contact.to_dict()
        restored = Contact.from_dict(d)
        assert restored == contact

    def test_given_contact_without_added_at_when_to_dict_then_omits_key(self) -> None:
        """given a Contact with no added_at when to_dict then key absent or None"""
        contact = Contact(id="test-uuid-jd", name="JD")
        d = contact.to_dict()
        assert "added_at" not in d or d["added_at"] is None

    def test_given_valid_email_when_validating_then_no_error(self) -> None:
        """given a valid email when validate then no exception"""
        contact = Contact(id="test-uuid-jd", name="JD", email="user@example.com")
        contact.validate()  # no raise

    def test_given_invalid_email_when_validating_then_raises_invalid_email_error(self) -> None:
        """given an invalid email when validate then raises InvalidEmailError"""
        contact = Contact(id="test-uuid-jd", name="JD", email="not-an-email")
        with pytest.raises(InvalidEmailError):
            contact.validate()

    def test_given_none_email_when_validating_then_no_error(self) -> None:
        """given None email when validate then no exception"""
        contact = Contact(id="test-uuid-jd", name="JD")
        contact.validate()  # no raise

    def test_given_minimal_contact_when_to_dict_then_omits_null_fields(self) -> None:
        """given a Contact with only required fields when to_dict then null fields omitted"""
        contact = Contact(id="test-uuid-jd", name="JD")
        d = contact.to_dict()
        assert "email" not in d
        assert "phone" not in d
        assert "cadence_days" not in d
        assert "added_at" not in d

    def test_given_contact_when_to_dict_then_preserves_falsy_non_null_fields(self) -> None:
        """given a Contact with empty notes when to_dict then empty string preserved"""
        contact = Contact(id="test-uuid-jd", name="JD", notes="")
        d = contact.to_dict()
        assert d.get("notes") == ""

    def test_given_stripped_dict_when_from_dict_then_defaults_restored(self) -> None:
        """given a dict with no optional fields when from_dict then defaults applied"""
        d = {"id": "test-uuid-jd", "name": "JD"}
        contact = Contact.from_dict(d)
        assert contact.email is None
        assert contact.phone is None
        assert contact.cadence_days is None
        assert contact.added_at is None
        assert contact.notes == ""

    def test_given_priority_type_when_used_then_accepts_expected_values(self) -> None:
        """given Priority type then deep/casual/network/acquaintance are accepted"""
        p: Priority = "deep"
        assert p == "deep"
        p = "casual"
        assert p == "casual"
        p = "network"
        assert p == "network"
        p = "acquaintance"
        assert p == "acquaintance"


class TestContactState:
    def test_given_minimal_contact_state_when_to_dict_and_from_dict_then_round_trips(self) -> None:
        """given a ContactState with only id/name when to_dict/from_dict returns equal instance"""
        state = ContactState(id="test-uuid-jdoe", name="jdoe")
        d = state.to_dict()
        restored = ContactState.from_dict(d)
        assert restored == state

    def test_given_contact_state_with_dates_when_to_dict_and_from_dict_then_round_trips(self) -> None:
        """given a ContactState with touch_count and removed when to_dict/from_dict round-trips"""
        state = ContactState(
            id="test-uuid-jdoe",
            name="jdoe",
            last_touched=date(2025, 6, 15),
            touch_count=5,
            removed=True,
            removed_at=date(2025, 7, 1),
        )
        d = state.to_dict()
        restored = ContactState.from_dict(d)
        assert restored == state

    def test_given_contact_state_with_dates_when_to_dict_then_serializes_as_iso(self) -> None:
        """given a ContactState with dates when to_dict then values are ISO strings"""
        state = ContactState(
            id="test-uuid-jdoe",
            name="jdoe",
            last_touched=date(2025, 6, 15),
            removed_at=date(2025, 7, 1),
        )
        d = state.to_dict()
        assert d["last_touched"] == "2025-06-15"
        assert d["removed_at"] == "2025-07-01"

    def test_given_minimal_state_when_to_dict_then_omits_null_fields(self) -> None:
        """given a ContactState with no optional fields when to_dict then null fields omitted"""
        state = ContactState(id="test-uuid-jdoe", name="jdoe")
        d = state.to_dict()
        assert "last_touched" not in d
        assert "removed_at" not in d
        # falsy-but-non-null fields preserved
        assert d["touch_count"] == 0
        assert d["removed"] is False

    def test_given_contact_state_default_when_created_then_snooze_count_is_zero(self) -> None:
        """given ContactState() when created then snooze_count defaults to 0"""
        state = ContactState(id="test-uuid-u1", name="user1")
        assert state.snooze_count == 0

    def test_given_contact_state_with_snooze_count_when_to_dict_then_included(self) -> None:
        """given ContactState(snooze_count=3) when to_dict then dict contains snooze_count=3"""
        state = ContactState(id="test-uuid-u1", name="user1", snooze_count=3)
        d = state.to_dict()
        assert d["snooze_count"] == 3

    def test_given_contact_state_dict_with_snooze_count_when_from_dict_then_parsed(self) -> None:
        """given {"snooze_count": 2} when from_dict then ContactState.snooze_count=2"""
        d = {"id": "test-uuid-u1", "name": "user1", "snooze_count": 2}
        state = ContactState.from_dict(d)
        assert state.snooze_count == 2

    def test_given_contact_state_dict_without_snooze_count_when_from_dict_then_defaults_zero(self) -> None:
        """given {} without snooze_count when from_dict then ContactState.snooze_count=0 (backward compat)"""
        d = {"id": "test-uuid-u1", "name": "user1"}
        state = ContactState.from_dict(d)
        assert state.snooze_count == 0

    def test_given_contact_state_default_when_created_then_warm_up_consumed_is_false(self) -> None:
        """given ContactState() when created then warm_up_consumed defaults to False"""
        state = ContactState(id="test-uuid-u1", name="user1")
        assert state.warm_up_consumed is False

    def test_given_contact_state_with_warm_up_consumed_when_to_dict_then_included(self) -> None:
        """given ContactState(warm_up_consumed=True) when to_dict then dict contains warm_up_consumed=True"""
        state = ContactState(id="test-uuid-u1", name="user1", warm_up_consumed=True)
        d = state.to_dict()
        assert d["warm_up_consumed"] is True

    def test_given_contact_state_dict_with_warm_up_consumed_when_from_dict_then_parsed(self) -> None:
        """given {"warm_up_consumed": true} when from_dict then ContactState.warm_up_consumed=True"""
        d = {"id": "test-uuid-u1", "name": "user1", "warm_up_consumed": True}
        state = ContactState.from_dict(d)
        assert state.warm_up_consumed is True

    def test_given_contact_state_dict_without_warm_up_consumed_when_from_dict_then_defaults_false(self) -> None:
        """given {} without warm_up_consumed when from_dict then ContactState.warm_up_consumed=False (backward compat)"""
        d = {"id": "test-uuid-u1", "name": "user1"}
        state = ContactState.from_dict(d)
        assert state.warm_up_consumed is False

    def test_given_contact_state_with_new_fields_when_round_trip_then_preserved(self) -> None:
        """given ContactState(snooze_count=2, warm_up_consumed=True) when to_dict→from_dict then fields preserved"""
        state = ContactState(
            id="test-uuid-u1",
            name="user1",
            snooze_count=2,
            warm_up_consumed=True,
        )
        d = state.to_dict()
        restored = ContactState.from_dict(d)
        assert restored.snooze_count == 2
        assert restored.warm_up_consumed is True
        assert restored == state


class TestLogEntry:
    def test_given_log_entry_when_to_dict_and_from_dict_then_round_trips(self) -> None:
        """given a LogEntry when to_dict then from_dict returns equal instance"""
        entry = LogEntry(
            timestamp=datetime(2025, 6, 1, 12, 30, 0),
            action="add",
            id="test-uuid-jdoe",
            name="jdoe",
            payload={"source": "import"},
        )
        d = entry.to_dict()
        restored = LogEntry.from_dict(d)
        assert restored == entry

    def test_given_log_entry_when_to_dict_then_timestamp_is_iso(self) -> None:
        """given a LogEntry when to_dict then timestamp is ISO string"""
        ts = datetime(2025, 6, 1, 12, 30, 0)
        entry = LogEntry(timestamp=ts, action="touch", id="test-uuid-jdoe", name="jdoe")
        d = entry.to_dict()
        assert d["timestamp"] == ts.isoformat()

    def test_given_log_entry_without_payload_when_from_dict_then_defaults_to_empty(self) -> None:
        """given a LogEntry with no payload then from_dict defaults to empty dict"""
        entry = LogEntry(
            timestamp=datetime(2025, 6, 1, 12, 30, 0),
            action="remove",
            id="test-uuid-jdoe",
            name="jdoe",
        )
        assert entry.payload == {}

        d = entry.to_dict()
        restored = LogEntry.from_dict(d)
        assert restored.payload == {}
