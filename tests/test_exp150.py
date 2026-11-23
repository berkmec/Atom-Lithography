"""Unit & physics verification tests for Exp150 (H168): Industrial Safety, HAZOP & 25-Row FMEA."""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
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
