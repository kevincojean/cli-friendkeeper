"""config-set subcommand: set a configuration key and persist."""

from __future__ import annotations

from typing import Any

import typer

from cli_friendkeeper.ccli.ccli import Context
from cli_friendkeeper.config import (
    VALID_LIST_COLUMNS,
    VALID_PRIORITIES,
    VALID_SUBCOMMANDS,
    load_config,
    save_config,
)

# Schema: maps flat config key → (domain, raw sub-key, validator, setter)
# Dot is the domain separator: cadence.deep, list.hide_acquaintances.
# Underscore separates words within a sub-key.

_CONFIG_KEYS: dict[str, tuple[str, str, Any, Any]] = {}


def _validate_bool(val: str) -> bool:
    if val.lower() in ("true", "1", "yes"):
        return True
    if val.lower() in ("false", "0", "no"):
        return False
    raise ValueError(f"expected boolean, got {val!r}")


for _p in VALID_PRIORITIES:
    _CONFIG_KEYS[f"cadence.{_p}"] = (
        "cadence", _p, int,
        lambda cfg, k, v, p=_p: setattr(cfg, "cadence", {**cfg.cadence, p: v}),
    )
    _CONFIG_KEYS[f"snooze.{_p}"] = (
        "snooze", _p, int,
        lambda cfg, k, v, p=_p: (
            setattr(cfg, "snooze", {**(cfg.snooze or {}), p: v})
        ),
    )

# Global keys (no domain)
_CONFIG_KEYS["default_priority"] = ("", "", str, lambda cfg, k, v: setattr(cfg, "default_priority", v))
_CONFIG_KEYS["default_subcommand"] = ("", "", str, lambda cfg, k, v: setattr(cfg, "default_subcommand", v))

# list.* keys
_CONFIG_KEYS["list.hide_acquaintances"] = ("", "", _validate_bool, lambda cfg, k, v: setattr(cfg, "list_hide_acquaintances", v))
_CONFIG_KEYS["list.sort_priority"] = ("", "", str, lambda cfg, k, v: setattr(cfg, "list_sort_priority", v))
_CONFIG_KEYS["list.sort_due_date"] = ("", "", str, lambda cfg, k, v: setattr(cfg, "list_sort_due_date", v))
_CONFIG_KEYS["list.columns"] = ("", "", str, lambda cfg, k, v: setattr(cfg, "list_columns", v.split(",") if "," in v else [v]))
_CONFIG_KEYS["list.priority_order"] = ("", "", str, lambda cfg, k, v: setattr(cfg, "priority_order", v.split(",") if "," in v else [v]))


def _print_usage() -> None:
    """Print usage help to stderr."""
    typer.echo(
        "Usage: friend config-set <key> <value>",
        err=True,
    )


def run(args: list[str], ctx: Context) -> int:
    """Set a config key and persist to disk.

    Dot is the domain separator: ``cadence.deep``, ``list.hide_acquaintances``.

    Keys:
      - ``cadence.<priority>`` — cadence days for a priority
      - ``snooze.<priority>`` — snooze days for a priority
      - ``default_priority`` — default priority for new contacts
      - ``default_subcommand`` — default subcommand
      - ``list.hide_acquaintances`` — true/false
      - ``list.sort_priority`` — asc/desc
      - ``list.sort_due_date`` — asc/desc
      - ``list.priority_order`` — comma-separated priority order
      - ``list.columns`` — comma-separated column names
    """
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0

    if args and args[0].startswith("--") and args[0] not in ("--help", "-h"):
        typer.echo(f"Unknown flag: {args[0]}", err=True)
        return 1

    if len(args) != 2:
        typer.echo("Error: usage: friend config-set <key> <value>", err=True)
        return 1

    key, value = args

    entry = _CONFIG_KEYS.get(key)
    if entry is None:
        typer.echo(
            f"Error: Unknown config key: {key}\n"
            f"Try: cadence_deep, default_priority, list_hide_acquaintances, list_columns, …",
            err=True,
        )
        return 1

    _, sub, validator, setter = entry

    if sub and sub not in VALID_PRIORITIES:
        typer.echo(f"Error: unknown priority {sub!r}", err=True)
        return 1

    # Validate + coerce the value
    try:
        if validator is int:
            v = int(value)
        elif validator is str:
            v = value
        elif validator is _validate_bool:
            v = validator(value)
        else:
            v = validator(value)
    except (ValueError, TypeError) as e:
        typer.echo(f"Error: {value!r} is not valid for {key}: {e}", err=True)
        return 1

    # Additional semantic validation
    if key in ("default_priority",) or key.startswith("cadence_"):
        if sub and v is int and v < 0:
            typer.echo("Error: cadence must be >= 0", err=True)
            return 1
    if key == "default_priority" and v not in VALID_PRIORITIES:
        typer.echo(
            f"Error: {v!r} is not a valid priority; "
            f"choose from {', '.join(sorted(VALID_PRIORITIES))}",
            err=True,
        )
        return 1
    if key == "default_subcommand" and v not in VALID_SUBCOMMANDS:
        typer.echo(
            f"Error: {v!r} is not a valid subcommand; "
            f"choose from {', '.join(sorted(VALID_SUBCOMMANDS))}",
            err=True,
        )
        return 1
    if "list_sort_" in key and v not in ("asc", "desc"):
        typer.echo("Error: must be 'asc' or 'desc'", err=True)
        return 1
    if key == "list_columns":
        for c in v:
            if c not in VALID_LIST_COLUMNS:
                typer.echo(
                    f"Error: unknown column {c!r}; valid: "
                    f"{', '.join(sorted(VALID_LIST_COLUMNS))}",
                    err=True,
                )
                return 1

    cfg = load_config()
    setter(cfg, key, v)
    save_config(cfg)
    typer.echo(f"Set {key} = {v}")
    return 0
