"""Exp129 (H147): First-Principles VOKL-6 (6-Valley Valley-Orbit Central-Cell Kohn-Luttinger)
Hyperfine Theory in Silicon.

Implements:
  1. Exact 6-valley coupled anisotropic effective-mass + Ning-Sah / Pantelides-Sah short-range
     central-cell Hamiltonian H_6v solved in a multi-scale 3D Gaussian-lobe variational basis
     (120 coupled states across +-x, +-y, +-z valleys; closed-form analytic overlap, kinetic,
     Coulomb, and intervalley Gaussian matrix elements).
  2. Strict zero-overfitting calibration exclusively to 31P spectral invariants:
       - E(1s A1) = -45.59 meV
       - Delta_VO(1s T2 - 1s A1) = 11.70 meV  (E(1s T2) = -33.89 meV)
       - Delta_VO(1s E  - 1s A1) = 13.01 meV  (E(1s E)  = -32.58 meV)
       - A_P(0)   = 117.53 MHz  (with Morton & Preston 1978 3s atomic core ratio
         eta_P / eta_Si = 7.252 / 5.115 = 1.4178; sensitivities at eta_P=eta_Si=186 and
         Assali et al. 2011 eta_Si=178 also computed).
     ZERO 29Si ENDOR shell ratios enter the calibration.
  3. Full 3D k-space Cohen-Bergstresser 145-PW empirical pseudopotential (EPM) conduction-band
     Bloch wavepacket convolution over the exact boundary-fitted 1st-BZ +z valley sector
     (zero free parameters), capturing off-Delta-axis Delta_1 - Delta_2' mixing, tetrahedral
     sublattice-B Bloch interference, and Lax-Birman intervalley umklapp selection rules.
  4. Full 3D hyperfine tensor A(R) = A_iso(R) I_3 + T_dip(R) across all 45,214 diamond lattice
     sites (R <= 6.0 nm), including both extended-wavefunction multipole dipolar tensor and
     point-dipole comparison.
  5. Out-of-sample benchmark against audited 29Si ENDOR & LMTO-GF shell ratios with complete
     physics ablation (Legacy KL -> Bare EMT -> VOKL-6 Envelope -> Full VOKL-6 + k-Bloch).

Epistemic status: no_lab_measurement=True ({Literatür}/{Analitik}/{Model}/{Sayısal-Simülasyon}).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares
from scipy.special import roots_legendre

# ---------------------------------------------------------------------------
# CODATA Physical Constants & Fixed Silicon Literature Parameters
# ---------------------------------------------------------------------------
HBAR_JS = 1.054571817e-34
M0_KG = 9.1093837015e-31
E_CHARGE_C = 1.602176634e-19
EPS0_FM = 8.8541878128e-12
MU0_NA2 = 4.0e-7 * math.pi
MUB_JT = 9.2740100783e-24

# Derived atomic/nanoscale constants (meV, nm)
HBAR2_OVER_2M0_MEV_NM2 = (HBAR_JS ** 2) / (2.0 * M0_KG * E_CHARGE_C * 1e-3 * 1e-18)
KC_VAC_MEV_NM = (E_CHARGE_C ** 2) / (4.0 * math.pi * EPS0_FM * E_CHARGE_C * 1e-3 * 1e-9)

# Silicon crystal & conduction band constants (fixed literature values)
A_SI_NM = 0.5431
A_SI_BOHR = 10.2631
K0_FRAC = 0.85
K0_INV_NM = K0_FRAC * 2.0 * math.pi / A_SI_NM
M_T = 0.1905
M_L = 0.9163
EPS_SI_4K = 11.4

# Spin, hyperfine & atomic core constants
G_E = 2.0023
GAMMA_31P_HZ_PER_T = 17.235e6
GAMMA_29SI_HZ_PER_T = 8.465e6
ETA_SI_KL = 186.0                         # Shulman & Wyluda (1956) / Kohn & Luttinger (1955)
ETA_SI_ASSALI = 178.0                     # Assali et al. PRB 83, 165301 (2011)
MORTON_PRESTON_PSI3S_SI = 5.115           # Morton & Preston JMR 30, 577 (1978) Table 1 (a.u.^-3)
MORTON_PRESTON_PSI3S_P = 7.252            # Morton & Preston JMR 30, 577 (1978) Table 1 (a.u.^-3)
P_TO_SI_CORE_RATIO = MORTON_PRESTON_PSI3S_P / MORTON_PRESTON_PSI3S_SI  # 1.41779
ETA_P_PHYSICAL = ETA_SI_KL * P_TO_SI_CORE_RATIO                        # 263.709

# Fermi-contact & dipolar prefactors in Hz * nm^3
FC_PREF_31P_HZ_NM3 = (2.0 / 3.0) * MU0_NA2 * G_E * MUB_JT * GAMMA_31P_HZ_PER_T * 1e27
FC_PREF_29SI_HZ_NM3 = (2.0 / 3.0) * MU0_NA2 * G_E * MUB_JT * GAMMA_29SI_HZ_PER_T * 1e27
DIP_PREF_29SI_HZ_NM3 = (MU0_NA2 / (4.0 * math.pi)) * G_E * MUB_JT * GAMMA_29SI_HZ_PER_T * 1e27

# Experimental 31P spectral calibration invariants (Ramdas & Rodriguez 1981; Mayur et al. 1993; Feher 1959)
TARGET_E_A1_MEV = -45.59
TARGET_E_T2_MEV = -33.89
TARGET_E_E_MEV = -32.58
TARGET_DVO_T2_MEV = 11.70
TARGET_DVO_E_MEV = 13.01
TARGET_AP0_MHZ = 117.53

# Audited out-of-sample 29Si ENDOR & LMTO-GF shell benchmarks (Exp56/60/69/75, Ma et al. 2022 Fig. 3)
REF_SHELL_COORD = np.array([0, 0, 4], dtype=int)
REF_SHELL_NM = REF_SHELL_COORD * (A_SI_NM / 4.0)
REF_A_REPO_HZ = 2.981e6   # A_repo = a_HM / 2 (Hale & Mieher a_HM = 5.962 MHz)
REF_A_HM_MHZ = 5.962

BENCHMARK_SHELLS: dict[str, dict[str, Any]] = {
    "(1,1,1)": {"coord": (1, 1, 1), "target_ratio": 0.092, "kind": "experiment"},
    "(3,3,1)": {"coord": (3, 3, 1), "target_ratio": 0.293, "kind": "experiment"},
    "(2,2,0)": {"coord": (2, 2, 0), "target_ratio": 0.050, "kind": "LMTO-GF"},
    "(1,1,-3)": {"coord": (1, 1, -3), "target_ratio": 0.030, "kind": "LMTO-GF"},
}

FORWARD_SHELLS: dict[str, tuple[int, int, int]] = {
    "(0,0,4)": (0, 0, 4),
    "(1,1,1)": (1, 1, 1),
    "(2,2,0)": (2, 2, 0),
    "(1,1,-3)": (1, 1, -3),
    "(3,3,1)": (3, 3, 1),
    "(2,2,2)": (2, 2, 2),
    "(4,4,0)": (4, 4, 0),
    "(4,0,4)": (4, 0, 4),
    "(3,3,3)": (3, 3, 3),
    "(0,0,8)": (0, 0, 8),
}


# ---------------------------------------------------------------------------
# 1. Anisotropic 3D Gaussian-Lobe Basis & 6-Valley Central-Cell Hamiltonian
# ---------------------------------------------------------------------------
def build_gaussian_basis() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (alpha, beta, norm) arrays for N_b=36 multi-scale 3D Gaussian basis functions.

    Three-tier basis resolving both the spherical central-cell cusp and the exact anisotropic
    Whittaker asymptotic tail (m_l / m_t = 4.810 -> (a_perp / a_par)^2 = 4.81):
      - 14 high-anisotropy pancake Gaussians (s in [0.12, 24.0] nm, beta/alpha = 4.810)
      - 12 intermediate-anisotropy Gaussians (s in [0.15, 18.0] nm, beta/alpha = 2.80)
      - 10 isotropic spherical core/mid Gaussians (s in [0.03, 3.0] nm, beta = alpha)
    """
    s_mass = np.geomspace(0.12, 24.0, 14)
    s_mid = np.geomspace(0.15, 18.0, 12)
    s_iso = np.geomspace(0.03, 3.0, 10)

    alpha = np.concatenate([1.0 / (s_mass ** 2), 1.0 / (s_mid ** 2), 1.0 / (s_iso ** 2)])
    beta = np.concatenate([(M_L / M_T) / (s_mass ** 2), 2.80 / (s_mid ** 2), 1.0 / (s_iso ** 2)])
    norm = np.sqrt((2.0 * alpha / math.pi)) * ((2.0 * beta / math.pi) ** 0.25)
    return alpha, beta, norm


def _aniso_coulomb_integral(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Exact analytic integral int d^3r exp(-p*(x^2+y^2) - q*z^2) / r."""
    out = np.empty_like(p, dtype=np.float64)
    diff = q - p
    tol = 1e-12 * np.maximum(p, q)
    m_gt = diff > tol
    m_lt = diff < -tol
    m_eq = ~(m_gt | m_lt)
    if np.any(m_gt):
        d = diff[m_gt]
        pm = p[m_gt]
        out[m_gt] = (2.0 * math.pi / np.sqrt(pm * d)) * np.arctan(np.sqrt(d / pm))
    if np.any(m_lt):
        d = -diff[m_lt]
        pm = p[m_lt]
        out[m_lt] = (2.0 * math.pi / np.sqrt(pm * d)) * np.arctanh(np.sqrt(d / pm))
    if np.any(m_eq):
        out[m_eq] = 2.0 * math.pi / p[m_eq]
    return out


@dataclass
class ValleyBlocks:
    alpha: np.ndarray
    beta: np.ndarray
    norm: np.ndarray
    S1: np.ndarray
    T1: np.ndarray
    Vcoul1: np.ndarray


def precompute_single_valley_blocks() -> ValleyBlocks:
    """Precompute exact single-valley overlap, anisotropic kinetic, and screened Coulomb matrices."""
    alpha, beta, norm = build_gaussian_basis()
    nn = np.outer(norm, norm)
    p = alpha[:, None] + alpha[None, :]
    q = beta[:, None] + beta[None, :]

    S1 = nn * (math.pi ** 1.5) / (p * np.sqrt(q))
    kin_pref = (
        (HBAR2_OVER_2M0_MEV_NM2 / M_T) * (4.0 * np.outer(alpha, alpha) / p)
        + (HBAR2_OVER_2M0_MEV_NM2 / M_L) * (2.0 * np.outer(beta, beta) / q)
    )
    T1 = kin_pref * S1

    coul_int = _aniso_coulomb_integral(p, q)
    Vcoul1 = -(KC_VAC_MEV_NM / EPS_SI_4K) * nn * coul_int
    return ValleyBlocks(alpha=alpha, beta=beta, norm=norm, S1=S1, T1=T1, Vcoul1=Vcoul1)


def solve_bare_emt(blocks: ValleyBlocks) -> dict[str, Any]:
    """Solve single-valley bare anisotropic EMT (V_cc = 0, macroscopic eps_Si = 11.4)."""
    H_emt = blocks.T1 + blocks.Vcoul1
    evals, evecs = eigh(H_emt, blocks.S1)
    c0 = evecs[:, 0]
    if float(np.dot(c0, blocks.norm)) < 0.0:
        c0 = -c0
    f0 = float(np.dot(c0, blocks.norm))
    return {
        "E_emt_1s_meV": float(evals[0]),
        "E_emt_2s_meV": float(evals[1]),
        "F_emt_0_nm_m1p5": f0,
        "coeffs": c0,
    }


def _gaussian_cc_blocks(blocks: ValleyBlocks, r_c: float) -> tuple[np.ndarray, np.ndarray]:
    """Exact analytic <g_mu,i | exp(-r^2 / (2 r_c^2)) | g_nu,j> for same-axis and orthogonal valleys."""
    lam = 0.5 / (r_c ** 2)
    alpha, beta, norm = blocks.alpha, blocks.beta, blocks.norm
    nn = np.outer(norm, norm)

    p_same = alpha[:, None] + alpha[None, :] + lam
    q_same = beta[:, None] + beta[None, :] + lam
    G_same = nn * (math.pi ** 1.5) / (p_same * np.sqrt(q_same))

    ex = beta[:, None] + alpha[None, :] + lam
    ey = alpha[:, None] + alpha[None, :] + lam
    ez = alpha[:, None] + beta[None, :] + lam
    G_orth = nn * (math.pi ** 1.5) / np.sqrt(ex * ey * ez)
    return G_same, G_orth


def assemble_6valley_matrices(
    blocks: ValleyBlocks,
    r_c: float,
    u_intra: float,
    u_g: float,
    u_f: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Assemble full 6*N_b x 6*N_b coupled 6-valley central-cell Hamiltonian H_6v and overlap S_6v.

    Valley ordering: 0:+x, 1:-x, 2:+y, 3:-y, 4:+z, 5:-z.
    Short-range Ning-Sah / Gamble central-cell kernel exp(-r^2 / (2 r_c^2)) incorporates both
    short-range dielectric deshielding and chemical core potential with Td valley-orbit couplings
    (U_intra diagonal, U_g opposite-valley g-process, U_f orthogonal-valley f-process).
    """
    nb = len(blocks.alpha)
    G_same, G_orth = _gaussian_cc_blocks(blocks, r_c)

    H_diag = blocks.T1 + blocks.Vcoul1 - u_intra * G_same
    H_g = -u_g * G_same
    H_f = -u_f * G_orth

    H6 = np.zeros((6 * nb, 6 * nb), dtype=np.float64)
    S6 = np.zeros((6 * nb, 6 * nb), dtype=np.float64)

    for mu in range(6):
        s_mu = slice(mu * nb, (mu + 1) * nb)
        S6[s_mu, s_mu] = blocks.S1
        H6[s_mu, s_mu] = H_diag
        axis_mu = mu // 2
        for nu in range(6):
            if nu == mu:
                continue
            s_nu = slice(nu * nb, (nu + 1) * nb)
            axis_nu = nu // 2
            H6[s_mu, s_nu] = H_g if axis_mu == axis_nu else H_f

    return H6, S6


def solve_6valley(
    blocks: ValleyBlocks,
    r_c: float,
    u_intra: float,
    u_g: float,
    u_f: float,
    eta_p: float = ETA_P_PHYSICAL,
) -> dict[str, Any]:
    """Diagonalize full 120x120 6-valley central-cell Hamiltonian H_6v and extract Td multiplets."""
    nb = len(blocks.alpha)
    H6, S6 = assemble_6valley_matrices(blocks, r_c, u_intra, u_g, u_f)
    evals, evecs = eigh(H6, S6)

    e6 = evals[:6]
    v6 = evecs[:, :6]

    a1_idx = None
    t2_idxs: list[int] = []
    e_idxs: list[int] = []
    for k in range(6):
        vec = v6[:, k].reshape(6, nb)
        amps = vec @ blocks.norm
        pair_diffs = np.array([amps[0] - amps[1], amps[2] - amps[3], amps[4] - amps[5]])
        if np.linalg.norm(pair_diffs) > 0.5 * np.linalg.norm(amps):
            t2_idxs.append(k)
        elif abs(np.sum(amps)) > 0.5 * np.linalg.norm(amps):
            a1_idx = k
        else:
            e_idxs.append(k)

    if a1_idx is None or len(t2_idxs) != 3 or len(e_idxs) != 2:
        a1_idx = 0
        t2_idxs = [1, 2, 3]
        e_idxs = [4, 5]

    c_a1_full = v6[:, a1_idx].reshape(6, nb).copy()
    if float(np.sum(c_a1_full @ blocks.norm)) < 0.0:
        c_a1_full = -c_a1_full

    norm_sq = float(v6[:, a1_idx] @ S6 @ v6[:, a1_idx])
    valley_norms = [float(c_a1_full[mu] @ blocks.S1 @ c_a1_full[mu]) for mu in range(6)]
    valley_spread = float(np.max(valley_norms) - np.min(valley_norms))

    psi_a1_0 = float(np.sum(c_a1_full @ blocks.norm))
    psi_a1_0_sq = psi_a1_0 ** 2
    a_p0_mhz = (FC_PREF_31P_HZ_NM3 * eta_p * psi_a1_0_sq) * 1e-6

    c_1v = c_a1_full[4] * math.sqrt(6.0)
    if float(np.dot(c_1v, blocks.norm)) < 0.0:
        c_1v = -c_1v

    e_a1 = float(e6[a1_idx])
    e_t2_vals = [float(e6[i]) for i in t2_idxs]
    e_e_vals = [float(e6[i]) for i in e_idxs]

    return {
        "E_1s_A1_meV": e_a1,
        "E_1s_T2_meV": float(np.mean(e_t2_vals)),
        "E_1s_E_meV": float(np.mean(e_e_vals)),
        "T2_degeneracy_spread_meV": float(np.max(e_t2_vals) - np.min(e_t2_vals)),
        "E_degeneracy_spread_meV": float(np.max(e_e_vals) - np.min(e_e_vals)),
        "Delta_VO_T2_meV": float(np.mean(e_t2_vals) - e_a1),
        "Delta_VO_E_meV": float(np.mean(e_e_vals) - e_a1),
        "A_P_0_MHz": float(a_p0_mhz),
        "Psi_A1_0_sq_nm_m3": float(psi_a1_0_sq),
        "norm_sq": norm_sq,
        "valley_weight_spread": valley_spread,
        "c_1v": c_1v,
        "e_manifold_meV": [float(x) for x in e6],
    }


def calibrate_vokl6_to_31p_invariants(blocks: ValleyBlocks, eta_p: float = ETA_P_PHYSICAL) -> dict[str, Any]:
    """Calibrate (r_c, U_intra, U_g, U_f) EXCLUSIVELY to the four 31P spectral invariants.

    ZERO 29Si ENDOR shells are referenced or used anywhere in this calibration.
    """
    def residuals(x: np.ndarray) -> np.ndarray:
        r_c, u_intra, u_g, u_f = float(x[0]), float(x[1]), float(x[2]), float(x[3])
        sol = solve_6valley(blocks, r_c, u_intra, u_g, u_f, eta_p=eta_p)
        return np.array([
            (sol["E_1s_A1_meV"] - TARGET_E_A1_MEV) / 0.01,
            (sol["Delta_VO_T2_meV"] - TARGET_DVO_T2_MEV) / 0.01,
            (sol["Delta_VO_E_meV"] - TARGET_DVO_E_MEV) / 0.01,
            (sol["A_P_0_MHz"] - TARGET_AP0_MHZ) / 0.10,
        ], dtype=np.float64)

    x0 = np.array([0.17, 900.0, 150.0, 320.0], dtype=np.float64)
    bounds = (
        np.array([0.05, 0.0, 0.0, 0.0], dtype=np.float64),
        np.array([0.35, 25000.0, 10000.0, 10000.0], dtype=np.float64),
    )
    res = least_squares(residuals, x0, bounds=bounds, xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=400)
    r_c, u_intra, u_g, u_f = [float(v) for v in res.x]
    sol = solve_6valley(blocks, r_c, u_intra, u_g, u_f, eta_p=eta_p)
    sol["params"] = {
        "r_c_nm": r_c,
        "U_intra_meV": u_intra,
        "U_g_meV": u_g,
        "U_f_meV": u_f,
        "eta_P_used": float(eta_p),
        "p_to_si_core_ratio": float(eta_p / ETA_SI_KL),
    }
    sol["optimizer_success"] = bool(res.success)
    sol["optimizer_cost"] = float(res.cost)
    return sol


# ---------------------------------------------------------------------------
# 2. Envelope Evaluation, Radial Profiles & Extended-Dipole Enclosed Charge
# ---------------------------------------------------------------------------
def eval_1v_envelope_realspace(
    r_nm: np.ndarray,
    blocks: ValleyBlocks,
    c_1v: np.ndarray,
    axis: int,
) -> np.ndarray:
    """Evaluate single-valley normalized envelope F_axis(r) at points r_nm [N, 3]."""
    r = np.atleast_2d(np.asarray(r_nm, dtype=np.float64))
    r2_tot = np.sum(r * r, axis=1)
    r_par2 = r[:, axis] ** 2
    r_perp2 = np.maximum(0.0, r2_tot - r_par2)
    weights = c_1v * blocks.norm
    expo = np.exp(-r_perp2[:, None] * blocks.alpha[None, :] - r_par2[:, None] * blocks.beta[None, :])
    return expo @ weights


def compute_effective_radii(blocks: ValleyBlocks, c_1v: np.ndarray) -> dict[str, float]:
    """Compute RMS radii and asymptotic 1/e decay lengths of the 1-valley envelope."""
    z_grid = np.linspace(0.0, 8.0, 801)
    pts_perp = np.column_stack([z_grid, np.zeros_like(z_grid), np.zeros_like(z_grid)])
    pts_par = np.column_stack([np.zeros_like(z_grid), np.zeros_like(z_grid), z_grid])
    f_perp = eval_1v_envelope_realspace(pts_perp, blocks, c_1v, axis=2)
    f_par = eval_1v_envelope_realspace(pts_par, blocks, c_1v, axis=2)

    mask = (z_grid >= 1.5) & (z_grid <= 4.5)
    slope_perp = float(np.polyfit(z_grid[mask], np.log(np.maximum(np.abs(f_perp[mask]), 1e-300)), 1)[0])
    slope_par = float(np.polyfit(z_grid[mask], np.log(np.maximum(np.abs(f_par[mask]), 1e-300)), 1)[0])

    alpha, beta = blocks.alpha, blocks.beta
    p = alpha[:, None] + alpha[None, :]
    q = beta[:, None] + beta[None, :]
    S1 = blocks.S1
    rho2_mean = float(c_1v @ (S1 / p) @ c_1v)
    z2_mean = float(c_1v @ (S1 / (2.0 * q)) @ c_1v)
    r_rms = math.sqrt(rho2_mean + z2_mean)
    return {
        "a_perp_tail_nm": float(-1.0 / slope_perp),
        "a_par_tail_nm": float(-1.0 / slope_par),
        "anisotropy_tail": float(slope_par / slope_perp),
        "r_rms_nm": float(r_rms),
        "rho_rms_nm": float(math.sqrt(rho2_mean)),
        "z_rms_nm": float(math.sqrt(z2_mean)),
    }


def enclosed_charge_fraction(r_norm_nm: np.ndarray, blocks: ValleyBlocks, c_1v: np.ndarray) -> np.ndarray:
    """Compute spherically averaged enclosed probability Q_enc(R) = int_{r<R} |F_1v(r)|^2 d^3r."""
    r_arr = np.asarray(r_norm_nm, dtype=np.float64)
    r_grid = np.linspace(0.0, 7.0, 1401)
    mu_x, mu_w = roots_legendre(12)
    mu = 0.5 * (mu_x + 1.0)
    mw = 0.5 * mu_w

    alpha, beta, norm = blocks.alpha, blocks.beta, blocks.norm
    weights = c_1v * norm
    ang_avg = np.zeros_like(r_grid)
    for j in range(len(mu)):
        rp2 = (r_grid ** 2) * (1.0 - mu[j] ** 2)
        rz2 = (r_grid ** 2) * (mu[j] ** 2)
        fval = np.exp(-rp2[:, None] * alpha[None, :] - rz2[:, None] * beta[None, :]) @ weights
        ang_avg += mw[j] * (fval ** 2)

    radial_pdf = 4.0 * math.pi * (r_grid ** 2) * ang_avg
    dr = r_grid[1] - r_grid[0]
    cdf = np.concatenate([[0.0], np.cumsum(0.5 * (radial_pdf[:-1] + radial_pdf[1:]) * dr)])
    cdf = np.clip(cdf, 0.0, 1.0)
    return np.interp(r_arr, r_grid, cdf)


# ---------------------------------------------------------------------------
# 3. Cohen-Bergstresser 145-PW EPM & Full 3D k-Space Bloch Wavepacket
# ---------------------------------------------------------------------------
def _build_cb_epm() -> tuple[np.ndarray, np.ndarray]:
    """Build exact Cohen-Bergstresser (1966) 145-PW EPM reciprocal lattice & symmetric potential.

    Origin at bond center:
      Atom A (donor site) at r_A = -t = -(a/8)(1,1,1)
      Atom B (1st NN +111) at r_B = +t = +(a/8)(1,1,1)
      Vector r_B - r_A = +2t = +(a/4)(1,1,1), matching ap25_register.SITES exactly.
    """
    gs = []
    for h in range(-4, 5):
        for k in range(-4, 5):
            for l in range(-4, 5):
                if (h % 2 == k % 2 == l % 2) and (h * h + k * k + l * l <= 28):
                    gs.append((h, k, l))
    G = np.array(gs, dtype=np.float64)
    dG = G[:, None, :] - G[None, :, :]
    d2 = np.rint(np.sum(dG ** 2, axis=-1)).astype(int)
    vs_ry = {3: -0.21, 8: 0.04, 11: 0.08}
    Vt = np.zeros((len(G), len(G)), dtype=np.float64)
    for key, val in vs_ry.items():
        Vt[d2 == key] = val * 0.5
    cosf = np.cos(np.sum(dG, axis=-1) * (2.0 * math.pi / 8.0))
    V = Vt * cosf
    return G, V


_EPM_G, _EPM_V = _build_cb_epm()
_EPM_PHASE_A = np.exp(-2j * math.pi * np.sum(_EPM_G, axis=1) / 8.0)  # r_A = -t
_EPM_PHASE_B = np.exp(+2j * math.pi * np.sum(_EPM_G, axis=1) / 8.0)  # r_B = +t
_EPM_KIN_PREF = 0.5 * ((2.0 * math.pi / A_SI_BOHR) ** 2)
_HA_TO_EV = 27.211386245988


def epm_bloch_state(k_frac: np.ndarray, ref_vec: np.ndarray | None = None) -> tuple[float, np.ndarray, complex, complex]:
    """Compute CB-EPM conduction band energy (Ha), eigenvector, u(r_A), u(r_B) at k_frac (in 2pi/a)."""
    kg = _EPM_G + np.asarray(k_frac, dtype=np.float64)[None, :]
    kin = _EPM_KIN_PREF * np.sum(kg * kg, axis=1)
    H = _EPM_V.copy()
    H[np.diag_indices_from(H)] += kin
    w, c = eigh(H)

    if ref_vec is None:
        idx = 4
    else:
        overlaps = np.abs(ref_vec.conj() @ c[:, 4:7])
        idx = 4 + int(np.argmax(overlaps))

    vec = c[:, idx].astype(np.complex128)
    ua = complex(np.dot(vec, _EPM_PHASE_A))
    ub = complex(np.dot(vec, _EPM_PHASE_B))
    if abs(ua) > 1e-12:
        ph = ua / abs(ua)
        vec = vec / ph
        ua = ua / ph
        ub = ub / ph
    return float(w[idx]), vec, ua, ub


def _shindo_nara_overlap_top(v1: np.ndarray, v2: np.ndarray, k1: np.ndarray, k2: np.ndarray) -> list[dict[str, Any]]:
    """Top reciprocal-lattice Fourier weights C_{12}(dG) of u_1^*(r) u_2(r) for intervalley selection rules."""
    gmap: dict[tuple[int, int, int], complex] = {}
    nz1 = np.where(np.abs(v1) > 1e-4)[0]
    nz2 = np.where(np.abs(v2) > 1e-4)[0]
    for i in nz1:
        for j in nz2:
            dG = tuple(int(round(x)) for x in (_EPM_G[j] - _EPM_G[i]))
            gmap[dG] = gmap.get(dG, 0.0j) + v1[i].conj() * v2[j]
    ranked = sorted(gmap.items(), key=lambda kv: -abs(kv[1]))[:5]
    out = []
    for dG, val in ranked:
        dk_tot = float(np.linalg.norm(k2 - k1 + np.array(dG, dtype=float)))
        out.append({"dG": list(dG), "dk_plus_dG_2pi_a": dk_tot, "C_abs": float(abs(val)), "C_re": float(val.real)})
    return out


def verify_epm_band_structure() -> dict[str, Any]:
    """Verify CB-EPM valley minimum, indirect gap, off-axis Delta_1-Delta_2' phase & Lax-Birman rules."""
    w_gamma, _ = eigh(_EPM_V + np.diag(_EPM_KIN_PREF * np.sum(_EPM_G ** 2, axis=1)))
    e_vbm = float(w_gamma[3])
    ks = np.linspace(0.75, 0.95, 41)
    ecbs = [epm_bloch_state(np.array([0.0, 0.0, kf]))[0] for kf in ks]
    imin = int(np.argmin(ecbs))
    k_star = float(ks[imin])
    gap_ev = (ecbs[imin] - e_vbm) * _HA_TO_EV

    _, v_pz, ua0, ub0 = epm_bloch_state(np.array([0.0, 0.0, K0_FRAC]))
    _, v_mz, _, _ = epm_bloch_state(np.array([0.0, 0.0, -K0_FRAC]))
    _, v_px, _, _ = epm_bloch_state(np.array([K0_FRAC, 0.0, 0.0]))
    q_on_axis = ub0 / ua0

    _, _, ua_off, ub_off = epm_bloch_state(np.array([0.15, 0.15, K0_FRAC]), ref_vec=v_pz)
    q_off_axis = ub_off / ua_off
    _, _, ua_opp, ub_opp = epm_bloch_state(np.array([0.15, -0.15, K0_FRAC]), ref_vec=v_pz)
    q_opp_axis = ub_opp / ua_opp

    # Check Lax-Birman forbidden g-process (0,0,2) umklapp weight
    g_top = _shindo_nara_overlap_top(v_pz, v_mz, np.array([0, 0, K0_FRAC]), np.array([0, 0, -K0_FRAC]))
    f_top = _shindo_nara_overlap_top(v_pz, v_px, np.array([0, 0, K0_FRAC]), np.array([K0_FRAC, 0, 0]))

    # Explicitly compute C_g(0,0,2)
    c_g_002 = 0.0j
    g_lookup = {tuple(int(round(x)) for x in _EPM_G[i]): i for i in range(len(_EPM_G))}
    for i in range(len(_EPM_G)):
        t = tuple(int(round(x)) for x in (_EPM_G[i] + np.array([0, 0, 2])))
        if t in g_lookup:
            c_g_002 += v_pz[i].conj() * v_mz[g_lookup[t]]

    return {
        "n_planewaves": int(len(_EPM_G)),
        "k_star_frac": k_star,
        "indirect_gap_eV": float(gap_ev),
        "uA_k0_abs": float(abs(ua0)),
        "q_on_axis": {"re": float(q_on_axis.real), "im": float(q_on_axis.imag)},
        "q_off_axis_0p15_0p15": {
            "re": float(q_off_axis.real),
            "im": float(q_off_axis.imag),
            "abs": float(abs(q_off_axis)),
            "arg_rad": float(np.angle(q_off_axis)),
        },
        "q_off_axis_0p15_m0p15": {
            "re": float(q_opp_axis.real),
            "im": float(q_opp_axis.imag),
            "arg_rad": float(np.angle(q_opp_axis)),
        },
        "lax_birman_C_g_002_abs": float(abs(c_g_002)),
        "top_g_process_umklapp": g_top[:3],
        "top_f_process_umklapp": f_top[:3],
    }


def sublattice_b_mask(r_nm: np.ndarray) -> np.ndarray:
    """Return boolean mask True for Sublattice B sites (odd m_i, sum(m) % 4 == 3)."""
    m = np.rint(np.atleast_2d(np.asarray(r_nm, dtype=np.float64)) * (4.0 / A_SI_NM)).astype(int)
    return ((m[:, 0] + m[:, 1] + m[:, 2]) % 4) == 3


def _sinh_quad_1d(a: float, b: float, center: float, scale: float, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Gauss-Legendre quadrature on [a, b] clustered smoothly around `center` via sinh transform."""
    u_lo = math.asinh((a - center) / scale)
    u_hi = math.asinh((b - center) / scale)
    gx, gw = roots_legendre(n)
    u = 0.5 * (u_hi - u_lo) * gx + 0.5 * (u_hi + u_lo)
    du = 0.5 * (u_hi - u_lo) * gw
    x = center + scale * np.sinh(u)
    w = scale * np.cosh(u) * du
    return x, w


@dataclass
class KBlochSectorGrid:
    k0_frac: float
    Q_vecs: np.ndarray
    W_3d: np.ndarray
    duA: np.ndarray
    duB: np.ndarray
    unique_epm_solves: int


_SECTOR_GRID_CACHE: dict[tuple[float, int, int], KBlochSectorGrid] = {}


def build_1stbz_sector_grid(k0_frac: float = K0_FRAC, n_xy: int = 10, n_z_lo: int = 8) -> KBlochSectorGrid:
    """Build boundary-fitted sinh-clustered 3D quadrature on the exact 1st-BZ +z valley sector.

    Exact FCC 1st-BZ +z Voronoi sector (1/6th of 1st BZ, zero valley overlap, strictly below X):
      0 < k_z < 1,  |k_x| <= min(k_z, 1.5 - k_z),  |k_y| <= min(k_z, 1.5 - k_z - |k_x|).
    Cached by (k0_frac, n_xy, n_z_lo) so repeated model evaluations reuse EPM eigenvectors cleanly.
    """
    cache_key = (round(float(k0_frac), 6), int(n_xy), int(n_z_lo))
    if cache_key in _SECTOR_GRID_CACHE:
        return _SECTOR_GRID_CACHE[cache_key]

    two_pi_a = 2.0 * math.pi / A_SI_NM
    n_z_hi = max(4, n_z_lo - 2)
    kz1, wz1 = _sinh_quad_1d(0.005, k0_frac, k0_frac, 0.05, n_z_lo)
    kz2, wz2 = _sinh_quad_1d(k0_frac, 0.999, k0_frac, 0.04, n_z_hi)
    kz_arr = np.concatenate([kz1, kz2])
    wz_arr = np.concatenate([wz1, wz2])

    _, vec0, ua0, _ = epm_bloch_state(np.array([0.0, 0.0, k0_frac]))
    ua0_abs = abs(ua0)

    q_list, w_list, dua_list, dub_list = [], [], [], []
    epm_cache: dict[tuple[int, int, int, int], tuple[complex, complex]] = {}
    for iz, (kz, wz) in enumerate(zip(kz_arr, wz_arr)):
        xmax = min(float(kz), 1.5 - float(kz))
        if xmax < 1e-6:
            continue
        kx_arr, wx_arr = _sinh_quad_1d(-xmax, xmax, 0.0, 0.06, n_xy)
        for kx, wx in zip(kx_arr, wx_arr):
            ymax = min(float(kz), 1.5 - float(kz) - abs(float(kx)))
            if ymax < 1e-6:
                continue
            ky_arr, wy_arr = _sinh_quad_1d(-ymax, ymax, 0.0, 0.06, n_xy)
            for ky, wy in zip(ky_arr, wy_arr):
                q_list.append((float(kx) * two_pi_a, float(ky) * two_pi_a, (float(kz) - k0_frac) * two_pi_a))
                w_list.append(float(wx * wy * wz) * (two_pi_a ** 3) / ((2.0 * math.pi) ** 3))
                af, bf = (abs(float(kx)), abs(float(ky))) if abs(kx) >= abs(ky) else (abs(float(ky)), abs(float(kx)))
                sgn = 1 if (kx * ky) >= 0.0 else -1
                key = (int(round(af * 1e5)), int(round(bf * 1e5)), iz, sgn)
                if key not in epm_cache:
                    _, _, ua, ub = epm_bloch_state(np.array([af, sgn * bf, float(kz)]), ref_vec=vec0)
                    uA_rel = abs(ua) / ua0_abs
                    uB_rel = (ub / ua) * uA_rel
                    epm_cache[key] = (uA_rel - 1.0, uB_rel - 1.0)
                da, db = epm_cache[key]
                dua_list.append(da)
                dub_list.append(db)

    grid = KBlochSectorGrid(
        k0_frac=float(k0_frac),
        Q_vecs=np.asarray(q_list, dtype=np.float64),
        W_3d=np.asarray(w_list, dtype=np.float64),
        duA=np.asarray(dua_list, dtype=np.complex128),
        duB=np.asarray(dub_list, dtype=np.complex128),
        unique_epm_solves=len(epm_cache),
    )
    _SECTOR_GRID_CACHE[cache_key] = grid
    return grid


def eval_vokl6_wavefunction_sites(
    r_nm: np.ndarray,
    blocks: ValleyBlocks,
    c_1v: np.ndarray,
    k0_frac: float = K0_FRAC,
    include_k_bloch: bool = True,
    n_xy: int = 10,
    n_z_lo: int = 8,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Evaluate full VOKL-6 1s(A1) wavefunction Psi_A1(R) at all lattice sites r_nm [N, 3]."""
    r = np.atleast_2d(np.asarray(r_nm, dtype=np.float64))
    k0 = k0_frac * 2.0 * math.pi / A_SI_NM

    f_x = eval_1v_envelope_realspace(r, blocks, c_1v, axis=0)
    f_y = eval_1v_envelope_realspace(r, blocks, c_1v, axis=1)
    f_z = eval_1v_envelope_realspace(r, blocks, c_1v, axis=2)

    psi_env = math.sqrt(2.0 / 3.0) * (
        f_x * np.cos(k0 * r[:, 0])
        + f_y * np.cos(k0 * r[:, 1])
        + f_z * np.cos(k0 * r[:, 2])
    )
    if not include_k_bloch:
        return psi_env, {"mode": "vokl6_envelope_only", "k0_frac": float(k0_frac)}

    grid = build_1stbz_sector_grid(k0_frac=k0_frac, n_xy=n_xy, n_z_lo=n_z_lo)
    Q_vecs, W_3d = grid.Q_vecs, grid.W_3d

    alpha, beta, norm = blocks.alpha, blocks.beta, blocks.norm
    ft_pref = (c_1v * norm) * (math.pi / alpha) * np.sqrt(math.pi / beta)
    q_perp2 = Q_vecs[:, 0] ** 2 + Q_vecs[:, 1] ** 2
    q_par2 = Q_vecs[:, 2] ** 2
    F_tilde = np.exp(
        -q_perp2[:, None] / (4.0 * alpha[None, :])
        - q_par2[:, None] / (4.0 * beta[None, :])
    ) @ ft_pref

    f0_exact = float(np.dot(c_1v, norm))
    f0_quad_frac = float(np.sum(W_3d * F_tilde)) / f0_exact
    f004_exact = float(eval_1v_envelope_realspace(REF_SHELL_NM[None, :], blocks, c_1v, axis=2)[0])
    f004_quad = float(np.real(np.sum(W_3d * F_tilde * np.exp(1j * (Q_vecs @ REF_SHELL_NM)))))
    f004_quad_frac = f004_quad / f004_exact

    w_duA = W_3d * F_tilde * grid.duA
    w_duB = W_3d * F_tilde * grid.duB

    is_B = sublattice_b_mask(r)
    idx_A = np.where(~is_B)[0]
    idx_B = np.where(is_B)[0]

    def _eval_valley_delta(coords_perm: np.ndarray) -> np.ndarray:
        n_pts = len(coords_perm)
        out = np.zeros(n_pts, dtype=np.float64)
        chunk = 4096
        for sub_idx, w_du in ((idx_A, w_duA), (idx_B, w_duB)):
            if len(sub_idx) == 0:
                continue
            for start in range(0, len(sub_idx), chunk):
                sl = sub_idx[start:start + chunk]
                pts_c = coords_perm[sl]
                phase = pts_c @ Q_vecs.T
                d_val = np.exp(1j * phase) @ w_du
                carrier = np.exp(1j * k0 * pts_c[:, 2])
                out[sl] = np.real(carrier * d_val)
        return out

    d_z = _eval_valley_delta(r)
    d_x = _eval_valley_delta(r[:, [1, 2, 0]])
    d_y = _eval_valley_delta(r[:, [2, 0, 1]])

    psi_bloch_corr = math.sqrt(2.0 / 3.0) * (d_x + d_y + d_z)
    psi_total = psi_env + psi_bloch_corr

    diag = {
        "mode": "vokl6_full_k_bloch_1stBZ_boundary_fitted",
        "k0_frac": float(k0_frac),
        "n_xy": int(n_xy),
        "n_z_lo": int(n_z_lo),
        "n_q_points": int(len(Q_vecs)),
        "unique_epm_solves": int(grid.unique_epm_solves),
        "quad_envelope_capture_at_0": float(f0_quad_frac),
        "quad_envelope_capture_at_004": float(f004_quad_frac),
        "max_abs_duA": float(np.max(np.abs(grid.duA))),
        "max_abs_duB": float(np.max(np.abs(grid.duB))),
        "max_imag_duB": float(np.max(np.abs(grid.duB.imag))),
    }
    return psi_total, diag


# ---------------------------------------------------------------------------
# 4. Full 3D Hyperfine Tensor A(R) = A_iso(R) I_3 + T_dip(R)
# ---------------------------------------------------------------------------
def compute_3d_hyperfine_tensor(
    r_nm: np.ndarray,
    a_iso_hz: np.ndarray,
    blocks: ValleyBlocks | None = None,
    c_1v: np.ndarray | None = None,
    extended_dipole: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute full 3x3 hyperfine tensor A(R) [N, 3, 3] and traceless dipolar tensor T_dip(R) [N, 3, 3]."""
    r = np.atleast_2d(np.asarray(r_nm, dtype=np.float64))
    r_norm = np.linalg.norm(r, axis=1)
    r_hat = r / r_norm[:, None]

    if extended_dipole and blocks is not None and c_1v is not None:
        q_enc = enclosed_charge_fraction(r_norm, blocks, c_1v)
    else:
        q_enc = np.ones_like(r_norm)

    scale = DIP_PREF_29SI_HZ_NM3 * q_enc / (r_norm ** 3)
    eye3 = np.eye(3, dtype=np.float64)[None, :, :]
    outer = r_hat[:, :, None] * r_hat[:, None, :]
    T_dip = scale[:, None, None] * (3.0 * outer - eye3)
    # Remove 1-ULP IEEE-754 norm rounding so dipolar tensor is exactly traceless (<1e-13 Hz)
    tr_dip = np.trace(T_dip, axis1=1, axis2=2)
    T_dip = T_dip - (tr_dip / 3.0)[:, None, None] * eye3
    A_tensor = a_iso_hz[:, None, None] * eye3 + T_dip
    return A_tensor, T_dip


def directional_secular_coupling(A_tensor: np.ndarray, b_unit: np.ndarray) -> np.ndarray:
    """Compute secular directional hyperfine coupling A_zz = b^T A(R) b (Hz)."""
    b = np.asarray(b_unit, dtype=np.float64)
    b = b / np.linalg.norm(b)
    return np.einsum("i,nij,j->n", b, A_tensor, b)


# ---------------------------------------------------------------------------
# 5. Legacy KL Reference & Shell Benchmark Utilities
# ---------------------------------------------------------------------------
def legacy_kl_S(r_nm: np.ndarray, a_t: float = 2.5, b_l: float = 1.4, k0f: float = 0.844) -> np.ndarray:
    """Exact Exp25/42/56/59/62 legacy Kohn-Luttinger envelope sum S(r)."""
    r = np.atleast_2d(np.asarray(r_nm, dtype=np.float64))
    k0 = k0f * 2.0 * math.pi / A_SI_NM
    r2 = np.sum(r * r, axis=1)
    out = np.zeros(len(r), dtype=np.float64)
    for i in range(3):
        ri2 = r[:, i] ** 2
        perp2 = np.maximum(0.0, r2 - ri2)
        out += np.exp(-np.sqrt(perp2 / (a_t ** 2) + ri2 / (b_l ** 2))) * np.cos(k0 * r[:, i])
    return out


def compute_shell_benchmark(psi_vals_by_shell: dict[str, float], is_normalized_psi: bool = True) -> dict[str, Any]:
    """Compute dimensionless ratios relative to (0,0,4), relative errors, and log10-RMS."""
    ref_sq = psi_vals_by_shell["(0,0,4)"] ** 2
    ratios = {name: float((val ** 2) / ref_sq) for name, val in psi_vals_by_shell.items()}

    rel_errors: dict[str, float] = {}
    log10_errs: list[float] = []
    for name, info in BENCHMARK_SHELLS.items():
        tgt = info["target_ratio"]
        pred = ratios[name]
        rel_errors[name] = float(abs(pred - tgt) / tgt)
        log10_errs.append(math.log10(max(pred, 1e-12) / tgt))

    out: dict[str, Any] = {
        "ratios": ratios,
        "rel_errors": rel_errors,
        "log10_rms_4shells": float(math.sqrt(float(np.mean(np.square(log10_errs))))),
        "err_R111": rel_errors["(1,1,1)"],
        "err_R331": rel_errors["(3,3,1)"],
        "A_repo_MHz": {name: float(ratios[name] * (REF_A_REPO_HZ * 1e-6)) for name in ratios},
    }
    if is_normalized_psi:
        out["abinitio_A004_MHz_eta186"] = float(FC_PREF_29SI_HZ_NM3 * ETA_SI_KL * ref_sq * 1e-6)
        out["abinitio_A004_MHz_eta178"] = float(FC_PREF_29SI_HZ_NM3 * ETA_SI_ASSALI * ref_sq * 1e-6)
    else:
        out["abinitio_A004_MHz_eta186"] = None
        out["abinitio_A004_MHz_eta178"] = None
    return out


def run_vokl6_theory_suite(n_xy: int = 10, n_z_lo: int = 8) -> dict[str, Any]:
    """Run full VOKL-6 calibration, EPM verification, ablation, and shell benchmarks."""
    blocks = precompute_single_valley_blocks()
    bare_emt = solve_bare_emt(blocks)

    # Primary physical calibration: Morton & Preston (1978) 3s core ratio eta_P = 263.71
    cal = calibrate_vokl6_to_31p_invariants(blocks, eta_p=ETA_P_PHYSICAL)
    # Sensitivities: eta_P = eta_Si = 186.0 (equal bunching) and Assali eta_Si = 178.0 * 1.4178 = 252.37
    cal_equal_eta = calibrate_vokl6_to_31p_invariants(blocks, eta_p=ETA_SI_KL)
    cal_assali = calibrate_vokl6_to_31p_invariants(blocks, eta_p=ETA_SI_ASSALI * P_TO_SI_CORE_RATIO)

    radii_emt = compute_effective_radii(blocks, bare_emt["coeffs"])
    radii_vokl6 = compute_effective_radii(blocks, cal["c_1v"])
    epm_info = verify_epm_band_structure()

    shell_names = list(FORWARD_SHELLS.keys())
    shell_coords_nm = np.array([FORWARD_SHELLS[k] for k in shell_names], dtype=np.float64) * (A_SI_NM / 4.0)

    # M0: Legacy KL (Exp25: a=2.5, b=1.4, k0f=0.844)
    s_kl = legacy_kl_S(shell_coords_nm, a_t=2.5, b_l=1.4, k0f=0.844)
    bench_kl = compute_shell_benchmark({n: float(s_kl[i]) for i, n in enumerate(shell_names)}, is_normalized_psi=False)

    # M1: Bare EMT (V_cc=0, k0f=0.85, frozen Bloch)
    psi_emt, _ = eval_vokl6_wavefunction_sites(
        shell_coords_nm, blocks, bare_emt["coeffs"], k0_frac=K0_FRAC, include_k_bloch=False
    )
    bench_emt = compute_shell_benchmark({n: float(psi_emt[i]) for i, n in enumerate(shell_names)})

    # M2: VOKL-6 Envelope Only (central-cell A1 contracted envelope, frozen-k0 Bloch)
    psi_vokl_env, _ = eval_vokl6_wavefunction_sites(
        shell_coords_nm, blocks, cal["c_1v"], k0_frac=K0_FRAC, include_k_bloch=False
    )
    bench_vokl_env = compute_shell_benchmark({n: float(psi_vokl_env[i]) for i, n in enumerate(shell_names)})

    # M3: Full VOKL-6 (central-cell A1 envelope + 3D k-space CB-EPM Bloch wavepacket, k0f=0.85)
    psi_vokl_full, kbloch_diag = eval_vokl6_wavefunction_sites(
        shell_coords_nm, blocks, cal["c_1v"], k0_frac=K0_FRAC, include_k_bloch=True, n_xy=n_xy, n_z_lo=n_z_lo
    )
    bench_vokl_full = compute_shell_benchmark({n: float(psi_vokl_full[i]) for i, n in enumerate(shell_names)})

    # Quadrature convergence check (coarser n_xy - 2, n_z_lo - 2)
    psi_vokl_coarse, _ = eval_vokl6_wavefunction_sites(
        shell_coords_nm, blocks, cal["c_1v"], k0_frac=K0_FRAC, include_k_bloch=True,
        n_xy=max(6, n_xy - 2), n_z_lo=max(6, n_z_lo - 2)
    )
    bench_vokl_coarse = compute_shell_benchmark({n: float(psi_vokl_coarse[i]) for i, n in enumerate(shell_names)})

    # Sensitivity checks: k0f = 0.844, equal eta_P = 186, Assali eta_Si = 178
    psi_vokl_0844, _ = eval_vokl6_wavefunction_sites(
        shell_coords_nm, blocks, cal["c_1v"], k0_frac=0.844, include_k_bloch=True, n_xy=n_xy, n_z_lo=n_z_lo
    )
    bench_vokl_0844 = compute_shell_benchmark({n: float(psi_vokl_0844[i]) for i, n in enumerate(shell_names)})

    psi_vokl_eq, _ = eval_vokl6_wavefunction_sites(
        shell_coords_nm, blocks, cal_equal_eta["c_1v"], k0_frac=K0_FRAC, include_k_bloch=True, n_xy=n_xy, n_z_lo=n_z_lo
    )
    bench_vokl_eq = compute_shell_benchmark({n: float(psi_vokl_eq[i]) for i, n in enumerate(shell_names)})

    psi_vokl_assali, _ = eval_vokl6_wavefunction_sites(
        shell_coords_nm, blocks, cal_assali["c_1v"], k0_frac=K0_FRAC, include_k_bloch=True, n_xy=n_xy, n_z_lo=n_z_lo
    )
    bench_vokl_assali = compute_shell_benchmark({n: float(psi_vokl_assali[i]) for i, n in enumerate(shell_names)})

    # Radial envelope profiles for plotting (0..5.5 nm)
    r_prof = np.linspace(0.0, 5.5, 221)
    pts_perp = np.column_stack([r_prof, np.zeros_like(r_prof), np.zeros_like(r_prof)])
    pts_par = np.column_stack([np.zeros_like(r_prof), np.zeros_like(r_prof), r_prof])
    profiles = {
        "r_nm": r_prof.tolist(),
        "F_vokl6_perp": eval_1v_envelope_realspace(pts_perp, blocks, cal["c_1v"], axis=2).tolist(),
        "F_vokl6_par": eval_1v_envelope_realspace(pts_par, blocks, cal["c_1v"], axis=2).tolist(),
        "F_emt_perp": eval_1v_envelope_realspace(pts_perp, blocks, bare_emt["coeffs"], axis=2).tolist(),
        "F_emt_par": eval_1v_envelope_realspace(pts_par, blocks, bare_emt["coeffs"], axis=2).tolist(),
        "F_kl_perp": (math.sqrt(1.0 / (math.pi * 2.5 * 2.5 * 1.4)) * np.exp(-r_prof / 2.5)).tolist(),
        "F_kl_par": (math.sqrt(1.0 / (math.pi * 2.5 * 2.5 * 1.4)) * np.exp(-r_prof / 1.4)).tolist(),
        "Q_enc_vokl6": enclosed_charge_fraction(r_prof, blocks, cal["c_1v"]).tolist(),
    }

    return {
        "blocks": blocks,
        "bare_emt": bare_emt,
        "calibration": cal,
        "calibration_equal_eta": cal_equal_eta,
        "calibration_assali": cal_assali,
        "radii_emt": radii_emt,
        "radii_vokl6": radii_vokl6,
        "epm": epm_info,
        "kbloch_diag": kbloch_diag,
        "profiles": profiles,
        "benchmarks": {
            "KL_legacy": bench_kl,
            "EMT_bare_k085": bench_emt,
            "VOKL6_envelope_only": bench_vokl_env,
            "VOKL6_full_k085": bench_vokl_full,
            "VOKL6_full_coarse_quad": bench_vokl_coarse,
            "VOKL6_full_k0844_sens": bench_vokl_0844,
            "VOKL6_full_eq_eta186_sens": bench_vokl_eq,
            "VOKL6_full_assali178_sens": bench_vokl_assali,
        },
    }


def compute_full_atlas_vokl6(
    sites_nm: np.ndarray,
    b_dir: np.ndarray,
    blocks: ValleyBlocks,
    c_1v: np.ndarray,
    k0_frac: float = K0_FRAC,
    n_xy: int = 10,
    n_z_lo: int = 8,
) -> dict[str, Any]:
    """Compute VOKL-6 wavefunction, 3D Fermi-contact + dipolar tensors & directional couplings on all sites."""
    psi_all, kdiag = eval_vokl6_wavefunction_sites(
        sites_nm, blocks, c_1v, k0_frac=k0_frac, include_k_bloch=True, n_xy=n_xy, n_z_lo=n_z_lo
    )
    psi_ref, _ = eval_vokl6_wavefunction_sites(
        REF_SHELL_NM[None, :], blocks, c_1v, k0_frac=k0_frac, include_k_bloch=True, n_xy=n_xy, n_z_lo=n_z_lo
    )
    ref_sq = float(psi_ref[0] ** 2)

    # Repo A/2 convention normalized at (0,0,4) = 2.981 MHz (exact apples-to-apples with Exp25/42/59/62)
    a_iso_norm = REF_A_REPO_HZ * (psi_all ** 2) / ref_sq
    # True Hale & Mieher spin-Hamiltonian convention H = a (S.I): a(0,0,4) = 5.962 MHz -> f_+- = |nu_n +- a/2|
    a_iso_hm5962 = (REF_A_HM_MHZ * 1e6) * (psi_all ** 2) / ref_sq
    # Ab-initio Fermi-contact in repo A/2 convention (a_abinit / 2 with eta_Si=186, zero (0,0,4) rescaling)
    a_iso_abinit_half = 0.5 * FC_PREF_29SI_HZ_NM3 * ETA_SI_KL * (psi_all ** 2)
    # Ab-initio Fermi-contact in full Hale & Mieher convention (a_abinit with eta_Si=186)
    a_iso_abinit_full = FC_PREF_29SI_HZ_NM3 * ETA_SI_KL * (psi_all ** 2)

    A_tens_ext, T_dip_ext = compute_3d_hyperfine_tensor(sites_nm, a_iso_norm, blocks=blocks, c_1v=c_1v, extended_dipole=True)
    A_tens_pt, T_dip_pt = compute_3d_hyperfine_tensor(sites_nm, a_iso_norm, extended_dipole=False)
    A_tens_hm, _ = compute_3d_hyperfine_tensor(sites_nm, a_iso_hm5962, blocks=blocks, c_1v=c_1v, extended_dipole=True)
    A_tens_abinit, _ = compute_3d_hyperfine_tensor(sites_nm, a_iso_abinit_half, blocks=blocks, c_1v=c_1v, extended_dipole=True)
    A_tens_abinit_full, _ = compute_3d_hyperfine_tensor(sites_nm, a_iso_abinit_full, blocks=blocks, c_1v=c_1v, extended_dipole=True)

    trace_ext_max = float(np.max(np.abs(np.trace(T_dip_ext, axis1=1, axis2=2))))
    trace_pt_max = float(np.max(np.abs(np.trace(T_dip_pt, axis1=1, axis2=2))))

    return {
        "psi_all": psi_all,
        "a_iso_norm_Hz": a_iso_norm,
        "a_iso_hm5962_Hz": a_iso_hm5962,
        "a_iso_abinit_half_Hz": a_iso_abinit_half,
        "a_iso_abinit_full_Hz": a_iso_abinit_full,
        "A_dir_ext_Hz": directional_secular_coupling(A_tens_ext, b_dir),
        "A_dir_pt_Hz": directional_secular_coupling(A_tens_pt, b_dir),
        "A_dir_hm5962_ext_Hz": directional_secular_coupling(A_tens_hm, b_dir),
        "A_dir_abinit_ext_Hz": directional_secular_coupling(A_tens_abinit, b_dir),
        "A_dir_abinit_full_ext_Hz": directional_secular_coupling(A_tens_abinit_full, b_dir),
        "max_abs_trace_T_dip_ext_Hz": trace_ext_max,
        "max_abs_trace_T_dip_pt_Hz": trace_pt_max,
        "kbloch_diag": kdiag,
    }


if __name__ == "__main__":
    import time
    t0 = time.time()
    out = run_vokl6_theory_suite(n_xy=10, n_z_lo=8)
    print(f"VOKL-6 theory suite completed in {time.time() - t0:.2f} s")
    print("Bare EMT:", {k: v for k, v in out["bare_emt"].items() if k != "coeffs"})
    print("VOKL-6 calibration:", {k: v for k, v in out["calibration"].items() if k != "c_1v"})
    print("Radii VOKL-6:", out["radii_vokl6"])
    print("EPM:", out["epm"])
    for mname, b in out["benchmarks"].items():
        ab = f"{b['abinitio_A004_MHz_eta186']:.3f}" if b["abinitio_A004_MHz_eta186"] is not None else "  N/A"
        print(
            f"  {mname:26s} | R111={b['ratios']['(1,1,1)']:.4f}({100*b['err_R111']:4.1f}%) | "
            f"R331={b['ratios']['(3,3,1)']:.4f}({100*b['err_R331']:4.1f}%) | "
            f"R220={b['ratios']['(2,2,0)']:.4f} | R11-3={b['ratios']['(1,1,-3)']:.5f} | "
            f"logRMS={b['log10_rms_4shells']:.4f} | A004={ab} MHz"
        )
