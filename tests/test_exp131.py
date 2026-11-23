"""Verification test suite for Exp131: M4 Scalable Architecture Theory (H149).

Run with:
  pytest -p no:cacheprovider -v tests/test_exp131.py

Uses pure stdlib + numpy/scipy (no PIL dependency, portable relative paths).
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

from experiments.exp131_scalable_m4_architecture.flipflop_cell131 import (
    build_flipflop_h4,
    evaluate_flipflop_cell,
    optimize_cell_dc_bias,
)
from experiments.exp131_scalable_m4_architecture.lindblad_bus131 import (
    simulate_dispersive_cz_pair,
    simulate_resonant_bell_batch,
)
from experiments.exp131_scalable_m4_architecture.percolation131 import (
    build_heavy_hex_graph,
    build_square_graph,
    compute_cad_m4_bus_geometry,
)

EXP_DIR = REPO_ROOT / "experiments" / "exp131_scalable_m4_architecture"
RES_DIR = REPO_ROOT / "results" / "exp131_scalable_m4_architecture"
EXP_JSON = RES_DIR / "exp131.json"
PRED_JSON = RES_DIR / "predictions_exp131.json"
SUMMARY_MD = RES_DIR / "summary_exp131.md"
FIG1_PNG = RES_DIR / "fig_exp131_m4_bus_fidelity.png"
FIG2_PNG = RES_DIR / "fig_exp131_2d_percolation.png"


def test_flipflop_4x4_hermiticity_and_sweetspot_gain() -> None:
    """Verify exact 4x4 flip-flop Hermiticity, shallow-donor rejection, & DC sweet-spot rescue."""
    h4 = build_flipflop_h4(eps_ghz=6.2, t_c_ghz=3.9, omega_ff_ghz=5.0)
    assert h4.shape == (4, 4)
    assert np.allclose(h4, h4.T, atol=1e-14)

    # Shallow donor (< 8.5 nm) cannot form distinct double-well tunnel barrier
    assert evaluate_flipflop_cell(z_nm=6.0, r_xy_nm=0.0, eps_ghz=0.0) is None
    assert optimize_cell_dc_bias(z_nm=6.0, r_xy_nm=0.0) is None

    # At z=14.5 nm, fixed eps=0 fails (charge gap t_c=3.93 GHz < 5 GHz), while DC tuning rescues C >> 100
    assert evaluate_flipflop_cell(z_nm=14.5, r_xy_nm=0.0, eps_ghz=0.0) is None
    opt = optimize_cell_dc_bias(z_nm=14.5, r_xy_nm=0.0, z_r_ohm=3000.0, q_l=2e5, s_eps_uev=1.0)
    assert opt is not None
    assert opt.valid
    assert opt.p_donor > 0.50
    assert opt.cooperativity > 1000.0
    assert opt.g_eff_mhz > 0.5


def test_lindblad_12x12_cptp_and_impedance_wall() -> None:
    """Live 12x12 Lindblad CPTP audit and 3 kOhm vs 50 Ohm impedance wall check."""
    pair_3k = [(1.8, 1.1, 0.05, 0.03, 18.0, 11.0)]
    scale_50 = math.sqrt(50.0 / 3000.0)
    pair_50 = [(1.8 * scale_50, 1.1 * scale_50, 0.05, 0.03, 18.0, 11.0)]

    r3k = simulate_resonant_bell_batch(pair_3k, kappa_khz=25.0)
    r50 = simulate_resonant_bell_batch(pair_50, kappa_khz=25.0)

    assert r3k["max_trace_err"] < 1e-10
    assert r3k["max_herm_err"] < 1e-10
    assert r3k["min_eigval"] >= -1e-10
    assert r50["max_trace_err"] < 1e-10
    assert r3k["mean_F_bell"] > 0.96
    assert r50["mean_F_bell"] < 0.88
    assert r3k["mean_F_bell"] - r50["mean_F_bell"] > 0.10


def test_dispersive_cz_noiseless_unitary_accuracy() -> None:
    """Verify smooth C^2-quintic adiabatic dispersive CZ gate reaches >99% noiseless F_avg."""
    res = simulate_dispersive_cz_pair(
        g1_mhz=2.0, g2_mhz=1.3,
        g1_rel_khz=0.0, g2_rel_khz=0.0,
        g1_phi_khz=0.0, g2_phi_khz=0.0,
        kappa_khz=0.0, eta=4.0, n_ramp=14,
    )
    assert res["F_avg_cz"] >= 0.99
    assert abs(res["ent_phase_over_pi"] - 1.0) < 0.02
    assert res["max_trace_err"] < 1e-10
    assert res["min_eigval"] >= -1e-10


def test_percolation_graphs_and_cad_geometry_physics() -> None:
    """Verify exact Square & Heavy-Hex graph topology and CAD M4 electromagnetic formulas."""
    sq = build_square_graph(11)
    assert sq["n_nodes"] == 121
    assert abs(sq["bulk_degree"] - 4.0) < 1e-9

    hh = build_heavy_hex_graph(4, 5, 7)
    degs = [len(nb) for nb in hh["adj"]]
    assert hh["n_nodes"] > 100
    assert min(degs) == 2 and max(degs) == 3
    assert 2.1 < hh["mean_degree"] < 2.4

    cad = compute_cad_m4_bus_geometry(delta_z_cap_opt_nm=8.0)
    # Verify exact transmission-line identities: Z_r = sqrt(L_l/C_l), L_res = v_ph / (2 f_r)
    l_per_m = cad["L_l_nH_per_um"] * 1e-3
    c_per_m = cad["C_l_pF_per_m"] * 1e-12
    assert abs(math.sqrt(l_per_m / c_per_m) - cad["Z_r_ohm"]) < 1e-6
    v_ph = 1.0 / math.sqrt(l_per_m * c_per_m)
    assert abs(v_ph / (2.0 * cad["f_r_ghz"] * 1e9) * 1e3 - cad["L_res_mm"]) < 1e-9
    assert 0.2 <= cad["L_res_mm"] <= 2.0
    assert 0.15 <= cad["B_M4_T"] <= 0.25
    assert cad["B_M4_T"] < cad["Exp109_B_limit_T"]


def test_exp131_json_schema_and_percolation_monotonicity() -> None:
    """Verify exp131.json completeness, epistemic flags, CPTP bounds, and MC vs Binomial."""
    assert PRED_JSON.exists(), "predictions_exp131.json missing"
    assert EXP_JSON.exists(), "exp131.json missing"
    data = json.loads(EXP_JSON.read_text(encoding="utf-8"))
    preds = json.loads(PRED_JSON.read_text(encoding="utf-8"))

    assert data["experiment"] == "exp131_scalable_m4_architecture"
    assert data["hypothesis_id"] == "H149"
    assert data["no_lab_measurement"] is True
    assert preds["no_lab_measurement"] is True

    # CPTP Lindblad precision
    cptp = data["part2_lindblad_bus"]["cptp_audit"]
    assert cptp["max_trace_err"] < 1e-10
    assert cptp["max_hermiticity_err"] < 1e-10
    assert cptp["min_eigenvalue"] >= -1e-10

    # All 7 predictions evaluated transparently
    ev = data["prediction_evaluation"]
    assert ev["n_total"] == 7
    assert set(ev["predictions"].keys()) == set(preds["predictions"].keys())
    for v in ev["predictions"].values():
        assert v["verdict"] in ("PASS", "FAIL")

    # Percolation monotonicity and MC vs exact binomial consistency
    p3 = data["part3_percolation_and_cad"]
    sq21 = p3["square_m4"]["square_L21"]["sweep"]
    sq11 = p3["square_m4"]["square_L11"]["sweep"]
    sq5 = p3["square_m4"]["square_L5"]["sweep"]
    hh7 = p3["heavy_hex_m4"]["heavy_hex_d7"]["sweep"]

    for sw in (sq5, sq11, sq21, hh7):
        ps = [r["P_perc"] for r in sw]
        for a, b in zip(ps, ps[1:]):
            assert b >= a - 0.02, f"Non-monotonic percolation: {ps}"

    # Verify Heavy-Hex d=7 strictly below Square L=11 at N_cand=2
    sq11_2 = next(r for r in sq11 if r["N_cand"] == 2)
    hh7_2 = next(r for r in hh7 if r["N_cand"] == 2)
    assert hh7_2["P_perc"] < sq11_2["P_perc"]

    # Verify MC vs exact analytical Binomial within 3% tolerance
    sq5_6 = next(r for r in sq5 if r["N_cand"] == 6)
    sq11_6 = next(r for r in sq11 if r["N_cand"] == 6)
    assert abs(sq5_6["Y_perfect_mc"] - sq5_6["Y_perfect_exact"]) < 0.03
    assert abs(sq11_6["Y_FT_5pct_mc"] - sq11_6["Y_FT_5pct_exact"]) < 0.03


def _assert_valid_png(path: Path, min_w: int = 1800, min_h: int = 1200, min_bytes: int = 80_000) -> None:
    assert path.exists(), f"Missing figure: {path.name}"
    raw = path.read_bytes()
    assert len(raw) >= min_bytes, f"PNG too small ({len(raw)} bytes): {path.name}"
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG magic header: {path.name}"
    assert raw[12:16] == b"IHDR", f"Missing IHDR chunk: {path.name}"
    width, height = struct.unpack(">II", raw[16:24])
    assert width >= min_w and height >= min_h, f"PNG resolution {width}x{height} below {min_w}x{min_h}"
    assert b"IDAT" in raw and b"IEND" in raw, f"Missing IDAT/IEND chunks: {path.name}"


def test_figures_valid_png_pure_stdlib() -> None:
    """Validate both Exp131 figures using pure stdlib PNG header/chunk inspection."""
    _assert_valid_png(FIG1_PNG)
    _assert_valid_png(FIG2_PNG)


def test_summary_gfm_tables_and_portability() -> None:
    """Check summary_exp131.md GFM table column consistency and zero hardcoded home paths."""
    assert SUMMARY_MD.exists(), "summary_exp131.md missing"
    lines = SUMMARY_MD.read_text(encoding="utf-8").splitlines()

    # Strict GFM table column count linter (counts unescaped pipes outside code spans)
    in_table = False
    expected_cols = 0
    for lineno, line in enumerate(lines, start=1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            # Strip escaped pipes \| and backtick code spans before counting separators
            cleaned = re.sub(r"`[^`]*`", "", s).replace("\\|", "")
            cols = cleaned.count("|") - 1
            if not in_table:
                in_table = True
                expected_cols = cols
                assert expected_cols >= 2, f"Malformed table header at line {lineno}"
            else:
                assert cols == expected_cols, (
                    f"GFM table column mismatch at line {lineno}: got {cols}, expected {expected_cols}"
                )
        else:
            in_table = False
            expected_cols = 0

    # Portability audit: zero hardcoded user paths anywhere in Exp131 code, results, or tests
    forbidden_a = "/" + "home" + "/" + "berk"
    forbidden_b = "/" + "run" + "/" + "media" + "/" + "berk"
    files_to_scan = (
        list(EXP_DIR.glob("*.py"))
        + list(RES_DIR.glob("*.json"))
        + list(RES_DIR.glob("*.md"))
        + [Path(__file__)]
    )
    for fp in files_to_scan:
        txt = fp.read_text(encoding="utf-8")
        assert forbidden_a not in txt, f"Hardcoded home path found in {fp.name}"
        assert forbidden_b not in txt, f"Hardcoded media path found in {fp.name}"
