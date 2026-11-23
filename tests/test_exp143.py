"""
Live Verification Suite for Exp143 (H161): D3 Multi-Harmonic Fourier GRAPE M4 Bus
CZ Gate, Live Exp138 MWPM Verification & Option-HPC 100 Gbps RoCEv2 Real-Time Decoder.

Run:
  python3 -B -m pytest -p no:cacheprovider -v tests/test_exp143.py
  (zero hardcoded user paths anywhere inside this file.)
"""

from __future__ import annotations

import json
from pathlib import Path
import struct
import zlib

import numpy as np

from experiments.exp137_echoed_m4_bus_gate.echo_bus_solver137 import FlipFlopPairSpec
from experiments.exp138_defective_surface_code_ft.rotated_surface_code138 import (
    build_rotated_surface_code,
    compile_ideal_circuit_dem,
    normalize_and_scale_pauli16,
    simulate_dem_mc,
)
from experiments.exp143_d3_grape_m4_and_hpc_decoder.grape_m4_bus143 import (
    optimize_grape_slice_cuda,
    simulate_grape_cz_cuda,
)
from experiments.exp143_d3_grape_m4_and_hpc_decoder.hpc_decoder143 import (
    analyze_option_hpc_decoder_wall,
    build_s9hpc_hardware_spec,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results" / "exp143_d3_grape_m4_and_hpc_decoder"
JSON_PATH = RESULTS_DIR / "exp143.json"
PRED_PATH = RESULTS_DIR / "predictions_exp143.json"
S9HPC_PATH = RESULTS_DIR / "s9hpc_hardware_spec.json"
SUMMARY_PATH = RESULTS_DIR / "summary_exp143.md"
FIG_PATH = RESULTS_DIR / "fig_exp143_d3_grape_hpc.png"


def test_01_live_grape_pulse_respects_coupling_cap_awg_bw_and_unitary() -> None:
    """Live CUDA/CPU K=8 Fourier GRAPE check: |s(t)|<=1, >=99.5% BW<300 MHz, noiseless F_avg>=0.999."""
    pair = FlipFlopPairSpec(
        g1_mhz=3.2, g2_mhz=2.0,
        d1_1_ghz_per_ghz=-1.8e-4, d2_1_inv_ghz=3.5e-5,
        d1_2_ghz_per_ghz=-1.5e-4, d2_2_inv_ghz=1.5e-5,
        dg1_mhz_per_ghz=-0.25, dg2_mhz_per_ghz=-0.06,
        gamma1_1_khz=0.10, gamma1_2_khz=0.05,
        label="test_fast_pair",
    )
    pl = optimize_grape_slice_cuda(pair, q_r_target=1e6, gamma_phi_nuc_khz=0.5, k_harmonics=8, n_steps=20, n_iters=120, seed=14301)
    assert pl.max_abs_s1 <= 1.0 + 1e-9
    assert pl.max_abs_s2 <= 1.0 + 1e-9
    assert pl.bw_300mhz_energy_frac >= 0.995
    assert pl.noiseless_slice_f_ent >= 0.999
    r0 = simulate_grape_cz_cuda(pair, pl, q_r=0.0, s_eps_uev=0.0, eps_rot=0.0)
    assert r0["F_avg"] >= 0.9985
    assert r0["p_leak"] <= 1e-3


def test_02_live_12x12_noisy_strang_lindblad_cptp_and_d3_regime() -> None:
    """Live 12x12 noisy Strang-Lindblad + M=40 1/f OU simulation passes strict CPTP & hits D3 fidelity."""
    pair = FlipFlopPairSpec(
        g1_mhz=3.58, g2_mhz=1.93,
        d1_1_ghz_per_ghz=-1.92e-4, d2_1_inv_ghz=4.33e-5,
        d1_2_ghz_per_ghz=-1.65e-4, d2_2_inv_ghz=1.48e-5,
        dg1_mhz_per_ghz=-0.31, dg2_mhz_per_ghz=-0.06,
        gamma1_1_khz=0.13, gamma1_2_khz=0.053,
        label="test_pair2",
    )
    pl = optimize_grape_slice_cuda(pair, q_r_target=1e6, gamma_phi_nuc_khz=0.0225, k_harmonics=8, n_steps=20, n_iters=140, seed=14302)
    r = simulate_grape_cz_cuda(
        pair, pl, q_r=1e6, s_eps_uev=0.25, n_traj=64, gamma_phi_nuc_khz=0.0225, sweet_spot_mode="double_sweet_spot", seed=14302
    )
    ca = r["cptp_audit"]
    assert ca["max_trace_err"] < 1e-10
    assert ca["max_herm_err"] < 1e-10
    assert ca["min_eigval"] > -1e-9
    assert abs(r["pauli_sum"] - 1.0) < 1e-10
    assert r["p_total_err"] < 0.0050
    assert r["F_avg"] > 0.9960


def test_03_live_exp138_mwpm_decoding_of_exp143_pauli16() -> None:
    """Feed extracted Exp143 GRAPE Pauli-16 channel directly into Exp138 Blossom MWPM and verify suppression."""
    assert JSON_PATH.exists()
    data = json.loads(JSON_PATH.read_text())
    ch = data["part2_noisy_1f_sweep"]["grape_echoed_exp136_0p0225kHz_nuc"]["Q10e5_S0p25"]
    p16 = normalize_and_scale_pauli16(ch["pauli_16"], ch["p_total_err"], symmetrize_qubits=True)
    code5 = build_rotated_surface_code(5)
    dem = compile_ideal_circuit_dem(code5, 5, p16, p_1q=0.00083, p_meas=0.003861, p_idle_Z=0.00018, memory_basis="Z")
    mc = simulate_dem_mc(dem, n_shots=400, rng=np.random.default_rng(14303))
    assert mc["eps_L"] < 0.015
    assert mc["raw_uncorrected_rate"] > 4.0 * max(mc["eps_L"], 1e-4)


def test_04_live_option_hpc_decoder_backlog_wall_and_bandwidth() -> None:
    """Verify Option-HPC latency chain proves CPU d=37 wall and parallel GPU/FPGA backlog-free closure."""
    hpc = analyze_option_hpc_decoder_wall(t_gate_d3_us=0.75, p_2q_d3=0.0035)
    d21 = next(r for r in hpc["surface_code_scaling"] if r["d"] == 21)
    d37 = next(r for r in hpc["surface_code_scaling"] if r["d"] == 37)
    qldpc = hpc["qldpc_gross_144_12_12"]
    assert not d21["backlog_free_cpu_2p62us"]
    assert not d37["backlog_free_cpu_8p93us"]
    assert d37["backlog_free_hpc_8p93us"]
    assert qldpc["backlog_free_hpc_2p62us"]
    assert d37["bw_100L_hard_v5_gbps"] <= 25.0
    assert qldpc["option_hpc_4u_modules_108L"] == 1
    spec = build_s9hpc_hardware_spec(hpc)
    assert spec["totals_base_4u_option_hpc_module"]["cryo_load_W"] == 0.0


def test_05_exp143_json_schema_verdicts_and_cptp_clean() -> None:
    """Verify exp143.json completeness, honest pre-registered verdicts, and CPTP invariants."""
    assert PRED_PATH.exists() and JSON_PATH.exists()
    data = json.loads(JSON_PATH.read_text())
    assert data["experiment"] == "exp143_d3_grape_m4_and_hpc_decoder"
    assert data["hypothesis_id"] == "H161"
    assert data["no_lab_measurement"] is True
    assert data["no_supplier_quotes"] is True
    assert data["n_total"] == 7
    # Honest pre-registered evaluation: DH4, DH5, DH6, DH7 PASS (4/7 PASS, 3/7 honest physical FAIL)
    assert data["n_passed"] == sum(1 for v in data["verdicts"].values() if v["passed"])
    assert data["verdicts"]["DH4_LIVE_EXP138_MWPM_LAMBDA_D3_PHYS"]["passed"] is True
    assert data["verdicts"]["DH5_OPTION_HPC_REALTIME_DECODER_WALL_AND_BACKLOG"]["passed"] is True
    assert data["verdicts"]["DH6_S9HPC_HARDWARE_SPEC_COMPLETE_FOR_CAD_BOM_V6"]["passed"] is True
    assert data["verdicts"]["DH7_CPTP_AUDIT_PORTABILITY_VISUAL_AND_TESTS"]["passed"] is True
    assert data["part2_noisy_1f_sweep"]["all_cptp_clean"] is True
    assert data["part1_grape_optimization"]["max_abs_s_all"] <= 1.0 + 1e-9
    assert data["part1_grape_optimization"]["min_bw_300mhz_energy_frac"] >= 0.995
    # High-g conservative & echoed Q=1e6 channels crack D3 (<0.50% / <0.40%) and cut 100L fleet >=6x
    c10 = data["part2_noisy_1f_sweep"]["grape_conservative_0p5kHz_nuc"]["Q10e5_S0p25"]
    e10 = data["part2_noisy_1f_sweep"]["grape_echoed_exp136_0p0225kHz_nuc"]["Q10e5_S0p25"]
    e10_nom = data["part2_noisy_1f_sweep"]["grape_echoed_exp136_0p0225kHz_nuc"]["Q10e5_S0p39"]
    assert c10["high_g_3pair_subset"]["p_total_err"] <= 0.0050
    assert e10["p_total_err"] <= 0.0035
    assert e10_nom["p_total_err"] <= 0.0045
    mwpm_c = data["part3_live_exp138_mwpm_verification"]["D3_phys_cons_Q1e6_S0p25_5pair"]
    mwpm_e = data["part3_live_exp138_mwpm_verification"]["D3_phys_echo_Q1e6_S0p25_5pair"]
    assert mwpm_c["fit_per_round"]["Lambda"] >= 2.20
    assert mwpm_c["scaling_N6_f1p5"]["targets"]["1e-9"]["cryostats_100L_unsplit_2887"] <= 130
    assert mwpm_e["fit_per_round"]["Lambda"] >= 2.50
    assert mwpm_e["scaling_N6_f1p5"]["targets"]["1e-9"]["cryostats_100L_unsplit_2887"] == 100


def test_06_s9hpc_hardware_spec_cad_bom_v6_schema() -> None:
    """Verify s9hpc_hardware_spec.json matches S6.5 CAD/BOM schema with zero cryo load."""
    assert S9HPC_PATH.exists()
    spec = json.loads(S9HPC_PATH.read_text())
    assert spec["subsystem_id"] == "S9.HPC"
    assert spec["no_supplier_quotes"] is True
    assert spec["no_lab_measurement"] is True
    tot = spec["totals_base_4u_option_hpc_module"]
    assert tot["total_mass_kg"] > 0 and tot["cryo_cold_mass_kg"] == 0.0
    assert tot["room_temp_power_W"] > 0 and tot["cryo_load_W"] == 0.0
    assert 0 < tot["cost_usd_low"] <= tot["cost_usd_nom"] <= tot["cost_usd_high"]
    assert len(spec["items"]) >= 3
    assert abs(sum(it["mass_kg_total"] for it in spec["items"]) - tot["total_mass_kg"]) < 1e-6
    assert abs(sum(it["power_W_total"] for it in spec["items"]) - tot["room_temp_power_W"]) < 1e-6
    assert sum(it["cost_usd_nom"] for it in spec["items"]) == tot["cost_usd_nom"]


def test_07_figure_png_2400x1400_stdlib_crc_integrity() -> None:
    """Verify fig_exp143_d3_grape_hpc.png via pure-stdlib PNG header & chunk CRC audit."""
    assert FIG_PATH.exists()
    raw = FIG_PATH.read_bytes()
    assert len(raw) > 50_000
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    ihdr_len, ihdr_type = struct.unpack(">I4s", raw[8:16])
    assert ihdr_type == b"IHDR" and ihdr_len == 13
    width, height = struct.unpack(">II", raw[16:24])
    assert (width, height) == (2400, 1400)
    pos = 8
    seen = []
    while pos < len(raw):
        length = struct.unpack(">I", raw[pos : pos + 4])[0]
        ctype = raw[pos + 4 : pos + 8]
        cdata = raw[pos + 8 : pos + 8 + length]
        crc_f = struct.unpack(">I", raw[pos + 8 + length : pos + 12 + length])[0]
        assert crc_f == (zlib.crc32(ctype + cdata) & 0xFFFFFFFF), f"CRC fail on {ctype!r}"
        seen.append(ctype)
        pos += 12 + length
    assert b"IDAT" in seen and seen[-1] == b"IEND"


def test_08_summary_markdown_gfm_tables_zero_errors() -> None:
    """Lint summary_exp143.md for zero malformed GFM tables and mandatory epistemic tags."""
    assert SUMMARY_PATH.exists()
    txt = SUMMARY_PATH.read_text(encoding="utf-8")
    assert len(txt) > 1500
    assert "no_lab_measurement" in txt
    assert "DH1" in txt and "DH7" in txt
    in_table = False
    expected_cols = 0
    table_count = 0
    for idx, line in enumerate(txt.splitlines(), 1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not in_table:
                in_table = True
                expected_cols = len(cells)
                table_count += 1
                assert expected_cols >= 2
            else:
                assert len(cells) == expected_cols, f"Line {idx}: GFM column mismatch"
        else:
            in_table = False
    assert table_count >= 4


def test_09_portability_zero_hardcoded_user_paths() -> None:
    """Ensure ZERO hardcoded user home/mount paths anywhere in Exp143 code, results, or tests."""
    forbidden = ("/" + "home" + "/" + "berk", "/" + "run" + "/" + "media" + "/" + "berk")
    targets = [
        REPO_ROOT / "experiments" / "exp143_d3_grape_m4_and_hpc_decoder",
        RESULTS_DIR,
        REPO_ROOT / "tests" / "test_exp143.py",
    ]
    hits = []
    for tgt in targets:
        files = [tgt] if tgt.is_file() else [p for p in tgt.rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".md")]
        for f in files:
            content = f.read_text(errors="ignore")
            for pat in forbidden:
                if pat in content:
                    hits.append(f"{f.relative_to(REPO_ROOT)} contains {pat}")
    assert hits == [], f"Hardcoded paths found: {hits}"
