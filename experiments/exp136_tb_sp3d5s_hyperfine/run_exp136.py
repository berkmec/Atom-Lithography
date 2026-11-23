"""Exp136 (H154): Master Runner — Atomistic 10-Band sp3d5s* Boykin-Klimeck Tight-Binding,
R331 Core Polarization, Atomistic Stark Tuning & Optimal 29Si Isotope Fraction f*.

Executes all 6 stages end-to-end (< 3 min on 8 CPU cores), evaluates pre-registered verdicts
TB1-TB7 strictly against results/exp136_tb_sp3d5s_hyperfine/predictions_exp136.json (never
modifying the pre-registration), and writes:
  - results/exp136_tb_sp3d5s_hyperfine/exp136.json
  - results/exp136_tb_sp3d5s_hyperfine/plot_data_exp136.json

Zero hardcoded user or host paths (strictly Path(__file__).resolve()).
Epistemic status: no_lab_measurement=True ({Literatür}/{Analitik}/{Model}/{Sayısal-Simülasyon}).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parents[1]
RESULTS_DIR = ROOT / "results" / "exp136_tb_sp3d5s_hyperfine"

sys.path.insert(0, str(THIS_DIR))
sys.path.insert(0, str(ROOT / "experiments" / "exp129_valley_orbital_hyperfine"))
sys.path.insert(0, str(ROOT / "experiments" / "exp42_isotope_coded_atom"))

import bath_yield129 as by129  # noqa: E402
import isotope_stark_sweep136 as sw136  # noqa: E402
import tb_sp3d5s_solver as tb  # noqa: E402


def _strip_psi(sol: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in sol.items() if k != "psi_a1"}


def main() -> None:
    t_start = time.time()
    pred_path = RESULTS_DIR / "predictions_exp136.json"
    if not pred_path.is_file():
        raise FileNotFoundError(f"Pre-registration file missing: {pred_path}")
    pred_doc = json.loads(pred_path.read_text(encoding="utf-8"))

    # Load Exp129 primary baseline numbers (read-only) for exact side-by-side comparison
    exp129_path = ROOT / "results" / "exp129_valley_orbital_hyperfine" / "exp129.json"
    d129 = json.loads(exp129_path.read_text(encoding="utf-8"))
    kl_129 = d129["shell_benchmarks"]["models"]["KL_legacy"]
    vokl_129 = d129["shell_benchmarks"]["models"]["VOKL6_full_k085"]

    print("=== Stage 1: Bulk Boykin-Klimeck (2004) Si sp3d5s* Bands & FFT-vs-CSR Equivalence ===", flush=True)
    t1 = time.time()
    bulk = tb.verify_bulk_si_bands()
    fft_csr_err = tb.verify_fft_vs_sparse_equivalence(N=4)
    print(
        f"  E_g(SO)={bulk['E_gap_indirect_SO_eV']:.4f} eV, k_min={bulk['k_min_frac_2pi_a']:.4f}, "
        f"m_t={bulk['m_t_m0']:.4f}, m_l={bulk['m_l_m0']:.4f}, Delta_0={bulk['Delta_0_VBM_SO_eV']:.5f} eV, "
        f"FFT-vs-CSR={fft_csr_err:.2e} ({time.time() - t1:.2f} s)",
        flush=True,
    )

    print("\n=== Stage 2: Supercell N=20 (16,000 atoms / 160,000 orbs) 31P Calibration & Finite-Size Check ===", flush=True)
    t2 = time.time()
    sc20 = tb.build_fcc_supercell(20)
    sc16 = tb.build_fcc_supercell(16)
    sc24 = tb.build_fcc_supercell(24)

    cal20 = tb.calibrate_31p_tb_decoupled(sc20)
    p = cal20["params"]
    print(
        f"  N=20 calibrated in {time.time() - t2:.1f} s ({cal20['calibration_solves']} solves): "
        f"E_A1={cal20['E_1s_A1_meV']:.4f}, dT2={cal20['Delta_VO_T2_meV']:.4f} (sp={cal20['T2_spread_meV']:.2e}), "
        f"dE={cal20['Delta_VO_E_meV']:.4f} (sp={cal20['E_spread_meV']:.2e}), AP0={cal20['A_P_0_MHz']:.3f} MHz",
        flush=True,
    )
    print(f"  Params (31P single-atom 4-orb, ZERO 29Si fit): {p}", flush=True)

    # Finite-size convergence check at identical calibrated params on N=16 and N=24
    sol16 = tb.solve_donor_1s_manifold(
        sc16, p["u0_s_eV"], p["u0_s_star_eV"], p["u0_p_eV"], p["u0_d_eV"], k_states=1, tol_eig=1e-7
    )
    sol24 = tb.solve_donor_1s_manifold(
        sc24, p["u0_s_eV"], p["u0_s_star_eV"], p["u0_p_eV"], p["u0_d_eV"], k_states=1, tol_eig=1e-7
    )
    fs_shift_16_20 = abs(sol16["E_1s_A1_meV"] - cal20["E_1s_A1_meV"])
    fs_shift_20_24 = abs(sol24["E_1s_A1_meV"] - cal20["E_1s_A1_meV"])
    print(
        f"  Finite-size convergence: E_A1(N=16)={sol16['E_1s_A1_meV']:.4f}, N=20={cal20['E_1s_A1_meV']:.4f} "
        f"(|16-20|={fs_shift_16_20:.4f} meV), N=24={sol24['E_1s_A1_meV']:.4f} (|20-24|={fs_shift_20_24:.4f} meV)",
        flush=True,
    )

    # 1-parameter Rahman scalar U_0 baseline on N=20
    rahman20 = tb.calibrate_rahman_1param_baseline(sc20)
    print(
        f"  Rahman 1-param U0={rahman20['U0_scalar_eV']:.4f} eV: E_A1={rahman20['E_1s_A1_meV']:.3f}, "
        f"dT2={rahman20['Delta_VO_T2_meV']:.3f}, dE={rahman20['Delta_VO_E_meV']:.3f}, AP0={rahman20['A_P_0_MHz']:.2f} MHz",
        flush=True,
    )

    print("\n=== Stage 3: Out-of-Sample 29Si ENDOR Shell Benchmark & Core-Polarization Ablation ===", flush=True)
    sh_direct = tb.evaluate_tb_shells(sc20, cal20["psi_a1"], alpha_cp_p=0.0, alpha_cp_d=0.0)
    sh_primary_cp = tb.evaluate_tb_shells(
        sc20, cal20["psi_a1"], alpha_cp_p=tb.ALPHA_CP_PRIMARY, alpha_cp_d=tb.ALPHA_CP_PRIMARY
    )
    sh_s_plus_sstar_direct = tb.evaluate_tb_shells(
        sc20, cal20["psi_a1"], alpha_cp_p=0.0, alpha_cp_d=0.0, include_s_star_in_29si=True
    )
    sh_s_plus_sstar_cp = tb.evaluate_tb_shells(
        sc20, cal20["psi_a1"], alpha_cp_p=tb.ALPHA_CP_PRIMARY, alpha_cp_d=tb.ALPHA_CP_PRIMARY, include_s_star_in_29si=True
    )
    sh_rahman_cp = tb.evaluate_tb_shells(
        sc20, rahman20["psi_a1"], alpha_cp_p=tb.ALPHA_CP_PRIMARY, alpha_cp_d=tb.ALPHA_CP_PRIMARY
    )
    sh_n24_cp = tb.evaluate_tb_shells(
        sc24, sol24["psi_a1"], alpha_cp_p=tb.ALPHA_CP_PRIMARY, alpha_cp_d=tb.ALPHA_CP_PRIMARY
    )

    cp_ablation = []
    for acp in [0.0, 0.005, 0.010, 0.015, 0.020, 0.030, 0.040, 0.060]:
        sh_a = tb.evaluate_tb_shells(sc20, cal20["psi_a1"], alpha_cp_p=acp, alpha_cp_d=acp)
        cp_ablation.append({
            "alpha_cp": acp,
            "abinitio_a004_MHz": sh_a["abinitio_a004_MHz"],
            "abinitio_a004_rel_err": sh_a["abinitio_a004_rel_err"],
            "R111": sh_a["ratios"]["(1,1,1)"],
            "R331": sh_a["ratios"]["(3,3,1)"],
            "err_R331": sh_a["err_R331"],
            "R220": sh_a["ratios"]["(2,2,0)"],
            "R11m3": sh_a["ratios"]["(1,1,-3)"],
            "log10_rms_4shells": sh_a["log10_rms_4shells"],
        })
        print(
            f"  alpha_cp={acp:.3f}: a004={sh_a['abinitio_a004_MHz']:.3f} ({100*sh_a['abinitio_a004_rel_err']:.1f}%), "
            f"R111={sh_a['ratios']['(1,1,1)']:.4f}, R331={sh_a['ratios']['(3,3,1)']:.4f} ({100*sh_a['err_R331']:.1f}%), "
            f"logRMS={sh_a['log10_rms_4shells']:.4f}",
            flush=True,
        )
    print(
        f"  [Sensitivity s+s* (0cp)]: a004={sh_s_plus_sstar_direct['abinitio_a004_MHz']:.3f} "
        f"({100*sh_s_plus_sstar_direct['abinitio_a004_rel_err']:.1f}%), "
        f"R111={sh_s_plus_sstar_direct['ratios']['(1,1,1)']:.4f}, "
        f"R331={sh_s_plus_sstar_direct['ratios']['(3,3,1)']:.4f} ({100*sh_s_plus_sstar_direct['err_R331']:.1f}%), "
        f"logRMS={sh_s_plus_sstar_direct['log10_rms_4shells']:.4f}",
        flush=True,
    )
    coord_audit = tb.audit_non_diamond_coordinates()

    print("\n=== Stage 4: Direct Atomistic E_z in [0, 3.0] MV/m Stark Shift Sweep & Box-Size Scaling ===", flush=True)
    t4 = time.time()
    ez_grid = list(pred_doc["sweep_grid"]["electric_fields_MV_per_m"])
    keep_ez = {0.0, 1.0, 2.0, 3.0}
    stark = tb.run_stark_sweep(
        sc20, p, cal20["psi_a1"], ez_grid, cal20["E_1s_A1_meV"], cal20["A_P_0_MHz"], keep_psi_fields=keep_ez
    )
    # Finite-box Stark scaling check at E_z = 1.0 MV/m on N=16 and N=24 (2p_0 box-confinement diagnostic)
    sol16_ez1 = tb.solve_donor_1s_manifold(
        sc16, p["u0_s_eV"], p["u0_s_star_eV"], p["u0_p_eV"], p["u0_d_eV"],
        e_field_mv_per_m=1.0, k_states=1, sigma_below_cbm_meV=-sol16["E_1s_A1_meV"] + 0.5,
        tol_eig=1e-8, v0_init=sol16["psi_a1"].ravel(),
    )
    sol24_ez1 = tb.solve_donor_1s_manifold(
        sc24, p["u0_s_eV"], p["u0_s_star_eV"], p["u0_p_eV"], p["u0_d_eV"],
        e_field_mv_per_m=1.0, k_states=1, sigma_below_cbm_meV=-sol24["E_1s_A1_meV"] + 0.5,
        tol_eig=1e-8, v0_init=sol24["psi_a1"].ravel(),
    )
    eta_n16 = (sol16_ez1["A_P_0_MHz"] - sol16["A_P_0_MHz"]) / sol16["A_P_0_MHz"]
    eta_n24 = (sol24_ez1["A_P_0_MHz"] - sol24["A_P_0_MHz"]) / sol24["A_P_0_MHz"]
    stark["finite_box_eta_A_scaling"] = {
        "N16_L6p14nm_um2_per_V2": float(eta_n16),
        "N20_L7p68nm_um2_per_V2": float(stark["eta_A_fit_um2_per_V2"]),
        "N24_L9p22nm_um2_per_V2": float(eta_n24),
    }
    print(
        f"  Stark sweep done in {time.time() - t4:.1f} s | eta_A(N=16/20/24) = "
        f"{eta_n16:.3e} / {stark['eta_A_fit_um2_per_V2']:.3e} / {eta_n24:.3e} um^2/V^2 "
        f"(R^2={stark['quadratic_fit_R2']:.8f}, parity_err={stark['parity_check_pos1_vs_neg1']['abs_A_parity_err_Hz']:.2e} Hz)",
        flush=True,
    )

    print("\n=== Stage 5: 45,214-Site Atomistic + Matched-Tail 3D Hyperfine Atlas (B || [123]) ===", flush=True)
    t5 = time.time()
    atlas_by_ez: dict[float, dict[str, Any]] = {}
    for ez_val in sorted(keep_ez):
        atlas_by_ez[ez_val] = tb.build_atomistic_45214_atlas(
            sc20, stark["psi_by_ez"][ez_val], by129.SITES_NM, by129.BDIR, alpha_cp=tb.ALPHA_CP_PRIMARY
        )
    atlas0 = atlas_by_ez[0.0]
    print(f"  Built 45,214-site atlases (E_z=0..3 MV/m) in {time.time() - t5:.2f} s | audit={atlas0['audit']}", flush=True)

    print("\n=== Stage 6: Mode B Isotope (f) x Stark (E_z) Yield, Coherence & M4 L=11 Percolation ===", flush=True)
    t6 = time.time()
    abundances = [float(x) for x in pred_doc["sweep_grid"]["abundances_pct"]]
    n_cell = int(pred_doc["sweep_grid"]["n_cell_realizations"])
    n_cand_list = tuple(int(x) for x in pred_doc["sweep_grid"]["percolation_N_cand_list"])

    # 6A. Primary full 8-abundance sweep under atomistic sp3d5s* Hale-Mieher 5.962 MHz atlas
    sweep_hm5962 = sw136.run_abundance_sweep(
        atlas0["A_zz_HM5962_Hz"], abundances, reals=n_cell, n_cand_list=n_cand_list
    )
    pareto_hm5962 = sw136.select_pareto_f_star(sweep_hm5962)

    print("  Primary TB+CP (HM5962) f-sweep:", flush=True)
    for r in sweep_hm5962:
        mb = r["mode_b"]
        coh = r["coherence"]
        p6 = r["m4_percolation_base"]["Y_FT_Ncand6"]
        nc995 = r["m4_percolation_base"]["N_cand_star_99p5pct"]
        print(
            f"    f={r['abundance_pct']:4.2f}% | P_yield={100*mb['yield_frac']:5.2f}% "
            f"(>=6.89k:{100*mb['gap_stats']['yield_and_gap_ge_6893Hz']:5.2f}%, "
            f">=10k:{100*mb['gap_stats']['yield_and_gap_ge_10kHz']:5.2f}%) | "
            f"M4 L=11 N6={100*p6:6.2f}% (N*={nc995:2d}) | "
            f"T2e_Hahn={coh['T2e_hahn_ms']:.2f} ms, XY8_N64={coh['T2e_XY8_N64_alpha2_ms']:.1f} ms, "
            f"T2n*={coh['T2n_star_abragam_ms']:.1f} ms",
            flush=True,
        )

    # 6B. Ab-initio (unscaled a004=3.65 MHz) & Legacy repo2981 sensitivities at key abundances
    key_f = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    sweep_abinit = sw136.run_abundance_sweep(
        atlas0["A_zz_abinit_Hz"], key_f, reals=n_cell, n_cand_list=n_cand_list
    )
    pareto_abinit = sw136.select_pareto_f_star(sweep_abinit)
    sweep_repo2981 = sw136.run_abundance_sweep(
        atlas0["A_zz_repo2981_Hz"], [0.5, 1.0, 2.0], reals=n_cell, n_cand_list=n_cand_list
    )

    # 6C. Stark electric-field Mode B yield tuning P_yield(f, E_z) for E_z in {0, 1, 2, 3} MV/m
    sweep_by_f = {r["abundance_pct"]: r["mode_b"] for r in sweep_hm5962}
    stark_yield_rows: list[dict[str, Any]] = []
    for f_ez in [1.0, 1.5, 2.0]:
        for ez_val in [0.0, 1.0, 2.0, 3.0]:
            if ez_val == 0.0 and f_ez in sweep_by_f:
                cell_ez = sweep_by_f[f_ez]
            else:
                cell_ez = sw136.augment_cell_with_15khz(
                    by129.run_mode_b_cell(atlas_by_ez[ez_val]["A_zz_HM5962_Hz"], f_pct=f_ez, reals=n_cell)
                )
            stark_yield_rows.append({
                "abundance_pct": f_ez,
                "E_z_MV_per_m": ez_val,
                "yield_frac": cell_ez["yield_frac"],
                "wilson_ci95": cell_ez["wilson_ci95"],
                "yield_and_gap_ge_6893Hz": cell_ez["gap_stats"]["yield_and_gap_ge_6893Hz"],
                "yield_and_gap_ge_10kHz": cell_ez["gap_stats"]["yield_and_gap_ge_10kHz"],
                "median_gap_Hz": cell_ez["gap_stats"]["median_Hz"],
            })
    print(f"  Mode B f x E_z sweep completed in {time.time() - t6:.1f} s", flush=True)

    # -----------------------------------------------------------------------
    # Stage 7: Strict Verbatim Verdict Evaluation (TB1 - TB7)
    # -----------------------------------------------------------------------
    tb1 = bool(
        1.10 <= bulk["E_gap_indirect_SO_eV"] <= 1.20
        and 0.80 <= bulk["k_min_frac_2pi_a"] <= 0.86
        and 0.17 <= bulk["m_t_m0"] <= 0.22
        and 0.85 <= bulk["m_l_m0"] <= 1.00
        and 0.038 <= bulk["Delta_0_VBM_SO_eV"] <= 0.050
        and fft_csr_err < 1e-12
    )
    tb2 = bool(
        cal20["N"] >= 16
        and cal20["n_atoms"] >= 8192
        and cal20["n_orbitals"] >= 81920
        and abs(cal20["E_1s_A1_meV"] - tb.TARGET_E_A1_MEV) <= 0.15
        and abs(cal20["Delta_VO_T2_meV"] - tb.TARGET_DVO_T2_MEV) <= 0.15
        and abs(cal20["Delta_VO_E_meV"] - tb.TARGET_DVO_E_MEV) <= 0.15
        and abs(cal20["A_P_0_MHz"] - tb.TARGET_AP0_MHZ) <= 1.0
        and cal20["T2_spread_meV"] < 1e-3
        and cal20["E_spread_meV"] < 1e-3
        and fs_shift_16_20 <= 1.5
    )
    tb3 = bool(
        sh_direct["err_R331"] <= 0.30
        and sh_primary_cp["err_R331"] <= 0.30
        and sh_primary_cp["err_R331"] < kl_129["err_R331"]
        and sh_primary_cp["err_R331"] < vokl_129["err_R331"]
        and tb.ALPHA_CP_PRIMARY <= 0.10
    )
    tb4 = bool(
        sh_primary_cp["log10_rms_4shells"] < kl_129["log10_rms_4shells"]
        and sh_primary_cp["log10_rms_4shells"] < vokl_129["log10_rms_4shells"]
        and sh_primary_cp["abinitio_a004_rel_err"] <= 0.35
    )
    tb5 = bool(
        -3.0e-2 <= stark["eta_A_fit_um2_per_V2"] <= -1.0e-3
        and len(stark_yield_rows) >= 12
    )
    y_by_f = {r["abundance_pct"]: r["mode_b"]["yield_frac"] for r in sweep_hm5962}
    mono_05_20 = all(
        y_by_f[f1] <= y_by_f[f2] + 1e-12
        for f1, f2 in zip([0.5, 1.0, 1.25, 1.5, 1.75], [1.0, 1.25, 1.5, 1.75, 2.0])
    ) and (y_by_f[2.0] > y_by_f[0.5])
    f_star_base = pareto_hm5962["f_star_base_Ncand6_99p5_pct"]
    tb6 = bool(mono_05_20 and f_star_base is not None and f_star_base <= 2.5)

    p_row = pareto_hm5962["primary_row"]
    tb7 = bool(
        p_row is not None
        and p_row["m4_percolation_base"]["Y_FT_Ncand6"] >= 0.995
        and p_row["coherence"]["T2e_hahn_ms"] >= 10.0
    )

    verdicts = {
        "TB1_BULK_SP3D5S_BANDS": tb1,
        "TB2_DONOR_31P_SPECTRUM_AND_CONVERGENCE": tb2,
        "TB3_ATOMISTIC_R331_IMPROVEMENT": tb3,
        "TB4_MULTISHELL_ENDOR_BENCHMARK": tb4,
        "TB5_STARK_SHIFT_AND_TUNING": tb5,
        "TB6_ISOTOPE_SWEEP_AND_M4_PERCOLATION": tb6,
        "TB7_SIMULTANEOUS_T2E_10MS_FEASIBILITY": tb7,
    }
    n_pass = sum(1 for v in verdicts.values() if v)
    n_total = len(verdicts)
    success_rule_met = all(verdicts[k] for k in [
        "TB1_BULK_SP3D5S_BANDS",
        "TB2_DONOR_31P_SPECTRUM_AND_CONVERGENCE",
        "TB3_ATOMISTIC_R331_IMPROVEMENT",
        "TB4_MULTISHELL_ENDOR_BENCHMARK",
        "TB5_STARK_SHIFT_AND_TUNING",
        "TB6_ISOTOPE_SWEEP_AND_M4_PERCOLATION",
    ])

    elapsed_sec = time.time() - t_start
    print(f"\n=== VERDICTS ({n_pass}/{n_total} PASS | elapsed={elapsed_sec:.1f} s) ===", flush=True)
    for k, v in verdicts.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}", flush=True)

    # Assemble clean JSON output (no raw numpy arrays, zero hardcoded host paths)
    stark_json = {k: v for k, v in stark.items() if k != "psi_by_ez"}
    result = {
        "experiment": "exp136_tb_sp3d5s_hyperfine",
        "hypothesis_id": "H154",
        "risk_target": "R1",
        "no_lab_measurement": True,
        "epistemic_tags": ["{Literatür}", "{Analitik}", "{Model}", "{Sayısal-Simülasyon}"],
        "elapsed_sec": float(elapsed_sec),
        "verdicts": verdicts,
        "verdict_counts": {"passed": n_pass, "failed": n_total - n_pass, "total": n_total},
        "success_rule_met": bool(success_rule_met),
        "stage1_bulk_si_sp3d5s": {
            "bands": bulk,
            "fft_vs_csr_N4_rel_err": float(fft_csr_err),
        },
        "stage2_donor_31p_supercell": {
            "primary_N20": _strip_psi(cal20),
            "finite_size_N16": _strip_psi(sol16),
            "finite_size_N24": _strip_psi(sol24),
            "finite_size_shift_N16_N20_meV": float(fs_shift_16_20),
            "finite_size_shift_N20_N24_meV": float(fs_shift_20_24),
            "rahman_1param_baseline_N20": _strip_psi(rahman20),
            "coulomb_alignment": "V(r) = -K_C/r + K_C/L_NN (L_NN = N*a0/sqrt(2) nearest-image Makov-Payne midpoint)",
        },
        "stage3_endor_shell_benchmarks": {
            "primary_alpha_cp": float(tb.ALPHA_CP_PRIMARY),
            "targets": tb.AUDITED_SHELLS,
            "exp129_KL_legacy": {
                "ratios": kl_129["ratios"],
                "err_R111": kl_129["err_R111"],
                "err_R331": kl_129["err_R331"],
                "log10_rms_4shells": kl_129["log10_rms_4shells"],
            },
            "exp129_VOKL6_full": {
                "ratios": vokl_129["ratios"],
                "err_R111": vokl_129["err_R111"],
                "err_R331": vokl_129["err_R331"],
                "log10_rms_4shells": vokl_129["log10_rms_4shells"],
                "abinitio_a004_MHz": vokl_129["abinitio_A004_MHz_eta186"],
            },
            "tb_sp3d5s_direct_3s": sh_direct,
            "tb_sp3d5s_primary_3s_cp": sh_primary_cp,
            "tb_sp3d5s_sensitivity_s_plus_sstar_direct": sh_s_plus_sstar_direct,
            "tb_sp3d5s_sensitivity_s_plus_sstar_cp": sh_s_plus_sstar_cp,
            "tb_sp3d5s_rahman_1param_cp": sh_rahman_cp,
            "tb_sp3d5s_N24_cp": sh_n24_cp,
            "core_polarization_ablation": cp_ablation,
            "non_diamond_coordinate_audit": coord_audit,
        },
        "stage4_stark_shift": stark_json,
        "stage5_atlas_45214_audit": {
            f"Ez_{ez:g}MVm": atlas_by_ez[ez]["audit"] for ez in sorted(keep_ez)
        },
        "stage6_isotope_stark_sweep": {
            "n_cell_realizations": n_cell,
            "m4_cap_yield_exp131": sw136.M4_CAP_YIELD_EXP131,
            "primary_TB_CP_HM5962": sweep_hm5962,
            "pareto_TB_CP_HM5962": pareto_hm5962,
            "sensitivity_TB_CP_abinit": sweep_abinit,
            "pareto_TB_CP_abinit": pareto_abinit,
            "sensitivity_TB_CP_repo2981": sweep_repo2981,
            "stark_tuning_yield_HM5962": stark_yield_rows,
            "exp129_mode_b_reference": {
                "KL_legacy": {
                    f: {
                        "yield_frac": d129["mode_b_yield_n400"]["KL_legacy"][f]["yield_frac"],
                        "yield_and_gap_ge_6893Hz": d129["mode_b_yield_n400"]["KL_legacy"][f]["gap_stats"]["yield_and_gap_ge_6893Hz"],
                    }
                    for f in ("F0.5", "F1", "F2")
                },
                "VOKL6_HM5962": {
                    f: {
                        "yield_frac": d129["mode_b_yield_n400"]["VOKL6_HM5962_ext"][f]["yield_frac"],
                        "yield_and_gap_ge_6893Hz": d129["mode_b_yield_n400"]["VOKL6_HM5962_ext"][f]["gap_stats"]["yield_and_gap_ge_6893Hz"],
                    }
                    for f in ("F0.5", "F1", "F2")
                },
            },
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = RESULTS_DIR / "exp136.json"
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    # Compact plot_data_exp136.json for pure-graphics plot_exp136.py (/usr/bin/python3)
    plot_data = {
        "verdicts": verdicts,
        "verdict_counts": result["verdict_counts"],
        "shell_comparison": {
            "shells": ["(1,1,1)", "(3,3,1)", "(2,2,0)", "(1,1,-3)"],
            "target": [0.092, 0.293, 0.050, 0.030],
            "KL_legacy": [kl_129["ratios"][s] for s in ["(1,1,1)", "(3,3,1)", "(2,2,0)", "(1,1,-3)"]],
            "VOKL6_full": [vokl_129["ratios"][s] for s in ["(1,1,1)", "(3,3,1)", "(2,2,0)", "(1,1,-3)"]],
            "TB_direct": [sh_direct["ratios"][s] for s in ["(1,1,1)", "(3,3,1)", "(2,2,0)", "(1,1,-3)"]],
            "TB_CP": [sh_primary_cp["ratios"][s] for s in ["(1,1,1)", "(3,3,1)", "(2,2,0)", "(1,1,-3)"]],
            "TB_s_sstar": [sh_s_plus_sstar_direct["ratios"][s] for s in ["(1,1,1)", "(3,3,1)", "(2,2,0)", "(1,1,-3)"]],
            "logRMS": {
                "KL": kl_129["log10_rms_4shells"],
                "VOKL6": vokl_129["log10_rms_4shells"],
                "TB_CP": sh_primary_cp["log10_rms_4shells"],
                "TB_s_sstar": sh_s_plus_sstar_direct["log10_rms_4shells"],
            },
            "err_R331_pct": {
                "KL": 100.0 * kl_129["err_R331"],
                "VOKL6": 100.0 * vokl_129["err_R331"],
                "TB_direct": 100.0 * sh_direct["err_R331"],
                "TB_CP": 100.0 * sh_primary_cp["err_R331"],
            },
        },
        "stark_rows": stark_json["rows"],
        "eta_A_fit_um2_per_V2": stark_json["eta_A_fit_um2_per_V2"],
        "stark_yield_rows": stark_yield_rows,
        "f_sweep_hm5962": [
            {
                "f_pct": r["abundance_pct"],
                "yield_base": r["mode_b"]["yield_frac"],
                "ci_lo": r["mode_b"]["wilson_ci95"][0],
                "ci_hi": r["mode_b"]["wilson_ci95"][1],
                "yield_gap6p89": r["mode_b"]["gap_stats"]["yield_and_gap_ge_6893Hz"],
                "yield_gap10": r["mode_b"]["gap_stats"]["yield_and_gap_ge_10kHz"],
                "Y_FT_N3": r["m4_percolation_base"]["by_N_cand"]["3"]["Y_FT_5pct_exact"],
                "Y_FT_N6": r["m4_percolation_base"]["by_N_cand"]["6"]["Y_FT_5pct_exact"],
                "Y_FT_N8": r["m4_percolation_base"]["by_N_cand"]["8"]["Y_FT_5pct_exact"],
                "Y_FT_N10": r["m4_percolation_base"]["by_N_cand"]["10"]["Y_FT_5pct_exact"],
                "Y_FT_N6_gap6p89": r["m4_percolation_gap6p89kHz"]["by_N_cand"]["6"]["Y_FT_5pct_exact"],
                "T2e_hahn_ms": r["coherence"]["T2e_hahn_ms"],
                "T2e_XY8_N32_ms": r["coherence"]["T2e_XY8_N32_alpha2_ms"],
                "T2e_XY8_N64_ms": r["coherence"]["T2e_XY8_N64_alpha2_ms"],
                "T2n_star_ms": r["coherence"]["T2n_star_abragam_ms"],
            }
            for r in sweep_hm5962
        ],
        "f_sweep_abinit": [
            {
                "f_pct": r["abundance_pct"],
                "yield_base": r["mode_b"]["yield_frac"],
                "Y_FT_N6": r["m4_percolation_base"]["by_N_cand"]["6"]["Y_FT_5pct_exact"],
            }
            for r in sweep_abinit
        ],
        "pareto_f_star_base_pct": pareto_hm5962["f_star_base_Ncand6_99p5_pct"],
        "pareto_f_star_gap6p89_pct": pareto_hm5962["f_star_gap6p89_Ncand6_99p5_pct"],
    }
    (RESULTS_DIR / "plot_data_exp136.json").write_text(json.dumps(plot_data, indent=2), encoding="utf-8")
    print(f"Wrote {out_json} and plot_data_exp136.json successfully.", flush=True)


if __name__ == "__main__":
    main()
