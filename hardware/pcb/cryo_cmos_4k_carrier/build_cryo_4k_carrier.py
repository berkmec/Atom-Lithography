"""Cryo-CMOS 4 K Chip Carrier & 968-Gate Crossbar Mux + MXC RC/Eccosorb Filter PCB & Live ngspice-47 Suite.

Covers BOM items: S6.10-03, S6.7-02, S7.3-02, S7.3-01.

Architecture:
  * 4-layer cryogenic thermal-cycle-hardened PCB (165 x 125 mm, >100 cooldowns 300 K <-> 4 K):
      - F.Cu / B.Cu (ENIG Au wire-bondable) over 0.254 mm Rogers RO4350B (er=3.48)
      - Internal 0.800 mm AlN / Cu-Invar-Cu CTE-matched thermal core (~4.5 ppm/K matching Si)
        sandwiched between In1.Cu (GND_4K) and In2.Cu (VDD_4K_1V2) solid reference planes.
  * 8x SKY130 4 K Cryo-CMOS Crossbar Mux Dies (U_MUX0..U_MUX7, S7.3-01 & S6.10-03):
      - Implements L=11 surface code (121 logical nodes x 8 DC gates/node = 968 local Stark/M4/SET
        DC gates, Exp131) on CTE-matched chip carriers (S7.3-02) with cryo-stable C0G/NP0 decoupling
        and controlled 50 Ohm SPI daisy-chain routing.
      - Strictly bounded 4 K total dissipation <= 15.4 mW (static bias + SPI + 968-gate dynamic refresh).
  * 8-Channel Modular 4 K / MXC (20 mK) 2-Stage RC + Eccosorb CR-124 RF Low-Pass DC Gate Filter Bank
    (S6.7-02) with cryo thin-film NiCr resistors, C0G/NP0 capacitors, HF bypass shunts, and
    Eccosorb CR-124 magnetically-loaded RF absorber stages.
  * Live ngspice-47 simulation (cryo_4k_gate_filter.cir) using native .temp -269.15 (4.00 K) and
    per-instance temp=-273.13 (20 mK MXC) + temp=26.85 (300 K DAC noise floor), verifying:
      - RF attenuation > 60 dB @ 1 GHz (with realistic resistor stray C & MLCC ESL!)
      - In-band thermal noise density < 0.5 uV/rtHz (intrinsic 4 K/20 mK + 300 K DAC floor)
      - Clean DC Stark gate step settling time
      - 968-gate SKY130 crossbar total dissipation <= 15.4 mW @ 4 K
      - Independent Python MNA AC transfer cross-check parity (< 0.5 dB).

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
    DEFAULT_EPISTEMIC_META,
    DesignRules,
    MnaCircuit,
    NetSpec,
    PinSpec,
    StackupLayer,
    TraceSpec,
    ViaSpec,
    ZoneSpec,
    auto_footprint_pads,
    auto_route_board,
    calc_microstrip_z0,
    run_ngspice,
    solve_microstrip_width_mm,
    verify_board_bundle,
)

OUT_DIR = Path(__file__).resolve().parent
K_B = 1.380649e-23


# ---------------------------------------------------------------------------
# 1. Footprint Helpers
# ---------------------------------------------------------------------------

def _grid_pins(
    pin_defs: list[tuple[str, str, str]],
    cols: int,
    pitch_mm: float = 1.20,
    pad_mm: float = 0.55,
) -> tuple[PinSpec, ...]:
    rows = int(math.ceil(len(pin_defs) / cols))
    res: list[PinSpec] = []
    for idx, (pnum, pname, ptype) in enumerate(pin_defs):
        r, c = divmod(idx, cols)
        dx = (c - (cols - 1) / 2.0) * pitch_mm
        dy = (r - (rows - 1) / 2.0) * pitch_mm
        res.append(PinSpec(pnum, pname, ptype, round(dx, 4), round(dy, 4), pad_mm, pad_mm, 0.0))
    return tuple(res)


# ---------------------------------------------------------------------------
# 2. 4-Layer Rogers / AlN / Cu-Invar-Cu 4 K Cryo-CMOS Carrier Board Builder
# ---------------------------------------------------------------------------

def build_cryo_4k_carrier() -> BoardSpec:
    """Build 4 K 4-layer Rogers/AlN/Cu-Invar-Cu 968-gate SKY130 Crossbar + RC/Eccosorb Filter PCB."""
    stackup = (
        StackupLayer("F.Cu", "signal", 0.035, material="Copper ENIG Au-Bond"),
        StackupLayer("dielectric 1", "core", 0.254, epsilon_r=3.48, loss_tangent=0.0037, material="Rogers RO4350B Cryo"),
        StackupLayer("In1.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 2", "core", 0.800, epsilon_r=8.90, loss_tangent=0.0010, material="AlN / Cu-Invar-Cu CTE Core"),
        StackupLayer("In2.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 3", "core", 0.254, epsilon_r=3.48, loss_tangent=0.0037, material="Rogers RO4350B Cryo"),
        StackupLayer("B.Cu", "signal", 0.035, material="Copper ENIG Au-Bond"),
    )

    w50_ms = solve_microstrip_width_mm(50.0, h_mm=0.254, t_mm=0.035, er=3.48)  # 0.5429 mm -> 50.00 Ohm

    comps: list[ComponentSpec] = []
    nets_dict: dict[str, list[tuple[str, str]]] = defaultdict(list)
    net_meta: dict[str, dict[str, Any]] = {}
    traces: list[TraceSpec] = []
    vias: list[ViaSpec] = []

    def add_c(c: ComponentSpec) -> ComponentSpec:
        comps.append(c)
        return c

    def conn(net: str, ref: str, pin: str | int) -> None:
        nets_dict[net].append((ref, str(pin)))

    def set_net(
        net: str,
        *,
        net_class: str = "Default",
        is_power: bool = False,
        has_pwr_flag: bool = False,
        voltage_v: float = 0.0,
        target_z0_ohm: float | None = None,
    ) -> None:
        net_meta[net] = {
            "net_class": net_class,
            "is_power": is_power,
            "has_pwr_flag": has_pwr_flag,
            "voltage_v": voltage_v,
            "target_z0_ohm": target_z0_ohm,
        }

    # Cryogenic 4 K Power & Bias Rails
    set_net("GND_4K", net_class="Cryo_PWR", is_power=True, has_pwr_flag=True, voltage_v=0.0)
    set_net("VDD_4K_1V2", net_class="Cryo_PWR", is_power=True, has_pwr_flag=True, voltage_v=1.2)
    set_net("VBIAS_POS_2V", net_class="Cryo_BIAS", is_power=True, has_pwr_flag=True, voltage_v=2.0)
    set_net("VBIAS_NEG_2V", net_class="Cryo_BIAS", is_power=True, has_pwr_flag=True, voltage_v=-2.0)

    # -----------------------------------------------------------------------
    # A. 300 K -> 4 K Input Loom Connectors & Thermalization Anchors (Left edge x = 10..24 mm)
    # -----------------------------------------------------------------------
    add_c(ComponentSpec(
        "J_300K_SPI", "OMNETICS_NANO_SPI_4K_IN", "Connector_PinHeader:HDR_2x4_2.54mm",
        12.0, 28.0,
        pins=auto_footprint_pads("HDR_2x4_2.54mm", [str(k) for k in range(1, 9)], {
            "1": "VDD_1V2", "2": "GND1", "3": "SPI_CLK", "4": "SPI_CS_N",
            "5": "SPI_MOSI", "6": "SPI_MISO", "7": "RST_N", "8": "GND2",
        }),
        bom_id="S6.10-03", epistemic_tag="{Aday-COTS}",
    ))
    add_c(ComponentSpec(
        "J_300K_BIAS", "OMNETICS_NANO_DAC_BIAS_IN", "Connector_PinHeader:HDR_2x4_2.54mm",
        12.0, 68.0,
        pins=auto_footprint_pads("HDR_2x4_2.54mm", [str(k) for k in range(1, 9)], {
            "1": "VBIAS_P", "2": "VBIAS_N", "3": "DAC_BUS0", "4": "DAC_BUS1",
            "5": "DAC_BUS2", "6": "DAC_BUS3", "7": "GND1", "8": "GND2",
        }),
        bom_id="S6.7-02", epistemic_tag="{Aday-COTS}",
    ))
    # 4 K OFHC Copper Cold-Stage Thermalization Anchors (S7.3-02)
    add_c(ComponentSpec("J_THERM_4K_A", "OFHC_4K_THERMAL_ANCHOR_A", "Connector_PinHeader:HDR_1x2_2.54mm", 12.0, 108.0, pins=auto_footprint_pads("HDR_1x2_2.54mm", ("1", "2")), bom_id="S7.3-02", epistemic_tag="{Pasif-COTS}"))
    add_c(ComponentSpec("J_THERM_4K_B", "OFHC_4K_THERMAL_ANCHOR_B", "Connector_PinHeader:HDR_1x2_2.54mm", 152.0, 108.0, pins=auto_footprint_pads("HDR_1x2_2.54mm", ("1", "2")), bom_id="S7.3-02", epistemic_tag="{Pasif-COTS}"))

    # Bulk C0G/NP0 Cryo Power Decoupling (zero X7R capacitance freeze-out at 4 K!)
    for idx_b, (cref, rnet, y_b) in enumerate((
        ("C_BULK_1V2", "VDD_4K_1V2", 16.0),
        ("C_BULK_VP", "VBIAS_POS_2V", 52.0),
        ("C_BULK_VN", "VBIAS_NEG_2V", 86.0),
    )):
        add_c(ComponentSpec(cref, "470nF_C0G_NP0_CRYO_1206", "Capacitor_SMD:C_1206_3216Metric", 26.0, y_b, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S7.3-02", epistemic_tag="{Pasif-COTS}"))
        conn(rnet, cref, 1); conn("GND_4K", cref, 2)

    # SPI 50 Ohm source damping / termination
    add_c(ComponentSpec("R_SPI_CLK", "49.9R_NICR_CRYO", "Resistor_SMD:R_0603_1608Metric", 26.0, 28.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S6.10-03", epistemic_tag="{Pasif-COTS}"))
    add_c(ComponentSpec("R_SPI_RST", "10k_NICR_CRYO", "Resistor_SMD:R_0603_1608Metric", 26.0, 36.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S6.10-03", epistemic_tag="{Pasif-COTS}"))

    conn("VDD_4K_1V2", "J_300K_SPI", 1); conn("GND_4K", "J_300K_SPI", 2); conn("GND_4K", "J_300K_SPI", 8)
    conn("SPI_CLK_IN", "J_300K_SPI", 3); conn("SPI_CLK_IN", "R_SPI_CLK", 1); conn("SPI_CLK_4K", "R_SPI_CLK", 2)
    conn("SPI_CS_N_4K", "J_300K_SPI", 4); conn("SPI_MOSI_4K", "J_300K_SPI", 5); conn("SPI_MISO_4K", "J_300K_SPI", 6)
    conn("RST_N_4K", "J_300K_SPI", 7); conn("VDD_4K_1V2", "R_SPI_RST", 1); conn("RST_N_4K", "R_SPI_RST", 2)

    conn("VBIAS_POS_2V", "J_300K_BIAS", 1); conn("VBIAS_NEG_2V", "J_300K_BIAS", 2)
    conn("DAC_BUS0", "J_300K_BIAS", 3); conn("DAC_BUS1", "J_300K_BIAS", 4)
    conn("DAC_BUS2", "J_300K_BIAS", 5); conn("DAC_BUS3", "J_300K_BIAS", 6)
    conn("GND_4K", "J_300K_BIAS", 7); conn("GND_4K", "J_300K_BIAS", 8)
    conn("GND_4K", "J_THERM_4K_A", 1); conn("GND_4K", "J_THERM_4K_A", 2)
    conn("GND_4K", "J_THERM_4K_B", 1); conn("GND_4K", "J_THERM_4K_B", 2)

    for n50 in ("SPI_CLK_4K", "SPI_MOSI_4K", "SPI_CS_N_4K", "SPI_MISO_4K"):
        set_net(n50, net_class="Cryo_SPI_50", target_z0_ohm=50.0)

    # -----------------------------------------------------------------------
    # B. 8x SKY130 4 K Crossbar Mux Chip Carriers (8 x 121 = 968 DC Gates, S7.3-01 / S6.10-03)
    #    Arranged in a clean 2x4 cryogenic grid (x = 46 & 68 mm, y = 20, 46, 72, 98 mm)
    # -----------------------------------------------------------------------
    mux_pdefs = [
        ("1", "VDD_1V2", "power_in"), ("2", "GND_4K", "power_in"),
        ("3", "VBIAS_P", "power_in"), ("4", "VBIAS_N", "power_in"),
        ("5", "SPI_CLK", "input"), ("6", "SPI_CS_N", "input"),
        ("7", "SPI_DIN", "input"), ("8", "SPI_DOUT", "output"),
        ("9", "RST_N", "input"), ("10", "DAC_IN", "input"),
        ("11", "GATE_BANK_OUT", "output"), ("12", "GND2", "power_in"),
    ]
    for m in range(8):
        col = m // 4
        row = m % 4
        xm = 46.0 + col * 24.0
        ym = 20.0 + row * 26.0
        mref = f"U_MUX{m}"
        add_c(ComponentSpec(
            mref, f"SKY130_4K_CROSSBAR_121G_M{m}", "Package_BGA:SKY130_CRYO_CARRIER_12P",
            xm, ym, pins=_grid_pins(mux_pdefs, cols=4, pitch_mm=1.60, pad_mm=0.55),
            mpn="SKY130-CRYO-MUX121-4K", bom_id="S7.3-01", epistemic_tag="{Ozel-Uretim}",
        ))
        # Per-chip cryo C0G/NP0 100 nF local decoupling (no X7R freeze-out!)
        cref = f"C_MUX{m}_1V2"
        add_c(ComponentSpec(cref, "100nF_C0G_NP0_0603", "Capacitor_SMD:C_0603_1608Metric", xm, ym + 9.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.3-02", epistemic_tag="{Pasif-COTS}"))
        conn("VDD_4K_1V2", cref, 1); conn("GND_4K", cref, 2)

        conn("VDD_4K_1V2", mref, 1); conn("GND_4K", mref, 2); conn("GND_4K", mref, 12)
        conn("VBIAS_POS_2V", mref, 3); conn("VBIAS_NEG_2V", mref, 4)
        conn("SPI_CLK_4K", mref, 5); conn("SPI_CS_N_4K", mref, 6); conn("RST_N_4K", mref, 9)
        conn(f"DAC_BUS{m % 4}", mref, 10)
        # Daisy-chain SPI across all 8 SKY130 chips
        din_net = "SPI_MOSI_4K" if m == 0 else f"SPI_CHAIN_{m-1}_{m}"
        dout_net = "SPI_MISO_4K" if m == 7 else f"SPI_CHAIN_{m}_{m+1}"
        conn(din_net, mref, 7); conn(dout_net, mref, 8)
        conn(f"GATE_RAW_CH{m}", mref, 11)

    # -----------------------------------------------------------------------
    # C. 8-Channel 4 K / MXC 2-Stage RC + Eccosorb CR-124 RF Low-Pass Filter Bank (S6.7-02)
    #    Each channel: R1(1k 4K) -> C1(100n C0G) || C1HF(100p C0G) -> FB_ECCO(CR-124) ->
    #                  R2(2k MXC) -> C2(47n C0G) || C2HF(100p C0G) -> J_MXC_GATE
    # -----------------------------------------------------------------------
    add_c(ComponentSpec(
        "J_MXC_GATE_A", "OMNETICS_MXC_20MK_GATES_0_3", "Connector_PinHeader:HDR_2x4_2.54mm",
        152.0, 28.0,
        pins=auto_footprint_pads("HDR_2x4_2.54mm", [str(k) for k in range(1, 9)], {
            "1": "G0_MXC", "2": "GND0", "3": "G1_MXC", "4": "GND1",
            "5": "G2_MXC", "6": "GND2", "7": "G3_MXC", "8": "GND3",
        }),
        bom_id="S6.7-02", epistemic_tag="{Aday-COTS}",
    ))
    add_c(ComponentSpec(
        "J_MXC_GATE_B", "OMNETICS_MXC_20MK_GATES_4_7", "Connector_PinHeader:HDR_2x4_2.54mm",
        152.0, 78.0,
        pins=auto_footprint_pads("HDR_2x4_2.54mm", [str(k) for k in range(1, 9)], {
            "1": "G4_MXC", "2": "GND4", "3": "G5_MXC", "4": "GND5",
            "5": "G6_MXC", "6": "GND6", "7": "G7_MXC", "8": "GND7",
        }),
        bom_id="S6.7-02", epistemic_tag="{Aday-COTS}",
    ))
    for p_gnd in (2, 4, 6, 8):
        conn("GND_4K", "J_MXC_GATE_A", p_gnd)
        conn("GND_4K", "J_MXC_GATE_B", p_gnd)

    for ch in range(8):
        yc = 14.0 + ch * 12.2
        r1 = f"R1_4K_CH{ch}"
        c1 = f"C1_4K_CH{ch}"
        c1hf = f"C1HF_CH{ch}"
        fb = f"FB_ECCO_CH{ch}"
        r2 = f"R2_MXC_CH{ch}"
        c2 = f"C2_MXC_CH{ch}"
        c2hf = f"C2HF_CH{ch}"

        add_c(ComponentSpec(r1, "1.0k_0.1pct_NICR_4K", "Resistor_SMD:R_0603_1608Metric", 90.0, yc, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S6.7-02", epistemic_tag="{Pasif-COTS}"))
        add_c(ComponentSpec(c1, "100nF_C0G_NP0_4K", "Capacitor_SMD:C_0805_2012Metric", 98.0, yc - 2.3, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S6.7-02", epistemic_tag="{Pasif-COTS}"))
        add_c(ComponentSpec(c1hf, "100pF_C0G_HF_0402", "Capacitor_SMD:C_0402_1005Metric", 98.0, yc + 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S6.7-02", epistemic_tag="{Pasif-COTS}"))
        add_c(ComponentSpec(fb, "ECCOSORB_CR124_RF_LPF", "Inductor_SMD:L_1206_3216Metric", 109.0, yc, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S6.7-02", epistemic_tag="{Ozel-Uretim}"))
        add_c(ComponentSpec(r2, "2.0k_0.1pct_NICR_MXC", "Resistor_SMD:R_0603_1608Metric", 120.0, yc, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S6.7-02", epistemic_tag="{Pasif-COTS}"))
        add_c(ComponentSpec(c2, "47nF_C0G_NP0_MXC", "Capacitor_SMD:C_0805_2012Metric", 129.0, yc - 2.3, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S6.7-02", epistemic_tag="{Pasif-COTS}"))
        add_c(ComponentSpec(c2hf, "100pF_C0G_HF_0402", "Capacitor_SMD:C_0402_1005Metric", 129.0, yc + 2.3, pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S6.7-02", epistemic_tag="{Pasif-COTS}"))

        conn(f"GATE_RAW_CH{ch}", r1, 1); conn(f"GATE_S1_CH{ch}", r1, 2)
        conn(f"GATE_S1_CH{ch}", c1, 1); conn("GND_4K", c1, 2)
        conn(f"GATE_S1_CH{ch}", c1hf, 1); conn("GND_4K", c1hf, 2)
        conn(f"GATE_S1_CH{ch}", fb, 1); conn(f"GATE_ECCO_CH{ch}", fb, 2)
        conn(f"GATE_ECCO_CH{ch}", r2, 1); conn(f"GATE_MXC_CH{ch}", r2, 2)
        conn(f"GATE_MXC_CH{ch}", c2, 1); conn("GND_4K", c2, 2)
        conn(f"GATE_MXC_CH{ch}", c2hf, 1); conn("GND_4K", c2hf, 2)
        if ch < 4:
            conn(f"GATE_MXC_CH{ch}", "J_MXC_GATE_A", 1 + ch * 2)
        else:
            conn(f"GATE_MXC_CH{ch}", "J_MXC_GATE_B", 1 + (ch - 4) * 2)

    # -----------------------------------------------------------------------
    # D. Thermal-Stitching Vias, Planes & Full Physical Auto-Routing (100% Pad-to-Pad)
    # -----------------------------------------------------------------------
    # Cryogenic thermalization & GND stitching via fence around filter bay and chip carriers
    for vx in (8.0, 36.0, 82.0, 140.0, 158.0):
        for vy in (6.0, 118.0):
            vias.append(ViaSpec("GND_4K", vx, vy, diameter_mm=0.70, drill_mm=0.35))

    rect_inner = ((2.0, 2.0), (163.0, 2.0), (163.0, 123.0), (2.0, 123.0))
    zones = (
        ZoneSpec("GND_4K", "In1.Cu", rect_inner, clearance_mm=0.20),
        ZoneSpec("VDD_4K_1V2", "In2.Cu", ((8.0, 8.0), (82.0, 8.0), (82.0, 114.0), (8.0, 114.0)), clearance_mm=0.20),
    )

    nets = tuple(
        NetSpec(
            name=nname,
            nodes=tuple(sorted(set(nodes))),
            net_class=net_meta.get(nname, {}).get("net_class", "Default"),
            is_power=net_meta.get(nname, {}).get("is_power", False),
            has_pwr_flag=net_meta.get(nname, {}).get("has_pwr_flag", False),
            voltage_v=net_meta.get(nname, {}).get("voltage_v", 0.0),
            target_z0_ohm=net_meta.get(nname, {}).get("target_z0_ohm"),
        )
        for nname, nodes in sorted(nets_dict.items())
    )

    spec = BoardSpec(
        name="cryo_cmos_4k_carrier",
        title="Cryo-CMOS 4 K Carrier (968-Gate SKY130 Mux + MXC RC/Eccosorb Filter) 4L",
        rev="v1.0",
        bom_ids=("S6.10-03", "S6.7-02", "S7.3-02", "S7.3-01"),
        width_mm=165.0,
        height_mm=125.0,
        stackup=stackup,
        components=tuple(comps),
        nets=nets,
        traces=tuple(traces),
        vias=tuple(vias),
        zones=zones,
        rules=DesignRules(min_trace_width_mm=0.127, min_clearance_mm=0.127, impedance_tol_pct=5.0),
        epistemic_meta={
            **DEFAULT_EPISTEMIC_META,
            "operating_temp_K": 4.0,
            "mxc_filter_stage_temp_K": 0.02,
            "total_multiplexed_dc_gates": 968,
            "surface_code_nodes_L11": 121,
            "gates_per_node": 8,
            "sky130_mux_dies_per_board": 8,
            "power_budget_4k_max_mW": 15.4,
            "stackup_material": "Rogers RO4350B / AlN-Cu-Invar-Cu Core (4-layer)",
        },
        notes=(
            f"50 Ohm SE SPI microstrip: w={w50_ms:.4f} mm -> Z0={calc_microstrip_z0(w50_ms, 0.254, 0.035, 3.48):.2f} Ohm",
            "All cryogenic capacitors are C0G/NP0 dielectric to prevent Class-II X7R capacitance freeze-out at 4 K.",
            "L=11 FT surface code (121 nodes x 8 DC gates = 968 gates), <=15.4 mW @ 4 K budget (Exp131 / S6.10-03).",
        ),
    )
    return auto_route_board(spec, grid_mm=0.50, preserve_existing=True)


# ---------------------------------------------------------------------------
# 3. Live ngspice-47 4 K / 20 mK Filter, Noise & 968-Gate Power Deck
# ---------------------------------------------------------------------------

FILTER_PARAMS: dict[str, float] = {
    "r_dac_300k_ohm": 3400.0,  # 7.50 nV/rtHz 300 K DAC floor (AD5791 class)
    "r_mux_on_ohm": 250.0,     # 4 K SKY130 transmission-gate R_on
    "r1_4k_ohm": 1000.0,
    "c_par_r1_f": 0.05e-12,    # Realistic 0603 resistor body stray C
    "c1_4k_f": 100.0e-9,
    "esr1_ohm": 0.050,
    "esl1_h": 0.60e-9,
    "c1hf_f": 100.0e-12,
    "esr1hf_ohm": 0.080,
    "esl1hf_h": 0.25e-9,
    # 3-section Eccosorb CR-124 magnetically-loaded lossy RF absorber ladder
    "r_ecco_dc_ohm": 5.0,
    "l_ecco_sec_h": 60.0e-9,
    "r_ecco_loss_ohm": 350.0,
    "c_ecco_sec_f": 4.0e-12,
    "esl_ecco_c_h": 0.20e-9,
    # Stage 2 (MXC 20 mK)
    "r2_mxc_ohm": 2000.0,
    "c_par_r2_f": 0.05e-12,
    "c2_mxc_f": 47.0e-9,
    "esr2_ohm": 0.050,
    "esl2_h": 0.60e-9,
    "c2hf_f": 100.0e-12,
    "esr2hf_ohm": 0.080,
    "esl2hf_h": 0.25e-9,
    "c_gate_load_f": 2.0e-12,
    "r_gate_leak_ohm": 100.0e6,
}


def render_cryo_4k_ngspice_deck() -> str:
    """Emit native ngspice-47 deck with .temp -269.15 (4 K) + 20 mK MXC + 968-gate crossbar power."""
    p = FILTER_PARAMS
    return f"""* Cryo-CMOS 4 K Carrier — 4 K / 20 mK 2-Stage RC + Eccosorb CR-124 Filter & 968-Gate Crossbar Power
* Native ngspice-47 deck (zero PSpice syntax) — M0/M1 DESIGN_ONLY
* BOM: S6.10-03 (968-gate 4 K SKY130 mux, <=15.4 mW), S6.7-02 (RC/Eccosorb <0.5 uV/rtHz), S7.3-01/02
* Global simulation temperature: 4.00 K (-269.15 C); MXC stage: 20 mK (-273.13 C); 300 K DAC ref: +26.85 C

.temp -269.15

* ===========================================================================
* SUBCIRCUIT A: 4 K / MXC (20 mK) 2-Stage RC + Eccosorb CR-124 DC Gate Filter
* ===========================================================================
* Stimulus: AC=1 V for RF attenuation sweep; TRAN 0 -> 1.0 V Stark gate step at t=10 us
Vgate_in n_in_src 0 DC 0 AC 1 PULSE(0 1.0 10u 100n 100n 5m 10m)

* Upstream 300 K DAC noise floor (AD5791 class: 7.50 nV/rtHz via 3.4 kOhm @ 300 K, noiseless unity buffer)
Rdac_n n_in_src n_dac_n {p['r_dac_300k_ohm']} temp=26.85
Edac_buf n_mux_in 0 n_dac_n 0 1.0

* 4 K SKY130 Crossbar Mux Switch On-Resistance (4.00 K global temp)
Rmux_on n_mux_in n_r1_in {p['r_mux_on_ohm']}

* Stage 1 (4 K): R1 = 1.0 kOhm (w/ 0.05 pF body stray) + C1 = 100 nF C0G || 100 pF HF bypass
R1_4k   n_r1_in n_s1 {p['r1_4k_ohm']}
Cpar_r1 n_r1_in n_s1 {p['c_par_r1_f']:.6e}
C1_4k   n_s1    n_c1r {p['c1_4k_f']:.6e}
Resr1   n_c1r   n_c1l {p['esr1_ohm']}
Lesl1   n_c1l   0     {p['esl1_h']:.6e}
C1_hf   n_s1    n_c1hfr {p['c1hf_f']:.6e}
Resr1h  n_c1hfr n_c1hfl {p['esr1hf_ohm']}
Lesl1h  n_c1hfl 0       {p['esl1hf_h']:.6e}

* Mid-Stage: 3-Section Eccosorb CR-124 Magnetically-Loaded RF Absorber Ladder (4 K -> MXC)
Re_dc1 n_s1   ne1_a {p['r_ecco_dc_ohm']}
Le_1   ne1_a  ne1   {p['l_ecco_sec_h']:.6e}
Re_ls1 ne1_a  ne1   {p['r_ecco_loss_ohm']}
Ce_1   ne1    ne1_l {p['c_ecco_sec_f']:.6e}
Lce_1  ne1_l  0     {p['esl_ecco_c_h']:.6e}

Re_dc2 ne1    ne2_a {p['r_ecco_dc_ohm']}
Le_2   ne2_a  ne2   {p['l_ecco_sec_h']:.6e}
Re_ls2 ne2_a  ne2   {p['r_ecco_loss_ohm']}
Ce_2   ne2    ne2_l {p['c_ecco_sec_f']:.6e}
Lce_2  ne2_l  0     {p['esl_ecco_c_h']:.6e}

Re_dc3 ne2    ne3_a {p['r_ecco_dc_ohm']}
Le_3   ne3_a  n_ecco {p['l_ecco_sec_h']:.6e}
Re_ls3 ne3_a  n_ecco {p['r_ecco_loss_ohm']}
Ce_3   n_ecco ne3_l  {p['c_ecco_sec_f']:.6e}
Lce_3  ne3_l  0      {p['esl_ecco_c_h']:.6e}

* Stage 2 (MXC 20 mK, temp=-273.13 C): R2 = 2.0 kOhm (w/ 0.05 pF stray) + C2 = 47 nF C0G || 100 pF HF
R2_mxc  n_ecco  n_gate_mxc {p['r2_mxc_ohm']} temp=-273.13
Cpar_r2 n_ecco  n_gate_mxc {p['c_par_r2_f']:.6e}
C2_mxc  n_gate_mxc n_c2r   {p['c2_mxc_f']:.6e}
Resr2   n_c2r   n_c2l      {p['esr2_ohm']} temp=-273.13
Lesl2   n_c2l   0          {p['esl2_h']:.6e}
C2_hf   n_gate_mxc n_c2hfr {p['c2hf_f']:.6e}
Resr2h  n_c2hfr n_c2hfl    {p['esr2hf_ohm']} temp=-273.13
Lesl2h  n_c2hfl 0          {p['esl2hf_h']:.6e}

* Stark / M4 / SET Cryogenic Gate Electrode Load (20 mK)
Cgate_mxc n_gate_mxc 0 {p['c_gate_load_f']:.6e}
Rgate_mxc n_gate_mxc 0 {p['r_gate_leak_ohm']:.6e} temp=-273.13

* Parallel Intrinsic-Only Filter Copy (0 Ohm noiseless input, isolating pure 4 K + 20 mK thermal noise!)
Vin_intr  ni_in  0 DC 0 AC 1
Rmux_i    ni_in  ni_r1 {p['r_mux_on_ohm']}
R1_i      ni_r1  ni_s1 {p['r1_4k_ohm']}
C1_i      ni_s1  0     {p['c1_4k_f']:.6e}
R2_i      ni_s1  ni_out {p['r2_mxc_ohm']} temp=-273.13
C2_i      ni_out 0     {p['c2_mxc_f']:.6e}

* ===========================================================================
* SUBCIRCUIT B: 968-Gate SKY130 4 K Crossbar Mux Static + Dynamic Power Model
*   L=11 Surface Code: 121 nodes x 8 gates = 968 gates across 8 SKY130 dies
*   4 K Core Supply VDD_4K = 1.2 V; Analog Gate-Hold Bias VBIAS = 2.0 V
*   Budget: P_total_4K <= 15.4 mW (Exp131 / BOM S6.10-03)
* ===========================================================================
Vvdd_4k  vdd_4k  0 DC 1.2
Vbias_4k vbias_4k 0 DC 2.0

* Static 4 K core + SPI/bandgap overhead across 8 dies: 1.12 mW @ 1.2 V (0.9333 mA)
Rstat_spi vdd_4k 0 1.2857k
* Static 968-gate sample-and-hold bias buffers: 968 x 11.2 uW = 10.8416 mW @ 2.0 V (5.4208 mA)
Rstat_968 vbias_4k 0 368.95

* Dynamic 968-gate SKY130 CMOS crossbar refresh bank (4 K threshold-shifted |Vto|=0.60 V)
* Scaled 968-gate total switched capacitance: 968 x 45 pF = 43.56 nF refreshed at f_ref = 25 kHz
* Analytical P_dyn = C_tot * V^2 * f = 43.56e-9 * 1.44 * 25e3 = 1.568 mW
.model NMOS_SKY4K NMOS(LEVEL=1 VTO=0.60 KP=4.5m LAMBDA=0.01)
.model PMOS_SKY4K PMOS(LEVEL=1 VTO=-0.60 KP=2.2m LAMBDA=0.01)
Vref_clk clk_ref 0 PULSE(0 1.2 1u 50n 50n 19.95u 40u)
Mdyn_p dyn_out clk_ref vdd_4k vdd_4k PMOS_SKY4K W=2000u L=1u
Mdyn_n dyn_out clk_ref 0      0      NMOS_SKY4K W=1000u L=1u
Cdyn_968 dyn_out 0 43.56n

.control
set noaskquit

* 1) AC Transfer Function: 1 Hz .. 2 GHz (verify >60 dB RF attenuation @ 1 GHz & -3 dB BW)
ac dec 80 1 2G
meas ac f_3db_hz WHEN vm(n_gate_mxc)=0.707107 FALL=1
meas ac atten_100khz_db FIND vdb(n_gate_mxc) AT=100k
meas ac atten_10mhz_db  FIND vdb(n_gate_mxc) AT=10Meg
meas ac atten_100mhz_db FIND vdb(n_gate_mxc) AT=100Meg
meas ac atten_1ghz_db   FIND vdb(n_gate_mxc) AT=1G

* 2) Noise Analysis (Total: 300 K DAC + 4 K stage + 20 mK MXC stage, 1 Hz .. 1 MHz)
noise v(n_gate_mxc) Vgate_in dec 40 1 1Meg
setplot noise1
let noise_10hz_v_rthz = onoise_spectrum[40]
let noise_peak_v_rthz = vecmax(onoise_spectrum)
print noise_10hz_v_rthz
print noise_peak_v_rthz
setplot noise2
let noise_rms_total_v = onoise_total
print noise_rms_total_v

* 3) Noise Analysis (Intrinsic 4 K + 20 mK filter thermal noise only, 1 Hz .. 1 MHz)
noise v(ni_out) Vin_intr dec 40 1 1Meg
setplot noise3
let noise_intr_10hz_v_rthz = onoise_spectrum[40]
print noise_intr_10hz_v_rthz
setplot noise4
let noise_intr_rms_v = onoise_total
print noise_intr_rms_v

* 4) Transient Analysis A: 968-Gate Crossbar 4 K Power Dissipation (5 full refresh cycles = 200 us)
tran 200n 240u
let p_4k_core_w = -1.2 * i(Vvdd_4k)
let p_4k_bias_w = -2.0 * i(Vbias_4k)
let p_4k_tot_w  = p_4k_core_w + p_4k_bias_w
meas tran p_4k_core_avg_w AVG p_4k_core_w FROM=40u TO=240u
meas tran p_4k_bias_avg_w AVG p_4k_bias_w FROM=40u TO=240u
meas tran p_4k_total_avg_w AVG p_4k_tot_w FROM=40u TO=240u

* 5) Transient Analysis B: DC Stark Gate Step Response & 0.1% Settling Time (0 -> 1.0 V)
tran 2u 3.0m
meas tran t_rise_10_90_s TRIG v(n_gate_mxc) VAL=0.10 RISE=1 TARG v(n_gate_mxc) VAL=0.90 RISE=1
meas tran t_settle_0p1pct_abs WHEN v(n_gate_mxc)=0.999 RISE=1
let t_settle_0p1pct_s = t_settle_0p1pct_abs - 10u
print t_settle_0p1pct_s

quit 0
.endc
.end
"""


def run_cryo_filter_mna_crosscheck() -> dict[str, Any]:
    """Independent Python MNA AC transfer cross-check of 4 K / MXC RC + Eccosorb filter."""
    p = FILTER_PARAMS
    mna = MnaCircuit()
    mna.add_vsource("n_mux_in", "0", ac=1.0)
    mna.add_resistor("n_mux_in", "n_r1_in", p["r_mux_on_ohm"])

    # Stage 1 (4 K)
    mna.add_resistor("n_r1_in", "n_s1", p["r1_4k_ohm"])
    mna.add_capacitor("n_r1_in", "n_s1", p["c_par_r1_f"])
    mna.add_capacitor("n_s1", "n_c1r", p["c1_4k_f"])
    mna.add_resistor("n_c1r", "n_c1l", p["esr1_ohm"])
    mna.add_inductor("n_c1l", "0", p["esl1_h"])
    mna.add_capacitor("n_s1", "n_c1hfr", p["c1hf_f"])
    mna.add_resistor("n_c1hfr", "n_c1hfl", p["esr1hf_ohm"])
    mna.add_inductor("n_c1hfl", "0", p["esl1hf_h"])

    # 3-section Eccosorb CR-124 ladder
    prev = "n_s1"
    for k, nxt in ((1, "ne1"), (2, "ne2"), (3, "n_ecco")):
        mid = f"ne{k}_a"
        mna.add_resistor(prev, mid, p["r_ecco_dc_ohm"])
        mna.add_inductor(mid, nxt, p["l_ecco_sec_h"])
        mna.add_resistor(mid, nxt, p["r_ecco_loss_ohm"])
        mna.add_capacitor(nxt, f"ne{k}_l", p["c_ecco_sec_f"])
        mna.add_inductor(f"ne{k}_l", "0", p["esl_ecco_c_h"])
        prev = nxt

    # Stage 2 (MXC 20 mK)
    mna.add_resistor("n_ecco", "n_gate_mxc", p["r2_mxc_ohm"])
    mna.add_capacitor("n_ecco", "n_gate_mxc", p["c_par_r2_f"])
    mna.add_capacitor("n_gate_mxc", "n_c2r", p["c2_mxc_f"])
    mna.add_resistor("n_c2r", "n_c2l", p["esr2_ohm"])
    mna.add_inductor("n_c2l", "0", p["esl2_h"])
    mna.add_capacitor("n_gate_mxc", "n_c2hfr", p["c2hf_f"])
    mna.add_resistor("n_c2hfr", "n_c2hfl", p["esr2hf_ohm"])
    mna.add_inductor("n_c2hfl", "0", p["esl2hf_h"])
    mna.add_capacitor("n_gate_mxc", "0", p["c_gate_load_f"])
    mna.add_resistor("n_gate_mxc", "0", p["r_gate_leak_ohm"])

    freqs = [100e3, 10e6, 100e6, 1e9]
    sol = mna.solve_ac(freqs)["n_gate_mxc"]
    dbs = [float(20.0 * math.log10(max(abs(v), 1e-30))) for v in sol]

    # Analytical Nyquist noise spot density at 10 Hz:
    #   300 K DAC (3.4 kOhm) + 4 K (R_mux=250 + R1=1000) + 20 mK (R2=2000)
    en_dac = math.sqrt(4.0 * K_B * 300.0 * p["r_dac_300k_ohm"])
    en_4k = math.sqrt(4.0 * K_B * 4.0 * (p["r_mux_on_ohm"] + p["r1_4k_ohm"]))
    en_20mk = math.sqrt(4.0 * K_B * 0.02 * p["r2_mxc_ohm"])
    en_tot_nv = math.hypot(en_dac, math.hypot(en_4k, en_20mk)) * 1e9
    en_intr_nv = math.hypot(en_4k, en_20mk) * 1e9
    return {
        "mna_atten_100khz_db": round(dbs[0], 3),
        "mna_atten_10mhz_db": round(dbs[1], 3),
        "mna_atten_100mhz_db": round(dbs[2], 3),
        "mna_atten_1ghz_db": round(dbs[3], 3),
        "analytical_total_noise_10hz_nV_rtHz": round(en_tot_nv, 4),
        "analytical_intrinsic_4k_20mk_noise_nV_rtHz": round(en_intr_nv, 4),
    }


def build_and_verify_all(out_dir: Path | None = None) -> dict[str, Any]:
    """Generate cryo_cmos_4k_carrier KiCad 8 files, run ERC/DRC + live 4 K ngspice-47 + MNA."""
    od = out_dir or OUT_DIR
    od.mkdir(parents=True, exist_ok=True)

    spec = build_cryo_4k_carrier()
    board_rep = verify_board_bundle(spec, od)

    cir_path = od / "cryo_4k_gate_filter.cir"
    cir_path.write_text(render_cryo_4k_ngspice_deck(), encoding="utf-8")
    spice_res = run_ngspice(cir_path, workdir=od)

    m = spice_res.metrics
    f_3db_hz = m.get("f_3db_hz", 0.0)
    atten_100m_db = m.get("atten_100mhz_db", 0.0)
    atten_1g_db = m.get("atten_1ghz_db", 0.0)
    noise_10hz_uv = m.get("noise_10hz_v_rthz", float("inf")) * 1e6
    noise_peak_uv = m.get("noise_peak_v_rthz", float("inf")) * 1e6
    noise_rms_uv = m.get("noise_rms_total_v", float("inf")) * 1e6
    noise_intr_nv = m.get("noise_intr_10hz_v_rthz", float("inf")) * 1e9
    p_4k_core_mw = m.get("p_4k_core_avg_w", float("inf")) * 1e3
    p_4k_bias_mw = m.get("p_4k_bias_avg_w", float("inf")) * 1e3
    p_4k_tot_mw = m.get("p_4k_total_avg_w", float("inf")) * 1e3
    t_rise_us = m.get("t_rise_10_90_s", float("inf")) * 1e6
    t_settle_ms = m.get("t_settle_0p1pct_s", float("inf")) * 1e3

    mna = run_cryo_filter_mna_crosscheck()
    atten_1g_diff_db = abs(atten_1g_db - mna["mna_atten_1ghz_db"])

    checks = {
        "sexpr_valid": board_rep["sexpr_valid"],
        "erc_zero_errors": bool(board_rep["erc"]["passed"] and len(board_rep["erc"]["errors"]) == 0),
        "drc_zero_errors": bool(board_rep["drc"]["passed"] and len(board_rep["drc"]["errors"]) == 0),
        "all_nets_physically_routed": bool(
            board_rep["drc"]["unrouted_net_count"] == 0
            and board_rep["drc"]["unconnected_items"] == 0
            and board_rep["drc"]["track_dangling_count"] == 0
            and board_rep["drc"]["routed_net_count"] == board_rep["drc"]["total_multi_pin_nets"]
        ),
        "stackup_4_copper_layers": board_rep["drc"]["stackup_summary"]["copper_layers"] == 4,
        "spi_50ohm_impedance_pass": bool(
            len(board_rep["drc"]["impedance_checks"]) >= 4
            and all(ic["passed"] for ic in board_rep["drc"]["impedance_checks"])
        ),
        "ngspice_ok": spice_res.ok,
        "rf_atten_1ghz_gt_60db": bool(atten_1g_db <= -60.0),
        "inband_noise_lt_0p5_uv_rthz": bool(0.0 < noise_peak_uv < 0.5 and 0.0 < noise_10hz_uv < 0.5),
        "settling_time_clean_lt_5ms": bool(0.0 < t_settle_ms < 5.0),
        "crossbar_968g_power_le_15p4mw": bool(0.0 < p_4k_tot_mw <= 15.4),
        "mna_ngspice_1ghz_parity_lt_0p5db": bool(atten_1g_diff_db < 0.5),
    }

    report = {
        "module": "cryo_cmos_4k_carrier",
        "bom_ids_covered": list(spec.bom_ids),
        "epistemic_meta": {
            **DEFAULT_EPISTEMIC_META,
            "simulation_engine": spice_res.version,
            "cryo_stage_temp_K": 4.0,
            "mxc_stage_temp_K": 0.02,
        },
        "board": board_rep,
        "ngspice_simulation": {
            "cir_file": cir_path.name,
            "version": spice_res.version,
            "ok": spice_res.ok,
            "errors": spice_res.errors,
            "warnings": spice_res.warnings,
            "raw_metrics": m,
            "derived": {
                "f_3db_Hz": round(f_3db_hz, 3),
                "atten_100khz_dB": round(m.get("atten_100khz_db", 0.0), 3),
                "atten_10mhz_dB": round(m.get("atten_10mhz_db", 0.0), 3),
                "atten_100mhz_dB": round(atten_100m_db, 3),
                "atten_1ghz_dB": round(atten_1g_db, 3),
                "noise_10hz_total_uV_rtHz": round(noise_10hz_uv, 6),
                "noise_10hz_total_nV_rtHz": round(noise_10hz_uv * 1e3, 4),
                "noise_peak_total_uV_rtHz": round(noise_peak_uv, 6),
                "noise_intrinsic_4k_20mk_nV_rtHz": round(noise_intr_nv, 4),
                "noise_integrated_rms_uV": round(noise_rms_uv, 5),
                "step_rise_10_90_us": round(t_rise_us, 3),
                "step_settle_0p1pct_ms": round(t_settle_ms, 4),
                "p_4k_core_plus_dyn_mW": round(p_4k_core_mw, 4),
                "p_4k_968g_bias_mW": round(p_4k_bias_mw, 4),
                "p_4k_968g_total_mW": round(p_4k_tot_mw, 4),
                "p_4k_budget_max_mW": 15.4,
            },
        },
        "mna_crosscheck": {
            **mna,
            "atten_1ghz_vs_ngspice_diff_dB": round(atten_1g_diff_db, 4),
        },
        "checks": checks,
        "all_passed": all(checks.values()),
    }

    (od / "cryo_cmos_4k_carrier_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    rep = build_and_verify_all()
    b = rep["board"]
    d = rep["ngspice_simulation"]["derived"]
    print("=== CRYO-CMOS 4 K CARRIER VERIFICATION ===")
    print(
        f"  PCB: layers={b['drc']['stackup_summary']['copper_layers']}L, "
        f"comps={b['erc']['component_count']}, nets={b['erc']['net_count']}, "
        f"routed={b['drc']['routed_net_count']}/{b['drc']['total_multi_pin_nets']}, "
        f"unconn={b['drc']['unconnected_items']}, dangling={b['drc']['track_dangling_count']}, "
        f"segs={b['drc']['segment_count']}, vias={b['drc']['via_count']}, "
        f"ERC_err={len(b['erc']['errors'])}, DRC_err={len(b['drc']['errors'])}, "
        f"Z0_checks={len(b['drc']['impedance_checks'])}"
    )
    if b["erc"]["errors"]:
        print("  ERC ERRORS:", b["erc"]["errors"][:8])
    if b["drc"]["errors"]:
        print("  DRC ERRORS:", b["drc"]["errors"][:8])
    print(
        f"  ngspice ({rep['ngspice_simulation']['version']}): ok={rep['ngspice_simulation']['ok']} | "
        f"f_3dB={d['f_3db_Hz']} Hz | atten@1GHz={d['atten_1ghz_dB']} dB | "
        f"noise@10Hz={d['noise_10hz_total_nV_rtHz']} nV/rtHz ({d['noise_10hz_total_uV_rtHz']} uV/rtHz, "
        f"intr={d['noise_intrinsic_4k_20mk_nV_rtHz']} nV/rtHz) | RMS={d['noise_integrated_rms_uV']} uVrms | "
        f"settle(0.1%)={d['step_settle_0p1pct_ms']} ms | P_4K(968g)={d['p_4k_968g_total_mW']} mW (<=15.4 mW)"
    )
    print(f"  MNA parity: 1 GHz diff={rep['mna_crosscheck']['atten_1ghz_vs_ngspice_diff_dB']} dB")
    print(f"  ALL_PASSED = {rep['all_passed']}")
    if not rep["all_passed"]:
        print("  FAILED:", [k for k, v in rep["checks"].items() if not v])
        if rep["ngspice_simulation"]["errors"]:
            print("  SPICE ERRORS:", rep["ngspice_simulation"]["errors"])
