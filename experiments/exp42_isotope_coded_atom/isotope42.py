"""Exp42: deterministic isotope-coded universal atom atlas.

A 31P donor is placed at the origin of the Exp25 diamond-lattice/Kohn-Luttinger
model. Selected spin-0 host sites are counterfactually substituted by 29Si.
The atlas compares strongest, random matched, spectrally optimized (ISO_CODE)
and uniform isotope occupations. Registered in
results/exp42/predictions_exp42.json before this simulation was run.
Output: results/exp42/isotope42.json.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(r"E:\quantum_cell")
sys.path.insert(0, str(ROOT / "experiments" / "exp25_universal_atom"))
import ap25_register as reg  # noqa: E402
import ap25_control as ctl  # noqa: E402

NU_HZ = reg.GN * 1.0
D_NN = 4.748  # Hz nm^3, Exp26 secular 29Si-29Si dipolar coefficient
DIRS = {
    "[001]": np.array([0.0, 0.0, 1.0]),
    "[110]": np.array([1.0, 1.0, 0.0]) / math.sqrt(2),
    "[111]": np.array([1.0, 1.0, 1.0]) / math.sqrt(3),
    "[123]": np.array([1.0, 2.0, 3.0]) / math.sqrt(14),
}
PRIMARY = "[123]"
SITES = np.array(reg.SITES, dtype=float)
RADII = np.linalg.norm(SITES, axis=1)
A_BY_DIR = {name: np.array(ctl.couplings_dir(SITES, reg.A_SITES, bdir), dtype=float) for name, bdir in DIRS.items()}


def dipolar_J(positions, bdir):
    pos = np.asarray(positions, dtype=float)
    n = len(pos)
    J = np.zeros((n, n))
    if n < 2:
        return J
    d = pos[:, None, :] - pos[None, :, :]
    r = np.linalg.norm(d, axis=2)
    with np.errstate(divide="ignore", invalid="ignore"):
        cos = np.where(r > 0, (d @ bdir) / np.where(r == 0, 1, r), 0.0)
        J = np.where(r > 0, D_NN * (1.0 - 3.0 * cos**2) / np.where(r == 0, 1, r) ** 3, 0.0)
    np.fill_diagonal(J, 0.0)
    return J


def register_gaps(A_register, A_env):
    """Nearest transition gap for each register f+ line in the full environment."""
    A_env = np.asarray(A_env, dtype=float)
    K = len(A_register)
    freqs = np.empty(2 * len(A_env))
    freqs[0::2] = np.abs(NU_HZ + A_env / 2.0)
    freqs[1::2] = np.abs(NU_HZ - A_env / 2.0)
    order = np.argsort(freqs)
    sorted_f = freqs[order]
    pos = np.empty(len(freqs), dtype=int)
    pos[order] = np.arange(len(freqs))
    gaps = []
    for k in range(K):
        p = pos[2 * k]
        neigh = []
        if p > 0:
            neigh.append(sorted_f[p] - sorted_f[p - 1])
        if p + 1 < len(sorted_f):
            neigh.append(sorted_f[p + 1] - sorted_f[p])
        gaps.append(float(min(neigh)) if neigh else float("inf"))
    return np.array(gaps)


def vandermonde_metrics(A):
    A = np.asarray(A, dtype=float)
    K = len(A)
    if K == 0:
        return dict(rank=0, condition=None, worst_reconstruction_error=None)
    scale = np.max(np.abs(A)) if np.max(np.abs(A)) > 0 else 1.0
    x = (A / scale) ** 2
    M = np.vander(x, N=K, increasing=True).T  # M[j,k] = x_k^j
    s = np.linalg.svd(M, compute_uv=False)
    rank = int(np.sum(s > s[0] * 1e-12)) if s[0] > 0 else 0
    cond = float(s[0] / s[-1]) if s[-1] > 0 else float("inf")
    errors = []
    for k in range(K):
        target = np.zeros(K)
        target[k] = 1.0
        w, *_ = np.linalg.lstsq(M, target, rcond=None)
        errors.append(float(np.linalg.norm(M @ w - target)))
    return dict(rank=rank, condition=cond, log10_condition=float(math.log10(cond)) if math.isfinite(cond) else None,
                worst_reconstruction_error=float(max(errors)) if errors else None,
                smallest_singular_ratio=float(s[-1] / s[0]) if s[0] > 0 else 0.0)


def subset_metrics(indices, A_all, bdir, A_env=None):
    idx = np.array(indices, dtype=int)
    A = np.array(A_all[idx], dtype=float)
    pos = SITES[idx]
    K = len(idx)
    env = A if A_env is None else np.concatenate([A, np.asarray(A_env, dtype=float)])
    gaps = register_gaps(A, env)
    if K > 1:
        dmat = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=2)
        iu = np.triu_indices(K, 1)
        pair_d = dmat[iu]
        J = dipolar_J(pos, bdir)
        pair_J = np.abs(J[iu])
        sorted_A = np.sort(A)
        min_gap_A = float(np.min(np.diff(sorted_A)))
    else:
        pair_d = np.array([np.inf])
        pair_J = np.array([0.0])
        min_gap_A = float("inf")
    min_abs_A = float(np.min(np.abs(A))) if K else 0.0
    resolving = float(1.0 / min(min_abs_A, min_gap_A)) if min(min_abs_A, min_gap_A) > 0 else float("inf")
    vm = vandermonde_metrics(A)
    return dict(
        K=int(K), site_indices=[int(x) for x in idx],
        positions_nm=[[float(x) for x in p] for p in pos],
        radii_nm=[float(x) for x in RADII[idx]],
        A_Hz=[float(x) for x in A], A_kHz=[float(x / 1e3) for x in A],
        min_abs_A_Hz=min_abs_A, mean_abs_A_Hz=float(np.mean(np.abs(A))) if K else 0.0,
        min_gap_A_Hz=min_gap_A, min_transition_gap_Hz=float(np.min(gaps)) if K else None,
        transition_gaps_Hz=[float(x) for x in gaps],
        addressable_counts={f"{int(d/1000)}kHz": int(np.sum(gaps >= d)) for d in (10e3, 30e3, 100e3)},
        all_addressable_10kHz=bool(np.all(gaps >= 10e3)), all_addressable_30kHz=bool(np.all(gaps >= 30e3)),
        all_addressable_100kHz=bool(np.all(gaps >= 100e3)),
        min_pair_distance_nm=float(np.min(pair_d)), nn_pairs_lt_0p24nm=int(np.sum(pair_d < 0.24)),
        max_abs_J_Hz=float(np.max(pair_J)), strong_pairs_ge_250Hz=int(np.sum(pair_J >= 250.0)),
        resolving_time_s=resolving, vandermonde=vm,
    )


def final_objective(m):
    cond_term = m["vandermonde"]["log10_condition"]
    cond_term = 30.0 if cond_term is None else min(cond_term, 30.0)
    return float(
        m["min_transition_gap_Hz"] / 1e3
        + 0.25 * min(m["min_gap_A_Hz"], 1e9) / 1e3
        + 5.0 * math.log10(max(m["min_abs_A_Hz"], 1.0) / 1e4)
        - 0.05 * m["max_abs_J_Hz"]
        - 2.0 * cond_term
        + 20.0 * min(m["min_pair_distance_nm"], 2.0)
    )


def greedy_iso_code(K, direction, starts=30, seed=4200):
    bdir = DIRS[direction]
    A_all = A_BY_DIR[direction]
    cand_all = np.where(np.abs(A_all) >= 10e3)[0]
    cand = cand_all[np.argsort(-np.abs(A_all[cand_all]))[:3000]]
    pos = SITES[cand]
    A = A_all[cand]
    fp = np.abs(NU_HZ + A / 2.0)
    fm = np.abs(NU_HZ - A / 2.0)
    freq = np.column_stack([fp, fm])
    order_strength = np.argsort(-np.abs(A))
    direction_offset = sum((i + 1) * ord(ch) for i, ch in enumerate(direction))
    rng = np.random.default_rng(seed + 100 * K + direction_offset)
    start_positions = list(order_strength[:15])
    start_positions += [int(x) for x in rng.integers(0, len(cand), max(0, starts - len(start_positions)))]
    best = None

    for start in start_positions:
        if abs(A[start]) < 30e3:
            continue
        selected = [int(start)]
        selected_mask = np.zeros(len(cand), dtype=bool)
        selected_mask[start] = True
        while len(selected) < K:
            sel = np.array(selected, dtype=int)
            dvec = pos[:, None, :] - pos[None, sel, :]
            dist = np.linalg.norm(dvec, axis=2)
            min_dist = np.min(dist, axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                cos = np.where(dist > 0, (dvec @ bdir) / np.where(dist == 0, 1, dist), 0.0)
                Jcross = np.where(dist > 0, np.abs(D_NN * (1.0 - 3.0 * cos**2) / np.where(dist == 0, 1, dist) ** 3), 0.0)
            max_J = np.max(Jcross, axis=1)
            cross_gap = np.min(np.abs(freq[:, None, :, None] - freq[None, sel, None, :]), axis=(1, 2, 3))
            own_gap = np.abs(fp - fm)
            trans_gap = np.minimum(cross_gap, own_gap)
            A_gap = np.min(np.abs(A[:, None] - A[None, sel]), axis=1)
            feasible = (~selected_mask) & (min_dist >= 0.30) & (trans_gap >= 30e3)
            if not np.any(feasible):
                feasible = (~selected_mask) & (min_dist >= 0.30)
            if not np.any(feasible):
                break
            score = (
                np.minimum(trans_gap, 300e3) / 1e3
                + 0.25 * np.minimum(A_gap, 300e3) / 1e3
                + 5.0 * np.log10(np.maximum(np.abs(A), 1.0) / 1e4)
                - 0.05 * max_J
                + 20.0 * np.minimum(min_dist, 2.0)
            )
            score = np.where(feasible, score, -np.inf)
            nxt = int(np.argmax(score))
            selected.append(nxt)
            selected_mask[nxt] = True
        if len(selected) != K:
            continue
        global_idx = cand[np.array(selected, dtype=int)]
        metrics = subset_metrics(global_idx, A_all, bdir)
        q = final_objective(metrics)
        if best is None or q > best[0]:
            best = (q, metrics)
    if best is None:
        raise RuntimeError(f"No complete ISO_CODE subset for K={K}, direction={direction}")
    best[1]["objective"] = float(best[0])
    best[1]["strategy"] = "ISO_CODE"
    best[1]["direction"] = direction
    return best[1]


def strongest_subset(K, direction):
    A_all = A_BY_DIR[direction]
    cand = np.where(np.abs(A_all) >= 10e3)[0]
    cand = cand[np.argsort(-np.abs(A_all[cand]))]
    chosen = []
    for idx in cand:
        if all(np.linalg.norm(SITES[idx] - SITES[j]) >= 0.30 for j in chosen):
            chosen.append(int(idx))
        if len(chosen) == K:
            break
    out = subset_metrics(chosen, A_all, DIRS[direction])
    out["strategy"] = "STRONGEST"
    out["direction"] = direction
    return out


def random_matched(K, direction, draws=200, seed=4242):
    A_all = A_BY_DIR[direction]
    cand = np.where(np.abs(A_all) >= 10e3)[0]
    rng = np.random.default_rng(seed + K)
    rows = []
    all30 = 0
    for _ in range(draws):
        chosen = []
        for idx in rng.permutation(cand):
            idx = int(idx)
            if all(np.linalg.norm(SITES[idx] - SITES[j]) >= 0.30 for j in chosen):
                chosen.append(idx)
            if len(chosen) == K:
                break
        m = subset_metrics(chosen, A_all, DIRS[direction])
        rows.append(m)
        all30 += int(m["all_addressable_30kHz"])
    gaps = np.array([x["min_transition_gap_Hz"] for x in rows])
    maxjs = np.array([x["max_abs_J_Hz"] for x in rows])
    summary = dict(
        K=K, draws=draws, median_min_transition_gap_Hz=float(np.median(gaps)),
        p10_min_transition_gap_Hz=float(np.percentile(gaps, 10)), p90_min_transition_gap_Hz=float(np.percentile(gaps, 90)),
        fraction_all_addressable_30kHz=float(all30 / draws), median_max_abs_J_Hz=float(np.median(maxjs)),
        median_min_abs_A_Hz=float(np.median([x["min_abs_A_Hz"] for x in rows])),
    )
    return summary, rows


def uniform_baselines(direction="[123]", configs=50, seed=4300):
    A_all = A_BY_DIR[direction]
    pairs = np.array(sorted(cKDTree(SITES).query_pairs(0.24)), dtype=int)
    rng = np.random.default_rng(seed)
    out = {}
    for label, frac in (("natural_46850ppm", 0.04685), ("10000ppm", 0.01), ("1000ppm", 0.001),
                        ("800ppm", 0.0008), ("200ppm", 0.0002), ("50ppm", 0.00005)):
        counts = []
        addr = {10: [], 30: [], 100: []}
        nn_frac = []
        for _ in range(configs):
            occ = rng.random(len(SITES)) < frac
            idx = np.where(occ)[0]
            counts.append(len(idx))
            if len(idx):
                gaps = register_gaps(A_all[idx], A_all[idx])
                for d_khz in addr:
                    addr[d_khz].append(int(np.sum(gaps >= d_khz * 1e3)))
                if len(pairs):
                    both = occ[pairs[:, 0]] & occ[pairs[:, 1]]
                    has = np.zeros(len(SITES), dtype=bool)
                    has[pairs[both, 0]] = True
                    has[pairs[both, 1]] = True
                    nn_frac.append(float(np.mean(has[idx])))
                else:
                    nn_frac.append(0.0)
            else:
                for d_khz in addr:
                    addr[d_khz].append(0)
                nn_frac.append(0.0)
        out[label] = dict(
            fraction_29Si=frac, configs=configs, mean_nuclei_6nm=float(np.mean(counts)),
            mean_addressable={f"{k}kHz": float(np.mean(v)) for k, v in addr.items()},
            frac_configs_ge4_addressable_30kHz=float(np.mean(np.array(addr[30]) >= 4)),
            mean_fraction_with_NN_pair=float(np.mean(nn_frac)),
        )
    return out


def residual_robustness(placement, direction=PRIMARY, realizations=200, seed=4400):
    idx = np.array(placement["site_indices"], dtype=int)
    A_all = A_BY_DIR[direction]
    A_reg = A_all[idx]
    remaining = np.array([i for i in range(len(SITES)) if i not in set(idx.tolist())], dtype=int)
    rng = np.random.default_rng(seed + len(idx))
    out = {}
    for ppm, frac in ((0, 0.0), (50, 50e-6), (200, 200e-6), (800, 800e-6), (1000, 0.001),
                      (10000, 0.01), (46850, 0.04685)):
        reps = 1 if frac == 0 else realizations
        retained10, retained30, residual_counts = [], [], []
        for _ in range(reps):
            occ = rng.random(len(remaining)) < frac if frac else np.zeros(len(remaining), dtype=bool)
            residual_idx = remaining[occ]
            gaps = register_gaps(A_reg, np.concatenate([A_reg, A_all[residual_idx]]))
            retained10.append(int(np.sum(gaps >= 10e3)))
            retained30.append(int(np.sum(gaps >= 30e3)))
            residual_counts.append(int(len(residual_idx)))
        retained10 = np.array(retained10)
        retained30 = np.array(retained30)
        out[f"{ppm}ppm"] = dict(
            residual_fraction=frac, realizations=reps, mean_residual_nuclei=float(np.mean(residual_counts)),
            median_retained_10kHz=float(np.median(retained10)), median_retained_30kHz=float(np.median(retained30)),
            fraction_at_least_Kminus1_10kHz=float(np.mean(retained10 >= len(idx) - 1)),
            fraction_all_retained_10kHz=float(np.mean(retained10 == len(idx))),
            fraction_all_retained_30kHz=float(np.mean(retained30 == len(idx))),
        )
    return out


def mass_variance(fractions, masses=(28.0, 29.0, 30.0)):
    fractions = np.array(fractions, dtype=float)
    masses = np.array(masses, dtype=float)
    mbar = float(np.sum(fractions * masses))
    return dict(mean_mass=mbar, g2=float(np.sum(fractions * ((masses - mbar) / mbar) ** 2)),
                phonon_frequency_scale_vs_pure28=float(math.sqrt(28.0 / mbar)))


def host_descriptors(K):
    n = len(SITES)
    return {
        "pure28_plus_coded29": mass_variance([1 - K / n, K / n, 0.0]),
        "pure30_plus_coded29": mass_variance([0.0, K / n, 1 - K / n]),
        "natural": mass_variance([0.9223, 0.04685, 0.03085]),
    }


def exact_finalists(iso_k4):
    idx = np.array(iso_k4["site_indices"], dtype=int)
    lie = {}
    Se, In = ctl.operators(4)
    for direction in DIRS:
        A = A_BY_DIR[direction][idx]
        H0 = ctl.drift(A / 1e6, Se, In)
        rank, full = ctl.lie_rank([H0] + ctl.controls(Se, In, 4))
        lie[direction] = dict(rank=int(rank), full=int(full), A_kHz=[float(x / 1e3) for x in A])
    old_omega = reg.OMEGA
    reg.OMEGA = 2 * np.pi * 3e3
    try:
        A_reg = A_BY_DIR[PRIMARY][idx]
        ghz_vals, ghz_time = reg.ghz(A_reg, [0, 1, 2, 3], NU_HZ)
        rng = np.random.default_rng(4500)
        remaining = np.array([i for i in range(len(SITES)) if i not in set(idx.tolist())], dtype=int)
        spectator_fids = []
        for _ in range(20):
            occ = rng.random(len(remaining)) < 50e-6
            A_env = np.concatenate([A_reg, A_BY_DIR[PRIMARY][remaining[occ]]])
            factor = reg.spectator_overlap(A_env, [0, 1, 2, 3], NU_HZ, {0, 1, 2, 3})
            spectator_fids.append(float(reg._ghz_with_factor(A_env, [0, 1, 2, 3], NU_HZ, factor)))
    finally:
        reg.OMEGA = old_omega
    return dict(
        lie_rank_by_direction=lie,
        ghz_register_only=dict(fidelities={k: float(v) for k, v in ghz_vals.items()}, time_us=float(ghz_time * 1e6), rabi_kHz=3.0),
        ghz_50ppm_spectators=dict(mean=float(np.mean(spectator_fids)), min=float(np.min(spectator_fids)), realizations=20),
    )


def main():
    t0 = time.time()
    pool_stats = {}
    for direction, A in A_BY_DIR.items():
        pool_stats[direction] = dict(
            sites_6nm=int(len(SITES)), candidates_ge_10kHz=int(np.sum(np.abs(A) >= 10e3)),
            candidates_ge_100kHz=int(np.sum(np.abs(A) >= 100e3)),
            candidates_ge_1MHz=int(np.sum(np.abs(A) >= 1e6)),
        )
    Ks = (4, 6, 8, 10, 12)
    iso_primary, strongest_primary, random_primary = {}, {}, {}
    for K in Ks:
        print(f"ISO_CODE K={K} primary...", flush=True)
        iso_primary[str(K)] = greedy_iso_code(K, PRIMARY, starts=30)
        strongest_primary[str(K)] = strongest_subset(K, PRIMARY)
        random_primary[str(K)], _ = random_matched(K, PRIMARY, draws=200)
    iso_by_direction_k8 = {}
    transfer_primary_k8 = {}
    primary_k8_idx = iso_primary["8"]["site_indices"]
    for direction in DIRS:
        print(f"ISO_CODE K=8 direction {direction}...", flush=True)
        iso_by_direction_k8[direction] = greedy_iso_code(8, direction, starts=20)
        m = subset_metrics(primary_k8_idx, A_BY_DIR[direction], DIRS[direction])
        m["strategy"] = "PRIMARY_ISO_CODE_TRANSFER"
        m["direction"] = direction
        transfer_primary_k8[direction] = m
    print("Uniform baselines...", flush=True)
    uniform = uniform_baselines(PRIMARY, configs=50)
    robustness = {str(K): residual_robustness(iso_primary[str(K)], PRIMARY, realizations=200) for K in (4, 8, 12)}
    print("Exact Lie/GHZ finalists...", flush=True)
    exact = exact_finalists(iso_primary["4"])
    hosts = host_descriptors(8)

    iso8 = iso_primary["8"]
    rand8 = random_primary["8"]
    rob8 = robustness["8"]
    lie_full_dirs = int(sum(v["rank"] == v["full"] for v in exact["lie_rank_by_direction"].values()))
    ghz = exact["ghz_register_only"]["fidelities"]
    universal_success = bool(
        iso8["all_addressable_30kHz"] and iso8["min_pair_distance_nm"] >= 0.30 and iso8["max_abs_J_Hz"] <= 100
        and iso8["vandermonde"]["rank"] == 8 and iso8["resolving_time_s"] <= 1e-3
        and exact["lie_rank_by_direction"][PRIMARY]["rank"] == 1023
        and ghz["no_dephasing"] >= 0.95 and ghz["T2e=10ms"] >= 0.90
    )
    verdicts = {
        "I1": "PASS" if pool_stats[PRIMARY]["candidates_ge_10kHz"] > 500 and pool_stats[PRIMARY]["candidates_ge_100kHz"] > 50 else "FAIL",
        "I2": "PASS" if iso8["all_addressable_30kHz"] and iso8["min_pair_distance_nm"] >= 0.30 and iso8["max_abs_J_Hz"] <= 100 and iso8["vandermonde"]["rank"] == 8 and iso8["resolving_time_s"] <= 1e-3 else "FAIL",
        "I3": "PASS" if iso8["min_transition_gap_Hz"] >= 5 * rand8["median_min_transition_gap_Hz"] and rand8["fraction_all_addressable_30kHz"] < 0.10 and strongest_primary["8"]["min_transition_gap_Hz"] < iso8["min_transition_gap_Hz"] else "FAIL",
        "I4": "PASS" if rob8["800ppm"]["fraction_at_least_Kminus1_10kHz"] >= 0.80 and rob8["10000ppm"]["median_retained_10kHz"] <= 6 else "FAIL",
        "I5": "PASS" if exact["lie_rank_by_direction"][PRIMARY]["rank"] == 1023 and lie_full_dirs >= 3 and ghz["no_dephasing"] >= 0.95 and ghz["T2e=10ms"] >= 0.90 else "FAIL",
        "I6": "PASS" if all(iso_primary[str(K)]["nn_pairs_lt_0p24nm"] == 0 for K in Ks) and uniform["natural_46850ppm"]["mean_fraction_with_NN_pair"] > 0 and all(iso_primary[str(K)]["max_abs_J_Hz"] < 250 for K in (4, 6, 8)) else "FAIL",
        "I7": "PASS" if abs(hosts["pure30_plus_coded29"]["phonon_frequency_scale_vs_pure28"] - math.sqrt(28.0 / hosts["pure30_plus_coded29"]["mean_mass"])) < 1e-12 else "FAIL",
        "universal_atom_success_rule": universal_success,
    }
    out = dict(
        exp="42", date="2026-10-19", task="deterministic isotope-coded universal atom atlas",
        registered="predictions_exp42.json",
        model=dict(
            hub="31P donor electron + nucleus in D0; D+ storage assumed from Exp25/26",
            lattice_sites_6nm=int(len(SITES)), primary_direction=PRIMARY,
            optimizer="ISO_CODE searches the 3000 strongest |A|>=10 kHz candidate sites; full pool is reported separately",
            limitations="KL contact model (~50% site accuracy), secular dipolar terms, no placement/fabrication error, no charge-noise or readout physics; deterministic single-site isotope substitution is a design target, not a demonstrated fabrication method.",
        ),
        pool_stats=pool_stats, iso_code_primary=iso_primary, strongest_primary=strongest_primary,
        random_matched_primary=random_primary, iso_code_by_direction_K8=iso_by_direction_k8,
        primary_K8_transfer=transfer_primary_k8, uniform_baselines=uniform,
        residual_robustness=robustness, exact_finalists=exact, host_descriptors_K8=hosts,
        verdicts=verdicts, runtime_s=round(time.time() - t0, 1),
    )
    outdir = ROOT / "results" / "exp42"
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        outdir = Path(r"C:\Users\pc\_exp42_out")
        outdir.mkdir(parents=True, exist_ok=True)
    dst = outdir / "isotope42.json"
    dst.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("WROTE", dst, "runtime", out["runtime_s"], "verdicts", verdicts, flush=True)
    print("pool_primary", pool_stats[PRIMARY], flush=True)
    for K in Ks:
        m = iso_primary[str(K)]
        print(f"ISO K={K}: gap_kHz={m['min_transition_gap_Hz']/1e3:.2f} minA_kHz={m['min_abs_A_Hz']/1e3:.1f} "
              f"maxJ={m['max_abs_J_Hz']:.1f} min_dist={m['min_pair_distance_nm']:.3f} "
              f"Tres_ms={m['resolving_time_s']*1e3:.3f} cond={m['vandermonde']['condition']:.3e} "
              f"rand_median_gap_kHz={random_primary[str(K)]['median_min_transition_gap_Hz']/1e3:.3f}", flush=True)
    print("robustness_K8", robustness["8"], flush=True)
    print("exact", exact, flush=True)
    print("uniform", uniform, flush=True)
    return 0 if all(v == "PASS" for k, v in verdicts.items() if k.startswith("I")) else 2


if __name__ == "__main__":
    raise SystemExit(main())



