"""Comprehensive test suite for Exp149 (H167): Q16.16 BOED Verilog RTL & Interactive HTML5 Digital Twin."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = ROOT / "experiments" / "exp149_boed_verilog_rtl_and_interactive_twin"
RES_DIR = ROOT / "results" / "exp149_boed_verilog_rtl_and_interactive_twin"
RTL_DIR = ROOT / "rtl" / "boed_fpga"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(EXP_DIR))

from build_interactive_twin import build_interactive_twin_html  # noqa: E402
from rtl_verifier149 import (  # noqa: E402
    SYNTH_RTL_FILES,
    co_verify_rtl_golden_vectors,
    lint_synthesizable_rtl,
    rtl_isqrt_cordic_16stage,
    verify_rom_hex_files_bit_exact,
)
from run_exp149 import run_exp149  # noqa: E402


def test_all_10_rtl_boed_fpga_files_exist():
    expected = [
        "boed_lut_rom.v",
        "boed_isqrt_cordic.v",
        "boed_q16_core.v",
        "boed_top_16ch.v",
        "tb_boed_q16_core.v",
        "zu48dr_boed_250mhz.xdc",
        "rom_loglik_p0.hex",
        "rom_loglik_p1.hex",
        "golden_vectors.mem",
        "README.md",
    ]
    for fname in expected:
        fp = RTL_DIR / fname
        assert fp.is_file() and fp.stat().st_size > 0, f"Missing or empty RTL file: {fname}"


def test_synthesizable_verilog_lint_zero_violations_and_ports():
    lint = lint_synthesizable_rtl(RTL_DIR)
    assert lint["lint_passed"] is True
    assert lint["forbidden_construct_count"] == 0, f"Forbidden constructs: {lint['forbidden_hits']}"
    assert lint["balance_error_count"] == 0, f"Balance errors: {lint['balance_errors']}"
    assert lint["port_error_count"] == 0, f"Port errors: {lint['port_errors']}"
    assert lint["width_mismatch_count"] == 0, f"Width mismatches: {lint['width_mismatches']}"
    assert lint["instantiations_checked"] >= 4
    assert set(lint["modules_parsed"]) == {
        "boed_lut_rom",
        "boed_isqrt_cordic",
        "boed_q16_core",
        "boed_top_16ch",
    }
    assert lint["xdc_checks"]["create_clock_period_ns"] == 4.0
    assert lint["xdc_checks"]["target_freq_MHz"] == 250.0


def test_rom_hex_files_512_words_zero_bit_diff():
    rom = verify_rom_hex_files_bit_exact(RTL_DIR)
    assert rom["all_zero_bit_diff"] is True
    assert rom["rom_p0_entries"] == 512
    assert rom["rom_p1_entries"] == 512
    assert rom["rom_p0_bit_diffs"] == 0
    assert rom["rom_p1_bit_diffs"] == 0


def test_golden_vectors_64_zero_lsb_and_584_cycles():
    co = co_verify_rtl_golden_vectors(RTL_DIR)
    assert co["all_zero_lsb"] is True
    assert co["n_golden_vectors"] == 64
    assert co["max_mu_off_q8_lsb_err"] == 0
    assert co["max_std_q4_lsb_err"] == 0
    assert co["max_next_probe_q8_lsb_err"] == 0
    assert co["isqrt_vectors_tested"] == 1000
    assert co["isqrt_max_lsb_err"] == 0
    assert co["sprt_max_lsb_err"] == 0
    assert co["sprt_latency_cycles"] == 4
    assert co["boed_cycles_min"] == 584
    assert co["boed_cycles_max"] == 584
    assert co["boed_latency_us_at_250MHz"] == 2.336


def test_isqrt_16stage_edge_cases():
    for val, exp in ((0, 0), (1, 1), (3, 1), (4, 2), (65535, 255), (65536, 256), (0xFFFFFFFF, 65535)):
        root, cyc = rtl_isqrt_cordic_16stage(val)
        assert root == exp and cyc == 16


def test_exp149_all_7_verdicts_pass_and_honest_eda_flag():
    res = run_exp149(write_outputs=False)
    assert res["no_external_eda_sim"] is True
    assert res["no_lab_measurement_rtl"] is True
    assert res["success_rule_met"] is True
    assert res["n_passed"] == res["n_total"] == 7
    for k, v in res["verdicts"].items():
        assert v is True, f"Verdict failed: {k}"


def test_interactive_html5_twin_zero_cdn_and_valid_embedded_json():
    html_path = ROOT / "docs" / "digital_twin_interactive.html"
    assert html_path.is_file()
    html = html_path.read_text(encoding="utf-8")
    low = html.lower()
    # Zero external CDN or remote HTTP dependencies
    assert "https://" not in low
    assert "http://" not in low
    assert "<canvas" in low
    assert "<svg" in low
    assert "ibm_marrakesh" in html
    assert "dc1tdo2nj2vs73dfrfl0" in html
    assert "no_external_eda_sim" in html

    # Verify embedded DATA JSON parses cleanly and contains live primary artifacts
    m = re.search(r"const DATA = (\{.*?\});\n", html, flags=re.DOTALL)
    assert m is not None, "Could not locate embedded const DATA JSON in digital_twin_interactive.html"
    embedded = json.loads(m.group(1).replace("<\\/", "</"))
    assert len(embedded["subsystems"]) == 9
    assert embedded["live_qpu"]["backend"]["name"] == "ibm_marrakesh"
    assert embedded["rtl_fpga"]["co_ver"]["boed_cycles_max"] == 584
    assert len(embedded["meta"]["v6_cert_sha256"]) == 64


def test_preregistration_order_and_2400x1400_png():
    pred = RES_DIR / "predictions_exp149.json"
    res_fp = RES_DIR / "exp149.json"
    fig_fp = RES_DIR / "fig_exp149_rtl_fpga_arch.png"
    assert pred.is_file() and res_fp.is_file() and fig_fp.is_file()
    assert pred.stat().st_mtime < res_fp.stat().st_mtime

    raw = fig_fp.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w = int.from_bytes(raw[16:20], "big")
    h = int.from_bytes(raw[20:24], "big")
    assert (w, h) == (2400, 1400)


def test_summary_md_zero_gfm_table_errors():
    md_path = RES_DIR / "summary_exp149.md"
    assert md_path.is_file()
    lines = md_path.read_text(encoding="utf-8").splitlines()
    i = 0
    in_code = False
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if not in_code and s.startswith("|") and s.endswith("|"):
            tbl = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                tbl.append(lines[i].strip())
                i += 1
            cols = [len(r.split("|")[1:-1]) for r in tbl]
            assert len(set(cols)) == 1, f"GFM table column mismatch in summary_exp149.md: {cols}"
        else:
            i += 1


def test_exp149_zero_hardcoded_host_paths_and_zero_secrets():
    files = [
        *(RTL_DIR / f for f in SYNTH_RTL_FILES),
        RTL_DIR / "tb_boed_q16_core.v",
        RTL_DIR / "zu48dr_boed_250mhz.xdc",
        RTL_DIR / "README.md",
        EXP_DIR / "rtl_verifier149.py",
        EXP_DIR / "build_interactive_twin.py",
        EXP_DIR / "run_exp149.py",
        EXP_DIR / "plot_exp149.py",
        RES_DIR / "predictions_exp149.json",
        RES_DIR / "exp149.json",
        RES_DIR / "summary_exp149.md",
        ROOT / "docs" / "digital_twin_interactive.html",
        ROOT / "tests" / "test_exp149.py",
    ]
    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    bad_crn = "crn:v1:" + "bluemix:"
    bad_jwt = "bearer " + "eyj"
    for fp in files:
        assert fp.is_file(), f"Missing Exp149 file: {fp}"
        txt = fp.read_text(encoding="utf-8")
        low = txt.lower()
        assert bad_a not in txt, f"Hardcoded host path found in {fp.name}"
        assert bad_b not in txt, f"Hardcoded mount path found in {fp.name}"
        assert bad_crn not in low, f"CRN pattern found in {fp.name}"
        assert bad_jwt not in low, f"JWT pattern found in {fp.name}"
