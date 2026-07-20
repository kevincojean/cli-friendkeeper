"""Tests for the CLI facade (ccli.py)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture

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
        """main([]) should return 0."""
        rc = main([])
        assert rc == 0

    def test_given_help_flag_when_calling_main_then_returns_zero(
        self,
    ) -> None:
        """main(["--help"]) should return 0."""
        rc = main(["--help"])
        assert rc == 0

    def test_given_no_args_when_calling_main_then_help_contains_all_subcommands(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """main([]) should print help text listing all subcommands."""
        main([])
        captured = capsys.readouterr()
        output = captured.out + captured.err
        for sub in SUBCOMMANDS:
            assert sub in output, f"help should mention {sub!r}"

    def test_given_help_flag_when_calling_main_then_help_contains_all_subcommands(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """main(["--help"]) should print help text listing all subcommands."""
        main(["--help"])
        captured = capsys.readouterr()
        output = captured.out + captured.err
        for sub in SUBCOMMANDS:
            assert sub in output, f"help should mention {sub!r}"


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
