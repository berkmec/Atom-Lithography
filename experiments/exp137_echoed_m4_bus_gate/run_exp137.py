"""Master runner for Exp137: Echoed M4 Cavity-QED Bus Gate under 1/f^alpha Noise (H155).

Executes:
  Part 1: Multi-OU 1/f^alpha PSD verification (alpha in {0.8, 1.0, 1.2}, [1 Hz, 100 MHz]),
          exact Cywinski DD filter-function suppression ratios, and noiseless 12x12
          unitary / DRAG-vs-no-DRAG cavity-leakage benchmark.
  Part 2: 4-protocol head-to-head comparison on Exp131 Best-of-6 heterogeneous 3 kOhm
          NbTiN donor pairs (N_traj = 512/pair on CUDA):
          (P1_markov anchor, P1 Bare 1/f, P2 FF-Echo-CZ, P3 XY4-DRAG-CZ,
           P4 Sweet-Spot Parametric AC-Stark Echo CZ), with both longitudinal-only (dw)
          and full longitudinal+transverse (dw+dg) 1/f noise, plus S_eps=2.0 stress and
          alpha in {0.8, 1.0, 1.2} color sweep.
  Part 3: 5x4 2D Fault-Tolerance Phase Map (S_eps in {0.25, 0.5, 1.0, 2.0, 5.0} ueV/rtHz
          x Q_r in {5e4, 1e5, 2e5, 5e5}) mapping the exact F_Bell >= 0.990 boundary.
  Part 4: Full 16-element Choi/PTM Pauli Error Channel export for Exp138 surface-code
          decoder at S_eps = 1.0, 0.5, and 0.25 ueV/rtHz.
  Part 5: Transparent evaluation of pre-registered predictions EC1-EC7.

Epistemic scope: {Model} / {Sayisal-Simulasyon}. no_lab_measurement=true.
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.exp131_scalable_m4_architecture.flipflop_cell131 import (
    Z_MIN_DOUBLE_WELL_NM,
    evaluate_flipflop_cell,
    optimize_cell_dc_bias,
    sample_exp124_donors,
    tunnel_coupling_ghz,
)
from experiments.exp137_echoed_m4_bus_gate.echo_bus_solver137 import (
    DEFAULT_T_PI_DRAG_GAUSS_US,
    PAULI_16_NAMES,
    FlipFlopPairSpec,
    audit_exact_4x4_tosi_clock_impossibility,
    audit_mw_pi_pulse_crosstalk,
    simulate_echoed_cz_cuda,
)
from experiments.exp137_echoed_m4_bus_gate.noise_ou137 import (
    compute_cywinski_filter_suppression,
    verify_ou_psd_spectrum,
)

RESULTS_DIR = REPO_ROOT / "results" / "exp137_echoed_m4_bus_gate"
PREDICTIONS_PATH = RESULTS_DIR / "predictions_exp137.json"
EXP131_ANCHOR_PATH = REPO_ROOT / "results" / "exp131_scalable_m4_architecture" / "exp131.json"
OUTPUT_JSON_PATH = RESULTS_DIR / "exp137.json"


def _optimize_cell_echo_bias(
    z_nm: float,
    r_xy_nm: float,
    z_r_ohm: float = 3000.0,
    q_l: float = 2e5,
    s_eps_ref: float = 1.0,
    dd_gain: float = 20.0,
):
    """Echo-aware DC bias optimizer for dynamical-decoupling M4 operation.

    Because XY4/Echo suppresses 1/f frequency dephasing by ~20x, the node controller no
    longer needs to sacrifice 80% of g_eff to hide from bare D1 noise; instead it maximizes
    echo-effective figure of merit g_eff / (kappa/2 + gamma1/2 + gamma_phi/dd_gain) while
    staying cleanly inside p_exc_charge <= 0.18 and E_ch >= 5.5 GHz.
    """
    if z_nm < Z_MIN_DOUBLE_WELL_NM:
        return None
    tc, _ = tunnel_coupling_ghz(z_nm, r_xy_nm)
    eps_min = 0.0 if tc >= 5.5 else math.sqrt(max(0.0, 5.55 ** 2 - tc * tc))
    if eps_min > 12.0:
        return None
    best = None
    best_sc = -1.0
    for ep in np.linspace(eps_min, 12.0, 56):
        c = evaluate_flipflop_cell(z_nm, r_xy_nm, float(ep), z_r_ohm, q_l, s_eps_ref)
        if c is not None and c.p_exc_charge <= 0.18:
            sc = c.g_eff_mhz / (0.5 * c.kappa_khz * 1e-3 + 0.5 * c.gamma_1_khz * 1e-3 + (c.gamma_phi_khz * 1e-3) / dd_gain)
            if sc > best_sc:
                best_sc = sc
                best = c
    return best


def build_exp131_best_of_6_pairs(
    n_pairs: int = 6,
    delta_z_cap_nm: float = 8.0,
    z_r_ohm: float = 3000.0,
    q_l: float = 2e5,
    s_eps_ref: float = 1.0,
    seed: int = 13701,
) -> tuple[list[FlipFlopPairSpec], list[FlipFlopPairSpec], list[tuple[float, float]]]:
    """Sample genuine Exp124 Best-of-6 31P donor pairs (Delta_z_cap* = 8.0 nm, 3 kOhm NbTiN).

    Returns:
      - echo_pairs: 6 heterogeneous pairs biased with echo-aware DC operating points (used
        apples-to-apples across P1, P2, P3, P4 under colored 1/f^alpha noise; certified yield ~95%),
      - exp131_markov_pairs: 6 pairs biased with Exp131's original un-echoed M_res criterion,
      - markov_gphis: Exp131 conservative Markovian dephasing rates for exact CM4 anchor check.
    """
    rng = np.random.default_rng(seed)
    z_arr, r_arr = sample_exp124_donors(450, delta_z_cap_nm, rng)

    echo_pool = []
    mk_pool = []
    for zi, ri in zip(z_arr, r_arr):
        ce = _optimize_cell_echo_bias(float(zi), float(ri), z_r_ohm, q_l, s_eps_ref)
        if ce is not None and ce.cooperativity >= 100.0:
            cp = evaluate_flipflop_cell(float(zi), float(ri), ce.eps_ghz + 5e-3, z_r_ohm, q_l, s_eps_ref)
            cm = evaluate_flipflop_cell(float(zi), float(ri), ce.eps_ghz - 5e-3, z_r_ohm, q_l, s_eps_ref)
            dg = (cp.g_eff_mhz - cm.g_eff_mhz) / 1e-2 if (cp and cm) else 0.0
            # Echo-aware node ranking balances coupling speed g_eff and flat dg/deps stability
            rank_sc = ce.g_eff_mhz / (0.0125 + (ce.gamma_phi_khz * 1e-3) / 20.0 + 0.06 * abs(dg))
            echo_pool.append((ce, float(dg), rank_sc))

        cmk = optimize_cell_dc_bias(float(zi), float(ri), z_r_ohm, q_l, s_eps_ref, f_r_ghz=5.0, objective="m_res")
        if cmk is not None and cmk.cooperativity >= 100.0:
            mk_pool.append(cmk)

    # Best-of-6 node selection (p_spec = 0.51 per candidate slot, matching Exp131)
    echo_sel = []
    while len(echo_sel) < 2 * n_pairs:
        surv = [echo_pool[int(rng.integers(0, len(echo_pool)))] for _ in range(6) if rng.random() < 0.51]
        if surv:
            echo_sel.append(max(surv, key=lambda item: item[2]))

    mk_sel = []
    while len(mk_sel) < 2 * n_pairs:
        surv = [mk_pool[int(rng.integers(0, len(mk_pool)))] for _ in range(6) if rng.random() < 0.51]
        if surv:
            mk_sel.append(max(surv, key=lambda c: c.m_res_merit))

    echo_pairs: list[FlipFlopPairSpec] = []
    mk_pairs: list[FlipFlopPairSpec] = []
    markov_gphis: list[tuple[float, float]] = []
    for i in range(n_pairs):
        (c1, dg1, _), (c2, dg2, _) = echo_sel[2 * i], echo_sel[2 * i + 1]
        echo_pairs.append(
            FlipFlopPairSpec(
                g1_mhz=c1.g_eff_mhz,
                g2_mhz=c2.g_eff_mhz,
                d1_1_ghz_per_ghz=c1.d1_ghz_per_ghz,
                d2_1_inv_ghz=c1.d2_inv_ghz,
                d1_2_ghz_per_ghz=c2.d1_ghz_per_ghz,
                d2_2_inv_ghz=c2.d2_inv_ghz,
                dg1_mhz_per_ghz=dg1,
                dg2_mhz_per_ghz=dg2,
                gamma1_1_khz=c1.gamma_1_khz,
                gamma1_2_khz=c2.gamma_1_khz,
                label=f"echo_b6_pair_{i}",
            )
        )
        m1, m2 = mk_sel[2 * i], mk_sel[2 * i + 1]
        mk_pairs.append(
            FlipFlopPairSpec(
                g1_mhz=m1.g_eff_mhz,
                g2_mhz=m2.g_eff_mhz,
                d1_1_ghz_per_ghz=m1.d1_ghz_per_ghz,
                d2_1_inv_ghz=m1.d2_inv_ghz,
                d1_2_ghz_per_ghz=m2.d1_ghz_per_ghz,
                d2_2_inv_ghz=m2.d2_inv_ghz,
                dg1_mhz_per_ghz=0.0,
                dg2_mhz_per_ghz=0.0,
                gamma1_1_khz=m1.gamma_1_khz,
                gamma1_2_khz=m2.gamma_1_khz,
                label=f"exp131_mk_pair_{i}",
            )
        )
        markov_gphis.append((m1.gamma_phi_khz, m2.gamma_phi_khz))
    return echo_pairs, mk_pairs, markov_gphis


def aggregate_channel_results(res_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Ensemble-average Pauli channels & fidelities across heterogeneous pairs."""
    n = len(res_list)
    pauli_16_avg = {name: float(np.mean([r["pauli_16"][name] for r in res_list])) for name in PAULI_16_NAMES}
    p_i = pauli_16_avg["II"]
    p_x = pauli_16_avg["IX"] + pauli_16_avg["XI"] + pauli_16_avg["XX"]
    p_y = pauli_16_avg["IY"] + pauli_16_avg["YI"] + pauli_16_avg["YY"] + pauli_16_avg["XY"] + pauli_16_avg["YX"]
    p_z = pauli_16_avg["IZ"] + pauli_16_avg["ZI"] + pauli_16_avg["XZ"] + pauli_16_avg["ZX"] + pauli_16_avg["YZ"] + pauli_16_avg["ZY"]
    p_zz = pauli_16_avg["ZZ"]
    p_sum = float(sum(pauli_16_avg.values()))
    f_avg = float(np.mean([r["F_avg"] for r in res_list]))
    f_bell = float(np.mean([r["F_Bell"] for r in res_list]))
    f_ent = float(np.mean([r["F_ent"] for r in res_list]))
    p_leak = float(np.mean([r["p_leak"] for r in res_list]))
    t_gate = float(np.mean([r["t_gate_us"] for r in res_list]))
    return {
        "n_pairs": int(n),
        "n_traj_per_pair": int(res_list[0]["n_traj"]),
        "total_trajectories": int(n * res_list[0]["n_traj"]),
        "F_ent": f_ent,
        "F_avg": f_avg,
        "median_F_avg": float(np.median([r["F_avg"] for r in res_list])),
        "min_F_avg": float(np.min([r["F_avg"] for r in res_list])),
        "max_F_avg": float(np.max([r["F_avg"] for r in res_list])),
        "F_Bell": f_bell,
        "median_F_Bell": float(np.median([r["F_Bell"] for r in res_list])),
        "t_gate_us": t_gate,
        "p_I": float(p_i),
        "p_X": float(p_x),
        "p_Y": float(p_y),
        "p_Z": float(p_z),
        "p_ZZ": float(p_zz),
        "p_leak": p_leak,
        "p_total_err": float(1.0 - p_i),
        "pauli_sum": p_sum,
        "nielsen_identity_err": abs(f_avg - (4.0 * p_i + 1.0) / 5.0),
        "z_bias_ratio": float((p_z + p_zz) / max(p_x + p_y, 1e-12)),
        "pauli_16": pauli_16_avg,
        "cptp_audit": {
            "max_trace_err": float(max(r["cptp_audit"]["max_trace_err"] for r in res_list)),
            "max_herm_err": float(max(r["cptp_audit"]["max_herm_err"] for r in res_list)),
            "min_eigval": float(min(r["cptp_audit"]["min_eigval"] for r in res_list)),
        },
        "per_pair_F_avg": [float(r["F_avg"]) for r in res_list],
        "per_pair_F_Bell": [float(r["F_Bell"]) for r in res_list],
    }


def evaluate_predictions(
    preds_doc: dict[str, Any],
    part1: dict[str, Any],
    part2: dict[str, Any],
    part3: dict[str, Any],
    part4: dict[str, Any],
    global_cptp: dict[str, float],
) -> dict[str, Any]:
    """Strictly evaluate pre-registered EC1-EC7 against measured simulation results."""
    preds = preds_doc["predictions"]
    verdicts: dict[str, Any] = {}

    # EC1: OU 1/f^alpha PSD + CPTP precision + noiseless XY4-DRAG unitary
    t1 = preds["EC1_ou_1f_noise_psd_and_cptp_precision"]["thresholds"]
    psd_err = part1["ou_psd_audit"]["worst_psd_rel_err"]
    rms_err = part1["ou_psd_audit"]["worst_rms_rel_err"]
    tr_err = global_cptp["max_trace_err"]
    hm_err = global_cptp["max_herm_err"]
    min_ev = global_cptp["min_eigval"]
    nl_p3 = part1["noiseless_unitary"]["P3"]
    ec1_pass = (
        psd_err < t1["max_psd_rel_err"]
        and rms_err < t1["max_rms_rel_err"]
        and tr_err < t1["max_trace_err"]
        and hm_err < t1["max_trace_err"]
        and min_ev >= -t1["max_trace_err"]
        and nl_p3["F_avg"] >= t1["min_noiseless_xy4_drag_F_avg"]
        and nl_p3["p_leak"] < t1["max_noiseless_leak"]
    )
    verdicts["EC1_ou_1f_noise_psd_and_cptp_precision"] = {
        "verdict": "PASS" if ec1_pass else "FAIL",
        "measured": {
            "worst_psd_rel_err": psd_err,
            "worst_rms_rel_err": rms_err,
            "max_trace_err": tr_err,
            "max_herm_err": hm_err,
            "min_eigval": min_ev,
            "noiseless_P3_F_avg": nl_p3["F_avg"],
            "noiseless_P3_p_leak": nl_p3["p_leak"],
        },
        "thresholds": t1,
    }

    # EC2: Bare CZ anchor and echo breakthrough
    t2 = preds["EC2_bare_cz_anchor_and_echo_breakthrough"]["thresholds"]
    f_mk = part2["markov_anchor_P1"]["F_avg"]
    p1_1f = part2["nominal_S1p0_full_dw_dg"]["P1"]
    p2_1f = part2["nominal_S1p0_full_dw_dg"]["P2"]
    p3_1f = part2["nominal_S1p0_full_dw_dg"]["P3"]
    p3_dw = part2["nominal_S1p0_dw_only"]["P3"]
    ec2_pass = (
        t2["markov_anchor_min"] <= f_mk <= t2["markov_anchor_max"]
        and p2_1f["F_avg"] > p1_1f["F_avg"]
        and p3_1f["F_avg"] >= t2["min_p3_F_avg"]
        and p3_1f["F_Bell"] >= t2["min_p3_F_bell"]
    )
    verdicts["EC2_bare_cz_anchor_and_echo_breakthrough"] = {
        "verdict": "PASS" if ec2_pass else "FAIL",
        "measured": {
            "markov_anchor_F_avg": f_mk,
            "P1_bare_1f_F_avg": p1_1f["F_avg"],
            "P2_ff_echo_F_avg": p2_1f["F_avg"],
            "P3_xy4_drag_F_avg_full_dg": p3_1f["F_avg"],
            "P3_xy4_drag_F_Bell_full_dg": p3_1f["F_Bell"],
            "P3_xy4_drag_F_avg_dw_only": p3_dw["F_avg"],
            "P3_xy4_drag_F_Bell_dw_only": p3_dw["F_Bell"],
        },
        "thresholds": t2,
    }

    # EC3: XY4-DRAG beats FF-Echo under pulse/alpha stress & DRAG cuts leakage
    t3 = preds["EC3_xy4_drag_beats_ff_echo_under_pulse_and_alpha_stress"]["thresholds"]
    nl_nodrag = part1["noiseless_unitary"]["P3_no_drag"]
    alpha_sw = part2["alpha_sweep_P3_and_P4"]
    f_a08 = alpha_sw["alpha_0.8"]["P3"]["F_avg"]
    f_a10 = alpha_sw["alpha_1.0"]["P3"]["F_avg"]
    f_a12 = alpha_sw["alpha_1.2"]["P3"]["F_avg"]
    ec3_pass = (
        p3_1f["F_avg"] > p2_1f["F_avg"]
        and nl_p3["p_leak"] < nl_nodrag["p_leak"]
        and (f_a08 < f_a10 < f_a12)
    )
    verdicts["EC3_xy4_drag_beats_ff_echo_under_pulse_and_alpha_stress"] = {
        "verdict": "PASS" if ec3_pass else "FAIL",
        "measured": {
            "P3_F_avg": p3_1f["F_avg"],
            "P2_F_avg": p2_1f["F_avg"],
            "P3_minus_P2": p3_1f["F_avg"] - p2_1f["F_avg"],
            "noiseless_P3_DRAG_leak": nl_p3["p_leak"],
            "noiseless_P3_noDRAG_leak": nl_nodrag["p_leak"],
            "P3_F_avg_alpha_0p8": f_a08,
            "P3_F_avg_alpha_1p0": f_a10,
            "P3_F_avg_alpha_1p2": f_a12,
        },
        "thresholds": t3,
    }

    # EC4: P4 sweet-spot parametric echo at nominal M4 & S=2.0 stress
    t4 = preds["EC4_sweetspot_p4_surface_code_threshold_at_nominal"]["thresholds"]
    p4_1f = part2["nominal_S1p0_full_dw_dg"]["P4"]
    s2_map = part2["stress_S2p0_full_dw_dg"]
    p4_beats_all_s2 = (
        s2_map["P4"]["F_avg"] > s2_map["P3"]["F_avg"]
        and s2_map["P4"]["F_avg"] > s2_map["P2"]["F_avg"]
        and s2_map["P4"]["F_avg"] > s2_map["P1"]["F_avg"]
    )
    ec4_pass = (
        p4_1f["F_avg"] >= t4["min_p4_nominal_F_avg"]
        and p4_1f["F_Bell"] >= t4["min_p4_nominal_F_bell"]
        and p4_beats_all_s2
    )
    verdicts["EC4_sweetspot_p4_surface_code_threshold_at_nominal"] = {
        "verdict": "PASS" if ec4_pass else "FAIL",
        "measured": {
            "P4_nominal_F_avg": p4_1f["F_avg"],
            "P4_nominal_F_Bell": p4_1f["F_Bell"],
            "P4_S2p0_F_avg": s2_map["P4"]["F_avg"],
            "P3_S2p0_F_avg": s2_map["P3"]["F_avg"],
            "P2_S2p0_F_avg": s2_map["P2"]["F_avg"],
            "P1_S2p0_F_avg": s2_map["P1"]["F_avg"],
        },
        "thresholds": t4,
    }

    # EC5: 2D fault-tolerance envelope & extreme failure wall
    t5 = preds["EC5_2d_fault_tolerance_envelope_and_failure_wall"]["thresholds"]
    pts = part3["points"]
    zone_pts = [p for p in pts if p["q_r"] >= 2e5 and p["s_eps_uev"] <= 1.0]
    min_zone_bell = min(p["F_Bell"] for p in zone_pts)
    hi_pt = next(p for p in pts if abs(p["q_r"] - 5e5) < 1e-3 and abs(p["s_eps_uev"] - 0.5) < 1e-6)
    wall_pt = next(p for p in pts if abs(p["q_r"] - 5e4) < 1e-3 and abs(p["s_eps_uev"] - 5.0) < 1e-6)
    ec5_pass = (
        min_zone_bell >= t5["min_nominal_zone_F_bell"]
        and hi_pt["F_Bell"] >= t5["min_highQ_lowS_F_bell"]
        and wall_pt["F_avg"] < t5["max_extreme_wall_F_avg"]
    )
    verdicts["EC5_2d_fault_tolerance_envelope_and_failure_wall"] = {
        "verdict": "PASS" if ec5_pass else "FAIL",
        "measured": {
            "min_F_Bell_in_Qge2e5_Sle1p0": min_zone_bell,
            "Q5e5_S0p5_F_Bell": hi_pt["F_Bell"],
            "Q5e5_S0p5_F_avg": hi_pt["F_avg"],
            "extreme_wall_Q5e4_S5p0_F_avg": wall_pt["F_avg"],
            "extreme_wall_Q5e4_S5p0_F_Bell": wall_pt["F_Bell"],
        },
        "thresholds": t5,
    }

    # EC6: Transverse dg jitter honest budget
    t6 = preds["EC6_transverse_dg_jitter_honest_budget"]["thresholds"]
    p3_pen = part2["nominal_S1p0_dw_only"]["P3"]["F_avg"] - part2["nominal_S1p0_full_dw_dg"]["P3"]["F_avg"]
    p4_pen = part2["nominal_S1p0_dw_only"]["P4"]["F_avg"] - part2["nominal_S1p0_full_dw_dg"]["P4"]["F_avg"]
    sup_fac = p3_pen / max(p4_pen, 1e-9)
    ec6_pass = p3_pen > t6["min_p3_dg_penalty"] and sup_fac >= t6["min_p4_dg_suppression_factor"]
    verdicts["EC6_transverse_dg_jitter_honest_budget"] = {
        "verdict": "PASS" if ec6_pass else "FAIL",
        "measured": {
            "P3_dg_penalty_Delta_F": float(p3_pen),
            "P4_dg_penalty_Delta_F": float(p4_pen),
            "P4_dg_suppression_factor": float(sup_fac),
        },
        "thresholds": t6,
    }

    # EC7: Exact Pauli error channel for Exp138 decoder
    t7 = preds["EC7_exact_pauli_error_channel_for_exp138_decoder"]["thresholds"]
    ch1 = part4["best_protocol_S1p0"]
    ch05 = part4["best_protocol_S0p5"]
    max_sum_err = max(abs(ch1["pauli_sum"] - 1.0), abs(ch05["pauli_sum"] - 1.0))
    max_niel_err = max(ch1["nielsen_identity_err"], ch05["nielsen_identity_err"])
    max_leak = max(ch1["p_leak"], ch05["p_leak"])
    ec7_pass = (
        max_sum_err < t7["max_pauli_sum_err"]
        and max_niel_err < t7["max_nielsen_err"]
        and max_leak < t7["max_p_leak"]
    )
    verdicts["EC7_exact_pauli_error_channel_for_exp138_decoder"] = {
        "verdict": "PASS" if ec7_pass else "FAIL",
        "measured": {
            "max_pauli_sum_err": float(max_sum_err),
            "max_nielsen_identity_err": float(max_niel_err),
            "max_p_leak": float(max_leak),
            "S1p0_p_total_err": ch1["p_total_err"],
            "S1p0_z_bias_ratio": ch1["z_bias_ratio"],
            "S0p5_p_total_err": ch05["p_total_err"],
            "S0p5_z_bias_ratio": ch05["z_bias_ratio"],
        },
        "thresholds": t7,
    }

    n_pass = sum(1 for v in verdicts.values() if v["verdict"] == "PASS")
    return {
        "n_pass": int(n_pass),
        "n_total": int(len(verdicts)),
        "overall_verdict": "PASS" if n_pass == len(verdicts) else "PARTIAL_FAIL",
        "predictions": verdicts,
    }


def main() -> dict[str, Any]:
    t0 = time.perf_counter()
    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError(f"Pre-registered predictions missing: {PREDICTIONS_PATH}")
    preds_doc = json.loads(PREDICTIONS_PATH.read_text(encoding="utf-8"))
    exp131_ref = json.loads(EXP131_ANCHOR_PATH.read_text(encoding="utf-8"))
    exp131_cz_anchor = exp131_ref["part2_lindblad_bus"]["universal_cz_gate"]["nominal_3kohm_Q2e5_S1"]["mean_F_avg_cz"]

    print("[Exp137] Part 1: Multi-OU 1/f^alpha PSD audit, Cywinski filter functions & noiseless unitary...")
    ou_audit = verify_ou_psd_spectrum(alphas=[0.8, 1.0, 1.2])
    cywinski = compute_cywinski_filter_suppression(t_gate_us=1.5, d1_ghz_per_ghz=1.0e-4, s0_uev=1.0)

    pairs, mk_pairs, markov_gphis = build_exp131_best_of_6_pairs(n_pairs=6, seed=13701)
    print("  -> Sampled 6 Echo-Aware Best-of-6 pairs:")
    for p in pairs:
        print(f"     {p.label}: g=({p.g1_mhz:.2f},{p.g2_mhz:.2f})MHz D1=({p.d1_1_ghz_per_ghz:+.1e},{p.d1_2_ghz_per_ghz:+.1e}) "
              f"dg/de=({p.dg1_mhz_per_ghz:+.2f},{p.dg2_mhz_per_ghz:+.2f})")

    # Noiseless unitary & DRAG leakage audit on pair 0
    nl_unitary: dict[str, Any] = {}
    for prot in ["P1", "P2", "P3", "P3_no_drag", "P4"]:
        r_nl = simulate_echoed_cz_cuda(pairs[0], q_r=0.0, s_eps_uev=0.0, protocol=prot, n_traj=1, eps_rot=0.0, include_dg_jitter=False, seed=10)
        nl_unitary[prot] = {
            "F_avg": r_nl["F_avg"],
            "F_Bell": r_nl["F_Bell"],
            "p_leak": r_nl["p_leak"],
            "ent_phase_over_pi": r_nl["ent_phase_over_pi"],
            "t_gate_us": r_nl["t_gate_us"],
        }
        print(f"  -> Noiseless {prot:10s}: F_avg={r_nl['F_avg']:.6f} leak={r_nl['p_leak']:.2e} t={r_nl['t_gate_us']:.3f}us")

    part1 = {
        "exp131_cz_anchor_ref": float(exp131_cz_anchor),
        "ou_psd_audit": ou_audit,
        "cywinski_filter_theory": cywinski,
        "noiseless_unitary": nl_unitary,
        "mw_pi_pulse_crosstalk_audit_OBS101": audit_mw_pi_pulse_crosstalk(),
        "tosi_4x4_clock_impossibility_OBS042": audit_exact_4x4_tosi_clock_impossibility(),
        "sampled_pairs": [
            {
                "label": p.label,
                "g1_mhz": p.g1_mhz,
                "g2_mhz": p.g2_mhz,
                "d1_1": p.d1_1_ghz_per_ghz,
                "d2_1": p.d2_1_inv_ghz,
                "d1_2": p.d1_2_ghz_per_ghz,
                "d2_2": p.d2_2_inv_ghz,
                "dg1_mhz_per_ghz": p.dg1_mhz_per_ghz,
                "dg2_mhz_per_ghz": p.dg2_mhz_per_ghz,
                "markov_gphi_khz": [mg[0], mg[1]],
            }
            for p, mg in zip(pairs, markov_gphis)
        ],
    }

    global_cptp = {"max_trace_err": 0.0, "max_herm_err": 0.0, "min_eigval": 1.0}

    def update_cptp(agg: dict[str, Any]) -> None:
        ca = agg["cptp_audit"]
        global_cptp["max_trace_err"] = max(global_cptp["max_trace_err"], ca["max_trace_err"])
        global_cptp["max_herm_err"] = max(global_cptp["max_herm_err"], ca["max_herm_err"])
        global_cptp["min_eigval"] = min(global_cptp["min_eigval"], ca["min_eigval"])

    print("[Exp137] Part 2: 4-protocol head-to-head benchmark (N_traj=512/pair on CUDA)...")
    # (a) Exact Exp131 Markovian bare CZ anchor (on Exp131 un-echoed M_res biased pairs)
    mk_runs = [
        simulate_echoed_cz_cuda(p, q_r=2e5, s_eps_uev=0.0, protocol="P1", n_traj=1, eps_rot=0.0,
                                include_dg_jitter=False, markovian_dephasing_override_khz=mg, seed=100 + i)
        for i, (p, mg) in enumerate(zip(mk_pairs, markov_gphis))
    ]
    markov_anchor = aggregate_channel_results(mk_runs)
    update_cptp(markov_anchor)
    print(f"  -> Markovian Bare CZ Anchor: F_avg={markov_anchor['F_avg']:.4f} (Exp131 ref: {exp131_cz_anchor:.4f})")

    # (b) Nominal S_eps = 1.0 ueV/rtHz, Q_r = 2e5, alpha = 1.0: BOTH dw-only and full (dw + dg)
    nom_dw_only: dict[str, Any] = {}
    nom_full_dg: dict[str, Any] = {}
    for prot in ["P1", "P2", "P3", "P4"]:
        runs_dw = [
            simulate_echoed_cz_cuda(p, q_r=2e5, s_eps_uev=1.0, protocol=prot, alpha=1.0, n_traj=512,
                                    t_pi_us=DEFAULT_T_PI_DRAG_GAUSS_US, eps_rot=0.015, include_dg_jitter=False, seed=200 + i)
            for i, p in enumerate(pairs)
        ]
        runs_dg = [
            simulate_echoed_cz_cuda(p, q_r=2e5, s_eps_uev=1.0, protocol=prot, alpha=1.0, n_traj=512,
                                    t_pi_us=DEFAULT_T_PI_DRAG_GAUSS_US, eps_rot=0.015, include_dg_jitter=True, seed=300 + i)
            for i, p in enumerate(pairs)
        ]
        agg_dw = aggregate_channel_results(runs_dw)
        agg_dg = aggregate_channel_results(runs_dg)
        update_cptp(agg_dw)
        update_cptp(agg_dg)
        nom_dw_only[prot] = agg_dw
        nom_full_dg[prot] = agg_dg
        print(f"  -> {prot} (S=1.0, Q=2e5): dw-only F_avg={agg_dw['F_avg']:.4f} F_Bell={agg_dw['F_Bell']:.4f} | "
              f"full(dw+dg) F_avg={agg_dg['F_avg']:.4f} F_Bell={agg_dg['F_Bell']:.4f} t={agg_dg['t_gate_us']:.3f}us")

    # (c) Stress test at S_eps = 2.0 ueV/rtHz (full dw+dg, 3 representative pairs, N_traj=512)
    rep_pairs = pairs[:3]
    stress_s2: dict[str, Any] = {}
    for prot in ["P1", "P2", "P3", "P4"]:
        runs_s2 = [
            simulate_echoed_cz_cuda(p, q_r=2e5, s_eps_uev=2.0, protocol=prot, alpha=1.0, n_traj=512,
                                    t_pi_us=DEFAULT_T_PI_DRAG_GAUSS_US, eps_rot=0.015, include_dg_jitter=True, seed=400 + i)
            for i, p in enumerate(rep_pairs)
        ]
        agg_s2 = aggregate_channel_results(runs_s2)
        update_cptp(agg_s2)
        stress_s2[prot] = agg_s2
    print(f"  -> Stress S=2.0 (full dw+dg): P1={stress_s2['P1']['F_avg']:.4f} P2={stress_s2['P2']['F_avg']:.4f} "
          f"P3={stress_s2['P3']['F_avg']:.4f} P4={stress_s2['P4']['F_avg']:.4f}")

    # (d) Noise color sweep alpha in {0.8, 1.0, 1.2} for P1, P2, P3, P4 (3 representative pairs, N_traj=512)
    alpha_sweep: dict[str, Any] = {}
    for av in [0.8, 1.0, 1.2]:
        alpha_sweep[f"alpha_{av:.1f}"] = {}
        for prot in ["P1", "P2", "P3", "P4"]:
            runs_a = [
                simulate_echoed_cz_cuda(p, q_r=2e5, s_eps_uev=1.0, protocol=prot, alpha=av, n_traj=512,
                                        t_pi_us=DEFAULT_T_PI_DRAG_GAUSS_US, eps_rot=0.015, include_dg_jitter=True, seed=500 + i)
                for i, p in enumerate(rep_pairs)
            ]
            agg_a = aggregate_channel_results(runs_a)
            update_cptp(agg_a)
            alpha_sweep[f"alpha_{av:.1f}"][prot] = {
                "F_avg": agg_a["F_avg"],
                "F_Bell": agg_a["F_Bell"],
                "p_total_err": agg_a["p_total_err"],
                "p_leak": agg_a["p_leak"],
            }
        print(f"  -> alpha={av:.1f}: P1={alpha_sweep[f'alpha_{av:.1f}']['P1']['F_avg']:.4f} "
              f"P2={alpha_sweep[f'alpha_{av:.1f}']['P2']['F_avg']:.4f} "
              f"P3={alpha_sweep[f'alpha_{av:.1f}']['P3']['F_avg']:.4f} "
              f"P4={alpha_sweep[f'alpha_{av:.1f}']['P4']['F_avg']:.4f}")

    part2 = {
        "markov_anchor_P1": markov_anchor,
        "nominal_S1p0_dw_only": nom_dw_only,
        "nominal_S1p0_full_dw_dg": nom_full_dg,
        "stress_S2p0_full_dw_dg": stress_s2,
        "alpha_sweep_P3_and_P4": alpha_sweep,
    }

    print("[Exp137] Part 3: 5x4 2D Fault-Tolerance Phase Map (S_eps x Q_r, P4 best echoed, N_traj=512)...")
    s_grid = [0.25, 0.5, 1.0, 2.0, 5.0]
    q_grid = [5e4, 1e5, 2e5, 5e5]
    pm_points: list[dict[str, Any]] = []
    for qr in q_grid:
        for sv in s_grid:
            runs_pm = [
                simulate_echoed_cz_cuda(p, q_r=qr, s_eps_uev=sv, protocol="P4", alpha=1.0, n_traj=512,
                                        t_pi_us=DEFAULT_T_PI_DRAG_GAUSS_US, eps_rot=0.015, include_dg_jitter=True, seed=700 + i)
                for i, p in enumerate(rep_pairs)
            ]
            agg_pm = aggregate_channel_results(runs_pm)
            update_cptp(agg_pm)
            pm_points.append({
                "q_r": float(qr),
                "s_eps_uev": float(sv),
                "kappa_khz": float((5.0 / qr) * 1e6),
                "protocol": "P4",
                "F_avg": agg_pm["F_avg"],
                "F_Bell": agg_pm["F_Bell"],
                "p_total_err": agg_pm["p_total_err"],
                "p_leak": agg_pm["p_leak"],
                "t_gate_us": agg_pm["t_gate_us"],
            })
            print(f"     Q={qr:.0e} S={sv:4.2f}: F_avg={agg_pm['F_avg']:.4f} F_Bell={agg_pm['F_Bell']:.4f} p_err={agg_pm['p_total_err']:.4f}")

    part3 = {
        "s_eps_uev_grid": s_grid,
        "q_r_grid": q_grid,
        "protocol_mapped": "P4",
        "n_pairs_per_point": len(rep_pairs),
        "n_traj_per_pair": 512,
        "points": pm_points,
    }

    print("[Exp137] Part 4: Full 16-Pauli Error Channel Export for Exp138 Surface-Code Decoder...")
    # Evaluate P4 (best) and P3 at S_eps = 0.5 and 0.25 across ALL 6 pairs (S=1.0 already done in Part 2!)
    runs_p4_s05 = [
        simulate_echoed_cz_cuda(p, q_r=2e5, s_eps_uev=0.5, protocol="P4", alpha=1.0, n_traj=512,
                                t_pi_us=DEFAULT_T_PI_DRAG_GAUSS_US, eps_rot=0.015, include_dg_jitter=True, seed=900 + i)
        for i, p in enumerate(pairs)
    ]
    runs_p3_s05 = [
        simulate_echoed_cz_cuda(p, q_r=2e5, s_eps_uev=0.5, protocol="P3", alpha=1.0, n_traj=512,
                                t_pi_us=DEFAULT_T_PI_DRAG_GAUSS_US, eps_rot=0.015, include_dg_jitter=True, seed=950 + i)
        for i, p in enumerate(pairs)
    ]
    runs_p4_s025 = [
        simulate_echoed_cz_cuda(p, q_r=2e5, s_eps_uev=0.25, protocol="P4", alpha=1.0, n_traj=512,
                                t_pi_us=DEFAULT_T_PI_DRAG_GAUSS_US, eps_rot=0.015, include_dg_jitter=True, seed=980 + i)
        for i, p in enumerate(pairs)
    ]
    agg_p4_s05 = aggregate_channel_results(runs_p4_s05)
    agg_p3_s05 = aggregate_channel_results(runs_p3_s05)
    agg_p4_s025 = aggregate_channel_results(runs_p4_s025)
    for agg in (agg_p4_s05, agg_p3_s05, agg_p4_s025):
        update_cptp(agg)

    part4 = {
        "best_protocol_name": "P4_SweetSpot_Parametric_Echo_CZ",
        "best_protocol_S1p0": nom_full_dg["P4"],
        "best_protocol_S0p5": agg_p4_s05,
        "best_protocol_S0p25": agg_p4_s025,
        "P3_XY4_DRAG_S1p0": nom_full_dg["P3"],
        "P3_XY4_DRAG_S0p5": agg_p3_s05,
        "P1_Bare_1f_S1p0": nom_full_dg["P1"],
    }

    evaluation = evaluate_predictions(preds_doc, part1, part2, part3, part4, global_cptp)
    elapsed_s = time.perf_counter() - t0

    result_doc = {
        "experiment": "exp137_echoed_m4_bus_gate",
        "hypothesis_id": "H155",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": float(elapsed_s),
        "no_lab_measurement": True,
        "epistemic_tags": ["Model", "Sayisal-Simulasyon", "Literatur"],
        "anchor_references": preds_doc["anchor_references"],
        "device_used": mk_runs[0]["device_used"],
        "global_cptp_audit": global_cptp,
        "part1_noise_and_unitary": part1,
        "part2_protocol_comparison": part2,
        "part3_2d_phase_map": part3,
        "part4_exp138_pauli_channels": part4,
        "prediction_evaluation": evaluation,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON_PATH.write_text(json.dumps(result_doc, indent=2), encoding="utf-8")
    print(f"[Exp137] Saved {OUTPUT_JSON_PATH.relative_to(REPO_ROOT)} in {elapsed_s:.1f}s")
    print(f"[Exp137] Verdict: {evaluation['n_pass']}/{evaluation['n_total']} ({evaluation['overall_verdict']})")
    for k, v in evaluation["predictions"].items():
        print(f"  - {k}: {v['verdict']} -> {v['measured']}")
    return result_doc


if __name__ == "__main__":
    main()
