"""Automated verification suite for BOM_DETAILED.csv, Exp128 Monte Carlo & RFQ/Engineering docs."""
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


def test_canonical_bom_csv_untouched_sha256() -> None:
    actual = hashlib.sha256(BOM_CSV.read_bytes()).hexdigest()
    assert actual == EXPECTED_BOM_SHA256


def test_bom_detailed_schema_and_value_invariants() -> None:
    df = pd.read_csv(BOM_DETAILED)
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) >= 120
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


def test_canonical_40_rows_and_exp124_125_127_deltas_covered() -> None:
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
    assert bds["total_parts"] == len(df)
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

    # Zero-error delta bridge
    db = data["delta_bridge_exp122_to_detailed"]
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
    assert data["rfq_coverage"]["rfq6_variance_share_mc"] >= 0.85

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


def test_deliverable_docs_and_figures_exist_and_valid() -> None:
    for p in (BOM_DETAILED, BOM_ENG_MD, RFQ_MD, PRED128_JSON, EXP128_JSON, SUMMARY128_MD):
        assert p.exists() and p.stat().st_size > 1000, f"Missing or tiny file: {p}"

    for fig in (FIG_TORNADO, FIG_M1M3):
        assert fig.exists() and fig.stat().st_size > 50_000
        w, h = read_png_size(fig)
        assert w >= 1800 and h >= 1000

    # Verify RFQ_SPECIFICATIONS covers all 6 RFQ packages
    rfq_text = RFQ_MD.read_text(encoding="utf-8")
    for tag in ("RFQ-01", "RFQ-02", "RFQ-03", "RFQ-04", "RFQ-05", "RFQ-06"):
        assert tag in rfq_text
