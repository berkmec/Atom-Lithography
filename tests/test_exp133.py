"""Automated verification suite for Exp133 (H151): Coupled Vibration, FEM, Thermal & Control."""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = ROOT / "experiments" / "exp133_coupled_vibration_thermal"
RES_DIR = ROOT / "results" / "exp133_coupled_vibration_thermal"
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

import dynamics133 as d  # noqa: E402

PRED_PATH = RES_DIR / "predictions_exp133.json"
JSON_PATH = RES_DIR / "exp133.json"
SUMMARY_PATH = RES_DIR / "summary_exp133.md"
FIG1_PATH = RES_DIR / "fig_exp133_psd_jitter.png"
FIG2_PATH = RES_DIR / "fig_exp133_isolation_budget.png"


def _load_json(path: Path) -> dict:
    assert path.exists(), f"Missing file: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _png_size(path: Path) -> tuple[int, int]:
    raw = path.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG signature: {path}"
    w, h = struct.unpack(">II", raw[16:24])
    return w, h


def _check_gfm_tables(md_text: str) -> list[str]:
    """Validate every GFM table has consistent pipe column counts across header/sep/rows."""
    errors: list[str] = []
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and line.endswith("|"):
            block = []
            start_ln = i + 1
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                block.append(lines[i].strip())
                i += 1
            if len(block) < 2:
                errors.append(f"Line {start_ln}: incomplete GFM table (<2 rows)")
                continue
            ncols = len([c for c in block[0].split("|")[1:-1]])
            sep_cells = [c.strip() for c in block[1].split("|")[1:-1]]
            if len(sep_cells) != ncols:
                errors.append(f"Line {start_ln + 1}: separator cols {len(sep_cells)} != header {ncols}")
            for cell in sep_cells:
                stripped = cell.replace(":", "").replace("-", "")
                if stripped != "" or "-" not in cell:
                    errors.append(f"Line {start_ln + 1}: malformed separator cell '{cell}'")
            for r_idx, row in enumerate(block[2:], start=2):
                rcells = row.split("|")[1:-1]
                if len(rcells) != ncols:
                    errors.append(f"Line {start_ln + r_idx}: row cols {len(rcells)} != header {ncols}")
        else:
            i += 1
    return errors


def test_predictions_pre_registered_and_epistemic_tags() -> None:
    pred = _load_json(PRED_PATH)
    res = _load_json(JSON_PATH)
    assert pred["no_lab_measurement"] is True
    assert res["no_lab_measurement"] is True
    assert pred["hypothesis_id"] == "H151"
    assert res["hypothesis_id"] == "H151"
    for key in [
        "CY1_modal_realism",
        "CY2_rigid_pt420_fails",
        "CY3_decoupled_open_still_exceeds",
        "CY4_closed_loop_meets_budget_vce",
        "CY5_cleanroom_floor_sensitivity",
        "CY6_decoupling_stiffness_envelope",
        "CY7_thermal_drift_budget",
        "CY8_exp124_total_closure",
    ]:
        assert key in pred["predictions"], f"Missing pre-registered prediction: {key}"
        assert key in res["verdicts"], f"Missing verdict: {key}"


def test_portability_no_hardcoded_user_paths() -> None:
    _u = chr(98) + "erk"
    forbidden = [
        "/" + "home/" + _u,
        "/" + "run/" + "media/" + _u,
    ]
    files_to_scan = (
        list(EXP_DIR.glob("*.py"))
        + list(RES_DIR.glob("*.json"))
        + list(RES_DIR.glob("*.md"))
        + [Path(__file__).resolve()]
    )
    assert len(files_to_scan) >= 6
    for fpath in files_to_scan:
        txt = fpath.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in txt, f"Hardcoded host path '{needle}' found in {fpath.name}"


def test_cad_v3_mass_conservation() -> None:
    res = _load_json(JSON_PATH)
    anc = res["cad_anchors"]
    assert abs(anc["mass_accounted_kg"] - anc["cad_total_mass_kg"]) < 0.05
    assert 950.0 < anc["cad_total_mass_kg"] < 1200.0
    assert anc["m_granite_kg"] > 200.0
    assert anc["m_dr_tower_kg"] > 150.0
    assert 1.0 <= anc["m_wafer_stage_kg"] <= 3.0
    assert anc["k_cold_finger_rigid_N_m"] > 8.0e6


def test_column_fem_mesh_convergence_and_modal_realism() -> None:
    res = _load_json(JSON_PATH)
    fem = res["column_fem"]
    assert fem["n_elem"] == 40
    assert 40.0 <= fem["f1_flanged_hz"] <= 350.0
    assert fem["f1_rigid_root_hz"] > fem["f1_flanged_hz"]
    assert fem["mesh_convergence"]["max_rel_diff"] < 0.005
    modes = res["configurations_vce"]["CFG4_V4_FULL_CTRL"]["passive_modal_freqs_hz"]
    assert len(modes) == 6
    assert all(m > 0.0 for m in modes)
    assert 1.0 <= modes[0] <= 2.5


def test_parseval_time_frequency_parity() -> None:
    res = _load_json(JSON_PATH)
    for cfg_name in ("CFG4_V4_FULL_CTRL", "CFG1_RIGID_OPEN"):
        pv = res["configurations_vce"][cfg_name]["parseval"]
        assert pv is not None
        assert pv["max_rel_err"] < 0.01, f"Parseval error too high on {cfg_name}: {pv}"


def test_control_stability_margins_cfg4() -> None:
    res = _load_json(JSON_PATH)
    cfg4 = res["configurations_vce"]["CFG4_V4_FULL_CTRL"]
    cm = cfg4["control_margins"]
    assert cm["is_stable"] is True
    assert cm["n_gain_crossings"] == 1
    assert cm["phase_margin_deg"] >= 45.0
    assert cm["gain_margin_db"] >= 6.0
    assert cm["sensitivity_peak_S_inf"] <= 2.0
    assert cfg4["piezo_force_peak_5sigma_N"] < 1.0


def test_rigid_pt420_fails_and_decoupled_open_insufficient() -> None:
    res = _load_json(JSON_PATH)
    c1 = res["configurations_vce"]["CFG1_RIGID_OPEN"]
    c2 = res["configurations_vce"]["CFG2_DECOUPLED_OPEN"]
    c5 = res["configurations_vce"]["CFG5_RIGID_FULL_CTRL"]
    assert c1["sigma_stage_nm"] > 50.0
    assert c5["sigma_stage_nm"] > 2.0
    assert c1["sigma_stage_nm"] / c2["sigma_stage_nm"] > 100.0
    assert c2["sigma_stage_nm"] > 0.50


def test_v4_cfg4_meets_budget_and_vc_floor_sweep() -> None:
    res = _load_json(JSON_PATH)
    c4 = res["configurations_vce"]["CFG4_V4_FULL_CTRL"]
    assert c4["sigma_stage_nm"] <= 0.50
    assert c4["sigma_pointing_nm"] <= 0.50
    vc = res["vc_floor_sweep"]
    assert vc["VC-C"]["cfg4_passes_0p50_nm"] is False
    assert vc["VC-E"]["cfg4_passes_0p50_nm"] is True
    assert vc["VC-G"]["cfg4_passes_0p50_nm"] is True
    assert vc["VC-E"]["cfg4_pointing_nm"] / vc["VC-G"]["cfg4_pointing_nm"] >= 1.5


def test_2d_stiffness_envelope_and_ofhc_braid_trade() -> None:
    res = _load_json(JSON_PATH)
    sw = res["stiffness_sweep_2d"]
    lims = sw["exact_limits_vce"]
    assert lims["k_bellows_max_at_kbraid60"]["k_max_N_m"] > 2000.0
    assert lims["k_braid_max_at_kbel2000"]["k_max_N_m"] > 60.0
    assert lims["braid_over_bellows_stage_sensitivity_ratio"] > 10.0
    grid_max = sw["sigma_max_grid_nm"]
    assert len(grid_max) == 13 and len(grid_max[0]) == 13
    # Lower-left decoupled operating box (k_braid <= 1e3, k_bellows <= 2e3) passes <= 0.50 nm
    for r in range(0, 5):
        for c in range(0, 4):
            assert grid_max[r][c] <= 0.50, f"Unexpected failure in safe box at r={r}, c={c}: {grid_max[r][c]}"
    # High-stiffness braid region (k_braid >= 1e5) strictly exceeds 5.0 nm everywhere
    for r in range(8, 13):
        for c in range(13):
            assert grid_max[r][c] > 5.0, f"Expected failure at stiff k_braid r={r}, c={c}: {grid_max[r][c]}"
    br = res["ofhc_braid_physics"]
    assert br["k_braid_N_m"] <= 60.0
    assert br["G_braid_20mK_mW_K"] >= 1.0


def test_thermal_drift_and_exp124_budget_closure() -> None:
    res = _load_json(JSON_PATH)
    th = res["thermal_drift"]["material_comparison"]
    assert th["naive_ss316_uncompensated"]["dT_10mK"]["sigma_thermal_nm"] > 0.30
    assert th["v3_zerodur_invar_cryo"]["dT_10mK"]["sigma_thermal_nm"] <= 0.30
    cl = res["exp124_budget_closure"]["CFG4_V4_FULL_CTRL_VCE"]
    assert cl["ArchB_HiRes_Ti0p25_10ms"]["sigma_total_exp133_nm"] <= cl["ArchB_HiRes_Ti0p25_10ms"]["sigma_total_exp124_orig_nm"]
    assert cl["ArchB_HiRes_Ti0p5_15ms"]["sigma_total_exp133_nm"] <= cl["ArchB_HiRes_Ti0p5_15ms"]["sigma_total_exp124_orig_nm"]
    assert cl["ArchB_HiRes_Ti0p25_10ms"]["sigma_equip_exp133_nm"] <= 1.20


def test_obs148_live_dynamics133_solver_execution_and_json_parity() -> None:
    """OBS-148: Directly invoke live dynamics133.py solvers (FEM, 6-DOF closed-loop, thermal drift, closure)."""
    anc = d.load_cad_and_exp124_anchors()
    fem40 = d.solve_column_fem(anc, refine_factor=1, include_flange_compliance=True)
    snout = d.compute_lower_snout_and_chamber_compliance(anc)
    assert 115.0 < fem40["f1_hz"] < 122.0

    freqs = np.arange(8, 20001) * 0.025
    cfg4 = d.MachineConfig("CFG4_LIVE", "live", 2000.0, 60.0, True, True, True, 25.0, "VC-E")
    r_live = d.evaluate_configuration(cfg4, anc, fem40, snout, freqs)
    assert r_live["sigma_stage_nm"] <= 0.50
    assert r_live["sigma_pointing_nm"] <= 0.50
    assert r_live["control_margins"]["is_stable"] is True
    assert r_live["control_margins"]["phase_margin_deg"] >= 45.0

    th_live = d.evaluate_thermal_drift(anc, dT_room_amp_mK=10.0, T_hvac_s=900.0, t_fiducial_s=300.0)
    assert th_live["sigma_thermal_nm"] <= 0.30

    # Verify live solver matches persisted JSON
    res = _load_json(JSON_PATH)
    assert math.isclose(fem40["f1_hz"], res["column_fem"]["f1_flanged_hz"], rel_tol=1e-4)
    assert math.isclose(r_live["sigma_stage_nm"], res["configurations_vce"]["CFG4_V4_FULL_CTRL"]["sigma_stage_nm"], rel_tol=0.03)


def test_obs010_obs040_obs041_obs046_uhv_shields_nonlinear_20mk_and_frost_live() -> None:
    """Live solver tests for nested 50K+4K UHV shields, 4.2K magnet mounting, frost & nonlinear 20mK stack."""
    sh = d.evaluate_uhv_cryo_shielding_and_frost()
    leg = sh["legacy_unshielded_audit"]
    red = sh["redesigned_nested_50K_4K_uhv_shields"]

    # Legacy audit honestly reproduces >2 W 20mK leak, >20 W 4K magnet leak, >3 nm frost
    assert leg["q_20mk_total_W"] > 2.0
    assert leg["q_4k_magnet_total_low_W"] > 20.0
    assert leg["frost_8h_H2O_1e_9mbar"]["thickness_8h_nm"] > 3.0

    # Redesigned nested 50K+4K UHV shields + intercepts + 4K cryo-baffle close cleanly
    assert red["q_20mk_total_external_uW"] < 1.0
    assert red["passes_20mk_sub_1uW_budget"] is True
    assert red["q_4k_total_charging_W"] < 1.5
    assert red["passes_4p2K_sub_1p5W_budget"] is True
    assert red["frost_8h_H2O_redesigned"]["thickness_8h_nm"] < 0.05
    assert red["passes_negligible_frost_lt_0p05nm"] is True

    # OBS-041: Full nonlinear Wiedemann-Franz + Kapitza + welded >=80 mm^2 OFHC braid stack
    nl = d.evaluate_nonlinear_20mk_thermal_stack(
        T_mxc_K=0.020,
        q_chuck_uW=red["q_20mk_total_external_uW"],
        q_wafer_onchip_uW=0.020,
    )
    assert nl["legacy_bolted_4braid_20mm2_audit"]["at_7p036uW_RRR100"]["T_wafer_mK"] > 80.0
    r_nl = nl["redesigned_welded_96mm2_ofhc_stack"]
    assert r_nl["braid_cu_area_mm2"] >= 80.0
    assert r_nl["k_braid_lateral_N_m"] <= 60.0
    assert r_nl["nominal_shielded_operating_point"]["T_wafer_mK"] < 25.0
    assert r_nl["stress_7p036uW_on_chuck_20nW_wafer"]["T_wafer_mK"] < 25.0
    assert r_nl["passes_wafer_T_lt_25mK"] is True


def test_obs077_obs104_wpm6_canonical_mass_and_pilot1a_corrections_live() -> None:
    """Live solver test for WP-M6 2,996.8 kg mass, upper column tip loads, S4.1-03 >=1000 kg & Pilot 1A FEA."""
    anc = d.load_cad_and_exp124_anchors()
    snout = d.compute_lower_snout_and_chamber_compliance(anc)
    freqs = np.arange(8, 20001) * 0.025
    wp = d.evaluate_wpm6_and_pilot1a_audit(anc, snout, freqs)

    assert 2940.0 < wp["wpm6_canonical_total_mass_kg"] < 3010.0
    f1c = wp["column_f1_comparison_hz"]
    assert f1c["wpm6_bom_spec_tip_loads"] < f1c["wpm6_stl_tip_loads"] < f1c["cad_v3_legacy"]
    assert f1c["all_inside_40_to_350_hz_cy1_band"] is True
    assert wp["s4_base_mass_reconciliation"]["S4.1-03_redesigned_sand_ballasted_kg"] >= 1000.0
    assert wp["s4_base_mass_reconciliation"]["S4.1-03_meets_1000kg_spec"] is True
    assert wp["cfg4_wpm6_closed_loop_vce"]["passes_0p50_nm_budget"] is True
    # OBS-104 Pilot 1A FEA corrections recorded
    p1a = wp["pilot1a_fea_corrections_obs104"]
    assert math.isclose(p1a["S6.9-01_pt420_remote_valve_stand"]["corrected_multimaterial_steel_full_assembly_f1_hz"], 106.91, abs_tol=0.1)
    assert math.isclose(p1a["S4.5-01_metrology_bridge"]["corrected_full_12shell_invar36_legs_f1_hz"], 526.62, abs_tol=0.1)


def test_verdicts_success_rule() -> None:
    res = _load_json(JSON_PATH)
    assert res["success_rule_met"] is True
    assert res["all_eight_verdicts_pass"] is True
    assert all(res["verdicts"].values())


def test_figures_and_summary_gfm_valid() -> None:
    for fig in (FIG1_PATH, FIG2_PATH):
        assert fig.exists(), f"Missing figure: {fig}"
        assert fig.stat().st_size > 80_000, f"Figure unexpectedly small: {fig}"
        w, h = _png_size(fig)
        assert w >= 2000 and h >= 1100, f"Low-res figure {fig}: {w}x{h}"

    assert SUMMARY_PATH.exists(), f"Missing summary: {SUMMARY_PATH}"
    md = SUMMARY_PATH.read_text(encoding="utf-8")
    assert "no_lab_measurement" in md
    assert "CY1_modal_realism" in md and "CY8_exp124_total_closure" in md
    errs = _check_gfm_tables(md)
    assert errs == [], f"GFM table errors in summary_exp133.md: {errs}"
