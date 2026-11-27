"""
Exp138 (H156) — Defective/Missing-Cell Rotated Surface Code Fault-Tolerant
Threshold, Exact Blossom MWPM Decoder, Super-Stabilizer Degradation &
Machine Scaling for Exp141 ($/logical qubit).

Reads all 6 v5.0 upstream JSON anchors dynamically (zero hardcoded user paths):
  - Exp136: 29Si yield (f=1.0%, f*=1.5%+2MV/m Stark) & XY8-N64 T2e
  - Exp137: Exact 16-Pauli M4 bus CZ channels & 2D (Q_r, S_eps) phase map
  - Exp139: Route C S_eps=0.3897 uev/rtHz & flip-flop yield 0.9770
  - Exp140: N_mux*=32 readout fidelity (0.996139 -> p_meas=0.003861) & 2887-cell MXC ceiling
  - Exp132: BOED 20mK spectroscopy FNR=0.002008, FPR=0.0
  - Exp126: 32D single-qubit Rx_pi2 fidelity (0.99917 -> p_1q=0.00083)

Outputs:
  results/exp138_defective_surface_code_ft/exp138.json

Epistemic Tag: {Sayısal-Simülasyon} / {Model} (no_lab_measurement = True).
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

from experiments.exp138_defective_surface_code_ft.rotated_surface_code138 import (
    apply_site_dropouts,
    build_rotated_surface_code,
    compile_deformed_circuit_dem,
    compile_ideal_circuit_dem,
    depolarizing_pauli16,
    normalize_and_scale_pauli16,
    simulate_dem_mc,
    wilson_ci95,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "exp138_defective_surface_code_ft"


# ---------------------------------------------------------------------------
# 1. Upstream v5.0 Anchor Loader
# ---------------------------------------------------------------------------

def _log_interp_2d(x: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Log-linear interpolation in S_eps between two adjacent Exp137 grid points."""
    if x <= x1:
        return float(y1)
    if x >= x2:
        return float(y2)
    t = (math.log(x) - math.log(x1)) / (math.log(x2) - math.log(x1))
    return float(y1 + t * (y2 - y1))


def load_upstream_anchors() -> Dict[str, Any]:
    """Load all 6 read-only upstream JSON anchors from REPO_ROOT/results."""
    e136 = json.loads((REPO_ROOT / "results/exp136_tb_sp3d5s_hyperfine/exp136.json").read_text())
    e137 = json.loads((REPO_ROOT / "results/exp137_echoed_m4_bus_gate/exp137.json").read_text())
    e139 = json.loads((REPO_ROOT / "results/exp139_epi_cap_process_integration/exp139.json").read_text())
    e140 = json.loads((REPO_ROOT / "results/exp140_cryo_fpga_boed_mux_readout/exp140.json").read_text())
    e132 = json.loads((REPO_ROOT / "results/exp132_bayesian_spectroscopy_cellisa3/exp132.json").read_text())
    e126 = json.loads((REPO_ROOT / "results/exp126_atom_cell_programming/exp126.json").read_text())

    # Exp136: f = 1.0%, 1.5%, 2.0% yields & XY8-N64 T2e
    prim136 = {r["abundance_pct"]: r for r in e136["stage6_isotope_stark_sweep"]["primary_TB_CP_HM5962"]}
    stark136 = {
        (r["abundance_pct"], r["E_z_MV_per_m"]): r
        for r in e136["stage6_isotope_stark_sweep"]["stark_tuning_yield_HM5962"]
    }
    f10_yield = float(prim136[1.0]["mode_b"]["yield_frac"])
    f10_yield_ddrf = float(prim136[1.0]["mode_b"]["gap_stats"]["yield_and_gap_ge_6893Hz"])
    f10_t2e_ms = float(prim136[1.0]["coherence"]["T2e_XY8_N64_alpha1_ms"])  # OBS-110 conservative alpha=1
    f15_yield_base = float(prim136[1.5]["mode_b"]["yield_frac"])
    f15_yield_stark2 = float(stark136[(1.5, 2.0)]["yield_frac"])
    f15_yield_stark2_ddrf = float(stark136[(1.5, 2.0)]["yield_and_gap_ge_6893Hz"])
    f15_t2e_ms = float(prim136[1.5]["coherence"]["T2e_XY8_N64_alpha1_ms"])  # OBS-110: 7.07 ms (not alpha=2 14.135 ms!)
    f20_yield = float(prim136[2.0]["mode_b"]["yield_frac"])
    f20_t2e_ms = float(prim136[2.0]["coherence"]["T2e_XY8_N64_alpha1_ms"])  # OBS-110: 5.42 ms

    # Exp139: Route C charge noise & flip-flop yield
    e139_routes = e139["charge_noise_and_exp137_bridge"]["routes"]
    route_c_bridge = e139_routes["route_C_nominal_FG350C_Dit_1p5e10"]
    route_a_bridge = e139_routes["route_A_5keV_post_anneal_mbe_unpassivated"]
    s_eps_route_c = float(route_c_bridge["S_eps_ueV_rtHz"])
    s_eps_route_c_lo = float(e139_routes["route_C_thin_oxide_Dit_1p0e10_dox5"]["S_eps_ueV_rtHz"])
    s_eps_route_c_hi = float(e139_routes["route_C_conservative_Dit_3p0e10"]["S_eps_ueV_rtHz"])
    s_eps_route_a = float(route_a_bridge["S_eps_ueV_rtHz"])
    p_ff_route_c = float(e139["route_flipflop_yields_exp131"]["route_C_v5_1530K_5keV_8nm_FG350C"]["yield_C_ge_100"])
    p_ff_route_a = float(e139["route_flipflop_yields_exp131"]["route_A_v5_1530K_5keV_8nm_mbe"]["yield_C_ge_100"])

    # Exp137: Pauli-16 templates + 2D (Q_r, S_eps) phase map points
    p4_ch = e137["part4_exp138_pauli_channels"]
    phase_pts = {
        (float(pt["q_r"]), float(pt["s_eps_uev"])): pt
        for pt in e137["part3_2d_phase_map"]["points"]
    }
    # Log-linear interpolation at Exp139 Route C nominal S_eps = 0.3897 between 0.25 and 0.50
    interp_route_c: Dict[str, Dict[str, float]] = {}
    for q_label, q_val in (("Q2e5", 200000.0), ("Q5e5", 500000.0)):
        pt_lo = phase_pts[(q_val, 0.25)]
        pt_hi = phase_pts[(q_val, 0.50)]
        p_err_c = _log_interp_2d(s_eps_route_c, 0.25, pt_lo["p_total_err"], 0.50, pt_hi["p_total_err"])
        p_leak_c = _log_interp_2d(s_eps_route_c, 0.25, pt_lo["p_leak"], 0.50, pt_hi["p_leak"])
        f_avg_c = 1.0 - 0.8 * p_err_c
        interp_route_c[q_label] = {
            "q_r": q_val,
            "s_eps_uev": s_eps_route_c,
            "p_total_err": p_err_c,
            "p_leak": p_leak_c,
            "F_avg": f_avg_c,
            "t_gate_us": float(pt_lo["t_gate_us"]),
        }

    # Exp140: MUX readout + cryostat capacity
    mux32 = e140["mux_readout_3kOhm_NbTiN"]["by_nmux"]["32"]
    f_ro_2us = float(mux32["F_ro_at_2us"])
    p_meas_2us = 1.0 - f_ro_2us
    f_ro_3us = float(mux32["best_F_ro"])
    p_meas_3us = 1.0 - f_ro_3us
    cryo_1024 = e140["cryo_heat_budgets"]["m4_1024_hemt7p8mW"]
    cryo_max_cells = int(cryo_1024["single_cryostat_max_cells"])
    cryo_nom_cells = int(cryo_1024["n_cells"])
    exp140_demo_cycle_us = float(e140["cellisa_v35_syndrome_demo"]["summary"]["cycle_duration_us"])

    # Exp132: BOED FNR/FPR
    boed = e132["boed_20mK_LNA1p4K_N2000"]
    boed_fnr = float(boed["fnr"])
    boed_fpr = float(boed["fpr"])

    # Exp126: 1-qubit gate fidelity (Rx_pi2 32D nominal mean across 4 nuclear qubits)
    rx_list = e126["part1_f1_universal_gates"]["gates_summary"]["Rx_pi2"]
    f_1q_mean = float(np.mean([g["nominal_fidelity_32d"] for g in rx_list]))
    p_1q = 1.0 - f_1q_mean

    # Physically complete 4-CZ + MUX readout rotated surface code syndrome cycle duration
    t_gate_fast_us = float(phase_pts[(500000.0, 0.25)]["t_gate_us"])
    t_cycle_4cz_us = 4.0 * t_gate_fast_us + 2.0 + 0.2  # 4 sequential CZ + 2 us RO + 0.2 us 1Q/reset
    p_idle_Z_f10 = 0.5 * (1.0 - math.exp(-(t_cycle_4cz_us * 1e-3) / f10_t2e_ms))
    p_idle_Z_f15 = 0.5 * (1.0 - math.exp(-(t_cycle_4cz_us * 1e-3) / f15_t2e_ms))

    return {
        "exp136": {
            "f10_yield": f10_yield,
            "f10_t2e_xy8_n64_ms": f10_t2e_ms,
            "f15_yield_base": f15_yield_base,
            "f15_yield_stark2": f15_yield_stark2,
            "f15_t2e_xy8_n64_ms": f15_t2e_ms,
            "f20_yield": f20_yield,
            "f20_t2e_xy8_n64_ms": f20_t2e_ms,
        },
        "exp139": {
            "s_eps_route_c_uev": s_eps_route_c,
            "s_eps_route_c_band_uev": [s_eps_route_c_lo, s_eps_route_c_hi],
            "s_eps_route_a_uev": s_eps_route_a,
            "p_ff_route_c": p_ff_route_c,
            "p_ff_route_a": p_ff_route_a,
        },
        "exp137": {
            "part4_channels": p4_ch,
            "phase_points_Q2e5_S0p25": phase_pts[(200000.0, 0.25)],
            "phase_points_Q2e5_S0p50": phase_pts[(200000.0, 0.50)],
            "phase_points_Q2e5_S1p00": phase_pts[(200000.0, 1.00)],
            "phase_points_Q5e5_S0p25": phase_pts[(500000.0, 0.25)],
            "phase_points_Q5e5_S0p50": phase_pts[(500000.0, 0.50)],
            "phase_points_Q5e5_S1p00": phase_pts[(500000.0, 1.00)],
            "interp_route_c": interp_route_c,
        },
        "exp140": {
            "n_mux_star": 32,
            "f_ro_2us": f_ro_2us,
            "p_meas_2us": p_meas_2us,
            "f_ro_3us": f_ro_3us,
            "p_meas_3us": p_meas_3us,
            "single_cryostat_max_cells": cryo_max_cells,
            "nominal_module_cells": cryo_nom_cells,
            "demo_1cz_cycle_us": exp140_demo_cycle_us,
            "full_4cz_syndrome_cycle_us": t_cycle_4cz_us,
        },
        "exp132": {
            "boed_fnr": boed_fnr,
            "boed_fpr": boed_fpr,
        },
        "exp126": {
            "f_1q_mean": f_1q_mean,
            "p_1q": p_1q,
        },
        "derived_idle": {
            "p_idle_Z_f10": p_idle_Z_f10,
            "p_idle_Z_f15": p_idle_Z_f15,
        },
    }


# ---------------------------------------------------------------------------
# 2. Parallel Worker Helpers (Top-Level Picklable Functions)
# ---------------------------------------------------------------------------

def eps_block_to_round(eps_blk: float, rounds: int) -> float:
    """
    Exact memory-decay per-round logical error inversion (Google Quantum AI / Fowler):
      eps_blk(r) = 0.5 * (1 - (1 - 2 * eps_round)^r)
      => eps_round = 0.5 * (1 - max(0, 1 - 2 * eps_blk)^(1 / r))
    For eps_blk << 0.5, equals eps_blk / r; for saturated eps_blk >= 0.5, saturates
    honestly at 0.50 without spurious 1/r decay.
    """
    if eps_blk <= 0.0:
        return 0.0
    if eps_blk >= 0.5:
        return 0.5
    return float(0.5 * (1.0 - (1.0 - 2.0 * eps_blk) ** (1.0 / float(rounds))))


def _worker_ideal_point(task: Dict[str, Any]) -> Dict[str, Any]:
    """Run one (d, basis, pauli16, noise) Monte Carlo job deterministically."""
    d = int(task["d"])
    rounds = int(task.get("rounds", d))
    basis = str(task["basis"])
    pauli16 = task["pauli16"]
    p_1q = float(task["p_1q"])
    p_meas = float(task["p_meas"])
    p_idle_Z = float(task["p_idle_Z"])
    p_idle_X = float(task.get("p_idle_X", 0.0))
    n_shots = int(task["n_shots"])
    seed = int(task["seed"])

    code = build_rotated_surface_code(d)
    dem = compile_ideal_circuit_dem(
        code=code,
        rounds=rounds,
        pauli16=pauli16,
        p_1q=p_1q,
        p_meas=p_meas,
        p_idle_Z=p_idle_Z,
        p_idle_X=p_idle_X,
        memory_basis=basis,
    )
    rng = np.random.default_rng(seed)
    res = simulate_dem_mc(dem, n_shots=n_shots, rng=rng, k_nn=10)
    eps = res["eps_L"]
    eps_round = eps_block_to_round(eps, rounds)
    ci_r_lo = eps_block_to_round(res["ci95_lo"], rounds)
    ci_r_hi = eps_block_to_round(res["ci95_hi"], rounds)
    return {
        "tag": task["tag"],
        "d": d,
        "rounds": rounds,
        "basis": basis,
        "non_graphlike": dem.non_graphlike_count,
        "n_mechanisms": dem.total_mechanism_count,
        "n_shots": res["n_shots"],
        "n_fail": res["n_fail"],
        "eps_L_block": eps,
        "ci95_block": [res["ci95_lo"], res["ci95_hi"]],
        "eps_L_round": float(eps_round),
        "ci95_round": [float(ci_r_lo), float(ci_r_hi)],
        "raw_uncorrected_rate": res["raw_uncorrected_rate"],
        "mean_defects_per_shot": res["mean_defects_per_shot"],
    }


def _worker_defective_batch(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate defective super-stabilizer realizations (geometry + circuit-level
    MWPM decoding) for one (regime, N_cand, d, scenario) job.
    """
    d = int(task["d"])
    p_drop = float(task["p_drop"])
    n_geom = int(task["n_geom"])
    n_decode_lattices = int(task["n_decode_lattices"])
    shots_per_lattice = int(task["shots_per_lattice"])
    pauli16 = task["pauli16"]
    p_1q = float(task["p_1q"])
    p_meas = float(task["p_meas"])
    p_idle_Z = float(task["p_idle_Z"])
    seed = int(task["seed"])

    code = build_rotated_surface_code(d)
    rng = np.random.default_rng(seed)

    d_effs: List[int] = []
    d_eff_xs: List[int] = []
    d_eff_zs: List[int] = []
    n_super_list: List[int] = []
    max_w_list: List[int] = []
    comm_all_ok = True
    n_comm_ok = 0

    # Decoding accumulators
    total_shots = 0
    total_fails_z = 0
    total_fails_x = 0
    n_broken_decode = 0
    representative_patch: Optional[Dict[str, Any]] = None

    for idx in range(n_geom):
        dead_data = set(np.flatnonzero(rng.random(code.n_data) < p_drop).tolist())
        dead_z = set(np.flatnonzero(rng.random(code.n_z) < p_drop).tolist())
        dead_x = set(np.flatnonzero(rng.random(code.n_x) < p_drop).tolist())
        df = apply_site_dropouts(code, dead_data, dead_z, dead_x)
        if df.commutes_exact:
            n_comm_ok += 1
        else:
            comm_all_ok = False
        d_effs.append(df.d_eff)
        d_eff_xs.append(df.d_eff_X)
        d_eff_zs.append(df.d_eff_Z)
        n_super_list.append(df.n_super_z + df.n_super_x)
        max_w_list.append(max(df.max_z_weight, df.max_x_weight))

        # Capture 1 clean illustrative patch with 1-3 defects for visualization
        if (
            representative_patch is None
            and d == 7
            and 1 <= len(dead_data) + len(dead_z) + len(dead_x) <= 3
            and df.d_eff >= 4
            and (df.n_super_z > 0 or df.n_super_x > 0)
        ):
            representative_patch = {
                "d": d,
                "p_drop": p_drop,
                "dead_data_coords": [list(code.data_coords[q]) for q in sorted(dead_data)],
                "dead_z_anc_coords": [list(code.z_coords[a]) for a in sorted(dead_z)],
                "dead_x_anc_coords": [list(code.x_coords[a]) for a in sorted(dead_x)],
                "z_super_stabs": [
                    {
                        "qubits": [list(code.data_coords[q]) for q in sorted(s)],
                        "weight": len(s),
                        "merge_count": c,
                    }
                    for s, c in zip(df.z_stabs, df.z_merge_counts)
                    if c > 1
                ],
                "x_super_stabs": [
                    {
                        "qubits": [list(code.data_coords[q]) for q in sorted(s)],
                        "weight": len(s),
                        "merge_count": c,
                    }
                    for s, c in zip(df.x_stabs, df.x_merge_counts)
                    if c > 1
                ],
                "d_eff_X": df.d_eff_X,
                "d_eff_Z": df.d_eff_Z,
                "d_eff": df.d_eff,
                "commutes_exact": df.commutes_exact,
            }

        # Decode circuit-level DEM on the first `n_decode_lattices` realizations
        if idx < n_decode_lattices and shots_per_lattice > 0:
            total_shots += shots_per_lattice
            if not df.survived or df.d_eff == 0:
                n_broken_decode += 1
                # Percolation failure -> completely uncorrectable (50% random logical error)
                total_fails_z += shots_per_lattice // 2
                total_fails_x += shots_per_lattice // 2
            else:
                dem_z = compile_deformed_circuit_dem(
                    df, d, pauli16, p_1q, p_meas, p_idle_Z, 0.0, memory_basis="Z"
                )
                dem_x = compile_deformed_circuit_dem(
                    df, d, pauli16, p_1q, p_meas, p_idle_Z, 0.0, memory_basis="X"
                )
                if dem_z is None:
                    total_fails_z += shots_per_lattice // 2
                else:
                    rz = simulate_dem_mc(dem_z, shots_per_lattice, rng, k_nn=10)
                    total_fails_z += int(rz["n_fail"])
                if dem_x is None:
                    total_fails_x += shots_per_lattice // 2
                else:
                    rx = simulate_dem_mc(dem_x, shots_per_lattice, rng, k_nn=10)
                    total_fails_x += int(rx["n_fail"])

    arr_d = np.array(d_effs, dtype=np.float64)
    surv_prob = float(np.mean(arr_d >= 1.0))
    out: Dict[str, Any] = {
        "tag": task["tag"],
        "d": d,
        "p_drop": p_drop,
        "n_geom_realizations": n_geom,
        "commutes_all_exact": comm_all_ok,
        "n_commutes_ok": n_comm_ok,
        "mean_d_eff": float(np.mean(arr_d)),
        "std_d_eff": float(np.std(arr_d)),
        "p10_d_eff": float(np.percentile(arr_d, 10)),
        "median_d_eff": float(np.median(arr_d)),
        "mean_d_eff_over_d": float(np.mean(arr_d) / float(d)),
        "mean_d_eff_X": float(np.mean(d_eff_xs)),
        "mean_d_eff_Z": float(np.mean(d_eff_zs)),
        "survival_prob": surv_prob,
        "mean_n_super_stabs": float(np.mean(n_super_list)),
        "mean_max_stab_weight": float(np.mean(max_w_list)),
        "representative_patch": representative_patch,
    }
    if total_shots > 0:
        eps_z = total_fails_z / float(total_shots)
        eps_x = total_fails_x / float(total_shots)
        eps_tot = 1.0 - (1.0 - eps_z) * (1.0 - eps_x)
        eps_z_r = eps_block_to_round(eps_z, d)
        eps_x_r = eps_block_to_round(eps_x, d)
        eps_round = 1.0 - (1.0 - eps_z_r) * (1.0 - eps_x_r)
        ci_z = wilson_ci95(total_fails_z, total_shots)
        ci_x = wilson_ci95(total_fails_x, total_shots)
        out["decoding"] = {
            "n_decode_lattices": n_decode_lattices,
            "shots_per_lattice": shots_per_lattice,
            "total_shots": total_shots,
            "n_broken_lattices": n_broken_decode,
            "eps_L_Z_block": float(eps_z),
            "ci95_Z_block": [float(ci_z[0]), float(ci_z[1])],
            "eps_L_X_block": float(eps_x),
            "ci95_X_block": [float(ci_x[0]), float(ci_x[1])],
            "eps_L_combined_block": float(eps_tot),
            "eps_L_combined_round": float(eps_round),
        }
    return out


# ---------------------------------------------------------------------------
# 3. Statistical & Scaling Analysis Utilities
# ---------------------------------------------------------------------------

def combine_zx_results(rz: Dict[str, Any], rx: Dict[str, Any]) -> Dict[str, Any]:
    """Combine independent Z-memory and X-memory logical error results conservatively."""
    d = int(rz["d"])
    rounds = int(rz["rounds"])
    ez_b, ex_b = float(rz["eps_L_block"]), float(rx["eps_L_block"])
    etot_b = 1.0 - (1.0 - ez_b) * (1.0 - ex_b)
    lo_b = 1.0 - (1.0 - float(rz["ci95_block"][0])) * (1.0 - float(rx["ci95_block"][0]))
    hi_b = 1.0 - (1.0 - float(rz["ci95_block"][1])) * (1.0 - float(rx["ci95_block"][1]))

    # Exact per-round inversion per basis (saturates cleanly at 0.5 -> combined 0.75)
    ez_r = eps_block_to_round(ez_b, rounds)
    ex_r = eps_block_to_round(ex_b, rounds)
    ez_r_lo = eps_block_to_round(float(rz["ci95_block"][0]), rounds)
    ez_r_hi = eps_block_to_round(float(rz["ci95_block"][1]), rounds)
    ex_r_lo = eps_block_to_round(float(rx["ci95_block"][0]), rounds)
    ex_r_hi = eps_block_to_round(float(rx["ci95_block"][1]), rounds)

    etot_r = 1.0 - (1.0 - ez_r) * (1.0 - ex_r)
    lo_r = 1.0 - (1.0 - ez_r_lo) * (1.0 - ex_r_lo)
    hi_r = 1.0 - (1.0 - ez_r_hi) * (1.0 - ex_r_hi)

    return {
        "d": d,
        "rounds": rounds,
        "n_shots_per_basis": int(min(rz["n_shots"], rx["n_shots"])),
        "Z_memory": {
            "n_shots": int(rz["n_shots"]),
            "n_fail": int(rz["n_fail"]),
            "eps_L_block": ez_b,
            "ci95_block": [float(rz["ci95_block"][0]), float(rz["ci95_block"][1])],
            "eps_L_round": float(ez_r),
            "ci95_round": [float(ez_r_lo), float(ez_r_hi)],
            "raw_uncorrected_rate": float(rz["raw_uncorrected_rate"]),
        },
        "X_memory": {
            "n_shots": int(rx["n_shots"]),
            "n_fail": int(rx["n_fail"]),
            "eps_L_block": ex_b,
            "ci95_block": [float(rx["ci95_block"][0]), float(rx["ci95_block"][1])],
            "eps_L_round": float(ex_r),
            "ci95_round": [float(ex_r_lo), float(ex_r_hi)],
            "raw_uncorrected_rate": float(rx["raw_uncorrected_rate"]),
        },
        "combined": {
            "eps_L_block": float(etot_b),
            "ci95_block": [float(lo_b), float(hi_b)],
            "eps_L_round": float(etot_r),
            "ci95_round": [float(lo_r), float(hi_r)],
        },
    }


def fit_exponential_suppression(
    ds: List[int],
    eps_vals: List[float],
    n_shots_list: List[int],
) -> Dict[str, Any]:
    """
    Weighted log-linear fit to Google Willow / Fowler exponential scaling:
      eps(d) = A * Lambda^(-(d + 1) / 2)
      ln(eps) = ln(A) - ((d + 1) / 2) * ln(Lambda)
    Detects saturated above-threshold states (eps >= 0.70 combined) cleanly as Lambda < 1.
    """
    # If all points are fully saturated at maximally mixed state (~0.75), strictly above threshold
    if all(e >= 0.70 for e in eps_vals):
        return {"Lambda": 0.0, "Lambda_ci95": [0.0, 0.0], "A": float(eps_vals[0]), "below_threshold": False, "saturated": True, "r2_weighted": 0.0}

    x_arr = []
    y_arr = []
    w_arr = []
    for d, eps, nsh in zip(ds, eps_vals, n_shots_list):
        eps_use = min(max(eps, 0.5 / max(nsh, 1000)), 0.75)
        x_arr.append((d + 1.0) / 2.0)
        y_arr.append(math.log(eps_use))
        var_log = (1.0 - min(eps_use, 0.99)) / max(nsh * eps_use, 0.5)
        w_arr.append(1.0 / max(var_log, 1e-4))

    if len(x_arr) < 2:
        return {"Lambda": 0.0, "Lambda_ci95": [0.0, 0.0], "A": 1.0, "below_threshold": False, "saturated": False, "r2_weighted": 0.0}

    x = np.array(x_arr, dtype=np.float64)
    y = np.array(y_arr, dtype=np.float64)
    w = np.array(w_arr, dtype=np.float64)

    W = np.sum(w)
    mx = np.sum(w * x) / W
    my = np.sum(w * y) / W
    cov = np.sum(w * (x - mx) * (y - my))
    varx = np.sum(w * (x - mx) ** 2)
    slope = cov / max(varx, 1e-12)
    intercept = my - slope * mx

    lam = math.exp(-slope)
    A = math.exp(intercept)
    y_pred = intercept + slope * x
    ss_res = float(np.sum(w * (y - y_pred) ** 2))
    ss_tot = float(np.sum(w * (y - my) ** 2))
    r2 = 1.0 - ss_res / max(ss_tot, 1e-12)
    dof = max(len(x) - 2, 1)
    se_slope = math.sqrt(max(ss_res / dof, 1e-6) / max(varx, 1e-12))
    lam_lo = math.exp(-(slope + 1.96 * se_slope))
    lam_hi = math.exp(-(slope - 1.96 * se_slope))

    return {
        "Lambda": float(lam),
        "Lambda_ci95": [float(lam_lo), float(lam_hi)],
        "A": float(A),
        "below_threshold": bool(lam > 1.0),
        "saturated": False,
        "r2_weighted": float(r2),
    }


def estimate_threshold_crossing(
    p_grid: List[float],
    curves_by_d: Dict[int, List[float]],
) -> Dict[str, Any]:
    """
    Estimate circuit-level threshold p_2q,th from distance-pair crossings
    scanning BACKWARDS from the above-threshold side (p_max) to locate the true
    sustained transition where eps(d_hi) crosses below eps(d_lo) (immune to
    single-point low-p Poisson fluctuations).
    """
    pair_crossings: Dict[str, Optional[float]] = {}
    valid_vals: List[float] = []
    ds_sorted = sorted(curves_by_d.keys())

    def _find_sustained_crossing(y_lo: List[float], y_hi: List[float]) -> Optional[float]:
        for k in range(len(p_grid) - 2, -1, -1):
            da = math.log(max(y_hi[k], 1e-6)) - math.log(max(y_lo[k], 1e-6))
            db = math.log(max(y_hi[k + 1], 1e-6)) - math.log(max(y_lo[k + 1], 1e-6))
            if da <= 0.0 and db >= 0.0 and (db - da) > 1e-9:
                frac = -da / (db - da)
                return float(p_grid[k] + frac * (p_grid[k + 1] - p_grid[k]))
        return None

    for i in range(len(ds_sorted) - 1):
        d1, d2 = ds_sorted[i], ds_sorted[i + 1]
        cross = _find_sustained_crossing(curves_by_d[d1], curves_by_d[d2])
        pair_crossings[f"d{d1}_d{d2}"] = cross
        if cross is not None:
            valid_vals.append(cross)

    d_lo, d_hi = ds_sorted[0], ds_sorted[-1]
    span_cross = _find_sustained_crossing(curves_by_d[d_lo], curves_by_d[d_hi])
    pair_crossings[f"d{d_lo}_d{d_hi}"] = span_cross
    if span_cross is not None:
        valid_vals.append(span_cross)

    mean_th = float(np.mean(valid_vals)) if valid_vals else None
    std_th = float(np.std(valid_vals)) if len(valid_vals) >= 2 else 0.0
    return {
        "p_2q_th": mean_th,
        "p_2q_th_std": std_th,
        "pair_crossings": pair_crossings,
    }


def compute_machine_scaling_table(
    fit_round: Dict[str, Any],
    n_cand: int,
    cryo_nom_cells: int,
    cryo_max_cells: int,
    n_logical_system: int = 100,
    deff_ratio: float = 1.0,
) -> Dict[str, Any]:
    """
    Given exponential suppression fit eps_L_round(d) = A * Lambda^(-(d+1)/2),
    compute minimum odd distance d*, active cells N_active = 2 d*^2 - 1,
    placed candidate cells N_phys_per_logical = N_cand * N_active,
    single-cryostat logical qubit capacity, and modular LD400/PT420 cryostats
    for `n_logical_system` logical qubits across eps_L in {1e-6, 1e-9, 1e-12}.
    """
    lam = float(fit_round["Lambda"])
    A = float(fit_round["A"])
    if lam <= 1.001:
        return {"feasible": False, "Lambda": lam, "targets": {}}

    targets_out: Dict[str, Any] = {}
    for label, eps_target in (("1e-6", 1e-6), ("1e-9", 1e-9), ("1e-12", 1e-12)):
        # Find smallest odd d >= 3 such that A * lam^(-(d_eff + 1)/2) <= eps_target
        d_star = 3
        while d_star < 199:
            d_eff = d_star * deff_ratio
            pred_round = A * (lam ** (-(d_eff + 1.0) / 2.0))
            if pred_round <= eps_target:
                break
            d_star += 2

        # Also find d*_block such that d-round block error d * pred_round <= eps_target
        d_star_block = d_star
        while d_star_block < 199:
            d_eff_b = d_star_block * deff_ratio
            pred_r_b = A * (lam ** (-(d_eff_b + 1.0) / 2.0))
            pred_blk = 1.0 - (1.0 - min(pred_r_b, 0.499)) ** d_star_block
            if pred_blk <= eps_target:
                break
            d_star_block += 2

        n_active = 2 * d_star * d_star - 1
        n_phys = n_cand * n_active
        n_active_block = 2 * d_star_block * d_star_block - 1
        n_phys_block = n_cand * n_active_block

        # Unsplit logical patches per single LD400/PT420 cryostat
        log_per_nom = cryo_nom_cells // n_active
        log_per_max = cryo_max_cells // n_active
        cryos_100L_unsplit = (
            math.ceil(n_logical_system / log_per_max)
            if log_per_max >= 1
            else math.ceil((n_logical_system * n_active) / cryo_max_cells)
        )
        cryos_100L_thermal_lb = math.ceil((n_logical_system * n_active) / cryo_max_cells)
        cryos_100L_nom1024 = (
            math.ceil(n_logical_system / log_per_nom)
            if log_per_nom >= 1
            else math.ceil((n_logical_system * n_active) / cryo_nom_cells)
        )

        targets_out[label] = {
            "eps_L_target": eps_target,
            "d_star": int(d_star),
            "d_star_block": int(d_star_block),
            "N_cand": int(n_cand),
            "N_active": int(n_active),
            "N_phys_per_logical": int(n_phys),
            "N_active_block": int(n_active_block),
            "N_phys_per_logical_block": int(n_phys_block),
            "pred_eps_L_round_at_d_star": float(A * (lam ** (-(d_star * deff_ratio + 1.0) / 2.0))),
            "logical_per_cryo_1024_nominal": int(log_per_nom),
            "logical_per_cryo_2887_max": int(log_per_max),
            "total_active_cells_100L": int(n_logical_system * n_active),
            "total_placed_candidates_100L": int(n_logical_system * n_phys),
            "cryostats_100L_unsplit_2887": int(cryos_100L_unsplit),
            "cryostats_100L_thermal_lb_2887": int(cryos_100L_thermal_lb),
            "cryostats_100L_nominal_1024": int(cryos_100L_nom1024),
        }

    return {
        "feasible": True,
        "Lambda": lam,
        "A": A,
        "N_cand": int(n_cand),
        "deff_ratio_applied": float(deff_ratio),
        "targets": targets_out,
    }


# ---------------------------------------------------------------------------
# 4. Main Experiment Pipeline
# ---------------------------------------------------------------------------

def scan_portability() -> List[str]:
    """Scan all Exp138 code/results/tests for forbidden hardcoded user paths."""
    import re
    patterns = (re.compile(r"/(?:home|run/media)/[a-zA-Z0-9_-]+"),)
    hits: List[str] = []
    targets = [
        REPO_ROOT / "experiments" / "exp138_defective_surface_code_ft",
        RESULTS_DIR,
        REPO_ROOT / "tests" / "test_exp138.py",
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


def run_exp138() -> Dict[str, Any]:
    t_start = time.time()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    predictions = json.loads((RESULTS_DIR / "predictions_exp138.json").read_text())
    anchors = load_upstream_anchors()

    p_1q = anchors["exp126"]["p_1q"]
    p_meas = anchors["exp140"]["p_meas_2us"]
    p_meas_3us = anchors["exp140"]["p_meas_3us"]
    p_idle_f10 = anchors["derived_idle"]["p_idle_Z_f10"]
    p_idle_f15 = anchors["derived_idle"]["p_idle_Z_f15"]

    p4_ch = anchors["exp137"]["part4_channels"]
    tpl_P1 = p4_ch["P1_Bare_1f_S1p0"]["pauli_16"]
    tpl_S1p0 = p4_ch["best_protocol_S1p0"]["pauli_16"]
    tpl_S0p5 = p4_ch["best_protocol_S0p5"]["pauli_16"]
    tpl_S0p25 = p4_ch["best_protocol_S0p25"]["pauli_16"]

    print("[Exp138] Step 1: Exact Rotated Surface Code Algebra Verification (d=3,5,7,9,11)...")
    algebra_checks: Dict[str, Any] = {}
    all_algebra_exact = True
    for d in (3, 5, 7, 9, 11):
        code = build_rotated_surface_code(d)
        df0 = apply_site_dropouts(code, set())
        p16_test = normalize_and_scale_pauli16(tpl_S0p25, 0.008)
        dem_z = compile_ideal_circuit_dem(code, d, p16_test, p_1q, p_meas, p_idle_f15, 0.0, "Z")
        dem_x = compile_ideal_circuit_dem(code, d, p16_test, p_1q, p_meas, p_idle_f15, 0.0, "X")
        # Exact unweighted circuit distance d_circ
        Gz = nx.Graph()
        for (u, v) in dem_z.graph_edges:
            Gz.add_edge(u, v)
        Gx = nx.Graph()
        for (u, v) in dem_x.graph_edges:
            Gx.add_edge(u, v)
        d_circ_z = int(nx.shortest_path_length(Gz, dem_z.bnd_a, dem_z.bnd_b))
        d_circ_x = int(nx.shortest_path_length(Gx, dem_x.bnd_a, dem_x.bnd_b))
        ok_d = (
            code.n_total == 2 * d * d - 1
            and df0.commutes_exact
            and df0.d_eff == d
            and d_circ_z == d
            and d_circ_x == d
            and dem_z.non_graphlike_count == 0
            and dem_x.non_graphlike_count == 0
        )
        all_algebra_exact = all_algebra_exact and ok_d
        algebra_checks[f"d{d}"] = {
            "d": d,
            "n_data": code.n_data,
            "n_z_stabs": code.n_z,
            "n_x_stabs": code.n_x,
            "n_total": code.n_total,
            "commutes_exact": True,
            "d_eff_ideal": df0.d_eff,
            "d_circ_Z": d_circ_z,
            "d_circ_X": d_circ_x,
            "non_graphlike_Z": dem_z.non_graphlike_count,
            "non_graphlike_X": dem_x.non_graphlike_count,
            "ok": ok_d,
        }
    print(f"  Algebra checks all_exact={all_algebra_exact}")

    # -----------------------------------------------------------------------
    # Build Parallel Task List for Part 1 (Threshold Sweep) & Part 2 (Scenarios)
    # -----------------------------------------------------------------------
    n_workers = min(os.cpu_count() or 4, 8)
    print(f"[Exp138] Step 2: Queueing parallel circuit-level MWPM jobs on {n_workers} CPU workers...")

    p_sweep_grid = [0.004, 0.006, 0.008, 0.010, 0.012, 0.014, 0.016, 0.018, 0.020, 0.024]
    sweep_ds = [3, 5, 7, 9]

    # Scenario definitions anchored 100% to Exp137 / Exp139 / Exp140 / Exp136 / Exp126
    e137_a = anchors["exp137"]
    scenarios_cfg: Dict[str, Dict[str, Any]] = {
        "A_v4_Bare_P1_S1p0_Q2e5": {
            "label": "Scenario A: v4.0 Bare P1 (S=1.0, Q=2e5, 6-pair)",
            "p_2q": float(p4_ch["P1_Bare_1f_S1p0"]["p_total_err"]),
            "p_leak": float(p4_ch["P1_Bare_1f_S1p0"]["p_leak"]),
            "F_avg": float(p4_ch["P1_Bare_1f_S1p0"]["F_avg"]),
            "q_r": 200000.0,
            "s_eps_uev": 1.0,
            "template": tpl_P1,
            "ds": [3, 5, 7],
            "p_meas": p_meas,
            "p_idle_Z": p_idle_f10,
        },
        "B1_v5_Unpass_P4_S1p0_6pair_Q2e5": {
            "label": "Scenario B1: v5.0 Unpassivated P4 (S=1.0, Q=2e5, 6-pair)",
            "p_2q": float(p4_ch["best_protocol_S1p0"]["p_total_err"]),
            "p_leak": float(p4_ch["best_protocol_S1p0"]["p_leak"]),
            "F_avg": float(p4_ch["best_protocol_S1p0"]["F_avg"]),
            "q_r": 200000.0,
            "s_eps_uev": 1.0,
            "template": tpl_S1p0,
            "ds": [3, 5, 7],
            "p_meas": p_meas,
            "p_idle_Z": p_idle_f15,
        },
        "B2_v5_Unpass_P4_S1p0_fast_Q2e5": {
            "label": "Scenario B2: v5.0 Unpassivated P4 (S=1.0, Q=2e5, fast pairs)",
            "p_2q": float(e137_a["phase_points_Q2e5_S1p00"]["p_total_err"]),
            "p_leak": float(e137_a["phase_points_Q2e5_S1p00"]["p_leak"]),
            "F_avg": float(e137_a["phase_points_Q2e5_S1p00"]["F_avg"]),
            "q_r": 200000.0,
            "s_eps_uev": 1.0,
            "template": tpl_S1p0,
            "ds": [3, 5, 7],
            "p_meas": p_meas,
            "p_idle_Z": p_idle_f15,
        },
        "C1_v5_RotaC_P4_S0p50_6pair_Q2e5": {
            "label": "Scenario C1: v5.0 Rota C P4 (S=0.50, Q=2e5, 6-pair)",
            "p_2q": float(p4_ch["best_protocol_S0p5"]["p_total_err"]),
            "p_leak": float(p4_ch["best_protocol_S0p5"]["p_leak"]),
            "F_avg": float(p4_ch["best_protocol_S0p5"]["F_avg"]),
            "q_r": 200000.0,
            "s_eps_uev": 0.50,
            "template": tpl_S0p5,
            "ds": [3, 5, 7],
            "p_meas": p_meas,
            "p_idle_Z": p_idle_f15,
        },
        "C2_v5_RotaC_P4_S0p39_fast_Q2e5": {
            "label": "Scenario C2: v5.0 Rota C Nominal P4 (S=0.390, Q=2e5, fast)",
            "p_2q": float(e137_a["interp_route_c"]["Q2e5"]["p_total_err"]),
            "p_leak": float(e137_a["interp_route_c"]["Q2e5"]["p_leak"]),
            "F_avg": float(e137_a["interp_route_c"]["Q2e5"]["F_avg"]),
            "q_r": 200000.0,
            "s_eps_uev": float(anchors["exp139"]["s_eps_route_c_uev"]),
            "template": tpl_S0p5,
            "ds": [3, 5, 7, 9, 11],
            "p_meas": p_meas,
            "p_idle_Z": p_idle_f15,
        },
        "C3_v5_RotaC_P4_S0p25_fast_Q2e5": {
            "label": "Scenario C3: v5.0 Rota C Best-Band P4 (S=0.25, Q=2e5, fast)",
            "p_2q": float(e137_a["phase_points_Q2e5_S0p25"]["p_total_err"]),
            "p_leak": float(e137_a["phase_points_Q2e5_S0p25"]["p_leak"]),
            "F_avg": float(e137_a["phase_points_Q2e5_S0p25"]["F_avg"]),
            "q_r": 200000.0,
            "s_eps_uev": 0.25,
            "template": tpl_S0p25,
            "ds": [3, 5, 7, 9, 11],
            "p_meas": p_meas,
            "p_idle_Z": p_idle_f15,
        },
        "D1_v5_RotaC_P4_S0p39_fast_Q5e5": {
            "label": "Scenario D1: v5.0 Rota C Nominal P4 (S=0.390, Q=5e5, fast)",
            "p_2q": float(e137_a["interp_route_c"]["Q5e5"]["p_total_err"]),
            "p_leak": float(e137_a["interp_route_c"]["Q5e5"]["p_leak"]),
            "F_avg": float(e137_a["interp_route_c"]["Q5e5"]["F_avg"]),
            "q_r": 500000.0,
            "s_eps_uev": float(anchors["exp139"]["s_eps_route_c_uev"]),
            "template": tpl_S0p5,
            "ds": [3, 5, 7, 9, 11],
            "p_meas": p_meas,
            "p_idle_Z": p_idle_f15,
        },
        "D2_v5_RotaC_P4_S0p25_fast_Q5e5": {
            "label": "Scenario D2: v5.0 Rota C High-Q P4 (S=0.25, Q=5e5, fast)",
            "p_2q": float(e137_a["phase_points_Q5e5_S0p25"]["p_total_err"]),
            "p_leak": float(e137_a["phase_points_Q5e5_S0p25"]["p_leak"]),
            "F_avg": float(e137_a["phase_points_Q5e5_S0p25"]["F_avg"]),
            "q_r": 500000.0,
            "s_eps_uev": 0.25,
            "template": tpl_S0p25,
            "ds": [3, 5, 7, 9, 11],
            "p_meas": p_meas,
            "p_idle_Z": p_idle_f15,
        },
        "D2_LRU_sensitivity_Q5e5_S0p25": {
            "label": "Scenario D2 + LRU Leakage Penalty (p_2q + p_leak = 0.00958)",
            "p_2q": float(e137_a["phase_points_Q5e5_S0p25"]["p_total_err"]),
            "p_leak": float(e137_a["phase_points_Q5e5_S0p25"]["p_leak"]),
            "p_leak_extra": float(e137_a["phase_points_Q5e5_S0p25"]["p_leak"]),
            "F_avg": float(e137_a["phase_points_Q5e5_S0p25"]["F_avg"]),
            "q_r": 500000.0,
            "s_eps_uev": 0.25,
            "template": tpl_S0p25,
            "ds": [3, 5, 7, 9],
            "p_meas": p_meas,
            "p_idle_Z": p_idle_f15,
        },
        "D2_RO3us_sensitivity_Q5e5_S0p25": {
            "label": "Scenario D2 + Exp140 Optimal 3us RO (p_meas=0.002232)",
            "p_2q": float(e137_a["phase_points_Q5e5_S0p25"]["p_total_err"]),
            "p_leak": float(e137_a["phase_points_Q5e5_S0p25"]["p_leak"]),
            "F_avg": float(e137_a["phase_points_Q5e5_S0p25"]["F_avg"]),
            "q_r": 500000.0,
            "s_eps_uev": 0.25,
            "template": tpl_S0p25,
            "ds": [3, 5, 7, 9],
            "p_meas": p_meas_3us,
            "p_idle_Z": p_idle_f15,
        },
        "D3_Target_FT_P4_p0p005": {
            "label": "Scenario D3 (Target): Deep-FT Next-Gen M4 Bus (p_2q=0.0050, F_avg=99.60%)",
            "p_2q": 0.0050,
            "p_leak": 0.00015,
            "F_avg": 0.9960,
            "q_r": 1000000.0,
            "s_eps_uev": 0.15,
            "template": tpl_S0p25,
            "ds": [3, 5, 7, 9, 11],
            "p_meas": p_meas,
            "p_idle_Z": p_idle_f15,
        },
    }

    ideal_tasks: List[Dict[str, Any]] = []
    seed_counter = 138000

    # Part 1 threshold sweep tasks
    for p2q in p_sweep_grid:
        p16 = normalize_and_scale_pauli16(tpl_S0p25, p2q, symmetrize_qubits=True)
        for d in sweep_ds:
            n_sh = 2500 if d <= 7 else 2000
            for basis in ("Z", "X"):
                seed_counter += 1
                ideal_tasks.append({
                    "tag": f"sweep|{p2q:.4f}|d{d}|{basis}",
                    "d": d,
                    "basis": basis,
                    "pauli16": p16,
                    "p_1q": p_1q,
                    "p_meas": p_meas,
                    "p_idle_Z": p_idle_f15,
                    "n_shots": n_sh,
                    "seed": seed_counter,
                })

    # Part 2 scenario tasks (high precision: 3000 shots for d<=7, 2000 for d=9,11; 3500 for D3 d=7,9)
    for sc_key, sc in scenarios_cfg.items():
        p16 = normalize_and_scale_pauli16(
            sc["template"],
            sc["p_2q"],
            p_leak_lru_extra=float(sc.get("p_leak_extra", 0.0)),
            symmetrize_qubits=True,
        )
        for d in sc["ds"]:
            if sc_key == "D3_Target_FT_P4_p0p005":
                n_sh = 4000 if d <= 9 else 2500
            elif sc_key.startswith(("A_", "B")):
                n_sh = 2000
            else:
                n_sh = 3000 if d <= 7 else 2000
            for basis in ("Z", "X"):
                seed_counter += 1
                ideal_tasks.append({
                    "tag": f"scen|{sc_key}|d{d}|{basis}",
                    "d": d,
                    "basis": basis,
                    "pauli16": p16,
                    "p_1q": p_1q,
                    "p_meas": sc["p_meas"],
                    "p_idle_Z": sc["p_idle_Z"],
                    "n_shots": n_sh,
                    "seed": seed_counter,
                })

    # Part 3 defective/missing-cell super-stabilizer tasks
    p_ff = anchors["exp139"]["p_ff_route_c"]
    fnr = anchors["exp132"]["boed_fnr"]
    regimes = {
        "f1p0_Ez0": {
            "label": "f=1.0% 29Si (Ez=0, Exp136 P_yield=0.5275)",
            "P_yield": anchors["exp136"]["f10_yield"],
            "p_idle_Z": p_idle_f10,
            "p_slot_with_boed": anchors["exp136"]["f10_yield"] * p_ff * (1.0 - fnr),
            "p_slot_ideal_spec": anchors["exp136"]["f10_yield"] * p_ff,
        },
        "f1p5_Stark2MVm": {
            "label": "f*=1.5% 29Si + 2 MV/m Stark (Exp136 P_yield=0.7750)",
            "P_yield": anchors["exp136"]["f15_yield_stark2"],
            "p_idle_Z": p_idle_f15,
            "p_slot_with_boed": anchors["exp136"]["f15_yield_stark2"] * p_ff * (1.0 - fnr),
            "p_slot_ideal_spec": anchors["exp136"]["f15_yield_stark2"] * p_ff,
        },
    }

    p16_D2 = normalize_and_scale_pauli16(
        tpl_S0p25, scenarios_cfg["D2_v5_RotaC_P4_S0p25_fast_Q5e5"]["p_2q"], symmetrize_qubits=True
    )
    p16_D3 = normalize_and_scale_pauli16(tpl_S0p25, 0.0050, symmetrize_qubits=True)

    defect_tasks: List[Dict[str, Any]] = []
    for r_key, reg in regimes.items():
        for n_cand in (1, 3, 6, 8):
            p_drop = (1.0 - reg["p_slot_with_boed"]) ** n_cand
            for d in (5, 7, 9):
                # Decode circuit-level DEM on d=5,7 for D2 (p_2q=0.0092); geometry on all d=5,7,9
                n_dec = 25 if d in (5, 7) else 0
                sh_lat = 120 if d in (5, 7) else 0  # 25 * 120 = 3000 shots per basis!
                seed_counter += 1
                defect_tasks.append({
                    "tag": f"def|{r_key}|N{n_cand}|d{d}|D2",
                    "d": d,
                    "p_drop": p_drop,
                    "n_geom": 200,
                    "n_decode_lattices": n_dec,
                    "shots_per_lattice": sh_lat,
                    "pauli16": p16_D2,
                    "p_1q": p_1q,
                    "p_meas": p_meas,
                    "p_idle_Z": reg["p_idle_Z"],
                    "seed": seed_counter,
                })
            # Also decode d=7 under deep-FT D3 (p_2q=0.0050) for N_cand=3,6
            if n_cand in (3, 6):
                seed_counter += 1
                defect_tasks.append({
                    "tag": f"def|{r_key}|N{n_cand}|d7|D3",
                    "d": 7,
                    "p_drop": p_drop,
                    "n_geom": 100,
                    "n_decode_lattices": 25,
                    "shots_per_lattice": 120,
                    "pauli16": p16_D3,
                    "p_1q": p_1q,
                    "p_meas": p_meas,
                    "p_idle_Z": reg["p_idle_Z"],
                    "seed": seed_counter,
                })

    # Also evaluate BOED ideal FNR=0 comparison at d=7, N_cand=6 (f=1.0%)
    for r_key, reg in regimes.items():
        p_drop_no_fnr = (1.0 - reg["p_slot_ideal_spec"]) ** 6
        seed_counter += 1
        defect_tasks.append({
            "tag": f"boed0|{r_key}|N6|d7|D2",
            "d": 7,
            "p_drop": p_drop_no_fnr,
            "n_geom": 200,
            "n_decode_lattices": 25,
            "shots_per_lattice": 120,
            "pauli16": p16_D2,
            "p_1q": p_1q,
            "p_meas": p_meas,
            "p_idle_Z": reg["p_idle_Z"],
            "seed": seed_counter,
        })

    # Defective threshold shift mini-sweep at p_drop = 1.31% (f=1%, N_cand=6) for d=5,7
    p_drop_f1_N6 = (1.0 - regimes["f1p0_Ez0"]["p_slot_with_boed"]) ** 6
    def_th_grid = [0.006, 0.009, 0.012, 0.015, 0.018]
    for p2q in def_th_grid:
        p16_sw = normalize_and_scale_pauli16(tpl_S0p25, p2q, symmetrize_qubits=True)
        for d in (5, 7):
            seed_counter += 1
            defect_tasks.append({
                "tag": f"defth|{p2q:.4f}|d{d}",
                "d": d,
                "p_drop": p_drop_f1_N6,
                "n_geom": 25,
                "n_decode_lattices": 25,
                "shots_per_lattice": 100,  # 2500 shots per basis
                "pauli16": p16_sw,
                "p_1q": p_1q,
                "p_meas": p_meas,
                "p_idle_Z": p_idle_f10,
                "seed": seed_counter,
            })

    print(f"  Running {len(ideal_tasks)} ideal MWPM jobs + {len(defect_tasks)} defective super-stabilizer jobs...")
    t_pool = time.time()
    ideal_results: Dict[str, Dict[str, Any]] = {}
    defect_results: Dict[str, Dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        futs_ideal = [pool.submit(_worker_ideal_point, t) for t in ideal_tasks]
        futs_def = [pool.submit(_worker_defective_batch, t) for t in defect_tasks]
        for f in futs_ideal:
            r = f.result()
            ideal_results[r["tag"]] = r
        for f in futs_def:
            r = f.result()
            defect_results[r["tag"]] = r
    print(f"  All Monte Carlo & super-stabilizer jobs completed in {time.time() - t_pool:.1f}s!")

    # -----------------------------------------------------------------------
    # Assemble Part 1: Threshold Sweep & Exact Crossings
    # -----------------------------------------------------------------------
    part1_points: List[Dict[str, Any]] = []
    curves_comb_round: Dict[int, List[float]] = {d: [] for d in sweep_ds}
    curves_comb_block: Dict[int, List[float]] = {d: [] for d in sweep_ds}
    curves_z_round: Dict[int, List[float]] = {d: [] for d in sweep_ds}
    curves_x_round: Dict[int, List[float]] = {d: [] for d in sweep_ds}
    combined_bound_holds = True
    min_shots_seen = 10**9

    for p2q in p_sweep_grid:
        pt_entry: Dict[str, Any] = {"p_2q": p2q, "F_avg_equiv": 1.0 - 0.8 * p2q, "by_d": {}}
        for d in sweep_ds:
            rz = ideal_results[f"sweep|{p2q:.4f}|d{d}|Z"]
            rx = ideal_results[f"sweep|{p2q:.4f}|d{d}|X"]
            min_shots_seen = min(min_shots_seen, rz["n_shots"], rx["n_shots"])
            comb = combine_zx_results(rz, rx)
            if comb["combined"]["eps_L_block"] + 1e-12 < max(rz["eps_L_block"], rx["eps_L_block"]):
                combined_bound_holds = False
            pt_entry["by_d"][f"d{d}"] = comb
            curves_comb_round[d].append(comb["combined"]["eps_L_round"])
            curves_comb_block[d].append(comb["combined"]["eps_L_block"])
            curves_z_round[d].append(rz["eps_L_round"])
            curves_x_round[d].append(rx["eps_L_round"])
        part1_points.append(pt_entry)

    th_comb_round = estimate_threshold_crossing(p_sweep_grid, curves_comb_round)
    th_comb_block = estimate_threshold_crossing(p_sweep_grid, curves_comb_block)
    th_z_round = estimate_threshold_crossing(p_sweep_grid, curves_z_round)
    th_x_round = estimate_threshold_crossing(p_sweep_grid, curves_x_round)

    print(
        f"  [Part 1] Threshold p_2q,th (per-round): combined={th_comb_round['p_2q_th']:.4f} "
        f"(Z-mem={th_z_round['p_2q_th']:.4f}, X-mem={th_x_round['p_2q_th']:.4f}) | "
        f"d-round block={th_comb_block['p_2q_th']:.4f}"
    )

    # -----------------------------------------------------------------------
    # Assemble Part 2: Scenarios A, B, C, D & D_target
    # -----------------------------------------------------------------------
    part2_scenarios: Dict[str, Any] = {}
    for sc_key, sc in scenarios_cfg.items():
        by_d: Dict[str, Any] = {}
        ds_list = sc["ds"]
        eps_r_list, eps_b_list, nsh_list = [], [], []
        eps_z_r_list, eps_x_r_list = [], []
        for d in ds_list:
            rz = ideal_results[f"scen|{sc_key}|d{d}|Z"]
            rx = ideal_results[f"scen|{sc_key}|d{d}|X"]
            min_shots_seen = min(min_shots_seen, rz["n_shots"], rx["n_shots"])
            comb = combine_zx_results(rz, rx)
            if comb["combined"]["eps_L_block"] + 1e-12 < max(rz["eps_L_block"], rx["eps_L_block"]):
                combined_bound_holds = False
            by_d[f"d{d}"] = comb
            eps_r_list.append(comb["combined"]["eps_L_round"])
            eps_b_list.append(comb["combined"]["eps_L_block"])
            eps_z_r_list.append(rz["eps_L_round"])
            eps_x_r_list.append(rx["eps_L_round"])
            nsh_list.append(min(rz["n_shots"], rx["n_shots"]))

        fit_round = fit_exponential_suppression(ds_list, eps_r_list, nsh_list)
        fit_block = fit_exponential_suppression(ds_list, eps_b_list, nsh_list)
        fit_z_round = fit_exponential_suppression(ds_list, eps_z_r_list, nsh_list)
        fit_x_round = fit_exponential_suppression(ds_list, eps_x_r_list, nsh_list)

        part2_scenarios[sc_key] = {
            "label": sc["label"],
            "p_2q": sc["p_2q"],
            "p_leak": sc["p_leak"],
            "p_leak_extra_lru": float(sc.get("p_leak_extra", 0.0)),
            "F_avg": sc["F_avg"],
            "q_r": sc["q_r"],
            "s_eps_uev": sc["s_eps_uev"],
            "p_meas": sc["p_meas"],
            "p_idle_Z": sc["p_idle_Z"],
            "by_d": by_d,
            "fit_per_round": fit_round,
            "fit_d_round_block": fit_block,
            "fit_Z_memory_per_round": fit_z_round,
            "fit_X_memory_per_round": fit_x_round,
        }
        print(
            f"  [Part 2] {sc_key:34s} p2q={sc['p_2q']:.4f} | "
            f"Lam_rnd={fit_round['Lambda']:.3f} (blk={fit_block['Lambda']:.3f}) | "
            f"eps_rnd(d3)={eps_r_list[0]:.4f} -> eps_rnd(d{ds_list[-1]})={eps_r_list[-1]:.5f}"
        )

    # -----------------------------------------------------------------------
    # Assemble Part 3: Defective Super-Stabilizer & BOED FNR Study
    # -----------------------------------------------------------------------
    all_superstab_commute = True
    part3_regimes: Dict[str, Any] = {}
    rep_patch_saved: Optional[Dict[str, Any]] = None

    for r_key, reg in regimes.items():
        by_ncand: Dict[str, Any] = {}
        for n_cand in (1, 3, 6, 8):
            p_drop = (1.0 - reg["p_slot_with_boed"]) ** n_cand
            p_drop_ideal = (1.0 - reg["p_slot_ideal_spec"]) ** n_cand
            entry: Dict[str, Any] = {
                "N_cand": n_cand,
                "p_drop_with_boed": float(p_drop),
                "p_drop_ideal_spec": float(p_drop_ideal),
                "boed_fnr_delta_p_drop": float(p_drop - p_drop_ideal),
                "by_d": {},
            }
            for d in (5, 7, 9):
                dr = defect_results[f"def|{r_key}|N{n_cand}|d{d}|D2"]
                if not dr["commutes_all_exact"]:
                    all_superstab_commute = False
                if rep_patch_saved is None and r_key == "f1p0_Ez0" and n_cand == 6 and d == 7 and dr["representative_patch"] is not None:
                    rep_patch_saved = dr["representative_patch"]
                dr_clean = {k: v for k, v in dr.items() if k != "representative_patch"}
                entry["by_d"][f"d{d}"] = dr_clean
            if n_cand in (3, 6):
                dr3 = defect_results[f"def|{r_key}|N{n_cand}|d7|D3"]
                if not dr3["commutes_all_exact"]:
                    all_superstab_commute = False
                entry["d7_D3_target_decode"] = {k: v for k, v in dr3.items() if k != "representative_patch"}
            by_ncand[f"N{n_cand}"] = entry

        # BOED FNR=0 comparison at N_cand=6, d=7
        dr_boed0 = defect_results[f"boed0|{r_key}|N6|d7|D2"]
        dr_boed1 = defect_results[f"def|{r_key}|N6|d7|D2"]
        if not dr_boed0["commutes_all_exact"]:
            all_superstab_commute = False

        part3_regimes[r_key] = {
            "label": reg["label"],
            "P_yield": reg["P_yield"],
            "p_ff": p_ff,
            "boed_fnr": fnr,
            "p_slot_with_boed": reg["p_slot_with_boed"],
            "p_slot_ideal_spec": reg["p_slot_ideal_spec"],
            "by_N_cand": by_ncand,
            "boed_fnr_audit_N6_d7": {
                "p_drop_FNR0": float(dr_boed0["p_drop"]),
                "p_drop_FNR_exp132": float(dr_boed1["p_drop"]),
                "delta_p_drop": float(dr_boed1["p_drop"] - dr_boed0["p_drop"]),
                "mean_d_eff_FNR0": dr_boed0["mean_d_eff"],
                "mean_d_eff_FNR_exp132": dr_boed1["mean_d_eff"],
                "delta_mean_d_eff": float(dr_boed1["mean_d_eff"] - dr_boed0["mean_d_eff"]),
                "eps_L_round_FNR0": dr_boed0["decoding"]["eps_L_combined_round"],
                "eps_L_round_FNR_exp132": dr_boed1["decoding"]["eps_L_combined_round"],
            },
        }

    # Defective threshold shift at f=1.0%, N_cand=6 (p_drop=1.31%)
    def_th_curves: Dict[int, List[float]] = {5: [], 7: []}
    def_th_points: List[Dict[str, Any]] = []
    for p2q in def_th_grid:
        r5 = defect_results[f"defth|{p2q:.4f}|d5"]
        r7 = defect_results[f"defth|{p2q:.4f}|d7"]
        if not (r5["commutes_all_exact"] and r7["commutes_all_exact"]):
            all_superstab_commute = False
        e5 = r5["decoding"]["eps_L_combined_round"]
        e7 = r7["decoding"]["eps_L_combined_round"]
        def_th_curves[5].append(e5)
        def_th_curves[7].append(e7)
        def_th_points.append({
            "p_2q": p2q,
            "d5_eps_round": e5,
            "d7_eps_round": e7,
            "d5_mean_d_eff": r5["mean_d_eff"],
            "d7_mean_d_eff": r7["mean_d_eff"],
        })
    th_def_f1_N6 = estimate_threshold_crossing(def_th_grid, def_th_curves)

    # -----------------------------------------------------------------------
    # Assemble Part 4: Machine Scaling & Exp141 Interface
    # -----------------------------------------------------------------------
    cryo_nom = anchors["exp140"]["nominal_module_cells"]
    cryo_max = anchors["exp140"]["single_cryostat_max_cells"]
    deff_ratio_f1_N6 = part3_regimes["f1p0_Ez0"]["by_N_cand"]["N6"]["by_d"]["d7"]["mean_d_eff_over_d"]
    deff_ratio_f15_N6 = part3_regimes["f1p5_Stark2MVm"]["by_N_cand"]["N6"]["by_d"]["d7"]["mean_d_eff_over_d"]
    deff_ratio_f15_N3 = part3_regimes["f1p5_Stark2MVm"]["by_N_cand"]["N3"]["by_d"]["d7"]["mean_d_eff_over_d"]

    scaling_scenarios: Dict[str, Any] = {}
    for sc_key in (
        "C2_v5_RotaC_P4_S0p39_fast_Q2e5",
        "C3_v5_RotaC_P4_S0p25_fast_Q2e5",
        "D1_v5_RotaC_P4_S0p39_fast_Q5e5",
        "D2_v5_RotaC_P4_S0p25_fast_Q5e5",
        "D3_Target_FT_P4_p0p005",
    ):
        fit_r = part2_scenarios[sc_key]["fit_per_round"]
        scaling_scenarios[sc_key] = {
            "ideal_N6_f1p5": compute_machine_scaling_table(
                fit_r, n_cand=6, cryo_nom_cells=cryo_nom, cryo_max_cells=cryo_max, deff_ratio=deff_ratio_f15_N6
            ),
            "compact_N3_f1p5": compute_machine_scaling_table(
                fit_r, n_cand=3, cryo_nom_cells=cryo_nom, cryo_max_cells=cryo_max, deff_ratio=deff_ratio_f15_N3
            ),
            "baseline_N6_f1p0_defective": compute_machine_scaling_table(
                fit_r, n_cand=6, cryo_nom_cells=cryo_nom, cryo_max_cells=cryo_max, deff_ratio=deff_ratio_f1_N6
            ),
        }

    # Primary Exp141 top-level interface: Scenario D2 (v5.0 Rota C High-Q P4, Q=5e5, S=0.25, f*=1.5%+2MV/m, N_cand=6)
    primary_scaling_key = "D2_v5_RotaC_P4_S0p25_fast_Q5e5"
    primary_scaling = scaling_scenarios[primary_scaling_key]["ideal_N6_f1p5"]
    # Fallback to D3 if D2 unexpectedly fails to produce finite targets
    if not primary_scaling.get("feasible"):
        primary_scaling_key = "D3_Target_FT_P4_p0p005"
        primary_scaling = scaling_scenarios[primary_scaling_key]["ideal_N6_f1p5"]

    target_logical_error_rates = primary_scaling["targets"]

    # -----------------------------------------------------------------------
    # Assemble Part 5: Pre-Registered FT1–FT7 Honest Verdicts
    # -----------------------------------------------------------------------
    p_th_comb = th_comb_round["p_2q_th"]
    p_th_z = th_z_round["p_2q_th"]
    p_th_x = th_x_round["p_2q_th"]

    # FT1
    ft1_pass = bool(all_algebra_exact and p_th_comb is not None and 0.0070 <= p_th_comb <= 0.0200)

    # FT2: Scenarios A, B1, B2 strictly above threshold (Lambda_round < 1.0 and eps_block(d7) > eps_block(d3))
    def _is_above_th(sc_name: str) -> bool:
        sc_d = part2_scenarios[sc_name]
        lam_r = sc_d["fit_per_round"]["Lambda"]
        e3 = sc_d["by_d"]["d3"]["combined"]["eps_L_block"]
        e7 = sc_d["by_d"]["d7"]["combined"]["eps_L_block"]
        return bool(lam_r < 1.0 and e7 > e3)

    sc_A_above = _is_above_th("A_v4_Bare_P1_S1p0_Q2e5")
    sc_B1_above = _is_above_th("B1_v5_Unpass_P4_S1p0_6pair_Q2e5")
    sc_B2_above = _is_above_th("B2_v5_Unpass_P4_S1p0_fast_Q2e5")
    ft2_pass = bool(sc_A_above and sc_B1_above and sc_B2_above)

    # FT3: Scenario D2 (Q=5e5, S=0.25) crosses below threshold (Lambda_round > 1.15, eps_round(d11) < eps_round(d3))
    #      AND D3_target (p_2q=0.0050) achieves Lambda_round >= 2.0
    d2_sc = part2_scenarios["D2_v5_RotaC_P4_S0p25_fast_Q5e5"]
    d3_sc = part2_scenarios["D3_Target_FT_P4_p0p005"]
    d2_lam = d2_sc["fit_per_round"]["Lambda"]
    d2_e3 = d2_sc["by_d"]["d3"]["combined"]["eps_L_round"]
    d2_e11 = d2_sc["by_d"]["d11"]["combined"]["eps_L_round"]
    d3_lam = d3_sc["fit_per_round"]["Lambda"]
    ft3_pass = bool(d2_lam > 1.15 and d2_e11 < d2_e3 and d3_lam >= 2.0)

    # FT4: Exact Pauli-16 & memory basis consistency
    ft4_pass = bool(
        combined_bound_holds
        and p_th_z is not None
        and p_th_x is not None
        and p_th_z >= 0.90 * p_th_x
    )

    # FT5: Defective super-stabilizer & BOED FNR
    f1_N1_d7 = part3_regimes["f1p0_Ez0"]["by_N_cand"]["N1"]["by_d"]["d7"]
    f1_N3_d7 = part3_regimes["f1p0_Ez0"]["by_N_cand"]["N3"]["by_d"]["d7"]
    f1_N6_d7 = part3_regimes["f1p0_Ez0"]["by_N_cand"]["N6"]["by_d"]["d7"]
    f15_N3_d7 = part3_regimes["f1p5_Stark2MVm"]["by_N_cand"]["N3"]["by_d"]["d7"]
    f15_N6_d7 = part3_regimes["f1p5_Stark2MVm"]["by_N_cand"]["N6"]["by_d"]["d7"]
    boed_delta_N6 = part3_regimes["f1p0_Ez0"]["boed_fnr_audit_N6_d7"]["delta_p_drop"]

    ft5_checks = {
        "all_superstab_commute": all_superstab_commute,
        "f1_N1_broken": bool(f1_N1_d7["mean_d_eff"] < 2.0),
        "f1_N3_degraded": bool(f1_N3_d7["mean_d_eff_over_d"] < 0.85),
        "f1_N6_preserved": bool(f1_N6_d7["mean_d_eff_over_d"] >= 0.85 and f1_N6_d7["survival_prob"] >= 0.98),
        "f15_N3_preserved": bool(f15_N3_d7["mean_d_eff_over_d"] >= 0.85),
        "f15_N6_near_ideal": bool(f15_N6_d7["mean_d_eff_over_d"] >= 0.99),
        "boed_fnr_delta_pdrop_N6_lt_5e4": bool(boed_delta_N6 < 0.0005),
    }
    ft5_pass = all(ft5_checks.values())

    # FT6: Machine scaling & Exp141 interface
    has_targets = all(k in target_logical_error_rates for k in ("1e-6", "1e-9", "1e-12"))
    mono_ok = False
    if has_targets:
        t6, t9, t12 = (
            target_logical_error_rates["1e-6"],
            target_logical_error_rates["1e-9"],
            target_logical_error_rates["1e-12"],
        )
        mono_ok = (
            t6["d_star"] <= t9["d_star"] <= t12["d_star"]
            and t6["cryostats_100L_unsplit_2887"]
            <= t9["cryostats_100L_unsplit_2887"]
            <= t12["cryostats_100L_unsplit_2887"]
            and t12["d_star"] < 199
        )
    ft6_pass = bool(has_targets and mono_ok)

    # FT7: Precision & portability
    portability_hits = scan_portability()
    ft7_pass = bool(min_shots_seen >= 2000 and len(portability_hits) == 0)

    verdicts = {
        "FT1_ROTATED_CODE_ALGEBRA_AND_THRESHOLD": {
            "passed": ft1_pass,
            "all_algebra_exact": all_algebra_exact,
            "p_2q_th_per_round": p_th_comb,
            "p_2q_th_d_round_block": th_comb_block["p_2q_th"],
        },
        "FT2_HONEST_NEGATIVE_CONTROLS_V4_AND_UNPASSIVATED": {
            "passed": ft2_pass,
            "scenario_A_above_th": sc_A_above,
            "scenario_B1_6pair_above_th": sc_B1_above,
            "scenario_B2_fast_above_th": sc_B2_above,
        },
        "FT3_V5_ROTA_C_THRESHOLD_CROSSING_AND_QR_HEADROOM": {
            "passed": ft3_pass,
            "D2_S0p25_Q5e5_Lambda_round": d2_lam,
            "D2_S0p25_Q5e5_eps_round_d3": d2_e3,
            "D2_S0p25_Q5e5_eps_round_d11": d2_e11,
            "D2_S0p25_Q5e5_Lambda_block": d2_sc["fit_d_round_block"]["Lambda"],
            "D3_target_p0p005_Lambda_round": d3_lam,
        },
        "FT4_EXACT_PAULI16_AND_MEMORY_BASIS_CONSISTENCY": {
            "passed": ft4_pass,
            "combined_bound_holds": combined_bound_holds,
            "p_2q_th_Zmem": p_th_z,
            "p_2q_th_Xmem": p_th_x,
        },
        "FT5_DEFECTIVE_SUPER_STABILIZER_AND_BOED_FNR": {
            "passed": ft5_pass,
            "checks": ft5_checks,
            "f1_N1_d7_mean_d_eff": f1_N1_d7["mean_d_eff"],
            "f1_N3_d7_d_eff_over_d": f1_N3_d7["mean_d_eff_over_d"],
            "f1_N6_d7_d_eff_over_d": f1_N6_d7["mean_d_eff_over_d"],
            "f15_N3_d7_d_eff_over_d": f15_N3_d7["mean_d_eff_over_d"],
            "f15_N6_d7_d_eff_over_d": f15_N6_d7["mean_d_eff_over_d"],
            "boed_delta_pdrop_N6_f1": boed_delta_N6,
        },
        "FT6_MACHINE_SCALING_AND_EXP141_INTERFACE": {
            "passed": ft6_pass,
            "primary_scaling_scenario": primary_scaling_key,
            "has_targets": has_targets,
            "monotonic_ok": mono_ok,
        },
        "FT7_STATISTICAL_PRECISION_PORTABILITY_AND_TESTS": {
            "passed": ft7_pass,
            "min_shots_primary": min_shots_seen,
            "hardcoded_path_hits": len(portability_hits),
        },
    }

    n_passed = sum(1 for v in verdicts.values() if v["passed"])
    n_total = len(verdicts)
    elapsed_s = time.time() - t_start

    # Compact upstream summary (avoid dumping raw 20kB pauli tables twice)
    upstream_summary = {
        "exp136": anchors["exp136"],
        "exp139": anchors["exp139"],
        "exp140": anchors["exp140"],
        "exp132": anchors["exp132"],
        "exp126": anchors["exp126"],
        "derived_idle": anchors["derived_idle"],
        "exp137_interp_route_c": anchors["exp137"]["interp_route_c"],
    }

    out_json: Dict[str, Any] = {
        "experiment": "exp138_defective_surface_code_ft",
        "hypothesis_id": "H156",
        "date": "2026-11-23",
        "no_lab_measurement": True,
        "epistemic_tag": "{Sayısal-Simülasyon}",
        "elapsed_sec": float(elapsed_s),
        "n_workers": n_workers,
        "n_passed": int(n_passed),
        "n_total": int(n_total),
        "success_rule_met": bool(n_passed >= 5 and all_algebra_exact and all_superstab_commute and len(portability_hits) == 0),
        # Top-level Exp141-compatible keys (directly readable by wafer_econ141.evaluate_logical_qubit_economics!)
        "primary_scaling_scenario": primary_scaling_key,
        "N_cand": int(primary_scaling.get("N_cand", 6)),
        "Lambda": float(primary_scaling.get("Lambda", 0.0)),
        "target_logical_error_rates": target_logical_error_rates,
        "upstream_anchors": upstream_summary,
        "predictions": predictions,
        "verdicts": verdicts,
        "part1_algebra_and_threshold": {
            "algebra_checks": algebra_checks,
            "all_algebra_exact": all_algebra_exact,
            "p_2q_grid": p_sweep_grid,
            "distances": sweep_ds,
            "threshold_combined_per_round": th_comb_round,
            "threshold_combined_d_round_block": th_comb_block,
            "threshold_Z_memory_per_round": th_z_round,
            "threshold_X_memory_per_round": th_x_round,
            "points": part1_points,
        },
        "part2_scenarios": part2_scenarios,
        "part3_defective_superstabilizers": {
            "all_superstab_commute": all_superstab_commute,
            "regimes": part3_regimes,
            "defective_threshold_shift_f1_N6": {
                "p_drop": float(p_drop_f1_N6),
                "p_2q_grid": def_th_grid,
                "threshold_per_round": th_def_f1_N6,
                "ideal_threshold_per_round": th_comb_round["p_2q_th"],
                "points": def_th_points,
            },
            "representative_d7_patch": rep_patch_saved,
        },
        "part4_machine_scaling_scenarios": scaling_scenarios,
        "portability_hardcoded_hits": portability_hits,
    }

    out_path = RESULTS_DIR / "exp138.json"
    out_path.write_text(json.dumps(out_json, indent=2))
    print(f"\n[Exp138] DONE in {elapsed_s:.1f}s -> {out_path.relative_to(REPO_ROOT)}")
    print(f"[Exp138] Verdicts: {n_passed}/{n_total} PASS (success_rule_met={out_json['success_rule_met']})")
    for k, v in verdicts.items():
        print(f"  {'PASS' if v['passed'] else 'FAIL'} | {k}")
    return out_json


def reanalyze_existing_exp138() -> Dict[str, Any]:
    """
    Re-run exact per-round memory-decay inversion, sustained threshold crossing,
    machine scaling, and FT1-FT7 verdicts on the exact raw Monte Carlo counts
    already stored in exp138.json (zero change to sampled shots/fails!).
    """
    out_path = RESULTS_DIR / "exp138.json"
    data = json.loads(out_path.read_text())
    predictions = json.loads((RESULTS_DIR / "predictions_exp138.json").read_text())

    # 1. Re-invert Part 1 points using exact eps_block_to_round
    p1 = data["part1_algebra_and_threshold"]
    p_sweep_grid = p1["p_2q_grid"]
    sweep_ds = p1["distances"]
    curves_comb_round: Dict[int, List[float]] = {d: [] for d in sweep_ds}
    curves_comb_block: Dict[int, List[float]] = {d: [] for d in sweep_ds}
    curves_z_round: Dict[int, List[float]] = {d: [] for d in sweep_ds}
    curves_x_round: Dict[int, List[float]] = {d: [] for d in sweep_ds}
    combined_bound_holds = True
    min_shots_seen = 10**9

    for pt in p1["points"]:
        for d in sweep_ds:
            entry = pt["by_d"][f"d{d}"]
            rz = dict(entry["Z_memory"], d=d, rounds=entry["rounds"])
            rx = dict(entry["X_memory"], d=d, rounds=entry["rounds"])
            min_shots_seen = min(min_shots_seen, rz["n_shots"], rx["n_shots"])
            comb = combine_zx_results(rz, rx)
            if comb["combined"]["eps_L_block"] + 1e-12 < max(rz["eps_L_block"], rx["eps_L_block"]):
                combined_bound_holds = False
            pt["by_d"][f"d{d}"] = comb
            curves_comb_round[d].append(comb["combined"]["eps_L_round"])
            curves_comb_block[d].append(comb["combined"]["eps_L_block"])
            curves_z_round[d].append(comb["Z_memory"]["eps_L_round"])
            curves_x_round[d].append(comb["X_memory"]["eps_L_round"])

    th_comb_round = estimate_threshold_crossing(p_sweep_grid, curves_comb_round)
    th_comb_block = estimate_threshold_crossing(p_sweep_grid, curves_comb_block)
    th_z_round = estimate_threshold_crossing(p_sweep_grid, curves_z_round)
    th_x_round = estimate_threshold_crossing(p_sweep_grid, curves_x_round)
    p1["threshold_combined_per_round"] = th_comb_round
    p1["threshold_combined_d_round_block"] = th_comb_block
    p1["threshold_Z_memory_per_round"] = th_z_round
    p1["threshold_X_memory_per_round"] = th_x_round

    # 2. Re-invert Part 2 scenarios & refit exponential suppression
    p2 = data["part2_scenarios"]
    for sc_key, sc in p2.items():
        ds_list = sorted(int(k[1:]) for k in sc["by_d"].keys())
        eps_r_list, eps_b_list, eps_z_r_list, eps_x_r_list, nsh_list = [], [], [], [], []
        for d in ds_list:
            entry = sc["by_d"][f"d{d}"]
            rz = dict(entry["Z_memory"], d=d, rounds=entry["rounds"])
            rx = dict(entry["X_memory"], d=d, rounds=entry["rounds"])
            min_shots_seen = min(min_shots_seen, rz["n_shots"], rx["n_shots"])
            comb = combine_zx_results(rz, rx)
            if comb["combined"]["eps_L_block"] + 1e-12 < max(rz["eps_L_block"], rx["eps_L_block"]):
                combined_bound_holds = False
            sc["by_d"][f"d{d}"] = comb
            eps_r_list.append(comb["combined"]["eps_L_round"])
            eps_b_list.append(comb["combined"]["eps_L_block"])
            eps_z_r_list.append(comb["Z_memory"]["eps_L_round"])
            eps_x_r_list.append(comb["X_memory"]["eps_L_round"])
            nsh_list.append(min(rz["n_shots"], rx["n_shots"]))
        sc["fit_per_round"] = fit_exponential_suppression(ds_list, eps_r_list, nsh_list)
        sc["fit_d_round_block"] = fit_exponential_suppression(ds_list, eps_b_list, nsh_list)
        sc["fit_Z_memory_per_round"] = fit_exponential_suppression(ds_list, eps_z_r_list, nsh_list)
        sc["fit_X_memory_per_round"] = fit_exponential_suppression(ds_list, eps_x_r_list, nsh_list)

    # 3. Re-invert Part 3 defective decoding round rates
    p3 = data["part3_defective_superstabilizers"]
    for rk, reg in p3["regimes"].items():
        for nk, n_ent in reg["by_N_cand"].items():
            for dk, d_ent in n_ent["by_d"].items():
                if "decoding" in d_ent:
                    dec = d_ent["decoding"]
                    dd = int(d_ent["d"])
                    ez_r = eps_block_to_round(dec["eps_L_Z_block"], dd)
                    ex_r = eps_block_to_round(dec["eps_L_X_block"], dd)
                    dec["eps_L_combined_round"] = float(1.0 - (1.0 - ez_r) * (1.0 - ex_r))
            if "d7_D3_target_decode" in n_ent and "decoding" in n_ent["d7_D3_target_decode"]:
                dec = n_ent["d7_D3_target_decode"]["decoding"]
                ez_r = eps_block_to_round(dec["eps_L_Z_block"], 7)
                ex_r = eps_block_to_round(dec["eps_L_X_block"], 7)
                dec["eps_L_combined_round"] = float(1.0 - (1.0 - ez_r) * (1.0 - ex_r))
        reg["boed_fnr_audit_N6_d7"]["eps_L_round_FNR_exp132"] = reg["by_N_cand"]["N6"]["by_d"]["d7"]["decoding"]["eps_L_combined_round"]

    # Recompute defective threshold crossing from saved points
    def_th = p3["defective_threshold_shift_f1_N6"]
    def_th["ideal_threshold_per_round"] = th_comb_round["p_2q_th"]
    def_th["threshold_per_round"] = estimate_threshold_crossing(
        def_th["p_2q_grid"],
        {
            5: [pt["d5_eps_round"] for pt in def_th["points"]],
            7: [pt["d7_eps_round"] for pt in def_th["points"]],
        },
    )

    # 4. Recompute Part 4 machine scaling
    cryo_nom = int(data["upstream_anchors"]["exp140"]["nominal_module_cells"])
    cryo_max = int(data["upstream_anchors"]["exp140"]["single_cryostat_max_cells"])
    deff_ratio_f1_N6 = p3["regimes"]["f1p0_Ez0"]["by_N_cand"]["N6"]["by_d"]["d7"]["mean_d_eff_over_d"]
    deff_ratio_f15_N6 = p3["regimes"]["f1p5_Stark2MVm"]["by_N_cand"]["N6"]["by_d"]["d7"]["mean_d_eff_over_d"]
    deff_ratio_f15_N3 = p3["regimes"]["f1p5_Stark2MVm"]["by_N_cand"]["N3"]["by_d"]["d7"]["mean_d_eff_over_d"]

    scaling_scenarios: Dict[str, Any] = {}
    for sc_key in (
        "C2_v5_RotaC_P4_S0p39_fast_Q2e5",
        "C3_v5_RotaC_P4_S0p25_fast_Q2e5",
        "D1_v5_RotaC_P4_S0p39_fast_Q5e5",
        "D2_v5_RotaC_P4_S0p25_fast_Q5e5",
        "D3_Target_FT_P4_p0p005",
    ):
        fit_r = p2[sc_key]["fit_per_round"]
        scaling_scenarios[sc_key] = {
            "ideal_N6_f1p5": compute_machine_scaling_table(
                fit_r, n_cand=6, cryo_nom_cells=cryo_nom, cryo_max_cells=cryo_max, deff_ratio=deff_ratio_f15_N6
            ),
            "compact_N3_f1p5": compute_machine_scaling_table(
                fit_r, n_cand=3, cryo_nom_cells=cryo_nom, cryo_max_cells=cryo_max, deff_ratio=deff_ratio_f15_N3
            ),
            "baseline_N6_f1p0_defective": compute_machine_scaling_table(
                fit_r, n_cand=6, cryo_nom_cells=cryo_nom, cryo_max_cells=cryo_max, deff_ratio=deff_ratio_f1_N6
            ),
        }
    data["part4_machine_scaling_scenarios"] = scaling_scenarios
    primary_scaling_key = "D2_v5_RotaC_P4_S0p25_fast_Q5e5"
    primary_scaling = scaling_scenarios[primary_scaling_key]["ideal_N6_f1p5"]
    data["primary_scaling_scenario"] = primary_scaling_key
    data["N_cand"] = int(primary_scaling["N_cand"])
    data["Lambda"] = float(primary_scaling["Lambda"])
    data["target_logical_error_rates"] = primary_scaling["targets"]

    # 5. Re-evaluate pre-registered FT1-FT7 honestly (ZERO changes to sealed predictions!)
    p_th_comb = th_comb_round["p_2q_th"]
    p_th_z = th_z_round["p_2q_th"]
    p_th_x = th_x_round["p_2q_th"]
    all_algebra_exact = bool(p1["all_algebra_exact"])
    all_superstab_commute = bool(p3["all_superstab_commute"])

    ft1_pass = bool(all_algebra_exact and p_th_comb is not None and 0.0070 <= p_th_comb <= 0.0200)

    def _is_above_th(sc_name: str) -> bool:
        sc_d = p2[sc_name]
        lam_r = sc_d["fit_per_round"]["Lambda"]
        e3 = sc_d["by_d"]["d3"]["combined"]["eps_L_block"]
        e7 = sc_d["by_d"]["d7"]["combined"]["eps_L_block"]
        return bool(lam_r < 1.0 and e7 > e3)

    sc_A_above = _is_above_th("A_v4_Bare_P1_S1p0_Q2e5")
    sc_B1_above = _is_above_th("B1_v5_Unpass_P4_S1p0_6pair_Q2e5")
    sc_B2_above = _is_above_th("B2_v5_Unpass_P4_S1p0_fast_Q2e5")
    ft2_pass = bool(sc_A_above and sc_B1_above and sc_B2_above)

    d2_sc = p2["D2_v5_RotaC_P4_S0p25_fast_Q5e5"]
    d3_sc = p2["D3_Target_FT_P4_p0p005"]
    d2_lam = d2_sc["fit_per_round"]["Lambda"]
    d2_e3 = d2_sc["by_d"]["d3"]["combined"]["eps_L_round"]
    d2_e11 = d2_sc["by_d"]["d11"]["combined"]["eps_L_round"]
    d3_lam = d3_sc["fit_per_round"]["Lambda"]
    ft3_pass = bool(d2_lam > 1.15 and d2_e11 < d2_e3 and d3_lam >= 2.0)

    ft4_pass = bool(
        combined_bound_holds and p_th_z is not None and p_th_x is not None and p_th_z >= 0.90 * p_th_x
    )

    f1_N1_d7 = p3["regimes"]["f1p0_Ez0"]["by_N_cand"]["N1"]["by_d"]["d7"]
    f1_N3_d7 = p3["regimes"]["f1p0_Ez0"]["by_N_cand"]["N3"]["by_d"]["d7"]
    f1_N6_d7 = p3["regimes"]["f1p0_Ez0"]["by_N_cand"]["N6"]["by_d"]["d7"]
    f15_N3_d7 = p3["regimes"]["f1p5_Stark2MVm"]["by_N_cand"]["N3"]["by_d"]["d7"]
    f15_N6_d7 = p3["regimes"]["f1p5_Stark2MVm"]["by_N_cand"]["N6"]["by_d"]["d7"]
    boed_delta_N6 = p3["regimes"]["f1p0_Ez0"]["boed_fnr_audit_N6_d7"]["delta_p_drop"]
    ft5_checks = {
        "all_superstab_commute": all_superstab_commute,
        "f1_N1_broken": bool(f1_N1_d7["mean_d_eff"] < 2.0),
        "f1_N3_degraded": bool(f1_N3_d7["mean_d_eff_over_d"] < 0.85),
        "f1_N6_preserved": bool(f1_N6_d7["mean_d_eff_over_d"] >= 0.85 and f1_N6_d7["survival_prob"] >= 0.98),
        "f15_N3_preserved": bool(f15_N3_d7["mean_d_eff_over_d"] >= 0.85),
        "f15_N6_near_ideal": bool(f15_N6_d7["mean_d_eff_over_d"] >= 0.99),
        "boed_fnr_delta_pdrop_N6_lt_5e4": bool(boed_delta_N6 < 0.0005),
    }
    ft5_pass = all(ft5_checks.values())

    tgts = data["target_logical_error_rates"]
    has_targets = all(k in tgts for k in ("1e-6", "1e-9", "1e-12"))
    mono_ok = bool(
        has_targets
        and tgts["1e-6"]["d_star"] <= tgts["1e-9"]["d_star"] <= tgts["1e-12"]["d_star"]
        and tgts["1e-6"]["cryostats_100L_unsplit_2887"]
        <= tgts["1e-9"]["cryostats_100L_unsplit_2887"]
        <= tgts["1e-12"]["cryostats_100L_unsplit_2887"]
        and tgts["1e-12"]["d_star"] < 199
    )
    ft6_pass = bool(has_targets and mono_ok)

    portability_hits = scan_portability()
    ft7_pass = bool(min_shots_seen >= 2000 and len(portability_hits) == 0)

    verdicts = {
        "FT1_ROTATED_CODE_ALGEBRA_AND_THRESHOLD": {
            "passed": ft1_pass,
            "all_algebra_exact": all_algebra_exact,
            "p_2q_th_per_round": p_th_comb,
            "p_2q_th_d_round_block": th_comb_block["p_2q_th"],
        },
        "FT2_HONEST_NEGATIVE_CONTROLS_V4_AND_UNPASSIVATED": {
            "passed": ft2_pass,
            "scenario_A_above_th": sc_A_above,
            "scenario_B1_6pair_above_th": sc_B1_above,
            "scenario_B2_fast_above_th": sc_B2_above,
        },
        "FT3_V5_ROTA_C_THRESHOLD_CROSSING_AND_QR_HEADROOM": {
            "passed": ft3_pass,
            "D2_S0p25_Q5e5_Lambda_round": d2_lam,
            "D2_S0p25_Q5e5_eps_round_d3": d2_e3,
            "D2_S0p25_Q5e5_eps_round_d11": d2_e11,
            "D2_S0p25_Q5e5_Lambda_block": d2_sc["fit_d_round_block"]["Lambda"],
            "D3_target_p0p005_Lambda_round": d3_lam,
        },
        "FT4_EXACT_PAULI16_AND_MEMORY_BASIS_CONSISTENCY": {
            "passed": ft4_pass,
            "combined_bound_holds": combined_bound_holds,
            "p_2q_th_Zmem": p_th_z,
            "p_2q_th_Xmem": p_th_x,
        },
        "FT5_DEFECTIVE_SUPER_STABILIZER_AND_BOED_FNR": {
            "passed": ft5_pass,
            "checks": ft5_checks,
            "f1_N1_d7_mean_d_eff": f1_N1_d7["mean_d_eff"],
            "f1_N3_d7_d_eff_over_d": f1_N3_d7["mean_d_eff_over_d"],
            "f1_N6_d7_d_eff_over_d": f1_N6_d7["mean_d_eff_over_d"],
            "f15_N3_d7_d_eff_over_d": f15_N3_d7["mean_d_eff_over_d"],
            "f15_N6_d7_d_eff_over_d": f15_N6_d7["mean_d_eff_over_d"],
            "boed_delta_pdrop_N6_f1": boed_delta_N6,
        },
        "FT6_MACHINE_SCALING_AND_EXP141_INTERFACE": {
            "passed": ft6_pass,
            "primary_scaling_scenario": primary_scaling_key,
            "has_targets": has_targets,
            "monotonic_ok": mono_ok,
        },
        "FT7_STATISTICAL_PRECISION_PORTABILITY_AND_TESTS": {
            "passed": ft7_pass,
            "min_shots_primary": min_shots_seen,
            "hardcoded_path_hits": len(portability_hits),
        },
    }
    n_passed = sum(1 for v in verdicts.values() if v["passed"])
    data["predictions"] = predictions
    data["verdicts"] = verdicts
    data["n_passed"] = int(n_passed)
    data["n_total"] = len(verdicts)
    data["success_rule_met"] = bool(n_passed >= 5 and all_algebra_exact and all_superstab_commute and len(portability_hits) == 0)
    data["portability_hardcoded_hits"] = portability_hits

    out_path.write_text(json.dumps(data, indent=2))
    print(f"[Exp138 --reanalyze] Thresholds: comb={p_th_comb:.4f}, Z={p_th_z:.4f}, X={p_th_x:.4f}")
    print(f"[Exp138 --reanalyze] Verdicts: {n_passed}/{len(verdicts)} PASS (success_rule_met={data['success_rule_met']})")
    for k, v in verdicts.items():
        print(f"  {'PASS' if v['passed'] else 'FAIL'} | {k}")
    return data


if __name__ == "__main__":
    import sys
    if "--reanalyze" in sys.argv:
        reanalyze_existing_exp138()
    else:
        run_exp138()
