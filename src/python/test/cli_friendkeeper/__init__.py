"""Test package for cli-friendkeeper.

The main ``cli_friendkeeper`` package lives under ``src/python/main``, but
pytest discovers tests under ``src/python/test``.  Without this ``__init__.py``
the test directory isn't a real package and can shadow the main one.

This module:
1. Inserts ``src/python/main`` early in ``sys.path`` so the real ``cli_friendkeeper``
   is found for absolute imports.
2. Redirects ``__path__`` to the main package directory so sub-module resolution
   (e.g. ``cli_friendkeeper.clock``) hits the real implementation.
3. Registers ``conftest`` as a top-level alias in ``sys.modules`` so that test
   files inside ``tests/`` can use ``from conftest import FakeStore``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# 1. Main source tree first in sys.path
_main_src = str(Path(__file__).resolve().parent.parent.parent / "main")
if _main_src not in sys.path:
    sys.path.insert(0, _main_src)

# 2. Include both the test-package directory (conftest.py lives here) and the
#    main-package directory (so sub-module imports resolve to the real code).
_test_dir = Path(__file__).resolve().parent
_main_dir = _test_dir.parent.parent / "main" / "cli_friendkeeper"
__path__ = [str(_test_dir), str(_main_dir)]

# 3. Top-level conftest alias so ``from conftest import …`` works in tests/
import importlib

_conftest = importlib.import_module("cli_friendkeeper.conftest")
sys.modules["conftest"] = _conftest
