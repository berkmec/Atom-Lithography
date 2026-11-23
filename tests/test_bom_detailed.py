"""Automated verification suite for BOM_DETAILED.csv (v4.0), Exp128 Monte Carlo & RFQ-01..07 docs.

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


def test_bom_detailed_v4_schema_and_value_invariants() -> None:
    df = pd.read_csv(BOM_DETAILED)
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) == 159
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


def test_canonical_40_rows_and_v3_plus_v4_deltas_covered() -> None:
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
    # Exp124 deceleration + energy filter + PH3 safety
    for pid in ("S1.3-02", "S1.5-01", "S1.5-02", "S1.5-03", "S1.6-01", "S1.6-02"):
        assert pid in part_ids
    # Exp125 1.5T/<=0.4T active bucking magnet + Nb shield + NbTiN resonators
    for pid in ("S6.3-01", "S6.3-02", "S6.3-03", "S6.6-07"):
        assert pid in part_ids
    # Exp127 in-vacuum 8-ch ultra-low-C IBIC frontend
    for pid in ("S3.2-01", "S3.2-02", "S3.2-03", "S3.2-04"):
        assert pid in part_ids
    # v4.0 upgrade packages: S5.5 (Exp130), S6.9 PT420 (Exp133), S6.10 M4 (Exp131), S7.1-04 & S8.3-03 BOED (Exp132/134)
    for pid in (
        "S5.5-01", "S5.5-02", "S5.5-03", "S5.5-04",
        "S6.9-01", "S6.9-02", "S6.9-03", "S6.9-04",
        "S6.10-01", "S6.10-02", "S6.10-03", "S6.10-04",
        "S7.1-04", "S8.3-03",
    ):
        assert pid in part_ids

    # Exact v3.0 ($4,189,600) + v4.0 (+$420,000) = M3 v4.0 ($4,609,600) reconciliation
    v4_mask = df["notes"].astype(str).str.contains("DELTA-V4.0", na=False)
    assert float(df[~v4_mask]["usd_nom"].sum()) == pytest.approx(4_189_600.0, abs=1e-6)
    assert float(df[v4_mask]["usd_low"].sum()) == pytest.approx(235_000.0, abs=1e-6)
    assert float(df[v4_mask]["usd_nom"].sum()) == pytest.approx(420_000.0, abs=1e-6)
    assert float(df[v4_mask]["usd_high"].sum()) == pytest.approx(782_000.0, abs=1e-6)
    assert float(df["usd_nom"].sum()) == pytest.approx(4_609_600.0, abs=1e-6)


def test_rollup_reconciliation_and_exp114_122_parity() -> None:
    df = pd.read_csv(BOM_DETAILED)
    data = json.loads(EXP128_JSON.read_text(encoding="utf-8"))

    # Exact Exp121/122 canonical gate
    gate = data["canonical_gate"]
    assert gate["sha256_matches_expected"] is True
    assert gate["gate_ok"] is True
    assert gate["nl55_b_frac"] == pytest.approx(0.5602950333504173, abs=1e-12)
    assert gate["nl55_b_abs"] == pytest.approx(2159.00039876329, abs=1e-9)
    assert gate["nl163_central_usd_u720"] == pytest.approx(2531244.3664524374, abs=1e-4)

    # Exact bottom-up pandas roll-up vs exp128.json
    bds = data["bom_detailed_summary"]
    assert bds["bom_version"] == "v4.0"
    assert bds["total_parts"] == len(df) == 159
    assert bds["m3_v3_base_nom_usd"] == pytest.approx(4_189_600.0, abs=1e-6)
    assert bds["v4_delta_nom_usd"] == pytest.approx(420_000.0, abs=1e-6)
    assert bds["m3_low_usd"] == pytest.approx(float(df["usd_low"].sum()), abs=1e-6)
    assert bds["m3_nom_usd"] == pytest.approx(float(df["usd_nom"].sum()), abs=1e-6)
    assert bds["m3_high_usd"] == pytest.approx(float(df["usd_high"].sum()), abs=1e-6)
    assert bds["reconciliation_error_usd"] < 1e-6
    assert bds["m1_nom_usd"] < bds["m3_nom_usd"]

    # Exact Exp114 56-chain bill ($680,400) & S6.8 DR ($720,000) parity
    s66_6 = float(df[df["part_id"].isin([f"S6.6-0{i}" for i in range(1, 7)])]["usd_nom"].sum())
    s68 = float(df[df["parent_bom_id"] == "S6.8"]["usd_nom"].sum())
    assert s66_6 == pytest.approx(56 * 12150.0, abs=1e-6)
    assert s68 == pytest.approx(720000.0, abs=1e-6)

    # Subsystem-by-subsystem reconciliation
    sr = data["subsystem_reconciliation"]
    for sub, g in df.groupby("subsystem"):
        assert sr[sub]["detailed_m3_nom_usd"] == pytest.approx(float(g["usd_nom"].sum()), abs=1e-6)
        assert sr[sub]["delta_vs_exp122_usd"] == pytest.approx(
            sr[sub]["detailed_m3_nom_usd"] - sr[sub]["exp122_central_usd"], abs=1e-6
        )

    # Zero-error delta bridge including v4.0 step
    db = data["delta_bridge_exp122_to_detailed"]
    assert db["delta_v4_0_upgrade_package_usd"] == pytest.approx(420_000.0, abs=1e-6)
    assert db["bridge_arithmetic_error_usd"] < 1e-6


def test_exp128_monte_carlo_and_evpi_invariants() -> None:
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

    ep = mc["exceedance_probabilities"]
    for pval in ep.values():
        assert 0.0 <= pval <= 1.0
    assert ep["P_BOM_gt_50M"] < 0.001
    assert ep["P_Program_stoch_gt_100M"] < 0.05
    assert ep["P_Program_x3_gt_50M"] <= ep["P_Program_stoch_gt_50M"] <= ep["P_Program_x10_gt_50M"]

    # Tornado covariance variance shares must sum to 1.0
    var_sum = sum(t["variance_contrib_share"] for t in data["tornado_bom_scope"])
    assert var_sum == pytest.approx(1.0, abs=1e-6)
    assert data["tornado_bom_scope"][0]["driver"].startswith("S6.6")
    assert data["rfq_coverage"]["rfq7_variance_share_mc"] >= 0.90
    assert data["rfq_coverage"]["rfq7_total_nom_usd"] > data["rfq_coverage"]["rfq6_total_nom_usd"]

    # EVPI 20 mK baseline vindication
    ev = data["evpi_20mk_vs_1k"]
    assert ev["expected_hw_saving_per_machine_usd"] > 500_000
    assert ev["cu5_ref_1mach_2M_p50_env_usd"] < 0.0
    assert ev["cu5_ref_breakeven_machines_hw"] >= 4.0

    # Verdicts match recorded honesty
    v = data["verdicts"]
    assert v["CU1_bom_integrity"] is True
    assert v["CU2_bom_cap_safety"] is True
    assert v["CU3_program_soft_hard_cap"] is True
    assert v["CU5_evpi_20mk_vindication"] is True
    assert v["CU6_mc_convergence"] is True
    assert v["success"] is True


def test_deliverable_docs_figures_and_gfm_integrity() -> None:
    for p in (BOM_DETAILED, BOM_ENG_MD, RFQ_MD, PRED128_JSON, EXP128_JSON, SUMMARY128_MD):
        assert p.exists() and p.stat().st_size > 1000, f"Missing or tiny file: {p}"

    for fig in (FIG_TORNADO, FIG_M1M3):
        assert fig.exists() and fig.stat().st_size > 50_000
        w, h = read_png_size(fig)
        assert (w, h) == (2200, 1260)

    # Verify RFQ_SPECIFICATIONS covers all 7 RFQ packages (RFQ-01..RFQ-07)
    rfq_text = RFQ_MD.read_text(encoding="utf-8")
    for tag in ("RFQ-01", "RFQ-02", "RFQ-03", "RFQ-04", "RFQ-05", "RFQ-06", "RFQ-07"):
        assert tag in rfq_text

    # Strict zero-mismatch GFM table verification across all 3 markdown deliverables
    for md in (BOM_ENG_MD, RFQ_MD, SUMMARY128_MD):
        assert _check_gfm_tables(md) == 0, f"GFM table mismatch in {md.name}"
