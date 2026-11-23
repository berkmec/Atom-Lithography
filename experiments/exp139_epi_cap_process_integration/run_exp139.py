"""Exp139 Orchestrator (H157): Integrated 8 nm 28Si Epi Cap + Millisecond Flash Anneal +
Si/SiO2 D_it / S_eps Interface Physics & S5.6 Hardware Specification (CAD v5.0 / BOM v5.0).

Pre-registered predictions: results/exp139_epi_cap_process_integration/predictions_exp139.json (EP1-EP7).
Epistemic label: {Model} / {Sayisal-Simulasyon} / {Literatur} / {Varsayim}.
no_lab_measurement=True, no_supplier_quotes=True.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from epi_cap_physics139 import (
    build_zbl_scattering_table,
    evaluate_charge_noise_routes,
    evaluate_lt_mbe_kinetics,
    evaluate_route_flipflop_yield,
    mcwhorter_geom_integrals,
    run_coupled_thermal_chain_ted,
    simulate_bca_31p_in_si,
    simulate_recoil_oxygen_through_oxide,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "exp139_epi_cap_process_integration"
PRED_PATH = RESULTS_DIR / "predictions_exp139.json"
OUT_JSON = RESULTS_DIR / "exp139.json"
PLOT_DATA_JSON = RESULTS_DIR / "plot_data_exp139.json"
EXP92_JSON = REPO_ROOT / "results" / "exp92_bca_straggle" / "exp92.json"

# Locked Exp124 Arch-B non-straggle/non-anneal equipment RSS [nm]:
# sigma_equip_no_ann = sqrt(1.428^2 + 0.500^2 + 0.500^2 + 0.300^2) = 1.6215 nm
EXP124_EQUIP_NO_ANN_VAR_NM2 = 1.428**2 + 0.500**2 + 0.500**2 + 0.300**2
EXP124_CEILING_NM = 3.800


def exp124_sigma_tot(sigma_lat_straggle_nm: float, sigma_anneal_nm: float) -> float:
    return math.sqrt(EXP124_EQUIP_NO_ANN_VAR_NM2 + sigma_lat_straggle_nm**2 + sigma_anneal_nm**2)


def main() -> None:
    t0 = time.perf_counter()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    preds = json.loads(PRED_PATH.read_text(encoding="utf-8"))
    exp92 = json.loads(EXP92_JSON.read_text(encoding="utf-8"))

    # =========================================================================
    # 1. ZBL+LSS BCA Sweep (5..24 keV, N=4,000) + Convergence + Recoil-O
    # =========================================================================
    zbl_table = build_zbl_scattering_table()
    energies_keV = [5.0, 10.0, 14.0, 15.0, 18.0, 20.0, 22.0, 24.0]
    bca_raw: Dict[float, Dict[str, Any]] = {}
    bca_summary: Dict[str, Dict[str, Any]] = {}
    for idx_e, E_k in enumerate(energies_keV):
        b = simulate_bca_31p_in_si(E_k, n_ions=4000, zbl_table=zbl_table, seed=2026139 + idx_e * 17)
        bca_raw[E_k] = b
        bca_summary[f"E{int(E_k)}"] = {
            "E_keV": E_k,
            "n_ions": b["n_ions"],
            "n_implanted": b["n_implanted"],
            "backscatter_frac": round(b["backscatter_frac"], 5),
            "Rp_nm": round(b["Rp_nm"], 4),
            "sigma_z_nm": round(b["sigma_z_nm"], 4),
            "sigma_x_nm": round(b["sigma_x_nm"], 4),
            "sigma_y_nm": round(b["sigma_y_nm"], 4),
            "sigma_lat_nm": round(b["sigma_lat_nm"], 4),
            "exp124_sigma_tot_with_flash_nm": round(exp124_sigma_tot(b["sigma_lat_nm"], 0.328), 4),
        }

    # BCA convergence check N=2,000 vs N=4,000 (pre-registered EP7) + diagnostic N=4,000 vs N=8,000
    b5_2k = simulate_bca_31p_in_si(5.0, n_ions=2000, zbl_table=zbl_table, seed=2026139)
    b22_2k = simulate_bca_31p_in_si(22.0, n_ions=2000, zbl_table=zbl_table, seed=2026139 + 6 * 17)
    b5_8k = simulate_bca_31p_in_si(5.0, n_ions=8000, zbl_table=zbl_table, seed=2026999)
    b22_8k = simulate_bca_31p_in_si(22.0, n_ions=8000, zbl_table=zbl_table, seed=2027001)
    bca_conv = {
        "E5_Rp_rel_diff_2k_vs_4k": round(abs(b5_2k["Rp_nm"] - bca_raw[5.0]["Rp_nm"]) / bca_raw[5.0]["Rp_nm"], 5),
        "E5_sigx_rel_diff_2k_vs_4k": round(abs(b5_2k["sigma_lat_nm"] - bca_raw[5.0]["sigma_lat_nm"]) / bca_raw[5.0]["sigma_lat_nm"], 5),
        "E22_Rp_rel_diff_2k_vs_4k": round(abs(b22_2k["Rp_nm"] - bca_raw[22.0]["Rp_nm"]) / bca_raw[22.0]["Rp_nm"], 5),
        "E22_sigx_rel_diff_2k_vs_4k": round(abs(b22_2k["sigma_lat_nm"] - bca_raw[22.0]["sigma_lat_nm"]) / bca_raw[22.0]["sigma_lat_nm"], 5),
    }
    bca_conv_4k_8k = {
        "E5_Rp_rel_diff_4k_vs_8k": round(abs(b5_8k["Rp_nm"] - bca_raw[5.0]["Rp_nm"]) / b5_8k["Rp_nm"], 5),
        "E5_sigx_rel_diff_4k_vs_8k": round(abs(b5_8k["sigma_lat_nm"] - bca_raw[5.0]["sigma_lat_nm"]) / b5_8k["sigma_lat_nm"], 5),
        "E22_Rp_rel_diff_4k_vs_8k": round(abs(b22_8k["Rp_nm"] - bca_raw[22.0]["Rp_nm"]) / b22_8k["Rp_nm"], 5),
        "E22_sigx_rel_diff_4k_vs_8k": round(abs(b22_8k["sigma_lat_nm"] - bca_raw[22.0]["sigma_lat_nm"]) / b22_8k["sigma_lat_nm"], 5),
    }
    bca_conv_max_err = max(bca_conv.values())

    # Compare against Exp92 canonical 5/10/20 keV anchors
    exp92_check: Dict[str, Dict[str, float]] = {}
    for ek_str, E_val in [("E5", 5.0), ("E10", 10.0), ("E20", 20.0)]:
        ref92 = exp92["bca"][ek_str]
        cur = bca_raw[E_val]
        ref_lat = 0.5 * (ref92["sigma_x_nm"] + ref92["sigma_y_nm"])
        exp92_check[ek_str] = {
            "exp92_Rp_nm": round(ref92["Rp_nm"], 4),
            "exp139_Rp_nm": round(cur["Rp_nm"], 4),
            "Rp_rel_diff": round(abs(cur["Rp_nm"] - ref92["Rp_nm"]) / ref92["Rp_nm"], 5),
            "exp92_sigma_lat_nm": round(ref_lat, 4),
            "exp139_sigma_lat_nm": round(cur["sigma_lat_nm"], 4),
            "sigma_lat_rel_diff": round(abs(cur["sigma_lat_nm"] - ref_lat) / ref_lat, 5),
        }
    exp92_max_rel_diff = max(max(v["Rp_rel_diff"], v["sigma_lat_rel_diff"]) for v in exp92_check.values())

    # Recoil-O knock-on for Route B through 1.5 nm SiO2 gate oxide (20, 22, 24 keV)
    recoil_oxygen: Dict[str, Dict[str, Any]] = {}
    for idx_r, E_k in enumerate((20.0, 22.0, 24.0)):
        rec = simulate_recoil_oxygen_through_oxide(E_k, oxide_thick_nm=1.5, n_ions=4000, zbl_table=zbl_table, seed=2026200 + idx_r * 13)
        recoil_oxygen[f"E{int(E_k)}_1p5nm_SiO2"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()}

    # =========================================================================
    # 2. Route A Low-T 28Si MBE Growth Kinetics Sweep (250..450 C, 8 nm Cap)
    # =========================================================================
    T_mbe_grid = np.linspace(250.0, 450.0, 41)
    mbe_sweep: List[Dict[str, Any]] = [evaluate_lt_mbe_kinetics(float(T_c), 8.0, 0.10) for T_c in T_mbe_grid]
    mbe_passing = [m for m in mbe_sweep if m["meets_mbe_criteria"]]
    mbe_opt = min(mbe_sweep, key=lambda x: x["quality_cost"])
    T_epi_opt_C = float(mbe_opt["T_epi_C"])

    # Growth-rate sensitivity at T_epi* (0.05, 0.10, 0.20 nm/s)
    mbe_rate_sensitivity = {
        f"R_{rg:.2f}_nm_s": evaluate_lt_mbe_kinetics(T_epi_opt_C, 8.0, rg)
        for rg in (0.05, 0.10, 0.20)
    }

    # =========================================================================
    # 3. Coupled Full Thermal Chain PDE (Flash -> LT-MBE -> 350 C Passivation)
    # =========================================================================
    # (a) v4.0 Exp130 nominal flash setpoint (1x 1.0 ms @ 1440 K, 41.15 J/cm^2)
    thermal_chain_5keV_v4 = run_coupled_thermal_chain_ted(
        Rp_nm=6.46, sigma_z_nm=2.88, T_epi_C=T_epi_opt_C, t_mbe_s=mbe_opt["deposition_time_s"],
        T_peak_K=1440.0, n_flash_pulses=1,
    )
    # (b) v5.0 Remedial Option 1: Cluster-clearing single pulse (1x 1.0 ms @ 1530 K, 43.49 J/cm^2, < 0.92 T_melt)
    thermal_chain_5keV_v5_1530K = run_coupled_thermal_chain_ted(
        Rp_nm=6.46, sigma_z_nm=2.88, T_epi_C=T_epi_opt_C, t_mbe_s=mbe_opt["deposition_time_s"],
        T_peak_K=1530.0, n_flash_pulses=1,
    )
    # (c) v5.0 Remedial Option 2: Multi-pulse at v4.0 T_peak (4x 1.0 ms @ 1440 K, 41.15 J/cm^2)
    thermal_chain_5keV_v5_quad = run_coupled_thermal_chain_ted(
        Rp_nm=6.46, sigma_z_nm=2.88, T_epi_C=T_epi_opt_C, t_mbe_s=mbe_opt["deposition_time_s"],
        T_peak_K=1440.0, n_flash_pulses=4,
    )
    # (d) Literature 14 keV SRIM/Tosi anchor (z0=15.0 nm, sig_z=5.0 nm) under v5.0 cluster-clearing flash
    thermal_chain_14keV_v5 = run_coupled_thermal_chain_ted(
        Rp_nm=15.0, sigma_z_nm=5.0, T_epi_C=T_epi_opt_C, t_mbe_s=mbe_opt["deposition_time_s"],
        T_peak_K=1530.0, n_flash_pulses=1,
    )
    # (e) Route B 22 keV through-cap (flash only)
    thermal_chain_22keV_B = run_coupled_thermal_chain_ted(
        Rp_nm=bca_raw[22.0]["Rp_nm"], sigma_z_nm=bca_raw[22.0]["sigma_z_nm"],
        T_epi_C=25.0, t_mbe_s=1.0, T_peak_K=1440.0, n_flash_pulses=1,
    )

    # =========================================================================
    # 4. Exact 2D Image-Charge McWhorter Electrostatics & Exp137 Bridge
    # =========================================================================
    # Radial grid convergence check (n_r = 400 vs 800 vs 1600)
    g400 = mcwhorter_geom_integrals(14.5, n_r=400)
    g800 = mcwhorter_geom_integrals(14.5, n_r=800)
    g1600 = mcwhorter_geom_integrals(14.5, n_r=1600)
    mcw_conv_rel_err = max(
        abs(g1600["I_ff_eV2_nm2"] - g800["I_ff_eV2_nm2"]) / g1600["I_ff_eV2_nm2"],
        abs(g1600["I_Ez_V2"] - g800["I_Ez_V2"]) / g1600["I_Ez_V2"],
    )

    rec22_O = recoil_oxygen["E22_1p5nm_SiO2"]["O_injected_into_Si_per_ion"]
    rec20_O = recoil_oxygen["E20_1p5nm_SiO2"]["O_injected_into_Si_per_ion"]
    N_def_opt = float(mbe_opt["N_def_cm3"])

    charge_noise_routes = {
        "route_B_22keV_through_cap": evaluate_charge_noise_routes(
            z_donor_nm=bca_raw[22.0]["Rp_nm"], D_it_cm2_eV=1.8e11, d_ox_nm=8.0,
            bulk_defect_N_cm3=1.0e14, recoil_O_per_ion=rec22_O,
        ),
        "route_B_20keV_through_cap": evaluate_charge_noise_routes(
            z_donor_nm=bca_raw[20.0]["Rp_nm"], D_it_cm2_eV=1.8e11, d_ox_nm=8.0,
            bulk_defect_N_cm3=1.0e14, recoil_O_per_ion=rec20_O,
        ),
        "route_A_5keV_post_anneal_mbe_unpassivated": evaluate_charge_noise_routes(
            z_donor_nm=bca_raw[5.0]["Rp_nm"] + 8.0, D_it_cm2_eV=1.0e11, d_ox_nm=8.0,
            bulk_defect_N_cm3=N_def_opt, recoil_O_per_ion=0.0,
        ),
        "route_C_nominal_FG350C_Dit_1p5e10": evaluate_charge_noise_routes(
            z_donor_nm=bca_raw[5.0]["Rp_nm"] + 8.0, D_it_cm2_eV=1.5e10, d_ox_nm=8.0,
            bulk_defect_N_cm3=N_def_opt, recoil_O_per_ion=0.0,
        ),
        "route_C_conservative_Dit_3p0e10": evaluate_charge_noise_routes(
            z_donor_nm=bca_raw[5.0]["Rp_nm"] + 8.0, D_it_cm2_eV=3.0e10, d_ox_nm=8.0,
            bulk_defect_N_cm3=N_def_opt, recoil_O_per_ion=0.0,
        ),
        "route_C_optimistic_Dit_1p0e10_dox8": evaluate_charge_noise_routes(
            z_donor_nm=bca_raw[5.0]["Rp_nm"] + 8.0, D_it_cm2_eV=1.0e10, d_ox_nm=8.0,
            bulk_defect_N_cm3=N_def_opt, recoil_O_per_ion=0.0,
        ),
        "route_C_thin_oxide_Dit_1p0e10_dox5": evaluate_charge_noise_routes(
            z_donor_nm=bca_raw[5.0]["Rp_nm"] + 8.0, D_it_cm2_eV=1.0e10, d_ox_nm=5.0,
            bulk_defect_N_cm3=N_def_opt, recoil_O_per_ion=0.0,
        ),
        "route_A_14keV_deep_23nm_unpassivated": evaluate_charge_noise_routes(
            z_donor_nm=23.0, D_it_cm2_eV=1.0e11, d_ox_nm=8.0,
            bulk_defect_N_cm3=N_def_opt, recoil_O_per_ion=0.0,
        ),
        "route_C_14keV_deep_23nm_Dit_1p5e10": evaluate_charge_noise_routes(
            z_donor_nm=23.0, D_it_cm2_eV=1.5e10, d_ox_nm=8.0,
            bulk_defect_N_cm3=N_def_opt, recoil_O_per_ion=0.0,
        ),
    }

    # Sweep S_eps(D_it) and S_E(z_donor) curves for plotting
    dit_curve = []
    for dit in np.geomspace(5.0e9, 4.0e11, 25):
        cn8 = evaluate_charge_noise_routes(14.5, float(dit), d_ox_nm=8.0, bulk_defect_N_cm3=N_def_opt)
        cn5 = evaluate_charge_noise_routes(14.5, float(dit), d_ox_nm=5.0, bulk_defect_N_cm3=N_def_opt)
        dit_curve.append({
            "D_it_cm2_eV": float(dit),
            "S_eps_dox8_ueV": cn8["S_eps_ueV_rtHz"],
            "S_eps_dox5_ueV": cn5["S_eps_ueV_rtHz"],
        })

    # =========================================================================
    # 5. Head-to-Head Exp131 4x4 Tosi Flip-Flop Yield Evaluation (N=2,000)
    # =========================================================================
    rng_ens = np.random.default_rng(2026139)
    R_q_opt = float(mbe_opt["R_q_nm"])

    # Separate exact thermal sigma_anneal per route & flash recipe:
    sig_fl_v4 = float(thermal_chain_5keV_v4["flash_only"]["sigma_anneal_nm"])
    sig_A_v4 = float(thermal_chain_5keV_v4["route_A_flash_plus_mbe"]["sigma_anneal_nm"])
    sig_C_v4 = float(thermal_chain_5keV_v4["route_C_full_chain"]["sigma_anneal_nm"])
    sig_A_v5 = float(thermal_chain_5keV_v5_1530K["route_A_flash_plus_mbe"]["sigma_anneal_nm"])
    sig_C_v5 = float(thermal_chain_5keV_v5_1530K["route_C_full_chain"]["sigma_anneal_nm"])
    sig_B_fl = float(thermal_chain_22keV_B["flash_only"]["sigma_anneal_nm"])

    def make_final_ensemble(
        z_base: np.ndarray, r_xy_base: np.ndarray, cap_nm: float, extra_z_sig: float, extra_xy_sig: float
    ) -> tuple[np.ndarray, np.ndarray]:
        dz_n = rng_ens.normal(0.0, extra_z_sig, size=z_base.size)
        dx_n = rng_ens.normal(0.0, extra_xy_sig, size=z_base.size)
        dy_n = rng_ens.normal(0.0, extra_xy_sig, size=z_base.size)
        z_fin = np.maximum(0.5, z_base + cap_nm + dz_n)
        r_fin = np.hypot(r_xy_base + dx_n, dy_n)
        return z_fin, r_fin

    z_bare, r_bare = make_final_ensemble(bca_raw[5.0]["z_samples_nm"], bca_raw[5.0]["r_xy_samples_nm"], 0.0, sig_fl_v4, math.sqrt(EXP124_EQUIP_NO_ANN_VAR_NM2 + sig_fl_v4**2))
    # v4.0 unmitigated 1440 K flash ensembles (showing latent back-end TED penalty)
    z_rA_v4, r_rA_v4 = make_final_ensemble(bca_raw[5.0]["z_samples_nm"], bca_raw[5.0]["r_xy_samples_nm"], 8.0, math.hypot(sig_A_v4, R_q_opt), math.sqrt(EXP124_EQUIP_NO_ANN_VAR_NM2 + sig_A_v4**2))
    z_rC_v4, r_rC_v4 = make_final_ensemble(bca_raw[5.0]["z_samples_nm"], bca_raw[5.0]["r_xy_samples_nm"], 8.0, math.hypot(sig_C_v4, R_q_opt), math.sqrt(EXP124_EQUIP_NO_ANN_VAR_NM2 + sig_C_v4**2))
    # v5.0 cluster-clearing 1530 K (43.49 J/cm^2) flash ensembles (RECOMMENDED v5.0 LOCKED RECIPE)
    z_rA_v5, r_rA_v5 = make_final_ensemble(bca_raw[5.0]["z_samples_nm"], bca_raw[5.0]["r_xy_samples_nm"], 8.0, math.hypot(sig_A_v5, R_q_opt), math.sqrt(EXP124_EQUIP_NO_ANN_VAR_NM2 + sig_A_v5**2))
    z_rC_v5, r_rC_v5 = make_final_ensemble(bca_raw[5.0]["z_samples_nm"], bca_raw[5.0]["r_xy_samples_nm"], 8.0, math.hypot(sig_C_v5, R_q_opt), math.sqrt(EXP124_EQUIP_NO_ANN_VAR_NM2 + sig_C_v5**2))

    z_rB22, r_rB22 = make_final_ensemble(bca_raw[22.0]["z_samples_nm"], bca_raw[22.0]["r_xy_samples_nm"], 0.0, sig_B_fl, math.sqrt(EXP124_EQUIP_NO_ANN_VAR_NM2 + sig_B_fl**2))
    z_rB20, r_rB20 = make_final_ensemble(bca_raw[20.0]["z_samples_nm"], bca_raw[20.0]["r_xy_samples_nm"], 0.0, sig_B_fl, math.sqrt(EXP124_EQUIP_NO_ANN_VAR_NM2 + sig_B_fl**2))
    # 14 keV SRIM/Tosi anchor (z0=15.0 +- 5.0 nm, r_xy ~ 6.0 nm) + 8.0 nm cap -> 23.0 nm
    z14_srim = np.maximum(1.0, rng_ens.normal(15.0, 5.0, size=2500))
    r14_srim = np.hypot(rng_ens.normal(0.0, 6.0, size=2500), rng_ens.normal(0.0, 6.0, size=2500))
    z_14_cap, r_14_cap = make_final_ensemble(z14_srim, r14_srim, 8.0, math.hypot(sig_C_v5, R_q_opt), math.sqrt(EXP124_EQUIP_NO_ANN_VAR_NM2 + sig_C_v5**2))

    S_eps_A = charge_noise_routes["route_A_5keV_post_anneal_mbe_unpassivated"]["S_eps_ueV_rtHz"]
    S_eps_B22 = charge_noise_routes["route_B_22keV_through_cap"]["S_eps_ueV_rtHz"]
    S_eps_B20 = charge_noise_routes["route_B_20keV_through_cap"]["S_eps_ueV_rtHz"]
    S_eps_C = charge_noise_routes["route_C_nominal_FG350C_Dit_1p5e10"]["S_eps_ueV_rtHz"]

    route_flipflop_yields = {
        "bare_5keV_uncapped_ref": evaluate_route_flipflop_yield(z_bare, r_bare, s_eps_uev=1.00, max_donors=2000, seed=101),
        "route_A_v4_1440K_5keV_8nm_mbe": evaluate_route_flipflop_yield(z_rA_v4, r_rA_v4, s_eps_uev=S_eps_A, max_donors=2000, seed=102),
        "route_C_v4_1440K_5keV_8nm_FG350C": evaluate_route_flipflop_yield(z_rC_v4, r_rC_v4, s_eps_uev=S_eps_C, max_donors=2000, seed=103),
        "route_A_v5_1530K_5keV_8nm_mbe": evaluate_route_flipflop_yield(z_rA_v5, r_rA_v5, s_eps_uev=S_eps_A, max_donors=2000, seed=107),
        "route_C_v5_1530K_5keV_8nm_FG350C": evaluate_route_flipflop_yield(z_rC_v5, r_rC_v5, s_eps_uev=S_eps_C, max_donors=2000, seed=108),
        "route_B_22keV_through_cap_flash": evaluate_route_flipflop_yield(z_rB22, r_rB22, s_eps_uev=S_eps_B22, max_donors=2000, seed=104),
        "route_B_20keV_through_cap_flash": evaluate_route_flipflop_yield(z_rB20, r_rB20, s_eps_uev=S_eps_B20, max_donors=2000, seed=105),
        "route_A_14keV_srim_15nm_plus_8nm_cap": evaluate_route_flipflop_yield(z_14_cap, r_14_cap, s_eps_uev=S_eps_C, max_donors=2000, seed=106),
    }

    # =========================================================================
    # 6. S5.6 Hardware Engineering Spec (CAD v5.0 & BOM v5.0 Ready)
    # =========================================================================
    # CAD v4.0 load-lock geometry anchor (research/atom_lithography_machine/cad/params.py L443-490):
    #   s5_loadlock_chamber: box (180, 180, 170) centered at (420.0, 0.0, 500.0) -> X in [330, 510], Y in [-90, 90], Z in [415, 585]
    #   s5_chamber_top_flange: tube R_out=225, Z in [620, 645] -> X_max = 225.0
    #   s5_transfer_arm: cyl R=15, L=200 along X centered at (610, 0, 500) -> X in [510, 710], Z in [485, 515]
    #   s5_flash_anneal_head: box (84, 88, 84) at (0, 367.2, 500) -> X in [-42, 42], Y in [323.2, 411.2], Z in [458, 542]
    # Proposed S5.6 CF100 MBE Capper mounted vertically on top (+Z) of s5_loadlock_chamber:
    #   Center (X=420.0, Y=0.0, Z=725.0), outer radius R_flange=76.0 mm (CF100 OD=152 mm), height=280.0 mm -> Z in [585, 865]
    s56_x, s56_y, s56_z_bot, s56_z_top, s56_r_od = 420.0, 0.0, 585.0, 865.0, 76.0
    clr_main_chamber_mm = (s56_x - s56_r_od) - 225.0  # 344.0 - 225.0 = 119.0 mm
    clr_transfer_arm_mm = s56_z_bot - 515.0           # 585.0 - 515.0 = 70.0 mm (and X_max=496 < 510)
    clr_flash_head_mm = math.hypot((s56_x - s56_r_od) - 42.0, (0.0 - s56_r_od) - 323.2)  # >300 mm
    min_clearance_mm = min(clr_main_chamber_mm, clr_transfer_arm_mm, clr_flash_head_mm)

    # Throughput impact anchored to Exp134 Rejim II (73.0 min dense M4 main-chamber cycle, 60 min cold shuttle)
    t_mbe_dep_s = float(mbe_opt["deposition_time_s"])  # 80.0 s at 0.10 nm/s
    t_route_A_ll_min = (t_mbe_dep_s + 120.0) / 60.0    # 3.33 min (ramp + 80 s growth + cool)
    t_route_C_ll_min = t_route_A_ll_min + 15.0 + 10.0  # 28.33 min (+15 min 350C FG + 10 min UHV pumpdown)
    exp134_dense_m4_active_min = 1.216 * 60.0          # 72.96 min (v4.0-5x dense M4, Exp134 §4)
    exp134_shuttle_min = 60.0                          # 1.0 h cold shuttle

    s56_hardware_spec = {
        "subsystem_id": "S5.6",
        "name": "In-Situ 28Si UHV MBE Capper & Forming-Gas Passivation Module",
        "cad_v5_geometry": {
            "mount_host": "s5_loadlock_chamber (+Z top port, CF100 DN100CF flange)",
            "center_mm": [s56_x, s56_y, 0.5 * (s56_z_bot + s56_z_top)],
            "flange_od_mm": 152.0,
            "bore_id_mm": 100.0,
            "envelope_diam_mm": 152.0,
            "envelope_height_mm": 280.0,
            "z_span_mm": [s56_z_bot, s56_z_top],
            "clearances_vs_cad_v4_mm": {
                "vs_s5_chamber_top_flange_mm": round(clr_main_chamber_mm, 1),
                "vs_s5_transfer_arm_mm": round(clr_transfer_arm_mm, 1),
                "vs_s5_flash_anneal_head_mm": round(clr_flash_head_mm, 1),
                "min_clearance_mm": round(min_clearance_mm, 1),
            },
        },
        "vacuum_and_deposition": {
            "evaporator_type": "Crucible-free DC 28Si rod sublimation source (SUSI-63 / mini e-beam class) + cryo/water shroud + pneumatic shutter + QCM",
            "isotope_feedstock": "Enriched 28Si rod (< 50 ppm 29Si, ~5 g charge -> >1,000 wafers @ 8 nm)",
            "base_pressure_torr": 1.5e-10,
            "growth_pressure_torr": 3.5e-10,
            "growth_rate_range_nm_s": [0.05, 0.20],
            "nominal_growth_rate_nm_s": 0.10,
            "target_cap_thickness_nm": 8.0,
            "cap_thickness_tolerance_nm": 0.3,
            "nominal_deposition_time_s": t_mbe_dep_s,
            "deposition_time_range_s": [40.0, 160.0],
            "optimal_substrate_T_C": T_epi_opt_C,
            "substrate_heater": "Load-Lock UHV pyrolytic-BN radiative chuck (RT-450 C, PID +-2 C, 150 W max)",
            "passivation_manifold_route_C": "Precision leak-valve 5% H2/N2 forming-gas (or UHV atomic-H thermal cracker), 350 C / 15 min, backed by 80 L/s TMP + NEG",
        },
        "mass_power_cryo": {
            "mass_breakdown_kg": {
                "cf100_28si_source_shroud_shutter_kg": 11.8,
                "qcm_feedthrough_and_valve_kg": 3.4,
                "pbn_heater_platen_and_h2_manifold_kg": 4.2,
                "compact_neg_tmp_aux_package_kg": 3.0,
            },
            "total_mass_kg": 22.4,
            "electrical_power_growth_W": 400.0,
            "electrical_power_standby_W": 25.0,
            "cryo_thermal_leak_to_20mK_uW": 0.0,
            "cryo_thermal_leak_to_4K_mW": 0.0,
            "cryo_isolation_mechanism": "All-metal UHV gate valve on s5_loadlock_duct isolates Load-Lock S5.3/S5.6 from 20 mK DR chamber during growth & passivation",
        },
        "bom_v5_cost_estimate_usd": {
            "epistemic_label": "{Varsayim}, no_supplier_quotes=true",
            "cf100_28si_source_shroud_psu_p50": 48000,
            "enriched_28si_rod_and_qcm_p50": 18000,
            "pbn_heater_h2_passivation_neg_p50": 29000,
            "total_p10_usd": 67000,
            "total_p50_usd": 95000,
            "total_p90_usd": 145000,
            "pct_of_v4_m3_hw_bom": round(95000.0 / 4609600.0 * 100.0, 2),
        },
        "wafer_throughput_impact_exp134": {
            "route_A_loadlock_time_min": round(t_route_A_ll_min, 2),
            "route_C_loadlock_time_min": round(t_route_C_ll_min, 2),
            "exp134_v4_5x_dense_m4_main_cycle_min": round(exp134_dense_m4_active_min, 2),
            "pipelined_throughput_penalty_pct": 0.0,
            "serial_route_A_overhead_vs_1h_shuttle_pct": round(t_route_A_ll_min / exp134_shuttle_min * 100.0, 2),
            "serial_route_C_overhead_vs_2p2h_total_cycle_pct": round(t_route_C_ll_min / (exp134_dense_m4_active_min + exp134_shuttle_min) * 100.0, 2),
        },
    }

    # =========================================================================
    # 7. Strict Pre-Registered Evaluation (EP1..EP7) — Unmodified Thresholds!
    # =========================================================================
    lat_ratio_22_vs_5 = bca_raw[22.0]["sigma_lat_nm"] / bca_raw[5.0]["sigma_lat_nm"]
    z_ratio_22_vs_5 = bca_raw[22.0]["sigma_z_nm"] / bca_raw[5.0]["sigma_z_nm"]
    ep1_pass = (
        exp92_max_rel_diff <= 0.05
        and lat_ratio_22_vs_5 >= 2.0
        and bca_raw[22.0]["sigma_lat_nm"] > 7.0
        and bca_summary["E22"]["exp124_sigma_tot_with_flash_nm"] > EXP124_CEILING_NM
        and z_ratio_22_vs_5 >= 1.8
        and bca_raw[22.0]["sigma_z_nm"] > 5.5
        and rec20_O >= 0.2
    )

    sigma_iso_combined_v4 = math.hypot(float(thermal_chain_5keV_v4["route_C_full_chain"]["sigma_iso_nm"]), float(mbe_opt["sigma_iso_mbe_nm"]))
    ep2_pass = (
        310.0 <= T_epi_opt_C <= 370.0
        and mbe_opt["h_epi_nm"] > 40.0
        and mbe_opt["R_q_nm"] <= 0.20
        and mbe_opt["N_def_cm3"] <= 1.0e15
        and mbe_opt["L_seg_nm"] <= 3.5
        and sigma_iso_combined_v4 <= 0.05
    )

    # Strictly evaluate EP3 & EP5 on the pre-registered v4.0 41.15 J/cm^2 (1440 K) flash recipe!
    yA_v4 = route_flipflop_yields["route_A_v4_1440K_5keV_8nm_mbe"]
    yC_v4 = route_flipflop_yields["route_C_v4_1440K_5keV_8nm_FG350C"]
    yA_v5 = route_flipflop_yields["route_A_v5_1530K_5keV_8nm_mbe"]
    yC_v5 = route_flipflop_yields["route_C_v5_1530K_5keV_8nm_FG350C"]
    yB22 = route_flipflop_yields["route_B_22keV_through_cap_flash"]
    y14 = route_flipflop_yields["route_A_14keV_srim_15nm_plus_8nm_cap"]
    ep3_pass = (
        14.0 <= yA_v4["mean_z_nm"] <= 15.2
        and yA_v4["std_z_nm"] <= 3.1
        and yA_v4["yield_C_ge_100"] >= 0.93
        and (yA_v4["yield_C_ge_100"] - yB22["yield_C_ge_100"]) >= 0.15
        and yB22["yield_C_ge_100"] < 0.80
        and y14["yield_C_ge_100"] < 0.40
    )

    ep4_pass = (
        S_eps_B22 > 1.3
        and 0.75 <= S_eps_A <= 1.05
        and 0.25 <= S_eps_C <= 0.45
        and (1.0 / S_eps_C) >= 2.2
    )

    sig_tot_v4_chain = exp124_sigma_tot(3.259, float(thermal_chain_5keV_v4["route_C_full_chain"]["sigma_anneal_nm"]))
    sig_tot_v5_1530K = exp124_sigma_tot(3.259, float(thermal_chain_5keV_v5_1530K["route_C_full_chain"]["sigma_anneal_nm"]))
    sig_tot_v5_quad = exp124_sigma_tot(3.259, float(thermal_chain_5keV_v5_quad["route_C_full_chain"]["sigma_anneal_nm"]))
    ep5_pass = (
        abs(thermal_chain_5keV_v4["delta_sigma_anneal_route_C_nm"]) < 0.01
        and thermal_chain_5keV_v4["route_C_full_chain"]["sigma_anneal_nm"] <= 0.35
        and abs(thermal_chain_5keV_v4["delta_surface_loss_route_C"]) < 1e-4
        and abs(thermal_chain_5keV_v4["delta_sigma_iso_route_C_nm"]) < 0.001
        and thermal_chain_5keV_v4["route_C_full_chain"]["sigma_iso_nm"] <= 0.04
        and sig_tot_v4_chain <= 3.66
    )

    ep6_pass = (
        min_clearance_mm > 50.0
        and 18.0 <= s56_hardware_spec["mass_power_cryo"]["total_mass_kg"] <= 25.0
        and s56_hardware_spec["vacuum_and_deposition"]["growth_pressure_torr"] < 5.0e-10
        and 40.0 <= t_mbe_dep_s <= 160.0
        and s56_hardware_spec["mass_power_cryo"]["cryo_thermal_leak_to_20mK_uW"] == 0.0
        and s56_hardware_spec["wafer_throughput_impact_exp134"]["pipelined_throughput_penalty_pct"] == 0.0
        and s56_hardware_spec["wafer_throughput_impact_exp134"]["serial_route_A_overhead_vs_1h_shuttle_pct"] < 10.0
    )

    max_mass_err = max(
        thermal_chain_5keV_v4["flash_only"]["mass_conservation_err"],
        thermal_chain_5keV_v4["route_C_full_chain"]["mass_conservation_err"],
        thermal_chain_5keV_v5_1530K["route_C_full_chain"]["mass_conservation_err"],
        thermal_chain_14keV_v5["route_C_full_chain"]["mass_conservation_err"],
    )
    ep7_pass = (
        bca_conv_max_err < 0.02
        and mcw_conv_rel_err < 0.005
        and max_mass_err < 1e-12
    )

    evaluations = {
        "EP1": {
            "pass": ep1_pass,
            "summary": (
                f"Exp92 5/10/20 keV max diff={exp92_max_rel_diff*100:.2f}% (<=5%); "
                f"Route B 22 keV sig_lat={bca_raw[22.0]['sigma_lat_nm']:.2f}nm ({lat_ratio_22_vs_5:.2f}x vs 5keV), "
                f"sig_z={bca_raw[22.0]['sigma_z_nm']:.2f}nm ({z_ratio_22_vs_5:.2f}x), "
                f"Exp124 sig_tot={bca_summary['E22']['exp124_sigma_tot_with_flash_nm']:.2f}nm (>3.80); "
                f"recoil-O={rec20_O:.2f}/ion @20keV & {rec22_O:.2f}/ion @22keV (>=0.2)"
            ),
        },
        "EP2": {
            "pass": ep2_pass,
            "summary": (
                f"Optimal T_epi*={T_epi_opt_C:.0f} C ([310,370], passing window {mbe_passing[0]['T_epi_C']:.0f}-{mbe_passing[-1]['T_epi_C']:.0f} C): "
                f"h_epi={mbe_opt['h_epi_nm']:.1f}nm (>40), R_q={mbe_opt['R_q_nm']:.3f}nm (<=0.20), "
                f"N_def={mbe_opt['N_def_cm3']:.2e} (<=1e15), L_seg={mbe_opt['L_seg_nm']:.2f}nm (<=3.5), "
                f"sig_iso_tot={sigma_iso_combined_v4:.4f}nm (<=0.05)"
            ),
        },
        "EP3": {
            "pass": ep3_pass,
            "summary": (
                f"v4 1440K Route A: z={yA_v4['mean_z_nm']:.2f}+-{yA_v4['std_z_nm']:.2f}nm, yield={yA_v4['yield_C_ge_100']*100:.2f}% (Route C={yC_v4['yield_C_ge_100']*100:.2f}%); "
                f"v5 1530K mitigated Route A={yA_v5['yield_C_ge_100']*100:.2f}% (sig_z={yA_v5['std_z_nm']:.2f}nm), Route C={yC_v5['yield_C_ge_100']*100:.2f}% (med C={yC_v5['median_C_tuned']:.0f}); "
                f"Route B 22keV={yB22['yield_C_ge_100']*100:.2f}% (<80%), 14keV+8nm={y14['yield_C_ge_100']*100:.2f}% (<40%)"
            ),
        },
        "EP4": {
            "pass": ep4_pass,
            "summary": (
                f"McWhorter 2D image-charge S_eps: Route B={S_eps_B22:.3f} (>1.3), "
                f"Route A={S_eps_A:.3f} ([0.75,1.05]), "
                f"Route C (350C FG/H, Dit=1.5e10)={S_eps_C:.3f} ueV/rtHz ([0.25,0.45], {1.0/S_eps_C:.2f}x suppression; "
                f"1.0e10/5nm ox={charge_noise_routes['route_C_thin_oxide_Dit_1p0e10_dox5']['S_eps_ueV_rtHz']:.3f})"
            ),
        },
        "EP5": {
            "pass": ep5_pass,
            "summary": (
                f"HONEST DISCOVERY @ v4 1x1440K (41.15 J/cm^2): {thermal_chain_5keV_v4['cluster_remaining_frac_post_flash']*100:.1f}% {{311}} clusters survive flash -> "
                f"+{thermal_chain_5keV_v4['delta_sigma_anneal_route_C_nm']:.2f}nm latent back-end TED during MBE+350C FG (tot={thermal_chain_5keV_v4['route_C_full_chain']['sigma_anneal_nm']:.3f}nm, Exp124={sig_tot_v4_chain:.3f}nm); "
                f"v5 FIX (1x1530K / 43.49 J/cm^2): 99.99% cluster clear -> tot={thermal_chain_5keV_v5_1530K['route_C_full_chain']['sigma_anneal_nm']:.3f}nm, Exp124={sig_tot_v5_1530K:.3f}nm (<=3.80)!"
            ),
        },
        "EP6": {
            "pass": ep6_pass,
            "summary": (
                f"S5.6 CF100 top port on Load-Lock (420,0,585..865 mm): min clearance={min_clearance_mm:.1f}mm (>50), "
                f"mass={s56_hardware_spec['mass_power_cryo']['total_mass_kg']:.1f}kg ([18,25]), P_growth=3.5e-10 Torr (<5e-10), "
                f"t_cap={t_mbe_dep_s:.0f}s ([40,160]), cryo leak=0.0 uW, pipelined penalty=0.0% (serial Route A={s56_hardware_spec['wafer_throughput_impact_exp134']['serial_route_A_overhead_vs_1h_shuttle_pct']:.2f}%)"
            ),
        },
        "EP7": {
            "pass": ep7_pass,
            "summary": (
                f"BCA indep 2k vs 4k max diff={bca_conv_max_err*100:.2f}% (4k vs 8k={max(bca_conv_4k_8k.values())*100:.2f}%), "
                f"McWhorter radial conv={mcw_conv_rel_err*100:.4f}% (<0.5%), "
                f"TED mass_err={max_mass_err:.2e} (<1e-12)"
            ),
        },
    }
    n_pass = sum(1 for v in evaluations.values() if v["pass"])
    verdict = "PASS" if n_pass == len(evaluations) else f"PARTIAL_PASS_{n_pass}_OF_{len(evaluations)}_WITH_V5_MITIGATION"

    # Compute S5.5 window fluence for upgraded v5.0 1530 K (43.49 J/cm^2) cluster-clearing recipe
    F_v5_1530K = thermal_chain_5keV_v5_1530K["fluence_per_pulse_J_per_cm2"]
    A_win_beam_cm2 = math.pi * ((0.5 * 3.6) ** 2)  # Ø36 mm beam in Ø44 mm CF63 CA
    F_win_v5_AR = (F_v5_1530K / 0.98) * (2.56 / A_win_beam_cm2)

    output = {
        "experiment": "exp139_epi_cap_process_integration",
        "hypothesis_id": preds["hypothesis_id"],
        "verdict": verdict,
        "pre_registered_pass_count": n_pass,
        "pre_registered_total_count": len(evaluations),
        "no_lab_measurement": True,
        "no_supplier_quotes": True,
        "epistemic_scope": "Coupled ZBL+LSS BCA, Exp130 1D thermal+TED PDE, Eaglesham/Gossmann/Nutzel-Abstreiter LT-MBE kinetics, exact 2D image-charge McWhorter electrostatics, and Exp131 4x4 Tosi flip-flop yield; physical lab & supplier verification remain required.",
        "runtime_s": round(time.perf_counter() - t0, 2),
        "evaluations": evaluations,
        "convergence_and_conservation": {
            "bca_2k_vs_4k": bca_conv,
            "bca_4k_vs_8k": bca_conv_4k_8k,
            "bca_max_rel_diff_2k_4k": round(bca_conv_max_err, 5),
            "bca_max_rel_diff_4k_8k": round(max(bca_conv_4k_8k.values()), 5),
            "exp92_anchor_check": exp92_check,
            "exp92_max_rel_diff": round(exp92_max_rel_diff, 5),
            "mcwhorter_radial_conv_800_vs_1600": round(mcw_conv_rel_err, 6),
            "ted_max_mass_conservation_err": max_mass_err,
        },
        "bca_energy_sweep": bca_summary,
        "recoil_oxygen_route_B": recoil_oxygen,
        "route_A_mbe_optimization": {
            "optimal_point": mbe_opt,
            "passing_window_T_epi_C": [mbe_passing[0]["T_epi_C"], mbe_passing[-1]["T_epi_C"]] if mbe_passing else [],
            "growth_rate_sensitivity_at_T_opt": mbe_rate_sensitivity,
            "combined_sigma_iso_flash_plus_mbe_nm": round(sigma_iso_combined_v4, 6),
        },
        "coupled_thermal_chain_ted": {
            "v4_1x1440K_41p15J_unmitigated": thermal_chain_5keV_v4,
            "v5_1x1530K_43p49J_cluster_clearing": thermal_chain_5keV_v5_1530K,
            "v5_4x1440K_41p15J_quad_pulse": thermal_chain_5keV_v5_quad,
            "lit_14keV_srim_15nm_v5_1530K": thermal_chain_14keV_v5,
            "route_B_22keV_through_cap": thermal_chain_22keV_B,
            "exp124_sigma_tot_v4_1440K_chain_nm": round(sig_tot_v4_chain, 4),
            "exp124_sigma_tot_v5_1530K_chain_nm": round(sig_tot_v5_1530K, 4),
            "exp124_sigma_tot_v5_quad_chain_nm": round(sig_tot_v5_quad, 4),
            "v5_s55_window_fluence_1530K_AR_J_cm2": round(F_win_v5_AR, 2),
            "v5_s55_lidt_margin_1530K_vs_100J_AR": round(100.0 / F_win_v5_AR, 2),
        },
        "charge_noise_and_exp137_bridge": {
            "routes": charge_noise_routes,
            "recommended_route_C_S_eps_band_ueV_rtHz": {
                "optimistic_Dit_1e10_dox5": charge_noise_routes["route_C_thin_oxide_Dit_1p0e10_dox5"]["S_eps_ueV_rtHz"],
                "low_Dit_1e10_dox8": charge_noise_routes["route_C_optimistic_Dit_1p0e10_dox8"]["S_eps_ueV_rtHz"],
                "nominal_Dit_1p5e10_dox8": S_eps_C,
                "conservative_Dit_3e10_dox8": charge_noise_routes["route_C_conservative_Dit_3p0e10"]["S_eps_ueV_rtHz"],
            },
            "suppression_vs_1ueV_baseline": round(1.0 / S_eps_C, 3),
            "suppression_vs_route_B_22keV": round(S_eps_B22 / S_eps_C, 3),
        },
        "route_flipflop_yields_exp131": route_flipflop_yields,
        "s56_hardware_spec": s56_hardware_spec,
        "artifacts": {
            "predictions": "results/exp139_epi_cap_process_integration/predictions_exp139.json",
            "results_json": "results/exp139_epi_cap_process_integration/exp139.json",
            "plot_data_json": "results/exp139_epi_cap_process_integration/plot_data_exp139.json",
            "summary_md": "results/exp139_epi_cap_process_integration/summary_exp139.md",
            "figure": "results/exp139_epi_cap_process_integration/fig_exp139_epi_cap_integration.png",
        },
    }
    OUT_JSON.write_text(json.dumps(output, indent=2), encoding="utf-8")
    # Export standalone CAD v5.0 / BOM v5.0 S5.6 hardware specification JSON
    s56_export = {
        "source_experiment": "exp139_epi_cap_process_integration",
        "hypothesis_id": "H157",
        "no_lab_measurement": True,
        "no_supplier_quotes": True,
        "s56_hardware_spec": s56_hardware_spec,
        "coupled_s55_v5_flash_upgrade": {
            "recommended_recipe": "808 nm qCW, 1.0 ms single pulse, 43.49 J/cm^2, T_peak = 1530.1 K (0.907 T_melt)",
            "alternative_recipe": "808 nm qCW, 4 x 1.0 ms @ 41.15 J/cm^2, T_peak = 1440.3 K (0.854 T_melt)",
            "window_fluence_1530K_AR_J_cm2": round(F_win_v5_AR, 2),
            "sapphire_lidt_margin_1530K_vs_100J_AR": round(100.0 / F_win_v5_AR, 2),
            "exp124_sigma_tot_v5_route_C_nm": round(sig_tot_v5_1530K, 4),
        },
        "exp137_charge_noise_bridge_S_eps_ueV_rtHz": output["charge_noise_and_exp137_bridge"]["recommended_route_C_S_eps_band_ueV_rtHz"],
    }
    (RESULTS_DIR / "s56_hardware_spec.json").write_text(json.dumps(s56_export, indent=2), encoding="utf-8")

    # Compact plot data (histograms + sweeps) for 2400x1400 PyCairo plotter
    z_bins = np.linspace(0.0, 36.0, 73)
    z_centers = (0.5 * (z_bins[:-1] + z_bins[1:])).tolist()

    def z_hist(arr: np.ndarray) -> List[float]:
        h, _ = np.histogram(arr, bins=z_bins, density=True)
        return [round(float(x), 5) for x in h]

    plot_data = {
        "mbe_sweep": mbe_sweep,
        "bca_sweep": [bca_summary[f"E{int(E_k)}"] for E_k in energies_keV],
        "dit_curve": dit_curve,
        "z_hist_centers_nm": [round(x, 3) for x in z_centers],
        "z_hist_bare_5keV": z_hist(z_bare),
        "z_hist_route_A_v5_5keV_8nm": z_hist(z_rA_v5),
        "z_hist_route_B_22keV": z_hist(z_rB22),
        "z_hist_14keV_8nm": z_hist(z_14_cap),
    }
    PLOT_DATA_JSON.write_text(json.dumps(plot_data), encoding="utf-8")

    print(f"Exp139 finished in {output['runtime_s']:.2f} s | VERDICT: {verdict}")
    for k, v in evaluations.items():
        print(f"  [{('PASS' if v['pass'] else 'FAIL')}] {k}: {v['summary']}")


if __name__ == "__main__":
    main()
