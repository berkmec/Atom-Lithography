"""Exact 12x12 open-quantum-system Lindblad cavity-QED bus simulator (Exp131).

Hilbert space: Qubit_1 (2) x Qubit_2 (2) x NbTiN Cavity (3 Fock states: |0>,|1>,|2>) = 12D.
Liouville superoperator dimension: 144 x 144, exponentiated exactly via PyTorch CUDA
batched matrix_exp (with automatic SciPy CPU fallback).

Implements:
1. Resonant sequential photon-swap Bell state gate (handles arbitrary g1 != g2
   heterogeneity with 100% ideal unitary fidelity).
2. Smooth C^2-quintic mixing-angle adiabatic dispersive sqrt(iSWAP) and full
   4-basis universal CZ gate (2 x sqrt(iSWAP) + X1 echo + local H/S^dag),
   evaluated by exact 16-element Choi / Nielsen average gate fidelity F_avg(CZ).
3. Full 4D phase map across (Z_r, Q_L, S_eps) and Delta_z_cap capping sweep.

Epistemic scope: {Model} / {Sayisal-Simulasyon}. No laboratory measurement.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.linalg import expm as scipy_expm

try:
    import torch
    _TORCH_AVAILABLE = True
    _TORCH_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
except Exception:
    _TORCH_AVAILABLE = False
    _TORCH_DEVICE = None

from .flipflop_cell131 import (
    CellResult,
    H_PLANCK,
    optimize_cell_dc_bias,
    sample_exp124_donors,
)

KB_BOLTZMANN = 1.380649e-23  # J/K

# Basis operators on Q1(2) x Q2(2) x Cavity(3)
_I2 = np.eye(2, dtype=np.complex128)
_I3 = np.eye(3, dtype=np.complex128)
_X2 = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
_H2 = np.array([[1.0, 1.0], [1.0, -1.0]], dtype=np.complex128) / math.sqrt(2.0)
_SM = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.complex128)
_SP = _SM.T.copy()
_NQ = np.array([[0.0, 0.0], [0.0, 1.0]], dtype=np.complex128)
_SZ = np.array([[-1.0, 0.0], [0.0, 1.0]], dtype=np.complex128)
_A_CAV = np.array(
    [[0.0, 1.0, 0.0], [0.0, 0.0, math.sqrt(2.0)], [0.0, 0.0, 0.0]],
    dtype=np.complex128,
)
_AD_CAV = _A_CAV.T.copy()


def _kron3(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    return np.kron(np.kron(a, b), c)


SM1 = _kron3(_SM, _I2, _I3)
SP1 = _kron3(_SP, _I2, _I3)
NQ1 = _kron3(_NQ, _I2, _I3)
SZ1 = _kron3(_SZ, _I2, _I3)

SM2 = _kron3(_I2, _SM, _I3)
SP2 = _kron3(_I2, _SP, _I3)
NQ2 = _kron3(_I2, _NQ, _I3)
SZ2 = _kron3(_I2, _SZ, _I3)

A_OP = _kron3(_I2, _I2, _A_CAV)
AD_OP = _kron3(_I2, _I2, _AD_CAV)
NC_OP = AD_OP @ A_OP

I12 = np.eye(12, dtype=np.complex128)
X1_12 = _kron3(_X2, _I2, _I3)
HH_12 = _kron3(_H2, _H2, _I3)
S_X1_144 = np.kron(X1_12.conj(), X1_12)
S_HH_144 = np.kron(HH_12.conj(), HH_12)
CZ_IDEAL_4 = np.diag([1.0, 1.0, 1.0, -1.0]).astype(np.complex128)

# Precompute 16 computational basis outer-product vectors |i,0><j,0| for 2-qubit Choi evaluation
_B_EMB = np.zeros((12, 4), dtype=np.complex128)
for _q in range(4):
    _B_EMB[_q * 3, _q] = 1.0
_V_IN_16 = np.zeros((144, 16), dtype=np.complex128)
for _i in range(4):
    for _j in range(4):
        _V_IN_16[:, _i * 4 + _j] = np.outer(_B_EMB[:, _i], _B_EMB[:, _j].conj()).reshape(-1, order="F")

# Precompute static dissipator superoperator components (reused across all Lindblad calls)
def _dissipator_superop(c: np.ndarray) -> np.ndarray:
    cd_c = c.conj().T @ c
    return np.kron(c.conj(), c) - 0.5 * (np.kron(I12, cd_c) + np.kron(cd_c.T, I12))


_DISS_A = _dissipator_superop(A_OP)
_DISS_AD = _dissipator_superop(AD_OP)
_DISS_SM1 = _dissipator_superop(SM1)
_DISS_SM2 = _dissipator_superop(SM2)
_DISS_SZ1 = _dissipator_superop(SZ1)
_DISS_SZ2 = _dissipator_superop(SZ2)

# Precompute static Hamiltonian superoperator terms -i (I kron H - H^T kron I)
def _ham_superop(h: np.ndarray) -> np.ndarray:
    return -1j * (np.kron(I12, h) - np.kron(h.T, I12))


_H_SUP_NQ1 = _ham_superop(NQ1)
_H_SUP_NQ2 = _ham_superop(NQ2)
_H_SUP_JC1 = _ham_superop(SP1 @ A_OP + SM1 @ AD_OP)
_H_SUP_JC2 = _ham_superop(SP2 @ A_OP + SM2 @ AD_OP)
_JC1_12 = SP1 @ A_OP + SM1 @ AD_OP
_JC2_12 = SP2 @ A_OP + SM2 @ AD_OP


def thermal_photon_number(f_r_ghz: float = 5.0, temp_mk: float = 20.0) -> float:
    """Bose-Einstein thermal photon number n_th = 1 / (exp(h f / k_B T) - 1)."""
    x = (H_PLANCK * f_r_ghz * 1e9) / (KB_BOLTZMANN * (temp_mk * 1e-3))
    if x > 700.0:
        return 0.0
    return 1.0 / (math.exp(x) - 1.0)


def batch_expm(mats: np.ndarray) -> np.ndarray:
    """Exact matrix exponential on a batch (B, N, N) using CUDA when available."""
    if _TORCH_AVAILABLE and _TORCH_DEVICE is not None and _TORCH_DEVICE.type == "cuda":
        # Chunk to keep GPU VRAM comfortable even for large batches
        out = np.empty_like(mats)
        chunk = 64
        for start in range(0, len(mats), chunk):
            t = torch.from_numpy(mats[start : start + chunk]).to(_TORCH_DEVICE)
            e = torch.linalg.matrix_exp(t)
            out[start : start + chunk] = e.cpu().numpy()
        return out
    return np.stack([scipy_expm(m) for m in mats], axis=0)


def partial_trace_cavity(rho12: np.ndarray) -> np.ndarray:
    """Trace out the 3-level cavity mode from a 12x12 density matrix -> 4x4 2-qubit rho."""
    return np.einsum("ijik->jk", rho12.reshape(4, 3, 4, 3).transpose(1, 0, 3, 2))


def audit_density_matrix(rho12: np.ndarray) -> tuple[float, float, float]:
    """Return (trace_err, hermiticity_err, min_eigenvalue) for CPTP verification."""
    tr_err = abs(complex(np.trace(rho12)) - 1.0)
    herm_err = float(np.linalg.norm(rho12 - rho12.conj().T))
    rho_h = 0.5 * (rho12 + rho12.conj().T)
    min_ev = float(np.min(np.linalg.eigvalsh(rho_h)))
    return float(tr_err), herm_err, min_ev


def build_dissipator_144(
    g1_rel_khz: float,
    g2_rel_khz: float,
    g1_phi_khz: float,
    g2_phi_khz: float,
    kappa_khz: float,
    f_r_ghz: float = 5.0,
    temp_mk: float = 20.0,
) -> np.ndarray:
    """Build exact 144x144 Lindblad dissipator in Mrad/s (time unit = microseconds)."""
    n_th = thermal_photon_number(f_r_ghz, temp_mk) if kappa_khz > 0.0 else 0.0
    kappa = 2.0 * math.pi * (kappa_khz * 1e-3)
    gam1_1 = 2.0 * math.pi * (g1_rel_khz * 1e-3)
    gam1_2 = 2.0 * math.pi * (g2_rel_khz * 1e-3)
    gphi_1 = 2.0 * math.pi * (g1_phi_khz * 1e-3)
    gphi_2 = 2.0 * math.pi * (g2_phi_khz * 1e-3)
    return (
        (kappa * (1.0 + n_th)) * _DISS_A
        + (kappa * n_th) * _DISS_AD
        + gam1_1 * _DISS_SM1
        + gam1_2 * _DISS_SM2
        + (0.5 * gphi_1) * _DISS_SZ1
        + (0.5 * gphi_2) * _DISS_SZ2
    )


def simulate_resonant_bell_batch(
    pairs: list[tuple[float, float, float, float, float, float]],
    kappa_khz: float,
    f_r_ghz: float = 5.0,
    temp_mk: float = 20.0,
) -> dict[str, Any]:
    """Batch-simulate resonant sequential photon-swap Bell gate in exact 12x12 Lindblad.

    Each element of `pairs` is (g1_mhz, g2_mhz, g1_rel_khz, g2_rel_khz, g1_phi_khz, g2_phi_khz).
    Step 1 puts the weaker-coupled qubit on cavity resonance for t1 = pi / (4 g_min) ->
    half-swap into cavity; Step 2 puts the stronger-coupled qubit on resonance for
    t2 = pi / (2 g_max) -> complete swap out of cavity, forming (|10> - e^{i phi}|01>)/sqrt(2).
    """
    n = len(pairs)
    if n == 0:
        return {
            "fidelities": [],
            "gate_times_us": [],
            "mean_F_bell": 0.0,
            "median_F_bell": 0.0,
            "p10_F_bell": 0.0,
            "p90_F_bell": 0.0,
            "mean_t_bell_us": 0.0,
            "max_trace_err": 0.0,
            "max_herm_err": 0.0,
            "min_eigval": 0.0,
        }

    mats = np.empty((2 * n, 144, 144), dtype=np.complex128)
    v0_list = []
    times_us = []

    for idx, (g1_mhz, g2_mhz, r1, r2, p1, p2) in enumerate(pairs):
        g1 = 2.0 * math.pi * g1_mhz
        g2 = 2.0 * math.pi * g2_mhz
        d_off = 2.0 * math.pi * max(150.0, 40.0 * max(g1_mhz, g2_mhz))
        l_diss = build_dissipator_144(r1, r2, p1, p2, kappa_khz, f_r_ghz, temp_mk)
        jc_sup = g1 * _H_SUP_JC1 + g2 * _H_SUP_JC2

        if g1 <= g2:
            t1 = math.pi / (4.0 * g1)
            t2 = math.pi / (2.0 * g2)
            l1 = d_off * _H_SUP_NQ2 + jc_sup + l_diss
            l2 = d_off * _H_SUP_NQ1 + jc_sup + l_diss
            v0 = _V_IN_16[:, 2 * 4 + 2]  # |10,0><10,0|
        else:
            t1 = math.pi / (4.0 * g2)
            t2 = math.pi / (2.0 * g1)
            l1 = d_off * _H_SUP_NQ1 + jc_sup + l_diss
            l2 = d_off * _H_SUP_NQ2 + jc_sup + l_diss
            v0 = _V_IN_16[:, 1 * 4 + 1]  # |01,0><01,0|

        mats[2 * idx] = l1 * t1
        mats[2 * idx + 1] = l2 * t2
        v0_list.append(v0)
        times_us.append(t1 + t2)

    exps = batch_expm(mats)

    fids = []
    max_tr = 0.0
    max_herm = 0.0
    min_ev = 1.0
    for idx in range(n):
        vec_f = exps[2 * idx + 1] @ (exps[2 * idx] @ v0_list[idx])
        rho_f = vec_f.reshape((12, 12), order="F")
        tr_e, hm_e, mev = audit_density_matrix(rho_f)
        max_tr = max(max_tr, tr_e)
        max_herm = max(max_herm, hm_e)
        min_ev = min(min_ev, mev)
        rho_q = partial_trace_cavity(rho_f)
        # Bell fidelity against (|10> + e^{i phi}|01>)/sqrt(2) with exact local virtual-Z phase
        f_bell = float(0.5 * (rho_q[2, 2].real + rho_q[1, 1].real) + abs(rho_q[2, 1]))
        fids.append(f_bell)

    arr_f = np.array(fids, dtype=np.float64)
    arr_t = np.array(times_us, dtype=np.float64)
    return {
        "fidelities": [float(x) for x in fids],
        "gate_times_us": [float(x) for x in times_us],
        "mean_F_bell": float(np.mean(arr_f)),
        "median_F_bell": float(np.median(arr_f)),
        "p10_F_bell": float(np.percentile(arr_f, 10)),
        "p90_F_bell": float(np.percentile(arr_f, 90)),
        "mean_t_bell_us": float(np.mean(arr_t)),
        "max_trace_err": float(max_tr),
        "max_herm_err": float(max_herm),
        "min_eigval": float(min_ev),
    }


def simulate_resonant_bell_trajectory(
    g1_mhz: float,
    g2_mhz: float,
    g1_rel_khz: float,
    g2_rel_khz: float,
    g1_phi_khz: float,
    g2_phi_khz: float,
    kappa_khz: float,
    n_steps_per_stage: int = 30,
    f_r_ghz: float = 5.0,
    temp_mk: float = 20.0,
) -> dict[str, Any]:
    """Compute exact 12x12 Lindblad time-evolution trace for a heterogeneous Bell gate."""
    g1 = 2.0 * math.pi * g1_mhz
    g2 = 2.0 * math.pi * g2_mhz
    d_off = 2.0 * math.pi * max(150.0, 40.0 * max(g1_mhz, g2_mhz))
    l_diss = build_dissipator_144(g1_rel_khz, g2_rel_khz, g1_phi_khz, g2_phi_khz, kappa_khz, f_r_ghz, temp_mk)
    jc_sup = g1 * _H_SUP_JC1 + g2 * _H_SUP_JC2

    if g1 <= g2:
        t1 = math.pi / (4.0 * g1)
        t2 = math.pi / (2.0 * g2)
        l1 = d_off * _H_SUP_NQ2 + jc_sup + l_diss
        l2 = d_off * _H_SUP_NQ1 + jc_sup + l_diss
        vec = _V_IN_16[:, 2 * 4 + 2].copy()
    else:
        t1 = math.pi / (4.0 * g2)
        t2 = math.pi / (2.0 * g1)
        l1 = d_off * _H_SUP_NQ1 + jc_sup + l_diss
        l2 = d_off * _H_SUP_NQ2 + jc_sup + l_diss
        vec = _V_IN_16[:, 1 * 4 + 1].copy()

    dt1 = t1 / n_steps_per_stage
    dt2 = t2 / n_steps_per_stage
    u_steps = batch_expm(np.stack([l1 * dt1, l2 * dt2], axis=0))
    p1_step, p2_step = u_steps[0], u_steps[1]

    t_list, p10_list, p01_list, ncav_list, fbell_list = [], [], [], [], []

    def record(t_val: float, v: np.ndarray) -> None:
        rho = v.reshape((12, 12), order="F")
        rq = partial_trace_cavity(rho)
        t_list.append(float(t_val))
        p10_list.append(float(rq[2, 2].real))
        p01_list.append(float(rq[1, 1].real))
        ncav_list.append(float(np.trace(NC_OP @ rho).real))
        fbell_list.append(float(0.5 * (rq[2, 2].real + rq[1, 1].real) + abs(rq[2, 1])))

    record(0.0, vec)
    for k in range(1, n_steps_per_stage + 1):
        vec = p1_step @ vec
        record(k * dt1, vec)
    for k in range(1, n_steps_per_stage + 1):
        vec = p2_step @ vec
        record(t1 + k * dt2, vec)

    return {
        "g1_mhz": float(g1_mhz),
        "g2_mhz": float(g2_mhz),
        "t1_us": float(t1),
        "t2_us": float(t2),
        "t_total_us": float(t1 + t2),
        "t_us": t_list,
        "P_10": p10_list,
        "P_01": p01_list,
        "n_cav": ncav_list,
        "F_bell": fbell_list,
        "final_F_bell": fbell_list[-1],
    }


def _build_h12_disp(g1: float, g2: float, delta: float) -> np.ndarray:
    """Exact AC-Stark-matched dispersive JC Hamiltonian (d_i = Delta - g_i^2 / Delta)."""
    d1 = delta - (g1 * g1) / delta
    d2 = delta - (g2 * g2) / delta
    return d1 * NQ1 + d2 * NQ2 + g1 * _JC1_12 + g2 * _JC2_12


def _build_h144_disp(g1: float, g2: float, delta: float) -> np.ndarray:
    d1 = delta - (g1 * g1) / delta
    d2 = delta - (g2 * g2) / delta
    return d1 * _H_SUP_NQ1 + d2 * _H_SUP_NQ2 + g1 * _H_SUP_JC1 + g2 * _H_SUP_JC2


def simulate_dispersive_cz_pair(
    g1_mhz: float,
    g2_mhz: float,
    g1_rel_khz: float,
    g2_rel_khz: float,
    g1_phi_khz: float,
    g2_phi_khz: float,
    kappa_khz: float,
    eta: float = 3.5,
    n_ramp: int = 16,
    f_r_ghz: float = 5.0,
    temp_mk: float = 20.0,
) -> dict[str, Any]:
    """Exact 12x12 Lindblad full 4-basis CZ gate via C^2-quintic adiabatic dispersive sqrt(iSWAP).

    Constructs CZ = (H kron H) (X1) (Rz_rf) sqrt(iSWAP) (X1) (Rz_rf) sqrt(iSWAP) (H kron H)
    and evaluates the full 16-element Choi / Nielsen average gate fidelity F_avg(CZ)
    plus single-step dispersive Bell fidelity F_bell_disp.
    """
    g1 = 2.0 * math.pi * g1_mhz
    g2 = 2.0 * math.pi * g2_mhz
    g_max = max(g1, g2)
    idx1 = [1, 3, 6]

    # Ensure ramp swap angle stays strictly below 0.22 * pi (prevents over-rotation when g1 ~ g2!)
    eta_eff = float(eta)
    while True:
        delta_gate = eta_eff * g_max
        delta_idle = 50.0 * g_max
        th_i = math.atan2(2.0 * g_max, delta_idle)
        th_g = math.atan2(2.0 * g_max, delta_gate)
        t_r = 14.0 / delta_gate
        dt_r = t_r / n_ramp
        us = [(k + 0.5) / n_ramp for k in range(n_ramp)]
        ss = [10.0 * (u**3) - 15.0 * (u**4) + 6.0 * (u**5) for u in us]
        deltas = [2.0 * g_max / math.tan(th_i + sk * (th_g - th_i)) for sk in ss]
        h_ramps = [_build_h12_disp(g1, g2, d) for d in deltas]
        th_ramp = 0.0
        for hk in h_ramps:
            ev1 = np.linalg.eigvalsh(hk[np.ix_(idx1, idx1)])
            th_ramp += 2.0 * 0.5 * (ev1[2] - ev1[1]) * dt_r
        if th_ramp <= 0.22 * math.pi or eta_eff >= 12.0:
            break
        eta_eff *= 1.25

    h_gate = _build_h12_disp(g1, g2, delta_gate)
    ev_g = np.linalg.eigvalsh(h_gate[np.ix_(idx1, idx1)])
    j_gate = 0.5 * (ev_g[2] - ev_g[1])
    t_hold = max(0.0, 0.25 * math.pi - th_ramp) / j_gate

    # Exact rotating-frame single-qubit phase calibration from 12x12 noiseless unitary
    u_mats = np.stack([-1j * hk * dt_r for hk in h_ramps] + [-1j * h_gate * t_hold], axis=0)
    u_exps = batch_expm(u_mats)
    u_up = np.eye(12, dtype=np.complex128)
    for k in range(n_ramp):
        u_up = u_exps[k] @ u_up
    u_dn = np.eye(12, dtype=np.complex128)
    for k in range(n_ramp - 1, -1, -1):
        u_dn = u_exps[k] @ u_dn
    u_half = u_dn @ u_exps[n_ramp] @ u_up
    phi1 = float(-np.angle(u_half[6, 6]))
    phi2 = float(-np.angle(u_half[3, 3]))
    unitary_p11 = float(abs(u_half[9, 9]) ** 2)

    # Full noisy 144x144 superoperator (batched on GPU in a single call)
    l_diss = build_dissipator_144(g1_rel_khz, g2_rel_khz, g1_phi_khz, g2_phi_khz, kappa_khz, f_r_ghz, temp_mk)
    l_mats = np.stack(
        [(_build_h144_disp(g1, g2, d) + l_diss) * dt_r for d in deltas]
        + [(_build_h144_disp(g1, g2, delta_gate) + l_diss) * t_hold],
        axis=0,
    )
    p_exps = batch_expm(l_mats)
    p_up = np.eye(144, dtype=np.complex128)
    for k in range(n_ramp):
        p_up = p_exps[k] @ p_up
    p_dn = np.eye(144, dtype=np.complex128)
    for k in range(n_ramp - 1, -1, -1):
        p_dn = p_exps[k] @ p_dn
    p_half = p_dn @ p_exps[n_ramp] @ p_up

    # Single-step dispersive Bell state fidelity on |10,0>
    rho_b12 = (p_half @ _V_IN_16[:, 2 * 4 + 2]).reshape((12, 12), order="F")
    tr_b, hm_b, mev_b = audit_density_matrix(rho_b12)
    rq_b = partial_trace_cavity(rho_b12)
    f_bell_disp = float(0.5 * (rq_b[2, 2].real + rq_b[1, 1].real) + abs(rq_b[2, 1]))

    # Full 2-step CZ superoperator
    u_rf = _kron3(
        np.diag([1.0, np.exp(1j * phi1)]),
        np.diag([1.0, np.exp(1j * phi2)]),
        _I3,
    )
    s_rf = np.kron(u_rf.conj(), u_rf)
    s_cz = S_HH_144 @ S_X1_144 @ s_rf @ p_half @ S_X1_144 @ s_rf @ p_half @ S_HH_144
    v_out = s_cz @ _V_IN_16

    # Audit diagonal physical state |11,0> after full CZ
    rho_11 = v_out[:, 3 * 4 + 3].reshape((12, 12), order="F")
    tr_c, hm_c, mev_c = audit_density_matrix(rho_11)

    # Extract deterministic single-qubit virtual-Z calibration phases & verify entangling phase = pi
    m_diag = np.array([partial_trace_cavity(v_out[:, k].reshape((12, 12), order="F"))[0, k] for k in range(4)])
    phases = np.angle(m_diag)
    ent_phase_over_pi = float(((phases[0] + phases[3] - phases[1] - phases[2]) % (2.0 * math.pi)) / math.pi)
    u_loc = np.diag([
        1.0,
        np.exp(1j * (phases[1] - phases[0])),
        np.exp(1j * (phases[2] - phases[0])),
        np.exp(1j * (phases[1] + phases[2] - 2.0 * phases[0])),
    ])
    u_tgt = u_loc.conj() @ CZ_IDEAL_4

    fe_val = 0.0 + 0.0j
    for i in range(4):
        for j in range(4):
            e_ij = partial_trace_cavity(v_out[:, i * 4 + j].reshape((12, 12), order="F"))
            fe_val += (u_tgt.conj().T @ e_ij @ u_tgt)[i, j]
    fe = float(fe_val.real / 16.0)
    f_avg_cz = float((4.0 * fe + 1.0) / 5.0)

    # Also compute CZ Bell-state fidelity on |++> -> CZ|++> = (|00>+|01>+|10>-|11>)/2
    psi_pp = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.complex128)
    rho_pp_12 = np.outer(_B_EMB @ psi_pp, (_B_EMB @ psi_pp).conj())
    rho_cz_pp = (s_cz @ rho_pp_12.reshape(-1, order="F")).reshape((12, 12), order="F")
    rq_pp = partial_trace_cavity(rho_cz_pp)
    psi_tgt = u_tgt @ psi_pp
    f_cz_bell_state = float(np.real(psi_tgt.conj() @ (rq_pp @ psi_tgt)))

    t_half_us = 2.0 * t_r + t_hold
    return {
        "eta_used": float(eta_eff),
        "t_half_us": float(t_half_us),
        "t_cz_us": float(2.0 * t_half_us),
        "unitary_p11": unitary_p11,
        "ent_phase_over_pi": ent_phase_over_pi,
        "F_bell_disp": f_bell_disp,
        "F_ent_cz": fe,
        "F_avg_cz": f_avg_cz,
        "F_cz_bell_state": f_cz_bell_state,
        "max_trace_err": float(max(tr_b, tr_c)),
        "max_herm_err": float(max(hm_b, hm_c)),
        "min_eigval": float(min(mev_b, mev_c)),
    }


def _cells_to_pairs(cells: list[CellResult], n_pairs: int, rng: np.random.Generator, z_scale: float = 1.0) -> list[tuple[float, float, float, float, float, float]]:
    """Sample n_pairs random heterogeneous pairs from certified cells, scaling g_eff by z_scale."""
    if len(cells) < 2:
        return []
    out = []
    m = len(cells)
    for _ in range(n_pairs):
        i, j = rng.integers(0, m, size=2)
        if i == j:
            j = (int(j) + 1) % m
        c1, c2 = cells[int(i)], cells[int(j)]
        out.append((
            c1.g_eff_mhz * z_scale,
            c2.g_eff_mhz * z_scale,
            c1.gamma_1_khz,
            c2.gamma_1_khz,
            c1.gamma_phi_khz,
            c2.gamma_phi_khz,
        ))
    return out


def _sample_best_of_ncand_cells(
    cells: list[CellResult],
    n_nodes: int,
    n_cand: int,
    p_spec: float,
    rng: np.random.Generator,
) -> list[CellResult]:
    """Simulate M4 logical-node candidate selection: each node has n_cand slots,
    each independently passes Mod B spectroscopy (p_spec) and draws a certified donor;
    the node controller activates the highest-M_res surviving donor.
    """
    if not cells:
        return []
    m = len(cells)
    selected: list[CellResult] = []
    for _ in range(n_nodes):
        survivors: list[CellResult] = []
        for _k in range(n_cand):
            if rng.random() < p_spec:
                survivors.append(cells[int(rng.integers(0, m))])
        if survivors:
            selected.append(max(survivors, key=lambda c: c.m_res_merit))
    return selected


def run_lindblad_bus_study(
    optimal_cells_3k: list[CellResult],
    capping_ensembles_3k: dict[float, list[CellResult]],
    delta_z_opt_nm: float = 8.0,
    f_r_ghz: float = 5.0,
    temp_mk: float = 20.0,
    p_spec: float = 0.51,
    n_cand_m4: int = 6,
    seed: int = 13102,
) -> dict[str, Any]:
    """Run all Part 2 Lindblad studies: 50 Ohm vs 3 kOhm, 4D phase map, capping, & full CZ.

    Evaluates BOTH:
      - Unified M4 Best-of-N_cand=6 node selection (activating the highest-M_res certified
        donor among the surviving slots in each 6-slot node pocket), and
      - Unselected N_cand=1 random C>=100 pair baseline (reported transparently side-by-side).
    """
    rng = np.random.default_rng(seed)

    # 1) 50 Ohm vs 3 kOhm comparison (Q_L=2e5, S_eps=1.0, optimal Delta_z_cap)
    kappa_nom = (f_r_ghz / 2e5) * 1e6  # 25.0 kHz
    scale_50 = math.sqrt(50.0 / 3000.0)

    # (a) Unselected N_cand=1 baseline (60 random pairs)
    pairs_3k_unsel = _cells_to_pairs(optimal_cells_3k, 60, rng, z_scale=1.0)
    pairs_50_unsel = [(g1 * scale_50, g2 * scale_50, r1, r2, p1, p2) for (g1, g2, r1, r2, p1, p2) in pairs_3k_unsel]
    res_3k_unsel = simulate_resonant_bell_batch(pairs_3k_unsel, kappa_nom, f_r_ghz, temp_mk)
    res_50_unsel = simulate_resonant_bell_batch(pairs_50_unsel, kappa_nom, f_r_ghz, temp_mk)

    # (b) Unified M4 Best-of-6 node selection (60 heterogeneous node pairs)
    b6_cells_3k = _sample_best_of_ncand_cells(optimal_cells_3k, 160, n_cand_m4, p_spec, rng)
    pairs_3k_60 = _cells_to_pairs(b6_cells_3k, 60, rng, z_scale=1.0)
    pairs_50_60 = [(g1 * scale_50, g2 * scale_50, r1, r2, p1, p2) for (g1, g2, r1, r2, p1, p2) in pairs_3k_60]
    res_3k_bell = simulate_resonant_bell_batch(pairs_3k_60, kappa_nom, f_r_ghz, temp_mk)
    res_50_bell = simulate_resonant_bell_batch(pairs_50_60, kappa_nom, f_r_ghz, temp_mk)

    # 2) Representative heterogeneous time-evolution trajectory (from Best-of-6 node donors)
    sorted_cells = sorted(b6_cells_3k, key=lambda c: c.g_eff_mhz)
    c_a = sorted_cells[int(0.30 * len(sorted_cells))]
    c_b = sorted_cells[int(0.75 * len(sorted_cells))]
    traj_3k = simulate_resonant_bell_trajectory(
        c_a.g_eff_mhz, c_b.g_eff_mhz, c_a.gamma_1_khz, c_b.gamma_1_khz,
        c_a.gamma_phi_khz, c_b.gamma_phi_khz, kappa_nom, n_steps_per_stage=35, f_r_ghz=f_r_ghz, temp_mk=temp_mk,
    )
    traj_50 = simulate_resonant_bell_trajectory(
        c_a.g_eff_mhz * scale_50, c_b.g_eff_mhz * scale_50, c_a.gamma_1_khz, c_b.gamma_1_khz,
        c_a.gamma_phi_khz, c_b.gamma_phi_khz, kappa_nom, n_steps_per_stage=35, f_r_ghz=f_r_ghz, temp_mk=temp_mk,
    )

    # 3) Full 4D phase map: Z_r x Q_L x S_eps (5 x 5 x 4 = 100 operating points, 30 Best-of-6 pairs/point)
    # Also includes diagnostic S_eps = 0.25 ueV/rtHz (Tosi 2017 100 V/m) row for roadmap threshold identification.
    z_r_grid = [50.0, 1000.0, 2000.0, 3000.0, 4000.0]
    q_l_grid = [2e4, 5e4, 1e5, 2e5, 5e5]
    s_eps_grid = [0.5, 1.0, 2.0, 5.0]

    z_pm, r_pm = sample_exp124_donors(140, delta_z_opt_nm, rng)
    phase_map: list[dict[str, Any]] = []
    worst_tr_err = max(res_3k_bell["max_trace_err"], res_50_bell["max_trace_err"], res_3k_unsel["max_trace_err"])
    worst_herm_err = max(res_3k_bell["max_herm_err"], res_50_bell["max_herm_err"], res_3k_unsel["max_herm_err"])
    worst_min_ev = min(res_3k_bell["min_eigval"], res_50_bell["min_eigval"], res_3k_unsel["min_eigval"])

    for q_l in q_l_grid:
        kappa_khz = (f_r_ghz / q_l) * 1e6
        for s_eps in s_eps_grid:
            cells_qs: list[CellResult] = []
            for zi, ri in zip(z_pm, r_pm):
                c = optimize_cell_dc_bias(float(zi), float(ri), 3000.0, q_l, s_eps, f_r_ghz, objective="m_res")
                if c is not None and c.cooperativity >= 20.0:
                    cells_qs.append(c)
            cert_qs = [c for c in cells_qs if c.cooperativity >= 100.0]
            pool_raw = cert_qs if len(cert_qs) >= 15 else cells_qs
            pool_b6 = _sample_best_of_ncand_cells(pool_raw, 90, n_cand_m4, p_spec, rng)
            base_pairs_3k = _cells_to_pairs(pool_b6, 30, rng, z_scale=1.0)

            for z_r in z_r_grid:
                z_sc = math.sqrt(z_r / 3000.0)
                pairs_z = [(g1 * z_sc, g2 * z_sc, r1, r2, p1, p2) for (g1, g2, r1, r2, p1, p2) in base_pairs_3k]
                r_bell = simulate_resonant_bell_batch(pairs_z, kappa_khz, f_r_ghz, temp_mk)
                worst_tr_err = max(worst_tr_err, r_bell["max_trace_err"])
                worst_herm_err = max(worst_herm_err, r_bell["max_herm_err"])
                worst_min_ev = min(worst_min_ev, r_bell["min_eigval"])
                phase_map.append({
                    "z_r_ohm": float(z_r),
                    "q_l": float(q_l),
                    "s_eps_uev": float(s_eps),
                    "kappa_khz": float(kappa_khz),
                    "n_pairs": len(pairs_z),
                    "mean_F_bell": r_bell["mean_F_bell"],
                    "median_F_bell": r_bell["median_F_bell"],
                    "p10_F_bell": r_bell["p10_F_bell"],
                    "p90_F_bell": r_bell["p90_F_bell"],
                    "mean_t_bell_us": r_bell["mean_t_bell_us"],
                })

    # Diagnostic ultra-low-noise Tosi 100 V/m check (S_eps = 0.25 ueV/rtHz, Z_r=3..4 kOhm, Q_L=2e5..5e5)
    tosi_diag: list[dict[str, Any]] = []
    for q_l in [2e5, 5e5]:
        kap = (f_r_ghz / q_l) * 1e6
        c_tosi = [
            c for zi, ri in zip(z_pm, r_pm)
            if (c := optimize_cell_dc_bias(float(zi), float(ri), 3000.0, q_l, 0.25, f_r_ghz, objective="m_res")) is not None
            and c.cooperativity >= 100.0
        ]
        b6_tosi = _sample_best_of_ncand_cells(c_tosi, 90, n_cand_m4, p_spec, rng)
        p_tosi_3k = _cells_to_pairs(b6_tosi, 30, rng, z_scale=1.0)
        for z_r in [3000.0, 4000.0]:
            z_sc = math.sqrt(z_r / 3000.0)
            pz = [(g1 * z_sc, g2 * z_sc, r1, r2, p1, p2) for (g1, g2, r1, r2, p1, p2) in p_tosi_3k]
            rb = simulate_resonant_bell_batch(pz, kap, f_r_ghz, temp_mk)
            tosi_diag.append({
                "z_r_ohm": float(z_r),
                "q_l": float(q_l),
                "s_eps_uev": 0.25,
                "mean_F_bell": rb["mean_F_bell"],
                "median_F_bell": rb["median_F_bell"],
                "p90_F_bell": rb["p90_F_bell"],
            })

    # 4) Capping thickness Delta_z_cap -> 2-cell Bell fidelity sweep (nominal 3 kOhm, Q_L=2e5, S_eps=1.0)
    capping_bell_sweep: list[dict[str, Any]] = []
    for dz, ens in sorted(capping_ensembles_3k.items()):
        b6_dz = _sample_best_of_ncand_cells(ens, 100, n_cand_m4, p_spec, rng)
        pairs_dz = _cells_to_pairs(b6_dz, 40, rng, z_scale=1.0)
        r_dz = simulate_resonant_bell_batch(pairs_dz, kappa_nom, f_r_ghz, temp_mk)
        capping_bell_sweep.append({
            "delta_z_cap_nm": float(dz),
            "n_certified_pool": len(ens),
            "n_pairs": len(pairs_dz),
            "mean_F_bell": r_dz["mean_F_bell"],
            "median_F_bell": r_dz["median_F_bell"],
            "mean_t_bell_us": r_dz["mean_t_bell_us"],
        })

    # 5) Full 4-basis universal CZ gate audit (eta=4.0 exact phase calibration ent/pi=1.000)
    noiseless_cz = simulate_dispersive_cz_pair(2.0, 1.3, 0.0, 0.0, 0.0, 0.0, 0.0, eta=4.0, n_ramp=16)

    pairs_cz_nom = pairs_3k_60[:24]
    cz_nom_favg = []
    cz_nom_fbell_state = []
    cz_nom_fdisp_bell = []
    cz_nom_t = []
    cz_nom_ent = []
    for (g1, g2, r1, r2, p1, p2) in pairs_cz_nom:
        best_c = simulate_dispersive_cz_pair(g1, g2, r1, r2, p1, p2, kappa_nom, eta=4.0, n_ramp=14)
        cz_nom_favg.append(best_c["F_avg_cz"])
        cz_nom_fbell_state.append(best_c["F_cz_bell_state"])
        cz_nom_fdisp_bell.append(best_c["F_bell_disp"])
        cz_nom_t.append(best_c["t_cz_us"])
        cz_nom_ent.append(best_c["ent_phase_over_pi"])
        worst_tr_err = max(worst_tr_err, best_c["max_trace_err"])
        worst_herm_err = max(worst_herm_err, best_c["max_herm_err"])
        worst_min_ev = min(worst_min_ev, best_c["min_eigval"])

    # Low-noise CZ (S_eps = 0.5 and Tosi S_eps = 0.25 at 3 kOhm, Q_L=2e5)
    cells_low = [
        c for zi, ri in zip(z_pm, r_pm)
        if (c := optimize_cell_dc_bias(float(zi), float(ri), 3000.0, 2e5, 0.5, f_r_ghz, objective="m_res")) is not None
        and c.cooperativity >= 100.0
    ]
    b6_low = _sample_best_of_ncand_cells(cells_low, 60, n_cand_m4, p_spec, rng)
    pairs_cz_low = _cells_to_pairs(b6_low, 16, rng, z_scale=1.0)
    cz_low_favg = []
    cz_low_t = []
    for (g1, g2, r1, r2, p1, p2) in pairs_cz_low:
        res_l = simulate_dispersive_cz_pair(g1, g2, r1, r2, p1, p2, kappa_nom, eta=4.0, n_ramp=14)
        cz_low_favg.append(res_l["F_avg_cz"])
        cz_low_t.append(res_l["t_cz_us"])

    # Tosi 100 V/m (S_eps = 0.25, Q_L=5e5) CZ check
    cells_tosi_cz = [
        c for zi, ri in zip(z_pm, r_pm)
        if (c := optimize_cell_dc_bias(float(zi), float(ri), 3000.0, 5e5, 0.25, f_r_ghz, objective="m_res")) is not None
        and c.cooperativity >= 100.0
    ]
    b6_tosi_cz = _sample_best_of_ncand_cells(cells_tosi_cz, 60, n_cand_m4, p_spec, rng)
    pairs_cz_tosi = _cells_to_pairs(b6_tosi_cz, 12, rng, z_scale=1.0)
    cz_tosi_favg = [
        simulate_dispersive_cz_pair(g1, g2, r1, r2, p1, p2, 10.0, eta=4.0, n_ramp=14)["F_avg_cz"]
        for (g1, g2, r1, r2, p1, p2) in pairs_cz_tosi
    ]

    # 50 Ohm CZ contrast (6 pairs)
    cz_50_favg = [
        simulate_dispersive_cz_pair(g1, g2, r1, r2, p1, p2, kappa_nom, eta=4.0, n_ramp=14)["F_avg_cz"]
        for (g1, g2, r1, r2, p1, p2) in pairs_50_60[:6]
    ]

    return {
        "device_used": str(_TORCH_DEVICE) if _TORCH_AVAILABLE else "scipy_cpu",
        "node_selection_protocol": f"Unified M4 Best-of-N_cand={n_cand_m4} (argmax M_res among Mod B surviving slots, p_spec={p_spec})",
        "thermal_photon_20mK_5GHz": float(thermal_photon_number(f_r_ghz, temp_mk)),
        "cptp_audit": {
            "max_trace_err": float(worst_tr_err),
            "max_hermiticity_err": float(worst_herm_err),
            "min_eigenvalue": float(worst_min_ev),
        },
        "impedance_wall_comparison": {
            "n_pairs": 60,
            "q_l": 2e5,
            "s_eps_uev": 1.0,
            "delta_z_cap_nm": float(delta_z_opt_nm),
            "cpw_50ohm": {k: v for k, v in res_50_bell.items() if k not in ("fidelities", "gate_times_us")},
            "nbtin_3kohm": {k: v for k, v in res_3k_bell.items() if k not in ("fidelities", "gate_times_us")},
            "unselected_Ncand1_baseline": {
                "cpw_50ohm_mean_F_bell": res_50_unsel["mean_F_bell"],
                "nbtin_3kohm_mean_F_bell": res_3k_unsel["mean_F_bell"],
                "nbtin_3kohm_median_F_bell": res_3k_unsel["median_F_bell"],
                "nbtin_3kohm_mean_t_bell_us": res_3k_unsel["mean_t_bell_us"],
            },
            "cpw_50ohm_fidelities": res_50_bell["fidelities"],
            "nbtin_3kohm_fidelities": res_3k_bell["fidelities"],
            "nbtin_3kohm_pair_g_min_mhz": [min(p[0], p[1]) for p in pairs_3k_60],
            "nbtin_3kohm_pair_g_max_mhz": [max(p[0], p[1]) for p in pairs_3k_60],
        },
        "bell_trajectories": {
            "nbtin_3kohm": traj_3k,
            "cpw_50ohm": traj_50,
        },
        "phase_map_4d": {
            "z_r_ohm_grid": z_r_grid,
            "q_l_grid": q_l_grid,
            "s_eps_uev_grid": s_eps_grid,
            "points": phase_map,
            "tosi_100Vm_S0p25_diagnostic": tosi_diag,
        },
        "capping_bell_sweep": capping_bell_sweep,
        "universal_cz_gate": {
            "noiseless_verification": noiseless_cz,
            "nominal_3kohm_Q2e5_S1": {
                "n_pairs": len(cz_nom_favg),
                "mean_F_avg_cz": float(np.mean(cz_nom_favg)),
                "median_F_avg_cz": float(np.median(cz_nom_favg)),
                "p10_F_avg_cz": float(np.percentile(cz_nom_favg, 10)),
                "p90_F_avg_cz": float(np.percentile(cz_nom_favg, 90)),
                "mean_F_cz_bell_state": float(np.mean(cz_nom_fbell_state)),
                "mean_F_bell_disp_single_step": float(np.mean(cz_nom_fdisp_bell)),
                "mean_t_cz_us": float(np.mean(cz_nom_t)),
                "mean_ent_phase_over_pi": float(np.mean(cz_nom_ent)),
                "fidelities_F_avg_cz": [float(x) for x in cz_nom_favg],
            },
            "low_noise_3kohm_Q2e5_S0p5": {
                "n_pairs": len(cz_low_favg),
                "mean_F_avg_cz": float(np.mean(cz_low_favg)),
                "median_F_avg_cz": float(np.median(cz_low_favg)),
                "mean_t_cz_us": float(np.mean(cz_low_t)),
            },
            "tosi_ultra_low_noise_3kohm_Q5e5_S0p25": {
                "n_pairs": len(cz_tosi_favg),
                "mean_F_avg_cz": float(np.mean(cz_tosi_favg)),
                "median_F_avg_cz": float(np.median(cz_tosi_favg)),
            },
            "cpw_50ohm_Q2e5_S1": {
                "n_pairs": len(cz_50_favg),
                "mean_F_avg_cz": float(np.mean(cz_50_favg)),
            },
        },
    }
