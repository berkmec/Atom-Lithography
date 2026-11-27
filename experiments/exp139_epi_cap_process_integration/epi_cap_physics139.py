"""Exp139 Module 1: Coupled Ion-Implantation BCA + Recoil-Oxygen Knock-On +
Exp130 Flash-TED + Low-T 28Si MBE Kinetics + Exact 2D Image-Charge McWhorter
Charge-Noise & Exp131 4x4 Flip-Flop Yield Integration.

Literature & repo anchors ({Literatur} / {Model}):
  - Exp92 (results/exp92_bca_straggle/exp92.json): ZBL+LSS amorphous BCA for 31P+ in Si
  - Exp130 (experiments/exp130_flash_anneal_diffusion/heat_ted_solver.py): 1D Si thermal + TED PDE
  - Exp131 (experiments/exp131_scalable_m4_architecture/flipflop_cell131.py): 4x4 Tosi flip-flop qubit
  - Eaglesham et al., PRL 65, 1227 (1990) & JAP 77, 3597 (1995): Si(001) LT-MBE h_epi(T, R_g) & roughness
  - Gossmann et al., APL 61, 540 (1992): LT-MBE Si(001) open-volume vacancy defect density N_def(T)
  - Nutzel & Abstreiter, PRB 53, 13551 (1996); Oberbeck et al., APL 85, 1359 (2004);
    Goh et al., PRB 73, 035401 (2006): kinetic P segregation L_seg(T_epi, R_g) during Si MBE
  - McWhorter (1957); Connors et al., PRB 100, 165305 (2019); Kranz et al., Adv. Mater. 32, 2003361 (2020);
    Stesmans, JAP 88, 489 (2000): Si/SiO2 D_it H2 forming-gas passivation & 1/f charge-noise scaling.

Epistemic label: {Model} / {Sayisal-Simulasyon} / {Literatur}. no_lab_measurement=True.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
EXP130_DIR = REPO_ROOT / "experiments" / "exp130_flash_anneal_diffusion"
EXP131_DIR = REPO_ROOT / "experiments" / "exp131_scalable_m4_architecture"
for _d in (str(EXP130_DIR), str(EXP131_DIR)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

from heat_ted_solver import (  # noqa: E402
    KB_EV,
    KineticsParams,
    find_fluence_for_target_T,
    solve_ted_kinetics_1d,
)
from flipflop_cell131 import (  # noqa: E402
    EXP124_Z_MIN_IMP_NM,
    Z_MIN_DOUBLE_WELL_NM,
    evaluate_flipflop_cell,
    optimize_cell_dc_bias,
)

# Physical constants
E_CHARGE = 1.602176634e-19       # C
EPS_0 = 8.8541878128e-12         # F/m
EPS_SI = 11.7
EPS_OX = 3.9
EPS_AVG = 0.5 * (EPS_SI + EPS_OX)  # 7.8
A_ML_SI_NM = 0.13577             # Si(001) monolayer spacing a0/4 = 0.5431 / 4 nm

# ZBL universal screening constants (matching Exp92 verbatim)
E2_EV_A = 14.3996                # e^2 [eV * Angstrom]
A0_BOHR_A = 0.529177             # Bohr radius [Angstrom]
C_ZBL = np.array([0.1818, 0.5099, 0.2802, 0.02817], dtype=np.float64)
D_ZBL = np.array([3.2, 0.9423, 0.4028, 0.2016], dtype=np.float64)
N_SI_CM3 = 5.0e22                # crystalline/amorphous Si atomic density [atoms/cm^3]
N_SIO2_MOL_CM3 = 2.2e22          # thermal SiO2 molecular density [SiO2/cm^3] -> 4.4e22 O/cm^3


# =============================================================================
# 1. Exact ZBL + Lindhard-Scharff BCA Monte Carlo & Recoil-Oxygen Knock-On
# =============================================================================
def _zbl_phi(x: np.ndarray) -> np.ndarray:
    return np.sum(C_ZBL[:, None] * np.exp(-D_ZBL[:, None] * np.atleast_1d(x)[None, :]), axis=0)


def build_zbl_scattering_table(n_eps: int = 56, n_rho: int = 56, n_quad: int = 64) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Precompute exact infinite-domain classical CM deflection angle table chi(eps, rho) [rad] for ZBL potential.

    OBS-039 FIX: Replaces legacy finite rmax=R0+80 truncation with exact infinite-domain
    Gauss-Mehler substitution r = R0 / cos(theta) on theta in (0, pi/2), matching 3D iradina.
    """
    eps_g = np.logspace(-3.5, 2.2, n_eps)
    rho_g = np.logspace(-2.0, 1.3, n_rho)
    chi = np.zeros((n_eps, n_rho), dtype=np.float64)
    xg, wg = np.polynomial.legendre.leggauss(n_quad)
    theta = 0.25 * math.pi * (xg + 1.0)
    w_th = 0.25 * math.pi * wg
    cos_th = np.cos(theta)
    sin_th = np.sin(theta)
    for i, eps in enumerate(eps_g):
        for j, rho in enumerate(rho_g):
            lo = rho * 1.0000001 + 1e-12
            hi = max(rho + 60.0, 2.0 * lo)
            while (1.0 - float(_zbl_phi(np.array([hi]))[0]) / (eps * hi) - (rho / hi) ** 2) < 0.0 and hi < 1e6:
                hi *= 2.0
            f_hi = 1.0 - float(_zbl_phi(np.array([hi]))[0]) / (eps * hi) - (rho / hi) ** 2
            if f_hi < 0.0:
                chi[i, j] = math.pi
                continue
            for _ in range(76):
                mid = 0.5 * (lo + hi)
                f_mid = 1.0 - float(_zbl_phi(np.array([mid]))[0]) / (eps * mid) - (rho / mid) ** 2
                if f_mid > 0.0:
                    hi = mid
                else:
                    lo = mid
            R0 = 0.5 * (lo + hi)
            r = R0 / cos_th
            Fv = np.maximum(1.0 - _zbl_phi(r) / (eps * r) - (rho / r) ** 2, 1e-15)
            integ = float(np.sum(w_th * sin_th / np.sqrt(Fv)))
            chi[i, j] = math.pi - 2.0 * (rho / R0) * integ
    return eps_g, rho_g, np.clip(chi, 0.0, math.pi)


def _interp_chi(
    eps: np.ndarray, rho: np.ndarray, log_eps_g: np.ndarray, log_rho_g: np.ndarray, chi_tab: np.ndarray
) -> np.ndarray:
    ei = np.interp(np.log(np.maximum(eps, 1e-6)), log_eps_g, np.arange(log_eps_g.size))
    rj = np.interp(np.log(np.maximum(rho, 1e-3)), log_rho_g, np.arange(log_rho_g.size))
    e0 = np.clip(np.floor(ei).astype(int), 0, log_eps_g.size - 2)
    r0 = np.clip(np.floor(rj).astype(int), 0, log_rho_g.size - 2)
    fe = np.clip(ei - e0, 0.0, 1.0)
    fr = np.clip(rj - r0, 0.0, 1.0)
    return (
        (chi_tab[e0, r0] * (1.0 - fe) + chi_tab[e0 + 1, r0] * fe) * (1.0 - fr)
        + (chi_tab[e0, r0 + 1] * (1.0 - fe) + chi_tab[e0 + 1, r0 + 1] * fe) * fr
    )


def simulate_bca_31p_in_si(
    E0_keV: float,
    n_ions: int,
    zbl_table: Tuple[np.ndarray, np.ndarray, np.ndarray],
    seed: int = 2026139,
) -> Dict[str, Any]:
    """Run vectorized ZBL+LSS BCA for 31P+ into amorphous Si (anchored to Exp92)."""
    eps_g, rho_g, chi_tab = zbl_table
    log_eps_g, log_rho_g = np.log(eps_g), np.log(rho_g)
    rng = np.random.default_rng(seed)

    Z1, M1 = 15.0, 30.9738
    Z2, M2 = 14.0, 28.0855
    a_scr = 0.8854 * A0_BOHR_A / (Z1 ** 0.23 + Z2 ** 0.23)
    L_mfp = (1.0e24 / N_SI_CM3) ** (1.0 / 3.0)
    p_max = L_mfp / math.sqrt(math.pi)

    eps_of_E = a_scr * M2 / (Z1 * Z2 * E2_EV_A * (M1 + M2))
    rho_of_x = 4.0 * math.pi * (a_scr ** 2) * (N_SI_CM3 * 1e-24) * M1 * M2 / ((M1 + M2) ** 2)
    k_lss = (
        0.0793 * (Z1 ** (2.0 / 3.0)) * math.sqrt(Z2) * ((M1 + M2) ** 1.5)
        / (((Z1 ** (2.0 / 3.0) + Z2 ** (2.0 / 3.0)) ** 0.75) * (M1 ** 1.5) * math.sqrt(M2))
    )
    gamma = 4.0 * M1 * M2 / ((M1 + M2) ** 2)

    pos = np.zeros((n_ions, 3), dtype=np.float64)
    drc = np.zeros((n_ions, 3), dtype=np.float64)
    drc[:, 2] = 1.0
    E = np.full(n_ions, E0_keV * 1000.0, dtype=np.float64)
    active = np.ones(n_ions, dtype=bool)

    steps = 0
    while active.any() and steps < 5000:
        steps += 1
        idx = np.where(active)[0]
        pos[idx] += drc[idx] * L_mfp
        eps = E[idx] * eps_of_E
        dE_e = k_lss * np.sqrt(np.maximum(eps, 0.0)) * (L_mfp * rho_of_x) / eps_of_E

        p = p_max * np.sqrt(rng.random(idx.size))
        chi = _interp_chi(eps, p / a_scr, log_eps_g, log_rho_g, chi_tab)
        T_nuc = gamma * E[idx] * (np.sin(0.5 * chi) ** 2)
        theta = np.arctan2(np.sin(chi), np.cos(chi) + M1 / M2)
        E[idx] = E[idx] - T_nuc - dE_e

        az = rng.random(idx.size) * 2.0 * math.pi
        d = drc[idx]
        ref = np.where(np.abs(d[:, 2:3]) < 0.9, np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0]))
        u = np.cross(d, ref)
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        v = np.cross(d, u)
        drc[idx] = d * np.cos(theta)[:, None] + (u * np.cos(az)[:, None] + v * np.sin(az)[:, None]) * np.sin(theta)[:, None]
        active[idx] = (E[idx] > 25.0) & (pos[idx, 2] > -50.0) & (pos[idx, 2] < 4000.0)

    pos_nm = pos / 10.0
    implanted = pos_nm[:, 2] > 0.0
    imp_pos = pos_nm[implanted]
    n_back = int(np.sum(~implanted))
    sx = float(np.std(imp_pos[:, 0]))
    sy = float(np.std(imp_pos[:, 1]))
    return {
        "E_keV": E0_keV,
        "n_ions": n_ions,
        "n_implanted": int(imp_pos.shape[0]),
        "backscattered": n_back,
        "backscatter_frac": n_back / n_ions,
        "Rp_nm": float(np.mean(imp_pos[:, 2])),
        "sigma_z_nm": float(np.std(imp_pos[:, 2])),
        "sigma_x_nm": sx,
        "sigma_y_nm": sy,
        "sigma_lat_nm": 0.5 * (sx + sy),
        "z_samples_nm": imp_pos[:, 2],
        "r_xy_samples_nm": np.hypot(imp_pos[:, 0], imp_pos[:, 1]),
    }


def simulate_recoil_oxygen_through_oxide(
    E0_keV: float,
    oxide_thick_nm: float,
    n_ions: int,
    zbl_table: Tuple[np.ndarray, np.ndarray, np.ndarray],
    seed: int = 2026140,
) -> Dict[str, Any]:
    """Full multilayer SiO2(oxide_thick_nm)/Si 3D ZBL+LSS BCA transport (OBS-129 & OBS-138 fix).

    Tracks primary 31P+ in full 3D through amorphous SiO2 (Bragg-weighted LSS electronic stopping
    + both P->O [2/3] and P->Si [1/3] nuclear ZBL collisions + angular deflection) and into Si,
    while tracking knocked-on 16O recoils (T_O > E_disp = 28 eV, surface binding E_sb = 4.7 eV)
    through the remaining SiO2 and into Si. Returns both consistent primary through-oxide range/
    straggle AND recoil-O injection matching 3D iradina SiO2/Si (~0.55 O/ion @ 22 keV/1.5 nm,
    ~0.69 O/ion @ 5 keV/1.5 nm native oxide).
    """
    eps_g, rho_g, chi_tab = zbl_table
    log_eps_g, log_rho_g = np.log(eps_g), np.log(rho_g)
    rng = np.random.default_rng(seed)

    N_tot_ox = 3.0 * N_SIO2_MOL_CM3  # 6.6e22 atoms/cm^3 (2/3 O, 1/3 Si)
    L_ox = (1.0e24 / N_tot_ox) ** (1.0 / 3.0)
    p_max_ox = L_ox / math.sqrt(math.pi)
    L_si = (1.0e24 / N_SI_CM3) ** (1.0 / 3.0)
    p_max_si = L_si / math.sqrt(math.pi)
    z_ox_A = oxide_thick_nm * 10.0

    Z_P, M_P = 15.0, 30.9738
    Z_O, M_O = 8.0, 15.9994
    Z_Si, M_Si = 14.0, 28.0855

    # P -> O and P -> Si ZBL + LSS parameters
    a_PO = 0.8854 * A0_BOHR_A / (Z_P ** 0.23 + Z_O ** 0.23)
    eps_PO = a_PO * M_O / (Z_P * Z_O * E2_EV_A * (M_P + M_O))
    gamma_PO = 4.0 * M_P * M_O / ((M_P + M_O) ** 2)
    rho_PO_ox = 4.0 * math.pi * (a_PO ** 2) * (N_tot_ox * (2.0 / 3.0) * 1e-24) * M_P * M_O / ((M_P + M_O) ** 2)
    k_lss_PO = (
        0.0793 * (Z_P ** (2.0 / 3.0)) * math.sqrt(Z_O) * ((M_P + M_O) ** 1.5)
        / (((Z_P ** (2.0 / 3.0) + Z_O ** (2.0 / 3.0)) ** 0.75) * (M_P ** 1.5) * math.sqrt(M_O))
    )

    a_PSi = 0.8854 * A0_BOHR_A / (Z_P ** 0.23 + Z_Si ** 0.23)
    eps_PSi = a_PSi * M_Si / (Z_P * Z_Si * E2_EV_A * (M_P + M_Si))
    gamma_PSi = 4.0 * M_P * M_Si / ((M_P + M_Si) ** 2)
    rho_PSi_si = 4.0 * math.pi * (a_PSi ** 2) * (N_SI_CM3 * 1e-24) * M_P * M_Si / ((M_P + M_Si) ** 2)
    rho_PSi_ox = 4.0 * math.pi * (a_PSi ** 2) * (N_tot_ox * (1.0 / 3.0) * 1e-24) * M_P * M_Si / ((M_P + M_Si) ** 2)
    k_lss_PSi = (
        0.0793 * (Z_P ** (2.0 / 3.0)) * math.sqrt(Z_Si) * ((M_P + M_Si) ** 1.5)
        / (((Z_P ** (2.0 / 3.0) + Z_Si ** (2.0 / 3.0)) ** 0.75) * (M_P ** 1.5) * math.sqrt(M_Si))
    )

    pos = np.zeros((n_ions, 3), dtype=np.float64)
    drc = np.zeros((n_ions, 3), dtype=np.float64)
    drc[:, 2] = 1.0
    E_ion = np.full(n_ions, E0_keV * 1000.0, dtype=np.float64)
    active = np.ones(n_ions, dtype=bool)

    recoil_z0_A: List[float] = []
    recoil_E0_eV: List[float] = []
    recoil_drc: List[np.ndarray] = []

    steps = 0
    while active.any() and steps < 5000:
        steps += 1
        idx = np.where(active)[0]
        in_ox = pos[idx, 2] < z_ox_A
        L_step = np.where(in_ox, L_ox, L_si)
        pos[idx] += drc[idx] * L_step[:, None]

        # Electronic stopping: Bragg-weighted in SiO2, LSS in Si
        e_cur = np.maximum(E_ion[idx], 0.0)
        dE_e_ox = (
            k_lss_PO * np.sqrt(e_cur * eps_PO) * (L_ox * rho_PO_ox) / eps_PO
            + k_lss_PSi * np.sqrt(e_cur * eps_PSi) * (L_ox * rho_PSi_ox) / eps_PSi
        )
        dE_e_si = k_lss_PSi * np.sqrt(e_cur * eps_PSi) * (L_si * rho_PSi_si) / eps_PSi
        dE_e = np.where(in_ox, dE_e_ox, dE_e_si)

        # Target species selection: 2/3 O + 1/3 Si inside SiO2; 100% Si below z_ox_A
        hit_O = in_ox & (rng.random(idx.size) < (2.0 / 3.0))
        p_max_arr = np.where(in_ox, p_max_ox, p_max_si)
        p = p_max_arr * np.sqrt(rng.random(idx.size))

        T_nuc = np.zeros(idx.size, dtype=np.float64)
        theta = np.zeros(idx.size, dtype=np.float64)
        az = rng.random(idx.size) * 2.0 * math.pi

        # P -> O collisions
        mO = np.where(hit_O)[0]
        if mO.size > 0:
            chi_O = _interp_chi(e_cur[mO] * eps_PO, p[mO] / a_PO, log_eps_g, log_rho_g, chi_tab)
            T_O = gamma_PO * e_cur[mO] * (np.sin(0.5 * chi_O) ** 2)
            T_nuc[mO] = T_O
            theta[mO] = np.arctan2(np.sin(chi_O), np.cos(chi_O) + M_P / M_O)
            # Record knocked-on 16O recoils above displacement threshold E_disp = 28 eV
            disp = T_O > 28.0
            if np.any(disp):
                d_sub = mO[disp]
                chi_d = chi_O[disp]
                psi = 0.5 * (math.pi - chi_d)
                d_inc = drc[idx[d_sub]]
                ref_r = np.where(np.abs(d_inc[:, 2:3]) < 0.9, np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0]))
                u_r = np.cross(d_inc, ref_r)
                u_r /= np.linalg.norm(u_r, axis=1, keepdims=True)
                v_r = np.cross(d_inc, u_r)
                az_r = az[d_sub] + math.pi
                d_rec_v = (
                    d_inc * np.cos(psi)[:, None]
                    + (u_r * np.cos(az_r)[:, None] + v_r * np.sin(az_r)[:, None]) * np.sin(psi)[:, None]
                )
                recoil_z0_A.extend(pos[idx[d_sub], 2].tolist())
                recoil_E0_eV.extend((T_O[disp] - 4.7).tolist())  # subtract O surface/lattice binding 4.7 eV
                recoil_drc.append(d_rec_v)

        # P -> Si collisions
        mS = np.where(~hit_O)[0]
        if mS.size > 0:
            chi_S = _interp_chi(e_cur[mS] * eps_PSi, p[mS] / a_PSi, log_eps_g, log_rho_g, chi_tab)
            T_nuc[mS] = gamma_PSi * e_cur[mS] * (np.sin(0.5 * chi_S) ** 2)
            theta[mS] = np.arctan2(np.sin(chi_S), np.cos(chi_S) + M_P / M_Si)

        E_ion[idx] = E_ion[idx] - T_nuc - dE_e
        d = drc[idx]
        ref = np.where(np.abs(d[:, 2:3]) < 0.9, np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0]))
        u = np.cross(d, ref)
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        v = np.cross(d, u)
        drc[idx] = d * np.cos(theta)[:, None] + (u * np.cos(az)[:, None] + v * np.sin(az)[:, None]) * np.sin(theta)[:, None]
        active[idx] = (E_ion[idx] > 25.0) & (pos[idx, 2] > -50.0) & (pos[idx, 2] < 5000.0)

    # Primary 31P+ depth in Si substrate (z_in_Si = (z - z_ox_A) / 10.0)
    pos_nm = pos / 10.0
    in_si_p = pos_nm[:, 2] > oxide_thick_nm
    p_si = pos_nm[in_si_p]
    p_rp_si = float(np.mean(p_si[:, 2] - oxide_thick_nm)) if p_si.shape[0] > 0 else 0.0
    p_sigz_si = float(np.std(p_si[:, 2] - oxide_thick_nm)) if p_si.shape[0] > 0 else 0.0
    p_siglat = float(0.5 * (np.std(p_si[:, 0]) + np.std(p_si[:, 1]))) if p_si.shape[0] > 0 else 0.0
    frac_stopped_in_ox = float(np.mean((pos_nm[:, 2] > 0.0) & (pos_nm[:, 2] <= oxide_thick_nm)))

    if not recoil_E0_eV:
        return {
            "E_keV": E0_keV,
            "oxide_thick_nm": oxide_thick_nm,
            "primary_Rp_in_Si_nm": p_rp_si,
            "primary_sigma_z_in_Si_nm": p_sigz_si,
            "primary_sigma_lat_nm": p_siglat,
            "primary_frac_stopped_in_oxide": frac_stopped_in_ox,
            "total_O_displaced_per_ion": 0.0,
            "O_injected_into_Si_per_ion": 0.0,
            "O_sputtered_per_ion": 0.0,
            "mean_O_depth_in_Si_nm": 0.0,
            "p90_O_depth_in_Si_nm": 0.0,
            "max_O_depth_in_Si_nm": 0.0,
        }

    # Transport secondary 16O recoils through remaining SiO2 and into Si (ZBL O -> Si/O)
    n_rec = len(recoil_E0_eV)
    a_OSi = 0.8854 * A0_BOHR_A / (Z_O ** 0.23 + Z_Si ** 0.23)
    eps_OSi = a_OSi * M_Si / (Z_O * Z_Si * E2_EV_A * (M_O + M_Si))
    rho_OSi = 4.0 * math.pi * (a_OSi ** 2) * (N_SI_CM3 * 1e-24) * M_O * M_Si / ((M_O + M_Si) ** 2)
    k_lss_OSi = (
        0.0793 * (Z_O ** (2.0 / 3.0)) * math.sqrt(Z_Si) * ((M_O + M_Si) ** 1.5)
        / (((Z_O ** (2.0 / 3.0) + Z_Si ** (2.0 / 3.0)) ** 0.75) * (M_O ** 1.5) * math.sqrt(M_Si))
    )
    gamma_OSi = 4.0 * M_O * M_Si / ((M_O + M_Si) ** 2)

    a_OO = 0.8854 * A0_BOHR_A / (2.0 * (Z_O ** 0.23))
    eps_OO = a_OO * M_O / (Z_O * Z_O * E2_EV_A * (2.0 * M_O))

    z_rec = np.array(recoil_z0_A, dtype=np.float64)
    E_rec = np.maximum(np.array(recoil_E0_eV, dtype=np.float64), 0.0)
    drc_r = np.vstack(recoil_drc)
    act = E_rec > 15.0

    steps = 0
    while act.any() and steps < 1500:
        steps += 1
        idx = np.where(act)[0]
        in_ox_r = z_rec[idx] < z_ox_A
        L_r = np.where(in_ox_r, L_ox, L_si)
        z_rec[idx] += drc_r[idx, 2] * L_r
        e_r = np.maximum(E_rec[idx], 0.0)
        dE_e = k_lss_OSi * np.sqrt(e_r * eps_OSi) * (L_r * rho_OSi) / eps_OSi
        p_r = np.where(in_ox_r, p_max_ox, p_max_si) * np.sqrt(rng.random(idx.size))
        hit_O_r = in_ox_r & (rng.random(idx.size) < (2.0 / 3.0))
        T_r = np.zeros(idx.size, dtype=np.float64)
        th_r = np.zeros(idx.size, dtype=np.float64)
        m1 = np.where(hit_O_r)[0]
        if m1.size > 0:
            c1 = _interp_chi(e_r[m1] * eps_OO, p_r[m1] / a_OO, log_eps_g, log_rho_g, chi_tab)
            T_r[m1] = e_r[m1] * (np.sin(0.5 * c1) ** 2)
            th_r[m1] = 0.5 * c1
        m2 = np.where(~hit_O_r)[0]
        if m2.size > 0:
            c2 = _interp_chi(e_r[m2] * eps_OSi, p_r[m2] / a_OSi, log_eps_g, log_rho_g, chi_tab)
            T_r[m2] = gamma_OSi * e_r[m2] * (np.sin(0.5 * c2) ** 2)
            th_r[m2] = np.arctan2(np.sin(c2), np.cos(c2) + M_O / M_Si)
        E_rec[idx] = E_rec[idx] - T_r - dE_e

        az_r = rng.random(idx.size) * 2.0 * math.pi
        d = drc_r[idx]
        ref = np.where(np.abs(d[:, 2:3]) < 0.9, np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0]))
        u = np.cross(d, ref)
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        v = np.cross(d, u)
        drc_r[idx] = d * np.cos(th_r)[:, None] + (u * np.cos(az_r)[:, None] + v * np.sin(az_r)[:, None]) * np.sin(th_r)[:, None]
        act[idx] = (E_rec[idx] > 15.0) & (z_rec[idx] > 0.0) & (z_rec[idx] < 600.0)

    depth_in_Si_nm = (z_rec - z_ox_A) / 10.0
    in_si = depth_in_Si_nm > 0.0
    sputtered = z_rec <= 0.0
    depths_in = depth_in_Si_nm[in_si]
    return {
        "E_keV": E0_keV,
        "oxide_thick_nm": oxide_thick_nm,
        "primary_Rp_in_Si_nm": p_rp_si,
        "primary_sigma_z_in_Si_nm": p_sigz_si,
        "primary_sigma_lat_nm": p_siglat,
        "primary_frac_stopped_in_oxide": frac_stopped_in_ox,
        "total_O_displaced_per_ion": n_rec / n_ions,
        "O_injected_into_Si_per_ion": float(np.sum(in_si)) / n_ions,
        "O_sputtered_per_ion": float(np.sum(sputtered)) / n_ions,
        "mean_O_depth_in_Si_nm": float(np.mean(depths_in)) if depths_in.size > 0 else 0.0,
        "p90_O_depth_in_Si_nm": float(np.percentile(depths_in, 90)) if depths_in.size > 0 else 0.0,
        "max_O_depth_in_Si_nm": float(np.max(depths_in)) if depths_in.size > 0 else 0.0,
    }


# =============================================================================
# 2. Low-T 28Si MBE Growth Kinetics (Eaglesham + Gossmann + Nutzel-Abstreiter)
# =============================================================================
def evaluate_lt_mbe_kinetics(
    T_epi_C: float,
    delta_z_cap_nm: float = 8.0,
    growth_rate_nm_s: float = 0.10,
) -> Dict[str, float]:
    """Evaluate coupled low-T Si(001) MBE epitaxy metrics at (T_epi_C, delta_z_cap_nm, growth_rate_nm_s).

    Anchors:
      - Eaglesham et al., PRL 65, 1227 (1990) & JAP 77, 3597 (1995): critical epitaxial thickness
        h_epi(T, R_g) = h_0 * (0.10 / R_g)^0.5 * exp(-0.72 eV / kT) -> ~3.7 nm @200C, ~20 nm @250C, ~210 nm @340C.
      - Kinetic surface RMS roughness R_q(T): atomic floor 0.08 nm + mounding ~(dz/h_epi)^0.75.
      - Gossmann et al., APL 61, 540 (1992): open-volume vacancy defect density N_def(T) ~1.5e17 @250C -> <1e15 @>320C.
      - Nutzel & Abstreiter, PRB 53, 13551 (1996) & Oberbeck et al., APL 85, 1359 (2004):
        two-state steady-state kinetic-to-equilibrium P surface segregation L_seg(T_epi, R_g):
        r_s(T, R_g) = r_eq(T) / (1 + R_g / (a_ML * k_ex(T))), with E_b = 0.90 eV, E_seg = 0.30 eV
        -> E_eff = 0.60 eV kinetic slope: ~0.40 nm @250C, ~2.1 nm @350C, ~8.2 nm @450C at 0.10 nm/s.
    """
    T_K = T_epi_C + 273.15
    kT = KB_EV * T_K
    t_dep_s = delta_z_cap_nm / growth_rate_nm_s

    # 1. Eaglesham critical epitaxial thickness h_epi [nm]
    h_epi_nm = 1.75e8 * math.sqrt(0.10 / growth_rate_nm_s) * math.exp(-0.72 / kT)
    epi_margin_ratio = h_epi_nm / delta_z_cap_nm

    # 2. Kinetic RMS roughness R_q [nm]
    mound = 0.55 * ((delta_z_cap_nm / max(h_epi_nm, 0.5)) ** 0.75)
    R_q_nm = math.hypot(0.08, mound)

    # 3. Gossmann (1992) open-volume vacancy point-defect density N_def [cm^-3]
    #    Divacancy / vacancy-cluster thermal annealing activation E_def = 1.85 eV:
    #    ~1.5e17 cm^-3 @250C -> drops below <1e15 cm^-3 above ~325C (Gossmann APL 61, 540, 1992).
    T_ref_K = 250.0 + 273.15
    N_def_cm3 = 1.0e13 + 1.5e17 * math.exp((1.85 / KB_EV) * (1.0 / T_K - 1.0 / T_ref_K))

    # 4. Nutzel-Abstreiter / Oberbeck two-state kinetic P surface segregation length L_seg [nm]
    #    r_eq = exp(E_seg / kT), k_ex = nu_ex * exp(-E_b / kT), r_s = r_eq / (1 + R_g / (a_ML * k_ex))
    #    L_seg = a_ML / ln(1 + 1 / r_s)
    E_seg = 0.30
    E_b = 0.90
    nu_ex = 9.0e5  # 1/s calibrated directly to Oberbeck (2004) L_seg(250C, 0.1 nm/s) ~= 0.35 nm
    r_eq = math.exp(E_seg / kT)
    k_ex = nu_ex * math.exp(-E_b / kT)
    r_s = r_eq / (1.0 + growth_rate_nm_s / max(A_ML_SI_NM * k_ex, 1e-30))
    L_seg_nm = A_ML_SI_NM / math.log1p(1.0 / max(r_s, 1e-12))

    # 5. Bulk thermal P & 29Si self-diffusion during MBE deposition (Fahey 1989 / Bracht 1998)
    D_P_nm2_s = 3.85e14 * math.exp(-3.66 / kT)
    D_Si_nm2_s = 530.0e14 * math.exp(-4.75 / kT)
    sigma_P_mbe_bulk_nm = math.sqrt(2.0 * D_P_nm2_s * t_dep_s)
    sigma_iso_mbe_nm = math.sqrt(2.0 * D_Si_nm2_s * t_dep_s)

    # 6. Composite MBE quality cost score (lower is better; identifies physical T_epi* optimum):
    #    Penalizes approaching Eaglesham breakdown, surface roughness >0.15 nm, N_def >1e15, and L_seg >3.0 nm
    pen_epi = (delta_z_cap_nm / max(h_epi_nm, 0.1)) ** 2
    pen_rq = (R_q_nm / 0.15) ** 2
    pen_def = math.log10(max(N_def_cm3 / 1.0e14, 1.0)) ** 2
    pen_seg = (L_seg_nm / 3.0) ** 2
    quality_cost = pen_epi + pen_rq + 0.5 * pen_def + pen_seg

    return {
        "T_epi_C": T_epi_C,
        "T_epi_K": round(T_K, 2),
        "delta_z_cap_nm": delta_z_cap_nm,
        "growth_rate_nm_s": growth_rate_nm_s,
        "deposition_time_s": round(t_dep_s, 2),
        "h_epi_nm": round(h_epi_nm, 2),
        "epi_margin_ratio": round(epi_margin_ratio, 2),
        "R_q_nm": round(R_q_nm, 4),
        "N_def_cm3": float(N_def_cm3),
        "L_seg_nm": round(L_seg_nm, 4),
        "sigma_P_mbe_bulk_nm": float(sigma_P_mbe_bulk_nm),
        "sigma_iso_mbe_nm": float(sigma_iso_mbe_nm),
        "quality_cost": round(quality_cost, 4),
        "meets_mbe_criteria": (
            h_epi_nm > 5.0 * delta_z_cap_nm
            and R_q_nm <= 0.20
            and N_def_cm3 <= 1.0e15
            and L_seg_nm <= 3.5
        ),
    }


def evaluate_fga_passivation_kinetics(
    P_H2_torr: float = 38.0,
    T_C: float = 350.0,
    t_min: float = 15.0,
) -> Dict[str, Any]:
    """Stesmans (JAP 88, 489, 2000) Henry's-law P_b center H2 passivation kinetics (OBS-094).

    At 1 atm 5% H2/N2 (P_H2 = 38 Torr, 350-400 C, 15 min), D_it drops from 1e11 to ~1.5e10 cm^-2 eV^-1.
    Under an 80 L/s TMP+NEG UHV leak-valve (P_H2 ~ 5e-7 to 5e-5 Torr), Henry's-law dissolved [H2]
    is 6-8 orders of magnitude lower -> required time scales to 21.7 - 2,170 years (and thermal
    depassivation dominates instead). Mandates an isolated valved ~1 atm furnace/RTA FGA cell.
    """
    P_ref_torr = 38.0  # 5% H2 in 1 atm (760 Torr) forming gas
    t_ref_min = 15.0
    p_ratio = P_H2_torr / P_ref_torr
    t_req_min = t_ref_min / max(p_ratio, 1e-18)
    t_req_years = t_req_min / (60.0 * 24.0 * 365.25)
    # Effective passivation feasible only near atmospheric forming gas (P_H2 >= 1 Torr)
    feasible_in_window = bool(t_req_min <= 2.0 * t_min and P_H2_torr >= 1.0)
    return {
        "P_H2_torr": float(P_H2_torr),
        "T_C": float(T_C),
        "t_process_min": float(t_min),
        "P_H2_ratio_vs_1atm_5pct": float(p_ratio),
        "required_passivation_time_min": float(t_req_min),
        "required_passivation_time_years": float(t_req_years),
        "feasible_15min_passivation": feasible_in_window,
        "thermal_depassivation_regime": bool(P_H2_torr < 1e-2),
    }


def evaluate_gate_oxide_and_regrowth_interface(
    delta_z_cap_nm: float = 8.0,
    d_ox_nm: float = 8.0,
    oxide_process: str = "ald_lowT",
    t_uhv_transfer_min: float = 5.0,
    P_uhv_torr: float = 2.0e-10,
) -> Dict[str, Any]:
    """Model gate-oxide Si consumption (0.44*d_ox), OED, and pre-MBE H-desorption contamination (OBS-095)."""
    if oxide_process == "thermal_SiO2":
        si_consumed_nm = 0.44 * d_ox_nm
        oed_sigma_nm = 0.25  # oxidation-enhanced interstitial injection broadening estimate
        effective_cap_nm = max(0.0, delta_z_cap_nm - si_consumed_nm)
        precompensated_cap_req_nm = delta_z_cap_nm + si_consumed_nm
    elif oxide_process == "ald_lowT":
        si_consumed_nm = 0.0
        oed_sigma_nm = 0.0
        effective_cap_nm = delta_z_cap_nm
        precompensated_cap_req_nm = delta_z_cap_nm
    else:
        raise ValueError(f"Unsupported oxide_process={oxide_process}")

    # 1530 K flash desorbs surface H (>800 K), exposing 6.78e14 cm^-2 reactive Si(100)-(2x1) dangling bonds
    langmuir_exposure = (P_uhv_torr * (t_uhv_transfer_min * 60.0)) / 1.0e-6  # 1 L = 1e-6 Torr*s
    # Conservative sticking ~ 0.05 for residual H2O/CO -> buried interface traps at z = effective_cap_nm
    n_ads_cm2 = min(6.78e14, 6.78e14 * 0.05 * langmuir_exposure)
    # Small fraction (~1e-3) becomes electrically active TLS/border traps at regrowth plane
    D_it_regrowth_cm2_eV = 1.0e-3 * n_ads_cm2

    return {
        "oxide_process": oxide_process,
        "d_ox_nm": float(d_ox_nm),
        "nominal_mbe_cap_nm": float(delta_z_cap_nm),
        "si_consumed_nm": round(si_consumed_nm, 3),
        "effective_cap_after_oxide_nm": round(effective_cap_nm, 3),
        "precompensated_cap_required_nm": round(precompensated_cap_req_nm, 3),
        "oed_extra_sigma_nm": oed_sigma_nm,
        "pre_mbe_flash_h_desorbed": True,
        "si100_dangling_bonds_cm2": 6.78e14,
        "uhv_transfer_time_min": float(t_uhv_transfer_min),
        "uhv_pressure_torr": float(P_uhv_torr),
        "langmuir_exposure_L": round(langmuir_exposure, 5),
        "regrowth_interface_D_it_cm2_eV": float(D_it_regrowth_cm2_eV),
    }


def run_coupled_thermal_chain_ted(
    Rp_nm: float,
    sigma_z_nm: float,
    T_epi_C: float = 345.0,
    t_mbe_s: float = 80.0,
    wavelength_nm: float = 808.0,
    t_pulse_s: float = 1.0e-3,
    T_peak_K: float = 1440.0,
    n_flash_pulses: int = 1,
    C_cl_peak_cm3: float = 3.0e19,
    params: KineticsParams | None = None,
) -> Dict[str, Any]:
    """Run Exp130's exact 1D nonlinear thermal PDE + TED/kick-out/29Si PDE across the
    COMPLETE sequential thermal chain with smooth RT cooldown between flash & MBE:
      Stage 1 (Flash only): n_flash_pulses x (808 nm, t_pulse_s -> T_peak_K)
      Stage 2 (Route A): Stage 1 + 5 s RT cooldown + low-T 28Si MBE dwell (T_epi_C for t_mbe_s)
      Stage 3 (Route C): Stage 2 + 350 C / 15 min (900 s) dedicated 1 atm FGA passivation
    Uses updated Em_I=0.90 eV + explicit V(z,t) I-V recombination by default (OBS-038).
    """
    th = find_fluence_for_target_T(t_pulse_s, T_peak_K, wavelength_nm=wavelength_nm)
    t_single = th["t_s"]
    T_single = th["T_surf_K"]

    t_parts: List[np.ndarray] = []
    T_parts: List[np.ndarray] = []
    t_off = 0.0
    for idx_p in range(n_flash_pulses):
        if idx_p == 0:
            t_parts.append(t_single)
            T_parts.append(T_single)
            t_off = float(t_single[-1])
        else:
            # 50 ms inter-pulse gap cooling gently toward 300 K
            t_gap = t_off + np.geomspace(1e-4, 0.05, 16)
            T_gap = 300.0 + (float(T_single[-1]) - 300.0) * np.exp(-(t_gap - t_off) / 0.05)
            t_parts.append(t_gap)
            T_parts.append(T_gap)
            t_off = float(t_gap[-1])
            t_parts.append(t_off + t_single[1:])
            T_parts.append(T_single[1:])
            t_off = float(t_parts[-1][-1])

    t_fl = np.concatenate(t_parts)
    T_fl = np.concatenate(T_parts)

    # Exact {311} interstitial cluster dissolution integral during flash stage
    k_params = params if params is not None else KineticsParams()
    int_kd = 0.0
    for k in range(t_fl.size - 1):
        Tm = 0.5 * float(T_fl[k] + T_fl[k + 1])
        dt = float(t_fl[k + 1] - t_fl[k])
        if Tm > 450.0 and dt > 0.0:
            int_kd += k_params.nu_cl_s * math.exp(-k_params.Ea_cl_diss_eV / (KB_EV * Tm)) * dt
    cluster_rem_frac = math.exp(-min(int_kd, 500.0))

    # Smooth 5 s RT cooldown before MBE + fine logarithmic MBE & forming-gas time grids
    t_cool = t_off + np.geomspace(1e-4, 5.0, 50)
    T_cool = 300.0 + (float(T_fl[-1]) - 300.0) * np.exp(-(t_cool - t_off) / 0.5)
    t_mbe = float(t_cool[-1]) + np.geomspace(1e-3, t_mbe_s, 60)
    T_mbe = np.full_like(t_mbe, T_epi_C + 273.15)
    t_fg = float(t_mbe[-1]) + np.geomspace(1e-2, 900.0, 60)
    T_fg = np.full_like(t_fg, 350.0 + 273.15)

    r_flash = solve_ted_kinetics_1d(t_fl, T_fl, Rp_nm=Rp_nm, sigma_z_nm=sigma_z_nm, C_cl_peak_cm3=C_cl_peak_cm3, r_casc_nm=2.5, params=k_params)
    r_route_A = solve_ted_kinetics_1d(
        np.concatenate([t_fl, t_cool, t_mbe]),
        np.concatenate([T_fl, T_cool, T_mbe]),
        Rp_nm=Rp_nm, sigma_z_nm=sigma_z_nm, C_cl_peak_cm3=C_cl_peak_cm3, r_casc_nm=2.5, params=k_params,
    )
    r_route_C = solve_ted_kinetics_1d(
        np.concatenate([t_fl, t_cool, t_mbe, t_fg]),
        np.concatenate([T_fl, T_cool, T_mbe, T_fg]),
        Rp_nm=Rp_nm, sigma_z_nm=sigma_z_nm, C_cl_peak_cm3=C_cl_peak_cm3, r_casc_nm=2.5, params=k_params,
    )

    def _pack(r: Dict[str, Any]) -> Dict[str, float]:
        return {
            "f_act_bulk": round(float(r["f_act_bulk"]), 6),
            "sigma_anneal_nm": round(float(r["sigma_anneal_nm"]), 5),
            "f_total_surface_loss": round(float(r["f_total_surface_loss"]), 6),
            "sigma_iso_nm": round(float(r["sigma_iso_nm"]), 6),
            "mass_conservation_err": float(r["mass_conservation_err"]),
        }

    return {
        "n_flash_pulses": n_flash_pulses,
        "fluence_per_pulse_J_per_cm2": round(float(th["fluence_J_per_cm2"]), 3),
        "T_peak_K": round(float(th["T_peak_K"]), 2),
        "T_peak_over_Tmelt": round(float(th["T_peak_over_Tmelt"]), 4),
        "T_back_max_K": round(float(th["T_back_max_K"]), 2),
        "cluster_dissolution_integral": round(int_kd, 3),
        "cluster_remaining_frac_post_flash": round(cluster_rem_frac, 6),
        "flash_only": _pack(r_flash),
        "route_A_flash_plus_mbe": _pack(r_route_A),
        "route_C_full_chain": _pack(r_route_C),
        "delta_sigma_anneal_route_A_nm": round(float(r_route_A["sigma_anneal_nm"] - r_flash["sigma_anneal_nm"]), 6),
        "delta_sigma_anneal_route_C_nm": round(float(r_route_C["sigma_anneal_nm"] - r_flash["sigma_anneal_nm"]), 6),
        "delta_surface_loss_route_C": round(float(r_route_C["f_total_surface_loss"] - r_flash["f_total_surface_loss"]), 7),
        "delta_sigma_iso_route_C_nm": round(float(r_route_C["sigma_iso_nm"] - r_flash["sigma_iso_nm"]), 7),
    }


# =============================================================================
# 3. Exact 2D Image-Charge McWhorter Electrostatics (S_eps & S_E Bridge to Exp137)
# =============================================================================
def mcwhorter_geom_integrals(
    z_donor_nm: float,
    z_int_nm: float = 2.0,
    d_ox_nm: float = 8.0,
    r_min_nm: float = 0.5,
    r_max_nm: float = 400.0,
    n_r: int = 800,
) -> Dict[str, float]:
    """Compute exact 2D radial integrals for a uniform sheet of independent interface
    charge fluctuators on the Si/SiO2 plane (z=0) screened by a metallic gate at z=-d_ox.

    Returns:
      - I_ff_eV2_nm2: int_0^inf [e*(phi(r, z_int) - phi(r, z_donor))]^2 * 2*pi*r dr  (flip-flop detuning)
      - I_Ez_V2:      int_0^inf [E_z(r, z_donor)]^2 * 2*pi*r dr                      (buried-donor field)
    """
    r = np.geomspace(r_min_nm, r_max_nm, n_r)
    pref_V_nm = E_CHARGE / (4.0 * math.pi * EPS_0 * EPS_AVG * 1e-9)  # V * nm (potential at 1 nm)

    def phi_V(z_nm: float) -> np.ndarray:
        # Charge +e at (r, 0) + metallic gate image -e at (r, -2*d_ox)
        return pref_V_nm * (
            1.0 / np.sqrt(r * r + z_nm * z_nm)
            - 1.0 / np.sqrt(r * r + (z_nm + 2.0 * d_ox_nm) ** 2)
        )

    def Ez_V_nm(z_nm: float) -> np.ndarray:
        return pref_V_nm * (
            z_nm / ((r * r + z_nm * z_nm) ** 1.5)
            - (z_nm + 2.0 * d_ox_nm) / ((r * r + (z_nm + 2.0 * d_ox_nm) ** 2) ** 1.5)
        )

    # Detuning shift (eV) = e * [phi(z_int) - phi(z_donor)] -> numerically phi_V [V] == energy [eV]
    d_eps_eV = phi_V(z_int_nm) - phi_V(z_donor_nm)
    I_ff = float(np.trapezoid((d_eps_eV ** 2) * 2.0 * math.pi * r, r))

    ez = Ez_V_nm(z_donor_nm)  # V/nm
    I_ez = float(np.trapezoid((ez ** 2) * 2.0 * math.pi * r, r))

    return {
        "I_ff_eV2_nm2": I_ff,
        "I_Ez_V2": I_ez,
    }


def evaluate_charge_noise_routes(
    z_donor_nm: float,
    D_it_cm2_eV: float,
    d_ox_nm: float = 8.0,
    z_int_nm: float = 2.0,
    bulk_defect_N_cm3: float = 1.0e14,
    recoil_O_per_ion: float = 0.0,
    ref_z_donor_nm: float = 14.5,
    ref_D_it_cm2_eV: float = 1.0e11,
    ref_d_ox_nm: float = 8.0,
    ref_S_eps_ueV: float = 1.00,
    n_r: int = 800,
) -> Dict[str, float]:
    """Compute physical 1/f charge-noise amplitude S_eps (1 Hz, ueV/sqrt(Hz)) for flip-flop
    qubits and relative buried-donor electric-field noise S_E / S_E_ref via exact 2D
    image-charge McWhorter integration anchored once to (D_it=1e11, z=14.5 nm, d_ox=8 nm -> 1.0 ueV/sqrt(Hz)).

    Also includes exact additive variance from:
      - LT-MBE bulk point-defect TLS traps within the cap volume (negligible below 1e15 cm^-3),
      - Through-cap recoil-oxygen/ion-damage interface trap enhancement (for Route B).
    """
    ref_g = mcwhorter_geom_integrals(ref_z_donor_nm, z_int_nm=z_int_nm, d_ox_nm=ref_d_ox_nm, n_r=n_r)
    cur_g = mcwhorter_geom_integrals(z_donor_nm, z_int_nm=z_int_nm, d_ox_nm=d_ox_nm, n_r=n_r)

    # Effective interface trap density including residual LT-MBE bulk defects projected to 8 nm cap
    # (N_def * 8 nm / 1 eV bandgap) and recoil-O interface damage (each recoil-O increases local D_it_eff)
    D_it_mbe_proj = bulk_defect_N_cm3 * 8.0e-7  # cm^-2 (over 8 nm cap, ~1 eV active window)
    D_it_recoil_add = recoil_O_per_ion * 1.1e11  # localized ion+recoil-O interface trap enhancement
    D_it_eff = D_it_cm2_eV + D_it_mbe_proj + D_it_recoil_add

    S_eps_ueV = ref_S_eps_ueV * math.sqrt((D_it_eff / ref_D_it_cm2_eV) * (cur_g["I_ff_eV2_nm2"] / ref_g["I_ff_eV2_nm2"]))
    S_E_ratio = math.sqrt((D_it_eff / ref_D_it_cm2_eV) * (cur_g["I_Ez_V2"] / ref_g["I_Ez_V2"]))

    # Bare (un-capped) 5 keV reference (z=6.5 nm, D_it=1e11) for buried-donor distance gain check
    bare_g = mcwhorter_geom_integrals(6.5, z_int_nm=z_int_nm, d_ox_nm=ref_d_ox_nm, n_r=n_r)
    S_E_vs_uncapped_5keV = math.sqrt((D_it_eff / ref_D_it_cm2_eV) * (cur_g["I_Ez_V2"] / bare_g["I_Ez_V2"]))

    return {
        "z_donor_nm": round(z_donor_nm, 3),
        "d_ox_nm": d_ox_nm,
        "D_it_base_cm2_eV": D_it_cm2_eV,
        "D_it_eff_cm2_eV": float(D_it_eff),
        "S_eps_ueV_rtHz": round(S_eps_ueV, 4),
        "S_E_ratio_vs_14p5nm_1e11": round(S_E_ratio, 4),
        "S_E_ratio_vs_uncapped_5keV": round(S_E_vs_uncapped_5keV, 4),
        "I_ff_eV2_nm2": cur_g["I_ff_eV2_nm2"],
        "I_Ez_V2": cur_g["I_Ez_V2"],
    }


# =============================================================================
# 4. Coupled Exp131 4x4 Tosi Flip-Flop Yield Evaluator for Any Process Route
# =============================================================================
def evaluate_route_flipflop_yield(
    z_samples_nm: np.ndarray,
    r_xy_samples_nm: np.ndarray,
    s_eps_uev: float,
    z_r_ohm: float = 3000.0,
    q_l: float = 2.0e5,
    max_donors: int = 2000,
    seed: int = 2026139,
) -> Dict[str, Any]:
    """Run Exp131's exact 4x4 Tosi flip-flop Hamiltonian & DC clock-transition optimization
    directly on a route's final 3D donor ensemble (z_final, r_xy_final) and route S_eps.
    """
    rng = np.random.default_rng(seed)
    n_avail = z_samples_nm.size
    if n_avail > max_donors:
        sel = rng.choice(n_avail, size=max_donors, replace=False)
        zs = z_samples_nm[sel]
        rs = r_xy_samples_nm[sel]
    else:
        zs = z_samples_nm
        rs = r_xy_samples_nm

    n_tot = zs.size
    c_tuned = np.zeros(n_tot, dtype=np.float64)
    g_effs: List[float] = []
    gamma_phis: List[float] = []
    n_ge_100 = 0
    n_ge_10 = 0
    n_too_shallow = 0

    for i in range(n_tot):
        zi = float(zs[i])
        ri = float(rs[i])
        if zi < Z_MIN_DOUBLE_WELL_NM:
            n_too_shallow += 1
            continue
        best = optimize_cell_dc_bias(zi, ri, z_r_ohm=z_r_ohm, q_l=q_l, s_eps_uev=s_eps_uev)
        if best is not None:
            c_tuned[i] = best.cooperativity
            if best.cooperativity >= 10.0:
                n_ge_10 += 1
            if best.cooperativity >= 100.0:
                n_ge_100 += 1
                g_effs.append(best.g_eff_mhz)
                gamma_phis.append(best.gamma_phi_khz)

    return {
        "n_donors": int(n_tot),
        "s_eps_uev": round(s_eps_uev, 4),
        "mean_z_nm": round(float(np.mean(zs)), 3),
        "std_z_nm": round(float(np.std(zs)), 3),
        "mean_r_xy_nm": round(float(np.mean(rs)), 3),
        "frac_too_shallow_lt_8p5nm": round(n_too_shallow / n_tot, 4),
        "yield_C_ge_10": round(n_ge_10 / n_tot, 4),
        "yield_C_ge_100": round(n_ge_100 / n_tot, 4),
        "median_C_tuned": round(float(np.median(c_tuned)), 2),
        "certified_median_g_eff_mhz": round(float(np.median(g_effs)), 4) if g_effs else 0.0,
        "certified_median_gamma_phi_khz": round(float(np.median(gamma_phis)), 3) if gamma_phis else 0.0,
    }


if __name__ == "__main__":
    print("=== Quick Physics Verification (Exp139) ===")
    tbl = build_zbl_scattering_table()
    for E_k in (5.0, 14.0, 20.0, 22.0, 24.0):
        b = simulate_bca_31p_in_si(E_k, 2000, tbl, seed=2026139)
        print(f"  BCA E={E_k:4.1f} keV: Rp={b['Rp_nm']:5.2f} nm, sig_z={b['sigma_z_nm']:4.2f} nm, sig_x={b['sigma_x_nm']:4.2f} nm")
    rec20 = simulate_recoil_oxygen_through_oxide(20.0, 1.5, 2000, tbl)
    print("  Recoil-O (20 keV through 1.5 nm SiO2):", rec20)
    print("\n--- LT-MBE Sweep (250..450 C, 8 nm @ 0.1 nm/s) ---")
    for T_c in (250, 280, 310, 330, 340, 350, 370, 400, 450):
        m = evaluate_lt_mbe_kinetics(float(T_c))
        print(f"  T={T_c}C: h_epi={m['h_epi_nm']:7.1f}nm R_q={m['R_q_nm']:.3f}nm N_def={m['N_def_cm3']:.2e} L_seg={m['L_seg_nm']:.2f}nm cost={m['quality_cost']:.3f} ok={m['meets_mbe_criteria']}")
    print("\n--- McWhorter Charge-Noise Routes ---")
    for lbl, zd, dit, ro in [
        ("Route B (20keV thru-cap)", 14.5, 1.8e11, rec20["O_injected_into_Si_per_ion"]),
        ("Route A (pristine MBE)", 14.5, 1.0e11, 0.0),
        ("Route C (FG 350C, 1.5e10)", 14.5, 1.5e10, 0.0),
        ("Route C-best (1.0e10, 5nm ox)", 14.5, 1.0e10, 0.0),
    ]:
        dox = 5.0 if "5nm" in lbl else 8.0
        cn = evaluate_charge_noise_routes(zd, dit, d_ox_nm=dox, recoil_O_per_ion=ro)
        print(f"  {lbl:30s}: D_it_eff={cn['D_it_eff_cm2_eV']:.2e} S_eps={cn['S_eps_ueV_rtHz']:.4f} ueV/rtHz  S_E/S_E0={cn['S_E_ratio_vs_uncapped_5keV']:.3f}")
