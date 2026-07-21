"""Tests for the config-set subcommand."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.monkeypatch import MonkeyPatch

CONFIG_DIR_REL = "com.kevincojean.cli-friendkeeper"
CONFIG_FILE_REL = f"{CONFIG_DIR_REL}/config.json"


class TestRunConfigSet:
    """Tests for run_config_set.run()."""

    def test_given_valid_key_value_when_running_then_config_is_updated(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given valid cadence.deep=7 when run then config is updated and persisted."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        from cli_friendkeeper.ccli.ccli import Context
        from cli_friendkeeper.ccli.task.run_config_set import run

        ctx = Context(tmp_path / "data")
        rc = run(["cadence.deep", "7"], ctx)

        assert rc == 0
        captured = capsys.readouterr()
        assert "Set cadence.deep = 7" in captured.out

        config_path = config_dir / CONFIG_FILE_REL
        assert config_path.exists()
        raw = json.loads(config_path.read_text())
        assert raw["cadence"]["deep"] == 7

    def test_given_invalid_key_when_running_then_returns_error(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given unknown config key when run then returns rc=1 with error message."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        from cli_friendkeeper.ccli.ccli import Context
        from cli_friendkeeper.ccli.task.run_config_set import run

        ctx = Context(tmp_path / "data")
        rc = run(["unknown.key", "7"], ctx)

        assert rc == 1
        captured = capsys.readouterr()
        assert "Error: Unknown config key: unknown.key" in captured.err

    def test_given_non_int_value_when_running_then_returns_error(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given non-integer value when run then returns rc=1 with error message."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        from cli_friendkeeper.ccli.ccli import Context
        from cli_friendkeeper.ccli.task.run_config_set import run

        ctx = Context(tmp_path / "data")
        rc = run(["cadence.deep", "not-a-number"], ctx)

        assert rc == 1
        captured = capsys.readouterr()
        assert "Error: not-a-number is not a valid integer" in captured.err

    def test_given_missing_args_when_running_then_returns_error(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given missing args when run then returns rc=1 with usage message."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        from cli_friendkeeper.ccli.ccli import Context
        from cli_friendkeeper.ccli.task.run_config_set import run

        ctx = Context(tmp_path / "data")
        rc = run(["cadence.deep"], ctx)

        assert rc == 1
        captured = capsys.readouterr()
        assert "Error: usage: friend config-set <key> <value>" in captured.err

    def test_given_no_config_file_when_running_then_creates_it(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given no config file when run then creates it with the new value."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        from cli_friendkeeper.ccli.ccli import Context
        from cli_friendkeeper.ccli.task.run_config_set import run

        ctx = Context(tmp_path / "data")

        config_path = config_dir / CONFIG_FILE_REL
        assert not config_path.exists()

        rc = run(["cadence.casual", "30"], ctx)

        assert rc == 0
        assert config_path.exists()
        raw = json.loads(config_path.read_text())
        assert raw["cadence"]["casual"] == 30

    def test_given_valid_default_priority_when_running_then_updates_config(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given valid default_priority when run then config is updated."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        from cli_friendkeeper.ccli.ccli import Context
        from cli_friendkeeper.ccli.task.run_config_set import run

        ctx = Context(tmp_path / "data")
        rc = run(["default_priority", "acquaintance"], ctx)

        assert rc == 0
        captured = capsys.readouterr()
        assert "Set default_priority = acquaintance" in captured.out

        config_path = config_dir / CONFIG_FILE_REL
        assert config_path.exists()
        raw = json.loads(config_path.read_text())
        assert raw["default_priority"] == "acquaintance"

    def test_given_invalid_default_priority_when_running_then_returns_error(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given invalid default_priority when run then returns rc=1."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        from cli_friendkeeper.ccli.ccli import Context
        from cli_friendkeeper.ccli.task.run_config_set import run

        ctx = Context(tmp_path / "data")
        rc = run(["default_priority", "invalid"], ctx)

        assert rc == 1
        captured = capsys.readouterr()
        assert "not a valid priority" in captured.err

    def test_given_valid_default_subcommand_when_running_then_updates_config(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given valid default_subcommand when run then config is updated."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        from cli_friendkeeper.ccli.ccli import Context
        from cli_friendkeeper.ccli.task.run_config_set import run

        ctx = Context(tmp_path / "data")
        rc = run(["default_subcommand", "list"], ctx)

        assert rc == 0
        captured = capsys.readouterr()
        assert "Set default_subcommand = list" in captured.out

        config_path = config_dir / CONFIG_FILE_REL
        assert config_path.exists()
        raw = json.loads(config_path.read_text())
        assert raw["default_subcommand"] == "list"

    def test_given_invalid_default_subcommand_when_running_then_returns_error(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given invalid default_subcommand when run then returns rc=1."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        from cli_friendkeeper.ccli.ccli import Context
        from cli_friendkeeper.ccli.task.run_config_set import run

        ctx = Context(tmp_path / "data")
        rc = run(["default_subcommand", "invalid"], ctx)

        assert rc == 1
        captured = capsys.readouterr()
        assert "not a valid subcommand" in captured.err
