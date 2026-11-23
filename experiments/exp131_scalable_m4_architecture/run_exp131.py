"""Master runner for Exp131: M4 Scalable Architecture Theory (H149).

Executes:
  Part 1: Exact 4x4 Tosi donor-interface flip-flop Hamiltonian & Exp124 3D straggle
          capping + local DC sweet-spot tuning sweep (N = 2000 donors/cap).
  Part 2: Exact 12x12 Lindblad open-quantum-system cavity-QED bus simulation
          (50 Ohm vs 3 kOhm wall, 4D Z_r x Q_L x S_eps phase map, capping sweep,
          and full 4-basis universal CZ average gate fidelity).
  Part 3: 2D Surface-Code (Square L=5, 11, 21) vs Heavy-Hex (d=3, 5, 7) site
          percolation & candidate-slot redundancy Monte Carlo (N_mc = 2000).
  Part 4: Concrete CAD v4.0 & BOM M4 NbTiN bus electromagnetic & layout geometry.
  Part 5: Transparent evaluation of pre-registered predictions CM1-CM7.

Epistemic scope: {Model} / {Sayisal-Simulasyon} / {Literatur}. no_lab_measurement=true.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Portable repo-root resolution (no hardcoded home paths)
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.exp131_scalable_m4_architecture.flipflop_cell131 import (
    run_capping_and_tuning_sweep,
)
from experiments.exp131_scalable_m4_architecture.lindblad_bus131 import (
    run_lindblad_bus_study,
)
from experiments.exp131_scalable_m4_architecture.percolation131 import (
    run_percolation_and_geometry_study,
)

RESULTS_DIR = REPO_ROOT / "results" / "exp131_scalable_m4_architecture"
PREDICTIONS_PATH = RESULTS_DIR / "predictions_exp131.json"
OUTPUT_JSON_PATH = RESULTS_DIR / "exp131.json"


def evaluate_predictions(
    preds_doc: dict[str, Any],
    part1: dict[str, Any],
    part2: dict[str, Any],
    part3: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate pre-registered CM1-CM7 strictly against predictions_exp131.json."""
    preds = preds_doc["predictions"]
    verdicts: dict[str, Any] = {}

    # CM1: capping window and sweet-spot gain
    t1 = preds["CM1_capping_window_and_sweetspot_gain"]["thresholds"]
    uncapped = next(d for d in part1["sweep"] if abs(d["delta_z_cap_nm"] - 0.0) < 1e-6)
    opt = part1["optimal_capping"]
    dz_opt = opt["delta_z_cap_nm"]
    gain_eff = opt["median_C_gain_vs_eps0"]
    cm1_pass = (
        uncapped["yield_C_ge_100_tuned"] < t1["max_uncapped_yield_C100"]
        and 6.0 <= dz_opt <= 10.0
        and opt["yield_C_ge_100_tuned"] >= t1["min_capped_tuned_yield_C100"]
        and gain_eff >= t1["min_tuning_coop_gain"]
    )
    verdicts["CM1_capping_window_and_sweetspot_gain"] = {
        "verdict": "PASS" if cm1_pass else "FAIL",
        "measured": {
            "uncapped_yield_C100": uncapped["yield_C_ge_100_tuned"],
            "optimal_delta_z_cap_nm": dz_opt,
            "optimal_yield_C100_tuned": opt["yield_C_ge_100_tuned"],
            "optimal_yield_C100_fixed_eps0": opt["yield_C_ge_100_fixed_eps0"],
            "optimal_median_C_tuned": opt["median_C_tuned"],
            "optimal_median_C_fixed_eps0": opt["median_C_fixed_eps0"],
            "median_C_gain_vs_eps0": gain_eff,
            "conditional_C_gain_vs_eps0": opt["conditional_C_gain_vs_eps0"],
        },
        "thresholds": t1,
    }

    # CM2: high impedance vs 50 Ohm wall
    t2 = preds["CM2_high_impedance_vs_50ohm_wall"]["thresholds"]
    f_50 = part2["impedance_wall_comparison"]["cpw_50ohm"]["mean_F_bell"]
    f_3k = part2["impedance_wall_comparison"]["nbtin_3kohm"]["mean_F_bell"]
    tr_err = part2["cptp_audit"]["max_trace_err"]
    hm_err = part2["cptp_audit"]["max_hermiticity_err"]
    cm2_pass = (
        f_50 < t2["max_50ohm_bell_fidelity"]
        and f_3k >= t2["min_3kohm_bell_fidelity"]
        and max(tr_err, hm_err) < t2["max_lindblad_trace_err"]
    )
    verdicts["CM2_high_impedance_vs_50ohm_wall"] = {
        "verdict": "PASS" if cm2_pass else "FAIL",
        "measured": {
            "mean_F_bell_50ohm": f_50,
            "mean_F_bell_3kohm": f_3k,
            "unselected_Ncand1_mean_F_bell_3kohm": part2["impedance_wall_comparison"]["unselected_Ncand1_baseline"]["nbtin_3kohm_mean_F_bell"],
            "unselected_Ncand1_mean_F_bell_50ohm": part2["impedance_wall_comparison"]["unselected_Ncand1_baseline"]["cpw_50ohm_mean_F_bell"],
            "max_trace_err": tr_err,
            "max_hermiticity_err": hm_err,
            "min_eigenvalue": part2["cptp_audit"]["min_eigenvalue"],
        },
        "thresholds": t2,
    }

    # CM3: surface code threshold envelope
    t3 = preds["CM3_surface_code_threshold_envelope"]["thresholds"]
    pm_pts = part2["phase_map_4d"]["points"]
    corner_pts = [
        p for p in pm_pts
        if p["z_r_ohm"] >= 3000.0 and p["q_l"] >= 2e5 and p["s_eps_uev"] <= 0.5
    ]
    best_corner = max(corner_pts, key=lambda p: p["mean_F_bell"])
    fail_pt = next(
        p for p in pm_pts
        if abs(p["z_r_ohm"] - 3000.0) < 1e-6 and abs(p["q_l"] - 5e4) < 1e-3 and abs(p["s_eps_uev"] - 5.0) < 1e-6
    )
    cm3_pass = (
        best_corner["mean_F_bell"] >= t3["min_corner_surface_code_fidelity"]
        and fail_pt["mean_F_bell"] < t3["max_high_noise_low_Q_fidelity"]
    )
    verdicts["CM3_surface_code_threshold_envelope"] = {
        "verdict": "PASS" if cm3_pass else "FAIL",
        "measured": {
            "best_low_noise_corner": {
                "z_r_ohm": best_corner["z_r_ohm"],
                "q_l": best_corner["q_l"],
                "s_eps_uev": best_corner["s_eps_uev"],
                "mean_F_bell": best_corner["mean_F_bell"],
            },
            "high_noise_low_Q_point": {
                "z_r_ohm": fail_pt["z_r_ohm"],
                "q_l": fail_pt["q_l"],
                "s_eps_uev": fail_pt["s_eps_uev"],
                "mean_F_bell": fail_pt["mean_F_bell"],
            },
        },
        "thresholds": t3,
    }

    # CM4: CZ vs Bell gate overhead at nominal M4
    t4 = preds["CM4_cz_vs_bell_gate_overhead"]["thresholds"]
    cz_nom = part2["universal_cz_gate"]["nominal_3kohm_Q2e5_S1"]
    f_cz_nom = cz_nom["mean_F_avg_cz"]
    cm4_pass = f_cz_nom >= t4["min_nominal_cz_fidelity"] and f_cz_nom < f_3k
    verdicts["CM4_cz_vs_bell_gate_overhead"] = {
        "verdict": "PASS" if cm4_pass else "FAIL",
        "measured": {
            "mean_F_avg_cz_nominal": f_cz_nom,
            "median_F_avg_cz_nominal": cz_nom["median_F_avg_cz"],
            "mean_F_cz_bell_state_nominal": cz_nom["mean_F_cz_bell_state"],
            "mean_F_bell_disp_single_step": cz_nom["mean_F_bell_disp_single_step"],
            "mean_F_bell_res_nominal": f_3k,
            "mean_t_cz_us": cz_nom["mean_t_cz_us"],
            "mean_F_avg_cz_low_noise_S0p5": part2["universal_cz_gate"]["low_noise_3kohm_Q2e5_S0p5"]["mean_F_avg_cz"],
        },
        "thresholds": t4,
    }

    # CM5: 2D square percolation & redundancy
    t5 = preds["CM5_2d_square_percolation_and_redundancy"]["thresholds"]
    sq21 = {r["N_cand"]: r for r in part3["square_m4"]["square_L21"]["sweep"]}
    sq11 = {r["N_cand"]: r for r in part3["square_m4"]["square_L11"]["sweep"]}
    sq5 = {r["N_cand"]: r for r in part3["square_m4"]["square_L5"]["sweep"]}
    cm5_pass = (
        sq21[1]["P_perc"] < t5["max_ncand1_perc_L21"]
        and sq21[3]["P_perc"] >= t5["min_ncand3_perc_L21"]
        and sq5[6]["Y_perfect_mc"] >= t5["min_ncand6_perfect_L5"]
        and sq11[6]["Y_FT_5pct_mc"] >= t5["min_ncand6_ft_L11"]
    )
    verdicts["CM5_2d_square_percolation_and_redundancy"] = {
        "verdict": "PASS" if cm5_pass else "FAIL",
        "measured": {
            "p_m4_combined": part3["yield_inputs"]["p_m4_combined"],
            "L21_Ncand1_P_perc": sq21[1]["P_perc"],
            "L21_Ncand3_P_perc": sq21[3]["P_perc"],
            "L5_Ncand6_Y_perfect_mc": sq5[6]["Y_perfect_mc"],
            "L5_Ncand6_Y_perfect_exact": sq5[6]["Y_perfect_exact"],
            "L11_Ncand6_Y_FT_mc": sq11[6]["Y_FT_5pct_mc"],
            "L11_Ncand6_Y_FT_exact": sq11[6]["Y_FT_5pct_exact"],
        },
        "thresholds": t5,
    }

    # CM6: heavy-hex vs square percolation
    t6 = preds["CM6_heavy_hex_vs_square_percolation"]["thresholds"]
    hh7 = {r["N_cand"]: r for r in part3["heavy_hex_m4"]["heavy_hex_d7"]["sweep"]}
    cm6_pass = (
        hh7[2]["P_perc"] < sq11[2]["P_perc"]
        and hh7[4]["P_perc"] >= t6["min_heavy_hex_ncand4_perc"]
    )
    verdicts["CM6_heavy_hex_vs_square_percolation"] = {
        "verdict": "PASS" if cm6_pass else "FAIL",
        "measured": {
            "heavy_hex_d7_n_nodes": part3["heavy_hex_m4"]["heavy_hex_d7"]["n_nodes"],
            "heavy_hex_d7_mean_degree": part3["heavy_hex_m4"]["heavy_hex_d7"]["mean_degree"],
            "heavy_hex_d7_Ncand2_P_perc": hh7[2]["P_perc"],
            "square_L11_Ncand2_P_perc": sq11[2]["P_perc"],
            "heavy_hex_d7_Ncand3_P_perc": hh7[3]["P_perc"],
            "heavy_hex_d7_Ncand4_P_perc": hh7[4]["P_perc"],
            "heavy_hex_d7_Ncand5_P_perc": hh7[5]["P_perc"],
        },
        "thresholds": t6,
    }

    # CM7: CAD M4 bus geometry feasibility
    t7 = preds["CM7_cad_m4_bus_geometry_feasibility"]["thresholds"]
    cad = part3["cad_m4_bus_geometry"]
    cm7_pass = (
        t7["min_L_res_mm"] <= cad["L_res_mm"] <= t7["max_L_res_mm"]
        and cad["inter_node_pitch_um"] <= 20.0
        and 0.15 <= cad["B_M4_T"] <= 0.25
        and cad["B_M4_T"] <= t7["max_B_M4_T"]
    )
    verdicts["CM7_cad_m4_bus_geometry_feasibility"] = {
        "verdict": "PASS" if cm7_pass else "FAIL",
        "measured": {
            "L_res_mm": cad["L_res_mm"],
            "inter_node_pitch_um": cad["inter_node_pitch_um"],
            "B_M4_T": cad["B_M4_T"],
            "B_margin_below_Exp109_pct": cad["B_margin_below_Exp109_pct"],
        },
        "thresholds": t7,
    }

    n_pass = sum(1 for v in verdicts.values() if v["verdict"] == "PASS")
    n_total = len(verdicts)
    return {
        "n_pass": n_pass,
        "n_total": n_total,
        "overall_verdict": "PASS" if n_pass == n_total else "PARTIAL_FAIL",
        "predictions": verdicts,
    }


def main() -> dict[str, Any]:
    t0 = time.perf_counter()
    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError(f"Pre-registered predictions missing: {PREDICTIONS_PATH}")
    preds_doc = json.loads(PREDICTIONS_PATH.read_text(encoding="utf-8"))

    print("[Exp131] Part 1: 4x4 Tosi flip-flop straggle & DC sweet-spot sweep (N=2000/cap)...")
    p1_raw = run_capping_and_tuning_sweep(
        delta_z_caps_nm=[0.0, 4.0, 6.0, 8.0, 10.0, 12.0],
        n_donors=2000,
        z_r_ohm=3000.0,
        q_l=2e5,
        s_eps_uev=1.0,
        f_r_ghz=5.0,
        seed=13101,
    )
    dz_opt = p1_raw["optimal_capping"]["delta_z_cap_nm"]
    p_ff_opt = p1_raw["optimal_capping"]["yield_C_ge_100_tuned"]
    print(f"  -> Optimal Delta_z_cap* = {dz_opt:.1f} nm, p_ff(C>=100) = {p_ff_opt:.4f}, "
          f"med_C = {p1_raw['optimal_capping']['median_C_tuned']:.1f}")

    print("[Exp131] Part 2: Exact 12x12 Lindblad bus simulation (50 Ohm vs 3 kOhm, 4D map, CZ)...")
    part2 = run_lindblad_bus_study(
        optimal_cells_3k=p1_raw["ensembles"][dz_opt],
        capping_ensembles_3k=p1_raw["ensembles"],
        delta_z_opt_nm=dz_opt,
        f_r_ghz=5.0,
        temp_mk=20.0,
        seed=13102,
    )
    print(f"  -> Device: {part2['device_used']} | 50 Ohm F_bell={part2['impedance_wall_comparison']['cpw_50ohm']['mean_F_bell']:.4f} "
          f"vs 3 kOhm F_bell={part2['impedance_wall_comparison']['nbtin_3kohm']['mean_F_bell']:.4f} | "
          f"CZ F_avg={part2['universal_cz_gate']['nominal_3kohm_Q2e5_S1']['mean_F_avg_cz']:.4f}")

    print("[Exp131] Part 3 & 4: 2D Square vs Heavy-Hex percolation (N_mc=2000) & CAD M4 geometry...")
    part3 = run_percolation_and_geometry_study(
        p_ff_opt=p_ff_opt,
        delta_z_cap_opt_nm=dz_opt,
        n_mc=2000,
        seed=13103,
    )

    # Strip non-JSON CellResult objects from part1 before serialization
    part1_serializable = {k: v for k, v in p1_raw.items() if k != "ensembles"}
    # Save compact sample of optimal-capping donor metrics (first 200 certified) for plotting histograms
    opt_sample = p1_raw["ensembles"][dz_opt][:200]
    part1_serializable["optimal_certified_sample"] = {
        "n_sample": len(opt_sample),
        "g_eff_mhz": [c.g_eff_mhz for c in opt_sample],
        "gamma_phi_khz": [c.gamma_phi_khz for c in opt_sample],
        "cooperativity": [c.cooperativity for c in opt_sample],
        "eps_ghz": [c.eps_ghz for c in opt_sample],
        "z_nm": [c.z_nm for c in opt_sample],
    }

    evaluation = evaluate_predictions(preds_doc, part1_serializable, part2, part3)
    elapsed_s = time.perf_counter() - t0

    result_doc = {
        "experiment": "exp131_scalable_m4_architecture",
        "hypothesis_id": "H149",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": float(elapsed_s),
        "no_lab_measurement": True,
        "epistemic_tags": ["Model", "Sayisal-Simulasyon", "Literatur"],
        "anchor_references": preds_doc["anchor_references"],
        "part1_flipflop_straggle": part1_serializable,
        "part2_lindblad_bus": part2,
        "part3_percolation_and_cad": part3,
        "prediction_evaluation": evaluation,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON_PATH.write_text(json.dumps(result_doc, indent=2), encoding="utf-8")
    print(f"[Exp131] Saved {OUTPUT_JSON_PATH.relative_to(REPO_ROOT)} in {elapsed_s:.1f}s")
    print(f"[Exp131] Verdict: {evaluation['n_pass']}/{evaluation['n_total']} ({evaluation['overall_verdict']})")
    for k, v in evaluation["predictions"].items():
        print(f"  - {k}: {v['verdict']} -> {v['measured']}")
    return result_doc


if __name__ == "__main__":
    main()
