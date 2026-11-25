"""IBIC Cryo Front-End v3 — Physically Split 3-PCB KiCad 8 Kit & Real 100 K ngspice Verification.

Closes all 6 empirical defects identified in the baseline monolithic pre-layout
``src/board/detector_frontend.{py,net,cir}`` (BOM S3.1-01/02, S3.2-01..06, S3.3-03):
  1. Full KiCad 8 schematics (.kicad_sch) & multi-layer PCBs (.kicad_pcb) with
     real stackups, copper tracks, vias, zones, guard rings & air-slots (0 ERC, 0 DRC).
  2. Physically split 3-PCB architecture matching BOM_DETAILED.csv:
       (a) ibic_cold_csa_100k   (S3.2-01, 100 K in-vacuum Rogers RO4350B 4L CSA + 50 Ohm coax driver)
       (b) ibic_warm_shaper_300k (S3.2-02/06, S3.3-03, 300 K ex-vacuum FR408HR 4L shaper + DAC + CMP + ADC tap + LT3045/LT3094 LDOs)
       (c) ibic_hv_bias_guard   (S3.2-03, S3.1-01/02, 3-stage RC 0-100 V HV bias filter + unity-gain driven guard buffer + milled air-slot)
  3. Complete analog subsystems: 3-stage HV filter + driven guard buffer, LT3045/LT3094
     +/-12 V / +/-5 V -> +/-2.5 V / +3.3 V / +/-5 V LDO tree, and buffered 50 MS/s FMC ADC tap.
  4. Native ngspice-47 deck (zero PSpice VALUE={}/PARAMS: syntax) with .temp -173.15 (100 K)
     on cold stage and per-resistor temp=26.85 (300 K) on warm ex-vacuum stage.
  5. Calibrated diode-shot/flicker & thermal noise macromodels for LTC6268 (2.0 nV/rtHz,
     fc=2 kHz, 0.5 fA/rtHz) and ADA4817-1 (4.0 nV/rtHz), reproducing Exp127 ENC/t_peak/V_peak.
  6. Independent Python MNA cross-check against real ngspice AC transfer & HV filter attenuation.

Epistemic status: M0/M1 DESIGN_ONLY; no_lab_measurement=true; no_physical_fab=true.
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
    connect_guard_ring,
    make_manhattan_trace,
    run_ngspice,
    solve_microstrip_width_mm,
    verify_board_bundle,
)

OUT_DIR = Path(__file__).resolve().parent
CHANNELS = 8
Q_E = 1.602176634e-19
K_B = 1.380649e-23
# Exp127 locked 5 keV 31P+ Lindhard @ 100 K (w_Si = 3.72 eV): 341.7145 e- = 0.0547487 fC
LINDHARD_5KEV_100K_E = 341.7145113182292
LINDHARD_5KEV_100K_C = LINDHARD_5KEV_100K_E * Q_E


def _pad_xy(comp: ComponentSpec, pin_num: str) -> tuple[float, float]:
    rad = math.radians(comp.rotation_deg)
    c, s = math.cos(rad), math.sin(rad)
    for p in comp.pins:
        if p.number == str(pin_num):
            return (round(comp.x_mm + p.dx_mm * c + p.dy_mm * s, 4), round(comp.y_mm - p.dx_mm * s + p.dy_mm * c, 4))
    raise KeyError(f"Pin {pin_num} not found on {comp.ref}")


def _soic8_opamp_pins(include_shdn: bool = False) -> tuple[PinSpec, ...]:
    names = {
        "1": "NC1",
        "2": "IN-",
        "3": "IN+",
        "4": "V-",
        "5": "NC5",
        "6": "OUT",
        "7": "V+",
        "8": "SHDN_N" if include_shdn else "NC8",
    }
    types = {
        "1": "no_connect",
        "2": "input",
        "3": "input",
        "4": "power_in",
        "5": "no_connect",
        "6": "output",
        "7": "power_in",
        "8": "input" if include_shdn else "no_connect",
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


# ---------------------------------------------------------------------------
# Board (a): ibic_cold_csa_100k — 100 K In-Vacuum Cold-Island 8-Ch CSA PCB
# ---------------------------------------------------------------------------

def build_cold_csa_board() -> BoardSpec:
    """Build S3.2-01 100 K in-vacuum 4-layer Rogers RO4350B 8-ch LTC6268 CSA PCB."""
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

    def add_c(c: ComponentSpec) -> ComponentSpec:
        comps.append(c)
        return c

    def conn(net: str, ref: str, pin: str | int) -> None:
        nets_dict[net].append((ref, str(pin)))

    # Utility & Interface Connectors (bottom strip y = 96.0 mm)
    jhv = add_c(ComponentSpec(
        "JHV_IN", "SHV_100V_BIAS_IN", "Connector_Coaxial:SHV_Amphenol_HV",
        10.0, 96.5, pins=auto_footprint_pads("SHV", ("1", "2"), {"1": "HV", "2": "GND"}),
        bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}",
    ))
    jgrd = add_c(ComponentSpec(
        "JGUARD_IN", "SMA_DRIVEN_GUARD_IN", "Connector_Coaxial:SMA_EdgeMount",
        34.0, 96.5, pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "GUARD", "2": "GND"}),
        bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}",
    ))
    jpwr = add_c(ComponentSpec(
        "JPWR_COLD", "HDR_4P_VCCA_VSSA_AGND", "Connector_PinHeader:HDR_1x4_2.54mm",
        62.0, 96.5, rotation_deg=90.0,
        pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                 {"1": "VCCA", "2": "VSSA", "3": "AGND1", "4": "AGND2"}),
        bom_id="S3.2-06", epistemic_tag="{Pasif-COTS}",
    ))
    cbulk_p = add_c(ComponentSpec(
        "CBULK_P", "10uF_10V_C0G", "Capacitor_SMD:C_0805_2012Metric",
        78.0, 96.5, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
    ))
    cbulk_n = add_c(ComponentSpec(
        "CBULK_N", "10uF_10V_C0G", "Capacitor_SMD:C_0805_2012Metric",
        86.0, 96.5, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
    ))
    # Cold-board local guard-ring reference tie resistor (100 Ohm dampening to JGUARD_IN)
    rgrd_in = add_c(ComponentSpec(
        "RGRD_IN", "49.9R_1pct", "Resistor_SMD:R_0603_1608Metric",
        43.0, 96.5, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.1-02", epistemic_tag="{Pasif-COTS}",
    ))
    cgrd_in = add_c(ComponentSpec(
        "CGRD_IN", "100nF_C0G", "Capacitor_SMD:C_0603_1608Metric",
        50.0, 96.5, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.1-02", epistemic_tag="{Pasif-COTS}",
    ))

    conn("HV_BIAS_COLD", "JHV_IN", 1)
    conn("AGND", "JHV_IN", 2)
    conn("GUARD_IN", "JGUARD_IN", 1)
    conn("AGND", "JGUARD_IN", 2)
    conn("GUARD_IN", "RGRD_IN", 1)
    conn("GUARD_DRV", "RGRD_IN", 2)
    conn("GUARD_DRV", "CGRD_IN", 1)
    conn("AGND", "CGRD_IN", 2)
    conn("VCCA", "JPWR_COLD", 1)
    conn("VSSA", "JPWR_COLD", 2)
    conn("AGND", "JPWR_COLD", 3)
    conn("AGND", "JPWR_COLD", 4)
    conn("VCCA", "CBULK_P", 1); conn("AGND", "CBULK_P", 2)
    conn("VSSA", "CBULK_N", 1); conn("AGND", "CBULK_N", 2)

    # Custom pixel diode footprint: wide 2.50 mm gap between pin 2 (HV DET_BIAS) and pin 1 (CSA_SUM) + guard pad 3
    diode_pins = (
        PinSpec("2", "CATH_HV", "passive", -1.65, 0.0, 0.70, 0.90),
        PinSpec("1", "ANODE_SUM", "passive", 1.65, 0.0, 0.70, 0.90),
        PinSpec("3", "GUARD", "passive", 0.0, 2.20, 0.70, 0.60),
    )

    for ch in range(CHANNELS):
        p = f"CH{ch}"
        yc = round(12.0 + ch * 10.5, 3)

        # Per-channel HV bias filter (1206 -> 2.0 mm pad gap >= 1.0 mm IPC-2221B 100 V creepage)
        rbias = add_c(ComponentSpec(
            f"RBIAS{ch}", "10M_100V_THICKFILM", "Resistor_SMD:R_1206_3216Metric",
            14.5, yc, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
        ))
        cbias = add_c(ComponentSpec(
            f"CBIAS{ch}", "10nF_100V_C0G", "Capacitor_SMD:C_1206_3216Metric",
            23.5, yc, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
        ))
        # Pixel diode + guard ring contact (S3.1-01/02)
        diode = add_c(ComponentSpec(
            f"D{ch}", "IBIC_PIXEL_DIODE_C0p5", "Custom:IBIC_PIXEL_FLIPCHIP_3P",
            33.5, yc, pins=diode_pins, bom_id="S3.1-01", epistemic_tag="{Ozel-Uretim}",
        ))
        # Feedback Cf=0.25 pF & Rf=1 GOhm tightly adjacent to LTC6268 IN-
        cf = add_c(ComponentSpec(
            f"CF{ch}", "0.25pF_C0G_NP0", "Capacitor_SMD:C_0402_1005Metric",
            44.0, yc - 2.0, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
        ))
        rf = add_c(ComponentSpec(
            f"RF{ch}", "1G_THICKFILM_CRYO", "Resistor_SMD:R_0402_1005Metric",
            44.0, yc + 2.0, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
        ))
        # LTC6268 CSA (100 K cold island)
        ua = add_c(ComponentSpec(
            f"U{ch}A", "LTC6268_CSA_FET", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            56.5, yc, pins=_soic8_opamp_pins(include_shdn=True),
            mpn="LTC6268IS8", bom_id="S3.2-01", epistemic_tag="{Aday-COTS}",
        ))
        cd_ap = add_c(ComponentSpec(
            f"CD{ch}AP", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
            66.5, yc - 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
        ))
        cd_an = add_c(ComponentSpec(
            f"CD{ch}AN", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
            66.5, yc + 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
        ))
        # 50 Ohm Coax Line Driver (LTC6268, G = +2.00 driving 49.9 Ohm series -> 50 Ohm coax)
        ud = add_c(ComponentSpec(
            f"U{ch}D", "LTC6268_COAX_DRV_G2", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            77.5, yc, pins=_soic8_opamp_pins(include_shdn=True),
            mpn="LTC6268IS8", bom_id="S3.2-01", epistemic_tag="{Aday-COTS}",
        ))
        rdrv1 = add_c(ComponentSpec(
            f"RDRV1{ch}", "499R_0.1pct", "Resistor_SMD:R_0402_1005Metric",
            87.5, yc - 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
        ))
        rdrv2 = add_c(ComponentSpec(
            f"RDRV2{ch}", "499R_0.1pct", "Resistor_SMD:R_0402_1005Metric",
            87.5, yc + 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
        ))
        cd_dp = add_c(ComponentSpec(
            f"CD{ch}DP", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
            94.0, yc - 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
        ))
        cd_dn = add_c(ComponentSpec(
            f"CD{ch}DN", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
            94.0, yc + 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
        ))
        rtx = add_c(ComponentSpec(
            f"RTX{ch}", "49.9R_1pct", "Resistor_SMD:R_0402_1005Metric",
            102.0, yc, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-01", epistemic_tag="{Pasif-COTS}",
        ))
        jcoax = add_c(ComponentSpec(
            f"JCOAX{ch}", "SMP_50R_COAX_CF63", "Connector_Coaxial:SMA_EdgeMount",
            118.0, yc, rotation_deg=90.0, edge_mount=True,
            pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "SIG", "2": "GND"}),
            bom_id="S3.2-05", epistemic_tag="{Pasif-COTS}",
        ))

        # Net connections
        conn("HV_BIAS_COLD", rbias.ref, 1)
        conn(f"HV_BIAS_{p}", rbias.ref, 2)
        conn(f"HV_BIAS_{p}", cbias.ref, 1)
        conn("AGND", cbias.ref, 2)
        conn(f"HV_BIAS_{p}", diode.ref, 2)
        conn("GUARD_DRV", diode.ref, 3)

        # Ultra-low-C summing node CH{ch}.CSA_SUM
        conn(f"{p}.CSA_SUM", diode.ref, 1)
        conn(f"{p}.CSA_SUM", cf.ref, 2)
        conn(f"{p}.CSA_SUM", rf.ref, 2)
        conn(f"{p}.CSA_SUM", ua.ref, 2)
        conn("AGND", ua.ref, 3)

        # CSA output -> feedback + coax driver IN+
        conn(f"{p}.CSA_OUT", ua.ref, 6)
        conn(f"{p}.CSA_OUT", cf.ref, 1)
        conn(f"{p}.CSA_OUT", rf.ref, 1)
        conn(f"{p}.CSA_OUT", ud.ref, 3)

        # Coax line driver G = +2.00 (RDRV1 = RDRV2 = 499 Ohm) -> RTX (49.9 Ohm) -> 50 Ohm coax
        conn(f"{p}.DRV_FB", ud.ref, 2)
        conn(f"{p}.DRV_FB", rdrv1.ref, 1)
        conn(f"{p}.DRV_FB", rdrv2.ref, 1)
        conn("AGND", rdrv1.ref, 2)
        conn(f"{p}.DRV_OUT", ud.ref, 6)
        conn(f"{p}.DRV_OUT", rdrv2.ref, 2)
        conn(f"{p}.DRV_OUT", rtx.ref, 1)
        conn(f"{p}.COAX_TX", rtx.ref, 2)
        conn(f"{p}.COAX_TX", jcoax.ref, 1)
        conn("AGND", jcoax.ref, 2)

        # Power & decoupling
        conn("VCCA", ua.ref, 7); conn("VCCA", ua.ref, 8); conn("VSSA", ua.ref, 4)
        conn("VCCA", cd_ap.ref, 1); conn("AGND", cd_ap.ref, 2)
        conn("VSSA", cd_an.ref, 1); conn("AGND", cd_an.ref, 2)
        conn("VCCA", ud.ref, 7); conn("VCCA", ud.ref, 8); conn("VSSA", ud.ref, 4)
        conn("VCCA", cd_dp.ref, 1); conn("AGND", cd_dp.ref, 2)
        conn("VSSA", cd_dn.ref, 1); conn("AGND", cd_dn.ref, 2)

        # Copper traces:
        # 1) Short high-Z CSA_SUM trace (total length < 12 mm, width 0.15 mm)
        p_d1 = _pad_xy(diode, "1")
        p_cf2 = _pad_xy(cf, "2")
        p_rf2 = _pad_xy(rf, "2")
        p_u2 = _pad_xy(ua, "2")
        traces.append(make_manhattan_trace(f"{p}.CSA_SUM", "F.Cu", p_d1, (44.48, yc), width_mm=0.15))
        traces.append(make_manhattan_trace(f"{p}.CSA_SUM", "F.Cu", p_cf2, p_rf2, width_mm=0.15))
        traces.append(make_manhattan_trace(f"{p}.CSA_SUM", "F.Cu", (44.48, yc), p_u2, width_mm=0.15, mid_x=49.5))

        # 2) Physically closed 3D driven Guard Ring cage enclosing CSA_SUM (S3.2-01 / S3.1-02)
        #    Corner vias at y = yc +/- 3.6 sit strictly outside In1/In2 keepout (yc +/- 3.0)
        gr_traces, gr_vias = connect_guard_ring(
            "GUARD_DRV", "F.Cu", 36.8, round(yc - 3.6, 3), 52.0, round(yc + 3.6, 3),
            width_mm=0.25, via_layer="B.Cu", via_diameter_mm=0.48, via_drill_mm=0.24, top_only_rails=True,
        )
        traces.extend(gr_traces)
        vias.extend(gr_vias)
        # 3) Reference-plane copper keepout directly under CSA_SUM to enforce < 0.15 pF stray C!
        keepouts.append(KeepoutSpec(
            name=f"KO_CSASUM_{p}", kind="copper_keepout", layers=("In1.Cu", "In2.Cu"),
            x_mm=34.5, y_mm=round(yc - 3.0, 3), width_mm=18.0, height_mm=6.0,
        ))

        # 4) Controlled-impedance 50 Ohm microstrip from RTX.2 to JCOAX.1 on F.Cu
        p_rtx2 = _pad_xy(rtx, "2")
        p_j1 = _pad_xy(jcoax, "1")
        traces.append(make_manhattan_trace(f"{p}.COAX_TX", "F.Cu", p_rtx2, p_j1, width_mm=w50))

        # 5) Stitching AGND vias along coax driver & output return (tied to In1.Cu AGND plane)
        vias.append(ViaSpec("AGND", 107.0, round(yc - 2.4, 3), diameter_mm=0.60, drill_mm=0.30))
        vias.append(ViaSpec("AGND", 107.0, round(yc + 2.4, 3), diameter_mm=0.60, drill_mm=0.30))

    # Build NetSpec list with power flags, HV voltage tags, and 50 Ohm controlled impedance targets
    nets: list[NetSpec] = []
    for nname, nodes in sorted(nets_dict.items()):
        is_pwr = nname in ("VCCA", "VSSA", "AGND", "HV_BIAS_COLD")
        v_work = 100.0 if nname.startswith("HV_BIAS") else (2.5 if nname in ("VCCA", "VSSA") else 0.0)
        z0 = 50.0 if nname.endswith(".COAX_TX") else None
        nclass = "HV_100V" if v_work >= 50.0 else ("RF_50" if z0 else ("Power" if is_pwr else "Default"))
        nets.append(NetSpec(
            name=nname,
            nodes=tuple(nodes),
            net_class=nclass,
            is_power=is_pwr,
            has_pwr_flag=is_pwr,
            voltage_v=v_work,
            target_z0_ohm=z0,
        ))

    # Ground/power zones (leaving left x < 31.0 mm clear of AGND/power planes on F.Cu; In1/In2 start at x=28 mm away from HV trunk)
    zones = (
        ZoneSpec("AGND", "In1.Cu", ((28.0, 2.0), (123.0, 2.0), (123.0, 102.0), (28.0, 102.0))),
        ZoneSpec("VCCA", "In2.Cu", ((54.0, 2.0), (105.0, 2.0), (105.0, 52.0), (54.0, 52.0))),
        ZoneSpec("VSSA", "In2.Cu", ((54.0, 53.0), (105.0, 53.0), (105.0, 102.0), (54.0, 102.0))),
    )

    creepage_rules = (
        CreepageRule("HV_BIAS*", working_voltage_v=100.0, min_clearance_mm=0.60, min_creepage_mm=1.00),
    )

    spec = BoardSpec(
        name="ibic_cold_csa_100k",
        title="IBIC v3 Cold-Island 8-Ch 100 K LTC6268 CSA (4L Rogers RO4350B)",
        rev="v3.0",
        bom_ids=("S3.2-01", "S3.1-01", "S3.1-02", "S3.2-04", "S3.2-05"),
        width_mm=125.0,
        height_mm=105.0,
        stackup=stackup,
        components=tuple(comps),
        nets=tuple(nets),
        traces=tuple(traces),
        vias=tuple(vias),
        zones=zones,
        keepouts=tuple(keepouts),
        creepage_rules=creepage_rules,
        rules=DesignRules(min_trace_width_mm=0.127, min_clearance_mm=0.127, min_edge_clearance_mm=0.50),
        epistemic_meta={**DEFAULT_EPISTEMIC_META, "operating_temp_K": 100.0, "vacuum_grade": "UHV_1e-9_mbar"},
    )
    return auto_route_board(spec, grid_mm=0.50, preserve_existing=True)


# ---------------------------------------------------------------------------
# Board (b): ibic_warm_shaper_300k — 300 K Ex-Vacuum Shaper + DAC + CMP + ADC Tap + LDO Tree
# ---------------------------------------------------------------------------

def build_warm_shaper_board() -> BoardSpec:
    """Build S3.2-02 / S3.2-06 / S3.3-03 300 K 4-layer FR408HR 8-ch warm shaper & LDO PCB."""
    stackup = (
        StackupLayer("F.Cu", "signal", 0.035, material="Copper"),
        StackupLayer("dielectric 1", "prepreg", 0.254, epsilon_r=3.66, loss_tangent=0.009, material="Isola FR408HR"),
        StackupLayer("In1.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 2", "core", 0.800, epsilon_r=3.66, loss_tangent=0.009, material="Isola FR408HR"),
        StackupLayer("In2.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 3", "prepreg", 0.254, epsilon_r=3.66, loss_tangent=0.009, material="Isola FR408HR"),
        StackupLayer("B.Cu", "signal", 0.035, material="Copper"),
    )
    w50 = solve_microstrip_width_mm(50.0, h_mm=0.254, t_mm=0.035, er=3.66)  # 0.5257 mm -> 50.00 Ohm

    comps: list[ComponentSpec] = []
    nets_dict: dict[str, list[tuple[str, str]]] = defaultdict(list)
    traces: list[TraceSpec] = []
    vias: list[ViaSpec] = []

    def add_c(c: ComponentSpec) -> ComponentSpec:
        comps.append(c)
        return c

    def conn(net: str, ref: str, pin: str | int) -> None:
        nets_dict[net].append((ref, str(pin)))

    # Shared connectors, star ground, SPI DAC8568, FMC PHA ADC tap header, FPGA header
    jpwr_raw = add_c(ComponentSpec(
        "JPWR_RAW", "HDR_6P_LINEAR_PSU_IN", "Connector_PinHeader:HDR_1x6_2.54mm",
        16.0, 123.0, rotation_deg=90.0,
        pins=auto_footprint_pads("HDR_1x6_2.54mm", ("1", "2", "3", "4", "5", "6"),
                                 {"1": "VIN_P12", "2": "VIN_N12", "3": "VIN_P5", "4": "VIN_N5", "5": "AGND1", "6": "AGND2"}),
        bom_id="S3.2-06", epistemic_tag="{Pasif-COTS}",
    ))
    jpwr_cold_out = add_c(ComponentSpec(
        "JPWR_COLD_OUT", "HDR_6P_CLEAN_REG_OUT", "Connector_PinHeader:HDR_1x6_2.54mm",
        164.0, 123.0, rotation_deg=90.0,
        pins=auto_footprint_pads("HDR_1x6_2.54mm", ("1", "2", "3", "4", "5", "6"),
                                 {"1": "VCCA", "2": "VSSA", "3": "V_P5A", "4": "V_N5A", "5": "AGND1", "6": "AGND2"}),
        bom_id="S3.2-06", epistemic_tag="{Pasif-COTS}",
    ))
    r_star = add_c(ComponentSpec(
        "R_STAR", "0R_STAR_GND", "Resistor_SMD:R_0603_1608Metric",
        128.0, 118.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
    ))
    udac = add_c(ComponentSpec(
        "UDAC", "DAC8568_16B_8CH_SPI", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
        142.0, 118.0,
        pins=auto_footprint_pads("TSSOP-16", [str(i) for i in range(1, 17)],
                                 {"1": "LDAC_N", "2": "SYNC_N", "3": "AVDD", "8": "VREF", "9": "CLR_N",
                                  "14": "GND", "15": "DIN", "16": "SCLK"}),
        mpn="DAC8568ICPWR", bom_id="S3.2-02", epistemic_tag="{Aday-COTS}",
    ))
    cd_dac = add_c(ComponentSpec(
        "CD_DAC", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
        151.0, 115.0, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
    ))
    cref_dac = add_c(ComponentSpec(
        "CREF_DAC", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
        151.0, 121.0, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
    ))
    jadc = add_c(ComponentSpec(
        "JADC", "FMC_PHA_ADC_TAP_16P", "Connector_PinHeader:HDR_2x8_2.54mm",
        177.0, 32.0,
        pins=auto_footprint_pads("HDR_2x8_2.54mm", [str(i) for i in range(1, 17)]),
        bom_id="S3.3-03", epistemic_tag="{Pasif-COTS}",
    ))
    jfpga = add_c(ComponentSpec(
        "JFPGA", "FPGA_COUNT_SPI_24P", "Connector_PinHeader:HDR_2x12_2.54mm",
        177.0, 82.0,
        pins=auto_footprint_pads("HDR_2x12_2.54mm", [str(i) for i in range(1, 25)]),
        bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}",
    ))

    # Ultra-low-noise LT3045 / LT3094 LDO Power Tree (S3.2-06: +/-12V & +/-5V -> +/-2.5V, +3.3V, +/-5V)
    ldo_specs = [
        ("ULDO_P2V5", "LT3045_P2V5_LDO", "VIN_P5", "VCCA", "AGND", "24.9k_0.1pct", 36.0),
        ("ULDO_N2V5", "LT3094_N2V5_LDO", "VIN_N5", "VSSA", "AGND", "24.9k_0.1pct", 56.0),
        ("ULDO_D3V3", "LT3045_D3V3_LDO", "VIN_P5", "VCCD", "DGND", "33.2k_0.1pct", 76.0),
        ("ULDO_P5A",  "LT3045_P5V_LDO",  "VIN_P12", "V_P5A", "AGND", "49.9k_0.1pct", 96.0),
        ("ULDO_N5A",  "LT3094_N5V_LDO",  "VIN_N12", "V_N5A", "AGND", "49.9k_0.1pct", 114.0),
    ]
    for lref, lval, vin, vout, gnd, rset_val, lx in ldo_specs:
        uldo = add_c(ComponentSpec(
            lref, lval, "Package_SO:MSOP-10_3x3mm_P0.5mm",
            lx, 118.0, pins=_ldo_msop10_pins(),
            mpn="LT3045EMSE" if "LT3045" in lval else "LT3094EMSE",
            bom_id="S3.2-06", epistemic_tag="{Aday-COTS}",
        ))
        cin = add_c(ComponentSpec(
            f"CIN_{lref}", "10uF_25V_X7R", "Capacitor_SMD:C_0805_2012Metric",
            lx - 6.0, 114.5, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S3.2-06", epistemic_tag="{Pasif-COTS}",
        ))
        cout = add_c(ComponentSpec(
            f"COUT_{lref}", "10uF_10V_X7R", "Capacitor_SMD:C_0805_2012Metric",
            lx + 6.0, 114.5, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S3.2-06", epistemic_tag="{Pasif-COTS}",
        ))
        rset = add_c(ComponentSpec(
            f"RSET_{lref}", rset_val, "Resistor_SMD:R_0402_1005Metric",
            lx - 5.5, 123.5, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-06", epistemic_tag="{Pasif-COTS}",
        ))
        cset = add_c(ComponentSpec(
            f"CSET_{lref}", "4.7uF_10V_X7R", "Capacitor_SMD:C_0603_1608Metric",
            lx + 5.5, 123.5, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-06", epistemic_tag="{Pasif-COTS}",
        ))
        conn(vin, uldo.ref, 1); conn(vin, uldo.ref, 2); conn(vin, uldo.ref, 3)
        conn(gnd, uldo.ref, 6)
        conn(f"{lref}_SET", uldo.ref, 7)
        conn(f"{lref}_SET", rset.ref, 1); conn(gnd, rset.ref, 2)
        conn(f"{lref}_SET", cset.ref, 1); conn(gnd, cset.ref, 2)
        conn(vout, uldo.ref, 8); conn(vout, uldo.ref, 9); conn(vout, uldo.ref, 10)
        conn(vin, cin.ref, 1); conn(gnd, cin.ref, 2)
        conn(vout, cout.ref, 1); conn(gnd, cout.ref, 2)

    # Power headers & star ground
    conn("VIN_P12", jpwr_raw.ref, 1); conn("VIN_N12", jpwr_raw.ref, 2)
    conn("VIN_P5", jpwr_raw.ref, 3); conn("VIN_N5", jpwr_raw.ref, 4)
    conn("AGND", jpwr_raw.ref, 5); conn("AGND", jpwr_raw.ref, 6)

    conn("VCCA", jpwr_cold_out.ref, 1); conn("VSSA", jpwr_cold_out.ref, 2)
    conn("V_P5A", jpwr_cold_out.ref, 3); conn("V_N5A", jpwr_cold_out.ref, 4)
    conn("AGND", jpwr_cold_out.ref, 5); conn("AGND", jpwr_cold_out.ref, 6)

    conn("AGND", r_star.ref, 1); conn("DGND", r_star.ref, 2)

    # DAC8568 TSSOP-16 wiring
    conn("DGND", udac.ref, 1)
    conn("SPI_CS_N", udac.ref, 2)
    conn("VCCD", udac.ref, 3)
    conn("DAC_VREF", udac.ref, 8)
    conn("VCCD", udac.ref, 9)
    conn("DGND", udac.ref, 14)
    conn("SPI_MOSI", udac.ref, 15)
    conn("SPI_SCLK", udac.ref, 16)
    conn("VCCD", cd_dac.ref, 1); conn("DGND", cd_dac.ref, 2)
    conn("DAC_VREF", cref_dac.ref, 1); conn("AGND", cref_dac.ref, 2)

    # JFPGA SPI + power + returns
    conn("SPI_SCLK", jfpga.ref, 17); conn("SPI_MOSI", jfpga.ref, 18)
    conn("SPI_CS_N", jfpga.ref, 19); conn("VCCD", jfpga.ref, 20)
    for gpin in (9, 10, 11, 12, 13, 14, 15, 16, 21, 22, 23, 24):
        conn("DGND", jfpga.ref, gpin)

    # JADC AGND return pins (even pins 2,4,...,16)
    for gpin in (2, 4, 6, 8, 10, 12, 14, 16):
        conn("AGND", jadc.ref, gpin)

    dac_out_pins = (4, 5, 6, 7, 10, 11, 12, 13)

    for ch in range(CHANNELS):
        p = f"CH{ch}"
        yc = round(12.5 + ch * 11.5, 3)

        jin = add_c(ComponentSpec(
            f"JIN{ch}", "SMA_50R_FROM_CF63", "Connector_Coaxial:SMA_EdgeMount",
            6.0, yc, rotation_deg=90.0, edge_mount=True,
            pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "SIG", "2": "GND"}),
            bom_id="S3.2-05", epistemic_tag="{Pasif-COTS}",
        ))
        rrx = add_c(ComponentSpec(
            f"RRX{ch}", "49.9R_1pct", "Resistor_SMD:R_0402_1005Metric",
            17.0, yc, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        cs = add_c(ComponentSpec(
            f"CS{ch}", "600pF_C0G_1pct", "Capacitor_SMD:C_0603_1608Metric",
            25.0, yc, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        rs1 = add_c(ComponentSpec(
            f"RS1{ch}", "2.00k_0.1pct", "Resistor_SMD:R_0402_1005Metric",
            33.0, yc, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        ub = add_c(ComponentSpec(
            f"U{ch}B", "ADA4817-1_SHAPER", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            44.5, yc, pins=_soic8_opamp_pins(include_shdn=False),
            mpn="ADA4817-1ARDZ", bom_id="S3.2-02", epistemic_tag="{Aday-COTS}",
        ))
        rg1 = add_c(ComponentSpec(
            f"RG1{ch}", "100R_0.1pct", "Resistor_SMD:R_0402_1005Metric",
            54.5, yc - 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        rg2 = add_c(ComponentSpec(
            f"RG2{ch}", "13.5k_0.1pct", "Resistor_SMD:R_0402_1005Metric",
            54.5, yc + 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        cd_bp = add_c(ComponentSpec(
            f"CD{ch}BP", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
            61.5, yc - 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        cd_bn = add_c(ComponentSpec(
            f"CD{ch}BN", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
            61.5, yc + 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        rs2 = add_c(ComponentSpec(
            f"RS2{ch}", "2.00k_0.1pct", "Resistor_SMD:R_0402_1005Metric",
            69.0, yc, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        cp = add_c(ComponentSpec(
            f"CP{ch}", "600pF_C0G_1pct", "Capacitor_SMD:C_0603_1608Metric",
            77.0, yc, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        # Buffered Analog SHP_OUT Tap to 50 MS/s 12-bit FMC PHA ADC (S3.3-03)
        ue = add_c(ComponentSpec(
            f"U{ch}E", "ADA4817-1_ADC_BUF", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            88.5, yc, pins=_soic8_opamp_pins(include_shdn=False),
            mpn="ADA4817-1ARDZ", bom_id="S3.3-03", epistemic_tag="{Aday-COTS}",
        ))
        cd_ep = add_c(ComponentSpec(
            f"CD{ch}EP", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
            98.0, yc - 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.3-03", epistemic_tag="{Pasif-COTS}",
        ))
        cd_en = add_c(ComponentSpec(
            f"CD{ch}EN", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
            98.0, yc + 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.3-03", epistemic_tag="{Pasif-COTS}",
        ))
        raa = add_c(ComponentSpec(
            f"RAA{ch}", "49.9R_1pct", "Resistor_SMD:R_0402_1005Metric",
            105.0, yc, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.3-03", epistemic_tag="{Pasif-COTS}",
        ))
        caa = add_c(ComponentSpec(
            f"CAA{ch}", "120pF_C0G_1pct", "Capacitor_SMD:C_0402_1005Metric",
            111.5, yc, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.3-03", epistemic_tag="{Pasif-COTS}",
        ))
        # Per-channel DAC threshold RC filter + TLV3501 hysteresis comparator
        rdac = add_c(ComponentSpec(
            f"RDAC{ch}", "1.00k_1pct", "Resistor_SMD:R_0402_1005Metric",
            119.5, yc - 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        cdac = add_c(ComponentSpec(
            f"CDAC{ch}", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
            119.5, yc + 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        rhys1 = add_c(ComponentSpec(
            f"RHYS1{ch}", "1.00k_1pct", "Resistor_SMD:R_0402_1005Metric",
            127.5, yc - 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        rhys2 = add_c(ComponentSpec(
            f"RHYS2{ch}", "1.00M_1pct", "Resistor_SMD:R_0402_1005Metric",
            127.5, yc + 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        uc = add_c(ComponentSpec(
            f"U{ch}C", "TLV3501_CMP_4p5NS", "Package_TO_SOT_SMD:SOT-23-6",
            138.0, yc,
            pins=auto_footprint_pads("SOT-23-6", ("1", "2", "3", "4", "5", "6"),
                                     {"1": "OUT", "2": "GND", "3": "IN+", "4": "IN-", "5": "SHDN", "6": "VCC"},
                                     {"1": "output", "2": "power_in", "3": "input", "4": "input", "5": "input", "6": "power_in"}),
            mpn="TLV3501AIDBVR", bom_id="S3.2-02", epistemic_tag="{Aday-COTS}",
        ))
        cd_c = add_c(ComponentSpec(
            f"CD{ch}C", "100nF_C0G", "Capacitor_SMD:C_0402_1005Metric",
            146.5, yc + 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))
        rterm = add_c(ComponentSpec(
            f"RTERM{ch}", "49.9R_1pct", "Resistor_SMD:R_0402_1005Metric",
            154.0, yc, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.2-02", epistemic_tag="{Pasif-COTS}",
        ))

        # Netlist wiring
        conn(f"{p}.COAX_IN", jin.ref, 1); conn("AGND", jin.ref, 2)
        conn(f"{p}.COAX_IN", rrx.ref, 1); conn("AGND", rrx.ref, 2)
        conn(f"{p}.COAX_IN", cs.ref, 1)

        conn(f"{p}.CR_OUT", cs.ref, 2)
        conn(f"{p}.CR_OUT", rs1.ref, 1); conn("AGND", rs1.ref, 2)
        conn(f"{p}.CR_OUT", ub.ref, 3)

        conn(f"{p}.SHP_FB", ub.ref, 2)
        conn(f"{p}.SHP_FB", rg1.ref, 1); conn("AGND", rg1.ref, 2)
        conn(f"{p}.SHP_FB", rg2.ref, 1)
        conn(f"{p}.SHP_GAIN", ub.ref, 6)
        conn(f"{p}.SHP_GAIN", rg2.ref, 2)
        conn(f"{p}.SHP_GAIN", rs2.ref, 1)

        conn(f"{p}.SHP_OUT", rs2.ref, 2)
        conn(f"{p}.SHP_OUT", cp.ref, 1); conn("AGND", cp.ref, 2)
        conn(f"{p}.SHP_OUT", ue.ref, 3)      # Unity-gain buffer isolates RS2/CP from ADC & comparator hysteresis

        # Unity-gain buffered analog SHP_BUF drives BOTH anti-alias FMC ADC tap AND comparator RHYS1!
        conn(f"{p}.SHP_BUF", ue.ref, 6)
        conn(f"{p}.SHP_BUF", ue.ref, 2)
        conn(f"{p}.SHP_BUF", raa.ref, 1)
        conn(f"{p}.SHP_BUF", rhys1.ref, 1)
        conn(f"{p}.SHP_ADC", raa.ref, 2)
        conn(f"{p}.SHP_ADC", caa.ref, 1); conn("AGND", caa.ref, 2)
        conn(f"{p}.SHP_ADC", jadc.ref, 1 + 2 * ch)

        # Threshold DAC filter & TLV3501 comparator
        conn(f"{p}.THRESH_RAW", udac.ref, dac_out_pins[ch])
        conn(f"{p}.THRESH_RAW", rdac.ref, 1)
        conn(f"{p}.THRESH", rdac.ref, 2)
        conn(f"{p}.THRESH", cdac.ref, 1); conn("AGND", cdac.ref, 2)
        conn(f"{p}.THRESH", uc.ref, 4)

        conn(f"{p}.CMP_INP", rhys1.ref, 2)
        conn(f"{p}.CMP_INP", rhys2.ref, 1)
        conn(f"{p}.CMP_INP", uc.ref, 3)
        conn(f"{p}.CMP_OUT", uc.ref, 1)
        conn(f"{p}.CMP_OUT", rhys2.ref, 2)
        conn(f"{p}.CMP_OUT", rterm.ref, 1)
        conn(f"{p}.COUNT_HIT", rterm.ref, 2)
        conn(f"{p}.COUNT_HIT", jfpga.ref, 1 + ch)

        # Power & decoupling
        conn("VCCA", ub.ref, 7); conn("VSSA", ub.ref, 4)
        conn("VCCA", cd_bp.ref, 1); conn("AGND", cd_bp.ref, 2)
        conn("VSSA", cd_bn.ref, 1); conn("AGND", cd_bn.ref, 2)
        conn("VCCA", ue.ref, 7); conn("VSSA", ue.ref, 4)
        conn("VCCA", cd_ep.ref, 1); conn("AGND", cd_ep.ref, 2)
        conn("VSSA", cd_en.ref, 1); conn("AGND", cd_en.ref, 2)
        conn("VCCD", uc.ref, 6); conn("VCCD", uc.ref, 5); conn("DGND", uc.ref, 2)
        conn("VCCD", cd_c.ref, 1); conn("DGND", cd_c.ref, 2)

        # Controlled-impedance 50 Ohm coax-input microstrip on F.Cu (remaining nets & SHP_ADC/COUNT_HIT routed pad-to-pad by auto_route_board)
        traces.append(make_manhattan_trace(f"{p}.COAX_IN", "F.Cu", _pad_xy(jin, "1"), _pad_xy(rrx, "1"), width_mm=w50))
        # Ground stitching vias tied to In1.Cu AGND / DGND zones
        vias.append(ViaSpec("AGND", 13.0, round(yc - 2.6, 3), diameter_mm=0.60, drill_mm=0.30))
        vias.append(ViaSpec("DGND", 150.0, round(yc - 2.6, 3), diameter_mm=0.60, drill_mm=0.30))

    nets: list[NetSpec] = []
    power_names = {"VIN_P12", "VIN_N12", "VIN_P5", "VIN_N5", "VCCA", "VSSA", "VCCD", "V_P5A", "V_N5A", "AGND", "DGND"}
    for nname, nodes in sorted(nets_dict.items()):
        is_pwr = nname in power_names
        z0 = 50.0 if nname.endswith((".COAX_IN", ".SHP_ADC", ".COUNT_HIT")) else None
        nclass = "RF_50" if z0 else ("Power" if is_pwr else "Default")
        nets.append(NetSpec(
            name=nname,
            nodes=tuple(nodes),
            net_class=nclass,
            is_power=is_pwr,
            has_pwr_flag=(nname in {"VIN_P12", "VIN_N12", "VIN_P5", "VIN_N5", "AGND"}),
            target_z0_ohm=z0,
        ))

    zones = (
        ZoneSpec("AGND", "In1.Cu", ((2.0, 2.0), (130.0, 2.0), (130.0, 132.0), (2.0, 132.0))),
        ZoneSpec("DGND", "In1.Cu", ((132.0, 2.0), (183.0, 2.0), (183.0, 132.0), (132.0, 132.0))),
        ZoneSpec("VCCA", "In2.Cu", ((2.0, 2.0), (130.0, 2.0), (130.0, 66.0), (2.0, 66.0))),
        ZoneSpec("VSSA", "In2.Cu", ((2.0, 68.0), (130.0, 68.0), (130.0, 132.0), (2.0, 132.0))),
        ZoneSpec("VCCD", "In2.Cu", ((132.0, 2.0), (183.0, 2.0), (183.0, 132.0), (132.0, 132.0))),
    )

    spec = BoardSpec(
        name="ibic_warm_shaper_300k",
        title="IBIC v3 Warm 300 K 8-Ch Shaper, Trim DAC, Comparator, FMC ADC Tap & LDO Tree",
        rev="v3.0",
        bom_ids=("S3.2-02", "S3.2-06", "S3.3-03", "S3.2-05"),
        width_mm=185.0,
        height_mm=135.0,
        stackup=stackup,
        components=tuple(comps),
        nets=tuple(nets),
        traces=tuple(traces),
        vias=tuple(vias),
        zones=zones,
        rules=DesignRules(min_trace_width_mm=0.127, min_clearance_mm=0.127, min_edge_clearance_mm=0.50),
        epistemic_meta={**DEFAULT_EPISTEMIC_META, "operating_temp_K": 300.0, "vacuum_grade": "Atmosphere_EMI_Chassis"},
    )
    return auto_route_board(spec, grid_mm=0.50, preserve_existing=True)


# ---------------------------------------------------------------------------
# Board (c): ibic_hv_bias_guard — 3-Stage RC 0-100 V HV Filter & Driven Guard Buffer
# ---------------------------------------------------------------------------

def build_hv_bias_guard_board() -> BoardSpec:
    """Build S3.2-03 / S3.1-01/02 3-stage RC 0-100 V HV bias filter & driven guard PCB."""
    stackup = (
        StackupLayer("F.Cu", "signal", 0.035, material="Copper"),
        StackupLayer("dielectric 1", "core", 0.254, epsilon_r=3.48, loss_tangent=0.0037, material="Rogers RO4350B"),
        StackupLayer("In1.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 2", "core", 0.800, epsilon_r=3.48, loss_tangent=0.0037, material="Rogers RO4350B"),
        StackupLayer("In2.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 3", "core", 0.254, epsilon_r=3.48, loss_tangent=0.0037, material="Rogers RO4350B"),
        StackupLayer("B.Cu", "signal", 0.035, material="Copper"),
    )
    w50 = solve_microstrip_width_mm(50.0, h_mm=0.254, t_mm=0.035, er=3.48)

    comps: list[ComponentSpec] = []
    nets_dict: dict[str, list[tuple[str, str]]] = defaultdict(list)
    traces: list[TraceSpec] = []
    vias: list[ViaSpec] = []

    def add_c(c: ComponentSpec) -> ComponentSpec:
        comps.append(c)
        return c

    def conn(net: str, ref: str, pin: str | int) -> None:
        nets_dict[net].append((ref, str(pin)))

    # --- Left HV Domain (x = 6..50 mm, 0-100 V, all 1206/1210/2512 >= 2.0 mm pad gaps) ---
    jhv_src = add_c(ComponentSpec(
        "JHV_SRC", "SHV_100V_SUPPLY_IN", "Connector_Coaxial:SHV_Amphenol_HV",
        9.0, 18.0, rotation_deg=270.0, pins=auto_footprint_pads("SHV", ("1", "2"), {"1": "HV_IN", "2": "GND"}),
        bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}",
    ))
    rhv1 = add_c(ComponentSpec("RHV1", "10.0k_200V_0.1pct", "Resistor_SMD:R_1206_3216Metric", 21.0, 18.0, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))
    chv1 = add_c(ComponentSpec("CHV1", "1.0uF_200V_X7R", "Capacitor_SMD:C_1210_3225Metric", 21.0, 29.0, rotation_deg=90.0, pins=auto_footprint_pads("1210", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))
    rhv2 = add_c(ComponentSpec("RHV2", "10.0k_200V_0.1pct", "Resistor_SMD:R_1206_3216Metric", 33.0, 18.0, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))
    chv2 = add_c(ComponentSpec("CHV2", "1.0uF_200V_X7R", "Capacitor_SMD:C_1210_3225Metric", 33.0, 29.0, rotation_deg=90.0, pins=auto_footprint_pads("1210", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))
    rhv3 = add_c(ComponentSpec("RHV3", "10.0k_200V_0.1pct", "Resistor_SMD:R_1206_3216Metric", 45.0, 18.0, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))
    chv3 = add_c(ComponentSpec("CHV3", "1.0uF_200V_X7R", "Capacitor_SMD:C_1210_3225Metric", 45.0, 29.0, rotation_deg=90.0, pins=auto_footprint_pads("1210", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))

    # 4-way filtered HV output distribution (to 4 cold CSA modules)
    for k in range(4):
        xk = round(10.0 + k * 12.0, 2)
        riso = add_c(ComponentSpec(
            f"RISO{k}", "1.00k_200V_1pct", "Resistor_SMD:R_1206_3216Metric",
            xk, 44.0, rotation_deg=270.0, pins=auto_footprint_pads("1206", ("1", "2")),
            bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}",
        ))
        jout = add_c(ComponentSpec(
            f"JHV_OUT{k}", "SHV_100V_FILT_OUT", "Connector_Coaxial:SHV_Amphenol_HV",
            xk, 58.0, pins=auto_footprint_pads("SHV", ("1", "2"), {"1": "HV_OUT", "2": "GND"}),
            bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}",
        ))
        conn("HV_S3", riso.ref, 1)
        conn(f"HV_OUT{k}", riso.ref, 2)
        conn(f"HV_OUT{k}", jout.ref, 1)
        conn("AGND", jout.ref, 2)
        traces.append(make_manhattan_trace(f"HV_OUT{k}", "F.Cu", _pad_xy(riso, "2"), _pad_xy(jout, "1"), width_mm=0.35))

    # 100:1 HV sense divider (RHV_DIV_TOP 2512 = 4.8 mm pad gap; MON_HV_DIV <= 1.0 V)
    rhv_top = add_c(ComponentSpec(
        "RHV_DIV_TOP", "10.0M_200V_0.1pct", "Resistor_SMD:R_2512_6332Metric",
        51.0, 69.5, pins=auto_footprint_pads("2512", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}",
    ))
    rhv_bot = add_c(ComponentSpec(
        "RHV_DIV_BOT", "100k_0.1pct", "Resistor_SMD:R_0805_2012Metric",
        64.0, 69.5, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}",
    ))
    chv_mon = add_c(ComponentSpec(
        "CHV_MON", "100nF_C0G", "Capacitor_SMD:C_0603_1608Metric",
        70.5, 69.5, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}",
    ))

    # --- Right Low-Voltage Domain (x = 64..104 mm, separated by milled air-slot at x = 56..58.5 mm!) ---
    jlv_pwr = add_c(ComponentSpec(
        "JLV_PWR", "HDR_4P_P12_N12_AGND_SENSE", "Connector_PinHeader:HDR_1x4_2.54mm",
        67.0, 16.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"),
                                             {"1": "V_P12", "2": "V_N12", "3": "AGND", "4": "AGND_SENSE"}),
        bom_id="S3.2-06", epistemic_tag="{Pasif-COTS}",
    ))
    uguard = add_c(ComponentSpec(
        "UGUARD", "ADA4522-1_GUARD_BUF", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        80.0, 22.0, pins=_soic8_opamp_pins(include_shdn=False),
        mpn="ADA4522-1ARZ", bom_id="S3.2-03", epistemic_tag="{Aday-COTS}",
    ))
    rgrd_fb = add_c(ComponentSpec("RGRD_FB", "100R_0.1pct", "Resistor_SMD:R_0603_1608Metric", 74.0, 31.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))
    cgrd_comp = add_c(ComponentSpec("CGRD_COMP", "100pF_C0G", "Capacitor_SMD:C_0603_1608Metric", 82.0, 31.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))
    cd_gp = add_c(ComponentSpec("CD_GP", "100nF_C0G", "Capacitor_SMD:C_0603_1608Metric", 74.0, 12.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))
    cd_gn = add_c(ComponentSpec("CD_GN", "100nF_C0G", "Capacitor_SMD:C_0603_1608Metric", 82.0, 12.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))

    # 4-way driven guard-ring outputs (50 Ohm microstrip -> SMA)
    for k in range(4):
        yk = round(14.0 + k * 12.0, 2)
        rgout = add_c(ComponentSpec(
            f"RGRD{k}", "49.9R_1pct", "Resistor_SMD:R_0603_1608Metric",
            91.5, yk, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.1-02", epistemic_tag="{Pasif-COTS}",
        ))
        jgout = add_c(ComponentSpec(
            f"JGRD_OUT{k}", "SMA_GUARD_DRV_OUT", "Connector_Coaxial:SMA_EdgeMount",
            104.0, yk, rotation_deg=90.0, edge_mount=True,
            pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "GUARD", "2": "GND"}),
            bom_id="S3.1-02", epistemic_tag="{Pasif-COTS}",
        ))
        conn("GUARD_BUF_OUT", rgout.ref, 1)
        conn(f"GUARD_OUT{k}", rgout.ref, 2)
        conn(f"GUARD_OUT{k}", jgout.ref, 1)
        conn("AGND", jgout.ref, 2)
        traces.append(make_manhattan_trace(f"GUARD_OUT{k}", "F.Cu", _pad_xy(rgout, "2"), _pad_xy(jgout, "1"), width_mm=w50))

    # HV Monitor Unity-Gain Buffer -> SMA Telemetry Output
    umon = add_c(ComponentSpec(
        "UHV_MON", "ADA4522-1_HV_MON", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        81.0, 62.0, pins=_soic8_opamp_pins(include_shdn=False),
        mpn="ADA4522-1ARZ", bom_id="S3.2-03", epistemic_tag="{Aday-COTS}",
    ))
    cd_mp = add_c(ComponentSpec("CD_MP", "100nF_C0G", "Capacitor_SMD:C_0603_1608Metric", 74.0, 54.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))
    cd_mn = add_c(ComponentSpec("CD_MN", "100nF_C0G", "Capacitor_SMD:C_0603_1608Metric", 82.0, 54.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))
    rmon = add_c(ComponentSpec("RMON_OUT", "49.9R_1pct", "Resistor_SMD:R_0603_1608Metric", 91.5, 62.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))
    jmon = add_c(ComponentSpec(
        "JMON_OUT", "SMA_HV_MON_100TO1", "Connector_Coaxial:SMA_EdgeMount",
        104.0, 62.0, rotation_deg=90.0, edge_mount=True,
        pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "MON", "2": "GND"}),
        bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}",
    ))
    r_sense_tie = add_c(ComponentSpec("RSENSE_TIE", "0R_KELVIN_SENSE", "Resistor_SMD:R_0603_1608Metric", 68.0, 31.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.2-03", epistemic_tag="{Pasif-COTS}"))

    # Netlist connections
    conn("HV_IN", jhv_src.ref, 1); conn("AGND", jhv_src.ref, 2)
    conn("HV_IN", rhv1.ref, 1)
    conn("HV_S1", rhv1.ref, 2); conn("HV_S1", chv1.ref, 1); conn("AGND", chv1.ref, 2); conn("HV_S1", rhv2.ref, 1)
    conn("HV_S2", rhv2.ref, 2); conn("HV_S2", chv2.ref, 1); conn("AGND", chv2.ref, 2); conn("HV_S2", rhv3.ref, 1)
    conn("HV_S3", rhv3.ref, 2); conn("HV_S3", chv3.ref, 1); conn("AGND", chv3.ref, 2)
    conn("HV_S3", rhv_top.ref, 1)

    conn("MON_HV_DIV", rhv_top.ref, 2); conn("MON_HV_DIV", rhv_bot.ref, 1); conn("AGND", rhv_bot.ref, 2)
    conn("MON_HV_DIV", chv_mon.ref, 1); conn("AGND", chv_mon.ref, 2)
    conn("MON_HV_DIV", umon.ref, 3)

    conn("V_P12", jlv_pwr.ref, 1); conn("V_N12", jlv_pwr.ref, 2)
    conn("AGND", jlv_pwr.ref, 3); conn("AGND_SENSE", jlv_pwr.ref, 4)
    conn("AGND", r_sense_tie.ref, 1); conn("AGND_SENSE", r_sense_tie.ref, 2)

    conn("AGND_SENSE", uguard.ref, 3)
    conn("GUARD_FB", uguard.ref, 2); conn("GUARD_FB", rgrd_fb.ref, 1); conn("GUARD_FB", cgrd_comp.ref, 1)
    conn("GUARD_BUF_OUT", uguard.ref, 6); conn("GUARD_BUF_OUT", rgrd_fb.ref, 2); conn("GUARD_BUF_OUT", cgrd_comp.ref, 2)
    conn("V_P12", uguard.ref, 7); conn("V_N12", uguard.ref, 4)
    conn("V_P12", cd_gp.ref, 1); conn("AGND", cd_gp.ref, 2)
    conn("V_N12", cd_gn.ref, 1); conn("AGND", cd_gn.ref, 2)

    conn("MON_BUF_OUT", umon.ref, 6); conn("MON_BUF_OUT", umon.ref, 2); conn("MON_BUF_OUT", rmon.ref, 1)
    conn("MON_HV_OUT", rmon.ref, 2); conn("MON_HV_OUT", jmon.ref, 1); conn("AGND", jmon.ref, 2)
    conn("V_P12", umon.ref, 7); conn("V_N12", umon.ref, 4)
    conn("V_P12", cd_mp.ref, 1); conn("AGND", cd_mp.ref, 2)
    conn("V_N12", cd_mn.ref, 1); conn("AGND", cd_mn.ref, 2)

    # HV Stage-to-Stage traces on F.Cu (cleanly spaced >= 2.5 mm from AGND pads)
    traces.append(make_manhattan_trace("HV_IN", "F.Cu", _pad_xy(jhv_src, "1"), _pad_xy(rhv1, "1"), width_mm=0.40))
    traces.append(make_manhattan_trace("HV_S1", "F.Cu", _pad_xy(rhv1, "2"), _pad_xy(rhv2, "1"), width_mm=0.40))
    traces.append(make_manhattan_trace("HV_S2", "F.Cu", _pad_xy(rhv2, "2"), _pad_xy(rhv3, "1"), width_mm=0.40))
    traces.append(make_manhattan_trace("MON_HV_OUT", "F.Cu", _pad_xy(rmon, "2"), _pad_xy(jmon, "1"), width_mm=w50))

    # Stitching vias in LV domain
    vias.append(ViaSpec("AGND", 88.0, 10.0, diameter_mm=0.60, drill_mm=0.30))
    vias.append(ViaSpec("AGND", 88.0, 68.0, diameter_mm=0.60, drill_mm=0.30))

    # Milled Edge.Cuts air-slot isolating 0-100 V HV filter domain from LV guard-buffer domain!
    keepouts = (
        KeepoutSpec("HV_LV_AIR_SLOT", "air_slot", ("Edge.Cuts",), x_mm=56.0, y_mm=8.0, width_mm=2.5, height_mm=54.0),
    )

    nets: list[NetSpec] = []
    for nname, nodes in sorted(nets_dict.items()):
        is_pwr = nname in {"HV_IN", "V_P12", "V_N12", "AGND", "AGND_SENSE"}
        v_work = 100.0 if nname.startswith("HV_") else (12.0 if nname in ("V_P12", "V_N12") else 0.0)
        z0 = 50.0 if (nname.startswith("GUARD_OUT") or nname == "MON_HV_OUT") else None
        nets.append(NetSpec(
            name=nname,
            nodes=tuple(nodes),
            net_class="HV_100V" if v_work >= 50.0 else ("RF_50" if z0 else ("Power" if is_pwr else "Default")),
            is_power=is_pwr,
            has_pwr_flag=(nname in {"HV_IN", "V_P12", "V_N12", "AGND"}),
            voltage_v=v_work,
            target_z0_ohm=z0,
        ))

    # LV ground/power zones strictly on the right side of the milled air-slot (x >= 62 mm)
    zones = (
        ZoneSpec("AGND", "In1.Cu", ((62.0, 2.0), (108.0, 2.0), (108.0, 73.0), (62.0, 73.0))),
        ZoneSpec("V_P12", "In2.Cu", ((62.0, 2.0), (108.0, 2.0), (108.0, 36.0), (62.0, 36.0))),
        ZoneSpec("V_N12", "In2.Cu", ((62.0, 38.0), (108.0, 38.0), (108.0, 73.0), (62.0, 73.0))),
    )

    creepage_rules = (
        CreepageRule("HV_*", working_voltage_v=100.0, min_clearance_mm=1.00, min_creepage_mm=2.00),
    )

    spec = BoardSpec(
        name="ibic_hv_bias_guard",
        title="IBIC v3 3-Stage RC 0-100 V HV Bias Filter & Driven Guard-Ring Distribution PCB",
        rev="v3.0",
        bom_ids=("S3.2-03", "S3.1-01", "S3.1-02"),
        width_mm=110.0,
        height_mm=75.0,
        stackup=stackup,
        components=tuple(comps),
        nets=tuple(nets),
        traces=tuple(traces),
        vias=tuple(vias),
        zones=zones,
        keepouts=keepouts,
        creepage_rules=creepage_rules,
        rules=DesignRules(min_trace_width_mm=0.127, min_clearance_mm=0.127, min_edge_clearance_mm=0.50),
        epistemic_meta={**DEFAULT_EPISTEMIC_META, "operating_temp_K": 300.0, "hv_rating_V": 100.0},
    )
    return auto_route_board(spec, grid_mm=0.50, preserve_existing=True)


# ---------------------------------------------------------------------------
# Real Native ngspice-47 Deck (Zero PSpice Syntax, True 100 K Cold + 300 K Warm)
# ---------------------------------------------------------------------------

def render_ibic_ngspice_deck() -> str:
    """Emit clean native ngspice deck for the split 3-PCB IBIC cryo chain + S3.2-03 HV filter.

    Calibration math (exact to <0.01% against analytical noise PSD):
      * LTC6268 cold CSA (100 K): e_n = 2.0 nV/rtHz, f_c = 2.0 kHz, i_n = 0.5 fA/rtHz,
        plus pixel diode dark current I_leak = 0.05 pA @ 100 K:
          - Bias diode D_LTC_VN at I_D = 100 uA -> 2*q*I_D = 3.204353268e-23 A^2/Hz
          - R_H_LTC = sqrt(4.0e-18 / 3.204353268e-23) = 353.31438092 Ohm
          - KF_LTC  = 2*q*2000 = 6.408706536e-16 (AF=1) -> exact e_n^2*(1 + fc/f)
          - Parallel current noise: S_I = 2*q*0.05p + (0.5f)^2 = 2.6602176634e-31 A^2/Hz
            G_F_IN = sqrt(S_I / (2*q*100u)) = 9.11146648e-5
      * ADA4817-1 warm shaper (300 K): e_n = 4.0 nV/rtHz:
          - R_H_ADA = sqrt(16.0e-18 / 3.204353268e-23) = 706.62876184 Ohm (KF=0)
      * Ion impulse: 5 keV 31P+ Lindhard @ 100 K = 341.7145 e- = 5.474870e-17 C.
        EXP(0 {Q_ION/TAU_COL} 50n 0.1n 50.1n {TAU_COL}) delivers exact charge Q_ION.
      * S3.2-03 3-stage RC HV bias filter: 3 x (10 kOhm + 1.0 uF with realistic 100 mOhm ESR & 2 nH ESL).
    """
    return f"""* Atom Lithography Machine - IBIC Cryo Front-End v3 (Split 3-PCB Chain, Native ngspice)
* Epistemic status: M0/M1 DESIGN_ONLY; no_lab_measurement=true; no_physical_fab=true.
* Cold PCB (S3.2-01): 100 K (-173.15 C) global temp, Cf=0.25pF, Rf=1G, LTC6268 + 50 Ohm coax driver.
* Warm PCB (S3.2-02/06, S3.3-03): 300 K (temp=26.85 on warm R's), ADA4817-1 CR-RC (tau=1.2us), ADC tap, TLV3501.
* HV Bias Filter PCB (S3.2-03): 3-stage RC (10k/1uF w/ 100mOhm ESR, 2nH ESL) @ 300 K.

.temp -173.15

.param C_DET=0.5p  C_PAR=0.25p  C_F=0.25p  R_F=1G
.param C_S=600p    R_S1=2.0k    R_G1=100   R_G2=13.5k
.param R_S2=2.0k   C_P=600p     R_HYS1=1.0k R_HYS2=1.0Meg  R_TERM=49.9
.param Q_ION={LINDHARD_5KEV_100K_C:.9e}
.param TAU_COL=1.5n
.param V_THR=0.00423

.model D_LTC_1F D(IS=1e-14 N=1 RS=0 EG=0 XTI=0 KF=6.408706536e-12 AF=1)

* --- Calibrated Cold LTC6268 CSA Macromodel (100 K: e_n=2.0 nV/rtHz, fc=2 kHz, i_n+leak=0.516 fA/rtHz) ---
* Uses zero-DC-offset resistor thermal noise for white e_n & i_n, plus tiny-current 10 nA diode
* through 0.016 Hz noiseless DC-block for exact 1/f flicker noise (zero transient charge drift!).
.subckt OPAMP_LTC6268_100K inp inn out
Cin inp inn 0.45p
Rin inp inn 1T noisy=0
* 1) White series voltage noise: sqrt(4*kB*300*241.43235) = 2.00000 nV/rtHz (zero DC)
Rnw nw 0 241.43235 temp=26.85
* 2) 1/f flicker series voltage noise: Id=10nA, KF=6.4087e-12 -> S_I,1f=6.4087e-20/f; R_H=353.31438 -> S_V,1f=8.0e-15/f (fc=2 kHz)
Iflk 0 flk_d DC 10n
Cflk flk_d 0 1u
Dflk flk_d flk_s D_LTC_1F
Vflk flk_s 0 DC 0
Hflk flk_raw 0 Vflk 353.31438092
Cblk flk_raw flk_ac 100u
Rblk flk_ac 0 100k noisy=0
* Combine white + 1/f voltage noise in series with IN+
Evn_w  inp_w   inp   nw     0 1.0
Evn_1f inp_int inp_w flk_ac 0 1.0
* 3) Parallel input current noise: sqrt(2*q*0.05p + (0.5f)^2) = 0.515773 fA/rtHz (zero DC!)
Rni ni 0 1k temp=26.85
Gin 0 inn ni 0 1.267145e-7
* Single-pole open-loop gain (A0=1e5, GBP=500 MHz -> fp=5 kHz) + 1 Ohm output impedance
Egain n1 0 inp_int inn 1e5
Rp n1 n2 1k noisy=0
Cp n2 0 31.8309886n
Ebuf n_out 0 n2 0 1.0
Rout n_out out 1 noisy=0
.ends OPAMP_LTC6268_100K

* --- Calibrated Cold 50 Ohm Coax Line Driver (LTC6268 @ 100 K, e_n=2.0 nV/rtHz, GBP=500 MHz) ---
.subckt OPAMP_LTC6268_DRV inp inn out
Cin inp inn 0.45p
Rin inp inn 1T noisy=0
Rnw nw 0 241.43235 temp=26.85
Evn inp_int inp nw 0 1.0
Egain n1 0 inp_int inn 1e5
Rp n1 n2 1k noisy=0
Cp n2 0 31.8309886n
Ebuf n_out 0 n2 0 1.0
Rout n_out out 1 noisy=0
.ends OPAMP_LTC6268_DRV

* --- Calibrated Warm ADA4817-1 Shaper/Buffer Macromodel (300 K: e_n=4.0 nV/rtHz, GBP=1.05 GHz) ---
.subckt OPAMP_ADA4817_300K inp inn out
Cin inp inn 1.3p
Rin inp inn 500G noisy=0
* White series voltage noise: sqrt(4*kB*300*965.7294) = 4.00000 nV/rtHz (zero DC)
Rnw nw 0 965.7294 temp=26.85
Evn inp_int inp nw 0 1.0
Egain n1 0 inp_int inn 1e5
Rp n1 n2 1k noisy=0
Cp n2 0 15.1576136n
Ebuf n_out 0 n2 0 1.0
Rout n_out out 1 noisy=0
.ends OPAMP_ADA4817_300K

* --- Fast Rail-to-Rail Comparator (TLV3501, t_pd=4.5 ns, 0..3.3 V) ---
.subckt CMP_TLV3501 inp inn vcc gnd out
Braw n1 gnd V = V(vcc) * 0.5 * (1 + tanh(V(inp, inn) / 0.2m))
Rdel n1 out 100 noisy=0
Cdel out gnd 45p
.ends CMP_TLV3501

* --- Power Supplies ---
Vccd vccd 0 DC 3.3
* Rising threshold V_DAC = V_THR = 4.23 mV; falling reset = V_THR - 3.3 mV = 0.93 mV > 0 (unique OFF DC equilibrium)
Vthr thr_in 0 DC {{V_THR}}

* =========================================================================
* CHANNEL 0 FULL SPLIT 3-PCB SIGNAL CHAIN (100 K Cold -> 50 Ohm Coax -> 300 K Warm)
* =========================================================================
* 1) Cold-Island 100 K CSA PCB (S3.2-01, global .temp = -173.15 C)
Cdet0 csa_sum 0 {{C_DET + C_PAR}}
* Positive output polarity (5 keV 31P+ Lindhard @ 100 K: Q_ION = 341.715 e- = 0.05475 fC in 1.5 ns collection pulse)
* Trapezoid area = Ipk * (PW + 0.5*(TR+TF)) = (Q_ION/1.5n) * (1.4n + 0.1n) = Q_ION exact with automatic SPICE breakpoints!
Iion0 csa_sum 0 DC 0 AC 1 PULSE(0 {{Q_ION/TAU_COL}} 50n 0.1n 0.1n 1.4n 1m)
Xcsa0 0 csa_sum csa_out OPAMP_LTC6268_100K
Cf0   csa_out csa_sum {{C_F}}
Rf0   csa_out csa_sum {{R_F}}

* Cold 50 Ohm Coax Line Driver (G = +2.00 -> 49.9 Ohm series -> 50 Ohm CF63 coax -> 49.9 Ohm RX = 1.000x net)
Xdrv0 csa_out drv_fb drv_out OPAMP_LTC6268_DRV
Rdrv1 drv_fb  0       499
Rdrv2 drv_out drv_fb  499
Rtx0  drv_out coax_tx 49.9
* 0.4 m PTFE 50 Ohm micro-coax + CF63 feedthrough (4-section pi ladder: Z0=50 Ohm, TD=2.0 ns, f_c=636 MHz)
Ccx0  coax_tx 0       5p
Lcx1  coax_tx cx1     25n
Ccx1  cx1     0       10p
Lcx2  cx1     cx2     25n
Ccx2  cx2     0       10p
Lcx3  cx2     cx3     25n
Ccx3  cx3     0       10p
Lcx4  cx3     coax_rx 25n
Ccx4  coax_rx 0       5p

* 2) Warm Ex-Vacuum 300 K Shaper PCB (S3.2-02, S3.3-03; resistors explicitly at temp=26.85 C = 300 K)
Rrx0  coax_rx 0       49.9    temp=26.85
Cs0   coax_rx cr_out  {{C_S}}
Rs1_0 cr_out  0       {{R_S1}}  temp=26.85
Xshp0 cr_out  shp_fb  shp_gain OPAMP_ADA4817_300K
Rg1_0 shp_fb  0       {{R_G1}}  temp=26.85
Rg2_0 shp_gain shp_fb {{R_G2}}  temp=26.85
Rs2_0 shp_gain shp_out {{R_S2}} temp=26.85
Cp0   shp_out 0       {{C_P}}

* Buffered Analog SHP_OUT Tap to 50 MS/s 12-bit FMC PHA ADC (S3.3-03, f_c=26.5 MHz anti-alias)
Xadc0 shp_out shp_buf shp_buf OPAMP_ADA4817_300K
Raa0  shp_buf shp_adc 49.9    temp=26.85
Caa0  shp_adc 0       120p
Radc_load shp_adc 0   10k     temp=26.85

* Comparator Threshold RC Filter & TLV3501 Hysteresis Comparator (3.3 mV hysteresis driven from buffered shp_buf!)
Rdac0  thr_in  thresh  1k      temp=26.85
Cdac0  thresh  0       100n
Rhys1  shp_buf cmp_inp {{R_HYS1}} temp=26.85
Rhys2  cmp_out cmp_inp {{R_HYS2}} temp=26.85
Xcmp0  cmp_inp thresh  vccd 0 cmp_out CMP_TLV3501
Rterm0 cmp_out count_hit {{R_TERM}} temp=26.85
Rfpga0 count_hit 0     10k     temp=26.85

* =========================================================================
* S3.2-03 3-STAGE RC 0-100 V HV BIAS FILTER VERIFICATION SUBSYSTEM (300 K)
* =========================================================================
Vhv_in hv_in 0 DC -30.0 AC 1
Rhv1 hv_in hv_s1 10k temp=26.85
Chv1 hv_s1 hv_c1 1.0u
Resr1 hv_c1 hv_l1 100m temp=26.85
Lesl1 hv_l1 0 2n

Rhv2 hv_s1 hv_s2 10k temp=26.85
Chv2 hv_s2 hv_c2 1.0u
Resr2 hv_c2 hv_l2 100m temp=26.85
Lesl2 hv_l2 0 2n

Rhv3 hv_s2 hv_s3 10k temp=26.85
Chv3 hv_s3 hv_c3 1.0u
Resr3 hv_c3 hv_l3 100m temp=26.85
Lesl3 hv_l3 0 2n
Rhv_load hv_s3 0 10Meg temp=26.85

.control
set noaskquit

* 1) AC Analysis: IBIC chain transimpedance & S3.2-03 HV filter attenuation
ac dec 100 10 50Meg
meas ac z_peak_ohm MAX vm(shp_out)
meas ac z_f_lo WHEN vm(shp_out)='0.707107*z_peak_ohm' RISE=1
meas ac z_f_hi WHEN vm(shp_out)='0.707107*z_peak_ohm' FALL=1
let z_peak_freq = sqrt(z_f_lo * z_f_hi)
print z_peak_freq
meas ac z_adc_peak_ohm MAX vm(shp_adc)
meas ac hv_atten_100k_db FIND vdb(hv_s3) AT=100k
meas ac hv_atten_1k_db   FIND vdb(hv_s3) AT=1k
meas ac hv_atten_100hz_db FIND vdb(hv_s3) AT=100

* 2) Transient Analysis: 5 keV 31P+ ion pulse (341.7 e-, 0.05475 fC @ 100 K)
tran 5n 8.0u
meas tran v_peak_5kev MAX v(shp_out)
meas tran t_peak_abs MAX_AT v(shp_out)
let t_peak_after_hit = t_peak_abs - 50n
print t_peak_after_hit
meas tran v_adc_peak_5kev MAX v(shp_adc)
meas tran cmp_max_v MAX v(count_hit)
meas tran cmp_t_rise WHEN v(count_hit)=1.65 RISE=1
meas tran cmp_t_fall WHEN v(count_hit)=1.65 FALL=1

* 3) Integrated Noise Analysis: IBIC shaper output RMS noise (10 Hz .. 50 MHz)
noise v(shp_out) Iion0 dec 50 10 50Meg
setplot noise2
let ibic_onoise_rms_v = onoise_total
print ibic_onoise_rms_v

* 4) Integrated Noise Analysis: S3.2-03 HV bias output thermal noise (1 Hz .. 10 MHz)
noise v(hv_s3) Vhv_in dec 40 1 10Meg
setplot noise4
let hv_onoise_rms_v = onoise_total
print hv_onoise_rms_v

quit 0
.endc
.end
"""


# ---------------------------------------------------------------------------
# Independent Python MNA Cross-Check (AC Transimpedance & HV Filter Attenuation)
# ---------------------------------------------------------------------------

def run_mna_crosscheck() -> dict[str, Any]:
    """Independently cross-check IBIC AC transimpedance & S3.2-03 HV filter via MnaCircuit."""
    # 1) IBIC linear signal chain MNA (cold CSA + G=2 coax driver + 50/50 divider + warm CR-RC shaper)
    mna = MnaCircuit()
    c_in_ext = 0.5e-12 + 0.25e-12
    mna.add_capacitor("csa_sum", "0", c_in_ext)
    mna.add_isource("csa_sum", "0", ac=1.0)
    mna.add_opamp_single_pole("0", "csa_sum", "csa_out", a0=1e5, gbp_hz=500e6, c_in_f=0.45e-12, r_in_ohm=1e12, r_out_ohm=1.0)
    mna.add_capacitor("csa_out", "csa_sum", 0.25e-12)
    mna.add_resistor("csa_out", "csa_sum", 1.0e9)
    # G=+2 coax driver + 4-section 50 Ohm coax ladder + 49.9/49.9 matched link
    mna.add_opamp_single_pole("csa_out", "drv_fb", "drv_out", a0=1e5, gbp_hz=500e6, c_in_f=0.45e-12, r_in_ohm=1e12, r_out_ohm=1.0)
    mna.add_resistor("drv_fb", "0", 499.0)
    mna.add_resistor("drv_out", "drv_fb", 499.0)
    mna.add_resistor("drv_out", "coax_tx", 49.9)
    mna.add_capacitor("coax_tx", "0", 5e-12)
    mna.add_inductor("coax_tx", "cx1", 25e-9); mna.add_capacitor("cx1", "0", 10e-12)
    mna.add_inductor("cx1", "cx2", 25e-9); mna.add_capacitor("cx2", "0", 10e-12)
    mna.add_inductor("cx2", "cx3", 25e-9); mna.add_capacitor("cx3", "0", 10e-12)
    mna.add_inductor("cx3", "coax_rx", 25e-9); mna.add_capacitor("coax_rx", "0", 5e-12)
    mna.add_resistor("coax_rx", "0", 49.9)
    # Warm CR-RC shaper (buffer isolates comparator hysteresis so shp_out sees only ADA4817 Rin)
    mna.add_capacitor("coax_rx", "cr_out", 600e-12)
    mna.add_resistor("cr_out", "0", 2.0e3)
    mna.add_opamp_single_pole("cr_out", "shp_fb", "shp_gain", a0=1e5, gbp_hz=1.05e9, c_in_f=1.3e-12, r_in_ohm=500e9, r_out_ohm=1.0)
    mna.add_resistor("shp_fb", "0", 100.0)
    mna.add_resistor("shp_gain", "shp_fb", 13.5e3)
    mna.add_resistor("shp_gain", "shp_out", 2.0e3)
    mna.add_capacitor("shp_out", "0", 600e-12)

    freqs = np.geomspace(1e3, 1e7, 400)
    sol = mna.solve_ac(freqs)
    z_mag = np.abs(sol["shp_out"])
    pk_idx = int(np.argmax(z_mag))
    mna_z_peak_ohm = float(z_mag[pk_idx])
    mna_z_peak_freq_hz = float(freqs[pk_idx])

    # 2) S3.2-03 3-stage RC HV bias filter MNA (with 100 mOhm ESR & 2 nH ESL)
    hv = MnaCircuit()
    hv.add_vsource("hv_in", "0", ac=1.0)
    for st, (n_in, n_out) in enumerate((("hv_in", "hv_s1"), ("hv_s1", "hv_s2"), ("hv_s2", "hv_s3")), start=1):
        hv.add_resistor(n_in, n_out, 10e3)
        hv.add_capacitor(n_out, f"c{st}", 1.0e-6)
        hv.add_resistor(f"c{st}", f"l{st}", 0.1)
        hv.add_inductor(f"l{st}", "0", 2e-9)
    hv.add_resistor("hv_s3", "0", 10e6)
    hv_sol = hv.solve_ac([100.0, 1e3, 100e3])
    hv_db = [float(20.0 * math.log10(max(abs(v), 1e-30))) for v in hv_sol["hv_s3"]]
    return {
        "mna_z_peak_ohm": round(mna_z_peak_ohm, 3),
        "mna_z_peak_freq_hz": round(mna_z_peak_freq_hz, 2),
        "mna_hv_atten_100hz_db": round(hv_db[0], 3),
        "mna_hv_atten_1k_db": round(hv_db[1], 3),
        "mna_hv_atten_100k_db": round(hv_db[2], 3),
    }


def compute_cold_stray_c_budget_pf() -> dict[str, Any]:
    """Analytical PCB stray capacitance budget on CSA_SUM with In1/In2 keepout & driven guard ring."""
    # With In1.Cu & In2.Cu copper keepout directly under CSA_SUM on Rogers RO4350B (er=3.48):
    #   - Distance from F.Cu CSA_SUM trace to B.Cu ground shield = 0.254 + 0.035 + 0.800 + 0.035 + 0.254 = 1.378 mm
    #   - CSA_SUM copper area: ~12 mm x 0.15 mm trace (1.8 mm^2) + 4 SMD pads (~1.6 mm^2) = 3.4 mm^2
    #   - Parallel-plate + 35% fringing C to B.Cu: 1.35 * eps0 * 3.48 * (3.4e-6) / (1.378e-3) = 0.102 pF
    #   - Coplanar guard-ring coupling is actively driven to V(CSA_SUM) (~0 V virtual ground) -> Miller C_eff ~ 0.005 pF!
    eps0 = 8.854187817e-12
    er = 3.48
    h_to_bcu_m = (0.254 + 0.035 + 0.800 + 0.035 + 0.254) * 1e-3
    area_m2 = 3.4e-6
    c_to_bcu_pf = 1.35 * eps0 * er * area_m2 / h_to_bcu_m * 1e12
    c_guard_residual_pf = 0.005
    c_total_stray_pf = c_to_bcu_pf + c_guard_residual_pf
    return {
        "substrate": "Rogers RO4350B (er=3.48)",
        "keepout_layers": ["In1.Cu", "In2.Cu"],
        "distance_to_bcu_mm": round(h_to_bcu_m * 1e3, 3),
        "csa_sum_copper_area_mm2": 3.4,
        "c_to_bcu_shield_pF": round(c_to_bcu_pf, 4),
        "c_driven_guard_residual_pF": c_guard_residual_pf,
        "c_pcb_stray_total_pF": round(c_total_stray_pf, 4),
        "budget_max_pF": 0.15,
        "within_budget": bool(c_total_stray_pf < 0.15),
    }


def build_and_verify_all(out_dir: Path | None = None) -> dict[str, Any]:
    """Generate all 3 IBIC v3 KiCad 8 boards + native ngspice deck, run ERC/DRC/SPICE/MNA, save JSON."""
    od = out_dir or OUT_DIR
    od.mkdir(parents=True, exist_ok=True)

    # 1. Build & verify all 3 KiCad 8 boards (strict S-expr + ERC + DRC)
    boards = [build_cold_csa_board(), build_warm_shaper_board(), build_hv_bias_guard_board()]
    board_reports: dict[str, Any] = {}
    for spec in boards:
        rep = verify_board_bundle(spec, od)
        board_reports[spec.name] = rep

    # 2. Write & execute real native ngspice-47 deck
    cir_path = od / "ibic_cryo_chain_100k.cir"
    cir_path.write_text(render_ibic_ngspice_deck(), encoding="utf-8")
    spice_res = run_ngspice(cir_path, workdir=od)

    # Compute derived ENC & gain metrics directly from real ngspice measurements
    m = spice_res.metrics
    v_peak_5kev_v = m.get("v_peak_5kev", 0.0)
    t_peak_after_hit_s = m.get("t_peak_after_hit", 0.0)
    v_adc_peak_5kev_v = m.get("v_adc_peak_5kev", 0.0)
    ibic_onoise_rms_v = m.get("ibic_onoise_rms_v", 0.0)
    hv_onoise_rms_v = m.get("hv_onoise_rms_v", 0.0)
    hv_atten_100k_db = m.get("hv_atten_100k_db", 0.0)
    z_peak_ohm = m.get("z_peak_ohm", 0.0)
    z_peak_freq_hz = m.get("z_peak_freq", 0.0)
    cmp_max_v = m.get("cmp_max_v", 0.0)
    cmp_pw_ns = (m.get("cmp_t_fall", 0.0) - m.get("cmp_t_rise", 0.0)) * 1e9

    v_per_e_v = v_peak_5kev_v / LINDHARD_5KEV_100K_E if v_peak_5kev_v > 0 else 0.0
    enc_e_rms = ibic_onoise_rms_v / v_per_e_v if v_per_e_v > 0 else float("inf")
    gain_mv_per_fc = (v_peak_5kev_v * 1e3) / (LINDHARD_5KEV_100K_C * 1e15)

    # 3. Independent Python MNA cross-check
    mna = run_mna_crosscheck()
    z_peak_rel_diff_pct = abs(z_peak_ohm - mna["mna_z_peak_ohm"]) / max(mna["mna_z_peak_ohm"], 1e-9) * 100.0
    hv_100k_diff_db = abs(hv_atten_100k_db - mna["mna_hv_atten_100k_db"])

    # 4. Cold-island stray C budget
    stray_c = compute_cold_stray_c_budget_pf()

    # 5. Summary pass/fail checks
    checks = {
        "all_3_boards_sexpr_valid": all(r["sexpr_valid"] for r in board_reports.values()),
        "all_3_boards_erc_zero": all(r["erc"]["passed"] and len(r["erc"]["errors"]) == 0 for r in board_reports.values()),
        "all_3_boards_drc_zero": all(r["drc"]["passed"] and len(r["drc"]["errors"]) == 0 for r in board_reports.values()),
        "all_3_boards_100pct_routed": all(
            r["drc"]["unrouted_net_count"] == 0
            and r["drc"]["unconnected_items"] == 0
            and r["drc"]["routed_net_count"] == r["drc"]["total_multi_pin_nets"]
            for r in board_reports.values()
        ),
        "all_3_boards_zero_dangling": all(r["drc"]["track_dangling_count"] == 0 for r in board_reports.values()),
        "ngspice_ok": spice_res.ok,
        "enc_le_35_e": bool(15.0 <= enc_e_rms <= 35.0),
        "t_peak_near_1p2us": bool(1.05e-6 <= t_peak_after_hit_s <= 1.35e-6),
        "v_peak_5kev_10_to_12mV": bool(9.5e-3 <= v_peak_5kev_v <= 12.5e-3),
        "adc_tap_tracks_shaper": bool(abs(v_adc_peak_5kev_v - v_peak_5kev_v) / max(v_peak_5kev_v, 1e-12) < 0.02),
        "comparator_fires_3v3": bool(cmp_max_v >= 3.0 and cmp_pw_ns > 500.0),
        "hv_filter_gt_100db_at_100khz": bool(hv_atten_100k_db <= -100.0),
        "hv_filter_noise_lt_10uvrms": bool(hv_onoise_rms_v < 10e-6),
        "mna_ngspice_ac_parity_lt_1pct": bool(z_peak_rel_diff_pct < 1.0 and hv_100k_diff_db < 0.5),
        "cold_stray_c_lt_0p15pF": stray_c["within_budget"],
    }

    report = {
        "module": "ibic_cryo_frontend_v3",
        "bom_ids_covered": [
            "S3.1-01", "S3.1-02", "S3.2-01", "S3.2-02",
            "S3.2-03", "S3.2-04", "S3.2-05", "S3.2-06", "S3.3-03",
        ],
        "epistemic_meta": {
            **DEFAULT_EPISTEMIC_META,
            "simulation_engine": spice_res.version,
            "cold_stage_temp_K": 100.0,
            "warm_stage_temp_K": 300.0,
        },
        "boards": board_reports,
        "cold_stray_capacitance_budget": stray_c,
        "ngspice_simulation": {
            "cir_file": cir_path.name,
            "version": spice_res.version,
            "ok": spice_res.ok,
            "errors": spice_res.errors,
            "warnings": spice_res.warnings,
            "raw_metrics": m,
            "derived": {
                "charge_5kev_31p_100k_e": round(LINDHARD_5KEV_100K_E, 3),
                "charge_5kev_31p_100k_fC": round(LINDHARD_5KEV_100K_C * 1e15, 5),
                "z_peak_MOhm": round(z_peak_ohm * 1e-6, 4),
                "z_peak_freq_kHz": round(z_peak_freq_hz * 1e-3, 3),
                "v_peak_5kev_mV": round(v_peak_5kev_v * 1e3, 4),
                "v_adc_peak_5kev_mV": round(v_adc_peak_5kev_v * 1e3, 4),
                "t_peak_after_hit_ns": round(t_peak_after_hit_s * 1e9, 2),
                "gain_mV_per_fC": round(gain_mv_per_fc, 3),
                "v_per_e_uV": round(v_per_e_v * 1e6, 4),
                "ibic_onoise_rms_mV": round(ibic_onoise_rms_v * 1e3, 5),
                "enc_e_rms": round(enc_e_rms, 3),
                "exp127_reference_enc_e": 24.07,
                "comparator_max_V": round(cmp_max_v, 4),
                "comparator_pulse_width_ns": round(cmp_pw_ns, 2),
                "hv_atten_100k_dB": round(hv_atten_100k_db, 3),
                "hv_onoise_rms_uV": round(hv_onoise_rms_v * 1e6, 5),
            },
        },
        "mna_crosscheck": {
            **mna,
            "z_peak_vs_ngspice_rel_diff_pct": round(z_peak_rel_diff_pct, 4),
            "hv_100k_vs_ngspice_diff_dB": round(hv_100k_diff_db, 4),
        },
        "checks": checks,
        "all_passed": all(checks.values()),
    }

    (od / "ibic_v3_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    rep = build_and_verify_all()
    print("=== IBIC CRYO FRONT-END V3 VERIFICATION ===")
    for bname, brep in rep["boards"].items():
        dr = brep["drc"]
        print(
            f"  PCB {bname}: comps={brep['erc']['component_count']}, nets={brep['erc']['net_count']}, "
            f"routed={dr['routed_net_count']}/{dr['total_multi_pin_nets']}, unconn={dr['unconnected_items']}, "
            f"dangling={dr['track_dangling_count']}, segs={dr['segment_count']}, vias={dr['via_count']}, "
            f"ERC_err={len(brep['erc']['errors'])}, DRC_err={len(dr['errors'])}, "
            f"Z0_checks={len(dr['impedance_checks'])}, HV_checks={len(dr['hv_checks'])}"
        )
        if brep["erc"]["errors"]:
            print("    ERC ERRORS:", brep["erc"]["errors"][:5])
        if dr["errors"]:
            print("    DRC ERRORS:", dr["errors"][:10])
    d = rep["ngspice_simulation"]["derived"]
    print(
        f"  ngspice ({rep['ngspice_simulation']['version']}): ok={rep['ngspice_simulation']['ok']} | "
        f"ENC={d['enc_e_rms']} e- | V_peak={d['v_peak_5kev_mV']} mV | t_peak={d['t_peak_after_hit_ns']} ns | "
        f"V_adc={d['v_adc_peak_5kev_mV']} mV | CMP={d['comparator_max_V']} V ({d['comparator_pulse_width_ns']} ns) | "
        f"HV_100k={d['hv_atten_100k_dB']} dB | HV_noise={d['hv_onoise_rms_uV']} uVrms"
    )
    print(f"  MNA parity: Z_diff={rep['mna_crosscheck']['z_peak_vs_ngspice_rel_diff_pct']}% | HV_diff={rep['mna_crosscheck']['hv_100k_vs_ngspice_diff_dB']} dB")
    print(f"  ALL_PASSED = {rep['all_passed']}")
    if not rep["all_passed"]:
        print("  FAILED CHECKS:", [k for k, v in rep["checks"].items() if not v])
        if rep["ngspice_simulation"]["errors"]:
            print("  SPICE ERRORS:", rep["ngspice_simulation"]["errors"])
