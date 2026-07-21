"""End-to-end tests for the cli-friendkeeper CLI.

Each test runs the real CLI via ``subprocess.run`` with isolated
``XDG_CACHE_HOME`` and ``XDG_CONFIG_HOME`` directories (via ``tmp_path``).
No mocking — every test is a true end-to-end shell invocation.
"""

from __future__ import annotations

import os
import re
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


def _parse_id(add_stdout: str) -> str:
    """Extract the UUID from ``add`` output: ``Added: Name (id: <uuid>)``."""
    m = re.search(r"\(id: ([a-f0-9-]+)\)", add_stdout)
    assert m, f"Could not parse id from: {add_stdout}"
    return m.group(1)


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
        contact_id = _parse_id(r.stdout)

        r = _cli("list", env=env)
        assert r.returncode == 0, r.stderr
        assert "Alice" in r.stdout

        r = _cli("touch", contact_id, env=env)
        assert r.returncode == 0, r.stderr
        assert "Touched: Alice" in r.stdout

        r = _cli("due", env=env)
        assert r.returncode == 0, r.stderr
        assert "Nothing due." in r.stdout

        r = _cli("remove", contact_id, "--force", env=env)
        assert r.returncode == 0, r.stderr
        assert "Removed: Alice" in r.stdout

        r = _cli("list", env=env)
        assert r.returncode == 0, r.stderr
        assert "No contacts yet." in r.stdout

    def test_given_added_contact_when_due_then_shows_as_due(self, tmp_path: Path) -> None:
        env = _env(tmp_path)

        r = _cli("add", "--name", "Bob", "--email", "bob@example.com", env=env)
        assert r.returncode == 0, r.stderr

        r = _cli("due", env=env)
        assert r.returncode == 0, r.stderr
        assert "Bob" in r.stdout

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
        contact_id = _parse_id(r.stdout)

        r = _cli("due", env=env)
        assert r.returncode == 0, r.stderr
        assert "Carol" in r.stdout

        r = _cli("touch", contact_id, env=env)
        assert r.returncode == 0, r.stderr

        r = _cli("due", env=env)
        assert r.returncode == 0, r.stderr
        assert "Nothing due." in r.stdout

    def test_given_deleted_state_file_when_rebuild_state_then_list_shows_contact(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        data_dir = tmp_path / "cache" / "com.kevincojean.cli-friendkeeper"

        r = _cli("add", "--name", "Dave", "--email", "dave@example.com", env=env)
        assert r.returncode == 0, r.stderr
        contact_id = _parse_id(r.stdout)

        r = _cli("touch", contact_id, env=env)
        assert r.returncode == 0, r.stderr

        state_file = data_dir / "state.jsonl"
        assert state_file.exists()
        state_file.unlink()

        r = _cli("rebuild-state", env=env)
        assert r.returncode == 0, r.stderr
        assert "Rebuilt state" in r.stdout

        r = _cli("list", env=env)
        assert r.returncode == 0, r.stderr
        assert "Dave" in r.stdout

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
        contact_id = _parse_id(r.stdout)

        r = _cli("remove", contact_id, "--force", env=env)
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
        assert "Grace" in r.stdout
        assert "Heidi" not in r.stdout

    def test_given_acquaintance_contact_when_due_then_never_shown(self, tmp_path: Path) -> None:
        """given acquaintance contact when due then never shown as due."""
        env = _env(tmp_path)

        r = _cli(
            "add", "--name", "Ivan",
            "--email", "ivan@example.com",
            "--priority", "acquaintance",
            env=env,
        )
        assert r.returncode == 0, r.stderr

        # Never touched — normally would be due, but not for acquaintance
        r = _cli("due", env=env)
        assert r.returncode == 0, r.stderr
        assert "Nothing due." in r.stdout or "Ivan" not in r.stdout

        # Should still appear in list
        r = _cli("list", env=env)
        assert r.returncode == 0, r.stderr
        assert "Ivan" in r.stdout

    def test_given_acquaintance_with_explicit_cadence_when_due_then_shown(self, tmp_path: Path) -> None:
        """given acquaintance with explicit --cadence-days when due then normal due logic."""
        env = _env(tmp_path)

        r = _cli(
            "add", "--name", "Judy",
            "--email", "judy@example.com",
            "--priority", "acquaintance",
            "--cadence-days", "1",
            env=env,
        )
        assert r.returncode == 0, r.stderr

        # Never touched but has explicit cadence of 1 day — due
        r = _cli("due", env=env)
        assert r.returncode == 0, r.stderr
        assert "Judy" in r.stdout
