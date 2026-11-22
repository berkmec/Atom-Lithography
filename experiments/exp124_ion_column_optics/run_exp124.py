"""Exp124 main runner: Ion Column Optics, 5 keV Retarding Closure & 3D Anisotropic Yield.

Run with:
    python3 -B experiments/exp124_ion_column_optics/run_exp124.py
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np

from column_physics import (
    ROOT,
    audit_historical_chain,
    boersch_and_coulomb,
    build_and_solve_lens_architectures,
    build_cad_column_dimensions,
    evaluate_spot_budget,
    hda_energy_filter,
    optimize_alpha_land,
    wien_mass_filter,
)
from anisotropic_yield import run_all_anisotropic_yields

OUT_DIR = ROOT / "results" / "exp124_ion_column_optics"


def main() -> None:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pred_path = OUT_DIR / "predictions_exp124.json"
    predictions = json.loads(pred_path.read_text(encoding="utf-8"))

    print("[Exp124] 1. Auditing historical chain (Exp66..Exp105) & Liouville deficit...", flush=True)
    hist_audit = audit_historical_chain(ROOT)
    print(f"  max_anchor_rel_err={hist_audit['max_anchor_rel_err']:.3e} | "
          f"attack91 deficit={hist_audit['liouville_audit_attack91']['brightness_deficit_factor_at_5keV_10mrad']:.3f}x",
          flush=True)

    print("[Exp124] 2. Solving 2D axisymmetric Laplace & ray-tracing lens architectures...", flush=True)
    lens_pkg = build_and_solve_lens_architectures()
    archs = lens_pkg["architectures"]
    for name, tr in archs.items():
        print(f"  {name:24s}: WD={tr['working_distance_mm']:.3f}mm f={tr['f_img_mm']:.3f}mm "
              f"Cc={tr['Cc_scherzer_mm']:.3f}mm (ray {tr['Cc_raytrace_mm']:.3f}, diff {tr['Cc_scherzer_vs_raytrace_rel_diff']*100:.2f}%) "
              f"Cs={tr['Cs_scherzer_mm']:.3f}mm (mult {tr['Cs_nonparaxial_mm']:.3f}, diff {tr['Cs_scherzer_vs_multipole_rel_diff']*100:.2f}%) "
              f"E_gap={tr['E_gap_nom_MV_m']:.2f} MV/m W_drift={tr['wronskian_rel_drift']:.2e}", flush=True)

    print("[Exp124] 3. Evaluating Wien filter, HDA energy filter, Boersch/Coulomb...", flush=True)
    wien_10 = wien_mass_filter(E_ext_eV=10000.0, B_T=0.45, L_w_mm=80.0, L_drift_mm=70.0, gap_mm=12.0, slit_mm=0.20)
    wien_15 = wien_mass_filter(E_ext_eV=15000.0, B_T=0.55, L_w_mm=80.0, L_drift_mm=70.0, gap_mm=12.0, slit_mm=0.20)
    hda_2eV = hda_energy_filter(E_pass_eV=200.0, R0_mm=40.0, slit_mm=0.70, alpha_in_mrad=30.0, dE_src_fwhm_eV=6.0)
    hda_hires = hda_energy_filter(E_pass_eV=100.0, R0_mm=40.0, slit_mm=0.35, alpha_in_mrad=25.0, dE_src_fwhm_eV=6.0)
    hda = hda_hires
    coul_5 = boersch_and_coulomb(E_col_eV=5000.0, I_flood_A=50e-9, L_col_m=0.35, r_beam_m=2.0e-3)
    coul_10 = boersch_and_coulomb(E_col_eV=10000.0, I_flood_A=50e-9, L_col_m=0.35, r_beam_m=2.0e-3)
    coul_15 = boersch_and_coulomb(E_col_eV=15000.0, I_flood_A=50e-9, L_col_m=0.35, r_beam_m=2.0e-3)
    coul_ratio_10_vs_5 = coul_5["dr_sc_laminar_um"] / coul_10["dr_sc_laminar_um"]
    coul_ratio_15_vs_5 = coul_5["dr_sc_laminar_um"] / coul_15["dr_sc_laminar_um"]
    coul_holts_10_vs_5 = coul_5["dr_holtsmark_flood_um"] / coul_10["dr_holtsmark_flood_um"]
    coul_holts_15_vs_5 = coul_5["dr_holtsmark_flood_um"] / coul_15["dr_holtsmark_flood_um"]

    print(f"  Wien 10 keV: dx(32PH+)={wien_10['dx_32PH_mm']:.3f} mm ({wien_10['separation_over_slit']:.2f}x slit), R_m={wien_10['mass_resolving_power']:.1f}")
    print(f"  HDA-2eV: dE={hda_2eV['dE_fwhm_eV']:.3f} eV, tau={hda_2eV['tau_gaussian_exact']:.3f} | "
          f"HDA-HiRes: dE={hda_hires['dE_fwhm_eV']:.3f} eV, tau={hda_hires['tau_gaussian_exact']:.3f}")
    print(f"  Coulomb suppression: laminar 10/5={coul_ratio_10_vs_5:.2f}x, 15/5={coul_ratio_15_vs_5:.2f}x; "
          f"Holtsmark 10/5={coul_holts_10_vs_5:.2f}x, 15/5={coul_holts_15_vs_5:.2f}x; "
          f"N_bar_beamlet={coul_10['single_beamlet_Nbar_col']:.2e}", flush=True)

    print("[Exp124] 4. Optimizing Liouville-consistent 5 keV operating windows...", flush=True)
    tr_b = archs["Arch-B_0p5mm_immersion"]
    tr_b15 = archs["Arch-B15_15to5keV"]
    tr_c = archs["Arch-C_32um_2stage"]
    tr_d = archs["Arch-D_MEMS_microgap35"]
    dE_hi = hda_hires["dE_fwhm_eV"]
    tau_hi = hda_hires["tau_gaussian_exact"]
    dE_2 = hda_2eV["dE_fwhm_eV"]
    tau_2 = hda_2eV["tau_gaussian_exact"]
    sigma_coul_10 = coul_10["sigma_coul_wafer_nm"]

    # Operating-point matrix: honestly compares naive 2 eV/1 ms vs real HDA-HiRes (0.453 eV) + write headroom & LMIS
    op_points = {}
    op_specs = [
        # (key, arch_trace, dE, J_src, Ti, tau_f, tau_shot, note)
        ("ArchB_naive_2eV_Ti1_1ms",     tr_b,   2.0,   100.0, 1.0,  0.25,   1.0,  "Exp82/91 params on real 10.6 MV/m lens -> FAILS (Cc=2.61 mm + Liouville)"),
        ("ArchB_HiRes_Ti1_1ms",         tr_b,   dE_hi, 100.0, 1.0,  tau_hi, 1.0,  "HDA 0.453 eV, conservative Ti=1.0 eV, 1 ms"),
        ("ArchB_HiRes_Ti0p5_15ms",      tr_b,   dE_hi, 100.0, 0.5,  tau_hi, 15.0, "CANONICAL GOLDEN: 10.6 MV/m, HDA 0.453 eV, Ti=0.5 eV, 15 ms (1024 beamlets: 2.95e9 shots/day = 15x readout ceiling)"),
        ("ArchB_HiRes_Ti0p25_10ms",     tr_b,   dE_hi, 100.0, 0.25, tau_hi, 10.0, "10.6 MV/m, HDA 0.453 eV, Ti=0.25 eV, 10 ms (1024 beamlets: 4.42e9 shots/day = 22x readout ceiling)"),
        ("ArchB_HiRes_Ti1_25ms",        tr_b,   dE_hi, 100.0, 1.0,  tau_hi, 25.0, "10.6 MV/m, HDA 0.453 eV, conservative Ti=1.0 eV, 25 ms (1024 beamlets: 1.77e9 shots/day = 9x readout ceiling)"),
        ("ArchB_HiRes_LMIS_1ms",        tr_b,   dE_hi, 1000.0, 0.25, tau_hi, 1.0, "10.6 MV/m + 10x brighter LMIS/cold-ion upgrade at 1.0 ms"),
        ("ArchB15_HiRes_Ti0p5_15ms",    tr_b15, dE_hi, 100.0, 0.5,  tau_hi, 15.0, "15->5 keV immersion (11.1 MV/m, WD=0.48 mm), Ti=0.5 eV, 15 ms"),
        ("ArchC_32um_HiRes_Ti0p5_15ms", tr_c,   dE_hi, 100.0, 0.5,  tau_hi, 15.0, "32 um 2-stage (9.8 MV/m) -> Cs=57.7 mm wall hurts spot!"),
        ("ArchD_MEMS35_HiRes_Ti0p5_5ms",tr_d,   dE_hi, 100.0, 0.5,  tau_hi, 5.0,  "MEMS micro-gap 35 MV/m (Cc=1.19 mm), Ti=0.5 eV, 5 ms"),
    ]
    for key, tr, dE, Jsrc, Ti, tf, tshot, note in op_specs:
        opt = optimize_alpha_land(
            5.0, tr["Cc_scherzer_mm"], tr["Cs_scherzer_mm"],
            dE_fwhm_eV=dE, J_src_A_m2=Jsrc, Ti_eV=Ti, tau_filter=tf, tau_shot_ms=tshot,
            sigma_coul_nm=sigma_coul_10,
        )
        opt["arch"] = tr["name"]
        opt["E_gap_nom_MV_m"] = tr["E_gap_nom_MV_m"]
        opt["working_distance_mm"] = tr["working_distance_mm"]
        opt["note"] = note
        op_points[key] = opt
        print(f"  {key:30s}: alpha={opt['alpha_land_mrad']:5.2f} mrad | "
              f"geom={opt['sigma_geom_nm']:.2f} chrom={opt['sigma_c_nm']:.2f} sph={opt['sigma_s_nm']:.2f} -> "
              f"spot={opt['sigma_spot_nm']:.3f} nm | tot={opt['sigma_total_nm']:.3f} nm | eta={opt['eta_ibic']:.4f}",
              flush=True)

    # Energy landing sweep (3..10 keV)
    energy_sweep = {}
    for E_land in (3.0, 4.0, 5.0, 6.0, 7.5, 10.0):
        energy_sweep[f"E{E_land:g}"] = {
            "ArchB_canonical": optimize_alpha_land(
                E_land, tr_b["Cc_scherzer_mm"], tr_b["Cs_scherzer_mm"],
                dE_fwhm_eV=dE_hi, Ti_eV=0.5, tau_filter=tau_hi, tau_shot_ms=15.0,
                sigma_coul_nm=sigma_coul_10,
            ),
            "ArchB_Ti1_25ms": optimize_alpha_land(
                E_land, tr_b["Cc_scherzer_mm"], tr_b["Cs_scherzer_mm"],
                dE_fwhm_eV=dE_hi, Ti_eV=1.0, tau_filter=tau_hi, tau_shot_ms=25.0,
                sigma_coul_nm=sigma_coul_10,
            ),
            "ArchB_naive_2eV_1ms": optimize_alpha_land(
                E_land, tr_b["Cc_scherzer_mm"], tr_b["Cs_scherzer_mm"],
                dE_fwhm_eV=2.0, Ti_eV=1.0, tau_filter=0.25, tau_shot_ms=1.0,
                sigma_coul_nm=sigma_coul_10,
            ),
        }

    # Alpha curves at E_land=5 keV for plotting (3..20 mrad)
    alpha_grid = np.linspace(3.0, 20.0, 171)
    alpha_curves = {
        "alpha_mrad": [float(a) for a in alpha_grid],
        "ArchB_naive_2eV_1ms": [
            evaluate_spot_budget(5.0, tr_b["Cc_scherzer_mm"], tr_b["Cs_scherzer_mm"], float(a),
                                 dE_fwhm_eV=2.0, Ti_eV=1.0, tau_filter=0.25, tau_shot_ms=1.0,
                                 sigma_coul_nm=sigma_coul_10)
            for a in alpha_grid
        ],
        "ArchB_canonical": [
            evaluate_spot_budget(5.0, tr_b["Cc_scherzer_mm"], tr_b["Cs_scherzer_mm"], float(a),
                                 dE_fwhm_eV=dE_hi, Ti_eV=0.5, tau_filter=tau_hi, tau_shot_ms=15.0,
                                 sigma_coul_nm=sigma_coul_10)
            for a in alpha_grid
        ],
        "ArchB_Ti1_25ms": [
            evaluate_spot_budget(5.0, tr_b["Cc_scherzer_mm"], tr_b["Cs_scherzer_mm"], float(a),
                                 dE_fwhm_eV=dE_hi, Ti_eV=1.0, tau_filter=tau_hi, tau_shot_ms=25.0,
                                 sigma_coul_nm=sigma_coul_10)
            for a in alpha_grid
        ],
    }

    canon_key = "ArchB_HiRes_Ti0p5_15ms"
    sigma_exp124 = op_points[canon_key]["sigma_total_nm"]

    print(f"[Exp124] 5. Building CAD v3.0 column dimensions (canonical={canon_key}, sigma_tot={sigma_exp124:.3f} nm)...", flush=True)
    cad_dims = build_cad_column_dimensions(tr_b, tr_c, wien_10, hda, wafer_top_z_cad_mm=500.0, uhv_chamber_inner_r_mm=182.0)

    print("[Exp124] 6. Running portable Exp57/105 audit & 3D anisotropic BCA/Holmes/surface/donor yields...", flush=True)
    t_y0 = time.time()
    yield_cells = run_all_anisotropic_yields(sigma_exp124_nm=sigma_exp124, reals=400)
    t_y = time.time() - t_y0
    for k, c in yield_cells.items():
        print(f"  {k:30s}: Y={c['yield_frac']:.4f} ({c['successes']:3d}/{c['realizations']}) "
              f"sig3D={c['sigma_geom_3d_nm']:.2f} surf_lost={c['lost_surface_frac_mean']*100:4.1f}% "
              f"d_back={c['donor_backscatter_frac']*100:4.1f}% elig_med={c['eligible_median']:.1f}",
              flush=True)
    print(f"  Anisotropic yield suite finished in {t_y:.1f}s.", flush=True)

    # ------------------------------------------------------------------
    # Evaluate pre-registered predictions CD1..CD8 verbatim!
    # ------------------------------------------------------------------
    cd1_pass = bool(
        hist_audit["max_anchor_rel_err"] < 1e-4
        and hist_audit["liouville_audit_attack91"]["brightness_deficit_factor_at_5keV_10mrad"] > 1.7
    )
    cd2_pass = bool(
        tr_b["wronskian_rel_drift"] < 1e-6
        and tr_c["wronskian_rel_drift"] < 1e-6
        and tr_b["Cc_scherzer_vs_raytrace_rel_diff"] < 0.05
        and tr_c["Cc_scherzer_vs_raytrace_rel_diff"] < 0.05
    )
    tr_a1 = archs["Arch-A1_32um_shortWD"]
    tr_a2 = archs["Arch-A2_32um_longWD"]
    cd3_pass = bool(
        tr_a1["E_gap_nom_MV_m"] > 15.0
        and tr_a2["Cs_scherzer_mm"] > 50.0
        and tr_b["E_gap_nom_MV_m"] <= 12.0 and tr_b["Cc_scherzer_mm"] <= 0.50
        and tr_c["E_gap_nom_MV_m"] <= 12.0 and tr_c["Cc_scherzer_mm"] <= 0.50
    )
    passing_ops = [
        k for k, v in op_points.items()
        if v["E_gap_nom_MV_m"] <= 12.0
        and v["sigma_spot_nm"] <= 1.50
        and v["sigma_total_nm"] <= 3.80
        and v["eta_ibic"] >= 0.99
    ]
    cd4_pass = bool(
        len(passing_ops) >= 1
        and wien_10["separation_over_slit"] >= 3.0
        and hda["dE_fwhm_eV"] <= 2.0
    )
    cd5_pass = bool(
        coul_ratio_10_vs_5 >= 2.5
        and coul_10["single_beamlet_Nbar_col"] < 0.01
    )
    cd6_pass = bool(
        yield_cells["AUDIT_EXP57_S5_N1024"]["successes"] == 49
        and yield_cells["AUDIT_EXP105_ISO3p8_N1024"]["successes"] == 277
    )
    y_iso = yield_cells["AUDIT_EXP105_ISO3p8_N1024"]["yield_frac"]
    y_bca_pure = yield_cells["ANISO_BCA_PURE_N1024"]["yield_frac"]
    y_p91_bca = yield_cells["ANISO_P91_BCA_N1024"]["yield_frac"]
    y_p91_holmes = yield_cells["ANISO_P91_HOLMES_N1024"]["yield_frac"]
    y_p91_bca_donor = yield_cells["ANISO_P91_BCA_DONOR_N1024"]["yield_frac"]

    cd7_pass = bool(
        0.74 <= y_bca_pure <= 0.88
        and y_p91_bca > 0.70
        and y_p91_holmes < 0.65
    )
    cd8_pass = bool((y_p91_bca - y_p91_bca_donor) >= 0.15)

    verdicts = {
        "CD1_audit_and_liouville_deficit": cd1_pass,
        "CD2_laplace_raytrace_verification": cd2_pass,
        "CD3_pitch_breakdown_vs_viable_lens": cd3_pass,
        "CD4_liouville_closed_5keV_window": cd4_pass,
        "CD5_boersch_coulomb_suppression": cd5_pass,
        "CD6_yield_engine_exact_audit": cd6_pass,
        "CD7_anisotropic_bca_vs_holmes_split": cd7_pass,
        "CD8_stochastic_donor_straggle_penalty": cd8_pass,
    }
    success_rule_met = bool(cd1_pass and cd2_pass and cd3_pass and cd4_pass and cd6_pass)

    # Throughput implications (Mode A 1000 beamlets x 1000 channels, 1 ms/shot, 1 s/spec, 50% duty)
    def mode_a_prod_per_day(cell: dict[str, Any], nb: int = 1000, ns: int = 1000, tau_shot_ms: float = 1.0) -> float:
        w = nb / (cell["exp_shots_per_register"] * tau_shot_ms * 1e-3) * 86400.0
        m = ns / (cell["exp_specs_per_register"] * 1.0) * 86400.0
        return 0.5 * min(w, m)

    production_summary = {
        k: {
            "yield_frac": yield_cells[k]["yield_frac"],
            "delta_vs_exp105_iso": yield_cells[k]["yield_frac"] - y_iso,
            "t_eff_s": yield_cells[k]["exp_specs_per_register"],
            "certified_per_day_1000x1000_1ms": mode_a_prod_per_day(yield_cells[k], 1000, 1000, 1.0),
            "certified_per_day_1024x1000_10ms": mode_a_prod_per_day(yield_cells[k], 1024, 1000, 10.0),
            "certified_per_day_1024x1000_15ms": mode_a_prod_per_day(yield_cells[k], 1024, 1000, 15.0),
        }
        for k in (
            "AUDIT_EXP105_ISO3p8_N1024",
            "ANISO_BCA_PURE_N1024",
            "ANISO_P91_BCA_N1024",
            "ANISO_EXP124_BCA_N1024",
            "ANISO_BCA_HOLMES_N1024",
            "ANISO_P91_HOLMES_N1024",
            "ANISO_P91_BCA_DONOR_N1024",
            "ANISO_EXP124_BCA_DONOR_N1024",
            "ANISO_P91_HOLMES_DONOR_N1024",
        )
    }

    # Save main JSON
    out = {
        "experiment": "exp124_ion_column_optics",
        "no_lab_measurement": True,
        "epistemic_tags": ["Model", "Analitik", "Sayısal-Simülasyon", "Literatür"],
        "predictions": predictions,
        "verdicts": verdicts,
        "success_rule_met": success_rule_met,
        "canonical_operating_point": canon_key,
        "passing_5keV_operating_points": passing_ops,
        "historical_chain_audit": hist_audit,
        "lens_architectures": archs,
        "wien_mass_filter": {"E10keV": wien_10, "E15keV": wien_15},
        "hda_energy_filter": {"HDA_2eV": hda_2eV, "HDA_HiRes_0p45eV": hda_hires},
        "boersch_coulomb": {
            "E5keV": coul_5,
            "E10keV": coul_10,
            "E15keV": coul_15,
            "suppression_laminar_10_vs_5": coul_ratio_10_vs_5,
            "suppression_laminar_15_vs_5": coul_ratio_15_vs_5,
            "suppression_holtsmark_10_vs_5": coul_holts_10_vs_5,
            "suppression_holtsmark_15_vs_5": coul_holts_15_vs_5,
        },
        "operating_points_5keV": op_points,
        "energy_sweep": energy_sweep,
        "cad_column_dimensions_mm": cad_dims,
        "anisotropic_yield_cells": yield_cells,
        "production_summary": production_summary,
        "elapsed_sec": round(time.time() - t0, 2),
    }

    (OUT_DIR / "exp124.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    # Save lightweight plot payload for /usr/bin/python3 (PyCairo + PIL)
    cfg_b, sol_b, _ = lens_pkg["solutions_for_plot"]["Arch-B"]
    cfg_c, sol_c, _ = lens_pkg["solutions_for_plot"]["Arch-C"]
    # Downsample axial potential for crisp curves
    plot_payload = {
        "alpha_curves": alpha_curves,
        "energy_sweep": energy_sweep,
        "op_points": op_points,
        "lens_profiles": {
            "ArchB": {
                "z_mm": [float(x) for x in sol_b["z_mm"][::4]],
                "phi0_kV": [float(x / 1000.0) for x in sol_b["phi"][0, ::4]],
                "Ez_MV_m": [float(x) for x in (np.abs(np.gradient(sol_b["phi"][0, :], sol_b["z_mm"][1] - sol_b["z_mm"][0])) / 1000.0)[::4]],
                "Cc_mm": tr_b["Cc_scherzer_mm"],
                "Cs_mm": tr_b["Cs_scherzer_mm"],
                "WD_mm": tr_b["working_distance_mm"],
                "E_gap_MV_m": tr_b["E_gap_nom_MV_m"],
            },
            "ArchC": {
                "z_mm": [float(x) for x in sol_c["z_mm"][::4]],
                "phi0_kV": [float(x / 1000.0) for x in sol_c["phi"][0, ::4]],
                "Cc_mm": tr_c["Cc_scherzer_mm"],
                "Cs_mm": tr_c["Cs_scherzer_mm"],
                "WD_mm": tr_c["working_distance_mm"],
                "E_gap_MV_m": tr_c["E_gap_nom_MV_m"],
            },
        },
        "yield_cells": yield_cells,
        "verdicts": verdicts,
        "success_rule_met": success_rule_met,
    }
    (OUT_DIR / "plot_data_exp124.json").write_text(json.dumps(plot_payload, indent=1), encoding="utf-8")

    print("\n=== EXP124 SUMMARY VERDICTS ===")
    for k, v in verdicts.items():
        print(f"  {k:40s}: {'PASS' if v else 'FAIL'}")
    print(f"  SUCCESS_RULE_MET = {success_rule_met} | passing_5keV_ops = {passing_ops}")
    print(f"  Total elapsed = {out['elapsed_sec']} s")


if __name__ == "__main__":
    main()
