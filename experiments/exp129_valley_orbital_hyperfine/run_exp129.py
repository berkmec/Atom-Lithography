"""Exp129 (H147) Orchestrator: VOKL-6 6-Valley Central-Cell Hyperfine Theory & Mode B Yield Recalibration.

Executes:
  1. First-principles VOKL-6 calibration exclusively to 31P spectral invariants + full EPM k-Bloch ablation.
  2. Full 45,214-site 3D hyperfine tensor atlas A(R) = A_iso(R) I_3 + T_dip(R) & KL vs VOKL-6 distribution audit.
  3. Bit-for-bit portable Exp59/62 Mode B audit (CE5, N=100).
  4. High-statistics Mode B epitaxial bath sweep (N_cell=400 per abundance for f in {0.5%, 1.0%, 2.0%})
     comparing Legacy KL vs VOKL-6 (primary normalized + extended dipole, point-dipole sensitivity,
     and zero-rescaling ab-initio sensitivity), including min_transition_gap_Hz and Exp126 6.893 kHz DDRF risk.
  5. Strict evaluation of all 7 pre-registered predictions CE1..CE7 from predictions_exp129.json.
  6. Writes results/exp129_valley_orbital_hyperfine/exp129.json and plot_data_exp129.json.

Epistemic status: no_lab_measurement=True ({Literatür}/{Analitik}/{Model}/{Sayısal-Simülasyon}).
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr

import bath_yield129 as by
import vokl6_theory as vt

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp129_valley_orbital_hyperfine"
PRED_PATH = OUT_DIR / "predictions_exp129.json"


def _coupling_atlas_comparison(a_kl: np.ndarray, a_vokl: np.ndarray, sites_nm: np.ndarray) -> dict[str, Any]:
    """Compare global 45,214-site coupling distributions between Legacy KL and VOKL-6."""
    abs_kl = np.abs(a_kl)
    abs_vk = np.abs(a_vokl)
    r_nm = np.linalg.norm(sites_nm, axis=1)

    strong_kl = abs_kl >= 10e3
    strong_vk = abs_vk >= 10e3
    either_strong = strong_kl | strong_vk

    ratio_on_kl_strong = abs_vk[strong_kl] / np.maximum(abs_kl[strong_kl], 1.0)
    rho_all = float(spearmanr(abs_kl, abs_vk).statistic)
    rho_strong = float(spearmanr(abs_kl[either_strong], abs_vk[either_strong]).statistic)

    # Radial shells breakdown of median |A| (Hz)
    radial_bins = [(0.2, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.0), (4.0, 5.0), (5.0, 6.0)]
    radial_summary = []
    for r0, r1 in radial_bins:
        m = (r_nm >= r0) & (r_nm < r1)
        radial_summary.append({
            "r_bin_nm": [r0, r1],
            "n_sites": int(np.sum(m)),
            "kl_median_absA_Hz": float(np.median(abs_kl[m])),
            "vokl6_median_absA_Hz": float(np.median(abs_vk[m])),
            "median_ratio_vokl6_over_kl": float(np.median(abs_vk[m] / np.maximum(abs_kl[m], 1e-6))),
            "kl_n_strong_10kHz": int(np.sum(abs_kl[m] >= 10e3)),
            "vokl6_n_strong_10kHz": int(np.sum(abs_vk[m] >= 10e3)),
        })

    return {
        "n_sites_total": int(len(a_kl)),
        "kl_n_strong_ge_10kHz": int(np.sum(strong_kl)),
        "vokl6_n_strong_ge_10kHz": int(np.sum(strong_vk)),
        "strong_site_ratio_vokl6_over_kl": float(np.sum(strong_vk) / max(1, int(np.sum(strong_kl)))),
        "spearman_absA_all_45214": rho_all,
        "spearman_absA_strong_union": rho_strong,
        "median_ratio_on_kl_strong": float(np.median(ratio_on_kl_strong)),
        "frac_change_gt_50pct_on_kl_strong": float(np.mean(np.abs(ratio_on_kl_strong - 1.0) > 0.50)),
        "radial_shell_breakdown": radial_summary,
    }


def _strip_gap_arrays(cell_dict: dict[str, Any]) -> dict[str, Any]:
    """Return a clean JSON copy of Mode B cell results without the raw 400-element gap list."""
    out = dict(cell_dict)
    gs = dict(cell_dict["gap_stats"])
    gs.pop("certified_min_gaps_Hz_sorted", None)
    out["gap_stats"] = gs
    return out


def main() -> None:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not PRED_PATH.exists():
        raise FileNotFoundError(f"Pre-registration file missing: {PRED_PATH}")
    preds = json.loads(PRED_PATH.read_text(encoding="utf-8"))

    print("[Exp129] Stage 1/4: Running first-principles VOKL-6 theory & ENDOR shell benchmark...", flush=True)
    t_th = time.time()
    th = vt.run_vokl6_theory_suite(n_xy=10, n_z_lo=8)
    blocks = th["blocks"]
    cal = th["calibration"]
    bare_emt = th["bare_emt"]
    print(
        f"  Theory done in {time.time() - t_th:.2f} s | E_EMT={bare_emt['E_emt_1s_meV']:.3f} meV | "
        f"E_A1={cal['E_1s_A1_meV']:.4f}, dT2={cal['Delta_VO_T2_meV']:.4f}, dE={cal['Delta_VO_E_meV']:.4f} meV, "
        f"A_P(0)={cal['A_P_0_MHz']:.3f} MHz, r_c={cal['params']['r_c_nm']:.4f} nm",
        flush=True,
    )

    print("[Exp129] Stage 2/4: Computing full 45,214-site 3D VOKL-6 hyperfine tensor atlas...", flush=True)
    t_at = time.time()
    atlas = vt.compute_full_atlas_vokl6(
        sites_nm=by.SITES_NM,
        b_dir=by.BDIR,
        blocks=blocks,
        c_1v=cal["c_1v"],
        k0_frac=vt.K0_FRAC,
        n_xy=10,
        n_z_lo=8,
    )
    atlas_cmp_ext = _coupling_atlas_comparison(by.A_KL_PRIMARY, atlas["A_dir_ext_Hz"], by.SITES_NM)
    atlas_cmp_hm = _coupling_atlas_comparison(by.A_KL_PRIMARY, atlas["A_dir_hm5962_ext_Hz"], by.SITES_NM)
    atlas_cmp_abinit = _coupling_atlas_comparison(by.A_KL_PRIMARY, atlas["A_dir_abinit_ext_Hz"], by.SITES_NM)
    print(
        f"  Atlas done in {time.time() - t_at:.2f} s | KL strong={atlas_cmp_ext['kl_n_strong_ge_10kHz']}, "
        f"VOKL6(2.981MHz)={atlas_cmp_ext['vokl6_n_strong_ge_10kHz']}, "
        f"VOKL6(HM 5.962MHz)={atlas_cmp_hm['vokl6_n_strong_ge_10kHz']}, "
        f"VOKL6(abinit)={atlas_cmp_abinit['vokl6_n_strong_ge_10kHz']} | "
        f"max|Tr(T_dip)|={atlas['max_abs_trace_T_dip_ext_Hz']:.2e} / {atlas['max_abs_trace_T_dip_pt_Hz']:.2e} Hz",
        flush=True,
    )

    print("[Exp129] Stage 3/4: Running portable Exp59/62 bit-for-bit audit (N=100)...", flush=True)
    audit59 = by.run_exp59_62_audit()
    print(f"  Audit CE5 all_exact_match={audit59['all_exact_match']}", flush=True)

    print("[Exp129] Stage 4/4: Running Mode B epitaxial bath sweep (N_cell=400, f=0.5/1.0/2.0%)...", flush=True)
    abundances = [0.5, 1.0, 2.0]
    n_cell = 400
    model_tables = {
        "KL_legacy": by.A_KL_PRIMARY,
        "VOKL6_norm_ext": atlas["A_dir_ext_Hz"],
        "VOKL6_norm_pt": atlas["A_dir_pt_Hz"],
        "VOKL6_HM5962_ext": atlas["A_dir_hm5962_ext_Hz"],
        "VOKL6_abinit_ext": atlas["A_dir_abinit_ext_Hz"],
    }

    mode_b_full: dict[str, dict[str, Any]] = {}
    gap_cdfs_for_plot: dict[str, dict[str, list[float]]] = {}
    for mname, a_vec in model_tables.items():
        t_m = time.time()
        mode_b_full[mname] = {}
        gap_cdfs_for_plot[mname] = {}
        for f_pct in abundances:
            fkey = f"F{f_pct:g}"
            res = by.run_mode_b_cell(a_vec, f_pct=f_pct, reals=n_cell)
            gap_cdfs_for_plot[mname][fkey] = res["gap_stats"]["certified_min_gaps_Hz_sorted"]
            mode_b_full[mname][fkey] = _strip_gap_arrays(res)
            gs = res["gap_stats"]
            print(
                f"  {mname:18s} {fkey:4s} | yield={res['yield_frac']:.4f} ({res['successes']:3d}/{n_cell}) "
                f"CI95=[{res['wilson_ci95'][0]:.3f},{res['wilson_ci95'][1]:.3f}] | "
                f"elig_med={res['eligible_median']:4.1f} strong_med={res['strong_median']:5.1f} | "
                f"gap_med={gs['median_Hz']/1e3:5.2f} kHz | <6.89kHz={100*gs['frac_lt_6893Hz']:4.1f}% "
                f"| <10kHz={100*gs['frac_lt_10kHz']:4.1f}%",
                flush=True,
            )
        print(f"  [{mname}] finished in {time.time() - t_m:.2f} s", flush=True)

    # Machine throughput & Risk R1 uncertainty band comparison
    # Legacy Exp60 uncertainty at f=0.5%: KL=26% vs EXT_DIAG=69% (+43 pp band).
    # Now compare VOKL-6 (normalized & ab-initio) vs KL across f=0.5%, 1.0%, 2.0%.
    yield_shifts_norm = {
        f"F{f:g}": float(mode_b_full["VOKL6_norm_ext"][f"F{f:g}"]["yield_frac"] - mode_b_full["KL_legacy"][f"F{f:g}"]["yield_frac"])
        for f in abundances
    }
    yield_shifts_hm5962 = {
        f"F{f:g}": float(mode_b_full["VOKL6_HM5962_ext"][f"F{f:g}"]["yield_frac"] - mode_b_full["KL_legacy"][f"F{f:g}"]["yield_frac"])
        for f in abundances
    }
    yield_shifts_abinit = {
        f"F{f:g}": float(mode_b_full["VOKL6_abinit_ext"][f"F{f:g}"]["yield_frac"] - mode_b_full["KL_legacy"][f"F{f:g}"]["yield_frac"])
        for f in abundances
    }
    max_abs_shift_norm = max(abs(v) for v in yield_shifts_norm.values())
    max_abs_shift_hm5962 = max(abs(v) for v in yield_shifts_hm5962.values())
    max_abs_shift_abinit = max(abs(v) for v in yield_shifts_abinit.values())

    # Evaluate pre-registered criteria CE1..CE7 verbatim (zero post-hoc edits!)
    b_kl = th["benchmarks"]["KL_legacy"]
    b_vk = th["benchmarks"]["VOKL6_full_k085"]

    ce1_pass = bool(
        abs(bare_emt["E_emt_1s_meV"] - (-31.27)) <= 0.25
        and abs(cal["E_1s_A1_meV"] - (-45.59)) <= 0.05
        and abs(cal["Delta_VO_T2_meV"] - 11.70) <= 0.05
        and abs(cal["Delta_VO_E_meV"] - 13.01) <= 0.05
        and abs(cal["A_P_0_MHz"] - 117.53) <= 0.50
        and (0.05 <= cal["params"]["r_c_nm"] <= 0.35)
    )
    ce2_pass = bool(
        cal["T2_degeneracy_spread_meV"] <= 1e-6
        and cal["E_degeneracy_spread_meV"] <= 1e-6
        and cal["valley_weight_spread"] <= 1e-10
        and abs(cal["norm_sq"] - 1.0) <= 1e-8
        and atlas["max_abs_trace_T_dip_ext_Hz"] < 1e-10
        and atlas["max_abs_trace_T_dip_pt_Hz"] < 1e-10
    )
    ce3_pass = bool(b_vk["err_R331"] <= 0.30 and b_vk["err_R331"] < b_kl["err_R331"])
    ce4_pass = bool(b_vk["log10_rms_4shells"] < b_kl["log10_rms_4shells"] and b_vk["err_R111"] <= 0.35)
    ce5_pass = bool(audit59["all_exact_match"])
    ce6_pass = bool(
        mode_b_full["VOKL6_norm_ext"]["F1"]["yield_frac"] >= 0.40
        and max_abs_shift_norm <= 0.15
    )
    f1_vk_gs = mode_b_full["VOKL6_norm_ext"]["F1"]["gap_stats"]
    ce7_pass = bool(
        f1_vk_gs["median_Hz"] >= by.GAP_THRESH_EXP126_HZ
        and f1_vk_gs["frac_lt_6893Hz"] <= 0.50
    )

    verdicts = {
        "CE1_SPECTRAL_INVARIANTS": ce1_pass,
        "CE2_SYMMETRY_AND_TENSOR": ce2_pass,
        "CE3_OUT_OF_SAMPLE_R331": ce3_pass,
        "CE4_MULTISHELL_LOG_RMS": ce4_pass,
        "CE5_PORTABLE_EXP59_AUDIT": ce5_pass,
        "CE6_MODE_B_YIELD_CLOSURE": ce6_pass,
        "CE7_GAP_RISK_6P89KHZ": ce7_pass,
    }
    n_pass = sum(1 for v in verdicts.values() if v)
    success_rule_met = all(verdicts.values())

    # Assemble clean serializable results JSON
    out_json: dict[str, Any] = {
        "experiment": "exp129_valley_orbital_hyperfine",
        "hypothesis_id": "H147",
        "risk_target": "R1",
        "no_lab_measurement": True,
        "epistemic_tags": preds["epistemic_tags"],
        "elapsed_sec": float(time.time() - t0),
        "verdicts": verdicts,
        "verdict_counts": {"passed": n_pass, "failed": len(verdicts) - n_pass, "total": len(verdicts)},
        "success_rule_met": success_rule_met,
        "bare_emt": {k: v for k, v in bare_emt.items() if k != "coeffs"},
        "vokl6_calibration": {k: v for k, v in cal.items() if k != "c_1v"},
        "vokl6_calibration_sensitivities": {
            "equal_eta_186": {k: v for k, v in th["calibration_equal_eta"].items() if k != "c_1v"},
            "assali_eta_178_x_1p4178": {k: v for k, v in th["calibration_assali"].items() if k != "c_1v"},
        },
        "radii_comparison": {
            "KL_legacy_params": {"a_perp_nm": 2.5, "a_par_nm": 1.4, "anisotropy": 2.5 / 1.4},
            "EMT_bare": th["radii_emt"],
            "VOKL6_1s_A1": th["radii_vokl6"],
        },
        "epm_verification": th["epm"],
        "kbloch_quadrature": th["kbloch_diag"],
        "shell_benchmarks": {
            "targets": vt.BENCHMARK_SHELLS,
            "models": th["benchmarks"],
            "legacy_repo_references": {
                "Exp56_KL_3param_fit": {"R111": 0.1543, "R331": 0.2265, "err_R111": 0.6773, "err_R331": 0.2270, "note": "Unphysical a=1.2<b=2.5"},
                "Exp60_EXT_DIAG_posthoc": {"R111": 0.0940, "R331": 0.2833, "err_R111": 0.0218, "err_R331": 0.0332, "note": "Unphysical k0=0.789, a=4.0"},
                "Exp69_Grid_EMT": {"R111": 0.1045, "R331": 0.1499, "err_R111": 0.1359, "err_R331": 0.4885, "note": "E=-28.75 meV unconverged"},
                "Exp75_SingleK0_Bloch": {"R111": 0.1047, "R331": 0.1493, "err_R111": 0.1383, "err_R331": 0.4905, "note": "q=1.000 by {C4z|tau} symmetry"},
            },
        },
        "atlas_45214_audit": {
            "max_abs_trace_T_dip_ext_Hz": atlas["max_abs_trace_T_dip_ext_Hz"],
            "max_abs_trace_T_dip_pt_Hz": atlas["max_abs_trace_T_dip_pt_Hz"],
            "VOKL6_norm_ext_vs_KL": atlas_cmp_ext,
            "VOKL6_HM5962_ext_vs_KL": atlas_cmp_hm,
            "VOKL6_abinit_ext_vs_KL": atlas_cmp_abinit,
        },
        "exp59_62_portable_audit": audit59,
        "mode_b_yield_n400": mode_b_full,
        "machine_impact_R1": {
            "yield_shifts_VOKL6_norm_minus_KL": yield_shifts_norm,
            "yield_shifts_VOKL6_HM5962_minus_KL": yield_shifts_hm5962,
            "yield_shifts_VOKL6_abinit_minus_KL": yield_shifts_abinit,
            "max_abs_yield_shift_norm": max_abs_shift_norm,
            "max_abs_yield_shift_hm5962": max_abs_shift_hm5962,
            "max_abs_yield_shift_abinit": max_abs_shift_abinit,
            "legacy_exp60_ext_diag_f0p5_shift": +0.43,
            "ddrf_6p89kHz_risk_F1": {
                "KL_legacy_frac_lt_6893Hz": mode_b_full["KL_legacy"]["F1"]["gap_stats"]["frac_lt_6893Hz"],
                "VOKL6_norm_ext_frac_lt_6893Hz": f1_vk_gs["frac_lt_6893Hz"],
                "VOKL6_HM5962_ext_frac_lt_6893Hz": mode_b_full["VOKL6_HM5962_ext"]["F1"]["gap_stats"]["frac_lt_6893Hz"],
                "VOKL6_abinit_ext_frac_lt_6893Hz": mode_b_full["VOKL6_abinit_ext"]["F1"]["gap_stats"]["frac_lt_6893Hz"],
                "KL_legacy_median_gap_Hz": mode_b_full["KL_legacy"]["F1"]["gap_stats"]["median_Hz"],
                "VOKL6_norm_ext_median_gap_Hz": f1_vk_gs["median_Hz"],
                "VOKL6_HM5962_ext_median_gap_Hz": mode_b_full["VOKL6_HM5962_ext"]["F1"]["gap_stats"]["median_Hz"],
                "VOKL6_abinit_ext_median_gap_Hz": mode_b_full["VOKL6_abinit_ext"]["F1"]["gap_stats"]["median_Hz"],
            },
        },
    }

    (OUT_DIR / "exp129.json").write_text(json.dumps(out_json, indent=2), encoding="utf-8")

    # Lightweight plot payload for PyCairo script (runs on /usr/bin/python3)
    plot_payload = {
        "calibration": out_json["vokl6_calibration"],
        "bare_emt": out_json["bare_emt"],
        "radii": out_json["radii_comparison"],
        "profiles": th["profiles"],
        "benchmarks": {
            "targets": vt.BENCHMARK_SHELLS,
            "KL_legacy": th["benchmarks"]["KL_legacy"],
            "EMT_bare_k085": th["benchmarks"]["EMT_bare_k085"],
            "VOKL6_envelope_only": th["benchmarks"]["VOKL6_envelope_only"],
            "VOKL6_full_k085": th["benchmarks"]["VOKL6_full_k085"],
        },
        "mode_b_yield_n400": mode_b_full,
        "gap_cdfs": gap_cdfs_for_plot,
        "radial_breakdown": atlas_cmp_ext["radial_shell_breakdown"],
        "verdicts": verdicts,
    }
    (OUT_DIR / "plot_data_exp129.json").write_text(json.dumps(plot_payload, indent=1), encoding="utf-8")

    print("\n================ EXP129 SUMMARY VERDICTS ================", flush=True)
    for k, v in verdicts.items():
        print(f"  {k:28s}: {'PASS' if v else 'FAIL'}", flush=True)
    print(f"Total passed: {n_pass}/{len(verdicts)} | success_rule_met={success_rule_met} | elapsed={time.time()-t0:.2f} s", flush=True)


if __name__ == "__main__":
    main()
