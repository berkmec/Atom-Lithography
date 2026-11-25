"""Unit & Integration Tests for the KiCad 8 EDA Kernel and IBIC Cryo Front-End v3 3-PCB Kit.

Verifies:
  1. Portable real rootless ngspice execution and generic zero-host-path hygiene.
  2. Strict S-expression parser, reconstructive schematic ERC, geometric PCB DRC,
     physical pad-segment-via-zone Union-Find connectivity (unconnected_items == 0,
     track_dangling_count == 0), analytical microstrip/stripline Z0 (±5%),
     IPC-2221/IEC-61010 HV creepage/clearance + >=1000 V through-board dielectric
     field checks (pads, segments & vias), deterministic auto_route_board(), and
     Python MNA — including negative fault-injection tests proving every checker
     catches real defects!
  3. All 3 split KiCad 8 IBIC v3 boards (ibic_cold_csa_100k, ibic_warm_shaper_300k,
     ibic_hv_bias_guard): strict S-expr, 0 ERC, 0 DRC, 100% physical routing
     (0 unconnected, 0 dangling), SCH/PCB parity, 50 Ohm Z0, HV rules.
  4. Live ngspice-47 execution of ibic_cryo_chain_100k.cir (AC, 5 keV TRAN, 100 K/300 K
     NOISE, S3.2-03 3-stage HV filter) and independent MNA cross-check parity.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re

import pytest

from hardware.pcb.ibic_cryo_frontend_v3.build_ibic_v3 import (
    LINDHARD_5KEV_100K_E,
    build_cold_csa_board,
    build_hv_bias_guard_board,
    build_warm_shaper_board,
    compute_cold_stray_c_budget_pf,
    run_mna_crosscheck,
)
from hardware.pcb.kicad_eda_verify import (
    BoardSpec,
    ComponentSpec,
    CreepageRule,
    KeepoutSpec,
    MnaCircuit,
    NetSpec,
    SexprParseError,
    StackupLayer,
    TraceSpec,
    ViaSpec,
    ZoneSpec,
    auto_footprint_pads,
    auto_route_board,
    calc_diff_microstrip_z0,
    calc_microstrip_z0,
    calc_stripline_z0,
    find_ngspice,
    get_ngspice_version,
    ipc2221_min_spacing_mm,
    parse_sexpr,
    run_drc,
    run_erc,
    run_ngspice,
    solve_diff_microstrip_width_mm,
    solve_microstrip_width_mm,
    solve_stripline_width_mm,
    write_kicad_pcb,
    write_kicad_sch,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
IBIC_DIR = REPO_ROOT / "hardware" / "pcb" / "ibic_cryo_frontend_v3"
HOST_PATH_RE = re.compile(r"/home/[A-Za-z0-9_.-]+|/Users/[A-Za-z0-9_.-]+|/run/media/[A-Za-z0-9_.-]+")


# ---------------------------------------------------------------------------
# 1. Portable ngspice Discovery, Hygiene & S-Expression Parser Tests
# ---------------------------------------------------------------------------

def test_ngspice_discovered_and_runnable() -> None:
    ng_bin = find_ngspice()
    assert ng_bin.is_file()
    ver = get_ngspice_version()
    assert "ngspice" in ver.lower()


def test_zero_hardcoded_user_paths_in_owned_code() -> None:
    targets = [
        REPO_ROOT / "hardware" / "pcb" / "__init__.py",
        REPO_ROOT / "hardware" / "pcb" / "kicad_eda_verify.py",
        IBIC_DIR / "build_ibic_v3.py",
        IBIC_DIR / "ibic_cryo_chain_100k.cir",
        IBIC_DIR / "ibic_v3_verification.json",
        IBIC_DIR / "README.md",
        Path(__file__).resolve(),
    ]
    for p in targets:
        text = p.read_text(encoding="utf-8")
        # Strip this regex literal line from the test file itself before scanning
        if p == Path(__file__).resolve():
            text = "\n".join(line for line in text.splitlines() if "HOST_PATH_RE =" not in line)
        match = HOST_PATH_RE.search(text)
        assert match is None, f"Hardcoded host path {match.group(0)!r} found in {p.relative_to(REPO_ROOT)}"


def test_sexpr_parser_valid_and_malformed_rejection() -> None:
    tree = parse_sexpr('(kicad_sch (version 20231120) (property "Value" "10k \\"precision\\""))')
    assert tree[0] == "kicad_sch"
    assert tree[1] == ["version", "20231120"]
    assert tree[2] == ["property", "Value", '10k "precision"']

    for bad in ("", "   ", "bare_atom", "(a (b 1)", "(a 1))", '(a "unterminated)', "(a 1) (b 2)"):
        with pytest.raises(SexprParseError):
            parse_sexpr(bad)


def test_impedance_and_ipc2221_calculators() -> None:
    w50 = solve_microstrip_width_mm(50.0, h_mm=0.254, t_mm=0.035, er=3.48)
    assert abs(calc_microstrip_z0(w50, 0.254, 0.035, 3.48) - 50.0) < 0.05
    assert 0.50 < w50 < 0.58  # Rogers RO4350B 10 mil 1 oz ~ 0.54 mm

    w100d = solve_diff_microstrip_width_mm(100.0, spacing_mm=0.20, h_mm=0.15, t_mm=0.035, er=3.66)
    assert abs(calc_diff_microstrip_z0(w100d, 0.20, 0.15, 0.035, 3.66) - 100.0) < 0.1

    w50_sl = solve_stripline_width_mm(50.0, b_mm=0.45, t_mm=0.035, er=3.66)
    assert abs(calc_stripline_z0(w50_sl, 0.45, 0.035, 3.66) - 50.0) < 0.1
    z_sl = calc_stripline_z0(0.18, b_mm=0.45, t_mm=0.035, er=3.66)
    assert 40.0 < z_sl < 65.0

    clr100, crp100 = ipc2221_min_spacing_mm(100.0)
    clr5k, crp5k = ipc2221_min_spacing_mm(5000.0)
    assert clr100 >= 0.6 and crp100 >= 1.0
    assert clr5k > clr100 and crp5k > clr5k


# ---------------------------------------------------------------------------
# 2. Adversarial Fault-Injection Tests (Prove ERC/DRC/Connectivity/HV Catch Real Bugs!)
# ---------------------------------------------------------------------------

def _minimal_clean_board() -> BoardSpec:
    stackup = (
        StackupLayer("F.Cu", "signal", 0.035, material="Copper"),
        StackupLayer("dielectric 1", "core", 0.254, epsilon_r=3.48, loss_tangent=0.0037, material="Rogers RO4350B"),
        StackupLayer("B.Cu", "power", 0.035, material="Copper"),
    )
    w50 = solve_microstrip_width_mm(50.0, 0.254, 0.035, 3.48)
    r1 = ComponentSpec("R1", "49.9R", "Resistor_SMD:R_0603_1608Metric", 10.0, 10.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="TEST")
    j1 = ComponentSpec("J1", "SMA_IN", "Connector_Coaxial:SMA", 20.0, 10.0, pins=auto_footprint_pads("SMA", ("1", "2")), bom_id="TEST")
    nets = (
        NetSpec("SIG50", (("R1", "2"), ("J1", "1")), target_z0_ohm=50.0),
        NetSpec("GND", (("R1", "1"), ("J1", "2")), is_power=True, has_pwr_flag=True),
    )
    # Both nets physically routed pad-to-pad (R1.1=9.2,10.0 -> J1.2=22.54,10.0 via bottom rail; SIG50 R1.2=10.8,10.0 -> J1.1=20.0,10.0)
    traces = (
        TraceSpec("SIG50", "F.Cu", ((10.8, 10.0), (20.0, 10.0)), width_mm=w50),
        TraceSpec("GND", "F.Cu", ((9.2, 10.0), (9.2, 14.0), (22.54, 14.0), (22.54, 10.0)), width_mm=0.25),
    )
    return BoardSpec(
        name="mini_test", title="Mini Test", rev="v1", bom_ids=("TEST",),
        width_mm=30.0, height_mm=20.0, stackup=stackup,
        components=(r1, j1), nets=nets, traces=traces,
    )


def test_erc_and_drc_detect_injected_defects(tmp_path: Path) -> None:
    clean = _minimal_clean_board()
    sch = write_kicad_sch(clean, tmp_path / "clean.kicad_sch")
    pcb = write_kicad_pcb(clean, tmp_path / "clean.kicad_pcb")
    assert run_erc(sch, clean, pcb_path=pcb).passed
    drc_clean = run_drc(pcb, clean)
    assert drc_clean.passed, f"Unexpected clean DRC errors: {drc_clean.errors}"
    assert drc_clean.routed_net_count == 2 and drc_clean.unrouted_net_count == 0
    assert drc_clean.unconnected_items == 0 and drc_clean.track_dangling_count == 0

    # 1) ERC must catch floating pin when a pin is omitted from nets
    bad_erc_spec = BoardSpec(
        **{**clean.__dict__, "nets": (NetSpec("GND", (("R1", "1"), ("J1", "2")), is_power=True, has_pwr_flag=True),)}
    )
    sch_bad = write_kicad_sch(bad_erc_spec, tmp_path / "bad_erc.kicad_sch")
    erc_bad = run_erc(sch_bad, bad_erc_spec)
    assert not erc_bad.passed
    assert any("Floating/unconnected pin" in e for e in erc_bad.errors)

    # 2) ERC must catch SCH/PCB parity mismatch if PCB drops a component
    pcb_corrupt = tmp_path / "corrupt.kicad_pcb"
    pcb_corrupt.write_text(pcb.read_text(encoding="utf-8").replace('(property "Reference" "R1"', '(property "Reference" "R99"'), encoding="utf-8")
    erc_par = run_erc(sch, clean, pcb_path=pcb_corrupt)
    assert not erc_par.passed and not erc_par.sch_pcb_parity_ok

    # 3) DRC must catch wrong impedance width (0.15 mm on 0.254 mm RO4350B -> ~92 Ohm >> 50 Ohm ±5%)
    bad_z0_spec = BoardSpec(
        **{
            **clean.__dict__,
            "traces": (
                TraceSpec("SIG50", "F.Cu", ((10.8, 10.0), (20.0, 10.0)), width_mm=0.15),
                clean.traces[1],
            ),
        }
    )
    pcb_z0 = write_kicad_pcb(bad_z0_spec, tmp_path / "bad_z0.kicad_pcb")
    drc_z0 = run_drc(pcb_z0, bad_z0_spec)
    assert not drc_z0.passed
    assert any("Impedance DRC fail" in e for e in drc_z0.errors)

    # 4) DRC must catch trace width violation & via annular-ring violation
    bad_geom_spec = BoardSpec(
        **{
            **clean.__dict__,
            "traces": (
                TraceSpec("SIG50", "F.Cu", ((10.8, 10.0), (20.0, 10.0)), width_mm=0.05),
                clean.traces[1],
            ),
            "vias": (ViaSpec("GND", 9.2, 14.0, diameter_mm=0.32, drill_mm=0.30),),
        }
    )
    pcb_geom = write_kicad_pcb(bad_geom_spec, tmp_path / "bad_geom.kicad_pcb")
    drc_geom = run_drc(pcb_geom, bad_geom_spec)
    assert not drc_geom.passed
    assert any("width" in e for e in drc_geom.errors)
    assert any("annular ring" in e for e in drc_geom.errors)

    # 5) DRC must catch an UNROUTED multi-pin net (unconnected_items > 0) AND auto_route_board fixes it!
    unrouted_spec = BoardSpec(**{**clean.__dict__, "traces": (clean.traces[0],)})  # GND unrouted!
    pcb_unr = write_kicad_pcb(unrouted_spec, tmp_path / "unrouted.kicad_pcb")
    drc_unr = run_drc(pcb_unr, unrouted_spec)
    assert not drc_unr.passed
    assert drc_unr.unrouted_net_count == 1 and drc_unr.unconnected_items == 1
    assert any("Unconnected net 'GND'" in e for e in drc_unr.errors)

    # auto_route_board must route the unrouted board to 0 unconnected & 0 dangling & 0 DRC!
    auto_spec = auto_route_board(BoardSpec(**{**clean.__dict__, "traces": ()}), grid_mm=0.50, preserve_existing=False)
    pcb_auto = write_kicad_pcb(auto_spec, tmp_path / "auto.kicad_pcb")
    drc_auto = run_drc(pcb_auto, auto_spec)
    assert drc_auto.passed, f"auto_route_board DRC errors: {drc_auto.errors}"
    assert drc_auto.routed_net_count == 2 and drc_auto.unconnected_items == 0 and drc_auto.track_dangling_count == 0

    # 6) DRC must catch a FLOATING / DANGLING trace stub touching 0 pads!
    dangling_spec = BoardSpec(
        **{
            **clean.__dict__,
            "traces": clean.traces + (TraceSpec("GND", "F.Cu", ((4.0, 4.0), (8.0, 4.0)), width_mm=0.20),),
        }
    )
    pcb_dang = write_kicad_pcb(dangling_spec, tmp_path / "dangling.kicad_pcb")
    drc_dang = run_drc(pcb_dang, dangling_spec)
    assert not drc_dang.passed
    assert drc_dang.track_dangling_count >= 1
    assert any("Dangling/floating trace" in e for e in drc_dang.errors)

    # 7) DRC HV creepage: fails without air-slot, PASSES when milled air-slot lengthens surface path!
    hv_stack = clean.stackup
    hv_c1 = ComponentSpec("R1", "10M_HV", "Resistor_SMD:R_0805_2012Metric", 10.0, 15.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="HV")
    hv_c2 = ComponentSpec("R2", "10k_LV", "Resistor_SMD:R_0805_2012Metric", 20.0, 15.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="LV")
    hv_nets = (
        NetSpec("HV_5KV", (("R1", "1"), ("R1", "2")), voltage_v=5000.0),
        NetSpec("GND", (("R2", "1"), ("R2", "2")), is_power=True, has_pwr_flag=True, voltage_v=0.0),
    )
    hv_traces = (
        TraceSpec("HV_5KV", "F.Cu", ((9.0, 15.0), (11.0, 15.0)), width_mm=0.25),
        TraceSpec("GND", "F.Cu", ((19.0, 15.0), (21.0, 15.0)), width_mm=0.25),
    )
    hv_rule = (CreepageRule("HV_*", working_voltage_v=5000.0, min_clearance_mm=6.0, min_creepage_mm=12.0),)
    # Straight distance between R1 (x=11.475) and R2 (x=18.525) is 7.05 mm: passes 6 mm clearance, FAILS 12 mm creepage!
    hv_noslot = BoardSpec(
        name="hv_ns", title="HV NoSlot", rev="v1", bom_ids=("HV",),
        width_mm=30.0, height_mm=30.0, stackup=hv_stack, components=(hv_c1, hv_c2),
        nets=hv_nets, traces=hv_traces, creepage_rules=hv_rule,
    )
    pcb_ns = write_kicad_pcb(hv_noslot, tmp_path / "hv_ns.kicad_pcb")
    drc_ns = run_drc(pcb_ns, hv_noslot)
    assert not drc_ns.passed
    assert any("HV Creepage/Clearance DRC fail" in e for e in drc_ns.errors)

    # Add a 20 mm tall milled air-slot between R1 and R2 -> forces creepage detour > 20 mm -> PASS!
    hv_slot = BoardSpec(
        **{
            **hv_noslot.__dict__,
            "keepouts": (KeepoutSpec("SLOT1", "air_slot", ("Edge.Cuts",), x_mm=14.5, y_mm=5.0, width_mm=1.5, height_mm=20.0),),
        }
    )
    pcb_sl = write_kicad_pcb(hv_slot, tmp_path / "hv_sl.kicad_pcb")
    drc_sl = run_drc(pcb_sl, hv_slot)
    assert drc_sl.passed, f"Unexpected HV slot DRC errors: {drc_sl.errors}"
    assert drc_sl.hv_checks[0]["measured_creepage_mm"] >= 12.0

    # 8) DRC must catch a >= 1000 V through-board dielectric stress violation on a SEGMENT over a B.Cu GND zone!
    #    5000 V across 0.254 mm Rogers core = 19,685 V/mm > 15,000 V/mm limit!
    hv_seg_stress = BoardSpec(
        **{
            **hv_slot.__dict__,
            "traces": (
                TraceSpec("HV_5KV", "F.Cu", ((9.0, 15.0), (9.0, 4.0), (12.0, 4.0), (11.0, 15.0)), width_mm=0.25),
                TraceSpec("GND", "F.Cu", ((19.0, 15.0), (21.0, 15.0)), width_mm=0.25),
            ),
            # GND zone on B.Cu directly under the HV_5KV segment at (9..12, 4) (NOT under R1 pads at y=15!)
            "zones": (ZoneSpec("GND", "B.Cu", ((8.0, 2.0), (26.0, 2.0), (26.0, 6.0), (8.0, 6.0))),),
        }
    )
    pcb_stress = write_kicad_pcb(hv_seg_stress, tmp_path / "hv_seg_stress.kicad_pcb")
    drc_stress = run_drc(pcb_stress, hv_seg_stress)
    assert not drc_stress.passed
    assert any("Through-board HV dielectric stress on seg:HV_5KV" in e for e in drc_stress.errors)


def test_ngspice_runner_catches_syntax_error_and_mna_matches_rc(tmp_path: Path) -> None:
    bad_cir = tmp_path / "bad.cir"
    bad_cir.write_text("* broken deck\nR1 a b 1k bogus_param=99\n.op\n.end\n", encoding="utf-8")
    res = run_ngspice(bad_cir, workdir=tmp_path)
    assert not res.ok and len(res.errors) >= 1

    # Pure-Python MNA analytical check on RC low-pass (R=1k, C=1/(2*pi*1k*10k) -> f_c = 10 kHz)
    mna = MnaCircuit()
    mna.add_vsource("in", "0", ac=1.0)
    mna.add_resistor("in", "out", 1e3)
    mna.add_capacitor("out", "0", 1.0 / (2.0 * math.pi * 1e3 * 1e4))
    sol = mna.solve_ac([1e4])
    mag = abs(sol["out"][0])
    assert abs(mag - 1.0 / math.sqrt(2.0)) < 1e-6


# ---------------------------------------------------------------------------
# 3. IBIC Cryo Front-End v3 — All 3 Split KiCad 8 Boards (S-expr, ERC=0, DRC=0, 100% Routed)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "builder,min_comps,min_z0_checks,expected_hv_checks,expected_slots",
    [
        (build_cold_csa_board, 120, 8, 1, 0),
        (build_warm_shaper_board, 210, 40, 0, 0),
        (build_hv_bias_guard_board, 35, 5, 1, 1),
    ],
)
def test_ibic_v3_split_boards_strict_sexpr_erc_drc_zero(
    builder, min_comps: int, min_z0_checks: int, expected_hv_checks: int, expected_slots: int
) -> None:
    spec = builder()
    sch_path = IBIC_DIR / f"{spec.name}.kicad_sch"
    pcb_path = IBIC_DIR / f"{spec.name}.kicad_pcb"
    assert sch_path.is_file(), f"Missing {sch_path}"
    assert pcb_path.is_file(), f"Missing {pcb_path}"

    # Strict S-expression validation from disk
    sch_tree = parse_sexpr(sch_path.read_text(encoding="utf-8"))
    pcb_tree = parse_sexpr(pcb_path.read_text(encoding="utf-8"))
    assert sch_tree[0] == "kicad_sch"
    assert pcb_tree[0] == "kicad_pcb"

    # Strict reconstructive ERC + SCH/PCB netlist parity
    erc = run_erc(sch_path, spec, pcb_path=pcb_path)
    assert erc.passed, f"ERC failed on {spec.name}: {erc.errors}"
    assert len(erc.errors) == 0
    assert erc.sch_pcb_parity_ok
    assert erc.component_count >= min_comps

    # Strict geometric PCB DRC + 100% physical routing + 0 dangling + Z0 + HV creepage/clearance
    drc = run_drc(pcb_path, spec)
    assert drc.passed, f"DRC failed on {spec.name}: {drc.errors}"
    assert len(drc.errors) == 0
    assert drc.total_multi_pin_nets > 0
    assert drc.routed_net_count == drc.total_multi_pin_nets
    assert drc.unrouted_net_count == 0
    assert drc.unconnected_items == 0
    assert drc.track_dangling_count == 0
    assert len(drc.impedance_checks) >= min_z0_checks
    assert all(ic["passed"] and ic["error_pct"] <= 5.0 for ic in drc.impedance_checks)
    assert len(drc.hv_checks) == expected_hv_checks
    assert all(hc["passed"] for hc in drc.hv_checks)
    assert drc.air_slot_count == expected_slots


def test_ibic_v3_cold_stray_capacitance_and_architecture_features() -> None:
    cold = build_cold_csa_board()
    guard_traces = [t for t in cold.traces if t.is_guard_ring]
    ko_csa = [k for k in cold.keepouts if k.kind == "copper_keepout"]
    assert len(guard_traces) == 32  # 4 closed 3D guard-cage rails per channel x 8 channels
    assert len(ko_csa) == 8         # In1/In2 cutout under every CSA_SUM node
    stray = compute_cold_stray_c_budget_pf()
    assert stray["within_budget"] and stray["c_pcb_stray_total_pF"] < 0.15

    warm = build_warm_shaper_board()
    ldos = [c for c in warm.components if c.ref.startswith("ULDO_")]
    adc_bufs = [c for c in warm.components if c.value == "ADA4817-1_ADC_BUF"]
    assert len(ldos) == 5
    assert len(adc_bufs) == 8
    assert any(c.ref == "JADC" for c in warm.components)
    assert any(c.ref == "UDAC" and "DAC8568" in c.value for c in warm.components)


# ---------------------------------------------------------------------------
# 4. Live Real ngspice-47 Simulation & Independent Python MNA Cross-Check
# ---------------------------------------------------------------------------

def test_ibic_v3_live_ngspice_100k_and_mna_parity() -> None:
    cir_path = IBIC_DIR / "ibic_cryo_chain_100k.cir"
    assert cir_path.is_file()
    cir_text = cir_path.read_text(encoding="utf-8")

    # Confirm zero legacy PSpice syntax defects & true 100 K / 300 K split temps
    assert "VALUE = {" not in cir_text and "VALUE={" not in cir_text
    assert "PARAMS:" not in cir_text
    assert ".temp -173.15" in cir_text
    assert "temp=26.85" in cir_text

    # Execute LIVE real ngspice -b!
    res = run_ngspice(cir_path, workdir=IBIC_DIR)
    assert res.ok, f"ngspice failed: {res.errors}\nstderr={res.stderr}"
    assert res.returncode == 0
    assert len(res.errors) == 0

    m = res.metrics
    v_peak = m["v_peak_5kev"]
    t_peak = m["t_peak_after_hit"]
    v_adc = m["v_adc_peak_5kev"]
    onoise_v = m["ibic_onoise_rms_v"]
    hv_atten_100k = m["hv_atten_100k_db"]
    hv_noise_v = m["hv_onoise_rms_v"]
    z_peak = m["z_peak_ohm"]
    cmp_max = m["cmp_max_v"]
    cmp_pw = m["cmp_t_fall"] - m["cmp_t_rise"]

    enc_e = onoise_v / (v_peak / LINDHARD_5KEV_100K_E)

    # Strict physical & Exp127 contract bounds
    assert 9.5e-3 <= v_peak <= 12.5e-3, f"V_peak out of 10-12 mV band: {v_peak*1e3:.3f} mV"
    assert 1.10e-6 <= t_peak <= 1.35e-6, f"t_peak not ~1.2 us: {t_peak*1e9:.1f} ns"
    assert 18.0 <= enc_e <= 35.0, f"ENC out of Exp127 bound (<=35 e-): {enc_e:.2f} e-"
    assert abs(v_adc - v_peak) / v_peak < 0.02
    assert cmp_max >= 3.0 and cmp_pw > 1.0e-6
    assert hv_atten_100k <= -100.0, f"S3.2-03 HV filter @ 100 kHz failed >100 dB: {hv_atten_100k:.2f} dB"
    assert hv_noise_v < 10.0e-6, f"S3.2-03 HV filter noise >= 10 uVrms: {hv_noise_v*1e6:.3f} uVrms"

    # Independent Python MNA cross-check parity (<1% Z_peak, <0.5 dB HV attenuation)
    mna = run_mna_crosscheck()
    z_diff_pct = abs(z_peak - mna["mna_z_peak_ohm"]) / mna["mna_z_peak_ohm"] * 100.0
    hv_diff_db = abs(hv_atten_100k - mna["mna_hv_atten_100k_db"])
    assert z_diff_pct < 1.0, f"MNA vs ngspice Z_peak diff {z_diff_pct:.3f}%"
    assert hv_diff_db < 0.5, f"MNA vs ngspice HV 100 kHz diff {hv_diff_db:.3f} dB"

    # Verification JSON artifact integrity & epistemic disclosure
    ver_json = json.loads((IBIC_DIR / "ibic_v3_verification.json").read_text(encoding="utf-8"))
    assert ver_json["all_passed"] is True
    assert ver_json["checks"]["all_3_boards_100pct_routed"] is True
    assert ver_json["checks"]["all_3_boards_zero_dangling"] is True
    assert ver_json["epistemic_meta"]["no_lab_measurement"] is True
    assert ver_json["epistemic_meta"]["no_physical_fab"] is True
    assert ver_json["epistemic_meta"]["iec61508_certified"] is False
    assert ver_json["epistemic_meta"]["semi_s2_certified"] is False
