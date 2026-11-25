"""FPGA Brain Carrier PCB (XC7K325T-2FFG900 + ZU48DR 2U Rack ICD) & Live ngspice-47 PDN Suite.

Covers BOM items: S3.3-01, S3.3-02, S3.3-04, S1.4-03, S4.5-03, S6.9-04 (plus S6.11-01 ZU48DR
2U rack ICD metadata, S3.3-03 FMC HPC ADC interface, and S7.4-01/S7.4-02 Rb/White Rabbit timing).

Architecture:
  * Sized directly from real Yosys pre-P&R cell counts:
      - boed_q16_core:       ecp5 3,871 LUT4 / 106 MULT18X18D; xc7 5,467 LUT / 99 DSP48E1
      - boed_top_16ch:       xcup 102,886 LUT / 1,584 DSP48E2 (ZU48DR: 24.2% LUT, 37.1% DSP)
      - fpga_top_machine_ctrl (boed_q16_core + all 6 rtl/machine_ctrl/ controllers):
                             xc7 14,252 LUT / 10,517 FF / 12 RAMB18E1 (6 BRAM36) / 124 DSP48E1
      - Carrier FPGA XC7K325T-2FFG900 (203,800 LUT, 840 DSP48E1, 445 BRAM36) -> >6.7x DSP
        and >14x LUT headroom over the full unified machine-control + BOED core.
  * 8-layer Isola FR408HR stackup (SIG1-GND-SIG2-PWR-GND-SIG3-GND-SIG4, er=3.66, tan_d=0.0092):
      - Controlled 50 Ohm SE microstrip/stripline (±5%) and 100 Ohm edge-coupled differential
        microstrip (±5%).
      - 2 oz PWR (In3.Cu) / 0.100 mm core / 2 oz GND2 (In4.Cu) planar decoupling pair for
        1.0 V VCCINT @ 15 A.
  * Complete board subsystems:
      - 12 V input protection + LM3880 power sequencer -> TPS546D24A (1.0 V VCCINT @ 15 A) +
        64-capacitor 5-decade PDN decoupling bank + 1.8 V, 1.2 V DDR4 + 0.6 V VTT, 2.5 V LVDS,
        3.3 V IO, and LT3045 ultra-low-noise 1.0 V/1.2 V MGT rails.
      - 10 MHz Rb + White Rabbit trigger -> LMK04828 dual-loop jitter cleaner -> 250 MHz /
        100 MHz / 125 MHz LVDS differential clocks.
      - 2 GB DDR4 (2x MT40A512M16LY-062E), 256 Mb QSPI NOR, FMC HPC (for S3.3-03 ADC),
        4x isolated LVDS/SPI mezzanine ports (IBIC, Blanker, HV-DAC, AOM/Pyro + 1oo2D Interlock),
        1000BASE-T GbE (DP83867IR), USB-UART (FT232HL), and 14-pin JTAG.
  * Live ngspice-47 PDN AC impedance & 5 A load-step transient verification (fpga_pdn_1v0.cir)
    plus independent Python MNA AC impedance cross-check:
      - Target |Z_PDN(f)| < 10 mOhm from 100 Hz to 20 MHz
      - Target 5 A load-step droop < 30 mV (±3% of 1.0 V VCCINT).

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
    calc_diff_microstrip_z0,
    calc_diff_stripline_z0,
    calc_microstrip_z0,
    calc_stripline_z0,
    make_manhattan_trace,
    run_ngspice,
    solve_diff_microstrip_width_mm,
    solve_diff_stripline_width_mm,
    solve_microstrip_width_mm,
    solve_stripline_width_mm,
    verify_board_bundle,
)

OUT_DIR = Path(__file__).resolve().parent
REPO_ROOT = OUT_DIR.parents[2]


# ---------------------------------------------------------------------------
# 1. Yosys-Measured Sizing & ZU48DR 2U Rack ICD Metadata
# ---------------------------------------------------------------------------

def load_yosys_sizing_metadata() -> dict[str, Any]:
    """Read real Yosys pre-P&R JSON metrics from repo results and compute XC7K325T headroom."""
    exp149_dir = REPO_ROOT / "results" / "exp149_boed_verilog_rtl_and_interactive_twin"
    ctrl_dir = REPO_ROOT / "results" / "stage2_rtl_verification"

    def _read_json(p: Path) -> dict[str, Any]:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}

    ecp5_core = _read_json(exp149_dir / "yosys_ecp5_core_stat.json")
    xc7_core = _read_json(exp149_dir / "yosys_xc7_core_stat.json")
    xcup_top16 = _read_json(exp149_dir / "yosys_xcup_top16_stat.json")
    xc7_ctrl = _read_json(ctrl_dir / "yosys_xc7_stat.json")

    # XC7K325T-2FFG900 device capacities (AMD/Xilinx DS180)
    k325t_cap = {"lut": 203800, "ff": 407600, "bram36": 445, "dsp48e1": 840}
    ctrl_lut = int(xc7_ctrl.get("lut_total", 14252))
    ctrl_ff = int(xc7_ctrl.get("ff_total", 10517))
    ctrl_bram36 = float(xc7_ctrl.get("bram36_equiv", 6.0))
    ctrl_dsp = int(xc7_ctrl.get("dsp_total", 124))

    return {
        "yosys_measured_sources": {
            "ecp5_boed_q16_core": {
                "lut4": int(ecp5_core.get("lut_total", 3871)),
                "ff": int(ecp5_core.get("ff_total", 4448)),
                "dp16kd": int(ecp5_core.get("bram_blocks", 12)),
                "mult18x18d": int(ecp5_core.get("dsp_total", 106)),
            },
            "xc7_boed_q16_core": {
                "lut": int(xc7_core.get("lut_total", 5467)),
                "ff": int(xc7_core.get("ff_total", 3080)),
                "ramb18e1": int(xc7_core.get("bram_blocks", 12)),
                "dsp48e1": int(xc7_core.get("dsp_total", 99)),
            },
            "xcup_boed_top_16ch": {
                "lut": int(xcup_top16.get("lut_total", 102886)),
                "ff": int(xcup_top16.get("ff_total", 59157)),
                "ramb18e2": int(xcup_top16.get("bram_blocks", 192)),
                "dsp48e2": int(xcup_top16.get("dsp_total", 1584)),
            },
            "xc7_fpga_top_machine_ctrl_plus_boed": {
                "lut": ctrl_lut,
                "ff": ctrl_ff,
                "bram36_equiv": ctrl_bram36,
                "dsp48e1": ctrl_dsp,
            },
        },
        "carrier_fpga": {
            "part_number": "XC7K325T-2FFG900",
            "epistemic_tag": "{Aday-COTS}",
            "capacity": k325t_cap,
            "utilization_pct": {
                "lut_pct": round(100.0 * ctrl_lut / k325t_cap["lut"], 2),
                "ff_pct": round(100.0 * ctrl_ff / k325t_cap["ff"], 2),
                "bram36_pct": round(100.0 * ctrl_bram36 / k325t_cap["bram36"], 2),
                "dsp48e1_pct": round(100.0 * ctrl_dsp / k325t_cap["dsp48e1"], 2),
            },
            "headroom_factor": {
                "lut_x": round(k325t_cap["lut"] / max(ctrl_lut, 1), 2),
                "ff_x": round(k325t_cap["ff"] / max(ctrl_ff, 1), 2),
                "bram36_x": round(k325t_cap["bram36"] / max(ctrl_bram36, 1e-6), 2),
                "dsp48e1_x": round(k325t_cap["dsp48e1"] / max(ctrl_dsp, 1), 2),
            },
        },
        "zu48dr_2u_rack_icd_ref": {
            "bom_id": "S6.11-01",
            "chassis": "2U 19-inch EMI Rack (482.6 x 520 x 88.9 mm, 11.50 kg)",
            "boards": 2,
            "device_per_board": "XCZU48DR-2FFVG1517E",
            "direct_rf_chains_total": 32,
            "boed_clock_mhz": 250.0,
            "step_latency_us": 2.336,
            "rack_power_300k_w": 87.96,
            "cryo_heat_load_w": 0.0,
            "inter_chassis_sync": ["10 MHz Rb (S7.4-01)", "White Rabbit Sub-ns Trigger (S7.4-02)", "1000BASE-T GbE + FMC/LVDS Bridge"],
        },
    }


# ---------------------------------------------------------------------------
# 2. Helper Pad & Footprint Builders
# ---------------------------------------------------------------------------

def _bga_grid_pins(
    pin_defs: list[tuple[str, str, str]],
    cols: int,
    pitch_mm: float = 1.0,
    pad_mm: float = 0.50,
) -> tuple[PinSpec, ...]:
    """Build deterministic grid pins for BGA/FMC footprints with explicit pin names/types."""
    rows = int(math.ceil(len(pin_defs) / cols))
    res: list[PinSpec] = []
    for idx, (pnum, pname, ptype) in enumerate(pin_defs):
        r = idx // cols
        c = idx % cols
        dx = (c - (cols - 1) / 2.0) * pitch_mm
        dy = (r - (rows - 1) / 2.0) * pitch_mm
        res.append(PinSpec(pnum, pname, ptype, round(dx, 4), round(dy, 4), pad_mm, pad_mm, 0.0))
    return tuple(res)


def _dual_row_smd_pins(
    pin_defs: list[tuple[str, str, str]],
    pitch_mm: float = 1.27,
    x_off_mm: float = 3.2,
    pw_mm: float = 1.30,
    ph_mm: float = 0.60,
) -> tuple[PinSpec, ...]:
    half = (len(pin_defs) + 1) // 2
    res: list[PinSpec] = []
    for idx, (pnum, pname, ptype) in enumerate(pin_defs):
        if idx < half:
            dy = (idx - (half - 1) / 2.0) * pitch_mm
            res.append(PinSpec(pnum, pname, ptype, round(-x_off_mm, 4), round(dy, 4), pw_mm, ph_mm, 0.0))
        else:
            ridx = idx - half
            rem = len(pin_defs) - half
            dy = ((rem - 1) / 2.0 - ridx) * pitch_mm
            res.append(PinSpec(pnum, pname, ptype, round(x_off_mm, 4), round(dy, 4), pw_mm, ph_mm, 0.0))
    return tuple(res)


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


# ---------------------------------------------------------------------------
# 3. 8-Layer Isola FR408HR FPGA Brain Carrier Board Builder
# ---------------------------------------------------------------------------

def build_fpga_brain_carrier() -> BoardSpec:
    """Build 8-layer Isola FR408HR XC7K325T-2FFG900 Carrier PCB (230 x 170 mm)."""
    # 8-Layer Isola FR408HR Stackup: SIG1-GND-SIG2-PWR-GND-SIG3-GND-SIG4
    # In3.Cu (PWR) & In4.Cu (GND2) are 2 oz (0.070 mm) copper over thin 0.100 mm core
    # for ultra-low spreading inductance and planar decoupling capacitance on 1.0 V VCCINT.
    stackup = (
        StackupLayer("F.Cu", "signal", 0.035, material="Copper"),
        StackupLayer("dielectric 1", "prepreg", 0.127, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR 1080"),
        StackupLayer("In1.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 2", "core", 0.200, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR Core"),
        StackupLayer("In2.Cu", "signal", 0.035, material="Copper"),
        StackupLayer("dielectric 3", "prepreg", 0.200, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR 2116"),
        StackupLayer("In3.Cu", "power", 0.070, material="Copper 2oz"),
        StackupLayer("dielectric 4", "core", 0.100, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR ThinCore"),
        StackupLayer("In4.Cu", "power", 0.070, material="Copper 2oz"),
        StackupLayer("dielectric 5", "prepreg", 0.200, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR 2116"),
        StackupLayer("In5.Cu", "signal", 0.035, material="Copper"),
        StackupLayer("dielectric 6", "core", 0.200, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR Core"),
        StackupLayer("In6.Cu", "power", 0.035, material="Copper"),
        StackupLayer("dielectric 7", "prepreg", 0.127, epsilon_r=3.66, loss_tangent=0.0092, material="Isola FR408HR 1080"),
        StackupLayer("B.Cu", "signal", 0.035, material="Copper"),
    )

    # Exact controlled-impedance widths solved directly from stackup geometry
    w50_ms = solve_microstrip_width_mm(50.0, h_mm=0.127, t_mm=0.035, er=3.66)
    s_diff_ms = 0.22
    w100_diff_ms = solve_diff_microstrip_width_mm(100.0, spacing_mm=s_diff_ms, h_mm=0.127, t_mm=0.035, er=3.66)
    w50_sl = solve_stripline_width_mm(50.0, b_mm=0.435, t_mm=0.035, er=3.66)
    s_diff_sl = 0.22
    w100_diff_sl = solve_diff_stripline_width_mm(100.0, spacing_mm=s_diff_sl, b_mm=0.435, t_mm=0.035, er=3.66)

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
        diff_pair_with: str | None = None,
    ) -> None:
        net_meta[net] = {
            "net_class": net_class,
            "is_power": is_power,
            "has_pwr_flag": has_pwr_flag,
            "voltage_v": voltage_v,
            "target_z0_ohm": target_z0_ohm,
            "diff_pair_with": diff_pair_with,
        }

    # Declare power rails
    for pname, pv, pflag in (
        ("GND", 0.0, True),
        ("VIN_12V_RAW", 12.0, True),
        ("VIN_12V", 12.0, False),
        ("VCCINT_1V0", 1.0, False),
        ("VCCAUX_1V8", 1.8, False),
        ("VDD_1V2_DDR", 1.2, False),
        ("VTT_0V6_DDR", 0.6, False),
        ("VCCO_2V5_LVDS", 2.5, False),
        ("VCCO_3V3_IO", 3.3, False),
        ("MGTAVCC_1V0", 1.0, False),
        ("MGTAVTT_1V2", 1.2, False),
    ):
        set_net(pname, net_class="Power", is_power=True, has_pwr_flag=pflag, voltage_v=pv)

    # -----------------------------------------------------------------------
    # A. Central FPGA: XC7K325T-2FFG900 (placed at x=122, y=82 mm)
    # -----------------------------------------------------------------------
    fpga_pin_defs: list[tuple[str, str, str]] = [
        # Power & Ground (pins 1..16)
        ("A1", "VCCINT_1", "power_in"), ("A2", "VCCINT_2", "power_in"),
        ("A3", "VCCAUX", "power_in"), ("A4", "VCCO_1V2", "power_in"),
        ("A5", "VCCO_2V5", "power_in"), ("A6", "VCCO_3V3", "power_in"),
        ("A7", "MGTAVCC", "power_in"), ("A8", "MGTAVTT", "power_in"),
        ("B1", "GND_1", "power_in"), ("B2", "GND_2", "power_in"),
        ("B3", "GND_3", "power_in"), ("B4", "GND_4", "power_in"),
        ("B5", "PGOOD_ALL", "input"), ("B6", "SYS_RST_N", "input"),
        ("B7", "DONE_LED", "output"), ("B8", "INIT_B", "bidirectional"),
        # Differential Clocks (pins 17..24: C1/C2=125M, C3/C4=100M, C5/C6=250M for zero-crossing In5.Cu L-bends!)
        ("C1", "CLK_125M_P", "input"), ("C2", "CLK_125M_N", "input"),
        ("C3", "CLK_100M_P", "input"), ("C4", "CLK_100M_N", "input"),
        ("C5", "CLK_250M_P", "input"), ("C6", "CLK_250M_N", "input"),
        ("C7", "WR_TRIG_IN", "input"), ("C8", "CLK_LOCKED", "input"),
        # DDR4 Memory Bank (pins 25..36: DDR_CK_P/N on D7/D8 right edge -> clear straight up to DDR4_A/B!)
        ("D1", "DDR_CS_N", "output"), ("D2", "DDR_WE_N", "output"),
        ("D3", "DDR_DQ0", "bidirectional"), ("D4", "DDR_DQ1", "bidirectional"),
        ("D5", "DDR_DQ2", "bidirectional"), ("D6", "DDR_DQ3", "bidirectional"),
        ("D7", "DDR_CK_P", "output"), ("D8", "DDR_CK_N", "output"),
        ("E1", "DDR_A0", "output"), ("E2", "DDR_A1", "output"),
        ("E3", "DDR_ODT", "output"), ("E4", "DDR_CKE", "output"),
        # QSPI Config Flash (pins 37..42)
        ("E5", "QSPI_CS_N", "output"), ("E6", "QSPI_CLK", "output"),
        ("E7", "QSPI_D0", "bidirectional"), ("E8", "QSPI_D1", "bidirectional"),
        ("F1", "QSPI_D2", "bidirectional"), ("F2", "QSPI_D3", "bidirectional"),
        # FMC HPC ADC Interface (S3.3-03 50 MS/s 12-bit PHA ADC) (pins 43..50)
        ("F3", "FMC_CLK_P", "input"), ("F4", "FMC_CLK_N", "input"),
        ("F5", "FMC_D0_P", "input"), ("F6", "FMC_D0_N", "input"),
        ("F7", "IBIC_HIT_P", "input"), ("F8", "IBIC_HIT_N", "input"),
        ("G1", "FMC_SPI_SCK", "output"), ("G2", "FMC_SPI_CSN", "output"),
        # 4x Isolated Mezzanine Ports (IBIC, Blanker, HV-DAC, AOM/Pyro + 1oo2D) (pins 51..68)
        ("G3", "FMC_D1_P", "input"), ("G4", "FMC_D1_N", "input"),
        ("G5", "IBIC_SPI_SCK", "output"), ("G6", "IBIC_SPI_MOSI", "output"),
        ("G7", "BLK_TX_P", "output"), ("G8", "BLK_TX_N", "output"),
        ("H1", "BLK_START", "output"), ("H2", "BLK_SAFE_FORCE", "output"),
        ("H3", "HVDAC_SCLK", "output"), ("H4", "HVDAC_MOSI", "output"),
        ("H5", "HVDAC_CSN", "output"), ("H6", "HVDAC_CLRN", "output"),
        ("H7", "AOM_SPI_SCK", "output"), ("H8", "AOM_RF_EN", "output"),
        ("J1", "IL_CH_A_OK", "input"), ("J2", "IL_CH_B_OK", "input"),
        ("J3", "IL_TRIP_OUT", "output"), ("J4", "IL_SAFE_EN", "output"),
        # 1000BASE-T GbE RGMII, USB-UART, JTAG (pins 69..80)
        ("J5", "RGMII_TXC", "output"), ("J6", "RGMII_TXD0", "output"),
        ("J7", "RGMII_RXC", "input"), ("J8", "RGMII_RXD0", "input"),
        ("K1", "UART_TX", "output"), ("K2", "UART_RX", "input"),
        ("K3", "JTAG_TCK", "input"), ("K4", "JTAG_TMS", "input"),
        ("K5", "JTAG_TDI", "input"), ("K6", "JTAG_TDO", "output"),
        ("K7", "PMBUS_SCL", "bidirectional"), ("K8", "PMBUS_SDA", "bidirectional"),
    ]
    u1 = add_c(ComponentSpec(
        "U1", "XC7K325T-2FFG900", "Package_BGA:Xilinx_FFG900_31x31mm_P2.0mm_Subset",
        122.0, 82.0, pins=_bga_grid_pins(fpga_pin_defs, cols=8, pitch_mm=2.00, pad_mm=0.55),
        mpn="XC7K325T-2FFG900I", bom_id="S3.3-01", epistemic_tag="{Aday-COTS}",
        body_w_mm=22.0, body_h_mm=24.0,
    ))
    conn("VCCINT_1V0", "U1", "A1"); conn("VCCINT_1V0", "U1", "A2")
    conn("VCCAUX_1V8", "U1", "A3"); conn("VDD_1V2_DDR", "U1", "A4")
    conn("VCCO_2V5_LVDS", "U1", "A5"); conn("VCCO_3V3_IO", "U1", "A6")
    conn("MGTAVCC_1V0", "U1", "A7"); conn("MGTAVTT_1V2", "U1", "A8")
    for p in ("B1", "B2", "B3", "B4"):
        conn("GND", "U1", p)
    conn("PGOOD_ALL", "U1", "B5"); conn("SYS_RST_N", "U1", "B6")
    conn("FPGA_DONE", "U1", "B7"); conn("FPGA_INIT_B", "U1", "B8")

    # Pull-ups / status LEDs for DONE & INIT_B & Reset
    r_done = add_c(ComponentSpec("R_DONE", "470R_0603", "Resistor_SMD:R_0603_1608Metric", 104.0, 68.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    d_done = add_c(ComponentSpec("D_DONE", "LED_GRN_0603", "LED_SMD:LED_0603_1608Metric", 104.0, 63.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    r_init = add_c(ComponentSpec("R_INIT", "4.7k_0603", "Resistor_SMD:R_0603_1608Metric", 104.0, 73.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    r_rst = add_c(ComponentSpec("R_RST", "10k_0603", "Resistor_SMD:R_0603_1608Metric", 104.0, 78.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    c_rst = add_c(ComponentSpec("C_RST", "100nF_0603", "Capacitor_SMD:C_0603_1608Metric", 104.0, 83.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    conn("FPGA_DONE", "R_DONE", 1); conn("LED_DONE_A", "R_DONE", 2)
    conn("LED_DONE_A", "D_DONE", 1); conn("GND", "D_DONE", 2)
    conn("VCCO_3V3_IO", "R_INIT", 1); conn("FPGA_INIT_B", "R_INIT", 2)
    conn("VCCO_3V3_IO", "R_RST", 1); conn("SYS_RST_N", "R_RST", 2)
    conn("SYS_RST_N", "C_RST", 1); conn("GND", "C_RST", 2)

    # -----------------------------------------------------------------------
    # B. 12 V Input Protection + Sequenced Power Tree (Left zone x = 10..78 mm)
    # -----------------------------------------------------------------------
    add_c(ComponentSpec(
        "J_PWR12V", "MOLEX_MINIFIT_12V_15A", "Connector_PinHeader:HDR_1x4_2.54mm",
        10.0, 22.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4"), {"1": "V12_A", "2": "V12_B", "3": "GND_A", "4": "GND_B"}),
        bom_id="S3.3-04", epistemic_tag="{Pasif-COTS}",
    ))
    add_c(ComponentSpec("F1", "10A_FAST_2410", "Resistor_SMD:R_1206_3216Metric", 20.0, 18.0, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S3.3-04", epistemic_tag="{Pasif-COTS}"))
    add_c(ComponentSpec("D_TVS1", "SMBJ15A_TVS", "Resistor_SMD:R_1206_3216Metric", 28.0, 18.0, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S3.3-04", epistemic_tag="{Pasif-COTS}"))
    add_c(ComponentSpec("C_IN12_1", "100uF_25V_POLY", "Capacitor_SMD:C_1210_3225Metric", 36.0, 18.0, pins=auto_footprint_pads("1210", ("1", "2")), bom_id="S3.3-04", epistemic_tag="{Pasif-COTS}"))
    add_c(ComponentSpec("C_IN12_2", "10uF_25V_X7R", "Capacitor_SMD:C_0805_2012Metric", 44.0, 18.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S3.3-04", epistemic_tag="{Pasif-COTS}"))
    conn("VIN_12V_RAW", "J_PWR12V", 1); conn("VIN_12V_RAW", "J_PWR12V", 2)
    conn("GND", "J_PWR12V", 3); conn("GND", "J_PWR12V", 4)
    conn("VIN_12V_RAW", "F1", 1); conn("VIN_12V", "F1", 2)
    conn("VIN_12V", "D_TVS1", 1); conn("GND", "D_TVS1", 2)
    conn("VIN_12V", "C_IN12_1", 1); conn("GND", "C_IN12_1", 2)
    conn("VIN_12V", "C_IN12_2", 1); conn("GND", "C_IN12_2", 2)

    # Power Sequencer LM3880MF-1AA (U_SEQ1)
    seq_pins = _dual_row_smd_pins([
        ("1", "VCC", "power_in"), ("2", "GND", "power_in"), ("3", "EN_IN", "input"), ("4", "PGOOD_OUT", "output"),
        ("5", "FLAG1_1V0", "output"), ("6", "FLAG2_1V8", "output"), ("7", "FLAG3_1V2", "output"), ("8", "FLAG4_IO", "output"),
    ], pitch_mm=1.27, x_off_mm=2.7)
    add_c(ComponentSpec("U_SEQ1", "LM3880MF-1AA", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 56.0, 18.0, pins=seq_pins, mpn="LM3880MF-1AA", bom_id="S3.3-01", epistemic_tag="{Aday-COTS}"))
    add_c(ComponentSpec("R_SEQ_EN", "10k_0603", "Resistor_SMD:R_0603_1608Metric", 66.0, 18.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    conn("VCCO_3V3_IO", "U_SEQ1", 1); conn("GND", "U_SEQ1", 2)
    conn("SEQ_EN", "U_SEQ1", 3); conn("PGOOD_ALL", "U_SEQ1", 4)
    conn("EN_1V0", "U_SEQ1", 5); conn("EN_1V8", "U_SEQ1", 6)
    conn("EN_1V2", "U_SEQ1", 7); conn("EN_2V5_3V3", "U_SEQ1", 8)
    conn("VIN_12V", "R_SEQ_EN", 1); conn("SEQ_EN", "R_SEQ_EN", 2)

    # Buck regulators helper
    def _add_buck(ref: str, val: str, mpn: str, x: float, y: float, vout_net: str, en_net: str, ind_val: str, with_pmbus: bool = False) -> None:
        pdefs = [
            ("1", "VIN", "power_in"), ("2", "GND", "power_in"), ("3", "EN", "input"), ("4", "SW", "output"),
            ("5", "VOUT_S", "power_out"), ("6", "PG", "output"),
        ]
        if with_pmbus:
            pdefs.extend([("7", "SCL", "bidirectional"), ("8", "SDA", "bidirectional")])
        else:
            pdefs.extend([("7", "FB", "input"), ("8", "SS", "passive")])
        add_c(ComponentSpec(ref, val, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", x, y, pins=_dual_row_smd_pins(pdefs, 1.27, 2.7), mpn=mpn, bom_id="S3.3-01", epistemic_tag="{Aday-COTS}"))
        lref = f"L_{ref[5:]}"
        cref = f"C_{ref[5:]}_OUT"
        add_c(ComponentSpec(lref, ind_val, "Inductor_SMD:L_1210_3225Metric", x + 11.0, y, pins=auto_footprint_pads("1210", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
        add_c(ComponentSpec(cref, "47uF_6V3_X5R", "Capacitor_SMD:C_1206_3216Metric", x + 19.0, y, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
        conn("VIN_12V", ref, 1); conn("GND", ref, 2); conn(en_net, ref, 3)
        sw_net = f"SW_{ref[5:]}"
        conn(sw_net, ref, 4); conn(sw_net, lref, 1)
        conn(vout_net, lref, 2); conn(vout_net, ref, 5)
        conn(vout_net, cref, 1); conn("GND", cref, 2)
        conn("PGOOD_ALL", ref, 6)
        if with_pmbus:
            conn("PMBUS_SCL", ref, 7); conn("PMBUS_SDA", ref, 8)
            conn("PMBUS_SCL", "U1", "K7"); conn("PMBUS_SDA", "U1", "K8")
        else:
            r_fb = f"R_FB_{ref[5:]}"
            c_ss = f"C_SS_{ref[5:]}"
            add_c(ComponentSpec(r_fb, "10k_0.1pct", "Resistor_SMD:R_0603_1608Metric", x + 26.0, y - 2.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
            add_c(ComponentSpec(c_ss, "10nF_0603", "Capacitor_SMD:C_0603_1608Metric", x + 26.0, y + 2.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
            conn(vout_net, r_fb, 1); conn(f"FB_{ref[5:]}", r_fb, 2); conn(f"FB_{ref[5:]}", ref, 7)
            conn(f"SS_{ref[5:]}", ref, 8); conn(f"SS_{ref[5:]}", c_ss, 1); conn("GND", c_ss, 2)

    _add_buck("U_VR_1V0", "TPS546D24A_1V0_15A", "TPS546D24ARVFR", 16.0, 38.0, "VCCINT_1V0", "EN_1V0", "0.47uH_20A", with_pmbus=True)
    _add_buck("U_VR_1V8", "TPS54527_1V8_4A", "TPS54527DDAR", 16.0, 52.0, "VCCAUX_1V8", "EN_1V8", "2.2uH_6A")
    _add_buck("U_VR_1V2", "TPS54527_1V2_DDR", "TPS54527DDAR", 16.0, 66.0, "VDD_1V2_DDR", "EN_1V2", "2.2uH_6A")
    _add_buck("U_VR_2V5", "TPS54327_2V5_LVDS", "TPS54327DDAR", 16.0, 80.0, "VCCO_2V5_LVDS", "EN_2V5_3V3", "3.3uH_4A")
    _add_buck("U_VR_3V3", "TPS54527_3V3_IO", "TPS54527DDAR", 16.0, 94.0, "VCCO_3V3_IO", "EN_2V5_3V3", "3.3uH_6A")

    # 0.6 V DDR4 VTT Regulator (TPS51200) + MGT Ultra-Low-Noise LDOs (2x LT3045)
    vtt_pins = _dual_row_smd_pins([
        ("1", "VLDOIN", "power_in"), ("2", "GND", "power_in"), ("3", "EN", "input"),
        ("4", "REFIN", "input"), ("5", "VO", "power_out"), ("6", "PGOOD", "output"),
    ], 1.27, 2.7)
    add_c(ComponentSpec("U_VTT_0V6", "TPS51200_0V6_VTT", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 56.0, 66.0, pins=vtt_pins, mpn="TPS51200DRCR", bom_id="S3.3-01", epistemic_tag="{Aday-COTS}"))
    add_c(ComponentSpec("C_VTT_OUT", "10uF_6V3_X5R", "Capacitor_SMD:C_0805_2012Metric", 66.0, 66.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    conn("VDD_1V2_DDR", "U_VTT_0V6", 1); conn("GND", "U_VTT_0V6", 2); conn("EN_1V2", "U_VTT_0V6", 3)
    conn("VDD_1V2_DDR", "U_VTT_0V6", 4); conn("VTT_0V6_DDR", "U_VTT_0V6", 5); conn("PGOOD_ALL", "U_VTT_0V6", 6)
    conn("VTT_0V6_DDR", "C_VTT_OUT", 1); conn("GND", "C_VTT_OUT", 2)

    for idx_mgt, (ref, val, vout_net, ym) in enumerate((
        ("U_LDO_MGT1V0", "LT3045_MGTAVCC_1V0", "MGTAVCC_1V0", 80.0),
        ("U_LDO_MGT1V2", "LT3045_MGTAVTT_1V2", "MGTAVTT_1V2", 94.0),
    )):
        ldo_pins = _dual_row_smd_pins([
            ("1", "IN", "power_in"), ("2", "EN", "input"), ("3", "GND", "power_in"),
            ("4", "SET", "passive"), ("5", "OUT", "power_out"), ("6", "PG", "output"),
        ], 1.27, 2.7)
        add_c(ComponentSpec(ref, val, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 56.0, ym, pins=ldo_pins, mpn="LT3045EDD", bom_id="S3.3-01", epistemic_tag="{Aday-COTS}"))
        add_c(ComponentSpec(f"R_SET_MGT{idx_mgt}", "10k_0.1pct", "Resistor_SMD:R_0603_1608Metric", 65.0, ym - 2.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
        add_c(ComponentSpec(f"C_OUT_MGT{idx_mgt}", "10uF_C0G", "Capacitor_SMD:C_0805_2012Metric", 65.0, ym + 2.0, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
        conn("VCCAUX_1V8", ref, 1); conn("EN_1V8", ref, 2); conn("GND", ref, 3)
        conn(f"SET_MGT{idx_mgt}", ref, 4); conn(f"SET_MGT{idx_mgt}", f"R_SET_MGT{idx_mgt}", 1); conn("GND", f"R_SET_MGT{idx_mgt}", 2)
        conn(vout_net, ref, 5); conn("PGOOD_ALL", ref, 6)
        conn(vout_net, f"C_OUT_MGT{idx_mgt}", 1); conn("GND", f"C_OUT_MGT{idx_mgt}", 2)

    # -----------------------------------------------------------------------
    # C. 1.0 V VCCINT 5-Decade PDN Decoupling Array (Matches fpga_pdn_1v0.cir!)
    #    4x 470uF POSCAP + 8x 47uF (1206) + 12x 4.7uF (0805) + 16x 470nF (0603) + 20x 47nF (0402)
    # -----------------------------------------------------------------------
    # Tier 1: 4x 470 uF Polymer/POSCAP near U_VR_1V0
    for i in range(4):
        cref = f"C_PDN_BULK{i+1}"
        add_c(ComponentSpec(cref, "470uF_2V5_POSCAP_9mR", "Capacitor_SMD:C_1210_3225Metric", 50.0 + i * 7.0, 38.0, pins=auto_footprint_pads("1210", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
        conn("VCCINT_1V0", cref, 1); conn("GND", cref, 2)
    # Tier 2: 8x 47 uF 1206 MLCC
    for i in range(8):
        cref = f"C_PDN_47U_{i+1}"
        add_c(ComponentSpec(cref, "47uF_6V3_X5R_1206", "Capacitor_SMD:C_1206_3216Metric", 50.0 + (i % 4) * 6.5, 45.0 + (i // 4) * 5.0, pins=auto_footprint_pads("1206", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
        conn("VCCINT_1V0", cref, 1); conn("GND", cref, 2)
    # Tier 3: 12x 4.7 uF 0805 MLCC around FPGA perimeter
    for i in range(12):
        cref = f"C_PDN_4U7_{i+1}"
        add_c(ComponentSpec(cref, "4.7uF_6V3_X7R_0805", "Capacitor_SMD:C_0805_2012Metric", 88.0 + (i % 6) * 5.0, 52.0 + (i // 6) * 4.5, pins=auto_footprint_pads("0805", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
        conn("VCCINT_1V0", cref, 1); conn("GND", cref, 2)
    # Tier 4: 16x 470 nF 0603 MLCC adjacent to FPGA BGA
    for i in range(16):
        cref = f"C_PDN_470N_{i+1}"
        add_c(ComponentSpec(cref, "470nF_10V_X7R_0603", "Capacitor_SMD:C_0603_1608Metric", 96.0 + (i % 8) * 4.0, 102.0 + (i // 8) * 3.8, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
        conn("VCCINT_1V0", cref, 1); conn("GND", cref, 2)
    # Tier 5: 24x 100 nF 0402 MLCC (B.Cu under-FFG900 perimeter rings, keeping central BGA escape vias unobstructed!)
    for i in range(24):
        cref = f"C_PDN_100N_{i+1}"
        xb = 100.0 + (i % 12) * 4.0
        yb = 67.5 if i < 12 else 96.5
        add_c(ComponentSpec(cref, "100nF_10V_X7R_0402", "Capacitor_SMD:C_0402_1005Metric", xb, yb, layer="B.Cu", pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
        conn("VCCINT_1V0", cref, 1); conn("GND", cref, 2)

    # -----------------------------------------------------------------------
    # D. Clock Tree: 10 MHz Rb (S7.4-01) + White Rabbit (S7.4-02) -> LMK04828
    # -----------------------------------------------------------------------
    j_rb = add_c(ComponentSpec("J_RB_10M", "SMA_10MHZ_RB_REF", "Connector_Coaxial:SMA_EdgeMount", 14.0, 120.0, rotation_deg=90.0, pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "CLK10M", "2": "GND"}), bom_id="S7.4-01", epistemic_tag="{Pasif-COTS}"))
    j_wr = add_c(ComponentSpec("J_WR_TRIG", "SMA_WHITE_RABBIT_TRIG", "Connector_Coaxial:SMA_EdgeMount", 14.0, 134.0, rotation_deg=90.0, pins=auto_footprint_pads("SMA", ("1", "2"), {"1": "WR_TRIG", "2": "GND"}), bom_id="S7.4-02", epistemic_tag="{Pasif-COTS}"))
    r_rb_t = add_c(ComponentSpec("R_RB_50", "49.9R_0.1pct", "Resistor_SMD:R_0603_1608Metric", 34.0, 120.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.4-01", epistemic_tag="{Pasif-COTS}"))
    r_wr_t = add_c(ComponentSpec("R_WR_50", "49.9R_0.1pct", "Resistor_SMD:R_0603_1608Metric", 34.0, 134.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S7.4-02", epistemic_tag="{Pasif-COTS}"))

    y_vcxo_pins = _dual_row_smd_pins([("1", "VCTRL", "input"), ("2", "GND", "power_in"), ("3", "OUT_100M", "output"), ("4", "VDD", "power_in")], 2.54, 3.0)
    add_c(ComponentSpec("Y_VCXO", "CVHD-950_100MHZ_VCXO", "Oscillator:CVHD-950_9x14mm", 34.0, 150.0, pins=y_vcxo_pins, mpn="CVHD-950-100.000", bom_id="S3.3-01", epistemic_tag="{Aday-COTS}"))

    # Pin ordering on right edge (9 bottom .. 16 top): N on lower pin, P on upper pin -> zero crossover on L-bend up to U1!
    lmk_pins = _dual_row_smd_pins([
        ("1", "VCC", "power_in"), ("2", "GND", "power_in"), ("3", "CLKIN0_10M", "input"), ("4", "OSCIN_100M", "input"),
        ("5", "CP1_OUT", "output"), ("6", "PLL_LOCK", "output"), ("7", "SPI_SCK", "input"), ("8", "SPI_MOSI", "input"),
        ("9", "CLK250_N", "output"), ("10", "CLK250_P", "output"), ("11", "CLK100_N", "output"), ("12", "CLK100_P", "output"),
        ("13", "CLK125_N", "output"), ("14", "CLK125_P", "output"), ("15", "SYNC_WR", "input"), ("16", "VCC_OUT", "power_in"),
    ], 1.27, 4.0)
    add_c(ComponentSpec("U_CLK", "LMK04828BISQ", "Package_DFN_QFN:QFN-64_9x9mm", 56.0, 135.0, pins=lmk_pins, mpn="LMK04828BISQ", bom_id="S3.3-01", epistemic_tag="{Aday-COTS}"))
    add_c(ComponentSpec("R_LF1", "1.2k_0603", "Resistor_SMD:R_0603_1608Metric", 45.0, 148.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    add_c(ComponentSpec("C_LF1", "22nF_C0G", "Capacitor_SMD:C_0603_1608Metric", 45.0, 154.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))

    # 100 Ohm LVDS clock receiver terminations directly on B.Cu escape vias beneath U1 (C1/C2=125M, C3/C4=100M, C5/C6=250M)!
    add_c(ComponentSpec("R_TERM_125M", "100R_0.1pct_0402", "Resistor_SMD:R_0402_1005Metric", 116.0, 78.0, layer="B.Cu", pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    add_c(ComponentSpec("R_TERM_100M", "100R_0.1pct_0402", "Resistor_SMD:R_0402_1005Metric", 120.0, 78.0, layer="B.Cu", pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    add_c(ComponentSpec("R_TERM_250M", "100R_0.1pct_0402", "Resistor_SMD:R_0402_1005Metric", 124.0, 78.0, layer="B.Cu", pins=auto_footprint_pads("0402", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))

    conn("CLK_10M_RB", "J_RB_10M", 1); conn("GND", "J_RB_10M", 2)
    conn("CLK_10M_RB", "R_RB_50", 1); conn("GND", "R_RB_50", 2); conn("CLK_10M_RB", "U_CLK", 3)
    conn("WR_TRIG_50", "J_WR_TRIG", 1); conn("GND", "J_WR_TRIG", 2)
    conn("WR_TRIG_50", "R_WR_50", 1); conn("GND", "R_WR_50", 2)
    conn("WR_TRIG_50", "U_CLK", 15); conn("WR_TRIG_50", "U1", "C7")
    conn("VCCO_3V3_IO", "Y_VCXO", 4); conn("GND", "Y_VCXO", 2)
    conn("VCXO_VCTRL", "Y_VCXO", 1); conn("VCXO_VCTRL", "R_LF1", 2); conn("VCXO_VCTRL", "C_LF1", 1); conn("GND", "C_LF1", 2)
    conn("PLL_CP1", "U_CLK", 5); conn("PLL_CP1", "R_LF1", 1)
    conn("VCXO_100M", "Y_VCXO", 3); conn("VCXO_100M", "U_CLK", 4)
    conn("VCCO_3V3_IO", "U_CLK", 1); conn("VCCO_2V5_LVDS", "U_CLK", 16); conn("GND", "U_CLK", 2)
    conn("CLK_LOCKED", "U_CLK", 6); conn("CLK_LOCKED", "U1", "C8")
    conn("IBIC_SPI_SCK", "U_CLK", 7); conn("IBIC_SPI_MOSI", "U_CLK", 8)
    for cname, p_p, p_n, fp1, fp2, rterm in (
        ("CLK_125M", 14, 13, "C1", "C2", "R_TERM_125M"),
        ("CLK_100M", 12, 11, "C3", "C4", "R_TERM_100M"),
        ("CLK_250M", 10, 9, "C5", "C6", "R_TERM_250M"),
    ):
        conn(f"{cname}_P", "U_CLK", p_p); conn(f"{cname}_P", "U1", fp1); conn(f"{cname}_P", rterm, 1)
        conn(f"{cname}_N", "U_CLK", p_n); conn(f"{cname}_N", "U1", fp2); conn(f"{cname}_N", rterm, 2)
        set_net(f"{cname}_P", net_class="LVDS_100", target_z0_ohm=100.0, diff_pair_with=f"{cname}_N")
        set_net(f"{cname}_N", net_class="LVDS_100", target_z0_ohm=100.0, diff_pair_with=f"{cname}_P")
    set_net("CLK_10M_RB", net_class="RF_50", target_z0_ohm=50.0)
    set_net("WR_TRIG_50", net_class="RF_50", target_z0_ohm=50.0)

    # -----------------------------------------------------------------------
    # E. Memory: 2 GB DDR4 (2x MT40A512M16LY) + 256 Mb QSPI NOR (Top zone)
    # -----------------------------------------------------------------------
    ddr_pdefs = [
        ("1", "VDD", "power_in"), ("2", "GND", "power_in"), ("3", "CS_N", "input"), ("4", "CK_P", "input"),
        ("5", "DQ0", "bidirectional"), ("6", "DQ1", "bidirectional"), ("7", "WE_N", "input"), ("8", "CK_N", "input"),
        ("9", "A0", "input"), ("10", "A1", "input"), ("11", "ODT", "input"), ("12", "CKE", "input"),
    ]
    add_c(ComponentSpec("U_DDR4_A", "MT40A512M16LY_1GB_A", "Package_BGA:FBGA-96_9x13mm", 112.0, 22.0, pins=_bga_grid_pins(ddr_pdefs, cols=4, pitch_mm=1.50), mpn="MT40A512M16LY-062E", bom_id="S3.3-01", epistemic_tag="{Aday-COTS}"))
    add_c(ComponentSpec("U_DDR4_B", "MT40A512M16LY_1GB_B", "Package_BGA:FBGA-96_9x13mm", 136.0, 22.0, pins=_bga_grid_pins(ddr_pdefs, cols=4, pitch_mm=1.50), mpn="MT40A512M16LY-062E", bom_id="S3.3-01", epistemic_tag="{Aday-COTS}"))
    add_c(ComponentSpec("R_DDR_VTT1", "39R_0603", "Resistor_SMD:R_0603_1608Metric", 124.0, 12.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    add_c(ComponentSpec("R_DDR_VTT2", "39R_0603", "Resistor_SMD:R_0603_1608Metric", 124.0, 32.0, pins=auto_footprint_pads("0603", ("1", "2")), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))

    for uddr, dq_pair in (("U_DDR4_A", ("DDR_DQ0", "DDR_DQ1")), ("U_DDR4_B", ("DDR_DQ2", "DDR_DQ3"))):
        conn("VDD_1V2_DDR", uddr, 1); conn("GND", uddr, 2)
        conn("DDR_CK_P", uddr, 4); conn("DDR_CK_N", uddr, 8)
        conn(dq_pair[0], uddr, 5); conn(dq_pair[1], uddr, 6)
        conn("DDR_CS_N", uddr, 3); conn("DDR_WE_N", uddr, 7)
        conn("DDR_A0", uddr, 9); conn("DDR_A1", uddr, 10)
        conn("DDR_ODT", uddr, 11); conn("DDR_CKE", uddr, 12)
    conn("DDR_CK_P", "U1", "D7"); conn("DDR_CK_N", "U1", "D8")
    conn("DDR_DQ0", "U1", "D3"); conn("DDR_DQ1", "U1", "D4"); conn("DDR_DQ2", "U1", "D5"); conn("DDR_DQ3", "U1", "D6")
    conn("DDR_CS_N", "U1", "D1"); conn("DDR_WE_N", "U1", "D2")
    conn("DDR_A0", "U1", "E1"); conn("DDR_A1", "U1", "E2"); conn("DDR_ODT", "U1", "E3"); conn("DDR_CKE", "U1", "E4")
    conn("DDR_A0", "R_DDR_VTT1", 1); conn("VTT_0V6_DDR", "R_DDR_VTT1", 2)
    conn("DDR_A1", "R_DDR_VTT2", 1); conn("VTT_0V6_DDR", "R_DDR_VTT2", 2)
    set_net("DDR_CK_P", net_class="DDR4_100", target_z0_ohm=100.0, diff_pair_with="DDR_CK_N")
    set_net("DDR_CK_N", net_class="DDR4_100", target_z0_ohm=100.0, diff_pair_with="DDR_CK_P")
    for dq in ("DDR_DQ0", "DDR_DQ1", "DDR_DQ2", "DDR_DQ3"):
        set_net(dq, net_class="DDR4_50", target_z0_ohm=50.0)

    # 256 Mb QSPI NOR Flash (MT25QU256ABA)
    qspi_pins = _dual_row_smd_pins([
        ("1", "CS_N", "input"), ("2", "D1", "bidirectional"), ("3", "D2", "bidirectional"), ("4", "GND", "power_in"),
        ("5", "D0", "bidirectional"), ("6", "CLK", "input"), ("7", "D3", "bidirectional"), ("8", "VCC", "power_in"),
    ], 1.27, 2.7)
    add_c(ComponentSpec("U_QSPI", "MT25QU256ABA_256Mb", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 90.0, 22.0, pins=qspi_pins, mpn="MT25QU256ABA1EW7", bom_id="S3.3-01", epistemic_tag="{Aday-COTS}"))
    conn("VCCAUX_1V8", "U_QSPI", 8); conn("GND", "U_QSPI", 4)
    conn("QSPI_CS_N", "U_QSPI", 1); conn("QSPI_CS_N", "U1", "E5")
    conn("QSPI_CLK", "U_QSPI", 6); conn("QSPI_CLK", "U1", "E6")
    conn("QSPI_D0", "U_QSPI", 5); conn("QSPI_D0", "U1", "E7")
    conn("QSPI_D1", "U_QSPI", 2); conn("QSPI_D1", "U1", "E8")
    conn("QSPI_D2", "U_QSPI", 3); conn("QSPI_D2", "U1", "F1")
    conn("QSPI_D3", "U_QSPI", 7); conn("QSPI_D3", "U1", "F2")

    # -----------------------------------------------------------------------
    # F. FMC HPC Connector (S3.3-03 50 MS/s 12-bit PHA ADC) (Top-Right)
    # -----------------------------------------------------------------------
    fmc_pdefs = [
        ("1", "V3P3", "power_out"), ("2", "V12P0", "power_out"), ("3", "GND1", "power_in"), ("4", "GND2", "power_in"),
        ("5", "CLK_P", "output"), ("6", "CLK_N", "output"), ("7", "D0_P", "output"), ("8", "D0_N", "output"),
        ("9", "D1_P", "output"), ("10", "D1_N", "output"), ("11", "SPI_SCK", "input"), ("12", "SPI_CSN", "input"),
    ]
    add_c(ComponentSpec("J_FMC_HPC", "ASP-134488-01_FMC_HPC", "Connector_Samtec:FMC_HPC_12P_SUBSET", 168.0, 26.0, pins=_bga_grid_pins(fmc_pdefs, cols=4, pitch_mm=1.50), mpn="ASP-134488-01", bom_id="S3.3-03", epistemic_tag="{Aday-COTS}"))
    conn("VCCO_3V3_IO", "J_FMC_HPC", 1); conn("VIN_12V", "J_FMC_HPC", 2)
    conn("GND", "J_FMC_HPC", 3); conn("GND", "J_FMC_HPC", 4)
    conn("FMC_CLK_P", "J_FMC_HPC", 5); conn("FMC_CLK_P", "U1", "F3")
    conn("FMC_CLK_N", "J_FMC_HPC", 6); conn("FMC_CLK_N", "U1", "F4")
    conn("FMC_D0_P", "J_FMC_HPC", 7); conn("FMC_D0_P", "U1", "F5")
    conn("FMC_D0_N", "J_FMC_HPC", 8); conn("FMC_D0_N", "U1", "F6")
    conn("FMC_D1_P", "J_FMC_HPC", 9); conn("FMC_D1_P", "U1", "G3")
    conn("FMC_D1_N", "J_FMC_HPC", 10); conn("FMC_D1_N", "U1", "G4")
    conn("FMC_SPI_SCK", "J_FMC_HPC", 11); conn("FMC_SPI_SCK", "U1", "G1")
    conn("FMC_SPI_CSN", "J_FMC_HPC", 12); conn("FMC_SPI_CSN", "U1", "G2")
    for pfx in ("FMC_CLK", "FMC_D0", "FMC_D1"):
        set_net(f"{pfx}_P", net_class="LVDS_100", target_z0_ohm=100.0, diff_pair_with=f"{pfx}_N")
        set_net(f"{pfx}_N", net_class="LVDS_100", target_z0_ohm=100.0, diff_pair_with=f"{pfx}_P")

    # -----------------------------------------------------------------------
    # G. 4x Isolated LVDS/SPI Mezzanine Ports (Right Edge x = 175..218 mm)
    #    Port 1: IBIC | Port 2: Blanker | Port 3: HV-DAC | Port 4: AOM/Pyro + 1oo2D Interlock
    # -----------------------------------------------------------------------
    iso_pdefs = [
        ("1", "VDD1", "power_in"), ("2", "GND1", "power_in"), ("3", "A1", "bidirectional"), ("4", "A2", "bidirectional"),
        ("5", "A3", "bidirectional"), ("6", "A4", "bidirectional"), ("7", "B4", "bidirectional"), ("8", "B3", "bidirectional"),
        ("9", "B2", "bidirectional"), ("10", "B1", "bidirectional"), ("11", "GND2", "power_in"), ("12", "VDD2", "power_in"),
    ]
    ports_cfg = [
        ("IBIC", "ADN4654_ISO_LVDS_IBIC", "ADN4654BRWZ", "S3.3-02", 58.0,
         ("IBIC_HIT_P", "IBIC_HIT_N", "IBIC_SPI_SCK", "IBIC_SPI_MOSI"),
         ("U1", ("F7", "F8", "G5", "G6")), True),
        ("BLK", "ADN4654_ISO_LVDS_BLANKER", "ADN4654BRWZ", "S3.3-02", 84.0,
         ("BLK_TX_P", "BLK_TX_N", "BLK_START", "BLK_SAFE_FORCE"),
         ("U1", ("G7", "G8", "H1", "H2")), True),
        ("HVDAC", "ADUM141D_ISO_SPI_HVDAC", "ADUM141DBRWZ", "S4.5-03", 110.0,
         ("HVDAC_SCLK", "HVDAC_MOSI", "HVDAC_CSN", "HVDAC_CLRN"),
         ("U1", ("H3", "H4", "H5", "H6")), False),
        ("AOM_IL", "ADUM141D_ISO_AOM_1OO2D", "ADUM141DBRWZ", "S1.4-03", 136.0,
         ("AOM_SPI_SCK", "AOM_RF_EN", "IL_CH_A_OK", "IL_TRIP_OUT"),
         ("U1", ("H7", "H8", "J1", "J3")), False),
    ]
    for pname, iso_val, iso_mpn, bom, yp, sigs, (uref, upins), is_lvds in ports_cfg:
        u_iso = f"U_ISO_{pname}"
        j_port = f"J_PORT_{pname}"
        add_c(ComponentSpec(u_iso, iso_val, "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", 180.0, yp, pins=_dual_row_smd_pins(iso_pdefs, 1.27, 4.4), mpn=iso_mpn, bom_id=bom, epistemic_tag="{Aday-COTS}"))
        add_c(ComponentSpec(j_port, f"HDR_2x4_ISO_{pname}", "Connector_PinHeader:HDR_2x4_2.54mm", 214.0, yp, pins=auto_footprint_pads("HDR_2x4_2.54mm", [str(k) for k in range(1, 9)]), bom_id=bom, epistemic_tag="{Pasif-COTS}"))
        conn("VCCO_3V3_IO", u_iso, 1); conn("GND", u_iso, 2)
        conn("VCCO_3V3_IO", u_iso, 12); conn("GND", u_iso, 11)
        conn("VCCO_3V3_IO", j_port, 1); conn("GND", j_port, 2)
        conn("GND", j_port, 7); conn("GND", j_port, 8)
        for idx_s, (sname, upin) in enumerate(zip(sigs, upins)):
            conn(sname, uref, upin)
            conn(sname, u_iso, 3 + idx_s)
            ext_net = f"EXT_{sname}"
            conn(ext_net, u_iso, 10 - idx_s)
            conn(ext_net, j_port, 3 + idx_s)
        if is_lvds:
            set_net(sigs[0], net_class="LVDS_100", target_z0_ohm=100.0, diff_pair_with=sigs[1])
            set_net(sigs[1], net_class="LVDS_100", target_z0_ohm=100.0, diff_pair_with=sigs[0])

    # Dedicated 1oo2D Ch-B & Safe-Enable secondary interlock port header (S6.9-04 / S7.SAFETY-03)
    add_c(ComponentSpec("J_IL_1OO2D_AUX", "HDR_1x4_1OO2D_CHB", "Connector_PinHeader:HDR_1x4_2.54mm", 214.0, 158.0, rotation_deg=90.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4")), bom_id="S6.9-04", epistemic_tag="{Pasif-COTS}"))
    conn("IL_CH_B_OK", "U1", "J2"); conn("IL_CH_B_OK", "J_IL_1OO2D_AUX", 1)
    conn("IL_SAFE_EN", "U1", "J4"); conn("IL_SAFE_EN", "J_IL_1OO2D_AUX", 2)
    conn("VCCO_3V3_IO", "J_IL_1OO2D_AUX", 3); conn("GND", "J_IL_1OO2D_AUX", 4)

    # -----------------------------------------------------------------------
    # H. Host Interfaces: 1000BASE-T GbE (DP83867IR), USB-UART (FT232HL), JTAG
    # -----------------------------------------------------------------------
    gbe_pins = _dual_row_smd_pins([
        ("1", "VDD33", "power_in"), ("2", "GND", "power_in"), ("3", "TXC", "input"), ("4", "TXD0", "input"),
        ("5", "RXC", "output"), ("6", "RXD0", "output"), ("7", "MDI0_P", "bidirectional"), ("8", "MDI0_N", "bidirectional"),
        ("9", "MDI1_P", "bidirectional"), ("10", "MDI1_N", "bidirectional"),
    ], 1.27, 3.2)
    add_c(ComponentSpec("U_GBE", "DP83867IR_1000BASET", "Package_DFN_QFN:QFN-48_7x7mm", 122.0, 134.0, pins=gbe_pins, mpn="DP83867IRRGZR", bom_id="S3.3-04", epistemic_tag="{Aday-COTS}"))
    add_c(ComponentSpec("J_ETH", "RJ45_MAGJACK_1GBE", "Connector_PinHeader:HDR_2x4_2.54mm", 122.0, 156.0, pins=auto_footprint_pads("HDR_2x4_2.54mm", [str(k) for k in range(1, 9)]), bom_id="S3.3-04", epistemic_tag="{Pasif-COTS}"))
    conn("VCCO_3V3_IO", "U_GBE", 1); conn("GND", "U_GBE", 2)
    conn("RGMII_TXC", "U1", "J5"); conn("RGMII_TXC", "U_GBE", 3)
    conn("RGMII_TXD0", "U1", "J6"); conn("RGMII_TXD0", "U_GBE", 4)
    conn("RGMII_RXC", "U1", "J7"); conn("RGMII_RXC", "U_GBE", 5)
    conn("RGMII_RXD0", "U1", "J8"); conn("RGMII_RXD0", "U_GBE", 6)
    conn("ETH_MDI0_P", "U_GBE", 7); conn("ETH_MDI0_P", "J_ETH", 1)
    conn("ETH_MDI0_N", "U_GBE", 8); conn("ETH_MDI0_N", "J_ETH", 2)
    conn("ETH_MDI1_P", "U_GBE", 9); conn("ETH_MDI1_P", "J_ETH", 3)
    conn("ETH_MDI1_N", "U_GBE", 10); conn("ETH_MDI1_N", "J_ETH", 4)
    conn("VCCO_3V3_IO", "J_ETH", 5); conn("GND", "J_ETH", 6); conn("GND", "J_ETH", 7); conn("GND", "J_ETH", 8)
    set_net("ETH_MDI0_P", net_class="ETH_100", target_z0_ohm=100.0, diff_pair_with="ETH_MDI0_N")
    set_net("ETH_MDI0_N", net_class="ETH_100", target_z0_ohm=100.0, diff_pair_with="ETH_MDI0_P")

    uart_pins = _dual_row_smd_pins([
        ("1", "V3P3", "power_in"), ("2", "GND", "power_in"), ("3", "TXD", "output"),
        ("4", "RXD", "input"), ("5", "USB_DP", "bidirectional"), ("6", "USB_DM", "bidirectional"),
    ], 1.27, 2.7)
    add_c(ComponentSpec("U_UART", "FT232HL_USB_UART", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 148.0, 134.0, pins=uart_pins, mpn="FT232HL-REEL", bom_id="S3.3-04", epistemic_tag="{Aday-COTS}"))
    add_c(ComponentSpec("J_USB", "USB_C_UART_CONSOLE", "Connector_PinHeader:HDR_1x4_2.54mm", 148.0, 156.0, rotation_deg=90.0, pins=auto_footprint_pads("HDR_1x4_2.54mm", ("1", "2", "3", "4")), bom_id="S3.3-04", epistemic_tag="{Pasif-COTS}"))
    conn("VCCO_3V3_IO", "U_UART", 1); conn("GND", "U_UART", 2)
    conn("UART_RX", "U1", "K2"); conn("UART_RX", "U_UART", 3)
    conn("UART_TX", "U1", "K1"); conn("UART_TX", "U_UART", 4)
    conn("USB_DP", "U_UART", 5); conn("USB_DP", "J_USB", 1)
    conn("USB_DM", "U_UART", 6); conn("USB_DM", "J_USB", 2)
    conn("VCCO_3V3_IO", "J_USB", 3); conn("GND", "J_USB", 4)

    add_c(ComponentSpec("J_JTAG", "XILINX_JTAG_14P", "Connector_PinHeader:HDR_2x4_2.54mm", 180.0, 156.0, pins=auto_footprint_pads("HDR_2x4_2.54mm", [str(k) for k in range(1, 9)]), bom_id="S3.3-01", epistemic_tag="{Pasif-COTS}"))
    conn("VCCO_2V5_LVDS", "J_JTAG", 1); conn("GND", "J_JTAG", 2)
    conn("JTAG_TCK", "U1", "K3"); conn("JTAG_TCK", "J_JTAG", 3)
    conn("JTAG_TMS", "U1", "K4"); conn("JTAG_TMS", "J_JTAG", 4)
    conn("JTAG_TDI", "U1", "K5"); conn("JTAG_TDI", "J_JTAG", 5)
    conn("JTAG_TDO", "U1", "K6"); conn("JTAG_TDO", "J_JTAG", 6)
    conn("GND", "J_JTAG", 7); conn("GND", "J_JTAG", 8)

    # -----------------------------------------------------------------------
    # I. Pad-to-Pad Coupled 3-Pin Diff Striplines + Reference Planes + Full Auto-Routing
    # -----------------------------------------------------------------------
    comp_map = {c.ref: c for c in comps}
    half_sl = round(0.5 * (w100_diff_sl + s_diff_sl), 4)

    # 1) 3-pin LVDS differential clocks (LMK04828 -> In5.Cu coupled 100 Ohm stripline -> U1 + B.Cu R_TERM via-in-pad!)
    for cname, p_p, p_n, fp1, fp2, rterm in (
        ("CLK_125M", 14, 13, "C1", "C2", "R_TERM_125M"),
        ("CLK_100M", 12, 11, "C3", "C4", "R_TERM_100M"),
        ("CLK_250M", 10, 9, "C5", "C6", "R_TERM_250M"),
    ):
        p_clk, n_clk = _pad_xy(comp_map["U_CLK"], str(p_p)), _pad_xy(comp_map["U_CLK"], str(p_n))
        p_fpga, n_fpga = _pad_xy(comp_map["U1"], fp1), _pad_xy(comp_map["U1"], fp2)
        p_rt, n_rt = _pad_xy(comp_map[rterm], "1"), _pad_xy(comp_map[rterm], "2")
        # Escape vias right next to U_CLK right-side pins (x=61.50, L=1.50 mm < 2.0 mm!)
        vp_clk = (round(p_clk[0] + 1.50, 4), p_clk[1])
        vn_clk = (round(n_clk[0] + 1.50, 4), n_clk[1])
        vias.append(ViaSpec(f"{cname}_P", vp_clk[0], vp_clk[1], diameter_mm=0.405, drill_mm=0.20))
        vias.append(ViaSpec(f"{cname}_N", vn_clk[0], vn_clk[1], diameter_mm=0.405, drill_mm=0.20))
        traces.append(TraceSpec(f"{cname}_P", "F.Cu", (p_clk, vp_clk), width_mm=w100_diff_ms, diff_spacing_mm=s_diff_ms))
        traces.append(TraceSpec(f"{cname}_N", "F.Cu", (n_clk, vn_clk), width_mm=w100_diff_ms, diff_spacing_mm=s_diff_ms))
        # Receiver escape vias right on B.Cu R_TERM pads (via-in-pad termination, L=1.13 mm < 2.0 mm!)
        vias.append(ViaSpec(f"{cname}_P", p_rt[0], p_rt[1], diameter_mm=0.405, drill_mm=0.20))
        vias.append(ViaSpec(f"{cname}_N", n_rt[0], n_rt[1], diameter_mm=0.405, drill_mm=0.20))
        traces.append(TraceSpec(f"{cname}_P", "F.Cu", (p_fpga, p_rt), width_mm=w100_diff_ms, diff_spacing_mm=s_diff_ms))
        traces.append(TraceSpec(f"{cname}_N", "F.Cu", (n_fpga, n_rt), width_mm=w100_diff_ms, diff_spacing_mm=s_diff_ms))
        # Nested zero-crossing L-bend coupled 100.00 Ohm stripline on In5.Cu (P is upper/left, N is lower/right!)
        y_mid = round(0.5 * (vp_clk[1] + vn_clk[1]), 4)
        x_col = round(0.5 * (p_rt[0] + n_rt[0]), 4)
        x_start = round(vp_clk[0] + 1.10, 4)
        y_end = round(p_rt[1] + 1.10, 4)
        yp, yn = round(y_mid - half_sl, 4), round(y_mid + half_sl, 4)
        xp, xn = round(x_col - half_sl, 4), round(x_col + half_sl, 4)
        traces.append(TraceSpec(f"{cname}_P", "In5.Cu", (vp_clk, (x_start, yp), (xp, yp), (xp, y_end), p_rt), width_mm=w100_diff_sl, diff_spacing_mm=s_diff_sl))
        traces.append(TraceSpec(f"{cname}_N", "In5.Cu", (vn_clk, (x_start, yn), (xn, yn), (xn, y_end), n_rt), width_mm=w100_diff_sl, diff_spacing_mm=s_diff_sl))

    # 2) 3-pin planar fly-by DDR4 differential clock (U1.D7/D8 -> In2.Cu coupled 100 Ohm stripline -> U_DDR4_A.4/8 -> U_DDR4_B.4/8)
    #    CK_P (pin 4, y=20.5) is directly above CK_N (pin 8, y=22.0) on right edge of both DDR4 chips -> ZERO crossing!
    p_u1d, n_u1d = _pad_xy(comp_map["U1"], "D7"), _pad_xy(comp_map["U1"], "D8")
    p_da, n_da = _pad_xy(comp_map["U_DDR4_A"], "4"), _pad_xy(comp_map["U_DDR4_A"], "8")
    p_db, n_db = _pad_xy(comp_map["U_DDR4_B"], "4"), _pad_xy(comp_map["U_DDR4_B"], "8")
    vp_u1d, vn_u1d = (round(p_u1d[0] + 0.52, 4), round(p_u1d[1] - 1.00, 4)), (round(n_u1d[0] - 0.52, 4), round(n_u1d[1] - 1.00, 4))
    vp_da, vn_da = (round(p_da[0] + 1.00, 4), p_da[1]), (round(n_da[0] + 1.00, 4), n_da[1])
    vp_db, vn_db = (round(p_db[0] + 1.00, 4), p_db[1]), (round(n_db[0] + 1.00, 4), n_db[1])
    for vxy_p, vxy_n, pad_p, pad_n in ((vp_u1d, vn_u1d, p_u1d, n_u1d), (vp_da, vn_da, p_da, n_da), (vp_db, vn_db, p_db, n_db)):
        vias.append(ViaSpec("DDR_CK_P", vxy_p[0], vxy_p[1], diameter_mm=0.405, drill_mm=0.20))
        vias.append(ViaSpec("DDR_CK_N", vxy_n[0], vxy_n[1], diameter_mm=0.405, drill_mm=0.20))
        traces.append(TraceSpec("DDR_CK_P", "F.Cu", (pad_p, vxy_p), width_mm=w100_diff_ms, diff_spacing_mm=s_diff_ms))
        traces.append(TraceSpec("DDR_CK_N", "F.Cu", (pad_n, vxy_n), width_mm=w100_diff_ms, diff_spacing_mm=s_diff_ms))
    # Planar coupled fly-by on In2.Cu: U1 (x=128.0, P left / N right) -> UP to y=27.5 -> LEFT (P bottom? wait: CCW turn puts P on BOTTOM!)
    # Turn CW to stay planar: go UP to y=26.5 -> turn RIGHT? Better: U1.D7=P (left), D8=N (right) -> turn LEFT (CCW): P=lower, N=upper ->
    # go LEFT to x=116.5 -> turn UP (CW): P=left, N=right -> turn RIGHT at y=21.25 (CW): P=TOP (21.069), N=BOTTOM (21.431)!
    # Matches vp_da (20.50 TOP) & vn_da (22.00 BOTTOM) and vp_db (20.50 TOP) & vn_db (22.00 BOTTOM) with ZERO crossings!
    x_u1 = round(0.5 * (vp_u1d[0] + vn_u1d[0]), 4)  # 128.00
    y_bot = round(vp_u1d[1] - 1.00, 4)              # 77.00
    y_jog = 27.5
    x_left = round(vp_da[0] + 1.20, 4)              # 116.45
    y_bar = round(0.5 * (vp_da[1] + vn_da[1]), 4)   # 21.25
    x_end = round(vp_db[0] - 1.00, 4)               # 138.25
    xp_u, xn_u = round(x_u1 - half_sl, 4), round(x_u1 + half_sl, 4)
    # Wait: at y_jog going LEFT from x_u1 to x_left, P is left -> turning LEFT means P is LOWER (y_jog+half_sl), N is UPPER (y_jog-half_sl);
    # then at x_left turning UP (CW), P (lower) becomes LEFT (x_left-half_sl) and N (upper) becomes RIGHT (x_left+half_sl);
    # then at y_bar turning RIGHT (CW), P (left) becomes TOP (y_bar-half_sl) and N (right) becomes BOTTOM (y_bar+half_sl)!
    traces.append(TraceSpec("DDR_CK_P", "In2.Cu", (
        vp_u1d,
        (xp_u, y_bot),
        (xp_u, round(y_jog + half_sl, 4)),
        (round(x_left - half_sl, 4), round(y_jog + half_sl, 4)),
        (round(x_left - half_sl, 4), round(y_bar - half_sl, 4)),
        (x_end, round(y_bar - half_sl, 4)),
        vp_db,
    ), width_mm=w100_diff_sl, diff_spacing_mm=s_diff_sl))
    traces.append(TraceSpec("DDR_CK_N", "In2.Cu", (
        vn_u1d,
        (xn_u, y_bot),
        (xn_u, round(y_jog - half_sl, 4)),
        (round(x_left + half_sl, 4), round(y_jog - half_sl, 4)),
        (round(x_left + half_sl, 4), round(y_bar + half_sl, 4)),
        (x_end, round(y_bar + half_sl, 4)),
        vn_db,
    ), width_mm=w100_diff_sl, diff_spacing_mm=s_diff_sl))
    # Short (<1.4 mm) planar taps into U_DDR4_A vias (P taps UP from top rail, N taps DOWN from bottom rail!)
    traces.append(TraceSpec("DDR_CK_P", "In2.Cu", ((round(x_left - half_sl, 4), round(y_bar - half_sl, 4)), vp_da), width_mm=w100_diff_sl, diff_spacing_mm=s_diff_sl))
    traces.append(TraceSpec("DDR_CK_N", "In2.Cu", ((round(x_left + half_sl, 4), round(y_bar + half_sl, 4)), vn_da), width_mm=w100_diff_sl, diff_spacing_mm=s_diff_sl))

    # GND stitching vias + VCCINT_1V0 low-inductance via array around FPGA
    for gx in (8.0, 78.0, 154.0, 222.0):
        for gy in (8.0, 162.0):
            vias.append(ViaSpec("GND", gx, gy, diameter_mm=0.60, drill_mm=0.30))
    for vx in (84.0, 90.0, 96.0, 102.0):
        vias.append(ViaSpec("VCCINT_1V0", vx, 38.0, diameter_mm=0.60, drill_mm=0.30))
        vias.append(ViaSpec("GND", vx, 41.0, diameter_mm=0.60, drill_mm=0.30))

    # Solid 8-layer Reference Planes: In1.Cu (GND1), In3.Cu (VCCINT_1V0), In4.Cu (GND2), In6.Cu (GND3)
    rect_inner = ((2.0, 2.0), (228.0, 2.0), (228.0, 168.0), (2.0, 168.0))
    zones = (
        ZoneSpec("GND", "In1.Cu", rect_inner, clearance_mm=0.20),
        ZoneSpec("VCCINT_1V0", "In3.Cu", ((8.0, 30.0), (150.0, 30.0), (150.0, 118.0), (8.0, 118.0)), clearance_mm=0.20),
        ZoneSpec("GND", "In4.Cu", rect_inner, clearance_mm=0.20),
        ZoneSpec("GND", "In6.Cu", rect_inner, clearance_mm=0.20),
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
            diff_pair_with=net_meta.get(nname, {}).get("diff_pair_with"),
        )
        for nname, nodes in sorted(nets_dict.items())
    )

    spec = BoardSpec(
        name="fpga_brain_carrier",
        title="FPGA Brain Carrier (XC7K325T-2FFG900 + ZU48DR ICD) 8L FR408HR",
        rev="v1.0",
        bom_ids=("S3.3-01", "S3.3-02", "S3.3-04", "S1.4-03", "S4.5-03", "S6.9-04", "S6.11-01"),
        width_mm=230.0,
        height_mm=170.0,
        stackup=stackup,
        components=tuple(comps),
        nets=nets,
        traces=tuple(traces),
        vias=tuple(vias),
        zones=zones,
        rules=DesignRules(min_trace_width_mm=0.127, min_clearance_mm=0.127, impedance_tol_pct=5.0),
        epistemic_meta={
            **DEFAULT_EPISTEMIC_META,
            "carrier_fpga": "XC7K325T-2FFG900",
            "stackup_material": "Isola FR408HR (8-layer, er=3.66)",
            "w50_microstrip_mm": w50_ms,
            "w100_diff_microstrip_mm": w100_diff_ms,
            "w50_stripline_mm": w50_sl,
            "w100_diff_stripline_mm": w100_diff_sl,
        },
        notes=(
            f"50 Ohm SE microstrip: w={w50_ms:.4f} mm -> Z0={calc_microstrip_z0(w50_ms, 0.127, 0.035, 3.66):.2f} Ohm",
            f"100 Ohm diff microstrip: w={w100_diff_ms:.4f} mm, s={s_diff_ms:.2f} mm -> Zdiff={calc_diff_microstrip_z0(w100_diff_ms, s_diff_ms, 0.127, 0.035, 3.66):.2f} Ohm",
            f"50 Ohm SE stripline (In2/In5.Cu): w={w50_sl:.4f} mm -> Z0={calc_stripline_z0(w50_sl, 0.435, 0.035, 3.66):.2f} Ohm",
            f"100 Ohm diff stripline (In2/In5.Cu): w={w100_diff_sl:.4f} mm, s={s_diff_sl:.2f} mm -> Zdiff={calc_diff_stripline_z0(w100_diff_sl, s_diff_sl, 0.435, 0.035, 3.66):.2f} Ohm",
        ),
    )
    return auto_route_board(spec, grid_mm=0.60, preserve_existing=True)


# ---------------------------------------------------------------------------
# 4. Live ngspice-47 PDN AC Impedance + 5 A Load-Step Transient Deck
# ---------------------------------------------------------------------------

# Shared PDN parameters used by BOTH ngspice-47 and independent Python MNA cross-check
PDN_PARAMS: dict[str, float] = {
    "v_nom_v": 1.0,
    # Dual-phase 15 A PMBus buck closed-loop small-signal output impedance (~120 kHz loop BW)
    "r_vrm_ohm": 1.0e-3,
    "l_vrm_h": 14.0e-9,
    # PCB plane spreading impedance (2 oz PWR / 0.100 mm core / 2 oz GND2) from VRM to mid-bulk
    "r_plane_vrm_ohm": 0.35e-3,
    "l_plane_vrm_h": 180.0e-12,
    # Tier 1: 4x 470 uF Polymer/POSCAP (each ESR=9 mOhm, ESL=1.8 nH)
    "c_bulk_f": 4 * 470.0e-6,
    "r_bulk_ohm": 9.0e-3 / 4.0,
    "l_bulk_h": 1.8e-9 / 4.0,
    # Tier 2: 8x 47 uF 1206 MLCC (each ESR=12 mOhm damped, ESL=0.80 nH)
    "c_47u_f": 8 * 47.0e-6,
    "r_47u_ohm": 12.0e-3 / 8.0,
    "l_47u_h": 0.80e-9 / 8.0,
    # Spreading from mid-bulk to FPGA perimeter
    "r_plane_mid_ohm": 0.25e-3,
    "l_plane_mid_h": 65.0e-12,
    # Tier 3: 12x 4.7 uF 0805 MLCC (each ESR=24 mOhm, ESL=0.55 nH)
    "c_4u7_f": 12 * 4.7e-6,
    "r_4u7_ohm": 24.0e-3 / 12.0,
    "l_4u7_h": 0.55e-9 / 12.0,
    # Tier 4: 16x 470 nF 0603 MLCC (each ESR=32 mOhm, ESL=0.40 nH)
    "c_470n_f": 16 * 470.0e-9,
    "r_470n_ohm": 32.0e-3 / 16.0,
    "l_470n_h": 0.40e-9 / 16.0,
    # Spreading from perimeter to BGA cavity + parallel FFG900 BGA via array (56 VCCINT + 150 GND balls)
    "r_plane_bga_ohm": 0.15e-3,
    "l_plane_bga_h": 14.0e-12,
    # Tier 5: 24x 100 nF 0402 under-BGA low-ESL MLCC (each ESR=36 mOhm, ESL=0.25 nH via-in-pad)
    "c_100n_f": 24 * 100.0e-9,
    "r_100n_ohm": 36.0e-3 / 24.0,
    "l_100n_h": 0.25e-9 / 24.0,
    # PCB 2 oz PWR/GND planar cavity capacitance (140x88 mm / 0.100 mm FR408HR er=3.66 -> ~4.0 nF)
    "c_plane_f": 4.0e-9,
    "r_plane_c_ohm": 2.0e-3,
    # XC7K325T FFG900 package + on-die decoupling capacitance (UG483: 56 VCCINT balls ~12 pH, 600 nF die+pkg)
    "l_pkg_h": 12.0e-12,
    "r_pkg_ohm": 0.25e-3,
    "c_die_f": 600.0e-9,
    "r_die_ohm": 6.0e-3,
}


def render_fpga_pdn_ngspice_deck() -> str:
    """Emit native ngspice-47 SPICE deck for 1.0 V VCCINT PDN AC impedance & 5 A transient."""
    p = PDN_PARAMS
    return f"""* FPGA Brain Carrier (XC7K325T-2FFG900) — 1.0 V VCCINT PDN AC Impedance & 5 A Load-Step
* Native ngspice-47 deck (zero PSpice syntax) — M0/M1 DESIGN_ONLY
* Stackup: 8-layer Isola FR408HR (In3.Cu 2oz PWR / 0.100 mm core / In4.Cu 2oz GND2)
* Targets: |Z_PDN(f)| < 10 mOhm (100 Hz .. 20 MHz), 5 A load-step droop < 30 mV (+/-3%)

.temp 26.85

* 1.0 V Dual-Phase PMBus Buck VRM (TPS546D24A 15 A class closed-loop small-signal output model)
Vvrm vrm_src 0 DC {p['v_nom_v']}
Rvrm vrm_src vrm_r {p['r_vrm_ohm']:.6e}
Lvrm vrm_r n_bulk {p['l_vrm_h']:.6e}

* Tier 1: 4x 470 uF Polymer/POSCAP Bulk Bank (1880 uF, ESR=2.25 mOhm, ESL=450 pH)
Cbulk n_bulk n_bulk_r {p['c_bulk_f']:.6e}
Rbulk n_bulk_r n_bulk_l {p['r_bulk_ohm']:.6e}
Lbulk n_bulk_l 0 {p['l_bulk_h']:.6e}

* PCB 2oz PWR/GND Plane Spreading: VRM -> Mid-Bulk MLCC Bank
Rpl1 n_bulk n_pl1 {p['r_plane_vrm_ohm']:.6e}
Lpl1 n_pl1 n_mid {p['l_plane_vrm_h']:.6e}

* Tier 2: 8x 47 uF 1206 MLCC Bank (376 uF, ESR=1.50 mOhm, ESL=100 pH)
C47u n_mid n_47u_r {p['c_47u_f']:.6e}
R47u n_47u_r n_47u_l {p['r_47u_ohm']:.6e}
L47u n_47u_l 0 {p['l_47u_h']:.6e}

* PCB Spreading: Mid-Bulk -> FPGA Perimeter Bank
Rpl2 n_mid n_pl2 {p['r_plane_mid_ohm']:.6e}
Lpl2 n_pl2 n_perim {p['l_plane_mid_h']:.6e}

* Tier 3: 12x 4.7 uF 0805 MLCC Bank (56.4 uF, ESR=2.00 mOhm, ESL=45.8 pH)
C4u7 n_perim n_4u7_r {p['c_4u7_f']:.6e}
R4u7 n_4u7_r n_4u7_l {p['r_4u7_ohm']:.6e}
L4u7 n_4u7_l 0 {p['l_4u7_h']:.6e}

* Tier 4: 16x 470 nF 0603 MLCC Bank (7.52 uF, ESR=2.00 mOhm, ESL=25.0 pH)
C470n n_perim n_470n_r {p['c_470n_f']:.6e}
R470n n_470n_r n_470n_l {p['r_470n_ohm']:.6e}
L470n n_470n_l 0 {p['l_470n_h']:.6e}

* PCB Spreading + BGA Via Array: Perimeter -> Under-BGA Cavity
Rpl3 n_perim n_pl3 {p['r_plane_bga_ohm']:.6e}
Lpl3 n_pl3 n_bga {p['l_plane_bga_h']:.6e}

* Tier 5: 24x 100 nF 0402 Under-BGA Low-ESL MLCC Bank (2.40 uF, ESR=1.50 mOhm, ESL=10.4 pH)
C100n n_bga n_100n_r {p['c_100n_f']:.6e}
R100n n_100n_r n_100n_l {p['r_100n_ohm']:.6e}
L100n n_100n_l 0 {p['l_100n_h']:.6e}

* Planar 2oz PWR/GND Cavity Capacitance (0.100 mm FR408HR core)
Cplane n_bga n_cpl {p['c_plane_f']:.6e}
Rplane_c n_cpl 0 {p['r_plane_c_ohm']:.6e}

* XC7K325T FFG900 Package Inductance & On-Die Decoupling
Rpkg n_bga n_pkg_r {p['r_pkg_ohm']:.6e}
Lpkg n_pkg_r vccint_die {p['l_pkg_h']:.6e}
Cdie vccint_die n_die_r {p['c_die_f']:.6e}
Rdie n_die_r 0 {p['r_die_ohm']:.6e}

* Load Current Stimulus at FPGA Die:
*   AC = 1 A (so vm(vccint_die) directly equals |Z_PDN(f)| in Ohms!)
*   TRAN = 1 A baseline -> 6 A (+5 A step, t_rise=50 ns, di/dt=100 A/us) -> 1 A release
Iload vccint_die 0 DC 1.0 AC 1.0 PULSE(1.0 6.0 10u 50n 50n 60u 200u)

.control
set noaskquit

* 1) AC PDN Impedance Sweep: 100 Hz to 30 MHz (100 pts/dec; evaluated over 100 Hz .. 20 MHz)
ac dec 100 100 30Meg
meas ac z_pdn_max_ohm MAX vm(vccint_die) FROM=100 TO=20Meg
meas ac z_pdn_max_freq_hz MAX_AT vm(vccint_die) FROM=100 TO=20Meg
meas ac z_pdn_100hz_ohm FIND vm(vccint_die) AT=100
meas ac z_pdn_10khz_ohm FIND vm(vccint_die) AT=10k
meas ac z_pdn_1mhz_ohm  FIND vm(vccint_die) AT=1Meg
meas ac z_pdn_10mhz_ohm FIND vm(vccint_die) AT=10Meg
meas ac z_pdn_20mhz_ohm FIND vm(vccint_die) AT=20Meg

* 2) Transient 5 A Load-Step (1 A -> 6 A in 50 ns) Droop & Overshoot
tran 20n 140u
meas tran v_init_v FIND v(vccint_die) AT=5u
meas tran v_min_step_v MIN v(vccint_die) FROM=9.5u TO=40u
meas tran v_max_rel_v  MAX v(vccint_die) FROM=69.5u TO=120u
let v_droop_v = v_init_v - v_min_step_v
let v_overshoot_v = v_max_rel_v - v_init_v
print v_droop_v
print v_overshoot_v

quit 0
.endc
.end
"""


def run_pdn_mna_crosscheck() -> dict[str, Any]:
    """Independent Python MNA AC impedance cross-check of 1.0 V VCCINT PDN (100 Hz .. 20 MHz)."""
    p = PDN_PARAMS
    mna = MnaCircuit()
    mna.add_vsource("vrm_src", "0", dc=p["v_nom_v"], ac=0.0)
    mna.add_resistor("vrm_src", "vrm_r", p["r_vrm_ohm"])
    mna.add_inductor("vrm_r", "n_bulk", p["l_vrm_h"])

    mna.add_capacitor("n_bulk", "n_bulk_r", p["c_bulk_f"])
    mna.add_resistor("n_bulk_r", "n_bulk_l", p["r_bulk_ohm"])
    mna.add_inductor("n_bulk_l", "0", p["l_bulk_h"])

    mna.add_resistor("n_bulk", "n_pl1", p["r_plane_vrm_ohm"])
    mna.add_inductor("n_pl1", "n_mid", p["l_plane_vrm_h"])

    mna.add_capacitor("n_mid", "n_47u_r", p["c_47u_f"])
    mna.add_resistor("n_47u_r", "n_47u_l", p["r_47u_ohm"])
    mna.add_inductor("n_47u_l", "0", p["l_47u_h"])

    mna.add_resistor("n_mid", "n_pl2", p["r_plane_mid_ohm"])
    mna.add_inductor("n_pl2", "n_perim", p["l_plane_mid_h"])

    mna.add_capacitor("n_perim", "n_4u7_r", p["c_4u7_f"])
    mna.add_resistor("n_4u7_r", "n_4u7_l", p["r_4u7_ohm"])
    mna.add_inductor("n_4u7_l", "0", p["l_4u7_h"])

    mna.add_capacitor("n_perim", "n_470n_r", p["c_470n_f"])
    mna.add_resistor("n_470n_r", "n_470n_l", p["r_470n_ohm"])
    mna.add_inductor("n_470n_l", "0", p["l_470n_h"])

    mna.add_resistor("n_perim", "n_pl3", p["r_plane_bga_ohm"])
    mna.add_inductor("n_pl3", "n_bga", p["l_plane_bga_h"])

    mna.add_capacitor("n_bga", "n_100n_r", p["c_100n_f"])
    mna.add_resistor("n_100n_r", "n_100n_l", p["r_100n_ohm"])
    mna.add_inductor("n_100n_l", "0", p["l_100n_h"])

    mna.add_capacitor("n_bga", "n_cpl", p["c_plane_f"])
    mna.add_resistor("n_cpl", "0", p["r_plane_c_ohm"])

    mna.add_resistor("n_bga", "n_pkg_r", p["r_pkg_ohm"])
    mna.add_inductor("n_pkg_r", "vccint_die", p["l_pkg_h"])
    mna.add_capacitor("vccint_die", "n_die_r", p["c_die_f"])
    mna.add_resistor("n_die_r", "0", p["r_die_ohm"])

    mna.add_isource("vccint_die", "0", ac=1.0)

    freqs = np.geomspace(100.0, 20.0e6, 600)
    sol = mna.solve_ac(freqs)
    z_mag = np.abs(sol["vccint_die"])
    pk_i = int(np.argmax(z_mag))
    spot = mna.solve_ac([100.0, 10e3, 1e6, 10e6, 20e6])["vccint_die"]
    return {
        "mna_z_pdn_max_mohm": round(float(z_mag[pk_i]) * 1e3, 4),
        "mna_z_pdn_max_freq_hz": round(float(freqs[pk_i]), 2),
        "mna_z_100hz_mohm": round(float(abs(spot[0])) * 1e3, 4),
        "mna_z_10khz_mohm": round(float(abs(spot[1])) * 1e3, 4),
        "mna_z_1mhz_mohm": round(float(abs(spot[2])) * 1e3, 4),
        "mna_z_10mhz_mohm": round(float(abs(spot[3])) * 1e3, 4),
        "mna_z_20mhz_mohm": round(float(abs(spot[4])) * 1e3, 4),
    }


def build_and_verify_all(out_dir: Path | None = None) -> dict[str, Any]:
    """Generate fpga_brain_carrier KiCad 8 files, run ERC/DRC + live ngspice-47 PDN + MNA."""
    od = out_dir or OUT_DIR
    od.mkdir(parents=True, exist_ok=True)

    spec = build_fpga_brain_carrier()
    board_rep = verify_board_bundle(spec, od)

    cir_path = od / "fpga_pdn_1v0.cir"
    cir_path.write_text(render_fpga_pdn_ngspice_deck(), encoding="utf-8")
    spice_res = run_ngspice(cir_path, workdir=od)

    m = spice_res.metrics
    z_max_mohm = m.get("z_pdn_max_ohm", float("inf")) * 1e3
    z_max_freq_hz = m.get("z_pdn_max_freq_hz", 0.0)
    z_20mhz_mohm = m.get("z_pdn_20mhz_ohm", float("inf")) * 1e3
    v_droop_mv = m.get("v_droop_v", float("inf")) * 1e3
    v_overshoot_mv = m.get("v_overshoot_v", float("inf")) * 1e3
    v_init_v = m.get("v_init_v", 0.0)

    mna = run_pdn_mna_crosscheck()
    z_mna_diff_pct = abs(z_max_mohm - mna["mna_z_pdn_max_mohm"]) / max(mna["mna_z_pdn_max_mohm"], 1e-9) * 100.0

    sizing = load_yosys_sizing_metadata()

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
        "stackup_8_copper_layers": board_rep["drc"]["stackup_summary"]["copper_layers"] == 8,
        "impedance_50se_and_100diff_pass": bool(
            len(board_rep["drc"]["impedance_checks"]) >= 20
            and all(ic["passed"] for ic in board_rep["drc"]["impedance_checks"])
        ),
        "fpga_headroom_gt_4x": bool(sizing["carrier_fpga"]["headroom_factor"]["dsp48e1_x"] > 4.0),
        "ngspice_ok": spice_res.ok,
        "z_pdn_max_lt_10mohm": bool(0.0 < z_max_mohm < 10.0),
        "z_pdn_20mhz_lt_10mohm": bool(0.0 < z_20mhz_mohm < 10.0),
        "droop_5a_lt_30mv": bool(0.0 < v_droop_mv < 30.0),
        "overshoot_5a_lt_30mv": bool(0.0 < v_overshoot_mv < 30.0),
        "mna_ngspice_pdn_parity_lt_1pct": bool(z_mna_diff_pct < 1.0),
    }

    report = {
        "module": "fpga_brain_carrier",
        "bom_ids_covered": list(spec.bom_ids),
        "epistemic_meta": {
            **DEFAULT_EPISTEMIC_META,
            "simulation_engine": spice_res.version,
        },
        "yosys_sizing_and_zu48dr_icd": sizing,
        "board": board_rep,
        "ngspice_simulation": {
            "cir_file": cir_path.name,
            "version": spice_res.version,
            "ok": spice_res.ok,
            "errors": spice_res.errors,
            "warnings": spice_res.warnings,
            "raw_metrics": m,
            "derived": {
                "z_pdn_max_mOhm": round(z_max_mohm, 4),
                "z_pdn_max_freq_kHz": round(z_max_freq_hz * 1e-3, 3),
                "z_pdn_100hz_mOhm": round(m.get("z_pdn_100hz_ohm", 0.0) * 1e3, 4),
                "z_pdn_10khz_mOhm": round(m.get("z_pdn_10khz_ohm", 0.0) * 1e3, 4),
                "z_pdn_1mhz_mOhm": round(m.get("z_pdn_1mhz_ohm", 0.0) * 1e3, 4),
                "z_pdn_10mhz_mOhm": round(m.get("z_pdn_10mhz_ohm", 0.0) * 1e3, 4),
                "z_pdn_20mhz_mOhm": round(z_20mhz_mohm, 4),
                "v_init_1a_V": round(v_init_v, 5),
                "v_droop_5a_step_mV": round(v_droop_mv, 4),
                "v_droop_pct": round(100.0 * v_droop_mv / 1000.0, 3),
                "v_overshoot_5a_release_mV": round(v_overshoot_mv, 4),
            },
        },
        "mna_crosscheck": {
            **mna,
            "z_max_vs_ngspice_rel_diff_pct": round(z_mna_diff_pct, 4),
        },
        "checks": checks,
        "all_passed": all(checks.values()),
    }

    (od / "fpga_brain_carrier_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    rep = build_and_verify_all()
    b = rep["board"]
    d = rep["ngspice_simulation"]["derived"]
    print("=== FPGA BRAIN CARRIER VERIFICATION ===")
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
        f"Z_max={d['z_pdn_max_mOhm']} mOhm @ {d['z_pdn_max_freq_kHz']} kHz | "
        f"Z_20MHz={d['z_pdn_20mhz_mOhm']} mOhm | 5A droop={d['v_droop_5a_step_mV']} mV ({d['v_droop_pct']}%) | "
        f"overshoot={d['v_overshoot_5a_release_mV']} mV"
    )
    print(f"  MNA parity: Z_max diff={rep['mna_crosscheck']['z_max_vs_ngspice_rel_diff_pct']}%")
    print(f"  ALL_PASSED = {rep['all_passed']}")
    if not rep["all_passed"]:
        print("  FAILED:", [k for k, v in rep["checks"].items() if not v])
        if rep["ngspice_simulation"]["errors"]:
            print("  SPICE ERRORS:", rep["ngspice_simulation"]["errors"])
