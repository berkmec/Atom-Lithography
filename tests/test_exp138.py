"""
Live Verification Suite for Exp138 (H156): Defective/Missing-Cell Rotated
Surface Code Fault-Tolerant Threshold, Exact Blossom MWPM & Machine Scaling.

Run:
  python3 -B -m pytest -p no:cacheprovider -v tests/test_exp138.py
  (zero hardcoded user paths anywhere inside this file.)
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import struct
import zlib

import networkx as nx
import numpy as np
import pytest

from experiments.exp138_defective_surface_code_ft.rotated_surface_code138 import (
    apply_site_dropouts,
    build_rotated_surface_code,
    compile_deformed_circuit_dem,
    compile_ideal_circuit_dem,
    decode_syndrome_mwpm,
    depolarizing_pauli16,
    normalize_and_scale_pauli16,
    simulate_dem_mc,
)
from experiments.exp141_v5_digital_twin.wafer_econ141 import (
    evaluate_logical_qubit_economics,
    evaluate_v5_wafer_economics,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results" / "exp138_defective_surface_code_ft"
JSON_PATH = RESULTS_DIR / "exp138.json"
PRED_PATH = RESULTS_DIR / "predictions_exp138.json"
SUMMARY_PATH = RESULTS_DIR / "summary_exp138.md"
FIG_PATH = RESULTS_DIR / "fig_exp138_surface_code_ft.png"


def test_01_rotated_surface_code_algebra_and_hook_immune_schedule() -> None:
    """Verify exact 2d^2-1 qubit count, CSS commutation, logical ops, and d_circ == d."""
    for d in (3, 5, 7, 9, 11):
        code = build_rotated_surface_code(d)
        assert code.n_data == d * d
        assert code.n_z == (d * d - 1) // 2
        assert code.n_x == (d * d - 1) // 2
        assert code.n_total == 2 * d * d - 1
        assert int(np.sum((code.H_X @ code.H_Z.T) % 2)) == 0
        assert int(np.sum((code.H_X @ code.Z_L) % 2)) == 0
        assert int(np.sum((code.H_Z @ code.X_L) % 2)) == 0
        assert int((code.X_L @ code.Z_L) % 2) == 1

        df0 = apply_site_dropouts(code, set())
        assert df0.commutes_exact
        assert df0.d_eff == d and df0.d_eff_X == d and df0.d_eff_Z == d

    # Verify circuit-level 3D graph distance d_circ == d and zero non-graphlike edges
    p16 = depolarizing_pauli16(0.005)
    for d in (3, 5, 7):
        code = build_rotated_surface_code(d)
        for basis in ("Z", "X"):
            dem = compile_ideal_circuit_dem(code, d, p16, 0.0008, 0.0038, 0.0003, 0.0, basis)
            assert dem.non_graphlike_count == 0
            G = nx.Graph()
            for (u, v) in dem.graph_edges:
                G.add_edge(u, v)
            assert nx.shortest_path_length(G, dem.bnd_a, dem.bnd_b) == d


def test_02_superstabilizer_gauge_deformation_commutes_and_degrades_d_eff() -> None:
    """Verify 100% H_X_def H_Z_def^T == 0 (mod 2) on random dead data + ancilla clusters."""
    rng = np.random.default_rng(13802)
    code7 = build_rotated_surface_code(7)

    # Single interior dead data qubit merges adjacent Z & X stabs into weight-6 super-stabs
    center_q = code7.coord_to_data[(3, 3)]
    df_single = apply_site_dropouts(code7, {center_q})
    assert df_single.commutes_exact
    assert df_single.max_z_weight == 6
    assert df_single.max_x_weight == 6
    assert df_single.d_eff == 6  # losing 1 interior qubit lowers d by 1

    # Stress-test 60 random realizations across low/med/high dropout
    for p_drop in (0.015, 0.12, 0.45):
        deffs = []
        for _ in range(20):
            dd = set(np.flatnonzero(rng.random(code7.n_data) < p_drop).tolist())
            dz = set(np.flatnonzero(rng.random(code7.n_z) < p_drop).tolist())
            dx = set(np.flatnonzero(rng.random(code7.n_x) < p_drop).tolist())
            df = apply_site_dropouts(code7, dd, dz, dx)
            assert df.commutes_exact, f"Commutation broken at p_drop={p_drop}"
            assert 0 <= df.d_eff <= 7
            deffs.append(df.d_eff)
        if p_drop == 0.45:
            assert float(np.mean(deffs)) < 2.0


def test_03_live_blossom_mwpm_corrects_all_weight1_weight2_and_beats_raw() -> None:
    """Verify exact Blossom MWPM corrects 100% of weight-1 & sampled weight-2 faults on d=5."""
    code5 = build_rotated_surface_code(5)
    p16 = depolarizing_pauli16(0.004)
    dem = compile_ideal_circuit_dem(code5, 5, p16, 0.0008, 0.0038, 0.0003, 0.0, "Z")

    # Every single elementary fault must be corrected with 0 logical errors
    for dets, obs, _ in dem.mechanisms:
        pred = decode_syndrome_mwpm(np.array(dets, dtype=int), dem)
        assert pred == obs

    # Sampled pairs of 2 faults on d=5 (t = floor((5-1)/2) = 2) must be 100% corrected
    rng = np.random.default_rng(13803)
    for _ in range(400):
        i, j = rng.integers(0, len(dem.mechanisms), size=2)
        d1, o1, _ = dem.mechanisms[int(i)]
        d2, o2, _ = dem.mechanisms[int(j)]
        syn = {}
        for x in d1 + d2:
            syn[x] = syn.get(x, 0) ^ 1
        defects = np.array(sorted(k for k, v in syn.items() if v == 1), dtype=int)
        assert decode_syndrome_mwpm(defects, dem) == (o1 ^ o2)

    # Live MC below threshold must beat raw uncorrected logical error rate by >= 5x
    mc = simulate_dem_mc(dem, n_shots=600, rng=rng)
    assert mc["eps_L"] < 0.02
    assert mc["raw_uncorrected_rate"] > 5.0 * max(mc["eps_L"], 1e-4)


def test_04_deformed_dem_compiles_and_decodes_cleanly() -> None:
    """Verify circuit-level DEM compilation and MWPM decoding on a defective d=5 code."""
    code5 = build_rotated_surface_code(5)
    df = apply_site_dropouts(code5, {code5.coord_to_data[(2, 2)]})
    assert df.commutes_exact and df.survived
    p16 = depolarizing_pauli16(0.005)
    dem_z = compile_deformed_circuit_dem(df, 5, p16, 0.0008, 0.0038, 0.0003, 0.0, "Z")
    assert dem_z is not None
    rng = np.random.default_rng(13804)
    mc = simulate_dem_mc(dem_z, n_shots=300, rng=rng)
    assert 0.0 <= mc["eps_L"] < 0.15


def test_04b_final_data_readout_obs133_present_in_dem() -> None:
    """OBS-133 check: boundary data-qubit prep & final transversal readout p_meas are included by default."""
    code3 = build_rotated_surface_code(3)
    p16 = depolarizing_pauli16(0.005)
    dem_with = compile_ideal_circuit_dem(code3, 3, p16, 0.0008, 0.0038, 0.0003, 0.0, "Z", include_final_data_ro=True)
    dem_without = compile_ideal_circuit_dem(code3, 3, p16, 0.0008, 0.0038, 0.0003, 0.0, "Z", include_final_data_ro=False)
    assert sum(m[2] for m in dem_with.mechanisms) > sum(m[2] for m in dem_without.mechanisms)


def test_05_pauli16_scaling_preserves_profile_and_normalization() -> None:
    """Verify Exp137 Pauli-16 normalization, symmetrization, and LRU leakage addition."""
    e137 = json.loads((REPO_ROOT / "results/exp137_echoed_m4_bus_gate/exp137.json").read_text())
    raw = e137["part4_exp138_pauli_channels"]["best_protocol_S0p25"]["pauli_16"]
    scaled = normalize_and_scale_pauli16(raw, 0.010, p_leak_lru_extra=0.0005, symmetrize_qubits=True)
    assert abs(sum(scaled.values()) - 1.0) < 1e-12
    assert abs((1.0 - scaled["II"]) - 0.0105) < 1e-12
    assert abs(scaled["XZ"] - scaled["ZX"]) < 1e-12
    assert abs(scaled["IY"] - scaled["YI"]) < 1e-12


def test_06_exp138_json_schema_verdicts_and_physics_consistency() -> None:
    """Verify exp138.json structure, pre-registered verdicts, negative controls & sub-threshold FT."""
    assert PRED_PATH.exists(), "predictions_exp138.json missing"
    assert JSON_PATH.exists(), "exp138.json missing"
    data = json.loads(JSON_PATH.read_text())

    assert data["experiment"] == "exp138_defective_surface_code_ft"
    assert data["hypothesis_id"] == "H156"
    assert data["no_lab_measurement"] is True
    assert data["n_total"] == 7
    assert data["n_passed"] >= 5
    # VC1-003: success_rule_met requires ALL 7 pre-registered gates; FT3/FT5 honest FAILs => partial framework validation only
    assert data["success_rule_met"] is (data["n_passed"] == data["n_total"])
    assert data["partial_framework_validation_only"] is (data["n_passed"] < data["n_total"])
    assert data["part1_algebra_and_threshold"]["all_algebra_exact"] is True
    assert data["part3_defective_superstabilizers"]["all_superstab_commute"] is True

    # Threshold must be physical (0.7% to 2.0%)
    p_th = data["part1_algebra_and_threshold"]["threshold_combined_per_round"]["p_2q_th"]
    assert p_th is not None and 0.0070 <= p_th <= 0.0200

    # Negative controls (Scenario A & B1 & B2) must be strictly above threshold
    p2 = data["part2_scenarios"]
    for bad_key in (
        "A_v4_Bare_P1_S1p0_Q2e5",
        "B1_v5_Unpass_P4_S1p0_6pair_Q2e5",
        "B2_v5_Unpass_P4_S1p0_fast_Q2e5",
    ):
        assert p2[bad_key]["fit_per_round"]["Lambda"] < 1.0

    # Deep-FT target D3 must show strong exponential suppression
    assert p2["D3_Target_FT_P4_p0p005"]["fit_per_round"]["Lambda"] >= 2.0

    # Honest OBS-022/029/047/110/111/133 closure audit: FT3 fails under unclamped physics & real Stim threshold
    assert data["verdicts"]["FT3_V5_ROTA_C_THRESHOLD_CROSSING_AND_QR_HEADROOM"]["passed"] is False
    audit = data["obs_022_029_047_110_111_133_honest_audit"]
    assert audit["stim_circuit_threshold_p2q_band_OBS022"] == [0.006, 0.0098]
    assert audit["ft_scaling_status"] == "HORIZON_TARGET_REQUIRED"
    assert audit["final_data_readout_impact_OBS133"]["p2q_0.0050"]["d3"]["relative_increase_pct"] > 0.0

    # Top-level Exp141 targets must exist and be monotonic
    tgts = data["target_logical_error_rates"]
    for k in ("1e-6", "1e-9", "1e-12"):
        assert k in tgts
        assert tgts[k]["N_active"] == 2 * tgts[k]["d_star"] ** 2 - 1
        assert tgts[k]["N_phys_per_logical"] == tgts[k]["N_cand"] * tgts[k]["N_active"]
    assert tgts["1e-6"]["d_star"] <= tgts["1e-9"]["d_star"] <= tgts["1e-12"]["d_star"]


def test_07_live_exp141_wafer_econ_integration_compatibility() -> None:
    """Verify exp138.json plugs directly into Exp141 wafer_econ141.evaluate_logical_qubit_economics."""
    data = json.loads(JSON_PATH.read_text())
    w_res = evaluate_v5_wafer_economics(n_mc=200, seed=141)
    l_res = evaluate_logical_qubit_economics(data, wafer_econ=w_res, n_mc=200, seed=141)
    bt = l_res["by_target_eps_L"]
    for k in ("1e-6", "1e-9", "1e-12"):
        assert k in bt
        assert bt[k]["d_star"] == data["target_logical_error_rates"][k]["d_star"]
        assert bt[k]["usd_per_logical_qubit_deployed"]["amortized_fab_wright"]["p50"] > 0.0
    assert (
        bt["1e-6"]["usd_per_logical_qubit_deployed"]["amortized_fab_wright"]["p50"]
        <= bt["1e-9"]["usd_per_logical_qubit_deployed"]["amortized_fab_wright"]["p50"]
        <= bt["1e-12"]["usd_per_logical_qubit_deployed"]["amortized_fab_wright"]["p50"]
    )


def test_08_figure_png_2400x1400_stdlib_integrity() -> None:
    """Verify fig_exp138_surface_code_ft.png using pure stdlib PNG chunk/IHDR/IDAT/IEND audit."""
    assert FIG_PATH.exists(), "fig_exp138_surface_code_ft.png missing"
    raw = FIG_PATH.read_bytes()
    assert len(raw) > 50_000, f"PNG unexpectedly small ({len(raw)} bytes)"
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    ihdr_len, ihdr_type = struct.unpack(">I4s", raw[8:16])
    assert ihdr_type == b"IHDR" and ihdr_len == 13
    width, height = struct.unpack(">II", raw[16:24])
    assert (width, height) == (2400, 1400), f"Expected 2400x1400, got {width}x{height}"
    # Walk all chunks and verify CRCs + presence of IDAT and IEND
    pos = 8
    seen_types = []
    while pos < len(raw):
        length = struct.unpack(">I", raw[pos : pos + 4])[0]
        ctype = raw[pos + 4 : pos + 8]
        cdata = raw[pos + 8 : pos + 8 + length]
        crc_file = struct.unpack(">I", raw[pos + 8 + length : pos + 12 + length])[0]
        crc_calc = zlib.crc32(ctype + cdata) & 0xFFFFFFFF
        assert crc_file == crc_calc, f"CRC mismatch in chunk {ctype!r}"
        seen_types.append(ctype)
        pos += 12 + length
    assert b"IDAT" in seen_types and seen_types[-1] == b"IEND"


def test_09_summary_markdown_gfm_tables_zero_errors() -> None:
    """Lint summary_exp138.md for zero malformed GFM tables and required sections."""
    assert SUMMARY_PATH.exists(), "summary_exp138.md missing"
    txt = SUMMARY_PATH.read_text(encoding="utf-8")
    assert len(txt) > 1500
    assert "no_lab_measurement" in txt
    assert "FT1" in txt and "FT7" in txt

    lines = txt.splitlines()
    in_table = False
    expected_cols = 0
    table_count = 0
    for idx, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not in_table:
                in_table = True
                expected_cols = len(cells)
                table_count += 1
                assert expected_cols >= 2, f"Line {idx}: table has <2 columns"
            else:
                assert len(cells) == expected_cols, (
                    f"Line {idx}: GFM column mismatch ({len(cells)} != {expected_cols}): {s}"
                )
        else:
            in_table = False
    assert table_count >= 4, f"Expected >= 4 GFM tables in summary_exp138.md, found {table_count}"


def test_10_portability_zero_hardcoded_user_paths() -> None:
    """Ensure ZERO hardcoded user home or mount paths anywhere in Exp138 code, results, or tests."""
    pat_re = re.compile(r"/(?:home|run/media)/[a-zA-Z0-9_-]+")
    targets = [
        REPO_ROOT / "experiments" / "exp138_defective_surface_code_ft",
        RESULTS_DIR,
        REPO_ROOT / "tests" / "test_exp138.py",
    ]
    hits = []
    for tgt in targets:
        files = [tgt] if tgt.is_file() else [p for p in tgt.rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".md")]
        for f in files:
            content = f.read_text(errors="ignore")
            for m in pat_re.finditer(content):
                hits.append(f"{f.relative_to(REPO_ROOT)} contains {m.group(0)}")
    assert hits == [], f"Hardcoded paths detected: {hits}"
