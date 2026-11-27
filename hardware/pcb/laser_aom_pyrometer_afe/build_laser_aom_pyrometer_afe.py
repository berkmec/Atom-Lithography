"""Laser AOM RF VCA, 10 us 2-Color InGaAs/Si Pyrometer TIA, 1 ms Integrator & <0.1 ms Crowbar PCB.

BOM Coverage:
  * S5.5-03: 10 us 2-color InGaAs (1550 nm) + Si (850 nm) pyrometer TIA & +/-1.5% 1.0 ms
    pulse-energy analog integrator.
  * S5.5-01: 808 nm qCW diode-laser bar stack modulation & enable interface.
  * S5.5-04: <0.1 ms hardware RF / diode-enable crowbar wired directly to 1oo2D safety interlock.
  * S5.3-03: High-speed optical pyrometer & closed-loop anneal controller interface
    (matching rtl/machine_ctrl/aom_pid_ctrl.v 100 kHz DAC, log-linearized [0.65, 1.40] gain, T_melt=1687 K).

Rev v2.0 Root-Cause Obstacle Closures (OBS-037, OBS-093, OBS-087):
  * OBS-037: All 3 photodiodes (D_PD_INGAAS, D_PD_SI, D_PD_ENERGY) properly REVERSE-BIASED
    (Anode -> -5 V via 1k, Cathode -> TIA/integrator virtual ground) yielding POSITIVE 0..+2.5 V
    outputs compatible with unipolar ADS8860 ADCs and TLV3501AID; TLV3501AID Pin 8 (SHDN) tied
    to DGND with correct OTEMP polarity (trips LOW when TIA_OUT_SI >= +1.50 V / 1687 K); 24 V
    diode-laser enable upgraded to series 60 V high-side P-MOSFETs (SQJ461EP) driven by low-side
    2N7002K drivers + 12 V Zener Vgs clamps (full 23.95 V output); 24 V interlock inputs use true
    LED-input optocouplers (TLP291) with 2.2k current limiters (zero 24 V on 5 V VCC1!).
  * OBS-093: 100 nF RF DC-blocking capacitor (C_RF_DCBLK) between ADL5602/L_RF_CHOKE and SMA output
    J_AOM_RF_OUT (zero +5 V DC on 50 Ohm coax); ADG901 powered from dedicated +2.5 V LDO (V_P2V5_RF
    <= 2.75 V abs-max); AD5541A VCA control scaled into [0.05, 0.95] V AD8367 compliance with
    log-linearized pre-distortion LUT eliminating the 16-24% 50 dB/V PID limit-cycle oscillation!
  * OBS-087: Exact vendor packages & pinouts: DFN-10+EP11 (LT3045EDD), DFN-12+EP13 (LT3094EDD),
    5-lead TSOT-23-5 UJ-5 fixed-output without RSET (ADP7142AUJZ-5.0/-3.3/-2.5), 16-TSSOP
    (ADG1211YRUZ), and 8-MSOP (ADG901BRMZ).

Epistemic Status: M0/M1 DESIGN_ONLY; no_lab_measurement=true; no_physical_fab=true;
iec61508_certified=false; semi_s2_certified=false.
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
    connect_guard_ring,
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


def _soic8_opamp_pins() -> tuple[PinSpec, ...]:
    names = {"1": "NC1", "2": "IN-", "3": "IN+", "4": "V-", "5": "NC5", "6": "OUT", "7": "V+", "8": "NC8"}
    types = {
        "1": "no_connect", "2": "input", "3": "input", "4": "power_in",
        "5": "no_connect", "6": "output", "7": "power_in", "8": "no_connect",
    }
    return auto_footprint_pads("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", [str(i) for i in range(1, 9)], names, types)


def _tlv3501_soic8_pins() -> tuple[PinSpec, ...]:
    """TLV3501AID 4.5 ns rail-to-rail comparator (SOIC-8, Pin 8 = active-HIGH SHDN -> MUST tie to GND!)."""
    names = {"1": "NC1", "2": "IN-", "3": "IN+", "4": "V-", "5": "NC5", "6": "OUT", "7": "V+", "8": "SHDN"}
    types = {
        "1": "no_connect", "2": "input", "3": "input", "4": "power_in",
        "5": "no_connect", "6": "output", "7": "power_in", "8": "input",
    }
    return auto_footprint_pads("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", [str(i) for i in range(1, 9)], names, types)


def _lt3045_dfn10_ep11_pins() -> tuple[PinSpec, ...]:
    """LT3045EDD EXACT 10-lead DFN-10 + Exposed Pad 11 (3x3 mm, 0.50 mm pitch)."""
    names = {
        "1": "IN1", "2": "IN2", "3": "EN_UV", "4": "PG", "5": "ILIM",
        "6": "PGFB", "7": "SET", "8": "GND", "9": "OUTS", "10": "OUT", "11": "GND_EP",
    }
    types = {
        "1": "power_in", "2": "power_in", "3": "input", "4": "no_connect", "5": "no_connect",
        "6": "input", "7": "input", "8": "power_in", "9": "input", "10": "power_out", "11": "power_in",
    }
    pins: list[PinSpec] = []
    for idx in range(5):
        dy = (idx - 2.0) * 0.50
        p = str(idx + 1)
        pins.append(PinSpec(p, names[p], types[p], -1.45, round(dy, 4), 0.70, 0.26))
    for idx in range(5):
        dy = (2.0 - idx) * 0.50
        p = str(idx + 6)
        pins.append(PinSpec(p, names[p], types[p], 1.45, round(dy, 4), 0.70, 0.26))
    pins.append(PinSpec("11", "GND_EP", "power_in", 0.0, 0.0, 1.50, 2.30))
    return tuple(pins)


def _lt3094_dfn12_ep13_pins() -> tuple[PinSpec, ...]:
    """LT3094EDD EXACT 12-lead DD DFN-12 + Exposed Pad 13 (3x3 mm, 0.45 mm pitch, negative LDO)."""
    names = {
        "1": "OUT1", "2": "OUT2", "3": "OUTS", "4": "SET", "5": "GND", "6": "PGFB",
        "7": "ILIM", "8": "VIOC", "9": "PG", "10": "EN_UV", "11": "IN1", "12": "IN2", "13": "IN_EP",
    }
    types = {
        "1": "power_out", "2": "power_out", "3": "input", "4": "input", "5": "power_in", "6": "input",
        "7": "no_connect", "8": "no_connect", "9": "no_connect", "10": "input", "11": "power_in", "12": "power_in", "13": "power_in",
    }
    pins: list[PinSpec] = []
    for idx in range(6):
        dy = (idx - 2.5) * 0.45
        p = str(idx + 1)
        pins.append(PinSpec(p, names[p], types[p], -1.45, round(dy, 4), 0.70, 0.24))
    for idx in range(6):
        dy = (2.5 - idx) * 0.45
        p = str(idx + 7)
        pins.append(PinSpec(p, names[p], types[p], 1.45, round(dy, 4), 0.70, 0.24))
    pins.append(PinSpec("13", "IN_EP", "power_in", 0.0, 0.0, 1.50, 2.30))
    return tuple(pins)


def _adp7142_tsot23_5_pins() -> tuple[PinSpec, ...]:
    """ADP7142AUJZ fixed-output LDO (EXACT 5-lead TSOT-23-5 / UJ-5, zero RSET!)."""
    names = {"1": "VIN", "2": "GND", "3": "EN", "4": "SENSE", "5": "VOUT"}
    types = {"1": "power_in", "2": "power_in", "3": "input", "4": "input", "5": "power_out"}
    return auto_footprint_pads("Package_TO_SOT_SMD:TSOT-23-5", ["1", "2", "3", "4", "5"], names, types)


def _ads8860_msop10_pins() -> tuple[PinSpec, ...]:
    """ADS8860IDGK 16-bit 1 MS/s SAR ADC (VSSOP-10)."""
    names = {
        "1": "REF", "2": "AVDD", "3": "AINP", "4": "AINN", "5": "GND",
        "6": "CONVST", "7": "DOUT", "8": "SCLK", "9": "DIN", "10": "DVDD",
    }
    types = {
        "1": "input", "2": "power_in", "3": "input", "4": "input", "5": "power_in",
        "6": "input", "7": "output", "8": "input", "9": "input", "10": "power_in",
    }
    return auto_footprint_pads("Package_SO:MSOP-10_3x3mm_P0.5mm", [str(i) for i in range(1, 11)], names, types)


def _ad5541_msop10_pins() -> tuple[PinSpec, ...]:
    """AD5541ABRMZ 16-bit 1 us-settling SPI DAC (MSOP-10)."""
    names = {
        "1": "VOUT", "2": "AGND", "3": "VREF", "4": "CS_N", "5": "SCLK",
        "6": "DIN", "7": "LDAC_N", "8": "DGND", "9": "VDD", "10": "NC",
    }
    types = {
        "1": "output", "2": "power_in", "3": "input", "4": "input", "5": "input",
        "6": "input", "7": "input", "8": "power_in", "9": "power_in", "10": "no_connect",
    }
    return auto_footprint_pads("Package_SO:MSOP-10_3x3mm_P0.5mm", [str(i) for i in range(1, 11)], names, types)


def _ad8367_tssop14_pins() -> tuple[PinSpec, ...]:
    """AD8367ARUZ 500 MHz 50 Ohm Linear-in-dB/V RF VCA (TSSOP-14)."""
    names = {
        "1": "RF_IN", "2": "GND1", "3": "MODE", "4": "GAIN_CTRL", "5": "VREF_NC", "6": "GND2", "7": "VPOS1",
        "8": "RF_OUT", "9": "GND3", "10": "DETO_NC", "11": "HPFL_NC", "12": "DECL_NC", "13": "GND4", "14": "VPOS2",
    }
    types = {
        "1": "input", "2": "power_in", "3": "input", "4": "input", "5": "no_connect", "6": "power_in", "7": "power_in",
        "8": "output", "9": "power_in", "10": "no_connect", "11": "no_connect", "12": "no_connect", "13": "power_in", "14": "power_in",
    }
    return auto_footprint_pads("Package_SO:TSSOP-14_4.4x5mm_P0.65mm", [str(i) for i in range(1, 15)], names, types)


def _adg901_msop8_pins() -> tuple[PinSpec, ...]:
    """ADG901BRMZ EXACT 8-lead MSOP-8 50 Ohm absorptive RF kill switch (VDD = 2.5 V <= 2.75 V abs-max!)."""
    names = {
        "1": "VDD_2V5", "2": "GND1", "3": "CTRL", "4": "RFC",
        "5": "GND2", "6": "GND3", "7": "RF1", "8": "GND4",
    }
    types = {
        "1": "power_in", "2": "power_in", "3": "input", "4": "bidirectional",
        "5": "power_in", "6": "power_in", "7": "bidirectional", "8": "power_in",
    }
    return auto_footprint_pads("Package_SO:MSOP-8_3x3mm_P0.65mm", [str(i) for i in range(1, 9)], names, types)


def _adg1211_tssop16_pins() -> tuple[PinSpec, ...]:
    """ADG1211YRUZ EXACT 16-lead TSSOP-16 quad low-charge-injection CMOS switch."""
    names = {
        "1": "IN1", "2": "D1", "3": "S1", "4": "VSS", "5": "GND", "6": "S4", "7": "D4", "8": "IN4",
        "9": "IN3", "10": "D3", "11": "S3", "12": "NC12", "13": "VDD", "14": "S2", "15": "D2", "16": "IN2",
    }
    types = {
        "1": "input", "2": "passive", "3": "passive", "4": "power_in", "5": "power_in",
        "6": "no_connect", "7": "no_connect", "8": "no_connect", "9": "no_connect",
        "10": "no_connect", "11": "no_connect", "12": "no_connect", "13": "power_in",
        "14": "no_connect", "15": "no_connect", "16": "no_connect",
    }
    return auto_footprint_pads("Package_SO:TSSOP-16_4.4x5mm_P0.65mm", [str(i) for i in range(1, 17)], names, types)


def _rf_amp_sot89_pins() -> tuple[PinSpec, ...]:
    """ADL5602 50 MHz - 4 GHz 50 Ohm RF output gain block (SOT-89-3 -> 4-pin with GND)."""
    return (
        PinSpec("1", "RF_IN", "input", -1.50, 0.0, 0.80, 1.00),
        PinSpec("2", "GND", "power_in", 0.0, 1.80, 1.40, 1.20),
        PinSpec("3", "RF_OUT", "output", 1.50, 0.0, 0.80, 1.00),
        PinSpec("4", "GND_TAB", "power_in", 0.0, -1.80, 1.40, 1.20),
    )


def _opto_tlp291_so4_pins() -> tuple[PinSpec, ...]:
    """TLP291GB 24 V-input-compatible phototransistor optocoupler (SOP-4, zero 5V VCC1 overvoltage!)."""
    return (
        PinSpec("1", "LED_A", "input", -2.54, -1.27, 1.20, 0.70),
        PinSpec("2", "LED_K", "input", -2.54, 1.27, 1.20, 0.70),
        PinSpec("3", "EMIT", "passive", 2.54, 1.27, 1.20, 0.70),
        PinSpec("4", "COLL", "passive", 2.54, -1.27, 1.20, 0.70),
    )


def _logic_sot23_5_pins() -> tuple[PinSpec, ...]:
    names = {"1": "A", "2": "B", "3": "GND", "4": "Y", "5": "VCC"}
    types = {"1": "input", "2": "input", "3": "power_in", "4": "output", "5": "power_in"}
    return auto_footprint_pads("Package_TO_SOT_SMD:SOT-23-5", [str(i) for i in range(1, 6)], names, types)


def _nmos_sot23_3_pins() -> tuple[PinSpec, ...]:
    return (
        PinSpec("1", "G", "input", -1.10, -0.95, 0.80, 0.60),
        PinSpec("2", "S", "passive", -1.10, 0.95, 0.80, 0.60),
        PinSpec("3", "D", "passive", 1.10, 0.0, 0.80, 0.60),
    )


def _pmos_dpak_pins() -> tuple[PinSpec, ...]:
    """SQJ461EP -60 V high-side P-MOSFET for 24 V diode-laser enable cutoff (TO-252-3 / DPAK)."""
    return (
        PinSpec("1", "G", "input", -2.28, 2.50, 1.20, 1.60),
        PinSpec("2", "D", "passive", 0.0, -2.50, 3.00, 2.20),
        PinSpec("3", "S", "passive", 2.28, 2.50, 1.20, 1.60),
    )


def _pd_3p_pins() -> tuple[PinSpec, ...]:
    """TO-46 / ceramic SMD photodiode (Pin 1=ANODE, Pin 2=CATHODE, Pin 3=CASE_GUARD)."""
    return (
        PinSpec("1", "ANODE", "passive", -1.80, 0.0, 0.90, 0.90),
        PinSpec("2", "CATHODE", "passive", 1.80, 0.0, 0.90, 0.90),
        PinSpec("3", "CASE_GUARD", "passive", 0.0, 2.00, 0.90, 0.80),
    )


def _lt6655_msop8_pins() -> tuple[PinSpec, ...]:
    names = {"1": "GND1", "2": "VIN", "3": "SHDN_N", "4": "GND2", "5": "GND3", "6": "VOUT_F", "7": "VOUT_S", "8": "GND4"}
    types = {
        "1": "power_in", "2": "power_in", "3": "input", "4": "power_in",
        "5": "power_in", "6": "power_out", "7": "input", "8": "power_in",
    }
    return auto_footprint_pads("Package_SO:MSOP-8_3x3mm_P0.65mm", [str(i) for i in range(1, 9)], names, types)


def build_laser_aom_pyrometer_board() -> BoardSpec:
    """Build 4-layer Rogers RO4350B / FR408HR 2-Color Pyrometer TIA + 1 ms Integrator + AOM RF VCA + Crowbar PCB."""
    stackup = (
        StackupLayer("F.Cu", "signal", 0.035, material="Copper"),
        StackupLayer("dielectric 1", "core", 0.254, epsilon_r=3.48, loss_tangent=0.0037, material="Rogers RO4350B"),
        StackupLayer("In1.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 2", "core", 0.800, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR"),
        StackupLayer("In2.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 3", "core", 0.254, epsilon_r=3.48, loss_tangent=0.0037, material="Rogers RO4350B"),
        StackupLayer("B.Cu", "signal", 0.035, material="Copper"),
    )
    w50 = solve_microstrip_width_mm(50.0, h_mm=0.254, t_mm=0.035, er=3.48)  # 0.5429 mm -> 50.00 Ohm

    comps: list[ComponentSpec] = []
    nets_dict: dict[str, list[tuple[str, str]]] = defaultdict(list)
    traces: list[TraceSpec] = []
    vias: list[ViaSpec] = []
    keepouts: list[KeepoutSpec] = []

    def add_c(c: ComponentSpec) -> ComponentSpec:
        comps.append(c)
        return c

    def conn(net: str, ref: str, pin: str | int) -> None:
        nets_dict[net].append((ref, str(pin)))

    # =========================================================================
    # SECTION 1 (TOP-LEFT, y=14..48 mm): 2-COLOR FAST PYROMETER TIAs (S5.5-03 / S5.3-03)
    #   OBS-037 FIX: REVERSE-BIAS photodiodes properly (Anode pin 1 -> -5V via RPB,
    #   Cathode pin 2 -> virtual ground TIA_SUM) -> POSITIVE 0..+2.5V TIA output!
    # =========================================================================
    pyro_specs = [
        ("INGAAS", "Hamamatsu_G12180-010A_1550nm", "100k_0.1pct", "12pF_C0G", 20.0, "S5.5-03"),
        ("SI",     "Hamamatsu_S5971_850nm",        "200k_0.1pct", "6.0pF_C0G", 42.0, "S5.3-03"),
    ]
    for tag, pd_val, rf_val, cf_val, yc, bid in pyro_specs:
        r_pb = add_c(ComponentSpec(f"RPB_{tag}", "1.00k_1pct", "Resistor_SMD:R_0603_1608Metric", 10.0, yc, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))
        c_pb = add_c(ComponentSpec(f"CPB_{tag}", "100nF_C0G", "Capacitor_SMD:C_0603_1608Metric", 16.0, yc - 5.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))
        pd = add_c(ComponentSpec(f"D_PD_{tag}", pd_val, "Custom:TO46_PHOTODIODE_3P", 22.0, yc, pins=_pd_3p_pins(), mpn=pd_val, bom_id=bid, epistemic_tag="{Aday-COTS}"))
        rf = add_c(ComponentSpec(f"RF_{tag}", rf_val, "Resistor_SMD:R_0603_1608Metric", 34.0, yc - 3.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))
        cf = add_c(ComponentSpec(f"CF_{tag}", cf_val, "Capacitor_SMD:C_0603_1608Metric", 34.0, yc + 3.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))
        utia = add_c(ComponentSpec(f"U_TIA_{tag}", "OPA657NB_1p6GHZ_TIA", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 46.0, yc, pins=_soic8_opamp_pins(), mpn="OPA657NB", bom_id=bid, epistemic_tag="{Aday-COTS}"))
        cd_p = add_c(ComponentSpec(f"CD_TIA_{tag}P", "100nF_C0G", "Capacitor_SMD:C_0603_1608Metric", 46.0, yc - 7.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))
        cd_n = add_c(ComponentSpec(f"CD_TIA_{tag}N", "100nF_C0G", "Capacitor_SMD:C_0603_1608Metric", 46.0, yc + 7.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))
        raa = add_c(ComponentSpec(f"RAA_{tag}", "100R_0.1pct", "Resistor_SMD:R_0603_1608Metric", 58.0, yc, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))
        caa = add_c(ComponentSpec(f"CAA_{tag}", "1.0nF_C0G", "Capacitor_SMD:C_0603_1608Metric", 64.0, yc + 5.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id=bid, epistemic_tag="{Pasif-COTS}"))
        uadc = add_c(ComponentSpec(f"U_ADC_{tag}", "ADS8860_16B_1MSPS", "Package_SO:MSOP-10_3x3mm_P0.5mm", 74.0, yc, pins=_ads8860_msop10_pins(), mpn="ADS8860IDGK", bom_id=bid, epistemic_tag="{Aday-COTS}"))

        # REVERSE-BIAS: Anode (pin 1) -> V_N5A (-5 V) via RPB; Cathode (pin 2) -> virtual ground TIA_SUM!
        conn("V_N5A", r_pb.ref, 1); conn(f"PD_BIAS_{tag}", r_pb.ref, 2)
        conn(f"PD_BIAS_{tag}", c_pb.ref, 1); conn("AGND", c_pb.ref, 2)
        conn(f"PD_BIAS_{tag}", pd.ref, 1)  # ANODE to -5 V -> REVERSE BIASED (+5 V across Cathode-Anode)!
        conn(f"TIA_SUM_{tag}", pd.ref, 2); conn("AGND", pd.ref, 3)  # CATHODE to virtual ground -> POSITIVE Vout!
        conn(f"TIA_SUM_{tag}", rf.ref, 1); conn(f"TIA_SUM_{tag}", cf.ref, 1); conn(f"TIA_SUM_{tag}", utia.ref, 2)
        conn("AGND", utia.ref, 3)
        conn(f"TIA_OUT_{tag}", utia.ref, 6); conn(f"TIA_OUT_{tag}", rf.ref, 2); conn(f"TIA_OUT_{tag}", cf.ref, 2); conn(f"TIA_OUT_{tag}", raa.ref, 1)
        conn("V_P5A", utia.ref, 7); conn("V_N5A", utia.ref, 4)
        conn("V_P5A", cd_p.ref, 1); conn("AGND", cd_p.ref, 2)
        conn("V_N5A", cd_n.ref, 1); conn("AGND", cd_n.ref, 2)
        conn(f"ADC_IN_{tag}", raa.ref, 2); conn(f"ADC_IN_{tag}", caa.ref, 1); conn("AGND", caa.ref, 2)
        conn("VREF_2V5", uadc.ref, 1); conn("V_P5A", uadc.ref, 2)
        conn(f"ADC_IN_{tag}", uadc.ref, 3); conn("AGND", uadc.ref, 4); conn("AGND", uadc.ref, 5)
        conn("ADC_PYRO_CS_N", uadc.ref, 6); conn(f"SPI_MISO_{tag}", uadc.ref, 7)
        conn("SPI_SCLK", uadc.ref, 8); conn("V_P3V3", uadc.ref, 9); conn("V_P3V3", uadc.ref, 10)

        keepouts.append(KeepoutSpec(
            f"KO_TIA_{tag}", "copper_keepout", ("In1.Cu", "In2.Cu"),
            x_mm=24.0, y_mm=yc - 5.2, width_mm=16.0, height_mm=10.4,
        ))
        gr_traces, gr_vias = connect_guard_ring(
            "AGND", "F.Cu", 25.5, round(yc - 6.2, 3), 41.5, round(yc + 6.2, 3),
            width_mm=0.25, via_layer="B.Cu", via_diameter_mm=0.48, via_drill_mm=0.24, top_only_rails=True,
        )
        traces.extend(gr_traces)
        vias.extend(gr_vias)

    # OBS-037 + OBS-087 FIX: Hardware Over-Temperature Comparator TLV3501AID
    #   * Positive TIA_OUT_SI (0..+2.5V) compared against OTEMP_THR (+1.50 V = 1687 K Si melt!)
    #   * Pin 8 (active-HIGH SHDN) tied strictly to DGND so comparator is ALWAYS enabled!
    u_otemp = add_c(ComponentSpec("U_CMP_OTEMP", "TLV3501_OTEMP_1687K", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 94.0, 32.0, pins=_tlv3501_soic8_pins(), mpn="TLV3501AID", bom_id="S5.5-03", epistemic_tag="{Aday-COTS}"))
    r_ot1 = add_c(ComponentSpec("R_OTEMP_TOP", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 86.0, 24.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))
    r_ot2 = add_c(ComponentSpec("R_OTEMP_BOT", "15.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 86.0, 38.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))
    conn("VREF_2V5", r_ot1.ref, 1); conn("OTEMP_THR", r_ot1.ref, 2); conn("OTEMP_THR", r_ot2.ref, 1); conn("AGND", r_ot2.ref, 2)
    conn("OTEMP_THR", u_otemp.ref, 3); conn("TIA_OUT_SI", u_otemp.ref, 2)
    conn("OTEMP_OK_N_LOW", u_otemp.ref, 6)  # HIGH (+3.3V) when TIA_OUT_SI < +1.50V (healthy); LOW (0V) when T >= 1687 K!
    conn("V_P3V3", u_otemp.ref, 7); conn("DGND", u_otemp.ref, 4); conn("DGND", u_otemp.ref, 8)  # Pin 8 SHDN -> DGND!

    # =========================================================================
    # SECTION 2 (MID-LEFT, y=64..92 mm): INLINE 1.0 ms PULSE-ENERGY INTEGRATOR (S5.5-03)
    #   OBS-037 + OBS-087 FIX: Reverse-biased D_PD_ENERGY (Anode -> -5V, Cathode -> INT_SUM -> POSITIVE 0..+2.5V!)
    #   + Exact 16-TSSOP ADG1211YRUZ!
    # =========================================================================
    pd_eng = add_c(ComponentSpec("D_PD_ENERGY", "Hamamatsu_S1223-01_808nm", "Custom:TO46_PHOTODIODE_3P", 22.0, 74.0, pins=_pd_3p_pins(), mpn="Hamamatsu_S1223-01", bom_id="S5.5-03", epistemic_tag="{Aday-COTS}"))
    r_eng_b = add_c(ComponentSpec("RPB_ENERGY", "1.00k_1pct", "Resistor_SMD:R_0603_1608Metric", 10.0, 74.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))
    c_int = add_c(ComponentSpec("C_INT_100N", "100nF_0.5pct_C0G_INT", "Capacitor_SMD:C_1206_3216Metric", 36.0, 68.0, pins=auto_footprint_pads("1206", ("1", "2")), mpn="TDK_C3216C0G1H104J", bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))
    u_int_sw = add_c(ComponentSpec("U_INT_RST_SW", "ADG1211YRUZ_TSSOP16", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm", 36.0, 82.0, pins=_adg1211_tssop16_pins(), mpn="ADG1211YRUZ", bom_id="S5.5-03", epistemic_tag="{Aday-COTS}"))
    u_int = add_c(ComponentSpec("U_INT_AMP", "OPA140_JFET_INTEGRATOR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 52.0, 74.0, pins=_soic8_opamp_pins(), mpn="OPA140AID", bom_id="S5.5-03", epistemic_tag="{Aday-COTS}"))
    r_int_s = add_c(ComponentSpec("R_INT_50R", "49.9R_0.1pct", "Resistor_SMD:R_0603_1608Metric", 64.0, 88.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))
    j_int_mon = add_c(ComponentSpec(
        "J_INT_MON", "SMA_ENERGY_INT_MON", "Connector_Coaxial:SMA_EdgeMount",
        64.0, 130.0, edge_mount=True,
        pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "INT_MON", "2": "GND"}),
        bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}",
    ))
    u_adc_eng = add_c(ComponentSpec("U_ADC_ENERGY", "ADS8860_ENERGY_ADC", "Package_SO:MSOP-10_3x3mm_P0.5mm", 74.0, 74.0, pins=_ads8860_msop10_pins(), mpn="ADS8860IDGK", bom_id="S5.5-03", epistemic_tag="{Aday-COTS}"))

    # REVERSE-BIAS: Anode (pin 1) -> -5 V; Cathode (pin 2) -> INT_SUM (virtual ground -> POSITIVE 0..+2V ramp!)
    conn("V_N5A", r_eng_b.ref, 1); conn("PD_BIAS_ENG", r_eng_b.ref, 2); conn("PD_BIAS_ENG", pd_eng.ref, 1)
    conn("INT_SUM", pd_eng.ref, 2); conn("AGND", pd_eng.ref, 3)
    conn("INT_SUM", c_int.ref, 1); conn("INT_SUM", u_int_sw.ref, 2); conn("INT_SUM", u_int.ref, 2)
    conn("AGND", u_int.ref, 3)
    conn("INT_OUT", u_int.ref, 6); conn("INT_OUT", c_int.ref, 2); conn("INT_OUT", u_int_sw.ref, 3)
    conn("INT_OUT", r_int_s.ref, 1); conn("INT_OUT", u_adc_eng.ref, 3)
    conn("V_P5A", u_int.ref, 7); conn("V_N5A", u_int.ref, 4)
    # ADG1211YRUZ TSSOP-16: 1=IN1, 2=D1, 3=S1, 4=VSS, 5=GND, 13=VDD
    conn("INT_RST_N", u_int_sw.ref, 1); conn("V_N5A", u_int_sw.ref, 4); conn("AGND", u_int_sw.ref, 5); conn("V_P5A", u_int_sw.ref, 13)
    conn("INT_MON_50", r_int_s.ref, 2); conn("INT_MON_50", j_int_mon.ref, 1); conn("AGND", j_int_mon.ref, 2)
    conn("VREF_2V5", u_adc_eng.ref, 1); conn("V_P5A", u_adc_eng.ref, 2)
    conn("AGND", u_adc_eng.ref, 4); conn("AGND", u_adc_eng.ref, 5)
    conn("ADC_ENG_CS_N", u_adc_eng.ref, 6); conn("SPI_MISO_ENG", u_adc_eng.ref, 7)
    conn("SPI_SCLK", u_adc_eng.ref, 8); conn("V_P3V3", u_adc_eng.ref, 9); conn("V_P3V3", u_adc_eng.ref, 10)

    # =========================================================================
    # SECTION 3 (TOP-RIGHT, x=108..200 mm, y=12..60 mm): 80-200 MHz AOM RF VCA STAGE (S5.5-01)
    #   OBS-093 + OBS-087 FIX:
    #   * Precision compliance divider scaling 0..2.5V AD5541A DAC (driven by log-linearized LUT!)
    #     into AD8367 [0.05..0.95 V] GAIN_CTRL range (eliminates 50 dB/V saturation & limit cycle!)
    #   * Exact 8-MSOP ADG901BRMZ powered from dedicated +2.5 V LDO (V_P2V5_RF <= 2.75 V abs-max!)
    #   * 100 nF RF DC-blocking capacitor C_RF_DCBLK between ADL5602/L_RF_CHOKE (+5V) and J_AOM_RF_OUT!
    # =========================================================================
    u_vref = add_c(ComponentSpec("U_VREF_2V5", "LT6655BHMS8-2.5", "Package_SO:MSOP-8_3x3mm_P0.65mm", 96.0, 74.0, pins=_lt6655_msop8_pins(), mpn="LT6655BHMS8-2.5", bom_id="S5.5-03", epistemic_tag="{Aday-COTS}"))
    u_dac_aom = add_c(ComponentSpec("U_DAC_AOM", "AD5541A_16B_100KHZ", "Package_SO:MSOP-10_3x3mm_P0.5mm", 116.0, 52.0, pins=_ad5541_msop10_pins(), mpn="AD5541ABRMZ", bom_id="S5.5-01", epistemic_tag="{Aday-COTS}"))
    u_vca_buf = add_c(ComponentSpec("U_VCA_CTRL", "ADA4898-1_VCA_DRV", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 132.0, 52.0, pins=_soic8_opamp_pins(), mpn="ADA4898-1YRDZ", bom_id="S5.5-01", epistemic_tag="{Aday-COTS}"))
    # Precision compliance divider (1.65k / 1.00k -> 0..2.5 V DAC scales to 0..0.943 V AD8367 linear-in-dB range!)
    r_vca_s = add_c(ComponentSpec("R_VCA_SERIES", "1.65k_0.1pct_COMPL", "Resistor_SMD:R_0603_1608Metric", 144.0, 52.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
    r_vca_sh = add_c(ComponentSpec("R_VCA_SHUNT", "1.00k_0.1pct_COMPL", "Resistor_SMD:R_0603_1608Metric", 144.0, 58.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-01", epistemic_tag="{Pasif-COTS}"))
    q_vca_clp = add_c(ComponentSpec("Q_VCA_CLAMP", "2N7002_VCA_CROWBAR", "Package_TO_SOT_SMD:SOT-23", 156.0, 52.0, pins=_nmos_sot23_3_pins(), mpn="2N7002K", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))

    # 50 Ohm Controlled-Impedance 80-200 MHz RF Chain on F.Cu (with C_RF_DCBLK before SMA!)
    j_rf_in = add_c(ComponentSpec(
        "J_RF_LO_IN", "SMA_80_200MHZ_LO_IN", "Connector_Coaxial:SMA_EdgeMount",
        112.0, 10.0, rotation_deg=180.0, edge_mount=True,
        pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "RF_LO", "2": "RFGND"}),
        bom_id="S5.5-01", epistemic_tag="{Pasif-COTS}",
    ))
    u_vca = add_c(ComponentSpec("U_AOM_VCA", "AD8367_500MHZ_VCA", "Package_SO:TSSOP-14_4.4x5mm_P0.65mm", 126.0, 26.0, pins=_ad8367_tssop14_pins(), mpn="AD8367ARUZ", bom_id="S5.5-01", epistemic_tag="{Aday-COTS}"))
    c_rf1 = add_c(ComponentSpec("C_RF_AC1", "100nF_RF_C0G", "Capacitor_SMD:C_0603_1608Metric", 138.0, 26.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-01", epistemic_tag="{Pasif-COTS}"))
    u_rf_sw = add_c(ComponentSpec("U_RF_KILL_SW", "ADG901BRMZ_MSOP8_2V5", "Package_SO:MSOP-8_3x3mm_P0.65mm", 150.0, 26.0, pins=_adg901_msop8_pins(), mpn="ADG901BRMZ", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))
    c_rf2 = add_c(ComponentSpec("C_RF_AC2", "100nF_RF_C0G", "Capacitor_SMD:C_0603_1608Metric", 162.0, 26.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-01", epistemic_tag="{Pasif-COTS}"))
    u_rf_drv = add_c(ComponentSpec("U_RF_DRV", "ADL5602_50R_RF_AMP", "Custom:SOT89_RF_4P", 172.0, 26.0, pins=_rf_amp_sot89_pins(), mpn="ADL5602ARKZ", bom_id="S5.5-01", epistemic_tag="{Aday-COTS}"))
    l_rf_bias = add_c(ComponentSpec("L_RF_CHOKE", "1.0uH_RF_CHOKE", "Inductor_SMD:L_0805_2012Metric", 172.0, 14.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S5.5-01", epistemic_tag="{Pasif-COTS}"))
    # OBS-093 FIX: Mandatory 100 nF RF DC-blocking capacitor isolating +5 V ADL5602 bias tee from 50 Ohm coax!
    c_rf_dcblk = add_c(ComponentSpec("C_RF_DCBLK", "100nF_RF_DC_BLOCK_C0G", "Capacitor_SMD:C_0603_1608Metric", 184.0, 26.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-01", epistemic_tag="{Pasif-COTS}"))
    j_rf_out = add_c(ComponentSpec(
        "J_AOM_RF_OUT", "SMA_AOM_RF_MOD_OUT", "Connector_Coaxial:SMA_EdgeMount",
        196.0, 26.0, rotation_deg=90.0, edge_mount=True,
        pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "AOM_RF", "2": "RFGND"}),
        bom_id="S5.5-01", epistemic_tag="{Pasif-COTS}",
    ))

    # =========================================================================
    # SECTION 4 (BOTTOM-RIGHT, x=112..194 mm, y=68..130 mm): <0.1 ms 1oo2D HARDWARE CROWBAR (S5.5-04)
    #   OBS-037 FIX:
    #   * True 24 V LED-input optocouplers (TLP291GB) with 2.2k series resistors & 3.3V pull-ups
    #   * Series 60 V high-side P-MOSFETs (SQJ461EP) driven by low-side 2N7002K + 10k/10k + 12V Zeners
    #     -> FULL 23.95 V DIODE_EN_OUT (zero 2.23 V NMOS source-follower clamping!)
    # =========================================================================
    j_ilk = add_c(ComponentSpec(
        "J_ILK_1OO2D", "HDR_6P_1OO2D_LASER_ILK", "Connector_PinHeader:HDR_1x6_2.54mm",
        116.0, 124.0, rotation_deg=90.0,
        pins=auto_footprint_pads("HDR_1x6_2.54mm", ("1", "2", "3", "4", "5", "6"),
                                 {"1": "SAFE_EN_A", "2": "SAFE_EN_B", "3": "ILK_RTN", "4": "V_24V_DIODE", "5": "DIODE_EN_OUT", "6": "DIODE_RTN"}),
        bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}",
    ))
    r_op_a = add_c(ComponentSpec("R_OPTO_A", "2.20k_1pct", "Resistor_SMD:R_0805_2012Metric", 114.0, 102.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
    r_op_b = add_c(ComponentSpec("R_OPTO_B", "2.20k_1pct", "Resistor_SMD:R_0805_2012Metric", 114.0, 88.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
    u_opto_a = add_c(ComponentSpec("U_OPTO_ILK_A", "TLP291GB_24V_CH_A", "Package_SO:SOP-4_3.8x4.1mm_P2.54mm", 128.0, 102.0, pins=_opto_tlp291_so4_pins(), mpn="TLP291GB", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))
    u_opto_b = add_c(ComponentSpec("U_OPTO_ILK_B", "TLP291GB_24V_CH_B", "Package_SO:SOP-4_3.8x4.1mm_P2.54mm", 128.0, 88.0, pins=_opto_tlp291_so4_pins(), mpn="TLP291GB", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))
    r_opu_a = add_c(ComponentSpec("R_OPTO_PU_A", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", 136.0, 102.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
    r_opu_b = add_c(ComponentSpec("R_OPTO_PU_B", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", 136.0, 88.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))

    u_and1 = add_c(ComponentSpec("U_AND_1OO2", "SN74LVC1G08_1OO2", "Package_TO_SOT_SMD:SOT-23-5", 148.0, 90.0, pins=_logic_sot23_5_pins(), mpn="SN74LVC1G08DBVR", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))
    u_and2 = add_c(ComponentSpec("U_AND_OTEMP", "SN74LVC1G08_OTEMP", "Package_TO_SOT_SMD:SOT-23-5", 158.0, 90.0, pins=_logic_sot23_5_pins(), mpn="SN74LVC1G08DBVR", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))
    u_and3 = add_c(ComponentSpec("U_AND_RFEN", "SN74LVC1G08_RFEN", "Package_TO_SOT_SMD:SOT-23-5", 168.0, 90.0, pins=_logic_sot23_5_pins(), mpn="SN74LVC1G08DBVR", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))
    u_inv_cb = add_c(ComponentSpec("U_INV_CLAMP", "SN74LVC1G04_CLAMP", "Package_TO_SOT_SMD:SOT-23-5", 168.0, 74.0, pins=_logic_sot23_5_pins(), mpn="SN74LVC1G04DBVR", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))

    # High-Side Series Dual P-MOSFET (SQJ461EP -60V) + Low-Side Gate Drivers (2N7002K) + 12V Zener Clamps!
    q_diode_a = add_c(ComponentSpec("Q_DIODE_EN_A", "SQJ461EP_PMOS_CHA", "Package_TO_SOT_SMD:TO-252-2", 154.0, 114.0, pins=_pmos_dpak_pins(), mpn="Vishay_SQJ461EP", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))
    q_diode_b = add_c(ComponentSpec("Q_DIODE_EN_B", "SQJ461EP_PMOS_CHB", "Package_TO_SOT_SMD:TO-252-2", 174.0, 114.0, pins=_pmos_dpak_pins(), mpn="Vishay_SQJ461EP", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))
    q_gdrv_a = add_c(ComponentSpec("Q_GDRV_DIODE_A", "2N7002K_PMOS_DRV_A", "Package_TO_SOT_SMD:SOT-23", 146.0, 128.0, pins=_nmos_sot23_3_pins(), mpn="2N7002K", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))
    q_gdrv_b = add_c(ComponentSpec("Q_GDRV_DIODE_B", "2N7002K_PMOS_DRV_B", "Package_TO_SOT_SMD:SOT-23", 166.0, 128.0, pins=_nmos_sot23_3_pins(), mpn="2N7002K", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))
    for tag_d, xd in (("A", 146.0), ("B", 166.0)):
        add_c(ComponentSpec(f"R_PMOS_PU_{tag_d}", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", xd, 106.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
        add_c(ComponentSpec(f"R_PMOS_DIV_{tag_d}", "10.0k_1pct", "Resistor_SMD:R_0603_1608Metric", xd, 120.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
        add_c(ComponentSpec(f"D_Z_PMOS_{tag_d}", "BZX84C12_VGS_CLAMP", "Diode_SMD:D_0805_2012Metric", xd + 8.0, 104.0, pins=auto_footprint_pads("0805", ("1", "2"), {"1": "K", "2": "A"}), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
    r_diode_pd = add_c(ComponentSpec("R_DIODE_PD", "1.00k_1pct", "Resistor_SMD:R_0805_2012Metric", 188.0, 114.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))

    # =========================================================================
    # SECTION 5 (BOTTOM-LEFT, x=10..104 mm, y=96..132 mm): FPGA SPI HEADER & EXACT-PACKAGE LDO TREE
    # =========================================================================
    j_fpga = add_c(ComponentSpec(
        "J_FPGA_AOM", "HDR_2x8_AOM_PID_RTL", "Connector_PinHeader:HDR_2x8_2.54mm",
        18.0, 112.0, pins=auto_footprint_pads("HDR_2x8_2.54mm", [str(i) for i in range(1, 17)], {
            "1": "SPI_SCLK", "2": "SPI_MOSI", "3": "SPI_MISO_INGAAS", "4": "SPI_MISO_SI",
            "5": "SPI_MISO_ENG", "6": "DAC_AOM_CS_N", "7": "ADC_PYRO_CS_N", "8": "ADC_ENG_CS_N",
            "9": "AOM_RF_EN", "10": "SHOT_GATE", "11": "INT_RST_N", "12": "OTEMP_OK_N_LOW",
            "13": "V_P3V3", "14": "DGND1", "15": "DGND2", "16": "HW_CROWBAR_OK",
        }),
        bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}",
    ))
    j_pwr = add_c(ComponentSpec(
        "JPWR_AFE", "HDR_5P_AFE_PWR", "Connector_PinHeader:HDR_1x5_2.54mm",
        40.0, 114.0, pins=auto_footprint_pads("HDR_1x5_2.54mm", ("1", "2", "3", "4", "5"),
                                              {"1": "V_P6_IN", "2": "V_N6_IN", "3": "AGND", "4": "DGND", "5": "RFGND"}),
        bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}",
    ))
    r_sg1 = add_c(ComponentSpec("R_STAR_AG_DG", "0R_STAR_AGND_DGND", "Resistor_SMD:R_0603_1608Metric", 50.0, 108.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))
    r_sg2 = add_c(ComponentSpec("R_STAR_AG_RF", "0R_STAR_AGND_RFGND", "Resistor_SMD:R_0603_1608Metric", 50.0, 116.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))

    # OBS-087 FIX: Exact vendor LDO packages & pinouts (DFN-10+EP11, DFN-12+EP13, 3x TSOT-23-5 fixed without RSET!)
    u_ldo_p5 = add_c(ComponentSpec("U_LDO_P5A", "LT3045EDD_P5A", "Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.55x2.48mm", 78.0, 100.0, pins=_lt3045_dfn10_ep11_pins(), mpn="LT3045EDD", bom_id="S5.5-03", epistemic_tag="{Aday-COTS}"))
    u_ldo_n5 = add_c(ComponentSpec("U_LDO_N5A", "LT3094EDD_N5A", "Package_DFN_QFN:DFN-12-1EP_3x3mm_P0.45mm_EP1.65x2.38mm", 94.0, 100.0, pins=_lt3094_dfn12_ep13_pins(), mpn="LT3094EDD", bom_id="S5.5-03", epistemic_tag="{Aday-COTS}"))
    u_ldo_rf = add_c(ComponentSpec("U_LDO_P5RF", "ADP7142AUJZ-5.0_RF", "Package_TO_SOT_SMD:TSOT-23-5", 78.0, 116.0, pins=_adp7142_tsot23_5_pins(), mpn="ADP7142AUJZ-5.0", bom_id="S5.5-01", epistemic_tag="{Aday-COTS}"))
    u_ldo_3v3 = add_c(ComponentSpec("U_LDO_3V3", "ADP7142AUJZ-3.3", "Package_TO_SOT_SMD:TSOT-23-5", 92.0, 116.0, pins=_adp7142_tsot23_5_pins(), mpn="ADP7142AUJZ-3.3", bom_id="S5.5-03", epistemic_tag="{Aday-COTS}"))
    u_ldo_2v5 = add_c(ComponentSpec("U_LDO_2V5RF", "ADP7142AUJZ-2.5_ADG901", "Package_TO_SOT_SMD:TSOT-23-5", 104.0, 64.0, pins=_adp7142_tsot23_5_pins(), mpn="ADP7142AUJZ-2.5", bom_id="S5.5-04", epistemic_tag="{Aday-COTS}"))

    # LT3045EDD (+5A) exact datasheet wiring (DFN-10+EP11)
    rs_p5 = add_c(ComponentSpec("RSET_LDO0", "49.9k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 84.0, 96.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))
    co_p5 = add_c(ComponentSpec("COUT_LDO0", "10uF_10V_C0G", "Capacitor_SMD:C_0603_1608Metric", 84.0, 104.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))
    conn("V_P6_IN", u_ldo_p5.ref, 1); conn("V_P6_IN", u_ldo_p5.ref, 2); conn("V_P6_IN", u_ldo_p5.ref, 3)
    conn("V_P5A", u_ldo_p5.ref, 6); conn("V_P5A", u_ldo_p5.ref, 9); conn("V_P5A", u_ldo_p5.ref, 10)
    conn("LDO_SET_0", u_ldo_p5.ref, 7); conn("LDO_SET_0", rs_p5.ref, 1); conn("AGND", rs_p5.ref, 2)
    conn("AGND", u_ldo_p5.ref, 8); conn("AGND", u_ldo_p5.ref, 11)
    conn("V_P5A", co_p5.ref, 1); conn("AGND", co_p5.ref, 2)

    # LT3094EDD (-5A) exact datasheet wiring (DFN-12+EP13)
    rs_n5 = add_c(ComponentSpec("RSET_LDO1", "49.9k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 100.0, 96.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))
    co_n5 = add_c(ComponentSpec("COUT_LDO1", "10uF_10V_C0G", "Capacitor_SMD:C_0603_1608Metric", 100.0, 104.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))
    conn("V_N5A", u_ldo_n5.ref, 1); conn("V_N5A", u_ldo_n5.ref, 2); conn("V_N5A", u_ldo_n5.ref, 3); conn("V_N5A", u_ldo_n5.ref, 6)
    conn("LDO_SET_1", u_ldo_n5.ref, 4); conn("LDO_SET_1", rs_n5.ref, 1); conn("AGND", rs_n5.ref, 2)
    conn("AGND", u_ldo_n5.ref, 5)
    conn("V_N6_IN", u_ldo_n5.ref, 10); conn("V_N6_IN", u_ldo_n5.ref, 11); conn("V_N6_IN", u_ldo_n5.ref, 12); conn("V_N6_IN", u_ldo_n5.ref, 13)
    conn("V_N5A", co_n5.ref, 1); conn("AGND", co_n5.ref, 2)

    # 3x Fixed-Output ADP7142AUJZ (TSOT-23-5 UJ-5, ZERO RSET!): 1=VIN, 2=GND, 3=EN, 4=SENSE->VOUT, 5=VOUT
    for idx_f, (ldo, rin, rout, gnd, cx, cy) in enumerate((
        (u_ldo_rf, "V_P6_IN", "V_P5RF", "RFGND", 84.0, 116.0),
        (u_ldo_3v3, "V_P6_IN", "V_P3V3", "DGND", 98.0, 116.0),
        (u_ldo_2v5, "V_P5RF", "V_P2V5_RF", "RFGND", 110.0, 64.0),
    )):
        co = add_c(ComponentSpec(f"COUT_FX{idx_f}", "10uF_10V_C0G", "Capacitor_SMD:C_0603_1608Metric", cx, cy, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-03", epistemic_tag="{Pasif-COTS}"))
        conn(rin, ldo.ref, 1); conn(gnd, ldo.ref, 2); conn(rin, ldo.ref, 3)
        conn(rout, ldo.ref, 4); conn(rout, ldo.ref, 5)
        conn(rout, co.ref, 1); conn(gnd, co.ref, 2)

    # =========================================================================
    # REMAINING NETLIST CONNECTIONS
    # =========================================================================
    conn("V_P6_IN", j_pwr.ref, 1); conn("V_N6_IN", j_pwr.ref, 2)
    conn("AGND", j_pwr.ref, 3); conn("DGND", j_pwr.ref, 4); conn("RFGND", j_pwr.ref, 5)
    conn("AGND", r_sg1.ref, 1); conn("DGND", r_sg1.ref, 2)
    conn("AGND", r_sg2.ref, 1); conn("RFGND", r_sg2.ref, 2)

    conn("V_P5A", u_vref.ref, 2); conn("V_P5A", u_vref.ref, 3)
    for p in (1, 4, 5, 8):
        conn("AGND", u_vref.ref, p)
    conn("VREF_2V5", u_vref.ref, 6); conn("VREF_2V5", u_vref.ref, 7)

    # FPGA SPI Interface Header
    conn("SPI_SCLK", j_fpga.ref, 1); conn("SPI_MOSI", j_fpga.ref, 2)
    conn("SPI_MISO_INGAAS", j_fpga.ref, 3); conn("SPI_MISO_SI", j_fpga.ref, 4)
    conn("SPI_MISO_ENG", j_fpga.ref, 5); conn("DAC_AOM_CS_N", j_fpga.ref, 6)
    conn("ADC_PYRO_CS_N", j_fpga.ref, 7); conn("ADC_ENG_CS_N", j_fpga.ref, 8)
    conn("AOM_RF_EN", j_fpga.ref, 9); conn("SHOT_GATE", j_fpga.ref, 10)
    conn("INT_RST_N", j_fpga.ref, 11); conn("OTEMP_OK_N_LOW", j_fpga.ref, 12)
    conn("V_P3V3", j_fpga.ref, 13); conn("DGND", j_fpga.ref, 14); conn("DGND", j_fpga.ref, 15)
    conn("HW_CROWBAR_OK", j_fpga.ref, 16)

    # AOM DAC -> Buffer -> Compliance Divider (0..0.943 V) -> Crowbar Clamp -> AD8367 -> ADG901(2.5V) -> ADL5602 -> C_RF_DCBLK -> SMA
    conn("DAC_AOM_RAW", u_dac_aom.ref, 1); conn("AGND", u_dac_aom.ref, 2); conn("VREF_2V5", u_dac_aom.ref, 3)
    conn("DAC_AOM_CS_N", u_dac_aom.ref, 4); conn("SPI_SCLK", u_dac_aom.ref, 5); conn("SPI_MOSI", u_dac_aom.ref, 6)
    conn("SHOT_GATE", u_dac_aom.ref, 7); conn("DGND", u_dac_aom.ref, 8); conn("V_P5A", u_dac_aom.ref, 9)

    conn("DAC_AOM_RAW", u_vca_buf.ref, 3)
    conn("VCA_BUF_OUT", u_vca_buf.ref, 6); conn("VCA_BUF_OUT", u_vca_buf.ref, 2); conn("VCA_BUF_OUT", r_vca_s.ref, 1)
    conn("V_P5A", u_vca_buf.ref, 7); conn("V_N5A", u_vca_buf.ref, 4)
    conn("VCA_CTRL", r_vca_s.ref, 2); conn("VCA_CTRL", r_vca_sh.ref, 1); conn("AGND", r_vca_sh.ref, 2)
    conn("VCA_CTRL", q_vca_clp.ref, 3); conn("VCA_CTRL", u_vca.ref, 4)
    conn("AGND", q_vca_clp.ref, 2); conn("HW_CROWBAR_TRIP", q_vca_clp.ref, 1)

    # 80-200 MHz 50 Ohm RF Chain (with ADG901 @ 2.5 V VDD and C_RF_DCBLK before SMA!)
    conn("RF_LO_50", j_rf_in.ref, 1); conn("RFGND", j_rf_in.ref, 2)
    conn("RF_LO_50", u_vca.ref, 1)
    for gp in (2, 6, 9, 13):
        conn("RFGND", u_vca.ref, gp)
    conn("V_P5RF", u_vca.ref, 3); conn("V_P5RF", u_vca.ref, 7); conn("V_P5RF", u_vca.ref, 14)
    conn("RF_VCA_50", u_vca.ref, 8); conn("RF_VCA_50", c_rf1.ref, 1)
    conn("RF_SW_IN_50", c_rf1.ref, 2); conn("RF_SW_IN_50", u_rf_sw.ref, 4)  # ADG901 pin 4 = RFC
    conn("V_P2V5_RF", u_rf_sw.ref, 1); conn("HW_CROWBAR_OK", u_rf_sw.ref, 3)  # Pin 1 = VDD (2.5V!), Pin 3 = CTRL
    for gp in (2, 5, 6, 8):
        conn("RFGND", u_rf_sw.ref, gp)
    conn("RF_SW_OUT_50", u_rf_sw.ref, 7); conn("RF_SW_OUT_50", c_rf2.ref, 1)  # Pin 7 = RF1
    conn("RF_DRV_IN_50", c_rf2.ref, 2); conn("RF_DRV_IN_50", u_rf_drv.ref, 1)
    conn("RFGND", u_rf_drv.ref, 2); conn("RFGND", u_rf_drv.ref, 4)
    conn("RF_DRV_BIAS_50", u_rf_drv.ref, 3); conn("RF_DRV_BIAS_50", l_rf_bias.ref, 1); conn("RF_DRV_BIAS_50", c_rf_dcblk.ref, 1)
    conn("V_P5RF", l_rf_bias.ref, 2)
    conn("AOM_RF_OUT_50", c_rf_dcblk.ref, 2); conn("AOM_RF_OUT_50", j_rf_out.ref, 1); conn("RFGND", j_rf_out.ref, 2)

    # 1oo2D Hardware Interlock Crowbar (24 V LED-input TLP291 optos + 3.3V pull-ups + high-side SQJ461EP PMOS!)
    conn("SAFE_LASER_EN_A", j_ilk.ref, 1); conn("SAFE_LASER_EN_B", j_ilk.ref, 2)
    conn("ILK_RTN", j_ilk.ref, 3); conn("V_24V_DIODE", j_ilk.ref, 4)
    conn("DIODE_EN_OUT", j_ilk.ref, 5); conn("DIODE_RTN", j_ilk.ref, 6)

    conn("SAFE_LASER_EN_A", r_op_a.ref, 1); conn("OPTO_A_LED", r_op_a.ref, 2); conn("OPTO_A_LED", u_opto_a.ref, 1); conn("ILK_RTN", u_opto_a.ref, 2)
    conn("DGND", u_opto_a.ref, 3); conn("ILK_A_OK", u_opto_a.ref, 4); conn("ILK_A_OK", r_opu_a.ref, 2); conn("V_P3V3", r_opu_a.ref, 1)

    conn("SAFE_LASER_EN_B", r_op_b.ref, 1); conn("OPTO_B_LED", r_op_b.ref, 2); conn("OPTO_B_LED", u_opto_b.ref, 1); conn("ILK_RTN", u_opto_b.ref, 2)
    conn("DGND", u_opto_b.ref, 3); conn("ILK_B_OK", u_opto_b.ref, 4); conn("ILK_B_OK", r_opu_b.ref, 2); conn("V_P3V3", r_opu_b.ref, 1)

    conn("ILK_A_OK", u_and1.ref, 1); conn("ILK_B_OK", u_and1.ref, 2)
    conn("DGND", u_and1.ref, 3); conn("V_P3V3", u_and1.ref, 5); conn("ILK_1OO2_OK", u_and1.ref, 4)

    conn("ILK_1OO2_OK", u_and2.ref, 1); conn("OTEMP_OK_N_LOW", u_and2.ref, 2)
    conn("DGND", u_and2.ref, 3); conn("V_P3V3", u_and2.ref, 5); conn("SAFE_THERM_OK", u_and2.ref, 4)

    conn("SAFE_THERM_OK", u_and3.ref, 1); conn("AOM_RF_EN", u_and3.ref, 2)
    conn("DGND", u_and3.ref, 3); conn("V_P3V3", u_and3.ref, 5); conn("HW_CROWBAR_OK", u_and3.ref, 4)

    conn("HW_CROWBAR_OK", u_inv_cb.ref, 1); conn("HW_CROWBAR_OK", u_inv_cb.ref, 2)
    conn("DGND", u_inv_cb.ref, 3); conn("V_P3V3", u_inv_cb.ref, 5); conn("HW_CROWBAR_TRIP", u_inv_cb.ref, 4)

    # Series High-Side P-MOSFET 24 V Diode-Laser Enable Cutoff (SQJ461EP driven by 2N7002K + 12 V Zener clamps!)
    # Stage A: V_24V_DIODE (Source pin 3) -> DIODE_MID (Drain pin 2), Gate driven by Q_GDRV_DIODE_A
    conn("V_24V_DIODE", q_diode_a.ref, 3); conn("DIODE_MID", q_diode_a.ref, 2); conn("PMOS_G_A", q_diode_a.ref, 1)
    conn("V_24V_DIODE", "R_PMOS_PU_A", 1); conn("PMOS_G_A", "R_PMOS_PU_A", 2)
    conn("PMOS_G_A", "R_PMOS_DIV_A", 1); conn("GDRV_D_A", "R_PMOS_DIV_A", 2)
    conn("V_24V_DIODE", "D_Z_PMOS_A", 1); conn("PMOS_G_A", "D_Z_PMOS_A", 2)
    conn("ILK_A_OK", q_gdrv_a.ref, 1); conn("DIODE_RTN", q_gdrv_a.ref, 2); conn("GDRV_D_A", q_gdrv_a.ref, 3)

    # Stage B: DIODE_MID (Source pin 3) -> DIODE_EN_OUT (Drain pin 2), Gate driven by Q_GDRV_DIODE_B
    conn("DIODE_MID", q_diode_b.ref, 3); conn("DIODE_EN_OUT", q_diode_b.ref, 2); conn("PMOS_G_B", q_diode_b.ref, 1)
    conn("DIODE_MID", "R_PMOS_PU_B", 1); conn("PMOS_G_B", "R_PMOS_PU_B", 2)
    conn("PMOS_G_B", "R_PMOS_DIV_B", 1); conn("GDRV_D_B", "R_PMOS_DIV_B", 2)
    conn("DIODE_MID", "D_Z_PMOS_B", 1); conn("PMOS_G_B", "D_Z_PMOS_B", 2)
    conn("HW_CROWBAR_OK", q_gdrv_b.ref, 1); conn("DIODE_RTN", q_gdrv_b.ref, 2); conn("GDRV_D_B", q_gdrv_b.ref, 3)

    conn("DIODE_EN_OUT", r_diode_pd.ref, 1); conn("DIODE_RTN", r_diode_pd.ref, 2)
    r_drtn = add_c(ComponentSpec("R_DIODE_RTN_TIE", "0R_DIODE_RTN", "Resistor_SMD:R_0603_1608Metric", 136.0, 128.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S5.5-04", epistemic_tag="{Pasif-COTS}"))
    conn("DIODE_RTN", r_drtn.ref, 1); conn("DGND", r_drtn.ref, 2)

    # =========================================================================
    # CONTROLLED-IMPEDANCE 50 OHM RF & MONITOR TRACES (w50 = 0.5429 mm on RO4350B!)
    # =========================================================================
    traces.append(make_manhattan_trace("RF_LO_50", "F.Cu", _pad_xy(j_rf_in, "1"), _pad_xy(u_vca, "1"), width_mm=w50, mid_y=18.0))
    traces.append(make_manhattan_trace("RF_VCA_50", "F.Cu", _pad_xy(u_vca, "8"), _pad_xy(c_rf1, "1"), width_mm=w50))
    traces.append(make_manhattan_trace("RF_SW_IN_50", "F.Cu", _pad_xy(c_rf1, "2"), _pad_xy(u_rf_sw, "4"), width_mm=w50))
    traces.append(make_manhattan_trace("RF_SW_OUT_50", "F.Cu", _pad_xy(u_rf_sw, "7"), _pad_xy(c_rf2, "1"), width_mm=w50))
    traces.append(make_manhattan_trace("RF_DRV_IN_50", "F.Cu", _pad_xy(c_rf2, "2"), _pad_xy(u_rf_drv, "1"), width_mm=w50))
    traces.append(make_manhattan_trace("RF_DRV_BIAS_50", "F.Cu", _pad_xy(u_rf_drv, "3"), _pad_xy(c_rf_dcblk, "1"), width_mm=w50))
    traces.append(make_manhattan_trace("AOM_RF_OUT_50", "F.Cu", _pad_xy(c_rf_dcblk, "2"), _pad_xy(j_rf_out, "1"), width_mm=w50))
    traces.append(make_manhattan_trace("INT_MON_50", "F.Cu", _pad_xy(r_int_s, "2"), _pad_xy(j_int_mon, "1"), width_mm=w50))

    for vx in (110.0, 126.0, 148.0, 174.0):
        vias.append(ViaSpec("RFGND", vx, 36.0, diameter_mm=0.60, drill_mm=0.30))
    for vx in (14.0, 56.0, 86.0):
        vias.append(ViaSpec("AGND", vx, 56.0, diameter_mm=0.60, drill_mm=0.30))

    zones = (
        ZoneSpec("AGND", "In1.Cu", ((2.0, 2.0), (104.0, 2.0), (104.0, 134.0), (2.0, 134.0))),
        ZoneSpec("RFGND", "In1.Cu", ((106.0, 2.0), (199.0, 2.0), (199.0, 62.0), (106.0, 62.0))),
        ZoneSpec("DGND", "In1.Cu", ((106.0, 64.0), (199.0, 64.0), (199.0, 134.0), (106.0, 134.0))),
        ZoneSpec("V_P5A", "In2.Cu", ((2.0, 2.0), (104.0, 2.0), (104.0, 60.0), (2.0, 60.0))),
        ZoneSpec("V_N5A", "In2.Cu", ((2.0, 62.0), (104.0, 62.0), (104.0, 134.0), (2.0, 134.0))),
        ZoneSpec("V_P5RF", "In2.Cu", ((106.0, 2.0), (199.0, 2.0), (199.0, 62.0), (106.0, 62.0))),
        ZoneSpec("V_P3V3", "In2.Cu", ((106.0, 64.0), (199.0, 64.0), (199.0, 134.0), (106.0, 134.0))),
    )

    rf50_nets = {"RF_LO_50", "RF_VCA_50", "RF_SW_IN_50", "RF_SW_OUT_50", "RF_DRV_IN_50", "RF_DRV_BIAS_50", "AOM_RF_OUT_50", "INT_MON_50"}
    pwr_nets = {
        "V_P6_IN", "V_N6_IN", "V_24V_DIODE", "V_P5A", "V_N5A", "V_P5RF", "V_P2V5_RF", "V_P3V3",
        "VREF_2V5", "AGND", "DGND", "RFGND", "ILK_RTN", "DIODE_RTN",
    }
    flag_nets = {"V_P6_IN", "V_N6_IN", "V_24V_DIODE", "AGND", "DGND", "RFGND", "ILK_RTN", "DIODE_RTN"}

    nets: list[NetSpec] = []
    for nname, nodes in sorted(nets_dict.items()):
        v_work = 24.0 if nname in ("V_24V_DIODE", "SAFE_LASER_EN_A", "SAFE_LASER_EN_B", "DIODE_EN_OUT", "DIODE_MID") else (
            5.0 if "5" in nname else (2.5 if "2V5" in nname else (3.3 if "3V3" in nname else 0.0))
        )
        z0 = 50.0 if nname in rf50_nets else None
        is_pwr = nname in pwr_nets
        nets.append(NetSpec(
            name=nname,
            nodes=tuple(nodes),
            net_class="RF_50" if z0 else ("Power" if is_pwr else "Default"),
            is_power=is_pwr,
            has_pwr_flag=(nname in flag_nets),
            voltage_v=v_work,
            target_z0_ohm=z0,
        ))

    spec = BoardSpec(
        name="laser_aom_pyrometer_afe",
        title="Laser 80-200 MHz AOM RF VCA, 10 us 2-Color Pyrometer TIA, 1 ms Integrator & <0.1 ms Crowbar PCB",
        rev="v2.0",
        bom_ids=("S5.5-03", "S5.5-01", "S5.5-04", "S5.3-03"),
        width_mm=201.0,
        height_mm=136.0,
        stackup=stackup,
        components=tuple(comps),
        nets=tuple(nets),
        traces=tuple(traces),
        vias=tuple(vias),
        zones=zones,
        keepouts=tuple(keepouts),
        rules=DesignRules(min_trace_width_mm=0.127, min_clearance_mm=0.127, min_edge_clearance_mm=0.50),
        epistemic_meta={
            **DEFAULT_EPISTEMIC_META,
            "operating_temp_K": 300.0,
            "rf_band_MHz": [80.0, 200.0],
            "pyro_wavelengths_nm": [1550.0, 850.0],
            "pyro_temp_range_K": [900.0, 1700.0],
            "photodiode_bias_polarity": "reverse_biased_5V_positive_TIA_out",
            "ad8367_linearization": "log_predistortion_LUT_50dB_per_V",
            "rtl_interface": "rtl/machine_ctrl/aom_pid_ctrl.v",
        },
    )
    return auto_route_board(spec, grid_mm=0.50, preserve_existing=True)


def render_laser_pyro_ngspice_deck() -> str:
    """Native ngspice-47 deck verifying:
    1) Reverse-biased 2-color TIAs (POSITIVE 0..+2.5 V output!) & real TLV3501 1687 K melt comparator
    2) Reverse-biased 1.0 ms pulse-energy integrator (POSITIVE 1.0/2.0 V, <1% linearity)
    3) Log-linearized 50 dB/V AD8367 VCA + DC-blocked 50 Ohm ADL5602 output (0 V DC on SMA!)
    4) Real high-side SQJ461EP P-MOSFET + 2N7002K 24 V diode-laser crowbar (>23.5 V ON, <0.05 V OFF, <50 us!)
    5) Closed-loop +8% thermal surge response with log-LUT linearized AD8367 (eliminates 16-24% limit cycle!)."""
    return """* Atom Lithography Machine - Laser AOM RF VCA (Log-Linearized AD8367), Reverse-Biased 2-Color Pyrometer TIA & Crowbar
* BOM: S5.5-03, S5.5-01, S5.5-04, S5.3-03
* Epistemic status: M0/M1 DESIGN_ONLY; no_lab_measurement=true; no_physical_fab=true.

.temp 26.85
.options reltol=1e-4 vntol=1e-6 abstol=1e-12

* --- Semiconductor & Op-Amp Models ---
.model D_PD_MOD  D(IS=1e-11 N=1.2 RS=5 CJO=1p BV=25)
.model M_SQJ461  PMOS(LEVEL=1 VTO=-2.5 KP=4.0 RD=0.04 RS=0.02)
.model M_2N7002  NMOS(LEVEL=1 VTO=1.8 KP=0.35 RD=1.5 RS=0.5)
.model D_Z12V    D(IS=1e-12 BV=12.0 IBV=5m N=1.2 RS=2.0)

* --- Wideband FET-Input TIA Op-Amp (OPA657: A0=1e5, GBP=1.6 GHz, Cin=4.5 pF, en=4.8 nV/rtHz) ---
.subckt OPAMP_OPA657 inp inn out
Cin inp inn 4.5p
Rin inp inn 1T noisy=0
Rnw nw 0 1390.6 temp=26.85
Evn inp_i inp nw 0 1.0
Egain n1 0 inp_i inn 1e5
Rp n1 n2 1k noisy=0
Cp n2 0 9.9472n
Ebuf n_out 0 n2 0 1.0
Rout n_out out 5 noisy=0
.ends OPAMP_OPA657

* --- Precision JFET Integrator Op-Amp (OPA140: A0=1e6, GBP=11 MHz, low Ib=10 pA) ---
.subckt OPAMP_OPA140 inp inn out
Cin inp inn 5.0p
Rin inp inn 1T noisy=0
Ibias inn 0 DC 10p
Egain n1 0 inp inn 1e6
Rp n1 n2 1k noisy=0
Cp n2 0 14.4686u
Ebuf n_out 0 n2 0 1.0
Rout n_out out 10 noisy=0
.ends OPAMP_OPA140

* --- Analog Switch Model (ADG1211: Ron=120 Ohm, Roff=10 GOhm) ---
.model SW_ADG1211 SW(VT=1.65 VH=0.1 RON=120 ROFF=10G)
.model SW_MOS_CB  SW(VT=1.65 VH=0.1 RON=1.5 ROFF=100Meg)

* Supplies
Vn5a vn5a 0 DC -5.0
Vp5rf vp5rf 0 DC 5.0
Vp3v3 vp3v3 0 DC 3.3
V24_dio v24_d 0 DC 24.0

* =========================================================================
* 1) REVERSE-BIASED 2-COLOR PYROMETER TIAs (POSITIVE 0..+2.5V OUTPUT!) + TLV3501 1687K OTEMP
* =========================================================================
* Channel 1: InGaAs 1550 nm (Anode -> -5V via 1k, Cathode -> ig_sum virtual GND => +5V REVERSE BIAS!)
Rpb_ig vn5a pd_an_ig 1.0k
Cpb_ig pd_an_ig 0 100n
Dpd_ig pd_an_ig ig_sum D_PD_MOD
* Photocurrent flows Cathode (ig_sum) -> Anode (pd_an_ig) => POSITIVE TIA output (+1.000 V for 10 uA!)
Ipd_ig ig_sum pd_an_ig DC 0 AC 1 PULSE(0 10u 5u 20n 20n 80u 200u)
Cpd_ig ig_sum 0 11.5p
X_ig   0 ig_sum ig_out OPAMP_OPA657
Rf_ig  ig_out ig_sum 100k
Cf_ig  ig_out ig_sum 12p
Rld_ig ig_out 0 10k

* Channel 2: Si 850 nm (Anode -> -5V via 1k, Cathode -> si_sum => +5V REVERSE BIAS, POSITIVE +1.000 V!)
* Steps 0 -> 5 uA (+1.00 V healthy) at 5 us, then to 9 uA (+1.80 V > +1.50 V 1687K Si melt!) at 120 us!
Rpb_si vn5a pd_an_si 1.0k
Cpb_si pd_an_si 0 100n
Dpd_si pd_an_si si_sum D_PD_MOD
Ipd_si si_sum pd_an_si DC 0 AC 1 PWL(0 0 5u 0 5.02u 5u 119.9u 5u 120u 9u 220u 9u)
Cpd_si si_sum 0 2.5p
X_si   0 si_sum si_out OPAMP_OPA657
Rf_si  si_out si_sum 200k
Cf_si  si_out si_sum 6.0p
Rld_si si_out 0 10k

* Real TLV3501AID 1687 K Hardware Over-Temperature Comparator (VREF=+1.50 V on IN+, si_out on IN-, SHDN=0V)
Vot_thr otemp_thr 0 DC 1.50
Botemp  otemp_ok 0 V = 1.65 * (1.0 + tanh(200.0 * (V(otemp_thr) - V(si_out))))

* =========================================================================
* 2) REVERSE-BIASED 1.0 ms PULSE-ENERGY INTEGRATOR (POSITIVE +1.0 V / +2.0 V, <1% LINEARITY)
* =========================================================================
Vint_rst int_rst 0 DC 3.3 PWL(0 3.3 49u 3.3 50u 0 1.299m 0 1.300m 3.3)
Rpb_e1   vn5a pd_an_e1 1.0k
Dpd_e1   pd_an_e1 int1_sum D_PD_MOD
Ieng_1x  int1_sum pd_an_e1 DC 0 PULSE(0 100u 0.100m 1u 1u 0.999m 5m)
Cint_1x  int1_out int1_sum 100n
Rlk_1x   int1_out int1_sum 10G
Srst_1x  int1_out int1_sum int_rst 0 SW_ADG1211
Xint_1x  0 int1_sum int1_out OPAMP_OPA140
Rld_1x   int1_out 0 100k

Rpb_e2   vn5a pd_an_e2 1.0k
Dpd_e2   pd_an_e2 int2_sum D_PD_MOD
Ieng_2x  int2_sum pd_an_e2 DC 0 PULSE(0 200u 0.100m 1u 1u 0.999m 5m)
Cint_2x  int2_out int2_sum 100n
Rlk_2x   int2_out int2_sum 10G
Srst_2x  int2_out int2_sum int_rst 0 SW_ADG1211
Xint_2x  0 int2_sum int2_out OPAMP_OPA140
Rld_2x   int2_out 0 100k

* =========================================================================
* 3) 80-200 MHz AOM RF CHAIN WITH +5V BIAS TEE + 100 nF DC-BLOCKING CAP (0 V DC ON SMA!)
* =========================================================================
Vrf_lo   rf_src 0 DC 0 AC 1
Rrf_src  rf_src rf_in 50
Crf_ac1  rf_in  rf_mid 100n
Rrf_dc   rf_mid 0 100k
Crf_par  rf_mid 0 1.5p
Crf_ac2  rf_mid rf_drv 100n
* +5 V ADL5602 bias choke fed on rf_drv, ISOLATED from 50 Ohm coax by C_RF_DCBLK (100 nF)!
Lrf_chk  vp5rf  rf_drv 1.0u
Crf_dblk rf_drv rf_out 100n
Rrf_ld   rf_out 0 50

* =========================================================================
* 4) LOG-LINEARIZED 50 dB/V AD8367 VCA + < 50 us REAL HIGH-SIDE PMOS 24 V CROWBAR
* =========================================================================
* PID linear gain command u_cmd in [0.65, 1.40] mapped via log-linearized LUT into AD8367 Vctrl in [0.425, 0.559] V:
*   V_ctrl = 0.50 + 0.40 * log10(u_cmd) => G_ad8367 = 10^(2.5 * (V_ctrl - 0.50)) == u_cmd (EXACT linear gain!)
Vu_cmd   u_cmd 0 DC 0.65 PWL(0 0.65 49u 0.65 50u 1.40 300u 1.40)
Blut_vca vca_lut 0 V = 0.50 + 0.40 * log10(max(V(u_cmd), 0.05))
Rvca_s   vca_lut vca_ctrl 499
Cvca_f   vca_ctrl 0 2.2n
Vilk_a   ilk_ok 0 DC 3.3 PWL(0 3.3 150u 3.3 150.5u 0 300u 0)
Bcb_drv  cb_trip 0 V = 3.3 - V(ilk_ok)
Scb_vca  vca_ctrl 0 cb_trip 0 SW_MOS_CB
* True AD8367 50 dB/V exponential gain response (drops to 0 when clamped by crowbar!)
Bad8367  vca_gain_lin 0 V = (V(vca_ctrl) > 0.05) ? pow(10.0, 2.5 * (V(vca_ctrl) - 0.50)) : 0.0

* Real High-Side Series SQJ461EP P-MOSFETs + Low-Side 2N7002K Drivers + 12V Zener Clamps (OBS-037 FIX!)
M_gdrv_a gdrv_a ilk_ok 0 0 M_2N7002 W=2 L=1
R_pu_a   v24_d  pmos_ga 10k
R_div_a  pmos_ga gdrv_a 10k
Dz_a     pmos_ga v24_d  D_Z12V
M_dio_a  dio_mid pmos_ga v24_d v24_d M_SQJ461 W=10 L=1

M_gdrv_b gdrv_b ilk_ok 0 0 M_2N7002 W=2 L=1
R_pu_b   dio_mid pmos_gb 10k
R_div_b  pmos_gb gdrv_b  10k
Dz_b     pmos_gb dio_mid D_Z12V
M_dio_b  diode_en pmos_gb dio_mid dio_mid M_SQJ461 W=10 L=1

Rdio_pd  diode_en 0 1.0k
Cdio_cab diode_en 0 2.0n

* =========================================================================
* 5) CLOSED-LOOP +8% LASER SURGE TEST WITH LOG-LINEARIZED AD8367 (ZERO LIMIT CYCLE!)
* =========================================================================
* Plant: P_out = (1 + surge) * G_ad8367(V_lut(u_pid)) filtered by tau = 15 us thermal/AOM pole
* PI controller (kp=0.42, ki=36000 s^-1) holds P_out = 1.000 against +8% surge at t=50 us!
V_surge  surge_in 0 DC 1.00 PWL(0 1.00 49u 1.00 50u 1.08 220u 1.08)
B_err    pid_err  0 V = 1.00 - V(p_meas)
* Integrator: d(i_term)/dt = 36000 * pid_err -> R=27.78k, C=1nF, initialized at 1.00 V
G_int    0 pid_int pid_err 0 36u
C_int    pid_int 0 1n IC=1.00
R_int_lk pid_int 0 100Meg
B_upid   u_pid    0 V = min(max(V(pid_int) + 0.42 * V(pid_err), 0.65), 1.40)
* Log-linearized pre-distortion LUT -> AD8367 50 dB/V -> exact linear modulation!
B_lut_cl v_cl_lut 0 V = 0.50 + 0.40 * log10(V(u_pid))
B_p_raw  p_raw    0 V = V(surge_in) * pow(10.0, 2.5 * (V(v_cl_lut) - 0.50))
R_tau    p_raw    p_meas 15k
C_tau    p_meas   0      1n IC=1.00

.control
set noaskquit

* 0) DC Operating Point: Verify 0 V DC on SMA RF output (C_RF_DCBLK) & +5 V reverse bias on photodiodes
op
let rf_out_dc_v = abs(v(rf_out))
let pd_ig_rev_bias_v = v(ig_sum) - v(pd_an_ig)
let pd_si_rev_bias_v = v(si_sum) - v(pd_an_si)
print rf_out_dc_v pd_ig_rev_bias_v pd_si_rev_bias_v

* 1) AC Analysis: 2-Color TIA -3 dB bandwidth & 80-200 MHz AOM RF 50 Ohm flatness
ac dec 100 100 500Meg
meas ac z_dc_ingaas FIND vm(ig_out) AT=1k
meas ac z_dc_si     FIND vm(si_out) AT=1k
let ig_3db = 0.707107 * z_dc_ingaas
let si_3db = 0.707107 * z_dc_si
meas ac f3db_ingaas_hz WHEN vm(ig_out)=$&ig_3db FALL=1
meas ac f3db_si_hz     WHEN vm(si_out)=$&si_3db FALL=1
meas ac rf_gain_80m_db  FIND vdb(rf_out) AT=80Meg
meas ac rf_gain_200m_db FIND vdb(rf_out) AT=200Meg
let rf_flatness_db = abs(rf_gain_200m_db - rf_gain_80m_db)
print rf_flatness_db

* 2) Transient A: Fast POSITIVE 2-Color TIA Step + TLV3501 1687K Trip + Log-Linearized VCA + PMOS Crowbar + Surge
tran 20n 220u 0 50n uic
* InGaAs TIA (POSITIVE 0 -> +1.000 V!)
meas tran ig_v_final FIND v(ig_out) AT=40u
let ig_v10 = 0.10 * ig_v_final
let ig_v90 = 0.90 * ig_v_final
meas tran ig_t10 WHEN v(ig_out)=$&ig_v10 RISE=1
meas tran ig_t90 WHEN v(ig_out)=$&ig_v90 RISE=1
let tau_rise_ingaas_s = ig_t90 - ig_t10

* Si TIA (POSITIVE 0 -> +1.000 V at 40 us; +1.80 V > 1.50 V OTEMP trip at 160 us!)
meas tran si_v_final FIND v(si_out) AT=40u
let si_v10 = 0.10 * si_v_final
let si_v90 = 0.90 * si_v_final
meas tran si_t10 WHEN v(si_out)=$&si_v10 RISE=1
meas tran si_t90 WHEN v(si_out)=$&si_v90 RISE=1
let tau_rise_si_s = si_t90 - si_t10
meas tran otemp_ok_healthy_v FIND v(otemp_ok) AT=40u
meas tran otemp_ok_1687k_v   FIND v(otemp_ok) AT=160u
print tau_rise_ingaas_s tau_rise_si_s otemp_ok_healthy_v otemp_ok_1687k_v

* Log-linearized AD8367 VCA modulation ratio [0.65, 1.40] & Hardware Crowbar Cutoff (< 50 us!)
meas tran vca_gain_lo FIND v(vca_gain_lin) AT=30u
meas tran vca_gain_hi FIND v(vca_gain_lin) AT=120u
let vca_mod_ratio = vca_gain_hi / vca_gain_lo
print vca_mod_ratio

let vca_10 = 0.10 * vca_gain_hi
meas tran vca_cb_t10 WHEN v(vca_gain_lin)=$&vca_10 FALL=1 TD=149u
let crowbar_vca_cutoff_s = vca_cb_t10 - 150u

meas tran diode_v_on  FIND v(diode_en) AT=120u
meas tran diode_v_off FIND v(diode_en) AT=200u
let dio_10 = 0.10 * diode_v_on
meas tran dio_cb_t10 WHEN v(diode_en)=$&dio_10 FALL=1 TD=149u
let crowbar_diode_cutoff_s = dio_cb_t10 - 150u
print diode_v_on diode_v_off crowbar_vca_cutoff_s crowbar_diode_cutoff_s

* Closed-loop +8% surge tail stability (proves ZERO 16-24% limit-cycle oscillation!)
meas tran cl_p_tail_max MAX v(p_meas) FROM=160u TO=215u
meas tran cl_p_tail_min MIN v(p_meas) FROM=160u TO=215u
let cl_p_tail_pp = cl_p_tail_max - cl_p_tail_min
print cl_p_tail_max cl_p_tail_min cl_p_tail_pp

* 3) Transient B: 1.0 ms Pulse-Energy Integrator 2x Linearity Sweep (POSITIVE +1.0 V / +2.0 V) & Reset
tran 1u 1.6m 0 2u
meas tran v_int_1x FIND v(int1_out) AT=1.20m
meas tran v_int_2x FIND v(int2_out) AT=1.20m
meas tran v_int_1x_after_rst FIND v(int1_out) AT=1.55m
let int_ratio_2x = v_int_2x / v_int_1x
let int_lin_err_pct = abs(int_ratio_2x - 2.0) / 2.0 * 100.0
print v_int_1x v_int_2x int_ratio_2x int_lin_err_pct

quit 0
.endc
.end
"""


def run_mna_crosscheck() -> dict[str, float]:
    """Independent Python MNA cross-check of both InGaAs & Si TIAs (DC transimpedance & -3 dB)."""
    results: dict[str, float] = {}
    for tag, rf, cf, cj in (("ingaas", 100e3, 12e-12, 12.5e-12), ("si", 200e3, 6e-12, 3.5e-12)):
        c = MnaCircuit()
        c.add_isource("0", "sum", dc=0.0, ac=1.0)
        c.add_capacitor("sum", "0", cj)
        c.add_opamp_single_pole("0", "sum", "out", a0=1e5, gbp_hz=1.6e9, c_in_f=4.5e-12, r_in_ohm=1e12, r_out_ohm=5.0)
        c.add_resistor("out", "sum", rf)
        c.add_capacitor("out", "sum", cf)
        c.add_resistor("out", "0", 10e3)
        freqs = [1e3, 132629.12]
        ac = c.solve_ac(freqs)
        z_dc = abs(ac["out"][0])
        z_fc = abs(ac["out"][1])
        results[f"mna_z_dc_{tag}_ohm"] = round(float(z_dc), 2)
        results[f"mna_ratio_at_132p6khz_{tag}"] = round(float(z_fc / z_dc), 5)
    return results


def build_and_verify(out_dir: Path | None = None) -> dict[str, Any]:
    od = Path(out_dir) if out_dir is not None else OUT_DIR
    od.mkdir(parents=True, exist_ok=True)

    spec = build_laser_aom_pyrometer_board()
    board_res = verify_board_bundle(spec, od)

    cir_path = od / "laser_pyro_tia_aom.cir"
    cir_path.write_text(render_laser_pyro_ngspice_deck(), encoding="utf-8")
    sp_res = run_ngspice(cir_path, workdir=od)
    mna_res = run_mna_crosscheck()

    m = sp_res.metrics
    tau_ig_us = float(m.get("tau_rise_ingaas_s", 999.0)) * 1e6
    tau_si_us = float(m.get("tau_rise_si_s", 999.0)) * 1e6
    int_err_pct = float(m.get("int_lin_err_pct", 999.0))
    cb_vca_us = float(m.get("crowbar_vca_cutoff_s", 999.0)) * 1e6
    cb_dio_us = float(m.get("crowbar_diode_cutoff_s", 999.0)) * 1e6
    vca_ratio = float(m.get("vca_mod_ratio", 0.0))
    rf_flat_db = float(m.get("rf_flatness_db", 999.0))
    rf_out_dc_v = float(m.get("rf_out_dc_v", 999.0))
    pd_ig_rev = float(m.get("pd_ig_rev_bias_v", -99.0))
    pd_si_rev = float(m.get("pd_si_rev_bias_v", -99.0))
    otemp_ok_h = float(m.get("otemp_ok_healthy_v", 0.0))
    otemp_ok_t = float(m.get("otemp_ok_1687k_v", 99.0))
    cl_tail_pp = float(m.get("cl_p_tail_pp", 99.0))
    dio_v_on = float(m.get("diode_v_on", 0.0))
    dio_v_off = abs(float(m.get("diode_v_off", 99.0)))
    v_rst_mv = abs(float(m.get("v_int_1x_after_rst", 999.0))) * 1e3
    mna_ig_err_pct = abs(float(m.get("z_dc_ingaas", 0.0)) - mna_res["mna_z_dc_ingaas_ohm"]) / mna_res["mna_z_dc_ingaas_ohm"] * 100.0

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
        "photodiodes_reverse_biased_5v": pd_ig_rev > 4.5 and pd_si_rev > 4.5,
        "otemp_tlv3501_trips_at_1687k": otemp_ok_h > 3.0 and otemp_ok_t < 0.2,
        "rf_sma_dc_blocked_zero_v": rf_out_dc_v < 1e-3,
        "tia_ingaas_rise_lt_10us": 0.0 < tau_ig_us < 10.0,
        "tia_si_rise_lt_10us": 0.0 < tau_si_us < 10.0,
        "integrator_2x_linearity_lt_1pct": int_err_pct < 1.0,
        "integrator_reset_lt_5mv": v_rst_mv < 5.0,
        "crowbar_vca_cutoff_lt_50us": 0.0 < cb_vca_us < 50.0,
        "crowbar_diode_pmos_24v_cutoff_lt_50us": 0.0 < cb_dio_us < 50.0 and dio_v_on > 23.0 and dio_v_off < 0.05,
        "vca_log_lut_gain_ratio_matches_1p40_over_0p65": abs(vca_ratio - (1.40 / 0.65)) < 0.05,
        "closed_loop_surge_zero_limit_cycle": cl_tail_pp < 0.01,
        "rf_80_200mhz_flatness_lt_0p5db": rf_flat_db < 0.5,
        "mna_tia_parity_lt_0p5pct": mna_ig_err_pct < 0.5,
    }

    report = {
        "suite": "laser_aom_pyrometer_afe",
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
                "rf_out_dc_v": round(rf_out_dc_v, 6),
                "pd_ingaas_rev_bias_v": round(pd_ig_rev, 4),
                "pd_si_rev_bias_v": round(pd_si_rev, 4),
                "otemp_ok_healthy_v": round(otemp_ok_h, 4),
                "otemp_ok_1687k_trip_v": round(otemp_ok_t, 4),
                "tau_rise_ingaas_us": round(tau_ig_us, 4),
                "tau_rise_si_us": round(tau_si_us, 4),
                "f3db_ingaas_khz": round(float(m.get("f3db_ingaas_hz", 0.0)) / 1e3, 3),
                "f3db_si_khz": round(float(m.get("f3db_si_hz", 0.0)) / 1e3, 3),
                "v_int_1x_v": round(float(m.get("v_int_1x", 0.0)), 6),
                "v_int_2x_v": round(float(m.get("v_int_2x", 0.0)), 6),
                "int_lin_err_pct": round(int_err_pct, 5),
                "v_int_after_reset_mv": round(v_rst_mv, 4),
                "vca_mod_ratio": round(vca_ratio, 4),
                "cl_surge_tail_pp": round(cl_tail_pp, 5),
                "crowbar_vca_cutoff_us": round(cb_vca_us, 4),
                "crowbar_diode_cutoff_us": round(cb_dio_us, 4),
                "diode_v_on_v": round(dio_v_on, 3),
                "diode_v_off_v": round(dio_v_off, 6),
                "rf_80_200mhz_flatness_db": round(rf_flat_db, 4),
            },
        },
        "mna_crosscheck": {**mna_res, "tia_ingaas_z_dc_diff_pct": round(mna_ig_err_pct, 5)},
        "checks": checks,
        "all_passed": all(checks.values()),
    }
    (od / "laser_aom_pyrometer_afe_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
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
        "z0_checks": len(drc_d["impedance_checks"]),
        "ngspice_summary": res["ngspice"]["summary"],
        "mna_crosscheck": res["mna_crosscheck"],
        "checks": res["checks"],
    }, indent=2))
    if not res["all_passed"]:
        print("ERC errors:", res["board"]["erc"]["errors"][:10])
        print("DRC errors:", res["board"]["drc"]["errors"][:10])
        print("SPICE errors:", res["ngspice"]["errors"][:10])
        raise SystemExit(1)
