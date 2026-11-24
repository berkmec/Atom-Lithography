"""Runner for Exp149 (H167): Real-EDA Verified Q16.16 BOED-FPGA Verilog RTL + Interactive HTML5 Twin.

Usage:
    PYTHONPATH=src python3 -B experiments/exp149_boed_verilog_rtl_and_interactive_twin/run_exp149.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from build_interactive_twin import build_interactive_twin_html  # noqa: E402
from rtl_verifier149 import RTL_DIR, SYNTH_RTL_FILES, run_full_rtl_verification  # noqa: E402

OUT_DIR = REPO_ROOT / "results" / "exp149_boed_verilog_rtl_and_interactive_twin"
PRED_PATH = OUT_DIR / "predictions_exp149.json"


def run_exp149(write_outputs: bool = True, run_yosys: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    preds = json.loads(PRED_PATH.read_text(encoding="utf-8"))

    rtl_res = run_full_rtl_verification(RTL_DIR, write_outputs=write_outputs, run_yosys=run_yosys)
    twin_info = build_interactive_twin_html(rtl_res=rtl_res, write_outputs=write_outputs)

    lint = rtl_res["structural_lint"]
    rom = rtl_res["rom_verification"]
    co = rtl_res["bit_exact_co_verification"]
    veril = rtl_res["verilator_lint"]
    iver = rtl_res["iverilog_simulation"]
    yos = rtl_res["yosys_synthesis"]
    res_b = rtl_res["zu48dr_resource_budget"]
    tot16 = res_b["total_16ch"]

    # Portability & zero-secret self-check
    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    bad_crn = "crn:v1:" + "bluemix:"
    bad_jwt = "bearer " + "eyj"
    scan_files = [
        *(RTL_DIR / f for f in SYNTH_RTL_FILES),
        RTL_DIR / "tb_boed_q16_core.v",
        RTL_DIR / "tb_boed_top_16ch.v",
        RTL_DIR / "zu48dr_boed_250mhz.xdc",
        RTL_DIR / "Makefile",
        RTL_DIR / "README.md",
        HERE / "rtl_verifier149.py",
        HERE / "build_interactive_twin.py",
        HERE / "run_exp149.py",
        HERE / "plot_exp149.py",
        REPO_ROOT / "docs" / "digital_twin_interactive.html",
        PRED_PATH,
    ]
    hygiene_hits: list[str] = []
    for fp in scan_files:
        if fp.is_file():
            txt = fp.read_text(encoding="utf-8")
            low = txt.lower()
            for tok in (bad_a, bad_b, bad_crn, bad_jwt):
                if tok in txt or tok in low:
                    hygiene_hits.append(f"{fp.name}:{tok}")

    yosys_targets = yos.get("targets", {})
    xcup_top16 = yosys_targets.get("xcup_top16", {})
    yosys_fits_zu48dr = bool(
        res_b.get("yosys_measured_pre_pnr", {})
        .get("targets", {})
        .get("xcup_top16", {})
        .get("fits_zu48dr", False)
    )

    verdicts = {
        "RV1_SYNTHESIZABLE_RTL_LINT_ZERO_VIOLATIONS": bool(
            lint["lint_passed"]
            and lint["forbidden_construct_count"] == 0
            and lint["zero_combinational_div_operators"]
            and lint["balance_error_count"] == 0
            and lint["port_error_count"] == 0
            and lint["width_mismatch_count"] == 0
            and lint["instantiations_checked"] >= 4
            and veril["all_passed"]
        ),
        "RV2_ROM_HEX_BIT_EXACT_PARITY": bool(
            rom["all_zero_bit_diff"]
            and rom["rom_p0_entries"] == 512
            and rom["rom_p1_entries"] == 512
            and rom["rom_p0_bit_diffs"] == 0
            and rom["rom_p1_bit_diffs"] == 0
        ),
        "RV3_GOLDEN_VECTORS_64_ZERO_LSB_PARITY": bool(
            co["n_golden_vectors"] == 64
            and co["max_mu_off_q8_lsb_err"] == 0
            and co["max_std_q4_lsb_err"] == 0
            and co["max_next_probe_q8_lsb_err"] == 0
            and co["isqrt_vectors_tested"] == 1000
            and co["isqrt_max_lsb_err"] == 0
            and co["sprt_max_lsb_err"] == 0
            and iver["all_passed"]
            and iver["boed_q16_core"]["vectors_tested"] == 64
            and iver["boed_q16_core"]["max_mu_off_q8_lsb_err"] == 0
            and iver["boed_q16_core"]["max_std_q4_lsb_err"] == 0
            and iver["boed_q16_core"]["max_next_probe_q8_lsb_err"] == 0
            and iver["boed_top_16ch"]["channels_verified"] == 4
        ),
        "RV4_CYCLE_COUNT_584_AND_TIMING_XDC": bool(
            co["boed_cycles_min"] == 584
            and co["boed_cycles_max"] == 584
            and iver["boed_q16_core"]["boed_cycles_min"] == 584
            and iver["boed_q16_core"]["boed_cycles_max"] == 584
            and abs(co["boed_latency_us_at_250MHz"] - 2.336) < 1e-6
            and co["sprt_latency_cycles"] == 4
            and abs(lint["xdc_checks"]["create_clock_period_ns"] - 4.0) < 1e-6
            and lint["xdc_checks"]["single_cycle_clean_no_multicycle_waivers"]
        ),
        "RV5_ZU48DR_16CH_RESOURCE_BUDGET_CLOSURE": bool(
            tot16["dsp48e2_pct"] < 15.0
            and tot16["bram36_pct"] < 10.0
            and tot16["lut_pct"] < 20.0
            and tot16["cryo_heat_load_W"] == 0.0
            and (RTL_DIR / "tb_boed_q16_core.v").is_file()
            and (RTL_DIR / "tb_boed_top_16ch.v").is_file()
            and (not run_yosys or yosys_fits_zu48dr)
        ),
        "RV6_INTERACTIVE_HTML5_TWIN_ZERO_CDN_LIVE_DATA": bool(
            twin_info["zero_external_cdn"]
            and twin_info["size_bytes"] >= 15_000
            and twin_info["embedded_subsystems"] == 9
            and twin_info["embedded_live_qpu_backend"] == "ibm_marrakesh"
            and len(twin_info["embedded_v6_sha256"]) == 64
        ),
        "RV7_ARTIFACTS_PORTABILITY_VISUAL_AND_TESTS": bool(len(hygiene_hits) == 0),
        "RV8_REAL_EDA_IVERILOG_VERILATOR_YOSYS": bool(
            veril["all_passed"]
            and iver["all_passed"]
            and (
                (
                    yos.get("all_passed", False)
                    and yos.get("check_assert_passed", False)
                    and {"xcup_core", "xc7_core", "ecp5_core", "xcup_top16"}.issubset(set(yosys_targets.keys()))
                    and int(xcup_top16.get("dsp_total", 0)) > 0
                    and int(xcup_top16.get("bram_blocks", 0)) > 0
                )
                if run_yosys
                else True
            )
        ),
    }

    out_data: dict[str, Any] = {
        "experiment": "exp149_boed_verilog_rtl_and_interactive_twin",
        "hypothesis_id": "H167",
        "version": "7.2-real-eda",
        "date": "2026-11-24",
        "no_lab_measurement_rtl": True,
        "no_external_eda_sim": False,
        "real_eda_verified": True,
        "no_vendor_vivado_pnr": True,
        "epistemic_scope": {
            "verilog_rtl_and_fpga_budget": (
                "Real-EDA-Verified (Icarus Verilog + Verilator -Wall + Yosys pre-P&R synth_xilinx/synth_ecp5; "
                "no_external_eda_sim=false, no_vendor_vivado_pnr=true, no_lab_measurement_rtl=true)"
            ),
            "embedded_live_qpu_tab": "Canli-Donanim-IBM-QPU (ibm_marrakesh, 156Q, job_id=dc1tdo2nj2vs73dfrfl0)",
        },
        "runtime_s": round(time.perf_counter() - t0, 3),
        "predictions": preds,
        "rtl_verification": rtl_res,
        "interactive_twin": twin_info,
        "hygiene_hits": hygiene_hits,
        "verdicts": verdicts,
        "n_passed": sum(1 for v in verdicts.values() if v),
        "n_total": len(verdicts),
        "success_rule_met": bool(all(verdicts.values())),
    }

    if write_outputs:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "exp149.json").write_text(json.dumps(out_data, indent=2) + "\n", encoding="utf-8")
    return out_data


def main() -> None:
    res = run_exp149(write_outputs=True, run_yosys=True)
    print(f"Exp149 finished in {res['runtime_s']}s | Verdicts: {res['n_passed']}/{res['n_total']} PASS")
    for k, v in res["verdicts"].items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(
        f"Interactive twin: {res['interactive_twin']['html_path']} "
        f"({res['interactive_twin']['size_bytes']:,} bytes, zero_cdn={res['interactive_twin']['zero_external_cdn']})"
    )
    if not res["success_rule_met"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
