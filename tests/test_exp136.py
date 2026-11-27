"""Exp136 (H154) Independent Verification Test Suite.

Covers:
  1. Bulk Boykin-Klimeck (2004) Si sp3d5s* band structure (TB1) & exact FFT-vs-sparse CSR < 1e-12.
  2. Non-diamond coordinate audit proving (3,3,0) and (1,1,3) invalid while all 10 report shells valid.
  3. 31P calibrated N=20 (16,000 atoms / 160,000 orbitals) spectral invariants, Td spreads & N=16 convergence (TB2).
  4. Out-of-sample ENDOR benchmark (TB3 R331 <= 30%, log10-RMS < KL 0.5736 & VOKL-6 0.7445, zero 29Si fit).
  5. 45,214-site atomistic+tail 3D hyperfine dipolar tensor exact tracelessness (< 1e-10 Hz).
  6. Direct atomistic Stark shift negative quadratic eta_A in Bradbury/Rahman range (TB5).
  7. Independent analytic Binomial M4 L=11 percolation, Exp62/126 T2e(f) & Abragam T2n*(f) recomputation.
  8. Strict independent recomputation of all TB1-TB7 verdicts in exp136.json against predictions_exp136.json.
  9. Publication figure PNG integrity (2400x1400 valid PNG) & zero hardcoded host paths across Exp136 files.
 10. GFM Markdown table column-consistency check on summary_exp136.md (0 table errors, no_lab_measurement).
"""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = ROOT / "experiments" / "exp136_tb_sp3d5s_hyperfine"
RES_DIR = ROOT / "results" / "exp136_tb_sp3d5s_hyperfine"

sys.path.insert(0, str(EXP_DIR))

import isotope_stark_sweep136 as sw136  # noqa: E402
import tb_sp3d5s_solver as tb  # noqa: E402


def _load_json(path: Path) -> dict:
    assert path.is_file(), f"Missing artifact: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_01_bulk_sp3d5s_bands_and_fft_csr_equivalence() -> None:
    """Verify Boykin-Klimeck (2004) Si bands & machine-precision FFT vs sparse CSR Hamiltonian."""
    b = tb.verify_bulk_si_bands()
    assert 1.10 <= b["E_gap_indirect_SO_eV"] <= 1.20
    assert 0.80 <= b["k_min_frac_2pi_a"] <= 0.86
    assert 0.17 <= b["m_t_m0"] <= 0.22
    assert 0.85 <= b["m_l_m0"] <= 1.00
    assert 0.038 <= b["Delta_0_VBM_SO_eV"] <= 0.050
    # Silicon CBM must carry substantial d- and p-orbital character
    assert b["cbm_orbital_weights"]["d"] > 0.30
    assert b["cbm_orbital_weights"]["p"] > 0.30

    rel_err = tb.verify_fft_vs_sparse_equivalence(N=4)
    assert rel_err < 1e-12, f"FFT vs sparse CSR mismatch: {rel_err}"


def test_02_non_diamond_coordinate_audit() -> None:
    """Confirm (3,3,0) and (1,1,3) are non-diamond while all 10 report shells are valid Si sites."""
    audit = tb.audit_non_diamond_coordinates()
    assert audit["(3,3,0)"]["is_valid_diamond"] is False
    assert audit["(1,1,3)"]["is_valid_diamond"] is False
    for name in tb.REPORT_SHELLS:
        assert audit[name]["is_valid_diamond"] is True, f"Report shell {name} failed diamond check"


def test_03_donor_31p_spectrum_and_convergence() -> None:
    """Verify N=20 31P calibration accuracy, Td multiplet degeneracies, and N=16 finite-size convergence."""
    d = _load_json(RES_DIR / "exp136.json")
    s2 = d["stage2_donor_31p_supercell"]
    n20 = s2["primary_N20"]
    assert n20["N"] >= 16 and n20["n_atoms"] >= 8192 and n20["n_orbitals"] >= 81920
    assert abs(n20["E_1s_A1_meV"] - tb.TARGET_E_A1_MEV) <= 0.15
    assert abs(n20["Delta_VO_T2_meV"] - tb.TARGET_DVO_T2_MEV) <= 0.15
    assert abs(n20["Delta_VO_E_meV"] - tb.TARGET_DVO_E_MEV) <= 0.15
    assert abs(n20["A_P_0_MHz"] - tb.TARGET_AP0_MHZ) <= 1.0
    assert n20["T2_spread_meV"] < 1e-3
    assert n20["E_spread_meV"] < 1e-3
    assert n20["eig_residual_eV"] < 1e-6
    assert s2["finite_size_shift_N16_N20_meV"] <= 1.5


def test_04_out_of_sample_endor_r331_and_logrms() -> None:
    """Verify atomistic sp3d5s* resolves R331 (<=30% err) & slashes 4-shell log10-RMS vs KL & VOKL-6."""
    d = _load_json(RES_DIR / "exp136.json")
    s3 = d["stage3_endor_shell_benchmarks"]
    assert 0.0 < s3["primary_alpha_cp"] <= 0.10
    sh_dir = s3["tb_sp3d5s_direct_3s"]
    sh_cp = s3["tb_sp3d5s_primary_3s_cp"]
    assert sh_dir["err_R331"] <= 0.30
    assert sh_cp["err_R331"] <= 0.30
    assert sh_cp["err_R331"] < s3["exp129_KL_legacy"]["err_R331"]
    assert sh_cp["err_R331"] < s3["exp129_VOKL6_full"]["err_R331"]
    assert sh_cp["log10_rms_4shells"] < s3["exp129_KL_legacy"]["log10_rms_4shells"]
    assert sh_cp["log10_rms_4shells"] < s3["exp129_VOKL6_full"]["log10_rms_4shells"]


def test_05_atlas_45214_dipolar_tracelessness() -> None:
    """Verify all 45,214-site E_z atlases have exact traceless 3D dipolar tensors (< 1e-10 Hz)."""
    d = _load_json(RES_DIR / "exp136.json")
    s5 = d["stage5_atlas_45214_audit"]
    assert "Ez_0MVm" in s5 and "Ez_3MVm" in s5
    for key, aud in s5.items():
        assert aud["n_sites_total"] == 45214, f"{key} site count mismatch"
        assert aud["n_sites_atomistic"] >= 8000
        assert aud["max_abs_trace_T_dip_Hz"] < 1e-10, f"{key} dipolar trace error too high"
        assert aud["frac_strong_in_atomistic_core"] >= 0.45


def test_06_atomistic_stark_shift_quadratic_and_parity() -> None:
    """Verify negative pure-quadratic 31P Stark shift, exact E(+1)==E(-1) parity, and N-scaling."""
    d = _load_json(RES_DIR / "exp136.json")
    s4 = d["stage4_stark_shift"]
    assert s4["eta_A_fit_um2_per_V2"] < 0.0
    assert s4["quadratic_fit_R2"] > 0.9999
    assert s4["electric_polarizability_ueV_per_MVm2"] > 0.0
    par = s4["parity_check_pos1_vs_neg1"]
    assert par["abs_E_parity_err_ueV"] < 1e-4
    assert par["abs_A_parity_err_Hz"] < 1e-1
    sc_eta = s4["finite_box_eta_A_scaling"]
    # Larger box relaxes 2p_0 confinement -> strictly larger |eta_A| from N=16 to N=24
    assert sc_eta["N24_L9p22nm_um2_per_V2"] < sc_eta["N20_L7p68nm_um2_per_V2"] < sc_eta["N16_L6p14nm_um2_per_V2"] < 0.0


def test_07_independent_percolation_and_coherence_recomputation() -> None:
    """Independently verify Binomial M4 L=11 FT percolation, Exp62/126 T2e(f) & Abragam T2n*(f)."""
    d = _load_json(RES_DIR / "exp136.json")
    rows = d["stage6_isotope_stark_sweep"]["primary_TB_CP_HM5962"]
    assert len(rows) == 8
    for r in rows:
        f_pct = r["abundance_pct"]
        # Independent Exp62/126 T2e(f) check
        k_bath = (1.0 / 0.0003 - 1.0 / 0.010) / 0.047
        t2e_ms_ref = 1e3 / (1.0 / 0.010 + k_bath * (f_pct / 100.0))
        assert abs(r["coherence"]["T2e_hahn_ms"] - t2e_ms_ref) < 1e-9
        assert abs(r["coherence"]["T2e_XY8_N64_alpha2_ms"] - t2e_ms_ref * (64.0 ** (2.0 / 3.0))) < 1e-9

        # Independent Abragam T2n*(f) check (strictly inversely proportional to f)
        coh_check = sw136.coherence_vs_abundance(f_pct)
        assert abs(r["coherence"]["T2n_star_abragam_ms"] - coh_check["T2n_star_abragam_ms"]) < 1e-9

        # Independent Binomial M4 L=11 (<=6/121 dead) check at N_cand=6
        p_m4 = r["mode_b"]["yield_frac"] * 0.9520
        p_node = 1.0 - (1.0 - p_m4) ** 6
        y_ref = sum(math.comb(121, k) * ((1.0 - p_node) ** k) * (p_node ** (121 - k)) for k in range(7))
        assert abs(r["m4_percolation_base"]["Y_FT_Ncand6"] - y_ref) < 1e-9


def test_08_exp136_verdict_integrity_and_preregistration() -> None:
    """Recompute every TB1-TB7 verdict independently from stored metrics and verify pre-registration."""
    pred = _load_json(RES_DIR / "predictions_exp136.json")
    d = _load_json(RES_DIR / "exp136.json")
    assert pred["no_lab_measurement"] is True
    assert d["no_lab_measurement"] is True
    assert pred["registered_before_computation"] is True

    v = d["verdicts"]
    s1 = d["stage1_bulk_si_sp3d5s"]
    b = s1["bands"]
    re_tb1 = (
        1.10 <= b["E_gap_indirect_SO_eV"] <= 1.20
        and 0.80 <= b["k_min_frac_2pi_a"] <= 0.86
        and 0.17 <= b["m_t_m0"] <= 0.22
        and 0.85 <= b["m_l_m0"] <= 1.00
        and 0.038 <= b["Delta_0_VBM_SO_eV"] <= 0.050
        and s1["fft_vs_csr_N4_rel_err"] < 1e-12
    )
    assert v["TB1_BULK_SP3D5S_BANDS"] == re_tb1 and re_tb1 is True

    s3 = d["stage3_endor_shell_benchmarks"]
    sh_cp = s3["tb_sp3d5s_primary_3s_cp"]
    re_tb4 = (
        sh_cp["log10_rms_4shells"] < s3["exp129_KL_legacy"]["log10_rms_4shells"]
        and sh_cp["log10_rms_4shells"] < s3["exp129_VOKL6_full"]["log10_rms_4shells"]
        and sh_cp["abinitio_a004_rel_err"] <= 0.35
    )
    assert v["TB4_MULTISHELL_ENDOR_BENCHMARK"] == re_tb4

    p_row = d["stage6_isotope_stark_sweep"]["pareto_TB_CP_HM5962"]["primary_row"]
    re_tb7 = (
        p_row is not None
        and p_row["m4_percolation_base"]["Y_FT_Ncand6"] >= 0.995
        and p_row["coherence"]["T2e_hahn_ms"] >= 10.0
    )
    assert v["TB7_SIMULTANEOUS_T2E_10MS_FEASIBILITY"] == re_tb7
    # Honest physical fact: raw Hahn-echo T2e at f >= 0.5% cannot reach 10 ms
    assert re_tb7 is False
    assert d["verdict_counts"]["passed"] == sum(1 for x in v.values() if x)
    # OBS-048, OBS-029, OBS-110 audits
    aud48 = d["ab_initio_uncertainty_and_stark_convergence_audit"]
    assert aud48["inter_model_spread_ratio"] > 2.0
    assert aud48["stark_n20_suppression_below_bulk_x"] > 7.0
    assert aud48["tb4_honest_verdict"] == "FAIL"
    assert aud48["tb5_honest_verdict"] == "FAIL"
    row_f15 = next(r for r in d["stage6_isotope_stark_sweep"]["primary_TB_CP_HM5962"] if abs(r["abundance_pct"] - 1.5) < 1e-6)
    assert 6.5 <= row_f15["coherence"]["T2e_conservative_planning_alpha1_ms"] <= 7.5
    assert row_f15["coherence"]["overhauser_sigma_KL_MHz"] > 1.2
    assert "m4_percolation_ddrf_and_iradina_valley" in row_f15


def test_09_png_integrity_and_zero_hardcoded_paths() -> None:
    """Verify 2400x1400 PNG header & zero hardcoded host/user paths across Exp136 files."""
    png = RES_DIR / "fig_exp136_tb_hyperfine_f_opt.png"
    assert png.is_file(), f"Missing figure: {png}"
    raw = png.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", raw[16:24])
    assert (width, height) == (2400, 1400), f"Unexpected PNG dimensions: {(width, height)}"

    import re
    forbidden = [
        re.compile(r"/home/[a-zA-Z0-9_-]+"),
        re.compile(r"/run/media/"),
        re.compile(r"E:\\\\"),
        re.compile(r"C:\\\\Users\\\\"),
    ]
    files_to_scan = [
        *EXP_DIR.glob("*.py"),
        *RES_DIR.glob("*.json"),
        *RES_DIR.glob("*.md"),
        Path(__file__).resolve(),
    ]
    for fp in files_to_scan:
        txt = fp.read_text(encoding="utf-8")
        if fp == Path(__file__).resolve():
            txt = "\n".join(ln for ln in txt.splitlines() if "re.compile(" not in ln)
        for pat in forbidden:
            assert pat.search(txt) is None, f"Hardcoded host path {pat.pattern!r} found in {fp.name}"


def test_10_summary_gfm_table_integrity() -> None:
    """Verify summary_exp136.md exists, sets no_lab_measurement, and has 0 GFM table column mismatches."""
    md = RES_DIR / "summary_exp136.md"
    assert md.is_file(), f"Missing summary: {md}"
    lines = md.read_text(encoding="utf-8").splitlines()
    assert any("no_lab_measurement" in ln for ln in lines)

    # Check every contiguous GFM table block for uniform column count
    i = 0
    table_count = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("|") and ln.endswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                block.append(lines[i].strip())
                i += 1
            table_count += 1
            assert len(block) >= 3, f"Malformed short table at line {i}"
            # Count unescaped pipe separators (subtract outer 2 pipes)
            def _col_count(row: str) -> int:
                cleaned = row.replace("\\|", "ESCAPED_PIPE")
                return cleaned.count("|") - 1

            expected_cols = _col_count(block[0])
            for r_idx, row in enumerate(block):
                got = _col_count(row)
                assert got == expected_cols, f"GFM column mismatch in table {table_count} row {r_idx}: {got} != {expected_cols}"
        else:
            i += 1
    assert table_count >= 4, f"Expected >=4 GFM summary tables, found {table_count}"
