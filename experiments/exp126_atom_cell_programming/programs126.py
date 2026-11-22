"""Exp126 quantum program compiler, electron-mediated entanglers (CZ/CNOT/CPhi/CCZ), and 32D noisy executor.

Compiles 5 canonical logical quantum programs (Bell, GHZ-4, QFT-3, BitFlip-3 QEC, Grover-2)
onto any certified heterogeneous silicon atom cell's GRAPE + interleaved XY8 pulse library,
executes them in full 2^5 = 32-dimensional Hilbert space under ideal, static corner (+-400 Hz x +-2%),
and calibrated time-domain 1/omega^alpha bath noise + electron pi-pulse error models, and computes
exact state/subspace fidelities, electron disentanglement leakage, and parallel array timing.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

import grape_dd126 as g126
import hamiltonian126 as h126


@dataclass
class ScheduleOp:
    kind: str                                      # "RF_WAVEFORM", "VIRTUAL_RZ_NUC", "ELECTRON_ROT"
    waveform: Optional[g126.PulseWaveform] = None
    qubit: int = 0
    axis: str = "Z"
    angle_rad: float = 0.0
    duration_us: float = 0.0


@dataclass
class CompiledProgram:
    name: str
    cell_id: str
    ops: List[ScheduleOp]
    ideal_state_32d: np.ndarray                    # Exact 32D target statevector (for full-state programs)
    total_duration_us: float
    electron_superposition_us: float
    n_rf_pulses: int
    n_dd_electron_pi_pulses: int
    n_two_qubit_blocks: int
    logical_qubits: Tuple[int, ...] = (0, 1, 2, 3)
    notes: str = ""

    def to_metadata_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "cell_id": self.cell_id,
            "total_duration_us": float(self.total_duration_us),
            "electron_superposition_us": float(self.electron_superposition_us),
            "n_rf_pulses": int(self.n_rf_pulses),
            "n_dd_electron_pi_pulses": int(self.n_dd_electron_pi_pulses),
            "n_two_qubit_blocks": int(self.n_two_qubit_blocks),
            "logical_qubits": list(self.logical_qubits),
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Schedule builders (logical -> physical RF/MW + interleaved XY8-GRAPE ops)
# ---------------------------------------------------------------------------
def _rz_nuc(k: int, angle_rad: float) -> ScheduleOp:
    return ScheduleOp(kind="VIRTUAL_RZ_NUC", qubit=k, axis="Z", angle_rad=float(angle_rad), duration_us=0.0)


def _e_rot(axis: str, angle_rad: float) -> ScheduleOp:
    # Fast broadband ESR/MW electron rotation (~50 ns, negligible compared to 500 us nuclear RF)
    dur = 0.0 if axis == "Z" else 0.05
    return ScheduleOp(kind="ELECTRON_ROT", qubit=-1, axis=axis, angle_rad=float(angle_rad), duration_us=dur)


def _rf(wf: g126.PulseWaveform) -> ScheduleOp:
    return ScheduleOp(kind="RF_WAVEFORM", waveform=wf, qubit=wf.target_qubit, duration_us=wf.duration_us)


def emit_h(lib: g126.CellPulseLibrary, k: int) -> List[ScheduleOp]:
    """H_k = i * Rz_k(pi/2) * Rx_k(pi/2) * Rz_k(pi/2) (1 physical RF pulse + 2 zero-time virtual Z)."""
    return [_rz_nuc(k, +0.5 * math.pi), _rf(lib.rx_pi2[k]), _rz_nuc(k, +0.5 * math.pi)]


def emit_rx(lib: g126.CellPulseLibrary, k: int, theta_rad: float) -> List[ScheduleOp]:
    """Arbitrary Rx_k(theta) via Rz(-pi/2) Rx(pi/2) Rz(theta) Rx(pi/2) Rz(+pi/2) (exact up to global phase)."""
    # Verify: Rz(pi/2) Rx(pi/2) Rz(-theta) Rx(-pi/2) Rz(-pi/2)?
    # Even simpler: H_k * Rz_k(theta) * H_k = Rx_k(theta)!! (2 physical Rx(pi/2) pulses!)
    return emit_h(lib, k) + [_rz_nuc(k, theta_rad)] + emit_h(lib, k)


def emit_cphi(
    lib: g126.CellPulseLibrary,
    i: int,
    j: int,
    phi_rad: float,
    cx_override: Optional[Dict[int, g126.PulseWaveform]] = None,
) -> List[ScheduleOp]:
    """Exact electron-mediated two-nucleus Controlled-Phase CPhi(i, j; phi) = diag(1, 1, 1, exp(i*phi)).

    Starts and ends with donor electron cleanly disentangled in |0_e>.
    Single-qubit H_i, H_j execute while electron is in |0_e> (zero T2e exposure).
    Only the 4 interleaved XY8-GRAPE cX pulses execute while electron is in superposition.
    """
    cx = cx_override or lib.cx_e_to_n
    ops: List[ScheduleOp] = []
    ops.extend(emit_h(lib, i))
    ops.extend(emit_h(lib, j))
    ops.append(_e_rot("X", -0.5 * math.pi))        # |0_e> -> |+y_e>
    ops.append(_rf(cx[j]))
    ops.append(_rf(cx[i]))
    ops.append(_e_rot("Y", -0.5 * phi_rad))        # exp(+i (phi/4) Y_e)
    ops.append(_rf(cx[i]))
    ops.append(_rf(cx[j]))
    ops.append(_e_rot("X", +0.5 * math.pi))        # |+y_e> -> |0_e>
    ops.extend(emit_h(lib, i))
    ops.extend(emit_h(lib, j))
    ops.append(_rz_nuc(i, +0.5 * phi_rad))
    ops.append(_rz_nuc(j, +0.5 * phi_rad))
    return ops


def emit_cz(lib: g126.CellPulseLibrary, i: int, j: int,
            cx_override: Optional[Dict[int, g126.PulseWaveform]] = None) -> List[ScheduleOp]:
    return emit_cphi(lib, i, j, math.pi, cx_override=cx_override)


def emit_cnot(lib: g126.CellPulseLibrary, ctrl: int, tgt: int,
              cx_override: Optional[Dict[int, g126.PulseWaveform]] = None) -> List[ScheduleOp]:
    """CNOT(ctrl -> tgt) = H_tgt * CZ(ctrl, tgt) * H_tgt (canceling the leading H_tgt * H_tgt = I)."""
    cx = cx_override or lib.cx_e_to_n
    ops: List[ScheduleOp] = []
    # Leading H_tgt cancels with CZ's leading H_tgt! Only emit H_ctrl before electron superposition.
    ops.extend(emit_h(lib, ctrl))
    ops.append(_e_rot("X", -0.5 * math.pi))
    ops.append(_rf(cx[tgt]))
    ops.append(_rf(cx[ctrl]))
    ops.append(_e_rot("Y", -0.5 * math.pi))
    ops.append(_rf(cx[ctrl]))
    ops.append(_rf(cx[tgt]))
    ops.append(_e_rot("X", +0.5 * math.pi))
    ops.extend(emit_h(lib, ctrl))
    ops.extend(emit_h(lib, tgt))
    ops.append(_rz_nuc(ctrl, +0.5 * math.pi))
    ops.append(_rz_nuc(tgt, +0.5 * math.pi))
    ops.extend(emit_h(lib, tgt))
    return ops


def emit_ccz_012(lib: g126.CellPulseLibrary,
                 cx_override: Optional[Dict[int, g126.PulseWaveform]] = None) -> List[ScheduleOp]:
    """Native electron-hub 3-qubit CCZ(0, 1, 2) = diag(1,1,1,1,1,1,1,-1) using 3-body W3 + three 2-body CPhi."""
    cx = cx_override or lib.cx_e_to_n
    ops: List[ScheduleOp] = []
    # exp(-i (pi/8) Z0 Z1 Z2) via native 3-body W3 block:
    for q in (0, 1, 2):
        ops.extend(emit_h(lib, q))
    ops.append(_e_rot("X", -0.5 * math.pi))
    ops.extend([_rf(cx[0]), _rf(cx[1]), _rf(cx[2])])
    ops.append(_e_rot("Y", +0.25 * math.pi))  # exp(-i (pi/8) Y_e) -> exp(-i (pi/8) Z0 Z1 Z2)
    ops.extend([_rf(cx[2]), _rf(cx[1]), _rf(cx[0])])
    ops.append(_e_rot("X", +0.5 * math.pi))
    for q in (0, 1, 2):
        ops.extend(emit_h(lib, q))
    # Plus pairwise exp(+i (pi/8) (Z0Z1 + Z0Z2 + Z1Z2)) and local Z:
    # Since CPhi(i,j; pi/2) = e^{-i pi/8} exp(+i pi/8 (ZiZj - Zi - Zj)), multiplying all 3 gives
    # exp(+i pi/8 (Z0Z1+Z0Z2+Z1Z2)) * exp(-i pi/4 (Z0+Z1+Z2)); then add Rz(-pi/4) on 0,1,2 -> exp(-i pi/8 (Z0+Z1+Z2))!
    ops.extend(emit_cphi(lib, 0, 1, +0.5 * math.pi, cx_override=cx))
    ops.extend(emit_cphi(lib, 0, 2, +0.5 * math.pi, cx_override=cx))
    ops.extend(emit_cphi(lib, 1, 2, +0.5 * math.pi, cx_override=cx))
    for q in (0, 1, 2):
        ops.append(_rz_nuc(q, -0.25 * math.pi))
    return ops


# ---------------------------------------------------------------------------
# Exact ideal 32D reference state builders
# ---------------------------------------------------------------------------
def _ideal_basis_state(bits_5: str) -> np.ndarray:
    idx = int(bits_5, 2)
    v = np.zeros(32, dtype=np.complex128)
    v[idx] = 1.0
    return v


def _ideal_bell_state() -> np.ndarray:
    # |0_e> x (|0000> + |1100>)/sqrt(2)
    return (_ideal_basis_state("00000") + _ideal_basis_state("01100")) / math.sqrt(2.0)


def _ideal_ghz4_state() -> np.ndarray:
    # (|0_e 1111> + |1_e 0000>)/sqrt(2)  (exact action of cX_{e->0..3} on (|0_e>+|1_e>)|0000>/sqrt(2)!)
    return (_ideal_basis_state("01111") + _ideal_basis_state("10000")) / math.sqrt(2.0)


def _ideal_qft3_on_101() -> np.ndarray:
    # 3-qubit QFT (without final physical SWAP, standard bit-reversed output order q2,q1,q0) on |x=5> = |101>
    # Exact circuit: X0, X2 -> H0 -> CS(1,0) -> CT(2,0) -> H1 -> CS(2,1) -> H2 on qubits (0,1,2), q3=0, e=0
    st = _ideal_basis_state("01010")  # e=0, q0=1, q1=0, q2=1, q3=0
    H = h126.HADAMARD_2
    def apply_1q(vec, mat, q_pos):
        U = h126.single_op(mat, q_pos, 5)
        return U @ vec
    def apply_cphi(vec, qa, qb, phi):
        out = vec.copy()
        for idx in range(32):
            ba = (idx >> (4 - qa)) & 1
            bb = (idx >> (4 - qb)) & 1
            if ba == 1 and bb == 1:
                out[idx] *= np.exp(1j * phi)
        return out
    st = apply_1q(st, H, 1)
    st = apply_cphi(st, 2, 1, math.pi / 2.0)
    st = apply_cphi(st, 3, 1, math.pi / 4.0)
    st = apply_1q(st, H, 2)
    st = apply_cphi(st, 3, 2, math.pi / 2.0)
    st = apply_1q(st, H, 3)
    return st


def _ideal_grover2_11() -> np.ndarray:
    return _ideal_basis_state("01100")


def _ideal_bitflip_logical_qubit0() -> np.ndarray:
    # |psi_L> = Rx(-0.4*pi) |0> = cos(0.2*pi)|0> + i sin(0.2*pi)|1>
    # Notice <psi_L|X|psi_L> = 0 => unencoded X error gives EXACT 0.000 fidelity!
    th = 0.2 * math.pi
    return np.array([math.cos(th), 1.0j * math.sin(th)], dtype=np.complex128)


# ---------------------------------------------------------------------------
# Schedule execution engine (full 32D ideal, static corners, or noisy MC)
# ---------------------------------------------------------------------------
def _schedule_stats(ops: Sequence[ScheduleOp]) -> Tuple[float, float, int, int, int]:
    total_us = 0.0
    esup_us = 0.0
    n_rf = 0
    n_dd = 0
    n_2q = 0
    in_sup = False
    for op in ops:
        total_us += op.duration_us
        if op.kind == "ELECTRON_ROT" and op.axis in ("X", "Y", "H"):
            if abs(abs(op.angle_rad) - 0.5 * math.pi) < 1e-6 or op.axis == "H":
                if op.axis == "X" and op.angle_rad < 0:
                    in_sup = True
                    n_2q += 1
                elif op.axis == "X" and op.angle_rad > 0:
                    in_sup = False
                elif op.axis == "H":
                    in_sup = not in_sup
        if op.kind == "RF_WAVEFORM" and op.waveform is not None:
            n_rf += 1
            n_dd += op.waveform.n_dd
            if in_sup or op.waveform.gate_name == "cX":
                esup_us += op.duration_us
    return total_us, esup_us, n_rf, n_dd, n_2q


def compile_program(
    name: str,
    lib: g126.CellPulseLibrary,
    cx_override: Optional[Dict[int, g126.PulseWaveform]] = None,
) -> CompiledProgram:
    """Compile a named logical quantum program onto cell-specific GRAPE + XY8 schedules."""
    cx = cx_override or lib.cx_e_to_n
    ops: List[ScheduleOp] = []
    if name == "Bell":
        ops.extend(emit_h(lib, 0))
        ops.extend(emit_cnot(lib, 0, 1, cx_override=cx))
        ideal = _ideal_bell_state()
        lqs = (0, 1)
        notes = "H_0 -> CNOT(0->1) on nuclei (0,1); electron disentangled in |0_e>."
    elif name == "GHZ-4":
        ops.append(_e_rot("H", math.pi))
        for k in range(4):
            ops.append(_rf(cx[k]))
        ideal = _ideal_ghz4_state()
        lqs = (0, 1, 2, 3)
        notes = "H_e -> cX_{e->0..3} full 5-spin entangled GHZ_4 (exact Exp48/62/63 benchmark)."
    elif name == "QFT-3":
        # Prepare |101> on nuclei (0,1,2)
        ops.append(_rf(lib.x_gate[0]))
        ops.append(_rf(lib.x_gate[2]))
        ops.extend(emit_h(lib, 0))
        ops.extend(emit_cphi(lib, 1, 0, 0.5 * math.pi, cx_override=cx))
        ops.extend(emit_cphi(lib, 2, 0, 0.25 * math.pi, cx_override=cx))
        ops.extend(emit_h(lib, 1))
        ops.extend(emit_cphi(lib, 2, 1, 0.5 * math.pi, cx_override=cx))
        ops.extend(emit_h(lib, 2))
        ideal = _ideal_qft3_on_101()
        lqs = (0, 1, 2)
        notes = "3-qubit QFT on |101> using native electron-mediated CS/CT blocks (bit-reversed output)."
    elif name == "Grover-2":
        ops.extend(emit_h(lib, 0))
        ops.extend(emit_h(lib, 1))
        # Oracle marking |11>
        ops.extend(emit_cz(lib, 0, 1, cx_override=cx))
        # Diffuser: H H X X CZ X X H H
        ops.extend(emit_h(lib, 0)); ops.extend(emit_h(lib, 1))
        ops.append(_rf(lib.x_gate[0])); ops.append(_rf(lib.x_gate[1]))
        ops.extend(emit_cz(lib, 0, 1, cx_override=cx))
        ops.append(_rf(lib.x_gate[0])); ops.append(_rf(lib.x_gate[1]))
        ops.extend(emit_h(lib, 0)); ops.extend(emit_h(lib, 1))
        ideal = _ideal_grover2_11()
        lqs = (0, 1)
        notes = "2-qubit Grover search for marked state |11> on nuclei (0,1)."
    elif name == "BitFlip-3":
        # Prepare |psi_L> = Rx(-0.4*pi)|0> = cos(0.2*pi)|0> + i sin(0.2*pi)|1> on qubit 0
        ops.extend(emit_rx(lib, 0, -0.4 * math.pi))
        # Encode onto (0, 1, 2)
        ops.extend(emit_cnot(lib, 0, 1, cx_override=cx))
        ops.extend(emit_cnot(lib, 0, 2, cx_override=cx))
        # Inject physical single-qubit X error on data qubit 0 (worst case; unencoded fidelity = 0.000!)
        ops.append(_rf(lib.x_gate[0]))
        # Decode parity syndromes onto qubits (1, 2)
        ops.extend(emit_cnot(lib, 0, 1, cx_override=cx))
        ops.extend(emit_cnot(lib, 0, 2, cx_override=cx))
        # Note: final syndrome Z-measurement on (1,2) + conditional feedforward X_0 applied in executor!
        # Reference ideal post-recovery state on |0_e> x |psi_L> x |110>
        psi_l = _ideal_bitflip_logical_qubit0()
        ideal = np.zeros(32, dtype=np.complex128)
        ideal[int("00110", 2)] = psi_l[0]
        ideal[int("01110", 2)] = psi_l[1]
        lqs = (0, 1, 2)
        notes = "3-qubit Bit-Flip QEC: prepare |psi_L> (unencoded X-error F=0.000), encode, inject X_0, decode, syndrome feedforward."
    else:
        raise ValueError(f"Unknown program: {name}")

    tot_us, esup_us, n_rf, n_dd, n_2q = _schedule_stats(ops)
    return CompiledProgram(
        name=name, cell_id=lib.cell.cell_id, ops=ops, ideal_state_32d=ideal,
        total_duration_us=tot_us, electron_superposition_us=esup_us,
        n_rf_pulses=n_rf, n_dd_electron_pi_pulses=n_dd, n_two_qubit_blocks=n_2q,
        logical_qubits=lqs, notes=notes,
    )


def _apply_ops_32d(
    psi_init: torch.Tensor,
    ops: Sequence[ScheduleOp],
    cell: h126.CellSpec,
    noise_alpha: Optional[float] = None,
    eps_stoch: float = 0.0,
    delta_theta_sys: float = 0.0,
    offset_hz: float = 0.0,
    amp_scale: float = 1.0,
    seed: int = 126,
    device: Optional[torch.device] = None,
) -> torch.Tensor:
    """Execute a sequence of physical ScheduleOps on (n_traj, 32) complex128 statevectors in full 32D."""
    dev = device or psi_init.device
    spin_ops = h126.get_ops4()
    n_traj = psi_init.shape[0]
    rng = np.random.default_rng(seed)

    # Pre-sample one continuous stationary 1/omega^alpha bath noise trajectory spanning all RF slices
    total_slices = sum(op.waveform.n_slices for op in ops if op.kind == "RF_WAVEFORM" and op.waveform is not None)
    noise_all = None
    if noise_alpha is not None and total_slices > 0:
        # All waveforms share dt = duration_us / n_slices (500/64 us = 7.8125 us)
        first_wf = next(op.waveform for op in ops if op.kind == "RF_WAVEFORM" and op.waveform is not None)
        dt_s = (first_wf.duration_us * 1e-6) / first_wf.n_slices
        noise_all = h126.sample_bath_noise_hz(cell.t2e_s, noise_alpha, dt_s, total_slices, n_traj, rng)

    psi = psi_init.clone()
    slice_cursor = 0
    with torch.no_grad():
        for op in ops:
            if op.kind == "VIRTUAL_RZ_NUC":
                iz_d = np.diag(spin_ops.Iz[op.qubit]).real
                ph = torch.tensor(np.exp(-1.0j * op.angle_rad * iz_d), dtype=torch.complex128, device=dev)
                p = psi.view(n_traj, 2, 16) * ph.view(1, 1, 16)
                psi = p.reshape(n_traj, 32)
            elif op.kind == "ELECTRON_ROT":
                if op.axis == "H":
                    U_e = torch.tensor(h126.HADAMARD_2, dtype=torch.complex128, device=dev).unsqueeze(0).expand(n_traj, 2, 2)
                elif op.axis == "Z":
                    ang = 0.5 * op.angle_rad
                    U_mat = np.diag([np.exp(-1.0j * ang), np.exp(+1.0j * ang)])
                    U_e = torch.tensor(U_mat, dtype=torch.complex128, device=dev).unsqueeze(0).expand(n_traj, 2, 2)
                else:
                    ang = 0.5 * op.angle_rad
                    P = h126.PX if op.axis == "X" else h126.PY
                    U_mat = math.cos(ang) * h126.I2 - 1.0j * math.sin(ang) * P
                    U_e = torch.tensor(U_mat, dtype=torch.complex128, device=dev).unsqueeze(0).expand(n_traj, 2, 2)
                psi = g126._apply_electron_2x2_to_psi32(U_e, psi)
            elif op.kind == "RF_WAVEFORM" and op.waveform is not None:
                m_len = op.waveform.n_slices
                seg = noise_all[:, slice_cursor : slice_cursor + m_len] if noise_all is not None else None
                slice_cursor += m_len
                psi = g126.propagate_waveform_noisy_32d(
                    psi, cell, op.waveform, noise_hz_seg=seg,
                    eps_stoch=eps_stoch, delta_theta_sys=delta_theta_sys,
                    offset_hz=offset_hz, amp_scale=amp_scale, rng=rng, device=dev,
                )
    return psi


def execute_program_32d(
    prog: CompiledProgram,
    lib: g126.CellPulseLibrary,
    noise_alpha: Optional[float] = None,
    eps_stoch: float = 0.0,
    delta_theta_sys: float = 0.0,
    offset_hz: float = 0.0,
    amp_scale: float = 1.0,
    n_traj: int = 128,
    seed: int = 126,
    include_spectator_overlap: bool = True,
    device: Optional[torch.device] = None,
) -> Dict[str, float]:
    """Execute a compiled program from |0_e 0000> in full 32D and return exact state/logical fidelity."""
    dev = device or g126.get_device()
    n_run = 1 if (noise_alpha is None and eps_stoch == 0.0) else int(n_traj)
    psi0 = torch.zeros((n_run, 32), dtype=torch.complex128, device=dev)
    psi0[:, 0] = 1.0

    psi_out = _apply_ops_32d(
        psi0, prog.ops, lib.cell,
        noise_alpha=noise_alpha, eps_stoch=eps_stoch, delta_theta_sys=delta_theta_sys,
        offset_hz=offset_hz, amp_scale=amp_scale, seed=seed, device=dev,
    )
    norm_err = float((torch.linalg.norm(psi_out, dim=1) - 1.0).abs().max().item())

    if prog.name == "BitFlip-3":
        # Syndrome Z-measurement on qubits (1, 2) + classical feedforward physical GRAPE X_0 on syndrome (1,1)!
        # Compute exact post-feedforward reduced density matrix rho_q0 (2x2) averaged over trajectories!
        # Basis index bits: b4=e, b3=q0, b2=q1, b1=q2, b0=q3
        rho_q0 = np.zeros((2, 2), dtype=np.complex128)
        psi_np = psi_out.cpu().numpy()
        # Syndrome == (1, 1) indices mask:
        mask_11 = np.array([(((idx >> 2) & 1) == 1 and ((idx >> 1) & 1) == 1) for idx in range(32)], dtype=bool)
        # Apply physical GRAPE X_0 waveform on the syndrome-11 projected branch!
        psi_s11 = psi_out.clone()
        mask_11_t = torch.tensor(mask_11, dtype=torch.bool, device=dev)
        psi_s11[:, ~mask_11_t] = 0.0
        psi_s11_corr = g126.propagate_waveform_noisy_32d(
            psi_s11, lib.cell, lib.x_gate[0], noise_hz_seg=None,
            eps_stoch=0.0, offset_hz=offset_hz, amp_scale=amp_scale, device=dev,
        )
        psi_s11_corr_np = psi_s11_corr.cpu().numpy()
        # Remaining 3 syndromes (no feedforward correction):
        psi_other_np = psi_np.copy()
        psi_other_np[:, mask_11] = 0.0

        # Trace out (e, q1, q2, q3) separately for each measured syndrome branch (incoherent classical outcome sum!)
        for branch_np in (psi_s11_corr_np, psi_other_np):
            # Reshape (n_run, 2_e, 2_q0, 8_rest) -> sum over e and rest
            b = branch_np.reshape(n_run, 2, 2, 8)
            # rho_q0[a, c] = mean_traj sum_{e, rest} b[traj, e, a, rest] * conj(b[traj, e, c, rest])
            rho_b = np.einsum("teak,teck->ac", b, b.conj()) / float(n_run)
            rho_q0 += rho_b

        psi_l = _ideal_bitflip_logical_qubit0()
        fid_logical = float(np.real(psi_l.conj() @ rho_q0 @ psi_l))
        syndrome_11_prob = float(np.mean(np.sum(np.abs(psi_np[:, mask_11]) ** 2, axis=1)))
        # Electron disentanglement purity check (prob in |0_e>)
        p_e0 = float(np.mean(np.sum(np.abs(psi_np[:, :16]) ** 2, axis=1)))
        return {
            "fidelity": fid_logical,
            "syndrome_11_prob": syndrome_11_prob,
            "electron_p0": p_e0,
            "max_state_norm_err": norm_err,
            "unencoded_error_fidelity": 0.0,
        }

    # Standard full-state / GHZ-4 / Bell / QFT-3 / Grover-2 fidelity <psi_ideal | rho_out | psi_ideal>
    # Compute ensemble density matrix overlap directly: mean_traj |<psi_ideal | psi_traj>|^2
    # Wait: for GHZ-4, ALSO multiply |0_e><1_e| coherence by the exact 448-bath spectator branch overlap!
    psi_id_t = torch.tensor(prog.ideal_state_32d, dtype=torch.complex128, device=dev)
    overlaps = torch.matmul(psi_out, psi_id_t.conj())
    fid_32d = float((overlaps.abs() ** 2).mean().item())
    fid_std = float((overlaps.abs() ** 2).std().item()) if n_run > 1 else 0.0

    spec_ovl = 1.0
    fid_with_spec = fid_32d
    if prog.name == "GHZ-4" and include_spectator_overlap:
        rf_wfs = [op.waveform for op in prog.ops if op.kind == "RF_WAVEFORM" and op.waveform is not None]
        spec_ovl = g126.evaluate_sequence_spectator_overlap(lib.cell, rf_wfs, device=dev)
        # Exact density-matrix GHZ fidelity with spectator bath overlap:
        # |GHZ> = (|a> + |b>)/sqrt(2), where |a> = |0_e 1111> (idx 15), |b> = |1_e 0000> (idx 16).
        # rho_aa = mean |psi[15]|^2, rho_bb = mean |psi[16]|^2, rho_ab = mean psi[15]*conj(psi[16]) * spec_ovl.
        a_amp = psi_out[:, 15]
        b_amp = psi_out[:, 16]
        rho_aa = float((a_amp.abs() ** 2).mean().item())
        rho_bb = float((b_amp.abs() ** 2).mean().item())
        rho_ab = complex((a_amp * b_amp.conj()).mean().item())
        # Note: include |rho_ab| (or Re(rho_ab) for phase-locked GHZ! Wait: check exact phase!)
        fid_phase_locked = float(0.5 * (rho_aa + rho_bb + 2.0 * np.real(rho_ab) * spec_ovl))
        fid_abs_coh = float(0.5 * (rho_aa + rho_bb + 2.0 * abs(rho_ab) * spec_ovl))
        fid_with_spec = fid_phase_locked
        return {
            "fidelity": fid_with_spec,
            "fidelity_32d_active_only": fid_32d,
            "fidelity_abs_coherence": fid_abs_coh,
            "spectator_overlap_all": spec_ovl,
            "rho_aa": rho_aa,
            "rho_bb": rho_bb,
            "abs_rho_ab": float(abs(rho_ab)),
            "traj_std": fid_std,
            "max_state_norm_err": norm_err,
        }

    # For Bell / QFT-3 / Grover-2: electron returns to |0_e>, check electron leakage and success probability
    psi_np = psi_out.cpu().numpy()
    p_e0 = float(np.mean(np.sum(np.abs(psi_np[:, :16]) ** 2, axis=1)))
    res = {
        "fidelity": fid_32d,
        "traj_std": fid_std,
        "electron_p0": p_e0,
        "electron_leakage": float(max(0.0, 1.0 - p_e0)),
        "max_state_norm_err": norm_err,
    }
    if prog.name == "Grover-2":
        # Target |11> probability on nuclei (0,1) regardless of ancillas/phase
        mask_11 = np.array([(((idx >> 3) & 1) == 1 and ((idx >> 2) & 1) == 1) for idx in range(32)], dtype=bool)
        res["marked_11_prob"] = float(np.mean(np.sum(np.abs(psi_np[:, mask_11]) ** 2, axis=1)))
    return res


def evaluate_two_qubit_gate_32d(
    lib: g126.CellPulseLibrary,
    i: int,
    j: int,
    gate_type: str = "CZ",
    noise_alpha: Optional[float] = None,
    eps_stoch: float = 0.0,
    n_traj: int = 64,
    seed: int = 12650,
    device: Optional[torch.device] = None,
) -> Dict[str, float]:
    """Evaluate exact 16x16 nuclear subspace gate fidelity & electron disentanglement leakage for CZ(i,j) or CNOT(i->j)."""
    dev = device or g126.get_device()
    ops_seq = emit_cz(lib, i, j) if gate_type == "CZ" else emit_cnot(lib, i, j)

    # Ideal 16x16 nuclear target unitary on |0_e> subspace
    U_id = np.eye(16, dtype=np.complex128)
    if gate_type == "CZ":
        for idx in range(16):
            bi = (idx >> (3 - i)) & 1
            bj = (idx >> (3 - j)) & 1
            if bi == 1 and bj == 1:
                U_id[idx, idx] = -1.0
    elif gate_type == "CNOT":
        U_id = np.zeros((16, 16), dtype=np.complex128)
        for idx in range(16):
            bi = (idx >> (3 - i)) & 1
            out_idx = idx ^ (1 << (3 - j)) if bi == 1 else idx
            U_id[out_idx, idx] = 1.0
    else:
        raise ValueError(gate_type)

    if noise_alpha is None and eps_stoch == 0.0:
        # Exact noiseless 16-basis propagation in one batch!
        basis = torch.zeros((16, 32), dtype=torch.complex128, device=dev)
        for idx in range(16):
            basis[idx, idx] = 1.0
        out = _apply_ops_32d(basis, ops_seq, lib.cell, device=dev)
        out_np = out.cpu().numpy()  # (16_in, 32_out)
        U_sub = out_np[:, :16].T    # (16_out, 16_in) on |0_e> subspace
        leak = float(np.max(np.sum(np.abs(out_np[:, 16:]) ** 2, axis=1)))
        u_err = float(np.linalg.norm(out_np @ out_np.conj().T - np.eye(16), ord="fro"))
        # Process fidelity |Tr(U_id^dag U_sub)|^2 / 16^2
        f_proc = float((abs(np.sum(U_id.conj() * U_sub)) / 16.0) ** 2)
        return {
            "pair": [int(i), int(j)],
            "gate": gate_type,
            "subspace_process_fidelity": f_proc,
            "max_electron_leakage": leak,
            "isometry_fro_err": u_err,
        }

    # Noisy entanglement fidelity via exact Choi-state / 16-basis Monte Carlo average:
    # For each trajectory, share the SAME bath & pulse realization across all 16 basis states!
    # We batch (n_traj * 16, 32) directly —Wait: even simpler, test on the 4-state entangled
    # basis + computational superposition states OR share rng/noise across 16 basis cols per trajectory!
    # Sharing exact trajectory across 16 basis states gives TRUE average process fidelity F_proc = E[|Tr(U_id^dag U_traj)|^2/256]!
    rng = np.random.default_rng(seed)
    total_slices = sum(op.waveform.n_slices for op in ops_seq if op.kind == "RF_WAVEFORM" and op.waveform is not None)
    first_wf = next(op.waveform for op in ops_seq if op.kind == "RF_WAVEFORM" and op.waveform is not None)
    dt_s = (first_wf.duration_us * 1e-6) / first_wf.n_slices
    noise_all = h126.sample_bath_noise_hz(lib.cell.t2e_s, noise_alpha, dt_s, total_slices, n_traj, rng) if noise_alpha is not None else None

    # Repeat each trajectory's noise 16 times so all 16 input basis states see the EXACT same trajectory!
    # And draw electron pi-pulse errors per trajectory (repeated across the 16 basis states)!
    # Easiest exact way: evolve a (n_traj, 32, 16) batch or loop over n_traj batches of 16 basis states?
    # Even faster: evaluate 64 trajectories where each trajectory propagates 16 basis states as (16, 32)!
    # Wait: 64 trajectories x 4 cX gates x 64 slices on (16, 32) = fast (<1.5 s on CUDA)!
    f_procs = []
    leaks = []
    U_id_t = torch.tensor(U_id, dtype=torch.complex128, device=dev)
    basis_16 = torch.zeros((16, 32), dtype=torch.complex128, device=dev)
    for idx in range(16):
        basis_16[idx, idx] = 1.0

    with torch.no_grad():
        for tr in range(n_traj):
            # Single-trajectory noise repeated across the 16 basis columns
            psi = basis_16.clone()
            spin_ops = h126.get_ops4()
            cursor = 0
            for op in ops_seq:
                if op.kind == "VIRTUAL_RZ_NUC":
                    iz_d = np.diag(spin_ops.Iz[op.qubit]).real
                    ph = torch.tensor(np.exp(-1.0j * op.angle_rad * iz_d), dtype=torch.complex128, device=dev)
                    psi = (psi.view(16, 2, 16) * ph.view(1, 1, 16)).reshape(16, 32)
                elif op.kind == "ELECTRON_ROT":
                    ang = 0.5 * op.angle_rad
                    P = h126.PX if op.axis == "X" else h126.PY
                    U_mat = math.cos(ang) * h126.I2 - 1.0j * math.sin(ang) * P
                    U_e = torch.tensor(U_mat, dtype=torch.complex128, device=dev).unsqueeze(0).expand(16, 2, 2)
                    psi = g126._apply_electron_2x2_to_psi32(U_e, psi)
                elif op.kind == "RF_WAVEFORM" and op.waveform is not None:
                    wf = op.waveform
                    m_len = wf.n_slices
                    seg = np.repeat(noise_all[tr : tr + 1, cursor : cursor + m_len], 16, axis=0) if noise_all is not None else None
                    cursor += m_len
                    # Draw ONE set of electron pi-pulse errors per pulse shared across all 16 basis columns!
                    psi = _propagate_wf_shared_pi(psi, lib.cell, wf, seg, eps_stoch, rng, dev)
            U_sub = psi[:, :16].T
            f_p = float(((U_id_t.conj() * U_sub).sum().abs() / 16.0).item() ** 2)
            # Average gate fidelity on d=16 subspace: F_avg = (d * F_proc + 1) / (d + 1)
            f_procs.append(f_p)
            leaks.append(float((psi[:, 16:].abs() ** 2).sum(dim=1).mean().item()))

    mean_fp = float(np.mean(f_procs))
    return {
        "pair": [int(i), int(j)],
        "gate": gate_type,
        "noisy_process_fidelity_mean": mean_fp,
        "noisy_avg_gate_fidelity": float((16.0 * mean_fp + 1.0) / 17.0),
        "noisy_process_fidelity_std": float(np.std(f_procs)),
        "mean_electron_leakage": float(np.mean(leaks)),
        "n_traj": int(n_traj),
    }


def _propagate_wf_shared_pi(
    psi_16: torch.Tensor,
    cell: h126.CellSpec,
    wf: g126.PulseWaveform,
    noise_seg_16: Optional[np.ndarray],
    eps_stoch: float,
    rng: np.random.Generator,
    dev: torch.device,
) -> torch.Tensor:
    """Helper: propagate 16 basis columns through wf with ONE shared stochastic electron pi-pulse realization."""
    ops = h126.get_ops4()
    M = wf.n_slices
    T = wf.duration_us * 1e-6
    dt = T / M
    pulse_after, parities = g126.dd_schedule(M, wf.n_dd, wf.dd_sequence if wf.n_dd > 0 else "XY8")
    A_t = float(cell.A_hz[wf.target_qubit])
    H_dip = h126.nuclear_dipolar_hamiltonian(cell.J_hz, ops)

    H_slices = np.zeros((2, M, 16, 16), dtype=np.complex128)
    for bi, sz_phys in enumerate((+0.5, -0.5)):
        for m in range(M):
            pm = parities[m]
            H = H_dip.copy()
            for j in range(4):
                freq = float(cell.A_hz[j]) * sz_phys - pm * 0.5 * A_t
                H += 2.0 * math.pi * freq * ops.Iz[j]
            H += 2.0 * math.pi * 1e3 * (wf.controls_khz[m, 0] * ops.Ix_tot + wf.controls_khz[m, 1] * ops.Iy_tot)
            H_slices[bi, m] = H

    H_t = torch.tensor(H_slices, dtype=torch.complex128, device=dev)
    U_nuc = torch.linalg.matrix_exp((-1.0j * dt) * H_t)
    noise_t = torch.tensor(noise_seg_16, dtype=torch.float64, device=dev) if noise_seg_16 is not None else None

    psi = psi_16
    for m in range(M):
        p = psi.view(16, 2, 16)
        p0 = p[:, 0, :] @ U_nuc[0, m].T
        p1 = p[:, 1, :] @ U_nuc[1, m].T
        if noise_t is not None:
            ep = torch.exp((-1.0j * math.pi * dt) * noise_t[:, m]).unsqueeze(1)
            p0 = p0 * ep
            p1 = p1 * ep.conj()
        psi = torch.stack([p0, p1], dim=1).reshape(16, 32)
        if m in pulse_after:
            # Draw 1 realization and broadcast across all 16 basis columns!
            U_e1 = g126._noisy_electron_pi_batch(pulse_after[m], 1, eps_stoch, 0.0, rng, dev).expand(16, 2, 2)
            psi = g126._apply_electron_2x2_to_psi32(U_e1, psi)

    vz_d0 = torch.tensor(g126._vz_diag_16(wf.virtual_z_nuc_rad, ops), dtype=torch.complex128, device=dev)
    p = psi.view(16, 2, 16)
    p0 = p[:, 0, :] * vz_d0.view(1, 16)
    p1 = p[:, 1, :]
    if wf.apply_virtual_rze_neg_pi2:
        p0 = 1.0j * p0
    psi = torch.stack([p0, p1], dim=1).reshape(16, 32)
    if wf.n_dd > 0:
        psi = psi * complex(g126.dd_net_electron_sign(wf.n_dd, wf.dd_sequence).conjugate())
    return psi
