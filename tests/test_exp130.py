"""Verification test suite for Exp130 (H148 / Risk R6: Millisecond Flash/Laser Annealing)."""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = REPO_ROOT / "experiments" / "exp130_flash_anneal_diffusion"
RES_DIR = REPO_ROOT / "results" / "exp130_flash_anneal_diffusion"

if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

from heat_ted_solver import (  # noqa: E402
    KB_J,
    MOLAR_MASS_SI,
    NA_AVOGADRO,
    T_MELT_SI,
    build_synthetic_thermal_waveform,
    compute_cryo_cooldown_to_20mK,
    cp_si,
    cp_si_debye_cryo,
    find_fluence_for_target_T,
    k_si,
    solve_ted_kinetics_1d,
    solve_thermal_1d,
)


def test_silicon_thermophysical_and_debye_limits() -> None:
    # Crystalline Si k(T) monotonically decreases from 300 K to T_melt; c_p(T) increases
    T_pts = np.array([300.0, 600.0, 1000.0, 1400.0, 1687.0])
    ks = k_si(T_pts)
    cps = cp_si(T_pts)
    assert np.all(np.diff(ks) < 0.0)
    assert np.all(np.diff(cps) > 0.0)
    assert 140.0 < ks[0] < 155.0
    assert 20.0 < ks[-1] < 25.0

    # Exact low-T Debye T^3 law: c_v(2 K) / c_v(1 K) == 8.0
    c_low = cp_si_debye_cryo(np.array([1.0, 2.0]))
    assert math.isclose(c_low[1] / c_low[0], 8.0, rel_tol=1e-6)

    # High-T Dulong-Petit limit: c_v(10000 K) -> 3 * R / M_Si
    R_spec = (NA_AVOGADRO * KB_J) / MOLAR_MASS_SI
    c_hi = cp_si_debye_cryo(np.array([10000.0]))[0]
    assert math.isclose(c_hi, 3.0 * R_spec, rel_tol=1e-3)


def test_thermal_pde_energy_conservation_and_wavelength_ordering() -> None:
    r808 = find_fluence_for_target_T(1.0e-3, 1440.0, wavelength_nm=808.0)
    r532 = find_fluence_for_target_T(1.0e-3, 1440.0, wavelength_nm=532.0)
    r308 = find_fluence_for_target_T(1.0e-3, 1440.0, wavelength_nm=308.0)

    for res in (r808, r532, r308):
        assert abs(res["T_peak_K"] - 1440.0) < 2.0
        assert res["energy_balance_rel_err"] < 5e-4
        assert res["T_back_max_K"] < 700.0
        assert res["t_quench_to_900K_ms"] < 1.0

    # Reflectivity ordering R_808 (0.33) < R_532 (0.37) < R_308 (0.60) -> fluence ordering
    assert r808["fluence_J_per_cm2"] < r532["fluence_J_per_cm2"] < r308["fluence_J_per_cm2"]
    assert 10.0 <= r808["fluence_J_per_cm2"] <= 45.0


def test_ted_mass_conservation_and_exp108_anchor() -> None:
    tw6, Tw6 = build_synthetic_thermal_waveform(600.0 + 273.15, 600.0)
    r600 = solve_ted_kinetics_1d(tw6, Tw6, C_cl_peak_cm3=1.5e20, r_casc_nm=None)
    tw8, Tw8 = build_synthetic_thermal_waveform(800.0 + 273.15, 600.0)
    r800 = solve_ted_kinetics_1d(tw8, Tw8, C_cl_peak_cm3=1.5e20, r_casc_nm=None)

    assert r600["mass_conservation_err"] < 1e-12
    assert r800["mass_conservation_err"] < 1e-12
    # EA1 literature anchor (doi:10.1063/1.331355)
    assert r600["f_surface_pileup"] >= 0.15
    assert r600["f_vacuum_escape"] < 0.05
    assert r800["f_vacuum_escape"] >= 0.30
    # Negative TED activation energy: 600 C spreads P further than 800 C
    assert r600["sigma_anneal_nm"] > r800["sigma_anneal_nm"]


def test_cryo_cooldown_monotonic_and_within_budget() -> None:
    c_tile = compute_cryo_cooldown_to_20mK(41.15, 0.16)
    c_field = compute_cryo_cooldown_to_20mK(41.15, 2.56)
    c_wafer = compute_cryo_cooldown_to_20mK(41.15, math.pi * 2.5**2)

    assert c_tile["t_cool_total_min"] < c_field["t_cool_total_min"] < c_wafer["t_cool_total_min"]
    assert c_field["t_cool_total_min"] <= 15.0
    assert c_wafer["t_cool_total_min"] <= 15.0


def test_exp130_json_verdicts_and_hardware_specs() -> None:
    preds = json.loads((RES_DIR / "predictions_exp130.json").read_text(encoding="utf-8"))
    exp = json.loads((RES_DIR / "exp130.json").read_text(encoding="utf-8"))

    assert preds["hypothesis_id"] == "H148"
    assert preds["no_lab_measurement"] is True
    assert exp["hypothesis_id"] == "H148"
    assert exp["verdict"] == "PASS"
    assert exp["no_lab_measurement"] is True

    for ea in ("EA1", "EA2", "EA3", "EA4", "EA5", "EA6"):
        assert exp["evaluations"][ea]["pass"] is True, f"{ea} failed"

    # Convergence checks
    assert exp["thermal_pde_convergence"]["T_peak_rel_diff_120_vs_160"] < 0.01
    assert exp["thermal_pde_convergence"]["max_energy_balance_rel_err"] < 0.005
    assert exp["ted_pde_convergence"]["sigma_anneal_rel_diff_150_vs_200"] < 0.01

    # Optimal 808 nm 1.0 ms operating point
    opt = exp["wavelength_and_pulse_benchmarks"]["808nm_diode_1.0ms_1440K"]
    assert opt["T_peak_K"] < 0.92 * T_MELT_SI
    assert opt["f_act_bulk"] >= 0.95
    assert opt["sigma_anneal_nm"] <= 0.50
    assert opt["f_total_surface_loss"] < 0.02
    assert opt["sigma_iso_nm"] <= 0.50
    assert opt["exp124_sigma_tot_nm"] <= 3.68

    # S5.5 sapphire viewport & LIDT margin
    s55 = exp["s55_optical_hardware_spec"]
    assert s55["cad_v3_anchor"]["optical_beam_diam_at_window_mm"] < s55["cad_v3_anchor"]["duct_clear_aperture_mm"]
    assert s55["sapphire_window_optics"]["transmission_uncoated"] >= 0.85
    assert s55["sapphire_window_optics"]["transmission_AR_808nm"] >= 0.97
    assert s55["delivery_modes"]["mode1_single_shot_16x16mm"]["lidt_safety_margin_vs_100J_floor_AR"] >= 3.0
    assert s55["delivery_modes"]["mode3_collimated_1to1_0.5ms"]["lidt_safety_margin_vs_100J_floor_AR"] >= 3.0


def test_png_artifacts_and_summary_exist_and_valid() -> None:
    for fname in ("fig_exp130_anneal_window.png", "fig_exp130_profiles_ted.png"):
        p = RES_DIR / fname
        assert p.exists(), f"Missing {p}"
        data = p.read_bytes()
        assert len(data) > 50_000
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        w, h = struct.unpack(">II", data[16:24])
        assert (w, h) == (1800, 1080)

    summary = (RES_DIR / "summary_exp130.md").read_text(encoding="utf-8")
    assert "no_lab_measurement = true" in summary
    assert "EA1" in summary and "EA6" in summary
    assert "S5.5" in summary


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
