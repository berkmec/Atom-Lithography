"""Regression, consistency, portability, and integrity tests for Exp134 (H152).

100% portable: resolves repository root strictly via Path(__file__).resolve().parents[1].
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = ROOT / "experiments" / "exp134_fab_economics_tco"
RES_DIR = ROOT / "results" / "exp134_fab_economics_tco"
BOM_CANONICAL = ROOT / "research" / "atom_lithography_machine" / "BOM.csv"
EXP_JSON = RES_DIR / "exp134.json"
PRED_JSON = RES_DIR / "predictions_exp134.json"
SUMMARY_MD = RES_DIR / "summary_exp134.md"

EXPECTED_BOM_SHA256 = "cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2"


def _load_exp() -> dict:
    assert EXP_JSON.exists(), f"Missing {EXP_JSON}"
    return json.loads(EXP_JSON.read_text(encoding="utf-8"))


def test_canonical_bom_sha256_untouched() -> None:
    digest = hashlib.sha256(BOM_CANONICAL.read_bytes()).hexdigest()
    assert digest == EXPECTED_BOM_SHA256
    data = _load_exp()
    assert data["baseline_gate"]["bom_csv_sha256"] == EXPECTED_BOM_SHA256
    assert data["baseline_gate"]["sha256_ok"] is True
    assert data["baseline_gate"]["gate_ok"] is True


def test_portability_no_hardcoded_user_paths() -> None:
    forbidden = ("/" + "home" + "/" + "berk", "/" + "run" + "/" + "media" + "/" + "berk")
    targets = [
        EXP_DIR / "tco_model134.py",
        EXP_DIR / "plot_exp134.py",
        Path(__file__).resolve(),
    ]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for bad in forbidden:
            assert bad not in text, f"Hardcoded path '{bad}' found in {path.name}"


def test_preregistration_and_epistemic_flags() -> None:
    assert PRED_JSON.exists()
    pred = json.loads(PRED_JSON.read_text(encoding="utf-8"))
    data = _load_exp()
    assert pred["hypothesis_id"] == "H152"
    assert pred["no_lab_measurement"] is True
    assert pred["no_supplier_quotes"] is True
    assert data["no_lab_measurement"] is True
    assert data["no_supplier_quotes"] is True
    assert data["budget_cap_v3_vs_v4"]["n_samples"] == 50000
    assert data["budget_cap_v3_vs_v4"]["seed"] == 2026134

    verdicts = data["verdicts"]
    assert verdicts["CX1_baseline_gate"] is True
    assert verdicts["CX2_v4_budget_cap_survival"] is True
    assert verdicts["CX3_bayesian_unit_cost_collapse"] is True
    assert verdicts["CX4_amdahl_wafer_floor"] is False
    assert verdicts["CX5_wright_learning_100x"] is True
    assert verdicts["CX6_mc_convergence_50k"] is True
    assert verdicts["success"] is True


def test_tco_and_budget_cap_bounds_and_monotonicity() -> None:
    data = _load_exp()
    tco = data["tco_5yr_summary_no_wafers"]
    for key, stats in tco.items():
        pcts = [stats["p05"], stats["p10"], stats["p25"], stats["p50"], stats["p75"], stats["p90"], stats["p95"], stats["p99"]]
        assert all(pcts[i] <= pcts[i + 1] for i in range(len(pcts) - 1)), f"Non-monotonic percentiles in {key}"

    assert tco["m1_lab_5yr_tco_usd"]["p50"] < tco["v3_fab_tool_n1_5yr_tco_usd"]["p50"]
    assert tco["v3_fab_tool_n1_5yr_tco_usd"]["p50"] < tco["v4_fab_tool_n1_5yr_tco_usd"]["p50"]
    assert tco["v4_fab_tool_n1_5yr_tco_usd"]["p50"] < tco["v3_foak_program_5yr_tco_usd"]["p50"]
    assert tco["v3_foak_program_5yr_tco_usd"]["p50"] < tco["v4_foak_program_5yr_tco_usd"]["p50"]
    assert tco["v4_foak_program_5yr_tco_usd"]["p95"] < 100e6

    bc = data["budget_cap_v3_vs_v4"]
    ep = bc["exceedance_probabilities"]
    for k, prob in ep.items():
        if k.startswith("P_"):
            assert 0.0 <= prob <= 1.0, f"Invalid probability {k}={prob}"
    assert ep["P_v4_BOM_gt_50M"] < 0.001
    assert ep["P_v4_Prog_stoch_gt_100M"] < 0.05
    assert ep["P_v4_Prog_stoch_gt_100M"] >= ep["P_v3_Prog_stoch_gt_100M"]
    assert ep["SE_P_v4_Prog_gt_100M"] < 0.002
    assert bc["convergence_25k_vs_50k"]["rel_diff_p50"] <= 0.01


def test_regime1_write_ceiling_and_value_leverage() -> None:
    data = _load_exp()
    r1 = data["regime1_steady_state_capacity"]
    v3_reg = r1["v3_0_baseline"]["throughput"]["net_reg_day"]
    v4_5x_reg = r1["v4_0_bayes5x_15ms"]["throughput"]["net_reg_day"]
    v4_10x_15ms = r1["v4_0_bayes10x_15ms_write_clamped"]["throughput"]
    v4_10x_10ms = r1["v4_0_bayes10x_10ms"]["throughput"]

    assert abs(v4_5x_reg / v3_reg - 5.0) < 1e-9
    assert v4_10x_15ms["bottleneck"] == "write"
    assert 7.5 < v4_10x_15ms["net_reg_day"] / v3_reg < 8.0
    assert v4_10x_10ms["bottleneck"] == "spectroscopy"
    assert abs(v4_10x_10ms["net_reg_day"] / v3_reg - 10.0) < 1e-9

    lev = data["v3_to_v4_value_leverage"]
    assert lev["capacity_5x_unit_cost_reduction_frac"] >= 0.75
    assert lev["capacity_10x_10ms_unit_cost_reduction_frac"] >= 0.85
    assert lev["hw_capex_leverage_ratio_5x"] > 40.0
    assert lev["tco5_leverage_ratio_5x"] > 70.0


def test_regime2_silicon_wafer_floor_and_wright_monotonicity() -> None:
    data = _load_exp()
    r2 = data["regime2_wafer_batch_amdahl"]
    std_v3 = r2["standard_2e6_8h"]["v3_0"]["wafer_price_sweep"]["usd_12000"]
    std_v4 = r2["standard_2e6_8h"]["v4_0_5x"]["wafer_price_sweep"]["usd_12000"]
    assert std_v3["wafer_cost_floor_per_chip_usd"] == 60.0
    assert std_v4["wafer_share_of_chip_cost"] > 0.70

    dense_v3 = r2["dense_5e7_1h"]["v3_0"]["wafer_price_sweep"]["usd_12000"]
    dense_v4 = r2["dense_5e7_1h"]["v4_0_5x"]["wafer_price_sweep"]["usd_12000"]
    assert dense_v4["wafer_cost_floor_per_chip_usd"] == 2.4
    assert dense_v4["wafer_share_of_chip_cost"] > 0.90
    mach_v3 = dense_v3["usd_per_chip_10k_p50"] - dense_v3["wafer_cost_floor_per_chip_usd"]
    mach_v4 = dense_v4["usd_per_chip_10k_p50"] - dense_v4["wafer_cost_floor_per_chip_usd"]
    assert (1.0 - mach_v4 / mach_v3) > 0.65

    wc = data["wright_learning_curves"]
    for bk in ("b_82", "b_85", "b_88"):
        ns = ["1", "5", "10", "25", "50", "100"]
        hws = [wc[bk][n]["hw_v4_nom_usd"] for n in ns]
        tcos = [wc[bk][n]["tco5_no_wafer_p50_usd"] for n in ns]
        assert all(hws[i] > hws[i + 1] for i in range(len(hws) - 1))
        assert all(tcos[i] > tcos[i + 1] for i in range(len(tcos) - 1))

    assert wc["b_82"]["100"]["wright_hw_multiplier"] < wc["b_85"]["100"]["wright_hw_multiplier"] < wc["b_88"]["100"]["wright_hw_multiplier"]
    assert wc["b_85"]["100"]["wright_hw_multiplier"] <= 0.40
    assert wc["b_85"]["100"]["dense_fab_d17_modb_logical_p50"] < 1.0


def test_figures_and_summary_gfm_integrity() -> None:
    for fname in ("fig_exp134_tco_cost_per_qubit.png", "fig_exp134_v3_vs_v4_scaling.png"):
        fpath = RES_DIR / fname
        assert fpath.exists() and fpath.stat().st_size > 100_000
        raw = fpath.read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        assert raw[12:16] == b"IHDR"
        w, h = struct.unpack(">II", raw[16:24])
        assert (w, h) == (2200, 1260)

    assert SUMMARY_MD.exists()
    lines = SUMMARY_MD.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 80
    # Strict GFM table pipe-count check (zero mismatches)
    expected_cols = None
    mismatches = 0
    for ln in lines:
        s = ln.strip()
        if s.startswith("|") and s.endswith("|"):
            cols = s.count("|") - 1
            if expected_cols is None:
                expected_cols = cols
            elif cols != expected_cols:
                mismatches += 1
        else:
            expected_cols = None
    assert mismatches == 0, f"Found {mismatches} GFM table column mismatches in {SUMMARY_MD.name}"
