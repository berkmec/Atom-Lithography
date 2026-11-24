"""CellISA v4.0 instruction set and AtomCellProgrammer / MultiCellProgrammer (Exp132-145).

Compiles high-level quantum/atom-cell programs expressed in ``CellISA`` into
per-cell physical MW/RF control waveforms tailored to each certified register's
measured hyperfine spectrum ``{A_k}``, verifies execution on the full
2^(N_nuc + 1) multi-spin Hilbert space (nominal + +/-400 Hz, +/-2% corners +
XY8 dynamical decoupling), and emits SHA-256 signed ``ProgramCertificate``
and ``MultiCellCertificate`` records (JSONL).

Supported CellISA opcodes (20 total in ``VALID_OPCODES_ALL``):
  * v2.0 (10 opcodes, 100% backwards-compatible):
      INIT, RX, RY, RZ, CZ, CNOT, GHZ, DD_HOLD, MEASURE, ARRAY_EXEC
  * v3.0 (4 multi-cell M4 & wafer-routing opcodes):
      BUS_TUNE, BUS_CZ, LOGICAL_ENCODE, WAFER_MAP_ROUTE
  * v3.5 (3 fault-tolerant echoed-CZ & multiplexed syndrome opcodes):
      ECHO_CZ, MUX_READOUT, SYNDROME_CYCLE
  * v4.0 (3 cloud-QPU / qLDPC / self-healing supervisory opcodes):
      QRAM_SWAP, QLDPC_ROUND, AUTO_RECAL

``VALID_OPCODES`` is preserved as the frozen 17-opcode v3.5 set for 100%
backward compatibility with Exp140/Exp141 regression checks; ``VALID_OPCODES_ALL``
exposes all 20 CellISA v4.0 opcodes.

Includes a portable ``verify_with_exp126_bridge()`` provenance link to the full
32D (2^5) 448-spectator XY8-GRAPE verification ledger in
``results/exp126_atom_cell_programming/exp126.json``.

Epistemic tag: {Model} (simulation/compiler layer; no physical hardware).
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.linalg import expm as _scipy_expm
from scipy.sparse import csr_matrix as _csr_matrix

from .factory import Certificate
from .pulse_engine import (
    CORNER_AMP_SCALES,
    CORNER_OFFSETS_HZ,
    DDRobustnessResult,
    MultiSpinSimulator,
    PulseWaveform,
    su2_rotation,
    synthesize_electron_mw_pulse,
    synthesize_selective_pulse,
)

VALID_OPCODES_V2 = frozenset({
    "INIT", "RX", "RY", "RZ", "CZ", "CNOT", "GHZ", "DD_HOLD", "MEASURE", "ARRAY_EXEC"
})
VALID_OPCODES_V3 = frozenset({
    "BUS_TUNE", "BUS_CZ", "LOGICAL_ENCODE", "WAFER_MAP_ROUTE"
})
VALID_OPCODES_V35 = frozenset({
    "ECHO_CZ", "MUX_READOUT", "SYNDROME_CYCLE"
})
VALID_OPCODES = VALID_OPCODES_V2 | VALID_OPCODES_V3 | VALID_OPCODES_V35
VALID_OPCODES_V4 = frozenset({
    "QRAM_SWAP", "QLDPC_ROUND", "AUTO_RECAL"
})
VALID_OPCODES_ALL = VALID_OPCODES | VALID_OPCODES_V4


def parse_qubit(q: int | str) -> int:
    """Map qubit identifier ('e' or 0 -> 0; 'n0'..'n7' or 1..8 -> 1..8)."""
    if isinstance(q, int):
        if q < 0:
            raise ValueError(f"Qubit index must be >= 0, got {q}")
        return q
    s = str(q).strip().lower()
    if s in ("e", "electron", "q0"):
        return 0
    if s.startswith("n") and s[1:].isdigit():
        return int(s[1:]) + 1
    if s.isdigit():
        return int(s)
    raise ValueError(f"Unrecognized qubit identifier: {q!r}")


@dataclass(frozen=True)
class CellInstruction:
    """Single immutable CellISA instruction."""
    opcode: str
    args: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        op = self.opcode.upper()
        if op not in VALID_OPCODES_ALL:
            raise ValueError(f"Invalid CellISA opcode {self.opcode!r}; valid: {sorted(VALID_OPCODES_ALL)}")
        object.__setattr__(self, "opcode", op)

    def to_dict(self) -> dict[str, Any]:
        return {"opcode": self.opcode, "args": self.args}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CellInstruction":
        return cls(opcode=d["opcode"], args=dict(d.get("args", {})))


@dataclass
class CellProgram:
    """Ordered sequence of CellISA instructions."""
    name: str
    instructions: list[CellInstruction] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, opcode: str, **kwargs: Any) -> "CellProgram":
        self.instructions.append(CellInstruction(opcode=opcode, args=kwargs))
        return self

    def used_nuclear_count(self) -> int:
        max_q = 0
        for inst in self.instructions:
            a = inst.args
            for key in ("target", "control"):
                if key in a:
                    max_q = max(max_q, parse_qubit(a[key]))
            for key in ("qubits",):
                if key in a:
                    for q in a[key]:
                        max_q = max(max_q, parse_qubit(q))
        return max(1, max_q)

    def to_json(self) -> str:
        payload = {
            "name": self.name,
            "instructions": [i.to_dict() for i in self.instructions],
            "metadata": self.metadata,
        }
        return json.dumps(payload, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "CellProgram":
        d = json.loads(text)
        return cls(
            name=d["name"],
            instructions=[CellInstruction.from_dict(x) for x in d["instructions"]],
            metadata=dict(d.get("metadata", {})),
        )


@dataclass
class ScheduleOp:
    """Compiled low-level physical operation inside a CompiledSchedule."""
    kind: str                       # "PULSE", "VIRTUAL_RZ", "DD_HOLD", "MEASURE"
    waveform: PulseWaveform | None = None
    qubit: int | None = None
    angle_rad: float = 0.0
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompiledSchedule:
    """Hardware-level MW/RF pulse schedule bound to one certified register."""
    program_name: str
    register_id: str
    b_field_T: float
    active_lines_Hz: list[float]
    n_qubits: int
    pulse_mode: str
    ops: list[ScheduleOp] = field(default_factory=list)

    @property
    def pulse_count(self) -> int:
        return sum(1 for o in self.ops if o.kind == "PULSE")

    @property
    def total_duration_us(self) -> float:
        tot_s = 0.0
        for o in self.ops:
            if o.kind == "PULSE" and o.waveform is not None:
                tot_s += o.waveform.duration_s
            elif o.kind == "DD_HOLD":
                tot_s += float(o.params.get("duration_us", 0.0)) * 1e-6
        return tot_s * 1e6

    def summary_segments(self) -> list[dict[str, Any]]:
        segs = []
        for o in self.ops:
            if o.kind == "PULSE" and o.waveform is not None:
                w = o.waveform
                segs.append({
                    "kind": "PULSE",
                    "channel": w.channel,
                    "label": w.label,
                    "freq_Hz": round(w.freq_Hz, 3),
                    "duration_us": round(w.duration_s * 1e6, 4),
                    "slices": len(w.ux_kHz),
                    "mode": w.mode,
                    "worst_corner_fid": round(w.worst_corner_fidelity, 6),
                })
            elif o.kind == "VIRTUAL_RZ":
                segs.append({
                    "kind": "VIRTUAL_RZ",
                    "qubit": o.qubit,
                    "angle_rad": round(o.angle_rad, 6),
                })
            elif o.kind == "DD_HOLD":
                segs.append({"kind": "DD_HOLD", **o.params})
            elif o.kind == "MEASURE":
                segs.append({"kind": "MEASURE", **o.params})
        return segs


@dataclass
class ProgramCertificate:
    """SHA-256 signed verification certificate for a compiled & executed CellProgram."""
    program_name: str
    register_id: str
    pulse_mode: str
    n_qubits: int
    active_lines_Hz: list[float]
    pulse_count: int
    total_duration_us: float
    nominal_state_fidelity: float
    corner_min_fidelity: float
    corner_mean_fidelity: float
    dd_coherence_gain: float | None
    dd_coherence: float | None
    measurement_counts: dict[str, int]
    readout_visibility: float
    certified: bool
    epistemic_tag: str = "Model"
    sha256: str = ""

    def canonical_payload(self) -> str:
        d = asdict(self)
        d.pop("sha256", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

    def compute_sha256(self) -> str:
        return hashlib.sha256(self.canonical_payload().encode("utf-8")).hexdigest()

    def sign(self) -> "ProgramCertificate":
        self.sha256 = self.compute_sha256()
        return self

    def verify_signature(self) -> bool:
        return bool(self.sha256) and self.sha256 == self.compute_sha256()


# ---------------------------------------------------------------------------
# Built-in canonical CellISA benchmark programs
# ---------------------------------------------------------------------------

def program_bell(shots: int = 1024, dd_us: float = 200.0) -> CellProgram:
    """2-qubit Bell state |Phi+> = (|00> + |11>)/sqrt(2) on (e, n0) + XY8 DD."""
    p = CellProgram(name="bell", metadata={"expected_support": ["00", "11"]})
    p.add("INIT", qubits=["e", "n0"], state="00")
    p.add("RY", target="e", theta=math.pi / 2.0)
    p.add("CNOT", control="e", target="n0")
    if dd_us > 0:
        p.add("DD_HOLD", duration_us=dd_us, sequence="XY8", pulses=16)
    p.add("MEASURE", qubits=["e", "n0"], basis="Z", shots=shots)
    return p


def program_ghz(n_qubits: int = 4, shots: int = 1024, dd_us: float = 200.0) -> CellProgram:
    """N-qubit GHZ state (|0..0> + |1..1>)/sqrt(2) on e + n0..n{N-2} + XY8 DD."""
    if n_qubits < 2:
        raise ValueError("GHZ requires at least 2 qubits")
    qubits = ["e"] + [f"n{k}" for k in range(n_qubits - 1)]
    p = CellProgram(
        name=f"ghz{n_qubits}",
        metadata={"expected_support": ["0" * n_qubits, "1" * n_qubits]},
    )
    p.add("INIT", qubits=qubits, state="0" * n_qubits)
    p.add("GHZ", qubits=qubits)
    if dd_us > 0:
        p.add("DD_HOLD", duration_us=dd_us, sequence="XY8", pulses=16)
    p.add("MEASURE", qubits=qubits, basis="Z", shots=shots)
    return p


def _add_hadamard(p: CellProgram, q: str) -> None:
    # H = -i * RY(pi/2) @ RZ(pi) (exact up to global phase -i)
    p.add("RZ", target=q, theta=math.pi)
    p.add("RY", target=q, theta=math.pi / 2.0)


def _add_cphase(p: CellProgram, ctrl: str, tgt: str, phi: float) -> None:
    """Exact controlled-phase diag(1, 1, 1, exp(i*phi)) using RZ + CNOT."""
    p.add("RZ", target=ctrl, theta=phi / 2.0)
    p.add("RZ", target=tgt, theta=phi / 2.0)
    p.add("CNOT", control=ctrl, target=tgt)
    p.add("RZ", target=tgt, theta=-phi / 2.0)
    p.add("CNOT", control=ctrl, target=tgt)


def program_qft3(input_state: str = "101", shots: int = 1024) -> CellProgram:
    """3-qubit Quantum Fourier Transform on (e, n0, n1) from computational basis state."""
    if len(input_state) != 3 or any(c not in "01" for c in input_state):
        raise ValueError("input_state must be a 3-bit string")
    qubits = ["e", "n0", "n1"]
    p = CellProgram(name="qft3", metadata={"input_state": input_state})
    p.add("INIT", qubits=qubits, state=input_state)
    # QFT on [e, n0, n1] (CPHASE is symmetric, so put 'e' as control whenever involved!)
    _add_hadamard(p, "e")
    _add_cphase(p, "e", "n0", math.pi / 2.0)
    _add_cphase(p, "e", "n1", math.pi / 4.0)
    _add_hadamard(p, "n0")
    _add_cphase(p, "n0", "n1", math.pi / 2.0)
    _add_hadamard(p, "n1")
    # Bit-reversal SWAP(e, n1)
    p.add("CNOT", control="e", target="n1")
    p.add("CNOT", control="n1", target="e")
    p.add("CNOT", control="e", target="n1")
    p.add("MEASURE", qubits=qubits, basis="Z", shots=shots)
    return p


def program_repcode3(logical_bit: int = 1, shots: int = 1024, dd_us: float = 200.0) -> CellProgram:
    """3-qubit bit-flip repetition code encode -> XY8 DD memory hold -> measure."""
    qubits = ["e", "n0", "n1"]
    p = CellProgram(
        name="repcode3",
        metadata={"logical_bit": int(logical_bit), "codeword": str(int(logical_bit)) * 3},
    )
    p.add("INIT", qubits=qubits, state="000")
    if int(logical_bit) == 1:
        p.add("RX", target="e", theta=math.pi)
    p.add("CNOT", control="e", target="n0")
    p.add("CNOT", control="e", target="n1")
    if dd_us > 0:
        p.add("DD_HOLD", duration_us=dd_us, sequence="XY8", pulses=16)
    p.add("MEASURE", qubits=qubits, basis="Z", shots=shots)
    return p


def builtin_program(name: str, **kwargs: Any) -> CellProgram:
    key = name.strip().lower()
    if key == "bell":
        return program_bell(**kwargs)
    if key in ("ghz", "ghz4"):
        return program_ghz(n_qubits=4, **kwargs)
    if key == "ghz3":
        return program_ghz(n_qubits=3, **kwargs)
    if key == "qft3":
        return program_qft3(**kwargs)
    if key == "repcode3":
        return program_repcode3(**kwargs)
    raise ValueError(f"Unknown built-in CellISA program: {name!r}")


# ---------------------------------------------------------------------------
# Ideal reference simulator & AtomCellProgrammer compiler/verifier
# ---------------------------------------------------------------------------

def _apply_ideal_1q(state: np.ndarray, n_qubits: int, q: int, U: np.ndarray) -> np.ndarray:
    psi = state.reshape([2] * n_qubits)
    psi = np.tensordot(U, psi, axes=([1], [q]))
    psi = np.moveaxis(psi, 0, q)
    return psi.reshape(1 << n_qubits)


def _apply_ideal_controlled(state: np.ndarray, n_qubits: int, ctrl: int, tgt: int, U: np.ndarray) -> np.ndarray:
    psi = state.reshape([2] * n_qubits).copy()
    slc = [slice(None)] * n_qubits
    slc[ctrl] = 1
    sub = psi[tuple(slc)]
    t_axis = tgt if tgt < ctrl else tgt - 1
    sub = np.tensordot(U, sub, axes=([1], [t_axis]))
    sub = np.moveaxis(sub, 0, t_axis)
    psi[tuple(slc)] = sub
    return psi.reshape(1 << n_qubits)


def simulate_ideal(program: CellProgram, n_qubits: int) -> np.ndarray:
    """Exact noiseless reference statevector for a CellProgram."""
    dim = 1 << n_qubits
    state = np.zeros(dim, dtype=complex)
    state[0] = 1.0 + 0.0j
    X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
    Z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
    for inst in program.instructions:
        op, a = inst.opcode, inst.args
        if op == "INIT":
            st = str(a.get("state", "0" * n_qubits))
            st = st.ljust(n_qubits, "0")[:n_qubits]
            state = np.zeros(dim, dtype=complex)
            state[int(st, 2)] = 1.0 + 0.0j
        elif op == "RX":
            state = _apply_ideal_1q(state, n_qubits, parse_qubit(a["target"]), su2_rotation("X", float(a["theta"])))
        elif op == "RY":
            state = _apply_ideal_1q(state, n_qubits, parse_qubit(a["target"]), su2_rotation("Y", float(a["theta"])))
        elif op == "RZ":
            state = _apply_ideal_1q(state, n_qubits, parse_qubit(a["target"]), su2_rotation("Z", float(a["theta"])))
        elif op == "CNOT":
            state = _apply_ideal_controlled(state, n_qubits, parse_qubit(a["control"]), parse_qubit(a["target"]), X)
        elif op == "CZ":
            state = _apply_ideal_controlled(state, n_qubits, parse_qubit(a["control"]), parse_qubit(a["target"]), Z)
        elif op == "GHZ":
            qs = [parse_qubit(q) for q in a["qubits"]]
            state = _apply_ideal_1q(state, n_qubits, qs[0], su2_rotation("Y", math.pi / 2.0))
            for tgt in qs[1:]:
                state = _apply_ideal_controlled(state, n_qubits, qs[0], tgt, X)
        elif op == "QRAM_SWAP":
            qa = parse_qubit(a.get("qubit_a", "e"))
            qb = parse_qubit(a.get("qubit_b", "n0"))
            state = _apply_ideal_controlled(state, n_qubits, qa, qb, X)
            state = _apply_ideal_controlled(state, n_qubits, qb, qa, X)
            state = _apply_ideal_controlled(state, n_qubits, qa, qb, X)
        elif op in ("DD_HOLD", "MEASURE", "ARRAY_EXEC", "AUTO_RECAL", "QLDPC_ROUND"):
            pass
    return state


class AtomCellProgrammer:
    """Compiles CellISA programs to physical MW/RF pulse schedules per certified cell."""

    def __init__(
        self,
        b_field_T: float = 1.5,
        pulse_mode: str = "shaped",
        readout_visibility: float = 0.99,
        pulse_error_eps: float = 1e-3,
        cert_fidelity_threshold: float = 0.95,
    ):
        self.b_field_T = float(b_field_T)
        self.pulse_mode = str(pulse_mode)
        self.readout_visibility = float(readout_visibility)
        self.pulse_error_eps = float(pulse_error_eps)
        self.cert_fidelity_threshold = float(cert_fidelity_threshold)

    def _emit_pulse(
        self,
        ops: list[ScheduleOp],
        A_active: np.ndarray,
        qubit: int,
        axis: str,
        theta: float,
        electron_branch: int | None,
        cache: dict[tuple, PulseWaveform],
    ) -> None:
        if abs(theta) < 1e-12:
            return
        if qubit == 0:
            key = ("MW", axis.upper(), round(theta, 8))
            if key not in cache:
                cache[key] = synthesize_electron_mw_pulse(
                    axis=axis, theta_rad=theta, b_field_T=self.b_field_T
                )
            ops.append(ScheduleOp(kind="PULSE", waveform=cache[key]))
            return

        nuc_idx = qubit - 1
        branches = (electron_branch,) if electron_branch is not None else (0, 1)
        for br in branches:
            key = ("RF", nuc_idx, br, axis.upper(), round(theta, 8), self.pulse_mode)
            if key not in cache:
                cache[key] = synthesize_selective_pulse(
                    A_active,
                    nucleus_idx=nuc_idx,
                    electron_branch=br,
                    axis=axis,
                    theta_rad=theta,
                    mode=self.pulse_mode,
                    b_field_T=self.b_field_T,
                )
            ops.append(ScheduleOp(kind="PULSE", waveform=cache[key]))

    def _emit_h(self, ops, A_active, q: int, cache) -> None:
        ops.append(ScheduleOp(kind="VIRTUAL_RZ", qubit=q, angle_rad=math.pi))
        self._emit_pulse(ops, A_active, q, "Y", math.pi / 2.0, None, cache)

    def _emit_cnot_e_to_n(self, ops, A_active, nuc_q: int, cache) -> None:
        # Selective RF Rx(pi) on electron branch e=1 gives -i*X on e=1;
        # virtual RZ(e, +pi/2) cancels the -i relative phase exactly.
        self._emit_pulse(ops, A_active, nuc_q, "X", math.pi, 1, cache)
        ops.append(ScheduleOp(kind="VIRTUAL_RZ", qubit=0, angle_rad=math.pi / 2.0))

    def _emit_cnot_n_to_e(self, ops, A_active, nuc_q: int, cache) -> None:
        self._emit_h(ops, A_active, 0, cache)
        self._emit_h(ops, A_active, nuc_q, cache)
        self._emit_cnot_e_to_n(ops, A_active, nuc_q, cache)
        self._emit_h(ops, A_active, 0, cache)
        self._emit_h(ops, A_active, nuc_q, cache)

    def _emit_swap_e_n(self, ops, A_active, nuc_q: int, cache) -> None:
        self._emit_cnot_e_to_n(ops, A_active, nuc_q, cache)
        self._emit_cnot_n_to_e(ops, A_active, nuc_q, cache)
        self._emit_cnot_e_to_n(ops, A_active, nuc_q, cache)

    def _emit_cz(self, ops, A_active, c: int, t: int, cache) -> None:
        if c == t:
            raise ValueError("CZ control and target must be distinct")
        if c == 0 or t == 0:
            nuc_q = t if c == 0 else c
            self._emit_h(ops, A_active, nuc_q, cache)
            self._emit_cnot_e_to_n(ops, A_active, nuc_q, cache)
            self._emit_h(ops, A_active, nuc_q, cache)
        else:
            # Exact operator identity: CZ(j, k) = SWAP(e, j) . CZ(e, k) . SWAP(e, j)
            self._emit_swap_e_n(ops, A_active, c, cache)
            self._emit_cz(ops, A_active, 0, t, cache)
            self._emit_swap_e_n(ops, A_active, c, cache)

    def _emit_cnot(self, ops, A_active, c: int, t: int, cache) -> None:
        if c == t:
            raise ValueError("CNOT control and target must be distinct")
        if c == 0:
            self._emit_cnot_e_to_n(ops, A_active, t, cache)
        elif t == 0:
            self._emit_cnot_n_to_e(ops, A_active, c, cache)
        else:
            # CNOT(j -> k) = H_k . CZ(j, k) . H_k
            self._emit_h(ops, A_active, t, cache)
            self._emit_cz(ops, A_active, c, t, cache)
            self._emit_h(ops, A_active, t, cache)

    def compile(self, cert: Certificate, program: CellProgram) -> CompiledSchedule:
        """Compile ``program`` into physical RF/MW pulses calibrated to ``cert.lines_Hz``."""
        if not cert.lines_Hz:
            raise ValueError(f"Certificate {cert.register_id} has empty lines_Hz; cannot compile")
        n_nuc_needed = program.used_nuclear_count()
        lines = np.sort(np.abs(np.asarray(cert.lines_Hz, dtype=float)))[::-1]
        if n_nuc_needed > len(lines):
            raise ValueError(
                f"Program {program.name} needs {n_nuc_needed} nuclei, "
                f"certificate {cert.register_id} only has {len(lines)}"
            )
        A_active = lines[:n_nuc_needed]
        ops: list[ScheduleOp] = []
        cache: dict[tuple, PulseWaveform] = {}

        for inst in program.instructions:
            op, a = inst.opcode, inst.args
            if op == "INIT":
                ops.append(ScheduleOp(kind="INIT", params=dict(a)))
            elif op == "RX":
                self._emit_pulse(ops, A_active, parse_qubit(a["target"]), "X", float(a["theta"]), None, cache)
            elif op == "RY":
                self._emit_pulse(ops, A_active, parse_qubit(a["target"]), "Y", float(a["theta"]), None, cache)
            elif op == "RZ":
                ops.append(ScheduleOp(kind="VIRTUAL_RZ", qubit=parse_qubit(a["target"]), angle_rad=float(a["theta"])))
            elif op == "CNOT":
                self._emit_cnot(ops, A_active, parse_qubit(a["control"]), parse_qubit(a["target"]), cache)
            elif op == "CZ":
                self._emit_cz(ops, A_active, parse_qubit(a["control"]), parse_qubit(a["target"]), cache)
            elif op == "GHZ":
                qs = [parse_qubit(q) for q in a["qubits"]]
                self._emit_pulse(ops, A_active, qs[0], "Y", math.pi / 2.0, None, cache)
                for tgt in qs[1:]:
                    self._emit_cnot(ops, A_active, qs[0], tgt, cache)
            elif op == "DD_HOLD":
                ops.append(ScheduleOp(kind="DD_HOLD", params={
                    "duration_us": float(a.get("duration_us", 200.0)),
                    "sequence": str(a.get("sequence", "XY8")),
                    "pulses": int(a.get("pulses", 16)),
                }))
            elif op == "MEASURE":
                ops.append(ScheduleOp(kind="MEASURE", params={
                    "qubits": [parse_qubit(q) for q in a.get("qubits", list(range(n_nuc_needed + 1)))],
                    "basis": str(a.get("basis", "Z")),
                    "shots": int(a.get("shots", 1024)),
                }))
            elif op == "QRAM_SWAP":
                qa = parse_qubit(a.get("qubit_a", "e"))
                qb = parse_qubit(a.get("qubit_b", "n0"))
                self._emit_cnot(ops, A_active, qa, qb, cache)
                self._emit_cnot(ops, A_active, qb, qa, cache)
                self._emit_cnot(ops, A_active, qa, qb, cache)
            elif op == "ARRAY_EXEC":
                raise ValueError("Use execute_array() to run ARRAY_EXEC across multiple cells")

        return CompiledSchedule(
            program_name=program.name,
            register_id=cert.register_id,
            b_field_T=self.b_field_T,
            active_lines_Hz=[float(x) for x in A_active],
            n_qubits=n_nuc_needed + 1,
            pulse_mode=self.pulse_mode,
            ops=ops,
        )

    def _run_schedule(
        self,
        schedule: CompiledSchedule,
        detuning_offset_Hz: float = 0.0,
        amp_scale: float = 1.0,
        with_dd_noise: bool = True,
        seed: int = 20261122,
    ) -> tuple[MultiSpinSimulator, DDRobustnessResult | None, dict[str, int]]:
        sim = MultiSpinSimulator(np.asarray(schedule.active_lines_Hz), b_field_T=schedule.b_field_T)
        dd_res: DDRobustnessResult | None = None
        meas_counts: dict[str, int] = {}
        rng = np.random.default_rng(seed)

        for o in schedule.ops:
            if o.kind == "INIT":
                st = str(o.params.get("state", "0" * schedule.n_qubits))
                st = st.ljust(schedule.n_qubits, "0")[:schedule.n_qubits]
                sim.reset(st)
            elif o.kind == "PULSE" and o.waveform is not None:
                sim.apply_waveform(
                    o.waveform,
                    detuning_offset_Hz=detuning_offset_Hz,
                    amp_scale=amp_scale,
                )
            elif o.kind == "VIRTUAL_RZ" and o.qubit is not None:
                sim.apply_virtual_rz(o.qubit, o.angle_rad)
            elif o.kind == "DD_HOLD" and with_dd_noise:
                dd_res = sim.apply_dd_hold(
                    duration_us=o.params["duration_us"],
                    n_pulses=o.params["pulses"],
                    pulse_error_eps=self.pulse_error_eps,
                    seed=seed,
                )
            elif o.kind == "MEASURE":
                meas_counts = sim.sample_measurements(
                    qubits=o.params["qubits"],
                    shots=o.params["shots"],
                    visibility=self.readout_visibility,
                    rng=rng,
                )
        return sim, dd_res, meas_counts

    def execute_and_certify(
        self,
        cert: Certificate,
        program: CellProgram,
        verify_corners: bool = True,
        corner_offsets_Hz: tuple[float, ...] = (-400.0, 0.0, 400.0),
        corner_amp_scales: tuple[float, ...] = (0.98, 1.00, 1.02),
        seed: int = 20261122,
    ) -> tuple[CompiledSchedule, ProgramCertificate]:
        """Compile, simulate (nominal + corners), and emit a SHA-256 signed ProgramCertificate."""
        schedule = self.compile(cert, program)
        psi_ideal = simulate_ideal(program, schedule.n_qubits)

        # Nominal physical simulation (including XY8 DD & finite visibility readout)
        sim_nom, dd_res, meas_counts = self._run_schedule(
            schedule, detuning_offset_Hz=0.0, amp_scale=1.0, with_dd_noise=True, seed=seed
        )
        nom_fid = float(abs(np.vdot(psi_ideal, sim_nom.state)) ** 2)

        # Corner verification across +/-400 Hz detuning x +/-2% RF amplitude
        corner_fids = [nom_fid]
        if verify_corners:
            corner_fids = []
            for off in corner_offsets_Hz:
                for sc in corner_amp_scales:
                    sim_c, _, _ = self._run_schedule(
                        schedule, detuning_offset_Hz=off, amp_scale=sc, with_dd_noise=False, seed=seed
                    )
                    corner_fids.append(float(abs(np.vdot(psi_ideal, sim_c.state)) ** 2))

        c_min = float(min(corner_fids))
        c_mean = float(np.mean(corner_fids))
        passed = bool(nom_fid >= self.cert_fidelity_threshold)

        pcert = ProgramCertificate(
            program_name=program.name,
            register_id=cert.register_id,
            pulse_mode=self.pulse_mode,
            n_qubits=schedule.n_qubits,
            active_lines_Hz=schedule.active_lines_Hz,
            pulse_count=schedule.pulse_count,
            total_duration_us=round(schedule.total_duration_us, 4),
            nominal_state_fidelity=round(nom_fid, 6),
            corner_min_fidelity=round(c_min, 6),
            corner_mean_fidelity=round(c_mean, 6),
            dd_coherence_gain=round(dd_res.coherence_gain, 4) if dd_res else None,
            dd_coherence=round(dd_res.dd_coherence, 6) if dd_res else None,
            measurement_counts=meas_counts,
            readout_visibility=self.readout_visibility,
            certified=passed,
        ).sign()
        return schedule, pcert

    def execute_array(
        self,
        certs: list[Certificate],
        program: CellProgram,
        verify_corners: bool = True,
        out_jsonl: str | Path | None = None,
        seed: int = 20261122,
    ) -> list[tuple[CompiledSchedule, ProgramCertificate]]:
        """Execute an ``ARRAY_EXEC`` across multiple certified cells, compiling bespoke pulses per cell."""
        results = []
        for idx, cert in enumerate(certs):
            sched, pcert = self.execute_and_certify(
                cert, program, verify_corners=verify_corners, seed=seed + idx
            )
            results.append((sched, pcert))
        if out_jsonl is not None:
            path = Path(out_jsonl)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                for _sched, pcert in results:
                    f.write(json.dumps(asdict(pcert)) + "\n")
        return results


# ===========================================================================
# CellISA v3.0 — Multi-Cell M4 Cavity-QED Bus, Wafer Routing & Exp126 Bridge
# ===========================================================================

@dataclass(frozen=True)
class BusLinkSpec:
    """High-impedance NbTiN cavity-QED dispersive spin-photon bus parameters."""
    cell_a: str
    cell_b: str
    g_MHz: float = 15.0             # spin-photon vacuum Rabi coupling (high-Z NbTiN)
    detuning_MHz: float = 150.0     # dispersive detuning Delta = 10 * g
    kappa_MHz: float = 0.50         # cavity linewidth (Q ~ 1.4e4 @ 7 GHz)
    t2_electron_us: float = 500.0   # DD-protected electron coherence time (us)
    z_resonator_kOhm: float = 2.5   # NbTiN kinetic-inductance resonator impedance
    hop_distance: int = 1           # number of bus hops on wafer grid

    @property
    def j_bus_MHz(self) -> float:
        """Dispersive exchange coupling J_bus = g^2 / Delta (MHz)."""
        return (self.g_MHz * self.g_MHz) / max(self.detuning_MHz, 1e-6)

    @property
    def cz_duration_us(self) -> float:
        """Two-cell CZ gate duration t_CZ = 1 / (4 * J_bus) in microseconds."""
        return 1.0 / (4.0 * max(self.j_bus_MHz, 1e-6))

    @property
    def purcell_rate_MHz(self) -> float:
        """Cavity-mediated Purcell decay rate 2 * kappa * (g / Delta)^2 (MHz)."""
        ratio = self.g_MHz / max(self.detuning_MHz, 1e-6)
        return 2.0 * self.kappa_MHz * (ratio * ratio)

    @property
    def cz_fidelity(self) -> float:
        """Single-hop physical dispersive CZ fidelity (Purcell + T2 dephasing)."""
        t_us = self.cz_duration_us
        err_purcell = 2.0 * math.pi * self.purcell_rate_MHz * t_us
        err_t2 = 2.0 * t_us / max(self.t2_electron_us, 1e-3)
        f_single = math.exp(-(err_purcell + err_t2))
        return float(f_single ** max(1, int(self.hop_distance)))


@dataclass
class WaferSite:
    """One physical fabrication site on a heterogeneous Mode B (f=1%) wafer grid."""
    row: int
    col: int
    status: str                     # "working", "crowded", "blank"
    certificate: Certificate | None = None
    spec_time_ms: float = 0.0

    @property
    def coord(self) -> tuple[int, int]:
        return (self.row, self.col)

    @property
    def cell_id(self) -> str:
        return self.certificate.register_id if self.certificate else f"DEAD-R{self.row}C{self.col}"


@dataclass
class WaferRoutingResult:
    """Dynamic routing map selecting connected working cells around dead sites."""
    grid_rows: int
    grid_cols: int
    working_sites: int
    dead_sites: int
    target_cells: int
    routed: bool
    assigned_coords: list[tuple[int, int]]
    assigned_cell_ids: list[str]
    bus_edges: list[tuple[str, str, int]]    # (cell_a, cell_b, manhattan_hops)
    bypassed_dead_coords: list[tuple[int, int]]
    mean_bus_hops: float
    total_bus_hops: int


@dataclass
class MultiCellCertificate:
    """SHA-256 signed verification certificate for a CellISA v3.0 multi-cell program."""
    isa_version: str
    program_name: str
    routed_cell_ids: list[str]
    routed_coords: list[list[int]]
    bus_links: list[dict[str, Any]]
    logical_code: str
    local_pulse_count: int
    bus_cz_count: int
    total_duration_us: float
    joint_state_fidelity: float
    min_bus_cz_fidelity: float
    logical_error_rate: float
    exp126_bridge: dict[str, Any]
    certified: bool
    epistemic_tag: str = "Model"
    sha256: str = ""

    def canonical_payload(self) -> str:
        d = asdict(self)
        d.pop("sha256", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

    def compute_sha256(self) -> str:
        return hashlib.sha256(self.canonical_payload().encode("utf-8")).hexdigest()

    def sign(self) -> "MultiCellCertificate":
        self.sha256 = self.compute_sha256()
        return self

    def verify_signature(self) -> bool:
        return bool(self.sha256) and self.sha256 == self.compute_sha256()


def verify_with_exp126_bridge(
    certs: list[Certificate],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Portable provenance bridge linking CellISA certificates to Exp126 32D verification.

    Uses ``Path(__file__).resolve().parents[2]`` (zero hardcoded host paths) to read
    ``results/exp126_atom_cell_programming/exp126.json`` and verify every cell's
    spectral gap and Vandermonde rank against the Exp126 32D 448-spectator benchmark.
    """
    root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    exp126_path = root / "results" / "exp126_atom_cell_programming" / "exp126.json"
    min_gaps = []
    vdm_ranks = []
    for c in certs:
        a = np.sort(np.abs(np.asarray(c.lines_Hz, dtype=float)))
        if len(a) >= 2:
            tr = np.sort(np.concatenate([a * 0.5, -a * 0.5]))
            min_gaps.append(float(np.min(np.diff(tr))))
            # Vandermonde rank on normalized couplings (Exp42/126 addressability check)
            a_norm = a / max(float(np.max(a)), 1.0)
            vdm = np.vander(a_norm, N=len(a_norm), increasing=True)
            vdm_ranks.append(int(np.linalg.matrix_rank(vdm)))
        else:
            min_gaps.append(0.0)
            vdm_ranks.append(0)

    bridge: dict[str, Any] = {
        "exp126_ledger_found": exp126_path.is_file(),
        "n_cells_checked": len(certs),
        "min_spectral_gap_Hz": round(min(min_gaps), 2) if min_gaps else 0.0,
        "all_clear_5kHz_gate": bool(all(g >= 5_000.0 for g in min_gaps)) if min_gaps else False,
        "min_vandermonde_rank": min(vdm_ranks) if vdm_ranks else 0,
        "dd_sweetspot_pulses": 32,
        "abstraction_note": (
            "CellISA v3.0 fast compiler verified locally on 2^(N+1) + cavity-bus model; "
            "full 32D 448-spectator interleaved XY8-GRAPE benchmark anchored to Exp126."
        ),
    }
    if exp126_path.is_file():
        d126 = json.loads(exp126_path.read_text(encoding="utf-8"))
        v126 = d126.get("verdicts", {})
        p4 = v126.get("P126_4_risk_r3_interleaved_dd_f1", {}).get("measured", {})
        p7 = v126.get("P126_7_multicell_program_fidelities", {}).get("measured", {})
        bridge["exp126_Q32D_f1_N64_alpha1"] = p4.get("Q_32d_f1_N64_alpha1_e1e3")
        bridge["exp126_Q32D_f1_N64_alpha2"] = p4.get("Q_32d_f1_N64_alpha2_e1e3")
        bridge["exp126_P126_4_pass"] = bool(v126.get("P126_4_risk_r3_interleaved_dd_f1", {}).get("passed", False))
        bridge["exp126_16cell_bell_mean"] = p7.get("mean_bell_a2")
        bridge["exp126_16cell_ghz4_mean"] = p7.get("mean_ghz4_a2")
        bridge["exp126_16cell_bitflip3_mean"] = p7.get("mean_bitflip3_a2")
    return bridge


class WaferRouter:
    """Dynamic WAFER_MAP_ROUTE solver on a heterogeneous Mode B (~51% yield) wafer grid.

    Models shared NbTiN cavity-QED bus rails connecting working cells within
    Manhattan distance <= ``max_bus_reach`` (shared row/column bus resonator).
    Finds the minimum-hop, highest-margin connected cluster of ``target_cells``
    working sites while bypassing dead/crowded/blank sites.
    """

    def __init__(self, max_bus_reach: int = 2):
        self.max_bus_reach = int(max_bus_reach)

    def route(self, sites: list[WaferSite], target_cells: int = 4) -> WaferRoutingResult:
        rows = max(s.row for s in sites) + 1 if sites else 0
        cols = max(s.col for s in sites) + 1 if sites else 0
        working = [s for s in sites if s.status == "working" and s.certificate is not None]
        dead = [s for s in sites if s.status != "working" or s.certificate is None]

        if len(working) < target_cells:
            return WaferRoutingResult(
                grid_rows=rows,
                grid_cols=cols,
                working_sites=len(working),
                dead_sites=len(dead),
                target_cells=target_cells,
                routed=False,
                assigned_coords=[s.coord for s in working],
                assigned_cell_ids=[s.cell_id for s in working],
                bus_edges=[],
                bypassed_dead_coords=[s.coord for s in dead],
                mean_bus_hops=float("inf"),
                total_bus_hops=0,
            )

        # Build adjacency list over working sites connected within max_bus_reach
        # (shared row/col cavity bus or nearby 2D resonator junction)
        adj: dict[int, list[tuple[int, int, int]]] = {i: [] for i in range(len(working))}
        for i in range(len(working)):
            for j in range(i + 1, len(working)):
                dist = abs(working[i].row - working[j].row) + abs(working[i].col - working[j].col)
                same_rail = (working[i].row == working[j].row) or (working[i].col == working[j].col)
                if dist <= self.max_bus_reach or (same_rail and dist <= self.max_bus_reach + 1):
                    # Effective bus hop count: direct rail link = 1, indirect = 2
                    hops = 1 if dist <= self.max_bus_reach else 2
                    adj[i].append((j, hops, dist))
                    adj[j].append((i, hops, dist))

        # Find best connected tree of size ``target_cells`` minimizing:
        #   (1) total resonator bus hops,
        #   (2) total physical Manhattan trace distance (prefers nearest-neighbor dist=1),
        #   (3) breaking ties by highest spectral gap margin!
        best_tree: tuple[int, int, float, list[int], list[tuple[int, int, int]]] | None = None
        for seed_idx in range(len(working)):
            chosen = [seed_idx]
            chosen_set = {seed_idx}
            edges: list[tuple[int, int, int]] = []
            total_hops = 0
            total_dist = 0
            # Prim-style greedy minimum-hop, minimum-distance tree growth from seed_idx
            while len(chosen) < target_cells:
                cand_edge = None
                for u in chosen:
                    for v, h, d in adj[u]:
                        if v in chosen_set:
                            continue
                        margin = working[v].certificate.min_spacing_Hz if working[v].certificate else 0.0
                        score = (h, d, -margin)
                        if cand_edge is None or score < cand_edge[0]:
                            cand_edge = (score, u, v, h, d)
                if cand_edge is None:
                    break
                _, u_sel, v_sel, h_sel, d_sel = cand_edge
                chosen.append(v_sel)
                chosen_set.add(v_sel)
                edges.append((u_sel, v_sel, h_sel))
                total_hops += h_sel
                total_dist += d_sel
            if len(chosen) == target_cells:
                min_margin = min(
                    working[i].certificate.min_spacing_Hz for i in chosen if working[i].certificate
                )
                key = (total_hops, total_dist, -min_margin)
                if best_tree is None or key < (best_tree[0], best_tree[1], best_tree[2]):
                    best_tree = (total_hops, total_dist, -min_margin, chosen, edges)

        if best_tree is None:
            return WaferRoutingResult(
                grid_rows=rows,
                grid_cols=cols,
                working_sites=len(working),
                dead_sites=len(dead),
                target_cells=target_cells,
                routed=False,
                assigned_coords=[],
                assigned_cell_ids=[],
                bus_edges=[],
                bypassed_dead_coords=[s.coord for s in dead],
                mean_bus_hops=float("inf"),
                total_bus_hops=0,
            )

        total_hops, _total_dist, _, chosen_idx, edges_idx = best_tree
        assigned_coords = [working[i].coord for i in chosen_idx]
        assigned_ids = [working[i].cell_id for i in chosen_idx]
        bus_edges = [(working[u].cell_id, working[v].cell_id, int(h)) for u, v, h in edges_idx]
        return WaferRoutingResult(
            grid_rows=rows,
            grid_cols=cols,
            working_sites=len(working),
            dead_sites=len(dead),
            target_cells=target_cells,
            routed=True,
            assigned_coords=assigned_coords,
            assigned_cell_ids=assigned_ids,
            bus_edges=bus_edges,
            bypassed_dead_coords=[s.coord for s in dead],
            mean_bus_hops=float(total_hops / max(len(bus_edges), 1)),
            total_bus_hops=int(total_hops),
        )


# ===========================================================================
# Physics Engines for CellISA v3.5 / v4.0 (Exp137, Exp140, Exp144, Exp147)
# ===========================================================================

_H_PLANCK = 6.62607015e-34
_E_CHARGE = 1.602176634e-19
_K_BOLTZMANN = 1.380649e-23
_GHZ_PER_UEV = (_E_CHARGE * 1e-6) / _H_PLANCK / 1e9

# ---------------------------------------------------------------------------
# 1. Exact 16D (Q1 x Q2 x 4-Fock Cavity) Strang-Split Lindblad + 1/f Choi CZ
# ---------------------------------------------------------------------------
_SB_I2 = np.eye(2, dtype=np.complex128)
_SB_X2 = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
_SB_Y2 = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=np.complex128)
_SB_Z2 = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)
_SB_SM = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.complex128)
_SB_NC = 4
_SB_AC = np.diag(np.sqrt(np.arange(1, _SB_NC, dtype=np.float64)), 1).astype(np.complex128)
_SB_ADC = _SB_AC.T.copy()
_SB_NC_OP = _SB_ADC @ _SB_AC
_SB_XC_OP = _SB_AC + _SB_ADC
_SB_CZ4 = np.diag([1.0, 1.0, 1.0, -1.0]).astype(np.complex128)
_SB_XX4 = np.kron(_SB_X2, _SB_X2)


def _sb_diss_local(op: np.ndarray) -> np.ndarray:
    d = op.shape[0]
    eye = np.eye(d, dtype=np.complex128)
    cdc = op.conj().T @ op
    return np.kron(op.conj(), op) - 0.5 * (np.kron(eye, cdc) + np.kron(cdc.T, eye))


_SB_DA_C = _sb_diss_local(_SB_AC)
_SB_DAD_C = _sb_diss_local(_SB_ADC)
_SB_DSM_Q = _sb_diss_local(_SB_SM)
_SB_DSZ_Q = _sb_diss_local(_SB_Z2)

_SB_P1_DICT = {"I": _SB_I2, "X": _SB_X2, "Y": _SB_Y2, "Z": _SB_Z2}
_SB_PAULI_16_NAMES = [a + b for a in "IXYZ" for b in "IXYZ"]
_SB_BELL_BASIS_16: dict[str, np.ndarray] = {}
for _p_name in _SB_PAULI_16_NAMES:
    _p_op = np.kron(_SB_P1_DICT[_p_name[0]], _SB_P1_DICT[_p_name[1]])
    _b_vec = np.zeros(16, dtype=np.complex128)
    for _k in range(4):
        _ek = np.zeros(4, dtype=np.complex128)
        _ek[_k] = 1.0
        _b_vec += 0.5 * np.kron(_ek, _p_op @ _ek)
    _SB_BELL_BASIS_16[_p_name] = _b_vec

_SB_B_EMB = np.zeros((4 * _SB_NC, 4), dtype=np.complex128)
for _q in range(4):
    _SB_B_EMB[_q * _SB_NC, _q] = 1.0
_SB_RHO_INIT_16 = np.array(
    [np.outer(_SB_B_EMB[:, i], _SB_B_EMB[:, j].conj()) for i in range(4) for j in range(4)],
    dtype=np.complex128,
)


def _sb_generate_ou_1f_ghz(
    n_traj: int,
    dts_us: list[float],
    s0_uev: float,
    alpha: float = 1.0,
    f_ir_hz: float = 1.0,
    f_uv_hz: float = 1.0e8,
    n_fluct: int = 40,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Exact Gillespie (1996) step-averaged multi-OU 1/f^alpha trajectories (GHz) with antithetic pairing.

    Computes the exact joint Gaussian distribution of (x_m(t+dt), (1/dt) int_t^{t+dt} x_m(s) ds)
    across Exp137's [1 Hz, 100 MHz] band (zero high-frequency step-size aliasing).
    """
    n_steps = len(dts_us)
    if s0_uev <= 0.0:
        return np.zeros((1, n_steps), dtype=np.float64)
    if rng is None:
        rng = np.random.default_rng()
    n_half = max(1, int(n_traj) // 2)
    f_m = np.geomspace(f_ir_hz, f_uv_hz, n_fluct)
    dlnf = math.log(f_uv_hz / f_ir_hz) / max(n_fluct - 1, 1)
    c_alpha = math.sin(0.5 * math.pi * float(np.clip(alpha, 0.25, 1.75)))
    sig_m_ghz = (
        float(s0_uev)
        * np.sqrt(c_alpha * (f_m ** (1.0 - alpha)) * dlnf)
        * _GHZ_PER_UEV
    )
    sig2 = sig_m_ghz * sig_m_ghz
    gam = 2.0 * math.pi * f_m

    x = rng.normal(0.0, 1.0, size=(n_half, n_fluct)) * sig_m_ghz[None, :]
    xbar = np.empty((n_half, n_steps), dtype=np.float64)
    for k in range(n_steps):
        dt_s = float(dts_us[k]) * 1e-6
        if dt_s <= 0.0:
            xbar[:, k] = np.sum(x, axis=1)
            continue
        gdt = gam * dt_s
        e1 = np.exp(-gdt)
        e2 = np.exp(-2.0 * gdt)
        small = gdt < 1e-4
        safe_g = np.where(small, 1.0, gdt)

        c_xi = np.where(small, 1.0 - 0.5 * gdt + (gdt ** 2) / 6.0, (1.0 - e1) / safe_g)
        var_x = sig2 * np.where(
            small,
            2.0 * gdt - 2.0 * (gdt ** 2) + (4.0 / 3.0) * (gdt ** 3),
            1.0 - e2,
        )
        var_i = sig2 * np.where(
            small,
            (2.0 / 3.0) * gdt - 0.5 * (gdt ** 2) + (7.0 / 30.0) * (gdt ** 3),
            (2.0 * gdt - 3.0 + 4.0 * e1 - e2) / (safe_g * safe_g),
        )
        cov_xi = sig2 * np.where(
            small,
            gdt - (gdt ** 2) + (7.0 / 12.0) * (gdt ** 3),
            ((1.0 - e1) ** 2) / safe_g,
        )

        l11 = np.sqrt(np.maximum(var_x, 0.0))
        l21 = np.where(l11 > 1e-30, cov_xi / np.where(l11 > 1e-30, l11, 1.0), 0.0)
        l22 = np.sqrt(np.maximum(var_i - l21 * l21, 0.0))

        z1 = rng.normal(0.0, 1.0, size=(n_half, n_fluct))
        z2 = rng.normal(0.0, 1.0, size=(n_half, n_fluct))
        i_avg = x * c_xi[None, :] + l21[None, :] * z1 + l22[None, :] * z2
        x = x * e1[None, :] + l11[None, :] * z1
        xbar[:, k] = np.sum(i_avg, axis=1)
    return np.vstack([xbar, -xbar])


def _sb_su2_pi_batch(dw: np.ndarray, axis: str, w_pi: float, dt_us: float) -> np.ndarray:
    """Exact SU(2) propagator exp(-i * 0.5 * (w_pi * sigma_axis + dw * Z) * dt) over trajectories."""
    hx = w_pi if axis == "X" else 0.0
    hy = w_pi if axis == "Y" else 0.0
    hz = dw
    norm = np.sqrt(hx * hx + hy * hy + hz * hz)
    ang = 0.5 * norm * dt_us
    c = np.cos(ang)
    safe_n = np.where(norm > 1e-15, norm, 1.0)
    s = np.where(norm > 1e-15, np.sin(ang) / safe_n, 0.5 * dt_us)
    U = np.empty((dw.size, 2, 2), dtype=np.complex128)
    U[:, 0, 0] = c - 1j * s * hz
    U[:, 0, 1] = -1j * s * (hx - 1j * hy)
    U[:, 1, 0] = -1j * s * (hx + 1j * hy)
    U[:, 1, 1] = c + 1j * s * hz
    return U


def _sb_kron_2q_superop(dq1: np.ndarray, dq2: np.ndarray) -> np.ndarray:
    return (
        np.tensordot(dq1.reshape(2, 2, 2, 2), dq2.reshape(2, 2, 2, 2), axes=0)
        .transpose(0, 4, 1, 5, 2, 6, 3, 7)
        .reshape(16, 16)
    )


def _sb_apply_diss_16d(rho: np.ndarray, dq16: np.ndarray, dc16: np.ndarray) -> np.ndarray:
    """Exact factored Lindblad dissipator on (M, 16, 16) density matrices (Q1 x Q2 x Cav4)."""
    M = rho.shape[0]
    nc = _SB_NC
    t = rho.reshape(M, 4, nc, 4, nc).transpose(0, 1, 3, 4, 2).reshape(M * 16, nc * nc)
    t = (t @ dc16.T).reshape(M, 4, 4, nc, nc).transpose(0, 1, 4, 2, 3)
    t = t.transpose(0, 2, 4, 3, 1).reshape(M * nc * nc, 16)
    t = (t @ dq16.T).reshape(M, nc, nc, 4, 4).transpose(0, 4, 1, 3, 2)
    return t.reshape(M, 4 * nc, 4 * nc)


def _sb_apply_dq_only_16d(rho: np.ndarray, dq16: np.ndarray) -> np.ndarray:
    """Apply 2-qubit Lindblad superoperator dq16 (16x16) leaving cavity indices untouched."""
    M = rho.shape[0]
    nc = _SB_NC
    t = rho.reshape(M, 4, nc, 4, nc).transpose(0, 2, 4, 3, 1).reshape(M * nc * nc, 16)
    t = (t @ dq16.T).reshape(M, nc, nc, 4, 4).transpose(0, 4, 1, 3, 2)
    return t.reshape(M, 4 * nc, 4 * nc)


def _sb_simulate_echo_bus_choi(
    g_MHz: float,
    detuning_MHz: float,
    kappa_MHz: float,
    t2_electron_us: float,
    s_eps_uev: float,
    echo_pulses: int,
    bare: bool,
    pi_pulse_us: float = 0.015,
    eps_rot: float = 0.002,
    alpha_1f: float = 1.0,
    hop_distance: int = 1,
    n_traj: int = 96,
    seed: int = 13701,
) -> dict[str, Any]:
    """Exact continuous-time 16D (Q1 x Q2 x 4-Fock cavity) Lindblad + Gillespie 1/f^alpha Choi solver.

    Models longitudinal dispersive spin-bus coupling H = Delta a^dag a + g_z (Z1 + Z2)(a + a^dag)
    generating exact geometric CZ phase Phi_ZZ = pi from the bosonic cavity loop, coupled with:
      - exact continuous-time bosonic cavity Liouvillian -i[H_c(Z1+Z2), .] + kappa*(1+n_th) D[a]
        + kappa*n_th D[a^dag] at 20 mK / 5 GHz (zero Trotter error over cavity loops & zero
        double-counting of cavity loss),
      - intrinsic electron T1 relaxation (~1 ms) + Markovian T2 dephasing matching Exp137,
      - exact Gillespie (1996) step-averaged multi-OU 1/f^alpha trajectories over [1 Hz, 100 MHz],
      - finite-duration microwave echo pi-pulses (default 15 ns matching Exp137 t_pi_us=0.015).
    """
    rng = np.random.default_rng(seed)
    g_mhz = max(float(g_MHz), 1e-3)
    delta_mhz = max(float(detuning_MHz), 1e-3)
    kappa_mhz = max(float(kappa_MHz), 0.0)
    t2_us = max(float(t2_electron_us), 1e-3)
    j_mhz = (g_mhz * g_mhz) / delta_mhz
    t_nom_us = 1.0 / (4.0 * max(j_mhz, 1e-6))
    delta_rad = 2.0 * math.pi * delta_mhz
    t_loop_us = 2.0 * math.pi / delta_rad

    if bare:
        fracs = [1.0]
        axes: list[str] = []
        frame = np.eye(4, dtype=np.complex128)
    elif echo_pulses <= 1:
        # Exact Hahn-echoed CZ/2 - (pi_X x pi_X) - CZ/2 with Pauli-frame X1 x X2 tracking
        fracs = [0.5, 0.5]
        axes = ["X"]
        frame = _SB_XX4.copy()
    else:
        n_e = int(echo_pulses)
        # Symmetric CPMG/XY-N schedule: [1/(2N), 1/N, ..., 1/N, 1/(2N)] with alternating X, Y
        fracs = [0.5 / n_e] + [1.0 / n_e] * (n_e - 1) + [0.5 / n_e]
        axes = ["X" if (i % 2 == 0) else "Y" for i in range(n_e)]
        frame = np.eye(4, dtype=np.complex128)
        for ax in axes:
            op1 = -1.0j * _SB_X2 if ax == "X" else -1.0j * _SB_Y2
            frame = np.kron(op1, op1) @ frame

    min_f = min(fracs)
    k_unit = max(1, int(round((t_nom_us * min_f) / t_loop_us)))
    unit_t = k_unit * t_loop_us
    seg_mults = [int(round(f / min_f)) for f in fracs]
    t_bus_us = sum(m * unit_t for m in seg_mults)
    # Exact geometric phase condition: 2 * g_z^2 * t_bus / delta = pi / 4
    g_z = math.sqrt((0.25 * math.pi) * delta_rad / max(2.0 * t_bus_us, 1e-12))

    n_sub = 2
    dt_unit = unit_t / n_sub
    dts_all: list[float] = []
    seg_counts: list[int] = []
    for idx_s, mult in enumerate(seg_mults):
        n_st = mult * n_sub
        seg_counts.append(n_st)
        dts_all.extend([dt_unit] * n_st)
        if idx_s < len(axes):
            dts_all.append(float(pi_pulse_us))
    t_gate_us = float(sum(dts_all))

    # Exact continuous-time 16x16 cavity Lindblad propagator exp(L_{ij} * dt_unit) for each (i, j)
    # Eliminates Strang-splitting cavity-loop resonance aliasing and captures exact photon loss!
    x_th = (_H_PLANCK * 5.0e9) / (_K_BOLTZMANN * 0.020)
    n_th = 0.0 if x_th > 700.0 else 1.0 / (math.exp(x_th) - 1.0)
    kap_rad = 2.0 * math.pi * kappa_mhz
    l_c_diss = kap_rad * (1.0 + n_th) * _SB_DA_C + kap_rad * n_th * _SB_DAD_C
    eye_c = np.eye(_SB_NC, dtype=np.complex128)
    z_sums = (2.0, 0.0, 0.0, -2.0)
    h_by_z = {zs: delta_rad * _SB_NC_OP + (g_z * zs) * _SB_XC_OP for zs in (2.0, 0.0, -2.0)}
    exp_cache: dict[tuple[float, float], np.ndarray] = {}
    p_cav_4x4 = np.empty((4, 4, _SB_NC * _SB_NC, _SB_NC * _SB_NC), dtype=np.complex128)
    for i, zi in enumerate(z_sums):
        for j, zj in enumerate(z_sums):
            key = (zi, zj)
            if key not in exp_cache:
                l_ij = -1.0j * (np.kron(eye_c, h_by_z[zi]) - np.kron(h_by_z[zj].T, eye_c)) + l_c_diss
                exp_cache[key] = _scipy_expm(l_ij * dt_unit)
            p_cav_4x4[i, j] = exp_cache[key]

    # Intrinsic qubit relaxation (T1 >= 1 ms, matching Exp137) + T2 dephasing (no double-counted kappa!)
    gam_1 = 0.0 if t2_us > 1.0e7 else 1.0 / max(2.0 * t2_us, 1.0e3)
    gam_phi = max(0.0, 0.5 / t2_us - 0.25 * gam_1)
    l_q = gam_1 * _SB_DSM_Q + gam_phi * _SB_DSZ_Q

    dq_sub = _sb_kron_2q_superop(_scipy_expm(l_q * (0.5 * dt_unit)), _scipy_expm(l_q * (0.5 * dt_unit)))
    dq_pi = _sb_kron_2q_superop(_scipy_expm(l_q * (0.5 * pi_pulse_us)), _scipy_expm(l_q * (0.5 * pi_pulse_us)))
    dc_pi = _scipy_expm(l_c_diss * (0.5 * pi_pulse_us))

    # Colored multi-OU 1/f^alpha charge noise (Exp131/137 hybridized spin-charge slope D1)
    d1_ghz_per_ghz = 7.5e-4
    de1 = _sb_generate_ou_1f_ghz(n_traj, dts_all, max(0.0, float(s_eps_uev)), alpha=alpha_1f, rng=rng)
    de2 = _sb_generate_ou_1f_ghz(n_traj, dts_all, max(0.0, float(s_eps_uev)), alpha=alpha_1f, rng=rng)
    n_eff = de1.shape[0]
    dw1 = 2.0 * math.pi * 1.0e3 * (d1_ghz_per_ghz * de1)
    dw2 = 2.0 * math.pi * 1.0e3 * (d1_ghz_per_ghz * de2)

    z1_ev = np.array([1.0, 1.0, -1.0, -1.0], dtype=np.float64)
    z2_ev = np.array([1.0, -1.0, 1.0, -1.0], dtype=np.float64)

    rho = np.broadcast_to(_SB_RHO_INIT_16, (n_eff, 16, 16, 16)).copy()
    w_pi = (math.pi * (1.0 + float(eps_rot))) / max(float(pi_pulse_us), 1e-6)
    step_i = 0
    for idx_s, n_st in enumerate(seg_counts):
        for _ in range(n_st):
            rho = _sb_apply_dq_only_16d(rho.reshape(n_eff * 16, 16, 16), dq_sub).reshape(n_eff, 16, 16, 16)
            ph4 = np.exp(-0.5j * dt_unit * (dw1[:, step_i, None] * z1_ev[None, :] + dw2[:, step_i, None] * z2_ev[None, :]))
            ph_ij = ph4[:, None, :, None] * ph4.conj()[:, None, None, :]
            rt = rho.reshape(n_eff, 16, 4, _SB_NC, 4, _SB_NC).transpose(0, 1, 2, 4, 5, 3).reshape(n_eff, 16, 4, 4, _SB_NC * _SB_NC)
            rt = np.einsum("ijab,nkijb->nkija", p_cav_4x4, rt) * ph_ij[:, :, :, :, None]
            rho = rt.reshape(n_eff, 16, 4, 4, _SB_NC, _SB_NC).transpose(0, 1, 2, 5, 3, 4).reshape(n_eff, 16, 16, 16)
            rho = _sb_apply_dq_only_16d(rho.reshape(n_eff * 16, 16, 16), dq_sub).reshape(n_eff, 16, 16, 16)
            step_i += 1
        if idx_s < len(axes):
            ax = axes[idx_s]
            rho = _sb_apply_diss_16d(rho.reshape(n_eff * 16, 16, 16), dq_pi, dc_pi).reshape(n_eff, 16, 16, 16)
            u1 = _sb_su2_pi_batch(dw1[:, step_i], ax, w_pi, float(pi_pulse_us))
            u2 = _sb_su2_pi_batch(dw2[:, step_i], ax, w_pi, float(pi_pulse_us))
            u12 = np.einsum("nij,nkl->nikjl", u1, u2).reshape(n_eff, 4, 4)
            rt = rho.reshape(n_eff, 16, 4, _SB_NC, 4, _SB_NC)
            rt = np.einsum("nab,nkbcde->nkacde", u12, rt)
            rt = np.einsum("nkabcd,nec->nkabed", rt, u12.conj())
            rho = rt.reshape(n_eff, 16, 16, 16)
            rho = _sb_apply_diss_16d(rho.reshape(n_eff * 16, 16, 16), dq_pi, dc_pi).reshape(n_eff, 16, 16, 16)
            step_i += 1

    rho_avg = np.mean(rho, axis=0)  # (16, 16, 16)

    # CPTP audit & cavity leakage on the 4 physical diagonal computational states
    max_tr_err = 0.0
    max_herm_err = 0.0
    min_eig = 1.0
    leak_list = []
    for k in range(4):
        rk = rho_avg[k * 4 + k]
        max_tr_err = max(max_tr_err, abs(complex(np.trace(rk)) - 1.0))
        max_herm_err = max(max_herm_err, float(np.linalg.norm(rk - rk.conj().T)))
        min_eig = min(min_eig, float(np.min(np.linalg.eigvalsh(0.5 * (rk + rk.conj().T)))))
        p_cav0 = float(np.real(np.trace(rk[::_SB_NC, ::_SB_NC])))
        leak_list.append(max(0.0, 1.0 - p_cav0))
    p_leak = float(np.mean(leak_list))

    # Partial trace over 4-Fock cavity -> reduced 2-qubit channel E_q(|i><j|)
    eq = np.einsum("bijik->bjk", rho_avg.reshape(16, 4, _SB_NC, 4, _SB_NC).transpose(0, 2, 1, 4, 3))
    eq_f = frame.conj().T @ eq @ frame

    # Extract deterministic single-qubit virtual-Z calibration phases & verify entangling phase
    phases = np.angle(np.array([eq_f[k][0, k] for k in range(4)]))
    ent_phase_over_pi = float(((phases[0] + phases[3] - phases[1] - phases[2]) % (2.0 * math.pi)) / math.pi)
    u_loc = np.diag([
        1.0,
        np.exp(1.0j * (phases[1] - phases[0])),
        np.exp(1.0j * (phases[2] - phases[0])),
        np.exp(1.0j * (phases[1] + phases[2] - 2.0 * phases[0])),
    ])
    u_tgt = u_loc.conj() @ _SB_CZ4

    # Build 16x16 error channel superoperator S_err: vec(Lambda(rho)) = S_err @ vec(rho)
    # and compose exactly hop_distance times for multi-hop bus routes!
    s_err = np.zeros((16, 16), dtype=np.complex128)
    for i in range(4):
        for j in range(4):
            lam_ij = u_tgt.conj().T @ eq_f[i * 4 + j] @ u_tgt
            s_err[:, i * 4 + j] = lam_ij.reshape(16)
    hops = max(1, int(hop_distance))
    s_tot = np.linalg.matrix_power(s_err, hops) if hops > 1 else s_err

    # Reconstruct exact 16x16 Choi matrix J_Lambda after hop_distance hops
    j_choi = np.zeros((16, 16), dtype=np.complex128)
    for i in range(4):
        for j in range(4):
            lam_ij = s_tot[:, i * 4 + j].reshape(4, 4)
            j_choi[i * 4 : (i + 1) * 4, j * 4 : (j + 1) * 4] = 0.25 * lam_ij

    pauli_16: dict[str, float] = {}
    for nm in _SB_PAULI_16_NAMES:
        v = _SB_BELL_BASIS_16[nm]
        pauli_16[nm] = float(np.real(v.conj() @ (j_choi @ v)))

    p_i = pauli_16["II"]
    p_x = pauli_16["IX"] + pauli_16["XI"] + pauli_16["XX"]
    p_y = pauli_16["IY"] + pauli_16["YI"] + pauli_16["YY"] + pauli_16["XY"] + pauli_16["YX"]
    p_z = pauli_16["IZ"] + pauli_16["ZI"] + pauli_16["XZ"] + pauli_16["ZX"] + pauli_16["YZ"] + pauli_16["ZY"]
    p_zz = pauli_16["ZZ"]
    f_ent = float(p_i)
    f_avg = float((4.0 * f_ent + 1.0) / 5.0)

    # Exact Bell-state fidelity: Lambda(|++><++|) vs |++><++| (unitarily equivalent to CZ|++>!)
    rho_pp = np.full((4, 4), 0.25, dtype=np.complex128)
    rho_pp_out = (s_tot @ rho_pp.reshape(16)).reshape(4, 4)
    psi_pp = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.complex128)
    f_bell = float(np.real(psi_pp.conj() @ (rho_pp_out @ psi_pp)))

    return {
        "F_ent": f_ent,
        "F_avg": f_avg,
        "F_Bell": f_bell,
        "t_gate_us": float(t_gate_us * hops),
        "ent_phase_over_pi": ent_phase_over_pi,
        "p_I": float(p_i),
        "p_X": float(p_x),
        "p_Y": float(p_y),
        "p_Z": float(p_z),
        "p_ZZ": float(p_zz),
        "p_leak": float(1.0 - (1.0 - p_leak) ** hops),
        "p_total_err": float(1.0 - p_i),
        "pauli_sum": float(sum(pauli_16.values())),
        "cptp_audit": {
            "max_trace_err": float(max_tr_err),
            "max_herm_err": float(max_herm_err),
            "min_eigval": float(min_eig),
        },
    }


# ---------------------------------------------------------------------------
# 2. Exact GF(2) Bivariate Bicycle qLDPC Algebra & Vectorized BP-OSD Decoder
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _BBCodeSpec:
    canonical_name: str
    l: int
    m: int
    d_lit: int
    A_terms: tuple[tuple[int, int], tuple[int, int], tuple[int, int]]
    B_terms: tuple[tuple[int, int], tuple[int, int], tuple[int, int]]


_BB_CODE_CATALOG: dict[str, _BBCodeSpec] = {
    "BB_72_12_6": _BBCodeSpec(
        canonical_name="BB_72_12_6", l=6, m=6, d_lit=6,
        A_terms=((3, 0), (0, 1), (0, 2)),
        B_terms=((0, 3), (1, 0), (2, 0)),
    ),
    "BB_90_8_10": _BBCodeSpec(
        canonical_name="BB_90_8_10", l=15, m=3, d_lit=10,
        A_terms=((9, 0), (0, 1), (0, 2)),
        B_terms=((0, 0), (2, 0), (7, 0)),
    ),
    "BB_144_12_12": _BBCodeSpec(
        canonical_name="BB_144_12_12", l=12, m=6, d_lit=12,
        A_terms=((3, 0), (0, 1), (0, 2)),
        B_terms=((0, 3), (1, 0), (2, 0)),
    ),
    "BB_288_12_18": _BBCodeSpec(
        canonical_name="BB_288_12_18", l=12, m=12, d_lit=18,
        A_terms=((3, 0), (0, 2), (0, 7)),
        B_terms=((0, 3), (1, 0), (2, 0)),
    ),
}


def _gf2_rref(mat: np.ndarray) -> tuple[np.ndarray, list[int]]:
    """Compute Reduced Row Echelon Form over GF(2) returning (rref, pivot_cols)."""
    M = (np.asarray(mat, dtype=np.uint8) & 1).copy()
    nrows, ncols = M.shape
    pivots: list[int] = []
    row = 0
    for col in range(ncols):
        if row >= nrows:
            break
        nz = np.flatnonzero(M[row:, col])
        if nz.size == 0:
            continue
        piv = row + int(nz[0])
        if piv != row:
            M[[row, piv]] = M[[piv, row]]
        mask = M[:, col].astype(bool)
        mask[row] = False
        if np.any(mask):
            M[mask] ^= M[row]
        pivots.append(col)
        row += 1
    return M, pivots


def _gf2_nullspace(mat: np.ndarray) -> np.ndarray:
    """Return basis rows of ker(mat) over GF(2)."""
    R, pivots = _gf2_rref(mat)
    ncols = R.shape[1]
    piv_set = set(pivots)
    free_cols = [c for c in range(ncols) if c not in piv_set]
    basis = np.zeros((len(free_cols), ncols), dtype=np.uint8)
    for k, fc in enumerate(free_cols):
        basis[k, fc] = 1
        for r_idx, pc in enumerate(pivots):
            if R[r_idx, fc]:
                basis[k, pc] = 1
    return basis


def _gf2_rowspace_complement(ker_basis: np.ndarray, row_mat: np.ndarray) -> np.ndarray:
    """Fast incremental GF(2) pivot reduction extracting ker_basis modulo rowspace(row_mat)."""
    R_row, piv_row = _gf2_rref(row_mat)
    basis_by_piv: dict[int, np.ndarray] = {
        pc: R_row[idx].copy() for idx, pc in enumerate(piv_row)
    }
    selected: list[np.ndarray] = []
    for v in ker_basis:
        rem = v.copy()
        while True:
            nz = np.flatnonzero(rem)
            if nz.size == 0:
                break
            lead = int(nz[0])
            if lead in basis_by_piv:
                rem ^= basis_by_piv[lead]
            else:
                basis_by_piv[lead] = rem
                selected.append(v.copy())
                break
    return np.array(selected, dtype=np.uint8)


def _gf2_symplectic_logical_basis(H_X: np.ndarray, H_Z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Construct CSS logical operators L_X, L_Z satisfying H_Z L_X^T=0, H_X L_Z^T=0, L_X L_Z^T=I_k (mod 2)."""
    ker_Z = _gf2_nullspace(H_Z)
    ker_X = _gf2_nullspace(H_X)
    L_X = _gf2_rowspace_complement(ker_Z, H_X)
    L_Z = _gf2_rowspace_complement(ker_X, H_Z)
    k = L_X.shape[0]
    if k != L_Z.shape[0]:
        raise RuntimeError(f"CSS logical count mismatch: {k} vs {L_Z.shape[0]}")
    for i in range(k):
        found = -1
        for j in range(i, k):
            if int(np.dot(L_X[i], L_Z[j]) & 1) == 1:
                found = j
                break
        if found < 0:
            raise RuntimeError(f"Symplectic pairing failed at logical index {i}")
        if found != i:
            L_Z[[i, found]] = L_Z[[found, i]]
        for j in range(k):
            if j != i and int(np.dot(L_X[j], L_Z[i]) & 1) == 1:
                L_X[j] ^= L_X[i]
            if j != i and int(np.dot(L_X[i], L_Z[j]) & 1) == 1:
                L_Z[j] ^= L_Z[i]
    return L_X, L_Z


def _cyclic_shift_gf2(size: int, power: int) -> np.ndarray:
    S = np.zeros((size, size), dtype=np.uint8)
    p = power % size
    for i in range(size):
        S[i, (i + p) % size] = 1
    return S


def _build_tanner_tables(H: np.ndarray) -> dict[str, Any]:
    """Precompute sparse CSR & padded edge tables for fast vectorized Min-Sum BP."""
    M, N = H.shape
    H_csr = _csr_matrix(H)
    rows, cols = np.nonzero(H)
    n_edges = int(rows.size)
    row_counts = np.bincount(rows, minlength=M)
    col_counts = np.bincount(cols, minlength=N)
    dc_max = int(np.max(row_counts)) if M > 0 else 1
    dv_max = int(np.max(col_counts)) if N > 0 else 1

    c_edges = np.full((M, dc_max), n_edges, dtype=np.int32)
    c_mask = np.zeros((M, dc_max), dtype=bool)
    c_pos = np.zeros(M, dtype=np.int32)
    for e_id, c in enumerate(rows):
        k = c_pos[c]
        c_edges[c, k] = e_id
        c_mask[c, k] = True
        c_pos[c] = k + 1

    v_edges = np.full((N, dv_max), n_edges, dtype=np.int32)
    v_pos = np.zeros(N, dtype=np.int32)
    for e_id, v in enumerate(cols):
        k = v_pos[v]
        v_edges[v, k] = e_id
        v_pos[v] = k + 1

    return {
        "H": H,
        "H_csr": H_csr,
        "M": M,
        "N": N,
        "n_edges": n_edges,
        "edge_v": cols.astype(np.int32),
        "c_edges": c_edges,
        "c_mask": c_mask,
        "v_edges": v_edges,
    }


@lru_cache(maxsize=8)
def _get_bb_code_algebra(code_key: str) -> dict[str, Any]:
    """Build and cache exact GF(2) BB CSS matrices (H_X, H_Z, L_X, L_Z) & Tanner tables."""
    spec = _BB_CODE_CATALOG[code_key]
    l, m = spec.l, spec.m
    A = np.zeros((l * m, l * m), dtype=np.uint8)
    for px, py in spec.A_terms:
        A ^= np.kron(_cyclic_shift_gf2(l, px), _cyclic_shift_gf2(m, py)).astype(np.uint8)
    B = np.zeros((l * m, l * m), dtype=np.uint8)
    for px, py in spec.B_terms:
        B ^= np.kron(_cyclic_shift_gf2(l, px), _cyclic_shift_gf2(m, py)).astype(np.uint8)

    H_X = np.hstack([A, B]).astype(np.uint8)
    H_Z = np.hstack([B.T, A.T]).astype(np.uint8)
    n_data = 2 * l * m
    comm_ok = bool(np.all(((H_X @ H_Z.T) & 1) == 0))
    _, piv_x = _gf2_rref(H_X)
    _, piv_z = _gf2_rref(H_Z)
    rank_x, rank_z = len(piv_x), len(piv_z)
    k_log = n_data - rank_x - rank_z
    L_X, L_Z = _gf2_symplectic_logical_basis(H_X, H_Z)
    symp_ok = bool(
        np.array_equal((L_X @ L_Z.T) & 1, np.eye(k_log, dtype=np.uint8))
        and np.all(((H_Z @ L_X.T) & 1) == 0)
        and np.all(((H_X @ L_Z.T) & 1) == 0)
    )
    return {
        "code_name": spec.canonical_name,
        "n_data": n_data,
        "n_ancilla": n_data,
        "k": k_log,
        "distance": spec.d_lit,
        "check_weight": int(np.max(np.sum(H_Z, axis=1))),
        "rank_X": rank_x,
        "rank_Z": rank_z,
        "commutativity_verified": comm_ok,
        "symplectic_verified": symp_ok,
        "H_X": H_X,
        "H_Z": H_Z,
        "L_X": L_X,
        "L_Z": L_Z,
        "tanner_X": _build_tanner_tables(H_X),
        "tanner_Z": _build_tanner_tables(H_Z),
    }


def _resolve_bb_code_key(code_name: str, n_data: int) -> str:
    """Map cell code name or alias to canonical BB code spec key."""
    norm = str(code_name).strip().upper().replace("[", "").replace("]", "").replace(",", "_").replace(" ", "")
    if norm in _BB_CODE_CATALOG:
        return norm
    for key in _BB_CODE_CATALOG:
        if key in norm:
            return key
    if "288" in norm or int(n_data) == 288:
        return "BB_288_12_18"
    if "72" in norm or int(n_data) == 72:
        return "BB_72_12_6"
    if "90" in norm or int(n_data) == 90:
        return "BB_90_8_10"
    return "BB_144_12_12"


def _bp_osd_decode_batch(
    tanner: dict[str, Any],
    syndromes: np.ndarray,
    p_prior: float,
    bp_max_iter: int = 35,
    ms_alpha: float = 0.625,
    use_osd: bool = True,
    osd_order: int = 1,
    osd_lambda: int = 16,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Pure-NumPy vectorized Normalized Min-Sum BP + bit-packed GF(2) Gauss-Jordan OSD decoder."""
    H = tanner["H"]
    H_csr = tanner["H_csr"]
    M, N = tanner["M"], tanner["N"]
    n_edges = tanner["n_edges"]
    edge_v = tanner["edge_v"]
    c_edges = tanner["c_edges"]
    c_mask = tanner["c_mask"]
    v_edges = tanner["v_edges"]

    p_eff = float(np.clip(p_prior, 1e-9, 0.499999))
    llr = np.full(N, math.log((1.0 - p_eff) / p_eff), dtype=np.float64)

    S = np.asarray(syndromes, dtype=np.uint8) & 1
    B = S.shape[0]
    e_hat = np.zeros((B, N), dtype=np.uint8)
    L_post = np.broadcast_to(llr[None, :], (B, N)).copy()

    nz_s = np.any(S != 0, axis=1)
    converged = ~nz_s
    if not np.any(nz_s):
        return e_hat, converged, 0

    act_idx = np.flatnonzero(nz_s)
    Ba = act_idx.size
    S_act = S[act_idx]
    s_sign = np.where(S_act == 1, -1.0, 1.0)

    q_msg = np.zeros((Ba, n_edges + 1), dtype=np.float64)
    q_msg[:, :n_edges] = llr[edge_v][None, :]
    active = np.ones(Ba, dtype=bool)
    L_act = np.broadcast_to(llr[None, :], (Ba, N)).copy()
    e_act = np.zeros((Ba, N), dtype=np.uint8)

    for _ in range(bp_max_iter):
        a_loc = np.flatnonzero(active)
        if a_loc.size == 0:
            break
        q_c = q_msg[a_loc][:, c_edges]
        abs_q = np.abs(q_c)
        abs_q[:, ~c_mask] = 1e9
        idx_min1 = np.argmin(abs_q, axis=2)
        b_ar = np.arange(a_loc.size)[:, None]
        m_ar = np.arange(M)[None, :]
        min1 = abs_q[b_ar, m_ar, idx_min1]
        abs_q_copy = abs_q.copy()
        abs_q_copy[b_ar, m_ar, idx_min1] = 1e9
        min2 = np.min(abs_q_copy, axis=2)

        sgn_q = np.where(q_c < 0.0, -1.0, 1.0)
        sgn_q[:, ~c_mask] = 1.0
        tot_sgn = s_sign[a_loc] * np.prod(sgn_q, axis=2)

        mag_out = np.broadcast_to(min1[:, :, None], q_c.shape).copy()
        mag_out[b_ar, m_ar, idx_min1] = min2
        out_c = ms_alpha * (tot_sgn[:, :, None] * sgn_q) * mag_out

        m_cur = np.zeros((a_loc.size, n_edges + 1), dtype=np.float64)
        m_cur[:, c_edges[c_mask]] = out_c[:, c_mask]

        sum_m = np.sum(m_cur[:, v_edges], axis=2)
        L_cur = llr[None, :] + sum_m
        L_act[a_loc] = L_cur
        hard = (L_cur < 0.0).astype(np.uint8)
        e_act[a_loc] = hard

        syn_chk = (hard @ H_csr.T) & 1
        ok = np.all(syn_chk == S_act[a_loc], axis=1)
        if np.any(ok):
            active[a_loc[ok]] = False
            if not np.any(active):
                break
        still_mask = ~ok
        if np.any(still_mask):
            s_loc = a_loc[still_mask]
            q_next = np.clip(L_cur[still_mask][:, edge_v] - m_cur[still_mask, :n_edges], -40.0, 40.0)
            q_msg[s_loc, :n_edges] = q_next

    e_hat[act_idx] = e_act
    L_post[act_idx] = L_act
    converged[act_idx] = ~active

    n_osd = 0
    if use_osd:
        fail_idx = np.flatnonzero(~converged)
        n_osd = int(fail_idx.size)
        for idx in fail_idx:
            s_vec = S[idx]
            col_order = np.argsort(L_post[idx], kind="mergesort")
            H_ord = H[:, col_order]
            n_w = (N + 1 + 63) // 64
            aug_bits = np.zeros((M, n_w * 64), dtype=np.uint8)
            aug_bits[:, :N] = H_ord
            aug_bits[:, N] = s_vec
            mat = np.packbits(aug_bits, axis=1, bitorder="little").view(np.uint64).copy()

            piv_cols: list[int] = []
            non_piv: list[int] = []
            row = 0
            for j in range(N):
                if row >= M:
                    non_piv.append(j)
                    continue
                w_idx = j >> 6
                b_mask = np.uint64(1) << np.uint64(j & 63)
                nz = np.flatnonzero(mat[row:, w_idx] & b_mask)
                if nz.size == 0:
                    non_piv.append(j)
                    continue
                piv_r = row + int(nz[0])
                if piv_r != row:
                    mat[[row, piv_r]] = mat[[piv_r, row]]
                elim = (mat[:, w_idx] & b_mask) != 0
                elim[row] = False
                if np.any(elim):
                    mat[elim] ^= mat[row]
                piv_cols.append(j)
                row += 1

            s_w = N >> 6
            s_bit = np.uint64(1) << np.uint64(N & 63)
            e_S0 = ((mat[:row, s_w] & s_bit) != 0).astype(np.uint8)
            piv_orig = col_order[piv_cols]
            llr_S = llr[piv_orig]
            best_cost = float(np.dot(e_S0, llr_S))
            best_e_S = e_S0
            best_T: tuple[int, ...] = ()

            if osd_order >= 1 and len(non_piv) > 0:
                lam = min(osd_lambda, len(non_piv))
                t_ord = non_piv[:lam]
                t_orig = col_order[t_ord]
                llr_T = llr[t_orig]
                T_vecs = np.zeros((lam, row), dtype=np.uint8)
                for kt, jc in enumerate(t_ord):
                    T_vecs[kt] = ((mat[:row, jc >> 6] & (np.uint64(1) << np.uint64(jc & 63))) != 0).astype(np.uint8)
                cand1 = e_S0[None, :] ^ T_vecs
                costs1 = cand1 @ llr_S + llr_T
                idx1 = int(np.argmin(costs1))
                if float(costs1[idx1]) < best_cost:
                    best_cost = float(costs1[idx1])
                    best_e_S = cand1[idx1].copy()
                    best_T = (int(t_orig[idx1]),)
                if osd_order >= 2 and lam >= 2:
                    iu, iv = np.triu_indices(lam, k=1)
                    cand2 = e_S0[None, :] ^ T_vecs[iu] ^ T_vecs[iv]
                    costs2 = cand2 @ llr_S + llr_T[iu] + llr_T[iv]
                    idx2 = int(np.argmin(costs2))
                    if float(costs2[idx2]) < best_cost:
                        best_cost = float(costs2[idx2])
                        best_e_S = cand2[idx2].copy()
                        best_T = (int(t_orig[iu[idx2]]), int(t_orig[iv[idx2]]))

            e_sol = np.zeros(N, dtype=np.uint8)
            e_sol[piv_orig] = best_e_S
            for tf in best_T:
                e_sol[tf] = 1
            e_hat[idx] = e_sol

    return e_hat, converged, n_osd


class MultiCellProgrammer:
    """CellISA v3.0 multi-cell M4 compiler, wafer router, and cavity-bus verifier."""

    def __init__(
        self,
        b_field_T: float = 1.5,
        pulse_mode: str = "shaped",
        bus_g_MHz: float = 15.0,
        bus_detuning_MHz: float = 150.0,
        bus_kappa_MHz: float = 0.50,
        t2_electron_us: float = 500.0,
    ):
        self.local_programmer = AtomCellProgrammer(b_field_T=b_field_T, pulse_mode=pulse_mode)
        self.b_field_T = float(b_field_T)
        self.pulse_mode = str(pulse_mode)
        self.bus_g_MHz = float(bus_g_MHz)
        self.bus_detuning_MHz = float(bus_detuning_MHz)
        self.bus_kappa_MHz = float(bus_kappa_MHz)
        self.t2_electron_us = float(t2_electron_us)

    def tune_bus(self, cell_a: str, cell_b: str, hop_distance: int = 1) -> BusLinkSpec:
        """Execute CellISA v3.0 ``BUS_TUNE`` returning physical NbTiN dispersive bus specs."""
        return BusLinkSpec(
            cell_a=cell_a,
            cell_b=cell_b,
            g_MHz=self.bus_g_MHz,
            detuning_MHz=self.bus_detuning_MHz,
            kappa_MHz=self.bus_kappa_MHz,
            t2_electron_us=self.t2_electron_us,
            hop_distance=hop_distance,
        )

    def execute_two_cell_bus_cz(
        self,
        cert_a: Certificate,
        cert_b: Certificate,
        hop_distance: int = 1,
        target_nuclear: bool = False,
    ) -> dict[str, Any]:
        """Simulate physical ``BUS_TUNE + BUS_CZ`` preparing a two-cell Bell state across cert_a & cert_b.

        Simulates local bespoke MW/RF pulses on each cell's measured hyperfine spectrum
        coupled with exact 2-qubit cavity-QED dispersive CZ gate + Purcell/T2 decay channel.
        """
        link = self.tune_bus(cert_a.register_id, cert_b.register_id, hop_distance=hop_distance)

        # Compile & verify local single-cell operations on each cell's unique {A_k}
        local_prep = CellProgram(name="local_bus_prep")
        local_prep.add("INIT", qubits=["e", "n0"], state="00")
        local_prep.add("RY", target="e", theta=math.pi / 2.0)
        if target_nuclear:
            local_prep.add("CNOT", control="e", target="n0")
        sched_a, pc_a = self.local_programmer.execute_and_certify(cert_a, local_prep, verify_corners=False)
        sched_b, pc_b = self.local_programmer.execute_and_certify(cert_b, local_prep, verify_corners=False)

        # Joint 2-cell Bell-state preparation via cavity-bus CZ with exact 4x4 Kraus channel:
        # |++> -> CZ_bus -> H_b -> |Phi+> = (|00> + |11>)/sqrt(2)
        h_mat = np.array([[1.0, 1.0], [1.0, -1.0]], dtype=complex) / math.sqrt(2.0)
        id2 = np.eye(2, dtype=complex)
        cz_4 = np.diag([1.0, 1.0, 1.0, -1.0]).astype(complex)
        psi_pp = np.array([0.5, 0.5, 0.5, 0.5], dtype=complex)
        psi_cz = cz_4 @ psi_pp
        rho = np.outer(psi_cz, np.conj(psi_cz))

        # Exact single-qubit Kraus operators for cavity Purcell decay + T2 dephasing per hop
        t_us = link.cz_duration_us
        p_ad = 1.0 - math.exp(-2.0 * math.pi * (0.5 * link.purcell_rate_MHz) * t_us)
        p_z = 0.5 * (1.0 - math.exp(-t_us / max(link.t2_electron_us, 1e-3)))
        k_ad = [
            np.array([[1.0, 0.0], [0.0, math.sqrt(max(1.0 - p_ad, 0.0))]], dtype=complex),
            np.array([[0.0, math.sqrt(max(p_ad, 0.0))], [0.0, 0.0]], dtype=complex),
        ]
        k_deph = [
            math.sqrt(max(1.0 - p_z, 0.0)) * id2,
            math.sqrt(max(p_z, 0.0)) * np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex),
        ]

        def _apply_1q_kraus(r_in: np.ndarray, ops: list[np.ndarray], qubit_idx: int) -> np.ndarray:
            r_out = np.zeros_like(r_in)
            for op in ops:
                full = np.kron(op, id2) if qubit_idx == 0 else np.kron(id2, op)
                r_out += full @ r_in @ full.conj().T
            return r_out

        for _ in range(max(1, int(hop_distance))):
            rho = _apply_1q_kraus(rho, k_ad, 0)
            rho = _apply_1q_kraus(rho, k_ad, 1)
            rho = _apply_1q_kraus(rho, k_deph, 0)
            rho = _apply_1q_kraus(rho, k_deph, 1)

        u_hb = np.kron(id2, h_mat)
        rho_bell = u_hb @ rho @ u_hb.conj().T
        psi_ideal = np.array([1.0, 0.0, 0.0, 1.0], dtype=complex) / math.sqrt(2.0)
        f_bus_kraus = float(np.real(np.vdot(psi_ideal, rho_bell @ psi_ideal)))

        # Combine exact Kraus cavity-bus fidelity with local bespoke RF/MW fidelity
        f_bus = link.cz_fidelity
        f_local = pc_a.nominal_state_fidelity * pc_b.nominal_state_fidelity
        state_fid = float(f_bus_kraus * f_local)

        return {
            "cell_a": cert_a.register_id,
            "cell_b": cert_b.register_id,
            "j_bus_MHz": round(link.j_bus_MHz, 4),
            "cz_duration_us": round(link.cz_duration_us, 4),
            "bus_cz_fidelity": round(f_bus, 6),
            "bus_kraus_bell_fidelity": round(f_bus_kraus, 6),
            "local_fidelity_product": round(f_local, 6),
            "joint_bell_fidelity": round(state_fid, 6),
            "local_pulses": sched_a.pulse_count + sched_b.pulse_count,
            "total_duration_us": round(sched_a.total_duration_us + sched_b.total_duration_us + link.cz_duration_us, 4),
            "hop_distance": hop_distance,
        }

    def execute_routed_multicell_program(
        self,
        wafer_sites: list[WaferSite],
        target_cells: int = 4,
        logical_code: str = "bitflip3_plus_ancilla",
        max_bus_reach: int = 2,
        out_jsonl: str | Path | None = None,
    ) -> tuple[WaferRoutingResult, MultiCellCertificate]:
        """Full CellISA v3.0 flow: WAFER_MAP_ROUTE -> BUS_TUNE -> BUS_CZ -> LOGICAL_ENCODE -> Cert."""
        router = WaferRouter(max_bus_reach=max_bus_reach)
        route = router.route(wafer_sites, target_cells=target_cells)
        if not route.routed:
            raise RuntimeError(
                f"WAFER_MAP_ROUTE failed: only {route.working_sites} working sites "
                f"(needed connected cluster of {target_cells})"
            )

        cert_by_id = {
            s.cell_id: s.certificate
            for s in wafer_sites
            if s.certificate is not None
        }
        routed_certs = [cert_by_id[cid] for cid in route.assigned_cell_ids]

        # Build formal CellISA v3.0 program record (validates all 4 new opcodes!)
        prog = CellProgram(name=f"multicell_{logical_code}")
        prog.add("WAFER_MAP_ROUTE", grid_shape=[route.grid_rows, route.grid_cols], target_cells=target_cells)
        bus_link_records = []
        bus_fids = []
        total_local_pulses = 0
        total_dur_us = 0.0
        for ca, cb, hops in route.bus_edges:
            prog.add("BUS_TUNE", cell_a=ca, cell_b=cb, g_MHz=self.bus_g_MHz, detuning_MHz=self.bus_detuning_MHz)
            prog.add("BUS_CZ", cell_a=ca, cell_b=cb, qubit_a="e", qubit_b="e")
            res_cz = self.execute_two_cell_bus_cz(
                cert_by_id[ca], cert_by_id[cb], hop_distance=hops, target_nuclear=True
            )
            bus_link_records.append(res_cz)
            bus_fids.append(res_cz["bus_cz_fidelity"])
            total_local_pulses += res_cz["local_pulses"]
            total_dur_us += res_cz["total_duration_us"]

        prog.add("LOGICAL_ENCODE", code=logical_code, cells=route.assigned_cell_ids, logical_state="1")

        # Joint distributed GHZ / repetition-code fidelity across the spanning tree of routed cells
        joint_fid = 1.0
        for rec in bus_link_records:
            joint_fid *= rec["joint_bell_fidelity"]

        # 3-cell repetition code logical bit-flip suppression: p_L = 3 p^2 - 2 p^3
        p_phys = max(0.0, 1.0 - float(np.mean(bus_fids)))
        p_logical = float(3.0 * p_phys * p_phys - 2.0 * (p_phys ** 3))

        exp126_info = verify_with_exp126_bridge(routed_certs)
        mcert = MultiCellCertificate(
            isa_version="3.0",
            program_name=prog.name,
            routed_cell_ids=route.assigned_cell_ids,
            routed_coords=[[r, c] for r, c in route.assigned_coords],
            bus_links=bus_link_records,
            logical_code=logical_code,
            local_pulse_count=total_local_pulses,
            bus_cz_count=len(bus_link_records),
            total_duration_us=round(total_dur_us, 4),
            joint_state_fidelity=round(joint_fid, 6),
            min_bus_cz_fidelity=round(min(bus_fids), 6),
            logical_error_rate=round(p_logical, 8),
            exp126_bridge=exp126_info,
            certified=bool(joint_fid >= 0.90 and min(bus_fids) >= 0.94 and exp126_info["all_clear_5kHz_gate"]),
        ).sign()

        if out_jsonl is not None:
            path = Path(out_jsonl)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                f.write(json.dumps(asdict(mcert)) + "\n")
        return route, mcert

    # -----------------------------------------------------------------------
    # CellISA v3.5 — Fault-Tolerant M4 Operations (ECHO_CZ, MUX_READOUT, SYNDROME_CYCLE)
    # -----------------------------------------------------------------------

    def execute_echo_cz(
        self,
        cert_a: Certificate,
        cert_b: Certificate,
        hop_distance: int = 1,
        s_eps_uev: float = 1.0,
        echo_pulses: int = 1,
        pi_pulse_us: float = 0.015,
        alpha_1f: float = 1.0,
        eps_rot: float = 0.002,
        n_traj: int = 96,
        seed: int = 13701,
    ) -> dict[str, Any]:
        """Execute CellISA v3.5 ``ECHO_CZ`` via exact continuous-time 16D Lindblad + Gillespie 1/f Choi evolution.

        Compares bare un-echoed dispersive bus CZ against dynamically echoed CZ (Hahn / CPMG-XY)
        using the exact continuous-time 16x16 bosonic cavity Liouvillian (cavity loss kappa +
        20 mK thermal bath, zero Trotter cavity-loop aliasing, zero double-counted Purcell term),
        intrinsic electron T1/T2 dissipation, exact Gillespie (1996) step-averaged multi-OU
        1/f^alpha charge-noise over Exp137's [1 Hz, 100 MHz] band, and finite microwave echo
        pi-pulses (default 15 ns matching Exp137 ``t_pi_us=0.015``).
        """
        link = self.tune_bus(cert_a.register_id, cert_b.register_id, hop_distance=hop_distance)
        n_echo = max(1, int(echo_pulses))

        bare_res = _sb_simulate_echo_bus_choi(
            g_MHz=link.g_MHz,
            detuning_MHz=link.detuning_MHz,
            kappa_MHz=link.kappa_MHz,
            t2_electron_us=link.t2_electron_us,
            s_eps_uev=float(s_eps_uev),
            echo_pulses=0,
            bare=True,
            pi_pulse_us=float(pi_pulse_us),
            eps_rot=float(eps_rot),
            alpha_1f=float(alpha_1f),
            hop_distance=int(hop_distance),
            n_traj=int(n_traj),
            seed=int(seed),
        )
        echo_res = _sb_simulate_echo_bus_choi(
            g_MHz=link.g_MHz,
            detuning_MHz=link.detuning_MHz,
            kappa_MHz=link.kappa_MHz,
            t2_electron_us=link.t2_electron_us,
            s_eps_uev=float(s_eps_uev),
            echo_pulses=n_echo,
            bare=False,
            pi_pulse_us=float(pi_pulse_us),
            eps_rot=float(eps_rot),
            alpha_1f=float(alpha_1f),
            hop_distance=int(hop_distance),
            n_traj=int(n_traj),
            seed=int(seed),
        )

        f_bare = bare_res["F_Bell"]
        f_echo = echo_res["F_Bell"]
        t_echo = echo_res["t_gate_us"]

        return {
            "cell_a": cert_a.register_id,
            "cell_b": cert_b.register_id,
            "model": "exact_16d_lindblad_gillespie_ou_1f_choi",
            "j_bus_MHz": round(link.j_bus_MHz, 4),
            "cz_duration_us": round(t_echo, 4),
            "bare_cz_bell_fidelity": round(f_bare, 6),
            "echo_cz_bell_fidelity": round(f_echo, 6),
            "echo_fidelity_gain": round(f_echo - f_bare, 6),
            "bare_process_fidelity": round(bare_res["F_ent"], 6),
            "echo_process_fidelity": round(echo_res["F_ent"], 6),
            "bare_avg_gate_fidelity": round(bare_res["F_avg"], 6),
            "echo_avg_gate_fidelity": round(echo_res["F_avg"], 6),
            "echo_entangling_phase_over_pi": round(echo_res["ent_phase_over_pi"], 5),
            "cavity_leakage_prob": round(echo_res["p_leak"], 6),
            "pauli_error_budget": {
                "p_I": round(echo_res["p_I"], 6),
                "p_X": round(echo_res["p_X"], 6),
                "p_Y": round(echo_res["p_Y"], 6),
                "p_Z": round(echo_res["p_Z"], 6),
                "p_ZZ": round(echo_res["p_ZZ"], 6),
                "p_total_err": round(echo_res["p_total_err"], 6),
                "pauli_sum": round(echo_res["pauli_sum"], 8),
            },
            "cptp_audit": echo_res["cptp_audit"],
            "bus_cz_fidelity": round(f_echo, 6),
            "joint_bell_fidelity": round(f_echo, 6),
            "echo_pulses": n_echo,
            "s_eps_uev": float(s_eps_uev),
            "alpha_1f": float(alpha_1f),
            "n_trajectories": int(n_traj),
            "hop_distance": int(hop_distance),
            "local_pulses": 2 * n_echo,
            "total_duration_us": round(t_echo, 4),
        }

    def execute_mux_readout(
        self,
        cell_ids: list[str],
        n_mux: int = 32,
        tau_ro_us: float = 2.0,
        single_shot_fidelity: float = 0.9945,
        crosstalk_error: float = 0.0008,
        *,
        bw_usable_GHz: float = 3.20,
        f_center_GHz: float = 6.0,
        kappa_ro_MHz: float = 2.0,
        g_readout_MHz: float = 12.0,
        detuning_r_MHz: float = 600.0,
        n_bar_target: float = 40.0,
        t1_intrinsic_us: float = 800.0,
        kappa_purcell_MHz: float = 80.0,
        delta_q_purcell_MHz: float = 1_000.0,
        loss_pre_twpa_dB: float = 1.5,
        twpa_gain_dB: float = 20.0,
        twpa_tn_K: float = 0.30,
        twpa_p1db_dBm: float = -98.0,
        loss_twpa_hemt_dB: float = 2.0,
        hemt_tn_K: float = 2.0,
        sigma_fab_MHz: float = 15.0,
        use_purcell_filter: bool = True,
        use_twpa: bool = True,
    ) -> dict[str, Any]:
        """Execute CellISA v3.5 ``MUX_READOUT`` with Exp140 dispersive cavity-QED, Purcell, TWPA & Lorentzian crosstalk physics.

        Note: ``single_shot_fidelity`` and ``crosstalk_error`` are retained in the signature for
        backward API compatibility only; fidelity is computed from first-principles dispersive shift 2*chi,
        Lorentzian lineshape pointer separation, Purcell decay Gamma_P, Friis TWPA/HEMT quantum noise
        cascade, multi-tone TWPA P_1dB backoff & IM3 distortion, adjacent-channel Lorentzian wing leakage,
        NbTiN fabrication scatter collisions, and Gaussian erfc assignment error per channel.
        """
        _ = (single_shot_fidelity, crosstalk_error)
        nm = max(1, int(n_mux))
        tau_us = max(float(tau_ro_us), 1e-3)
        tau_s = tau_us * 1e-6
        inst = CellInstruction(
            opcode="MUX_READOUT",
            args={
                "cells": list(cell_ids),
                "n_mux": nm,
                "tau_ro_us": tau_us,
            },
        )
        n_cells = len(cell_ids)
        n_lines = max(1, int(math.ceil(max(n_cells, 1) / nm)))

        # 1. Dispersive readout shift 2*chi & Lorentzian pointer-state phase separation
        f0_hz = float(f_center_GHz) * 1.0e9
        kappa_ro = max(float(kappa_ro_MHz), 1e-4)
        kappa_rad = 2.0 * math.pi * kappa_ro * 1.0e6
        g_ro = max(float(g_readout_MHz), 1e-4)
        delta_r = max(float(detuning_r_MHz), 1e-3)
        chi_MHz = (g_ro * g_ro) / delta_r
        n_crit = (delta_r / (2.0 * g_ro)) ** 2
        # Exact complex Lorentzian reflection contrast at probe f = f_r between f_r + chi and f_r - chi
        s21_0 = 1.0 - (0.5 * kappa_ro) / (0.5 * kappa_ro - 1.0j * chi_MHz)
        s21_1 = 1.0 - (0.5 * kappa_ro) / (0.5 * kappa_ro + 1.0j * chi_MHz)
        sin2_half_theta = float(0.25 * (abs(s21_0 - s21_1) ** 2))

        # 2. Purcell decay Gamma_P (bare vs Jeffrey et al. PRL 2014 bandpass Purcell filter)
        gamma_p_bare_s = kappa_rad * ((g_ro / delta_r) ** 2)
        purcell_factor = (
            (2.0 * float(delta_q_purcell_MHz) / max(float(kappa_purcell_MHz), 1e-3)) ** 2
            if use_purcell_filter
            else 1.0
        )
        gamma_p_eff_s = gamma_p_bare_s / max(purcell_factor, 1.0)
        t1_purcell_us = 1.0e6 / max(gamma_p_eff_s, 1e-12)
        t1_eff_us = 1.0 / (1.0 / max(float(t1_intrinsic_us), 1e-3) + 1.0 / t1_purcell_us)

        # 3. Friis quantum noise cascade (SQL + pre-TWPA loss + 20 mK TWPA + 4 K HEMT)
        t_sql_K = (_H_PLANCK * f0_hz) / (2.0 * _K_BOLTZMANN)
        eta_in = 10.0 ** (-float(loss_pre_twpa_dB) / 10.0)
        eta_mid = 10.0 ** (-float(loss_twpa_hemt_dB) / 10.0)
        if use_twpa:
            g_twpa = 10.0 ** (float(twpa_gain_dB) / 10.0)
            t_sys_K = (t_sql_K + float(twpa_tn_K)) / eta_in + (float(hemt_tn_K) / eta_mid) / (eta_in * g_twpa)
        else:
            t_sys_K = (t_sql_K + float(hemt_tn_K) / eta_mid) / eta_in
        eta_meas = t_sql_K / max(t_sys_K, 1e-9)

        # 4. Multi-tone TWPA P_1dB PAPR backoff & IM3 intermodulation crosstalk
        df_ch_MHz = (float(bw_usable_GHz) * 1.0e3) / float(nm)
        p_tone_nom_W = 0.5 * float(n_bar_target) * _H_PLANCK * f0_hz * kappa_rad
        papr_dB = 0.0 if nm == 1 else (3.0 + 3.2 * math.log10(float(nm)))
        papr_lin = 10.0 ** (papr_dB / 10.0)
        p_tot_nom_twpa_W = nm * p_tone_nom_W * eta_in
        p_peak_nom_W = p_tot_nom_twpa_W * papr_lin
        p1db_W = 1.0e-3 * (10.0 ** (float(twpa_p1db_dBm) / 10.0))
        p_lin_cap_W = p1db_W * (10.0 ** (-2.0 / 10.0))
        backoff_lin = max(1.0, p_peak_nom_W / p_lin_cap_W) if use_twpa else 1.0
        backoff_dB = 10.0 * math.log10(backoff_lin)
        n_bar_eff = min(float(n_bar_target) / backoff_lin, 0.5 * n_crit)

        ip3_W = p1db_W * (10.0 ** (9.6 / 10.0))
        p_tot_eff_W = p_tot_nom_twpa_W / backoff_lin
        im3_ratio = (
            ((nm * 0.35) ** 2) * ((p_tot_eff_W / nm) / ip3_W) ** 2
            if (use_twpa and nm > 1)
            else 0.0
        )
        im3_noise_penalty = min(0.80, 12.0 * im3_ratio)

        # 5. Per-channel Lorentzian wing leakage, NbTiN collision & Gaussian erfc assignment fidelity
        x_ring = 0.5 * kappa_rad * tau_s
        f_ring = max(0.05, 1.0 - (1.0 - math.exp(-x_ring)) / max(x_ring, 1e-9))
        err_t1 = 0.5 * (1.0 - math.exp(-tau_us / max(t1_eff_us, 1e-6)))
        sigma_pair = math.sqrt(2.0) * max(float(sigma_fab_MHz), 1e-6)

        # Full multiplexed frequency comb on a feedline (centered around f_center_GHz)
        f_lo_MHz = float(f_center_GHz) * 1.0e3 - 0.5 * float(bw_usable_GHz) * 1.0e3
        comb_freqs_MHz = f_lo_MHz + (np.arange(nm, dtype=np.float64) + 0.5) * df_ch_MHz

        def _eval_slot(slot_idx: int) -> dict[str, float]:
            fj = float(comb_freqs_MHz[slot_idx])
            if nm == 1:
                xt_lor = 0.0
                p_coll = 0.0
            else:
                diffs = np.abs(comb_freqs_MHz - fj)
                mask = np.arange(nm) != slot_idx
                # Exact Lorentzian wing power leakage from all other comb channels
                xt_lor = float(np.sum(1.0 / (1.0 + (diffs[mask] / (0.5 * kappa_ro)) ** 2)))
                # Adjacent-neighbor NbTiN fabrication-scatter collision probability
                n_adj = (1 if slot_idx > 0 else 0) + (1 if slot_idx < nm - 1 else 0)
                z_coll = (df_ch_MHz - 3.0 * kappa_ro) / sigma_pair
                p_pair = 0.5 * math.erfc(z_coll / math.sqrt(2.0))
                p_coll = min(0.25, n_adj * p_pair)

            snr2 = (
                4.0 * eta_meas * kappa_rad * n_bar_eff * sin2_half_theta * tau_s * f_ring
            ) / (1.0 + im3_noise_penalty + 4.0 * xt_lor)
            snr = math.sqrt(max(snr2, 0.0))
            err_sep = 0.5 * math.erfc(snr / (2.0 * math.sqrt(2.0)))
            err_xt = 0.5 * xt_lor + 0.5 * p_coll
            f_ch = max(0.5, 1.0 - err_sep - err_t1 - err_xt)
            return {
                "freq_MHz": round(fj, 2),
                "snr": round(snr, 4),
                "err_sep": round(err_sep, 6),
                "err_t1": round(err_t1, 6),
                "lorentz_xt": round(xt_lor, 6),
                "collision_err": round(p_coll, 6),
                "fidelity": round(f_ch, 6),
            }

        # Evaluate active cell slots distributed across the interior of the multiplexed comb
        n_eval = max(n_cells, 1)
        channel_reports: list[dict[str, float]] = []
        f_list: list[float] = []
        snr_list: list[float] = []
        xt_list: list[float] = []
        for idx in range(n_eval):
            # Map active cells into interior multiplexed slots (avoiding artificial edge-only bias for small batches)
            slot = ((idx + (nm // 4)) % nm) if nm >= 4 else (idx % nm)
            rep = _eval_slot(slot)
            channel_reports.append(rep)
            f_list.append(rep["fidelity"])
            snr_list.append(rep["snr"])
            xt_list.append(rep["lorentz_xt"])

        f_per_cell = float(np.mean(f_list))
        f_batch_joint = float(np.prod(f_list)) if n_cells > 0 else f_per_cell

        return {
            "opcode": inst.opcode,
            "model": "exp140_dispersive_lorentzian_purcell_twpa_erfc",
            "n_cells": n_cells,
            "n_mux": nm,
            "feedlines_used": n_lines,
            "parallel_duration_us": round(tau_us, 4),
            "per_cell_readout_fidelity": round(f_per_cell, 6),
            "batch_joint_readout_fidelity": round(f_batch_joint, 6),
            "chi_MHz": round(chi_MHz, 4),
            "n_crit": round(n_crit, 1),
            "sin2_half_theta": round(sin2_half_theta, 5),
            "channel_spacing_MHz": round(df_ch_MHz, 2),
            "purcell_gamma_kHz": round((gamma_p_eff_s / (2.0 * math.pi)) * 1e-3, 4),
            "purcell_protection_factor": round(purcell_factor, 1),
            "t1_eff_us": round(t1_eff_us, 2),
            "t_sys_K": round(t_sys_K, 4),
            "eta_meas": round(eta_meas, 4),
            "twpa_backoff_dB": round(backoff_dB, 2),
            "n_bar_effective": round(n_bar_eff, 2),
            "im3_noise_penalty": round(im3_noise_penalty, 6),
            "mean_snr": round(float(np.mean(snr_list)), 4),
            "mean_lorentzian_xt": round(float(np.mean(xt_list)), 6),
            "err_t1": round(err_t1, 6),
            "sample_channels": channel_reports[:4],
        }

    def execute_syndrome_cycle(
        self,
        wafer_sites: list[WaferSite],
        target_cells: int = 4,
        logical_code: str = "stabilizer_z4_echo_mux",
        n_mux: int = 32,
        tau_ro_us: float = 2.0,
        s_eps_uev: float = 1.0,
        echo_pulses: int = 1,
        readout_fidelity: float = 0.9945,
        crosstalk_error: float = 0.0008,
        rounds: int = 1,
        out_jsonl: str | Path | None = None,
    ) -> tuple[WaferRoutingResult, MultiCellCertificate, dict[str, Any]]:
        """Full CellISA v3.5 fault-tolerant stabilizer cycle:
        WAFER_MAP_ROUTE -> BUS_TUNE -> ECHO_CZ -> MUX_READOUT -> SYNDROME_CYCLE -> Cert (v3.5).
        """
        route = WaferRouter(max_bus_reach=2).route(wafer_sites, target_cells=target_cells)
        if not route.routed:
            raise RuntimeError(f"WAFER_MAP_ROUTE failed for {target_cells} cells")

        cert_by_id = {s.cell_id: s.certificate for s in wafer_sites if s.certificate is not None}
        routed_certs = [cert_by_id[cid] for cid in route.assigned_cell_ids]

        prog = CellProgram(name=f"syndrome_{logical_code}")
        prog.add("WAFER_MAP_ROUTE", grid_shape=[route.grid_rows, route.grid_cols], target_cells=target_cells)

        echo_records: list[dict[str, Any]] = []
        bare_fids: list[float] = []
        echo_fids: list[float] = []
        total_local_pulses = 0
        cycle_gate_us = 0.0
        for ca, cb, hops in route.bus_edges:
            prog.add("BUS_TUNE", cell_a=ca, cell_b=cb, g_MHz=self.bus_g_MHz, detuning_MHz=self.bus_detuning_MHz)
            prog.add("ECHO_CZ", cell_a=ca, cell_b=cb, echo_pulses=echo_pulses, s_eps_uev=s_eps_uev)
            rec = self.execute_echo_cz(
                cert_by_id[ca], cert_by_id[cb], hop_distance=hops, s_eps_uev=s_eps_uev, echo_pulses=echo_pulses
            )
            echo_records.append(rec)
            bare_fids.append(rec["bare_cz_bell_fidelity"])
            echo_fids.append(rec["echo_cz_bell_fidelity"])
            total_local_pulses += rec["local_pulses"]
            cycle_gate_us += rec["total_duration_us"]

        prog.add("MUX_READOUT", cells=route.assigned_cell_ids, n_mux=n_mux, tau_ro_us=tau_ro_us)
        mux_rec = self.execute_mux_readout(
            route.assigned_cell_ids,
            n_mux=n_mux,
            tau_ro_us=tau_ro_us,
            single_shot_fidelity=readout_fidelity,
            crosstalk_error=crosstalk_error,
        )
        prog.add(
            "SYNDROME_CYCLE",
            code=logical_code,
            cells=route.assigned_cell_ids,
            rounds=int(rounds),
            n_mux=int(n_mux),
        )

        # Single-round stabilizer extraction fidelity = product(ECHO_CZ) * ancilla readout fidelity
        f_gates = 1.0
        for f in echo_fids:
            f_gates *= f
        f_round = f_gates * mux_rec["per_cell_readout_fidelity"]
        f_total = f_round ** max(1, int(rounds))
        cycle_us = (cycle_gate_us + mux_rec["parallel_duration_us"]) * max(1, int(rounds))

        p_phys = max(0.0, 1.0 - float(np.mean(echo_fids)))
        p_logical = float(3.0 * p_phys * p_phys - 2.0 * (p_phys ** 3))
        exp126_info = verify_with_exp126_bridge(routed_certs)

        mcert = MultiCellCertificate(
            isa_version="3.5",
            program_name=prog.name,
            routed_cell_ids=route.assigned_cell_ids,
            routed_coords=[[r, c] for r, c in route.assigned_coords],
            bus_links=echo_records,
            logical_code=logical_code,
            local_pulse_count=total_local_pulses * max(1, int(rounds)),
            bus_cz_count=len(echo_records) * max(1, int(rounds)),
            total_duration_us=round(cycle_us, 4),
            joint_state_fidelity=round(f_total, 6),
            min_bus_cz_fidelity=round(min(echo_fids), 6),
            logical_error_rate=round(p_logical, 8),
            exp126_bridge=exp126_info,
            certified=bool(f_total >= 0.90 and min(echo_fids) >= 0.95 and exp126_info["all_clear_5kHz_gate"]),
        ).sign()

        if out_jsonl is not None:
            path = Path(out_jsonl)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                f.write(json.dumps(asdict(mcert)) + "\n")

        syndrome_summary = {
            "isa_version": "3.5",
            "opcodes_used": sorted({inst.opcode for inst in prog.instructions}),
            "total_opcodes_supported": len(VALID_OPCODES),
            "rounds": int(rounds),
            "mean_bare_cz_fidelity": round(float(np.mean(bare_fids)), 6),
            "mean_echo_cz_fidelity": round(float(np.mean(echo_fids)), 6),
            "echo_fidelity_gain": round(float(np.mean(echo_fids) - np.mean(bare_fids)), 6),
            "mux_readout": mux_rec,
            "syndrome_round_fidelity": round(f_round, 6),
            "cycle_duration_us": round(cycle_us, 4),
        }
        return route, mcert, syndrome_summary

    # -----------------------------------------------------------------------
    # CellISA v4.0 — Cloud-QPU, qLDPC & Autonomous Recalibration Opcodes
    # -----------------------------------------------------------------------

    def execute_qram_swap(
        self,
        cert: Certificate,
        qubit_a: str = "e",
        qubit_b: str = "n0",
        seed: int = 2026145,
    ) -> dict[str, Any]:
        """Execute CellISA v4.0 ``QRAM_SWAP`` between electron bus and nuclear memory spin."""
        prog = CellProgram(name="qram_swap_v4")
        prog.add("INIT", qubits=[qubit_a, qubit_b], state="10")
        prog.add("QRAM_SWAP", qubit_a=qubit_a, qubit_b=qubit_b)
        prog.add("MEASURE", qubits=[qubit_a, qubit_b], basis="Z", shots=512)
        sched, pcert = self.local_programmer.execute_and_certify(
            cert, prog, verify_corners=False, seed=seed
        )
        return {
            "opcode": "QRAM_SWAP",
            "isa_version": "4.0",
            "total_opcodes_v4": len(VALID_OPCODES_ALL),
            "register_id": cert.register_id,
            "qubit_a": qubit_a,
            "qubit_b": qubit_b,
            "pulse_count": sched.pulse_count,
            "duration_us": round(sched.total_duration_us, 4),
            "swap_fidelity": pcert.nominal_state_fidelity,
            "certified": pcert.certified,
            "cert_sha256": pcert.sha256,
        }

    def execute_qldpc_round(
        self,
        code_name: str = "BB_144_12_12",
        n_data: int = 144,
        n_logical: int = 12,
        distance: int = 12,
        check_weight: int = 6,
        p_phys: float = 0.002,
        p_threshold: float = 0.007,
        n_mux: int = 32,
        tau_ro_us: float = 2.0,
        echo_cz_us: float = 0.29,
        rounds: int = 1,
        *,
        n_shots: int = 256,
        seed: int = 2026145,
        use_osd: bool = True,
        osd_order: int = 1,
        injected_x_error: list[int] | np.ndarray | None = None,
        injected_z_error: list[int] | np.ndarray | None = None,
    ) -> dict[str, Any]:
        """Execute CellISA v4.0 ``QLDPC_ROUND`` with exact GF(2) BB parity checks & BP-OSD decoding.

        Builds the exact Bivariate Bicycle CSS parity-check matrices (H_X, H_Z) and symplectic
        logical operators (L_X, L_Z) grounded in Exp144/Exp147 (Bravyi et al., Nature 2024),
        extracts exact GF(2) syndromes s_Z = H_Z e_X (mod 2) and s_X = H_X e_Z (mod 2), and
        decodes with vectorized Normalized Min-Sum Belief Propagation + bit-packed GF(2) OSD.
        """
        _ = (n_logical, distance, check_weight, p_threshold)
        code_key = _resolve_bb_code_key(code_name, n_data)
        code = _get_bb_code_algebra(code_key)

        n_d = int(code["n_data"])
        n_a = int(code["n_ancilla"])
        k_l = int(code["k"])
        dist = int(code["distance"])
        w_chk = int(code["check_weight"])
        n_rounds = max(1, int(rounds))
        nm = max(1, int(n_mux))

        inst = CellInstruction(
            opcode="QLDPC_ROUND",
            args={
                "code_name": code_name,
                "n_data": n_d,
                "n_logical": k_l,
                "distance": dist,
                "rounds": n_rounds,
                "n_mux": nm,
            },
        )
        feedlines_required = int(math.ceil(n_a / nm))
        round_duration_us = w_chk * float(echo_cz_us) + float(tau_ro_us)
        total_duration_us = round_duration_us * n_rounds
        code_rate = float(k_l) / max(float(n_d + n_a), 1.0)

        H_X_csr = code["tanner_X"]["H_csr"]
        H_Z_csr = code["tanner_Z"]["H_csr"]
        L_X = code["L_X"]
        L_Z = code["L_Z"]

        p_err = float(np.clip(p_phys, 0.0, 0.5))
        p_prior = max(p_err, 1e-4)

        deterministic_mode = (injected_x_error is not None) or (injected_z_error is not None)
        if deterministic_mode:
            e_x = (
                np.zeros((1, n_d), dtype=np.uint8)
                if injected_x_error is None
                else (np.asarray(injected_x_error, dtype=np.uint8).reshape(1, n_d) & 1).copy()
            )
            e_z = (
                np.zeros((1, n_d), dtype=np.uint8)
                if injected_z_error is None
                else (np.asarray(injected_z_error, dtype=np.uint8).reshape(1, n_d) & 1).copy()
            )
            syn_z = (e_x @ H_Z_csr.T) & 1
            syn_x = (e_z @ H_X_csr.T) & 1

            e_x_hat, conv_x, osd_x = _bp_osd_decode_batch(
                code["tanner_Z"], syn_z, p_prior, use_osd=use_osd, osd_order=osd_order
            )
            e_z_hat, conv_z, osd_z = _bp_osd_decode_batch(
                code["tanner_X"], syn_x, p_prior, use_osd=use_osd, osd_order=osd_order
            )

            res_x = e_x ^ e_x_hat
            res_z = e_z ^ e_z_hat
            syn_z_ok = bool(np.all(((res_x @ H_Z_csr.T) & 1) == 0))
            syn_x_ok = bool(np.all(((res_z @ H_X_csr.T) & 1) == 0))
            log_z_flip = bool(np.any(((res_x @ L_Z.T) & 1) != 0))
            log_x_flip = bool(np.any(((res_z @ L_X.T) & 1) != 0))
            log_fail = bool(log_z_flip or log_x_flip or (not syn_z_ok) or (not syn_x_ok))

            return {
                "opcode": inst.opcode,
                "isa_version": "4.0",
                "total_opcodes_v4": len(VALID_OPCODES_ALL),
                "decoder": "gf2_bb_normalized_min_sum_bp_osd",
                "mode": "deterministic_injected_error",
                "code_name": code_name,
                "resolved_bb_code": code["code_name"],
                "n_data": n_d,
                "n_ancilla": n_a,
                "n_logical": k_l,
                "distance": dist,
                "check_weight": w_chk,
                "rank_H_X": code["rank_X"],
                "rank_H_Z": code["rank_Z"],
                "css_commutativity_verified": code["commutativity_verified"],
                "symplectic_logical_verified": code["symplectic_verified"],
                "code_rate_k_over_2n": round(code_rate, 6),
                "feedlines_required": feedlines_required,
                "round_duration_us": round(round_duration_us, 4),
                "total_duration_us": round(total_duration_us, 4),
                "p_phys": p_err,
                "p_logical_per_round_est": 1.0 if log_fail else 0.0,
                "rounds": 1,
                "n_shots": 1,
                "n_logical_errors": 1 if log_fail else 0,
                "syndrome_Z_weight": int(np.sum(syn_z)),
                "syndrome_X_weight": int(np.sum(syn_x)),
                "syndrome_Z_vector": [int(b) for b in syn_z[0]],
                "syndrome_X_vector": [int(b) for b in syn_x[0]],
                "correction_weight_X": int(np.sum(e_x_hat)),
                "correction_weight_Z": int(np.sum(e_z_hat)),
                "decoded_syndrome_matched": bool(syn_z_ok and syn_x_ok),
                "logical_error_Z_observable": log_z_flip,
                "logical_error_X_observable": log_x_flip,
                "bp_converged_frac": 0.5 * (float(conv_x[0]) + float(conv_z[0])),
                "n_osd_triggered": int(osd_x + osd_z),
                "syndrome_valid_frac": 1.0 if (syn_z_ok and syn_x_ok) else 0.0,
            }

        # Monte Carlo multi-round GF(2) CSS parity-check & BP-OSD decoding simulation
        rng = np.random.default_rng(int(seed))
        B = max(1, int(n_shots))
        e_x = np.zeros((B, n_d), dtype=np.uint8)
        e_z = np.zeros((B, n_d), dtype=np.uint8)

        tot_bp_conv = 0
        tot_osd = 0
        tot_syn_valid = 0
        tot_nz_syn_z = 0
        tot_nz_syn_x = 0
        sum_syn_w_z = 0
        sum_syn_w_x = 0
        any_syn_invalid = np.zeros(B, dtype=bool)

        for _ in range(n_rounds):
            if p_err > 0.0:
                e_x ^= (rng.random((B, n_d)) < p_err).astype(np.uint8)
                e_z ^= (rng.random((B, n_d)) < p_err).astype(np.uint8)

            syn_z = (e_x @ H_Z_csr.T) & 1
            syn_x = (e_z @ H_X_csr.T) & 1
            tot_nz_syn_z += int(np.sum(np.any(syn_z != 0, axis=1)))
            tot_nz_syn_x += int(np.sum(np.any(syn_x != 0, axis=1)))
            sum_syn_w_z += int(np.sum(syn_z))
            sum_syn_w_x += int(np.sum(syn_x))

            e_x_hat, conv_x, osd_x = _bp_osd_decode_batch(
                code["tanner_Z"], syn_z, p_prior, use_osd=use_osd, osd_order=osd_order
            )
            e_z_hat, conv_z, osd_z = _bp_osd_decode_batch(
                code["tanner_X"], syn_x, p_prior, use_osd=use_osd, osd_order=osd_order
            )
            tot_bp_conv += int(np.sum(conv_x)) + int(np.sum(conv_z))
            tot_osd += int(osd_x + osd_z)

            e_x ^= e_x_hat
            e_z ^= e_z_hat

            ok_z = np.all(((e_x @ H_Z_csr.T) & 1) == 0, axis=1)
            ok_x = np.all(((e_z @ H_X_csr.T) & 1) == 0, axis=1)
            tot_syn_valid += int(np.sum(ok_z)) + int(np.sum(ok_x))
            any_syn_invalid |= (~ok_z) | (~ok_x)

        log_z_fail = np.any(((e_x @ L_Z.T) & 1) != 0, axis=1)
        log_x_fail = np.any(((e_z @ L_X.T) & 1) != 0, axis=1)
        shot_fail = log_z_fail | log_x_fail | any_syn_invalid
        n_log_err = int(np.sum(shot_fail))
        p_block = n_log_err / float(B)
        p_round = 1.0 - ((max(0.0, 1.0 - p_block)) ** (1.0 / n_rounds))

        # Wilson 95% confidence interval on block & per-round logical error rate
        z95 = 1.95996
        denom = 1.0 + (z95 * z95) / B
        center = (p_block + (z95 * z95) / (2.0 * B)) / denom
        half = (z95 * math.sqrt((p_block * (1.0 - p_block) + (z95 * z95) / (4.0 * B)) / B)) / denom
        ci_hi_block = min(1.0, center + half)
        ci_hi_round = 1.0 - ((max(0.0, 1.0 - ci_hi_block)) ** (1.0 / n_rounds))

        total_decodes = 2 * B * n_rounds
        return {
            "opcode": inst.opcode,
            "isa_version": "4.0",
            "total_opcodes_v4": len(VALID_OPCODES_ALL),
            "decoder": "gf2_bb_normalized_min_sum_bp_osd",
            "mode": "monte_carlo_css_gf2",
            "code_name": code_name,
            "resolved_bb_code": code["code_name"],
            "n_data": n_d,
            "n_ancilla": n_a,
            "n_logical": k_l,
            "distance": dist,
            "check_weight": w_chk,
            "rank_H_X": code["rank_X"],
            "rank_H_Z": code["rank_Z"],
            "css_commutativity_verified": code["commutativity_verified"],
            "symplectic_logical_verified": code["symplectic_verified"],
            "code_rate_k_over_2n": round(code_rate, 6),
            "feedlines_required": feedlines_required,
            "round_duration_us": round(round_duration_us, 4),
            "total_duration_us": round(total_duration_us, 4),
            "p_phys": p_err,
            "p_logical_per_round_est": float(f"{p_round:.4e}"),
            "p_logical_block_mc": round(p_block, 6),
            "p_logical_per_round_ci95_upper": float(f"{ci_hi_round:.4e}"),
            "rounds": n_rounds,
            "n_shots": B,
            "n_logical_errors": n_log_err,
            "nonzero_syndrome_events_Z": tot_nz_syn_z,
            "nonzero_syndrome_events_X": tot_nz_syn_x,
            "mean_syndrome_weight_Z": round(sum_syn_w_z / float(B * n_rounds), 4),
            "mean_syndrome_weight_X": round(sum_syn_w_x / float(B * n_rounds), 4),
            "bp_converged_frac": round(tot_bp_conv / float(total_decodes), 6),
            "n_osd_triggered": tot_osd,
            "syndrome_valid_frac": round(tot_syn_valid / float(total_decodes), 6),
        }

    def execute_auto_recal(
        self,
        fault_type: str = "thermal_drift_Hz",
        magnitude: float = 350.0,
        seed: int = 2026145,
    ) -> dict[str, Any]:
        """Execute CellISA v4.0 ``AUTO_RECAL`` supervisory closed-loop fault recovery."""
        inst = CellInstruction(
            opcode="AUTO_RECAL",
            args={"fault_type": str(fault_type), "magnitude": float(magnitude)},
        )
        from .auto_recal import AutoRecalController

        ctrl = AutoRecalController(seed=seed)
        if fault_type == "laser_power_drift_pct":
            res = ctrl.mitigate_laser_power_drift(drift_pct=float(magnitude))
        elif fault_type == "vacuum_spike_torr":
            res = ctrl.mitigate_vacuum_spike(peak_pressure_torr=float(magnitude))
        elif fault_type == "blanker_dead_frac":
            res = ctrl.mitigate_blanker_dead_channels(dead_fraction=float(magnitude))
        else:
            res = ctrl.mitigate_hyperfine_thermal_drift(drift_Hz=float(magnitude))
        return {
            "opcode": inst.opcode,
            "isa_version": "4.0",
            "total_opcodes_v4": len(VALID_OPCODES_ALL),
            "recovery": res,
        }


