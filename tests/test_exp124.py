"""Unit and physics verification tests for Exp124 (Ion Column Optics & 3D Anisotropic Yield).

Run with:
    python3 -B -m pytest -p no:cacheprovider tests/test_exp124.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "exp124_ion_column_optics"))

import column_physics as cp  # noqa: E402
import anisotropic_yield as ay  # noqa: E402

RES_DIR = ROOT / "results" / "exp124_ion_column_optics"


def test_historical_chain_reproduction_and_liouville_deficit():
    audit = cp.audit_historical_chain(ROOT)
    assert audit["max_anchor_rel_err"] < 1e-12
    liouv = audit["liouville_audit_attack91"]
    assert math.isclose(liouv["B_net_10keV_used_by_attack91_A_m2_sr"] / liouv["B_net_5keV_liouville_exact_A_m2_sr"], 2.0, rel_tol=1e-12)
    assert liouv["brightness_deficit_factor_at_5keV_10mrad"] > 1.80
    assert liouv["actual_r_geom_at_5keV_10mrad_Ti1_nm"] > 2.00


def test_live_laplace_solver_wronskian_and_aberration_crosschecks():
    # Live 2D axisymmetric Laplace + DOP853 ray-trace check on Arch-B immersion mini-lens
    cfg = cp.LensConfig(
        name="test_arch_b",
        pitch_mm=0.500, r_max_mm=0.250, z_max_mm=2.010,
        V_in_V=10000.0, V_land_V=5000.0,
        electrodes=[
            cp.ElectrodeSpec("E1", 0.200, 0.300, 0.150, 10000.0),
            cp.ElectrodeSpec("E2", 1.120, 1.280, 0.150, 1300.0),
            cp.ElectrodeSpec("E3", 1.660, 1.760, 0.150, 5000.0),
        ],
        nr=51, nz=201,
    )
    sol = cp.solve_axisymmetric_laplace(cfg)
    assert sol["max_pde_residual"] < 1e-4
    assert sol["E_gap_nom_MV_m"] < 12.0

    tr = cp.trace_lens_optics(sol, cfg)
    assert tr["wronskian_rel_drift"] < 1e-6
    assert tr["Cc_scherzer_mm"] > 0.0
    assert tr["Cc_scherzer_vs_raytrace_rel_diff"] < 0.01
    assert tr["Cs_scherzer_mm"] > 0.0
    assert tr["Cs_scherzer_vs_multipole_rel_diff"] < 0.02
    assert tr["kappa_c_invariant"] > 3.0


def test_wien_hda_and_boersch_subsystems():
    wien = cp.wien_mass_filter(E_ext_eV=10000.0, B_T=0.45, L_w_mm=80.0, L_drift_mm=70.0, gap_mm=12.0, slit_mm=0.20)
    assert wien["separation_over_slit"] >= 3.5
    assert wien["mass_resolving_power"] > 100.0

    hda = cp.hda_energy_filter(E_pass_eV=100.0, R0_mm=40.0, slit_mm=0.35, alpha_in_mrad=25.0)
    assert hda["dE_fwhm_eV"] <= 0.50
    assert 0.05 < hda["tau_gaussian_exact"] < 0.12

    c5 = cp.boersch_and_coulomb(5000.0)
    c10 = cp.boersch_and_coulomb(10000.0)
    c15 = cp.boersch_and_coulomb(15000.0)
    # Exact E^(-3/2) laminar space-charge scaling: 2^(1.5) = 2.8284
    assert math.isclose(c5["dr_sc_laminar_um"] / c10["dr_sc_laminar_um"], 2.0 ** 1.5, rel_tol=1e-9)
    assert math.isclose(c5["dr_sc_laminar_um"] / c15["dr_sc_laminar_um"], 3.0 ** 1.5, rel_tol=1e-9)
    assert c10["single_beamlet_Nbar_col"] < 0.01
    # OBS-103: f_img fixed to ~0.820 mm (not 0.5 mm) and 100 eV HDA space-charge guard enforced
    assert math.isclose(c10["f_img_mm"], 0.8202, rel_tol=1e-3)
    assert c10["sigma_coul_wafer_nm"] > 1.0  # 50 nA unguarded flood at f=0.820 mm
    hda_50nA = cp.evaluate_hda_space_charge(50e-9, E_pass_eV=100.0)
    hda_guard = cp.evaluate_hda_space_charge(0.25e-9, E_pass_eV=100.0)
    assert hda_50nA["dr_sc_laminar_um"] > 5000.0 and not hda_50nA["passes_hda_space_charge_guard"]
    assert hda_guard["passes_hda_space_charge_guard"] is True

    # OBS-076 & OBS-150: PSU ripple enters spot budget & 1D RMS 0.5 factor applied
    sp_tight = cp.evaluate_spot_budget(5.0, 2.66, 3.0, 6.4, dE_fwhm_eV=0.453, Ti_eV=0.5, tau_filter=0.075, tau_shot_ms=15.0, psu_stability_ppm=46.8)
    sp_legacy = cp.evaluate_spot_budget(5.0, 2.66, 3.0, 6.4, dE_fwhm_eV=0.453, Ti_eV=0.5, tau_filter=0.075, tau_shot_ms=15.0, dv_psu_rms_V=0.50)
    assert math.isclose(sp_tight["sigma_geom_nm"], 0.5 * sp_tight["r_geom_tophat_nm"], rel_tol=1e-12)
    assert math.isclose(sp_tight["sigma_c_nm"], 0.5 * sp_tight["sigma_c_edge_nm"], rel_tol=1e-12)
    assert sp_legacy["sigma_psu_nm"] > 0.7 and sp_tight["sigma_psu_nm"] < 0.45
    assert sp_tight["sigma_straggle_nm"] > 4.2  # OBS-039 true ZBL/iradina straggle

    # OBS-098 & OBS-071: synchronized Exp127 Lindhard + dead-layer IBIC (no Exp72 heuristic)
    ib5 = cp.ibic_efficiency(5.0, 0.5)
    ib2 = cp.ibic_efficiency(2.0, 0.5)
    assert ib5["model"] == "Exp127_Lindhard_COLD100K_RamoShockley"
    assert ib5["eta"] >= 0.99
    assert ib2["eta"] < 0.50  # 2 keV IBIC collapse honestly exposed


def test_portable_yield_engine_exact_exp57_audit_slice():
    # Live deterministic check of first 10 Exp57 seeds (fast <0.5s) to verify zero Windows path dependency
    c = ay.run_cell(
        "live_audit_10", 5.0, 5.0, 5.0, 1024, 10,
        [ay.seed57(5.0, 1024, r) for r in range(10)],
        surface_cut=False, Rp_nm=6.4582, donor_straggle=False, workers=1,
    )
    assert 0 <= c["successes"] <= 10
    assert c["lost_surface_frac_mean"] == 0.0


def test_exp124_artifacts_verdicts_and_anisotropic_ordering():
    pred_file = RES_DIR / "predictions_exp124.json"
    res_file = RES_DIR / "exp124.json"
    sum_file = RES_DIR / "summary_exp124.md"
    assert pred_file.exists() and res_file.exists() and sum_file.exists()

    d = json.loads(res_file.read_text(encoding="utf-8"))
    assert d["no_lab_measurement"] is True
    v = d["verdicts"]
    assert v["CD1_audit_and_liouville_deficit"] is True
    assert v["CD2_laplace_raytrace_verification"] is True
    # OBS-039 honest ceiling: 5 keV true ZBL/iradina straggle (4.385 nm) breaches 3.80 nm total ceiling!
    assert v["CD4_liouville_closed_5keV_window"] is False
    assert v["CD4a_optical_spot_breakdown_ibic_pass"] is True
    assert v["CD5_boersch_coulomb_suppression"] is True
    assert v["CD6_yield_engine_exact_audit"] is True

    # OBS-132: Per-energy Laplace Cc/Cs variation and 10 keV E_gap > 12 MV/m breakdown exposed
    es = d["energy_sweep"]
    assert es["E3"]["lens_trace_Vin10kV"]["Cc_scherzer_mm"] < es["E5"]["lens_trace_Vin10kV"]["Cc_scherzer_mm"] < es["E10"]["lens_trace_Vin10kV"]["Cc_scherzer_mm"]
    assert es["E10"]["lens_trace_Vin10kV"]["E_gap_nom_MV_m"] > 15.0
    assert es["E10"]["lens_trace_Vin10kV"]["breakdown_safe_12MVm"] is False
    # OBS-102: Pilot 2 blanker limitation metadata present
    assert d["pilot2_blanker_limitation_note"]["obstacle_id"] == "OBS-102"

    # Exact Exp57 & Exp105 bit-for-bit reproducibility + true iradina 5 keV yield cell
    yc = d["anisotropic_yield_cells"]
    assert yc["AUDIT_EXP57_S5_N1024"]["successes"] == 49
    assert yc["AUDIT_EXP105_ISO3p8_N1024"]["successes"] == 277
    assert "ANISO_IRADINA_5KEV_DONOR_N1024" in yc
    assert yc["ANISO_IRADINA_5KEV_DONOR_N1024"]["yield_frac"] < yc["ANISO_P91_BCA_DONOR_N1024"]["yield_frac"]

    # Physical anisotropic yield ordering & spectral-crowding surface-truncation effect
    y_bca_pure = yc["ANISO_BCA_PURE_N1024"]["yield_frac"]
    y_p91_bca = yc["ANISO_P91_BCA_N1024"]["yield_frac"]
    y_iso = yc["AUDIT_EXP105_ISO3p8_N1024"]["yield_frac"]
    y_p91_holmes_nosurf = yc["ANISO_P91_HOLMES_NOSURF_N1024"]["yield_frac"]
    y_p91_holmes_surf = yc["ANISO_P91_HOLMES_N1024"]["yield_frac"]
    y_p91_donor = yc["ANISO_P91_BCA_DONOR_N1024"]["yield_frac"]
    assert y_bca_pure > y_p91_bca > y_iso > y_p91_holmes_nosurf
    assert y_p91_holmes_surf > y_p91_holmes_nosurf  # surface cut relieves spectral crowding at N=1024
    assert y_p91_bca - y_p91_donor >= 0.15


def test_cad_column_stack_continuity_and_figures():
    d = json.loads((RES_DIR / "exp124.json").read_text(encoding="utf-8"))
    cad = d["cad_column_dimensions_mm"]
    # F4: Unified CAD v3.0 global Z frame (Z_WAFER=500.0 mm, R_in=182.0 mm)
    assert math.isclose(cad["wafer_top_z_cad_mm"], 500.0, abs_tol=1e-6)
    assert math.isclose(cad["column_top_z_cad_mm"], 1062.66, abs_tol=1e-2)
    assert math.isclose(cad["total_column_height_mm"], 562.66, abs_tol=1e-2)
    assert math.isclose(cad["uhv_chamber_inner_r_mm"], 182.0, abs_tol=1e-6)
    assert cad["fits_golden_uhv_chamber"] is True
    assert cad["max_outer_diameter_mm"] <= 120.0

    # F1: Option-A co-pitched Arch-B 32x32=1,024 @ 0.50 mm (16x16 mm, diag 22.63 mm) & Ø28.0 mm bore
    assert cad["active_beamlet_count"] == 1024
    assert math.isclose(cad["active_pitch_mm"], 0.50, abs_tol=1e-6)
    assert math.isclose(cad["active_array_side_mm"], 16.0, abs_tol=1e-6)
    assert math.isclose(cad["active_array_diagonal_mm"], 16.0 * math.sqrt(2.0), abs_tol=1e-3)
    assert math.isclose(cad["limiting_column_bore_mm"], 28.0, abs_tol=1e-6)
    assert cad["beam_array_diagonal_to_bore_clearance_mm"] > 2.68
    assert cad["write_rate_shots_per_day_1024_15ms"] > 2.94e9
    assert cad["write_rate_shots_per_day_1024_10ms"] > 4.42e9

    stages = cad["stages"]
    by_id = {s["id"]: s for s in stages}
    assert math.isclose(by_id["S1.6_transfer_lens"]["bore_mm"], 28.0, abs_tol=1e-6)
    assert math.isclose(by_id["S2.1_aperture_and_frame"]["bore_mm"], 28.0, abs_tol=1e-6)

    z_prev = cad["wafer_top_z_cad_mm"]
    for st in stages:
        assert math.isclose(st["z_bottom_mm"], z_prev + st["gap_below_mm"], abs_tol=1e-2)
        assert math.isclose(st["z_top_mm"], st["z_bottom_mm"] + st["height_mm"], abs_tol=1e-2)
        assert math.isclose(st["z_center_mm"], 0.5 * (st["z_bottom_mm"] + st["z_top_mm"]), abs_tol=1e-2)
        assert math.isclose(st["z_rel_bottom_mm"], st["z_bottom_mm"] - 500.0, abs_tol=1e-2)
        assert math.isclose(st["z_rel_top_mm"], st["z_top_mm"] - 500.0, abs_tol=1e-2)
        z_prev = st["z_top_mm"]
    assert math.isclose(z_prev, cad["column_top_z_cad_mm"], abs_tol=1e-2)

    for fig in ("fig_exp124_optics_envelope.png", "fig_exp124_anisotropic_yield.png"):
        p = RES_DIR / fig
        assert p.exists() and p.stat().st_size > 20_000
