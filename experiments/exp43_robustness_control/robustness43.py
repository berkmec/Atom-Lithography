"""Exp43A: placement/coupling robustness of the Exp42 isotope code.
Registered in results/exp43/predictions_exp43.json before this run.
Output: results/exp43/robustness43.json.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(r"E:\quantum_cell")
sys.path.insert(0, str(ROOT / "experiments" / "exp42_isotope_coded_atom"))
import isotope42 as iso  # noqa: E402

EXP42 = json.loads((ROOT / "results" / "exp42" / "isotope42.json").read_text(encoding="utf-8"))
TREE = cKDTree(iso.SITES)
PRIMARY = iso.PRIMARY
BDIR = iso.DIRS[PRIMARY]
A_PRIMARY = iso.A_BY_DIR[PRIMARY]
NU = iso.NU_HZ


def compact(m, extra=None):
    out = dict(
        min_transition_gap_Hz=float(m["min_transition_gap_Hz"]),
        retained_10kHz=int(m["addressable_counts"]["10kHz"]),
        retained_30kHz=int(m["addressable_counts"]["30kHz"]),
        retained_100kHz=int(m["addressable_counts"]["100kHz"]),
        all10=bool(m["all_addressable_10kHz"]), all30=bool(m["all_addressable_30kHz"]),
        max_abs_J_Hz=float(m["max_abs_J_Hz"]), min_pair_distance_nm=float(m["min_pair_distance_nm"]),
        nn_pairs=int(m["nn_pairs_lt_0p24nm"]), resolving_time_s=float(m["resolving_time_s"]),
        vandermonde_rank=int(m["vandermonde"]["rank"]),
        vandermonde_log10_condition=m["vandermonde"]["log10_condition"],
    )
    if extra:
        out.update(extra)
    return out


def custom_metrics(positions, A_register, bdir, A_extra=()):
    pos = np.asarray(positions, dtype=float)
    A = np.asarray(A_register, dtype=float)
    K = len(A)
    env = np.concatenate([A, np.asarray(A_extra, dtype=float)]) if len(A_extra) else A
    gaps = iso.register_gaps(A, env)
    if K > 1:
        dmat = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=2)
        iu = np.triu_indices(K, 1)
        pair_d = dmat[iu]
        pair_J = np.abs(iso.dipolar_J(pos, bdir)[iu])
        min_gap_A = float(np.min(np.diff(np.sort(A))))
    else:
        pair_d = np.array([np.inf]); pair_J = np.array([0.0]); min_gap_A = float("inf")
    min_abs = float(np.min(np.abs(A)))
    resolving = float(1.0 / min(min_abs, min_gap_A)) if min(min_abs, min_gap_A) > 0 else float("inf")
    vm = iso.vandermonde_metrics(A)
    return dict(
        min_transition_gap_Hz=float(np.min(gaps)), transition_gaps_Hz=[float(x) for x in gaps],
        addressable_counts={f"{int(d/1000)}kHz": int(np.sum(gaps >= d)) for d in (10e3, 30e3, 100e3)},
        all_addressable_10kHz=bool(np.all(gaps >= 10e3)), all_addressable_30kHz=bool(np.all(gaps >= 30e3)),
        all_addressable_100kHz=bool(np.all(gaps >= 100e3)), min_pair_distance_nm=float(np.min(pair_d)),
        nn_pairs_lt_0p24nm=int(np.sum(pair_d < 0.24)), max_abs_J_Hz=float(np.max(pair_J)),
        resolving_time_s=resolving, vandermonde=vm,
    )


def summarize(rows, K):
    gaps = np.array([x["min_transition_gap_Hz"] for x in rows], dtype=float)
    ret10 = np.array([x["retained_10kHz"] for x in rows], dtype=float)
    ret30 = np.array([x["retained_30kHz"] for x in rows], dtype=float)
    res = np.array([x["resolving_time_s"] for x in rows], dtype=float)
    finite = np.isfinite(res)
    return dict(
        K=int(K), realizations=int(len(rows)),
        median_min_gap_Hz=float(np.median(gaps)), p10_min_gap_Hz=float(np.percentile(gaps, 10)),
        p90_min_gap_Hz=float(np.percentile(gaps, 90)),
        fraction_all10=float(np.mean([x["all10"] for x in rows])),
        fraction_all30=float(np.mean([x["all30"] for x in rows])),
        fraction_at_least_Kminus1_10=float(np.mean(ret10 >= K - 1)),
        fraction_at_least_Kminus1_30=float(np.mean(ret30 >= K - 1)),
        median_retained_10=float(np.median(ret10)), median_retained_30=float(np.median(ret30)),
        median_max_J_Hz=float(np.median([x["max_abs_J_Hz"] for x in rows])),
        fraction_any_NN_pair=float(np.mean([x["nn_pairs"] > 0 for x in rows])),
        fraction_full_vandermonde=float(np.mean([x["vandermonde_rank"] == K for x in rows])),
        median_resolving_time_s=float(np.median(res[finite])) if np.any(finite) else None,
        fraction_infinite_resolving=float(np.mean(~finite)),
        min_gap_samples_Hz=[float(x) for x in gaps],
    )


def nominal_flip(actual_A, nominal_A, rabi_hz=10e3):
    omega = 2 * np.pi * rabi_hz
    tau = np.pi / omega
    det = 2 * np.pi * ((np.abs(NU + np.asarray(actual_A) / 2) - np.abs(NU + np.asarray(nominal_A) / 2)))
    w = np.sqrt(omega**2 + det**2)
    return (omega**2 / w**2) * np.sin(w * tau / 2) ** 2


def gaussian_snap(base_idx, sigma, rng):
    chosen = []
    used = set()
    for idx in base_idx:
        target = iso.SITES[idx] + rng.normal(0.0, sigma, size=3)
        _, neigh = TREE.query(target, k=100)
        pick = None
        for cand in np.atleast_1d(neigh):
            cand = int(cand)
            if cand not in used:
                pick = cand
                break
        if pick is None:
            _, neigh = TREE.query(target, k=2000)
            pick = next(int(c) for c in neigh if int(c) not in used)
        chosen.append(pick)
        used.add(pick)
    return np.array(chosen, dtype=int)


def main():
    t0 = time.time()
    base = {K: np.array(EXP42["iso_code_primary"][str(K)]["site_indices"], dtype=int) for K in (4, 8, 12)}
    out = dict(exp="43A", date="2026-10-19", registered="predictions_exp43.json", scenarios={})

    # One-site displacement.
    one_site = {}
    nominal_displaced = {}
    for K, idx0 in base.items():
        nominal_A = A_PRIMARY[idx0]
        for radius in (0.25, 0.50, 1.00):
            neighbors = [np.array([j for j in TREE.query_ball_point(iso.SITES[idx], radius) if j != idx], dtype=int) for idx in idx0]
            rng = np.random.default_rng(43100 + K * 100 + int(radius * 100))
            rows, flips = [], []
            for _ in range(1000):
                slot = int(rng.integers(0, K))
                choices = np.array([j for j in neighbors[slot] if j not in set(idx0.tolist())], dtype=int)
                new_idx = idx0.copy()
                if len(choices):
                    new_idx[slot] = int(rng.choice(choices))
                m = iso.subset_metrics(new_idx, A_PRIMARY, BDIR)
                rows.append(compact(m))
                flips.append(float(nominal_flip(A_PRIMARY[new_idx[slot]], nominal_A[slot])))
            key = f"K{K}_R{radius:.2f}nm"
            one_site[key] = summarize(rows, K)
            nominal_displaced[key] = dict(median_flip=float(np.median(flips)), mean_flip=float(np.mean(flips)),
                                          p90_flip=float(np.percentile(flips, 90)))
            print("ONE_SITE", key, one_site[key]["fraction_all30"], nominal_displaced[key], flush=True)
    out["scenarios"]["one_site_displacement"] = one_site
    out["nominal_pulse_one_site"] = nominal_displaced

    # All-site Gaussian snap.
    gauss = {}
    gauss_k8_indices = {}
    for K, idx0 in base.items():
        for sigma in (0.10, 0.25, 0.50, 1.00):
            rng = np.random.default_rng(43200 + K * 100 + int(sigma * 100))
            rows, keep_idx = [], []
            for rep in range(1000):
                idx = gaussian_snap(idx0, sigma, rng)
                rows.append(compact(iso.subset_metrics(idx, A_PRIMARY, BDIR)))
                if K == 8 and rep < 1000:
                    keep_idx.append(idx)
            key = f"K{K}_sigma{sigma:.2f}nm"
            gauss[key] = summarize(rows, K)
            if K == 8:
                gauss_k8_indices[key] = keep_idx
            print("GAUSS", key, gauss[key]["fraction_all30"], gauss[key]["median_retained_30"], flush=True)
    out["scenarios"]["gaussian_snap"] = gauss

    # B-direction retune on the same Gaussian sigma=0.50 K=8 placements.
    fixed_rows, retuned_rows = [], []
    dir_wins = {d: 0 for d in iso.DIRS}
    for idx in gauss_k8_indices["K8_sigma0.50nm"]:
        candidates = {}
        for direction in iso.DIRS:
            candidates[direction] = iso.subset_metrics(idx, iso.A_BY_DIR[direction], iso.DIRS[direction])
        fixed_rows.append(compact(candidates[PRIMARY]))
        best_dir = max(candidates, key=lambda d: candidates[d]["min_transition_gap_Hz"])
        dir_wins[best_dir] += 1
        retuned_rows.append(compact(candidates[best_dir], dict(best_direction=best_dir)))
    out["B_retune_GAUSS_K8_sigma0p50"] = dict(
        fixed_123=summarize(fixed_rows, 8), retuned=summarize(retuned_rows, 8), direction_wins=dir_wins,
        median_gap_ratio=float(np.median([r["min_transition_gap_Hz"] for r in retuned_rows]) /
                               np.median([r["min_transition_gap_Hz"] for r in fixed_rows])),
    )
    print("B_RETUNE", out["B_retune_GAUSS_K8_sigma0p50"], flush=True)

    # Coupling-only errors.
    coupling = {}
    for K, idx0 in base.items():
        pos = iso.SITES[idx0]
        A0 = A_PRIMARY[idx0]
        for sigma in (0.10, 0.25, 0.50):
            rng = np.random.default_rng(43300 + K * 100 + int(sigma * 100))
            rows = []
            for _ in range(1000):
                Aerr = A0 * np.exp(rng.normal(0.0, sigma, size=K))
                rows.append(compact(custom_metrics(pos, Aerr, BDIR)))
            key = f"K{K}_sigma_lnA{sigma:.2f}"
            coupling[key] = summarize(rows, K)
            print("COUPLING", key, coupling[key]["fraction_all30"], flush=True)
    out["scenarios"]["coupling_lognormal"] = coupling

    # Combined K=8 scenarios.
    combined = {}
    idx0 = base[8]
    all_idx = np.arange(len(iso.SITES))
    for label, sigma_pos, sigma_A, ppm in (("moderate", 0.25, 0.25, 200), ("severe", 0.50, 0.50, 800)):
        rng = np.random.default_rng(43400 + ppm)
        rows = []
        for _ in range(500):
            idx = gaussian_snap(idx0, sigma_pos, rng)
            Aerr = A_PRIMARY[idx] * np.exp(rng.normal(0.0, sigma_A, size=8))
            remaining = np.array([i for i in all_idx if i not in set(idx.tolist())], dtype=int)
            occ = rng.random(len(remaining)) < ppm * 1e-6
            residual = remaining[occ]
            Ares = A_PRIMARY[residual] * np.exp(rng.normal(0.0, sigma_A, size=len(residual)))
            rows.append(compact(custom_metrics(iso.SITES[idx], Aerr, BDIR, Ares)))
        combined[label] = summarize(rows, 8)
        combined[label].update(sigma_pos_nm=sigma_pos, sigma_lnA=sigma_A, residual_ppm=ppm)
        print("COMBINED", label, combined[label], flush=True)
    out["scenarios"]["combined_K8"] = combined
    out["runtime_s"] = round(time.time() - t0, 1)
    dst = ROOT / "results" / "exp43" / "robustness43.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("WROTE", dst, "runtime", out["runtime_s"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

