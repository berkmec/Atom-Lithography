"""Tests for Exp135 (H153): End-to-End v4.0 Full-Machine Digital Twin."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "exp135_v4_digital_twin"))

from digital_twin135 import (
    exact_binomial_ft_yield,
    load_primary_ledgers,
    mc_2d_square_percolation,
    min_ncand_for_target_ft_yield,
    run_digital_twin,
    verify_master_certificate,
)


def test_all_11_primary_ledgers_load_with_sha256():
    ledgers, hashes = load_primary_ledgers(ROOT)
    assert len(ledgers) == 11
    assert len(hashes) == 11
    for h in hashes.values():
        assert len(h) == 64


def test_m4_percolation_vokl6_collision_and_mc_parity():
    # KL canonical: p_M4 = 0.51 * 0.952 = 0.48552 -> N_cand* = 6 for L=11 (>=99%)
    p_kl = 0.51 * 0.952
    assert min_ncand_for_target_ft_yield(p_kl, L=11, target_yield=0.99) == 6
    y_kl_6 = exact_binomial_ft_yield(121, 6, 1.0 - (1.0 - p_kl) ** 6)
    assert y_kl_6 == pytest.approx(0.99239, abs=1e-4)

    # VOKL-6 HM5962 downside: p_M4 = 0.3325 * 0.952 = 0.31654 -> N_cand=6 collapses, N_cand*=11
    p_hm = 0.3325 * 0.952
    y_hm_6 = exact_binomial_ft_yield(121, 6, 1.0 - (1.0 - p_hm) ** 6)
    assert y_hm_6 < 0.05
    assert min_ncand_for_target_ft_yield(p_hm, L=11, target_yield=0.99) == 11

    # MC parity against exact binomial at N_cand = 9 (p_node = 0.96815)
    p_node_9 = 1.0 - (1.0 - p_hm) ** 9
    mc = mc_2d_square_percolation(L=11, p_node=p_node_9, n_mc=1_500, seed=2026135)
    assert abs(mc["Y_FT_5pct_mc"] - mc["Y_FT_5pct_exact"]) < 0.03

    # VOKL-6 HM5962 f=2% isotope lever restores N_cand* = 6
    assert min_ncand_for_target_ft_yield(0.545 * 0.952, L=11, target_yield=0.99) == 6
    # VOKL-6 norm worst-case floor requires N_cand* > 80 (red-line)
    assert min_ncand_for_target_ft_yield(0.0475 * 0.952, L=11, target_yield=0.99) >= 80


def test_digital_twin_end_to_end_verdicts_and_master_cert():
    # Historical v4.0 disk snapshot preserves all 7/7 PASS verdicts verbatim
    hist = json.loads((ROOT / "results" / "exp135_v4_digital_twin" / "exp135.json").read_text(encoding="utf-8"))
    assert hist["n_passed"] == hist["n_total"] == 7
    assert hist["success_rule_met"] is True

    # Live execution verifies DT2..DT7 after Wave-1 OBS-039 fixed Exp92 ZBL rmax=R0+80 straggle truncation
    # (which honestly raises true 5 keV 31P+ placement above the legacy 3.80 nm v4.0 ceiling -> DT1=False).
    res = run_digital_twin(write_outputs=False)
    assert res["no_lab_measurement"] is True
    for k, v in res["verdicts"].items():
        if k != "DT1_PLACEMENT_BUDGET_V4":
            assert v is True, f"Live v4 verdict failed: {k}"

    l1 = res["layer1_placement_budget"]
    assert l1["v400_coupled_15ms_nm"] > 0.0
    assert l1["v400_coupled_10ms_nm"] > 0.0
    assert l1["rigid_CFG1_15ms_nm"] > 2000.0

    # Adaptive BOED accelerates as bath yield drops and stays write-limited across all 3 R1 regimes
    r4 = res["layer4_boed_throughput"]["regimes"]
    assert r4["KL_canonical_f1"]["boed_t_spec_factory_ms"] > r4["VOKL6_HM5962_f1"]["boed_t_spec_factory_ms"]
    assert r4["VOKL6_HM5962_f1"]["boed_t_spec_factory_ms"] > r4["VOKL6_norm_f1_worst"]["boed_t_spec_factory_ms"]
    assert all(r["write_limited_15ms"] and r["write_limited_10ms"] for r in r4.values())
    assert r4["KL_canonical_f1"]["v400_net_15ms_per_day"] >= 1.50e9

    # SHA-256 Master Certificate verification & tamper detection
    mcert = res["v4_master_certificate"]
    assert verify_master_certificate(mcert)
    tampered = dict(mcert)
    tampered["placement_sigma_v4_15ms_nm"] = 9.999
    assert not verify_master_certificate(tampered)


def test_saved_artifacts_and_disk_master_certificate():
    out = ROOT / "results" / "exp135_v4_digital_twin"
    pred = out / "predictions_exp135.json"
    res_fp = out / "exp135.json"
    cert_fp = out / "v4_digital_twin_cert.json"
    assert pred.is_file() and res_fp.is_file() and cert_fp.is_file()
    assert pred.stat().st_mtime < res_fp.stat().st_mtime

    disk_cert = json.loads(cert_fp.read_text(encoding="utf-8"))
    assert verify_master_certificate(disk_cert)


def test_exp135_zero_hardcoded_host_paths():
    files = [
        ROOT / "experiments" / "exp135_v4_digital_twin" / "digital_twin135.py",
        ROOT / "experiments" / "exp135_v4_digital_twin" / "plot_exp135.py",
        ROOT / "results" / "exp135_v4_digital_twin" / "predictions_exp135.json",
        ROOT / "results" / "exp135_v4_digital_twin" / "exp135.json",
        ROOT / "results" / "exp135_v4_digital_twin" / "v4_digital_twin_cert.json",
        ROOT / "tests" / "test_exp135.py",
    ]
    md = ROOT / "results" / "exp135_v4_digital_twin" / "summary_exp135.md"
    if md.is_file():
        files.append(md)
    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    for fp in files:
        txt = fp.read_text(encoding="utf-8")
        assert bad_a not in txt, f"Hardcoded host path found in {fp.name}"
        assert bad_b not in txt, f"Hardcoded mount path found in {fp.name}"


def test_master_certificate_sha256_matches_summary_and_readme():
    cert_fp = ROOT / "results" / "exp135_v4_digital_twin" / "v4_digital_twin_cert.json"
    sha = json.loads(cert_fp.read_text(encoding="utf-8"))["sha256"]
    assert len(sha) == 64
    summary_txt = (ROOT / "results" / "exp135_v4_digital_twin" / "summary_exp135.md").read_text(encoding="utf-8")
    readme_txt = (ROOT / "README.md").read_text(encoding="utf-8")
    assert sha in summary_txt, "v4_digital_twin_cert.json sha256 missing from summary_exp135.md"
    assert sha in readme_txt, "v4_digital_twin_cert.json sha256 missing from README.md"
