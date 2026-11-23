"""Tests for Exp132 (H150): Bayesian Adaptive Spectroscopy (BOED) & CellISA v3.0 Multi-Cell M4 Compiler."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from machine_control.adaptive_spectroscopy import (
    BOEDConfig,
    BayesianSpectrometer,
    CandidateSpectrum,
    compute_min_transition_spacing_Hz,
    fisher_crlb_sigma_Hz,
    sample_candidate_population,
)
from machine_control.config import MachineConfig
from machine_control.factory import Certificate, Factory
from machine_control.programmer import (
    BusLinkSpec,
    CellInstruction,
    CellProgram,
    MultiCellProgrammer,
    VALID_OPCODES_V3,
    WaferRouter,
    WaferSite,
    verify_with_exp126_bridge,
)
from machine_control.sim import main as sim_main


def test_boed_early_abort_precision_and_classification_integrity():
    rng_pop = np.random.default_rng(13211)
    rng_spec = np.random.default_rng(13212)
    cands = sample_candidate_population(250, rng_pop)
    spec = BayesianSpectrometer(BOEDConfig(), rng=rng_spec)
    res = [spec.inspect_candidate(c) for c in cands]

    t_blank = [r.total_time_ms for c, r in zip(cands, res) if c.label == "blank"]
    t_crowd = [r.total_time_ms for c, r in zip(cands, res) if c.label == "crowded"]
    t_work = [r.total_time_ms for c, r in zip(cands, res) if c.label == "working"]

    assert np.mean(t_blank) < 3.0
    assert np.mean(t_crowd) < 15.0
    assert np.mean([r.total_time_ms for r in res]) < 100.0

    # Classification integrity
    work_pairs = [(c, r) for c, r in zip(cands, res) if c.label == "working"]
    nonwork_pairs = [(c, r) for c, r in zip(cands, res) if c.label != "working"]
    fnr = sum(1 for _, r in work_pairs if not r.accepted) / len(work_pairs)
    fpr = sum(1 for _, r in nonwork_pairs if r.accepted) / len(nonwork_pairs)
    assert fnr < 0.02
    assert fpr < 0.01

    # Stage-2 BOED frequency precision <= 100 Hz (2x sharper than legacy 200 Hz)
    errs = np.concatenate([
        r.estimated_lines_Hz - c.true_lines_Hz
        for c, r in work_pairs
        if r.accepted and len(r.estimated_lines_Hz) == 8
    ])
    rms_Hz = float(np.sqrt(np.mean(errs * errs)))
    assert rms_Hz <= 100.0
    # Empirical RMS must stay above single-shot CRLB bound floor (sanity check)
    crlb = fisher_crlb_sigma_Hz(1_000.0, 10.0, 6)
    assert rms_Hz > 0.7 * crlb


def test_v400_bayesian_factory_beats_v300_and_hits_write_ceiling():
    cfg_v3 = MachineConfig.v300_baseline()
    cfg_v4 = MachineConfig.v400_bayesian()
    assert cfg_v4.spectroscopy_mode == "bayesian"
    assert cfg_v4.beamlets == 1_024
    assert cfg_v4.shot_cycle_s == pytest.approx(0.015)

    r3 = Factory(cfg_v3).run(40)
    r4 = Factory(cfg_v4).run(40)
    assert r4.mean_spec_time_ms < 120.0
    assert r4.early_aborts > 0
    assert r4.certified_per_day_analytic >= 1.0e9
    assert r4.certified_per_day_analytic > 5.0 * r3.certified_per_day_analytic


def test_cellisa_v3_opcodes_and_cavity_bus_physics():
    for op in ("BUS_TUNE", "BUS_CZ", "LOGICAL_ENCODE", "WAFER_MAP_ROUTE"):
        assert op in VALID_OPCODES_V3
        inst = CellInstruction(opcode=op, args={"demo": True})
        assert inst.opcode == op

    link = BusLinkSpec("C0", "C1", g_MHz=15.0, detuning_MHz=150.0, kappa_MHz=0.50, t2_electron_us=500.0)
    assert link.j_bus_MHz == pytest.approx(1.5)
    assert link.cz_duration_us == pytest.approx(1.0 / 6.0, rel=1e-4)
    assert 0.95 < link.cz_fidelity < 1.0
    link_2hop = BusLinkSpec("C0", "C2", g_MHz=15.0, detuning_MHz=150.0, kappa_MHz=0.50, hop_distance=2)
    assert link_2hop.cz_fidelity == pytest.approx(link.cz_fidelity ** 2, rel=1e-6)


def test_wafer_router_and_multicell_certificate_with_exp126_bridge(tmp_path):
    # Deterministic 4x4 heterogeneous wafer with 9 working and 7 dead sites
    base_lines = np.array([62e3, 125e3, 240e3, 470e3, 820e3, 1280e3, 1950e3, 2950e3])
    rng = np.random.default_rng(77)
    dead_coords = {(0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 0), (3, 2)}
    sites = []
    for r in range(4):
        for c in range(4):
            if (r, c) in dead_coords:
                sites.append(WaferSite(r, c, "blank" if (r + c) % 2 == 0 else "crowded", None, 1.0))
            else:
                lines = np.sort(base_lines * rng.uniform(0.92, 1.08, size=8))
                cert = Certificate(
                    register_id=f"T-R{r}C{c}",
                    slot=r * 4 + c,
                    attempts=1,
                    shots=1,
                    min_spacing_Hz=compute_min_transition_spacing_Hz(lines),
                    dd_quality_gate=True,
                    lines_Hz=[float(x) for x in lines],
                )
                sites.append(WaferSite(r, c, "working", cert, 75.0))

    prog = MultiCellProgrammer(b_field_T=1.5, pulse_mode="shaped")
    out_file = tmp_path / "mcert.jsonl"
    route, mcert = prog.execute_routed_multicell_program(
        sites, target_cells=4, logical_code="bitflip3_plus_ancilla", out_jsonl=out_file
    )
    assert route.routed
    assert len(route.assigned_cell_ids) == 4
    assert all(tuple(rc) not in dead_coords for rc in route.assigned_coords)
    assert mcert.certified
    assert mcert.min_bus_cz_fidelity >= 0.94
    assert mcert.joint_state_fidelity >= 0.90
    assert mcert.verify_signature()
    assert mcert.exp126_bridge["exp126_ledger_found"]
    assert mcert.exp126_bridge["all_clear_5kHz_gate"]
    assert out_file.is_file()

    # SHA-256 tamper detection
    mcert.joint_state_fidelity = 0.123456
    assert not mcert.verify_signature()


def test_sim_cli_v400_preset(tmp_path):
    certs = tmp_path / "v4_certs.jsonl"
    rep = sim_main(["--slots", "20", "--preset", "v400", "--certs", str(certs)])
    assert rep.certified > 0
    assert rep.mean_spec_time_ms < 150.0
    assert certs.is_file()


def test_exp132_code_has_zero_hardcoded_host_paths():
    files = [
        ROOT / "src" / "machine_control" / "adaptive_spectroscopy.py",
        ROOT / "src" / "machine_control" / "programmer.py",
        ROOT / "src" / "machine_control" / "config.py",
        ROOT / "src" / "machine_control" / "factory.py",
        ROOT / "src" / "machine_control" / "sim.py",
        ROOT / "experiments" / "exp132_bayesian_spectroscopy_cellisa3" / "run_exp132.py",
    ]
    bad_a = "/" + "home/berk"
    bad_b = "/" + "run/media/berk"
    for fp in files:
        txt = fp.read_text(encoding="utf-8")
        assert bad_a not in txt, f"Hardcoded host path found in {fp.name}"
        assert bad_b not in txt, f"Hardcoded mount path found in {fp.name}"
