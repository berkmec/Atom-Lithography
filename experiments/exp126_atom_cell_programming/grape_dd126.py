"""Exp126 GPU-accelerated full-32D minimax-robust GRAPE + interleaved XY8/CPMG synthesizer & noisy propagator.

Clean public API designed both for Exp126 (Risk R3 Hamiltonian closure & 16-cell programmability)
and direct reuse/mirroring by src/machine_control/pulse_engine.py.

Key physics implemented:
  1. Exact 2^5 = 32-dimensional Hilbert space (1 central 31P donor electron + 4 active 29Si nuclei)
     including all hyperfine A_k S_z I_z^k and secular nuclear dipolar J_ij couplings.
  2. Exact interleaved XY8 / CPMG electron pi-pulses synchronized with carrier-toggled nuclear RF GRAPE
     waveforms (eliminating the hyperfine-refocusing / DDRF spectator crosstalk discovered when f_mod > min_gap
     by jointly optimizing full-32D minimax corner fidelity + all-bath spectator overlap with realistic 15 kHz
     NMR coil headroom, well within demonstrated 30-50 kHz Si:P NMR coils).
  3. Exact eigen-frame virtual-Z tracking for n_dd = 0 single-qubit nuclear gates (Rx(pi/2), Ry(pi/2), X)
     executed while the donor electron is parked in its |0_e> eigenstate.
  4. Exact time-domain stochastic 1/omega^alpha bath noise + stochastic/systematic electron pi-pulse errors.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

import hamiltonian126 as h126

DEFAULT_OFFSETS_HZ = (-400.0, 0.0, 400.0)
DEFAULT_SCALES = (0.98, 1.0, 1.02)
DEFAULT_BOUND_KHZ = 15.0  # Realistic Si:P NMR Rabi headroom (~1.8 mT; Pla et al. Nature 2013 ~30 kHz)


def get_device(prefer_cuda: bool = True) -> torch.device:
    if prefer_cuda and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


# ---------------------------------------------------------------------------
# Interleaved DD timing & phase schedules (exact symmetric CPMG / XY8)
# ---------------------------------------------------------------------------
def dd_schedule(n_slices: int, n_dd: int, sequence: str = "XY8") -> Tuple[Dict[int, str], np.ndarray]:
    """Return (pulse_after_map: slice_idx -> 'X'|'Y', parities: float64[n_slices] in {+1,-1}).

    Places n_dd electron pi-pulses symmetrically at (p + 0.5) * T / n_dd so that
    sum(parities) == 0 and final parity == +1, guaranteeing exact hyperfine refocusing.
    """
    if n_dd == 0:
        return {}, np.ones(n_slices, dtype=np.float64)
    if n_dd % 2 != 0:
        raise ValueError(f"n_dd must be even for net refocusing, got {n_dd}")
    if n_slices % n_dd != 0 or (n_slices // n_dd) % 2 != 0:
        raise ValueError(f"n_slices ({n_slices}) must be an even multiple of n_dd ({n_dd})")

    spacing = n_slices // n_dd
    half = spacing // 2
    seq = sequence.upper()
    if seq == "CPMG":
        axes = ["X"] * n_dd
    elif seq == "XY8":
        if n_dd == 2:
            # (-i X)(-i X) = -I (global phase only); avoid XY which yields -i Z
            axes = ["X", "X"]
        elif n_dd == 4:
            axes = ["X", "Y", "X", "Y"]
        else:
            pat = ["X", "Y", "X", "Y", "Y", "X", "Y", "X"]
            axes = [pat[i % 8] for i in range(n_dd)]
    else:
        raise ValueError(f"Unknown DD sequence: {sequence}")

    pulse_after: Dict[int, str] = {}
    for p_idx in range(n_dd):
        m_after = half - 1 + p_idx * spacing
        pulse_after[m_after] = axes[p_idx]

    parities = np.empty(n_slices, dtype=np.float64)
    cur = 1.0
    for m in range(n_slices):
        parities[m] = cur
        if m in pulse_after:
            cur = -cur
    assert abs(float(np.sum(parities))) < 1e-12 and cur == 1.0
    return pulse_after, parities


def dd_net_electron_sign(n_dd: int, sequence: str = "XY8") -> complex:
    """Exact net scalar factor c in {+1, -1} such that prod(-i P_k) = c * I_2."""
    if n_dd == 0:
        return 1.0 + 0.0j
    pulse_after, _ = dd_schedule(max(2 * n_dd, 64), n_dd, sequence)
    U = np.eye(2, dtype=np.complex128)
    for m in sorted(pulse_after):
        P = h126.PX if pulse_after[m] == "X" else h126.PY
        U = (-1.0j * P) @ U
    assert np.max(np.abs(U - U[0, 0] * np.eye(2))) < 1e-12
    return complex(U[0, 0])


# ---------------------------------------------------------------------------
# Public dataclasses (clean API for software-hw pulse_engine.py)
# ---------------------------------------------------------------------------
@dataclass
class PulseWaveform:
    gate_name: str               # "cX", "Rx_pi2", "Ry_pi2", "X"
    target_qubit: int            # 0..3
    duration_us: float
    n_slices: int
    n_dd: int
    dd_sequence: str             # "XY8", "CPMG", or "NONE"
    carrier_offset_hz: float     # +A_k / 2 (toggled by parity p_m when n_dd > 0)
    controls_khz: np.ndarray     # (n_slices, 2) float64 [u_x, u_y] in kHz
    bound_khz: float = DEFAULT_BOUND_KHZ
    apply_virtual_rze_neg_pi2: bool = False  # True for cX so diag(-i X_k, I) -> diag(X_k, I)
    virtual_z_nuc_rad: np.ndarray = field(default_factory=lambda: np.zeros(4, dtype=np.float64))
    # Verified metrics (full 32D exact complex128)
    nominal_fidelity_32d: float = 0.0
    worst_corner_fidelity_32d: float = 0.0
    corner_fidelities: List[float] = field(default_factory=list)
    max_unitarity_err_fro: float = 0.0
    min_spectator_retention_all: float = 1.0
    min_spectator_retention_nom: float = 1.0
    spectator_overlap_all_nom: float = 1.0
    max_amp_khz: float = 0.0
    rms_slew_khz_per_slice: float = 0.0
    synth_elapsed_s: float = 0.0

    def to_summary_dict(self) -> Dict[str, object]:
        return {
            "gate_name": self.gate_name,
            "target_qubit": int(self.target_qubit),
            "duration_us": float(self.duration_us),
            "n_slices": int(self.n_slices),
            "n_dd": int(self.n_dd),
            "dd_sequence": self.dd_sequence,
            "carrier_offset_kHz": float(self.carrier_offset_hz / 1e3),
            "bound_kHz": float(self.bound_khz),
            "nominal_fidelity_32d": float(self.nominal_fidelity_32d),
            "worst_corner_fidelity_32d": float(self.worst_corner_fidelity_32d),
            "max_unitarity_err_fro": float(self.max_unitarity_err_fro),
            "min_spectator_retention_all": float(self.min_spectator_retention_all),
            "min_spectator_retention_nom": float(self.min_spectator_retention_nom),
            "spectator_overlap_all_nom": float(self.spectator_overlap_all_nom),
            "max_amp_kHz": float(self.max_amp_khz),
            "rms_slew_kHz_per_slice": float(self.rms_slew_khz_per_slice),
            "synth_elapsed_s": float(self.synth_elapsed_s),
        }


@dataclass
class CellPulseLibrary:
    cell: h126.CellSpec
    rx_pi2: Dict[int, PulseWaveform]
    ry_pi2: Dict[int, PulseWaveform]
    x_gate: Dict[int, PulseWaveform]
    cx_e_to_n: Dict[int, PulseWaveform]          # Default interleaved XY8 cX_{e->k}
    cx_by_ndd: Dict[Tuple[int, int, str], PulseWaveform] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Target unitary & eigen-frame virtual-Z helpers
# ---------------------------------------------------------------------------
def _target_blocks(gate_name: str, target_qubit: int, ops: h126.SpinOperators) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Return (U_tgt_branch0 [16x16], U_tgt_branch1 [16x16 or None if electron in |0_e>])."""
    I16 = np.eye(16, dtype=np.complex128)
    s2 = 1.0 / math.sqrt(2.0)
    Xk = 2.0 * ops.Ix[target_qubit]
    Yk = 2.0 * ops.Iy[target_qubit]
    if gate_name == "cX":
        return (-1.0j * Xk), I16
    elif gate_name == "X":
        return (-1.0j * Xk), None
    elif gate_name == "Rx_pi2":
        return (s2 * I16 - 1.0j * s2 * Xk), None
    elif gate_name == "Ry_pi2":
        return (s2 * I16 - 1.0j * s2 * Yk), None
    else:
        raise ValueError(f"Unsupported gate_name: {gate_name}")


def _target_2x2(gate_name: str) -> np.ndarray:
    s2 = 1.0 / math.sqrt(2.0)
    if gate_name in ("cX", "X"):
        return -1.0j * h126.PX
    elif gate_name == "Rx_pi2":
        return s2 * h126.I2 - 1.0j * s2 * h126.PX
    elif gate_name == "Ry_pi2":
        return s2 * h126.I2 - 1.0j * s2 * h126.PY
    raise ValueError(gate_name)


def _eigenframe_vz_phases(cell: h126.CellSpec, target_qubit: int, duration_us: float, n_dd: int) -> np.ndarray:
    """Deterministic virtual-Z frame compensation (rad) for idle nuclei when n_dd == 0.

    When n_dd > 0 (symmetric XY8/CPMG), free hyperfine evolution integrates to exactly zero so VZ = 0.
    When n_dd == 0 (single-qubit gates with electron in |0_e>, or unrefocused cX), idle nucleus j != target
    precesses by -2*pi*(A_j - A_target)/2 * T around I_z^j; the qubit eigen-frame removes this known phase
    exactly via a zero-time virtual-Z update: exp(+i * phi_j * I_z^j).
    """
    if n_dd > 0:
        return np.zeros(4, dtype=np.float64)
    T = float(duration_us) * 1e-6
    A_t = float(cell.A_hz[target_qubit])
    phases = np.zeros(4, dtype=np.float64)
    for j in range(4):
        if j != target_qubit:
            phases[j] = 2.0 * math.pi * (0.5 * (float(cell.A_hz[j]) - A_t)) * T
    return phases


def _vz_diag_16(phases_rad: np.ndarray, ops: h126.SpinOperators) -> np.ndarray:
    """Diagonal 16-element array for exp(+i sum_j phases_rad[j] * Iz_j)."""
    angle = np.zeros(16, dtype=np.float64)
    for j in range(4):
        if phases_rad[j] != 0.0:
            angle += float(phases_rad[j]) * np.diag(ops.Iz[j]).real
    return np.exp(+1.0j * angle)


def _select_critical_spectators(A_target_hz: float, A_spec_hz: np.ndarray, n_dd: int,
                                duration_us: float, k_max: int = 80) -> np.ndarray:
    """Select spectators closest to target OR to DDRF harmonics (2n+1)*f_mod so none slip through."""
    if len(A_spec_hz) <= k_max:
        return A_spec_hz
    d_min = np.minimum(np.abs(A_spec_hz - A_target_hz) * 0.5, np.abs(A_spec_hz + A_target_hz) * 0.5)
    score = d_min.copy()
    if n_dd > 0:
        f_mod = float(n_dd) / (2.0 * float(duration_us) * 1e-6)
        # Prioritize spectators inside the toggling bandwidth |det| <= 3*f_mod + 30 kHz and near odd harmonics
        for mult in (1, 3, 5):
            h_dist = np.minimum(
                np.abs(np.abs(A_spec_hz - A_target_hz) * 0.5 - mult * f_mod),
                np.abs(np.abs(A_spec_hz + A_target_hz) * 0.5 - mult * f_mod),
            )
            score = np.minimum(score, h_dist * (1.0 + 0.3 * mult))
    idx = np.argsort(score)[:k_max]
    return A_spec_hz[idx]


# ---------------------------------------------------------------------------
# Exact full-32D propagation & verification (complex128)
# ---------------------------------------------------------------------------
def evaluate_gate_32d(
    cell: h126.CellSpec,
    controls_khz: np.ndarray,
    gate_name: str,
    target_qubit: int,
    duration_us: float,
    n_dd: int,
    dd_sequence: str = "XY8",
    offsets_hz: Sequence[float] = DEFAULT_OFFSETS_HZ,
    scales: Sequence[float] = DEFAULT_SCALES,
    device: Optional[torch.device] = None,
) -> Dict[str, object]:
    """Exact full-32D (16x16 x 2 blocks) verification across all (offset, scale) corners + ALL bath spectators."""
    dev = device or get_device()
    ops = h126.get_ops4()
    ctrl = np.asarray(controls_khz, dtype=np.float64)
    M = ctrl.shape[0]
    T = float(duration_us) * 1e-6
    dt = T / M
    _, parities = dd_schedule(M, n_dd, dd_sequence)
    net_sign = dd_net_electron_sign(n_dd, dd_sequence)

    H_dip = h126.nuclear_dipolar_hamiltonian(cell.J_hz, ops)
    U_tgt0_np, U_tgt1_np = _target_blocks(gate_name, target_qubit, ops)
    two_branch = U_tgt1_np is not None
    branches = (+0.5, -0.5) if two_branch else (+0.5,)
    n_br = len(branches)

    vz_phases_0 = _eigenframe_vz_phases(cell, target_qubit, duration_us, n_dd)
    vz_diag_0 = _vz_diag_16(vz_phases_0, ops)
    # For n_dd == 0 & two_branch (unprotected cX baseline), branch 1 has opposite hyperfine free precession
    if two_branch and n_dd == 0:
        vz_phases_1 = np.array(
            [2.0 * math.pi * (-0.5 * float(cell.A_hz[j]) - 0.5 * float(cell.A_hz[target_qubit])) * T for j in range(4)],
            dtype=np.float64,
        )
        vz_diag_1 = _vz_diag_16(vz_phases_1, ops)
    else:
        vz_diag_1 = np.ones(16, dtype=np.complex128)

    corners = [(float(o), float(s)) for o in offsets_hz for s in scales]
    B = len(corners)
    iz_diag = np.diag(ops.Iz_tot).real

    H_base = np.zeros((B, n_br, M, 16, 16), dtype=np.complex128)
    U_back = np.zeros((B, n_br, 16, 16), dtype=np.complex128)
    sc_arr = np.zeros((B, 1, 1, 1, 1), dtype=np.float64)
    A_t = float(cell.A_hz[target_qubit])
    for ci, (off, sc) in enumerate(corners):
        sc_arr[ci, 0, 0, 0, 0] = sc
        back_off = np.exp(+1.0j * 2.0 * math.pi * off * T * iz_diag)
        U_back[ci, 0] = np.diag(back_off * vz_diag_0)
        if two_branch:
            U_back[ci, 1] = np.diag(back_off * vz_diag_1)
        for bi, sz0 in enumerate(branches):
            for m, pm in enumerate(parities):
                H = H_dip.copy()
                for j in range(4):
                    freq = float(cell.A_hz[j]) * sz0 * pm - pm * A_t * 0.5 + off
                    H += 2.0 * math.pi * freq * ops.Iz[j]
                H_base[ci, bi, m] = H

    with torch.no_grad():
        H_t = torch.tensor(H_base, dtype=torch.complex128, device=dev)
        Ub_t = torch.tensor(U_back, dtype=torch.complex128, device=dev)
        sc_t = torch.tensor(sc_arr, dtype=torch.float64, device=dev)
        u_t = torch.tensor(ctrl, dtype=torch.float64, device=dev)
        Ix_t = torch.tensor(2.0 * math.pi * 1e3 * ops.Ix_tot, dtype=torch.complex128, device=dev)
        Iy_t = torch.tensor(2.0 * math.pi * 1e3 * ops.Iy_tot, dtype=torch.complex128, device=dev)
        H_tot = H_t + sc_t * (u_t[:, 0].view(1, 1, M, 1, 1) * Ix_t + u_t[:, 1].view(1, 1, M, 1, 1) * Iy_t)
        Us = torch.linalg.matrix_exp((-1.0j * dt) * H_tot)
        U_rot = Us[:, :, 0]
        for m in range(1, M):
            U_rot = Us[:, :, m] @ U_rot
        U_lab = net_sign * (Ub_t @ U_rot)

        I16_t = torch.eye(16, dtype=torch.complex128, device=dev)
        diff_u = U_lab.conj().transpose(-1, -2) @ U_lab - I16_t
        max_u_err = float(torch.linalg.norm(diff_u, ord="fro", dim=(-2, -1)).max().item())

        Ut0 = torch.tensor(U_tgt0_np, dtype=torch.complex128, device=dev)
        ov0 = (Ut0.conj() * U_lab[:, 0]).sum(dim=(-2, -1))
        if two_branch:
            Ut1 = torch.tensor(U_tgt1_np, dtype=torch.complex128, device=dev)
            ov1 = (Ut1.conj() * U_lab[:, 1]).sum(dim=(-2, -1))
            fids = (((ov0 + ov1).abs() / 32.0) ** 2).cpu().numpy()
        else:
            fids = ((ov0.abs() / 16.0) ** 2).cpu().numpy()

        nom_idx = corners.index((0.0, 1.0)) if (0.0, 1.0) in corners else 0
        U0_nom = U_lab[nom_idx, 0].cpu().numpy()
        U1_nom = U_lab[nom_idx, 1].cpu().numpy() if two_branch else None

        # Exact SU(2) evaluation across ALL bath spectators!
        A_spec = cell.A_spectators_hz
        min_spec_ret_all = 1.0
        min_spec_ret_nom = 1.0
        spec_ovl_prod_nom = 1.0
        if len(A_spec) > 0:
            Ns = len(A_spec)
            sp_nz = np.empty((B, 2 * Ns, M), dtype=np.float64)
            sp_sc = np.empty((B, 2 * Ns, 1), dtype=np.float64)
            for ci, (off, sc) in enumerate(corners):
                sp_sc[ci, :, 0] = sc
                sp_nz[ci, 0::2, :] = 2.0 * math.pi * (
                    +0.5 * A_spec[:, None] * parities[None, :] - 0.5 * A_t * parities[None, :] + off
                )
                sp_nz[ci, 1::2, :] = 2.0 * math.pi * (
                    -0.5 * A_spec[:, None] * parities[None, :] - 0.5 * A_t * parities[None, :] + off
                )
            nz_t = torch.tensor(sp_nz, dtype=torch.float64, device=dev)
            sc_sp_t = torch.tensor(sp_sc, dtype=torch.float64, device=dev)
            nx = (2.0 * math.pi * 1e3) * sc_sp_t * u_t[:, 0].view(1, 1, M)
            ny = (2.0 * math.pi * 1e3) * sc_sp_t * u_t[:, 1].view(1, 1, M)
            norm = torch.sqrt(nx * nx + ny * ny + nz_t * nz_t + 1e-30)
            half = 0.5 * norm * dt
            c = torch.cos(half)
            s = torch.sin(half) / norm
            a = c - 1.0j * s * nz_t
            b = -s * ny - 1.0j * s * nx
            p0 = torch.ones((B, 2 * Ns), dtype=torch.complex128, device=dev)
            p1 = torch.zeros((B, 2 * Ns), dtype=torch.complex128, device=dev)
            for m in range(M):
                am, bm = a[:, :, m], b[:, :, m]
                p0, p1 = am * p0 + bm * p1, -bm.conj() * p0 + am.conj() * p1
            rets = p0.abs() ** 2
            rets_active = rets if two_branch else rets[:, 0::2]
            min_spec_ret_all = float(rets_active.min().item())
            min_spec_ret_nom = float(rets_active[nom_idx].min().item())
            p0p, p1p = p0[nom_idx, 0::2], p1[nom_idx, 0::2]
            p0m, p1m = p0[nom_idx, 1::2], p1[nom_idx, 1::2]
            # For n_dd == 0, undo free hyperfine phase exp(+-i pi A_s T) on spectator overlap?
            # No! In physical GHZ, spectator overlap |<psi+|psi->| IS invariant to global phase on each spin
            # ONLY if spectator started in |0> (eigenstate of Iz): yes! Because |0> picks up a pure phase
            # e^{-i phi/2} on branch + and e^{+i phi/2} on branch -, wait: |<0|U+^dag U-|0>| = |p0+* p0- + p1+* p1-|
            # IS invariant to diagonal Z-rotations ONLY for |p0+* p0-| = |p0+||p0-| when p1=0!
            # Wait: check! In Exp48 shaped_ghz48.py line 64:
            # overlap *= abs(sp[0].conj() * sm[0] + sp[1].conj() * sm[1]) where sp, sm are propagated from |0>
            # in the spin's own rotating frame (f_p and f_m), so free Z phase is already removed!
            # In our carrier frame, relative free Z phase on |0> is purely a global phase on |0>, which multiplies
            # BOTH sp[0] and sp[1] by opposite signs, EXCEPT at t=T when sum(parities)==0 free phase is 0 anyway!
            if n_dd == 0:
                # Transform spectator out of carrier frame into its own eigenframe (matches Exp48 exact definition)
                ph_p = torch.tensor(np.exp(+0.5j * 2.0 * math.pi * (0.5 * A_spec - 0.5 * A_t) * T),
                                    dtype=torch.complex128, device=dev)
                ph_m = torch.tensor(np.exp(+0.5j * 2.0 * math.pi * (-0.5 * A_spec - 0.5 * A_t) * T),
                                    dtype=torch.complex128, device=dev)
                p0p, p1p = ph_p * p0p, ph_p.conj() * p1p
                p0m, p1m = ph_m * p0m, ph_m.conj() * p1m
            ovls = (p0p.conj() * p0m + p1p.conj() * p1m).abs()
            spec_ovl_prod_nom = float(ovls.prod().item())

    return {
        "nominal_fidelity_32d": float(fids[nom_idx]),
        "worst_corner_fidelity_32d": float(np.min(fids)),
        "corner_fidelities": [float(x) for x in fids],
        "max_unitarity_err_fro": max_u_err,
        "min_spectator_retention_all": min_spec_ret_all,
        "min_spectator_retention_nom": min_spec_ret_nom,
        "spectator_overlap_all_nom": spec_ovl_prod_nom,
        "virtual_z_nuc_rad": vz_phases_0,
        "U0_nom": U0_nom,
        "U1_nom": U1_nom,
    }


def evaluate_sequence_spectator_overlap(
    cell: h126.CellSpec,
    waveforms: Sequence[PulseWaveform],
    device: Optional[torch.device] = None,
) -> float:
    """Exact sequential product overlap prod_{s in bath} |<psi_s^+(T)|psi_s^-(T)>| across a multi-gate sequence."""
    A_spec = cell.A_spectators_hz
    if len(A_spec) == 0:
        return 1.0
    dev = device or get_device()
    Ns = len(A_spec)
    with torch.no_grad():
        p0 = torch.ones(2 * Ns, dtype=torch.complex128, device=dev)
        p1 = torch.zeros(2 * Ns, dtype=torch.complex128, device=dev)
        for wf in waveforms:
            M = wf.n_slices
            T = wf.duration_us * 1e-6
            dt = T / M
            _, parities = dd_schedule(M, wf.n_dd, wf.dd_sequence if wf.n_dd > 0 else "XY8")
            A_t = float(cell.A_hz[wf.target_qubit])
            sp_nz = np.empty((2 * Ns, M), dtype=np.float64)
            sp_nz[0::2, :] = 2.0 * math.pi * (+0.5 * A_spec[:, None] * parities[None, :] - 0.5 * A_t * parities[None, :])
            sp_nz[1::2, :] = 2.0 * math.pi * (-0.5 * A_spec[:, None] * parities[None, :] - 0.5 * A_t * parities[None, :])
            nz_t = torch.tensor(sp_nz, dtype=torch.float64, device=dev)
            u_t = torch.tensor(wf.controls_khz, dtype=torch.float64, device=dev)
            nx = (2.0 * math.pi * 1e3) * u_t[:, 0].view(1, M)
            ny = (2.0 * math.pi * 1e3) * u_t[:, 1].view(1, M)
            norm = torch.sqrt(nx * nx + ny * ny + nz_t * nz_t + 1e-30)
            half = 0.5 * norm * dt
            c = torch.cos(half)
            s = torch.sin(half) / norm
            a = c - 1.0j * s * nz_t
            b = -s * ny - 1.0j * s * nx
            for m in range(M):
                am, bm = a[:, m], b[:, m]
                p0, p1 = am * p0 + bm * p1, -bm.conj() * p0 + am.conj() * p1
            if wf.n_dd == 0:
                ph_p = torch.tensor(np.exp(+0.5j * 2.0 * math.pi * (0.5 * A_spec - 0.5 * A_t) * T),
                                    dtype=torch.complex128, device=dev)
                ph_m = torch.tensor(np.exp(+0.5j * 2.0 * math.pi * (-0.5 * A_spec - 0.5 * A_t) * T),
                                    dtype=torch.complex128, device=dev)
                p0[0::2] *= ph_p; p1[0::2] *= ph_p.conj()
                p0[1::2] *= ph_m; p1[1::2] *= ph_m.conj()
        ovls = (p0[0::2].conj() * p0[1::2] + p1[0::2].conj() * p1[1::2]).abs()
        return float(ovls.prod().item())


# ---------------------------------------------------------------------------
# Two-stage GPU minimax-robust GRAPE synthesizer
# ---------------------------------------------------------------------------
def synthesize_gate_grape(
    cell: h126.CellSpec,
    gate_name: str,
    target_qubit: int,
    duration_us: float = 500.0,
    n_slices: int = 64,
    n_dd: int = 16,
    dd_sequence: str = "XY8",
    bound_khz: float = DEFAULT_BOUND_KHZ,
    offsets_hz: Sequence[float] = DEFAULT_OFFSETS_HZ,
    scales: Sequence[float] = DEFAULT_SCALES,
    stage1_iters: int = 160,
    stage2_iters: int = 50,
    smooth_weight: float = 2e-5,
    spec_weight: float = 2.0,
    device: Optional[torch.device] = None,
) -> PulseWaveform:
    """Synthesize a minimax-robust, bandwidth-smoothed, full-32D verified GRAPE pulse.

    Stage 1: Fast batched 2x2 SU(2) warm-start on active nuclei + ALL critical bath spectators across all 9 corners.
    Stage 2: Exact full-32D (16x16 x n_br complex128) L-BFGS polish including all dipolar J_ij + critical spectators.
    """
    t0 = time.time()
    dev = device or get_device()
    ops = h126.get_ops4()
    T = float(duration_us) * 1e-6
    M = int(n_slices)
    dt = T / M
    if gate_name in ("Rx_pi2", "Ry_pi2", "X"):
        n_dd = 0
        dd_sequence = "NONE"

    _, parities = dd_schedule(M, n_dd, dd_sequence)
    net_sign = dd_net_electron_sign(n_dd, dd_sequence)
    corners = [(float(o), float(s)) for o in offsets_hz for s in scales]
    B = len(corners)
    A_t = float(cell.A_hz[target_qubit])
    # Select up to 80 critical spectators (closest + DDRF harmonics) for direct GPU penalization
    A_near = _select_critical_spectators(A_t, cell.A_spectators_hz, n_dd, duration_us, k_max=80)
    vz_phases_0 = _eigenframe_vz_phases(cell, target_qubit, duration_us, n_dd)

    # Initial Gaussian seed matching target rotation angle and axis
    x_grid = (np.arange(M) + 0.5) / M
    raw = np.exp(-0.5 * ((x_grid - 0.5) / (1.0 / 6.0)) ** 2)
    angle_turns = 0.5 if gate_name in ("cX", "X") else 0.25
    amp0_khz = raw * (angle_turns / (dt * float(np.sum(raw)))) / 1e3
    u_init = np.zeros((M, 2), dtype=np.float64)
    if gate_name == "Ry_pi2":
        u_init[:, 1] = amp0_khz
    else:
        u_init[:, 0] = amp0_khz
    u_clip = np.clip(u_init / bound_khz, -0.95, 0.95)
    u_param = torch.tensor(bound_khz * np.arctanh(u_clip), dtype=torch.float64, device=dev, requires_grad=True)

    two_branch = (gate_name == "cX")
    line_A: List[float] = []
    line_sz0: List[float] = []
    line_vz: List[float] = []
    for j in range(4):
        line_A.append(float(cell.A_hz[j]))
        line_sz0.append(+0.5)
        line_vz.append(float(vz_phases_0[j]))
    if two_branch:
        for j in range(4):
            line_A.append(float(cell.A_hz[j]))
            line_sz0.append(-0.5)
            vz1 = 2.0 * math.pi * (-0.5 * float(cell.A_hz[j]) - 0.5 * A_t) * T if n_dd == 0 else 0.0
            line_vz.append(float(vz1))
    n_active_lines = len(line_A)
    for a_s in A_near:
        line_A.append(float(a_s))
        line_sz0.append(+0.5)
        line_vz.append(2.0 * math.pi * (0.5 * float(a_s) - 0.5 * A_t) * T if n_dd == 0 else 0.0)
        if two_branch:
            line_A.append(float(a_s))
            line_sz0.append(-0.5)
            line_vz.append(2.0 * math.pi * (-0.5 * float(a_s) - 0.5 * A_t) * T if n_dd == 0 else 0.0)

    L_tot = len(line_A)
    line_A_arr = np.asarray(line_A, dtype=np.float64)
    line_sz_arr = np.asarray(line_sz0, dtype=np.float64)
    line_vz_arr = np.asarray(line_vz, dtype=np.float64)

    nz_s1 = np.empty((B, L_tot, M), dtype=np.float64)
    sc_s1 = np.empty((B, L_tot, 1), dtype=np.float64)
    back_phase_s1 = np.empty((B, L_tot), dtype=np.complex128)
    for ci, (off, sc) in enumerate(corners):
        sc_s1[ci, :, 0] = sc
        back_phase_s1[ci, :] = np.exp(+0.5j * (2.0 * math.pi * off * T + line_vz_arr))
        nz_s1[ci] = 2.0 * math.pi * (
            (line_A_arr * line_sz_arr)[:, None] * parities[None, :] - 0.5 * A_t * parities[None, :] + off
        )
    nz_s1_t = torch.tensor(nz_s1, dtype=torch.float64, device=dev)
    sc_s1_t = torch.tensor(sc_s1, dtype=torch.float64, device=dev)
    bp_s1_t = torch.tensor(back_phase_s1, dtype=torch.complex128, device=dev)
    Ut2_t = torch.tensor(_target_2x2(gate_name), dtype=torch.complex128, device=dev)
    tgt_idx_s1 = target_qubit
    nom_idx = corners.index((0.0, 1.0)) if (0.0, 1.0) in corners else 0

    def stage1_loss() -> torch.Tensor:
        u = bound_khz * torch.tanh(u_param / bound_khz)
        nx = (2.0 * math.pi * 1e3) * sc_s1_t * u[:, 0].view(1, 1, M)
        ny = (2.0 * math.pi * 1e3) * sc_s1_t * u[:, 1].view(1, 1, M)
        nz = nz_s1_t
        norm = torch.sqrt(nx * nx + ny * ny + nz * nz + 1e-30)
        half = 0.5 * norm * dt
        c = torch.cos(half)
        s = torch.sin(half) / norm
        a = c - 1.0j * s * nz
        b = -s * ny - 1.0j * s * nx
        u00 = torch.ones((B, L_tot), dtype=torch.complex128, device=dev)
        u01 = torch.zeros((B, L_tot), dtype=torch.complex128, device=dev)
        for m in range(M):
            am, bm = a[:, :, m], b[:, :, m]
            u00, u01 = am * u00 - bm * u01.conj(), am * u01 + bm * u00.conj()
        u00_lab = bp_s1_t * u00
        u01_lab = bp_s1_t * u01
        u10_lab = -u01_lab.conj()
        u11_lab = u00_lab.conj()

        ov_tgt = (
            Ut2_t[0, 0].conj() * u00_lab[:, tgt_idx_s1]
            + Ut2_t[0, 1].conj() * u01_lab[:, tgt_idx_s1]
            + Ut2_t[1, 0].conj() * u10_lab[:, tgt_idx_s1]
            + Ut2_t[1, 1].conj() * u11_lab[:, tgt_idx_s1]
        )
        prod0 = torch.ones(B, dtype=torch.complex128, device=dev)
        for j in range(4):
            tr_j = ov_tgt if j == tgt_idx_s1 else (u00_lab[:, j] + u11_lab[:, j])
            prod0 = prod0 * tr_j
        if two_branch:
            prod1 = torch.ones(B, dtype=torch.complex128, device=dev)
            for j in range(4, 8):
                prod1 = prod1 * (u00_lab[:, j] + u11_lab[:, j])
            fids = ((prod0 + prod1).abs() / 32.0) ** 2
        else:
            fids = (prod0.abs() / 16.0) ** 2

        tau = 0.002
        loss_reg = tau * torch.logsumexp((1.0 - fids) / tau, dim=0) + 0.05 * (1.0 - fids[nom_idx])
        loss_spec = torch.tensor(0.0, dtype=torch.float64, device=dev)
        if L_tot > n_active_lines:
            # Penalize SUM of spectator infidelities (directly bounds product overlap!) + worst spectator
            sp_infid = 1.0 - (u00_lab[:, n_active_lines:].abs() ** 2)
            loss_spec = spec_weight * (sp_infid.sum(dim=1).mean() * 0.25 + 0.002 * torch.logsumexp(sp_infid / 0.002, dim=1).mean())
            if two_branch:
                a0 = u00_lab[:, n_active_lines::2]
                b0 = u10_lab[:, n_active_lines::2]
                a1 = u00_lab[:, n_active_lines + 1 :: 2]
                b1 = u10_lab[:, n_active_lines + 1 :: 2]
                sp_ovl = (a0.conj() * a1 + b0.conj() * b1).abs()
                loss_spec = loss_spec + spec_weight * (1.0 - sp_ovl).sum(dim=1).mean() * 0.5
        smooth = smooth_weight * ((u[1:] - u[:-1]) ** 2).mean()
        edge = 0.25 * smooth_weight * ((u[0] ** 2).sum() + (u[-1] ** 2).sum())
        return loss_reg + loss_spec + smooth + edge

    if stage1_iters > 0:
        opt1 = torch.optim.LBFGS([u_param], lr=1.0, max_iter=stage1_iters, line_search_fn="strong_wolfe")

        def closure1():
            opt1.zero_grad()
            l = stage1_loss()
            l.backward()
            return l

        opt1.step(closure1)

    # ---- Stage 2: Exact full-32D (16x16 x n_br complex128) polish including dipolar J_ij + critical spectators ----
    if stage2_iters > 0:
        H_dip = h126.nuclear_dipolar_hamiltonian(cell.J_hz, ops)
        U_tgt0_np, U_tgt1_np = _target_blocks(gate_name, target_qubit, ops)
        branches = (+0.5, -0.5) if two_branch else (+0.5,)
        n_br = len(branches)
        iz_diag = np.diag(ops.Iz_tot).real
        vz_diag_0 = _vz_diag_16(vz_phases_0, ops)
        if two_branch and n_dd == 0:
            vz_phases_1 = np.array(
                [2.0 * math.pi * (-0.5 * float(cell.A_hz[j]) - 0.5 * A_t) * T for j in range(4)],
                dtype=np.float64,
            )
            vz_diag_1 = _vz_diag_16(vz_phases_1, ops)
        else:
            vz_diag_1 = np.ones(16, dtype=np.complex128)

        H_base = np.zeros((B, n_br, M, 16, 16), dtype=np.complex128)
        U_back = np.zeros((B, n_br, 16, 16), dtype=np.complex128)
        sc_arr = np.zeros((B, 1, 1, 1, 1), dtype=np.float64)
        for ci, (off, sc) in enumerate(corners):
            sc_arr[ci, 0, 0, 0, 0] = sc
            back_off = np.exp(+1.0j * 2.0 * math.pi * off * T * iz_diag)
            U_back[ci, 0] = np.diag(back_off * vz_diag_0)
            if two_branch:
                U_back[ci, 1] = np.diag(back_off * vz_diag_1)
            for bi, sz0 in enumerate(branches):
                for m, pm in enumerate(parities):
                    H = H_dip.copy()
                    for j in range(4):
                        freq = float(cell.A_hz[j]) * sz0 * pm - pm * A_t * 0.5 + off
                        H += 2.0 * math.pi * freq * ops.Iz[j]
                    H_base[ci, bi, m] = H

        H_base_t = torch.tensor(H_base, dtype=torch.complex128, device=dev)
        Ub_t = torch.tensor(U_back, dtype=torch.complex128, device=dev)
        sc_t = torch.tensor(sc_arr, dtype=torch.float64, device=dev)
        Ix_t = torch.tensor(2.0 * math.pi * 1e3 * ops.Ix_tot, dtype=torch.complex128, device=dev)
        Iy_t = torch.tensor(2.0 * math.pi * 1e3 * ops.Iy_tot, dtype=torch.complex128, device=dev)
        Ut0_t = torch.tensor(U_tgt0_np, dtype=torch.complex128, device=dev)
        Ut1_t = torch.tensor(U_tgt1_np, dtype=torch.complex128, device=dev) if two_branch else None

        has_spec = L_tot > n_active_lines
        if has_spec:
            sp_nz_t = nz_s1_t[:, n_active_lines:, :]
            sp_sc_t = sc_s1_t[:, n_active_lines:, :]
            sp_bp_t = bp_s1_t[:, n_active_lines:]

        def stage2_loss() -> torch.Tensor:
            u = bound_khz * torch.tanh(u_param / bound_khz)
            H = H_base_t + sc_t * (u[:, 0].view(1, 1, M, 1, 1) * Ix_t + u[:, 1].view(1, 1, M, 1, 1) * Iy_t)
            Us = torch.linalg.matrix_exp((-1.0j * dt) * H)
            U_rot = Us[:, :, 0]
            for m in range(1, M):
                U_rot = Us[:, :, m] @ U_rot
            U_lab = net_sign * (Ub_t @ U_rot)
            ov0 = (Ut0_t.conj() * U_lab[:, 0]).sum(dim=(-2, -1))
            if two_branch:
                ov1 = (Ut1_t.conj() * U_lab[:, 1]).sum(dim=(-2, -1))
                fids = ((ov0 + ov1).abs() / 32.0) ** 2
            else:
                fids = (ov0.abs() / 16.0) ** 2

            tau = 0.002
            loss_reg = tau * torch.logsumexp((1.0 - fids) / tau, dim=0) + 0.05 * (1.0 - fids[nom_idx])
            loss_spec = torch.tensor(0.0, dtype=torch.float64, device=dev)
            if has_spec:
                nx = (2.0 * math.pi * 1e3) * sp_sc_t * u[:, 0].view(1, 1, M)
                ny = (2.0 * math.pi * 1e3) * sp_sc_t * u[:, 1].view(1, 1, M)
                norm = torch.sqrt(nx * nx + ny * ny + sp_nz_t * sp_nz_t + 1e-30)
                half = 0.5 * norm * dt
                c = torch.cos(half)
                s = torch.sin(half) / norm
                a = c - 1.0j * s * sp_nz_t
                b = -s * ny - 1.0j * s * nx
                p0 = torch.ones((B, L_tot - n_active_lines), dtype=torch.complex128, device=dev)
                p1 = torch.zeros((B, L_tot - n_active_lines), dtype=torch.complex128, device=dev)
                for m in range(M):
                    am, bm = a[:, :, m], b[:, :, m]
                    p0, p1 = am * p0 + bm * p1, -bm.conj() * p0 + am.conj() * p1
                p0 = sp_bp_t * p0
                p1 = sp_bp_t.conj() * p1
                sp_infid = 1.0 - (p0.abs() ** 2)
                loss_spec = spec_weight * (sp_infid.sum(dim=1).mean() * 0.25 + 0.002 * torch.logsumexp(sp_infid / 0.002, dim=1).mean())
                if two_branch:
                    ovl = (p0[:, 0::2].conj() * p0[:, 1::2] + p1[:, 0::2].conj() * p1[:, 1::2]).abs()
                    loss_spec = loss_spec + spec_weight * (1.0 - ovl).sum(dim=1).mean() * 0.5
            smooth = smooth_weight * ((u[1:] - u[:-1]) ** 2).mean()
            edge = 0.25 * smooth_weight * ((u[0] ** 2).sum() + (u[-1] ** 2).sum())
            return loss_reg + loss_spec + smooth + edge

        opt2 = torch.optim.LBFGS([u_param], lr=0.8, max_iter=stage2_iters, line_search_fn="strong_wolfe")

        def closure2():
            opt2.zero_grad()
            l = stage2_loss()
            l.backward()
            return l

        opt2.step(closure2)

    with torch.no_grad():
        ctrl_final = (bound_khz * torch.tanh(u_param / bound_khz)).cpu().numpy()

    ev = evaluate_gate_32d(
        cell, ctrl_final, gate_name, target_qubit, duration_us, n_dd, dd_sequence,
        offsets_hz=offsets_hz, scales=scales, device=dev,
    )
    slew = float(np.sqrt(np.mean(np.diff(ctrl_final, axis=0) ** 2)))
    return PulseWaveform(
        gate_name=gate_name,
        target_qubit=int(target_qubit),
        duration_us=float(duration_us),
        n_slices=M,
        n_dd=int(n_dd),
        dd_sequence=dd_sequence,
        carrier_offset_hz=0.5 * A_t,
        controls_khz=ctrl_final,
        bound_khz=float(bound_khz),
        apply_virtual_rze_neg_pi2=(gate_name == "cX"),
        virtual_z_nuc_rad=ev["virtual_z_nuc_rad"],
        nominal_fidelity_32d=ev["nominal_fidelity_32d"],
        worst_corner_fidelity_32d=ev["worst_corner_fidelity_32d"],
        corner_fidelities=ev["corner_fidelities"],
        max_unitarity_err_fro=ev["max_unitarity_err_fro"],
        min_spectator_retention_all=ev["min_spectator_retention_all"],
        min_spectator_retention_nom=ev["min_spectator_retention_nom"],
        spectator_overlap_all_nom=ev["spectator_overlap_all_nom"],
        max_amp_khz=float(np.max(np.abs(ctrl_final))),
        rms_slew_khz_per_slice=slew,
        synth_elapsed_s=float(time.time() - t0),
    )


def phase_rotate_waveform(wf: PulseWaveform, phi_rad: float, new_gate_name: str, cell: h126.CellSpec,
                          device: Optional[torch.device] = None) -> PulseWaveform:
    """Exact RF frame rotation (u_x, u_y) -> R(phi) (u_x, u_y) producing e^{-i phi I_z} U e^{+i phi I_z}."""
    c, s = math.cos(phi_rad), math.sin(phi_rad)
    ctrl = wf.controls_khz.copy()
    ux = c * ctrl[:, 0] - s * ctrl[:, 1]
    uy = s * ctrl[:, 0] + c * ctrl[:, 1]
    new_ctrl = np.stack([ux, uy], axis=1)
    ev = evaluate_gate_32d(
        cell, new_ctrl, new_gate_name, wf.target_qubit, wf.duration_us, wf.n_dd, wf.dd_sequence, device=device
    )
    return PulseWaveform(
        gate_name=new_gate_name,
        target_qubit=wf.target_qubit,
        duration_us=wf.duration_us,
        n_slices=wf.n_slices,
        n_dd=wf.n_dd,
        dd_sequence=wf.dd_sequence,
        carrier_offset_hz=wf.carrier_offset_hz,
        controls_khz=new_ctrl,
        bound_khz=wf.bound_khz,
        apply_virtual_rze_neg_pi2=wf.apply_virtual_rze_neg_pi2,
        virtual_z_nuc_rad=ev["virtual_z_nuc_rad"],
        nominal_fidelity_32d=ev["nominal_fidelity_32d"],
        worst_corner_fidelity_32d=ev["worst_corner_fidelity_32d"],
        corner_fidelities=ev["corner_fidelities"],
        max_unitarity_err_fro=ev["max_unitarity_err_fro"],
        min_spectator_retention_all=ev["min_spectator_retention_all"],
        min_spectator_retention_nom=ev["min_spectator_retention_nom"],
        spectator_overlap_all_nom=ev["spectator_overlap_all_nom"],
        max_amp_khz=float(np.max(np.abs(new_ctrl))),
        rms_slew_khz_per_slice=float(np.sqrt(np.mean(np.diff(new_ctrl, axis=0) ** 2))),
        synth_elapsed_s=0.0,
    )


def synthesize_cell_library(
    cell: h126.CellSpec,
    cx_n_dd: int = 16,
    cx_sequence: str = "XY8",
    duration_us: float = 500.0,
    n_slices: int = 64,
    bound_khz: float = DEFAULT_BOUND_KHZ,
    native_ry_and_x: bool = False,
    stage1_iters: int = 160,
    stage2_iters: int = 45,
    device: Optional[torch.device] = None,
) -> CellPulseLibrary:
    """Synthesize complete cell-specific GRAPE + interleaved XY8 gate library for a certified 4-qubit atom cell."""
    dev = device or get_device()
    rx_map: Dict[int, PulseWaveform] = {}
    ry_map: Dict[int, PulseWaveform] = {}
    x_map: Dict[int, PulseWaveform] = {}
    cx_map: Dict[int, PulseWaveform] = {}
    cx_extra: Dict[Tuple[int, int, str], PulseWaveform] = {}

    for k in range(4):
        rx_map[k] = synthesize_gate_grape(
            cell, "Rx_pi2", k, duration_us=duration_us, n_slices=n_slices, n_dd=0,
            bound_khz=bound_khz, stage1_iters=stage1_iters, stage2_iters=stage2_iters, device=dev,
        )
        if native_ry_and_x:
            ry_map[k] = synthesize_gate_grape(
                cell, "Ry_pi2", k, duration_us=duration_us, n_slices=n_slices, n_dd=0,
                bound_khz=bound_khz, stage1_iters=stage1_iters, stage2_iters=stage2_iters, device=dev,
            )
        else:
            ry_map[k] = phase_rotate_waveform(rx_map[k], +0.5 * math.pi, "Ry_pi2", cell, device=dev)
        x_map[k] = synthesize_gate_grape(
            cell, "X", k, duration_us=duration_us, n_slices=n_slices, n_dd=0,
            bound_khz=bound_khz, stage1_iters=stage1_iters, stage2_iters=stage2_iters, device=dev,
        )
        cx_map[k] = synthesize_gate_grape(
            cell, "cX", k, duration_us=duration_us, n_slices=n_slices, n_dd=cx_n_dd, dd_sequence=cx_sequence,
            bound_khz=bound_khz, stage1_iters=stage1_iters, stage2_iters=stage2_iters, device=dev,
        )
        cx_extra[(k, cx_n_dd, cx_sequence)] = cx_map[k]

    return CellPulseLibrary(cell=cell, rx_pi2=rx_map, ry_pi2=ry_map, x_gate=x_map,
                            cx_e_to_n=cx_map, cx_by_ndd=cx_extra)


# ---------------------------------------------------------------------------
# Exact 32D Noisy Trajectory Engine (1/omega^alpha bath + pi-pulse errors)
# ---------------------------------------------------------------------------
def _noisy_electron_pi_batch(
    axis: str,
    n_traj: int,
    eps_stoch: float,
    delta_theta_sys: float,
    rng: np.random.Generator,
    dev: torch.device,
) -> torch.Tensor:
    """Return (n_traj, 2, 2) complex128 noisy electron pi-pulse unitaries."""
    ang = 0.5 * (math.pi + float(delta_theta_sys))
    P = h126.PX if axis == "X" else h126.PY
    U_base = math.cos(ang) * h126.I2 - 1.0j * math.sin(ang) * P
    if eps_stoch <= 0.0:
        return torch.tensor(U_base, dtype=torch.complex128, device=dev).unsqueeze(0).expand(n_traj, 2, 2).clone()

    sigma = math.sqrt(float(eps_stoch)) * 0.5
    e = rng.normal(0.0, sigma, size=(n_traj, 3))
    enorm = np.linalg.norm(e, axis=1)
    c = np.cos(enorm)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.where(enorm > 1e-15, np.sin(enorm) / np.where(enorm > 1e-15, enorm, 1.0), 1.0)
    ex, ey, ez = e[:, 0], e[:, 1], e[:, 2]
    U_err = np.empty((n_traj, 2, 2), dtype=np.complex128)
    U_err[:, 0, 0] = c - 1.0j * s * ez
    U_err[:, 0, 1] = -s * ey - 1.0j * s * ex
    U_err[:, 1, 0] = s * ey - 1.0j * s * ex
    U_err[:, 1, 1] = c + 1.0j * s * ez
    U_tot = np.einsum("ij,njk->nik", U_base, U_err)
    return torch.tensor(U_tot, dtype=torch.complex128, device=dev)


def _apply_electron_2x2_to_psi32(U_e: torch.Tensor, psi: torch.Tensor) -> torch.Tensor:
    p = psi.view(-1, 2, 16)
    out = torch.einsum("nij,njk->nik", U_e, p)
    return out.reshape(-1, 32)


def propagate_waveform_noisy_32d(
    psi_batch: torch.Tensor,
    cell: h126.CellSpec,
    wf: PulseWaveform,
    noise_hz_seg: Optional[np.ndarray],
    eps_stoch: float = 0.0,
    delta_theta_sys: float = 0.0,
    offset_hz: float = 0.0,
    amp_scale: float = 1.0,
    rng: Optional[np.random.Generator] = None,
    device: Optional[torch.device] = None,
) -> torch.Tensor:
    """Propagate (n_traj, 32) statevectors through a physical GRAPE + interleaved DD waveform in full 32D."""
    dev = device or psi_batch.device
    ops = h126.get_ops4()
    n_traj = psi_batch.shape[0]
    M = wf.n_slices
    T = wf.duration_us * 1e-6
    dt = T / M
    pulse_after, parities = dd_schedule(M, wf.n_dd, wf.dd_sequence if wf.n_dd > 0 else "XY8")
    A_t = float(cell.A_hz[wf.target_qubit])
    H_dip = h126.nuclear_dipolar_hamiltonian(cell.J_hz, ops)

    H_slices = np.zeros((2, M, 16, 16), dtype=np.complex128)
    for bi, sz_phys in enumerate((+0.5, -0.5)):
        for m in range(M):
            pm = parities[m]
            H = H_dip.copy()
            for j in range(4):
                freq = float(cell.A_hz[j]) * sz_phys - pm * 0.5 * A_t + float(offset_hz)
                H += 2.0 * math.pi * freq * ops.Iz[j]
            ux = float(amp_scale) * float(wf.controls_khz[m, 0])
            uy = float(amp_scale) * float(wf.controls_khz[m, 1])
            H += 2.0 * math.pi * 1e3 * (ux * ops.Ix_tot + uy * ops.Iy_tot)
            H_slices[bi, m] = H

    with torch.no_grad():
        H_t = torch.tensor(H_slices, dtype=torch.complex128, device=dev)
        U_nuc = torch.linalg.matrix_exp((-1.0j * dt) * H_t)
        noise_t = torch.tensor(noise_hz_seg, dtype=torch.float64, device=dev) if noise_hz_seg is not None else None

        psi = psi_batch.clone()
        rng = rng or np.random.default_rng(0)

        for m in range(M):
            p = psi.view(n_traj, 2, 16)
            p0 = p[:, 0, :] @ U_nuc[0, m].T
            p1 = p[:, 1, :] @ U_nuc[1, m].T
            if noise_t is not None:
                half_ph = (math.pi * dt) * noise_t[:, m]
                ep = torch.exp(-1.0j * half_ph).unsqueeze(1)
                p0 = p0 * ep
                p1 = p1 * ep.conj()
            psi = torch.stack([p0, p1], dim=1).reshape(n_traj, 32)

            if m in pulse_after:
                U_e = _noisy_electron_pi_batch(pulse_after[m], n_traj, eps_stoch, delta_theta_sys, rng, dev)
                psi = _apply_electron_2x2_to_psi32(U_e, psi)

        # Frame-return U_back for carrier offset + deterministic eigen-frame virtual-Z when n_dd == 0
        iz_diag = np.diag(ops.Iz_tot).real
        back_off = np.exp(+1.0j * 2.0 * math.pi * float(offset_hz) * T * iz_diag) if abs(offset_hz) > 0.0 else np.ones(16, dtype=np.complex128)
        vz_d0 = _vz_diag_16(wf.virtual_z_nuc_rad, ops)
        if wf.n_dd == 0 and wf.gate_name == "cX":
            vz1 = np.array([2.0 * math.pi * (-0.5 * float(cell.A_hz[j]) - 0.5 * A_t) * T for j in range(4)], dtype=np.float64)
            vz_d1 = _vz_diag_16(vz1, ops)
        else:
            vz_d1 = np.ones(16, dtype=np.complex128)
        u0_back = torch.tensor(back_off * vz_d0, dtype=torch.complex128, device=dev)
        u1_back = torch.tensor(back_off * vz_d1, dtype=torch.complex128, device=dev)
        p = psi.view(n_traj, 2, 16)
        p0 = p[:, 0, :] * u0_back.view(1, 16)
        p1 = p[:, 1, :] * u1_back.view(1, 16)

        if wf.apply_virtual_rze_neg_pi2:
            p0 = 1.0j * p0
        psi = torch.stack([p0, p1], dim=1).reshape(n_traj, 32)

        if wf.n_dd > 0:
            net_s = dd_net_electron_sign(wf.n_dd, wf.dd_sequence)
            psi = psi * complex(net_s.conjugate())

    return psi


def run_hahn_echo_32d(
    cell: h126.CellSpec,
    alpha: float,
    dt_s: float = 500e-6 / 64,
    n_traj: int = 512,
    seed: int = 12600,
    device: Optional[torch.device] = None,
) -> Dict[str, float]:
    """Verify time-domain 1/omega^alpha bath calibration directly in full 32D Hahn-echo evolution at T = T2e(f)."""
    dev = device or get_device()
    ops = h126.get_ops4()
    t2e = cell.t2e_s
    n_echo = max(4, int(round(t2e / dt_s)))
    if n_echo % 2 == 1:
        n_echo += 1
    half = n_echo // 2
    rng = np.random.default_rng(seed)
    noise = h126.sample_bath_noise_hz(t2e, alpha, dt_s, n_echo, n_traj, rng)

    psi0 = np.zeros(32, dtype=np.complex128)
    psi0[0] = 1.0 / math.sqrt(2.0)
    psi0[16] = 1.0 / math.sqrt(2.0)
    H_dip = h126.nuclear_dipolar_hamiltonian(cell.J_hz, ops)
    H0_p = H_dip + sum(2.0 * math.pi * (+0.5 * float(cell.A_hz[j])) * ops.Iz[j] for j in range(4))
    H0_m = H_dip + sum(2.0 * math.pi * (-0.5 * float(cell.A_hz[j])) * ops.Iz[j] for j in range(4))

    with torch.no_grad():
        U_p = torch.linalg.matrix_exp((-1.0j * dt_s) * torch.tensor(H0_p, dtype=torch.complex128, device=dev))
        U_m = torch.linalg.matrix_exp((-1.0j * dt_s) * torch.tensor(H0_m, dtype=torch.complex128, device=dev))
        U_x = torch.tensor(-1.0j * h126.PX, dtype=torch.complex128, device=dev).unsqueeze(0).expand(n_traj, 2, 2)
        noise_t = torch.tensor(noise, dtype=torch.float64, device=dev)

        psi = torch.tensor(psi0, dtype=torch.complex128, device=dev).unsqueeze(0).repeat(n_traj, 1)
        for m in range(n_echo):
            p = psi.view(n_traj, 2, 16)
            p0 = p[:, 0, :] @ U_p.T
            p1 = p[:, 1, :] @ U_m.T
            ep = torch.exp((-1.0j * math.pi * dt_s) * noise_t[:, m]).unsqueeze(1)
            p0 = p0 * ep
            p1 = p1 * ep.conj()
            psi = torch.stack([p0, p1], dim=1).reshape(n_traj, 32)
            if m == half - 1:
                psi = _apply_electron_2x2_to_psi32(U_x, psi)

        p = psi.view(n_traj, 2, 16)
        rho01_per_traj = (p[:, 1, :].conj() * p[:, 0, :]).sum(dim=1)
        coherence = float(2.0 * torch.abs(rho01_per_traj.mean()).item())
        norm_err = float((torch.linalg.norm(psi, dim=1) - 1.0).abs().max().item())

    return {
        "t2e_ms": float(t2e * 1e3),
        "actual_echo_ms": float(n_echo * dt_s * 1e3),
        "alpha": float(alpha),
        "n_traj": int(n_traj),
        "coherence_W": coherence,
        "target_inv_e": float(math.exp(-1.0)),
        "abs_err": float(abs(coherence - math.exp(-1.0))),
        "max_state_norm_err": norm_err,
    }
