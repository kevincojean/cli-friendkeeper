"""Concurrency tests — verify that flock serialization works across concurrent subprocess calls.

Each test launches multiple subprocesses in parallel via ``ThreadPoolExecutor``
and asserts correct behaviour under contention.  No mocking — every test uses
real flock via real subprocess invocations.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import subprocess
from pathlib import Path

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


def _parse_id(add_stdout: str) -> str:
    m = re.search(r"\(id: ([a-f0-9-]+)\)", add_stdout)
    assert m, f"Could not parse id from: {add_stdout}"
    return m.group(1)


def _data_dir(tmp_path: Path) -> Path:
    """Return the data directory within an isolated tmp_path."""
    return tmp_path / "cache" / "com.kevincojean.cli-friendkeeper"


class TestConcurrency:
    """Race-condition tests for flock-based serialization."""

    def test_given_contact_when_concurrent_touch_then_touch_count_equals_parallel_calls(self, tmp_path: Path) -> None:
        """5 parallel ``friend touch <id>`` calls → touch_count == 5 (no lost updates)."""
        env = _env(tmp_path)
        data_dir = _data_dir(tmp_path)

        r = _cli(
            "add",
            "--name", "Alice",
            "--email", "alice@example.com",
            env=env,
        )
        assert r.returncode == 0, r.stderr
        contact_id = _parse_id(r.stdout)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(_cli, "touch", contact_id, env=env)
                for _ in range(5)
            ]
            results = [
                f.result() for f in concurrent.futures.as_completed(futures)
            ]

        for i, r in enumerate(results):
            assert r.returncode == 0, f"Touch {i} failed: {r.stderr}"

        state_path = data_dir / "state.jsonl"
        assert state_path.exists(), f"state.jsonl not found at {state_path}"
        lines = [
            json.loads(line)
            for line in state_path.read_text().strip().split("\n")
            if line.strip()
        ]
        alice_states = [s for s in lines if s.get("id") == contact_id]
        assert len(alice_states) == 1, (
            f"Expected 1 state entry for {contact_id}, got {len(alice_states)}"
        )
        assert alice_states[0]["touch_count"] == 5, (
            f"Expected touch_count=5, got {alice_states[0]['touch_count']}"
        )

    def test_given_different_names_when_concurrent_add_then_all_succeed(self, tmp_path: Path) -> None:
        """5 parallel ``friend add`` for different names → all 5 succeed, 5 contacts exist."""
        env = _env(tmp_path)
        names = ["alice", "bob", "carol", "dave", "eve"]

        def add_person(name: str) -> subprocess.CompletedProcess:
            return _cli(
                "add", "--name", name.capitalize(),
                "--email", f"{name}@example.com",
                env=env,
            )

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=5
        ) as executor:
            future_to_name = {
                executor.submit(add_person, name): name for name in names
            }
            results: list[tuple[str, subprocess.CompletedProcess]] = []
            for future in concurrent.futures.as_completed(future_to_name):
                name = future_to_name[future]
                results.append((name, future.result()))

        for name, r in results:
            assert r.returncode == 0, (
                f"Add '{name}' failed: {r.stderr}"
            )

        r = _cli("list", "--json", env=env)
        assert r.returncode == 0, r.stderr
        contacts = json.loads(r.stdout)
        assert len(contacts) == 5, (
            f"Expected 5 contacts, got {len(contacts)}: "
            f"{[c['name'] for c in contacts]}"
        )

    def test_given_same_contact_when_concurrent_remove_then_exactly_one_succeeds(self, tmp_path: Path) -> None:
        """5 parallel ``friend remove <id> --force`` → exactly 1 succeeds, 4 fail."""
        env = _env(tmp_path)

        r = _cli(
            "add",
            "--name", "Alice",
            "--email", "alice@example.com",
            env=env,
        )
        assert r.returncode == 0, r.stderr
        contact_id = _parse_id(r.stdout)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=5
        ) as executor:
            futures = [
                executor.submit(
                    _cli, "remove", contact_id, "--force", env=env
                )
                for _ in range(5)
            ]
            results = [
                f.result() for f in concurrent.futures.as_completed(futures)
            ]

        success_count = sum(1 for r in results if r.returncode == 0)
        fail_count = sum(1 for r in results if r.returncode == 1)

        assert success_count == 1, (
            f"Expected exactly 1 success, got {success_count}. "
            f"Return codes: {[r.returncode for r in results]}"
        )
        assert fail_count == 4, (
            f"Expected exactly 4 failures, got {fail_count}. "
            f"Return codes: {[r.returncode for r in results]}"
        )

        for r in results:
            if r.returncode == 1:
                assert any(
                    msg in r.stderr.lower()
                    for msg in ["not found", "already removed"]
                ), (
                    f"Expected failure message in stderr, got: {r.stderr}"
                )

        r = _cli("list", env=env)
        assert r.returncode == 0, r.stderr
        assert "No contacts yet." in r.stdout
