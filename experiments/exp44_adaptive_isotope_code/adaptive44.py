"""Exp44: post-fabrication adaptive isotope-code selection.

The fabrication step produces an actual 29Si cloud around one 31P donor.
Post-fabrication spectroscopy provides measured couplings for that cloud; an
adaptive selector then chooses K nuclei while every unselected nucleus remains
as a spectator. Registered in results/exp44/predictions_exp44.json.
Output: results/exp44/adaptive44.json.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(r"E:\quantum_cell")
sys.path.insert(0, str(ROOT / "experiments" / "exp42_isotope_coded_atom"))
sys.path.insert(0, str(ROOT / "experiments" / "exp43_robustness_control"))
import isotope42 as iso  # noqa: E402
import robustness43 as rob  # noqa: E402

PRIMARY = iso.PRIMARY
BDIR = iso.DIRS[PRIMARY]
A_ALL = iso.A_BY_DIR[PRIMARY]
NU = iso.NU_HZ


def intended_targets(max_m=128):
    cand = np.where(np.abs(A_ALL) >= 10e3)[0]
    cand = cand[np.argsort(-np.abs(A_ALL[cand]))]
    chosen = []
    for idx in cand:
        if all(np.linalg.norm(iso.SITES[idx] - iso.SITES[j]) >= 0.30 for j in chosen):
            chosen.append(int(idx))
        if len(chosen) == max_m:
            break
    return np.array(chosen, dtype=int)


INTENDED = intended_targets(128)
CANDIDATES = np.where(np.abs(A_ALL) >= 10e3)[0]


def robust_gaps(A_hat, rel=0.25):
    A = np.asarray(A_hat, dtype=float)
    lo = np.minimum(A * (1 - rel), A * (1 + rel))
    hi = np.maximum(A * (1 - rel), A * (1 + rel))
    intervals = []
    for a_lo, a_hi in zip(lo, hi):
        intervals.append((abs(NU + a_lo / 2), abs(NU + a_hi / 2)))
        intervals.append((abs(NU - a_lo / 2), abs(NU - a_hi / 2)))
    intervals = np.array([[min(a, b), max(a, b)] for a, b in intervals], dtype=float)
    gaps = []
    for k in range(len(A)):
        target = intervals[2 * k]
        dists = []
        for j, iv in enumerate(intervals):
            if j == 2 * k:
                continue
            dists.append(max(0.0, max(target[0], iv[0]) - min(target[1], iv[1])))
        gaps.append(float(min(dists)))
    return np.array(gaps), intervals


def selector(cloud_idx, A_hat, K=8, robust=False, starts=12, seed=4400, extra_freqs=None):
    cloud_idx = np.array(cloud_idx, dtype=int)
    A_hat = np.asarray(A_hat, dtype=float)
    pos = iso.SITES[cloud_idx]
    M = len(cloud_idx)
    fp = np.abs(NU + A_hat / 2)
    fm = np.abs(NU - A_hat / 2)
    freq = np.column_stack([fp, fm])
    if robust:
        full_gap, intervals = robust_gaps(A_hat, 0.25)
        intervals = intervals.reshape(M, 2, 2)
    else:
        full_gap = iso.register_gaps(A_hat, A_hat)
        intervals = None
    if extra_freqs is not None and len(extra_freqs):
        extra = np.asarray(extra_freqs, dtype=float)
        nearest_extra = np.min(np.abs(fp[:, None] - extra[None, :]), axis=1)
        full_gap = np.minimum(full_gap, nearest_extra)
    rng = np.random.default_rng(seed)
    start_order = list(np.argsort(-full_gap)[:5])
    start_order += [int(x) for x in rng.integers(0, M, max(0, starts - len(start_order)))]
    best = None

    for start in start_order:
        selected = [int(start)]
        used = np.zeros(M, dtype=bool)
        used[start] = True
        while len(selected) < K:
            sel = np.array(selected, dtype=int)
            dist = np.linalg.norm(pos[:, None, :] - pos[None, sel, :], axis=2)
            min_dist = np.min(dist, axis=1)
            dvec = pos[:, None, :] - pos[None, sel, :]
            with np.errstate(divide="ignore", invalid="ignore"):
                cos = np.where(dist > 0, (dvec @ BDIR) / np.where(dist == 0, 1, dist), 0.0)
                Jcross = np.where(dist > 0, np.abs(iso.D_NN * (1 - 3 * cos**2) / np.where(dist == 0, 1, dist) ** 3), 0.0)
            max_J = np.max(Jcross, axis=1)
            if robust:
                cross_gap = np.full(M, np.inf)
                cand_lo = intervals[:, :, 0]
                cand_hi = intervals[:, :, 1]
                for s in sel:
                    for tt in range(2):
                        iv_lo, iv_hi = intervals[s, tt, 0], intervals[s, tt, 1]
                        dist_iv = np.maximum(0.0, np.maximum(cand_lo, iv_lo) - np.minimum(cand_hi, iv_hi))
                        cross_gap = np.minimum(cross_gap, np.min(dist_iv, axis=1))
            else:
                cross_gap = np.min(np.abs(freq[:, None, :, None] - freq[None, sel, None, :]), axis=(1, 2, 3))
            A_gap = np.min(np.abs(A_hat[:, None] - A_hat[None, sel]), axis=1)
            eff_gap = np.minimum(full_gap, cross_gap)
            feasible = (~used) & (min_dist >= 0.30)
            if not np.any(feasible):
                break
            score = (np.minimum(eff_gap, 300e3) / 1e3 + 0.25 * np.minimum(A_gap, 300e3) / 1e3
                     + 5.0 * np.log10(np.maximum(np.abs(A_hat), 1.0) / 1e4)
                     - 0.05 * max_J + 20.0 * np.minimum(min_dist, 2.0))
            score = np.where(feasible, score, -np.inf)
            nxt = int(np.argmax(score))
            selected.append(nxt)
            used[nxt] = True
        if len(selected) != K:
            continue
        sel = np.array(selected, dtype=int)
        # Light measured objective; exact Vandermonde is evaluated once below.
        Jsel = np.abs(iso.dipolar_J(pos[sel], BDIR))
        iu = np.triu_indices(K, 1)
        light = float(np.min(full_gap[sel]) / 1e3 + 0.25 * np.min(np.diff(np.sort(A_hat[sel]))) / 1e3
                      - 0.05 * np.max(Jsel[iu]) + 20.0 * np.min(np.linalg.norm(pos[sel][:, None] - pos[sel][None], axis=2)[iu]))
        if best is None or light > best[0]:
            best = (light, sel)
    if best is None:
        raise RuntimeError("Adaptive selector could not complete K")
    return best[1]


def spectator_metrics(cloud_idx, selected_local, A_true_cloud):
    sel = np.array(selected_local, dtype=int)
    spec = np.array([i for i in range(len(cloud_idx)) if i not in set(sel.tolist())], dtype=int)
    if len(spec) == 0:
        return dict(max_selected_spectator_J_Hz=0.0, selected_spectator_NN_pairs=0,
                    selected_with_NN_spectator=0, D0_leakage_proxy=0.0, D0_leakage_proxy_max=0.0)
    pos_s = iso.SITES[np.array(cloud_idx)[sel]]
    pos_x = iso.SITES[np.array(cloud_idx)[spec]]
    dvec = pos_s[:, None, :] - pos_x[None, :, :]
    dist = np.linalg.norm(dvec, axis=2)
    cos = (dvec @ BDIR) / dist
    J = np.abs(iso.D_NN * (1 - 3 * cos**2) / dist**3)
    detuning = np.maximum(np.abs(A_true_cloud[sel][:, None] - A_true_cloud[spec][None, :]) / 2.0, 1.0)
    leak_terms = (J / detuning) ** 2
    return dict(
        max_selected_spectator_J_Hz=float(np.max(J)),
        selected_spectator_NN_pairs=int(np.sum(dist < 0.24)),
        selected_with_NN_spectator=int(np.sum(np.any(dist < 0.24, axis=1))),
        D0_leakage_proxy=float(np.sum(leak_terms)), D0_leakage_proxy_max=float(np.max(np.sum(leak_terms, axis=1))),
    )


def evaluate_selection(cloud_idx, selected_local, A_true_cloud, extra_idx=()):
    cloud_idx = np.array(cloud_idx, dtype=int)
    sel = np.array(selected_local, dtype=int)
    spec_local = np.array([i for i in range(len(cloud_idx)) if i not in set(sel.tolist())], dtype=int)
    extra_idx = np.array(extra_idx, dtype=int)
    extra_A = list(A_true_cloud[spec_local]) + list(A_ALL[extra_idx])
    m = rob.custom_metrics(iso.SITES[cloud_idx[sel]], A_true_cloud[sel], BDIR, np.array(extra_A))
    out = rob.compact(m)
    out.update(spectator_metrics(cloud_idx, sel, A_true_cloud))
    out["selected_global_indices"] = [int(cloud_idx[i]) for i in sel]
    out["selected_local_indices"] = [int(x) for x in sel]
    return out


def summarize(rows, K=8):
    gaps = np.array([x["min_transition_gap_Hz"] for x in rows], dtype=float)
    return dict(
        realizations=int(len(rows)), fraction_all30=float(np.mean([x["all30"] for x in rows])),
        fraction_all10=float(np.mean([x["all10"] for x in rows])),
        median_min_gap_Hz=float(np.median(gaps)), p10_min_gap_Hz=float(np.percentile(gaps, 10)),
        median_retained_30=float(np.median([x["retained_30kHz"] for x in rows])),
        median_retained_10=float(np.median([x["retained_10kHz"] for x in rows])),
        fraction_at_least_Kminus1_30=float(np.mean([x["retained_30kHz"] >= K - 1 for x in rows])),
        median_max_selected_J_Hz=float(np.median([x["max_abs_J_Hz"] for x in rows])),
        fraction_selected_NN_pair=float(np.mean([x["nn_pairs"] > 0 for x in rows])),
        fraction_any_selected_spectator_NN=float(np.mean([x["selected_spectator_NN_pairs"] > 0 for x in rows])),
        median_max_selected_spectator_J_Hz=float(np.median([x["max_selected_spectator_J_Hz"] for x in rows])),
        median_D0_leakage_proxy=float(np.median([x["D0_leakage_proxy"] for x in rows])),
        fraction_full_vandermonde=float(np.mean([x["vandermonde_rank"] == K for x in rows])),
        min_gap_samples_Hz=[float(x) for x in gaps],
    )


def main():
    t0 = time.time()
    out = dict(exp="44A", date="2026-10-19", registered="predictions_exp44.json",
               intended_targets=[int(x) for x in INTENDED], scenarios={})

    targeted = {}
    stored_m64_s050 = []
    for M in (16, 32, 64, 128):
        for sigma in (0.25, 0.50, 1.00):
            rng = np.random.default_rng(44100 + M * 10 + int(sigma * 100))
            rows = []
            for rep in range(100):
                cloud = rob.gaussian_snap(INTENDED[:M], sigma, rng)
                A = A_ALL[cloud]
                sel = selector(cloud, A, starts=12, seed=int(rng.integers(0, 10_000_000)))
                ev = evaluate_selection(cloud, sel, A)
                rows.append(ev)
                if M == 64 and sigma == 0.50:
                    stored_m64_s050.append(dict(realization=int(rep), cloud_global_indices=[int(x) for x in cloud],
                                                selected_local_indices=[int(x) for x in sel], metrics=ev))
            key = f"M{M}_sigma{sigma:.2f}"
            targeted[key] = summarize(rows, 8)
            print("TARGETED", key, targeted[key]["fraction_all30"], targeted[key]["median_min_gap_Hz"], flush=True)
    out["scenarios"]["targeted"] = targeted
    out["targeted_M64_sigma050_realizations"] = stored_m64_s050

    uniform = {}
    for M in (16, 64, 128):
        rng = np.random.default_rng(44200 + M)
        rows = []
        for _ in range(100):
            cloud = np.array(rng.choice(CANDIDATES, size=M, replace=False), dtype=int)
            A = A_ALL[cloud]
            sel = selector(cloud, A, starts=12, seed=int(rng.integers(0, 10_000_000)))
            rows.append(evaluate_selection(cloud, sel, A))
        key = f"M{M}"
        uniform[key] = summarize(rows, 8)
        print("UNIFORM", key, uniform[key]["fraction_all30"], uniform[key]["median_min_gap_Hz"], flush=True)
    out["scenarios"]["uniform"] = uniform

    natural_rows = []
    natural_addressable = []
    rng = np.random.default_rng(44300)
    for _ in range(20):
        cloud = np.where(rng.random(len(iso.SITES)) < 0.04685)[0]
        A = A_ALL[cloud]
        gaps = iso.register_gaps(A, A)
        natural_addressable.append(int(np.sum(gaps >= 30e3)))
        sel = selector(cloud, A, starts=5, seed=int(rng.integers(0, 10_000_000)))
        natural_rows.append(evaluate_selection(cloud, sel, A))
    out["scenarios"]["natural"] = summarize(natural_rows, 8)
    out["natural_addressable_counts_30kHz"] = natural_addressable
    print("NATURAL", out["scenarios"]["natural"], "addressable median", float(np.median(natural_addressable)), flush=True)

    residual_scenarios = {}
    all_idx = np.arange(len(iso.SITES))
    for ppm in (50, 200):
        rng = np.random.default_rng(44400 + ppm)
        rows = []
        for _ in range(100):
            cloud = rob.gaussian_snap(INTENDED[:64], 0.50, rng)
            remaining = np.array([i for i in all_idx if i not in set(cloud.tolist())], dtype=int)
            extra = remaining[rng.random(len(remaining)) < ppm * 1e-6]
            A = A_ALL[cloud]
            extra_freqs = np.array([x for a in A_ALL[extra] for x in (abs(NU + a / 2), abs(NU - a / 2))])
            sel = selector(cloud, A, starts=12, seed=int(rng.integers(0, 10_000_000)), extra_freqs=extra_freqs)
            rows.append(evaluate_selection(cloud, sel, A, extra_idx=extra))
        residual_scenarios[f"{ppm}ppm"] = summarize(rows, 8)
        print("RESIDUAL", ppm, residual_scenarios[f"{ppm}ppm"]["fraction_all30"], flush=True)
    out["scenarios"]["targeted_M64_residual"] = residual_scenarios

    measurement = {}
    for sigma_meas in (0.0, 0.05, 0.10, 0.25):
        rng = np.random.default_rng(44500 + int(sigma_meas * 100))
        rows_nom, rows_rob = [], []
        for _ in range(100):
            cloud = rob.gaussian_snap(INTENDED[:64], 0.50, rng)
            A_true = A_ALL[cloud]
            A_hat = A_true if sigma_meas == 0 else A_true * np.exp(rng.normal(0.0, sigma_meas, size=len(A_true)))
            sel_nom = selector(cloud, A_hat, robust=False, starts=10, seed=int(rng.integers(0, 10_000_000)))
            sel_rob = selector(cloud, A_hat, robust=True, starts=10, seed=int(rng.integers(0, 10_000_000)))
            rows_nom.append(evaluate_selection(cloud, sel_nom, A_true))
            rows_rob.append(evaluate_selection(cloud, sel_rob, A_true))
        key = f"sigma_meas{sigma_meas:.2f}"
        measurement[key] = dict(nominal=summarize(rows_nom, 8), robust=summarize(rows_rob, 8))
        print("MEASURE", key, measurement[key]["nominal"]["fraction_all30"], measurement[key]["robust"]["fraction_all30"], flush=True)
    out["measurement_noise_targeted_M64_sigma050"] = measurement
    out["runtime_s"] = round(time.time() - t0, 1)
    dst = ROOT / "results" / "exp44" / "adaptive44.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("WROTE", dst, "runtime", out["runtime_s"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

