"""Zero-Dependency Live Interactive HTML5 Digital Twin Builder (Exp149 / v7.0 Refresh).

Reads all live primary JSONs (Exp128 v7.0, Exp136, Exp140, Exp141, Exp142, Exp143, Exp144,
Exp145/ibm_qpu_live_results, Exp146 cert, Exp147, Exp148, Exp150/s_safety_spec, CAD v6.0,
BOM_DETAILED.csv v7.0, and Exp149 Verilog RTL verification metrics) directly from disk and
emits a deterministic, self-contained single-file HTML5 interactive engineering web
application at ``docs/digital_twin_interactive.html``.

Zero external CDN/HTTP dependencies, zero secrets, zero hardcoded host paths.

Usage:
    PYTHONPATH=src python3 -B experiments/exp149_boed_verilog_rtl_and_interactive_twin/build_interactive_twin.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from rtl_verifier149 import run_full_rtl_verification  # noqa: E402


def _load_json(rel: str) -> dict[str, Any]:
    return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


def collect_live_twin_payload(rtl_res: dict[str, Any] | None = None) -> dict[str, Any]:
    """Assemble deterministic live embedded JSON payload strictly from disk primary artifacts."""
    d128 = _load_json("results/exp128_bom_sensitivity/exp128.json")
    d136 = _load_json("results/exp136_tb_sp3d5s_hyperfine/exp136.json")
    d140 = _load_json("results/exp140_cryo_fpga_boed_mux_readout/exp140.json")
    d141 = _load_json("results/exp141_v5_digital_twin/exp141.json")
    d142 = _load_json("results/exp142_option_q_multispecies_qram/exp142.json")
    d143 = _load_json("results/exp143_d3_grape_m4_and_hpc_decoder/exp143.json")
    d144 = _load_json("results/exp144_qldpc_bivariate_bicycle_m4/exp144.json")
    live_qpu = _load_json("results/exp145_cloud_qpu_ibm_validation/ibm_qpu_live_results.json")
    v6_cert = _load_json("results/exp146_v6_digital_twin/v6_digital_twin_cert.json")
    d147 = _load_json("results/exp147_universal_qldpc_d18_magic_state/exp147.json")
    d148 = _load_json("results/exp148_sb121_quadrupole_echo_qudit/exp148.json")
    d150 = _load_json("results/exp150_industrial_safety_fmea_hazop/exp150.json")
    s_safety = _load_json("results/exp150_industrial_safety_fmea_hazop/s_safety_spec.json")
    cad = _load_json("research/atom_lithography_machine/cad/cad_verification.json")
    rtl = rtl_res or run_full_rtl_verification(write_outputs=False)

    # Aggregate BOM_DETAILED.csv by subsystem live from disk
    bom_by_sub: dict[str, dict[str, Any]] = {}
    with (REPO_ROOT / "research/atom_lithography_machine/BOM_DETAILED.csv").open(
        "r", encoding="utf-8", newline=""
    ) as f:
        for row in csv.DictReader(f):
            sub = row["subsystem"].strip()
            slot = bom_by_sub.setdefault(sub, {"parts": 0, "usd_low": 0.0, "usd_nom": 0.0, "usd_high": 0.0})
            slot["parts"] += 1
            slot["usd_low"] += float(row["usd_low"])
            slot["usd_nom"] += float(row["usd_nom"])
            slot["usd_high"] += float(row["usd_high"])

    # Keep 9 canonical machine subsystems (preserving Exp149 contract) + v7.0 S7.SAFETY metadata
    cad_subs = cad["subsystems"]
    subsystems = [
        {
            "id": "S1",
            "name": "Ion Source, Column & S1.7 Multi-Species",
            "temp": "300 K (HV 14-22 keV)",
            "cad_parts": cad_subs["s1_ion_source_column"]["part_count"],
            "cad_mass_kg": round(cad_subs["s1_ion_source_column"]["mass_kg"], 3),
            "bom_parts": bom_by_sub.get("S1", {}).get("parts", 0),
            "bom_nom_usd": round(bom_by_sub.get("S1", {}).get("usd_nom", 0.0)),
            "rfq": "RFQ-01 + RFQ-09A (S1.7 121Sb Q-Echo-8 / 167Er)",
            "safety": "Exp150 S7.SAFETY-01: Sub-atm SDS PH3 (0.00715 ppm << 0.05 TLV) + 18.3 ms HV crowbar",
        },
        {
            "id": "S2",
            "name": "32x32 MEMS Multi-Beamlet Write Head",
            "temp": "300 K UHV",
            "cad_parts": cad_subs["s2_mems_write_head"]["part_count"],
            "cad_mass_kg": round(cad_subs["s2_mems_write_head"]["mass_kg"], 3),
            "bom_parts": bom_by_sub.get("S2", {}).get("parts", 0),
            "bom_nom_usd": round(bom_by_sub.get("S2", {}).get("usd_nom", 0.0)),
            "rfq": "RFQ-02 (1,024 active + 128 spare blanker channels)",
            "safety": "Blanker watchdog RTL + 5% dead-channel auto-remap (auto_recal.py)",
        },
        {
            "id": "S3",
            "name": "IBIC Single-Ion Detector Frontend",
            "temp": "300 K / Cryo-compatible",
            "cad_parts": cad_subs["s3_ibic_detector_assembly"]["part_count"],
            "cad_mass_kg": round(cad_subs["s3_ibic_detector_assembly"]["mass_kg"], 3),
            "bom_parts": bom_by_sub.get("S3", {}).get("parts", 0),
            "bom_nom_usd": round(bom_by_sub.get("S3", {}).get("usd_nom", 0.0)),
            "rfq": "COTS + Custom ASIC/JFET frontend",
            "safety": "Counted-implantation closed-loop gate (99.9%+ single-ion detection)",
        },
        {
            "id": "S4",
            "name": "6-DOF Piezo Stage & Interferometry",
            "temp": "300 K UHV (Zerodur)",
            "cad_parts": cad_subs["s4_piezo_stage_interferometry"]["part_count"],
            "cad_mass_kg": round(cad_subs["s4_piezo_stage_interferometry"]["mass_kg"], 3),
            "bom_parts": bom_by_sub.get("S4", {}).get("parts", 0),
            "bom_nom_usd": round(bom_by_sub.get("S4", {}).get("usd_nom", 0.0)),
            "rfq": "RFQ-03 (sub-nm laser interferometry + active vibration control)",
            "safety": "CFG4 active decoupling: sigma_total = 3.57 nm <= 3.80 nm",
        },
        {
            "id": "S5",
            "name": "UHV Chamber, S5.5 Flash Anneal & S5.6 MBE",
            "temp": "300 K (1530 K flash, 2e-10 Torr)",
            "cad_parts": cad_subs["s5_uhv_chamber_loadlock"]["part_count"],
            "cad_mass_kg": round(cad_subs["s5_uhv_chamber_loadlock"]["mass_kg"], 3),
            "bom_parts": bom_by_sub.get("S5", {}).get("parts", 0),
            "bom_nom_usd": round(bom_by_sub.get("S5", {}).get("usd_nom", 0.0)),
            "rfq": "RFQ-07 (S5.5 808nm 43.49 J/cm2) + RFQ-08 (S5.6 28Si MBE)",
            "safety": "Exp150 OD=8 + 3 mm steel dual Laser/X-ray model (1.19e-23 uSv/h) + 3.2 ms SIL-3 target shutter (uncertified M0) + 80 ms UHV gate valve",
        },
        {
            "id": "S6",
            "name": "20 mK LD400 DR, 1.5T Magnet & S6.5 Cryo-MUX",
            "temp": "20 mK / 100 mK / 4 K / 50 K",
            "cad_parts": cad_subs["s6_cryo_dr_magnet_readout"]["part_count"],
            "cad_mass_kg": round(cad_subs["s6_cryo_dr_magnet_readout"]["mass_kg"], 3),
            "bom_parts": bom_by_sub.get("S6", {}).get("parts", 0),
            "bom_nom_usd": round(bom_by_sub.get("S6", {}).get("usd_nom", 0.0)),
            "rfq": "RFQ-04/05/06/08 (N_mux*=32, 3 kOhm NbTiN, 2,887 cells/cryo)",
            "safety": "Exp150 Dry-cryo He O2 = 20.57% (>=19.5% OSHA) + DN50 16.4x OVC relief + 64.6 K quench dump",
        },
        {
            "id": "S7",
            "name": "ZU48DR RFSoC, S9.HPC & S7.SAFETY (RFQ-10)",
            "temp": "300 K Rack + Facility Safety (+355 kg)",
            "cad_parts": cad_subs["s7_electronics_rack_interconnect"]["part_count"],
            "cad_mass_kg": round(cad_subs["s7_electronics_rack_interconnect"]["mass_kg"], 3),
            "bom_parts": bom_by_sub.get("S7", {}).get("parts", 0),
            "bom_nom_usd": round(bom_by_sub.get("S7", {}).get("usd_nom", 0.0)),
            "rfq": "RFQ-08 (RFSoC ZU48DR) + RFQ-09B (RDMA) + RFQ-10 (S7.SAFETY $145k, 6 items)",
            "safety": "16-ch Q16.16 BOED RTL (584 cyc) + uncertified M0 SIL-3 target PLC (SEMI S2 / IEC 61508 reference) + 15 kVA UPS (40/213 min), 0 W cryo",
        },
        {
            "id": "S9.4",
            "name": "Option-Q: 50 Ohm <-> 3 kOhm qRAM & 1550 nm Fiber",
            "temp": "20 mK / 4 K (+0.78 uW @ 20 mK)",
            "cad_parts": cad["exp142_s9q_audit"]["s91_part_count"] + cad["exp142_s9q_audit"]["s16_part_count"],
            "cad_mass_kg": cad["exp142_s9q_audit"]["total_mass_kg"],
            "bom_parts": 4,
            "bom_nom_usd": round(d128["bom_detailed_summary"]["v6_option_q_nom_usd"]),
            "rfq": "RFQ-09 Lot 9A (Chebyshev-5 IL=0.0004 dB, F_SWAP=0.9858)",
            "safety": "Passive superconducting NbTiN (0 W standby, 8,403x-25,122x lifetime)",
        },
        {
            "id": "S9.HPC",
            "name": "Option-HPC: 4U 100G RoCEv2 Real-Time QEC Decoder",
            "temp": "300 K (2,195 W, 0.0 W cryo)",
            "cad_parts": cad["exp143_s9hpc_audit"]["part_count"],
            "cad_mass_kg": cad["exp143_s9hpc_audit"]["total_mass_kg"],
            "bom_parts": 3,
            "bom_nom_usd": round(d128["bom_detailed_summary"]["v6_option_hpc_nom_usd"]),
            "rfq": "RFQ-09 Lot 9B (tau_ingest=777 ns, d=37: 6.34 us, qLDPC: 2.32 us)",
            "safety": "Redundant 100G QSFP28 fiber link, backlog-free streaming FIFO",
        },
    ]

    # Extract Exp143 GRAPE grid points for live slider interpolation
    echo_grid = d143["part2_noisy_1f_sweep"]["grape_echoed_exp136_0p0225kHz_nuc"]
    grape_pts = {
        k: {
            "p_2q": float(v["p_total_err"]),
            "F_Bell": float(v["F_Bell"]),
            "F_avg": float(v["F_avg"]),
        }
        for k, v in echo_grid.items()
    }

    # Extract Exp140 N_mux readout table
    mux_tbl = {
        k: {
            "F_ro_2us": float(v["F_ro_at_2us"]),
            "p_meas": round(1.0 - float(v["F_ro_at_2us"]), 6),
        }
        for k, v in d140["mux_readout_3kOhm_NbTiN"]["by_nmux"].items()
    }

    # Extract Exp136 Stark isotope yields
    stark_tbl = [
        {
            "f_pct": float(r["abundance_pct"]),
            "Ez": float(r["E_z_MV_per_m"]),
            "yield": float(r["yield_frac"]),
        }
        for r in d136["stage6_isotope_stark_sweep"]["stark_tuning_yield_HM5962"]
    ]

    # Extract v7.0 live payloads: Exp147 (Universal qLDPC d=18 + FeMoco/RSA-2048), Exp148 (121Sb Q-Echo-8), Exp150 (Safety)
    b128 = d128["bom_detailed_summary"]
    mc7 = d128["v7_modular_mc_comparison"]
    femoco_cult = d147["part5_flagship_algorithms"]["FeMoco_192L_1e8T"]["qLDPC_d18_Gidney_Cult_116to12"]
    femoco_sc = d147["part5_flagship_algorithms"]["FeMoco_192L_1e8T"]["SurfaceCode_D3_Baseline"]
    femoco_comp = d147["part5_flagship_algorithms"]["FeMoco_192L_1e8T"]["compression_vs_SC_Cultivation"]
    rsa_cult = d147["part5_flagship_algorithms"]["RSA2048_4096L_1e10T"]["qLDPC_d24_D3_GidneyCult"]
    rsa_sc = d147["part5_flagship_algorithms"]["RSA2048_4096L_1e10T"]["SurfaceCode_D3_Baseline"]
    rsa_comp = d147["part5_flagship_algorithms"]["RSA2048_4096L_1e10T"]["compression_d24_Cult_vs_SC"]
    p2_147 = d147["part2_m4_layout_and_576_yield"]

    sq3 = d148["verdicts_sq1_to_sq6"]["SQ3_QECHO_CLOSES_EXP142_OQ6_500HZ"]["measured"]
    sq4 = d148["verdicts_sq1_to_sq6"]["SQ4_COLORED_1F_STRAIN_SCALING"]["measured"]
    sq6 = d148["verdicts_sq1_to_sq6"]["SQ6_SU8_GRAPE_LOGICAL_GATES"]["measured"]
    fmea = d150["fmea_summary"]

    return {
        "meta": {
            "version": "v7.1 (TRL 1-2 M0 Conceptual Design & Reduced-Order Multiphysics + RTL + Uncertified Safety Target + Cloud QPU Control Proxy)",
            "v6_cert_sha256": v6_cert["sha256"],
            "cad_version": cad["cad_version"],
            "cad_parts": cad["master_assembly"]["part_count"],
            "cad_mass_kg": round(float(cad["master_assembly"]["total_mass_kg"]), 3),
            "facility_safety_mass_kg": round(float(d128["v7_hardware_mass_reconciliation"]["facility_safety_bom_total_mass_kg"]), 1),
            "total_facility_mass_kg": round(float(d128["v7_hardware_mass_reconciliation"]["total_facility_load_mass_kg"]), 3),
            "cad_clashes": cad["interference_audit"]["solid_clashes"],
            "cad_pairs": cad["interference_audit"]["pairs_checked"],
            "bom_version": b128["bom_version"],
            "bom_parts": b128["total_parts"],
            "rfq9_nom_pct": round(float(d128["rfq_coverage"]["rfq9_nom_share"]) * 100.0, 2),
            "rfq10_nom_pct": round(float(d128["rfq_coverage"]["rfq10_nom_share"]) * 100.0, 2),
            "rfq10_var_pct": round(float(d128["rfq_coverage"]["rfq10_variance_share_mc"]) * 100.0, 2),
            "mxc_cap_cells": d140["cryo_heat_budgets"]["m4_10000_hemt7p8mW"]["single_cryostat_max_cells"],
        },
        "bom_modular": {
            "base_nom": b128["m3_v5_base_nom_usd"],
            "safety_nom": b128["v7_safety_nom_usd"],
            "opt_q_nom": b128["v6_option_q_nom_usd"],
            "opt_hpc_nom": b128["v6_option_hpc_nom_usd"],
            "base_plus_safety_nom": b128["m3_base_plus_safety_nom_usd"],
            "v6_full_nom": b128["m3_v6_full_nom_usd"],
            "v7_full_nom": b128["m3_v7_safety_certified_full_nom_usd"],
            "base_p100m": round(mc7["M3_v5_0_Base"]["P_Program_stoch_gt_100M"] * 100.0, 2),
            "base_safety_p100m": round(mc7["M3_v5_0_Base_Plus_Safety"]["P_Program_stoch_gt_100M"] * 100.0, 2),
            "hpc_p100m": round(mc7["M3_v6_0_Plus_Option_HPC"]["P_Program_stoch_gt_100M"] * 100.0, 2),
            "q_p100m": round(mc7["M3_v6_0_Plus_Option_Q"]["P_Program_stoch_gt_100M"] * 100.0, 2),
            "full_p100m": round(mc7["M3_v6_0_Full_Option_Q_and_HPC"]["P_Program_stoch_gt_100M"] * 100.0, 2),
            "v7_full_p100m": round(mc7["M3_v7_0_Safety_Certified_Full"]["P_Program_stoch_gt_100M"] * 100.0, 2),
            "base_prog_p50_M": round(mc7["M3_v5_0_Base"]["program_stoch_usd"]["p50"] / 1e6, 2),
            "base_safety_prog_p50_M": round(mc7["M3_v5_0_Base_Plus_Safety"]["program_stoch_usd"]["p50"] / 1e6, 2),
            "full_prog_p50_M": round(mc7["M3_v6_0_Full_Option_Q_and_HPC"]["program_stoch_usd"]["p50"] / 1e6, 2),
            "v7_full_prog_p50_M": round(mc7["M3_v7_0_Safety_Certified_Full"]["program_stoch_usd"]["p50"] / 1e6, 2),
        },
        "physics_anchors": {
            "grape_echo_grid": grape_pts,
            "mux_table": mux_tbl,
            "stark_table": stark_tbl,
            "option_q_20mk_uW": d142["part1_qram_bridge"]["cryo_heat_budget"]["option_q_added_load"]["mxc_20mK_uW"],
            "base_1024_20mk_uW": round(
                d142["part1_qram_bridge"]["cryo_heat_budget"]["combined_with_exp140_1024"]["mxc_20mK_uW"]
                - d142["part1_qram_bridge"]["cryo_heat_budget"]["option_q_added_load"]["mxc_20mK_uW"],
                3,
            ),
            "qldpc_bb144": d144["part5_cryostat_and_tco_compression"]["configs"]["BB144_100L_9blk"],
            "qldpc_bb288": d144["part5_cryostat_and_tco_compression"]["configs"]["BB288_100L_9blk_d18_ref"],
            "sc_baselines": d144["part5_cryostat_and_tco_compression"]["surface_code_baselines_exp141"],
            "wafer_v5_daily_cells": {
                "W1": 1_550_000_000,
                "W2": 1_550_000_000,
                "W3": 1_550_000_000,
            },
            "wafer_cost_usd": {"W1": 400.0, "W2": 96.0, "W3": 69.0},
            "v5_d3_lambda_base": d141["v5_master_certificate"]["ft_D3_Lambda"],
        },
        "subsystems": subsystems,
        "live_qpu": {
            "backend": live_qpu["backend"],
            "job": live_qpu["job"],
            "timing_actual": live_qpu["timing_actual"],
            "analysis": live_qpu["analysis"],
        },
        "rtl_fpga": {
            "no_external_eda_sim": rtl["no_external_eda_sim"],
            "lint": rtl["structural_lint"],
            "rom": rtl["rom_verification"],
            "co_ver": rtl["bit_exact_co_verification"],
            "resources": rtl["zu48dr_resource_budget"],
        },
        "v7_algorithms": {
            "bb288_L_max_um": p2_147["layout_by_pitch_um"]["20um"]["L_max_um"],
            "bb288_p_th_pct": round(float(d147["part3_d6_to_d18_circuit_dem"]["uniform_4code_sweep"]["p_th_72_vs_288"]) * 100.0, 3),
            "bb288_yield_576_N8_pct": p2_147["defect_yields_576cell"]["f1p5_Ez2MVm_v5_star"]["by_N_cand"]["N8"]["block_576_yield_pct"],
            "bb288_yield_576_N9_pct": p2_147["defect_yields_576cell"]["f1p5_Ez2MVm_v5_star"]["by_N_cand"]["N9"]["block_576_yield_pct"],
            "exp147_passed": f"{d147['n_passed']}/{d147['n_total']}",
            "femoco": {
                "qldpc_cryos": femoco_cult["total_cryostats_ld400"],
                "sc_cryos": femoco_sc["total_cryostats_ld400"],
                "runtime_hours": femoco_cult["runtime_hours"],
                "power_mw": femoco_cult["tco_and_power"]["total_facility_power_mw"],
                "cost_per_solve_usd": femoco_cult["cost_per_solve_usd_p50"],
                "cryo_compression_x": femoco_comp["cryostats_x"],
                "uq5_honest_note": "UQ5 honest FAIL: 2-3 us readout ceiling (p_meas=0.22-0.39%) requires D3++ (p_2q<=0.20%, p_meas<=0.10%) or d=24 for p_fail_mem<1%",
            },
            "rsa2048": {
                "qldpc_cryos": rsa_cult["total_cryostats_ld400"],
                "sc_cryos": rsa_sc["total_cryostats_ld400"],
                "runtime_hours": rsa_cult["runtime_hours"],
                "power_mw": rsa_cult["tco_and_power"]["total_facility_power_mw"],
                "tco5_musd": rsa_cult["tco_and_power"]["tco5_musd_p50"],
                "cryo_compression_x": rsa_comp["cryostats_x"],
            },
        },
        "v7_sb121": {
            "bare_gross_0L": sq3["bare_gross_0L_1ms"],
            "qecho4_gross_0L": round(float(d148["benchmarks"]["quasistatic_500Hz_1ms"]["qecho4_ideal"]["gross_0L"]), 5),
            "qecho8_gross_0L": sq3["qecho8_finite_neutral_gross_0L_1ms"],
            "infidelity_reduction_x": round((1.0 - sq3["bare_gross_0L_1ms"]) / (1.0 - sq3["qecho8_finite_neutral_gross_0L_1ms"]), 1),
            "bare_cat77": sq3["bare_cat77_1ms"],
            "qecho8_cat77": sq3["qecho8_finite_neutral_cat77_1ms"],
            "min_su8_grape_F_L": sq6["min_F_L_noiseless_full_crosstalk"],
            "t2_gain_qecho8_1f": sq4["T2_gain_qecho8_vs_bare"],
            "t2_gain_qecho64_1f": sq4["T2_gain_qecho64_vs_bare"],
            "t2_qecho64_ms": sq4["qecho64_gross_T2_eff_ms"],
            "exp148_passed": d148["core_sq_passed"],
            "sq4_honest_note": "SQ4 honest physical FAIL for single-cycle Q-Echo-8 under broadband 1/f (8.39x); multi-cycle Q-Echo-64 reaches 28.08x (1.45 ms)",
        },
        "v7_safety": {
            "criteria_passed": d150["criteria_passed"],
            "fmea_rows": fmea["n_rows"],
            "hazop_nodes": len(d150["hazop_10_nodes"]),
            "max_rpn_pre": fmea["max_rpn_pre"],
            "max_rpn_post": fmea["max_rpn_post"],
            "mean_rpn_pre": fmea["mean_rpn_pre"],
            "mean_rpn_post": fmea["mean_rpn_post"],
            "mean_rpn_reduction_pct": fmea["mean_rpn_reduction_pct"],
            "unacceptable_post_gt60": fmea["n_unacceptable_post_gt60"],
            "laser_od_spec": d150["hazard_1_laser_s55"]["specified_enclosure_OD"],
            "shutter_ms": d150["hazard_1_laser_s55"]["interlock_sil3"]["shutter_close_ms"],
            "xray_22kev_shrouded_uSv_h": d150["hazard_3_hv_and_xray"]["energy_sweep"]["22keV"]["s55_sapphire_plus_3mm_steel_shroud_uSv_h"],
            "ph3_operator_ppm": d150["hazard_2_ph3_and_forming_gas"]["mitigated_sds_system"]["operator_direct_sds_diffusive_ppm"],
            "he_o2_60m3_pct": d150["hazard_4_cryo_odh_and_quench"]["helium_odh"]["room_sweep"]["60m3"]["dry_ld400_pt420_O2_pct"],
            "ups_kva": d150["hazard_5_epo_ups_shutdown"]["ups_spec"]["rating_kVA"],
            "ups_full_min": d150["hazard_5_epo_ups_shutdown"]["ups_spec"]["runtime_at_rated_13p5kW_min"],
            "ups_tier1_min": d150["hazard_5_epo_ups_shutdown"]["ups_spec"]["runtime_tier1_min"],
            "uhv_valve_ms": d150["hazard_5_epo_ups_shutdown"]["uhv_isolation"]["gate_valve_close_ms"],
            "kit_totals": s_safety["totals"],
            "kit_items": [
                {
                    "id": it["part_id"],
                    "name": it["name"],
                    "mass_kg": it["mass_kg_total"],
                    "power_W": it["power_W_total"],
                    "nom_usd": it["cost_usd_nom"],
                    "sil": it["sil_level"],
                }
                for it in s_safety["items"]
            ],
        },
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Atom Lithography Machine — Interactive Model Explorer (v7.1, TRL 1-2 / M0)</title>
<style>
  :root {
    --bg: #0b1120;
    --panel: #111827;
    --panel2: #1e293b;
    --border: #334155;
    --text: #f1f5f9;
    --muted: #94a3b8;
    --cyan: #38bdf8;
    --blue: #3b82f6;
    --emerald: #10b981;
    --amber: #f59e0b;
    --coral: #ef4444;
    --purple: #a78bfa;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "DejaVu Sans", sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    min-height: 100vh;
  }
  header {
    background: linear-gradient(135deg, #0f172a 0%, #172554 100%);
    border-bottom: 1px solid var(--border);
    padding: 18px 28px;
  }
  .hdr-top { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
  h1 { font-size: 1.35rem; font-weight: 700; letter-spacing: -0.01em; color: #fff; }
  .badge-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .badge {
    font-size: 0.74rem; font-weight: 600; padding: 4px 10px; border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.18); background: rgba(15,23,42,0.7);
  }
  .badge.live { border-color: var(--emerald); color: #6ee7b7; background: rgba(16,185,129,0.14); }
  .badge.model { border-color: var(--amber); color: #fcd34d; background: rgba(245,158,11,0.14); }
  .badge.rtl { border-color: var(--cyan); color: #7dd3fc; background: rgba(56,189,248,0.14); }
  .badge.safe { border-color: var(--purple); color: #ddd6fe; background: rgba(167,139,250,0.14); }
  .epistemic-banner {
    margin-top: 10px; padding: 8px 14px; border-radius: 8px;
    background: rgba(15, 23, 42, 0.75); border-left: 4px solid var(--amber);
    font-size: 0.80rem; color: #cbd5e1;
  }
  .epistemic-banner strong { color: #fff; }
  nav.tabs {
    display: flex; gap: 6px; padding: 12px 28px 0; background: #0f172a;
    border-bottom: 1px solid var(--border); flex-wrap: wrap;
  }
  .tab-btn {
    padding: 10px 16px; border: 1px solid transparent; border-bottom: none;
    border-radius: 8px 8px 0 0; background: transparent; color: var(--muted);
    font-size: 0.88rem; font-weight: 600; cursor: pointer; transition: all 0.15s;
  }
  .tab-btn:hover { color: #fff; background: rgba(255,255,255,0.04); }
  .tab-btn.active {
    color: var(--cyan); background: var(--bg); border-color: var(--border);
    position: relative; top: 1px;
  }
  main { padding: 22px 28px 40px; max-width: 1480px; margin: 0 auto; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
  .grid-2 { display: grid; grid-template-columns: 375px 1fr; gap: 20px; }
  .grid-even { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
  @media (max-width: 980px) { .grid-2, .grid-even { grid-template-columns: 1fr; } }
  .card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
    padding: 18px 20px;
  }
  .card h2 { font-size: 1.02rem; color: #fff; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
  .card h3 { font-size: 0.86rem; color: var(--cyan); margin: 12px 0 6px; text-transform: uppercase; letter-spacing: 0.04em; }
  .ctrl-group { margin-bottom: 13px; }
  .ctrl-label { display: flex; justify-content: space-between; font-size: 0.83rem; margin-bottom: 5px; color: #cbd5e1; }
  .ctrl-label span.val { font-family: monospace; color: var(--cyan); font-weight: 700; }
  input[type="range"] { width: 100%; accent-color: var(--cyan); cursor: pointer; }
  select {
    width: 100%; padding: 7px 10px; border-radius: 6px; background: var(--panel2);
    color: var(--text); border: 1px solid var(--border); font-size: 0.84rem;
  }
  .chk-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
  .chk-row label {
    display: flex; align-items: center; gap: 6px; font-size: 0.81rem;
    padding: 6px 9px; background: var(--panel2); border: 1px solid var(--border);
    border-radius: 6px; cursor: pointer;
  }
  .preset-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
  .preset-btn {
    padding: 5px 10px; font-size: 0.76rem; font-weight: 600; border-radius: 6px;
    border: 1px solid var(--border); background: #0f172a; color: var(--cyan); cursor: pointer;
  }
  .preset-btn:hover { background: var(--panel2); border-color: var(--cyan); }
  .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px; }
  @media (max-width: 1180px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
  .kpi {
    background: var(--panel2); border: 1px solid var(--border); border-radius: 10px;
    padding: 12px 14px;
  }
  .kpi .k-lbl { font-size: 0.73rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
  .kpi .k-val { font-size: 1.34rem; font-weight: 700; margin: 4px 0 2px; font-family: monospace; }
  .kpi .k-sub { font-size: 0.75rem; color: #cbd5e1; }
  .c-emerald { color: var(--emerald); }
  .c-cyan { color: var(--cyan); }
  .c-amber { color: var(--amber); }
  .c-coral { color: var(--coral); }
  .c-purple { color: var(--purple); }
  canvas { width: 100%; height: auto; display: block; background: #0f172a; border-radius: 8px; border: 1px solid #1e293b; }
  svg.arch-svg { width: 100%; height: auto; background: #0f172a; border-radius: 10px; border: 1px solid #1e293b; }
  .sub-node { cursor: pointer; transition: opacity 0.15s; }
  .sub-node:hover rect { stroke: #38bdf8; stroke-width: 2.6; }
  .sub-node.selected rect { stroke: #10b981; stroke-width: 3.2; filter: drop-shadow(0 0 8px rgba(16,185,129,0.5)); }
  table.spec { width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-top: 8px; }
  table.spec th, table.spec td { padding: 7px 9px; border-bottom: 1px solid var(--border); text-align: left; }
  table.spec th { color: var(--muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }
  table.spec td.num { font-family: monospace; text-align: right; color: var(--cyan); }
  .bar-track { height: 14px; background: #1e293b; border-radius: 7px; overflow: hidden; margin-top: 4px; }
  .bar-fill { height: 100%; border-radius: 7px; }
  .note-box {
    margin-top: 10px; padding: 9px 12px; border-radius: 8px; background: rgba(245,158,11,0.10);
    border-left: 3px solid var(--amber); font-size: 0.79rem; color: #fde68a;
  }
  footer {
    text-align: center; padding: 16px 24px; color: var(--muted); font-size: 0.76rem;
    border-top: 1px solid var(--border); background: #0f172a;
  }
  code.hash { font-family: monospace; font-size: 0.76rem; color: var(--cyan); word-break: break-all; }
</style>
</head>
<body>
<header>
  <div class="hdr-top">
    <div>
      <h1>Atom Lithography Machine — Interactive Model Explorer (v7.1, TRL 1-2 / M0)</h1>
      <div style="font-size:0.81rem;color:#94a3b8;margin-top:3px;">
        Anchored v6.0 Artifact File-Integrity SHA-256 (provenance only): <code class="hash" id="hdr-sha"></code>
      </div>
    </div>
    <div class="badge-row">
      <span class="badge live">CLOUD QPU PROXY: ibm_marrakesh (156Q, Non-Silicon)</span>
      <span class="badge rtl">Verilog RTL: 584 cyc / 2.336 us</span>
      <span class="badge safe">Uncertified M0 Safety Target: RPN 280-&gt;42</span>
      <span class="badge model">Si:31P Fab &amp; BOM v7.0: TRL 1-2 (M0) Model</span>
    </div>
  </div>
  <div class="epistemic-banner">
    <strong>Epistemic Boundary (TRL 1-2 / M0):</strong> Silicon <sup>31</sup>P atom lithography fabrication (S1-S8), CAD v6.0 (199p nominal static geometry only; excl. GD&amp;T/thermal/DFM), BOM v7.0 (180p parametric / 10-RFQ draft, <code>no_supplier_quotes=true</code>), D3 GRAPE, Universal qLDPC d=18 (Exp147), <sup>121</sup>Sb Q-Echo-8 (Exp148), Verilog RTL (<code>no_external_eda_sim=true</code>, Exp149), and Exp150 Preliminary Safety FMEA/HAZOP (uncertified M0 — SEMI does not certify S2; no IEC 61508 SIL assessment) are <strong>conceptual systems-design &amp; reduced-order multiphysics models (M0, no_lab_measurement=true, tapeout_done=false)</strong>. Control-stack execution (CellISA v4.0 -&gt; OpenQASM 3.0), Hahn-Echo/XY4 DD, 5Q d=3 QEC, and bit-exact Q16.16 BOED Ramsey estimation were run on <strong>ibm_marrakesh (156Q Heron r2, job_id=dc1tdo2nj2vs73dfrfl0, 0 secret leaks) as a cloud superconducting-QPU control/decoder proxy</strong> (validates zero silicon <sup>31</sup>P fabrication hardware).
  </div>
</header>

<nav class="tabs">
  <button class="tab-btn active" onclick="openTab('explorer', this)">1. Interactive Parameter &amp; BOM v7.0 Explorer</button>
  <button class="tab-btn" onclick="openTab('schematic', this)">2. Machine Subsystems (S1-S9)</button>
  <button class="tab-btn" onclick="openTab('liveqpu', this)">3. Cloud QPU Control Proxy (ibm_marrakesh 156Q)</button>
  <button class="tab-btn" onclick="openTab('rtl', this)">4. Verilog RTL &amp; 584-Cycle FPGA Pipeline</button>
  <button class="tab-btn" onclick="openTab('v7suite', this)">5. v7.0 Algorithms, 121Sb Q-Echo &amp; M0 Safety Target</button>
</nav>

<main>
  <!-- TAB 1: INTERACTIVE PARAMETER EXPLORER -->
  <section id="tab-explorer" class="tab-panel active">
    <div class="grid-2">
      <div class="card">
        <h2>Physics &amp; BOM v7.0 Controls</h2>
        <div class="ctrl-group">
          <div class="ctrl-label"><span>Charge Noise S_eps (ueV/sqrt(Hz))</span><span class="val" id="v-seps">0.25</span></div>
          <input id="sl-seps" type="range" min="0.15" max="1.00" step="0.01" value="0.25" oninput="updateExplorer()">
          <div style="font-size:0.72rem;color:#94a3b8;">Route C nominal: 0.39 | Optimistic: 0.25 | Unmitigated v4: 1.00</div>
        </div>
        <div class="ctrl-group">
          <div class="ctrl-label"><span>M4 Cavity Quality Factor Q_r</span><span class="val" id="v-qr">1.0e6</span></div>
          <select id="sel-qr" onchange="updateExplorer()">
            <option value="5e5">5.0e5 (v5 Baseline, kappa=10 kHz)</option>
            <option value="1e6" selected>1.0e6 (v6/v7 D3 GRAPE Target, kappa=5 kHz)</option>
          </select>
        </div>
        <div class="ctrl-group">
          <div class="ctrl-label"><span>29Si Isotope &amp; Stark Assist (Exp136)</span><span class="val" id="v-fstar">1.5% + 2 MV/m</span></div>
          <select id="sel-fstar" onchange="updateExplorer()">
            <option value="1.0_0">f = 1.0% (No Stark, yield 33.3%)</option>
            <option value="1.5_2" selected>f* = 1.5% + 2 MV/m Stark (yield 75.6%)</option>
            <option value="2.0_2">f = 2.0% + 2 MV/m Stark (yield 81.2%)</option>
          </select>
        </div>
        <div class="ctrl-group">
          <div class="ctrl-label"><span>Cryo-MUX Ratio N_mux (Exp140)</span><span class="val" id="v-nmux">32</span></div>
          <select id="sel-nmux" onchange="updateExplorer()">
            <option value="8">N_mux = 8 (F_ro = 99.78%)</option>
            <option value="16">N_mux = 16 (F_ro = 99.72%)</option>
            <option value="32" selected>N_mux* = 32 (Optimal, F_ro = 99.61%)</option>
            <option value="64">N_mux = 64 (F_ro = 99.21%)</option>
          </select>
        </div>
        <div class="ctrl-group">
          <div class="ctrl-label"><span>Wafer Pricing Tier (Exp141)</span><span class="val" id="v-wafer">W3 ($69)</span></div>
          <select id="sel-wafer" onchange="updateExplorer()">
            <option value="W1">W1 — Current R&amp;D 28Si ($400 / wafer)</option>
            <option value="W2">W2 — Pilot 28Si Epi ($96 / wafer)</option>
            <option value="W3" selected>W3 — Volume 28Si Epi ($69 / wafer)</option>
          </select>
        </div>
        <div class="ctrl-group">
          <div class="ctrl-label"><span>Fault-Tolerant QEC Code</span><span class="val" id="v-code">qLDPC [[144,12,12]]</span></div>
          <select id="sel-code" onchange="updateExplorer()">
            <option value="SC">Rotated Surface Code (Exp138/143)</option>
            <option value="BB144" selected>qLDPC Gross Code [[144,12,12]] (Exp144)</option>
            <option value="BB288">qLDPC Universal d=18 [[288,12,18]] (Exp147)</option>
          </select>
        </div>
        <div class="ctrl-group">
          <div class="ctrl-label"><span>Modular Hardware Options (BOM v7.0 / 10-RFQ)</span></div>
          <div class="chk-row">
            <label><input type="checkbox" id="chk-safety" checked onchange="updateExplorer()"> +S7.SAFETY (+$145k, 355 kg fac.)</label>
            <label><input type="checkbox" id="chk-optq" onchange="updateExplorer()"> +Option-Q (+$168k, +9.2 kg)</label>
            <label><input type="checkbox" id="chk-opthpc" onchange="updateExplorer()"> +Option-HPC (+$132k, +64.0 kg)</label>
          </div>
          <div class="preset-row">
            <button class="preset-btn" onclick="applyBomPreset(true,false,false)">Phase-1: Base+Safety ($5.39M, 4.67%)</button>
            <button class="preset-btn" onclick="applyBomPreset(true,true,true)">v7.0 Full ($5.69M, 5.22% Phased)</button>
          </div>
        </div>
      </div>

      <div>
        <div class="kpi-grid">
          <div class="kpi"><div class="k-lbl">2Q M4 CZ Fidelity</div><div class="k-val c-emerald" id="k-fbell">99.69%</div><div class="k-sub" id="k-p2q">p_2q = 0.337%</div></div>
          <div class="kpi"><div class="k-lbl">FT Lambda (SC eq.)</div><div class="k-val c-cyan" id="k-lambda">2.825</div><div class="k-sub" id="k-ro">2 us RO F = 99.61%</div></div>
          <div class="kpi"><div class="k-lbl">100L Fleet Cryostats</div><div class="k-val c-emerald" id="k-cryo">1</div><div class="k-sub" id="k-cryo-sub">108L in 1 LD400 (679x vs D2)</div></div>
          <div class="kpi"><div class="k-lbl">Deployed $/L_sys (5y)</div><div class="k-val c-amber" id="k-usdl">$63.8k</div><div class="k-sub" id="k-fabl">Silicon fab: $0.0085/L</div></div>
          <div class="kpi"><div class="k-lbl">M3 Machine BOM (v7.0)</div><div class="k-val c-cyan" id="k-bom">$5.39M</div><div class="k-sub" id="k-p100">P(&gt;$100M) = 4.67% (PASS)</div></div>
          <div class="kpi"><div class="k-lbl">Mass (Frame / Total)</div><div class="k-val" id="k-mass">1,034.9 / 1,389.9 kg</div><div class="k-sub" id="k-parts">173 BOM / 189 CAD + 355 kg fac.</div></div>
          <div class="kpi"><div class="k-lbl">MXC 20 mK Heat Load</div><div class="k-val c-purple" id="k-mxc">6.26 uW</div><div class="k-sub">Limit 14.0 uW (0 W from Safety)</div></div>
          <div class="kpi"><div class="k-lbl">Model Capacity (Assumed Inputs)</div><div class="k-val c-emerald" id="k-daily">1.55B / day</div><div class="k-sub" id="k-blkyld">288-cell block yield: 99.64%</div></div>
        </div>
        <div class="card">
          <h2>Live Architecture Comparison (100L Fleet Cryostats &amp; $/L_sys — Log Scale)</h2>
          <canvas id="cv-explorer" width="960" height="340"></canvas>
        </div>
      </div>
    </div>
  </section>

  <!-- TAB 2: CLICKABLE S1-S9 MACHINE SCHEMATIC -->
  <section id="tab-schematic" class="tab-panel">
    <div class="grid-2" style="grid-template-columns: 1.25fr 1fr;">
      <div class="card">
        <h2>Interactive Atom Lithography Machine Architecture (Click Any Subsystem)</h2>
        <svg class="arch-svg" viewBox="0 0 760 490" id="svg-arch">
          <defs>
            <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b"/>
            </marker>
          </defs>
          <line x1="175" y1="92" x2="175" y2="122" stroke="#64748b" stroke-width="2" marker-end="url(#arr)"/>
          <line x1="175" y1="186" x2="175" y2="216" stroke="#64748b" stroke-width="2" marker-end="url(#arr)"/>
          <line x1="175" y1="280" x2="175" y2="310" stroke="#64748b" stroke-width="2" marker-end="url(#arr)"/>
          <line x1="310" y1="342" x2="365" y2="342" stroke="#38bdf8" stroke-width="2" marker-end="url(#arr)"/>
          <line x1="310" y1="248" x2="365" y2="248" stroke="#f59e0b" stroke-width="2" marker-end="url(#arr)"/>
          <line x1="540" y1="290" x2="540" y2="316" stroke="#a78bfa" stroke-width="2" marker-end="url(#arr)"/>
          <line x1="540" y1="168" x2="540" y2="196" stroke="#10b981" stroke-width="2" marker-end="url(#arr)"/>

          <g class="sub-node selected" data-sub="S1" onclick="selectSub('S1')">
            <rect x="40" y="28" width="270" height="62" rx="10" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>
            <text x="56" y="54" fill="#f8fafc" font-size="14" font-weight="700">S1: Ion Source &amp; Column</text>
            <text x="56" y="74" fill="#94a3b8" font-size="11.5">31P / S1.7 Multi (121Sb Q-Echo, 167Er)</text>
          </g>
          <g class="sub-node" data-sub="S2" onclick="selectSub('S2')">
            <rect x="40" y="124" width="270" height="62" rx="10" fill="#1e293b" stroke="#475569" stroke-width="1.8"/>
            <text x="56" y="150" fill="#f8fafc" font-size="14" font-weight="700">S2: 32x32 MEMS Write Head</text>
            <text x="56" y="170" fill="#94a3b8" font-size="11.5">1,024 active + 128 spare beamlets | Arch B</text>
          </g>
          <g class="sub-node" data-sub="S3" onclick="selectSub('S3')">
            <rect x="40" y="218" width="270" height="62" rx="10" fill="#1e293b" stroke="#475569" stroke-width="1.8"/>
            <text x="56" y="244" fill="#f8fafc" font-size="14" font-weight="700">S3: IBIC Ion Detector</text>
            <text x="56" y="264" fill="#94a3b8" font-size="11.5">Counted single-ion implantation gate</text>
          </g>
          <g class="sub-node" data-sub="S4" onclick="selectSub('S4')">
            <rect x="40" y="312" width="270" height="62" rx="10" fill="#1e293b" stroke="#475569" stroke-width="1.8"/>
            <text x="56" y="338" fill="#f8fafc" font-size="14" font-weight="700">S4: 6-DOF Piezo &amp; Interferometer</text>
            <text x="56" y="358" fill="#94a3b8" font-size="11.5">CFG4 decoupled | sigma_tot = 3.57 nm</text>
          </g>
          <g class="sub-node" data-sub="S5" onclick="selectSub('S5')">
            <rect x="40" y="396" width="270" height="68" rx="10" fill="#1e293b" stroke="#f59e0b" stroke-width="1.8"/>
            <text x="56" y="422" fill="#fcd34d" font-size="14" font-weight="700">S5: UHV + S5.5 Flash + S5.6 MBE</text>
            <text x="56" y="442" fill="#94a3b8" font-size="11.5">OD=8 + 3mm steel | 3.2 ms SIL-3 target (uncert.)</text>
          </g>
          <g class="sub-node" data-sub="S7" onclick="selectSub('S7')">
            <rect x="370" y="28" width="350" height="68" rx="10" fill="#1e293b" stroke="#38bdf8" stroke-width="1.8"/>
            <text x="386" y="54" fill="#7dd3fc" font-size="14" font-weight="700">S7: ZU48DR RFSoC &amp; S7.SAFETY (RFQ-10)</text>
            <text x="386" y="74" fill="#94a3b8" font-size="11.5">16-ch BOED RTL (584 cyc) + Uncert. SIL-3 target (+$145k)</text>
          </g>
          <g class="sub-node" data-sub="S9.HPC" onclick="selectSub('S9.HPC')">
            <rect x="370" y="108" width="350" height="62" rx="10" fill="#1e293b" stroke="#10b981" stroke-width="1.8"/>
            <text x="386" y="134" fill="#6ee7b7" font-size="14" font-weight="700">S9.HPC: Option-HPC 100G RoCEv2</text>
            <text x="386" y="154" fill="#94a3b8" font-size="11.5">+$132k | 64 kg | 2.32 us qLDPC / 6.34 us d=37</text>
          </g>
          <g class="sub-node" data-sub="S6" onclick="selectSub('S6')">
            <rect x="370" y="198" width="350" height="92" rx="10" fill="#172554" stroke="#3b82f6" stroke-width="2"/>
            <text x="386" y="226" fill="#fff" font-size="14.5" font-weight="700">S6: 20 mK LD400 DR + 1.5T Magnet</text>
            <text x="386" y="248" fill="#bfdbfe" font-size="12">S6.5 Cryo-MUX (N_mux*=32, 3 kOhm NbTiN)</text>
            <text x="386" y="268" fill="#93c5fd" font-size="11.5">2,887 cells/cryo | FeMoco: 16 cryos (37.1x)</text>
          </g>
          <g class="sub-node" data-sub="S9.4" onclick="selectSub('S9.4')">
            <rect x="370" y="318" width="350" height="72" rx="10" fill="#1e1b4b" stroke="#a78bfa" stroke-width="1.8"/>
            <text x="386" y="345" fill="#ddd6fe" font-size="14" font-weight="700">S9.4: Option-Q 50 Ohm &lt;-&gt; 3 kOhm qRAM</text>
            <text x="386" y="366" fill="#c4b5fd" font-size="11.5">+$168k | 9.2 kg | +0.78 uW @ 20 mK | 8,403x life</text>
          </g>
          <rect x="370" y="408" width="350" height="56" rx="8" fill="#064e3b" fill-opacity="0.35" stroke="#10b981" stroke-width="1.2"/>
          <text x="545" y="432" text-anchor="middle" fill="#6ee7b7" font-size="12" font-weight="700">CAD v6 Nominal: 199p / 1,108 kg | BOM v7 Parametric: 180p</text>
          <text x="545" y="451" text-anchor="middle" fill="#a7f3d0" font-size="11">0/19,701 static clashes (excl. GD&amp;T/thermal/DFM) | 10-RFQ draft</text>
        </svg>
      </div>
      <div class="card">
        <h2 id="sub-title">Subsystem Inspector</h2>
        <div id="sub-detail"></div>
        <h3>All Subsystems Summary (Nominal CAD v6.0 &amp; Parametric BOM v7.0)</h3>
        <table class="spec" id="tbl-subs"></table>
      </div>
    </div>
  </section>

  <!-- TAB 3: CLOUD QPU CONTROL PROXY (NON-SILICON) -->
  <section id="tab-liveqpu" class="tab-panel">
    <div class="kpi-grid">
      <div class="kpi"><div class="k-lbl">Cloud QPU Proxy (Non-Silicon)</div><div class="k-val c-emerald" id="q-name">ibm_marrakesh</div><div class="k-sub" id="q-job">156Q Heron r2 | 32.54 s (0 Si fab)</div></div>
      <div class="kpi"><div class="k-lbl">Proxy C1 XY4 DD Gain</div><div class="k-val c-cyan" id="q-xy4">+59.55 pp</div><div class="k-sub" id="q-xy4-sub">Bare 0.3325 -&gt; XY4 0.9280</div></div>
      <div class="kpi"><div class="k-lbl">Proxy C1 Bell Fidelity</div><div class="k-val c-emerald" id="q-bell">0.9733</div><div class="k-sub">ZZ=+0.961, XX=+0.972, YY=-0.960</div></div>
      <div class="kpi"><div class="k-lbl">Proxy C3 Q16 vs FP64</div><div class="k-val c-amber" id="q-boed">1.6 Hz</div><div class="k-sub">3 vs 8 pts (2.67x) | drift -4.52 kHz</div></div>
    </div>
    <div class="grid-even">
      <div class="card">
        <h2>C3: Cloud QPU Proxy (ibm_marrakesh) 8-Point Ramsey Fringe &amp; Q16.16 BOED (3 Selected Points)</h2>
        <canvas id="cv-ramsey" width="660" height="340"></canvas>
      </div>
      <div class="card">
        <h2>C1 DD / Bell &amp; C2 5-Qubit Linear d=3 Repetition Code (Superconducting Control Proxy)</h2>
        <canvas id="cv-qpu-bars" width="660" height="340"></canvas>
      </div>
    </div>
  </section>

  <!-- TAB 4: VERILOG RTL & 584-CYCLE FPGA PIPELINE -->
  <section id="tab-rtl" class="tab-panel">
    <div class="kpi-grid">
      <div class="kpi"><div class="k-lbl">BOED Core Latency</div><div class="k-val c-cyan">584 cyc</div><div class="k-sub">2.336 us @ 250 MHz (4.0 ns XDC)</div></div>
      <div class="kpi"><div class="k-lbl">Stage-0 SPRT Abort</div><div class="k-val c-emerald">4 cyc</div><div class="k-sub">16.0 ns early blank-site abort</div></div>
      <div class="kpi"><div class="k-lbl">Synthesis Lint &amp; ROM</div><div class="k-val c-emerald" id="r-lint">0 Errors</div><div class="k-sub" id="r-rom">1,024/1,024 ROM = 0-bit diff</div></div>
      <div class="kpi"><div class="k-lbl">Golden Vectors (N=64)</div><div class="k-val c-emerald" id="r-lsb">0 LSB</div><div class="k-sub">1,000 isqrt + 64 BOED = exact</div></div>
    </div>
    <div class="grid-even">
      <div class="card">
        <h2>boed_q16_core.v — Deterministic 584-Cycle FSM &amp; 4-Lane SIMD Pipeline</h2>
        <canvas id="cv-fsm" width="660" height="300"></canvas>
        <p style="font-size:0.80rem;color:#94a3b8;margin-top:10px;">
          Note: <code>no_external_eda_sim = true</code> (host has no iverilog/verilator/vivado). All 4 synthesizable IEEE 1364-2005 modules pass structural linting (0 forbidden constructs, 0 port/width mismatches) and cycle-accurate Python bit-exact co-verification against <code>fpga_boed_dsp.py</code>.
        </p>
      </div>
      <div class="card">
        <h2>Xilinx ZU48DR RFSoC 16-Channel Utilization (boed_top_16ch.v)</h2>
        <div id="rtl-bars" style="margin-top:8px;"></div>
        <h3>RTL Module &amp; Verification Ledger</h3>
        <table class="spec" id="tbl-rtl"></table>
      </div>
    </div>
  </section>

  <!-- TAB 5: v7.0 UNIVERSAL ALGORITHMS, 121Sb Q-ECHO-8 & PRELIMINARY M0 SAFETY TARGET -->
  <section id="tab-v7suite" class="tab-panel">
    <div class="kpi-grid">
      <div class="kpi"><div class="k-lbl">FeMoco (192L, 10^8 T)</div><div class="k-val c-emerald" id="v7-femoco">16 cryos</div><div class="k-sub" id="v7-femoco-sub">3.38 h | $6,537/calc | 37.1x vs SC</div></div>
      <div class="kpi"><div class="k-lbl">RSA-2048 (4096L, 10^10 T)</div><div class="k-val c-cyan" id="v7-rsa">291 cryos</div><div class="k-sub" id="v7-rsa-sub">7.37 MW | 21.1 h | 52.7x vs SC</div></div>
      <div class="kpi"><div class="k-lbl">121Sb Q-Echo-8 (500 Hz)</div><div class="k-val c-emerald" id="v7-sb">0.99908</div><div class="k-sub" id="v7-sb-sub">0.5800 -&gt; 0.99908 (455.5x infid drop)</div></div>
      <div class="kpi"><div class="k-lbl">Preliminary M0 Safety FMEA</div><div class="k-val c-purple" id="v7-rpn">RPN 280-&gt;42</div><div class="k-sub" id="v7-rpn-sub">-86.3% | 0 residual &gt;60 | Uncertified M0</div></div>
    </div>
    <div class="grid-even">
      <div class="card">
        <h2>Exp147 Universal qLDPC Scaling &amp; Exp148 121Sb Q-Echo-8 Model Iteration</h2>
        <canvas id="cv-v7-alg" width="660" height="330"></canvas>
        <div class="note-box" id="v7-honest-notes"></div>
      </div>
      <div class="card">
        <h2>Exp150 Preliminary Safety-Interlock Design Target (Uncertified M0 — SEMI does not certify S2; no IEC 61508 SIL assessment)</h2>
        <canvas id="cv-v7-safety" width="660" height="175"></canvas>
        <h3>5-Hazard Reduced-Order Model Target &amp; S7.SAFETY-01..06 Parametric BOM ($145k, 355 kg)</h3>
        <table class="spec" id="tbl-safety"></table>
      </div>
    </div>
  </section>
</main>

<footer>
  Atom Lithography Machine v7.1 Interactive Model Explorer (TRL 1-2 / M0) | Zero external CDN dependencies | Embedded JSONs from repository artifacts (Exp128-Exp150) | Zero API tokens/CRNs.
</footer>

<script>
const DATA = __TWIN_JSON_DATA__;

function openTab(id, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  btn.classList.add('active');
  if (id === 'explorer') updateExplorer();
  if (id === 'liveqpu') drawLiveQPU();
  if (id === 'rtl') drawRTL();
  if (id === 'v7suite') drawV7Suite();
}

function applyBomPreset(safety, optq, opthpc) {
  document.getElementById('chk-safety').checked = safety;
  document.getElementById('chk-optq').checked = optq;
  document.getElementById('chk-opthpc').checked = opthpc;
  updateExplorer();
}

function updateExplorer() {
  const sEps = parseFloat(document.getElementById('sl-seps').value);
  const qr = document.getElementById('sel-qr').value;
  const fstar = document.getElementById('sel-fstar').value;
  const nmux = document.getElementById('sel-nmux').value;
  const wafer = document.getElementById('sel-wafer').value;
  const code = document.getElementById('sel-code').value;
  const hasSafety = document.getElementById('chk-safety').checked;
  const optQ = document.getElementById('chk-optq').checked;
  const optHPC = document.getElementById('chk-opthpc').checked;

  document.getElementById('v-seps').textContent = sEps.toFixed(2);
  document.getElementById('v-qr').textContent = qr === '1e6' ? '1.0e6' : '5.0e5';
  document.getElementById('v-fstar').textContent = fstar === '1.5_2' ? '1.5% + 2 MV/m' : (fstar === '2.0_2' ? '2.0% + 2 MV/m' : '1.0% (No Stark)');
  document.getElementById('v-nmux').textContent = nmux;
  document.getElementById('v-wafer').textContent = wafer + ' ($' + DATA.physics_anchors.wafer_cost_usd[wafer] + ')';
  document.getElementById('v-code').textContent = code === 'SC' ? 'Surface Code' : (code === 'BB144' ? 'qLDPC [[144,12,12]]' : 'qLDPC [[288,12,18]]');

  // Physics interpolation anchored to Exp143 GRAPE echo grid
  const g = DATA.physics_anchors.grape_echo_grid;
  const baseKey25 = qr === '1e6' ? 'Q10e5_S0p25' : 'Q5e5_S0p25';
  const baseKey39 = qr === '1e6' ? 'Q10e5_S0p39' : 'Q5e5_S0p39';
  const baseKey50 = qr === '1e6' ? 'Q10e5_S0p50' : 'Q5e5_S0p50';
  let p2q;
  if (sEps <= 0.39) {
    const t = (sEps - 0.25) / 0.14;
    p2q = g[baseKey25].p_2q + t * (g[baseKey39].p_2q - g[baseKey25].p_2q);
  } else {
    const t = (sEps - 0.39) / 0.11;
    p2q = g[baseKey39].p_2q + Math.min(t, 5.5) * (g[baseKey50].p_2q - g[baseKey39].p_2q);
  }
  p2q = Math.max(0.0020, Math.min(0.08, p2q));
  const fBell = Math.max(0.80, 1.0 - 0.93 * p2q);

  const muxEntry = DATA.physics_anchors.mux_table[nmux];
  const fRo = muxEntry.F_ro_2us;
  const pMeas = muxEntry.p_meas;

  const pEff = 0.72 * p2q + 0.28 * pMeas;
  const lam = Math.max(0.45, 0.00985 / Math.max(pEff, 0.0018));

  const pSlot = fstar === '1.5_2' ? 0.75565 : (fstar === '2.0_2' ? 0.812 : 0.3325);
  const pDrop = Math.pow(1.0 - pSlot, 8);
  const nBlkCells = code === 'BB288' ? 576 : 288;
  const blkYld = Math.pow(1.0 - pDrop, nBlkCells) * 100.0;

  let cryos, usdSys, usdFab, cryoSub;
  const wScale = DATA.physics_anchors.wafer_cost_usd[wafer] / 69.0;
  if (code === 'BB144') {
    cryos = p2q <= 0.006 ? 1 : 2;
    usdSys = cryos === 1 ? DATA.physics_anchors.qldpc_bb144.usd_per_logical_sys_amort_wright.p50 : 127650;
    usdFab = DATA.physics_anchors.qldpc_bb144.fab_cost_by_wafer[wafer].usd_per_logical_fab_p50;
    cryoSub = cryos === 1 ? '108L in 1 LD400 (679x vs D2)' : 'Above D3 p_2q -> extra overhead';
  } else if (code === 'BB288') {
    cryos = 2;
    usdSys = DATA.physics_anchors.qldpc_bb288.usd_per_logical_sys_amort_wright.p50;
    usdFab = DATA.physics_anchors.qldpc_bb288.fab_cost_by_wafer[wafer].usd_per_logical_fab_p50;
    cryoSub = '108L d=18 in 2 LD400 (FeMoco: 16 cryos)';
  } else {
    const dStar = lam > 1.05 ? Math.max(15, Math.min(99, Math.round(2 * Math.log(1e-9 / 0.1) / (-Math.log(lam))) | 1)) : 99;
    const cellsPerL = 2 * dStar * dStar - 1;
    cryos = Math.max(10, Math.ceil((100 * cellsPerL) / 2887));
    usdSys = 27594.4 * cryos;
    usdFab = 0.000265 * cellsPerL * wScale;
    cryoSub = 'Surface Code d*=' + dStar + ' (' + cellsPerL.toLocaleString() + ' cells/L)';
  }

  // Modular BOM v7.0 (including S7.SAFETY +$145k / 355 kg facility kit)
  const bm = DATA.bom_modular;
  const bomNom = bm.base_nom + (hasSafety ? bm.safety_nom : 0) + (optQ ? bm.opt_q_nom : 0) + (optHPC ? bm.opt_hpc_nom : 0);
  let p100m;
  if (hasSafety) {
    if (optQ && optHPC) p100m = bm.v7_full_p100m;
    else if (optQ) p100m = +(bm.q_p100m + (bm.base_safety_p100m - bm.base_p100m)).toFixed(2);
    else if (optHPC) p100m = +(bm.hpc_p100m + (bm.base_safety_p100m - bm.base_p100m)).toFixed(2);
    else p100m = bm.base_safety_p100m;
  } else {
    p100m = (optQ && optHPC) ? bm.full_p100m : (optQ ? bm.q_p100m : (optHPC ? bm.hpc_p100m : bm.base_p100m));
  }
  const frameMass = 1034.937 + (optQ ? 9.2 : 0) + (optHPC ? 64.0 : 0);
  const facMass = hasSafety ? 355.0 : 0.0;
  const partsBom = 167 + (hasSafety ? 6 : 0) + (optQ ? 4 : 0) + (optHPC ? 3 : 0);
  const partsCad = 189 + (optQ ? 5 : 0) + (optHPC ? 5 : 0);
  const mxcUw = DATA.physics_anchors.base_1024_20mk_uW + (optQ ? DATA.physics_anchors.option_q_20mk_uW : 0);

  document.getElementById('k-fbell').textContent = (fBell * 100).toFixed(2) + '%';
  document.getElementById('k-p2q').textContent = 'p_2q = ' + (p2q * 100).toFixed(3) + '%';
  document.getElementById('k-lambda').textContent = lam.toFixed(3);
  document.getElementById('k-lambda').className = 'k-val ' + (lam >= 2.2 ? 'c-emerald' : (lam >= 1.2 ? 'c-amber' : 'c-coral'));
  document.getElementById('k-ro').textContent = '2 us RO F = ' + (fRo * 100).toFixed(2) + '%';
  document.getElementById('k-cryo').textContent = cryos.toLocaleString();
  document.getElementById('k-cryo-sub').textContent = cryoSub;
  document.getElementById('k-usdl').textContent = usdSys >= 1e6 ? ('$' + (usdSys / 1e6).toFixed(2) + 'M') : ('$' + (usdSys / 1e3).toFixed(1) + 'k');
  document.getElementById('k-fabl').textContent = 'Silicon fab (' + wafer + '): $' + usdFab.toFixed(4) + '/L';
  document.getElementById('k-bom').textContent = '$' + (bomNom / 1e6).toFixed(2) + 'M';
  const p100El = document.getElementById('k-p100');
  if (p100m < 5.0) {
    p100El.textContent = 'P(>$100M) = ' + p100m.toFixed(2) + '% (<5% PASS)';
    p100El.style.color = '#6ee7b7';
  } else {
    p100El.textContent = 'P(>$100M) = ' + p100m.toFixed(2) + '% (>5% Phased)';
    p100El.style.color = '#fcd34d';
  }
  document.getElementById('k-mass').textContent = facMass > 0
    ? (frameMass.toFixed(1) + ' + 355 kg')
    : (frameMass.toFixed(1) + ' kg');
  document.getElementById('k-parts').textContent = partsBom + ' BOM / ' + partsCad + ' CAD' + (facMass > 0 ? ' + fac.' : '');
  document.getElementById('k-mxc').textContent = mxcUw.toFixed(2) + ' uW';
  document.getElementById('k-blkyld').textContent = nBlkCells + '-cell block yield (N8): ' + blkYld.toFixed(2) + '%';

  drawExplorerChart(cryos, usdSys);
}

function drawExplorerChart(liveCryo, liveUsd) {
  const cv = document.getElementById('cv-explorer');
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#0f172a';
  ctx.fillRect(0, 0, W, H);

  const items = [
    { lbl: 'v5 D2 SC', cryo: 679, usd: 14.94e6, col: '#ef4444' },
    { lbl: 'v6 D3 GRAPE SC', cryo: 100, usd: 2.76e6, col: '#f59e0b' },
    { lbl: 'v6 qLDPC BB144', cryo: 1, usd: 63827, col: '#10b981' },
    { lbl: 'Selected Config', cryo: liveCryo, usd: liveUsd, col: '#38bdf8' }
  ];

  function drawBars(ox, bwArea, title, getter, minV, maxV, fmt) {
    ctx.fillStyle = '#e2e8f0';
    ctx.font = '700 14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(title, ox + bwArea / 2, 26);

    const py = 48, ph = H - 102;
    const lmin = Math.log10(minV), lmax = Math.log10(maxV);
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i++) {
      const y = py + (ph * i) / 3;
      ctx.beginPath(); ctx.moveTo(ox, y); ctx.lineTo(ox + bwArea, y); ctx.stroke();
    }
    const gw = bwArea / items.length;
    const bw = Math.min(62, gw * 0.58);
    items.forEach((it, idx) => {
      const val = Math.max(minV, getter(it));
      const frac = Math.max(0.05, Math.min(1.0, (Math.log10(val) - lmin) / (lmax - lmin)));
      const bh = ph * frac;
      const cx = ox + (idx + 0.5) * gw;
      ctx.fillStyle = it.col;
      ctx.fillRect(cx - bw / 2, py + ph - bh, bw, bh);
      ctx.fillStyle = '#fff';
      ctx.font = '700 12.5px monospace';
      ctx.fillText(fmt(getter(it)), cx, py + ph - bh - 7);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '600 11.5px sans-serif';
      ctx.fillText(it.lbl, cx, py + ph + 20);
    });
  }
  drawBars(34, 410, '100L Fleet Cryostats (log scale)', x => x.cryo, 0.5, 1500, v => String(v));
  drawBars(514, 410, '5-yr Deployed $/L_sys (log scale)', x => x.usd, 2e4, 3e7, v => v >= 1e6 ? ('$' + (v/1e6).toFixed(2) + 'M') : ('$' + (v/1e3).toFixed(1) + 'k'));
}

function selectSub(id) {
  document.querySelectorAll('.sub-node').forEach(n => n.classList.toggle('selected', n.dataset.sub === id));
  const s = DATA.subsystems.find(x => x.id === id) || DATA.subsystems[0];
  document.getElementById('sub-title').textContent = s.id + ' — ' + s.name;
  document.getElementById('sub-detail').innerHTML = `
    <div class="kpi-grid" style="grid-template-columns:repeat(3,1fr);margin-bottom:10px;">
      <div class="kpi"><div class="k-lbl">CAD v6 Mass</div><div class="k-val c-cyan">${s.cad_mass_kg} kg</div><div class="k-sub">${s.cad_parts} CAD solids</div></div>
      <div class="kpi"><div class="k-lbl">BOM v7 Nom</div><div class="k-val c-emerald">$${(s.bom_nom_usd/1e3).toFixed(1)}k</div><div class="k-sub">${s.bom_parts} BOM lines</div></div>
      <div class="kpi"><div class="k-lbl">Thermal Stage</div><div class="k-val" style="font-size:0.92rem;">${s.temp}</div><div class="k-sub">Model design target</div></div>
    </div>
    <p style="font-size:0.84rem;color:#cbd5e1;margin-bottom:6px;"><strong>RFQ Scope:</strong> ${s.rfq}</p>
    <p style="font-size:0.84rem;color:#94a3b8;"><strong>Safety &amp; Control:</strong> ${s.safety}</p>
  `;
}

function drawLiveQPU() {
  const q = DATA.live_qpu;
  const c1 = q.analysis.C1_dd_and_bell;
  const c2 = q.analysis.C2_repcode3;
  const c3 = q.analysis.C3_ramsey_boed;

  const cv = document.getElementById('cv-ramsey');
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.fillStyle = '#0f172a'; ctx.fillRect(0, 0, W, H);
  const px = 64, py = 30, pw = W - 94, ph = H - 82;
  const mx = t => px + pw * (t / 8.5);
  const my = v => py + ph * (1 - (v + 0.04) / 1.10);

  ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 1;
  [0, 0.25, 0.5, 0.75, 1.0].forEach(v => {
    ctx.beginPath(); ctx.moveTo(px, my(v)); ctx.lineTo(px + pw, my(v)); ctx.stroke();
    ctx.fillStyle = '#94a3b8'; ctx.font = '11px monospace'; ctx.textAlign = 'right';
    ctx.fillText(v.toFixed(2), px - 8, my(v) + 4);
  });
  for (let t = 0; t <= 8; t++) {
    ctx.fillStyle = '#94a3b8'; ctx.font = '11px monospace'; ctx.textAlign = 'center';
    ctx.fillText(t + ' us', mx(t), py + ph + 18);
  }
  ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 2.5; ctx.beginPath();
  for (let s = 0; s <= 160; s++) {
    const t = 0.2 + 8.1 * s / 160;
    const v = 0.5 * (1 + c3.visibility_est * Math.exp(-t / 120) * Math.cos(2 * Math.PI * c3.blind_8pt.est_freq_kHz * 1e-3 * t));
    if (s === 0) ctx.moveTo(mx(t), my(v)); else ctx.lineTo(mx(t), my(v));
  }
  ctx.stroke();

  const selSet = new Set(c3.q16_16_boed.queried_indices);
  c3.delays_us.forEach((t, i) => {
    const p = c3.p0_measured[i];
    ctx.beginPath();
    ctx.arc(mx(t), my(p), selSet.has(i) ? 8.5 : 5.5, 0, Math.PI * 2);
    ctx.fillStyle = selSet.has(i) ? '#f59e0b' : '#3b82f6';
    ctx.fill();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.6; ctx.stroke();
  });
  ctx.fillStyle = '#fcd34d'; ctx.font = '700 12px monospace'; ctx.textAlign = 'center';
  ctx.fillText('Gold = 3 Q16.16 BOED points (120.106 kHz, 1.6 Hz vs FP64) | Blue = 8 live ibm_marrakesh PUBs', px + pw/2, H - 14);

  const cv2 = document.getElementById('cv-qpu-bars');
  const ctx2 = cv2.getContext('2d');
  ctx2.fillStyle = '#0f172a'; ctx2.fillRect(0, 0, W, H);
  const bars = [
    { l: 'C1 Bare', v: c1.p0_bare_idle, col: '#64748b', t: c1.p0_bare_idle.toFixed(3) },
    { l: 'C1 Echo', v: c1.p0_hahn_echo, col: '#3b82f6', t: c1.p0_hahn_echo.toFixed(3) },
    { l: 'C1 XY4', v: c1.p0_xy4_dd, col: '#06b6d4', t: c1.p0_xy4_dd.toFixed(3) },
    { l: 'C1 Bell F', v: c1.bell_fidelity_Phi_plus, col: '#10b981', t: c1.bell_fidelity_Phi_plus.toFixed(3) },
    { l: 'C2 1-p_phys', v: 1 - c2.avg_p_phys, col: '#f59e0b', t: 'err ' + (c2.avg_p_phys*100).toFixed(2) + '%' },
    { l: 'C2 1-p_maj', v: 1 - c2.avg_p_L_majority, col: '#10b981', t: 'err ' + (c2.avg_p_L_majority*100).toFixed(2) + '%' }
  ];
  const gw = (W - 60) / bars.length;
  bars.forEach((b, i) => {
    const x = 30 + (i + 0.5) * gw;
    const bh = (H - 100) * b.v;
    ctx2.fillStyle = b.col;
    ctx2.fillRect(x - 28, H - 56 - bh, 56, bh);
    ctx2.fillStyle = '#fff'; ctx2.font = '700 11.5px monospace'; ctx2.textAlign = 'center';
    ctx2.fillText(b.t, x, H - 64 - bh);
    ctx2.fillStyle = '#cbd5e1'; ctx2.font = '600 11px sans-serif';
    ctx2.fillText(b.l, x, H - 34);
  });
  ctx2.fillStyle = '#6ee7b7'; ctx2.font = '700 12px monospace'; ctx2.textAlign = 'center';
  ctx2.fillText('Live C2 Post-Sel: 0.000% error (0 / 7,451 shots, 91.0% keep) | Chain [2,3,4,5,6] (0 SWAPs)', W / 2, H - 10);
}

function drawRTL() {
  const cv = document.getElementById('cv-fsm');
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.fillStyle = '#0f172a'; ctx.fillRect(0, 0, W, H);

  ctx.fillStyle = '#e2e8f0'; ctx.font = '700 13px sans-serif'; ctx.textAlign = 'left';
  ctx.fillText('Stage-0 SPRT Early-Abort Pipeline (4 cycles = 16.0 ns @ 250 MHz)', 24, 34);
  const sprtW = 580;
  ['C1: Sub', 'C2: DSP48 Mul', 'C3: Q16 Shift', 'C4: LLR+Cmp'].forEach((s, i) => {
    ctx.fillStyle = '#0ea5e9';
    ctx.fillRect(24 + i * (sprtW / 4), 46, sprtW / 4 - 6, 32);
    ctx.fillStyle = '#0b1120'; ctx.font = '700 11.5px monospace'; ctx.textAlign = 'center';
    ctx.fillText(s, 24 + (i + 0.5) * (sprtW / 4) - 3, 66);
  });

  ctx.fillStyle = '#e2e8f0'; ctx.font = '700 13px sans-serif'; ctx.textAlign = 'left';
  ctx.fillText('Stage-2 BOED 4-Lane SIMD FSM (Total = 584 cycles = 2.336 us @ 250 MHz)', 24, 120);
  const phases = [
    { name: 'S_PASS1', cyc: 263, col: '#3b82f6' },
    { name: 'S_PASS2', cyc: 265, col: '#10b981' },
    { name: 'S_POST', cyc: 56, col: '#f59e0b' }
  ];
  let cx = 24;
  const totW = W - 48;
  phases.forEach(p => {
    const pw = totW * (p.cyc / 584);
    ctx.fillStyle = p.col;
    ctx.fillRect(cx, 136, pw - 4, 68);
    ctx.fillStyle = '#fff'; ctx.font = '700 13px monospace'; ctx.textAlign = 'center';
    ctx.fillText(p.cyc + ' cyc', cx + pw / 2 - 2, 166);
    ctx.font = '600 10.5px sans-serif';
    ctx.fillText((p.cyc * 4) + ' ns', cx + pw / 2 - 2, 186);
    cx += pw;
  });
  ctx.fillStyle = '#94a3b8'; ctx.font = '12px monospace'; ctx.textAlign = 'left';
  ctx.fillText('Pass 1: 251 beats (4 lanes) + 12 pipe = 263 cyc  |  Pass 2: 251 beats + 14 pipe = 265 cyc', 24, 232);
  ctx.fillText('Post  : 32 cyc floor-div + 16-stage pipelined isqrt + 8 cyc Fisher argmax = 56 cyc', 24, 254);
  ctx.fillStyle = '#6ee7b7'; ctx.font = '700 12.5px monospace';
  ctx.fillText('TOTAL = 263 + 265 + 56 = 584 clock cycles = 2,336 ns (2.336 us) | 0-LSB vs fpga_boed_dsp.py', 24, 282);

  const res = DATA.rtl_fpga.resources.total_16ch;
  const rows = [
    ['DSP48E2 (16 ch)', res.dsp48e2 + ' / 4,272', res.dsp48e2_pct, '#38bdf8'],
    ['BRAM36  (16 ch)', res.bram36 + ' / 1,080', res.bram36_pct, '#10b981'],
    ['CLB LUT (16 ch)', res.lut.toLocaleString() + ' / 425,280', res.lut_pct, '#a78bfa'],
    ['Flip-Flop (16 ch)', res.ff.toLocaleString() + ' / 850,560', res.ff_pct, '#f59e0b']
  ];
  document.getElementById('rtl-bars').innerHTML = rows.map(r => `
    <div style="margin-bottom:10px;">
      <div class="ctrl-label"><span>${r[0]}</span><span class="val">${r[1]} (${r[2]}%)</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, r[2]*3)}%;background:${r[3]};"></div></div>
    </div>
  `).join('');
}

function drawV7Suite() {
  const alg = DATA.v7_algorithms;
  const sb = DATA.v7_sb121;
  const sf = DATA.v7_safety;

  document.getElementById('v7-femoco').textContent = alg.femoco.qldpc_cryos + ' cryos';
  document.getElementById('v7-femoco-sub').textContent = alg.femoco.runtime_hours.toFixed(2) + ' h | $' + Math.round(alg.femoco.cost_per_solve_usd).toLocaleString() + '/calc | ' + alg.femoco.cryo_compression_x.toFixed(1) + 'x vs SC';
  document.getElementById('v7-rsa').textContent = alg.rsa2048.qldpc_cryos + ' cryos';
  document.getElementById('v7-rsa-sub').textContent = alg.rsa2048.power_mw.toFixed(2) + ' MW | ' + alg.rsa2048.runtime_hours.toFixed(1) + ' h | ' + alg.rsa2048.cryo_compression_x.toFixed(1) + 'x vs SC';
  document.getElementById('v7-sb').textContent = sb.qecho8_gross_0L.toFixed(5);
  document.getElementById('v7-sb-sub').textContent = sb.bare_gross_0L.toFixed(4) + ' -> ' + sb.qecho8_gross_0L.toFixed(5) + ' (' + sb.infidelity_reduction_x.toFixed(1) + 'x drop)';
  document.getElementById('v7-rpn').textContent = 'RPN ' + sf.max_rpn_pre + '->' + sf.max_rpn_post;
  document.getElementById('v7-rpn-sub').textContent = '-' + sf.mean_rpn_reduction_pct.toFixed(1) + '% | 0 >60 | Uncertified M0 | ' + sf.criteria_passed + ' PASS';

  // Canvas 1: Left = FeMoco & RSA-2048 Cryostat Compression (log10), Right = 121Sb Q-Echo-8 Fidelity Restoration
  const cv = document.getElementById('cv-v7-alg');
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.fillStyle = '#0f172a'; ctx.fillRect(0, 0, W, H);

  // Left half: Algorithms log10 cryostats
  const algBars = [
    { l: 'FeMoco SC', v: alg.femoco.sc_cryos, col: '#ef4444' },
    { l: 'FeMoco qLDPC', v: alg.femoco.qldpc_cryos, col: '#10b981' },
    { l: 'RSA SC', v: alg.rsa2048.sc_cryos, col: '#f59e0b' },
    { l: 'RSA qLDPC', v: alg.rsa2048.qldpc_cryos, col: '#38bdf8' }
  ];
  ctx.fillStyle = '#e2e8f0'; ctx.font = '700 12.5px sans-serif'; ctx.textAlign = 'center';
  ctx.fillText('Cryostats (log scale): 37.1x & 52.7x Compression', 175, 24);
  const py = 46, ph = H - 100;
  algBars.forEach((b, i) => {
    const cx = 36 + i * 74 + 30;
    const frac = Math.max(0.08, (Math.log10(b.v) - 0.8) / (Math.log10(25000) - 0.8));
    const bh = ph * frac;
    ctx.fillStyle = b.col;
    ctx.fillRect(cx - 22, py + ph - bh, 44, bh);
    ctx.fillStyle = '#fff'; ctx.font = '700 11px monospace';
    ctx.fillText(b.v.toLocaleString(), cx, py + ph - bh - 6);
    ctx.fillStyle = '#94a3b8'; ctx.font = '600 10px sans-serif';
    ctx.fillText(b.l, cx, py + ph + 16);
  });

  // Right half: 121Sb Q-Echo-8 Fidelity
  ctx.fillStyle = '#e2e8f0'; ctx.font = '700 12.5px sans-serif'; ctx.textAlign = 'center';
  ctx.fillText('121Sb (500 Hz, 1 ms): 455.5x Infidelity Drop', 500, 24);
  const sbBars = [
    { l: 'Bare Gross', v: sb.bare_gross_0L, col: '#ef4444' },
    { l: 'Q-Echo-4', v: sb.qecho4_gross_0L, col: '#f59e0b' },
    { l: 'Q-Echo-8', v: sb.qecho8_gross_0L, col: '#10b981' },
    { l: 'Cat +-7/2', v: sb.qecho8_cat77, col: '#a78bfa' }
  ];
  sbBars.forEach((b, i) => {
    const cx = 365 + i * 72 + 28;
    const bh = ph * b.v;
    ctx.fillStyle = b.col;
    ctx.fillRect(cx - 21, py + ph - bh, 42, bh);
    ctx.fillStyle = '#fff'; ctx.font = '700 10.5px monospace';
    ctx.fillText(b.v.toFixed(4), cx, py + ph - bh - 6);
    ctx.fillStyle = '#94a3b8'; ctx.font = '600 10px sans-serif';
    ctx.fillText(b.l, cx, py + ph + 16);
  });
  ctx.fillStyle = '#6ee7b7'; ctx.font = '700 11px monospace'; ctx.textAlign = 'center';
  ctx.fillText('BB288 L_max=' + alg.bb288_L_max_um + ' um | p_th=' + alg.bb288_p_th_pct + '% | SU(8) GRAPE min F_L=' + sb.min_su8_grape_F_L.toFixed(4), W/2, H - 12);

  document.getElementById('v7-honest-notes').innerHTML =
    '<strong>Honest Physical Boundaries:</strong> (1) ' + alg.femoco.uq5_honest_note + '. (2) ' + sb.sq4_honest_note + '.';

  // Canvas 2: Safety FMEA RPN Pre vs Post horizontal bars
  const cv2 = document.getElementById('cv-v7-safety');
  const ctx2 = cv2.getContext('2d');
  const W2 = cv2.width, H2 = cv2.height;
  ctx2.fillStyle = '#0f172a'; ctx2.fillRect(0, 0, W2, H2);
  ctx2.fillStyle = '#e2e8f0'; ctx2.font = '700 12.5px sans-serif'; ctx2.textAlign = 'left';
  ctx2.fillText('25-Row Preliminary M0 FMEA Target (Residual RPN <= 60; Uncertified)', 20, 24);
  const rpnRows = [
    { lbl: 'Max RPN Pre-Mitigation', v: sf.max_rpn_pre, col: '#ef4444' },
    { lbl: 'Mean RPN Pre (25 rows)', v: sf.mean_rpn_pre, col: '#f59e0b' },
    { lbl: 'Max RPN Post (M0 FMEA Target)', v: sf.max_rpn_post, col: '#10b981' },
    { lbl: 'Mean RPN Post (-86.3%)', v: sf.mean_rpn_post, col: '#38bdf8' }
  ];
  rpnRows.forEach((r, i) => {
    const y = 42 + i * 31;
    ctx2.fillStyle = '#cbd5e1'; ctx2.font = '600 11px sans-serif'; ctx2.textAlign = 'left';
    ctx2.fillText(r.lbl, 20, y + 14);
    const bx = 205, bw = (W2 - 285) * (r.v / 300.0);
    ctx2.fillStyle = '#1e293b'; ctx2.fillRect(bx, y + 2, W2 - 285, 18);
    ctx2.fillStyle = r.col; ctx2.fillRect(bx, y + 2, bw, 18);
    ctx2.fillStyle = '#fff'; ctx2.font = '700 11.5px monospace'; ctx2.textAlign = 'left';
    ctx2.fillText(String(r.v), bx + bw + 8, y + 15);
  });
  // Threshold line at RPN = 60
  const tx60 = 205 + (W2 - 285) * (60.0 / 300.0);
  ctx2.strokeStyle = '#6ee7b7'; ctx2.setLineDash([4, 3]); ctx2.lineWidth = 1.5;
  ctx2.beginPath(); ctx2.moveTo(tx60, 36); ctx2.lineTo(tx60, H2 - 8); ctx2.stroke();
  ctx2.setLineDash([]);

  document.getElementById('tbl-safety').innerHTML = `
    <tr><th>Safety Domain / Kit Item</th><th class="num">Model Target</th><th class="num">SIL Target (Uncertified) / Cost</th></tr>
    <tr><td>S5.5 Laser + 22 keV X-Ray Shroud</td><td class="num">OD=${sf.laser_od_spec} + 3mm (${sf.xray_22kev_shrouded_uSv_h.toExponential(2)} uSv/h)</td><td class="num">SIL-3 target (uncertified M0, ${sf.shutter_ms} ms)</td></tr>
    <tr><td>S1.1 Sub-Atm SDS PH3 Cabinet</td><td class="num">${sf.ph3_operator_ppm.toFixed(5)} ppm (&lt;&lt;0.05 TLV)</td><td class="num">SIL-3 target (uncertified M0, $42k)</td></tr>
    <tr><td>S6 Dry-Cryo He ODH (60 m3 room)</td><td class="num">O2 = ${sf.he_o2_60m3_pct.toFixed(2)}% (&gt;=19.5% OSHA)</td><td class="num">SIL-2 target (uncertified, $12k)</td></tr>
    <tr><td>15 kVA Online UPS + UHV Gate Valve</td><td class="num">${sf.ups_full_min}/${sf.ups_tier1_min.toFixed(0)} min | ${sf.uhv_valve_ms} ms valve</td><td class="num">SIL-2 target (uncertified, $36k)</td></tr>
    <tr><td><strong>S7.SAFETY Total (6 Items, RFQ-10 Draft)</strong></td><td class="num"><strong>${sf.kit_totals.total_mass_kg} kg | ${sf.kit_totals.steady_electrical_power_W} W | 0 W cryo</strong></td><td class="num"><strong>$${(sf.kit_totals.cost_usd_nom/1e3).toFixed(0)}k</strong></td></tr>
  `;
}

// Init
document.getElementById('hdr-sha').textContent = DATA.meta.v6_cert_sha256;
document.getElementById('tbl-subs').innerHTML =
  '<tr><th>ID</th><th>Subsystem</th><th class="num">CAD kg</th><th class="num">BOM $k</th></tr>' +
  DATA.subsystems.map(s => `<tr style="cursor:pointer" onclick="selectSub('${s.id}')"><td><strong>${s.id}</strong></td><td>${s.name}</td><td class="num">${s.cad_mass_kg}</td><td class="num">$${(s.bom_nom_usd/1e3).toFixed(1)}k</td></tr>`).join('');
const lint = DATA.rtl_fpga.lint;
const co = DATA.rtl_fpga.co_ver;
document.getElementById('tbl-rtl').innerHTML = `
  <tr><th>Check</th><th class="num">Measured</th></tr>
  <tr><td>Synthesizable RTL Files (IEEE-2005)</td><td class="num">${lint.synth_files_checked.length} files (${lint.total_rtl_loc} LOC)</td></tr>
  <tr><td>Forbidden Constructs / Port / Width Errors</td><td class="num">${lint.forbidden_construct_count} / ${lint.port_error_count} / ${lint.width_mismatch_count}</td></tr>
  <tr><td>BRAM ROM .hex Words Verified (0-bit diff)</td><td class="num">${DATA.rtl_fpga.rom.total_words_checked} / 1,024</td></tr>
  <tr><td>Golden Vectors (N=64) Max LSB Error</td><td class="num">${co.max_mu_off_q8_lsb_err} LSB</td></tr>
  <tr><td>16-Stage isqrt (N=1,000) Max LSB Error</td><td class="num">${co.isqrt_max_lsb_err} LSB</td></tr>
  <tr><td>ZU48DR XDC Clock Constraint</td><td class="num">${lint.xdc_checks.create_clock_period_ns.toFixed(3)} ns (${lint.xdc_checks.target_freq_MHz} MHz)</td></tr>
`;
selectSub('S1');
updateExplorer();
drawV7Suite();
</script>
</body>
</html>
"""


def build_interactive_twin_html(
    out_path: Path | None = None,
    rtl_res: dict[str, Any] | None = None,
    write_outputs: bool = True,
) -> dict[str, Any]:
    """Generate deterministic self-contained docs/digital_twin_interactive.html (read-only verify if write_outputs=False)."""
    payload = collect_live_twin_payload(rtl_res=rtl_res)
    json_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    json_str = json_str.replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__TWIN_JSON_DATA__", json_str)

    target = out_path or (REPO_ROOT / "docs" / "digital_twin_interactive.html")
    if write_outputs:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
    elif target.is_file():
        disk_html = target.read_text(encoding="utf-8")
        assert disk_html == html, "docs/digital_twin_interactive.html on disk differs from deterministic build"

    low = html.lower()
    has_external_cdn = any(
        pat in low for pat in ("https://", "http://", "cdn.jsdelivr", "unpkg.com", "fonts.googleapis")
    )
    return {
        "html_path": str(target.relative_to(REPO_ROOT)),
        "size_bytes": len(html.encode("utf-8")),
        "zero_external_cdn": not has_external_cdn,
        "embedded_subsystems": len(payload["subsystems"]),
        "embedded_live_qpu_backend": payload["live_qpu"]["backend"]["name"],
        "embedded_v6_sha256": payload["meta"]["v6_cert_sha256"],
    }


if __name__ == "__main__":
    info = build_interactive_twin_html()
    print(json.dumps(info, indent=2))
