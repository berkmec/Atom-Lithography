"""Comprehensive Real-EDA test suite for Exp149 (H167): Q16.16 BOED Verilog RTL & Interactive HTML5 Twin."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = ROOT / "experiments" / "exp149_boed_verilog_rtl_and_interactive_twin"
RES_DIR = ROOT / "results" / "exp149_boed_verilog_rtl_and_interactive_twin"
RTL_DIR = ROOT / "rtl" / "boed_fpga"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(EXP_DIR))

from machine_control.fpga_boed_dsp import FPGACoreConfig, Q1616BOEDCore  # noqa: E402
from rtl_verifier149 import (  # noqa: E402
    GOLDEN_SCENARIOS,
    SYNTH_RTL_FILES,
    co_verify_rtl_golden_vectors,
    discover_eda_toolchain,
    lint_synthesizable_rtl,
    rtl_isqrt_cordic_16stage,
    run_iverilog_simulation,
    run_verilator_lint,
    verify_rom_hex_files_bit_exact,
)
from run_exp149 import run_exp149  # noqa: E402


@pytest.fixture(scope="module")
def live_exp149_result():
    """Execute full live Exp149 (Verilator -Wall + Icarus Verilog vvp + 4-target Yosys) once per module."""
    return run_exp149(write_outputs=False, run_yosys=True)


def test_all_rtl_boed_fpga_files_exist():
    expected = [
        "boed_lut_rom.v",
        "boed_isqrt_cordic.v",
        "boed_q16_core.v",
        "boed_top_16ch.v",
        "tb_boed_q16_core.v",
        "tb_boed_top_16ch.v",
        "zu48dr_boed_250mhz.xdc",
        "rom_loglik_p0.hex",
        "rom_loglik_p1.hex",
        "golden_vectors.mem",
        "Makefile",
        "README.md",
    ]
    for fname in expected:
        fp = RTL_DIR / fname
        assert fp.is_file() and fp.stat().st_size > 0, f"Missing or empty RTL file: {fname}"


def test_real_eda_toolchain_installed_and_discoverable():
    tc = discover_eda_toolchain()
    assert tc["all_required_available"] is True
    for tool in ("iverilog", "vvp", "verilator", "yosys"):
        assert tc["tools"][tool]["available"] is True, f"Required EDA tool missing: {tool}"
        assert tc["tools"][tool]["version"], f"Empty version string for {tool}"


def test_synthesizable_verilog_lint_zero_violations_zero_div_and_clean_xdc():
    lint = lint_synthesizable_rtl(RTL_DIR)
    assert lint["lint_passed"] is True
    assert lint["forbidden_construct_count"] == 0, f"Forbidden constructs: {lint['forbidden_hits']}"
    assert lint["zero_combinational_div_operators"] is True, "Combinational `/` operator found in synthesizable RTL!"
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
    assert lint["xdc_checks"]["has_multicycle_path"] is False
    assert lint["xdc_checks"]["single_cycle_clean_no_multicycle_waivers"] is True


def test_real_verilator_lint_wall_zero_warnings_core_and_top16():
    veril = run_verilator_lint(RTL_DIR)
    assert veril["all_passed"] is True
    for mod in ("boed_q16_core", "boed_top_16ch"):
        rec = veril["targets"][mod]
        assert rec["passed"] is True, f"Verilator lint failed for {mod}: {rec}"
        assert rec["returncode"] == 0
        assert rec["warning_count"] == 0, f"Verilator warnings on {mod}: {rec['warnings']}"
        assert rec["error_count"] == 0, f"Verilator errors on {mod}: {rec['errors']}"


def test_real_iverilog_vvp_bit_exact_64_diverse_vectors_and_top16():
    iver = run_iverilog_simulation(RTL_DIR)
    assert iver["all_passed"] is True

    core = iver["boed_q16_core"]
    assert core["passed"] is True
    assert core["compile_returncode"] == 0
    assert core["vvp_returncode"] == 0
    assert core["vectors_tested"] == 64
    assert len(core["regimes_tested"]) == 8
    assert set(core["regimes_tested"]) == {s["name"] for s in GOLDEN_SCENARIOS}
    assert core["boed_errors"] == 0
    assert core["sprt_errors"] == 0
    assert core["isqrt_errors"] == 0
    assert core["max_mu_off_q8_lsb_err"] == 0
    assert core["max_std_q4_lsb_err"] == 0
    assert core["max_next_probe_q8_lsb_err"] == 0
    assert core["sprt_max_lsb_err"] == 0
    assert core["boed_cycles_min"] == 584
    assert core["boed_cycles_max"] == 584

    top16 = iver["boed_top_16ch"]
    assert top16["passed"] is True
    assert top16["channels_verified"] == 4
    assert top16["errors"] == 0
    assert top16["sprt_ch3_donor"] == 1


def test_real_yosys_synthesis_xcup_xc7_ecp5_and_honest_pre_pnr_distinction(live_exp149_result):
    rtl = live_exp149_result["rtl_verification"]
    yos = rtl["yosys_synthesis"]
    assert yos["all_passed"] is True
    assert yos["check_assert_passed"] is True
    assert yos["measurement_kind"] == "yosys_pre_pnr_measured"
    assert yos["no_vendor_vivado_pnr"] is True

    targets = yos["targets"]
    assert set(targets.keys()) == {"xcup_core", "xc7_core", "ecp5_core", "xcup_top16"}
    for tkey, rec in targets.items():
        assert rec["passed"] is True, f"Yosys synthesis failed for {tkey}"
        assert rec["lut_total"] > 1000
        assert rec["ff_total"] > 1000
        assert rec["bram_blocks"] >= 12
        assert rec["dsp_total"] >= 50

    # True BRAM inference confirmed (4 posterior banks + 8 dual-port LUT ROMs = 12 per engine, 192 for 16ch)
    assert targets["xcup_core"]["bram_blocks"] == 12
    assert targets["xc7_core"]["bram_blocks"] == 12
    assert targets["ecp5_core"]["bram_blocks"] == 12
    assert targets["xcup_top16"]["bram_blocks"] == 192

    # Explicitly distinguish Yosys pre-P&R cell counts from analytical Vivado post-P&R estimates
    rb = rtl["zu48dr_resource_budget"]
    assert rb["estimation_kind"] == "analytical_vivado_post_pnr_estimate"
    assert rb["no_vendor_vivado_pnr"] is True
    ym = rb["yosys_measured_pre_pnr"]
    assert ym["measurement_kind"] == "yosys_pre_pnr_measured"
    assert ym["targets"]["xcup_top16"]["fits_zu48dr"] is True
    assert ym["targets"]["xcup_top16"]["zu48dr_pct"]["dsp48e2_pct"] < 50.0
    assert ym["targets"]["xcup_top16"]["zu48dr_pct"]["bram36_equiv_pct"] < 15.0
    assert ym["targets"]["xcup_top16"]["zu48dr_pct"]["lut_pct"] < 35.0
    assert ym["targets"]["xcup_top16"]["zu48dr_pct"]["ff_pct"] < 15.0

    # Also verify fpga_boed_dsp.Q1616BOEDCore.resource_budget() preserves backwards compatibility
    standalone_rb = Q1616BOEDCore(FPGACoreConfig()).resource_budget(yosys_measured_pre_pnr=targets)
    assert standalone_rb["yosys_measured_pre_pnr"]["targets"]["xcup_top16"]["dsp_total"] == targets["xcup_top16"]["dsp_total"]


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
    assert len(co["regimes_covered"]) == 8
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


def test_exp149_all_8_verdicts_pass_and_honest_eda_flags(live_exp149_result):
    res = live_exp149_result
    assert res["no_external_eda_sim"] is False
    assert res["real_eda_verified"] is True
    assert res["no_vendor_vivado_pnr"] is True
    assert res["no_lab_measurement_rtl"] is True
    assert res["success_rule_met"] is True
    assert res["n_passed"] == res["n_total"] == 8
    for k, v in res["verdicts"].items():
        assert v is True, f"Verdict failed: {k}"

    # Verify baseline empirical audit is recorded cleanly
    base = res["rtl_verification"]["baseline_before_fixes"]
    assert base["iverilog_original_tb_mismatches"] == 64
    assert base["iverilog_negedge_tb_mismatches"] == 64
    assert base["verilator_lint_warnings"] == 40
    assert len(base["bugs_fixed"]) >= 5


def test_interactive_html5_twin_zero_cdn_and_valid_embedded_json():
    html_path = ROOT / "docs" / "digital_twin_interactive.html"
    assert html_path.is_file()
    html = html_path.read_text(encoding="utf-8")
    low = html.lower()
    assert "https://" not in low
    assert "http://" not in low
    assert "<canvas" in low
    assert "<svg" in low
    assert "ibm_marrakesh" in html
    assert "dc1tdo2nj2vs73dfrfl0" in html
    assert "no_vendor_vivado_pnr" in html

    m = re.search(r"const DATA = (\{.*?\});\n", html, flags=re.DOTALL)
    assert m is not None, "Could not locate embedded const DATA JSON in digital_twin_interactive.html"
    embedded = json.loads(m.group(1).replace("<\\/", "</"))
    assert len(embedded["subsystems"]) == 9
    assert embedded["live_qpu"]["backend"]["name"] == "ibm_marrakesh"
    assert embedded["rtl_fpga"]["no_external_eda_sim"] is False
    assert embedded["rtl_fpga"]["real_eda_verified"] is True
    assert embedded["rtl_fpga"]["no_vendor_vivado_pnr"] is True
    assert embedded["rtl_fpga"]["co_ver"]["boed_cycles_max"] == 584
    assert embedded["rtl_fpga"]["iverilog"]["all_passed"] is True
    assert embedded["rtl_fpga"]["verilator"]["all_passed"] is True
    assert embedded["rtl_fpga"]["yosys"]["all_passed"] is True
    assert len(embedded["meta"]["v6_cert_sha256"]) == 64


def test_preregistration_order_yosys_artifacts_and_2400x1400_png():
    pred = RES_DIR / "predictions_exp149.json"
    res_fp = RES_DIR / "exp149.json"
    fig_fp = RES_DIR / "fig_exp149_rtl_fpga_arch.png"
    assert pred.is_file() and res_fp.is_file() and fig_fp.is_file()
    assert pred.stat().st_mtime < res_fp.stat().st_mtime

    for extra in (
        "baseline_eda_audit.json",
        "yosys_xcup_core_stat.json",
        "yosys_xc7_core_stat.json",
        "yosys_ecp5_core_stat.json",
        "yosys_xcup_top16_stat.json",
    ):
        fp = RES_DIR / extra
        assert fp.is_file() and fp.stat().st_size > 0, f"Missing Exp149 EDA artifact: {extra}"

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
        RTL_DIR / "tb_boed_top_16ch.v",
        RTL_DIR / "zu48dr_boed_250mhz.xdc",
        RTL_DIR / "Makefile",
        RTL_DIR / "README.md",
        EXP_DIR / "rtl_verifier149.py",
        EXP_DIR / "build_interactive_twin.py",
        EXP_DIR / "run_exp149.py",
        EXP_DIR / "plot_exp149.py",
        RES_DIR / "predictions_exp149.json",
        RES_DIR / "exp149.json",
        RES_DIR / "baseline_eda_audit.json",
        RES_DIR / "yosys_xcup_core_stat.json",
        RES_DIR / "yosys_xc7_core_stat.json",
        RES_DIR / "yosys_ecp5_core_stat.json",
        RES_DIR / "yosys_xcup_top16_stat.json",
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
