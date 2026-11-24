"""Comprehensive test suite for Exp151 (H169): Master v7.2 Digital Twin & Cryptographic SHA-256 Manifest."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "exp151_v7_digital_twin"))

from digital_twin151 import (  # noqa: E402
    ALL_LOCKED_ARTIFACTS,
    BOED_REAL_BATH_ARTIFACT_REL,
    HISTORICAL_MASTER_CERTS,
    INTERACTIVE_TWIN_ARTIFACT_REL,
    LIVE_QPU_ARTIFACT_REL,
    load_all_v7_artifacts,
    run_v7_digital_twin,
    sha256_file,
    verify_v7_certificate,
)

OUT_DIR = ROOT / "results" / "exp151_v7_digital_twin"


def test_all_39_v7_artifacts_load_and_have_64hex_sha256():
    ledgers, eng, live_data, all_hashes, twin_html = load_all_v7_artifacts(ROOT)
    assert len(ledgers) == 27
    assert len(all_hashes) == 39
    assert set(all_hashes.keys()) == set(ALL_LOCKED_ARTIFACTS.keys())
    for k, h in all_hashes.items():
        assert len(h) == 64, f"Invalid SHA-256 length for {k}"
    assert eng["cad_v6"]["overall_pass"] is True
    assert eng["cad_v6"]["master_assembly"]["part_count"] == 199
    assert eng["cad_v6"]["interference_audit"]["solid_clashes"] == 0
    assert len(eng["bom_v7_rows"]) == 180
    assert eng["boed_real_bath"]["benchmark"] == "boed_real_si29_lattice_bath_step2a"
    assert live_data["backend"]["name"] == "ibm_marrakesh"
    assert len(twin_html) >= 40_000


def test_v7_digital_twin_all_8_verdicts_pass_live():
    res = run_v7_digital_twin(write_outputs=False)
    assert res["success_rule_met"] is True
    assert res["n_passed"] == res["n_total"] == 8
    for k, v in res["verdicts"].items():
        assert v is True, f"Verdict failed: {k}"

    assert res["layer2_universal_qldpc_d18"]["femoco"]["qldpc_cryostats"] == 16
    assert res["layer2_universal_qldpc_d18"]["rsa2048"]["qldpc_cryostats"] == 291
    assert res["layer3_sb121_qecho8"]["qecho8_gross_0L_1ms"] >= 0.9990
    assert res["layer3_sb121_qecho8"]["gross_infidelity_reduction_x"] >= 450.0

    # Real EDA verification gates (Exp149)
    l4 = res["layer4_verilog_rtl_and_twin"]
    assert l4["no_external_eda_sim"] is False
    assert l4["real_eda_verified"] is True
    assert l4["no_vendor_vivado_pnr"] is True
    assert l4["no_lab_measurement_rtl"] is True
    assert l4["zero_combinational_div_operators"] is True
    assert l4["boed_cycles_exact"] == 584
    assert l4["golden_all_zero_lsb"] is True
    assert l4["verilator_lint"]["all_passed"] is True
    assert l4["verilator_lint"]["boed_q16_core_warnings"] == 0
    assert l4["verilator_lint"]["boed_top_16ch_warnings"] == 0
    assert l4["iverilog_simulation"]["all_passed"] is True
    assert l4["iverilog_simulation"]["vectors_tested"] == 64
    assert l4["iverilog_simulation"]["boed_errors"] == 0
    assert l4["iverilog_simulation"]["top_16ch_passed"] is True
    ys = l4["yosys_measured_pre_pnr"]
    assert ys["all_passed"] is True
    assert ys["check_assert_passed"] is True
    assert ys["disk_stat_json_parity"] is True
    assert ys["targets"]["xcup_core"]["dsp_total"] == 99
    assert ys["targets"]["xc7_core"]["dsp_total"] == 99
    assert ys["targets"]["ecp5_core"]["dsp_total"] == 106
    assert ys["targets"]["xcup_top16"]["dsp_total"] == 1584
    assert ys["targets"]["xcup_top16"]["bram_blocks"] == 192
    assert ys["targets"]["xcup_top16"]["fits_zu48dr"] is True

    # Clean preliminary-parametric Exp150 safety status (zero false SIL-3 claim)
    l5 = res["layer5_industrial_safety"]
    assert l5["max_rpn_post"] == 42
    assert l5["iec61508_certified"] is False
    assert l5["semi_s2_certified"] is False
    assert l5["certification_status"] == "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED"
    assert l5["sil3_pfd_band_met_at_nominal_assumed_lambda_du"] is True
    assert l5["requires_third_party_assessment"] is True
    assert l5["zero_false_sil3_claim"] is True
    assert l5["pfd_sensitivity_sweep"]["n_cases_degraded_to_sil2"] >= 4
    assert l5["pfd_sensitivity_sweep"]["pfd_10x_lambda_du_beta10pct"] >= 1.0e-3
    assert l5["odh_box_ode_transient"]["dry_60m3_0ACH_min_O2_pct"] > 20.5

    # Upgraded control physics + real 1% 29Si bath BOED + IBM QPU proxy
    l6 = res["layer6_live_ibm_qpu_and_cellisa40"]
    assert l6["live_ibm_qpu"]["c1_bell_fidelity"] >= 0.97
    assert l6["live_cellisa_v40"]["echo_cz"]["echo_fidelity_gain"] > 0.15
    assert l6["live_cellisa_v40"]["echo_cz"]["cptp_max_trace_err"] < 1e-12
    assert l6["live_cellisa_v40"]["mux_readout"]["exp140_n32_ceiling_reproduced"] is True
    assert l6["live_cellisa_v40"]["qldpc_round"]["css_commutativity_verified"] is True
    assert l6["live_cellisa_v40"]["qldpc_round"]["symplectic_logical_verified"] is True
    assert l6["live_auto_recal"]["blanker_step_and_stitch"]["wafer_site_coverage_after_pct"] == 100.0
    assert 0.0 < l6["live_auto_recal"]["blanker_step_and_stitch"]["throughput_after_recal_pct"] < 100.0
    assert l6["live_auto_recal"]["blanker_step_and_stitch"]["max_coordinate_mismatch_um"] == 0.0
    assert l6["live_auto_recal"]["uhv_langmuir_ode"]["surface_monolayer_coverage_frac"] < 0.01
    assert l6["live_auto_recal"]["laser_thermal_pde"]["worst_uncontrolled_sigma_nm"] > 0.50
    assert l6["live_auto_recal"]["laser_thermal_pde"]["worst_controlled_sigma_nm"] <= 0.50
    bath = l6["real_si29_bath_boed"]
    assert bath["boed_identification_accuracy"] > bath["uniform_identification_accuracy"]
    assert bath["probe_speedup_vs_uniform_raw"] >= 8.0
    assert bath["legacy_exp132_fnr_on_real_bath"] == 1.0
    assert bath["honest_failure_walls"]["low_snr_cliff_fnr_at_snr3"] == 1.0


def test_disk_v7_master_cert_sha256_and_tamper_detection():
    cert_fp = OUT_DIR / "v7_digital_twin_cert.json"
    exp151_fp = OUT_DIR / "exp151.json"
    assert cert_fp.is_file() and exp151_fp.is_file()
    raw_cert = cert_fp.read_text(encoding="utf-8")
    raw_exp151 = exp151_fp.read_text(encoding="utf-8")
    legacy_bad_key = "sil3" + "_achieved"
    assert legacy_bad_key not in raw_cert
    assert legacy_bad_key not in raw_exp151

    cert = json.loads(raw_cert)
    assert len(cert["sha256"]) == 64
    assert cert["n_locked_artifacts"] == 39
    assert cert["exp149_no_external_eda_sim"] is False
    assert cert["exp149_real_eda_verified"] is True
    assert cert["exp149_no_vendor_vivado_pnr"] is True
    assert cert["exp150_iec61508_certified"] is False
    assert cert["exp150_semi_s2_certified"] is False
    assert cert["exp150_certification_status"] == "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED"
    assert 0.0 < cert["live_auto_recal_blanker_honest_throughput_pct"] < 100.0
    assert verify_v7_certificate(cert) is True

    for key, bad_val in (
        ("bom_v7_m3_v7_full_nom_usd", 1.0),
        ("exp148_sb121_qecho8_gross_0L", 0.5),
        ("exp150_fmea_max_rpn_post", 999),
        ("exp150_iec61508_certified", True),
        ("exp149_rtl_cycles", 123),
        ("real_si29_bath_boed_accuracy", 0.1),
        ("live_qpu_bell_fidelity", 0.42),
    ):
        tampered = dict(cert)
        tampered[key] = bad_val
        assert verify_v7_certificate(tampered) is False, f"Tamper undetected on {key}"

    # Tamper inside nested locked_artifacts_sha256 must also invalidate digest
    tampered_nested = json.loads(json.dumps(cert))
    tampered_nested["locked_artifacts_sha256"]["exp150"] = "0" * 64
    assert verify_v7_certificate(tampered_nested) is False
    tampered_nested2 = json.loads(json.dumps(cert))
    tampered_nested2["locked_artifacts_sha256"]["boed_real_bath_benchmark"] = "f" * 64
    assert verify_v7_certificate(tampered_nested2) is False


def test_all_39_locked_artifacts_sha256_match_live_disk():
    cert = json.loads((OUT_DIR / "v7_digital_twin_cert.json").read_text(encoding="utf-8"))
    recorded = cert["locked_artifacts_sha256"]
    assert len(ALL_LOCKED_ARTIFACTS) == 39
    assert set(recorded.keys()) == set(ALL_LOCKED_ARTIFACTS.keys())
    for key, rel in ALL_LOCKED_ARTIFACTS.items():
        live_h = sha256_file(ROOT / rel)
        assert recorded[key] == live_h, f"SHA-256 mismatch on live disk for {key} ({rel})"


def test_historical_v4_v5_v6_master_certs_strictly_untouched():
    for ver, (rel, expected_sha) in HISTORICAL_MASTER_CERTS.items():
        fp = ROOT / rel
        assert fp.is_file(), f"Missing historical {ver} cert: {rel}"
        cert = json.loads(fp.read_text(encoding="utf-8"))
        assert cert["sha256"] == expected_sha, f"Historical {ver} cert altered!"


def test_honest_physical_and_economic_boundaries_preserved():
    res = json.loads((OUT_DIR / "exp151.json").read_text(encoding="utf-8"))
    assert res["no_lab_measurement_silicon_rtl_safety"] is True
    assert res["no_supplier_quotes"] is True
    assert res["no_external_eda_sim"] is False
    assert res["real_eda_verified"] is True
    assert res["no_vendor_vivado_pnr"] is True
    assert res["iec61508_certified"] is False
    assert res["semi_s2_certified"] is False
    assert res["safety_certification_status"] == "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED"
    assert res["layer2_universal_qldpc_d18"]["uq4_honest_fail"] is True
    assert res["layer2_universal_qldpc_d18"]["uq5_honest_fail"] is True
    assert res["layer3_sb121_qecho8"]["sq4_honest_1f_fail"] is True
    assert res["layer4_verilog_rtl_and_twin"]["no_external_eda_sim"] is False
    assert res["layer4_verilog_rtl_and_twin"]["no_vendor_vivado_pnr"] is True
    assert res["layer5_industrial_safety"]["iec61508_certified"] is False
    assert res["layer5_industrial_safety"]["semi_s2_certified"] is False
    mt = res["layer7_v7_phased_procurement_and_evolution"]["modular_tiers_v7"]
    assert mt["M3_v5_0_Base"]["P_gt_100M_pct"] < 5.0
    assert mt["M3_Phase1_Base_Plus_Safety"]["P_gt_100M_pct"] < 5.0
    assert mt["M3_v6_0_Full"]["P_gt_100M_pct"] < 5.0
    assert mt["M3_v7_0_Full"]["P_gt_100M_pct"] > 5.0


def test_live_v7_interactive_html5_twin_zero_cdn_and_v7_payload():
    html_fp = ROOT / INTERACTIVE_TWIN_ARTIFACT_REL
    assert html_fp.is_file()
    html = html_fp.read_text(encoding="utf-8")
    low = html.lower()
    assert "https://" not in low
    assert "http://" not in low
    m = re.search(r"const DATA = (\{.*?\});\n", html, flags=re.DOTALL)
    assert m is not None
    emb = json.loads(m.group(1).replace("<\\/", "</"))
    assert len(emb["subsystems"]) == 9
    assert emb["rtl_fpga"]["no_external_eda_sim"] is False
    assert emb["rtl_fpga"]["real_eda_verified"] is True
    assert emb["bom_modular"]["base_plus_safety_nom"] == 5_392_800.0
    assert emb["bom_modular"]["v7_full_nom"] == 5_692_800.0
    assert emb["v7_algorithms"]["femoco"]["qldpc_cryos"] == 16
    assert emb["v7_algorithms"]["rsa2048"]["qldpc_cryos"] == 291
    assert emb["v7_sb121"]["qecho8_gross_0L"] >= 0.9990
    assert emb["v7_safety"]["max_rpn_post"] == 42

    cert = json.loads((OUT_DIR / "v7_digital_twin_cert.json").read_text(encoding="utf-8"))
    assert cert["locked_artifacts_sha256"]["interactive_twin_html"] == sha256_file(html_fp)


def test_summary_md_contains_exact_full_64hex_sha256_and_zero_gfm_errors():
    cert = json.loads((OUT_DIR / "v7_digital_twin_cert.json").read_text(encoding="utf-8"))
    full_hash = cert["sha256"]
    live_hash = cert["locked_artifacts_sha256"]["live_ibm_qpu_results"]
    twin_hash = cert["locked_artifacts_sha256"]["interactive_twin_html"]
    bath_hash = cert["locked_artifacts_sha256"]["boed_real_bath_benchmark"]
    assert all(len(h) == 64 for h in (full_hash, live_hash, twin_hash, bath_hash))

    md_fp = OUT_DIR / "summary_exp151.md"
    assert md_fp.is_file()
    md_text = md_fp.read_text(encoding="utf-8")
    assert full_hash in md_text, "summary_exp151.md must contain full 64-hex v7 cert SHA-256"
    assert live_hash in md_text, "summary_exp151.md must contain full 64-hex live QPU SHA-256"
    assert twin_hash in md_text, "summary_exp151.md must contain full 64-hex HTML5 twin SHA-256"
    assert bath_hash in md_text, "summary_exp151.md must contain full 64-hex real-bath BOED SHA-256"

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
            assert len(set(cols)) == 1, f"GFM column mismatch in summary_exp151.md: {cols}"
        else:
            i += 1


def test_preregistration_order_and_2400x1400_png():
    pred = OUT_DIR / "predictions_exp151.json"
    res_fp = OUT_DIR / "exp151.json"
    fig_fp = OUT_DIR / "fig_exp151_v7_digital_twin.png"
    assert pred.is_file() and res_fp.is_file() and fig_fp.is_file()
    assert pred.stat().st_mtime < res_fp.stat().st_mtime

    raw = fig_fp.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w = int.from_bytes(raw[16:20], "big")
    h = int.from_bytes(raw[20:24], "big")
    assert (w, h) == (2400, 1400)


def test_exp151_zero_hardcoded_host_paths_and_zero_secrets():
    files = [
        ROOT / "experiments" / "exp151_v7_digital_twin" / "digital_twin151.py",
        ROOT / "experiments" / "exp151_v7_digital_twin" / "run_exp151.py",
        ROOT / "experiments" / "exp151_v7_digital_twin" / "plot_exp151.py",
        OUT_DIR / "predictions_exp151.json",
        OUT_DIR / "exp151.json",
        OUT_DIR / "exp151_plot_data.json",
        OUT_DIR / "v7_digital_twin_cert.json",
        OUT_DIR / "summary_exp151.md",
        ROOT / INTERACTIVE_TWIN_ARTIFACT_REL,
        ROOT / LIVE_QPU_ARTIFACT_REL,
        ROOT / BOED_REAL_BATH_ARTIFACT_REL,
        ROOT / "tests" / "test_exp151.py",
    ]
    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    bad_crn = "crn:v1:" + "bluemix:"
    bad_jwt = "bearer " + "eyj"
    for fp in files:
        assert fp.is_file(), f"Missing Exp151 file: {fp}"
        txt = fp.read_text(encoding="utf-8")
        low = txt.lower()
        assert bad_a not in txt, f"Hardcoded host path found in {fp.name}"
        assert bad_b not in txt, f"Hardcoded mount path found in {fp.name}"
        assert bad_crn not in low, f"CRN secret pattern found in {fp.name}"
        assert bad_jwt not in low, f"JWT Bearer token found in {fp.name}"


def test_phased_procurement_and_v3_to_v7_trajectory():
    res = json.loads((OUT_DIR / "exp151.json").read_text(encoding="utf-8"))
    l7 = res["layer7_v7_phased_procurement_and_evolution"]
    bom = l7["bom_evolution_nom_usd"]
    assert bom["v3_0_base"] == 4_189_600.0
    assert bom["v4_0_base"] == 4_609_600.0
    assert bom["v5_0_base"] == 5_247_800.0
    assert bom["v7_phase1_base_safety"] == 5_392_800.0
    assert bom["v6_0_full"] == 5_547_800.0
    assert bom["v7_0_full"] == 5_692_800.0
    fl = l7["fleet_100L_trajectory"]
    assert fl["v5_D2_SC_cryostats"] == 679
    assert fl["v6_D3_GRAPE_SC_cryostats"] == 100
    assert fl["v6_qLDPC_108L_cryostats"] == 1


def test_live_ibm_qpu_and_cellisa40_in_disk_exp151():
    res = json.loads((OUT_DIR / "exp151.json").read_text(encoding="utf-8"))
    l6 = res["layer6_live_ibm_qpu_and_cellisa40"]
    assert l6["secret_leaks"] == []
    assert l6["live_ibm_qpu"]["backend_name"] == "ibm_marrakesh"
    assert l6["live_ibm_qpu"]["job_id"] == "dc1tdo2nj2vs73dfrfl0"
    assert l6["live_ibm_qpu"]["c2_avg_p_L_postsel"] == 0.0
    assert l6["live_cellisa_v40"]["v40_total_opcodes"] == 20
    assert l6["live_cellisa_v40"]["echo_cz"]["echo_fidelity_gain"] > 0.15
    assert l6["live_cellisa_v40"]["mux_readout"]["exp140_n32_ceiling_reproduced"] is True
    assert l6["live_cellisa_v40"]["qldpc_round"]["css_commutativity_verified"] is True
    assert l6["live_auto_recal"]["all_passed"] is True
    assert l6["live_auto_recal"]["blanker_step_and_stitch"]["wafer_site_coverage_after_pct"] == 100.0
    assert 0.0 < l6["live_auto_recal"]["blanker_step_and_stitch"]["throughput_after_recal_pct"] < 100.0
    assert l6["real_si29_bath_boed"]["boed_identification_accuracy"] > 0.90


def test_v7_master_cert_sha256_matches_canonical_docs():
    cert = json.loads((OUT_DIR / "v7_digital_twin_cert.json").read_text(encoding="utf-8"))
    full_hash = cert["sha256"]
    assert len(full_hash) == 64
    canonical_docs = [
        ROOT / "README.md",
        ROOT / "research" / "atom_lithography_machine" / "DESIGN.md",
        ROOT / "research" / "atom_lithography_machine" / "TECHNICAL_MANUAL.md",
        ROOT / "research" / "atom_lithography_machine" / "MODULAR.md",
        ROOT / "research" / "atom_lithography_machine" / "PROJECT_DOSSIER.md",
        ROOT / "research" / "hypotheses" / "hypotheses.md",
        OUT_DIR / "summary_exp151.md",
    ]
    for doc in canonical_docs:
        assert doc.is_file(), f"Missing canonical doc: {doc}"
        assert full_hash in doc.read_text(encoding="utf-8"), (
            f"Canonical v7 master SHA-256 missing or mismatched in {doc.relative_to(ROOT)}"
        )
