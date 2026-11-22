"""Exp125 Module 3: Risk R8 — Phase-Sensitive Silicon Valley Interference (cos(k0*R) on Si Lattice)
& Narrow Tunnel-Coupling Control Window Sensitivity for the 1 K Hot-Readout Ancilla Route.

Extends Exp118 (Exp92 BCA 5 keV straggle sigma_lat=3.25 nm, Rp=6.46+-2.88 nm; House et al. 2015
tc_ref=1 GHz @ 20 nm, gate tunability up to 100x) with physical silicon conduction-band valley
interference (Koiller, Hu, Das Sarma, PRL 88, 027903 (2002); a_Si=0.5431 nm, k0=0.85*2pi/a_Si)
and computes the realistic yield lower bound, oversampling N99, and exact BOM cost break-even
yield p_crit against the 20 mK dilution baseline (S6.8=D, golden=0.5215).

Epistemic label: {Model} / {Sayısal-Simülasyon} / {Literatür}. no_lab_measurement=True.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Silicon crystal & valley parameters (literature anchors)
A_SI_NM = 0.5431                        # Si diamond-cubic lattice constant (nm)
A_SUB_NM = A_SI_NM / 4.0                # Nearest sub-lattice spacing a_Si/4 = 0.135775 nm
K0_VALLEY_INV_NM = 0.85 * 2.0 * math.pi / A_SI_NM  # 9.8340 nm^-1 (conduction-band valley minimum)

# Exp92 BCA 5 keV 31P+ in Si straggle & Exp118 baseline anchors
SIGMA_LAT_NM = 3.25
SIGMA_Z_NM = 2.88
DONOR_RP_NM = 6.46
ANC_Z_NM = 5.0
R_REF_NM = 20.0
TC_REF_HZ = 1.0e9  # House et al., Nat. Commun. 6:8848 (2015)

# BOM cost baseline parameters (Exp114/116/117/121, 40-row BOM.csv)
CENTRAL_CHAIN_CLASS = 16.875


def snap_to_si_diamond_lattice(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Snap continuous 3D coordinates (nm) to nearest valid Si diamond-cubic lattice sites.

    Diamond lattice = FCC + (1/4, 1/4, 1/4) basis in units of a_Si:
      Sublattice A: (n_x, n_y, n_z) * (a_Si/2) with n_x + n_y + n_z even
      Sublattice B: Sublattice A + (a_Si/4, a_Si/4, a_Si/4)
    Vectorized nearest-site projection over both sublattices.
    """
    half_a = 0.5 * A_SI_NM
    quarter_a = 0.25 * A_SI_NM

    def nearest_fcc(px: np.ndarray, py: np.ndarray, pz: np.ndarray):
        ix = np.rint(px / half_a)
        iy = np.rint(py / half_a)
        iz = np.rint(pz / half_a)
        # Enforce even parity ix + iy + iz == 0 (mod 2) by flipping coordinate with largest rounding error
        odd = (np.abs(ix + iy + iz).astype(np.int64) % 2) == 1
        if np.any(odd):
            ex = px / half_a - ix
            ey = py / half_a - iy
            ez = pz / half_a - iz
            ax, ay, az = np.abs(ex), np.abs(ey), np.abs(ez)
            flip_x = odd & (ax >= ay) & (ax >= az)
            flip_y = odd & (~flip_x) & (ay >= az)
            flip_z = odd & (~flip_x) & (~flip_y)
            ix = np.where(flip_x, ix + np.where(ex >= 0, 1.0, -1.0), ix)
            iy = np.where(flip_y, iy + np.where(ey >= 0, 1.0, -1.0), iy)
            iz = np.where(flip_z, iz + np.where(ez >= 0, 1.0, -1.0), iz)
        return ix * half_a, iy * half_a, iz * half_a

    ax, ay, az = nearest_fcc(x, y, z)
    bx, by, bz = nearest_fcc(x - quarter_a, y - quarter_a, z - quarter_a)
    bx += quarter_a; by += quarter_a; bz += quarter_a

    d2_a = (x - ax) ** 2 + (y - ay) ** 2 + (z - az) ** 2
    d2_b = (x - bx) ** 2 + (y - by) ** 2 + (z - bz) ** 2
    use_b = d2_b < d2_a
    return (
        np.where(use_b, bx, ax),
        np.where(use_b, by, ay),
        np.where(use_b, bz, az),
    )


def mc_ancilla_yield(
    r0_nm: float = 20.0,
    g_tune: float = 100.0,
    win_lo_hz: float = 1.0e6,
    win_hi_hz: float = 1.0e10,
    valley_model: str = "none",
    lam_nm: float = 2.0,
    s_lat_nm: float = SIGMA_LAT_NM,
    s_z_nm: float = SIGMA_Z_NM,
    n_samples: int = 200_000,
    seed: int = 125,
    snap_lattice: bool = True,
) -> Dict[str, float]:
    """Monte Carlo usable ancilla-donor tunnel-coupling yield under Exp92 BCA straggle.

    valley_model:
      - "none": no valley suppression
      - "exp118_logU": Exp118 legacy factor 10^U(-1, 0) (for exact replication gate)
      - "V1_interface_2valley": MOS/interface ancilla QD (+/-z valleys), |cos(k0*z_d + phi0)|
      - "V2_koiller_6valley": bulk Si:P donor-dot 6-valley Koiller-Hu-Das-Sarma factor
                              (1/3)*|cos(k0*x) + cos(k0*y) + cos(k0*z)| on discrete Si diamond lattice
    """
    rng = np.random.default_rng(seed)
    dx = rng.normal(0.0, s_lat_nm, n_samples)
    dy = rng.normal(0.0, s_lat_nm, n_samples)
    dz = rng.normal(0.0, s_z_nm, n_samples)

    x = r0_nm + dx
    y = dy
    z = DONOR_RP_NM + dz
    # Physical surface cutoff: donor stays below Si surface (z > 0.2 nm) for physical valley models
    if valley_model in ("V1_interface_2valley", "V2_koiller_6valley"):
        z = np.maximum(z, 0.2)
        if snap_lattice:
            x, y, z = snap_to_si_diamond_lattice(x, y, z)

    dz_rel = z - ANC_Z_NM
    r = np.sqrt(x ** 2 + y ** 2 + dz_rel ** 2)
    logtc = math.log10(TC_REF_HZ) - (r - R_REF_NM) / (lam_nm * math.log(10.0))

    if valley_model == "exp118_logU":
        logtc = logtc + rng.uniform(-1.0, 0.0, n_samples)
    elif valley_model == "V1_interface_2valley":
        # Interface phase offset phi0 ~ U(0, pi) captures atomic step / interface disorder across wafer
        phi0 = rng.uniform(0.0, math.pi, n_samples)
        v_fac = np.abs(np.cos(K0_VALLEY_INV_NM * z + phi0))
        logtc = logtc + np.log10(np.maximum(v_fac, 1e-12))
    elif valley_model == "V2_koiller_6valley":
        # Exact 6-valley symmetric interference on discrete Si diamond lattice sites
        # Relative displacement vector R = (x, y, z - ANC_Z_NM) snapped to lattice difference
        v_fac = np.abs(
            np.cos(K0_VALLEY_INV_NM * x)
            + np.cos(K0_VALLEY_INV_NM * y)
            + np.cos(K0_VALLEY_INV_NM * dz_rel)
        ) / 3.0
        logtc = logtc + np.log10(np.maximum(v_fac, 1e-12))
    elif valley_model != "none":
        raise ValueError(f"Unknown valley_model: {valley_model}")

    lo = math.log10(win_lo_hz) - math.log10(g_tune)
    hi = math.log10(win_hi_hz) + math.log10(g_tune)
    usable = (logtc >= lo) & (logtc <= hi)
    too_weak = logtc < lo
    too_strong = logtc > hi

    p = float(np.mean(usable))
    n99 = 1 if p >= 0.99 else (int(math.ceil(math.log(0.01) / math.log(1.0 - p))) if p > 1e-6 else 999999)
    return {
        "p_yield": p,
        "frac_too_weak": float(np.mean(too_weak)),
        "frac_too_strong": float(np.mean(too_strong)),
        "N99": n99,
        "log10_tc_median": float(np.median(logtc)),
        "log10_tc_p10": float(np.percentile(logtc, 10)),
        "log10_tc_p90": float(np.percentile(logtc, 90)),
        "bare_window_decades": float(math.log10(win_hi_hz / win_lo_hz)),
        "effective_window_decades": float(hi - lo),
    }


def replicate_exp118_gate() -> Dict:
    """Replicate Exp118 legacy baseline (R20_G100_v0, R20_G100_v1, R15_G1_v0, R15_G1_v1)."""
    r20_v0 = mc_ancilla_yield(20.0, 100.0, 1e6, 1e10, "none", seed=118, snap_lattice=False)
    r20_v1 = mc_ancilla_yield(20.0, 100.0, 1e6, 1e10, "exp118_logU", seed=118, snap_lattice=False)
    r15_v0 = mc_ancilla_yield(15.0, 1.0, 1e6, 1e10, "none", seed=118, snap_lattice=False)
    r15_v1 = mc_ancilla_yield(15.0, 1.0, 1e6, 1e10, "exp118_logU", seed=118, snap_lattice=False)
    ok = (
        abs(r20_v0["p_yield"] - 1.0) < 1e-4
        and abs(r20_v1["p_yield"] - 1.0) < 1e-4
        and abs(r15_v0["p_yield"] - 0.53491) < 0.004
        and abs(r15_v1["p_yield"] - 0.77561) < 0.004
    )
    return {
        "ok": ok,
        "R20_G100_none": r20_v0["p_yield"],
        "R20_G100_logU": r20_v1["p_yield"],
        "R15_G1_none": r15_v0["p_yield"],
        "R15_G1_logU": r15_v1["p_yield"],
    }


def cost_breakeven_vs_20mk(
    nl: int = 163,
    chain_class: float = CENTRAL_CHAIN_CLASS,
    golden_cost_c_base: float = 2615.6171756283857,  # Exp116/117: 2515.617 + 100 (S6.8=C)
    ref_cost_c_base: float = 5841.25,                # Exp116/117: 5741.25 + 100 (S6.8=C)
    abs_cost_c_base: float = 1265.87539876329,       # Exp117 NL163 central S6.8=C
    golden_frac_d_baseline: float = 0.5215082033196196,  # Exp116/121 S6.8=D baseline
    abs_cost_d_baseline: float = 2165.87539876329,       # Exp116/121 S6.8=D baseline
) -> Dict:
    """Exact oversampling cost model (Exp118 pattern) and break-even yield p_crit vs S6.8=D.

    If ancilla coupling yield is p < 1, achieving the same certified throughput requires
    1/p times as many parallel readout channels/chains:
      extra_chains_g = ceil(9000 / nl) * (1/p - 1)
      extra_chains_r = ceil(10000 / nl) * (1/p - 1)
    Wait: for absolute cost at 1e6/day (1 chain when p=1), extra chains = max(0, ceil(34/p/nl) - 1)
    or continuous chain oversampling (1/p - 1) * chain_class (matching Exp118).
    We compute BOTH golden-fraction parity p_crit_golden (where 1K golden_frac equals DR 0.5215)
    AND absolute-cost parity (where 1K golden_cost_1K equals DR golden_cost_D = 3515.62)!
    """
    chains_g = math.ceil(9000 / nl)
    chains_r = math.ceil(10000 / nl)
    golden_cost_d = golden_cost_c_base + 900.0  # D (+1000) vs C (+100) = +900 fixed units

    def eval_at_p(p: float) -> Dict[str, float]:
        adder_g = chains_g * (1.0 / p - 1.0) * chain_class
        adder_r = chains_r * (1.0 / p - 1.0) * chain_class
        frac = (golden_cost_c_base + adder_g) / (ref_cost_c_base + adder_r)
        g_cost = golden_cost_c_base + adder_g
        a_cost = abs_cost_c_base + (1.0 / p - 1.0) * chain_class
        return {"p": p, "golden_frac": frac, "golden_cost": g_cost, "abs_cost": a_cost, "adder_g": adder_g}

    # Exact closed-form p_crit where 1K golden_cost(p) == DR golden_cost_D (+900 units):
    # chains_g * (1/p - 1) * chain_class = 900 -> 1/p = 1 + 900 / (chains_g * chain_class)
    p_crit_golden_cost = 1.0 / (1.0 + 900.0 / (chains_g * chain_class))

    # Exact closed-form p_crit where 1K golden_frac(p) == DR golden_frac_D (0.5215):
    # (g_c + cg*(1/p - 1)*cc) / (r_c + cr*(1/p - 1)*cc) = f_D
    # Let u = 1/p - 1: g_c + cg*cc*u = f_D * (r_c + cr*cc*u)
    # u * cc * (cg - f_D * cr) = f_D * r_c - g_c
    u_frac = (golden_frac_d_baseline * ref_cost_c_base - golden_cost_c_base) / (
        chain_class * (chains_g - golden_frac_d_baseline * chains_r)
    )
    p_crit_golden_frac = 1.0 / (1.0 + u_frac)

    curve = [eval_at_p(p) for p in (1.0, 0.90, 0.80, 0.70, 0.60, 0.50, 0.40, 0.30)]
    return {
        "nl": nl,
        "chains_golden_base": chains_g,
        "chain_class": chain_class,
        "DR_D_golden_frac": golden_frac_d_baseline,
        "DR_D_golden_cost": golden_cost_d,
        "DR_D_abs_cost": abs_cost_d_baseline,
        "p_crit_golden_cost_parity": float(p_crit_golden_cost),
        "p_crit_golden_frac_parity": float(p_crit_golden_frac),
        "curve": curve,
    }


def run_r8_sensitivity_study(n_samples: int = 200_000) -> Dict:
    """Full Risk R8 sensitivity sweep: valley models x window widths x gate tunability x lambda."""
    gate = replicate_exp118_gate()

    # Target-matched windows centered on tc_ref = 1 GHz (R0 = 20 nm, House et al. 2015 anchor),
    # plus Exp118's exact W4 baseline [1 MHz, 10 GHz] and an off-center 100 MHz check.
    windows = {
        "W4_exp118_1MHz_10GHz": (1.0e6, 1.0e10),       # 4 decades bare (Exp118 baseline)
        "W3_wide_32MHz_32GHz": (3.162e7, 3.162e10),    # 3 decades bare centered on 1 GHz
        "W2_realistic_100MHz_10GHz": (1.0e8, 1.0e10),  # 2 decades bare centered on 1 GHz
        "W1_tight_316MHz_3p16GHz": (3.162e8, 3.162e9), # 1 decade bare centered on 1 GHz
        "W2_lowfreq_10MHz_1GHz": (1.0e7, 1.0e9),       # 2 decades off-center (100 MHz) check
    }
    models = ("none", "exp118_logU", "V1_interface_2valley", "V2_koiller_6valley")
    g_vals = (1.0, 3.0, 10.0, 30.0, 100.0)

    # Primary sweep at R0 = 20 nm, lambda = 2.0 nm
    sweep = {}
    for wname, (wlo, whi) in windows.items():
        sweep[wname] = {}
        for m in models:
            sweep[wname][m] = {}
            for g in g_vals:
                sweep[wname][m][f"G{int(g)}"] = mc_ancilla_yield(
                    r0_nm=20.0, g_tune=g, win_lo_hz=wlo, win_hi_hz=whi,
                    valley_model=m, lam_nm=2.0, n_samples=n_samples, seed=125
                )

    # Lambda Bohr-decay sensitivity at target-matched realistic & tight points (1 GHz center)
    lam_sens = {}
    for lam in (1.5, 2.0, 2.5):
        lam_sens[f"lam_{lam}nm"] = {
            "V1_W2_G10": mc_ancilla_yield(20.0, 10.0, 1.0e8, 1.0e10, "V1_interface_2valley", lam_nm=lam, n_samples=n_samples, seed=125),
            "V2_W2_G10": mc_ancilla_yield(20.0, 10.0, 1.0e8, 1.0e10, "V2_koiller_6valley", lam_nm=lam, n_samples=n_samples, seed=125),
            "V2_W1_G3": mc_ancilla_yield(20.0, 3.0, 3.162e8, 3.162e9, "V2_koiller_6valley", lam_nm=lam, n_samples=n_samples, seed=125),
        }

    # Sigma_lat = 3.8 nm total budget sensitivity (including equipment sigma)
    sig38_sens = {
        "V1_W2_G10_sig3p8": mc_ancilla_yield(20.0, 10.0, 1.0e8, 1.0e10, "V1_interface_2valley", s_lat_nm=3.8, n_samples=n_samples, seed=125),
        "V2_W2_G10_sig3p8": mc_ancilla_yield(20.0, 10.0, 1.0e8, 1.0e10, "V2_koiller_6valley", s_lat_nm=3.8, n_samples=n_samples, seed=125),
        "V2_W1_G3_sig3p8": mc_ancilla_yield(20.0, 3.0, 3.162e8, 3.162e9, "V2_koiller_6valley", s_lat_nm=3.8, n_samples=n_samples, seed=125),
    }

    breakeven = cost_breakeven_vs_20mk()

    return {
        "exp118_replication_gate": gate,
        "silicon_valley_constants": {
            "a_Si_nm": A_SI_NM,
            "k0_valley_inv_nm": K0_VALLEY_INV_NM,
            "valley_half_period_nm": math.pi / K0_VALLEY_INV_NM,
        },
        "sweep_R20_lam2": sweep,
        "lambda_sensitivity_W2_G10": lam_sens,
        "sigma_total_3p8nm_sensitivity": sig38_sens,
        "cost_breakeven": breakeven,
    }


if __name__ == "__main__":
    res = run_r8_sensitivity_study(n_samples=100_000)
    print("Exp118 gate:", res["exp118_replication_gate"])
    print("Break-even vs DR (S6.8=D):",
          "p_crit_golden_cost =", round(res["cost_breakeven"]["p_crit_golden_cost_parity"], 4),
          "p_crit_golden_frac =", round(res["cost_breakeven"]["p_crit_golden_frac_parity"], 4))
    for wname, mdict in res["sweep_R20_lam2"].items():
        print(f"\nWindow: {wname}")
        for m in ("none", "exp118_logU", "V1_interface_2valley", "V2_koiller_6valley"):
            row = "  ".join(f"G{g}:{mdict[m][f'G{g}']['p_yield']:.3f}(N99={mdict[m][f'G{g}']['N99']})" for g in (1, 3, 10, 30, 100))
            print(f"  {m:22s} | {row}")
