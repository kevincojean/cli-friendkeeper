"""End-to-end tests for the cli-friendkeeper CLI.

Each test runs the real CLI via ``subprocess.run`` with isolated
``XDG_CACHE_HOME`` and ``XDG_CONFIG_HOME`` directories (via ``tmp_path``).
No mocking — every test is a true end-to-end shell invocation.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


def _cli(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    """Run the friendkeeper CLI via ``uv run python -m …``."""
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "cli_friendkeeper",
        *args,
    ]
    merged = {**os.environ, **env}
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=merged,
        cwd=PROJECT_ROOT,
    )


def _env(tmp_path: Path) -> dict[str, str]:
    """Build environment dict with isolated XDG directories."""
    return {
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "PATH": os.environ.get("PATH", ""),
    }


class TestE2E:
    def test_given_contact_when_added_listed_touched_and_removed_then_returns_to_empty(self, tmp_path: Path) -> None:
        env = _env(tmp_path)

        r = _cli("add", "--name", "Alice", "--email", "alice@example.com", env=env)
        assert r.returncode == 0, r.stderr

        r = _cli("list", env=env)
        assert r.returncode == 0, r.stderr
        assert "alice" in r.stdout

        r = _cli("touch", "alice", env=env)
        assert r.returncode == 0, r.stderr
        assert "Touched: alice" in r.stdout

        r = _cli("due", env=env)
        assert r.returncode == 0, r.stderr
        assert "Nothing due." in r.stdout

        r = _cli("remove", "alice", "--force", env=env)
        assert r.returncode == 0, r.stderr
        assert "Removed: alice" in r.stdout

        r = _cli("list", env=env)
        assert r.returncode == 0, r.stderr
        assert "No contacts yet." in r.stdout

    def test_given_added_contact_when_due_then_shows_as_due(self, tmp_path: Path) -> None:
        env = _env(tmp_path)

        r = _cli("add", "--name", "Bob", "--email", "bob@example.com", env=env)
        assert r.returncode == 0, r.stderr

        r = _cli("due", env=env)
        assert r.returncode == 0, r.stderr
        assert "bob" in r.stdout

    def test_given_touched_contact_when_due_then_shows_nothing_due(self, tmp_path: Path) -> None:
        env = _env(tmp_path)

        r = _cli(
            "add",
            "--name", "Carol",
            "--email", "carol@example.com",
            "--priority", "network",
            env=env,
        )
        assert r.returncode == 0, r.stderr

        r = _cli("due", env=env)
        assert r.returncode == 0, r.stderr
        assert "carol" in r.stdout

        r = _cli("touch", "carol", env=env)
        assert r.returncode == 0, r.stderr

        r = _cli("due", env=env)
        assert r.returncode == 0, r.stderr
        assert "Nothing due." in r.stdout

    def test_given_deleted_state_file_when_rebuild_state_then_list_shows_contact(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        data_dir = tmp_path / "cache" / "com.kevincojean" / "cli-tools-friend"

        r = _cli("add", "--name", "Dave", "--email", "dave@example.com", env=env)
        assert r.returncode == 0, r.stderr

        r = _cli("touch", "dave", env=env)
        assert r.returncode == 0, r.stderr

        state_file = data_dir / "state.jsonl"
        assert state_file.exists()
        state_file.unlink()

        r = _cli("rebuild-state", env=env)
        assert r.returncode == 0, r.stderr
        assert "Rebuilt state" in r.stdout

        r = _cli("list", env=env)
        assert r.returncode == 0, r.stderr
        assert "dave" in r.stdout

    def test_given_config_set_when_config_show_then_shows_updated_value(self, tmp_path: Path) -> None:
        env = _env(tmp_path)

        r = _cli("config-set", "cadence.deep", "7", env=env)
        assert r.returncode == 0, r.stderr
        assert "Set cadence.deep = 7" in r.stdout

        r = _cli("config-show", env=env)
        assert r.returncode == 0, r.stderr
        assert '"deep": 7' in r.stdout

    def test_given_added_contact_when_force_removed_then_list_shows_empty(self, tmp_path: Path) -> None:
        env = _env(tmp_path)

        r = _cli("add", "--name", "Eve", "--email", "eve@example.com", env=env)
        assert r.returncode == 0, r.stderr

        r = _cli("remove", "eve", "--force", env=env)
        assert r.returncode == 0, r.stderr

        r = _cli("list", env=env)
        assert r.returncode == 0, r.stderr
        assert "No contacts yet." in r.stdout

    def test_given_invalid_email_when_add_then_returns_one(self, tmp_path: Path) -> None:
        env = _env(tmp_path)

        r = _cli("add", "--name", "Frank", "--email", "not-an-email", env=env)
        assert r.returncode == 1
        assert "invalid email" in r.stderr.lower()

    def test_given_priority_deep_filter_when_list_then_only_deep_contacts_shown(self, tmp_path: Path) -> None:
        env = _env(tmp_path)

        r = _cli(
            "add", "--name", "Grace",
            "--email", "grace@example.com",
            "--priority", "deep",
            env=env,
        )
        assert r.returncode == 0, r.stderr

        r = _cli(
            "add", "--name", "Heidi",
            "--email", "heidi@example.com",
            "--priority", "casual",
            env=env,
        )
        assert r.returncode == 0, r.stderr

        r = _cli("list", "--priority", "deep", env=env)
        assert r.returncode == 0, r.stderr
        assert "grace" in r.stdout
        assert "heidi" not in r.stdout
