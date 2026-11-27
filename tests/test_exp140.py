"""Tests for Exp140 (H158): Q16.16 BOED-FPGA DSP, 3 kOhm NbTiN Mux Cryo Readout & CellISA v3.5."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "exp140_cryo_fpga_boed_mux_readout"))

from machine_control.adaptive_spectroscopy import (
    BOEDConfig,
    compute_min_transition_spacing_Hz,
    sample_candidate_population,
)
from machine_control.factory import Certificate
from machine_control.fpga_boed_dsp import (
    FPGACoreConfig,
    Q1616BOEDCore,
    build_exp_neg_lut_q16,
    build_lorentzian_lut_q16,
    from_q16,
    lut_interp_q16,
    run_paired_fp64_vs_q16_benchmark,
    to_q16,
)
from machine_control.programmer import (
    CellInstruction,
    MultiCellCertificate,
    MultiCellProgrammer,
    VALID_OPCODES,
    VALID_OPCODES_V2,
    VALID_OPCODES_V3,
    VALID_OPCODES_V35,
    WaferSite,
)
from mux_cryo_model140 import (
    build_s65_hardware_spec,
    chebyshev_bandpass_s21_sq,
    evaluate_cavity_readout_contrast,
    evaluate_cryo_heat_budget,
    evaluate_mux_readout_sweep,
    evaluate_purcell_and_noise_chain,
    simulate_all_pairs_mux_collisions,
)


def test_q16_luts_and_cycle_exact_fpga_timing():
    lor_lut = build_lorentzian_lut_q16()
    exp_lut = build_exp_neg_lut_q16()
    u = np.linspace(0.0, 10.0, 200)
    lor_q = from_q16(lut_interp_q16(to_q16(u), lor_lut, 12.0, 512))
    assert np.max(np.abs(lor_q - 1.0 / (1.0 + u * u))) < 2e-4

    x = np.linspace(0.0, 14.0, 200)
    exp_q = from_q16(lut_interp_q16(to_q16(x), exp_lut, 16.0, 512))
    assert np.max(np.abs(exp_q - np.exp(-x))) < 2e-4

    core = Q1616BOEDCore(FPGACoreConfig())
    assert core.step_latency_us < 25.0
    assert core.cycles_per_step == 584
    rb = core.resource_budget()
    assert rb["total_16ch"]["dsp48e2_pct"] < 25.0
    assert rb["total_16ch"]["bram36_pct"] < 25.0
    assert rb["total_16ch"]["lut_pct"] < 25.0


def test_q16_vs_fp64_paired_boed_parity():
    cands = sample_candidate_population(160, np.random.default_rng(14011))
    bench = run_paired_fp64_vs_q16_benchmark(cands, BOEDConfig(), FPGACoreConfig(), seed=14011)
    assert bench["stage0_sprt_disagreements"] == 0
    assert bench["parity"]["abs_delta_rms_Hz"] < 1.0
    assert bench["parity"]["abs_delta_fnr_pct"] < 0.05
    assert bench["parity"]["abs_delta_fpr_pct"] < 0.05
    assert bench["q16_16"]["rms_freq_error_Hz"] <= 100.0


def test_3kohm_nbtin_purcell_twpa_and_physical_nmux_ceiling():
    ch = evaluate_purcell_and_noise_chain()
    # OBS-012: Wideband >= 3.5 GHz multi-pole stub Purcell filter cleanly > 1.2 GHz above 5.0 GHz qubits
    assert ch["purcell_passband_bw_GHz"] >= 3.50
    assert ch["min_detuning_to_M4_qubit_GHz"] > 1.20
    assert ch["min_clearance_to_6p264GHz_box_mode_MHz"] > 100.0
    assert ch["max_passband_insertion_loss_32ch_dB"] < 0.25
    assert ch["channels_gt_3dB_loss_32ch"] == 0
    assert ch["purcell_protection_factor"] > 1000.0
    assert ch["t1_purcell_filtered_ms"] > 100.0

    # OBS-075: Honest Caves heterodyne SQL (hf/k_B) & exact 4.000x reflection vs hanger-notch contrast
    assert ch["sql_convention"] == "Caves_heterodyne_dual_quadrature_hf_over_kB"
    assert abs(ch["t_sql_K"] - 2.0 * ch["t_sql_single_quad_ref_K"]) < 1e-3
    assert ch["t_sys_with_twpa_K"] < 1.0
    assert ch["eta_meas_with_twpa"] > 4.0 * ch["eta_meas_hemt_only"]
    sp = ch["s_param_contrast_audit"]
    assert abs(sp["reflection_over_notch_ratio"] - 4.0) < 1e-5

    mx = evaluate_mux_readout_sweep()
    assert mx["n_mux_star"] == 32
    assert mx["by_nmux"]["32"]["F_ro_at_2us"] >= 0.990
    assert mx["by_nmux"]["32"]["max_purcell_passband_IL_dB"] < 0.25
    assert mx["by_nmux"]["64"]["F_ro_at_2us"] < 0.990
    assert mx["by_nmux"]["64"]["twpa_backoff_dB"] > mx["by_nmux"]["32"]["twpa_backoff_dB"]
    # OBS-075: All-pairs N(N-1)/2 collision MC shows >50% feedline collision at N_mux=64 untrimmed
    assert mx["by_nmux"]["64"]["feedline_any_collision_untrimmed_pct"] > 50.0
    assert mx["by_nmux"]["32"]["feedline_any_collision_trimmed_pct"] < 0.1


def test_cryo_heat_budget_1024_closes_and_10000_hits_single_fridge_wall():
    # OBS-011 & OBS-130: Full 5-stage LD400+PT420 budget incl. 0.8K Still, 32 TWPA pumps, XY/ENDOR, 968 DC/32 therm
    c1024 = evaluate_cryo_heat_budget(1_024, n_mux=32, xy_mux=32, use_low_power_hemt=False)
    assert c1024["closes_single_pt420_ld400"] is True
    assert c1024["loads"]["mxc_20mK_uW"] <= 14.0
    assert c1024["loads"]["cp_100mK_uW"] <= 400.0
    assert c1024["loads"]["still_0p8K_mW"] <= 40.0
    assert c1024["loads"]["stage_4K_W"] <= 2.0
    assert c1024["loads"]["stage_50K_W"] <= 40.0
    assert c1024["n_dc_therm_wires"] == 1000
    assert c1024["double_counting_audit_obs130"]["legacy_50mW_double_count_removed"] is True
    assert c1024["double_counting_audit_obs130"]["still_0p8K_stage_checked"] is True

    # Legacy unmitigated audit honestly exceeds 14 uW MXC at 1,024 cells (<1,000 max cells)
    c1024_leg = evaluate_cryo_heat_budget(
        1_024, n_mux=32, xy_mux=32, use_low_power_hemt=False, use_redesigned_pump_and_endor=False
    )
    assert c1024_leg["closes_single_pt420_ld400"] is False
    assert c1024_leg["loads"]["mxc_20mK_uW"] > 14.0
    assert c1024_leg["single_cryostat_max_cells"] < 1_000

    c10000 = evaluate_cryo_heat_budget(10_000, n_mux=32, xy_mux=32, use_low_power_hemt=False)
    assert c10000["closes_single_pt420_ld400"] is False
    assert c10000["loads"]["mxc_20mK_uW"] > 14.0
    assert c10000["loads"]["stage_4K_W"] > 2.0
    assert c10000["min_modular_ld400_pt420_cryostats"] >= 4
    assert 2_000 < c10000["single_cryostat_max_cells"] < 4_000


def test_cellisa_v35_opcodes_echo_cz_and_syndrome_cycle(tmp_path):
    assert len(VALID_OPCODES_V2) == 10
    assert len(VALID_OPCODES_V3) == 4
    assert VALID_OPCODES_V35 == frozenset({"ECHO_CZ", "MUX_READOUT", "SYNDROME_CYCLE"})
    assert len(VALID_OPCODES) == 17
    for op in VALID_OPCODES_V35:
        inst = CellInstruction(opcode=op, args={"ok": True})
        assert inst.opcode == op

    # Build deterministic 4x4 wafer
    rng = np.random.default_rng(14077)
    base = np.array([62e3, 128e3, 248e3, 480e3, 835e3, 1295e3, 1960e3, 2990e3])
    dead = {(0, 1), (1, 2), (2, 1), (2, 3), (3, 0), (3, 2)}
    sites = []
    for r in range(4):
        for c in range(4):
            if (r, c) in dead:
                sites.append(WaferSite(r, c, "blank", None, 0.73))
            else:
                lines = np.sort(base * rng.uniform(0.93, 1.07, size=8))
                cert = Certificate(
                    register_id=f"T35-R{r}C{c}",
                    slot=r * 4 + c,
                    attempts=1,
                    shots=1,
                    min_spacing_Hz=compute_min_transition_spacing_Hz(lines),
                    dd_quality_gate=True,
                    lines_Hz=[float(x) for x in lines],
                )
                sites.append(WaferSite(r, c, "working", cert, 74.0))

    mprog = MultiCellProgrammer(b_field_T=1.5, pulse_mode="shaped")
    out_jsonl = tmp_path / "syn_v35.jsonl"
    # Quiet sweet-spot charge noise certifies >=0.95 ECHO_CZ & >=0.90 syndrome round
    route, mcert, summary = mprog.execute_syndrome_cycle(
        sites, target_cells=4, n_mux=32, tau_ro_us=2.0, s_eps_uev=0.10, echo_pulses=4, out_jsonl=out_jsonl
    )
    assert route.routed
    assert mcert.isa_version == "3.5"
    assert mcert.certified
    assert mcert.verify_signature()
    assert summary["syndrome_round_fidelity"] > 0.90
    assert out_jsonl.is_file()

    # High-noise 1.0 ueV stress point demonstrates >0.15 echo fidelity recovery over bare CZ (OBS-085)
    _, _, stress_summary = mprog.execute_syndrome_cycle(
        sites, target_cells=4, n_mux=32, tau_ro_us=2.0, s_eps_uev=1.0, echo_pulses=1, out_jsonl=None
    )
    assert stress_summary["mean_echo_cz_fidelity"] > stress_summary["mean_bare_cz_fidelity"] + 0.15

    # SHA-256 tamper detection
    mcert.joint_state_fidelity = 0.42
    assert not mcert.verify_signature()


def test_s65_hardware_spec_and_disk_artifacts():
    out = ROOT / "results" / "exp140_cryo_fpga_boed_mux_readout"
    pred = out / "predictions_exp140.json"
    res_fp = out / "exp140.json"
    s65_fp = out / "s65_hardware_spec.json"
    syn_fp = out / "syndrome_v35_demo.jsonl"
    assert pred.is_file() and res_fp.is_file() and s65_fp.is_file() and syn_fp.is_file()
    assert pred.stat().st_mtime < res_fp.stat().st_mtime

    s65 = json.loads(s65_fp.read_text(encoding="utf-8"))
    assert s65["subsystem_id"] == "S6.5"
    assert s65["n_mux_star"] == 32
    assert s65["totals_1024_cell_module"]["cost_usd_nom"] > 0

    mc = MultiCellCertificate(**json.loads(syn_fp.read_text(encoding="utf-8").strip()))
    assert mc.isa_version == "3.5"
    assert mc.verify_signature()


def test_exp140_zero_hardcoded_host_paths():
    files = [
        ROOT / "src" / "machine_control" / "fpga_boed_dsp.py",
        ROOT / "src" / "machine_control" / "programmer.py",
        ROOT / "experiments" / "exp140_cryo_fpga_boed_mux_readout" / "mux_cryo_model140.py",
        ROOT / "experiments" / "exp140_cryo_fpga_boed_mux_readout" / "run_exp140.py",
        ROOT / "experiments" / "exp140_cryo_fpga_boed_mux_readout" / "plot_exp140.py",
        ROOT / "results" / "exp140_cryo_fpga_boed_mux_readout" / "predictions_exp140.json",
        ROOT / "results" / "exp140_cryo_fpga_boed_mux_readout" / "exp140.json",
        ROOT / "results" / "exp140_cryo_fpga_boed_mux_readout" / "s65_hardware_spec.json",
        ROOT / "tests" / "test_exp140.py",
    ]
    md = ROOT / "results" / "exp140_cryo_fpga_boed_mux_readout" / "summary_exp140.md"
    if md.is_file():
        files.append(md)
    _u = chr(98) + "erk"
    bad_a = "/" + "home/" + _u
    bad_b = "/" + "run/media/" + _u
    for fp in files:
        txt = fp.read_text(encoding="utf-8")
        assert bad_a not in txt, f"Hardcoded host path found in {fp.name}"
        assert bad_b not in txt, f"Hardcoded mount path found in {fp.name}"
