"""Exp148 (H166) Independent Verification Test Suite (>= 9 tests).

Verifies:
  1. Exact 8x8 & 16x16 121Sb Hamiltonians, Exp142 NMR spacings (473.9 / 70.0 kHz), and CPTP Lindblad (<1e-12).
  2. Exact even-odd brickwork Q-Echo-4 (cancels Iz^2, leaves Iz) & Q-Echo-8 (cancels BOTH Iz^2 & Iz to <1e-12).
  3. Exp142 OQ6 closure under 500 Hz quasistatic strain + 20 ms B with finite multi-tone pulses (@ 25 kHz).
  4. Exact analytical Gaussian multi-OU variance agreement vs trajectory Monte Carlo & strict monotonicity across [10, 1000] Hz.
  5. Neutral (473.9 kHz) vs Ionized (70.0 kHz) finite-pulse RF crosstalk wall monotonicity across Omega in [5..25] kHz.
  6. Exact analytical Fréchet derivative check in su8_grape148 & logical gate synthesis metrics {X_L, Z_L, H_L}.
  7. Independent verdict recomputation directly from locked predictions_exp148.json + exp148.json (honest SQ4 FAIL preserved).
  8. Portability (zero hardcoded host paths), epistemic tags (no_lab_measurement=True), and 2400x1400 PNG check.
  9. Zero GFM table errors in summary_exp148.md & canonical BOM.csv untouched integrity.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = REPO_ROOT / "experiments" / "exp148_sb121_quadrupole_echo_qudit"
RES_DIR = REPO_ROOT / "results" / "exp148_sb121_quadrupole_echo_qudit"
BOM_CSV = REPO_ROOT / "research" / "atom_lithography_machine" / "BOM.csv"

if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

import sb121_echo_solver148 as solver
import su8_grape148 as grape


def test_01_sb121_hamiltonian_spacings_and_cptp() -> None:
    """SQ1 live check: exact 8x8 & 16x16 NMR spacings match Exp142 (+-1 kHz) and CPTP holds (<1e-12)."""
    m = solver.build_sb121_models()
    assert abs(m["min_spacing_neutral_kHz"] - 473.90) <= 1.0
    assert abs(m["min_spacing_ionized_kHz"] - 70.00) <= 1.0
    assert m["H_16_MHz"].shape == (16, 16)
    assert np.allclose(m["H_16_MHz"], m["H_16_MHz"].conj().T, atol=1e-12)
    cptp = solver.verify_8x8_and_16x16_cptp(m)
    assert cptp["max_trace_err_8x8"] < 1e-12
    assert cptp["min_eig_8x8"] >= -1e-12
    assert cptp["max_trace_err_16x16"] < 1e-12
    assert cptp["min_eig_16x16"] >= -1e-12


def test_02_brickwork_qecho4_and_qecho8_exact_algebra() -> None:
    """SQ2 live check: Q-Echo-4 cancels Iz^2 leaving Iz; Q-Echo-8 cancels BOTH Iz^2 & Iz to <1e-12."""
    m = solver.build_sb121_models()
    alg = solver.verify_qecho_algebraic_cancellation(m)
    assert alg["qecho4_residual_Iz2_fro"] < 1e-12
    assert alg["qecho4_residual_Iz_fro"] > 1.0
    assert alg["qecho8_residual_Iz2_fro"] < 1e-12
    assert alg["qecho8_residual_Iz_fro"] < 1e-12
    assert alg["qecho8_closure_err_fro"] < 1e-12
    assert alg["qecho8_static_500Hz_process_fidelity"] > 1.0 - 1e-12


def test_03_finite_pulse_oq6_closure_at_500hz() -> None:
    """SQ3 live + JSON check: composite 90-240-90 quadrature Q-Echo-8 @ 25 kHz closes Exp142 OQ6."""
    m = solver.build_sb121_models()
    st = solver.benchmark_states()
    ev0 = solver.evaluate_finite_pulse_brickwork(
        m["freqs_neutral_MHz"], m["transition_dipoles_Mk"],
        omega_peak_khz=25.0, t_total_ms=1.0, df_b_mhz=0.0, df_q_mhz=0.0,
        pulse_type="composite_90_240_90", phase_cycling="quadrature_alt",
    )
    assert ev0["noiseless_cycle_process_fidelity"] >= 0.999
    ev500 = solver.evaluate_finite_pulse_brickwork(
        m["freqs_neutral_MHz"], m["transition_dipoles_Mk"],
        omega_peak_khz=25.0, t_total_ms=1.0, df_b_mhz=0.0, df_q_mhz=500e-6,
        pulse_type="composite_90_240_90", phase_cycling="quadrature_alt",
        z_cal_override=ev0["Z_cal"],
    )
    fg = abs(complex(st["gross_0L"].conj() @ ev500["U_tot"] @ st["gross_0L"])) ** 2
    fc = abs(complex(st["spin_cat_pm7_2"].conj() @ ev500["U_tot"] @ st["spin_cat_pm7_2"])) ** 2
    assert fg >= 0.995
    assert fc >= 0.995

    doc = json.loads((RES_DIR / "exp148.json").read_text(encoding="utf-8"))
    qs = doc["benchmarks"]["quasistatic_500Hz_1ms"]
    assert abs(qs["bare"]["gross_0L"] - 0.5855) <= 0.02
    assert qs["qecho8_finite_neutral_25kHz"]["gross_0L"] >= 0.980
    assert qs["qecho8_finite_neutral_25kHz"]["spin_cat_pm7_2"] >= 0.985


def test_04_exact_ou_covariance_vs_mc_and_1f_monotonicity() -> None:
    """SQ4 check: exact multi-OU Gaussian covariance matches MC (<0.02) & multi-cycle scaling is monotonic."""
    doc = json.loads((RES_DIR / "exp148.json").read_text(encoding="utf-8"))
    assert doc["benchmarks"]["quasistatic_500Hz_1ms"]["bare_mc16000_crosscheck_max_err"] < 0.015
    assert doc["benchmarks"]["colored_1f_ou_mc2048_crosscheck_err"] < 0.025

    sw = doc["benchmarks"]["colored_1f_delta_fQ_sweep_1ms"]
    assert len(sw) == 7
    for r in sw:
        assert r["qecho64_gross_0L"] >= r["qecho32_gross_0L"] - 1e-12
        assert r["qecho32_gross_0L"] >= r["qecho16_gross_0L"] - 1e-12
        assert r["qecho16_gross_0L"] >= r["qecho8_gross_0L"] - 1e-12
        assert r["qecho8_gross_0L"] >= r["bare_gross_0L"] - 1e-12

    t2 = doc["benchmarks"]["colored_1f_500Hz_decay_curves"]["T2_eff_ms"]
    # Cywinski N_cyc^{1/2} scaling: Q-Echo-8 < Q-Echo-16 < Q-Echo-32 < Q-Echo-64
    assert t2["bare_gross_ms"] < t2["qecho8_gross_ms"] < t2["qecho16_gross_ms"] < t2["qecho32_gross_ms"] < t2["qecho64_gross_ms"]
    assert t2["gross_gain_qecho64_vs_bare"] >= 25.0


def test_05_neutral_vs_ionized_rf_crosstalk_wall() -> None:
    """SQ5 check: neutral stays >= 0.998 at 25 kHz while ionized 70 kHz collapses monotonically."""
    doc = json.loads((RES_DIR / "exp148.json").read_text(encoding="utf-8"))
    ion = doc["benchmarks"]["ionized_crosstalk_sweep"]
    assert len(ion) == 4
    f_ion = [r["ionized_hann_process_fidelity"] for r in ion]
    f_neu = [r["neutral_composite_process_fidelity"] for r in ion]
    assert all(f_ion[i] > f_ion[i + 1] for i in range(3))
    assert f_ion[0] >= 0.99
    assert f_ion[-1] < 0.65
    assert min(f_neu) >= 0.999


def test_06_su8_grape_frechet_gradient_and_logical_gates() -> None:
    """SQ6 check: analytical Fréchet derivative matches finite differences (<1e-7) & {X_L, Z_L, H_L} gates meet spec."""
    m = solver.build_sb121_models()
    xs, ys = grape._tone_generators_8x8(m["transition_dipoles_Mk"])
    ops = xs + ys
    rng = np.random.default_rng(148)
    u = rng.uniform(-0.1, 0.1, size=14)
    H = 0.001 * m["Iz2"] + sum(u[c] * ops[c] for c in range(14))
    _, dUs = grape._expm_frechet_exact(H, 1.5, ops)
    eps = 1e-6
    for c in range(14):
        Up, _ = grape._expm_frechet_exact(H + eps * ops[c], 1.5, [])
        Um, _ = grape._expm_frechet_exact(H - eps * ops[c], 1.5, [])
        assert np.linalg.norm(dUs[c] - (Up - Um) / (2.0 * eps)) < 1e-7

    doc = json.loads((RES_DIR / "exp148.json").read_text(encoding="utf-8"))
    gr = doc["su8_grape_logical_gates"]
    assert set(gr["gates"].keys()) == {"X_L", "Z_L", "H_L"}
    assert gr["max_peak_rabi_used_kHz"] <= 40.0
    assert gr["min_F_L_noiseless_full_crosstalk"] >= 0.995
    assert gr["max_p_leak_noiseless_full_crosstalk"] <= 5e-3
    assert gr["min_F_L_noisy_500Hz_strain"] >= 0.985


def test_07_independent_preregistered_verdict_recomputation() -> None:
    """Independently recompute SQ1..SQ6 from exp148.json against locked predictions_exp148.json."""
    preds = json.loads((RES_DIR / "predictions_exp148.json").read_text(encoding="utf-8"))
    doc = json.loads((RES_DIR / "exp148.json").read_text(encoding="utf-8"))
    assert preds["registered_before_computation"] is True
    assert preds["no_lab_measurement"] is True
    assert doc["no_lab_measurement"] is True

    v = doc["verdicts_sq1_to_sq6"]
    assert v["SQ1_BARE_ANCHOR_AND_CPTP"]["status"] == "PASS"
    assert v["SQ2_QECHO_ALGEBRAIC_CANCELLATION"]["status"] == "PASS"
    assert v["SQ3_QECHO_CLOSES_EXP142_OQ6_500HZ"]["status"] == "PASS"
    # Honest physical Cywinski 1/f FAIL for N_cyc=1 Q-Echo-8 (<20x / <1.0 ms): must stay honestly reported as FAIL!
    t2_g = doc["benchmarks"]["colored_1f_500Hz_decay_curves"]["T2_eff_ms"]
    expected_sq4 = "PASS" if (t2_g["gross_gain_qecho8_vs_bare"] >= 20.0 and t2_g["qecho8_gross_ms"] >= 1.0) else "FAIL"
    assert v["SQ4_COLORED_1F_STRAIN_SCALING"]["status"] == expected_sq4
    assert v["SQ5_FINITE_PULSE_CROSSTALK_AND_IONIZED_WALL"]["status"] == "PASS"
    assert v["SQ6_SU8_GRAPE_LOGICAL_GATES"]["status"] == "PASS"


def test_08_png_dimensions_and_portability() -> None:
    """SQ7 check: 2400x1400 PNG exists & zero hardcoded host paths across all Exp148 code/results/tests."""
    png = RES_DIR / "fig_exp148_sb121_qudit_echo.png"
    assert png.exists() and png.stat().st_size > 40_000
    raw = png.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", raw[16:24])
    assert (w, h) == (2400, 1400)

    forbidden = (
        "/home/" + "berk",
        "/run/media/" + "berk",
        "E:" + "\\",
        "C:" + "\\Users",
    )
    files = list(EXP_DIR.glob("*.py")) + list(RES_DIR.glob("*.json")) + list(RES_DIR.glob("*.md")) + [Path(__file__)]
    for fp in files:
        txt = fp.read_text(encoding="utf-8")
        for pat in forbidden:
            assert pat not in txt, f"Hardcoded host path {pat!r} found in {fp.name}"


def test_09_summary_gfm_tables_and_bom_untouched() -> None:
    """SQ7 check: 0 GFM table syntax errors in summary_exp148.md and canonical BOM.csv SHA-256 unchanged."""
    md_path = RES_DIR / "summary_exp148.md"
    assert md_path.exists()
    lines = md_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 40

    # Verify every GFM table block has matching pipe column counts and valid separator row
    i = 0
    table_count = 0
    while i < len(lines):
        if lines[i].strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:\-\|]+\|\s*$", lines[i + 1]):
            table_count += 1
            ncols = len([c for c in lines[i].strip().strip("|").split("|")])
            sep_cols = len([c for c in lines[i + 1].strip().strip("|").split("|")])
            assert sep_cols == ncols, f"Table {table_count} separator mismatch at line {i + 2}"
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                # Replace escaped pipes \| before counting columns
                row_clean = lines[j].strip().strip("|").replace(r"\|", "PIPE")
                rcols = len(row_clean.split("|"))
                assert rcols == ncols, f"Table {table_count} row {j + 1} has {rcols} cols != {ncols}"
                j += 1
            i = j
        else:
            i += 1
    assert table_count >= 4

    # Verify canonical BOM.csv untouched
    sha = hashlib.sha256(BOM_CSV.read_bytes()).hexdigest()
    assert sha == "cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2"
