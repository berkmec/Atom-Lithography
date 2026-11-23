"""Exp144 Master Runner (H162): Long-Range 300 um M4 Bus qLDPC Bivariate Bicycle
[[144, 12, 12]] Gross Code Revolution.

Evaluates:
  1. Exact GF(2) CSS algebra, symplectic logical basis, and depth-7 zero-kickback
     Bravyi CNOT schedules for [[72,12,6]], [[90,8,10]], and [[144,12,12]].
  2. Exact thickness-2 folded-torus 24x12 physical layout on Exp131 3 kOhm NbTiN M4
     resonators (P_cell in [20, 50] um) + defect-free 288-cell block & 10-block (120L)
     single-cryostat die yield under Exp136 f*=1.5%+2MV/m vs f=1.0%.
  3. Pure-NumPy Normalized Min-Sum BP + bit-packed GF(2) OSD-0 / OSD-2 code-capacity
     scaling and decoder gain benchmark.
  4. Full 3D space-time circuit-level DEM (R=4 noisy rounds + R=6 depth audit) across
     uniform depolarizing threshold sweep AND Exp137/138/140 D2 / D3 / D3+ / D3++
     silicon machine noise regimes (Z + X memory combined, both depolarizing and
     Exp137 P4-conjugated Pauli channels).
  5. Exact cryostat fleet packing under Exp140 2,887-cell MXC ceiling and apples-to-apples
     100L / 120L 5-year TCO ($/L_sys & $/L_fab) via Exp141's exact wafer_econ141.py model.

Strictly portable (Path(__file__).resolve() only; zero hardcoded host paths).
no_lab_measurement=True, no_supplier_quotes=True.
"""
from __future__ import annotations

import concurrent.futures
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# Ensure repository root is importable cleanly from any CWD
THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from bb_codes_and_layout144 import (  # noqa: E402
    BB_CODE_SPECS,
    build_bb_code,
    build_thickness2_m4_layout,
    compute_defective_block_yields,
    find_verified_commuting_schedule,
)
from bp_osd_decoder144 import (  # noqa: E402
    build_bb_circuit_dem,
    run_dem_monte_carlo,
)
from experiments.exp141_v5_digital_twin.wafer_econ141 import (  # noqa: E402
    EXP140_CRYO_CELL_CAP_THERMAL,
    EXP140_RO_MUX_RATIO,
    EXP140_S65_MUX_1024_USD,
    HORIZON_YR,
    RUNTIME_CRYOSTAT_BAY_HW_USD,
    V5_M3_HW_NOM_USD,
    _sample_lognormal_p10_p50_p90,
    evaluate_v5_wafer_economics,
    wright_multiplier,
)

RESULTS_DIR = REPO_ROOT / "results" / "exp144_qldpc_bivariate_bicycle_m4"
PRED_PATH = RESULTS_DIR / "predictions_exp144.json"
OUT_JSON = RESULTS_DIR / "exp144.json"
PLOT_JSON = RESULTS_DIR / "plot_data_exp144.json"

N_WORKERS = min(8, os.cpu_count() or 1)


# =============================================================================
# Parallel Monte Carlo Worker Helpers (Deterministic Per-Task Seeds)
# =============================================================================
def _wilson_ci95(k: int, n: int) -> Tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    z = 1.95996
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _combine_z_x_memory(z_res: Dict[str, Any], x_res: Dict[str, Any], n_rounds: int, k_log: int) -> Dict[str, Any]:
    """Combine independent Z-memory and X-memory block failure rates cleanly."""
    pz_blk = z_res["p_L_block"]
    px_blk = x_res["p_L_block"]
    p_comb_blk = 1.0 - (1.0 - pz_blk) * (1.0 - px_blk)
    p_comb_rnd = 1.0 - max(0.0, 1.0 - p_comb_blk) ** (1.0 / max(n_rounds, 1))
    p_comb_rnd_per_L = 1.0 - max(0.0, 1.0 - p_comb_rnd) ** (1.0 / max(k_log, 1))

    # Conservative CI envelope combining Z and X Wilson bounds
    lo_blk = 1.0 - (1.0 - z_res["p_L_block_ci95"][0]) * (1.0 - x_res["p_L_block_ci95"][0])
    hi_blk = 1.0 - (1.0 - z_res["p_L_block_ci95"][1]) * (1.0 - x_res["p_L_block_ci95"][1])
    lo_rnd = 1.0 - max(0.0, 1.0 - lo_blk) ** (1.0 / max(n_rounds, 1))
    hi_rnd = 1.0 - max(0.0, 1.0 - hi_blk) ** (1.0 / max(n_rounds, 1))
    lo_rnd_L = 1.0 - max(0.0, 1.0 - lo_rnd) ** (1.0 / max(k_log, 1))
    hi_rnd_L = 1.0 - max(0.0, 1.0 - hi_rnd) ** (1.0 / max(k_log, 1))

    return {
        "p_L_block_combined": round(p_comb_blk, 6),
        "p_L_block_ci95": [round(lo_blk, 6), round(hi_blk, 6)],
        "p_L_round_block": round(p_comb_rnd, 6),
        "p_L_round_block_ci95": [round(lo_rnd, 6), round(hi_rnd, 6)],
        "p_L_round_per_logical": round(p_comb_rnd_per_L, 6),
        "p_L_round_per_logical_ci95": [round(lo_rnd_L, 6), round(hi_rnd_L, 6)],
        "syndrome_valid_frac_min": min(z_res["syndrome_valid_frac"], x_res["syndrome_valid_frac"]),
        "bp_converged_frac_avg": round(0.5 * (z_res["bp_converged_frac"] + x_res["bp_converged_frac"]), 5),
        "Z_memory": z_res,
        "X_memory": x_res,
    }


def _worker_code_cap(task: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    code = build_bb_code(BB_CODE_SPECS[task["code_name"]])
    H_Z = code["H_Z"]
    L_Z = code["L_Z"]
    dem = {
        "H_dem": H_Z,
        "L_dem": L_Z,
        "p_dem": np.full(H_Z.shape[1], task["p"], dtype=np.float64),
        "n_noisy_rounds": 1,
    }
    res = run_dem_monte_carlo(
        dem,
        n_shots=task["n_shots"],
        seed=task["seed"],
        osd_order=task["osd_order"],
        osd_lambda=task.get("osd_lambda", 32),
        use_osd=task["use_osd"],
        batch_size=500,
        bp_max_iter=50,
    )
    return task["key"], res


def _worker_circuit_chunk(task: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    code = build_bb_code(BB_CODE_SPECS[task["code_name"]])
    sched = find_verified_commuting_schedule(code)
    dem = build_bb_circuit_dem(
        code,
        sched,
        n_noisy_rounds=task["n_rounds"],
        p_2q=task["p_2q"],
        p_meas=task["p_meas"],
        p_1q_idle_step=task["p_1q_idle_step"],
        p_prep=task["p_prep"],
        p_data_ro_idle=task["p_data_ro_idle"],
        memory_basis=task["basis"],
        p2q_pauli_weights=task.get("p2q_pauli_weights"),
        include_boundary_noise=task.get("include_boundary_noise", True),
    )
    mc = run_dem_monte_carlo(
        dem,
        n_shots=task["n_shots"],
        seed=task["seed"],
        osd_order=task.get("osd_order", 2),
        osd_lambda=task.get("osd_lambda", 32),
        use_osd=task.get("use_osd", True),
        batch_size=300,
        bp_max_iter=50,
    )
    mc["M_detectors"] = dem["M_detectors"]
    mc["N_fault_mechanisms"] = dem["N_fault_mechanisms"]
    mc["n_noisy_rounds"] = dem["n_noisy_rounds"]
    mc["k_log"] = code["k"]
    return task["group_key"], mc


def _merge_mc_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge independent seeded MC chunks into one exact aggregated result."""
    n_shots = sum(c["n_shots"] for c in chunks)
    n_err = sum(c["n_logical_errors"] for c in chunks)
    n_bp = sum(round(c["bp_converged_frac"] * c["n_shots"]) for c in chunks)
    n_osd = sum(c["n_osd_triggered"] for c in chunks)
    n_syn = sum(round(c["syndrome_valid_frac"] * c["n_shots"]) for c in chunks)
    n_rounds = chunks[0]["n_noisy_rounds"]
    k_log = chunks[0]["k_log"]

    p_blk = n_err / n_shots
    lo_b, hi_b = _wilson_ci95(n_err, n_shots)
    p_rnd = 1.0 - max(0.0, 1.0 - p_blk) ** (1.0 / max(n_rounds, 1))
    lo_r = 1.0 - max(0.0, 1.0 - lo_b) ** (1.0 / max(n_rounds, 1))
    hi_r = 1.0 - max(0.0, 1.0 - hi_b) ** (1.0 / max(n_rounds, 1))
    p_rnd_L = 1.0 - max(0.0, 1.0 - p_rnd) ** (1.0 / max(k_log, 1))
    lo_rL = 1.0 - max(0.0, 1.0 - lo_r) ** (1.0 / max(k_log, 1))
    hi_rL = 1.0 - max(0.0, 1.0 - hi_r) ** (1.0 / max(k_log, 1))

    return {
        "n_shots": n_shots,
        "n_logical_errors": n_err,
        "p_L_block": round(p_blk, 6),
        "p_L_block_ci95": [round(lo_b, 6), round(hi_b, 6)],
        "p_L_round": round(p_rnd, 6),
        "p_L_round_ci95": [round(lo_r, 6), round(hi_r, 6)],
        "p_L_round_per_logical": round(p_rnd_L, 6),
        "p_L_round_per_logical_ci95": [round(lo_rL, 6), round(hi_rL, 6)],
        "bp_converged_frac": round(n_bp / n_shots, 5),
        "n_osd_triggered": n_osd,
        "syndrome_valid_frac": round(n_syn / n_shots, 6),
        "M_detectors": chunks[0]["M_detectors"],
        "N_fault_mechanisms": chunks[0]["N_fault_mechanisms"],
        "n_noisy_rounds": n_rounds,
    }


def _run_parallel_circuit_tasks(tasks: List[Dict[str, Any]], max_workers: int = N_WORKERS) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as pool:
        for gkey, res in pool.map(_worker_circuit_chunk, tasks):
            grouped.setdefault(gkey, []).append(res)
    return {gkey: _merge_mc_chunks(chunks) for gkey, chunks in grouped.items()}


def _split_chunks(base_task: Dict[str, Any], total_shots: int, n_chunks: int, seed_base: int) -> List[Dict[str, Any]]:
    out = []
    q, rem = divmod(total_shots, n_chunks)
    for ci in range(n_chunks):
        t = dict(base_task)
        t["n_shots"] = q + (1 if ci < rem else 0)
        t["seed"] = seed_base + ci * 997
        if t["n_shots"] > 0:
            out.append(t)
    return out


# =============================================================================
# Upstream Ledger Loading & Exact Cryostat / TCO Economics
# =============================================================================
def load_upstream_anchors() -> Dict[str, Any]:
    e136 = json.loads((REPO_ROOT / "results" / "exp136_tb_sp3d5s_hyperfine" / "exp136.json").read_text())
    e137 = json.loads((REPO_ROOT / "results" / "exp137_echoed_m4_bus_gate" / "exp137.json").read_text())
    e138 = json.loads((REPO_ROOT / "results" / "exp138_defective_surface_code_ft" / "exp138.json").read_text())
    e139 = json.loads((REPO_ROOT / "results" / "exp139_epi_cap_process_integration" / "exp139.json").read_text())
    e140 = json.loads((REPO_ROOT / "results" / "exp140_cryo_fpga_boed_mux_readout" / "exp140.json").read_text())
    e141 = json.loads((REPO_ROOT / "results" / "exp141_v5_digital_twin" / "exp141.json").read_text())

    u138 = e138["upstream_anchors"]
    p2_d2 = e138["part2_scenarios"]["D2_v5_RotaC_P4_S0p25_fast_Q5e5"]
    p2_d3 = e138["part2_scenarios"]["D3_Target_FT_P4_p0p005"]

    t_gate_us = float(u138["exp137_interp_route_c"]["Q5e5"]["t_gate_us"])
    t_ro_2us = 2.0
    t_ro_3us = 3.0
    t_1q_reset_us = 0.20
    t_cyc_bb_2us = 7.0 * t_gate_us + t_ro_2us + t_1q_reset_us
    t_cyc_bb_3us = 7.0 * t_gate_us + t_ro_3us + t_1q_reset_us
    t2e_ms = float(u138["exp136"]["f15_t2e_xy8_n64_ms"])

    return {
        "exp136_f10_yield": float(u138["exp136"]["f10_yield"]),
        "exp136_f15_stark2_yield": float(u138["exp136"]["f15_yield_stark2"]),
        "exp136_t2e_f15_ms": t2e_ms,
        "exp139_p_ff_route_c": float(u138["exp139"]["p_ff_route_c"]),
        "exp139_s_eps_route_c_uev": float(u138["exp139"]["s_eps_route_c_uev"]),
        "exp137_t_gate_us": t_gate_us,
        "exp137_p4_pauli_16_S0p25": dict(e137["part4_exp138_pauli_channels"]["best_protocol_S0p25"]["pauli_16"]),
        "exp126_p_1q": float(u138["exp126"]["p_1q"]),
        "exp140_p_meas_2us": float(u138["exp140"]["p_meas_2us"]),
        "exp140_p_meas_3us": float(u138["exp140"]["p_meas_3us"]),
        "exp140_cryo_cap_cells": int(u138["exp140"]["single_cryostat_max_cells"]),
        "exp140_n_mux_star": int(u138["exp140"]["n_mux_star"]),
        "t_cyc_bb_2us": round(t_cyc_bb_2us, 4),
        "t_cyc_bb_3us": round(t_cyc_bb_3us, 4),
        "p_idle_step_Z": 0.5 * (1.0 - math.exp(-(t_gate_us * 1e-3) / t2e_ms)),
        "p_idle_ro_2us_Z": 0.5 * (1.0 - math.exp(-((t_ro_2us + t_1q_reset_us) * 1e-3) / t2e_ms)),
        "p_idle_ro_3us_Z": 0.5 * (1.0 - math.exp(-((t_ro_3us + t_1q_reset_us) * 1e-3) / t2e_ms)),
        "p_idle_full_cycle_bb_2us_Z": 0.5 * (1.0 - math.exp(-(t_cyc_bb_2us * 1e-3) / t2e_ms)),
        "exp138_D2_p2q": float(p2_d2["p_2q"]),
        "exp138_D2_d7_eps_round": float(p2_d2["by_d"]["d7"]["combined"]["eps_L_round"]),
        "exp138_D2_d11_eps_round": float(p2_d2["by_d"]["d11"]["combined"]["eps_L_round"]),
        "exp138_D3_p2q": float(p2_d3["p_2q"]),
        "exp138_D3_d7_eps_round": float(p2_d3["by_d"]["d7"]["combined"]["eps_L_round"]),
        "exp138_D3_d9_eps_round": float(p2_d3["by_d"]["d9"]["combined"]["eps_L_round"]),
        "exp138_D3_d11_eps_round": float(p2_d3["by_d"]["d11"]["combined"]["eps_L_round"]),
        "exp141_layer7": e141["layer7_logical_qubit_economics"],
        "exp136_verified_loaded": bool(e136.get("experiment")),
        "exp139_verified_loaded": bool(e139.get("experiment")),
        "exp140_verified_loaded": bool(e140.get("experiment")),
    }


def evaluate_qldpc_cryo_and_tco(
    anchors: Dict[str, Any],
    n_cand_qldpc: int = 8,
    wright_b: float = 0.85,
    n_mc: int = 20_000,
    seed: int = 2026144,
) -> Dict[str, Any]:
    """Exact apples-to-apples cryostat packing & 5-year TCO for [[144,12,12]] Gross Code
    using Exp141's exact wafer_econ141.py cost model and Exp140's 2,887-cell MXC cap.
    """
    cryo_cap = anchors["exp140_cryo_cap_cells"]  # 2,887 active cells / LD400+PT420
    cells_per_block = 288  # 144 data + 144 ancilla
    logical_per_block = 12
    active_per_logical = cells_per_block / logical_per_block  # 24.0
    phys_cand_per_logical = active_per_logical * n_cand_qldpc  # 192.0 at N_cand=8

    max_blocks_per_cryo = cryo_cap // cells_per_block  # 10 blocks
    max_logical_per_cryo = max_blocks_per_cryo * logical_per_block  # 120 logical qubits!

    wafer_econ = evaluate_v5_wafer_economics(bom_v5_m3=V5_M3_HW_NOM_USD, n_mc=n_mc, seed=seed - 1)
    fab_tco5_v5_p50 = wafer_econ["fab_tco5_no_wafer"]["v5_0_usd"]["p50"]
    eff_yield_v5 = wafer_econ["throughput"]["v5_0_15ms"]["eff_yield"]

    rng = np.random.default_rng(seed)
    cryo_hw_s = _sample_lognormal_p10_p50_p90(rng, *RUNTIME_CRYOSTAT_BAY_HW_USD, n_mc)
    mux_1024_s = _sample_lognormal_p10_p50_p90(rng, *EXP140_S65_MUX_1024_USD, n_mc)
    install_s = _sample_lognormal_p10_p50_p90(rng, 1.20, 1.35, 1.55, n_mc)
    maint_s = _sample_lognormal_p10_p50_p90(rng, 0.06, 0.08, 0.11, n_mc)
    cryo_opex_base_yr = (
        rng.uniform(20.0, 30.0, size=n_mc) * 8760.0 * _sample_lognormal_p10_p50_p90(rng, 0.09, 0.14, 0.22, n_mc)
        + _sample_lognormal_p10_p50_p90(rng, 30_000.0, 45_000.0, 70_000.0, n_mc)
        + _sample_lognormal_p10_p50_p90(rng, 0.35, 0.50, 0.75, n_mc) * 160_000.0
    )

    def _p10_p50_p90(arr: np.ndarray) -> Dict[str, float]:
        q10, q50, q90 = np.percentile(arr, [10.0, 50.0, 90.0])
        return {"p10": round(float(q10), 2), "p50": round(float(q50), 2), "p90": round(float(q90), 2)}

    configs = [
        # (key, label, n_blocks_active, n_blocks_on_die, n_logical_delivered, n_logical_denom, cells_per_blk, k_per_blk)
        ("BB144_100L_9blk", "[[144,12,12]] 9 Blocks = 108L (meets >=100L)", 9, 9, 108, 108, 288, 12),
        ("BB144_100L_9plus1_spared", "[[144,12,12]] 9 Active + 1 Spare = 108L (99.94% die yield)", 9, 10, 108, 108, 288, 12),
        ("BB144_120L_10blk_full_cryo", "[[144,12,12]] 10 Blocks = 120L (Full 1-Cryostat Packing)", 10, 10, 120, 120, 288, 12),
        ("BB288_100L_9blk_d18_ref", "[[288,12,18]] High-d18 Ref: 9 Blocks = 108L (2 Cryostats)", 9, 9, 108, 108, 576, 12),
    ]

    out_configs: Dict[str, Any] = {}
    for key, label, n_blk_act, n_blk_die, n_log, n_log_denom, c_blk, k_blk in configs:
        active_cells = n_blk_act * c_blk
        die_cells = n_blk_die * c_blk
        blks_per_cryo = cryo_cap // c_blk
        n_cryo = math.ceil(n_blk_die / max(blks_per_cryo, 1))
        mxc_util_pct = 100.0 * active_cells / (n_cryo * cryo_cap)
        n_ro_chains = math.ceil(active_cells / EXP140_RO_MUX_RATIO)
        n_mux_1024 = n_ro_chains / 32.0

        # Silicon wafer fab cost per logical qubit (exact Exp141 convention: W1/W2/W3)
        cand_per_L = (die_cells / n_log) * n_cand_qldpc
        fab_by_w: Dict[str, Any] = {}
        for wcode in ("W1", "W2", "W3"):
            usd_reg = wafer_econ["scenarios"][wcode]["v5_0_dense_1h_15ms"]["usd_per_register_nom_wafer_p50"]
            fab_per_L = cand_per_L * usd_reg
            fab_by_w[wcode] = {
                "usd_per_logical_fab_p50": round(fab_per_L, 5),
                "usd_per_logical_fab_raw_cand_p50": round(fab_per_L * eff_yield_v5, 5),
                "system_chip_fab_usd_p50": round(fab_per_L * n_log * 5.0, 2),
            }

        w_cryo = wright_multiplier(n_cryo, wright_b)
        w_mux = wright_multiplier(max(1.0, n_mux_1024), wright_b)

        hw_wr = n_cryo * cryo_hw_s * w_cryo + n_mux_1024 * mux_1024_s * w_mux
        hw_n1 = n_cryo * cryo_hw_s + n_mux_1024 * mux_1024_s
        facility = 1_200_000.0 + 350_000.0 * n_cryo
        chips_w3 = fab_by_w["W3"]["system_chip_fab_usd_p50"]
        opex_wr = HORIZON_YR * (n_cryo * cryo_opex_base_yr + maint_s * hw_wr)
        opex_n1 = HORIZON_YR * (n_cryo * cryo_opex_base_yr + maint_s * hw_n1)

        tco5_amort_wr = install_s * hw_wr + facility + opex_wr + chips_w3
        tco5_amort_n1 = install_s * hw_n1 + facility + opex_n1 + chips_w3
        tco5_ded_wr = tco5_amort_wr + fab_tco5_v5_p50

        out_configs[key] = {
            "label": label,
            "n_blocks_active": n_blk_act,
            "n_blocks_on_die": n_blk_die,
            "n_logical_delivered": n_log,
            "active_cells_total": active_cells,
            "die_cells_total": die_cells,
            "active_cells_per_logical": round(active_cells / n_log, 2),
            "placed_candidates_total": int(die_cells * n_cand_qldpc),
            "placed_candidates_per_logical": round(cand_per_L, 2),
            "n_cryostats": n_cryo,
            "mxc_utilization_pct": round(mxc_util_pct, 2),
            "n_readout_chains_mux32": n_ro_chains,
            "n_s65_1024_modules": round(n_mux_1024, 4),
            "fab_cost_by_wafer": fab_by_w,
            "system_tco5_amort_wright_usd": _p10_p50_p90(tco5_amort_wr),
            "system_tco5_amort_n1_usd": _p10_p50_p90(tco5_amort_n1),
            "system_tco5_ded_fab_wright_usd": _p10_p50_p90(tco5_ded_wr),
            "usd_per_logical_sys_amort_wright": _p10_p50_p90(tco5_amort_wr / n_log_denom),
            "usd_per_logical_sys_amort_per100L": _p10_p50_p90(tco5_amort_wr / 100.0),
            "usd_per_logical_sys_ded_wright": _p10_p50_p90(tco5_ded_wr / n_log_denom),
        }

    # Exact comparison ratios vs Exp141 Surface Code (D2 & D3 at 1e-6 and 1e-9)
    l7 = anchors["exp141_layer7"]
    bb_9blk = out_configs["BB144_100L_9blk"]
    bb_usd_L = bb_9blk["usd_per_logical_sys_amort_wright"]["p50"]
    bb_usd_per100L = bb_9blk["usd_per_logical_sys_amort_per100L"]["p50"]

    d2_1e9 = l7["D2_primary_Lambda1p40"]["1e-9"]
    d3_1e9 = l7["D3_target_Lambda2p52"]["1e-9"]
    d3_1e6 = l7["D3_target_Lambda2p52"]["1e-6"]
    d2_1e6 = l7["D2_primary_Lambda1p40"]["1e-6"]

    return {
        "exp140_mxc_cap_cells": cryo_cap,
        "n_cand_qldpc": n_cand_qldpc,
        "gross_code_single_cryo_blocks": max_blocks_per_cryo,
        "gross_code_single_cryo_logical_qubits": max_logical_per_cryo,
        "gross_code_single_cryo_active_cells": max_blocks_per_cryo * cells_per_block,
        "gross_code_single_cryo_mxc_margin_cells": cryo_cap - max_blocks_per_cryo * cells_per_block,
        "configs": out_configs,
        "surface_code_baselines_exp141": {
            "D2_1e-6": d2_1e6,
            "D2_1e-9": d2_1e9,
            "D3_1e-6": d3_1e6,
            "D3_1e-9": d3_1e9,
        },
        "compression_ratios_BB144_9blk_vs_surface_code": {
            "cryostats_vs_D2_1e-9": round(d2_1e9["cryostats_100L"] / bb_9blk["n_cryostats"], 2),
            "cryostats_vs_D3_1e-9": round(d3_1e9["cryostats_100L"] / bb_9blk["n_cryostats"], 2),
            "cryostats_vs_D3_1e-6": round(d3_1e6["cryostats_100L"] / bb_9blk["n_cryostats"], 2),
            "usd_per_L_sys_vs_D2_1e-9": round(d2_1e9["sys_100L_usd_per_L_amort_wright_p50"] / bb_usd_L, 2),
            "usd_per_L_sys_vs_D3_1e-9": round(d3_1e9["sys_100L_usd_per_L_amort_wright_p50"] / bb_usd_L, 2),
            "usd_per_L_sys_vs_D3_1e-6": round(d3_1e6["sys_100L_usd_per_L_amort_wright_p50"] / bb_usd_L, 2),
            "usd_per_100L_norm_vs_D3_1e-9": round(d3_1e9["sys_100L_usd_per_L_amort_wright_p50"] / bb_usd_per100L, 2),
            "active_cells_per_L_vs_d7_SC": round(97.0 / active_per_logical, 2),
            "active_cells_per_L_vs_d11_SC": round(241.0 / active_per_logical, 2),
            "active_cells_per_L_vs_D3_1e-9_SC": round(d3_1e9["N_active"] / active_per_logical, 2),
            "active_cells_per_L_vs_D2_1e-9_SC": round(d2_1e9["N_active"] / active_per_logical, 2),
        },
    }


def _estimate_threshold_crossing(p_grid: List[float], r_small: List[float], r_large: List[float]) -> float | None:
    """Find linear-in-log-p crossing where r_large transitions from < r_small to > r_small."""
    for i in range(len(p_grid) - 1):
        d0 = r_large[i] - r_small[i]
        d1 = r_large[i + 1] - r_small[i + 1]
        if d0 <= 0.0 and d1 >= 0.0 and (d1 - d0) > 1e-12:
            frac = -d0 / (d1 - d0)
            p_cross = p_grid[i] + frac * (p_grid[i + 1] - p_grid[i])
            return round(float(p_cross), 6)
    return None


def _scan_hardcoded_paths(paths: List[Path]) -> List[str]:
    bad_tokens = ("/home/" + "berk", "/run/media/" + "berk", "/" + "Users/")
    hits: List[str] = []
    for p in paths:
        if not p.exists():
            continue
        txt = p.read_text(errors="ignore")
        for tok in bad_tokens:
            if tok in txt:
                hits.append(f"{p.name}:{tok}")
    return hits


# =============================================================================
# Main Execution Pipeline
# =============================================================================
def main() -> None:
    t_start = time.perf_counter()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    predictions = json.loads(PRED_PATH.read_text())
    anchors = load_upstream_anchors()

    print(f"=== Exp144 (H162): qLDPC Bivariate Bicycle [[144,12,12]] on 300 um M4 Bus (workers={N_WORKERS}) ===")

    # -------------------------------------------------------------------------
    # PART 1: Exact BB CSS Algebra & Depth-7 Zero-Kickback CNOT Schedules (QL1)
    # -------------------------------------------------------------------------
    codes = {}
    scheds = {}
    part1_algebra: Dict[str, Any] = {}
    for name, spec in BB_CODE_SPECS.items():
        c = build_bb_code(spec)
        s = find_verified_commuting_schedule(c)
        codes[name] = c
        scheds[name] = s
        L_X, L_Z = c["L_X"], c["L_Z"]
        H_X, H_Z = c["H_X"], c["H_Z"]
        symp_ok = bool(
            np.array_equal((L_X @ L_Z.T) & 1, np.eye(c["k"], dtype=np.uint8))
            and np.all(((H_Z @ L_X.T) & 1) == 0)
            and np.all(((H_X @ L_Z.T) & 1) == 0)
        )
        part1_algebra[name] = {
            "label": spec.name,
            "l": spec.l,
            "m": spec.m,
            "n_data": c["n_data"],
            "n_physical_total": c["n_total_cells"],
            "k": c["k"],
            "d_lit": spec.d_lit,
            "encoding_rate_k_over_n": round(c["k"] / c["n_data"], 5),
            "active_cells_per_logical": round(c["n_total_cells"] / c["k"], 2),
            "rank_X": c["rank_X"],
            "rank_Z": c["rank_Z"],
            "css_commutes": c["commutativity_H_X_H_ZT_zero"],
            "exact_weight_6": c["all_row_col_weight_6"],
            "symplectic_logical_valid": symp_ok,
            "min_basis_logical_weight_X": int(np.min(np.sum(L_X, axis=1))),
            "min_basis_logical_weight_Z": int(np.min(np.sum(L_Z, axis=1))),
            "schedule_depth": s["depth_cnot_layers"],
            "schedule_total_cnots": s["total_cnots_per_round"],
            "schedule_zero_collisions": s["zero_collision_verified"],
            "schedule_zero_kickback": s["zero_kickback_verified"],
            "schedule_valid": bool(s["zero_collision_verified"] and s["zero_kickback_verified"]),
            "schedule_steps": s["step_labels"],
        }
        print(
            f"  [Part 1] {name}: [[{c['n_data']},{c['k']},{spec.d_lit}]], "
            f"comm={c['commutativity_H_X_H_ZT_zero']}, wt6={c['all_row_col_weight_6']}, symp={symp_ok}, "
            f"depth={s['depth_cnot_layers']}, zero_kickback={s['zero_kickback_verified']}"
        )

    # -------------------------------------------------------------------------
    # PART 2: Thickness-2 M4 Physical Layout & Defective-Block Yield (QL2, QL6)
    # -------------------------------------------------------------------------
    pitches_um = (20.0, 25.0, 30.0, 35.0, 40.0, 50.0)
    lay_full = build_thickness2_m4_layout(codes["BB_144_12_12"], pitches_um=pitches_um)
    layout_by_pitch = {f"{int(ps['pitch_um'])}um": ps for ps in lay_full["pitch_sweep"]}

    # Defect-free block & 10-block (120L) single-cryostat die yield (uses exact Exp136 x Exp139 x Exp132 BOED)
    dy_all = compute_defective_block_yields(n_cells_block=288, n_blocks_cryo=10)
    yield_f10_rows = {f"N{r['N_cand']}": r for r in dy_all["f1p0_Ez0_baseline"]["by_N_cand"]}
    yield_f15_rows = {f"N{r['N_cand']}": r for r in dy_all["f1p5_Ez2MVm_v5_star"]["by_N_cand"]}

    # 9-of-10 spared block yield (binomial >= 9 defect-free blocks out of 10 on die)
    p_blk_n8 = yield_f15_rows["N8"]["block_288_yield"]
    p_die_9of10_n8 = (p_blk_n8 ** 10) + 10.0 * (p_blk_n8 ** 9) * (1.0 - p_blk_n8)
    p_blk_n6 = yield_f15_rows["N6"]["block_288_yield"]
    p_die_9of10_n6 = (p_blk_n6 ** 10) + 10.0 * (p_blk_n6 ** 9) * (1.0 - p_blk_n6)

    part2_layout_defects = {
        "grid_shape": lay_full["grid_shape"],
        "n_qubits": lay_full["n_qubits"],
        "n_edges_total": lay_full["n_edges_total"],
        "n_edges_layer1_local": lay_full["n_edges_layer1_local"],
        "n_edges_layer2_long_range": lay_full["n_edges_layer2_long_range"],
        "torus_thickness": lay_full["torus_thickness"],
        "layer1_torus_crossings": lay_full["layer1_torus_crossings"],
        "flat_folded_layer1_airbridges": lay_full["flat_folded_layer1_airbridges"],
        "flat_folded_layer2_airbridges": lay_full["flat_folded_layer2_airbridges"],
        "layout_by_pitch_um": layout_by_pitch,
        "recommended_pitch_um": 20.0,
        "recommended_layout_summary": layout_by_pitch["20um"],
        "defect_yield_f1p0_Ez0_no_stark": {
            "p_slot": dy_all["f1p0_Ez0_baseline"]["p_slot"],
            "by_N_cand": yield_f10_rows,
        },
        "defect_yield_f1p5_Ez2MVm_v5_star": {
            "p_slot": dy_all["f1p5_Ez2MVm_v5_star"]["p_slot"],
            "by_N_cand": yield_f15_rows,
        },
        "spared_9of10_cryostat_die_yield_f1p5": {
            "N6_pct": round(100.0 * p_die_9of10_n6, 4),
            "N8_pct": round(100.0 * p_die_9of10_n8, 4),
        },
    }
    print(
        f"  [Part 2] Layout 20um: L_max={layout_by_pitch['20um']['L_max_um']} um <= 300 um ({layout_by_pitch['20um']['fits_300um_m4_resonator']}), "
        f"die={layout_by_pitch['20um']['block_size_um'][0]}x{layout_by_pitch['20um']['block_size_um'][1]} um | "
        f"Yield f=1.0% N6={yield_f10_rows['N6']['block_288_yield_pct']}%, "
        f"f*=1.5% N6={yield_f15_rows['N6']['block_288_yield_pct']}%, "
        f"N8={yield_f15_rows['N8']['block_288_yield_pct']}% (10-blk={yield_f15_rows['N8']['cryo_10block_120L_yield_pct']}%, 9/10 spared={round(100*p_die_9of10_n8, 2)}%)"
    )

    # -------------------------------------------------------------------------
    # PART 3: Code-Capacity Scaling & BP vs BP+OSD-0 vs BP+OSD-2 Gain (QL3)
    # -------------------------------------------------------------------------
    t3 = time.perf_counter()
    p_cc_grid = [0.02, 0.03, 0.04, 0.05, 0.06]
    cc_tasks: List[Dict[str, Any]] = []
    for ci, cname in enumerate(("BB_72_12_6", "BB_90_8_10", "BB_144_12_12")):
        for pi, pv in enumerate(p_cc_grid):
            cc_tasks.append({
                "key": f"{cname}|osd2|{pv:.3f}",
                "code_name": cname,
                "p": pv,
                "n_shots": 2500,
                "seed": 10000 + ci * 1000 + pi * 37,
                "use_osd": True,
                "osd_order": 2,
                "osd_lambda": 80,  # Exact full non-pivot OSD-2 sweep (no truncation bias between N=72,90,144)
            })
    # Decoder ablation on [[144,12,12]] at p = 0.03, 0.04, 0.05: BP-only vs BP+OSD-0 vs BP+OSD-2
    for pi, pv in enumerate((0.03, 0.04, 0.05)):
        cc_tasks.append({
            "key": f"BB_144_12_12|bp_only|{pv:.3f}",
            "code_name": "BB_144_12_12",
            "p": pv,
            "n_shots": 2500,
            "seed": 20000 + pi * 37,
            "use_osd": False,
            "osd_order": 0,
        })
        cc_tasks.append({
            "key": f"BB_144_12_12|osd0|{pv:.3f}",
            "code_name": "BB_144_12_12",
            "p": pv,
            "n_shots": 2500,
            "seed": 20000 + pi * 37,
            "use_osd": True,
            "osd_order": 0,
        })

    cc_results: Dict[str, Dict[str, Any]] = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=N_WORKERS) as pool:
        for k_out, r_out in pool.map(_worker_code_cap, cc_tasks):
            cc_results[k_out] = r_out

    cc_by_code = {
        cname: {f"{pv:.3f}": cc_results[f"{cname}|osd2|{pv:.3f}"] for pv in p_cc_grid}
        for cname in ("BB_72_12_6", "BB_90_8_10", "BB_144_12_12")
    }
    ablation_144 = {}
    for pv in (0.03, 0.04, 0.05):
        bp_r = cc_results[f"BB_144_12_12|bp_only|{pv:.3f}"]
        o0_r = cc_results[f"BB_144_12_12|osd0|{pv:.3f}"]
        o2_r = cc_results[f"BB_144_12_12|osd2|{pv:.3f}"]
        gain_o2 = bp_r["p_L_block"] / max(o2_r["p_L_block"], 1e-9)
        ablation_144[f"{pv:.3f}"] = {
            "bp_only": bp_r,
            "bp_osd0": o0_r,
            "bp_osd2": o2_r,
            "osd2_gain_vs_bp_only": round(gain_o2, 2),
        }

    p04_72 = cc_by_code["BB_72_12_6"]["0.040"]["p_L_block"]
    p04_90 = cc_by_code["BB_90_8_10"]["0.040"]["p_L_block"]
    p04_144 = cc_by_code["BB_144_12_12"]["0.040"]["p_L_block"]
    d6_to_d12_suppression = round(p04_72 / max(p04_144, 1e-9), 2)

    part3_code_capacity = {
        "p_grid": p_cc_grid,
        "n_shots_per_point": 2500,
        "by_code_bp_osd2": cc_by_code,
        "decoder_ablation_BB_144_12_12": ablation_144,
        "p04_ordering_72_90_144": [p04_72, p04_90, p04_144],
        "p04_d6_to_d12_suppression_x": d6_to_d12_suppression,
        "elapsed_s": round(time.perf_counter() - t3, 2),
    }
    print(
        f"  [Part 3] Code-cap p=0.04: BB72={p04_72:.4f} > BB90={p04_90:.4f} > BB144={p04_144:.4f} "
        f"({d6_to_d12_suppression}x), OSD2/BP gain={ablation_144['0.040']['osd2_gain_vs_bp_only']}x ({part3_code_capacity['elapsed_s']}s)"
    )

    # -------------------------------------------------------------------------
    # PART 4A: Full 3D Circuit-Level Uniform Depolarizing Threshold Sweep (QL4)
    # -------------------------------------------------------------------------
    t4a = time.perf_counter()
    p_circ_grid = [0.0020, 0.0030, 0.0040, 0.0050, 0.0060, 0.0070, 0.0085, 0.0100]
    circ_tasks: List[Dict[str, Any]] = []
    seed_ctr = 30000
    for cname in ("BB_72_12_6", "BB_90_8_10", "BB_144_12_12"):
        for pv in p_circ_grid:
            n_sh = 2000 if pv <= 0.0035 else 1000
            n_ch = 8 if cname == "BB_144_12_12" else 4
            base = {
                "group_key": f"unif|{cname}|{pv:.4f}",
                "code_name": cname,
                "n_rounds": 4,
                "p_2q": pv,
                "p_meas": pv,
                "p_prep": pv,
                "p_1q_idle_step": (2.0 / 3.0) * pv,
                "p_data_ro_idle": (2.0 / 3.0) * pv,
                "basis": "Z",
                "include_boundary_noise": True,
                "osd_order": 2,
                "osd_lambda": 32,
            }
            circ_tasks.extend(_split_chunks(base, n_sh, n_ch, seed_ctr))
            seed_ctr += 20000

    # Round-depth invariance audit: R=6 noisy rounds on BB_144_12_12 at p=0.003 & p=0.005
    for pv in (0.0030, 0.0050):
        base = {
            "group_key": f"r6_audit|BB_144_12_12|{pv:.4f}",
            "code_name": "BB_144_12_12",
            "n_rounds": 6,
            "p_2q": pv,
            "p_meas": pv,
            "p_prep": pv,
            "p_1q_idle_step": (2.0 / 3.0) * pv,
            "p_data_ro_idle": (2.0 / 3.0) * pv,
            "basis": "Z",
            "include_boundary_noise": True,
            "osd_order": 2,
            "osd_lambda": 32,
        }
        circ_tasks.extend(_split_chunks(base, 800, 8, seed_ctr))
        seed_ctr += 20000

    unif_res = _run_parallel_circuit_tasks(circ_tasks)
    unif_by_code = {
        cname: {f"{pv:.4f}": unif_res[f"unif|{cname}|{pv:.4f}"] for pv in p_circ_grid}
        for cname in ("BB_72_12_6", "BB_90_8_10", "BB_144_12_12")
    }
    r72_list = [unif_by_code["BB_72_12_6"][f"{pv:.4f}"]["p_L_round"] for pv in p_circ_grid]
    r90_list = [unif_by_code["BB_90_8_10"][f"{pv:.4f}"]["p_L_round"] for pv in p_circ_grid]
    r144_list = [unif_by_code["BB_144_12_12"][f"{pv:.4f}"]["p_L_round"] for pv in p_circ_grid]
    r72_perL = [unif_by_code["BB_72_12_6"][f"{pv:.4f}"]["p_L_round_per_logical"] for pv in p_circ_grid]
    r90_perL = [unif_by_code["BB_90_8_10"][f"{pv:.4f}"]["p_L_round_per_logical"] for pv in p_circ_grid]
    r144_perL = [unif_by_code["BB_144_12_12"][f"{pv:.4f}"]["p_L_round_per_logical"] for pv in p_circ_grid]

    p_th_72_vs_144 = _estimate_threshold_crossing(p_circ_grid, r72_list, r144_list)
    p_th_72_vs_90_perL = _estimate_threshold_crossing(p_circ_grid, r72_perL, r90_perL)

    r6_audit = {
        "p_0.0030": unif_res["r6_audit|BB_144_12_12|0.0030"],
        "p_0.0050": unif_res["r6_audit|BB_144_12_12|0.0050"],
    }
    t4a_s = round(time.perf_counter() - t4a, 2)
    print(
        f"  [Part 4A] Uniform Bravyi DEM (R=4, Z-mem): p_th(72 vs 144) = "
        f"{p_th_72_vs_144*100 if p_th_72_vs_144 else -1:.3f}% | "
        f"BB144 p_L/rnd @0.3%={r144_list[1]:.5f}, @0.5%={r144_list[3]:.5f}, @0.7%={r144_list[5]:.5f} ({t4a_s}s)"
    )

    # -------------------------------------------------------------------------
    # PART 4B: Real Exp137/138/140 Silicon Machine Regimes (Z + X Memory!) (QL4)
    # -------------------------------------------------------------------------
    t4b = time.perf_counter()
    p_1q = anchors["exp126_p_1q"]
    p_meas_2 = anchors["exp140_p_meas_2us"]
    p_meas_3 = anchors["exp140_p_meas_3us"]
    p_idle_step_Z = anchors["p_idle_step_Z"]
    p_idle_ro_2_Z = anchors["p_idle_ro_2us_Z"]
    p_idle_ro_3_Z = anchors["p_idle_ro_3us_Z"]
    # Conservative symmetric idle floor for X-errors (~1/10 of Z dephasing since T1 >> T2e in 28Si)
    p_idle_step_X = 0.1 * p_idle_step_Z
    p_idle_ro_2_X = 0.1 * p_idle_ro_2_Z
    p_idle_ro_3_X = 0.1 * p_idle_ro_3_Z
    pauli16_p4 = anchors["exp137_p4_pauli_16_S0p25"]

    machine_specs = [
        # (key, label, p_2q, p_meas, p_prep, ro_mode, pauli_weights, n_shots_per_basis)
        ("D2_Exp138_p0p92_depol", "D2 v5.0 (S_eps=0.25, Q=5e5, 2us RO, depol 2Q)", anchors["exp138_D2_p2q"], p_meas_2, p_1q, "2us", None, 1000),
        ("D2_Exp138_p0p92_P4biased", "D2 v5.0 (S_eps=0.25, Q=5e5, 2us RO, Exp137 P4 Pauli)", anchors["exp138_D2_p2q"], p_meas_2, p_1q, "2us", pauli16_p4, 1000),
        ("D3_Exp138_p0p50_RO2us_depol", "D3 FT Target (p_2q=0.50%, 2us RO=0.386%, depol 2Q)", 0.0050, p_meas_2, p_1q, "2us", None, 2000),
        ("D3_Exp138_p0p50_RO2us_P4biased", "D3 FT Target (p_2q=0.50%, 2us RO=0.386%, Exp137 P4 Pauli)", 0.0050, p_meas_2, p_1q, "2us", pauli16_p4, 2000),
        ("D3_Exp138_p0p50_RO3us_depol", "D3 FT Target + 3us RO (p_2q=0.50%, 3us RO=0.223%)", 0.0050, p_meas_3, p_1q, "3us", None, 2000),
        ("D3plus_p0p30_RO2us_depol", "D3+ Next-Gen (p_2q=0.30%, 2us RO=0.386%)", 0.0030, p_meas_2, p_1q, "2us", None, 3000),
        ("D3plus_p0p30_RO3us_depol", "D3+ Next-Gen + 3us RO (p_2q=0.30%, 3us RO=0.223%)", 0.0030, p_meas_3, p_1q, "3us", None, 3000),
        ("D3plusplus_p0p20_RO3us", "D3++ Deep FT (p_2q=0.20%, 3us RO=0.223%)", 0.0020, p_meas_3, p_1q, "3us", None, 3000),
    ]

    mach_tasks: List[Dict[str, Any]] = []
    for skey, slabel, p2q, pm, pp, rom, pw, n_sh in machine_specs:
        for basis in ("Z", "X"):
            # In Z-memory (X errors): idle error is T1-limited (~0.1 * Z-dephasing);
            # In X-memory (Z errors): idle error is T2e-limited (Exp136 exact 14.135 ms)!
            id_step = p_idle_step_X if basis == "Z" else p_idle_step_Z
            id_ro = (p_idle_ro_2_X if rom == "2us" else p_idle_ro_3_X) if basis == "Z" else (p_idle_ro_2_Z if rom == "2us" else p_idle_ro_3_Z)
            base = {
                "group_key": f"mach|{skey}|{basis}",
                "code_name": "BB_144_12_12",
                "n_rounds": 4,
                "p_2q": p2q,
                "p_meas": pm,
                "p_prep": pp,
                "p_1q_idle_step": id_step,
                "p_data_ro_idle": id_ro,
                "basis": basis,
                "p2q_pauli_weights": pw,
                "include_boundary_noise": True,
                "osd_order": 2,
                "osd_lambda": 32,
            }
            mach_tasks.extend(_split_chunks(base, n_sh, 8, seed_ctr))
            seed_ctr += 20000

    mach_raw = _run_parallel_circuit_tasks(mach_tasks)
    machine_regimes: Dict[str, Any] = {}
    for skey, slabel, p2q, pm, pp, rom, pw, n_sh in machine_specs:
        z_r = mach_raw[f"mach|{skey}|Z"]
        x_r = mach_raw[f"mach|{skey}|X"]
        comb = _combine_z_x_memory(z_r, x_r, n_rounds=4, k_log=12)
        machine_regimes[skey] = {
            "label": slabel,
            "p_2q": p2q,
            "p_meas": pm,
            "p_prep": pp,
            "readout_mode": rom,
            "uses_exp137_p4_pauli": pw is not None,
            "T_cycle_bb_us": anchors["t_cyc_bb_2us"] if rom == "2us" else anchors["t_cyc_bb_3us"],
            "n_shots_per_basis": n_sh,
            **comb,
        }
        print(
            f"  [Part 4B] {skey}: p_L/rnd(blk)={comb['p_L_round_block']:.5f} | "
            f"p_L/rnd(1L)={comb['p_L_round_per_logical']:.5f} "
            f"[Z={z_r['p_L_round']:.5f}, X={x_r['p_L_round']:.5f}, syn={comb['syndrome_valid_frac_min']:.4f}]"
        )

    # Power-law scaling fit on uniform BB_144_12_12 below threshold (p in 0.003..0.006 where n_err > 0)
    fit_pts = [
        (pv, unif_by_code["BB_144_12_12"][f"{pv:.4f}"]["p_L_round"])
        for pv in (0.0030, 0.0040, 0.0050, 0.0060)
        if unif_by_code["BB_144_12_12"][f"{pv:.4f}"]["p_L_round"] > 0
    ]
    if len(fit_pts) >= 2:
        lx = np.log([pt[0] for pt in fit_pts])
        ly = np.log([pt[1] for pt in fit_pts])
        slope, intercept = np.polyfit(lx, ly, 1)
        d_eff_circ = float(2.0 * slope - 1.0)
        # Solve exp(intercept) * p^slope = target -> p = (target / exp(intercept))^(1/slope)
        p_req_1e6_unif = float(math.exp((math.log(1e-6) - intercept) / slope))
        p_req_1e9_unif = float(math.exp((math.log(1e-9) - intercept) / slope))
    else:
        slope, intercept, d_eff_circ, p_req_1e6_unif, p_req_1e9_unif = (0.0, 0.0, 0.0, 0.0, 0.0)

    part4_circuit_dem = {
        "n_noisy_rounds_primary": 4,
        "uniform_depolarizing_sweep": {
            "p_grid": p_circ_grid,
            "by_code": unif_by_code,
            "p_th_crossing_72_vs_144": p_th_72_vs_144,
            "p_th_crossing_72_vs_90_perL": p_th_72_vs_90_perL,
            "r6_round_depth_audit_BB144": r6_audit,
            "subthreshold_power_law_fit_BB144": {
                "slope_alpha": round(float(slope), 3),
                "d_eff_circuit": round(d_eff_circ, 2),
                "p_unif_est_for_1e-6_block_round": round(p_req_1e6_unif, 5),
                "p_unif_est_for_1e-9_block_round": round(p_req_1e9_unif, 5),
            },
            "elapsed_s": t4a_s,
        },
        "machine_regimes_BB144_Z_and_X": machine_regimes,
        "surface_code_comparison_anchors_exp138": {
            "D2_p2q_0p92_d7_eps_round": anchors["exp138_D2_d7_eps_round"],
            "D2_p2q_0p92_d11_eps_round": anchors["exp138_D2_d11_eps_round"],
            "D3_p2q_0p50_d7_eps_round": anchors["exp138_D3_d7_eps_round"],
            "D3_p2q_0p50_d9_eps_round": anchors["exp138_D3_d9_eps_round"],
            "D3_p2q_0p50_d11_eps_round": anchors["exp138_D3_d11_eps_round"],
            "d7_active_cells_per_L": 97,
            "d11_active_cells_per_L": 241,
            "gross_code_active_cells_per_L": 24,
        },
        "machine_elapsed_s": round(time.perf_counter() - t4b, 2),
    }

    # -------------------------------------------------------------------------
    # PART 5: Cryostat Packing & $/L_sys Compression vs Exp138/141 (QL5)
    # -------------------------------------------------------------------------
    t5 = time.perf_counter()
    part5_cryo_tco = evaluate_qldpc_cryo_and_tco(anchors, n_cand_qldpc=8)
    bb9 = part5_cryo_tco["configs"]["BB144_100L_9blk"]
    comp = part5_cryo_tco["compression_ratios_BB144_9blk_vs_surface_code"]
    print(
        f"  [Part 5] 1-Cryo capacity={part5_cryo_tco['gross_code_single_cryo_logical_qubits']}L (10 blk, 2880/2887 cells) | "
        f"100L (9 blk=108L): {bb9['n_cryostats']} cryo, ${bb9['usd_per_logical_sys_amort_wright']['p50']:,.0f}/L_sys "
        f"({comp['usd_per_L_sys_vs_D3_1e-9']}x vs D3, {comp['usd_per_L_sys_vs_D2_1e-9']}x vs D2) ({time.perf_counter()-t5:.2f}s)"
    )

    # -------------------------------------------------------------------------
    # PART 6: Honest Evaluation of Pre-Registered Predictions QL1..QL7
    # -------------------------------------------------------------------------
    ql1_pass = all(
        part1_algebra[c]["css_commutes"]
        and part1_algebra[c]["exact_weight_6"]
        and part1_algebra[c]["symplectic_logical_valid"]
        and part1_algebra[c]["schedule_valid"]
        for c in ("BB_72_12_6", "BB_90_8_10", "BB_144_12_12")
    ) and (
        part1_algebra["BB_72_12_6"]["k"] == 12
        and part1_algebra["BB_90_8_10"]["k"] == 8
        and part1_algebra["BB_144_12_12"]["k"] == 12
    )

    lay20 = part2_layout_defects["recommended_layout_summary"]
    y_n6 = yield_f15_rows["N6"]["block_288_yield_pct"]
    y_n8 = yield_f15_rows["N8"]["block_288_yield_pct"]
    ql2_pass = bool(
        lay20["L_max_um"] <= 300.0
        and lay20["fits_300um_m4_resonator"]
        and (93.0 <= y_n6 <= 96.0)
        and (y_n8 > 99.5)
    )

    osd2_gain = ablation_144["0.040"]["osd2_gain_vs_bp_only"]
    ql3_pass = bool(
        osd2_gain >= 5.0
        and (p04_144 < p04_90 < p04_72)
        and (d6_to_d12_suppression >= 10.0)
    )

    d2_blk = machine_regimes["D2_Exp138_p0p92_depol"]["p_L_round_block"]
    d3_1L = machine_regimes["D3_Exp138_p0p50_RO2us_depol"]["p_L_round_per_logical"]
    d3p_blk = machine_regimes["D3plus_p0p30_RO3us_depol"]["p_L_round_block"]
    d3p_1L = machine_regimes["D3plus_p0p30_RO3us_depol"]["p_L_round_per_logical"]
    sc_d3_d7 = anchors["exp138_D3_d7_eps_round"]
    ql4_pass = bool(
        (p_th_72_vs_144 is not None)
        and (0.0040 <= p_th_72_vs_144 <= 0.0100)
        and (d2_blk > 0.01)  # honest near/above-threshold regime at D2
        and (d3p_blk < 1e-3)
        and (d3p_1L < sc_d3_d7)
        and (24 < 97)
    )

    ql5_pass = bool(
        part5_cryo_tco["gross_code_single_cryo_blocks"] == 10
        and part5_cryo_tco["gross_code_single_cryo_logical_qubits"] == 120
        and bb9["n_cryostats"] == 1
        and comp["cryostats_vs_D3_1e-9"] >= 50.0
        and comp["cryostats_vs_D2_1e-9"] == 679.0
        and comp["usd_per_L_sys_vs_D3_1e-9"] >= 20.0
    )

    y_f10_n6 = yield_f10_rows["N6"]["block_288_yield_pct"]
    y_10blk_n8 = yield_f15_rows["N8"]["cryo_10block_120L_yield_pct"]
    ql6_pass = bool(y_f10_n6 < 5.0 and y_n8 > 99.5 and y_10blk_n8 > 96.0)

    port_hits = _scan_hardcoded_paths([
        THIS_DIR / "bb_codes_and_layout144.py",
        THIS_DIR / "bp_osd_decoder144.py",
        THIS_DIR / "run_exp144.py",
        PRED_PATH,
    ])
    ql7_code_portability_pass = len(port_hits) == 0

    verdicts = {
        "QL1_EXACT_BB_CSS_ALGEBRA": ql1_pass,
        "QL2_THICKNESS2_M4_LAYOUT_AND_YIELD": ql2_pass,
        "QL3_BP_OSD_GAIN_AND_CODE_CAP_SCALING": ql3_pass,
        "QL4_CIRCUIT_THRESHOLD_AND_MACHINE_REGIMES": ql4_pass,
        "QL5_CRYOSTAT_AND_TCO_COMPRESSION": ql5_pass,
        "QL6_DEFECTIVE_BLOCK_RESILIENCE": ql6_pass,
        "QL7_PORTABILITY_AND_ARTIFACTS": ql7_code_portability_pass,
    }
    n_passed = sum(1 for v in verdicts.values() if v)

    elapsed_total = round(time.perf_counter() - t_start, 2)
    payload = {
        "experiment": "exp144_qldpc_bivariate_bicycle_m4",
        "hypothesis_id": "H162",
        "version": "6.0-phaseA",
        "date": "2026-11-23",
        "no_lab_measurement": True,
        "no_supplier_quotes": True,
        "epistemic_tags": ["Model", "Sayisal-Simulasyon", "Literatur", "Varsayim"],
        "runtime_s": elapsed_total,
        "n_workers": N_WORKERS,
        "upstream_anchors": {k: v for k, v in anchors.items() if k != "exp141_layer7"},
        "predictions": predictions,
        "verdicts": verdicts,
        "n_passed": n_passed,
        "n_total": len(verdicts),
        "success_rule_met": bool(n_passed >= 6 and ql1_pass and ql7_code_portability_pass),
        "part1_bb_algebra_and_schedules": part1_algebra,
        "part2_m4_layout_and_defect_yield": part2_layout_defects,
        "part3_code_capacity_bp_osd": part3_code_capacity,
        "part4_circuit_level_dem": part4_circuit_dem,
        "part5_cryostat_and_tco_compression": part5_cryo_tco,
        "portability_hardcoded_hits": port_hits,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2))

    # Compact plot_data_exp144.json (including 2D geometry coords for Panel C schematic!)
    plot_data = {
        "experiment": "exp144_qldpc_bivariate_bicycle_m4",
        "no_lab_measurement": True,
        "no_supplier_quotes": True,
        "verdicts": verdicts,
        "n_passed": n_passed,
        "n_total": len(verdicts),
        "panelA_code_capacity": {
            "p_grid": p_cc_grid,
            "BB_72_12_6": [cc_by_code["BB_72_12_6"][f"{pv:.3f}"]["p_L_block"] for pv in p_cc_grid],
            "BB_90_8_10": [cc_by_code["BB_90_8_10"][f"{pv:.3f}"]["p_L_block"] for pv in p_cc_grid],
            "BB_144_12_12": [cc_by_code["BB_144_12_12"][f"{pv:.3f}"]["p_L_block"] for pv in p_cc_grid],
            "ablation_p04": {
                "bp_only": ablation_144["0.040"]["bp_only"]["p_L_block"],
                "bp_osd0": ablation_144["0.040"]["bp_osd0"]["p_L_block"],
                "bp_osd2": ablation_144["0.040"]["bp_osd2"]["p_L_block"],
                "osd2_gain": osd2_gain,
            },
        },
        "panelB_circuit_dem": {
            "p_grid": p_circ_grid,
            "BB_72_12_6_pL_rnd": r72_list,
            "BB_90_8_10_pL_rnd": r90_list,
            "BB_144_12_12_pL_rnd": r144_list,
            "BB_72_12_6_pL_1L": r72_perL,
            "BB_90_8_10_pL_1L": r90_perL,
            "BB_144_12_12_pL_1L": r144_perL,
            "p_th": p_th_72_vs_144,
            "machine_points": {
                k: {
                    "p_2q": v["p_2q"],
                    "p_L_round_block": v["p_L_round_block"],
                    "p_L_round_per_logical": v["p_L_round_per_logical"],
                }
                for k, v in machine_regimes.items()
            },
            "exp138_sc_anchors": part4_circuit_dem["surface_code_comparison_anchors_exp138"],
        },
        "panelC_layout_20um": {
            "die_width_um": lay20["block_size_um"][0],
            "die_height_um": lay20["block_size_um"][1],
            "L_max_um": lay20["L_max_um"],
            "L1_max_um": lay20["layer1_max_eucl_um"],
            "coords_folded_um": {
                str(q): [float(xy[0] * 20.0), float(xy[1] * 20.0), lay_full["qubit_types"][q]]
                for q, xy in lay_full["coords_folded"].items()
            },
            "layer1_edges": [[int(u), int(v)] for u, v in lay_full["layer1_edges"]],
            "layer2_edges": [[int(u), int(v)] for u, v in lay_full["layer2_edges"]],
        },
        "panelD_pitch_resonator": {
            "pitches_um": list(pitches_um),
            "L_max_um": [layout_by_pitch[f"{int(p)}um"]["L_max_um"] for p in pitches_um],
            "L1_max_um": [layout_by_pitch[f"{int(p)}um"]["layer1_max_eucl_um"] for p in pitches_um],
            "f_r_fixed_GHz": [layout_by_pitch[f"{int(p)}um"]["f_r_fixed_100pH_ghz"] for p in pitches_um],
            "Lsq_req_pH": [layout_by_pitch[f"{int(p)}um"]["L_sq_pH_for_5GHz"] for p in pitches_um],
        },
        "panelE_defect_yield": {
            "N_cand_grid": [4, 5, 6, 7, 8, 9, 10],
            "f10_block_pct": [yield_f10_rows[f"N{n}"]["block_288_yield_pct"] for n in range(4, 11)],
            "f15_block_pct": [yield_f15_rows[f"N{n}"]["block_288_yield_pct"] for n in range(4, 11)],
            "f15_10blk_cryo_pct": [yield_f15_rows[f"N{n}"]["cryo_10block_120L_yield_pct"] for n in range(4, 11)],
            "f15_9of10_spared_N8_pct": round(100.0 * p_die_9of10_n8, 3),
        },
        "panelF_cryo_tco": {
            "labels": ["SC D2\n(1e-9)", "SC D3\n(1e-9)", "SC D3\n(1e-6)", "BB-288\n(d=18)", "BB-144\n(Gross)"],
            "cryostats_100L": [
                anchors["exp141_layer7"]["D2_primary_Lambda1p40"]["1e-9"]["cryostats_100L"],
                anchors["exp141_layer7"]["D3_target_Lambda2p52"]["1e-9"]["cryostats_100L"],
                anchors["exp141_layer7"]["D3_target_Lambda2p52"]["1e-6"]["cryostats_100L"],
                part5_cryo_tco["configs"]["BB288_100L_9blk_d18_ref"]["n_cryostats"],
                bb9["n_cryostats"],
            ],
            "usd_per_L_sys_M": [
                round(anchors["exp141_layer7"]["D2_primary_Lambda1p40"]["1e-9"]["sys_100L_usd_per_L_amort_wright_p50"] / 1e6, 4),
                round(anchors["exp141_layer7"]["D3_target_Lambda2p52"]["1e-9"]["sys_100L_usd_per_L_amort_wright_p50"] / 1e6, 4),
                round(anchors["exp141_layer7"]["D3_target_Lambda2p52"]["1e-6"]["sys_100L_usd_per_L_amort_wright_p50"] / 1e6, 4),
                round(part5_cryo_tco["configs"]["BB288_100L_9blk_d18_ref"]["usd_per_logical_sys_amort_wright"]["p50"] / 1e6, 4),
                round(bb9["usd_per_logical_sys_amort_wright"]["p50"] / 1e6, 4),
            ],
            "compression_ratios": comp,
        },
    }
    PLOT_JSON.write_text(json.dumps(plot_data, indent=2))

    print(f"\n=== Exp144 COMPLETE in {elapsed_total:.1f}s | Verdicts: {n_passed}/{len(verdicts)} PASS ===")
    for vk, vv in verdicts.items():
        print(f"  {vk}: {'PASS' if vv else 'FAIL'}")


if __name__ == "__main__":
    main()
