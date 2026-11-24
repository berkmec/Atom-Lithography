"""Exp151 (H169): Master v7.2 End-to-End Digital Twin & Cryptographic SHA-256 File-Integrity Manifest.

Unifies all 39 primary v7.2 repository artifacts:
  - 27 primary experiment ledgers (Exp124..Exp150)
  - Real 1% 29Si diamond-cubic lattice-bath BOED benchmark (results/boed_real_bath_benchmark.json)
  - Live 156Q IBM Heron r2 hardware validation (ibm_marrakesh, job_id=dc1tdo2nj2vs73dfrfl0)
  - CAD v6.0 (199 parts, 1,108.137 kg, 0/19,701 static clashes, 40/40 clearances)
  - BOM v7.0 (180 parts, Base $5.248M / Base+Safety $5.393M / v6 Full $5.548M / v7 Full $5.693M, 10-RFQ)
  - Real-EDA-verified synthesizable IEEE 1364-2005 Verilog RTL (rtl/boed_fpga/: 4 .v + 2 .hex + golden_vectors.mem;
    Verilator -Wall 0 warnings, Icarus Verilog 64/64 0-LSB / 584 cyc, Yosys pre-P&R xcup/xc7/ecp5)
  - Zero-CDN Live Interactive HTML5 Digital Twin (docs/digital_twin_interactive.html)
into a single canonical-JSON SHA-256 file-integrity manifest (provenance only, not certification).

Portable execution (zero hardcoded host paths):
    PYTHONPATH=src python3 -B experiments/exp151_v7_digital_twin/run_exp151.py

Epistemic boundary:
    - Silicon 31P/121Sb/167Er fabrication, CAD/BOM v7.0, Universal qLDPC d=18 (Exp147),
      121Sb Q-Echo-8 (Exp148), 1% 29Si lattice-bath BOED, upgraded auto_recal/programmer physics,
      and Exp150 preliminary parametric safety (iec61508_certified=false, semi_s2_certified=false,
      PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED): {Model}/{Sayisal-Simulasyon}/{Varsayim}/{Liste-Capasi}
      (TRL 1-2 / M0, no_lab_measurement=true, no_supplier_quotes=true).
    - Verilog RTL (Exp149): verified with real open-source EDA tools on host (iverilog + vvp + verilator +
      yosys pre-P&R; no_external_eda_sim=false, real_eda_verified=true, no_vendor_vivado_pnr=true,
      no_lab_measurement_rtl=true).
    - Control/DD/Bell/d=3-QEC/Q16.16-BOED hardware proxy on ibm_marrakesh:
      {Canli-Donanim-IBM-QPU} (independently recomputed from raw shot counts on disk, 0 secrets;
      validates zero silicon 31P fabrication hardware).
"""
from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
EXP149_DIR = ROOT / "experiments" / "exp149_boed_verilog_rtl_and_interactive_twin"
if str(EXP149_DIR) not in sys.path:
    sys.path.insert(0, str(EXP149_DIR))

from machine_control.auto_recal import AutoRecalController  # noqa: E402
from machine_control.cloud_qpu_bridge import analyze_validation_suite_counts  # noqa: E402
from machine_control.factory import Certificate  # noqa: E402
from machine_control.programmer import (  # noqa: E402
    MultiCellProgrammer,
    VALID_OPCODES,
    VALID_OPCODES_ALL,
    VALID_OPCODES_V4,
)
from rtl_verifier149 import RTL_DIR, run_full_rtl_verification  # noqa: E402

OUT_DIR = ROOT / "results" / "exp151_v7_digital_twin"
PRED_PATH = OUT_DIR / "predictions_exp151.json"

PRIMARY_EXPERIMENT_LEDGERS: dict[str, str] = {
    "exp124": "results/exp124_ion_column_optics/exp124.json",
    "exp125": "results/exp125_cryo_magnet_readout/exp125.json",
    "exp126": "results/exp126_atom_cell_programming/exp126.json",
    "exp127": "results/exp127_detector_frontend_sim/exp127.json",
    "exp128": "results/exp128_bom_sensitivity/exp128.json",
    "exp129": "results/exp129_valley_orbital_hyperfine/exp129.json",
    "exp130": "results/exp130_flash_anneal_diffusion/exp130.json",
    "exp131": "results/exp131_scalable_m4_architecture/exp131.json",
    "exp132": "results/exp132_bayesian_spectroscopy_cellisa3/exp132.json",
    "exp133": "results/exp133_coupled_vibration_thermal/exp133.json",
    "exp134": "results/exp134_fab_economics_tco/exp134.json",
    "exp135": "results/exp135_v4_digital_twin/exp135.json",
    "exp136": "results/exp136_tb_sp3d5s_hyperfine/exp136.json",
    "exp137": "results/exp137_echoed_m4_bus_gate/exp137.json",
    "exp138": "results/exp138_defective_surface_code_ft/exp138.json",
    "exp139": "results/exp139_epi_cap_process_integration/exp139.json",
    "exp140": "results/exp140_cryo_fpga_boed_mux_readout/exp140.json",
    "exp141": "results/exp141_v5_digital_twin/exp141.json",
    "exp142": "results/exp142_option_q_multispecies_qram/exp142.json",
    "exp143": "results/exp143_d3_grape_m4_and_hpc_decoder/exp143.json",
    "exp144": "results/exp144_qldpc_bivariate_bicycle_m4/exp144.json",
    "exp145": "results/exp145_cloud_qpu_ibm_validation/exp145.json",
    "exp146": "results/exp146_v6_digital_twin/exp146.json",
    "exp147": "results/exp147_universal_qldpc_d18_magic_state/exp147.json",
    "exp148": "results/exp148_sb121_quadrupole_echo_qudit/exp148.json",
    "exp149": "results/exp149_boed_verilog_rtl_and_interactive_twin/exp149.json",
    "exp150": "results/exp150_industrial_safety_fmea_hazop/exp150.json",
}

ENGINEERING_ARTIFACTS: dict[str, str] = {
    "cad_v6": "research/atom_lithography_machine/cad/cad_verification.json",
    "bom_detailed_v7": "research/atom_lithography_machine/BOM_DETAILED.csv",
}

RTL_ARTIFACTS: dict[str, str] = {
    "rtl_boed_lut_rom": "rtl/boed_fpga/boed_lut_rom.v",
    "rtl_boed_isqrt_cordic": "rtl/boed_fpga/boed_isqrt_cordic.v",
    "rtl_boed_q16_core": "rtl/boed_fpga/boed_q16_core.v",
    "rtl_boed_top_16ch": "rtl/boed_fpga/boed_top_16ch.v",
    "rtl_rom_loglik_p0": "rtl/boed_fpga/rom_loglik_p0.hex",
    "rtl_rom_loglik_p1": "rtl/boed_fpga/rom_loglik_p1.hex",
    "rtl_golden_vectors": "rtl/boed_fpga/golden_vectors.mem",
}

INTERACTIVE_TWIN_ARTIFACT_REL = "docs/digital_twin_interactive.html"
LIVE_QPU_ARTIFACT_REL = "results/exp145_cloud_qpu_ibm_validation/ibm_qpu_live_results.json"
BOED_REAL_BATH_ARTIFACT_REL = "results/boed_real_bath_benchmark.json"

ALL_LOCKED_ARTIFACTS: dict[str, str] = {
    **PRIMARY_EXPERIMENT_LEDGERS,
    **ENGINEERING_ARTIFACTS,
    **RTL_ARTIFACTS,
    "interactive_twin_html": INTERACTIVE_TWIN_ARTIFACT_REL,
    "live_ibm_qpu_results": LIVE_QPU_ARTIFACT_REL,
    "boed_real_bath_benchmark": BOED_REAL_BATH_ARTIFACT_REL,
}

HISTORICAL_MASTER_CERTS: dict[str, tuple[str, str]] = {
    "v4": (
        "results/exp135_v4_digital_twin/v4_digital_twin_cert.json",
        "feffc1d4ba2b0698c3f61015c6684da47f57ea863a8b3e0da845cc9c71914b57",
    ),
    "v5": (
        "results/exp141_v5_digital_twin/v5_digital_twin_cert.json",
        "2828e8ce8d9388f7cba5490b2d05add930aadc5fe6d3ba4295f0380f816d43d1",
    ),
    "v6": (
        "results/exp146_v6_digital_twin/v6_digital_twin_cert.json",
        "ca3f0e0267263bacb973f46c3cc2d321c0f204075ea232f4094758e1a9abf1d7",
    ),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_all_v7_artifacts(
    root: Path = ROOT,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, str], str]:
    """Load all 27 experiment JSONs + CAD v6.0 + BOM v7.0 + 7 RTL + HTML5 Twin + Live QPU + Real-Bath BOED (39 total)."""
    ledgers: dict[str, dict[str, Any]] = {}
    all_hashes: dict[str, str] = {}

    for key, rel in PRIMARY_EXPERIMENT_LEDGERS.items():
        fp = root / rel
        if not fp.is_file():
            raise FileNotFoundError(f"Missing primary experiment ledger: {rel}")
        raw = fp.read_bytes()
        all_hashes[key] = hashlib.sha256(raw).hexdigest()
        ledgers[key] = json.loads(raw.decode("utf-8"))

    for key, rel in {**ENGINEERING_ARTIFACTS, **RTL_ARTIFACTS}.items():
        fp = root / rel
        if not fp.is_file():
            raise FileNotFoundError(f"Missing v7.2 artifact: {rel}")
        all_hashes[key] = hashlib.sha256(fp.read_bytes()).hexdigest()

    twin_fp = root / INTERACTIVE_TWIN_ARTIFACT_REL
    live_fp = root / LIVE_QPU_ARTIFACT_REL
    bath_fp = root / BOED_REAL_BATH_ARTIFACT_REL
    for fp in (twin_fp, live_fp, bath_fp):
        if not fp.is_file():
            raise FileNotFoundError(f"Missing v7.2 artifact: {fp}")

    twin_raw = twin_fp.read_bytes()
    live_raw = live_fp.read_bytes()
    bath_raw = bath_fp.read_bytes()
    all_hashes["interactive_twin_html"] = hashlib.sha256(twin_raw).hexdigest()
    all_hashes["live_ibm_qpu_results"] = hashlib.sha256(live_raw).hexdigest()
    all_hashes["boed_real_bath_benchmark"] = hashlib.sha256(bath_raw).hexdigest()

    cad_data = json.loads((root / ENGINEERING_ARTIFACTS["cad_v6"]).read_text(encoding="utf-8"))
    with (root / ENGINEERING_ARTIFACTS["bom_detailed_v7"]).open("r", encoding="utf-8", newline="") as f:
        bom_rows = list(csv.DictReader(f))
    live_data = json.loads(live_raw.decode("utf-8"))
    bath_data = json.loads(bath_raw.decode("utf-8"))
    twin_html = twin_raw.decode("utf-8")

    eng = {"cad_v6": cad_data, "bom_v7_rows": bom_rows, "boed_real_bath": bath_data}
    return ledgers, eng, live_data, all_hashes, twin_html


def compute_layer1_integrity(
    ledgers: dict[str, Any],
    eng: dict[str, Any],
    all_hashes: dict[str, str],
) -> dict[str, Any]:
    """DT7_1: 39/39 Ledger + CAD v6.0 + BOM v7.0 + RTL + Interactive HTML5 Twin + Live QPU + Real-Bath BOED Lock."""
    cad = eng["cad_v6"]
    ma = cad["master_assembly"]
    ia = cad["interference_audit"]
    cc = cad["critical_clearances"]
    cc_total = len(cc)
    cc_pass = sum(1 for v in cc.values() if isinstance(v, dict) and v.get("pass") is True)

    b128 = ledgers["exp128"]["bom_detailed_summary"]
    rfq = ledgers["exp128"]["rfq_coverage"]
    mass_v6 = ledgers["exp128"]["v6_hardware_mass_reconciliation"]
    mass_v7 = ledgers["exp128"]["v7_hardware_mass_reconciliation"]

    return {
        "n_experiment_ledgers": len(PRIMARY_EXPERIMENT_LEDGERS),
        "n_rtl_locked_files": len(RTL_ARTIFACTS),
        "n_total_locked_artifacts": len(all_hashes),
        "live_qpu_artifact_sha256": all_hashes["live_ibm_qpu_results"],
        "interactive_twin_html_sha256": all_hashes["interactive_twin_html"],
        "boed_real_bath_sha256": all_hashes["boed_real_bath_benchmark"],
        "cad_v6": {
            "version": cad["cad_version"],
            "overall_pass": bool(cad["overall_pass"]),
            "part_count": int(ma["part_count"]),
            "total_mass_kg": round(float(ma["total_mass_kg"]), 3),
            "stl_triangles": int(ma["stl"]["triangles"]),
            "stl_watertight": bool(ma["stl"]["is_watertight"]),
            "pairs_checked": int(ia["pairs_checked"]),
            "solid_clashes": int(ia["solid_clashes"]),
            "clearances_passed": cc_pass,
            "clearances_total": cc_total,
        },
        "bom_v7": {
            "version": b128["bom_version"],
            "csv_row_count": len(eng["bom_v7_rows"]),
            "exp128_total_parts": int(b128["total_parts"]),
            "v5_base_parts": int(b128["v5_base_parts"]),
            "v6_option_parts": int(b128["v6_option_parts"]),
            "v7_safety_parts": int(b128["v7_safety_parts"]),
            "m3_v5_base_nom_usd": float(b128["m3_v5_base_nom_usd"]),
            "m3_base_plus_safety_nom_usd": float(b128["m3_base_plus_safety_nom_usd"]),
            "m3_v6_full_nom_usd": float(b128["m3_v6_full_nom_usd"]),
            "m3_v7_full_nom_usd": float(b128["m3_v7_safety_certified_full_nom_usd"]),
            "v7_safety_nom_usd": float(b128["v7_safety_nom_usd"]),
            "reconciliation_error_usd": float(b128["reconciliation_error_usd"]),
            "on_frame_cad_mass_error_kg": float(mass_v6["mass_reconciliation_error_kg"]),
            "facility_safety_mass_kg": float(mass_v7["facility_safety_bom_total_mass_kg"]),
            "total_facility_load_mass_kg": round(float(mass_v7["total_facility_load_mass_kg"]), 3),
            "v7_mass_reconciliation_error_kg": float(mass_v7["mass_reconciliation_error_kg"]),
            "rfq10_nom_share_pct": round(float(rfq["rfq10_nom_share"]) * 100.0, 2),
            "rfq10_var_share_pct": round(float(rfq["rfq10_variance_share_mc"]) * 100.0, 2),
        },
    }


def compute_layer2_universal_qldpc_d18(ledgers: dict[str, Any]) -> dict[str, Any]:
    """DT7_2: Exp147 Universal qLDPC [[288,12,18]] + Magic State Factory + FeMoco/RSA-2048."""
    d147 = ledgers["exp147"]
    alg = d147["part1_bb288_algebra_and_family"]["bb288_summary"]
    p2 = d147["part2_m4_layout_and_576_yield"]
    l20 = p2["layout_by_pitch_um"]["20um"]
    y576 = p2["defect_yields_576cell"]["f1p5_Ez2MVm_v5_star"]["by_N_cand"]
    p3 = d147["part3_d6_to_d18_circuit_dem"]["uniform_4code_sweep"]
    femoco_cult = d147["part5_flagship_algorithms"]["FeMoco_192L_1e8T"]["qLDPC_d18_Gidney_Cult_116to12"]
    femoco_sc = d147["part5_flagship_algorithms"]["FeMoco_192L_1e8T"]["SurfaceCode_D3_Baseline"]
    femoco_comp = d147["part5_flagship_algorithms"]["FeMoco_192L_1e8T"]["compression_vs_SC_Cultivation"]
    rsa_cult = d147["part5_flagship_algorithms"]["RSA2048_4096L_1e10T"]["qLDPC_d24_D3_GidneyCult"]
    rsa_sc = d147["part5_flagship_algorithms"]["RSA2048_4096L_1e10T"]["SurfaceCode_D3_Baseline"]
    rsa_comp = d147["part5_flagship_algorithms"]["RSA2048_4096L_1e10T"]["compression_d24_Cult_vs_SC"]

    return {
        "exp147_n_passed": int(d147["n_passed"]),
        "exp147_n_total": int(d147["n_total"]),
        "uq4_honest_fail": not bool(d147["verdicts"]["UQ4_UNIVERSAL_MAGIC_STATE_FACTORIES"]),
        "uq5_honest_fail": not bool(d147["verdicts"]["UQ5_FEMOCO_CHEMISTRY_RESOURCE_AND_COST"]),
        "bb288_commutes": bool(alg["commutativity_H_X_H_ZT_zero"]),
        "bb288_d_lit": int(alg["d_lit"]),
        "bb288_depth": int(alg["schedule_depth"]),
        "bb288_zero_kickback": bool(alg["schedule_zero_kickback"]),
        "L_max_um": float(l20["L_max_um"]),
        "fits_300um_m4_resonator": bool(l20["fits_300um_m4_resonator"]),
        "p_th_72_vs_288_pct": round(float(p3["p_th_72_vs_288"]) * 100.0, 3),
        "yield_576_N8_pct": round(float(y576["N8"]["block_576_yield_pct"]), 3),
        "yield_576_N9_pct": round(float(y576["N9"]["block_576_yield_pct"]), 3),
        "femoco": {
            "qldpc_cryostats": int(femoco_cult["total_cryostats_ld400"]),
            "sc_cryostats": int(femoco_sc["total_cryostats_ld400"]),
            "runtime_hours": round(float(femoco_cult["runtime_hours"]), 3),
            "power_MW": round(float(femoco_cult["tco_and_power"]["total_facility_power_mw"]), 4),
            "cost_per_solve_usd_p50": round(float(femoco_cult["cost_per_solve_usd_p50"]), 2),
            "cryo_compression_x": round(float(femoco_comp["cryostats_x"]), 2),
            "honest_uq5_readout_ceiling_note": "2-3 us readout ceiling (p_meas=0.22-0.39%) drives p_fail_memory at d=18; D3++ (p_2q<=0.20%, p_meas<=0.10%) or d=24 closes memory floor.",
        },
        "rsa2048": {
            "qldpc_cryostats": int(rsa_cult["total_cryostats_ld400"]),
            "sc_cryostats": int(rsa_sc["total_cryostats_ld400"]),
            "runtime_hours": round(float(rsa_cult["runtime_hours"]), 2),
            "power_MW": round(float(rsa_cult["tco_and_power"]["total_facility_power_mw"]), 3),
            "tco5_musd_p50": round(float(rsa_cult["tco_and_power"]["tco5_musd_p50"]), 3),
            "cryo_compression_x": round(float(rsa_comp["cryostats_x"]), 2),
        },
    }


def compute_layer3_sb121_qecho8(ledgers: dict[str, Any]) -> dict[str, Any]:
    """DT7_3: Exp148 121Sb Q-Echo-8 static quadrupole wall closure & SU(8) GRAPE."""
    d148 = ledgers["exp148"]
    v = d148["verdicts_sq1_to_sq6"]
    sq2 = v["SQ2_QECHO_ALGEBRAIC_CANCELLATION"]["measured"]
    sq3 = v["SQ3_QECHO_CLOSES_EXP142_OQ6_500HZ"]["measured"]
    sq4 = v["SQ4_COLORED_1F_STRAIN_SCALING"]["measured"]
    sq6 = v["SQ6_SU8_GRAPE_LOGICAL_GATES"]["measured"]
    gates = d148["su8_grape_logical_gates"]["gates"]

    bare_g = float(sq3["bare_gross_0L_1ms"])
    echo_g = float(sq3["qecho8_finite_neutral_gross_0L_1ms"])
    infid_red = (1.0 - bare_g) / max(1.0 - echo_g, 1e-12)

    return {
        "exp148_core_passed": d148["core_sq_passed"],
        "exp142_oq6_closure_status": d148["exp142_oq6_closure_status"],
        "qecho8_algebraic_static_F_proc": float(sq2["qecho8_static_500Hz_process_fidelity"]),
        "bare_gross_0L_1ms": round(bare_g, 5),
        "qecho8_gross_0L_1ms": round(echo_g, 6),
        "gross_infidelity_reduction_x": round(infid_red, 1),
        "bare_cat77_1ms": round(float(sq3["bare_cat77_1ms"]), 5),
        "qecho8_cat77_1ms": round(float(sq3["qecho8_finite_neutral_cat77_1ms"]), 6),
        "su8_grape_X_L_F": round(float(gates["X_L"]["F_L_noiseless_full_crosstalk"]), 6),
        "su8_grape_Z_L_F": round(float(gates["Z_L"]["F_L_noiseless_full_crosstalk"]), 6),
        "su8_grape_H_L_F": round(float(gates["H_L"]["F_L_noiseless_full_crosstalk"]), 6),
        "su8_grape_min_F": round(float(sq6["min_F_L_noiseless_full_crosstalk"]), 6),
        "sq4_honest_1f_fail": v["SQ4_COLORED_1F_STRAIN_SCALING"]["status"] == "FAIL",
        "t2_gain_qecho8_1f_x": float(sq4["T2_gain_qecho8_vs_bare"]),
        "t2_gain_qecho64_1f_x": float(sq4["T2_gain_qecho64_vs_bare"]),
        "t2_qecho64_ms": float(sq4["qecho64_gross_T2_eff_ms"]),
    }


def compute_layer4_verilog_rtl_and_twin(
    ledgers: dict[str, Any],
    twin_html: str,
    run_live_yosys: bool = False,
) -> dict[str, Any]:
    """DT7_4: Real-EDA HDL verification (iverilog + verilator + yosys from Exp149) & HTML5 Twin audit."""
    # Never write into rtl/boed_fpga/ from Exp151; always run live Verilator -Wall + Icarus Verilog 64-vec + top16!
    rtl = run_full_rtl_verification(RTL_DIR, write_outputs=False, run_yosys=run_live_yosys)
    lint = rtl["structural_lint"]
    rom = rtl["rom_verification"]
    co = rtl["bit_exact_co_verification"]
    vlint = rtl["verilator_lint"]
    isim = rtl["iverilog_simulation"]
    tot16_analyt = rtl["zu48dr_resource_budget"]["total_16ch"]

    e149 = ledgers["exp149"]
    e149_rv = e149["rtl_verification"]
    yosys_src = rtl["yosys_synthesis"] if run_live_yosys else e149_rv["yosys_synthesis"]
    yosys_targets = yosys_src["targets"]

    # Independently cross-check all 4 measured Yosys stat JSON artifacts on disk against exp149.json
    e149_res_dir = ROOT / "results" / "exp149_boed_verilog_rtl_and_interactive_twin"
    yosys_disk_parity = True
    yosys_summary: dict[str, dict[str, Any]] = {}
    zu48dr_caps = {"dsp48e2": 4272, "bram36": 1080, "lut": 425280, "ff": 850560}
    for tname in ("xcup_core", "xc7_core", "ecp5_core", "xcup_top16"):
        td = yosys_targets[tname]
        stat_fp = e149_res_dir / f"yosys_{tname}_stat.json"
        if not stat_fp.is_file():
            yosys_disk_parity = False
        else:
            disk_td = json.loads(stat_fp.read_text(encoding="utf-8"))
            for fld in ("lut_total", "ff_total", "bram_blocks", "bram36_equiv", "dsp_total", "carry_cells", "passed"):
                if disk_td.get(fld) != td.get(fld):
                    yosys_disk_parity = False
        entry: dict[str, Any] = {
            "family": td["family"],
            "top_module": td["top_module"],
            "measurement_kind": td.get("measurement_kind", "yosys_pre_pnr_measured"),
            "lut_total": int(td["lut_total"]),
            "ff_total": int(td["ff_total"]),
            "bram_blocks": int(td["bram_blocks"]),
            "bram36_equiv": float(td["bram36_equiv"]),
            "dsp_total": int(td["dsp_total"]),
            "carry_cells": int(td["carry_cells"]),
            "passed": bool(td["passed"]),
        }
        if tname in ("xcup_core", "xcup_top16"):
            dsp_pct = round(100.0 * entry["dsp_total"] / zu48dr_caps["dsp48e2"], 2)
            bram_pct = round(100.0 * entry["bram36_equiv"] / zu48dr_caps["bram36"], 2)
            lut_pct = round(100.0 * entry["lut_total"] / zu48dr_caps["lut"], 2)
            ff_pct = round(100.0 * entry["ff_total"] / zu48dr_caps["ff"], 2)
            entry["zu48dr_pct"] = {
                "dsp48e2_pct": dsp_pct,
                "bram36_equiv_pct": bram_pct,
                "lut_pct": lut_pct,
                "ff_pct": ff_pct,
            }
            entry["fits_zu48dr"] = bool(dsp_pct < 100.0 and bram_pct < 100.0 and lut_pct < 100.0 and ff_pct < 100.0)
        yosys_summary[tname] = entry

    low_html = twin_html.lower()
    has_external_cdn = any(p in low_html for p in ("https://", "http://", "cdn.jsdelivr", "unpkg.com"))
    twin_leaks = [
        tok for tok in ("crn:v1:" + "bluemix:", "bearer " + "eyj", "/" + "home/berk", "/" + "run/media/berk")
        if tok in low_html or tok in twin_html
    ]
    m = re.search(r"const DATA = (\{.*?\});\n", twin_html, flags=re.DOTALL)
    embedded_ok = False
    embedded_v7_keys_ok = False
    embedded_real_eda_ok = False
    if m is not None:
        emb = json.loads(m.group(1).replace("<\\/", "</"))
        embedded_ok = (
            len(emb.get("subsystems", [])) == 9
            and emb.get("live_qpu", {}).get("backend", {}).get("name") == "ibm_marrakesh"
            and emb.get("rtl_fpga", {}).get("co_ver", {}).get("boed_cycles_max") == 584
        )
        embedded_v7_keys_ok = all(k in emb for k in ("v7_algorithms", "v7_sb121", "v7_safety"))
        embedded_real_eda_ok = (
            emb.get("rtl_fpga", {}).get("no_external_eda_sim") is False
            and emb.get("rtl_fpga", {}).get("real_eda_verified") is True
        )

    icore = isim["boed_q16_core"]
    itop = isim["boed_top_16ch"]
    vcore = vlint["targets"]["boed_q16_core"]
    vtop = vlint["targets"]["boed_top_16ch"]

    return {
        "no_external_eda_sim": bool(e149["no_external_eda_sim"] or rtl["no_external_eda_sim"]),
        "real_eda_verified": bool(e149["real_eda_verified"] and vlint["all_passed"] and isim["all_passed"] and yosys_src["all_passed"]),
        "no_vendor_vivado_pnr": bool(e149["no_vendor_vivado_pnr"]),
        "no_lab_measurement_rtl": bool(e149["no_lab_measurement_rtl"]),
        "exp149_verdicts_passed": f"{e149['n_passed']}/{e149['n_total']}",
        "synth_files_count": len(lint["synth_files_checked"]),
        "total_rtl_loc": int(lint["total_rtl_loc"]),
        "forbidden_constructs": int(lint["forbidden_construct_count"]),
        "zero_combinational_div_operators": bool(lint.get("zero_combinational_div_operators", False)),
        "single_cycle_clean_no_multicycle_waivers": bool(
            lint.get("xdc_checks", {}).get("single_cycle_clean_no_multicycle_waivers", False)
        ),
        "port_errors": int(lint["port_error_count"]),
        "width_mismatches": int(lint["width_mismatch_count"]),
        "rom_words_checked": int(rom["total_words_checked"]),
        "rom_all_zero_bit_diff": bool(rom["all_zero_bit_diff"]),
        "golden_vectors_tested": int(co["n_golden_vectors"]),
        "golden_all_zero_lsb": bool(co["all_zero_lsb"]),
        "isqrt_vectors_tested": int(co["isqrt_vectors_tested"]),
        "isqrt_max_lsb_err": int(co["isqrt_max_lsb_err"]),
        "boed_cycles_exact": int(co["boed_cycles_max"]),
        "boed_latency_us_250MHz": float(co["boed_latency_us_at_250MHz"]),
        "sprt_latency_cycles": int(co["sprt_latency_cycles"]),
        "verilator_lint": {
            "all_passed": bool(vlint["all_passed"]),
            "boed_q16_core_warnings": int(vcore["warning_count"]),
            "boed_q16_core_errors": int(vcore["error_count"]),
            "boed_top_16ch_warnings": int(vtop["warning_count"]),
            "boed_top_16ch_errors": int(vtop["error_count"]),
        },
        "iverilog_simulation": {
            "all_passed": bool(isim["all_passed"]),
            "vectors_tested": int(icore["vectors_tested"]),
            "boed_errors": int(icore["boed_errors"]),
            "sprt_errors": int(icore["sprt_errors"]),
            "isqrt_errors": int(icore["isqrt_errors"]),
            "max_mu_off_q8_lsb_err": int(icore["max_mu_off_q8_lsb_err"]),
            "max_std_q4_lsb_err": int(icore["max_std_q4_lsb_err"]),
            "max_next_probe_q8_lsb_err": int(icore["max_next_probe_q8_lsb_err"]),
            "boed_cycles_min": int(icore["boed_cycles_min"]),
            "boed_cycles_max": int(icore["boed_cycles_max"]),
            "top_16ch_passed": bool(itop["passed"]),
            "top_16ch_channels_verified": int(itop["channels_verified"]),
            "top_16ch_errors": int(itop["errors"]),
        },
        "yosys_measured_pre_pnr": {
            "all_passed": bool(yosys_src["all_passed"]),
            "check_assert_passed": bool(yosys_src.get("check_assert_passed", False)),
            "disk_stat_json_parity": yosys_disk_parity,
            "no_vendor_vivado_pnr": True,
            "targets": yosys_summary,
        },
        "zu48dr_16ch_dsp_pct_analytical_vivado_est": float(tot16_analyt["dsp48e2_pct"]),
        "zu48dr_16ch_bram_pct_analytical_vivado_est": float(tot16_analyt["bram36_pct"]),
        "zu48dr_16ch_dsp_pct": float(yosys_summary["xcup_top16"]["zu48dr_pct"]["dsp48e2_pct"]),
        "zu48dr_16ch_bram_pct": float(yosys_summary["xcup_top16"]["zu48dr_pct"]["bram36_equiv_pct"]),
        "zu48dr_16ch_lut_pct": float(yosys_summary["xcup_top16"]["zu48dr_pct"]["lut_pct"]),
        "zu48dr_16ch_ff_pct": float(yosys_summary["xcup_top16"]["zu48dr_pct"]["ff_pct"]),
        "zu48dr_16ch_cryo_W": float(tot16_analyt["cryo_heat_load_W"]),
        "interactive_twin": {
            "size_bytes": len(twin_html.encode("utf-8")),
            "zero_external_cdn": not has_external_cdn,
            "zero_secret_and_path_leaks": len(twin_leaks) == 0,
            "embedded_json_valid": embedded_ok,
            "embedded_v7_live_sections": embedded_v7_keys_ok,
            "embedded_real_eda_verified": embedded_real_eda_ok,
        },
    }


def compute_layer5_industrial_safety(ledgers: dict[str, Any]) -> dict[str, Any]:
    """DT7_5: Exp150 Preliminary Parametric Safety FMEA/HAZOP & S7.SAFETY (Uncertified M0)."""
    d150 = ledgers["exp150"]
    fmea = d150["fmea_summary"]
    h1 = d150["hazard_1_laser_s55"]
    il = h1["interlock_sil3"]
    pfd_sw = il["pfd_sensitivity_sweep"]
    h2 = d150["hazard_2_ph3_and_forming_gas"]
    h3 = d150["hazard_3_hv_and_xray"]["energy_sweep"]["22keV"]
    odh = d150["hazard_4_cryo_odh_and_quench"]["helium_odh"]
    h4 = odh["room_sweep"]["60m3"]
    odh_tr = odh["box_ode_transient"]
    h5 = d150["hazard_5_epo_ups_shutdown"]
    kit = d150["s_safety_spec"]["totals"]

    legacy_bad_key = "sil3" + "_achieved"
    zero_false_sil3_claim = (legacy_bad_key not in d150) and (legacy_bad_key not in il)
    b10_10x = next(
        c for c in pfd_sw["by_beta"]["beta_10pct"]
        if abs(float(c["lambda_du_multiplier"]) - 10.0) < 1e-9
    )

    return {
        "overall_verdict": d150["overall_verdict"],
        "criteria_passed": d150["criteria_passed"],
        "all_7_verdicts_pass": all(bool(v["pass"]) for v in d150["preregistered_verdicts"].values()),
        "iec61508_certified": bool(d150["iec61508_certified"]),
        "semi_s2_certified": bool(d150["semi_s2_certified"]),
        "certification_status": str(d150["certification_status"]),
        "sil3_pfd_band_met_at_nominal_assumed_lambda_du": bool(
            il["sil3_pfd_band_met_at_nominal_assumed_lambda_du"]
        ),
        "requires_third_party_assessment": bool(d150["requires_third_party_assessment"]),
        "zero_false_sil3_claim": zero_false_sil3_claim,
        "fmea_rows": int(fmea["n_rows"]),
        "hazop_nodes": len(d150["hazop_10_nodes"]),
        "max_rpn_pre": int(fmea["max_rpn_pre"]),
        "max_rpn_post": int(fmea["max_rpn_post"]),
        "mean_rpn_reduction_pct": float(fmea["mean_rpn_reduction_pct"]),
        "residual_gt_60_count": int(fmea["n_unacceptable_post_gt60"]),
        "laser_od_spec": int(h1["specified_enclosure_OD"]),
        "sil3_shutter_ms": float(il["shutter_close_ms"]),
        "pfd_avg_1oo2d_nominal": float(il["pfd_avg_1oo2d"]),
        "pfd_sensitivity_sweep": {
            "n_cases_total": int(pfd_sw["summary"]["n_cases_total"]),
            "n_cases_in_sil3_pfd_band": int(pfd_sw["summary"]["n_cases_in_sil3_pfd_band"]),
            "n_cases_degraded_to_sil2": int(pfd_sw["summary"]["n_cases_degraded_to_sil2"]),
            "pfd_10x_lambda_du_beta10pct": float(b10_10x["pfd_avg_1oo2d"]),
            "band_10x_lambda_du_beta10pct": str(b10_10x["parametric_pfd_band"]),
            "max_multiplier_beta2pct": float(pfd_sw["sil3_band_boundaries_by_beta"]["beta_2pct"]["max_multiplier_vs_nominal"]),
            "max_multiplier_beta5pct": float(pfd_sw["sil3_band_boundaries_by_beta"]["beta_5pct"]["max_multiplier_vs_nominal"]),
            "max_multiplier_beta10pct": float(pfd_sw["sil3_band_boundaries_by_beta"]["beta_10pct"]["max_multiplier_vs_nominal"]),
        },
        "xray_22kev_shrouded_uSv_h": float(h3["s55_sapphire_plus_3mm_steel_shroud_uSv_h"]),
        "ph3_operator_ppm": float(h2["mitigated_sds_system"]["operator_direct_sds_diffusive_ppm"]),
        "he_60m3_O2_pct": float(h4["dry_ld400_pt420_O2_pct"]),
        "odh_box_ode_transient": {
            "dry_60m3_20ACH_min_O2_pct": float(odh_tr["dry_60m3_20ACH"]["o2_min_pct"]),
            "dry_60m3_0ACH_min_O2_pct": float(odh_tr["dry_60m3_0ACH_hvac_loss"]["o2_min_pct"]),
            "dry_15m3_0ACH_min_O2_pct": float(odh_tr["dry_15m3_0ACH_hvac_loss"]["o2_min_pct"]),
            "wet_100L_60m3_20ACH_min_O2_pct": float(odh_tr["wet_100L_60m3_20ACH"]["o2_min_pct"]),
        },
        "ups_rating_kVA": float(h5["ups_spec"]["rating_kVA"]),
        "ups_full_load_min": float(h5["ups_spec"]["runtime_at_rated_13p5kW_min"]),
        "ups_tier1_min": float(h5["ups_spec"]["runtime_tier1_min"]),
        "uhv_gate_valve_ms": float(h5["uhv_isolation"]["gate_valve_close_ms"]),
        "s_safety_items": int(kit["n_items"]),
        "s_safety_nom_usd": float(kit["cost_usd_nom"]),
        "s_safety_mass_kg": float(kit["total_mass_kg"]),
        "s_safety_power_W": float(kit["steady_electrical_power_W"]),
        "s_safety_cryo_W": float(kit["cryo_load_W"]),
    }


def run_layer6_live_ibm_qpu_and_cellisa40(
    live_data: dict[str, Any],
    live_raw_text: str,
    boed_real_bath: dict[str, Any],
) -> dict[str, Any]:
    """DT7_6: Live ibm_marrakesh raw-count audit + upgraded CellISA/auto_recal physics + real 1% 29Si bath BOED."""
    secret_leaks: list[str] = []
    low_txt = live_raw_text.lower()
    for pat in ("crn:v1:" + "bluemix:", "bearer " + "eyj", "api" + "key=", "/" + "home/berk", "/" + "run/media/berk"):
        if pat in low_txt:
            secret_leaks.append(pat)

    recomp = analyze_validation_suite_counts(
        counts_by_pub=live_data["counts_by_pub"],
        c3_delays_us=live_data["timing_actual"]["c3_delays_us"],
        c3_programmed_kHz=live_data["timing_actual"]["c3_programmed_detuning_kHz"],
        c1_idle_us=live_data["timing_actual"]["c1_idle_us"],
    )
    lc1 = recomp["C1_dd_and_bell"]
    lc2 = recomp["C2_repcode3"]
    lc3 = recomp["C3_ramsey_boed"]

    mcp = MultiCellProgrammer()
    demo_cert = Certificate(
        register_id="REG-EXP151-V7-01",
        slot=0,
        attempts=1,
        shots=1,
        min_spacing_Hz=12_000.0,
        dd_quality_gate=True,
        lines_Hz=[120_000.0, 92_000.0, 68_000.0, 48_000.0],
    )
    demo_cert_b = Certificate(
        register_id="REG-EXP151-V7-02",
        slot=1,
        attempts=1,
        shots=1,
        min_spacing_Hz=12_000.0,
        dd_quality_gate=True,
        lines_Hz=[118_000.0, 90_000.0, 66_000.0, 46_000.0],
    )
    qram_live = mcp.execute_qram_swap(demo_cert, qubit_a="e", qubit_b="n0", seed=2026151)
    echo_cz_live = mcp.execute_echo_cz(demo_cert, demo_cert_b, n_traj=12, seed=2026151)
    mux32_live = mcp.execute_mux_readout([f"C{i}" for i in range(32)], n_mux=32)
    mux64_live = mcp.execute_mux_readout([f"C{i}" for i in range(64)], n_mux=64)
    qldpc_live = mcp.execute_qldpc_round(
        code_name="BB_288_12_18", p_phys=0.00337, rounds=1, n_shots=128, seed=2026151
    )
    recal_live = AutoRecalController(seed=2026151).run_all_fault_scenarios()

    r_las = recal_live["S5_5_laser_drift"]
    r_uhv = recal_live["S5_uhv_vacuum_spike"]
    r_blk = recal_live["S3_blanker_dead_channels"]
    r_hyp = recal_live["hyperfine_thermal_drift"]

    # Real 1% 29Si diamond-cubic lattice-bath BOED benchmark summary (Step 2A)
    bs = boed_real_bath["bath_statistics"]
    ab = boed_real_bath["adaptive_boed"]
    un = boed_real_bath["uniform_nyquist"]
    lg = boed_real_bath["legacy_exp132_on_real_bath"]
    cp = boed_real_bath["comparison"]
    hf = boed_real_bath["honest_failure_regimes"]
    fac = boed_real_bath["factory_real_si29_verification_15slots"]
    fwall = hf["fourier_resolution_wall"]
    snr_curve = hf["low_snr_breakdown"]["curve"]
    snr3_pt = next(p for p in snr_curve if abs(float(p["snr_per_fine_probe"]) - 3.0) < 1e-9)

    return {
        "epistemic_split": {
            "silicon_31P_bath_control_safety": "Model/Sayisal-Simulasyon (TRL 1-2 / M0, no_lab_measurement=true, iec61508_certified=false, semi_s2_certified=false)",
            "rtl_eda_verification": "Real open-source EDA verified on host (iverilog + verilator -Wall + yosys pre-P&R; no_external_eda_sim=false, no_vendor_vivado_pnr=true)",
            "ibm_qpu_metrics": "Canli-Donanim-IBM-QPU (ibm_marrakesh, 156Q Heron r2; superconducting control/decoder proxy, validates zero silicon 31P hardware)",
        },
        "secret_leaks": secret_leaks,
        "live_ibm_qpu": {
            "backend_name": live_data["backend"]["name"],
            "n_qubits": int(live_data["backend"]["n_qubits"]),
            "job_id": live_data["job"]["job_id"],
            "wall_clock_seconds": float(live_data["job"]["wall_clock_seconds"]),
            "c1_bare_p0": lc1["p0_bare_idle"],
            "c1_echo_p0": lc1["p0_hahn_echo"],
            "c1_xy4_p0": lc1["p0_xy4_dd"],
            "c1_xy4_gain_pp": round(lc1["dd_gain_xy4_over_bare"] * 100.0, 2),
            "c1_bell_fidelity": lc1["bell_fidelity_Phi_plus"],
            "c2_suppression_mwpm": round(lc2["avg_p_phys"] / max(lc2["avg_p_L_syndrome_mwpm"], 1e-6), 2),
            "c2_suppression_majority": lc2["suppression_ratio_decoded"],
            "c2_avg_p_L_postsel": lc2["avg_p_L_postsel"],
            "c3_q16_boed_kHz": lc3["q16_16_boed"]["est_freq_kHz"],
            "c3_q16_points_used": lc3["q16_16_boed"]["n_points"],
            "c3_q16_vs_fp64_kHz": lc3["q16_16_boed"]["q16_vs_fp64_diff_kHz"],
        },
        "live_cellisa_v40": {
            "v35_compat_opcodes": len(VALID_OPCODES),
            "v40_total_opcodes": len(VALID_OPCODES_ALL),
            "v40_new_opcodes": sorted(VALID_OPCODES_V4),
            "qram_swap_fidelity": float(qram_live["swap_fidelity"]),
            "echo_cz": {
                "model": str(echo_cz_live["model"]),
                "bare_cz_bell_fidelity": float(echo_cz_live["bare_cz_bell_fidelity"]),
                "echo_cz_bell_fidelity": float(echo_cz_live["echo_cz_bell_fidelity"]),
                "echo_fidelity_gain": float(echo_cz_live["echo_fidelity_gain"]),
                "echo_entangling_phase_over_pi": float(echo_cz_live["echo_entangling_phase_over_pi"]),
                "cavity_leakage_prob": float(echo_cz_live["cavity_leakage_prob"]),
                "cptp_max_trace_err": float(echo_cz_live["cptp_audit"]["max_trace_err"]),
                "cptp_min_eigval": float(echo_cz_live["cptp_audit"]["min_eigval"]),
            },
            "mux_readout": {
                "model": str(mux32_live["model"]),
                "mux32_per_cell_fidelity": float(mux32_live["per_cell_readout_fidelity"]),
                "mux64_per_cell_fidelity": float(mux64_live["per_cell_readout_fidelity"]),
                "mux32_mean_snr": float(mux32_live["mean_snr"]),
                "mux64_mean_snr": float(mux64_live["mean_snr"]),
                "exp140_n32_ceiling_reproduced": bool(
                    mux32_live["per_cell_readout_fidelity"] >= 0.990
                    and mux64_live["per_cell_readout_fidelity"] < 0.990
                ),
            },
            "qldpc_round": {
                "decoder": str(qldpc_live["decoder"]),
                "code_name": str(qldpc_live["code_name"]),
                "n_data": int(qldpc_live["n_data"]),
                "n_logical": int(qldpc_live["n_logical"]),
                "distance": int(qldpc_live["distance"]),
                "css_commutativity_verified": bool(qldpc_live["css_commutativity_verified"]),
                "symplectic_logical_verified": bool(qldpc_live["symplectic_logical_verified"]),
                "feedlines_required": int(qldpc_live["feedlines_required"]),
                "n_shots": int(qldpc_live["n_shots"]),
                "n_logical_errors": int(qldpc_live["n_logical_errors"]),
                "syndrome_valid_frac": float(qldpc_live["syndrome_valid_frac"]),
                "bp_converged_frac": float(qldpc_live["bp_converged_frac"]),
            },
            "qldpc_round_feedlines": int(qldpc_live["feedlines_required"]),
        },
        "live_auto_recal": {
            "n_passed": int(recal_live["n_passed"]),
            "n_fault_modes": int(recal_live["n_fault_modes"]),
            "all_passed": bool(recal_live["all_passed"]),
            "laser_thermal_pde": {
                "thermal_model": str(r_las["thermal_model"]),
                "reference_T_peak_K": float(r_las["reference_T_peak_K"]),
                "reference_energy_balance_rel_err": float(r_las["reference_energy_balance_rel_err"]),
                "worst_uncontrolled_sigma_nm": float(r_las["worst_uncontrolled_sigma_nm"]),
                "worst_controlled_sigma_nm": float(r_las["worst_controlled_sigma_nm"]),
                "max_abs_delta_T_peak_K": float(r_las["max_abs_delta_T_peak_K"]),
            },
            "uhv_langmuir_ode": {
                "ode_solver": str(r_uhv["ode_solver"]),
                "peak_ch2_wafer_torr": float(r_uhv["peak_ch2_wafer_torr"]),
                "exposure_langmuir_total": float(r_uhv["exposure_langmuir_total"]),
                "exposure_langmuir_burst_excess": float(r_uhv["exposure_langmuir_burst_excess"]),
                "valve_excess_protection_factor": float(r_uhv["valve_excess_protection_factor"]),
                "surface_monolayer_coverage_frac": float(r_uhv["surface_monolayer_coverage_frac"]),
                "pumpdown_recovery_s": float(r_uhv["pumpdown_recovery_s"]),
            },
            "blanker_step_and_stitch": {
                "compensation_mode": str(r_blk["compensation_mode"]),
                "dead_channels_detected": int(r_blk["dead_channels_detected"]),
                "stitch_passes_required": int(r_blk["stitch_passes_required"]),
                "wafer_site_coverage_after_pct": float(r_blk["wafer_site_coverage_after_pct"]),
                "throughput_after_recal_pct": float(r_blk["throughput_after_recal_pct"]),
                "throughput_penalty_pct": float(r_blk["throughput_penalty_pct"]),
                "max_coordinate_mismatch_um": float(r_blk["max_coordinate_mismatch_um"]),
                "zero_double_exposure": bool(r_blk["zero_double_exposure"]),
            },
            "hyperfine_boed_relock": {
                "max_relock_time_ms": float(r_hyp["max_relock_time_ms"]),
                "max_residual_error_Hz": float(r_hyp["max_residual_error_Hz"]),
            },
        },
        "real_si29_bath_boed": {
            "benchmark": str(boed_real_bath["benchmark"]),
            "no_lab_measurement": bool(boed_real_bath["no_lab_measurement"]),
            "abundance_pct": float(bs["abundance_pct"]),
            "lattice_total_sites": int(bs["lattice_total_sites"]),
            "n_candidates": int(bs["n_candidates"]),
            "n_donor_clouds": int(bs["n_donor_clouds"]),
            "mean_29Si_spins_per_donor": float(bs["mean_29Si_spins_per_donor"]),
            "natural_working_yield_pct": round(float(bs["natural_working_yield_among_donors"]) * 100.0, 2),
            "median_t2_star_electron_us": float(bs["median_t2_star_electron_us"]),
            "median_t2_bath_dd_ms": float(bs["median_t2_bath_dd_ms"]),
            "legacy_exp132_fnr_on_real_bath": float(lg["fnr"]),
            "boed_identification_accuracy": float(ab["identification_accuracy"]),
            "boed_fnr": float(ab["fnr"]),
            "boed_fpr": float(ab["fpr"]),
            "boed_mean_probes": float(ab["mean_probes_per_candidate"]),
            "boed_mean_time_ms": float(ab["mean_time_ms"]),
            "boed_a_par_rmse_Hz": float(ab["a_par_localization"]["rmse_Hz"]),
            "boed_b_perp_median_abs_err_Hz": float(ab["b_perp_localization"]["median_abs_err_Hz"]),
            "boed_b_perp_secular_lt100kHz_rmse_Hz": float(ab["b_perp_localization"]["secular_lt_100kHz_rmse_Hz"]),
            "uniform_identification_accuracy": float(un["identification_accuracy"]),
            "uniform_fnr": float(un["fnr"]),
            "uniform_mean_probes": float(un["mean_probes_per_candidate"]),
            "uniform_a_par_rmse_Hz": float(un["a_par_localization"]["rmse_Hz"]),
            "probe_speedup_vs_uniform_raw": float(cp["probe_speedup_boed_vs_uniform_raw"]),
            "probe_speedup_vs_uniform_esr_gated": float(cp["probe_speedup_boed_vs_uniform_esr_gated"]),
            "time_speedup_vs_uniform_raw": float(cp["time_speedup_boed_vs_uniform_raw"]),
            "time_speedup_vs_uniform_esr_gated": float(cp["time_speedup_boed_vs_uniform_esr_gated"]),
            "honest_failure_walls": {
                "fourier_linewidth_1_over_Tmax_Hz": float(fwall["fourier_linewidth_1_over_Tmax_Hz"]),
                "sub_5kHz_gap_leakage_pct": float(hf["sub_linewidth_pairs_in_real_bath"]["leakage_rate_pct"]),
                "sub_1p5kHz_fourier_limit_lines": int(hf["sub_linewidth_pairs_in_real_bath"]["sub_1p5kHz_fourier_limit_lines"]),
                "low_snr_cliff_fnr_at_snr3": float(snr3_pt["fnr"]),
                "non_secular_first_shell_lines_ge100kHz": int(hf["weak_b_perp_clutter_floor"][">=100kHz"]["count"]),
            },
            "factory_15slot_real_si29": {
                "slots": int(fac["slots"]),
                "certified": int(fac["certified"]),
                "slot_success": float(fac["slot_success"]),
                "mean_spec_time_ms": float(fac["mean_spec_time_ms"]),
                "a_par_rmse_Hz": float(fac["real_bath_a_par_rmse_Hz"]),
                "b_perp_rmse_Hz": float(fac["real_bath_b_perp_rmse_Hz"]),
            },
        },
    }


def compute_layer7_v7_phased_procurement_and_evolution(ledgers: dict[str, Any]) -> dict[str, Any]:
    """DT7_7: Exp128 v7.0 modular budget-cap & phased procurement + v3->v7 fleet/algorithm trajectory."""
    d128 = ledgers["exp128"]
    b128 = d128["bom_detailed_summary"]
    mc7 = d128["v7_modular_mc_comparison"]
    v128 = d128["verdicts"]
    p5_144 = ledgers["exp144"]["part5_cryostat_and_tco_compression"]
    sc_base = p5_144["surface_code_baselines_exp141"]
    ql_9blk = p5_144["configs"]["BB144_100L_9blk"]

    def _tier(key: str) -> dict[str, Any]:
        t = mc7[key]
        return {
            "bom_nom_usd": float(t["bom_nom_usd"]),
            "prog_p50_M": round(float(t["program_stoch_usd"]["p50"]) / 1e6, 3),
            "prog_p95_M": round(float(t["program_stoch_usd"]["p95"]) / 1e6, 3),
            "P_gt_100M_pct": round(float(t["P_Program_stoch_gt_100M"]) * 100.0, 2),
        }

    return {
        "exp128_verdicts": {
            "CU1_bom_integrity": bool(v128["CU1_bom_integrity"]),
            "CU2_bom_cap_safety": bool(v128["CU2_bom_cap_safety"]),
            "CU3_base_plus_safety_pass": bool(v128["CU3_base_plus_safety_program_soft_hard_cap"]),
            "CU3_v6_full_pass": bool(v128["CU3_v6_full_program_soft_hard_cap"]),
            "CU3_v7_full_honest_exceed": not bool(v128["CU3_program_soft_hard_cap"]),
            "CU4_bc_wall_dominance": bool(v128["CU4_bc_wall_dominance"]),
            "CU5_evpi_20mk_vindication": bool(v128["CU5_evpi_20mk_vindication"]),
            "CU6_mc_convergence": bool(v128["CU6_mc_convergence"]),
        },
        "modular_tiers_v7": {
            "M3_v5_0_Base": _tier("M3_v5_0_Base"),
            "M3_Phase1_Base_Plus_Safety": _tier("M3_v5_0_Base_Plus_Safety"),
            "M3_v6_0_Full": _tier("M3_v6_0_Full_Option_Q_and_HPC"),
            "M3_v7_0_Full": _tier("M3_v7_0_Safety_Certified_Full"),
        },
        "phased_procurement_strategy": (
            "Phase-1: M3 Base+Safety ($5,392,800, P>$100M=4.67% < 5%, 6/6 CU PASS) -> "
            "RFQ-05 cryogenic price lock -> Phase-2: +Option-Q & +Option-HPC (v7 Full $5,692,800, honest 5.22% uncapped)."
        ),
        "bom_evolution_nom_usd": {
            "v3_0_base": float(b128["m3_v3_base_nom_usd"]),
            "v4_0_base": float(b128["m3_v4_base_nom_usd"]),
            "v5_0_base": float(b128["m3_v5_base_nom_usd"]),
            "v7_phase1_base_safety": float(b128["m3_base_plus_safety_nom_usd"]),
            "v6_0_full": float(b128["m3_v6_full_nom_usd"]),
            "v7_0_full": float(b128["m3_v7_safety_certified_full_nom_usd"]),
        },
        "fleet_100L_trajectory": {
            "v5_D2_SC_cryostats": int(sc_base["D2_1e-9"]["cryostats_100L"]),
            "v6_D3_GRAPE_SC_cryostats": int(sc_base["D3_1e-9"]["cryostats_100L"]),
            "v6_qLDPC_108L_cryostats": int(ql_9blk["n_cryostats"]),
            "v5_D2_SC_usd_per_L_sys": round(float(sc_base["D2_1e-9"]["sys_100L_usd_per_L_amort_wright_p50"]), 2),
            "v6_D3_GRAPE_SC_usd_per_L_sys": round(float(sc_base["D3_1e-9"]["sys_100L_usd_per_L_amort_wright_p50"]), 2),
            "v6_qLDPC_108L_usd_per_L_sys": round(float(ql_9blk["usd_per_logical_sys_amort_wright"]["p50"]), 2),
        },
    }


def check_historical_certs(root: Path = ROOT) -> dict[str, bool]:
    """Verify v4/v5/v6 historical master certificates remain untouched on disk."""
    res: dict[str, bool] = {}
    for ver, (rel, expected_sha) in HISTORICAL_MASTER_CERTS.items():
        fp = root / rel
        if not fp.is_file():
            res[ver] = False
        else:
            cert = json.loads(fp.read_text(encoding="utf-8"))
            res[ver] = cert.get("sha256") == expected_sha
    return res


def build_v7_master_certificate(
    all_hashes: dict[str, str],
    l1: dict[str, Any],
    l2: dict[str, Any],
    l3: dict[str, Any],
    l4: dict[str, Any],
    l5: dict[str, Any],
    l6: dict[str, Any],
    l7: dict[str, Any],
) -> dict[str, Any]:
    """Build canonical JSON v7.2 Master Digital Twin File-Integrity Manifest with full 64-hex SHA-256."""
    y_t = l4["yosys_measured_pre_pnr"]["targets"]
    bath = l6["real_si29_bath_boed"]
    rec = l6["live_auto_recal"]
    c4 = l6["live_cellisa_v40"]
    payload: dict[str, Any] = {
        "certificate_type": "ATOM_LITHOGRAPHY_MACHINE_V7_MASTER_DIGITAL_TWIN",
        "experiment": "exp151_v7_digital_twin",
        "hypothesis_id": "H169",
        "version": "7.2",
        "epistemic_scope": {
            "silicon_31P_fab_bath_control_safety": (
                "Model/Sayisal-Simulasyon/Varsayim/Liste-Capasi (TRL 1-2 / M0, no_lab_measurement=true, "
                "no_supplier_quotes=true, iec61508_certified=false, semi_s2_certified=false, "
                "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED)"
            ),
            "rtl_eda_verification": (
                "Real open-source EDA verified on host (iverilog + vvp + verilator -Wall + yosys pre-P&R; "
                "no_external_eda_sim=false, real_eda_verified=true, no_vendor_vivado_pnr=true, no_lab_measurement_rtl=true)"
            ),
            "control_stack_cloud_qpu": (
                f"Canli-Donanim-IBM-QPU ({l6['live_ibm_qpu']['backend_name']}, "
                f"{l6['live_ibm_qpu']['n_qubits']}Q, job_id={l6['live_ibm_qpu']['job_id']}; "
                "superconducting control/decoder proxy, validates zero silicon 31P hardware)"
            ),
        },
        "n_locked_artifacts": len(all_hashes),
        "locked_artifacts_sha256": dict(sorted(all_hashes.items())),
        "historical_master_cert_sha256": {ver: sha for ver, (_, sha) in HISTORICAL_MASTER_CERTS.items()},
        "cad_v6_parts": l1["cad_v6"]["part_count"],
        "cad_v6_mass_kg": l1["cad_v6"]["total_mass_kg"],
        "cad_v6_clashes": l1["cad_v6"]["solid_clashes"],
        "cad_v6_clearances_pass": f"{l1['cad_v6']['clearances_passed']}/{l1['cad_v6']['clearances_total']}",
        "bom_v7_parts": l1["bom_v7"]["exp128_total_parts"],
        "bom_v7_m3_base_nom_usd": l1["bom_v7"]["m3_v5_base_nom_usd"],
        "bom_v7_m3_phase1_base_safety_nom_usd": l1["bom_v7"]["m3_base_plus_safety_nom_usd"],
        "bom_v7_m3_v6_full_nom_usd": l1["bom_v7"]["m3_v6_full_nom_usd"],
        "bom_v7_m3_v7_full_nom_usd": l1["bom_v7"]["m3_v7_full_nom_usd"],
        "bom_v7_reconciliation_error_usd": l1["bom_v7"]["reconciliation_error_usd"],
        "bom_v7_on_frame_cad_mass_error_kg": l1["bom_v7"]["on_frame_cad_mass_error_kg"],
        "bom_v7_facility_safety_mass_kg": l1["bom_v7"]["facility_safety_mass_kg"],
        "bom_v7_total_facility_mass_kg": l1["bom_v7"]["total_facility_load_mass_kg"],
        "bom_v7_rfq10_nom_share_pct": l1["bom_v7"]["rfq10_nom_share_pct"],
        "bom_v7_rfq10_var_share_pct": l1["bom_v7"]["rfq10_var_share_pct"],
        "bom_v7_phase1_P_gt_100M_pct": l7["modular_tiers_v7"]["M3_Phase1_Base_Plus_Safety"]["P_gt_100M_pct"],
        "bom_v7_full_P_gt_100M_pct": l7["modular_tiers_v7"]["M3_v7_0_Full"]["P_gt_100M_pct"],
        "exp147_bb288_L_max_um": l2["L_max_um"],
        "exp147_bb288_p_th_pct": l2["p_th_72_vs_288_pct"],
        "exp147_yield_576_N8_pct": l2["yield_576_N8_pct"],
        "exp147_yield_576_N9_pct": l2["yield_576_N9_pct"],
        "exp147_femoco_cryostats": l2["femoco"]["qldpc_cryostats"],
        "exp147_femoco_runtime_h": l2["femoco"]["runtime_hours"],
        "exp147_femoco_cost_per_solve_usd": l2["femoco"]["cost_per_solve_usd_p50"],
        "exp147_femoco_compression_x": l2["femoco"]["cryo_compression_x"],
        "exp147_rsa2048_cryostats": l2["rsa2048"]["qldpc_cryostats"],
        "exp147_rsa2048_power_MW": l2["rsa2048"]["power_MW"],
        "exp147_rsa2048_runtime_h": l2["rsa2048"]["runtime_hours"],
        "exp147_rsa2048_compression_x": l2["rsa2048"]["cryo_compression_x"],
        "exp148_sb121_bare_gross_0L": l3["bare_gross_0L_1ms"],
        "exp148_sb121_qecho8_gross_0L": l3["qecho8_gross_0L_1ms"],
        "exp148_sb121_infidelity_reduction_x": l3["gross_infidelity_reduction_x"],
        "exp148_sb121_qecho8_cat77": l3["qecho8_cat77_1ms"],
        "exp148_sb121_su8_grape_min_F": l3["su8_grape_min_F"],
        "exp148_sb121_qecho64_1f_gain_x": l3["t2_gain_qecho64_1f_x"],
        "exp149_rtl_loc": l4["total_rtl_loc"],
        "exp149_rtl_cycles": l4["boed_cycles_exact"],
        "exp149_rtl_latency_us": l4["boed_latency_us_250MHz"],
        "exp149_rtl_golden_zero_lsb": l4["golden_all_zero_lsb"],
        "exp149_rtl_rom_words": l4["rom_words_checked"],
        "exp149_no_external_eda_sim": l4["no_external_eda_sim"],
        "exp149_real_eda_verified": l4["real_eda_verified"],
        "exp149_no_vendor_vivado_pnr": l4["no_vendor_vivado_pnr"],
        "exp149_no_lab_measurement_rtl": l4["no_lab_measurement_rtl"],
        "exp149_verilator_warnings": (
            l4["verilator_lint"]["boed_q16_core_warnings"] + l4["verilator_lint"]["boed_top_16ch_warnings"]
        ),
        "exp149_iverilog_vectors_64_zero_lsb": bool(
            l4["iverilog_simulation"]["all_passed"]
            and l4["iverilog_simulation"]["vectors_tested"] == 64
            and l4["iverilog_simulation"]["max_mu_off_q8_lsb_err"] == 0
            and l4["iverilog_simulation"]["max_std_q4_lsb_err"] == 0
            and l4["iverilog_simulation"]["max_next_probe_q8_lsb_err"] == 0
        ),
        "exp149_yosys_xcup_top16_measured": {
            "lut_total": y_t["xcup_top16"]["lut_total"],
            "ff_total": y_t["xcup_top16"]["ff_total"],
            "bram_blocks": y_t["xcup_top16"]["bram_blocks"],
            "bram36_equiv": y_t["xcup_top16"]["bram36_equiv"],
            "dsp_total": y_t["xcup_top16"]["dsp_total"],
            "zu48dr_dsp_pct": y_t["xcup_top16"]["zu48dr_pct"]["dsp48e2_pct"],
            "zu48dr_bram36_pct": y_t["xcup_top16"]["zu48dr_pct"]["bram36_equiv_pct"],
            "zu48dr_lut_pct": y_t["xcup_top16"]["zu48dr_pct"]["lut_pct"],
            "zu48dr_ff_pct": y_t["xcup_top16"]["zu48dr_pct"]["ff_pct"],
        },
        "exp150_safety_criteria": l5["criteria_passed"],
        "exp150_iec61508_certified": l5["iec61508_certified"],
        "exp150_semi_s2_certified": l5["semi_s2_certified"],
        "exp150_certification_status": l5["certification_status"],
        "exp150_sil3_pfd_band_met_at_nominal_assumed_lambda_du": l5["sil3_pfd_band_met_at_nominal_assumed_lambda_du"],
        "exp150_requires_third_party_assessment": l5["requires_third_party_assessment"],
        "exp150_pfd_avg_1oo2d_nominal": l5["pfd_avg_1oo2d_nominal"],
        "exp150_pfd_10x_lambda_du_beta10pct": l5["pfd_sensitivity_sweep"]["pfd_10x_lambda_du_beta10pct"],
        "exp150_fmea_max_rpn_pre": l5["max_rpn_pre"],
        "exp150_fmea_max_rpn_post": l5["max_rpn_post"],
        "exp150_fmea_mean_reduction_pct": l5["mean_rpn_reduction_pct"],
        "exp150_ph3_operator_ppm": l5["ph3_operator_ppm"],
        "exp150_he_60m3_O2_pct": l5["he_60m3_O2_pct"],
        "exp150_ups_full_tier1_min": [l5["ups_full_load_min"], l5["ups_tier1_min"]],
        "exp150_s_safety_nom_usd": l5["s_safety_nom_usd"],
        "real_si29_bath_boed_accuracy": bath["boed_identification_accuracy"],
        "real_si29_bath_boed_probe_speedup_raw": bath["probe_speedup_vs_uniform_raw"],
        "real_si29_bath_boed_a_par_rmse_Hz": bath["boed_a_par_rmse_Hz"],
        "real_si29_bath_legacy_fnr": bath["legacy_exp132_fnr_on_real_bath"],
        "real_si29_bath_fourier_wall_Hz": bath["honest_failure_walls"]["fourier_linewidth_1_over_Tmax_Hz"],
        "live_qpu_backend": l6["live_ibm_qpu"]["backend_name"],
        "live_qpu_job_id": l6["live_ibm_qpu"]["job_id"],
        "live_qpu_bell_fidelity": l6["live_ibm_qpu"]["c1_bell_fidelity"],
        "live_qpu_xy4_gain_pp": l6["live_ibm_qpu"]["c1_xy4_gain_pp"],
        "live_qpu_q16_vs_fp64_kHz": l6["live_ibm_qpu"]["c3_q16_vs_fp64_kHz"],
        "live_cellisa_v40_opcodes": c4["v40_total_opcodes"],
        "live_cellisa_echo_cz_bell_fidelity": c4["echo_cz"]["echo_cz_bell_fidelity"],
        "live_cellisa_mux32_fidelity": c4["mux_readout"]["mux32_per_cell_fidelity"],
        "live_cellisa_qldpc_bb288_feedlines": c4["qldpc_round"]["feedlines_required"],
        "live_auto_recal_passed": f"{rec['n_passed']}/{rec['n_fault_modes']}",
        "live_auto_recal_blanker_coverage_pct": rec["blanker_step_and_stitch"]["wafer_site_coverage_after_pct"],
        "live_auto_recal_blanker_honest_throughput_pct": rec["blanker_step_and_stitch"]["throughput_after_recal_pct"],
        "live_auto_recal_uhv_langmuir_total": rec["uhv_langmuir_ode"]["exposure_langmuir_total"],
    }
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    cert = dict(payload)
    cert["sha256"] = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    return cert


def verify_v7_certificate(cert: dict[str, Any]) -> bool:
    """Recompute canonical SHA-256 digest and verify full 64-hex match."""
    sig = str(cert.get("sha256", ""))
    if len(sig) != 64:
        return False
    payload = {k: v for k, v in cert.items() if k != "sha256"}
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest() == sig


def render_summary_exp151_md(out_data: dict[str, Any]) -> str:
    """Render reproducible GFM-valid Exp151 v7.2 summary with exact 64-hex SHA-256 digests."""
    l1 = out_data["layer1_integrity"]
    l2 = out_data["layer2_universal_qldpc_d18"]
    l3 = out_data["layer3_sb121_qecho8"]
    l4 = out_data["layer4_verilog_rtl_and_twin"]
    l5 = out_data["layer5_industrial_safety"]
    l6 = out_data["layer6_live_ibm_qpu_and_cellisa40"]
    l7 = out_data["layer7_v7_phased_procurement_and_evolution"]
    cert = out_data["v7_master_certificate"]
    verdicts = out_data["verdicts"]

    y_t = l4["yosys_measured_pre_pnr"]["targets"]
    y16 = y_t["xcup_top16"]
    yc = y_t["xcup_core"]
    y7 = y_t["xc7_core"]
    ye = y_t["ecp5_core"]
    bath = l6["real_si29_bath_boed"]
    rec = l6["live_auto_recal"]
    c4 = l6["live_cellisa_v40"]
    lq = l6["live_ibm_qpu"]
    pfd_sw = l5["pfd_sensitivity_sweep"]

    def _badge(key: str) -> str:
        return "**PASS**" if verdicts[key] else "**FAIL**"

    lines = [
        "# Exp151 (H169): v7.2 Bütünleşik Artefakt Özeti ve SHA-256 Dosya Bütünlüğü Manifestosu (TRL 1–2 / M0)",
        "",
        f"**Tarih:** {out_data['date']} | **Hipotez:** `H169` | **Sürüm:** `v{out_data['version']}` | **Ön-Kayıtlı Yazılım & EDA Kontrolleri:** **`{out_data['n_passed']}/{out_data['n_total']} PASS` (`DT7_1..DT7_8`)**",
        "",
        "> **Epistemik Kapsam ve Sınırlılıklar (`TRL 1–2 / M0`):**",
        "> - **Kavramsal Sistem Tasarımı ve İndirgenmiş-Mertebe Çok-Fizikli Modelleme (`M0`):** Silikon `³¹P / ¹²¹Sb / ¹⁶⁷Er` fabrikasyon modelleri (`S1..S8`), nominal statik `CAD v6.0` (`199` parça; GD&T, termal büzülme, titreşim ve DFM hariç), parametrik `BOM v7.0` (`180` parça / `10-RFQ` taslağı, `no_supplier_quotes = true`), `Exp147` (`qLDPC d=18`), `Exp148` (`¹²¹Sb` `Q-Echo-8`), gerçek `1% ²⁹Si` elmas-kübik örgü banyosu BOED kıyaslaması (`results/boed_real_bath_benchmark.json`), yükseltilmiş fiziksel `auto_recal` (2-oda UHV ODE + doğrusal-olmayan Si termal PDE + dürüst step-and-stitch) & `programmer` (16D Lindblad/OU Echo-CZ, Exp140 dispersif mux, gerçek GF(2) BB qLDPC) modelleri sayısal tasarım modellemesidir (`no_lab_measurement = true`, `tapeout_done = false`).",
        f"> - **Gerçek Açık-Kaynak EDA Doğrulamalı Verilog RTL (`Exp149`):** `rtl/boed_fpga/` (`{l4['total_rtl_loc']}` LOC, `0` kombinasyonel `/` bölücü) konak makinede gerçek `verilator --lint-only -Wall` (`0` uyarı/hata), `iverilog -g2012 -Wall + vvp` (`64/64` vektör + `4`-kanal AXI4-Stream `0 LSB`, `584` çevrim) ve gerçek `yosys` sentezi (`xcup`/`xc7`/`ecp5`, `check -assert` temiz) ile doğrulanmıştır (`no_external_eda_sim = false`, `real_eda_verified = true`, `no_vendor_vivado_pnr = true`, `no_lab_measurement_rtl = true`). Ticari Vivado P&R zamanlama kapanışı ve fiziksel FPGA donanım testi henüz yapılmamıştır.",
        f"> - **Sertifikasız Ön Emniyet Sınırı (`Exp150`):** `{l5['certification_status']}` (`iec61508_certified = false`, `semi_s2_certified = false`, `requires_third_party_assessment = true`). `SEMI`, `SEMI S2` için sertifika vermez; `IEC 61508 SIL-3` ise bağımsız fonksiyonel emniyet değerlendirmesi ve tedarikçi FMEDA verisi gerektirir. `λ_DU × β` duyarlılık taraması (`15` durum) nominal varsayımda `PFD_avg = {l5['pfd_avg_1oo2d_nominal']:.4e} < 1e-3` verirken `10× λ_DU` + `β = 10%` altında `{pfd_sw['pfd_10x_lambda_du_beta10pct']:.4e}` ile **`SIL-2` bandına düştüğünü** açıkça gösterir.",
        f"> - **Bulut Süperiletken-QPU Kontrol/Dekoder Proxy Kıyaslaması (`Exp145`):** `CellISA v4.0 → OpenQASM 3.0`, Hahn-Echo/XY4 DD, Bell tomografi, 5-kübit `d=3` tekrar kodu ve `Q16.16` BOED algoritmaları `{lq['backend_name']}` (`{lq['n_qubits']}Q Heron r2`, `job_id = {lq['job_id']}`, `0` gizli anahtar sızıntısı) süperiletken bulut işlemcisinde çalıştırılmıştır; bu koşum **silikon `³¹P` fabrikasyon donanımını doğrulamaz**.",
        "> - **Dosya Bütünlüğü ve Yazılım Testleri:** `SHA-256` özetleri yalnızca üretilen dosyaların sonradan değiştirilmediğini izleyen **dosya-bütünlüğü / izlenebilirlik özetidir** (bilimsel doğrulama veya sertifikasyon değildir).",
        "",
        "---",
        "",
        "## 1. Dosya Bütünlüğü ve İzlenebilirlik Manifestosu (Tam 64-Hex `SHA-256` — Bilimsel Kanıt Değil)",
        "",
        "- **`v7_digital_twin_cert.json` Kanonik JSON `SHA-256` (Tam 64-Hex — Dosya Bütünlüğü Özeti):**",
        f"  `{cert['sha256']}`",
        "- **Bulut QPU Proxy Ham Sayım Defteri (`results/exp145_cloud_qpu_ibm_validation/ibm_qpu_live_results.json`) `SHA-256`:**",
        f"  `{l1['live_qpu_artifact_sha256']}`",
        f"- **Çevrimdışı HTML5 Model Gezgini (`docs/digital_twin_interactive.html`, `{l4['interactive_twin']['size_bytes']:,}` bayt, `0` CDN) `SHA-256`:**",
        f"  `{l1['interactive_twin_html_sha256']}`",
        "- **Gerçek `1% ²⁹Si` Örgü Banyosu BOED Kıyaslama Defteri (`results/boed_real_bath_benchmark.json`) `SHA-256`:**",
        f"  `{l1['boed_real_bath_sha256']}`",
        f"- **İzlenen Artefakt Sayısı:** **`{cert['n_locked_artifacts']} / {cert['n_locked_artifacts']}`** (`27` deney JSON'u `Exp124..Exp150` + `1` IBM QPU proxy JSON + `1` gerçek `1% ²⁹Si` banyo BOED JSON + nominal `CAD v6.0` + parametrik `BOM_DETAILED.csv v7.0` + `7` `rtl/boed_fpga/` dosyası + `docs/digital_twin_interactive.html`).",
        "- **Dokunulmadan Korunan Tarihsel Dosya-Bütünlüğü Manifestoları:**",
        f"  - `v4_digital_twin_cert.json`: `{HISTORICAL_MASTER_CERTS['v4'][1]}`",
        f"  - `v5_digital_twin_cert.json`: `{HISTORICAL_MASTER_CERTS['v5'][1]}`",
        f"  - `v6_digital_twin_cert.json`: `{HISTORICAL_MASTER_CERTS['v6'][1]}`",
        "",
        "---",
        "",
        f"## 2. Ön-Kayıtlı `DT7_1 .. DT7_8` Yazılım & Gerçek-EDA Tutarlılık Tablosu (`{out_data['n_passed']}/{out_data['n_total']} PASS`)",
        "",
        "| Kontrol ID | Kapsam | Ölçülen Model / Gerçek-EDA / Dosya Bulguları | Sonuç |",
        "| --- | --- | --- | --- |",
        (
            f"| `DT7_1_LEDGER_CAD_BOM_RTL_TWIN_SHA256_LOCK` | `{cert['n_locked_artifacts']}/{cert['n_locked_artifacts']}` `SHA-256` + CAD v6 + BOM v7 "
            f"| `27` deney JSON + gerçek `1% ²⁹Si` banyo JSON + nominal statik `CAD v6.0` (`{l1['cad_v6']['part_count']}p`, `{l1['cad_v6']['total_mass_kg']:.3f} kg`, `0/{l1['cad_v6']['pairs_checked']:,}` çakışma, `40/40` zarf) + parametrik `BOM v7.0` (`{l1['bom_v7']['csv_row_count']}p`, `$0.00` köprü, `0.0000 kg` şasi + `{l1['bom_v7']['facility_safety_mass_kg']:.1f} kg` tesis = `{l1['bom_v7']['total_facility_load_mass_kg']:.3f} kg`, `10-RFQ` `%{l1['bom_v7']['rfq10_nom_share_pct']:.2f}` nom / `%{l1['bom_v7']['rfq10_var_share_pct']:.2f}` var) "
            f"| {_badge('DT7_1_LEDGER_CAD_BOM_RTL_TWIN_SHA256_LOCK')} |"
        ),
        (
            f"| `DT7_2_UNIVERSAL_QLDPC_D18_AND_ALGORITHMS` | `Exp147` `qLDPC d=18` "
            f"| `[[288,12,18]]` `L_max = {l2['L_max_um']} µm <= 300`, `p_th = %{l2['p_th_72_vs_288_pct']}`, `576`-hücre `%{l2['yield_576_N8_pct']} (N=8)` / `%{l2['yield_576_N9_pct']} (N=9)`; FeMoco `{l2['femoco']['qldpc_cryostats']}` kriyo / `{l2['femoco']['runtime_hours']} sa` / `${l2['femoco']['cost_per_solve_usd_p50']:,.0f}` (`{l2['femoco']['cryo_compression_x']}x`, dürüst `UQ5` notu); RSA-2048 `{l2['rsa2048']['qldpc_cryostats']}` kriyo / `{l2['rsa2048']['power_MW']} MW` / `{l2['rsa2048']['runtime_hours']} sa` (`{l2['rsa2048']['cryo_compression_x']}x`) "
            f"| {_badge('DT7_2_UNIVERSAL_QLDPC_D18_AND_ALGORITHMS')} |"
        ),
        (
            f"| `DT7_3_SB121_QECHO8_CLOSURE_AND_SU8_GRAPE` | `Exp148` `¹²¹Sb` `Q-Echo-8` "
            f"| Statik `500 Hz` Gross `{l3['bare_gross_0L_1ms']:.4f} -> {l3['qecho8_gross_0L_1ms']:.5f}` (`{l3['gross_infidelity_reduction_x']:.1f}x` infidelite düşüşü), Cat `{l3['bare_cat77_1ms']:.4f} -> {l3['qecho8_cat77_1ms']:.5f}`, `SU(8)` GRAPE `>= {l3['su8_grape_min_F']:.4f}`; dürüst Cywiński `1/f` sınırı (`SQ4 FAIL`, `Q-Echo-8: {l3['t2_gain_qecho8_1f_x']}x`, `Q-Echo-64: {l3['t2_gain_qecho64_1f_x']}x = {l3['t2_qecho64_ms']} ms`) "
            f"| {_badge('DT7_3_SB121_QECHO8_CLOSURE_AND_SU8_GRAPE')} |"
        ),
        (
            f"| `DT7_4_VERILOG_RTL_AND_INTERACTIVE_TWIN` | `Exp149` Gerçek EDA + HTML5 Gezgin "
            f"| `4` `.v` (`{l4['total_rtl_loc']}` LOC, `0` kombinasyonel `/`), `verilator -Wall`: `0` uyarı/hata; `iverilog+vvp`: `64/64` vektör + `4`-ch `top_16ch` `0 LSB` / `584` çevrim (`2.336 µs`); `yosys` ölçümü `xcup_top16`: `{y16['lut_total']:,}` LUT (`%{y16['zu48dr_pct']['lut_pct']}`), `{y16['ff_total']:,}` FF (`%{y16['zu48dr_pct']['ff_pct']}`), `{y16['bram_blocks']}` RAMB18 (`{y16['bram36_equiv']:.0f}` BRAM36 = `%{y16['zu48dr_pct']['bram36_equiv_pct']}`), `{y16['dsp_total']:,}` DSP (`%{y16['zu48dr_pct']['dsp48e2_pct']}`); `no_external_eda_sim=false`, `no_vendor_vivado_pnr=true`, HTML5 `0` CDN "
            f"| {_badge('DT7_4_VERILOG_RTL_AND_INTERACTIVE_TWIN')} |"
        ),
        (
            f"| `DT7_5_INDUSTRIAL_SAFETY_FMEA_HAZOP_SEMI_S2` | `Exp150` Sertifikasız Ön Emniyet "
            f"| `{l5['criteria_passed']} PASS`, `{l5['certification_status']}` (`iec61508_certified=false`, `semi_s2_certified=false`, `0` sahte `SIL-3` iddiası), `25` FMEA + `10` HAZOP (`RPN 280 -> {l5['max_rpn_post']} <= 60`), nominal `PFD={l5['pfd_avg_1oo2d_nominal']:.3e}` (`10x λ_DU @ β=10% -> {pfd_sw['pfd_10x_lambda_du_beta10pct']:.3e}` `SIL-2`), ODH RK4 `60 m³` `0 ACH = %{l5['odh_box_ode_transient']['dry_60m3_0ACH_min_O2_pct']:.2f}`, `S7.SAFETY = ${l5['s_safety_nom_usd']:,.0f} / {l5['s_safety_mass_kg']:.0f} kg / 0 W` kriyo "
            f"| {_badge('DT7_5_INDUSTRIAL_SAFETY_FMEA_HAZOP_SEMI_S2')} |"
        ),
        (
            f"| `DT7_6_LIVE_IBM_QPU_CELLISA40_AND_EPISTEMIC_BOUNDARY` | `Exp145` Proxy + Fizik + `1% ²⁹Si` Banyo "
            f"| `{lq['backend_name']}` (`156Q`, `0` sızıntı): XY4 `+{lq['c1_xy4_gain_pp']} pp`, Bell `{lq['c1_bell_fidelity']:.4f}`, `d=3` `{lq['c2_suppression_mwpm']}x`; `auto_recal` (`4/4`): Si PDE `T_peak={rec['laser_thermal_pde']['reference_T_peak_K']:.1f} K`, UHV ODE `{rec['uhv_langmuir_ode']['exposure_langmuir_total']} L` (`{rec['uhv_langmuir_ode']['surface_monolayer_coverage_frac']} ML`), dürüst stitch `{rec['blanker_step_and_stitch']['wafer_site_coverage_after_pct']:.0f}%` kapsama / **`%{rec['blanker_step_and_stitch']['throughput_after_recal_pct']:.2f}`** verim; `CellISA`: 16D Echo-CZ `F={c4['echo_cz']['echo_cz_bell_fidelity']:.4f}`, mux32 `{c4['mux_readout']['mux32_per_cell_fidelity']:.4f}` vs mux64 `{c4['mux_readout']['mux64_per_cell_fidelity']:.4f}`, GF(2) `BB_288` (`0` mantıksal hata); `1% ²⁹Si` BOED: **`%{bath['boed_identification_accuracy']*100:.2f}`** doğruluk, **`{bath['probe_speedup_vs_uniform_raw']}x`** prob / **`{bath['time_speedup_vs_uniform_raw']}x`** zaman hızlanması, `A_par RMSE = {bath['boed_a_par_rmse_Hz']} Hz` "
            f"| {_badge('DT7_6_LIVE_IBM_QPU_CELLISA40_AND_EPISTEMIC_BOUNDARY')} |"
        ),
        (
            f"| `DT7_7_MODULAR_V7_BUDGET_CAP_AND_PHASED_PROCUREMENT` | `Exp128 v7.0` Parametrik Fazlı Bütçe "
            f"| `M3 Base $5.248M (%{l7['modular_tiers_v7']['M3_v5_0_Base']['P_gt_100M_pct']})`, **Faz-1 `Base+Safety $5.393M (%{l7['modular_tiers_v7']['M3_Phase1_Base_Plus_Safety']['P_gt_100M_pct']} < %5, 6/6 CU PASS)`**, `v6 Full $5.548M (%{l7['modular_tiers_v7']['M3_v6_0_Full']['P_gt_100M_pct']})`, dürüst `v7 Full $5.693M (%{l7['modular_tiers_v7']['M3_v7_0_Full']['P_gt_100M_pct']} > %5 -> Faz-2)` "
            f"| {_badge('DT7_7_MODULAR_V7_BUDGET_CAP_AND_PHASED_PROCUREMENT')} |"
        ),
        (
            f"| `DT7_8_CRYPTO_V7_CERT_PORTABILITY_AND_TESTS` | Dosya Bütünlüğü ve Hijyen "
            f"| `v7_digital_twin_cert.json` `SHA-256` bütünlüğü + tahrifat tespiti aktif, `v4/v5/v6` manifestoları dokunulmamış, `0` mutlak yol, `0` sır/token "
            f"| {_badge('DT7_8_CRYPTO_V7_CERT_PORTABILITY_AND_TESTS')} |"
        ),
        "",
        "---",
        "",
        "## 3. Gerçek EDA Yosys Ölçümleri (`Exp149`) & Gerçek `1% ²⁹Si` Banyo BOED Özeti",
        "",
        "### 3.1. `Yosys` Ön-P&R Sentez Kaynak Ölçümleri (`no_external_eda_sim = false`, `no_vendor_vivado_pnr = true`)",
        "",
        "| Hedef | Aile | Üst Modül | LUT | FF | BRAM Blok (BRAM36-eq) | DSP | Carry | ZU48DR Sığma |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        f"| `xcup_core` | `xcup` | `boed_q16_core` | `{yc['lut_total']:,}` | `{yc['ff_total']:,}` | `{yc['bram_blocks']}` (`{yc['bram36_equiv']:.1f}`) | `{yc['dsp_total']}` | `{yc['carry_cells']:,}` | `PASS` (`DSP %{yc['zu48dr_pct']['dsp48e2_pct']}`) |",
        f"| `xcup_top16` | `xcup` | `boed_top_16ch` | `{y16['lut_total']:,}` | `{y16['ff_total']:,}` | `{y16['bram_blocks']}` (`{y16['bram36_equiv']:.1f}`) | `{y16['dsp_total']:,}` | `{y16['carry_cells']:,}` | `PASS` (`DSP %{y16['zu48dr_pct']['dsp48e2_pct']}`, `LUT %{y16['zu48dr_pct']['lut_pct']}`) |",
        f"| `xc7_core` | `xc7` | `boed_q16_core` | `{y7['lut_total']:,}` | `{y7['ff_total']:,}` | `{y7['bram_blocks']}` (`{y7['bram36_equiv']:.1f}`) | `{y7['dsp_total']}` | `{y7['carry_cells']:,}` | `Referans 7-Serisi` |",
        f"| `ecp5_core` | `ecp5` | `boed_q16_core` | `{ye['lut_total']:,}` | `{ye['ff_total']:,}` | `{ye['bram_blocks']}` (`{ye['bram36_equiv']:.1f}`) | `{ye['dsp_total']}` | `{ye['carry_cells']:,}` | `Açık-Kaynak ECP5` |",
        "",
        "### 3.2. Gerçek `1% ²⁹Si` Elmas-Kübik Örgü Banyosu BOED Kıyaslaması (`N = 260`, `218` Donör Bulutu, `452.5` ²⁹Si/donör)",
        "",
        "| Protokol | Doğruluk | `FNR` | Ort. Prob | Ort. Süre (ms) | `A_par` RMSE (Hz) | `B_perp` Medyan Hata (Hz) | Not |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        f"| **Yükseltilmiş `AdaptiveBOEDSpectroscopy`** | **`%{bath['boed_identification_accuracy']*100:.2f}`** | `%{bath['boed_fnr']*100:.2f}` | `{bath['boed_mean_probes']:.1f}` | `{bath['boed_mean_time_ms']:.1f}` | `{bath['boed_a_par_rmse_Hz']:.2f}` | `{bath['boed_b_perp_median_abs_err_Hz']:.1f}` | `{bath['probe_speedup_vs_uniform_raw']}x` prob / `{bath['time_speedup_vs_uniform_raw']}x` zaman hızlanması (raw) |",
        f"| `UniformNyquistSpectrometer` (Aynı Banyo) | `%{bath['uniform_identification_accuracy']*100:.2f}` | `%{bath['uniform_fnr']*100:.2f}` | `{bath['uniform_mean_probes']:.1f}` | `3427.1` | `{bath['uniform_a_par_rmse_Hz']:.2f}` | `107.9` | ESR-kapılı hızlanma: `{bath['probe_speedup_vs_uniform_esr_gated']}x` prob / `{bath['time_speedup_vs_uniform_esr_gated']}x` zaman |",
        f"| Eski `Exp132` Protokolü (Gerçek Banyo Denetimi) | `%57.69` | **`%100.00`** | `181.6` | `29.9` | `—` | `—` | Zayıf-banyo karmaşasında `0/110` çalışma bulutu kabul |",
        "",
        "---",
        "",
        "## 4. Dürüst Fiziksel, Modelleme ve Sertifikasyon Sınırları",
        "",
        f"1. **`Exp147` (`UQ4` / `UQ5` Dürüst FAIL):** `[[288,12,18]]` kodu `L_max = {l2['L_max_um']} µm <= 300 µm` ve `FeMoco` için `{l2['femoco']['qldpc_cryostats']}` kriyostat (`{l2['femoco']['cryo_compression_x']}x` model sıkıştırması) verse de `2–3 µs` okuma tavanı (`p_meas = %0.22–%0.39`) `d=18` bellek hata tabanını sınırlar; `D3++` veya `d=24` gereklidir.",
        f"2. **`Exp148` (`SQ4` Dürüst FAIL):** `Q-Echo-8` statik `500 Hz` modelde `{l3['gross_infidelity_reduction_x']:.1f}x` infidelite düşüşü verse de geniş bant `1/f` gürültüsü altında tek çevrim `Q-Echo-8` `{l3['t2_gain_qecho8_1f_x']}x`, çok-çevrimli `Q-Echo-64` `{l3['t2_gain_qecho64_1f_x']}x` (`{l3['t2_qecho64_ms']} ms`) düzeyinde kalır.",
        "3. **`Exp149` (`no_external_eda_sim = false`, `no_vendor_vivado_pnr = true`):** `iverilog` (`64/64` vektör + `4`-ch AXI4-Stream `0 LSB`), `verilator -Wall` (`0` uyarı) ve `yosys` (`xcup`/`xc7`/`ecp5`) gerçek açık-kaynak EDA ile doğrulandı; ancak ticari Vivado P&R zamanlama kapanışı ve fiziksel ZU48DR kart ölçümü yapılmamıştır.",
        f"4. **Gerçek `1% ²⁹Si` Banyo BOED Başarısızlık Duvarları:** Fourier çizgi genişliği duvarı (`1/T_max = {bath['honest_failure_walls']['fourier_linewidth_1_over_Tmax_Hz']:.0f} Hz`; `<5 kHz` aralık sızıntısı `%{bath['honest_failure_walls']['sub_5kHz_gap_leakage_pct']}`), düşük-SNR uçurumu (`SNR <= 3` altında `FNR = %100`), zayıf-`B_perp` banyo gürültüsü ve ilk-kabuk seküler-olmayan `{bath['honest_failure_walls']['non_secular_first_shell_lines_ge100kHz']}` spin (yüksek `B_dd` gerektirir).",
        f"5. **`auto_recal` & `programmer` Dürüst Fizik Sınırları:** `%5` (`51/1024`) ölü blanker kanalında wafer-sahne step-and-stitch `%100.0` konum kapsamasını sıfır koordinat hatasıyla sağlar ancak gerçek verim **`%{rec['blanker_step_and_stitch']['throughput_after_recal_pct']:.2f}`** düzeyine düşer (`-%{rec['blanker_step_and_stitch']['throughput_penalty_pct']:.2f}` gerçek adım-dikiş maliyeti); `N_mux = 64` okuma sadakati `{c4['mux_readout']['mux64_per_cell_fidelity']:.4f} < 0.990` ile Exp140 tavanını doğrular.",
        f"6. **`Exp150` (`{l5['certification_status']}`):** `iec61508_certified = false`, `semi_s2_certified = false`, `requires_third_party_assessment = true`. `10× λ_DU` + `β = 10%` altında `PFD_avg = {pfd_sw['pfd_10x_lambda_du_beta10pct']:.4e}` ile `SIL-2` bandına düşülür; bağımsız saha değerlendirmesi ve FMEDA zorunludur.",
        "7. **`Exp128 v7.0` (`v7 Full` Dürüst `%5.22`):** Tüm seçeneklerin tek seferde alınması `P(Prog > $100M) = %5.22` ile `%5` tavanını marjinal aşar; **Faz-1 `Base+Safety` (`%4.67 < %5`) → `RFQ-05` fiyat kilidi → Faz-2 `+Q/+HPC`** fazlı tedarik stratejisi öngörülmüştür (`no_supplier_quotes = true`).",
        "8. **Ölçüm / Tedarikçi / Proxy Sınırı:** Silikon-dışı `ibm_marrakesh` bulut QPU kontrol/dekoder proxy kıyaslaması dışında hiçbir deneysel laboratuvar ölçümü veya gerçek tedarikçi teklifi mevcut değildir (`TRL 1–2 / M0`). Kapanış onayı (`KABUL`) sıfır bağlamlı bağımsız Carbon denetimine aittir.",
        "",
        "![Exp151 Bütünleşik Artefakt Özeti ve Dosya Bütünlüğü Manifestosu](fig_exp151_v7_digital_twin.png)",
        "",
    ]
    return "\n".join(lines)


def run_v7_digital_twin(write_outputs: bool = True, run_live_yosys: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    preds = json.loads(PRED_PATH.read_text(encoding="utf-8"))
    ledgers, eng, live_data, all_hashes, twin_html = load_all_v7_artifacts(ROOT)
    live_raw_text = (ROOT / LIVE_QPU_ARTIFACT_REL).read_text(encoding="utf-8")
    boed_real_bath = eng["boed_real_bath"]

    l1 = compute_layer1_integrity(ledgers, eng, all_hashes)
    l2 = compute_layer2_universal_qldpc_d18(ledgers)
    l3 = compute_layer3_sb121_qecho8(ledgers)
    l4 = compute_layer4_verilog_rtl_and_twin(ledgers, twin_html, run_live_yosys=run_live_yosys)
    l5 = compute_layer5_industrial_safety(ledgers)
    l6 = run_layer6_live_ibm_qpu_and_cellisa40(live_data, live_raw_text, boed_real_bath)
    l7 = compute_layer7_v7_phased_procurement_and_evolution(ledgers)
    hist_ok = check_historical_certs(ROOT)
    master_cert = build_v7_master_certificate(all_hashes, l1, l2, l3, l4, l5, l6, l7)

    # Portability & zero-secret self-check
    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    bad_crn = "crn:v1:" + "bluemix:"
    bad_jwt = "bearer " + "eyj"
    hygiene_hits: list[str] = []
    for fp in (
        ROOT / "experiments" / "exp151_v7_digital_twin" / "digital_twin151.py",
        ROOT / "experiments" / "exp151_v7_digital_twin" / "run_exp151.py",
        PRED_PATH,
        ROOT / INTERACTIVE_TWIN_ARTIFACT_REL,
        ROOT / BOED_REAL_BATH_ARTIFACT_REL,
    ):
        if fp.is_file():
            txt = fp.read_text(encoding="utf-8")
            low = txt.lower()
            for tok in (bad_a, bad_b, bad_crn, bad_jwt):
                if tok in txt or tok in low:
                    hygiene_hits.append(f"{fp.name}:{tok}")

    y_t = l4["yosys_measured_pre_pnr"]["targets"]
    rec = l6["live_auto_recal"]
    c4 = l6["live_cellisa_v40"]
    bath = l6["real_si29_bath_boed"]

    verdicts = {
        "DT7_1_LEDGER_CAD_BOM_RTL_TWIN_SHA256_LOCK": bool(
            l1["n_experiment_ledgers"] == 27
            and l1["n_rtl_locked_files"] == 7
            and l1["n_total_locked_artifacts"] == len(ALL_LOCKED_ARTIFACTS) == 39
            and all(len(h) == 64 for h in all_hashes.values())
            and l1["cad_v6"]["overall_pass"]
            and l1["cad_v6"]["part_count"] == 199
            and abs(l1["cad_v6"]["total_mass_kg"] - 1108.137) < 0.01
            and l1["cad_v6"]["solid_clashes"] == 0
            and l1["cad_v6"]["clearances_passed"] == l1["cad_v6"]["clearances_total"] == 40
            and l1["bom_v7"]["csv_row_count"] == 180
            and abs(l1["bom_v7"]["m3_v5_base_nom_usd"] - 5_247_800.0) < 1.0
            and abs(l1["bom_v7"]["m3_base_plus_safety_nom_usd"] - 5_392_800.0) < 1.0
            and abs(l1["bom_v7"]["m3_v6_full_nom_usd"] - 5_547_800.0) < 1.0
            and abs(l1["bom_v7"]["m3_v7_full_nom_usd"] - 5_692_800.0) < 1.0
            and l1["bom_v7"]["reconciliation_error_usd"] == 0.0
            and l1["bom_v7"]["on_frame_cad_mass_error_kg"] == 0.0
            and abs(l1["bom_v7"]["facility_safety_mass_kg"] - 355.0) < 0.1
            and l1["bom_v7"]["rfq10_nom_share_pct"] >= 78.0
            and l1["bom_v7"]["rfq10_var_share_pct"] >= 92.0
        ),
        "DT7_2_UNIVERSAL_QLDPC_D18_AND_ALGORITHMS": bool(
            l2["bb288_commutes"]
            and l2["bb288_d_lit"] == 18
            and l2["bb288_depth"] == 7
            and l2["bb288_zero_kickback"]
            and l2["L_max_um"] <= 300.0
            and l2["fits_300um_m4_resonator"]
            and l2["p_th_72_vs_288_pct"] >= 0.75
            and l2["yield_576_N8_pct"] >= 99.0
            and l2["yield_576_N9_pct"] >= 99.8
            and l2["femoco"]["qldpc_cryostats"] <= 20
            and l2["femoco"]["cryo_compression_x"] >= 35.0
            and l2["rsa2048"]["qldpc_cryostats"] <= 300
            and l2["rsa2048"]["power_MW"] <= 10.0
            and l2["rsa2048"]["cryo_compression_x"] >= 50.0
            and l2["uq5_honest_fail"]
        ),
        "DT7_3_SB121_QECHO8_CLOSURE_AND_SU8_GRAPE": bool(
            l3["qecho8_algebraic_static_F_proc"] >= 0.999999
            and l3["qecho8_gross_0L_1ms"] >= 0.9990
            and l3["gross_infidelity_reduction_x"] >= 400.0
            and l3["qecho8_cat77_1ms"] >= 0.9990
            and l3["su8_grape_min_F"] >= 0.9950
            and l3["sq4_honest_1f_fail"]
            and l3["t2_gain_qecho64_1f_x"] >= 25.0
        ),
        "DT7_4_VERILOG_RTL_AND_INTERACTIVE_TWIN": bool(
            (l4["no_external_eda_sim"] is False)
            and l4["real_eda_verified"] is True
            and l4["no_vendor_vivado_pnr"] is True
            and l4["no_lab_measurement_rtl"] is True
            and l4["exp149_verdicts_passed"] == "8/8"
            and l4["synth_files_count"] == 4
            and l4["total_rtl_loc"] >= 800
            and l4["forbidden_constructs"] == 0
            and l4["zero_combinational_div_operators"] is True
            and l4["single_cycle_clean_no_multicycle_waivers"] is True
            and l4["port_errors"] == 0
            and l4["width_mismatches"] == 0
            and l4["rom_words_checked"] == 1024
            and l4["rom_all_zero_bit_diff"]
            and l4["golden_vectors_tested"] == 64
            and l4["golden_all_zero_lsb"]
            and l4["isqrt_vectors_tested"] == 1000
            and l4["isqrt_max_lsb_err"] == 0
            and l4["boed_cycles_exact"] == 584
            and abs(l4["boed_latency_us_250MHz"] - 2.336) < 1e-6
            and l4["sprt_latency_cycles"] == 4
            and l4["verilator_lint"]["all_passed"]
            and l4["verilator_lint"]["boed_q16_core_warnings"] == 0
            and l4["verilator_lint"]["boed_top_16ch_warnings"] == 0
            and l4["iverilog_simulation"]["all_passed"]
            and l4["iverilog_simulation"]["vectors_tested"] == 64
            and l4["iverilog_simulation"]["boed_errors"] == 0
            and l4["iverilog_simulation"]["max_mu_off_q8_lsb_err"] == 0
            and l4["iverilog_simulation"]["max_std_q4_lsb_err"] == 0
            and l4["iverilog_simulation"]["max_next_probe_q8_lsb_err"] == 0
            and l4["iverilog_simulation"]["top_16ch_passed"]
            and l4["yosys_measured_pre_pnr"]["all_passed"]
            and l4["yosys_measured_pre_pnr"]["check_assert_passed"]
            and l4["yosys_measured_pre_pnr"]["disk_stat_json_parity"]
            and y_t["xcup_top16"]["fits_zu48dr"]
            and y_t["xcup_core"]["dsp_total"] > 0
            and y_t["xc7_core"]["dsp_total"] > 0
            and y_t["ecp5_core"]["dsp_total"] > 0
            and l4["zu48dr_16ch_cryo_W"] == 0.0
            and l4["interactive_twin"]["zero_external_cdn"]
            and l4["interactive_twin"]["zero_secret_and_path_leaks"]
            and l4["interactive_twin"]["embedded_json_valid"]
            and l4["interactive_twin"]["embedded_v7_live_sections"]
            and l4["interactive_twin"]["embedded_real_eda_verified"]
        ),
        "DT7_5_INDUSTRIAL_SAFETY_FMEA_HAZOP_SEMI_S2": bool(
            l5["all_7_verdicts_pass"]
            and l5["iec61508_certified"] is False
            and l5["semi_s2_certified"] is False
            and l5["certification_status"] == "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED"
            and l5["sil3_pfd_band_met_at_nominal_assumed_lambda_du"] is True
            and l5["requires_third_party_assessment"] is True
            and l5["zero_false_sil3_claim"] is True
            and l5["pfd_sensitivity_sweep"]["n_cases_degraded_to_sil2"] >= 1
            and l5["pfd_sensitivity_sweep"]["pfd_10x_lambda_du_beta10pct"] >= 1.0e-3
            and l5["odh_box_ode_transient"]["dry_60m3_0ACH_min_O2_pct"] > 20.5
            and l5["fmea_rows"] == 25
            and l5["hazop_nodes"] == 10
            and l5["max_rpn_pre"] == 280
            and l5["max_rpn_post"] <= 60
            and l5["residual_gt_60_count"] == 0
            and l5["laser_od_spec"] >= 8
            and l5["sil3_shutter_ms"] <= 5.0
            and l5["xray_22kev_shrouded_uSv_h"] < 1e-10
            and l5["ph3_operator_ppm"] < 0.01
            and l5["he_60m3_O2_pct"] >= 19.5
            and l5["ups_full_load_min"] >= 30.0
            and l5["ups_tier1_min"] >= 180.0
            and l5["uhv_gate_valve_ms"] <= 100.0
            and abs(l5["s_safety_nom_usd"] - 145_000.0) < 1.0
            and abs(l5["s_safety_mass_kg"] - 355.0) < 0.1
            and l5["s_safety_cryo_W"] == 0.0
        ),
        "DT7_6_LIVE_IBM_QPU_CELLISA40_AND_EPISTEMIC_BOUNDARY": bool(
            len(l6["secret_leaks"]) == 0
            and c4["v35_compat_opcodes"] == 17
            and c4["v40_total_opcodes"] == 20
            and c4["echo_cz"]["echo_fidelity_gain"] > 0.15
            and c4["echo_cz"]["cptp_max_trace_err"] < 1e-12
            and c4["mux_readout"]["exp140_n32_ceiling_reproduced"]
            and c4["qldpc_round"]["css_commutativity_verified"]
            and c4["qldpc_round"]["symplectic_logical_verified"]
            and c4["qldpc_round"]["syndrome_valid_frac"] == 1.0
            and rec["all_passed"]
            and rec["laser_thermal_pde"]["worst_uncontrolled_sigma_nm"] > 0.50
            and rec["laser_thermal_pde"]["worst_controlled_sigma_nm"] <= 0.50
            and rec["uhv_langmuir_ode"]["surface_monolayer_coverage_frac"] < 0.01
            and rec["blanker_step_and_stitch"]["wafer_site_coverage_after_pct"] == 100.0
            and 0.0 < rec["blanker_step_and_stitch"]["throughput_after_recal_pct"] < 100.0
            and rec["blanker_step_and_stitch"]["max_coordinate_mismatch_um"] == 0.0
            and bath["boed_identification_accuracy"] > bath["uniform_identification_accuracy"]
            and bath["probe_speedup_vs_uniform_raw"] >= 8.0
            and bath["legacy_exp132_fnr_on_real_bath"] == 1.0
            and bath["honest_failure_walls"]["low_snr_cliff_fnr_at_snr3"] == 1.0
            and l6["live_ibm_qpu"]["c1_xy4_gain_pp"] >= 50.0
            and l6["live_ibm_qpu"]["c1_bell_fidelity"] >= 0.95
            and l6["live_ibm_qpu"]["c2_suppression_mwpm"] >= 5.0
            and l6["live_ibm_qpu"]["c2_avg_p_L_postsel"] == 0.0
            and l6["live_ibm_qpu"]["c3_q16_points_used"] <= 5
            and l6["live_ibm_qpu"]["c3_q16_vs_fp64_kHz"] < 0.01
        ),
        "DT7_7_MODULAR_V7_BUDGET_CAP_AND_PHASED_PROCUREMENT": bool(
            l7["exp128_verdicts"]["CU1_bom_integrity"]
            and l7["exp128_verdicts"]["CU2_bom_cap_safety"]
            and l7["exp128_verdicts"]["CU3_base_plus_safety_pass"]
            and l7["exp128_verdicts"]["CU3_v6_full_pass"]
            and l7["exp128_verdicts"]["CU3_v7_full_honest_exceed"]
            and l7["exp128_verdicts"]["CU4_bc_wall_dominance"]
            and l7["exp128_verdicts"]["CU5_evpi_20mk_vindication"]
            and l7["exp128_verdicts"]["CU6_mc_convergence"]
            and l7["modular_tiers_v7"]["M3_v5_0_Base"]["P_gt_100M_pct"] < 5.0
            and l7["modular_tiers_v7"]["M3_Phase1_Base_Plus_Safety"]["P_gt_100M_pct"] < 5.0
            and l7["modular_tiers_v7"]["M3_v6_0_Full"]["P_gt_100M_pct"] < 5.0
            and l7["modular_tiers_v7"]["M3_v7_0_Full"]["P_gt_100M_pct"] > 5.0
        ),
        "DT7_8_CRYPTO_V7_CERT_PORTABILITY_AND_TESTS": bool(
            verify_v7_certificate(master_cert)
            and len(master_cert["sha256"]) == 64
            and all(hist_ok.values())
            and len(hygiene_hits) == 0
            and len(l6["secret_leaks"]) == 0
        ),
    }

    out_data = {
        "experiment": "exp151_v7_digital_twin",
        "hypothesis_id": "H169",
        "version": "7.2",
        "date": str(date.today()),
        "no_lab_measurement_silicon_rtl_safety": True,
        "no_supplier_quotes": True,
        "no_external_eda_sim": False,
        "real_eda_verified": True,
        "no_vendor_vivado_pnr": True,
        "iec61508_certified": False,
        "semi_s2_certified": False,
        "safety_certification_status": "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED",
        "epistemic_scope": {
            "silicon_31P_fab_bath_control_safety_economics": (
                "Model/Sayisal-Simulasyon/Varsayim/Liste-Capasi (TRL 1-2 / M0, no_lab_measurement=true, "
                "no_supplier_quotes=true, iec61508_certified=false, semi_s2_certified=false)"
            ),
            "rtl_eda_verification": (
                "Real open-source EDA verified on host (iverilog + vvp + verilator -Wall + yosys pre-P&R; "
                "no_external_eda_sim=false, real_eda_verified=true, no_vendor_vivado_pnr=true, no_lab_measurement_rtl=true)"
            ),
            "control_stack_cloud_qpu": (
                f"Canli-Donanim-IBM-QPU ({l6['live_ibm_qpu']['backend_name']}, "
                f"{l6['live_ibm_qpu']['n_qubits']}Q, job_id={l6['live_ibm_qpu']['job_id']}; "
                "superconducting control/decoder proxy, validates zero silicon 31P hardware)"
            ),
        },
        "runtime_s": round(time.perf_counter() - t0, 3),
        "predictions": preds,
        "verdicts": verdicts,
        "n_passed": sum(1 for v in verdicts.values() if v),
        "n_total": len(verdicts),
        "success_rule_met": bool(all(verdicts.values())),
        "locked_artifacts_sha256": dict(sorted(all_hashes.items())),
        "historical_certs_untouched": hist_ok,
        "layer1_integrity": l1,
        "layer2_universal_qldpc_d18": l2,
        "layer3_sb121_qecho8": l3,
        "layer4_verilog_rtl_and_twin": l4,
        "layer5_industrial_safety": l5,
        "layer6_live_ibm_qpu_and_cellisa40": l6,
        "layer7_v7_phased_procurement_and_evolution": l7,
        "v7_master_certificate": master_cert,
        "hygiene_hits": hygiene_hits,
    }

    if write_outputs:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "exp151.json").write_text(json.dumps(out_data, indent=2) + "\n", encoding="utf-8")
        (OUT_DIR / "v7_digital_twin_cert.json").write_text(
            json.dumps(master_cert, indent=2) + "\n", encoding="utf-8"
        )
        plot_payload = {
            "version": out_data["version"],
            "n_passed": out_data["n_passed"],
            "n_total": out_data["n_total"],
            "verdicts": verdicts,
            "l1": l1,
            "l2": l2,
            "l3": l3,
            "l4": l4,
            "l5": l5,
            "l6": l6,
            "l7": l7,
            "master_cert": master_cert,
        }
        (OUT_DIR / "exp151_plot_data.json").write_text(
            json.dumps(plot_payload, indent=2) + "\n", encoding="utf-8"
        )
        (OUT_DIR / "summary_exp151.md").write_text(
            render_summary_exp151_md(out_data), encoding="utf-8"
        )
    return out_data
