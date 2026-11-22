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


@pytest.mark.parametrize("prog_name,min_f_nom", [
    ("bell", 0.98),
    ("ghz", 0.98),
    ("qft3", 0.99),
    ("repcode3", 0.98),
])
def test_programmer_compiles_and_verifies_builtin_programs_shaped(prog_name, min_f_nom):
    cert = _sample_cert(0)
    eng = AtomCellProgrammer(b_field_T=1.5, pulse_mode="shaped", readout_visibility=0.99)
    prog = builtin_program(prog_name)
    sched, pcert = eng.execute_and_certify(cert, prog, verify_corners=True)
    assert sched.pulse_count >= 2
    assert pcert.nominal_state_fidelity >= min_f_nom
    assert pcert.certified
    assert pcert.verify_signature()
    assert sum(pcert.measurement_counts.values()) == 1024

    # Tamper detection on SHA-256 certificate
    pcert.nominal_state_fidelity = 0.123456
    assert not pcert.verify_signature()


def test_programmer_grape_bell_and_ghz_high_corner_fidelity():
    cert = _sample_cert(0)
    eng = AtomCellProgrammer(b_field_T=1.5, pulse_mode="grape", readout_visibility=0.99)
    for pname in ("bell", "ghz"):
        _sched, pcert = eng.execute_and_certify(cert, builtin_program(pname), verify_corners=True)
        assert pcert.nominal_state_fidelity >= 0.99
        assert pcert.corner_min_fidelity >= 0.985
        assert pcert.dd_coherence_gain is not None and pcert.dd_coherence_gain > 3.0
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
