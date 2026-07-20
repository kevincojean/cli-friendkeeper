"""Low-level JSONL (JSON Lines) file I/O with flock-based locking.

Provides read, append, and atomic-write operations for JSONL files,
using ``fcntl.flock`` for cross-process synchronisation.
"""

from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from cli_friendkeeper.errors import StorageError


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file, returning one dict per non-blank line.

    Returns an empty list if the file does not exist.
    Raises |StorageError| on JSON parse errors.
    """
    if not path.exists():
        return []

    records: list[dict] = []
    with path.open("r") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError:
                raise StorageError(f"corrupt line in {path}: {line!r}")
    return records


def append_jsonl(path: Path, record: dict) -> None:
    """Append *record* as one JSON line under an exclusive flock.

    Creates the file if it does not exist.  The flock guarantees that
    concurrent writers (even in separate processes) do not interleave
    their output lines.
    """
    with path.open("a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(json.dumps(record) + "\n")
        f.flush()
        os.fsync(f.fileno())
        # File closed -> lock released automatically.


def write_jsonl_atomic(path: Path, records: list[dict]) -> None:
    """Atomically replace *path* with *records* serialised as JSONL.

    Writes to a ``.tmp`` sibling, then uses :func:`os.replace` for an
    atomic swap so that concurrent readers always see a consistent file.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


@contextmanager
def flock_exclusive(path: Path) -> Generator[None, None, None]:
    """Context manager that acquires an exclusive flock on *path*.

    The file is opened in append mode and kept open for the duration of
    the ``with`` block, guaranteeing mutual exclusion across processes.
    The lock is released (and the file closed) when the block exits.
    """
    f = path.open("a")
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        f.close()
