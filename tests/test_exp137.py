"""Verification test suite for Exp137: Echoed M4 Cavity-QED Bus Gate (H155).

Run with:
  pytest -p no:cacheprovider -v tests/test_exp137.py

Pure stdlib + numpy/scipy/torch (no PIL dependency, portable relative paths).
"""

from __future__ import annotations

import json
import math
import re
import struct
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.exp137_echoed_m4_bus_gate.echo_bus_solver137 import (
    PAULI_16_NAMES,
    FlipFlopPairSpec,
    audit_exact_4x4_tosi_clock_impossibility,
    audit_mw_pi_pulse_crosstalk,
    simulate_echoed_cz_cuda,
)
from experiments.exp137_echoed_m4_bus_gate.noise_ou137 import (
    compute_cywinski_filter_suppression,
    generate_ou_1f_trajectories_ghz,
    verify_ou_psd_spectrum,
)

EXP_DIR = REPO_ROOT / "experiments" / "exp137_echoed_m4_bus_gate"
RES_DIR = REPO_ROOT / "results" / "exp137_echoed_m4_bus_gate"
EXP_JSON = RES_DIR / "exp137.json"
PRED_JSON = RES_DIR / "predictions_exp137.json"
SUMMARY_MD = RES_DIR / "summary_exp137.md"
FIG_PNG = RES_DIR / "fig_exp137_echoed_m4_bus.png"


def test_ou_1f_psd_and_cywinski_suppression() -> None:
    """Verify multi-OU 1/f^alpha PSD accuracy and analytical Cywinski filter ordering."""
    audit = verify_ou_psd_spectrum(alphas=[0.8, 1.0, 1.2])
    assert audit["worst_psd_rel_err"] < 0.10
    assert audit["worst_rms_rel_err"] < 0.05

    # Live trajectory variance check
    rng = np.random.default_rng(7)
    traj = generate_ou_1f_trajectories_ghz(256, [0.02] * 20, s0_uev=1.0, alpha=1.0, rng=rng)
    assert traj.shape == (256, 20)
    assert np.all(np.isfinite(traj))
    assert float(np.std(traj)) > 0.5

    cyw = compute_cywinski_filter_suppression()
    for k in ("alpha_0.8", "alpha_1.0", "alpha_1.2"):
        assert cyw[k]["var_xy4"] < cyw[k]["var_echo2"] < cyw[k]["var_bare"]


def test_live_12x12_noiseless_drag_unitary_and_leakage_cut() -> None:
    """Live 12x12 solver: noiseless XY4-DRAG hits >=0.999 F_avg and beats no-DRAG leakage."""
    pair = FlipFlopPairSpec(
        g1_mhz=2.2, g2_mhz=1.6,
        d1_1_ghz_per_ghz=-8e-5, d2_1_inv_ghz=2e-5,
        d1_2_ghz_per_ghz=-1e-5, d2_2_inv_ghz=-1e-5,
        dg1_mhz_per_ghz=-0.4, dg2_mhz_per_ghz=-0.5,
        gamma1_1_khz=0.05, gamma1_2_khz=0.03,
        label="test_pair",
    )
    r_drag = simulate_echoed_cz_cuda(pair, q_r=0.0, s_eps_uev=0.0, protocol="P3", n_traj=1, eps_rot=0.0, include_dg_jitter=False)
    r_nodr = simulate_echoed_cz_cuda(pair, q_r=0.0, s_eps_uev=0.0, protocol="P3_no_drag", n_traj=1, eps_rot=0.0, include_dg_jitter=False)

    assert r_drag["F_avg"] >= 0.999
    assert r_drag["p_leak"] < 1e-4
    assert r_drag["p_leak"] < r_nodr["p_leak"]
    assert abs(r_drag["ent_phase_over_pi"] - 1.0) < 0.01
    assert r_drag["cptp_audit"]["max_trace_err"] < 1e-10


def test_live_12x12_colored_1f_echo_beats_bare_and_cptp() -> None:
    """Live 12x12 colored 1/f trajectory run: P3 XY4-DRAG strictly beats P1 Bare with exact CPTP."""
    pair = FlipFlopPairSpec(
        g1_mhz=2.5, g2_mhz=1.8,
        d1_1_ghz_per_ghz=-1.0e-4, d2_1_inv_ghz=2.5e-5,
        d1_2_ghz_per_ghz=-1.0e-4, d2_2_inv_ghz=2.5e-5,
        dg1_mhz_per_ghz=-0.3, dg2_mhz_per_ghz=-0.3,
        gamma1_1_khz=0.05, gamma1_2_khz=0.03,
        label="noisy_pair",
    )
    r_p1 = simulate_echoed_cz_cuda(pair, q_r=2e5, s_eps_uev=1.0, protocol="P1", alpha=1.0, n_traj=64, include_dg_jitter=False, seed=42)
    r_p3 = simulate_echoed_cz_cuda(pair, q_r=2e5, s_eps_uev=1.0, protocol="P3", alpha=1.0, n_traj=64, include_dg_jitter=False, seed=42)

    assert r_p3["F_avg"] > r_p1["F_avg"] + 0.03
    assert r_p3["cptp_audit"]["max_trace_err"] < 1e-9
    assert r_p3["cptp_audit"]["max_herm_err"] < 1e-9
    assert r_p3["cptp_audit"]["min_eigval"] >= -1e-9
    assert abs(r_p3["pauli_sum"] - 1.0) < 1e-6
    assert abs(r_p3["F_avg"] - (4.0 * r_p3["p_I"] + 1.0) / 5.0) < 1e-5


def test_exp137_json_schema_and_cptp_bounds() -> None:
    """Verify exp137.json completeness, pre-registered EC1-EC7, and global CPTP precision."""
    assert PRED_JSON.exists(), "predictions_exp137.json missing"
    assert EXP_JSON.exists(), "exp137.json missing"
    data = json.loads(EXP_JSON.read_text(encoding="utf-8"))
    preds = json.loads(PRED_JSON.read_text(encoding="utf-8"))

    assert data["experiment"] == "exp137_echoed_m4_bus_gate"
    assert data["hypothesis_id"] == "H155"
    assert data["no_lab_measurement"] is True
    assert preds["no_lab_measurement"] is True

    cptp = data["global_cptp_audit"]
    assert cptp["max_trace_err"] < 1e-9
    assert cptp["max_herm_err"] < 1e-9
    assert cptp["min_eigval"] >= -1e-9

    ev = data["prediction_evaluation"]
    assert ev["n_total"] == 7
    assert set(ev["predictions"].keys()) == set(preds["predictions"].keys())
    for v in ev["predictions"].values():
        assert v["verdict"] in ("PASS", "FAIL")

    # OBS-042 (no synthetic clamping), OBS-101 (60ns DRAG/Gauss eliminates 97.8% rect flip), OBS-111 (12-dec OU)
    assert data["part4_exp138_pauli_channels"]["synthetic_clamping_removed"] is True
    assert data["part1_noise_and_unitary"]["ou_psd_audit"]["f_ir_hz"] <= 1e-2
    xt = audit_mw_pi_pulse_crosstalk()
    assert xt["rect_15ns_max_neighbor_flip"] > 0.90
    assert xt["drag_gauss_60ns_hyperfine_117p53MHz_flip"] < 1e-3
    clk = audit_exact_4x4_tosi_clock_impossibility()
    assert clk["simultaneous_clock_and_flat_g_possible"] is False
    assert clk["by_depth"]["z_12nm"]["has_clock_transition_d1_le_4e6"] is False
    assert clk["by_depth"]["z_14nm"]["has_clock_transition_d1_le_4e6"] is True
    assert abs(clk["by_depth"]["z_14nm"]["min_abs_d1_point"]["dg_mhz_per_ghz"]) > 0.5


def test_exp138_pauli_channels_exact_normalization() -> None:
    """Verify exported Exp138 Pauli error channels at S_eps=1.0 and 0.5 ueV/rtHz."""
    data = json.loads(EXP_JSON.read_text(encoding="utf-8"))
    p4 = data["part4_exp138_pauli_channels"]
    for key in ("best_protocol_S1p0", "best_protocol_S0p5", "best_protocol_S0p25", "P3_XY4_DRAG_S1p0"):
        ch = p4[key]
        assert set(ch["pauli_16"].keys()) == set(PAULI_16_NAMES)
        assert abs(sum(ch["pauli_16"].values()) - 1.0) < 1e-6
        grouped = ch["p_I"] + ch["p_X"] + ch["p_Y"] + ch["p_Z"] + ch["p_ZZ"]
        assert abs(grouped - 1.0) < 1e-6
        assert abs(ch["F_avg"] - (4.0 * ch["p_I"] + 1.0) / 5.0) < 1e-5
        assert ch["p_total_err"] >= 0.0 and ch["p_leak"] >= 0.0
        assert ch["t_gate_us"] > 0.0


def test_2d_phase_map_completeness_and_monotonicity() -> None:
    """Verify 5x4 (S_eps x Q_r) phase map has 20 points and degrades at high S_eps / low Q_r."""
    data = json.loads(EXP_JSON.read_text(encoding="utf-8"))
    pm = data["part3_2d_phase_map"]
    pts = pm["points"]
    assert len(pts) == 20
    lk = {(p["s_eps_uev"], p["q_r"]): p for p in pts}
    assert lk[(0.25, 5e5)]["F_Bell"] > lk[(5.0, 5e4)]["F_Bell"]
    assert lk[(0.5, 5e5)]["F_avg"] > lk[(0.5, 5e4)]["F_avg"]


def test_figure_valid_png_pure_stdlib() -> None:
    """Validate 2400x1400 PNG figure via pure stdlib header/IHDR/IDAT/IEND check."""
    assert FIG_PNG.exists(), "fig_exp137_echoed_m4_bus.png missing"
    raw = FIG_PNG.read_bytes()
    assert len(raw) >= 80_000, f"PNG too small: {len(raw)} bytes"
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert raw[12:16] == b"IHDR"
    w, h = struct.unpack(">II", raw[16:24])
    assert w == 2400 and h == 1400, f"Expected 2400x1400, got {w}x{h}"
    assert b"IDAT" in raw and b"IEND" in raw


def test_summary_gfm_tables_and_portability() -> None:
    """Verify summary_exp137.md has 0 GFM table errors and zero hardcoded user paths."""
    assert SUMMARY_MD.exists(), "summary_exp137.md missing"
    lines = SUMMARY_MD.read_text(encoding="utf-8").splitlines()
    in_table = False
    expected_cols = 0
    for lineno, line in enumerate(lines, start=1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cleaned = re.sub(r"`[^`]*`", "", s).replace("\\|", "")
            cols = cleaned.count("|") - 1
            if not in_table:
                in_table = True
                expected_cols = cols
                assert expected_cols >= 2, f"Malformed table header at line {lineno}"
            else:
                assert cols == expected_cols, f"GFM mismatch line {lineno}: {cols} != {expected_cols}"
        else:
            in_table = False
            expected_cols = 0

    forb_pats = (re.compile(r"/home/[a-zA-Z0-9_-]+"), re.compile(r"/run/media/"))
    files = list(EXP_DIR.glob("*.py")) + list(RES_DIR.glob("*.json")) + list(RES_DIR.glob("*.md")) + [Path(__file__)]
    for fp in files:
        txt = fp.read_text(encoding="utf-8")
        if fp == Path(__file__):
            txt = "\n".join(ln for ln in txt.splitlines() if "forb_pats =" not in ln)
        for pat in forb_pats:
            assert pat.search(txt) is None, f"Hardcoded path {pat.pattern} in {fp.name}"
