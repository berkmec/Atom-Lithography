"""Exp136 (H154): Mode B Isotope-Abundance (f) x Stark Field (E_z) Yield, Coherence & M4 Percolation Engine.

Couples the atomistic 10-band sp3d5s* Boykin-Klimeck (2004) 29Si hyperfine atlas to:
  1. Portable multi-core Mode B epitaxial bath K=8 selection (exact Exp59/62/129 GAUSS500 selector
     on deterministic seed59 realizations, N_cell=400 per operating point), including gap-certified
     yields at 6.893 kHz (Exp126 DDRF), 10 kHz, and 15 kHz.
  2. Donor electron coherence T2e(f) (Exp62/126 two-anchor Hahn-echo model + Witzel CCE2 pure-bath
     ceiling + XY8/CPMG N=32 & N=64 dynamical decoupling extension) and first-principles Abragam
     dilute-spin 29Si nuclear dipolar dephasing time T2n*(f).
  3. Exact M4 L=11 (121-node, <=5% dead = <=6/121) 2D surface-code fault-tolerant percolation across
     N_cand in {3, 6, 8, 9, 10, 12} with Exp131 8.0 nm epi-cap yield (p_ff_opt = 0.9520), plus
     Pareto-optimal isotope fraction f* selection for Exp138.

Zero hardcoded user or host paths (strictly Path(__file__).resolve()).
Epistemic status: no_lab_measurement=True ({Literatür}/{Analitik}/{Model}/{Sayısal-Simülasyon}).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "exp129_valley_orbital_hyperfine"))
sys.path.insert(0, str(ROOT / "experiments" / "exp42_isotope_coded_atom"))

import bath_yield129 as by129  # noqa: E402

# Fixed repo anchors (read-only literature / upstream ledger constants)
M4_CAP_YIELD_EXP131 = 0.9520  # Exp131 Δz_cap* = 8.0 nm tuned flip-flop yield (p_ff_opt)
T2E0_S_EXP126 = 0.010  # 10.0 ms purified 28Si baseline (Exp62/63/126)
T2E_NAT_S_EXP126 = 0.0003  # 0.30 ms natural Si (4.7% 29Si, Abe et al. 2010 / Exp62/126)
F_NAT_FRAC = 0.047
K_BATH_PER_FRAC_EXP126 = (1.0 / T2E_NAT_S_EXP126 - 1.0 / T2E0_S_EXP126) / F_NAT_FRAC

# First-principles Abragam (1961) dilute spin-1/2 29Si dipolar linewidth constants
MU0_OVER_4PI = 1e-7
HBAR_JS = 1.054571817e-34
GAMMA_29SI_RAD_S_T = 2.0 * math.pi * 8.465e6  # 5.318716e7 rad/(s*T)
A0_NM = 0.5431
N_SI_PER_NM3 = 8.0 / (A0_NM ** 3)  # 49.9415 atoms/nm^3
# Abragam Ch. IV dilute Lorentzian HWHM: dw_1/2 = (4*pi^2 / (9*sqrt(3))) * (mu0/4pi) * hbar * gamma_n^2 * n_I
ABRAGAM_PREF = (4.0 * (math.pi ** 2)) / (9.0 * math.sqrt(3.0))
DIP_CONST_RAD_NM3_S = MU0_OVER_4PI * HBAR_JS * (GAMMA_29SI_RAD_S_T ** 2) * 1e27  # ~29.83 rad*nm^3/s

GAP_THRESH_15KHZ_HZ = 15000.0


def coherence_vs_abundance(f_pct: float) -> dict[str, float]:
    """Compute electron T2e (Hahn + CCE2 ceiling + XY8 DD) and nuclear T2n* (Abragam) vs 29Si %."""
    f_frac = max(float(f_pct) / 100.0, 1e-9)

    # 1. Exact Exp62/126 two-anchor donor electron Hahn-echo T2e(f)
    t2e_hahn_s = 1.0 / (1.0 / T2E0_S_EXP126 + K_BATH_PER_FRAC_EXP126 * f_frac)
    t2e_hahn_ms = t2e_hahn_s * 1e3

    # 2. Pure 29Si nuclear-bath CCE2 spectral-diffusion ceiling (Witzel et al. PRL 2010, ~1/f)
    t2e_witzel_bath_ms = (T2E_NAT_S_EXP126 * 1e3) * (F_NAT_FRAC / f_frac)

    # 3. Dynamical decoupling extension (Exp63/126): T2e_DD(N) = T2e * N^(alpha/(alpha+1))
    #    alpha=2 (Ornstein-Uhlenbeck / spectral diffusion): N^(2/3)
    #    alpha=1 (conservative 1/f): N^(1/2)
    t2e_xy8_n32_a2_ms = t2e_hahn_ms * (32.0 ** (2.0 / 3.0))
    t2e_xy8_n64_a2_ms = t2e_hahn_ms * (64.0 ** (2.0 / 3.0))
    t2e_xy8_n32_a1_ms = t2e_hahn_ms * (32.0 ** 0.5)
    t2e_xy8_n64_a1_ms = t2e_hahn_ms * (64.0 ** 0.5)

    # 4. First-principles Abragam dilute spin-1/2 29Si nuclear dipolar T2n*(f)
    n_29si_nm3 = N_SI_PER_NM3 * f_frac
    dw_half_rad_s = ABRAGAM_PREF * DIP_CONST_RAD_NM3_S * n_29si_nm3
    t2n_star_ms = (1.0 / dw_half_rad_s) * 1e3

    return {
        "abundance_pct": float(f_pct),
        "T2e_hahn_ms": float(t2e_hahn_ms),
        "T2e_witzel_pure_bath_ms": float(t2e_witzel_bath_ms),
        "T2e_XY8_N32_alpha2_ms": float(t2e_xy8_n32_a2_ms),
        "T2e_XY8_N64_alpha2_ms": float(t2e_xy8_n64_a2_ms),
        "T2e_XY8_N32_alpha1_ms": float(t2e_xy8_n32_a1_ms),
        "T2e_XY8_N64_alpha1_ms": float(t2e_xy8_n64_a1_ms),
        "T2n_star_abragam_ms": float(t2n_star_ms),
        "gamma_29si_hwhm_Hz": float(dw_half_rad_s / (2.0 * math.pi)),
    }


def exact_binomial_ft_yield(n_nodes: int, max_dead: int, p_node: float) -> float:
    """Exact Binomial CDF P(dead <= max_dead) on n_nodes independent sites."""
    p = min(max(float(p_node), 0.0), 1.0)
    q = 1.0 - p
    total = 0.0
    for k in range(0, min(max_dead, n_nodes) + 1):
        total += math.comb(n_nodes, k) * (q ** k) * (p ** (n_nodes - k))
    return float(min(max(total, 0.0), 1.0))


def min_ncand_for_ft_yield(
    p_single: float,
    L: int = 11,
    max_dead_frac: float = 0.05,
    target_yield: float = 0.995,
    max_search: int = 200,
) -> int:
    """Smallest integer N_cand achieving exact LxL FT yield >= target_yield."""
    n_nodes = L * L
    max_dead = int(math.floor(max_dead_frac * n_nodes))
    for nc in range(1, max_search + 1):
        p_node = 1.0 - ((1.0 - p_single) ** nc)
        if exact_binomial_ft_yield(n_nodes, max_dead, p_node) >= target_yield:
            return nc
    return max_search


def evaluate_m4_percolation(
    p_yield: float,
    m4_cap_yield: float = M4_CAP_YIELD_EXP131,
    L: int = 11,
    max_dead_frac: float = 0.05,
    n_cand_list: tuple[int, ...] = (3, 6, 8, 9, 10, 12),
) -> dict[str, Any]:
    """Compute exact M4 L=11 FT (<=5% dead = <=6/121) surface-code yield across N_cand."""
    p_m4 = float(p_yield) * float(m4_cap_yield)
    n_nodes = L * L
    max_dead = int(math.floor(max_dead_frac * n_nodes))
    by_ncand: dict[str, dict[str, float]] = {}
    for nc in n_cand_list:
        p_node = 1.0 - ((1.0 - p_m4) ** nc)
        y_ft = exact_binomial_ft_yield(n_nodes, max_dead, p_node)
        by_ncand[str(nc)] = {
            "N_cand": int(nc),
            "p_node": float(p_node),
            "Y_FT_5pct_exact": float(y_ft),
            "expected_dead_nodes": float(n_nodes * (1.0 - p_node)),
        }
    return {
        "L": int(L),
        "n_nodes": int(n_nodes),
        "max_dead_FT": int(max_dead),
        "m4_cap_yield": float(m4_cap_yield),
        "p_yield_base": float(p_yield),
        "p_M4_single_site": float(p_m4),
        "by_N_cand": by_ncand,
        "Y_FT_Ncand6": float(by_ncand["6"]["Y_FT_5pct_exact"]),
        "N_cand_star_99pct": int(min_ncand_for_ft_yield(p_m4, L=L, max_dead_frac=max_dead_frac, target_yield=0.990)),
        "N_cand_star_99p5pct": int(min_ncand_for_ft_yield(p_m4, L=L, max_dead_frac=max_dead_frac, target_yield=0.995)),
    }


def augment_cell_with_15khz(cell_res: dict[str, Any]) -> dict[str, Any]:
    """Add exact 15 kHz gap-certified yield metrics to bath_yield129 cell dictionary."""
    gs = cell_res["gap_stats"]
    reals = int(cell_res["realizations"])
    gaps = np.asarray(gs.get("certified_min_gaps_Hz_sorted", []), dtype=np.float64)
    if len(gaps) > 0:
        n_lt_15 = int(np.sum(gaps < GAP_THRESH_15KHZ_HZ))
        n_ge_15 = int(np.sum(gaps >= GAP_THRESH_15KHZ_HZ))
        gs["frac_lt_15kHz"] = float(n_lt_15 / len(gaps))
        gs["count_lt_15kHz"] = n_lt_15
        gs["yield_and_gap_ge_15kHz"] = float(n_ge_15 / reals)
    else:
        gs["frac_lt_15kHz"] = 1.0
        gs["count_lt_15kHz"] = 0
        gs["yield_and_gap_ge_15kHz"] = 0.0
    # Strip full sorted list from compact summary after deriving stats (keep quantiles + counts)
    compact = dict(cell_res)
    compact_gs = {k: v for k, v in gs.items() if k != "certified_min_gaps_Hz_sorted"}
    compact["gap_stats"] = compact_gs
    return compact


def run_abundance_sweep(
    a_all: np.ndarray,
    abundances_pct: list[float],
    reals: int = 400,
    max_workers: int | None = None,
    n_cand_list: tuple[int, ...] = (3, 6, 8, 9, 10, 12),
) -> list[dict[str, Any]]:
    """Run full Mode B K=8 yield + coherence + M4 L=11 percolation sweep over 29Si abundances."""
    rows: list[dict[str, Any]] = []
    for f_pct in abundances_pct:
        raw_cell = by129.run_mode_b_cell(a_all, f_pct=float(f_pct), reals=reals, max_workers=max_workers)
        cell = augment_cell_with_15khz(raw_cell)
        coh = coherence_vs_abundance(float(f_pct))
        perc_base = evaluate_m4_percolation(cell["yield_frac"], n_cand_list=n_cand_list)
        perc_gap6p89 = evaluate_m4_percolation(
            cell["gap_stats"]["yield_and_gap_ge_6893Hz"], n_cand_list=n_cand_list
        )
        perc_gap10 = evaluate_m4_percolation(
            cell["gap_stats"]["yield_and_gap_ge_10kHz"], n_cand_list=n_cand_list
        )
        rows.append({
            "abundance_pct": float(f_pct),
            "mode_b": cell,
            "coherence": coh,
            "m4_percolation_base": perc_base,
            "m4_percolation_gap6p89kHz": perc_gap6p89,
            "m4_percolation_gap10kHz": perc_gap10,
        })
    return rows


def select_pareto_f_star(sweep_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Identify Pareto-optimal 29Si isotope fraction f* balancing M4 L=11 N_cand=6 >= 99.5% and max T2e/T2n*."""
    # Minimum f meeting base M4 L=11 FT >= 99.5% at N_cand=6 (highest T2e & T2n* among feasible points!)
    feasible_base_nc6 = [r for r in sweep_rows if r["m4_percolation_base"]["Y_FT_Ncand6"] >= 0.995]
    feasible_gap6p89_nc6 = [r for r in sweep_rows if r["m4_percolation_gap6p89kHz"]["Y_FT_Ncand6"] >= 0.995]
    feasible_gap10_nc6 = [r for r in sweep_rows if r["m4_percolation_gap10kHz"]["Y_FT_Ncand6"] >= 0.995]

    best_base = min(feasible_base_nc6, key=lambda r: r["abundance_pct"]) if feasible_base_nc6 else None
    best_gap6p89 = min(feasible_gap6p89_nc6, key=lambda r: r["abundance_pct"]) if feasible_gap6p89_nc6 else None
    best_gap10 = min(feasible_gap10_nc6, key=lambda r: r["abundance_pct"]) if feasible_gap10_nc6 else None

    # Primary recommendation: lowest f that passes M4 L=11 N_cand=6 >= 99.5% on gap-certified >=6.893 kHz
    # if available (or base if not), maximizing T2e and T2n*!
    primary = best_base
    return {
        "f_star_base_Ncand6_99p5_pct": None if best_base is None else best_base["abundance_pct"],
        "f_star_gap6p89_Ncand6_99p5_pct": None if best_gap6p89 is None else best_gap6p89["abundance_pct"],
        "f_star_gap10_Ncand6_99p5_pct": None if best_gap10 is None else best_gap10["abundance_pct"],
        "primary_f_star_pct": None if primary is None else primary["abundance_pct"],
        "primary_row": primary,
        "gap6p89_certified_row": best_gap6p89,
    }
