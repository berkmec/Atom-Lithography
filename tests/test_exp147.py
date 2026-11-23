"""Unit & integration tests for Exp147 (H165): Universal [[288,12,18]] d=18 qLDPC +
Magic State Factories & FeMoco / RSA-2048 Resource Budgets.

Run with:
  python3 -B -m pytest -p no:cacheprovider tests/test_exp147.py

Strictly portable (Path(__file__).resolve() only; zero hardcoded host paths).
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
EXP_DIR = REPO_ROOT / "experiments" / "exp147_universal_qldpc_d18_magic_state"
RES_DIR = REPO_ROOT / "results" / "exp147_universal_qldpc_d18_magic_state"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

from bb288_algebra_layout147 import (  # noqa: E402
    build_bb288_thickness2_m4_layout,
    compute_bb288_defect_yields,
    verify_bb288_algebra_and_schedule,
)
from experiments.exp144_qldpc_bivariate_bicycle_m4.bp_osd_decoder144 import (  # noqa: E402
    BPOSDDecoder,
    build_bb_circuit_dem,
)
from magic_state_and_algos147 import (  # noqa: E402
    evaluate_15to1_stage,
    optimize_magic_state_factories,
)


def test_bb288_exact_css_algebra_ranks_and_symplectic_basis() -> None:
    """Verify [[288,12,18]] exact GF(2) commutativity, weight-6, rank=138, k=12, symplectic L_X L_Z^T=I_12."""
    v = verify_bb288_algebra_and_schedule()
    s = v["summary"]
    c = v["code"]
    assert s["n_data"] == 288
    assert s["n_total_cells"] == 576
    assert s["k"] == 12
    assert s["rank_X"] == 138
    assert s["rank_Z"] == 138
    assert s["commutativity_H_X_H_ZT_zero"] is True
    assert s["all_row_col_weight_6"] is True
    assert s["symplectic_logical_valid"] is True
    assert s["min_basis_logical_weight_X"] == 18
    assert s["min_basis_logical_weight_Z"] == 18
    assert np.all(((c["H_X"] @ c["H_Z"].T) & 1) == 0)


def test_bb288_depth7_zero_kickback_schedule() -> None:
    """Verify Bravyi Lemma-5 depth-7 schedule on [[288,12,18]] has 1,728 CNOTs, 0 collisions, 0 kickback."""
    v = verify_bb288_algebra_and_schedule()
    s = v["summary"]
    assert s["schedule_depth"] == 7
    assert s["schedule_total_cnots"] == 1728
    assert s["schedule_zero_collisions"] is True
    assert s["schedule_zero_kickback"] is True


def test_bb288_z12_automorphism_layout_fits_300um_bus() -> None:
    """Verify b'=5b mod 12 automorphism gives exact unit torus distance on all 1,152 L1 edges and L_max <= 300 um."""
    v = verify_bb288_algebra_and_schedule()
    lay = build_bb288_thickness2_m4_layout(v["code"], pitches_um=(15.0, 20.0, 25.0))
    assert lay["n_qubits"] == 576
    assert lay["n_edges_layer1_local"] == 1152
    assert lay["n_edges_layer2_long_range"] == 576
    assert lay["layer1_all_unit_torus_distance"] is True
    assert lay["layer1_torus_crossings"] == 0
    assert len(set(lay["coords_folded"].values())) == 576

    p15 = next(r for r in lay["pitch_sweep"] if r["pitch_um"] == 15.0)
    p20 = next(r for r in lay["pitch_sweep"] if r["pitch_um"] == 20.0)
    assert p15["L_max_um"] <= 300.0 and p15["fits_300um_m4_resonator"] is True
    assert p20["L_max_um"] <= 300.0 and p20["fits_300um_m4_resonator"] is True


def test_bb288_576cell_defect_yield_stark_cliff() -> None:
    """Verify f=1.0% N=6 collapses (<0.1%) while Exp136 f*=1.5%+2MV/m hits >99.0% at N=8 and >99.8% at N=9."""
    dy = compute_bb288_defect_yields(n_cells_block=576, n_blocks_cryo=5, n_blocks_femoco_mem=16)
    assert dy["f1p0_Ez0_no_stark"]["by_N_cand"]["N6"]["block_576_yield_pct"] < 0.1
    assert dy["f1p5_Ez2MVm_v5_star"]["by_N_cand"]["N8"]["block_576_yield_pct"] > 99.0
    assert dy["f1p5_Ez2MVm_v5_star"]["by_N_cand"]["N9"]["block_576_yield_pct"] > 99.8
    assert dy["f1p5_Ez2MVm_v5_star"]["by_N_cand"]["N8"]["femoco_16of18_spared_yield_pct"] > 99.9


def test_bb288_circuit_dem_zero_syndrome_and_shape() -> None:
    """Verify [[288,12,18]] 3D circuit DEM builds cleanly (M=4*144=576 for R=3) and decodes zero syndrome."""
    v = verify_bb288_algebra_and_schedule()
    dem = build_bb_circuit_dem(
        v["code"], v["schedule"], n_noisy_rounds=3, p_2q=0.00337, p_meas=0.00386, p_1q_idle_step=4e-5, p_prep=0.00083
    )
    assert dem["M_detectors"] == 4 * 144
    assert dem["N_fault_mechanisms"] > 3000
    dec = BPOSDDecoder(dem["H_dem"], dem["p_dem"], bp_max_iter=20)
    z_syn = np.zeros((3, dem["M_detectors"]), dtype=np.uint8)
    out = dec.decode_batch(z_syn, use_osd=True)
    assert np.all(out["e_hat"] == 0)
    assert out["bp_converged_frac"] == 1.0


def test_magic_state_factory_physics_honest_1stage_fail_and_2stage_pass() -> None:
    """Verify single-stage 15-to-1 cannot hit 1e-10 at D3 while two-stage Litinski & Cultivation+116to12 both hit <=1e-10."""
    fac = optimize_magic_state_factories(
        p_2q=0.0033687, p_1q=0.0008295, a_sc=0.017377, lambda_sc=2.8253, t_cyc_sc_us=6.7022
    )
    assert fac["F1_single_stage_15to1_raw"]["meets_1e10"] is False
    assert fac["F1_single_stage_15to1_raw"]["p_out"] > 1e-6
    assert fac["F2_litinski_twostage_15to1_x_116to12"]["meets_1e10"] is True
    assert fac["F2_litinski_twostage_15to1_x_116to12"]["rate_khz"] >= 5.0
    assert fac["F4_gidney_cultivation_plus_116to12_highthroughput"]["meets_1e10"] is True
    assert fac["F4_gidney_cultivation_plus_116to12_highthroughput"]["rate_khz"] >= 5.0

    # Verify compact vs fast space-time pairing (zero mixing!)
    c_s = evaluate_15to1_stage(0.004, 15, 7, 7, 0.017377, 2.8253, 6.7022, variant="compact")
    f_s = evaluate_15to1_stage(0.004, 15, 7, 7, 0.017377, 2.8253, 6.7022, variant="fast")
    assert c_s["n_rounds"] == 11 * 7 and f_s["n_rounds"] == 6 * 7
    assert c_s["active_cells"] < f_s["active_cells"]


def test_exp147_json_schema_honest_verdicts_and_epistemic_flags() -> None:
    """Verify exp147.json exists, enforces epistemic flags, and preserves honest verdicts & >=10x algo compression."""
    jpath = RES_DIR / "exp147.json"
    assert jpath.exists(), "Run run_exp147.py first"
    d = json.loads(jpath.read_text())

    assert d["experiment"] == "exp147_universal_qldpc_d18_magic_state"
    assert d["hypothesis_id"] == "H165"
    assert d["no_lab_measurement"] is True
    assert d["no_supplier_quotes"] is True
    assert d["verdicts"]["UQ1_EXACT_BB288_ALGEBRA_AND_SCHEDULE"] is True
    assert d["verdicts"]["UQ2_THICKNESS2_M4_LAYOUT_AND_576_YIELD"] is True
    assert d["verdicts"]["UQ3_D6_TO_D18_CIRCUIT_DEM_SCALING"] is True
    assert d["verdicts"]["UQ6_RSA2048_SHOR_CRYO_POWER_COMPRESSION"] is True
    assert d["verdicts"]["UQ7_PORTABILITY_VISUALIZATION_AND_TESTS"] is True
    assert d["portability_hardcoded_hits"] == []

    # Verify >= 10x compression on both FeMoco and RSA-2048
    p5 = d["part5_flagship_algorithms"]
    assert p5["FeMoco_192L_1e8T"]["compression_vs_SC_Cultivation"]["cryostats_x"] >= 10.0
    assert p5["RSA2048_4096L_1e10T"]["compression_d24_Cult_vs_SC"]["cryostats_x"] >= 10.0
    assert p5["RSA2048_4096L_1e10T"]["compression_d24_Cult_vs_SC"]["power_x"] >= 10.0


def test_exp147_png_dimensions_and_summary_md_integrity() -> None:
    """Verify 2400x1400 PNG header and summary_exp147.md epistemic disclaimers."""
    png_path = RES_DIR / "fig_exp147_universal_qldpc_magic.png"
    assert png_path.exists()
    raw = png_path.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", raw[16:24])
    assert (w, h) == (2400, 1400)

    md_path = RES_DIR / "summary_exp147.md"
    assert md_path.exists()
    md = md_path.read_text()
    assert "no_lab_measurement" in md
    assert "no_supplier_quotes" in md
    assert "H165" in md


def test_exp147_summary_gfm_tables_zero_errors() -> None:
    """Verify every GFM markdown table in summary_exp147.md has exact consistent column counts."""
    md = (RES_DIR / "summary_exp147.md").read_text()
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


def test_exp147_strict_portability_no_hardcoded_host_paths() -> None:
    """Verify ZERO hardcoded host paths across all Exp147 code, results, markdown, and tests."""
    bad_tokens = ("/home/" + "berk", "/run/media/" + "berk", "/" + "Users/")
    files = list(EXP_DIR.glob("*.py")) + list(RES_DIR.glob("*.json")) + list(RES_DIR.glob("*.md")) + [Path(__file__).resolve()]
    hits = []
    for f in files:
        txt = f.read_text(errors="ignore")
        for tok in bad_tokens:
            if tok in txt:
                hits.append(f"{f.name}:{tok}")
    assert hits == [], f"Hardcoded host path detected: {hits}"
