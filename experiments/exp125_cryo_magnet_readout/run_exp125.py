"""Exp125 Orchestrator: Risk R7 Magnet/Shield Closure + Unified 5-Stage Cryo/RF/Throughput + Risk R8 Valley Bound.

Run with: python3 -B experiments/exp125_cryo_magnet_readout/run_exp125.py
Outputs:
  - results/exp125_cryo_magnet_readout/exp125.json
  - results/exp125_cryo_magnet_readout/plot_data_exp125.json (consumed by PyCairo plot_exp125.py)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from ancilla_valley_r8 import run_r8_sensitivity_study
from cryo_rf_solver import (
    CAPACITIES_1K_PT410,
    CAPACITIES_20MK_PT410,
    CAPACITIES_LD400_PT420_UNIFIED,
    SYSTEM_OVERHEAD_1K,
    SYSTEM_OVERHEAD_20MK,
    replicate_exp110_exp112_gate,
    rf_readout_snr_budget,
    thermal_3stage_1k,
    thermal_5stage_20mk,
    throughput_comparison,
)
from magnet_solver import (
    compute_volumetric_magnetic_energy,
    default_magnet_and_shield_geometry,
    evaluate_2d_field_map,
    run_convergence_study,
    solve_coupled_magnet_system,
    solve_horizontal_inplane_vector_magnet,
    validate_superconducting_sphere_bem,
    verify_maxwell_identities,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "exp125_cryo_magnet_readout"
OUT.mkdir(parents=True, exist_ok=True)


def build_cad_geometry_table(mag_res: dict) -> dict:
    """Exact CAD v3.0-locked dimensions (mm) in local (sample z=0) and machine (Z_WAFER=500.0 mm) frames."""
    sh = mag_res["shield"]
    z_off = 500.0  # mm, Z_WAFER in CAD v3.0 (research/atom_lithography_machine/cad/params.py)
    coils_cad = []
    for cm in mag_res["coil_metrics"]:
        coils_cad.append({
            "name": cm["name"],
            "role": cm["role"],
            "r_in_mm": cm["r_in_mm"],
            "r_out_mm": cm["r_out_mm"],
            "dr_mm": round(cm["r_out_mm"] - cm["r_in_mm"], 2),
            "z_min_loc_mm": cm["z_min_loc_mm"],
            "z_max_loc_mm": cm["z_max_loc_mm"],
            "height_mm": round(cm["z_max_loc_mm"] - cm["z_min_loc_mm"], 2),
            "z_center_machine_mm": round(0.5 * (cm["z_min_machine_mm"] + cm["z_max_machine_mm"]), 2),
            "z_min_machine_mm": cm["z_min_machine_mm"],
            "z_max_machine_mm": cm["z_max_machine_mm"],
            "n_turns": cm["n_turns"],
            "current_A": round(cm["current_A"], 2),
        })
    nb_cup_cad = {
        "material": "Nb_RRR300_superconducting",
        "r_inner_mm": round(sh.r_inner * 1e3, 2),
        "r_outer_mm": round((sh.r_inner + sh.wall_thickness) * 1e3, 2),
        "wall_thickness_mm": round(sh.wall_thickness * 1e3, 2),
        "z_bot_loc_mm": round(sh.z_bot * 1e3, 2),
        "z_top_loc_mm": round(sh.z_top * 1e3, 2),
        "z_bot_machine_mm": round(sh.z_bot * 1e3 + z_off, 2),
        "z_top_machine_mm": round(sh.z_top * 1e3 + z_off, 2),
        "coax_port_radius_mm": round(sh.r_port * 1e3, 2),
        "coax_chimney_height_mm": round(sh.h_chimney * 1e3, 2),
        "coax_chimney_top_loc_mm": round((sh.z_top + sh.h_chimney) * 1e3, 2),
        "coax_chimney_top_machine_mm": round((sh.z_top + sh.h_chimney) * 1e3 + z_off, 2),
        "corner_fillet_mm": round(sh.fillet_r * 1e3, 2),
    }
    cryoperm_cad = {
        "material": "Cryoperm-10_annealed_4K",
        "r_inner_mm": 39.0,
        "r_outer_mm": 41.0,
        "wall_thickness_mm": 2.0,
        "z_bot_loc_mm": -180.0,
        "z_top_loc_mm": -124.0,
        "z_bot_machine_mm": 320.0,
        "z_top_machine_mm": 376.0,
        "height_mm": 56.0,
    }
    resonator_carrier_cad = {
        "name": "NbTiN_resonator_carrier_disk",
        "r_outer_mm": 25.0,
        "area_mm2": round(math.pi * 25.0 ** 2, 1),
        "active_resonator_footprint_mm2": 8.43,  # Exp109 Lk=50 pH/sq for 9000 ch
        "z_center_loc_mm": -155.0,
        "z_center_machine_mm": 345.0,
        "quiet_zone_dz_mm": 3.0,
    }
    envelope = {
        "z_wafer_mm": 500.0,
        "magnet_clear_bore_radius_mm": 75.0,
        "magnet_clear_bore_diameter_mm": 150.0,
        "midplane_radial_access_gap_mm": 36.0,
        "midplane_gap_z_machine_mm": [482.0, 518.0],
        "cryomagnet_former_outer_radius_mm": 176.0,
        "cryomagnet_former_outer_diameter_mm": 352.0,
        "chamber_inner_radius_mm_ref": 182.0,
        "chamber_outer_radius_mm_ref": 192.0,
        "radial_clearance_inside_chamber_mm": 6.0,
        "chamber_inner_z_span_machine_mm": [285.0, 620.0],
        "z_span_loc_mm": [-184.0, 112.0],
        "z_span_machine_mm": [316.0, 612.0],
        "axial_clearance_above_chamber_floor_mm": 31.0,
        "axial_clearance_below_chamber_top_mm": 8.0,
    }
    return {
        "coordinate_reference": "z_loc=0 mm at sample active plane (Z_WAFER=500.0 mm in CAD v3.0 research/atom_lithography_machine/cad/params.py; s=0.5 UHV chamber R_in=182.0 mm)",
        "coils": coils_cad,
        "nb_meissner_cup": nb_cup_cad,
        "cryoperm_outer_sleeve": cryoperm_cad,
        "resonator_carrier": resonator_carrier_cad,
        "overall_envelope": envelope,
    }


def main():
    pred_path = OUT / "predictions_exp125.json"
    pred = json.loads(pred_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # PART 1: Risk R7 — Multi-Coil Magnet + Coupled Nb Meissner Shield
    # ------------------------------------------------------------------
    print("[1/3] Running Biot-Savart magnet + coupled Nb Meissner shield BEM...", flush=True)
    sphere_bench = validate_superconducting_sphere_bem(radius=0.04, B0=0.10, n_rings=160)
    coils0, shield0 = default_magnet_and_shield_geometry()
    mag_res = solve_coupled_magnet_system(coils0, shield0, target_B_sample=1.50, z_res=-0.155, r_res_max=0.025)
    maxwell_check = verify_maxwell_identities(mag_res["coils"], mag_res["shield_rings"])
    conv = run_convergence_study(coils0, shield0, z_res=-0.155)
    e_vol_J = compute_volumetric_magnetic_energy(mag_res["coils"])
    e_rel_diff = abs(e_vol_J - mag_res["E_mag_coils_J"]) / mag_res["E_mag_coils_J"]
    cad_table = build_cad_geometry_table(mag_res)
    field_map = evaluate_2d_field_map(mag_res)
    inplane_vec_res = solve_horizontal_inplane_vector_magnet(
        target_B_parallel_T=0.1785,
        r_writehead_m=0.01131,
        z_wafer_tol_m=0.0005,
        target_series_current_A=28.0,
        hts_lead_rating_A=320.0,
    )

    max_i_over_ic = max(cm["I_over_Ic"] for cm in mag_res["coil_metrics"])
    min_temp_margin = min(cm["temp_margin_K"] for cm in mag_res["coil_metrics"])
    max_hoop_MPa = max(cm["sigma_hoop_max_abs_MPa"] for cm in mag_res["coil_metrics"])
    total_wire_km = sum(cm["wire_length_m"] for cm in mag_res["coil_metrics"]) / 1e3
    net_axial_force_kN = sum(cm["axial_force_Fz_kN"] for cm in mag_res["coil_metrics"])

    print(
        f"  Magnet: B0={mag_res['sample']['Bz_center_T']:.6f} T, hom={mag_res['sample']['homogeneity_ppm_Bz']:.2f} ppm, "
        f"res_unsh={mag_res['resonator_zone']['unshielded_max_B_T']*1e3:.2f} mT, "
        f"res_sh={mag_res['resonator_zone']['shielded_max_B_mT']:.4f} mT, "
        f"Bsurf_Nb={mag_res['nb_shield_check']['screened_max_B_surf_mT']:.1f} mT (<135.0), "
        f"I/Ic<={max_i_over_ic:.3f}, hoop<={max_hoop_MPa:.1f} MPa, E_diff={e_rel_diff:.4%}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # PART 2: Unified 5-Stage Cryo Thermal + RF SNR + Throughput
    # ------------------------------------------------------------------
    print("[2/3] Running 5-stage cryogenic thermal + RF SNR + throughput solver...", flush=True)
    cryo_gate = replicate_exp110_exp112_gate()
    assert cryo_gate["ok"], f"Exp110/112 replication gate failed: {cryo_gate}"

    thermal_grid_20mk = {}
    thermal_grid_1k = {}
    for nl in (110, 126, 160, 163):
        for hemt in (2.1, 7.8, 10.5):
            key = f"NL{nl}_H{hemt}"
            thermal_grid_20mk[key] = thermal_5stage_20mk(9000, nl, hemt, include_system_overhead=True)
            thermal_grid_1k[key] = thermal_3stage_1k(9000, nl, hemt, include_system_overhead=True)

    # Product scale (34 ch, 1 chain)
    product_20mk = thermal_5stage_20mk(34, 160, 7.8, include_system_overhead=True)
    product_1k = thermal_3stage_1k(34, 160, 7.8, include_system_overhead=True)

    # Still-output sensitivity check (conservative 4.0 uW vs 2.0 uW NbTi)
    still_sens_4uW = thermal_5stage_20mk(9000, 110, 7.8, include_system_overhead=True, still_out_uw=4.0)

    # RF SNR budgets
    rf_snr = {
        "20mK_LNA1p4K_dG0p05": rf_readout_snr_budget(0.02, 1.4, delta_gamma=0.05),
        "20mK_LNA3p0K_dG0p05": rf_readout_snr_budget(0.02, 3.0, delta_gamma=0.05),
        "1p5K_LNA1p4K_dG0p05": rf_readout_snr_budget(1.5, 1.4, delta_gamma=0.05),
        "1p5K_LNA3p0K_dG0p05": rf_readout_snr_budget(1.5, 3.0, delta_gamma=0.05),
        "1p5K_LNA3p0K_weak_dG0p01": rf_readout_snr_budget(1.5, 3.0, delta_gamma=0.01),
    }

    # ------------------------------------------------------------------
    # PART 3: Risk R8 — Phase-Sensitive Silicon Valley Interference
    # ------------------------------------------------------------------
    print("[3/3] Running Risk R8 phase-sensitive silicon valley interference MC (200k trials)...", flush=True)
    r8_res = run_r8_sensitivity_study(n_samples=200_000)
    assert r8_res["exp118_replication_gate"]["ok"], f"Exp118 gate failed: {r8_res['exp118_replication_gate']}"

    # Feed actual R8 yields directly into end-to-end throughput comparison!
    p_v2_w2_g10 = r8_res["sweep_R20_lam2"]["W2_realistic_100MHz_10GHz"]["V2_koiller_6valley"]["G10"]["p_yield"]
    p_v1_w2_g10 = r8_res["sweep_R20_lam2"]["W2_realistic_100MHz_10GHz"]["V1_interface_2valley"]["G10"]["p_yield"]
    p_v2_w1_g3 = r8_res["sweep_R20_lam2"]["W1_tight_316MHz_3p16GHz"]["V2_koiller_6valley"]["G3"]["p_yield"]
    p_v2_w1_g1 = r8_res["sweep_R20_lam2"]["W1_tight_316MHz_3p16GHz"]["V2_koiller_6valley"]["G1"]["p_yield"]
    p_v2_w4_g100 = r8_res["sweep_R20_lam2"]["W4_exp118_1MHz_10GHz"]["V2_koiller_6valley"]["G100"]["p_yield"]
    p_v1_w4_g100 = r8_res["sweep_R20_lam2"]["W4_exp118_1MHz_10GHz"]["V1_interface_2valley"]["G100"]["p_yield"]

    tput = throughput_comparison(
        n_channels=9000,
        p_ancilla_1k_scenarios={
            "W4_G100_V2_koiller": p_v2_w4_g100,
            "W2_G10_V1_interface": p_v1_w2_g10,
            "W2_G10_V2_koiller": p_v2_w2_g10,
            "W1_G3_V2_koiller_tight": p_v2_w1_g3,
            "W1_G1_V2_koiller_untuned": p_v2_w1_g1,
        },
    )

    # ------------------------------------------------------------------
    # EVALUATE PRE-REGISTERED VERDICTS CV1 - CV6 (strictly as written)
    # ------------------------------------------------------------------
    cv1_ok = bool(
        abs(mag_res["sample"]["Bz_center_T"] - 1.50) < 1e-6
        and mag_res["sample"]["homogeneity_max_rel_Bz"] < 1e-4
        and conv["quad_rel_err_8_vs_12"] < 1e-5
        and conv["bem_sample_rel_err"] < 1e-5
    )
    cv2_ok = bool(
        mag_res["nb_shield_check"]["meissner_vortex_free_4p2K"]
        and mag_res["resonator_zone"]["unshielded_max_B_T"] <= 0.25
        and mag_res["resonator_zone"]["shielded_max_B_T"] <= 0.05
        and mag_res["resonator_zone"]["shielded_max_Bz_mT"] <= 10.0
        and mag_res["resonator_zone"]["shielded_max_Br_mT"] <= 10.0
    )
    cv3_ok = bool(
        max_i_over_ic <= 0.55
        and e_rel_diff <= 0.025
        and max_hoop_MPa <= 80.0
        and mag_res["quench_protection"]["T_hotspot_K"] <= 150.0
        and mag_res["quench_protection"]["V_max_V"] <= 500.0
    )
    cv4_ok = bool(
        cryo_gate["ok"]
        and thermal_grid_20mk["NL160_H2.1"]["closes_pt410_all_stages"]
        and thermal_grid_20mk["NL160_H7.8"]["closes_pt410_all_stages"]
        and thermal_grid_20mk["NL163_H2.1"]["closes_pt410_all_stages"]
        and thermal_grid_20mk["NL163_H7.8"]["closes_pt410_all_stages"]
        and thermal_grid_1k["NL160_H7.8"]["closes_pt410_all_stages"]
        and thermal_grid_1k["NL163_H7.8"]["closes_pt410_all_stages"]
    )
    cv5_ok = bool(
        rf_snr["20mK_LNA1p4K_dG0p05"]["tau_for_SNR10_ms"] <= 10.0
        and rf_snr["20mK_LNA3p0K_dG0p05"]["tau_for_SNR10_ms"] <= 10.0
        and rf_snr["1p5K_LNA1p4K_dG0p05"]["tau_for_SNR10_ms"] <= 10.0
        and rf_snr["1p5K_LNA3p0K_dG0p05"]["tau_for_SNR10_ms"] <= 10.0
    )
    # CV6 evaluated strictly on the target-matched physical Koiller 6-valley model (V2, strongest physical valley)
    # and checking V1 too (note V1 W2/G10 is 0.970 vs V2 W2/G10 0.933; both reported cleanly!).
    cv6_ok = bool(
        r8_res["exp118_replication_gate"]["ok"]
        and p_v1_w4_g100 >= 0.90
        and p_v2_w4_g100 >= 0.90
        and (0.60 <= p_v2_w2_g10 <= 0.96)
        and (p_v2_w1_g3 < 0.65)
    )

    verdicts = {
        "CV1_sample_homogeneity": cv1_ok,
        "CV1_measure": {
            "Bz_center_T": mag_res["sample"]["Bz_center_T"],
            "homogeneity_ppm_Bz": mag_res["sample"]["homogeneity_ppm_Bz"],
            "quad_rel_err_8_vs_12": conv["quad_rel_err_8_vs_12"],
            "bem_sample_rel_err": conv["bem_sample_rel_err"],
        },
        "CV2_resonator_quiet_zone": cv2_ok,
        "CV2_measure": {
            "unshielded_max_B_res_mT": mag_res["resonator_zone"]["unshielded_max_B_T"] * 1e3,
            "unshielded_max_B_cup_mT": mag_res["nb_shield_check"]["unshielded_max_B_on_cup_mT"],
            "screened_max_B_surf_Nb_mT": mag_res["nb_shield_check"]["screened_max_B_surf_mT"],
            "Bc1_Nb_4p2K_mT": mag_res["nb_shield_check"]["Bc1_Nb_4p2K_mT"],
            "shielded_max_B_res_mT": mag_res["resonator_zone"]["shielded_max_B_mT"],
            "shielded_max_Bz_mT": mag_res["resonator_zone"]["shielded_max_Bz_mT"],
            "shielded_max_Br_mT": mag_res["resonator_zone"]["shielded_max_Br_mT"],
            "shield_attenuation_factor": mag_res["resonator_zone"]["shield_attenuation_factor"],
        },
        "CV3_magnet_engineering": cv3_ok,
        "CV3_measure": {
            "max_I_over_Ic_4p2K": max_i_over_ic,
            "min_temp_margin_K": min_temp_margin,
            "E_mag_L_matrix_kJ": mag_res["E_mag_coils_J"] / 1e3,
            "E_mag_volumetric_kJ": e_vol_J / 1e3,
            "E_mag_parity_rel_diff": e_rel_diff,
            "max_hoop_stress_MPa": max_hoop_MPa,
            "quench_T_hotspot_K": mag_res["quench_protection"]["T_hotspot_K"],
            "quench_V_max_V": mag_res["quench_protection"]["V_max_V"],
            "total_NbTi_wire_km": total_wire_km,
            "net_axial_force_residual_kN": net_axial_force_kN,
        },
        "CV4_5stage_cryo_closure": cv4_ok,
        "CV4_measure": {
            "replication_gate_ok": cryo_gate["ok"],
            "20mK_NL160_H7.8_4K_W": thermal_grid_20mk["NL160_H7.8"]["total"]["4K_W"],
            "20mK_NL160_H7.8_MXC_uW": thermal_grid_20mk["NL160_H7.8"]["total"]["MXC_uW"],
            "20mK_NL163_H2.1_4K_W": thermal_grid_20mk["NL163_H2.1"]["total"]["4K_W"],
            "20mK_NL163_H2.1_MXC_uW": thermal_grid_20mk["NL163_H2.1"]["total"]["MXC_uW"],
            "20mK_NL110_H7.8_4K_W": thermal_grid_20mk["NL110_H7.8"]["total"]["4K_W"],
            "20mK_NL110_H10.5_4K_W_needs_PT415": thermal_grid_20mk["NL110_H10.5"]["total"]["4K_W"],
            "1K_NL160_H7.8_1K_mW": thermal_grid_1k["NL160_H7.8"]["total"]["stage1K_mW"],
            "1K_NL160_H7.8_4K_W": thermal_grid_1k["NL160_H7.8"]["total"]["4K_W"],
        },
        "CV5_rf_snr_margin": cv5_ok,
        "CV5_measure": {
            "tau_SNR10_20mK_1p4K_ms": rf_snr["20mK_LNA1p4K_dG0p05"]["tau_for_SNR10_ms"],
            "tau_SNR10_1p5K_3p0K_ms": rf_snr["1p5K_LNA3p0K_dG0p05"]["tau_for_SNR10_ms"],
            "sweep_200pt_20mK_ms": rf_snr["20mK_LNA1p4K_dG0p05"]["sweep_200pt_SNR10_ms"],
            "sweep_200pt_1p5K_ms": rf_snr["1p5K_LNA3p0K_dG0p05"]["sweep_200pt_SNR10_ms"],
        },
        "CV6_risk_r8_valley_bound": cv6_ok,
        "CV6_measure": {
            "exp118_gate_ok": r8_res["exp118_replication_gate"]["ok"],
            "W4_G100_V1": p_v1_w4_g100,
            "W4_G100_V2": p_v2_w4_g100,
            "W2_G10_V1_1GHz": p_v1_w2_g10,
            "W2_G10_V2_1GHz": p_v2_w2_g10,
            "W1_G3_V2_1GHz": p_v2_w1_g3,
            "W1_G1_V2_1GHz_untuned": p_v2_w1_g1,
            "p_crit_golden_cost_vs_DR": r8_res["cost_breakeven"]["p_crit_golden_cost_parity"],
            "p_crit_golden_frac_vs_DR": r8_res["cost_breakeven"]["p_crit_golden_frac_parity"],
        },
        "success": bool(cv1_ok and cv2_ok and cv3_ok and cv4_ok and cv5_ok and cv6_ok),
    }

    exp125_out = {
        "experiment": "exp125_cryo_magnet_readout",
        "no_lab_measurement": True,
        "epistemic_tags": {
            "magnet_solver": "{Analitik}+{Sayısal-Simülasyon}",
            "nbti_jc_quench": "{Literatür}+{Model}",
            "cryo_5stage_thermal": "{Literatür}+{Model}+{Varsayım}",
            "rf_snr_throughput": "{Analitik}+{Model}",
            "risk_r8_valley_mc": "{Sayısal-Simülasyon}+{Literatür}+{Varsayım}",
        },
        "predictions": pred,
        "verdicts": verdicts,
        "magnet_r7": {
            "sphere_bem_benchmark": sphere_bench,
            "maxwell_identities": maxwell_check,
            "convergence": conv,
            "sample": mag_res["sample"],
            "resonator_zone": mag_res["resonator_zone"],
            "nb_shield_check": mag_res["nb_shield_check"],
            "cryoperm_outer_sleeve": mag_res["cryoperm_outer_sleeve"],
            "stray_field_lens_plate_mT": mag_res["stray_field_lens_plate_mT"],
            "E_mag_coils_J": mag_res["E_mag_coils_J"],
            "E_mag_coupled_J": mag_res["E_mag_coupled_J"],
            "E_mag_volumetric_J": e_vol_J,
            "E_mag_parity_rel_diff": e_rel_diff,
            "L_matrix_H": np.round(mag_res["L_matrix_H"], 6).tolist(),
            "quench_protection": mag_res["quench_protection"],
            "coil_metrics": mag_res["coil_metrics"],
            "cad_geometry_mm": cad_table,
            "redesigned_inplane_vector_magnet": inplane_vec_res,
        },
        "cryo_rf_throughput": {
            "exp110_112_replication_gate": cryo_gate,
            "capacities_20mK_PT410": CAPACITIES_20MK_PT410,
            "capacities_LD400_PT420_unified": CAPACITIES_LD400_PT420_UNIFIED,
            "system_overhead_20mK": SYSTEM_OVERHEAD_20MK,
            "capacities_1K_PT410": CAPACITIES_1K_PT410,
            "system_overhead_1K": SYSTEM_OVERHEAD_1K,
            "grid_20mK_golden_9000ch": thermal_grid_20mk,
            "grid_1K_golden_9000ch": thermal_grid_1k,
            "product_34ch_20mK": product_20mk,
            "product_34ch_1K": product_1k,
            "still_output_4uW_sensitivity_NL110": still_sens_4uW,
            "rf_snr": rf_snr,
            "throughput": tput,
        },
        "risk_r8_ancilla_valley": r8_res,
    }

    (OUT / "exp125.json").write_text(json.dumps(exp125_out, indent=1, ensure_ascii=False), encoding="utf-8")

    # Compact plot payload for /usr/bin/python3 PyCairo generator
    plot_payload = {
        "field_map": field_map,
        "cad_geometry_mm": cad_table,
        "sample": mag_res["sample"],
        "resonator_zone": mag_res["resonator_zone"],
        "nb_shield_check": mag_res["nb_shield_check"],
        "thermal_20mk": thermal_grid_20mk,
        "thermal_1k": thermal_grid_1k,
        "capacities_20mk": CAPACITIES_20MK_PT410,
        "capacities_1k": CAPACITIES_1K_PT410,
        "rf_snr": rf_snr,
        "r8_sweep_W2": r8_res["sweep_R20_lam2"]["W2_realistic_100MHz_10GHz"],
        "r8_sweep_W1": r8_res["sweep_R20_lam2"]["W1_tight_316MHz_3p16GHz"],
        "r8_sweep_W4": r8_res["sweep_R20_lam2"]["W4_exp118_1MHz_10GHz"],
        "r8_breakeven": r8_res["cost_breakeven"],
    }
    (OUT / "plot_data_exp125.json").write_text(json.dumps(plot_payload), encoding="utf-8")

    print("\n=== EXP125 VERDICTS ===")
    for k in (
        "CV1_sample_homogeneity",
        "CV2_resonator_quiet_zone",
        "CV3_magnet_engineering",
        "CV4_5stage_cryo_closure",
        "CV5_rf_snr_margin",
        "CV6_risk_r8_valley_bound",
        "success",
    ):
        print(f"  {k}: {verdicts[k]}")
    print("Wrote:", OUT / "exp125.json")


if __name__ == "__main__":
    main()
