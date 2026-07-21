"""Tests for the config-show subcommand."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.monkeypatch import MonkeyPatch

from cli_friendkeeper.config import DEFAULT_CADENCE


class TestRunConfigShow:
    """Tests for run_config_show.run()."""

    def test_given_no_config_file_when_config_show_then_prints_defaults(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given no config file when run then prints default cadence values."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        from cli_friendkeeper.ccli.ccli import Context
        from cli_friendkeeper.ccli.task.run_config_show import run

        ctx = Context(tmp_path / "data")
        rc = run([], ctx)

        assert rc == 0
        captured = capsys.readouterr()
        out = captured.out

        assert "Config file:" in out
        assert "default_subcommand = due" in out
        for priority in ("deep", "casual", "network", "acquaintance"):
            assert priority in out
            assert str(DEFAULT_CADENCE[priority]) in out

    def test_given_custom_config_file_when_config_show_then_prints_custom_values(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given custom config file when run then prints custom values."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        custom = {"deep": 3, "casual": 10, "network": 60}
        config_path = (
            config_dir / "com.kevincojean.cli-friendkeeper" / "config.json"
        )
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"cadence": custom}) + "\n")

        from cli_friendkeeper.ccli.ccli import Context
        from cli_friendkeeper.ccli.task.run_config_show import run

        ctx = Context(tmp_path / "data")
        rc = run([], ctx)

        assert rc == 0
        captured = capsys.readouterr()
        out = captured.out

        assert "Config file:" in out
        for priority, days in custom.items():
            assert priority in out
            assert str(days) in out
