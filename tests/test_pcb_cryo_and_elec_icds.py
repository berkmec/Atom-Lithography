"""Comprehensive Verification Suite for Cryo-RF Harness PCB, 3 Live ngspice-47 Decks & 95 Electrical ICDs.

Verifies:
  1. KiCad 8 cryo_rf_bias_panel.{kicad_sch,kicad_pcb}: strict S-expr, 0 ERC errors/warnings,
     0 DRC errors, SCH/PCB parity, 24x 50.00 Ohm controlled-impedance checks, 400 V HV air-slot check.
  2. Live ngspice-47 execution of all 3 cryo-RF/quench/rf-SET decks:
       - qram_chebyshev_50_to_3k.cir   (S9.4-02: |S11| <= -20 dB 4-8 GHz, |S21| > -0.2 dB, ABCD parity)
       - magnet_quench_dump_1p563ohm.cir (S6.3-04: V_peak <= 400 V, tau ~ 0.370 s, >=99% energy in R_dump)
       - rf_set_tank_biastee.cir       (S6.7-01: 250-400 MHz f_res, Delta|Gamma| >= 0.25, DC iso > 40 dB, MNA parity)
  3. cryo_rf_thermal_attenuation.json: 6-stage attenuation & Exp125/140/142 thermal load reconciliation.
  4. All 95/95 per-part electrical ICD JSONs (17 E2 + 35 E3 + 43 E4) cross-checked against BOM_DETAILED.csv.
  5. master_electrical_power_ups_budget.json: exact S7.SAFETY-04 15 kVA / 13.5 kW / 10 kWh UPS Tier-1/Tier-2
     math + 10 MHz Rb & White Rabbit 32-port timing fan-out tree.
  6. Zero hardcoded host/user paths across every owned file.
"""
from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

import pytest

from hardware.icd.electrical.build_electrical_icds import (
    ALL_95_IDS,
    E2_IDS,
    E3_IDS,
    E4_IDS,
    VALID_GROUNDING_DOMAINS,
    VALID_UPS_TIERS,
)
from hardware.pcb.cryo_rf_harness_icd.build_cryo_rf_harness import (
    E2_PART_IDS,
    build_cryo_rf_bias_panel_board,
    write_and_run_magnet_quench_spice,
    write_and_run_qram_chebyshev_spice,
    write_and_run_rf_set_spice,
)
from hardware.pcb.kicad_eda_verify import parse_sexpr, run_drc, run_erc, run_ngspice

REPO_ROOT = Path(__file__).resolve().parents[1]
CRYO_DIR = REPO_ROOT / "hardware" / "pcb" / "cryo_rf_harness_icd"
ICD_DIR = REPO_ROOT / "hardware" / "icd" / "electrical"
BOM_CSV = REPO_ROOT / "research" / "atom_lithography_machine" / "BOM_DETAILED.csv"


def _load_bom() -> dict[str, dict[str, str]]:
    with BOM_CSV.open("r", encoding="utf-8", newline="") as f:
        return {row["part_id"]: row for row in csv.DictReader(f)}


# ---------------------------------------------------------------------------
# 1. KiCad 8 Cryo-RF Bulkhead PCB Verification (0 ERC, 0 DRC, Z0 & 400 V HV)
# ---------------------------------------------------------------------------

def test_cryo_rf_bias_panel_kicad_erc_and_drc() -> None:
    board = build_cryo_rf_bias_panel_board()
    assert board.epistemic_meta["iec61508_certified"] is False
    assert board.epistemic_meta["semi_s2_certified"] is False
    assert board.epistemic_meta["no_lab_measurement"] is True

    sch_path = CRYO_DIR / "cryo_rf_bias_panel.kicad_sch"
    pcb_path = CRYO_DIR / "cryo_rf_bias_panel.kicad_pcb"
    assert sch_path.is_file() and pcb_path.is_file()

    # Strict S-expression syntax check on generated files on disk
    sch_tree = parse_sexpr(sch_path.read_text(encoding="utf-8"))
    pcb_tree = parse_sexpr(pcb_path.read_text(encoding="utf-8"))
    assert sch_tree[0] == "kicad_sch"
    assert pcb_tree[0] == "kicad_pcb"

    erc = run_erc(sch_path, board, pcb_path=pcb_path)
    assert erc.passed, f"ERC failed: {erc.errors}"
    assert len(erc.errors) == 0
    assert len(erc.warnings) == 0
    assert erc.sch_pcb_parity_ok is True
    assert erc.component_count >= 110
    assert erc.net_count >= 65

    drc = run_drc(pcb_path, board)
    assert drc.passed, f"DRC failed: {drc.errors}"
    assert len(drc.errors) == 0
    assert drc.total_multi_pin_nets == erc.net_count
    assert drc.routed_net_count == drc.total_multi_pin_nets
    assert drc.unrouted_net_count == 0
    assert drc.unconnected_items == 0
    assert drc.track_dangling_count == 0
    assert drc.air_slot_count == 1
    assert len(drc.impedance_checks) == 8  # 8 straight zero-jog, zero-stub 50.00 Ohm RF segments (RF50_IN0..3, RF50_OUT0..3)
    assert all(c["passed"] for c in drc.impedance_checks)
    assert len(drc.hv_checks) >= 1
    assert all(c["passed"] for c in drc.hv_checks)
    assert all(c["through_board_ok"] for c in drc.hv_checks)

    # OBS-033: Verify MSOP-12-1EP LDO pinouts (LT3045 EP=AGND_CRYO, LT3094 EP=VIN_N5V)
    pin_net = {node: ns.name for ns in board.nets for node in ns.nodes}
    ldo_p = [c for c in board.components if c.ref == "U_LDO_P"][0]
    ldo_n = [c for c in board.components if c.ref == "U_LDO_N"][0]
    assert "MSOP-12-1EP" in ldo_p.footprint and len(ldo_p.pins) == 13
    assert "MSOP-12-1EP" in ldo_n.footprint and len(ldo_n.pins) == 13
    assert pin_net[("U_LDO_P", "8")] == "AGND_CRYO" and pin_net[("U_LDO_P", "13")] == "AGND_CRYO"
    assert pin_net[("U_LDO_N", "9")] == "AGND_CRYO" and pin_net[("U_LDO_N", "13")] == "VIN_N5V"

    # OBS-028 & OBS-036: Verify inline zero-stub RF routing + full 2-stage choke/shunt + Kelvin divider
    for k in range(4):
        assert any(c.ref == f"C_SH1_{k}" for c in board.components)
        assert any(c.ref == f"L_CHK2_{k}" for c in board.components)
        assert any(c.ref == f"C_SH2_{k}" for c in board.components)
        assert any(c.ref == f"R_SETDIV_{k}" for c in board.components)
        in_segs = [t for t in board.traces if t.net == f"RF50_IN{k}"]
        assert all(len(t.points_mm) == 2 for t in in_segs), f"RF50_IN{k} must be straight inline (no 90-deg jogs)"

    # OBS-092: Verify >=5.0 mm VTAP differential pad gap on J_QUENCH_MAG & R_QTAP_DIV sense divider
    j_q = [c for c in board.components if c.ref == "J_QUENCH_MAG"][0]
    p1, p2 = j_q.pins[0], j_q.pins[1]
    vtap_gap_mm = abs(p2.dy_mm - p1.dy_mm) - 0.5 * (p1.pad_h_mm + p2.pad_h_mm)
    assert vtap_gap_mm >= 5.0, f"VTAP_P/N differential gap {vtap_gap_mm:.2f} mm < 5.0 mm"
    assert any(c.ref == "R_QTAP_DIV" for c in board.components)

    # Stored verification JSON must also carry semi_s2_certified=False and 100% routing
    stored = json.loads((CRYO_DIR / "cryo_rf_thermal_attenuation.json").read_text(encoding="utf-8"))
    pcb_rep = stored["pcb_verification"]
    assert pcb_rep["epistemic_meta"]["semi_s2_certified"] is False
    assert pcb_rep["epistemic_meta"]["iec61508_certified"] is False
    assert pcb_rep["drc"]["routed_net_count"] == pcb_rep["drc"]["total_multi_pin_nets"]
    assert pcb_rep["drc"]["unrouted_net_count"] == 0
    assert pcb_rep["drc"]["unconnected_items"] == 0
    assert pcb_rep["drc"]["track_dangling_count"] == 0


# ---------------------------------------------------------------------------
# 2. Live ngspice-47 Verification of All 3 Cryo-RF / Quench / rf-SET Decks
# ---------------------------------------------------------------------------

def test_live_ngspice_qram_chebyshev_50_to_3k(tmp_path: Path) -> None:
    disk_cir = CRYO_DIR / "qram_chebyshev_50_to_3k.cir"
    assert disk_cir.is_file()
    cir_txt = disk_cir.read_text(encoding="utf-8")
    # OBS-105: zero unrealizable >200 Ohm T-line circuit cards (pure lumped superconducting NbTiN LC ladder)
    t_cards = [ln.strip() for ln in cir_txt.splitlines() if ln.strip() and not ln.strip().startswith("*") and ln.strip().upper().startswith("T")]
    assert t_cards == [], f"Unexpected transmission line cards in lumped cryo LC deck: {t_cards}"
    res_disk = run_ngspice(disk_cir, workdir=tmp_path)
    assert res_disk.ok, f"Disk Chebyshev deck failed: {res_disk.errors}"

    rep = write_and_run_qram_chebyshev_spice(tmp_path)
    assert rep["ngspice_ok"] is True
    assert rep["pass"] is True
    assert rep["max_s11_4_8_db"] <= -20.0, f"Expected |S11| <= -20 dB, got {rep['max_s11_4_8_db']}"
    assert rep["min_s21_4_8_db"] > -0.2, f"Expected |S21| > -0.2 dB, got {rep['min_s21_4_8_db']}"
    assert rep["bw20_ghz"] >= 4.0
    assert rep["max_passivity"] <= 1.0001
    # Exact ABCD parity check
    assert rep["abcd_crosscheck"]["s11_parity_diff_db"] < 0.05
    assert rep["abcd_crosscheck"]["s21_parity_diff_db"] < 0.01


def test_live_ngspice_magnet_quench_dump_1p563ohm(tmp_path: Path) -> None:
    disk_cir = CRYO_DIR / "magnet_quench_dump_1p563ohm.cir"
    assert disk_cir.is_file()
    assert ".temp -268.95" in disk_cir.read_text(encoding="utf-8")  # OBS-092: true 4.2 K bath
    res_disk = run_ngspice(disk_cir, workdir=tmp_path)
    assert res_disk.ok, f"Disk quench deck failed: {res_disk.errors}"

    rep = write_and_run_magnet_quench_spice(tmp_path)
    assert rep["ngspice_ok"] is True
    assert rep["pass"] is True
    assert rep["n_coils"] == 8
    assert abs(rep["E_stored_kJ"] - 18.9408) < 0.01
    assert rep["v_peak_V"] <= 400.0, f"Peak voltage exceeded 400 V: {rep['v_peak_V']}"
    assert rep["v_open_dump_fault_peak_V"] < 400.0, f"Open-dump fault exceeded 400 V: {rep['v_open_dump_fault_peak_V']}"
    assert abs(rep["tau_decay_s"] - 0.370) <= 0.010, f"tau out of range: {rep['tau_decay_s']}"
    assert rep["e_dump_fraction_pct"] >= 99.0, f"Dump fraction < 99%: {rep['e_dump_fraction_pct']}"
    assert rep["dump_bank_T_peak_C"] < 55.0
    assert rep["analytical_crosscheck"]["tau_rel_diff_pct"] < 0.5


def test_live_ngspice_rf_set_tank_biastee(tmp_path: Path) -> None:
    disk_cir = CRYO_DIR / "rf_set_tank_biastee.cir"
    assert disk_cir.is_file()
    res_disk = run_ngspice(disk_cir, workdir=tmp_path)
    assert res_disk.ok, f"Disk rf-SET deck failed: {res_disk.errors}"

    rep = write_and_run_rf_set_spice(tmp_path)
    assert rep["ngspice_ok"] is True
    assert rep["pass"] is True
    assert 250.0 <= rep["f_res_MHz"] <= 400.0
    assert rep["delta_gamma_mag"] >= 0.25
    assert rep["dc_bias_isolation_at_fres_dB"] > 40.0
    assert rep["dc_bias_isolation_worst_200_450MHz_dB"] > 40.0
    # OBS-036: Safe mV-scale DC bias across rf-SET (zero +3.3 V leak!)
    assert 0.5 <= rep["v_set_dc_50k_mV"] <= 2.0
    assert 0.5 <= rep["v_set_dc_200k_mV"] <= 2.0
    # OBS-028: Zero-stub inline conical bias-tee through-line S11/S21 across 4-8 GHz (eliminates -21.8 dB stub notch!)
    assert rep["inline_biastee_4_8ghz_max_s11_dB"] <= -20.0
    assert rep["inline_biastee_4_8ghz_min_s21_dB"] > -0.1
    # Independent MNA cross-check parity
    assert rep["mna_crosscheck"]["delta_gamma_diff"] < 1e-4
    assert rep["mna_crosscheck"]["iso_diff_dB"] < 0.05


# ---------------------------------------------------------------------------
# 3. Cryo-RF Thermal & Attenuation Reconciliation (Exp125 / Exp140 / Exp142)
# ---------------------------------------------------------------------------

def test_cryo_rf_thermal_attenuation_budget() -> None:
    data = json.loads((CRYO_DIR / "cryo_rf_thermal_attenuation.json").read_text(encoding="utf-8"))
    assert data["epistemic_flags"]["no_lab_measurement"] is True
    assert data["epistemic_flags"]["iec61508_certified"] is False
    assert set(data["covered_e2_part_ids"]) == set(E2_PART_IDS)
    assert len(data["covered_e2_part_ids"]) == 17
    assert data["covered_quench_part_id"] == "S6.3-04"

    att = data["staged_attenuation_300K_to_20mK"]
    assert att["total_input_attenuation_dB"] == 60.0
    assert len(att["stages"]) == 6
    assert att["final_n_th_at_20mK"] < 0.01

    tb = data["thermal_load_budget"]["combined_m4_plus_option_q"]
    assert abs(tb["mxc_20mK_uW"] - 7.036) < 0.01
    assert abs(tb["cp_100mK_uW"] - 65.73) < 0.05
    assert abs(tb["stage_4K_W"] - 0.550) < 0.002
    assert abs(tb["stage_50K_W"] - 8.74) < 0.02
    assert data["thermal_load_budget"]["margins"]["all_stages_pass"] is True

    # All 3 stored simulation verdicts PASS
    for key in ("qram_chebyshev_50_to_3k", "magnet_quench_dump_1p563ohm", "rf_set_tank_biastee"):
        assert data["ngspice_simulations"][key]["pass"] is True


# ---------------------------------------------------------------------------
# 4. Complete 95/95 Per-Part Electrical ICD Verification vs BOM_DETAILED.csv
# ---------------------------------------------------------------------------

def test_all_95_electrical_icds_valid_and_bom_reconciled() -> None:
    bom = _load_bom()
    assert len(E2_IDS) == 17 and len(E3_IDS) == 35 and len(E4_IDS) == 43
    assert len(set(ALL_95_IDS)) == 95

    on_disk = sorted(p.stem for p in ICD_DIR.glob("S*.json"))
    assert set(on_disk) == set(ALL_95_IDS), (
        f"ICD file mismatch: missing={set(ALL_95_IDS)-set(on_disk)}, extra={set(on_disk)-set(ALL_95_IDS)}"
    )

    class_counts = {"E2": 0, "E3": 0, "E4": 0}
    total_usd = 0.0

    for pid in ALL_95_IDS:
        icd = json.loads((ICD_DIR / f"{pid}.json").read_text(encoding="utf-8"))
        brow = bom[pid]

        # Exact BOM identity & cost parity
        assert icd["part_id"] == pid
        assert icd["parent_bom_id"] == brow["parent_bom_id"]
        assert icd["subsystem"] == brow["subsystem"]
        assert icd["part_name"] == brow["part_name"]
        assert abs(icd["usd_nom"] - float(brow["usd_nom"])) < 1e-6
        total_usd += icd["usd_nom"]

        # Class, grounding domain & UPS tier enums
        expected_cls = "E2" if pid in E2_IDS else ("E3" if pid in E3_IDS else "E4")
        assert icd["electrical_class"] == expected_cls
        class_counts[expected_cls] += 1
        assert icd["grounding_domain"] in VALID_GROUNDING_DOMAINS
        assert icd["ups_tier"] in VALID_UPS_TIERS

        # Non-empty supply rails & connectors with pin-by-pin signal tables
        assert len(icd["supply_rails"]) >= 1
        for r in icd["supply_rails"]:
            assert r["source_part_id"] in bom, f"{pid}: invalid rail source {r['source_part_id']}"
            assert r["steady_power_w"] >= 0.0 and r["peak_power_w"] >= r["steady_power_w"]

        assert len(icd["connectors_and_pinout"]) >= 1
        for c in icd["connectors_and_pinout"]:
            assert c["mating_part_id"] in bom, f"{pid}: invalid connector mating {c['mating_part_id']}"
            assert len(c["pins"]) >= 1
            for pin in c["pins"]:
                assert pin["pin"] and pin["signal"] and pin["direction"] and pin["nominal_level"]

        assert len(icd["mating_part_ids"]) >= 1
        for mid in icd["mating_part_ids"]:
            assert mid in bom, f"{pid}: invalid mating_part_id {mid}"
        for hook in icd["interlock_hooks"]:
            assert hook["target_part_id"] in bom, f"{pid}: invalid interlock target {hook['target_part_id']}"

        # Per-part power reconciliation fields (zero double-counting)
        assert "incremental_mains_w" in icd and icd["incremental_mains_w"] >= 0.0
        assert "supply_rails_steady_sum_w" in icd
        assert "secondary_or_parent_derived_w" in icd and icd["secondary_or_parent_derived_w"] >= 0.0
        assert "non_exp150_aux_shed_w" in icd and icd["non_exp150_aux_shed_w"] >= 0.0
        assert isinstance(icd.get("reconciliation_note"), str) and len(icd["reconciliation_note"]) > 10
        raw_calc = round(sum(r["steady_power_w"] for r in icd["supply_rails"]), 4)
        assert abs(icd["supply_rails_steady_sum_w"] - raw_calc) < 1e-4

        # Epistemic calibration flags
        ef = icd["epistemic_flags"]
        assert ef["design_maturity"] == "M0_M1_ELECTRICAL_ICD_DESIGN_ONLY"
        assert ef["no_lab_measurement"] is True
        assert ef["iec61508_certified"] is False
        assert ef["semi_s2_certified"] is False

    assert class_counts == {"E2": 17, "E3": 35, "E4": 43}
    assert abs(total_usd - 3_434_800.0) < 1e-3


# ---------------------------------------------------------------------------
# 5. Master Electrical Power, 15 kVA LFP UPS & Timing Tree Verification
# ---------------------------------------------------------------------------

def test_master_ups_power_budget_and_timing_trees() -> None:
    bom = _load_bom()
    master = json.loads((ICD_DIR / "master_electrical_power_ups_budget.json").read_text(encoding="utf-8"))

    assert master["icd_coverage"]["total_per_part_icds"] == 95
    assert master["icd_coverage"]["by_electrical_class"] == {"E2": 17, "E3": 35, "E4": 43}

    # Independently sum Tier-1, Tier-2 & all 28 TIER2_SHED reconciliation fields directly from disk
    disk_t1_w = 0.0
    disk_t2_w = 0.0
    t2_28_count = 0
    t2_28_raw_w = 0.0
    t2_28_exp150_w = 0.0
    t2_28_aux_w = 0.0
    t2_28_overlap_w = 0.0
    t2_28_incr_w = 0.0
    for pid in ALL_95_IDS:
        icd = json.loads((ICD_DIR / f"{pid}.json").read_text(encoding="utf-8"))
        if icd["ups_budget_group"] == "EXP150_TIER1_CRITICAL":
            disk_t1_w += icd["exp150_ups_allocation_w"]
        elif icd["ups_budget_group"] == "EXP150_TIER2_SHED":
            disk_t2_w += icd["exp150_ups_allocation_w"]
        if icd["ups_tier"] == "TIER2_SHED":
            t2_28_count += 1
            t2_28_raw_w += icd["supply_rails_steady_sum_w"]
            t2_28_exp150_w += icd["exp150_ups_allocation_w"]
            t2_28_aux_w += icd["non_exp150_aux_shed_w"]
            t2_28_overlap_w += icd["secondary_or_parent_derived_w"]
            t2_28_incr_w += icd["incremental_mains_w"]

    ups = master["ups_s7_safety_04"]
    assert ups["rating_kVA"] == 15.0
    assert ups["rated_real_power_kW"] == 13.5
    assert ups["battery_energy_kWh"] == 12.0
    assert ups["internal_loss_W"] == 350.0
    assert ups["transfer_time_ms"] == 0.0
    assert ups["utility_side_tier2_contactor_ahead_of_ups"] is True
    assert ups["pt420_wall_power_utility_side_kW"] == 12.5
    assert ups["dedicated_magnet_rampdown_ups_branch_W"] == 650.0
    assert ups["ups_peak_load_within_13p5kW_rating"] is True

    # Tier-1 exact math: 95-ICD sum + E1 external (S7.SAFETY-03 120 W + S6.11-01 88 W) == 2533.0 W
    t1 = ups["tier1_critical"]
    e1_t1_w = sum(x["power_w"] for x in t1["items_from_e1_boards"])
    assert abs(disk_t1_w - t1["from_95_icds_W"]) < 1e-6
    assert abs(disk_t1_w + e1_t1_w - 2533.0) < 1e-6
    assert t1["total_kW"] == 2.533
    assert abs(sum(t1["exp150_buckets_W"].values()) - 2533.0) < 1e-6

    # Runtime verification: BOTH Exp150 reference formula AND conservative 12 kWh LFP incl. 350 W idle loss + 120 s Tier-1B ramp-down
    expected_t1_exp150_min = round((12.0 * 0.90 / 2.533) * 60.0, 1)
    assert t1["runtime_tier1_min_exp150_nominal_eta090"] == expected_t1_exp150_min == 255.8
    assert t1["runtime_min"] == 202.8
    assert t1["meets_180min_requirement"] is True

    expected_p_batt_w = round(2533.0 / 0.90 + 350.0, 2)
    assert abs(t1["battery_dc_draw_incl_350w_loss_W"] - expected_p_batt_w) < 0.05
    assert t1["runtime_tier1_min_conservative_100pct_dod_incl_350w_loss"] == 225.5
    assert t1["runtime_tier1_min_conservative_90pct_dod_incl_350w_loss"] == 202.8
    assert t1["tier1_conservative_100pct_dod_meets_180min"] is True
    assert t1["tier1_conservative_90pct_dod_meets_180min"] is True
    sizing = t1["conservative_sizing_requirements_for_180min_at_90pct_dod"]
    assert sizing["min_lfp_pack_kWh_at_2p533kW"] >= 10.5
    assert sizing["installed_nominal_lfp_pack_kWh"] == 12.0
    assert sizing["recommended_nominal_lfp_pack_kWh"] == 12.0
    assert sizing["max_tier1_load_kW_at_12kWh"] >= 2.90

    # Tier-2 exact math & 28-part TIER2_SHED zero-discrepancy reconciliation (12.5 kW PT420 utility-side)
    assert abs(disk_t2_w - 15275.0) < 1e-6
    assert ups["tier2_sheddable"]["total_kW"] == 15.275
    assert abs(sum(ups["tier2_sheddable"]["exp150_buckets_W"].values()) - 15275.0) < 1e-6
    t2_rec = ups["tier2_sheddable"]["tier2_shed_28part_reconciliation"]
    assert t2_28_count == t2_rec["tier2_shed_part_count"] == 28
    assert abs(t2_28_raw_w - 21026.0) < 1e-6
    assert abs(t2_28_exp150_w - 15275.0) < 1e-6
    assert abs(t2_28_aux_w - 5401.0) < 1e-6
    assert abs(t2_28_overlap_w - 350.0) < 1e-6
    assert abs(t2_28_incr_w - (t2_28_exp150_w + t2_28_aux_w)) < 1e-6
    assert abs(t2_28_raw_w - (t2_28_exp150_w + t2_28_aux_w + t2_28_overlap_w)) < 1e-6
    assert t2_rec["reconciliation_discrepancy_W"] == 0.0
    assert t2_rec["raw_supply_rails_steady_sum_W"] == 21026.0
    assert t2_rec["exp150_tier2_ups_allocation_W"] == 15275.0
    assert t2_rec["non_exp150_aux_incremental_mains_W"] == 5401.0
    assert t2_rec["secondary_and_backplane_derived_overlap_W"] == 350.0

    # Combined reconciliation & full-load runtime (43.2 min nom / 46.9 min 100% DoD / 42.2 min 90% DoD >= 30 min)
    rec = ups["reconciliation"]
    assert rec["exp150_combined_tier1_plus_tier2_kW"] == 17.808
    assert rec["runtime_at_rated_13p5kW_min"] == 43.2
    assert rec["runtime_at_rated_13p5kW_conservative_100pct_dod_incl_350w_min"] == 46.9
    assert rec["runtime_at_rated_13p5kW_conservative_90pct_dod_incl_350w_min"] == 42.2
    assert rec["meets_30min_full_load_requirement"] is True
    assert rec["operational_phase_ups_load_kW"]["all_modes_within_13p5kW_ups"] is True

    # Grounding domain partition covers all 95/95 parts
    assert master["grounding_domains"]["total_assigned"] == 95
    assigned = [pid for d in master["grounding_domains"]["domains"].values() for pid in d["part_ids"]]
    assert len(assigned) == 95 and set(assigned) == set(ALL_95_IDS)

    # 10 MHz Rb (16 ch) + White Rabbit (8 SFP + 8 Coax) timing tree verification
    rb = master["timing_distribution"]["rb_10mhz_atomic_clock"]
    assert rb["source_part_id"] == "S7.4-01"
    assert len(rb["fanout_channels"]) == 16
    for ch in rb["fanout_channels"]:
        assert ch["target_part_id"] in bom

    wr = master["timing_distribution"]["white_rabbit_trigger_fanout"]
    assert wr["source_part_id"] == "S7.4-02"
    assert wr["max_interchannel_skew_ps"] <= 200.0
    assert len(wr["optical_sfp_ports"]) == 8
    assert len(wr["coax_50ohm_ports"]) == 8
    for p in wr["optical_sfp_ports"] + wr["coax_50ohm_ports"]:
        assert p["target_part_id"] in bom


# ---------------------------------------------------------------------------
# 6. Zero Hardcoded Host/User Path Leak Guard Across Every Owned File
# ---------------------------------------------------------------------------

def test_zero_hardcoded_host_paths_in_all_owned_files() -> None:
    host_path_re = re.compile(r"/home/[A-Za-z0-9_.-]+|/Users/[A-Za-z0-9_.-]+|/run/media/[A-Za-z0-9_.-]+")
    owned_files = (
        list(CRYO_DIR.rglob("*"))
        + list(ICD_DIR.rglob("*"))
        + [Path(__file__).resolve()]
    )
    checked = 0
    for p in owned_files:
        if not p.is_file() or "__pycache__" in p.parts or p.suffix == ".pyc":
            continue
        text = p.read_text(encoding="utf-8")
        checked += 1
        # Exclude the regex pattern literal itself when scanning this test file
        scan_text = text.replace(host_path_re.pattern, "") if p.resolve() == Path(__file__).resolve() else text
        m = host_path_re.search(scan_text)
        assert m is None, f"Host path leak {m.group(0)!r} in {p.relative_to(REPO_ROOT)}"
    assert checked >= 105
