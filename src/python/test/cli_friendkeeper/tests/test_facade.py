"""Tests for the CLI facade (ccli.py)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.monkeypatch import MonkeyPatch

from cli_friendkeeper.ccli.ccli import main

SUBCOMMANDS = [
    "add",
    "list",
    "due",
    "touch",
    "remove",
    "rebuild-state",
    "config-show",
    "config-set",
]


class TestMainHelp:
    """Tests for help output."""

    def test_given_no_args_when_calling_main_then_returns_zero(
        self,
    ) -> None:
        """main([]) should return 0 (dispatches to default subcommand due)."""
        rc = main([])
        assert rc == 0

    def test_given_help_flag_when_calling_main_then_returns_zero(
        self,
    ) -> None:
        """main(["--help"]) should return 0."""
        rc = main(["--help"])
        assert rc == 0

    def test_given_help_flag_when_calling_main_then_help_contains_all_subcommands(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """main(["--help"]) should print help text listing all subcommands."""
        main(["--help"])
        captured = capsys.readouterr()
        output = captured.out + captured.err
        for sub in SUBCOMMANDS:
            assert sub in output, f"help should mention {sub!r}"

    def test_given_no_args_when_calling_main_then_dispatches_to_due(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """main([]) should dispatch to due (contains "Nothing due." or a due table)."""
        main([])
        captured = capsys.readouterr()
        output = captured.out + captured.err
        # due output contains either "Nothing due." or table header "Days Since"
        assert "Nothing due." in output or "Days Since" in output


class TestMainDefaultSubcommand:
    """Tests for default subcommand dispatch."""

    def test_given_config_with_list_default_when_main_no_args_then_dispatches_to_list(
        self, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str], tmp_path: Path
    ) -> None:
        """given config default_subcommand=list when main([]) then runs list."""
        config_dir = tmp_path / "config"
        cache_dir = tmp_path / "cache"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

        config_path = (
            config_dir / "com.kevincojean.cli-friendkeeper" / "config.json"
        )
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps({
                "cadence": {"deep": 15, "casual": 45, "network": 180, "acquaintance": 0},
                "default_subcommand": "list",
            })
            + "\n",
        )

        rc = main([])
        assert rc == 0
        captured = capsys.readouterr()
        assert "No contacts yet." in captured.out


class TestMainUnknown:
    """Tests for unknown subcommand handling."""

    def test_given_unknown_subcommand_when_calling_main_then_returns_one(
        self,
    ) -> None:
        """main(["unknown"]) should return 1."""
        rc = main(["unknown"])
        assert rc == 1

    def test_given_unknown_subcommand_when_calling_main_then_prints_error(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """main(["unknown"]) should print error message to stderr."""
        main(["unknown"])
        captured = capsys.readouterr()
        assert "unknown" in captured.err.lower()
