"""Tests for cli_friendkeeper.store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cli_friendkeeper.store import (
    StorageError,
    append_jsonl,
    flock_exclusive,
    read_jsonl,
    write_jsonl_atomic,
)


class TestReadJsonl:
    def test_given_missing_file_when_reading_then_returns_empty_list(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.jsonl"
        assert read_jsonl(path) == []

    def test_given_empty_file_when_reading_then_returns_empty_list(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        assert read_jsonl(path) == []

    def test_given_file_with_blank_lines_when_reading_then_skips_them(self, tmp_path: Path) -> None:
        path = tmp_path / "blanks.jsonl"
        path.write_text('\n\n{"a": 1}\n\n{"b": 2}\n\n')
        assert read_jsonl(path) == [{"a": 1}, {"b": 2}]

    def test_given_corrupt_line_when_reading_then_raises_storage_error(self, tmp_path: Path) -> None:
        path = tmp_path / "corrupt.jsonl"
        path.write_text('{"valid": true}\nnot json\n{"also_valid": false}\n')
        with pytest.raises(StorageError, match="corrupt line"):
            read_jsonl(path)

    def test_given_appended_records_when_reading_then_returns_them(self, tmp_path: Path) -> None:
        path = tmp_path / "roundtrip.jsonl"
        records = [{"name": "Alice"}, {"name": "Bob", "age": 30}]
        for r in records:
            append_jsonl(path, r)
        assert read_jsonl(path) == records


class TestAppendJsonl:
    def test_given_missing_file_when_appending_then_creates_it(self, tmp_path: Path) -> None:
        path = tmp_path / "new.jsonl"
        append_jsonl(path, {"x": 1})
        assert path.read_text() == '{"x": 1}\n'

    def test_given_existing_file_when_appending_then_adds_to_it(self, tmp_path: Path) -> None:
        path = tmp_path / "existing.jsonl"
        path.write_text('{"a": 1}\n')
        append_jsonl(path, {"b": 2})
        assert read_jsonl(path) == [{"a": 1}, {"b": 2}]


class TestWriteJsonlAtomic:
    def test_given_records_when_writing_then_readable(self, tmp_path: Path) -> None:
        path = tmp_path / "atomic.jsonl"
        records = [{"id": 1}, {"id": 2}]
        write_jsonl_atomic(path, records)
        assert read_jsonl(path) == records

    def test_given_atomic_write_when_complete_then_no_tmp_file_left(self, tmp_path: Path) -> None:
        path = tmp_path / "notmp.jsonl"
        write_jsonl_atomic(path, [{"x": 1}])
        assert not path.with_suffix(".jsonl.tmp").exists()

    def test_given_atomic_write_when_successful_then_replaces_content(
        self, tmp_path: Path,
    ) -> None:
        path = tmp_path / "safe.jsonl"
        path.write_text('{"original": true}\n')
        write_jsonl_atomic(path, [{"new": "data"}])
        assert read_jsonl(path) == [{"new": "data"}]

    def test_given_symlink_file_when_writing_atomically_then_preserves_symlink(
        self, tmp_path: Path,
    ) -> None:
        target = tmp_path / "real.jsonl"
        target.write_text('{"original": true}\n')
        link = tmp_path / "link.jsonl"
        link.symlink_to(target)
        write_jsonl_atomic(link, [{"new": "data"}])
        assert link.is_symlink()
        assert link.resolve() == target.resolve()
        assert read_jsonl(target) == [{"new": "data"}]
        assert read_jsonl(link) == [{"new": "data"}]


class TestFlockExclusive:
    def test_given_lock_when_acquiring_then_releases(self, tmp_path: Path) -> None:
        path = tmp_path / "lock.jsonl"
        with flock_exclusive(path):
            path.write_text('{"held": true}\n')
        assert path.read_text() == '{"held": true}\n'

    def test_given_lock_when_exception_then_still_releases(self, tmp_path: Path) -> None:
        path = tmp_path / "except.jsonl"
        with pytest.raises(RuntimeError):
            with flock_exclusive(path):
                path.write_text('{"before": true}\n')
                raise RuntimeError("boom")
        assert path.read_text() == '{"before": true}\n'
