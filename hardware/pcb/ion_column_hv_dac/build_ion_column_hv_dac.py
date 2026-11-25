"""Ion Column HV Precision DAC, 5 kV 1000:1 Divider, 3-Stage Active Ripple Filter & <5 us Trim PCB.

BOM Coverage:
  * Primary custom boards: S1.3-03 (5.000 kV ±0.5 V column HV divider & active ripple filter),
    S2.3-04 (multi-channel mini-lens HV focus supply <2 mVpp), S6.10-04 (M4 20-bit DC dipole gate
    DAC <0.5 uV/rtHz).
  * Direct interfaces: S1.1-05 (15 kV ion source HV deck), S1.2-03 (Wien filter +/-5 kV <5 mVpp),
    S1.5-03 (HDA energy filter <50 mVpp), S4.5-03 (on-the-fly interferometer deflector trim <5 us),
    and rtl/machine_ctrl/spi_dac_hv_ctrl.v (SPI + LDAC_N + HV_CLR_N + HV_SAFE_CLAMP).

Key Design Specs:
  * 4-layer Isola FR408HR (er=3.66, CTI>=600 MG-I), 220 x 150 mm.
  * Milled Edge.Cuts air-slots separating the 5 kV HV filter/divider/clamp bay from the LV 20-bit
    DAC & trim-summer bay (>= 12 mm clearance & creepage @ 5 kV per IEC 61010-1).
  * 4x AD5791BRUZ 20-bit ultra-low-noise SPI DACs (< 0.5 uV/rtHz) with LT6655B-5 + OPA211 +/-10 V
    reference & ADuM1401 digital isolation.
  * Caddock USF370 99.900 MOhm / Vishay Z201 100.00 kOhm compensated 1000:1 HV feedback divider
    (V_land = 5.000 kV +/- 0.5 V, dE/E <= 1e-4).
  * 3-stage RC + active anti-phase ripple cancellation filter (> 80 dB @ 100 kHz, holding 10 Vpp
    HV PSU switching ripple to < 1 mVpp << 2 mVpp mini-lens spec).
  * Fast < 5 us on-the-fly interferometer deflector trim summer (THS4031, 50 Ohm SMA I/O).
  * Hard-wired HV_SAFE_CLAMP zero-clamp (async DAC HV_CLR_N + Gigavac G81C NC HV vacuum relay +
    IXTH1N450HV MOSFET backup dump).

Epistemic Status: M0/M1 DESIGN_ONLY; no_lab_measurement=true; no_physical_fab=true;
iec61508_certified=false; semi_s2_certified=false.
"""
from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from hardware.pcb.kicad_eda_verify import (
    BoardSpec,
    ComponentSpec,
    CreepageRule,
    DEFAULT_EPISTEMIC_META,
    DesignRules,
    KeepoutSpec,
    MnaCircuit,
    NetSpec,
    PinSpec,
    StackupLayer,
    TraceSpec,
    ViaSpec,
    ZoneSpec,
    auto_footprint_pads,
    auto_route_board,
    make_manhattan_trace,
    run_ngspice,
    solve_microstrip_width_mm,
    verify_board_bundle,
)

OUT_DIR = Path(__file__).resolve().parent


def _pad_xy(comp: ComponentSpec, pin_num: str) -> tuple[float, float]:
    rad = math.radians(comp.rotation_deg)
    c, s = math.cos(rad), math.sin(rad)
    for p in comp.pins:
        if p.number == str(pin_num):
            return (
                round(comp.x_mm + p.dx_mm * c + p.dy_mm * s, 4),
                round(comp.y_mm - p.dx_mm * s + p.dy_mm * c, 4),
            )
    raise KeyError(f"Pin {pin_num} not found on {comp.ref}")


def _hv_turret_pin() -> tuple[PinSpec, ...]:
    """Single-terminal 5 kV alumina-standoff HV turret pad."""
    return (PinSpec("1", "HV", "passive", 0.0, 0.0, 2.40, 2.40, drill_mm=1.20),)


def _hv_axial_pins(span_mm: float = 34.0, vertical: bool = False) -> tuple[PinSpec, ...]:
    """Wide-span 5-10 kV HV component footprint (straddling a milled Edge.Cuts air-slot)."""
    half = span_mm * 0.5
    if vertical:
        return (
            PinSpec("1", "HV_A", "passive", 0.0, -half, 2.20, 2.20, drill_mm=1.00),
            PinSpec("2", "HV_B", "passive", 0.0, half, 2.20, 2.20, drill_mm=1.00),
        )
    return (
        PinSpec("1", "HV_A", "passive", -half, 0.0, 2.20, 2.20, drill_mm=1.00),
        PinSpec("2", "HV_B", "passive", half, 0.0, 2.20, 2.20, drill_mm=1.00),
    )


def _hv_relay_nc_pins() -> tuple[PinSpec, ...]:
    """Gigavac G81C-class 10 kV NC vacuum relay: HV contacts at dy=-17 mm, LV coil at dy=+17 mm."""
    return (
        PinSpec("1", "HV_COM", "passive", -4.5, -17.0, 2.40, 2.40, drill_mm=1.20),
        PinSpec("2", "HV_NC", "passive", 4.5, -17.0, 2.40, 2.40, drill_mm=1.20),
        PinSpec("3", "COIL_P", "input", -3.0, 17.0, 1.80, 1.80, drill_mm=0.90),
        PinSpec("4", "COIL_N", "input", 3.0, 17.0, 1.80, 1.80, drill_mm=0.90),
    )


def _hv_mosfet_to247_pins() -> tuple[PinSpec, ...]:
    """IXTH1N450HV 4.5 kV MOSFET (TO-247 wide-pitch 5.45 mm)."""
    return (
        PinSpec("1", "G", "input", -5.45, 0.0, 2.00, 2.00, drill_mm=1.10),
        PinSpec("2", "D", "passive", 0.0, 0.0, 2.00, 2.00, drill_mm=1.10),
        PinSpec("3", "S", "passive", 5.45, 0.0, 2.00, 2.00, drill_mm=1.10),
    )


def _soic8_opamp_pins() -> tuple[PinSpec, ...]:
    names = {"1": "NC1", "2": "IN-", "3": "IN+", "4": "V-", "5": "NC5", "6": "OUT", "7": "V+", "8": "NC8"}
    types = {
        "1": "no_connect", "2": "input", "3": "input", "4": "power_in",
        "5": "no_connect", "6": "output", "7": "power_in", "8": "no_connect",
    }
    return auto_footprint_pads("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", [str(i) for i in range(1, 9)], names, types)


def _ldo_msop10_pins() -> tuple[PinSpec, ...]:
    names = {
        "1": "IN1", "2": "IN2", "3": "EN", "4": "PG", "5": "ILIM",
        "6": "GND", "7": "SET", "8": "OUTS", "9": "OUT1", "10": "OUT2",
    }
    types = {
        "1": "power_in", "2": "power_in", "3": "input", "4": "no_connect", "5": "no_connect",
        "6": "power_in", "7": "input", "8": "input", "9": "power_out", "10": "power_out",
    }
    return auto_footprint_pads("Package_SO:MSOP-10_3x3mm_P0.5mm", [str(i) for i in range(1, 11)], names, types)


def _ad5791_tssop20_pins() -> tuple[PinSpec, ...]:
    """AD5791BRUZ 20-bit +/-10 V ultra-low-noise precision DAC (TSSOP-20)."""
    names = {
        "1": "VOUT", "2": "VREFPS", "3": "VREFPF", "4": "AGND1", "5": "VREFNF",
        "6": "VREFNS", "7": "VDD", "8": "VSS", "9": "SYNC_N", "10": "SCLK",
        "11": "SDIN", "12": "SDO", "13": "LDAC_N", "14": "CLR_N", "15": "RESET_N",
        "16": "DGND", "17": "IOVCC", "18": "VCC_D", "19": "INV_FB", "20": "RFB",
    }
    types = {
        "1": "output", "2": "input", "3": "input", "4": "power_in", "5": "input",
        "6": "input", "7": "power_in", "8": "power_in", "9": "input", "10": "input",
        "11": "input", "12": "no_connect", "13": "input", "14": "input", "15": "input",
        "16": "power_in", "17": "power_in", "18": "power_in", "19": "no_connect", "20": "no_connect",
    }
    return auto_footprint_pads("Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm", [str(i) for i in range(1, 21)], names, types)


def _adum1401_soic16_pins() -> tuple[PinSpec, ...]:
    """ADuM1401BRWZ 4-ch digital isolator (SOIC-16W, 7.6 mm creepage body)."""
    names = {
        "1": "VDD1", "2": "GND1A", "3": "VIA", "4": "VIB", "5": "VIC", "6": "VOD", "7": "VE1", "8": "GND1B",
        "9": "GND2B", "10": "VE2", "11": "VID", "12": "VOC", "13": "VOB", "14": "VOA", "15": "GND2A", "16": "VDD2",
    }
    types = {
        "1": "power_in", "2": "power_in", "3": "input", "4": "input", "5": "input", "6": "no_connect",
        "7": "input", "8": "power_in", "9": "power_in", "10": "input", "11": "no_connect",
        "12": "output", "13": "output", "14": "output", "15": "power_in", "16": "power_in",
    }
    return auto_footprint_pads("Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", [str(i) for i in range(1, 17)], names, types)


def _lt6655_msop8_pins() -> tuple[PinSpec, ...]:
    names = {"1": "GND1", "2": "VIN", "3": "SHDN_N", "4": "GND2", "5": "GND3", "6": "VOUT_F", "7": "VOUT_S", "8": "GND4"}
    types = {
        "1": "power_in", "2": "power_in", "3": "input", "4": "power_in",
        "5": "power_in", "6": "power_out", "7": "input", "8": "power_in",
    }
    return auto_footprint_pads("Package_SO:MSOP-8_3x3mm_P0.65mm", [str(i) for i in range(1, 9)], names, types)


def build_ion_column_hv_dac_board() -> BoardSpec:
    """Build 4-layer Isola FR408HR Ion Column HV DAC + 5 kV Divider + Active Ripple Filter + <5 us Trim PCB."""
    stackup = (
        StackupLayer("F.Cu", "signal", 0.035, material="Copper"),
        StackupLayer("dielectric 1", "prepreg", 0.200, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR"),
        StackupLayer("In1.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 2", "core", 1.100, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR"),
        StackupLayer("In2.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 3", "prepreg", 0.200, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR"),
        StackupLayer("B.Cu", "signal", 0.035, material="Copper"),
    )
    w50 = solve_microstrip_width_mm(50.0, h_mm=0.200, t_mm=0.035, er=3.66)

    comps: list[ComponentSpec] = []
    nets_dict: dict[str, list[tuple[str, str]]] = defaultdict(list)
    traces: list[TraceSpec] = []
    vias: list[ViaSpec] = []

    def add_c(c: ComponentSpec) -> ComponentSpec:
        comps.append(c)
        return c

    def conn(net: str, ref: str, pin: str | int) -> None:
        nets_dict[net].append((ref, str(pin)))

    # =========================================================================
    # ZONE 1 (LEFT, x=10..84 mm, y=14..56 mm): 5 kV HV FILTER, TAPS & CLAMP
    # =========================================================================
    # HV Turret Input (S1.1-05 / S1.3 HV PSU feed) & 4 HV Filtered Output Turrets
    j_hv_in = add_c(ComponentSpec(
        "JHV_5KV_IN", "HV_TURRET_5KV_IN", "Custom:HV_ALUMINA_TURRET_5KV",
        14.0, 22.0, pins=_hv_turret_pin(), mpn="Keystone_1502_Alumina_5kV",
        bom_id="S1.1-05", epistemic_tag="{Pasif-COTS}",
    ))
    j_hv_land = add_c(ComponentSpec(
        "JHV_LAND_OUT", "HV_TURRET_5KV_LANDING", "Custom:HV_ALUMINA_TURRET_5KV",
        72.0, 18.0, pins=_hv_turret_pin(), mpn="Keystone_1502_Alumina_5kV",
        bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    j_hv_mini = add_c(ComponentSpec(
        "JHV_MINILENS", "HV_TURRET_MINILENS_2MVPP", "Custom:HV_ALUMINA_TURRET_5KV",
        82.0, 18.0, pins=_hv_turret_pin(), mpn="Keystone_1502_Alumina_5kV",
        bom_id="S2.3-04", epistemic_tag="{Pasif-COTS}",
    ))
    j_hv_wien = add_c(ComponentSpec(
        "JHV_WIEN", "HV_TURRET_WIEN_5MVPP", "Custom:HV_ALUMINA_TURRET_5KV",
        72.0, 28.0, pins=_hv_turret_pin(), mpn="Keystone_1502_Alumina_5kV",
        bom_id="S1.2-03", epistemic_tag="{Pasif-COTS}",
    ))
    j_hv_hda = add_c(ComponentSpec(
        "JHV_HDA", "HV_TURRET_HDA_50MVPP", "Custom:HV_ALUMINA_TURRET_5KV",
        82.0, 28.0, pins=_hv_turret_pin(), mpn="Keystone_1502_Alumina_5kV",
        bom_id="S1.5-03", epistemic_tag="{Pasif-COTS}",
    ))

    # 3-Stage RC HV Ripple Filter Series Resistors (Ohmite MOX-2 10.0 kOhm 5 kV)
    rhv1 = add_c(ComponentSpec(
        "RHV_F1", "10.0k_5KV_MOX", "Resistor_SMD:R_2512_6332Metric",
        26.0, 36.0, pins=auto_footprint_pads("2512", ("1", "2")),
        mpn="Ohmite_MOX200001002FE", bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    rhv2 = add_c(ComponentSpec(
        "RHV_F2", "10.0k_5KV_MOX", "Resistor_SMD:R_2512_6332Metric",
        42.0, 36.0, pins=auto_footprint_pads("2512", ("1", "2")),
        mpn="Ohmite_MOX200001002FE", bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    rhv3 = add_c(ComponentSpec(
        "RHV_F3", "10.0k_5KV_MOX", "Resistor_SMD:R_2512_6332Metric",
        58.0, 36.0, pins=auto_footprint_pads("2512", ("1", "2")),
        mpn="Ohmite_MOX200001002FE", bom_id="S2.3-04", epistemic_tag="{Pasif-COTS}",
    ))
    # Decoupling isolation resistors to Wien/HDA/Mini-Lens output turrets
    rhv_mini = add_c(ComponentSpec(
        "RHV_MINI", "1.00k_5KV_MOX", "Resistor_SMD:R_2512_6332Metric",
        80.0, 36.0, pins=auto_footprint_pads("2512", ("1", "2")),
        mpn="Ohmite_MOX200001001FE", bom_id="S2.3-04", epistemic_tag="{Pasif-COTS}",
    ))

    # 3-Stage 6 kV Film Filter Capacitors + Active Ripple-Sense Cap
    # All centered at y = 70.0 mm with 34.0 mm vertical lead pitch (pin 1 @ y=53 mm HV, pin 2 @ y=87 mm RTN/LV)
    # straddling the horizontal milled air-slot y=[68..72 mm]!
    chv1 = add_c(ComponentSpec(
        "CHV_F1", "10nF_6KV_FKP1", "Custom:WIMA_FKP1_6KV_P34mm",
        18.0, 70.0, pins=_hv_axial_pins(34.0, vertical=True),
        mpn="WIMA_FKP1Y021007D", bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    chv2 = add_c(ComponentSpec(
        "CHV_F2", "10nF_6KV_FKP1", "Custom:WIMA_FKP1_6KV_P34mm",
        30.0, 70.0, pins=_hv_axial_pins(34.0, vertical=True),
        mpn="WIMA_FKP1Y021007D", bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    chv3 = add_c(ComponentSpec(
        "CHV_F3", "10nF_6KV_FKP1", "Custom:WIMA_FKP1_6KV_P34mm",
        42.0, 70.0, pins=_hv_axial_pins(34.0, vertical=True),
        mpn="WIMA_FKP1Y021007D", bom_id="S2.3-04", epistemic_tag="{Pasif-COTS}",
    ))
    c_rip_s = add_c(ComponentSpec(
        "C_RIP_SENSE", "1.0nF_6KV_C0G", "Custom:WIMA_FKP1_6KV_P34mm",
        52.0, 70.0, pins=_hv_axial_pins(34.0, vertical=True),
        mpn="Vishay_HV_102K6KV", bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))

    # Hard-Wired HV_SAFE_CLAMP: 10 kV NC Vacuum Relay + 500 kOhm HV Dump Resistor + Backup 4.5 kV MOSFET
    k_clamp = add_c(ComponentSpec(
        "K_HV_CLAMP", "GIGAVAC_G81C_10KV_NC", "Custom:HV_VACUUM_RELAY_G81C_P34mm",
        64.0, 70.0, pins=_hv_relay_nc_pins(),
        mpn="Gigavac_G81C245", bom_id="S1.3-03", epistemic_tag="{Aday-COTS}",
    ))
    r_dump = add_c(ComponentSpec(
        "R_CLAMP_DUMP", "500k_10KV_MOX", "Custom:OHMITE_MOX4_10KV_P34mm",
        74.0, 70.0, pins=_hv_axial_pins(34.0, vertical=True),
        mpn="Ohmite_MOX400235003FE", bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    q_clamp = add_c(ComponentSpec(
        "Q_HV_CLAMP", "IXTH1N450HV_4p5KV", "Package_TO_SOT_THT:TO-247-3_Vertical",
        78.0, 108.0, pins=_hv_mosfet_to247_pins(),
        mpn="IXYS_IXTH1N450HV", bom_id="S1.3-03", epistemic_tag="{Aday-COTS}",
    ))
    r_qgate = add_c(ComponentSpec(
        "R_QCLAMP_G", "1.00k_0.1pct", "Resistor_SMD:R_0805_2012Metric",
        68.0, 118.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    r_qpd = add_c(ComponentSpec(
        "R_QCLAMP_PD", "100k_1pct", "Resistor_SMD:R_0805_2012Metric",
        78.0, 118.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    d_kfly = add_c(ComponentSpec(
        "D_CLAMP_FLY", "1N4148WS_FLYBACK", "Diode_SMD:D_0805_2012Metric",
        74.0, 96.0, pins=auto_footprint_pads("0805", ("1", "2"), {"1": "K", "2": "A"}),
        bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))

    # Active Ripple Cancellation Amplifier (Bottom HV-Return Strip, x=26..60 mm, y=102..132 mm)
    # Senses AC ripple via C_RIP_SENSE (y=87) and drives bottom of CHV_F3 in anti-phase!
    u_rip = add_c(ComponentSpec(
        "U_RIP_ACT", "ADA4898-1_RIPPLE_AMP", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        46.0, 106.0, pins=_soic8_opamp_pins(),
        mpn="ADA4898-1YRDZ", bom_id="S1.3-03", epistemic_tag="{Aday-COTS}",
    ))
    r_rip_in = add_c(ComponentSpec(
        "R_RIP_IN", "10.0k_0.1pct", "Resistor_SMD:R_0805_2012Metric",
        58.0, 98.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    r_rip_fb = add_c(ComponentSpec(
        "R_RIP_FB", "100k_0.1pct", "Resistor_SMD:R_0805_2012Metric",
        58.0, 106.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    c_rip_fb = add_c(ComponentSpec(
        "C_RIP_FB", "10pF_C0G", "Capacitor_SMD:C_0805_2012Metric",
        58.0, 114.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    r_rip_inj = add_c(ComponentSpec(
        "R_RIP_INJ", "100R_1pct", "Resistor_SMD:R_0805_2012Metric",
        38.0, 96.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    cd_rip_p = add_c(ComponentSpec("CD_RIP_P", "100nF_50V_C0G", "Capacitor_SMD:C_0805_2012Metric", 34.0, 106.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}"))
    cd_rip_n = add_c(ComponentSpec("CD_RIP_N", "100nF_50V_C0G", "Capacitor_SMD:C_0805_2012Metric", 34.0, 114.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}"))

    # HV Return Ground Terminal Block (bottom left, cleanly >= 35 mm below HV_5KV_*)
    j_hv_rtn = add_c(ComponentSpec(
        "JHV_RTN_BUS", "TERM_4P_HV_RTN_SHIELD", "Connector_PinHeader:HDR_1x4_5.08mm",
        16.0, 126.0, pins=auto_footprint_pads("HDR_1x4_5.08mm", ("1", "2", "3", "4"),
                                              {"1": "HV_RTN1", "2": "HV_RTN2", "3": "HV_SHLD1", "4": "HV_SHLD2"}),
        bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))

    # =========================================================================
    # HV/LV BARRIER STRADDLERS (x=98 mm, straddling vertical air-slot x=[96..100])
    # =========================================================================
    # Precision Caddock USF370 1000:1 HV Feedback Divider Top Leg (99.900 MOhm, 5 kV) + 2 pF Comp Cap
    # Pin 1 @ x=80 mm (HV_5KV_OUT), Pin 2 @ x=116 mm (HV_FB_DIV, 5.000 V): 36 mm pitch!
    r_div_top = add_c(ComponentSpec(
        "R_DIV_HV_TOP", "99.900M_5KV_CADDOCK_0.01pct", "Custom:CADDOCK_USF370_5KV_P36mm",
        98.0, 44.0, pins=_hv_axial_pins(36.0, vertical=False),
        mpn="Caddock_USF370-99.9M-0.01%", bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    c_div_top = add_c(ComponentSpec(
        "C_DIV_HV_TOP", "2.0pF_6KV_C0G_COMP", "Custom:HV_CAP_6KV_P36mm",
        98.0, 54.0, pins=_hv_axial_pins(36.0, vertical=False),
        mpn="Knowles_2225J6K002P0C", bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))

    # =========================================================================
    # ZONE 2 (RIGHT, x=116..214 mm): LV 1000:1 FEEDBACK, 20-BIT DAC BANK, <5 us TRIM
    # =========================================================================
    # 1000:1 Precision Divider Low-Side Leg + Compensation Cap + Zero-Drift Buffer + HV Error Amp
    r_div_bot = add_c(ComponentSpec(
        "R_DIV_BOT", "100.00k_Z201_0.005pct", "Resistor_SMD:R_1206_3216Metric",
        124.0, 44.0, pins=auto_footprint_pads("1206", ("1", "2")),
        mpn="Vishay_Z201_100K_0.005%", bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    c_div_bot = add_c(ComponentSpec(
        "C_DIV_BOT", "1.998nF_C0G_0.5pct", "Capacitor_SMD:C_0805_2012Metric",
        124.0, 54.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    u_fb_buf = add_c(ComponentSpec(
        "U_HV_FB_BUF", "ADA4522-1_FB_BUF", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        136.0, 46.0, pins=_soic8_opamp_pins(),
        mpn="ADA4522-1ARZ", bom_id="S1.3-03", epistemic_tag="{Aday-COTS}",
    ))
    u_hv_err = add_c(ComponentSpec(
        "U_HV_ERR_INT", "OPA211_HV_LOOP_ERR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        152.0, 46.0, pins=_soic8_opamp_pins(),
        mpn="OPA211AID", bom_id="S1.3-03", epistemic_tag="{Aday-COTS}",
    ))
    r_err_fb = add_c(ComponentSpec("R_ERR_FB", "10.0k_0.01pct", "Resistor_SMD:R_0805_2012Metric", 144.0, 38.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}"))
    r_err_ref = add_c(ComponentSpec("R_ERR_REF", "10.0k_0.01pct", "Resistor_SMD:R_0805_2012Metric", 144.0, 54.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}"))
    c_err_int = add_c(ComponentSpec("C_ERR_INT", "100nF_C0G", "Capacitor_SMD:C_0805_2012Metric", 160.0, 38.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}"))
    r_prog_s = add_c(ComponentSpec("R_PROG_50R", "49.9R_0.1pct", "Resistor_SMD:R_0603_1608Metric", 198.0, 46.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}"))
    j_hv_prog = add_c(ComponentSpec(
        "J_HV_PROG_OUT", "SMA_HV_PSU_PROG_OUT", "Connector_Coaxial:SMA_EdgeMount",
        214.0, 46.0, rotation_deg=90.0, edge_mount=True,
        pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "PROG", "2": "GND"}),
        bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))

    # --- Ultra-Low-Noise Power Tree & Precision +/-10 V Reference (Top-Right, y=14..32 mm) ---
    j_pwr = add_c(ComponentSpec(
        "JPWR_LV_IN", "HDR_6P_LV_PWR", "Connector_PinHeader:HDR_1x6_2.54mm",
        120.0, 18.0, rotation_deg=90.0,
        pins=auto_footprint_pads("HDR_1x6_2.54mm", ("1", "2", "3", "4", "5", "6"),
                                 {"1": "V_P18", "2": "V_N18", "3": "V_P6", "4": "V_24V_CLAMP", "5": "AGND", "6": "DGND"}),
        bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    r_star_dg = add_c(ComponentSpec("R_STAR_DGND", "0R_STAR_AGND_DGND", "Resistor_SMD:R_0805_2012Metric", 132.0, 14.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}"))
    r_star_hv = add_c(ComponentSpec("R_STAR_HVRTN", "0R_STAR_AGND_HVRTN", "Resistor_SMD:R_0805_2012Metric", 132.0, 22.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}"))

    u_ldo_p15 = add_c(ComponentSpec("U_LDO_P15", "LT3045_P15V", "Package_SO:MSOP-10_3x3mm_P0.5mm", 146.0, 16.0, pins=_ldo_msop10_pins(), mpn="LT3045EDD", bom_id="S2.3-04", epistemic_tag="{Aday-COTS}"))
    u_ldo_n15 = add_c(ComponentSpec("U_LDO_N15", "LT3094_N15V", "Package_SO:MSOP-10_3x3mm_P0.5mm", 158.0, 16.0, pins=_ldo_msop10_pins(), mpn="LT3094EDD", bom_id="S2.3-04", epistemic_tag="{Aday-COTS}"))
    u_ldo_p5 = add_c(ComponentSpec("U_LDO_P5", "LT3045_P5V", "Package_SO:MSOP-10_3x3mm_P0.5mm", 170.0, 16.0, pins=_ldo_msop10_pins(), mpn="LT3045EDD", bom_id="S6.10-04", epistemic_tag="{Aday-COTS}"))
    u_ldo_3v3 = add_c(ComponentSpec("U_LDO_3V3", "ADP7142_P3V3", "Package_SO:MSOP-10_3x3mm_P0.5mm", 182.0, 16.0, pins=_ldo_msop10_pins(), mpn="ADP7142AUJZ-3.3", bom_id="S6.10-04", epistemic_tag="{Aday-COTS}"))

    # LDO SET resistors & output bypass caps
    for idx, (ldo, set_val, rail_in, rail_out, x0) in enumerate((
        (u_ldo_p15, "150k_0.1pct", "V_P18_IN", "V_P15A", 146.0),
        (u_ldo_n15, "150k_0.1pct", "V_N18_IN", "V_N15A", 158.0),
        (u_ldo_p5, "49.9k_0.1pct", "V_P6_IN", "V_P5A", 170.0),
        (u_ldo_3v3, "33.2k_0.1pct", "V_P6_IN", "V_P3V3", 182.0),
    )):
        gnd = "DGND" if rail_out == "V_P3V3" else "AGND"
        rset = add_c(ComponentSpec(f"RSET_LDO{idx}", set_val, "Resistor_SMD:R_0603_1608Metric", x0, 26.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S2.3-04", epistemic_tag="{Pasif-COTS}"))
        cout = add_c(ComponentSpec(f"COUT_LDO{idx}", "10uF_25V_X7R", "Capacitor_SMD:C_0805_2012Metric", x0 + 5.0, 26.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S2.3-04", epistemic_tag="{Pasif-COTS}"))
        conn(rail_in, ldo.ref, 1); conn(rail_in, ldo.ref, 2); conn(rail_in, ldo.ref, 3)
        conn(gnd, ldo.ref, 6)
        conn(f"LDO_SET_{idx}", ldo.ref, 7); conn(f"LDO_SET_{idx}", rset.ref, 1); conn(gnd, rset.ref, 2)
        conn(rail_out, ldo.ref, 8); conn(rail_out, ldo.ref, 9); conn(rail_out, ldo.ref, 10)
        conn(rail_out, cout.ref, 1); conn(gnd, cout.ref, 2)

    # Precision LT6655B-5 + OPA211 +/-10 V Reference Buffers
    u_vref = add_c(ComponentSpec("U_VREF5", "LT6655BHMS8-5", "Package_SO:MSOP-8_3x3mm_P0.65mm", 196.0, 16.0, pins=_lt6655_msop8_pins(), mpn="LT6655BHMS8-5", bom_id="S6.10-04", epistemic_tag="{Aday-COTS}"))
    u_ref_p10 = add_c(ComponentSpec("U_REFP10", "OPA211_REF_P10V", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 174.0, 36.0, pins=_soic8_opamp_pins(), mpn="OPA211AID", bom_id="S6.10-04", epistemic_tag="{Aday-COTS}"))
    u_ref_n10 = add_c(ComponentSpec("U_REFN10", "OPA211_REF_N10V", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 186.0, 36.0, pins=_soic8_opamp_pins(), mpn="OPA211AID", bom_id="S6.10-04", epistemic_tag="{Aday-COTS}"))
    r_rp1 = add_c(ComponentSpec("R_RP1", "10.0k_0.01pct", "Resistor_SMD:R_0603_1608Metric", 196.0, 26.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S6.10-04", epistemic_tag="{Pasif-COTS}"))
    r_rp2 = add_c(ComponentSpec("R_RP2", "10.0k_0.01pct", "Resistor_SMD:R_0603_1608Metric", 204.0, 26.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S6.10-04", epistemic_tag="{Pasif-COTS}"))
    r_rn1 = add_c(ComponentSpec("R_RN1", "10.0k_0.01pct", "Resistor_SMD:R_0603_1608Metric", 196.0, 32.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S6.10-04", epistemic_tag="{Pasif-COTS}"))
    r_rn2 = add_c(ComponentSpec("R_RN2", "10.0k_0.01pct", "Resistor_SMD:R_0603_1608Metric", 204.0, 32.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S6.10-04", epistemic_tag="{Pasif-COTS}"))

    # --- 4x AD5791BRUZ 20-Bit Ultra-Low-Noise SPI DAC Bank (y=68..108 mm) ---
    j_spi = add_c(ComponentSpec(
        "J_SPI_FPGA", "HDR_2x6_SPI_HV_CTRL", "Connector_PinHeader:HDR_2x6_2.54mm",
        120.0, 126.0, pins=auto_footprint_pads("HDR_2x6_2.54mm", [str(i) for i in range(1, 13)], {
            "1": "SPI_CS_N", "2": "SPI_SCLK", "3": "SPI_MOSI", "4": "SPI_LDAC_N",
            "5": "HV_CLR_N", "6": "HV_SAFE_CLAMP", "7": "V_P3V3", "8": "DGND1",
            "9": "DGND2", "10": "DAC_RST_N", "11": "CLAMP_STATUS", "12": "DGND3",
        }),
        bom_id="S6.10-04", epistemic_tag="{Pasif-COTS}",
    ))
    u_iso1 = add_c(ComponentSpec("U_ISO_SPI1", "ADuM1401BRWZ_SPI", "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", 136.0, 126.0, pins=_adum1401_soic16_pins(), mpn="ADuM1401BRWZ", bom_id="S6.10-04", epistemic_tag="{Aday-COTS}"))
    u_iso2 = add_c(ComponentSpec("U_ISO_CTRL", "ADuM1401BRWZ_CLAMP", "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", 154.0, 126.0, pins=_adum1401_soic16_pins(), mpn="ADuM1401BRWZ", bom_id="S1.3-03", epistemic_tag="{Aday-COTS}"))
    r_cl_stat = add_c(ComponentSpec("R_CLAMP_STAT", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", 130.0, 112.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S1.3-03", epistemic_tag="{Pasif-COTS}"))

    dac_channels = [
        ("DAC0", "S1.3-03", "DAC0_LAND_SET", 128.0, 74.0),
        ("DAC1", "S2.3-04", "DAC1_MINI_SET", 148.0, 74.0),
        ("DAC2", "S1.2-03", "DAC2_WIEN_SET", 168.0, 74.0),
        ("DAC3", "S6.10-04", "DAC3_M4_GATE", 188.0, 74.0),
    ]
    dac_bufs: list[ComponentSpec] = []
    for idx, (tag, bid, out_net, dx, dy) in enumerate(dac_channels):
        udac = add_c(ComponentSpec(
            f"U_{tag}", "AD5791BRUZ_20BIT", "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
            dx, dy, pins=_ad5791_tssop20_pins(), mpn="AD5791BRUZ", bom_id=bid, epistemic_tag="{Aday-COTS}",
        ))
        ubuf = add_c(ComponentSpec(
            f"U_BUF_{idx}", "OPA211_DAC_BUF", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            dx, dy + 18.0, pins=_soic8_opamp_pins(), mpn="OPA211AID", bom_id=bid, epistemic_tag="{Aday-COTS}",
        ))
        dac_bufs.append(ubuf)
        cd_p = add_c(ComponentSpec(f"CD_DAC{idx}P", "100nF_25V_C0G", "Capacitor_SMD:C_0603_1608Metric", dx - 5.0, dy - 10.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))
        cd_n = add_c(ComponentSpec(f"CD_DAC{idx}N", "100nF_25V_C0G", "Capacitor_SMD:C_0603_1608Metric", dx + 5.0, dy - 10.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))
        r_f = add_c(ComponentSpec(f"RF_DAC{idx}", "1.00k_0.1pct", "Resistor_SMD:R_0603_1608Metric", dx - 4.0, dy + 10.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))
        c_f = add_c(ComponentSpec(f"CF_DAC{idx}", "10nF_C0G", "Capacitor_SMD:C_0603_1608Metric", dx + 4.0, dy + 10.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))

        conn(f"DAC{idx}_RAW", udac.ref, 1)
        conn("VREF_P10", udac.ref, 2); conn("VREF_P10", udac.ref, 3)
        conn("AGND", udac.ref, 4)
        conn("VREF_N10", udac.ref, 5); conn("VREF_N10", udac.ref, 6)
        conn("V_P15A", udac.ref, 7); conn("V_N15A", udac.ref, 8)
        conn("ISO_CS_N", udac.ref, 9); conn("ISO_SCLK", udac.ref, 10); conn("ISO_MOSI", udac.ref, 11)
        conn("ISO_LDAC_N", udac.ref, 13); conn("ISO_CLR_N", udac.ref, 14); conn("ISO_RST_N", udac.ref, 15)
        conn("AGND", udac.ref, 16); conn("V_P5A", udac.ref, 17); conn("V_P5A", udac.ref, 18)

        conn(f"DAC{idx}_RAW", r_f.ref, 1); conn(f"DAC{idx}_FILT", r_f.ref, 2)
        conn(f"DAC{idx}_FILT", c_f.ref, 1); conn("AGND", c_f.ref, 2)
        conn(f"DAC{idx}_FILT", ubuf.ref, 3)
        conn(out_net, ubuf.ref, 6); conn(out_net, ubuf.ref, 2)
        conn("V_P15A", ubuf.ref, 7); conn("V_N15A", ubuf.ref, 4)
        conn("V_P15A", cd_p.ref, 1); conn("AGND", cd_p.ref, 2)
        conn("V_N15A", cd_n.ref, 1); conn("AGND", cd_n.ref, 2)

    # M4 20-Bit Cryo Dipole Gate Output (S6.10-04, 50 Ohm SMA) & Wien/HDA Monitor SMA
    r_m4_50 = add_c(ComponentSpec("R_M4_50R", "49.9R_0.1pct", "Resistor_SMD:R_0603_1608Metric", 200.0, 92.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S6.10-04", epistemic_tag="{Pasif-COTS}"))
    j_m4_out = add_c(ComponentSpec(
        "J_M4_DAC_OUT", "SMA_M4_DIPOLE_DAC", "Connector_Coaxial:SMA_EdgeMount",
        214.0, 92.0, rotation_deg=90.0, edge_mount=True,
        pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "M4_OUT", "2": "GND"}),
        bom_id="S6.10-04", epistemic_tag="{Pasif-COTS}",
    ))
    r_wien_50 = add_c(ComponentSpec("R_WIEN_50R", "49.9R_0.1pct", "Resistor_SMD:R_0603_1608Metric", 200.0, 74.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S1.2-03", epistemic_tag="{Pasif-COTS}"))
    j_wien_out = add_c(ComponentSpec(
        "J_WIEN_PROG", "SMA_WIEN_HDA_PROG", "Connector_Coaxial:SMA_EdgeMount",
        214.0, 74.0, rotation_deg=90.0, edge_mount=True,
        pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "WIEN_OUT", "2": "GND"}),
        bom_id="S1.2-03", epistemic_tag="{Pasif-COTS}",
    ))

    # --- Fast <5 us Interferometer Deflector Trim Summer (S4.5-03, Bottom-Right, y=110..136 mm) ---
    j_trim_in = add_c(ComponentSpec(
        "J_TRIM_IN", "SMA_INTERF_TRIM_IN", "Connector_Coaxial:SMA_EdgeMount",
        214.0, 114.0, rotation_deg=90.0, edge_mount=True,
        pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "TRIM_IN", "2": "GND"}),
        bom_id="S4.5-03", epistemic_tag="{Pasif-COTS}",
    ))
    r_trim_term = add_c(ComponentSpec("R_TRIM_TERM", "49.9R_0.1pct", "Resistor_SMD:R_0603_1608Metric", 202.0, 114.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S4.5-03", epistemic_tag="{Pasif-COTS}"))
    r_trim_in = add_c(ComponentSpec("R_TRIM_IN", "1.00k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 192.0, 114.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S4.5-03", epistemic_tag="{Pasif-COTS}"))
    r_trim_dc = add_c(ComponentSpec("R_TRIM_DC", "1.00k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 174.0, 114.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S4.5-03", epistemic_tag="{Pasif-COTS}"))
    u_trim = add_c(ComponentSpec("U_TRIM_SUM", "THS4031_FAST_SUMMER", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 182.0, 126.0, pins=_soic8_opamp_pins(), mpn="THS4031ID", bom_id="S4.5-03", epistemic_tag="{Aday-COTS}"))
    r_trim_fb = add_c(ComponentSpec("R_TRIM_FB", "1.00k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 192.0, 124.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S4.5-03", epistemic_tag="{Pasif-COTS}"))
    c_trim_fb = add_c(ComponentSpec("C_TRIM_FB", "330pF_C0G", "Capacitor_SMD:C_0603_1608Metric", 192.0, 130.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S4.5-03", epistemic_tag="{Pasif-COTS}"))
    r_trim_out = add_c(ComponentSpec("R_TRIM_50R", "49.9R_0.1pct", "Resistor_SMD:R_0603_1608Metric", 202.0, 132.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S4.5-03", epistemic_tag="{Pasif-COTS}"))
    j_trim_out = add_c(ComponentSpec(
        "J_DEFL_TRIM_OUT", "SMA_DEFL_TRIM_OUT", "Connector_Coaxial:SMA_EdgeMount",
        214.0, 132.0, rotation_deg=90.0, edge_mount=True,
        pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "DEFL_OUT", "2": "GND"}),
        bom_id="S4.5-03", epistemic_tag="{Pasif-COTS}",
    ))

    # =========================================================================
    # NETLIST CONNECTIONS
    # =========================================================================
    # 5 kV HV Filter Chain & Outputs (all named HV_5KV_* -> CreepageRule checked!)
    conn("HV_5KV_IN", j_hv_in.ref, 1); conn("HV_5KV_IN", rhv1.ref, 1)
    conn("HV_5KV_S1", rhv1.ref, 2); conn("HV_5KV_S1", chv1.ref, 1); conn("HV_5KV_S1", rhv2.ref, 1)
    conn("HV_5KV_S2", rhv2.ref, 2); conn("HV_5KV_S2", chv2.ref, 1); conn("HV_5KV_S2", rhv3.ref, 1)
    conn("HV_5KV_OUT", rhv3.ref, 2); conn("HV_5KV_OUT", chv3.ref, 1); conn("HV_5KV_OUT", c_rip_s.ref, 1)
    conn("HV_5KV_OUT", j_hv_land.ref, 1); conn("HV_5KV_OUT", j_hv_wien.ref, 1); conn("HV_5KV_OUT", j_hv_hda.ref, 1)
    conn("HV_5KV_OUT", rhv_mini.ref, 1); conn("HV_5KV_OUT", k_clamp.ref, 1)
    conn("HV_5KV_OUT", r_div_top.ref, 1); conn("HV_5KV_OUT", c_div_top.ref, 1)
    conn("HV_5KV_MINILENS", rhv_mini.ref, 2); conn("HV_5KV_MINILENS", j_hv_mini.ref, 1)
    conn("HV_5KV_CLAMP_NODE", k_clamp.ref, 2); conn("HV_5KV_CLAMP_NODE", r_dump.ref, 1)

    # HV Return & Active Ripple Cancellation
    conn("HV_RTN", chv1.ref, 2); conn("HV_RTN", chv2.ref, 2)
    conn("HV_RTN", j_hv_rtn.ref, 1); conn("HV_RTN", j_hv_rtn.ref, 2)
    conn("HV_RTN", j_hv_rtn.ref, 3); conn("HV_RTN", j_hv_rtn.ref, 4)
    conn("HV_RTN", q_clamp.ref, 3); conn("HV_RTN", r_qpd.ref, 2)
    conn("HV_RTN", r_star_hv.ref, 2); conn("AGND", r_star_hv.ref, 1)

    conn("RIP_SENSE_LV", c_rip_s.ref, 2); conn("RIP_SENSE_LV", r_rip_in.ref, 1)
    conn("RIP_AMP_INN", r_rip_in.ref, 2); conn("RIP_AMP_INN", u_rip.ref, 2)
    conn("RIP_AMP_INN", r_rip_fb.ref, 1); conn("RIP_AMP_INN", c_rip_fb.ref, 1)
    conn("AGND", u_rip.ref, 3)
    conn("RIP_AMP_OUT", u_rip.ref, 6); conn("RIP_AMP_OUT", r_rip_fb.ref, 2); conn("RIP_AMP_OUT", c_rip_fb.ref, 2)
    conn("RIP_AMP_OUT", r_rip_inj.ref, 1)
    conn("RIP_INJ_NODE", r_rip_inj.ref, 2); conn("RIP_INJ_NODE", chv3.ref, 2)
    conn("V_P15A", u_rip.ref, 7); conn("V_N15A", u_rip.ref, 4)
    conn("V_P15A", cd_rip_p.ref, 1); conn("AGND", cd_rip_p.ref, 2)
    conn("V_N15A", cd_rip_n.ref, 1); conn("AGND", cd_rip_n.ref, 2)

    # HV Clamp Control (Relay Coil + MOSFET Backup)
    conn("HV_CLAMP_DRAIN", r_dump.ref, 2); conn("HV_CLAMP_DRAIN", q_clamp.ref, 2)
    conn("HV_CLAMP_GATE", q_clamp.ref, 1); conn("HV_CLAMP_GATE", r_qgate.ref, 2); conn("HV_CLAMP_GATE", r_qpd.ref, 1)
    conn("ISO_CLAMP_DRV", r_qgate.ref, 1); conn("ISO_CLAMP_DRV", u_iso2.ref, 12)
    conn("V_24V_CLAMP", k_clamp.ref, 3); conn("V_24V_CLAMP", d_kfly.ref, 1)
    conn("CLAMP_COIL_N", k_clamp.ref, 4); conn("CLAMP_COIL_N", d_kfly.ref, 2); conn("CLAMP_COIL_N", r_cl_stat.ref, 1)
    conn("CLAMP_STATUS", r_cl_stat.ref, 2); conn("CLAMP_STATUS", j_spi.ref, 11)

    # 1000:1 Divider Feedback & HV Loop Error Amp
    conn("HV_FB_DIV", r_div_top.ref, 2); conn("HV_FB_DIV", c_div_top.ref, 2)
    conn("HV_FB_DIV", r_div_bot.ref, 1); conn("HV_FB_DIV", c_div_bot.ref, 1)
    conn("HV_FB_DIV", u_fb_buf.ref, 3)
    conn("AGND", r_div_bot.ref, 2); conn("AGND", c_div_bot.ref, 2)
    conn("HV_FB_BUF", u_fb_buf.ref, 6); conn("HV_FB_BUF", u_fb_buf.ref, 2); conn("HV_FB_BUF", r_err_fb.ref, 1)
    conn("V_P15A", u_fb_buf.ref, 7); conn("V_N15A", u_fb_buf.ref, 4)

    conn("HV_ERR_SUM", r_err_fb.ref, 2); conn("HV_ERR_SUM", u_hv_err.ref, 2); conn("HV_ERR_SUM", c_err_int.ref, 1)
    conn("DAC0_LAND_SET", r_err_ref.ref, 1); conn("HV_ERR_REF", r_err_ref.ref, 2); conn("HV_ERR_REF", u_hv_err.ref, 3)
    conn("HV_ERR_OUT", u_hv_err.ref, 6); conn("HV_ERR_OUT", c_err_int.ref, 2); conn("HV_ERR_OUT", r_prog_s.ref, 1)
    conn("V_P15A", u_hv_err.ref, 7); conn("V_N15A", u_hv_err.ref, 4)
    conn("HV_PROG_50", r_prog_s.ref, 2); conn("HV_PROG_50", j_hv_prog.ref, 1); conn("AGND", j_hv_prog.ref, 2)

    # LV Power & Star Ground
    conn("V_P18_IN", j_pwr.ref, 1); conn("V_N18_IN", j_pwr.ref, 2); conn("V_P6_IN", j_pwr.ref, 3)
    conn("V_24V_CLAMP", j_pwr.ref, 4); conn("AGND", j_pwr.ref, 5); conn("DGND", j_pwr.ref, 6)
    conn("AGND", r_star_dg.ref, 1); conn("DGND", r_star_dg.ref, 2)

    # Precision +/-10 V Reference Chain
    conn("V_P15A", u_vref.ref, 2); conn("V_P15A", u_vref.ref, 3)
    for p in (1, 4, 5, 8):
        conn("AGND", u_vref.ref, p)
    conn("VREF_5V", u_vref.ref, 6); conn("VREF_5V", u_vref.ref, 7); conn("VREF_5V", u_ref_p10.ref, 3)
    conn("VREF_P10_FB", u_ref_p10.ref, 2); conn("VREF_P10_FB", r_rp1.ref, 1); conn("VREF_P10_FB", r_rp2.ref, 1)
    conn("AGND", r_rp1.ref, 2); conn("VREF_P10", r_rp2.ref, 2); conn("VREF_P10", u_ref_p10.ref, 6)
    conn("V_P15A", u_ref_p10.ref, 7); conn("V_N15A", u_ref_p10.ref, 4)

    conn("VREF_P10", r_rn1.ref, 1); conn("VREF_N10_FB", r_rn1.ref, 2); conn("VREF_N10_FB", r_rn2.ref, 1)
    conn("VREF_N10_FB", u_ref_n10.ref, 2); conn("AGND", u_ref_n10.ref, 3)
    conn("VREF_N10", r_rn2.ref, 2); conn("VREF_N10", u_ref_n10.ref, 6)
    conn("V_P15A", u_ref_n10.ref, 7); conn("V_N15A", u_ref_n10.ref, 4)

    # SPI Digital Isolation (matching rtl/machine_ctrl/spi_dac_hv_ctrl.v)
    conn("SPI_CS_N", j_spi.ref, 1); conn("SPI_SCLK", j_spi.ref, 2); conn("SPI_MOSI", j_spi.ref, 3)
    conn("SPI_LDAC_N", j_spi.ref, 4); conn("HV_CLR_N", j_spi.ref, 5); conn("HV_SAFE_CLAMP", j_spi.ref, 6)
    conn("V_P3V3", j_spi.ref, 7); conn("DGND", j_spi.ref, 8); conn("DGND", j_spi.ref, 9)
    conn("DAC_RST_N", j_spi.ref, 10); conn("DGND", j_spi.ref, 12)

    conn("V_P3V3", u_iso1.ref, 1); conn("V_P3V3", u_iso1.ref, 7)
    conn("DGND", u_iso1.ref, 2); conn("DGND", u_iso1.ref, 8)
    conn("SPI_CS_N", u_iso1.ref, 3); conn("SPI_SCLK", u_iso1.ref, 4); conn("SPI_MOSI", u_iso1.ref, 5)
    conn("AGND", u_iso1.ref, 9); conn("AGND", u_iso1.ref, 15)
    conn("V_P5A", u_iso1.ref, 10); conn("V_P5A", u_iso1.ref, 16)
    conn("ISO_CS_N", u_iso1.ref, 14); conn("ISO_SCLK", u_iso1.ref, 13); conn("ISO_MOSI", u_iso1.ref, 12)

    conn("V_P3V3", u_iso2.ref, 1); conn("V_P3V3", u_iso2.ref, 7)
    conn("DGND", u_iso2.ref, 2); conn("DGND", u_iso2.ref, 8)
    conn("SPI_LDAC_N", u_iso2.ref, 3); conn("HV_CLR_N", u_iso2.ref, 4); conn("HV_SAFE_CLAMP", u_iso2.ref, 5)
    conn("AGND", u_iso2.ref, 9); conn("AGND", u_iso2.ref, 15)
    conn("V_P5A", u_iso2.ref, 10); conn("V_P5A", u_iso2.ref, 16)
    conn("ISO_LDAC_N", u_iso2.ref, 14); conn("ISO_CLR_N", u_iso2.ref, 13)
    # Reset tied high to V_P5A via DAC_RST_N pullup resistor
    r_rst_pu = add_c(ComponentSpec("R_RST_PU", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", 162.0, 114.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S6.10-04", epistemic_tag="{Pasif-COTS}"))
    conn("DAC_RST_N", r_rst_pu.ref, 1); conn("ISO_RST_N", r_rst_pu.ref, 2)

    # DAC2 (Wien/HDA) & DAC3 (M4 Cryo Dipole Gate) 50 Ohm SMA Outputs
    conn("DAC2_WIEN_SET", r_wien_50.ref, 1); conn("WIEN_PROG_50", r_wien_50.ref, 2)
    conn("WIEN_PROG_50", j_wien_out.ref, 1); conn("AGND", j_wien_out.ref, 2)
    conn("DAC3_M4_GATE", r_m4_50.ref, 1); conn("M4_GATE_50", r_m4_50.ref, 2)
    conn("M4_GATE_50", j_m4_out.ref, 1); conn("AGND", j_m4_out.ref, 2)

    # Fast <5 us Interferometer Deflector Trim Summer (S4.5-03)
    conn("TRIM_IN_50", j_trim_in.ref, 1); conn("AGND", j_trim_in.ref, 2)
    conn("TRIM_IN_50", r_trim_term.ref, 2); conn("AGND", r_trim_term.ref, 1)
    conn("TRIM_IN_50", r_trim_in.ref, 2); conn("TRIM_SUM_NODE", r_trim_in.ref, 1)
    conn("DAC1_MINI_SET", r_trim_dc.ref, 1); conn("TRIM_SUM_NODE", r_trim_dc.ref, 2)
    conn("TRIM_SUM_NODE", u_trim.ref, 2); conn("TRIM_SUM_NODE", r_trim_fb.ref, 1); conn("TRIM_SUM_NODE", c_trim_fb.ref, 1)
    conn("AGND", u_trim.ref, 3)
    conn("TRIM_AMP_OUT", u_trim.ref, 6); conn("TRIM_AMP_OUT", r_trim_fb.ref, 2); conn("TRIM_AMP_OUT", c_trim_fb.ref, 2)
    conn("TRIM_AMP_OUT", r_trim_out.ref, 1)
    conn("DEFL_TRIM_50", r_trim_out.ref, 2); conn("DEFL_TRIM_50", j_trim_out.ref, 1); conn("AGND", j_trim_out.ref, 2)
    conn("V_P15A", u_trim.ref, 7); conn("V_N15A", u_trim.ref, 4)

    # =========================================================================
    # COPPER TRACES (HV 1.0 mm wide, 50 Ohm RF microstrips w50, LV control)
    # =========================================================================
    # HV 5 kV Filter Trunk on F.Cu (strictly inside y=[18..53], x=[14..84])
    traces.append(make_manhattan_trace("HV_5KV_IN", "F.Cu", _pad_xy(j_hv_in, "1"), _pad_xy(rhv1, "1"), width_mm=1.00, mid_y=28.0))
    traces.append(make_manhattan_trace("HV_5KV_S1", "F.Cu", _pad_xy(rhv1, "2"), _pad_xy(rhv2, "1"), width_mm=1.00))
    traces.append(make_manhattan_trace("HV_5KV_S1", "F.Cu", _pad_xy(rhv1, "2"), _pad_xy(chv1, "1"), width_mm=0.80, mid_y=42.0))
    traces.append(make_manhattan_trace("HV_5KV_S2", "F.Cu", _pad_xy(rhv2, "2"), _pad_xy(rhv3, "1"), width_mm=1.00))
    traces.append(make_manhattan_trace("HV_5KV_S2", "F.Cu", _pad_xy(rhv2, "2"), _pad_xy(chv2, "1"), width_mm=0.80, mid_y=45.0))
    traces.append(make_manhattan_trace("HV_5KV_OUT", "F.Cu", _pad_xy(rhv3, "2"), _pad_xy(j_hv_land, "1"), width_mm=1.00, mid_x=66.0))
    traces.append(make_manhattan_trace("HV_5KV_OUT", "F.Cu", _pad_xy(rhv3, "2"), _pad_xy(chv3, "1"), width_mm=0.80, mid_y=48.0))
    traces.append(make_manhattan_trace("HV_5KV_OUT", "F.Cu", _pad_xy(chv3, "1"), _pad_xy(c_rip_s, "1"), width_mm=0.80))
    traces.append(make_manhattan_trace("HV_5KV_OUT", "F.Cu", _pad_xy(c_rip_s, "1"), _pad_xy(k_clamp, "1"), width_mm=0.80))
    traces.append(make_manhattan_trace("HV_5KV_OUT", "F.Cu", _pad_xy(r_div_top, "1"), _pad_xy(c_div_top, "1"), width_mm=0.80))
    traces.append(make_manhattan_trace("HV_5KV_MINILENS", "F.Cu", _pad_xy(rhv_mini, "2"), _pad_xy(j_hv_mini, "1"), width_mm=0.80, mid_x=86.0))
    traces.append(make_manhattan_trace("HV_5KV_CLAMP_NODE", "F.Cu", _pad_xy(k_clamp, "2"), _pad_xy(r_dump, "1"), width_mm=0.80))

    # Controlled-Impedance 50 Ohm Microstrip Traces on F.Cu (LV Bay)
    traces.append(make_manhattan_trace("HV_PROG_50", "F.Cu", _pad_xy(r_prog_s, "2"), _pad_xy(j_hv_prog, "1"), width_mm=w50))
    traces.append(make_manhattan_trace("WIEN_PROG_50", "F.Cu", _pad_xy(r_wien_50, "2"), _pad_xy(j_wien_out, "1"), width_mm=w50))
    traces.append(make_manhattan_trace("M4_GATE_50", "F.Cu", _pad_xy(r_m4_50, "2"), _pad_xy(j_m4_out, "1"), width_mm=w50))
    traces.append(make_manhattan_trace("TRIM_IN_50", "F.Cu", _pad_xy(j_trim_in, "1"), _pad_xy(r_trim_term, "2"), width_mm=w50))
    traces.append(make_manhattan_trace("DEFL_TRIM_50", "F.Cu", _pad_xy(r_trim_out, "2"), _pad_xy(j_trim_out, "1"), width_mm=w50))

    # HV Return Bus on B.Cu (strictly y >= 87 mm)
    traces.append(make_manhattan_trace("HV_RTN", "B.Cu", _pad_xy(chv1, "2"), _pad_xy(chv2, "2"), width_mm=1.00))
    traces.append(make_manhattan_trace("HV_RTN", "B.Cu", _pad_xy(chv1, "2"), _pad_xy(j_hv_rtn, "1"), width_mm=1.00, mid_x=22.0))

    # LV Ground Stitching Vias (strictly in LV bay x >= 118 mm)
    for vx in (122.0, 152.0, 182.0, 206.0):
        vias.append(ViaSpec("AGND", vx, 10.0, diameter_mm=0.70, drill_mm=0.35))
        vias.append(ViaSpec("AGND", vx, 142.0, diameter_mm=0.70, drill_mm=0.35))

    # =========================================================================
    # MILLED EDGE.CUTS HV AIR-SLOTS (>= 12 mm clearance & creepage @ 5 kV!)
    # =========================================================================
    # L-shaped milled Edge.Cuts air-slot barrier enclosing the 5 kV top-left island (x<=86, y<=54):
    # vertical slot x=[96..100], y=[8..82] + horizontal slot x=[10..90], y=[68..72];
    # leaves y=[86..146] open for LV return/clamp/ripple-amp routing (>30 mm below 5 kV!).
    keepouts = (
        KeepoutSpec("HV_LV_MAIN_AIR_SLOT", "air_slot", ("Edge.Cuts",), x_mm=96.0, y_mm=8.0, width_mm=4.0, height_mm=74.0),
        KeepoutSpec("HV_HOT_RTN_AIR_SLOT", "air_slot", ("Edge.Cuts",), x_mm=10.0, y_mm=68.0, width_mm=80.0, height_mm=4.0),
    )

    # LV Planes strictly in LV bay (x >= 114 mm -> >= 25 mm clearance from HV_5KV_* & zero through-board overlap!)
    zones = (
        ZoneSpec("AGND", "In1.Cu", ((114.0, 4.0), (216.0, 4.0), (216.0, 146.0), (114.0, 146.0))),
        ZoneSpec("V_P15A", "In2.Cu", ((114.0, 4.0), (216.0, 4.0), (216.0, 72.0), (114.0, 72.0))),
        ZoneSpec("V_N15A", "In2.Cu", ((114.0, 76.0), (216.0, 76.0), (216.0, 146.0), (114.0, 146.0))),
    )

    # Assemble Nets with exact voltages, power flags, and 50 Ohm Z0 constraints
    rf50_nets = {"HV_PROG_50", "WIEN_PROG_50", "M4_GATE_50", "TRIM_IN_50", "DEFL_TRIM_50"}
    pwr_nets = {
        "HV_5KV_IN", "V_P18_IN", "V_N18_IN", "V_P6_IN", "V_24V_CLAMP",
        "V_P15A", "V_N15A", "V_P5A", "V_P3V3", "VREF_5V", "AGND", "DGND", "HV_RTN",
    }
    flag_nets = {"HV_5KV_IN", "V_P18_IN", "V_N18_IN", "V_P6_IN", "V_24V_CLAMP", "AGND", "DGND", "HV_RTN"}

    nets: list[NetSpec] = []
    for nname, nodes in sorted(nets_dict.items()):
        v_work = 5000.0 if nname.startswith("HV_5KV_") else (
            24.0 if nname == "V_24V_CLAMP" else (
                18.0 if nname in ("V_P18_IN", "V_N18_IN") else (
                    15.0 if nname in ("V_P15A", "V_N15A") else 5.0 if "5" in nname else 0.0
                )
            )
        )
        z0 = 50.0 if nname in rf50_nets else None
        is_pwr = nname in pwr_nets
        nets.append(NetSpec(
            name=nname,
            nodes=tuple(nodes),
            net_class="HV_5KV" if v_work >= 1000.0 else ("RF_50" if z0 else ("Power" if is_pwr else "Default")),
            is_power=is_pwr,
            has_pwr_flag=(nname in flag_nets),
            voltage_v=v_work,
            target_z0_ohm=z0,
        ))

    creepage_rules = (
        CreepageRule(
            net_pattern="HV_5KV_*",
            working_voltage_v=5000.0,
            min_clearance_mm=12.0,
            min_creepage_mm=16.0,
            standard="IEC 61010-1 / IPC-2221B (5 kV MG-I)",
            pollution_degree=2,
            material_group="I",
        ),
    )

    spec = BoardSpec(
        name="ion_column_hv_dac",
        title="Ion Column 20-Bit HV DAC, 5 kV 1000:1 Divider, 3-Stage Active Ripple Filter & <5 us Trim PCB",
        rev="v1.0",
        bom_ids=("S1.3-03", "S2.3-04", "S6.10-04", "S1.1-05", "S1.2-03", "S1.5-03", "S4.5-03"),
        width_mm=220.0,
        height_mm=150.0,
        stackup=stackup,
        components=tuple(comps),
        nets=tuple(nets),
        traces=tuple(traces),
        vias=tuple(vias),
        zones=zones,
        keepouts=keepouts,
        creepage_rules=creepage_rules,
        rules=DesignRules(min_trace_width_mm=0.127, min_clearance_mm=0.127, min_edge_clearance_mm=0.50),
        epistemic_meta={
            **DEFAULT_EPISTEMIC_META,
            "operating_temp_K": 300.0,
            "hv_rating_V": 5000.0,
            "dac_resolution_bits": 20,
            "rtl_interface": "rtl/machine_ctrl/spi_dac_hv_ctrl.v",
        },
    )
    return auto_route_board(spec, grid_mm=0.50, preserve_existing=True)


def render_ion_hv_ngspice_deck() -> str:
    """Native ngspice-47 deck verifying 3-stage active/RC HV ripple filter, 1000:1 divider, <5 us trim & M4 noise."""
    return """* Atom Lithography Machine - Ion Column HV DAC, 5 kV Filter, 1000:1 Divider & <5 us Trim
* BOM: S1.3-03, S2.3-04, S6.10-04, S1.1-05, S1.2-03, S1.5-03, S4.5-03
* Epistemic status: M0/M1 DESIGN_ONLY; no_lab_measurement=true; no_physical_fab=true.

.temp 26.85
.options reltol=1e-4 vntol=1e-6 abstol=1e-12

* --- High-Speed Low-Noise Op-Amp Macromodel (THS4031 / ADA4898-1: A0=1e5, GBP=100 MHz, en=1.1 nV/rtHz) ---
.subckt OPAMP_FAST_LN inp inn out
Cin inp inn 2.0p
Rin inp inn 100Meg noisy=0
Rnw nw 0 73.033 temp=26.85
Evn inp_i inp nw 0 1.0
Egain n1 0 inp_i inn 1e5
Rp n1 n2 1k noisy=0
Cp n2 0 159.155n
Ebuf n_out 0 n2 0 1.0
Rout n_out out 5 noisy=0
.ends OPAMP_FAST_LN

* --- Precision Zero-Drift Op-Amp (OPA211 / ADA4522-1: A0=1e6, GBP=45 MHz, en=1.1 nV/rtHz) ---
.subckt OPAMP_PREC inp inn out
Cin inp inn 3.0p
Rin inp inn 1G noisy=0
Rnw nw 0 73.033 temp=26.85
Evn inp_i inp nw 0 1.0
Egain n1 0 inp_i inn 1e6
Rp n1 n2 1k noisy=0
Cp n2 0 3.5368u
Ebuf n_out 0 n2 0 1.0
Rout n_out out 10 noisy=0
.ends OPAMP_PREC

* =========================================================================
* 1) 5.000 kV 3-STAGE RC + ACTIVE ANTI-PHASE RIPPLE FILTER & 1000:1 DIVIDER
* =========================================================================
* 5000.000 V DC + 10 Vpp (5.0 Vpk) 100 kHz HV PSU switching ripple + AC=1 stimulus
* Compensated DC supply (5001.500 V) accounts for 30 kOhm * 50 uA = 1.500 V divider drop
* (which the closed-loop HV error amplifier regulates out at hv_out = 5000.000 V).
Vhv_psu hv_in 0 DC 5001.500 AC 1 SIN(5001.500 5.0 100k 0 0)

* Stage 1..3 RC (3 x 10 kOhm 5 kV MOX + 3 x 10 nF 6 kV WIMA FKP1 w/ 50 mOhm ESR & 15 nH ESL)
Rhv1 hv_in hv_s1 10k
Chv1 hv_s1 c1_esr 10n
Resr1 c1_esr c1_esl 50m
Lesl1 c1_esl 0 15n

Rhv2 hv_s1 hv_s2 10k
Chv2 hv_s2 c2_esr 10n
Resr2 c2_esr c2_esl 50m
Lesl2 c2_esl 0 15n

Rhv3 hv_s2 hv_out 10k
Chv3 hv_out c3_esr 10n
Resr3 c3_esr c3_esl 50m
Lesl3 c3_esl rip_inj 15n

* Closed-loop active anti-phase ripple cancellation stage:
* Senses residual AC ripple directly on hv_out via 1.0 nF 6 kV cap and drives bottom of Chv3
* in negative feedback (G = -10 at 100 kHz -> adds >20 dB rejection on top of passive -107.9 dB!).
Crip_s hv_out rip_s_ac 1.0n
Rrip_g rip_s_ac 0 10Meg
Rrip_in rip_s_ac rip_inn 10.0k
Rrip_fb rip_amp rip_inn 100k
Crip_fb rip_amp rip_inn 10p
Xrip 0 rip_inn rip_amp OPAMP_FAST_LN
Rrip_inj rip_amp rip_inj 100
Rrip_dc  rip_inj 0       100k

* Precision Caddock USF370 1000:1 Compensated HV Feedback Divider (99.900 MOhm / 100.00 kOhm)
* Ratio = 100k / (99.9M + 100k) = 1.000000e-3 exact!
Rdiv_top hv_out hv_fb 99.9Meg
Cdiv_top hv_out hv_fb 2.0p
Rdiv_bot hv_fb  0     100k
Cdiv_bot hv_fb  0     1.998n
Xfb_buf  hv_fb  hv_fb_buf hv_fb_buf OPAMP_PREC
Rfb_load hv_fb_buf 0 1Meg

* High-impedance buffered AC-coupled ripple measurement probe (ZERO loading on hv_out)
Erip_prb hv_prb_buf 0 hv_out 0 1.0
Crip_prb hv_prb_buf hv_rip_ac 100n
Rrip_prb hv_rip_ac  0         10Meg

* Separate passive-only 3-stage reference branch for exact AC comparison (zero active boost)
Vhv_ref  hv_ref_in 0 DC 5001.500 AC 1
Rhv1p hv_ref_in hv_p1 10k
Chv1p hv_p1     cp1   10n
Resr1p cp1      lp1   50m
Lesl1p lp1      0     15n
Rhv2p hv_p1     hv_p2 10k
Chv2p hv_p2     cp2   10n
Resr2p cp2      lp2   50m
Lesl2p lp2      0     15n
Rhv3p hv_p2     hv_p3 10k
Chv3p hv_p3     cp3   10n
Resr3p cp3      lp3   50m
Lesl3p lp3      0     15n
Rloadp hv_p3    0     100Meg

* =========================================================================
* 2) FAST < 5 us ON-THE-FLY INTERFEROMETER DEFLECTOR TRIM SUMMER (S4.5-03)
* =========================================================================
* 50 Ohm source stepping 0 -> +2.0 V (1.0 V at terminated 50 Ohm input) at t=2 us (single-shot)
Vtrim_src trim_src 0 DC 0 PULSE(0 2.0 2u 50n 50n 10m 20m)
Rtrim_src trim_src trim_in 49.9
Rtrim_trm trim_in  0       49.9
* Static 20-bit DAC DC offset = -2.500 V (inverted by summer to +2.500 V baseline)
Vdac_dc   dac_dc   0 DC -2.500
Rtrim_in  trim_in  trim_sum 1.0k
Rtrim_dc  dac_dc   trim_sum 1.0k
Rtrim_fb  trim_amp trim_sum 1.0k
Ctrim_fb  trim_amp trim_sum 330p
Xtrim     0        trim_sum trim_amp OPAMP_FAST_LN
Rtrim_out trim_amp defl_out 49.9
Rdefl_ld  defl_out 0        10k

* =========================================================================
* 3) M4 20-BIT ULTRA-LOW-NOISE DC DIPOLE GATE DAC CHANNEL (S6.10-04)
* =========================================================================
* AD5791 output noise modeled as 7.5 nV/rtHz white source (R_eq = 3.395 kOhm @ 300 K)
Rm4_dac  m4_dac_n 0 3395.1 temp=26.85
Em4_src  m4_raw   0 m4_dac_n 0 1.0
Vm4_ac   m4_in    m4_raw DC 0 AC 1
Rm4_f    m4_in    m4_filt 1.0k
Cm4_f    m4_filt  0       10n
Xm4_buf  m4_filt  m4_out  m4_out OPAMP_PREC
Rm4_load m4_out   0       10k

.control
set noaskquit

* 1) DC Operating Point: Verify 1000:1 HV feedback divider accuracy
op
let hv_dc_v = v(hv_out)
let hv_fb_dc_v = v(hv_fb_buf)
let hv_div_ratio = hv_dc_v / hv_fb_dc_v
let hv_div_err_ppm = abs(hv_div_ratio - 1000.0) / 1000.0 * 1e6
print hv_dc_v hv_fb_dc_v hv_div_ratio hv_div_err_ppm

* 2) AC Analysis: 3-stage HV ripple rejection at 100 kHz & divider AC ratio
ac dec 100 1 10Meg
meas ac hv_atten_100k_db FIND vdb(hv_out) AT=100k
meas ac hv_passive_100k_db FIND vdb(hv_p3) AT=100k
meas ac hv_atten_10k_db  FIND vdb(hv_out) AT=10k
meas ac div_ac_10k_db    FIND vdb(hv_fb_buf) AT=10k

* 3) Transient A: Fast < 5 us Deflector Trim Summer Step Response (t=0..15 us)
tran 10n 15u 0 10n
meas tran trim_v_init  FIND v(defl_out) AT=1.5u
meas tran trim_v_final FIND v(defl_out) AT=14.5u
let v10_thr = trim_v_init + 0.10 * (trim_v_final - trim_v_init)
let v90_thr = trim_v_init + 0.90 * (trim_v_final - trim_v_init)
let v99_thr = trim_v_init + 0.99 * (trim_v_final - trim_v_init)
meas tran trim_t10 WHEN v(defl_out)=$&v10_thr FALL=1
meas tran trim_t90 WHEN v(defl_out)=$&v90_thr FALL=1
meas tran trim_t99 WHEN v(defl_out)=$&v99_thr FALL=1
let trim_rise_10_90_s = trim_t90 - trim_t10
let trim_settle_1pct_s = trim_t99 - 2.0u
print trim_rise_10_90_s trim_settle_1pct_s

* 4) Transient B: Steady-state 5.000 kV + 10 Vpp 100 kHz switching ripple (after 1.5 ms settle)
tran 250n 1.6m 1.5m 250n
meas tran hv_out_dc_chk AVG v(hv_out) FROM=1.52m TO=1.60m
meas tran hv_ac_max MAX v(hv_rip_ac) FROM=1.52m TO=1.60m
meas tran hv_ac_min MIN v(hv_rip_ac) FROM=1.52m TO=1.60m
let hv_ripple_vpp = hv_ac_max - hv_ac_min
print hv_ripple_vpp

* 5) Noise Analysis: M4 20-bit DC dipole gate output noise PSD @ 1 kHz (< 0.5 uV/rtHz)
* dec 30 from 10 Hz -> index 0=10 Hz, 30=100 Hz, 60=1000 Hz
noise v(m4_out) Vm4_ac dec 30 10 1Meg
let m4_onoise_rms_v = onoise_total
print m4_onoise_rms_v
setplot previous
let m4_noise_freq_chk = frequency[60]
let m4_noise_1khz_v_rthz = onoise_spectrum[60]
print m4_noise_freq_chk m4_noise_1khz_v_rthz

quit 0
.endc
.end
"""


def run_mna_crosscheck() -> dict[str, float]:
    """Independent pure-Python MNA check of passive 3-stage HV filter @ 100 kHz & 1000:1 divider."""
    c = MnaCircuit()
    c.add_vsource("hv_in", "0", dc=5001.5, ac=1.0)
    c.add_resistor("hv_in", "s1", 10e3)
    c.add_capacitor("s1", "c1", 10e-9); c.add_resistor("c1", "l1", 0.05); c.add_inductor("l1", "0", 15e-9)
    c.add_resistor("s1", "s2", 10e3)
    c.add_capacitor("s2", "c2", 10e-9); c.add_resistor("c2", "l2", 0.05); c.add_inductor("l2", "0", 15e-9)
    c.add_resistor("s2", "s3", 10e3)
    c.add_capacitor("s3", "c3", 10e-9); c.add_resistor("c3", "l3", 0.05); c.add_inductor("l3", "0", 15e-9)
    c.add_resistor("s3", "fb", 99.9e6); c.add_capacitor("s3", "fb", 2.0e-12)
    c.add_resistor("fb", "0", 100e3); c.add_capacitor("fb", "0", 1.998e-9)

    dc = c.solve_dc()
    ac = c.solve_ac([100e3])
    atten_100k_db = float(20.0 * math.log10(abs(ac["s3"][0])))
    div_ratio = float(dc["s3"] / dc["fb"])
    return {
        "mna_passive_hv_atten_100k_db": round(atten_100k_db, 4),
        "mna_hv_dc_v": round(dc["s3"], 6),
        "mna_fb_dc_v": round(dc["fb"], 6),
        "mna_div_ratio": round(div_ratio, 6),
    }


def build_and_verify(out_dir: Path | None = None) -> dict[str, Any]:
    od = Path(out_dir) if out_dir is not None else OUT_DIR
    od.mkdir(parents=True, exist_ok=True)

    spec = build_ion_column_hv_dac_board()
    board_res = verify_board_bundle(spec, od)

    cir_path = od / "ion_hv_filter_trim.cir"
    cir_path.write_text(render_ion_hv_ngspice_deck(), encoding="utf-8")
    sp_res = run_ngspice(cir_path, workdir=od)
    mna_res = run_mna_crosscheck()

    m = sp_res.metrics
    hv_atten_100k_db = float(m.get("hv_atten_100k_db", 0.0))
    hv_passive_100k_db = float(m.get("hv_passive_100k_db", 0.0))
    hv_ripple_mvpp = float(m.get("hv_ripple_vpp", 999.0)) * 1e3
    trim_rise_us = float(m.get("trim_rise_10_90_s", 999.0)) * 1e6
    trim_settle_us = float(m.get("trim_settle_1pct_s", 999.0)) * 1e6
    hv_div_ratio = float(m.get("hv_div_ratio", 0.0))
    hv_div_err_ppm = float(m.get("hv_div_err_ppm", 999999.0))
    m4_noise_nv_rthz = float(m.get("m4_noise_1khz_v_rthz", 999.0)) * 1e9
    mna_diff_db = abs(hv_passive_100k_db - mna_res["mna_passive_hv_atten_100k_db"])

    drc_d = board_res["drc"]
    checks = {
        "board_erc_drc_zero": board_res["passed"],
        "all_nets_routed_zero_unconnected": (
            drc_d.get("unrouted_net_count") == 0
            and drc_d.get("unconnected_items") == 0
            and drc_d.get("track_dangling_count") == 0
            and drc_d.get("routed_net_count", 0) == drc_d.get("total_multi_pin_nets", -1)
        ),
        "ngspice_ok": sp_res.ok,
        "hv_rejection_gt_80db": hv_atten_100k_db < -80.0,
        "hv_ripple_lt_1mvpp": hv_ripple_mvpp < 1.0,
        "trim_rise_lt_5us": 0.0 < trim_rise_us < 5.0,
        "trim_settle_lt_5us": 0.0 < trim_settle_us < 5.0,
        "divider_1000_to_1_within_100ppm": hv_div_err_ppm <= 100.0,
        "m4_dac_noise_lt_500nv_rthz": 0.0 < m4_noise_nv_rthz < 500.0,
        "mna_parity_within_0p1db": mna_diff_db < 0.1,
    }

    report = {
        "suite": "ion_column_hv_dac",
        "bom_ids": list(spec.bom_ids),
        "epistemic_meta": dict(spec.epistemic_meta),
        "board": board_res,
        "ngspice": {
            "cir_file": cir_path.name,
            "version": sp_res.version,
            "returncode": sp_res.returncode,
            "ok": sp_res.ok,
            "errors": sp_res.errors,
            "warnings": sp_res.warnings,
            "metrics_raw": sp_res.metrics,
            "summary": {
                "hv_atten_100k_db": round(hv_atten_100k_db, 3),
                "hv_passive_100k_db": round(hv_passive_100k_db, 3),
                "hv_ripple_mvpp_for_10vpp_in": round(hv_ripple_mvpp, 6),
                "hv_dc_v": round(float(m.get("hv_dc_v", 0.0)), 4),
                "hv_fb_dc_v": round(float(m.get("hv_fb_dc_v", 0.0)), 6),
                "hv_div_ratio": round(hv_div_ratio, 6),
                "hv_div_err_ppm": round(hv_div_err_ppm, 3),
                "trim_rise_10_90_us": round(trim_rise_us, 4),
                "trim_settle_1pct_us": round(trim_settle_us, 4),
                "m4_noise_1khz_nv_rthz": round(m4_noise_nv_rthz, 3),
                "m4_onoise_rms_uv": round(float(m.get("m4_onoise_rms_v", 0.0)) * 1e6, 4),
            },
        },
        "mna_crosscheck": {**mna_res, "hv_passive_100k_diff_db": round(mna_diff_db, 5)},
        "checks": checks,
        "all_passed": all(checks.values()),
    }
    (od / "ion_column_hv_dac_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    res = build_and_verify()
    drc_d = res["board"]["drc"]
    print(json.dumps({
        "all_passed": res["all_passed"],
        "erc_errors": len(res["board"]["erc"]["errors"]),
        "drc_errors": len(drc_d["errors"]),
        "routing": {
            "routed_net_count": drc_d["routed_net_count"],
            "total_multi_pin_nets": drc_d["total_multi_pin_nets"],
            "unrouted_net_count": drc_d["unrouted_net_count"],
            "unconnected_items": drc_d["unconnected_items"],
            "track_dangling_count": drc_d["track_dangling_count"],
            "segment_count": drc_d["segment_count"],
            "via_count": drc_d["via_count"],
        },
        "hv_checks": drc_d["hv_checks"],
        "ngspice_summary": res["ngspice"]["summary"],
        "mna_crosscheck": res["mna_crosscheck"],
        "checks": res["checks"],
    }, indent=2))
    if not res["all_passed"]:
        print("ERC errors:", res["board"]["erc"]["errors"][:10])
        print("DRC errors:", res["board"]["drc"]["errors"][:10])
        print("SPICE errors:", res["ngspice"]["errors"][:10])
        raise SystemExit(1)
