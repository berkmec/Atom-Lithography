"""Exp48 pulse-aware exact/greedy selection on fresh clouds."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, r"E:\quantum_cell\experiments\exp42_isotope_coded_atom")
sys.path.insert(0, r"E:\quantum_cell\experiments\exp43_robustness_control")
sys.path.insert(0, r"E:\quantum_cell\experiments\exp44_adaptive_isotope_code")
import isotope42 as iso
import robustness43 as rob
import adaptive44 as ad

ROOT = Path(r"E:\quantum_cell")
OUT = ROOT / "results" / "exp48"
OUT.mkdir(parents=True, exist_ok=True)
A_ALL = iso.A_BY_DIR[iso.PRIMARY]
BDIR = iso.DIRS[iso.PRIMARY]
NU = iso.NU_HZ
PULSE = json.loads((ROOT / "results" / "exp47" / "pulse47.json").read_text(encoding="utf-8"))
EXP45 = json.loads((ROOT / "results" / "exp45" / "spectral45.json").read_text(encoding="utf-8"))
OPS = [("GAUSS", 500), ("HANN", 500), ("GAUSS", 1000), ("HANN", 1000)]
DET_GRID = np.asarray(PULSE["detunings_hz"], dtype=float)
LOG_DET = np.log10(DET_GRID)
LOG_ENV = {(f, t): np.log10(np.maximum(np.asarray(PULSE["jitter_envelope"][f][str(t)], dtype=float), 1e-300))
           for f, t in OPS}


def seed48(sigma, real):
    return 49_000_000 + int(round(sigma * 1000)) * 10_000 + int(real)


def pulse_p(fam, tus, detuning_hz):
    x = np.log10(np.maximum(np.asarray(detuning_hz, dtype=float), 1.0))
    return 10.0 ** np.interp(x, LOG_DET, LOG_ENV[(fam, int(tus))])


def eligibility(cloud, avals, fam, tus):
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


def fallback_selector(cloud, avals, K=8):
    gaps = iso.register_gaps(avals, avals)
    order = list(np.argsort(-gaps))
    pos = iso.SITES[cloud]
    sel = []
    for dmin in (0.30, 0.24, 0.0):
        for i in order:
            if i in sel:
                continue
            if sel and np.min(np.linalg.norm(pos[sel] - pos[i], axis=1)) < dmin:
                continue
            sel.append(int(i))
            if len(sel) == K:
                return np.array(sel, dtype=int)
    return np.array(order[:K], dtype=int)


def select_safe(cloud, avals, seed):
    try:
        return ad.selector(cloud, avals, starts=12, seed=seed)
    except RuntimeError:
        return fallback_selector(cloud, avals)


def pair_masks(cloud):
    pos = iso.SITES[cloud]
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


def find_rank_clique(mask, need, chosen, adj, avals, priority):
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


def pulse_exact(eligible_idx, gaps, sum_flip, adj, avals):
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


def pulse_greedy(eligible_idx, gaps, sum_flip, cloud, avals, seed=4800, starts=12):
    eligible = [int(i) for i in eligible_idx]
    if len(eligible) < 8:
        return None
    rng = np.random.default_rng(seed)
    pos = iso.SITES[cloud]
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
                score = min(gaps[i], 100_000.0) / 1000.0 - 1000.0 * float(sum_flip[i]) \
                    - 0.05 * float(np.max(jmat[i, sel])) + 20.0 * float(np.min(dist[i, sel]))
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


def selection_record(cloud, sel, avals, gaps, max_flip, sum_flip):
    ev = ad.evaluate_selection(cloud, sel, avals)
    return dict(evaluation=ev, selected_local=[int(x) for x in sel],
                selected_global=[int(cloud[i]) for i in sel],
                min_gap_hz=float(np.min(gaps[sel])),
                worst_max_flip=float(np.max(max_flip[sel])),
                worst_sum_flip=float(np.max(sum_flip[sel])))


def main():
    t0 = time.time()
    designs = {
        "NOMINAL_M16": np.array(EXP45["intended_spectral_targets"]["16"]["global_indices"], dtype=int),
        "NOMINAL_M24": np.array(EXP45["intended_spectral_targets"]["24"]["global_indices"], dtype=int),
    }
    scenarios = [("NOMINAL_M16", 0.175), ("NOMINAL_M16", 0.25), ("NOMINAL_M16", 0.50),
                 ("NOMINAL_M24", 0.25)]
    results = {}
    first_finalists = {}
    timing = {"exact_GAUSS_500us_s": [], "greedy_GAUSS_500us_s": []}
    for name, sigma in scenarios:
        idx = designs[name]
        is_m16 = name.endswith("M16")
        stats = {}
        for fam, tus in OPS:
            stats[f"{fam}_{tus}us"] = dict(eligible_counts=[], baseline=0, exact=0, greedy=0,
                                           exact_min_gaps=[], exact_worst_sums=[])
        for real in range(200):
            rng = np.random.default_rng(seed48(sigma, real))
            cloud = rob.gaussian_snap(idx, sigma, rng)
            avals = A_ALL[cloud]
            gaps = iso.register_gaps(avals, avals)
            adj, _dist, _j = pair_masks(cloud)
            base_sel = select_safe(cloud, avals, seed=4900 + real)
            base_ev = ad.evaluate_selection(cloud, base_sel, avals)
            base_struct = bool(base_ev["min_pair_distance_nm"] >= 0.30
                               and base_ev["max_abs_J_Hz"] <= 100.0 and base_ev["vandermonde_rank"] == 8)
            for fam, tus in OPS:
                op = f"{fam}_{tus}us"
                eligible, max_flip, sum_flip = eligibility(cloud, avals, fam, tus)
                eidx = np.where(eligible)[0]
                st = stats[op]
                st["eligible_counts"].append(int(len(eidx)))
                if base_struct and bool(np.all(eligible[base_sel])):
                    st["baseline"] += 1
                exact_sel = None
                if is_m16:
                    t_start = time.perf_counter() if (name == "NOMINAL_M16" and sigma == 0.25 and op == "GAUSS_500us") else None
                    exact_sel = pulse_exact(eidx, gaps, sum_flip, adj, avals)
                    if t_start is not None:
                        timing["exact_GAUSS_500us_s"].append(time.perf_counter() - t_start)
                    if exact_sel is not None:
                        st["exact"] += 1
                        st["exact_min_gaps"].append(float(np.min(gaps[exact_sel])))
                        st["exact_worst_sums"].append(float(np.max(sum_flip[exact_sel])))
                        if name == "NOMINAL_M16" and sigma == 0.25 and op not in first_finalists:
                            first_finalists[op] = dict(
                                realization=int(real), cloud_global_indices=[int(x) for x in cloud],
                                **selection_record(cloud, exact_sel, avals, gaps, max_flip, sum_flip))
                t_start = time.perf_counter() if (name == "NOMINAL_M16" and sigma == 0.25 and op == "GAUSS_500us") else None
                greedy_sel = pulse_greedy(eidx, gaps, sum_flip, cloud, avals, seed=4950 + real)
                if t_start is not None:
                    timing["greedy_GAUSS_500us_s"].append(time.perf_counter() - t_start)
                if greedy_sel is not None:
                    st["greedy"] += 1
        scen = {}
        for op, st in stats.items():
            scen[op] = dict(
                eligible_median=float(np.median(st["eligible_counts"])),
                eligible_mean=float(np.mean(st["eligible_counts"])),
                eligible_counts=st["eligible_counts"],
                baseline_yield=float(st["baseline"] / 200),
                exact_yield=(float(st["exact"] / 200) if name.endswith("M16") else None),
                greedy_yield=float(st["greedy"] / 200),
                exact_success_min_gap_median_hz=(float(np.median(st["exact_min_gaps"])) if st["exact_min_gaps"] else None),
                exact_success_worst_sum_median=(float(np.median(st["exact_worst_sums"])) if st["exact_worst_sums"] else None),
            )
        results[f"{name}@sigma{sigma}"] = scen
        print(f"SELECT48 {name} sigma={sigma}: " +
              " ".join(f"{op} base={scen[op]['baseline_yield']:.3f} exact={scen[op]['exact_yield']} greedy={scen[op]['greedy_yield']:.3f} eligmed={scen[op]['eligible_median']:.0f}" for op in scen),
              flush=True)
    timing_summary = {k: dict(median_s=float(np.median(v)), mean_s=float(np.mean(v)), n=len(v))
                      for k, v in timing.items()}
    out = dict(experiment="exp48_pulse_select", seed_formula="49000000 + round(sigma*1000)*10000 + realization",
               results=results, first_exact_finalists_M16_sigma025=first_finalists,
               timing_M16_sigma025=timing_summary, elapsed_sec=float(time.time() - t0), no_lab_measurement=True)
    (OUT / "pulse_select48.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("TIMING", timing_summary)
    print("FINALISTS", list(first_finalists))
    print("PULSE_SELECT48_DONE", flush=True)


if __name__ == "__main__":
    main()
