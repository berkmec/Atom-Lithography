"""Comprehensive test suite for Exp146 (H164): Master v6.0 Digital Twin & Cryptographic SHA-256 Certificate."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "exp146_v6_digital_twin"))

from digital_twin146 import (  # noqa: E402
    ENGINEERING_ARTIFACTS,
    LIVE_QPU_ARTIFACT_REL,
    PRIMARY_EXPERIMENT_LEDGERS,
    load_all_v6_artifacts,
    run_v6_digital_twin,
    sha256_file,
    verify_v6_certificate,
)

OUT_DIR = ROOT / "results" / "exp146_v6_digital_twin"


def test_all_24_primary_and_live_qpu_artifacts_load():
    ledgers, eng, live_data, hashes, live_sha = load_all_v6_artifacts(ROOT)
    assert len(ledgers) == 22
    assert len(hashes) == 24
    assert len(live_sha) == 64
    for h in hashes.values():
        assert len(h) == 64
    assert eng["cad_v6"]["overall_pass"] is True
    assert eng["cad_v6"]["master_assembly"]["part_count"] == 199
    assert eng["cad_v6"]["interference_audit"]["solid_clashes"] == 0
    assert len(eng["bom_v6_rows"]) == 174
    assert live_data["backend"]["name"] == "ibm_marrakesh"


def test_v6_digital_twin_all_8_verdicts_pass_live():
    res = run_v6_digital_twin(write_outputs=False)
    assert res["success_rule_met"] is True
    assert res["n_passed"] == res["n_total"] == 8
    for k, v in res["verdicts"].items():
        assert v is True, f"Verdict failed: {k}"

    # Spot-check key v6.0 physical & economic breakthroughs
    assert res["layer2_d3_grape"]["echo_Q1e6_S0p39_p_2q_pct"] <= 0.45
    assert res["layer2_d3_grape"]["lambda_D3_phys_echo_Q1e6_S0p25"] >= 2.80
    assert res["layer3_qldpc"]["L_max_um"] <= 300.0
    assert res["layer3_qldpc"]["config_108L_cryostats"] == 1
    assert res["layer3_qldpc"]["config_108L_usd_per_L_sys_p50"] < 70_000.0
    assert res["layer4_option_q_multispecies"]["F_SWAP_rt_31P_nuclear"] >= 0.985
    assert res["layer5_option_hpc"]["d37_sc_backlog_free_6p70us"] is True
    assert res["layer5_option_hpc"]["qldpc_108L_backlog_free_2p62us"] is True
    assert res["layer6_live_ibm_qpu_and_cellisa40"]["live_ibm_qpu"]["c1_bell_fidelity"] >= 0.95
    assert res["layer6_live_ibm_qpu_and_cellisa40"]["live_auto_recal"]["all_passed"] is True


def test_disk_v6_master_cert_sha256_and_tamper_detection():
    cert_fp = OUT_DIR / "v6_digital_twin_cert.json"
    assert cert_fp.is_file()
    cert = json.loads(cert_fp.read_text(encoding="utf-8"))
    assert len(cert["sha256"]) == 64
    assert verify_v6_certificate(cert) is True

    # Tamper detection on key fields
    for key, bad_val in (
        ("bom_v6_m3_full_nom_usd", 1.0),
        ("live_qpu_bell_fidelity", 0.50),
        ("qldpc_108L_cryostats", 99),
    ):
        tampered = dict(cert)
        tampered[key] = bad_val
        assert verify_v6_certificate(tampered) is False


def test_all_24_primary_plus_live_qpu_sha256_match_live_disk():
    cert = json.loads((OUT_DIR / "v6_digital_twin_cert.json").read_text(encoding="utf-8"))
    recorded = cert["primary_ledger_sha256"]
    all_paths = {**PRIMARY_EXPERIMENT_LEDGERS, **ENGINEERING_ARTIFACTS}
    assert len(all_paths) == 24
    assert set(recorded.keys()) == set(all_paths.keys())
    for key, rel in all_paths.items():
        live_h = sha256_file(ROOT / rel)
        assert recorded[key] == live_h, f"SHA-256 mismatch on disk for {key} ({rel})"

    # Live IBM QPU raw counts JSON must also match bit-for-bit!
    live_qpu_h = sha256_file(ROOT / LIVE_QPU_ARTIFACT_REL)
    assert cert["live_ibm_qpu_results_sha256"] == live_qpu_h


def test_v5_historical_certificate_untouched_and_valid():
    v5_cert_fp = ROOT / "results" / "exp141_v5_digital_twin" / "v5_digital_twin_cert.json"
    assert v5_cert_fp.is_file()
    v5_cert = json.loads(v5_cert_fp.read_text(encoding="utf-8"))
    assert v5_cert["sha256"] == "2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1"


def test_summary_md_contains_exact_full_64hex_sha256_and_zero_gfm_errors():
    cert = json.loads((OUT_DIR / "v6_digital_twin_cert.json").read_text(encoding="utf-8"))
    full_hash = cert["sha256"]
    live_hash = cert["live_ibm_qpu_results_sha256"]
    assert len(full_hash) == 64 and len(live_hash) == 64

    md_path = OUT_DIR / "summary_exp146.md"
    assert md_path.is_file()
    md_text = md_path.read_text(encoding="utf-8")
    assert full_hash in md_text, "summary_exp146.md must contain full untruncated 64-hex v6 cert SHA-256!"
    assert live_hash in md_text, "summary_exp146.md must contain full untruncated 64-hex live QPU SHA-256!"

    # GFM table column consistency check (0 errors)
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
            assert len(set(cols)) == 1, f"GFM table column mismatch: {cols}"
        else:
            i += 1


def test_preregistration_order_and_2400x1400_figure():
    pred = OUT_DIR / "predictions_exp146.json"
    res_fp = OUT_DIR / "exp146.json"
    fig_fp = OUT_DIR / "fig_exp146_v6_digital_twin.png"
    assert pred.is_file() and res_fp.is_file() and fig_fp.is_file()
    assert pred.stat().st_mtime < res_fp.stat().st_mtime

    raw = fig_fp.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w = int.from_bytes(raw[16:20], "big")
    h = int.from_bytes(raw[20:24], "big")
    assert (w, h) == (2400, 1400)


def test_live_ibm_qpu_json_and_exp146_zero_secrets_zero_host_paths():
    files = [
        ROOT / "experiments" / "exp146_v6_digital_twin" / "digital_twin146.py",
        ROOT / "experiments" / "exp146_v6_digital_twin" / "run_exp146.py",
        ROOT / "experiments" / "exp146_v6_digital_twin" / "plot_exp146.py",
        OUT_DIR / "predictions_exp146.json",
        OUT_DIR / "exp146.json",
        OUT_DIR / "exp146_plot_data.json",
        OUT_DIR / "v6_digital_twin_cert.json",
        OUT_DIR / "summary_exp146.md",
        ROOT / LIVE_QPU_ARTIFACT_REL,
        ROOT / "tests" / "test_exp146.py",
    ]
    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    bad_crn = "crn:v1:" + "bluemix:"
    bad_jwt = "bearer " + "eyj"
    for fp in files:
        assert fp.is_file(), f"Missing file: {fp}"
        txt = fp.read_text(encoding="utf-8")
        low = txt.lower()
        assert bad_a not in txt, f"Hardcoded host path found in {fp.name}"
        assert bad_b not in txt, f"Hardcoded mount path found in {fp.name}"
        assert bad_crn not in low, f"CRN secret pattern found in {fp.name}"
        assert bad_jwt not in low, f"JWT Bearer token found in {fp.name}"


def test_evolution_trajectory_v5_D2_to_v6_qLDPC_compression():
    res = json.loads((OUT_DIR / "exp146.json").read_text(encoding="utf-8"))
    tr = res["layer7_v3_to_v6_evolution"]["fleet_100L_trajectory"]
    assert tr["v5_D2_SC_cryostats"] == 679
    assert tr["v6_D3_GRAPE_SC_cryostats"] == 100
    assert tr["v6_qLDPC_108L_cryostats"] == 1
    assert tr["total_usd_per_L_compression_x"] >= 234.0


def test_v6_master_cert_sha256_matches_canonical_docs():
    cert = json.loads((OUT_DIR / "v6_digital_twin_cert.json").read_text(encoding="utf-8"))
    full_hash = cert["sha256"]
    assert len(full_hash) == 64
    canonical_docs = [
        ROOT / "README.md",
        ROOT / "research" / "atom_lithography_machine" / "DESIGN.md",
        ROOT / "research" / "atom_lithography_machine" / "TECHNICAL_MANUAL.md",
        ROOT / "research" / "atom_lithography_machine" / "MODULAR.md",
        ROOT / "research" / "atom_lithography_machine" / "PROJECT_DOSSIER.md",
        ROOT / "research" / "hypotheses" / "hypotheses.md",
        OUT_DIR / "summary_exp146.md",
    ]
    for doc in canonical_docs:
        assert doc.is_file(), f"Missing canonical doc: {doc}"
        assert full_hash in doc.read_text(encoding="utf-8"), (
            f"Full 64-hex v6 SHA-256 missing from {doc.relative_to(ROOT)}"
        )
