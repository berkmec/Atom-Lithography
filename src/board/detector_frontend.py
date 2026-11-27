"""8-Channel IBIC Detector Front-End Netlist, SPICE Deck & ERC Validator (v2.1).

Scope: BOM S3.1 / S3.2 / S3.3 + S2.4 FPGA count interface (DESIGN.md v3.0,
Exp72, Exp91 5 keV P91, Exp127).

Default locked profile (``--profile cold100k``, Exp127 F3 closure):
  * Cold-island in-vacuum CSA at T = 100 K:
      - RF = 1 GOhm (tau_f = 250 us), CF = 0.25 pF
      - Buffered CR-RC active shaper: CS = CP = 600 pF, RS1 = RS2 = 2.00 kOhm
        (tau_s = 1.2 us < 0.01% of 15 ms HDA-HiRes shot cycle), RG1 = 100 Ohm,
        RG2 = 13.5 kOhm (G_stage = 136 -> effective CR-RC peak gain G/e = 50.0)
      - Lindhard 5 keV 31P+ @ 100 K charge impulse: Q_ION = 0.055f (~342 e-),
        5.5-sigma rising threshold V_THR = 4.23 mV (ENC = 24.1 e- rms,
        MC eta = 0.99936 at C_det = 0.5 pF, Rice P_false = 2.59e-4 / 1 ms)
Optional warm profile (``--profile rt300k``):
  * Room-temperature 300 K / 200 ns baseline (RF = 100 MOhm, CS = CP = 100 pF,
    Q_ION = 0.056f [351 e-], V_THR = 15.67 mV; fails 5 keV under Lindhard).

Generates and ERC-validates:
  1. ``detector_frontend.net`` — valid KiCad (version D) S-expression netlist
     (204 components, 107 unique nets, 0 ERC errors).
  2. ``detector_frontend.cir`` — standard SPICE3 / ngspice deck (subcircuit +
     8-channel instantiation + AC/TRAN/NOISE analysis cards).
  3. ``validate_netlist()`` — automated Electrical Rules Check (ERC).

Epistemic note: All active semiconductors are labeled ``{Aday-COTS}`` (candidate
commercial parts; no PCB layout, Gerber, or lab measurement exists in this repo).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

CHANNELS = 8  # per front-end tile board

PROFILES: dict[str, dict] = {
    "cold100k": {
        "name": "COLD_100K",
        "temp_K": 100.0,
        "cf_F": 0.25e-12,
        "rf_Ohm": 1.0e9,
        "rf_label": "1G_THICKFILM",
        "rf_spice": "1G",
        "cs_F": 600e-12,
        "cs_label": "600pF_C0G_1pct",
        "cs_spice": "600p",
        "rs1_Ohm": 2.0e3,
        "rg1_Ohm": 100.0,
        "rg2_Ohm": 13.5e3,
        "rs2_Ohm": 2.0e3,
        "cp_F": 600e-12,
        "cp_label": "600pF_C0G_1pct",
        "cp_spice": "600p",
        "tau_s_ns": 1200.0,
        "q_ion_spice": "0.055f",    # ~342 e- Lindhard 5 keV 31P+ @ 100 K (w=3.72 eV)
        "v_thr_spice": "0.00423",   # 4.23 mV (5.5-sigma ENC=24.1 e- rms)
        "rhys1_Ohm": 1.0e3,
        "rhys2_Ohm": 3.3e6,
        "rterm_Ohm": 49.9,
        "rbias_Ohm": 10e6,
        "cbias_F": 10e-9,
        "rdac_Ohm": 1.0e3,
        "cdac_F": 100e-9,
        "vcca_V": 2.5,
        "vssa_V": -2.5,
        "vccd_V": 3.3,
        "vbias_V": -30.0,
    },
    "rt300k": {
        "name": "RT_300K",
        "temp_K": 300.0,
        "cf_F": 0.25e-12,
        "rf_Ohm": 100e6,
        "rf_label": "100M_THICKFILM",
        "rf_spice": "100Meg",
        "cs_F": 100e-12,
        "cs_label": "100pF_C0G_1pct",
        "cs_spice": "100p",
        "rs1_Ohm": 2.0e3,
        "rg1_Ohm": 100.0,
        "rg2_Ohm": 13.5e3,
        "rs2_Ohm": 2.0e3,
        "cp_F": 100e-12,
        "cp_label": "100pF_C0G_1pct",
        "cp_spice": "100p",
        "tau_s_ns": 200.0,
        "q_ion_spice": "0.056f",    # ~351 e- Lindhard 5 keV 31P+ @ 300 K (w=3.62 eV)
        "v_thr_spice": "0.01567",   # 15.67 mV (5.5-sigma ENC=89.9 e- rms)
        "rhys1_Ohm": 1.0e3,
        "rhys2_Ohm": 3.3e6,
        "rterm_Ohm": 49.9,
        "rbias_Ohm": 10e6,
        "cbias_F": 10e-9,
        "rdac_Ohm": 1.0e3,
        "cdac_F": 100e-9,
        "vcca_V": 2.5,
        "vssa_V": -2.5,
        "vccd_V": 3.3,
        "vbias_V": -30.0,
    },
}

DEFAULT_PROFILE = "cold100k"

# Nominal locked analog circuit parameters (Exp127 F3: COLD_100K / 1.2 us / 1 GOhm)
CIRCUIT_PARAMS = {"channels": CHANNELS, **PROFILES[DEFAULT_PROFILE]}


def get_profile(profile: str = DEFAULT_PROFILE) -> dict:
    key = profile.strip().lower()
    if key not in PROFILES:
        raise ValueError(f"Unknown board profile {profile!r}; expected one of {sorted(PROFILES)}")
    return PROFILES[key]


@dataclass(frozen=True)
class Component:
    ref: str
    value: str
    footprint: str
    kind: str           # "diode", "opamp", "comparator", "dac", "R", "C", "conn"
    mpn_tag: str        # "{Aday-COTS}", "{Ozel-Uretim}", "{Pasif-COTS}"
    required_pins: tuple[str, ...]


@dataclass
class BoardDesign:
    components: list[Component]
    nets: dict[str, list[tuple[str, str]]]  # net_name -> list[(ref, pin)]
    profile: str = DEFAULT_PROFILE


def build_board_design(channels: int = CHANNELS, profile: str = DEFAULT_PROFILE) -> BoardDesign:
    """Construct complete electrical graph (components + merged unique nets)."""
    cfg = get_profile(profile)
    comps: list[Component] = []
    nets: dict[str, list[tuple[str, str]]] = defaultdict(list)

    def connect(net: str, ref: str, pin: str | int) -> None:
        nets[net].append((ref, str(pin)))

    # Shared connectors, star-ground, bulk bias filter, bulk power decoupling, SPI DAC
    comps.extend([
        Component("JPWR", "PWR_4PIN_VCCA_VSSA_VCCD", "HDR_1x4_2.54mm", "conn", "{Pasif-COTS}", ("1", "2", "3", "4")),
        Component("JBIAS", "HV_BIAS_SMA", "SMA_EDGE", "conn", "{Pasif-COTS}", ("1", "2")),
        Component("JFPGA", "FPGA_IF_24PIN", "HDR_2x12_1.27mm", "conn", "{Pasif-COTS}", tuple(str(i) for i in range(1, 25))),
        Component("R_STAR", "0R_STAR_GND", "0603", "R", "{Pasif-COTS}", ("1", "2")),
        Component("RBIAS_BULK", "100k_100V", "0603", "R", "{Pasif-COTS}", ("1", "2")),
        Component("CBIAS_BULK", "100nF_100V_X7R", "0805", "C", "{Pasif-COTS}", ("1", "2")),
        Component("CBULK_P", "10uF_10V", "0805", "C", "{Pasif-COTS}", ("1", "2")),
        Component("CBULK_N", "10uF_10V", "0805", "C", "{Pasif-COTS}", ("1", "2")),
        Component("CBULK_D", "10uF_10V", "0805", "C", "{Pasif-COTS}", ("1", "2")),
        Component("UDAC", "DAC8568_16B_8CH_SPI", "TSSOP-16", "dac", "{Aday-COTS}", tuple(str(i) for i in range(1, 17))),
        Component("CD_DAC", "100nF_C0G", "0402", "C", "{Pasif-COTS}", ("1", "2")),
        Component("CREF_DAC", "100nF_C0G", "0402", "C", "{Pasif-COTS}", ("1", "2")),
    ])

    # Power rails & star ground
    connect("VCCA", "JPWR", 1)
    connect("VSSA", "JPWR", 2)
    connect("VCCD", "JPWR", 3)
    connect("AGND", "JPWR", 4)
    connect("AGND", "R_STAR", 1)
    connect("DGND", "R_STAR", 2)

    connect("VCCA", "CBULK_P", 1); connect("AGND", "CBULK_P", 2)
    connect("VSSA", "CBULK_N", 1); connect("AGND", "CBULK_N", 2)
    connect("VCCD", "CBULK_D", 1); connect("DGND", "CBULK_D", 2)

    # HV bias bulk filter
    connect("HV_BIAS_IN", "JBIAS", 1)
    connect("AGND", "JBIAS", 2)
    connect("HV_BIAS_IN", "RBIAS_BULK", 1)
    connect("HV_BIAS_FILT", "RBIAS_BULK", 2)
    connect("HV_BIAS_FILT", "CBIAS_BULK", 1)
    connect("AGND", "CBIAS_BULK", 2)

    # DAC8568 TSSOP-16 connections (pins 1-16)
    connect("DGND", "UDAC", 1)          # LDAC_N -> low (auto update)
    connect("SPI_CS_N", "UDAC", 2)      # SYNC_N
    connect("VCCD", "UDAC", 3)          # AVDD
    connect("DAC_VREF", "UDAC", 8)      # VREFIN/OUT
    connect("VCCD", "UDAC", 9)          # CLR_N -> high
    connect("DGND", "UDAC", 14)         # GND
    connect("SPI_MOSI", "UDAC", 15)     # DIN
    connect("SPI_SCLK", "UDAC", 16)     # SCLK
    connect("VCCD", "CD_DAC", 1); connect("DGND", "CD_DAC", 2)
    connect("DAC_VREF", "CREF_DAC", 1); connect("AGND", "CREF_DAC", 2)

    # JFPGA 24-pin header: pins 1..8 = COUNT_HIT[0..7], 9..16 = DGND returns,
    # 17 = SPI_SCLK, 18 = SPI_MOSI, 19 = SPI_CS_N, 20 = VCCD, 21..24 = DGND
    connect("SPI_SCLK", "JFPGA", 17)
    connect("SPI_MOSI", "JFPGA", 18)
    connect("SPI_CS_N", "JFPGA", 19)
    connect("VCCD", "JFPGA", 20)
    for gpin in (9, 10, 11, 12, 13, 14, 15, 16, 21, 22, 23, 24):
        connect("DGND", "JFPGA", gpin)

    dac_out_pins = (4, 5, 6, 7, 10, 11, 12, 13)

    for ch in range(channels):
        p = f"CH{ch}"
        comps.extend([
            Component(f"D{ch}", "IBIC_PIXEL_DIODE_C0p5", "CUSTOM_FLIPCHIP", "diode", "{Ozel-Uretim}", ("1", "2")),
            Component(f"RBIAS{ch}", "10M_100V", "0402", "R", "{Pasif-COTS}", ("1", "2")),
            Component(f"CBIAS{ch}", "10nF_100V_C0G", "0603", "C", "{Pasif-COTS}", ("1", "2")),
            Component(f"U{ch}A", "LTC6268_CSA_FET", "SOIC-8", "opamp", "{Aday-COTS}", ("1", "2", "3", "4", "6", "7")),
            Component(f"CF{ch}", "0.25pF_C0G", "0402", "C", "{Pasif-COTS}", ("1", "2")),
            Component(f"RF{ch}", cfg["rf_label"], "0402", "R", "{Pasif-COTS}", ("1", "2")),
            Component(f"CS{ch}", cfg["cs_label"], "0402", "C", "{Pasif-COTS}", ("1", "2")),
            Component(f"RS1{ch}", "2.00k_0.1pct", "0402", "R", "{Pasif-COTS}", ("1", "2")),
            Component(f"U{ch}B", "ADA4817-1_SHAPER", "SOIC-8-1EP", "opamp", "{Aday-COTS}", ("1", "2", "3", "4", "6", "7", "8", "EP")),
            Component(f"RG1{ch}", "100R_0.1pct", "0402", "R", "{Pasif-COTS}", ("1", "2")),
            Component(f"RG2{ch}", "13.5k_0.1pct", "0402", "R", "{Pasif-COTS}", ("1", "2")),
            Component(f"RS2{ch}", "2.00k_0.1pct", "0402", "R", "{Pasif-COTS}", ("1", "2")),
            Component(f"CP{ch}", cfg["cp_label"], "0402", "C", "{Pasif-COTS}", ("1", "2")),
            Component(f"RDAC{ch}", "1.00k_1pct", "0402", "R", "{Pasif-COTS}", ("1", "2")),
            Component(f"CDAC{ch}", "100nF_C0G", "0402", "C", "{Pasif-COTS}", ("1", "2")),
            Component(f"RHYS1{ch}", "1.00k_1pct", "0402", "R", "{Pasif-COTS}", ("1", "2")),
            Component(f"RHYS2{ch}", "3.30M_1pct", "0402", "R", "{Pasif-COTS}", ("1", "2")),
            Component(f"U{ch}C", "TLV3501_CMP_4p5NS", "SOT-23-6", "comparator", "{Aday-COTS}", ("1", "2", "3", "4", "5", "6")),
            Component(f"RTERM{ch}", "49.9R_1pct", "0402", "R", "{Pasif-COTS}", ("1", "2")),
            Component(f"CD{ch}AP", "100nF_C0G", "0402", "C", "{Pasif-COTS}", ("1", "2")),
            Component(f"CD{ch}AN", "100nF_C0G", "0402", "C", "{Pasif-COTS}", ("1", "2")),
            Component(f"CD{ch}BP", "100nF_C0G", "0402", "C", "{Pasif-COTS}", ("1", "2")),
            Component(f"CD{ch}BN", "100nF_C0G", "0402", "C", "{Pasif-COTS}", ("1", "2")),
            Component(f"CD{ch}C", "100nF_C0G", "0402", "C", "{Pasif-COTS}", ("1", "2")),
        ])

        # Per-channel HV bias filter & pixel diode
        connect("HV_BIAS_FILT", f"RBIAS{ch}", 1)
        connect(f"{p}.DET_BIAS", f"RBIAS{ch}", 2)
        connect(f"{p}.DET_BIAS", f"CBIAS{ch}", 1)
        connect("AGND", f"CBIAS{ch}", 2)
        connect(f"{p}.DET_BIAS", f"D{ch}", 2)

        # Single merged summing node: D{ch}.1 + CF{ch}.2 + RF{ch}.2 + U{ch}A IN- (LTC6268IS8 S8 pin 6)
        # Exact Analog Devices LTC6268IS8 S8 pinout: 1:~SHDN, 2:V+, 3:OUT, 4:V-, 5:NC, 6:-IN, 7:+IN, 8:NC
        connect(f"{p}.CSA_SUM", f"D{ch}", 1)
        connect(f"{p}.CSA_SUM", f"CF{ch}", 2)
        connect(f"{p}.CSA_SUM", f"RF{ch}", 2)
        connect(f"{p}.CSA_SUM", f"U{ch}A", 6)
        connect("AGND", f"U{ch}A", 7)   # +IN (pin 7) tied cleanly to AGND (no floating input!)

        # CSA output (pin 3) -> feedback + CR differentiator input
        connect(f"{p}.CSA_OUT", f"U{ch}A", 3)
        connect(f"{p}.CSA_OUT", f"CF{ch}", 1)
        connect(f"{p}.CSA_OUT", f"RF{ch}", 1)
        connect(f"{p}.CSA_OUT", f"CS{ch}", 1)

        # CR differentiator (CS + RS1) -> Shaper U{ch}B +IN (ADA4817-1ARDZ SOIC-8-EP pin 3)
        connect(f"{p}.CR_OUT", f"CS{ch}", 2)
        connect(f"{p}.CR_OUT", f"RS1{ch}", 1)
        connect(f"{p}.CR_OUT", f"U{ch}B", 3)
        connect("AGND", f"RS1{ch}", 2)

        # Shaper U{ch}B non-inverting gain feedback (RG1=100R, RG2=13.5k -> G=136)
        # Exact ADA4817-1ARDZ SOIC-8-EP pinout: 1:FB, 2:-IN, 3:+IN, 4:-VS, 5:NC, 6:OUT, 7:+VS, 8:PD, EP:-VS
        connect(f"{p}.SHP_FB", f"U{ch}B", 2)
        connect(f"{p}.SHP_FB", f"RG1{ch}", 1)
        connect(f"{p}.SHP_FB", f"RG2{ch}", 1)
        connect("AGND", f"RG1{ch}", 2)
        connect(f"{p}.SHP_GAIN", f"U{ch}B", 6)
        connect(f"{p}.SHP_GAIN", f"U{ch}B", 1)  # Pin 1 FB tied to OUT/RG2 node
        connect(f"{p}.SHP_GAIN", f"RG2{ch}", 2)
        connect(f"{p}.SHP_GAIN", f"RS2{ch}", 1)

        # RC integrator (RS2 + CP) -> comparator hysteresis input
        connect(f"{p}.SHP_OUT", f"RS2{ch}", 2)
        connect(f"{p}.SHP_OUT", f"CP{ch}", 1)
        connect(f"{p}.SHP_OUT", f"RHYS1{ch}", 1)
        connect("AGND", f"CP{ch}", 2)

        # Per-channel SPI DAC threshold + RC filter -> comparator -IN (TI SBOS321 TLV3501 DBV pin 1)
        # Exact TI SBOS321 SOT-23-6 DBV pinout: 1:-IN, 2:V-, 3:+IN, 4:V+, 5:OUT, 6:SHDN(active-HIGH)
        connect(f"{p}.THRESH_RAW", "UDAC", dac_out_pins[ch])
        connect(f"{p}.THRESH_RAW", f"RDAC{ch}", 1)
        connect(f"{p}.THRESH", f"RDAC{ch}", 2)
        connect(f"{p}.THRESH", f"CDAC{ch}", 1)
        connect(f"{p}.THRESH", f"U{ch}C", 1)
        connect("AGND", f"CDAC{ch}", 2)

        # Hysteresis comparator U{ch}C -> RTERM -> JFPGA (Pin 3:+IN, Pin 5:OUT)
        connect(f"{p}.CMP_INP", f"RHYS1{ch}", 2)
        connect(f"{p}.CMP_INP", f"RHYS2{ch}", 1)
        connect(f"{p}.CMP_INP", f"U{ch}C", 3)
        connect(f"{p}.CMP_OUT", f"U{ch}C", 5)
        connect(f"{p}.CMP_OUT", f"RHYS2{ch}", 2)
        connect(f"{p}.CMP_OUT", f"RTERM{ch}", 1)
        connect(f"{p}.COUNT_HIT", f"RTERM{ch}", 2)
        connect(f"{p}.COUNT_HIT", "JFPGA", 1 + ch)

        # Active IC power, enable/PD/SHDN & local 100 nF decoupling
        connect("VCCA", f"U{ch}A", 1); connect("VCCA", f"U{ch}A", 2); connect("VSSA", f"U{ch}A", 4)
        connect("VCCA", f"CD{ch}AP", 1); connect("AGND", f"CD{ch}AP", 2)
        connect("VSSA", f"CD{ch}AN", 1); connect("AGND", f"CD{ch}AN", 2)

        connect("VCCA", f"U{ch}B", 7); connect("VCCA", f"U{ch}B", 8)
        connect("VSSA", f"U{ch}B", 4); connect("VSSA", f"U{ch}B", "EP")
        connect("VCCA", f"CD{ch}BP", 1); connect("AGND", f"CD{ch}BP", 2)
        connect("VSSA", f"CD{ch}BN", 1); connect("AGND", f"CD{ch}BN", 2)

        connect("VCCD", f"U{ch}C", 4); connect("DGND", f"U{ch}C", 2); connect("DGND", f"U{ch}C", 6)
        connect("VCCD", f"CD{ch}C", 1); connect("DGND", f"CD{ch}C", 2)

    return BoardDesign(components=comps, nets=dict(nets), profile=profile)


def validate_netlist(design: BoardDesign, channels: int = CHANNELS) -> list[str]:
    """Run strict Electrical Rules Check (ERC); returns list of error strings (empty = PASS)."""
    errors: list[str] = []
    comp_map: dict[str, Component] = {}
    for c in design.components:
        if c.ref in comp_map:
            errors.append(f"Duplicate component ref: {c.ref}")
        comp_map[c.ref] = c

    # 1. Verify no pin belongs to >1 net, no unknown ref, and every net has >=2 nodes
    pin_owner: dict[tuple[str, str], str] = {}
    for net_name, nodes in design.nets.items():
        if len(nodes) < 2:
            errors.append(f"Single-node (dangling) net: {net_name} ({nodes})")
        seen_in_net = set()
        for ref, pin in nodes:
            if ref not in comp_map:
                errors.append(f"Net {net_name} references unknown component {ref}")
            key = (ref, pin)
            if key in seen_in_net:
                errors.append(f"Duplicate pin {ref}.{pin} in net {net_name}")
            seen_in_net.add(key)
            if key in pin_owner:
                errors.append(
                    f"Pin conflict: {ref}.{pin} connected to both {pin_owner[key]} and {net_name}"
                )
            pin_owner[key] = net_name

    # 2. Verify every required pin of every component is connected (no floating op-amp inputs/rails)
    for c in design.components:
        for pin in c.required_pins:
            if (c.ref, pin) not in pin_owner:
                errors.append(f"Unconnected (floating) required pin: {c.ref}.{pin} ({c.value})")

    # 3. Verify mandatory power nets and 8 independent per-channel threshold & hit nets
    for req_net in ("VCCA", "VSSA", "VCCD", "AGND", "DGND", "SPI_SCLK", "SPI_MOSI", "SPI_CS_N"):
        if req_net not in design.nets:
            errors.append(f"Missing required global net: {req_net}")
    for ch in range(channels):
        for suffix in ("CSA_SUM", "CSA_OUT", "CR_OUT", "SHP_FB", "SHP_OUT", "THRESH", "COUNT_HIT"):
            n = f"CH{ch}.{suffix}"
            if n not in design.nets:
                errors.append(f"Missing channel net: {n}")
        # Verify exact LTC6268IS8 S8 pinout (1:~SHDN=VCCA, 2:V+=VCCA, 3:OUT=CSA_OUT, 4:V-=VSSA, 6:-IN=CSA_SUM, 7:+IN=AGND)
        if pin_owner.get((f"U{ch}A", "1")) != "VCCA" or pin_owner.get((f"U{ch}A", "2")) != "VCCA":
            errors.append(f"Channel {ch} LTC6268IS8 pin 1 (~SHDN) / pin 2 (V+) must tie to VCCA")
        if pin_owner.get((f"U{ch}A", "3")) != f"CH{ch}.CSA_OUT" or pin_owner.get((f"U{ch}A", "6")) != f"CH{ch}.CSA_SUM":
            errors.append(f"Channel {ch} LTC6268IS8 pin 3 (OUT) / pin 6 (-IN) pinout mismatch")
        if pin_owner.get((f"U{ch}A", "7")) != "AGND":
            errors.append(f"Channel {ch} LTC6268IS8 pin 7 (+IN) must tie to AGND")
        # Verify exact ADA4817-1ARDZ SOIC-8-EP pinout (1:FB=SHP_GAIN, 8:PD=VCCA, EP=VSSA)
        if pin_owner.get((f"U{ch}B", "1")) != f"CH{ch}.SHP_GAIN" or pin_owner.get((f"U{ch}B", "8")) != "VCCA":
            errors.append(f"Channel {ch} ADA4817-1ARDZ pin 1 (FB) / pin 8 (PD) pinout mismatch")
        if pin_owner.get((f"U{ch}B", "EP")) != "VSSA":
            errors.append(f"Channel {ch} ADA4817-1ARDZ exposed thermal pad EP must tie to VSSA")
        # Verify exact TI SBOS321 TLV3501AIDBVR SOT-23-6 DBV pinout
        if pin_owner.get((f"U{ch}C", "1")) != f"CH{ch}.THRESH":
            errors.append(f"Channel {ch} TLV3501 pin 1 (-IN) not driven by dedicated CH{ch}.THRESH")
        if pin_owner.get((f"U{ch}C", "4")) != "VCCD":
            errors.append(f"Channel {ch} TLV3501 pin 4 (V+) must tie to VCCD")
        if pin_owner.get((f"U{ch}C", "5")) != f"CH{ch}.CMP_OUT":
            errors.append(f"Channel {ch} TLV3501 pin 5 (OUT) must drive CH{ch}.CMP_OUT")
        if pin_owner.get((f"U{ch}C", "6")) != "DGND":
            errors.append(f"Channel {ch} TLV3501 pin 6 (SHDN, active-HIGH) must tie to DGND to enable")

    # 4. Verify active ICs carry candidate-COTS MPN values (not bare placeholders)
    banned = {"CSA_OPAMP_JFET", "SHAPER_OPAMP", "COMPARATOR_FAST", "THRESHOLD_DAC"}
    for c in design.components:
        if c.value in banned:
            errors.append(f"Unresolved placeholder part value on {c.ref}: {c.value}")

    return errors


def render_kicad_netlist(design: BoardDesign) -> str:
    """Emit standard KiCad (version D) S-expression netlist."""
    cfg = get_profile(design.profile)
    lines = [
        "(export (version D)",
        "  (design",
        '    (source "src/board/detector_frontend.py")',
        '    (date "2026-11-23")',
        f'    (tool "ALM detector_frontend.py v2.1 ({cfg["name"]}, Exp127 ERC-verified)")',
        '    (sheet (number 1) (name "/") (tstamps "/")',
        '      (title_block',
        f'        (title "Atom Lithography Machine - 8-Ch In-Vacuum IBIC Front-End ({cfg["name"]})")',
        '        (rev "v2.1")',
        f'        (comment (number 1) (value "BOM S3.1/S3.2/S3.3 + S2.4; RF={cfg["rf_spice"]}, CS=CP={cfg["cs_spice"]}, tau_s={cfg["tau_s_ns"]:.0f} ns"))',
        '        (comment (number 2) (value "Candidate COTS MPNs {Aday-COTS}; no PCB layout")))))',
        "  (components",
    ]
    for c in design.components:
        lines.append(
            f'    (comp (ref {c.ref}) (value "{c.value}") '
            f'(footprint "{c.footprint}") (fields (field (name "Status") "{c.mpn_tag}")))'
        )
    lines.append("  )")
    lines.append("  (nets")
    for code, (net_name, nodes) in enumerate(sorted(design.nets.items()), start=1):
        lines.append(f'    (net (code {code}) (name "{net_name}")')
        for ref, pin in nodes:
            lines.append(f"      (node (ref {ref}) (pin {pin}))")
        lines.append("    )")
    lines.append("  )")
    lines.append(")")
    return "\n".join(lines) + "\n"


def render_spice_deck(channels: int = CHANNELS, profile: str = DEFAULT_PROFILE) -> str:
    """Emit native SPICE3 / ngspice-47 deck matching the 8-channel IBIC circuit."""
    p = get_profile(profile)
    temp_c = p["temp_K"] - 273.15
    tran_stop = "8.0u" if p["tau_s_ns"] >= 800.0 else "2.5u"
    tran_step = "5n" if p["tau_s_ns"] >= 800.0 else "2n"
    rhys2_spice = "3.3Meg"
    lines = [
        f"* Atom Lithography Machine - 8-Channel IBIC Detector Front-End (v2.1, Profile={p['name']}, Exp127)",
        "* Native ngspice-47 macromodel deck ({Aday-COTS}; no physical lab measurement).",
        f"* Locked P91 5 keV 31P+ @ {p['temp_K']:.0f} K: RF={p['rf_spice']}, CS=CP={p['cs_spice']} (tau_s={p['tau_s_ns']:.0f} ns), Q_ION={p['q_ion_spice']}.",
        f"* Rails: VCCA=+{p['vcca_V']}V, VSSA={p['vssa_V']}V, VCCD=+{p['vccd_V']}V, VBIAS={p['vbias_V']}V.",
        "",
        f".temp {temp_c:.2f}",
        "",
        f".param C_DET=0.5p  C_PAR=0.25p  C_F=0.25p  R_F={p['rf_spice']}",
        f".param C_S={p['cs_spice']}   R_S1=2.0k    R_G1=100   R_G2=13.5k",
        f".param R_S2=2.0k   C_P={p['cp_spice']}    R_HYS1=1.0k R_HYS2={rhys2_spice}  R_TERM=49.9",
        f".param Q_ION={p['q_ion_spice']}  TAU_COL=1.5n  V_THR={p['v_thr_spice']}",
        "",
        "* Behavioral single-pole op-amp macromodels matching datasheet GBP, C_in & white e_n (native ngspice B-sources)",
        ".subckt OPAMP_LTC6268 inp inn vcc vss out",
        "Cin inp inn 0.45p",
        "Rin inp inn 1T noisy=0",
        "* White series voltage noise: 2.0 nV/rtHz (zero DC offset)",
        "Rnw nw 0 241.43235 temp=26.85",
        "Evn inp_int inp nw 0 1.0",
        "Egain n1 0 inp_int inn 1e5",
        "* GBP = 500 MHz -> dominant pole f_p = 5 kHz (R=1k, C=31.83nF)",
        "Rp n1 n2 1k noisy=0",
        "Cp n2 0 31.8309886n",
        "Bbuf n_out 0 V = 0.5*(v(vcc)+v(vss)) + (0.5*(v(vcc)-v(vss))-0.1) * tanh((v(n2) - 0.5*(v(vcc)+v(vss))) / (0.5*(v(vcc)-v(vss))-0.1 + 1m))",
        "Rout n_out out 1 noisy=0",
        ".ends OPAMP_LTC6268",
        "",
        ".subckt OPAMP_ADA4817 inp inn vcc vss out",
        "Cin inp inn 1.3p",
        "Rin inp inn 500G noisy=0",
        "* White series voltage noise: 4.0 nV/rtHz (zero DC offset)",
        "Rnw nw 0 965.7294 temp=26.85",
        "Evn inp_int inp nw 0 1.0",
        "Egain n1 0 inp_int inn 1e5",
        "* GBP = 1.05 GHz -> dominant pole f_p = 10.5 kHz (R=1k, C=15.16nF)",
        "Rp n1 n2 1k noisy=0",
        "Cp n2 0 15.1576136n",
        "Bbuf n_out 0 V = 0.5*(v(vcc)+v(vss)) + (0.5*(v(vcc)-v(vss))-0.2) * tanh((v(n2) - 0.5*(v(vcc)+v(vss))) / (0.5*(v(vcc)-v(vss))-0.2 + 1m))",
        "Rout n_out out 1 noisy=0",
        ".ends OPAMP_ADA4817",
        "",
        ".subckt CMP_TLV3501 inp inn vcc gnd shdn out",
        "* 4.5 ns comparator macromodel with rail-to-rail 0..VCCD output & smooth active-HIGH SHDN (TI SBOS321)",
        "Braw n1 gnd V = v(vcc, gnd) * 0.5 * (1 + tanh((0.5*v(vcc, gnd) - v(shdn, gnd)) / 0.05)) * 0.5 * (1 + tanh(v(inp, inn) / 0.2m))",
        "Rdel n1 out 100 noisy=0",
        "Cdel out gnd 45p",
        ".ends CMP_TLV3501",
        "",
        "* Single IBIC Front-End Channel Subcircuit (csa_sum exposed for top-level stimulus & .noise)",
        ".subckt IBIC_CHANNEL csa_sum hv_bias thresh_in count_hit vcca vssa vccd agnd dgnd",
        "* Per-channel HV bias filter & pixel capacitance",
        "Rbias hv_bias det_bias 10Meg",
        "Cbias det_bias agnd 10n",
        "Cdet  csa_sum agnd {C_DET + C_PAR}",
        "* CSA stage (LTC6268): positive output when Iion extracts charge (csa_sum -> agnd)",
        "Xcsa  agnd csa_sum vcca vssa csa_out OPAMP_LTC6268",
        "Cf    csa_out csa_sum {C_F}",
        "Rf    csa_out csa_sum {R_F}",
        f"* Buffered CR-RC active shaper (tau_1 = tau_2 = {p['tau_s_ns']:.0f} ns, G_stage = 136 -> G_peak = 50)",
        "Cs    csa_out cr_out {C_S}",
        "Rs1   cr_out  agnd   {R_S1}",
        "Xshp  cr_out  shp_fb vcca vssa shp_gain OPAMP_ADA4817",
        "Rg1   shp_fb  agnd   {R_G1}",
        "Rg2   shp_gain shp_fb {R_G2}",
        "Rs2   shp_gain shp_out {R_S2}",
        "Cp    shp_out agnd   {C_P}",
        "* Per-channel DAC threshold RC filter & non-latching hysteresis comparator (TLV3501, V_hys=3.0mV < V_THR)",
        "Rdac  thresh_in thresh 1k",
        "Cdac  thresh agnd 100n",
        "Rhys1 shp_out cmp_inp {R_HYS1}",
        "Rhys2 cmp_out cmp_inp {R_HYS2}",
        "Xcmp  cmp_inp thresh vccd dgnd dgnd cmp_out CMP_TLV3501",
        "Rterm cmp_out count_hit {R_TERM}",
        ".ends IBIC_CHANNEL",
        "",
        "* Board Power Supplies & Star Ground",
        f"Vcca vcca agnd DC {p['vcca_V']}",
        f"Vssa vssa agnd DC {p['vssa_V']}",
        f"Vccd vccd dgnd DC {p['vccd_V']}",
        f"Vbias hv_in agnd DC {p['vbias_V']}",
        "Rstar agnd dgnd 1m noisy=0",
        "Rbias_bulk hv_in hv_filt 100k",
        "Cbias_bulk hv_filt agnd 100n",
        "Vagnd agnd 0 DC 0",
        "",
        "* 8-Channel Tile Instantiation (CH0..CH7) with Individual DAC Thresholds & Top-Level Ion Stimulus",
        "* CH0 receives 5 keV 31P+ charge pulse Q_ION (csa_sum -> agnd = positive hole-collection polarity); CH1..CH7 dark",
    ]
    for ch in range(channels):
        if ch == 0:
            lines.append(
                "Iion0 csa_sum_0 agnd DC 0 AC 1 PULSE(0 {Q_ION/TAU_COL} 50n 0.1n 0.1n 1.4n 1m)"
            )
        else:
            lines.append(f"Iion{ch} csa_sum_{ch} agnd DC 0")
        lines.append(f"Vthr{ch} thr_raw_{ch} agnd DC {{V_THR}}")
        lines.append(
            f"Xch{ch} csa_sum_{ch} hv_filt thr_raw_{ch} count_hit_{ch} vcca vssa vccd agnd dgnd IBIC_CHANNEL"
        )
        lines.append(f"Rfpga{ch} count_hit_{ch} dgnd 10k")

    lines.extend([
        "",
        "* Native ngspice-47 Batch Analyses (AC, TRAN, NOISE)",
        ".control",
        "set noaskquit",
        "ac dec 100 100 100Meg",
        "meas ac z_peak_ohm MAX vm(Xch0.shp_out)",
        f"tran {tran_step} {tran_stop}",
        "meas tran csa_peak_v MAX v(Xch0.csa_out)",
        "meas tran shp_peak_v MAX v(Xch0.shp_out)",
        "meas tran hit0_init_v FIND v(count_hit_0) AT=10n",
        "meas tran hit0_max_v MAX v(count_hit_0)",
        f"meas tran hit0_end_v FIND v(count_hit_0) AT={tran_stop}",
        "meas tran hit1_max_v MAX v(count_hit_1)",
        "meas tran hit7_max_v MAX v(count_hit_7)",
        "noise v(Xch0.shp_out) Iion0 dec 50 1k 50Meg",
        "setplot noise2",
        "let shp_onoise_rms_v = onoise_total",
        "print shp_onoise_rms_v",
        "quit 0",
        ".endc",
        ".end",
    ])
    return "\n".join(lines) + "\n"


def generate_board_artifacts(
    out_dir: Path | None = None,
    profile: str = DEFAULT_PROFILE,
) -> tuple[Path, Path, BoardDesign, list[str]]:
    """Build, ERC-validate, and write detector_frontend.net and detector_frontend.cir."""
    target_dir = out_dir or Path(__file__).resolve().parent
    design = build_board_design(CHANNELS, profile=profile)
    errors = validate_netlist(design, CHANNELS)
    if errors:
        raise RuntimeError("ERC FAILED:\n" + "\n".join(errors))
    net_path = target_dir / "detector_frontend.net"
    cir_path = target_dir / "detector_frontend.cir"
    net_path.write_text(render_kicad_netlist(design), encoding="utf-8")
    cir_path.write_text(render_spice_deck(CHANNELS, profile=profile), encoding="utf-8")
    return net_path, cir_path, design, errors


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Generate & ERC-validate 8-ch IBIC front-end netlist/SPICE")
    ap.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()),
        default=DEFAULT_PROFILE,
        help="operating profile: cold100k (locked default: 1 GOhm, 600 pF, 1.2 us) or rt300k (100 MOhm, 100 pF, 200 ns)",
    )
    args = ap.parse_args(argv)
    net_path, cir_path, design, errors = generate_board_artifacts(profile=args.profile)
    cfg = get_profile(args.profile)
    print(
        f"BOARD_ARTIFACTS_OK: profile={cfg['name']} comps={len(design.components)} "
        f"nets={len(design.nets)} erc_errors={len(errors)} "
        f"RF={cfg['rf_spice']} CS=CP={cfg['cs_spice']} Q_ION={cfg['q_ion_spice']} "
        f"net={net_path.name} cir={cir_path.name}"
    )


if __name__ == "__main__":
    main()
