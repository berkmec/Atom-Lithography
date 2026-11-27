"""Pytest verification suite for Exp125 (Risk R7 magnet/shield, 5-stage cryo/RF, Risk R8 valley MC).

Run with: python3 -B -m pytest -p no:cacheprovider tests/test_exp125.py -v
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = ROOT / "experiments" / "exp125_cryo_magnet_readout"
RES_DIR = ROOT / "results" / "exp125_cryo_magnet_readout"
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

import ancilla_valley_r8 as r8
import cryo_rf_solver as cryo
import magnet_solver as ms


# ---------------------------------------------------------------------------
# 1. Exact Biot-Savart & Electromagnetic Law Tests
# ---------------------------------------------------------------------------
def test_circular_loop_on_axis_analytical_formula():
    """Verify exact Biot-Savart against textbook on-axis formula Bz = mu0*I*a^2 / (2*(a^2+z^2)^(3/2))."""
    a = 0.08
    I = 125.0
    z_pts = np.array([-0.15, -0.04, 0.0, 0.05, 0.22])
    r_pts = np.zeros_like(z_pts)
    Br, Bz, Ap = ms.filament_field_and_aphi(np.array([a]), np.array([0.0]), np.array([I]), r_pts, z_pts)
    Bz_exact = ms.MU0 * I * a ** 2 / (2.0 * (a ** 2 + z_pts ** 2) ** 1.5)
    assert np.allclose(Bz, Bz_exact, rtol=1e-12, atol=1e-15)
    assert np.allclose(Br, 0.0, atol=1e-15)
    assert np.allclose(Ap, 0.0, atol=1e-15)


def test_small_m_crossover_smoothness():
    """Ensure small-m Taylor series matches elliptic formula seamlessly across m = 1e-4."""
    a, z0, I = 0.10, 0.0, 100.0
    z_obs = 0.05
    # Find rho near m = 1e-4: m ~ 4*a*rho / (a^2 + z^2)
    rho_lo = 3.0e-6  # m < 1e-4
    rho_hi = 3.3e-6  # m > 1e-4
    Br, Bz, Ap = ms.filament_field_and_aphi(
        np.array([a]), np.array([z0]), np.array([I]),
        np.array([rho_lo, rho_hi]), np.array([z_obs, z_obs])
    )
    # Near axis, Br and Ap scale linearly with rho
    assert abs((Br[1] / rho_hi) / (Br[0] / rho_lo) - 1.0) < 1e-4
    assert abs((Ap[1] / rho_hi) / (Ap[0] / rho_lo) - 1.0) < 1e-4
    assert abs(Bz[1] - Bz[0]) / Bz[0] < 1e-5


def test_superconducting_sphere_bem_analytical_benchmark():
    """Verify Meissner BEM solver against analytical superconducting sphere in uniform B0."""
    sp = ms.validate_superconducting_sphere_bem(radius=0.04, B0=0.10, n_rings=120)
    assert sp["K_phi_max_rel_err"] < 0.005
    assert sp["interior_max_B_over_B0"] < 0.005
    assert sp["exterior_r1p05_rel_err"] < 0.002


def test_coupled_magnet_r7_specs_and_maxwell():
    """Verify live coupled 8-coil + Nb Meissner cup solver meets CV1, CV2, CV3 and Maxwell laws."""
    coils, shield = ms.default_magnet_and_shield_geometry()
    res = ms.solve_coupled_magnet_system(coils, shield, target_B_sample=1.50, z_res=-0.155, r_res_max=0.025)

    # CV1: Sample field & homogeneity
    assert abs(res["sample"]["Bz_center_T"] - 1.50) < 1e-6
    assert res["sample"]["homogeneity_max_rel_Bz"] < 1.0e-4  # < 100 ppm

    # CV2: Resonator quiet zone & Meissner vortex-free regime
    assert res["resonator_zone"]["unshielded_max_B_T"] <= 0.25
    assert res["resonator_zone"]["shielded_max_B_T"] <= 0.05
    assert res["resonator_zone"]["shielded_max_Bz_mT"] <= 10.0
    assert res["resonator_zone"]["shielded_max_Br_mT"] <= 10.0
    assert res["nb_shield_check"]["meissner_vortex_free_4p2K"] is True
    assert res["nb_shield_check"]["screened_max_B_surf_mT"] < res["nb_shield_check"]["Bc1_Nb_4p2K_mT"]

    # CV3: NbTi critical current, hoop stress, quench
    assert max(cm["I_over_Ic"] for cm in res["coil_metrics"]) <= 0.55
    assert min(cm["temp_margin_K"] for cm in res["coil_metrics"]) >= 1.5
    assert max(cm["sigma_hoop_max_abs_MPa"] for cm in res["coil_metrics"]) <= 80.0
    assert res["quench_protection"]["T_hotspot_K"] <= 150.0
    assert res["quench_protection"]["V_max_V"] <= 500.0

    # Maxwell identities: div(B)=0, B=curl(A)
    mx = ms.verify_maxwell_identities(res["coils"], res["shield_rings"])
    assert mx["max_divB_rel"] < 1e-5
    assert mx["max_curlA_rel"] < 1e-5


def test_nbti_critical_surface_anchor():
    """Verify Bottura (2000) NbTi Jc(5 T, 4.2 K) = 2800 A/mm^2 and monotonic decay with B, T."""
    jc_5t = ms.nbti_jc_sc_A_per_m2(5.0, 4.2) / 1e6  # A/mm^2
    assert abs(jc_5t - 2800.0) < 1e-6
    assert ms.nbti_jc_sc_A_per_m2(2.0, 4.2) > ms.nbti_jc_sc_A_per_m2(5.0, 4.2) > ms.nbti_jc_sc_A_per_m2(8.0, 4.2)
    assert ms.nbti_jc_sc_A_per_m2(5.0, 2.0) > ms.nbti_jc_sc_A_per_m2(5.0, 4.2) > ms.nbti_jc_sc_A_per_m2(5.0, 6.5)
    assert ms.nbti_jc_sc_A_per_m2(12.0, 4.2) == 0.0  # > Bc2(4.2K) = 10.67 T


# ---------------------------------------------------------------------------
# 2. 5-Stage Cryo Thermal + RF SNR + Throughput Tests
# ---------------------------------------------------------------------------
def test_exp110_exp112_cryo_replication_gate():
    gate = cryo.replicate_exp110_exp112_gate()
    assert gate["ok"] is True
    assert abs(gate["exp110_NL58_mxc_uW"] - 5.2375752) < 1e-9
    assert abs(gate["exp110_NL58_4K_7p5mW_W"] - 1.482) < 1e-9
    assert abs(gate["exp112_NL163_4K_2p1mW_W"] - 0.2296) < 1e-9


def test_5stage_cryo_closure_20mk_and_1k():
    b20 = cryo.thermal_5stage_20mk(9000, 160, 7.8, include_system_overhead=True)
    assert b20["closes_pt410_all_stages"] is True
    assert b20["total"]["4K_W"] < 1.0
    assert b20["total"]["MXC_uW"] < 19.0
    assert b20["total"]["CP_uW"] < 200.0
    assert b20["total"]["Still_mW"] < 40.0
    assert b20["total"]["50K_W"] < 40.0

    b1k = cryo.thermal_3stage_1k(9000, 160, 7.8, include_system_overhead=True)
    assert b1k["closes_pt410_all_stages"] is True
    assert b1k["total"]["stage1K_mW"] < 100.0
    assert b1k["total"]["4K_W"] < 1.0


def test_rf_snr_margin_and_throughput():
    s20 = cryo.rf_readout_snr_budget(0.02, 1.4, delta_gamma=0.05)
    s1k = cryo.rf_readout_snr_budget(1.5, 3.0, delta_gamma=0.05)
    assert s20["tau_for_SNR10_ms"] < 1.0
    assert s1k["tau_for_SNR10_ms"] < 1.0
    assert s20["sweep_200pt_SNR10_ms"] < 100.0
    assert s1k["sweep_200pt_SNR10_ms"] < 100.0

    tp = cryo.throughput_comparison(9000)
    assert tp["baseline_20mK"]["certified_ModB_f1pct_per_day"] > 1.0e8
    assert tp["hot_1K_scenarios"]["moderate_R8_p0.85"]["slowdown_vs_20mK"] > 3.16


# ---------------------------------------------------------------------------
# 3. Risk R8 Silicon Diamond Lattice & Valley Interference Tests
# ---------------------------------------------------------------------------
def test_si_diamond_lattice_snapping():
    """Verify snapped coordinates lie on valid Si diamond-cubic sites with max snap distance <= sqrt(3)/4 a_Si."""
    rng = np.random.default_rng(7)
    x = rng.uniform(-10.0, 10.0, 5000)
    y = rng.uniform(-10.0, 10.0, 5000)
    z = rng.uniform(0.0, 15.0, 5000)
    sx, sy, sz = r8.snap_to_si_diamond_lattice(x, y, z)
    dist = np.sqrt((x - sx) ** 2 + (y - sy) ** 2 + (z - sz) ** 2)
    # Distance to nearest site in diamond lattice cannot exceed circumradius of Voronoi cell (< 0.5*a_Si)
    assert float(np.max(dist)) < 0.5 * r8.A_SI_NM
    # Check every snapped coordinate is either sublattice A (even multiples of a/2) or B (+ a/4)
    q = r8.A_SI_NM / 4.0
    qx = np.rint(sx / q).astype(int)
    qy = np.rint(sy / q).astype(int)
    qz = np.rint(sz / q).astype(int)
    assert np.allclose(sx, qx * q, atol=1e-10)
    is_sub_a = (qx % 2 == 0) & (qy % 2 == 0) & (qz % 2 == 0) & (((qx + qy + qz) // 2) % 2 == 0)
    is_sub_b = (qx % 2 != 0) & (qy % 2 != 0) & (qz % 2 != 0) & ((((qx - 1) + (qy - 1) + (qz - 1)) // 2) % 2 == 0)
    assert bool(np.all(is_sub_a | is_sub_b))


def test_exp118_replication_and_r8_breakeven():
    gate = r8.replicate_exp118_gate()
    assert gate["ok"] is True

    # Phase-sensitive Koiller 6-valley penalty increases monotonically as window narrows
    p_w4 = r8.mc_ancilla_yield(20.0, 100.0, 1e6, 1e10, "V2_koiller_6valley", n_samples=40_000, seed=125)["p_yield"]
    p_w2 = r8.mc_ancilla_yield(20.0, 10.0, 1e8, 1e10, "V2_koiller_6valley", n_samples=40_000, seed=125)["p_yield"]
    p_w1 = r8.mc_ancilla_yield(20.0, 3.0, 3.162e8, 3.162e9, "V2_koiller_6valley", n_samples=40_000, seed=125)["p_yield"]
    assert p_w4 >= 0.99
    assert 0.85 <= p_w2 <= 0.96
    assert p_w1 < 0.65

    be = r8.cost_breakeven_vs_20mk()
    assert 0.45 < be["p_crit_golden_frac_parity"] < be["p_crit_golden_cost_parity"] < 0.55


# ---------------------------------------------------------------------------
# 4. Persisted Artifact Integrity Tests
# ---------------------------------------------------------------------------
def test_exp125_artifacts_and_verdicts():
    required = [
        RES_DIR / "predictions_exp125.json",
        RES_DIR / "exp125.json",
        RES_DIR / "summary_exp125.md",
        RES_DIR / "fig_exp125_bfield_map.png",
        RES_DIR / "fig_exp125_thermal_snr.png",
    ]
    for p in required:
        assert p.exists() and p.stat().st_size > 1000, f"Missing or tiny artifact: {p}"

    # Verify PNG magic headers
    for png in (RES_DIR / "fig_exp125_bfield_map.png", RES_DIR / "fig_exp125_thermal_snr.png"):
        assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    data = json.loads((RES_DIR / "exp125.json").read_text(encoding="utf-8"))
    assert data["no_lab_measurement"] is True
    v = data["verdicts"]
    assert v["success"] is True
    for k in (
        "CV1_sample_homogeneity",
        "CV2_resonator_quiet_zone",
        "CV3_magnet_engineering",
        "CV4_5stage_cryo_closure",
        "CV5_rf_snr_margin",
        "CV6_risk_r8_valley_bound",
    ):
        assert v[k] is True, f"Verdict failed: {k}"
    assert data["magnet_r7"]["E_mag_parity_rel_diff"] < 0.025
    assert data["magnet_r7"]["convergence"]["quad_rel_err_8_vs_12"] < 1e-5
    assert data["magnet_r7"]["convergence"]["bem_sample_rel_err"] < 1e-5

    # CAD v3.0 coordinate & UHV chamber parity assertions (Carbon F4 closure)
    cad = data["magnet_r7"]["cad_geometry_mm"]
    env = cad["overall_envelope"]
    assert env["z_wafer_mm"] == 500.0
    assert env["z_span_machine_mm"] == [316.0, 612.0]
    assert env["chamber_inner_radius_mm_ref"] == 182.0
    assert env["radial_clearance_inside_chamber_mm"] == 6.0
    assert cad["resonator_carrier"]["z_center_machine_mm"] == 345.0
    assert data["magnet_r7"]["resonator_zone"]["z_res_machine_mm"] == 345.0
    assert cad["nb_meissner_cup"]["z_bot_machine_mm"] == 326.0
    assert cad["nb_meissner_cup"]["z_top_machine_mm"] == 364.0
    assert cad["cryoperm_outer_sleeve"]["z_bot_machine_mm"] == 320.0
    assert cad["cryoperm_outer_sleeve"]["z_top_machine_mm"] == 376.0


# ---------------------------------------------------------------------------
# 5. Wave 1B Obstacle Closure Tests (OBS-008, OBS-072, OBS-099, OBS-130)
# ---------------------------------------------------------------------------
def test_obs008_obs072_obs099_horizontal_inplane_vector_magnet_and_quench_eddy():
    """Live solver test for horizontal in-plane split-Helmholtz vector magnet, series PSU, Cryoperm 2R/t & eddy."""
    ivm = ms.solve_horizontal_inplane_vector_magnet(
        target_B_parallel_T=0.1785,
        r_writehead_m=0.01131,
        z_wafer_tol_m=0.0005,
        target_series_current_A=28.0,
        hts_lead_rating_A=320.0,
    )
    # OBS-008: Strict in-plane field eliminating perpendicular Abrikosov vortices in NbTiN
    vx = ivm["inplane_vortex_safety_obs008"]
    assert vx["inplane_limit_satisfied"] is True
    assert vx["max_B_perp_z0_uT"] == 0.0
    assert vx["vortex_free_10um_pads"] is True
    assert vx["vortex_free_2um_feedlines"] is True
    assert vx["max_intrinsic_tilt_deg"] < 0.05
    assert vx["homogeneity_16x16mm_ppm"] < 50.0  # r <= 11.31 mm uniformity (OBS-072)

    # OBS-072: Equal-current series winding (1 PSU, 1 persistent switch), tie flanges, Cryoperm 2R/t
    ser = ivm["series_winding_topology"]
    assert ser["n_independent_main_psus"] == 1
    assert ser["n_persistent_switches"] == 1
    assert ser["n_trim_psus"] == 1
    assert ser["max_I_over_Ic_at_1p5T"] < 0.55

    fl = ivm["structural_tie_flanges_obs072"]
    assert fl["zero_floating_coils"] is True
    assert abs(fl["net_axial_force_residual_kN"]) < 1e-3
    assert fl["safety_factor"] > 5.0

    # Thin-wall 2R/t flux concentration factor in Cryoperm-10
    cp_dual = ivm["stray_field_and_cryoperm_obs072"]["redesigned_dual_layer_cryoperm"]
    assert cp_dual["flux_concentration_transverse_2R_over_t"] > 5.0
    assert cp_dual["wall_saturated"] is False
    assert cp_dual["wall_saturation_margin"] > 4.0

    # Legacy 2 mm Cryoperm explicitly exposes thin-wall 2R/t concentration (40x at R=40mm, t=2mm)
    cp_sat = ms.cryoperm_cylindrical_sf(
        mu_r=20000.0, thickness_m=0.002, radius_m=0.040, length_m=0.056,
        b_radial_ext_T=0.04856, b_axial_ext_T=0.07546,
    )
    assert math.isclose(cp_sat["flux_concentration_transverse_2R_over_t"], 40.0, rel_tol=1e-6)
    assert cp_sat["wall_saturated"] is True
    assert cp_sat["B_wall_peak_T"] > 0.75

    # OBS-099: >= 300 A HTS leads + radially-slotted AlN chuck quench eddy reduction
    hts = ivm["hts_leads_and_quench_eddy_obs099"]["hts_leads"]
    assert hts["rated_current_A"] >= 300.0
    assert hts["meets_300A_spec"] is True
    assert hts["operating_current_ESR_1p50T_A"] < hts["rated_current_A"]

    ed_mono = ivm["hts_leads_and_quench_eddy_obs099"]["chuck_eddy_legacy_mono_1p5T_RRR50"]
    ed_slot = ivm["hts_leads_and_quench_eddy_obs099"]["chuck_eddy_redesigned_slotted_AlN_1p5T"]
    ed_m4 = ivm["hts_leads_and_quench_eddy_obs099"]["chuck_eddy_redesigned_slotted_AlN_M4"]
    assert ed_mono["E_eddy_J"] > 50.0 and ed_mono["T_chuck_peak_K"] > 20.0
    assert ed_slot["E_eddy_J"] < 0.2 and ed_slot["T_chuck_peak_K"] < 6.0
    assert ed_m4["E_eddy_J"] < 0.01 and ed_m4["T_chuck_peak_K"] < 1.0
    assert ivm["hts_leads_and_quench_eddy_obs099"]["eddy_energy_reduction_factor_1p5T"] > 1000.0


def test_obs130_unified_ld400_pt420_14uW_capacity_map():
    """Verify authoritative 6-stage LD400+PT420 14 uW MXC capacity map in Exp125 cryo_rf_solver."""
    cap = cryo.CAPACITIES_LD400_PT420_UNIFIED
    assert cap["MXC_20mK_uW"] == 14.0
    assert cap["4K_W"] == 2.0
    assert cap["Still_0p8K_mW"] == 40.0
    assert cap["CP_100mK_uW"] == 400.0
    b20 = cryo.thermal_5stage_20mk(9000, 160, 7.8, include_system_overhead=True)
    assert b20["closes_ld400_pt420_unified_14uW"] is True
    assert b20["total"]["MXC_uW"] <= 14.0
