"""Verification Test Suite for Wave 2B HV, Laser/Pyrometer & 1oo2D Safety PCBs + Live ngspice-47.

Covers all 3 custom KiCad 8 + live ngspice-47 board suites (with 100% physical routing DRC):
  1. hardware/pcb/ion_column_hv_dac/       (S1.3-03, S2.3-04, S6.10-04; S1.1-05, S1.2-03, S1.5-03, S4.5-03)
  2. hardware/pcb/laser_aom_pyrometer_afe/ (S5.5-03, S5.5-01, S5.5-04, S5.3-03)
  3. hardware/pcb/safety_interlock_1oo2d/  (S7.SAFETY-03/02/05/06/01, S7.4-04, S5.5-04; DESIGN_ONLY_NOT_CERTIFIED)
"""
from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from hardware.pcb.ion_column_hv_dac.build_ion_column_hv_dac import (
    build_ion_column_hv_dac_board,
    run_mna_crosscheck as run_ion_mna,
)
from hardware.pcb.kicad_eda_verify import (
    BoardSpec,
    parse_sexpr,
    run_drc,
    run_erc,
    run_ngspice,
    write_kicad_pcb,
)
from hardware.pcb.laser_aom_pyrometer_afe.build_laser_aom_pyrometer_afe import (
    build_laser_aom_pyrometer_board,
    run_mna_crosscheck as run_laser_mna,
)
from hardware.pcb.safety_interlock_1oo2d.build_safety_interlock_1oo2d import (
    build_safety_interlock_1oo2d_board,
    run_analytical_crosscheck as run_safety_ana,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PCB_ROOT = REPO_ROOT / "hardware" / "pcb"
ION_DIR = PCB_ROOT / "ion_column_hv_dac"
LASER_DIR = PCB_ROOT / "laser_aom_pyrometer_afe"
SAFETY_DIR = PCB_ROOT / "safety_interlock_1oo2d"

HOST_PATH_RE = re.compile(r"/home/[A-Za-z0-9_.-]+|/Users/[A-Za-z0-9_.-]+|/run/media/[A-Za-z0-9_.-]+")


@pytest.fixture(scope="module")
def ion_spec() -> BoardSpec:
    return build_ion_column_hv_dac_board()


@pytest.fixture(scope="module")
def laser_spec() -> BoardSpec:
    return build_laser_aom_pyrometer_board()


@pytest.fixture(scope="module")
def safety_spec() -> BoardSpec:
    return build_safety_interlock_1oo2d_board()


# ---------------------------------------------------------------------------
# 1. Hygiene & Epistemic Calibration Tests
# ---------------------------------------------------------------------------

def test_zero_hardcoded_host_paths_in_wave2b_artifacts() -> None:
    owned_files = [
        ION_DIR / "build_ion_column_hv_dac.py",
        ION_DIR / "ion_column_hv_dac.kicad_sch",
        ION_DIR / "ion_column_hv_dac.kicad_pcb",
        ION_DIR / "ion_hv_filter_trim.cir",
        ION_DIR / "ion_column_hv_dac_verification.json",
        ION_DIR / "README.md",
        LASER_DIR / "build_laser_aom_pyrometer_afe.py",
        LASER_DIR / "laser_aom_pyrometer_afe.kicad_sch",
        LASER_DIR / "laser_aom_pyrometer_afe.kicad_pcb",
        LASER_DIR / "laser_pyro_tia_aom.cir",
        LASER_DIR / "laser_aom_pyrometer_afe_verification.json",
        LASER_DIR / "README.md",
        SAFETY_DIR / "build_safety_interlock_1oo2d.py",
        SAFETY_DIR / "safety_interlock_1oo2d.kicad_sch",
        SAFETY_DIR / "safety_interlock_1oo2d.kicad_pcb",
        SAFETY_DIR / "safety_1oo2d_crowbar.cir",
        SAFETY_DIR / "safety_interlock_1oo2d_verification.json",
        SAFETY_DIR / "README.md",
        Path(__file__).resolve(),
    ]
    for p in owned_files:
        assert p.is_file(), f"Expected deliverable missing: {p}"
        text = p.read_text(encoding="utf-8")
        hit = HOST_PATH_RE.search(text)
        assert hit is None, f"Hardcoded host path {hit.group(0)!r} found in {p.relative_to(REPO_ROOT)}"


def test_safety_interlock_strictly_labeled_design_only_not_certified(safety_spec: BoardSpec) -> None:
    assert safety_spec.epistemic_meta["iec61508_certified"] is False
    assert safety_spec.epistemic_meta["semi_s2_certified"] is False
    assert safety_spec.epistemic_meta["requires_third_party_assessment"] is True
    assert safety_spec.epistemic_meta["certification_status"] == "DESIGN_ONLY_NOT_CERTIFIED"
    assert safety_spec.epistemic_meta["no_lab_measurement"] is True
    assert safety_spec.epistemic_meta["no_physical_fab"] is True

    ver_json = json.loads((SAFETY_DIR / "safety_interlock_1oo2d_verification.json").read_text(encoding="utf-8"))
    assert ver_json["iec61508_certified"] is False
    assert ver_json["semi_s2_certified"] is False
    assert ver_json["requires_third_party_assessment"] is True
    assert ver_json["certification_status"] == "DESIGN_ONLY_NOT_CERTIFIED"
    assert ver_json["all_passed"] is True

    for fname in ("safety_interlock_1oo2d.kicad_sch", "safety_interlock_1oo2d.kicad_pcb", "safety_1oo2d_crowbar.cir", "README.md"):
        txt = (SAFETY_DIR / fname).read_text(encoding="utf-8")
        assert "DESIGN_ONLY_NOT_CERTIFIED" in txt, f"Missing DESIGN_ONLY_NOT_CERTIFIED label in {fname}"


# ---------------------------------------------------------------------------
# 2. Board 1: ion_column_hv_dac — KiCad 8 ERC/DRC/Routing/HV + Live ngspice-47
# ---------------------------------------------------------------------------

def test_ion_column_hv_dac_kicad_erc_drc_and_5kv_hv_rules(ion_spec: BoardSpec) -> None:
    expected_boms = {"S1.3-03", "S2.3-04", "S6.10-04", "S1.1-05", "S1.2-03", "S1.5-03", "S4.5-03"}
    assert expected_boms.issubset(set(ion_spec.bom_ids))

    sch = ION_DIR / "ion_column_hv_dac.kicad_sch"
    pcb = ION_DIR / "ion_column_hv_dac.kicad_pcb"
    assert parse_sexpr(sch.read_text(encoding="utf-8"))[0] == "kicad_sch"
    assert parse_sexpr(pcb.read_text(encoding="utf-8"))[0] == "kicad_pcb"

    erc = run_erc(sch, ion_spec, pcb_path=pcb)
    assert erc.passed, f"ERC failed: {erc.errors}"
    assert erc.sch_pcb_parity_ok
    assert erc.component_count >= 90

    drc = run_drc(pcb, ion_spec)
    assert drc.passed, f"DRC failed: {drc.errors}"
    assert drc.unrouted_net_count == 0
    assert drc.unconnected_items == 0
    assert drc.track_dangling_count == 0
    assert drc.routed_net_count == drc.total_multi_pin_nets and drc.total_multi_pin_nets >= 72
    assert drc.stackup_summary["copper_layers"] == 4
    assert drc.air_slot_count >= 2
    assert len(drc.impedance_checks) >= 5
    assert all(ic["passed"] and ic["error_pct"] < 1.0 for ic in drc.impedance_checks)
    assert len(drc.hv_checks) == 1
    hv = drc.hv_checks[0]
    assert hv["passed"] is True
    assert hv["through_board_ok"] is True
    assert hv["measured_clearance_mm"] >= 12.0
    assert hv["measured_creepage_mm"] >= 16.0

    # OBS-020 / OBS-078 / OBS-087 regressions:
    comp_map = {c.ref: c for c in ion_spec.components}
    # ALL resistors touching HV_5KV_* nets must be HV thru-hole (never 2512 SMD!)
    hv_refs = {ref for n in ion_spec.nets if n.name.startswith("HV_5KV_") for ref, _ in n.nodes}
    for ref in hv_refs:
        if ref.startswith("R"):
            assert "2512" not in comp_map[ref].footprint, f"{ref} must not use 2512 SMD on 5 kV"
    # Parallel fail-safe crowbar + isolated coil driver + isolated DAC_RST_N (no ADuM1401 bypass!)
    for req in ("K_HV_CLAMP", "Q_HV_CLAMP_TOP", "Q_HV_CLAMP", "Q_KCLAMP_DRV", "U_ISO_SPI1", "U_ISO_RST", "R_RST_PU"):
        assert req in comp_map, f"Missing OBS-020/078 component {req}"
    assert "RSET_LDO_3V3" not in comp_map and "R_SET_P5A" not in comp_map, "Fixed-output ADP7142AUJZ-3.3 must not have fake RSET"
    # Exact IC package pin counts (OBS-087)
    assert len(comp_map["U_LDO_P5"].pins) == 11    # DFN-10+EP11 LT3045EDD (ultra-low-noise 5V DAC rail)
    assert len(comp_map["U_LDO_3V3"].pins) == 5    # TSOT-23-5 ADP7142AUJZ-3.3 (fixed output)
    assert len(comp_map["U_LDO_P15"].pins) == 11   # DFN-10+EP11 LT3045EDD
    assert len(comp_map["U_LDO_N15"].pins) == 13   # DFN-12+EP13 LT3094EDD


def test_ion_column_hv_dac_live_ngspice_and_mna_parity() -> None:
    cir = ION_DIR / "ion_hv_filter_trim.cir"
    res = run_ngspice(cir, workdir=ION_DIR)
    assert res.ok, f"ngspice failed: {res.errors}"
    assert res.returncode == 0
    assert len(res.errors) == 0

    m = res.metrics
    # OBS-078: Real 100/120 Hz mains ripple rejection (> 25 dB) + 100 kHz (> 80 dB) + passive MNA parity < 0.05 dB
    assert m["hv_atten_100hz_db"] < -25.0
    assert m["hv_atten_120hz_db"] < -25.0
    assert m["hv_atten_100k_db"] < -80.0
    assert m["hv_atten_100k_db"] < m["hv_passive_100k_db"] - 10.0  # active stage adds >10 dB boost
    mna = run_ion_mna()
    assert abs(m["hv_passive_100k_db"] - mna["mna_passive_hv_atten_100k_db"]) < 0.05

    # 10 Vpp 100 kHz ripple held to < 1 mVpp (< 2 mVpp mini-lens spec)
    ripple_mvpp = m["hv_ripple_vpp"] * 1e3
    assert 0.0 < ripple_mvpp < 1.0

    # OBS-078: Divider & loop accuracy <= 46.8 ppm
    assert abs(m["hv_dc_v"] - 5000.0) < 0.5
    assert m["hv_div_err_ppm"] <= 46.8
    assert m["hv_reg_err_ppm"] <= 46.8

    # OBS-020: Parallel fail-safe NC relay + 9 kV cascode NMOS discharges 5 kV -> < 50 V on power loss!
    assert 0.0 <= m["cb_pwrloss_v"] < 50.0
    assert m["cb_mos_vds_max"] < 4500.0

    # Fast < 5 us on-the-fly interferometer deflector trim step (10-90% & 1% settling)
    assert 0.0 < m["trim_rise_10_90_s"] < 5.0e-6
    assert 0.0 < m["trim_settle_1pct_s"] < 5.0e-6

    # M4 20-bit DC dipole gate DAC noise < 0.5 uV/rtHz @ 1 kHz
    assert abs(m["m4_noise_freq_chk"] - 1000.0) < 1.0
    assert 0.0 < m["m4_noise_1khz_v_rthz"] < 0.5e-6


# ---------------------------------------------------------------------------
# 3. Board 2: laser_aom_pyrometer_afe — KiCad 8 ERC/DRC/Routing + Live ngspice-47
# ---------------------------------------------------------------------------

def test_laser_aom_pyrometer_afe_kicad_erc_drc_and_50ohm_rf(laser_spec: BoardSpec) -> None:
    expected_boms = {"S5.5-03", "S5.5-01", "S5.5-04", "S5.3-03"}
    assert expected_boms.issubset(set(laser_spec.bom_ids))

    sch = LASER_DIR / "laser_aom_pyrometer_afe.kicad_sch"
    pcb = LASER_DIR / "laser_aom_pyrometer_afe.kicad_pcb"
    assert parse_sexpr(sch.read_text(encoding="utf-8"))[0] == "kicad_sch"
    assert parse_sexpr(pcb.read_text(encoding="utf-8"))[0] == "kicad_pcb"

    erc = run_erc(sch, laser_spec, pcb_path=pcb)
    assert erc.passed, f"ERC failed: {erc.errors}"
    assert erc.sch_pcb_parity_ok
    assert erc.component_count >= 70

    drc = run_drc(pcb, laser_spec)
    assert drc.passed, f"DRC failed: {drc.errors}"
    assert drc.unrouted_net_count == 0
    assert drc.unconnected_items == 0
    assert drc.track_dangling_count == 0
    assert drc.routed_net_count == drc.total_multi_pin_nets and drc.total_multi_pin_nets >= 63
    assert drc.stackup_summary["copper_layers"] == 4
    assert len(drc.impedance_checks) >= 10
    assert all(ic["passed"] and ic["error_pct"] < 1.0 for ic in drc.impedance_checks)

    # OBS-037 / OBS-093 / OBS-087 regressions:
    comp_map = {c.ref: c for c in laser_spec.components}
    for req in ("C_RF_DCBLK", "U_LDO_2V5RF", "U_RF_KILL_SW", "U_INT_RST_SW", "Q_DIODE_EN_A", "Q_DIODE_EN_B", "Q_GDRV_DIODE_A", "U_AOM_VCA", "U_CMP_OTEMP"):
        assert req in comp_map, f"Missing OBS-037/093/087 component {req}"
    assert len(comp_map["U_RF_KILL_SW"].pins) == 8  # 8-MSOP ADG901BRMZ @ 2.5V
    assert len(comp_map["U_INT_RST_SW"].pins) == 16 # 16-TSSOP ADG1211YRUZ
    assert len(comp_map["U_LDO_P5A"].pins) == 11    # DFN-10+EP11 LT3045EDD
    assert len(comp_map["U_LDO_N5A"].pins) == 13    # DFN-12+EP13 LT3094EDD
    assert len(comp_map["U_LDO_3V3"].pins) == 5     # TSOT-23-5 ADP7142AUJZ
    assert len(comp_map["U_LDO_2V5RF"].pins) == 5   # TSOT-23-5 ADP7142AUJZ-2.5
    # Verify TLV3501AID Pin 8 (SHDN) tied to DGND (active-LOW shutdown bug fixed!)
    dgnd_nodes = set(next(n for n in laser_spec.nets if n.name == "DGND").nodes)
    assert ("U_CMP_OTEMP", "8") in dgnd_nodes, "TLV3501AID Pin 8 SHDN must tie to DGND!"


def test_laser_aom_pyrometer_afe_live_ngspice_and_mna_parity() -> None:
    cir = LASER_DIR / "laser_pyro_tia_aom.cir"
    res = run_ngspice(cir, workdir=LASER_DIR)
    assert res.ok, f"ngspice failed: {res.errors}"
    assert res.returncode == 0
    assert len(res.errors) == 0

    m = res.metrics
    # OBS-037: Reverse-biased photodiodes (+5V rev bias, positive TIA outputs!), TLV3501 OTEMP polarity, DC-blocked RF SMA!
    assert m["pd_ig_rev_bias_v"] > 4.5 and m["pd_si_rev_bias_v"] > 4.5
    assert m["ig_v_final"] > 0.5 and m["si_v_final"] > 0.5
    assert m["otemp_ok_healthy_v"] > 3.0 and m["otemp_ok_1687k_v"] < 0.2
    assert abs(m["rf_out_dc_v"]) < 1e-3

    # 2-color InGaAs (1550 nm) + Si (850 nm) TIA rise time < 10 us + MNA parity
    assert 0.0 < m["tau_rise_ingaas_s"] < 10.0e-6
    assert 0.0 < m["tau_rise_si_s"] < 10.0e-6
    mna = run_laser_mna()
    assert abs(m["z_dc_ingaas"] - mna["mna_z_dc_ingaas_ohm"]) / mna["mna_z_dc_ingaas_ohm"] < 0.005
    assert abs(m["z_dc_si"] - mna["mna_z_dc_si_ohm"]) / mna["mna_z_dc_si_ohm"] < 0.005

    # 1.0 ms pulse-energy integrator 2x linearity (< 1% error) & clean reset
    assert 0.98 < m["v_int_1x"] < 1.02
    assert 1.96 < m["v_int_2x"] < 2.04
    assert m["int_lin_err_pct"] < 1.0
    assert abs(m["v_int_1x_after_rst"]) < 5.0e-3

    # OBS-093: Log-linearized AD8367 50 dB/V VCA [0.65, 1.40] gain ratio, zero PID limit cycle (< 2% tail p-p), < 50 us cutoff
    assert abs(m["vca_mod_ratio"] - (1.40 / 0.65)) < 0.05
    assert m["cl_p_tail_pp"] < 0.02
    assert m["rf_flatness_db"] < 0.5
    assert 0.0 < m["crowbar_vca_cutoff_s"] < 50.0e-6
    assert 0.0 < m["crowbar_diode_cutoff_s"] < 50.0e-6
    assert m["diode_v_on"] > 23.0 and abs(m["diode_v_off"]) < 0.05


# ---------------------------------------------------------------------------
# 4. Board 3: safety_interlock_1oo2d — KiCad 8 ERC/DRC/Routing/22kV + Live ngspice-47
# ---------------------------------------------------------------------------

def test_safety_interlock_1oo2d_kicad_erc_drc_and_22kv_hv_rules(safety_spec: BoardSpec) -> None:
    expected_boms = {
        "S7.SAFETY-03", "S7.SAFETY-02", "S7.SAFETY-05", "S7.SAFETY-06",
        "S7.SAFETY-01", "S7.4-04", "S5.5-04",
    }
    assert expected_boms.issubset(set(safety_spec.bom_ids))

    # Verify diverse hardware components exist in schematic/PCB (force-guided relays + opto SSRs + WDT + 4x E-Stop)
    refs = {c.ref for c in safety_spec.components}
    for required_ref in (
        "J_ESTOP1", "J_ESTOP2", "J_ESTOP3", "J_ESTOP4",
        "K_FG_A1", "K_FG_A2", "U_OPTO_SSR_B1", "Q_SSR_B1",
        "U_WDT_WIN", "U_DIAG_XOR_VOTE", "U_DIAG_XOR_FB",
        "K_CROWBAR_A", "K_CROWBAR_B", "R_CROWBAR_1", "R_CROWBAR_2",
    ):
        assert required_ref in refs, f"Missing required 1oo2D safety component {required_ref}"

    sch = SAFETY_DIR / "safety_interlock_1oo2d.kicad_sch"
    pcb = SAFETY_DIR / "safety_interlock_1oo2d.kicad_pcb"
    assert parse_sexpr(sch.read_text(encoding="utf-8"))[0] == "kicad_sch"
    assert parse_sexpr(pcb.read_text(encoding="utf-8"))[0] == "kicad_pcb"

    erc = run_erc(sch, safety_spec, pcb_path=pcb)
    assert erc.passed, f"ERC failed: {erc.errors}"
    assert erc.sch_pcb_parity_ok

    drc = run_drc(pcb, safety_spec)
    assert drc.passed, f"DRC failed: {drc.errors}"
    assert drc.unrouted_net_count == 0
    assert drc.unconnected_items == 0
    assert drc.track_dangling_count == 0
    assert drc.routed_net_count == drc.total_multi_pin_nets and drc.total_multi_pin_nets >= 74
    assert drc.stackup_summary["copper_layers"] == 4
    assert drc.air_slot_count >= 2
    assert len(drc.hv_checks) == 1
    hv = drc.hv_checks[0]
    assert hv["passed"] is True
    assert hv["through_board_ok"] is True
    assert hv["measured_clearance_mm"] >= 30.0
    assert hv["measured_creepage_mm"] >= 50.0

    # OBS-051 / OBS-052 / OBS-053 / OBS-087 regressions:
    comp_map = {c.ref: c for c in safety_spec.components}
    # Zero 0R_1206 SMD HV-PE jumper; bolted M6 star stud return!
    assert not any("0R_1206" in c.value for c in safety_spec.components), "0R_1206 SMD HV-PE jumper forbidden!"
    # Exact 10-pin G7SA-3A1B force-guided safety relays (OBS-087)
    assert len(comp_map["K_FG_A1"].pins) == 10 and len(comp_map["K_FG_A2"].pins) == 10
    # Independent diagnostic WDT rail + 2N7002K coil drivers + 5V Zener clamp + 33ms skew blanking RC!
    assert any(n.name == "V_5V_DIAG" for n in safety_spec.nets)
    for req in ("Q_DRV_KFG1", "Q_DRV_KFG2", "D_Z_DIAG_FBB", "R_FB_SKEW_FILT", "C_FB_SKEW_FILT", "U_OPTO_WDT_AB"):
        assert req in comp_map, f"Missing OBS-052/053 component {req}"


def test_safety_interlock_1oo2d_live_ngspice_crowbar_and_fault_injection() -> None:
    cir = SAFETY_DIR / "safety_1oo2d_crowbar.cir"
    res = run_ngspice(cir, workdir=SAFETY_DIR)
    assert res.ok, f"ngspice failed: {res.errors}"
    assert res.returncode == 0
    assert len(res.errors) == 0

    m = res.metrics
    ana = run_safety_ana()

    # 1) Nominal 22 kV 1.5 nF 2 MOhm crowbar -> < 50 V in ~18.3 ms < 50 ms, E = 0.363 J < 0.5 J
    assert abs(m["hv_nom_init_v"] - 22000.0) < 5.0
    assert 15.0 < m["hv_nom_t50_ms"] < 50.0
    assert abs(m["hv_nom_t50_ms"] - ana["analytical_t_50v_ms"]) < 0.5
    assert 0.35 < m["hv_nom_energy_j"] < 0.50
    assert abs(m["hv_nom_energy_j"] - 0.363) < 0.005
    assert m["hv_nom_v_at_40m"] < 2.0

    # 2) Single-channel fault injection: K_CROWBAR_A stuck OPEN -> Ch-B still discharges < 50 ms!
    assert 15.0 < m["hv_flt_t50_ms"] < 50.0
    assert abs(m["hv_flt_energy_j"] - 0.363) < 0.005

    # 3) Single-channel fault injection: K_FG_A1 welded CLOSED -> Ch-B SSR cuts shutter safe + discrepancy trips!
    assert m["sh_v_on"] > 23.0
    assert abs(m["sh_v_safe"]) < 0.05
    assert abs(m["sh_i_safe"]) < 1e-4
    assert 0.0 < m["sh_drop_ms"] < 3.2
    assert m["discrep_fault_v"] > 4.5

    # 4) Single-channel open-wire sensor break on ESTOP_A -> de-energizes load safe!
    assert m["ow_v_on"] > 23.0
    assert abs(m["ow_v_safe"]) < 0.05

    # 5) OBS-052 / OBS-053 component-level comparator, live-zero, OSHA O2, Vgs clamp, skew blanking regressions!
    assert m["ph3_healthy_5ma_v"] > 4.5 and m["ph3_openwire_0ma_v"] < 0.5 and m["ph3_leak_12ma_v"] < 0.5
    assert m["o2_healthy_20p9_v"] > 4.5 and m["o2_osha_19p0_trip_v"] < 0.5
    assert 10.0 < m["pmos_vgs_on_v"] < 15.0
    assert m["skew_blank_peak_v"] < 2.0


# ---------------------------------------------------------------------------
# 5. Adversarial Negative Check: HV Air-Slot Removal Must Fail 22 kV Creepage
# ---------------------------------------------------------------------------

def test_removing_hv_air_slots_triggers_real_drc_failure(safety_spec: BoardSpec, tmp_path: Path) -> None:
    no_slots_spec = BoardSpec(
        **{
            **safety_spec.__dict__,
            "keepouts": (),  # Strip milled air-slots: direct clearance is ~43.2 mm (< 50 mm creepage req!)
        }
    )
    pcb_bad = write_kicad_pcb(no_slots_spec, tmp_path / "safety_no_slots.kicad_pcb")
    drc_bad = run_drc(pcb_bad, no_slots_spec)
    assert not drc_bad.passed
    assert any("HV Creepage/Clearance DRC fail" in e for e in drc_bad.errors)


def test_verification_json_reports_match_all_passed() -> None:
    for vpath in (
        ION_DIR / "ion_column_hv_dac_verification.json",
        LASER_DIR / "laser_aom_pyrometer_afe_verification.json",
        SAFETY_DIR / "safety_interlock_1oo2d_verification.json",
    ):
        data = json.loads(vpath.read_text(encoding="utf-8"))
        assert data["all_passed"] is True, f"{vpath.name} did not pass all checks: {data['checks']}"
        assert data["board"]["passed"] is True
        assert len(data["board"]["erc"]["errors"]) == 0
        assert len(data["board"]["drc"]["errors"]) == 0
        assert data["board"]["drc"]["unrouted_net_count"] == 0
        assert data["board"]["drc"]["unconnected_items"] == 0
        assert data["board"]["drc"]["track_dangling_count"] == 0
        assert data["board"]["drc"]["routed_net_count"] == data["board"]["drc"]["total_multi_pin_nets"]
        assert data["ngspice"]["ok"] is True
