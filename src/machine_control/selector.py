"""Register selection, two fidelity levels.

StochasticSelector: Bernoulli attempts at the registered bath yield (Exp59/62),
for factory-scale runs.
AtlasSelector: one real bath-cloud attempt through the project's own
pulse-aware selection (Exp42/43/44/48 machinery), for verification runs.

v2.0 (2026-11-22):
- Replaced hardcoded Windows path ``Path(r"E:\\quantum_cell")`` with portable
  repo-root resolution (``find_repo_root()``).
- Added a clean, read-only in-memory import bridge that rewrites embedded
  ``E:\\quantum_cell`` paths when loading legacy ``experiments/exp42..48``
  modules so ``AtlasSelector`` runs natively on Linux and Windows without
  mutating any archived experiment files.
- Fixed ``_seed59`` to use ``self.abundance_pct`` (exact match at 1.0%).
"""
from __future__ import annotations

import os
import re
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import numpy as np


def find_repo_root(start: Path | None = None) -> Path:
    """Resolve the atom_lithography_machine / quantum_cell repository root."""
    env_root = os.environ.get("ALM_REPO_ROOT")
    if env_root:
        p = Path(env_root).resolve()
        if (p / "experiments").is_dir():
            return p
    here = (start or Path(__file__)).resolve()
    for candidate in (here.parent, *here.parents):
        if (candidate / "experiments").is_dir() and (candidate / "src").is_dir():
            return candidate
    raise FileNotFoundError(
        f"Could not locate repository root containing 'experiments/' and 'src/' from {here}"
    )


ROOT = find_repo_root()

# Ordered legacy Exp25/42/43/44/48 modules required by AtlasSelector.
_LEGACY_CHAIN = (
    ("ap25_register", "experiments/exp25_universal_atom/ap25_register.py"),
    ("ap25_control", "experiments/exp25_universal_atom/ap25_control.py"),
    ("isotope42", "experiments/exp42_isotope_coded_atom/isotope42.py"),
    ("robustness43", "experiments/exp43_robustness_control/robustness43.py"),
    ("adaptive44", "experiments/exp44_adaptive_isotope_code/adaptive44.py"),
    ("pulse_select48", "experiments/exp48_pulse_aware_selection/pulse_select48.py"),
)


def _rewrite_legacy_windows_paths(source: str, repo_root: Path) -> str:
    """Rewrite literal ``r"E:\\quantum_cell..."`` strings in memory only."""
    posix_root = repo_root.resolve().as_posix()

    def _repl(match: re.Match[str]) -> str:
        tail = match.group(1).replace("\\", "/")
        return repr(f"{posix_root}{tail}")

    # Match raw or normal single/double quoted strings starting with E:\quantum_cell
    pattern = re.compile(r'r?["\']E:\\\\?quantum_cell([^"\']*)["\']')
    return pattern.sub(_repl, source)


def _load_legacy_module(module_name: str, rel_path: str, repo_root: Path) -> types.ModuleType:
    """Load an archived experiment module without touching disk files."""
    if module_name in sys.modules:
        mod = sys.modules[module_name]
        # Verify cached module points to this repo root if it defines ROOT
        if not hasattr(mod, "ROOT") or Path(getattr(mod, "ROOT")).resolve() == repo_root.resolve():
            return mod
    file_path = repo_root / rel_path
    if not file_path.is_file():
        raise FileNotFoundError(f"Legacy physics module not found: {file_path}")
    raw_src = file_path.read_text(encoding="utf-8")
    patched_src = _rewrite_legacy_windows_paths(raw_src, repo_root)
    mod = types.ModuleType(module_name)
    mod.__file__ = str(file_path)
    mod.__package__ = ""
    sys.modules[module_name] = mod
    code = compile(patched_src, str(file_path), "exec")
    exec(code, mod.__dict__)
    return mod


def load_atlas_modules(repo_root: Path | None = None):
    """Load and return ``(isotope42, adaptive44, pulse_select48)`` portably."""
    root = (repo_root or find_repo_root()).resolve()
    # Ensure exp25 dir is on sys.path for internal relative imports
    exp25_dir = str(root / "experiments" / "exp25_universal_atom")
    if exp25_dir not in sys.path:
        sys.path.insert(0, exp25_dir)
    loaded = {}
    for mod_name, rel_path in _LEGACY_CHAIN:
        loaded[mod_name] = _load_legacy_module(mod_name, rel_path, root)
    return loaded["isotope42"], loaded["adaptive44"], loaded["pulse_select48"]


@dataclass
class AttemptResult:
    success: bool
    true_lines_Hz: np.ndarray | None   # hyperfine line set when a register exists
    info: dict


class StochasticSelector:
    """Fast mode: success ~ Bernoulli(p_eff); lines synthesized around a template."""

    TEMPLATE_HZ = np.array([2.981e6, 1.9e6, 1.2e6, 0.8e6, 0.45e6, 0.22e6, 0.11e6, 0.055e6])

    def __init__(self, yield_frac: float, rng: np.random.Generator):
        self.yield_frac = float(yield_frac)
        self.rng = rng

    def attempt(self, p_eff: float) -> AttemptResult:
        if self.rng.random() < p_eff:
            jitter = self.rng.normal(1.0, 0.05, size=len(self.TEMPLATE_HZ))
            return AttemptResult(True, self.TEMPLATE_HZ * jitter, {"mode": "stochastic"})
        return AttemptResult(False, None, {"mode": "stochastic"})


class AtlasSelector:
    """Verification mode: real Exp48 pulse-aware selection on a bath cloud."""

    def __init__(self, abundance_pct: float, seed: int = 0, repo_root: Path | None = None):
        iso, ad, ps = load_atlas_modules(repo_root)
        self.iso, self.ad, self.ps = iso, ad, ps
        self.abundance_pct = float(abundance_pct)
        self.A_all = iso.A_BY_DIR[iso.PRIMARY]
        self.n_sites = len(iso.SITES)
        self.m = int(round(self.abundance_pct / 100.0 * self.n_sites))
        self.seed = int(seed)
        self.counter = 0

    def _seed59(self, real: int) -> int:
        return 59_000_000 + int(round(self.abundance_pct * 1000)) * 1000 + int(real)

    def attempt(self, p_eff: float | None = None) -> AttemptResult:
        iso, ad, ps = self.iso, self.ad, self.ps
        rng = np.random.default_rng(self._seed59(self.seed + self.counter))
        self.counter += 1
        cloud = np.sort(rng.choice(self.n_sites, size=self.m, replace=False))
        avals = self.A_all[cloud]
        gaps = iso.register_gaps(avals, avals)
        eligible, _mf, sum_flip = ps.eligibility(cloud, avals, "GAUSS", 500)
        eidx = np.where(eligible)[0]
        sel = None
        if len(eidx) >= 8:
            if len(eidx) <= 28:
                adj, _d, _j = ps.pair_masks(cloud)
                sel = ps.pulse_exact(eidx, gaps, sum_flip, adj, avals)
            else:
                sel = ps.pulse_greedy(eidx, gaps, sum_flip, cloud, avals, seed=5900)
        if sel is None:
            return AttemptResult(False, None, {"mode": "atlas", "eligible": int(len(eidx))})
        ev = ad.evaluate_selection(cloud, np.asarray(sel), avals)
        ok = (
            ev["min_pair_distance_nm"] >= 0.30
            and ev["max_abs_J_Hz"] <= 100.0
            and ev["vandermonde_rank"] == 8
        )
        lines = np.sort(np.abs(avals[np.asarray(sel)])) if ok else None
        return AttemptResult(
            bool(ok),
            lines,
            {"mode": "atlas", "eligible": int(len(eidx)), "evaluation": ev},
        )
