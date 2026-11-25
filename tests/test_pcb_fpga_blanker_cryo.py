"""Comprehensive Verification Tests for Wave 2B Boards:
  1. fpga_brain_carrier      (8L Isola FR408HR, XC7K325T-2FFG900 + ZU48DR ICD, live PDN SPICE)
  2. blanker_asic_mezzanine  (6L Rogers/Polyimide UHV, 4x64 SKY130, 5 kV Iso, live HV driver SPICE)
  3. cryo_cmos_4k_carrier    (4L Rogers/AlN/Cu-Invar-Cu, 968-gate SKY130 + 4 K/MXC filter SPICE)

Verifies strict S-expression validity, reconstructive schematic ERC (0 errors, SCH<->PCB parity),
geometric PCB DRC (0 errors, controlled Z0 ±5%, 5 kV air-slot & IEC 61010-1 creepage/clearance),
adversarial fault-injection on the 5 kV barrier, live ngspice-47 execution (0 errors, 0 warnings),
independent Python MNA/Nyquist cross-checks, and zero hardcoded host paths.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
import re

import pytest

from hardware.pcb.blanker_asic_mezzanine.build_blanker_mezzanine import (
    BLANKER_TILE_RTL_PORTS,
    build_blanker_mezzanine,
)
from hardware.pcb.cryo_cmos_4k_carrier.build_cryo_4k_carrier import (
    build_cryo_4k_carrier,
    run_cryo_filter_mna_crosscheck,
)
from hardware.pcb.fpga_brain_carrier.build_fpga_carrier import (
    build_fpga_brain_carrier,
    load_yosys_sizing_metadata,
    run_pdn_mna_crosscheck,
)
from hardware.pcb.kicad_eda_verify import (
    BoardSpec,
    ComponentSpec,
    auto_footprint_pads,
    parse_sexpr,
    run_drc,
    run_erc,
    run_ngspice,
    verify_board_bundle,
    write_kicad_pcb,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PCB_ROOT = REPO_ROOT / "hardware" / "pcb"
FPGA_DIR = PCB_ROOT / "fpga_brain_carrier"
BLANKER_DIR = PCB_ROOT / "blanker_asic_mezzanine"
CRYO_DIR = PCB_ROOT / "cryo_cmos_4k_carrier"


# Cached per-session BoardSpec builders (still runs live auto_route_board once per board!)
_cached_fpga = functools.lru_cache(maxsize=1)(build_fpga_brain_carrier)
_cached_blanker = functools.lru_cache(maxsize=1)(build_blanker_mezzanine)
_cached_cryo = functools.lru_cache(maxsize=1)(build_cryo_4k_carrier)

HOST_PATH_RE = re.compile(r"/home/[A-Za-z0-9_.-]+|/Users/[A-Za-z0-9_.-]+|/run/media/[A-Za-z0-9_.-]+")


# ---------------------------------------------------------------------------
# 1. Hygiene, Reproducibility & Epistemic Contract Tests
# ---------------------------------------------------------------------------

def test_zero_hardcoded_host_paths_across_wave2b_files() -> None:
    owned_files = [
        FPGA_DIR / "build_fpga_carrier.py",
        FPGA_DIR / "fpga_pdn_1v0.cir",
        FPGA_DIR / "fpga_brain_carrier_verification.json",
        FPGA_DIR / "README.md",
        BLANKER_DIR / "build_blanker_mezzanine.py",
        BLANKER_DIR / "blanker_hv_driver.cir",
        BLANKER_DIR / "blanker_asic_mezzanine_verification.json",
        BLANKER_DIR / "README.md",
        CRYO_DIR / "build_cryo_4k_carrier.py",
        CRYO_DIR / "cryo_4k_gate_filter.cir",
        CRYO_DIR / "cryo_cmos_4k_carrier_verification.json",
        CRYO_DIR / "README.md",
        Path(__file__).resolve(),
    ]
    for path in owned_files:
        assert path.is_file(), f"Missing expected Wave 2B artifact: {path}"
        text = path.read_text(encoding="utf-8")
        m = HOST_PATH_RE.search(text)
        assert m is None, f"Hardcoded host path {m.group(0)!r} found in {path.relative_to(REPO_ROOT)}"


@pytest.mark.parametrize(
    "json_path",
    [
        FPGA_DIR / "fpga_brain_carrier_verification.json",
        BLANKER_DIR / "blanker_asic_mezzanine_verification.json",
        CRYO_DIR / "cryo_cmos_4k_carrier_verification.json",
    ],
)
def test_verification_json_epistemic_contract(json_path: Path) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["all_passed"] is True
    assert all(data["checks"].values())
    meta = data["epistemic_meta"]
    assert meta["design_stage"] == "M0/M1_DESIGN_ONLY"
    assert meta["no_lab_measurement"] is True
    assert meta["no_physical_fab"] is True
    assert meta["iec61508_certified"] is False
    assert meta["semi_s2_certified"] is False
    assert "ngspice" in meta["simulation_engine"].lower()


# ---------------------------------------------------------------------------
# 2. Strict KiCad 8 S-Expr, ERC=0, DRC=0, Stackup & Z0 Verification (All 3 Boards)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "board_dir,builder,expected_layers,min_comps,min_z0,expected_hv,expected_slots",
    [
        (FPGA_DIR, _cached_fpga, 8, 130, 20, 0, 0),
        (BLANKER_DIR, _cached_blanker, 6, 60, 8, 1, 1),
        (CRYO_DIR, _cached_cryo, 4, 80, 4, 0, 0),
    ],
)
def test_all_three_boards_strict_sexpr_erc_drc_zero(
    board_dir: Path,
    builder,
    expected_layers: int,
    min_comps: int,
    min_z0: int,
    expected_hv: int,
    expected_slots: int,
    tmp_path: Path,
) -> None:
    spec = builder()
    sch_path = board_dir / f"{spec.name}.kicad_sch"
    pcb_path = board_dir / f"{spec.name}.kicad_pcb"
    assert sch_path.is_file() and pcb_path.is_file()

    # Strict S-expr parse from disk
    sch_tree = parse_sexpr(sch_path.read_text(encoding="utf-8"))
    pcb_tree = parse_sexpr(pcb_path.read_text(encoding="utf-8"))
    assert sch_tree[0] == "kicad_sch"
    assert pcb_tree[0] == "kicad_pcb"

    # Strict reconstructive ERC + SCH/PCB parity
    erc = run_erc(sch_path, spec, pcb_path=pcb_path)
    assert erc.passed, f"ERC failed on {spec.name}: {erc.errors}"
    assert len(erc.errors) == 0
    assert erc.sch_pcb_parity_ok
    assert erc.component_count >= min_comps

    # Strict geometric PCB DRC + physical connectivity + stackup + controlled impedance + HV clearance/creepage
    drc = run_drc(pcb_path, spec)
    assert drc.passed, f"DRC failed on {spec.name}: {drc.errors}"
    assert len(drc.errors) == 0
    assert drc.unrouted_net_count == 0
    assert drc.unconnected_items == 0
    assert drc.track_dangling_count == 0
    assert drc.routed_net_count == drc.total_multi_pin_nets and drc.total_multi_pin_nets > 0
    assert drc.stackup_summary["copper_layers"] == expected_layers
    assert len(drc.impedance_checks) >= min_z0
    assert all(ic["passed"] and ic["error_pct"] <= 5.0 for ic in drc.impedance_checks)
    assert len(drc.hv_checks) == expected_hv
    assert all(hc["passed"] for hc in drc.hv_checks)
    assert drc.air_slot_count == expected_slots

    # Deterministic regeneration parity check
    rebuilt = verify_board_bundle(spec, tmp_path)
    assert rebuilt["passed"] is True
    assert rebuilt["drc"]["unrouted_net_count"] == 0
    assert rebuilt["drc"]["unconnected_items"] == 0
    assert rebuilt["drc"]["track_dangling_count"] == 0
    assert (tmp_path / f"{spec.name}.kicad_sch").read_text(encoding="utf-8") == sch_path.read_text(encoding="utf-8")
    assert (tmp_path / f"{spec.name}.kicad_pcb").read_text(encoding="utf-8") == pcb_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 3. Suite 1: FPGA Brain Carrier Architecture, Yosys Sizing & Live PDN ngspice-47
# ---------------------------------------------------------------------------

def test_fpga_brain_carrier_yosys_sizing_and_architecture() -> None:
    sizing = load_yosys_sizing_metadata()
    src = sizing["yosys_measured_sources"]
    assert src["ecp5_boed_q16_core"]["lut4"] == 3871
    assert src["ecp5_boed_q16_core"]["mult18x18d"] == 106
    assert src["xc7_boed_q16_core"]["lut"] == 5467
    assert src["xc7_boed_q16_core"]["dsp48e1"] == 99
    assert src["xcup_boed_top_16ch"]["lut"] == 102886
    assert src["xcup_boed_top_16ch"]["dsp48e2"] == 1584
    assert sizing["carrier_fpga"]["part_number"] == "XC7K325T-2FFG900"
    assert sizing["carrier_fpga"]["headroom_factor"]["dsp48e1_x"] > 4.0
    assert sizing["carrier_fpga"]["headroom_factor"]["lut_x"] > 10.0
    assert sizing["zu48dr_2u_rack_icd_ref"]["bom_id"] == "S6.11-01"

    spec = _cached_fpga()
    refs = {c.ref for c in spec.components}
    for required_ref in (
        "U1", "U_SEQ1", "U_VR_1V0", "U_VR_1V8", "U_VR_1V2", "U_VTT_0V6",
        "U_VR_2V5", "U_VR_3V3", "U_LDO_MGT1V0", "U_LDO_MGT1V2",
        "J_RB_10M", "J_WR_TRIG", "U_CLK", "Y_VCXO",
        "U_DDR4_A", "U_DDR4_B", "U_QSPI", "J_FMC_HPC",
        "U_ISO_IBIC", "U_ISO_BLK", "U_ISO_HVDAC", "U_ISO_AOM_IL",
        "U_GBE", "J_ETH", "U_UART", "J_USB", "J_JTAG",
    ):
        assert required_ref in refs, f"Missing required FPGA carrier component {required_ref}"
    pdn_caps = [c for c in spec.components if c.ref.startswith("C_PDN_")]
    assert len(pdn_caps) == 64  # 4 + 8 + 12 + 16 + 24 multi-decade bank


def test_fpga_pdn_live_ngspice_and_mna_parity() -> None:
    cir_path = FPGA_DIR / "fpga_pdn_1v0.cir"
    assert cir_path.is_file()
    res = run_ngspice(cir_path, workdir=FPGA_DIR)
    assert res.ok and res.returncode == 0
    assert len(res.errors) == 0 and len(res.warnings) == 0

    m = res.metrics
    z_max_mohm = m["z_pdn_max_ohm"] * 1e3
    z_20m_mohm = m["z_pdn_20mhz_ohm"] * 1e3
    v_droop_mv = m["v_droop_v"] * 1e3
    v_over_mv = m["v_overshoot_v"] * 1e3

    assert 0.5 < z_max_mohm < 10.0, f"PDN peak impedance {z_max_mohm:.3f} mOhm >= 10 mOhm"
    assert 0.5 < z_20m_mohm < 10.0, f"PDN 20 MHz impedance {z_20m_mohm:.3f} mOhm >= 10 mOhm"
    assert 1.0 < v_droop_mv < 30.0, f"5 A step droop {v_droop_mv:.3f} mV >= 30 mV (±3%)"
    assert 0.5 < v_over_mv < 30.0, f"5 A release overshoot {v_over_mv:.3f} mV >= 30 mV"

    # Independent Python MNA parity (< 1%)
    mna = run_pdn_mna_crosscheck()
    rel_diff_pct = abs(z_max_mohm - mna["mna_z_pdn_max_mohm"]) / mna["mna_z_pdn_max_mohm"] * 100.0
    assert rel_diff_pct < 1.0, f"MNA vs ngspice PDN Z_max diff {rel_diff_pct:.3f}%"


# ---------------------------------------------------------------------------
# 4. Suite 2: Blanker ASIC Mezzanine RTL Parity, 5 kV Barrier & Live HV SPICE
# ---------------------------------------------------------------------------

def test_blanker_mezzanine_rtl_interface_and_5kv_barrier_fault_injection(tmp_path: Path) -> None:
    # Verify exact blanker_tile.v port names directly against read-only src/rtl/blanker_tile.v
    rtl_text = (REPO_ROOT / "src" / "rtl" / "blanker_tile.v").read_text(encoding="utf-8")
    for port in BLANKER_TILE_RTL_PORTS:
        base_port = port.split("[", 1)[0]
        assert base_port in rtl_text, f"Port {base_port} not found in src/rtl/blanker_tile.v"

    spec = _cached_blanker()
    refs = {c.ref for c in spec.components}
    for t in range(4):
        assert f"U_TILE{t}" in refs
    for b in range(16):
        assert f"U_HVDRV{b}" in refs
    for req in ("J_CF100_A", "J_CF100_B", "J_LTCC_A", "J_LTCC_B", "U_DCDC_5KV", "U_ISO_CTRL", "U_ISO_DATA", "U_ISO_OVRD", "U_OVRD_GATE"):
        assert req in refs

    # Verify nominal 5 kV HV clearance (>=12 mm) & creepage (>=15 mm)
    drc_ok = run_drc(BLANKER_DIR / "blanker_asic_mezzanine.kicad_pcb", spec)
    assert drc_ok.passed
    hv = drc_ok.hv_checks[0]
    assert hv["measured_clearance_mm"] >= 12.0
    assert hv["measured_creepage_mm"] >= 15.0
    assert hv["through_board_ok"] is True

    # Adversarial HV fault-injection: place an Earth-GND resistor inside the 5 kV moat -> DRC MUST FAIL!
    bad_comp = ComponentSpec(
        "R_BAD_MOAT", "10k_MOAT_FAULT", "Resistor_SMD:R_0603_1608Metric",
        50.0, 20.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="TEST",
    )
    bad_nets = tuple(
        ns if ns.name != "GND_EARTH" else ns.__class__(
            **{**ns.__dict__, "nodes": ns.nodes + (("R_BAD_MOAT", "1"), ("R_BAD_MOAT", "2"))}
        )
        for ns in spec.nets
    )
    bad_spec = BoardSpec(**{**spec.__dict__, "components": spec.components + (bad_comp,), "nets": bad_nets})
    bad_pcb = write_kicad_pcb(bad_spec, tmp_path / "blanker_moat_fault.kicad_pcb")
    drc_bad = run_drc(bad_pcb, bad_spec)
    assert not drc_bad.passed
    assert any("HV Creepage/Clearance DRC fail" in e for e in drc_bad.errors)


def test_blanker_hv_driver_live_ngspice() -> None:
    cir_path = BLANKER_DIR / "blanker_hv_driver.cir"
    assert cir_path.is_file()
    res = run_ngspice(cir_path, workdir=BLANKER_DIR)
    assert res.ok and res.returncode == 0
    assert len(res.errors) == 0 and len(res.warnings) == 0

    m = res.metrics
    t_rise_ns = m["t_rise_10_90_s"] * 1e9
    t_fall_ns = m["t_fall_90_10_s"] * 1e9
    t_ovrd_ns = m["t_ovrd_clamp_s"] * 1e9

    assert 0.5 < t_rise_ns < 100.0, f"10-90% rise time {t_rise_ns:.2f} ns >= 100 ns"
    assert 0.5 < t_fall_ns < 100.0, f"90-10% fall time {t_fall_ns:.2f} ns >= 100 ns"
    assert 5.0 < t_ovrd_ns < 200.0, f"Global blank-override clamp {t_ovrd_ns:.2f} ns >= 200 ns"
    assert m["v_plate_hi_v"] >= 53.0
    assert m["v_plate_lo_v"] <= 0.1
    assert m["v_plate_ovrd_v"] >= 53.0  # Clamped HIGH even while blanker_open is stuck at 1.8 V!

    # Bounded 256-ch board dynamic+static power
    e_tot_j = m["e_hv_cycle_j"] + m["e_5v_cycle_j"] + m["e_1v8_cycle_j"]
    p_stat_w = m["p_hv_static_w"]
    p_256_1khz_w = 256.0 * (e_tot_j * 1e3 + p_stat_w)
    p_256_50khz_w = 256.0 * (e_tot_j * 50e3 + p_stat_w)
    assert p_256_1khz_w < 0.10, f"256-ch @ 1 kHz power {p_256_1khz_w*1e3:.1f} mW unexpectedly high"
    assert p_256_50khz_w < 5.0, f"256-ch @ 50 kHz power {p_256_50khz_w:.2f} W exceeds 5 W deck budget"


# ---------------------------------------------------------------------------
# 5. Suite 3: Cryo-CMOS 4 K Carrier Architecture & Live 4 K / 20 mK ngspice-47
# ---------------------------------------------------------------------------

def test_cryo_4k_carrier_architecture_and_cryo_dielectrics() -> None:
    spec = _cached_cryo()
    muxes = [c for c in spec.components if c.ref.startswith("U_MUX")]
    eccos = [c for c in spec.components if c.ref.startswith("FB_ECCO_")]
    caps = [c for c in spec.components if c.ref.startswith("C")]
    assert len(muxes) == 8  # 8 x 121 = 968 multiplexed DC gates
    assert len(eccos) == 8  # 8 Eccosorb CR-124 filter channels
    assert len(caps) >= 30
    # Zero Class-II X7R/X5R capacitors on 4 K board (prevents cryogenic capacitance freeze-out!)
    assert all("C0G" in c.value.upper() for c in caps)
    assert spec.epistemic_meta["total_multiplexed_dc_gates"] == 968
    assert spec.epistemic_meta["power_budget_4k_max_mW"] == 15.4


def test_cryo_4k_filter_and_crossbar_power_live_ngspice_and_mna() -> None:
    cir_path = CRYO_DIR / "cryo_4k_gate_filter.cir"
    assert cir_path.is_file()
    cir_text = cir_path.read_text(encoding="utf-8")
    assert ".temp -269.15" in cir_text
    assert "temp=-273.13" in cir_text

    res = run_ngspice(cir_path, workdir=CRYO_DIR)
    assert res.ok and res.returncode == 0
    assert len(res.errors) == 0 and len(res.warnings) == 0

    m = res.metrics
    atten_1ghz = m["atten_1ghz_db"]
    noise_10hz_uv = m["noise_10hz_v_rthz"] * 1e6
    noise_peak_uv = m["noise_peak_v_rthz"] * 1e6
    noise_intr_nv = m["noise_intr_10hz_v_rthz"] * 1e9
    p_4k_tot_mw = m["p_4k_total_avg_w"] * 1e3
    t_settle_ms = m["t_settle_0p1pct_s"] * 1e3

    assert atten_1ghz <= -60.0, f"RF attenuation @ 1 GHz ({atten_1ghz:.2f} dB) failed >60 dB spec"
    assert 0.0 < noise_10hz_uv < 0.5, f"In-band noise {noise_10hz_uv:.4f} uV/rtHz >= 0.5 uV/rtHz"
    assert 0.0 < noise_peak_uv < 0.5, f"Peak noise {noise_peak_uv:.4f} uV/rtHz >= 0.5 uV/rtHz"
    assert 0.0 < t_settle_ms < 5.0, f"Settling time {t_settle_ms:.3f} ms out of range"
    assert 0.0 < p_4k_tot_mw <= 15.4, f"968-gate 4 K power {p_4k_tot_mw:.3f} mW > 15.4 mW budget"

    # Independent Python MNA & Nyquist parity checks
    mna = run_cryo_filter_mna_crosscheck()
    assert abs(atten_1ghz - mna["mna_atten_1ghz_db"]) < 0.5
    assert abs(m["atten_100mhz_db"] - mna["mna_atten_100mhz_db"]) < 0.1
    assert abs(noise_intr_nv - mna["analytical_intrinsic_4k_20mk_noise_nV_rtHz"]) / mna["analytical_intrinsic_4k_20mk_noise_nV_rtHz"] < 0.02
