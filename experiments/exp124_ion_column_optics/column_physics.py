"""Exp124 Track 1: Liouville-consistent 10-15 -> 5 keV ion-optical column physics.

Modules:
  1. Historical chain audit (Exp66, 71, 72, 81, 82, 91_budget_attack, 92, 105)
     and exact Liouville/Lagrange-Helmholtz deficit proof for _attack91.py.
  2. Exact 2D axisymmetric Laplace PDE solver (scipy.sparse.linalg.spsolve) for
     electrostatic Einzel + retarding immersion micro/mini-lenses, coupled to
     DOP853 paraxial & full non-paraxial ray tracing (Wronskian invariant,
     positive-definite Scherzer C_c vs direct chromatic ray trace, exact
     non-paraxial C_s, peak electrode E_max vs UHV breakdown).
  3. Full column subsystems: Duoplasmatron (PH3), Wien mass filter (31P+ vs
     32PH+), Hemispherical Deflector Analyzer (HDA, dE <= 2 eV), Jansen
     Boersch / Coulomb trajectory blur, spot synthesis, Exp72/92 IBIC eta(E),
     and CAD-ready mechanical dimension table (mm).

Epistemic status: no_lab_measurement=True ({Model}/{Analitik}/{Sayisal-Simulasyon}/{Literatur}).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicSpline, UnivariateSpline, make_interp_spline
from scipy.sparse.linalg import spsolve
from scipy.special import erf

# CODATA 2018 physical constants
E_CHARGE = 1.602176634e-19     # C
EPS0 = 8.8541878128e-12        # F/m
H_PLANCK = 6.62607015e-34      # J s
AMU = 1.66053906660e-27        # kg
M_P31 = 30.973761998 * AMU     # kg (31P+ ion)
M_PH32 = 31.981587 * AMU       # kg (32PH+ ion)
FWHM_TO_SIGMA = 2.0 * math.sqrt(2.0 * math.log(2.0))  # 2.354820045...

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# 1. Historical chain audit & Exp72/92 shared physics models
# ---------------------------------------------------------------------------

def ibic_efficiency_exp72_legacy(E_keV: float, C_pF: float = 0.5, threshold_sigma: float = 5.0) -> dict[str, float]:
    """Historical Exp72 + Exp92 verbatim IBIC heuristic (retained ONLY for audit_historical_chain)."""
    e_grid = np.array([3.0, 4.0, 5.0, 10.0, 20.0])
    f_grid = np.array([0.32, 0.335, 0.35, 0.40, 0.45])
    frac = float(np.interp(E_keV, e_grid, f_grid))
    signal_e = (E_keV * 1000.0 * frac) / 3.6
    enc_e = 50.0 + 25.0 * C_pF
    sigma_s_e = 0.15 * signal_e
    eta = 0.5 * (1.0 + math.erf((signal_e - threshold_sigma * enc_e) / (math.sqrt(2.0) * sigma_s_e)))
    return dict(E_keV=E_keV, C_pF=C_pF, ion_frac=frac, signal_e=signal_e,
                enc_e=enc_e, sigma_signal_e=sigma_s_e, eta=eta)


def ibic_efficiency(
    E_keV: float,
    C_pF: float = 0.5,
    threshold_sigma: float = 6.2,
    dead_layer_nm: float = 1.5,
    c_par_pF: float = 0.25,
    temp_K: float = 100.0,
) -> dict[str, float]:
    """Synchronized Exp127 Lindhard/COLD_100K + Ramo-Shockley surface dead-layer IBIC model (OBS-071/098/083).

    Replaces the obsolete Exp72 heuristic (frac=0.35, ENC=62.5 e-) with exact Lindhard
    electronic partition (w=3.72 eV @ 100 K), iradina-calibrated surface dead-layer CCE
    (default 1.5 nm spec -> CCE=0.85 at 5 keV), and Parseval-anchored COLD_100K ENC
    (24.07 e- at C_det=0.5 pF, C_par=0.25 pF; scaled linearly with C_tot = C_det + C_par + 0.45 pF).
    Default threshold_sigma=6.2 closes 15 ms Rice P_false < 1e-3 (OBS-083).
    """
    Z1, M1 = 15.0, 30.973762
    Z2, M2 = 14.0, 28.085
    a0_nm = 0.05291772109
    e2_ev_nm = 1.43996454784
    z_term = Z1 ** (2.0 / 3.0) + Z2 ** (2.0 / 3.0)
    a_L = 0.8853 * a0_nm / math.sqrt(z_term)
    k_L = (
        0.0793 * (Z1 ** (2.0 / 3.0)) * math.sqrt(Z2) * ((M1 + M2) ** 1.5)
        / ((z_term ** 0.75) * (M1 ** 1.5) * math.sqrt(M2))
    )
    eps = (float(E_keV) * 1e3) * a_L * M2 / (Z1 * Z2 * e2_ev_nm * (M1 + M2))
    g_eps = 3.0 * (eps ** 0.15) + 0.7 * (eps ** 0.6) + eps
    y_e = (k_L * g_eps) / (1.0 + k_L * g_eps)
    w_eV = 3.62 if temp_K >= 200.0 else 3.72
    signal_raw_e = (y_e * E_keV * 1000.0) / w_eV

    # Iradina depth-resolved surface dead-layer loss fraction + minor surface recomb
    e_anc = np.array([2.0, 3.0, 5.0, 10.0, 20.0])
    d_anc = np.array([0.0, 1.5, 2.0, 3.0, 5.0])
    f_tbl = np.array([
        [0.0, 0.310, 0.415, 0.540, 0.678],
        [0.0, 0.225, 0.310, 0.415, 0.522],
        [0.0, 0.0859, 0.1206, 0.1966, 0.3637],
        [0.0, 0.0430, 0.0610, 0.1000, 0.1850],
        [0.0, 0.0220, 0.0310, 0.0520, 0.0960],
    ])
    f_d = float(np.interp(max(0.0, dead_layer_nm), d_anc, [float(np.interp(E_keV, e_anc, f_tbl[:, k])) for k in range(len(d_anc))]))
    s_rec = 0.070 if dead_layer_nm >= 1.5 else 0.0
    cce = max(0.05, (1.0 - f_d) * (1.0 - s_rec))
    signal_e = cce * signal_raw_e

    # Parseval-anchored COLD_100K 1200ns Rf=1G ENC(C_det, C_par): 24.07 e- at C_det=0.5, C_par=0.25 (C_in=0.45)
    c_tot_pF = C_pF + c_par_pF + 0.45
    enc_e = math.hypot(12.2, 17.3 * c_tot_pF) if temp_K < 200.0 else math.hypot(28.0, 39.0 * c_tot_pF)
    strag_rel = 0.18 if E_keV <= 6.0 else 0.15
    sigma_tot_e = math.sqrt((strag_rel * signal_e) ** 2 + 0.115 * max(signal_e, 1.0) + enc_e ** 2)
    eta = 0.5 * (1.0 + math.erf((signal_e - threshold_sigma * enc_e) / (math.sqrt(2.0) * sigma_tot_e)))
    return dict(
        E_keV=E_keV, C_pF=C_pF, c_par_pF=c_par_pF, dead_layer_nm=dead_layer_nm,
        cce=cce, ion_frac=y_e, signal_raw_e=signal_raw_e, signal_e=signal_e,
        enc_e=enc_e, sigma_signal_e=strag_rel * signal_e, threshold_sigma=threshold_sigma, eta=eta,
        model="Exp127_Lindhard_COLD100K_RamoShockley",
    )


def bca_straggle_nm(E_keV: float) -> float:
    """Interpolate corrected infinite-domain ZBL+LSS BCA / iradina 3D lateral sigma_lat(E) in nm (OBS-039).

    Anchored to fixed Exp92 (_bca92.py exact Gauss-Mehler quadrature) & 3D iradina 1.2.3
    (5 keV: 4.385 nm / iradina 4.410 nm; 10 keV: 7.130 nm / iradina 7.105 nm).
    """
    e_grid = np.array([2.0, 3.0, 4.0, 5.0, 6.0, 7.5, 10.0, 15.0, 20.0])
    s_grid = np.array([2.342, 3.165, 3.825, 4.385, 4.978, 5.711, 7.130, 9.583, 12.221])
    return float(np.exp(np.interp(math.log(E_keV), np.log(e_grid), np.log(s_grid))))


def bca_depth_profile_nm(E_keV: float) -> tuple[float, float]:
    """Return corrected (Rp_nm, sigma_z_nm) from fixed Exp92 / iradina 3D BCA (OBS-039)."""
    e_grid = np.array([2.0, 3.0, 4.0, 5.0, 6.0, 7.5, 10.0, 15.0, 20.0])
    rp_grid = np.array([5.33, 7.14, 8.78, 10.31, 11.87, 14.06, 17.43, 24.40, 31.24])
    dz_grid = np.array([2.73, 3.65, 4.52, 5.10, 5.81, 6.91, 8.29, 11.69, 14.47])
    rp = float(np.exp(np.interp(math.log(E_keV), np.log(e_grid), np.log(rp_grid))))
    dz = float(np.exp(np.interp(math.log(E_keV), np.log(e_grid), np.log(dz_grid))))
    return rp, dz


def de_broglie_nm(E_eV: float, mass_kg: float = M_P31) -> float:
    """Non-relativistic de Broglie wavelength in nm."""
    lam_m = H_PLANCK / math.sqrt(2.0 * mass_kg * E_eV * E_CHARGE)
    return lam_m * 1e9


def audit_historical_chain(root: Path = ROOT) -> dict[str, Any]:
    """Re-derive and verify anchors across Exp66, 71, 72, 81, 82, 91b, 92, 105."""
    res = root / "results"
    d66 = json.loads((res / "exp66/exp66.json").read_text(encoding="utf-8"))
    d71 = json.loads((res / "exp71/exp71.json").read_text(encoding="utf-8"))
    d72 = json.loads((res / "exp72/exp72.json").read_text(encoding="utf-8"))
    d81 = json.loads((res / "exp81_source/exp81.json").read_text(encoding="utf-8"))
    d82 = json.loads((res / "exp82_chromatic/exp82.json").read_text(encoding="utf-8"))
    d91b = json.loads((res / "exp91_budget_attack/exp91.json").read_text(encoding="utf-8"))
    d92 = json.loads((res / "exp92_bca_straggle/exp92.json").read_text(encoding="utf-8"))
    d105 = json.loads((res / "exp105_p91_feedback/exp105.json").read_text(encoding="utf-8"))

    # Exp66 EUV 10 keV
    sig_eq_66 = math.sqrt(2.0**2 + 0.5**2 + 0.5**2 + 0.3**2 + 1.0**2)
    sig_tot_66 = math.hypot(sig_eq_66, 5.0)
    err_66 = abs(sig_tot_66 - d66["table"]["euv_grade"]["E10"]["sigma_total_nm"]) / sig_tot_66

    # Exp71 brightness & Child-Langmuir
    I_req = E_CHARGE / 1e-3
    B_req_71 = I_req / ((math.pi * (2e-9)**2) * (math.pi * (10e-3)**2))
    err_71 = abs(B_req_71 - d71["cases"]["r2_a10"]["B_required"]) / B_req_71

    # Exp72 IBIC verbatim check (uses legacy Exp72 heuristic strictly for historical audit)
    ib72_5 = ibic_efficiency_exp72_legacy(5.0, 0.5)
    ib72_10_c5 = ibic_efficiency_exp72_legacy(10.0, 5.0)
    err_72_e10_c5 = abs(ib72_10_c5["eta"] - d72["table"]["E10_C5"]["eta"]) / d72["table"]["E10_C5"]["eta"]
    err_72_e5_c05 = abs(ib72_5["eta"] - d72["table"]["E5_C0.5"]["eta"]) / d72["table"]["E5_C0.5"]["eta"]

    # Exp81 duoplasmatron brightness at 10 keV
    B_81_Ti1 = 100.0 * 10000.0 / (math.pi * 1.0)
    err_81 = abs(B_81_Ti1 - d81["brightness"]["B_by_Ti"]["1.0"]) / B_81_Ti1

    # Exp82 filtered 10 keV dE=2 eV Cc=1 mm (uses 2.355 exactly)
    sc_82 = 1e6 * 0.010 * (2.0 / 2.355) / 10000.0
    st_82 = math.sqrt(5.0**2 + 2.0**2 + sc_82**2 + 0.5**2 + 0.5**2 + 0.3**2 + 1.0**2)
    err_82 = abs(st_82 - d82["grid"]["dE2_Cc1"]["sigma_total"]) / st_82

    # Exp91_budget_attack P91 (5 keV, Cc=0.5 mm, dE=2 eV, spot_geom=1.5, anneal=0.5)
    sc_91 = 0.5e6 * 0.010 * (2.0 / 2.355) / 5000.0
    eq_91 = math.sqrt(1.5**2 + sc_91**2 + 0.5**2 + 0.5**2 + 0.3**2 + 0.5**2)
    tot_91 = math.hypot(3.0, eq_91)
    err_91 = abs(tot_91 - d91b["p91"]["sigma_total"]) / tot_91

    # Exp92 BCA P91 total
    s_bca_5 = d92["bca"]["E5"]["sigma_x_nm"]
    tot_92 = math.hypot(s_bca_5, eq_91)
    err_92 = abs(tot_92 - d92["sigma_total_P91_BCA"]) / tot_92

    # Liouville / Lagrange-Helmholtz brightness audit of _attack91.py
    J_src = 100.0      # A/m^2 (US11289299B2)
    Ti_cons = 1.0      # eV (Exp81 conservative)
    tau_filt = 0.25    # 4x filter loss (Exp82)
    B_r_raw = J_src / (math.pi * Ti_cons)           # 31.831 A/m^2/sr/V
    B_r_net = tau_filt * B_r_raw                    # 7.9577 A/m^2/sr/V
    B_net_10keV = B_r_net * 10000.0                 # 79,577.5 A/m^2/sr
    B_net_5keV = B_r_net * 5000.0                   # 39,788.7 A/m^2/sr
    B_req_1p5_a10 = I_req / ((math.pi * (1.5e-9)**2) * (math.pi * (10e-3)**2))
    deficit_ratio = B_req_1p5_a10 / B_net_5keV      # 1.8133x deficit!
    r_geom_actual_a10_5keV_nm = (1.0 / (math.pi * 10e-3)) * math.sqrt(I_req / B_net_5keV) * 1e9

    max_rel_err = max(err_66, err_71, err_72_e10_c5, err_72_e5_c05, err_81, err_82, err_91, err_92)

    return {
        "anchor_rel_errors": {
            "exp66_euv_10keV": err_66,
            "exp71_B_req_2nm_10mrad": err_71,
            "exp72_E10_C5_rel_err": err_72_e10_c5,
            "exp72_E5_C0p5_rel_err": err_72_e5_c05,
            "exp81_B_Ti1_10keV": err_81,
            "exp82_dE2_Cc1_10keV": err_82,
            "exp91b_P91_sigma_total": err_91,
            "exp92_BCA_P91_sigma_total": err_92,
            "exp105_yield_3p8_recorded": d105["yield_38"],
            "exp105_prod_1000x1000_recorded": d105["production_1000x1000"],
        },
        "max_anchor_rel_err": max_rel_err,
        "liouville_audit_attack91": {
            "B_r_raw_A_m2_sr_V": B_r_raw,
            "B_r_net_after_4x_filter_A_m2_sr_V": B_r_net,
            "B_net_10keV_used_by_attack91_A_m2_sr": B_net_10keV,
            "B_net_5keV_liouville_exact_A_m2_sr": B_net_5keV,
            "B_req_1p5nm_10mrad_exact_A_m2_sr": B_req_1p5_a10,
            "brightness_deficit_factor_at_5keV_10mrad": deficit_ratio,
            "actual_r_geom_at_5keV_10mrad_Ti1_nm": r_geom_actual_a10_5keV_nm,
            "attack91_bugs_confirmed": [
                "Liouville violation: _attack91.py compared 5 keV spot B_req=7.22e4 against 10 keV B_net=7.96e4; exact B(5 keV)=B_r*5000=3.98e4 (1.81x deficit at alpha=10 mrad, Ti=1 eV).",
                "Clamped straggle below 5 keV: np.interp clamped E=3,4 keV to 3.0 nm, creating artificial 5 keV minimum (fixed by Exp92 BCA + Exp72 IBIC).",
                "Hybrid production bug: used Exp65 sigma=10 nm anchors (35000 shots, 34 specs) times 0.49 -> 6.05e5/day vs Exp105 self-consistent 2.92e7/day (48.2x off)."
            ]
        }
    }


# ---------------------------------------------------------------------------
# 2. Exact 2D Axisymmetric Laplace Solver & Ray-Tracing Electrostatic Lens
# ---------------------------------------------------------------------------

@dataclass
class ElectrodeSpec:
    """Axisymmetric annular aperture electrode: metal occupies r >= r_bore, z in [z0, z1]."""
    name: str
    z0_mm: float
    z1_mm: float
    r_bore_mm: float
    V_kin_V: float  # Equivalent ion kinetic potential Phi = V_src - V_elec (> 0)


@dataclass
class LensConfig:
    """Axisymmetric electrostatic multi-electrode micro/mini-lens cell."""
    name: str
    pitch_mm: float
    r_max_mm: float
    z_max_mm: float
    V_in_V: float
    V_land_V: float
    electrodes: list[ElectrodeSpec]
    nr: int = 121
    nz: int = 361


def solve_axisymmetric_laplace(cfg: LensConfig) -> dict[str, Any]:
    """Solve 2D axisymmetric Laplace eq (d2/dr2 + (1/r)d/dr + d2/dz2) Phi = 0 on (r,z)."""
    nr, nz = cfg.nr, cfg.nz
    r = np.linspace(0.0, cfg.r_max_mm, nr)
    z = np.linspace(0.0, cfg.z_max_mm, nz)
    hr = r[1] - r[0]
    hz = z[1] - z[0]

    # Classify Dirichlet nodes: entrance z=0, wafer z=z_max, electrodes
    is_dir = np.zeros((nr, nz), dtype=bool)
    val_dir = np.zeros((nr, nz), dtype=float)

    is_dir[:, 0] = True
    val_dir[:, 0] = cfg.V_in_V
    is_dir[:, -1] = True
    val_dir[:, -1] = cfg.V_land_V

    for el in cfg.electrodes:
        r_mask = r >= el.r_bore_mm - 1e-12
        z_mask = (z >= el.z0_mm - 1e-12) & (z <= el.z1_mm + 1e-12)
        mask = np.outer(r_mask, z_mask)
        is_dir |= mask
        val_dir[mask] = el.V_kin_V

    N = nr * nz
    rows, cols, vals = [], [], []
    rhs = np.zeros(N, dtype=float)

    inv_hr2 = 1.0 / (hr * hr)
    inv_hz2 = 1.0 / (hz * hz)

    idx = np.arange(N).reshape(nr, nz)

    # Dirichlet nodes
    di, dj = np.where(is_dir)
    d_idx = idx[di, dj]
    rows.append(d_idx)
    cols.append(d_idx)
    vals.append(np.ones_like(d_idx, dtype=float))
    rhs[d_idx] = val_dir[di, dj]

    # Interior free nodes (split into r=0 axis, 0<i<nr-1 interior, i=nr-1 outer Neumann)
    free = ~is_dir

    # (a) Axis i=0: 4*(Phi[1,j]-Phi[0,j])/hr^2 + (Phi[0,j+1]-2*Phi[0,j]+Phi[0,j-1])/hz^2 = 0
    j_ax = np.where(free[0, :])[0]
    if len(j_ax):
        c0 = idx[0, j_ax]
        rows.extend([c0, c0, c0, c0])
        cols.extend([c0, idx[1, j_ax], idx[0, j_ax + 1], idx[0, j_ax - 1]])
        vals.extend([
            np.full(len(j_ax), -4.0 * inv_hr2 - 2.0 * inv_hz2),
            np.full(len(j_ax), 4.0 * inv_hr2),
            np.full(len(j_ax), inv_hz2),
            np.full(len(j_ax), inv_hz2),
        ])

    # (b) Interior 1 <= i <= nr-2
    ii, jj = np.where(free[1:nr - 1, :])
    ii = ii + 1
    if len(ii):
        c0 = idx[ii, jj]
        ri = r[ii]
        c_rp = inv_hr2 + 1.0 / (2.0 * hr * ri)
        c_rm = inv_hr2 - 1.0 / (2.0 * hr * ri)
        rows.extend([c0, c0, c0, c0, c0])
        cols.extend([c0, idx[ii + 1, jj], idx[ii - 1, jj], idx[ii, jj + 1], idx[ii, jj - 1]])
        vals.extend([
            np.full(len(ii), -2.0 * inv_hr2 - 2.0 * inv_hz2),
            c_rp,
            c_rm,
            np.full(len(ii), inv_hz2),
            np.full(len(ii), inv_hz2),
        ])

    # (c) Outer radial wall i=nr-1: periodic cell symmetry dPhi/dr = 0 => Phi[nr] = Phi[nr-2]
    j_out = np.where(free[nr - 1, :])[0]
    if len(j_out):
        c0 = idx[nr - 1, j_out]
        rows.extend([c0, c0, c0, c0])
        cols.extend([c0, idx[nr - 2, j_out], idx[nr - 1, j_out + 1], idx[nr - 1, j_out - 1]])
        vals.extend([
            np.full(len(j_out), -2.0 * inv_hr2 - 2.0 * inv_hz2),
            np.full(len(j_out), 2.0 * inv_hr2),
            np.full(len(j_out), inv_hz2),
            np.full(len(j_out), inv_hz2),
        ])

    A = sparse.csc_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(N, N),
    )
    phi = spsolve(A, rhs).reshape(nr, nz)

    # Electric field magnitude in MV/m (V / mm = kV/m; / 1000 = MV/m)
    dphi_dr = np.gradient(phi, hr, axis=0)
    dphi_dz = np.gradient(phi, hz, axis=1)
    E_MV_m = np.hypot(dphi_dr, dphi_dz) / 1000.0
    # Compute peak E in vacuum region (free nodes) and mean gap E on axis
    E_max_vac_MV_m = float(np.max(E_MV_m[free]))
    # Exclude 1-cell sharp numerical 90-deg corner artifact to report both corner-grid E_max and
    # physically rounded-edge (r_fillet >= 2*h) E_995 / smooth gap field
    E_p995_MV_m = float(np.percentile(E_MV_m[free], 99.5))
    E_axis_max_MV_m = float(np.max(np.abs(dphi_dz[0, :]) / 1000.0))

    # Nominal parallel-plate gap fields between successive electrodes & final electrode->wafer
    gap_fields = []
    sorted_el = sorted(cfg.electrodes, key=lambda e: e.z0_mm)
    for a, b in zip(sorted_el[:-1], sorted_el[1:]):
        gap = b.z0_mm - a.z1_mm
        if gap > 0:
            gap_fields.append(abs(b.V_kin_V - a.V_kin_V) / gap / 1000.0)
    if sorted_el:
        wd = cfg.z_max_mm - sorted_el[-1].z1_mm
        if wd > 0:
            gap_fields.append(abs(cfg.V_land_V - sorted_el[-1].V_kin_V) / wd / 1000.0)
    E_gap_nom_MV_m = float(max(gap_fields)) if gap_fields else 0.0

    # Max residual on free interior nodes (sanity verification of PDE solution)
    lap_res = np.zeros_like(phi)
    lap_res[1:-1, 1:-1] = (
        (phi[2:, 1:-1] - 2 * phi[1:-1, 1:-1] + phi[:-2, 1:-1]) * inv_hr2
        + (phi[2:, 1:-1] - phi[:-2, 1:-1]) / (2.0 * hr * r[1:-1, None])
        + (phi[1:-1, 2:] - 2 * phi[1:-1, 1:-1] + phi[1:-1, :-2]) * inv_hz2
    )
    max_pde_residual = float(np.max(np.abs(lap_res[1:-1, 1:-1][free[1:-1, 1:-1]])))

    return {
        "r_mm": r,
        "z_mm": z,
        "phi": phi,
        "free": free,
        "E_MV_m": E_MV_m,
        "E_max_grid_MV_m": E_max_vac_MV_m,
        "E_p995_MV_m": E_p995_MV_m,
        "E_axis_max_MV_m": E_axis_max_MV_m,
        "E_gap_nom_MV_m": E_gap_nom_MV_m,
        "max_pde_residual": max_pde_residual,
    }


def trace_lens_optics(
    sol: dict[str, Any],
    cfg: LensConfig,
    dV_test_V: float = 2.0,
) -> dict[str, Any]:
    """Trace paraxial + chromatic + exact multipole non-paraxial rays through solved Laplace field.

    Uses quintic axial spline Phi_0(z) so Phi_0..Phi_0^(4) are continuous and satisfy
    axisymmetric Laplace equation analytically to O(r^6), eliminating radial FD grid noise
    near the axis. Cross-checks BOTH C_c (Scherzer vs direct chromatic ray trace) AND
    C_s (Scherzer integral vs exact 5th-order multipole non-paraxial ray trace).
    """
    z_grid = sol["z_mm"]
    phi0 = sol["phi"][0, :]
    sp0 = make_interp_spline(z_grid, phi0, k=5)
    sp1 = sp0.derivative(1)
    sp2 = sp0.derivative(2)
    sp3 = sp0.derivative(3)
    sp4 = sp0.derivative(4)

    z_end = float(z_grid[-1])

    def paraxial_rhs(z, y, dV=0.0):
        p = float(sp0(z)) + dV
        p1 = float(sp1(z))
        p2 = float(sp2(z))
        return [y[1], -(p1 / (2.0 * p)) * y[1] - (p2 / (4.0 * p)) * y[0]]

    # 1. Principal parallel ray r_par: r(0)=1, r'(0)=0
    sol_par = solve_ivp(
        lambda z, y: paraxial_rhs(z, y, 0.0),
        (0.0, z_end), [1.0, 0.0], method="DOP853", rtol=1e-11, atol=1e-13,
        max_step=z_end / 100.0, dense_output=True,
    )
    # 2. Linearly independent ray r_ang: r(0)=0, r'(0)=1 (for Wronskian / Liouville check)
    sol_ang = solve_ivp(
        lambda z, y: paraxial_rhs(z, y, 0.0),
        (0.0, z_end), [0.0, 1.0], method="DOP853", rtol=1e-11, atol=1e-13,
        max_step=z_end / 100.0, dense_output=True,
    )

    z_dense = np.linspace(0.0, z_end, 4001)
    rp_vals = sol_par.sol(z_dense)
    ra_vals = sol_ang.sol(z_dense)
    phi_dense = sp0(z_dense)

    # Exact Lagrange-Helmholtz Wronskian invariant: W(z) = sqrt(Phi0(z)) * (r_par*r_ang' - r_ang*r_par')
    W = np.sqrt(phi_dense) * (rp_vals[0] * ra_vals[1] - ra_vals[0] * rp_vals[1])
    wronskian_rel_drift = float(np.max(np.abs(W - W[0])) / abs(W[0]))

    # Find first paraxial focal crossing z_focus_mm
    r_par_z = rp_vals[0]
    cross_idx = np.where(np.diff(np.signbit(r_par_z)))[0]
    if len(cross_idx) > 0:
        k = int(cross_idx[0])
        a_z, b_z = float(z_dense[k]), float(z_dense[k + 1])
        for _ in range(50):
            m_z = 0.5 * (a_z + b_z)
            if sol_par.sol(m_z)[0] * sol_par.sol(a_z)[0] <= 0:
                b_z = m_z
            else:
                a_z = m_z
        z_focus_mm = 0.5 * (a_z + b_z)
        focused_inside = True
        r_wafer_signed = float(z_focus_mm - z_end)
    else:
        r_end, rp_end = float(sol_par.sol(z_end)[0]), float(sol_par.sol(z_end)[1])
        z_focus_mm = (z_end - r_end / rp_end) if rp_end < -1e-12 else float("inf")
        focused_inside = False
        r_wafer_signed = float(r_end)

    z_eval = z_focus_mm if (focused_inside and z_focus_mm <= z_end) else z_end
    _r_ev, rp_ev = sol_par.sol(z_eval)
    alpha_i_per_r0 = -float(rp_ev)
    f_img_mm = 1.0 / alpha_i_per_r0 if alpha_i_per_r0 > 1e-12 else float("inf")
    phi_i = float(sp0(z_eval))

    # 3. Positive-definite Scherzer chromatic integral C_c (prefactor sqrt(Phi_i) / alpha_i^2)
    z_int = np.linspace(0.0, z_eval, 4001)
    y_int = sol_par.sol(z_int)
    r_i = y_int[0]
    rp_i = y_int[1]
    p_i = sp0(z_int)
    p1_i = sp1(z_int)
    p2_i = sp2(z_int)
    integrand_cc = (1.0 / np.sqrt(p_i)) * (
        0.5 * (rp_i - (p1_i / (4.0 * p_i)) * r_i) ** 2
        + (5.0 / 32.0) * ((p1_i / p_i) ** 2) * (r_i ** 2)
    )
    Cc_scherzer_mm = float((phi_i ** 0.5) / (alpha_i_per_r0 ** 2) * np.trapezoid(integrand_cc, z_int))

    # 4. Direct finite-difference chromatic ray-trace cross-check (dV = +-dV_test_V)
    sol_p = solve_ivp(
        lambda z, y: paraxial_rhs(z, y, +dV_test_V),
        (0.0, z_eval), [1.0, 0.0], method="DOP853", rtol=1e-11, atol=1e-13, max_step=z_eval / 100.0,
    )
    sol_m = solve_ivp(
        lambda z, y: paraxial_rhs(z, y, -dV_test_V),
        (0.0, z_eval), [1.0, 0.0], method="DOP853", rtol=1e-11, atol=1e-13, max_step=z_eval / 100.0,
    )
    dr_chrom = 0.5 * (float(sol_p.y[0, -1]) - float(sol_m.y[0, -1]))
    Cc_raytrace_mm = float(dr_chrom / (alpha_i_per_r0 * (dV_test_V / phi_i)))
    Cc_rel_diff = abs(Cc_scherzer_mm - Cc_raytrace_mm) / max(abs(Cc_raytrace_mm), 1e-12)

    # 5a. Exact Scherzer spherical aberration integral C_s (Hawkes & Kasper Vol. 1 Eq. 24.53)
    t1 = (5.0 / 4.0) * ((p2_i / p_i) ** 2) * (r_i ** 4)
    t2 = (5.0 / 24.0) * ((p1_i / p_i) ** 4) * (r_i ** 4)
    t3 = (14.0 / 3.0) * ((p1_i / p_i) ** 3) * (r_i ** 3) * rp_i
    t4 = -(3.0 / 2.0) * ((p1_i / p_i) ** 2) * (r_i ** 2) * (rp_i ** 2)
    Cs_scherzer_mm = float(
        (1.0 / (16.0 * (phi_i ** 0.5) * (alpha_i_per_r0 ** 4)))
        * np.trapezoid(np.sqrt(p_i) * (t1 + t2 + t3 + t4), z_int)
    )

    # 5b. Direct non-paraxial ray tracing in exact axisymmetric multipole potential Phi(r,z)
    # Use a gentle quintic smoothing spline (s=1e-2 V^2 on ~10^4 V -> <1e-7 relative shift)
    # to prevent finite-difference 1/h^4 corner-ripple amplification in Phi_0^(4)(z).
    min_bore = min(el.r_bore_mm for el in cfg.electrodes)
    sp_sm = UnivariateSpline(z_grid, phi0, k=5, s=1e-2)
    sp_sm1 = sp_sm.derivative(1)
    sp_sm2 = sp_sm.derivative(2)
    sp_sm3 = sp_sm.derivative(3)
    sp_sm4 = sp_sm.derivative(4)

    def multipole_rhs(z, y):
        rv, rpv = y[0], y[1]
        p0 = float(sp_sm(z))
        p1 = float(sp_sm1(z))
        p2 = float(sp_sm2(z))
        p3 = float(sp_sm3(z))
        p4 = float(sp_sm4(z))
        p = max(10.0, p0 - 0.25 * rv * rv * p2 + (rv ** 4) / 64.0 * p4)
        pr = -0.5 * rv * p2 + (rv ** 3) / 16.0 * p4
        pz = p1 - 0.25 * rv * rv * p3
        return [rpv, ((1.0 + rpv * rpv) / (2.0 * p)) * (pr - rpv * pz)]

    r0_test = 0.008 * min_bore
    # Re-locate exact paraxial focus of sp_sm so tiny spline shift doesn't leak defocus into Cs!
    def par_sm(z, y):
        p = float(sp_sm(z))
        return [y[1], -(float(sp_sm1(z)) / (2.0 * p)) * y[1] - (float(sp_sm2(z)) / (4.0 * p)) * y[0]]
    sol_sm_par = solve_ivp(par_sm, (0.0, z_end), [r0_test, 0.0], method="DOP853", rtol=1e-12, atol=1e-14, max_step=z_end / 100.0)
    sol_np = solve_ivp(
        multipole_rhs, (0.0, z_end), [r0_test, 0.0],
        method="DOP853", rtol=1e-12, atol=1e-14, max_step=z_end / 100.0,
    )
    # Compare non-paraxial ray directly against paraxial ray at z_end (exact spherical difference dr_sph!)
    dr_sph = float(sol_sm_par.y[0, -1] - sol_np.y[0, -1])
    alpha_sm = -float(sol_sm_par.y[1, -1])
    Cs_multipole_mm = float(dr_sph / (alpha_sm ** 3))
    Cs_rel_diff = abs(Cs_scherzer_mm - Cs_multipole_mm) / max(abs(Cs_scherzer_mm), 1e-12)

    last_el = max(cfg.electrodes, key=lambda e: e.z1_mm)
    wd_mm = float(z_eval - last_el.z1_mm)
    # Dimensionless Scherzer-breakdown invariant kappa_c = Cc * E_gap / V_land
    kappa_c = float(Cc_scherzer_mm * (sol["E_gap_nom_MV_m"] * 1000.0) / cfg.V_land_V)

    return {
        "name": cfg.name,
        "pitch_mm": cfg.pitch_mm,
        "min_bore_mm": min_bore,
        "V_in_V": cfg.V_in_V,
        "V_land_V": cfg.V_land_V,
        "z_wafer_mm": z_end,
        "z_focus_paraxial_mm": z_focus_mm,
        "focus_error_um": abs(z_focus_mm - z_end) * 1000.0,
        "working_distance_mm": wd_mm,
        "f_img_mm": f_img_mm,
        "f_over_D": f_img_mm / (2.0 * min_bore),
        "phi_min_axis_V": float(np.min(phi0)),
        "wronskian_rel_drift": wronskian_rel_drift,
        "Cc_scherzer_mm": Cc_scherzer_mm,
        "Cc_raytrace_mm": Cc_raytrace_mm,
        "Cc_scherzer_vs_raytrace_rel_diff": Cc_rel_diff,
        "Cs_scherzer_mm": Cs_scherzer_mm,
        "Cs_nonparaxial_mm": Cs_multipole_mm,
        "Cs_scherzer_vs_multipole_rel_diff": Cs_rel_diff,
        "E_gap_nom_MV_m": sol["E_gap_nom_MV_m"],
        "E_axis_max_MV_m": sol["E_axis_max_MV_m"],
        "E_p995_MV_m": sol["E_p995_MV_m"],
        "E_max_grid_MV_m": sol["E_max_grid_MV_m"],
        "kappa_c_invariant": kappa_c,
        "max_pde_residual": sol["max_pde_residual"],
        "focused_at_wafer": bool(abs(z_focus_mm - z_end) < 0.015 * z_end),
        "r_wafer_signed": r_wafer_signed,
    }


def _fast_paraxial_metric(z_grid: np.ndarray, phi0: np.ndarray) -> tuple[float, float]:
    """Fast paraxial-only focus residual for rapid linear-superposition tuning."""
    if float(np.min(phi0)) <= 50.0:
        return -1e3, 1e6  # ion mirror / reflected (too low V_mid)
    cs0 = CubicSpline(z_grid, phi0, bc_type="natural")
    cs1 = cs0.derivative(1)
    cs2 = cs0.derivative(2)
    z_end = float(z_grid[-1])

    def rhs(z, y):
        p = float(cs0(z))
        return [y[1], -(float(cs1(z)) / (2.0 * p)) * y[1] - (float(cs2(z)) / (4.0 * p)) * y[0]]

    sol = solve_ivp(rhs, (0.0, z_end), [1.0, 0.0], method="RK45", rtol=1e-8, atol=1e-10,
                    max_step=z_end / 80.0, dense_output=True)
    z_d = np.linspace(0.0, z_end, 1001)
    r_d = sol.sol(z_d)[0]
    cross = np.where(np.diff(np.signbit(r_d)))[0]
    if len(cross) > 0:
        k = int(cross[0])
        a, b = float(z_d[k]), float(z_d[k + 1])
        for _ in range(30):
            m = 0.5 * (a + b)
            if sol.sol(m)[0] * sol.sol(a)[0] <= 0:
                b = m
            else:
                a = m
        zf = 0.5 * (a + b)
        return float(zf - z_end), abs(zf - z_end) * 1000.0
    r_end = float(sol.sol(z_end)[0])
    rp_end = float(sol.sol(z_end)[1])
    zf = (z_end - r_end / rp_end) if rp_end < -1e-12 else float("inf")
    return float(r_end), abs(zf - z_end) * 1000.0


def tune_einzel_focus(make_cfg_fn, v_lo: float, v_hi: float, tol_um: float = 1.0) -> tuple[LensConfig, dict[str, Any], dict[str, Any]]:
    """Exact Laplace linear-superposition tuner: only 2 PDE solves total per lens!"""
    cfg0 = make_cfg_fn(v_lo)
    cfg1 = make_cfg_fn(v_hi)
    sol0 = solve_axisymmetric_laplace(cfg0)
    sol1 = solve_axisymmetric_laplace(cfg1)
    z_grid = sol0["z_mm"]
    phi0_lo = sol0["phi"][0, :]
    phi0_hi = sol1["phi"][0, :]

    def metric(vm: float) -> tuple[float, float]:
        t = (vm - v_lo) / (v_hi - v_lo)
        phi0 = (1.0 - t) * phi0_lo + t * phi0_hi
        return _fast_paraxial_metric(z_grid, phi0)

    # Scan 21 points (takes ~0.05s total!) to locate exact focus bracket
    scan_vs = np.linspace(v_lo, v_hi, 21)
    vals = [metric(float(v))[0] for v in scan_vs]
    bracket = None
    # Prefer highest-V_mid bracket (weakest deceleration = lowest aberration / no mirror)
    for i in range(len(scan_vs) - 2, -1, -1):
        if vals[i] > -500.0 and vals[i + 1] > -500.0:
            if (vals[i] <= 0.0 <= vals[i + 1]) or (vals[i] >= 0.0 >= vals[i + 1]):
                bracket = (float(scan_vs[i]), float(scan_vs[i + 1]), vals[i], vals[i + 1])
                break
    if bracket is None:
        raise ValueError(f"Focus bracket failed across [{v_lo}, {v_hi}]: {list(zip(scan_vs.round(1), np.round(vals, 5)))}")

    a, b, fa, fb = bracket
    for _ in range(24):
        m = 0.5 * (a + b)
        fm, err_um = metric(m)
        if err_um <= tol_um:
            a = b = m
            break
        if fm * fa <= 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    v_opt = 0.5 * (a + b)
    cfg_opt = make_cfg_fn(v_opt)
    sol_opt = solve_axisymmetric_laplace(cfg_opt)
    tr_opt = trace_lens_optics(sol_opt, cfg_opt)
    tr_opt["V_focus_electrode_V"] = v_opt
    return cfg_opt, sol_opt, tr_opt


def build_and_solve_lens_architectures() -> dict[str, Any]:
    """Solve & compare 5 physical electrostatic lens architectures at E_land=5 keV."""
    out = {}

    # 1. Arch-A1: Direct 32 um-pitch (D=18 um) 10->5 keV at WD=0.06 mm (exposes UHV breakdown wall!)
    def make_arch_a1(v_mid: float) -> LensConfig:
        return LensConfig(
            name="Arch-A1_32um_shortWD_breakdown",
            pitch_mm=0.032, r_max_mm=0.016, z_max_mm=0.160,
            V_in_V=10000.0, V_land_V=5000.0,
            electrodes=[
                ElectrodeSpec("E1_top", 0.030, 0.042, 0.009, 10000.0),
                ElectrodeSpec("E2_einzel", 0.058, 0.072, 0.009, v_mid),
                ElectrodeSpec("E3_ret", 0.088, 0.100, 0.009, 10000.0),
            ],
            nr=49, nz=241,
        )
    cfg_a1, sol_a1, tr_a1 = tune_einzel_focus(make_arch_a1, 1500.0, 9500.0, tol_um=0.5)
    out["Arch-A1_32um_shortWD"] = tr_a1

    # 2. Arch-A2: Direct 32 um-pitch (D=18 um) 10->5 keV at WD=0.50 mm (exposes spherical aberration wall!)
    def make_arch_a2(v_mid: float) -> LensConfig:
        return LensConfig(
            name="Arch-A2_32um_longWD_Cs_wall",
            pitch_mm=0.032, r_max_mm=0.016, z_max_mm=0.600,
            V_in_V=10000.0, V_land_V=5000.0,
            electrodes=[
                ElectrodeSpec("E1_top", 0.030, 0.042, 0.009, 10000.0),
                ElectrodeSpec("E2_einzel", 0.058, 0.072, 0.009, v_mid),
                ElectrodeSpec("E3_ret", 0.088, 0.100, 0.009, 10000.0),
            ],
            nr=49, nz=301,
        )
    cfg_a2, sol_a2, tr_a2 = tune_einzel_focus(make_arch_a2, 4000.0, 9900.0, tol_um=2.0)
    out["Arch-A2_32um_longWD"] = tr_a2

    # 3. Arch-B (RECOMMENDED GOLDEN BASELINE): 0.50 mm-pitch Field-Free-Wafer Retarding Immersion Mini-Lens
    #    D_bore = 0.30 mm (r_bore = 0.15 mm), 10 -> V_foc(~1.3 kV) -> 5 keV -> field-free 5 keV wafer!
    #    Every single inter-electrode gap <= 10.6 MV/m (breakdown-safe UHV!), WD = 0.25 mm!
    def make_arch_b(v_mid: float) -> LensConfig:
        return LensConfig(
            name="Arch-B_0p5mm_immersion_minilens",
            pitch_mm=0.500, r_max_mm=0.250, z_max_mm=2.010,
            V_in_V=10000.0, V_land_V=5000.0,
            electrodes=[
                ElectrodeSpec("E1_liner_10kV", 0.200, 0.300, 0.150, 10000.0),
                ElectrodeSpec("E2_focus", 1.120, 1.280, 0.150, v_mid),
                ElectrodeSpec("E3_ground_5kV", 1.660, 1.760, 0.150, 5000.0),
            ],
            nr=81, nz=321,
        )
    cfg_b, sol_b, tr_b = tune_einzel_focus(make_arch_b, 800.0, 4500.0, tol_um=1.0)
    out["Arch-B_0p5mm_immersion"] = tr_b

    # 4. Arch-B15: 15 -> 5 keV Immersion Mini-Lens Variant (0.60 mm pitch, D=0.28 mm, WD=0.48 mm, E_gap <= 11.1 MV/m)
    def make_arch_b15(v_mid: float) -> LensConfig:
        return LensConfig(
            name="Arch-B15_0p6mm_15to5keV_immersion",
            pitch_mm=0.600, r_max_mm=0.300, z_max_mm=2.620,
            V_in_V=15000.0, V_land_V=5000.0,
            electrodes=[
                ElectrodeSpec("E1_liner_15kV", 0.200, 0.320, 0.140, 15000.0),
                ElectrodeSpec("E2_focus", 1.500, 1.700, 0.140, v_mid),
                ElectrodeSpec("E3_ground_5kV", 2.020, 2.140, 0.140, 5000.0),
            ],
            nr=73, nz=321,
        )
    cfg_b15, sol_b15, tr_b15 = tune_einzel_focus(make_arch_b15, 1000.0, 4800.0, tol_um=1.5)
    out["Arch-B15_15to5keV"] = tr_b15

    # 5. Arch-C: Breakdown-Safe (<=10 MV/m) 2-Stage Pre-Retarded 32 um-Pitch Micro-Lens (10->5.5->5.0 keV)
    #    Demonstrates that even at 32 um pitch, enforcing E_gap <= 10 MV/m forces Cc ~ 2.38 mm (kappa_c invariant!)
    def make_arch_c(v_mid: float) -> LensConfig:
        return LensConfig(
            name="Arch-C_32um_2stage_10MVm",
            pitch_mm=0.032, r_max_mm=0.016, z_max_mm=1.023,
            V_in_V=5500.0, V_land_V=5000.0,
            electrodes=[
                ElectrodeSpec("E1_5p5kV", 0.040, 0.060, 0.009, 5500.0),
                ElectrodeSpec("E2_focus", 0.500, 0.530, 0.009, v_mid),
                ElectrodeSpec("E3_ground_5kV", 0.920, 0.940, 0.009, 5000.0),
            ],
            nr=49, nz=301,
        )
    cfg_c, sol_c, tr_c = tune_einzel_focus(make_arch_c, 600.0, 3500.0, tol_um=1.0)
    tr_c["pre_retard_stage"] = {
        "V_in_V": 10000.0, "V_out_V": 5500.0, "gap_mm": 0.750,
        "E_pre_MV_m": (10000.0 - 5500.0) / 0.750 / 1000.0,
        "blanker_voltage_5p5keV_V": 53.3333333 * (5500.0 / 10000.0),
    }
    out["Arch-C_32um_2stage"] = tr_c

    # 6. Arch-D: MEMS Micro-Gap Variant (D=50 um, g=100 um, E_gap=35 MV/m — micro-gap Clump/FN vacuum limit!)
    def make_arch_d(v_mid: float) -> LensConfig:
        return LensConfig(
            name="Arch-D_MEMS_microgap_35MVm",
            pitch_mm=0.100, r_max_mm=0.050, z_max_mm=0.570,
            V_in_V=5500.0, V_land_V=5000.0,
            electrodes=[
                ElectrodeSpec("E1_5p5kV", 0.040, 0.060, 0.025, 5500.0),
                ElectrodeSpec("E2_focus", 0.160, 0.190, 0.025, v_mid),
                ElectrodeSpec("E3_ground_5kV", 0.290, 0.310, 0.025, 5000.0),
            ],
            nr=57, nz=285,
        )
    cfg_d, sol_d, tr_d = tune_einzel_focus(make_arch_d, 1200.0, 4200.0, tol_um=1.0)
    out["Arch-D_MEMS_microgap35"] = tr_d

    return {
        "architectures": out,
        "solutions_for_plot": {
            "Arch-B": (cfg_b, sol_b, tr_b),
            "Arch-C": (cfg_c, sol_c, tr_c),
            "Arch-D": (cfg_d, sol_d, tr_d),
        },
    }


def solve_arch_b_at_landing_energy(
    E_land_keV: float,
    V_in_V: float = 10000.0,
    nr: int = 65,
    nz: int = 261,
) -> dict[str, Any]:
    """Re-solve exact 2D Laplace + DOP853 Arch-B optics at arbitrary landing energy (OBS-132).

    Avoids reusing fixed 5 keV Cc/Cs across 2-10 keV and exposes E_gap > 12 MV/m breakdown
    at high E_land (7.5-10 keV) when V_in=10 kV is held constant.
    """
    V_land = float(E_land_keV) * 1000.0

    def make_cfg(v_mid: float) -> LensConfig:
        return LensConfig(
            name=f"Arch-B_Eland_{E_land_keV:g}keV_Vin_{V_in_V/1000:g}kV",
            pitch_mm=0.500, r_max_mm=0.250, z_max_mm=2.010,
            V_in_V=V_in_V, V_land_V=V_land,
            electrodes=[
                ElectrodeSpec("E1_liner", 0.200, 0.300, 0.150, V_in_V),
                ElectrodeSpec("E2_focus", 1.120, 1.280, 0.150, v_mid),
                ElectrodeSpec("E3_ground", 1.660, 1.760, 0.150, V_land),
            ],
            nr=nr, nz=nz,
        )

    v_lo = max(120.0, 0.08 * min(V_in_V, V_land))
    v_hi = max(V_in_V, V_land) * 0.95
    _, _, tr = tune_einzel_focus(make_cfg, v_lo, v_hi, tol_um=2.0)
    tr["breakdown_safe_12MVm"] = bool(tr["E_gap_nom_MV_m"] <= 12.0)
    return tr


def evaluate_hda_space_charge(
    I_hda_A: float = 50e-9,
    E_pass_eV: float = 100.0,
    R0_mm: float = 40.0,
    r_beam_mm: float = 0.35,
) -> dict[str, float]:
    """Evaluate 100 eV HDA laminar space-charge & Holtsmark expansion + current guard (OBS-103).

    Inside S1.5-01 HDA-HiRes (L = pi * R0 = 125.66 mm, E_pass = 100 eV), decelerating 50 nA
    increases E^(-3/2) by 1,000x, causing dr_sc = 8.12 mm explosion unless current is
    aperture-limited upstream to <= 0.25-0.50 nA.
    """
    L_hda_m = math.pi * (R0_mm * 1e-3)
    r_b_m = r_beam_mm * 1e-3
    v_pass = math.sqrt(2.0 * E_CHARGE * E_pass_eV / M_P31)
    lam = I_hda_A / (E_CHARGE * v_pass)
    n_vol = lam / (math.pi * r_b_m ** 2)
    ke_e = E_CHARGE / (4.0 * math.pi * EPS0)
    E_H = 2.603 * ke_e * (n_vol ** (2.0 / 3.0))
    dr_holts_m = 0.25 * E_H * (L_hda_m ** 2) / E_pass_eV
    dr_sc_m = (I_hda_A * (L_hda_m ** 2)) / (
        4.0 * math.pi * EPS0 * math.sqrt(2.0 * E_CHARGE / M_P31) * r_b_m * (E_pass_eV ** 1.5)
    )
    # Safe upper current keeping dr_sc <= 0.25 * r_beam (<= 87.5 um)
    I_guard_A = 0.25 * r_b_m * (
        4.0 * math.pi * EPS0 * math.sqrt(2.0 * E_CHARGE / M_P31) * r_b_m * (E_pass_eV ** 1.5)
    ) / (L_hda_m ** 2)
    return {
        "E_pass_eV": float(E_pass_eV),
        "L_hda_mm": float(L_hda_m * 1e3),
        "r_beam_mm": float(r_beam_mm),
        "I_hda_nA": float(I_hda_A * 1e9),
        "dr_sc_laminar_um": float(dr_sc_m * 1e6),
        "dr_holtsmark_um": float(dr_holts_m * 1e6),
        "I_guard_max_nA": float(I_guard_A * 1e9),
        "passes_hda_space_charge_guard": bool(I_hda_A <= I_guard_A),
    }


# ---------------------------------------------------------------------------
# 3. Wien Filter, HDA Energy Filter, Boersch/Coulomb & Spot Budget
# ---------------------------------------------------------------------------

def wien_mass_filter(E_ext_eV: float = 10000.0, B_T: float = 0.45,
                     L_w_mm: float = 80.0, L_drift_mm: float = 70.0,
                     gap_mm: float = 12.0, slit_mm: float = 0.20) -> dict[str, float]:
    """Crossed E x B Wien mass filter for 31P+ vs 32PH+, 33PH2+, 34PH3+."""
    v0 = math.sqrt(2.0 * E_CHARGE * E_ext_eV / M_P31)
    E_w_V_m = v0 * B_T
    V_plates_V = E_w_V_m * (gap_mm * 1e-3)
    # Deflection angle for mass m + dm: theta = (q*B*L_w)/(m*v0) * (1 - sqrt(m/(m+dm)))
    # = (E_w * L_w / (2 * V_ext)) * (1 - sqrt(m/(m+dm)))
    pref = (E_w_V_m * (L_w_mm * 1e-3)) / (2.0 * E_ext_eV)
    theta_32 = pref * (1.0 - math.sqrt(M_P31 / M_PH32))
    dx_32_mm = theta_32 * (0.5 * L_w_mm + L_drift_mm)
    # Mass resolving power R_m = m/dm where dx(dm) = slit_mm -> approx (dx_32/slit) * 31
    R_mass = (dx_32_mm / slit_mm) * (M_P31 / (M_PH32 - M_P31))
    return dict(
        E_ext_eV=E_ext_eV, v0_m_s=v0, B_T=B_T, E_w_kV_m=E_w_V_m / 1e3,
        V_plates_V=V_plates_V, gap_mm=gap_mm, L_w_mm=L_w_mm, L_drift_mm=L_drift_mm,
        slit_mm=slit_mm, theta_32PH_mrad=theta_32 * 1e3,
        dx_32PH_mm=dx_32_mm, separation_over_slit=dx_32_mm / slit_mm,
        mass_resolving_power=R_mass,
    )


def hda_energy_filter(E_pass_eV: float = 200.0, R0_mm: float = 40.0,
                      slit_mm: float = 0.70, alpha_in_mrad: float = 30.0,
                      dE_src_fwhm_eV: float = 6.0) -> dict[str, float]:
    """Hemispherical Deflector Analyzer (pre-retarded to E_pass, re-accelerated to E_ext)."""
    alpha = alpha_in_mrad * 1e-3
    dE_fwhm = E_pass_eV * (slit_mm / (2.0 * R0_mm) + 0.25 * alpha * alpha)
    # Exact Gaussian transmission of central window +-dE_fwhm/2 from source FWHM dE_src_fwhm
    sigma_src = dE_src_fwhm_eV / FWHM_TO_SIGMA
    tau_gauss = float(erf((0.5 * dE_fwhm) / (math.sqrt(2.0) * sigma_src)))
    return dict(
        E_pass_eV=E_pass_eV, R0_mm=R0_mm, slit_mm=slit_mm, alpha_in_mrad=alpha_in_mrad,
        dE_fwhm_eV=dE_fwhm, dE_src_fwhm_eV=dE_src_fwhm_eV,
        tau_gaussian_exact=tau_gauss, tau_conservative_exp82=0.25,
    )


def boersch_and_coulomb(
    E_col_eV: float,
    I_flood_A: float = 50e-9,
    L_col_m: float = 0.35,
    r_beam_m: float = 2.0e-3,
    alpha_col_rad: float = 1e-3,
    I_beamlet_A: float = E_CHARGE / 1e-3,
    L_head_m: float = 0.005,
    E_land_eV: float = 5000.0,
    f_img_m: float = 0.8202e-3,
) -> dict[str, float]:
    """Jansen (1990) stochastic Coulomb interaction estimates: upper flood column & single beamlet.

    Standard cylindrical-beam Boersch energy spread (Jansen, Adv. Electronics & Electron Phys. Suppl. 21):
      dE_B,FWHM ~ C_B * (m/q)^(1/4) * I^(1/2) / (E^(1/4) * r_b^(1/2)) * ...
    Specifically in the Holtsmark/Gaussian-crossover & cylindrical-beam regime:
      sigma_E_B = (e / (4*pi*eps0)) * sqrt( (2 * pi * lambda_lin) / r_eff ) ...
    Using exact Jansen cylindrical pencil/flood beam formula:
      linear ion density lambda_lin = I / (e * v), mean axial spacing d_z = 1 / lambda_lin.
      Nearest-neighbor Coulomb potential energy scale: U_nn = e^2 / (4*pi*eps0 * d_avg).
      Trajectory displacement in a drift of length L scales as:
        sigma_r_C = C_t * (e / (4*pi*eps0)) * (I / (v * E_J)) * L / r_beam * ...
      Specifically for uncorrelated stochastic kicks in a beam of radius r_b, current I, drift L:
        RMS transverse kick angle per unit length scales as I^(1/2) / (v^(3/2) * r_b^(1/2)),
        and in the Holtsmark dilute regime (d_z >> r_b, exact for nA beams!):
        dE_B_rms (eV) ~ 0.5 * (e / (4*pi*eps0)) * sqrt(lambda_lin / r_b)  (weakly dependent on L)
        sigma_r_C (m) ~ 0.14 * (e / (4*pi*eps0)) * (I / (e * v))^(2/3) * L^2 / (E_eV)  [Holtsmark 2/3-power]
        and in continuous-collision Gaussian regime (Loeffler/Jansen):
        sigma_r_C_Loeffler = (e / (4*pi*eps0 * E_eV)) * sqrt(lambda_lin * L) * (L / r_b) * (1 / sqrt(8*pi))
    """
    v_col = math.sqrt(2.0 * E_CHARGE * E_col_eV / M_P31)
    v_land = math.sqrt(2.0 * E_CHARGE * E_land_eV / M_P31)
    lam_flood = I_flood_A / (E_CHARGE * v_col)  # ions/m in upper flood beam
    d_ax_flood = 1.0 / lam_flood

    # Single-beamlet occupancy in whole column & in final head
    t_tof_col = L_col_m / v_col
    t_tof_head = L_head_m / v_land
    N_bar_beamlet_col = (I_beamlet_A / E_CHARGE) * t_tof_col
    N_bar_beamlet_head = (I_beamlet_A / E_CHARGE) * t_tof_head

    # Coulomb constant k_e * e in V*m: e/(4*pi*eps0) = 1.43996e-9 V*m
    ke_e = E_CHARGE / (4.0 * math.pi * EPS0)

    # Upper flood beam: mean 3D inter-ion spacing d_3D = (pi * r_b^2 / lam_flood)^(1/3)
    n_vol = lam_flood / (math.pi * r_beam_m ** 2)
    d_3D = n_vol ** (-1.0 / 3.0)
    # Thermodynamic/Boersch longitudinal energy spread generated from potential energy relaxation
    # dE_B_fwhm ~ 2.355 * sqrt( (ke_e * e / d_3D) * kT_perp )? In Jansen's cylindrical limit:
    # dE_rms (eV) = sqrt(2) * ke_e * sqrt(lam_flood / r_beam_m) * (for cylindrical beam, upper bound)
    dE_boersch_rms_eV = math.sqrt(2.0) * ke_e * math.sqrt(lam_flood / r_beam_m)
    dE_boersch_fwhm_eV = FWHM_TO_SIGMA * dE_boersch_rms_eV

    # Stochastic transverse trajectory displacement in flood beam (Jansen/Loeffler scaling ~ I^0.5 * L^1.5 / (E^1.25 * r_b^0.5)
    # Wait: compute exact RMS transverse kick from Coulomb encounters over drift L_col:
    # Transverse impulse per encounter at impact param b: dv_perp = 2*e^2/(4*pi*eps0 * m * v_rel * b)
    # Mean transverse electric field in cylindrical beam of density n_vol: E_rms ~ 2.603 * ke_e * n_vol^(2/3) (Holtsmark)
    # Over flight time t = L/v, lateral displacement (Holtsmark): dr_H = 0.5 * (q/m) * E_H * t^2
    #   = 0.5 * (E_H * L^2) / (2 * E_col_eV) = 0.25 * E_H * L^2 / E_col_eV !
    # Notice E_H ~ n_vol^(2/3) ~ (I / v)^(2/3) ~ E_col^(-1/3), so dr_H ~ E_col^(-4/3)!!
    # And space-charge defocusing (laminar): dr_sc = (I * L^2) / (16*pi*eps0 * sqrt(2q/m) * r_b * E_col^(3/2)) ~ E_col^(-3/2)!!
    E_holtsmark_V_m = 2.603 * ke_e * (n_vol ** (2.0 / 3.0))
    dr_holtsmark_m = 0.25 * E_holtsmark_V_m * (L_col_m ** 2) / E_col_eV
    # Referred to wafer after demagnification M_demag (for flood beam -> micro-aperture, angular spread dtheta = dr_H / L_col)
    dtheta_coul_rad = 0.5 * E_holtsmark_V_m * L_col_m / E_col_eV

    # Laminar space-charge radial expansion at edge of flood beam (scales STRICTLY as E_col^(-3/2))
    dr_sc_laminar_m = (I_flood_A * (L_col_m ** 2)) / (
        4.0 * math.pi * EPS0 * math.sqrt(2.0 * E_CHARGE / M_P31) * r_beam_m * (E_col_eV ** 1.5)
    )

    # Referred spot blur at wafer using actual Arch-B f_img=0.8202 mm (OBS-103: fixed from legacy 0.5 mm!)
    # Note: flood-column angular kicks upstream of S2.1 dilute virtual-source brightness rather than
    # adding directly after the 10.5 um aperture; downstream of S2.1 single-beamlet N_bar ~ 1e-7 -> ~0 nm.
    sigma_coul_wafer_nm = dtheta_coul_rad * f_img_m * 1e9
    # Downstream beamlet-only Holtsmark kick inside head (L_head, I_beamlet): virtually zero
    lam_b = I_beamlet_A / (E_CHARGE * v_land)
    n_vol_b = lam_b / (math.pi * (5.25e-6) ** 2)
    E_H_b = 2.603 * ke_e * (n_vol_b ** (2.0 / 3.0))
    sigma_coul_beamlet_nm = (0.25 * E_H_b * (L_head_m ** 2) / E_land_eV) * 1e9

    return dict(
        E_col_eV=E_col_eV,
        I_flood_nA=I_flood_A * 1e9,
        f_img_mm=f_img_m * 1e3,
        v_col_m_s=v_col,
        lambda_flood_per_m=lam_flood,
        d_axial_flood_um=d_ax_flood * 1e6,
        d_3D_flood_um=d_3D * 1e6,
        dE_boersch_fwhm_eV=dE_boersch_fwhm_eV,
        dr_holtsmark_flood_um=dr_holtsmark_m * 1e6,
        dr_sc_laminar_um=dr_sc_laminar_m * 1e6,
        dtheta_coul_urad=dtheta_coul_rad * 1e6,
        sigma_coul_wafer_nm=sigma_coul_wafer_nm,
        sigma_coul_beamlet_downstream_nm=sigma_coul_beamlet_nm,
        single_beamlet_Nbar_col=N_bar_beamlet_col,
        single_beamlet_Nbar_head=N_bar_beamlet_head,
        single_beamlet_P_ge2_col=1.0 - math.exp(-N_bar_beamlet_col) * (1.0 + N_bar_beamlet_col),
    )


def evaluate_spot_budget(
    E_land_keV: float,
    Cc_mm: float,
    Cs_mm: float,
    alpha_land_mrad: float,
    dE_fwhm_eV: float = 2.0,
    J_src_A_m2: float = 100.0,
    Ti_eV: float = 1.0,
    tau_filter: float = 0.25,
    tau_shot_ms: float = 1.0,
    sigma_stage_nm: float = 0.5,
    sigma_pointing_nm: float = 0.5,
    sigma_thermal_nm: float = 0.3,
    sigma_anneal_nm: float = 0.5,
    sigma_coul_nm: float = 0.0,
    C_ibic_pF: float = 0.5,
    psu_stability_ppm: float = 46.8,
    dv_psu_rms_V: float | None = None,
    dead_layer_nm: float = 1.5,
    ibic_thr_sigma: float = 6.2,
) -> dict[str, float]:
    """Liouville-exact 1D-RMS spot & total placement error budget at E_land (OBS-039/076/098/150).

    Standardizes on 1D RMS Barth-Kruit definitions (OBS-150):
      - Uniform top-hat disk of radius r_geom has 1D RMS sigma_geom = 0.5 * r_geom.
      - Uniform circular aperture illumination of semi-angle alpha has 1D RMS angle alpha/2,
        so chromatic 1D RMS blur is sigma_c = 0.5 * Cc * alpha * (sigma_E / E_land).
    Includes HV PSU ripple & DC stability sigma_psu (OBS-076, default <= 46.8 ppm tightened spec),
    corrected infinite-domain ZBL/iradina straggle (OBS-039), and synchronized Exp127 IBIC (OBS-098).
    """
    E_land_eV = E_land_keV * 1000.0
    alpha = alpha_land_mrad * 1e-3
    I_b = E_CHARGE / (tau_shot_ms * 1e-3)

    # Exact Liouville reduced brightness conserved through electrostatic deceleration
    B_r_net = tau_filter * J_src_A_m2 / (math.pi * Ti_eV)  # A / (m^2 sr V)
    B_land = B_r_net * E_land_eV                           # A / (m^2 sr)

    # Top-hat source-image radius r_geom (Exp71 convention) -> 1D RMS = r_geom / 2 (OBS-150)
    r_geom_tophat_nm = (1.0 / (math.pi * alpha)) * math.sqrt(I_b / B_land) * 1e9
    sigma_geom_nm = 0.5 * r_geom_tophat_nm

    # Chromatic 1D RMS blur with 0.5 uniform-aperture projection factor (OBS-150)
    sigma_c_edge_nm = (Cc_mm * 1e6) * alpha * ((dE_fwhm_eV / FWHM_TO_SIGMA) / E_land_eV)
    sigma_c_nm = 0.5 * sigma_c_edge_nm

    # HV PSU ripple & DC stability chromatic defocus (OBS-076: <= 46.8 ppm spec -> dv_rms_V)
    if dv_psu_rms_V is None:
        dv_eff_V = (psu_stability_ppm * 1e-6) * E_land_eV
    else:
        dv_eff_V = float(dv_psu_rms_V)
    sigma_psu_nm = 0.5 * (Cc_mm * 1e6) * alpha * (dv_eff_V / E_land_eV)

    # Spherical 1-sigma blur at disk of least confusion (Barth-Kruit / Reimer: r_min = 0.25 Cs a^3, rms ~ r_min / sqrt(2))
    r_sph_min_nm = 0.25 * (Cs_mm * 1e6) * (alpha ** 3)
    sigma_s_nm = r_sph_min_nm / math.sqrt(2.0)

    # Diffraction 1-sigma blur (de Broglie 31P+)
    lam_nm = de_broglie_nm(E_land_eV)
    sigma_d_nm = 0.42 * lam_nm / alpha

    # Blanker edge transit time at 10 keV (L=0.80 mm): 3.205 ns vs 2.1 ns edge -> P_edge ~ t_tr / tau_shot (OBS-150)
    v_10keV = math.sqrt(2.0 * E_CHARGE * 10000.0 / M_P31)
    t_blanker_transit_ns = (0.80e-3 / v_10keV) * 1e9
    p_blanker_edge_hit = (t_blanker_transit_ns * 1e-9) / (tau_shot_ms * 1e-3)

    # Total spot 1-sigma (RSS) including HV PSU ripple/stability
    sigma_spot_nm = math.sqrt(
        sigma_geom_nm ** 2 + sigma_c_nm ** 2 + sigma_psu_nm ** 2
        + sigma_s_nm ** 2 + sigma_d_nm ** 2 + sigma_coul_nm ** 2
    )
    sigma_equip_nm = math.sqrt(
        sigma_spot_nm ** 2 + sigma_stage_nm ** 2 + sigma_pointing_nm ** 2
        + sigma_thermal_nm ** 2 + sigma_anneal_nm ** 2
    )
    sigma_straggle_nm = bca_straggle_nm(E_land_keV)
    sigma_total_nm = math.hypot(sigma_equip_nm, sigma_straggle_nm)
    ibic_info = ibic_efficiency(E_land_keV, C_ibic_pF, threshold_sigma=ibic_thr_sigma, dead_layer_nm=dead_layer_nm)
    eta_ibic = ibic_info["eta"]

    return dict(
        E_land_keV=E_land_keV, alpha_land_mrad=alpha_land_mrad,
        Cc_mm=Cc_mm, Cs_mm=Cs_mm, dE_fwhm_eV=dE_fwhm_eV,
        J_src_A_m2=J_src_A_m2, Ti_eV=Ti_eV, tau_filter=tau_filter, tau_shot_ms=tau_shot_ms,
        B_r_net_A_m2_sr_V=B_r_net, B_land_A_m2_sr=B_land,
        r_geom_tophat_nm=r_geom_tophat_nm, sigma_geom_nm=sigma_geom_nm,
        sigma_c_edge_nm=sigma_c_edge_nm, sigma_c_nm=sigma_c_nm,
        psu_stability_ppm=psu_stability_ppm, dv_psu_rms_V=dv_eff_V, sigma_psu_nm=sigma_psu_nm,
        sigma_s_nm=sigma_s_nm, r_sph_min_nm=r_sph_min_nm, sigma_d_nm=sigma_d_nm,
        sigma_coul_nm=sigma_coul_nm,
        t_blanker_transit_ns=t_blanker_transit_ns, p_blanker_edge_hit=p_blanker_edge_hit,
        sigma_spot_nm=sigma_spot_nm, sigma_equip_nm=sigma_equip_nm,
        sigma_straggle_nm=sigma_straggle_nm, sigma_total_nm=sigma_total_nm,
        eta_ibic=eta_ibic, ibic_dead_layer_nm=dead_layer_nm, ibic_cce=ibic_info["cce"],
    )


def optimize_alpha_land(
    E_land_keV: float, Cc_mm: float, Cs_mm: float, **kwargs
) -> dict[str, float]:
    """Find optimal landing semi-angle alpha_land_mrad in [3, 40] mrad minimizing sigma_spot."""
    alphas = np.linspace(3.0, 40.0, 741)
    best = None
    for a in alphas:
        res = evaluate_spot_budget(E_land_keV, Cc_mm, Cs_mm, float(a), **kwargs)
        if best is None or res["sigma_spot_nm"] < best["sigma_spot_nm"]:
            best = res
    return best


def build_cad_column_dimensions(
    arch_b_trace: dict[str, Any],
    arch_c_trace: dict[str, Any],
    wien: dict[str, float],
    hda: dict[str, float],
    wafer_top_z_cad_mm: float = 500.0,
    uhv_chamber_inner_r_mm: float = 182.0,
) -> dict[str, Any]:
    """Produce definitive CAD v3.0 mechanical dimensions (mm) for the 10 -> 5 keV column.

    Single unified coordinate frame (CAD v3.0):
      - Wafer active top surface at Z_WAFER = 500.00 mm (local z_rel = 0.00 mm).
      - Compact s=0.5 UHV chamber inner radius R_in = 182.0 mm (6.0 mm clearance to Ø352 magnet).
      - Active Arch-B Option-A array: 32x32 = 1,024 beamlets, co-pitched at 0.50 mm across
        S2.1 aperture + S2.2 blanker + S2.3 Arch-B mini-lens -> 16.0 x 16.0 mm active square
        (diagonal 22.627 mm) with Ø28.0 mm bore in S1.6/S2.1 (2.686 mm radial margin, zero clipping).
    """
    wd_b = round(arch_b_trace["working_distance_mm"], 3)
    array_n_side = 32
    active_beamlets = array_n_side * array_n_side  # 1,024
    pitch_mm = 0.50
    array_side_mm = array_n_side * pitch_mm        # 16.0 mm
    array_diag_mm = array_side_mm * math.sqrt(2.0) # 22.6274 mm
    limiting_bore_mm = 28.0
    diag_radial_clearance_mm = 0.5 * (limiting_bore_mm - array_diag_mm)  # 2.6863 mm

    stages = [
        # Ordered bottom-up from wafer top (Z_WAFER = 500.00 mm, z_rel = 0.00 mm)
        dict(id="S2.3_retarding_minilens", label="Field-Free Retarding Immersion Mini-Lens (Arch-B, 10->1.3->5 keV)",
             height_mm=1.76, gap_below_mm=wd_b, od_mm=60.0, bore_mm=0.30,
             array_active_mm="16.0x16.0 (32x32=1024 co-pitched @0.50 mm; diag 22.63 mm)",
             voltage_V="-5000 -> +3700 -> 0 V (E<=10.60 MV/m)",
             material="Doped Si / Mo + Al2O3 HV spacers", mass_est_kg=0.20),
        dict(id="S2.2_blanker_and_stop", label="SKY130/MEMS Co-Pitched Blanker + Beam-Stop Stack (0.50 mm pitch)",
             height_mm=4.0, gap_below_mm=1.0, od_mm=60.0, bore_mm=0.008,
             array_active_mm="16.0x16.0 (32x32=1024 @0.50 mm; 16x 64-ch SKY130 tiles)",
             voltage_V="-5000 +/- 53.3 V",
             material="SKY130 CMOS + 30 um doped Si shield", mass_est_kg=0.12),
        dict(id="S2.1_aperture_and_frame", label="MEMS Co-Pitched Aperture Plate + Kinematic Head Mount (Ø28 mm clear bore)",
             height_mm=24.0, gap_below_mm=0.65, od_mm=100.0, bore_mm=limiting_bore_mm,
             array_active_mm="16.0x16.0 (32x32=1024 @0.50 mm; 2.69 mm radial margin to Ø28 bore)",
             voltage_V="-5000 V (floated liner)",
             material="Invar-36 / Ti-6Al-4V + Si aperture", mass_est_kg=1.40),
        dict(id="S1.6_transfer_lens", label="Telecentric Flood Transfer Lens (Einzel, Ø28 mm clear bore)",
             height_mm=65.0, gap_below_mm=8.0, od_mm=84.0, bore_mm=limiting_bore_mm,
             array_active_mm="Uniform <0.5 mrad flood across 16x16 mm (2.69 mm radial margin)",
             voltage_V="-5000 V liner / focus elem",
             material="316L SS / OFHC Cu / Macor", mass_est_kg=2.60),
        dict(id="S1.5_energy_filter_HDA", label=f"Hemispherical Energy Filter (dE={hda['dE_fwhm_eV']:.2f} eV, E_pass={hda['E_pass_eV']:.0f} eV)",
             height_mm=95.0, gap_below_mm=10.0, od_mm=110.0, bore_mm=16.0,
             array_active_mm=f"R0={hda['R0_mm']:.0f} mm, slit={hda['slit_mm']:.2f} mm",
             voltage_V=f"-5000 V liner (retarded to {hda['E_pass_eV']:.0f} eV inside)",
             material="Mu-metal shielded Al/Mo hemispheres", mass_est_kg=5.20),
        dict(id="S1.2_wien_mass_filter", label="Wien Mass Filter + Drift & 200 um Mass Slit (31P+)",
             height_mm=wien["L_w_mm"] + wien["L_drift_mm"], gap_below_mm=8.0, od_mm=110.0, bore_mm=12.0,
             array_active_mm=f"B={wien['B_T']:.2f} T, V_p={wien['V_plates_V']:.0f} V, dx(32PH+)={wien['dx_32PH_mm']:.2f} mm",
             voltage_V="-5000 V liner +/- 674 V plates",
             material="SmCo Halbach / FeCo yoke + Mo plates", mass_est_kg=6.80),
        dict(id="S1.4_condenser_lens", label="Extractor & Condenser Einzel Lens",
             height_mm=45.0, gap_below_mm=6.0, od_mm=84.0, bore_mm=20.0,
             array_active_mm="Matches duoplasmatron to Wien entrance", voltage_V="+5000 V -> -5000 V (10 keV)",
             material="316L SS + Al2O3 HV feedthroughs", mass_est_kg=2.10),
        dict(id="S1.1_duoplasmatron", label="Duoplasmatron Ion Source (PH3 feed + expansion cup)",
             height_mm=140.0, gap_below_mm=4.0, od_mm=90.0, bore_mm=0.10,
             array_active_mm="Anode 100 um, J=10 mA/cm2, dE_cup~6 eV", voltage_V="+5000 V anode (5 kV to gnd)",
             material="Water-cooled Fe/Cu/Mo + HV ceramic break", mass_est_kg=7.50),
    ]

    z_cur = wafer_top_z_cad_mm
    assembled = []
    for st in stages:
        z_bot = z_cur + st["gap_below_mm"]
        z_top = z_bot + st["height_mm"]
        z_mid = 0.5 * (z_bot + z_top)
        rec = dict(st)
        rec["z_bottom_mm"] = round(z_bot, 3)
        rec["z_top_mm"] = round(z_top, 3)
        rec["z_center_mm"] = round(z_mid, 3)
        rec["z_rel_bottom_mm"] = round(z_bot - wafer_top_z_cad_mm, 3)
        rec["z_rel_top_mm"] = round(z_top - wafer_top_z_cad_mm, 3)
        assembled.append(rec)
        z_cur = z_top

    total_height = round(z_cur - wafer_top_z_cad_mm, 3)
    max_od = max(s["od_mm"] for s in assembled)
    total_mass = round(sum(s["mass_est_kg"] for s in assembled), 2)
    write_shots_15ms = 0.5 * active_beamlets * 86400.0 / 0.015
    write_shots_10ms = 0.5 * active_beamlets * 86400.0 / 0.010

    return {
        "coordinate_frame": "CAD v3.0 unified global Z (Z_WAFER = 500.00 mm; z_rel = z_CAD - 500.00 mm)",
        "wafer_top_z_cad_mm": wafer_top_z_cad_mm,
        "column_top_z_cad_mm": round(z_cur, 3),
        "total_column_height_mm": total_height,
        "max_outer_diameter_mm": max_od,
        "total_column_mass_est_kg": total_mass,
        "uhv_chamber_inner_r_mm": uhv_chamber_inner_r_mm,
        "chamber_flange_interface_z_mm": 620.0,
        "fits_golden_uhv_chamber": bool(max_od / 2.0 < uhv_chamber_inner_r_mm - 40.0),
        "active_array_option": "Option-A co-pitched Arch-B (32x32=1,024 @ 0.50 mm across S2.1/S2.2/S2.3)",
        "active_beamlet_count": active_beamlets,
        "active_pitch_mm": pitch_mm,
        "active_tiles_64ch": active_beamlets // 64,
        "active_array_side_mm": array_side_mm,
        "active_array_diagonal_mm": round(array_diag_mm, 4),
        "limiting_column_bore_mm": limiting_bore_mm,
        "beam_array_diagonal_to_bore_clearance_mm": round(diag_radial_clearance_mm, 4),
        "write_rate_shots_per_day_1024_15ms": write_shots_15ms,
        "write_rate_shots_per_day_1024_10ms": write_shots_10ms,
        "hv_grounding_scheme": "Wafer/Cryo/IBIC at 0 V ground; column liner floated at -5.0 kV (10 keV beam); duoplasmatron anode at +5.0 kV (or liner -10 kV for 15 keV variant).",
        "arch_c_historical_alternative_note": {
            "status": "Historical Exp78/79 / Arch-C alternative only (NOT active baseline; Cs=51.58 mm degrades spot to 1.93 nm)",
            "working_distance_mm": round(arch_c_trace["working_distance_mm"], 3),
            "pre_retard_gap_mm": 0.750,
            "pitch_mm": 0.032,
            "array_10k_size_mm": "3.2x3.2",
        },
        "stages": assembled,
    }
