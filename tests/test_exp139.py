"""Verification test suite for Exp139 (H157: Integrated 8 nm 28Si Epi Cap + ms Flash Anneal
+ Si/SiO2 D_it/S_eps Interface Charge-Noise Bridge & S5.6 Hardware Specification)."""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = REPO_ROOT / "experiments" / "exp139_epi_cap_process_integration"
RES_DIR = REPO_ROOT / "results" / "exp139_epi_cap_process_integration"

if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

from epi_cap_physics139 import (  # noqa: E402
    build_zbl_scattering_table,
    evaluate_charge_noise_routes,
    evaluate_lt_mbe_kinetics,
    mcwhorter_geom_integrals,
    run_coupled_thermal_chain_ted,
    simulate_bca_31p_in_si,
    simulate_recoil_oxygen_through_oxide,
)


def test_lt_mbe_competing_tradeoff_and_optimum() -> None:
    m250 = evaluate_lt_mbe_kinetics(250.0)
    m345 = evaluate_lt_mbe_kinetics(345.0)
    m450 = evaluate_lt_mbe_kinetics(450.0)

    # Eaglesham h_epi increases with T; R_q and N_def decrease; L_seg increases
    assert m250["h_epi_nm"] < m345["h_epi_nm"] < m450["h_epi_nm"]
    assert m250["R_q_nm"] > m345["R_q_nm"] > m450["R_q_nm"]
    assert m250["N_def_cm3"] > m345["N_def_cm3"] > m450["N_def_cm3"]
    assert m250["L_seg_nm"] < m345["L_seg_nm"] < m450["L_seg_nm"]

    # Interior physical optimum around 345 C strictly outperforms extremes
    assert m345["meets_mbe_criteria"] is True
    assert m250["meets_mbe_criteria"] is False
    assert m450["meets_mbe_criteria"] is False
    assert m345["quality_cost"] < m250["quality_cost"]
    assert m345["quality_cost"] < m450["quality_cost"]


def test_mcwhorter_exact_scaling_and_grid_convergence() -> None:
    g800 = mcwhorter_geom_integrals(14.5, n_r=800)
    g1600 = mcwhorter_geom_integrals(14.5, n_r=1600)
    assert abs(g1600["I_ff_eV2_nm2"] - g800["I_ff_eV2_nm2"]) / g1600["I_ff_eV2_nm2"] < 5e-3
    assert abs(g1600["I_Ez_V2"] - g800["I_Ez_V2"]) / g1600["I_Ez_V2"] < 5e-3

    # Exact sqrt(D_it) scaling at zero bulk-defect floor
    c_hi = evaluate_charge_noise_routes(14.5, 1.0e11, bulk_defect_N_cm3=0.0)
    c_lo = evaluate_charge_noise_routes(14.5, 1.0e10, bulk_defect_N_cm3=0.0)
    assert math.isclose(c_hi["S_eps_ueV_rtHz"] / c_lo["S_eps_ueV_rtHz"], math.sqrt(10.0), rel_tol=1e-3)

    # Buried-donor electric-field noise strictly decreases with deeper donor burial
    c_deep = evaluate_charge_noise_routes(23.0, 1.0e11, bulk_defect_N_cm3=0.0)
    assert c_deep["I_Ez_V2"] < c_hi["I_Ez_V2"]


def test_bca_and_recoil_oxygen_physics() -> None:
    from epi_cap_physics139 import evaluate_fga_passivation_kinetics, evaluate_gate_oxide_and_regrowth_interface
    tbl = build_zbl_scattering_table(n_eps=40, n_rho=40, n_quad=48)
    b5 = simulate_bca_31p_in_si(5.0, 600, tbl, seed=42)
    b22 = simulate_bca_31p_in_si(22.0, 600, tbl, seed=43)
    # OBS-039: Corrected infinite-domain ZBL BCA matches 3D iradina (5 keV Rp~10.3 nm, 22 keV Rp~33-34 nm)
    assert 9.0 < b5["Rp_nm"] < 12.0
    assert 3.8 < b5["sigma_lat_nm"] < 5.2
    assert 28.0 < b22["Rp_nm"] < 40.0
    assert b22["sigma_lat_nm"] > 2.0 * b5["sigma_lat_nm"]
    assert b22["sigma_z_nm"] > 2.0 * b5["sigma_z_nm"]

    # OBS-129 & OBS-138: Full multilayer SiO2/Si recoil-O + primary transport
    rec22 = simulate_recoil_oxygen_through_oxide(22.0, 1.5, 600, tbl, seed=44)
    assert 0.2 < rec22["O_injected_into_Si_per_ion"] < 1.2
    assert rec22["mean_O_depth_in_Si_nm"] > 0.8
    assert rec22["primary_Rp_in_Si_nm"] > 25.0
    rec5 = simulate_recoil_oxygen_through_oxide(5.0, 1.5, 600, tbl, seed=45)
    assert rec5["O_injected_into_Si_per_ion"] > 0.3

    # OBS-094: 1 atm FGA succeeds in 15 min; UHV leak-valve fails by 6-8 orders
    fg_1atm = evaluate_fga_passivation_kinetics(38.0)
    fg_uhv = evaluate_fga_passivation_kinetics(5e-6)
    assert fg_1atm["feasible_15min_passivation"] is True
    assert fg_uhv["feasible_15min_passivation"] is False
    assert fg_uhv["required_passivation_time_years"] > 10.0

    # OBS-095: Gate oxide Si consumption 0.44*d_ox & pre-MBE regrowth traps
    ox_th = evaluate_gate_oxide_and_regrowth_interface(8.0, 8.0, "thermal_SiO2")
    ox_ald = evaluate_gate_oxide_and_regrowth_interface(8.0, 8.0, "ald_lowT")
    assert math.isclose(ox_th["si_consumed_nm"], 3.52, abs_tol=1e-3)
    assert ox_ald["si_consumed_nm"] == 0.0
    assert ox_th["regrowth_interface_D_it_cm2_eV"] > 0.0


def test_coupled_thermal_chain_v4_discovery_and_v5_fix() -> None:
    from epi_cap_physics139 import KineticsParams
    ch_v4 = run_coupled_thermal_chain_ted(10.31, 5.10, T_epi_C=345.0, t_mbe_s=80.0, T_peak_K=1440.0, n_flash_pulses=1)
    ch_v5 = run_coupled_thermal_chain_ted(10.31, 5.10, T_epi_C=345.0, t_mbe_s=80.0, T_peak_K=1530.0, n_flash_pulses=1)
    ch_v5_hi = run_coupled_thermal_chain_ted(10.31, 5.10, T_epi_C=345.0, t_mbe_s=80.0, T_peak_K=1530.0, n_flash_pulses=1, C_cl_peak_cm3=4.5e20)

    assert ch_v4["route_C_full_chain"]["mass_conservation_err"] < 1e-12
    assert ch_v5["route_C_full_chain"]["mass_conservation_err"] < 1e-12

    # OBS-038 FIX: With realistic Em_I=0.90 eV + I-V recombination, v4 1440 K no longer freezes monomers at 345 C!
    assert ch_v4["delta_sigma_anneal_route_C_nm"] < 0.05
    assert ch_v4["route_C_full_chain"]["sigma_anneal_nm"] <= 0.50
    assert ch_v5["cluster_remaining_frac_post_flash"] < 1e-3
    assert ch_v5["route_C_full_chain"]["sigma_anneal_nm"] <= 0.50
    assert ch_v5["T_peak_over_Tmelt"] < 0.92
    # High iradina cascade damage (30% of 99.6 vac/ion) increases TED broadening significantly
    assert ch_v5_hi["route_C_full_chain"]["sigma_anneal_nm"] > ch_v5["route_C_full_chain"]["sigma_anneal_nm"]


def test_exp139_json_integrity_and_honest_verdicts() -> None:
    preds = json.loads((RES_DIR / "predictions_exp139.json").read_text(encoding="utf-8"))
    exp = json.loads((RES_DIR / "exp139.json").read_text(encoding="utf-8"))

    assert preds["hypothesis_id"] == "H157"
    assert preds["no_lab_measurement"] is True
    assert exp["hypothesis_id"] == "H157"
    assert exp["no_lab_measurement"] is True
    assert exp["no_supplier_quotes"] is True

    # Core structural predictions must PASS
    for ep in ("EP1", "EP2", "EP6"):
        assert exp["evaluations"][ep]["pass"] is True, f"{ep} should PASS"

    # OBS-006, OBS-039 & OBS-095 honest verdicts: 5 keV true BCA + 8 nm cap + regrowth traps
    # fails old 93% EP3 yield, pushes Route A S_eps slightly above 1.05 (1.078), and breaches 3.80 nm ceiling!
    assert exp["evaluations"]["EP3"]["pass"] is False
    assert exp["evaluations"]["EP5"]["pass"] is False
    assert exp["charge_noise_and_exp137_bridge"]["routes"]["route_A_5keV_post_anneal_mbe_unpassivated"]["S_eps_ueV_rtHz"] > 1.0
    assert exp["charge_noise_and_exp137_bridge"]["routes"]["route_C_nominal_FG350C_Dit_1p5e10"]["S_eps_ueV_rtHz"] <= 0.45
    th = exp["coupled_thermal_chain_ted"]
    assert th["exp124_sigma_tot_v5_1530K_chain_nm"] > 4.40
    assert th["v5_s55_lidt_margin_1530K_vs_100J_AR"] >= 3.0
    assert exp["fga_passivation_kinetics_obs094"]["dedicated_1atm_furnace_5pctH2_38Torr"]["feasible_15min_passivation"] is True
    assert exp["fga_passivation_kinetics_obs094"]["uhv_leak_valve_high_5e_5Torr"]["feasible_15min_passivation"] is False


def test_route_yield_ordering_and_exp137_bridge() -> None:
    exp = json.loads((RES_DIR / "exp139.json").read_text(encoding="utf-8"))
    y = exp["route_flipflop_yields_exp131"]

    # OBS-006 honest yield under true 3D BCA/iradina 5 keV (Rp~10.3 nm, sig_z~5.1 nm):
    # Locked 8 nm cap collapses to ~55-72% (well below legacy 95%), thin 4 nm cap recovers partially (~72-82%),
    # and 3 keV / 121Sb trade-off options outperform 5 keV + 8 nm cap!
    assert y["route_C_v5_1530K_5keV_8nm_FG350C"]["yield_C_ge_100"] < 0.78
    assert y["route_C_v5_5keV_thin_4nm_cap_opt"]["yield_C_ge_100"] > y["route_C_v5_1530K_5keV_8nm_FG350C"]["yield_C_ge_100"]
    assert y["tradeoff_3keV_31P_6nm_cap_needs_cryoJFET_IBIC"]["yield_C_ge_100"] > y["route_C_v5_1530K_5keV_8nm_FG350C"]["yield_C_ge_100"]
    assert y["tradeoff_7p5keV_121Sb_3nm_cap_heavy_ion"]["yield_C_ge_100"] > y["route_C_v5_1530K_5keV_8nm_FG350C"]["yield_C_ge_100"]
    assert y["route_B_22keV_through_cap_flash"]["yield_C_ge_100"] < 0.25

    # Exp137 charge-noise bridge strictly suppresses S_eps below 0.45 ueV/rtHz (with 1 atm FGA)
    br = exp["charge_noise_and_exp137_bridge"]
    assert 0.25 <= br["recommended_route_C_S_eps_band_ueV_rtHz"]["nominal_Dit_1p5e10_dox8"] <= 0.45
    assert br["suppression_vs_1ueV_baseline"] >= 2.2
    assert br["suppression_vs_route_B_22keV"] >= 3.5


def test_s56_hardware_spec_cad_v5_and_bom_v5_ready() -> None:
    exp = json.loads((RES_DIR / "exp139.json").read_text(encoding="utf-8"))
    s56 = exp["s56_hardware_spec"]

    assert s56["subsystem_id"] == "S5.6"
    assert s56["cad_v5_geometry"]["clearances_vs_cad_v4_mm"]["min_clearance_mm"] > 50.0
    assert 18.0 <= s56["mass_power_cryo"]["total_mass_kg"] <= 25.0
    assert s56["mass_power_cryo"]["cryo_thermal_leak_to_20mK_uW"] == 0.0
    assert s56["vacuum_and_deposition"]["growth_pressure_torr"] < 5.0e-10
    assert 40.0 <= s56["vacuum_and_deposition"]["nominal_deposition_time_s"] <= 160.0
    assert s56["wafer_throughput_impact_exp134"]["pipelined_throughput_penalty_pct"] == 0.0
    assert s56["bom_v5_cost_estimate_usd"]["total_p10_usd"] < s56["bom_v5_cost_estimate_usd"]["total_p50_usd"] < s56["bom_v5_cost_estimate_usd"]["total_p90_usd"]


def test_png_and_summary_artifacts_valid() -> None:
    png = RES_DIR / "fig_exp139_epi_cap_integration.png"
    assert png.exists()
    raw = png.read_bytes()
    assert len(raw) > 80_000
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", raw[16:24])
    assert (w, h) == (2400, 1400)

    summary = (RES_DIR / "summary_exp139.md").read_text(encoding="utf-8")
    assert "no_lab_measurement = true" in summary
    assert "no_supplier_quotes = true" in summary
    assert "S5.6" in summary and "1530" in summary


def test_strict_portability_no_hardcoded_user_paths() -> None:
    forbidden = ("/" + "home/" + "berk", "/" + "run/media/" + "berk")
    files_to_check = (
        list(EXP_DIR.glob("*.py"))
        + list(RES_DIR.glob("*.json"))
        + list(RES_DIR.glob("*.md"))
        + [Path(__file__)]
    )
    for fp in files_to_check:
        text = fp.read_text(encoding="utf-8")
        for bad in forbidden:
            assert bad not in text, f"Hardcoded path '{bad}' found in {fp.relative_to(REPO_ROOT)}"
