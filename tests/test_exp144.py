"""Unit & integration tests for Exp144 (H162): qLDPC Bivariate Bicycle [[144,12,12]] on 300 um M4 Bus.

Run with:
  python3 -B -m pytest -p no:cacheprovider tests/test_exp144.py

Strictly portable (Path(__file__).resolve() only; zero hardcoded host paths).
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
EXP_DIR = REPO_ROOT / "experiments" / "exp144_qldpc_bivariate_bicycle_m4"
RES_DIR = REPO_ROOT / "results" / "exp144_qldpc_bivariate_bicycle_m4"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

from bb_codes_and_layout144 import (  # noqa: E402
    BB_CODE_SPECS,
    build_bb_code,
    build_thickness2_m4_layout,
    compute_defective_block_yields,
    find_verified_commuting_schedule,
)
from bp_osd_decoder144 import (  # noqa: E402
    BPOSDDecoder,
    build_bb_circuit_dem,
    run_dem_monte_carlo,
)


def test_bb_css_algebra_and_symplectic_logicals() -> None:
    """Verify exact GF(2) CSS commutativity, weight-6 regularity, ranks, k, and symplectic basis."""
    expected_k = {"BB_72_12_6": 12, "BB_90_8_10": 8, "BB_144_12_12": 12}
    for name, exp_k in expected_k.items():
        c = build_bb_code(BB_CODE_SPECS[name])
        H_X, H_Z = c["H_X"], c["H_Z"]
        L_X, L_Z = c["L_X"], c["L_Z"]
        assert c["k"] == exp_k
        assert c["commutativity_H_X_H_ZT_zero"] is True
        assert c["all_row_col_weight_6"] is True
        assert np.all(((H_X @ H_Z.T) & 1) == 0)
        assert np.array_equal((L_X @ L_Z.T) & 1, np.eye(exp_k, dtype=np.uint8))
        assert np.all(((H_Z @ L_X.T) & 1) == 0)
        assert np.all(((H_X @ L_Z.T) & 1) == 0)


def test_depth7_zero_kickback_bravyi_schedule() -> None:
    """Verify Bravyi Lemma-5 depth-7 schedule has 0 collisions & 0 cross-type ancilla kickback."""
    expected_cnots = {"BB_72_12_6": 432, "BB_90_8_10": 540, "BB_144_12_12": 864}
    for name, exp_c in expected_cnots.items():
        c = build_bb_code(BB_CODE_SPECS[name])
        s = find_verified_commuting_schedule(c)
        assert s["depth_cnot_layers"] == 7
        assert s["total_cnots_per_round"] == exp_c
        assert s["zero_collision_verified"] is True
        assert s["zero_kickback_verified"] is True


def test_thickness2_m4_layout_fits_300um_bus() -> None:
    """Verify 24x12 folded-torus bijection, 576+288 edges, and L_max <= 300 um at P_cell=20 um."""
    c144 = build_bb_code(BB_CODE_SPECS["BB_144_12_12"])
    lay = build_thickness2_m4_layout(c144, pitches_um=(20.0, 25.0, 30.0))
    assert lay["n_qubits"] == 288
    assert lay["n_edges_layer1_local"] == 576
    assert lay["n_edges_layer2_long_range"] == 288
    assert lay["torus_thickness"] == 2
    assert len(set(lay["coords_folded"].values())) == 288

    p20 = next(r for r in lay["pitch_sweep"] if r["pitch_um"] == 20.0)
    assert p20["L_max_um"] <= 300.0
    assert p20["fits_300um_m4_resonator"] is True
    assert p20["f_r_fixed_100pH_ghz"] == 5.0


def test_defect_yield_stark_cliff_and_n8_recovery() -> None:
    """Verify f=1.0% N=6 collapses (<5%) while Exp136 f*=1.5%+2MV/m N=8 exceeds 99.5%."""
    dy = compute_defective_block_yields(n_cells_block=288, n_blocks_cryo=10)
    f10_n6 = next(r for r in dy["f1p0_Ez0_baseline"]["by_N_cand"] if r["N_cand"] == 6)
    f15_n6 = next(r for r in dy["f1p5_Ez2MVm_v5_star"]["by_N_cand"] if r["N_cand"] == 6)
    f15_n8 = next(r for r in dy["f1p5_Ez2MVm_v5_star"]["by_N_cand"] if r["N_cand"] == 8)

    assert f10_n6["block_288_yield_pct"] < 5.0
    assert 93.0 <= f15_n6["block_288_yield_pct"] <= 96.0
    assert f15_n8["block_288_yield_pct"] > 99.5
    assert f15_n8["cryo_10block_120L_yield_pct"] > 96.0


def test_bp_osd_syndrome_validity_and_osd2_gain() -> None:
    """Verify 100% syndrome consistency on BP+OSD-2 and strong gain over standalone BP."""
    c144 = build_bb_code(BB_CODE_SPECS["BB_144_12_12"])
    H_Z, L_Z = c144["H_Z"], c144["L_Z"]
    dem = {"H_dem": H_Z, "L_dem": L_Z, "p_dem": np.full(H_Z.shape[1], 0.04), "n_noisy_rounds": 1}

    res_bp = run_dem_monte_carlo(dem, n_shots=300, seed=123, use_osd=False, bp_max_iter=40)
    res_osd2 = run_dem_monte_carlo(dem, n_shots=300, seed=123, use_osd=True, osd_order=2, osd_lambda=32, bp_max_iter=40)

    assert res_osd2["syndrome_valid_frac"] == 1.0
    assert res_osd2["p_L_block"] < res_bp["p_L_block"]


def test_circuit_dem_zero_noise_and_pauli_channel_consistency() -> None:
    """Verify uniform Pauli weights exactly match depolarizing DEM and zero-syndrome decodes to zero error."""
    c72 = build_bb_code(BB_CODE_SPECS["BB_72_12_6"])
    s72 = find_verified_commuting_schedule(c72)

    dem_depol = build_bb_circuit_dem(
        c72, s72, n_noisy_rounds=2, p_2q=0.005, p_meas=0.005, p_1q_idle_step=0.001, p_prep=0.002, memory_basis="Z"
    )
    unif_16 = {a + b: (1.0 / 15.0 if a + b != "II" else 0.0) for a in "IXYZ" for b in "IXYZ"}
    dem_pauli = build_bb_circuit_dem(
        c72, s72, n_noisy_rounds=2, p_2q=0.005, p_meas=0.005, p_1q_idle_step=0.001, p_prep=0.002,
        memory_basis="Z", p2q_pauli_weights=unif_16,
    )
    assert dem_depol["M_detectors"] == 3 * 36
    assert dem_depol["N_fault_mechanisms"] == dem_pauli["N_fault_mechanisms"]
    assert np.allclose(np.sort(dem_depol["p_dem"]), np.sort(dem_pauli["p_dem"]), atol=1e-12)

    # Zero syndrome must decode cleanly to zero error
    dec = BPOSDDecoder(dem_depol["H_dem"], dem_depol["p_dem"], bp_max_iter=20)
    z_syn = np.zeros((4, dem_depol["M_detectors"]), dtype=np.uint8)
    out = dec.decode_batch(z_syn, use_osd=True)
    assert np.all(out["e_hat"] == 0)
    assert out["bp_converged_frac"] == 1.0


def test_exp144_json_schema_verdicts_and_epistemic_flags() -> None:
    """Verify exp144.json exists, passes success rule (>=6/7 QL verdicts), and sets honest epistemic flags."""
    jpath = RES_DIR / "exp144.json"
    assert jpath.exists(), "Run run_exp144.py first"
    data = json.loads(jpath.read_text())

    assert data["experiment"] == "exp144_qldpc_bivariate_bicycle_m4"
    assert data["hypothesis_id"] == "H162"
    assert data["no_lab_measurement"] is True
    assert data["no_supplier_quotes"] is True
    assert data["success_rule_met"] is True
    assert data["n_passed"] >= 6
    assert data["verdicts"]["QL1_EXACT_BB_CSS_ALGEBRA"] is True
    assert data["verdicts"]["QL2_THICKNESS2_M4_LAYOUT_AND_YIELD"] is True
    assert data["verdicts"]["QL5_CRYOSTAT_AND_TCO_COMPRESSION"] is True
    assert data["verdicts"]["QL6_DEFECTIVE_BLOCK_RESILIENCE"] is True
    assert data["portability_hardcoded_hits"] == []

    # Verify exact single-cryostat 120L packing & 100x cryostat compression vs D3 Surface Code
    p5 = data["part5_cryostat_and_tco_compression"]
    assert p5["gross_code_single_cryo_blocks"] == 10
    assert p5["gross_code_single_cryo_logical_qubits"] == 120
    assert p5["configs"]["BB144_100L_9blk"]["n_cryostats"] == 1
    assert p5["compression_ratios_BB144_9blk_vs_surface_code"]["cryostats_vs_D3_1e-9"] == 100.0
    assert p5["compression_ratios_BB144_9blk_vs_surface_code"]["cryostats_vs_D2_1e-9"] == 679.0


def test_exp144_png_dimensions_and_summary_gfm() -> None:
    """Verify 2400x1400 PNG header validity and summary_exp144.md existence & epistemic disclaimers."""
    png_path = RES_DIR / "fig_exp144_qldpc_m4.png"
    assert png_path.exists()
    raw = png_path.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", raw[16:24])
    assert (w, h) == (2400, 1400)

    md_path = RES_DIR / "summary_exp144.md"
    assert md_path.exists()
    md = md_path.read_text()
    assert "no_lab_measurement" in md
    assert "no_supplier_quotes" in md
    assert "H162" in md


def test_exp144_summary_gfm_tables_zero_errors() -> None:
    """Verify every GFM markdown table in summary_exp144.md has exact consistent column counts."""
    md = (RES_DIR / "summary_exp144.md").read_text()
    in_tbl = False
    exp_cols = 0
    tbl_count = 0
    for idx, line in enumerate(md.splitlines(), 1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cols = len(s.split("|")) - 2
            if not in_tbl:
                in_tbl = True
                exp_cols = cols
                tbl_count += 1
            else:
                assert cols == exp_cols, f"GFM table column mismatch on line {idx}: {cols} != {exp_cols}"
        else:
            in_tbl = False
    assert tbl_count >= 5


def test_exp144_strict_portability_no_hardcoded_host_paths() -> None:
    """Verify ZERO hardcoded host paths across all Exp144 code, results, markdown, and tests."""
    bad_tokens = ("/home/" + "berk", "/run/media/" + "berk", "/" + "Users/")
    files = list(EXP_DIR.glob("*.py")) + list(RES_DIR.glob("*.json")) + list(RES_DIR.glob("*.md")) + [Path(__file__).resolve()]
    hits = []
    for f in files:
        txt = f.read_text(errors="ignore")
        for tok in bad_tokens:
            if tok in txt:
                hits.append(f"{f.name}:{tok}")
    assert hits == [], f"Hardcoded host path detected: {hits}"
