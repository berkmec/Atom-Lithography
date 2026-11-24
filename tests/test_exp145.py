"""Comprehensive test suite for Exp145 (H163): CellISA v4.0, Native OpenQASM 3.0, IBM REST Bridge & Auto-Recal."""
from __future__ import annotations

import base64
import io
import json
import math
from pathlib import Path
import re
from typing import Any
import zlib

import numpy as np
import pytest

from src.machine_control.auto_recal import AutoRecalController
from src.machine_control.cloud_qpu_bridge import (
    C1_IDLE_US,
    C2_IDLE_US,
    C3_DELAYS_US,
    C3_DETUNING_KHZ,
    IBMQuantumRESTClient,
    NativeOpenQASM3Transpiler,
    SUITE_PUB_SPECS,
    align_delay_dt,
    analyze_validation_suite_counts,
    detect_ibm_base_url,
    make_synthetic_heavy_hex_backend,
    parse_backend_metrics,
    parse_sampler_v2_counts,
    redact_secrets,
    select_best_linear_chain,
    simulate_offline_heron_counts,
    validate_openqasm3_isa,
)
from src.machine_control.factory import Certificate
from src.machine_control.programmer import (
    CellInstruction,
    CellProgram,
    MultiCellProgrammer,
    VALID_OPCODES,
    VALID_OPCODES_ALL,
    VALID_OPCODES_V4,
    program_bell,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Exact OpenQASM 3.0 Unitary / Statevector Evaluator for Verification
# ---------------------------------------------------------------------------

def _eval_angle(expr: str) -> float:
    s = expr.strip()
    if s == "pi":
        return math.pi
    if s == "-pi":
        return -math.pi
    if s == "pi/2":
        return math.pi / 2.0
    if s == "-pi/2":
        return -math.pi / 2.0
    return float(s)


def _simulate_openqasm3_ideal(qasm: str, qubit_order: list[int]) -> np.ndarray:
    """Exact noiseless statevector simulator for native OpenQASM 3.0 ({rz, sx, x, id, cz, ecr})."""
    q_to_idx = {q: i for i, q in enumerate(qubit_order)}
    n = len(qubit_order)
    psi = np.zeros(1 << n, dtype=complex)
    psi[0] = 1.0 + 0.0j

    id2 = np.eye(2, dtype=complex)
    x_mat = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
    y_mat = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=complex)
    sx_mat = 0.5 * np.array([[1.0 + 1.0j, 1.0 - 1.0j], [1.0 - 1.0j, 1.0 + 1.0j]], dtype=complex)
    cz_mat = np.diag([1.0, 1.0, 1.0, -1.0]).astype(complex)
    # Exact Qiskit ECRGate on (q0=first arg, q1=second arg): (X_0 I_1 - Y_0 X_1) / sqrt(2)
    ecr_mat = (np.kron(x_mat, id2) - np.kron(y_mat, x_mat)) / math.sqrt(2.0)

    def _apply_1q(state: np.ndarray, q_i: int, U: np.ndarray) -> np.ndarray:
        t = state.reshape([2] * n)
        t = np.tensordot(U, t, axes=([1], [q_i]))
        t = np.moveaxis(t, 0, q_i)
        return t.reshape(1 << n)

    def _apply_2q(state: np.ndarray, q_a: int, q_b: int, U4: np.ndarray) -> np.ndarray:
        t = state.reshape([2] * n)
        t = np.moveaxis(t, [q_a, q_b], [0, 1])
        rest = t.shape[2:]
        flat = t.reshape(4, -1)
        flat = U4 @ flat
        t = flat.reshape((2, 2) + rest)
        t = np.moveaxis(t, [0, 1], [q_a, q_b])
        return t.reshape(1 << n)

    in_def = False
    for raw in qasm.splitlines():
        ln = raw.strip()
        if not ln or ln.startswith(("//", "OPENQASM", "include", "bit[", "barrier", "delay[")):
            continue
        if ln.startswith("gate "):
            in_def = True
            continue
        if in_def:
            if "}" in ln:
                in_def = False
            continue
        if "measure" in ln:
            continue
        m = re.match(r"^([a-zA-Z_]+)(?:\(([^)]*)\))?\s+(.+);$", ln)
        assert m is not None, f"Could not parse OpenQASM 3 line: {ln}"
        gname = m.group(1).lower()
        arg = m.group(2)
        q_ops = [q_to_idx[int(x.strip().lstrip("$"))] for x in m.group(3).split(",")]
        if gname == "x":
            psi = _apply_1q(psi, q_ops[0], x_mat)
        elif gname == "sx":
            psi = _apply_1q(psi, q_ops[0], sx_mat)
        elif gname == "id":
            pass
        elif gname == "rz":
            th = _eval_angle(arg)
            u_rz = np.diag([np.exp(-0.5j * th), np.exp(0.5j * th)])
            psi = _apply_1q(psi, q_ops[0], u_rz)
        elif gname == "cz":
            psi = _apply_2q(psi, q_ops[0], q_ops[1], cz_mat)
        elif gname == "ecr":
            psi = _apply_2q(psi, q_ops[0], q_ops[1], ecr_mat)
        else:
            raise AssertionError(f"Unexpected non-native gate {gname!r}")
    return psi


# ---------------------------------------------------------------------------
# 1. CellISA v4.0 Opcode & Backward Compatibility Tests
# ---------------------------------------------------------------------------

def test_cellisa_v40_opcodes_and_v35_compat():
    """Verify 20 opcodes in VALID_OPCODES_ALL while preserving len(VALID_OPCODES)==17."""
    assert len(VALID_OPCODES) == 17
    assert len(VALID_OPCODES_V4) == 3
    assert VALID_OPCODES_V4 == {"QRAM_SWAP", "QLDPC_ROUND", "AUTO_RECAL"}
    assert len(VALID_OPCODES_ALL) == 20
    assert VALID_OPCODES.issubset(VALID_OPCODES_ALL)

    # All 3 new v4.0 opcodes instantiate cleanly as CellInstruction
    for op in ("QRAM_SWAP", "QLDPC_ROUND", "AUTO_RECAL"):
        inst = CellInstruction(opcode=op, args={"test": True})
        assert inst.opcode == op

    with pytest.raises(ValueError):
        CellInstruction(opcode="NONEXISTENT_OPCODE")


def test_cellisa_v40_multicell_execution():
    """Verify MultiCellProgrammer executes QRAM_SWAP, QLDPC_ROUND, and AUTO_RECAL."""
    mcp = MultiCellProgrammer()
    cert = Certificate(
        register_id="REG-V4-TEST",
        slot=0,
        attempts=1,
        shots=1,
        min_spacing_Hz=12_000.0,
        dd_quality_gate=True,
        lines_Hz=[120_000.0, 92_000.0, 68_000.0, 48_000.0],
    )
    qram = mcp.execute_qram_swap(cert, qubit_a="e", qubit_b="n0", seed=2026145)
    assert qram["opcode"] == "QRAM_SWAP"
    assert qram["total_opcodes_v4"] == 20
    assert qram["swap_fidelity"] >= 0.99
    assert qram["certified"] is True

    qldpc = mcp.execute_qldpc_round(code_name="BB_144_12_12", p_phys=0.002, rounds=2)
    assert qldpc["opcode"] == "QLDPC_ROUND"
    assert qldpc["feedlines_required"] == 5  # ceil(144 / 32) = 5
    assert qldpc["p_logical_per_round_est"] < 1e-4

    recal = mcp.execute_auto_recal(fault_type="thermal_drift_Hz", magnitude=350.0, seed=2026145)
    assert recal["opcode"] == "AUTO_RECAL"
    assert recal["recovery"]["passed"] is True


# ---------------------------------------------------------------------------
# 2. Native-ISA OpenQASM 3.0 Exact Unitary & Timing Tests (Heron cz & Eagle ecr)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("family,native_2q", [("heron", "cz"), ("eagle", "ecr")])
def test_openqasm3_transpiler_exact_unitary_and_isa(family: str, native_2q: str):
    """Verify ALL 16 OpenQASM 3.0 circuits pass static ISA + 16-dt checks AND match exact quantum states."""
    cfg, props = make_synthetic_heavy_hex_backend(family=family, seed=2026145)
    chain_info = select_best_linear_chain(cfg, props, length=5)
    qs = chain_info["qubits"]
    assert len(qs) == 5
    assert len(set(qs)) == 5

    tr = NativeOpenQASM3Transpiler(
        qubits=qs,
        native_2q=native_2q,
        dt_s=chain_info["dt_s"],
        granularity=chain_info["granularity"],
        min_delay_dt=chain_info["min_delay_dt"],
        directed_edges=chain_info["directed_edges"],
    )
    suite = tr.build_validation_suite()
    assert len(suite) == 16

    for pub_name, _nb in SUITE_PUB_SPECS:
        chk = validate_openqasm3_isa(
            suite[pub_name]["qasm"],
            native_2q=native_2q,
            granularity=16,
        )
        assert chk["valid"], f"{family}/{pub_name} failed ISA validation: {chk['errors']}"

    # Exact noiseless statevector checks:
    # 1. C1a/b/c (Bare, Echo, XY4) all return exact |0> up to global phase
    for nm in ("C1a_bare_idle", "C1b_hahn_echo", "C1c_xy4_dd"):
        psi = _simulate_openqasm3_ideal(suite[nm]["qasm"], [qs[0]])
        assert abs(psi[0]) ** 2 == pytest.approx(1.0, abs=1e-12)

    # 2. C1d Bell ZZ produces exact |Phi+> = (|00> + |11>)/sqrt(2)
    psi_zz = _simulate_openqasm3_ideal(suite["C1d_bell_zz"]["qasm"], qs[:2])
    phi_plus = np.array([1.0, 0.0, 0.0, 1.0], dtype=complex) / math.sqrt(2.0)
    assert abs(np.vdot(phi_plus, psi_zz)) ** 2 == pytest.approx(1.0, abs=1e-12)

    # 3. C1e Bell XX has <XX> = +1 (support strictly on {00, 11}) and C1f Bell YY has <YY> = -1 ({01, 10})
    psi_xx = _simulate_openqasm3_ideal(suite["C1e_bell_xx"]["qasm"], qs[:2])
    assert (abs(psi_xx[0]) ** 2 + abs(psi_xx[3]) ** 2) == pytest.approx(1.0, abs=1e-12)
    psi_yy = _simulate_openqasm3_ideal(suite["C1f_bell_yy"]["qasm"], qs[:2])
    assert (abs(psi_yy[1]) ** 2 + abs(psi_yy[2]) ** 2) == pytest.approx(1.0, abs=1e-12)

    # 4. C2a/b d=3 repetition code: |00000> for logical 0 and |10101> (D0=1,A0=0,D1=1,A1=0,D2=1) for logical 1
    psi_rep0 = _simulate_openqasm3_ideal(suite["C2a_rep3_logical0"]["qasm"], qs[:5])
    assert abs(psi_rep0[0b00000]) ** 2 == pytest.approx(1.0, abs=1e-12)
    psi_rep1 = _simulate_openqasm3_ideal(suite["C2b_rep3_logical1"]["qasm"], qs[:5])
    assert abs(psi_rep1[0b10101]) ** 2 == pytest.approx(1.0, abs=1e-12)

    # 5. C3 Ramsey at ~2.0 us (quarter period of 125 kHz) has P(0) ~= 0.5 and at ~4.0 us P(0) ~= 0.0
    psi_r2 = _simulate_openqasm3_ideal(suite["C3_ramsey_2p0us"]["qasm"], [qs[0]])
    tau2 = suite["C3_ramsey_2p0us"]["actual_delay_us"] * 1e-6
    expected_p0_2 = 0.5 * (1.0 + math.cos(2.0 * math.pi * C3_DETUNING_KHZ * 1e3 * tau2))
    assert abs(psi_r2[0]) ** 2 == pytest.approx(expected_p0_2, abs=1e-10)

    # 6. CellProgram -> OpenQASM 3.0 export
    bell_qasm = tr.transpile_cell_program(program_bell(shots=512, dd_us=10.0))
    assert validate_openqasm3_isa(bell_qasm, native_2q=native_2q, granularity=16)["valid"]


def test_ibm_2026_rest_nanosecond_dt_normalization():
    """Regression test: IBM 2026 REST /configuration returns dt=4.0 in ns (not 4e-9 s)."""
    cfg_ns = {
        "n_qubits": 156,
        "basis_gates": ["cz", "id", "rz", "sx", "x"],
        "coupling_map": [[0, 1], [1, 2], [2, 3], [3, 4]],
        "dt": 4.0,  # IBM Quantum Platform 2026 REST nanosecond unit!
        "timing_constraints": {"granularity": 1, "min_length": 2},
    }
    m_ns = parse_backend_metrics(cfg_ns)
    assert m_ns["dt_s"] == pytest.approx(4e-9, rel=1e-12)
    assert m_ns["granularity"] == 16
    assert m_ns["min_delay_dt"] == 64

    # Also verify legacy seconds format (dt=4e-9) normalizes identically
    cfg_s = dict(cfg_ns, dt=4e-9)
    m_s = parse_backend_metrics(cfg_s)
    assert m_s["dt_s"] == pytest.approx(4e-9, rel=1e-12)

    # Verify C1 (~48 us) and C3 (1..8 us) produce distinct 16-dt aligned delays and full Ramsey oscillation
    tr = NativeOpenQASM3Transpiler(
        qubits=[0, 1, 2, 3, 4],
        native_2q="cz",
        dt_s=m_ns["dt_s"],
        granularity=m_ns["granularity"],
        min_delay_dt=m_ns["min_delay_dt"],
    )
    suite = tr.build_validation_suite()
    assert 47.0 <= suite["C1a_bare_idle"]["idle_us"] <= 49.0
    assert suite["C1a_bare_idle"]["total_dt"] % 128 == 0
    c3_dts = [suite[f"C3_ramsey_{f'{d:.1f}'.replace('.', 'p')}us"]["delay_dt"] for d in C3_DELAYS_US]
    assert len(set(c3_dts)) == 8
    assert all(dt_val % 16 == 0 and dt_val >= 256 for dt_val in c3_dts)
    # Check 4.0 us Ramsey point hits trough (P(0) < 0.05) and 8.0 us hits peak (P(0) > 0.95)
    psi_4 = _simulate_openqasm3_ideal(suite["C3_ramsey_4p0us"]["qasm"], [0])
    psi_8 = _simulate_openqasm3_ideal(suite["C3_ramsey_8p0us"]["qasm"], [0])
    assert abs(psi_4[0]) ** 2 < 0.05
    assert abs(psi_8[0]) ** 2 > 0.95


def test_delay_alignment_and_subgraph_selector_prefers_low_error():
    """Verify 16-dt delay alignment and optimal 5-qubit chain avoids faulty high-error qubits."""
    assert align_delay_dt(20e-6, 4e-9, granularity=16) % 16 == 0
    assert align_delay_dt(0.5e-6, 0.5e-9, granularity=16) % 16 == 0

    cfg, props = make_synthetic_heavy_hex_backend(family="heron", n_qubits=30, seed=42)
    # Deliberately corrupt qubits 0..9 with terrible readout error (0.45) and low T2 (2 us)
    for q in range(10):
        props["qubits"][q] = [
            {"name": "T1", "unit": "us", "value": 5.0},
            {"name": "T2", "unit": "us", "value": 2.0},
            {"name": "readout_error", "unit": "", "value": 0.45},
        ]
    chain = select_best_linear_chain(cfg, props, length=5)
    assert all(q >= 10 for q in chain["qubits"]), f"Selector failed to avoid faulty qubits: {chain['qubits']}"


# ---------------------------------------------------------------------------
# 3. SamplerV2 Universal Decoder & Mocked IBM REST Client + Security Tests
# ---------------------------------------------------------------------------

def test_sampler_v2_universal_decoder_all_formats():
    """Verify parse_sampler_v2_counts decodes hex samples, binary samples, counts dict, and BitArray."""
    # Format 1: Hex samples
    p1 = {"results": [{"data": {"c": {"samples": ["0x0", "0x3", "0x3", "0x1"], "num_bits": 2}}}]}
    assert parse_sampler_v2_counts(p1) == [{"00": 1, "01": 1, "11": 2}]

    # Format 2: Binary string samples
    p2 = {"results": [{"data": {"c": {"samples": ["10101", "00000", "10101"], "num_bits": 5}}}]}
    assert parse_sampler_v2_counts(p2) == [{"00000": 1, "10101": 2}]

    # Format 3: Counts dict with hex keys
    p3 = {"results": [{"data": {"c": {"counts": {"0x0": 100, "0x15": 250}, "num_bits": 5}}}]}
    assert parse_sampler_v2_counts(p3) == [{"00000": 100, "10101": 250}]

    # Format 4: Nested Qiskit __value__ BitArray with base64+zlib numpy payload
    arr = np.array([[0], [3], [3]], dtype=np.uint8)
    buf = io.BytesIO()
    np.save(buf, arr)
    b64 = base64.b64encode(zlib.compress(buf.getvalue())).decode("ascii")
    p4 = {
        "__value__": {
            "pub_results": [{
                "__value__": {
                    "data": {
                        "__value__": {
                            "fields": {
                                "c": {
                                    "__type__": "BitArray",
                                    "__value__": {
                                        "num_bits": 2,
                                        "array": {"__type__": "ndarray", "__value__": b64},
                                    },
                                }
                            }
                        }
                    }
                }
            }]
        }
    }
    assert parse_sampler_v2_counts(p4) == [{"00": 1, "11": 2}]


class _MockResponse:
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload) if not isinstance(payload, str) else payload

    def json(self) -> Any:
        if isinstance(self._payload, str):
            return json.loads(self._payload)
        return self._payload


class _MockIBMSession:
    def __init__(self, secret_token: str, secret_crn: str, fail_job: bool = False):
        self.secret_token = secret_token
        self.secret_crn = secret_crn
        self.fail_job = fail_job
        self.calls: list[tuple[str, str]] = []
        self.cfg, self.props = make_synthetic_heavy_hex_backend(family="heron", n_qubits=20, seed=7)

    def post(self, url: str, headers: dict, data: dict, timeout: float) -> _MockResponse:
        self.calls.append(("POST", url))
        if "iam.cloud.ibm.com" in url:
            assert data["apikey"] == self.secret_token
            return _MockResponse(200, {"access_token": "FAKE_IAM_BEARER_XYZ987654", "expires_in": 3600})
        return _MockResponse(404, {"error": "not found"})

    def request(self, method: str, url: str, headers: dict, json: Any = None, timeout: float = 30.0) -> _MockResponse:
        self.calls.append((method, url))
        assert headers["Service-CRN"] == self.secret_crn
        assert headers["Authorization"] == "Bearer FAKE_IAM_BEARER_XYZ987654"
        if url.endswith("/backends"):
            return _MockResponse(200, {"devices": [
                {"name": "ibmq_qasm_simulator", "simulator": True, "operational": True, "pending_jobs": 0},
                {"name": "ibm_mock_heron", "simulator": False, "operational": True, "pending_jobs": 2},
            ]})
        if url.endswith("/backends/ibm_mock_heron/configuration"):
            return _MockResponse(200, self.cfg)
        if url.endswith("/backends/ibm_mock_heron/properties"):
            return _MockResponse(200, self.props)
        if url.endswith("/jobs") and method == "POST":
            if self.fail_job:
                return _MockResponse(
                    500,
                    f"Backend error with Bearer FAKE_IAM_BEARER_XYZ987654 and {self.secret_crn}",
                )
            return _MockResponse(200, {"id": "job_mock_145", "status": "Queued"})
        if url.endswith("/jobs/job_mock_145"):
            return _MockResponse(200, {"id": "job_mock_145", "status": "Completed", "usage": {"quantum_seconds": 12}})
        if url.endswith("/jobs/job_mock_145/results"):
            return _MockResponse(200, {"results": [{"data": {"c": {"samples": ["0x0", "0x3"], "num_bits": 2}}}]})
        return _MockResponse(404, {"error": f"unhandled {url}"})


def test_ibm_rest_client_mocked_flow_and_zero_secret_leakage():
    """Test IAM auth, EU/US region detection, backend selection, job submission, and secret redaction."""
    fake_key = "SUPER_SECRET_API_KEY_999999"
    fake_crn_eu = "crn:v1:bluemix:public:quantum-computing:eu-de:a/deadbeef:1234::"
    fake_crn_us = "crn:v1:bluemix:public:quantum-computing:us-east:a/deadbeef:1234::"

    assert "eu-de" in detect_ibm_base_url(fake_crn_eu)
    assert "eu-de" not in detect_ibm_base_url(fake_crn_us)

    # Redaction check
    leaked = f"Failed auth Bearer abc.def.123 with {fake_key} and {fake_crn_eu}"
    cleaned = redact_secrets(leaked, (fake_key, fake_crn_eu))
    assert fake_key not in cleaned
    assert "deadbeef" not in cleaned
    assert "abc.def.123" not in cleaned

    # Happy path mocked REST flow
    sess = _MockIBMSession(fake_key, fake_crn_eu, fail_job=False)
    client = IBMQuantumRESTClient(api_key=fake_key, service_crn=fake_crn_eu, session=sess)
    best = client.select_best_online_backend()
    assert best["name"] == "ibm_mock_heron"
    assert best["is_heron"] is True
    sub = client.submit_sampler_v2("ibm_mock_heron", ["OPENQASM 3.0;\nbit[2] c;\n"], shots=256)
    assert sub["job_id"] == "job_mock_145"
    meta = client.wait_for_job("job_mock_145", poll_interval_s=0.01)
    assert meta["status"] == "Completed"
    res = client.get_job_results("job_mock_145")
    assert parse_sampler_v2_counts(res) == [{"00": 1, "11": 1}]

    # Failure path MUST scrub secrets from exception string
    sess_fail = _MockIBMSession(fake_key, fake_crn_eu, fail_job=True)
    client_fail = IBMQuantumRESTClient(api_key=fake_key, service_crn=fake_crn_eu, session=sess_fail)
    with pytest.raises(RuntimeError) as exc_info:
        client_fail.submit_sampler_v2("ibm_mock_heron", ["OPENQASM 3.0;\n"], shots=64)
    err_str = str(exc_info.value)
    assert fake_key not in err_str
    assert "FAKE_IAM_BEARER_XYZ987654" not in err_str
    assert "deadbeef" not in err_str


# ---------------------------------------------------------------------------
# 4. Offline Heron Physics (C1/C2/C3) & Q16.16 BOED Parity Tests
# ---------------------------------------------------------------------------

def test_offline_heron_c1_c2_c3_physics_and_q16_parity():
    """Verify CQ3 (DD + Bell >= 0.95), CQ4 (d=3 suppression), and CQ5 (Q16 vs FP64 < 0.5 kHz)."""
    counts = simulate_offline_heron_counts(shots=4096, seed=2026145)
    assert len(counts) == 16
    res = analyze_validation_suite_counts(counts, c3_programmed_kHz=C3_DETUNING_KHZ)

    c1 = res["C1_dd_and_bell"]
    assert c1["p0_xy4_dd"] > c1["p0_bare_idle"]
    assert c1["p0_hahn_echo"] > c1["p0_bare_idle"]
    assert c1["bell_fidelity_Phi_plus"] >= 0.95

    c2 = res["C2_repcode3"]
    assert c2["avg_p_L_decoded"] < 0.5 * c2["avg_p_phys"]
    assert c2["suppression_ratio_decoded"] >= 5.0

    c3 = res["C3_ramsey_boed"]
    q16 = c3["q16_16_boed"]
    assert q16["n_points"] <= 5
    assert q16["q16_vs_fp64_diff_kHz"] < 0.5
    assert q16["err_vs_programmed_kHz"] <= 3.0


# ---------------------------------------------------------------------------
# 5. Self-Healing Auto-Recalibration 4 Fault Modes Tests (CQ6)
# ---------------------------------------------------------------------------

def test_auto_recal_all_4_fault_modes():
    """Verify all 4 injected machine fault modes recover autonomously within spec."""
    ctrl = AutoRecalController(seed=2026145)
    out = ctrl.run_all_fault_scenarios()
    assert out["all_passed"] is True
    assert out["n_passed"] == 4

    # (a) Laser +/-8% drift
    laser = out["S5_5_laser_drift"]
    assert laser["worst_uncontrolled_sigma_nm"] > 0.50  # confirms fault actually breaks open-loop spec!
    assert laser["worst_controlled_sigma_nm"] <= 0.50

    # (b) UHV vacuum spike
    uhv = out["S5_uhv_vacuum_spike"]
    assert uhv["gate_valve_locked"] is True
    assert uhv["beam_paused"] is True
    assert uhv["safe_resumed"] is True

    # (c) 32x32 blanker 5% dead channels (honest wafer-stage step-and-stitch compensation)
    blank = out["S3_blanker_dead_channels"]
    assert blank["dead_channels_detected"] == 51
    assert blank["channels_remapped"] == 51
    assert blank["wafer_site_coverage_after_pct"] == 100.0
    assert 0.0 < blank["throughput_after_recal_pct"] < 100.0
    assert blank["max_coordinate_mismatch_um"] == 0.0
    assert blank["passed"] is True

    # (d) 31P +/-350 Hz thermal drift Q16.16 BOED relock
    therm = out["hyperfine_thermal_drift"]
    assert therm["max_relock_time_ms"] < 5.0
    assert therm["max_residual_error_Hz"] < 100.0


# ---------------------------------------------------------------------------
# 6. Live Hardware Artifact Integrity, GFM Validation & Security Hygiene (CQ7)
# ---------------------------------------------------------------------------

def test_live_ibm_marrakesh_results_and_figure_integrity():
    """Verify live ibm_marrakesh JSON, merged exp145.json, and 2400x1400 PNG artifact."""
    res_dir = REPO_ROOT / "results" / "exp145_cloud_qpu_ibm_validation"
    live_path = res_dir / "ibm_qpu_live_results.json"
    merged_path = res_dir / "exp145.json"
    fig_path = res_dir / "fig_exp145_ibm_qpu_live.png"
    assert live_path.is_file()
    assert merged_path.is_file()
    assert fig_path.is_file()

    # Check PNG signature and 2400x1400 IHDR dimensions (bytes 16..24)
    raw_png = fig_path.read_bytes()
    assert raw_png[:8] == b"\x89PNG\r\n\x1a\n"
    w = int.from_bytes(raw_png[16:20], "big")
    h = int.from_bytes(raw_png[20:24], "big")
    assert (w, h) == (2400, 1400)

    live = json.loads(live_path.read_text(encoding="utf-8"))
    assert live["mode"] == "live_ibm_qpu_hardware"
    assert live["backend"]["n_qubits"] >= 100
    assert live["backend"]["dt_ns"] == pytest.approx(4.0, abs=0.5)
    assert len(live["backend"]["selected_5q_chain"]) == 5
    assert len(live["counts_by_pub"]) == 16

    la = live["analysis"]
    assert la["C1_dd_and_bell"]["p0_xy4_dd"] > la["C1_dd_and_bell"]["p0_bare_idle"]
    assert la["C1_dd_and_bell"]["bell_fidelity_Phi_plus"] >= 0.85
    assert la["C2_repcode3"]["avg_p_L_decoded"] < 0.5 * la["C2_repcode3"]["avg_p_phys"]
    assert la["C3_ramsey_boed"]["q16_16_boed"]["n_points"] <= 5
    assert la["C3_ramsey_boed"]["q16_16_boed"]["q16_vs_fp64_diff_kHz"] < 0.5
    assert la["C3_ramsey_boed"]["q16_16_boed"]["posterior_std_kHz"] < 5.0

    merged = json.loads(merged_path.read_text(encoding="utf-8"))
    assert merged["all_offline_passed"] is True
    assert merged["all_live_passed"] is True


def test_exp145_zero_hardcoded_paths_zero_secrets_and_gfm_valid():
    """Verify all Exp145 artifacts contain zero host paths, zero secrets, and 0 GFM table errors."""
    res_dir = REPO_ROOT / "results" / "exp145_cloud_qpu_ibm_validation"
    targets = [
        REPO_ROOT / "src" / "machine_control" / "cloud_qpu_bridge.py",
        REPO_ROOT / "src" / "machine_control" / "auto_recal.py",
        REPO_ROOT / "src" / "machine_control" / "programmer.py",
        REPO_ROOT / "experiments" / "exp145_cloud_qpu_ibm_validation" / "run_exp145_offline.py",
        REPO_ROOT / "experiments" / "exp145_cloud_qpu_ibm_validation" / "run_ibm_live_qpu.py",
        REPO_ROOT / "experiments" / "exp145_cloud_qpu_ibm_validation" / "plot_exp145.py",
        res_dir / "predictions_exp145.json",
        res_dir / "exp145_offline.json",
        res_dir / "ibm_qpu_live_results.json",
        res_dir / "exp145.json",
        res_dir / "summary_exp145.md",
    ]
    forbidden_paths = ("/home/" + "berk", "/run/media/" + "berk")
    for p in targets:
        assert p.is_file(), f"Missing expected Exp145 file: {p}"
        txt = p.read_text(encoding="utf-8")
        for fp in forbidden_paths:
            assert fp not in txt, f"Hardcoded host path {fp!r} found in {p.name}"
        assert "crn:v1:bluemix:" not in txt.lower(), f"Real CRN pattern found in {p.name}"
        assert "bearer eyj" not in txt.lower(), f"Real JWT Bearer token found in {p.name}"

    # Verify 0 GFM table column mismatches in summary_exp145.md
    md_lines = (res_dir / "summary_exp145.md").read_text(encoding="utf-8").splitlines()
    table_cols: int | None = None
    in_code = False
    for ln_no, ln in enumerate(md_lines, start=1):
        s = ln.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if s.startswith("|") and s.endswith("|"):
            cols = s.count("|") - 1
            if table_cols is None:
                table_cols = cols
            else:
                assert cols == table_cols, (
                    f"GFM table column mismatch at summary_exp145.md:{ln_no} "
                    f"(expected {table_cols}, got {cols})"
                )
        else:
            table_cols = None
