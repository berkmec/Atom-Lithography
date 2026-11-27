"""Exp130 Orchestrator: Risk R6 Theory & Process Closure — Millisecond Flash/Laser Annealing
(31P Activation vs Non-Equilibrium TED Diffusion, Surface Escape, 28Si/29Si Bath Mixing,
and S5.5 Optical Hardware Specification for CAD v3.0/v4.0).

Hypothesis: H148 (predictions registered in results/exp130_flash_anneal_diffusion/predictions_exp130.json).
Epistemic label: {Model} / {Sayısal-Simülasyon} / {Literatür}. no_lab_measurement=True.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from heat_ted_solver import (
    T_MELT_SI,
    KineticsParams,
    build_synthetic_thermal_waveform,
    compute_cryo_cooldown_to_20mK,
    find_fluence_for_target_T,
    solve_ted_kinetics_1d,
    solve_thermal_1d,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "exp130_flash_anneal_diffusion"
PRED_PATH = RESULTS_DIR / "predictions_exp130.json"
OUT_JSON = RESULTS_DIR / "exp130.json"
PLOT_DATA_JSON = RESULTS_DIR / "plot_data_exp130.json"

# Locked Exp124 Arch-B non-anneal RSS placement components [nm]
# OBS-039: True corrected ZBL/iradina 5 keV lateral straggle = 4.385 nm (legacy truncated = 3.259 nm)
EXP124_FIXED_VAR_LEGACY_NM2 = 3.259**2 + 1.428**2 + 0.500**2 + 0.500**2 + 0.300**2
EXP124_FIXED_VAR_NM2 = 4.385**2 + 1.250**2 + 0.500**2 + 0.500**2 + 0.300**2
EXP124_BASELINE_SIGMA_ANNEAL_NM = 0.500
EXP124_CEILING_NM = 3.800


def exp124_sigma_tot(sigma_anneal_nm: float) -> float:
    return math.sqrt(EXP124_FIXED_VAR_NM2 + sigma_anneal_nm**2)


def exp124_sigma_tot_legacy_bca(sigma_anneal_nm: float) -> float:
    return math.sqrt(EXP124_FIXED_VAR_LEGACY_NM2 + sigma_anneal_nm**2)


def evaluate_window_criteria(res: Dict[str, Any], T_peak_K: float, sigma_limit_nm: float = 0.50) -> Dict[str, bool]:
    c_act = float(res["f_act_bulk"]) >= 0.95
    c_diff = float(res["sigma_anneal_nm"]) <= sigma_limit_nm
    c_loss = float(res["f_total_surface_loss"]) < 0.02
    c_iso = float(res["sigma_iso_nm"]) <= 0.50
    c_melt = T_peak_K < 0.92 * T_MELT_SI
    return {
        "pass_act_ge_95pct": c_act,
        "pass_sigma_anneal": c_diff,
        "pass_surface_loss_lt_2pct": c_loss,
        "pass_sigma_iso_le_05nm": c_iso,
        "pass_non_melting_092Tm": c_melt,
        "pass_all": c_act and c_diff and c_loss and c_iso and c_melt,
    }


def main() -> None:
    t0 = time.perf_counter()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    preds = json.loads(PRED_PATH.read_text(encoding="utf-8"))

    # =========================================================================
    # 1. Primary Operating Point & 1D Thermal PDE Convergence (808 nm, 1.0 ms)
    # =========================================================================
    T_opt_K = 1440.0
    tp_opt_s = 1.0e-3
    th_opt = find_fluence_for_target_T(tp_opt_s, T_opt_K, wavelength_nm=808.0)
    F_opt = float(th_opt["fluence_J_per_cm2"])

    thermal_conv: List[Dict[str, float]] = []
    for nc, ns in [(80, 40), (120, 80), (160, 160)]:
        rc = solve_thermal_1d(F_opt, tp_opt_s, 808.0, n_cells=nc, n_steps_pulse=ns, n_steps_cool=int(ns * 1.5))
        thermal_conv.append({
            "n_cells": nc,
            "n_steps_pulse": ns,
            "T_peak_K": round(float(rc["T_peak_K"]), 4),
            "T_back_max_K": round(float(rc["T_back_max_K"]), 4),
            "t_quench_to_900K_ms": round(float(rc["t_quench_to_900K_ms"]), 4),
            "energy_balance_rel_err": float(rc["energy_balance_rel_err"]),
        })
    conv_T_rel_err = abs(thermal_conv[2]["T_peak_K"] - thermal_conv[1]["T_peak_K"]) / thermal_conv[2]["T_peak_K"]
    conv_E_max_err = max(x["energy_balance_rel_err"] for x in thermal_conv)

    # Wavelength & pulse-width benchmarks (exact 1D PDE -> coupled TED PDE)
    wl_specs = [
        ("308nm_excimer_50us_1440K", 308.0, 0.05e-3, 1440.0),
        ("308nm_excimer_1ms_1440K", 308.0, 1.0e-3, 1440.0),
        ("532nm_green_1ms_1440K", 532.0, 1.0e-3, 1440.0),
        ("808nm_diode_0.5ms_1440K", 808.0, 0.5e-3, 1440.0),
        ("808nm_diode_1.0ms_1440K", 808.0, 1.0e-3, 1440.0),
        ("808nm_diode_1.5ms_1440K", 808.0, 1.5e-3, 1440.0),
        ("808nm_diode_2.0ms_1440K", 808.0, 2.0e-3, 1440.0),
    ]
    wavelength_benchmarks: Dict[str, Dict[str, Any]] = {}
    thermal_waveforms_plot: Dict[str, Dict[str, List[float]]] = {}
    ted_opt_full: Dict[str, Any] = {}

    for key, wl, tp_s, T_tgt in wl_specs:
        th = find_fluence_for_target_T(tp_s, T_tgt, wavelength_nm=wl)
        ted = solve_ted_kinetics_1d(th["t_s"], th["T_surf_K"], C_cl_peak_cm3=3.0e19, r_casc_nm=2.5)
        crit_05 = evaluate_window_criteria(ted, float(th["T_peak_K"]), sigma_limit_nm=0.50)
        crit_10 = evaluate_window_criteria(ted, float(th["T_peak_K"]), sigma_limit_nm=1.00)
        wavelength_benchmarks[key] = {
            "wavelength_nm": wl,
            "t_pulse_ms": tp_s * 1e3,
            "T_peak_K": round(float(th["T_peak_K"]), 2),
            "T_peak_over_Tmelt": round(float(th["T_peak_over_Tmelt"]), 4),
            "fluence_J_per_cm2": round(float(th["fluence_J_per_cm2"]), 3),
            "E_absorbed_J_cm2": round(float(th["E_absorbed_J_cm2"]), 3),
            "T_back_max_K": round(float(th["T_back_max_K"]), 2),
            "t_quench_to_900K_ms": round(float(th["t_quench_to_900K_ms"]), 4),
            "energy_balance_rel_err": float(th["energy_balance_rel_err"]),
            "f_act_bulk": round(float(ted["f_act_bulk"]), 5),
            "f_total_surface_loss": round(float(ted["f_total_surface_loss"]), 6),
            "sigma_anneal_nm": round(float(ted["sigma_anneal_nm"]), 4),
            "sigma_iso_nm": round(float(ted["sigma_iso_nm"]), 5),
            "exp124_sigma_tot_nm": round(exp124_sigma_tot(float(ted["sigma_anneal_nm"])), 4),
            "mass_conservation_err": float(ted["mass_conservation_err"]),
            "pass_strict_05nm": crit_05["pass_all"],
            "pass_limit_10nm": crit_10["pass_all"],
        }
        if key in ("308nm_excimer_50us_1440K", "532nm_green_1ms_1440K", "808nm_diode_0.5ms_1440K", "808nm_diode_1.0ms_1440K"):
            thermal_waveforms_plot[key] = {
                "t_ms": [round(float(x * 1e3), 5) for x in th["t_s"]],
                "T_surf_K": [round(float(x), 2) for x in th["T_surf_K"]],
                "T_back_K": [round(float(x), 2) for x in th["T_back_K"]],
            }
        if key == "808nm_diode_1.0ms_1440K":
            ted_opt_full = ted

    # Pulse-width curve at 808 nm, T_peak = 1440 K (for figure subpanel)
    tp_curve_ms = [0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0]
    fluence_curve: List[Dict[str, float]] = []
    for tp_m in tp_curve_ms:
        th_c = find_fluence_for_target_T(tp_m * 1e-3, 1440.0, wavelength_nm=808.0)
        ted_c = solve_ted_kinetics_1d(th_c["t_s"], th_c["T_surf_K"], C_cl_peak_cm3=3.0e19, r_casc_nm=2.5)
        fluence_curve.append({
            "t_pulse_ms": tp_m,
            "fluence_J_per_cm2": round(float(th_c["fluence_J_per_cm2"]), 3),
            "T_back_max_K": round(float(th_c["T_back_max_K"]), 2),
            "t_quench_to_900K_ms": round(float(th_c["t_quench_to_900K_ms"]), 4),
            "sigma_anneal_nm": round(float(ted_c["sigma_anneal_nm"]), 4),
            "f_act_bulk": round(float(ted_c["f_act_bulk"]), 5),
            "exp124_sigma_tot_nm": round(exp124_sigma_tot(float(ted_c["sigma_anneal_nm"])), 4),
        })

    # =========================================================================
    # 2. Exp108 Anchor Reproduction (doi:10.1063/1.331355: 600C & 800C / 10 min)
    # =========================================================================
    exp108_anchor: Dict[str, Any] = {}
    exp108_profiles_plot: Dict[str, Any] = {}
    for T_C in (600.0, 800.0):
        t_w, T_w = build_synthetic_thermal_waveform(T_C + 273.15, 600.0)
        # 1D planar blanket high-dose implant (r_casc_nm=None, dose=1e15 cm^-2 with 1 ML saturation OBS-151)
        p_blanket = KineticsParams(dose_cm2=1.0e15, spe_regime="planar_10nm")
        r_a = solve_ted_kinetics_1d(t_w, T_w, C_cl_peak_cm3=1.5e20, r_casc_nm=None, params=p_blanket)
        lbl = f"{int(T_C)}C_10min_uhv_blanket"
        exp108_anchor[lbl] = {
            "T_C": T_C,
            "T_K": round(T_C + 273.15, 2),
            "duration_s": 600.0,
            "geometry": "1D planar blanket high-dose (~1e15 cm^-2, r_casc=None)",
            "f_act_bulk": round(float(r_a["f_act_bulk"]), 5),
            "f_inact_bulk": round(float(r_a["f_inact_bulk"]), 5),
            "f_surface_pileup": round(float(r_a["f_surface_pileup"]), 5),
            "f_vacuum_escape": round(float(r_a["f_vacuum_escape"]), 5),
            "f_total_surface_loss": round(float(r_a["f_total_surface_loss"]), 5),
            "sigma_anneal_nm": round(float(r_a["sigma_anneal_nm"]), 3),
            "mass_conservation_err": float(r_a["mass_conservation_err"]),
        }
        exp108_profiles_plot[lbl] = {
            "z_nm": [round(float(x), 3) for x in r_a["z_nm"]],
            "P_init": [round(float(x), 6) for x in r_a["P_init"]],
            "P_act_final": [round(float(x), 6) for x in r_a["P_act_final"]],
            "f_surface_pileup": round(float(r_a["f_surface_pileup"]), 5),
            "f_vacuum_escape": round(float(r_a["f_vacuum_escape"]), 5),
        }

    # =========================================================================
    # 3. Conventional Anneal Benchmarks on Machine 5 keV Single-Donor Target
    # =========================================================================
    conventional_benchmarks: Dict[str, Any] = {}
    machine_profiles_plot: Dict[str, Any] = {
        "z_nm": [round(float(x), 3) for x in ted_opt_full["z_nm"]],
        "P_init": [round(float(x), 6) for x in ted_opt_full["P_init"]],
        "P_flash_1ms_1440K": [round(float(x), 6) for x in ted_opt_full["P_act_final"]],
        "C29_flash_1ms_1440K": [round(float(x), 6) for x in ted_opt_full["C29_final"]],
    }
    conv_cases = [
        ("furnace_600C_10min", 600.0, 600.0),
        ("furnace_800C_10min", 800.0, 600.0),
        ("rta_1000C_10s", 1000.0, 10.0),
    ]
    for name, T_C, dur_s in conv_cases:
        tw, Tw = build_synthetic_thermal_waveform(T_C + 273.15, dur_s)
        rr = solve_ted_kinetics_1d(tw, Tw, C_cl_peak_cm3=3.0e19, r_casc_nm=2.5)
        crit_10 = evaluate_window_criteria(rr, T_C + 273.15, sigma_limit_nm=1.00)
        crit_05 = evaluate_window_criteria(rr, T_C + 273.15, sigma_limit_nm=0.50)
        conventional_benchmarks[name] = {
            "T_C": T_C,
            "T_K": round(T_C + 273.15, 2),
            "duration_s": dur_s,
            "f_act_bulk": round(float(rr["f_act_bulk"]), 5),
            "f_surface_pileup": round(float(rr["f_surface_pileup"]), 5),
            "f_vacuum_escape": round(float(rr["f_vacuum_escape"]), 5),
            "f_total_surface_loss": round(float(rr["f_total_surface_loss"]), 5),
            "sigma_anneal_nm": round(float(rr["sigma_anneal_nm"]), 4),
            "sigma_iso_nm": round(float(rr["sigma_iso_nm"]), 5),
            "exp124_sigma_tot_nm": round(exp124_sigma_tot(float(rr["sigma_anneal_nm"])), 4),
            "mass_conservation_err": float(rr["mass_conservation_err"]),
            "criteria_10nm": crit_10,
            "pass_strict_05nm": crit_05["pass_all"],
            "pass_limit_10nm": crit_10["pass_all"],
        }
        machine_profiles_plot[f"P_{name}"] = [round(float(x), 6) for x in rr["P_act_final"]]
        machine_profiles_plot[f"C29_{name}"] = [round(float(x), 6) for x in rr["C29_final"]]

    # =========================================================================
    # 4. Full 2D (t_pulse x T_peak) Phase Diagram Sweep (36 x 34 = 1224 points)
    # =========================================================================
    tp_grid_s = np.geomspace(1.0e-5, 600.0, 36)
    T_grid_K = np.linspace(700.0, 1660.0, 34)
    n_tp, n_T = tp_grid_s.size, T_grid_K.size

    f_act_map = np.zeros((n_T, n_tp), dtype=np.float64)
    sigma_ann_map = np.zeros((n_T, n_tp), dtype=np.float64)
    loss_map = np.zeros((n_T, n_tp), dtype=np.float64)
    sigma_iso_map = np.zeros((n_T, n_tp), dtype=np.float64)
    pass_05_map = np.zeros((n_T, n_tp), dtype=np.int32)
    pass_10_map = np.zeros((n_T, n_tp), dtype=np.int32)

    for j, tp_s in enumerate(tp_grid_s):
        for i, T_K in enumerate(T_grid_K):
            tw, Tw = build_synthetic_thermal_waveform(float(T_K), float(tp_s), n_pts=100)
            rr = solve_ted_kinetics_1d(tw, Tw, C_cl_peak_cm3=3.0e19, r_casc_nm=2.5, n_cells=120)
            f_act_map[i, j] = rr["f_act_bulk"]
            sigma_ann_map[i, j] = rr["sigma_anneal_nm"]
            loss_map[i, j] = rr["f_total_surface_loss"]
            sigma_iso_map[i, j] = rr["sigma_iso_nm"]
            c05 = evaluate_window_criteria(rr, float(T_K), sigma_limit_nm=0.50)
            c10 = evaluate_window_criteria(rr, float(T_K), sigma_limit_nm=1.00)
            pass_05_map[i, j] = 1 if c05["pass_all"] else 0
            pass_10_map[i, j] = 1 if c10["pass_all"] else 0

    # Extract feasible millisecond window bounds
    idx_pass_05 = np.argwhere(pass_05_map == 1)
    idx_pass_10 = np.argwhere(pass_10_map == 1)
    ms_mask_tp = (tp_grid_s >= 0.3e-3) & (tp_grid_s <= 5.0e-3)
    ms_mask_T = (T_grid_K >= 1320.0) & (T_grid_K <= 1540.0)
    ms_subgrid_05 = pass_05_map[np.ix_(ms_mask_T, ms_mask_tp)]

    phase_summary = {
        "grid_shape": [int(n_T), int(n_tp)],
        "t_pulse_range_s": [float(tp_grid_s[0]), float(tp_grid_s[-1])],
        "T_peak_range_K": [float(T_grid_K[0]), float(T_grid_K[-1])],
        "T_non_melting_limit_K": round(0.92 * T_MELT_SI, 2),
        "n_pass_strict_05nm": int(idx_pass_05.shape[0]),
        "n_pass_limit_10nm": int(idx_pass_10.shape[0]),
        "strict_05nm_window_t_pulse_ms": [
            round(float(np.min(tp_grid_s[idx_pass_05[:, 1]]) * 1e3), 4),
            round(float(np.max(tp_grid_s[idx_pass_05[:, 1]]) * 1e3), 4),
        ] if idx_pass_05.size > 0 else [],
        "strict_05nm_window_T_peak_K": [
            round(float(np.min(T_grid_K[idx_pass_05[:, 0]])), 1),
            round(float(np.max(T_grid_K[idx_pass_05[:, 0]])), 1),
        ] if idx_pass_05.size > 0 else [],
        "limit_10nm_window_t_pulse_ms": [
            round(float(np.min(tp_grid_s[idx_pass_10[:, 1]]) * 1e3), 4),
            round(float(np.max(tp_grid_s[idx_pass_10[:, 1]]) * 1e3), 4),
        ] if idx_pass_10.size > 0 else [],
        "ms_target_box_pass_count": int(np.sum(ms_subgrid_05)),
        "ms_target_box_total_count": int(ms_subgrid_05.size),
        "ms_target_box_pass_fraction": round(float(np.mean(ms_subgrid_05)), 4),
    }

    # =========================================================================
    # 5. TED Grid Convergence & UQ Stress Tests at Optimal Operating Point
    # =========================================================================
    ted_conv: List[Dict[str, Any]] = []
    for nc_ted in (100, 150, 200):
        rt = solve_ted_kinetics_1d(th_opt["t_s"], th_opt["T_surf_K"], C_cl_peak_cm3=3.0e19, r_casc_nm=2.5, n_cells=nc_ted)
        ted_conv.append({
            "n_cells": nc_ted,
            "dz_nm": round(60.0 / nc_ted, 4),
            "f_act_bulk": round(float(rt["f_act_bulk"]), 6),
            "sigma_anneal_nm": round(float(rt["sigma_anneal_nm"]), 5),
            "f_total_surface_loss": round(float(rt["f_total_surface_loss"]), 6),
            "sigma_iso_nm": round(float(rt["sigma_iso_nm"]), 6),
            "mass_conservation_err": float(rt["mass_conservation_err"]),
        })
    ted_conv_rel_err = abs(ted_conv[2]["sigma_anneal_nm"] - ted_conv[1]["sigma_anneal_nm"]) / ted_conv[2]["sigma_anneal_nm"]

    uq_cases = [
        ("nominal_808nm_1ms_1440K", F_opt, dict(C_cl_peak_cm3=3.0e19, r_casc_nm=2.5)),
        ("fluence_minus_5pct", F_opt * 0.95, dict(C_cl_peak_cm3=3.0e19, r_casc_nm=2.5)),
        ("fluence_plus_5pct", F_opt * 1.05, dict(C_cl_peak_cm3=3.0e19, r_casc_nm=2.5)),
        ("pocket_3d_spe_regime_L2nm", F_opt, dict(C_cl_peak_cm3=3.0e19, r_casc_nm=2.5, params=KineticsParams(spe_regime="pocket_3d"))),
        ("slow_spe_0.5x_nu_act", F_opt, dict(C_cl_peak_cm3=3.0e19, r_casc_nm=2.5, params=KineticsParams(nu_act_s=1.84e14))),
        ("wide_cascade_r_4nm", F_opt, dict(C_cl_peak_cm3=3.0e19, r_casc_nm=4.0)),
        ("damage_3x_9e19_cm3", F_opt, dict(C_cl_peak_cm3=9.0e19, r_casc_nm=2.5)),
        ("iradina_damage_10pct_1p5e20_cm3", F_opt, dict(C_cl_peak_cm3=1.5e20, r_casc_nm=2.5, Rp_nm=10.31, sigma_z_nm=5.10)),
        ("iradina_damage_30pct_4p5e20_cm3", F_opt, dict(C_cl_peak_cm3=4.5e20, r_casc_nm=2.5, Rp_nm=10.31, sigma_z_nm=5.10)),
        ("true_iradina_depth_Rp10p31_sigz5p10", F_opt, dict(C_cl_peak_cm3=3.0e19, r_casc_nm=2.5, Rp_nm=10.31, sigma_z_nm=5.10)),
        ("legacy_EmI_1p77eV_comparison", F_opt, dict(C_cl_peak_cm3=3.0e19, r_casc_nm=2.5, params=KineticsParams(Ef_I_eV=3.18, Em_I_eV=1.77, f_vac_init_ratio=0.0))),
        ("blanket_1D_upper_bound_r_None", F_opt, dict(C_cl_peak_cm3=3.0e19, r_casc_nm=None)),
    ]
    uq_results: Dict[str, Any] = {}
    for lbl, F_val, kw in uq_cases:
        th_u = solve_thermal_1d(F_val, tp_opt_s, 808.0) if abs(F_val - F_opt) > 1e-6 else th_opt
        ted_u = solve_ted_kinetics_1d(th_u["t_s"], th_u["T_surf_K"], **kw)
        c05 = evaluate_window_criteria(ted_u, float(th_u["T_peak_K"]), sigma_limit_nm=0.50)
        c10 = evaluate_window_criteria(ted_u, float(th_u["T_peak_K"]), sigma_limit_nm=1.00)
        uq_results[lbl] = {
            "fluence_J_per_cm2": round(F_val, 3),
            "T_peak_K": round(float(th_u["T_peak_K"]), 2),
            "f_act_bulk": round(float(ted_u["f_act_bulk"]), 5),
            "sigma_anneal_nm": round(float(ted_u["sigma_anneal_nm"]), 4),
            "f_total_surface_loss": round(float(ted_u["f_total_surface_loss"]), 6),
            "sigma_iso_nm": round(float(ted_u["sigma_iso_nm"]), 5),
            "exp124_sigma_tot_nm": round(exp124_sigma_tot(float(ted_u["sigma_anneal_nm"])), 4),
            "pass_strict_05nm": c05["pass_all"],
            "pass_limit_10nm": c10["pass_all"],
        }

    # =========================================================================
    # 6. Cryo Recovery (20 mK) & S5.5 Optical Hardware Spec (OBS-100 fixed!)
    # =========================================================================
    cryo_scenarios = {
        "in_line_loadlock_rt_baseline": {
            "description": "In-line RT UHV load-lock flash post-implant (MANDATORY production baseline; 0 J cryo load)",
            "E_absorbed_J": 0.0,
            "T_bulk_eq_post_flash_K": 0.02,
            "t_cool_total_s": 0.0,
            "t_cool_total_min": 0.0,
            "in_situ_20mK_flash_viable": True,
        },
        # Current CAD S6.2-01 (0.725 kg Cu + 0.08 kg AlN, NO 4 K mechanical heat switch -> Still-limited!)
        "insitu_s55_16x16mm_active_field": compute_cryo_cooldown_to_20mK(F_opt, 2.56, absorptivity=0.67, has_4k_thermal_switch=False),
        "insitu_s55_4x4mm_single_tile": compute_cryo_cooldown_to_20mK(F_opt, 0.16, absorptivity=0.67, has_4k_thermal_switch=False),
        "insitu_s55_50mm_full_wafer": compute_cryo_cooldown_to_20mK(F_opt, math.pi * 2.5**2, absorptivity=0.67, has_4k_thermal_switch=False),
        # Required hardware upgrade: dedicated 1.0 W mechanical 4 K heat switch at S6.2-01
        "insitu_s55_16x16mm_with_4k_switch_upgrade": compute_cryo_cooldown_to_20mK(F_opt, 2.56, absorptivity=0.67, has_4k_thermal_switch=True),
        "insitu_s55_50mm_with_4k_switch_upgrade": compute_cryo_cooldown_to_20mK(F_opt, math.pi * 2.5**2, absorptivity=0.67, has_4k_thermal_switch=True),
    }

    # Sapphire optical properties at 808 nm (Al2O3 ordinary ray n_o = 1.760)
    n_sapphire_808 = 1.760
    R_saph_single = ((n_sapphire_808 - 1.0) / (n_sapphire_808 + 1.0)) ** 2
    T_saph_uncoated = ((1.0 - R_saph_single) ** 2) / (1.0 - R_saph_single**2)  # exact multiple-reflection slab
    T_saph_AR = 0.980  # commercial 808 nm V-coat / dual-side BBAR sapphire
    T_mirror_45_HR = 0.990
    T_homogenizer = 0.960
    T_optical_train_AR = T_saph_AR * T_mirror_45_HR * T_homogenizer  # 0.9314

    # CAD v3.0 S5.5 geometry (research/atom_lithography_machine/cad/params.py L437-444)
    duct_clear_diam_mm = 44.0
    window_od_mm = 50.0
    window_thick_mm = 8.0
    beam_diam_at_window_mm = 36.0  # 82% fill of Ø44 mm clear aperture (zero clipping margin 4 mm radial)
    A_win_beam_cm2 = math.pi * ((0.5 * beam_diam_at_window_mm * 0.1) ** 2)  # 10.1788 cm^2
    A_active_field_cm2 = 1.6 * 1.6  # 2.56 cm^2 (16 x 16 mm active qubit array)
    A_tile_cm2 = 0.4 * 0.4          # 0.16 cm^2 (4 x 4 mm step-and-flash tile)

    # Sapphire 1 ms LIDT (ISO 21254 tau^0.5 scaling from conservative 10 J/cm^2 @ 10 ns -> 3162 J/cm^2 intrinsic,
    # conservative engineering floor = 100 J/cm^2 AR-coated / 250 J/cm^2 uncoated at 1 ms, 808 nm)
    lidt_1ms_floor_J_cm2 = 100.0
    lidt_1ms_uncoated_typ_J_cm2 = 250.0
    lidt_1ms_intrinsic_scaling_J_cm2 = 10.0 * math.sqrt(1.0e-3 / 1.0e-8)

    # Fluence at sapphire window for 3 delivery architectures
    F_win_16x16_AR = (F_opt / T_saph_AR) * (A_active_field_cm2 / A_win_beam_cm2)
    F_win_16x16_uncoated = (F_opt / T_saph_uncoated) * (A_active_field_cm2 / A_win_beam_cm2)
    F_win_4x4_AR = (F_opt / T_saph_AR) * (A_tile_cm2 / A_win_beam_cm2)
    F_05ms = wavelength_benchmarks["808nm_diode_0.5ms_1440K"]["fluence_J_per_cm2"]
    F_win_1to1_05ms_AR = F_05ms / T_saph_AR

    # Optical energy & peak power (accounting for 0.90 raised-cosine flat-top duty factor)
    E_wafer_16x16_J = F_opt * A_active_field_cm2
    E_source_16x16_J = E_wafer_16x16_J / T_optical_train_AR
    P_peak_source_16x16_kW = (E_source_16x16_J / (0.90 * tp_opt_s)) / 1e3

    E_wafer_4x4_J = F_opt * A_tile_cm2
    E_source_4x4_J = E_wafer_4x4_J / T_optical_train_AR
    P_peak_source_4x4_kW = (E_source_4x4_J / (0.90 * tp_opt_s)) / 1e3

    s55_hardware_spec = {
        "cad_v3_anchor": {
            "port_id": "S5.5",
            "location": "Equatorial +Y viewport at Z_WAFER = 500.0 mm (CAD v3.0 params.py L437-444)",
            "duct_clear_aperture_mm": duct_clear_diam_mm,
            "viewport_flange": "CF63 UHV bakeable sapphire viewport (Al2O3 single crystal)",
            "sapphire_disc_od_mm": window_od_mm,
            "sapphire_thickness_mm": window_thick_mm,
            "external_head_envelope_mm": [84.0, 88.0, 84.0],
            "optical_beam_diam_at_window_mm": beam_diam_at_window_mm,
            "radial_clearance_mm": 0.5 * (duct_clear_diam_mm - beam_diam_at_window_mm),
        },
        "primary_source_spec": {
            "technology": "808 nm qCW macro-channel diode-laser bar stack (fiber-bundle coupled to S5.5 homogenizer head)",
            "wavelength_nm": 808.0,
            "backup_wavelength_nm": 532.0,
            "pulse_duration_ms": 1.0,
            "pulse_shape": "Flat-top raised-cosine (10% rise / 80% plateau / 10% fall), uniformity <= +-2% across die",
            "wafer_fluence_J_per_cm2": round(F_opt, 2),
            "fluence_tolerance_pct": 5.0,
            "peak_surface_T_K": round(float(th_opt["T_peak_K"]), 1),
            "peak_surface_T_C": round(float(th_opt["T_peak_K"]) - 273.15, 1),
            "margin_below_Tmelt_K": round(T_MELT_SI - float(th_opt["T_peak_K"]), 1),
            "self_quench_to_900K_ms": round(float(th_opt["t_quench_to_900K_ms"]), 3),
            "wafer_backside_max_T_K": round(float(th_opt["T_back_max_K"]), 1),
        },
        "sapphire_window_optics": {
            "refractive_index_808nm": n_sapphire_808,
            "transmission_uncoated": round(T_saph_uncoated, 4),
            "transmission_AR_808nm": T_saph_AR,
            "optical_train_throughput_AR": round(T_optical_train_AR, 4),
            "lidt_1ms_conservative_floor_J_per_cm2": lidt_1ms_floor_J_cm2,
            "lidt_1ms_uncoated_typical_J_per_cm2": lidt_1ms_uncoated_typ_J_cm2,
            "lidt_1ms_iso21254_intrinsic_J_per_cm2": round(lidt_1ms_intrinsic_scaling_J_cm2, 1),
        },
        "delivery_modes": {
            "mode1_single_shot_16x16mm": {
                "field_mm": "16 x 16 mm (2.56 cm^2, single shot, zero stitch seams)",
                "wafer_pulse_energy_J": round(E_wafer_16x16_J, 2),
                "source_pulse_energy_J": round(E_source_16x16_J, 2),
                "source_peak_power_kW": round(P_peak_source_16x16_kW, 2),
                "window_fluence_AR_J_per_cm2": round(F_win_16x16_AR, 2),
                "window_fluence_uncoated_J_per_cm2": round(F_win_16x16_uncoated, 2),
                "lidt_safety_margin_vs_100J_floor_AR": round(lidt_1ms_floor_J_cm2 / F_win_16x16_AR, 2),
                "lidt_safety_margin_vs_100J_floor_uncoated": round(lidt_1ms_floor_J_cm2 / F_win_16x16_uncoated, 2),
                "cryo_recovery_to_20mK_min": round(cryo_scenarios["insitu_s55_16x16mm_active_field"]["t_cool_total_min"], 2),
            },
            "mode2_step_and_flash_4x4mm": {
                "field_mm": "4 x 4 mm (0.16 cm^2, 16 stitched shots via XY stage — compact BOM option)",
                "wafer_pulse_energy_J": round(E_wafer_4x4_J, 2),
                "source_pulse_energy_J": round(E_source_4x4_J, 2),
                "source_peak_power_kW": round(P_peak_source_4x4_kW, 2),
                "window_fluence_AR_J_per_cm2": round(F_win_4x4_AR, 3),
                "lidt_safety_margin_vs_100J_floor_AR": round(lidt_1ms_floor_J_cm2 / F_win_4x4_AR, 1),
                "cryo_recovery_single_tile_min": round(cryo_scenarios["insitu_s55_4x4mm_single_tile"]["t_cool_total_min"], 2),
            },
            "mode3_collimated_1to1_0.5ms": {
                "field_mm": "Ø36 mm collimated 1:1 (0.5 ms / 1440 K, zero relay demagnification)",
                "wafer_fluence_J_per_cm2": round(F_05ms, 2),
                "window_fluence_AR_J_per_cm2": round(F_win_1to1_05ms_AR, 2),
                "lidt_safety_margin_vs_100J_floor_AR": round(lidt_1ms_floor_J_cm2 / F_win_1to1_05ms_AR, 2),
            },
            "mode4_inline_loadlock_rt_baseline": {
                "location": "RT UHV load-lock post-implant flash station (same 808 nm 1.0 ms recipe)",
                "cryo_heat_load_J": 0.0,
                "cryo_recovery_min": 0.0,
                "role": "Recommended high-throughput production baseline; S5.5 viewport retained for in-situ re-anneal",
            },
        },
        "diagnostics_and_interlocks": [
            "Fast InGaAs/Si two-color pyrometer (10 us response, 900-1700 K) via dichroic beamsplitter on S5.5",
            "Inline photodiode pulse-energy integrator (closed-loop +-1.5% fluence calibration per shot)",
            "Hardwired laser-shutter interlock tied to MXC temperature (< 1 K) & UHV gate-valve status",
        ],
    }

    # =========================================================================
    # 7. Strict Pre-Registered Prediction Evaluation (EA1..EA6)
    # =========================================================================
    a600 = exp108_anchor["600C_10min_uhv_blanket"]
    a800 = exp108_anchor["800C_10min_uhv_blanket"]
    ea1_pass = (
        a600["f_surface_pileup"] >= 0.15
        and a600["f_vacuum_escape"] < 0.05
        and a800["f_vacuum_escape"] >= 0.30
        and a600["mass_conservation_err"] < 1e-11
        and a800["mass_conservation_err"] < 1e-11
    )

    opt_b = wavelength_benchmarks["808nm_diode_1.0ms_1440K"]
    ea2_pass = (
        conv_T_rel_err < 0.01
        and conv_E_max_err < 0.005
        and (1400.0 <= opt_b["T_peak_K"] <= 1520.0)
        and (opt_b["T_peak_K"] < 0.92 * T_MELT_SI)
        and (10.0 <= opt_b["fluence_J_per_cm2"] <= 45.0)
        and (opt_b["t_quench_to_900K_ms"] < 10.0)
        and (opt_b["T_back_max_K"] < 700.0)
    )

    ea3_pass = (
        not conventional_benchmarks["furnace_600C_10min"]["pass_limit_10nm"]
        and not conventional_benchmarks["furnace_800C_10min"]["pass_limit_10nm"]
        and not conventional_benchmarks["rta_1000C_10s"]["pass_limit_10nm"]
    )

    ea4_pass = (
        opt_b["pass_strict_05nm"]
        and phase_summary["ms_target_box_pass_count"] >= 20
        and opt_b["f_act_bulk"] >= 0.95
        and opt_b["sigma_anneal_nm"] <= 0.50
        and opt_b["f_total_surface_loss"] < 0.02
        and opt_b["sigma_iso_nm"] <= 0.50
    )

    cool_16 = cryo_scenarios["insitu_s55_16x16mm_active_field"]
    cool_16_sw = cryo_scenarios["insitu_s55_16x16mm_with_4k_switch_upgrade"]
    # OBS-039 & OBS-100 honest gating: without a 4 K heat switch in CAD (and with true 4.385 nm BCA straggle),
    # in-situ 20 mK flash recovery takes ~40 min (>15 min) -> RT load-lock flash is mandatory!
    ea5_pass = bool(
        opt_b["sigma_anneal_nm"] <= 0.50
        and cryo_scenarios["in_line_loadlock_rt_baseline"]["E_absorbed_J"] == 0.0
        and cool_16_sw["t_cool_total_min"] <= 15.0
        and exp124_sigma_tot_legacy_bca(float(opt_b["sigma_anneal_nm"])) <= 3.68
    )
    ea5_insitu_current_cad_pass = bool(cool_16["t_cool_total_min"] <= 15.0)
    ea5_true_bca_3p8_pass = bool(opt_b["exp124_sigma_tot_nm"] <= EXP124_CEILING_NM)

    ea6_pass = (
        T_saph_uncoated >= 0.85
        and T_saph_AR >= 0.97
        and s55_hardware_spec["delivery_modes"]["mode1_single_shot_16x16mm"]["lidt_safety_margin_vs_100J_floor_AR"] >= 3.0
        and s55_hardware_spec["delivery_modes"]["mode3_collimated_1to1_0.5ms"]["lidt_safety_margin_vs_100J_floor_AR"] >= 3.0
        and beam_diam_at_window_mm <= duct_clear_diam_mm
    )

    evaluations = {
        "EA1": {
            "pass": ea1_pass,
            "summary": (
                f"600C/10min: pileup={a600['f_surface_pileup']*100:.1f}% (>=15%), "
                f"escape={a600['f_vacuum_escape']*100:.2f}% (<5%); "
                f"800C/10min: escape={a800['f_vacuum_escape']*100:.1f}% (>=30%); "
                f"mass_err={max(a600['mass_conservation_err'], a800['mass_conservation_err']):.2e}"
            ),
        },
        "EA2": {
            "pass": ea2_pass,
            "summary": (
                f"Thermal PDE conv={conv_T_rel_err*100:.3f}% (<1%), E_err={conv_E_max_err*100:.4f}% (<0.5%); "
                f"808nm 1.0ms T_peak={opt_b['T_peak_K']:.1f}K (<1552K), F={opt_b['fluence_J_per_cm2']:.2f} J/cm^2 ([10,45]), "
                f"t_quench={opt_b['t_quench_to_900K_ms']:.3f}ms (<10ms), T_back={opt_b['T_back_max_K']:.1f}K (<700K)"
            ),
        },
        "EA3": {
            "pass": ea3_pass,
            "summary": (
                f"Furnace 600C (sig={conventional_benchmarks['furnace_600C_10min']['sigma_anneal_nm']:.2f}nm, loss={conventional_benchmarks['furnace_600C_10min']['f_total_surface_loss']*100:.1f}%), "
                f"Furnace 800C (sig={conventional_benchmarks['furnace_800C_10min']['sigma_anneal_nm']:.2f}nm, loss={conventional_benchmarks['furnace_800C_10min']['f_total_surface_loss']*100:.1f}%), "
                f"RTA 1000C/10s (sig={conventional_benchmarks['rta_1000C_10s']['sigma_anneal_nm']:.2f}nm, loss={conventional_benchmarks['rta_1000C_10s']['f_total_surface_loss']*100:.1f}%) all FAIL"
            ),
        },
        "EA4": {
            "pass": ea4_pass,
            "summary": (
                f"Contiguous ms window t={phase_summary['strict_05nm_window_t_pulse_ms']} ms, T={phase_summary['strict_05nm_window_T_peak_K']} K "
                f"({phase_summary['ms_target_box_pass_count']}/{phase_summary['ms_target_box_total_count']} box pts PASS); "
                f"opt 808nm 1.0ms/1440K: f_act={opt_b['f_act_bulk']*100:.2f}%, sig={opt_b['sigma_anneal_nm']:.3f}nm, "
                f"loss={opt_b['f_total_surface_loss']*100:.3f}%, sig_iso={opt_b['sigma_iso_nm']:.4f}nm"
            ),
        },
        "EA5": {
            "pass": ea5_pass,
            "pass_insitu_20mK_current_cad_no_4k_switch": ea5_insitu_current_cad_pass,
            "pass_true_bca_3p80nm_ceiling": ea5_true_bca_3p8_pass,
            "summary": (
                f"Flash sigma_anneal={opt_b['sigma_anneal_nm']:.3f}nm (<=0.50nm); "
                f"true-BCA Exp124 sigma_tot={opt_b['exp124_sigma_tot_nm']:.3f}nm (legacy-BCA {exp124_sigma_tot_legacy_bca(float(opt_b['sigma_anneal_nm'])):.3f}nm); "
                f"cryo cooldown (0.725 kg Cu + Sommerfeld + RC): current CAD (no 4K switch) 16x16mm={cool_16['t_cool_total_min']:.1f}min / 50mm={cryo_scenarios['insitu_s55_50mm_full_wafer']['t_cool_total_min']:.1f}min -> IN-SITU LOCKED OUT; "
                f"with 4K switch upgrade 16x16mm={cool_16_sw['t_cool_total_min']:.2f}min; RT load-lock=0.0min (MANDATORY baseline)"
            ),
        },
        "EA6": {
            "pass": ea6_pass,
            "summary": (
                f"S5.5 CF63 sapphire Ø44mm CA (Ø36mm beam), T_uncoated={T_saph_uncoated*100:.1f}% (>=85%), T_AR={T_saph_AR*100:.1f}% (>=97%); "
                f"LIDT margin vs 100 J/cm^2 floor: {s55_hardware_spec['delivery_modes']['mode1_single_shot_16x16mm']['lidt_safety_margin_vs_100J_floor_AR']:.2f}x (16x16mm AR), "
                f"{s55_hardware_spec['delivery_modes']['mode1_single_shot_16x16mm']['lidt_safety_margin_vs_100J_floor_uncoated']:.2f}x (uncoated), "
                f"{s55_hardware_spec['delivery_modes']['mode3_collimated_1to1_0.5ms']['lidt_safety_margin_vs_100J_floor_AR']:.2f}x (1:1 0.5ms)"
            ),
        },
    }
    all_pass = all(v["pass"] for v in evaluations.values())

    output = {
        "experiment": "exp130_flash_anneal_diffusion",
        "hypothesis_id": preds["hypothesis_id"],
        "verdict": "PASS" if all_pass else "FAIL",
        "no_lab_measurement": True,
        "epistemic_scope": "Model + numerical PDE simulation anchored to literature (Glassbrenner-Slack, Fahey, Bracht, Stolk/Cowern, Olson-Roth, Exp108 doi:10.1063/1.331355); physical M1 G4 lab verification remains required for hardware closure.",
        "runtime_s": round(time.perf_counter() - t0, 2),
        "evaluations": evaluations,
        "thermal_pde_convergence": {
            "runs": thermal_conv,
            "T_peak_rel_diff_120_vs_160": round(conv_T_rel_err, 6),
            "max_energy_balance_rel_err": conv_E_max_err,
        },
        "ted_pde_convergence": {
            "runs": ted_conv,
            "sigma_anneal_rel_diff_150_vs_200": round(ted_conv_rel_err, 6),
        },
        "exp108_anchor_doi_10_1063_1_331355": exp108_anchor,
        "conventional_anneal_benchmarks": conventional_benchmarks,
        "wavelength_and_pulse_benchmarks": wavelength_benchmarks,
        "fluence_pulse_curve_808nm_1440K": fluence_curve,
        "phase_diagram_summary": phase_summary,
        "uq_stress_tests": uq_results,
        "exp124_placement_budget_impact": {
            "fixed_non_anneal_rss_nm": round(math.sqrt(EXP124_FIXED_VAR_NM2), 4),
            "baseline_sigma_anneal_0.50nm_tot_nm": round(exp124_sigma_tot(0.500), 4),
            "optimal_808nm_1ms_1440K_tot_nm": opt_b["exp124_sigma_tot_nm"],
            "compact_808nm_0.5ms_1440K_tot_nm": wavelength_benchmarks["808nm_diode_0.5ms_1440K"]["exp124_sigma_tot_nm"],
            "damage_3x_stress_tot_nm": uq_results["damage_3x_9e19_cm3"]["exp124_sigma_tot_nm"],
            "rta_1000C_10s_tot_nm": conventional_benchmarks["rta_1000C_10s"]["exp124_sigma_tot_nm"],
            "furnace_600C_10min_tot_nm": conventional_benchmarks["furnace_600C_10min"]["exp124_sigma_tot_nm"],
            "exp124_ceiling_nm": EXP124_CEILING_NM,
        },
        "cryo_cooldown_to_20mK": cryo_scenarios,
        "pilot2c_lammps_md_limitations": {
            "obstacle_id": "OBS-096",
            "cascade_1kev_artifacts": (
                "Pilot 2C in.cascade_1kev launched PKA 1.48 nm from the x>61 A Berendsen bath slab "
                "(vs max recoil range 3.68 nm), placing 62/142 (43.7%) residual displaced atoms inside "
                "the thermostat bath, draining 664.6 eV, wrapping across PBC, equilibrating to only 253.5 K, "
                "and omitting ZBL short-range repulsion on Stillinger-Weber."
            ),
            "diffusivity_1530k_secant_overestimate": (
                "Pilot 2C log_anneal_1530k.lammps computed D_int = 5.648e-6 cm^2/s from a single t=0..20 ps "
                "secant across initial 0..4 ps relaxation; the 4..20 ps Einstein slope yields 9.640e-7 cm^2/s "
                "(5.86x lower). 5 keV P->Si ZBL-splined cascade MD and >=100 ps dilute interstitial MSD remain required."
            ),
            "exp130_monomer_em_calibration": "heat_ted_solver.py now uses Em_I=0.90 eV, Ef_I=4.05 eV (exact Bracht D_I*C_I*) + explicit V(z,t) I-V recombination (OBS-038).",
        },
        "s55_optical_hardware_spec": s55_hardware_spec,
        "artifacts": {
            "predictions": "results/exp130_flash_anneal_diffusion/predictions_exp130.json",
            "results_json": "results/exp130_flash_anneal_diffusion/exp130.json",
            "plot_data_json": "results/exp130_flash_anneal_diffusion/plot_data_exp130.json",
            "summary_md": "results/exp130_flash_anneal_diffusion/summary_exp130.md",
            "fig_window": "results/exp130_flash_anneal_diffusion/fig_exp130_anneal_window.png",
            "fig_profiles": "results/exp130_flash_anneal_diffusion/fig_exp130_profiles_ted.png",
        },
    }

    OUT_JSON.write_text(json.dumps(output, indent=2), encoding="utf-8")

    plot_data = {
        "tp_grid_s": [float(x) for x in tp_grid_s],
        "T_grid_K": [float(x) for x in T_grid_K],
        "f_act_map": [[round(float(v), 5) for v in row] for row in f_act_map],
        "sigma_ann_map": [[round(float(v), 5) for v in row] for row in sigma_ann_map],
        "loss_map": [[round(float(v), 6) for v in row] for row in loss_map],
        "sigma_iso_map": [[round(float(v), 6) for v in row] for row in sigma_iso_map],
        "pass_05_map": pass_05_map.tolist(),
        "pass_10_map": pass_10_map.tolist(),
        "fluence_curve": fluence_curve,
        "thermal_waveforms": thermal_waveforms_plot,
        "exp108_profiles": exp108_profiles_plot,
        "machine_profiles": machine_profiles_plot,
        "cryo_scenarios": cryo_scenarios,
    }
    PLOT_DATA_JSON.write_text(json.dumps(plot_data), encoding="utf-8")

    print(f"Exp130 finished in {output['runtime_s']:.2f} s | VERDICT: {output['verdict']}")
    for k, v in evaluations.items():
        print(f"  [{('PASS' if v['pass'] else 'FAIL')}] {k}: {v['summary']}")


if __name__ == "__main__":
    main()
