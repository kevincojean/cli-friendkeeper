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
