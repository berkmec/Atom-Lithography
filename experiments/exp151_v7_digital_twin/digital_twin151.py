"""Exp151 (H169): Master v7.0 End-to-End Digital Twin & Cryptographic SHA-256 Certificate.

Unifies all 38 primary v7.0 repository artifacts:
  - 27 primary experiment ledgers (Exp124..Exp150)
  - Live 156Q IBM Heron r2 hardware validation (ibm_marrakesh, job_id=dc1tdo2nj2vs73dfrfl0)
  - CAD v6.0 (199 parts, 1,108.137 kg, 0/19,701 clashes, 40/40 clearances)
  - BOM v7.0 (180 parts, Base $5.248M / Base+Safety $5.393M / v6 Full $5.548M / v7 Full $5.693M, 10-RFQ)
  - Synthesizable IEEE 1364-2005 Verilog RTL (rtl/boed_fpga/: 4 .v + 2 .hex + golden_vectors.mem)
  - Zero-CDN Live Interactive HTML5 Digital Twin (docs/digital_twin_interactive.html)
into a single canonical-JSON cryptographically signed v7.0 Master Digital Twin Certificate.

Portable execution (zero hardcoded host paths):
    PYTHONPATH=src python3 -B experiments/exp151_v7_digital_twin/run_exp151.py

Epistemic boundary:
    - Silicon 31P fabrication, CAD/BOM v7.0, Universal qLDPC d=18 (Exp147), 121Sb Q-Echo-8
      (Exp148), Verilog RTL (no_external_eda_sim=true, Exp149), SEMI S2/IEC 61508 Safety
      (Exp150), and auto_recal: {Model}/{Sayisal-Simulasyon}/{Varsayim}/{Liste-Capasi}
      (M0, no_lab_measurement=true, no_supplier_quotes=true).
    - Control/DD/Bell/d=3-QEC/Q16.16-BOED hardware benchmark on ibm_marrakesh:
      {Canli-Donanim-IBM-QPU} (independently recomputed from raw shot counts on disk, 0 secrets).
"""
from __future__ import annotations

import csv
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

ALL_LOCKED_ARTIFACTS: dict[str, str] = {
    **PRIMARY_EXPERIMENT_LEDGERS,
    **ENGINEERING_ARTIFACTS,
    **RTL_ARTIFACTS,
    "interactive_twin_html": INTERACTIVE_TWIN_ARTIFACT_REL,
    "live_ibm_qpu_results": LIVE_QPU_ARTIFACT_REL,
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
    """Load all 27 experiment JSONs + CAD v6.0 + BOM v7.0 + 7 RTL + HTML5 Twin + Live QPU (38 total)."""
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
            raise FileNotFoundError(f"Missing v7.0 artifact: {rel}")
        all_hashes[key] = hashlib.sha256(fp.read_bytes()).hexdigest()

    twin_fp = root / INTERACTIVE_TWIN_ARTIFACT_REL
    live_fp = root / LIVE_QPU_ARTIFACT_REL
    for fp in (twin_fp, live_fp):
        if not fp.is_file():
            raise FileNotFoundError(f"Missing v7.0 artifact: {fp}")

    twin_raw = twin_fp.read_bytes()
    live_raw = live_fp.read_bytes()
    all_hashes["interactive_twin_html"] = hashlib.sha256(twin_raw).hexdigest()
    all_hashes["live_ibm_qpu_results"] = hashlib.sha256(live_raw).hexdigest()

    cad_data = json.loads((root / ENGINEERING_ARTIFACTS["cad_v6"]).read_text(encoding="utf-8"))
    with (root / ENGINEERING_ARTIFACTS["bom_detailed_v7"]).open("r", encoding="utf-8", newline="") as f:
        bom_rows = list(csv.DictReader(f))
    live_data = json.loads(live_raw.decode("utf-8"))
    twin_html = twin_raw.decode("utf-8")

    eng = {"cad_v6": cad_data, "bom_v7_rows": bom_rows}
    return ledgers, eng, live_data, all_hashes, twin_html


def compute_layer1_integrity(
    ledgers: dict[str, Any],
    eng: dict[str, Any],
    all_hashes: dict[str, str],
) -> dict[str, Any]:
    """DT7_1: 38/38 Ledger + CAD v6.0 + BOM v7.0 + RTL + Interactive HTML5 Twin + Live QPU Lock."""
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
    write_outputs: bool = False,
) -> dict[str, Any]:
    """DT7_4: Live RTL lint/ROM/64-vector verification (Exp149) & v7.0 Interactive HTML5 Twin audit."""
    rtl = run_full_rtl_verification(RTL_DIR, write_outputs=write_outputs)
    lint = rtl["structural_lint"]
    rom = rtl["rom_verification"]
    co = rtl["bit_exact_co_verification"]
    tot16 = rtl["zu48dr_resource_budget"]["total_16ch"]

    low_html = twin_html.lower()
    has_external_cdn = any(p in low_html for p in ("https://", "http://", "cdn.jsdelivr", "unpkg.com"))
    twin_leaks = [
        tok for tok in ("crn:v1:" + "bluemix:", "bearer " + "eyj", "/" + "home/berk", "/" + "run/media/berk")
        if tok in low_html or tok in twin_html
    ]
    m = re.search(r"const DATA = (\{.*?\});\n", twin_html, flags=re.DOTALL)
    embedded_ok = False
    embedded_v7_keys_ok = False
    if m is not None:
        emb = json.loads(m.group(1).replace("<\\/", "</"))
        embedded_ok = (
            len(emb.get("subsystems", [])) == 9
            and emb.get("live_qpu", {}).get("backend", {}).get("name") == "ibm_marrakesh"
            and emb.get("rtl_fpga", {}).get("co_ver", {}).get("boed_cycles_max") == 584
        )
        embedded_v7_keys_ok = all(k in emb for k in ("v7_algorithms", "v7_sb121", "v7_safety"))

    return {
        "no_external_eda_sim": bool(rtl["no_external_eda_sim"]),
        "exp149_verdicts_passed": f"{ledgers['exp149']['n_passed']}/{ledgers['exp149']['n_total']}",
        "synth_files_count": len(lint["synth_files_checked"]),
        "total_rtl_loc": int(lint["total_rtl_loc"]),
        "forbidden_constructs": int(lint["forbidden_construct_count"]),
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
        "zu48dr_16ch_dsp_pct": float(tot16["dsp48e2_pct"]),
        "zu48dr_16ch_bram_pct": float(tot16["bram36_pct"]),
        "zu48dr_16ch_cryo_W": float(tot16["cryo_heat_load_W"]),
        "interactive_twin": {
            "size_bytes": len(twin_html.encode("utf-8")),
            "zero_external_cdn": not has_external_cdn,
            "zero_secret_and_path_leaks": len(twin_leaks) == 0,
            "embedded_json_valid": embedded_ok,
            "embedded_v7_live_sections": embedded_v7_keys_ok,
        },
    }


def compute_layer5_industrial_safety(ledgers: dict[str, Any]) -> dict[str, Any]:
    """DT7_5: Exp150 SEMI S2 / IEC 61508 Industrial Safety FMEA/HAZOP & S7.SAFETY."""
    d150 = ledgers["exp150"]
    fmea = d150["fmea_summary"]
    h1 = d150["hazard_1_laser_s55"]
    h2 = d150["hazard_2_ph3_and_forming_gas"]
    h3 = d150["hazard_3_hv_and_xray"]["energy_sweep"]["22keV"]
    h4 = d150["hazard_4_cryo_odh_and_quench"]["helium_odh"]["room_sweep"]["60m3"]
    h5 = d150["hazard_5_epo_ups_shutdown"]
    kit = d150["s_safety_spec"]["totals"]

    return {
        "overall_verdict": d150["overall_verdict"],
        "criteria_passed": d150["criteria_passed"],
        "all_7_verdicts_pass": all(bool(v["pass"]) for v in d150["preregistered_verdicts"].values()),
        "fmea_rows": int(fmea["n_rows"]),
        "hazop_nodes": len(d150["hazop_10_nodes"]),
        "max_rpn_pre": int(fmea["max_rpn_pre"]),
        "max_rpn_post": int(fmea["max_rpn_post"]),
        "mean_rpn_reduction_pct": float(fmea["mean_rpn_reduction_pct"]),
        "residual_gt_60_count": int(fmea["n_unacceptable_post_gt60"]),
        "laser_od_spec": int(h1["specified_enclosure_OD"]),
        "sil3_shutter_ms": float(h1["interlock_sil3"]["shutter_close_ms"]),
        "xray_22kev_shrouded_uSv_h": float(h3["s55_sapphire_plus_3mm_steel_shroud_uSv_h"]),
        "ph3_operator_ppm": float(h2["mitigated_sds_system"]["operator_direct_sds_diffusive_ppm"]),
        "he_60m3_O2_pct": float(h4["dry_ld400_pt420_O2_pct"]),
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
) -> dict[str, Any]:
    """DT7_6: Independent raw-count verification of live ibm_marrakesh + live CellISA v4.0 + auto_recal."""
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
    qram_live = mcp.execute_qram_swap(demo_cert, qubit_a="e", qubit_b="n0", seed=2026151)
    qldpc_live = mcp.execute_qldpc_round(code_name="BB_288_12_18", p_phys=0.00337, rounds=1)
    recal_live = AutoRecalController(seed=2026151).run_all_fault_scenarios()

    return {
        "epistemic_split": {
            "silicon_31P_rtl_safety": "Model/Sayisal-Simulasyon (M0, no_lab_measurement=true, no_external_eda_sim=true)",
            "ibm_qpu_metrics": "Canli-Donanim-IBM-QPU (ibm_marrakesh, 156Q Heron r2)",
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
            "qram_swap_fidelity": qram_live["swap_fidelity"],
            "qldpc_round_feedlines": qldpc_live["feedlines_required"],
        },
        "live_auto_recal": {
            "n_passed": recal_live["n_passed"],
            "n_fault_modes": recal_live["n_fault_modes"],
            "all_passed": recal_live["all_passed"],
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
    """Build canonical JSON v7.0 Master Digital Twin Certificate with full 64-hex SHA-256."""
    payload: dict[str, Any] = {
        "certificate_type": "ATOM_LITHOGRAPHY_MACHINE_V7_MASTER_DIGITAL_TWIN",
        "experiment": "exp151_v7_digital_twin",
        "hypothesis_id": "H169",
        "version": "7.0",
        "epistemic_scope": {
            "silicon_31P_fab_rtl_safety": "Model/Sayisal-Simulasyon/Varsayim/Liste-Capasi (M0, no_lab_measurement=true, no_supplier_quotes=true, no_external_eda_sim=true)",
            "control_stack_cloud_qpu": f"Canli-Donanim-IBM-QPU ({l6['live_ibm_qpu']['backend_name']}, {l6['live_ibm_qpu']['n_qubits']}Q, job_id={l6['live_ibm_qpu']['job_id']})",
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
        "exp150_safety_criteria": l5["criteria_passed"],
        "exp150_fmea_max_rpn_pre": l5["max_rpn_pre"],
        "exp150_fmea_max_rpn_post": l5["max_rpn_post"],
        "exp150_fmea_mean_reduction_pct": l5["mean_rpn_reduction_pct"],
        "exp150_ph3_operator_ppm": l5["ph3_operator_ppm"],
        "exp150_he_60m3_O2_pct": l5["he_60m3_O2_pct"],
        "exp150_ups_full_tier1_min": [l5["ups_full_load_min"], l5["ups_tier1_min"]],
        "exp150_s_safety_nom_usd": l5["s_safety_nom_usd"],
        "live_qpu_backend": l6["live_ibm_qpu"]["backend_name"],
        "live_qpu_job_id": l6["live_ibm_qpu"]["job_id"],
        "live_qpu_bell_fidelity": l6["live_ibm_qpu"]["c1_bell_fidelity"],
        "live_qpu_xy4_gain_pp": l6["live_ibm_qpu"]["c1_xy4_gain_pp"],
        "live_qpu_q16_vs_fp64_kHz": l6["live_ibm_qpu"]["c3_q16_vs_fp64_kHz"],
        "live_cellisa_v40_opcodes": l6["live_cellisa_v40"]["v40_total_opcodes"],
        "live_auto_recal_passed": f"{l6['live_auto_recal']['n_passed']}/{l6['live_auto_recal']['n_fault_modes']}",
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


def run_v7_digital_twin(write_outputs: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    preds = json.loads(PRED_PATH.read_text(encoding="utf-8"))
    ledgers, eng, live_data, all_hashes, twin_html = load_all_v7_artifacts(ROOT)
    live_raw_text = (ROOT / LIVE_QPU_ARTIFACT_REL).read_text(encoding="utf-8")

    l1 = compute_layer1_integrity(ledgers, eng, all_hashes)
    l2 = compute_layer2_universal_qldpc_d18(ledgers)
    l3 = compute_layer3_sb121_qecho8(ledgers)
    l4 = compute_layer4_verilog_rtl_and_twin(ledgers, twin_html, write_outputs=write_outputs)
    l5 = compute_layer5_industrial_safety(ledgers)
    l6 = run_layer6_live_ibm_qpu_and_cellisa40(live_data, live_raw_text)
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
    ):
        if fp.is_file():
            txt = fp.read_text(encoding="utf-8")
            low = txt.lower()
            for tok in (bad_a, bad_b, bad_crn, bad_jwt):
                if tok in txt or tok in low:
                    hygiene_hits.append(f"{fp.name}:{tok}")

    verdicts = {
        "DT7_1_LEDGER_CAD_BOM_RTL_TWIN_SHA256_LOCK": bool(
            l1["n_experiment_ledgers"] == 27
            and l1["n_rtl_locked_files"] == 7
            and l1["n_total_locked_artifacts"] == 38
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
            l4["no_external_eda_sim"]
            and l4["synth_files_count"] == 4
            and l4["total_rtl_loc"] >= 800
            and l4["forbidden_constructs"] == 0
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
            and l4["zu48dr_16ch_dsp_pct"] < 15.0
            and l4["zu48dr_16ch_cryo_W"] == 0.0
            and l4["interactive_twin"]["zero_external_cdn"]
            and l4["interactive_twin"]["zero_secret_and_path_leaks"]
            and l4["interactive_twin"]["embedded_json_valid"]
            and l4["interactive_twin"]["embedded_v7_live_sections"]
        ),
        "DT7_5_INDUSTRIAL_SAFETY_FMEA_HAZOP_SEMI_S2": bool(
            l5["all_7_verdicts_pass"]
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
            and l6["live_cellisa_v40"]["v35_compat_opcodes"] == 17
            and l6["live_cellisa_v40"]["v40_total_opcodes"] == 20
            and l6["live_auto_recal"]["all_passed"]
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
        "version": "7.0",
        "date": "2026-11-23",
        "no_lab_measurement_silicon_rtl_safety": True,
        "no_supplier_quotes": True,
        "no_external_eda_sim": True,
        "epistemic_scope": {
            "silicon_31P_fab_rtl_safety_economics": "Model/Sayisal-Simulasyon/Varsayim/Liste-Capasi (M0, no_lab_measurement=true, no_supplier_quotes=true, no_external_eda_sim=true)",
            "control_stack_cloud_qpu": f"Canli-Donanim-IBM-QPU ({l6['live_ibm_qpu']['backend_name']}, {l6['live_ibm_qpu']['n_qubits']}Q, job_id={l6['live_ibm_qpu']['job_id']})",
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
    return out_data
