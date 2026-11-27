"""Regression, live-solver execution, consistency, portability, and integrity tests for Exp134 (H152).

Upgraded for OBS-060, OBS-062, OBS-068 & OBS-148:
- Directly imports and executes deterministic & Monte Carlo solver entrypoints from tco_model134.py
  in memory (NOT merely reading cached JSON!).
- Validates v7.0 BOM ($5.693M Full / $5.393M Phase-1 Base+Safety), safety starter-item overlap
  reconciliation ($76.2k), unbudgeted safety cert + TWPA/MEMS NRE (+$890k), annual EHS/cryo/scrubber
  OPEX, 3-tier wafer diameter reconciliation (50 mm FOAK vs 100 mm vs 200 mm), and honest real 1% 29Si
  bath + 5%-dead stitch throughput.

100% portable: resolves repository root strictly via Path(__file__).resolve().parents[1].
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
EXP_DIR = ROOT / "experiments" / "exp134_fab_economics_tco"
RES_DIR = ROOT / "results" / "exp134_fab_economics_tco"
BOM_CANONICAL = ROOT / "research" / "atom_lithography_machine" / "BOM.csv"
EXP_JSON = RES_DIR / "exp134.json"
PRED_JSON = RES_DIR / "predictions_exp134.json"
SUMMARY_MD = RES_DIR / "summary_exp134.md"

if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

import tco_model134 as tm  # noqa: E402

EXPECTED_BOM_SHA256 = "cee02adfd207e37bbbc6b66982226b27fa87c2be528ede2b762f72840759cfc2"


def _load_exp() -> dict:
    assert EXP_JSON.exists(), f"Missing {EXP_JSON}"
    return json.loads(EXP_JSON.read_text(encoding="utf-8"))


def test_live_solver_unit_functions_and_in_memory_mc() -> None:
    """OBS-148: Directly invoke and test live tco_model134 solver functions in memory."""
    tp1 = tm.throughput_model(bayesian_speedup=1.0, shot_cycle_s=0.015)
    tp5 = tm.throughput_model(bayesian_speedup=5.0, shot_cycle_s=0.015)
    tp_stitch = tm.throughput_model(
        bayesian_speedup=1.0 / tm.REAL_SI29_BOED_SPEC_TIME_S,
        shot_cycle_s=0.015,
        stitch_eff=tm.BLANKER_5PCT_DEAD_STITCH_EFF,
    )
    assert tp5["net_reg_day"] == pytest.approx(5.0 * tp1["net_reg_day"], rel=1e-9)
    assert tp_stitch["bottleneck"] == "write"
    assert tp_stitch["net_reg_day"] < tp5["net_reg_day"]

    wb = tm.wafer_batch_throughput(tp5["net_reg_day"], 5.0e7, 1.0)
    assert 0.0 < wb["active_duty_fraction"] < 1.0
    assert wb["wafers_per_yr"] > 0.0

    assert tm.wright_multiplier(1, 0.85) == pytest.approx(1.0)
    assert tm.wright_multiplier(2, 0.85) == pytest.approx(0.85)
    assert tm.wright_multiplier(100, 0.85) < 0.40

    lc17 = tm.logical_qubit_cells(17)
    assert lc17["n_phys_bare"] == 577.0
    assert lc17["n_cells_modb_1over051"] == pytest.approx(577.0 / tm.BATH_YIELD_MODB)

    arr = np.array([10e6, 12e6, 15e6, 18e6, 20e6], dtype=float)
    ue = tm.build_unit_econ_summary(arr, reg_5yr=1e11)
    assert ue["usd_per_register"]["p50"] == pytest.approx(15e6 / 1e11)

    # Execute full Monte Carlo solver live in memory (without mutating disk)
    live = tm.run_tco_model(n_samples=2000, seed=2026134, write_outputs=False)
    assert live["bom_version_synced"] == "v7.0"
    assert live["procurement_status"] == "UNQUOTED_ROM_ESTIMATE"
    assert live["baseline_gate"]["gate_ok"] is True
    assert live["baseline_gate"]["bom_detailed_m3_nom_usd"] == pytest.approx(5_692_800.0, abs=1.0)
    assert live["v7_lifecycle_tco_obs062"]["safety_starter_overlap_reconciled_usd"] == pytest.approx(76_200.0, abs=1.0)
    assert live["v7_lifecycle_tco_obs062"]["unbudgeted_nre_total_nom_usd"] == pytest.approx(890_000.0, abs=1.0)
    assert set(live["wafer_tier_reconciliation_obs060"].keys()) == {"FOAK_50mm", "PILOT_100mm", "FAB_200mm"}
    assert live["wafer_tier_reconciliation_obs060"]["FOAK_50mm"]["fits_current_cad_bore_150mm"] is True
    assert live["wafer_tier_reconciliation_obs060"]["FAB_200mm"]["fits_current_cad_bore_150mm"] is False


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


def test_preregistration_v7_baseline_and_epistemic_flags() -> None:
    assert PRED_JSON.exists()
    pred = json.loads(PRED_JSON.read_text(encoding="utf-8"))
    data = _load_exp()
    assert pred["hypothesis_id"] == "H152"
    assert pred["no_lab_measurement"] is True
    assert pred["no_supplier_quotes"] is True
    assert data["no_lab_measurement"] is True
    assert data["no_supplier_quotes"] is True
    assert data["bom_version_synced"] == "v7.0"
    assert data["procurement_status"] == "UNQUOTED_ROM_ESTIMATE"
    assert data["budget_cap_v3_vs_v4"]["n_samples"] == 50000
    assert data["budget_cap_v3_vs_v4"]["seed"] == 2026134

    # OBS-062: v7.0 BOM + NRE + OPEX lifecycle checks
    bg = data["baseline_gate"]
    assert bg["bom_detailed_m3_nom_usd"] == pytest.approx(5_692_800.0, abs=1.0)
    assert bg["bom_detailed_v7_phase1_nom_usd"] == pytest.approx(5_392_800.0, abs=1.0)
    assert bg["v7_vs_v3_hw_pct_increase"] > 0.35

    v7 = data["v7_lifecycle_tco_obs062"]
    assert v7["safety_starter_overlap_reconciled_usd"] == pytest.approx(76_200.0, abs=1.0)
    assert v7["unbudgeted_nre_total_nom_usd"] == pytest.approx(890_000.0, abs=1.0)
    assert v7["P_v7_phase1_prog_gt_100M"] < 0.05
    assert v7["P_v7_full_prog_gt_100M"] >= 0.05
    assert v7["P_v7_full_lifecycle_foak_5yr_tco_gt_100M"] > 0.05

    opex = data["opex_annual_breakdown_usd"]
    for k in ("power_20_30kw_incl_12p5kw_pt420", "he3_topup_and_ghs_consumables", "scrubber_media_and_radiation_ehs", "pt420_coldhead_rebuild_reserve"):
        assert opex[k]["p50"] > 0.0

    verdicts = data["verdicts"]
    assert verdicts["CX1_baseline_gate"] is True
    assert verdicts["CX2_v4_budget_cap_survival"] is True
    assert verdicts["CX2_v7_phase1_budget_cap_survival"] is True
    assert verdicts["CX2_v7_full_honest_exceeds_5pct_cap"] is True
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
    assert tco["v4_fab_tool_n1_5yr_tco_usd"]["p50"] < tco["v7_phase1_fab_tool_n1_5yr_tco_usd"]["p50"]
    assert tco["v7_phase1_fab_tool_n1_5yr_tco_usd"]["p50"] < tco["v7_full_lifecycle_fab_tool_n1_5yr_tco_usd"]["p50"]
    assert tco["v7_full_lifecycle_fab_tool_n1_5yr_tco_usd"]["p50"] < tco["v7_full_lifecycle_foak_program_5yr_tco_usd"]["p50"]

    bc = data["budget_cap_v3_vs_v4"]
    ep = bc["exceedance_probabilities"]
    for k, prob in ep.items():
        if k.startswith("P_"):
            assert 0.0 <= prob <= 1.0, f"Invalid probability {k}={prob}"
    assert ep["P_v4_BOM_gt_50M"] < 0.001
    assert ep["P_v4_Prog_stoch_gt_100M"] < 0.05
    assert ep["SE_P_v4_Prog_gt_100M"] < 0.002
    assert bc["convergence_25k_vs_50k"]["rel_diff_p50"] <= 0.015


def test_regime1_write_ceiling_real_bath_and_wafer_tiers() -> None:
    data = _load_exp()
    r1 = data["regime1_steady_state_capacity"]
    v3_reg = r1["v3_0_baseline"]["throughput"]["net_reg_day"]
    v4_5x_reg = r1["v4_0_bayes5x_15ms"]["throughput"]["net_reg_day"]
    v4_10x_15ms = r1["v4_0_bayes10x_15ms_write_clamped"]["throughput"]
    v4_10x_10ms = r1["v4_0_bayes10x_10ms"]["throughput"]
    v7_stitch = r1["v7_0_real_si29_boed_5pct_stitch"]["throughput"]

    assert abs(v4_5x_reg / v3_reg - 5.0) < 1e-9
    assert v4_10x_15ms["bottleneck"] == "write"
    assert 7.5 < v4_10x_15ms["net_reg_day"] / v3_reg < 8.0
    assert v4_10x_10ms["bottleneck"] == "spectroscopy"
    assert abs(v4_10x_10ms["net_reg_day"] / v3_reg - 10.0) < 1e-9
    assert v7_stitch["net_reg_day"] < v4_10x_15ms["net_reg_day"]

    # OBS-060: 3-tier wafer reconciliation
    wt = data["wafer_tier_reconciliation_obs060"]
    assert wt["FOAK_50mm"]["diameter_mm"] == 50.0
    assert wt["FOAK_50mm"]["bore_redesign_capex_adder_usd"] == 0.0
    assert wt["FAB_200mm"]["diameter_mm"] == 200.0
    assert wt["FAB_200mm"]["bore_redesign_capex_adder_usd"] >= 1_500_000.0


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
        hws = [wc[bk][n]["hw_v7_full_nom_usd"] for n in ns]
        tcos = [wc[bk][n]["tco5_v7_no_wafer_p50_usd"] for n in ns]
        assert all(hws[i] > hws[i + 1] for i in range(len(hws) - 1))
        assert all(tcos[i] > tcos[i + 1] for i in range(len(tcos) - 1))

    assert wc["b_82"]["100"]["wright_hw_multiplier"] < wc["b_85"]["100"]["wright_hw_multiplier"] < wc["b_88"]["100"]["wright_hw_multiplier"]
    assert wc["b_85"]["100"]["wright_hw_multiplier"] <= 0.40


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
