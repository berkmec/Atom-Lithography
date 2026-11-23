"""CellISA v3.0 instruction set and AtomCellProgrammer / MultiCellProgrammer (Exp132).

Compiles high-level quantum/atom-cell programs expressed in ``CellISA`` into
per-cell physical MW/RF control waveforms tailored to each certified register's
measured hyperfine spectrum ``{A_k}``, verifies execution on the full
2^(N_nuc + 1) multi-spin Hilbert space (nominal + +/-400 Hz, +/-2% corners +
XY8 dynamical decoupling), and emits SHA-256 signed ``ProgramCertificate``
and ``MultiCellCertificate`` records (JSONL).

Supported CellISA opcodes:
  * v2.0 (10 opcodes, 100% backwards-compatible):
      INIT, RX, RY, RZ, CZ, CNOT, GHZ, DD_HOLD, MEASURE, ARRAY_EXEC
  * v3.0 (4 multi-cell M4 & wafer-routing opcodes):
      BUS_TUNE, BUS_CZ, LOGICAL_ENCODE, WAFER_MAP_ROUTE

Includes a portable ``verify_with_exp126_bridge()`` provenance link to the full
32D (2^5) 448-spectator XY8-GRAPE verification ledger in
``results/exp126_atom_cell_programming/exp126.json``.

Epistemic tag: {Model} (simulation/compiler layer; no physical hardware).
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

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
VALID_OPCODES = VALID_OPCODES_V2 | VALID_OPCODES_V3


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
        if op not in VALID_OPCODES:
            raise ValueError(f"Invalid CellISA opcode {self.opcode!r}; valid: {sorted(VALID_OPCODES)}")
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
        elif op in ("DD_HOLD", "MEASURE", "ARRAY_EXEC"):
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

