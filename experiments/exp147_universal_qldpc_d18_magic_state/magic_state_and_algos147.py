"""Exp147 Module 2: Universal qLDPC Pauli-Based Computation, Magic State Factories
(Litinski 15-to-1, Two-Stage (15-to-1)x(116-to-12), Gidney 2024 Cultivation + Distillation),
and Full Resource / Cryostat / Power / Runtime / TCO Budgets for FeMoco & RSA-2048 Shor.

Anchored directly to Exp140 (2,887 MXC cell cap, N_mux*=32), Exp141 (wafer_econ141.py exact
MC TCO model), Exp143 (D3 GRAPE p_2q=0.337%/0.395%, Lambda_SC=2.825, T_cyc,SC=6.702 us,
Option-HPC 2.195 kW/4U), and Exp144/Exp147 BB qLDPC codes.

Strictly portable (Path(__file__).resolve() only; zero hardcoded host paths).
Epistemic scope: {Model} / {Literatur} / {Varsayim}. no_lab_measurement=True, no_supplier_quotes=True.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.exp141_v5_digital_twin.wafer_econ141 import (  # noqa: E402
    EXP140_CRYO_CELL_CAP_THERMAL,
    EXP140_RO_MUX_RATIO,
    EXP140_S65_MUX_1024_USD,
    HORIZON_YR,
    RUNTIME_CRYOSTAT_BAY_HW_USD,
    V5_M3_HW_NOM_USD,
    _sample_lognormal_p10_p50_p90,
    evaluate_v5_wafer_economics,
    wright_multiplier,
)


# =============================================================================
# 1. Surface-Code Clifford Floor & Magic State Factory Optimizer
# =============================================================================
def sc_per_round_err(d: int, a_sc: float, lambda_sc: float) -> float:
    """Empirical rotated surface-code combined Z+X logical error per round (Exp138/143)."""
    return float(a_sc * (lambda_sc ** (-0.5 * (d + 1))))


def min_sc_distance_for_target(eps_target: float, a_sc: float, lambda_sc: float, d_min: int = 5, d_max: int = 99) -> int:
    """Smallest odd surface-code distance d achieving eps_SC(d) <= eps_target."""
    for d in range(d_min, d_max + 1, 2):
        if sc_per_round_err(d, a_sc, lambda_sc) <= eps_target:
            return d
    return d_max


def compact_15to1_cells(d_x: int, d_z: int) -> int:
    """Active physical cells for Litinski (Quantum 3, 205, 2019, Fig. 6) compact 11-tile
    asymmetric (15-to-1)_{d_X, d_Z, d_m} factory (11*d_m rounds per output state):
      1 output patch (d_X^2) + 4 distillation qubits (4 * d_X * d_Z) + 6 routing/ancilla patches (6 * d_Z^2),
      multiplied by 2 for data + ancilla physical cells per rotated SC patch.
    """
    return int(2 * (d_x * d_x + 4 * d_x * d_z + 6 * d_z * d_z))


def fast_15to1_cells(d_x: int, d_z: int) -> int:
    """Active physical cells for Litinski (Quantum 3, 205, 2019, Fig. 4 / Table 1) fast 6*d_m
    (15-to-1)_{d_X, d_Z, d_m} factory: 2 * (d_X + 4*d_Z) * (3*d_X) physical qubits.
    """
    return int(2 * (d_x + 4 * d_z) * (3 * d_x))


def compact_116to12_cells(d_x: int, d_z: int) -> int:
    """Active physical cells for Litinski (Quantum 3, 205, 2019, Section 4) (116-to-12)
    triorthogonal [[116,12,4]] factory (11*d_m rounds -> 12 distilled |T> states):
      12 output distillation patches (12 * d_X * d_Z) + 32 routing/ancilla tiles (32 * d_Z^2),
      multiplied by 2 for data + ancilla physical cells.
    """
    return int(2 * (12 * d_x * d_z + 32 * d_z * d_z))


def evaluate_15to1_stage(
    p_in: float,
    d_x: int,
    d_z: int,
    d_m: int,
    a_sc: float,
    lambda_sc: float,
    t_cyc_sc_us: float,
    variant: str = "compact",
) -> Dict[str, Any]:
    """Exact Litinski (2019) single-stage (15-to-1)_{d_X, d_Z, d_m} error & footprint.

    variant='compact' (Litinski Fig. 6): 11*d_m rounds, compact_15to1_cells(d_x, d_z).
    variant='fast'    (Litinski Fig. 4):  6*d_m rounds, fast_15to1_cells(d_x, d_z).
    Strictly pairs each variant's exact space footprint with its exact time depth (zero mixing).
    """
    eps_x = 0.5 * sc_per_round_err(d_x, a_sc, lambda_sc)
    eps_z = 0.5 * sc_per_round_err(d_z, a_sc, lambda_sc)
    eps_m = 0.5 * sc_per_round_err(d_m, a_sc, lambda_sc)

    if variant == "fast":
        n_rounds = 6 * d_m
        cells = fast_15to1_cells(d_x, d_z)
    else:
        n_rounds = 11 * d_m
        cells = compact_15to1_cells(d_x, d_z)

    p_cliff_x_out = n_rounds * eps_x
    p_in_eff = p_in + (n_rounds * eps_z) + (15.0 * eps_m)
    p_distill = 35.0 * (p_in_eff ** 3)
    p_out = p_distill + p_cliff_x_out

    p_accept = max(0.5, (1.0 - p_in_eff) ** 15)
    t_cycle_us = (n_rounds * t_cyc_sc_us) / p_accept
    rate_khz = 1000.0 / t_cycle_us
    cryos = math.ceil(cells / EXP140_CRYO_CELL_CAP_THERMAL)

    return {
        "variant": variant,
        "d_X": d_x,
        "d_Z": d_z,
        "d_m": d_m,
        "n_rounds": n_rounds,
        "p_in": p_in,
        "p_in_eff": p_in_eff,
        "p_distill_35p3": p_distill,
        "p_clifford_x_out": p_cliff_x_out,
        "p_out": p_out,
        "p_accept": round(p_accept, 5),
        "t_cycle_us": round(t_cycle_us, 2),
        "rate_khz": round(rate_khz, 3),
        "active_cells": cells,
        "cryostats_ld400": cryos,
    }


def evaluate_116to12_stage(
    p_in: float,
    d_x: int,
    d_z: int,
    d_m: int,
    a_sc: float,
    lambda_sc: float,
    t_cyc_sc_us: float,
) -> Dict[str, Any]:
    """Exact Litinski (2019) Section 4 (116-to-12) triorthogonal [[116,12,4]] stage:
    Produces 12 distilled |T> states every 11*d_m cycles with p_out_block = 41.25 * p_in^4
    (per-output error = 3.4375 * p_in^4 + Clifford X-floor per output patch).
    """
    eps_x = 0.5 * sc_per_round_err(d_x, a_sc, lambda_sc)
    eps_z = 0.5 * sc_per_round_err(d_z, a_sc, lambda_sc)
    eps_m = 0.5 * sc_per_round_err(d_m, a_sc, lambda_sc)

    n_rounds = 11 * d_m
    p_cliff_x_per_t = n_rounds * eps_x
    p_in_eff = p_in + (n_rounds * eps_z) + (116.0 * eps_m)
    p_distill_per_t = (41.25 / 12.0) * (p_in_eff ** 4)
    p_out_per_t = p_distill_per_t + p_cliff_x_per_t

    p_accept = max(0.5, (1.0 - p_in_eff) ** 116)
    t_cycle_us = (n_rounds * t_cyc_sc_us) / p_accept
    rate_khz = (12.0 * 1000.0) / t_cycle_us  # 12 states per cycle!
    cells = compact_116to12_cells(d_x, d_z)
    cryos = math.ceil(cells / EXP140_CRYO_CELL_CAP_THERMAL)

    return {
        "d_X": d_x,
        "d_Z": d_z,
        "d_m": d_m,
        "n_rounds": n_rounds,
        "p_in": p_in,
        "p_in_eff": p_in_eff,
        "p_distill_per_t": p_distill_per_t,
        "p_clifford_x_per_t": p_cliff_x_per_t,
        "p_out": p_out_per_t,
        "p_accept": round(p_accept, 5),
        "t_cycle_us": round(t_cycle_us, 2),
        "rate_khz": round(rate_khz, 3),
        "active_cells": cells,
        "cryostats_ld400": cryos,
    }


def optimize_magic_state_factories(
    p_2q: float,
    p_1q: float,
    a_sc: float,
    lambda_sc: float,
    t_cyc_sc_us: float,
    p_target: float = 1e-10,
) -> Dict[str, Any]:
    """Evaluate and optimize 4 physical Magic State Factory architectures on silicon M4 hardware:
      F1: Single-stage Litinski 15-to-1 from raw injection (proves honest inability to hit 1e-10 at D3)
      F2: Pure Litinski Two-Stage (15-to-1)^M x (116-to-12) (no cultivation assumption; hits p_T <= 1e-10)
      F3: Gidney (2024) Cultivation (d_c=5, p_cult=1e-4) + Single-Stage Compact 15-to-1 (<= 6 cryostats!)
      F4: Gidney (2024) Cultivation (d_c=5, p_cult=1e-4) + Single-Stage (116-to-12) (high-throughput!)
    """
    # Conservative raw injection error (un-postselected Li 2015: p_in = p_2q + p_1q)
    p_in_raw = p_2q + p_1q
    # Post-selected Li 2015 injection sensitivity (~0.6 * p_2q)
    p_in_ps = 0.6 * p_2q

    # F1: Single-stage 15-to-1 (even with arbitrarily large Clifford distances, 35 * p_in^3 sets a hard wall!)
    f1_raw = evaluate_15to1_stage(p_in_raw, d_x=35, d_z=19, d_m=15, a_sc=a_sc, lambda_sc=lambda_sc, t_cyc_sc_us=t_cyc_sc_us, variant="compact")
    f1_ps = evaluate_15to1_stage(p_in_ps, d_x=35, d_z=19, d_m=15, a_sc=a_sc, lambda_sc=lambda_sc, t_cyc_sc_us=t_cyc_sc_us, variant="compact")

    # F2: Pure Litinski Two-Stage: optimize Stage-1 (15-to-1) x Stage-2 (116-to-12) for p_T <= p_target & R_T >= 5 kHz
    best_f2 = None
    for s1_var in ("compact", "fast"):
        for d1_x in (11, 13, 15):
            for d1_z in (5, 7):
                s1 = evaluate_15to1_stage(p_in_raw, d1_x, d1_z, d1_z, a_sc, lambda_sc, t_cyc_sc_us, variant=s1_var)
                if s1["p_out"] > 2e-4:
                    continue
                for d2_x in range(39, 65, 2):
                    for d2_z in (13, 15, 17, 19, 21):
                        for d2_m in (13, 15, 17):
                            s2 = evaluate_116to12_stage(s1["p_out"], d2_x, d2_z, d2_m, a_sc, lambda_sc, t_cyc_sc_us)
                            if s2["p_out"] > p_target:
                                continue
                            r_goal = min(5.05, s2["rate_khz"])
                            n_s1 = max(1, math.ceil((r_goal * 116.0 / 12.0) / s1["rate_khz"]))
                            r_comb = min(s2["rate_khz"], n_s1 * s1["rate_khz"] * (12.0 / 116.0))
                            if r_comb < 5.0:
                                continue
                            tot_cells = n_s1 * s1["active_cells"] + s2["active_cells"]
                            tot_cryos = math.ceil(tot_cells / EXP140_CRYO_CELL_CAP_THERMAL)
                            cand = {
                                "name": f"Litinski Two-Stage ({s1_var} 15-to-1)^{n_s1}_{{{d1_x},{d1_z},{d1_z}}} x (116-to-12)_{{{d2_x},{d2_z},{d2_m}}}",
                                "n_stage1_tiles": n_s1,
                                "stage1": s1,
                                "stage2": s2,
                                "p_T": s2["p_out"],
                                "rate_khz": round(r_comb, 3),
                                "time_per_T_us": round(1000.0 / r_comb, 2),
                                "active_cells": tot_cells,
                                "cryostats_ld400": tot_cryos,
                                "meets_1e10": bool(s2["p_out"] <= p_target),
                            }
                            if best_f2 is None or (tot_cryos, tot_cells) < (best_f2["cryostats_ld400"], best_f2["active_cells"]):
                                best_f2 = cand

    # F3: Gidney-Shutty-Jones (2024, arXiv:2409.17595) Magic State Cultivation (d_c=5 color code,
    # ~110 active cells/patch, ~15 rounds, ~10% post-selection survival at p~0.34% -> conservative p_cult=1.0e-4)
    # + Single-Stage Compact (15-to-1)
    p_cult_conservative = 1.0e-4  # {Literatur}/{Varsayim}: conservative bound at p_2q ~ 0.34-0.40%
    cult_cells_per_patch = 110
    cult_rate_per_patch_khz = (0.10 * 1000.0) / (15.0 * t_cyc_sc_us)

    best_f3 = None
    for d_x in range(39, 65, 2):
        for d_z in (15, 17, 19, 21, 23):
            for d_m in (11, 13, 15, 17):
                st = evaluate_15to1_stage(p_cult_conservative, d_x, d_z, d_m, a_sc, lambda_sc, t_cyc_sc_us, variant="compact")
                if st["p_out"] > p_target:
                    continue
                n_cult = max(1, math.ceil((15.0 * st["rate_khz"]) / cult_rate_per_patch_khz))
                cult_cells = n_cult * cult_cells_per_patch
                tot_cells = st["active_cells"] + cult_cells
                tot_cryos = math.ceil(tot_cells / EXP140_CRYO_CELL_CAP_THERMAL)
                cand = {
                    "name": f"Gidney Cultivation (p_cult=1e-4, {n_cult}x d=5) + compact (15-to-1)_{{{d_x},{d_z},{d_m}}}",
                    "p_cult_input": p_cult_conservative,
                    "n_cult_patches": n_cult,
                    "cult_active_cells": cult_cells,
                    "distill_stage": st,
                    "p_T": st["p_out"],
                    "rate_khz": st["rate_khz"],
                    "time_per_T_us": round(1000.0 / st["rate_khz"], 2),
                    "active_cells": tot_cells,
                    "cryostats_ld400": tot_cryos,
                    "meets_1e10": bool(st["p_out"] <= p_target),
                }
                if best_f3 is None or (tot_cryos, tot_cells) < (best_f3["cryostats_ld400"], best_f3["active_cells"]):
                    best_f3 = cand

    # F4: Gidney Cultivation (p_cult=1e-4) + Single-Stage (116-to-12) (Ultra-high throughput >= 10 kHz!)
    best_f4 = None
    for d_x in range(39, 65, 2):
        for d_z in (13, 15, 17, 19, 21):
            for d_m in (13, 15, 17):
                st = evaluate_116to12_stage(p_cult_conservative, d_x, d_z, d_m, a_sc, lambda_sc, t_cyc_sc_us)
                if st["p_out"] > p_target:
                    continue
                # Need enough cultivation patches to supply 116 states per cycle -> 116 * (rate_khz / 12)
                n_cult = max(1, math.ceil((st["rate_khz"] * (116.0 / 12.0)) / cult_rate_per_patch_khz))
                cult_cells = n_cult * cult_cells_per_patch
                tot_cells = st["active_cells"] + cult_cells
                tot_cryos = math.ceil(tot_cells / EXP140_CRYO_CELL_CAP_THERMAL)
                cand = {
                    "name": f"Gidney Cultivation (p_cult=1e-4, {n_cult}x d=5) + (116-to-12)_{{{d_x},{d_z},{d_m}}}",
                    "p_cult_input": p_cult_conservative,
                    "n_cult_patches": n_cult,
                    "cult_active_cells": cult_cells,
                    "distill_stage": st,
                    "p_T": st["p_out"],
                    "rate_khz": st["rate_khz"],
                    "time_per_T_us": round(1000.0 / st["rate_khz"], 2),
                    "active_cells": tot_cells,
                    "cryostats_ld400": tot_cryos,
                    "meets_1e10": bool(st["p_out"] <= p_target),
                }
                if best_f4 is None or (tot_cryos, tot_cells) < (best_f4["cryostats_ld400"], best_f4["active_cells"]):
                    best_f4 = cand

    return {
        "inputs": {
            "p_2q": p_2q,
            "p_1q": p_1q,
            "p_in_raw": round(p_in_raw, 6),
            "p_in_postselected": round(p_in_ps, 6),
            "A_SC": a_sc,
            "Lambda_SC": lambda_sc,
            "T_cyc_SC_us": round(t_cyc_sc_us, 4),
            "p_T_target": p_target,
        },
        "F1_single_stage_15to1_raw": {**f1_raw, "meets_1e10": bool(f1_raw["p_out"] <= p_target)},
        "F1b_single_stage_15to1_postselected": {**f1_ps, "meets_1e10": bool(f1_ps["p_out"] <= p_target)},
        "F2_litinski_twostage_15to1_x_116to12": best_f2,
        "F3_gidney_cultivation_plus_15to1_compact": best_f3,
        "F4_gidney_cultivation_plus_116to12_highthroughput": best_f4,
    }


# =============================================================================
# 2. Exact Exp141 System TCO Evaluator for Arbitrary Deployed Cryostat Fleets
# =============================================================================
def compute_system_tco_exp141(
    n_cryostats: int,
    total_active_cells: int,
    n_cand_avg: float,
    n_hpc_4u_modules: int,
    wafer_econ: Dict[str, Any],
    wright_b: float = 0.85,
    n_mc: int = 20_000,
    seed: int = 2026147,
) -> Dict[str, Any]:
    """Exact Exp141 wafer_econ141.py 5-year deployed TCO (CAPEX + installation + facility + 5yr OPEX
    + W3 silicon chips + Exp143 Option-HPC 4U decoder modules at $132k nom, 2.195 kW/module).
    """
    rng = np.random.default_rng(seed)
    cryo_hw_s = _sample_lognormal_p10_p50_p90(rng, *RUNTIME_CRYOSTAT_BAY_HW_USD, n_mc)
    mux_1024_s = _sample_lognormal_p10_p50_p90(rng, *EXP140_S65_MUX_1024_USD, n_mc)
    hpc_4u_s = _sample_lognormal_p10_p50_p90(rng, 98_000.0, 132_000.0, 181_000.0, n_mc)  # Exp143 exact
    install_s = _sample_lognormal_p10_p50_p90(rng, 1.20, 1.35, 1.55, n_mc)
    maint_s = _sample_lognormal_p10_p50_p90(rng, 0.06, 0.08, 0.11, n_mc)

    elec_price = _sample_lognormal_p10_p50_p90(rng, 0.09, 0.14, 0.22, n_mc)
    cryo_opex_yr = (
        rng.uniform(20.0, 30.0, size=n_mc) * 8760.0 * elec_price
        + _sample_lognormal_p10_p50_p90(rng, 30_000.0, 45_000.0, 70_000.0, n_mc)
        + _sample_lognormal_p10_p50_p90(rng, 0.35, 0.50, 0.75, n_mc) * 160_000.0
    )
    hpc_power_kw = n_hpc_4u_modules * 2.195
    hpc_elec_yr = hpc_power_kw * 8760.0 * elec_price

    n_ro_chains = math.ceil(total_active_cells / EXP140_RO_MUX_RATIO)
    n_mux_1024 = n_ro_chains / 32.0
    w_cryo = wright_multiplier(max(1, n_cryostats), wright_b)
    w_mux = wright_multiplier(max(1.0, n_mux_1024), wright_b)
    w_hpc = wright_multiplier(max(1, n_hpc_4u_modules), wright_b)

    hw_wr = (
        n_cryostats * cryo_hw_s * w_cryo
        + n_mux_1024 * mux_1024_s * w_mux
        + n_hpc_4u_modules * hpc_4u_s * w_hpc
    )
    facility = 1_200_000.0 + 350_000.0 * n_cryostats

    usd_reg_w3 = wafer_econ["scenarios"]["W3"]["v5_0_dense_1h_15ms"]["usd_per_register_nom_wafer_p50"]
    chips_w3_usd = total_active_cells * n_cand_avg * usd_reg_w3 * 5.0  # 5x qualification spares

    opex_5yr = HORIZON_YR * (n_cryostats * cryo_opex_yr + hpc_elec_yr + maint_s * hw_wr)
    tco5_usd = install_s * hw_wr + facility + opex_5yr + chips_w3_usd

    q10, q50, q90 = np.percentile(tco5_usd, [10.0, 50.0, 90.0])
    total_power_kw = n_cryostats * 25.0 + hpc_power_kw

    return {
        "n_cryostats": n_cryostats,
        "n_readout_chains": n_ro_chains,
        "n_hpc_4u_modules": n_hpc_4u_modules,
        "total_facility_power_kw": round(total_power_kw, 2),
        "total_facility_power_mw": round(total_power_kw / 1000.0, 4),
        "chips_w3_usd_p50": round(chips_w3_usd, 2),
        "tco5_usd_p10": round(float(q10), 2),
        "tco5_usd_p50": round(float(q50), 2),
        "tco5_usd_p90": round(float(q90), 2),
        "tco5_musd_p50": round(float(q50) / 1e6, 3),
    }


# =============================================================================
# 3. Full Flagship Algorithm Budgets: FeMoco Chemistry & RSA-2048 Shor
# =============================================================================
def evaluate_flagship_algorithms(
    factories: Dict[str, Any],
    p_L_round_1L_bb288_d3: float,
    p_L_round_1L_bb288_d3pp: float,
    p_L_round_1L_bb360_d24_d3: float,
    t_cyc_bb_us: float,
    a_sc: float,
    lambda_sc: float,
    t_cyc_sc_us: float,
    n_mc: int = 20_000,
) -> Dict[str, Any]:
    """Compute exact end-to-end hardware, runtime, error-budget, power, and TCO budgets for:
      (A) FeMoco Nitrogen-Fixation Catalyst (192L, 1.0e8 T-gates + Lee 2021 2,142L/1.28e11 T sensitivity)
      (B) 2048-Bit RSA / Shor's Algorithm (4,096L, 1.0e10 T-gates + honest space-time volume audit)
    Comparing qLDPC [[288,12,18]] + Magic State Factories vs Exp138/143 D3 Surface Code.
    """
    wafer_econ = evaluate_v5_wafer_economics(bom_v5_m3=V5_M3_HW_NOM_USD, n_mc=n_mc, seed=2026146)
    f2_lit = factories["F2_litinski_twostage_15to1_x_116to12"]
    f4_cult = factories["F4_gidney_cultivation_plus_116to12_highthroughput"]
    f3_cult_comp = factories["F3_gidney_cultivation_plus_15to1_compact"]

    # 5-year effective productive runtime at 70% cryostat+calibration uptime
    productive_hours_5yr = HORIZON_YR * 8760.0 * 0.70  # 30,660 hours

    # -------------------------------------------------------------------------
    # ALGORITHM A: FeMoco Nitrogen-Fixation Catalyst (192L, 1.0e8 T-gates)
    # -------------------------------------------------------------------------
    femoco_L = 192  # 16 blocks x 12L = 192 logical qubits (covers 54-76 orb active space + QPE/QROM workspace)
    femoco_T = 1.0e8  # Canonical 10^8 T-gates (Reiher 2017 / Berry 2019 double-factorized QPE)

    def _build_femoco_arch(
        label: str,
        mem_cells: int,
        mem_cryos: int,
        routing_cells: int,
        factory: Dict[str, Any],
        n_factories: int,
        p_L_mem_1L: float,
        t_cyc_mem_us: float,
        n_cand_avg: float,
        hpc_modules: int,
        seed: int,
    ) -> Dict[str, Any]:
        # Magic-state consumption speed vs qLDPC lattice-surgery reaction speed:
        # Reaction / Pauli-measurement time per serial T-layer ~ 1*d_mem or pipelined 1*T_cyc_mem;
        # With auto-CCZ / Pauli-based teleportation, execution is factory-rate limited when T-depth ~ 10^8!
        r_T_total_khz = n_factories * factory["rate_khz"]
        runtime_s = femoco_T / (r_T_total_khz * 1000.0)
        runtime_hr = runtime_s / 3600.0
        n_mem_rounds = runtime_s / (t_cyc_mem_us * 1e-6)
        st_vol = femoco_L * n_mem_rounds

        # Exact error budget: memory failure + factory failure
        p_fail_mem = 1.0 - math.exp(-st_vol * p_L_mem_1L)
        p_fail_fac = 1.0 - math.exp(-femoco_T * factory["p_T"])
        p_fail_tot = 1.0 - (1.0 - p_fail_mem) * (1.0 - p_fail_fac)

        fac_cells = n_factories * factory["active_cells"]
        tot_cells = mem_cells + routing_cells + fac_cells
        # Keep memory+routing cryostats cleanly separated from factory cryostats (modular!)
        mem_route_cryos = max(mem_cryos, math.ceil((mem_cells + routing_cells) / EXP140_CRYO_CELL_CAP_THERMAL))
        fac_cryos = n_factories * factory["cryostats_ld400"]
        tot_cryos = mem_route_cryos + fac_cryos

        tco = compute_system_tco_exp141(
            n_cryostats=tot_cryos,
            total_active_cells=tot_cells,
            n_cand_avg=n_cand_avg,
            n_hpc_4u_modules=hpc_modules,
            wafer_econ=wafer_econ,
            n_mc=n_mc,
            seed=seed,
        )
        solves_5yr = productive_hours_5yr / max(runtime_hr, 1e-6)
        cost_per_solve = tco["tco5_usd_p50"] / max(solves_5yr, 1.0)
        return {
            "label": label,
            "n_logical": femoco_L,
            "n_T_gates": femoco_T,
            "mem_active_cells": mem_cells,
            "routing_active_cells": routing_cells,
            "factory_name": factory["name"],
            "n_factories": n_factories,
            "factory_active_cells": fac_cells,
            "total_active_cells": tot_cells,
            "mem_route_cryostats": mem_route_cryos,
            "factory_cryostats": fac_cryos,
            "total_cryostats_ld400": tot_cryos,
            "R_T_total_khz": round(r_T_total_khz, 3),
            "runtime_hours": round(runtime_hr, 3),
            "n_memory_rounds": round(n_mem_rounds, 1),
            "spacetime_volume_L_rounds": float(st_vol),
            "p_fail_memory": float(p_fail_mem),
            "p_fail_factory": float(p_fail_fac),
            "p_fail_total": float(p_fail_tot),
            "tco_and_power": tco,
            "solves_per_5yr_70pct_uptime": round(solves_5yr, 1),
            "cost_per_solve_usd_p50": round(cost_per_solve, 2),
        }

    # FeMoco 1: [[288,12,18]] + 1 Pure Litinski Two-Stage Factory (ZERO cultivation assumption!)
    # 16 memory blocks (9,216 cells) + 2 routing/surgery blocks (1,152 cells) = 10,368 cells -> 4 LD400 cryostats
    femoco_qldpc_lit = _build_femoco_arch(
        label="qLDPC [[288,12,18]] + 1x Litinski (15-to-1)x(116-to-12)",
        mem_cells=16 * 576,
        mem_cryos=4,
        routing_cells=2 * 576,
        factory=f2_lit,
        n_factories=1,
        p_L_mem_1L=p_L_round_1L_bb288_d3,
        t_cyc_mem_us=t_cyc_bb_us,
        n_cand_avg=8.0,  # N_cand=8/9 on qLDPC, 6 on SC factory -> conservative 8.0 avg
        hpc_modules=3,   # 2x for 16 qLDPC blocks + 1x for factory MWPM
        seed=2026151,
    )

    # FeMoco 2: [[288,12,18]] + 1 Gidney Cultivation + (116-to-12) Factory
    femoco_qldpc_cult_fast = _build_femoco_arch(
        label="qLDPC [[288,12,18]] + 1x Gidney Cult + (116-to-12)",
        mem_cells=16 * 576,
        mem_cryos=4,
        routing_cells=2 * 576,
        factory=f4_cult,
        n_factories=1,
        p_L_mem_1L=p_L_round_1L_bb288_d3,
        t_cyc_mem_us=t_cyc_bb_us,
        n_cand_avg=8.0,
        hpc_modules=3,
        seed=2026152,
    )

    # FeMoco 3: [[288,12,18]] + 1 Ultra-Compact Gidney Cultivation + (15-to-1) Factory (minimum cryostats!)
    femoco_qldpc_cult_min = _build_femoco_arch(
        label="qLDPC [[288,12,18]] + 2x Gidney Cult + Compact (15-to-1)",
        mem_cells=16 * 576,
        mem_cryos=4,
        routing_cells=2 * 576,
        factory=f3_cult_comp,
        n_factories=2,
        p_L_mem_1L=p_L_round_1L_bb288_d3,
        t_cyc_mem_us=t_cyc_bb_us,
        n_cand_avg=8.0,
        hpc_modules=3,
        seed=2026153,
    )

    # FeMoco Baseline: Exp138/143 D3 Surface Code (192L, p_fail_mem <= 1% over V_ST ~ 5e11 -> eps_SC <= 2e-14?
    # Let's compute exact required odd d_SC for P_mem <= 1% over 192L x ~3e9 rounds = 5.8e11 L-rounds -> eps <= 1.7e-14 -> d=33..37!)
    # Check at T_cyc_SC=6.70 us, runtime ~5.4h = 2.9e9 rounds * 192L = 5.6e11 L-rounds -> eps_SC <= 1.8e-14 -> d_SC:
    # Actually even at Exp143's canonical 1e-9 target (d=33, 2,177 cells/L, 1 patch per cryostat since 2,177 > 2,887/2),
    # let's compute exact d_SC for P_mem <= 0.01 honestly:
    est_sc_rounds_femoco = (femoco_T / (f2_lit["rate_khz"] * 1000.0)) / (t_cyc_sc_us * 1e-6)
    eps_req_femoco_sc = 0.01 / (femoco_L * est_sc_rounds_femoco)
    d_sc_femoco = min_sc_distance_for_target(eps_req_femoco_sc, a_sc, lambda_sc, d_min=25, d_max=61)
    sc_cells_per_L_femoco = 2 * d_sc_femoco * d_sc_femoco - 1
    # Unsplit patch packing (Exp141 convention):
    sc_L_per_cryo = max(1, EXP140_CRYO_CELL_CAP_THERMAL // sc_cells_per_L_femoco)
    sc_mem_cells_femoco = femoco_L * sc_cells_per_L_femoco
    sc_route_cells_femoco = int(0.50 * sc_mem_cells_femoco)  # Litinski standard 50% surface-code routing overhead
    sc_mem_cryos_femoco = (
        math.ceil((femoco_L * 1.5) / sc_L_per_cryo)
        if sc_cells_per_L_femoco <= EXP140_CRYO_CELL_CAP_THERMAL
        else math.ceil((sc_mem_cells_femoco + sc_route_cells_femoco) / EXP140_CRYO_CELL_CAP_THERMAL)
    )
    femoco_sc_baseline = _build_femoco_arch(
        label=f"Exp143 D3 Surface Code (d={d_sc_femoco}) + 1x Litinski Two-Stage",
        mem_cells=sc_mem_cells_femoco,
        mem_cryos=sc_mem_cryos_femoco,
        routing_cells=sc_route_cells_femoco,
        factory=f2_lit,
        n_factories=1,
        p_L_mem_1L=sc_per_round_err(d_sc_femoco, a_sc, lambda_sc),
        t_cyc_mem_us=t_cyc_sc_us,
        n_cand_avg=6.0,
        hpc_modules=14,  # Exp143: 7x 4U per 100L -> ~14x 4U for 192L
        seed=2026154,
    )
    femoco_sc_baseline["d_surface_code"] = d_sc_femoco

    # Sensitivity note: Lee et al. (PRX Quantum 2021) full 76-orb Li active space (2,142L, 3.2e10 Toffoli = 1.28e11 T)
    lee21_T = 1.28e11
    lee21_blocks = math.ceil(2142 / 12)  # 179 blocks
    lee21_mem_cryos = math.ceil((lee21_blocks * 576 * 1.15) / EXP140_CRYO_CELL_CAP_THERMAL)  # 42 cryos
    lee21_n_fac = 16  # 16 parallel Cultivation+(116-to-12) -> 200 kHz -> 178 hours (~7.4 days)
    lee21_runtime_days = (lee21_T / (lee21_n_fac * f4_cult["rate_khz"] * 1000.0)) / 86400.0

    # -------------------------------------------------------------------------
    # ALGORITHM B: 2048-Bit RSA / Shor's Algorithm (4,096L, 1.0e10 T-gates)
    # -------------------------------------------------------------------------
    rsa_L = 4096
    rsa_T = 1.0e10  # Canonical 10^10 T-gates (Gidney & Ekera 2021: 2.7B Toffoli ~ 1.08e10 T)

    def _build_rsa_arch(
        label: str,
        code_label: str,
        mem_cells: int,
        mem_cryos: int,
        routing_cells: int,
        factory: Dict[str, Any],
        n_factories: int,
        p_L_mem_1L: float,
        t_cyc_mem_us: float,
        n_cand_avg: float,
        hpc_modules: int,
        seed: int,
    ) -> Dict[str, Any]:
        r_T_total_khz = n_factories * factory["rate_khz"]
        runtime_s = rsa_T / (r_T_total_khz * 1000.0)
        runtime_hr = runtime_s / 3600.0
        n_mem_rounds = runtime_s / (t_cyc_mem_us * 1e-6)
        st_vol = rsa_L * n_mem_rounds

        p_fail_mem = 1.0 - math.exp(-st_vol * p_L_mem_1L)
        p_fail_fac = 1.0 - math.exp(-rsa_T * factory["p_T"])
        p_fail_tot = 1.0 - (1.0 - p_fail_mem) * (1.0 - p_fail_fac)

        fac_cells = n_factories * factory["active_cells"]
        tot_cells = mem_cells + routing_cells + fac_cells
        mem_route_cryos = max(mem_cryos, math.ceil((mem_cells + routing_cells) / EXP140_CRYO_CELL_CAP_THERMAL))
        fac_cryos = n_factories * factory["cryostats_ld400"]
        tot_cryos = mem_route_cryos + fac_cryos

        tco = compute_system_tco_exp141(
            n_cryostats=tot_cryos,
            total_active_cells=tot_cells,
            n_cand_avg=n_cand_avg,
            n_hpc_4u_modules=hpc_modules,
            wafer_econ=wafer_econ,
            n_mc=n_mc,
            seed=seed,
        )
        return {
            "label": label,
            "code_label": code_label,
            "n_logical": rsa_L,
            "n_T_gates": rsa_T,
            "mem_active_cells": mem_cells,
            "routing_active_cells": routing_cells,
            "factory_name": factory["name"],
            "n_factories": n_factories,
            "factory_active_cells": fac_cells,
            "total_active_cells": tot_cells,
            "mem_route_cryostats": mem_route_cryos,
            "factory_cryostats": fac_cryos,
            "total_cryostats_ld400": tot_cryos,
            "R_T_total_khz": round(r_T_total_khz, 2),
            "runtime_hours": round(runtime_hr, 2),
            "runtime_days": round(runtime_hr / 24.0, 3),
            "n_memory_rounds": float(n_mem_rounds),
            "spacetime_volume_L_rounds": float(st_vol),
            "p_L_mem_1L_used": float(p_L_mem_1L),
            "p_fail_memory": float(p_fail_mem),
            "p_fail_factory": float(p_fail_fac),
            "p_fail_total": float(p_fail_tot),
            "tco_and_power": tco,
        }

    # RSA 1: [[288,12,18]] (342 blocks = 4,104L) + 16x Litinski Two-Stage (honest D3 vs D3++ memory audit!)
    rsa_bb288_blocks = math.ceil(rsa_L / 12)  # 342
    rsa_bb288_mem_cells = rsa_bb288_blocks * 576  # 196,992
    rsa_bb288_route_cells = int(0.15 * rsa_bb288_mem_cells)  # 29,549
    rsa_bb288_mem_cryos = math.ceil((rsa_bb288_mem_cells + rsa_bb288_route_cells) / EXP140_CRYO_CELL_CAP_THERMAL)  # 79

    # Note: 16x Litinski (15-to-1)x(116-to-12) gives R_T ~ 82 kHz -> 33.8 hr; with p_T ~ 5e-11, 10^10 T -> p_fac ~ 0.40
    # (acceptable for Shor retry!), OR with p_T <= 1e-11 (d_X=49 -> +1 cryo) p_fac <= 0.10! Let's check exact p_fail!
    rsa_qldpc_d18_lit_d3pp = _build_rsa_arch(
        label="qLDPC [[288,12,18]] (D3++ 0.20%) + 16x Litinski Two-Stage",
        code_label="[[288,12,18]] @ D3++ (p_2q=0.20%)",
        mem_cells=rsa_bb288_mem_cells,
        mem_cryos=rsa_bb288_mem_cryos,
        routing_cells=rsa_bb288_route_cells,
        factory=f2_lit,
        n_factories=16,
        p_L_mem_1L=p_L_round_1L_bb288_d3pp,
        t_cyc_mem_us=t_cyc_bb_us,
        n_cand_avg=8.0,
        hpc_modules=40,
        seed=2026161,
    )

    # RSA 2: Honest D3 (0.337%) upgrade to d=24 [[360,12,24]] (720 cells/blk -> 99 memory cryos) + 16x Gidney Cult+(116-to-12)
    rsa_bb360_mem_cells = rsa_bb288_blocks * 720  # 246,240
    rsa_bb360_route_cells = int(0.15 * rsa_bb360_mem_cells)
    rsa_bb360_mem_cryos = math.ceil((rsa_bb360_mem_cells + rsa_bb360_route_cells) / EXP140_CRYO_CELL_CAP_THERMAL)  # 99

    rsa_qldpc_d24_cult_d3 = _build_rsa_arch(
        label="qLDPC [[360,12,24]] (D3 0.337%) + 16x Gidney Cult+(116-to-12)",
        code_label="[[360,12,24]] @ D3 (p_2q=0.337%)",
        mem_cells=rsa_bb360_mem_cells,
        mem_cryos=rsa_bb360_mem_cryos,
        routing_cells=rsa_bb360_route_cells,
        factory=f4_cult,
        n_factories=16,
        p_L_mem_1L=p_L_round_1L_bb360_d24_d3,
        t_cyc_mem_us=t_cyc_bb_us,
        n_cand_avg=9.0,
        hpc_modules=45,
        seed=2026162,
    )

    # RSA 2b: Also check [[288,12,18]] at D3 (0.337%) transparently (honest space-time audit!)
    rsa_qldpc_d18_cult_d3_audit = _build_rsa_arch(
        label="qLDPC [[288,12,18]] (D3 0.337% Audit) + 16x Gidney Cult+(116-to-12)",
        code_label="[[288,12,18]] @ D3 (0.337%, honest ST audit)",
        mem_cells=rsa_bb288_mem_cells,
        mem_cryos=rsa_bb288_mem_cryos,
        routing_cells=rsa_bb288_route_cells,
        factory=f4_cult,
        n_factories=16,
        p_L_mem_1L=p_L_round_1L_bb288_d3,
        t_cyc_mem_us=t_cyc_bb_us,
        n_cand_avg=8.0,
        hpc_modules=40,
        seed=2026163,
    )

    # RSA Baseline: Exp143 D3 Surface Code (4,096L, V_ST ~ 5e13 L-rounds -> requires eps_SC <= 2e-15 -> d_SC ~ 49!)
    est_sc_rounds_rsa = (rsa_T / (16 * f2_lit["rate_khz"] * 1000.0)) / (t_cyc_sc_us * 1e-6)
    eps_req_rsa_sc = 0.10 / (rsa_L * est_sc_rounds_rsa)
    d_sc_rsa = min_sc_distance_for_target(eps_req_rsa_sc, a_sc, lambda_sc, d_min=33, d_max=65)
    sc_cells_per_L_rsa = 2 * d_sc_rsa * d_sc_rsa - 1
    sc_mem_cells_rsa = rsa_L * sc_cells_per_L_rsa
    sc_route_cells_rsa = int(0.50 * sc_mem_cells_rsa)
    sc_mem_cryos_rsa = math.ceil((sc_mem_cells_rsa + sc_route_cells_rsa) / EXP140_CRYO_CELL_CAP_THERMAL)

    rsa_sc_baseline = _build_rsa_arch(
        label=f"Exp143 D3 Surface Code (d={d_sc_rsa}) + 16x Litinski Two-Stage",
        code_label=f"Surface Code d={d_sc_rsa} @ D3 (0.337%)",
        mem_cells=sc_mem_cells_rsa,
        mem_cryos=sc_mem_cryos_rsa,
        routing_cells=sc_route_cells_rsa,
        factory=f2_lit,
        n_factories=16,
        p_L_mem_1L=sc_per_round_err(d_sc_rsa, a_sc, lambda_sc),
        t_cyc_mem_us=t_cyc_sc_us,
        n_cand_avg=6.0,
        hpc_modules=288,  # ~7x 4U per 100L x 41
        seed=2026164,
    )
    rsa_sc_baseline["d_surface_code"] = d_sc_rsa

    return {
        "FeMoco_192L_1e8T": {
            "qLDPC_d18_Litinski_TwoStage": femoco_qldpc_lit,
            "qLDPC_d18_Gidney_Cult_116to12": femoco_qldpc_cult_fast,
            "qLDPC_d18_Gidney_Cult_Compact15to1": femoco_qldpc_cult_min,
            "SurfaceCode_D3_Baseline": femoco_sc_baseline,
            "compression_vs_SC_Litinski": {
                "cryostats_x": round(femoco_sc_baseline["total_cryostats_ld400"] / femoco_qldpc_lit["total_cryostats_ld400"], 2),
                "power_x": round(femoco_sc_baseline["tco_and_power"]["total_facility_power_kw"] / femoco_qldpc_lit["tco_and_power"]["total_facility_power_kw"], 2),
                "tco_x": round(femoco_sc_baseline["tco_and_power"]["tco5_usd_p50"] / femoco_qldpc_lit["tco_and_power"]["tco5_usd_p50"], 2),
                "cost_per_solve_x": round(femoco_sc_baseline["cost_per_solve_usd_p50"] / femoco_qldpc_lit["cost_per_solve_usd_p50"], 2),
            },
            "compression_vs_SC_Cultivation": {
                "cryostats_x": round(femoco_sc_baseline["total_cryostats_ld400"] / femoco_qldpc_cult_fast["total_cryostats_ld400"], 2),
                "power_x": round(femoco_sc_baseline["tco_and_power"]["total_facility_power_kw"] / femoco_qldpc_cult_fast["tco_and_power"]["total_facility_power_kw"], 2),
                "tco_x": round(femoco_sc_baseline["tco_and_power"]["tco5_usd_p50"] / femoco_qldpc_cult_fast["tco_and_power"]["tco5_usd_p50"], 2),
                "cost_per_solve_x": round(femoco_sc_baseline["cost_per_solve_usd_p50"] / femoco_qldpc_cult_fast["cost_per_solve_usd_p50"], 2),
            },
            "lee2021_full_76orb_sensitivity": {
                "n_logical": 2142,
                "n_T_gates": lee21_T,
                "bb288_blocks": lee21_blocks,
                "mem_route_cryostats": lee21_mem_cryos,
                "n_cult_factories": lee21_n_fac,
                "total_cryostats": lee21_mem_cryos + lee21_n_fac * f4_cult["cryostats_ld400"],
                "runtime_days": round(lee21_runtime_days, 2),
            },
        },
        "RSA2048_4096L_1e10T": {
            "qLDPC_d18_D3pp_Litinski": rsa_qldpc_d18_lit_d3pp,
            "qLDPC_d24_D3_GidneyCult": rsa_qldpc_d24_cult_d3,
            "qLDPC_d18_D3_HonestSTAudit": rsa_qldpc_d18_cult_d3_audit,
            "SurfaceCode_D3_Baseline": rsa_sc_baseline,
            "compression_d18_Litinski_vs_SC": {
                "cryostats_x": round(rsa_sc_baseline["total_cryostats_ld400"] / rsa_qldpc_d18_lit_d3pp["total_cryostats_ld400"], 2),
                "power_x": round(rsa_sc_baseline["tco_and_power"]["total_facility_power_mw"] / rsa_qldpc_d18_lit_d3pp["tco_and_power"]["total_facility_power_mw"], 2),
                "tco_x": round(rsa_sc_baseline["tco_and_power"]["tco5_usd_p50"] / rsa_qldpc_d18_lit_d3pp["tco_and_power"]["tco5_usd_p50"], 2),
            },
            "compression_d24_Cult_vs_SC": {
                "cryostats_x": round(rsa_sc_baseline["total_cryostats_ld400"] / rsa_qldpc_d24_cult_d3["total_cryostats_ld400"], 2),
                "power_x": round(rsa_sc_baseline["tco_and_power"]["total_facility_power_mw"] / rsa_qldpc_d24_cult_d3["tco_and_power"]["total_facility_power_mw"], 2),
                "tco_x": round(rsa_sc_baseline["tco_and_power"]["tco5_usd_p50"] / rsa_qldpc_d24_cult_d3["tco_and_power"]["tco5_usd_p50"], 2),
            },
        },
    }


if __name__ == "__main__":
    fac = optimize_magic_state_factories(
        p_2q=0.0033687, p_1q=0.0008295, a_sc=0.017377, lambda_sc=2.8253, t_cyc_sc_us=6.7022
    )
    print("=== Magic State Factories @ Exp143 D3 GRAPE (0.337%, Lambda_SC=2.825) ===")
    for k in ("F1_single_stage_15to1_raw", "F1b_single_stage_15to1_postselected", "F2_litinski_twostage_15to1_x_116to12", "F3_gidney_cultivation_plus_15to1_compact", "F4_gidney_cultivation_plus_116to12_highthroughput"):
        v = fac[k]
        p_t = v.get("p_T", v.get("p_out"))
        print(f"  {k}: p_T={p_t:.2e} (<=1e-10: {v['meets_1e10']}), R_T={v['rate_khz']} kHz, cells={v['active_cells']}, cryos={v['cryostats_ld400']}")

    alg = evaluate_flagship_algorithms(
        factories=fac,
        p_L_round_1L_bb288_d3=1e-10,
        p_L_round_1L_bb288_d3pp=1e-15,
        p_L_round_1L_bb360_d24_d3=1e-15,
        t_cyc_bb_us=10.0789,
        a_sc=0.017377,
        lambda_sc=2.8253,
        t_cyc_sc_us=6.7022,
        n_mc=5000,
    )
    print("\n=== FeMoco (192L, 1e8 T) ===")
    for k, v in alg["FeMoco_192L_1e8T"].items():
        if isinstance(v, dict) and "total_cryostats_ld400" in v:
            print(f"  {k}: cryos={v['total_cryostats_ld400']}, runtime={v['runtime_hours']}h, P={v['tco_and_power']['total_facility_power_kw']}kW, TCO=${v['tco_and_power']['tco5_musd_p50']}M, $/solve=${v['cost_per_solve_usd_p50']}, P_fail={v['p_fail_total']:.4f}")
    print("  Compression Litinski:", alg["FeMoco_192L_1e8T"]["compression_vs_SC_Litinski"])
    print("  Compression Cultivation:", alg["FeMoco_192L_1e8T"]["compression_vs_SC_Cultivation"])

    print("\n=== RSA-2048 Shor (4096L, 1e10 T) ===")
    for k, v in alg["RSA2048_4096L_1e10T"].items():
        if isinstance(v, dict) and "total_cryostats_ld400" in v:
            print(f"  {k}: cryos={v['total_cryostats_ld400']}, runtime={v['runtime_hours']}h, P={v['tco_and_power']['total_facility_power_mw']}MW, TCO=${v['tco_and_power']['tco5_musd_p50']}M, P_fail={v['p_fail_total']:.4f}")
    print("  Compression d18 Litinski:", alg["RSA2048_4096L_1e10T"]["compression_d18_Litinski_vs_SC"])
    print("  Compression d24 Cult:", alg["RSA2048_4096L_1e10T"]["compression_d24_Cult_vs_SC"])
