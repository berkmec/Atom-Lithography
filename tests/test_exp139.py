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
    tbl = build_zbl_scattering_table(n_eps=40, n_rho=40, n_quad=120)
    b5 = simulate_bca_31p_in_si(5.0, 600, tbl, seed=42)
    b22 = simulate_bca_31p_in_si(22.0, 600, tbl, seed=43)
    assert 5.5 < b5["Rp_nm"] < 7.5
    assert 13.0 < b22["Rp_nm"] < 16.5
    assert b22["sigma_lat_nm"] > 2.0 * b5["sigma_lat_nm"]
    assert b22["sigma_z_nm"] > 1.7 * b5["sigma_z_nm"]

    rec = simulate_recoil_oxygen_through_oxide(22.0, 1.5, 600, tbl, seed=44)
    assert rec["O_injected_into_Si_per_ion"] > 0.3
    assert rec["mean_O_depth_in_Si_nm"] > 0.2


def test_coupled_thermal_chain_v4_discovery_and_v5_fix() -> None:
    ch_v4 = run_coupled_thermal_chain_ted(6.46, 2.88, T_epi_C=345.0, t_mbe_s=80.0, T_peak_K=1440.0, n_flash_pulses=1)
    ch_v5 = run_coupled_thermal_chain_ted(6.46, 2.88, T_epi_C=345.0, t_mbe_s=80.0, T_peak_K=1530.0, n_flash_pulses=1)

    assert ch_v4["route_C_full_chain"]["mass_conservation_err"] < 1e-12
    assert ch_v5["route_C_full_chain"]["mass_conservation_err"] < 1e-12

    # v4 1440 K leaves >10% undissolved {311} clusters -> significant back-end TED > 1.0 nm
    assert ch_v4["cluster_remaining_frac_post_flash"] > 0.10
    assert ch_v4["route_C_full_chain"]["sigma_anneal_nm"] > 1.0

    # v5 1530 K clears >99.9% of clusters -> suppresses back-end TED by >20x & stays <= 0.50 nm
    assert ch_v5["cluster_remaining_frac_post_flash"] < 1e-3
    assert ch_v5["route_C_full_chain"]["sigma_anneal_nm"] <= 0.50
    assert ch_v5["delta_sigma_anneal_route_C_nm"] < 0.05
    assert ch_v5["T_peak_over_Tmelt"] < 0.92


def test_exp139_json_integrity_and_honest_verdicts() -> None:
    preds = json.loads((RES_DIR / "predictions_exp139.json").read_text(encoding="utf-8"))
    exp = json.loads((RES_DIR / "exp139.json").read_text(encoding="utf-8"))

    assert preds["hypothesis_id"] == "H157"
    assert preds["no_lab_measurement"] is True
    assert exp["hypothesis_id"] == "H157"
    assert exp["no_lab_measurement"] is True
    assert exp["no_supplier_quotes"] is True

    # Core structural predictions must PASS
    for ep in ("EP1", "EP2", "EP4", "EP6"):
        assert exp["evaluations"][ep]["pass"] is True, f"{ep} should PASS"

    # Honest EP5 FAIL on v4.0 1440 K setpoint must not be hidden; v5.0 1530 K must fix Exp124 budget
    assert exp["evaluations"]["EP5"]["pass"] is False
    th = exp["coupled_thermal_chain_ted"]
    assert th["exp124_sigma_tot_v4_1440K_chain_nm"] > 3.80
    assert th["exp124_sigma_tot_v5_1530K_chain_nm"] <= 3.70
    assert th["v5_s55_lidt_margin_1530K_vs_100J_AR"] >= 3.0


def test_route_yield_ordering_and_exp137_bridge() -> None:
    exp = json.loads((RES_DIR / "exp139.json").read_text(encoding="utf-8"))
    y = exp["route_flipflop_yields_exp131"]

    # v5 Route C > v5 Route A > Route B (22 keV) > 14 keV+8nm > Bare 5 keV
    assert y["route_C_v5_1530K_5keV_8nm_FG350C"]["yield_C_ge_100"] >= 0.95
    assert y["route_A_v5_1530K_5keV_8nm_mbe"]["yield_C_ge_100"] >= 0.93
    assert y["route_B_22keV_through_cap_flash"]["yield_C_ge_100"] < 0.70
    assert y["route_A_14keV_srim_15nm_plus_8nm_cap"]["yield_C_ge_100"] < 0.40
    assert y["bare_5keV_uncapped_ref"]["yield_C_ge_100"] < 0.35

    # Exp137 charge-noise bridge strictly suppresses S_eps below 0.45 ueV/rtHz
    br = exp["charge_noise_and_exp137_bridge"]
    assert 0.25 <= br["recommended_route_C_S_eps_band_ueV_rtHz"]["nominal_Dit_1p5e10_dox8"] <= 0.45
    assert br["suppression_vs_1ueV_baseline"] >= 2.2
    assert br["suppression_vs_route_B_22keV"] >= 4.0


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
