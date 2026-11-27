"""Pytest configuration and path/optional-dependency guards for Atom Lithography Machine.

Ensures both the repository root (`.`) and `src/` are on `sys.path` even when pytest
is invoked without `PYTHONPATH`, and gracefully excludes untracked optional-FEM legacy
tests when their optional binary/FEM dependencies (`gmsh`, `skfem`) are absent from the
active Python environment.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"

for _entry in (str(_SRC_DIR), str(_REPO_ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

collect_ignore: list[str] = []

if importlib.util.find_spec("gmsh") is None:
    collect_ignore.append("test_fem.py")

if importlib.util.find_spec("skfem") is None:
    collect_ignore.append("test_chain_phonon.py")
