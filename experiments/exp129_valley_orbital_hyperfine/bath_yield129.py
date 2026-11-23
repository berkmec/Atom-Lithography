"""Exp129 (H147): Portable Multi-Core Mode B Epitaxial Bath K=8 Yield & DDRF Gap-Risk Engine.

Portably reproduces Exp59/62 Mode B epitaxial bath K=8 selection physics relative to repository
ROOT (zero hardcoded user or Windows paths, zero side-effect directory creation).

Audit gate (CE5):
  - Legacy KL on exact seed59 (N=100): f=0.5% -> 26/100, f=1.0% -> 51/100, f=2.0% -> 69/100.

Production comparison (CE6, CE7):
  - N_cell = 400 realizations per abundance across f in {0.5%, 1.0%, 2.0%} comparing:
      (1) Legacy KL (Exp25/42/59/62 baseline)
      (2) VOKL-6 (normalized (0,0,4)=2.981 MHz + extended-wavefunction dipolar tensor)
      (3) VOKL-6 point-dipole sensitivity (isolating pure Fermi-contact shift vs KL)
      (4) VOKL-6 ab-initio scaling sensitivity (eta_Si=186, zero (0,0,4) rescaling)
  - Tracks certified K=8 yield (with 95% Wilson CI), eligible/strong counts, radial distribution
    of selected register qubits, min_transition_gap_Hz quantiles, and fraction below Exp126's
    6.893 kHz DDRF crosstalk threshold (plus 10 kHz and 16 kHz thresholds).

Epistemic status: no_lab_measurement=True ({Model}/{Sayısal-Simülasyon}).
"""
from __future__ import annotations

import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "exp25_universal_atom"))
sys.path.insert(0, str(ROOT / "experiments" / "exp42_isotope_coded_atom"))

import isotope42 as iso  # noqa: E402

PRIMARY = iso.PRIMARY
BDIR = iso.DIRS[PRIMARY]
A_KL_PRIMARY = iso.A_BY_DIR[PRIMARY]
NU_HZ = iso.NU_HZ
SITES_NM = iso.SITES
N_SITES = len(SITES_NM)
SITE_RADII_NM = np.linalg.norm(SITES_NM, axis=1)

_PULSE = json.loads((ROOT / "results" / "exp47" / "pulse47.json").read_text(encoding="utf-8"))
_DET_GRID = np.asarray(_PULSE["detunings_hz"], dtype=np.float64)
_LOG_DET = np.log10(_DET_GRID)
_LOG_ENV = {
    (f, t): np.log10(np.maximum(np.asarray(_PULSE["jitter_envelope"][f][str(t)], dtype=np.float64), 1e-300))
    for f, t in (("GAUSS", 500), ("HANN", 500), ("GAUSS", 1000), ("HANN", 1000))
}

GAP_THRESH_EXP126_HZ = 6893.0
GAP_THRESH_10KHZ_HZ = 10000.0
GAP_THRESH_16KHZ_HZ = 16000.0


def seed59(f_pct: float, real: int) -> int:
    """Exact Exp59/62 deterministic seed formula."""
    return 59_000_000 + int(round(f_pct * 1000.0)) * 1000 + int(real)


def wilson_ci95(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """95% Wilson score confidence interval for binomial proportion."""
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1.0 + (z * z) / total
    center = (p + (z * z) / (2.0 * total)) / denom
    half = (z / denom) * math.sqrt((p * (1.0 - p)) / total + (z * z) / (4.0 * total * total))
    return (max(0.0, center - half), min(1.0, center + half))


def pulse_p(fam: str, tus: int, detuning_hz: np.ndarray) -> np.ndarray:
    x = np.log10(np.maximum(np.asarray(detuning_hz, dtype=np.float64), 1.0))
    return 10.0 ** np.interp(x, _LOG_DET, _LOG_ENV[(fam, int(tus))])


def eligibility(avals: np.ndarray, fam: str = "GAUSS", tus: int = 500) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorized exact GAUSS500 eligibility matching Exp48/59/62 bit-for-bit."""
    m = len(avals)
    freqs = np.empty(2 * m, dtype=np.float64)
    freqs[0::2] = np.abs(NU_HZ + avals / 2.0)
    freqs[1::2] = np.abs(NU_HZ - avals / 2.0)

    # Full pairwise detuning matrix (m, 2*m) with self-transition (i, 2*i) excluded cleanly
    target_f = freqs[0::2][:, None]
    det = np.abs(freqs[None, :] - target_f)
    p = pulse_p(fam, tus, det)
    # Zero out self-transition (i, 2*i) before max and sum
    idx_i = np.arange(m)
    p[idx_i, 2 * idx_i] = 0.0
    max_flip = np.max(p, axis=1)
    sum_flip = np.sum(p, axis=1)
    elig = (max_flip <= 1e-3) & (sum_flip <= 1e-2)
    return elig, max_flip, sum_flip


def pair_masks(cloud: np.ndarray) -> tuple[list[int], np.ndarray, np.ndarray]:
    pos = SITES_NM[cloud]
    dist = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=2)
    jmat = np.abs(iso.dipolar_J(pos, BDIR))
    feasible = (dist >= 0.30) & (jmat <= 100.0)
    np.fill_diagonal(feasible, False)
    masks = []
    for i in range(len(cloud)):
        mask_val = 0
        for j in np.where(feasible[i])[0]:
            mask_val |= 1 << int(j)
        masks.append(mask_val)
    return masks, dist, jmat


def find_rank_clique(
    mask: int,
    need: int,
    chosen: list[int],
    adj: list[int],
    avals: np.ndarray,
    priority: dict[int, float],
) -> list[int] | None:
    if need == 0:
        return list(chosen) if iso.vandermonde_metrics(avals[list(chosen)])["rank"] == 8 else None
    if mask.bit_count() < need:
        return None
    bits = [i for i in range(len(avals)) if mask & (1 << i)]
    v = min(bits, key=lambda i: priority[i])
    included = find_rank_clique(mask & adj[v] & ~(1 << v), need - 1, chosen + [v], adj, avals, priority)
    if included is not None:
        return included
    return find_rank_clique(mask & ~(1 << v), need, chosen, adj, avals, priority)


def pulse_exact(
    eligible_idx: np.ndarray,
    gaps: np.ndarray,
    sum_flip: np.ndarray,
    adj: list[int],
    avals: np.ndarray,
) -> np.ndarray | None:
    if len(eligible_idx) < 8:
        return None
    order = sorted((int(i) for i in eligible_idx), key=lambda i: (-gaps[i], sum_flip[i]))
    priority = {int(i): float(sum_flip[i]) for i in eligible_idx}
    for low_pos in range(7, len(order)):
        req = order[low_pos]
        prefix_mask = 0
        for i in order[:low_pos]:
            prefix_mask |= 1 << i
        mask = prefix_mask & adj[req]
        found = find_rank_clique(mask, 7, [req], adj, avals, priority)
        if found is not None:
            return np.array(found, dtype=int)
    return None


def pulse_greedy(
    eligible_idx: np.ndarray,
    gaps: np.ndarray,
    sum_flip: np.ndarray,
    cloud: np.ndarray,
    avals: np.ndarray,
    seed: int = 5900,
    starts: int = 12,
) -> np.ndarray | None:
    eligible = [int(i) for i in eligible_idx]
    if len(eligible) < 8:
        return None
    rng = np.random.default_rng(seed)
    pos = SITES_NM[cloud]
    dist = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=2)
    jmat = np.abs(iso.dipolar_J(pos, BDIR))
    ranked = sorted(eligible, key=lambda i: (-gaps[i], sum_flip[i]))
    start_list = ranked[:5] + [int(x) for x in rng.choice(ranked, size=min(starts - 5, len(ranked)), replace=False)]
    best = None
    for first in start_list:
        sel = [int(first)]
        while len(sel) < 8:
            scored = []
            for i in eligible:
                if i in sel:
                    continue
                if np.min(dist[i, sel]) < 0.30 or np.max(jmat[i, sel]) > 100.0:
                    continue
                score = (
                    min(gaps[i], 100_000.0) / 1000.0
                    - 1000.0 * float(sum_flip[i])
                    - 0.05 * float(np.max(jmat[i, sel]))
                    + 20.0 * float(np.min(dist[i, sel]))
                )
                scored.append((score, i))
            if not scored:
                break
            sel.append(max(scored)[1])
        if len(sel) < 8 or iso.vandermonde_metrics(avals[sel])["rank"] != 8:
            continue
        key = (float(np.min(gaps[sel])), -float(np.max(sum_flip[sel])))
        if best is None or key > best[0]:
            best = (key, np.array(sel, dtype=int))
    return None if best is None else best[1]


# Worker global coupling table (initialized per pool to avoid pickling 45k array per task)
_WORKER_A_ALL: np.ndarray | None = None


def _init_worker(a_all: np.ndarray) -> None:
    global _WORKER_A_ALL
    _WORKER_A_ALL = a_all


def _eval_one_bath_realization(args: tuple[float, int, int]) -> tuple[int, int, int, float, float, float, float, float]:
    """Evaluate one deterministic Mode B epitaxial bath realization.

    Returns:
      (success, n_elig, n_strong, min_gap_Hz, max_J_Hz, min_pair_d_nm, min_abs_A_sel_Hz, mean_r_sel_nm)
    """
    f_pct, m_atoms, real = args
    assert _WORKER_A_ALL is not None
    rng = np.random.default_rng(seed59(f_pct, real))
    cloud = np.sort(rng.choice(N_SITES, size=m_atoms, replace=False))
    avals = _WORKER_A_ALL[cloud]
    n_strong = int(np.sum(np.abs(avals) >= 10e3))
    gaps = iso.register_gaps(avals, avals)
    elig_mask, _mf, sum_flip = eligibility(avals, "GAUSS", 500)
    eidx = np.where(elig_mask)[0]
    n_elig = int(len(eidx))

    sel = None
    if n_elig >= 8:
        if n_elig <= 28:
            adj, _d, _j = pair_masks(cloud)
            sel = pulse_exact(eidx, gaps, sum_flip, adj, avals)
        else:
            sel = pulse_greedy(eidx, gaps, sum_flip, cloud, avals, seed=5900 + real)

    if sel is None:
        return (0, n_elig, n_strong, 0.0, 0.0, 0.0, 0.0, 0.0)

    sel_arr = np.asarray(sel, dtype=int)
    pos = SITES_NM[cloud[sel_arr]]
    dmat = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=2)
    iu = np.triu_indices(8, 1)
    min_d = float(np.min(dmat[iu]))
    max_j = float(np.max(np.abs(iso.dipolar_J(pos, BDIR)[iu])))
    rank = iso.vandermonde_metrics(avals[sel_arr])["rank"]
    if not (min_d >= 0.30 and max_j <= 100.0 and rank == 8):
        return (0, n_elig, n_strong, 0.0, 0.0, 0.0, 0.0, 0.0)

    min_gap = float(np.min(gaps[sel_arr]))
    min_abs_a = float(np.min(np.abs(avals[sel_arr])))
    mean_r = float(np.mean(SITE_RADII_NM[cloud[sel_arr]]))
    return (1, n_elig, n_strong, min_gap, max_j, min_d, min_abs_a, mean_r)


def run_mode_b_cell(
    a_all: np.ndarray,
    f_pct: float,
    reals: int = 400,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Run Mode B K=8 bath yield simulation for abundance f_pct across `reals` realizations."""
    m_atoms = int(round((f_pct / 100.0) * N_SITES))
    tasks = [(float(f_pct), m_atoms, r) for r in range(reals)]
    workers = max_workers or min(8, os.cpu_count() or 1)

    if workers <= 1 or reals < 16:
        _init_worker(a_all)
        rows = [_eval_one_bath_realization(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(a_all,)) as ex:
            rows = list(ex.map(_eval_one_bath_realization, tasks, chunksize=8))

    succ_flags = [r[0] for r in rows]
    elig_counts = [r[1] for r in rows]
    strong_counts = [r[2] for r in rows]
    successes = int(sum(succ_flags))
    yield_frac = float(successes / reals)
    ci_lo, ci_hi = wilson_ci95(successes, reals)

    cert_gaps = np.array([r[3] for r in rows if r[0] == 1], dtype=np.float64)
    cert_max_j = np.array([r[4] for r in rows if r[0] == 1], dtype=np.float64)
    cert_min_d = np.array([r[5] for r in rows if r[0] == 1], dtype=np.float64)
    cert_min_a = np.array([r[6] for r in rows if r[0] == 1], dtype=np.float64)
    cert_mean_r = np.array([r[7] for r in rows if r[0] == 1], dtype=np.float64)

    if len(cert_gaps) > 0:
        gap_stats: dict[str, Any] = {
            "count": int(len(cert_gaps)),
            "min_Hz": float(np.min(cert_gaps)),
            "p10_Hz": float(np.percentile(cert_gaps, 10)),
            "p25_Hz": float(np.percentile(cert_gaps, 25)),
            "median_Hz": float(np.median(cert_gaps)),
            "mean_Hz": float(np.mean(cert_gaps)),
            "p75_Hz": float(np.percentile(cert_gaps, 75)),
            "p90_Hz": float(np.percentile(cert_gaps, 90)),
            "max_Hz": float(np.max(cert_gaps)),
            "frac_lt_6893Hz": float(np.mean(cert_gaps < GAP_THRESH_EXP126_HZ)),
            "count_lt_6893Hz": int(np.sum(cert_gaps < GAP_THRESH_EXP126_HZ)),
            "frac_lt_10kHz": float(np.mean(cert_gaps < GAP_THRESH_10KHZ_HZ)),
            "count_lt_10kHz": int(np.sum(cert_gaps < GAP_THRESH_10KHZ_HZ)),
            "frac_lt_16kHz": float(np.mean(cert_gaps < GAP_THRESH_16KHZ_HZ)),
            "count_lt_16kHz": int(np.sum(cert_gaps < GAP_THRESH_16KHZ_HZ)),
            "yield_and_gap_ge_6893Hz": float(np.sum(cert_gaps >= GAP_THRESH_EXP126_HZ) / reals),
            "yield_and_gap_ge_10kHz": float(np.sum(cert_gaps >= GAP_THRESH_10KHZ_HZ) / reals),
            "max_J_median_Hz": float(np.median(cert_max_j)),
            "max_J_p90_Hz": float(np.percentile(cert_max_j, 90)),
            "min_pair_dist_median_nm": float(np.median(cert_min_d)),
            "min_abs_A_selected_median_Hz": float(np.median(cert_min_a)),
            "selected_mean_radius_median_nm": float(np.median(cert_mean_r)),
            "certified_min_gaps_Hz_sorted": np.sort(cert_gaps).tolist(),
        }
    else:
        gap_stats = {
            "count": 0,
            "median_Hz": 0.0,
            "frac_lt_6893Hz": 1.0,
            "frac_lt_10kHz": 1.0,
            "frac_lt_16kHz": 1.0,
            "yield_and_gap_ge_6893Hz": 0.0,
            "yield_and_gap_ge_10kHz": 0.0,
            "certified_min_gaps_Hz_sorted": [],
        }

    return {
        "abundance_pct": float(f_pct),
        "M_atoms": int(m_atoms),
        "realizations": int(reals),
        "successes": successes,
        "yield_frac": yield_frac,
        "wilson_ci95": [float(ci_lo), float(ci_hi)],
        "eligible_median": float(np.median(elig_counts)),
        "eligible_mean": float(np.mean(elig_counts)),
        "strong_median": float(np.median(strong_counts)),
        "strong_mean": float(np.mean(strong_counts)),
        "gap_stats": gap_stats,
    }


def run_exp59_62_audit(max_workers: int | None = None) -> dict[str, Any]:
    """Bit-for-bit audit against Exp59/62 legacy KL yields on seed59 (reals=100)."""
    targets = {0.5: 26, 1.0: 51, 2.0: 69}
    audit = {}
    all_exact = True
    for f_pct, expected_succ in targets.items():
        res = run_mode_b_cell(A_KL_PRIMARY, f_pct=f_pct, reals=100, max_workers=max_workers)
        matched = bool(res["successes"] == expected_succ)
        all_exact = all_exact and matched
        audit[f"F{f_pct:g}"] = {
            "abundance_pct": f_pct,
            "expected_successes_100": expected_succ,
            "computed_successes_100": res["successes"],
            "yield_frac": res["yield_frac"],
            "eligible_median": res["eligible_median"],
            "strong_median": res["strong_median"],
            "exact_match": matched,
        }
    return {"all_exact_match": all_exact, "cells": audit}


if __name__ == "__main__":
    import time
    t0 = time.time()
    aud = run_exp59_62_audit()
    print(f"Exp59/62 audit completed in {time.time() - t0:.2f} s | all_exact={aud['all_exact_match']}")
    for k, v in aud["cells"].items():
        print(" ", k, v)
