"""Runner for Exp133 (H151): Coupled Multi-Physics Vibration, Thermal Drift & Control.

Executes full FEM + 6-DOF MDOF + closed-loop control + 2D (k_bellows, k_braid) sweep
+ thermal drift + Exp124 placement budget closure, evaluates pre-registered CY1-CY8
verdicts, and writes results/exp133_coupled_vibration_thermal/exp133.json.
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

import dynamics133 as d

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results" / "exp133_coupled_vibration_thermal"
PRED_PATH = RESULTS_DIR / "predictions_exp133.json"
OUT_JSON = RESULTS_DIR / "exp133.json"


def downsample_log_spectrum(
    freqs_hz: np.ndarray,
    psd_nm2_hz: np.ndarray,
    cum_nm: np.ndarray,
    n_pts: int = 420,
) -> dict[str, list[float]]:
    """Downsample spectrum onto log-spaced grid while preserving sharp 1.4 Hz comb peaks."""
    f_log = np.geomspace(float(freqs_hz[0]), float(freqs_hz[-1]), n_pts)
    # Also include exact 1.4 Hz harmonic bins and structural resonances so peaks aren't clipped
    special_f = [1.4 * n for n in range(1, 21)] + [1.5, 4.5, 7.0, 16.0, 18.0, 50.0, 118.2, 180.0]
    all_f = np.unique(np.concatenate([f_log, [f for f in special_f if freqs_hz[0] <= f <= freqs_hz[-1]]]))

    idx = np.searchsorted(freqs_hz, all_f)
    idx = np.clip(idx, 0, len(freqs_hz) - 1)
    # Local max-hold in +/-2 bin window for ASD so narrow Lorentzian peaks render crisply
    asd_vals = []
    cum_vals = []
    f_vals = []
    for k in idx:
        lo = max(0, int(k) - 1)
        hi = min(len(freqs_hz), int(k) + 2)
        p_max = float(np.max(psd_nm2_hz[lo:hi]))
        f_vals.append(round(float(freqs_hz[k]), 5))
        asd_vals.append(round(math.sqrt(max(p_max, 0.0)), 6))
        cum_vals.append(round(float(cum_nm[k]), 6))
    return {
        "freq_hz": f_vals,
        "asd_nm_per_rtHz": asd_vals,
        "cum_rms_nm": cum_vals,
    }


def strip_private_arrays(res: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in res.items() if not k.startswith("_")}


def bisect_stiffness_limit(
    param_name: str,
    fixed_other: float,
    cad_anchors: dict[str, Any],
    col_fem: dict[str, Any],
    snout: dict[str, float],
    freqs_hz: np.ndarray,
    target_nm: float = 0.50,
    lo_log10: float = 1.0,
    hi_log10: float = 7.0,
) -> dict[str, float]:
    """Find exact upper stiffness bound where max(sigma_stage, sigma_pointing) <= target_nm."""
    def eval_at(val: float) -> tuple[float, float]:
        if param_name == "k_braid":
            cfg = d.MachineConfig("bs", "", fixed_other, val, True, True, True, 25.0, "VC-E")
        else:
            cfg = d.MachineConfig("bs", "", val, fixed_other, True, True, True, 25.0, "VC-E")
        r = d.evaluate_configuration(cfg, cad_anchors, col_fem, snout, freqs_hz)
        return r["sigma_stage_nm"], r["sigma_pointing_nm"]

    lo, hi = lo_log10, hi_log10
    for _ in range(22):
        mid = 0.5 * (lo + hi)
        st, pt = eval_at(10.0 ** mid)
        if max(st, pt) <= target_nm:
            lo = mid
        else:
            hi = mid
    k_lim = 10.0 ** lo
    st_lim, pt_lim = eval_at(k_lim)
    return {
        "k_max_N_m": k_lim,
        "sigma_stage_at_limit_nm": st_lim,
        "sigma_pointing_at_limit_nm": pt_lim,
        "governing_metric": "sigma_stage" if st_lim >= pt_lim else "sigma_pointing",
    }


def main() -> None:
    t0 = time.perf_counter()
    assert PRED_PATH.exists(), f"Missing pre-registered predictions: {PRED_PATH}"
    preds_doc = json.loads(PRED_PATH.read_text(encoding="utf-8"))

    # 1. Load real CAD v3.0 & Exp124 anchors
    anc = d.load_cad_and_exp124_anchors()

    # 2. Conforming Euler-Bernoulli FEM & mesh convergence check (19 vs 40 vs 80 elems)
    fem20 = d.solve_column_fem(anc, refine_factor=0, include_flange_compliance=True)
    fem40 = d.solve_column_fem(anc, refine_factor=1, include_flange_compliance=True)
    fem80 = d.solve_column_fem(anc, refine_factor=2, include_flange_compliance=True)
    fem40_rigid = d.solve_column_fem(anc, refine_factor=1, include_flange_compliance=False)
    snout = d.compute_lower_snout_and_chamber_compliance(anc)

    mesh_conv_rel_err = max(
        abs(fem40["f1_hz"] - fem20["f1_hz"]) / fem40["f1_hz"],
        abs(fem80["f1_hz"] - fem40["f1_hz"]) / fem40["f1_hz"],
    )

    # 3. Exact FFT frequency grid: fs = 1000 Hz, T = 128 s -> df = 1/128 Hz, f in [0.203125, 500.0] Hz
    df = 1.0 / 128.0
    freqs = np.arange(26, 64001) * df

    # 4. Evaluate 5 primary architectural configurations on VC-E (+ rigid nominal instability check)
    k_ovc_rigid = anc["k_ovc_rigid_eff_N_m"]
    k_cu_rigid = anc["k_cold_finger_rigid_N_m"]
    # CAD v4.0 nominal decoupling: 2,000 N/m edge-welded CF63 bellows + 52.7 N/m OFHC braids (design spec <= 60 N/m)
    braid_design = d.compute_ofhc_braid_design(
        n_braids=4, strands_per_braid=2550, strand_diam_um=50.0,
        braid_length_mm=100.0, rrr=200.0, friction_factor=12.0,
    )
    k_bellows_v4 = 2000.0
    k_braid_v4 = 60.0  # Conservative design rating (actual 4x2550x50um braid computes 52.7 N/m)

    configs_vce = [
        d.MachineConfig(
            "CFG1_RIGID_OPEN",
            "CAD v3.0 Rijit PT420 + Açık Çevrim",
            k_ovc_rigid, k_cu_rigid, False, False, False, 0.0, "VC-E",
        ),
        d.MachineConfig(
            "CFG2_DECOUPLED_OPEN",
            "Mekanik Ayrık PT420 + Pasif İzolasyon (Açık Çevrim)",
            k_bellows_v4, k_braid_v4, True, False, False, 0.0, "VC-E",
        ),
        d.MachineConfig(
            "CFG3_ACTIVE_ISO_PID",
            "Ayrık PT420 + Aktif Tabla + Piezo PID",
            k_bellows_v4, k_braid_v4, True, True, True, 0.0, "VC-E",
        ),
        d.MachineConfig(
            "CFG4_V4_FULL_CTRL",
            "CAD v4.0 Tam Mimari (Ayrık + Aktif Tabla + PID + 1,4 Hz FF)",
            k_bellows_v4, k_braid_v4, True, True, True, 25.0, "VC-E",
        ),
        d.MachineConfig(
            "CFG5_RIGID_FULL_CTRL",
            "Rijit PT420 + Tam Kontrol (Yeniden Ayarlı Servo)",
            k_ovc_rigid, k_cu_rigid, False, True, True, 25.0, "VC-E",
            retune_for_rigid=True,
        ),
    ]

    cfg_results: dict[str, Any] = {}
    spectra_for_plot: dict[str, Any] = {}
    for cfg in configs_vce:
        do_parseval = cfg.name in ("CFG4_V4_FULL_CTRL", "CFG1_RIGID_OPEN")
        r = d.evaluate_configuration(cfg, anc, fem40, snout, freqs, run_parseval_check=do_parseval)
        cfg_results[cfg.name] = strip_private_arrays(r)
        if cfg.name in ("CFG1_RIGID_OPEN", "CFG2_DECOUPLED_OPEN", "CFG3_ACTIVE_ISO_PID", "CFG4_V4_FULL_CTRL"):
            spectra_for_plot[cfg.name] = {
                "stage": downsample_log_spectrum(freqs, r["_S_stage_nm2_hz"], r["_cum_stage_nm"]),
                "pointing": downsample_log_spectrum(freqs, r["_S_point_nm2_hz"], r["_cum_point_nm"]),
            }

    # Also check un-retuned nominal controller on rigid Cu rod (demonstrates 180->411 Hz notch miss)
    cfg5_nom = d.MachineConfig(
        "CFG5_RIGID_NOMINAL_CTRL",
        "Rijit PT420 + Nominal 180 Hz Servo",
        k_ovc_rigid, k_cu_rigid, False, True, True, 25.0, "VC-E",
        retune_for_rigid=False,
    )
    r_cfg5_nom = d.evaluate_configuration(cfg5_nom, anc, fem40, snout, freqs)
    cfg_results["CFG5_RIGID_NOMINAL_CTRL"] = strip_private_arrays(r_cfg5_nom)

    # 5. Cleanroom floor sensitivity sweep (VC-C / VC-E / VC-G) on CFG4 and CFG3
    vc_sweep: dict[str, Any] = {}
    for vc in ("VC-C", "VC-E", "VC-G"):
        c_v4 = d.MachineConfig(f"CFG4_{vc}", f"CAD v4.0 ({vc})", k_bellows_v4, k_braid_v4, True, True, True, 25.0, vc)
        r_v4 = d.evaluate_configuration(c_v4, anc, fem40, snout, freqs)
        c_v3 = d.MachineConfig(f"CFG3_{vc}", f"Aktif+PID ({vc})", k_bellows_v4, k_braid_v4, True, True, True, 0.0, vc)
        r_v3 = d.evaluate_configuration(c_v3, anc, fem40, snout, freqs)
        s_fl = d.seismic_floor_disp_psd(freqs, vc)
        vc_sweep[vc] = {
            "vc_velocity_um_s": d.VC_VELOCITY_UM_S[vc],
            "floor_rms_disp_um": float(math.sqrt(np.sum(s_fl) * df) * 1e6),
            "cfg4_stage_nm": r_v4["sigma_stage_nm"],
            "cfg4_pointing_nm": r_v4["sigma_pointing_nm"],
            "cfg4_mech_rss_nm": r_v4["sigma_mech_rss_nm"],
            "cfg4_mech_coherent_nm": r_v4["sigma_mech_coherent_nm"],
            "cfg4_passes_0p50_nm": (r_v4["sigma_stage_nm"] <= 0.50) and (r_v4["sigma_pointing_nm"] <= 0.50),
            "cfg3_stage_nm": r_v3["sigma_stage_nm"],
            "cfg3_pointing_nm": r_v3["sigma_pointing_nm"],
        }

    # 6. 2D (k_bellows, k_braid) decoupling stiffness sweep (13x13 grid on fast df=0.025 Hz grid)
    #    plus exact bisection of k_bellows_max and k_braid_max at full df=1/128 Hz resolution!
    freqs_fast = np.arange(8, 20001) * 0.025  # 0.20 .. 500.0 Hz (df=0.025 Hz -> resolves 1.4 Hz comb cleanly)
    kb_vals = [float(10.0 ** x) for x in np.linspace(1.0, 7.0, 13)]   # k_braid: 10 .. 1e7 N/m
    kbl_vals = [float(10.0 ** x) for x in np.linspace(2.0, 7.0, 13)]  # k_bellows: 100 .. 1e7 N/m

    grid_stage = []
    grid_point = []
    grid_max = []
    for kb in kb_vals:
        row_s, row_p, row_m = [], [], []
        for kbl in kbl_vals:
            c_sw = d.MachineConfig("sw2d", "", kbl, kb, True, True, True, 25.0, "VC-E", retune_for_rigid=False)
            r_sw = d.evaluate_configuration(c_sw, anc, fem40, snout, freqs_fast)
            s_v = round(r_sw["sigma_stage_nm"], 5)
            p_v = round(r_sw["sigma_pointing_nm"], 5)
            row_s.append(s_v)
            row_p.append(p_v)
            row_m.append(round(max(s_v, p_v), 5))
        grid_stage.append(row_s)
        grid_point.append(row_p)
        grid_max.append(row_m)

    # Exact full-resolution bisection bounds (at nominal decoupled value of the other stiffness)
    lim_braid = bisect_stiffness_limit("k_braid", k_bellows_v4, anc, fem40, snout, freqs, 0.50, 1.0, 6.0)
    lim_bellows = bisect_stiffness_limit("k_bellows", k_braid_v4, anc, fem40, snout, freqs, 0.50, 2.0, 7.0)

    # Quantify direct sensitivity ratio: delta(sigma_stage) for 1e5 N/m perturbation in k_braid vs k_bellows
    r_base = cfg_results["CFG4_V4_FULL_CTRL"]
    r_kb_1e5 = d.evaluate_configuration(
        d.MachineConfig("sens_kb", "", k_bellows_v4, 1.0e5, True, True, True, 25.0, "VC-E"),
        anc, fem40, snout, freqs,
    )
    r_kbl_1e5 = d.evaluate_configuration(
        d.MachineConfig("sens_kbl", "", 1.0e5, k_braid_v4, True, True, True, 25.0, "VC-E"),
        anc, fem40, snout, freqs,
    )
    d_stg_braid = abs(r_kb_1e5["sigma_stage_nm"] - r_base["sigma_stage_nm"])
    d_stg_bellows = abs(r_kbl_1e5["sigma_stage_nm"] - r_base["sigma_stage_nm"])
    braid_over_bellows_stage_sensitivity = d_stg_braid / max(d_stg_bellows, 1e-12)

    # 7. Coupled Thermal Drift Sweep
    thermal_cases: dict[str, Any] = {}
    for mode in ("naive_ss316_uncompensated", "v3_zerodur_invar_cryo"):
        thermal_cases[mode] = {}
        for dT_mK in (10.0, 50.0, 100.0):
            key = f"dT_{int(dT_mK)}mK"
            thermal_cases[mode][key] = d.evaluate_thermal_drift(
                anc, dT_room_amp_mK=dT_mK, T_hvac_s=900.0, t_fiducial_s=300.0, material_mode=mode
            )

    fiducial_sweep = {}
    for tf in (60.0, 120.0, 300.0, 600.0):
        fiducial_sweep[f"tfid_{int(tf)}s"] = d.evaluate_thermal_drift(
            anc, dT_room_amp_mK=10.0, T_hvac_s=900.0, t_fiducial_s=tf, material_mode="v3_zerodur_invar_cryo"
        )

    th_naive_10 = thermal_cases["naive_ss316_uncompensated"]["dT_10mK"]
    th_v3_10 = thermal_cases["v3_zerodur_invar_cryo"]["dT_10mK"]

    # 8. Exp124 5 keV Total Placement Budget Closure
    r_cfg4 = cfg_results["CFG4_V4_FULL_CTRL"]
    exp124_closure_cfg4 = d.compute_exp124_budget_closure(
        anc,
        sigma_stage_nm=r_cfg4["sigma_stage_nm"],
        sigma_pointing_nm=r_cfg4["sigma_pointing_nm"],
        sigma_thermal_nm=th_v3_10["sigma_thermal_nm"],
    )
    r_cfg1 = cfg_results["CFG1_RIGID_OPEN"]
    exp124_closure_cfg1 = d.compute_exp124_budget_closure(
        anc,
        sigma_stage_nm=r_cfg1["sigma_stage_nm"],
        sigma_pointing_nm=r_cfg1["sigma_pointing_nm"],
        sigma_thermal_nm=th_naive_10["sigma_thermal_nm"],
    )

    # 9. Explicit CAD v4.0 Mechanical Decoupling Engineering Specification
    cad_v4_spec = {
        "pt420_remote_rotary_valve": {
            "mandatory": True,
            "flex_he_line_length_mm": 600.0,
            "valve_box_offset_from_dr_mm": 500.0,
            "hf_force_reduction_factor": 12.7,
            "fundamental_1p4hz_reduction_factor": 3.6,
        },
        "s6_cryo_bridge_ovc_bellows": {
            "replaces_v3_part": "s6_cryo_bridge_ovc (rigid Ø56×3 SS tube, k=4.96 MN/m)",
            "type": "Edge-welded 316L UHV CF63 hydro/edge-welded bellows",
            "id_mm": 44.0,
            "od_mm": 68.0,
            "active_bellows_length_mm": 120.0,
            "convolutions": 28,
            "ply_thickness_mm": 0.15,
            "design_k_bellows_N_m": k_bellows_v4,
            "max_allowable_k_bellows_N_m": round(lim_bellows["k_max_N_m"], 1),
            "safety_factor": round(lim_bellows["k_max_N_m"] / k_bellows_v4, 2),
        },
        "s6_mxc_cold_finger_braids": {
            "replaces_v3_part": "s6_mxc_cold_finger (solid Ø7×497 mm OFHC Cu rod, k=9.06 MN/m)",
            "architecture": "397 mm Ø12 mm DR-side OFHC Cu busbar + 4× parallel S-loop OFHC Cu braids (100 mm) inside 36 mm magnet split gap",
            "n_parallel_braids": braid_design["n_braids"],
            "strands_per_braid": braid_design["strands_per_braid"],
            "strand_diameter_um": braid_design["strand_diam_um"],
            "braid_free_length_mm": braid_design["braid_length_mm"],
            "total_cu_cross_section_mm2": round(braid_design["total_cu_area_mm2"], 2),
            "rrr_min": braid_design["rrr"],
            "computed_k_braid_N_m": round(braid_design["k_braid_N_m"], 2),
            "design_rating_k_braid_N_m": k_braid_v4,
            "max_allowable_k_braid_N_m": round(lim_braid["k_max_N_m"], 1),
            "safety_factor": round(lim_braid["k_max_N_m"] / k_braid_v4, 1),
            "G_braid_20mK_mW_K": round(braid_design["G_braid_20mK_mW_K"], 3),
            "G_total_link_20mK_mW_K": round(braid_design["G_total_link_20mK_mW_K"], 3),
            "dT_wafer_at_2p5uW_mK": round(braid_design["dT_at_2p5uW_mK"], 2),
        },
        "s4_active_isolation_and_control": {
            "pneumatic_air_spring_f0_hz": 1.50,
            "active_table_bandwidth_hz": [0.5, 100.0],
            "piezo_stage_loaded_f1_hz": 180.0,
            "piezo_servo_crossover_hz": round(r_cfg4["control_margins"]["f_crossover_hz"], 2),
            "piezo_notch_hz": 180.0,
            "piezo_phase_margin_deg": round(r_cfg4["control_margins"]["phase_margin_deg"], 2),
            "piezo_gain_margin_db": round(r_cfg4["control_margins"]["gain_margin_db"], 2),
            "piezo_S_inf": round(r_cfg4["control_margins"]["sensitivity_peak_S_inf"], 3),
            "harmonic_ff_harmonics": "n = 1..15 (1.4..21.0 Hz, 25 dB coherent cancellation via rotary-valve phase encoder)",
            "min_cleanroom_floor_grade": "VC-E (3.1 um/s 1/3-octave RMS velocity; VC-G recommended for >3.5x pointing margin)",
            "max_fiducial_rezero_interval_s": 300.0,
            "cleanroom_hvac_spec_mK": 10.0,
            "column_additional_brace_needed": False,
            "column_f1_hz": round(fem40["f1_hz"], 2),
        },
    }

    # 10. Objective Pre-Registered Verdict Evaluation (CY1-CY8)
    passive_modes = r_cfg4["passive_modal_freqs_hz"]
    cm4 = r_cfg4["control_margins"]
    parseval4 = r_cfg4["parseval"]

    verdicts = {
        "CY1_modal_realism": bool(
            all(f > 0.0 for f in passive_modes)
            and (40.0 <= fem40["f1_hz"] <= 350.0)
            and (1.0 <= passive_modes[0] <= 2.5)
            and (mesh_conv_rel_err < 0.005)
            and (parseval4["max_rel_err"] < 0.01)
        ),
        "CY2_rigid_pt420_fails": bool(
            (cfg_results["CFG1_RIGID_OPEN"]["sigma_stage_nm"] > 50.0)
            and (cfg_results["CFG5_RIGID_FULL_CTRL"]["sigma_stage_nm"] > 2.0)
        ),
        "CY3_decoupled_open_still_exceeds": bool(
            (cfg_results["CFG1_RIGID_OPEN"]["sigma_stage_nm"] / cfg_results["CFG2_DECOUPLED_OPEN"]["sigma_stage_nm"] > 100.0)
            and (cfg_results["CFG2_DECOUPLED_OPEN"]["sigma_stage_nm"] > 0.50)
        ),
        "CY4_closed_loop_meets_budget_vce": bool(
            (r_cfg4["sigma_stage_nm"] <= 0.50)
            and (r_cfg4["sigma_pointing_nm"] <= 0.50)
            and (cm4["phase_margin_deg"] >= 45.0)
            and (cm4["gain_margin_db"] >= 6.0)
            and (cm4["sensitivity_peak_S_inf"] <= 2.0)
            and cm4["is_stable"]
        ),
        "CY5_cleanroom_floor_sensitivity": bool(
            (not vc_sweep["VC-C"]["cfg4_passes_0p50_nm"])
            and vc_sweep["VC-E"]["cfg4_passes_0p50_nm"]
            and vc_sweep["VC-G"]["cfg4_passes_0p50_nm"]
            and (vc_sweep["VC-E"]["cfg4_pointing_nm"] / vc_sweep["VC-G"]["cfg4_pointing_nm"] >= 1.5)
        ),
        "CY6_decoupling_stiffness_envelope": bool(
            (lim_bellows["k_max_N_m"] > k_bellows_v4)
            and (lim_braid["k_max_N_m"] > k_braid_v4)
            and (braid_over_bellows_stage_sensitivity > 10.0)
        ),
        "CY7_thermal_drift_budget": bool(
            (th_naive_10["sigma_thermal_nm"] > 0.30)
            and (th_v3_10["sigma_thermal_nm"] <= 0.30)
        ),
        "CY8_exp124_total_closure": bool(
            (exp124_closure_cfg4["ArchB_HiRes_Ti0p25_10ms"]["sigma_total_exp133_nm"] <= 3.674)
            and (exp124_closure_cfg4["ArchB_HiRes_Ti0p5_15ms"]["sigma_total_exp133_nm"] <= 3.80)
        ),
    }

    mandatory_keys = [
        "CY1_modal_realism", "CY2_rigid_pt420_fails", "CY4_closed_loop_meets_budget_vce",
        "CY6_decoupling_stiffness_envelope", "CY7_thermal_drift_budget", "CY8_exp124_total_closure",
    ]
    success_rule_met = all(verdicts[k] for k in mandatory_keys)
    all_eight_pass = all(verdicts.values())

    # Assemble clean portable JSON output (zero absolute host paths!)
    cad_summary = {k: v for k, v in anc.items() if k != "parts_raw"}
    out = {
        "experiment": "exp133_coupled_vibration_thermal",
        "hypothesis_id": "H151",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runtime_s": round(time.perf_counter() - t0, 3),
        "no_lab_measurement": True,
        "epistemic_tags": ["{Model}", "{Sayısal-Simülasyon}", "{Literatür}"],
        "predictions_ref": "results/exp133_coupled_vibration_thermal/predictions_exp133.json",
        "cad_anchors": cad_summary,
        "column_fem": {
            "n_elem": fem40["n_elem"],
            "L_upper_m": fem40["L_upper_m"],
            "m_upper_total_kg": fem40["m_upper_total_kg"],
            "k_rot_root_Nm_rad": fem40["k_rot_root_Nm_rad"],
            "f1_flanged_hz": fem40["f1_hz"],
            "f2_flanged_hz": fem40["f2_hz"],
            "f3_flanged_hz": fem40["f3_hz"],
            "f1_rigid_root_hz": fem40_rigid["f1_hz"],
            "m_col_1_kg": fem40["m_col_1_kg"],
            "eff_modal_mass_fraction": fem40["eff_modal_mass_fraction"],
            "mesh_convergence": {
                "n_elem_coarse": fem20["n_elem"],
                "f1_coarse_hz": fem20["f1_hz"],
                "n_elem_nominal": fem40["n_elem"],
                "f1_nominal_hz": fem40["f1_hz"],
                "n_elem_fine": fem80["n_elem"],
                "f1_fine_hz": fem80["f1_hz"],
                "max_rel_diff": mesh_conv_rel_err,
            },
            "lower_snout_and_chamber": snout,
        },
        "configurations_vce": cfg_results,
        "vc_floor_sweep": vc_sweep,
        "stiffness_sweep_2d": {
            "k_braid_grid_N_m": kb_vals,
            "k_bellows_grid_N_m": kbl_vals,
            "sigma_stage_grid_nm": grid_stage,
            "sigma_pointing_grid_nm": grid_point,
            "sigma_max_grid_nm": grid_max,
            "exact_limits_vce": {
                "k_braid_max_at_kbel2000": lim_braid,
                "k_bellows_max_at_kbraid60": lim_bellows,
                "braid_over_bellows_stage_sensitivity_ratio": braid_over_bellows_stage_sensitivity,
            },
        },
        "ofhc_braid_physics": braid_design,
        "thermal_drift": {
            "material_comparison": thermal_cases,
            "fiducial_interval_sweep_10mK": fiducial_sweep,
        },
        "exp124_budget_closure": {
            "CFG4_V4_FULL_CTRL_VCE": exp124_closure_cfg4,
            "CFG1_RIGID_OPEN_VCE": exp124_closure_cfg1,
        },
        "cad_v4_mechanical_decoupling_spec": cad_v4_spec,
        "verdicts": verdicts,
        "success_rule_met": success_rule_met,
        "all_eight_verdicts_pass": all_eight_pass,
        "plot_spectra": spectra_for_plot,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Exp133 finished in {out['runtime_s']:.2f} s -> {OUT_JSON.relative_to(ROOT)}")
    print(f"Column FEM f1 = {fem40['f1_hz']:.3f} Hz (mesh err = {mesh_conv_rel_err:.2e}), f1_rigid = {fem40_rigid['f1_hz']:.2f} Hz")
    print(f"CFG1 Rigid Open   : stage={r_cfg1['sigma_stage_nm']:.2f} nm, point={r_cfg1['sigma_pointing_nm']:.2f} nm")
    print(f"CFG2 Decoupled Op : stage={cfg_results['CFG2_DECOUPLED_OPEN']['sigma_stage_nm']:.4f} nm, point={cfg_results['CFG2_DECOUPLED_OPEN']['sigma_pointing_nm']:.4f} nm")
    print(f"CFG3 Active+PID   : stage={cfg_results['CFG3_ACTIVE_ISO_PID']['sigma_stage_nm']:.4f} nm, point={cfg_results['CFG3_ACTIVE_ISO_PID']['sigma_pointing_nm']:.4f} nm")
    print(f"CFG4 v4 Full VC-E : stage={r_cfg4['sigma_stage_nm']:.4f} nm, point={r_cfg4['sigma_pointing_nm']:.4f} nm, thermal={th_v3_10['sigma_thermal_nm']:.4f} nm")
    print(f"CFG5 Rigid+Ctrl   : stage={cfg_results['CFG5_RIGID_FULL_CTRL']['sigma_stage_nm']:.2f} nm, point={cfg_results['CFG5_RIGID_FULL_CTRL']['sigma_pointing_nm']:.2f} nm")
    print(f"Margins (CFG4)    : fc={cm4['f_crossover_hz']:.2f} Hz, PM={cm4['phase_margin_deg']:.2f} deg, GM={cm4['gain_margin_db']:.2f} dB, S_inf={cm4['sensitivity_peak_S_inf']:.3f}")
    print(f"Parseval (CFG4)   : max_rel_err={parseval4['max_rel_err']:.2e}")
    print(f"Stiffness bounds  : k_bellows_max={lim_bellows['k_max_N_m']:.1f} N/m, k_braid_max={lim_braid['k_max_N_m']:.1f} N/m (sens ratio={braid_over_bellows_stage_sensitivity:.1f}x)")
    print(f"VC Sweep (CFG4)   : VC-C ptg={vc_sweep['VC-C']['cfg4_pointing_nm']:.4f} | VC-E ptg={vc_sweep['VC-E']['cfg4_pointing_nm']:.4f} | VC-G ptg={vc_sweep['VC-G']['cfg4_pointing_nm']:.4f}")
    print(f"Exp124 Closure    : HiRes={exp124_closure_cfg4['ArchB_HiRes_Ti0p25_10ms']['sigma_total_exp133_nm']:.4f} nm (orig 3.6740) | Canon={exp124_closure_cfg4['ArchB_HiRes_Ti0p5_15ms']['sigma_total_exp133_nm']:.4f} nm (orig 3.7155)")
    print("Verdicts:", verdicts)
    print(f"success_rule_met={success_rule_met}, all_eight_pass={all_eight_pass}")


if __name__ == "__main__":
    main()
