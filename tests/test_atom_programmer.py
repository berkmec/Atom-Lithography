"""Tests for pulse_engine (GRAPE + XY8 DD) and programmer (CellISA + AtomCellProgrammer)."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from machine_control.calibrator import calibrate
from machine_control.config import MachineConfig
from machine_control.factory import Certificate, Factory
from machine_control.programmer import (
    AtomCellProgrammer,
    CellInstruction,
    CellProgram,
    builtin_program,
    simulate_ideal,
)
from machine_control.pulse_engine import (
    MultiSpinSimulator,
    propagate_su2_ensemble,
    simulate_xy8_dd,
    slice_unitary,
    synthesize_selective_pulse,
)


def _sample_cert(idx: int = 0) -> Certificate:
    rep = Factory(MachineConfig.v224_baseline()).run(15)
    return rep.certificates[idx]


def test_su2_propagator_is_unitary_to_machine_precision():
    rng = np.random.default_rng(42)
    nx = rng.normal(0.0, 5e4, size=64)
    ny = rng.normal(0.0, 5e4, size=64)
    nz = rng.normal(0.0, 2e5, size=64)
    U = slice_unitary(nx, ny, nz, dt_s=1e-5)
    eye = np.eye(2, dtype=complex)[None, :, :]
    prod = np.einsum("nji,njk->nik", np.conj(U), U)
    assert np.max(np.abs(prod - eye)) < 1e-13
    # Determinant = 1 for SU(2)
    dets = U[:, 0, 0] * U[:, 1, 1] - U[:, 0, 1] * U[:, 1, 0]
    assert np.max(np.abs(dets - 1.0)) < 1e-13


def test_grape_9corner_synthesis_beats_shaped_under_detuning_and_amp_errors():
    lines = np.array([2.98e6, 1.90e6, 1.20e6, 0.80e6, 0.45e6, 0.22e6, 0.11e6, 0.055e6])
    wf_s = synthesize_selective_pulse(lines, nucleus_idx=0, electron_branch=1, mode="shaped")
    wf_g = synthesize_selective_pulse(lines, nucleus_idx=0, electron_branch=1, mode="grape")
    assert wf_g.worst_corner_fidelity >= 0.99
    assert wf_g.worst_spectator_retention >= 0.999
    assert wf_g.worst_corner_fidelity > wf_s.worst_corner_fidelity


def test_calibrator_live_grape_mode_certifies_and_rejects_crowded():
    wide = np.array([2.98e6, 1.90e6, 1.20e6, 0.45e6])
    crowded = np.array([100e3, 102e3, 900e3, 2.9e6])
    res_ok = calibrate(wide, mode="grape", max_targets=2)
    res_bad = calibrate(crowded, mode="grape", max_targets=2)
    assert res_ok.certified and res_ok.corner_verified
    assert res_ok.min_corner_fidelity >= 0.99
    assert len(res_ok.waveforms) == 2
    assert not res_bad.certified


def test_xy8_dynamical_decoupling_extends_coherence_over_fid():
    res = simulate_xy8_dd(duration_us=200.0, n_pulses=16, sigma_bath_kHz=12.0, tau_corr_us=500.0)
    assert res.dd_coherence > 0.85
    assert res.fid_coherence < 0.35
    assert res.coherence_gain > 3.0


def test_cellisa_roundtrip_and_opcode_validation():
    p = builtin_program("ghz")
    text = p.to_json()
    p2 = CellProgram.from_json(text)
    assert p2.name == p.name
    assert len(p2.instructions) == len(p.instructions)
    with pytest.raises(ValueError):
        CellInstruction(opcode="INVALID_OP")


@pytest.mark.parametrize("prog_name,min_f_nom,expect_cert", [
    ("bell", 0.97, True),
    ("ghz", 0.97, True),
    ("qft3", 0.99, False),     # Uncompensated shaped qft3 has corner_min < 0.90 -> MUST NOT certify!
    ("repcode3", 0.98, True),
])
def test_programmer_compiles_and_verifies_builtin_programs_shaped(prog_name, min_f_nom, expect_cert):
    cert = _sample_cert(0)
    eng = AtomCellProgrammer(b_field_T=1.5, pulse_mode="shaped", readout_visibility=0.99)
    prog = builtin_program(prog_name)
    sched, pcert = eng.execute_and_certify(cert, prog, verify_corners=True)
    assert sched.pulse_count >= 2
    assert pcert.nominal_state_fidelity >= min_f_nom
    assert pcert.certified is expect_cert
    if pcert.certified:
        assert pcert.corner_min_fidelity >= 0.90
    assert pcert.verify_signature()
    assert sum(pcert.measurement_counts.values()) == 1024

    # Tamper detection on SHA-256 certificate
    pcert.nominal_state_fidelity = 0.123456
    assert not pcert.verify_signature()


def test_programmer_grape_bell_and_ghz_high_corner_fidelity():
    cert = _sample_cert(0)
    eng = AtomCellProgrammer(b_field_T=1.5, pulse_mode="grape", readout_visibility=0.99)
    for pname in ("bell", "ghz"):
        # Unitary gate fidelity without DD noise >= 0.99; with 200 us XY8 DD bounded by (1 + W)/2
        _sched_u, pcert_u = eng.execute_and_certify(cert, builtin_program(pname, dd_us=0.0), verify_corners=True)
        assert pcert_u.nominal_state_fidelity >= 0.99
        assert pcert_u.corner_min_fidelity >= 0.985
        assert pcert_u.certified is True
        assert pcert_u.verify_signature()

        _sched, pcert = eng.execute_and_certify(cert, builtin_program(pname), verify_corners=True)
        assert pcert.dd_coherence is not None
        assert pcert.nominal_state_fidelity <= 0.5 * (1.0 + pcert.dd_coherence) + 1e-3
        assert pcert.nominal_state_fidelity >= 0.97
        assert pcert.corner_min_fidelity >= 0.985
        assert pcert.dd_coherence_gain is not None and pcert.dd_coherence_gain > 3.0
        assert pcert.certified is True
        assert pcert.verify_signature()


def test_array_exec_compiles_bespoke_frequencies_per_cell(tmp_path):
    rep = Factory(MachineConfig.v224_baseline()).run(10)
    cells = rep.certificates[:3]
    eng = AtomCellProgrammer(b_field_T=1.5, pulse_mode="shaped")
    out_jsonl = tmp_path / "array_certs.jsonl"
    results = eng.execute_array(cells, builtin_program("bell"), verify_corners=True, out_jsonl=out_jsonl)
    assert len(results) == 3

    # Each cell has its own measured hyperfine spectrum -> unique compiled RF carrier frequency
    rf_freqs = []
    for sched, pcert in results:
        rf_ops = [o.waveform.freq_Hz for o in sched.ops if o.kind == "PULSE" and o.waveform.channel == "RF"]
        assert len(rf_ops) >= 1
        rf_freqs.append(rf_ops[0])
        assert pcert.verify_signature() and pcert.certified
    assert len(set(round(f, 1) for f in rf_freqs)) == 3

    # Verify JSONL output
    rows = [json.loads(x) for x in out_jsonl.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 3
    assert all(r["register_id"] == c.register_id for r, c in zip(rows, cells))


# ===========================================================================
# Regression Tests for OBS-026, OBS-027, OBS-084, OBS-146
# ===========================================================================

def test_obs026_negative_hyperfine_b_perp_and_corner_certification_gate():
    from machine_control.programmer import ProgramCertificate
    from machine_control.pulse_engine import transition_frequencies

    # 1) Exact dressed eigen-frequencies for A = -120 kHz, B_perp = 30 kHz at 1.5 T
    freqs = transition_frequencies(np.array([-120_000.0]), b_field_T=1.5, b_perp_hz=np.array([30_000.0]))
    assert freqs[0] == pytest.approx(12_637_508.902, abs=0.05)  # e=0 (m_s=+1/2)
    assert freqs[1] == pytest.approx(12_757_508.818, abs=0.05)  # e=1 (m_s=-1/2)

    # AtomCellProgrammer.compile preserves sign of A < 0 and b_perp_Hz, targeting e=1 manifold
    cert_neg = Certificate(
        register_id="NEG-A-0",
        slot=0,
        attempts=1,
        shots=1,
        min_spacing_Hz=60_000.0,
        dd_quality_gate=True,
        lines_Hz=[-120_000.0, 240_000.0],
        b_perp_Hz=[30_000.0, 15_000.0],
    )
    eng = AtomCellProgrammer(b_field_T=1.5, pulse_mode="shaped")
    prog = CellProgram("cnot_neg")
    prog.add("INIT", qubits=["e", "n0", "n1"], state="100")
    prog.add("CNOT", control="e", target="n1")
    sched = eng.compile(cert_neg, prog)
    # n1 is sorted second by |A|: A = -120 kHz, B_perp = 30 kHz -> e=1 RF pulse at 12,757,508.8 Hz
    assert sched.active_lines_Hz[1] == pytest.approx(-120_000.0)
    rf_pulses = [o.waveform for o in sched.ops if o.kind == "PULSE" and o.waveform.channel == "RF"]
    assert len(rf_pulses) == 1
    assert rf_pulses[0].freq_Hz == pytest.approx(12_757_508.818, abs=0.1)

    # 2) Tight 5.1 kHz register GHZ3 with corner_min_fidelity < 0.90 MUST NOT be certified
    cert_tight = Certificate(
        register_id="TIGHT-2",
        slot=0,
        attempts=1,
        shots=1,
        min_spacing_Hz=5_100.0,
        dd_quality_gate=True,
        lines_Hz=[72_200.0, 62_000.0],
    )
    _, pcert_tight = eng.execute_and_certify(cert_tight, builtin_program("ghz", n_qubits=3), verify_corners=True)
    assert pcert_tight.corner_min_fidelity < 0.90
    assert pcert_tight.certified is False

    # 3) ProgramCertificate itself forbids certified=True when corner_min_fidelity < 0.90
    with pytest.raises(ValueError, match="corner_min_fidelity"):
        ProgramCertificate(
            program_name="bad",
            register_id="BAD-0",
            pulse_mode="shaped",
            n_qubits=2,
            active_lines_Hz=[120_000.0],
            pulse_count=1,
            total_duration_us=500.0,
            nominal_state_fidelity=0.98,
            corner_min_fidelity=0.892,
            corner_mean_fidelity=0.91,
            dd_coherence_gain=None,
            dd_coherence=None,
            measurement_counts={"00": 512, "11": 512},
            readout_visibility=0.99,
            certified=True,
        )


def test_obs084_kraus_dd_infidelity_and_finite_mw_hyperfine_detuning():
    from machine_control.pulse_engine import synthesize_electron_mw_pulse

    # 1) Non-unitary Kraus Pauli-Z DD channel: infidelity on |Phi+> equals exact (1 - W)/2, purity < 1
    sim = MultiSpinSimulator(np.array([250_000.0]), b_field_T=1.5)
    phi_plus = np.array([1.0, 0.0, 0.0, 1.0], dtype=complex) / math.sqrt(2.0)
    sim.state = phi_plus.copy()
    dd_res = sim.apply_dd_hold(duration_us=200.0, n_pulses=16, sigma_bath_kHz=12.0, tau_corr_us=500.0)
    expected_fid = 0.5 * (1.0 + dd_res.dd_coherence)
    expected_purity = 0.5 * (1.0 + dd_res.dd_coherence ** 2)
    assert sim.state_fidelity(phi_plus) == pytest.approx(expected_fid, abs=1e-12)
    assert sim.purity() == pytest.approx(expected_purity, abs=1e-12)
    assert sim.purity() < 0.99

    # 2) Finite 5 MHz MW pi-pulse with Sum(A_k)/2 = 3.999 MHz exhibits exact off-resonant P_flip ~= 0.49894
    sim_mw = MultiSpinSimulator(np.array([7_998_000.0]), b_field_T=1.5)
    sim_mw.reset("00")
    wf_mw = synthesize_electron_mw_pulse(axis="X", theta_rad=math.pi, rabi_MHz=5.0, b_field_T=1.5)
    sim_mw.apply_waveform(wf_mw)
    p_flip = float(sim_mw.probabilities()[2])  # |10> state (electron flipped, nucleus |0>)
    assert p_flip == pytest.approx(0.49894, abs=1e-3)


def test_obs146_builtin_program_ghz_accepts_n_qubits_kwarg():
    p3 = builtin_program("ghz", n_qubits=3, shots=256)
    p5 = builtin_program("ghz", n_qubits=5, shots=128)
    assert p3.name == "ghz3"
    assert p3.used_nuclear_count() == 2
    assert p5.name == "ghz5"
    assert p5.used_nuclear_count() == 4


def test_obs027_cloud_qpu_dd_hold_identity_and_coupling_map_validation():
    import re
    from machine_control.cloud_qpu_bridge import (
        IBMQuantumRESTClient,
        NativeOpenQASM3Transpiler,
        validate_openqasm3_isa,
    )

    chain = [7, 6, 5, 4, 3]
    edges = [(7, 6), (6, 7), (6, 5), (5, 6), (5, 4), (4, 5), (4, 3), (3, 4)]
    tr = NativeOpenQASM3Transpiler(qubits=chain, native_2q="cz", dt_s=4e-9, granularity=16, directed_edges=edges)

    # 1) Transpiling Bell + DD_HOLD must preserve |Phi+> (exact identity DD, never single X bit-flip!)
    bell_qasm = tr.transpile_cell_program(builtin_program("bell", dd_us=20.0))
    chk_bell = validate_openqasm3_isa(bell_qasm, native_2q="cz", granularity=16, coupling_map=edges)
    assert chk_bell["valid"], chk_bell["errors"]

    # Statevector check on [7, 6]
    def _eval_sv(qasm: str, q_order: list[int]) -> np.ndarray:
        idx_map = {q: i for i, q in enumerate(q_order)}
        n = len(q_order)
        psi = np.zeros(1 << n, dtype=complex)
        psi[0] = 1.0
        x_m = np.array([[0, 1], [1, 0]], dtype=complex)
        sx_m = 0.5 * np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]], dtype=complex)
        cz_m = np.diag([1, 1, 1, -1]).astype(complex)
        for raw in qasm.splitlines():
            ln = raw.strip()
            if not ln or ln.startswith(("//", "OPENQASM", "include", "bit[", "barrier", "delay[")) or "measure" in ln:
                continue
            m = re.match(r"^([a-zA-Z_]+)(?:\(([^)]*)\))?\s+(.+);$", ln)
            g, arg, ops = m.group(1).lower(), m.group(2), [idx_map[int(s.strip()[1:])] for s in m.group(3).split(",")]
            if len(ops) == 1:
                if g == "x":
                    u = x_m
                elif g == "sx":
                    u = sx_m
                elif g == "rz":
                    s = arg.strip()
                    ang_tbl = {"pi": math.pi, "-pi": -math.pi, "pi/2": math.pi / 2, "-pi/2": -math.pi / 2}
                    th = ang_tbl[s] if s in ang_tbl else float(s)
                    u = np.diag([np.exp(-0.5j * th), np.exp(0.5j * th)])
                else:
                    continue
                t = np.moveaxis(np.tensordot(u, psi.reshape([2] * n), axes=([1], [ops[0]])), 0, ops[0])
                psi = t.reshape(1 << n)
            elif g == "cz":
                t = np.moveaxis(psi.reshape([2] * n), ops, [0, 1])
                rest = t.shape[2:]
                t = (cz_m @ t.reshape(4, -1)).reshape((2, 2) + rest)
                psi = np.moveaxis(t, [0, 1], ops).reshape(1 << n)
        return psi

    sv_bell = _eval_sv(bell_qasm, [7, 6])
    phi_plus = np.array([1.0, 0.0, 0.0, 1.0], dtype=complex) / math.sqrt(2.0)
    assert abs(np.vdot(phi_plus, sv_bell)) ** 2 == pytest.approx(1.0, abs=1e-12)

    # 2) Transpiling 4-qubit GHZ on linear chain uses strictly adjacent edges & prepares exact GHZ4
    ghz4_qasm = tr.transpile_cell_program(builtin_program("ghz", n_qubits=4, dd_us=20.0))
    chk_ghz = validate_openqasm3_isa(ghz4_qasm, native_2q="cz", granularity=16, coupling_map=edges)
    assert chk_ghz["valid"], chk_ghz["errors"]
    sv_ghz = _eval_sv(ghz4_qasm, [7, 6, 5, 4])
    ghz_ideal = np.zeros(16, dtype=complex)
    ghz_ideal[0] = ghz_ideal[15] = 1.0 / math.sqrt(2.0)
    assert abs(np.vdot(ghz_ideal, sv_ghz)) ** 2 == pytest.approx(1.0, abs=1e-12)

    # 3) validate_openqasm3_isa MUST reject unrouted non-adjacent 2Q gates when coupling_map is given
    bad_qasm = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nbit[2] c;\ncz $7, $5;\n'
    chk_bad = validate_openqasm3_isa(bad_qasm, native_2q="cz", granularity=16, coupling_map=edges)
    assert chk_bad["valid"] is False
    assert any("Non-adjacent" in e for e in chk_bad["errors"])

    # 4) select_best_online_backend MUST fail closed when backend status REST call errors
    class _BrokenStatusClient(IBMQuantumRESTClient):
        def list_backends(self):
            return [{"name": "ibm_broken", "simulator": False}]
        def get_backend_status(self, backend_name: str):
            raise RuntimeError("HTTP 503 status endpoint unreachable")

    client = _BrokenStatusClient(api_key="dummy_key", service_crn="crn:v1:bluemix:public:quantum:us-east:a/0:1::")
    with pytest.raises(RuntimeError, match="No operational"):
        client.select_best_online_backend()
