"""
Exp143 (H161) — Master Runner: D3 Fourier-GRAPE M4 Bus CZ Gate (p_2q <= 0.45%)
+ Live Exp138 Edmonds Blossom MWPM Verification + Option-HPC 100 Gbps RoCEv2
RDMA Real-Time Decoder Wall & CAD/BOM v6.0 Hardware Spec (s9hpc_hardware_spec.json).

Outputs:
  - results/exp143_d3_grape_m4_and_hpc_decoder/exp143.json
  - results/exp143_d3_grape_m4_and_hpc_decoder/s9hpc_hardware_spec.json

Epistemic Tag: {Sayısal-Simülasyon} / {Model} / {Varsayım}.
no_lab_measurement = True, no_supplier_quotes = True.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Dict, List

import numpy as np

from experiments.exp137_echoed_m4_bus_gate.echo_bus_solver137 import (
    GAMMA_PHI_NUC_1PCT_KHZ,
    PAULI_16_NAMES,
    FlipFlopPairSpec,
    simulate_echoed_cz_cuda,
)
from experiments.exp137_echoed_m4_bus_gate.run_exp137 import build_exp131_best_of_6_pairs
from experiments.exp138_defective_surface_code_ft.rotated_surface_code138 import (
    build_rotated_surface_code,
    compile_ideal_circuit_dem,
    normalize_and_scale_pauli16,
    simulate_dem_mc,
)
from experiments.exp138_defective_surface_code_ft.run_exp138 import (
    combine_zx_results,
    compute_machine_scaling_table,
    eps_block_to_round,
    fit_exponential_suppression,
)
from experiments.exp143_d3_grape_m4_and_hpc_decoder.grape_m4_bus143 import (
    GrapeSlicePulse,
    optimize_grape_slice_multistart_cuda,
    simulate_grape_cz_cuda,
)
from experiments.exp143_d3_grape_m4_and_hpc_decoder.hpc_decoder143 import (
    analyze_option_hpc_decoder_wall,
    build_s9hpc_hardware_spec,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "exp143_d3_grape_m4_and_hpc_decoder"


def load_upstream_anchors() -> Dict[str, Any]:
    e136 = json.loads((REPO_ROOT / "results/exp136_tb_sp3d5s_hyperfine/exp136.json").read_text())
    e137 = json.loads((REPO_ROOT / "results/exp137_echoed_m4_bus_gate/exp137.json").read_text())
    e138 = json.loads((REPO_ROOT / "results/exp138_defective_surface_code_ft/exp138.json").read_text())
    e139 = json.loads((REPO_ROOT / "results/exp139_epi_cap_process_integration/exp139.json").read_text())
    e140 = json.loads((REPO_ROOT / "results/exp140_cryo_fpga_boed_mux_readout/exp140.json").read_text())
    e126 = json.loads((REPO_ROOT / "results/exp126_atom_cell_programming/exp126.json").read_text())

    prim136 = {r["abundance_pct"]: r for r in e136["stage6_isotope_stark_sweep"]["primary_TB_CP_HM5962"]}
    t2e_f15_alpha2_ms = float(prim136[1.5]["coherence"]["T2e_XY8_N64_alpha2_ms"])
    t2e_f15_alpha1_ms = float(prim136[1.5]["coherence"]["T2e_XY8_N64_alpha1_ms"])
    t2e_f15_hahn_ms = float(prim136[1.5]["coherence"]["T2e_hahn_ms"])
    # OBS-085/OBS-110 FIX: A 4-pulse bus gate has N=4 (NOT N=64!) under conservative alpha=1 (1/f) noise:
    # T2e_N4_alpha1 = T2e_hahn * sqrt(4) = 2 * T2e_hahn (~1.76 ms at f=1.5%), while idle memory uses alpha=1 N=64 (7.07 ms).
    t2e_f15_ms = t2e_f15_alpha1_ms
    t2e_f10_ms = float(prim136[1.0]["coherence"]["T2e_XY8_N64_alpha1_ms"])
    t2e_4pulse_alpha1_ms = t2e_f15_hahn_ms * math.sqrt(4.0)
    gamma_phi_echo_f15_khz = 1.0 / (math.pi * t2e_4pulse_alpha1_ms)  # Honest 4-pulse alpha=1 rate (~0.180 kHz, NOT N=64 0.0225 kHz!)

    s_eps_route_c = float(
        e139["charge_noise_and_exp137_bridge"]["routes"]["route_C_nominal_FG350C_Dit_1p5e10"]["S_eps_ueV_rtHz"]
    )
    p_meas_2us = 1.0 - float(e140["mux_readout_3kOhm_NbTiN"]["by_nmux"]["32"]["F_ro_at_2us"])
    cryo_max = int(e140["cryo_heat_budgets"]["m4_1024_hemt7p8mW"]["single_cryostat_max_cells"])
    cryo_nom = int(e140["cryo_heat_budgets"]["m4_1024_hemt7p8mW"]["n_cells"])
    t_cyc_fast_us = float(e140["cellisa_v35_syndrome_demo"]["summary"]["cycle_duration_us"])

    rx_list = e126["part1_f1_universal_gates"]["gates_summary"]["Rx_pi2"]
    p_1q = 1.0 - float(np.mean([g["nominal_fidelity_32d"] for g in rx_list]))

    exp138_d2_lam = float(e138["part2_scenarios"]["D2_v5_RotaC_P4_S0p25_fast_Q5e5"]["fit_per_round"]["Lambda"])
    exp138_d2_cryos_100L = int(e138["target_logical_error_rates"]["1e-9"]["cryostats_100L_unsplit_2887"])
    exp138_deff_f15_N6 = float(
        e138["part3_defective_superstabilizers"]["regimes"]["f1p5_Stark2MVm"]["by_N_cand"]["N6"]["by_d"]["d7"][
            "mean_d_eff_over_d"
        ]
    )

    return {
        "t2e_xy8_f15_ms": t2e_f15_ms,
        "t2e_xy8_f10_ms": t2e_f10_ms,
        "gamma_phi_nuc_cons_khz": float(GAMMA_PHI_NUC_1PCT_KHZ),
        "gamma_phi_nuc_echo_f15_khz": float(gamma_phi_echo_f15_khz),
        "s_eps_route_c_uev": s_eps_route_c,
        "p_meas_2us": p_meas_2us,
        "p_1q": p_1q,
        "cryo_max_cells": cryo_max,
        "cryo_nom_cells": cryo_nom,
        "t_cyc_fast_us": t_cyc_fast_us,
        "exp138_d2_lambda": exp138_d2_lam,
        "exp138_d2_cryos_100L_1e9": exp138_d2_cryos_100L,
        "exp138_deff_ratio_f15_N6": exp138_deff_f15_N6,
    }


def _aggregate_pair_channels(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate exact 16-Pauli channels and CPTP audits across an ensemble of pairs."""
    n = len(results)
    pauli_16 = {name: float(np.mean([r["pauli_16"][name] for r in results])) for name in PAULI_16_NAMES}
    p_sum = float(sum(pauli_16.values()))
    p_i = pauli_16["II"]
    p_total_err = 1.0 - p_i
    f_ent = p_i
    f_avg = (4.0 * f_ent + 1.0) / 5.0
    p_x = pauli_16["IX"] + pauli_16["XI"] + pauli_16["XX"]
    p_y = pauli_16["IY"] + pauli_16["YI"] + pauli_16["YY"] + pauli_16["XY"] + pauli_16["YX"]
    p_z = pauli_16["IZ"] + pauli_16["ZI"] + pauli_16["XZ"] + pauli_16["ZX"] + pauli_16["YZ"] + pauli_16["ZY"]
    p_zz = pauli_16["ZZ"]
    return {
        "n_pairs": n,
        "n_traj_per_pair": int(results[0]["n_traj"]),
        "total_trajectories": int(sum(r["n_traj"] for r in results)),
        "t_gate_us": float(np.mean([r["t_gate_us"] for r in results])),
        "F_ent": float(f_ent),
        "F_avg": float(f_avg),
        "F_Bell": float(np.mean([r["F_Bell"] for r in results])),
        "p_total_err": float(p_total_err),
        "p_leak": float(np.mean([r["p_leak"] for r in results])),
        "pauli_sum": p_sum,
        "z_bias_ratio": float((p_z + p_zz) / max(p_x + p_y, 1e-12)),
        "pauli_16": pauli_16,
        "per_pair_p_err": {r["pair_label"]: float(r["p_total_err"]) for r in results},
        "per_pair_F_avg": {r["pair_label"]: float(r["F_avg"]) for r in results},
        "per_pair_t_gate_us": {r["pair_label"]: float(r["t_gate_us"]) for r in results},
        "cptp_audit": {
            "max_trace_err": float(max(r["cptp_audit"]["max_trace_err"] for r in results)),
            "max_herm_err": float(max(r["cptp_audit"]["max_herm_err"] for r in results)),
            "min_eigval": float(min(r["cptp_audit"]["min_eigval"] for r in results)),
        },
    }


def _worker_exp138_mwpm(task: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level picklable worker executing Exp138's exact Edmonds Blossom MWPM decoder."""
    d = int(task["d"])
    basis = str(task["basis"])
    pauli16 = task["pauli16"]
    p_1q = float(task["p_1q"])
    p_meas = float(task["p_meas"])
    p_idle_Z = float(task["p_idle_Z"])
    n_shots = int(task["n_shots"])
    seed = int(task["seed"])

    code = build_rotated_surface_code(d)
    dem = compile_ideal_circuit_dem(
        code=code,
        rounds=d,
        pauli16=pauli16,
        p_1q=p_1q,
        p_meas=p_meas,
        p_idle_Z=p_idle_Z,
        p_idle_X=0.0,
        memory_basis=basis,
    )
    rng = np.random.default_rng(seed)
    res = simulate_dem_mc(dem, n_shots=n_shots, rng=rng, k_nn=10)
    eps_b = res["eps_L"]
    return {
        "tag": task["tag"],
        "d": d,
        "rounds": d,
        "basis": basis,
        "n_shots": res["n_shots"],
        "n_fail": res["n_fail"],
        "eps_L_block": float(eps_b),
        "ci95_block": [float(res["ci95_lo"]), float(res["ci95_hi"])],
        "eps_L_round": float(eps_block_to_round(eps_b, d)),
        "ci95_round": [
            float(eps_block_to_round(res["ci95_lo"], d)),
            float(eps_block_to_round(res["ci95_hi"], d)),
        ],
        "raw_uncorrected_rate": float(res["raw_uncorrected_rate"]),
    }


def scan_portability() -> List[str]:
    import re
    patterns = (re.compile(r"/(?:home|run/media)/[a-zA-Z0-9_-]+"),)
    hits: List[str] = []
    targets = [
        REPO_ROOT / "experiments" / "exp143_d3_grape_m4_and_hpc_decoder",
        RESULTS_DIR,
        REPO_ROOT / "tests" / "test_exp143.py",
    ]
    for tgt in targets:
        if tgt.is_file():
            files = [tgt]
        elif tgt.is_dir():
            files = [p for p in tgt.rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".md")]
        else:
            continue
        for f in files:
            txt = f.read_text(errors="ignore")
            for pat in patterns:
                if pat.search(txt):
                    hits.append(f"{f.relative_to(REPO_ROOT)} matches {pat.pattern}")
    return hits


def run_exp143() -> Dict[str, Any]:
    t0 = time.time()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    predictions = json.loads((RESULTS_DIR / "predictions_exp143.json").read_text())
    anchors = load_upstream_anchors()

    # Load exact Exp131 Best-of-6 donor pair ensemble (same seed 13701 as Exp137!)
    echo_pairs, _, _ = build_exp131_best_of_6_pairs(n_pairs=6)
    fast_pairs = [p for p in echo_pairs if min(p.g1_mhz, p.g2_mhz) >= 1.15]  # 5 certified fast pairs
    high_g_indices = [i for i, p in enumerate(fast_pairs) if math.sqrt(p.g1_mhz * p.g2_mhz) >= 2.0]

    print(f"[Exp143] Loaded {len(fast_pairs)} certified fast M4 pairs ({len(high_g_indices)} high-g >=2.0 MHz).")
    print("[Exp143] Part 1: Optimizing K=8 Fourier GRAPE pulses on CUDA GPU (2-restart Pareto)...")
    t_opt = time.time()

    lib_cons: List[GrapeSlicePulse] = []
    lib_echo: List[GrapeSlicePulse] = []
    for i, p in enumerate(fast_pairs):
        pl_c = optimize_grape_slice_multistart_cuda(
            pair=p,
            q_r_target=5e5,
            gamma_phi_nuc_khz=anchors["gamma_phi_nuc_cons_khz"],
            k_harmonics=8,
            n_steps=24,
            n_iters=210,
            seed=14301 + i,
        )
        pl_e = optimize_grape_slice_multistart_cuda(
            pair=p,
            q_r_target=5e5,
            gamma_phi_nuc_khz=anchors["gamma_phi_nuc_echo_f15_khz"],
            k_harmonics=8,
            n_steps=24,
            n_iters=210,
            seed=14351 + i,
        )
        lib_cons.append(pl_c)
        lib_echo.append(pl_e)
        print(
            f"  {p.label}: cons t4={4*pl_c.t_slice_us+0.06:.3f}us f_sl={pl_c.noiseless_slice_f_ent:.6f} <nc>={pl_c.mean_n_cav_slice:.3f} BW300={pl_c.bw_300mhz_energy_frac*100:.2f}% | "
            f"echo t4={4*pl_e.t_slice_us+0.06:.3f}us f_sl={pl_e.noiseless_slice_f_ent:.6f} <nc>={pl_e.mean_n_cav_slice:.3f}"
        )
    print(f"  GRAPE optimization finished in {time.time() - t_opt:.1f}s!")

    # Noiseless 4-slice XY4 unitary verification
    nl_cons = [simulate_grape_cz_cuda(p, pl, q_r=0.0, s_eps_uev=0.0, eps_rot=0.0) for p, pl in zip(fast_pairs, lib_cons)]
    nl_echo = [simulate_grape_cz_cuda(p, pl, q_r=0.0, s_eps_uev=0.0, eps_rot=0.0) for p, pl in zip(fast_pairs, lib_echo)]
    agg_nl_cons = _aggregate_pair_channels(nl_cons)
    agg_nl_echo = _aggregate_pair_channels(nl_echo)

    max_abs_s_all = max(max(pl.max_abs_s1, pl.max_abs_s2) for pl in lib_cons + lib_echo)
    min_bw300_all = min(pl.bw_300mhz_energy_frac for pl in lib_cons + lib_echo)
    max_f99_all = max(pl.bw_99pct_mhz for pl in lib_cons + lib_echo)
    mean_t_gate_cons = agg_nl_cons["t_gate_us"]

    print(
        f"  [Noiseless Audit] cons: p_err={agg_nl_cons['p_total_err']:.5f} leak={agg_nl_cons['p_leak']:.2e} t={mean_t_gate_cons:.3f}us | "
        f"echo: p_err={agg_nl_echo['p_total_err']:.5f} leak={agg_nl_echo['p_leak']:.2e} t={agg_nl_echo['t_gate_us']:.3f}us | "
        f"max|s|={max_abs_s_all:.4f} BW300={min_bw300_all*100:.2f}% f99={max_f99_all:.1f}MHz"
    )

    # Export representative waveform (pair_2: g=3.58, 1.93 MHz) for Panel A visualization
    rep_idx = 2
    rep_pl = lib_cons[rep_idx]
    rep_waveform = {
        "pair_label": rep_pl.pair_label,
        "g1_mhz": rep_pl.g1_mhz,
        "g2_mhz": rep_pl.g2_mhz,
        "t_slice_us": rep_pl.t_slice_us,
        "t_grid_ns": [float((k + 0.5) * rep_pl.dt_us * 1e3) for k in range(rep_pl.n_steps)],
        "s1_re": [float(x) for x in np.real(rep_pl.s1_complex)],
        "s1_im": [float(x) for x in np.imag(rep_pl.s1_complex)],
        "s2_re": [float(x) for x in np.real(rep_pl.s2_complex)],
        "s2_im": [float(x) for x in np.imag(rep_pl.s2_complex)],
        "delta1_mhz": [float(x / (2.0 * math.pi)) for x in rep_pl.delta1_mrad],
        "delta2_mhz": [float(x / (2.0 * math.pi)) for x in rep_pl.delta2_mrad],
        "bw_300mhz_energy_frac": rep_pl.bw_300mhz_energy_frac,
        "bw_99pct_mhz": rep_pl.bw_99pct_mhz,
    }

    # -----------------------------------------------------------------------
    # Part 2: Full 12x12 CUDA Strang-Lindblad + M=40 1/f OU Sweep (N_traj=512/pair)
    # -----------------------------------------------------------------------
    print("[Exp143] Part 2: Running 12x12 CUDA Strang-Lindblad + M=40 1/f OU sweep (N_traj=512/pair)...")
    t_sim = time.time()
    n_traj = 512
    s_grid = [0.25, anchors["s_eps_route_c_uev"], 0.50]
    q_grid = [200000.0, 500000.0, 1000000.0]  # Physical NbTiN Q=2e5, 5e5 + horizon target 1e6 (OBS-085)

    # Apples-to-apples Exp137 P4 baseline on the exact same 5 fast pairs (N_traj=512/pair)
    p4_baselines: Dict[str, Any] = {}
    for q_r in q_grid:
        for s_eps in (0.25, anchors["s_eps_route_c_uev"]):
            key = f"P4_Q{int(q_r/1e5)}e5_S{s_eps:.2f}".replace(".", "p")
            res_p4 = [
                simulate_echoed_cz_cuda(p, q_r=q_r, s_eps_uev=s_eps, protocol="P4", n_traj=n_traj, seed=143100 + i)
                for i, p in enumerate(fast_pairs)
            ]
            p4_baselines[key] = _aggregate_pair_channels(res_p4)

    # GRAPE sweep: (1) Conservative 0.5 kHz nuc (double_sweet_spot + P4_exact ablation), (2) Echoed Exp136 0.0225 kHz nuc
    grape_cons_grid: Dict[str, Any] = {}
    grape_echo_grid: Dict[str, Any] = {}
    all_cptp_clean = True

    def _audit_cptp(agg: Dict[str, Any]) -> None:
        nonlocal all_cptp_clean
        ca = agg["cptp_audit"]
        if (
            ca["max_trace_err"] >= 1e-10
            or ca["max_herm_err"] >= 1e-10
            or ca["min_eigval"] <= -1e-9
            or abs(agg["pauli_sum"] - 1.0) >= 1e-10
        ):
            all_cptp_clean = False

    _audit_cptp(agg_nl_cons)
    _audit_cptp(agg_nl_echo)

    seed_s = 143200
    for q_r in q_grid:
        for s_eps in s_grid:
            k_tag = f"Q{int(q_r/1e5)}e5_S{s_eps:.2f}".replace(".", "p")
            # Conservative 0.5 kHz nuclear bath
            rc_list = [
                simulate_grape_cz_cuda(
                    p, pl, q_r=q_r, s_eps_uev=s_eps, n_traj=n_traj,
                    gamma_phi_nuc_khz=anchors["gamma_phi_nuc_cons_khz"],
                    sweet_spot_mode="double_sweet_spot", seed=seed_s + i,
                )
                for i, (p, pl) in enumerate(zip(fast_pairs, lib_cons))
            ]
            seed_s += 20
            agg_c = _aggregate_pair_channels(rc_list)
            agg_c["high_g_3pair_subset"] = _aggregate_pair_channels([rc_list[idx] for idx in high_g_indices])
            _audit_cptp(agg_c)
            grape_cons_grid[k_tag] = agg_c

            # Physically consistent Exp136 echoed nuclear bath (T_2e,XY8 = 14.135 ms -> 0.0225 kHz)
            re_list = [
                simulate_grape_cz_cuda(
                    p, pl, q_r=q_r, s_eps_uev=s_eps, n_traj=n_traj,
                    gamma_phi_nuc_khz=anchors["gamma_phi_nuc_echo_f15_khz"],
                    sweet_spot_mode="double_sweet_spot", seed=seed_s + i,
                )
                for i, (p, pl) in enumerate(zip(fast_pairs, lib_echo))
            ]
            seed_s += 20
            agg_e = _aggregate_pair_channels(re_list)
            agg_e["high_g_3pair_subset"] = _aggregate_pair_channels([re_list[idx] for idx in high_g_indices])
            _audit_cptp(agg_e)
            grape_echo_grid[k_tag] = agg_e

            print(
                f"  {k_tag:14s} | Cons(0.5kHz): p2q={agg_c['p_total_err']:.5f} (hi-g={agg_c['high_g_3pair_subset']['p_total_err']:.5f}) F_avg={agg_c['F_avg']:.5f} F_Bell={agg_c['F_Bell']:.5f} | "
                f"Echo(0.022kHz): p2q={agg_e['p_total_err']:.5f} (hi-g={agg_e['high_g_3pair_subset']['p_total_err']:.5f}) F_avg={agg_e['F_avg']:.5f}"
            )

    # Strict P4_exact sweet-spot ablation at Q=1e6, S=0.25 (isolating pure GRAPE vs double-sweet-spot gain)
    rc_p4ss = [
        simulate_grape_cz_cuda(
            p, pl, q_r=1e6, s_eps_uev=0.25, n_traj=n_traj,
            gamma_phi_nuc_khz=anchors["gamma_phi_nuc_cons_khz"],
            sweet_spot_mode="P4_exact", seed=143900 + i,
        )
        for i, (p, pl) in enumerate(zip(fast_pairs, lib_cons))
    ]
    agg_cons_p4ss = _aggregate_pair_channels(rc_p4ss)
    _audit_cptp(agg_cons_p4ss)
    print(f"  Part 2 completed in {time.time() - t_sim:.1f}s! (all_cptp_clean={all_cptp_clean})")

    # -----------------------------------------------------------------------
    # Part 3: Live Exp138 Edmonds Blossom MWPM Surface-Code Verification
    # -----------------------------------------------------------------------
    print("[Exp143] Part 3: Feeding real GRAPE Pauli-16 channels into Exp138 live MWPM decoder (d=3,5,7,9)...")
    t_qec = time.time()
    qec_candidates = {
        "D3_phys_cons_Q1e6_S0p25_5pair": {
            "label": "GRAPE Cons 0.5kHz (Q=1e6, S=0.25, 5-pair)",
            "channel": grape_cons_grid["Q10e5_S0p25"],
        },
        "D3_phys_cons_Q1e6_S0p25_highG3": {
            "label": "GRAPE Cons 0.5kHz (Q=1e6, S=0.25, high-g >=2MHz)",
            "channel": grape_cons_grid["Q10e5_S0p25"]["high_g_3pair_subset"],
        },
        "D3_phys_echo_Q5e5_S0p39_5pair": {
            "label": "GRAPE Echo 0.022kHz (Q=5e5, S=0.390 nom, 5-pair)",
            "channel": grape_echo_grid["Q5e5_S0p39"],
        },
        "D3_phys_echo_Q1e6_S0p25_5pair": {
            "label": "GRAPE Echo 0.022kHz (Q=1e6, S=0.25, 5-pair)",
            "channel": grape_echo_grid["Q10e5_S0p25"],
        },
    }

    mwpm_tasks: List[Dict[str, Any]] = []
    seed_q = 143500
    qec_ds = [3, 5, 7, 9]
    for ck, cinfo in qec_candidates.items():
        ch = cinfo["channel"]
        p16_sym = normalize_and_scale_pauli16(ch["pauli_16"], ch["p_total_err"], symmetrize_qubits=True)
        t_cyc_4cz_us = 4.0 * ch["t_gate_us"] + 2.0 + 0.2
        p_idle_z = 0.5 * (1.0 - math.exp(-(t_cyc_4cz_us * 1e-3) / anchors["t2e_xy8_f15_ms"]))
        for d in qec_ds:
            n_sh = 3500 if d <= 7 else 2500
            for basis in ("Z", "X"):
                seed_q += 1
                mwpm_tasks.append({
                    "tag": f"{ck}|d{d}|{basis}",
                    "d": d,
                    "basis": basis,
                    "pauli16": p16_sym,
                    "p_1q": anchors["p_1q"],
                    "p_meas": anchors["p_meas_2us"],
                    "p_idle_Z": p_idle_z,
                    "n_shots": n_sh,
                    "seed": seed_q,
                })

    n_workers = min(os.cpu_count() or 4, 8)
    mwpm_raw: Dict[str, Dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        for res in pool.map(_worker_exp138_mwpm, mwpm_tasks):
            mwpm_raw[res["tag"]] = res

    part3_mwpm: Dict[str, Any] = {}
    for ck, cinfo in qec_candidates.items():
        ch = cinfo["channel"]
        by_d: Dict[str, Any] = {}
        eps_r_l, eps_b_l, nsh_l = [], [], []
        for d in qec_ds:
            rz = mwpm_raw[f"{ck}|d{d}|Z"]
            rx = mwpm_raw[f"{ck}|d{d}|X"]
            comb = combine_zx_results(rz, rx)
            by_d[f"d{d}"] = comb
            eps_r_l.append(comb["combined"]["eps_L_round"])
            eps_b_l.append(comb["combined"]["eps_L_block"])
            nsh_l.append(min(rz["n_shots"], rx["n_shots"]))
        fit_r = fit_exponential_suppression(qec_ds, eps_r_l, nsh_l)
        fit_b = fit_exponential_suppression(qec_ds, eps_b_l, nsh_l)
        scaling = compute_machine_scaling_table(
            fit_round=fit_r,
            n_cand=6,
            cryo_nom_cells=anchors["cryo_nom_cells"],
            cryo_max_cells=anchors["cryo_max_cells"],
            deff_ratio=anchors["exp138_deff_ratio_f15_N6"],
        )
        part3_mwpm[ck] = {
            "label": cinfo["label"],
            "p_2q": ch["p_total_err"],
            "F_avg": ch["F_avg"],
            "t_gate_us": ch["t_gate_us"],
            "by_d": by_d,
            "fit_per_round": fit_r,
            "fit_d_round_block": fit_b,
            "scaling_N6_f1p5": scaling,
        }
        c100 = scaling["targets"]["1e-9"]["cryostats_100L_unsplit_2887"] if scaling["feasible"] else -1
        d9 = scaling["targets"]["1e-9"]["d_star"] if scaling["feasible"] else -1
        print(
            f"  [MWPM] {ck:34s} p2q={ch['p_total_err']:.4f} | Lam_rnd={fit_r['Lambda']:.3f} | "
            f"d*(1e-9)={d9} | 100L cryos={c100} (vs Exp138 D2: {anchors['exp138_d2_cryos_100L_1e9']})"
        )
    print(f"  Part 3 live Exp138 MWPM completed in {time.time() - t_qec:.1f}s!")

    # -----------------------------------------------------------------------
    # Part 4: Option-HPC Real-Time 100 Gbps RoCEv2 Decoder Wall & S9.HPC Spec
    # -----------------------------------------------------------------------
    print("[Exp143] Part 4: Running Option-HPC 100G RoCEv2 RDMA decoder wall & S9.HPC hardware spec...")
    best_echo_ch = grape_echo_grid["Q10e5_S0p25"]
    hpc_analysis = analyze_option_hpc_decoder_wall(
        t_gate_d3_us=best_echo_ch["t_gate_us"],
        t_cyc_fast_us=anchors["t_cyc_fast_us"],
        t_cyc_4cz_v5_us=8.932,
        p_2q_d3=best_echo_ch["p_total_err"],
        p_meas=anchors["p_meas_2us"],
    )
    s9hpc_spec = build_s9hpc_hardware_spec(hpc_analysis)
    s9hpc_path = RESULTS_DIR / "s9hpc_hardware_spec.json"
    s9hpc_path.write_text(json.dumps(s9hpc_spec, indent=2))
    print(f"  Wrote {s9hpc_path.relative_to(REPO_ROOT)} (mass={s9hpc_spec['totals_base_4u_option_hpc_module']['total_mass_kg']} kg, power={s9hpc_spec['totals_base_4u_option_hpc_module']['room_temp_power_W']} W, nom=${s9hpc_spec['totals_base_4u_option_hpc_module']['cost_usd_nom']:,})")

    # -----------------------------------------------------------------------
    # Part 5: Pre-Registered DH1–DH7 Honest Evaluation
    # -----------------------------------------------------------------------
    # DH1: Noiseless unitary, leakage, coupling ceiling, 300 MHz AWG BW, t_gate <= 0.90 us
    dh1_checks = {
        "noiseless_p_err_le_5e4": bool(agg_nl_cons["p_total_err"] <= 0.0005 and agg_nl_echo["p_total_err"] <= 0.0005),
        "noiseless_p_leak_le_1e4": bool(agg_nl_cons["p_leak"] <= 1e-4 and agg_nl_echo["p_leak"] <= 1e-4),
        "coupling_cap_obeyed": bool(max_abs_s_all <= 1.0 + 1e-9),
        "bw_300mhz_ge_99p5pct": bool(min_bw300_all >= 0.995),
        "mean_t_gate_le_0p90us": bool(mean_t_gate_cons <= 0.90),
    }
    dh1_pass = all(dh1_checks.values())

    # DH2: Strict conservative Exp137 noise (0.5 kHz nuc, Q=1e6, S=0.25, 5-pair fast ensemble)
    c_1e6_025 = grape_cons_grid["Q10e5_S0p25"]
    p4_1e6_025 = p4_baselines["P4_Q10e5_S0p25"]
    gain_vs_p4 = float(p4_1e6_025["p_total_err"] / max(c_1e6_025["p_total_err"], 1e-9))
    dh2_checks = {
        "cons_Q1e6_S0p25_p_err_le_0p0050": bool(c_1e6_025["p_total_err"] <= 0.0050),
        "cons_Q1e6_S0p25_F_avg_ge_0p9960": bool(c_1e6_025["F_avg"] >= 0.9960),
        "cons_Q1e6_S0p25_F_Bell_ge_0p9965": bool(c_1e6_025["F_Bell"] >= 0.9965),
        "gain_vs_P4_ge_1p70": bool(gain_vs_p4 >= 1.70),
    }
    dh2_pass = all(dh2_checks.values())

    # DH3: Echoed Exp136 29Si nuclear bath (Q=5e5 S=0.39 <= 0.0045 AND Q=1e6 S=0.25 <= 0.0035)
    e_5e5_039 = grape_echo_grid["Q5e5_S0p39"]
    e_1e6_025 = grape_echo_grid["Q10e5_S0p25"]
    dh3_checks = {
        "echo_Q5e5_S0p39_p_err_le_0p0045": bool(e_5e5_039["p_total_err"] <= 0.0045),
        "echo_Q1e6_S0p25_p_err_le_0p0035": bool(e_1e6_025["p_total_err"] <= 0.0035),
    }
    dh3_pass = all(dh3_checks.values())

    # DH4: Live Exp138 MWPM empirical Lambda >= 2.20 and 100L 10^-9 cryostats <= 130
    mwpm_cons = part3_mwpm["D3_phys_cons_Q1e6_S0p25_5pair"]
    mwpm_echo_5 = part3_mwpm["D3_phys_echo_Q5e5_S0p39_5pair"]
    mwpm_echo_10 = part3_mwpm["D3_phys_echo_Q1e6_S0p25_5pair"]
    lam_cons = mwpm_cons["fit_per_round"]["Lambda"]
    cryo_cons = mwpm_cons["scaling_N6_f1p5"]["targets"]["1e-9"]["cryostats_100L_unsplit_2887"]
    lam_echo10 = mwpm_echo_10["fit_per_round"]["Lambda"]
    cryo_echo10 = mwpm_echo_10["scaling_N6_f1p5"]["targets"]["1e-9"]["cryostats_100L_unsplit_2887"]
    dh4_pass = bool(lam_cons >= 2.20 and cryo_cons <= 130)

    # DH5: Option-HPC backlog wall & bandwidth
    d37_hpc = next(r for r in hpc_analysis["surface_code_scaling"] if r["d"] == 37)
    d21_hpc = next(r for r in hpc_analysis["surface_code_scaling"] if r["d"] == 21)
    qldpc_hpc = hpc_analysis["qldpc_gross_144_12_12"]
    dh5_checks = {
        "cpu_single_fails_d37_8p93us": bool(not d37_hpc["backlog_free_cpu_8p93us"]),
        "cpu_single_fails_d21_2p62us": bool(not d21_hpc["backlog_free_cpu_2p62us"]),
        "hpc_parallel_passes_d37_8p93us": bool(d37_hpc["backlog_free_hpc_8p93us"]),
        "qldpc_mean_lt_2p62us": bool(qldpc_hpc["backlog_free_hpc_2p62us"]),
        "bw_100L_d37_hard_v5_le_25gbps": bool(d37_hpc["bw_100L_hard_v5_gbps"] <= 25.0),
    }
    dh5_pass = all(dh5_checks.values())

    # DH6: s9hpc_hardware_spec.json complete
    tot_hpc = s9hpc_spec["totals_base_4u_option_hpc_module"]
    dh6_pass = bool(
        s9hpc_spec["subsystem_id"] == "S9.HPC"
        and s9hpc_spec["no_supplier_quotes"] is True
        and tot_hpc["total_mass_kg"] > 0
        and tot_hpc["room_temp_power_W"] > 0
        and tot_hpc["cryo_load_W"] == 0.0
        and 0 < tot_hpc["cost_usd_low"] <= tot_hpc["cost_usd_nom"] <= tot_hpc["cost_usd_high"]
    )

    # DH7: CPTP & portability
    portability_hits = scan_portability()
    dh7_pass = bool(all_cptp_clean and len(portability_hits) == 0)

    verdicts = {
        "DH1_GRAPE_UNITARY_AND_AWG_BANDWIDTH": {
            "passed": dh1_pass,
            "checks": dh1_checks,
            "noiseless_p_err_cons": agg_nl_cons["p_total_err"],
            "noiseless_p_leak_cons": agg_nl_cons["p_leak"],
            "mean_t_gate_cons_us": mean_t_gate_cons,
            "min_bw_300mhz_frac": min_bw300_all,
            "max_f99_mhz": max_f99_all,
        },
        "DH2_D3_GATE_FIDELITY_UNDER_CONSERVATIVE_EXP137_NOISE": {
            "passed": dh2_pass,
            "checks": dh2_checks,
            "cons_Q1e6_S0p25_p_err_5pair": c_1e6_025["p_total_err"],
            "cons_Q1e6_S0p25_p_err_highG3": c_1e6_025["high_g_3pair_subset"]["p_total_err"],
            "cons_Q1e6_S0p25_F_avg_5pair": c_1e6_025["F_avg"],
            "cons_Q1e6_S0p25_F_Bell_5pair": c_1e6_025["F_Bell"],
            "P4_Q1e6_S0p25_p_err_5pair": p4_1e6_025["p_total_err"],
            "gain_vs_P4": gain_vs_p4,
        },
        "DH3_D3_GATE_FIDELITY_AT_NOMINAL_ROTA_C_AND_ECHOED_NUC": {
            "passed": dh3_pass,
            "checks": dh3_checks,
            "echo_Q5e5_S0p39_p_err_5pair": e_5e5_039["p_total_err"],
            "echo_Q5e5_S0p39_F_avg_5pair": e_5e5_039["F_avg"],
            "echo_Q1e6_S0p25_p_err_5pair": e_1e6_025["p_total_err"],
            "echo_Q1e6_S0p25_F_avg_5pair": e_1e6_025["F_avg"],
        },
        "DH4_LIVE_EXP138_MWPM_LAMBDA_D3_PHYS": {
            "passed": dh4_pass,
            "Lambda_D3_phys_cons_5pair": lam_cons,
            "cryostats_100L_1e9_cons_5pair": cryo_cons,
            "Lambda_D3_phys_echo_Q5e5_S0p39": mwpm_echo_5["fit_per_round"]["Lambda"],
            "cryostats_100L_1e9_echo_Q5e5_S0p39": mwpm_echo_5["scaling_N6_f1p5"]["targets"]["1e-9"]["cryostats_100L_unsplit_2887"],
            "Lambda_D3_phys_echo_Q1e6_S0p25": lam_echo10,
            "cryostats_100L_1e9_echo_Q1e6_S0p25": cryo_echo10,
            "exp138_D2_baseline_cryostats_100L_1e9": anchors["exp138_d2_cryos_100L_1e9"],
        },
        "DH5_OPTION_HPC_REALTIME_DECODER_WALL_AND_BACKLOG": {
            "passed": dh5_pass,
            "checks": dh5_checks,
            "d37_tau_cpu_single_us": d37_hpc["tau_cpu_single_us"],
            "d37_tau_hpc_e2e_stream_us": d37_hpc["tau_hpc_e2e_stream_us"],
            "qldpc_tau_hpc_e2e_mean_us": qldpc_hpc["tau_hpc_e2e_mean_us"],
            "d37_100L_hard_bw_v5_gbps": d37_hpc["bw_100L_hard_v5_gbps"],
        },
        "DH6_S9HPC_HARDWARE_SPEC_COMPLETE_FOR_CAD_BOM_V6": {
            "passed": dh6_pass,
            "total_mass_kg": tot_hpc["total_mass_kg"],
            "room_temp_power_W": tot_hpc["room_temp_power_W"],
            "cost_usd_nom": tot_hpc["cost_usd_nom"],
        },
        "DH7_CPTP_AUDIT_PORTABILITY_VISUAL_AND_TESTS": {
            "passed": dh7_pass,
            "all_cptp_clean": all_cptp_clean,
            "hardcoded_path_hits": len(portability_hits),
        },
    }

    n_passed = sum(1 for v in verdicts.values() if v["passed"])
    elapsed = time.time() - t0

    # Top-level Exp141-compatible D3 physical scaling export (from primary echoed Q=1e6, S=0.25)
    out_json: Dict[str, Any] = {
        "experiment": "exp143_d3_grape_m4_and_hpc_decoder",
        "hypothesis_id": "H161",
        "date": "2026-11-23",
        "no_lab_measurement": True,
        "no_supplier_quotes": True,
        "epistemic_tag": "{Sayısal-Simülasyon}",
        "elapsed_sec": float(elapsed),
        "n_passed": int(n_passed),
        "n_total": len(verdicts),
        "success_rule_met": bool(n_passed >= 5 and all_cptp_clean and len(portability_hits) == 0),
        "upstream_anchors": anchors,
        "predictions": predictions,
        "verdicts": verdicts,
        "part1_grape_optimization": {
            "k_harmonics": 8,
            "n_steps_per_slice": 24,
            "n_fast_pairs": len(fast_pairs),
            "high_g_pair_labels": [fast_pairs[i].label for i in high_g_indices],
            "max_abs_s_all": float(max_abs_s_all),
            "min_bw_300mhz_energy_frac": float(min_bw300_all),
            "max_bw_99pct_mhz": float(max_f99_all),
            "noiseless_cons_library": agg_nl_cons,
            "noiseless_echo_library": agg_nl_echo,
            "per_pair_cons_pulses": [
                {
                    "pair_label": pl.pair_label,
                    "g1_mhz": pl.g1_mhz,
                    "g2_mhz": pl.g2_mhz,
                    "t_slice_us": pl.t_slice_us,
                    "t_gate_4slice_us": 4.0 * pl.t_slice_us + 0.06,
                    "noiseless_slice_f_ent": pl.noiseless_slice_f_ent,
                    "noiseless_slice_p_leak": pl.noiseless_slice_p_leak,
                    "mean_n_cav_slice": pl.mean_n_cav_slice,
                    "max_abs_s": max(pl.max_abs_s1, pl.max_abs_s2),
                    "bw_300mhz_energy_frac": pl.bw_300mhz_energy_frac,
                    "bw_99pct_mhz": pl.bw_99pct_mhz,
                }
                for pl in lib_cons
            ],
            "per_pair_echo_pulses": [
                {
                    "pair_label": pl.pair_label,
                    "g1_mhz": pl.g1_mhz,
                    "g2_mhz": pl.g2_mhz,
                    "t_slice_us": pl.t_slice_us,
                    "t_gate_4slice_us": 4.0 * pl.t_slice_us + 0.06,
                    "noiseless_slice_f_ent": pl.noiseless_slice_f_ent,
                    "noiseless_slice_p_leak": pl.noiseless_slice_p_leak,
                    "mean_n_cav_slice": pl.mean_n_cav_slice,
                    "max_abs_s": max(pl.max_abs_s1, pl.max_abs_s2),
                    "bw_300mhz_energy_frac": pl.bw_300mhz_energy_frac,
                    "bw_99pct_mhz": pl.bw_99pct_mhz,
                }
                for pl in lib_echo
            ],
            "representative_waveform": rep_waveform,
        },
        "part2_noisy_1f_sweep": {
            "n_traj_per_pair": n_traj,
            "s_eps_grid_uev": s_grid,
            "q_r_grid": q_grid,
            "p4_baselines_5pair": p4_baselines,
            "grape_conservative_0p5kHz_nuc": grape_cons_grid,
            "grape_conservative_P4_sweetspot_ablation_Q1e6_S0p25": agg_cons_p4ss,
            "grape_echoed_exp136_0p0225kHz_nuc": grape_echo_grid,
            "all_cptp_clean": all_cptp_clean,
        },
        "part3_live_exp138_mwpm_verification": part3_mwpm,
        "part4_option_hpc_decoder_wall": hpc_analysis,
        "s9hpc_hardware_spec_summary": s9hpc_spec["totals_base_4u_option_hpc_module"],
        "portability_hardcoded_hits": portability_hits,
    }

    out_path = RESULTS_DIR / "exp143.json"
    out_path.write_text(json.dumps(out_json, indent=2))
    print(f"\n[Exp143] DONE in {elapsed:.1f}s -> {out_path.relative_to(REPO_ROOT)}")
    print(f"[Exp143] Verdicts: {n_passed}/{len(verdicts)} PASS (success_rule_met={out_json['success_rule_met']})")
    for k, v in verdicts.items():
        print(f"  {'PASS' if v['passed'] else 'FAIL'} | {k}")
    return out_json


if __name__ == "__main__":
    run_exp143()
