from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cli_friendkeeper.errors import ConfigError, InvalidPriorityError, StorageError
from cli_friendkeeper.paths import config_file

DEFAULT_CADENCE: dict[str, int] = {
    "deep": 15,
    "casual": 45,
    "network": 180,
    "acquaintance": 0,
}

DEFAULT_SNOOZE: dict[str, int] = {
    "deep": 7,
    "casual": 15,
    "network": 30,
    "acquaintance": 90,
}

DEFAULT_PRIORITY: str = "casual"

DEFAULT_SUBCOMMAND: str = "due"

VALID_PRIORITIES = frozenset(DEFAULT_CADENCE.keys())

DEFAULT_PRIORITY_ORDER: list[str] = ["acquaintance", "network", "casual", "deep"]

VALID_SUBCOMMANDS = frozenset({
    "add",
    "catch-up",
    "list",
    "due",
    "touch",
    "remove",
    "rebuild-state",
    "config-show",
    "config-set",
})


@dataclass
class Config:
    cadence: dict[str, int]
    snooze: dict[str, int] | None = None
    default_priority: str = DEFAULT_PRIORITY
    default_subcommand: str = DEFAULT_SUBCOMMAND
    priority_order: list[str] | None = None
    list_hide_acquaintances: bool | None = None
    list_sort_priority: str | None = None
    list_sort_due_date: str | None = None

    def __post_init__(self) -> None:
        if self.snooze is None:
            self.snooze = dict(DEFAULT_SNOOZE)
        if self.priority_order is None:
            self.priority_order = list(DEFAULT_PRIORITY_ORDER)
        if self.list_hide_acquaintances is None:
            self.list_hide_acquaintances = True
        if self.list_sort_priority is None:
            self.list_sort_priority = "asc"
        if self.list_sort_due_date is None:
            self.list_sort_due_date = "desc"


def load_config(path: Path | None = None) -> Config:
    if path is None:
        path = config_file()

    if not path.exists():
        return Config(cadence=dict(DEFAULT_CADENCE))

    try:
        raw: Any = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ConfigError(f"invalid JSON in {path}: {e}") from e

    _validate(raw, path)
    default_priority = raw.get("default_priority", DEFAULT_PRIORITY)
    if default_priority not in VALID_PRIORITIES:
        raise ConfigError(f"{path}: invalid default_priority {default_priority!r}")
    default_subcommand = raw.get("default_subcommand", DEFAULT_SUBCOMMAND)
    if default_subcommand not in VALID_SUBCOMMANDS:
        raise ConfigError(
            f"{path}: invalid default_subcommand {default_subcommand!r}; "
            f"valid: {', '.join(sorted(VALID_SUBCOMMANDS))}"
        )
    return Config(
        cadence=raw["cadence"],
        snooze=raw.get("snooze"),
        default_priority=default_priority,
        default_subcommand=default_subcommand,
        priority_order=raw.get("priority_order"),
        list_hide_acquaintances=raw.get("list_hide_acquaintances"),
        list_sort_priority=raw.get("list_sort_priority"),
        list_sort_due_date=raw.get("list_sort_due_date"),
    )


def _validate(raw: Any, path: Path) -> None:
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: expected a JSON object, got {type(raw).__name__}")

    cadence = raw.get("cadence")
    if not isinstance(cadence, dict):
        raise ConfigError(
            f"{path}: 'cadence' must be a JSON object, got {type(cadence).__name__}"
        )

    for key, val in cadence.items():
        if not isinstance(key, str) or not isinstance(val, int):
            raise ConfigError(
                f"{path}: 'cadence' values must be integers, got {type(val).__name__} for key {key!r}"
            )

    snooze = raw.get("snooze")
    if snooze is not None:
        if not isinstance(snooze, dict):
            raise ConfigError(
                f"{path}: 'snooze' must be a JSON object, got {type(snooze).__name__}"
            )
        for key, val in snooze.items():
            if not isinstance(key, str) or not isinstance(val, int):
                raise ConfigError(
                    f"{path}: 'snooze' values must be integers, got {type(val).__name__} for key {key!r}"
                )

    priority_order = raw.get("priority_order")
    if priority_order is not None:
        if not isinstance(priority_order, list) or not all(
            isinstance(p, str) for p in priority_order
        ):
            raise ConfigError(
                f"{path}: 'priority_order' must be a list of strings, "
                f"got {type(priority_order).__name__}"
            )
        for p in priority_order:
            if p not in VALID_PRIORITIES:
                raise ConfigError(
                    f"{path}: 'priority_order' contains invalid priority {p!r}"
                )

    list_hide_acquaintances = raw.get("list_hide_acquaintances")
    if list_hide_acquaintances is not None and not isinstance(list_hide_acquaintances, bool):
        raise ConfigError(
            f"{path}: 'list_hide_acquaintances' must be a boolean, "
            f"got {type(list_hide_acquaintances).__name__}"
        )

    _validate_sort_key("list_sort_priority", raw, path)
    _validate_sort_key("list_sort_due_date", raw, path)


def _validate_sort_key(key: str, raw: dict[str, Any], path: Path) -> None:
    val = raw.get(key)
    if val is not None and val not in ("asc", "desc"):
        raise ConfigError(
            f"{path}: {key!r} must be 'asc' or 'desc', got {val!r}"
        )


def save_config(cfg: Config, path: Path | None = None) -> None:
    if path is None:
        path = config_file()

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"cadence": cfg.cadence}
        if cfg.snooze is not None and cfg.snooze != DEFAULT_SNOOZE:
            payload["snooze"] = cfg.snooze
        if cfg.default_priority != DEFAULT_PRIORITY:
            payload["default_priority"] = cfg.default_priority
        if cfg.default_subcommand != DEFAULT_SUBCOMMAND:
            payload["default_subcommand"] = cfg.default_subcommand
        if cfg.priority_order is not None and cfg.priority_order != DEFAULT_PRIORITY_ORDER:
            payload["priority_order"] = cfg.priority_order
        if cfg.list_hide_acquaintances is not None and cfg.list_hide_acquaintances is not True:
            payload["list_hide_acquaintances"] = cfg.list_hide_acquaintances
        if cfg.list_sort_priority is not None and cfg.list_sort_priority != "asc":
            payload["list_sort_priority"] = cfg.list_sort_priority
        if cfg.list_sort_due_date is not None and cfg.list_sort_due_date != "desc":
            payload["list_sort_due_date"] = cfg.list_sort_due_date
        path.write_text(json.dumps(payload, indent=2) + "\n")
    except OSError as e:
        raise StorageError(f"could not write config to {path}: {e}") from e


def effective_cadence(cfg: Config, priority: str, override: int | None) -> int:
    if override is not None:
        return override

    if priority in cfg.cadence:
        return cfg.cadence[priority]

    if priority in DEFAULT_CADENCE:
        return DEFAULT_CADENCE[priority]

    raise InvalidPriorityError(f"unknown priority: {priority!r}")


def effective_snooze(cfg: Config, priority: str) -> int:
    if cfg.snooze is not None and priority in cfg.snooze:
        return cfg.snooze[priority]
    if priority in DEFAULT_SNOOZE:
        return DEFAULT_SNOOZE[priority]
    raise InvalidPriorityError(f"unknown priority: {priority!r}")
