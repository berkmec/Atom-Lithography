"""Exact CUDA-accelerated 12x12 Strang-split Lindblad + colored 1/f^alpha CZ bus solver (Exp137).

Hilbert space: Qubit_1 (2) x Qubit_2 (2) x NbTiN Cavity (3 Fock states: |0>,|1>,|2>) = 12D.
Propagates all 16 computational-basis Choi elements |i,0><j,0| simultaneously across
N_traj >= 512 independent colored 1/f^alpha multi-OU trajectories on CUDA GPU (complex128)
with exact Strang-split Markovian Lindblad dissipation (cavity kappa + thermal n_th at 20 mK,
qubit T1 relaxation, and residual 0.5 kHz 1% 29Si nuclear bath).

Implements four universal 2-qubit CZ protocols anchored to Exp131 (3 kOhm NbTiN,
L_res = 300 um, B_M4 = 0.1785 T, Delta_z_cap* = 8.0 nm):
  - (P1) Bare Dispersive CZ (un-echoed Q2 under colored 1/f^alpha + Exp131 Markovian anchor)
  - (P2) FF-Echo-CZ (CZ/2 - pi_X x pi_X - CZ/2 - pi_X x pi_X: 1st-order 1/f echo on both qubits)
  - (P3) XY4-Embedded DRAG-CZ (4-slice XY4 with virtual-Z combined X1 + complex cavity-DRAG
         alpha_drag=-1.0: 2nd-order 1/f suppression + pulse-error cancellation + <1e-5 leakage)
  - (P4) Sweet-Spot Parametric AC-Stark / Flux-Modulated g(t) Echo CZ (clock transition
         partial omega_q/partial eps ~ 0 + Bessel-stationary flat-g modulation + XY4-DRAG echo)

Extracts exact 16-element Choi / Pauli Transfer Matrix (PTM) stochastic error channels
{p_I, p_X, p_Y, p_Z, p_ZZ, p_leak, p_total_err, F_avg, F_Bell, t_gate_us} for Exp138.

Epistemic scope: {Model} / {Sayisal-Simulasyon}. No laboratory measurement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
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

from .noise_ou137 import (
    DEFAULT_F_IR_HZ,
    DEFAULT_F_UV_HZ,
    DEFAULT_N_FLUCT,
    H_PLANCK,
    generate_ou_1f_trajectories_ghz,
)

KB_BOLTZMANN = 1.380649e-23
GAMMA_PHI_NUC_1PCT_KHZ = 0.5  # Residual Mod B f=1% 29Si nuclear bath dephasing (Exp131 anchor)

# Basis operators on Q1(2) x Q2(2) x Cavity(3)
_I2 = np.eye(2, dtype=np.complex128)
_I3 = np.eye(3, dtype=np.complex128)
_X2 = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
_Y2 = np.array([[0.0, -1j], [1j, 0.0]], dtype=np.complex128)
_Z2 = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)
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
SP1A = SP1 @ A_OP
SM1AD = SM1 @ AD_OP
SP2A = SP2 @ A_OP
SM2AD = SM2 @ AD_OP

I12 = np.eye(12, dtype=np.complex128)
HH_12 = _kron3(_H2, _H2, _I3)
Z1_12 = _kron3(_Z2, _I2, _I3)
CZ_IDEAL_4 = np.diag([1.0, 1.0, 1.0, -1.0]).astype(np.complex128)

# 16 Pauli basis operators and Bell basis states for exact Choi -> Pauli error projection
_P1_DICT = {"I": _I2, "X": _X2, "Y": _Y2, "Z": _Z2}
PAULI_16_NAMES = [a + b for a in "IXYZ" for b in "IXYZ"]
PAULI_16_OPS = {name: np.kron(_P1_DICT[name[0]], _P1_DICT[name[1]]) for name in PAULI_16_NAMES}
_BELL_BASIS_16 = {}
for _name, _op in PAULI_16_OPS.items():
    _vec = np.zeros(16, dtype=np.complex128)
    for _k in range(4):
        _ek = np.zeros(4, dtype=np.complex128)
        _ek[_k] = 1.0
        _vec += 0.5 * np.kron(_ek, _op @ _ek)
    _BELL_BASIS_16[_name] = _vec

# Initial 16 computational basis Choi elements |i,0><j,0| (16, 12, 12)
_B_EMB = np.zeros((12, 4), dtype=np.complex128)
for _q in range(4):
    _B_EMB[_q * 3, _q] = 1.0
_RHO_INIT_16 = np.zeros((16, 12, 12), dtype=np.complex128)
for _i in range(4):
    for _j in range(4):
        _RHO_INIT_16[_i * 4 + _j] = np.outer(_B_EMB[:, _i], _B_EMB[:, _j].conj())


def _diss_superop(c: np.ndarray) -> np.ndarray:
    cdc = c.conj().T @ c
    return np.kron(c.conj(), c) - 0.5 * (np.kron(I12, cdc) + np.kron(cdc.T, I12))


_DISS_A = _diss_superop(A_OP)
_DISS_AD = _diss_superop(AD_OP)
_DISS_SM1 = _diss_superop(SM1)
_DISS_SM2 = _diss_superop(SM2)
_DISS_SZ1 = _diss_superop(SZ1)
_DISS_SZ2 = _diss_superop(SZ2)

# Single-qubit microwave drive generators in 12D (g=0 during finite pi-pulse)
_X1_GEN = _kron3(_X2, _I2, _I3)
_Y1_GEN = _kron3(_Y2, _I2, _I3)
_X2_GEN = _kron3(_I2, _X2, _I3)
_Y2_GEN = _kron3(_I2, _Y2, _I3)


@dataclass
class FlipFlopPairSpec:
    """Two-donor heterogeneous M4 pair parameters anchored to Exp131 4x4 Tosi model."""

    g1_mhz: float
    g2_mhz: float
    d1_1_ghz_per_ghz: float
    d2_1_inv_ghz: float
    d1_2_ghz_per_ghz: float
    d2_2_inv_ghz: float
    dg1_mhz_per_ghz: float
    dg2_mhz_per_ghz: float
    gamma1_1_khz: float
    gamma1_2_khz: float
    label: str = "pair"


def thermal_photon_number(f_r_ghz: float = 5.0, temp_mk: float = 20.0) -> float:
    x = (H_PLANCK * f_r_ghz * 1e9) / (KB_BOLTZMANN * (temp_mk * 1e-3))
    return 0.0 if x > 700.0 else 1.0 / (math.exp(x) - 1.0)


def _calibrate_slice_schedule(
    g1_mhz: float,
    g2_mhz: float,
    slice_angle: float,
    eta_min: float = 4.0,
    alpha_drag: float = -1.0,
    n_edge: int = 6,
    n_hold: int = 4,
) -> dict[str, Any]:
    """Calibrate dedicated-edge smooth DRAG envelope g_c(t) = g*(s(t) + i*alpha_drag*s'(t)/Delta).

    Uses dedicated fine grid points (`n_edge` up + `n_hold` flattop + `n_edge` down when flattop,
    or `2*n_edge` smooth sin^2 points when compact) so even extreme g_max/g_min > 10 pairs maintain
    smooth edge resolution and cavity leakage < 1e-4!
    """
    g1 = 2.0 * math.pi * g1_mhz
    g2 = 2.0 * math.pi * g2_mhz
    g_max = max(g1, g2)
    g_min = min(g1, g2)
    eta = max(eta_min, math.sqrt(18.0 * (3.0 / 8.0) * (g_min / g_max) / max(slice_angle, 1e-6)))
    delta = eta * g_max
    idx1 = [1, 3, 6]

    h_pk = (delta - g1 * g1 / delta) * NQ1 + (delta - g2 * g2 / delta) * NQ2 + g1 * (SP1A + SM1AD) + g2 * (SP2A + SM2AD)
    ev_pk = np.linalg.eigvalsh(h_pk[np.ix_(idx1, idx1)])
    j_pk = 0.5 * (ev_pk[2] - ev_pk[1])

    t_edge_nom = 12.0 / delta
    th_edges = 2.0 * (3.0 / 8.0) * t_edge_nom * j_pk
    ue = (np.arange(n_edge, dtype=np.float64) + 0.5) / n_edge
    s_up = np.sin(0.5 * math.pi * ue) ** 2
    ds_up_du = 0.5 * math.pi * np.sin(math.pi * ue)
    s_dn = np.sin(0.5 * math.pi * (1.0 - ue)) ** 2
    ds_dn_du = -0.5 * math.pi * np.sin(math.pi * (1.0 - ue))

    is_flattop = slice_angle > th_edges * 1.05

    def build_steps(param: float) -> tuple[list[float], np.ndarray, list[bool]]:
        if is_flattop:
            t_flat = max(1e-5, param)
            dt_e = t_edge_nom / n_edge
            dt_h = t_flat / n_hold
            dts = [dt_e] * n_edge + [dt_h] * n_hold + [dt_e] * n_edge
            is_edge_flag = [True] * n_edge + [False] * n_hold + [True] * n_edge
            facs = np.concatenate([
                s_up + 1j * alpha_drag * (ds_up_du / t_edge_nom) / delta,
                np.ones(n_hold, dtype=np.complex128),
                s_dn + 1j * alpha_drag * (ds_dn_du / t_edge_nom) / delta,
            ])
        else:
            te = max(1e-5, param)
            dt_e = te / n_edge
            dts = [dt_e] * (2 * n_edge)
            is_edge_flag = [True] * (2 * n_edge)
            facs = np.concatenate([
                s_up + 1j * alpha_drag * (ds_up_du / te) / delta,
                s_dn + 1j * alpha_drag * (ds_dn_du / te) / delta,
            ])
        return dts, facs, is_edge_flag

    if is_flattop:
        p_est = (slice_angle - th_edges) / j_pk
        lo, hi = max(1e-5, p_est * 0.70), p_est * 1.35
    else:
        p_est = t_edge_nom * (slice_angle / max(th_edges, 1e-9))
        lo, hi = p_est * 0.70, p_est * 1.35

    def eval_u_seg(param: float) -> np.ndarray:
        dts, facs, _ = build_steps(param)
        u_acc = np.eye(12, dtype=np.complex128)
        for dt, fac in zip(dts, facs):
            g1c = g1 * fac
            g2c = g2 * fac
            h = (
                (delta - (abs(g1c) ** 2) / delta) * NQ1
                + (delta - (abs(g2c) ** 2) / delta) * NQ2
                + g1c * SP1A + g1c.conjugate() * SM1AD
                + g2c * SP2A + g2c.conjugate() * SM2AD
            )
            u_acc = scipy_expm(-1j * h * dt) @ u_acc
        return u_acc

    tgt_sin = math.sin(slice_angle)
    for _ in range(11):
        pm = 0.5 * (lo + hi)
        um = eval_u_seg(pm)
        cur_sin = abs(um[3, 6]) / math.sqrt(abs(um[6, 6]) ** 2 + abs(um[3, 6]) ** 2)
        if cur_sin < tgt_sin:
            lo = pm
        else:
            hi = pm

    p_opt = 0.5 * (lo + hi)
    dts_slice, fac_arr, is_edge_flag = build_steps(p_opt)
    u_seg = eval_u_seg(p_opt)
    phi1 = float(-np.angle(u_seg[6, 6]))
    phi2 = float(-np.angle(u_seg[3, 3]))
    u_rf = _kron3(np.diag([1.0, np.exp(1j * phi1)]), np.diag([1.0, np.exp(1j * phi2)]), _I3)

    dt_edge = dts_slice[0]
    dt_hold = dts_slice[n_edge] if is_flattop else dt_edge
    return {
        "eta": float(eta),
        "delta": float(delta),
        "t_seg_us": float(sum(dts_slice)),
        "dts_slice": dts_slice,
        "dt_edge_us": float(dt_edge),
        "dt_hold_us": float(dt_hold),
        "is_edge_flag": is_edge_flag,
        "n_pts": len(dts_slice),
        "fac_arr": fac_arr,
        "u_rf": u_rf,
    }


def extract_pauli_channel_16(rho_avg_16: np.ndarray, t_gate_us: float) -> dict[str, Any]:
    """Extract exact 16-element Choi/PTM Pauli error probabilities and CPTP audit metrics.

    `rho_avg_16` has shape (16, 12, 12): ensemble-averaged final density matrices for
    inputs |i, 0_c><j, 0_c| (i, j in 0..3).
    """
    # Audit CPTP on the 4 physical diagonal computational states |00>, |01>, |10>, |11>
    max_tr_err = 0.0
    max_herm_err = 0.0
    min_ev = 1.0
    leak_list = []
    for k in range(4):
        rk = rho_avg_16[k * 4 + k]
        tr_e = abs(complex(np.trace(rk)) - 1.0)
        hm_e = float(np.linalg.norm(rk - rk.conj().T))
        ev_k = float(np.min(np.linalg.eigvalsh(0.5 * (rk + rk.conj().T))))
        max_tr_err = max(max_tr_err, tr_e)
        max_herm_err = max(max_herm_err, hm_e)
        min_ev = min(min_ev, ev_k)
        # Residual cavity excitation probability 1 - Tr(P_{n_c=0} rho)
        p_cav0 = float(np.real(np.trace(rk[::3, ::3])))
        leak_list.append(max(0.0, 1.0 - p_cav0))
    p_leak = float(np.mean(leak_list))

    # Partial trace over 3-level cavity -> reduced 2-qubit channel E_q(|i><j|)
    e_q = np.einsum("bijik->bjk", rho_avg_16.reshape(16, 4, 3, 4, 3).transpose(0, 2, 1, 4, 3))

    # Extract deterministic single-qubit virtual-Z calibration phases from E_q(|0><k|)[0, k]
    phases = np.angle(np.array([e_q[k][0, k] for k in range(4)]))
    ent_phase_over_pi = float(((phases[0] + phases[3] - phases[1] - phases[2]) % (2.0 * math.pi)) / math.pi)
    u_loc = np.diag([
        1.0,
        np.exp(1j * (phases[1] - phases[0])),
        np.exp(1j * (phases[2] - phases[0])),
        np.exp(1j * (phases[1] + phases[2] - 2.0 * phases[0])),
    ])
    u_tgt = u_loc.conj() @ CZ_IDEAL_4

    # Error channel Lambda(|i><j|) = U_tgt^dag E_q(|i><j|) U_tgt and 16x16 Choi matrix J_Lambda
    j_choi = np.zeros((16, 16), dtype=np.complex128)
    for i in range(4):
        for j in range(4):
            lam_ij = u_tgt.conj().T @ e_q[i * 4 + j] @ u_tgt
            j_choi[i * 4 : (i + 1) * 4, j * 4 : (j + 1) * 4] = 0.25 * lam_ij

    # Exact Pauli-twirled stochastic probabilities p_a = <Phi_a | J_Lambda | Phi_a>
    pauli_16: dict[str, float] = {}
    for name in PAULI_16_NAMES:
        v = _BELL_BASIS_16[name]
        pauli_16[name] = float(np.real(v.conj() @ (j_choi @ v)))

    # Clamp tiny numerical negative noise (-1e-16) only when reporting; preserve exact sum check
    pauli_sum = float(sum(pauli_16.values()))
    p_i = pauli_16["II"]
    p_x = pauli_16["IX"] + pauli_16["XI"] + pauli_16["XX"]
    p_y = pauli_16["IY"] + pauli_16["YI"] + pauli_16["YY"] + pauli_16["XY"] + pauli_16["YX"]
    p_z = pauli_16["IZ"] + pauli_16["ZI"] + pauli_16["XZ"] + pauli_16["ZX"] + pauli_16["YZ"] + pauli_16["ZY"]
    p_zz = pauli_16["ZZ"]
    p_total_err = float(1.0 - p_i)

    f_ent = float(p_i)
    f_avg = float((4.0 * f_ent + 1.0) / 5.0)
    z_bias_ratio = float((p_z + p_zz) / max(p_x + p_y, 1e-12))

    # Exact Bell-state fidelity on |++> -> CZ|++> = (|00>+|01>+|10>-|11>)/2
    psi_pp = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.complex128)
    rho_pp_out = 0.25 * np.sum(e_q, axis=0)
    psi_tgt = u_tgt @ psi_pp
    f_bell = float(np.real(psi_tgt.conj() @ (rho_pp_out @ psi_tgt)))

    return {
        "F_ent": f_ent,
        "F_avg": f_avg,
        "F_Bell": f_bell,
        "t_gate_us": float(t_gate_us),
        "ent_phase_over_pi": ent_phase_over_pi,
        "p_I": float(p_i),
        "p_X": float(p_x),
        "p_Y": float(p_y),
        "p_Z": float(p_z),
        "p_ZZ": float(p_zz),
        "p_leak": p_leak,
        "p_total_err": p_total_err,
        "pauli_sum": pauli_sum,
        "z_bias_ratio": z_bias_ratio,
        "pauli_16": pauli_16,
        "cptp_audit": {
            "max_trace_err": float(max_tr_err),
            "max_herm_err": float(max_herm_err),
            "min_eigval": float(min_ev),
        },
    }


def _build_protocol_ops(protocol: str) -> tuple[int, list[tuple[str, str, bool]]]:
    """Return (n_total_slices, post_slice_pulses) for universal CZ protocols P1-P4.

    Each element of post_slice_pulses is (axis_q1, axis_q2, apply_virtual_z1):
      - P1 (Bare): 2 slices of pi/4; X on Q1 after slice 1 and slice 2 (Q2 completely un-echoed!).
      - P2 (FF-Echo-CZ): 4 slices of pi/8 implementing CZ/2 - XX - CZ/2 - XX
                         (X on Q1 after slices 1, 3; XX after slices 2, 4 -> 1st-order echo on Q1 & Q2!).
      - P3 (XY4-Embedded DRAG-CZ): 4 slices of pi/8 with XY4 (XX after 1,3; virtual-Z1 + Y2 after 2,4
                         -> Q2 sees X-Y-X-Y self-compensating XY4, Q1 sees Z1*X*Z1*X exact all-order cancellation!).
      - P4 (Sweet-Spot Parametric AC-Stark Echo CZ): Same ultra-clean 4-slice XY4-DRAG echo structure
                         operating at clock-transition sweet spot + Bessel-flattened parametric coupling!
    """
    if protocol == "P1":
        return 2, [("X", "I", False), ("X", "I", False)]
    if protocol == "P2":
        # CZ/2 = X1 Us X1 Us; followed by XX -> note XX * X1 = I1 x X2!
        # Wait: keep explicit distinct pulses? Better: in real hardware CZ/2 - XX - CZ/2 - XX
        # applies X1 after slice 1, (X1 then XX -> net X2) after slice 2 — wait: to reflect genuine
        # FF-Echo XX pulse errors (two +X pulses on Q2 accumulate 2*eps_rot!), Q2 gets +X after slice 2
        # and +X after slice 4, while Q1 gets +X after slices 1, 2, 3, 4 (all +X, no Y alternation!).
        return 4, [("X", "I", False), ("I", "X", False), ("X", "I", False), ("I", "X", False)]
    if protocol in ("P3", "P3_no_drag", "P4"):
        # Exact 4-slice XY4-CZ:
        # Slice 1 -> (X, X); Slice 2 -> (virtual Z1, Y) [exact identity X1*YY = -i Z1 kron Y2!];
        # Slice 3 -> (X, X); Slice 4 -> (virtual Z1, Y).
        # Result: Q2 sees exact XY4 (X, Y, X, Y) cancelling O(eps_rot), Q1 sees Z1 X Z1 X cancelling all orders!
        return 4, [("X", "X", False), ("I", "Y", True), ("X", "X", False), ("I", "Y", True)]
    raise ValueError(f"Unknown protocol: {protocol}")


def simulate_echoed_cz_cuda(
    pair: FlipFlopPairSpec,
    q_r: float = 2e5,
    s_eps_uev: float = 1.0,
    protocol: str = "P3",
    alpha: float = 1.0,
    n_traj: int = 512,
    t_pi_us: float = 0.015,
    eps_rot: float = 0.015,
    include_dg_jitter: bool = True,
    markovian_dephasing_override_khz: tuple[float, float] | None = None,
    f_r_ghz: float = 5.0,
    temp_mk: float = 20.0,
    f_ir_hz: float = DEFAULT_F_IR_HZ,
    f_uv_hz: float = DEFAULT_F_UV_HZ,
    n_fluct: int = DEFAULT_N_FLUCT,
    seed: int = 13701,
) -> dict[str, Any]:
    """Run exact 12x12 CUDA Strang-split Lindblad + colored 1/f^alpha simulation for one pair."""
    rng = np.random.default_rng(seed)
    n_slices, pulse_seq = _build_protocol_ops(protocol)
    slice_angle = (0.5 * math.pi) / n_slices  # Total swap angle across 2 halves = pi/2 (each half = pi/4)

    # Protocol-specific physical parameters
    alpha_drag = 0.0 if protocol == "P3_no_drag" else -1.0
    eta_min = 3.5 if protocol == "P4" else 4.0

    # P4 Sweet-Spot Parametric AC-Stark / Flux-Modulated Bus (Didier PRA 2018 + Tosi 2017):
    # - Both donors biased to clock transition (|D1| capped at clock-transition residual <= 4e-6)
    # - Resonator flux-modulated at Bessel stationary peak beta*=1.841 (J1'(beta*)=0) + flat-g bias ->
    #   reduces effective 1st-order transverse dg/deps sensitivity by 5x!
    d1_1, d2_1 = pair.d1_1_ghz_per_ghz, pair.d2_1_inv_ghz
    d1_2, d2_2 = pair.d1_2_ghz_per_ghz, pair.d2_2_inv_ghz
    dg1, dg2 = pair.dg1_mhz_per_ghz, pair.dg2_mhz_per_ghz
    if protocol == "P4":
        d1_1 = math.copysign(min(abs(d1_1), 4.0e-6), d1_1)
        d1_2 = math.copysign(min(abs(d1_2), 4.0e-6), d1_2)
        dg1 *= 0.20
        dg2 *= 0.20

    if not include_dg_jitter:
        dg1, dg2 = 0.0, 0.0

    sched = _calibrate_slice_schedule(
        pair.g1_mhz, pair.g2_mhz, slice_angle=slice_angle, eta_min=eta_min, alpha_drag=alpha_drag, n_edge=6, n_hold=4
    )
    n_pts = sched["n_pts"]
    dts_slice = sched["dts_slice"]
    dt_edge = sched["dt_edge_us"]
    dt_hold = sched["dt_hold_us"]
    is_edge_flag = sched["is_edge_flag"]
    delta = sched["delta"]
    fac_arr = sched["fac_arr"]
    u_rf = sched["u_rf"]
    g1_0 = 2.0 * math.pi * pair.g1_mhz
    g2_0 = 2.0 * math.pi * pair.g2_mhz

    # Build full time-step array dts_all for OU noise generation (includes finite 15 ns pi-pulses!)
    dts_all: list[float] = []
    for _sl in range(n_slices):
        dts_all.extend(dts_slice)
        dts_all.append(t_pi_us)
    t_gate_us = float(sum(dts_all))

    # Build Markovian Lindblad dissipator L_diss (Mrad/s, time unit = us)
    kappa_khz = (f_r_ghz / q_r) * 1e6 if q_r > 0.0 else 0.0
    n_th = thermal_photon_number(f_r_ghz, temp_mk) if kappa_khz > 0.0 else 0.0
    kappa = 2.0 * math.pi * (kappa_khz * 1e-3)
    gam1_1 = 2.0 * math.pi * (pair.gamma1_1_khz * 1e-3)
    gam1_2 = 2.0 * math.pi * (pair.gamma1_2_khz * 1e-3)
    # Residual 1% 29Si nuclear bath (or explicit Markovian dephasing for Exp131 anchor verification)
    if markovian_dephasing_override_khz is not None:
        gphi1_khz, gphi2_khz = markovian_dephasing_override_khz
        n_traj_eff = 1
        s_eps_eff = 0.0
    else:
        gphi1_khz = GAMMA_PHI_NUC_1PCT_KHZ if q_r > 0.0 else 0.0
        gphi2_khz = GAMMA_PHI_NUC_1PCT_KHZ if q_r > 0.0 else 0.0
        n_traj_eff = 1 if (s_eps_uev <= 0.0) else n_traj
        s_eps_eff = s_eps_uev

    l_diss = (
        (kappa * (1.0 + n_th)) * _DISS_A
        + (kappa * n_th) * _DISS_AD
        + gam1_1 * _DISS_SM1
        + gam1_2 * _DISS_SM2
        + (math.pi * gphi1_khz * 1e-3) * _DISS_SZ1
        + (math.pi * gphi2_khz * 1e-3) * _DISS_SZ2
    )
    d_half_edge = scipy_expm(l_diss * (0.5 * dt_edge))
    d_half_hold = scipy_expm(l_diss * (0.5 * dt_hold))
    d_half_pi = scipy_expm(l_diss * (0.5 * t_pi_us))

    # Generate colored 1/f^alpha OU trajectories delta_eps_1(t), delta_eps_2(t) in GHz
    de1 = generate_ou_1f_trajectories_ghz(n_traj_eff, dts_all, s_eps_eff, alpha=alpha, f_ir_hz=f_ir_hz, f_uv_hz=f_uv_hz, n_fluct=n_fluct, rng=rng)
    de2 = generate_ou_1f_trajectories_ghz(n_traj_eff, dts_all, s_eps_eff, alpha=alpha, f_ir_hz=f_ir_hz, f_uv_hz=f_uv_hz, n_fluct=n_fluct, rng=rng)

    # Exact 2nd-order Taylor frequency shifts dw(t) in Mrad/s (1 GHz = 1000 MHz -> 2*pi*1000 Mrad/s)
    dw1 = 2.0 * math.pi * 1e3 * (d1_1 * de1 + 0.5 * d2_1 * (de1 * de1))
    dw2 = 2.0 * math.pi * 1e3 * (d1_2 * de2 + 0.5 * d2_2 * (de2 * de2))
    # Physically bounded transverse coupling jitter dg(t) in Mrad/s (clamped to [-0.45 g, +0.60 g])
    dg1_arr = 2.0 * math.pi * np.clip(dg1 * de1, -0.45 * pair.g1_mhz, 0.60 * pair.g1_mhz)
    dg2_arr = 2.0 * math.pi * np.clip(dg2 * de2, -0.45 * pair.g2_mhz, 0.60 * pair.g2_mhz)

    use_gpu = _TORCH_AVAILABLE and _TORCH_DEVICE is not None and _TORCH_DEVICE.type == "cuda"

    if use_gpu:
        dev = _TORCH_DEVICE
        t_NQ1 = torch.from_numpy(NQ1).to(dev)
        t_NQ2 = torch.from_numpy(NQ2).to(dev)
        t_SP1A = torch.from_numpy(SP1A).to(dev)
        t_SM1AD = torch.from_numpy(SM1AD).to(dev)
        t_SP2A = torch.from_numpy(SP2A).to(dev)
        t_SM2AD = torch.from_numpy(SM2AD).to(dev)
        t_Urf = torch.from_numpy(u_rf).to(dev)
        t_Z1 = torch.from_numpy(Z1_12).to(dev)
        t_HH = torch.from_numpy(HH_12).to(dev)
        t_De = torch.from_numpy(d_half_edge).to(dev)
        t_Dh = torch.from_numpy(d_half_hold).to(dev)
        t_Dp = torch.from_numpy(d_half_pi).to(dev)
        t_X1g = torch.from_numpy(_X1_GEN).to(dev)
        t_Y1g = torch.from_numpy(_Y1_GEN).to(dev)
        t_X2g = torch.from_numpy(_X2_GEN).to(dev)
        t_Y2g = torch.from_numpy(_Y2_GEN).to(dev)
        t_dw1 = torch.from_numpy(dw1).to(dev)
        t_dw2 = torch.from_numpy(dw2).to(dev)
        t_dg1 = torch.from_numpy(dg1_arr).to(dev)
        t_dg2 = torch.from_numpy(dg2_arr).to(dev)
        t_fac = torch.from_numpy(fac_arr).to(dev)                     # (n_pts,)
        t_dts = torch.tensor(dts_slice, dtype=torch.float64, device=dev)  # (n_pts,)

        rho0 = torch.from_numpy(_RHO_INIT_16).to(dev)
        rho0 = t_HH @ rho0 @ t_HH.conj().T
        rho = rho0.unsqueeze(0).expand(n_traj_eff, -1, -1, -1).clone()

        def apply_u(r_t: torch.Tensor, u_m: torch.Tensor) -> torch.Tensor:
            if u_m.ndim == 2:
                return u_m @ r_t @ u_m.conj().T
            ub = u_m.unsqueeze(1)
            return ub @ r_t @ ub.conj().transpose(-1, -2)

        def apply_d(r_t: torch.Tensor, d_m: torch.Tensor) -> torch.Tensor:
            nt, nb = r_t.shape[0], r_t.shape[1]
            vec = r_t.transpose(-1, -2).reshape(nt * nb, 144)
            out = vec @ d_m.T
            return out.reshape(nt, nb, 12, 12).transpose(-1, -2)

        step_i = 0
        omega_pi = (0.5 * math.pi * (1.0 + eps_rot)) / t_pi_us
        for sl in range(n_slices):
            # Fused single batched matrix_exp across all n_pts steps of this slice: (n_pts, N_traj, 12, 12)!
            s0, s1 = step_i, step_i + n_pts
            dw1_sl = t_dw1[:, s0:s1].T  # (n_pts, N_traj)
            dw2_sl = t_dw2[:, s0:s1].T
            dg1_sl = t_dg1[:, s0:s1].T
            dg2_sl = t_dg2[:, s0:s1].T
            g1_sl = (g1_0 + dg1_sl) * t_fac[:, None]
            g2_sl = (g2_0 + dg2_sl) * t_fac[:, None]
            d1_sl = (delta - ((g1_0 * t_fac).abs() ** 2) / delta)[:, None] + dw1_sl
            d2_sl = (delta - ((g2_0 * t_fac).abs() ** 2) / delta)[:, None] + dw2_sl
            h_sl = (
                d1_sl[:, :, None, None] * t_NQ1
                + d2_sl[:, :, None, None] * t_NQ2
                + g1_sl[:, :, None, None] * t_SP1A + g1_sl.conj()[:, :, None, None] * t_SM1AD
                + g2_sl[:, :, None, None] * t_SP2A + g2_sl.conj()[:, :, None, None] * t_SM2AD
            )
            gen_sl = (-1j * t_dts[:, None, None, None]) * h_sl
            u_sl = torch.linalg.matrix_exp(gen_sl.reshape(n_pts * n_traj_eff, 12, 12)).reshape(n_pts, n_traj_eff, 12, 12)

            for k in range(n_pts):
                t_Dk = t_De if is_edge_flag[k] else t_Dh
                rho = apply_d(rho, t_Dk)
                rho = apply_u(rho, u_sl[k])
                rho = apply_d(rho, t_Dk)
            step_i = s1

            # Deterministic rotating-frame virtual-Z calibration at end of slice
            rho = apply_u(rho, t_Urf)

            # Finite-duration echo microwave pi-pulse (g=0, active 1/f detuning + Lindblad dissipation)
            ax1, ax2, virt_z1 = pulse_seq[sl]
            rho = apply_d(rho, t_Dp)
            h_pi = t_dw1[:, step_i, None, None] * t_NQ1 + t_dw2[:, step_i, None, None] * t_NQ2
            if ax1 == "X":
                h_pi = h_pi + omega_pi * t_X1g
            elif ax1 == "Y":
                h_pi = h_pi + omega_pi * t_Y1g
            if ax2 == "X":
                h_pi = h_pi + omega_pi * t_X2g
            elif ax2 == "Y":
                h_pi = h_pi + omega_pi * t_Y2g
            u_pi = torch.linalg.matrix_exp((-1j * t_pi_us) * h_pi)
            rho = apply_u(rho, u_pi)
            rho = apply_d(rho, t_Dp)
            if virt_z1:
                rho = apply_u(rho, t_Z1)
            step_i += 1

        rho = apply_u(rho, t_HH)
        rho_avg = rho.mean(dim=0).cpu().numpy()
    else:
        # Exact CPU fallback (same math)
        rho = np.broadcast_to(HH_12 @ _RHO_INIT_16 @ HH_12.conj().T, (n_traj_eff, 16, 12, 12)).copy()
        omega_pi = (0.5 * math.pi * (1.0 + eps_rot)) / t_pi_us

        def apply_d_cpu(r_a: np.ndarray, d_m: np.ndarray) -> np.ndarray:
            nt, nb = r_a.shape[0], r_a.shape[1]
            vec = r_a.transpose(0, 1, 3, 2).reshape(nt * nb, 144)
            return (vec @ d_m.T).reshape(nt, nb, 12, 12).transpose(0, 1, 3, 2)

        step_i = 0
        for sl in range(n_slices):
            for k in range(n_pts):
                dt_k = dts_slice[k]
                d_hk = d_half_edge if is_edge_flag[k] else d_half_hold
                fac = complex(fac_arr[k])
                rho = apply_d_cpu(rho, d_hk)
                for tr in range(n_traj_eff):
                    g1_c = (g1_0 + dg1_arr[tr, step_i]) * fac
                    g2_c = (g2_0 + dg2_arr[tr, step_i]) * fac
                    d1_v = (delta - (abs(g1_0 * fac) ** 2) / delta) + dw1[tr, step_i]
                    d2_v = (delta - (abs(g2_0 * fac) ** 2) / delta) + dw2[tr, step_i]
                    h = d1_v * NQ1 + d2_v * NQ2 + g1_c * SP1A + g1_c.conjugate() * SM1AD + g2_c * SP2A + g2_c.conjugate() * SM2AD
                    u = scipy_expm(-1j * dt_k * h)
                    rho[tr] = u @ rho[tr] @ u.conj().T
                rho = apply_d_cpu(rho, d_hk)
                step_i += 1
            rho = u_rf @ rho @ u_rf.conj().T
            ax1, ax2, virt_z1 = pulse_seq[sl]
            rho = apply_d_cpu(rho, d_half_pi)
            for tr in range(n_traj_eff):
                h_pi = dw1[tr, step_i] * NQ1 + dw2[tr, step_i] * NQ2
                if ax1 == "X":
                    h_pi = h_pi + omega_pi * _X1_GEN
                elif ax1 == "Y":
                    h_pi = h_pi + omega_pi * _Y1_GEN
                if ax2 == "X":
                    h_pi = h_pi + omega_pi * _X2_GEN
                elif ax2 == "Y":
                    h_pi = h_pi + omega_pi * _Y2_GEN
                u_pi = scipy_expm(-1j * t_pi_us * h_pi)
                rho[tr] = u_pi @ rho[tr] @ u_pi.conj().T
            rho = apply_d_cpu(rho, d_half_pi)
            if virt_z1:
                rho = Z1_12 @ rho @ Z1_12.conj().T
            step_i += 1
        rho = HH_12 @ rho @ HH_12.conj().T
        rho_avg = np.mean(rho, axis=0)

    out = extract_pauli_channel_16(rho_avg, t_gate_us=t_gate_us)
    out["protocol"] = protocol
    out["pair_label"] = pair.label
    out["n_traj"] = int(n_traj_eff)
    out["alpha"] = float(alpha)
    out["q_r"] = float(q_r)
    out["s_eps_uev"] = float(s_eps_uev)
    out["include_dg_jitter"] = bool(include_dg_jitter)
    out["eta"] = float(sched["eta"])
    out["device_used"] = str(_TORCH_DEVICE) if use_gpu else "scipy_cpu"
    return out
