from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Literal
from uuid import NAMESPACE_DNS, uuid5

from email_validator import EmailNotValidError, validate_email

from cli_friendkeeper.errors import InvalidEmailError

Priority = Literal["deep", "casual", "network"]


@dataclass
class Contact:
    id: str
    name: str
    email: str | None = None
    phone: str | None = None
    priority: Priority = "casual"
    cadence_days: int | None = None
    notes: str = ""
    added_at: date | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.added_at:
            d["added_at"] = self.added_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Contact:
        kwargs = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        if "id" not in kwargs:
            kwargs["id"] = str(uuid5(NAMESPACE_DNS, f"cli-friendkeeper:{kwargs.get('name', 'unknown')}"))
        if "added_at" in kwargs and isinstance(kwargs["added_at"], str):
            kwargs["added_at"] = date.fromisoformat(kwargs["added_at"])
        return cls(**kwargs)

    def validate(self) -> None:
        if self.email is not None:
            try:
                validate_email(self.email, check_deliverability=False)
            except EmailNotValidError as e:
                raise InvalidEmailError(str(e))


@dataclass
class ContactState:
    id: str
    name: str
    last_touched: date | None = None
    touch_count: int = 0
    removed: bool = False
    removed_at: date | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.last_touched:
            d["last_touched"] = self.last_touched.isoformat()
        if self.removed_at:
            d["removed_at"] = self.removed_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContactState:
        kwargs = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        if "id" not in kwargs:
            kwargs["id"] = str(uuid5(NAMESPACE_DNS, f"cli-friendkeeper:{kwargs.get('name', 'unknown')}"))
        if "last_touched" in kwargs and isinstance(kwargs["last_touched"], str):
            kwargs["last_touched"] = date.fromisoformat(kwargs["last_touched"])
        if "removed_at" in kwargs and isinstance(kwargs["removed_at"], str):
            kwargs["removed_at"] = date.fromisoformat(kwargs["removed_at"])
        return cls(**kwargs)


@dataclass
class LogEntry:
    timestamp: datetime
    action: Literal["add", "touch", "remove", "rebuild-state"]
    id: str
    name: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LogEntry:
        kwargs = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        if "id" not in kwargs:
            kwargs["id"] = str(uuid5(NAMESPACE_DNS, f"cli-friendkeeper:{kwargs.get('name', 'unknown')}"))
        if "timestamp" in kwargs and isinstance(kwargs["timestamp"], str):
            kwargs["timestamp"] = datetime.fromisoformat(kwargs["timestamp"])
        if "payload" not in kwargs:
            kwargs["payload"] = {}
        return cls(**kwargs)
