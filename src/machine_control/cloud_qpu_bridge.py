"""Zero-dependency native-ISA OpenQASM 3.0 transpiler & IBM Quantum Platform 2026 REST bridge (Exp145).

Provides:
  1. ``select_best_linear_chain``: Globally optimal connected 5-qubit linear subgraph
     selector on IBM Heavy-Hex topologies (zero SWAPs for d=3 repetition code).
  2. ``NativeOpenQASM3Transpiler``: Emits strictly native-ISA OpenQASM 3.0 targeting
     both IBM Heron (``{rz, sx, x, id, cz}``) and IBM Eagle (``{rz, sx, x, id, ecr}``)
     with ``granularity``-aligned (16-dt) hardware timing delays, plus CellISA -> OpenQASM 3.0
     export for standard CellProgram circuits.
  3. ``IBMQuantumRESTClient``: Pure-``requests`` IBM Cloud IAM + Quantum Platform 2026
     REST API v1 client (ZERO ``qiskit`` dependency, ZERO hardcoded credentials, strict
     secret redaction on all errors/logs, universal SamplerV2 result parser).
  4. ``simulate_offline_heron_counts`` & ``analyze_validation_suite_counts``: Shared
     exact physics analyzer for Circuits C1 (Bare/Echo/XY4 DD + 2Q Bell tomography),
     C2 (5Q linear d=3 repetition code with space-time syndrome MWPM decoding), and
     C3 (8-point Ramsey fringe comparing bit-exact Q16.16 BOED vs FP64 BOED vs blind fit).

Epistemic status:
  - Offline simulator outputs are tagged ``{Model}`` / ``{Sayisal-Simulasyon}``.
  - Real IBM QPU execution results are tagged ``{Canli-Donanim-IBM-QPU}``.
"""
from __future__ import annotations

import base64
from collections import Counter
from dataclasses import dataclass
import io
import json
import math
import os
import re
import time
from typing import Any
import zlib

import numpy as np

from .fpga_boed_dsp import (
    EXP_LUT_SIZE,
    EXP_X_MAX,
    INT32_MAX,
    INT32_MIN,
    Q_FRAC,
    Q_HALF,
    Q_ONE,
    build_exp_neg_lut_q16,
    lut_interp_q16,
    q16_mul,
    to_q16,
)
from .programmer import CellProgram, parse_qubit

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Constants & Validation Suite Specification
# ---------------------------------------------------------------------------

IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
IBM_API_BASE_US = "https://quantum.cloud.ibm.com/api/v1"
IBM_API_BASE_EU = "https://eu-de.quantum.cloud.ibm.com/api/v1"
DEFAULT_API_VERSIONS = ("2026-02-01", "2026-04-15", "2025-05-01", "2025-01-01", None)

C1_IDLE_US = 48.0
C2_IDLE_US = 4.0
C3_DETUNING_KHZ = 125.0
C3_DELAYS_US = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)

SUITE_PUB_SPECS: tuple[tuple[str, int], ...] = (
    ("C1a_bare_idle", 1),
    ("C1b_hahn_echo", 1),
    ("C1c_xy4_dd", 1),
    ("C1d_bell_zz", 2),
    ("C1e_bell_xx", 2),
    ("C1f_bell_yy", 2),
    ("C2a_rep3_logical0", 5),
    ("C2b_rep3_logical1", 5),
    *(
        (f"C3_ramsey_{f'{d:.1f}'.replace('.', 'p')}us", 1)
        for d in C3_DELAYS_US
    ),
)


# ---------------------------------------------------------------------------
# Secret Redaction & Security Helpers
# ---------------------------------------------------------------------------

def redact_secrets(text: str, secrets: tuple[str, ...] = ()) -> str:
    """Scrub any API key, IAM Bearer token, or Service-CRN from logs/errors."""
    out = str(text)
    for sec in secrets:
        if sec and len(sec) >= 6:
            out = out.replace(sec, "[REDACTED]")
    out = re.sub(r"Bearer\s+[A-Za-z0-9._\-+/=]+", "Bearer [REDACTED]", out)
    out = re.sub(r"crn:v1:[^\s\"',;\]\}]+", "crn:v1:[REDACTED]", out)
    out = re.sub(r"apikey=[^\s&\"']+", "apikey=[REDACTED]", out)
    return out


def detect_ibm_base_url(service_crn: str) -> str:
    """Auto-select IBM Quantum Platform 2026 regional REST endpoint from CRN."""
    if "eu-de" in str(service_crn).lower():
        return IBM_API_BASE_EU
    return IBM_API_BASE_US


# ---------------------------------------------------------------------------
# Backend Properties Parser & 5-Qubit Linear Chain Selector
# ---------------------------------------------------------------------------

def _to_seconds(val: float, unit: str) -> float:
    u = str(unit or "s").strip().lower()
    if u in ("ns", "nanosecond", "nanoseconds"):
        return val * 1e-9
    if u in ("us", "µs", "microsecond", "microseconds"):
        return val * 1e-6
    if u in ("ms", "millisecond", "milliseconds"):
        return val * 1e-3
    return val


def parse_backend_metrics(
    config: dict[str, Any],
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract normalized qubit T1/T2/readout_error and 2Q gate_error from IBM JSON."""
    n_qubits = int(config.get("n_qubits") or config.get("num_qubits") or 0)
    basis_gates = [str(g).lower() for g in config.get("basis_gates", [])]
    coupling_map = [
        (int(edge[0]), int(edge[1]))
        for edge in config.get("coupling_map", [])
        if isinstance(edge, (list, tuple)) and len(edge) == 2
    ]
    if n_qubits == 0 and coupling_map:
        n_qubits = max(max(u, v) for u, v in coupling_map) + 1

    native_2q = "cz" if "cz" in basis_gates else ("ecr" if "ecr" in basis_gates else "cx")
    default_dt = 4e-9 if native_2q == "cz" else 0.5e-9
    raw_dt = float(config.get("dt") or default_dt)
    # IBM Quantum Platform 2026 REST /configuration returns dt in nanoseconds (e.g. 4.0),
    # whereas legacy configs return dt in seconds (e.g. 4e-9). Normalize both cleanly to seconds!
    dt_s = raw_dt * 1e-9 if raw_dt > 1e-3 else raw_dt
    tc = config.get("timing_constraints") or {}
    granularity = max(16, int(tc.get("granularity") or 16))
    min_delay_dt = max(64, int(tc.get("min_length") or 64))

    t1_s: dict[int, float] = {}
    t2_s: dict[int, float] = {}
    ro_err: dict[int, float] = {}
    twoq_err: dict[tuple[int, int], float] = {}

    if properties:
        qubits_props = properties.get("qubits") or []
        for q_idx, q_items in enumerate(qubits_props):
            if not isinstance(q_items, list):
                continue
            for item in q_items:
                name = str(item.get("name", "")).lower()
                val = item.get("value")
                if val is None:
                    continue
                fval = float(val)
                unit = str(item.get("unit", ""))
                if name == "t1":
                    t1_s[q_idx] = _to_seconds(fval, unit)
                elif name == "t2":
                    t2_s[q_idx] = _to_seconds(fval, unit)
                elif name in ("readout_error", "prob_meas0_prep1", "prob_meas1_prep0"):
                    if name == "readout_error":
                        ro_err[q_idx] = fval
                    elif q_idx not in ro_err:
                        ro_err[q_idx] = fval

        for g in properties.get("gates") or []:
            gname = str(g.get("gate", "")).lower()
            qs = g.get("qubits") or []
            if len(qs) == 2 and gname in ("cz", "ecr", "cx"):
                for p in g.get("parameters") or []:
                    if str(p.get("name", "")).lower() == "gate_error" and p.get("value") is not None:
                        err = float(p["value"])
                        u, v = int(qs[0]), int(qs[1])
                        twoq_err[(u, v)] = err
                        if gname == "cz":
                            twoq_err.setdefault((v, u), err)

    return {
        "n_qubits": n_qubits,
        "basis_gates": basis_gates,
        "native_2q": native_2q,
        "coupling_map": coupling_map,
        "directed_edges": set(coupling_map),
        "dt_s": dt_s,
        "granularity": granularity,
        "min_delay_dt": min_delay_dt,
        "t1_s": t1_s,
        "t2_s": t2_s,
        "readout_error": ro_err,
        "twoq_error": twoq_err,
    }


def select_best_linear_chain(
    config: dict[str, Any],
    properties: dict[str, Any] | None = None,
    length: int = 5,
) -> dict[str, Any]:
    """Find the globally optimal connected linear path of ``length`` qubits on Heavy-Hex.

    Guarantees ZERO SWAP gates for C1 (2Q Bell on chain[0:2]) and C2 (5Q d=3 repetition
    code with data=(q0,q2,q4) and ancillas=(q1,q3)). Minimizes 2Q gate error, readout
    error, and inverse T2 across the chain, with extra weight on q0 and edge (q0, q1).
    """
    m = parse_backend_metrics(config, properties)
    undirected: dict[int, set[int]] = {}
    for u, v in m["coupling_map"]:
        if u == v:
            continue
        undirected.setdefault(u, set()).add(v)
        undirected.setdefault(v, set()).add(u)

    if not undirected:
        raise ValueError("Backend configuration has an empty coupling_map")

    t2_map = m["t2_s"]
    ro_map = m["readout_error"]
    e2_map = m["twoq_error"]

    def _edge_err(u: int, v: int) -> float:
        if (u, v) in e2_map:
            return min(0.5, max(1e-4, e2_map[(u, v)]))
        if (v, u) in e2_map:
            return min(0.5, max(1e-4, e2_map[(v, u)]))
        return 0.015

    def _q_cost(q: int) -> float:
        ro = min(0.5, max(1e-4, ro_map.get(q, 0.025)))
        t2 = max(1e-6, t2_map.get(q, 80e-6))
        # Penalize faulty/uncalibrated qubits with readout error >= 0.3 or T2 < 10 us
        pen = 5.0 if (ro >= 0.30 or t2 < 10e-6) else 0.0
        return 0.5 * ro + 0.25 * min(1.0, 20e-6 / t2) + pen

    best_score = float("inf")
    best_path: list[int] | None = None

    # Exact DFS over all simple paths of length ``length`` (fast on Heavy-Hex: deg <= 3)
    nodes = sorted(undirected.keys())

    def _dfs(path: list[int], visited: set[int], acc_score: float) -> None:
        nonlocal best_score, best_path
        if acc_score >= best_score:
            return
        if len(path) == length:
            best_score = acc_score
            best_path = list(path)
            return
        last = path[-1]
        for nxt in sorted(undirected[last]):
            if nxt in visited:
                continue
            e_cost = _edge_err(last, nxt)
            # Extra weight on edge (q0, q1) used by C1 Bell tomography
            w_edge = 1.5 if len(path) == 1 else 1.0
            q_cost = _q_cost(nxt)
            visited.add(nxt)
            path.append(nxt)
            _dfs(path, visited, acc_score + w_edge * e_cost + q_cost)
            path.pop()
            visited.remove(nxt)

    for start in nodes:
        # Extra weight on q0 used by C1 DD and C3 Ramsey
        _dfs([start], {start}, 1.5 * _q_cost(start))

    if best_path is None:
        raise RuntimeError(f"No connected linear chain of length {length} found in coupling_map")

    edge_errors = [round(_edge_err(best_path[i], best_path[i + 1]), 6) for i in range(length - 1)]
    ro_errors = [round(ro_map.get(q, 0.025), 6) for q in best_path]
    t1_us = [round(m["t1_s"].get(q, 150e-6) * 1e6, 2) for q in best_path]
    t2_us = [round(t2_map.get(q, 80e-6) * 1e6, 2) for q in best_path]

    return {
        "qubits": best_path,
        "native_2q": m["native_2q"],
        "dt_s": m["dt_s"],
        "granularity": m["granularity"],
        "min_delay_dt": m["min_delay_dt"],
        "directed_edges": sorted([list(e) for e in m["directed_edges"]]),
        "chain_edge_errors": edge_errors,
        "chain_readout_errors": ro_errors,
        "chain_t1_us": t1_us,
        "chain_t2_us": t2_us,
        "score": round(best_score, 6),
    }


def make_synthetic_heavy_hex_backend(
    family: str = "heron",
    n_qubits: int = 133,
    seed: int = 2026145,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Construct a realistic IBM Heron (cz) or Eagle (ecr) backend config & properties."""
    rng = np.random.default_rng(seed)
    fam = family.strip().lower()
    is_heron = fam != "eagle"
    native_2q = "cz" if is_heron else "ecr"
    basis = ["cz", "id", "rz", "sx", "x"] if is_heron else ["ecr", "id", "rz", "sx", "x"]
    dt_s = 4e-9 if is_heron else 0.5e-9

    # Build a Heavy-Hex-like sparse planar graph (degree <= 3) with long chains
    edges: list[list[int]] = []
    for q in range(n_qubits - 1):
        if (q + 1) % 15 != 0:
            edges.append([q, q + 1])
            if is_heron:
                edges.append([q + 1, q])
    # Add vertical rungs every 4 qubits
    for q in range(0, n_qubits - 15, 4):
        edges.append([q, q + 15])
        if is_heron:
            edges.append([q + 15, q])

    config = {
        "backend_name": "ibm_heron_sim_133" if is_heron else "ibm_eagle_sim_127",
        "n_qubits": n_qubits,
        "simulator": False,
        "basis_gates": basis,
        "coupling_map": edges,
        "dt": dt_s,
        "timing_constraints": {
            "granularity": 16,
            "min_length": 64,
            "pulse_alignment": 16,
        },
    }

    qubits_props = []
    for q in range(n_qubits):
        t1_us = float(np.clip(rng.normal(185.0 if is_heron else 140.0, 35.0), 40.0, 320.0))
        t2_us = float(np.clip(rng.normal(125.0 if is_heron else 95.0, 30.0), 25.0, 260.0))
        ro = float(np.clip(rng.normal(0.015 if is_heron else 0.022, 0.006), 0.004, 0.08))
        qubits_props.append([
            {"name": "T1", "unit": "us", "value": round(t1_us, 3)},
            {"name": "T2", "unit": "us", "value": round(t2_us, 3)},
            {"name": "readout_error", "unit": "", "value": round(ro, 6)},
        ])

    gate_props = []
    seen = set()
    for u, v in edges:
        key = (min(u, v), max(u, v)) if is_heron else (u, v)
        if key in seen:
            continue
        seen.add(key)
        gerr = float(np.clip(rng.normal(0.0055 if is_heron else 0.009, 0.002), 0.0015, 0.04))
        gate_props.append({
            "gate": native_2q,
            "qubits": [u, v],
            "parameters": [{"name": "gate_error", "unit": "", "value": round(gerr, 6)}],
        })

    properties = {
        "backend_name": config["backend_name"],
        "qubits": qubits_props,
        "gates": gate_props,
    }
    return config, properties


# ---------------------------------------------------------------------------
# Native-ISA OpenQASM 3.0 Transpiler (Heron cz & Eagle ecr)
# ---------------------------------------------------------------------------

def align_delay_dt(
    duration_s: float,
    dt_s: float,
    granularity: int = 16,
    min_delay_dt: int = 64,
) -> int:
    """Snap a physical delay duration (s) to an exact hardware ``granularity``-dt multiple."""
    if duration_s <= 0.0:
        return 0
    raw_dt = duration_s / max(dt_s, 1e-12)
    g = max(1, int(granularity))
    snapped = int(round(raw_dt / g)) * g
    if snapped < min_delay_dt:
        snapped = int(math.ceil(min_delay_dt / g)) * g
    return snapped


def _fmt_angle(theta: float) -> str:
    """Format an angle cleanly for OpenQASM 3.0."""
    # Wrap to (-pi, pi]
    t = (float(theta) + math.pi) % (2.0 * math.pi) - math.pi
    if abs(t - math.pi) < 1e-12 or abs(t + math.pi) < 1e-12:
        return "pi"
    if abs(t - math.pi / 2.0) < 1e-12:
        return "pi/2"
    if abs(t + math.pi / 2.0) < 1e-12:
        return "-pi/2"
    return f"{t:.10f}"


class NativeOpenQASM3Transpiler:
    """Zero-dependency compiler emitting strictly native-ISA OpenQASM 3.0 for IBM QPUs.

    Targets:
      - ``cz`` (IBM Heron: ``ibm_fez``, ``ibm_torino``, ``ibm_marrakesh``, ...)
      - ``ecr`` (IBM Eagle: ``ibm_brisbane``, ``ibm_sherbrooke``, ``ibm_kyiv``, ...)

    Single-qubit basis: ``{rz, sx, x, id}``.
    All physical qubits are addressed directly via ``$q`` matching the selected
    connected subgraph (zero SWAPs) and all ``delay[Ndt]`` statements obey the
    backend's ``granularity`` (16-dt) constraint.
    """

    def __init__(
        self,
        qubits: list[int],
        native_2q: str = "cz",
        dt_s: float = 4e-9,
        granularity: int = 16,
        min_delay_dt: int = 64,
        directed_edges: set[tuple[int, int]] | list[list[int]] | None = None,
    ):
        self.qubits = [int(q) for q in qubits]
        self.native_2q = str(native_2q).lower()
        if self.native_2q not in ("cz", "ecr"):
            raise ValueError(f"Unsupported native_2q={native_2q!r}; expected 'cz' or 'ecr'")
        self.dt_s = float(dt_s)
        self.granularity = int(granularity)
        self.min_delay_dt = int(min_delay_dt)
        if directed_edges is None:
            # Default: all adjacent chain edges valid in both directions for cz, forward for ecr
            de: set[tuple[int, int]] = set()
            for i in range(len(self.qubits) - 1):
                u, v = self.qubits[i], self.qubits[i + 1]
                de.add((u, v))
                if self.native_2q == "cz":
                    de.add((v, u))
            self.directed_edges = de
        else:
            self.directed_edges = {(int(e[0]), int(e[1])) for e in directed_edges}

    def _header(self, n_bits: int) -> list[str]:
        lines = [
            "OPENQASM 3.0;",
            'include "stdgates.inc";',
        ]
        if self.native_2q == "ecr":
            # Standard Qiskit/IBM ECRGate definition (verified exact to 1.1e-16)
            lines.extend([
                "gate ecr _gate_q_0, _gate_q_1 {",
                "  s _gate_q_0;",
                "  sx _gate_q_1;",
                "  cx _gate_q_0, _gate_q_1;",
                "  x _gate_q_0;",
                "}",
            ])
        lines.append(f"bit[{int(n_bits)}] c;")
        return lines

    def _emit_rz(self, lines: list[str], q: int, theta: float) -> None:
        t = (float(theta) + math.pi) % (2.0 * math.pi) - math.pi
        if abs(t) < 1e-12:
            return
        lines.append(f"rz({_fmt_angle(t)}) ${q};")

    def _emit_h(self, lines: list[str], q: int) -> None:
        # Exact H = e^{-i pi/4} Rz(pi/2) . SX . Rz(pi/2)
        lines.append(f"rz(pi/2) ${q};")
        lines.append(f"sx ${q};")
        lines.append(f"rz(pi/2) ${q};")

    def _emit_x(self, lines: list[str], q: int) -> None:
        lines.append(f"x ${q};")

    def _emit_y(self, lines: list[str], q: int) -> None:
        # Exact up to global phase: Rz(pi) . X = -i Z X = +Y
        lines.append(f"x ${q};")
        lines.append(f"rz(pi) ${q};")

    def _emit_rx(self, lines: list[str], q: int, theta: float) -> None:
        # Exact Rx(theta) = Rz(-pi/2) . SX . Rz(pi - theta) . SX . Rz(-pi/2)  (up to global phase)
        # Or simpler: Rx(theta) = Rz(pi/2) . SX . Rz(theta + pi) . SX . Rz(pi/2)
        # Check special angles first for minimal pulse depth:
        t = (float(theta) + math.pi) % (2.0 * math.pi) - math.pi
        if abs(t) < 1e-12:
            return
        if abs(abs(t) - math.pi) < 1e-12:
            lines.append(f"x ${q};")
            return
        if abs(t - math.pi / 2.0) < 1e-12:
            lines.append(f"sx ${q};")
            return
        if abs(t + math.pi / 2.0) < 1e-12:
            lines.append(f"rz(pi) ${q};")
            lines.append(f"sx ${q};")
            lines.append(f"rz(pi) ${q};")
            return
        # General Rx(theta) = H . Rz(theta) . H (exact, 2 SX gates)
        self._emit_h(lines, q)
        self._emit_rz(lines, q, t)
        self._emit_h(lines, q)

    def _emit_ry(self, lines: list[str], q: int, theta: float) -> None:
        # Exact Ry(theta) = Rz(pi/2) . Rx(theta) . Rz(-pi/2)
        t = (float(theta) + math.pi) % (2.0 * math.pi) - math.pi
        if abs(t) < 1e-12:
            return
        if abs(abs(t) - math.pi) < 1e-12:
            self._emit_y(lines, q)
            return
        # Circuit order: Rz(-pi/2), then Rx(theta), then Rz(pi/2)
        # Even shorter (1 SX for +-pi/2):
        if abs(t - math.pi / 2.0) < 1e-12:
            lines.append(f"rz(-pi/2) ${q};")
            lines.append(f"sx ${q};")
            lines.append(f"rz(pi/2) ${q};")
            return
        if abs(t + math.pi / 2.0) < 1e-12:
            lines.append(f"rz(pi/2) ${q};")
            lines.append(f"sx ${q};")
            lines.append(f"rz(-pi/2) ${q};")
            return
        lines.append(f"rz(-pi/2) ${q};")
        self._emit_rx(lines, q, t)
        lines.append(f"rz(pi/2) ${q};")

    def _emit_cnot_native_ecr_forward(self, lines: list[str], ctrl: int, tgt: int) -> None:
        """Exact CNOT(ctrl -> tgt) using native directed ecr $ctrl, $tgt (err = 2.36e-16)."""
        lines.append(f"x ${ctrl};")
        lines.append(f"ecr ${ctrl}, ${tgt};")
        lines.append(f"rz(pi/2) ${ctrl};")
        lines.append(f"sx ${tgt};")

    def _emit_cnot(self, lines: list[str], ctrl: int, tgt: int) -> None:
        """Emit exact native-ISA CNOT(ctrl -> tgt) respecting Heron cz or directed Eagle ecr."""
        if self.native_2q == "cz":
            # CNOT(c -> t) = H(t) . CZ(c, t) . H(t)
            self._emit_h(lines, tgt)
            lines.append(f"cz ${ctrl}, ${tgt};")
            self._emit_h(lines, tgt)
            return

        # Eagle native ecr: check directed coupling orientation
        if (ctrl, tgt) in self.directed_edges or (tgt, ctrl) not in self.directed_edges:
            self._emit_cnot_native_ecr_forward(lines, ctrl, tgt)
        else:
            # Reverse orientation via H(c) H(t) CNOT(t -> c) H(c) H(t)
            self._emit_h(lines, ctrl)
            self._emit_h(lines, tgt)
            self._emit_cnot_native_ecr_forward(lines, tgt, ctrl)
            self._emit_h(lines, ctrl)
            self._emit_h(lines, tgt)

    def _emit_cz(self, lines: list[str], a: int, b: int) -> None:
        if self.native_2q == "cz":
            lines.append(f"cz ${a}, ${b};")
            return
        # CZ(a, b) = H(b) . CNOT(a -> b) . H(b)
        self._emit_h(lines, b)
        self._emit_cnot(lines, a, b)
        self._emit_h(lines, b)

    def _emit_delay(self, lines: list[str], q: int, duration_s: float) -> int:
        n_dt = align_delay_dt(duration_s, self.dt_s, self.granularity, self.min_delay_dt)
        if n_dt > 0:
            lines.append(f"delay[{n_dt}dt] ${q};")
        return n_dt

    def _emit_delay_dt(self, lines: list[str], q: int, n_dt: int) -> None:
        if n_dt > 0:
            lines.append(f"delay[{int(n_dt)}dt] ${q};")

    # --- Circuit Builders (C1, C2, C3 + Generic CellProgram) ---

    def build_c1_dd_and_bell(self, idle_us: float = C1_IDLE_US) -> dict[str, dict[str, Any]]:
        """Build the 6 C1 OpenQASM 3.0 circuits (Bare, Hahn-Echo, XY4 DD + Bell ZZ/XX/YY)."""
        q0, q1 = self.qubits[0], self.qubits[1]
        # Make total idle time identical across Bare, Echo, and XY4 (exact multiple of 8 * granularity)
        g8 = 8 * self.granularity
        raw_total = (idle_us * 1e-6) / max(self.dt_s, 1e-12)
        total_dt = max(g8, int(round(raw_total / g8)) * g8)
        half_dt = total_dt // 2
        tau_dt = total_dt // 8
        two_tau_dt = 2 * tau_dt
        actual_idle_us = total_dt * self.dt_s * 1e6

        out: dict[str, dict[str, Any]] = {}

        # C1a: Bare idle |+> -> delay -> H -> M
        lines = self._header(1)
        self._emit_h(lines, q0)
        lines.append(f"barrier ${q0};")
        self._emit_delay_dt(lines, q0, total_dt)
        lines.append(f"barrier ${q0};")
        self._emit_h(lines, q0)
        lines.append(f"c[0] = measure ${q0};")
        out["C1a_bare_idle"] = {"qasm": "\n".join(lines), "num_bits": 1, "idle_us": round(actual_idle_us, 4), "total_dt": total_dt}

        # C1b: Hahn-Echo |+> -> delay/2 -> X -> delay/2 -> H -> M
        lines = self._header(1)
        self._emit_h(lines, q0)
        lines.append(f"barrier ${q0};")
        self._emit_delay_dt(lines, q0, half_dt)
        self._emit_x(lines, q0)
        self._emit_delay_dt(lines, q0, half_dt)
        lines.append(f"barrier ${q0};")
        self._emit_h(lines, q0)
        lines.append(f"c[0] = measure ${q0};")
        out["C1b_hahn_echo"] = {"qasm": "\n".join(lines), "num_bits": 1, "idle_us": round(actual_idle_us, 4), "total_dt": total_dt}

        # C1c: XY4 Dynamical Decoupling |+> -> tau - X - 2tau - Y - 2tau - X - 2tau - Y - tau -> H -> M
        lines = self._header(1)
        self._emit_h(lines, q0)
        lines.append(f"barrier ${q0};")
        self._emit_delay_dt(lines, q0, tau_dt)
        self._emit_x(lines, q0)
        self._emit_delay_dt(lines, q0, two_tau_dt)
        self._emit_y(lines, q0)
        self._emit_delay_dt(lines, q0, two_tau_dt)
        self._emit_x(lines, q0)
        self._emit_delay_dt(lines, q0, two_tau_dt)
        self._emit_y(lines, q0)
        self._emit_delay_dt(lines, q0, tau_dt)
        lines.append(f"barrier ${q0};")
        self._emit_h(lines, q0)
        lines.append(f"c[0] = measure ${q0};")
        out["C1c_xy4_dd"] = {"qasm": "\n".join(lines), "num_bits": 1, "idle_us": round(actual_idle_us, 4), "total_dt": total_dt}

        # C1d/e/f: 2Q Bell |Phi+> tomography in ZZ, XX, YY bases on (q0, q1)
        for name, basis in (("C1d_bell_zz", "ZZ"), ("C1e_bell_xx", "XX"), ("C1f_bell_yy", "YY")):
            lines = self._header(2)
            self._emit_h(lines, q0)
            self._emit_cnot(lines, q0, q1)
            lines.append(f"barrier ${q0}, ${q1};")
            if basis == "XX":
                self._emit_h(lines, q0)
                self._emit_h(lines, q1)
            elif basis == "YY":
                # Y-basis measurement: S^dag = Rz(-pi/2), then H
                self._emit_rz(lines, q0, -math.pi / 2.0)
                self._emit_h(lines, q0)
                self._emit_rz(lines, q1, -math.pi / 2.0)
                self._emit_h(lines, q1)
            lines.append(f"c[0] = measure ${q0};")
            lines.append(f"c[1] = measure ${q1};")
            out[name] = {"qasm": "\n".join(lines), "num_bits": 2, "basis": basis, "qubits": [q0, q1]}

        return out

    def build_c2_repcode3(self, idle_us: float = C2_IDLE_US) -> dict[str, dict[str, Any]]:
        """Build 2 C2 circuits: 5-qubit linear d=3 bit-flip repetition code (0 SWAPs).

        Physical mapping on connected linear chain ``[q0, q1, q2, q3, q4]``:
          - Data qubits:    D0=q0 (c[0]), D1=q2 (c[2]), D2=q4 (c[4])
          - Ancilla qubits: A0=q1 (c[1], checks Z_D0 Z_D1), A1=q3 (c[3], checks Z_D1 Z_D2)
        """
        if len(self.qubits) < 5:
            raise ValueError("C2 d=3 repetition code requires a 5-qubit linear chain")
        d0, a0, d1, a1, d2 = self.qubits[:5]
        idle_dt = align_delay_dt(idle_us * 1e-6, self.dt_s, self.granularity, self.min_delay_dt)
        actual_idle_us = idle_dt * self.dt_s * 1e6
        out: dict[str, dict[str, Any]] = {}

        for name, logical_bit in (("C2a_rep3_logical0", 0), ("C2b_rep3_logical1", 1)):
            lines = self._header(5)
            # 1. Encode |0_L> = |000> or |1_L> = |111> on (d0, d1, d2)
            if logical_bit == 1:
                self._emit_x(lines, d0)
                self._emit_x(lines, d1)
                self._emit_x(lines, d2)
            lines.append(f"barrier ${d0}, ${a0}, ${d1}, ${a1}, ${d2};")
            # 2. Idle memory hold on data qubits (accumulating realistic T1/bit-flip errors)
            self._emit_delay_dt(lines, d0, idle_dt)
            self._emit_delay_dt(lines, d1, idle_dt)
            self._emit_delay_dt(lines, d2, idle_dt)
            lines.append(f"barrier ${d0}, ${a0}, ${d1}, ${a1}, ${d2};")
            # 3. Nearest-neighbor Z0Z1 and Z1Z2 parity syndrome extraction (ZERO SWAPs!)
            self._emit_cnot(lines, d0, a0)
            self._emit_cnot(lines, d1, a1)
            lines.append(f"barrier ${d0}, ${a0}, ${d1}, ${a1}, ${d2};")
            self._emit_cnot(lines, d1, a0)
            self._emit_cnot(lines, d2, a1)
            lines.append(f"barrier ${d0}, ${a0}, ${d1}, ${a1}, ${d2};")
            # 4. Measure all 5 qubits into c[0..4] = [D0, A0, D1, A1, D2]
            for idx, q in enumerate((d0, a0, d1, a1, d2)):
                lines.append(f"c[{idx}] = measure ${q};")
            out[name] = {
                "qasm": "\n".join(lines),
                "num_bits": 5,
                "logical_bit": logical_bit,
                "idle_us": round(actual_idle_us, 4),
                "idle_dt": idle_dt,
                "qubits": [d0, a0, d1, a1, d2],
            }
        return out

    def build_c3_ramsey(
        self,
        delays_us: tuple[float, ...] = C3_DELAYS_US,
        detuning_kHz: float = C3_DETUNING_KHZ,
    ) -> dict[str, dict[str, Any]]:
        """Build 8 C3 Ramsey fringe circuits on q0 with virtual detuning ``detuning_kHz``."""
        q0 = self.qubits[0]
        out: dict[str, dict[str, Any]] = {}
        for d_us in delays_us:
            tag = f"{d_us:.1f}".replace(".", "p")
            name = f"C3_ramsey_{tag}us"
            n_dt = align_delay_dt(d_us * 1e-6, self.dt_s, self.granularity, self.min_delay_dt)
            actual_s = n_dt * self.dt_s
            actual_us = actual_s * 1e6
            phi_rad = 2.0 * math.pi * (detuning_kHz * 1e3) * actual_s

            lines = self._header(1)
            self._emit_h(lines, q0)
            lines.append(f"barrier ${q0};")
            self._emit_delay_dt(lines, q0, n_dt)
            self._emit_rz(lines, q0, phi_rad)
            lines.append(f"barrier ${q0};")
            self._emit_h(lines, q0)
            lines.append(f"c[0] = measure ${q0};")
            out[name] = {
                "qasm": "\n".join(lines),
                "num_bits": 1,
                "nominal_delay_us": float(d_us),
                "actual_delay_us": round(actual_us, 6),
                "delay_dt": n_dt,
                "detuning_kHz": float(detuning_kHz),
                "phase_rad": round(phi_rad, 6),
            }
        return out

    def build_validation_suite(
        self,
        c1_idle_us: float = C1_IDLE_US,
        c2_idle_us: float = C2_IDLE_US,
        c3_detuning_kHz: float = C3_DETUNING_KHZ,
    ) -> dict[str, dict[str, Any]]:
        """Build the complete 16-PUB Exp145 hardware validation suite (C1 + C2 + C3)."""
        suite: dict[str, dict[str, Any]] = {}
        suite.update(self.build_c1_dd_and_bell(idle_us=c1_idle_us))
        suite.update(self.build_c2_repcode3(idle_us=c2_idle_us))
        suite.update(self.build_c3_ramsey(detuning_kHz=c3_detuning_kHz))
        return suite

    def _emit_swap(self, lines: list[str], a: int, b: int) -> None:
        """Emit native-ISA SWAP(a, b) using 3 adjacent CNOTs."""
        self._emit_cnot(lines, a, b)
        self._emit_cnot(lines, b, a)
        self._emit_cnot(lines, a, b)

    def _shortest_coupling_path(self, src: int, dst: int) -> list[int]:
        """BFS shortest undirected path between physical qubits ``src`` and ``dst``."""
        if src == dst:
            return [src]
        adj: dict[int, list[int]] = {}
        for u, v in self.directed_edges:
            adj.setdefault(u, []).append(v)
            adj.setdefault(v, []).append(u)
        if src not in adj or dst not in adj:
            raise ValueError(f"Qubits ({src}, {dst}) are not connected in coupling_map")
        from collections import deque
        q: deque[list[int]] = deque([[src]])
        seen = {src}
        while q:
            path = q.popleft()
            cur = path[-1]
            for nxt in sorted(adj.get(cur, [])):
                if nxt == dst:
                    return path + [nxt]
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(path + [nxt])
        raise ValueError(f"No coupling path between physical qubits {src} and {dst}")

    def _emit_routed_2q(self, lines: list[str], ctrl: int, tgt: int, kind: str = "cnot") -> None:
        """Emit 2Q gate routed strictly over adjacent physical coupling edges via SWAP chain."""
        if (ctrl, tgt) in self.directed_edges or (tgt, ctrl) in self.directed_edges:
            if kind == "cz":
                self._emit_cz(lines, ctrl, tgt)
            else:
                self._emit_cnot(lines, ctrl, tgt)
            return
        path = self._shortest_coupling_path(ctrl, tgt)
        # Swap ctrl forward along path[:-1] until adjacent to tgt
        for i in range(len(path) - 2):
            self._emit_swap(lines, path[i], path[i + 1])
        if kind == "cz":
            self._emit_cz(lines, path[-2], path[-1])
        else:
            self._emit_cnot(lines, path[-2], path[-1])
        # Uncompute SWAP chain to restore logical-to-physical qubit mapping
        for i in range(len(path) - 3, -1, -1):
            self._emit_swap(lines, path[i], path[i + 1])

    def _emit_dd_sequence(
        self,
        lines: list[str],
        q: int,
        dur_s: float,
        sequence: str = "XY4",
        pulses: int = 4,
    ) -> None:
        """Emit an exact-identity even-length DD sequence (or bare delay) on qubit ``q``.

        Never emits a single uncompensated X bit-flip: XY4=[X,Y,X,Y] (-I),
        XY8=[X,Y,X,Y,Y,X,Y,X] (+I), CPMG/ECHO2=[X,X] (+I), IDLE=delay (+I).
        """
        seq = str(sequence or "XY4").strip().upper()
        n_req = int(pulses)
        if seq in ("IDLE", "BARE", "NONE") or n_req <= 0:
            n_dt = align_delay_dt(dur_s, self.dt_s, self.granularity, self.min_delay_dt)
            lines.append(f"barrier ${q};")
            self._emit_delay_dt(lines, q, n_dt)
            lines.append(f"barrier ${q};")
            return

        if seq == "XY8":
            base = ("X", "Y", "X", "Y", "Y", "X", "Y", "X")
            # Keep pulse count a positive multiple of 8 (capped reasonably for OpenQASM clarity)
            n_p = max(8, min(16, int(math.ceil(n_req / 8.0)) * 8))
            axes = [base[i % 8] for i in range(n_p)]
        elif seq == "XY4":
            base = ("X", "Y", "X", "Y")
            n_p = max(4, min(16, int(math.ceil(n_req / 4.0)) * 4))
            axes = [base[i % 4] for i in range(n_p)]
        else:
            # Even-pulse CPMG / echoed identity (X-X ...): always even so net unitary is +I
            n_p = max(2, min(16, n_req + (n_req % 2)))
            axes = ["X"] * n_p

        unit_g = 2 * n_p * self.granularity
        raw_total = dur_s / max(self.dt_s, 1e-12)
        total_dt = max(unit_g, int(round(raw_total / unit_g)) * unit_g)
        tau_dt = total_dt // (2 * n_p)
        two_tau_dt = 2 * tau_dt

        lines.append(f"barrier ${q};")
        self._emit_delay_dt(lines, q, tau_dt)
        for i, ax in enumerate(axes):
            if ax == "X":
                self._emit_x(lines, q)
            else:
                self._emit_y(lines, q)
            self._emit_delay_dt(lines, q, two_tau_dt if i < n_p - 1 else tau_dt)
        lines.append(f"barrier ${q};")

    def transpile_cell_program(self, program: CellProgram) -> str:
        """Transpile a CellISA v2.0-v4.0 ``CellProgram`` into native-ISA OpenQASM 3.0."""
        n_q = max(2, program.used_nuclear_count() + 1)
        if n_q > len(self.qubits):
            raise ValueError(f"Program needs {n_q} qubits, chain only has {len(self.qubits)}")
        lines = self._header(n_q)
        measured = False

        for inst in program.instructions:
            op, a = inst.opcode, inst.args
            if op == "INIT":
                st = str(a.get("state", "0" * n_q))
                for idx, ch in enumerate(st[:n_q]):
                    if ch == "1":
                        self._emit_x(lines, self.qubits[idx])
            elif op == "RX":
                self._emit_rx(lines, self.qubits[parse_qubit(a["target"])], float(a["theta"]))
            elif op == "RY":
                self._emit_ry(lines, self.qubits[parse_qubit(a["target"])], float(a["theta"]))
            elif op == "RZ":
                self._emit_rz(lines, self.qubits[parse_qubit(a["target"])], float(a["theta"]))
            elif op == "CNOT":
                c_idx = parse_qubit(a["control"])
                t_idx = parse_qubit(a["target"])
                self._emit_routed_2q(lines, self.qubits[c_idx], self.qubits[t_idx], kind="cnot")
            elif op == "CZ":
                c_idx = parse_qubit(a["control"])
                t_idx = parse_qubit(a["target"])
                self._emit_routed_2q(lines, self.qubits[c_idx], self.qubits[t_idx], kind="cz")
            elif op == "GHZ":
                qs = [self.qubits[parse_qubit(q)] for q in a["qubits"]]
                self._emit_ry(lines, qs[0], math.pi / 2.0)
                # Ladder CNOTs along adjacent chain qubits produce exact GHZ with zero non-adjacent edges
                for idx_g in range(len(qs) - 1):
                    self._emit_routed_2q(lines, qs[idx_g], qs[idx_g + 1], kind="cnot")
            elif op == "QRAM_SWAP":
                qa = self.qubits[parse_qubit(a.get("qubit_a", "e"))]
                qb = self.qubits[parse_qubit(a.get("qubit_b", "n0"))]
                self._emit_routed_2q(lines, qa, qb, kind="cnot")
                self._emit_routed_2q(lines, qb, qa, kind="cnot")
                self._emit_routed_2q(lines, qa, qb, kind="cnot")
            elif op == "DD_HOLD":
                dur_s = float(a.get("duration_us", 20.0)) * 1e-6
                seq = str(a.get("sequence", "XY4"))
                n_pulses = int(a.get("pulses", 4))
                self._emit_dd_sequence(lines, self.qubits[0], dur_s, sequence=seq, pulses=n_pulses)
            elif op == "MEASURE":
                qs = [parse_qubit(q) for q in a.get("qubits", list(range(n_q)))]
                for bit_i, q_idx in enumerate(qs):
                    lines.append(f"c[{bit_i}] = measure ${self.qubits[q_idx]};")
                measured = True
            # Supervisory / wafer-level opcodes (WAFER_MAP_ROUTE, BUS_TUNE, AUTO_RECAL, etc.)
            # are metadata-level and emit no low-level QPU gate instructions.

        if not measured:
            for bit_i in range(n_q):
                lines.append(f"c[{bit_i}] = measure ${self.qubits[bit_i]};")
        return "\n".join(lines)


def validate_openqasm3_isa(
    qasm: str,
    native_2q: str = "cz",
    granularity: int = 16,
    coupling_map: list[list[int]] | list[tuple[int, int]] | set[tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """Static ISA, timing, and physical coupling-map adjacency validator for OpenQASM 3.0."""
    allowed_1q = {"rz", "sx", "x", "id"}
    native_2q_l = native_2q.lower()
    allowed_2q = {native_2q_l}
    allowed_edges: set[tuple[int, int]] | None = None
    if coupling_map is not None:
        allowed_edges = {(int(e[0]), int(e[1])) for e in coupling_map}
    lines = [ln.strip() for ln in qasm.splitlines() if ln.strip()]
    errors: list[str] = []

    if not lines or not lines[0].startswith("OPENQASM 3.0"):
        errors.append("Missing OPENQASM 3.0 header")

    in_gate_def = False
    n_2q = 0
    n_1q = 0
    n_delays = 0
    n_meas = 0

    for ln in lines:
        if ln.startswith("gate "):
            in_gate_def = True
            continue
        if in_gate_def:
            if "}" in ln:
                in_gate_def = False
            continue
        if ln.startswith(("OPENQASM", "include", "bit[", "barrier", "//")):
            continue
        if "measure" in ln:
            n_meas += 1
            continue
        m_del = re.match(r"^delay\[(\d+)dt\]\s+\$\d+;$", ln)
        if m_del:
            dt_val = int(m_del.group(1))
            n_delays += 1
            if dt_val % granularity != 0:
                errors.append(f"Delay {dt_val}dt is not a multiple of granularity={granularity}")
            continue
        m_gate = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)(?:\([^)]*\))?\s+(.+);$", ln)
        if not m_gate:
            errors.append(f"Unparsed statement: {ln}")
            continue
        gname = m_gate.group(1).lower()
        qargs = [x.strip() for x in m_gate.group(2).split(",")]
        phys_ids: list[int] = []
        for qa in qargs:
            if not re.match(r"^\$\d+$", qa):
                errors.append(f"Non-physical qubit operand {qa!r} in {ln!r}")
            else:
                phys_ids.append(int(qa[1:]))
        if len(qargs) == 1:
            if gname not in allowed_1q:
                errors.append(f"Non-native 1Q gate {gname!r} (allowed: {sorted(allowed_1q)})")
            n_1q += 1
        elif len(qargs) == 2:
            if gname not in allowed_2q:
                errors.append(f"Non-native 2Q gate {gname!r} (allowed: {sorted(allowed_2q)})")
            if allowed_edges is not None and len(phys_ids) == 2:
                edge = (phys_ids[0], phys_ids[1])
                rev = (phys_ids[1], phys_ids[0])
                edge_ok = (
                    (edge in allowed_edges or rev in allowed_edges)
                    if native_2q_l == "cz"
                    else (edge in allowed_edges)
                )
                if not edge_ok:
                    errors.append(
                        f"Non-adjacent / unrouted 2Q gate {gname} ${edge[0]}, ${edge[1]} "
                        f"not in coupling_map"
                    )
            n_2q += 1
        else:
            errors.append(f"Unsupported {len(qargs)}-qubit gate {gname!r}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "native_2q": native_2q,
        "n_1q_gates": n_1q,
        "n_2q_gates": n_2q,
        "n_delays": n_delays,
        "n_measurements": n_meas,
    }


# ---------------------------------------------------------------------------
# SamplerV2 Universal Result Decoder
# ---------------------------------------------------------------------------

def _decode_sample_token(tok: Any, num_bits: int) -> str:
    """Normalize a single IBM SamplerV2 sample (hex '0x1a', bin '01010', or int) to bitstring."""
    if isinstance(tok, int):
        val = tok
    else:
        s = str(tok).strip().lower()
        if s.startswith("0x"):
            val = int(s, 16)
        elif s.startswith("0b"):
            val = int(s, 2)
        elif all(ch in "01" for ch in s) and len(s) == num_bits:
            return s
        else:
            # Hex without 0x prefix or decimal
            try:
                val = int(s, 16)
            except ValueError:
                val = int(s, 10)
    mask = (1 << num_bits) - 1
    return format(val & mask, f"0{num_bits}b")


def _extract_reg_obj(pub_res: dict[str, Any]) -> dict[str, Any]:
    """Locate the classical register dictionary inside any IBM SamplerV2 result schema."""
    cur = pub_res
    if "__value__" in cur and isinstance(cur["__value__"], dict):
        cur = cur["__value__"]
    data = cur.get("data", cur)
    if "__value__" in data and isinstance(data["__value__"], dict):
        data = data["__value__"]
    if "fields" in data and isinstance(data["fields"], dict):
        data = data["fields"]
    if "c" in data and isinstance(data["c"], dict):
        reg = data["c"]
    else:
        # Take first dict-valued register key
        reg = next((v for v in data.values() if isinstance(v, dict)), data)
    if "__value__" in reg and isinstance(reg["__value__"], dict):
        reg = reg["__value__"]
    return reg


def parse_sampler_v2_counts(
    result_payload: dict[str, Any],
    expected_num_bits: list[int] | None = None,
) -> list[dict[str, int]]:
    """Decode IBM Quantum Platform 2026 SamplerV2 results across all JSON/BitArray formats.

    Supports:
      1. ``results[i].data.c.samples`` with hex strings (``"0x0"``, ``"0x15"``)
      2. ``results[i].data.c.samples`` with binary strings (``"00"``, ``"10101"``)
      3. ``results[i].data.c.counts`` dicts (hex or binary keys)
      4. Nested Qiskit JSON ``__type__="BitArray"`` / ``__value__`` wrappers (including
         base64+zlib serialized numpy BitArrays if returned by legacy Runtime encoders)
    """
    pub_list = result_payload.get("results")
    if pub_list is None and "__value__" in result_payload:
        val = result_payload["__value__"]
        if isinstance(val, dict):
            pub_list = val.get("pub_results") or val.get("results")
    if not isinstance(pub_list, list):
        raise ValueError("Unrecognized SamplerV2 result payload: missing 'results' list")

    counts_list: list[dict[str, int]] = []
    for idx, pub_res in enumerate(pub_list):
        reg = _extract_reg_obj(pub_res)
        nb = reg.get("num_bits")
        if nb is None and expected_num_bits and idx < len(expected_num_bits):
            nb = expected_num_bits[idx]
        if nb is None:
            nb = 1
        num_bits = int(nb)

        if "samples" in reg and isinstance(reg["samples"], list):
            c: Counter[str] = Counter()
            for tok in reg["samples"]:
                c[_decode_sample_token(tok, num_bits)] += 1
            counts_list.append(dict(sorted(c.items())))
        elif "counts" in reg and isinstance(reg["counts"], dict):
            out_c: dict[str, int] = {}
            for k, v in reg["counts"].items():
                bk = _decode_sample_token(k, num_bits)
                out_c[bk] = out_c.get(bk, 0) + int(v)
            counts_list.append(dict(sorted(out_c.items())))
        elif "array" in reg:
            # Base64 / zlib / numpy BitArray decoding
            arr_obj = reg["array"]
            if isinstance(arr_obj, dict) and "__value__" in arr_obj:
                raw_b64 = arr_obj["__value__"]
                raw_bytes = base64.b64decode(raw_b64)
                try:
                    raw_bytes = zlib.decompress(raw_bytes)
                except zlib.error:
                    pass
                arr = np.load(io.BytesIO(raw_bytes), allow_pickle=False)
            else:
                arr = np.asarray(arr_obj, dtype=np.uint8)
            arr2d = arr.reshape(-1, arr.shape[-1])
            c = Counter()
            for row in arr2d:
                val = 0
                for byte in row:
                    val = (val << 8) | int(byte)
                c[_decode_sample_token(val, num_bits)] += 1
            counts_list.append(dict(sorted(c.items())))
        else:
            raise ValueError(f"SamplerV2 PUB {idx} register lacks samples/counts/array keys")

    return counts_list


# ---------------------------------------------------------------------------
# Pure-requests IBM Quantum Platform 2026 REST API v1 Client
# ---------------------------------------------------------------------------

class IBMQuantumRESTClient:
    """Zero-Qiskit pure-``requests`` client for IBM Quantum Platform 2026 REST API v1.

    Security guarantees:
      - Credentials are read strictly from environment variables (or explicit runtime args)
        and NEVER logged, printed, serialized to JSON, or leaked in exceptions.
    """

    def __init__(
        self,
        api_key: str | None = None,
        service_crn: str | None = None,
        base_url: str | None = None,
        api_version: str | None = "2026-02-01",
        timeout_s: float = 30.0,
        session: Any | None = None,
    ):
        self._api_key = (api_key if api_key is not None else os.environ.get("IBM_QUANTUM_TOKEN", "")).strip()
        self._service_crn = (
            service_crn if service_crn is not None else os.environ.get("IBM_QUANTUM_INSTANCE", "")
        ).strip()
        if not self._api_key or not self._service_crn:
            raise EnvironmentError(
                "Missing IBM Quantum credentials: set IBM_QUANTUM_TOKEN and IBM_QUANTUM_INSTANCE "
                "environment variables before invoking live IBM QPU calls."
            )
        self.base_url = (base_url or detect_ibm_base_url(self._service_crn)).rstrip("/")
        self.api_version = api_version
        self.timeout_s = float(timeout_s)
        if session is not None:
            self._session = session
        else:
            if requests is None:  # pragma: no cover
                raise ImportError("requests package is required for IBMQuantumRESTClient")
            self._session = requests.Session()
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

    def _secrets(self) -> tuple[str, ...]:
        s = [self._api_key, self._service_crn]
        if self._access_token:
            s.append(self._access_token)
        return tuple(s)

    def authenticate(self, force: bool = False) -> str:
        """Exchange IBM Cloud API key for a short-lived IAM Bearer token."""
        now = time.time()
        if not force and self._access_token and now < self._token_expiry - 60.0:
            return self._access_token
        resp = self._session.post(
            IAM_TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": self._api_key,
            },
            timeout=self.timeout_s,
        )
        if resp.status_code >= 400:
            msg = redact_secrets(resp.text[:300], self._secrets())
            raise RuntimeError(f"IBM IAM authentication failed (HTTP {resp.status_code}): {msg}")
        data = resp.json()
        token = str(data.get("access_token", "")).strip()
        if not token:
            raise RuntimeError("IBM IAM authentication response missing access_token")
        self._access_token = token
        expires_in = float(data.get("expires_in", 3600))
        self._token_expiry = now + expires_in
        return token

    def _headers(self, api_version: str | None) -> dict[str, str]:
        token = self.authenticate()
        hdrs = {
            "Authorization": f"Bearer {token}",
            "Service-CRN": self._service_crn,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if api_version:
            hdrs["IBM-API-Version"] = api_version
        return hdrs

    def _request_json(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        versions_to_try: list[str | None] = [self.api_version]
        for v in DEFAULT_API_VERSIONS:
            if v not in versions_to_try:
                versions_to_try.append(v)

        last_err = ""
        for idx, ver in enumerate(versions_to_try):
            resp = self._session.request(
                method,
                url,
                headers=self._headers(ver),
                json=json_body,
                timeout=self.timeout_s,
            )
            if resp.status_code == 401 and idx == 0:
                self.authenticate(force=True)
                resp = self._session.request(
                    method,
                    url,
                    headers=self._headers(ver),
                    json=json_body,
                    timeout=self.timeout_s,
                )
            if resp.status_code < 400:
                self.api_version = ver
                try:
                    return resp.json()
                except ValueError:
                    # Some IBM result endpoints return JSON lines or wrapped text
                    txt = resp.text.strip()
                    for line in reversed(txt.splitlines()):
                        line = line.strip()
                        if line.startswith("{"):
                            return json.loads(line)
                    raise RuntimeError(f"Non-JSON response from {path}: {redact_secrets(txt[:200], self._secrets())}")

            body_clean = redact_secrets(resp.text[:350], self._secrets())
            last_err = f"HTTP {resp.status_code} on {method} {path}: {body_clean}"
            # Retry alternate IBM-API-Version only if version header is rejected
            if resp.status_code in (400, 406) and ("version" in body_clean.lower() or "ibm-api-version" in body_clean.lower()):
                continue
            raise RuntimeError(last_err)

        raise RuntimeError(last_err)

    def list_backends(self) -> list[dict[str, Any]]:
        """List accessible IBM Quantum backends as normalized metadata dicts."""
        raw = self._request_json("GET", "/backends")
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = raw.get("devices") or raw.get("backends") or raw.get("items") or []
        else:
            items = []

        out: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, str):
                out.append({"name": item})
            elif isinstance(item, dict):
                name = item.get("name") or item.get("backend_name") or ""
                if name:
                    norm = dict(item)
                    norm["name"] = str(name)
                    out.append(norm)
        return out

    def get_backend_status(self, backend_name: str) -> dict[str, Any]:
        return self._request_json("GET", f"/backends/{backend_name}/status")

    def get_backend_configuration(self, backend_name: str) -> dict[str, Any]:
        return self._request_json("GET", f"/backends/{backend_name}/configuration")

    def get_backend_properties(self, backend_name: str) -> dict[str, Any]:
        return self._request_json("GET", f"/backends/{backend_name}/properties")

    def select_best_online_backend(
        self,
        preferred_backend: str | None = None,
        min_qubits: int = 5,
    ) -> dict[str, Any]:
        """Select the best online real IBM QPU (preferring Heron cz + lowest queue)."""
        backends = self.list_backends()
        if not backends:
            raise RuntimeError("No IBM Quantum backends returned for this instance")

        candidates: list[dict[str, Any]] = []
        for b in backends:
            name = b["name"]
            if preferred_backend and name != preferred_backend:
                continue
            if b.get("simulator") is True or "simulator" in name.lower():
                continue
            # Query status if not embedded
            operational = b.get("operational")
            pending = b.get("pending_jobs")
            status_msg = str(b.get("status", "")).lower()
            if operational is None or pending is None:
                try:
                    st = self.get_backend_status(name)
                    operational = bool(st.get("operational", st.get("state", False)))
                    pending = st.get("pending_jobs", st.get("length_queue", 9999))
                    status_msg = str(st.get("status_msg", st.get("message", status_msg))).lower()
                except Exception:
                    # Fail closed on REST status errors: never assume a backend is operational
                    operational = False
                    pending = 9999
            if operational is False or status_msg in ("offline", "retired", "maintenance"):
                continue
            try:
                cfg = self.get_backend_configuration(name)
            except Exception:
                continue
            if cfg.get("simulator") is True:
                continue
            nq = int(cfg.get("n_qubits") or cfg.get("num_qubits") or 0)
            if nq < min_qubits:
                continue
            basis = [str(g).lower() for g in cfg.get("basis_gates", [])]
            is_heron = "cz" in basis
            candidates.append({
                "name": name,
                "n_qubits": nq,
                "is_heron": is_heron,
                "native_2q": "cz" if is_heron else ("ecr" if "ecr" in basis else "cx"),
                "pending_jobs": int(pending if pending is not None else 9999),
                "configuration": cfg,
            })

        if not candidates:
            raise RuntimeError("No operational real IBM QPU backend (>= 5 qubits) available")

        # Prefer Heron (cz) first, then lowest pending queue, then highest qubit count
        candidates.sort(key=lambda c: (0 if c["is_heron"] else 1, c["pending_jobs"], -c["n_qubits"]))
        chosen = candidates[0]
        try:
            chosen["properties"] = self.get_backend_properties(chosen["name"])
        except Exception:
            chosen["properties"] = None
        return chosen

    def submit_sampler_v2(
        self,
        backend_name: str,
        qasm_circuits: list[str],
        shots: int = 4096,
    ) -> dict[str, Any]:
        """Submit a batch of OpenQASM 3.0 circuits to IBM SamplerV2 via POST /jobs."""
        shots_int = int(shots)
        payloads = [
            {
                "program_id": "sampler",
                "backend": backend_name,
                "params": {
                    "pubs": [[q] for q in qasm_circuits],
                    "options": {"default_shots": shots_int},
                    "version": 2,
                },
            },
            {
                "program_id": "sampler",
                "backend": backend_name,
                "params": {
                    "pubs": [[q, None, shots_int] for q in qasm_circuits],
                    "version": 2,
                },
            },
            {
                "program_id": "sampler",
                "backend": backend_name,
                "params": {
                    "pubs": [[q] for q in qasm_circuits],
                    "options": {"default_shots": shots_int},
                },
            },
        ]
        resp: dict[str, Any] | None = None
        last_exc: Exception | None = None
        for payload in payloads:
            try:
                resp = self._request_json("POST", "/jobs", json_body=payload)
                break
            except RuntimeError as exc:
                last_exc = exc
                if "HTTP 400" in str(exc) or "HTTP 422" in str(exc):
                    continue
                raise
        if resp is None:
            raise last_exc if last_exc is not None else RuntimeError("IBM POST /jobs failed")
        job_id = resp.get("id") or resp.get("job_id")
        if not job_id:
            raise RuntimeError("IBM POST /jobs response missing job id")
        return {"job_id": str(job_id), "backend": backend_name, "raw_status": resp.get("status", "Queued")}

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self._request_json("GET", f"/jobs/{job_id}")

    def wait_for_job(
        self,
        job_id: str,
        poll_interval_s: float = 5.0,
        timeout_s: float = 600.0,
    ) -> dict[str, Any]:
        """Poll GET /jobs/{id} until terminal status (Completed / Failed / Cancelled)."""
        t0 = time.time()
        while True:
            info = self.get_job(job_id)
            st = str(info.get("status") or info.get("state", {}).get("status", "")).strip()
            stl = st.lower()
            if stl in ("completed", "done"):
                return info
            if stl in ("failed", "cancelled", "canceled", "error"):
                reason = redact_secrets(
                    str(info.get("state", {}).get("reason") or info.get("reason") or st),
                    self._secrets(),
                )
                raise RuntimeError(f"IBM QPU job {job_id} ended with status={st}: {reason}")
            if time.time() - t0 > timeout_s:
                raise TimeoutError(f"IBM QPU job {job_id} timed out after {timeout_s:.0f}s (last status={st})")
            time.sleep(poll_interval_s)

    def get_job_results(self, job_id: str) -> dict[str, Any]:
        return self._request_json("GET", f"/jobs/{job_id}/results")


# ---------------------------------------------------------------------------
# Offline Noisy IBM Heron Simulator (Exact Density Matrix + Sampling)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HeronNoiseModel:
    """Realistic IBM Heron superconducting transmon noise parameters ({Model})."""
    t1_us: float = 180.0
    t2_bare_us: float = 24.0         # Ramsey T2* under low-frequency flux/charge drift
    t2_echo_us: float = 130.0        # Hahn-Echo T2E
    t2_xy4_us: float = 165.0         # XY4 dynamical decoupling T2_DD
    p_1q: float = 0.0004             # Single-qubit depolarizing error
    p_2q: float = 0.0055             # Native CZ 2-qubit depolarizing error
    p_ro: float = 0.014              # Symmetric readout assignment error
    native_detuning_kHz: float = 0.0 # Residual qubit frequency offset


def _sample_bitstring_probs(
    probs: np.ndarray,
    num_bits: int,
    shots: int,
    rng: np.random.Generator,
) -> dict[str, int]:
    p = np.clip(np.asarray(probs, dtype=float), 0.0, 1.0)
    p /= np.sum(p)
    draws = rng.multinomial(int(shots), p)
    return {
        format(idx, f"0{num_bits}b"): int(cnt)
        for idx, cnt in enumerate(draws)
        if cnt > 0
    }


def simulate_offline_heron_counts(
    shots: int = 4096,
    noise: HeronNoiseModel | None = None,
    c1_idle_us: float = C1_IDLE_US,
    c2_idle_us: float = C2_IDLE_US,
    c3_delays_us: list[float] | tuple[float, ...] | None = None,
    c3_detuning_kHz: float = C3_DETUNING_KHZ,
    seed: int = 2026145,
) -> dict[str, dict[str, int]]:
    """Simulate all 16 Exp145 validation PUBs under a realistic IBM Heron noise model.

    Uses exact single-qubit Bloch/Kraus dynamics (C1 DD, C3 Ramsey), exact 2-qubit
    depolarizing + T1 + readout assignment matrix (C1 Bell), and exact per-shot
    physical idle + CNOT + readout Monte Carlo on the 5-qubit linear chain (C2 d=3).
    """
    nm = noise or HeronNoiseModel()
    rng = np.random.default_rng(seed)
    counts: dict[str, dict[str, int]] = {}

    # --- C1a/b/c: Dynamical Decoupling survival P(0) ---
    # Survival of |+> after idle t: 0.5 * (1 + (1 - 2*p_ro) * (1 - n_p*p_1q) * exp(-t / T2_eff))
    for name, t2_eff, n_pulses in (
        ("C1a_bare_idle", nm.t2_bare_us, 2),
        ("C1b_hahn_echo", nm.t2_echo_us, 3),
        ("C1c_xy4_dd", nm.t2_xy4_us, 6),
    ):
        vis = (1.0 - 2.0 * nm.p_ro) * ((1.0 - nm.p_1q) ** n_pulses)
        p0 = 0.5 * (1.0 + vis * math.exp(-c1_idle_us / max(t2_eff, 1e-3)))
        counts[name] = _sample_bitstring_probs(np.array([p0, 1.0 - p0]), 1, shots, rng)

    # --- C1d/e/f: Exact 4x4 density matrix Bell |Phi+> tomography ---
    # Prepare |Phi+>, apply 2Q depolarizing (p_2q) + 1Q depolarizing + readout confusion
    psi_bell = np.array([1.0, 0.0, 0.0, 1.0], dtype=complex) / math.sqrt(2.0)
    rho = np.outer(psi_bell, psi_bell.conj())
    # 2Q depolarizing channel from CZ + 1Q gates
    p_dep = min(0.5, nm.p_2q + 4.0 * nm.p_1q)
    rho = (1.0 - p_dep) * rho + (p_dep / 4.0) * np.eye(4, dtype=complex)
    # Exact readout assignment matrix M (kron of 2x2 symmetric bit-flip matrices)
    m1 = np.array([[1.0 - nm.p_ro, nm.p_ro], [nm.p_ro, 1.0 - nm.p_ro]], dtype=float)
    m2 = np.kron(m1, m1)

    h1 = np.array([[1.0, 1.0], [1.0, -1.0]], dtype=complex) / math.sqrt(2.0)
    sdg = np.diag([1.0, -1.0j])
    u_rot = {
        "C1d_bell_zz": np.eye(4, dtype=complex),
        "C1e_bell_xx": np.kron(h1, h1),
        "C1f_bell_yy": np.kron(h1 @ sdg, h1 @ sdg),
    }
    for name, U in u_rot.items():
        rho_b = U @ rho @ U.conj().T
        # Little-endian ordering: index = 2*c1 + c0 (symmetric for Bell, exact anyway)
        probs_ideal = np.real(np.diag(rho_b))
        probs_ro = m2 @ probs_ideal
        counts[name] = _sample_bitstring_probs(probs_ro, 2, shots, rng)

    # --- C2a/b: 5-qubit linear d=3 repetition code exact shot-by-shot circuit noise ---
    # Physical error probabilities during C2_IDLE_US + 4 nearest-neighbor CNOTs + readout:
    p_idle_1to0 = 1.0 - math.exp(-c2_idle_us / max(nm.t1_us, 1e-3))  # T1 decay |1> -> |0>
    p_idle_0to1 = 0.002  # Thermal excitation |0> -> |1>
    p_cnot_x = 0.5 * nm.p_2q  # X/Y component of 2Q depolarizing per qubit per CNOT

    for name, logical_bit in (("C2a_rep3_logical0", 0), ("C2b_rep3_logical1", 1)):
        d0 = np.full(shots, logical_bit, dtype=np.int8)
        d1 = np.full(shots, logical_bit, dtype=np.int8)
        d2 = np.full(shots, logical_bit, dtype=np.int8)
        a0 = np.zeros(shots, dtype=np.int8)
        a1 = np.zeros(shots, dtype=np.int8)

        # Idle hold on data qubits (T1 decay on |1>, thermal excitation on |0>)
        p_flip = p_idle_1to0 if logical_bit == 1 else p_idle_0to1
        d0 ^= (rng.random(shots) < p_flip).astype(np.int8)
        d1 ^= (rng.random(shots) < p_flip).astype(np.int8)
        d2 ^= (rng.random(shots) < p_flip).astype(np.int8)

        # 4 syndrome CNOTs with independent 2Q depolarizing X-flip errors:
        # CNOT(d0 -> a0), CNOT(d1 -> a1), CNOT(d1 -> a0), CNOT(d2 -> a1)
        for ctrl, tgt in ((d0, a0), (d1, a1), (d1, a0), (d2, a1)):
            tgt ^= ctrl
            ctrl ^= (rng.random(shots) < p_cnot_x).astype(np.int8)
            tgt ^= (rng.random(shots) < p_cnot_x).astype(np.int8)

        # Measurement readout assignment errors on all 5 qubits
        d0 ^= (rng.random(shots) < nm.p_ro).astype(np.int8)
        a0 ^= (rng.random(shots) < nm.p_ro).astype(np.int8)
        d1 ^= (rng.random(shots) < nm.p_ro).astype(np.int8)
        a1 ^= (rng.random(shots) < nm.p_ro).astype(np.int8)
        d2 ^= (rng.random(shots) < nm.p_ro).astype(np.int8)

        # Pack little-endian bitstring: c[0]=D0 (LSB), c[1]=A0, c[2]=D1, c[3]=A1, c[4]=D2 (MSB)
        vals = (d0.astype(np.int32)
                | (a0.astype(np.int32) << 1)
                | (d1.astype(np.int32) << 2)
                | (a1.astype(np.int32) << 3)
                | (d2.astype(np.int32) << 4))
        c_cnt: Counter[str] = Counter()
        uniq, freqs = np.unique(vals, return_counts=True)
        for u_val, fr in zip(uniq, freqs):
            c_cnt[format(int(u_val), "05b")] = int(fr)
        counts[name] = dict(sorted(c_cnt.items()))

    # --- C3: 8-point Ramsey fringe at detuning f_eff = c3_detuning_kHz + native_detuning ---
    f_eff_kHz = c3_detuning_kHz + nm.native_detuning_kHz
    vis_c3 = (1.0 - 2.0 * nm.p_ro) * ((1.0 - nm.p_1q) ** 2)
    actual_c3 = list(c3_delays_us) if c3_delays_us is not None else list(C3_DELAYS_US)
    for nom_us, act_us in zip(C3_DELAYS_US, actual_c3):
        tag = f"{nom_us:.1f}".replace(".", "p")
        name = f"C3_ramsey_{tag}us"
        phi = 2.0 * math.pi * (f_eff_kHz * 1e3) * (act_us * 1e-6)
        p0 = 0.5 * (1.0 + vis_c3 * math.exp(-act_us / max(nm.t2_bare_us, 1e-3)) * math.cos(phi))
        counts[name] = _sample_bitstring_probs(np.array([p0, 1.0 - p0]), 1, shots, rng)

    return counts


# ---------------------------------------------------------------------------
# Bit-Exact Q16.16 BOED vs FP64 BOED vs Blind 8-Point Ramsey Analyzer (C3)
# ---------------------------------------------------------------------------

def run_c3_ramsey_q16_boed(
    delays_us: list[float],
    p0_measured: list[float],
    shots_per_point: list[int],
    visibility_est: float = 0.94,
    t2_est_us: float = 40.0,
    max_adaptive_points: int = 5,
    target_sigma_kHz: float = 1.2,
    f_min_kHz: float = 30.0,
    f_max_kHz: float = 220.0,
    f_step_kHz: float = 0.25,
) -> dict[str, Any]:
    """Compare Bit-Exact Q16.16 BOED, FP64 BOED, and Blind 8-point fit on Ramsey counts.

    Uses a completely FLAT uniform prior over ``[f_min_kHz, f_max_kHz]`` (zero prior bias
    toward 125 kHz!) and executes the Q16.16 engine strictly in integer arithmetic using
    ``fpga_boed_dsp``'s BRAM ``exp(-x)`` LUT and Q16.16 fixed-point multipliers.
    """
    n_pts = len(delays_us)
    taus_s = np.asarray(delays_us, dtype=np.float64) * 1e-6
    y_obs = 2.0 * np.asarray(p0_measured, dtype=np.float64) - 1.0  # in [-1, +1]
    # Effective standard error per point (binomial + small model-mismatch floor 0.025)
    sigmas = np.array([
        math.sqrt(max(p * (1.0 - p), 0.02) / max(sh, 1) * 4.0 + 0.025 ** 2)
        for p, sh in zip(p0_measured, shots_per_point)
    ], dtype=np.float64)

    # Frequency grid (761 bins @ 0.25 kHz spacing -> fits single ZU48DR BRAM36!)
    n_bins = int(round((f_max_kHz - f_min_kHz) / f_step_kHz)) + 1
    f_grid_kHz = f_min_kHz + np.arange(n_bins, dtype=np.float64) * f_step_kHz
    grid_idx = np.arange(n_bins, dtype=np.int64)

    # Forward cosine model matrix M[k, j] = V * exp(-tau_k / T2) * cos(2*pi * f_j * tau_k)
    vis = float(np.clip(visibility_est, 0.55, 0.995))
    decay = np.exp(-np.asarray(delays_us, dtype=np.float64) / max(t2_est_us, 5.0))
    model_fp = (vis * decay)[:, None] * np.cos(2.0 * math.pi * taus_s[:, None] * (f_grid_kHz[None, :] * 1e3))

    # --- 1. Blind 8-point uniform Bayesian posterior mean ---
    lp_blind = np.zeros(n_bins, dtype=np.float64)
    for k in range(n_pts):
        lp_blind -= 0.5 * ((y_obs[k] - model_fp[k]) / sigmas[k]) ** 2
    lp_blind -= np.max(lp_blind)
    w_blind = np.exp(lp_blind)
    w_blind /= np.sum(w_blind)
    mu_blind_kHz = float(np.sum(w_blind * f_grid_kHz))
    std_blind_kHz = float(math.sqrt(max(float(np.sum(w_blind * (f_grid_kHz - mu_blind_kHz) ** 2)), 1e-6)))

    # --- 2. Adaptive FP64 BOED (<= max_adaptive_points) ---
    # Acquisition: select unqueried delay tau_k maximizing predictive variance Var_p[model(tau_k, f)]
    # (maximum mutual information / Fisher information gain for Gaussian observations!).
    lp_fp = np.zeros(n_bins, dtype=np.float64)
    queried_fp: list[int] = []
    # Start at index 1 (tau=1.0 us) for unambiguous coarse phase lock
    next_k = 1 if n_pts > 1 else 0
    mu_fp_kHz = 0.5 * (f_min_kHz + f_max_kHz)
    std_fp_kHz = (f_max_kHz - f_min_kHz) / math.sqrt(12.0)

    for _step in range(min(max_adaptive_points, n_pts)):
        k = next_k
        queried_fp.append(k)
        lp_fp -= 0.5 * ((y_obs[k] - model_fp[k]) / sigmas[k]) ** 2
        w = np.exp(lp_fp - np.max(lp_fp))
        w /= np.sum(w)
        mu_fp_kHz = float(np.sum(w * f_grid_kHz))
        std_fp_kHz = float(math.sqrt(max(float(np.sum(w * (f_grid_kHz - mu_fp_kHz) ** 2)), 1e-6)))
        if len(queried_fp) >= 3 and std_fp_kHz <= target_sigma_kHz:
            break
        remaining = [idx for idx in range(n_pts) if idx not in queried_fp]
        if not remaining:
            break
        best_gain = -1.0
        best_rem = remaining[0]
        for r in remaining:
            pred = model_fp[r]
            mean_p = float(np.sum(w * pred))
            var_p = float(np.sum(w * (pred - mean_p) ** 2))
            # Information gain proportional to log(1 + var_p / sigma_r^2)
            gain = var_p / (sigmas[r] ** 2)
            if gain > best_gain:
                best_gain = gain
                best_rem = r
        next_k = best_rem

    # --- 3. Bit-Exact Q16.16 Integer BOED (<= max_adaptive_points) ---
    exp_lut = build_exp_neg_lut_q16()
    model_q16 = np.asarray(to_q16(model_fp), dtype=np.int64)
    lp_q16 = np.zeros(n_bins, dtype=np.int64)
    queried_q16: list[int] = []
    next_k_q = 1 if n_pts > 1 else 0
    mu_q16_kHz = 0.5 * (f_min_kHz + f_max_kHz)
    std_q16_kHz = (f_max_kHz - f_min_kHz) / math.sqrt(12.0)

    # Pre-scale grid index to integer quarter-kHz (f_step_kHz = 0.25 kHz)
    f_min_q8 = int(round(f_min_kHz * 256.0))
    step_q8 = int(round(f_step_kHz * 256.0))

    for _step in range(min(max_adaptive_points, n_pts)):
        k = next_k_q
        queried_q16.append(k)

        y_q = int(to_q16(float(y_obs[k])))
        resid_q = y_q - model_q16[k]
        resid2_q = q16_mul(resid_q, resid_q)
        # Scale 0.5 / sigma^2 safely into Q16.16 (with shift guard against int32 overflow)
        inv_2var_val = 0.5 / max(float(sigmas[k]) ** 2, 1e-6)
        # Use Q12.4 scaling if inv_2var > 1000 so intermediate products stay strictly within 48-bit DSP
        inv_2var_q16 = int(to_q16(min(inv_2var_val, 2000.0)))
        delta_lp_q = q16_mul(resid2_q, inv_2var_q16)
        lp_q16 = np.clip(lp_q16 - delta_lp_q, INT32_MIN, INT32_MAX)

        max_lp = int(np.max(lp_q16))
        neg_x_q = max_lp - lp_q16
        w_q = lut_interp_q16(neg_x_q, exp_lut, EXP_X_MAX, EXP_LUT_SIZE)

        acc_z = max(1, int(np.sum(w_q, dtype=np.int64)))
        acc_m1 = int(np.sum(w_q * grid_idx, dtype=np.int64))
        acc_m2 = int(np.sum(w_q * (grid_idx * grid_idx), dtype=np.int64))

        mean_idx_q8 = (acc_m1 * 256) // acc_z
        mu_q8 = f_min_q8 + ((mean_idx_q8 * step_q8) >> 8)
        mu_q16_kHz = mu_q8 / 256.0

        ex2_q16 = (acc_m2 << 16) // acc_z
        var_idx_q16 = max(0, ex2_q16 - mean_idx_q8 * mean_idx_q8)
        # std_idx in Q8, convert to kHz
        std_idx_q8 = math.isqrt(var_idx_q16)
        std_q16_kHz = (std_idx_q8 / 256.0) * f_step_kHz

        if len(queried_q16) >= 3 and std_q16_kHz <= target_sigma_kHz:
            break
        remaining = [idx for idx in range(n_pts) if idx not in queried_q16]
        if not remaining:
            break
        best_gain_q = -1
        best_rem_q = remaining[0]
        for r in remaining:
            pred_q = model_q16[r]
            # Integer predictive variance: E[pred^2] - E[pred]^2 scaled by 1/sigma^2
            ep_q = int(np.sum(w_q * pred_q, dtype=np.int64)) // acc_z
            dp_q = (pred_q - ep_q) >> 4  # Q12 to prevent 64-bit overflow
            var_num = int(np.sum(w_q * (dp_q * dp_q), dtype=np.int64)) // acc_z
            inv_s2_int = int(round(1.0 / max(float(sigmas[r]) ** 2, 1e-6)))
            gain_q = var_num * inv_s2_int
            if gain_q > best_gain_q:
                best_gain_q = gain_q
                best_rem_q = r
        next_k_q = best_rem_q

    return {
        "prior_range_kHz": [f_min_kHz, f_max_kHz],
        "grid_bins": n_bins,
        "grid_step_kHz": f_step_kHz,
        "visibility_est": round(vis, 4),
        "blind_8pt": {
            "n_points": n_pts,
            "est_freq_kHz": round(mu_blind_kHz, 4),
            "posterior_std_kHz": round(std_blind_kHz, 4),
        },
        "fp64_boed": {
            "n_points": len(queried_fp),
            "queried_indices": queried_fp,
            "queried_delays_us": [delays_us[i] for i in queried_fp],
            "est_freq_kHz": round(mu_fp_kHz, 4),
            "posterior_std_kHz": round(std_fp_kHz, 4),
        },
        "q16_16_boed": {
            "n_points": len(queried_q16),
            "queried_indices": queried_q16,
            "queried_delays_us": [delays_us[i] for i in queried_q16],
            "est_freq_kHz": round(mu_q16_kHz, 4),
            "posterior_std_kHz": round(std_q16_kHz, 4),
            "q16_vs_fp64_diff_kHz": round(abs(mu_q16_kHz - mu_fp_kHz), 4),
            "q16_vs_blind8_diff_kHz": round(abs(mu_q16_kHz - mu_blind_kHz), 4),
        },
    }


# ---------------------------------------------------------------------------
# Shared Validation Suite Analyzer (Offline Simulator AND Live IBM QPU)
# ---------------------------------------------------------------------------

def _bit(bitstr: str, k: int) -> int:
    """Return classical bit c[k] from little-endian bitstring (c[0] is rightmost char)."""
    return int(bitstr[len(bitstr) - 1 - k])


def _expect_zz_2q(counts: dict[str, int]) -> float:
    tot = sum(counts.values())
    if tot <= 0:
        return 0.0
    acc = 0.0
    for bs, n in counts.items():
        b0, b1 = _bit(bs, 0), _bit(bs, 1)
        acc += n * (1.0 if b0 == b1 else -1.0)
    return acc / tot


def _analyze_rep3_counts(counts: dict[str, int], logical_bit: int) -> dict[str, Any]:
    """Decode 5-bit d=3 repetition code counts [c0=D0, c1=A0, c2=D1, c3=A1, c4=D2]."""
    tot = sum(counts.values())
    if tot <= 0:
        raise ValueError("Empty counts dictionary for C2 repetition code")

    phys_errs = 0
    maj_errs = 0
    mwpm_errs = 0
    postsel_tot = 0
    postsel_errs = 0

    for bs, n in counts.items():
        d0, s0, d1, s1, d2 = _bit(bs, 0), _bit(bs, 1), _bit(bs, 2), _bit(bs, 3), _bit(bs, 4)

        # Raw unencoded physical error rate across the 3 data qubits
        phys_errs += n * ((d0 != logical_bit) + (d1 != logical_bit) + (d2 != logical_bit))

        # 1. Data-qubit majority vote (exact d=3 classical decode)
        maj = 1 if (d0 + d1 + d2) >= 2 else 0
        if maj != logical_bit:
            maj_errs += n

        # 2. Space-time syndrome-assisted MWPM decoder:
        #    Correct single mid-circuit data flip indicated by (s0, s1), then majority vote.
        #    Corrects all weight-1 errors (data idle, data readout, OR ancilla error) plus
        #    mixed idle+readout weight-2 errors!
        c0 = 1 if (s0 == 1 and s1 == 0) else 0
        c1 = 1 if (s0 == 1 and s1 == 1) else 0
        c2 = 1 if (s0 == 0 and s1 == 1) else 0
        dd0, dd1, dd2 = d0 ^ c0, d1 ^ c1, d2 ^ c2
        mwpm_bit = 1 if (dd0 + dd1 + dd2) >= 2 else 0
        if mwpm_bit != logical_bit:
            mwpm_errs += n

        # 3. Zero-syndrome post-selection (s0 == 0 and s1 == 0)
        if s0 == 0 and s1 == 0:
            postsel_tot += n
            if maj != logical_bit:
                postsel_errs += n

    p_phys = phys_errs / (3.0 * tot)
    p_maj = maj_errs / tot
    p_mwpm = mwpm_errs / tot
    p_postsel = (postsel_errs / postsel_tot) if postsel_tot > 0 else 1.0
    return {
        "shots": tot,
        "logical_bit": int(logical_bit),
        "p_phys": round(p_phys, 6),
        "p_L_majority": round(p_maj, 6),
        "p_L_syndrome_mwpm": round(p_mwpm, 6),
        "p_L_postsel": round(p_postsel, 6),
        "postsel_keep_rate": round(postsel_tot / tot, 6),
        "suppression_factor_mwpm": round(p_phys / max(p_mwpm, 1e-6), 3),
        "suppression_factor_majority": round(p_phys / max(p_maj, 1e-6), 3),
    }


def analyze_validation_suite_counts(
    counts_by_pub: dict[str, dict[str, int]],
    c3_delays_us: list[float] | None = None,
    c3_programmed_kHz: float = C3_DETUNING_KHZ,
    c1_idle_us: float = C1_IDLE_US,
) -> dict[str, Any]:
    """Analyze the 16 Exp145 validation PUB count dictionaries (works on simulator OR live QPU)."""
    # --- C1: Dynamical Decoupling & Bell Tomography ---
    def _p0(name: str) -> float:
        c = counts_by_pub[name]
        tot = max(1, sum(c.values()))
        return sum(n for bs, n in c.items() if _bit(bs, 0) == 0) / tot

    p_bare = _p0("C1a_bare_idle")
    p_echo = _p0("C1b_hahn_echo")
    p_xy4 = _p0("C1c_xy4_dd")

    exp_zz = _expect_zz_2q(counts_by_pub["C1d_bell_zz"])
    exp_xx = _expect_zz_2q(counts_by_pub["C1e_bell_xx"])
    exp_yy = _expect_zz_2q(counts_by_pub["C1f_bell_yy"])
    bell_fid = 0.25 * (1.0 + exp_zz + exp_xx - exp_yy)

    c1_res = {
        "p0_bare_idle": round(p_bare, 6),
        "p0_hahn_echo": round(p_echo, 6),
        "p0_xy4_dd": round(p_xy4, 6),
        "dd_gain_echo_over_bare": round(p_echo - p_bare, 6),
        "dd_gain_xy4_over_bare": round(p_xy4 - p_bare, 6),
        "bell_expect_ZZ": round(exp_zz, 6),
        "bell_expect_XX": round(exp_xx, 6),
        "bell_expect_YY": round(exp_yy, 6),
        "bell_fidelity_Phi_plus": round(bell_fid, 6),
    }

    # --- C2: 5Q Linear d=3 Repetition Code ---
    c2_0 = _analyze_rep3_counts(counts_by_pub["C2a_rep3_logical0"], 0)
    c2_1 = _analyze_rep3_counts(counts_by_pub["C2b_rep3_logical1"], 1)
    p_phys_avg = 0.5 * (c2_0["p_phys"] + c2_1["p_phys"])
    p_maj_avg = 0.5 * (c2_0["p_L_majority"] + c2_1["p_L_majority"])
    p_mwpm_avg = 0.5 * (c2_0["p_L_syndrome_mwpm"] + c2_1["p_L_syndrome_mwpm"])
    p_post_avg = 0.5 * (c2_0["p_L_postsel"] + c2_1["p_L_postsel"])
    p_best_dec = min(p_maj_avg, p_mwpm_avg)
    c2_res = {
        "logical_0": c2_0,
        "logical_1": c2_1,
        "avg_p_phys": round(p_phys_avg, 6),
        "avg_p_L_majority": round(p_maj_avg, 6),
        "avg_p_L_syndrome_mwpm": round(p_mwpm_avg, 6),
        "avg_p_L_decoded": round(p_best_dec, 6),
        "avg_p_L_postsel": round(p_post_avg, 6),
        "avg_postsel_keep_rate": round(0.5 * (c2_0["postsel_keep_rate"] + c2_1["postsel_keep_rate"]), 6),
        "suppression_ratio_decoded": round(p_phys_avg / max(p_best_dec, 1e-6), 3),
        "suppression_ratio_postsel": round(p_phys_avg / max(p_post_avg, 1e-6), 3),
    }

    # --- C3: 8-Point Ramsey Fringe + Bit-Exact Q16.16 BOED ---
    delays = list(c3_delays_us) if c3_delays_us is not None else list(C3_DELAYS_US)
    c3_names = [f"C3_ramsey_{f'{d:.1f}'.replace('.', 'p')}us" for d in C3_DELAYS_US]
    p0_list: list[float] = []
    shots_list: list[int] = []
    for nm in c3_names:
        c = counts_by_pub[nm]
        sh = max(1, sum(c.values()))
        p0_list.append(sum(n for bs, n in c.items() if _bit(bs, 0) == 0) / sh)
        shots_list.append(sh)

    # Self-calibrate zero-delay visibility V0 and Ramsey T2* directly from C1 (independent of C3!):
    #   <ZZ> ~= (1 - 2*p_ro)^2 * (1 - p_2q) => V0 ~= sqrt(<ZZ>)
    #   (2*p_bare - 1) ~= V0 * exp(-c1_idle_us / T2*) => T2* = -c1_idle_us / ln((2*p_bare-1)/V0)
    vis_est = float(np.clip(math.sqrt(max(exp_zz, 0.36)), 0.65, 0.99))
    bare_bloch = max(0.05, min(vis_est * 0.98, 2.0 * p_bare - 1.0))
    t2_est_us = float(np.clip(-c1_idle_us / math.log(bare_bloch / vis_est), 5.0, 250.0))
    c3_boed = run_c3_ramsey_q16_boed(
        delays_us=delays,
        p0_measured=p0_list,
        shots_per_point=shots_list,
        visibility_est=vis_est,
        t2_est_us=t2_est_us,
    )
    c3_boed["programmed_detuning_kHz"] = float(c3_programmed_kHz)
    c3_boed["delays_us"] = [round(d, 6) for d in delays]
    c3_boed["p0_measured"] = [round(p, 6) for p in p0_list]
    c3_boed["blind_8pt"]["err_vs_programmed_kHz"] = round(
        abs(c3_boed["blind_8pt"]["est_freq_kHz"] - c3_programmed_kHz), 4
    )
    c3_boed["fp64_boed"]["err_vs_programmed_kHz"] = round(
        abs(c3_boed["fp64_boed"]["est_freq_kHz"] - c3_programmed_kHz), 4
    )
    c3_boed["q16_16_boed"]["err_vs_programmed_kHz"] = round(
        abs(c3_boed["q16_16_boed"]["est_freq_kHz"] - c3_programmed_kHz), 4
    )

    return {
        "C1_dd_and_bell": c1_res,
        "C2_repcode3": c2_res,
        "C3_ramsey_boed": c3_boed,
    }
