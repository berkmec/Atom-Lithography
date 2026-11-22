"""Exp124 Track 1 (Part 3): Portable Exp57/105 yield engine + 3D anisotropic BCA & surface truncation.

Portably loads Exp25/42 Kohn-Luttinger lattice/hyperfine physics and Exp47 pulse envelopes
relative to repository ROOT (zero Windows E:\\ paths, zero side-effect directories).

Audit gate:
  - Must reproduce Exp57 AUDIT_S5_N1024 = 49/100 (0.4900) bit-for-bit.
  - Must reproduce Exp105 S3.8_N1024 = 277/400 (0.6925) bit-for-bit.

Anisotropic physics extensions:
  - True 3D Gaussian (sigma_x, sigma_y, sigma_z) with Exp92 BCA (sigma_z=2.88 nm, R_p=6.46 nm)
    and Exp91 Holmes (sigma_z=5.27 nm) straggle profiles.
  - Wafer surface boundary condition z_lab > 0 (both pre-snap ion loss and post-snap lattice site).
  - Stochastic 31P donor 3D straggle mode (correlated cloud-to-donor shift + donor backscatter).

Epistemic status: no_lab_measurement=True ({Model}/{Sayisal-Simulasyon}).
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
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "exp25_universal_atom"))
sys.path.insert(0, str(ROOT / "experiments" / "exp42_isotope_coded_atom"))

import isotope42 as iso  # noqa: E402

PRIMARY = iso.PRIMARY
BDIR = iso.DIRS[PRIMARY]
A_ALL = iso.A_BY_DIR[PRIMARY]
NU = iso.NU_HZ
SITES = iso.SITES
TREE = cKDTree(SITES)

_PULSE = json.loads((ROOT / "results" / "exp47" / "pulse47.json").read_text(encoding="utf-8"))
_DET_GRID = np.asarray(_PULSE["detunings_hz"], dtype=float)
_LOG_DET = np.log10(_DET_GRID)
_LOG_ENV = {
    (f, t): np.log10(np.maximum(np.asarray(_PULSE["jitter_envelope"][f][str(t)], dtype=float), 1e-300))
    for f, t in (("GAUSS", 500), ("HANN", 500), ("GAUSS", 1000), ("HANN", 1000))
}


def pulse_p(fam: str, tus: int, detuning_hz: np.ndarray) -> np.ndarray:
    x = np.log10(np.maximum(np.asarray(detuning_hz, dtype=float), 1.0))
    return 10.0 ** np.interp(x, _LOG_DET, _LOG_ENV[(fam, int(tus))])


def eligibility(cloud: np.ndarray, avals: np.ndarray, fam: str = "GAUSS", tus: int = 500):
    freqs = np.empty(2 * len(cloud))
    freqs[0::2] = np.abs(NU + avals / 2.0)
    freqs[1::2] = np.abs(NU - avals / 2.0)
    max_flip = np.zeros(len(cloud))
    sum_flip = np.zeros(len(cloud))
    for i in range(len(cloud)):
        det = np.abs(freqs - freqs[2 * i])
        det = np.delete(det, 2 * i)
        p = pulse_p(fam, tus, det)
        max_flip[i] = float(np.max(p))
        sum_flip[i] = float(np.sum(p))
    eligible = (max_flip <= 1e-3) & (sum_flip <= 1e-2)
    return eligible, max_flip, sum_flip


def pair_masks(cloud: np.ndarray):
    pos = SITES[cloud]
    dist = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=2)
    jmat = np.abs(iso.dipolar_J(pos, BDIR))
    feasible = (dist >= 0.30) & (jmat <= 100.0)
    np.fill_diagonal(feasible, False)
    masks = []
    for i in range(len(cloud)):
        m = 0
        for j in np.where(feasible[i])[0]:
            m |= 1 << int(j)
        masks.append(m)
    return masks, dist, jmat


def find_rank_clique(mask: int, need: int, chosen: list[int], adj: list[int], avals: np.ndarray, priority: dict[int, float]):
    if need == 0:
        return list(chosen) if iso.vandermonde_metrics(avals[list(chosen)])["rank"] == 8 else None
    if bin(mask).count("1") < need:
        return None
    bits = [i for i in range(len(avals)) if mask & (1 << i)]
    v = min(bits, key=lambda i: priority[i])
    included = find_rank_clique(mask & adj[v] & ~(1 << v), need - 1, chosen + [v], adj, avals, priority)
    if included is not None:
        return included
    return find_rank_clique(mask & ~(1 << v), need, chosen, adj, avals, priority)


def pulse_exact(eligible_idx: np.ndarray, gaps: np.ndarray, sum_flip: np.ndarray, adj: list[int], avals: np.ndarray):
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


def pulse_greedy(eligible_idx: np.ndarray, gaps: np.ndarray, sum_flip: np.ndarray,
                 cloud: np.ndarray, avals: np.ndarray, seed: int = 4800, starts: int = 12):
    eligible = [int(i) for i in eligible_idx]
    if len(eligible) < 8:
        return None
    rng = np.random.default_rng(seed)
    pos = SITES[cloud]
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
                score = (min(gaps[i], 100_000.0) / 1000.0 - 1000.0 * float(sum_flip[i])
                         - 0.05 * float(np.max(jmat[i, sel])) + 20.0 * float(np.min(dist[i, sel])))
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


def verify_selection_criteria(cloud: np.ndarray, sel: np.ndarray, avals: np.ndarray) -> bool:
    """Exact Exp44/57/105 acceptance check: min_d >= 0.30 nm, max |J| <= 100 Hz, Vandermonde rank == 8."""
    pos = SITES[cloud[sel]]
    dmat = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=2)
    iu = np.triu_indices(len(sel), 1)
    min_d = float(np.min(dmat[iu]))
    max_j = float(np.max(np.abs(iso.dipolar_J(pos, BDIR)[iu])))
    rank = iso.vandermonde_metrics(avals[sel])["rank"]
    return bool(min_d >= 0.30 and max_j <= 100.0 and rank == 8)


def _eval_single_realization(args: tuple) -> tuple[int, int, int, int, int, int, int]:
    """Worker evaluating one deterministic realization.

    Returns (success, n_eligible, n_strong, n_lost_surface, n_lost_far, donor_backscattered, donor_shallow_lt2nm).
    """
    (sigma_x, sigma_y, sigma_z, n_imp, real, seed, surface_cut, Rp_nm, donor_straggle) = args
    rng = np.random.default_rng(seed)

    # 1. Donor position in lab frame (z_lab > 0 inside crystal; surface at z_lab = 0)
    donor_back = 0
    donor_shallow = 0
    if donor_straggle:
        dx_d = float(rng.normal(0.0, sigma_x))
        dy_d = float(rng.normal(0.0, sigma_y))
        dz_d = float(rng.normal(0.0, sigma_z))
        z_d_lab = Rp_nm + dz_d
        if surface_cut and z_d_lab <= 0.0:
            # Donor backscattered out of wafer -> failed attempt
            return (0, 0, 0, 0, n_imp, 1, 0)
        if z_d_lab < 2.0:
            donor_shallow = 1
        donor_offset = np.array([dx_d, dy_d, dz_d], dtype=float)
    else:
        z_d_lab = Rp_nm
        donor_offset = np.zeros(3, dtype=float)

    # 2. Implant N 29Si atoms around centroid (0, 0, Rp_nm)
    if sigma_x == sigma_y == sigma_z and not surface_cut and not donor_straggle:
        # Exact bit-for-bit RNG call order of _yield105.py!
        pts = rng.normal(0.0, sigma_x, size=(n_imp, 3))
        lost_surf = 0
    else:
        # Standard normal draw scaled per axis (preserves exact RNG call shape (n, 3))
        pts = rng.normal(0.0, 1.0, size=(n_imp, 3)) * np.array([sigma_x, sigma_y, sigma_z])
        if surface_cut:
            z_si_lab = Rp_nm + pts[:, 2]
            in_crystal = z_si_lab > 0.0
            lost_surf = int(n_imp - np.sum(in_crystal))
            pts = pts[in_crystal]
        else:
            lost_surf = 0

    # Transform to donor-centered frame
    pts_rel = pts - donor_offset
    r = np.linalg.norm(pts_rel, axis=1)
    keep = pts_rel[r <= 6.0]
    lost_far = int(len(pts_rel) - len(keep))

    if len(keep) == 0:
        return (0, 0, 0, lost_surf, lost_far, donor_back, donor_shallow)

    _d, idx = TREE.query(keep)
    cloud = np.unique(idx.astype(int))

    # Post-snap surface check: no lattice site may lie outside crystal (z_d_lab + z_site <= 0)
    if surface_cut and len(cloud) > 0:
        valid_site = (z_d_lab + SITES[cloud, 2]) > 0.0
        cloud = cloud[valid_site]

    if len(cloud) < 8:
        n_strong = int(np.sum(np.abs(A_ALL[cloud]) >= 10e3)) if len(cloud) else 0
        return (0, 0, n_strong, lost_surf, lost_far, donor_back, donor_shallow)

    avals = A_ALL[cloud]
    n_strong = int(np.sum(np.abs(avals) >= 10e3))
    gaps = iso.register_gaps(avals, avals)
    elig_mask, _mf, sum_flip = eligibility(cloud, avals, "GAUSS", 500)
    eidx = np.where(elig_mask)[0]
    n_elig = int(len(eidx))

    sel = None
    if n_elig >= 8:
        if n_elig <= 28:
            adj, _dist, _j = pair_masks(cloud)
            sel = pulse_exact(eidx, gaps, sum_flip, adj, avals)
        else:
            sel = pulse_greedy(eidx, gaps, sum_flip, cloud, avals, seed=5700 + real)

    succ = 1 if (sel is not None and verify_selection_criteria(cloud, np.asarray(sel), avals)) else 0
    return (succ, n_elig, n_strong, lost_surf, lost_far, donor_back, donor_shallow)


def seed57(sigma: float, n: int, real: int) -> int:
    return 57_000_000 + int(sigma) * 1_000_000 + int(n) * 1000 + int(real)


def seed105(sigma: float, n: int, real: int) -> int:
    return 105_000_000 + int(round(sigma * 10)) * 1_000_000 + int(n) * 1000 + int(real)


def seed124(cell_idx: int, n: int, real: int) -> int:
    return 124_000_000 + int(cell_idx) * 1_000_000 + int(n) * 1000 + int(real)


def run_cell(
    label: str,
    sigma_x: float,
    sigma_y: float,
    sigma_z: float,
    n_imp: int,
    reals: int,
    seeds: list[int],
    surface_cut: bool = True,
    Rp_nm: float = 6.4582,
    donor_straggle: bool = False,
    workers: int | None = None,
) -> dict[str, Any]:
    """Run deterministic Monte Carlo yield cell across CPU workers."""
    tasks = [
        (float(sigma_x), float(sigma_y), float(sigma_z), int(n_imp), int(r), int(seeds[r]),
         bool(surface_cut), float(Rp_nm), bool(donor_straggle))
        for r in range(reals)
    ]
    n_workers = workers if workers is not None else max(1, min(os.cpu_count() or 1, 8))
    if n_workers > 1 and reals >= 20:
        with ProcessPoolExecutor(max_workers=n_workers) as ex:
            results = list(ex.map(_eval_single_realization, tasks, chunksize=max(1, reals // (n_workers * 4))))
    else:
        results = [_eval_single_realization(t) for t in tasks]

    arr = np.array(results, dtype=int)
    succ = int(np.sum(arr[:, 0]))
    y = float(succ / reals)
    # Binomial 1-sigma SE and 95% Wilson CI
    se = math.sqrt(y * (1.0 - y) / reals)
    z95 = 1.95996398454
    denom = 1.0 + z95 ** 2 / reals
    center = (y + z95 ** 2 / (2.0 * reals)) / denom
    half = (z95 / denom) * math.sqrt(y * (1.0 - y) / reals + z95 ** 2 / (4.0 * reals ** 2))

    # Effective geometric mean sigma
    sigma_geom_3d = (sigma_x * sigma_y * sigma_z) ** (1.0 / 3.0)
    # Expected specs & shots per certified register (R=1, Exp65 analytic exact = 1/y)
    specs_per_reg = (1.0 / y) if y > 0 else float("inf")
    shots_per_reg = ((n_imp + 1) / y) if y > 0 else float("inf")

    return {
        "label": label,
        "sigma_x_nm": float(sigma_x),
        "sigma_y_nm": float(sigma_y),
        "sigma_z_nm": float(sigma_z),
        "sigma_geom_3d_nm": float(sigma_geom_3d),
        "N_implanted": int(n_imp),
        "realizations": int(reals),
        "surface_cut": bool(surface_cut),
        "Rp_nm": float(Rp_nm),
        "donor_straggle": bool(donor_straggle),
        "successes": succ,
        "yield_frac": y,
        "yield_se": float(se),
        "ci95_lo": float(max(0.0, center - half)),
        "ci95_hi": float(min(1.0, center + half)),
        "eligible_median": float(np.median(arr[:, 1])),
        "strong_median": float(np.median(arr[:, 2])),
        "lost_surface_frac_mean": float(np.mean(arr[:, 3]) / n_imp),
        "lost_far_frac_mean": float(np.mean(arr[:, 4]) / n_imp),
        "donor_backscatter_frac": float(np.mean(arr[:, 5])),
        "donor_shallow_lt2nm_frac": float(np.mean(arr[:, 6])),
        "exp_specs_per_register": float(specs_per_reg),
        "exp_shots_per_register": float(shots_per_reg),
    }


def run_all_anisotropic_yields(sigma_exp124_nm: float, reals: int = 400) -> dict[str, Any]:
    """Execute exact Exp57/105 audits + full 3D anisotropic BCA/Holmes/surface/donor sweep."""
    cells = {}

    # 1. Mandatory bit-for-bit audits (exact original seeds!)
    cells["AUDIT_EXP57_S5_N1024"] = run_cell(
        "AUDIT_EXP57_S5_N1024", 5.0, 5.0, 5.0, 1024, 100,
        [seed57(5.0, 1024, r) for r in range(100)],
        surface_cut=False, Rp_nm=6.4582, donor_straggle=False,
    )
    cells["AUDIT_EXP105_ISO3p8_N1024"] = run_cell(
        "AUDIT_EXP105_ISO3p8_N1024", 3.8, 3.8, 3.8, 1024, 400,
        [seed105(3.8, 1024, r) for r in range(400)],
        surface_cut=False, Rp_nm=6.4582, donor_straggle=False,
    )

    # 2. 3D Anisotropic BCA & Holmes sweep (400 realizations/cell, Rp=6.4582 nm from Exp92 5 keV)
    # Using shared cell-index seed124 scheme for complete determinism
    specs = [
        # (key, idx, sx, sy, sz, N, surf, Rp, donor_straggle)
        ("ANISO_BCA_PURE_N1024",           1, 3.25, 3.25, 2.88, 1024, True,  6.4582, False),
        ("ANISO_BCA_PURE_N256",            2, 3.25, 3.25, 2.88,  256, True,  6.4582, False),
        ("ANISO_P91_BCA_N1024",            3, 3.80, 3.80, 2.88, 1024, True,  6.4582, False),
        ("ANISO_P91_BCA_N256",             4, 3.80, 3.80, 2.88,  256, True,  6.4582, False),
        ("ANISO_EXP124_BCA_N1024",         5, sigma_exp124_nm, sigma_exp124_nm, 2.88, 1024, True, 6.4582, False),
        ("ANISO_BCA_HOLMES_N1024",         6, 3.25, 3.25, 5.27, 1024, True,  6.4582, False),
        ("ANISO_P91_HOLMES_N1024",         7, 3.80, 3.80, 5.27, 1024, True,  6.4582, False),
        ("ANISO_P91_HOLMES_N256",          8, 3.80, 3.80, 5.27,  256, True,  6.4582, False),
        ("ANISO_P91_HOLMES_RP9_N1024",     9, 3.80, 3.80, 5.27, 1024, True,  9.0000, False),
        ("ANISO_P91_BCA_NOSURF_N1024",    10, 3.80, 3.80, 2.88, 1024, False, 6.4582, False),
        ("ANISO_P91_HOLMES_NOSURF_N1024", 11, 3.80, 3.80, 5.27, 1024, False, 6.4582, False),
        ("ANISO_P91_BCA_DONOR_N1024",     12, 3.80, 3.80, 2.88, 1024, True,  6.4582, True),
        ("ANISO_EXP124_BCA_DONOR_N1024",  13, sigma_exp124_nm, sigma_exp124_nm, 2.88, 1024, True, 6.4582, True),
        ("ANISO_P91_HOLMES_DONOR_N1024",  14, 3.80, 3.80, 5.27, 1024, True,  6.4582, True),
    ]

    for key, idx, sx, sy, sz, n_imp, surf, rp, dstr in specs:
        cells[key] = run_cell(
            key, sx, sy, sz, n_imp, reals,
            [seed124(idx, n_imp, r) for r in range(reals)],
            surface_cut=surf, Rp_nm=rp, donor_straggle=dstr,
        )

    return cells
