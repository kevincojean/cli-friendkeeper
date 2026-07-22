from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cli_friendkeeper.errors import ConfigError, InvalidPriorityError, StorageError
from cli_friendkeeper.paths import config_file

if TYPE_CHECKING:
    from cli_friendkeeper.models import ContactState

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

VALID_LIST_COLUMNS = frozenset({
    "id", "name", "priority", "last_touched", "due_date",
    "days_since", "cadence", "removed", "notes", "email", "phone",
})

DEFAULT_LIST_COLUMNS: list[str] = ["id", "name", "priority", "last_touched", "due_date"]

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
    list_columns: list[str] | None = None
    warm_up: dict[str, int] | None = None
    warm_up_max_snoozes: dict[str, int] | None = None
    acquaintance_auto_upgrade: bool = True

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
        if self.list_columns is None:
            self.list_columns = list(DEFAULT_LIST_COLUMNS)
        if self.warm_up is None:
            self.warm_up = {"acquaintance": 45, "casual": 15}
        if self.warm_up_max_snoozes is None:
            self.warm_up_max_snoozes = {"acquaintance": 2, "casual": 3}


def _flat_or_raw(raw: dict[str, Any], flat_key: str, legacy_key: str) -> Any:
    """Read *flat_key* (dot notation) falling back to *legacy_key* (underscore)."""
    if flat_key in raw:
        return raw[flat_key]
    if legacy_key in raw:
        return raw[legacy_key]
    return None


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

    # Extract cadence: nested (old) or cadence.<prio> (new)
    cadence = dict(raw.get("cadence", {})) if isinstance(raw.get("cadence"), dict) else {}
    for key, val in raw.items():
        if key.startswith("cadence."):
            prio = key[len("cadence."):]
            if prio in VALID_PRIORITIES:
                cadence[prio] = val

    # Extract snooze: nested (old) or snooze.<prio> (new)
    snooze = dict(raw.get("snooze", {})) if isinstance(raw.get("snooze"), dict) else {}
    for key, val in raw.items():
        if key.startswith("snooze."):
            prio = key[len("snooze."):]
            if prio in VALID_PRIORITIES:
                snooze[prio] = val

    warm_up = {}
    if isinstance(raw.get("warm_up"), dict):
        warm_up = dict(raw["warm_up"])
    for key, val in raw.items():
        if key.startswith("warm_up.") and not key.startswith("warm_up.max_snoozes."):
            prio = key[len("warm_up."):]
            if prio in VALID_PRIORITIES:
                warm_up[prio] = val
    if not warm_up:
        warm_up = None

    warm_up_max_snoozes = {}
    if isinstance(raw.get("warm_up_max_snoozes"), dict):
        warm_up_max_snoozes = dict(raw["warm_up_max_snoozes"])
    for key, val in raw.items():
        if key.startswith("warm_up.max_snoozes."):
            prio = key[len("warm_up.max_snoozes."):]
            if prio in VALID_PRIORITIES:
                warm_up_max_snoozes[prio] = val
    if not warm_up_max_snoozes:
        warm_up_max_snoozes = None

    acquaintance_auto_upgrade = raw.get("acquaintance.auto_upgrade", raw.get("acquaintance_auto_upgrade", True))

    list_hide_acquaintances = _flat_or_raw(raw, "list.hide_acquaintances", "list_hide_acquaintances")
    list_sort_priority = _flat_or_raw(raw, "list.sort_priority", "list_sort_priority")
    list_sort_due_date = _flat_or_raw(raw, "list.sort_due_date", "list_sort_due_date")
    list_columns = _flat_or_raw(raw, "list.columns", "list_columns")
    priority_order = _flat_or_raw(raw, "list.priority_order", "priority_order")

    return Config(
        cadence=cadence or dict(DEFAULT_CADENCE),
        snooze=snooze or None,
        default_priority=default_priority,
        default_subcommand=default_subcommand,
        priority_order=priority_order,
        list_hide_acquaintances=list_hide_acquaintances,
        list_sort_priority=list_sort_priority,
        list_sort_due_date=list_sort_due_date,
        list_columns=list_columns,
        warm_up=warm_up,
        warm_up_max_snoozes=warm_up_max_snoozes,
        acquaintance_auto_upgrade=acquaintance_auto_upgrade,
    )


def _validate(raw: Any, path: Path) -> None:
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: expected a JSON object, got {type(raw).__name__}")

    # cadence: nested (old) or cadence.<priority> flat keys (new)
    cadence_ok = isinstance(raw.get("cadence"), dict) or any(
        k.startswith("cadence.") and k[len("cadence."):] in VALID_PRIORITIES
        for k in raw
    )
    if not cadence_ok:
        raise ConfigError(
            f"{path}: missing 'cadence' object or 'cadence.<priority>' flat keys"
        )

    # Validate nested cadence (old format)
    cadence = raw.get("cadence")
    if isinstance(cadence, dict):
        for key, val in cadence.items():
            if not isinstance(key, str) or not isinstance(val, int):
                raise ConfigError(
                    f"{path}: 'cadence' values must be integers, "
                    f"got {type(val).__name__} for key {key!r}"
                )

    # Validate flat cadence.<priority> keys
    for key, val in raw.items():
        if key.startswith("cadence."):
            prio = key[len("cadence."):]
            if prio not in VALID_PRIORITIES:
                raise ConfigError(
                    f"{path}: unknown priority {prio!r} in {key!r}"
                )
            if not isinstance(val, int):
                raise ConfigError(
                    f"{path}: {key!r} must be an integer, got {type(val).__name__}"
                )

    # snooze: nested (old) or snooze.<priority> flat keys (new)
    snooze = raw.get("snooze")
    if isinstance(snooze, dict):
        for key, val in snooze.items():
            if not isinstance(key, str) or not isinstance(val, int):
                raise ConfigError(
                    f"{path}: 'snooze' values must be integers, "
                    f"got {type(val).__name__} for key {key!r}"
                )

    for key, val in raw.items():
        if key.startswith("snooze."):
            prio = key[len("snooze."):]
            if prio not in VALID_PRIORITIES:
                raise ConfigError(
                    f"{path}: unknown priority {prio!r} in {key!r}"
                )
            if not isinstance(val, int):
                raise ConfigError(
                    f"{path}: {key!r} must be an integer, got {type(val).__name__}"
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

    for key, val in raw.items():
        if key.startswith("warm_up."):
            if key.startswith("warm_up.max_snoozes."):
                prio = key[len("warm_up.max_snoozes."):]
                if prio not in VALID_PRIORITIES:
                    raise ConfigError(
                        f"{path}: unknown priority {prio!r} in warm_up.max_snoozes"
                    )
                if not isinstance(val, int) or val < 0:
                    raise ConfigError(
                        f"{path}: warm_up.max_snoozes values must be non-negative integers, "
                        f"got {val!r}"
                    )
            else:
                prio = key[len("warm_up."):]
                if prio not in VALID_PRIORITIES:
                    raise ConfigError(
                        f"{path}: unknown priority {prio!r} in {key!r}"
                    )
                if not isinstance(val, int):
                    raise ConfigError(
                        f"{path}: warm_up values must be integers, "
                        f"got {type(val).__name__} for {key!r}"
                    )

    _validate_flat_bool("acquaintance.auto_upgrade", raw, path)
    _validate_flat_bool("list.hide_acquaintances", raw, path)
    _validate_flat_bool("list_hide_acquaintances", raw, path)

    _validate_flat_sort("list.sort_priority", raw, path)
    _validate_flat_sort("list_sort_priority", raw, path)
    _validate_flat_sort("list.sort_due_date", raw, path)
    _validate_flat_sort("list_sort_due_date", raw, path)

    for flat_key in ("list.columns", "list_columns"):
        _validate_flat_list(flat_key, raw, path)


def _validate_flat_bool(key: str, raw: dict[str, Any], path: Path) -> None:
    val = raw.get(key)
    if val is not None and not isinstance(val, bool):
        raise ConfigError(
            f"{path}: {key!r} must be a boolean, got {type(val).__name__}"
        )


def _validate_flat_sort(key: str, raw: dict[str, Any], path: Path) -> None:
    val = raw.get(key)
    if val is not None and val not in ("asc", "desc"):
        raise ConfigError(
            f"{path}: {key!r} must be 'asc' or 'desc', got {val!r}"
        )


def _validate_flat_list(key: str, raw: dict[str, Any], path: Path) -> None:
    val = raw.get(key)
    if val is not None:
        if not isinstance(val, list) or not all(isinstance(c, str) for c in val):
            raise ConfigError(
                f"{path}: {key!r} must be a list of strings, "
                f"got {type(val).__name__}"
            )
        for c in val:
            if c not in VALID_LIST_COLUMNS:
                raise ConfigError(
                    f"{path}: {key!r} contains unknown column {c!r}; "
                    f"valid: {', '.join(sorted(VALID_LIST_COLUMNS))}"
                )


def save_config(cfg: Config, path: Path | None = None) -> None:
    if path is None:
        path = config_file()

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {}
        # Write cadence as flat cadence.<priority> keys
        for prio, days in cfg.cadence.items():
            if days != DEFAULT_CADENCE.get(prio):
                payload[f"cadence.{prio}"] = days
        if not payload:
            # All defaults — signal one key so validation passes
            payload["cadence.deep"] = DEFAULT_CADENCE["deep"]
        # Write snooze as flat snooze.<priority> keys
        if cfg.snooze is not None:
            for prio, days in cfg.snooze.items():
                if days != DEFAULT_SNOOZE.get(prio):
                    payload[f"snooze.{prio}"] = days
        if cfg.warm_up is not None:
            for prio, days in cfg.warm_up.items():
                DEFAULT_WARM_UP = {"acquaintance": 45, "casual": 15}
                if days != DEFAULT_WARM_UP.get(prio):
                    payload[f"warm_up.{prio}"] = days
        if cfg.warm_up_max_snoozes is not None:
            for prio, n in cfg.warm_up_max_snoozes.items():
                DEFAULT_WARM_UP_MAX = {"acquaintance": 2, "casual": 3}
                if n != DEFAULT_WARM_UP_MAX.get(prio):
                    payload[f"warm_up.max_snoozes.{prio}"] = n
        if cfg.acquaintance_auto_upgrade is not True:
            payload["acquaintance.auto_upgrade"] = cfg.acquaintance_auto_upgrade
        if cfg.default_priority != DEFAULT_PRIORITY:
            payload["default_priority"] = cfg.default_priority
        if cfg.default_subcommand != DEFAULT_SUBCOMMAND:
            payload["default_subcommand"] = cfg.default_subcommand
        if cfg.priority_order is not None and cfg.priority_order != DEFAULT_PRIORITY_ORDER:
            payload["list.priority_order"] = cfg.priority_order
        if cfg.list_hide_acquaintances is not None and cfg.list_hide_acquaintances is not True:
            payload["list.hide_acquaintances"] = cfg.list_hide_acquaintances
        if cfg.list_sort_priority is not None and cfg.list_sort_priority != "asc":
            payload["list.sort_priority"] = cfg.list_sort_priority
        if cfg.list_sort_due_date is not None and cfg.list_sort_due_date != "desc":
            payload["list.sort_due_date"] = cfg.list_sort_due_date
        if cfg.list_columns is not None and cfg.list_columns != DEFAULT_LIST_COLUMNS:
            payload["list.columns"] = cfg.list_columns
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


def effective_cadence_with_warm_up(cfg: Config, priority: str, state: ContactState) -> int:
    wc = (cfg.warm_up or {}).get(priority)
    if state.warm_up_consumed is False and wc is not None:
        return wc
    return effective_cadence(cfg, priority, None)
