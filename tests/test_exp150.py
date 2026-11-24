"""Unit & physics verification tests for Exp150 (H168): Industrial Safety, HAZOP & 25-Row FMEA."""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXP_DIR = ROOT / "experiments/exp150_industrial_safety_fmea_hazop"
RES_DIR = ROOT / "results/exp150_industrial_safety_fmea_hazop"


@pytest.fixture(scope="module")
def exp150_data() -> dict:
    return json.loads((RES_DIR / "exp150.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def safety_spec() -> dict:
    return json.loads((RES_DIR / "s_safety_spec.json").read_text(encoding="utf-8"))


def test_preregistered_verdicts_7_of_7_pass(exp150_data: dict) -> None:
    prereg = json.loads((RES_DIR / "predictions_exp150.json").read_text(encoding="utf-8"))
    assert prereg["hypothesis_id"] == "H168"
    assert prereg["no_lab_measurement"] is True
    assert prereg["no_supplier_quotes"] is True

    assert exp150_data["overall_verdict"] == "PASS"
    assert exp150_data["criteria_passed"] == "7/7"
    assert exp150_data["no_lab_measurement"] is True
    assert exp150_data["no_supplier_quotes"] is True
    for k, v in exp150_data["preregistered_verdicts"].items():
        assert v["pass"] is True, f"Pre-registered criterion failed: {k}"


def test_sf1_ansi_laser_physics_and_sil3(exp150_data: dict) -> None:
    las = exp150_data["hazard_1_laser_s55"]
    # Independent ANSI Z136.1 recomputation for 808 nm, 1.0 ms
    c_a = 10.0 ** (0.002 * (808.0 - 700.0))
    mpe1 = 1.8e-3 * c_a * (1e-3 ** 0.75)
    mpe4 = mpe1 * (4.0 ** -0.25)
    assert math.isclose(las["ansi_C_A_808nm"], c_a, rel_tol=1e-4)
    assert math.isclose(las["mpe_eye_1pulse_J_cm2"], mpe1, rel_tol=1e-4)
    assert math.isclose(las["mpe_eye_4pulse_uJ_cm2"], mpe4 * 1e6, rel_tol=1e-3)

    assert las["nohd_collimated_20mrad_m"] > 1000.0
    assert las["nhz_diffuse_m"] > 10.0
    assert 6.3 <= las["od_required_4pulse_wafer"] <= 6.8
    assert las["od_sweep"]["OD6"]["pass_class1_embedded"] is False
    assert las["od_sweep"]["OD7"]["pass_class1_embedded"] is True
    assert las["od_sweep"]["OD8"]["pass_class1_embedded"] is True
    assert las["od_sweep"]["OD8"]["ratio_to_4pulse_MPE_at_wafer"] < 0.05
    assert las["interlock_sil3"]["shutter_close_ms"] <= 5.0
    assert las["interlock_sil3"]["pfd_avg_1oo2d"] < 1e-3
    assert las["interlock_sil3"]["pfd_avg_1oo2d"] < las["interlock_sil3"]["pfd_single_channel"]


def test_epistemic_certification_boundaries_and_no_false_sil3_claim(
    exp150_data: dict, safety_spec: dict
) -> None:
    raw_exp150 = (RES_DIR / "exp150.json").read_text(encoding="utf-8")
    raw_spec = (RES_DIR / "s_safety_spec.json").read_text(encoding="utf-8")
    assert "sil3_achieved" not in raw_exp150
    assert "sil3_achieved" not in raw_spec

    il = exp150_data["hazard_1_laser_s55"]["interlock_sil3"]
    assert "sil3_achieved" not in il

    for container in (exp150_data, il):
        assert container["iec61508_certified"] is False
        assert container["semi_s2_certified"] is False
        assert container["certification_status"] == "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED"
        assert container["sil3_pfd_band_met_at_nominal_assumed_lambda_du"] is True
        assert container["requires_third_party_assessment"] is True

    assert safety_spec["iec61508_certified"] is False
    assert safety_spec["semi_s2_certified"] is False
    assert safety_spec["certification_status"] == "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED"
    assert safety_spec["requires_third_party_assessment"] is True
    assert "Lab-Ready" not in safety_spec["title"]
    assert exp150_data["hazard_3_hv_and_xray"]["hv_crowbar"]["iec61010_certified"] is False

    for row in exp150_data["fmea_25_rows"]:
        assert row["sil_certification_status"] == "DESIGN_TARGET_ONLY_NOT_CERTIFIED"
    for node in exp150_data["hazop_10_nodes"]:
        assert node["sil_certification_status"] == "DESIGN_TARGET_ONLY_NOT_CERTIFIED"
    for item in safety_spec["items"]:
        assert item["sil_certification_status"] == "DESIGN_TARGET_ONLY_NOT_CERTIFIED"


def test_1oo2d_pfd_lambda_du_and_beta_sensitivity_sweep(exp150_data: dict) -> None:
    from experiments.exp150_industrial_safety_fmea_hazop.safety_physics150 import (
        classify_parametric_pfd_band,
        compute_1oo2d_pfd_avg,
        max_lambda_du_for_sil3_band,
    )

    il = exp150_data["hazard_1_laser_s55"]["interlock_sil3"]
    sw = il["pfd_sensitivity_sweep"]
    lam_nom = sw["lambda_du_nominal_per_h"]
    t_i = sw["proof_test_interval_h"]

    assert set((0.5, 1.0, 3.0, 10.0)).issubset(set(sw["lambda_du_multipliers"]))
    assert sw["beta_ccf_values"] == [0.02, 0.05, 0.10]
    assert len(sw["cases"]) == len(sw["lambda_du_multipliers"]) * len(sw["beta_ccf_values"])

    # Independently recompute every single grid cell from IEC 61508-6 1oo2 formula
    for c in sw["cases"]:
        lam = lam_nom * c["lambda_du_multiplier"]
        beta = c["beta_ccf"]
        expected_pfd = ((1.0 - beta) ** 2) * ((lam * t_i) ** 2) / 3.0 + 0.5 * beta * lam * t_i
        assert math.isclose(c["pfd_avg_1oo2d"], expected_pfd, rel_tol=1e-3)
        assert c["sil3_pfd_band_met"] is (expected_pfd < 1.0e-3)
        assert c["parametric_pfd_band"] == classify_parametric_pfd_band(expected_pfd)

    # Monotonicity in lambda_DU multiplier for each beta, and in beta for each multiplier
    for b_key in ("beta_2pct", "beta_5pct", "beta_10pct"):
        pfds = [r["pfd_avg_1oo2d"] for r in sw["by_beta"][b_key]]
        assert pfds == sorted(pfds) and len(set(pfds)) == len(pfds)
    for i in range(len(sw["lambda_du_multipliers"])):
        p2 = sw["by_beta"]["beta_2pct"][i]["pfd_avg_1oo2d"]
        p5 = sw["by_beta"]["beta_5pct"][i]["pfd_avg_1oo2d"]
        p10 = sw["by_beta"]["beta_10pct"][i]["pfd_avg_1oo2d"]
        assert p2 < p5 < p10

    # Must clearly show BOTH SIL-3 retention (nominal) and SIL-2 degradation (10x @ beta=10%)
    b10_10x = next(r for r in sw["by_beta"]["beta_10pct"] if r["lambda_du_multiplier"] == 10.0)
    assert b10_10x["pfd_avg_1oo2d"] >= 1.0e-3
    assert b10_10x["sil3_pfd_band_met"] is False
    assert b10_10x["parametric_pfd_band"] == "SIL-2_BAND"
    assert sw["summary"]["n_cases_in_sil3_pfd_band"] > 0
    assert sw["summary"]["n_cases_degraded_to_sil2"] >= 4

    # Analytical SIL-3 band boundaries invert the 1oo2D quadratic exactly
    for b_info in sw["sil3_band_boundaries_by_beta"].values():
        beta = b_info["beta_ccf"]
        lam_lim = max_lambda_du_for_sil3_band(t_i, beta, 1.0e-3)
        assert math.isclose(compute_1oo2d_pfd_avg(lam_lim, t_i, beta), 1.0e-3, rel_tol=1e-9)
        assert math.isclose(b_info["max_lambda_du_for_sil3_band_per_h"], lam_lim, rel_tol=1e-3)


def test_cryo_odh_room_box_ode_transient(exp150_data: dict) -> None:
    odh = exp150_data["hazard_4_cryo_odh_and_quench"]["helium_odh"]
    tr = odh["box_ode_transient"]
    v_he = odh["total_with_20pct_margin_stp_m3"]

    # Zero-ventilation RK4 ODE must match analytical exponential displacement O2_amb * exp(-V_He / V_room)
    for key, v_room in (("dry_60m3_0ACH_hvac_loss", 60.0), ("dry_15m3_0ACH_hvac_loss", 15.0)):
        exact = 20.95 * math.exp(-v_he / v_room)
        assert math.isclose(tr[key]["o2_min_pct"], exact, abs_tol=1e-3)
        assert math.isclose(tr[key]["o2_final_600s_pct"], exact, abs_tol=1e-3)

    # Active ventilation improves minimum O2 and restores O2 by 600 s
    assert tr["dry_60m3_20ACH"]["o2_min_pct"] > tr["dry_60m3_0ACH_hvac_loss"]["o2_min_pct"]
    assert tr["dry_60m3_20ACH"]["o2_final_600s_pct"] > 20.9
    assert tr["dry_60m3_20ACH"]["time_below_osha_19p5pct_s"] == 0.0
    assert tr["dry_60m3_0ACH_hvac_loss"]["time_below_osha_19p5pct_s"] == 0.0

    # Small 15 m^3 closet dips below 19.5% OSHA (justifying mandatory wall O2 monitor)
    assert tr["dry_15m3_0ACH_hvac_loss"]["passes_osha_19p5pct"] is False
    assert tr["dry_15m3_0ACH_hvac_loss"]["time_below_osha_19p5pct_s"] > 500.0
    assert tr["dry_15m3_6ACH"]["o2_final_600s_pct"] > tr["dry_15m3_0ACH_hvac_loss"]["o2_final_600s_pct"]

    # Wet 100 L LHe contrast drops catastrophically below 10% O2 even at 20 ACH
    assert tr["wet_100L_60m3_20ACH"]["o2_min_pct"] < 10.0
    assert tr["wet_100L_60m3_20ACH"]["passes_osha_19p5pct"] is False


def test_sf2_ph3_dispersion_and_forming_gas(exp150_data: dict) -> None:
    gas = exp150_data["hazard_2_ph3_and_forming_gas"]
    hp = gas["unmitigated_hp_cylinder"]
    sds = gas["mitigated_sds_system"]
    fg = gas["forming_gas_s56"]

    assert hp["room_60m3_peak_ppm"] > 50.0  # exceeds NIOSH IDLH
    assert sds["pressure_torr"] < 760.0     # strictly sub-atmospheric
    assert sds["operator_conservative_ppm"] < 0.01
    assert sds["margin_below_tlv_twa"] >= 5.0
    assert sds["margin_below_idlh"] >= 5000.0
    assert fg["h2_vol_pct"] < fg["iso10156_nonflammable_limit_pct"]
    assert fg["intrinsically_nonflammable_in_air"] is True
    assert all(c >= 0.0 for c in gas["time_series"]["hp_unmitigated_ppm"])
    assert all(c >= 0.0 for c in gas["time_series"]["sds_mitigated_room_ppm"])


def test_sf3_xray_attenuation_monotonicity_and_crowbar(exp150_data: dict) -> None:
    hvx = exp150_data["hazard_3_hv_and_xray"]
    e22 = hvx["energy_sweep"]["22keV"]
    # Strict physical monotonicity across barriers
    assert e22["unshielded_30cm_uSv_h"] > e22["s55_bare_sapphire_8mm_uSv_h"]
    assert e22["s55_bare_sapphire_8mm_uSv_h"] > 1.0  # critical finding: bare sapphire leaks >1 uSv/h!
    assert e22["s55_sapphire_plus_3mm_steel_shroud_uSv_h"] < 0.01
    assert e22["wall_6mm_316L_uSv_h"] < 1e-6
    assert e22["wall_10mm_cad_316L_uSv_h"] < e22["wall_6mm_316L_uSv_h"]
    # Energy monotonicity: 22 keV > 14 keV > 10 keV
    assert e22["unshielded_30cm_uSv_h"] > hvx["energy_sweep"]["14keV"]["unshielded_30cm_uSv_h"] > hvx["energy_sweep"]["10keV"]["unshielded_30cm_uSv_h"]

    crow = hvx["hv_crowbar"]
    assert 0.0 < crow["stored_energy_10kV_J"] < crow["stored_energy_22kV_J"] < 0.50
    assert crow["discharge_to_50V_10kV_ms"] < crow["discharge_to_50V_22kV_ms"] < 50.0
    assert crow["iec61010_pass"] is True


def test_sf4_cryo_odh_asme_dn50_and_quench(exp150_data: dict) -> None:
    cryo = exp150_data["hazard_4_cryo_odh_and_quench"]
    sweep = cryo["helium_odh"]["room_sweep"]
    # O2 must monotonically increase with room volume, and dry must strictly beat wet 100L LHe
    o2_vals = [sweep[k]["dry_ld400_pt420_O2_pct"] for k in ("15m3", "30m3", "60m3", "120m3")]
    assert o2_vals == sorted(o2_vals)
    assert sweep["60m3"]["dry_ld400_pt420_O2_pct"] > 20.5
    for k in ("15m3", "30m3", "60m3", "120m3"):
        assert sweep[k]["dry_ld400_pt420_O2_pct"] > sweep[k]["wet_100L_LHe_comparison_O2_pct"]

    rel = cryo["asme_ovc_relief"]
    assert rel["set_pressure_barg"] == 0.5
    assert rel["relief_safety_margin"] >= 10.0
    assert rel["relief_safety_margin_he"] >= 10.0
    assert rel["relief_safety_margin_n2"] >= 10.0

    qch = cryo["magnet_quench_exp125"]
    assert qch["dump_resistor_peak_1p5T_C"] < 55.0
    assert qch["T_hotspot_K"] < 150.0
    assert qch["E_mag_M4_0p1785T_kJ"] < qch["E_mag_1p5T_kJ"]


def test_sf5_epo_ups_shutdown_and_oxidation(exp150_data: dict) -> None:
    epo = exp150_data["hazard_5_epo_ups_shutdown"]
    ups = epo["ups_spec"]
    uhv = epo["uhv_isolation"]

    assert ups["rating_kVA"] == 15.0
    assert ups["transfer_time_ms"] == 0.0
    assert ups["runtime_at_rated_13p5kW_min"] >= 30.0
    assert ups["runtime_tier1_min"] >= 180.0
    assert uhv["gate_valve_close_ms"] <= 100.0
    assert 0.0 < uhv["wafer_oxidation_ML"] < 0.01

    times = [st["t_ms"] for st in epo["shutdown_sequence"]]
    assert times == sorted(times) and len(times) >= 6


def test_sf6_fmea_25_rows_and_hazop_10_nodes(exp150_data: dict) -> None:
    rows = exp150_data["fmea_25_rows"]
    fstat = exp150_data["fmea_summary"]
    hazop = exp150_data["hazop_10_nodes"]

    assert len(rows) == 25
    assert len(hazop) == 10
    assert [r["id"] for r in rows] == [f"FM-{i:02d}" for i in range(1, 26)]
    assert [h["node"] for h in hazop] == [f"HZ-{i:02d}" for i in range(1, 11)]

    for r in rows:
        assert r["S_pre"] * r["O_pre"] * r["D_pre"] == r["RPN_pre"]
        assert r["S_post"] * r["O_post"] * r["D_post"] == r["RPN_post"]
        assert r["RPN_post"] < r["RPN_pre"]
        assert r["RPN_post"] <= 60

    assert fstat["max_rpn_pre"] >= 240
    assert fstat["max_rpn_post"] <= 60
    assert fstat["n_unacceptable_post_gt60"] == 0
    assert fstat["mean_rpn_reduction_pct"] >= 75.0


def test_sf7_safety_kit_spec_reconciliation(safety_spec: dict) -> None:
    items = safety_spec["items"]
    tot = safety_spec["totals"]
    assert safety_spec["subsystem_id"] == "S7.SAFETY"
    assert safety_spec["no_lab_measurement"] is True
    assert safety_spec["no_supplier_quotes"] is True
    assert len(items) == 6
    assert [x["part_id"] for x in items] == [f"S7.SAFETY-0{i}" for i in range(1, 7)]

    assert math.isclose(sum(x["mass_kg_total"] for x in items), tot["total_mass_kg"], rel_tol=1e-6)
    assert math.isclose(sum(x["power_W_total"] for x in items), tot["steady_electrical_power_W"], rel_tol=1e-6)
    assert all(x["cryo_load_W"] == 0.0 for x in items) and tot["cryo_load_W"] == 0.0
    assert sum(x["cost_usd_low"] for x in items) == tot["cost_usd_low"]
    assert sum(x["cost_usd_nom"] for x in items) == tot["cost_usd_nom"]
    assert sum(x["cost_usd_high"] for x in items) == tot["cost_usd_high"]
    assert tot["cost_usd_low"] < tot["cost_usd_nom"] < tot["cost_usd_high"]
    assert 0.0 < tot["pct_of_m3_v6_full_bom"] <= 5.0


def test_upstream_anchor_consistency(exp150_data: dict) -> None:
    cad = json.loads((ROOT / "research/atom_lithography_machine/cad/cad_verification.json").read_text(encoding="utf-8"))
    e128 = json.loads((ROOT / "results/exp128_bom_sensitivity/exp128.json").read_text(encoding="utf-8"))
    anc = exp150_data["upstream_anchors"]
    assert anc["flash_fluence_v5_J_cm2"] == cad["design_specs"]["s55_v5_flash_fluence_J_cm2"]
    assert anc["chamber_wall_cad_mm"] == cad["design_specs"]["chamber_r_out_mm"] - cad["design_specs"]["chamber_r_in_mm"]
    m3_v6_ref = e128["bom_detailed_summary"].get("m3_v6_full_nom_usd", e128["bom_detailed_summary"]["m3_nom_usd"])
    assert anc["m3_v6_full_bom_usd"] == m3_v6_ref


def test_figure_png_exists_and_2400x1400() -> None:
    png = RES_DIR / "fig_exp150_safety_fmea_hazop.png"
    assert png.exists()
    raw = png.read_bytes()
    assert len(raw) > 100_000
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", raw[16:24])
    assert (w, h) == (2400, 1400)


def test_summary_markdown_gfm_tables_valid() -> None:
    md_lines = (RES_DIR / "summary_exp150.md").read_text(encoding="utf-8").splitlines()
    table_blocks = 0
    cur_cols: int | None = None
    for idx, line in enumerate(md_lines, 1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            ncols = s.count("|") - 1
            if cur_cols is None:
                cur_cols = ncols
                table_blocks += 1
            else:
                assert ncols == cur_cols, f"GFM table column mismatch at line {idx}: got {ncols}, expected {cur_cols}"
        else:
            cur_cols = None
    assert table_blocks >= 7


def test_zero_hardcoded_user_paths() -> None:
    forbidden = ("/home/" + "berk", "/run/media/" + "berk")
    files = list(EXP_DIR.glob("*.py")) + list(RES_DIR.glob("*.json")) + list(RES_DIR.glob("*.md")) + [Path(__file__)]
    for f in files:
        txt = f.read_text(encoding="utf-8")
        for pat in forbidden:
            assert pat not in txt, f"Hardcoded user path found in {f.name}"
