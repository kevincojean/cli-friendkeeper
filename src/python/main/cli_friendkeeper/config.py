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

DEFAULT_PRIORITY: str = "casual"

VALID_PRIORITIES = frozenset(DEFAULT_CADENCE.keys())


@dataclass
class Config:
    cadence: dict[str, int]
    default_priority: str = DEFAULT_PRIORITY


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
    return Config(cadence=raw["cadence"], default_priority=default_priority)


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


def save_config(cfg: Config, path: Path | None = None) -> None:
    if path is None:
        path = config_file()

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"cadence": cfg.cadence}
        if cfg.default_priority != DEFAULT_PRIORITY:
            payload["default_priority"] = cfg.default_priority
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
