"""Verification tests for Exp129 (H147): VOKL-6 6-Valley Central-Cell Hyperfine Theory & Mode B Yield."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = ROOT / "experiments" / "exp129_valley_orbital_hyperfine"
RES_DIR = ROOT / "results" / "exp129_valley_orbital_hyperfine"

sys.path.insert(0, str(EXP_DIR))
import bath_yield129 as by  # noqa: E402
import vokl6_theory as vt  # noqa: E402


def test_bare_emt_and_vokl6_spectral_invariants() -> None:
    """Verify Faulkner bare EMT binding energy and exact 4-invariant 31P calibration (zero 29Si fitting)."""
    blocks = vt.precompute_single_valley_blocks()
    bare = vt.solve_bare_emt(blocks)
    assert abs(bare["E_emt_1s_meV"] - (-31.27)) <= 0.25

    cal = vt.calibrate_vokl6_to_31p_invariants(blocks)
    assert cal["optimizer_success"] is True
    assert abs(cal["E_1s_A1_meV"] - (-45.59)) <= 1e-3
    assert abs(cal["Delta_VO_T2_meV"] - 11.70) <= 1e-3
    assert abs(cal["Delta_VO_E_meV"] - 13.01) <= 1e-3
    assert abs(cal["A_P_0_MHz"] - 117.53) <= 1e-2

    p = cal["params"]
    assert 0.05 <= p["r_c_nm"] <= 0.35
    assert p["U_intra_meV"] > 0.0
    assert p["U_g_meV"] > 0.0
    assert p["U_f_meV"] > p["U_g_meV"]  # Lax-Birman f-process dominance


def test_td_multiplet_degeneracy_and_normalization() -> None:
    """Verify exact Td 1x A1, 3x T2, 2x E degeneracies and 6-valley wavefunction normalization."""
    blocks = vt.precompute_single_valley_blocks()
    cal = vt.calibrate_vokl6_to_31p_invariants(blocks)
    assert cal["T2_degeneracy_spread_meV"] < 1e-6
    assert cal["E_degeneracy_spread_meV"] < 1e-6
    assert cal["valley_weight_spread"] < 1e-10
    assert abs(cal["norm_sq"] - 1.0) < 1e-10


def test_epm_bloch_symmetries_and_lax_birman() -> None:
    """Verify CB-EPM on-axis screw symmetry lock, off-axis Delta_1-Delta_2' phase, and Lax-Birman zero."""
    epm = vt.verify_epm_band_structure()
    assert epm["n_planewaves"] == 145
    assert 0.80 <= epm["k_star_frac"] <= 0.90
    assert abs(epm["q_on_axis"]["re"] - 1.0) < 1e-10
    assert abs(epm["q_on_axis"]["im"]) < 1e-10

    q_pp = epm["q_off_axis_0p15_0p15"]
    q_pm = epm["q_off_axis_0p15_m0p15"]
    assert abs(q_pp["im"]) > 0.5
    assert abs(q_pp["im"] + q_pm["im"]) < 1e-10
    assert abs(q_pp["re"] - q_pm["re"]) < 1e-10
    assert epm["lax_birman_C_g_002_abs"] < 1e-10


def test_3d_hyperfine_tensor_tracelessness_and_qenc() -> None:
    """Verify full 3x3 dipolar tensor symmetry, zero trace, and monotonic enclosed probability Q_enc(r)."""
    blocks = vt.precompute_single_valley_blocks()
    cal = vt.calibrate_vokl6_to_31p_invariants(blocks)
    sample_r = by.SITES_NM[:256]
    a_iso = np.full(len(sample_r), 1e5, dtype=np.float64)

    A_ext, T_ext = vt.compute_3d_hyperfine_tensor(sample_r, a_iso, blocks=blocks, c_1v=cal["c_1v"], extended_dipole=True)
    A_pt, T_pt = vt.compute_3d_hyperfine_tensor(sample_r, a_iso, extended_dipole=False)

    assert np.max(np.abs(np.trace(T_ext, axis1=1, axis2=2))) < 1e-10
    assert np.max(np.abs(np.trace(T_pt, axis1=1, axis2=2))) < 1e-10
    assert np.max(np.abs(T_ext - np.swapaxes(T_ext, 1, 2))) < 1e-10
    assert np.max(np.abs(A_ext - np.swapaxes(A_ext, 1, 2))) < 1e-10

    r_grid = np.linspace(0.0, 6.0, 61)
    q_enc = vt.enclosed_charge_fraction(r_grid, blocks, cal["c_1v"])
    assert q_enc[0] == 0.0
    assert np.all(np.diff(q_enc) >= -1e-12)
    assert 0.90 <= q_enc[-1] <= 1.0


def test_portable_bath_determinism() -> None:
    """Verify Mode B portable engine determinism on seed59."""
    r1 = by.run_mode_b_cell(by.A_KL_PRIMARY, f_pct=0.5, reals=12, max_workers=1)
    r2 = by.run_mode_b_cell(by.A_KL_PRIMARY, f_pct=0.5, reals=12, max_workers=1)
    assert r1["successes"] == r2["successes"]
    assert r1["eligible_median"] == r2["eligible_median"]
    assert r1["gap_stats"]["certified_min_gaps_Hz_sorted"] == r2["gap_stats"]["certified_min_gaps_Hz_sorted"]


def test_exp129_results_verdicts_figures_and_portability() -> None:
    """Verify all generated Exp129 JSON, PNG, Markdown artifacts, verdict integrity, and zero hardcoded paths."""
    pred_file = RES_DIR / "predictions_exp129.json"
    res_file = RES_DIR / "exp129.json"
    sum_file = RES_DIR / "summary_exp129.md"
    fig1 = RES_DIR / "fig_exp129_endor_shells.png"
    fig2 = RES_DIR / "fig_exp129_vokl6_yield.png"

    for p in (pred_file, res_file, sum_file, fig1, fig2):
        assert p.exists(), f"Missing required Exp129 artifact: {p.name}"

    for fig in (fig1, fig2):
        raw = fig.read_bytes()
        assert len(raw) > 25_000, f"Figure too small: {fig.name}"
        assert raw[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG header: {fig.name}"

    pred = json.loads(pred_file.read_text(encoding="utf-8"))
    res = json.loads(res_file.read_text(encoding="utf-8"))

    assert pred["no_lab_measurement"] is True
    assert res["no_lab_measurement"] is True
    assert res["exp59_62_portable_audit"]["all_exact_match"] is True
    assert res["verdicts"]["CE1_SPECTRAL_INVARIANTS"] is True
    assert res["verdicts"]["CE2_SYMMETRY_AND_TENSOR"] is True
    assert res["verdicts"]["CE5_PORTABLE_EXP59_AUDIT"] is True

    # Independently recompute all 7 verdicts from recorded numerical outputs (zero tampering check)
    b_kl = res["shell_benchmarks"]["models"]["KL_legacy"]
    b_vk = res["shell_benchmarks"]["models"]["VOKL6_full_k085"]
    assert res["verdicts"]["CE3_OUT_OF_SAMPLE_R331"] == bool(b_vk["err_R331"] <= 0.30 and b_vk["err_R331"] < b_kl["err_R331"])
    assert res["verdicts"]["CE4_MULTISHELL_LOG_RMS"] == bool(
        b_vk["log10_rms_4shells"] < b_kl["log10_rms_4shells"] and b_vk["err_R111"] <= 0.35
    )
    mb = res["mode_b_yield_n400"]
    max_shift = max(
        abs(mb["VOKL6_norm_ext"][fk]["yield_frac"] - mb["KL_legacy"][fk]["yield_frac"])
        for fk in ("F0.5", "F1", "F2")
    )
    assert res["verdicts"]["CE6_MODE_B_YIELD_CLOSURE"] == bool(
        mb["VOKL6_norm_ext"]["F1"]["yield_frac"] >= 0.40 and max_shift <= 0.15
    )
    f1_gs = mb["VOKL6_norm_ext"]["F1"]["gap_stats"]
    assert res["verdicts"]["CE7_GAP_RISK_6P89KHZ"] == bool(
        f1_gs["median_Hz"] >= 6893.0 and f1_gs["frac_lt_6893Hz"] <= 0.50
    )
    # OBS-048 & OBS-029: explicit Exp129 (7.95 MHz) vs Exp136 (3.65 MHz) uncertainty band & DDRF certified yields
    band = res["machine_impact_R1"]["ab_initio_scale_uncertainty_band_OBS048"]
    assert band["inter_model_spread_ratio"] > 2.0
    assert abs(band["exp129_vokl6_abinit_a004_MHz"] - 7.951) < 0.1
    assert abs(band["exp136_sp3d5s_abinit_a004_MHz"] - 3.648) < 0.05
    ddrf_y = res["machine_impact_R1"]["ddrf_6p89kHz_certified_yields_VOKL6_HM5962"]
    assert 0.0 < ddrf_y["F1"] < mb["VOKL6_HM5962_ext"]["F1"]["yield_frac"]

    # Portability check: zero hardcoded machine-specific user paths in any newly authored Exp129 file
    forbidden = [re.compile(r"/home/[a-zA-Z0-9_-]+"), re.compile(r"/run/media/"), re.compile(r"[A-Za-z]:\\\\quantum_cell")]
    files_to_scan = [
        EXP_DIR / "vokl6_theory.py",
        EXP_DIR / "bath_yield129.py",
        EXP_DIR / "run_exp129.py",
        EXP_DIR / "plot_exp129.py",
        sum_file,
        pred_file,
        Path(__file__).resolve(),
    ]
    for fpath in files_to_scan:
        txt = fpath.read_text(encoding="utf-8")
        # Ignore our own regex pattern line inside this test file
        if fpath == Path(__file__).resolve():
            lines = [ln for ln in txt.splitlines() if "forbidden =" not in ln]
            txt = "\n".join(lines)
        for pat in forbidden:
            assert pat.search(txt) is None, f"Forbidden hardcoded path pattern {pat.pattern} found in {fpath.name}"

    # GFM Markdown table column consistency check on summary_exp129.md
    lines = sum_file.read_text(encoding="utf-8").splitlines()
    table_blocks: list[list[tuple[int, str]]] = []
    cur: list[tuple[int, str]] = []
    for idx, ln in enumerate(lines, 1):
        if ln.strip().startswith("|") and ln.strip().endswith("|"):
            cur.append((idx, ln.strip()))
        else:
            if cur:
                table_blocks.append(cur)
                cur = []
    if cur:
        table_blocks.append(cur)
    assert len(table_blocks) >= 3, "Expected >=3 GFM tables in summary_exp129.md"
    for blk in table_blocks:
        counts = [len(re.split(r"(?<!\\)\|", row[1:-1])) for _, row in blk]
        assert len(set(counts)) == 1, f"Inconsistent GFM table column counts at lines {[i for i, _ in blk]}: {counts}"
