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
  * S7.SAFETY-05: Cleanroom O2 < 19.5% OSHA ODH comparator & quench fault input.
  * S7.SAFETY-06: <80 ms fail-close spring-return UHV gate-valve solenoid driver.
  * S7.SAFETY-01: Dual 0.02 ppm / 0.05 ppm PH3 4-20 mA live-zero window comparators.
  * S7.4-04:      Machine safety interlock PLC/FPGA opto-isolated 3.3 V interface (UHV > 1e-8 Torr trip).
  * S5.5-04:      MXC < 1 K live-zero thermal trip & <0.1 ms laser crowbar dual-enable outputs.
  * RTL Parity:   rtl/machine_ctrl/uhv_interlock_fsm.v (ch_a_ok, ch_b_ok, wdt_kick, safe_*_en).

Architecture (Rev v2.0 — Root-Cause Obstacle Closure OBS-051, OBS-052, OBS-053, OBS-087):
  * 4-layer Isola FR408HR (er=3.66, CTI>=600 MG-I), 312 x 190 mm.
  * 4-20 mA live-zero (<3.5 mA open-wire fail-safe trip) window comparators on PH3, MXC, UHV, and O2;
    O2 trip threshold raised to 19.57% O2 (VREF_O2 = 4.130 V >= 4.12 V OSHA 19.5% limit);
    10 kOhm V_5V_A pull-ups on all LM2903DR open-collector outputs.
  * Diverse Ch-A (LM2903DR + SN74LVC1G08 + low-side 2N7002K 24 V coil drivers + 10-pin Omron
    G7SA-3A1B-DC24 force-guided safety relays) & Ch-B (MAX9032 + CD4081B + 470R LED-limited
    CPC1017N opto-SSRs + 12 V Zener-clamped SQJ461EP high-side P-MOSFETs).
  * Independent OR-ed diagnostic/WDT 5 V rail (U_REG_5V_DIAG, TSOT-23-5 ADP7142AUJZ-5.0) coupled
    to Ch-A and Ch-B via dual optocoupler U_OPTO_WDT_AB (eliminating single-rail V_5V_A CCF);
    33 ms RC discrepancy blanking filter preventing 10 ms relay/SSR turn-on skew nuisance trips;
    full opto-isolation to 3.3 V FPGA header J_FPGA_ILK (zero 24 V or cross-domain ties);
    HV_SAFE_CLAMP_3V3 active-HIGH=CLAMP aligned with spi_dac_hv_ctrl.v.
  * Isolated 22 kV active 2.00 MOhm HV crowbar bay with THREE milled Edge.Cuts air-slots enforcing
    >= 30 mm clearance & >= 50 mm creepage across BOTH HV-to-LV AND open-switch relay contacts
    (K_CROWBAR_A/B HV_22KV_BUS vs HV_22KV_DUMP), auxiliary contact feedback on K_CROWBAR_A/B,
    and dedicated bolted M6 PE star lug (zero SMD jumper to signal ground).
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
    "architecture_target": "1oo2D_de_energize_to_trip_live_zero_window",
    "hv_crowbar_rating_V": 22000.0,
    "o2_trip_threshold_pct": 19.57,
    "live_zero_trip_mA": 3.54,
    "discrepancy_blanking_ms": 33.0,
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
    """LM2903DR (Ch-A, open-collector) / MAX9032 (Ch-B, push-pull) dual comparator (SOIC-8)."""
    names = {"1": "OUT1", "2": "IN1-", "3": "IN1+", "4": "GND", "5": "IN2+", "6": "IN2-", "7": "OUT2", "8": "VCC"}
    types = {
        "1": "output", "2": "input", "3": "input", "4": "power_in",
        "5": "input", "6": "input", "7": "output", "8": "power_in",
    }
    return auto_footprint_pads("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", [str(i) for i in range(1, 9)], names, types)


def _fg_relay_g7sa_10p_pins() -> tuple[PinSpec, ...]:
    """Omron G7SA-3A1B-DC24 IEC 61810-3 force-guided safety relay (EXACT 10-pin THT: coil + 3x NO + 1x NC mirror)."""
    return (
        PinSpec("1", "COIL_A1", "input", -10.16, -5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("2", "COIL_A2", "input", -10.16, 5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("3", "NO1_13", "passive", -5.08, -5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("4", "NO1_14", "passive", -5.08, 5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("5", "NO2_23", "passive", 0.0, -5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("6", "NO2_24", "passive", 0.0, 5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("7", "NO3_33", "passive", 5.08, -5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("8", "NO3_34", "passive", 5.08, 5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("9", "NC_MIR_41", "passive", 10.16, -5.08, 1.80, 1.80, drill_mm=1.00),
        PinSpec("10", "NC_MIR_42", "passive", 10.16, 5.08, 1.80, 1.80, drill_mm=1.00),
    )


def _ssr_opto_soic4_pins() -> tuple[PinSpec, ...]:
    """CPC1017N solid-state opto-SSR driver / TLP291 single optocoupler (SOP-4)."""
    return (
        PinSpec("1", "LED_A", "input", -2.54, -1.27, 1.20, 0.70),
        PinSpec("2", "LED_K", "input", -2.54, 1.27, 1.20, 0.70),
        PinSpec("3", "OUT_B", "passive", 2.54, 1.27, 1.20, 0.70),
        PinSpec("4", "OUT_A", "passive", 2.54, -1.27, 1.20, 0.70),
    )


def _dual_opto_so8_pins() -> tuple[PinSpec, ...]:
    """TLP291-2 dual channel optocoupler (SOIC-8)."""
    names = {
        "1": "LED1_A", "2": "LED1_K", "3": "LED2_A", "4": "LED2_K",
        "5": "E2", "6": "C2", "7": "E1", "8": "C1",
    }
    types = {
        "1": "input", "2": "input", "3": "input", "4": "input",
        "5": "passive", "6": "passive", "7": "passive", "8": "passive",
    }
    return auto_footprint_pads("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", [str(i) for i in range(1, 9)], names, types)


def _pmos_dpak_pins() -> tuple[PinSpec, ...]:
    """SQJ461EP high-side P-MOSFET safety cutoff switch (TO-252-3 / DPAK)."""
    return (
        PinSpec("1", "G", "input", -2.28, 2.50, 1.20, 1.60),
        PinSpec("2", "D", "passive", 0.0, -2.50, 3.00, 2.20),
        PinSpec("3", "S", "passive", 2.28, 2.50, 1.20, 1.60),
    )


def _nmos_sot23_3_pins() -> tuple[PinSpec, ...]:
    """2N7002K low-side N-MOSFET 24 V relay coil driver (SOT-23-3)."""
    return (
        PinSpec("1", "G", "input", -1.10, -0.95, 0.80, 0.60),
        PinSpec("2", "S", "passive", -1.10, 0.95, 0.80, 0.60),
        PinSpec("3", "D", "passive", 1.10, 0.0, 0.80, 0.60),
    )


def _logic_sot23_5_pins() -> tuple[PinSpec, ...]:
    names = {"1": "A", "2": "B", "3": "GND", "4": "Y", "5": "VCC"}
    types = {"1": "input", "2": "input", "3": "power_in", "4": "output", "5": "power_in"}
    return auto_footprint_pads("Package_TO_SOT_SMD:SOT-23-5", [str(i) for i in range(1, 6)], names, types)


def _adp7142_tsot23_5_pins() -> tuple[PinSpec, ...]:
    """ADP7142AUJZ-5.0 fixed-output LDO (EXACT 5-lead TSOT-23-5 / UJ-5, zero RSET!)."""
    names = {"1": "VIN", "2": "GND", "3": "EN", "4": "SENSE", "5": "VOUT"}
    types = {"1": "power_in", "2": "power_in", "3": "input", "4": "input", "5": "power_out"}
    return auto_footprint_pads("Package_TO_SOT_SMD:TSOT-23-5", ["1", "2", "3", "4", "5"], names, types)


def _wdt_sot23_6_pins() -> tuple[PinSpec, ...]:
    """TPS3850 hardware window watchdog supervisor (SOT-23-6)."""
    names = {"1": "WDO_N", "2": "GND", "3": "WDI", "4": "SET0", "5": "SET1", "6": "VDD"}
    types = {"1": "output", "2": "power_in", "3": "input", "4": "input", "5": "input", "6": "power_in"}
    return auto_footprint_pads("Package_TO_SOT_SMD:SOT-23-6", [str(i) for i in range(1, 7)], names, types)


def _ldo_sot223_pins() -> tuple[PinSpec, ...]:
    """LM2936MP-5.0 automotive-grade 40 V LDO (SOT-223-4)."""
    return (
        PinSpec("1", "VIN", "power_in", -2.30, 2.50, 1.10, 1.60),
        PinSpec("2", "GND", "power_in", 0.0, 2.50, 1.10, 1.60),
        PinSpec("3", "VOUT", "power_out", 2.30, 2.50, 1.10, 1.60),
        PinSpec("4", "TAB_GND", "power_in", 0.0, -2.50, 2.60, 1.60),
    )


def _hv22k_turret_pin() -> tuple[PinSpec, ...]:
    return (PinSpec("1", "HV_22KV", "passive", 0.0, 0.0, 2.60, 2.60, drill_mm=1.30),)


def _pe_m6_lug_pin() -> tuple[PinSpec, ...]:
    """Dedicated M6 bolted chassis PE star return ring-terminal lug (zero SMD tie!)."""
    return (PinSpec("1", "CHASSIS_PE_M6", "power_in", 0.0, 0.0, 6.20, 6.20, drill_mm=3.20),)


def _hv22k_relay_nc_wide_pins() -> tuple[PinSpec, ...]:
    """25 kV NC HV Vacuum Relay (Gigavac G81C-25KV / Ross E25) with wide-spaced HV contacts + aux mirror:
    * Pin 1 (HV_COM = 22 kV BUS)  @ dy = -48.0 mm (top HV island)
    * Pin 2 (HV_NC  = 22 kV DUMP) @ dy =  -4.0 mm (44 mm pitch across milled slot -> >=41.6 mm clr, >=58 mm crp!)
    * Pins 3-4 (24 V COIL_P/N)    @ dy = +48.0 mm (52 mm below HV_NC across 2nd milled slot!)
    * Pins 5-6 (AUX_MIR_A/B)      @ dy = +56.0 mm (mechanically linked auxiliary diagnostic feedback)
    """
    return (
        PinSpec("1", "HV_COM", "passive", 0.0, -48.0, 2.40, 2.40, drill_mm=1.20),
        PinSpec("2", "HV_NC", "passive", 0.0, -4.0, 2.40, 2.40, drill_mm=1.20),
        PinSpec("3", "COIL_P", "input", -3.5, 48.0, 1.80, 1.80, drill_mm=0.90),
        PinSpec("4", "COIL_N", "input", 3.5, 48.0, 1.80, 1.80, drill_mm=0.90),
        PinSpec("5", "AUX_A", "passive", -3.5, 56.0, 1.80, 1.80, drill_mm=0.90),
        PinSpec("6", "AUX_B", "passive", 3.5, 56.0, 1.80, 1.80, drill_mm=0.90),
    )


def _hv22k_res_vertical_pins() -> tuple[PinSpec, ...]:
    """Ohmite MOX-4-25KV 1.00 MOhm 25 kV non-inductive HV resistor straddling 22 kV air-slot (52 mm pitch)."""
    return (
        PinSpec("1", "HV_TOP", "passive", 0.0, -26.0, 2.40, 2.40, drill_mm=1.20),
        PinSpec("2", "HV_BOT", "passive", 0.0, 26.0, 2.40, 2.40, drill_mm=1.20),
    )


def _hv22k_res_horiz_pins() -> tuple[PinSpec, ...]:
    return (
        PinSpec("1", "HV_A", "passive", -10.0, 0.0, 2.40, 2.40, drill_mm=1.20),
        PinSpec("2", "HV_B", "passive", 10.0, 0.0, 2.40, 2.40, drill_mm=1.20),
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
    # SECTION 1 (LEFT EDGE, x=10..34 mm): DUAL 24 V UPS POWER, INDEPENDENT DIAG RAIL & FIELD SENSORS
    # =========================================================================
    j_pwr = add_c(ComponentSpec(
        "JPWR_24V_UPS", "TERM_4P_DUAL_24V_UPS", "Connector_PinHeader:HDR_1x4_5.08mm",
        10.0, 18.0, pins=auto_footprint_pads("HDR_1x4_5.08mm", ("1", "2", "3", "4"),
                                             {"1": "V24_UPS_A", "2": "GND_A", "3": "V24_UPS_B", "4": "GND_B"}),
        bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
    ))
    # Diverse 5 V regulators: Ch-A (LM2936MP-5.0 SOT-223), Ch-B (ADP7142AUJZ-5.0 TSOT-23-5!),
    # plus Independent Diagnostic/WDT 5 V rail fed by diode-OR of V_24V_A & V_24V_B (breaks V_5V_A CCF!)
    u_reg_a = add_c(ComponentSpec("U_REG_5V_A", "LM2936MP-5.0_CHA", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", 24.0, 14.0, pins=_ldo_sot223_pins(), mpn="LM2936MP-5.0", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_reg_b = add_c(ComponentSpec("U_REG_5V_B", "ADP7142AUJZ-5.0_CHB", "Package_TO_SOT_SMD:TSOT-23-5", 24.0, 174.0, pins=_adp7142_tsot23_5_pins(), mpn="ADP7142AUJZ-5.0", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    d_or_a = add_c(ComponentSpec("D_OR_DIAG_A", "SS34_DIAG_OR_A", "Diode_SMD:D_0805_2012Metric", 22.0, 88.0, pins=auto_footprint_pads("0805", ("1", "2"), {"1": "A", "2": "K"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    d_or_b = add_c(ComponentSpec("D_OR_DIAG_B", "SS34_DIAG_OR_B", "Diode_SMD:D_0805_2012Metric", 22.0, 96.0, pins=auto_footprint_pads("0805", ("1", "2"), {"1": "A", "2": "K"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    u_reg_diag = add_c(ComponentSpec("U_REG_5V_DIAG", "ADP7142AUJZ-5.0_DIAG", "Package_TO_SOT_SMD:TSOT-23-5", 32.0, 92.0, pins=_adp7142_tsot23_5_pins(), mpn="ADP7142AUJZ-5.0", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))

    # 4x Dual-NC E-Stop Mushroom Loop Connectors (S7.SAFETY-03, wired in series A1->A4 and B1->B4!)
    for idx in range(1, 5):
        ye = round(38.0 + (idx - 1) * 16.0, 1)
        je = add_c(ComponentSpec(
            f"J_ESTOP{idx}", f"TERM_4P_ESTOP_MUSHROOM_{idx}", "Connector_PinHeader:HDR_1x4_2.54mm",
            10.0, ye, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
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
    r_es_pda = add_c(ComponentSpec("R_ESTOP_PD_A", "10.0k_1pct", "Resistor_SMD:R_0805_2012Metric", 22.0, 62.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_es_pdb = add_c(ComponentSpec("R_ESTOP_PD_B", "10.0k_1pct", "Resistor_SMD:R_0805_2012Metric", 22.0, 110.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    conn("ESTOP_LOOP_A", r_es_pda.ref, 1); conn("GND_A", r_es_pda.ref, 2)
    conn("ESTOP_LOOP_B", r_es_pdb.ref, 1); conn("GND_B", r_es_pdb.ref, 2)

    # Field Sensor Connectors (4-20 mA live-zero loops on PH3, O2, MXC, UHV + Door/Quench NC)
    j_ph3 = add_c(ComponentSpec(
        "J_PH3_SENS", "TERM_4P_PH3_4_20MA_DUAL", "Connector_PinHeader:HDR_1x4_2.54mm",
        10.0, 118.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                              {"1": "PH3_4_20_A", "2": "GND_A", "3": "PH3_4_20_B", "4": "GND_B"}),
        bom_id="S7.SAFETY-01", epistemic_tag="{Pasif-COTS}",
    ))
    j_o2 = add_c(ComponentSpec(
        "J_O2_SENS", "TERM_4P_O2_19p5PCT_DUAL", "Connector_PinHeader:HDR_1x4_2.54mm",
        10.0, 134.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                              {"1": "O2_4_20_A", "2": "GND_A", "3": "O2_4_20_B", "4": "GND_B"}),
        bom_id="S7.SAFETY-05", epistemic_tag="{Pasif-COTS}",
    ))
    j_mxc_uhv = add_c(ComponentSpec(
        "J_MXC_UHV_SENS", "TERM_6P_MXC1K_UHV1E8_4_20MA", "Connector_PinHeader:HDR_1x6_2.54mm",
        10.0, 156.0, pins=auto_footprint_pads("HDR_1x6_2.54mm", ("1", "2", "3", "4", "5", "6"),
                                              {"1": "MXC_4_20_A", "2": "MXC_4_20_B", "3": "UHV_4_20_A", "4": "UHV_4_20_B", "5": "DOOR_QUENCH_A", "6": "DOOR_QUENCH_B"}),
        bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}",
    ))

    # =========================================================================
    # SECTION 2 (x=36..106 mm): DUAL-CHANNEL 4-20 mA LIVE-ZERO WINDOW COMPARATORS
    #   OBS-053 FIX:
    #   * 250 Ohm 0.1% burden on ALL 4 sensor loops (PH3, O2, MXC, UHV -> 4-20 mA = 1.00..5.00 V)
    #   * Live-zero under-range comparator VREF_LZ = 5.0 * 2.15k/(10k+2.15k) = 0.8848 V (3.54 mA):
    #     open-wire 0 mA -> 0 V < 0.885 V -> trips SAFE!
    #   * O2 threshold raised: VREF_O2 = 5.0 * 47.5k/(10k+47.5k) = 4.1304 V (16.52 mA = 19.57% O2 >= 19.5% OSHA!)
    #   * Ch-A LM2903DR open-collector outputs ALL have 10.0k pull-ups to V_5V_A (wired-AND window!)
    #   * Ch-B MAX9032 push-pull window outputs combined via dedicated CD4081B window AND gates!
    # =========================================================================
    for ch, gnd, v5, yc_base, cmp_mpn, cmp_val in (
        ("A", "GND_A", "V_5V_A", 18.0, "LM2903DR",  "LM2903_WINDOW_CHA"),
        ("B", "GND_B", "V_5V_B", 112.0, "MAX9032AKA", "MAX9032_WINDOW_CHB"),
    ):
        # 250 Ohm 0.1% burden resistors on PH3, O2, MXC, UHV (live-zero 4-20 mA -> 1.0..5.0 V; open wire -> 0 V!)
        rb_ph3 = add_c(ComponentSpec(f"R_BURD_PH3_{ch}", "250R_0.1pct_4_20MA", "Resistor_SMD:R_0805_2012Metric", 38.0, yc_base, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-01", epistemic_tag="{Pasif-COTS}"))
        rb_o2 = add_c(ComponentSpec(f"R_BURD_O2_{ch}", "250R_0.1pct_4_20MA", "Resistor_SMD:R_0805_2012Metric", 38.0, yc_base + 14.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-05", epistemic_tag="{Pasif-COTS}"))
        rb_mxc = add_c(ComponentSpec(f"R_BURD_MXC_{ch}", "250R_0.1pct_4_20MA", "Resistor_SMD:R_0805_2012Metric", 38.0, yc_base + 28.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
        rb_uhv = add_c(ComponentSpec(f"R_BURD_UHV_{ch}", "250R_0.1pct_4_20MA", "Resistor_SMD:R_0805_2012Metric", 38.0, yc_base + 42.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.4-04", epistemic_tag="{Pasif-COTS}"))

        # Precision reference dividers: PH3 (1.664V), O2 (4.130V = 19.57% OSHA!), MXC (2.500V), UHV (3.000V), Live-Zero (0.885V = 3.54 mA!)
        r_ref_ph3_t = add_c(ComponentSpec(f"R_REF_PH3_T{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 46.0, yc_base - 4.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-01", epistemic_tag="{Pasif-COTS}"))
        r_ref_ph3_b = add_c(ComponentSpec(f"R_REF_PH3_B{ch}", "4.99k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 46.0, yc_base + 2.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-01", epistemic_tag="{Pasif-COTS}"))
        r_ref_o2_t = add_c(ComponentSpec(f"R_REF_O2_T{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 46.0, yc_base + 10.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-05", epistemic_tag="{Pasif-COTS}"))
        r_ref_o2_b = add_c(ComponentSpec(f"R_REF_O2_B{ch}", "47.5k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 46.0, yc_base + 16.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-05", epistemic_tag="{Pasif-COTS}"))
        r_ref_mxc_t = add_c(ComponentSpec(f"R_REF_MXC_T{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 46.0, yc_base + 24.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
        r_ref_mxc_b = add_c(ComponentSpec(f"R_REF_MXC_B{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 46.0, yc_base + 30.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
        r_ref_uhv_t = add_c(ComponentSpec(f"R_REF_UHV_T{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 46.0, yc_base + 38.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.4-04", epistemic_tag="{Pasif-COTS}"))
        r_ref_uhv_b = add_c(ComponentSpec(f"R_REF_UHV_B{ch}", "15.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 46.0, yc_base + 44.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.4-04", epistemic_tag="{Pasif-COTS}"))
        r_ref_lz_t = add_c(ComponentSpec(f"R_REF_LZ_T{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 46.0, yc_base + 52.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
        r_ref_lz_b = add_c(ComponentSpec(f"R_REF_LZ_B{ch}", "2.15k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 46.0, yc_base + 58.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

        # Dual Comparators:
        # U_CMP_GAS: PH3 high-limit (V_PH3 < VREF_PH3) + O2 OSHA low-limit (V_O2 > VREF_O2 = 4.130V = 19.57%)
        # U_CMP_VAC: MXC high-limit (V_MXC < VREF_MXC) + UHV high-limit (V_UHV < VREF_UHV)
        # U_CMP_LZ1: PH3 live-zero (V_PH3 > VREF_LZ = 0.885V) + MXC live-zero (V_MXC > VREF_LZ)
        # U_CMP_LZ2: UHV live-zero (V_UHV > VREF_LZ) + O2 live-zero (V_O2 > VREF_LZ)
        u_cmp1 = add_c(ComponentSpec(f"U_CMP_GAS_{ch}", cmp_val, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 58.0, yc_base + 4.0, pins=_dual_cmp_soic8_pins(), mpn=cmp_mpn, bom_id="S7.SAFETY-01", epistemic_tag="{Aday-COTS}"))
        u_cmp2 = add_c(ComponentSpec(f"U_CMP_VAC_{ch}", cmp_val, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 58.0, yc_base + 24.0, pins=_dual_cmp_soic8_pins(), mpn=cmp_mpn, bom_id="S7.4-04", epistemic_tag="{Aday-COTS}"))
        u_cmp_lz1 = add_c(ComponentSpec(f"U_CMP_LZ1_{ch}", cmp_val, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 58.0, yc_base + 42.0, pins=_dual_cmp_soic8_pins(), mpn=cmp_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
        u_cmp_lz2 = add_c(ComponentSpec(f"U_CMP_LZ2_{ch}", cmp_val, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 58.0, yc_base + 56.0, pins=_dual_cmp_soic8_pins(), mpn=cmp_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))

        # Wire burdens & reference dividers
        conn(f"PH3_SENS_{ch}", rb_ph3.ref, 1); conn(gnd, rb_ph3.ref, 2)
        conn(f"O2_SENS_{ch}", rb_o2.ref, 1); conn(gnd, rb_o2.ref, 2)
        conn(f"MXC_SENS_{ch}", rb_mxc.ref, 1); conn(gnd, rb_mxc.ref, 2)
        conn(f"UHV_SENS_{ch}", rb_uhv.ref, 1); conn(gnd, rb_uhv.ref, 2)
        conn(v5, r_ref_ph3_t.ref, 1); conn(f"VREF_PH3_{ch}", r_ref_ph3_t.ref, 2); conn(f"VREF_PH3_{ch}", r_ref_ph3_b.ref, 1); conn(gnd, r_ref_ph3_b.ref, 2)
        conn(v5, r_ref_o2_t.ref, 1); conn(f"VREF_O2_{ch}", r_ref_o2_t.ref, 2); conn(f"VREF_O2_{ch}", r_ref_o2_b.ref, 1); conn(gnd, r_ref_o2_b.ref, 2)
        conn(v5, r_ref_mxc_t.ref, 1); conn(f"VREF_MXC_{ch}", r_ref_mxc_t.ref, 2); conn(f"VREF_MXC_{ch}", r_ref_mxc_b.ref, 1); conn(gnd, r_ref_mxc_b.ref, 2)
        conn(v5, r_ref_uhv_t.ref, 1); conn(f"VREF_UHV_{ch}", r_ref_uhv_t.ref, 2); conn(f"VREF_UHV_{ch}", r_ref_uhv_b.ref, 1); conn(gnd, r_ref_uhv_b.ref, 2)
        conn(v5, r_ref_lz_t.ref, 1); conn(f"VREF_LZ_{ch}", r_ref_lz_t.ref, 2); conn(f"VREF_LZ_{ch}", r_ref_lz_b.ref, 1); conn(gnd, r_ref_lz_b.ref, 2)

        for uc in (u_cmp1, u_cmp2, u_cmp_lz1, u_cmp_lz2):
            conn(v5, uc.ref, 8); conn(gnd, uc.ref, 4)

        # Comparator inputs:
        # High-limit: IN+ = VREF, IN- = SENS (HIGH when SENS < VREF)
        # Live-zero & O2 low-limit: IN+ = SENS, IN- = VREF (HIGH when SENS > VREF; 0 V open-wire -> LOW!)
        conn(f"VREF_PH3_{ch}", u_cmp1.ref, 3); conn(f"PH3_SENS_{ch}", u_cmp1.ref, 2)
        conn(f"O2_SENS_{ch}", u_cmp1.ref, 5); conn(f"VREF_O2_{ch}", u_cmp1.ref, 6)
        conn(f"VREF_MXC_{ch}", u_cmp2.ref, 3); conn(f"MXC_SENS_{ch}", u_cmp2.ref, 2)
        conn(f"VREF_UHV_{ch}", u_cmp2.ref, 5); conn(f"UHV_SENS_{ch}", u_cmp2.ref, 6)
        conn(f"PH3_SENS_{ch}", u_cmp_lz1.ref, 3); conn(f"VREF_LZ_{ch}", u_cmp_lz1.ref, 2)
        conn(f"MXC_SENS_{ch}", u_cmp_lz1.ref, 5); conn(f"VREF_LZ_{ch}", u_cmp_lz1.ref, 6)
        conn(f"UHV_SENS_{ch}", u_cmp_lz2.ref, 3); conn(f"VREF_LZ_{ch}", u_cmp_lz2.ref, 2)
        conn(f"O2_SENS_{ch}", u_cmp_lz2.ref, 5); conn(f"VREF_LZ_{ch}", u_cmp_lz2.ref, 6)

        v_mpn = "SN74LVC1G08DBVR" if ch == "A" else "CD4081B_DIVERSE"
        if ch == "A":
            # Open-collector LM2903DR: wired-AND window comparators with mandatory 10k pull-ups to V_5V_A!
            conn("PH3_OK_A", u_cmp1.ref, 1); conn("PH3_OK_A", u_cmp_lz1.ref, 1)
            conn("O2_OK_A", u_cmp1.ref, 7); conn("O2_OK_A", u_cmp_lz2.ref, 7)
            conn("MXC_OK_A", u_cmp2.ref, 1); conn("MXC_OK_A", u_cmp_lz1.ref, 7)
            conn("UHV_OK_A", u_cmp2.ref, 7); conn("UHV_OK_A", u_cmp_lz2.ref, 1)
            for idx_pu, onet in enumerate(("PH3_OK_A", "O2_OK_A", "MXC_OK_A", "UHV_OK_A")):
                rpu = add_c(ComponentSpec(f"R_PU_{onet}", "10.0k_1pct_OC_PU", "Resistor_SMD:R_0603_1608Metric", 68.0, yc_base + idx_pu * 14.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
                conn(v5, rpu.ref, 1); conn(onet, rpu.ref, 2)
        else:
            # Push-pull MAX9032 (Ch-B): combine high-limit & live-zero outputs via CD4081B window AND gates!
            conn("PH3_HI_OK_B", u_cmp1.ref, 1); conn("PH3_LZ_OK_B", u_cmp_lz1.ref, 1)
            conn("O2_LO_OK_B", u_cmp1.ref, 7); conn("O2_LZ_OK_B", u_cmp_lz2.ref, 7)
            conn("MXC_HI_OK_B", u_cmp2.ref, 1); conn("MXC_LZ_OK_B", u_cmp_lz1.ref, 7)
            conn("UHV_HI_OK_B", u_cmp2.ref, 7); conn("UHV_LZ_OK_B", u_cmp_lz2.ref, 1)
            for idx_w, (na, nb, ny) in enumerate((
                ("PH3_HI_OK_B", "PH3_LZ_OK_B", "PH3_OK_B"),
                ("O2_LO_OK_B", "O2_LZ_OK_B", "O2_OK_B"),
                ("MXC_HI_OK_B", "MXC_LZ_OK_B", "MXC_OK_B"),
                ("UHV_HI_OK_B", "UHV_LZ_OK_B", "UHV_OK_B"),
            )):
                uw = add_c(ComponentSpec(f"U_WIN_{ny}", f"AND_WIN_{v_mpn}", "Package_TO_SOT_SMD:SOT-23-5", 68.0, yc_base + idx_w * 14.0, pins=_logic_sot23_5_pins(), mpn=v_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
                conn(na, uw.ref, 1); conn(nb, uw.ref, 2); conn(ny, uw.ref, 4); conn(v5, uw.ref, 5); conn(gnd, uw.ref, 3)

        # Diverse Hardware Voting AND Cascade per Channel (Ch-A: SN74LVC1G08, Ch-B: CD4081B)
        u_v1 = add_c(ComponentSpec(f"U_VOTE1_{ch}", f"AND_GAS_{v_mpn}", "Package_TO_SOT_SMD:SOT-23-5", 80.0, yc_base + 4.0, pins=_logic_sot23_5_pins(), mpn=v_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
        u_v2 = add_c(ComponentSpec(f"U_VOTE2_{ch}", f"AND_VAC_{v_mpn}", "Package_TO_SOT_SMD:SOT-23-5", 80.0, yc_base + 22.0, pins=_logic_sot23_5_pins(), mpn=v_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
        u_v3 = add_c(ComponentSpec(f"U_VOTE3_{ch}", f"AND_ESTOP_{v_mpn}", "Package_TO_SOT_SMD:SOT-23-5", 80.0, yc_base + 40.0, pins=_logic_sot23_5_pins(), mpn=v_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
        u_v4 = add_c(ComponentSpec(f"U_VOTE4_{ch}", f"AND_SENS_{v_mpn}", "Package_TO_SOT_SMD:SOT-23-5", 92.0, yc_base + 14.0, pins=_logic_sot23_5_pins(), mpn=v_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
        u_v5 = add_c(ComponentSpec(f"U_VOTE5_{ch}", f"AND_WDT_DISC_{v_mpn}", "Package_TO_SOT_SMD:SOT-23-5", 92.0, yc_base + 34.0, pins=_logic_sot23_5_pins(), mpn=v_mpn, bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))

        conn(f"PH3_OK_{ch}", u_v1.ref, 1); conn(f"O2_OK_{ch}", u_v1.ref, 2); conn(f"GAS_OK_{ch}", u_v1.ref, 4); conn(v5, u_v1.ref, 5); conn(gnd, u_v1.ref, 3)
        conn(f"MXC_OK_{ch}", u_v2.ref, 1); conn(f"UHV_OK_{ch}", u_v2.ref, 2); conn(f"VAC_OK_{ch}", u_v2.ref, 4); conn(v5, u_v2.ref, 5); conn(gnd, u_v2.ref, 3)
        conn(f"ESTOP_LOOP_{ch}", u_v3.ref, 1); conn(f"DOOR_QUENCH_{ch}", u_v3.ref, 2); conn(f"ES_DR_OK_{ch}", u_v3.ref, 4); conn(v5, u_v3.ref, 5); conn(gnd, u_v3.ref, 3)
        conn(f"GAS_OK_{ch}", u_v4.ref, 1); conn(f"VAC_OK_{ch}", u_v4.ref, 2); conn(f"SENS_ALL_OK_{ch}", u_v4.ref, 4); conn(v5, u_v4.ref, 5); conn(gnd, u_v4.ref, 3)
        conn(f"SENS_ALL_OK_{ch}", u_v5.ref, 1); conn(f"ES_DR_OK_{ch}", u_v5.ref, 2); conn(f"CH_PRE_VOTE_{ch}", u_v5.ref, 4); conn(v5, u_v5.ref, 5); conn(gnd, u_v5.ref, 3)

    # Final Channel Gate combining Pre-Vote AND Galvanically Isolated WDT_DIAG_OK_A / WDT_DIAG_OK_B!
    u_fin_a = add_c(ComponentSpec("U_FINAL_A", "SN74LVC1G08_FINAL_A", "Package_TO_SOT_SMD:SOT-23-5", 104.0, 42.0, pins=_logic_sot23_5_pins(), mpn="SN74LVC1G08DBVR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_fin_b = add_c(ComponentSpec("U_FINAL_B", "CD4081B_FINAL_B", "Package_TO_SOT_SMD:SOT-23-5", 104.0, 140.0, pins=_logic_sot23_5_pins(), mpn="CD4081B", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    conn("CH_PRE_VOTE_A", u_fin_a.ref, 1); conn("WDT_DIAG_OK_A", u_fin_a.ref, 2); conn("VOTE_SAFE_A", u_fin_a.ref, 4); conn("V_5V_A", u_fin_a.ref, 5); conn("GND_A", u_fin_a.ref, 3)
    conn("CH_PRE_VOTE_B", u_fin_b.ref, 1); conn("WDT_DIAG_OK_B", u_fin_b.ref, 2); conn("VOTE_SAFE_B", u_fin_b.ref, 4); conn("V_5V_B", u_fin_b.ref, 5); conn("GND_B", u_fin_b.ref, 3)

    # =========================================================================
    # SECTION 3 (CENTER, x=44..120 mm, y=78..106 mm): INDEPENDENT DIAGNOSTIC ISLAND,
    #   33 ms RELAY/SSR SKEW BLANKING, DUAL-OPTO WDT DISTRIBUTION & OPTO-ISOLATED 3.3 V FPGA HEADER
    # =========================================================================
    u_wdt = add_c(ComponentSpec("U_WDT_WIN", "TPS3850_WINDOW_WDT", "Package_TO_SOT_SMD:SOT-23-6", 82.0, 92.0, pins=_wdt_sot23_6_pins(), mpn="TPS3850H50QDRCRQ1", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_xor_v = add_c(ComponentSpec("U_DIAG_XOR_VOTE", "SN74AHC1G86_DISCREP1", "Package_TO_SOT_SMD:SOT-23-5", 92.0, 84.0, pins=_logic_sot23_5_pins(), mpn="SN74AHC1G86DBVR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_xor_fb = add_c(ComponentSpec("U_DIAG_XOR_FB", "SN74AHC1G86_DISCREP2", "Package_TO_SOT_SMD:SOT-23-5", 92.0, 98.0, pins=_logic_sot23_5_pins(), mpn="SN74AHC1G86DBVR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_diag_nor = add_c(ComponentSpec("U_DIAG_NOR", "SN74LVC1G02_DIAG_OK", "Package_TO_SOT_SMD:SOT-23-5", 108.0, 90.0, pins=_logic_sot23_5_pins(), mpn="SN74LVC1G02DBVR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_wdt_and = add_c(ComponentSpec("U_WDT_DIAG_AND", "SN74LVC1G08_WDT_DIAG", "Package_TO_SOT_SMD:SOT-23-5", 118.0, 90.0, pins=_logic_sot23_5_pins(), mpn="SN74LVC1G08DBVR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))

    # 33 ms RC blanking filters on BOTH vote discrepancy and relay/SSR feedback discrepancy (prevents 10 ms turn-on skew nuisance trip!)
    r_disc_f = add_c(ComponentSpec("R_DISC_FILT", "33.0k_1pct", "Resistor_SMD:R_0603_1608Metric", 100.0, 80.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    c_disc_f = add_c(ComponentSpec("C_DISC_FILT", "1.0uF_16V_X7R", "Capacitor_SMD:C_0603_1608Metric", 106.0, 80.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_fb_filt = add_c(ComponentSpec("R_FB_SKEW_FILT", "33.0k_1pct_33MS_BLANK", "Resistor_SMD:R_0603_1608Metric", 100.0, 98.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    c_fb_filt = add_c(ComponentSpec("C_FB_SKEW_FILT", "1.0uF_16V_X7R", "Capacitor_SMD:C_0603_1608Metric", 106.0, 98.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

    # Dual Optocoupler isolating WDT_DIAG_OK from V_5V_DIAG into Ch-A (V_5V_A/GND_A) and Ch-B (V_5V_B/GND_B)!
    u_opto_wdt = add_c(ComponentSpec("U_OPTO_WDT_AB", "TLP291-2_WDT_ISO_AB", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 118.0, 76.0, pins=_dual_opto_so8_pins(), mpn="TLP291-2GB", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    r_wdt_la = add_c(ComponentSpec("R_WDT_LED_A", "470R_1pct", "Resistor_SMD:R_0603_1608Metric", 112.0, 70.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_wdt_lb = add_c(ComponentSpec("R_WDT_LED_B", "470R_1pct", "Resistor_SMD:R_0603_1608Metric", 112.0, 82.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_wdt_pua = add_c(ComponentSpec("R_WDT_PU_A", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", 108.0, 58.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_wdt_pub = add_c(ComponentSpec("R_WDT_PU_B", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", 118.0, 104.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

    # Opto-Isolated 3.3 V FPGA Telemetry & Watchdog Interface (ZERO 24 V or unisolated 5 V on J_FPGA_ILK!)
    j_fpga = add_c(ComponentSpec(
        "J_FPGA_ILK", "HDR_2x6_UHV_ILK_3V3_ISO", "Connector_PinHeader:HDR_2x6_2.54mm",
        44.0, 92.0, pins=auto_footprint_pads("HDR_2x6_2.54mm", [str(i) for i in range(1, 13)], {
            "1": "FPGA_WDT_KICK_3V3", "2": "WDT_OK_3V3", "3": "DISCREP_FAULT_3V3", "4": "VOTE_SAFE_A_3V3",
            "5": "VOTE_SAFE_B_3V3", "6": "DIAG_FB_A_3V3", "7": "DIAG_FB_B_3V3", "8": "HV_SAFE_CLAMP_3V3",
            "9": "V_3V3_FPGA", "10": "GND_FPGA1", "11": "GND_FPGA2", "12": "WDT_DIAG_OK_3V3",
        }),
        bom_id="S7.4-04", epistemic_tag="{Pasif-COTS}",
    ))
    u_opto_fpga_wdt = add_c(ComponentSpec("U_OPTO_FPGA_WDT", "TLP291-2_FPGA_WDT", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 56.0, 88.0, pins=_dual_opto_so8_pins(), mpn="TLP291-2GB", bom_id="S7.4-04", epistemic_tag="{Aday-COTS}"))
    u_opto_fpga_st1 = add_c(ComponentSpec("U_OPTO_FPGA_ST1", "TLP291-2_FPGA_VOTE", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 66.0, 88.0, pins=_dual_opto_so8_pins(), mpn="TLP291-2GB", bom_id="S7.4-04", epistemic_tag="{Aday-COTS}"))
    u_opto_fpga_st2 = add_c(ComponentSpec("U_OPTO_FPGA_ST2", "TLP291-2_FPGA_FB", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 74.0, 98.0, pins=_dual_opto_so8_pins(), mpn="TLP291-2GB", bom_id="S7.4-04", epistemic_tag="{Aday-COTS}"))
    u_opto_fpga_clp = add_c(ComponentSpec("U_OPTO_FPGA_CLP", "TLP291-2_FPGA_CLAMP", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 66.0, 98.0, pins=_dual_opto_so8_pins(), mpn="TLP291-2GB", bom_id="S7.4-04", epistemic_tag="{Aday-COTS}"))
    # Series LED resistors & 3.3 V pull-ups for FPGA opto channels
    for idx_f, (rname, rx, ry, val) in enumerate((
        ("R_FLED_WDTK", 50.0, 80.0, "330R_1pct"),
        ("R_FLED_WDTO", 50.0, 98.0, "470R_1pct"),
        ("R_FLED_VA", 60.0, 80.0, "470R_1pct"),
        ("R_FLED_VB", 60.0, 98.0, "470R_1pct"),
        ("R_FLED_FBA", 70.0, 80.0, "470R_1pct"),
        ("R_FLED_FBB", 70.0, 105.0, "470R_1pct"),
        ("R_FLED_CLP", 60.0, 105.0, "2.40k_1pct_24V"),
        ("R_FLED_DISC", 76.0, 80.0, "470R_1pct"),
    )):
        add_c(ComponentSpec(rname, val, "Resistor_SMD:R_0603_1608Metric", rx, ry, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.4-04", epistemic_tag="{Pasif-COTS}"))
    for idx_p, (rname, rx, ry) in enumerate((
        ("R_FPU_WDTK", 76.0, 88.0),
        ("R_FPU_WDTO", 50.0, 84.0),
        ("R_FPU_VA", 50.0, 102.0),
        ("R_FPU_VB", 54.0, 105.0),
        ("R_FPU_FBA", 48.0, 105.0),
        ("R_FPU_FBB", 42.0, 105.0),
        ("R_FPU_CLP", 36.0, 105.0),
        ("R_FPU_DISC", 42.0, 80.0),
    )):
        add_c(ComponentSpec(rname, "10.0k_1pct_3V3_PU", "Resistor_SMD:R_0603_1608Metric", rx, ry, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.4-04", epistemic_tag="{Pasif-COTS}"))

    # =========================================================================
    # SECTION 4 (x=122..188 mm): DIVERSE FINAL CUTOFF ELEMENTS & ACTUATOR OUTPUTS
    #   Ch-A (TOP): Low-side 2N7002K 24 V coil drivers + 10-pin Omron G7SA-3A1B-DC24 Force-Guided Relays
    #   Ch-B (BOT): 470R LED-limited CPC1017N Opto-SSRs + 12 V Zener-clamped SQJ461EP High-Side P-MOSFETs
    # =========================================================================
    q_drv_fg1 = add_c(ComponentSpec("Q_DRV_KFG1", "2N7002K_24V_COIL_DRV1", "Package_TO_SOT_SMD:SOT-23", 122.0, 32.0, pins=_nmos_sot23_3_pins(), mpn="2N7002K", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    q_drv_fg2 = add_c(ComponentSpec("Q_DRV_KFG2", "2N7002K_24V_COIL_DRV2", "Package_TO_SOT_SMD:SOT-23", 122.0, 58.0, pins=_nmos_sot23_3_pins(), mpn="2N7002K", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    r_g_fg1 = add_c(ComponentSpec("R_G_KFG1", "100R_1pct", "Resistor_SMD:R_0603_1608Metric", 114.0, 28.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_g_fg2 = add_c(ComponentSpec("R_G_KFG2", "100R_1pct", "Resistor_SMD:R_0603_1608Metric", 114.0, 54.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_pd_fg1 = add_c(ComponentSpec("R_PD_KFG1", "100k_1pct", "Resistor_SMD:R_0603_1608Metric", 114.0, 36.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_pd_fg2 = add_c(ComponentSpec("R_PD_KFG2", "100k_1pct", "Resistor_SMD:R_0603_1608Metric", 114.0, 62.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

    k_fg1 = add_c(ComponentSpec("K_FG_A1", "OMRON_G7SA_3A1B_SHUTTER_10P", "Custom:OMRON_G7SA_3A1B_10P_THT", 142.0, 28.0, pins=_fg_relay_g7sa_10p_pins(), mpn="Omron_G7SA-3A1B-DC24", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    k_fg2 = add_c(ComponentSpec("K_FG_A2", "OMRON_G7SA_3A1B_VALVE_10P", "Custom:OMRON_G7SA_3A1B_10P_THT", 142.0, 58.0, pins=_fg_relay_g7sa_10p_pins(), mpn="Omron_G7SA-3A1B-DC24", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    d_fg1_f = add_c(ComponentSpec("D_FG1_FLY", "1N4148WS_FLYBACK", "Diode_SMD:D_0805_2012Metric", 128.0, 18.0, pins=auto_footprint_pads("0805", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    d_fg2_f = add_c(ComponentSpec("D_FG2_FLY", "1N4148WS_FLYBACK", "Diode_SMD:D_0805_2012Metric", 128.0, 44.0, pins=auto_footprint_pads("0805", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_mir_pu = add_c(ComponentSpec("R_MIRROR_PU", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", 160.0, 44.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

    # Diverse Ch-B Solid-State Cutoff Path: 470R LED current limit + CPC1017N + 12 V Zener-clamped SQJ461EP!
    # Plus dedicated 3rd Ch-B switch Q_SSR_B3 for K_CROWBAR_B coil (strictly V_24V_B / GND_B domain!)
    r_led_s1 = add_c(ComponentSpec("R_LED_SSR1", "470R_1pct_LED_LIM", "Resistor_SMD:R_0603_1608Metric", 116.0, 120.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_led_s2 = add_c(ComponentSpec("R_LED_SSR2", "470R_1pct_LED_LIM", "Resistor_SMD:R_0603_1608Metric", 116.0, 144.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_led_s3 = add_c(ComponentSpec("R_LED_SSR3", "470R_1pct_LED_LIM", "Resistor_SMD:R_0603_1608Metric", 116.0, 168.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    u_ssr1 = add_c(ComponentSpec("U_OPTO_SSR_B1", "CPC1017N_SSR_SHUTTER", "Package_SO:SOP-4_3.8x4.1mm_P2.54mm", 126.0, 120.0, pins=_ssr_opto_soic4_pins(), mpn="CPC1017NTR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_ssr2 = add_c(ComponentSpec("U_OPTO_SSR_B2", "CPC1017N_SSR_VALVE", "Package_SO:SOP-4_3.8x4.1mm_P2.54mm", 126.0, 144.0, pins=_ssr_opto_soic4_pins(), mpn="CPC1017NTR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    u_ssr3 = add_c(ComponentSpec("U_OPTO_SSR_B3", "CPC1017N_SSR_CROWBAR_B", "Package_SO:SOP-4_3.8x4.1mm_P2.54mm", 126.0, 168.0, pins=_ssr_opto_soic4_pins(), mpn="CPC1017NTR", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    q_ssr1 = add_c(ComponentSpec("Q_SSR_B1", "SQJ461EP_PMOS_SHUTTER", "Package_TO_SOT_SMD:TO-252-2", 148.0, 120.0, pins=_pmos_dpak_pins(), mpn="Vishay_SQJ461EP", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    q_ssr2 = add_c(ComponentSpec("Q_SSR_B2", "SQJ461EP_PMOS_VALVE", "Package_TO_SOT_SMD:TO-252-2", 148.0, 144.0, pins=_pmos_dpak_pins(), mpn="Vishay_SQJ461EP", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))
    q_ssr3 = add_c(ComponentSpec("Q_SSR_B3", "SQJ461EP_PMOS_CB_B", "Package_TO_SOT_SMD:TO-252-2", 148.0, 168.0, pins=_pmos_dpak_pins(), mpn="Vishay_SQJ461EP", bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}"))

    # 10k/10k Gate dividers + 12 V Zener clamps (BZX84C12) protecting SQJ461EP Vgs <= -12 V (abs max +/-20 V!)
    for idx_s, ys in ((1, 112.0), (2, 136.0), (3, 160.0)):
        add_c(ComponentSpec(f"R_SSR{idx_s}_PU", "10.0k_1pct", "Resistor_SMD:R_0805_2012Metric", 136.0, ys, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
        add_c(ComponentSpec(f"R_SSR{idx_s}_DIV", "10.0k_1pct_VGS_DIV", "Resistor_SMD:R_0805_2012Metric", 136.0, ys + 12.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
        add_c(ComponentSpec(f"D_Z_SSR{idx_s}", "BZX84C12_VGS_CLAMP", "Diode_SMD:D_0805_2012Metric", 146.0, ys, pins=auto_footprint_pads("0805", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

    # Proper 24 V -> 4.51 V resistive divider + 4.7 V Zener clamp for DIAG_FB_B (valve + shutter SSR feedback!)
    r_fb_bt = add_c(ComponentSpec("R_DIAG_FB_B_T", "43.2k_1pct_24V_DIV", "Resistor_SMD:R_0805_2012Metric", 162.0, 144.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_fb_bb = add_c(ComponentSpec("R_DIAG_FB_B_B", "10.0k_1pct_24V_DIV", "Resistor_SMD:R_0805_2012Metric", 162.0, 152.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    d_z_fbb = add_c(ComponentSpec("D_Z_DIAG_FBB", "BZX84C4V7_5V_CLAMP", "Diode_SMD:D_0805_2012Metric", 162.0, 160.0, pins=auto_footprint_pads("0805", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    r_fb_sh = add_c(ComponentSpec("R_DIAG_SH_B", "43.2k_1pct_SH_FB", "Resistor_SMD:R_0805_2012Metric", 162.0, 130.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-02", epistemic_tag="{Pasif-COTS}"))

    # Fast Demagnetization TVS Clamps (<3.2 ms Shutter & <80 ms UHV Gate Valve) + Output Terminal Blocks
    d_tvs_sh = add_c(ComponentSpec("D_TVS_SHUTTER", "SMBJ36A_FAST_DROP", "Diode_SMD:D_1206_3216Metric", 166.0, 26.0, pins=auto_footprint_pads("1206", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-02", epistemic_tag="{Pasif-COTS}"))
    d_tvs_vl = add_c(ComponentSpec("D_TVS_VALVE", "SMBJ36A_FAST_VALVE", "Diode_SMD:D_1206_3216Metric", 166.0, 56.0, pins=auto_footprint_pads("1206", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-06", epistemic_tag="{Pasif-COTS}"))
    j_shut = add_c(ComponentSpec(
        "J_SHUTTER_OUT", "TERM_4P_DUALCOIL_SHUTTER", "Connector_PinHeader:HDR_1x4_2.54mm",
        182.0, 26.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                              {"1": "SHUT_COIL1_P", "2": "GND_A", "3": "SHUT_COIL2_P", "4": "GND_A2"}),
        bom_id="S7.SAFETY-02", epistemic_tag="{Pasif-COTS}",
    ))
    j_valve = add_c(ComponentSpec(
        "J_UHV_VALVE_OUT", "TERM_4P_UHV_GATEVALVE_80MS", "Connector_PinHeader:HDR_1x4_2.54mm",
        182.0, 56.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                              {"1": "UHV_VALVE_P", "2": "GND_A", "3": "HV_SAFE_CLAMP_24V", "4": "GND_A2"}),
        bom_id="S7.SAFETY-06", epistemic_tag="{Pasif-COTS}",
    ))
    j_las_cb = add_c(ComponentSpec(
        "J_LASER_CB_OUT", "TERM_4P_LASER_1OO2D_OUT", "Connector_PinHeader:HDR_1x4_2.54mm",
        182.0, 124.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                              {"1": "SAFE_LASER_EN_A", "2": "SAFE_LASER_EN_B", "3": "GND_A", "4": "GND_B"}),
        bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}",
    ))

    # =========================================================================
    # SECTION 5 (RIGHT HV BAY, x=234..304 mm): 22 kV ACTIVE 2.00 MOhm HV CROWBAR (S7.SAFETY-03)
    #   OBS-051 FIX:
    #   * Vertical slot HV22K_LV_MAIN_SLOT: x=[206..214], y=[6..126] separates LV (x<=186) from 22 kV (x>=234)
    #     -> direct clr >= 42 mm (>= 30 mm req), slot-detour crp >= 60 mm (>= 50 mm req)!
    #   * Horizontal slot HV22K_BUS_DUMP_SLOT: x=[226..304], y=[42..50] separates HV_22KV_BUS (y=24)
    #     from HV_22KV_DUMP (y=68) RIGHT BETWEEN K_CROWBAR_A/B open contacts!
    #     -> open-contact clr = 41.6 mm (>= 30 mm req), slot-detour crp >= 58.9 mm (>= 50 mm req)!
    #   * Horizontal slot HV22K_HOT_RTN_SLOT: x=[226..304], y=[92..100] separates HV_22KV_DUMP/MID (y<=68)
    #     from 24 V crowbar coils & M6 PE return (y>=120) -> clr >= 49 mm, crp >= 62 mm!
    #   * Dedicated bolted M6 PE star lug (ZERO SMD 0R tie to GND_B!)
    # =========================================================================
    j_hv22_in = add_c(ComponentSpec(
        "JHV_22KV_IN", "HV_TURRET_22KV_BUS", "Custom:HV_ALUMINA_TURRET_25KV",
        234.0, 24.0, pins=_hv22k_turret_pin(), mpn="CeramTec_25kV_Alumina_Turret",
        bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
    ))
    k_cb_a = add_c(ComponentSpec(
        "K_CROWBAR_A", "GIGAVAC_G81C_25KV_NC_CHA", "Custom:HV25KV_VACUUM_RELAY_WIDE_P44_52mm",
        246.0, 72.0, pins=_hv22k_relay_nc_wide_pins(), mpn="Gigavac_G81C-25KV-NC",
        bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}",
    ))
    k_cb_b = add_c(ComponentSpec(
        "K_CROWBAR_B", "ROSS_E25_25KV_NC_CHB", "Custom:HV25KV_VACUUM_RELAY_WIDE_P44_52mm",
        270.0, 72.0, pins=_hv22k_relay_nc_wide_pins(), mpn="Ross_E25-NC-25KV",
        bom_id="S7.SAFETY-03", epistemic_tag="{Aday-COTS}",
    ))
    r_cb_1 = add_c(ComponentSpec(
        "R_CROWBAR_1", "1.00M_25KV_OHMITE_MOX4", "Custom:OHMITE_MOX4_25KV_H20mm",
        290.0, 68.0, pins=_hv22k_res_horiz_pins(), mpn="Ohmite_MOX400231004FE",
        bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
    ))
    r_cb_2 = add_c(ComponentSpec(
        "R_CROWBAR_2", "1.00M_25KV_OHMITE_MOX4", "Custom:OHMITE_MOX4_25KV_V52mm",
        300.0, 102.0, pins=_hv22k_res_vertical_pins(), mpn="Ohmite_MOX400231004FE",
        bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
    ))
    # Dedicated M6 Bolted Heavy Chassis PE Star Return Studs (NO SMD 0R jumper to signal GND_B!)
    j_hv22_rtn = add_c(ComponentSpec(
        "JHV_22KV_RTN", "HV_CROWBAR_PE_STUD_M6", "Custom:PE_STAR_LUG_M6",
        300.0, 148.0, pins=_pe_m6_lug_pin(), mpn="Keystone_PE_Star_Lug_M6",
        bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
    ))
    j_pe_chassis = add_c(ComponentSpec(
        "J_PE_CHASSIS_LUG", "CHASSIS_PE_STAR_M6", "Custom:PE_STAR_LUG_M6",
        300.0, 166.0, pins=_pe_m6_lug_pin(), mpn="Keystone_PE_Star_Lug_M6",
        bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}",
    ))
    d_cba_f = add_c(ComponentSpec("D_CB_A_FLY", "SMBJ36A_CB_A", "Diode_SMD:D_1206_3216Metric", 246.0, 144.0, pins=auto_footprint_pads("1206", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    d_cbb_f = add_c(ComponentSpec("D_CB_B_FLY", "SMBJ36A_CB_B", "Diode_SMD:D_1206_3216Metric", 270.0, 144.0, pins=auto_footprint_pads("1206", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    # Crowbar auxiliary contact diagnostic pull-up to V_5V_DIAG
    r_cb_aux_pu = add_c(ComponentSpec("R_CB_AUX_PU", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", 232.0, 158.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))

    # =========================================================================
    # NETLIST CONNECTIONS
    # =========================================================================
    # Power (independent Ch-A, Ch-B, and diode-OR'd Diagnostic rail)
    conn("V_24V_A", j_pwr.ref, 1); conn("GND_A", j_pwr.ref, 2)
    conn("V_24V_B", j_pwr.ref, 3); conn("GND_B", j_pwr.ref, 4)
    conn("V_24V_A", u_reg_a.ref, 1); conn("GND_A", u_reg_a.ref, 2); conn("GND_A", u_reg_a.ref, 4); conn("V_5V_A", u_reg_a.ref, 3)
    # ADP7142AUJZ-5.0 TSOT-23-5: 1=VIN, 2=GND, 3=EN, 4=SENSE(tied to VOUT), 5=VOUT
    conn("V_24V_B", u_reg_b.ref, 1); conn("GND_B", u_reg_b.ref, 2); conn("V_24V_B", u_reg_b.ref, 3)
    conn("V_5V_B", u_reg_b.ref, 4); conn("V_5V_B", u_reg_b.ref, 5)
    # Independent Diagnostic/WDT 5 V rail (diode-OR of V_24V_A & V_24V_B -> V_24V_DIAG -> ADP7142AUJZ-5.0 -> V_5V_DIAG)
    conn("V_24V_A", d_or_a.ref, 1); conn("V_24V_DIAG", d_or_a.ref, 2)
    conn("V_24V_B", d_or_b.ref, 1); conn("V_24V_DIAG", d_or_b.ref, 2)
    conn("V_24V_DIAG", u_reg_diag.ref, 1); conn("GND_DIAG", u_reg_diag.ref, 2); conn("V_24V_DIAG", u_reg_diag.ref, 3)
    conn("V_5V_DIAG", u_reg_diag.ref, 4); conn("V_5V_DIAG", u_reg_diag.ref, 5)
    # Reference GND_DIAG to star return via 0R single-point diagnostic tie
    r_gnd_diag = add_c(ComponentSpec("R_GND_DIAG_STAR", "0R_DIAG_REF", "Resistor_SMD:R_0805_2012Metric", 32.0, 82.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S7.SAFETY-03", epistemic_tag="{Pasif-COTS}"))
    conn("GND_DIAG", r_gnd_diag.ref, 1); conn("GND_A", r_gnd_diag.ref, 2)

    # Sensor Connectors (all 4-20 mA live-zero loops)
    conn("PH3_SENS_A", j_ph3.ref, 1); conn("GND_A", j_ph3.ref, 2); conn("PH3_SENS_B", j_ph3.ref, 3); conn("GND_B", j_ph3.ref, 4)
    conn("O2_SENS_A", j_o2.ref, 1); conn("GND_A", j_o2.ref, 2); conn("O2_SENS_B", j_o2.ref, 3); conn("GND_B", j_o2.ref, 4)
    conn("MXC_SENS_A", j_mxc_uhv.ref, 1); conn("MXC_SENS_B", j_mxc_uhv.ref, 2)
    conn("UHV_SENS_A", j_mxc_uhv.ref, 3); conn("UHV_SENS_B", j_mxc_uhv.ref, 4)
    conn("DOOR_QUENCH_A", j_mxc_uhv.ref, 5); conn("DOOR_QUENCH_B", j_mxc_uhv.ref, 6)

    # Independent Diagnostic / Watchdog Island (V_5V_DIAG / GND_DIAG)
    conn("WDT_OK", u_wdt.ref, 1); conn("GND_DIAG", u_wdt.ref, 2); conn("WDT_KICK_ISO", u_wdt.ref, 3)
    conn("V_5V_DIAG", u_wdt.ref, 4); conn("GND_DIAG", u_wdt.ref, 5); conn("V_5V_DIAG", u_wdt.ref, 6)

    conn("CH_PRE_VOTE_A", u_xor_v.ref, 1); conn("CH_PRE_VOTE_B", u_xor_v.ref, 2)
    conn("GND_DIAG", u_xor_v.ref, 3); conn("V_5V_DIAG", u_xor_v.ref, 5); conn("DISC_VOTE_RAW", u_xor_v.ref, 4)

    conn("DIAG_FB_A", u_xor_fb.ref, 1); conn("DIAG_FB_B", u_xor_fb.ref, 2)
    conn("GND_DIAG", u_xor_fb.ref, 3); conn("V_5V_DIAG", u_xor_fb.ref, 5); conn("DISC_FB_RAW", u_xor_fb.ref, 4)

    # 33 ms RC discrepancy blanking filters (eliminates 10 ms relay/SSR turn-on skew nuisance trip!)
    conn("DISC_VOTE_RAW", r_disc_f.ref, 1); conn("DISCREP_FAULT", r_disc_f.ref, 2)
    conn("DISCREP_FAULT", c_disc_f.ref, 1); conn("GND_DIAG", c_disc_f.ref, 2)
    conn("DISC_FB_RAW", r_fb_filt.ref, 1); conn("DISC_FB_FILT", r_fb_filt.ref, 2)
    conn("DISC_FB_FILT", c_fb_filt.ref, 1); conn("GND_DIAG", c_fb_filt.ref, 2)

    conn("DISCREP_FAULT", u_diag_nor.ref, 1); conn("DISC_FB_FILT", u_diag_nor.ref, 2)
    conn("GND_DIAG", u_diag_nor.ref, 3); conn("V_5V_DIAG", u_diag_nor.ref, 5); conn("DIAG_OK", u_diag_nor.ref, 4)

    conn("WDT_OK", u_wdt_and.ref, 1); conn("DIAG_OK", u_wdt_and.ref, 2)
    conn("GND_DIAG", u_wdt_and.ref, 3); conn("V_5V_DIAG", u_wdt_and.ref, 5); conn("WDT_DIAG_OK", u_wdt_and.ref, 4)

    # Galvanically isolated WDT_DIAG_OK distribution into Ch-A (V_5V_A/GND_A) and Ch-B (V_5V_B/GND_B)!
    conn("WDT_DIAG_OK", r_wdt_la.ref, 1); conn("WDT_LED_A", r_wdt_la.ref, 2); conn("WDT_LED_A", u_opto_wdt.ref, 1); conn("GND_DIAG", u_opto_wdt.ref, 2)
    conn("WDT_DIAG_OK", r_wdt_lb.ref, 1); conn("WDT_LED_B", r_wdt_lb.ref, 2); conn("WDT_LED_B", u_opto_wdt.ref, 3); conn("GND_DIAG", u_opto_wdt.ref, 4)
    conn("V_5V_A", r_wdt_pua.ref, 1); conn("WDT_DIAG_OK_A", r_wdt_pua.ref, 2); conn("WDT_DIAG_OK_A", u_opto_wdt.ref, 8); conn("GND_A", u_opto_wdt.ref, 7)
    conn("V_5V_B", r_wdt_pub.ref, 1); conn("WDT_DIAG_OK_B", r_wdt_pub.ref, 2); conn("WDT_DIAG_OK_B", u_opto_wdt.ref, 6); conn("GND_B", u_opto_wdt.ref, 5)

    # Opto-Isolated 3.3 V FPGA Header Connections (V_3V3_FPGA / GND_FPGA strictly isolated from 24 V & 5 V!)
    conn("FPGA_WDT_KICK_3V3", j_fpga.ref, 1); conn("WDT_OK_3V3", j_fpga.ref, 2)
    conn("DISCREP_FAULT_3V3", j_fpga.ref, 3); conn("VOTE_SAFE_A_3V3", j_fpga.ref, 4)
    conn("VOTE_SAFE_B_3V3", j_fpga.ref, 5); conn("DIAG_FB_A_3V3", j_fpga.ref, 6)
    conn("DIAG_FB_B_3V3", j_fpga.ref, 7); conn("HV_SAFE_CLAMP_3V3", j_fpga.ref, 8)
    conn("V_3V3_FPGA", j_fpga.ref, 9); conn("GND_FPGA", j_fpga.ref, 10)
    conn("GND_FPGA", j_fpga.ref, 11); conn("WDT_DIAG_OK_3V3", j_fpga.ref, 12)

    # FPGA Opto 1: FPGA_WDT_KICK_3V3 -> WDT_KICK_ISO (Ch1) & WDT_OK -> WDT_OK_3V3 (Ch2)
    conn("FPGA_WDT_KICK_3V3", "R_FLED_WDTK", 1); conn("FLED_WDTK", "R_FLED_WDTK", 2); conn("FLED_WDTK", u_opto_fpga_wdt.ref, 1); conn("GND_FPGA", u_opto_fpga_wdt.ref, 2)
    conn("V_5V_DIAG", "R_FPU_WDTK", 1); conn("WDT_KICK_ISO", "R_FPU_WDTK", 2); conn("WDT_KICK_ISO", u_opto_fpga_wdt.ref, 8); conn("GND_DIAG", u_opto_fpga_wdt.ref, 7)
    conn("WDT_OK", "R_FLED_WDTO", 1); conn("FLED_WDTO", "R_FLED_WDTO", 2); conn("FLED_WDTO", u_opto_fpga_wdt.ref, 3); conn("GND_DIAG", u_opto_fpga_wdt.ref, 4)
    conn("V_3V3_FPGA", "R_FPU_WDTO", 1); conn("WDT_OK_3V3", "R_FPU_WDTO", 2); conn("WDT_OK_3V3", u_opto_fpga_wdt.ref, 6); conn("GND_FPGA", u_opto_fpga_wdt.ref, 5)

    # FPGA Opto 2: VOTE_SAFE_A -> VOTE_SAFE_A_3V3 & VOTE_SAFE_B -> VOTE_SAFE_B_3V3
    conn("VOTE_SAFE_A", "R_FLED_VA", 1); conn("FLED_VA", "R_FLED_VA", 2); conn("FLED_VA", u_opto_fpga_st1.ref, 1); conn("GND_A", u_opto_fpga_st1.ref, 2)
    conn("V_3V3_FPGA", "R_FPU_VA", 1); conn("VOTE_SAFE_A_3V3", "R_FPU_VA", 2); conn("VOTE_SAFE_A_3V3", u_opto_fpga_st1.ref, 8); conn("GND_FPGA", u_opto_fpga_st1.ref, 7)
    conn("VOTE_SAFE_B", "R_FLED_VB", 1); conn("FLED_VB", "R_FLED_VB", 2); conn("FLED_VB", u_opto_fpga_st1.ref, 3); conn("GND_B", u_opto_fpga_st1.ref, 4)
    conn("V_3V3_FPGA", "R_FPU_VB", 1); conn("VOTE_SAFE_B_3V3", "R_FPU_VB", 2); conn("VOTE_SAFE_B_3V3", u_opto_fpga_st1.ref, 6); conn("GND_FPGA", u_opto_fpga_st1.ref, 5)

    # FPGA Opto 3: DIAG_FB_A -> DIAG_FB_A_3V3 & DIAG_FB_B -> DIAG_FB_B_3V3
    conn("DIAG_FB_A", "R_FLED_FBA", 1); conn("FLED_FBA", "R_FLED_FBA", 2); conn("FLED_FBA", u_opto_fpga_st2.ref, 1); conn("GND_A", u_opto_fpga_st2.ref, 2)
    conn("V_3V3_FPGA", "R_FPU_FBA", 1); conn("DIAG_FB_A_3V3", "R_FPU_FBA", 2); conn("DIAG_FB_A_3V3", u_opto_fpga_st2.ref, 8); conn("GND_FPGA", u_opto_fpga_st2.ref, 7)
    conn("DIAG_FB_B", "R_FLED_FBB", 1); conn("FLED_FBB", "R_FLED_FBB", 2); conn("FLED_FBB", u_opto_fpga_st2.ref, 3); conn("GND_DIAG", u_opto_fpga_st2.ref, 4)
    conn("V_3V3_FPGA", "R_FPU_FBB", 1); conn("DIAG_FB_B_3V3", "R_FPU_FBB", 2); conn("DIAG_FB_B_3V3", u_opto_fpga_st2.ref, 6); conn("GND_FPGA", u_opto_fpga_st2.ref, 5)

    # FPGA Opto 4: HV_SAFE_CLAMP_24V (24V=healthy) -> HV_SAFE_CLAMP_3V3 (3.3V active-HIGH=CLAMP!) & DISCREP_FAULT -> DISCREP_FAULT_3V3
    # When HV_SAFE_CLAMP_24V is 24V (healthy), opto conducts and pulls HV_SAFE_CLAMP_3V3 LOW (0V = normal);
    # when tripped or power lost, opto turns OFF and R_FPU_CLP pulls HV_SAFE_CLAMP_3V3 HIGH (3.3V = CLAMP, matching spi_dac_hv_ctrl.v!)
    conn("HV_SAFE_CLAMP_24V", "R_FLED_CLP", 1); conn("FLED_CLP", "R_FLED_CLP", 2); conn("FLED_CLP", u_opto_fpga_clp.ref, 1); conn("GND_A", u_opto_fpga_clp.ref, 2)
    conn("V_3V3_FPGA", "R_FPU_CLP", 1); conn("HV_SAFE_CLAMP_3V3", "R_FPU_CLP", 2); conn("HV_SAFE_CLAMP_3V3", u_opto_fpga_clp.ref, 8); conn("GND_FPGA", u_opto_fpga_clp.ref, 7)
    conn("DISCREP_FAULT", "R_FLED_DISC", 1); conn("FLED_DISC", "R_FLED_DISC", 2); conn("FLED_DISC", u_opto_fpga_clp.ref, 3); conn("GND_DIAG", u_opto_fpga_clp.ref, 4)
    conn("V_3V3_FPGA", "R_FPU_DISC", 1); conn("DISCREP_FAULT_3V3", "R_FPU_DISC", 2); conn("DISCREP_FAULT_3V3", u_opto_fpga_clp.ref, 6); conn("GND_FPGA", u_opto_fpga_clp.ref, 5)
    # Tie WDT_DIAG_OK_3V3 to WDT_OK_3V3 via 0R telemetry tap
    r_wdt_t = add_c(ComponentSpec("R_WDT_TELEM", "0R_TELEM", "Resistor_SMD:R_0603_1608Metric", 36.0, 80.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.4-04", epistemic_tag="{Pasif-COTS}"))
    conn("WDT_OK_3V3", r_wdt_t.ref, 1); conn("WDT_DIAG_OK_3V3", r_wdt_t.ref, 2)

    # Ch-A Low-Side 24 V MOSFET Coil Drivers -> 10-pin Omron G7SA-3A1B-DC24 Force-Guided Safety Relays!
    conn("VOTE_SAFE_A", r_g_fg1.ref, 1); conn("GATE_KFG1", r_g_fg1.ref, 2); conn("GATE_KFG1", r_pd_fg1.ref, 1); conn("GND_A", r_pd_fg1.ref, 2)
    conn("GATE_KFG1", q_drv_fg1.ref, 1); conn("GND_A", q_drv_fg1.ref, 2); conn("KFG1_COIL_N", q_drv_fg1.ref, 3)
    conn("V_24V_A", k_fg1.ref, 1); conn("KFG1_COIL_N", k_fg1.ref, 2)
    conn("V_24V_A", d_fg1_f.ref, 1); conn("KFG1_COIL_N", d_fg1_f.ref, 2)

    conn("VOTE_SAFE_A", r_g_fg2.ref, 1); conn("GATE_KFG2", r_g_fg2.ref, 2); conn("GATE_KFG2", r_pd_fg2.ref, 1); conn("GND_A", r_pd_fg2.ref, 2)
    conn("GATE_KFG2", q_drv_fg2.ref, 1); conn("GND_A", q_drv_fg2.ref, 2); conn("KFG2_COIL_N", q_drv_fg2.ref, 3)
    conn("V_24V_A", k_fg2.ref, 1); conn("KFG2_COIL_N", k_fg2.ref, 2)
    conn("V_24V_A", d_fg2_f.ref, 1); conn("KFG2_COIL_N", d_fg2_f.ref, 2)

    # Series Safety Cutoff Topology on 10-pin G7SA-3A1B (3x NO: pins 3-4, 5-6, 7-8; 1x NC mirror: pins 9-10!)
    conn("V_24V_A", k_fg1.ref, 3); conn("SHUT_MID_AB", k_fg1.ref, 4)
    conn("V_24V_A", k_fg1.ref, 5); conn("SAFE_LASER_EN_A", k_fg1.ref, 6)
    conn("V_24V_A", k_fg1.ref, 7); conn("CB_COIL_A_24V", k_fg1.ref, 8)
    # Mechanically linked NC mirror contacts (pins 9-10) in series with K_CROWBAR_A/B aux contacts!
    conn("V_5V_A", r_mir_pu.ref, 1); conn("DIAG_FB_A", r_mir_pu.ref, 2)
    conn("DIAG_FB_A", k_fg1.ref, 9); conn("MIR_MID", k_fg1.ref, 10)
    conn("MIR_MID", k_fg2.ref, 9); conn("GND_A", k_fg2.ref, 10)

    conn("V_24V_A", k_fg2.ref, 3); conn("VALVE_MID_AB", k_fg2.ref, 4)
    conn("V_24V_A", k_fg2.ref, 5); conn("HV_SAFE_CLAMP_24V", k_fg2.ref, 6)
    conn("V_24V_A", k_fg2.ref, 7); conn("SHUT_COIL2_24V", k_fg2.ref, 8)

    # Diverse Ch-B Solid-State Cutoff: 470R LED series resistor + CPC1017N + 10k/10k + 12V Zener gate clamp on SQJ461EP!
    # SSR1 (Shutter series cutoff):
    conn("VOTE_SAFE_B", r_led_s1.ref, 1); conn("SSR1_LED_A", r_led_s1.ref, 2); conn("SSR1_LED_A", u_ssr1.ref, 1); conn("GND_B", u_ssr1.ref, 2)
    conn("GND_A", u_ssr1.ref, 3); conn("SSR1_DIV_LO", u_ssr1.ref, 4)
    conn("SHUT_MID_AB", "R_SSR1_PU", 1); conn("SSR1_GATE", "R_SSR1_PU", 2)
    conn("SSR1_GATE", "R_SSR1_DIV", 1); conn("SSR1_DIV_LO", "R_SSR1_DIV", 2)
    conn("SHUT_MID_AB", "D_Z_SSR1", 1); conn("SSR1_GATE", "D_Z_SSR1", 2)
    conn("SSR1_GATE", q_ssr1.ref, 1); conn("SHUT_MID_AB", q_ssr1.ref, 3); conn("SHUT_SAFE_24V", q_ssr1.ref, 2)

    # SSR2 (UHV Valve series cutoff):
    conn("VOTE_SAFE_B", r_led_s2.ref, 1); conn("SSR2_LED_A", r_led_s2.ref, 2); conn("SSR2_LED_A", u_ssr2.ref, 1); conn("GND_B", u_ssr2.ref, 2)
    conn("GND_A", u_ssr2.ref, 3); conn("SSR2_DIV_LO", u_ssr2.ref, 4)
    conn("VALVE_MID_AB", "R_SSR2_PU", 1); conn("SSR2_GATE", "R_SSR2_PU", 2)
    conn("SSR2_GATE", "R_SSR2_DIV", 1); conn("SSR2_DIV_LO", "R_SSR2_DIV", 2)
    conn("VALVE_MID_AB", "D_Z_SSR2", 1); conn("SSR2_GATE", "D_Z_SSR2", 2)
    conn("SSR2_GATE", q_ssr2.ref, 1); conn("VALVE_MID_AB", q_ssr2.ref, 3); conn("VALVE_SAFE_24V", q_ssr2.ref, 2)

    # SSR3 (Dedicated Ch-B 22 kV Crowbar Coil B & Laser Enable B, strictly V_24V_B / GND_B domain — ZERO cross-domain short!):
    conn("VOTE_SAFE_B", r_led_s3.ref, 1); conn("SSR3_LED_A", r_led_s3.ref, 2); conn("SSR3_LED_A", u_ssr3.ref, 1); conn("GND_B", u_ssr3.ref, 2)
    conn("GND_B", u_ssr3.ref, 3); conn("SSR3_DIV_LO", u_ssr3.ref, 4)
    conn("V_24V_B", "R_SSR3_PU", 1); conn("SSR3_GATE", "R_SSR3_PU", 2)
    conn("SSR3_GATE", "R_SSR3_DIV", 1); conn("SSR3_DIV_LO", "R_SSR3_DIV", 2)
    conn("V_24V_B", "D_Z_SSR3", 1); conn("SSR3_GATE", "D_Z_SSR3", 2)
    conn("SSR3_GATE", q_ssr3.ref, 1); conn("V_24V_B", q_ssr3.ref, 3); conn("SAFE_LASER_EN_B", q_ssr3.ref, 2)

    # 24 V -> 4.51 V Divider + 4.7 V Zener Clamp for DIAG_FB_B (monitors VALVE_SAFE_24V & SHUT_SAFE_24V!)
    conn("VALVE_SAFE_24V", r_fb_bt.ref, 1); conn("DIAG_FB_B", r_fb_bt.ref, 2)
    conn("SHUT_SAFE_24V", r_fb_sh.ref, 1); conn("DIAG_FB_B", r_fb_sh.ref, 2)
    conn("DIAG_FB_B", r_fb_bb.ref, 1); conn("GND_DIAG", r_fb_bb.ref, 2)
    conn("DIAG_FB_B", d_z_fbb.ref, 1); conn("GND_DIAG", d_z_fbb.ref, 2)

    # Actuator Output Connectors & Fast TVS Demagnetization Clamps (zero GND_A/GND_B shorts!)
    conn("SHUT_SAFE_24V", d_tvs_sh.ref, 1); conn("GND_A", d_tvs_sh.ref, 2)
    conn("SHUT_SAFE_24V", j_shut.ref, 1); conn("GND_A", j_shut.ref, 2)
    conn("SHUT_COIL2_24V", j_shut.ref, 3); conn("GND_A", j_shut.ref, 4)

    conn("VALVE_SAFE_24V", d_tvs_vl.ref, 1); conn("GND_A", d_tvs_vl.ref, 2)
    conn("VALVE_SAFE_24V", j_valve.ref, 1); conn("GND_A", j_valve.ref, 2)
    conn("HV_SAFE_CLAMP_24V", j_valve.ref, 3); conn("GND_A", j_valve.ref, 4)

    conn("SAFE_LASER_EN_A", j_las_cb.ref, 1); conn("SAFE_LASER_EN_B", j_las_cb.ref, 2)
    conn("GND_A", j_las_cb.ref, 3); conn("GND_B", j_las_cb.ref, 4)

    # 22 kV Active 2.00 MOhm HV Crowbar Bay (Parallel Diverse NC Relays K_CROWBAR_A || K_CROWBAR_B!)
    conn("HV_22KV_BUS", j_hv22_in.ref, 1); conn("HV_22KV_BUS", k_cb_a.ref, 1); conn("HV_22KV_BUS", k_cb_b.ref, 1)
    conn("HV_22KV_DUMP", k_cb_a.ref, 2); conn("HV_22KV_DUMP", k_cb_b.ref, 2); conn("HV_22KV_DUMP", r_cb_1.ref, 1)
    conn("HV_22KV_MID", r_cb_1.ref, 2); conn("HV_22KV_MID", r_cb_2.ref, 1)
    # Dedicated M6 bolted PE star return (ZERO SMD tie to signal GND_B!)
    conn("HV_CROWBAR_RTN", r_cb_2.ref, 2); conn("HV_CROWBAR_RTN", j_hv22_rtn.ref, 1); conn("HV_CROWBAR_RTN", j_pe_chassis.ref, 1)

    # 22 kV Crowbar Relay Coils (Ch-A strictly GND_A, Ch-B strictly GND_B) + Auxiliary Mirror Diagnostic Loop!
    conn("CB_COIL_A_24V", k_cb_a.ref, 3); conn("GND_A", k_cb_a.ref, 4)
    conn("CB_COIL_A_24V", d_cba_f.ref, 1); conn("GND_A", d_cba_f.ref, 2)
    conn("SAFE_LASER_EN_B", k_cb_b.ref, 3); conn("GND_B", k_cb_b.ref, 4)
    conn("SAFE_LASER_EN_B", d_cbb_f.ref, 1); conn("GND_B", d_cbb_f.ref, 2)
    # Series auxiliary diagnostic feedback across K_CROWBAR_A & K_CROWBAR_B
    conn("V_5V_DIAG", r_cb_aux_pu.ref, 1); conn("CB_AUX_DIAG", r_cb_aux_pu.ref, 2)
    conn("CB_AUX_DIAG", k_cb_a.ref, 5); conn("CB_AUX_MID", k_cb_a.ref, 6)
    conn("CB_AUX_MID", k_cb_b.ref, 5); conn("GND_DIAG", k_cb_b.ref, 6)

    # =========================================================================
    # COPPER TRACES & STITCHING VIAS
    # =========================================================================
    ka1, ka2 = _pad_xy(k_cb_a, "1"), _pad_xy(k_cb_a, "2")
    kb1, kb2 = _pad_xy(k_cb_b, "1"), _pad_xy(k_cb_b, "2")
    # HV_22KV_BUS strictly on top island y = 24 mm (above slot y=[42..50])
    traces.append(make_manhattan_trace("HV_22KV_BUS", "F.Cu", _pad_xy(j_hv22_in, "1"), ka1, width_mm=1.50))
    traces.append(make_manhattan_trace("HV_22KV_BUS", "F.Cu", ka1, kb1, width_mm=1.50))
    # HV_22KV_DUMP strictly on middle island y = 68 mm (between slots y=[42..50] and y=[92..100])
    traces.append(make_manhattan_trace("HV_22KV_DUMP", "F.Cu", ka2, kb2, width_mm=1.50))
    traces.append(make_manhattan_trace("HV_22KV_DUMP", "F.Cu", kb2, _pad_xy(r_cb_1, "1"), width_mm=1.50))
    # HV_22KV_MID from R_CROWBAR_1.2 (300, 68) to R_CROWBAR_2.1 (300, 76)
    traces.append(make_manhattan_trace("HV_22KV_MID", "F.Cu", _pad_xy(r_cb_1, "2"), _pad_xy(r_cb_2, "1"), width_mm=1.50))
    # HV Return Bus on B.Cu (strictly y >= 128 mm to bolted M6 PE star studs)
    traces.append(make_manhattan_trace("HV_CROWBAR_RTN", "B.Cu", _pad_xy(r_cb_2, "2"), _pad_xy(j_hv22_rtn, "1"), width_mm=2.50))
    traces.append(make_manhattan_trace("HV_CROWBAR_RTN", "B.Cu", _pad_xy(j_hv22_rtn, "1"), _pad_xy(j_pe_chassis, "1"), width_mm=2.50))

    # LV Stitching Vias (strictly in LV bay x <= 184 mm)
    for vx in (34.0, 96.0, 168.0):
        vias.append(ViaSpec("GND_A", vx, 10.0, diameter_mm=0.70, drill_mm=0.35))
        vias.append(ViaSpec("GND_B", vx, 182.0, diameter_mm=0.70, drill_mm=0.35))

    # =========================================================================
    # MILLED EDGE.CUTS 22 kV HV ISOLATION AIR-SLOTS (>= 30 mm clr / >= 50 mm crp!)
    #   1) HV22K_LV_MAIN_SLOT:  vertical slot x=[206..214], y=[6..118] separating LV bay from 22 kV bay
    #   2) HV22K_BUS_DUMP_SLOT: horizontal slot x=[226..304], y=[42..50] separating 22 kV BUS vs DUMP contacts!
    #   3) HV22K_HOT_RTN_SLOT:  horizontal slot x=[226..304], y=[92..100] separating 22 kV DUMP/MID vs coils/PE!
    # =========================================================================
    keepouts = (
        KeepoutSpec("HV22K_LV_MAIN_SLOT", "air_slot", ("Edge.Cuts",), x_mm=206.0, y_mm=6.0, width_mm=8.0, height_mm=112.0),
        KeepoutSpec("HV22K_BUS_DUMP_SLOT", "air_slot", ("Edge.Cuts",), x_mm=226.0, y_mm=42.0, width_mm=78.0, height_mm=8.0),
        KeepoutSpec("HV22K_HOT_RTN_SLOT", "air_slot", ("Edge.Cuts",), x_mm=226.0, y_mm=92.0, width_mm=78.0, height_mm=8.0),
    )

    # LV Planes strictly in LV bay (x <= 188 mm -> >= 44 mm direct clearance from HV_22KV_* & zero through-board overlap!)
    # Dedicated isolated GND_FPGA island in In1.Cu between GND_A (y<=74) and GND_B (y>=108)
    zones = (
        ZoneSpec("GND_A", "In1.Cu", ((4.0, 4.0), (188.0, 4.0), (188.0, 74.0), (4.0, 74.0))),
        ZoneSpec("GND_FPGA", "In1.Cu", ((38.0, 77.0), (78.0, 77.0), (78.0, 105.0), (38.0, 105.0))),
        ZoneSpec("GND_B", "In1.Cu", ((4.0, 108.0), (188.0, 108.0), (188.0, 186.0), (4.0, 186.0))),
        ZoneSpec("V_24V_A", "In2.Cu", ((4.0, 4.0), (188.0, 4.0), (188.0, 74.0), (4.0, 74.0))),
        ZoneSpec("V_24V_B", "In2.Cu", ((4.0, 108.0), (188.0, 108.0), (188.0, 186.0), (4.0, 186.0))),
    )

    pwr_nets = {
        "V_24V_A", "V_24V_B", "V_24V_DIAG", "V_5V_A", "V_5V_B", "V_5V_DIAG",
        "V_3V3_FPGA", "GND_A", "GND_B", "GND_DIAG", "GND_FPGA", "HV_22KV_BUS", "HV_CROWBAR_RTN",
    }
    flag_nets = {"V_24V_A", "V_24V_B", "V_24V_DIAG", "V_3V3_FPGA", "GND_A", "GND_B", "GND_DIAG", "GND_FPGA", "HV_22KV_BUS", "HV_CROWBAR_RTN"}

    nets: list[NetSpec] = []
    for nname, nodes in sorted(nets_dict.items()):
        if nname == "HV_22KV_BUS":
            v_work = 22000.0
        elif nname in ("HV_22KV_DUMP", "HV_22KV_MID"):
            # During normal HV-ON operation (relays OPEN), HV_22KV_DUMP & HV_22KV_MID sit at 0 V via 2 MOhm to PE
            # (full 22 kV differential across open relay contacts K_CROWBAR_A/B!), rising to 22 kV/11 kV on crowbar dump.
            v_work = 0.0
        elif "24V" in nname or "SHUT" in nname or "VALVE" in nname or "LASER" in nname or "CB_COIL" in nname or "KFG" in nname:
            v_work = 24.0
        elif "5V" in nname:
            v_work = 5.0
        elif "3V3" in nname:
            v_work = 3.3
        else:
            v_work = 0.0
        is_pwr = nname in pwr_nets
        nets.append(NetSpec(
            name=nname,
            nodes=tuple(nodes),
            net_class="HV_22KV" if nname.startswith("HV_22KV_") else ("Power" if is_pwr else "Default"),
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
            standard="IEC 61010-1 / IPC-2221B (22 kV MG-I Air-Slotted, Open-Contact Checked)",
            pollution_degree=2,
            material_group="I",
            differential_pairs=(("HV_22KV_BUS", "HV_22KV_DUMP"), ("HV_22KV_BUS", "HV_22KV_MID")),
        ),
    )

    spec = BoardSpec(
        name="safety_interlock_1oo2d",
        title="1oo2D Diverse Safety Interlock & 22 kV 2 MOhm HV Crowbar PCB [DESIGN_ONLY_NOT_CERTIFIED]",
        rev="v2.0",
        bom_ids=("S7.SAFETY-03", "S7.SAFETY-02", "S7.SAFETY-05", "S7.SAFETY-06", "S7.SAFETY-01", "S7.4-04", "S5.5-04"),
        width_mm=312.0,
        height_mm=190.0,
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
    """Component-level ngspice-47 deck verifying 22 kV crowbar, 4-20 mA live-zero window comparators,
    19.5% OSHA O2 trip, LM2903 pull-ups, 2N7002 24V relay driver, 12V Zener-clamped SQJ461EP PMOS,
    33 ms relay/SSR skew blanking, and 1oo2D single-channel fault injection."""
    return """* Atom Lithography Machine - 1oo2D Safety Interlock & 22 kV 2 MOhm HV Crowbar (Component-Level SPICE)
* BOM: S7.SAFETY-03, S7.SAFETY-02, S7.SAFETY-05, S7.SAFETY-06, S7.SAFETY-01, S7.4-04, S5.5-04
* STRICT EPISTEMIC NOTICE: DESIGN_ONLY_NOT_CERTIFIED (iec61508_certified=false, semi_s2_certified=false)

.temp 26.85
.options reltol=1e-4 vntol=1e-6 abstol=1e-12

* --- Real Component Semiconductor & Relay Models ---
.model QN_BJT    NPN(IS=1e-14 BF=150 VAF=80)
.model M_2N7002  NMOS(LEVEL=1 VTO=2.0 KP=0.35 RD=1.5 RS=0.5)
.model M_SQJ461  PMOS(LEVEL=1 VTO=-2.5 KP=4.0 RD=0.04 RS=0.02)
.model D_Z12V    D(IS=1e-12 BV=12.0 IBV=5m N=1.2 RS=2.0)
.model D_TVS36   D(IS=1e-12 BV=36.0 IBV=1m N=1.5 RS=0.5)
.model D_1N4148  D(IS=2.5e-9 RS=0.6 N=1.75)
* Normally-Closed 25 kV HV Vacuum Crowbar Relay: CLOSED (0.1 Ohm) when coil V < 8 V, OPEN (100 GOhm) when coil V > 12 V
.model SW_HV_NC  SW(VT=10.0 VH=2.0 RON=100G ROFF=0.1)
* HV PSU Isolation Contactor
.model SW_HV_NO  SW(VT=10.0 VH=2.0 RON=100  ROFF=100G)
* Omron G7SA 24 V Force-Guided Relay Contact (closes when 24 V coil energized > 12 V)
.model SW_G7SA   SW(VT=12.0 VH=2.0 RON=0.05 ROFF=100Meg)
* CPC1017N Opto-SSR Output (closes when LED forward drop > 0.45 V / I_LED > 3 mA)
.model SW_OPTO   SW(VT=0.45 VH=0.05 RON=8.0 ROFF=100Meg)

* --- Real Open-Collector LM2903DR Comparator Subcircuit (Requires External Pull-Up!) ---
.subckt LM2903_OC inp inn out vcc gnd
* Input differential stage driving open-collector NPN sinking stage (no internal pull-up!)
Ediff n_drv gnd VALUE = { 2.5 * (1.0 - tanh(200.0 * (V(inp) - V(inn)))) }
Rb_oc n_drv n_b 10k
Q_oc  out n_b gnd QN_BJT
.ends LM2903_OC

* --- 5 V CMOS 2-Input AND Gate Subcircuit (SN74LVC1G08) ---
.subckt CMOS_AND2 a b y vcc gnd
Band y_int gnd V = { 0.5 * V(vcc) * (1.0 + tanh(20.0 * (min(V(a), V(b)) - 0.5 * V(vcc)))) }
R_o  y_int y 50
C_o  y gnd 2p
.ends CMOS_AND2

* --- 5 V CMOS 2-Input XOR Gate Subcircuit (SN74AHC1G86) ---
.subckt CMOS_XOR2 a b y vcc gnd
Bxor y_int gnd V = { 0.5 * V(vcc) * (1.0 + tanh(20.0 * (abs(V(a) - V(b)) - 0.5 * V(vcc)))) }
R_o  y_int y 50
C_o  y gnd 2p
.ends CMOS_XOR2

* Supplies
V5a  v5a  0 DC 5.0
V24a v24a 0 DC 24.0
V24b v24b 0 DC 24.0

* Global 24 V trip stimulus: HEALTHY (24 V) for t < 1.0 ms; TRIPPED (0 V) for t >= 1.0 ms
Vtrip24 trip_24v 0 DC 24.0 PWL(0 24.0 0.999m 24.0 1.000m 0.0 50m 0.0)
Vtrip5  trip_5v  0 DC 5.0  PWL(0 5.0  0.999m 5.0  1.000m 0.0 50m 0.0)
Vstuck24 stuck_24v 0 DC 24.0

* =========================================================================
* 1) NOMINAL 22 kV 1.5 nF ACTIVE 2.00 MOhm HV CROWBAR DISCHARGE
* =========================================================================
Vhv_nom   hv_src_n 0 DC 22000
Spsu_nom  hv_src_n hv_bus_n trip_24v 0 SW_HV_NO
Cstray_n  hv_bus_n 0 1.5n IC=22000
Sk_cba_n  hv_bus_n hv_dmp_n trip_24v 0 SW_HV_NC
Sk_cbb_n  hv_bus_n hv_dmp_n trip_24v 0 SW_HV_NC
Rcb1_n    hv_dmp_n hv_mid_n 1.00Meg
Rcb2_n    hv_mid_n 0        1.00Meg
Bp_nom    p_dump_n 0 V = (V(hv_dmp_n) * V(hv_dmp_n)) / 2.0e6

* =========================================================================
* 2) SINGLE-CHANNEL FAULT INJECTION #1: K_CROWBAR_A STUCK OPEN (Ch-B Discharges!)
* =========================================================================
Vhv_flt   hv_src_f 0 DC 22000
Spsu_flt  hv_src_f hv_bus_f trip_24v  0 SW_HV_NO
Cstray_f  hv_bus_f 0 1.5n IC=22000
Sk_cba_f  hv_bus_f hv_dmp_f stuck_24v 0 SW_HV_NC
Sk_cbb_f  hv_bus_f hv_dmp_f trip_24v  0 SW_HV_NC
Rcb1_f    hv_dmp_f hv_mid_f 1.00Meg
Rcb2_f    hv_mid_f 0        1.00Meg
Bp_flt    p_dump_f 0 V = (V(hv_dmp_f) * V(hv_dmp_f)) / 2.0e6

* =========================================================================
* 3) COMPONENT-LEVEL 24V SHUTTER CUTOFF (K_FG_A1 WELDED CLOSED + REAL SQJ461EP PMOS
*    WITH 10k/10k + 12V ZENER GATE CLAMP + 470R CPC1017N + 33 ms DISCREPANCY BLANKING)
* =========================================================================
R_weld_a   v24a sh_mid_ab 10m
* CPC1017N LED driven by 5 V trip_5v via 470 Ohm current-limiting resistor
R_led_s1   trip_5v ssr1_led 470
D_led_s1   ssr1_led 0 D_1N4148
S_opto_s1  ssr1_div_lo 0 ssr1_led 0 SW_OPTO
* 10k/10k divider + 12 V Zener clamp protecting SQJ461EP Vgs <= -12 V (abs-max +/-20 V!)
R_ssr1_pu  sh_mid_ab ssr1_gate 10k
R_ssr1_div ssr1_gate ssr1_div_lo 10k
Dz_ssr1    ssr1_gate sh_mid_ab D_Z12V
* Real P-MOSFET SQJ461EP high-side safety cutoff switch
M_ssr_b1   sh_out ssr1_gate sh_mid_ab sh_mid_ab M_SQJ461 W=10 L=1
* Dual-coil shutter actuator load (48 Ohm, 20 mH) + 36 V fast-drop TVS clamp
R_sh_c     sh_out sh_ind 48.0
L_sh_c     sh_ind 0      20m
D_sh_tvs   0      sh_out D_TVS36
R_sh_bleed sh_out 0      100k

* Component-level discrepancy XOR + 33 ms RC blanking filter (verifies welded relay trips after blanking!)
* Mirror A reads 0 V (welded closed); Ch-B 24V->4.51V divider reads ~4.5V when ON, 0V when OFF -> inverted FB_B=5V when OFF
R_fbb_t    sh_out fb_b_div 43.2k
R_fbb_b    fb_b_div 0      10.0k
* Compare welded-closed Ch-A (stuck 5 V) vs actual Ch-B divider (drops 4.5 V -> 0 V at t=1 ms)
V_mira_wld diag_fb_a 0 DC 5.0
X_xor_wld  diag_fb_a fb_b_div disc_wld_raw v5a 0 CMOS_XOR2
R_wld_flt  disc_wld_raw disc_wld_rc 33k
C_wld_flt  disc_wld_rc  0           1.0u
X_wld_buf  disc_wld_rc v5a discrep_fault v5a 0 CMOS_AND2

* =========================================================================
* 4) TURN-ON SKEW TEST (10 ms G7SA MECHANICAL RELAY vs 50 us SSR THROUGH 33 ms BLANKING!)
* =========================================================================
* Normal turn-on at t=1 ms: SSR closes in 50 us (t=1.05 ms), G7SA relay closes in 10 ms (t=11 ms)
* -> raw XOR pulses HIGH for 10 ms, but 33 ms RC blanking keeps disc_skew_rc < 1.3 V (ZERO nuisance trip!)
V_skew_a   sk_a 0 DC 0 PWL(0 0 11.0m 0 11.1m 5.0 50m 5.0)
V_skew_b   sk_b 0 DC 0 PWL(0 0 1.05m 0 1.10m 5.0 50m 5.0)
X_xor_sk   sk_a sk_b disc_sk_raw v5a 0 CMOS_XOR2
R_sk_flt   disc_sk_raw disc_sk_rc 33k
C_sk_flt   disc_sk_rc  0          1.0u

* =========================================================================
* 5) REAL 4-20 mA LIVE-ZERO WINDOW COMPARATORS (LM2903DR + 10k PULL-UP) & 19.5% OSHA O2
* =========================================================================
* Precision Reference Dividers
R_ref_ph3t v5a vref_ph3 10.0k
R_ref_ph3b vref_ph3 0   4.99k
R_ref_lzt  v5a vref_lz  10.0k
R_ref_lzb  vref_lz 0    2.15k
R_ref_o2t  v5a vref_o2  10.0k
R_ref_o2b  vref_o2 0    47.5k

* PH3 4-20 mA sensor: 0..10 ms = 5.0 mA (healthy!), 10..25 ms = 0.0 mA (OPEN WIRE -> MUST TRIP SAFE!), 25..45 ms = 12 mA (GAS LEAK -> TRIP!)
I_ph3_loop 0 ph3_sens DC 5m PWL(0 5m 9.9m 5m 10.0m 0 24.9m 0 25.0m 12m 45m 12m)
R_burd_ph3 ph3_sens 0 250.0
X_ph3_hi   vref_ph3 ph3_sens ph3_ok_a v5a 0 LM2903_OC
X_ph3_lz   ph3_sens vref_lz  ph3_ok_a v5a 0 LM2903_OC
R_pu_ph3   v5a ph3_ok_a 10.0k

* O2 4-20 mA sensor (0-25%): 0..15 ms = 20.9% (17.376 mA -> HEALTHY!), 15..45 ms = 19.0% (16.16 mA < 19.5% OSHA -> MUST TRIP SAFE!)
I_o2_loop  0 o2_sens DC 17.376m PWL(0 17.376m 14.9m 17.376m 15.0m 16.16m 45m 16.16m)
R_burd_o2  o2_sens 0 250.0
X_o2_lo    o2_sens vref_o2 o2_ok_a v5a 0 LM2903_OC
X_o2_lz    o2_sens vref_lz o2_ok_a v5a 0 LM2903_OC
R_pu_o2    v5a o2_ok_a 10.0k

* =========================================================================
* 6) SINGLE-CHANNEL OPEN-WIRE E-STOP BREAK WITH REAL 2N7002K 24V RELAY DRIVER
* =========================================================================
Vestop_a   es_a 0 DC 5.0 PWL(0 5.0 0.999m 5.0 1.000m 0.0 50m 0.0)
Vestop_b   es_b 0 DC 5.0
X_and_ow   es_a es_b vote_ow v5a 0 CMOS_AND2
R_g_ow     vote_ow g_ow 100
R_pd_ow    g_ow 0 100k
M_drv_ow   coil_n_ow g_ow 0 0 M_2N7002 W=2 L=1
R_coil_ow  v24a coil_n_ow 1150
D_fly_ow   coil_n_ow v24a D_1N4148
S_g7sa_ow  v24a ow_load v24a coil_n_ow SW_G7SA
R_ow_ld    ow_load 0 48.0

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

* 3) Component-Level Welded Ch-A Relay + Zener-Clamped SQJ461EP PMOS + 33 ms Blanking Discrepancy
meas tran sh_i_on   FIND i(L_sh_c) AT=0.5m
meas tran sh_v_on   FIND v(sh_out) AT=0.5m
meas tran sh_v_safe FIND v(sh_out) AT=5.0m
meas tran sh_i_safe FIND i(L_sh_c) AT=5.0m
let sh_i10 = 0.10 * sh_i_on
meas tran sh_t_drop_abs WHEN i(L_sh_c)=$&sh_i10 FALL=1 TD=0.99m
let sh_drop_ms = (sh_t_drop_abs - 1.0m) * 1e3
let v_pmos_sg = v(sh_mid_ab) - v(ssr1_gate)
meas tran pmos_vgs_on_v FIND v_pmos_sg AT=0.5m
meas tran discrep_fault_v FIND v(discrep_fault) AT=42.0m
print sh_drop_ms pmos_vgs_on_v discrep_fault_v

* 4) 10 ms Relay/SSR Turn-On Skew Blanking (peak filtered voltage stays < 2.0 V -> zero nuisance trip!)
meas tran skew_blank_peak_v MAX v(disc_sk_rc) FROM=0 TO=20m
print skew_blank_peak_v

* 5) 4-20 mA Live-Zero PH3 Window & 19.5% OSHA O2 Comparator Verification
meas tran ph3_healthy_5ma_v   FIND v(ph3_ok_a) AT=5.0m
meas tran ph3_openwire_0ma_v  FIND v(ph3_ok_a) AT=18.0m
meas tran ph3_leak_12ma_v     FIND v(ph3_ok_a) AT=35.0m
meas tran o2_healthy_20p9_v   FIND v(o2_ok_a)  AT=5.0m
meas tran o2_osha_19p0_trip_v FIND v(o2_ok_a)  AT=25.0m
print ph3_healthy_5ma_v ph3_openwire_0ma_v ph3_leak_12ma_v o2_healthy_20p9_v o2_osha_19p0_trip_v

* 6) Open-Wire E-Stop Break via Real 2N7002K + 24 V G7SA Coil
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
    pmos_vgs = float(m.get("pmos_vgs_on_v", 99.0))
    skew_pk = float(m.get("skew_blank_peak_v", 99.0))
    ph3_ok = float(m.get("ph3_healthy_5ma_v", 0.0))
    ph3_ow = float(m.get("ph3_openwire_0ma_v", 99.0))
    ph3_lk = float(m.get("ph3_leak_12ma_v", 99.0))
    o2_ok = float(m.get("o2_healthy_20p9_v", 0.0))
    o2_trip = float(m.get("o2_osha_19p0_trip_v", 99.0))

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
        "pmos_vgs_zener_clamped_lt_15v": 8.0 < pmos_vgs < 15.0,
        "skew_blanking_no_nuisance_trip": skew_pk < 2.0,
        "fault_discrepancy_comparator_triggered": disc_v > 4.5,
        "live_zero_ph3_openwire_and_leak_trip_safe": ph3_ok > 4.5 and ph3_ow < 0.3 and ph3_lk < 0.3,
        "osha_o2_19p5pct_trip_safe": o2_ok > 4.5 and o2_trip < 0.3,
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
                "pmos_vgs_clamped_v": round(pmos_vgs, 3),
                "skew_blank_peak_v": round(skew_pk, 3),
                "discrepancy_fault_asserted_v": round(disc_v, 3),
                "ph3_healthy_5ma_v": round(ph3_ok, 3),
                "ph3_openwire_0ma_v": round(ph3_ow, 3),
                "ph3_leak_12ma_v": round(ph3_lk, 3),
                "o2_healthy_20p9_v": round(o2_ok, 3),
                "o2_osha_19p0_trip_v": round(o2_trip, 3),
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
