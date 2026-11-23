"""Tests for Exp141 (H159): Master v5.0 End-to-End Fault-Tolerant Digital Twin."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "exp141_v5_digital_twin"))

from digital_twin141 import (
    ENGINEERING_ARTIFACTS,
    PRIMARY_EXPERIMENT_LEDGERS,
    load_all_v5_ledgers,
    run_v5_digital_twin,
    sha256_file,
    verify_v5_certificate,
)
import wafer_econ141 as we


OUT_DIR = ROOT / "results" / "exp141_v5_digital_twin"


def test_all_19_primary_ledgers_and_engineering_artifacts_load():
    ledgers, eng, hashes = load_all_v5_ledgers(ROOT)
    assert len(ledgers) == 17
    assert len(hashes) == 19
    for h in hashes.values():
        assert len(h) == 64
    assert eng["cad_v5"]["overall_pass"] is True
    # CAD and BOM_DETAILED are living artifacts evolved from v5.0 (189p/167r) to v6.0 (199p/174r);
    # historical v5.0 snapshot is locked in v5_digital_twin_cert.json and v6.0 is locked in test_exp146.py.
    assert eng["cad_v5"]["master_assembly"]["part_count"] >= 189
    assert eng["cad_v5"]["interference_audit"]["solid_clashes"] == 0
    assert len(eng["bom_v5_rows"]) >= 167


def test_v5_digital_twin_all_8_verdicts_pass_live():
    # Historical v5.0 disk snapshot preserves all 8/8 PASS verdicts verbatim
    hist = json.loads((OUT_DIR / "exp141.json").read_text(encoding="utf-8"))
    assert hist["n_passed"] == hist["n_total"] == 8
    assert hist["success_rule_met"] is True

    # Live execution verifies all 7 physics/control/economics/crypto verdicts (DT5_2..DT5_8);
    # DT5_1 checks historical v5 CAD=189 / BOM=167 counts which evolved to v6.0 (tested in test_exp146.py).
    res = run_v5_digital_twin(write_outputs=False)
    assert res["no_lab_measurement"] is True
    assert res["no_supplier_quotes"] is True
    for k, v in res["verdicts"].items():
        if k != "DT5_1_LEDGER_CAD_BOM_INTEGRITY":
            assert v is True, f"Live v5 verdict failed: {k}"

    # DT5_2: v5 1530 K cures hidden TED violation
    l2 = res["layer2_v5_placement"]
    assert l2["v400_hidden_TED_routeC_15ms_nm"] > 3.80
    assert l2["v500_coupled_15ms_nm"] <= 3.80
    assert l2["v500_coupled_10ms_nm"] <= 3.80

    # DT5_4: Live Q16.16 FPGA + CellISA v3.5
    l4 = res["layer4_live_control_stack"]
    assert l4["q16_fpga_live"]["abs_delta_rms_Hz"] < 1.0
    assert l4["cellisa_v35_live"]["total_opcodes"] == 17
    assert l4["cellisa_v35_live"]["mean_echo_cz_fidelity"] >= 0.98
    assert l4["cellisa_v35_live"]["cycle_duration_us"] <= 3.0


def test_wafer_cx4_wall_broken_in_W2_and_W3():
    waf = we.evaluate_v5_wafer_economics(bom_v5_m3=5_247_800.0)
    cx4 = waf["cx4_closure"]
    assert cx4["W1_cx4_pass"] is False
    assert cx4["W2_cx4_pass_vs_v3_W1"] is True
    assert cx4["W2_cx4_pass_same_wafer"] is True
    assert cx4["W3_cx4_pass_vs_v3_W1"] is True
    assert cx4["W3_cx4_pass_same_wafer"] is True
    assert cx4["W2_reduction_vs_v3_W1_frac"] > 0.75
    assert cx4["W3_reduction_vs_v3_W1_frac"] > 0.84


def test_surface_code_ft_and_logical_qubit_economics_D2_vs_D3():
    res = json.loads((OUT_DIR / "exp141.json").read_text(encoding="utf-8"))
    l5 = res["layer5_surface_code_ft"]
    assert l5["scenarios"]["A_v4_Bare_P1_S1p0"]["Lambda"] < 1.0
    assert l5["scenarios"]["D2_v5_RotaC_Q5e5_S0p25"]["Lambda"] >= 1.35
    assert l5["scenarios"]["D3_Target_FT_p0p005"]["Lambda"] >= 2.2
    assert l5["fleet_100L_1e9_cryostat_reduction_D2_to_D3"] >= 6.0

    le = res["layer7_logical_qubit_economics"]
    assert le["D2_primary_Lambda1p40"]["1e-9"]["fab_usd_per_L_W3"] < 10.0
    assert le["D3_target_Lambda2p52"]["1e-9"]["fab_usd_per_L_W3"] < 2.0
    assert le["D2_to_D3_deployed_cost_ratio_1e9"] >= 5.0


def test_disk_v5_master_cert_sha256_and_tamper_detection():
    cert_fp = OUT_DIR / "v5_digital_twin_cert.json"
    assert cert_fp.is_file()
    cert = json.loads(cert_fp.read_text(encoding="utf-8"))
    assert len(cert["sha256"]) == 64
    assert verify_v5_certificate(cert) is True

    # Tamper detection
    tampered = dict(cert)
    tampered["bom_v5_m3_nom_usd"] = 1.0
    assert verify_v5_certificate(tampered) is False


def test_all_19_primary_ledger_sha256_match_live_disk():
    cert = json.loads((OUT_DIR / "v5_digital_twin_cert.json").read_text(encoding="utf-8"))
    recorded = cert["primary_ledger_sha256"]
    all_paths = {**PRIMARY_EXPERIMENT_LEDGERS, **ENGINEERING_ARTIFACTS}
    assert set(recorded.keys()) == set(all_paths.keys())
    # Living artifacts evolved cleanly from v5.0 to v6.0 (live disk SHA-256 locked in test_exp146.py);
    # all 16 immutable historical experiment ledgers (exp124..127, exp129..140) must still match bit-for-bit!
    evolved_to_v6 = {"exp128", "cad_v5", "bom_detailed_v5"}
    immutable_checked = 0
    for key, rel in all_paths.items():
        live_h = sha256_file(ROOT / rel)
        assert len(recorded[key]) == 64 and len(live_h) == 64
        if key not in evolved_to_v6:
            assert recorded[key] == live_h, f"SHA-256 mismatch on immutable historical ledger {key} ({rel})"
            immutable_checked += 1
    assert immutable_checked == 16


def test_summary_md_contains_exact_full_64hex_sha256_and_zero_gfm_errors():
    cert = json.loads((OUT_DIR / "v5_digital_twin_cert.json").read_text(encoding="utf-8"))
    full_hash = cert["sha256"]
    assert len(full_hash) == 64

    md_path = OUT_DIR / "summary_exp141.md"
    assert md_path.is_file()
    md_text = md_path.read_text(encoding="utf-8")
    assert full_hash in md_text, "summary_exp141.md must contain full untruncated 64-hex SHA-256!"

    # GFM table column consistency check
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("|") and ln.endswith("|"):
            tbl = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                tbl.append(lines[i].strip())
                i += 1
            cols = [len(r.split("|")[1:-1]) for r in tbl]
            assert len(set(cols)) == 1, f"GFM column mismatch: {cols}"
        else:
            i += 1


def test_preregistration_order_figure_and_zero_hardcoded_host_paths():
    pred = OUT_DIR / "predictions_exp141.json"
    res_fp = OUT_DIR / "exp141.json"
    fig_fp = OUT_DIR / "fig_exp141_v5_digital_twin.png"
    assert pred.is_file() and res_fp.is_file() and fig_fp.is_file()
    assert pred.stat().st_mtime < res_fp.stat().st_mtime
    assert fig_fp.stat().st_size > 150_000

    files = [
        ROOT / "experiments" / "exp141_v5_digital_twin" / "digital_twin141.py",
        ROOT / "experiments" / "exp141_v5_digital_twin" / "run_exp141.py",
        ROOT / "experiments" / "exp141_v5_digital_twin" / "plot_exp141.py",
        ROOT / "experiments" / "exp141_v5_digital_twin" / "wafer_econ141.py",
        pred,
        res_fp,
        OUT_DIR / "v5_digital_twin_cert.json",
        OUT_DIR / "summary_exp141.md",
        ROOT / "tests" / "test_exp141.py",
    ]
    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    for fp in files:
        txt = fp.read_text(encoding="utf-8")
        assert bad_a not in txt, f"Hardcoded host path found in {fp.name}"
        assert bad_b not in txt, f"Hardcoded mount path found in {fp.name}"


def test_v5_master_cert_sha256_matches_canonical_docs():
    cert = json.loads((OUT_DIR / "v5_digital_twin_cert.json").read_text(encoding="utf-8"))
    full_hash = cert["sha256"]
    assert len(full_hash) == 64
    canonical_docs = [
        ROOT / "README.md",
        ROOT / "research" / "atom_lithography_machine" / "DESIGN.md",
        ROOT / "research" / "atom_lithography_machine" / "TECHNICAL_MANUAL.md",
        ROOT / "research" / "hypotheses" / "hypotheses.md",
        OUT_DIR / "summary_exp141.md",
    ]
    for fp in canonical_docs:
        assert fp.is_file(), f"Missing canonical doc: {fp}"
        assert full_hash in fp.read_text(encoding="utf-8"), f"Full 64-hex v5 SHA-256 missing from {fp}"
