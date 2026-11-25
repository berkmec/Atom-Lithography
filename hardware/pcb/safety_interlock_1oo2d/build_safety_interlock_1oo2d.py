"""Diverse Dual-Channel 1oo2D Safety Interlock & 22 kV Active 2 MOhm HV Crowbar PCB.

STRICT EPISTEMIC NOTICE:
  DESIGN_ONLY_NOT_CERTIFIED
  iec61508_certified            = False
  semi_s2_certified             = False
  requires_third_party_assessment = True
  no_lab_measurement            = True
  no_physical_fab               = True

BOM Coverage:
  * S7.SAFETY-03: 1oo2D hardwired safety voting board, 4x dual-NC E-Stop loop, 2 MOhm 22 kV HV crowbar.
  * S7.SAFETY-02: Class-1 laser/X-ray shroud guard switches & dual-coil <3.2 ms mechanical shutter driver.
  * S7.SAFETY-05: Cleanroom O2 < 19.5% ODH comparator & quench fault input.
  * S7.SAFETY-06: <80 ms fail-close spring-return UHV gate-valve solenoid driver.
  * S7.SAFETY-01: Dual 0.02 ppm / 0.05 ppm PH3 4-20 mA sensor comparators.
  * S7.4-04:      Machine safety interlock PLC interface (UHV pressure > 1e-8 Torr trip).
  * S5.5-04:      MXC < 1 K thermal trip & <0.1 ms laser crowbar dual-enable outputs.
  * RTL Parity:   rtl/machine_ctrl/uhv_interlock_fsm.v (ch_a_ok, ch_b_ok, wdt_kick, safe_*_en).

Architecture:
  * 4-layer Isola FR408HR (er=3.66, CTI>=600 MG-I), 280 x 175 mm.
  * Physically separated diverse Ch-A (LM2903 + SN74LVC1G08 + Omron G7SA IEC 61810-3 force-guided
    safety relays) & Ch-B (MAX9032 + CD4081B + CPC1017N opto-SSR + SQJ461EP high-side MOSFET
    series cutoff), cross-channel XOR diagnostic discrepancy comparators, and TPS3850 hardware
    window watchdog.
  * Isolated 22 kV active 2.00 MOhm HV crowbar bay separated by milled Edge.Cuts air-slots
    (>= 30 mm clearance, >= 50 mm creepage) with diverse parallel NC 25 kV HV vacuum relays
    (Gigavac G81C + Ross E25) discharging C_stray = 1.5 nF from 22 kV -> <50 V in ~18.26 ms < 50 ms
    (E = 0.363 J < 0.5 J) even under single-channel relay fault injection.
"""
from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Any

from hardware.pcb.kicad_eda_verify import (
    BoardSpec,
    ComponentSpec,
    CreepageRule,
    DesignRules,
    KeepoutSpec,
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
    verify_board_bundle,
)

OUT_DIR = Path(__file__).resolve().parent

SAFETY_EPISTEMIC_META: dict[str, Any] = {
    "design_stage": "DESIGN_ONLY_NOT_CERTIFIED",
    "certification_status": "DESIGN_ONLY_NOT_CERTIFIED",
    "no_lab_measurement": True,
    "no_physical_fab": True,
    "iec61508_certified": False,
    "semi_s2_certified": False,
    "requires_third_party_assessment": True,
    "architecture_target": "1oo2D_de_energize_to_trip",
    "hv_crowbar_rating_V": 22000.0,
    "rtl_interface": "rtl/machine_ctrl/uhv_interlock_fsm.v",
}


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


def _dual_cmp_soic8_pins() -> tuple[PinSpec, ...]:
    """LM2903 (Ch-A) / MAX9032 (Ch-B) dual comparator (SOIC-8)."""
    names = {"1": "OUT1", "2": "IN1-", "3": "IN1+", "4": "GND", "5": "IN2+", "6": "IN2-", "7": "OUT2", "8": "VCC"}
    types = {
        "1": "output", "2": "input", "3": "input", "4": "power_in",
        "5": "input", "6": "input", "7": "output", "8": "power_in",
    }
    return auto_footprint_pads("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", [str(i) for i in range(1, 9)], names, types)


def _fg_relay_g7sa_pins() -> tuple[PinSpec, ...]:
    """Omron G7SA-3A1B IEC 61810-3 force-guided safety relay (10-pin THT: coil + 2x NO + 1x NC mirror)."""
    return (
        PinSpec("1", "COIL_P", "input", -7.5, -5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("2", "COIL_N", "input", -7.5, 5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("3", "NO1_A", "passive", -2.5, -5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("4", "NO1_B", "passive", -2.5, 5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("5", "NO2_A", "passive", 2.5, -5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("6", "NO2_B", "passive", 2.5, 5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("7", "NC_MIR_A", "passive", 7.5, -5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("8", "NC_MIR_B", "passive", 7.5, 5.08, 1.80, 1.80, drill_mm=1.00),
    )


def _ssr_opto_soic4_pins() -> tuple[PinSpec, ...]:
    """CPC1017N solid-state opto-SSR driver (SOP-4)."""
    return (
        PinSpec("1", "LED_A", "input", -2.54, -1.27, 1.20, 0.70),
        PinSpec("2", "LED_K", "input", -2.54, 1.27, 1.20, 0.70),
        PinSpec("3", "OUT_B", "passive", 2.54, 1.27, 1.20, 0.70),
        PinSpec("4", "OUT_A", "passive", 2.54, -1.27, 1.20, 0.70),
    )


def _pmos_dpak_pins() -> tuple[PinSpec, ...]:
    """SQJ461EP / IRF9540N high-side P-MOSFET safety cutoff switch (DPAK-3)."""
    return (
        PinSpec("1", "G", "input", -2.28, 2.50, 1.20, 1.60),
        PinSpec("2", "D", "passive", 0.0, -2.50, 3.00, 2.20),
        PinSpec("3", "S", "passive", 2.28, 2.50, 1.20, 1.60),
    )


def _logic_sot23_5_pins() -> tuple[PinSpec, ...]:
    names = {"1": "A", "2": "B", "3": "GND", "4": "Y", "5": "VCC"}
    types = {"1": "input", "2": "input", "3": "power_in", "4": "output", "5": "power_in"}
    return auto_footprint_pads("Package_TO_SOT_SMD:SOT-23-5", [str(i) for i in range(1, 6)], names, types)


def _wdt_sot23_6_pins() -> tuple[PinSpec, ...]:
    """TPS3850 hardware window watchdog supervisor (SOT-23-6)."""
    names = {"1": "WDO_N", "2": "GND", "3": "WDI", "4": "SET0", "5": "SET1", "6": "VDD"}
    types = {"1": "output", "2": "power_in", "3": "input", "4": "input", "5": "input", "6": "power_in"}
    return auto_footprint_pads("Package_TO_SOT_SMD:SOT-23-6", [str(i) for i in range(1, 7)], names, types)


def _ldo_sot223_pins() -> tuple[PinSpec, ...]:
    return (
        PinSpec("1", "VIN", "power_in", -2.30, 2.50, 1.10, 1.60),
        PinSpec("2", "GND", "power_in", 0.0, 2.50, 1.10, 1.60),
        PinSpec("3", "VOUT", "power_out", 2.30, 2.50, 1.10, 1.60),
        PinSpec("4", "TAB_GND", "power_in", 0.0, -2.50, 2.60, 1.60),
    )


def _hv22k_turret_pin() -> tuple[PinSpec, ...]:
    return (PinSpec("1", "HV_22KV", "passive", 0.0, 0.0, 2.60, 2.60, drill_mm=1.30),)


def _hv22k_relay_nc_pins() -> tuple[PinSpec, ...]:
    """25 kV NC HV Vacuum Relay (Gigavac G81C-25KV / Ross E25): HV contacts @ dy=-29 mm, 24 V coil @ dy=+29 mm."""
    return (
        PinSpec("1", "HV_COM", "passive", -4.5, -29.0, 2.40, 2.40, drill_mm=1.20),
        PinSpec("2", "HV_NC", "passive", 4.5, -29.0, 2.40, 2.40, drill_mm=1.20),
        PinSpec("3", "COIL_P", "input", -3.5, 29.0, 1.80, 1.80, drill_mm=0.90),
        PinSpec("4", "COIL_N", "input", 3.5, 29.0, 1.80, 1.80, drill_mm=0.90),
    )


def _hv22k_res_vertical_pins() -> tuple[PinSpec, ...]:
    """Ohmite MOX-4-25KV 1.00 MOhm 25 kV non-inductive HV resistor straddling 22 kV air-slot (58 mm pitch)."""
    return (
        PinSpec("1", "HV_TOP", "passive", 0.0, -29.0, 2.40, 2.40, drill_mm=1.20),
        PinSpec("2", "HV_BOT", "passive", 0.0, 29.0, 2.40, 2.40, drill_mm=1.20),
    )


def _hv22k_res_horiz_pins() -> tuple[PinSpec, ...]:
    return (
        PinSpec("1", "HV_A", "passive", -12.0, 0.0, 2.40, 2.40, drill_mm=1.20),
        PinSpec("2", "HV_B", "passive", 12.0, 0.0, 2.40, 2.40, drill_mm=1.20),
    )


def build_safety_interlock_1oo2d_board() -> BoardSpec:
    """Build diverse 1oo2D fail-safe voting & 22 kV active 2 MOhm HV crowbar PCB (DESIGN_ONLY_NOT_CERTIFIED)."""
    stackup = (
        StackupLayer("F.Cu", "signal", 0.035, material="Copper"),
        StackupLayer("dielectric 1", "prepreg", 0.200, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR"),
        StackupLayer("In1.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 2", "core", 1.100, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR"),
        StackupLayer("In2.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 3", "prepreg", 0.200, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR"),
        StackupLayer("B.Cu", "signal", 0.035, material="Copper"),
    )

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
    # SECTION 1 (LEFT EDGE, x=10..26 mm): DUAL 24 V UPS POWER & ALL FIELD SENSORS
    # =========================================================================
    j_pwr = add_c(ComponentSpec(
        "JPWR_24V_UPS", "TERM_4P_DUAL_24V_UPS", "Connector_PinHeader:HDR_1x4_5.08mm",
        12.0, 18.0, pins=auto_footprint_pads("HDR_1x4_5.08mm", ("1", "2", "3", "4"),
                                             {"1": "V24_UPS_A", "2": "GND_A", "3": "V24_UPS_B", "4": "GND_B"}),
        bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
    ))
    # Diverse 5 V regulators for Ch-A (LM2936) and Ch-B (ADP7142) + 0R star ground tie
    u_reg_a = add_c(ComponentSpec("U_REG_5V_A", "LM2936MP-5.0_CHA", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", 26.0, 16.0, pins=_ldo_sot223_pins(), mpn="LM2936MP-5.0", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_reg_b = add_c(ComponentSpec("U_REG_5V_B", "ADP7142_5V_CHB", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", 26.0, 156.0, pins=_ldo_sot223_pins(), mpn="ADP7142AUJZ-5.0", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    r_gnd_ab = add_c(ComponentSpec("R_GND_AB_TIE", "0R_STAR_GNDA_GNDB", "Resistor_SMD:R_0805_2012Metric", 26.0, 86.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

    # 4x Dual-NC E-Stop Mushroom Loop Connectors (S7.SAFETY-03, wired in series A1->A4 and B1->B4!)
    for idx in range(1, 5):
        ye = round(38.0 + (idx - 1) * 18.0, 1)
        je = add_c(ComponentSpec(
            f"J_ESTOP{idx}", f"TERM_4P_ESTOP_MUSHROOM_{idx}", "Connector_PinHeader:HDR_1x4_2.54mm",
            12.0, ye, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                               {"1": "NC_A_IN", "2": "NC_A_OUT", "3": "NC_B_IN", "4": "NC_B_OUT"}),
            bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
        ))
        a_in = "V_5V_A" if idx == 1 else f"ESTOP_A_{idx - 1}"
        a_out = "ESTOP_LOOP_A" if idx == 4 else f"ESTOP_A_{idx}"
        b_in = "V_5V_B" if idx == 1 else f"ESTOP_B_{idx - 1}"
        b_out = "ESTOP_LOOP_B" if idx == 4 else f"ESTOP_B_{idx}"
        conn(a_in, je.ref, 1); conn(a_out, je.ref, 2)
        conn(b_in, je.ref, 3); conn(b_out, je.ref, 4)
    # Fail-safe pulldowns on E-Stop loops (open-wire -> 0 V -> immediate trip!)
    r_es_pda = add_c(ComponentSpec("R_ESTOP_PD_A", "10.0k_1pct", "Resistor_SMD:R_0805_2012Metric", 24.0, 62.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_es_pdb = add_c(ComponentSpec("R_ESTOP_PD_B", "10.0k_1pct", "Resistor_SMD:R_0805_2012Metric", 24.0, 108.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    conn("ESTOP_LOOP_A", r_es_pda.ref, 1); conn("GND_A", r_es_pda.ref, 2)
    conn("ESTOP_LOOP_B", r_es_pdb.ref, 1); conn("GND_B", r_es_pdb.ref, 2)

    # Field Sensor Connectors (bottom-left x=12 mm, y=112..162 mm):
    # PH3 dual 4-20 mA (S7.SAFETY-01), O2 < 19.5% (S7.SAFETY-05), MXC < 1 K (S5.5-04), UHV > 1e-8 Torr (S7.4-04), Door/Quench (S7.SAFETY-02)
    j_ph3 = add_c(ComponentSpec(
        "J_PH3_SENS", "TERM_4P_PH3_4_20MA_DUAL", "Connector_PinHeader:HDR_1x4_2.54mm",
        12.0, 114.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                              {"1": "PH3_4_20_A", "2": "GND_A", "3": "PH3_4_20_B", "4": "GND_B"}),
        bom_id="S7.SAFETY-01", epistemic_tag="{Pasif-COTS}",
    ))
    j_o2 = add_c(ComponentSpec(
        "J_O2_SENS", "TERM_4P_O2_19p5PCT_DUAL", "Connector_PinHeader:HDR_1x4_2.54mm",
        12.0, 130.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                              {"1": "O2_4_20_A", "2": "GND_A", "3": "O2_4_20_B", "4": "GND_B"}),
        bom_id="S7.SAFETY-05", epistemic_tag="{Pasif-COTS}",
    ))
    j_mxc_uhv = add_c(ComponentSpec(
        "J_MXC_UHV_SENS", "TERM_6P_MXC1K_UHV1E8", "Connector_PinHeader:HDR_1x6_2.54mm",
        12.0, 152.0, pins=auto_footprint_pads("HDR_1x6_2.54mm", ("1", "2", "3", "4", "5", "6"),
                                              {"1": "MXC_V_A", "2": "MXC_V_B", "3": "UHV_V_A", "4": "UHV_V_B", "5": "DOOR_QUENCH_A", "6": "DOOR_QUENCH_B"}),
        bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}",
    ))

    # =========================================================================
    # SECTION 2 (x=38..92 mm): DUAL-CHANNEL DIVERSE SENSOR COMPARATORS (Ch-A TOP, Ch-B BOTTOM)
    # =========================================================================
    # Burden resistors (250 Ohm 0.1% -> 4-20 mA = 1.00-5.00 V) & reference thresholds for PH3, O2, MXC, UHV
    for ch, gnd, v5, yc_base, cmp_mpn, cmp_val in (
        ("A", "GND_A", "V_5V_A", 24.0, "LM2903DR",  "LM2903_DUAL_CMP_CHA"),
        ("B", "GND_B", "V_5V_B", 112.0, "MAX9032AKA", "MAX9032_DUAL_CMP_CHB"),
    ):
        # Burden resistors for PH3 (0.02/0.05 ppm) and O2 (<19.5%)
        rb_ph3 = add_c(ComponentSpec(f"R_BURD_PH3_{ch}", "250R_0.1pct_4_20MA", "Resistor_SMD:R_0805_2012Metric", 40.0, yc_base, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-01", epistemic_tag="{Pasif-COTS}"))
        rb_o2 = add_c(ComponentSpec(f"R_BURD_O2_{ch}", "250R_0.1pct_4_20MA", "Resistor_SMD:R_0805_2012Metric", 40.0, yc_base + 14.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-05", epistemic_tag="{Pasif-COTS}"))
        # Reference dividers for PH3 (0.02/0.05 ppm), O2 (19.5%), MXC (1.0 K), UHV (1e-8 Torr)
        r_ref_ph3_t = add_c(ComponentSpec(f"R_REF_PH3_T{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 48.0, yc_base - 4.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-01", epistemic_tag="{Pasif-COTS}"))
        r_ref_ph3_b = add_c(ComponentSpec(f"R_REF_PH3_B{ch}", "4.99k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 48.0, yc_base + 4.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-01", epistemic_tag="{Pasif-COTS}"))
        r_ref_o2_t = add_c(ComponentSpec(f"R_REF_O2_T{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 48.0, yc_base + 10.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-05", epistemic_tag="{Pasif-COTS}"))
        r_ref_o2_b = add_c(ComponentSpec(f"R_REF_O2_B{ch}", "30.1k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 48.0, yc_base + 18.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-05", epistemic_tag="{Pasif-COTS}"))
        r_ref_mxc_t = add_c(ComponentSpec(f"R_REF_MXC_T{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 48.0, yc_base + 28.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
        r_ref_mxc_b = add_c(ComponentSpec(f"R_REF_MXC_B{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 48.0, yc_base + 34.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
        r_ref_uhv_t = add_c(ComponentSpec(f"R_REF_UHV_T{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 48.0, yc_base + 42.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.4-04", epistemic_tag="{Pasif-COTS}"))
        r_ref_uhv_b = add_c(ComponentSpec(f"R_REF_UHV_B{ch}", "15.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 48.0, yc_base + 48.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.4-04", epistemic_tag="{Pasif-COTS}"))

        # Dual Comparator 1: PH3 (0.02/0.05 ppm) + O2 (<19.5%)
        u_cmp1 = add_c(ComponentSpec(f"U_CMP_GAS_{ch}", cmp_val, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 62.0, yc_base + 6.0, pins=_dual_cmp_soic8_pins(), mpn=cmp_mpn, bom_id="S7.SAFETY-01", epistemic_tag="{Aday-COTS}"))
        # Dual Comparator 2: MXC (<1 K) + UHV (>1e-8 Torr)
        u_cmp2 = add_c(ComponentSpec(f"U_CMP_VAC_{ch}", cmp_val, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 62.0, yc_base + 36.0, pins=_dual_cmp_soic8_pins(), mpn=cmp_mpn, bom_id="S7.4-04", epistemic_tag="{Aday-COTS}"))

        # Wire burdens & comparators (output HIGH = HEALTHY, LOW = TRIP!)
        conn(f"PH3_SENS_{ch}", rb_ph3.ref, 1); conn(gnd, rb_ph3.ref, 2)
        conn(f"O2_SENS_{ch}", rb_o2.ref, 1); conn(gnd, rb_o2.ref, 2)
        conn(v5, r_ref_ph3_t.ref, 1); conn(f"VREF_PH3_{ch}", r_ref_ph3_t.ref, 2); conn(f"VREF_PH3_{ch}", r_ref_ph3_b.ref, 1); conn(gnd, r_ref_ph3_b.ref, 2)
        conn(v5, r_ref_o2_t.ref, 1); conn(f"VREF_O2_{ch}", r_ref_o2_t.ref, 2); conn(f"VREF_O2_{ch}", r_ref_o2_b.ref, 1); conn(gnd, r_ref_o2_b.ref, 2)
        conn(v5, r_ref_mxc_t.ref, 1); conn(f"VREF_MXC_{ch}", r_ref_mxc_t.ref, 2); conn(f"VREF_MXC_{ch}", r_ref_mxc_b.ref, 1); conn(gnd, r_ref_mxc_b.ref, 2)
        conn(v5, r_ref_uhv_t.ref, 1); conn(f"VREF_UHV_{ch}", r_ref_uhv_t.ref, 2); conn(f"VREF_UHV_{ch}", r_ref_uhv_b.ref, 1); conn(gnd, r_ref_uhv_b.ref, 2)

        # PH3 healthy when V_PH3 < VREF_PH3; O2 healthy when V_O2 > VREF_O2
        conn(f"VREF_PH3_{ch}", u_cmp1.ref, 3); conn(f"PH3_SENS_{ch}", u_cmp1.ref, 2); conn(f"PH3_OK_{ch}", u_cmp1.ref, 1)
        conn(f"O2_SENS_{ch}", u_cmp1.ref, 5); conn(f"VREF_O2_{ch}", u_cmp1.ref, 6); conn(f"O2_OK_{ch}", u_cmp1.ref, 7)
        conn(v5, u_cmp1.ref, 8); conn(gnd, u_cmp1.ref, 4)

        # MXC healthy when T < 1 K (V_MXC < VREF); UHV healthy when P < 1e-8 Torr (V_UHV < VREF)
        conn(f"VREF_MXC_{ch}", u_cmp2.ref, 3); conn(f"MXC_SENS_{ch}", u_cmp2.ref, 2); conn(f"MXC_OK_{ch}", u_cmp2.ref, 1)
        conn(f"VREF_UHV_{ch}", u_cmp2.ref, 5); conn(f"UHV_SENS_{ch}", u_cmp2.ref, 6); conn(f"UHV_OK_{ch}", u_cmp2.ref, 7)
        conn(v5, u_cmp2.ref, 8); conn(gnd, u_cmp2.ref, 4)

        # Diverse Hardware Voting AND Cascade per Channel (Ch-A: SN74LVC1G08, Ch-B: CD4081B)
        v_mpn = "SN74LVC1G08DBVR" if ch == "A" else "CD4081B_DIVERSE"
        u_v1 = add_c(ComponentSpec(f"U_VOTE1_{ch}", f"AND_GAS_{v_mpn}", "Package_TO_SOT_SMD:SOT-23-5", 78.0, yc_base + 4.0, pins=_logic_sot23_5_pins(), mpn=v_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
        u_v2 = add_c(ComponentSpec(f"U_VOTE2_{ch}", f"AND_VAC_{v_mpn}", "Package_TO_SOT_SMD:SOT-23-5", 78.0, yc_base + 22.0, pins=_logic_sot23_5_pins(), mpn=v_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
        u_v3 = add_c(ComponentSpec(f"U_VOTE3_{ch}", f"AND_ESTOP_{v_mpn}", "Package_TO_SOT_SMD:SOT-23-5", 78.0, yc_base + 40.0, pins=_logic_sot23_5_pins(), mpn=v_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
        u_v4 = add_c(ComponentSpec(f"U_VOTE4_{ch}", f"AND_SENS_{v_mpn}", "Package_TO_SOT_SMD:SOT-23-5", 90.0, yc_base + 14.0, pins=_logic_sot23_5_pins(), mpn=v_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
        u_v5 = add_c(ComponentSpec(f"U_VOTE5_{ch}", f"AND_WDT_DISC_{v_mpn}", "Package_TO_SOT_SMD:SOT-23-5", 90.0, yc_base + 34.0, pins=_logic_sot23_5_pins(), mpn=v_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))

        conn(f"PH3_OK_{ch}", u_v1.ref, 1); conn(f"O2_OK_{ch}", u_v1.ref, 2); conn(f"GAS_OK_{ch}", u_v1.ref, 4); conn(v5, u_v1.ref, 5); conn(gnd, u_v1.ref, 3)
        conn(f"MXC_OK_{ch}", u_v2.ref, 1); conn(f"UHV_OK_{ch}", u_v2.ref, 2); conn(f"VAC_OK_{ch}", u_v2.ref, 4); conn(v5, u_v2.ref, 5); conn(gnd, u_v2.ref, 3)
        conn(f"ESTOP_LOOP_{ch}", u_v3.ref, 1); conn(f"DOOR_QUENCH_{ch}", u_v3.ref, 2); conn(f"ES_DR_OK_{ch}", u_v3.ref, 4); conn(v5, u_v3.ref, 5); conn(gnd, u_v3.ref, 3)
        conn(f"GAS_OK_{ch}", u_v4.ref, 1); conn(f"VAC_OK_{ch}", u_v4.ref, 2); conn(f"SENS_ALL_OK_{ch}", u_v4.ref, 4); conn(v5, u_v4.ref, 5); conn(gnd, u_v4.ref, 3)
        conn(f"SENS_ALL_OK_{ch}", u_v5.ref, 1); conn(f"ES_DR_OK_{ch}", u_v5.ref, 2); conn(f"CH_PRE_VOTE_{ch}", u_v5.ref, 4); conn(v5, u_v5.ref, 5); conn(gnd, u_v5.ref, 3)

    # Final Channel Gate combining Pre-Vote AND Hardware Watchdog & Diagnostic OK
    u_fin_a = add_c(ComponentSpec("U_FINAL_A", "SN74LVC1G08_FINAL_A", "Package_TO_SOT_SMD:SOT-23-5", 104.0, 44.0, pins=_logic_sot23_5_pins(), mpn="SN74LVC1G08DBVR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_fin_b = add_c(ComponentSpec("U_FINAL_B", "CD4081B_FINAL_B", "Package_TO_SOT_SMD:SOT-23-5", 104.0, 134.0, pins=_logic_sot23_5_pins(), mpn="CD4081B", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    conn("CH_PRE_VOTE_A", u_fin_a.ref, 1); conn("WDT_DIAG_OK", u_fin_a.ref, 2); conn("VOTE_SAFE_A", u_fin_a.ref, 4); conn("V_5V_A", u_fin_a.ref, 5); conn("GND_A", u_fin_a.ref, 3)
    conn("CH_PRE_VOTE_B", u_fin_b.ref, 1); conn("WDT_DIAG_OK", u_fin_b.ref, 2); conn("VOTE_SAFE_B", u_fin_b.ref, 4); conn("V_5V_B", u_fin_b.ref, 5); conn("GND_B", u_fin_b.ref, 3)

    # =========================================================================
    # SECTION 3 (CENTER, x=76..114 mm, y=78..96 mm): DIAGNOSTIC DISCREPANCY & WINDOW WATCHDOG
    # =========================================================================
    u_wdt = add_c(ComponentSpec("U_WDT_WIN", "TPS3850_WINDOW_WDT", "Package_TO_SOT_SMD:SOT-23-6", 80.0, 86.0, pins=_wdt_sot23_6_pins(), mpn="TPS3850H50QDRCRQ1", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_xor_v = add_c(ComponentSpec("U_DIAG_XOR_VOTE", "SN74AHC1G86_DISCREP1", "Package_TO_SOT_SMD:SOT-23-5", 92.0, 82.0, pins=_logic_sot23_5_pins(), mpn="SN74AHC1G86DBVR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_xor_fb = add_c(ComponentSpec("U_DIAG_XOR_FB", "SN74AHC1G86_DISCREP2", "Package_TO_SOT_SMD:SOT-23-5", 92.0, 92.0, pins=_logic_sot23_5_pins(), mpn="SN74AHC1G86DBVR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_diag_nor = add_c(ComponentSpec("U_DIAG_NOR", "SN74LVC1G02_DIAG_OK", "Package_TO_SOT_SMD:SOT-23-5", 104.0, 86.0, pins=_logic_sot23_5_pins(), mpn="SN74LVC1G02DBVR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_wdt_and = add_c(ComponentSpec("U_WDT_DIAG_AND", "SN74LVC1G08_WDT_DIAG", "Package_TO_SOT_SMD:SOT-23-5", 114.0, 86.0, pins=_logic_sot23_5_pins(), mpn="SN74LVC1G08DBVR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    r_disc_f = add_c(ComponentSpec("R_DISC_FILT", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", 100.0, 74.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    c_disc_f = add_c(ComponentSpec("C_DISC_FILT", "1.0uF_16V_X7R", "Capacitor_SMD:C_0603_1608Metric", 108.0, 74.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

    # FPGA Telemetry / Watchdog Header (matching rtl/machine_ctrl/uhv_interlock_fsm.v)
    j_fpga = add_c(ComponentSpec(
        "J_FPGA_ILK", "HDR_2x6_UHV_ILK_FSM", "Connector_PinHeader:HDR_2x6_2.54mm",
        52.0, 86.0, pins=auto_footprint_pads("HDR_2x6_2.54mm", [str(i) for i in range(1, 13)], {
            "1": "FPGA_WDT_KICK", "2": "WDT_OK_N_HIGH", "3": "DISCREP_FAULT", "4": "VOTE_SAFE_A",
            "5": "VOTE_SAFE_B", "6": "DIAG_FB_A", "7": "DIAG_FB_B", "8": "HV_SAFE_CLAMP",
            "9": "V_5V_A", "10": "GND_A", "11": "GND_B", "12": "WDT_DIAG_OK",
        }),
        bom_id="S7.4-04", epistemic_tag="{Pasif-COTS}",
    ))

    # =========================================================================
    # SECTION 4 (x=122..166 mm): DIVERSE FINAL CUTOFF ELEMENTS & ACTUATOR OUTPUTS
    #   Ch-A (TOP): Dual IEC 61810-3 Force-Guided Safety Relays K_FG_A1, K_FG_A2
    #   Ch-B (BOT): Diverse Opto-SSR CPC1017N + High-Side P-MOSFET SQJ461EP (SERIES!)
    # =========================================================================
    k_fg1 = add_c(ComponentSpec("K_FG_A1", "OMRON_G7SA_3A1B_SHUTTER", "Custom:OMRON_G7SA_FORCE_GUIDED", 132.0, 30.0, pins=_fg_relay_g7sa_pins(), mpn="Omron_G7SA-3A1B-DC24", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    k_fg2 = add_c(ComponentSpec("K_FG_A2", "OMRON_G7SA_3A1B_VALVE", "Custom:OMRON_G7SA_FORCE_GUIDED", 132.0, 56.0, pins=_fg_relay_g7sa_pins(), mpn="Omron_G7SA-3A1B-DC24", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    d_fg1_f = add_c(ComponentSpec("D_FG1_FLY", "1N4148WS_FLYBACK", "Diode_SMD:D_0805_2012Metric", 118.0, 30.0, pins=auto_footprint_pads("0805", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    d_fg2_f = add_c(ComponentSpec("D_FG2_FLY", "1N4148WS_FLYBACK", "Diode_SMD:D_0805_2012Metric", 118.0, 56.0, pins=auto_footprint_pads("0805", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_mir_pu = add_c(ComponentSpec("R_MIRROR_PU", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", 148.0, 44.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

    # Diverse Ch-B Solid-State Cutoff Path (CPC1017N Opto-SSR + SQJ461EP High-Side MOSFETs)
    u_ssr1 = add_c(ComponentSpec("U_OPTO_SSR_B1", "CPC1017N_SSR_SHUTTER", "Package_SO:SOP-4_3.8x4.1mm_P2.54mm", 122.0, 118.0, pins=_ssr_opto_soic4_pins(), mpn="CPC1017NTR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_ssr2 = add_c(ComponentSpec("U_OPTO_SSR_B2", "CPC1017N_SSR_VALVE", "Package_SO:SOP-4_3.8x4.1mm_P2.54mm", 122.0, 142.0, pins=_ssr_opto_soic4_pins(), mpn="CPC1017NTR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    q_ssr1 = add_c(ComponentSpec("Q_SSR_B1", "SQJ461EP_PMOS_SHUTTER", "Package_TO_SOT_SMD:TO-252-2", 138.0, 118.0, pins=_pmos_dpak_pins(), mpn="Vishay_SQJ461EP", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    q_ssr2 = add_c(ComponentSpec("Q_SSR_B2", "SQJ461EP_PMOS_VALVE", "Package_TO_SOT_SMD:TO-252-2", 138.0, 142.0, pins=_pmos_dpak_pins(), mpn="Vishay_SQJ461EP", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    r_ssr1_g = add_c(ComponentSpec("R_SSR1_PU", "10.0k_1pct", "Resistor_SMD:R_0805_2012Metric", 130.0, 108.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_ssr2_g = add_c(ComponentSpec("R_SSR2_PU", "10.0k_1pct", "Resistor_SMD:R_0805_2012Metric", 130.0, 132.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_fb_b = add_c(ComponentSpec("R_DIAG_FB_B", "10.0k_1pct", "Resistor_SMD:R_0805_2012Metric", 138.0, 158.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

    # Fast Demagnetization TVS Clamps (<3.2 ms Shutter & <80 ms UHV Gate Valve) + Output Terminal Blocks
    d_tvs_sh = add_c(ComponentSpec("D_TVS_SHUTTER", "SMBJ36A_FAST_DROP", "Diode_SMD:D_1206_3216Metric", 150.0, 26.0, pins=auto_footprint_pads("1206", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-02", epistemic_tag="{Pasif-COTS}"))
    d_tvs_vl = add_c(ComponentSpec("D_TVS_VALVE", "SMBJ36A_FAST_VALVE", "Diode_SMD:D_1206_3216Metric", 150.0, 56.0, pins=auto_footprint_pads("1206", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-06", epistemic_tag="{Pasif-COTS}"))
    j_shut = add_c(ComponentSpec(
        "J_SHUTTER_OUT", "TERM_4P_DUALCOIL_SHUTTER", "Connector_PinHeader:HDR_1x4_2.54mm",
        164.0, 26.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                              {"1": "SHUT_COIL1_P", "2": "GND_A", "3": "SHUT_COIL2_P", "4": "GND_B"}),
        bom_id="S7.SAFETY-02", epistemic_tag="{Pasif-COTS}",
    ))
    j_valve = add_c(ComponentSpec(
        "J_UHV_VALVE_OUT", "TERM_4P_UHV_GATEVALVE_80MS", "Connector_PinHeader:HDR_1x4_2.54mm",
        164.0, 56.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                              {"1": "UHV_VALVE_P", "2": "GND_A", "3": "HV_SAFE_CLAMP", "4": "GND_B"}),
        bom_id="S7.SAFETY-06", epistemic_tag="{Pasif-COTS}",
    ))
    j_las_cb = add_c(ComponentSpec(
        "J_LASER_CB_OUT", "TERM_4P_LASER_1OO2D_OUT", "Connector_PinHeader:HDR_1x4_2.54mm",
        164.0, 126.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                              {"1": "SAFE_LASER_EN_A", "2": "SAFE_LASER_EN_B", "3": "GND_A", "4": "GND_B"}),
        bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}",
    ))

    # =========================================================================
    # SECTION 5 (RIGHT HV BAY, x=216..270 mm): 22 kV ACTIVE 2.00 MOhm HV CROWBAR (S7.SAFETY-03)
    #   Separated from LV bay (x<=168) by 8x159 mm vertical air-slot x=[182..190]
    #   Hot 22 kV nodes strictly y<=58 mm; Return & 24 V coils strictly y>=114 mm
    #   separated by 72x8 mm horizontal air-slot y=[82..90] -> >=46 mm clr & >=65 mm crp!
    # =========================================================================
    j_hv22_in = add_c(ComponentSpec(
        "JHV_22KV_IN", "HV_TURRET_22KV_BUS", "Custom:HV_ALUMINA_TURRET_25KV",
        218.0, 26.0, pins=_hv22k_turret_pin(), mpn="CeramTec_25kV_Alumina_Turret",
        bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
    ))
    # Parallel Diverse Normally-Closed 25 kV HV Vacuum Crowbar Relays (Ch-A + Ch-B)
    # Both straddle horizontal slot y=[82..90]: HV contacts @ y=57 mm, 24 V coils @ y=115 mm!
    k_cb_a = add_c(ComponentSpec(
        "K_CROWBAR_A", "GIGAVAC_G81C_25KV_NC_CHA", "Custom:HV25KV_VACUUM_RELAY_P58mm",
        224.0, 86.0, pins=_hv22k_relay_nc_pins(), mpn="Gigavac_G81C-25KV-NC",
        bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}",
    ))
    k_cb_b = add_c(ComponentSpec(
        "K_CROWBAR_B", "ROSS_E25_25KV_NC_CHB", "Custom:HV25KV_VACUUM_RELAY_P58mm",
        244.0, 86.0, pins=_hv22k_relay_nc_pins(), mpn="Ross_E25-NC-25KV",
        bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}",
    ))
    # Active 2.00 MOhm Non-Inductive HV Discharge Resistor String (2 x 1.00 MOhm Ohmite MOX-4-25KV in series)
    # R_CROWBAR_1 horizontal in HV hot bay (y=38 mm); R_CROWBAR_2 straddles y=[82..90] slot to HV_CROWBAR_RTN!
    r_cb_1 = add_c(ComponentSpec(
        "R_CROWBAR_1", "1.00M_25KV_OHMITE_MOX4", "Custom:OHMITE_MOX4_25KV_H24mm",
        250.0, 38.0, pins=_hv22k_res_horiz_pins(), mpn="Ohmite_MOX400231004FE",
        bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
    ))
    r_cb_2 = add_c(ComponentSpec(
        "R_CROWBAR_2", "1.00M_25KV_OHMITE_MOX4", "Custom:OHMITE_MOX4_25KV_V58mm",
        262.0, 86.0, pins=_hv22k_res_vertical_pins(), mpn="Ohmite_MOX400231004FE",
        bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
    ))
    j_hv22_rtn = add_c(ComponentSpec(
        "JHV_22KV_RTN", "HV_CROWBAR_PE_STUD", "Custom:HV_ALUMINA_TURRET_25KV",
        262.0, 146.0, pins=_hv22k_turret_pin(), mpn="Keystone_PE_Stud_M4",
        bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
    ))
    d_cba_f = add_c(ComponentSpec("D_CB_A_FLY", "SMBJ36A_CB_A", "Diode_SMD:D_1206_3216Metric", 224.0, 130.0, pins=auto_footprint_pads("1206", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    d_cbb_f = add_c(ComponentSpec("D_CB_B_FLY", "SMBJ36A_CB_B", "Diode_SMD:D_1206_3216Metric", 244.0, 130.0, pins=auto_footprint_pads("1206", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_hv_pe = add_c(ComponentSpec("R_HV_PE_TIE", "0R_HV_RTN_STAR", "Resistor_SMD:R_1206_3216Metric", 244.0, 146.0, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

    # =========================================================================
    # NETLIST CONNECTIONS
    # =========================================================================
    # Power & Star Ground
    conn("V_24V_A", j_pwr.ref, 1); conn("GND_A", j_pwr.ref, 2)
    conn("V_24V_B", j_pwr.ref, 3); conn("GND_B", j_pwr.ref, 4)
    conn("GND_A", r_gnd_ab.ref, 1); conn("GND_B", r_gnd_ab.ref, 2)
    conn("V_24V_A", u_reg_a.ref, 1); conn("GND_A", u_reg_a.ref, 2); conn("GND_A", u_reg_a.ref, 4); conn("V_5V_A", u_reg_a.ref, 3)
    conn("V_24V_B", u_reg_b.ref, 1); conn("GND_B", u_reg_b.ref, 2); conn("GND_B", u_reg_b.ref, 4); conn("V_5V_B", u_reg_b.ref, 3)

    # Sensor Connectors
    conn("PH3_SENS_A", j_ph3.ref, 1); conn("GND_A", j_ph3.ref, 2); conn("PH3_SENS_B", j_ph3.ref, 3); conn("GND_B", j_ph3.ref, 4)
    conn("O2_SENS_A", j_o2.ref, 1); conn("GND_A", j_o2.ref, 2); conn("O2_SENS_B", j_o2.ref, 3); conn("GND_B", j_o2.ref, 4)
    conn("MXC_SENS_A", j_mxc_uhv.ref, 1); conn("MXC_SENS_B", j_mxc_uhv.ref, 2)
    conn("UHV_SENS_A", j_mxc_uhv.ref, 3); conn("UHV_SENS_B", j_mxc_uhv.ref, 4)
    conn("DOOR_QUENCH_A", j_mxc_uhv.ref, 5); conn("DOOR_QUENCH_B", j_mxc_uhv.ref, 6)

    # Watchdog, Cross-Channel Diagnostic Discrepancy Comparators & FPGA Telemetry
    conn("WDT_OK", u_wdt.ref, 1); conn("GND_A", u_wdt.ref, 2); conn("FPGA_WDT_KICK", u_wdt.ref, 3)
    conn("V_5V_A", u_wdt.ref, 4); conn("GND_A", u_wdt.ref, 5); conn("V_5V_A", u_wdt.ref, 6)

    conn("CH_PRE_VOTE_A", u_xor_v.ref, 1); conn("CH_PRE_VOTE_B", u_xor_v.ref, 2)
    conn("GND_A", u_xor_v.ref, 3); conn("V_5V_A", u_xor_v.ref, 5); conn("DISC_VOTE_RAW", u_xor_v.ref, 4)

    conn("DIAG_FB_A", u_xor_fb.ref, 1); conn("DIAG_FB_B", u_xor_fb.ref, 2)
    conn("GND_A", u_xor_fb.ref, 3); conn("V_5V_A", u_xor_fb.ref, 5); conn("DISC_FB_RAW", u_xor_fb.ref, 4)

    conn("DISC_VOTE_RAW", r_disc_f.ref, 1); conn("DISCREP_FAULT", r_disc_f.ref, 2)
    conn("DISCREP_FAULT", c_disc_f.ref, 1); conn("GND_A", c_disc_f.ref, 2)
    conn("DISCREP_FAULT", u_diag_nor.ref, 1); conn("DISC_FB_RAW", u_diag_nor.ref, 2)
    conn("GND_A", u_diag_nor.ref, 3); conn("V_5V_A", u_diag_nor.ref, 5); conn("DIAG_OK", u_diag_nor.ref, 4)

    conn("WDT_OK", u_wdt_and.ref, 1); conn("DIAG_OK", u_wdt_and.ref, 2)
    conn("GND_A", u_wdt_and.ref, 3); conn("V_5V_A", u_wdt_and.ref, 5); conn("WDT_DIAG_OK", u_wdt_and.ref, 4)

    conn("FPGA_WDT_KICK", j_fpga.ref, 1); conn("WDT_OK", j_fpga.ref, 2)
    conn("DISCREP_FAULT", j_fpga.ref, 3); conn("VOTE_SAFE_A", j_fpga.ref, 4)
    conn("VOTE_SAFE_B", j_fpga.ref, 5); conn("DIAG_FB_A", j_fpga.ref, 6)
    conn("DIAG_FB_B", j_fpga.ref, 7); conn("HV_SAFE_CLAMP", j_fpga.ref, 8)
    conn("V_5V_A", j_fpga.ref, 9); conn("GND_A", j_fpga.ref, 10)
    conn("GND_B", j_fpga.ref, 11); conn("WDT_DIAG_OK", j_fpga.ref, 12)

    # Ch-A Force-Guided Safety Relays K_FG_A1 (Shutter + Laser) & K_FG_A2 (UHV Valve + HV Clamp)
    conn("VOTE_SAFE_A", k_fg1.ref, 1); conn("GND_A", k_fg1.ref, 2)
    conn("VOTE_SAFE_A", d_fg1_f.ref, 1); conn("GND_A", d_fg1_f.ref, 2)
    conn("VOTE_SAFE_A", k_fg2.ref, 1); conn("GND_A", k_fg2.ref, 2)
    conn("VOTE_SAFE_A", d_fg2_f.ref, 1); conn("GND_A", d_fg2_f.ref, 2)

    # Series Safety Cutoff Topology: V_24V_A -> K_FG_A1 NO -> Q_SSR_B1 (Ch-B) -> Shutter!
    # Even if K_FG_A1 sticks welded CLOSED, Q_SSR_B1 OPENS and de-energizes Shutter!
    conn("V_24V_A", k_fg1.ref, 3); conn("SHUT_MID_AB", k_fg1.ref, 4)
    conn("V_24V_A", k_fg1.ref, 5); conn("SAFE_LASER_EN_A", k_fg1.ref, 6)
    # Mechanically linked NC mirror contacts (IEC 61810-3 weld detection!)
    conn("V_5V_A", r_mir_pu.ref, 1); conn("DIAG_FB_A", r_mir_pu.ref, 2)
    conn("DIAG_FB_A", k_fg1.ref, 7); conn("MIR_MID", k_fg1.ref, 8)
    conn("MIR_MID", k_fg2.ref, 7); conn("GND_A", k_fg2.ref, 8)

    conn("V_24V_A", k_fg2.ref, 3); conn("VALVE_MID_AB", k_fg2.ref, 4)
    conn("V_24V_A", k_fg2.ref, 5); conn("HV_SAFE_CLAMP", k_fg2.ref, 6)

    # Diverse Ch-B Opto-SSR + High-Side P-MOSFET Cutoff
    conn("VOTE_SAFE_B", u_ssr1.ref, 1); conn("GND_B", u_ssr1.ref, 2)
    conn("GND_B", u_ssr1.ref, 3); conn("SSR1_GATE", u_ssr1.ref, 4)
    conn("SHUT_MID_AB", r_ssr1_g.ref, 1); conn("SSR1_GATE", r_ssr1_g.ref, 2)
    conn("SSR1_GATE", q_ssr1.ref, 1); conn("SHUT_MID_AB", q_ssr1.ref, 3); conn("SHUT_SAFE_24V", q_ssr1.ref, 2)

    conn("VOTE_SAFE_B", u_ssr2.ref, 1); conn("GND_B", u_ssr2.ref, 2)
    conn("GND_B", u_ssr2.ref, 3); conn("SSR2_GATE", u_ssr2.ref, 4)
    conn("VALVE_MID_AB", r_ssr2_g.ref, 1); conn("SSR2_GATE", r_ssr2_g.ref, 2)
    conn("SSR2_GATE", q_ssr2.ref, 1); conn("VALVE_MID_AB", q_ssr2.ref, 3); conn("VALVE_SAFE_24V", q_ssr2.ref, 2)
    conn("VALVE_SAFE_24V", r_fb_b.ref, 1); conn("DIAG_FB_B", r_fb_b.ref, 2)

    # Actuator Output Connectors & Fast TVS Demagnetization Clamps
    conn("SHUT_SAFE_24V", d_tvs_sh.ref, 1); conn("GND_A", d_tvs_sh.ref, 2)
    conn("SHUT_SAFE_24V", j_shut.ref, 1); conn("GND_A", j_shut.ref, 2)
    conn("SHUT_SAFE_24V", j_shut.ref, 3); conn("GND_B", j_shut.ref, 4)

    conn("VALVE_SAFE_24V", d_tvs_vl.ref, 1); conn("GND_A", d_tvs_vl.ref, 2)
    conn("VALVE_SAFE_24V", j_valve.ref, 1); conn("GND_A", j_valve.ref, 2)
    conn("HV_SAFE_CLAMP", j_valve.ref, 3); conn("GND_B", j_valve.ref, 4)

    conn("SAFE_LASER_EN_A", j_las_cb.ref, 1); conn("SHUT_SAFE_24V", j_las_cb.ref, 2)
    conn("GND_A", j_las_cb.ref, 3); conn("GND_B", j_las_cb.ref, 4)

    # 22 kV Active 2.00 MOhm HV Crowbar Bay (Parallel Diverse NC Relays K_CROWBAR_A || K_CROWBAR_B!)
    conn("HV_22KV_BUS", j_hv22_in.ref, 1); conn("HV_22KV_BUS", k_cb_a.ref, 1); conn("HV_22KV_BUS", k_cb_b.ref, 1)
    conn("HV_22KV_DUMP", k_cb_a.ref, 2); conn("HV_22KV_DUMP", k_cb_b.ref, 2); conn("HV_22KV_DUMP", r_cb_1.ref, 1)
    conn("HV_22KV_MID", r_cb_1.ref, 2); conn("HV_22KV_MID", r_cb_2.ref, 1)
    conn("HV_CROWBAR_RTN", r_cb_2.ref, 2); conn("HV_CROWBAR_RTN", j_hv22_rtn.ref, 1)
    conn("HV_CROWBAR_RTN", r_hv_pe.ref, 1); conn("GND_B", r_hv_pe.ref, 2)

    # 22 kV Crowbar Relay Coils (De-Energize-To-Crowbar: energized by SAFE_LASER_EN_A & VALVE_SAFE_24V!)
    conn("SAFE_LASER_EN_A", k_cb_a.ref, 3); conn("GND_A", k_cb_a.ref, 4)
    conn("SAFE_LASER_EN_A", d_cba_f.ref, 1); conn("GND_A", d_cba_f.ref, 2)
    conn("VALVE_SAFE_24V", k_cb_b.ref, 3); conn("GND_B", k_cb_b.ref, 4)
    conn("VALVE_SAFE_24V", d_cbb_f.ref, 1); conn("GND_B", d_cbb_f.ref, 2)

    # =========================================================================
    # COPPER TRACES & STITCHING VIAS
    # =========================================================================
    # 22 kV HV Crowbar Bus on F.Cu (strictly inside x=[218..264], y=[26..66]; zero crossings!)
    ka1, ka2 = _pad_xy(k_cb_a, "1"), _pad_xy(k_cb_a, "2")
    kb1, kb2 = _pad_xy(k_cb_b, "1"), _pad_xy(k_cb_b, "2")
    traces.append(make_manhattan_trace("HV_22KV_BUS", "F.Cu", _pad_xy(j_hv22_in, "1"), ka1, width_mm=1.50, mid_y=40.0))
    traces.append(TraceSpec("HV_22KV_BUS", "F.Cu", (ka1, (ka1[0], 46.0), (kb1[0], 46.0), kb1), width_mm=1.50))
    traces.append(TraceSpec("HV_22KV_DUMP", "F.Cu", (ka2, (ka2[0], 65.0), (kb2[0], 65.0), kb2), width_mm=1.50))
    traces.append(make_manhattan_trace("HV_22KV_DUMP", "F.Cu", kb2, _pad_xy(r_cb_1, "1"), width_mm=1.50, mid_y=38.0))
    traces.append(make_manhattan_trace("HV_22KV_MID", "F.Cu", _pad_xy(r_cb_1, "2"), _pad_xy(r_cb_2, "1"), width_mm=1.50))
    # HV Return Bus on B.Cu (strictly y >= 115 mm)
    traces.append(make_manhattan_trace("HV_CROWBAR_RTN", "B.Cu", _pad_xy(r_cb_2, "2"), _pad_xy(j_hv22_rtn, "1"), width_mm=1.50))

    # LV Stitching Vias (strictly in LV bay x <= 166 mm)
    for vx in (34.0, 84.0, 144.0):
        vias.append(ViaSpec("GND_A", vx, 10.0, diameter_mm=0.70, drill_mm=0.35))
        vias.append(ViaSpec("GND_B", vx, 166.0, diameter_mm=0.70, drill_mm=0.35))

    # =========================================================================
    # MILLED EDGE.CUTS 22 kV HV ISOLATION AIR-SLOTS (>= 30 mm clr / >= 50 mm crp!)
    # =========================================================================
    # L-shaped milled Edge.Cuts 22 kV air-slot barrier enclosing the top-right 22 kV island (x>=216, y<=66):
    # vertical slot x=[182..190], y=[8..108] + horizontal slot x=[202..272], y=[82..90];
    # leaves y=[112..170] open for 24 V crowbar coils & PE return (>=46 mm clr & >=59 mm crp!).
    keepouts = (
        KeepoutSpec("HV22K_LV_MAIN_SLOT", "air_slot", ("Edge.Cuts",), x_mm=182.0, y_mm=8.0, width_mm=8.0, height_mm=100.0),
        KeepoutSpec("HV22K_HOT_RTN_SLOT", "air_slot", ("Edge.Cuts",), x_mm=202.0, y_mm=82.0, width_mm=70.0, height_mm=8.0),
    )

    # LV Planes strictly in LV bay (x <= 170 mm -> >= 46 mm from HV_22KV_* & zero through-board overlap!)
    zones = (
        ZoneSpec("GND_A", "In1.Cu", ((4.0, 4.0), (170.0, 4.0), (170.0, 82.0), (4.0, 82.0))),
        ZoneSpec("GND_B", "In1.Cu", ((4.0, 90.0), (170.0, 90.0), (170.0, 171.0), (4.0, 171.0))),
        ZoneSpec("V_24V_A", "In2.Cu", ((4.0, 4.0), (170.0, 4.0), (170.0, 82.0), (4.0, 82.0))),
        ZoneSpec("V_24V_B", "In2.Cu", ((4.0, 90.0), (170.0, 90.0), (170.0, 171.0), (4.0, 171.0))),
    )

    pwr_nets = {"V_24V_A", "V_24V_B", "V_5V_A", "V_5V_B", "GND_A", "GND_B", "HV_22KV_BUS", "HV_CROWBAR_RTN"}
    flag_nets = {"V_24V_A", "V_24V_B", "GND_A", "GND_B", "HV_22KV_BUS", "HV_CROWBAR_RTN"}

    nets: list[NetSpec] = []
    for nname, nodes in sorted(nets_dict.items()):
        v_work = 22000.0 if nname.startswith("HV_22KV_") else (
            24.0 if ("24V" in nname or "SHUT" in nname or "VALVE" in nname or "LASER" in nname or "CLAMP" in nname) else (
                5.0 if "5V" in nname else 0.0
            )
        )
        is_pwr = nname in pwr_nets
        nets.append(NetSpec(
            name=nname,
            nodes=tuple(nodes),
            net_class="HV_22KV" if v_work >= 10000.0 else ("Power" if is_pwr else "Default"),
            is_power=is_pwr,
            has_pwr_flag=(nname in flag_nets),
            voltage_v=v_work,
        ))

    creepage_rules = (
        CreepageRule(
            net_pattern="HV_22KV_*",
            working_voltage_v=22000.0,
            min_clearance_mm=30.0,
            min_creepage_mm=50.0,
            standard="IEC 61010-1 / IPC-2221B (22 kV MG-I Air-Slotted)",
            pollution_degree=2,
            material_group="I",
        ),
    )

    spec = BoardSpec(
        name="safety_interlock_1oo2d",
        title="1oo2D Diverse Safety Interlock & 22 kV 2 MOhm HV Crowbar PCB [DESIGN_ONLY_NOT_CERTIFIED]",
        rev="v1.0",
        bom_ids=("S7.SAFETY-03", "S7.SAFETY-02", "S7.SAFETY-05", "S7.SAFETY-06", "S7.SAFETY-01", "S7.4-04", "S5.5-04"),
        width_mm=280.0,
        height_mm=175.0,
        stackup=stackup,
        components=tuple(comps),
        nets=tuple(nets),
        traces=tuple(traces),
        vias=tuple(vias),
        zones=zones,
        keepouts=keepouts,
        creepage_rules=creepage_rules,
        rules=DesignRules(min_trace_width_mm=0.127, min_clearance_mm=0.127, min_edge_clearance_mm=0.50),
        epistemic_meta=dict(SAFETY_EPISTEMIC_META),
    )
    return auto_route_board(spec, grid_mm=0.50, preserve_existing=True)


def render_safety_1oo2d_ngspice_deck() -> str:
    """Native ngspice-47 deck verifying 22 kV 1.5 nF 2 MOhm crowbar & 1oo2D single-channel fault injection."""
    return """* Atom Lithography Machine - 1oo2D Safety Interlock & 22 kV 2 MOhm HV Crowbar Verification
* BOM: S7.SAFETY-03, S7.SAFETY-02, S7.SAFETY-05, S7.SAFETY-06, S7.SAFETY-01, S7.4-04, S5.5-04
* STRICT EPISTEMIC NOTICE: DESIGN_ONLY_NOT_CERTIFIED (iec61508_certified=false, semi_s2_certified=false)

.temp 26.85
.options reltol=1e-4 vntol=1e-6 abstol=1e-12

* --- Switch Models ---
* Normally-Closed 25 kV HV Vacuum Crowbar Relay: CLOSED (Ron=0.1 Ohm) when coil V < 2 V (de-energized), OPEN (100 GOhm) when V > 2 V
.model SW_HV_NC  SW(VT=2.5 VH=0.2 RON=100G ROFF=0.1)
* HV PSU Isolation Contactor (OPEN on trip, CLOSED when healthy)
.model SW_HV_NO  SW(VT=2.5 VH=0.2 RON=100  ROFF=100G)
* LV Safety Relay / MOSFET Cutoff (CLOSED when energized > 2.5 V, OPEN = 100 MOhm when de-energized)
.model SW_LV_NO  SW(VT=2.5 VH=0.2 RON=0.05 ROFF=100Meg)
* Fast 36 V TVS Zener Demagnetization Clamp Model
.model D_TVS36   D(IS=1e-12 BV=36.0 IBV=1m N=1.5 RS=0.5)

* Trip command: HEALTHY (5.0 V) for t < 1.0 ms; TRIPPED (0.0 V) for t >= 1.0 ms
Vtrip_cmd trip_ok 0 DC 5.0 PWL(0 5.0 0.999m 5.0 1.000m 0.0 50m 0.0)
* Always-HIGH rail (for modeling stuck-ON / stuck-welded Channel-A fault!)
Vstuck_hi stuck_hi 0 DC 5.0

* =========================================================================
* 1) NOMINAL 22 kV 1.5 nF ACTIVE 2.00 MOhm HV CROWBAR DISCHARGE (BOTH Ch-A & Ch-B TRIP)
* =========================================================================
* C_stray = 1.500 nF charged to 22,000 V; at t=1.0 ms HV PSU disconnects & K_CROWBAR_A || K_CROWBAR_B close
* onto R_CROWBAR_1 (1.00 MOhm) + R_CROWBAR_2 (1.00 MOhm) = 2.00 MOhm.
* Analytical: tau = 2.00M * 1.5n = 3.000 ms; t_50V = 3.000 * ln(22000/50) = 18.2603 ms; E = 0.3630 J.
Vhv_nom   hv_src_n 0 DC 22000
Spsu_nom  hv_src_n hv_bus_n trip_ok 0 SW_HV_NO
Cstray_n  hv_bus_n 0 1.5n IC=22000
Sk_cba_n  hv_bus_n hv_dmp_n trip_ok 0 SW_HV_NC
Sk_cbb_n  hv_bus_n hv_dmp_n trip_ok 0 SW_HV_NC
Rcb1_n    hv_dmp_n hv_mid_n 1.00Meg
Rcb2_n    hv_mid_n 0        1.00Meg
* Instantaneous power dissipated in 2.00 MOhm dump resistor: P = V(hv_dmp_n)^2 / 2.00Meg
Bp_nom    p_dump_n 0 V = (V(hv_dmp_n) * V(hv_dmp_n)) / 2.0e6

* =========================================================================
* 2) SINGLE-CHANNEL FAULT INJECTION #1: K_CROWBAR_A STUCK OPEN (FAILED RELAY)
* =========================================================================
* K_CROWBAR_A coil stuck energized (HV contact STUCK OPEN = 100 GOhm!), ONLY diverse Ch-B K_CROWBAR_B closes!
Vhv_flt   hv_src_f 0 DC 22000
Spsu_flt  hv_src_f hv_bus_f trip_ok  0 SW_HV_NO
Cstray_f  hv_bus_f 0 1.5n IC=22000
Sk_cba_f  hv_bus_f hv_dmp_f stuck_hi 0 SW_HV_NC
Sk_cbb_f  hv_bus_f hv_dmp_f trip_ok  0 SW_HV_NC
Rcb1_f    hv_dmp_f hv_mid_f 1.00Meg
Rcb2_f    hv_mid_f 0        1.00Meg
Bp_flt    p_dump_f 0 V = (V(hv_dmp_f) * V(hv_dmp_f)) / 2.0e6

* =========================================================================
* 3) SINGLE-CHANNEL FAULT INJECTION #2: K_FG_A1 STUCK WELDED CLOSED ON 24 V SHUTTER
* =========================================================================
* Channel-A force-guided relay K_FG_A1 sticks WELDED CLOSED (10 mOhm!).
* Diverse Channel-B P-MOSFET SSR Q_SSR_B1 in SERIES still opens at t=1.0 ms -> de-energizes shutter coil!
* 36 V TVS zener clamp accelerates coil demagnetization (< 1 ms << 3.2 ms mechanical shutter spec!).
V24_sh    v24_sh 0 DC 24.0
R_weld_a  v24_sh sh_mid_ab 10m
Sq_ssr_b  sh_mid_ab sh_out trip_ok 0 SW_LV_NO
* Dual-coil shutter actuator load (48 Ohm, 20 mH -> 500 mA hold current) + 36 V fast-drop TVS clamp
R_sh_c    sh_out sh_ind 48.0
L_sh_c    sh_ind 0      20m
D_sh_tvs  0      sh_out D_TVS36
R_sh_bleed sh_out 0     100k

* Cross-channel diagnostic discrepancy comparator:
* Mirror feedback A reads 0 V (welded closed!) while Ch-B feedback reads 5 V (open!) -> XOR asserts 5 V FAULT!
B_fb_a    diag_fb_a 0 V = 0.0
B_fb_b    diag_fb_b 0 V = 5.0 * (1.0 - V(trip_ok) / 5.0)
B_xor_d   discrep_fault 0 V = abs(V(diag_fb_a) - V(diag_fb_b))

* =========================================================================
* 4) SINGLE-CHANNEL FAULT INJECTION #3: OPEN-WIRE SENSOR BREAK ON Ch-A E-STOP
* =========================================================================
* ESTOP_A breaks (5 V -> 0 V at t=1.0 ms) while ESTOP_B stays 5.0 V -> 1oo2 hardware AND drops BOTH channels!
Vestop_a  es_a 0 DC 5.0 PWL(0 5.0 0.999m 5.0 1.000m 0.0 50m 0.0)
Vestop_b  es_b 0 DC 5.0
B_vote1oo2 vote_1oo2 0 V = min(V(es_a), V(es_b))
V24_ow    v24_ow 0 DC 24.0
S_ow_a    v24_ow ow_mid vote_1oo2 0 SW_LV_NO
S_ow_b    ow_mid ow_load vote_1oo2 0 SW_LV_NO
R_ow_ld   ow_load 0 48.0

.control
set noaskquit

tran 20u 45m 0 50u

* 1) Nominal 22 kV -> <50 V active 2 MOhm crowbar discharge
meas tran hv_nom_init_v  FIND v(hv_bus_n) AT=0.5m
meas tran hv_nom_t50_abs WHEN v(hv_bus_n)=50.0 FALL=1 TD=0.99m
let hv_nom_t50_ms = (hv_nom_t50_abs - 1.0m) * 1e3
meas tran hv_nom_v_at_40m FIND v(hv_bus_n) AT=40m
meas tran hv_nom_energy_j INTEG v(p_dump_n) FROM=0.99m TO=44m
print hv_nom_t50_ms

* 2) Fault-Injected 22 kV Crowbar (K_CROWBAR_A stuck OPEN; Ch-B K_CROWBAR_B discharges!)
meas tran hv_flt_t50_abs WHEN v(hv_bus_f)=50.0 FALL=1 TD=0.99m
let hv_flt_t50_ms = (hv_flt_t50_abs - 1.0m) * 1e3
meas tran hv_flt_v_at_40m FIND v(hv_bus_f) AT=40m
meas tran hv_flt_energy_j INTEG v(p_dump_f) FROM=0.99m TO=44m
print hv_flt_t50_ms

* 3) Fault-Injected Welded Ch-A Relay (K_FG_A1 welded 10 mOhm; Ch-B SSR cuts 24 V shutter safe!)
meas tran sh_i_on   FIND i(L_sh_c) AT=0.5m
meas tran sh_v_on   FIND v(sh_out) AT=0.5m
meas tran sh_v_safe FIND v(sh_out) AT=5.0m
meas tran sh_i_safe FIND i(L_sh_c) AT=5.0m
let sh_i10 = 0.10 * sh_i_on
meas tran sh_t_drop_abs WHEN i(L_sh_c)=$&sh_i10 FALL=1 TD=0.99m
let sh_drop_ms = (sh_t_drop_abs - 1.0m) * 1e3
meas tran discrep_fault_v FIND v(discrep_fault) AT=5.0m
print sh_drop_ms

* 4) Fault-Injected Open-Wire Sensor Break (ESTOP_A broken while ESTOP_B=5V -> 1oo2 load safe!)
meas tran ow_v_on   FIND v(ow_load) AT=0.5m
meas tran ow_v_safe FIND v(ow_load) AT=5.0m

quit 0
.endc
.end
"""


def run_analytical_crosscheck() -> dict[str, float]:
    """Independent analytical physics cross-check of 22 kV 1.5 nF 2.00 MOhm RC crowbar discharge."""
    v0 = 22000.0
    c_stray = 1.5e-9
    r_dump = 2.0e6
    tau_ms = r_dump * c_stray * 1e3
    t_50v_ms = tau_ms * math.log(v0 / 50.0)
    energy_j = 0.5 * c_stray * v0 * v0
    return {
        "analytical_tau_ms": round(tau_ms, 5),
        "analytical_t_50v_ms": round(t_50v_ms, 5),
        "analytical_stored_energy_j": round(energy_j, 5),
    }


def build_and_verify(out_dir: Path | None = None) -> dict[str, Any]:
    od = Path(out_dir) if out_dir is not None else OUT_DIR
    od.mkdir(parents=True, exist_ok=True)

    spec = build_safety_interlock_1oo2d_board()
    board_res = verify_board_bundle(spec, od)

    cir_path = od / "safety_1oo2d_crowbar.cir"
    cir_path.write_text(render_safety_1oo2d_ngspice_deck(), encoding="utf-8")
    sp_res = run_ngspice(cir_path, workdir=od)
    ana_res = run_analytical_crosscheck()

    m = sp_res.metrics
    t50_nom = float(m.get("hv_nom_t50_ms", 999.0))
    t50_flt = float(m.get("hv_flt_t50_ms", 999.0))
    e_nom = float(m.get("hv_nom_energy_j", 0.0))
    e_flt = float(m.get("hv_flt_energy_j", 0.0))
    sh_v_safe = abs(float(m.get("sh_v_safe", 999.0)))
    sh_i_safe = abs(float(m.get("sh_i_safe", 999.0)))
    sh_drop_ms = float(m.get("sh_drop_ms", 999.0))
    disc_v = float(m.get("discrep_fault_v", 0.0))
    ow_v_safe = abs(float(m.get("ow_v_safe", 999.0)))

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
        "epistemic_not_certified_locked": (
            spec.epistemic_meta["iec61508_certified"] is False
            and spec.epistemic_meta["semi_s2_certified"] is False
            and spec.epistemic_meta["requires_third_party_assessment"] is True
            and spec.epistemic_meta["certification_status"] == "DESIGN_ONLY_NOT_CERTIFIED"
        ),
        "hv_nom_discharge_lt_50ms": 15.0 < t50_nom < 50.0,
        "hv_nom_matches_analytical_18p26ms": abs(t50_nom - ana_res["analytical_t_50v_ms"]) < 0.5,
        "hv_energy_lt_0p5j": 0.30 < e_nom < 0.50 and abs(e_nom - ana_res["analytical_stored_energy_j"]) < 0.01,
        "fault_cha_crowbar_stuck_open_still_safe_lt_50ms": 15.0 < t50_flt < 50.0 and abs(e_flt - e_nom) < 0.01,
        "fault_cha_relay_welded_shutter_still_safe": sh_v_safe < 0.05 and sh_i_safe < 1e-4 and 0.0 < sh_drop_ms < 3.2,
        "fault_discrepancy_comparator_triggered": disc_v > 4.5,
        "fault_open_wire_sensor_deenergizes_safe": ow_v_safe < 0.05,
    }

    report = {
        "suite": "safety_interlock_1oo2d",
        "bom_ids": list(spec.bom_ids),
        "epistemic_meta": dict(spec.epistemic_meta),
        "iec61508_certified": False,
        "semi_s2_certified": False,
        "requires_third_party_assessment": True,
        "certification_status": "DESIGN_ONLY_NOT_CERTIFIED",
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
                "hv_22kv_nom_t50v_ms": round(t50_nom, 4),
                "hv_22kv_nom_energy_j": round(e_nom, 5),
                "hv_22kv_nom_v_at_40ms_v": round(float(m.get("hv_nom_v_at_40m", 999.0)), 4),
                "hv_22kv_fault_cha_stuck_open_t50v_ms": round(t50_flt, 4),
                "hv_22kv_fault_cha_stuck_open_energy_j": round(e_flt, 5),
                "shutter_fault_cha_welded_v_safe_v": round(sh_v_safe, 6),
                "shutter_fault_cha_welded_drop_ms": round(sh_drop_ms, 4),
                "discrepancy_fault_asserted_v": round(disc_v, 3),
                "open_wire_estop_load_v_safe_v": round(ow_v_safe, 6),
            },
        },
        "analytical_crosscheck": ana_res,
        "checks": checks,
        "all_passed": all(checks.values()),
    }
    (od / "safety_interlock_1oo2d_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
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
        "epistemic_meta": res["epistemic_meta"],
        "ngspice_summary": res["ngspice"]["summary"],
        "analytical_crosscheck": res["analytical_crosscheck"],
        "checks": res["checks"],
    }, indent=2))
    if not res["all_passed"]:
        print("ERC errors:", res["board"]["erc"]["errors"][:10])
        print("DRC errors:", res["board"]["drc"]["errors"][:10])
        print("SPICE errors:", res["ngspice"]["errors"][:10])
        raise SystemExit(1)
