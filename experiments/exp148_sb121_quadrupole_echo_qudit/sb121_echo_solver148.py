"""Exp148 (H166) Part 1: Exact 8x8 & 16x16 121Sb (I=7/2) Open-Quantum-System Dynamic Quadrupole Echo Solver.

Resolves Exp142 OQ6 FAIL (500 Hz quadrupole strain collapsing Gross binomial to 0.5855 @ 1 ms) via:
  1. Exact 16x16 electron-nuclear (S=1/2 x I=7/2) and 8x8 nuclear 121Sb Hamiltonians reproducing
     Exp142 NMR spacings (473.90 kHz neutral donor, 70.00 kHz ionized 121Sb+) with CPTP Lindblad
     verification (max |Tr(rho)-1| < 1e-12, min_eig >= -1e-12).
  2. Exact even-odd brickwork SU(8) dynamical decoupling:
       - Q-Echo-4 (C_4 + C_4): 4 segments canceling 100% static I_z^2 quadrupole strain (<1e-12).
       - Q-Echo-8 (P_brick^8 = I_8): 8-cycle visiting all 8 m_I states, canceling BOTH static
         I_z^2 quadrupole strain AND static I_z magnetic noise simultaneously to <1e-12!
  3. Realistic finite-duration multi-tone NMR brickwork pulses (Hann-shaped multi-tone RF drive
     retaining all off-resonant adjacent-transition crosstalk across all 7 transitions) in both
     neutral 121Sb (473.9 kHz spacing) and ionized 121Sb+ (70.0 kHz spacing, speed-vs-leakage wall).
  4. Quasistatic AND colored 1/f^alpha (M=20 log-spaced OU modes, [1 Hz, 100 kHz]) quadrupole
     strain sweep across delta_f_Q in [10, 1000] Hz + T2_eff extraction and 121Sb vs 31P comparison.

Zero hardcoded host paths. Epistemic: no_lab_measurement=True ({Literatür}/{Analitik}/{Model}/{Sayısal-Simülasyon}).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.linalg import eigh, expm

# Fixed physical constants matching Exp142 & predictions_exp148.json
B0_T = 1.5
GAMMA_E_MHZ_T = 28024.95
GAMMA_N_MHZ_T = 10.19
A_SB_MHZ = 186.8
F_Q_NOM_KHZ = 35.0
ETA_Q_NOM = 0.15
T2_MAG_BARE_MS = 20.0
T1_N_S = 100.0
T1_E_S = 1.0


def spin_operators(spin_val: float = 3.5) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exact (2I+1)x(2I+1) spin matrices (Ix, Iy, Iz) in |+I>, ..., |-I> basis."""
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


def build_sb121_models(
    b0_t: float = B0_T,
    a_sb_mhz: float = A_SB_MHZ,
    f_q_khz: float = F_Q_NOM_KHZ,
    eta_q: float = ETA_Q_NOM,
) -> dict[str, Any]:
    """Build exact 16x16 neutral-donor and 8x8 ionized 121Sb Hamiltonians & NMR transition tables."""
    Ix, Iy, Iz = spin_operators(3.5)
    I8 = np.eye(8, dtype=np.complex128)
    I2 = np.eye(2, dtype=np.complex128)
    Sx = 0.5 * np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
    Sy = 0.5 * np.array([[0.0, -1j], [1j, 0.0]], dtype=np.complex128)
    Sz = 0.5 * np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)

    f_q_mhz = f_q_khz * 1e-3
    H_quad = f_q_mhz * (Iz @ Iz - (3.5 * 4.5 / 3.0) * I8) + (eta_q * f_q_mhz / 3.0) * (Ix @ Ix - Iy @ Iy)

    # Full 16x16 neutral 121Sb donor Hamiltonian (MHz)
    H_16 = (
        GAMMA_E_MHZ_T * b0_t * np.kron(Sz, I8)
        - GAMMA_N_MHZ_T * b0_t * np.kron(I2, Iz)
        + a_sb_mhz * (np.kron(Sx, Ix) + np.kron(Sy, Iy) + np.kron(Sz, Iz))
        + np.kron(I2, H_quad)
    )
    evals_16, evecs_16 = eigh(H_16)
    # Lower 8 eigenstates correspond to |down_e, m_I> ordered by energy; sort them into |+7/2>..|-7/2> m_I order!
    v_down = evecs_16[:, :8]
    e_down_raw = evals_16[:8]
    iz_exp = np.real(np.diag(v_down.conj().T @ np.kron(I2, Iz) @ v_down))
    order_m = np.argsort(-iz_exp)  # +7/2 down to -7/2
    e_neutral_mhz = e_down_raw[order_m]
    v_down_ord = v_down[:, order_m]
    # Exact dressed NMR transition frequencies (MHz) between adjacent |k> and |k+1>
    # Note: in |down_e>, E(+7/2) < E(+5/2) < ... < E(-7/2) because -A/2 * m_I lowers +7/2!
    freqs_neutral_mhz = np.abs(np.diff(e_neutral_mhz))
    spacings_neutral_khz = np.diff(np.sort(freqs_neutral_mhz)) * 1e3

    # Exact 8x8 ionized 121Sb+ nuclear Hamiltonian (MHz)
    H_ion_8 = -GAMMA_N_MHZ_T * b0_t * Iz + H_quad
    e_ion_raw, v_ion = eigh(H_ion_8)
    iz_ion = np.real(np.diag(v_ion.conj().T @ Iz @ v_ion))
    ord_ion = np.argsort(-iz_ion)
    e_ion_mhz = e_ion_raw[ord_ion]
    freqs_ion_mhz = np.abs(np.diff(e_ion_mhz))
    spacings_ion_khz = np.diff(np.sort(freqs_ion_mhz)) * 1e3

    # Exact transition dipole matrix elements M_k = |<k|Ix|k+1>|
    m_k = np.array([abs(complex(Ix[k, k + 1])) for k in range(7)], dtype=np.float64)

    return {
        "Ix": Ix,
        "Iy": Iy,
        "Iz": Iz,
        "Iz2": Iz @ Iz,
        "I8": I8,
        "H_16_MHz": H_16,
        "H_ion_8_MHz": H_ion_8,
        "e_neutral_MHz": e_neutral_mhz,
        "freqs_neutral_MHz": freqs_neutral_mhz,
        "min_spacing_neutral_kHz": float(np.min(spacings_neutral_khz)),
        "e_ionized_MHz": e_ion_mhz,
        "freqs_ionized_MHz": freqs_ion_mhz,
        "min_spacing_ionized_kHz": float(np.min(spacings_ion_khz)),
        "transition_dipoles_Mk": m_k,
        "v_down_ord": v_down_ord,
    }


def benchmark_states() -> dict[str, np.ndarray]:
    """Return canonical 8D states: Gross binomial |0_L>, |1_L>, |+_L>, spin-cat |+-7/2>, clock |+-1/2>, edge."""
    c0_gross = np.zeros(8, dtype=np.complex128); c0_gross[0] = math.sqrt(0.3); c0_gross[5] = math.sqrt(0.7)
    c1_gross = np.zeros(8, dtype=np.complex128); c1_gross[2] = math.sqrt(0.7); c1_gross[7] = math.sqrt(0.3)
    cp_gross = (c0_gross + c1_gross) / math.sqrt(2.0)

    cat77 = np.zeros(8, dtype=np.complex128); cat77[0] = 1.0 / math.sqrt(2.0); cat77[7] = 1.0 / math.sqrt(2.0)
    clock12 = np.zeros(8, dtype=np.complex128); clock12[3] = 1.0 / math.sqrt(2.0); clock12[4] = 1.0 / math.sqrt(2.0)
    edge75 = np.zeros(8, dtype=np.complex128); edge75[0] = 1.0 / math.sqrt(2.0); edge75[1] = 1.0 / math.sqrt(2.0)

    return {
        "gross_0L": c0_gross,
        "gross_1L": c1_gross,
        "gross_plusL": cp_gross,
        "spin_cat_pm7_2": cat77,
        "clock_pm1_2": clock12,
        "edge_7_2_5_2": edge75,
    }


# ---------------------------------------------------------------------------
# 1. Exact 8x8 & 16x16 CPTP Lindblad Verification (SQ1)
# ---------------------------------------------------------------------------
def _lindblad_rk4_step(rho: np.ndarray, H_rad_us: np.ndarray, c_ops: list[np.ndarray], dt_us: float) -> np.ndarray:
    def rhs(r: np.ndarray) -> np.ndarray:
        dr = -1j * (H_rad_us @ r - r @ H_rad_us)
        for c in c_ops:
            cd_c = c.conj().T @ c
            dr += c @ r @ c.conj().T - 0.5 * (cd_c @ r + r @ cd_c)
        return dr

    k1 = rhs(rho)
    k2 = rhs(rho + 0.5 * dt_us * k1)
    k3 = rhs(rho + 0.5 * dt_us * k2)
    k4 = rhs(rho + dt_us * k3)
    out = rho + (dt_us / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    return 0.5 * (out + out.conj().T)


def verify_8x8_and_16x16_cptp(models: dict[str, Any]) -> dict[str, Any]:
    """Verify exact CPTP Lindblad preservation in both 8x8 nuclear and 16x16 electron-nuclear spaces."""
    Ix, Iy, Iz = models["Ix"], models["Iy"], models["Iz"]
    I8 = models["I8"]
    I2 = np.eye(2, dtype=np.complex128)
    sm_e = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.complex128)

    # 8x8 exact superoperator expm check over 1 ms with T1n=100 s, T2_mag=20 ms, quadrupole Lindblad
    gamma1_n = 1.0 / (T1_N_S * 1e6)       # us^-1
    gamma_phi_b = 1.0 / (T2_MAG_BARE_MS * 1e3)  # us^-1
    Ip = Ix + 1j * Iy
    Im = Ix - 1j * Iy
    c_ops_8 = [
        math.sqrt(gamma1_n / 15.0) * Im,
        math.sqrt(gamma1_n / 15.0) * Ip,
        math.sqrt(2.0 * gamma_phi_b) * Iz,
    ]
    H_8_rad = 2.0 * math.pi * np.diag(models["e_neutral_MHz"] - models["e_neutral_MHz"][0]) * 1e-3  # small drift for RK4
    # Exact 64x64 Liouvillian expm on 8x8
    L8 = -1j * (np.kron(I8, H_8_rad) - np.kron(H_8_rad.T, I8))
    for c in c_ops_8:
        cdc = c.conj().T @ c
        L8 += np.kron(c.conj(), c) - 0.5 * np.kron(I8, cdc) - 0.5 * np.kron(cdc.T, I8)
    U8 = expm(L8 * 1000.0)  # 1 ms exact CPTP map!
    psi0 = benchmark_states()["gross_0L"]
    rho0_8 = np.outer(psi0, psi0.conj())
    rho1_8 = (U8 @ rho0_8.reshape(-1, order="F")).reshape((8, 8), order="F")
    rho1_8 = 0.5 * (rho1_8 + rho1_8.conj().T)
    tr_err_8 = abs(float(np.trace(rho1_8).real) - 1.0)
    min_eig_8 = float(np.min(np.linalg.eigvalsh(rho1_8)))

    # 16x16 full coupled electron-nuclear Lindblad via exact RK4 in rotating interaction frame
    # (exact dressed eigenbasis of H_16 with electron T1_e=1 s, nuclear T1_n=100 s, magnetic T2=20 ms)
    v_down = models["v_down_ord"]
    psi0_16 = v_down @ psi0
    rho_16 = np.outer(psi0_16, psi0_16.conj())
    gamma1_e = 1.0 / (T1_E_S * 1e6)  # us^-1
    c_ops_16 = [
        math.sqrt(gamma1_e) * np.kron(sm_e, I8),
        math.sqrt(gamma1_n / 15.0) * np.kron(I2, Im),
        math.sqrt(2.0 * gamma_phi_b) * np.kron(I2, Iz),
    ]
    # Rotate into energy eigenframe (drift zero in interaction frame, pure Lindblad dissipation over 1 ms in 100 steps)
    H_zero_16 = np.zeros((16, 16), dtype=np.complex128)
    for _ in range(100):
        rho_16 = _lindblad_rk4_step(rho_16, H_zero_16, c_ops_16, dt_us=10.0)
    tr_err_16 = abs(float(np.trace(rho_16).real) - 1.0)
    min_eig_16 = float(np.min(np.linalg.eigvalsh(rho_16)))
    fid_16_mag_only = float(np.real(psi0_16.conj() @ rho_16 @ psi0_16))

    return {
        "max_trace_err_8x8": float(tr_err_8),
        "min_eig_8x8": float(min_eig_8),
        "max_trace_err_16x16": float(tr_err_16),
        "min_eig_16x16": float(min_eig_16),
        "gross_0L_16x16_1ms_lindblad_mag_fidelity": float(fid_16_mag_only),
    }


# ---------------------------------------------------------------------------
# 2. Exact Even-Odd Brickwork Q-Echo-4 & Q-Echo-8 Sequences (Ideal + Finite Pulse!)
# ---------------------------------------------------------------------------
def build_ideal_brickwork_unitaries() -> dict[str, np.ndarray]:
    """Construct exact SU(8) brickwork swap layers & verify Q-Echo-4 / Q-Echo-8 algebra."""
    # Exact adjacent pi-pulse swap: exp(-i * pi/2 * sigma_x) = -i * sigma_x on pair (k, k+1)
    def _pair_layer(pairs: list[tuple[int, int]]) -> np.ndarray:
        U = np.eye(8, dtype=np.complex128)
        for a, b in pairs:
            U[a, a] = 0.0; U[b, b] = 0.0
            U[a, b] = -1j; U[b, a] = -1j
        return U

    L_even = _pair_layer([(0, 1), (2, 3), (4, 5), (6, 7)])
    L_odd_8 = _pair_layer([(1, 2), (3, 4), (5, 6)])
    L_odd_4 = _pair_layer([(1, 2), (5, 6)])

    # P_brick_8 = L_odd_8 @ L_even -> single 8-cycle (0->2->4->6->7->5->3->1->0)
    P8 = L_odd_8 @ L_even
    # P_brick_4 = L_odd_4 @ L_even -> two disjoint 4-cycles (0->2->3->1->0) & (4->6->7->5->4)
    P4 = L_odd_4 @ L_even

    # Exact frame closure diagonal unitaries so P4^4 @ Z4_close == I_8 and P8^8 @ Z8_close == I_8
    P4_pow4 = np.linalg.matrix_power(P4, 4)
    P8_pow8 = np.linalg.matrix_power(P8, 8)
    Z4_close = P4_pow4.conj().T
    Z8_close = P8_pow8.conj().T

    return {
        "L_even": L_even,
        "L_odd_8": L_odd_8,
        "L_odd_4": L_odd_4,
        "P4": P4,
        "P8": P8,
        "Z4_close": Z4_close,
        "Z8_close": Z8_close,
    }


def verify_qecho_algebraic_cancellation(models: dict[str, Any]) -> dict[str, Any]:
    """Prove Q-Echo-4 cancels I_z^2 (<1e-12) and Q-Echo-8 cancels BOTH I_z^2 & I_z (<1e-12)."""
    bw = build_ideal_brickwork_unitaries()
    Iz, Iz2, I8 = models["Iz"], models["Iz2"], models["I8"]
    tr_iz2_avg = (float(np.trace(Iz2).real) / 8.0) * I8  # (21/4) * I8

    # Average toggled noise Hamiltonian H_bar = (1/K) sum_{r=0}^{K-1} P^{-r} H P^r
    def _avg_toggled(P: np.ndarray, H: np.ndarray, K: int) -> np.ndarray:
        acc = np.zeros_like(H)
        Pk = I8.copy()
        for _ in range(K):
            acc += Pk.conj().T @ H @ Pk
            Pk = P @ Pk
        return acc / float(K)

    avg4_iz2 = _avg_toggled(bw["P4"], Iz2 - tr_iz2_avg, 4)
    avg4_iz = _avg_toggled(bw["P4"], Iz, 4)
    avg8_iz2 = _avg_toggled(bw["P8"], Iz2 - tr_iz2_avg, 8)
    avg8_iz = _avg_toggled(bw["P8"], Iz, 8)

    # Also verify exact static-noise echo unitary fidelity on Gross binomial & spin-cat at dfQ=500 Hz, dfB=50 Hz
    t_tot_ms = 1.0
    H_stat = 2.0 * math.pi * (50e-6 * Iz + 500e-6 * Iz2)  # rad/us
    U_seg8 = expm(-1j * H_stat * (t_tot_ms * 1e3 / 8.0))
    U_tot8 = I8.copy()
    for _ in range(8):
        U_tot8 = bw["P8"] @ U_seg8 @ U_tot8
    U_tot8 = bw["Z8_close"] @ U_tot8
    # Global phase invariant unitary fidelity |Tr(U)|/8
    f_stat_echo8 = float((abs(np.trace(U_tot8)) / 8.0) ** 2)

    return {
        "qecho4_residual_Iz2_fro": float(np.linalg.norm(avg4_iz2)),
        "qecho4_residual_Iz_fro": float(np.linalg.norm(avg4_iz)),
        "qecho8_residual_Iz2_fro": float(np.linalg.norm(avg8_iz2)),
        "qecho8_residual_Iz_fro": float(np.linalg.norm(avg8_iz)),
        "qecho8_closure_err_fro": float(np.linalg.norm(bw["Z8_close"] @ np.linalg.matrix_power(bw["P8"], 8) - I8)),
        "qecho8_static_500Hz_process_fidelity": f_stat_echo8,
    }


def simulate_finite_multitone_layer(
    freqs_mhz: np.ndarray,
    m_k: np.ndarray,
    active_tones: list[int],
    omega_peak_khz: float,
    df_b_mhz: float = 0.0,
    df_q_mhz: float = 0.0,
    pulse_type: str = "hann_pi",
    phase_rad: float = 0.0,
    edge_frac: float = 0.22,
) -> tuple[np.ndarray, float]:
    """Exact anti-aliased 8x8 interaction-picture evolution of a finite multi-tone NMR layer.

    Retains ALL off-resonant cross-terms between every active tone k in `active_tones` and every
    adjacent transition j in {0..6} at exact detuning (f_j - f_k), plus real noise (df_b, df_q)
    acting continuously during the finite pulse. Uses adaptive dt <= 1/(12 * max_beat) with batched
    exact 8x8 Hermitian eigendecomposition so the 2.93 MHz max beat in neutral 121Sb has zero aliasing.

    Supported `pulse_type`:
      - "hann_pi": single Hann-enveloped pi-pulse (mean=0.5 -> t_p = 1/f_peak)
      - "tukey_pi": smooth Tukey flat-top pi-pulse (edge_frac ramps, mean=1-edge_frac)
      - "composite_90_240_90": smooth Tukey-edged Levitt-Freeman 90_phi - 240_{phi+pi/2} - 90_phi
        off-resonance-compensated inversion pulse canceling outer-transition quadrupole detuning to O((Delta/Omega)^4).
    """
    f_peak_mhz = omega_peak_khz * 1e-3
    h_peak = math.pi * f_peak_mhz  # H_{k,k+1} peak = 0.5 * 2*pi*f_peak = pi * f_peak
    max_beat = float(np.max(freqs_mhz) - np.min(freqs_mhz))
    w_trans = 2.0 * math.pi * freqs_mhz
    iz_d = np.array([3.5 - k for k in range(8)], dtype=np.float64)
    h_diag = 2.0 * math.pi * (df_b_mhz * iz_d + df_q_mhz * (iz_d ** 2))
    tone_w = np.array([w_trans[k] for k in active_tones], dtype=np.float64)
    tone_amp_norm = np.array([1.0 / m_k[k] for k in active_tones], dtype=np.float64)
    det = w_trans[:, None] - tone_w[None, :]  # (7, n_tones)

    if pulse_type == "hann_pi":
        segs = [(math.pi, phase_rad, "hann")]
    elif pulse_type == "tukey_pi":
        segs = [(math.pi, phase_rad, "tukey")]
    elif pulse_type == "composite_90_240_90":
        segs = [
            (0.5 * math.pi, phase_rad, "tukey"),
            (4.0 * math.pi / 3.0, phase_rad + 0.5 * math.pi, "tukey"),
            (0.5 * math.pi, phase_rad, "tukey"),
        ]
    else:
        raise ValueError(f"Unknown pulse_type: {pulse_type}")

    U = np.eye(8, dtype=np.complex128)
    t_cum = 0.0
    idx = np.arange(8)
    jidx = np.arange(7)

    for angle_rad, ph, shape in segs:
        mean_env = 0.5 if shape == "hann" else (1.0 - edge_frac)
        t_seg = angle_rad / (2.0 * h_peak * mean_env)
        n_steps = max(120, int(math.ceil(t_seg * max_beat * 12.0)))
        dt = t_seg / float(n_steps)
        u = (np.arange(n_steps) + 0.5) / float(n_steps)
        tm = t_cum + u * t_seg

        if shape == "hann":
            env = 0.5 * (1.0 - np.cos(2.0 * math.pi * u))
        else:
            env = np.ones(n_steps, dtype=np.float64)
            if edge_frac > 0.0:
                left = u < edge_frac
                right = u > (1.0 - edge_frac)
                env[left] = 0.5 * (1.0 - np.cos(math.pi * u[left] / edge_frac))
                env[right] = 0.5 * (1.0 - np.cos(math.pi * (1.0 - u[right]) / edge_frac))

        phases = np.exp(1j * (tm[:, None, None] * det[None, :, :] - ph))
        off = h_peak * env[:, None] * m_k[None, :] * np.sum(tone_amp_norm[None, None, :] * phases, axis=2)

        H_all = np.zeros((n_steps, 8, 8), dtype=np.complex128)
        H_all[:, idx, idx] = h_diag[None, :]
        H_all[:, jidx, jidx + 1] = off
        H_all[:, jidx + 1, jidx] = off.conj()

        w, v = np.linalg.eigh(H_all)
        ew = np.exp(-1j * w * dt)
        Us = np.einsum("sij,sj,skj->sik", v, ew, v.conj())
        for k in range(n_steps):
            U = Us[k] @ U
        t_cum += t_seg

    return U, float(t_cum)


def evaluate_finite_pulse_brickwork(
    freqs_mhz: np.ndarray,
    m_k: np.ndarray,
    omega_peak_khz: float,
    t_total_ms: float = 1.0,
    df_b_mhz: float = 0.0,
    df_q_mhz: float = 0.0,
    pulse_type: str = "composite_90_240_90",
    phase_cycling: str = "quadrature_alt",
    edge_frac: float = 0.22,
    z_cal_override: np.ndarray | None = None,
) -> dict[str, Any]:
    """Evaluate 1 full finite-pulse multi-tone Q-Echo-8 cycle over t_total_ms with symmetric wait & virtual-Z cal."""
    if phase_cycling == "none":
        ph_ev = [0.0] * 8
        ph_od = [0.0] * 8
    elif phase_cycling == "quadrature_alt":
        # Quadrature alternating phase cycling: even layers (0, pi), odd layers (pi/2, 3pi/2)
        ph_ev = [0.0, math.pi] * 4
        ph_od = [0.5 * math.pi, 1.5 * math.pi] * 4
    else:
        raise ValueError(f"Unknown phase_cycling: {phase_cycling}")

    # Cache unique noiseless layers (at most 2 even + 2 odd!) for fast deterministic AC-Stark calibration
    cache0: dict[tuple[str, float], np.ndarray] = {}
    tp_us = 0.0
    U_cyc_0 = np.eye(8, dtype=np.complex128)
    for pe, po in zip(ph_ev, ph_od):
        if ("e", pe) not in cache0:
            cache0[("e", pe)], tp_us = simulate_finite_multitone_layer(
                freqs_mhz, m_k, [0, 2, 4, 6], omega_peak_khz, 0.0, 0.0, pulse_type, pe, edge_frac
            )
        if ("o", po) not in cache0:
            cache0[("o", po)], _ = simulate_finite_multitone_layer(
                freqs_mhz, m_k, [1, 3, 5], omega_peak_khz, 0.0, 0.0, pulse_type, po, edge_frac
            )
        U_cyc_0 = (cache0[("o", po)] @ cache0[("e", pe)]) @ U_cyc_0

    if z_cal_override is not None:
        Z_cal = z_cal_override
    else:
        Z_cal = np.diag(np.exp(-1j * np.angle(np.diag(U_cyc_0))))
    f_noiseless_proc = float((abs(np.trace(Z_cal @ U_cyc_0)) / 8.0) ** 2)

    pulse_total_us = 16.0 * tp_us
    t_tot_us = t_total_ms * 1e3
    tau_seg_us = max(0.0, (t_tot_us - pulse_total_us) / 8.0)
    actual_total_us = pulse_total_us + 8.0 * tau_seg_us

    if abs(df_b_mhz) < 1e-15 and abs(df_q_mhz) < 1e-15:
        U_tot = Z_cal @ U_cyc_0
    else:
        iz_d = np.array([3.5 - k for k in range(8)], dtype=np.float64)
        U_wait_half = np.diag(
            np.exp(-1j * 2.0 * math.pi * (df_b_mhz * iz_d + df_q_mhz * (iz_d ** 2)) * (0.5 * tau_seg_us))
        )
        cache_n: dict[tuple[str, float], np.ndarray] = {}
        U_run = np.eye(8, dtype=np.complex128)
        for pe, po in zip(ph_ev, ph_od):
            if ("e", pe) not in cache_n:
                cache_n[("e", pe)], _ = simulate_finite_multitone_layer(
                    freqs_mhz, m_k, [0, 2, 4, 6], omega_peak_khz, df_b_mhz, df_q_mhz, pulse_type, pe, edge_frac
                )
            if ("o", po) not in cache_n:
                cache_n[("o", po)], _ = simulate_finite_multitone_layer(
                    freqs_mhz, m_k, [1, 3, 5], omega_peak_khz, df_b_mhz, df_q_mhz, pulse_type, po, edge_frac
                )
            U_run = U_wait_half @ (cache_n[("o", po)] @ cache_n[("e", pe)]) @ U_wait_half @ U_run
        U_tot = Z_cal @ U_run

    return {
        "omega_peak_kHz": float(omega_peak_khz),
        "pulse_type": pulse_type,
        "phase_cycling": phase_cycling,
        "t_pulse_single_us": float(tp_us),
        "t_pulses_total_us": float(pulse_total_us),
        "tau_seg_us": float(tau_seg_us),
        "actual_total_ms": float(actual_total_us * 1e-3),
        "noiseless_cycle_process_fidelity": f_noiseless_proc,
        "Z_cal": Z_cal,
        "U_tot": U_tot,
    }


# ---------------------------------------------------------------------------
# 3. Quasistatic & Colored 1/f^alpha Multi-OU Strain Noise Engine (SQ3, SQ4, SQ5)
# ---------------------------------------------------------------------------
def build_multi_ou_1f_params(
    rms_hz: float,
    f_min_hz: float = 1.0,
    f_max_hz: float = 1e5,
    n_modes: int = 20,
    alpha: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Construct M=20 log-spaced OU decay rates gamma_m (s^-1) and mode stds sigma_m (Hz) for 1/f^alpha PSD."""
    freqs = np.logspace(math.log10(f_min_hz), math.log10(f_max_hz), n_modes)
    gammas = 2.0 * math.pi * freqs  # rad/s
    # For 1/f^alpha over log-spaced modes, variance weight per log-bin scales as f^(1 - alpha)
    weights = freqs ** (1.0 - alpha)
    weights = weights / np.sum(weights)
    sigmas = rms_hz * np.sqrt(weights)
    return gammas, sigmas


def sample_ou_trajectories(
    gammas_s: np.ndarray,
    sigmas_hz: np.ndarray,
    n_traj: int,
    n_steps: int,
    dt_s: float,
    seed: int,
) -> np.ndarray:
    """Exact stationary multi-OU generator returning [n_traj, n_steps] noise trajectories in Hz."""
    rng = np.random.default_rng(seed)
    m = len(gammas_s)
    phi = np.exp(-gammas_s * dt_s)  # (m,)
    innov = sigmas_hz * np.sqrt(np.maximum(0.0, 1.0 - phi * phi))  # (m,)

    # Initialize from exact stationary distribution N(0, sigma_m^2)
    x = rng.normal(0.0, 1.0, size=(n_traj, m)) * sigmas_hz[None, :]
    out = np.empty((n_traj, n_steps), dtype=np.float64)
    for s in range(n_steps):
        out[:, s] = np.sum(x, axis=1)
        x = x * phi[None, :] + rng.normal(0.0, 1.0, size=(n_traj, m)) * innov[None, :]
    return out


def _eval_ideal_echo_trajectory_fidelities(
    df_b_hz: np.ndarray,
    df_q_hz: np.ndarray,
    dt_s: float,
    protocol: str,
    states: dict[str, np.ndarray],
) -> dict[str, float]:
    """Vectorized exact fidelity evaluation over [n_traj, n_steps] trajectories for Bare / Q-Echo-4 / Q-Echo-8 / N-cycle.

    Because the brickwork permutation maps each basis state k deterministically through a sequence
    of m_I(k, seg) values on each equal segment, the total accumulated diagonal phase for basis state k
    is EXACTLY:
      phi_k = 2*pi * dt_s * sum_t [ df_b(t) * m(k, t) + df_q(t) * m(k, t)^2 ]!
    """
    n_traj, n_steps = df_q_hz.shape
    ms = np.array([3.5 - k for k in range(8)], dtype=np.float64)
    # Brickwork permutations as index maps (where basis state k sits after r applications of P)
    p8_perm = [2, 0, 4, 1, 6, 3, 7, 5]  # verify: 0->2->4->6->7->5->3->1->0!
    p4_perm = [2, 0, 3, 1, 6, 4, 7, 5]  # verify: 0->2->3->1->0 and 4->6->7->5->4!

    if protocol == "bare":
        n_segs = 1
        perm_seq = [list(range(8))]
    elif protocol == "qecho4":
        n_segs = 4
        perm_seq = []
        cur = list(range(8))
        for _ in range(4):
            perm_seq.append(cur)
            cur = [p4_perm[i] for i in cur]
    elif protocol.startswith("qecho8"):
        # Supports qecho8 (1 cycle = 8 segs), qecho8_x2 (16 segs), qecho8_x4 (32 segs)
        n_cyc = 1
        if "_x" in protocol:
            n_cyc = int(protocol.split("_x")[1])
        n_segs = 8 * n_cyc
        perm_seq = []
        cur = list(range(8))
        for _ in range(n_segs):
            perm_seq.append(cur)
            cur = [p8_perm[i] for i in cur]
    else:
        raise ValueError(f"Unknown protocol: {protocol}")

    # Map each time step s in 0..n_steps-1 to its segment index in 0..n_segs-1
    seg_idx = np.minimum((np.arange(n_steps) * n_segs) // n_steps, n_segs - 1)
    # Precompute m_mat [n_steps, 8] and m2_mat [n_steps, 8]
    perm_arr = np.array(perm_seq, dtype=int)  # (n_segs, 8)
    idx_t = perm_arr[seg_idx]                 # (n_steps, 8)
    m_t = ms[idx_t]                           # (n_steps, 8)
    m2_t = m_t * m_t                          # (n_steps, 8)

    # Accumulated phase [n_traj, 8] in radians
    phases = (2.0 * math.pi * dt_s) * (df_b_hz @ m_t + df_q_hz @ m2_t)  # (n_traj, 8)
    exp_ph = np.exp(-1j * phases)  # (n_traj, 8)

    fids: dict[str, float] = {}
    for name, psi in states.items():
        # |<psi | exp(-i diag(phi)) | psi>|^2 = |sum_k |psi_k|^2 exp(-i phi_k)|^2
        w = np.abs(psi) ** 2  # (8,)
        overlaps = exp_ph @ w  # (n_traj,)
        fids[name] = float(np.mean(np.abs(overlaps) ** 2))
    return fids


def exact_ou_phase_variance(
    gammas_s: np.ndarray,
    sigmas_hz: np.ndarray,
    w_segs: np.ndarray,
    tau_s: float,
) -> float:
    """Exact closed-form Gaussian phase variance Var(2*pi * int_0^T x(t) w(t) dt) for multi-OU noise.

    For piecewise-constant segment weights `w_segs` on S equal intervals of length `tau_s`,
    E[x_m(t1) x_m(t2)] = sigma_m^2 * exp(-gamma_m |t1 - t2|) integrates analytically to machine precision,
    eliminating Monte Carlo sampling variance in 1/f filter-function evaluation!
    """
    S = len(w_segs)
    idx = np.arange(S)
    dist = np.abs(idx[:, None] - idx[None, :])
    var_tot = 0.0
    for gm, sm in zip(gammas_s, sigmas_hz):
        g = float(gm) * tau_s
        if g < 1e-6:
            i0 = (tau_s ** 2) * (1.0 - g / 3.0 + (g * g) / 12.0)
            c_fac = tau_s * (1.0 - 0.5 * g + (g * g) / 6.0)
        else:
            eg = math.exp(-g)
            i0 = (2.0 / (float(gm) ** 2)) * (g - 1.0 + eg)
            c_fac = (1.0 - eg) / float(gm)
        K = np.where(dist == 0, i0, (c_fac * c_fac) * np.exp(-g * np.maximum(dist - 1, 0)))
        var_tot += (float(sm) ** 2) * float(w_segs @ K @ w_segs)
    return float(((2.0 * math.pi) ** 2) * var_tot)


def exact_gaussian_echo_fidelities(
    gammas_b: np.ndarray,
    sigmas_b: np.ndarray,
    gammas_q: np.ndarray,
    sigmas_q: np.ndarray,
    t_total_s: float,
    protocol: str,
    states: dict[str, np.ndarray],
) -> dict[str, float]:
    """Exact closed-form Gaussian expectation E[|<psi|exp(-i diag(Phi))|psi>|^2] for any static or multi-OU process.

    Since Phi_a - Phi_b is zero-mean Gaussian with exact variance V_{ab},
      E[|<psi|U|psi>|^2] = sum_{a,b} |psi_a|^2 |psi_b|^2 exp(-0.5 * V_{ab})!
    """
    ms = np.array([3.5 - k for k in range(8)], dtype=np.float64)
    p8_perm = [2, 0, 4, 1, 6, 3, 7, 5]
    p4_perm = [2, 0, 3, 1, 6, 4, 7, 5]

    if protocol == "bare":
        perm_seq = [list(range(8))]
    elif protocol == "qecho4":
        perm_seq = []
        cur = list(range(8))
        for _ in range(4):
            perm_seq.append(cur)
            cur = [p4_perm[i] for i in cur]
    elif protocol.startswith("qecho8"):
        n_cyc = int(protocol.split("_x")[1]) if "_x" in protocol else 1
        perm_seq = []
        cur = list(range(8))
        for _ in range(8 * n_cyc):
            perm_seq.append(cur)
            cur = [p8_perm[i] for i in cur]
    else:
        raise ValueError(f"Unknown protocol: {protocol}")

    perm_arr = np.array(perm_seq, dtype=int)  # (S, 8)
    S = perm_arr.shape[0]
    tau_s = t_total_s / float(S)
    m_mat = ms[perm_arr]      # (S, 8)
    m2_mat = m_mat * m_mat    # (S, 8)

    # Precompute 8x8 covariance matrix of Phi_a - Phi_b for all pairs (a, b) needed by benchmark states
    fids: dict[str, float] = {}
    pair_cache: dict[tuple[int, int], float] = {}
    for name, psi in states.items():
        w = np.abs(psi) ** 2
        nz = [int(i) for i in range(8) if w[i] > 1e-15]
        acc = 0.0
        for a in nz:
            for b in nz:
                if a == b:
                    acc += float(w[a] * w[b])
                else:
                    key = (min(a, b), max(a, b))
                    if key not in pair_cache:
                        dm = m_mat[:, a] - m_mat[:, b]
                        dm2 = m2_mat[:, a] - m2_mat[:, b]
                        vb = exact_ou_phase_variance(gammas_b, sigmas_b, dm, tau_s) if len(gammas_b) else 0.0
                        vq = exact_ou_phase_variance(gammas_q, sigmas_q, dm2, tau_s) if len(gammas_q) else 0.0
                        pair_cache[key] = math.exp(-0.5 * (vb + vq))
                    acc += float(w[a] * w[b]) * pair_cache[key]
        fids[name] = float(acc)
    return fids


def run_quasistatic_and_1f_benchmarks(models: dict[str, Any]) -> dict[str, Any]:
    """Run full quasistatic (Exp142 anchor + 3 finite-pulse tiers) and colored 1/f sweeps."""
    states = benchmark_states()
    sigma_b_hz = 1.0 / (math.sqrt(2.0) * math.pi * (T2_MAG_BARE_MS * 1e-3))  # 11.254 Hz for T2_mag=20 ms

    # 1. Exact Quasistatic Benchmark at Exp142 anchor (delta_f_Q = 500 Hz, T2_mag = 20 ms, t = 1 ms)
    #    Computed via exact closed-form Gaussian expectation (gamma -> 0) AND cross-checked with N_mc = 16000!
    g_zero = np.array([1e-12], dtype=np.float64)
    qs_bare = exact_gaussian_echo_fidelities(
        g_zero, np.array([sigma_b_hz]), g_zero, np.array([500.0]), 1e-3, "bare", states
    )
    qs_q4 = exact_gaussian_echo_fidelities(
        g_zero, np.array([sigma_b_hz]), g_zero, np.array([500.0]), 1e-3, "qecho4", states
    )
    qs_q8_ideal = exact_gaussian_echo_fidelities(
        g_zero, np.array([sigma_b_hz]), g_zero, np.array([500.0]), 1e-3, "qecho8", states
    )
    # High-N Monte Carlo cross-check of exact analytical expectation (N_mc = 16000)
    rng = np.random.default_rng(14801)
    n_mc = 16000
    dfq_grid = np.repeat(rng.normal(0.0, 500.0, size=(n_mc, 1)), 8, axis=1)
    dfb_grid = np.repeat(rng.normal(0.0, sigma_b_hz, size=(n_mc, 1)), 8, axis=1)
    qs_bare_mc = _eval_ideal_echo_trajectory_fidelities(dfb_grid, dfq_grid, 1e-3 / 8.0, "bare", states)
    qs_mc_max_err = max(abs(qs_bare[k] - qs_bare_mc[k]) for k in states)

    # Real finite-pulse multi-tone brickwork Q-Echo-8 under 500 Hz quasistatic strain + 20 ms magnetic noise!
    # Neutral 121Sb donor (473.9 kHz spacing, Omega_peak = 25.0 kHz) — compare ALL 3 finite-pulse tiers:
    #   Tier A: Simple uncompensated Hann pi-pulse brickwork (no phase cycling)
    #   Tier B: Quadrature phase-cycled smooth Tukey pi-pulse brickwork
    #   Tier C: Quadrature phase-cycled Levitt-Freeman composite 90-240-90 brickwork (cancels 3 kHz outer-transition detuning!)
    n_fp_mc = 24
    rng_fp = np.random.default_rng(14802)
    dfq_fp = rng_fp.normal(0.0, 500.0, size=n_fp_mc) * 1e-6  # MHz
    dfb_fp = rng_fp.normal(0.0, sigma_b_hz, size=n_fp_mc) * 1e-6  # MHz

    def _run_fp_tier(pulse_type: str, phase_cycling: str) -> tuple[dict[str, float], dict[str, Any]]:
        ev0 = evaluate_finite_pulse_brickwork(
            models["freqs_neutral_MHz"], models["transition_dipoles_Mk"],
            omega_peak_khz=25.0, t_total_ms=1.0, df_b_mhz=0.0, df_q_mhz=0.0,
            pulse_type=pulse_type, phase_cycling=phase_cycling,
        )
        z_cal = ev0["Z_cal"]
        meta = {k: v for k, v in ev0.items() if k not in ("U_tot", "Z_cal")}
        acc = {k: [] for k in states}
        proc_list = []
        for db, dfq in zip(dfb_fp, dfq_fp):
            ev = evaluate_finite_pulse_brickwork(
                models["freqs_neutral_MHz"], models["transition_dipoles_Mk"],
                omega_peak_khz=25.0, t_total_ms=1.0, df_b_mhz=float(db), df_q_mhz=float(dfq),
                pulse_type=pulse_type, phase_cycling=phase_cycling, z_cal_override=z_cal,
            )
            U = ev["U_tot"]
            proc_list.append(float((abs(np.trace(U)) / 8.0) ** 2))
            for name, psi in states.items():
                acc[name].append(float(abs(complex(psi.conj() @ U @ psi)) ** 2))
        out_f = {k: float(np.mean(v)) for k, v in acc.items()}
        out_f["process_fidelity_mean"] = float(np.mean(proc_list))
        return out_f, meta

    qs_q8_fp_hann, fp_meta_hann = _run_fp_tier("hann_pi", "none")
    qs_q8_fp_tukey, fp_meta_tukey = _run_fp_tier("tukey_pi", "quadrature_alt")
    qs_q8_finite_neutral, fp_meta = _run_fp_tier("composite_90_240_90", "quadrature_alt")

    # Neutral vs Ionized 121Sb+ RF crosstalk speed-vs-leakage sweep (70.0 kHz vs 473.9 kHz spacing, Omega in {5,10,15,25} kHz)
    ionized_crosstalk_sweep = []
    for om_khz in [5.0, 10.0, 15.0, 25.0]:
        ev_ion_h = evaluate_finite_pulse_brickwork(
            models["freqs_ionized_MHz"], models["transition_dipoles_Mk"],
            omega_peak_khz=om_khz, t_total_ms=max(1.0, 16.0 / om_khz + 0.1),
            df_b_mhz=0.0, df_q_mhz=0.0, pulse_type="hann_pi", phase_cycling="none",
        )
        ev_ion_c = evaluate_finite_pulse_brickwork(
            models["freqs_ionized_MHz"], models["transition_dipoles_Mk"],
            omega_peak_khz=om_khz, t_total_ms=max(1.0, 38.0 / om_khz + 0.1),
            df_b_mhz=0.0, df_q_mhz=0.0, pulse_type="composite_90_240_90", phase_cycling="quadrature_alt",
        )
        ev_neu_h = evaluate_finite_pulse_brickwork(
            models["freqs_neutral_MHz"], models["transition_dipoles_Mk"],
            omega_peak_khz=om_khz, t_total_ms=max(1.0, 16.0 / om_khz + 0.1),
            df_b_mhz=0.0, df_q_mhz=0.0, pulse_type="hann_pi", phase_cycling="none",
        )
        ev_neu_c = evaluate_finite_pulse_brickwork(
            models["freqs_neutral_MHz"], models["transition_dipoles_Mk"],
            omega_peak_khz=om_khz, t_total_ms=max(1.0, 38.0 / om_khz + 0.1),
            df_b_mhz=0.0, df_q_mhz=0.0, pulse_type="composite_90_240_90", phase_cycling="quadrature_alt",
        )
        U_ion_h = ev_ion_h["U_tot"]
        f_gross_ion = float(abs(complex(states["gross_0L"].conj() @ U_ion_h @ states["gross_0L"])) ** 2)
        ionized_crosstalk_sweep.append({
            "omega_peak_kHz": om_khz,
            "t_pulse_hann_us": ev_ion_h["t_pulse_single_us"],
            "t_pulses_16_hann_ms": ev_ion_h["t_pulses_total_us"] * 1e-3,
            "t_pulses_16_composite_ms": ev_ion_c["t_pulses_total_us"] * 1e-3,
            "ionized_hann_process_fidelity": ev_ion_h["noiseless_cycle_process_fidelity"],
            "ionized_composite_process_fidelity": ev_ion_c["noiseless_cycle_process_fidelity"],
            "ionized_gross_0L_hann_fidelity": f_gross_ion,
            "ionized_crosstalk_infidelity": float(1.0 - ev_ion_h["noiseless_cycle_process_fidelity"]),
            "neutral_hann_process_fidelity": ev_neu_h["noiseless_cycle_process_fidelity"],
            "neutral_composite_process_fidelity": ev_neu_c["noiseless_cycle_process_fidelity"],
        })

    # 2. Colored 1/f^alpha Multi-OU Strain Noise Sweep across delta_f_Q in [10, 1000] Hz at t = 1 ms
    #    Uses EXACT analytical Gaussian multi-OU covariance (zero MC noise!) + cross-check with N=2048 MC!
    dfq_list = [10.0, 50.0, 100.0, 250.0, 500.0, 750.0, 1000.0]
    gammas_q, unit_sigmas_q = build_multi_ou_1f_params(1.0, f_min_hz=1.0, f_max_hz=1e5, n_modes=20, alpha=1.0)
    gammas_b, sigmas_b = build_multi_ou_1f_params(sigma_b_hz, f_min_hz=1.0, f_max_hz=1e4, n_modes=16, alpha=1.0)

    # Cross-check exact analytical formula vs N=2048 trajectory MC at delta_f_Q = 100 Hz, Q-Echo-8
    n_ou_steps = 128
    dt_ou = 1e-3 / float(n_ou_steps)
    mc_q100 = 100.0 * sample_ou_trajectories(gammas_q, unit_sigmas_q, 2048, n_ou_steps, dt_ou, seed=14810)
    mc_b = sample_ou_trajectories(gammas_b, sigmas_b, 2048, n_ou_steps, dt_ou, seed=14811)
    mc_q8_100 = _eval_ideal_echo_trajectory_fidelities(mc_b, mc_q100, dt_ou, "qecho8", states)

    colored_1f_sweep = []
    for dfq_rms in dfq_list:
        sq = dfq_rms * unit_sigmas_q
        fb = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq, 1e-3, "bare", states)
        fq4 = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq, 1e-3, "qecho4", states)
        fq8 = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq, 1e-3, "qecho8", states)
        fq16 = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq, 1e-3, "qecho8_x2", states)
        fq32 = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq, 1e-3, "qecho8_x4", states)
        fq64 = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq, 1e-3, "qecho8_x8", states)
        colored_1f_sweep.append({
            "delta_f_Q_rms_Hz": dfq_rms,
            "bare_gross_0L": fb["gross_0L"],
            "qecho4_gross_0L": fq4["gross_0L"],
            "qecho8_gross_0L": fq8["gross_0L"],
            "qecho16_gross_0L": fq16["gross_0L"],
            "qecho32_gross_0L": fq32["gross_0L"],
            "qecho64_gross_0L": fq64["gross_0L"],
            "bare_cat77": fb["spin_cat_pm7_2"],
            "qecho8_cat77": fq8["spin_cat_pm7_2"],
            "qecho32_cat77": fq32["spin_cat_pm7_2"],
            "bare_clock12": fb["clock_pm1_2"],
            "qecho8_clock12": fq8["clock_pm1_2"],
        })

    ou_exact_100 = [r["qecho8_gross_0L"] for r in colored_1f_sweep if abs(r["delta_f_Q_rms_Hz"] - 100.0) < 1e-6][0]
    ou_mc_crosscheck_err = abs(ou_exact_100 - mc_q8_100["gross_0L"])

    # 3. Exact Time-Decay Curves at delta_f_Q = 500 Hz (1/f noise) + Exact Bisection T2_eff extraction!
    t_grid_ms = [0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0, 1.5, 2.0, 5.0, 10.0, 20.0]
    decay_curves: dict[str, list[float]] = {
        k: []
        for k in ("bare_gross", "qecho8_gross", "qecho16_gross", "qecho32_gross", "qecho64_gross", "bare_cat77", "qecho8_cat77", "bare_clock12")
    }
    sq_500 = 500.0 * unit_sigmas_q
    for t_ms in t_grid_ms:
        t_s = t_ms * 1e-3
        fb = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq_500, t_s, "bare", states)
        f8 = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq_500, t_s, "qecho8", states)
        f16 = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq_500, t_s, "qecho8_x2", states)
        f32 = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq_500, t_s, "qecho8_x4", states)
        f64 = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq_500, t_s, "qecho8_x8", states)
        decay_curves["bare_gross"].append(fb["gross_0L"])
        decay_curves["qecho8_gross"].append(f8["gross_0L"])
        decay_curves["qecho16_gross"].append(f16["gross_0L"])
        decay_curves["qecho32_gross"].append(f32["gross_0L"])
        decay_curves["qecho64_gross"].append(f64["gross_0L"])
        decay_curves["bare_cat77"].append(fb["spin_cat_pm7_2"])
        decay_curves["qecho8_cat77"].append(f8["spin_cat_pm7_2"])
        decay_curves["bare_clock12"].append(fb["clock_pm1_2"])

    def _exact_t2_bisect_ms(protocol: str, state_key: str, f_inf: float, hi_ms: float = 100.0) -> float:
        thresh = f_inf + (1.0 - f_inf) * math.exp(-1.0)
        lo, hi = 1e-3, hi_ms
        f_hi = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq_500, hi * 1e-3, protocol, {state_key: states[state_key]})[state_key]
        if f_hi >= thresh:
            return float(hi)
        for _ in range(36):
            mid = 0.5 * (lo + hi)
            fm = exact_gaussian_echo_fidelities(gammas_b, sigmas_b, gammas_q, sq_500, mid * 1e-3, protocol, {state_key: states[state_key]})[state_key]
            if fm > thresh:
                lo = mid
            else:
                hi = mid
        return float(0.5 * (lo + hi))

    f_inf_gross = 0.3 ** 2 + 0.7 ** 2  # 0.580 exact infinite-time dephasing floor of Gross |0_L>
    t2_eff = {
        "bare_gross_ms": _exact_t2_bisect_ms("bare", "gross_0L", f_inf_gross),
        "qecho8_gross_ms": _exact_t2_bisect_ms("qecho8", "gross_0L", f_inf_gross),
        "qecho16_gross_ms": _exact_t2_bisect_ms("qecho8_x2", "gross_0L", f_inf_gross),
        "qecho32_gross_ms": _exact_t2_bisect_ms("qecho8_x4", "gross_0L", f_inf_gross),
        "qecho64_gross_ms": _exact_t2_bisect_ms("qecho8_x8", "gross_0L", f_inf_gross),
        "bare_cat77_ms": _exact_t2_bisect_ms("bare", "spin_cat_pm7_2", 0.50),
        "qecho8_cat77_ms": _exact_t2_bisect_ms("qecho8", "spin_cat_pm7_2", 0.50),
        "bare_clock12_ms": _exact_t2_bisect_ms("bare", "clock_pm1_2", 0.50),
    }
    t2_eff["gross_gain_qecho8_vs_bare"] = float(t2_eff["qecho8_gross_ms"] / max(t2_eff["bare_gross_ms"], 1e-9))
    t2_eff["gross_gain_qecho16_vs_bare"] = float(t2_eff["qecho16_gross_ms"] / max(t2_eff["bare_gross_ms"], 1e-9))
    t2_eff["gross_gain_qecho32_vs_bare"] = float(t2_eff["qecho32_gross_ms"] / max(t2_eff["bare_gross_ms"], 1e-9))
    t2_eff["gross_gain_qecho64_vs_bare"] = float(t2_eff["qecho64_gross_ms"] / max(t2_eff["bare_gross_ms"], 1e-9))

    return {
        "quasistatic_500Hz_1ms": {
            "bare": qs_bare,
            "bare_mc16000_crosscheck_max_err": float(qs_mc_max_err),
            "qecho4_ideal": qs_q4,
            "qecho8_ideal": qs_q8_ideal,
            "qecho8_finite_hann_no_cycle_25kHz": qs_q8_fp_hann,
            "qecho8_finite_tukey_quad_25kHz": qs_q8_fp_tukey,
            "qecho8_finite_neutral_25kHz": qs_q8_finite_neutral,
            "finite_pulse_meta_hann": fp_meta_hann,
            "finite_pulse_meta_tukey": fp_meta_tukey,
            "finite_pulse_meta_neutral": fp_meta,
        },
        "ionized_crosstalk_sweep": ionized_crosstalk_sweep,
        "colored_1f_delta_fQ_sweep_1ms": colored_1f_sweep,
        "colored_1f_ou_mc2048_crosscheck_err": float(ou_mc_crosscheck_err),
        "colored_1f_500Hz_decay_curves": {
            "t_ms": t_grid_ms,
            "curves": decay_curves,
            "T2_eff_ms": t2_eff,
        },
    }
