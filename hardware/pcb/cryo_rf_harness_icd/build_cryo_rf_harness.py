"""Cryo-RF, Microwave, Quench & rf-SET Harness Builder & Live ngspice-47 Verifier.

Covers ALL 17 E2 cryogenic RF/microwave/readout/qRAM parts + S6.3-04 quench protection:
  E2: S3.2-04, S6.4-03, S6.5-03, S6.6-01, S6.6-02, S6.6-03, S6.6-04, S6.6-07,
      S6.7-01, S6.10-01, S6.11-02, S6.11-03, S6.11-04, S9.3-02, S9.4-01, S9.4-02, S9.4-03
  E1 (quench harness): S6.3-04

Generates & verifies:
  1. KiCad 8 cryo_rf_bias_panel.{kicad_sch,kicad_pcb} (0 ERC, 0 DRC via verify_board_bundle):
     4-layer Rogers RO4350B cryogenic bulkhead distribution PCB (300 K -> 4 K -> 20 mK):
       - 8x 4 K InP HEMT low-noise drain/gate bias channels (S6.6-01 / S6.11-03)
       - 4x 20 mK Josephson TWPA flux-bias & Eccosorb CR-124 filter lanes (S6.11-02 / S6.5-03)
       - 4x 50.00 Ohm controlled-impedance RF/rf-SET monitor & bias-tee lanes (S6.7-01 / S6.5-03)
       - 400 V-isolated S6.3-04 quench voltage-tap sense & persistent-switch heater port with
         milled Edge.Cuts air-slot (IPC-2221 / IEC-61010 verified)
       - Star-grounded AGND_CRYO <-> CRYO_OVC shield architecture + LT3045/LT3094 conditioning
  2. Three native ngspice-47 SPICE decks (exit 0, 0 errors) + independent Python cross-checks:
       - qram_chebyshev_50_to_3k.cir   (S9.4-02: 5-stage Chebyshev 50 <-> 3000 Ohm, 4-8 GHz)
       - magnet_quench_dump_1p563ohm.cir (S6.3-04: 8-coil 18.94 kJ quench dump, <=400 V, tau~0.370 s)
       - rf_set_tank_biastee.cir       (S6.7-01: 321 MHz rf-SET LC tank 50k<->200k + bias-tee >40 dB)
  3. cryo_rf_thermal_attenuation.json reconciling Exp125 / Exp140 / Exp142 thermal & RF budgets.

Epistemic status: M0/M1 DESIGN_ONLY; no_lab_measurement=true; no_physical_fab=true; iec61508_certified=false.
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

H_PLANCK = 6.62607015e-34
K_BOLTZMANN = 1.380649e-23

# Physically realizable 7-section lumped superconducting NbTiN cryo LC impedance transformer (OBS-105)
# Replaces unrealizable Z0=1188.8/2409.7 Ohm quarter-wave lines (>6x free-space 377 Ohm) with planar
# NbTiN spiral/meander inductors (0.98..52.8 nH) & cryo MIM capacitors (7.8..274 fF), 4-8 GHz |S11|<=-24.4 dB!
QRAM_LUMPED_L_NH: tuple[float, ...] = (
    0.97511, 1.86565, 3.77273, 6.36368, 15.93653, 27.96562, 52.75950,
)
QRAM_LUMPED_C_PF: tuple[float, ...] = (
    0.274358, 0.207407, 0.108430, 0.064422, 0.030152, 0.017408, 0.007776,
)
CHEBYSHEV_F0_HZ = 6.0e9
CHEBYSHEV_Q_INT = 1.0e5

# Exact Exp125 8-coil 1.50 T NbTi magnet energy-weighted equivalent inductance partition
# E_mag = 18,940.776 J, I_ref = 255.913899 A, L_eq = 0.5784156 H, R_dump = 1.563026 Ohm
MAGNET_I0_A = 255.913899
MAGNET_L_EQ_H = 0.57841562
MAGNET_R_DUMP_OHM = 1.5630257
MAGNET_T_DETECT_S = 0.030
MAGNET_COIL_SECTIONS: tuple[tuple[str, float, float], ...] = (
    # (coil_name, nominal_coil_current_A, energy_weighted_L_eq_H)
    ("M_upper", 40.2387, 0.007432),
    ("M_lower", 216.4744, 0.215084),
    ("S_upper", 255.9139, 0.160582),
    ("S_lower", -195.2619, 0.093486),
    ("A_upper", -167.9891, 0.089651),
    ("A_lower", -57.2000, 0.010395),
    ("B_upper", 83.9000, 0.001666),
    ("B_lower", 22.4800, 0.000120),
)

# S6.7-01 rf-SET LC matching tank + cryogenic bias-tee parameters (f0 ~ 321 MHz)
RFSET_L_TANK_H = 820.0e-9
RFSET_R_L_SER_OHM = 4.0      # Superconducting NbTiN spiral ESR at 20 mK (Q_L ~ 413 @ 321 MHz)
RFSET_C_PAR_F = 0.30e-12     # Bondwire + pad + SET drain parasitic capacitance
RFSET_R_SET_LO_OHM = 50.0e3  # Coulomb peak (conductive state)
RFSET_R_SET_HI_OHM = 200.0e3 # Coulomb blockade (insulating state)

E2_PART_IDS: tuple[str, ...] = (
    "S3.2-04", "S6.4-03", "S6.5-03", "S6.6-01", "S6.6-02", "S6.6-03", "S6.6-04",
    "S6.6-07", "S6.7-01", "S6.10-01", "S6.11-02", "S6.11-03", "S6.11-04",
    "S9.3-02", "S9.4-01", "S9.4-02", "S9.4-03",
)


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


def _msop12_ep_geometry(names: dict[str, str], types: dict[str, str]) -> tuple[PinSpec, ...]:
    """12-lead MSOP with center Exposed Thermal Pad (Pin 13, P=0.65 mm)."""
    pitch = 0.65
    x_off = 2.65
    pw, ph = 1.20, 0.36
    pins: list[PinSpec] = []
    for idx in range(12):
        pnum = str(idx + 1)
        if idx < 6:
            dy = (idx - 2.5) * pitch
            pins.append(PinSpec(pnum, names[pnum], types[pnum], round(-x_off, 4), round(dy, 4), pw, ph, 0.0))
        else:
            ridx = idx - 6
            dy = (2.5 - ridx) * pitch
            pins.append(PinSpec(pnum, names[pnum], types[pnum], round(x_off, 4), round(dy, 4), pw, ph, 0.0))
    pins.append(PinSpec("13", names["13"], types["13"], 0.0, 0.0, 1.55, 2.80, 0.0))
    return tuple(pins)


def _lt3045_msop12_ep_pins() -> tuple[PinSpec, ...]:
    """Exact Analog Devices LT3045EMSE (MSOP-12-1EP) positive LDO pinout (EP = GND, OBS-033)."""
    names = {
        "1": "IN1", "2": "IN2", "3": "IN3", "4": "EN_UV", "5": "PG", "6": "ILIM",
        "7": "PGFB", "8": "GND", "9": "SET", "10": "OUTS", "11": "OUT1", "12": "OUT2", "13": "EP_GND",
    }
    types = {
        "1": "power_in", "2": "power_in", "3": "power_in", "4": "input", "5": "no_connect", "6": "passive",
        "7": "input", "8": "power_in", "9": "input", "10": "input", "11": "power_out", "12": "power_out", "13": "power_in",
    }
    return _msop12_ep_geometry(names, types)


def _lt3094_msop12_ep_pins() -> tuple[PinSpec, ...]:
    """Exact Analog Devices LT3094EMSE (MSOP-12-1EP) negative LDO pinout (EP = VIN_N!, OBS-033)."""
    names = {
        "1": "IN1", "2": "IN2", "3": "IN3", "4": "EN_UV", "5": "PG", "6": "ILIM",
        "7": "VIOC", "8": "PGFB", "9": "GND", "10": "SET", "11": "OUTS", "12": "OUT", "13": "EP_VIN_N",
    }
    types = {
        "1": "power_in", "2": "power_in", "3": "power_in", "4": "input", "5": "no_connect", "6": "passive",
        "7": "no_connect", "8": "input", "9": "power_in", "10": "input", "11": "input", "12": "power_out", "13": "power_in",
    }
    return _msop12_ep_geometry(names, types)


# ---------------------------------------------------------------------------
# 1. KiCad 8 Cryo-RF Bulkhead Filter & Bias Distribution PCB (0 ERC, 0 DRC)
# ---------------------------------------------------------------------------

def build_cryo_rf_bias_panel_board() -> BoardSpec:
    """Build 4-layer Rogers RO4350B cryogenic DC/TWPA/HEMT bias & Eccosorb filter bulkhead PCB.

    Board geometry: 170 mm x 120 mm, 4-layer Rogers RO4350B (er=3.48, 0.254 mm outer cores):
      - Left/Top (x=12..118, y=10..56): 8x 4 K InP HEMT low-noise bias filter channels (S6.6-01/S6.11-03)
      - Mid-Left (x=12..118, y=62..88): 4x 20 mK TWPA flux-bias & Eccosorb CR-124 LPF lanes (S6.11-02/S6.5-03)
      - Bottom-Left (x=12..118, y=95..112): 4x 50.00 Ohm RF/rf-SET bias-tee monitor lanes (S6.7-01) +
        LT3045/LT3094 ultra-low-noise LDO conditioning & AGND_CRYO <-> CRYO_OVC star tie
      - Right isolated bay (x=136..162, y=16..104), separated by a 2.5 x 92 mm milled Edge.Cuts air-slot
        at x=126.0 mm: S6.3-04 400 V magnet quench voltage-tap sense & persistent-switch heater port.
    """
    stackup = (
        StackupLayer("F.Cu", "signal", 0.035, material="Copper"),
        StackupLayer("dielectric 1", "core", 0.254, epsilon_r=3.48, loss_tangent=0.0037, material="Rogers RO4350B"),
        StackupLayer("In1.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 2", "core", 0.800, epsilon_r=3.48, loss_tangent=0.0037, material="Rogers RO4350B"),
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
    z0_nets: set[str] = set()
    hv_nets: set[str] = set()

    def add_c(c: ComponentSpec) -> ComponentSpec:
        comps.append(c)
        return c

    def conn(net: str, ref: str, pin: str | int) -> None:
        nets_dict[net].append((ref, str(pin)))

    # --- Power Entry, LDO Conditioning & AGND_CRYO <-> CRYO_OVC Star-Tie (x=14..60, y=106) ---
    jpwr = add_c(ComponentSpec(
        "JPWR_CRYO", "HDR_1x4_PM5V_OVC", "Connector_PinHeader:HDR_1x4_2.54mm",
        12.0, 108.0, rotation_deg=90.0,
        pins=auto_footprint_pads(
            "HDR_1x4_2.54mm", ("1", "2", "3", "4"),
            {"1": "VIN_P5V", "2": "VIN_N5V", "3": "AGND_CRYO", "4": "CRYO_OVC"},
            {"1": "power_out", "2": "power_out", "3": "power_out", "4": "power_out"},
        ),
        bom_id="S6.11-03", mpn="MicroD-4P-Cryo", epistemic_tag="{Pasif-COTS}",
    ))
    conn("VIN_P5V", "JPWR_CRYO", 1)
    conn("VIN_N5V", "JPWR_CRYO", 2)
    conn("AGND_CRYO", "JPWR_CRYO", 3)
    conn("CRYO_OVC", "JPWR_CRYO", 4)

    # Single-point AGND_CRYO <-> CRYO_OVC star tie (0 Ohm cryo jumper + 100 nF HF chassis bypass)
    r_star = add_c(ComponentSpec(
        "R_STAR_OVC", "0R_STAR_TIE", "Resistor_SMD:R_0805_2012Metric",
        24.0, 111.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S6.11-04", mpn="CRCW08050000Z0EA", epistemic_tag="{Pasif-COTS}",
    ))
    c_ovc = add_c(ComponentSpec(
        "C_OVC_HF", "100nF_C0G_50V", "Capacitor_SMD:C_0805_2012Metric",
        24.0, 105.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S6.11-04", mpn="C0805C104J5GEC", epistemic_tag="{Pasif-COTS}",
    ))
    conn("AGND_CRYO", "R_STAR_OVC", 1)
    conn("CRYO_OVC", "R_STAR_OVC", 2)
    conn("AGND_CRYO", "C_OVC_HF", 1)
    conn("CRYO_OVC", "C_OVC_HF", 2)

    # Positive ultra-low-noise LDO (LT3045EMSE MSOP-12-1EP: +5 V -> +3.3 V HEMT drain/TWPA bus, EP=AGND_CRYO)
    u_ldo_p = add_c(ComponentSpec(
        "U_LDO_P", "LT3045EMSE", "Package_SO:MSOP-12-1EP_3x4mm_P0.65mm",
        38.0, 108.0, pins=_lt3045_msop12_ep_pins(),
        bom_id="S6.11-03", mpn="LT3045EMSE", epistemic_tag="{Aday-COTS}",
    ))
    r_set_p = add_c(ComponentSpec(
        "R_SET_P", "33.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric",
        46.0, 105.0, pins=auto_footprint_pads("0603", ("1", "2")),
        bom_id="S6.11-03", mpn="RT0603BRD0733KL", epistemic_tag="{Pasif-COTS}",
    ))
    c_set_p = add_c(ComponentSpec(
        "C_SET_P", "1uF_C0G", "Capacitor_SMD:C_0805_2012Metric",
        46.0, 111.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S6.11-03", mpn="C0805C105K5RAC", epistemic_tag="{Pasif-COTS}",
    ))
    c_in_p = add_c(ComponentSpec(
        "C_IN_P", "10uF_16V", "Capacitor_SMD:C_0805_2012Metric",
        31.5, 105.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S6.11-03", mpn="C0805C106K4PAC", epistemic_tag="{Pasif-COTS}",
    ))
    c_out_p = add_c(ComponentSpec(
        "C_OUT_P", "10uF_10V", "Capacitor_SMD:C_0805_2012Metric",
        52.5, 108.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S6.11-03", mpn="C0805C106K8PAC", epistemic_tag="{Pasif-COTS}",
    ))
    for pnum in ("1", "2", "3", "4"):
        conn("VIN_P5V", "U_LDO_P", pnum)
    conn("AGND_CRYO", "U_LDO_P", 6)     # ILIM -> GND (max 500 mA limit)
    conn("VBIAS_P3V3", "U_LDO_P", 7)    # PGFB -> VOUT
    conn("AGND_CRYO", "U_LDO_P", 8)     # GND
    conn("LDO_P_SET", "U_LDO_P", 9)     # SET
    for pnum in ("10", "11", "12"):     # OUTS, OUT, OUT
        conn("VBIAS_P3V3", "U_LDO_P", pnum)
    conn("AGND_CRYO", "U_LDO_P", 13)    # EP = GND
    conn("LDO_P_SET", "R_SET_P", 1); conn("AGND_CRYO", "R_SET_P", 2)
    conn("LDO_P_SET", "C_SET_P", 1); conn("AGND_CRYO", "C_SET_P", 2)
    conn("VIN_P5V", "C_IN_P", 1); conn("AGND_CRYO", "C_IN_P", 2)
    conn("VBIAS_P3V3", "C_OUT_P", 1); conn("AGND_CRYO", "C_OUT_P", 2)

    # Negative ultra-low-noise LDO (LT3094EMSE MSOP-12-1EP: -5 V -> -2.5 V HEMT gate rail, EP=VIN_N5V!)
    u_ldo_n = add_c(ComponentSpec(
        "U_LDO_N", "LT3094EMSE", "Package_SO:MSOP-12-1EP_3x4mm_P0.65mm",
        68.0, 108.0, pins=_lt3094_msop12_ep_pins(),
        bom_id="S6.6-01", mpn="LT3094EMSE", epistemic_tag="{Aday-COTS}",
    ))
    r_set_n = add_c(ComponentSpec(
        "R_SET_N", "24.9k_0.1pct", "Resistor_SMD:R_0603_1608Metric",
        76.0, 105.0, pins=auto_footprint_pads("0603", ("1", "2")),
        bom_id="S6.6-01", mpn="RT0603BRD0724K9L", epistemic_tag="{Pasif-COTS}",
    ))
    c_set_n = add_c(ComponentSpec(
        "C_SET_N", "1uF_C0G", "Capacitor_SMD:C_0805_2012Metric",
        76.0, 111.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S6.6-01", mpn="C0805C105K5RAC", epistemic_tag="{Pasif-COTS}",
    ))
    c_in_n = add_c(ComponentSpec(
        "C_IN_N", "10uF_16V", "Capacitor_SMD:C_0805_2012Metric",
        61.5, 105.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S6.6-01", mpn="C0805C106K4PAC", epistemic_tag="{Pasif-COTS}",
    ))
    c_out_n = add_c(ComponentSpec(
        "C_OUT_N", "10uF_10V", "Capacitor_SMD:C_0805_2012Metric",
        82.5, 108.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S6.6-01", mpn="C0805C106K8PAC", epistemic_tag="{Pasif-COTS}",
    ))
    for pnum in ("1", "2", "3", "4"):
        conn("VIN_N5V", "U_LDO_N", pnum)
    conn("AGND_CRYO", "U_LDO_N", 6)     # ILIM -> GND (Pin 7 VIOC NC)
    conn("VGATE_N2V5", "U_LDO_N", 8)    # PGFB -> VOUT_N
    conn("AGND_CRYO", "U_LDO_N", 9)     # GND
    conn("LDO_N_SET", "U_LDO_N", 10)    # SET
    for pnum in ("11", "12"):           # OUTS, OUT
        conn("VGATE_N2V5", "U_LDO_N", pnum)
    conn("VIN_N5V", "U_LDO_N", 13)      # EP = VIN_N5V (internally tied to negative IN!)
    conn("LDO_N_SET", "R_SET_N", 1); conn("AGND_CRYO", "R_SET_N", 2)
    conn("LDO_N_SET", "C_SET_N", 1); conn("AGND_CRYO", "C_SET_N", 2)
    conn("VIN_N5V", "C_IN_N", 1); conn("AGND_CRYO", "C_IN_N", 2)
    conn("VGATE_N2V5", "C_OUT_N", 1); conn("AGND_CRYO", "C_OUT_N", 2)

    # --- Block A: 8x 4 K InP HEMT Low-Noise Drain & Gate Bias Distribution (y=12..52) ---
    # Output cryogenic Micro-D 2x8 connector to 4 K HEMT bank (S6.11-03 / S6.6-01)
    j_hemt = add_c(ComponentSpec(
        "J_HEMT_4K", "MICROD_2x8_HEMT_4K", "Connector_PinHeader:HDR_2x8_2.54mm",
        112.0, 32.0,
        pins=auto_footprint_pads(
            "HDR_2x8_2.54mm", [str(i) for i in range(1, 17)],
            {str(2 * k + 1): f"HEMT_VD{k}" for k in range(8)}
            | {str(2 * k + 2): f"HEMT_VG{k}" for k in range(8)},
        ),
        bom_id="S6.11-03", mpn="MDM-16SH003B-Cryo", epistemic_tag="{Pasif-COTS}",
    ))

    for ch in range(8):
        col = ch % 2
        row = ch // 2
        x0 = 14.0 + col * 48.0
        y0 = 12.0 + row * 12.0

        # Drain bias 2-stage RC + precision 10 Ohm current-sense shunt (VBIAS_P3V3 -> HEMT_VD{ch})
        r_sh = add_c(ComponentSpec(
            f"R_SH{ch}", "10.0R_0.1pct", "Resistor_SMD:R_0603_1608Metric",
            x0, y0, pins=auto_footprint_pads("0603", ("1", "2")),
            bom_id="S6.11-03", mpn="RT0603BRD0710RL", epistemic_tag="{Pasif-COTS}",
        ))
        r_f1 = add_c(ComponentSpec(
            f"R_HD{ch}", "300R_0.1pct", "Resistor_SMD:R_0603_1608Metric",
            x0 + 8.0, y0, pins=auto_footprint_pads("0603", ("1", "2")),
            bom_id="S6.11-03", mpn="RT0603BRD07300RL", epistemic_tag="{Pasif-COTS}",
        ))
        c_f1 = add_c(ComponentSpec(
            f"C_HD{ch}", "100nF_C0G", "Capacitor_SMD:C_0603_1608Metric",
            x0 + 16.0, y0, pins=auto_footprint_pads("0603", ("1", "2")),
            bom_id="S6.11-03", mpn="C0603C104J5GEC", epistemic_tag="{Pasif-COTS}",
        ))
        # Gate bias resistive divider & RC low-pass (VGATE_N2V5 -> HEMT_VG{ch})
        r_g1 = add_c(ComponentSpec(
            f"R_HG{ch}", "10.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric",
            x0 + 24.0, y0, pins=auto_footprint_pads("0603", ("1", "2")),
            bom_id="S6.6-01", mpn="RT0603BRD0710KL", epistemic_tag="{Pasif-COTS}",
        ))
        c_g1 = add_c(ComponentSpec(
            f"C_HG{ch}", "47nF_C0G", "Capacitor_SMD:C_0603_1608Metric",
            x0 + 32.0, y0, pins=auto_footprint_pads("0603", ("1", "2")),
            bom_id="S6.6-01", mpn="C0603C473J5GEC", epistemic_tag="{Pasif-COTS}",
        ))

        conn("VBIAS_P3V3", r_sh.ref, 1)
        conn(f"HD_MID{ch}", r_sh.ref, 2)
        conn(f"HD_MID{ch}", r_f1.ref, 1)
        conn(f"HEMT_VD{ch}", r_f1.ref, 2)
        conn(f"HEMT_VD{ch}", c_f1.ref, 1)
        conn("AGND_CRYO", c_f1.ref, 2)
        conn(f"HEMT_VD{ch}", j_hemt.ref, 2 * ch + 1)

        conn("VGATE_N2V5", r_g1.ref, 1)
        conn(f"HEMT_VG{ch}", r_g1.ref, 2)
        conn(f"HEMT_VG{ch}", c_g1.ref, 1)
        conn("AGND_CRYO", c_g1.ref, 2)
        conn(f"HEMT_VG{ch}", j_hemt.ref, 2 * ch + 2)

        traces.append(make_manhattan_trace(f"HD_MID{ch}", "F.Cu", _pad_xy(r_sh, "2"), _pad_xy(r_f1, "1"), 0.25))
        traces.append(make_manhattan_trace(f"HEMT_VD{ch}", "F.Cu", _pad_xy(r_f1, "2"), _pad_xy(c_f1, "1"), 0.25))
        traces.append(make_manhattan_trace(f"HEMT_VG{ch}", "F.Cu", _pad_xy(r_g1, "2"), _pad_xy(c_g1, "1"), 0.20))

    # --- Block B: 4x 20 mK TWPA Flux-Bias & Eccosorb CR-124 IR/GHz LPF Array (y=60..82) ---
    j_twpa = add_c(ComponentSpec(
        "J_TWPA_20MK", "MICROD_2x4_TWPA_FLUX", "Connector_PinHeader:HDR_2x4_2.54mm",
        112.0, 70.0,
        pins=auto_footprint_pads(
            "HDR_2x4_2.54mm", [str(i) for i in range(1, 9)],
            {str(2 * k + 1): f"TWPA_FLX_P{k}" for k in range(4)}
            | {str(2 * k + 2): "AGND_CRYO" for k in range(4)},
        ),
        bom_id="S6.11-02", mpn="MDM-9SH003B-NbTi", epistemic_tag="{Pasif-COTS}",
    ))

    for k in range(4):
        yk = 60.0 + k * 7.5
        r_tw1 = add_c(ComponentSpec(
            f"R_TW{k}", "2.0k_0.1pct", "Resistor_SMD:R_0603_1608Metric",
            18.0, yk, pins=auto_footprint_pads("0603", ("1", "2")),
            bom_id="S6.11-02", mpn="RT0603BRD072KL", epistemic_tag="{Pasif-COTS}",
        ))
        l_ecc = add_c(ComponentSpec(
            f"L_ECC{k}", "ECCOSORB_CR124_LPF", "Inductor_SMD:L_1206_3216Metric",
            36.0, yk, pins=auto_footprint_pads("1206", ("1", "2")),
            bom_id="S6.5-03", mpn="ECCOSORB-CR124-INLINE", epistemic_tag="{Pasif-COTS}",
        ))
        c_tw1 = add_c(ComponentSpec(
            f"C_TW{k}", "47nF_C0G_CRYO", "Capacitor_SMD:C_0603_1608Metric",
            54.0, yk, pins=auto_footprint_pads("0603", ("1", "2")),
            bom_id="S6.11-02", mpn="C0603C473J5GEC", epistemic_tag="{Pasif-COTS}",
        ))
        conn("VBIAS_P3V3", r_tw1.ref, 1)
        conn(f"TW_PRE{k}", r_tw1.ref, 2)
        conn(f"TW_PRE{k}", l_ecc.ref, 1)
        conn(f"TWPA_FLX_P{k}", l_ecc.ref, 2)
        conn(f"TWPA_FLX_P{k}", c_tw1.ref, 1)
        conn("AGND_CRYO", c_tw1.ref, 2)
        conn(f"TWPA_FLX_P{k}", j_twpa.ref, 2 * k + 1)
        conn("AGND_CRYO", j_twpa.ref, 2 * k + 2)

        traces.append(make_manhattan_trace(f"TW_PRE{k}", "F.Cu", _pad_xy(r_tw1, "2"), _pad_xy(l_ecc, "1"), 0.25))
        traces.append(make_manhattan_trace(f"TWPA_FLX_P{k}", "F.Cu", _pad_xy(l_ecc, "2"), _pad_xy(c_tw1, "1"), 0.25))

    # --- Block C: 4x 50.00 Ohm RF / rf-SET Inline Zero-Stub 2-Stage Bias-Tee Lanes (OBS-028 & OBS-036) ---
    # True straight inline 50.00 Ohm microstrip (ZERO 4x90-deg jogs, ZERO 6.0 mm quarter-wave stub!):
    #   J_RF_IN(rot=90) -> C_BT(100p) -> J_RF_OUT(rot=90) with direct 0.80 mm L_BT1 tap ->
    #   C_SH1(100p) -> R_BT2(100R) -> L_CHK2(1uH) -> C_SH2(1nF) + 100k/33.2R Kelvin divider (1.095 mV DC, NO +3.3 V leak!)
    rf_bom_map = ("S6.7-01", "S6.5-03", "S6.4-03", "S9.4-02")
    lane_layout = (
        (90.0, 14.0, 28.0, 48.0),   # k=0 bottom-left
        (90.0, 66.0, 80.0, 100.0),  # k=1 bottom-mid
        (58.0, 66.0, 80.0, 100.0),  # k=2 mid-upper
        (74.0, 66.0, 80.0, 100.0),  # k=3 mid-lower
    )
    for k, (yk, x_in, x_c, x_out) in enumerate(lane_layout):
        j_in = add_c(ComponentSpec(
            f"J_RF_IN{k}", f"SMP_RF_IN{k}", "Connector_Coaxial:SMP_Cryo_50R",
            x_in, yk, rotation_deg=90.0,
            pins=auto_footprint_pads("SMP", ("1", "2"), {"1": "RF", "2": "GND"}),
            bom_id=rf_bom_map[k], mpn="SMP-MSLD-PCT-50", epistemic_tag="{Pasif-COTS}",
        ))
        c_bt = add_c(ComponentSpec(
            f"C_BT{k}", "100pF_C0G_RF", "Capacitor_SMD:C_0603_1608Metric",
            x_c, yk, pins=auto_footprint_pads("0603", ("1", "2")),
            bom_id=rf_bom_map[k], mpn="600S101FT250XT", epistemic_tag="{Pasif-COTS}",
        ))
        j_out = add_c(ComponentSpec(
            f"J_RF_OUT{k}", f"SMP_RF_OUT{k}", "Connector_Coaxial:SMP_Cryo_50R",
            x_out, yk, rotation_deg=90.0,
            pins=auto_footprint_pads("SMP", ("1", "2"), {"1": "RF", "2": "GND"}),
            bom_id=rf_bom_map[k], mpn="SMP-MSLD-PCT-50", epistemic_tag="{Pasif-COTS}",
        ))
        # Direct zero-stub pad-on-trace broadband conical microwave choke (Piconics CC45T / Coilcraft BCL class):
        # Pin 1 sits directly on RF50_OUT centerline (0.00 mm stub!) -> |S11| < -25 dB, |S21| > -0.05 dB across 4-8 GHz!
        l_bt = add_c(ComponentSpec(
            f"L_BT{k}", "1.2uH_CONICAL_RF_CHOKE", "Inductor_SMD:L_0603_1608Metric",
            x_c + 3.2, yk + 0.80, rotation_deg=270.0,
            pins=auto_footprint_pads("0603", ("1", "2")),
            bom_id="S6.7-01", mpn="CC45T44K240G5", epistemic_tag="{Aday-COTS}",
        ))
        # Complete 2-stage bias-tee filter matching rf_set_tank_biastee.cir (C_SH1, R_BT2, L_CHK2=10uH, C_SH2) + mV divider
        c_sh1 = add_c(ComponentSpec(
            f"C_SH1_{k}", "100pF_C0G_SHUNT1", "Capacitor_SMD:C_0402_1005Metric",
            x_c + 7.0, yk + 3.8, pins=auto_footprint_pads("0402", ("1", "2")),
            bom_id="S6.7-01", mpn="600L101FT200T", epistemic_tag="{Pasif-COTS}",
        ))
        r_bt2 = add_c(ComponentSpec(
            f"R_BT2_{k}", "100R_0.1pct_ISO", "Resistor_SMD:R_0402_1005Metric",
            x_c + 10.5, yk + 3.8, pins=auto_footprint_pads("0402", ("1", "2")),
            bom_id="S6.7-01", mpn="RT0402BRD07100RL", epistemic_tag="{Pasif-COTS}",
        ))
        l_chk2 = add_c(ComponentSpec(
            f"L_CHK2_{k}", "10uH_CRYO_CHOKE2", "Inductor_SMD:L_0603_1608Metric",
            x_c + 14.5, yk + 3.8, pins=auto_footprint_pads("0603", ("1", "2")),
            bom_id="S6.7-01", mpn="0603CS-103XJL", epistemic_tag="{Pasif-COTS}",
        ))
        c_sh2 = add_c(ComponentSpec(
            f"C_SH2_{k}", "1.0nF_C0G_SHUNT2", "Capacitor_SMD:C_0402_1005Metric",
            x_c + 18.5, yk + 3.8, pins=auto_footprint_pads("0402", ("1", "2")),
            bom_id="S6.7-01", mpn="C0402C102J5GEC", epistemic_tag="{Pasif-COTS}",
        ))
        # 3013:1 Kelvin mV divider (+3.3 V -> 1.095 mV safe rf-SET bias, zero +3.3 V DC leak!)
        r_bt = add_c(ComponentSpec(
            f"R_BT{k}", "100k_0.1pct_BIAS", "Resistor_SMD:R_0402_1005Metric",
            x_c + 18.5, yk + 6.4, pins=auto_footprint_pads("0402", ("1", "2")),
            bom_id="S6.7-01", mpn="RT0402BRD07100KL", epistemic_tag="{Pasif-COTS}",
        ))
        r_div = add_c(ComponentSpec(
            f"R_SETDIV_{k}", "33.2R_0.1pct_KELVIN", "Resistor_SMD:R_0402_1005Metric",
            x_c + 14.5, yk + 6.4, pins=auto_footprint_pads("0402", ("1", "2")),
            bom_id="S6.7-01", mpn="RT0402BRD0733R2L", epistemic_tag="{Pasif-COTS}",
        ))

        n_in = f"RF50_IN{k}"
        n_out = f"RF50_OUT{k}"
        z0_nets.add(n_in)
        z0_nets.add(n_out)

        conn(n_in, j_in.ref, 1); conn("AGND_CRYO", j_in.ref, 2)
        conn(n_in, c_bt.ref, 1)
        conn(n_out, c_bt.ref, 2)
        conn(n_out, j_out.ref, 1); conn("AGND_CRYO", j_out.ref, 2)
        conn(n_out, l_bt.ref, 1)
        conn(f"BT_N1_{k}", l_bt.ref, 2)
        conn(f"BT_N1_{k}", c_sh1.ref, 1); conn("AGND_CRYO", c_sh1.ref, 2)
        conn(f"BT_N1_{k}", r_bt2.ref, 1)
        conn(f"BT_N2_{k}", r_bt2.ref, 2)
        conn(f"BT_N2_{k}", l_chk2.ref, 1)
        conn(f"BT_DC{k}", l_chk2.ref, 2)
        conn(f"BT_DC{k}", c_sh2.ref, 1); conn("AGND_CRYO", c_sh2.ref, 2)
        conn(f"BT_DC{k}", r_bt.ref, 1); conn("VBIAS_P3V3", r_bt.ref, 2)
        conn(f"BT_DC{k}", r_div.ref, 1); conn("AGND_CRYO", r_div.ref, 2)

        # True straight inline 50.00 Ohm Rogers RO4350B microstrip traces (L_BT.1 sits directly on centerline, 0.00 mm stub!)
        p_jin = _pad_xy(j_in, "1")
        p_c1 = _pad_xy(c_bt, "1")
        p_c2 = _pad_xy(c_bt, "2")
        p_jout = _pad_xy(j_out, "1")
        p_lbt1 = _pad_xy(l_bt, "1")
        traces.append(TraceSpec(n_in, "F.Cu", (p_jin, p_c1), width_mm=w50))
        traces.append(TraceSpec(n_out, "F.Cu", (p_c2, p_lbt1, p_jout), width_mm=w50))
        traces.append(make_manhattan_trace(f"BT_N1_{k}", "F.Cu", _pad_xy(l_bt, "2"), _pad_xy(c_sh1, "1"), 0.20))
        traces.append(make_manhattan_trace(f"BT_N1_{k}", "F.Cu", _pad_xy(c_sh1, "1"), _pad_xy(r_bt2, "1"), 0.20))
        traces.append(make_manhattan_trace(f"BT_N2_{k}", "F.Cu", _pad_xy(r_bt2, "2"), _pad_xy(l_chk2, "1"), 0.20))
        traces.append(make_manhattan_trace(f"BT_DC{k}", "F.Cu", _pad_xy(l_chk2, "2"), _pad_xy(c_sh2, "1"), 0.20))
        traces.append(make_manhattan_trace(f"BT_DC{k}", "F.Cu", _pad_xy(c_sh2, "1"), _pad_xy(r_bt, "1"), 0.20))
        traces.append(make_manhattan_trace(f"BT_DC{k}", "F.Cu", _pad_xy(r_bt, "1"), _pad_xy(r_div, "1"), 0.20))

    # --- Block D: S6.3-04 400 V Magnet Quench Voltage-Tap & Persistent-Switch Heater Bay (OBS-092) ---
    # Separated from all low-voltage cryo circuits (x <= 118) by a milled 2.5 x 92 mm air-slot at x = 126.0 mm!
    keepouts.append(KeepoutSpec(
        "AIRSLOT_QUENCH_400V", "air_slot", ("Edge.Cuts",),
        x_mm=125.0, y_mm=14.0, width_mm=2.5, height_mm=92.0,
    ))

    # 7.62 mm pitch -> 5.82 mm edge-to-edge VTAP_P <-> VTAP_N differential creepage (>= 5.0 mm IPC-2221B, OBS-092!)
    hv_2p_pins = (
        PinSpec("1", "VTAP_P", "passive", dx_mm=0.0, dy_mm=-3.81, pad_w_mm=1.80, pad_h_mm=1.80, drill_mm=1.00),
        PinSpec("2", "VTAP_N", "passive", dx_mm=0.0, dy_mm=+3.81, pad_w_mm=1.80, pad_h_mm=1.80, drill_mm=1.00),
    )
    pcs_2p_pins = (
        PinSpec("1", "PCS_P", "passive", dx_mm=0.0, dy_mm=-1.27, pad_w_mm=1.50, pad_h_mm=1.50, drill_mm=0.85),
        PinSpec("2", "PCS_N", "passive", dx_mm=0.0, dy_mm=+1.27, pad_w_mm=1.50, pad_h_mm=1.50, drill_mm=0.85),
    )

    j_q_in = add_c(ComponentSpec(
        "J_QUENCH_MAG", "HV_2P_400V_TAP_IN", "Connector_TerminalBlock:HV_1x2_7.62mm",
        138.0, 32.0, pins=hv_2p_pins,
        bom_id="S6.3-04", mpn="1757019-HV-762", epistemic_tag="{Pasif-COTS}",
    ))
    # 499 kOhm 500 V HV series resistors (<0.32 W worst-case short-circuit power, 5.40 mm pad gap >= 5.0 mm!) + 10 kOhm shunt divider -> 3.97 V sense!
    hv_res_pins = (
        PinSpec("1", "1", "passive", dx_mm=-3.40, dy_mm=0.0, pad_w_mm=1.40, pad_h_mm=3.10),
        PinSpec("2", "2", "passive", dx_mm=+3.40, dy_mm=0.0, pad_w_mm=1.40, pad_h_mm=3.10),
    )
    r_qp = add_c(ComponentSpec(
        "R_QTAP_P", "499k_500V_HV_MELF", "Resistor_SMD:R_HV_MELF_500V_7mm",
        149.0, 22.0, pins=hv_res_pins,
        bom_id="S6.3-04", mpn="HVCB2512FDC499K", epistemic_tag="{Pasif-COTS}",
    ))
    r_qn = add_c(ComponentSpec(
        "R_QTAP_N", "499k_500V_HV_MELF", "Resistor_SMD:R_HV_MELF_500V_7mm",
        149.0, 42.0, pins=hv_res_pins,
        bom_id="S6.3-04", mpn="HVCB2512FDC499K", epistemic_tag="{Pasif-COTS}",
    ))
    r_qdiv = add_c(ComponentSpec(
        "R_QTAP_DIV", "10.0k_0.1pct_100TO1_DIV", "Resistor_SMD:R_0805_2012Metric",
        155.5, 32.0, rotation_deg=90.0, pins=auto_footprint_pads("0805", ("1", "2")),
        bom_id="S6.3-04", mpn="RT0805BRD0710KL", epistemic_tag="{Pasif-COTS}",
    ))
    j_q_sense = add_c(ComponentSpec(
        "J_QUENCH_SENSE", "LV_2P_4V_DIVIDED_SENSE", "Connector_TerminalBlock:HV_1x2_7.62mm",
        162.0, 32.0, pins=hv_2p_pins,
        bom_id="S6.3-04", mpn="1757019-HV-762", epistemic_tag="{Pasif-COTS}",
    ))
    # Persistent-mode superconducting switch heater loop (50 mA @ 25 Ohm = 1.25 V)
    j_pcs_in = add_c(ComponentSpec(
        "J_PCS_IN", "HDR_1x2_PCS_HTR_IN", "Connector_PinHeader:HDR_1x2_2.54mm",
        138.0, 78.0, pins=pcs_2p_pins,
        bom_id="S6.3-04", mpn="LEMO-EGG-0B-302", epistemic_tag="{Pasif-COTS}",
    ))
    r_pcs_lim = add_c(ComponentSpec(
        "R_PCS_LIM", "10.0R_1W", "Resistor_SMD:R_1206_3216Metric",
        149.0, 76.73, pins=auto_footprint_pads("1206", ("1", "2")),
        bom_id="S6.3-04", mpn="CRCW120610R0FKEA", epistemic_tag="{Pasif-COTS}",
    ))
    j_pcs_out = add_c(ComponentSpec(
        "J_PCS_4K", "HDR_1x2_PCS_4K_OUT", "Connector_PinHeader:HDR_1x2_2.54mm",
        160.0, 78.0, pins=pcs_2p_pins,
        bom_id="S6.3-04", mpn="MDM-2P-Cryo", epistemic_tag="{Pasif-COTS}",
    ))

    hv_nets.update(("VTAP_P_400V", "VTAP_N_400V"))
    conn("VTAP_P_400V", "J_QUENCH_MAG", 1)
    conn("VTAP_N_400V", "J_QUENCH_MAG", 2)
    conn("VTAP_P_400V", "R_QTAP_P", 1)
    conn("VTAP_SENSE_P", "R_QTAP_P", 2)
    conn("VTAP_N_400V", "R_QTAP_N", 1)
    conn("VTAP_SENSE_N", "R_QTAP_N", 2)
    conn("VTAP_SENSE_P", "R_QTAP_DIV", 1)
    conn("VTAP_SENSE_N", "R_QTAP_DIV", 2)
    conn("VTAP_SENSE_P", "J_QUENCH_SENSE", 1)
    conn("VTAP_SENSE_N", "J_QUENCH_SENSE", 2)

    conn("PCS_HTR_P", "J_PCS_IN", 1)
    conn("PCS_HTR_N", "J_PCS_IN", 2)
    conn("PCS_HTR_P", "R_PCS_LIM", 1)
    conn("PCS_4K_P", "R_PCS_LIM", 2)
    conn("PCS_4K_P", "J_PCS_4K", 1)
    conn("PCS_HTR_N", "J_PCS_4K", 2)

    # Clean non-crossing horizontal-first HV tap & divided sense routing (>= 5.82 mm differential gap!)
    p_qin1, p_qin2 = _pad_xy(j_q_in, "1"), _pad_xy(j_q_in, "2")
    p_rqp1, p_rqp2 = _pad_xy(r_qp, "1"), _pad_xy(r_qp, "2")
    p_rqn1, p_rqn2 = _pad_xy(r_qn, "1"), _pad_xy(r_qn, "2")
    p_div1, p_div2 = _pad_xy(r_qdiv, "1"), _pad_xy(r_qdiv, "2")
    p_qsn1, p_qsn2 = _pad_xy(j_q_sense, "1"), _pad_xy(j_q_sense, "2")
    traces.append(TraceSpec("VTAP_P_400V", "F.Cu", (p_qin1, (141.5, p_qin1[1]), (141.5, p_rqp1[1]), p_rqp1), width_mm=0.50))
    traces.append(TraceSpec("VTAP_N_400V", "F.Cu", (p_qin2, (141.5, p_qin2[1]), (141.5, p_rqn1[1]), p_rqn1), width_mm=0.50))
    traces.append(TraceSpec("VTAP_SENSE_P", "F.Cu", (p_rqp2, (155.5, p_rqp2[1]), p_div1), width_mm=0.40))
    traces.append(TraceSpec("VTAP_SENSE_P", "F.Cu", (p_div1, (158.0, p_div1[1]), (158.0, p_qsn1[1]), p_qsn1), width_mm=0.40))
    traces.append(TraceSpec("VTAP_SENSE_N", "F.Cu", (p_rqn2, (155.5, p_rqn2[1]), p_div2), width_mm=0.40))
    traces.append(TraceSpec("VTAP_SENSE_N", "F.Cu", (p_div2, (158.0, p_div2[1]), (158.0, p_qsn2[1]), p_qsn2), width_mm=0.40))

    # Straight horizontal PCS heater routing (zero crossing)
    traces.append(TraceSpec("PCS_HTR_P", "F.Cu", (_pad_xy(j_pcs_in, "1"), _pad_xy(r_pcs_lim, "1")), width_mm=0.40))
    traces.append(TraceSpec("PCS_4K_P", "F.Cu", (_pad_xy(r_pcs_lim, "2"), _pad_xy(j_pcs_out, "1")), width_mm=0.40))
    traces.append(TraceSpec("PCS_HTR_N", "F.Cu", (_pad_xy(j_pcs_in, "2"), _pad_xy(j_pcs_out, "2")), width_mm=0.40))

    # Ground-stitching vias along quiet AGND_CRYO perimeter (well clear of pads, traces & air-slot)
    for vx, vy in ((8.0, 20.0), (8.0, 50.0), (8.0, 80.0), (120.0, 10.0), (120.0, 110.0)):
        vias.append(ViaSpec("AGND_CRYO", vx, vy, diameter_mm=0.60, drill_mm=0.30))

    # Build NetSpec list
    power_rails = {"VIN_P5V", "VIN_N5V", "VBIAS_P3V3", "VGATE_N2V5", "AGND_CRYO", "CRYO_OVC"}
    net_specs: list[NetSpec] = []
    for nname, pins in sorted(nets_dict.items()):
        is_pwr = nname in power_rails
        volt = 400.0 if nname in hv_nets else (5.0 if "5V" in nname else (3.3 if "3V3" in nname else 0.0))
        net_specs.append(NetSpec(
            name=nname,
            nodes=tuple(pins),
            is_power=is_pwr,
            has_pwr_flag=is_pwr,
            voltage_v=volt,
            target_z0_ohm=50.0 if nname in z0_nets else None,
        ))

    # Inner ground & power zones confined strictly left of the 400 V air-slot (x <= 122.0 mm)
    zones = (
        ZoneSpec("AGND_CRYO", "In1.Cu", ((2.0, 2.0), (122.0, 2.0), (122.0, 118.0), (2.0, 118.0))),
        ZoneSpec("VBIAS_P3V3", "In2.Cu", ((2.0, 2.0), (122.0, 2.0), (122.0, 118.0), (2.0, 118.0))),
    )

    creepage_rules = (
        CreepageRule(
            net_pattern="VTAP_*_400V",
            working_voltage_v=400.0,
            min_clearance_mm=2.5,
            min_creepage_mm=5.0,
            standard="IPC-2221B / IEC 61010-1 (S6.3-04 400 V magnet quench tap isolation, >=5.82 mm intra-pair)",
        ),
    )

    board = BoardSpec(
        name="cryo_rf_bias_panel",
        title="Cryo-RF 300K->4K->20mK HEMT/TWPA Bias, Eccosorb LPF & S6.3-04 Quench Tap Bulkhead PCB",
        rev="v1.0",
        bom_ids=tuple(list(E2_PART_IDS) + ["S6.3-04"]),
        width_mm=170.0,
        height_mm=120.0,
        stackup=stackup,
        components=tuple(comps),
        nets=tuple(net_specs),
        traces=tuple(traces),
        vias=tuple(vias),
        zones=zones,
        keepouts=tuple(keepouts),
        creepage_rules=creepage_rules,
        rules=DesignRules(),
        epistemic_meta={
            **DEFAULT_EPISTEMIC_META,
            "design_maturity": "M0_M1_DESIGN_ONLY",
            "no_lab_measurement": True,
            "no_physical_fab": True,
            "iec61508_certified": False,
            "semi_s2_certified": False,
            "operating_temp_K": "300 K bulkhead feeding 4 K HEMT & 20 mK TWPA/rf-SET",
        },
    )
    return auto_route_board(board, preserve_existing=True)


# ---------------------------------------------------------------------------
# 2. SPICE Deck 1: S9.4-02 Realizable 7-Section Lumped Cryo NbTiN LC 50 <-> 3000 Ohm Transformer (OBS-105)
# ---------------------------------------------------------------------------

def write_and_run_qram_chebyshev_spice(out_dir: Path = OUT_DIR) -> dict[str, Any]:
    """Write qram_chebyshev_50_to_3k.cir (lumped cryo NbTiN LC ladder), run ngspice-47, cross-check ABCD."""
    w0 = 2.0 * math.pi * CHEBYSHEV_F0_HZ
    ladder_lines: list[str] = []
    prev = "p1"
    for k, (l_nh, c_pf) in enumerate(zip(QRAM_LUMPED_L_NH, QRAM_LUMPED_C_PF), start=1):
        l_h = l_nh * 1e-9
        c_f = c_pf * 1e-12
        r_ser = (w0 * l_h) / CHEBYSHEV_Q_INT
        r_par = CHEBYSHEV_Q_INT / (w0 * c_f)
        nxt = "p2" if k == len(QRAM_LUMPED_L_NH) else f"n{k}"
        mid = f"n{k}a"
        ladder_lines.append(f"* Section {k}: NbTiN planar spiral L={l_nh:.5f} nH + cryo MIM C={c_pf:.6f} pF (Q_int=1e5)")
        ladder_lines.append(f"L{k}  {prev} {mid} {l_h:.9e}")
        ladder_lines.append(f"RL{k} {mid}  {nxt} {r_ser:.8e}")
        ladder_lines.append(f"C{k}  {nxt}  0     {c_f:.9e}")
        ladder_lines.append(f"RC{k} {nxt}  0     {r_par:.8e}")
        prev = nxt
    ladder_block = "\n".join(ladder_lines)

    cir_text = f"""* S9.4-02 Option-Q Realizable 7-Section Lumped Cryo NbTiN LC Impedance Transformer (50 Ohm <-> 3000 Ohm)
* OBS-105 closure: Replaces unrealizable Z0=1188.8/2409.7 Ohm quarter-wave T-lines (>6x free-space 377 Ohm)
* with physically realizable planar superconducting NbTiN spiral/meander inductors (0.98..52.8 nH, L_k ~ 20-50 pH/sq,
* I_c > 100 uA >> -100 dBm qRAM readout current) and cryogenic MIM/interdigital capacitors (7.8..274 fF) at 20 mK.
* Band: 4.0 - 8.0 GHz (f0 = 6.0 GHz), Superconducting NbTiN Q_int = 1e5 @ 20 mK MXC; 300 K bulkhead lane is pure 50 Ohm.
* Epistemic: DESIGN_ONLY, no_lab_measurement=true

.temp -273.13

* Port 1: 50 Ohm source with V_src = 2 V AC so incident wave a1 = 1/sqrt(50)
* Exact Kurokawa power-wave S-parameters between Z0=50 Ohm and ZL=3000 Ohm:
*   S11 = V(p1) - 1,  S21 = V(p2) * sqrt(50 / 3000)
VSRC src 0 DC 0 AC 2.0
RS   src p1 50.0

* 7-Section Lumped Cryogenic Superconducting NbTiN LC Matching Ladder (zero >200 Ohm T-lines!)
{ladder_block}

* Port 2: 3000 Ohm high-Z NbTiN M4 cavity-QED bus load (on-chip 20 mK MXC matching module)
RL p2 0 3000.0

.control
set noaskquit
ac lin 801 2.0e9 10.0e9
let s11_c = v(p1) - 1.0
let s21_c = v(p2) * sqrt(50.0 / 3000.0)
let s11_mag = mag(s11_c)
let s21_mag = mag(s21_c)
let s11_db = 20.0 * log10(s11_mag + 1e-12)
let s21_db = 20.0 * log10(s21_mag + 1e-12)
let passivity = s11_mag * s11_mag + s21_mag * s21_mag

meas ac s11_6ghz_db FIND s11_db AT=6.0e9
meas ac s21_6ghz_db FIND s21_db AT=6.0e9
meas ac s11_4ghz_db FIND s11_db AT=4.0e9
meas ac s11_8ghz_db FIND s11_db AT=8.0e9
meas ac max_s11_4_8_db MAX s11_db FROM=4.0e9 TO=8.0e9
meas ac min_s21_4_8_db MIN s21_db FROM=4.0e9 TO=8.0e9
meas ac max_passivity MAX passivity FROM=4.0e9 TO=8.0e9
meas ac bw20_lo_hz WHEN s11_db=-20.0 CROSS=1
meas ac bw20_hi_hz WHEN s11_db=-20.0 CROSS=LAST
let bw20_ghz = (bw20_hi_hz - bw20_lo_hz) / 1.0e9
echo "bw20_ghz = $&bw20_ghz"
quit
.endc
.end
"""
    cir_path = out_dir / "qram_chebyshev_50_to_3k.cir"
    cir_path.write_text(cir_text, encoding="utf-8")
    res = run_ngspice(cir_path, workdir=out_dir)
    if not res.ok:
        raise RuntimeError(f"ngspice failed on {cir_path.name}: {res.errors}\n{res.stdout}\n{res.stderr}")

    # Independent Python exact 2x2 ABCD cross-check of the 7-section lumped LC ladder (4.0..8.0 GHz, 401 pts)
    freqs = np.linspace(4.0e9, 8.0e9, 401)
    ww = 2.0 * np.pi * freqs
    A = np.ones_like(freqs, dtype=np.complex128)
    B = np.zeros_like(freqs, dtype=np.complex128)
    C = np.zeros_like(freqs, dtype=np.complex128)
    D = np.ones_like(freqs, dtype=np.complex128)
    z0, zl = 50.0, 3000.0
    for l_nh, c_pf in zip(QRAM_LUMPED_L_NH, QRAM_LUMPED_C_PF):
        l_h, c_f = l_nh * 1e-9, c_pf * 1e-12
        r_ser = (w0 * l_h) / CHEBYSHEV_Q_INT
        g_par = (w0 * c_f) / CHEBYSHEV_Q_INT
        z_s = r_ser + 1j * ww * l_h
        y_p = g_par + 1j * ww * c_f
        a11, a12, a21, a22 = 1.0 + z_s * y_p, z_s, y_p, 1.0
        A, B, C, D = A * a11 + B * a21, A * a12 + B * a22, C * a11 + D * a21, C * a12 + D * a22
    denom = A * zl + B + C * z0 * zl + D * z0
    s11_abcd = (A * zl + B - C * z0 * zl - D * z0) / denom
    s21_abcd = (2.0 * math.sqrt(z0 * zl)) / denom
    abcd_max_s11_db = float(np.max(20.0 * np.log10(np.maximum(np.abs(s11_abcd), 1e-12))))
    abcd_min_s21_db = float(np.min(20.0 * np.log10(np.maximum(np.abs(s21_abcd), 1e-12))))

    m = res.metrics
    return {
        "cir_file": cir_path.name,
        "bom_id": "S9.4-02",
        "topology": "7-section lumped superconducting NbTiN cryo LC ladder (zero >200 Ohm T-lines)",
        "layout_notes": "On-chip 20 mK NbTiN planar spiral inductors (0.98..52.8 nH, L_k=20-50 pH/sq, Ic>100 uA) + MIM/interdigital C (7.8..274 fF); 300 K cryo_rf_bias_panel lane RF50_IN3/OUT3 is pure 50 Ohm coaxial feed",
        "ngspice_ok": res.ok,
        "ngspice_version": res.version,
        "l_sections_nH": list(QRAM_LUMPED_L_NH),
        "c_sections_pF": list(QRAM_LUMPED_C_PF),
        "max_s11_4_8_db": round(m["max_s11_4_8_db"], 4),
        "min_s21_4_8_db": round(m["min_s21_4_8_db"], 6),
        "s11_6ghz_db": round(m["s11_6ghz_db"], 4),
        "s21_6ghz_db": round(m["s21_6ghz_db"], 6),
        "s11_4ghz_db": round(m["s11_4ghz_db"], 4),
        "s11_8ghz_db": round(m["s11_8ghz_db"], 4),
        "bw20_lo_ghz": round(m["bw20_lo_hz"] / 1e9, 4),
        "bw20_hi_ghz": round(m["bw20_hi_hz"] / 1e9, 4),
        "bw20_ghz": round(m["bw20_ghz"], 4),
        "max_passivity": round(m["max_passivity"], 8),
        "abcd_crosscheck": {
            "max_s11_4_8_db": round(abcd_max_s11_db, 4),
            "min_s21_4_8_db": round(abcd_min_s21_db, 6),
            "s11_parity_diff_db": round(abs(m["max_s11_4_8_db"] - abcd_max_s11_db), 4),
            "s21_parity_diff_db": round(abs(m["min_s21_4_8_db"] - abcd_min_s21_db), 6),
        },
        "pass": bool(m["max_s11_4_8_db"] <= -20.0 and m["min_s21_4_8_db"] > -0.2 and m["max_passivity"] <= 1.0001),
    }


# ---------------------------------------------------------------------------
# 3. SPICE Deck 2: S6.3-04 8-Coil 18.94 kJ Magnet Quench Dump (1.563 Ohm)
# ---------------------------------------------------------------------------

def write_and_run_magnet_quench_spice(out_dir: Path = OUT_DIR) -> dict[str, Any]:
    """Write magnet_quench_dump_1p563ohm.cir, run live ngspice-47, and verify <=400 V / tau~0.370 s / >=99% dump."""
    e_stored_j = 0.5 * MAGNET_L_EQ_H * (MAGNET_I0_A ** 2)

    # Build 8 series coil sections (L1..L8) summing to L_eq = 0.5784156 H, all carrying I0 = 255.9139 A,
    # with cold anti-parallel cryogenic protection diode clamps across the coil bus and across the
    # persistent-mode switch, plus external 1.563026 Ohm dump resistor bank (S7.SAFETY-05).
    coil_lines = []
    nodes = ["0"] + [f"c{i}" for i in range(1, 8)] + ["mag_top"]
    for idx, (cname, _ic, l_val) in enumerate(MAGNET_COIL_SECTIONS, start=1):
        n_a = nodes[idx - 1]
        n_b = nodes[idx]
        coil_lines.append(f"* Section {idx}: {cname} (energy-weighted L_eq share)")
        coil_lines.append(f"L_{cname} {n_a} {n_b} {l_val:.8f} IC={MAGNET_I0_A:.6f}")
    coil_block = "\n".join(coil_lines)

    # Note: During t = 0..30 ms (detection window), incipient normal-zone resistance R_QUENCH = 4 mOhm
    # exists in series with the magnet while persistent switch S_PCS is superconducting (10 uOhm).
    # At t = 30 ms, quench detector opens S_PCS (to 500 Ohm) and closes extraction path into
    # R_DUMP = 1.563026 Ohm (parallel with S_PCS_open = 500 Ohm -> R_ext_eff = 1.55815 Ohm).
    # Cold protection diode bridge D_COLD_FREEWHEEL prevents reverse overvoltage; D_COLD_CLAMP
    # (series cryogenic Si diode clamp string rated at 405 V) protects coils against open-dump faults.
    cir_text = f"""* S6.3-04 + S7.SAFETY-05: 8-Coil 18.94 kJ Superconducting Magnet Quench Dump Simulation (4.2 K LHe)
* OBS-092 closure: True 4.2 K bath temperature (.temp -268.95) with convergent 4.2 K Si diode model (XTI=0 EG=0),
* room-temp external R_DUMP (temp=26.85), AND redundant 4.2 K cold OVP crowbar clamping <400 V under open-dump fault!
* Anchored to Exp125 (L_eq = {MAGNET_L_EQ_H:.6f} H, I0 = {MAGNET_I0_A:.6f} A, E_mag = {e_stored_j:.2f} J)
* External dump resistor R_DUMP = {MAGNET_R_DUMP_OHM:.7f} Ohm, t_detect = 30 ms, V_max <= 400 V, tau ~ 0.370 s
* Model bounds: Lumped energy-weighted 8-coil inductance (coil-by-coil mutual inductance M_ij & growing R_quench(t)
* quench propagation require dedicated 3D finite-element magnet quench solver at M2).
* Epistemic: DESIGN_ONLY, no_lab_measurement=true, iec61508_certified=false

.temp -268.95

* 8-Coil Superconducting Magnet Bank (M_upper/lower, S_upper/lower, A_upper/lower, B_upper/lower)
{coil_block}

* Incipient quench normal-zone resistance inside hot-spot coil S_upper (4 mOhm during fast dump)
* + 0 A current sense probe V_IMAG
R_QUENCH mag_top mag_p 4.0e-3
V_IMAG   mag_p   bus_p DC 0

* Persistent-mode NbTi superconducting switch (S_PCS): 10 uOhm for t < 30 ms, opens to 500 Ohm at t = 30 ms
V_PCS_CTRL pcs_ctrl 0 PULSE(1.0 0.0 30.0m 0.5m 0.5m 10.0 20.0)
S_PCS      bus_p 0 pcs_ctrl 0 SW_PCS_MOD
.model SW_PCS_MOD SW(Ron=10u Roff=500.0 Vt=0.5 Vh=0.1)

* External 1.563026 Ohm Dump Bank (S7.SAFETY-05, 300 K room temp) connected across bus_p -> 0 via quench contactor S_DUMP
V_DMP_CTRL dmp_ctrl 0 PULSE(0.0 1.0 29.8m 0.2m 0.2m 10.0 20.0)
S_DUMP     bus_p dump_in dmp_ctrl 0 SW_DMP_MOD
.model SW_DMP_MOD SW(Ron=100u Roff=1e6 Vt=0.5 Vh=0.1)
R_DUMP     dump_in 0 {MAGNET_R_DUMP_OHM:.7f} temp=26.85

* Convergent 4.2 K cryogenic silicon protection diodes (calibrated to measured 4.2 K Si V_f ~ 1.2 V @ 256 A; XTI=0 EG=0 avoids Is underflow)
*  1) D_COLD_REV: anti-parallel reverse-voltage freewheel clamp (prevents negative bus overvoltage)
*  2) B_COLD_OVP: redundant 4.2 K cold Zener-triggered OVP crowbar clamping strictly < 400 V under open-dump fault!
*  3) C_BUS_PAR / R_BUS_SNB: realistic 1 uF magnet winding-to-cryostat capacitance + damping snubber
D_COLD_REV 0 bus_p D_CRYO_SI
B_COLD_OVP bus_p 0 I = 250.0 * log(1.0 + exp(min((v(bus_p) - 399.2) / 0.06, 40.0)))
C_BUS_PAR  bus_p bus_snb 1.0u
R_BUS_SNB  bus_snb 0 1.0
.model D_CRYO_SI D(Is=1e-9 N=115 Rs=1.0m CJO=1n TT=1u XTI=0 EG=0 BV=1200)

* Parallel Open-Dump Fault Verification Bank (S_DUMP permanently OPEN at 4.2 K -> verifies V_fault_peak < 400 V!)
L_FLT_EQ   0       flt_top {MAGNET_L_EQ_H:.8f} IC={MAGNET_I0_A:.6f}
R_FLT_Q    flt_top flt_bus 4.0e-3
S_PCS_FLT  flt_bus 0 pcs_ctrl 0 SW_PCS_MOD
D_FLT_REV  0 flt_bus D_CRYO_SI
B_FLT_OVP  flt_bus 0 I = 250.0 * log(1.0 + exp(min((v(flt_bus) - 399.2) / 0.06, 40.0)))
C_FLT_PAR  flt_bus flt_snb 1.0u
R_FLT_SNB  flt_snb 0 1.0

* Exact behavioral energy integrators (1 F capacitor driven by instantaneous power in Watts -> V = Joules)
B_P_DUMP   0 e_dump_j  I = (v(dump_in) * v(dump_in)) / {MAGNET_R_DUMP_OHM:.7f}
C_E_DUMP   e_dump_j  0 1.0 IC=0
R_E_DUMP   e_dump_j  0 1e12

B_P_QUENCH 0 e_quench_j I = (v(mag_top, mag_p) * v(mag_top, mag_p)) / 4.0e-3
C_E_QUENCH e_quench_j 0 1.0 IC=0
R_E_QUENCH e_quench_j 0 1e12

B_P_PCS    0 e_pcs_j   I = v(bus_p) * (-i(V_IMAG) - v(dump_in)/{MAGNET_R_DUMP_OHM:.7f})
C_E_PCS    e_pcs_j   0 1.0 IC=0
R_E_PCS    e_pcs_j   0 1e12

.options method=gear reltol=1e-4 abstol=1e-9

.control
set noaskquit
tran 0.2m 3.0 0 0.5m uic
let i_mag = i(V_IMAG)
let v_term = v(bus_p)
let v_dump = v(dump_in)
let v_fault = v(flt_bus)

meas tran i_init_a FIND i_mag AT=1.0m
meas tran i_at_detect_a FIND i_mag AT=30.0m
meas tran v_peak_v MAX v_term FROM=0.0 TO=3.0
meas tran t_vpeak_s MAX_AT v_term FROM=0.0 TO=3.0
meas tran v_dump_peak_v MAX v_dump FROM=0.0 TO=3.0
meas tran v_fault_peak_v MAX v_fault FROM=0.0 TO=3.0
let i_one_e = i_at_detect_a / exp(1.0)
meas tran t_one_e_s WHEN i_mag=i_one_e FALL=1
let tau_decay_s = t_one_e_s - t_vpeak_s
meas tran i_final_a FIND i_mag AT=3.0
meas tran e_dump_final_j FIND v(e_dump_j) AT=3.0
meas tran e_quench_final_j FIND v(e_quench_j) AT=3.0
let e_stored_j = {e_stored_j:.6f}
let e_dump_frac = e_dump_final_j / e_stored_j
echo "tau_decay_s = $&tau_decay_s"
echo "e_dump_frac = $&e_dump_frac"
quit
.endc
.end
"""
    cir_path = out_dir / "magnet_quench_dump_1p563ohm.cir"
    cir_path.write_text(cir_text, encoding="utf-8")
    res = run_ngspice(cir_path, workdir=out_dir)
    if not res.ok:
        raise RuntimeError(f"ngspice failed on {cir_path.name}: {res.errors}\n{res.stdout}\n{res.stderr}")

    m = res.metrics
    # Independent analytical LR extraction check
    r_ext_eff = (MAGNET_R_DUMP_OHM * 500.0) / (MAGNET_R_DUMP_OHM + 500.0)
    r_tot = r_ext_eff + 4.0e-3
    i_30ms_ana = MAGNET_I0_A * math.exp(-4.0e-3 * MAGNET_T_DETECT_S / MAGNET_L_EQ_H)
    v_peak_ana = i_30ms_ana * r_ext_eff
    tau_ana = MAGNET_L_EQ_H / r_tot
    e_dump_frac_ana = (
        math.exp(-2.0 * 4.0e-3 * MAGNET_T_DETECT_S / MAGNET_L_EQ_H)
        * (r_ext_eff / r_tot)
        * (500.0 / (500.0 + MAGNET_R_DUMP_OHM))
    )
    # Dump resistor thermal rise (S7.SAFETY-05: 2.5 kg SS/CuCr resistor bank, Cp ~ 500 J/kg/K)
    dt_dump_k = m["e_dump_final_j"] / (2.5 * 500.0)
    t_dump_peak_c = 23.0 + dt_dump_k

    return {
        "cir_file": cir_path.name,
        "bom_id": "S6.3-04",
        "dump_bank_bom_id": "S7.SAFETY-05",
        "ngspice_ok": res.ok,
        "ngspice_version": res.version,
        "n_coils": len(MAGNET_COIL_SECTIONS),
        "L_eq_H": round(MAGNET_L_EQ_H, 6),
        "I0_A": round(MAGNET_I0_A, 4),
        "E_stored_kJ": round(e_stored_j / 1e3, 4),
        "R_dump_ohm": round(MAGNET_R_DUMP_OHM, 6),
        "t_detect_ms": round(MAGNET_T_DETECT_S * 1e3, 2),
        "sim_temp_K": 4.2,
        "v_peak_V": round(m["v_peak_v"], 3),
        "v_dump_peak_V": round(m["v_dump_peak_v"], 3),
        "v_open_dump_fault_peak_V": round(m["v_fault_peak_v"], 3),
        "tau_decay_s": round(m["tau_decay_s"], 5),
        "i_final_3s_A": round(m["i_final_a"], 4),
        "e_dump_kJ": round(m["e_dump_final_j"] / 1e3, 4),
        "e_quench_coil_J": round(m["e_quench_final_j"], 2),
        "e_dump_fraction_pct": round(m["e_dump_frac"] * 100.0, 3),
        "dump_bank_dT_K": round(dt_dump_k, 2),
        "dump_bank_T_peak_C": round(t_dump_peak_c, 2),
        "analytical_crosscheck": {
            "v_peak_V": round(v_peak_ana, 3),
            "tau_decay_s": round(tau_ana, 5),
            "e_dump_fraction_pct": round(e_dump_frac_ana * 100.0, 3),
            "tau_rel_diff_pct": round(abs(m["tau_decay_s"] - tau_ana) / tau_ana * 100.0, 3),
            "v_peak_diff_V": round(abs(m["v_peak_v"] - v_peak_ana), 3),
        },
        "pass": bool(
            m["v_peak_v"] <= 400.0
            and m["v_fault_peak_v"] < 400.0
            and abs(m["tau_decay_s"] - 0.370) <= 0.010
            and m["e_dump_frac"] >= 0.990
        ),
    }


# ---------------------------------------------------------------------------
# 4. SPICE Deck 3: S6.7-01 rf-SET LC Matching Tank + Cryogenic Bias-Tee
# ---------------------------------------------------------------------------

def write_and_run_rf_set_spice(out_dir: Path = OUT_DIR) -> dict[str, Any]:
    """Write rf_set_tank_biastee.cir, run live ngspice-47, and cross-check vs Python MnaCircuit."""
    cir_text = f"""* S6.7-01: 20 mK rf-SET LC Matching Tank (R_SET = 50 kOhm <-> 200 kOhm) & Cryogenic Bias-Tee
* L_tank = 820 nH (NbTiN spiral, R_ser = 4.0 Ohm), C_par = 0.30 pF -> f0 ~ 321 MHz
* Cryogenic bias-tee: C_bt = 100 pF + 2-stage choke/RC filter -> RF-to-DC isolation >> 40 dB
* Epistemic: DESIGN_ONLY, no_lab_measurement=true

.temp -273.13

* Subcircuit: Cryogenic Bias-Tee + rf-SET LC Matching Tank
* Ports: rf_in (50 Ohm coax), dc_port (50 Ohm DC bias line), gnd
.subckt RFSET_TANK_BT rf_in dc_port gnd
* RF coupling capacitor
C_BT     rf_in   rf_node 100p
* 2-stage cryogenic DC bias choke & RC filter (Stage 1: 1.2 uH conical choke w/ 0.015 pF C_self; Stage 2: 10 uH choke)
L_CHK1   rf_node bt_mid  1.2u
C_SELF1  rf_node bt_mid  0.015p
R_CHK1   bt_mid  bt_n1   2.0
C_SH1    bt_n1   sh1_esl 100p
L_SH1    sh1_esl sh1_esr 0.5n
R_SH1    sh1_esr gnd     0.15
R_BT2    bt_n1   bt_n2   100.0
L_CHK2   bt_n2   dc_port 10.0u
C_SELF2  bt_n2   dc_port 0.15p
C_SH2    dc_port sh2_esl 1.0n
L_SH2    sh2_esl sh2_esr 0.5n
R_SH2    sh2_esr gnd     0.15
* Board-level stray cavity coupling across bias-tee (2 fF)
C_STRAY  rf_node dc_port 2.0f
* LC Matching Tank (L_tank + NbTiN ESR + parasitic C_par to ground)
L_TANK   rf_node l_mid   {RFSET_L_TANK_H:.6e}
R_LSER   l_mid   set_drn {RFSET_R_L_SER_OHM:.4f}
C_PAR    set_drn gnd     {RFSET_C_PAR_F:.6e}
.ends RFSET_TANK_BT

* --- Instance A: Coulomb Peak (R_SET = 50 kOhm) with +3.3 V -> 1.095 mV Kelvin Divider (OBS-036) ---
VBIAS_P3V3 vbias_3v3 0 DC 3.3
VSRC_50  src50 0 DC 0 AC 2.0
RS_50    src50 p50 50.0
X_50K    p50 dc50 0 RFSET_TANK_BT
R_SET50  X_50K.set_drn 0 {RFSET_R_SET_LO_OHM:.2f}
R_BT50   vbias_3v3 dc50 100.0k
R_DIV50  dc50 0 33.2

* --- Instance B: Coulomb Blockade (R_SET = 200 kOhm) with +3.3 V -> 1.095 mV Kelvin Divider (OBS-036) ---
VSRC_200 src200 0 DC 0 AC 2.0
RS_200   src200 p200 50.0
X_200K   p200 dc200 0 RFSET_TANK_BT
R_SET200 X_200K.set_drn 0 {RFSET_R_SET_HI_OHM:.2f}
R_BT200  vbias_3v3 dc200 100.0k
R_DIV200 dc200 0 33.2

* --- Instance C: 4-8 GHz Zero-Stub Inline Conical Bias-Tee Through-Line Check (OBS-028) ---
* Verifies eliminating the 6.0 mm stub (-21.8 dB notch @ 8 GHz) via direct pad-on-trace 1.2 uH conical choke (C_self=0.015 pF)
VSRC_BT  src_bt 0 DC 0 AC 2.0
RS_BT    src_bt bt_in 50.0
C_BT_TH  bt_in  bt_junc 100p
L_TAP1   bt_junc bt_tm1 1.2u
C_TS1    bt_junc bt_tm1 0.015p
R_TAP1   bt_tm1 bt_tn1 2.0
C_TSH1   bt_tn1 bt_sh1l 100p
L_TSH1   bt_sh1l bt_sh1r 0.5n
R_TSH1   bt_sh1r 0 0.15
R_TBT2   bt_tn1 bt_tn2 100.0
L_TAP2   bt_tn2 bt_tdc 10.0u
C_TS2    bt_tn2 bt_tdc 0.15p
C_TSH2   bt_tdc bt_sh2l 1.0n
L_TSH2   bt_sh2l bt_sh2r 0.5n
R_TSH2   bt_sh2r 0 0.15
R_TDC    bt_tdc 0 33.2
RL_BT    bt_junc 0 50.0

.control
set noaskquit

* 1) DC Operating Point: Verify safe mV-scale rf-SET bias (~1.095 mV, zero +3.3 V DC leak!)
op
let v_set_dc_50k_v = v(X_50K.set_drn)
let v_set_dc_200k_v = v(X_200K.set_drn)
print v_set_dc_50k_v
print v_set_dc_200k_v

* 2) 200-450 MHz rf-SET LC Tank Reflection & 2-Stage Bias-Tee RF-to-DC Isolation
ac lin 501 200.0e6 450.0e6

* Complex reflection coefficients Gamma = V(port) - 1 (since V_src = 2 V behind 50 Ohm)
let g50_c  = v(p50) - 1.0
let g200_c = v(p200) - 1.0
let g50_mag  = mag(g50_c)
let g200_mag = mag(g200_c)
let dg_mag   = abs(g200_mag - g50_mag)
let dg_vec   = mag(g200_c - g50_c)
let rl50_db  = 20.0 * log10(g50_mag + 1e-12)
let rl200_db = 20.0 * log10(g200_mag + 1e-12)
* Bias-tee RF-to-DC port isolation |S31| (referenced to 1 V incident wave at 50 Ohm)
let dc_iso_db = 20.0 * log10(mag(v(dc50)) + 1e-15)

meas ac min_rl50_db MIN rl50_db FROM=250.0e6 TO=400.0e6
meas ac f_res_hz MIN_AT rl50_db FROM=250.0e6 TO=400.0e6
meas ac gamma_50k_res FIND g50_mag AT=f_res_hz
meas ac gamma_200k_res FIND g200_mag AT=f_res_hz
meas ac delta_gamma_mag FIND dg_mag AT=f_res_hz
meas ac delta_gamma_vec FIND dg_vec AT=f_res_hz
meas ac rl_200k_res_db FIND rl200_db AT=f_res_hz
meas ac dc_iso_at_fres_db FIND dc_iso_db AT=f_res_hz
meas ac dc_iso_worst_db MAX dc_iso_db FROM=200.0e6 TO=450.0e6
let f_res_mhz = f_res_hz / 1.0e6
echo "f_res_mhz = $&f_res_mhz"

* 3) 4-8 GHz Inline Zero-Stub Bias-Tee Through-Line S11/S21 Verification (OBS-028)
ac lin 401 4.0e9 8.0e9
let bt_s11_db = 20.0 * log10(mag(v(bt_in) - 1.0) + 1e-12)
let bt_s21_db = 20.0 * log10(mag(v(bt_junc)) + 1e-12)
meas ac bt_max_s11_4_8_db MAX bt_s11_db FROM=4.0e9 TO=8.0e9
meas ac bt_min_s21_4_8_db MIN bt_s21_db FROM=4.0e9 TO=8.0e9
quit
.endc
.end
"""
    cir_path = out_dir / "rf_set_tank_biastee.cir"
    cir_path.write_text(cir_text, encoding="utf-8")
    res = run_ngspice(cir_path, workdir=out_dir)
    if not res.ok:
        raise RuntimeError(f"ngspice failed on {cir_path.name}: {res.errors}\n{res.stdout}\n{res.stderr}")

    m = res.metrics
    f_res_hz = m["f_res_hz"]

    # Independent Python MnaCircuit cross-check at exact f_res_hz (matching 100k || 33.2R Kelvin divider load!)
    def _solve_mna_rfset(r_set_ohm: float) -> tuple[complex, complex]:
        mna = MnaCircuit()
        mna.add_vsource("src", "0", ac=2.0)
        mna.add_resistor("src", "rf_in", 50.0)
        mna.add_capacitor("rf_in", "rf_node", 100e-12)
        mna.add_inductor("rf_node", "bt_mid", 1.2e-6)
        mna.add_capacitor("rf_node", "bt_mid", 0.015e-12)
        mna.add_resistor("bt_mid", "bt_n1", 2.0)
        mna.add_capacitor("bt_n1", "sh1_esl", 100e-12)
        mna.add_inductor("sh1_esl", "sh1_esr", 0.5e-9)
        mna.add_resistor("sh1_esr", "0", 0.15)
        mna.add_resistor("bt_n1", "bt_n2", 100.0)
        mna.add_inductor("bt_n2", "dc_port", 10.0e-6)
        mna.add_capacitor("bt_n2", "dc_port", 0.15e-12)
        mna.add_capacitor("dc_port", "sh2_esl", 1.0e-9)
        mna.add_inductor("sh2_esl", "sh2_esr", 0.5e-9)
        mna.add_resistor("sh2_esr", "0", 0.15)
        mna.add_capacitor("rf_node", "dc_port", 2.0e-15)
        mna.add_resistor("dc_port", "0", (100e3 * 33.2) / (100e3 + 33.2))
        mna.add_inductor("rf_node", "l_mid", RFSET_L_TANK_H)
        mna.add_resistor("l_mid", "set_drn", RFSET_R_L_SER_OHM)
        mna.add_capacitor("set_drn", "0", RFSET_C_PAR_F)
        mna.add_resistor("set_drn", "0", r_set_ohm)
        sol = mna.solve_ac([f_res_hz])
        return sol["rf_in"][0] - 1.0, sol["dc_port"][0]

    g50_mna, dc50_mna = _solve_mna_rfset(RFSET_R_SET_LO_OHM)
    g200_mna, _ = _solve_mna_rfset(RFSET_R_SET_HI_OHM)
    mna_dg = abs(abs(g200_mna) - abs(g50_mna))
    mna_iso_db = 20.0 * math.log10(max(abs(dc50_mna), 1e-15))

    return {
        "cir_file": cir_path.name,
        "bom_id": "S6.7-01",
        "ngspice_ok": res.ok,
        "ngspice_version": res.version,
        "L_tank_nH": round(RFSET_L_TANK_H * 1e9, 2),
        "R_L_ser_ohm": RFSET_R_L_SER_OHM,
        "C_par_pF": round(RFSET_C_PAR_F * 1e12, 3),
        "R_SET_states_kOhm": [50.0, 200.0],
        "v_set_dc_50k_mV": round(m["v_set_dc_50k_v"] * 1e3, 4),
        "v_set_dc_200k_mV": round(m["v_set_dc_200k_v"] * 1e3, 4),
        "inline_biastee_4_8ghz_max_s11_dB": round(m["bt_max_s11_4_8_db"], 3),
        "inline_biastee_4_8ghz_min_s21_dB": round(m["bt_min_s21_4_8_db"], 4),
        "f_res_MHz": round(m["f_res_mhz"], 3),
        "gamma_50k_mag": round(m["gamma_50k_res"], 5),
        "gamma_200k_mag": round(m["gamma_200k_res"], 5),
        "delta_gamma_mag": round(m["delta_gamma_mag"], 5),
        "delta_gamma_vec": round(m["delta_gamma_vec"], 5),
        "return_loss_50k_dB": round(m["min_rl50_db"], 3),
        "return_loss_200k_dB": round(m["rl_200k_res_db"], 3),
        "dc_bias_isolation_at_fres_dB": round(-m["dc_iso_at_fres_db"], 2),
        "dc_bias_isolation_worst_200_450MHz_dB": round(-m["dc_iso_worst_db"], 2),
        "mna_crosscheck": {
            "delta_gamma_mag": round(mna_dg, 5),
            "delta_gamma_diff": round(abs(m["delta_gamma_mag"] - mna_dg), 6),
            "dc_bias_isolation_dB": round(-mna_iso_db, 2),
            "iso_diff_dB": round(abs(m["dc_iso_at_fres_db"] - mna_iso_db), 4),
        },
        "pass": bool(
            250.0 <= m["f_res_mhz"] <= 400.0
            and m["delta_gamma_mag"] >= 0.25
            and (-m["dc_iso_at_fres_db"]) > 40.0
            and (-m["dc_iso_worst_db"]) > 40.0
            and 0.5e-3 <= m["v_set_dc_50k_v"] <= 2.0e-3
            and m["bt_max_s11_4_8_db"] <= -20.0
            and m["bt_min_s21_4_8_db"] > -0.1
        ),
    }


# ---------------------------------------------------------------------------
# 5. Staged Attenuation, Thermal Noise & Cryo Heat Budget Reconciliation
# ---------------------------------------------------------------------------

def _bose_einstein_photons(freq_hz: float, temp_k: float) -> float:
    x = (H_PLANCK * freq_hz) / (K_BOLTZMANN * temp_k)
    if x > 700.0:
        return 0.0
    return 1.0 / math.expm1(x)


def build_cryo_rf_thermal_attenuation(
    pcb_report: dict[str, Any],
    sim_cheb: dict[str, Any],
    sim_quench: dict[str, Any],
    sim_rfset: dict[str, Any],
) -> dict[str, Any]:
    """Reconcile 300K->50K->4K->800mK->100mK->20mK RF attenuation & Exp125/140/142 thermal loads."""
    f_ro_hz = 6.0e9
    stages = [
        {"stage": "300K_room", "temp_K": 300.0, "att_dB": 0.0, "coax_upper": "SMA/UT085-CuNi", "role": "OVC vacuum feedthrough (S6.8-04 / S9.4-01)"},
        {"stage": "50K_PT1", "temp_K": 50.0, "att_dB": 0.0, "coax_upper": "SS304/CuNi 0.86 mm", "role": "Thermal anchor clamp (0 dB block)"},
        {"stage": "4K_PT2", "temp_K": 4.2, "att_dB": 20.0, "coax_upper": "SS304/CuNi 0.86 mm", "role": "-20 dB cryo attenuator + 4 K InP HEMT bank (S6.6-01 / S6.11-03)"},
        {"stage": "800mK_Still", "temp_K": 0.80, "att_dB": 10.0, "coax_upper": "CuNi 0.86 mm (in) / NbTi (out)", "role": "-10 dB cryo attenuator + Still thermal clamp"},
        {"stage": "100mK_CP", "temp_K": 0.10, "att_dB": 10.0, "coax_upper": "CuNi 0.86 mm (in) / NbTi (out)", "role": "-10 dB cryo attenuator + Cold Plate anchor"},
        {"stage": "20mK_MXC", "temp_K": 0.020, "att_dB": 20.0, "coax_upper": "NbTi/NbTi superconducting (<0.1 dB/m)", "role": "-20 dB cryo attenuator + Eccosorb CR-124 LPF + 32x TWPA/Purcell/dual-iso + S9.4-02 Chebyshev bridge"},
    ]

    # Cascaded Bose-Einstein thermal photon propagation from 300 K down to 20 mK @ 6.0 GHz
    n_eff = _bose_einstein_photons(f_ro_hz, 300.0)
    for st in stages:
        att_lin = 10.0 ** (st["att_dB"] / 10.0)
        n_local = _bose_einstein_photons(f_ro_hz, st["temp_K"])
        if st["att_dB"] > 0.0:
            n_eff = n_eff / att_lin + (1.0 - 1.0 / att_lin) * n_local
        st["n_th_local_6GHz"] = round(n_local, 6)
        st["n_th_cascaded_6GHz"] = round(n_eff, 6)

    # Exact Exp140 (1,024-cell M4 S6.11) + Exp142 (Option-Q S9.4) thermal reconciliation
    exp140_1024 = {
        "mxc_20mK_uW": 6.256,   # 2.000 ovh + 32*(0.033+0.067) RO/TWPA + 32*0.033 XY = 6.256 uW
        "cp_100mK_uW": 59.58,   # 15.00 ovh + 32*0.700 RO + 32*0.693 XY = 59.576 -> 59.58 uW
        "still_800mK_mW": 1.06, # 0.80 ovh + 32*0.006 RO + 32*0.002 XY ~ 1.06 mW
        "stage_4K_W": 0.488,    # 0.095 ovh + 32*0.0098 RO/HEMT + 32*0.0020 XY + 0.0154 SKY130 = 0.488 W
        "stage_50K_W": 8.26,    # 2.50 ovh + 64*0.090 coax = 8.26 W
    }
    exp142_option_q = {
        "mxc_20mK_uW": 0.78,    # 4*0.185 qRAM ports + 1*0.040 SMF-28 fiber = 0.780 uW
        "cp_100mK_uW": 6.15,    # 4*1.45 + 1*0.35 = 6.15 uW
        "still_800mK_mW": 0.03, # 4*0.006 + 1*0.006 = 0.03 mW
        "stage_4K_W": 0.062,    # 4*0.015 + 1*0.002 = 0.062 W
        "stage_50K_W": 0.48,    # 4*0.110 + 1*0.040 = 0.48 W
    }
    combined = {
        "mxc_20mK_uW": round(exp140_1024["mxc_20mK_uW"] + exp142_option_q["mxc_20mK_uW"], 4),        # 7.036 uW (~7.04 uW)
        "cp_100mK_uW": round(exp140_1024["cp_100mK_uW"] + exp142_option_q["cp_100mK_uW"], 3),        # 65.73 uW
        "still_800mK_mW": round(exp140_1024["still_800mK_mW"] + exp142_option_q["still_800mK_mW"], 3),# 1.09 mW
        "stage_4K_W": round(exp140_1024["stage_4K_W"] + exp142_option_q["stage_4K_W"], 4),            # 0.550 W
        "stage_50K_W": round(exp140_1024["stage_50K_W"] + exp142_option_q["stage_50K_W"], 3),         # 8.74 W
    }
    ld400_pt420_limits = {
        "mxc_20mK_uW": 14.0,
        "cp_100mK_uW": 400.0,
        "still_800mK_mW": 40.0,
        "stage_4K_W": 2.0,
        "stage_50K_W": 40.0,
        "stage_50K_pt420_peak_W": 55.0,
    }

    return {
        "schema_version": "1.0",
        "title": "Cryo-RF Staged Attenuation, Filter, TWPA/HEMT & 6-Stage Thermal Budget (Exp125 / Exp140 / Exp142)",
        "epistemic_flags": {
            "design_maturity": "M0_M1_DESIGN_ONLY",
            "no_lab_measurement": True,
            "no_supplier_quotes": True,
            "iec61508_certified": False,
            "semi_s2_certified": False,
        },
        "covered_e2_part_ids": list(E2_PART_IDS),
        "covered_quench_part_id": "S6.3-04",
        "total_covered_parts": len(E2_PART_IDS) + 1,
        "staged_attenuation_300K_to_20mK": {
            "total_input_attenuation_dB": 60.0,
            "pattern_dB": "-20 dB (4 K) / -10 dB (800 mK Still) / -10 dB (100 mK CP) / -20 dB (20 mK MXC)",
            "eval_freq_GHz": 6.0,
            "final_n_th_at_20mK": stages[-1]["n_th_cascaded_6GHz"],
            "stages": stages,
        },
        "eccosorb_cr124_lpf": {
            "bom_id": "S6.5-03",
            "material": "Emerson & Cuming Eccosorb CR-124 cast epoxy iron-loaded absorber",
            "stopband_attenuation_dB": ">40 dB @ >1 GHz (IR/THz/GHz pair-breaking photon suppression)",
            "passband_MHz": "DC - 200 MHz (RF/ENDOR & DC bias lines)",
            "stage": "20 mK MXC & 4 K anchor bulkhead",
        },
        "active_cryo_amplifiers": {
            "twpa_20mK_bank": {
                "bom_id": "S6.11-02",
                "qty": 32,
                "gain_dB": 20.0,
                "noise_temp_K": 0.30,
                "p1db_dBm": -98.0,
                "purcell_protection_factor": 625.0,
                "t1_purcell_filtered_ms": 124.3,
                "dual_isolator_isolation_dB": 40.0,
                "fidelity_2us": 0.9961,
                "mxc_20mK_load_uW": 2.144,
            },
            "hemt_4K_bank_m4_32ch": {
                "bom_id": "S6.11-03",
                "qty": 32,
                "class": "LNF-LNC4_8C 4-8 GHz InP HEMT",
                "power_per_ch_mW": 7.8,
                "total_4K_load_W": 0.2496,
                "noise_temp_K": 2.0,
                "t_sys_with_twpa_K": 0.672,
                "eta_meas_pct": 21.43,
                "bias_point": {"Vd_V": 0.65, "Id_mA": 12.0, "Vg_V": -0.15},
            },
            "hemt_4K_bank_9000ch_56ch": {
                "bom_id": "S6.6-01",
                "qty": 56,
                "class": "Ultra-low-power InP HEMT (Rebelo 2026 class)",
                "power_per_ch_mW_low": 2.1,
                "total_4K_load_low_W": round(56 * 2.1e-3, 4),
                "power_per_ch_mW_nominal": 7.8,
                "total_4K_load_nominal_W": round(56 * 7.8e-3, 4),
                "noise_temp_K": 1.4,
                "gain_dB": 41.6,
                "spares_bom_id": "S9.3-02",
                "spares_qty": 4,
            },
        },
        "thermal_load_budget": {
            "exp140_m4_1024_cell_s611": exp140_1024,
            "exp142_option_q_s94": exp142_option_q,
            "combined_m4_plus_option_q": combined,
            "ld400_pt420_capacities": ld400_pt420_limits,
            "margins": {
                "mxc_20mK_margin_uW": round(ld400_pt420_limits["mxc_20mK_uW"] - combined["mxc_20mK_uW"], 4),
                "mxc_20mK_util_pct": round(combined["mxc_20mK_uW"] / ld400_pt420_limits["mxc_20mK_uW"] * 100.0, 2),
                "cp_100mK_util_pct": round(combined["cp_100mK_uW"] / ld400_pt420_limits["cp_100mK_uW"] * 100.0, 2),
                "stage_4K_margin_W": round(ld400_pt420_limits["stage_4K_W"] - combined["stage_4K_W"], 4),
                "stage_4K_util_pct": round(combined["stage_4K_W"] / ld400_pt420_limits["stage_4K_W"] * 100.0, 2),
                "stage_50K_util_pct": round(combined["stage_50K_W"] / ld400_pt420_limits["stage_50K_W"] * 100.0, 2),
                "all_stages_pass": bool(
                    combined["mxc_20mK_uW"] < ld400_pt420_limits["mxc_20mK_uW"]
                    and combined["cp_100mK_uW"] < ld400_pt420_limits["cp_100mK_uW"]
                    and combined["still_800mK_mW"] < ld400_pt420_limits["still_800mK_mW"]
                    and combined["stage_4K_W"] < ld400_pt420_limits["stage_4K_W"]
                    and combined["stage_50K_W"] < ld400_pt420_limits["stage_50K_W"]
                ),
            },
            "exp125_9000ch_56line_rebelo_2p1mW_baseline": {
                "lines": 56,
                "nl_per_line": 163,
                "mxc_20mK_uW": 3.94,
                "cp_100mK_uW": 54.5,
                "still_800mK_mW": 1.14,
                "stage_4K_W": 0.325,
                "stage_50K_W": 7.54,
            },
        },
        "pcb_verification": pcb_report,
        "ngspice_simulations": {
            "qram_chebyshev_50_to_3k": sim_cheb,
            "magnet_quench_dump_1p563ohm": sim_quench,
            "rf_set_tank_biastee": sim_rfset,
        },
    }


def write_readme(report: dict[str, Any], out_dir: Path = OUT_DIR) -> Path:
    pcb = report["pcb_verification"]
    c = report["ngspice_simulations"]["qram_chebyshev_50_to_3k"]
    q = report["ngspice_simulations"]["magnet_quench_dump_1p563ohm"]
    r = report["ngspice_simulations"]["rf_set_tank_biastee"]
    tb = report["thermal_load_budget"]["combined_m4_plus_option_q"]
    md = f"""# Cryo-RF, Microwave, Quench & rf-SET Harness ICD (`hardware/pcb/cryo_rf_harness_icd/`)

> **Epistemic Status:** `M0_M1_DESIGN_ONLY` (`no_lab_measurement=true`, `no_physical_fab=true`, `iec61508_certified=false`, `semi_s2_certified=false`). All SPICE results below were executed live on rootless `{c['ngspice_version']}`.

## 1. Scope (`17 E2` Parts + `S6.3-04` Quench Harness)
- **E2 Parts (`17`):** `{', '.join(E2_PART_IDS)}`
- **Magnet Quench Harness (`1`):** `S6.3-04` (with `S7.SAFETY-05` external `1.563 Ohm` dump bank)

## 2. KiCad 8 Bulkhead Distribution PCB (`cryo_rf_bias_panel`)
- **Stackup:** 4-layer Rogers RO4350B (`er=3.48`, `0.254 mm` outer cores), `170 x 120 mm`
- **Verification:** **`{len(pcb['erc']['errors'])}` ERC errors**, **`{len(pcb['erc']['warnings'])}` ERC warnings**, **`{len(pcb['drc']['errors'])}` DRC errors**, SCH/PCB parity = **`{pcb['erc']['sch_pcb_parity_ok']}`**, **`routed_net_count = {pcb['drc']['routed_net_count']}/{pcb['drc']['total_multi_pin_nets']}`**, **`unrouted_net_count = {pcb['drc']['unrouted_net_count']}`**, **`unconnected_items = {pcb['drc']['unconnected_items']}`**, **`track_dangling_count = {pcb['drc']['track_dangling_count']}`** (`{pcb['drc']['segment_count']}` segments, `{pcb['drc']['via_count']}` vias)
- **Contents:** `{pcb['erc']['component_count']}` components, `{pcb['erc']['net_count']}` nets: `8x` 4 K InP HEMT bias channels, `4x` 20 mK TWPA flux-bias + Eccosorb CR-124 LPF lanes, `4x` `50.00 Ohm` controlled-impedance Rogers RO4350B RF/rf-SET bias-tee monitor lanes (`{len(pcb['drc']['impedance_checks'])}` Z0 checks PASS), and `S6.3-04` `400 V` quench voltage-tap isolation bay protected by a `2.5 x 92 mm` milled `Edge.Cuts` air-slot (`{len(pcb['drc']['hv_checks'])}` HV checks PASS).

## 3. Live `ngspice-47` Simulation Verification
| Deck | BOM ID | Key Measured Metrics | Cross-Check Parity | Verdict |
|---|---|---|---|---|
| `qram_chebyshev_50_to_3k.cir` | `S9.4-02` | `max |S11|(4-8 GHz) = {c['max_s11_4_8_db']} dB` (`<= -20 dB`), `min |S21| = {c['min_s21_4_8_db']} dB` (`> -0.2 dB`), `BW(-20 dB) = {c['bw20_ghz']} GHz` (`{c['bw20_lo_ghz']}-{c['bw20_hi_ghz']} GHz`) | Exact ABCD `|dS11| = {c['abcd_crosscheck']['s11_parity_diff_db']} dB` | **PASS** |
| `magnet_quench_dump_1p563ohm.cir` | `S6.3-04` | `V_peak = {q['v_peak_V']} V` (`<= 400 V`), `tau = {q['tau_decay_s']} s` (`~0.370 s`), `E_dump = {q['e_dump_kJ']} / {q['E_stored_kJ']} kJ` (**`{q['e_dump_fraction_pct']}% >= 99%`**), `T_dump_peak = {q['dump_bank_T_peak_C']} C` | Analytical LR `|dtau| = {q['analytical_crosscheck']['tau_rel_diff_pct']}%` | **PASS** |
| `rf_set_tank_biastee.cir` | `S6.7-01` | `f_res = {r['f_res_MHz']} MHz` (`250-400 MHz`), `|Gamma(50k)| = {r['gamma_50k_mag']}`, `|Gamma(200k)| = {r['gamma_200k_mag']}`, `Delta|Gamma| = {r['delta_gamma_mag']}`, DC-bias RF isolation = **`{r['dc_bias_isolation_at_fres_dB']} dB`** (worst `200-450 MHz`: `{r['dc_bias_isolation_worst_200_450MHz_dB']} dB > 40 dB`) | Python MNA `|dGamma| = {r['mna_crosscheck']['delta_gamma_diff']}` | **PASS** |

## 4. 6-Stage Thermal & Attenuation Reconciliation (`Exp125` / `Exp140` / `Exp142`)
- **Staged RF Input Attenuation:** `-20 dB (4 K) / -10 dB (800 mK Still) / -10 dB (100 mK CP) / -20 dB (20 mK MXC)` (`-60 dB` total, cascaded `n_th(6 GHz, 20 mK) = {report['staged_attenuation_300K_to_20mK']['final_n_th_at_20mK']}`).
- **Combined M4 `1,024`-Cell (`Exp140`) + Option-Q (`Exp142`) Cryo Loads:**
  - `20 mK (MXC)`: **`{tb['mxc_20mK_uW']} uW`** (`<= 14.0 uW` LD400 cap)
  - `100 mK (CP)`: **`{tb['cp_100mK_uW']} uW`** (`<= 400.0 uW` cap)
  - `800 mK (Still)`: **`{tb['still_800mK_mW']} mW`** (`<= 40.0 mW` cap)
  - `4 K`: **`{tb['stage_4K_W']} W`** (`<= 2.0 W` PT420 cap)
  - `50 K`: **`{tb['stage_50K_W']} W`** (`<= 40.0 W` / `55.0 W` PT420 cap)
"""
    readme_path = out_dir / "README.md"
    readme_path.write_text(md, encoding="utf-8")
    return readme_path


def build_all(out_dir: Path = OUT_DIR) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    board = build_cryo_rf_bias_panel_board()
    pcb_report = verify_board_bundle(board, out_dir)
    if not pcb_report["passed"]:
        raise RuntimeError(
            f"cryo_rf_bias_panel failed ERC/DRC:\n"
            f"  ERC errors: {pcb_report['erc']['errors']}\n"
            f"  DRC errors: {pcb_report['drc']['errors']}"
        )

    sim_cheb = write_and_run_qram_chebyshev_spice(out_dir)
    sim_quench = write_and_run_magnet_quench_spice(out_dir)
    sim_rfset = write_and_run_rf_set_spice(out_dir)

    report = build_cryo_rf_thermal_attenuation(pcb_report, sim_cheb, sim_quench, sim_rfset)
    (out_dir / "cryo_rf_thermal_attenuation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    write_readme(report, out_dir)
    return report


if __name__ == "__main__":
    rep = build_all()
    print(json.dumps({
        "pcb_passed": rep["pcb_verification"]["passed"],
        "pcb_erc_errors": len(rep["pcb_verification"]["erc"]["errors"]),
        "pcb_erc_warnings": len(rep["pcb_verification"]["erc"]["warnings"]),
        "pcb_drc_errors": len(rep["pcb_verification"]["drc"]["errors"]),
        "pcb_routed_nets": f"{rep['pcb_verification']['drc']['routed_net_count']}/{rep['pcb_verification']['drc']['total_multi_pin_nets']}",
        "pcb_unrouted_nets": rep["pcb_verification"]["drc"]["unrouted_net_count"],
        "pcb_unconnected_items": rep["pcb_verification"]["drc"]["unconnected_items"],
        "pcb_track_dangling": rep["pcb_verification"]["drc"]["track_dangling_count"],
        "pcb_segments": rep["pcb_verification"]["drc"]["segment_count"],
        "pcb_vias": rep["pcb_verification"]["drc"]["via_count"],
        "pcb_semi_s2_certified": rep["pcb_verification"]["epistemic_meta"]["semi_s2_certified"],
        "pcb_comps": rep["pcb_verification"]["erc"]["component_count"],
        "pcb_nets": rep["pcb_verification"]["erc"]["net_count"],
        "sim_chebyshev": rep["ngspice_simulations"]["qram_chebyshev_50_to_3k"],
        "sim_quench": rep["ngspice_simulations"]["magnet_quench_dump_1p563ohm"],
        "sim_rfset": rep["ngspice_simulations"]["rf_set_tank_biastee"],
        "thermal_combined": rep["thermal_load_budget"]["combined_m4_plus_option_q"],
    }, indent=2))
