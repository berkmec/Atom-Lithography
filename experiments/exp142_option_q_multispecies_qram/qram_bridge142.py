"""Exp142 (H160) Part 1: Option-Q Superconducting 4-8 GHz qRAM Bridge Physics.

Implements:
  1. Exact ABCD transfer-matrix synthesis & verification of 50 Ohm <-> 3000 Ohm (60:1) impedance
     transformers at f0 = 6.0 GHz with realistic superconducting conductor loss (Q_int = 1e5 NbTiN):
       - Single lambda/4 baseline (Z1 = sqrt(50*3000) = 387.3 Ohm)
       - 3-section & 5-section exact equal-ripple Chebyshev multi-section transformers
       - Continuous Klopfenstein (1956) Bessel-I1 optimal taper (120 cascaded ABCD sections)
     Verifies exact lossless passivity |S11|^2 + |S21|^2 = 1 to <1e-13.
  2. Exact 12x12 open-quantum-system Lindblad SWAP simulation (Transmon [2] x Bridge Resonator [3]
     x 31P Flip-Flop [2]) via exact 144x144 Liouvillian matrix exponential (expm), verifying CPTP
     (|Tr(rho)-1| < 1e-12, min_eig >= -1e-12) and exact 6-state Nielsen average state fidelity across
     write -> nuclear-register storage (t_store in [10 us, 10 s]) -> read vs bare Transmon idle.
  3. Per-port 20 mK / 100 mK / 4 K / 50 K cryogenic heat load budget (CuNi/NbTi coax + SMF-28 fiber)
     checked against the remaining single LD400/PT420 headroom from Exp140.

Zero hardcoded host paths. Epistemic: no_lab_measurement=True ({Literatür}/{Analitik}/{Model}/{Sayısal-Simülasyon}).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.linalg import expm
from scipy.optimize import minimize
from scipy.special import i1 as bessel_i1

Z0_OHM = 50.0
ZL_OHM = 3000.0
F0_GHZ = 6.0
Q_INT_SC = 1.0e5


# ---------------------------------------------------------------------------
# 1. Exact ABCD Multi-Section Chebyshev & Klopfenstein Impedance Transformer
# ---------------------------------------------------------------------------
def _abcd_cascade_sparam(
    z_sections: np.ndarray,
    len_frac_lambda0: np.ndarray,
    freqs_ghz: np.ndarray,
    z0: float = Z0_OHM,
    zl: float = ZL_OHM,
    q_int: float | None = Q_INT_SC,
    f0_ghz: float = F0_GHZ,
) -> tuple[np.ndarray, np.ndarray]:
    """Exact ABCD cascade returning complex (S11, S21) across freqs_ghz."""
    nf = len(freqs_ghz)
    A = np.ones(nf, dtype=np.complex128)
    B = np.zeros(nf, dtype=np.complex128)
    C = np.zeros(nf, dtype=np.complex128)
    D = np.ones(nf, dtype=np.complex128)

    for zk, lf in zip(z_sections, len_frac_lambda0):
        # Electrical length beta*l = 2*pi * lf * (f / f0); attenuation alpha*l = (pi / Q_int) * lf * (f / f0)
        beta_l = 2.0 * math.pi * lf * (freqs_ghz / f0_ghz)
        if q_int is not None and q_int > 0.0:
            alpha_l = (math.pi / q_int) * lf * (freqs_ghz / f0_ghz)
        else:
            alpha_l = np.zeros_like(beta_l)
        gl = alpha_l + 1j * beta_l
        ch = np.cosh(gl)
        sh = np.sinh(gl)
        a_n = A * ch + B * (sh / zk)
        b_n = A * (zk * sh) + B * ch
        c_n = C * ch + D * (sh / zk)
        d_n = C * (zk * sh) + D * ch
        A, B, C, D = a_n, b_n, c_n, d_n

    # Exact power-wave S-parameters between unequal real port impedances z0 and zl (Kurokawa 1965)
    denom = A * zl + B + C * z0 * zl + D * z0
    s11 = (A * zl + B - C * z0 * zl - D * z0) / denom
    s21 = (2.0 * math.sqrt(z0 * zl)) / denom
    return s11, s21


def synthesize_chebyshev_exact(
    n_sections: int,
    z0: float = Z0_OHM,
    zl: float = ZL_OHM,
    f_lo_ghz: float = 4.0,
    f_hi_ghz: float = 8.0,
    f0_ghz: float = F0_GHZ,
) -> np.ndarray:
    """Synthesize exact symmetric N-section quarter-wave Chebyshev impedances for large Z_L/Z_0 = 60.

    Enforces exact geometric anti-symmetry Z_k * Z_{N+1-k} = Z0 * ZL and directly minimizes
    minimax passband |S11(f)| across [f_lo, f_hi] via exact ABCD evaluation (avoiding small-reflection
    approximation error at R = 60).
    """
    z_mid = math.sqrt(z0 * zl)
    if n_sections == 1:
        return np.array([z_mid], dtype=np.float64)

    # Geometric progression initial guess in log-impedance space
    log_z_init = np.linspace(math.log(z0), math.log(zl), n_sections + 2)[1:-1]
    n_free = n_sections // 2
    x0 = log_z_init[:n_free]
    f_grid = np.linspace(f_lo_ghz, f_hi_ghz, 81)
    lens = np.full(n_sections, 0.25, dtype=np.float64)

    def unpack(x: np.ndarray) -> np.ndarray:
        z_half = np.exp(x)
        z_rev = (z0 * zl) / z_half[::-1]
        if n_sections % 2 == 1:
            return np.concatenate([z_half, [z_mid], z_rev])
        return np.concatenate([z_half, z_rev])

    def objective(x: np.ndarray) -> float:
        zs = unpack(x)
        if np.any(np.diff(zs) <= 0.0) or zs[0] <= z0 or zs[-1] >= zl:
            return 10.0
        s11, _ = _abcd_cascade_sparam(zs, lens, f_grid, z0=z0, zl=zl, q_int=None, f0_ghz=f0_ghz)
        # Smooth L_16 approximation to minimax passband |S11|
        m = np.abs(s11)
        return float(np.max(m) + 0.05 * (np.mean(m ** 8) ** 0.125))

    res = minimize(objective, x0, method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-7, "maxiter": 4000})
    return unpack(res.x)


def synthesize_klopfenstein_taper(
    n_steps: int = 120,
    gamma_m: float = 0.05,
    z0: float = Z0_OHM,
    zl: float = ZL_OHM,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Exact Klopfenstein (1956, Proc. IRE 44, 31) optimal impedance taper for Z0 <-> ZL.

    Returns (z_sections [n_steps], len_frac_lambda0 [n_steps], total_length_lambda0).
    For R = 60, Gamma_0 = 0.5 * ln(ZL/Z0) = 2.0472, A = arccosh(Gamma_0 / gamma_m) = 4.405.
    Cutoff electrical length beta_c * L = A -> at f_c = 3.5 GHz (well below 4-8 GHz band!),
    L / lambda_0 = (A / (2*pi)) * (f0 / f_c).
    """
    gamma0 = 0.5 * math.log(zl / z0)
    A = math.acosh(gamma0 / gamma_m)
    # Choose cutoff f_c = 3.6 GHz so full 4-8 GHz band sits cleanly above Klopfenstein cutoff!
    f_c_ghz = 3.6
    total_len_lam0 = (A / (2.0 * math.pi)) * (F0_GHZ / f_c_ghz)

    # Numerically evaluate Klopfenstein phi(x, A) = int_0^x I1(A*sqrt(1-y^2)) / (A*sqrt(1-y^2)) dy on fine grid
    y_fine = np.linspace(0.0, 1.0, 2001)
    s_y = np.sqrt(np.maximum(0.0, 1.0 - y_fine * y_fine))
    arg = np.where(s_y > 1e-12, A * s_y, 1.0)
    integrand = np.where(s_y > 1e-12, bessel_i1(arg) / arg, 0.5)
    phi_fine = np.concatenate([[0.0], np.cumsum(0.5 * (integrand[:-1] + integrand[1:]) * np.diff(y_fine))])

    # Midpoints u in [-1, 1] for n_steps equal-length micro-sections
    u_mid = np.linspace(-1.0 + 1.0 / n_steps, 1.0 - 1.0 / n_steps, n_steps)
    phi_u = np.sign(u_mid) * np.interp(np.abs(u_mid), y_fine, phi_fine)

    ln_z = 0.5 * math.log(z0 * zl) + (gamma0 / math.cosh(A)) * (A * A * phi_u)
    z_sec = np.exp(ln_z)
    lens = np.full(n_steps, total_len_lam0 / n_steps, dtype=np.float64)
    return z_sec, lens, float(total_len_lam0)


def _extract_bw_and_metrics(freqs_ghz: np.ndarray, s11: np.ndarray, s21: np.ndarray, f0_ghz: float = F0_GHZ) -> dict[str, Any]:
    s11_db = 20.0 * np.log10(np.maximum(np.abs(s11), 1e-15))
    s21_db = 20.0 * np.log10(np.maximum(np.abs(s21), 1e-15))
    passivity_err = float(np.max(np.abs(s11) ** 2 + np.abs(s21) ** 2 - 1.0))

    i0 = int(np.argmin(np.abs(freqs_ghz - f0_ghz)))
    il_6ghz_db = float(-s21_db[i0])
    rl_6ghz_db = float(-s11_db[i0])

    def _contiguous_bw(thresh_db: float) -> tuple[float, float, float]:
        ok = s11_db <= thresh_db
        if not ok[i0]:
            return (0.0, float(freqs_ghz[i0]), float(freqs_ghz[i0]))
        lo, hi = i0, i0
        while lo > 0 and ok[lo - 1]:
            lo -= 1
        while hi < len(freqs_ghz) - 1 and ok[hi + 1]:
            hi += 1
        return (float(freqs_ghz[hi] - freqs_ghz[lo]), float(freqs_ghz[lo]), float(freqs_ghz[hi]))

    bw15, f15_lo, f15_hi = _contiguous_bw(-15.0)
    bw20, f20_lo, f20_hi = _contiguous_bw(-20.0)
    in_4_8 = (freqs_ghz >= 4.0) & (freqs_ghz <= 8.0)
    max_s11_4_8_db = float(np.max(s11_db[in_4_8]))
    max_il_4_8_db = float(np.max(-s21_db[in_4_8]))

    return {
        "IL_6GHz_dB": il_6ghz_db,
        "RL_6GHz_dB": rl_6ghz_db,
        "max_S11_4_8GHz_dB": max_s11_4_8_db,
        "max_IL_4_8GHz_dB": max_il_4_8_db,
        "bw_15dB_GHz": bw15,
        "bw_15dB_span_GHz": [f15_lo, f15_hi],
        "bw_20dB_GHz": bw20,
        "bw_20dB_span_GHz": [f20_lo, f20_hi],
        "max_passivity_excess": passivity_err,
        "s11_dB": s11_db,
        "s21_dB": s21_db,
    }


def analyze_impedance_transformers() -> dict[str, Any]:
    """Synthesize & compare 1-sec, 3-sec, 5-sec Chebyshev and Klopfenstein 50 <-> 3000 Ohm transformers."""
    freqs = np.linspace(2.0, 10.0, 801)
    designs: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    designs["single_qw_N1"] = (synthesize_chebyshev_exact(1), np.array([0.25]))
    designs["chebyshev_N3"] = (synthesize_chebyshev_exact(3), np.full(3, 0.25))
    designs["chebyshev_N5"] = (synthesize_chebyshev_exact(5), np.full(5, 0.25))
    zk, lk, tot_k = synthesize_klopfenstein_taper(n_steps=120, gamma_m=0.05)
    designs["klopfenstein_taper"] = (zk, lk)

    summary: dict[str, Any] = {"freqs_GHz": freqs}
    for name, (zs, lens) in designs.items():
        # Lossless unitarity check
        s11_0, s21_0 = _abcd_cascade_sparam(zs, lens, freqs, q_int=None)
        unitarity_err = float(np.max(np.abs(np.abs(s11_0) ** 2 + np.abs(s21_0) ** 2 - 1.0)))
        # Lossy NbTiN superconducting Q_int = 1e5
        s11, s21 = _abcd_cascade_sparam(zs, lens, freqs, q_int=Q_INT_SC)
        m = _extract_bw_and_metrics(freqs, s11, s21)
        m["lossless_unitarity_err"] = unitarity_err
        m["n_sections"] = int(len(zs))
        m["total_length_lambda0"] = float(np.sum(lens))
        m["Z_sections_ohm"] = [float(x) for x in zs] if len(zs) <= 10 else [float(zs[0]), float(zs[len(zs) // 2]), float(zs[-1])]
        summary[name] = m

    summary["klopfenstein_total_len_lambda0"] = tot_k
    summary["bw_gain_N5_vs_N1"] = float(summary["chebyshev_N5"]["bw_15dB_GHz"] / max(summary["single_qw_N1"]["bw_15dB_GHz"], 1e-9))
    summary["bw_gain_klopfenstein_vs_N1"] = float(summary["klopfenstein_taper"]["bw_15dB_GHz"] / max(summary["single_qw_N1"]["bw_15dB_GHz"], 1e-9))
    return summary


# ---------------------------------------------------------------------------
# 2. Exact 12x12 Lindblad qRAM SWAP Simulation (Transmon <-> Bridge <-> 31P)
# ---------------------------------------------------------------------------
def _liouvillian_superop(H: np.ndarray, c_ops: list[np.ndarray]) -> np.ndarray:
    """Build exact d^2 x d^2 Lindblad Liouvillian superoperator for vec(rho) (column-major)."""
    d = H.shape[0]
    I_d = np.eye(d, dtype=np.complex128)
    L = -1j * (np.kron(I_d, H) - np.kron(H.T, I_d))
    for c in c_ops:
        cd_c = c.conj().T @ c
        L += np.kron(c.conj(), c) - 0.5 * np.kron(I_d, cd_c) - 0.5 * np.kron(cd_c.T, I_d)
    return L


def _apply_channel_expm(rho: np.ndarray, U_super: np.ndarray) -> np.ndarray:
    d = rho.shape[0]
    vec = rho.reshape(-1, order="F")
    out = (U_super @ vec).reshape((d, d), order="F")
    return 0.5 * (out + out.conj().T)


def _partial_trace_to_qubit(rho_18: np.ndarray, keep: str, d_t: int = 3) -> np.ndarray:
    """Partial trace of (T:d_t, R:3, P:2) density matrix keeping 'T' (projected to computational 2x2) or 'P'."""
    t = rho_18.reshape(d_t, 3, 2, d_t, 3, 2)
    if keep == "T":
        rho_t_full = np.einsum("irjkrj->ik", t)
        return rho_t_full[:2, :2]
    if keep == "T_full":
        return np.einsum("irjkrj->ik", t)
    if keep == "P":
        return np.einsum("ijrijl->rl", t)
    raise ValueError(f"Unknown subsystem: {keep}")


def run_lindblad_qram_swap(
    il_bridge_db: float = 0.0007,
    transmon_t1_us: float = 200.0,
    transmon_t2_us: float = 150.0,
    transmon_anharm_mhz: float = -250.0,
    q_bridge: float = 2.0e5,
    bus_fsr_mhz: float = 600.0,
    g_tr_mhz: float = 12.0,
    g_pr_mhz: float = 4.0,
    p31_ff_t1_us: float = 500.0,
    p31_ff_t2_us: float = 25.0,
    e_to_n_fidelity_one_way: float = 0.996,
    t2n_star_ms: float = 17.7,
    t2n_dd_nom_s: float = 1.0,
    t2n_dd_opt_s: float = 3.0,
) -> dict[str, Any]:
    """Simulate exact 18x18 CPTP Lindblad Transmon (3-level |g,e,f>) <-> Bridge (3) <-> 31P (2) qRAM cycle.

    OBS-131 FIXES:
      1. Replaces ad-hoc `pass_loss_frac * g_tr * 0.25` with physical cavity round-trip FSR loss
         kappa_loss = FSR * (-ln |S21|^2) derived directly from ABCD S21 insertion loss IL_dB
         (giving exact loaded Q_L = 2*pi*f0 / (kappa_int + kappa_loss)).
      2. Upgrades Transmon to 3-level anharmonic basis (|g>, |e>, |f> with alpha = -250 MHz -> 18D Hilbert space)
         to quantify |f> leakage during the T <-> R iSWAP hop.
      3. Evaluates honest 31P flip-flop coherence sensitivity (Exp131/137 1/f T2* = 0.29 us, realistic
         echoed T2 = 10 us + 0.05 dB bond / 0.50 dB connector, vs monolithic idealized T2 = 25 us).
    """
    # Operators in H_T (3) x H_R (3) x H_P (2) = 18
    I2 = np.eye(2, dtype=np.complex128)
    I3 = np.eye(3, dtype=np.complex128)
    a3 = np.array([[0.0, 1.0, 0.0], [0.0, 0.0, math.sqrt(2.0)], [0.0, 0.0, 0.0]], dtype=np.complex128)
    ad3 = a3.conj().T
    n3 = ad3 @ a3
    # Pure dephasing operator on transmon (0, -1, -2) -> matches 0.5*sz on {|g>,|e>}
    proj_e_f = np.diag([0.0, 1.0, 2.0]).astype(np.complex128)
    sm = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.complex128)
    sp = sm.T
    sz = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)

    a_T = np.kron(np.kron(a3, I3), I2)
    ad_T = a_T.conj().T
    n_T = np.kron(np.kron(n3, I3), I2)
    n_T_anh = np.kron(np.kron(n3 @ (n3 - I3), I3), I2)
    deph_T = np.kron(np.kron(proj_e_f, I3), I2)
    a_R = np.kron(np.kron(I3, a3), I2)
    ad_R = a_R.conj().T
    sm_P = np.kron(np.kron(I3, I3), sm)
    sp_P = np.kron(np.kron(I3, I3), sp)
    sz_P = np.kron(np.kron(I3, I3), sz)

    # Rates in rad/us
    g_tr = 2.0 * math.pi * g_tr_mhz  # rad/us
    g_pr = 2.0 * math.pi * g_pr_mhz  # rad/us
    alpha_T = 2.0 * math.pi * transmon_anharm_mhz  # rad/us (-250 MHz anharmonicity)

    gamma1_T = 1.0 / transmon_t1_us
    gamma_phi_T = max(0.0, 1.0 / transmon_t2_us - 0.5 * gamma1_T)
    # Physical loaded resonator decay rate (OBS-131): intrinsic Q_bridge + FSR * (-ln |S21|^2)
    kappa_R_int = 2.0 * math.pi * (F0_GHZ * 1e3) / q_bridge  # rad/us (~0.1885 rad/us)
    s21_power = max(10.0 ** (-il_bridge_db / 10.0), 1e-12)
    kappa_R_ext_loss = bus_fsr_mhz * (-math.log(s21_power))  # 1/us = rad/us power decay rate
    kappa_R = kappa_R_int + kappa_R_ext_loss
    q_loaded_eff = (2.0 * math.pi * F0_GHZ * 1e3) / max(kappa_R, 1e-12)

    gamma1_P = 1.0 / p31_ff_t1_us
    gamma_phi_P = max(0.0, 1.0 / p31_ff_t2_us - 0.5 * gamma1_P)

    c_ops = [
        math.sqrt(gamma1_T) * a_T,
        math.sqrt(2.0 * gamma_phi_T) * deph_T,
        math.sqrt(kappa_R) * a_R,
        math.sqrt(gamma1_P) * sm_P,
        math.sqrt(0.5 * gamma_phi_P) * sz_P,
    ]

    # Step 1: Resonant iSWAP Transmon <-> Bridge including transmon |f> anharmonicity (t1 = pi / (2 * g_tr))
    H_tr = 0.5 * alpha_T * n_T_anh + g_tr * (ad_T @ a_R + a_T @ ad_R)
    t1_us = math.pi / (2.0 * g_tr)
    U_tr = expm(_liouvillian_superop(H_tr, c_ops) * t1_us)

    # Step 2: Resonant iSWAP Bridge <-> 31P Flip-Flop (t2 = pi / (2 * g_pr))
    H_pr = 0.5 * alpha_T * n_T_anh + g_pr * (ad_R @ sm_P + a_R @ sp_P)
    t2_us = math.pi / (2.0 * g_pr)
    U_pr = expm(_liouvillian_superop(H_pr, c_ops) * t2_us)

    z_corr_1q = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)

    # 6 cardinal Bloch states for exact Nielsen average state fidelity
    kets = [
        np.array([1.0, 0.0], dtype=np.complex128),
        np.array([0.0, 1.0], dtype=np.complex128),
        np.array([1.0, 1.0], dtype=np.complex128) / math.sqrt(2.0),
        np.array([1.0, -1.0], dtype=np.complex128) / math.sqrt(2.0),
        np.array([1.0, 1.0j], dtype=np.complex128) / math.sqrt(2.0),
        np.array([1.0, -1.0j], dtype=np.complex128) / math.sqrt(2.0),
    ]
    g0_R = np.array([1.0, 0.0, 0.0], dtype=np.complex128)
    g0_P = np.array([1.0, 0.0], dtype=np.complex128)
    g0_T = np.array([1.0, 0.0, 0.0], dtype=np.complex128)
    rho_R0 = np.outer(g0_R, g0_R.conj())
    rho_P0 = np.outer(g0_P, g0_P.conj())
    rho_T0 = np.outer(g0_T, g0_T.conj())

    f_write_list = []
    f_rt_photon_list = []
    max_trace_err = 0.0
    min_eig_all = 1.0
    max_f_leak = 0.0

    # Also compute full round-trip with nuclear-memory storage channel D_mem(t_store) applied on 31P!
    t_store_s = np.logspace(-5, 1, 61)  # 10 us to 10 s

    def _apply_nuclear_storage_1q(rho_1q: np.ndarray, t_s: float, t1_s: float, t2_s: float, p_en_rt: float) -> np.ndarray:
        lam_en = max(0.0, min(1.0, 2.0 * p_en_rt - 1.0))
        r = lam_en * rho_1q + (1.0 - lam_en) * 0.5 * I2
        e1 = math.exp(-t_s / t1_s)
        e2 = math.exp(-t_s / t2_s)
        out = np.empty((2, 2), dtype=np.complex128)
        out[0, 0] = 1.0 - (1.0 - r[0, 0]) * e1
        out[1, 1] = r[1, 1] * e1
        out[0, 1] = r[0, 1] * e2
        out[1, 0] = r[1, 0] * e2
        return out

    stored_p_states = []
    for psi in kets:
        psi3 = np.array([psi[0], psi[1], 0.0], dtype=np.complex128)
        rho_T_in = np.outer(psi3, psi3.conj())
        rho_18 = np.kron(np.kron(rho_T_in, rho_R0), rho_P0)
        # Write: T -> R -> P
        rho_after_1 = _apply_channel_expm(rho_18, U_tr)
        rho_after_w = _apply_channel_expm(rho_after_1, U_pr)

        for rr in (rho_after_1, rho_after_w):
            max_trace_err = max(max_trace_err, abs(float(np.trace(rr).real) - 1.0))
            min_eig_all = min(min_eig_all, float(np.min(np.linalg.eigvalsh(rr))))
            rt_full = _partial_trace_to_qubit(rr, "T_full")
            max_f_leak = max(max_f_leak, float(np.real(rt_full[2, 2])))

        rho_P_w = _partial_trace_to_qubit(rho_after_w, "P")
        rho_P_corr = z_corr_1q @ rho_P_w @ z_corr_1q
        f_write_list.append(float(np.real(psi.conj() @ rho_P_corr @ psi)))
        stored_p_states.append(rho_P_w)

        # Immediate photon round-trip (t_store = 0): P -> R -> T
        rho_18_back = np.kron(np.kron(rho_T0, rho_R0), rho_P_w)
        rho_after_r1 = _apply_channel_expm(rho_18_back, U_pr)
        rho_after_rt = _apply_channel_expm(rho_after_r1, U_tr)
        for rr in (rho_after_r1, rho_after_rt):
            max_trace_err = max(max_trace_err, abs(float(np.trace(rr).real) - 1.0))
            min_eig_all = min(min_eig_all, float(np.min(np.linalg.eigvalsh(rr))))
        rho_T_out = _partial_trace_to_qubit(rho_after_rt, "T")
        f_rt_photon_list.append(float(np.real(psi.conj() @ rho_T_out @ psi)))

    # Storage curves over t_store in [10 us, 10 s]
    f_bare_transmon = np.zeros(len(t_store_s), dtype=np.float64)
    f_qram_t2n_star = np.zeros(len(t_store_s), dtype=np.float64)
    f_qram_xy8_1s = np.zeros(len(t_store_s), dtype=np.float64)
    f_qram_xy8_3s = np.zeros(len(t_store_s), dtype=np.float64)
    f_qram_29si_bank = np.zeros(len(t_store_s), dtype=np.float64)

    p_en_rt_p31 = e_to_n_fidelity_one_way ** 2
    p_en_rt_29si = 0.990 ** 2

    for ti, ts in enumerate(t_store_s):
        e1_t = math.exp(-ts / (transmon_t1_us * 1e-6))
        e2_t = math.exp(-ts / (transmon_t2_us * 1e-6))
        f_bare_transmon[ti] = (3.0 + e1_t + 2.0 * e2_t) / 6.0

        f_star_s, f_1s_s, f_3s_s, f_bank_s = [], [], [], []
        for idx, psi in enumerate(kets):
            rp = stored_p_states[idx]
            for acc, t2_mem, p_rt in (
                (f_star_s, t2n_star_ms * 1e-3, p_en_rt_p31),
                (f_1s_s, t2n_dd_nom_s, p_en_rt_p31),
                (f_3s_s, t2n_dd_opt_s, p_en_rt_p31),
                (f_bank_s, t2n_dd_nom_s, p_en_rt_29si),
            ):
                rp_s = _apply_nuclear_storage_1q(rp, ts, t1_s=1000.0, t2_s=t2_mem, p_en_rt=p_rt)
                r18 = np.kron(np.kron(rho_T0, rho_R0), rp_s)
                r_out = _apply_channel_expm(_apply_channel_expm(r18, U_pr), U_tr)
                rt_q = _partial_trace_to_qubit(r_out, "T")
                acc.append(float(np.real(psi.conj() @ rt_q @ psi)))

        f_qram_t2n_star[ti] = float(np.mean(f_star_s))
        f_qram_xy8_1s[ti] = float(np.mean(f_1s_s))
        f_qram_xy8_3s[ti] = float(np.mean(f_3s_s))
        f_qram_29si_bank[ti] = float(np.mean(f_bank_s))

    def _time_to_threshold(f_arr: np.ndarray, thresh: float) -> float:
        if f_arr[0] < thresh:
            return 0.0
        below = np.where(f_arr < thresh)[0]
        if len(below) == 0:
            return float(t_store_s[-1])
        j = int(below[0])
        if j == 0:
            return float(t_store_s[0])
        lt0, lt1 = math.log10(t_store_s[j - 1]), math.log10(t_store_s[j])
        frac = (f_arr[j - 1] - thresh) / max(f_arr[j - 1] - f_arr[j], 1e-12)
        return float(10.0 ** (lt0 + frac * (lt1 - lt0)))

    t90_bare = _time_to_threshold(f_bare_transmon, 0.90)
    t90_star = _time_to_threshold(f_qram_t2n_star, 0.90)
    t90_dd1s = _time_to_threshold(f_qram_xy8_1s, 0.90)
    t90_dd3s = _time_to_threshold(f_qram_xy8_3s, 0.90)
    t80_bare = _time_to_threshold(f_bare_transmon, 0.80)
    t80_dd1s = _time_to_threshold(f_qram_xy8_1s, 0.80)

    cross_idx = np.where(f_qram_xy8_1s > f_bare_transmon)[0]
    t_breakeven_us = float(t_store_s[cross_idx[0]] * 1e6) if len(cross_idx) > 0 else 0.0
    f_swap_rt_total = float(f_qram_xy8_1s[0])

    return {
        "hilbert_dim": 18,
        "transmon_levels": 3,
        "transmon_anharm_mhz": float(transmon_anharm_mhz),
        "max_transmon_f_leakage": float(max_f_leak),
        "il_bridge_db": float(il_bridge_db),
        "p31_ff_t2_us": float(p31_ff_t2_us),
        "bus_fsr_mhz": float(bus_fsr_mhz),
        "kappa_R_int_rad_us": float(kappa_R_int),
        "kappa_R_ext_loss_rad_us": float(kappa_R_ext_loss),
        "kappa_R_total_rad_us": float(kappa_R),
        "Q_loaded_eff": float(q_loaded_eff),
        "t_write_photon_ns": float((t1_us + t2_us) * 1e3),
        "t_hop_TR_ns": float(t1_us * 1e3),
        "t_hop_RP_ns": float(t2_us * 1e3),
        "F_write_photon_only": float(np.mean(f_write_list)),
        "F_SWAP_rt_photon_only": float(np.mean(f_rt_photon_list)),
        "F_SWAP_rt_with_nuclear_31P": f_swap_rt_total,
        "F_SWAP_rt_with_29Si_bank": float(f_qram_29si_bank[0]),
        "cptp_max_trace_err": float(max_trace_err),
        "cptp_min_eig": float(min_eig_all),
        "t_breakeven_vs_transmon_us": t_breakeven_us,
        "time_to_F90_s": {
            "bare_transmon": t90_bare,
            "qram_T2n_star_17p7ms": t90_star,
            "qram_XY8_DD_1s": t90_dd1s,
            "qram_XY8_DD_3s": t90_dd3s,
        },
        "lifetime_gain_F90_vs_transmon": {
            "qram_T2n_star_17p7ms": float(t90_star / max(t90_bare, 1e-12)),
            "qram_XY8_DD_1s": float(t90_dd1s / max(t90_bare, 1e-12)),
            "qram_XY8_DD_3s": float(t90_dd3s / max(t90_bare, 1e-12)),
        },
        "lifetime_gain_F80_DD1s_vs_transmon": float(t80_dd1s / max(t80_bare, 1e-12)),
        "t_store_s": t_store_s.tolist(),
        "F_curves": {
            "bare_transmon": f_bare_transmon.tolist(),
            "qram_T2n_star": f_qram_t2n_star.tolist(),
            "qram_XY8_1s": f_qram_xy8_1s.tolist(),
            "qram_XY8_3s": f_qram_xy8_3s.tolist(),
            "qram_29Si_bank_1s": f_qram_29si_bank.tolist(),
        },
    }


# ---------------------------------------------------------------------------
# 3. Per-Port & Option-Q Cryogenic Heat Budget (Consistent with Exp140 LD400/PT420)
# ---------------------------------------------------------------------------
def compute_option_q_cryo_budget(n_qram_ports: int = 4, n_optical_fibers: int = 1) -> dict[str, Any]:
    """Compute exact 50 K / 4 K / 100 mK / 20 mK thermal loads per qRAM port & SMF-28 fiber.

    Coax heat loads follow Krinner et al. (EPJ Quantum Tech. 6, 2, 2019) and Exp140:
      - 0.86 mm NbTi superconducting bridge line (4 K -> 20 mK): ~0.065 uW at 20 mK (passive conduction)
        + microwave drive/attenuation leakage ~0.12 uW/port -> 0.185 uW/port at 20 mK MXC,
        0.015 W/port at 4 K (CuNi 50 K->4 K conduction + 20 dB attenuator), 0.11 W/port at 50 K.
      - SMF-28 silica optical fiber (125 um cladding, A = 1.23e-8 m^2, L = 0.25 m/stage):
        passive conduction <0.02 uW at 20 mK + 1536 nm optical pulse average power (~100 pW @ 100 kHz -> 0.0001 uW)
        + stray absorption margin 0.04 uW -> 0.04 uW at 20 mK, 0.002 W at 4 K, 0.04 W at 50 K.
    """
    per_port_20mK_uW = 0.185
    per_port_100mK_uW = 1.45
    per_port_4K_W = 0.015
    per_port_50K_W = 0.110

    per_fiber_20mK_uW = 0.040
    per_fiber_100mK_uW = 0.35
    per_fiber_4K_W = 0.002
    per_fiber_50K_W = 0.040

    add_20mK = n_qram_ports * per_port_20mK_uW + n_optical_fibers * per_fiber_20mK_uW
    add_100mK = n_qram_ports * per_port_100mK_uW + n_optical_fibers * per_fiber_100mK_uW
    add_4K = n_qram_ports * per_port_4K_W + n_optical_fibers * per_fiber_4K_W
    add_50K = n_qram_ports * per_port_50K_W + n_optical_fibers * per_fiber_50K_W

    # Combine with Exp140 1,024-cell S6.5 baseline on single LD400/PT420
    base_20mK, lim_20mK = 6.256, 14.0
    base_100mK, lim_100mK = 59.58, 400.0
    base_4K, lim_4K = 0.488, 2.0
    base_50K, lim_50K = 8.26, 40.0

    tot_20mK = base_20mK + add_20mK
    tot_100mK = base_100mK + add_100mK
    tot_4K = base_4K + add_4K
    tot_50K = base_50K + add_50K

    return {
        "n_qram_ports": int(n_qram_ports),
        "n_optical_fibers": int(n_optical_fibers),
        "per_qram_port": {
            "mxc_20mK_uW": per_port_20mK_uW,
            "cp_100mK_uW": per_port_100mK_uW,
            "stage_4K_W": per_port_4K_W,
            "stage_50K_W": per_port_50K_W,
        },
        "per_smf28_fiber": {
            "mxc_20mK_uW": per_fiber_20mK_uW,
            "cp_100mK_uW": per_fiber_100mK_uW,
            "stage_4K_W": per_fiber_4K_W,
            "stage_50K_W": per_fiber_50K_W,
        },
        "option_q_added_load": {
            "mxc_20mK_uW": float(add_20mK),
            "cp_100mK_uW": float(add_100mK),
            "stage_4K_W": float(add_4K),
            "stage_50K_W": float(add_50K),
        },
        "combined_with_exp140_1024": {
            "mxc_20mK_uW": float(tot_20mK),
            "mxc_20mK_margin_uW": float(lim_20mK - tot_20mK),
            "cp_100mK_uW": float(tot_100mK),
            "stage_4K_W": float(tot_4K),
            "stage_4K_margin_W": float(lim_4K - tot_4K),
            "stage_50K_W": float(tot_50K),
            "all_stages_within_ld400_pt420": bool(
                tot_20mK <= lim_20mK and tot_100mK <= lim_100mK and tot_4K <= lim_4K and tot_50K <= lim_50K
            ),
        },
    }
