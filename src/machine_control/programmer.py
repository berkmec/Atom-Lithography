"""CellISA instruction set and AtomCellProgrammer compiler/verifier (v2.0).

Compiles high-level quantum/atom-cell programs expressed in ``CellISA`` into
per-cell physical MW/RF control waveforms tailored to each certified register's
measured hyperfine spectrum ``{A_k}``, verifies execution on the full
2^(N_nuc + 1) multi-spin Hilbert space (nominal + +/-400 Hz, +/-2% corners +
XY8 dynamical decoupling), and emits SHA-256 signed ``ProgramCertificate``
records (JSONL).

Supported CellISA opcodes:
  INIT, RX, RY, RZ, CZ, CNOT, GHZ, DD_HOLD, MEASURE, ARRAY_EXEC

Epistemic tag: {Model} (simulation/compiler layer; no physical hardware).
"""
from __future__ import annotations

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

VALID_OPCODES = frozenset({
    "INIT", "RX", "RY", "RZ", "CZ", "CNOT", "GHZ", "DD_HOLD", "MEASURE", "ARRAY_EXEC"
})


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
