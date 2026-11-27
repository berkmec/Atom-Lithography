"""Automated verification suite for BOM_DETAILED.csv (v7.0), Exp128 Monte Carlo & RFQ-01..10 docs.

100% portable: resolves repository root strictly via Path(__file__).resolve().parents[1].
"""
from __future__ import annotations

import csv
import hashlib
import json
import struct
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
BOM_CSV = ROOT / "research" / "atom_lithography_machine" / "BOM.csv"
BOM_DETAILED = ROOT / "research" / "atom_lithography_machine" / "BOM_DETAILED.csv"
BOM_ENG_MD = ROOT / "research" / "atom_lithography_machine" / "BOM_ENGINEERING.md"
RFQ_MD = ROOT / "research" / "atom_lithography_machine" / "RFQ_SPECIFICATIONS.md"
S56_SPEC_JSON = ROOT / "results" / "exp139_epi_cap_process_integration" / "s56_hardware_spec.json"
S65_SPEC_JSON = ROOT / "results" / "exp140_cryo_fpga_boed_mux_readout" / "s65_hardware_spec.json"
S9Q_SPEC_JSON = ROOT / "results" / "exp142_option_q_multispecies_qram" / "s9q_hardware_spec.json"
S9HPC_SPEC_JSON = ROOT / "results" / "exp143_d3_grape_m4_and_hpc_decoder" / "s9hpc_hardware_spec.json"
S_SAFETY_SPEC_JSON = ROOT / "results" / "exp150_industrial_safety_fmea_hazop" / "s_safety_spec.json"
EXP128_CODE_DIR = ROOT / "experiments" / "exp128_bom_sensitivity"
EXP128_DIR = ROOT / "results" / "exp128_bom_sensitivity"
EXP128_JSON = EXP128_DIR / "exp128.json"
PRED128_JSON = EXP128_DIR / "predictions_exp128.json"
SUMMARY128_MD = EXP128_DIR / "summary_exp128.md"
FIG_TORNADO = EXP128_DIR / "fig_exp128_tornado_cdf.png"
FIG_M1M3 = EXP128_DIR / "fig_exp128_m1_vs_m3_cost.png"

EXPECTED_BOM_SHA256 = "cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2"
EXPECTED_COLUMNS = [
    "part_id",
    "parent_bom_id",
    "subsystem",
    "part_name",
    "qty",
    "unit",
    "material",
    "key_spec",
    "tolerance",
    "temp_stage",
    "vacuum_grade",
    "procurement_class",
    "parent_cost_class",
    "usd_low",
    "usd_nom",
    "usd_high",
    "cad_module",
    "epistemic_tag",
    "notes",
]
VALID_PROCUREMENT = {"COTS", "CUS", "R&D", "COTS/CUS", "CUS/R&D", "IN-HOUSE"}
VALID_EPISTEMIC = {
    "{Model-Kalibrasyon-Exp114}",
    "{Liste-Çapası}",
    "{Varsayım}",
    "{Program-NRE-Kapsam}",
}
VALID_CAD_MODULES = {
    "s1_ion_source_column",
    "s2_mems_write_head",
    "s3_ibic_detector_assembly",
    "s4_piezo_stage_interferometry",
    "s5_uhv_chamber_loadlock",
    "s6_cryo_dr_magnet_readout",
    "s7_electronics_rack_interconnect",
    "software_control_stack",
    "consumables_calibration",
}


def read_png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"Not a valid PNG: {path}"
    w, h = struct.unpack(">II", header[16:24])
    return w, h


def _check_gfm_tables(md_path: Path) -> int:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    expected_cols = None
    mismatches = 0
    for ln in lines:
        s = ln.strip()
        if s.startswith("|") and s.endswith("|"):
            cols = s.count("|") - 1
            if expected_cols is None:
                expected_cols = cols
            elif cols != expected_cols:
                mismatches += 1
        else:
            expected_cols = None
    return mismatches


def test_canonical_bom_csv_untouched_sha256() -> None:
    actual = hashlib.sha256(BOM_CSV.read_bytes()).hexdigest()
    assert actual == EXPECTED_BOM_SHA256


def test_portability_no_hardcoded_user_paths() -> None:
    forbidden = ("/" + "home" + "/" + "berk", "/" + "run" + "/" + "media" + "/" + "berk")
    targets = [
        EXP128_CODE_DIR / "build_bom_detailed.py",
        EXP128_CODE_DIR / "run_exp128.py",
        EXP128_CODE_DIR / "plot_exp128.py",
        Path(__file__).resolve(),
    ]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for bad in forbidden:
            assert bad not in text, f"Hardcoded path '{bad}' found in {path.name}"


def test_bom_detailed_v7_schema_and_value_invariants() -> None:
    df = pd.read_csv(BOM_DETAILED)
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) == 180
    assert df["part_id"].is_unique
    for col in EXPECTED_COLUMNS:
        assert df[col].notna().all(), f"NaN detected in column {col}"
    assert (df["qty"] > 0).all()
    assert (df["usd_low"] >= 0).all()
    assert (df["usd_low"] <= df["usd_nom"]).all()
    assert (df["usd_nom"] <= df["usd_high"]).all()
    assert set(df["procurement_class"]).issubset(VALID_PROCUREMENT)
    assert set(df["epistemic_tag"]).issubset(VALID_EPISTEMIC)
    assert set(df["cad_module"]).issubset(VALID_CAD_MODULES)
    for _, r in df.iterrows():
        assert r["subsystem"] == r["parent_bom_id"].split(".")[0]


def test_canonical_40_rows_and_v3_v4_v5_v6_v7_modular_parity() -> None:
    canon_ids = set()
    with BOM_CSV.open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            rid = (row.get("id") or "").strip()
            if rid:
                canon_ids.add(rid)
    assert len(canon_ids) == 40

    df = pd.read_csv(BOM_DETAILED)
    parents = set(df["parent_bom_id"].unique())
    assert canon_ids.issubset(parents), f"Missing canonical IDs: {canon_ids - parents}"

    part_ids = set(df["part_id"].unique())
    # v3.0 / v4.0 / v5.0 / v6.0 / v7.0 key IDs (zero collision with canonical S1.6/S6.5/S9.1)
    for pid in (
        "S1.3-02", "S1.5-01", "S1.6-01", "S1.6-02", "S6.3-01", "S6.6-07", "S3.2-01",
        "S5.5-01", "S6.9-01", "S6.10-01", "S6.10-02", "S6.10-03", "S6.10-04", "S7.1-04", "S8.3-03",
        "S6.5-01", "S6.5-02", "S6.5-03", "S5.6-01", "S5.6-04", "S6.11-01", "S6.11-04",
        "S9.1-01", "S9.1-02", "S1.7-01", "S9.4-01", "S9.4-02", "S9.4-03", "S9.HPC-01", "S9.HPC-03",
        "S7.SAFETY-01", "S7.SAFETY-02", "S7.SAFETY-03", "S7.SAFETY-04", "S7.SAFETY-05", "S7.SAFETY-06",
    ):
        assert pid in part_ids

    # Anti-double-counting check: superseded v4.0 rows zeroed cleanly & S6.10-04 halved to $20k DC-only
    assert float(df.loc[df["part_id"] == "S6.10-02", "usd_nom"].iloc[0]) == 0.0
    assert float(df.loc[df["part_id"] == "S7.1-04", "usd_nom"].iloc[0]) == 0.0
    assert float(df.loc[df["part_id"] == "S6.10-04", "usd_nom"].iloc[0]) == 20_000.0

    # Exact parity against ALL 5 primary hardware spec JSONs (Exp139/140/142/143/150)
    s56_spec = json.loads(S56_SPEC_JSON.read_text(encoding="utf-8"))["s56_hardware_spec"]
    s65_spec = json.loads(S65_SPEC_JSON.read_text(encoding="utf-8"))
    s9q_spec = json.loads(S9Q_SPEC_JSON.read_text(encoding="utf-8"))
    s9hpc_spec = json.loads(S9HPC_SPEC_JSON.read_text(encoding="utf-8"))
    s_safety_spec = json.loads(S_SAFETY_SPEC_JSON.read_text(encoding="utf-8"))

    s56_df = df[df["parent_bom_id"] == "S5.6"]
    s611_df = df[df["parent_bom_id"] == "S6.11"]
    optq_df = df[df["notes"].astype(str).str.contains("DELTA-V6.0-OPTQ", na=False)]
    opthpc_df = df[df["notes"].astype(str).str.contains("DELTA-V6.0-OPTHPC", na=False)]
    saf_df = df[df["notes"].astype(str).str.contains("DELTA-V7.0-SAFETY", na=False)]
    base_v5_df = df[~df["notes"].astype(str).str.contains("DELTA-V6.0|DELTA-V7.0", na=False)]

    assert float(s56_df["usd_low"].sum()) == pytest.approx(s56_spec["bom_v5_cost_estimate_usd"]["total_p10_usd"], abs=1e-6)
    assert float(s56_df["usd_nom"].sum()) == pytest.approx(s56_spec["bom_v5_cost_estimate_usd"]["total_p50_usd"], abs=1e-6)
    assert float(s56_df["usd_high"].sum()) == pytest.approx(s56_spec["bom_v5_cost_estimate_usd"]["total_p90_usd"], abs=1e-6)

    assert float(s611_df["usd_low"].sum()) == pytest.approx(s65_spec["totals_1024_cell_module"]["cost_usd_low"], abs=1e-6)
    assert float(s611_df["usd_nom"].sum()) == pytest.approx(s65_spec["totals_1024_cell_module"]["cost_usd_nom"], abs=1e-6)
    assert float(s611_df["usd_high"].sum()) == pytest.approx(s65_spec["totals_1024_cell_module"]["cost_usd_high"], abs=1e-6)

    assert len(optq_df) == 4
    assert float(optq_df["usd_low"].sum()) == pytest.approx(s9q_spec["totals_option_q_plus_s1_multi"]["cost_usd_low"], abs=1e-6)
    assert float(optq_df["usd_nom"].sum()) == pytest.approx(s9q_spec["totals_option_q_plus_s1_multi"]["cost_usd_nom"], abs=1e-6)
    assert float(optq_df["usd_high"].sum()) == pytest.approx(s9q_spec["totals_option_q_plus_s1_multi"]["cost_usd_high"], abs=1e-6)

    assert len(opthpc_df) == 3
    assert float(opthpc_df["usd_low"].sum()) == pytest.approx(s9hpc_spec["totals_base_4u_option_hpc_module"]["cost_usd_low"], abs=1e-6)
    assert float(opthpc_df["usd_nom"].sum()) == pytest.approx(s9hpc_spec["totals_base_4u_option_hpc_module"]["cost_usd_nom"], abs=1e-6)
    assert float(opthpc_df["usd_high"].sum()) == pytest.approx(s9hpc_spec["totals_base_4u_option_hpc_module"]["cost_usd_high"], abs=1e-6)

    assert len(saf_df) == 6
    assert float(saf_df["usd_low"].sum()) == pytest.approx(s_safety_spec["totals"]["cost_usd_low"], abs=1e-6)
    assert float(saf_df["usd_nom"].sum()) == pytest.approx(s_safety_spec["totals"]["cost_usd_nom"], abs=1e-6)
    assert float(saf_df["usd_high"].sum()) == pytest.approx(s_safety_spec["totals"]["cost_usd_high"], abs=1e-6)

    # All modular configuration totals exact to $0.00!
    assert len(base_v5_df) == 167
    assert float(base_v5_df["usd_nom"].sum()) == pytest.approx(5_247_800.0, abs=1e-6)
    assert float(base_v5_df["usd_nom"].sum() + saf_df["usd_nom"].sum()) == pytest.approx(5_392_800.0, abs=1e-6)
    assert float(base_v5_df["usd_nom"].sum() + optq_df["usd_nom"].sum() + opthpc_df["usd_nom"].sum()) == pytest.approx(5_547_800.0, abs=1e-6)
    assert float(df["usd_nom"].sum()) == pytest.approx(5_692_800.0, abs=1e-6)


def test_rollup_reconciliation_mass_parity_and_exp114_122() -> None:
    df = pd.read_csv(BOM_DETAILED)
    data = json.loads(EXP128_JSON.read_text(encoding="utf-8"))

    # Exact Exp121/122 canonical gate
    gate = data["canonical_gate"]
    assert gate["sha256_matches_expected"] is True
    assert gate["gate_ok"] is True
    assert gate["nl55_b_frac"] == pytest.approx(0.5602950333504173, abs=1e-12)
    assert gate["nl55_b_abs"] == pytest.approx(2159.00039876329, abs=1e-9)
    assert gate["nl163_central_usd_u720"] == pytest.approx(2531244.3664524374, abs=1e-4)

    # Exact bottom-up pandas roll-up vs exp128.json (v7.0 modular bridge)
    bds = data["bom_detailed_summary"]
    assert bds["bom_version"] == "v7.0"
    assert bds["total_parts"] == len(df) == 180
    assert bds["v5_base_parts"] == 167
    assert bds["v6_option_parts"] == 7
    assert bds["v7_safety_parts"] == 6
    assert bds["m3_v3_base_nom_usd"] == pytest.approx(4_189_600.0, abs=1e-6)
    assert bds["m3_v4_base_nom_usd"] == pytest.approx(4_609_600.0, abs=1e-6)
    assert bds["m3_v5_base_nom_usd"] == pytest.approx(5_247_800.0, abs=1e-6)
    assert bds["m3_base_plus_safety_nom_usd"] == pytest.approx(5_392_800.0, abs=1e-6)
    assert bds["m3_v6_full_nom_usd"] == pytest.approx(5_547_800.0, abs=1e-6)
    assert bds["v7_safety_nom_usd"] == pytest.approx(145_000.0, abs=1e-6)
    assert bds["m3_v7_safety_certified_full_nom_usd"] == pytest.approx(5_692_800.0, abs=1e-6)
    assert bds["m1_nom_usd"] == pytest.approx(2_466_120.0, abs=1e-6)
    assert bds["m1_plus_safety_nom_usd"] == pytest.approx(2_611_120.0, abs=1e-6)
    assert bds["m3_low_usd"] == pytest.approx(float(df["usd_low"].sum()), abs=1e-6)
    assert bds["m3_nom_usd"] == pytest.approx(float(df["usd_nom"].sum()), abs=1e-6)
    assert bds["m3_high_usd"] == pytest.approx(float(df["usd_high"].sum()), abs=1e-6)
    assert bds["reconciliation_error_usd"] < 1e-6

    # Exact mass parity: on-frame CAD v6 (1108.137 kg) + external facility safety (355.0 kg) = 1463.137 kg
    mr6 = data["v6_hardware_mass_reconciliation"]
    assert mr6["cad_v6_full_mass_kg"] == pytest.approx(1108.137, abs=1e-9)
    assert mr6["mass_reconciliation_error_kg"] < 1e-9

    mr7 = data["v7_hardware_mass_reconciliation"]
    assert mr7["on_frame_cad_v6_mass_kg"] == pytest.approx(1108.137, abs=1e-9)
    assert mr7["facility_safety_bom_total_mass_kg"] == pytest.approx(355.0, abs=1e-9)
    assert mr7["total_facility_load_mass_kg"] == pytest.approx(1463.137, abs=1e-9)
    assert mr7["facility_safety_cryo_load_W"] == pytest.approx(0.0, abs=1e-9)
    assert mr7["mass_reconciliation_error_kg"] < 1e-9

    # Exact Exp114 56-chain bill ($680,400) & S6.8 DR ($720,000) parity
    s66_6 = float(df[df["part_id"].isin([f"S6.6-0{i}" for i in range(1, 7)])]["usd_nom"].sum())
    s68 = float(df[df["parent_bom_id"] == "S6.8"]["usd_nom"].sum())
    assert s66_6 == pytest.approx(56 * 12150.0, abs=1e-6)
    assert s68 == pytest.approx(720000.0, abs=1e-6)

    # Subsystem-by-subsystem reconciliation & zero-error delta bridge
    sr = data["subsystem_reconciliation"]
    for sub, g in df.groupby("subsystem"):
        assert sr[sub]["detailed_m3_nom_usd"] == pytest.approx(float(g["usd_nom"].sum()), abs=1e-6)
        assert sr[sub]["delta_vs_exp122_usd"] == pytest.approx(
            sr[sub]["detailed_m3_nom_usd"] - sr[sub]["exp122_central_usd"], abs=1e-6
        )
    db = data["delta_bridge_exp122_to_detailed"]
    assert db["bridge_arithmetic_error_usd"] < 1e-6


def test_exp128_v7_monte_carlo_10rfq_modular_and_evpi_invariants() -> None:
    data = json.loads(EXP128_JSON.read_text(encoding="utf-8"))
    assert data["no_lab_measurement"] is True
    assert data["no_supplier_quotes"] is True

    mc = data["monte_carlo_model_a_detailed"]
    assert mc["n_samples"] == 100_000
    for key in (
        "bom_pure_no_bc_shock_usd",
        "bom_with_bc_and_nl_usd",
        "program_x3_usd",
        "program_stochastic_3_to_10_usd",
        "program_x10_usd",
    ):
        d = mc[key]
        seq = [d["p05"], d["p10"], d["p25"], d["p50"], d["p75"], d["p90"], d["p95"], d["p99"]]
        assert seq == sorted(seq), f"Non-monotonic percentiles in {key}"

    # Verify strict ordering across all 6 modular MC configurations & Phase-1 Base+Safety <5% safety
    mod = data["v7_modular_mc_comparison"]
    assert (
        mod["M3_v5_0_Base"]["bom_mc_usd"]["p50"]
        < mod["M3_v5_0_Base_Plus_Safety"]["bom_mc_usd"]["p50"]
        < mod["M3_v6_0_Full_Option_Q_and_HPC"]["bom_mc_usd"]["p50"]
        < mod["M3_v7_0_Safety_Certified_Full"]["bom_mc_usd"]["p50"]
    )
    assert mod["M3_v5_0_Base"]["P_Program_stoch_gt_100M"] < 0.05
    assert mod["M3_v5_0_Base_Plus_Safety"]["P_Program_stoch_gt_100M"] < 0.05
    assert mod["M3_v6_0_Full_Option_Q_and_HPC"]["P_Program_stoch_gt_100M"] < 0.05

    ep = mc["exceedance_probabilities"]
    for pval in ep.values():
        assert 0.0 <= pval <= 1.0
    assert ep["P_BOM_gt_50M"] < 0.001
    assert ep["P_Program_x3_gt_50M"] <= ep["P_Program_stoch_gt_50M"] <= ep["P_Program_x10_gt_50M"]

    # Tornado covariance variance shares must sum to 1.0 & 10-RFQ must exceed 75% nom and 90% MC variance
    var_sum = sum(t["variance_contrib_share"] for t in data["tornado_bom_scope"])
    assert var_sum == pytest.approx(1.0, abs=1e-6)
    assert data["tornado_bom_scope"][0]["driver"].startswith("S6.6")
    rc = data["rfq_coverage"]
    assert rc["rfq10_nom_share"] >= 0.75
    assert rc["rfq10_variance_share_mc"] >= 0.90
    assert (
        rc["rfq10_total_nom_usd"]
        > rc["rfq9_total_nom_usd"]
        > rc["rfq8_total_nom_usd"]
        > rc["rfq7_total_nom_usd"]
        > rc["rfq6_total_nom_usd"]
    )

    # EVPI 20 mK baseline vindication
    ev = data["evpi_20mk_vs_1k"]
    assert ev["expected_hw_saving_per_machine_usd"] > 500_000
    assert ev["cu5_ref_1mach_2M_p50_env_usd"] < 0.0
    assert ev["cu5_ref_breakeven_machines_hw"] >= 4.0

    # Core pre-registered verdicts + Phase-1 Base+Safety CU3 PASS; honest CU3_v7_full recorded accurately
    v = data["verdicts"]
    for key in (
        "CU1_bom_integrity",
        "CU2_bom_cap_safety",
        "CU3_base_v5_program_soft_hard_cap",
        "CU3_base_plus_safety_program_soft_hard_cap",
        "CU3_v6_full_program_soft_hard_cap",
        "CU4_bc_wall_dominance",
        "CU5_evpi_20mk_vindication",
        "CU6_mc_convergence",
        "success",
    ):
        assert v[key] is True, f"Verdict {key} failed"


def test_deliverable_docs_figures_and_gfm_integrity() -> None:
    for p in (BOM_DETAILED, BOM_ENG_MD, RFQ_MD, PRED128_JSON, EXP128_JSON, SUMMARY128_MD):
        assert p.exists() and p.stat().st_size > 1000, f"Missing or tiny file: {p}"

    for fig in (FIG_TORNADO, FIG_M1M3):
        assert fig.exists() and fig.stat().st_size > 50_000
        w, h = read_png_size(fig)
        assert (w, h) == (2200, 1260)

    # Verify RFQ_SPECIFICATIONS covers all 10 RFQ packages (RFQ-01..RFQ-10)
    rfq_text = RFQ_MD.read_text(encoding="utf-8")
    for tag in ("RFQ-01", "RFQ-02", "RFQ-03", "RFQ-04", "RFQ-05", "RFQ-06", "RFQ-07", "RFQ-08", "RFQ-09", "RFQ-10"):
        assert tag in rfq_text

    # Strict zero-mismatch GFM table verification across all 3 markdown deliverables
    for md in (BOM_ENG_MD, RFQ_MD, SUMMARY128_MD):
        assert _check_gfm_tables(md) == 0, f"GFM table mismatch in {md.name}"

    # OBS-061: Zero shuttered Efabless active dependency; UNQUOTED_ROM_ESTIMATE & lead-time registry present
    assert "UNQUOTED_ROM_ESTIMATE" in rfq_text
    assert "ChipFoundry" in rfq_text and "SkyWater" in rfq_text


def test_obstacle_closures_bom_ups_icds_and_180_verification_tests() -> None:
    """Verify OBS-060, 061, 068, 079, 120, 126, 134, 139 across BOM_DETAILED, CAD params, and hardware/icd."""
    df = pd.read_csv(BOM_DETAILED)
    by_id = df.set_index("part_id")

    # OBS-060: 50 mm FOAK wafer alignment in BOM S5.4-01 & cad/params.py
    assert "50 mm" in str(by_id.loc["S5.4-01", "key_spec"])
    params_txt = (ROOT / "research" / "atom_lithography_machine" / "cad" / "params.py").read_text(encoding="utf-8")
    assert '"wafer_diameter_mm": 50.0' in params_txt
    assert '"wafer_tier_canonical": "FOAK_50mm"' in params_txt

    # OBS-061: Efabless replaced by active SkyWater/ChipFoundry/MOSIS MPW brokers
    assert "ChipFoundry" in str(by_id.loc["S7.3-01", "notes"])
    assert "ChipFoundry" in str(by_id.loc["S2.4-01", "notes"])
    exp128 = json.loads(EXP128_JSON.read_text(encoding="utf-8"))
    assert exp128["procurement_status"] == "UNQUOTED_ROM_ESTIMATE"
    assert len(exp128["supply_chain_lead_time_registry_obs061"]["critical_path_chokepoints"]) >= 7

    # OBS-134 & OBS-139: 5% MBE capture in S5.6-02 & iradina sputtering yield in S9.3-01
    assert "427" in str(by_id.loc["S5.6-02", "key_spec"]) and "190" in str(by_id.loc["S5.6-02", "key_spec"])
    assert "0.913" in str(by_id.loc["S9.3-01", "key_spec"]) and "1.711" in str(by_id.loc["S9.3-01", "key_spec"])

    # OBS-068, 079, 126: Master UPS budget, S2.4-01 (300 K), S6.3-05 (>=300 A HTS + 650 W ramp-down), PT420 12.5 kW
    ups_master = json.loads((ROOT / "hardware" / "icd" / "electrical" / "master_electrical_power_ups_budget.json").read_text(encoding="utf-8"))
    ups = ups_master["ups_s7_safety_04"]
    assert ups["battery_energy_kWh"] == 12.0
    assert ups["usable_battery_energy_90pct_dod_kWh"] == 10.8
    assert ups["pt420_wall_power_utility_side_kW"] == 12.5
    assert ups["utility_side_tier2_contactor_ahead_of_ups"] is True
    assert ups["tier1_plus_tier1b_peak_ups_load_kW"] <= 13.5
    assert ups["dedicated_magnet_rampdown_ups_branch_W"] == 650.0
    assert ups["tier1_critical"]["runtime_tier1_min_conservative_90pct_dod_incl_350w_loss"] >= 180.0
    assert ups["tier1_critical"]["tier1_conservative_90pct_dod_meets_180min"] is True
    assert ups["tier2_sheddable"]["tier2_shed_28part_reconciliation"]["reconciliation_discrepancy_W"] == 0.0

    s24 = json.loads((ROOT / "hardware" / "icd" / "parts" / "S2.4-01.json").read_text(encoding="utf-8"))
    assert s24["artifact_links"]["cad"]["temp_k"] == 300.0
    assert s24["thermal_boundary_spec"]["cryo_4k_heat_load_W"] == 0.0

    s63 = json.loads((ROOT / "hardware" / "icd" / "parts" / "S6.3-05.json").read_text(encoding="utf-8"))
    assert s63["magnet_power_and_hts_spec"]["psu_current_rating_A"] >= 300.0
    assert s63["magnet_power_and_hts_spec"]["dedicated_ups_tier1b_rampdown_W"] == 650.0

    # OBS-120: ALL 180/180 hardware/icd/parts/*.json have non-empty, real existing verification_tests
    part_files = sorted((ROOT / "hardware" / "icd" / "parts").glob("*.json"))
    assert len(part_files) == 180
    for pf in part_files:
        pd_json = json.loads(pf.read_text(encoding="utf-8"))
        vts = pd_json["artifact_links"]["verification_tests"]
        assert isinstance(vts, list) and len(vts) >= 2, f"Empty verification_tests in {pf.name}"
        for rel in vts:
            assert (ROOT / rel).is_file(), f"Broken verification_test path {rel} in {pf.name}"
