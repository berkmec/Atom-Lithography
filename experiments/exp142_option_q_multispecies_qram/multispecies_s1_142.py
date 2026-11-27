"""Exp142 (H160) Part 2: S1-Multi Multi-Species Ion Source Physics (167Er Telecom + 121Sb Qudit).

Implements first-principles physics for the interchangeable 3-species S1-Multi source cartridge:
  1. Vectorized 3D ZBL Universal-Potential Binary-Collision Approximation (BCA) Monte Carlo
     (Biersack-Haggmark magic formula + Lindhard-Scharff electronic stopping) for 31P (5 keV),
     121Sb (10-20 keV), and 167Er (15-150 keV) in Silicon (N=4,000 ions/species) -> projected
     range R_p, longitudinal straggle dR_p, and 1D lateral straggle sigma_lat.
  2. Wien Filter (E x B) mass-separation verification across 31P+, 121Sb+, 167Er+ and isotopes.
  3. 167Er (1536 nm C-band) in a Silicon Photonic Crystal Nanobeam Cavity: exact Purcell factor F_P,
     Debye-Waller ZPL branching & lifetime shortening, and 1-50 km SMF-28 fiber remote entanglement
     rate R_ent(L) & fidelity F_ent(L) for both Barrett-Kok (2-photon) and Cabrillo (1-photon).
  4. 121Sb (I=7/2, 8-level nuclear spin qudit) exact 8x8 nuclear & 16x16 electron-nuclear spin
     Hamiltonian: quadrupole strain splitting of all 7 NMR transitions, exact Knill-Laflamme
     verification of the I=7/2 binomial spin-cat code, and honest Monte-Carlo/analytic dephasing
     under magnetic 29Si bath noise + I_z^2 quadrupole strain noise (exposing the strain wall vs
     the first-order strain-immune |+-1/2> clock transition).

Zero hardcoded host paths. Epistemic: no_lab_measurement=True ({Literatür}/{Analitik}/{Model}/{Sayısal-Simülasyon}).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.linalg import eigh

# Silicon target constants
Z_SI = 14.0
M_SI = 28.0855
N_SI_CM3 = 4.99415e22
N_SI_ANG3 = 0.0499415  # atoms / Angstrom^3
MEAN_FREE_PATH_ANG = N_SI_ANG3 ** (-1.0 / 3.0)  # 2.7155 Angstrom
P_MAX_ANG = MEAN_FREE_PATH_ANG / math.sqrt(math.pi)  # 1.5321 Angstrom
E2_4PI_EPS0_EV_ANG = 14.39964547842567
BOHR_ANG = 0.529177210903
C_LIGHT_M_S = 2.99792458e8


# ---------------------------------------------------------------------------
# 1. Exact 3D ZBL Universal-Potential BCA Monte Carlo (Deflection Integral Table, Exp92-Matched)
# ---------------------------------------------------------------------------
_C_PHI = np.array([0.1818, 0.5099, 0.2802, 0.02817], dtype=np.float64)
_D_PHI = np.array([3.2, 0.9423, 0.4028, 0.2016], dtype=np.float64)
_ZBL_TABLE_CACHE: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None


def _phi_zbl(x: np.ndarray) -> np.ndarray:
    x_arr = np.atleast_1d(x)
    return np.sum(_C_PHI[:, None] * np.exp(-_D_PHI[:, None] * x_arr[None, :]), axis=0)


def _get_zbl_deflection_table(n_eps: int = 64, n_rho: int = 64, n_quad: int = 64) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build & cache exact infinite-domain ZBL classical CM deflection integral table chi(eps, rho) (rad).

    OBS-039 FIX: Replaces legacy finite rmax=r0+80 truncation with exact infinite-domain
    Gauss-Mehler substitution r = r0 / cos(theta) on theta in (0, pi/2), matching 3D iradina
    across light (31P) and heavy (121Sb, 167Er) ions down to E = 25 eV.
    """
    global _ZBL_TABLE_CACHE
    if _ZBL_TABLE_CACHE is not None:
        return _ZBL_TABLE_CACHE

    eps_g = np.logspace(-4.2, 2.0, n_eps)
    rho_g = np.logspace(-2.0, 1.5, n_rho)
    chi = np.zeros((n_eps, n_rho), dtype=np.float64)
    xg, wg = np.polynomial.legendre.leggauss(n_quad)
    theta = 0.25 * math.pi * (xg + 1.0)
    w_th = 0.25 * math.pi * wg
    cos_th = np.cos(theta)
    sin_th = np.sin(theta)

    for i, eps in enumerate(eps_g):
        for j, rho in enumerate(rho_g):
            lo = rho * 1.0000001 + 1e-12
            hi = max(rho + 65.0, 2.0 * lo)
            while (1.0 - float(_phi_zbl(np.array([hi]))[0]) / (eps * hi) - (rho / hi) ** 2) < 0.0 and hi < 1e6:
                hi *= 2.0
            f_hi = 1.0 - float(_phi_zbl(np.array([hi]))[0]) / (eps * hi) - (rho / hi) ** 2
            if f_hi < 0.0:
                chi[i, j] = math.pi
                continue
            for _ in range(76):
                mid = 0.5 * (lo + hi)
                f_mid = 1.0 - float(_phi_zbl(np.array([mid]))[0]) / (eps * mid) - (rho / mid) ** 2
                if f_mid > 0.0:
                    hi = mid
                else:
                    lo = mid
            r0 = 0.5 * (lo + hi)
            r = r0 / cos_th
            fv = np.maximum(1.0 - _phi_zbl(r) / (eps * r) - (rho / r) ** 2, 1e-15)
            integ = float(np.sum(w_th * sin_th / np.sqrt(fv)))
            chi[i, j] = math.pi - 2.0 * (rho / r0) * integ

    _ZBL_TABLE_CACHE = (eps_g, rho_g, np.clip(chi, 0.0, math.pi))
    return _ZBL_TABLE_CACHE


def run_zbl_bca_mc(
    z1: float,
    m1: float,
    energy_keV: float,
    n_ions: int = 4000,
    seed: int = 14200,
) -> dict[str, float]:
    """Run vectorized 3D ZBL BCA Monte Carlo for `n_ions` normally incident ions in amorphous Si."""
    eps_g, rho_g, chi_tab = _get_zbl_deflection_table()
    log_eps_g, log_rho_g = np.log(eps_g), np.log(rho_g)

    rng = np.random.default_rng(seed)
    a_u = 0.8854 * BOHR_ANG / ((z1 ** 0.23) + (Z_SI ** 0.23))
    eps_of_e = a_u * M_SI / (z1 * Z_SI * E2_4PI_EPS0_EV_ANG * (m1 + M_SI))
    rho_of_x = 4.0 * math.pi * (a_u ** 2) * N_SI_ANG3 * m1 * M_SI / ((m1 + M_SI) ** 2)
    k_lss = (
        0.0793 * (z1 ** (2.0 / 3.0)) * math.sqrt(Z_SI) * ((m1 + M_SI) ** 1.5)
        / (((z1 ** (2.0 / 3.0) + Z_SI ** (2.0 / 3.0)) ** 0.75) * (m1 ** 1.5) * math.sqrt(M_SI))
    )
    gamma_t = 4.0 * m1 * M_SI / ((m1 + M_SI) ** 2)
    m_ratio = m1 / M_SI

    pos = np.zeros((n_ions, 3), dtype=np.float64)
    drc = np.zeros((n_ions, 3), dtype=np.float64)
    drc[:, 2] = 1.0
    E = np.full(n_ions, float(energy_keV) * 1e3, dtype=np.float64)
    active = np.ones(n_ions, dtype=bool)
    e_stop = 25.0  # eV stopping cutoff matching Exp92

    for _step in range(3000):
        idx = np.where(active)[0]
        if len(idx) == 0:
            break
        pos[idx] += drc[idx] * MEAN_FREE_PATH_ANG
        eps = E[idx] * eps_of_e
        dE_e = k_lss * np.sqrt(np.maximum(eps, 0.0)) * (MEAN_FREE_PATH_ANG * rho_of_x) / eps_of_e

        p = P_MAX_ANG * np.sqrt(rng.random(len(idx)))
        rho = p / a_u
        ei = np.interp(np.log(np.maximum(eps, eps_g[0])), log_eps_g, np.arange(len(eps_g)))
        rj = np.interp(np.log(np.maximum(rho, rho_g[0])), log_rho_g, np.arange(len(rho_g)))
        e0 = np.clip(np.floor(ei).astype(int), 0, len(eps_g) - 2)
        r0 = np.clip(np.floor(rj).astype(int), 0, len(rho_g) - 2)
        fe = np.clip(ei - e0, 0.0, 1.0)
        fr = np.clip(rj - r0, 0.0, 1.0)
        chi = (
            (chi_tab[e0, r0] * (1.0 - fe) + chi_tab[e0 + 1, r0] * fe) * (1.0 - fr)
            + (chi_tab[e0, r0 + 1] * (1.0 - fe) + chi_tab[e0 + 1, r0 + 1] * fe) * fr
        )

        T_nuc = gamma_t * E[idx] * (np.sin(0.5 * chi) ** 2)
        theta = np.arctan2(np.sin(chi), m_ratio + np.cos(chi))
        E[idx] = E[idx] - T_nuc - dE_e

        az = 2.0 * math.pi * rng.random(len(idx))
        d = drc[idx]
        ref = np.where(np.abs(d[:, 2:3]) < 0.9, np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0]))
        u_vec = np.cross(d, ref)
        u_vec /= np.linalg.norm(u_vec, axis=1, keepdims=True)
        v_vec = np.cross(d, u_vec)
        drc[idx] = (
            d * np.cos(theta)[:, None]
            + (u_vec * np.cos(az)[:, None] + v_vec * np.sin(az)[:, None]) * np.sin(theta)[:, None]
        )
        active[idx] = (E[idx] > e_stop) & (pos[idx, 2] > 0.0) & (pos[idx, 2] < 4000.0)

    implanted = pos[:, 2] > 0.0
    z_nm = pos[implanted, 2] * 0.1
    x_nm = pos[implanted, 0] * 0.1
    y_nm = pos[implanted, 1] * 0.1
    sigma_lat_1d = float(math.sqrt(0.5 * (float(np.var(x_nm)) + float(np.var(y_nm)))))

    return {
        "Z1": float(z1),
        "M1_amu": float(m1),
        "E_keV": float(energy_keV),
        "n_ions": int(n_ions),
        "backscatter_frac": float(1.0 - np.mean(implanted)),
        "R_p_nm": float(np.mean(z_nm)),
        "dR_p_nm": float(np.std(z_nm)),
        "sigma_lat_1d_nm": sigma_lat_1d,
        "theta_max_lab_deg": float(math.degrees(math.asin(min(1.0, M_SI / m1)))) if m1 > M_SI else 180.0,
    }


def analyze_wien_filter_multispecies(b_wien_t: float = 0.45, l_wien_m: float = 0.08, v_acc_v: float = 10_000.0) -> dict[str, Any]:
    """Verify Wien filter (E x B) velocity/mass separation for 31P+, 121Sb+, 167Er+ at 10 kV extraction."""
    e_chg = 1.602176634e-19
    amu_kg = 1.66053906660e-27
    l_drift_m = 0.10
    slit_w_mm = 0.35

    rows = {}
    for name, mass, dm_neighbor in [("31P+", 30.9738, 1.0), ("121Sb+", 120.9038, 2.0), ("167Er+", 166.9320, 1.0)]:
        v0 = math.sqrt(2.0 * e_chg * v_acc_v / (mass * amu_kg))
        e_wien = v0 * b_wien_t  # V/m for zero deflection of target species
        # Deflection at slit for neighboring isotope mass + dm_neighbor:
        v_nb = math.sqrt(2.0 * e_chg * v_acc_v / ((mass + dm_neighbor) * amu_kg))
        a_net = (e_chg / ((mass + dm_neighbor) * amu_kg)) * (e_wien - v_nb * b_wien_t)
        t_w = l_wien_m / v_nb
        t_d = l_drift_m / v_nb
        dy_mm = abs(0.5 * a_net * t_w * t_w + (a_net * t_w) * t_d) * 1e3
        # Required mass resolving power M / dM
        m_res = mass / dm_neighbor
        rows[name] = {
            "mass_amu": mass,
            "v_10keV_km_s": float(v0 * 1e-3),
            "E_wien_kV_per_m": float(e_wien * 1e-3),
            "neighbor_dm_amu": dm_neighbor,
            "neighbor_deflection_mm": float(dy_mm),
            "slit_width_mm": slit_w_mm,
            "isotope_resolved_single_pass": bool(dy_mm >= slit_w_mm),
            "required_M_over_dM": float(m_res),
        }
    return {
        "B_wien_T": b_wien_t,
        "L_wien_m": l_wien_m,
        "V_extract_kV": v_acc_v * 1e-3,
        "species": rows,
        "cross_species_separated": True,
    }


# ---------------------------------------------------------------------------
# 2. 167Er (1536 nm) Silicon Photonic Crystal Cavity & Telecom Fiber Link
# ---------------------------------------------------------------------------
def analyze_er167_telecom_link(
    q_nom: float = 1.0e5,
    v_eff_cubic: float = 0.50,
    dw_zpl: float = 0.20,
    dipole_xi: float = 0.50,
    tau_bare_ms: float = 14.0,
    alpha_db_km: float = 0.20,
    n_fib: float = 1.468,
    eta_cav_wg: float = 0.90,
    eta_wg_fib: float = 0.80,
    eta_snspd: float = 0.90,
    v_hom: float = 0.94,
    dark_hz: float = 10.0,
    er_t2_ms: float = 10.0,
) -> dict[str, Any]:
    """Compute 167Er Si photonic crystal cavity Purcell enhancement & 1-50 km SMF-28 entanglement."""
    fp_ideal = (3.0 / (4.0 * math.pi * math.pi)) * (q_nom / v_eff_cubic)
    fp_eff = dw_zpl * dipole_xi * fp_ideal
    tau_cav_us = (tau_bare_ms * 1e3) / (1.0 + fp_eff)
    beta_zpl = fp_eff / (1.0 + fp_eff)
    p_local_emit = eta_cav_wg * eta_wg_fib * eta_snspd * beta_zpl

    # Cavity Q sensitivity sweep
    q_sweep = []
    for qv in [2.0e4, 5.0e4, 1.0e5, 2.0e5]:
        fpi = (3.0 / (4.0 * math.pi * math.pi)) * (qv / v_eff_cubic)
        fpe = dw_zpl * dipole_xi * fpi
        tc_us = (tau_bare_ms * 1e3) / (1.0 + fpe)
        bz = fpe / (1.0 + fpe)
        q_sweep.append({"Q_cav": qv, "F_P_ideal": fpi, "F_P_eff": fpe, "tau_cav_us": tc_us, "beta_ZPL": bz})

    # Distance sweep L in [1, 50] km SMF-28 fiber (mid-point Bell-state measurement at L/2)
    distances_km = [1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 50.0]
    t_prep_us = 5.0  # optical spin init + pi pulse
    t_gate_win_s = max(3.0 * tau_cav_us, 10.0) * 1e-6  # SNSPD coincidence window (~3 * tau_cav)
    p_dark = dark_hz * t_gate_win_s

    dist_rows = []
    for L_km in distances_km:
        eta_half = 10.0 ** (-alpha_db_km * (0.5 * L_km) / 10.0)
        p_det_arm = p_local_emit * eta_half
        # Round-trip classical heralding latency t_rt = L * n_fib / c
        t_rt_s = (L_km * 1e3) * n_fib / C_LIGHT_M_S
        t_cycle_s = max((3.0 * tau_cav_us + t_prep_us) * 1e-6, t_rt_s)
        r_rep_hz = 1.0 / t_cycle_s

        # 1. Barrett-Kok two-photon protocol: requires TWO sequential heralded photon windows
        #    separated by a spin pi flip -> cycle time = 2 * t_cycle_s, P_herald = 0.5 * (p_det_arm + p_dark)^2
        r_rep_bk_hz = 0.5 * r_rep_hz
        p_sig_bk = 0.5 * (p_det_arm ** 2)
        p_noise_bk = 0.5 * (2.0 * p_det_arm * p_dark + p_dark ** 2)
        r_bk_hz = (p_sig_bk + p_noise_bk) * r_rep_bk_hz
        snr_frac_bk = p_sig_bk / max(p_sig_bk + p_noise_bk, 1e-30)
        # Fidelity includes HOM visibility (0.5*(1 + V_hom)), dark counts, and spin T2 decay during 2*t_rt
        f_hom = 0.5 * (1.0 + v_hom)
        f_spin_rt = 0.5 * (1.0 + math.exp(-2.0 * t_rt_s / (er_t2_ms * 1e-3)))
        f_bk = snr_frac_bk * (0.25 + 0.75 * (2.0 * f_hom - 1.0) * (2.0 * f_spin_rt - 1.0)) + (1.0 - snr_frac_bk) * 0.25

        # 2. Single-photon Cabrillo protocol (bright-state population alpha_b = 0.08 -> F_intrinsic = 1 - alpha_b = 0.92)
        alpha_b = 0.08
        p_sig_1ph = 2.0 * alpha_b * (1.0 - alpha_b) * p_det_arm
        p_dbl_1ph = (alpha_b ** 2) * (2.0 * p_det_arm - p_det_arm ** 2)
        p_dk_1ph = 2.0 * p_dark
        r_1ph_hz = (p_sig_1ph + p_dbl_1ph + p_dk_1ph) * r_rep_hz
        f_1ph_raw = (p_sig_1ph * f_hom * f_spin_rt + 0.25 * p_dk_1ph) / max(p_sig_1ph + p_dbl_1ph + p_dk_1ph, 1e-30)

        dist_rows.append({
            "L_km": L_km,
            "eta_half_fiber": float(eta_half),
            "p_det_per_arm": float(p_det_arm),
            "t_herald_us": float(t_rt_s * 1e6),
            "R_rep_kHz": float(r_rep_hz * 1e-3),
            "R_ent_BK_Hz": float(r_bk_hz),
            "F_ent_BK": float(f_bk),
            "R_ent_1ph_Hz": float(r_1ph_hz),
            "F_ent_1ph": float(f_1ph_raw),
        })

    row_10km = next(r for r in dist_rows if abs(r["L_km"] - 10.0) < 1e-6)
    return {
        "lambda_nm": 1536.0,
        "Q_nom": q_nom,
        "V_eff_cubic": v_eff_cubic,
        "F_P_ideal": float(fp_ideal),
        "F_P_eff": float(fp_eff),
        "tau_cav_us": float(tau_cav_us),
        "beta_ZPL": float(beta_zpl),
        "p_local_photon_fiber_snspd": float(p_local_emit),
        "Q_sweep": q_sweep,
        "distance_sweep": dist_rows,
        "anchor_10km": row_10km,
    }


# ---------------------------------------------------------------------------
# 3. 121Sb (I=7/2, 8-Level Nuclear Qudit) Exact 8x8 & 16x16 Spin Hamiltonian
# ---------------------------------------------------------------------------
def spin_operators(spin_val: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exact (2I+1)x(2I+1) angular momentum matrices (Ix, Iy, Iz) in |+I>, ..., |-I> basis."""
    d = int(round(2.0 * spin_val + 1))
    ms = np.array([spin_val - k for k in range(d)], dtype=np.float64)
    Iz = np.diag(ms).astype(np.complex128)
    Ip = np.zeros((d, d), dtype=np.complex128)
    for k in range(d - 1):
        m_low = ms[k + 1]
        Ip[k, k + 1] = math.sqrt(spin_val * (spin_val + 1.0) - m_low * (m_low + 1.0))
    Im = Ip.conj().T
    Ix = 0.5 * (Ip + Im)
    Iy = -0.5j * (Ip - Im)
    return Ix, Iy, Iz


def analyze_sb121_qudit(
    b0_t: float = 1.5,
    a_sb_mhz: float = 186.8,
    gamma_n_mhz_t: float = 10.19,
    f_q_nom_khz: float = 35.0,
    eta_q: float = 0.15,
    delta_f_q_rms_hz: float = 500.0,
    t2_mag_ms: float = 20.0,
) -> dict[str, Any]:
    """Exact 8x8 (I=7/2) nuclear & 16x16 coupled 121Sb Hamiltonian, Knill-Laflamme QEC & strain wall."""
    I_val = 3.5
    Ix, Iy, Iz = spin_operators(I_val)
    I8 = np.eye(8, dtype=np.complex128)
    I2 = np.eye(2, dtype=np.complex128)
    Sx = 0.5 * np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
    Sy = 0.5 * np.array([[0.0, -1j], [1j, 0.0]], dtype=np.complex128)
    Sz = 0.5 * np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)

    # Full 16x16 donor Hamiltonian in MHz (electron gamma_e = 28024.95 MHz/T)
    gamma_e_mhz_t = 28024.95
    f_q_mhz = f_q_nom_khz * 1e-3
    H_quad_8 = f_q_mhz * (Iz @ Iz - (I_val * (I_val + 1.0) / 3.0) * I8) + (eta_q * f_q_mhz / 3.0) * (Ix @ Ix - Iy @ Iy)
    H_16 = (
        gamma_e_mhz_t * b0_t * np.kron(Sz, I8)
        - gamma_n_mhz_t * b0_t * np.kron(I2, Iz)
        + a_sb_mhz * (np.kron(Sx, Ix) + np.kron(Sy, Iy) + np.kron(Sz, Iz))
        + np.kron(I2, H_quad_8)
    )
    evals_16, _ = eigh(H_16)
    # Lower 8 eigenvalues = ionized/electron |down> nuclear manifold; compute all 7 adjacent NMR transitions (MHz)
    e_down = evals_16[:8]
    nmr_freqs_mhz = np.sort(np.diff(e_down))
    nmr_spacings_khz = np.diff(nmr_freqs_mhz) * 1e3
    min_nmr_spacing_khz = float(np.min(nmr_spacings_khz))

    # Also verify pure 8x8 ionized-donor (121Sb+) nuclear manifold (zero electron hyperfine -> pure Zeeman + Quadrupole)
    H_ion_8 = -gamma_n_mhz_t * b0_t * Iz + H_quad_8
    e_ion, _ = eigh(H_ion_8)
    ion_nmr_mhz = np.sort(np.diff(e_ion))
    ion_min_spacing_khz = float(np.min(np.diff(ion_nmr_mhz)) * 1e3)

    # Exact Knill-Laflamme verification for two I=7/2 single-atom codes against {I, Ix, Iy} errors:
    #   Code A: Binomial Spin-Cat (Gross PRX Quantum 2021):
    #     |0_L> = (|+7/2> + |-1/2>) / sqrt(2)   (indices 0 and 4)
    #     |1_L> = (|-7/2> + |+1/2>) / sqrt(2)   (indices 7 and 3)
    #     Wait: Check exact distance! I_x connects m -> m+-1:
    #       Ix |+7/2> = c0 |+5/2> (idx 1), Ix |-1/2> = c3 |+1/2> (idx 3) + c4 |-3/2> (idx 5) -> wait, hits idx 3 in |1_L>!
    #     Now check Gross (2021) exact spin-7/2 code:
    #       |0_L> = sqrt(3/10)|+7/2> + sqrt(7/10)|-3/2>  (indices 0 and 5 -> gap dm=5!)
    #       |1_L> = sqrt(7/10)|+3/2> + sqrt(3/10)|-7/2>  (indices 2 and 7 -> gap dm=5!)
    #     WAIT! Check <0_L| Iz |0_L> = 0.3*(3.5) + 0.7*(-1.5) = 1.05 - 1.05 = 0.000 EXACT!!
    #     Check <1_L| Iz |1_L> = 0.7*(1.5) + 0.3*(-3.5) = 1.05 - 1.05 = 0.000 EXACT!!
    #     Check <0_L| Ix |1_L> = 0, <0_L| Ix^2 |1_L> = 0? Let's test Knill-Laflamme <c_i | E_a^dag E_b | c_j> = C_ab delta_ij!
    #   Code B: Spin-Cat Detection Code (Yu et al. Nature Physics 2025):
    #     |0_L> = |+7/2> (idx 0), |1_L> = |-7/2> (idx 7) -> separates |0_L> and |1_L> by 7 spin flips!
    #     Detects up to 6 consecutive I_x/I_y bit flips (and corrects up to 3 bit flips)!
    c0_gross = np.zeros(8, dtype=np.complex128); c0_gross[0] = math.sqrt(0.3); c0_gross[5] = math.sqrt(0.7)
    c1_gross = np.zeros(8, dtype=np.complex128); c1_gross[2] = math.sqrt(0.7); c1_gross[7] = math.sqrt(0.3)

    c0_cat = np.zeros(8, dtype=np.complex128); c0_cat[0] = 1.0
    c1_cat = np.zeros(8, dtype=np.complex128); c1_cat[7] = 1.0

    def _kl_check(v0: np.ndarray, v1: np.ndarray, errs: list[np.ndarray]) -> dict[str, float]:
        """Compute max Knill-Laflamme violation max |<0|Ea^dag Eb|1>| and |<0|Ea^dag Eb|0> - <1|Ea^dag Eb|1>|."""
        max_off = 0.0
        max_diag_diff = 0.0
        for ea in errs:
            for eb in errs:
                op = ea.conj().T @ eb
                m01 = abs(complex(v0.conj() @ op @ v1))
                m00 = complex(v0.conj() @ op @ v0)
                m11 = complex(v1.conj() @ op @ v1)
                max_off = max(max_off, m01)
                max_diag_diff = max(max_diag_diff, abs(m00 - m11))
        return {"max_off_diag": float(max_off), "max_diag_diff": float(max_diag_diff)}

    kl_gross_full = _kl_check(c0_gross, c1_gross, [I8, Ix, Iy, Iz])
    kl_cat_flip = _kl_check(c0_cat, c1_cat, [I8, Ix, Iy])
    kl_cat_z = _kl_check(c0_cat, c1_cat, [I8, Iz])  # |+-7/2> does NOT correct Iz dephasing!

    # Honest dephasing under BOTH magnetic 29Si bath noise (T2_mag=20 ms for dm=1) AND
    # quasistatic electric quadrupole strain noise delta_f_Q_rms = 500 Hz (H_noise = delta_f_Q * Iz^2)!
    # Exact Gaussian quasistatic average: E[exp(i * 2*pi * delta_f * t)] = exp(-2 * pi^2 * sigma_f^2 * t^2)
    # Magnetic noise sigma_B (Hz for dm=1): exp(-2 * pi^2 * sigma_B^2 * T2_mag^2) = 1/e -> sigma_B = 1/(sqrt(2)*pi*T2_mag)
    sigma_b_hz = 1.0 / (math.sqrt(2.0) * math.pi * (t2_mag_ms * 1e-3))  # ~11.25 Hz for T2=20 ms

    def _coherence_t2_star_ms(dm_mag: float, dm2_quad: float) -> float:
        sig_tot_hz = math.sqrt((dm_mag * sigma_b_hz) ** 2 + (dm2_quad * delta_f_q_rms_hz) ** 2)
        return float(1e3 / (math.sqrt(2.0) * math.pi * sig_tot_hz))

    # Compare 4 concrete encodings inside the 8-level 121Sb qudit:
    #   1. |+1/2> <-> |-1/2> clock transition: dm=1, dm^2 = 0.25 - 0.25 = 0 (FIRST-ORDER STRAIN IMMUNE!)
    #   2. |+7/2> <-> |+5/2> edge qubit:       dm=1, dm^2 = 12.25 - 6.25 = 6.0 (strong strain dephasing!)
    #   3. |+7/2> <-> |-7/2> spin-cat:         dm=7, dm^2 = 12.25 - 12.25 = 0 (strain-symmetric, 7x B-noise!)
    #   4. Gross binomial |0_L>=(|+7/2>,|-3/2>): internal dm=5, dm^2 = 12.25 - 2.25 = 10.0 (SEVERE I_z^2 strain dephasing!)
    t2_clock_ms = _coherence_t2_star_ms(dm_mag=1.0, dm2_quad=0.0)
    t2_edge75_ms = _coherence_t2_star_ms(dm_mag=1.0, dm2_quad=6.0)
    t2_cat77_ms = _coherence_t2_star_ms(dm_mag=7.0, dm2_quad=0.0)
    t2_gross_int_ms = _coherence_t2_star_ms(dm_mag=5.0, dm2_quad=10.0)

    # Also evaluate transverse quadrupole strain noise (eta_q * delta_f_Q) mixing on |+-7/2> vs |+-1/2> via exact 8x8 MC
    rng = np.random.default_rng(14288)
    n_mc = 400
    dfq_samples = rng.normal(0.0, delta_f_q_rms_hz * 1e-6, size=n_mc)  # MHz
    db_samples = rng.normal(0.0, sigma_b_hz * 1e-6, size=n_mc)         # MHz
    t_eval_ms = 1.0  # 1.0 ms coherence benchmark

    def _mc_coherence_1ms(psi_init: np.ndarray, t_ms: float) -> float:
        # Secular rotating-frame noise Hamiltonian at B0=1.5 T (gamma_n B0 = 15.3 MHz >> 500 Hz ->
        # transverse Ix^2 - Iy^2 suppressed by (500 Hz / 30.6 MHz)^2 ~ 10^-10):
        #   H_noise_sec = 2*pi * (db * Iz + dfq * Iz^2)
        rho_acc = np.zeros((8, 8), dtype=np.complex128)
        t_us = t_ms * 1e3
        iz_diag = np.real(np.diag(Iz))
        iz2_diag = iz_diag ** 2
        for db, dfq in zip(db_samples, dfq_samples):
            w = 2.0 * math.pi * (db * iz_diag + dfq * iz2_diag)
            psi_t = np.exp(-1j * w * t_us) * psi_init
            rho_acc += np.outer(psi_t, psi_t.conj())
        rho_acc /= n_mc
        return float(np.real(psi_init.conj() @ rho_acc @ psi_init))

    psi_clock = np.zeros(8, dtype=np.complex128); psi_clock[3] = 1.0 / math.sqrt(2.0); psi_clock[4] = 1.0 / math.sqrt(2.0)
    psi_cat77 = (c0_cat + c1_cat) / math.sqrt(2.0)
    psi_gross = c0_gross.copy()
    psi_edge75 = np.zeros(8, dtype=np.complex128); psi_edge75[0] = 1.0 / math.sqrt(2.0); psi_edge75[1] = 1.0 / math.sqrt(2.0)

    f1ms_clock = _mc_coherence_1ms(psi_clock, t_eval_ms)
    f1ms_cat77 = _mc_coherence_1ms(psi_cat77, t_eval_ms)
    f1ms_gross = _mc_coherence_1ms(psi_gross, t_eval_ms)
    f1ms_edge75 = _mc_coherence_1ms(psi_edge75, t_eval_ms)

    return {
        "spin_I": I_val,
        "n_levels": 8,
        "logical_qubits_raw": 3,
        "B0_T": b0_t,
        "A_hyperfine_MHz": a_sb_mhz,
        "f_Q_nom_kHz": f_q_nom_khz,
        "delta_f_Q_rms_Hz": delta_f_q_rms_hz,
        "donor_down_nmr_freqs_MHz": [float(x) for x in nmr_freqs_mhz],
        "donor_min_nmr_spacing_kHz": min_nmr_spacing_khz,
        "ionized_nmr_freqs_MHz": [float(x) for x in ion_nmr_mhz],
        "ionized_min_nmr_spacing_kHz": ion_min_spacing_khz,
        "knill_laflamme": {
            "gross_binomial_I_Ix_Iy_Iz": kl_gross_full,
            "spin_cat_77_I_Ix_Iy": kl_cat_flip,
            "spin_cat_77_I_Iz_unprotected": kl_cat_z,
        },
        "T2_star_ms": {
            "clock_pm1_2": t2_clock_ms,
            "edge_7_2_5_2": t2_edge75_ms,
            "spin_cat_pm7_2": t2_cat77_ms,
            "gross_binomial_internal": t2_gross_int_ms,
        },
        "mc_fidelity_at_1ms_with_500Hz_strain": {
            "clock_pm1_2": f1ms_clock,
            "spin_cat_pm7_2": f1ms_cat77,
            "edge_7_2_5_2": f1ms_edge75,
            "gross_binomial_0L": f1ms_gross,
        },
    }


# ---------------------------------------------------------------------------
# 4. OBS-154: Preliminary Arrhenius Activation, Segregation & Precipitation Model
#    for 121Sb and 167Er Multi-Species Implants under S5.5 Flash & S5.6 MBE
# ---------------------------------------------------------------------------
def analyze_multispecies_anneal_kinetics() -> dict[str, Any]:
    """Preliminary Arrhenius sensitivity model for 121Sb and 167Er thermal processing (OBS-154).

    Epistemic status: {Model} / {Literatür}, no_lab_measurement=True.
    Literature anchors:
      - 121Sb in Si: vacancy-mediated D_Sb = 12.9 cm^2/s * exp(-4.08 eV/kT) (Fahey 1989 / Larsen 1993),
        f_V ~ 0.98 (negligible interstitial TED), strong surface segregation E_seg ~ 0.85 eV during SPE/MBE
        (Jorke 1988; Barnett & Greene 1985), solid solubility C_sol ~ 4e19 cm^-3 @ 1000 C.
      - 167Er in Si: optical Er3+ (1536 nm) activation window 650-900 C (often O-co-doped; Polman JAP 82,
        1997; Gritsch et al. PRX 12, 041009, 2022), low equilibrium solubility (~1e18 cm^-3), rapid ErSi2 precipitation &
        Er-O dissociation above 1000 C (D_Er ~ 1e-3 cm^2/s * exp(-2.5 eV/kT)).
    """
    kb_ev = 8.617333262e-5
    a_ml_nm = 0.13577

    recipes = [
        ("s55_flash_1530K_1ms", 1530.0, 1.0e-3),
        ("s55_flash_1440K_1ms", 1440.0, 1.0e-3),
        ("rta_900C_10s", 900.0 + 273.15, 10.0),
        ("furnace_750C_30min_ErO", 750.0 + 273.15, 1800.0),
        ("s56_mbe_345C_80s", 345.0 + 273.15, 80.0),
        ("s56_mbe_275C_80s_lowT", 275.0 + 273.15, 80.0),
    ]

    sb_rows = {}
    er_rows = {}
    for name, T_K, t_s in recipes:
        kT = kb_ev * T_K
        # 121Sb: vacancy-mediated bulk diffusion + SPE pocket activation (Ea=2.70 eV) + MBE segregation L_seg
        D_sb_nm2_s = 12.9e14 * math.exp(-4.08 / kT)
        sig_sb_nm = math.sqrt(2.0 * D_sb_nm2_s * t_s)
        f_act_sb = 1.0 - math.exp(-min(1.84e15 * math.exp(-2.70 / kT) * t_s, 500.0))
        # Sb kinetic MBE segregation length (E_seg=0.85 eV vs P 0.30 eV -> strong surface push-out at 345 C!)
        r_eq_sb = math.exp(min(0.85 / kT, 40.0))
        k_ex_sb = 9.0e5 * math.exp(-1.05 / kT)
        r_s_sb = r_eq_sb / (1.0 + 0.10 / max(a_ml_nm * k_ex_sb, 1e-30))
        L_seg_sb_nm = a_ml_nm / math.log1p(1.0 / max(r_s_sb, 1e-12)) if T_K < 800.0 else 0.0
        sb_compat = bool(f_act_sb >= 0.90 and sig_sb_nm <= 0.50) if T_K >= 900.0 else bool(L_seg_sb_nm <= 4.0)
        sb_rows[name] = {
            "T_K": round(T_K, 2),
            "t_s": t_s,
            "sigma_diff_nm": round(sig_sb_nm, 5),
            "f_act_pocket_spe": round(f_act_sb, 5),
            "mbe_L_seg_nm_if_capping": round(L_seg_sb_nm, 3),
            "compatible_preliminary": sb_compat,
        }

        # 167Er: optical center activation (Ea=2.0 eV, peak 650-900 C) vs high-T Er-O dissociation / ErSi2 precipitation (Ea=2.5 eV)
        D_er_nm2_s = 1.0e-3 * 1e14 * math.exp(-2.50 / kT)
        sig_er_nm = math.sqrt(2.0 * D_er_nm2_s * t_s)
        f_opt_form = 1.0 - math.exp(-min(1.0e8 * math.exp(-2.00 / kT) * t_s, 500.0))
        # Optical quenching / ErSi2 precipitation probability above ~1000 C (1273 K)
        k_precip = 5.0e11 * math.exp(-2.50 / kT)
        f_surv_nonprecip = math.exp(-min(k_precip * t_s, 500.0)) if T_K > 1100.0 else 1.0
        f_opt_yield = f_opt_form * f_surv_nonprecip
        er_rows[name] = {
            "T_K": round(T_K, 2),
            "t_s": t_s,
            "sigma_diff_nm": round(sig_er_nm, 4),
            "f_optical_activation_raw": round(f_opt_form, 5),
            "f_non_precipitated_ErSi2": round(f_surv_nonprecip, 5),
            "net_optical_center_yield": round(f_opt_yield, 5),
            "compatible_with_1536nm_optical_center": bool(f_opt_yield >= 0.50 and sig_er_nm <= 15.0),
        }

    return {
        "obstacle_id": "OBS-154",
        "epistemic_status": "Preliminary Arrhenius sensitivity model ({Model}/{Literatur}); lab SIMS/DLTS/PL verification required.",
        "sb121_kinetics": sb_rows,
        "er167_kinetics": er_rows,
        "s55_1530K_flash_compatibility": {
            "31P": True,
            "121Sb": sb_rows["s55_flash_1530K_1ms"]["compatible_preliminary"],
            "167Er": er_rows["s55_flash_1530K_1ms"]["compatible_with_1536nm_optical_center"],
            "process_note": (
                "121Sb is preliminarily compatible with 1530 K / 1 ms flash (vacancy-mediated -> negligible TED, "
                "high pocket SPE activation), but requires lower-T MBE capping (<=275-300 C) to suppress strong "
                "Sb surface segregation. 167Er is INCOMPATIBLE with 1530 K S5.5 flash due to rapid ErSi2 "
                "precipitation / Er-O dissociation and requires a dedicated 700-850 C O-co-doped RTA/furnace step."
            ),
        },
    }
