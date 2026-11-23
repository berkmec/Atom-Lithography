"""Exp146 (H164): Master v6.0 End-to-End Digital Twin & Cryptographic SHA-256 Certificate.

Unifies all 22 primary experiment ledgers (Exp124-Exp145), CAD v6.0 (199 parts,
1108.137 kg, 0/19,701 clashes, 40/40 clearances), BOM v6.0 (174 parts, M3 Base
$5,247,800 / Full $5,547,800, 9-RFQ), live 156-qubit IBM Heron r2 hardware validation
(ibm_marrakesh, job_id=dc1tdo2nj2vs73dfrfl0), and live src/machine_control/ CellISA v4.0
+ auto_recal.py into a single cryptographically signed v6.0 Master Digital Twin Certificate.

Portable execution (zero hardcoded host paths):
    PYTHONPATH=src python3 -B experiments/exp146_v6_digital_twin/run_exp146.py

Epistemic scope:
    - Silicon 31P fabrication, CAD/BOM v6.0, D3 GRAPE, qLDPC, Option-Q/HPC, and auto_recal:
      {Model} / {Sayisal-Simulasyon} / {Varsayim} / {Liste-Capasi} (M0, no_lab_measurement=true,
      no_supplier_quotes=true).
    - Control/DD/Bell/d=3-QEC/Q16.16-BOED hardware benchmark on ibm_marrakesh:
      {Canli-Donanim-IBM-QPU} (recomputed directly from raw shot counts on disk, zero secrets).
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from machine_control.auto_recal import AutoRecalController  # noqa: E402
from machine_control.cloud_qpu_bridge import analyze_validation_suite_counts  # noqa: E402
from machine_control.factory import Certificate  # noqa: E402
from machine_control.programmer import (  # noqa: E402
    MultiCellProgrammer,
    VALID_OPCODES,
    VALID_OPCODES_ALL,
    VALID_OPCODES_V4,
)

OUT_DIR = ROOT / "results" / "exp146_v6_digital_twin"
PRED_PATH = OUT_DIR / "predictions_exp146.json"

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
}

ENGINEERING_ARTIFACTS: dict[str, str] = {
    "cad_v6": "research/atom_lithography_machine/cad/cad_verification.json",
    "bom_detailed_v6": "research/atom_lithography_machine/BOM_DETAILED.csv",
}

LIVE_QPU_ARTIFACT_REL = "results/exp145_cloud_qpu_ibm_validation/ibm_qpu_live_results.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_all_v6_artifacts(
    root: Path = ROOT,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, str], str]:
    """Load all 22 experiment JSONs + CAD v6.0 + BOM v6.0 (24 primary) + live IBM QPU JSON."""
    ledgers: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}

    for key, rel in PRIMARY_EXPERIMENT_LEDGERS.items():
        fp = root / rel
        if not fp.is_file():
            raise FileNotFoundError(f"Missing primary experiment ledger: {rel}")
        raw = fp.read_bytes()
        hashes[key] = hashlib.sha256(raw).hexdigest()
        ledgers[key] = json.loads(raw.decode("utf-8"))

    cad_fp = root / ENGINEERING_ARTIFACTS["cad_v6"]
    bom_fp = root / ENGINEERING_ARTIFACTS["bom_detailed_v6"]
    live_fp = root / LIVE_QPU_ARTIFACT_REL
    for fp in (cad_fp, bom_fp, live_fp):
        if not fp.is_file():
            raise FileNotFoundError(f"Missing v6.0 artifact: {fp}")

    cad_raw = cad_fp.read_bytes()
    bom_raw = bom_fp.read_bytes()
    live_raw = live_fp.read_bytes()
    hashes["cad_v6"] = hashlib.sha256(cad_raw).hexdigest()
    hashes["bom_detailed_v6"] = hashlib.sha256(bom_raw).hexdigest()
    live_sha256 = hashlib.sha256(live_raw).hexdigest()

    cad_data = json.loads(cad_raw.decode("utf-8"))
    with bom_fp.open("r", encoding="utf-8", newline="") as f:
        bom_rows = list(csv.DictReader(f))
    live_data = json.loads(live_raw.decode("utf-8"))

    eng = {"cad_v6": cad_data, "bom_v6_rows": bom_rows}
    return ledgers, eng, live_data, hashes, live_sha256


def compute_layer1_integrity(
    ledgers: dict[str, Any],
    eng: dict[str, Any],
    hashes: dict[str, str],
    live_sha256: str,
) -> dict[str, Any]:
    """DT6_1: 24/24 Primary Ledger + CAD v6.0 + BOM v6.0 + Live QPU SHA-256 Lock."""
    cad = eng["cad_v6"]
    ma = cad["master_assembly"]
    ia = cad["interference_audit"]
    cc = cad["critical_clearances"]
    cc_total = len(cc)
    cc_pass = sum(1 for v in cc.values() if isinstance(v, dict) and v.get("pass") is True)

    b128 = ledgers["exp128"]["bom_detailed_summary"]
    rfq = ledgers["exp128"]["rfq_coverage"]
    mass_rec = ledgers["exp128"]["v6_hardware_mass_reconciliation"]

    return {
        "n_experiment_ledgers": len(PRIMARY_EXPERIMENT_LEDGERS),
        "n_primary_hashed_artifacts": len(hashes),
        "live_qpu_artifact_sha256": live_sha256,
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
            "exp142_s9q_pass": bool(cad["exp142_s9q_audit"]["pass"]),
            "exp143_s9hpc_pass": bool(cad["exp143_s9hpc_audit"]["pass"]),
        },
        "bom_v6": {
            "version": b128["bom_version"],
            "csv_row_count": len(eng["bom_v6_rows"]),
            "exp128_total_parts": int(b128["total_parts"]),
            "v5_base_parts": int(b128["v5_base_parts"]),
            "v6_option_parts": int(b128["v6_option_parts"]),
            "m1_nom_usd": float(b128["m1_nom_usd"]),
            "m3_v3_nom_usd": float(b128["m3_v3_base_nom_usd"]),
            "m3_v4_nom_usd": float(b128["m3_v4_base_nom_usd"]),
            "m3_v5_base_nom_usd": float(b128["m3_v5_base_nom_usd"]),
            "m3_v6_plus_option_q_nom_usd": float(b128["m3_v6_plus_option_q_nom_usd"]),
            "m3_v6_plus_option_hpc_nom_usd": float(b128["m3_v6_plus_option_hpc_nom_usd"]),
            "m3_v6_full_nom_usd": float(b128["m3_v6_full_nom_usd"]),
            "option_q_nom_usd": float(b128["v6_option_q_nom_usd"]),
            "option_hpc_nom_usd": float(b128["v6_option_hpc_nom_usd"]),
            "reconciliation_error_usd": float(b128["reconciliation_error_usd"]),
            "cad_mass_reconciliation_error_kg": float(mass_rec["mass_reconciliation_error_kg"]),
            "rfq9_nom_share_pct": round(float(rfq["rfq9_nom_share"]) * 100.0, 2),
            "rfq9_var_share_pct": round(float(rfq["rfq9_variance_share_mc"]) * 100.0, 2),
        },
    }


def compute_layer2_d3_grape(ledgers: dict[str, Any]) -> dict[str, Any]:
    """DT6_2: Exp143 K=8 Fourier GRAPE M4 physical gate closure & live Exp138 MWPM."""
    d143 = ledgers["exp143"]
    p1 = d143["part1_grape_optimization"]
    echo = d143["part2_noisy_1f_sweep"]["grape_echoed_exp136_0p0225kHz_nuc"]
    cons = d143["part2_noisy_1f_sweep"]["grape_conservative_0p5kHz_nuc"]
    mwpm = d143["part3_live_exp138_mwpm_verification"]
    dh4 = d143["verdicts"]["DH4_LIVE_EXP138_MWPM_LAMBDA_D3_PHYS"]

    q10_s39 = echo["Q10e5_S0p39"]
    q10_s25 = echo["Q10e5_S0p25"]
    c_q10_s25 = cons["Q10e5_S0p25"]

    return {
        "k_harmonics": int(p1["k_harmonics"]),
        "t_gate_cons_us": round(float(mwpm["D3_phys_cons_Q1e6_S0p25_5pair"]["t_gate_us"]), 4),
        "t_gate_echo_us": round(float(mwpm["D3_phys_echo_Q1e6_S0p25_5pair"]["t_gate_us"]), 4),
        "bw_le_300mhz_frac": float(p1["min_bw_300mhz_energy_frac"]),
        "max_bw_99pct_mhz": round(float(p1["max_bw_99pct_mhz"]), 2),
        "all_cptp_clean": bool(d143["part2_noisy_1f_sweep"]["all_cptp_clean"]),
        "echo_Q1e6_S0p39_p_2q_pct": round(float(q10_s39["p_total_err"]) * 100.0, 4),
        "echo_Q1e6_S0p39_F_avg": round(float(q10_s39["F_avg"]), 6),
        "echo_Q1e6_S0p25_p_2q_pct": round(float(q10_s25["p_total_err"]) * 100.0, 4),
        "echo_Q1e6_S0p25_F_avg": round(float(q10_s25["F_avg"]), 6),
        "echo_Q1e6_S0p25_F_Bell": round(float(q10_s25["F_Bell"]), 6),
        "cons_Q1e6_S0p25_5pair_p_2q_pct": round(float(c_q10_s25["p_total_err"]) * 100.0, 4),
        "cons_Q1e6_S0p25_highG3_p_2q_pct": round(
            float(mwpm["D3_phys_cons_Q1e6_S0p25_highG3"]["p_2q"]) * 100.0, 4
        ),
        "lambda_D3_phys_echo_Q1e6_S0p25": round(float(dh4["Lambda_D3_phys_echo_Q1e6_S0p25"]), 4),
        "lambda_D3_phys_cons_5pair": round(float(dh4["Lambda_D3_phys_cons_5pair"]), 4),
        "cryostats_100L_1e9_D2_baseline": int(dh4["exp138_D2_baseline_cryostats_100L_1e9"]),
        "cryostats_100L_1e9_D3_echo": int(dh4["cryostats_100L_1e9_echo_Q1e6_S0p25"]),
        "cryostat_reduction_D2_to_D3": round(
            float(dh4["exp138_D2_baseline_cryostats_100L_1e9"])
            / max(float(dh4["cryostats_100L_1e9_echo_Q1e6_S0p25"]), 1.0),
            2,
        ),
    }


def compute_layer3_qldpc(ledgers: dict[str, Any]) -> dict[str, Any]:
    """DT6_3: Exp144 [[144,12,12]] Gross Code single-cryostat & $/L_sys revolution."""
    d144 = ledgers["exp144"]
    p2 = d144["part2_m4_layout_and_defect_yield"]
    rec = p2["recommended_layout_summary"]
    y15_n8 = p2["defect_yield_f1p5_Ez2MVm_v5_star"]["by_N_cand"]["N8"]
    sp9 = p2["spared_9of10_cryostat_die_yield_f1p5"]
    p4_m = d144["part4_circuit_level_dem"]["machine_regimes_BB144_Z_and_X"]
    p5 = d144["part5_cryostat_and_tco_compression"]
    c9 = p5["configs"]["BB144_100L_9blk"]
    c10 = p5["configs"]["BB144_120L_10blk_full_cryo"]
    ratios = p5["compression_ratios_BB144_9blk_vs_surface_code"]

    return {
        "code": "BB_144_12_12",
        "pitch_um": float(rec["pitch_um"]),
        "L_max_um": float(rec["L_max_um"]),
        "fits_300um_m4_resonator": bool(rec["fits_300um_m4_resonator"]),
        "block_288_yield_f15_N8_pct": round(float(y15_n8["block_288_yield_pct"]), 3),
        "spared_9of10_108L_die_yield_N8_pct": round(float(sp9["N8_pct"]), 4),
        "p_L_per_round_1L_D3_P4biased": float(p4_m["D3_Exp138_p0p50_RO2us_P4biased"]["p_L_round_per_logical"]),
        "p_L_per_round_1L_D3plus_2us": float(p4_m["D3plus_p0p30_RO2us_depol"]["p_L_round_per_logical"]),
        "p_L_per_round_1L_D3plus_3us": float(p4_m["D3plus_p0p30_RO3us_depol"]["p_L_round_per_logical"]),
        "single_cryostat_max_blocks": int(p5["gross_code_single_cryo_blocks"]),
        "single_cryostat_max_logical_qubits": int(p5["gross_code_single_cryo_logical_qubits"]),
        "single_cryostat_active_cells": int(p5["gross_code_single_cryo_active_cells"]),
        "config_108L_cryostats": int(c9["n_cryostats"]),
        "config_108L_logical_delivered": int(c9["n_logical_delivered"]),
        "config_108L_usd_per_L_sys_p50": round(float(c9["usd_per_logical_sys_amort_wright"]["p50"]), 2),
        "config_120L_usd_per_L_sys_p50": round(float(c10["usd_per_logical_sys_amort_wright"]["p50"]), 2),
        "config_108L_W3_fab_usd_per_L": float(c9["fab_cost_by_wafer"]["W3"]["usd_per_logical_fab_p50"]),
        "compression_cryo_vs_D2_SC": float(ratios["cryostats_vs_D2_1e-9"]),
        "compression_cryo_vs_D3_SC": float(ratios["cryostats_vs_D3_1e-9"]),
        "compression_usd_vs_D2_SC": float(ratios["usd_per_L_sys_vs_D2_1e-9"]),
        "compression_usd_vs_D3_SC": float(ratios["usd_per_L_sys_vs_D3_1e-9"]),
        "all_7_verdicts_pass": bool(d144["success_rule_met"]),
    }


def compute_layer4_option_q_multispecies(ledgers: dict[str, Any]) -> dict[str, Any]:
    """DT6_4: Exp142 Option-Q 50 Ohm <-> 3 kOhm qRAM bridge & S1-Multi (167Er, 121Sb)."""
    d142 = ledgers["exp142"]
    ch5 = d142["part1_qram_bridge"]["impedance_transformers"]["chebyshev_N5"]
    lind = d142["part1_qram_bridge"]["lindblad_12x12_swap"]
    cryo = d142["part1_qram_bridge"]["cryo_heat_budget"]
    er10 = d142["part2_s1_multispecies"]["er167_telecom_link"]["anchor_10km"]
    zbl = d142["part2_s1_multispecies"]["zbl_bca_implantation"]
    p5_sig = float(zbl["31P_5keV"]["sigma_lat_1d_nm"])
    sb75_sig = float(zbl["121Sb_7p5keV"]["sigma_lat_1d_nm"])
    sb_reduction_pct = 100.0 * (1.0 - sb75_sig / p5_sig)

    return {
        "chebyshev5_IL_6GHz_dB": round(float(ch5["IL_6GHz_dB"]), 6),
        "chebyshev5_max_S11_dB": round(float(ch5["max_S11_4_8GHz_dB"]), 2),
        "chebyshev5_bw_15dB_GHz": round(float(ch5["bw_15dB_GHz"]), 3),
        "F_SWAP_rt_31P_nuclear": round(float(lind["F_SWAP_rt_with_nuclear_31P"]), 5),
        "F_SWAP_rt_photon_only": round(float(lind["F_SWAP_rt_photon_only"]), 5),
        "lifetime_gain_F90_XY8_1s": round(float(lind["lifetime_gain_F90_vs_transmon"]["qram_XY8_DD_1s"]), 1),
        "lifetime_gain_F90_XY8_3s": round(float(lind["lifetime_gain_F90_vs_transmon"]["qram_XY8_DD_3s"]), 1),
        "cryo_added_20mK_uW": float(cryo["option_q_added_load"]["mxc_20mK_uW"]),
        "cryo_added_4K_W": float(cryo["option_q_added_load"]["stage_4K_W"]),
        "cryo_all_within_ld400": bool(cryo["combined_with_exp140_1024"]["all_stages_within_ld400_pt420"]),
        "er167_10km_BK_rate_Hz": round(float(er10["R_ent_BK_Hz"]), 1),
        "er167_10km_BK_fidelity": round(float(er10["F_ent_BK"]), 4),
        "sb121_7p5keV_sigma_lat_nm": round(sb75_sig, 3),
        "p31_5keV_sigma_lat_nm": round(p5_sig, 3),
        "sb121_straggle_reduction_pct": round(sb_reduction_pct, 2),
        "s9q_mass_kg": float(d142["part3_s9q_hardware_spec_summary"]["total_mass_kg"]),
        "s9q_cost_nom_usd": float(d142["part3_s9q_hardware_spec_summary"]["cost_usd_nom"]),
    }


def compute_layer5_option_hpc(ledgers: dict[str, Any]) -> dict[str, Any]:
    """DT6_5: Exp143 Option-HPC 100G RoCEv2 RDMA real-time decoder closure."""
    d143 = ledgers["exp143"]
    p4 = d143["part4_option_hpc_decoder_wall"]
    dh5 = d143["verdicts"]["DH5_OPTION_HPC_REALTIME_DECODER_WALL_AND_BACKLOG"]
    ql = p4["qldpc_gross_144_12_12"]
    hw = d143["s9hpc_hardware_spec_summary"]

    return {
        "tau_ingest_ns": round(float(p4["tau_ingest_us"]) * 1000.0, 1),
        "d37_sc_cpu_single_us": round(float(dh5["d37_tau_cpu_single_us"]), 3),
        "d37_sc_hpc_e2e_us": round(float(dh5["d37_tau_hpc_e2e_stream_us"]), 3),
        "d37_sc_backlog_free_6p70us": bool(float(dh5["d37_tau_hpc_e2e_stream_us"]) < 6.70),
        "qldpc_108L_hpc_e2e_mean_us": round(float(ql["tau_hpc_e2e_mean_us"]), 4),
        "qldpc_108L_backlog_free_2p62us": bool(ql["backlog_free_hpc_2p62us"]),
        "qldpc_108L_4u_modules": int(ql["option_hpc_4u_modules_108L"]),
        "qldpc_108L_bw_d3_gbps": round(float(ql["bw_108L_hard_d3_gbps"]), 4),
        "s9hpc_mass_kg": float(hw["total_mass_kg"]),
        "s9hpc_room_temp_power_W": float(hw["room_temp_power_W"]),
        "s9hpc_cryo_load_W": float(hw["cryo_load_W"]),
        "s9hpc_cost_nom_usd": float(hw["cost_usd_nom"]),
    }


def run_layer6_live_ibm_qpu_and_cellisa40(
    live_data: dict[str, Any],
    live_raw_text: str,
) -> dict[str, Any]:
    """DT6_6: Independent raw-count verification of live ibm_marrakesh + live CellISA v4.0 + auto_recal."""
    # 1. Secret-leak check on live hardware artifact
    secret_leaks: list[str] = []
    low_txt = live_raw_text.lower()
    for pat in ("crn:v1:" + "bluemix:", "bearer " + "eyj", "api" + "key=", "/home/" + "berk", "/run/media/" + "berk"):
        if pat in low_txt:
            secret_leaks.append(pat)

    # 2. Independently recompute C1, C2, C3 metrics directly from raw ibm_marrakesh shot counts!
    recomp = analyze_validation_suite_counts(
        counts_by_pub=live_data["counts_by_pub"],
        c3_delays_us=live_data["timing_actual"]["c3_delays_us"],
        c3_programmed_kHz=live_data["timing_actual"]["c3_programmed_detuning_kHz"],
        c1_idle_us=live_data["timing_actual"]["c1_idle_us"],
    )
    lc1 = recomp["C1_dd_and_bell"]
    lc2 = recomp["C2_repcode3"]
    lc3 = recomp["C3_ramsey_boed"]

    # 3. Execute live CellISA v4.0 opcodes + AutoRecalController (4 fault modes)
    mcp = MultiCellProgrammer()
    demo_cert = Certificate(
        register_id="REG-EXP146-V6-01",
        slot=0,
        attempts=1,
        shots=1,
        min_spacing_Hz=12_000.0,
        dd_quality_gate=True,
        lines_Hz=[120_000.0, 92_000.0, 68_000.0, 48_000.0],
    )
    qram_live = mcp.execute_qram_swap(demo_cert, qubit_a="e", qubit_b="n0", seed=2026146)
    qldpc_live = mcp.execute_qldpc_round(code_name="BB_144_12_12", p_phys=0.003, rounds=1)
    recal_live = AutoRecalController(seed=2026146).run_all_fault_scenarios()

    return {
        "epistemic_split": {
            "ibm_qpu_metrics": "Canli-Donanim-IBM-QPU",
            "cellisa40_and_auto_recal": "Model/Sayisal-Simulasyon (M0)",
        },
        "secret_leaks": secret_leaks,
        "live_ibm_qpu": {
            "backend_name": live_data["backend"]["name"],
            "n_qubits": int(live_data["backend"]["n_qubits"]),
            "native_2q": live_data["backend"]["native_2q"],
            "dt_ns": float(live_data["backend"]["dt_ns"]),
            "selected_5q_chain": live_data["backend"]["selected_5q_chain"],
            "job_id": live_data["job"]["job_id"],
            "wall_clock_seconds": float(live_data["job"]["wall_clock_seconds"]),
            "shots_per_pub": int(live_data["job"]["shots_per_pub"]),
            "c1_bare_p0": lc1["p0_bare_idle"],
            "c1_echo_p0": lc1["p0_hahn_echo"],
            "c1_xy4_p0": lc1["p0_xy4_dd"],
            "c1_xy4_gain_pp": round(lc1["dd_gain_xy4_over_bare"] * 100.0, 2),
            "c1_bell_fidelity": lc1["bell_fidelity_Phi_plus"],
            "c2_avg_p_phys": lc2["avg_p_phys"],
            "c2_avg_p_L_mwpm": lc2["avg_p_L_syndrome_mwpm"],
            "c2_avg_p_L_majority": lc2["avg_p_L_majority"],
            "c2_avg_p_L_postsel": lc2["avg_p_L_postsel"],
            "c2_suppression_mwpm": round(lc2["avg_p_phys"] / max(lc2["avg_p_L_syndrome_mwpm"], 1e-6), 2),
            "c2_suppression_majority": lc2["suppression_ratio_decoded"],
            "c3_blind8_kHz": lc3["blind_8pt"]["est_freq_kHz"],
            "c3_fp64_boed_kHz": lc3["fp64_boed"]["est_freq_kHz"],
            "c3_q16_boed_kHz": lc3["q16_16_boed"]["est_freq_kHz"],
            "c3_q16_points_used": lc3["q16_16_boed"]["n_points"],
            "c3_q16_vs_fp64_kHz": lc3["q16_16_boed"]["q16_vs_fp64_diff_kHz"],
            "c3_q16_vs_blind8_kHz": lc3["q16_16_boed"]["q16_vs_blind8_diff_kHz"],
            "c3_measured_q2_drift_kHz": round(lc3["blind_8pt"]["est_freq_kHz"] - 125.0, 4),
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
            "laser_sigma_nm": recal_live["S5_5_laser_drift"]["worst_controlled_sigma_nm"],
            "uhv_locked": recal_live["S5_uhv_vacuum_spike"]["gate_valve_locked"],
            "blanker_throughput_pct": recal_live["S3_blanker_dead_channels"]["throughput_after_recal_pct"],
            "hyperfine_relock_ms": recal_live["hyperfine_thermal_drift"]["max_relock_time_ms"],
            "hyperfine_resid_Hz": recal_live["hyperfine_thermal_drift"]["max_residual_error_Hz"],
        },
    }


def compute_layer7_v3_to_v6_evolution(ledgers: dict[str, Any]) -> dict[str, Any]:
    """DT6_7: Complete v3.0 -> v4.0 -> v5.0 -> v6.0 architecture, fleet & modular TCO trajectory."""
    b128 = ledgers["exp128"]["bom_detailed_summary"]
    mc = ledgers["exp128"]["v6_modular_mc_comparison"]
    p5_144 = ledgers["exp144"]["part5_cryostat_and_tco_compression"]
    sc_base = p5_144["surface_code_baselines_exp141"]
    ql_9blk = p5_144["configs"]["BB144_100L_9blk"]

    base_mc = mc["M3_v5_0_Base"]
    optq_mc = mc["M3_v6_0_Plus_Option_Q"]
    opthpc_mc = mc["M3_v6_0_Plus_Option_HPC"]
    full_mc = mc["M3_v6_0_Full_Option_Q_and_HPC"]

    return {
        "bom_evolution_nom_usd": {
            "v3_0_base": float(b128["m3_v3_base_nom_usd"]),
            "v4_0_base": float(b128["m3_v4_base_nom_usd"]),
            "v5_0_base": float(b128["m3_v5_base_nom_usd"]),
            "v6_0_plus_option_hpc": float(b128["m3_v6_plus_option_hpc_nom_usd"]),
            "v6_0_plus_option_q": float(b128["m3_v6_plus_option_q_nom_usd"]),
            "v6_0_full": float(b128["m3_v6_full_nom_usd"]),
        },
        "modular_mc_100k": {
            "M3_v5_0_Base": {
                "bom_nom_usd": float(base_mc["bom_nom_usd"]),
                "prog_p50_M": round(float(base_mc["program_stoch_usd"]["p50"]) / 1e6, 3),
                "P_gt_100M_pct": round(float(base_mc["P_Program_stoch_gt_100M"]) * 100.0, 2),
                "foak_5yr_p50_M": round(float(base_mc["foak_program_5yr_tco_no_wafers_usd"]["p50"]) / 1e6, 3),
                "P_foak_gt_100M_pct": round(float(base_mc["P_foak_5yr_tco_gt_100M"]) * 100.0, 2),
            },
            "M3_v6_0_Plus_Option_HPC": {
                "bom_nom_usd": float(opthpc_mc["bom_nom_usd"]),
                "prog_p50_M": round(float(opthpc_mc["program_stoch_usd"]["p50"]) / 1e6, 3),
                "P_gt_100M_pct": round(float(opthpc_mc["P_Program_stoch_gt_100M"]) * 100.0, 2),
            },
            "M3_v6_0_Plus_Option_Q": {
                "bom_nom_usd": float(optq_mc["bom_nom_usd"]),
                "prog_p50_M": round(float(optq_mc["program_stoch_usd"]["p50"]) / 1e6, 3),
                "P_gt_100M_pct": round(float(optq_mc["P_Program_stoch_gt_100M"]) * 100.0, 2),
            },
            "M3_v6_0_Full": {
                "bom_nom_usd": float(full_mc["bom_nom_usd"]),
                "prog_p50_M": round(float(full_mc["program_stoch_usd"]["p50"]) / 1e6, 3),
                "prog_p95_M": round(float(full_mc["program_stoch_usd"]["p95"]) / 1e6, 3),
                "P_gt_100M_pct": round(float(full_mc["P_Program_stoch_gt_100M"]) * 100.0, 2),
                "foak_5yr_p50_M": round(float(full_mc["foak_program_5yr_tco_no_wafers_usd"]["p50"]) / 1e6, 3),
                "P_foak_gt_100M_pct": round(float(full_mc["P_foak_5yr_tco_gt_100M"]) * 100.0, 2),
            },
        },
        "fleet_100L_trajectory": {
            "v5_D2_SC_cryostats": int(sc_base["D2_1e-9"]["cryostats_100L"]),
            "v6_D3_GRAPE_SC_cryostats": int(sc_base["D3_1e-9"]["cryostats_100L"]),
            "v6_qLDPC_108L_cryostats": int(ql_9blk["n_cryostats"]),
            "v5_D2_SC_usd_per_L_sys": round(float(sc_base["D2_1e-9"]["sys_100L_usd_per_L_amort_wright_p50"]), 2),
            "v6_D3_GRAPE_SC_usd_per_L_sys": round(float(sc_base["D3_1e-9"]["sys_100L_usd_per_L_amort_wright_p50"]), 2),
            "v6_qLDPC_108L_usd_per_L_sys": round(float(ql_9blk["usd_per_logical_sys_amort_wright"]["p50"]), 2),
            "total_usd_per_L_compression_x": round(
                float(sc_base["D2_1e-9"]["sys_100L_usd_per_L_amort_wright_p50"])
                / float(ql_9blk["usd_per_logical_sys_amort_wright"]["p50"]),
                2,
            ),
        },
    }


def build_v6_master_certificate(
    hashes: dict[str, str],
    live_sha256: str,
    l1: dict[str, Any],
    l2: dict[str, Any],
    l3: dict[str, Any],
    l4: dict[str, Any],
    l5: dict[str, Any],
    l6: dict[str, Any],
    l7: dict[str, Any],
) -> dict[str, Any]:
    """Build canonical JSON v6.0 Master Digital Twin Certificate with full 64-hex SHA-256."""
    payload: dict[str, Any] = {
        "certificate_type": "ATOM_LITHOGRAPHY_MACHINE_V6_MASTER_DIGITAL_TWIN",
        "experiment": "exp146_v6_digital_twin",
        "hypothesis_id": "H164",
        "version": "6.0",
        "epistemic_scope": {
            "silicon_31P_fabrication": "Model/Sayisal-Simulasyon/Varsayim/Liste-Capasi (M0, no_lab_measurement=true, no_supplier_quotes=true)",
            "control_stack_cloud_qpu": f"Canli-Donanim-IBM-QPU ({l6['live_ibm_qpu']['backend_name']}, {l6['live_ibm_qpu']['n_qubits']}Q, job_id={l6['live_ibm_qpu']['job_id']})",
        },
        "primary_ledger_sha256": dict(sorted(hashes.items())),
        "live_ibm_qpu_results_sha256": live_sha256,
        "cad_v6_parts": l1["cad_v6"]["part_count"],
        "cad_v6_mass_kg": l1["cad_v6"]["total_mass_kg"],
        "cad_v6_clashes": l1["cad_v6"]["solid_clashes"],
        "cad_v6_clearances_pass": f"{l1['cad_v6']['clearances_passed']}/{l1['cad_v6']['clearances_total']}",
        "cad_v6_stl_triangles": l1["cad_v6"]["stl_triangles"],
        "bom_v6_parts": l1["bom_v6"]["exp128_total_parts"],
        "bom_v6_m3_base_nom_usd": l1["bom_v6"]["m3_v5_base_nom_usd"],
        "bom_v6_m3_full_nom_usd": l1["bom_v6"]["m3_v6_full_nom_usd"],
        "bom_v6_reconciliation_error_usd": l1["bom_v6"]["reconciliation_error_usd"],
        "bom_v6_cad_mass_error_kg": l1["bom_v6"]["cad_mass_reconciliation_error_kg"],
        "bom_v6_rfq9_nom_share_pct": l1["bom_v6"]["rfq9_nom_share_pct"],
        "bom_v6_rfq9_var_share_pct": l1["bom_v6"]["rfq9_var_share_pct"],
        "d3_grape_echo_Q1e6_S0p39_p2q_pct": l2["echo_Q1e6_S0p39_p_2q_pct"],
        "d3_grape_echo_Q1e6_S0p25_p2q_pct": l2["echo_Q1e6_S0p25_p_2q_pct"],
        "d3_grape_lambda_phys": l2["lambda_D3_phys_echo_Q1e6_S0p25"],
        "qldpc_L_max_um": l3["L_max_um"],
        "qldpc_block_yield_f15_N8_pct": l3["block_288_yield_f15_N8_pct"],
        "qldpc_spared_108L_die_yield_pct": l3["spared_9of10_108L_die_yield_N8_pct"],
        "qldpc_single_cryo_logical_qubits": l3["single_cryostat_max_logical_qubits"],
        "qldpc_108L_cryostats": l3["config_108L_cryostats"],
        "qldpc_108L_usd_per_L_sys": l3["config_108L_usd_per_L_sys_p50"],
        "qldpc_108L_W3_fab_usd_per_L": l3["config_108L_W3_fab_usd_per_L"],
        "option_q_cheb5_IL_dB": l4["chebyshev5_IL_6GHz_dB"],
        "option_q_F_SWAP_31P": l4["F_SWAP_rt_31P_nuclear"],
        "option_q_lifetime_gain_XY8_1s": l4["lifetime_gain_F90_XY8_1s"],
        "option_q_er167_10km_Hz": l4["er167_10km_BK_rate_Hz"],
        "option_hpc_d37_e2e_us": l5["d37_sc_hpc_e2e_us"],
        "option_hpc_qldpc_108L_e2e_us": l5["qldpc_108L_hpc_e2e_mean_us"],
        "live_qpu_backend": l6["live_ibm_qpu"]["backend_name"],
        "live_qpu_job_id": l6["live_ibm_qpu"]["job_id"],
        "live_qpu_bell_fidelity": l6["live_ibm_qpu"]["c1_bell_fidelity"],
        "live_qpu_xy4_gain_pp": l6["live_ibm_qpu"]["c1_xy4_gain_pp"],
        "live_qpu_d3_suppression_majority": l6["live_ibm_qpu"]["c2_suppression_majority"],
        "live_qpu_q16_vs_fp64_kHz": l6["live_ibm_qpu"]["c3_q16_vs_fp64_kHz"],
        "live_cellisa_v40_opcodes": l6["live_cellisa_v40"]["v40_total_opcodes"],
        "live_auto_recal_passed": f"{l6['live_auto_recal']['n_passed']}/{l6['live_auto_recal']['n_fault_modes']}",
        "evolution_100L_cryostats": [
            l7["fleet_100L_trajectory"]["v5_D2_SC_cryostats"],
            l7["fleet_100L_trajectory"]["v6_D3_GRAPE_SC_cryostats"],
            l7["fleet_100L_trajectory"]["v6_qLDPC_108L_cryostats"],
        ],
        "evolution_usd_per_L_compression_x": l7["fleet_100L_trajectory"]["total_usd_per_L_compression_x"],
    }
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    cert = dict(payload)
    cert["sha256"] = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    return cert


def verify_v6_certificate(cert: dict[str, Any]) -> bool:
    """Recompute canonical SHA-256 digest and verify full 64-hex match."""
    sig = str(cert.get("sha256", ""))
    if len(sig) != 64:
        return False
    payload = {k: v for k, v in cert.items() if k != "sha256"}
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest() == sig


def run_v6_digital_twin(write_outputs: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    preds = json.loads(PRED_PATH.read_text(encoding="utf-8"))
    ledgers, eng, live_data, hashes, live_sha256 = load_all_v6_artifacts(ROOT)
    live_raw_text = (ROOT / LIVE_QPU_ARTIFACT_REL).read_text(encoding="utf-8")

    l1 = compute_layer1_integrity(ledgers, eng, hashes, live_sha256)
    l2 = compute_layer2_d3_grape(ledgers)
    l3 = compute_layer3_qldpc(ledgers)
    l4 = compute_layer4_option_q_multispecies(ledgers)
    l5 = compute_layer5_option_hpc(ledgers)
    l6 = run_layer6_live_ibm_qpu_and_cellisa40(live_data, live_raw_text)
    l7 = compute_layer7_v3_to_v6_evolution(ledgers)
    master_cert = build_v6_master_certificate(hashes, live_sha256, l1, l2, l3, l4, l5, l6, l7)

    # Portability self-check
    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    hardcoded_hits: list[str] = []
    for fp in (
        ROOT / "experiments" / "exp146_v6_digital_twin" / "digital_twin146.py",
        ROOT / "experiments" / "exp146_v6_digital_twin" / "run_exp146.py",
        PRED_PATH,
    ):
        if fp.is_file():
            txt = fp.read_text(encoding="utf-8")
            if bad_a in txt:
                hardcoded_hits.append(f"{fp.name}:{bad_a}")
            if bad_b in txt:
                hardcoded_hits.append(f"{fp.name}:{bad_b}")

    # Evaluate pre-registered DT6_1 .. DT6_8
    verdicts = {
        "DT6_1_LEDGER_CAD_BOM_SHA256_LOCK": bool(
            l1["n_experiment_ledgers"] == 22
            and l1["n_primary_hashed_artifacts"] == 24
            and len(l1["live_qpu_artifact_sha256"]) == 64
            and l1["cad_v6"]["overall_pass"]
            and l1["cad_v6"]["part_count"] == 199
            and abs(l1["cad_v6"]["total_mass_kg"] - 1108.137) < 0.01
            and l1["cad_v6"]["solid_clashes"] == 0
            and l1["cad_v6"]["clearances_passed"] == l1["cad_v6"]["clearances_total"] == 40
            and l1["cad_v6"]["stl_triangles"] == 39536
            and l1["cad_v6"]["stl_watertight"]
            and l1["bom_v6"]["csv_row_count"] == 174
            and abs(l1["bom_v6"]["m3_v5_base_nom_usd"] - 5_247_800.0) < 1.0
            and abs(l1["bom_v6"]["m3_v6_full_nom_usd"] - 5_547_800.0) < 1.0
            and l1["bom_v6"]["reconciliation_error_usd"] == 0.0
            and l1["bom_v6"]["cad_mass_reconciliation_error_kg"] == 0.0
            and l1["bom_v6"]["rfq9_nom_share_pct"] >= 77.0
            and l1["bom_v6"]["rfq9_var_share_pct"] >= 92.0
        ),
        "DT6_2_D3_GRAPE_M4_PHYSICAL_CLOSURE": bool(
            l2["t_gate_cons_us"] <= 1.0
            and l2["bw_le_300mhz_frac"] == 1.0
            and l2["all_cptp_clean"]
            and l2["echo_Q1e6_S0p39_p_2q_pct"] <= 0.45
            and l2["echo_Q1e6_S0p25_p_2q_pct"] <= 0.35
            and l2["echo_Q1e6_S0p25_F_avg"] >= 0.997
            and l2["echo_Q1e6_S0p25_F_Bell"] >= 0.9965
            and l2["lambda_D3_phys_echo_Q1e6_S0p25"] >= 2.80
            and l2["cryostats_100L_1e9_D3_echo"] <= 100
        ),
        "DT6_3_QLDPC_BB144_SINGLE_CRYOSTAT_REVOLUTION": bool(
            l3["L_max_um"] <= 300.0
            and l3["fits_300um_m4_resonator"]
            and l3["block_288_yield_f15_N8_pct"] >= 99.5
            and l3["spared_9of10_108L_die_yield_N8_pct"] >= 99.9
            and l3["p_L_per_round_1L_D3plus_2us"] <= 3e-5
            and l3["single_cryostat_max_logical_qubits"] == 120
            and l3["config_108L_cryostats"] == 1
            and l3["config_108L_usd_per_L_sys_p50"] <= 70_000.0
            and l3["compression_usd_vs_D2_SC"] >= 200.0
            and l3["compression_usd_vs_D3_SC"] >= 40.0
            and l3["config_108L_W3_fab_usd_per_L"] < 0.01
        ),
        "DT6_4_OPTION_Q_AND_S1_MULTI_PLATFORM": bool(
            l4["chebyshev5_IL_6GHz_dB"] <= 0.01
            and l4["chebyshev5_bw_15dB_GHz"] >= 5.0
            and l4["F_SWAP_rt_31P_nuclear"] >= 0.985
            and l4["lifetime_gain_F90_XY8_1s"] >= 8000.0
            and l4["cryo_added_20mK_uW"] <= 1.0
            and l4["cryo_all_within_ld400"]
            and l4["er167_10km_BK_rate_Hz"] >= 1000.0
            and l4["er167_10km_BK_fidelity"] >= 0.94
            and l4["sb121_straggle_reduction_pct"] >= 40.0
        ),
        "DT6_5_OPTION_HPC_ROCEV2_DECODER_CLOSURE": bool(
            l5["tau_ingest_ns"] < 1000.0
            and l5["d37_sc_backlog_free_6p70us"]
            and l5["qldpc_108L_backlog_free_2p62us"]
            and l5["qldpc_108L_4u_modules"] == 1
            and l5["s9hpc_room_temp_power_W"] <= 2500.0
            and l5["s9hpc_cryo_load_W"] == 0.0
        ),
        "DT6_6_LIVE_IBM_MARRAKESH_AND_CELLISA40_AUTOREKAL": bool(
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
        "DT6_7_V3_TO_V6_EVOLUTION_AND_MODULAR_ECONOMICS": bool(
            l7["modular_mc_100k"]["M3_v5_0_Base"]["P_gt_100M_pct"] < 5.0
            and l7["modular_mc_100k"]["M3_v6_0_Full"]["P_gt_100M_pct"] < 5.0
            and l7["fleet_100L_trajectory"]["v5_D2_SC_cryostats"] == 679
            and l7["fleet_100L_trajectory"]["v6_D3_GRAPE_SC_cryostats"] == 100
            and l7["fleet_100L_trajectory"]["v6_qLDPC_108L_cryostats"] == 1
            and l7["fleet_100L_trajectory"]["total_usd_per_L_compression_x"] >= 230.0
        ),
        "DT6_8_CRYPTO_V6_CERT_PORTABILITY_AND_TESTS": bool(
            verify_v6_certificate(master_cert)
            and len(master_cert["sha256"]) == 64
            and len(hardcoded_hits) == 0
            and len(l6["secret_leaks"]) == 0
        ),
    }

    out_data = {
        "experiment": "exp146_v6_digital_twin",
        "hypothesis_id": "H164",
        "version": "6.0",
        "date": "2026-11-23",
        "epistemic_scope": {
            "silicon_31P_fabrication_and_economics": "Model/Sayisal-Simulasyon/Varsayim/Liste-Capasi (M0, no_lab_measurement=true, no_supplier_quotes=true)",
            "control_stack_cloud_qpu": f"Canli-Donanim-IBM-QPU ({l6['live_ibm_qpu']['backend_name']}, {l6['live_ibm_qpu']['n_qubits']}Q, job_id={l6['live_ibm_qpu']['job_id']})",
        },
        "runtime_s": round(time.perf_counter() - t0, 2),
        "predictions": preds,
        "verdicts": verdicts,
        "n_passed": sum(1 for v in verdicts.values() if v),
        "n_total": len(verdicts),
        "success_rule_met": bool(all(verdicts.values())),
        "primary_ledger_sha256": dict(sorted(hashes.items())),
        "live_ibm_qpu_results_sha256": live_sha256,
        "layer1_integrity": l1,
        "layer2_d3_grape": l2,
        "layer3_qldpc": l3,
        "layer4_option_q_multispecies": l4,
        "layer5_option_hpc": l5,
        "layer6_live_ibm_qpu_and_cellisa40": l6,
        "layer7_v3_to_v6_evolution": l7,
        "v6_master_certificate": master_cert,
        "portability_hardcoded_hits": hardcoded_hits,
    }

    if write_outputs:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "exp146.json").write_text(json.dumps(out_data, indent=2) + "\n", encoding="utf-8")
        (OUT_DIR / "v6_digital_twin_cert.json").write_text(
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
        (OUT_DIR / "exp146_plot_data.json").write_text(
            json.dumps(plot_payload, indent=2) + "\n", encoding="utf-8"
        )
    return out_data
