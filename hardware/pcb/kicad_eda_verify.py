"""Shared KiCad 8 S-Expression Builder, Strict ERC/DRC Verifier, ngspice Runner & Python MNA Cross-Checker.

Shared electronics EDA kernel for all Stage-2 custom PCBs in ``hardware/pcb/*``:
  * ``ibic_cryo_frontend_v3`` (3-PCB split kit)
  * ``fpga_brain_carrier``, ``blanker_asic_mezzanine``, ``cryo_cmos_4k_carrier``
  * ``ion_column_hv_dac``, ``laser_aom_pyrometer_afe``, ``safety_interlock_1oo2d``
  * ``cryo_rf_harness_icd``

Epistemic contract:
  All generated KiCad 8 schematics/PCBs and SPICE runs carry explicit M0/M1
  ``DESIGN_ONLY`` metadata (``no_lab_measurement=true``, ``no_physical_fab=true``,
  ``iec61508_certified=false``, ``semi_s2_certified=false``).
  Zero host-specific hardcoded paths; ``ngspice`` is discovered portably via
  ``shutil.which`` and ``Path.home() / ".local/bin/ngspice"``.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
import fnmatch
import heapq
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Sequence
import uuid

import numpy as np

# ---------------------------------------------------------------------------
# Constants & Epistemic Defaults
# ---------------------------------------------------------------------------

KICAD_SCH_VERSION = "20231120"
KICAD_PCB_VERSION = "20240108"

DEFAULT_EPISTEMIC_META: dict[str, Any] = {
    "design_stage": "M0/M1_DESIGN_ONLY",
    "no_lab_measurement": True,
    "no_physical_fab": True,
    "iec61508_certified": False,
    "semi_s2_certified": False,
}

BANNED_PLACEHOLDER_VALUES: frozenset[str] = frozenset({
    "",
    "TBD",
    "TODO",
    "PLACEHOLDER",
    "UNSPECIFIED",
    "CSA_OPAMP_JFET",
    "SHAPER_OPAMP",
    "COMPARATOR_FAST",
    "THRESHOLD_DAC",
})


def _det_uuid(seed: str) -> str:
    """Deterministic UUIDv5 so KiCad 8 artifacts are reproducible across runs."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"alm.kicad8.{seed}"))


def _q(text: str) -> str:
    """Escape a string as a KiCad S-expression double-quoted literal."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


# ---------------------------------------------------------------------------
# 1. Data Model (BoardSpec, ComponentSpec, NetSpec, StackupLayer, ...)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StackupLayer:
    name: str
    layer_type: str  # "signal", "power", "mixed", "core", "prepreg", "soldermask"
    thickness_mm: float
    epsilon_r: float = 1.0
    loss_tangent: float = 0.0
    material: str = ""

    @property
    def is_copper(self) -> bool:
        return self.layer_type in {"signal", "power", "mixed", "copper"} or self.name.endswith(".Cu")


@dataclass(frozen=True)
class PinSpec:
    number: str
    name: str = ""
    electrical_type: str = "passive"  # input, output, bidirectional, power_in, power_out, passive, open_collector, no_connect
    dx_mm: float = 0.0
    dy_mm: float = 0.0
    pad_w_mm: float = 0.6
    pad_h_mm: float = 0.6
    drill_mm: float = 0.0  # >0.0 => through-hole pad on *.Cu


@dataclass(frozen=True)
class ComponentSpec:
    ref: str
    value: str
    footprint: str
    x_mm: float
    y_mm: float
    rotation_deg: float = 0.0
    layer: str = "F.Cu"
    pins: tuple[PinSpec, ...] = ()
    lib_id: str = ""
    mpn: str = ""
    epistemic_tag: str = "{Aday-COTS}"
    bom_id: str = ""
    sch_x_mm: float | None = None
    sch_y_mm: float | None = None
    body_w_mm: float = 0.0
    body_h_mm: float = 0.0
    edge_mount: bool = False


@dataclass(frozen=True)
class NetSpec:
    name: str
    nodes: tuple[tuple[str, str], ...]
    net_class: str = "Default"
    is_power: bool = False
    has_pwr_flag: bool = False
    voltage_v: float = 0.0
    target_z0_ohm: float | None = None
    diff_pair_with: str | None = None


@dataclass(frozen=True)
class TraceSpec:
    net: str
    layer: str
    points_mm: tuple[tuple[float, float], ...]
    width_mm: float
    is_guard_ring: bool = False
    diff_spacing_mm: float | None = None


@dataclass(frozen=True)
class ViaSpec:
    net: str
    x_mm: float
    y_mm: float
    diameter_mm: float = 0.6
    drill_mm: float = 0.3
    layers: tuple[str, str] = ("F.Cu", "B.Cu")


@dataclass(frozen=True)
class ZoneSpec:
    net: str
    layer: str
    polygon_mm: tuple[tuple[float, float], ...]
    clearance_mm: float = 0.2
    min_thickness_mm: float = 0.2
    is_keepout: bool = False


@dataclass(frozen=True)
class KeepoutSpec:
    name: str
    kind: str  # "air_slot" (Edge.Cuts milled cutout) | "copper_keepout" (rule area)
    layers: tuple[str, ...]
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float


@dataclass(frozen=True)
class CreepageRule:
    net_pattern: str
    working_voltage_v: float
    min_clearance_mm: float
    min_creepage_mm: float
    standard: str = "IPC-2221B / IEC 61010-1"
    pollution_degree: int = 2
    material_group: str = "I"
    differential_pairs: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class DesignRules:
    min_trace_width_mm: float = 0.127
    min_clearance_mm: float = 0.127
    min_via_drill_mm: float = 0.20
    min_annular_ring_mm: float = 0.10
    min_edge_clearance_mm: float = 0.50
    min_slot_clearance_mm: float = 0.30
    impedance_tol_pct: float = 5.0
    max_dielectric_field_v_per_mm: float = 15000.0


@dataclass(frozen=True)
class BoardSpec:
    name: str
    title: str
    rev: str
    bom_ids: tuple[str, ...]
    width_mm: float
    height_mm: float
    stackup: tuple[StackupLayer, ...]
    components: tuple[ComponentSpec, ...]
    nets: tuple[NetSpec, ...]
    traces: tuple[TraceSpec, ...] = ()
    vias: tuple[ViaSpec, ...] = ()
    zones: tuple[ZoneSpec, ...] = ()
    keepouts: tuple[KeepoutSpec, ...] = ()
    creepage_rules: tuple[CreepageRule, ...] = ()
    rules: DesignRules = DesignRules()
    epistemic_meta: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_EPISTEMIC_META))
    notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# 2. Footprint Pad Geometry Helpers & Controlled-Impedance / HV Calculators
# ---------------------------------------------------------------------------

def auto_footprint_pads(
    footprint: str,
    pin_numbers: Sequence[str],
    pin_names: dict[str, str] | None = None,
    pin_types: dict[str, str] | None = None,
) -> tuple[PinSpec, ...]:
    """Generate physically realistic, non-overlapping pad geometry for standard footprints."""
    fp = footprint.upper()
    pnames = pin_names or {}
    ptypes = pin_types or {}
    pins_list = [str(p) for p in pin_numbers]
    n = len(pins_list)

    def _mk(num: str, dx: float, dy: float, pw: float, ph: float, drill: float = 0.0) -> PinSpec:
        return PinSpec(
            number=num,
            name=pnames.get(num, num),
            electrical_type=ptypes.get(num, "passive"),
            dx_mm=round(dx, 4),
            dy_mm=round(dy, 4),
            pad_w_mm=round(pw, 4),
            pad_h_mm=round(ph, 4),
            drill_mm=round(drill, 4),
        )

    # 2-pin SMD chip passives
    if n == 2:
        if "0402" in fp:
            return (_mk(pins_list[0], -0.48, 0.0, 0.50, 0.60), _mk(pins_list[1], 0.48, 0.0, 0.50, 0.60))
        if "0603" in fp:
            return (_mk(pins_list[0], -0.80, 0.0, 0.80, 0.90), _mk(pins_list[1], 0.80, 0.0, 0.80, 0.90))
        if "0805" in fp:
            return (_mk(pins_list[0], -1.00, 0.0, 0.95, 1.30), _mk(pins_list[1], 1.00, 0.0, 0.95, 1.30))
        if "1206" in fp:
            return (_mk(pins_list[0], -1.55, 0.0, 1.10, 1.65), _mk(pins_list[1], 1.55, 0.0, 1.10, 1.65))
        if "1210" in fp:
            return (_mk(pins_list[0], -1.55, 0.0, 1.10, 2.50), _mk(pins_list[1], 1.55, 0.0, 1.10, 2.50))
        if "2512" in fp or "HV_MELF" in fp or "HV_RES" in fp:
            return (_mk(pins_list[0], -3.10, 0.0, 1.40, 3.10), _mk(pins_list[1], 3.10, 0.0, 1.40, 3.10))
        if "SMA" in fp or "SMB" in fp or "SMP" in fp or "COAX" in fp or "MMCX" in fp:
            return (
                _mk(pins_list[0], 0.0, 0.0, 0.85, 2.20),
                _mk(pins_list[1], 2.54, 0.0, 1.40, 2.20, drill=0.90),
            )
        if "SHV" in fp or "MHV" in fp or "BNC" in fp:
            return (
                _mk(pins_list[0], 0.0, 0.0, 1.80, 1.80, drill=1.00),
                _mk(pins_list[1], 5.08, 0.0, 2.00, 2.00, drill=1.20),
            )
        if "FLIPCHIP" in fp or "DIODE" in fp:
            return (_mk(pins_list[0], -1.00, 0.0, 0.70, 0.80), _mk(pins_list[1], 1.00, 0.0, 0.70, 0.80))
        # Generic 2-pin
        return (_mk(pins_list[0], -1.27, 0.0, 1.00, 1.00), _mk(pins_list[1], 1.27, 0.0, 1.00, 1.00))

    # 3-pin connectors / coax with 2 gnd / SOT-23-3
    if n == 3 and ("SMA" in fp or "SMB" in fp or "COAX" in fp):
        return (
            _mk(pins_list[0], 0.0, 0.0, 0.85, 2.20),
            _mk(pins_list[1], -2.54, 0.0, 1.40, 2.20, drill=0.90),
            _mk(pins_list[2], 2.54, 0.0, 1.40, 2.20, drill=0.90),
        )

    # SOT-23-5 / SOT-23-6 / TSOT-23-5 (UJ-5) (0.95 mm pitch)
    if "SOT-23" in fp or "SOT23" in fp or "TSOT" in fp:
        pitch = 0.95
        half = (n + 1) // 2
        res: list[PinSpec] = []
        for idx, pnum in enumerate(pins_list):
            if idx < half:
                dy = (idx - (half - 1) / 2.0) * pitch
                res.append(_mk(pnum, -1.35, dy, 0.95, 0.55))
            else:
                ridx = idx - half
                rem = n - half
                if n == 5:
                    # Standard 5-pin SOT-23-5 / TSOT-23-5 (pins 4 & 5 at +/-0.95 mm, skipping center)
                    dy = (1.0 - 2.0 * ridx) * pitch
                else:
                    dy = ((rem - 1) / 2.0 - ridx) * pitch
                res.append(_mk(pnum, 1.35, dy, 0.95, 0.55))
        return tuple(res)

    # SOIC (1.27 mm pitch) / MSOP / TSSOP / DFN (0.65 mm or 0.50 mm pitch)
    if any(k in fp for k in ("SOIC", "MSOP", "TSSOP", "DFN", "DIP", "SOP", "RELAY")):
        if "SOIC" in fp or "SOP" in fp:
            pitch, x_off, pw, ph, drill = 1.27, 2.70, 1.45, 0.60, 0.0
        elif "TSSOP" in fp or "MSOP" in fp:
            pitch, x_off, pw, ph, drill = 0.65, 2.90, 1.35, 0.40, 0.0
        elif "DFN" in fp:
            pitch, x_off, pw, ph, drill = 0.50, 1.45, 0.80, 0.28, 0.0
        elif "RELAY" in fp:
            pitch, x_off, pw, ph, drill = 5.08, 3.81, 1.80, 1.80, 1.00
        else:
            pitch, x_off, pw, ph, drill = 2.54, 3.81, 1.60, 1.60, 0.80
        half = (n + 1) // 2
        res = []
        for idx, pnum in enumerate(pins_list):
            if idx < half:
                dy = (idx - (half - 1) / 2.0) * pitch
                res.append(_mk(pnum, -x_off, dy, pw, ph, drill))
            else:
                ridx = idx - half
                rem = n - half
                dy = ((rem - 1) / 2.0 - ridx) * pitch
                res.append(_mk(pnum, x_off, dy, pw, ph, drill))
        return tuple(res)

    # QFN / QFP 4-sided packages
    if "QFN" in fp or "QFP" in fp or "LQFP" in fp:
        pitch = 0.50 if "QFN" in fp else 0.50
        per_side = max(1, math.ceil(n / 4))
        span = (per_side - 1) * pitch
        offset = span / 2.0 + 1.35
        res = []
        for idx, pnum in enumerate(pins_list):
            side = idx // per_side
            pos = (idx % per_side) - (per_side - 1) / 2.0
            if side == 0:  # left
                res.append(_mk(pnum, -offset, pos * pitch, 0.80, 0.28))
            elif side == 1:  # bottom
                res.append(_mk(pnum, pos * pitch, offset, 0.28, 0.80))
            elif side == 2:  # right
                res.append(_mk(pnum, offset, -pos * pitch, 0.80, 0.28))
            else:  # top
                res.append(_mk(pnum, -pos * pitch, -offset, 0.28, 0.80))
        return tuple(res)

    # BGA / grid array
    if "BGA" in fp or "FFG" in fp or "FMC" in fp:
        pitch = 1.00 if "BGA" in fp or "FFG" in fp else 1.27
        cols = max(2, int(math.ceil(math.sqrt(n))))
        rows = int(math.ceil(n / cols))
        res = []
        for idx, pnum in enumerate(pins_list):
            r = idx // cols
            c = idx % cols
            dx = (c - (cols - 1) / 2.0) * pitch
            dy = (r - (rows - 1) / 2.0) * pitch
            res.append(_mk(pnum, dx, dy, 0.50, 0.50))
        return tuple(res)

    # 2-row Headers (HDR_2xN / PINHEADER_2xN)
    if "2X" in fp or "DUAL" in fp or "HDR_2" in fp:
        pitch = 1.27 if "1.27" in fp else 2.54
        pw = 0.85 if pitch < 2.0 else 1.60
        drill = 0.50 if pitch < 2.0 else 0.90
        rows = (n + 1) // 2
        res = []
        for idx, pnum in enumerate(pins_list):
            row = idx // 2
            col = idx % 2
            dx = (col - 0.5) * pitch
            dy = (row - (rows - 1) / 2.0) * pitch
            res.append(_mk(pnum, dx, dy, pw, pw, drill))
        return tuple(res)

    # 1-row Headers / terminal blocks / generic
    pitch = 1.27 if "1.27" in fp else (5.08 if "5.08" in fp or "HV" in fp else 2.54)
    pw = 0.85 if pitch < 2.0 else 1.65
    drill = 0.50 if pitch < 2.0 else 0.95
    res = []
    for idx, pnum in enumerate(pins_list):
        dy = (idx - (n - 1) / 2.0) * pitch
        res.append(_mk(pnum, 0.0, dy, pw, pw, drill))
    return tuple(res)


def ipc2221_min_spacing_mm(voltage_v: float, coated: bool = False, altitude_m: float = 2000.0) -> tuple[float, float]:
    """Return (min_clearance_mm, min_creepage_mm) per IPC-2221B Table 6-1 & IEC 61010-1 PD2.

    Conservative engineering envelope for uncoated/coated HV PCBs (Material Group I,
    CTI >= 600 such as Rogers RO4350B / PTFE / Al2O3 / Isola FR408HR).
    """
    v = abs(float(voltage_v))
    alt_factor = 1.0 if altitude_m <= 2000.0 else 1.0 + 0.14 * ((altitude_m - 2000.0) / 1000.0)
    if v <= 15.0:
        clr, crp = 0.13, 0.15
    elif v <= 30.0:
        clr, crp = 0.13, 0.25
    elif v <= 50.0:
        clr, crp = 0.25 if coated else 0.60, 0.60
    elif v <= 100.0:
        clr, crp = 0.40 if coated else 0.60, 1.00
    elif v <= 150.0:
        clr, crp = 0.50 if coated else 0.80, 1.40
    elif v <= 300.0:
        clr, crp = 0.80 if coated else 1.25, 2.00
    elif v <= 500.0:
        clr, crp = 1.25 if coated else 2.50, 3.20
    else:
        # IPC-2221B >500 V linear extension:
        # Uncoated external: 2.5 mm + 0.005 mm/V; Coated: 0.8 mm + 0.00305 mm/V
        # IEC 61010-1 creepage ~2.5 mm/kV (MG I) with safety margin for HV decks
        if coated:
            clr = 0.80 + 0.00305 * (v - 500.0)
        else:
            clr = 2.50 + 0.0050 * (v - 500.0)
        crp = max(clr * 1.25, 3.20 + 0.0025 * (v - 500.0))
    return (round(clr * alt_factor, 3), round(crp, 3))


def calc_microstrip_z0(width_mm: float, h_mm: float, t_mm: float, er: float) -> float:
    """Hammerstad-Jensen analytical microstrip impedance Z0 [Ohm] (<0.2% accuracy)."""
    w = max(float(width_mm), 1e-6)
    h = max(float(h_mm), 1e-6)
    t = max(float(t_mm), 0.0)
    er = max(float(er), 1.0)
    if t > 0.0:
        # Hammerstad finite copper thickness correction
        th = t / h
        wh = w / h
        coth_arg = math.sqrt(6.517 * wh)
        coth_val = 1.0 / math.tanh(min(coth_arg, 50.0))
        dw1 = (t / math.pi) * math.log(1.0 + (4.0 * math.e) / (th * coth_val * coth_val))
        w_eff = w + 0.5 * dw1 * (1.0 + 1.0 / math.cosh(math.sqrt(er - 1.0)))
    else:
        w_eff = w
    u = w_eff / h
    a_u = 1.0 + (1.0 / 49.0) * math.log((u**4 + (u / 52.0) ** 2) / (u**4 + 0.432)) + (1.0 / 18.7) * math.log(
        1.0 + (u / 18.1) ** 3
    )
    b_er = 0.564 * (((er - 0.9) / (er + 3.0)) ** 0.053)
    er_eff = 0.5 * (er + 1.0) + 0.5 * (er - 1.0) * ((1.0 + 10.0 / u) ** (-a_u * b_er))
    f_u = 6.0 + (2.0 * math.pi - 6.0) * math.exp(-((30.666 / u) ** 0.7528))
    z0 = (60.0 / math.sqrt(er_eff)) * math.log(f_u / u + math.sqrt(1.0 + (2.0 / u) ** 2))
    return float(z0)


def calc_stripline_z0(width_mm: float, b_mm: float, t_mm: float, er: float) -> float:
    """Wadell / Cohn symmetric stripline characteristic impedance Z0 [Ohm] (<0.5% accuracy)."""
    w = max(float(width_mm), 1e-6)
    b = max(float(b_mm), 1e-6)
    t = max(float(t_mm), 0.0)
    er = max(float(er), 1.0)
    h_eff = max(b - t, 1e-6)
    if t > 0.0:
        m = 6.0 / (3.0 + 2.0 * t / h_eff)
        dw = (t / math.pi) * (
            1.0
            - 0.5 * math.log((t / (2.0 * b - t)) ** 2 + (0.0796 * t / (w + 1.1 * t)) ** m)
        )
        w_eff = w + dw
    else:
        w_eff = w
    r = (4.0 / math.pi) * (h_eff / max(w_eff, 1e-6))
    z0 = (30.0 / math.sqrt(er)) * math.log(1.0 + r * (2.0 * r + math.sqrt((2.0 * r) ** 2 + 6.27)))
    return float(z0)


def solve_stripline_width_mm(target_z0: float, b_mm: float, t_mm: float, er: float) -> float:
    """Solve symmetric stripline trace width [mm] for exact target Z0 via bisection."""
    lo, hi = 0.02, 20.0 * b_mm
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if calc_stripline_z0(mid, b_mm, t_mm, er) > target_z0:
            lo = mid
        else:
            hi = mid
    return round(0.5 * (lo + hi), 4)


def calc_diff_microstrip_z0(width_mm: float, spacing_mm: float, h_mm: float, t_mm: float, er: float) -> float:
    """IPC-2141 edge-coupled differential microstrip impedance Z_diff [Ohm]."""
    z0_se = calc_microstrip_z0(width_mm, h_mm, t_mm, er)
    return float(2.0 * z0_se * (1.0 - 0.48 * math.exp(-0.96 * max(spacing_mm, 1e-6) / max(h_mm, 1e-6))))


def calc_diff_stripline_z0(width_mm: float, spacing_mm: float, b_mm: float, t_mm: float, er: float) -> float:
    """IPC-2141 edge-coupled differential stripline impedance Z_diff [Ohm]."""
    z0_se = calc_stripline_z0(width_mm, b_mm, t_mm, er)
    return float(2.0 * z0_se * (1.0 - 0.347 * math.exp(-2.9 * max(spacing_mm, 1e-6) / max(b_mm, 1e-6))))


def solve_microstrip_width_mm(target_z0: float, h_mm: float, t_mm: float, er: float) -> float:
    """Solve microstrip trace width [mm] for exact target Z0 via bisection."""
    lo, hi = 0.02, 20.0 * h_mm
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if calc_microstrip_z0(mid, h_mm, t_mm, er) > target_z0:
            lo = mid
        else:
            hi = mid
    return round(0.5 * (lo + hi), 4)


def solve_diff_microstrip_width_mm(
    target_zdiff: float, spacing_mm: float, h_mm: float, t_mm: float, er: float
) -> float:
    """Solve edge-coupled differential microstrip width [mm] for target Z_diff."""
    lo, hi = 0.02, 20.0 * h_mm
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if calc_diff_microstrip_z0(mid, spacing_mm, h_mm, t_mm, er) > target_zdiff:
            lo = mid
        else:
            hi = mid
    return round(0.5 * (lo + hi), 4)


def solve_diff_stripline_width_mm(
    target_zdiff: float, spacing_mm: float, b_mm: float, t_mm: float, er: float
) -> float:
    """Solve edge-coupled differential stripline width [mm] for target Z_diff."""
    lo, hi = 0.02, 20.0 * b_mm
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if calc_diff_stripline_z0(mid, spacing_mm, b_mm, t_mm, er) > target_zdiff:
            lo = mid
        else:
            hi = mid
    return round(0.5 * (lo + hi), 4)


def make_manhattan_trace(
    net: str,
    layer: str,
    p0: tuple[float, float],
    p1: tuple[float, float],
    width_mm: float,
    mid_x: float | None = None,
    mid_y: float | None = None,
    is_guard_ring: bool = False,
    diff_spacing_mm: float | None = None,
) -> TraceSpec:
    """Construct an orthogonal Manhattan polyline TraceSpec between two points."""
    x0, y0 = round(p0[0], 4), round(p0[1], 4)
    x1, y1 = round(p1[0], 4), round(p1[1], 4)
    if abs(x0 - x1) < 1e-4 or abs(y0 - y1) < 1e-4:
        pts: tuple[tuple[float, float], ...] = ((x0, y0), (x1, y1))
    elif mid_x is not None:
        mx = round(mid_x, 4)
        pts = ((x0, y0), (mx, y0), (mx, y1), (x1, y1))
    elif mid_y is not None:
        my = round(mid_y, 4)
        pts = ((x0, y0), (x0, my), (x1, my), (x1, y1))
    else:
        pts = ((x0, y0), (x1, y0), (x1, y1))
    # Deduplicate consecutive identical points
    clean: list[tuple[float, float]] = []
    for pt in pts:
        if not clean or math.hypot(pt[0] - clean[-1][0], pt[1] - clean[-1][1]) > 1e-4:
            clean.append(pt)
    return TraceSpec(
        net=net,
        layer=layer,
        points_mm=tuple(clean),
        width_mm=round(width_mm, 4),
        is_guard_ring=is_guard_ring,
        diff_spacing_mm=diff_spacing_mm,
    )


# ---------------------------------------------------------------------------
# 3. Strict Recursive S-Expression Parser (Rejects Malformed KiCad Files)
# ---------------------------------------------------------------------------

class SexprParseError(ValueError):
    """Raised when a KiCad S-expression is syntactically malformed."""


def parse_sexpr(text: str) -> list[Any]:
    """Strictly parse a single top-level KiCad S-expression into nested Python lists.

    Rejects:
      - Empty input or non-list top-level expression
      - Unbalanced opening '(' or unexpected closing ')'
      - Unterminated double-quoted strings
      - Trailing garbage tokens after the top-level closing ')'
    """
    n = len(text)
    if n == 0:
        raise SexprParseError("Empty S-expression input")

    tokens: list[tuple[str, str, int]] = []  # (kind, value, pos)
    i = 0
    while i < n:
        ch = text[i]
        if ch in " \t\r\n":
            i += 1
            continue
        if ch == "(":
            tokens.append(("LPAREN", "(", i))
            i += 1
            continue
        if ch == ")":
            tokens.append(("RPAREN", ")", i))
            i += 1
            continue
        if ch == '"':
            start = i
            i += 1
            buf: list[str] = []
            closed = False
            while i < n:
                c = text[i]
                if c == "\\":
                    if i + 1 >= n:
                        raise SexprParseError(f"Unterminated escape in string at offset {start}")
                    nxt = text[i + 1]
                    buf.append("\n" if nxt == "n" else nxt)
                    i += 2
                elif c == '"':
                    i += 1
                    closed = True
                    break
                else:
                    buf.append(c)
                    i += 1
            if not closed:
                raise SexprParseError(f"Unterminated double-quoted string at offset {start}")
            tokens.append(("STRING", "".join(buf), start))
            continue
        # Bare atom
        start = i
        while i < n and text[i] not in ' \t\r\n()"':
            i += 1
        tokens.append(("ATOM", text[start:i], start))

    if not tokens:
        raise SexprParseError("Whitespace-only S-expression input")
    if tokens[0][0] != "LPAREN":
        raise SexprParseError(f"Expected '(' at start of S-expression, got {tokens[0][1]!r} at offset {tokens[0][2]}")

    # Iterative stack-based parser (handles arbitrarily deep trees without recursion limit issues)
    stack: list[list[Any]] = []
    root: list[Any] | None = None
    for idx, (kind, val, pos) in enumerate(tokens):
        if kind == "LPAREN":
            if root is not None:
                raise SexprParseError(f"Unexpected trailing '(' after top-level expression at offset {pos}")
            new_list: list[Any] = []
            if stack:
                stack[-1].append(new_list)
            stack.append(new_list)
        elif kind == "RPAREN":
            if not stack:
                raise SexprParseError(f"Unexpected ')' without matching '(' at offset {pos}")
            finished = stack.pop()
            if not stack:
                root = finished
        else:
            if not stack:
                raise SexprParseError(f"Unexpected token {val!r} outside top-level list at offset {pos}")
            stack[-1].append(val)

    if stack:
        raise SexprParseError(f"Unclosed '(' — {len(stack)} open list(s) remaining at EOF")
    assert root is not None
    return root


def _find_children(node: list[Any], tag: str) -> list[list[Any]]:
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == tag]


def _find_first(node: list[Any], tag: str) -> list[Any] | None:
    for c in node[1:]:
        if isinstance(c, list) and c and c[0] == tag:
            return c
    return None


# ---------------------------------------------------------------------------
# 4. KiCad 8 Schematic Writer (.kicad_sch, version 20231120)
# ---------------------------------------------------------------------------

def _infer_lib_id(comp: ComponentSpec) -> str:
    if comp.lib_id:
        return comp.lib_id
    r = comp.ref.upper()
    if r.startswith("R"):
        return f"Device:R_{len(comp.pins)}P"
    if r.startswith("C"):
        return f"Device:C_{len(comp.pins)}P"
    if r.startswith("L"):
        return f"Device:L_{len(comp.pins)}P"
    if r.startswith("D"):
        return f"Device:D_{len(comp.pins)}P"
    if r.startswith("J") or r.startswith("P"):
        return f"Connector:Conn_{len(comp.pins)}P"
    return f"Custom:{re.sub(r'[^A-Za-z0-9_]', '_', comp.value)}_{len(comp.pins)}P"


def _symbol_pin_layout(pins: tuple[PinSpec, ...]) -> tuple[float, float, dict[str, tuple[float, float, int, PinSpec]]]:
    """Compute KiCad lib_symbol box half-width/half-height and per-pin (lx, ly, angle) coordinates.

    All coordinates lie cleanly on a 2.54 mm grid so schematic wires and labels connect exactly.
    """
    n = len(pins)
    left_n = (n + 1) // 2
    right_n = n - left_n
    rows = max(1, left_n, right_n)
    half_h = max(2.54, ((rows + 1) * 2.54) / 2.0)
    # Snap half_h to multiple of 2.54 mm
    half_h = math.ceil(half_h / 2.54) * 2.54
    half_w = 5.08 if n <= 4 else 7.62
    pin_len = 2.54
    pin_map: dict[str, tuple[float, float, int, PinSpec]] = {}
    for idx, ps in enumerate(pins):
        if idx < left_n:
            row_offset = (left_n - 1) / 2.0 - idx
            ly = round(round(row_offset) * 2.54 if left_n % 2 == 1 else (left_n / 2.0 - idx - 0.5) * 2.54, 4)
            # Snap to 1.27 mm grid cleanly
            lx = round(-(half_w + pin_len), 4)
            pin_map[ps.number] = (lx, ly, 0, ps)
        else:
            ridx = idx - left_n
            ly = round(round((right_n - 1) / 2.0 - ridx) * 2.54 if right_n % 2 == 1 else (right_n / 2.0 - ridx - 0.5) * 2.54, 4)
            lx = round(half_w + pin_len, 4)
            pin_map[ps.number] = (lx, ly, 180, ps)
    return half_w, half_h, pin_map


def write_kicad_sch(board_spec: BoardSpec, path: str | Path) -> Path:
    """Emit a strictly valid KiCad 8 schematic (.kicad_sch, version 20231120).

    Every component pin is wired via an explicit ``(wire ...)`` segment to its
    net ``(label ...)`` or ``(global_label ...)`` so schematic-level ERC
    reconstructs the complete netlist directly from wire geometry.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    root_uuid = _det_uuid(f"sch.root.{board_spec.name}")

    # Build (ref, pin) -> net_name lookup and net metadata
    pin_to_net: dict[tuple[str, str], str] = {}
    net_meta: dict[str, NetSpec] = {}
    for ns in board_spec.nets:
        net_meta[ns.name] = ns
        for ref, pin in ns.nodes:
            pin_to_net[(ref, str(pin))] = ns.name

    # Collect unique lib_symbol definitions keyed by (lib_id, pin_signature)
    lib_defs: dict[str, tuple[float, float, dict[str, tuple[float, float, int, PinSpec]]]] = {}
    comp_lib_ids: dict[str, str] = {}
    for comp in board_spec.components:
        pins = comp.pins or auto_footprint_pads(comp.footprint, ("1", "2"))
        base_id = _infer_lib_id(comp)
        sig = ",".join(f"{p.number}:{p.name}:{p.electrical_type}" for p in pins)
        # Disambiguate if two components share base_id with different pin signatures
        lib_id = base_id
        if lib_id in lib_defs:
            existing_pins = lib_defs[lib_id][2]
            existing_sig = ",".join(
                f"{ps.number}:{ps.name}:{ps.electrical_type}"
                for _, (_, _, _, ps) in existing_pins.items()
            )
            if existing_sig != sig:
                lib_id = f"{base_id}_{_det_uuid(sig)[:6]}"
        if lib_id not in lib_defs:
            lib_defs[lib_id] = _symbol_pin_layout(pins)
        comp_lib_ids[comp.ref] = lib_id

    pwr_flag_nets = [ns.name for ns in board_spec.nets if ns.has_pwr_flag]
    lines: list[str] = [
        "(kicad_sch",
        f"  (version {KICAD_SCH_VERSION})",
        '  (generator "kicad_eda_verify")',
        '  (generator_version "8.0")',
        f"  (uuid {_q(root_uuid)})",
        '  (paper "A2")',
        "  (title_block",
        f"    (title {_q(board_spec.title)})",
        '    (date "2026-11-25")',
        f"    (rev {_q(board_spec.rev)})",
        '    (company "Atom Lithography Machine — M0/M1 DESIGN_ONLY")',
        f"    (comment 1 {_q('BOM: ' + ', '.join(board_spec.bom_ids))})",
        f"    (comment 2 {_q('Epistemic: design_stage=' + str(board_spec.epistemic_meta.get('design_stage', 'M0/M1_DESIGN_ONLY')) + ', no_lab_measurement=' + str(board_spec.epistemic_meta.get('no_lab_measurement', True)) + ', iec61508_certified=' + str(board_spec.epistemic_meta.get('iec61508_certified', False)))})",
        "  )",
        "  (lib_symbols",
    ]

    # Emit power:PWR_FLAG if any power net uses a power flag
    if pwr_flag_nets:
        lines.extend([
            '    (symbol "power:PWR_FLAG" (power) (pin_numbers hide) (pin_names (offset 0) hide)',
            "      (in_bom yes) (on_board yes)",
            '      (property "Reference" "#FLG" (at 0 1.905 0) (effects (font (size 1.27 1.27)) hide))',
            '      (property "Value" "PWR_FLAG" (at 0 3.81 0) (effects (font (size 1.27 1.27))))',
            '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
            '      (symbol "PWR_FLAG_0_0"',
            "        (polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.016 1.905) (xy 0 2.54) (xy 1.016 1.905) (xy 0 1.27))",
            "          (stroke (width 0) (type default)) (fill (type none))))",
            '      (symbol "PWR_FLAG_0_1"',
            '        (pin power_out line (at 0 0 90) (length 0)',
            '          (name "pwr" (effects (font (size 1.27 1.27))))',
            '          (number "1" (effects (font (size 1.27 1.27))))))',
            "    )",
        ])

    # Emit each unique symbol definition
    for lib_id, (half_w, half_h, pin_map) in sorted(lib_defs.items()):
        sym_short = lib_id.split(":", 1)[-1]
        lines.extend([
            f"    (symbol {_q(lib_id)} (in_bom yes) (on_board yes)",
            f'      (property "Reference" "U" (at 0 {half_h + 2.54:.4f} 0) (effects (font (size 1.27 1.27))))',
            f'      (property "Value" {_q(sym_short)} (at 0 {-half_h - 2.54:.4f} 0) (effects (font (size 1.27 1.27))))',
            '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
            f"      (symbol {_q(sym_short + '_0_1')}",
            f"        (rectangle (start {-half_w:.4f} {half_h:.4f}) (end {half_w:.4f} {-half_h:.4f})",
            "          (stroke (width 0.254) (type default)) (fill (type background))))",
            f"      (symbol {_q(sym_short + '_1_1')}",
        ])
        for pnum, (lx, ly, ang, ps) in pin_map.items():
            etype = ps.electrical_type or "passive"
            pname = ps.name if ps.name else pnum
            lines.append(
                f"        (pin {etype} line (at {lx:.4f} {ly:.4f} {ang}) (length 2.54) "
                f"(name {_q(pname)} (effects (font (size 1.27 1.27)))) "
                f"(number {_q(pnum)} (effects (font (size 1.27 1.27)))))"
            )
        lines.append("      )")
        lines.append("    )")
    lines.append("  )")

    # Auto-layout schematic coordinates cleanly without overlapping pins/wires
    col_x_start = 45.72
    col_pitch = 66.04
    max_cols = 8
    cur_col = 0
    cur_y = 35.56
    row_max_h = 0.0
    comp_coords: dict[str, tuple[float, float]] = {}

    for comp in board_spec.components:
        lib_id = comp_lib_ids[comp.ref]
        _, half_h, _ = lib_defs[lib_id]
        if comp.sch_x_mm is not None and comp.sch_y_mm is not None:
            comp_coords[comp.ref] = (round(comp.sch_x_mm, 4), round(comp.sch_y_mm, 4))
            continue
        sy = round(cur_y + half_h + 5.08, 4)
        sx = round(col_x_start + cur_col * col_pitch, 4)
        comp_coords[comp.ref] = (sx, sy)
        row_max_h = max(row_max_h, 2.0 * half_h + 15.24)
        cur_col += 1
        if cur_col >= max_cols:
            cur_col = 0
            cur_y = round(cur_y + row_max_h + 5.08, 4)
            row_max_h = 0.0

    # Place symbols, wires, and labels
    wire_lines: list[str] = []
    label_lines: list[str] = []
    stub_len = 5.08

    for comp in board_spec.components:
        lib_id = comp_lib_ids[comp.ref]
        half_w, half_h, pin_map = lib_defs[lib_id]
        sx, sy = comp_coords[comp.ref]
        suuid = _det_uuid(f"sch.sym.{board_spec.name}.{comp.ref}")
        bom_id = comp.bom_id or (board_spec.bom_ids[0] if board_spec.bom_ids else "")
        lines.extend([
            f"  (symbol (lib_id {_q(lib_id)}) (at {sx:.4f} {sy:.4f} 0) (unit 1)",
            "    (in_bom yes) (on_board yes) (dnp no)",
            f"    (uuid {_q(suuid)})",
            f'    (property "Reference" {_q(comp.ref)} (at {sx:.4f} {sy - half_h - 2.54:.4f} 0) (effects (font (size 1.27 1.27))))',
            f'    (property "Value" {_q(comp.value)} (at {sx:.4f} {sy + half_h + 2.54:.4f} 0) (effects (font (size 1.27 1.27))))',
            f'    (property "Footprint" {_q(comp.footprint)} (at {sx:.4f} {sy:.4f} 0) (effects (font (size 1.27 1.27)) hide))',
            f'    (property "BOM_ID" {_q(bom_id)} (at {sx:.4f} {sy:.4f} 0) (effects (font (size 1.27 1.27)) hide))',
            f'    (property "MPN" {_q(comp.mpn or comp.value)} (at {sx:.4f} {sy:.4f} 0) (effects (font (size 1.27 1.27)) hide))',
            f'    (property "Epistemic" {_q(comp.epistemic_tag)} (at {sx:.4f} {sy:.4f} 0) (effects (font (size 1.27 1.27)) hide))',
        ])
        for pnum, (lx, ly, ang, ps) in pin_map.items():
            puuid = _det_uuid(f"sch.pin.{board_spec.name}.{comp.ref}.{pnum}")
            lines.append(f"    (pin {_q(pnum)} (uuid {_q(puuid)}))")
            # Sheet pin coordinates: KiCad lib Y points UP, sheet Y points DOWN
            px = round(sx + lx, 4)
            py = round(sy - ly, 4)
            net_name = pin_to_net.get((comp.ref, pnum))
            if net_name is not None:
                wx = round(px - stub_len, 4) if ang == 0 else round(px + stub_len, 4)
                wy = py
                wuuid = _det_uuid(f"sch.wire.{board_spec.name}.{comp.ref}.{pnum}")
                luuid = _det_uuid(f"sch.lbl.{board_spec.name}.{comp.ref}.{pnum}")
                wire_lines.append(
                    f"  (wire (pts (xy {px:.4f} {py:.4f}) (xy {wx:.4f} {wy:.4f})) "
                    f"(stroke (width 0) (type default)) (uuid {_q(wuuid)}))"
                )
                ns = net_meta[net_name]
                if ns.is_power:
                    label_lines.append(
                        f"  (global_label {_q(net_name)} (shape input) (at {wx:.4f} {wy:.4f} {180 if ang == 0 else 0}) "
                        f"(fields_autoplaced yes) (effects (font (size 1.27 1.27))) (uuid {_q(luuid)}))"
                    )
                else:
                    label_lines.append(
                        f"  (label {_q(net_name)} (at {wx:.4f} {wy:.4f} {180 if ang == 0 else 0}) "
                        f"(fields_autoplaced yes) (effects (font (size 1.27 1.27))) (uuid {_q(luuid)}))"
                    )
            elif ps.electrical_type == "no_connect":
                nuuid = _det_uuid(f"sch.nc.{board_spec.name}.{comp.ref}.{pnum}")
                label_lines.append(f"  (no_connect (at {px:.4f} {py:.4f}) (uuid {_q(nuuid)}))")
        lines.extend([
            f'    (instances (project {_q(board_spec.name)} (path {_q("/" + root_uuid)} (reference {_q(comp.ref)}) (unit 1))))',
            "  )",
        ])

    # Place power:PWR_FLAG instances in a dedicated clean bank at the bottom
    flag_y = round(cur_y + row_max_h + 20.32, 4)
    for fidx, net_name in enumerate(pwr_flag_nets, start=1):
        fx = round(col_x_start + (fidx - 1) * 25.4, 4)
        fy = flag_y
        fref = f"#FLG{fidx:02d}"
        fuuid = _det_uuid(f"sch.pwrflag.{board_spec.name}.{net_name}")
        wuuid = _det_uuid(f"sch.pwrwire.{board_spec.name}.{net_name}")
        luuid = _det_uuid(f"sch.pwrlbl.{board_spec.name}.{net_name}")
        lines.extend([
            f'  (symbol (lib_id "power:PWR_FLAG") (at {fx:.4f} {fy:.4f} 0) (unit 1)',
            "    (in_bom yes) (on_board yes) (dnp no)",
            f"    (uuid {_q(fuuid)})",
            f'    (property "Reference" {_q(fref)} (at {fx:.4f} {fy - 2.54:.4f} 0) (effects (font (size 1.27 1.27)) hide))',
            f'    (property "Value" "PWR_FLAG" (at {fx:.4f} {fy - 5.08:.4f} 0) (effects (font (size 1.27 1.27))))',
            '    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
            f'    (pin "1" (uuid {_q(_det_uuid(f"sch.pwrpin.{board_spec.name}.{net_name}"))}))',
            f'    (instances (project {_q(board_spec.name)} (path {_q("/" + root_uuid)} (reference {_q(fref)}) (unit 1))))',
            "  )",
        ])
        wire_lines.append(
            f"  (wire (pts (xy {fx:.4f} {fy:.4f}) (xy {fx:.4f} {fy + 5.08:.4f})) "
            f"(stroke (width 0) (type default)) (uuid {_q(wuuid)}))"
        )
        label_lines.append(
            f"  (global_label {_q(net_name)} (shape input) (at {fx:.4f} {fy + 5.08:.4f} 270) "
            f"(fields_autoplaced yes) (effects (font (size 1.27 1.27))) (uuid {_q(luuid)}))"
        )

    lines.extend(wire_lines)
    lines.extend(label_lines)
    lines.append('  (sheet_instances (path "/" (page "1")))')
    lines.append(")")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# 5. KiCad 8 PCB Writer (.kicad_pcb, version 20240108)
# ---------------------------------------------------------------------------

def _kicad_layer_number(name: str, copper_layers: list[StackupLayer]) -> int:
    if name == "F.Cu":
        return 0
    if name == "B.Cu":
        return 31
    inner = [l.name for l in copper_layers if l.name not in ("F.Cu", "B.Cu")]
    if name in inner:
        return inner.index(name) + 1
    raise ValueError(f"Unknown copper layer name: {name!r}")


def _pad_abs_xy(comp: ComponentSpec, ps: PinSpec) -> tuple[float, float, float, float]:
    """Compute pad center (px, py) and rotated bounding-box (w, h) in board coordinates."""
    rad = math.radians(comp.rotation_deg)
    c, s = math.cos(rad), math.sin(rad)
    # KiCad PCB rotation is CCW in math / CW on screen; standard rotation transform:
    rx = ps.dx_mm * c + ps.dy_mm * s
    ry = -ps.dx_mm * s + ps.dy_mm * c
    px = comp.x_mm + rx
    py = comp.y_mm + ry
    bw = abs(ps.pad_w_mm * c) + abs(ps.pad_h_mm * s)
    bh = abs(ps.pad_w_mm * s) + abs(ps.pad_h_mm * c)
    return (round(px, 4), round(py, 4), round(bw, 4), round(bh, 4))


def write_kicad_pcb(board_spec: BoardSpec, path: str | Path) -> Path:
    """Emit a strictly valid KiCad 8 PCB file (.kicad_pcb, version 20240108)."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    copper_layers = [l for l in board_spec.stackup if l.is_copper]
    total_thickness = sum(l.thickness_mm for l in board_spec.stackup) or 1.6

    # Deterministic net ID map (0 = unconnected)
    net_ids: dict[str, int] = {"": 0}
    for idx, ns in enumerate(board_spec.nets, start=1):
        net_ids[ns.name] = idx
    pin_to_net: dict[tuple[str, str], str] = {}
    for ns in board_spec.nets:
        for ref, pin in ns.nodes:
            pin_to_net[(ref, str(pin))] = ns.name

    lines: list[str] = [
        "(kicad_pcb",
        f"  (version {KICAD_PCB_VERSION})",
        '  (generator "kicad_eda_verify")',
        '  (generator_version "8.0")',
        f"  (general (thickness {total_thickness:.4f}) (legacy_teardrops no))",
        '  (paper "A4")',
        "  (title_block",
        f"    (title {_q(board_spec.title)})",
        '    (date "2026-11-25")',
        f"    (rev {_q(board_spec.rev)})",
        '    (company "Atom Lithography Machine — M0/M1 DESIGN_ONLY")',
        f"    (comment 1 {_q('BOM: ' + ', '.join(board_spec.bom_ids))})",
        f"    (comment 2 {_q('Epistemic: no_lab_measurement=' + str(board_spec.epistemic_meta.get('no_lab_measurement', True)) + ', no_physical_fab=' + str(board_spec.epistemic_meta.get('no_physical_fab', True)) + ', iec61508_certified=' + str(board_spec.epistemic_meta.get('iec61508_certified', False)))})",
        "  )",
        "  (layers",
    ]
    for cl in copper_layers:
        lnum = _kicad_layer_number(cl.name, copper_layers)
        ltype = cl.layer_type if cl.layer_type in ("signal", "power", "mixed") else "signal"
        lines.append(f"    ({lnum} {_q(cl.name)} {ltype})")
    lines.extend([
        '    (36 "B.SilkS" user "B.Silkscreen")',
        '    (37 "F.SilkS" user "F.Silkscreen")',
        '    (38 "B.Mask" user)',
        '    (39 "F.Mask" user)',
        '    (44 "Edge.Cuts" user)',
        '    (46 "B.CrtYd" user "B.Courtyard")',
        '    (47 "F.CrtYd" user "F.Courtyard")',
        '    (48 "B.Fab" user)',
        '    (49 "F.Fab" user)',
        "  )",
        "  (setup",
        "    (stackup",
        '      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.015) (epsilon_r 3.5))',
    ])
    for sl in board_spec.stackup:
        if sl.is_copper:
            lines.append(
                f'      (layer {_q(sl.name)} (type "copper") (thickness {sl.thickness_mm:.4f}))'
            )
        else:
            mat = sl.material or "FR4"
            lines.append(
                f"      (layer {_q(sl.name)} (type {_q(sl.layer_type)}) "
                f"(thickness {sl.thickness_mm:.4f}) (material {_q(mat)}) "
                f"(epsilon_r {sl.epsilon_r:.4f}) (loss_tangent {sl.loss_tangent:.5f}))"
            )
    lines.extend([
        '      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.015) (epsilon_r 3.5))',
        '      (copper_finish "ENIG")',
        "    )",
        "    (pad_to_mask_clearance 0.05)",
        "  )",
        '  (net 0 "")',
    ])
    for ns in board_spec.nets:
        lines.append(f"  (net {net_ids[ns.name]} {_q(ns.name)})")

    # Board outline on Edge.Cuts
    lines.append(
        f"  (gr_rect (start 0 0) (end {board_spec.width_mm:.4f} {board_spec.height_mm:.4f}) "
        f'(stroke (width 0.15) (type solid)) (fill none) (layer "Edge.Cuts") '
        f"(uuid {_q(_det_uuid(f'pcb.outline.{board_spec.name}'))}))"
    )

    # Milled HV air-slots as interior Edge.Cuts cutouts
    for ko in board_spec.keepouts:
        if ko.kind == "air_slot":
            lines.append(
                f"  (gr_rect (start {ko.x_mm:.4f} {ko.y_mm:.4f}) "
                f"(end {ko.x_mm + ko.width_mm:.4f} {ko.y_mm + ko.height_mm:.4f}) "
                f'(stroke (width 0.15) (type solid)) (fill none) (layer "Edge.Cuts") '
                f"(uuid {_q(_det_uuid(f'pcb.slot.{board_spec.name}.{ko.name}'))}))"
            )

    # Silkscreen title & epistemic banner
    lines.append(
        f"  (gr_text {_q(board_spec.title + ' REV ' + board_spec.rev + ' [DESIGN_ONLY]')} "
        f"(at {board_spec.width_mm * 0.5:.4f} 2.2 0) "
        f'(layer "F.SilkS") (uuid {_q(_det_uuid(f"pcb.silk.{board_spec.name}"))}) '
        f"(effects (font (size 1.2 1.2) (thickness 0.15))))"
    )

    # Footprints & Pads
    for comp in board_spec.components:
        pins = comp.pins or auto_footprint_pads(comp.footprint, ("1", "2"))
        fuuid = _det_uuid(f"pcb.fp.{board_spec.name}.{comp.ref}")
        bom_id = comp.bom_id or (board_spec.bom_ids[0] if board_spec.bom_ids else "")
        xs = [p.dx_mm - p.pad_w_mm * 0.5 for p in pins] + [p.dx_mm + p.pad_w_mm * 0.5 for p in pins]
        ys = [p.dy_mm - p.pad_h_mm * 0.5 for p in pins] + [p.dy_mm + p.pad_h_mm * 0.5 for p in pins]
        bw = comp.body_w_mm if comp.body_w_mm > 0 else max(1.0, max(xs) - min(xs) + 0.4)
        bh = comp.body_h_mm if comp.body_h_mm > 0 else max(1.0, max(ys) - min(ys) + 0.4)
        silk_layer = "F.SilkS" if comp.layer == "F.Cu" else "B.SilkS"
        fab_layer = "F.Fab" if comp.layer == "F.Cu" else "B.Fab"
        crtyd_layer = "F.CrtYd" if comp.layer == "F.Cu" else "B.CrtYd"

        lines.extend([
            f"  (footprint {_q(comp.footprint)}",
            f"    (layer {_q(comp.layer)})",
            f"    (uuid {_q(fuuid)})",
            f"    (at {comp.x_mm:.4f} {comp.y_mm:.4f} {comp.rotation_deg:.2f})",
            f'    (property "Reference" {_q(comp.ref)} (at 0 {-bh * 0.5 - 0.9:.4f} 0) (layer {_q(silk_layer)}) '
            f"(uuid {_q(_det_uuid(f'pcb.ref.{board_spec.name}.{comp.ref}'))}) (effects (font (size 0.8 0.8) (thickness 0.12))))",
            f'    (property "Value" {_q(comp.value)} (at 0 {bh * 0.5 + 0.9:.4f} 0) (layer {_q(fab_layer)}) '
            f"(uuid {_q(_det_uuid(f'pcb.val.{board_spec.name}.{comp.ref}'))}) (effects (font (size 0.8 0.8) (thickness 0.12))))",
            f'    (property "BOM_ID" {_q(bom_id)} (at 0 0 0) (layer {_q(fab_layer)}) (hide yes) '
            f"(uuid {_q(_det_uuid(f'pcb.bom.{board_spec.name}.{comp.ref}'))}) (effects (font (size 0.8 0.8) (thickness 0.12))))",
            f'    (property "EdgeMount" {_q("yes" if comp.edge_mount else "no")} (at 0 0 0) (layer {_q(fab_layer)}) (hide yes) '
            f"(uuid {_q(_det_uuid(f'pcb.em.{board_spec.name}.{comp.ref}'))}) (effects (font (size 0.8 0.8) (thickness 0.12))))",
            f"    (fp_rect (start {-bw * 0.5:.4f} {-bh * 0.5:.4f}) (end {bw * 0.5:.4f} {bh * 0.5:.4f}) "
            f"(stroke (width 0.12) (type solid)) (fill none) (layer {_q(silk_layer)}) "
            f"(uuid {_q(_det_uuid(f'pcb.silkbox.{board_spec.name}.{comp.ref}'))}))",
            f"    (fp_rect (start {-bw * 0.5 - 0.2:.4f} {-bh * 0.5 - 0.2:.4f}) (end {bw * 0.5 + 0.2:.4f} {bh * 0.5 + 0.2:.4f}) "
            f"(stroke (width 0.05) (type solid)) (fill none) (layer {_q(crtyd_layer)}) "
            f"(uuid {_q(_det_uuid(f'pcb.crtyd.{board_spec.name}.{comp.ref}'))}))",
        ])
        for ps in pins:
            nname = pin_to_net.get((comp.ref, ps.number), "")
            nid = net_ids.get(nname, 0)
            puuid = _det_uuid(f"pcb.pad.{board_spec.name}.{comp.ref}.{ps.number}")
            if ps.drill_mm > 0.0:
                lines.append(
                    f"    (pad {_q(ps.number)} thru_hole circle (at {ps.dx_mm:.4f} {ps.dy_mm:.4f}) "
                    f"(size {ps.pad_w_mm:.4f} {ps.pad_h_mm:.4f}) (drill {ps.drill_mm:.4f}) "
                    f'(layers "*.Cu" "*.Mask") (net {nid} {_q(nname)}) (uuid {_q(puuid)}))'
                )
            else:
                paste_l = "F.Paste" if comp.layer == "F.Cu" else "B.Paste"
                mask_l = "F.Mask" if comp.layer == "F.Cu" else "B.Mask"
                lines.append(
                    f"    (pad {_q(ps.number)} smd roundrect (at {ps.dx_mm:.4f} {ps.dy_mm:.4f}) "
                    f"(size {ps.pad_w_mm:.4f} {ps.pad_h_mm:.4f}) "
                    f"(layers {_q(comp.layer)} {_q(paste_l)} {_q(mask_l)}) (roundrect_rratio 0.25) "
                    f"(net {nid} {_q(nname)}) (uuid {_q(puuid)}))"
                )
        lines.append("  )")

    # Copper tracks (segments), including guard-ring copper tracks
    seg_idx = 0
    for tr in board_spec.traces:
        nid = net_ids.get(tr.net, 0)
        for i in range(len(tr.points_mm) - 1):
            x0, y0 = tr.points_mm[i]
            x1, y1 = tr.points_mm[i + 1]
            if math.hypot(x1 - x0, y1 - y0) < 1e-6:
                continue
            seg_idx += 1
            suuid = _det_uuid(f"pcb.seg.{board_spec.name}.{seg_idx}.{tr.net}")
            lines.append(
                f"  (segment (start {x0:.4f} {y0:.4f}) (end {x1:.4f} {y1:.4f}) "
                f"(width {tr.width_mm:.4f}) (layer {_q(tr.layer)}) (net {nid}) (uuid {_q(suuid)}))"
            )

    # Vias
    for vidx, via in enumerate(board_spec.vias, start=1):
        nid = net_ids.get(via.net, 0)
        vuuid = _det_uuid(f"pcb.via.{board_spec.name}.{vidx}.{via.net}")
        lines.append(
            f"  (via (at {via.x_mm:.4f} {via.y_mm:.4f}) (size {via.diameter_mm:.4f}) "
            f"(drill {via.drill_mm:.4f}) (layers {_q(via.layers[0])} {_q(via.layers[1])}) "
            f"(net {nid}) (uuid {_q(vuuid)}))"
        )

    # Ground / Power Copper Zones
    for zidx, z in enumerate(board_spec.zones, start=1):
        nid = net_ids.get(z.net, 0)
        zuuid = _det_uuid(f"pcb.zone.{board_spec.name}.{zidx}.{z.net}.{z.layer}")
        pts_str = " ".join(f"(xy {x:.4f} {y:.4f})" for x, y in z.polygon_mm)
        lines.extend([
            f"  (zone (net {nid}) (net_name {_q(z.net)}) (layer {_q(z.layer)}) (uuid {_q(zuuid)})",
            f"    (connect_pads (clearance {z.clearance_mm:.4f}))",
            f"    (min_thickness {z.min_thickness_mm:.4f})",
            f"    (polygon (pts {pts_str}))",
            "  )",
        ])

    # Copper Keepout Rule Areas (e.g., ground-plane cutout under CSA_SUM for <0.15 pF stray C)
    for kidx, ko in enumerate(board_spec.keepouts, start=1):
        if ko.kind == "copper_keepout":
            kuuid = _det_uuid(f"pcb.ko.{board_spec.name}.{kidx}.{ko.name}")
            layers_str = " ".join(_q(l) for l in ko.layers)
            x0, y0, x1, y1 = ko.x_mm, ko.y_mm, ko.x_mm + ko.width_mm, ko.y_mm + ko.height_mm
            pts_str = f"(xy {x0:.4f} {y0:.4f}) (xy {x1:.4f} {y0:.4f}) (xy {x1:.4f} {y1:.4f}) (xy {x0:.4f} {y1:.4f})"
            lines.extend([
                f'  (zone (net 0) (net_name "") (layers {layers_str}) (uuid {_q(kuuid)})',
                "    (keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))",
                f"    (polygon (pts {pts_str}))",
                "  )",
            ])

    lines.append(")")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# 6. Strict Electrical Rules Check (run_erc) — Reconstructs Netlist From Disk
# ---------------------------------------------------------------------------

@dataclass
class ErcResult:
    passed: bool
    errors: list[str]
    warnings: list[str]
    component_count: int
    net_count: int
    sch_pcb_parity_ok: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _qpt(x: float, y: float) -> tuple[int, int]:
    """Quantize schematic coordinates to 0.01 mm integer ticks for exact wire connectivity."""
    return (int(round(x * 100.0)), int(round(y * 100.0)))


def _parse_pcb_netlist(pcb_path: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Extract {ref: {pin_num: net_name}} directly from a .kicad_pcb file on disk."""
    errs: list[str] = []
    tree = parse_sexpr(pcb_path.read_text(encoding="utf-8"))
    if not tree or tree[0] != "kicad_pcb":
        return {}, [f"Invalid PCB root tag in {pcb_path.name}: {tree[0] if tree else None!r}"]
    fp_map: dict[str, dict[str, str]] = {}
    for fp in _find_children(tree, "footprint"):
        ref = ""
        for prop in _find_children(fp, "property"):
            if len(prop) >= 3 and prop[1] == "Reference":
                ref = str(prop[2])
        if not ref:
            errs.append("PCB footprint missing Reference property")
            continue
        if ref in fp_map:
            errs.append(f"Duplicate footprint Reference in PCB: {ref}")
        pins: dict[str, str] = {}
        for pad in _find_children(fp, "pad"):
            pnum = str(pad[1])
            net_node = _find_first(pad, "net")
            nname = str(net_node[2]) if net_node and len(net_node) >= 3 else ""
            pins[pnum] = nname
        fp_map[ref] = pins
    return fp_map, errs


def run_erc(
    sch_path: str | Path,
    board_spec: BoardSpec,
    pcb_path: str | Path | None = None,
) -> ErcResult:
    """Strictly validate a KiCad 8 .kicad_sch file (and optional .kicad_pcb parity).

    Reconstructs electrical connectivity from the actual parsed schematic
    ``(lib_symbols ...)``, placed ``(symbol ...)`` pin coordinates, ``(wire ...)``
    segments, and ``(label ...)`` / ``(global_label ...)`` elements on disk.
    """
    sp = Path(sch_path)
    errors: list[str] = []
    warnings: list[str] = []

    try:
        tree = parse_sexpr(sp.read_text(encoding="utf-8"))
    except (OSError, SexprParseError) as exc:
        return ErcResult(False, [f"Schematic parse failed: {exc}"], [], 0, 0, False)

    if not tree or tree[0] != "kicad_sch":
        return ErcResult(False, [f"Root tag is {tree[0] if tree else None!r}, expected 'kicad_sch'"], [], 0, 0, False)
    ver_node = _find_first(tree, "version")
    if not ver_node or len(ver_node) < 2 or str(ver_node[1]) != KICAD_SCH_VERSION:
        errors.append(f"Expected KiCad 8 schematic version {KICAD_SCH_VERSION}, got {ver_node}")

    # 1. Parse lib_symbols pin definitions
    lib_pins: dict[str, dict[str, tuple[float, float, str]]] = {}
    lib_sym_sec = _find_first(tree, "lib_symbols")
    if not lib_sym_sec:
        errors.append("Schematic missing (lib_symbols ...) section")
    else:
        for sym in _find_children(lib_sym_sec, "symbol"):
            lid = str(sym[1])
            pmap: dict[str, tuple[float, float, str]] = {}
            for sub in _find_children(sym, "symbol"):
                for pnode in _find_children(sub, "pin"):
                    etype = str(pnode[1])
                    at_node = _find_first(pnode, "at")
                    num_node = _find_first(pnode, "number")
                    if at_node and num_node and len(at_node) >= 3 and len(num_node) >= 2:
                        pmap[str(num_node[1])] = (float(at_node[1]), float(at_node[2]), etype)
            lib_pins[lid] = pmap

    # 2. Union-Find over wire segments
    parent: dict[tuple[int, int], tuple[int, int]] = {}

    def find(pt: tuple[int, int]) -> tuple[int, int]:
        parent.setdefault(pt, pt)
        while parent[pt] != pt:
            parent[pt] = parent[parent[pt]]
            pt = parent[pt]
        return pt

    def union(a: tuple[int, int], b: tuple[int, int]) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for wnode in _find_children(tree, "wire"):
        pts_node = _find_first(wnode, "pts")
        if not pts_node:
            continue
        xys = _find_children(pts_node, "xy")
        for i in range(len(xys) - 1):
            p0 = _qpt(float(xys[i][1]), float(xys[i][2]))
            p1 = _qpt(float(xys[i + 1][1]), float(xys[i + 1][2]))
            union(p0, p1)

    # 3. Map labels & global_labels to wire components
    comp_labels: dict[tuple[int, int], set[str]] = defaultdict(set)
    for tag in ("label", "global_label"):
        for lnode in _find_children(tree, tag):
            lname = str(lnode[1])
            at_node = _find_first(lnode, "at")
            if not at_node or len(at_node) < 3:
                errors.append(f"Malformed {tag} {lname!r}: missing (at x y)")
                continue
            pt = _qpt(float(at_node[1]), float(at_node[2]))
            comp_labels[find(pt)].add(lname)

    for root_pt, names in comp_labels.items():
        if len(names) > 1:
            errors.append(f"Shorted conflicting net labels on same wire node {root_pt}: {sorted(names)}")

    nc_pts: set[tuple[int, int]] = set()
    for nc in _find_children(tree, "no_connect"):
        at_node = _find_first(nc, "at")
        if at_node and len(at_node) >= 3:
            nc_pts.add(_qpt(float(at_node[1]), float(at_node[2])))

    # 4. Walk placed symbols, reconstruct schematic netlist, validate properties & pins
    seen_refs: set[str] = set()
    sch_nets: dict[str, set[tuple[str, str]]] = defaultdict(set)
    pin_etypes: dict[tuple[str, str], str] = {}
    pwr_flag_nets: set[str] = set()
    phys_comp_count = 0

    for sym in _find_children(tree, "symbol"):
        lid_node = _find_first(sym, "lib_id")
        at_node = _find_first(sym, "at")
        if not lid_node or not at_node:
            errors.append("Placed symbol missing lib_id or at")
            continue
        lid = str(lid_node[1])
        sx, sy = float(at_node[1]), float(at_node[2])
        srot = float(at_node[3]) if len(at_node) >= 4 else 0.0
        props: dict[str, str] = {}
        for pr in _find_children(sym, "property"):
            if len(pr) >= 3:
                props[str(pr[1])] = str(pr[2])
        ref = props.get("Reference", "")
        val = props.get("Value", "")
        fp = props.get("Footprint", "")
        if not ref:
            errors.append(f"Placed symbol {lid} at ({sx},{sy}) missing Reference")
            continue
        if ref in seen_refs:
            errors.append(f"Duplicate Reference designator in schematic: {ref}")
        seen_refs.add(ref)

        is_pwr_flag = ref.startswith("#FLG") or lid == "power:PWR_FLAG"
        if not is_pwr_flag:
            phys_comp_count += 1
            if val.strip().upper() in BANNED_PLACEHOLDER_VALUES:
                errors.append(f"Missing or placeholder Value on {ref}: {val!r}")
            if not fp.strip():
                errors.append(f"Missing Footprint on component {ref} ({val})")
            if not props.get("BOM_ID", "").strip():
                warnings.append(f"Component {ref} missing BOM_ID property")

        if lid not in lib_pins:
            errors.append(f"Component {ref} references undefined lib_symbol {lid!r}")
            continue

        rad = math.radians(srot)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        for pnum, (lx, ly, etype) in lib_pins[lid].items():
            rx = lx * cos_r - ly * sin_r
            ry = lx * sin_r + ly * cos_r
            px, py = sx + rx, sy - ry
            q = _qpt(px, py)
            lbls = comp_labels.get(find(q), set())
            if is_pwr_flag:
                if not lbls:
                    errors.append(f"PWR_FLAG {ref} is not wired to any net label")
                else:
                    pwr_flag_nets.update(lbls)
                continue
            if not lbls:
                if etype == "no_connect" or q in nc_pts:
                    continue
                errors.append(f"Floating/unconnected pin in schematic: {ref}.{pnum} ({val}, type={etype})")
                continue
            nname = next(iter(lbls))
            sch_nets[nname].add((ref, pnum))
            pin_etypes[(ref, pnum)] = etype

    # 5. Electrical checks: dangling single-pin nets, pin conflicts, power rail driving
    pin_owner: dict[tuple[str, str], str] = {}
    for nname, nodes in sch_nets.items():
        if len(nodes) < 2:
            errors.append(f"Single-pin (dangling) net in schematic: {nname} -> {sorted(nodes)}")
        for rp in nodes:
            if rp in pin_owner and pin_owner[rp] != nname:
                errors.append(f"Pin conflict: {rp[0]}.{rp[1]} on both {pin_owner[rp]} and {nname}")
            pin_owner[rp] = nname

    # Power rail driving check (supports direct power_out, connector feed J*/P*, PWR_FLAG, or 0R star tie)
    spec_net_map = {ns.name: ns for ns in board_spec.nets}
    comp_map = {c.ref: c for c in board_spec.components}
    driven_power_nets: set[str] = set()
    for ns in board_spec.nets:
        if not ns.is_power:
            continue
        nodes = sch_nets.get(ns.name, set())
        if ns.name in pwr_flag_nets:
            driven_power_nets.add(ns.name)
            continue
        for ref, pnum in nodes:
            if pin_etypes.get((ref, pnum)) == "power_out":
                driven_power_nets.add(ns.name)
                break
            if ref.upper().startswith(("J", "P", "TP", "CON")):
                driven_power_nets.add(ns.name)
                break
    # Propagate power driving across 0R / star-ground / ferrite / passive ties
    changed = True
    while changed:
        changed = False
        for ns in board_spec.nets:
            if not ns.is_power or ns.name in driven_power_nets:
                continue
            for ref, _ in sch_nets.get(ns.name, set()):
                c = comp_map.get(ref)
                if c and (ref.upper().startswith(("R", "L", "FB")) and any(
                    other in driven_power_nets
                    for other, onodes in sch_nets.items()
                    if other != ns.name and any(r == ref for r, _ in onodes)
                )):
                    driven_power_nets.add(ns.name)
                    changed = True
                    break

    for ns in board_spec.nets:
        if ns.is_power and ns.name not in driven_power_nets:
            errors.append(
                f"Undriven power rail {ns.name!r}: no power_out pin, connector feed, star-tie, or PWR_FLAG"
            )

    # 6. Parity between reconstructed schematic netlist and BoardSpec
    expected_nets = {ns.name: {(r, str(p)) for r, p in ns.nodes} for ns in board_spec.nets}
    for nname, enodes in expected_nets.items():
        actual = sch_nets.get(nname, set())
        if actual != enodes:
            errors.append(
                f"Schematic/Spec net mismatch on {nname!r}: missing={sorted(enodes - actual)}, extra={sorted(actual - enodes)}"
            )
    for nname in set(sch_nets.keys()) - set(expected_nets.keys()):
        errors.append(f"Unexpected extra net in schematic not in BoardSpec: {nname!r}")

    # 7. Schematic <-> PCB netlist parity
    sch_pcb_parity_ok = True
    if pcb_path is not None:
        pcb_fp_map, pcb_errs = _parse_pcb_netlist(Path(pcb_path))
        if pcb_errs:
            errors.extend(pcb_errs)
            sch_pcb_parity_ok = False
        spec_refs = {c.ref for c in board_spec.components}
        pcb_refs = set(pcb_fp_map.keys())
        if spec_refs != pcb_refs:
            errors.append(
                f"SCH/PCB component mismatch: missing_in_pcb={sorted(spec_refs - pcb_refs)}, extra_in_pcb={sorted(pcb_refs - spec_refs)}"
            )
            sch_pcb_parity_ok = False
        # Reconstruct PCB nets
        pcb_nets: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for ref, pdict in pcb_fp_map.items():
            for pnum, nname in pdict.items():
                if nname:
                    pcb_nets[nname].add((ref, pnum))
        if set(pcb_nets.keys()) != set(sch_nets.keys()):
            errors.append(
                f"SCH/PCB net set mismatch: only_sch={sorted(set(sch_nets) - set(pcb_nets))}, "
                f"only_pcb={sorted(set(pcb_nets) - set(sch_nets))}"
            )
            sch_pcb_parity_ok = False
        for nname in sorted(set(sch_nets) & set(pcb_nets)):
            if sch_nets[nname] != pcb_nets[nname]:
                errors.append(
                    f"SCH/PCB pad-net parity mismatch on {nname!r}: "
                    f"only_sch={sorted(sch_nets[nname] - pcb_nets[nname])}, "
                    f"only_pcb={sorted(pcb_nets[nname] - sch_nets[nname])}"
                )
                sch_pcb_parity_ok = False

    return ErcResult(
        passed=(len(errors) == 0),
        errors=errors,
        warnings=warnings,
        component_count=phys_comp_count,
        net_count=len(sch_nets),
        sch_pcb_parity_ok=sch_pcb_parity_ok,
        details={
            "power_rails_driven": sorted(driven_power_nets),
            "pwr_flags_found": sorted(pwr_flag_nets),
            "lib_symbol_count": len(lib_pins),
        },
    )


# ---------------------------------------------------------------------------
# 7. Strict Geometric PCB DRC + Controlled-Impedance + HV Creepage/Clearance
# ---------------------------------------------------------------------------

@dataclass
class DrcResult:
    passed: bool
    errors: list[str]
    warnings: list[str]
    pad_count: int
    segment_count: int
    via_count: int
    zone_count: int
    air_slot_count: int
    min_measured_clearance_mm: float | None
    impedance_checks: list[dict[str, Any]]
    hv_checks: list[dict[str, Any]]
    stackup_summary: dict[str, Any] = field(default_factory=dict)
    routed_net_count: int = 0
    unrouted_net_count: int = 0
    unconnected_items: int = 0
    track_dangling_count: int = 0
    total_multi_pin_nets: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _point_in_polygon(x: float, y: float, poly: Sequence[tuple[float, float]], eps: float = 1e-6) -> bool:
    """Ray-casting + boundary point-in-polygon test for arbitrary copper pour zones."""
    n = len(poly)
    if n < 3:
        return False
    inside = False
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if _dist_point_to_seg(x, y, x1, y1, x2, y2) <= eps:
            return True
        if (y1 > y) != (y2 > y):
            x_int = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_int:
                inside = not inside
    return inside


def _point_in_zone_copper(
    x: float,
    y: float,
    poly: Sequence[tuple[float, float]],
    layer: str,
    keepout_zones: Sequence[tuple[tuple[str, ...], _Box, bool, bool, bool]],
    air_slots: Sequence[_Box],
    tol: float = 0.015,
) -> bool:
    """Return True if (x, y) lies inside filled copper of zone on ``layer`` (outside keepouts & air-slots)."""
    if not _point_in_polygon(x, y, poly, eps=tol):
        return False
    for slot in air_slots:
        if slot.dist_to_point(x, y) <= 1e-6:
            return False
    for klayers, kbox, _, _, no_pour in keepout_zones:
        if no_pour and layer in klayers and kbox.dist_to_point(x, y) <= 1e-6:
            return False
    return True


@dataclass(frozen=True)
class _Box:
    x0: float
    y0: float
    x1: float
    y1: float

    def dist_to_box(self, other: _Box) -> float:
        dx = max(0.0, max(self.x0 - other.x1, other.x0 - self.x1))
        dy = max(0.0, max(self.y0 - other.y1, other.y0 - self.y1))
        return math.hypot(dx, dy)

    def dist_to_point(self, x: float, y: float) -> float:
        dx = max(0.0, max(self.x0 - x, x - self.x1))
        dy = max(0.0, max(self.y0 - y, y - self.y1))
        return math.hypot(dx, dy)

    @property
    def center(self) -> tuple[float, float]:
        return (0.5 * (self.x0 + self.x1), 0.5 * (self.y0 + self.y1))

    def closest_points_to(self, other: _Box) -> tuple[tuple[float, float], tuple[float, float]]:
        if self.x1 < other.x0:
            ax, bx = self.x1, other.x0
        elif other.x1 < self.x0:
            ax, bx = self.x0, other.x1
        else:
            ax = bx = 0.5 * (max(self.x0, other.x0) + min(self.x1, other.x1))
        if self.y1 < other.y0:
            ay, by = self.y1, other.y0
        elif other.y1 < self.y0:
            ay, by = self.y0, other.y1
        else:
            ay = by = 0.5 * (max(self.y0, other.y0) + min(self.y1, other.y1))
        return ((ax, ay), (bx, by))


def _dist_point_to_seg(px: float, py: float, x0: float, y0: float, x1: float, y1: float) -> float:
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy
    if l2 <= 1e-12:
        return math.hypot(px - x0, py - y0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / l2))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def _ccw(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def _segments_intersect(
    ax: float, ay: float, bx: float, by: float, cx: float, cy: float, dx: float, dy: float
) -> bool:
    if max(ax, bx) < min(cx, dx) - 1e-9 or max(cx, dx) < min(ax, bx) - 1e-9:
        return False
    if max(ay, by) < min(cy, dy) - 1e-9 or max(cy, dy) < min(ay, by) - 1e-9:
        return False
    o1 = _ccw(ax, ay, bx, by, cx, cy)
    o2 = _ccw(ax, ay, bx, by, dx, dy)
    o3 = _ccw(cx, cy, dx, dy, ax, ay)
    o4 = _ccw(cx, cy, dx, dy, bx, by)
    return (o1 * o2 <= 1e-12) and (o3 * o4 <= 1e-12)


def _dist_seg_to_seg(
    ax: float, ay: float, bx: float, by: float, cx: float, cy: float, dx: float, dy: float
) -> float:
    if _segments_intersect(ax, ay, bx, by, cx, cy, dx, dy):
        return 0.0
    return min(
        _dist_point_to_seg(ax, ay, cx, cy, dx, dy),
        _dist_point_to_seg(bx, by, cx, cy, dx, dy),
        _dist_point_to_seg(cx, cy, ax, ay, bx, by),
        _dist_point_to_seg(dx, dy, ax, ay, bx, by),
    )


def _dist_seg_to_box(x0: float, y0: float, x1: float, y1: float, box: _Box) -> float:
    # Check if either endpoint inside box
    if box.dist_to_point(x0, y0) == 0.0 or box.dist_to_point(x1, y1) == 0.0:
        return 0.0
    # Check intersection with box's 4 edges
    edges = (
        (box.x0, box.y0, box.x1, box.y0),
        (box.x1, box.y0, box.x1, box.y1),
        (box.x1, box.y1, box.x0, box.y1),
        (box.x0, box.y1, box.x0, box.y0),
    )
    return min(_dist_seg_to_seg(x0, y0, x1, y1, ex0, ey0, ex1, ey1) for ex0, ey0, ex1, ey1 in edges)


def _creepage_around_slots(
    p1: tuple[float, float],
    p2: tuple[float, float],
    direct_edge_dist: float,
    air_slots: list[_Box],
) -> float:
    """Compute PCB surface creepage accounting for milled Edge.Cuts air-slots.

    If a milled air-slot intercepts the line between p1 and p2, surface tracking
    must route around the slot corners (shortest of the 4 corner detours), per
    IEC 61010-1 / IPC-2221B slot-interrupted creepage geometry.
    """
    best_creepage = direct_edge_dist
    x1, y1 = p1
    x2, y2 = p2
    c_dist = math.hypot(x2 - x1, y2 - y1)
    edge_shrink = max(0.0, c_dist - direct_edge_dist)
    for slot in air_slots:
        if _dist_seg_to_box(x1, y1, x2, y2, slot) <= 1e-6:
            # Compute shortest detour around the slot boundary (either top/bottom or left/right)
            c_top = math.hypot(x1 - slot.x0, y1 - slot.y0) + (slot.x1 - slot.x0) + math.hypot(x2 - slot.x1, y2 - slot.y0)
            c_top_r = math.hypot(x1 - slot.x1, y1 - slot.y0) + (slot.x1 - slot.x0) + math.hypot(x2 - slot.x0, y2 - slot.y0)
            c_bot = math.hypot(x1 - slot.x0, y1 - slot.y1) + (slot.x1 - slot.x0) + math.hypot(x2 - slot.x1, y2 - slot.y1)
            c_bot_r = math.hypot(x1 - slot.x1, y1 - slot.y1) + (slot.x1 - slot.x0) + math.hypot(x2 - slot.x0, y2 - slot.y1)
            c_left = math.hypot(x1 - slot.x0, y1 - slot.y0) + (slot.y1 - slot.y0) + math.hypot(x2 - slot.x0, y2 - slot.y1)
            c_left_r = math.hypot(x1 - slot.x0, y1 - slot.y1) + (slot.y1 - slot.y0) + math.hypot(x2 - slot.x0, y2 - slot.y0)
            c_right = math.hypot(x1 - slot.x1, y1 - slot.y0) + (slot.y1 - slot.y0) + math.hypot(x2 - slot.x1, y2 - slot.y1)
            c_right_r = math.hypot(x1 - slot.x1, y1 - slot.y1) + (slot.y1 - slot.y0) + math.hypot(x2 - slot.x1, y2 - slot.y0)
            detour_center = min(c_top, c_top_r, c_bot, c_bot_r, c_left, c_left_r, c_right, c_right_r)
            detour_edge = max(direct_edge_dist, detour_center - edge_shrink)
            best_creepage = max(best_creepage, detour_edge)
    return best_creepage


def run_drc(pcb_path: str | Path, board_spec: BoardSpec) -> DrcResult:
    """Run strict geometric PCB DRC, controlled-impedance Z0, and HV creepage/clearance checks."""
    pp = Path(pcb_path)
    errors: list[str] = []
    warnings: list[str] = []
    rules = board_spec.rules

    try:
        tree = parse_sexpr(pp.read_text(encoding="utf-8"))
    except (OSError, SexprParseError) as exc:
        return DrcResult(False, [f"PCB parse failed: {exc}"], [], 0, 0, 0, 0, 0, None, [], [])

    if not tree or tree[0] != "kicad_pcb":
        return DrcResult(False, [f"Invalid PCB root tag: {tree[0] if tree else None!r}"], [], 0, 0, 0, 0, 0, None, [], [])
    ver_node = _find_first(tree, "version")
    if not ver_node or len(ver_node) < 2 or str(ver_node[1]) != KICAD_PCB_VERSION:
        errors.append(f"Expected KiCad 8 PCB version {KICAD_PCB_VERSION}, got {ver_node}")

    # 1. Parse stackup & copper layers
    stackup_entries: list[dict[str, Any]] = []
    setup_node = _find_first(tree, "setup")
    stackup_node = _find_first(setup_node, "stackup") if setup_node else None
    if not stackup_node:
        errors.append("PCB missing (setup (stackup ...)) definition")
    else:
        for lnode in _find_children(stackup_node, "layer"):
            lname = str(lnode[1])
            ltype = str(_find_first(lnode, "type")[1]) if _find_first(lnode, "type") else ""
            thick = float(_find_first(lnode, "thickness")[1]) if _find_first(lnode, "thickness") else 0.0
            er_n = _find_first(lnode, "epsilon_r")
            er = float(er_n[1]) if er_n else 1.0
            if thick <= 0.0:
                errors.append(f"Non-positive stackup thickness on layer {lname!r}: {thick}")
            if ltype in ("core", "prepreg") and er < 1.0:
                errors.append(f"Invalid dielectric epsilon_r on {lname!r}: {er}")
            stackup_entries.append({"name": lname, "type": ltype, "thickness_mm": thick, "epsilon_r": er})

    copper_order = [e for e in stackup_entries if e["type"] == "copper" or e["name"].endswith(".Cu")]
    all_cu_names = [e["name"] for e in copper_order]
    if len(all_cu_names) < 2:
        errors.append(f"PCB must define >=2 copper layers in stackup, found {all_cu_names}")

    # 2. Parse Edge.Cuts outer outline & milled air-slots
    edge_rects: list[_Box] = []
    for gr in _find_children(tree, "gr_rect"):
        lnode = _find_first(gr, "layer")
        if lnode and str(lnode[1]) == "Edge.Cuts":
            st = _find_first(gr, "start")
            en = _find_first(gr, "end")
            if st and en:
                x0, y0 = float(st[1]), float(st[2])
                x1, y1 = float(en[1]), float(en[2])
                edge_rects.append(_Box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
    if not edge_rects:
        return DrcResult(False, ["PCB missing Edge.Cuts board outline"], [], 0, 0, 0, 0, 0, None, [], [])
    # Largest Edge.Cuts rectangle is board outline; smaller interior ones are milled HV air-slots
    edge_rects.sort(key=lambda b: (b.x1 - b.x0) * (b.y1 - b.y0), reverse=True)
    outline = edge_rects[0]
    air_slots = edge_rects[1:]

    # 3. Parse net table
    net_id_to_name: dict[int, str] = {}
    for nnode in _find_children(tree, "net"):
        if len(nnode) >= 3:
            net_id_to_name[int(nnode[1])] = str(nnode[2])

    # 4. Parse footprints & pads into absolute board geometry
    # Record: (box, net_name, layers_tuple, label, edge_mount)
    pads: list[tuple[_Box, str, tuple[str, ...], str, bool]] = []
    for fp in _find_children(tree, "footprint"):
        at_n = _find_first(fp, "at")
        fx, fy = float(at_n[1]), float(at_n[2])
        frot = float(at_n[3]) if len(at_n) >= 4 else 0.0
        ref = "?"
        edge_mount = False
        for pr in _find_children(fp, "property"):
            if len(pr) >= 3:
                if pr[1] == "Reference":
                    ref = str(pr[2])
                elif pr[1] == "EdgeMount" and str(pr[2]).lower() == "yes":
                    edge_mount = True
        rad = math.radians(frot)
        c, s = math.cos(rad), math.sin(rad)
        for pnode in _find_children(fp, "pad"):
            pnum = str(pnode[1])
            pat = _find_first(pnode, "at")
            psize = _find_first(pnode, "size")
            players = _find_first(pnode, "layers")
            pnet = _find_first(pnode, "net")
            dx, dy = float(pat[1]), float(pat[2])
            pw, ph = float(psize[1]), float(psize[2])
            px = fx + dx * c + dy * s
            py = fy - dx * s + dy * c
            bw = abs(pw * c) + abs(ph * s)
            bh = abs(pw * s) + abs(ph * c)
            box = _Box(px - 0.5 * bw, py - 0.5 * bh, px + 0.5 * bw, py + 0.5 * bh)
            nname = str(pnet[2]) if pnet and len(pnet) >= 3 else ""
            raw_layers = [str(x) for x in (players[1:] if players else [])]
            cu_set: list[str] = []
            for rl in raw_layers:
                if rl == "*.Cu":
                    cu_set = list(all_cu_names)
                    break
                if rl in all_cu_names:
                    cu_set.append(rl)
            pads.append((box, nname, tuple(cu_set), f"{ref}.{pnum}", edge_mount))

    # 5. Parse segments
    # Record: (x0, y0, x1, y1, width, layer, net_name)
    segments: list[tuple[float, float, float, float, float, str, str]] = []
    for snode in _find_children(tree, "segment"):
        st = _find_first(snode, "start")
        en = _find_first(snode, "end")
        wn = _find_first(snode, "width")
        ln = _find_first(snode, "layer")
        nn = _find_first(snode, "net")
        x0, y0 = float(st[1]), float(st[2])
        x1, y1 = float(en[1]), float(en[2])
        w = float(wn[1])
        layer = str(ln[1])
        nname = net_id_to_name.get(int(nn[1]), "") if nn else ""
        segments.append((x0, y0, x1, y1, w, layer, nname))

    # 6. Parse vias
    # Record: (x, y, size, drill, layers_tuple, net_name)
    vias: list[tuple[float, float, float, float, tuple[str, ...], str]] = []
    for vnode in _find_children(tree, "via"):
        at_n = _find_first(vnode, "at")
        sz_n = _find_first(vnode, "size")
        dr_n = _find_first(vnode, "drill")
        ly_n = _find_first(vnode, "layers")
        nn = _find_first(vnode, "net")
        vx, vy = float(at_n[1]), float(at_n[2])
        vsize, vdrill = float(sz_n[1]), float(dr_n[1])
        lpair = (str(ly_n[1]), str(ly_n[2])) if ly_n and len(ly_n) >= 3 else ("F.Cu", "B.Cu")
        # Vias span all copper layers between lpair[0] and lpair[1]
        if lpair[0] in all_cu_names and lpair[1] in all_cu_names:
            i0, i1 = all_cu_names.index(lpair[0]), all_cu_names.index(lpair[1])
            vlayers = tuple(all_cu_names[min(i0, i1): max(i0, i1) + 1])
        else:
            vlayers = tuple(all_cu_names)
        nname = net_id_to_name.get(int(nn[1]), "") if nn else ""
        vias.append((vx, vy, vsize, vdrill, vlayers, nname))

    # 7. Parse zones & copper keepout areas
    # copper_zones: (net_name, layer, bbox, polygon_tuple)
    copper_zones: list[tuple[str, str, _Box, tuple[tuple[float, float], ...]]] = []
    # keepout_zones: (layers, bbox, no_tracks, no_vias, no_pour)
    keepout_zones: list[tuple[tuple[str, ...], _Box, bool, bool, bool]] = []
    for znode in _find_children(tree, "zone"):
        poly = _find_first(znode, "polygon")
        pts = _find_first(poly, "pts") if poly else None
        if not pts:
            continue
        xys = [(float(p[1]), float(p[2])) for p in _find_children(pts, "xy")]
        if len(xys) < 3:
            continue
        zbox = _Box(min(p[0] for p in xys), min(p[1] for p in xys), max(p[0] for p in xys), max(p[1] for p in xys))
        ko = _find_first(znode, "keepout")
        if ko:
            ly_n = _find_first(znode, "layers")
            ly_single = _find_first(znode, "layer")
            klayers = tuple(str(x) for x in ly_n[1:]) if ly_n else ((str(ly_single[1]),) if ly_single else ())
            nt = (_find_first(ko, "tracks") or ["", "allowed"])[1] == "not_allowed"
            nv = (_find_first(ko, "vias") or ["", "allowed"])[1] == "not_allowed"
            np_flag = (_find_first(ko, "copperpour") or ["", "not_allowed"])[1] == "not_allowed"
            keepout_zones.append((klayers, zbox, nt, nv, np_flag))
        else:
            nn = _find_first(znode, "net_name")
            ly = _find_first(znode, "layer")
            copper_zones.append((str(nn[1]) if nn else "", str(ly[1]) if ly else "", zbox, tuple(xys)))

    # --- CHECK A: Board outline containment, edge clearance, air-slot interference ---
    edge_mount_pads: dict[str, list[tuple[_Box, tuple[str, ...]]]] = defaultdict(list)
    for box, nname, layers, label, edge_mount in pads:
        if edge_mount and nname:
            edge_mount_pads[nname].append((box, layers))
        margin = 0.0 if edge_mount else rules.min_edge_clearance_mm
        if (
            box.x0 < outline.x0 + margin - 1e-6
            or box.x1 > outline.x1 - margin + 1e-6
            or box.y0 < outline.y0 + margin - 1e-6
            or box.y1 > outline.y1 - margin + 1e-6
        ):
            errors.append(
                f"Pad {label} ({nname}) violates board outline/edge clearance "
                f"(margin>={margin:.2f} mm): box=({box.x0:.2f},{box.y0:.2f})-({box.x1:.2f},{box.y1:.2f})"
            )
        for slot in air_slots:
            if box.dist_to_box(slot) < rules.min_slot_clearance_mm - 1e-6:
                errors.append(f"Pad {label} ({nname}) violates milled air-slot clearance ({rules.min_slot_clearance_mm} mm)")

    def _pt_in_em_pad(px: float, py: float, nname: str, layer: str) -> bool:
        for pbox, players in edge_mount_pads.get(nname, ()):
            if layer in players and pbox.dist_to_point(px, py) <= 0.02:
                return True
        return False

    for x0, y0, x1, y1, w, layer, nname in segments:
        if w < rules.min_trace_width_mm - 1e-6:
            errors.append(f"Trace on net {nname!r} ({layer}) width {w:.4f} mm < min {rules.min_trace_width_mm:.4f} mm")
        hw = 0.5 * w
        m = rules.min_edge_clearance_mm
        # Allow edge-mount pad entry endpoints within [outline.x0, outline.x1] x [outline.y0, outline.y1]
        m0 = 0.0 if _pt_in_em_pad(x0, y0, nname, layer) else m
        m1 = 0.0 if _pt_in_em_pad(x1, y1, nname, layer) else m
        if (
            x0 - hw < outline.x0 + m0 - 1e-6
            or x0 + hw > outline.x1 - m0 + 1e-6
            or y0 - hw < outline.y0 + m0 - 1e-6
            or y0 + hw > outline.y1 - m0 + 1e-6
            or x1 - hw < outline.x0 + m1 - 1e-6
            or x1 + hw > outline.x1 - m1 + 1e-6
            or y1 - hw < outline.y0 + m1 - 1e-6
            or y1 + hw > outline.y1 - m1 + 1e-6
        ):
            errors.append(
                f"Trace on net {nname!r} ({layer}) ({x0:.2f},{y0:.2f})-({x1:.2f},{y1:.2f}) violates board edge clearance"
            )
        for slot in air_slots:
            if _dist_seg_to_box(x0, y0, x1, y1, slot) - hw < rules.min_slot_clearance_mm - 1e-6:
                errors.append(f"Trace on net {nname!r} ({layer}) intersects/violates milled air-slot")
        for klayers, kbox, no_tracks, _, _ in keepout_zones:
            if no_tracks and layer in klayers:
                if _dist_seg_to_box(x0, y0, x1, y1, kbox) - hw < -1e-6:
                    errors.append(f"Trace on net {nname!r} ({layer}) enters copper keepout region")

    for vx, vy, vsize, vdrill, vlayers, nname in vias:
        if vdrill < rules.min_via_drill_mm - 1e-6:
            errors.append(f"Via on net {nname!r} at ({vx:.2f},{vy:.2f}) drill {vdrill:.3f} < min {rules.min_via_drill_mm:.3f}")
        ann = 0.5 * (vsize - vdrill)
        if ann < rules.min_annular_ring_mm - 1e-6:
            errors.append(f"Via on net {nname!r} at ({vx:.2f},{vy:.2f}) annular ring {ann:.3f} < min {rules.min_annular_ring_mm:.3f}")
        vr = 0.5 * vsize
        m = rules.min_edge_clearance_mm
        if (
            vx - vr < outline.x0 + m - 1e-6
            or vx + vr > outline.x1 - m + 1e-6
            or vy - vr < outline.y0 + m - 1e-6
            or vy + vr > outline.y1 - m + 1e-6
        ):
            errors.append(f"Via on net {nname!r} at ({vx:.2f},{vy:.2f}) violates board edge clearance")
        for slot in air_slots:
            if slot.dist_to_point(vx, vy) - vr < rules.min_slot_clearance_mm - 1e-6:
                errors.append(f"Via on net {nname!r} at ({vx:.2f},{vy:.2f}) violates milled air-slot clearance")
        for klayers, kbox, _, no_vias, _ in keepout_zones:
            if no_vias and any(l in klayers for l in vlayers):
                if kbox.dist_to_point(vx, vy) - vr < -1e-6:
                    errors.append(f"Via on net {nname!r} at ({vx:.2f},{vy:.2f}) enters keepout region")

    # --- CHECK B: Pad-to-Pad, Track-to-Track, Track-to-Pad, Via clearances (spatial hash) ---
    cell_sz = max(5.0, rules.min_clearance_mm * 10.0)
    min_clr_measured: float | None = None

    def _record_clr(d: float, msg: str) -> None:
        nonlocal min_clr_measured
        if min_clr_measured is None or d < min_clr_measured:
            min_clr_measured = d
        if d < rules.min_clearance_mm - 1e-6:
            errors.append(f"Clearance violation ({d:.4f} mm < {rules.min_clearance_mm:.4f} mm): {msg}")

    for layer in all_cu_names:
        # Spatial hash for pads on this layer
        layer_pads = [(box, nname, label) for box, nname, layers, label, _ in pads if layer in layers]
        pad_grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        for idx, (box, _, _) in enumerate(layer_pads):
            gx0, gy0 = int(math.floor((box.x0 - rules.min_clearance_mm) / cell_sz)), int(math.floor((box.y0 - rules.min_clearance_mm) / cell_sz))
            gx1, gy1 = int(math.floor((box.x1 + rules.min_clearance_mm) / cell_sz)), int(math.floor((box.y1 + rules.min_clearance_mm) / cell_sz))
            for gx in range(gx0, gx1 + 1):
                for gy in range(gy0, gy1 + 1):
                    pad_grid[(gx, gy)].append(idx)

        seen_pad_pairs: set[tuple[int, int]] = set()
        for indices in pad_grid.values():
            m_len = len(indices)
            for a_i in range(m_len):
                i = indices[a_i]
                bi, ni, li = layer_pads[i]
                for b_i in range(a_i + 1, m_len):
                    j = indices[b_i]
                    pair = (i, j) if i < j else (j, i)
                    if pair in seen_pad_pairs:
                        continue
                    seen_pad_pairs.add(pair)
                    bj, nj, lj = layer_pads[j]
                    if ni and ni == nj:
                        continue
                    d = bi.dist_to_box(bj)
                    _record_clr(d, f"pad {li} ({ni}) vs pad {lj} ({nj}) on {layer}")

        # Segments on this layer
        layer_segs = [
            (x0, y0, x1, y1, w, nname)
            for x0, y0, x1, y1, w, sl, nname in segments
            if sl == layer
        ]
        # Track vs Pad & Track vs Track via grid
        seg_grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        for idx, (x0, y0, x1, y1, w, nname) in enumerate(layer_segs):
            hw = 0.5 * w + rules.min_clearance_mm
            gx0, gy0 = int(math.floor((min(x0, x1) - hw) / cell_sz)), int(math.floor((min(y0, y1) - hw) / cell_sz))
            gx1, gy1 = int(math.floor((max(x0, x1) + hw) / cell_sz)), int(math.floor((max(y0, y1) + hw) / cell_sz))
            checked_pads: set[int] = set()
            for gx in range(gx0, gx1 + 1):
                for gy in range(gy0, gy1 + 1):
                    seg_grid[(gx, gy)].append(idx)
                    for pidx in pad_grid.get((gx, gy), ()):
                        if pidx in checked_pads:
                            continue
                        checked_pads.add(pidx)
                        pbox, pnet, plbl = layer_pads[pidx]
                        if nname and nname == pnet:
                            continue
                        d = _dist_seg_to_box(x0, y0, x1, y1, pbox) - 0.5 * w
                        _record_clr(d, f"trace {nname!r} vs pad {plbl} ({pnet}) on {layer}")

        seen_seg_pairs: set[tuple[int, int]] = set()
        for indices in seg_grid.values():
            m_len = len(indices)
            for a_i in range(m_len):
                i = indices[a_i]
                ax0, ay0, ax1, ay1, aw, an = layer_segs[i]
                for b_i in range(a_i + 1, m_len):
                    j = indices[b_i]
                    pair = (i, j) if i < j else (j, i)
                    if pair in seen_seg_pairs:
                        continue
                    seen_seg_pairs.add(pair)
                    bx0, by0, bx1, by1, bw, bn = layer_segs[j]
                    if an and an == bn:
                        continue
                    d = _dist_seg_to_seg(ax0, ay0, ax1, ay1, bx0, by0, bx1, by1) - 0.5 * (aw + bw)
                    _record_clr(d, f"trace {an!r} vs trace {bn!r} on {layer}")

        # Vias on this layer vs pads, segments, and other vias
        layer_vias = [(vx, vy, vsize, nname) for vx, vy, vsize, _, vlayers, nname in vias if layer in vlayers]
        for vi, (vx, vy, vsize, vnet) in enumerate(layer_vias):
            vr = 0.5 * vsize
            gx, gy = int(math.floor(vx / cell_sz)), int(math.floor(vy / cell_sz))
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    for pidx in pad_grid.get((gx + ox, gy + oy), ()):
                        pbox, pnet, plbl = layer_pads[pidx]
                        if vnet and vnet == pnet:
                            continue
                        d = pbox.dist_to_point(vx, vy) - vr
                        _record_clr(d, f"via {vnet!r} at ({vx:.2f},{vy:.2f}) vs pad {plbl} ({pnet}) on {layer}")
                    for sidx in seg_grid.get((gx + ox, gy + oy), ()):
                        sx0, sy0, sx1, sy1, sw, snet = layer_segs[sidx]
                        if vnet and vnet == snet:
                            continue
                        d = _dist_point_to_seg(vx, vy, sx0, sy0, sx1, sy1) - vr - 0.5 * sw
                        _record_clr(d, f"via {vnet!r} at ({vx:.2f},{vy:.2f}) vs trace {snet!r} on {layer}")
            for vj in range(vi + 1, len(layer_vias)):
                vx2, vy2, vsize2, vnet2 = layer_vias[vj]
                if vnet and vnet == vnet2:
                    continue
                d = math.hypot(vx - vx2, vy - vy2) - vr - 0.5 * vsize2
                _record_clr(d, f"via {vnet!r} vs via {vnet2!r} on {layer}")

    # --- CHECK C: Controlled-Impedance Microstrip / Stripline Analytical Verification (±5%) ---
    # Helper: compute dielectric reference geometry for any copper layer from parsed stackup
    def _layer_dielectric_params(layer_name: str) -> tuple[str, float, float, float]:
        """Return (mode 'microstrip'|'stripline', h_or_b_mm, t_cu_mm, er)."""
        idx = next((k for k, e in enumerate(stackup_entries) if e["name"] == layer_name), None)
        if idx is None:
            raise ValueError(f"Layer {layer_name!r} not in stackup")
        t_cu = stackup_entries[idx]["thickness_mm"]
        # Find nearest dielectric above & below to next copper plane
        above_h, above_er = 0.0, 1.0
        for k in range(idx - 1, -1, -1):
            e = stackup_entries[k]
            if e["type"] == "copper" or e["name"].endswith(".Cu"):
                break
            if e["type"] in ("core", "prepreg"):
                above_h += e["thickness_mm"]
                above_er = e["epsilon_r"]
        below_h, below_er = 0.0, 1.0
        for k in range(idx + 1, len(stackup_entries)):
            e = stackup_entries[k]
            if e["type"] == "copper" or e["name"].endswith(".Cu"):
                break
            if e["type"] in ("core", "prepreg"):
                below_h += e["thickness_mm"]
                below_er = e["epsilon_r"]
        if layer_name in ("F.Cu", "B.Cu") or above_h == 0.0 or below_h == 0.0:
            h = below_h if below_h > 0.0 else above_h
            er = below_er if below_h > 0.0 else above_er
            return ("microstrip", h, t_cu, er)
        er_avg = (above_h * above_er + below_h * below_er) / (above_h + below_h)
        return ("stripline", above_h + below_h + t_cu, t_cu, er_avg)

    # Map trace-level differential spacing metadata from BoardSpec if provided
    trace_diff_spacing: dict[str, float] = {}
    for tr in board_spec.traces:
        if tr.diff_spacing_mm is not None:
            trace_diff_spacing[tr.net] = tr.diff_spacing_mm

    impedance_checks: list[dict[str, Any]] = []
    for ns in board_spec.nets:
        if ns.target_z0_ohm is None:
            continue
        net_segs = [s for s in segments if s[6] == ns.name]
        if not net_segs:
            errors.append(f"Controlled-impedance net {ns.name!r} (target {ns.target_z0_ohm} Ohm) has 0 routed segments")
            continue
        if ns.diff_pair_with:
            total_len = 0.0
            in_tol_len = 0.0
            coupled_seg_count = 0
            for x0, y0, x1, y1, w, layer, _ in net_segs:
                seg_len = math.hypot(x1 - x0, y1 - y0)
                total_len += seg_len
                mode, hb, t_cu, er = _layer_dielectric_params(layer)
                partner_segs = [s for s in segments if s[6] == ns.diff_pair_with and s[5] == layer]
                measured_s: float | None = None
                for px0, py0, px1, py1, pw, _, _ in partner_segs:
                    d_edge = _dist_seg_to_seg(x0, y0, x1, y1, px0, py0, px1, py1) - 0.5 * (w + pw)
                    if d_edge > 0.0 and (measured_s is None or d_edge < measured_s):
                        measured_s = d_edge
                spacing = measured_s if measured_s is not None else trace_diff_spacing.get(ns.name)
                if spacing is None:
                    # Short pad-entry dogleg (<2.0 mm) on breakout layer is tolerated only if >=75% body is coupled
                    if seg_len >= 2.0:
                        errors.append(
                            f"Diff-pair net {ns.name!r} segment ({seg_len:.2f} mm) has no coupled spacing to {ns.diff_pair_with!r} on {layer}"
                        )
                    continue
                z0 = (
                    calc_diff_microstrip_z0(w, spacing, hb, t_cu, er)
                    if mode == "microstrip"
                    else calc_diff_stripline_z0(w, spacing, hb, t_cu, er)
                )
                err_pct = abs(z0 - ns.target_z0_ohm) / ns.target_z0_ohm * 100.0
                seg_ok = err_pct <= rules.impedance_tol_pct
                if seg_ok:
                    in_tol_len += seg_len
                    coupled_seg_count += 1
                # Record body segments (or all segments if short board) and enforce strict ±5% on body >= 2.0 mm
                if seg_len >= 2.0 or len(net_segs) <= 2:
                    rec = {
                        "net": ns.name,
                        "layer": layer,
                        "mode": f"diff_{mode}",
                        "width_mm": w,
                        "spacing_mm": round(spacing, 4),
                        "h_or_b_mm": round(hb, 4),
                        "epsilon_r": er,
                        "target_z0_ohm": ns.target_z0_ohm,
                        "computed_z0_ohm": round(z0, 3),
                        "error_pct": round(err_pct, 3),
                        "passed": seg_ok,
                    }
                    impedance_checks.append(rec)
                    if not seg_ok:
                        errors.append(
                            f"Impedance DRC fail on {ns.name!r} ({layer}, diff_{mode}, L={seg_len:.2f} mm): "
                            f"Z0={z0:.2f} Ohm vs target {ns.target_z0_ohm:.2f} Ohm ({err_pct:.2f}% > ±{rules.impedance_tol_pct}%)"
                        )
            coupled_frac = in_tol_len / max(total_len, 1e-9)
            if coupled_seg_count == 0 or coupled_frac < 0.70:
                errors.append(
                    f"Diff-pair net {ns.name!r} coupled length fraction {coupled_frac*100:.1f}% < 70.0% within ±{rules.impedance_tol_pct}%"
                )
            continue

        for x0, y0, x1, y1, w, layer, _ in net_segs:
            mode, hb, t_cu, er = _layer_dielectric_params(layer)
            z0 = (
                calc_microstrip_z0(w, hb, t_cu, er)
                if mode == "microstrip"
                else calc_stripline_z0(w, hb, t_cu, er)
            )
            kind_str = mode
            err_pct = abs(z0 - ns.target_z0_ohm) / ns.target_z0_ohm * 100.0
            rec = {
                "net": ns.name,
                "layer": layer,
                "mode": kind_str,
                "width_mm": w,
                "h_or_b_mm": round(hb, 4),
                "epsilon_r": er,
                "target_z0_ohm": ns.target_z0_ohm,
                "computed_z0_ohm": round(z0, 3),
                "error_pct": round(err_pct, 3),
                "passed": err_pct <= rules.impedance_tol_pct,
            }
            impedance_checks.append(rec)
            if not rec["passed"]:
                errors.append(
                    f"Impedance DRC fail on {ns.name!r} ({layer}, {kind_str}): "
                    f"Z0={z0:.2f} Ohm vs target {ns.target_z0_ohm:.2f} Ohm ({err_pct:.2f}% > ±{rules.impedance_tol_pct}%)"
                )

    # --- CHECK D: IPC-2221 / IEC-61010 HV Creepage & Clearance Verification ---
    net_voltages_signed = {ns.name: float(ns.voltage_v) for ns in board_spec.nets}
    net_voltages = {ns.name: abs(ns.voltage_v) for ns in board_spec.nets}
    hv_checks: list[dict[str, Any]] = []

    def _is_intra_hv_differential(rule_obj: CreepageRule, net_a: str, net_b: str) -> bool:
        """Return True if two distinct HV-group nets can experience high open-switch voltage differential."""
        if net_a == net_b:
            return False
        # 1) Explicit voltage difference in NetSpec >= 50% of working_voltage_v
        if abs(net_voltages_signed.get(net_a, 0.0) - net_voltages_signed.get(net_b, 0.0)) >= 0.5 * abs(rule_obj.working_voltage_v):
            return True
        # 2) Explicit differential_pairs patterns on CreepageRule
        for pat_a, pat_b in rule_obj.differential_pairs:
            if (fnmatch.fnmatch(net_a, pat_a) and fnmatch.fnmatch(net_b, pat_b)) or (
                fnmatch.fnmatch(net_a, pat_b) and fnmatch.fnmatch(net_b, pat_a)
            ):
                return True
        # 3) Automatic open-switch crowbar/clamp net detection (prevents DRC grouping bypass!)
        ua, ub = net_a.upper(), net_b.upper()
        hot_toks = ("BUS", "OUT", "_IN")
        sw_toks = ("DUMP", "CLAMP_NODE", "CROWBAR_RTN")
        a_hot = any(t in ua for t in hot_toks) and not any(t in ua for t in sw_toks)
        b_hot = any(t in ub for t in hot_toks) and not any(t in ub for t in sw_toks)
        a_sw = any(t in ua for t in sw_toks)
        b_sw = any(t in ub for t in sw_toks)
        if (a_hot and b_sw) or (b_hot and a_sw):
            return True
        return False

    # Precompute adjacent copper layer pairs & dielectric separation thicknesses from stackup
    adj_cu_pairs: list[tuple[str, str, float]] = []
    cu_stack_indices = [k for k, e in enumerate(stackup_entries) if e["name"] in all_cu_names]
    for ci in range(len(cu_stack_indices) - 1):
        i_a, i_b = cu_stack_indices[ci], cu_stack_indices[ci + 1]
        d_between = sum(
            stackup_entries[k]["thickness_mm"]
            for k in range(i_a + 1, i_b)
            if stackup_entries[k]["type"] in ("core", "prepreg")
        )
        if d_between > 0.0:
            adj_cu_pairs.append((stackup_entries[i_a]["name"], stackup_entries[i_b]["name"], d_between))

    for rule in board_spec.creepage_rules:
        matched_hv = {ns.name for ns in board_spec.nets if fnmatch.fnmatch(ns.name, rule.net_pattern)}
        if not matched_hv:
            errors.append(f"CreepageRule pattern {rule.net_pattern!r} matched 0 nets in BoardSpec")
            continue

        min_clr: float | None = None
        min_crp: float | None = None
        worst_pair = ""

        # Collect primitives on HV nets vs lower-voltage nets per layer
        hv_by_layer: dict[str, list[tuple[_Box, str, str]]] = defaultdict(list)
        lv_by_layer: dict[str, list[tuple[_Box, str, str]]] = defaultdict(list)
        for layer in all_cu_names:
            for box, nname, layers, lbl, _ in pads:
                if layer not in layers or not nname:
                    continue
                if nname in matched_hv:
                    hv_by_layer[layer].append((box, nname, f"pad:{lbl}"))
                elif abs(rule.working_voltage_v - net_voltages.get(nname, 0.0)) >= 0.5 * rule.working_voltage_v:
                    lv_by_layer[layer].append((box, nname, f"pad:{lbl}"))
            for x0, y0, x1, y1, w, sl, nname in segments:
                if sl != layer or not nname:
                    continue
                hw = 0.5 * w
                sbox = _Box(min(x0, x1) - hw, min(y0, y1) - hw, max(x0, x1) + hw, max(y0, y1) + hw)
                if nname in matched_hv:
                    hv_by_layer[layer].append((sbox, nname, f"seg:{nname}"))
                elif abs(rule.working_voltage_v - net_voltages.get(nname, 0.0)) >= 0.5 * rule.working_voltage_v:
                    lv_by_layer[layer].append((sbox, nname, f"seg:{nname}"))
            for vx, vy, vsize, _, vlayers, nname in vias:
                if layer not in vlayers or not nname:
                    continue
                vr = 0.5 * vsize
                vbox = _Box(vx - vr, vy - vr, vx + vr, vy + vr)
                if nname in matched_hv:
                    hv_by_layer[layer].append((vbox, nname, f"via:{nname}"))
                elif abs(rule.working_voltage_v - net_voltages.get(nname, 0.0)) >= 0.5 * rule.working_voltage_v:
                    lv_by_layer[layer].append((vbox, nname, f"via:{nname}"))

            # Check HV primitives vs LV primitives
            for hbox, hnet, hlbl in hv_by_layer[layer]:
                for lbox, lnet, llbl in lv_by_layer[layer]:
                    d_clr = hbox.dist_to_box(lbox)
                    p1_e, p2_e = hbox.closest_points_to(lbox)
                    d_crp = _creepage_around_slots(p1_e, p2_e, d_clr, air_slots)
                    if min_clr is None or d_clr < min_clr:
                        min_clr = d_clr
                        worst_pair = f"{hlbl}({hnet}) vs {llbl}({lnet}) on {layer}"
                    if min_crp is None or d_crp < min_crp:
                        min_crp = d_crp

            # Check intra-group HV differential pairs (open-switch crowbar contacts, differing HV potentials!)
            hv_items_l = hv_by_layer[layer]
            n_hv_l = len(hv_items_l)
            for idx_a in range(n_hv_l):
                hbox_a, hnet_a, hlbl_a = hv_items_l[idx_a]
                for idx_b in range(idx_a + 1, n_hv_l):
                    hbox_b, hnet_b, hlbl_b = hv_items_l[idx_b]
                    if not _is_intra_hv_differential(rule, hnet_a, hnet_b):
                        continue
                    d_clr = hbox_a.dist_to_box(hbox_b)
                    p1_e, p2_e = hbox_a.closest_points_to(hbox_b)
                    d_crp = _creepage_around_slots(p1_e, p2_e, d_clr, air_slots)
                    if min_clr is None or d_clr < min_clr:
                        min_clr = d_clr
                        worst_pair = f"{hlbl_a}({hnet_a}) vs {hlbl_b}({hnet_b}) on {layer}"
                    if min_crp is None or d_crp < min_crp:
                        min_crp = d_crp

            # Check HV feature overlap against lower-voltage copper zones on the SAME layer
            for znet, zlayer, zbox, _ in copper_zones:
                if zlayer != layer or znet in matched_hv:
                    continue
                if abs(rule.working_voltage_v - net_voltages.get(znet, 0.0)) < 0.5 * rule.working_voltage_v:
                    continue
                for hbox, hnet, hlbl in hv_by_layer[layer]:
                    d_clr = hbox.dist_to_box(zbox)
                    p1_e, p2_e = hbox.closest_points_to(zbox)
                    d_crp = _creepage_around_slots(p1_e, p2_e, d_clr, air_slots)
                    if min_clr is None or d_clr < min_clr:
                        min_clr = d_clr
                        worst_pair = f"{hlbl}({hnet}) vs zone({znet}) on {layer}"
                    if min_crp is None or d_crp < min_crp:
                        min_crp = d_crp

        # Through-board dielectric withstand check between adjacent copper layers if working_voltage_v >= 1000 V
        # Checks ALL HV pads, segments, AND vias against ALL LV zones/primitives AND intra-HV differential pairs!
        through_board_ok = True
        if rule.working_voltage_v >= 1000.0:
            for l_a, l_b, d_thick in adj_cu_pairs:
                field_v_mm = rule.working_voltage_v / max(d_thick, 1e-6)
                if field_v_mm <= rules.max_dielectric_field_v_per_mm:
                    continue
                for hv_l, lv_l in ((l_a, l_b), (l_b, l_a)):
                    hv_items = hv_by_layer[hv_l]
                    if not hv_items:
                        continue
                    lv_items: list[tuple[_Box, str, str]] = list(lv_by_layer[lv_l])
                    for znet, zlayer, zbox, _ in copper_zones:
                        if zlayer == lv_l and znet not in matched_hv:
                            if abs(rule.working_voltage_v - net_voltages.get(znet, 0.0)) >= 0.5 * rule.working_voltage_v:
                                lv_items.append((zbox, znet, f"zone:{znet}"))
                    for hbox, hnet, hlbl in hv_items:
                        for lbox, lnet, llbl in lv_items:
                            if hbox.dist_to_box(lbox) <= 1e-6:
                                through_board_ok = False
                                errors.append(
                                    f"Through-board HV dielectric stress on {hlbl}({hnet}) [{hv_l}] over {llbl}({lnet}) [{lv_l}]: "
                                    f"{field_v_mm:.0f} V/mm > {rules.max_dielectric_field_v_per_mm:.0f} V/mm (d={d_thick:.3f} mm)"
                                )
                        for hbox2, hnet2, hlbl2 in hv_by_layer[lv_l]:
                            if _is_intra_hv_differential(rule, hnet, hnet2) and hbox.dist_to_box(hbox2) <= 1e-6:
                                through_board_ok = False
                                errors.append(
                                    f"Through-board HV differential stress on {hlbl}({hnet}) [{hv_l}] over {hlbl2}({hnet2}) [{lv_l}]: "
                                    f"{field_v_mm:.0f} V/mm > {rules.max_dielectric_field_v_per_mm:.0f} V/mm (d={d_thick:.3f} mm)"
                                )

        passed_rule = (
            min_clr is not None
            and min_crp is not None
            and min_clr >= rule.min_clearance_mm - 1e-6
            and min_crp >= rule.min_creepage_mm - 1e-6
            and through_board_ok
        )
        hv_rec = {
            "pattern": rule.net_pattern,
            "matched_nets": sorted(matched_hv),
            "working_voltage_v": rule.working_voltage_v,
            "standard": rule.standard,
            "req_clearance_mm": rule.min_clearance_mm,
            "req_creepage_mm": rule.min_creepage_mm,
            "measured_clearance_mm": round(min_clr, 4) if min_clr is not None else None,
            "measured_creepage_mm": round(min_crp, 4) if min_crp is not None else None,
            "worst_pair": worst_pair,
            "through_board_ok": through_board_ok,
            "passed": passed_rule,
        }
        hv_checks.append(hv_rec)
        if not passed_rule:
            errors.append(
                f"HV Creepage/Clearance DRC fail for {rule.net_pattern!r} ({rule.working_voltage_v} V): "
                f"clr={min_clr} mm (req>={rule.min_clearance_mm}), crp={min_crp} mm (req>={rule.min_creepage_mm}) [{worst_pair}]"
            )

    # --- CHECK E: Strict Physical Pad-Segment-Via-Zone Copper Connectivity & Dangling-Track DRC ---
    conn_tol = 0.015
    pads_by_net: dict[str, list[tuple[_Box, tuple[str, ...], str]]] = defaultdict(list)
    for box, nname, layers, lbl, _ in pads:
        if nname:
            pads_by_net[nname].append((box, layers, lbl))
    segs_by_net: dict[str, list[tuple[float, float, float, float, float, str]]] = defaultdict(list)
    for x0, y0, x1, y1, w, layer, nname in segments:
        if nname:
            segs_by_net[nname].append((x0, y0, x1, y1, w, layer))
    vias_by_net: dict[str, list[tuple[float, float, float, tuple[str, ...]]]] = defaultdict(list)
    for vx, vy, vsize, _, vlayers, nname in vias:
        if nname:
            vias_by_net[nname].append((vx, vy, vsize, vlayers))
    zones_by_net: dict[str, list[tuple[str, _Box, tuple[tuple[float, float], ...]]]] = defaultdict(list)
    for znet, zlayer, zbox, zpoly in copper_zones:
        if znet:
            zones_by_net[znet].append((zlayer, zbox, zpoly))

    # Flag any segment or via on net 0 (unassigned copper) as dangling
    track_dangling_count = 0
    for x0, y0, x1, y1, w, layer, nname in segments:
        if not nname:
            track_dangling_count += 1
            errors.append(f"Dangling trace on unassigned net 0 ({layer}) ({x0:.2f},{y0:.2f})-({x1:.2f},{y1:.2f})")

    routed_net_count = 0
    unrouted_net_count = 0
    unconnected_items = 0
    total_multi_pin_nets = 0

    all_active_nets = sorted(set(pads_by_net.keys()) | set(segs_by_net.keys()) | set(vias_by_net.keys()))
    for nname in all_active_nets:
        npads = pads_by_net.get(nname, [])
        nsegs = segs_by_net.get(nname, [])
        nvias = vias_by_net.get(nname, [])
        nzones = zones_by_net.get(nname, [])

        # Union-Find indices: [0..P-1] pads, [P..P+S-1] segs, [P+S..P+S+V-1] vias, [P+S+V..P+S+V+Z-1] zones
        n_p, n_s, n_v, n_z = len(npads), len(nsegs), len(nvias), len(nzones)
        off_s = n_p
        off_v = off_s + n_s
        off_z = off_v + n_v
        uf_parent = list(range(off_z + n_z))

        def uf_find(i: int) -> int:
            while uf_parent[i] != i:
                uf_parent[i] = uf_parent[uf_parent[i]]
                i = uf_parent[i]
            return i

        def uf_union(i: int, j: int) -> None:
            ri, rj = uf_find(i), uf_find(j)
            if ri != rj:
                uf_parent[ri] = rj

        # 1. Pad <-> Pad (touching same-net pads on shared layer)
        for i in range(n_p):
            bi, li, _ = npads[i]
            li_set = set(li)
            for j in range(i + 1, n_p):
                bj, lj, _ = npads[j]
                if li_set.intersection(lj) and bi.dist_to_box(bj) <= conn_tol:
                    uf_union(i, j)

        # 2. Pad <-> Segment, Pad <-> Via, Pad <-> Zone
        for i, (pbox, players, _) in enumerate(npads):
            pl_set = set(players)
            pcx, pcy = pbox.center
            for j, (x0, y0, x1, y1, w, sl) in enumerate(nsegs):
                if sl in pl_set and _dist_seg_to_box(x0, y0, x1, y1, pbox) <= 0.5 * w + conn_tol:
                    uf_union(i, off_s + j)
            for k, (vx, vy, vsize, vlayers) in enumerate(nvias):
                if pl_set.intersection(vlayers) and pbox.dist_to_point(vx, vy) <= 0.5 * vsize + conn_tol:
                    uf_union(i, off_v + k)
            for m, (zl, zbox, zpoly) in enumerate(nzones):
                if zl in pl_set and pbox.dist_to_box(zbox) <= conn_tol:
                    if _point_in_zone_copper(pcx, pcy, zpoly, zl, keepout_zones, air_slots, tol=conn_tol):
                        uf_union(i, off_z + m)

        # 3. Segment <-> Segment, Segment <-> Via, Segment <-> Zone
        for j, (ax0, ay0, ax1, ay1, aw, al) in enumerate(nsegs):
            for j2 in range(j + 1, n_s):
                bx0, by0, bx1, by1, bw, bl = nsegs[j2]
                if al == bl and _dist_seg_to_seg(ax0, ay0, ax1, ay1, bx0, by0, bx1, by1) <= 0.5 * (aw + bw) + conn_tol:
                    uf_union(off_s + j, off_s + j2)
            for k, (vx, vy, vsize, vlayers) in enumerate(nvias):
                if al in vlayers and _dist_point_to_seg(vx, vy, ax0, ay0, ax1, ay1) <= 0.5 * vsize + 0.5 * aw + conn_tol:
                    uf_union(off_s + j, off_v + k)
            for m, (zl, zbox, zpoly) in enumerate(nzones):
                if al == zl and _dist_seg_to_box(ax0, ay0, ax1, ay1, zbox) <= 0.5 * aw + conn_tol:
                    mx, my = 0.5 * (ax0 + ax1), 0.5 * (ay0 + ay1)
                    if (
                        _point_in_zone_copper(ax0, ay0, zpoly, zl, keepout_zones, air_slots, tol=conn_tol)
                        or _point_in_zone_copper(ax1, ay1, zpoly, zl, keepout_zones, air_slots, tol=conn_tol)
                        or _point_in_zone_copper(mx, my, zpoly, zl, keepout_zones, air_slots, tol=conn_tol)
                    ):
                        uf_union(off_s + j, off_z + m)

        # 4. Via <-> Via, Via <-> Zone
        for k, (vx, vy, vsize, vlayers) in enumerate(nvias):
            vl_set = set(vlayers)
            for k2 in range(k + 1, n_v):
                vx2, vy2, vsize2, vlayers2 = nvias[k2]
                if vl_set.intersection(vlayers2) and math.hypot(vx - vx2, vy - vy2) <= 0.5 * (vsize + vsize2) + conn_tol:
                    uf_union(off_v + k, off_v + k2)
            for m, (zl, zbox, zpoly) in enumerate(nzones):
                if zl in vl_set and zbox.dist_to_point(vx, vy) <= 0.5 * vsize + conn_tol:
                    if _point_in_zone_copper(vx, vy, zpoly, zl, keepout_zones, air_slots, tol=0.5 * vsize + conn_tol):
                        uf_union(off_v + k, off_z + m)

        # 5. Zone <-> Zone (same net, same layer, overlapping)
        for m in range(n_z):
            zlm, zbm, _ = nzones[m]
            for m2 in range(m + 1, n_z):
                zlm2, zbm2, _ = nzones[m2]
                if zlm == zlm2 and zbm.dist_to_box(zbm2) <= conn_tol:
                    uf_union(off_z + m, off_z + m2)

        pad_roots = {uf_find(i) for i in range(n_p)}

        # 6. Dangling-track check on every segment (both endpoints terminated AND connected to >=1 pad)
        def _endpoint_terminated(ex: float, ey: float, w: float, layer: str, self_idx: int) -> bool:
            hw = 0.5 * w
            for pbox, players, _ in npads:
                if layer in players and pbox.dist_to_point(ex, ey) <= hw + conn_tol:
                    return True
            for vx, vy, vsize, vlayers in nvias:
                if layer in vlayers and math.hypot(ex - vx, ey - vy) <= 0.5 * vsize + hw + conn_tol:
                    return True
            for zl, zbox, zpoly in nzones:
                if layer == zl and zbox.dist_to_point(ex, ey) <= hw + conn_tol:
                    if _point_in_zone_copper(ex, ey, zpoly, zl, keepout_zones, air_slots, tol=hw + conn_tol):
                        return True
            for j2, (bx0, by0, bx1, by1, bw, bl) in enumerate(nsegs):
                if j2 == self_idx or bl != layer:
                    continue
                if _dist_point_to_seg(ex, ey, bx0, by0, bx1, by1) <= 0.5 * (w + bw) + conn_tol:
                    return True
            return False

        for j, (ax0, ay0, ax1, ay1, aw, al) in enumerate(nsegs):
            reasons: list[str] = []
            if uf_find(off_s + j) not in pad_roots:
                reasons.append("floating island touching 0 same-net pads")
            if not _endpoint_terminated(ax0, ay0, aw, al, j):
                reasons.append(f"open start ({ax0:.2f},{ay0:.2f})")
            if not _endpoint_terminated(ax1, ay1, aw, al, j):
                reasons.append(f"open end ({ax1:.2f},{ay1:.2f})")
            if reasons:
                track_dangling_count += 1
                errors.append(
                    f"Dangling/floating trace on net {nname!r} ({al}) ({ax0:.2f},{ay0:.2f})-({ax1:.2f},{ay1:.2f}): "
                    + "; ".join(reasons)
                )

        # 7. Floating-via check
        for k, (vx, vy, _, _) in enumerate(nvias):
            if uf_find(off_v + k) not in pad_roots:
                errors.append(f"Floating/unconnected via on net {nname!r} at ({vx:.2f},{vy:.2f}) touching 0 pads")

        # 8. Multi-pin net completeness (unconnected_items = islands - 1)
        if n_p >= 2:
            total_multi_pin_nets += 1
            n_islands = len(pad_roots)
            if n_islands == 1:
                routed_net_count += 1
            else:
                unrouted_net_count += 1
                unconnected_items += (n_islands - 1)
                errors.append(
                    f"Unconnected net {nname!r}: {n_p} pads split into {n_islands} copper islands "
                    f"({n_islands - 1} missing ratsnest connection(s))"
                )

    return DrcResult(
        passed=(len(errors) == 0),
        errors=errors,
        warnings=warnings,
        pad_count=len(pads),
        segment_count=len(segments),
        via_count=len(vias),
        zone_count=len(copper_zones),
        air_slot_count=len(air_slots),
        min_measured_clearance_mm=round(min_clr_measured, 4) if min_clr_measured is not None else None,
        impedance_checks=impedance_checks,
        hv_checks=hv_checks,
        stackup_summary={
            "copper_layers": len(all_cu_names),
            "total_thickness_mm": round(sum(e["thickness_mm"] for e in stackup_entries), 4),
            "board_size_mm": [round(outline.x1 - outline.x0, 3), round(outline.y1 - outline.y0, 3)],
        },
        routed_net_count=routed_net_count,
        unrouted_net_count=unrouted_net_count,
        unconnected_items=unconnected_items,
        track_dangling_count=track_dangling_count,
        total_multi_pin_nets=total_multi_pin_nets,
    )


# ---------------------------------------------------------------------------
# 8. Portable Real ngspice Discovery, Batch Runner & Output Parser
# ---------------------------------------------------------------------------

def find_ngspice() -> Path:
    """Portably locate real ``ngspice`` binary (zero hardcoded user paths)."""
    env_override = os.environ.get("NGSPICE_BIN")
    if env_override:
        p = Path(env_override)
        if p.is_file() and os.access(p, os.X_OK):
            return p
    which_hit = shutil.which("ngspice")
    if which_hit:
        return Path(which_hit)
    candidates = (
        Path.home() / ".local" / "bin" / "ngspice",
        Path.home() / ".local" / "ngspice" / "usr" / "bin" / "ngspice",
    )
    for cand in candidates:
        if cand.is_file() and os.access(cand, os.X_OK):
            return cand
    raise FileNotFoundError(
        "ngspice binary not found in PATH or ~/.local/bin/ngspice. "
        "Install rootless ngspice into ~/.local/ngspice and ~/.local/bin/ngspice."
    )


def get_ngspice_version() -> str:
    """Return the version string reported by ``ngspice -v`` (e.g. 'ngspice-47')."""
    ng = find_ngspice()
    proc = subprocess.run([str(ng), "-v"], capture_output=True, text=True, timeout=10, check=False)
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    m = re.search(r"(ngspice[- ]?[0-9]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE)
    return m.group(1) if m else text.strip().splitlines()[0]


@dataclass
class NgspiceResult:
    returncode: int
    ok: bool
    version: str
    errors: list[str]
    warnings: list[str]
    metrics: dict[str, float]
    tables: dict[str, list[dict[str, float]]]
    stdout: str
    stderr: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "returncode": self.returncode,
            "ok": self.ok,
            "version": self.version,
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics,
            "table_names": sorted(self.tables.keys()),
        }


_SPICE_ERROR_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\berror\b[: ]", re.IGNORECASE),
    re.compile(r"\bfatal\b", re.IGNORECASE),
    re.compile(r"singular matrix", re.IGNORECASE),
    re.compile(r"timestep too small", re.IGNORECASE),
    re.compile(r"doAnalyses:.*failed", re.IGNORECASE),
    re.compile(r"no such vector", re.IGNORECASE),
    re.compile(r"unrecognized parameter", re.IGNORECASE),
    re.compile(r"unknown subckt", re.IGNORECASE),
    re.compile(r"syntax error", re.IGNORECASE),
    re.compile(r"measurement .* failed", re.IGNORECASE),
    re.compile(r"run simulation\(s\) aborted", re.IGNORECASE),
    re.compile(r"simulation\(s\) aborted", re.IGNORECASE),
)

_SCALAR_METRIC_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_\.\[\]]*)\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?:\s|$)"
)


def run_ngspice(
    cir_path: str | Path,
    workdir: str | Path | None = None,
    timeout_s: float = 60.0,
) -> NgspiceResult:
    """Invoke real ``ngspice -b`` on a SPICE deck, verify zero errors, and parse metrics."""
    cp = Path(cir_path).resolve()
    cwd = Path(workdir).resolve() if workdir is not None else cp.parent
    ng = find_ngspice()
    version = get_ngspice_version()

    proc = subprocess.run(
        [str(ng), "-b", str(cp)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, float] = {}
    tables: dict[str, list[dict[str, float]]] = {}

    if proc.returncode != 0:
        errors.append(f"ngspice exited with non-zero code {proc.returncode}")

    lines = combined.splitlines()
    for line in lines:
        sline = line.strip()
        if not sline:
            continue
        if any(pat.search(sline) for pat in _SPICE_ERROR_PATTERNS):
            # Ignore benign banner/note lines that don't denote errors
            if not sline.startswith("Note:"):
                errors.append(sline)
        elif sline.lower().startswith("warning:"):
            warnings.append(sline)

        # Parse scalar .meas or print lines ("metric_name = 1.234e-05")
        m = _SCALAR_METRIC_RE.match(sline)
        if m:
            key, val_s = m.group(1), m.group(2)
            # Exclude internal SPICE banner/header lines
            if key.lower() not in ("temp", "tnom", "no"):
                try:
                    metrics[key] = float(val_s)
                except ValueError:
                    pass

    # Parse tabular `.print` blocks ("Index  col1  col2 ...")
    cur_table_name = ""
    cur_cols: list[str] = []
    table_idx = 0
    for line in lines:
        sline = line.strip()
        if sline.startswith("Index"):
            cols = sline.split()
            if len(cols) >= 2:
                table_idx += 1
                cur_table_name = f"table_{table_idx}"
                cur_cols = cols
                tables[cur_table_name] = []
            continue
        if cur_cols and sline and sline[0].isdigit():
            parts = sline.replace(",", " ").split()
            if len(parts) >= len(cur_cols):
                try:
                    row = {cur_cols[k]: float(parts[k]) for k in range(len(cur_cols))}
                    tables[cur_table_name].append(row)
                except ValueError:
                    cur_cols = []
        elif cur_cols and (sline.startswith("---") or sline == ""):
            continue
        elif cur_cols and not sline[0].isdigit():
            cur_cols = []

    ok = (proc.returncode == 0) and (len(errors) == 0)
    return NgspiceResult(
        returncode=proc.returncode,
        ok=ok,
        version=version,
        errors=errors,
        warnings=warnings,
        metrics=metrics,
        tables=tables,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


# ---------------------------------------------------------------------------
# 9. Independent Pure-Python Modified Nodal Analysis (MNA) Cross-Checker
# ---------------------------------------------------------------------------

class MnaCircuit:
    """Pure-Python linear AC/DC Modified Nodal Analysis solver for independent SPICE cross-checks.

    Ground node is ``"0"`` (or ``"GND"``). Supports R, C, L, VCVS, VCCS, ideal
    single-pole op-amps, independent voltage sources, and independent current sources.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, int] = {}
        self._resistors: list[tuple[str, str, float]] = []
        self._capacitors: list[tuple[str, str, float]] = []
        self._inductors: list[tuple[str, str, float]] = []
        self._vcvs: list[tuple[str, str, str, str, float]] = []
        self._vccs: list[tuple[str, str, str, str, float]] = []
        self._vsources: list[tuple[str, str, complex, float]] = []  # (np, nn, ac, dc)
        self._isources: list[tuple[str, str, complex, float]] = []  # (np, nn, ac, dc)
        self._opamps: list[tuple[str, str, str, float, float, float, float, float]] = []

    def _reg(self, node: str) -> None:
        if node not in ("0", "GND") and node not in self._nodes:
            self._nodes[node] = len(self._nodes)

    def _idx(self, node: str) -> int | None:
        if node in ("0", "GND"):
            return None
        return self._nodes[node]

    def add_resistor(self, n1: str, n2: str, r_ohm: float) -> None:
        self._reg(n1); self._reg(n2)
        self._resistors.append((n1, n2, float(r_ohm)))

    def add_capacitor(self, n1: str, n2: str, c_f: float) -> None:
        self._reg(n1); self._reg(n2)
        self._capacitors.append((n1, n2, float(c_f)))

    def add_inductor(self, n1: str, n2: str, l_h: float) -> None:
        self._reg(n1); self._reg(n2)
        self._inductors.append((n1, n2, float(l_h)))

    def add_vcvs(self, out_p: str, out_n: str, in_p: str, in_n: str, gain: float) -> None:
        for n in (out_p, out_n, in_p, in_n):
            self._reg(n)
        self._vcvs.append((out_p, out_n, in_p, in_n, float(gain)))

    def add_vccs(self, out_p: str, out_n: str, in_p: str, in_n: str, gm: float) -> None:
        for n in (out_p, out_n, in_p, in_n):
            self._reg(n)
        self._vccs.append((out_p, out_n, in_p, in_n, float(gm)))

    def add_vsource(self, n_p: str, n_n: str, dc: float = 0.0, ac: complex = 0.0) -> None:
        self._reg(n_p); self._reg(n_n)
        self._vsources.append((n_p, n_n, complex(ac), float(dc)))

    def add_isource(self, n_from: str, n_to: str, dc: float = 0.0, ac: complex = 0.0) -> None:
        """Current flows from n_from into n_to (SPICE convention: I n_from n_to val)."""
        self._reg(n_from); self._reg(n_to)
        self._isources.append((n_from, n_to, complex(ac), float(dc)))

    def add_opamp_single_pole(
        self,
        inp: str,
        inn: str,
        out: str,
        a0: float = 1e5,
        gbp_hz: float = 500e6,
        c_in_f: float = 0.0,
        r_in_ohm: float = 1e12,
        r_out_ohm: float = 0.0,
    ) -> None:
        for n in (inp, inn, out):
            self._reg(n)
        if c_in_f > 0.0:
            self.add_capacitor(inp, inn, c_in_f)
        if r_in_ohm > 0.0:
            self.add_resistor(inp, inn, r_in_ohm)
        self._opamps.append((inp, inn, out, float(a0), float(gbp_hz), float(c_in_f), float(r_in_ohm), float(r_out_ohm)))

    def _solve_at_s(self, s: complex, is_dc: bool) -> dict[str, complex]:
        n_v = len(self._nodes)
        n_extra = len(self._vsources) + len(self._vcvs) + len(self._opamps) + (len(self._inductors) if is_dc else 0)
        dim = n_v + n_extra
        A = np.zeros((dim, dim), dtype=np.complex128)
        b = np.zeros(dim, dtype=np.complex128)

        def stamp_y(n1: str, n2: str, y: complex) -> None:
            i, j = self._idx(n1), self._idx(n2)
            if i is not None:
                A[i, i] += y
            if j is not None:
                A[j, j] += y
            if i is not None and j is not None:
                A[i, j] -= y
                A[j, i] -= y

        for n1, n2, r in self._resistors:
            stamp_y(n1, n2, 1.0 / r)
        if not is_dc:
            for n1, n2, c in self._capacitors:
                stamp_y(n1, n2, s * c)
            for n1, n2, l_val in self._inductors:
                stamp_y(n1, n2, 1.0 / (s * l_val))

        for out_p, out_n, in_p, in_n, gm in self._vccs:
            op, on, ip, inn = self._idx(out_p), self._idx(out_n), self._idx(in_p), self._idx(in_n)
            if op is not None and ip is not None:
                A[op, ip] += gm
            if op is not None and inn is not None:
                A[op, inn] -= gm
            if on is not None and ip is not None:
                A[on, ip] -= gm
            if on is not None and inn is not None:
                A[on, inn] += gm

        for n_from, n_to, ac, dc in self._isources:
            val = dc if is_dc else ac
            i_f, i_t = self._idx(n_from), self._idx(n_to)
            if i_f is not None:
                b[i_f] -= val
            if i_t is not None:
                b[i_t] += val

        row = n_v
        for n_p, n_n, ac, dc in self._vsources:
            val = dc if is_dc else ac
            ip, inn = self._idx(n_p), self._idx(n_n)
            if ip is not None:
                A[ip, row] += 1.0
                A[row, ip] += 1.0
            if inn is not None:
                A[inn, row] -= 1.0
                A[row, inn] -= 1.0
            b[row] = val
            row += 1

        for out_p, out_n, in_p, in_n, gain in self._vcvs:
            op, on, ip, inn = self._idx(out_p), self._idx(out_n), self._idx(in_p), self._idx(in_n)
            if op is not None:
                A[op, row] += 1.0
                A[row, op] += 1.0
            if on is not None:
                A[on, row] -= 1.0
                A[row, on] -= 1.0
            if ip is not None:
                A[row, ip] -= gain
            if inn is not None:
                A[row, inn] += gain
            row += 1

        for inp, inn, out, a0, gbp_hz, _, _, r_out in self._opamps:
            wp = 2.0 * math.pi * gbp_hz / a0
            a_ol = a0 if is_dc else a0 / (1.0 + s / wp)
            io, ip, in_i = self._idx(out), self._idx(inp), self._idx(inn)
            if io is not None:
                A[io, row] += 1.0
                A[row, io] += 1.0
            if r_out > 0.0:
                A[row, row] -= r_out
            if ip is not None:
                A[row, ip] -= a_ol
            if in_i is not None:
                A[row, in_i] += a_ol
            row += 1

        if is_dc:
            for n1, n2, _ in self._inductors:
                i1, i2 = self._idx(n1), self._idx(n2)
                if i1 is not None:
                    A[i1, row] += 1.0
                    A[row, i1] += 1.0
                if i2 is not None:
                    A[i2, row] -= 1.0
                    A[row, i2] -= 1.0
                row += 1

        sol = np.linalg.solve(A, b)
        out_dict = {"0": 0.0 + 0.0j, "GND": 0.0 + 0.0j}
        for name, idx in self._nodes.items():
            out_dict[name] = complex(sol[idx])
        return out_dict

    def solve_dc(self) -> dict[str, float]:
        res = self._solve_at_s(0.0 + 0.0j, is_dc=True)
        return {k: float(v.real) for k, v in res.items()}

    def solve_ac(self, freqs_hz: np.ndarray | Sequence[float]) -> dict[str, np.ndarray]:
        freqs = np.asarray(freqs_hz, dtype=float)
        out: dict[str, np.ndarray] = {name: np.zeros(len(freqs), dtype=np.complex128) for name in self._nodes}
        out["0"] = np.zeros(len(freqs), dtype=np.complex128)
        for k, f in enumerate(freqs):
            s = 1j * 2.0 * math.pi * float(f)
            sol = self._solve_at_s(s, is_dc=False)
            for name in self._nodes:
                out[name][k] = sol[name]
        return out


# ---------------------------------------------------------------------------
# 10. Deterministic Multi-Layer Physical Copper Router & Guard-Ring Helper
# ---------------------------------------------------------------------------

def connect_guard_ring(
    net: str,
    layer: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    width_mm: float = 0.25,
    via_layer: str = "B.Cu",
    via_diameter_mm: float = 0.50,
    via_drill_mm: float = 0.25,
    top_only_rails: bool = False,
) -> tuple[list[TraceSpec], list[ViaSpec]]:
    """Construct a physically closed, zero-dangling-endpoint guard ring around [x0, x1] x [y0, y1].

    When ``top_only_rails=True`` (e.g., high-Z CSA_SUM where traces enter/exit horizontally on
    ``layer``), places top & bottom horizontal guard rails on ``layer``, drops 4 corner vias
    outside the keepout window, and closes the left & right vertical rails on ``via_layer``.
    When ``top_only_rails=False``, emits a closed 4-sided copper loop on ``layer`` plus a tie via.
    """
    ax0, ax1 = round(min(x0, x1), 4), round(max(x0, x1), 4)
    ay0, ay1 = round(min(y0, y1), 4), round(max(y0, y1), 4)
    w = round(width_mm, 4)
    if top_only_rails:
        traces = [
            TraceSpec(net=net, layer=layer, points_mm=((ax0, ay0), (ax1, ay0)), width_mm=w, is_guard_ring=True),
            TraceSpec(net=net, layer=layer, points_mm=((ax0, ay1), (ax1, ay1)), width_mm=w, is_guard_ring=True),
            TraceSpec(net=net, layer=via_layer, points_mm=((ax0, ay0), (ax0, ay1)), width_mm=w, is_guard_ring=True),
            TraceSpec(net=net, layer=via_layer, points_mm=((ax1, ay0), (ax1, ay1)), width_mm=w, is_guard_ring=True),
        ]
        vias = [
            ViaSpec(net=net, x_mm=ax0, y_mm=ay0, diameter_mm=via_diameter_mm, drill_mm=via_drill_mm, layers=(layer, via_layer)),
            ViaSpec(net=net, x_mm=ax1, y_mm=ay0, diameter_mm=via_diameter_mm, drill_mm=via_drill_mm, layers=(layer, via_layer)),
            ViaSpec(net=net, x_mm=ax0, y_mm=ay1, diameter_mm=via_diameter_mm, drill_mm=via_drill_mm, layers=(layer, via_layer)),
            ViaSpec(net=net, x_mm=ax1, y_mm=ay1, diameter_mm=via_diameter_mm, drill_mm=via_drill_mm, layers=(layer, via_layer)),
        ]
        return traces, vias
    traces = [
        TraceSpec(
            net=net,
            layer=layer,
            points_mm=((ax0, ay0), (ax1, ay0), (ax1, ay1), (ax0, ay1), (ax0, ay0)),
            width_mm=w,
            is_guard_ring=True,
        ),
    ]
    vias = [
        ViaSpec(net=net, x_mm=ax0, y_mm=ay0, diameter_mm=via_diameter_mm, drill_mm=via_drill_mm, layers=(layer, via_layer)),
    ]
    return traces, vias


def _simplify_polyline(pts: Sequence[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    """Collapse duplicate and collinear intermediate points into minimal orthogonal segments."""
    dedup: list[tuple[float, float]] = []
    for x, y in pts:
        rx, ry = round(x, 4), round(y, 4)
        if not dedup or math.hypot(rx - dedup[-1][0], ry - dedup[-1][1]) > 1e-4:
            dedup.append((rx, ry))
    if len(dedup) <= 2:
        return tuple(dedup)
    out: list[tuple[float, float]] = [dedup[0]]
    for i in range(1, len(dedup) - 1):
        ax, ay = out[-1]
        bx, by = dedup[i]
        cx, cy = dedup[i + 1]
        # Skip collinear midpoint if moving in the same direction (not reversing)
        v1x, v1y = bx - ax, by - ay
        v2x, v2y = cx - bx, cy - by
        cross = abs(v1x * v2y - v1y * v2x)
        dot = v1x * v2x + v1y * v2y
        if cross <= 1e-6 and dot >= 0.0:
            continue
        out.append((bx, by))
    out.append(dedup[-1])
    return tuple(out)


def _stackup_layer_dielectric(
    stackup: Sequence[StackupLayer], layer_name: str
) -> tuple[str, float, float, float]:
    """Compute (mode 'microstrip'|'stripline', h_or_b_mm, t_cu_mm, er) from BoardSpec.stackup."""
    idx = next((k for k, sl in enumerate(stackup) if sl.name == layer_name), None)
    if idx is None:
        raise ValueError(f"Layer {layer_name!r} not in BoardSpec.stackup")
    t_cu = stackup[idx].thickness_mm
    above_h, above_er = 0.0, 1.0
    for k in range(idx - 1, -1, -1):
        sl = stackup[k]
        if sl.is_copper:
            break
        if sl.layer_type in ("core", "prepreg"):
            above_h += sl.thickness_mm
            above_er = sl.epsilon_r
    below_h, below_er = 0.0, 1.0
    for k in range(idx + 1, len(stackup)):
        sl = stackup[k]
        if sl.is_copper:
            break
        if sl.layer_type in ("core", "prepreg"):
            below_h += sl.thickness_mm
            below_er = sl.epsilon_r
    if layer_name in ("F.Cu", "B.Cu") or above_h == 0.0 or below_h == 0.0:
        h = below_h if below_h > 0.0 else above_h
        er = below_er if below_h > 0.0 else above_er
        return ("microstrip", h, t_cu, er)
    er_avg = (above_h * above_er + below_h * below_er) / (above_h + below_h)
    return ("stripline", above_h + below_h + t_cu, t_cu, er_avg)


class _RouteSpace:
    """Spatial-hashed continuous geometry & HV clearance oracle used by auto_route_board."""

    def __init__(self, board_spec: BoardSpec) -> None:
        self.spec = board_spec
        self.rules = board_spec.rules
        self.outline = _Box(0.0, 0.0, board_spec.width_mm, board_spec.height_mm)
        self.cu_layers = [sl.name for sl in board_spec.stackup if sl.is_copper]
        self.cell = 5.0
        self.hv_cell = 15.0

        # Keepouts & air-slots
        self.air_slots: list[_Box] = []
        self.keepout_zones: list[tuple[tuple[str, ...], _Box, bool, bool, bool]] = []
        for ko in board_spec.keepouts:
            kbox = _Box(ko.x_mm, ko.y_mm, ko.x_mm + ko.width_mm, ko.y_mm + ko.height_mm)
            if ko.kind == "air_slot":
                self.air_slots.append(kbox)
            elif ko.kind == "copper_keepout":
                self.keepout_zones.append((ko.layers, kbox, True, True, True))

        # Zones
        self.zones: list[tuple[str, str, _Box, tuple[tuple[float, float], ...]]] = []
        self.zones_by_layer: dict[str, list[tuple[str, _Box, tuple[tuple[float, float], ...]]]] = defaultdict(list)
        self.zones_by_net: dict[str, list[tuple[str, _Box, tuple[tuple[float, float], ...]]]] = defaultdict(list)
        for z in board_spec.zones:
            if z.is_keepout or len(z.polygon_mm) < 3:
                continue
            zbox = _Box(
                min(p[0] for p in z.polygon_mm),
                min(p[1] for p in z.polygon_mm),
                max(p[0] for p in z.polygon_mm),
                max(p[1] for p in z.polygon_mm),
            )
            self.zones.append((z.net, z.layer, zbox, z.polygon_mm))
            self.zones_by_layer[z.layer].append((z.net, zbox, z.polygon_mm))
            self.zones_by_net[z.net].append((z.layer, zbox, z.polygon_mm))

        # Net metadata & HV rules
        self.net_voltage: dict[str, float] = {ns.name: abs(ns.voltage_v) for ns in board_spec.nets}
        self.hv_rules_for_net: dict[str, list[CreepageRule]] = defaultdict(list)
        self.rule_matched_nets: list[tuple[CreepageRule, set[str]]] = []
        # Precomputed per-rule voltage-side membership & coarse HV spatial grids (O(1) domain fast-skip!)
        self.rule_net_roles: dict[str, list[tuple[int, bool]]] = defaultdict(list)  # net -> [(rule_idx, is_hv_side)]
        self.hv_dom_items: list[dict[str, list[tuple[_Box, str]]]] = []
        self.lv_dom_items: list[dict[str, list[tuple[_Box, str]]]] = []
        self.hv_dom_grid: list[dict[str, dict[tuple[int, int], list[int]]]] = []
        self.lv_dom_grid: list[dict[str, dict[tuple[int, int], list[int]]]] = []
        self.hv_dom_bbox: list[dict[str, _Box | None]] = []
        self.lv_dom_bbox: list[dict[str, _Box | None]] = []

        for ridx, rule in enumerate(board_spec.creepage_rules):
            matched = {ns.name for ns in board_spec.nets if fnmatch.fnmatch(ns.name, rule.net_pattern)}
            self.rule_matched_nets.append((rule, matched))
            self.hv_dom_items.append({l: [] for l in self.cu_layers})
            self.lv_dom_items.append({l: [] for l in self.cu_layers})
            self.hv_dom_grid.append({l: defaultdict(list) for l in self.cu_layers})
            self.lv_dom_grid.append({l: defaultdict(list) for l in self.cu_layers})
            self.hv_dom_bbox.append({l: None for l in self.cu_layers})
            self.lv_dom_bbox.append({l: None for l in self.cu_layers})
            for ns in board_spec.nets:
                if ns.name in matched:
                    self.hv_rules_for_net[ns.name].append(rule)
                    self.rule_net_roles[ns.name].append((ridx, True))
                elif abs(rule.working_voltage_v - abs(ns.voltage_v)) >= 0.5 * rule.working_voltage_v:
                    self.rule_net_roles[ns.name].append((ridx, False))

        # Adjacent-layer >= 1000 V dielectric conflict map: layer -> list[(adj_layer, rule, matched_hv)]
        self.adj_hv_conflicts: dict[str, list[tuple[str, CreepageRule, set[str]]]] = defaultdict(list)
        cu_indices = [k for k, sl in enumerate(board_spec.stackup) if sl.is_copper]
        for ci in range(len(cu_indices) - 1):
            ia, ib = cu_indices[ci], cu_indices[ci + 1]
            d_between = sum(
                board_spec.stackup[k].thickness_mm
                for k in range(ia + 1, ib)
                if board_spec.stackup[k].layer_type in ("core", "prepreg")
            )
            la, lb = board_spec.stackup[ia].name, board_spec.stackup[ib].name
            for rule, matched in self.rule_matched_nets:
                if rule.working_voltage_v >= 1000.0 and d_between > 0.0:
                    if rule.working_voltage_v / d_between > self.rules.max_dielectric_field_v_per_mm:
                        self.adj_hv_conflicts[la].append((lb, rule, matched))
                        self.adj_hv_conflicts[lb].append((la, rule, matched))

        # Index zones into HV/LV domain grids
        for znet, zlayer, zbox, _ in self.zones:
            self._index_hv_domain(znet, (zlayer,), zbox)

        # Spatial grids per layer (normal clearance only needs halo ~ min_clearance!)
        self.pad_list: list[tuple[_Box, str, tuple[str, ...], str, bool, tuple[float, float]]] = []
        self.pad_grid: dict[str, dict[tuple[int, int], list[int]]] = {l: defaultdict(list) for l in self.cu_layers}
        self.em_pads_by_net: dict[str, list[tuple[_Box, tuple[str, ...]]]] = defaultdict(list)
        self.seg_list: list[tuple[float, float, float, float, float, str, str]] = []
        self.seg_grid: dict[str, dict[tuple[int, int], list[int]]] = {l: defaultdict(list) for l in self.cu_layers}
        self.via_list: list[tuple[float, float, float, tuple[str, ...], str]] = []
        self.via_grid: dict[str, dict[tuple[int, int], list[int]]] = {l: defaultdict(list) for l in self.cu_layers}

        # Populate pads
        pin_to_net: dict[tuple[str, str], str] = {}
        for ns in board_spec.nets:
            for ref, pin in ns.nodes:
                pin_to_net[(ref, str(pin))] = ns.name

        for comp in board_spec.components:
            pins = comp.pins or auto_footprint_pads(comp.footprint, ("1", "2"))
            for ps in pins:
                px, py, bw, bh = _pad_abs_xy(comp, ps)
                pbox = _Box(px - 0.5 * bw, py - 0.5 * bh, px + 0.5 * bw, py + 0.5 * bh)
                nname = pin_to_net.get((comp.ref, ps.number), "")
                players = tuple(self.cu_layers) if ps.drill_mm > 0.0 else (comp.layer,)
                pidx = len(self.pad_list)
                self.pad_list.append((pbox, nname, players, f"{comp.ref}.{ps.number}", comp.edge_mount, (comp.x_mm, comp.y_mm)))
                if comp.edge_mount and nname:
                    self.em_pads_by_net[nname].append((pbox, players))
                self._index_box(self.pad_grid, players, pbox, pidx)
                if nname:
                    self._index_hv_domain(nname, players, pbox)

    def _index_hv_domain(self, net: str, layers: Sequence[str], box: _Box) -> None:
        roles = self.rule_net_roles.get(net)
        if not roles:
            return
        gx0 = int(math.floor(box.x0 / self.hv_cell))
        gx1 = int(math.floor(box.x1 / self.hv_cell))
        gy0 = int(math.floor(box.y0 / self.hv_cell))
        gy1 = int(math.floor(box.y1 / self.hv_cell))
        for ridx, is_hv in roles:
            items_d = self.hv_dom_items[ridx] if is_hv else self.lv_dom_items[ridx]
            grid_d = self.hv_dom_grid[ridx] if is_hv else self.lv_dom_grid[ridx]
            bbox_d = self.hv_dom_bbox[ridx] if is_hv else self.lv_dom_bbox[ridx]
            for l in layers:
                if l not in items_d:
                    continue
                idx = len(items_d[l])
                items_d[l].append((box, net))
                gl = grid_d[l]
                for gx in range(gx0, gx1 + 1):
                    for gy in range(gy0, gy1 + 1):
                        gl[(gx, gy)].append(idx)
                cur = bbox_d[l]
                if cur is None:
                    bbox_d[l] = box
                else:
                    bbox_d[l] = _Box(min(cur.x0, box.x0), min(cur.y0, box.y0), max(cur.x1, box.x1), max(cur.y1, box.y1))

    def _index_box(
        self,
        grid: dict[str, dict[tuple[int, int], list[int]]],
        layers: Sequence[str],
        box: _Box,
        idx: int,
    ) -> None:
        gx0 = int(math.floor(box.x0 / self.cell))
        gx1 = int(math.floor(box.x1 / self.cell))
        gy0 = int(math.floor(box.y0 / self.cell))
        gy1 = int(math.floor(box.y1 / self.cell))
        for l in layers:
            if l not in grid:
                continue
            gl = grid[l]
            for gx in range(gx0, gx1 + 1):
                for gy in range(gy0, gy1 + 1):
                    gl[(gx, gy)].append(idx)

    def add_segment(self, x0: float, y0: float, x1: float, y1: float, w: float, layer: str, net: str) -> None:
        sidx = len(self.seg_list)
        self.seg_list.append((x0, y0, x1, y1, w, layer, net))
        hw = 0.5 * w
        sbox = _Box(min(x0, x1) - hw, min(y0, y1) - hw, max(x0, x1) + hw, max(y0, y1) + hw)
        self._index_box(self.seg_grid, (layer,), sbox, sidx)
        if net:
            self._index_hv_domain(net, (layer,), sbox)

    def add_via(self, vx: float, vy: float, vsize: float, vlayers: tuple[str, ...], net: str) -> None:
        vidx = len(self.via_list)
        self.via_list.append((vx, vy, vsize, vlayers, net))
        vr = 0.5 * vsize
        vbox = _Box(vx - vr, vy - vr, vx + vr, vy + vr)
        self._index_box(self.via_grid, vlayers, vbox, vidx)
        if net:
            self._index_hv_domain(net, vlayers, vbox)

    def _hv_domain_ok(self, box: _Box, layer: str, net: str, ignore_nets: set[str] | None = None) -> bool:
        """Fast O(1)-skip HV creepage/clearance check against opposite-voltage domain only."""
        roles = self.rule_net_roles.get(net)
        if not roles:
            return True
        for ridx, is_hv in roles:
            rule, _ = self.rule_matched_nets[ridx]
            opp_bbox = (self.lv_dom_bbox[ridx] if is_hv else self.hv_dom_bbox[ridx]).get(layer)
            if opp_bbox is None:
                continue
            # Direct air clearance halo; if creepage > clearance, air-slots can satisfy creepage while
            # direct distance >= min_clearance, so we must scan up to max(min_clr, min_crp)
            req_clr = rule.min_clearance_mm + 0.03
            req_crp = rule.min_creepage_mm + 0.03
            halo = max(req_clr, req_crp)
            if box.dist_to_box(opp_bbox) >= halo:
                continue
            opp_items = (self.lv_dom_items[ridx] if is_hv else self.hv_dom_items[ridx])[layer]
            opp_grid = (self.lv_dom_grid[ridx] if is_hv else self.hv_dom_grid[ridx])[layer]
            gx0 = int(math.floor((box.x0 - halo) / self.hv_cell))
            gx1 = int(math.floor((box.x1 + halo) / self.hv_cell))
            gy0 = int(math.floor((box.y0 - halo) / self.hv_cell))
            gy1 = int(math.floor((box.y1 + halo) / self.hv_cell))
            seen: set[int] = set()
            for gx in range(gx0, gx1 + 1):
                for gy in range(gy0, gy1 + 1):
                    for idx in opp_grid.get((gx, gy), ()):
                        if idx in seen:
                            continue
                        seen.add(idx)
                        obox, onet = opp_items[idx]
                        if onet == net or (ignore_nets and onet in ignore_nets):
                            continue
                        bbox_clr = box.dist_to_box(obox)
                        if bbox_clr >= halo:
                            continue
                        if bbox_clr < req_clr:
                            return False
                        if bbox_clr < req_crp:
                            p1, p2 = box.closest_points_to(obox)
                            if _creepage_around_slots(p1, p2, bbox_clr, self.air_slots) < req_crp:
                                return False
        return True

    def _adj_dielectric_ok(self, box: _Box, layer: str, net: str) -> bool:
        conflicts = self.adj_hv_conflicts.get(layer)
        if not conflicts:
            return True
        gx0 = int(math.floor((box.x0 - 0.1) / self.hv_cell))
        gx1 = int(math.floor((box.x1 + 0.1) / self.hv_cell))
        gy0 = int(math.floor((box.y0 - 0.1) / self.hv_cell))
        gy1 = int(math.floor((box.y1 + 0.1) / self.hv_cell))
        roles = self.rule_net_roles.get(net)
        if not roles:
            return True
        role_map = dict(roles)
        for adj_l, rule, matched in conflicts:
            ridx = next((ri for ri, (rl, _) in enumerate(self.rule_matched_nets) if rl is rule), None)
            if ridx is None or ridx not in role_map:
                continue
            is_hv = role_map[ridx]
            opp_bbox = (self.lv_dom_bbox[ridx] if is_hv else self.hv_dom_bbox[ridx]).get(adj_l)
            if opp_bbox is None or box.dist_to_box(opp_bbox) > 0.05:
                continue
            opp_items = (self.lv_dom_items[ridx] if is_hv else self.hv_dom_items[ridx])[adj_l]
            opp_grid = (self.lv_dom_grid[ridx] if is_hv else self.hv_dom_grid[ridx])[adj_l]
            seen: set[int] = set()
            for gx in range(gx0, gx1 + 1):
                for gy in range(gy0, gy1 + 1):
                    for idx in opp_grid.get((gx, gy), ()):
                        if idx in seen:
                            continue
                        seen.add(idx)
                        obox, onet = opp_items[idx]
                        if onet != net and box.dist_to_box(obox) <= 0.05:
                            return False
        return True

    def _pt_in_em_pad(self, x: float, y: float, net: str, layer: str) -> bool:
        for pbox, players in self.em_pads_by_net.get(net, ()):
            if layer in players and pbox.dist_to_point(x, y) <= 0.015:
                return True
        return False

    def segment_ok(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        w: float,
        layer: str,
        net: str,
        ignore_nets: set[str] | None = None,
    ) -> bool:
        hw = 0.5 * w
        m = self.rules.min_edge_clearance_mm + 0.02
        m0 = 0.02 if self._pt_in_em_pad(x0, y0, net, layer) else m
        m1 = 0.02 if self._pt_in_em_pad(x1, y1, net, layer) else m
        if (
            x0 - hw < self.outline.x0 + m0
            or x0 + hw > self.outline.x1 - m0
            or y0 - hw < self.outline.y0 + m0
            or y0 + hw > self.outline.y1 - m0
            or x1 - hw < self.outline.x0 + m1
            or x1 + hw > self.outline.x1 - m1
            or y1 - hw < self.outline.y0 + m1
            or y1 + hw > self.outline.y1 - m1
        ):
            return False
        for slot in self.air_slots:
            if _dist_seg_to_box(x0, y0, x1, y1, slot) - hw < self.rules.min_slot_clearance_mm + 0.03:
                return False
        for klayers, kbox, no_tracks, _, _ in self.keepout_zones:
            if no_tracks and layer in klayers and _dist_seg_to_box(x0, y0, x1, y1, kbox) - hw < 0.02:
                return False

        sbox = _Box(min(x0, x1) - hw, min(y0, y1) - hw, max(x0, x1) + hw, max(y0, y1) + hw)
        if not self._adj_dielectric_ok(sbox, layer, net):
            return False
        if not self._hv_domain_ok(sbox, layer, net, ignore_nets=ignore_nets):
            return False

        # Normal copper-to-copper clearance scan uses tight local halo only!
        min_clr = self.rules.min_clearance_mm + 0.015
        halo = min_clr + hw + 0.05
        gx0 = int(math.floor((sbox.x0 - halo) / self.cell))
        gx1 = int(math.floor((sbox.x1 + halo) / self.cell))
        gy0 = int(math.floor((sbox.y0 - halo) / self.cell))
        gy1 = int(math.floor((sbox.y1 + halo) / self.cell))

        seen_p: set[int] = set()
        seen_s: set[int] = set()
        seen_v: set[int] = set()
        pgrid = self.pad_grid[layer]
        sgrid = self.seg_grid[layer]
        vgrid = self.via_grid[layer]

        for gx in range(gx0, gx1 + 1):
            for gy in range(gy0, gy1 + 1):
                for pidx in pgrid.get((gx, gy), ()):
                    if pidx in seen_p:
                        continue
                    seen_p.add(pidx)
                    pbox, pnet, _, _, _, _ = self.pad_list[pidx]
                    if pnet == net or (ignore_nets and pnet in ignore_nets):
                        continue
                    if sbox.dist_to_box(pbox) >= min_clr:
                        continue
                    if _dist_seg_to_box(x0, y0, x1, y1, pbox) - hw < min_clr:
                        return False
                for sidx in sgrid.get((gx, gy), ()):
                    if sidx in seen_s:
                        continue
                    seen_s.add(sidx)
                    bx0, by0, bx1, by1, bw, _, bnet = self.seg_list[sidx]
                    if bnet == net or (ignore_nets and bnet in ignore_nets):
                        continue
                    if _dist_seg_to_seg(x0, y0, x1, y1, bx0, by0, bx1, by1) - hw - 0.5 * bw < min_clr:
                        return False
                for vidx in vgrid.get((gx, gy), ()):
                    if vidx in seen_v:
                        continue
                    seen_v.add(vidx)
                    vx, vy, vsize, _, vnet = self.via_list[vidx]
                    if vnet == net or (ignore_nets and vnet in ignore_nets):
                        continue
                    if _dist_point_to_seg(vx, vy, x0, y0, x1, y1) - hw - 0.5 * vsize < min_clr:
                        return False
        return True

    def via_ok(
        self,
        vx: float,
        vy: float,
        vsize: float,
        vlayers: tuple[str, ...],
        net: str,
        ignore_nets: set[str] | None = None,
    ) -> bool:
        vr = 0.5 * vsize
        m = self.rules.min_edge_clearance_mm + 0.02
        if (
            vx - vr < self.outline.x0 + m
            or vx + vr > self.outline.x1 - m
            or vy - vr < self.outline.y0 + m
            or vy + vr > self.outline.y1 - m
        ):
            return False
        for slot in self.air_slots:
            if slot.dist_to_point(vx, vy) - vr < self.rules.min_slot_clearance_mm + 0.03:
                return False
        for klayers, kbox, _, no_vias, _ in self.keepout_zones:
            if no_vias and any(l in klayers for l in vlayers):
                if kbox.dist_to_point(vx, vy) - vr < 0.02:
                    return False

        vbox = _Box(vx - vr, vy - vr, vx + vr, vy + vr)
        min_clr = self.rules.min_clearance_mm + 0.015
        halo = min_clr + vr + 0.05
        gx0 = int(math.floor((vbox.x0 - halo) / self.cell))
        gx1 = int(math.floor((vbox.x1 + halo) / self.cell))
        gy0 = int(math.floor((vbox.y0 - halo) / self.cell))
        gy1 = int(math.floor((vbox.y1 + halo) / self.cell))

        for layer in vlayers:
            if not self._adj_dielectric_ok(vbox, layer, net):
                return False
            if not self._hv_domain_ok(vbox, layer, net, ignore_nets=ignore_nets):
                return False
            seen_p: set[int] = set()
            seen_s: set[int] = set()
            seen_v: set[int] = set()
            pgrid = self.pad_grid[layer]
            sgrid = self.seg_grid[layer]
            vgrid = self.via_grid[layer]
            for gx in range(gx0, gx1 + 1):
                for gy in range(gy0, gy1 + 1):
                    for pidx in pgrid.get((gx, gy), ()):
                        if pidx in seen_p:
                            continue
                        seen_p.add(pidx)
                        pbox, pnet, _, _, _, _ = self.pad_list[pidx]
                        if pnet == net or (ignore_nets and pnet in ignore_nets):
                            continue
                        if pbox.dist_to_point(vx, vy) - vr < min_clr:
                            return False
                    for sidx in sgrid.get((gx, gy), ()):
                        if sidx in seen_s:
                            continue
                        seen_s.add(sidx)
                        sx0, sy0, sx1, sy1, sw, _, snet = self.seg_list[sidx]
                        if snet == net or (ignore_nets and snet in ignore_nets):
                            continue
                        if _dist_point_to_seg(vx, vy, sx0, sy0, sx1, sy1) - vr - 0.5 * sw < min_clr:
                            return False
                    for vidx in vgrid.get((gx, gy), ()):
                        if vidx in seen_v:
                            continue
                        seen_v.add(vidx)
                        vx2, vy2, vsize2, _, vnet2 = self.via_list[vidx]
                        if vnet2 == net or (ignore_nets and vnet2 in ignore_nets):
                            continue
                        if math.hypot(vx - vx2, vy - vy2) - vr - 0.5 * vsize2 < min_clr:
                            return False
        return True


def _offset_ortho_polyline(
    center_pts: Sequence[tuple[float, float]],
    half_pitch: float,
    flip: bool = False,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Offset an orthogonal center-line polyline into exact parallel P/N rails at ±half_pitch.

    At every orthogonal corner C_i between perpendicular segments d_{i-1} and d_i with left
    unit normals n_{i-1} and n_i, the exact mitered rail corner is C_i ± h*(n_{i-1} + n_i),
    guaranteeing constant edge-to-edge gap along 100% of every segment with zero crossings.
    """
    pts = list(_simplify_polyline(center_pts))
    if len(pts) < 2:
        return [], []
    h = -half_pitch if flip else half_pitch
    normals: list[tuple[float, float]] = []
    for i in range(len(pts) - 1):
        dx = pts[i + 1][0] - pts[i][0]
        dy = pts[i + 1][1] - pts[i][1]
        L = math.hypot(dx, dy)
        if L <= 1e-9:
            normals.append((0.0, 1.0))
        else:
            normals.append((-dy / L, dx / L))
    p_rail: list[tuple[float, float]] = []
    n_rail: list[tuple[float, float]] = []
    # Start point
    n0 = normals[0]
    p_rail.append((round(pts[0][0] + h * n0[0], 4), round(pts[0][1] + h * n0[1], 4)))
    n_rail.append((round(pts[0][0] - h * n0[0], 4), round(pts[0][1] - h * n0[1], 4)))
    # Interior orthogonal corners
    for i in range(1, len(pts) - 1):
        nx = normals[i - 1][0] + normals[i][0]
        ny = normals[i - 1][1] + normals[i][1]
        p_rail.append((round(pts[i][0] + h * nx, 4), round(pts[i][1] + h * ny, 4)))
        n_rail.append((round(pts[i][0] - h * nx, 4), round(pts[i][1] - h * ny, 4)))
    # End point
    ne = normals[-1]
    p_rail.append((round(pts[-1][0] + h * ne[0], 4), round(pts[-1][1] + h * ne[1], 4)))
    n_rail.append((round(pts[-1][0] - h * ne[0], 4), round(pts[-1][1] - h * ne[1], 4)))
    return p_rail, n_rail


def _auto_route_once(
    board_spec: BoardSpec,
    *,
    grid_mm: float,
    default_trace_width_mm: float,
    via_diameter_mm: float,
    via_drill_mm: float,
    preserve_existing: bool,
    route_power_via_zones: bool,
    priority_boost: set[str],
) -> tuple[BoardSpec, set[str]]:
    rules = board_spec.rules
    v_drill = max(via_drill_mm, rules.min_via_drill_mm)
    v_diam = max(via_diameter_mm, round(v_drill + 2.0 * rules.min_annular_ring_mm + 0.01, 4))
    # Compact BGA/QFN dogbone escape via obeying DesignRules (e.g. 0.405/0.20 mm fits 1.0 mm BGA!)
    v_drill_esc = rules.min_via_drill_mm
    v_diam_esc = min(v_diam, round(v_drill_esc + 2.0 * rules.min_annular_ring_mm + 0.005, 4))
    base_w = max(default_trace_width_mm, rules.min_trace_width_mm + 0.02)

    space = _RouteSpace(board_spec)
    all_cu = space.cu_layers
    zone_layers = {z.layer for z in board_spec.zones if not z.is_keepout}
    route_layers: list[str] = []
    for l in all_cu:
        if l in ("F.Cu", "B.Cu") or l not in zone_layers:
            route_layers.append(l)
    if not route_layers:
        route_layers = list(all_cu)
    thru_layers = (all_cu[0], all_cu[-1])
    thru_span = tuple(all_cu)

    net_map: dict[str, NetSpec] = {ns.name: ns for ns in board_spec.nets}
    layer_diel: dict[str, tuple[str, float, float, float]] = {
        l: _stackup_layer_dielectric(board_spec.stackup, l) for l in all_cu
    }

    def trace_width_for(nname: str, layer: str) -> float:
        ns = net_map.get(nname)
        if ns is None or ns.target_z0_ohm is None:
            return round(base_w, 4)
        mode, hb, t_cu, er = layer_diel[layer]
        if ns.diff_pair_with:
            s_gap = max(0.20, rules.min_clearance_mm + 0.05)
            w_d = (
                solve_diff_microstrip_width_mm(ns.target_z0_ohm, s_gap, hb, t_cu, er)
                if mode == "microstrip"
                else solve_diff_stripline_width_mm(ns.target_z0_ohm, s_gap, hb, t_cu, er)
            )
            return round(max(w_d, rules.min_trace_width_mm), 4)
        w_se = (
            solve_microstrip_width_mm(ns.target_z0_ohm, hb, t_cu, er)
            if mode == "microstrip"
            else solve_stripline_width_mm(ns.target_z0_ohm, hb, t_cu, er)
        )
        return round(max(w_se, rules.min_trace_width_mm), 4)

    out_traces: list[TraceSpec] = []
    out_vias: list[ViaSpec] = []

    def commit_trace(tr: TraceSpec) -> None:
        pts = _simplify_polyline(tr.points_mm)
        if len(pts) < 2:
            return
        tr_clean = TraceSpec(
            net=tr.net,
            layer=tr.layer,
            points_mm=pts,
            width_mm=round(tr.width_mm, 4),
            is_guard_ring=tr.is_guard_ring,
            diff_spacing_mm=tr.diff_spacing_mm,
        )
        out_traces.append(tr_clean)
        for i in range(len(pts) - 1):
            space.add_segment(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], tr_clean.width_mm, tr_clean.layer, tr_clean.net)

    def commit_via(v: ViaSpec) -> None:
        out_vias.append(v)
        i0 = all_cu.index(v.layers[0]) if v.layers[0] in all_cu else 0
        i1 = all_cu.index(v.layers[1]) if v.layers[1] in all_cu else len(all_cu) - 1
        span = tuple(all_cu[min(i0, i1): max(i0, i1) + 1])
        space.add_via(v.x_mm, v.y_mm, v.diameter_mm, span, v.net)

    # Phase 1: Preserve guard rings & (optionally) valid non-conflicting existing traces/vias
    for v in board_spec.vias:
        if preserve_existing or any(tr.is_guard_ring and tr.net == v.net for tr in board_spec.traces):
            i0 = all_cu.index(v.layers[0]) if v.layers[0] in all_cu else 0
            i1 = all_cu.index(v.layers[1]) if v.layers[1] in all_cu else len(all_cu) - 1
            span = tuple(all_cu[min(i0, i1): max(i0, i1) + 1])
            if space.via_ok(v.x_mm, v.y_mm, v.diameter_mm, span, v.net):
                commit_via(v)

    for tr in board_spec.traces:
        if tr.is_guard_ring or preserve_existing:
            ok_all = True
            for i in range(len(tr.points_mm) - 1):
                x0, y0 = tr.points_mm[i]
                x1, y1 = tr.points_mm[i + 1]
                if math.hypot(x1 - x0, y1 - y0) > 1e-5:
                    if not space.segment_ok(x0, y0, x1, y1, tr.width_mm, tr.layer, tr.net):
                        ok_all = False
                        break
            if ok_all:
                commit_trace(tr)

    # Helper: compute Union-Find islands of a net across all its pads, committed segs, vias, zones
    def _net_islands(nname: str) -> tuple[
        list[list[tuple[float, float, tuple[str, ...], tuple[float, float], bool]]],
        int,
    ]:
        npads = [(pbox, players, ccenter) for pbox, pnet, players, _, _, ccenter in space.pad_list if pnet == nname]
        nsegs = [(x0, y0, x1, y1, w, sl) for x0, y0, x1, y1, w, sl, snet in space.seg_list if snet == nname]
        nvias = [(vx, vy, vsize, vlayers) for vx, vy, vsize, vlayers, vnet in space.via_list if vnet == nname]
        nzones = space.zones_by_net.get(nname, [])
        n_p, n_s, n_v, n_z = len(npads), len(nsegs), len(nvias), len(nzones)
        off_s, off_v, off_z = n_p, n_p + n_s, n_p + n_s + n_v
        uf = list(range(off_z + n_z))
        tol = 0.015

        def find(i: int) -> int:
            while uf[i] != i:
                uf[i] = uf[uf[i]]
                i = uf[i]
            return i

        def union(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                uf[ri] = rj

        for i in range(n_p):
            bi, li, _ = npads[i]
            ls = set(li)
            for j in range(i + 1, n_p):
                if ls.intersection(npads[j][1]) and bi.dist_to_box(npads[j][0]) <= tol:
                    union(i, j)
        for i, (pbox, players, _) in enumerate(npads):
            ps = set(players)
            pcx, pcy = pbox.center
            for j, (x0, y0, x1, y1, w, sl) in enumerate(nsegs):
                if sl in ps and _dist_seg_to_box(x0, y0, x1, y1, pbox) <= 0.5 * w + tol:
                    union(i, off_s + j)
            for k, (vx, vy, vsize, vl) in enumerate(nvias):
                if ps.intersection(vl) and pbox.dist_to_point(vx, vy) <= 0.5 * vsize + tol:
                    union(i, off_v + k)
            for m, (zl, zbox, zpoly) in enumerate(nzones):
                if zl in ps and pbox.dist_to_box(zbox) <= tol:
                    if _point_in_zone_copper(pcx, pcy, zpoly, zl, space.keepout_zones, space.air_slots, tol=tol):
                        union(i, off_z + m)
        for j, (ax0, ay0, ax1, ay1, aw, al) in enumerate(nsegs):
            for j2 in range(j + 1, n_s):
                bx0, by0, bx1, by1, bw, bl = nsegs[j2]
                if al == bl and _dist_seg_to_seg(ax0, ay0, ax1, ay1, bx0, by0, bx1, by1) <= 0.5 * (aw + bw) + tol:
                    union(off_s + j, off_s + j2)
            for k, (vx, vy, vsize, vl) in enumerate(nvias):
                if al in vl and _dist_point_to_seg(vx, vy, ax0, ay0, ax1, ay1) <= 0.5 * vsize + 0.5 * aw + tol:
                    union(off_s + j, off_v + k)
            for m, (zl, zbox, zpoly) in enumerate(nzones):
                if al == zl and _dist_seg_to_box(ax0, ay0, ax1, ay1, zbox) <= 0.5 * aw + tol:
                    mx, my = 0.5 * (ax0 + ax1), 0.5 * (ay0 + ay1)
                    if (
                        _point_in_zone_copper(ax0, ay0, zpoly, zl, space.keepout_zones, space.air_slots, tol=tol)
                        or _point_in_zone_copper(ax1, ay1, zpoly, zl, space.keepout_zones, space.air_slots, tol=tol)
                        or _point_in_zone_copper(mx, my, zpoly, zl, space.keepout_zones, space.air_slots, tol=tol)
                    ):
                        union(off_s + j, off_z + m)
        for k, (vx, vy, vsize, vl) in enumerate(nvias):
            vs = set(vl)
            for k2 in range(k + 1, n_v):
                vx2, vy2, vsize2, vl2 = nvias[k2]
                if vs.intersection(vl2) and math.hypot(vx - vx2, vy - vy2) <= 0.5 * (vsize + vsize2) + tol:
                    union(off_v + k, off_v + k2)
            for m, (zl, zbox, zpoly) in enumerate(nzones):
                if zl in vs and zbox.dist_to_point(vx, vy) <= 0.5 * vsize + tol:
                    if _point_in_zone_copper(vx, vy, zpoly, zl, space.keepout_zones, space.air_slots, tol=0.5 * vsize + tol):
                        union(off_v + k, off_z + m)
        for m in range(n_z):
            for m2 in range(m + 1, n_z):
                if nzones[m][0] == nzones[m2][0] and nzones[m][1].dist_to_box(nzones[m2][1]) <= tol:
                    union(off_z + m, off_z + m2)

        groups: dict[int, list[tuple[float, float, tuple[str, ...], tuple[float, float], bool]]] = defaultdict(list)
        pad_roots: set[int] = set()
        for i, (pbox, players, ccenter) in enumerate(npads):
            r = find(i)
            pad_roots.add(r)
            cx, cy = pbox.center
            groups[r].append((round(cx, 4), round(cy, 4), players, ccenter, True))
        for k, (vx, vy, _, vl) in enumerate(nvias):
            r = find(off_v + k)
            groups[r].append((round(vx, 4), round(vy, 4), vl, (vx, vy), False))
        # Add clean perimeter-interior access points for any zone belonging to a pad island!
        for m, (zl, zbox, zpoly) in enumerate(nzones):
            r = find(off_z + m)
            if r not in pad_roots:
                continue
            # Sample clean perimeter points inset 1.0 mm inside zbox
            zx0, zx1 = zbox.x0 + 1.0, zbox.x1 - 1.0
            zy0, zy1 = zbox.y0 + 1.0, zbox.y1 - 1.0
            if zx1 > zx0 and zy1 > zy0:
                samples: list[tuple[float, float]] = []
                for frac in (0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95):
                    samples.append((round(zx0 + frac * (zx1 - zx0), 2), round(zy0, 2)))
                    samples.append((round(zx0 + frac * (zx1 - zx0), 2), round(zy1, 2)))
                    samples.append((round(zx0, 2), round(zy0 + frac * (zy1 - zy0), 2)))
                    samples.append((round(zx1, 2), round(zy0 + frac * (zy1 - zy0), 2)))
                for sx, sy in samples:
                    if (
                        _point_in_zone_copper(sx, sy, zpoly, zl, space.keepout_zones, space.air_slots, tol=-0.10)
                        and space.via_ok(sx, sy, v_diam, thru_span, nname)
                    ):
                        groups[r].append((sx, sy, (zl,), (sx, sy), False))
        for j, (ax0, ay0, ax1, ay1, _, al) in enumerate(nsegs):
            r = find(off_s + j)
            if r not in pad_roots:
                groups[r].append((round(ax0, 4), round(ay0, 4), (al,), (ax0, ay0), False))
        active_roots = sorted(groups.keys())
        return [groups[r] for r in active_roots], len(pad_roots)

    # Phase 2: Power & Ground SMD Pad Via-to-Zone Fanout (incl. 45° BGA diagonal dogbone vias!)
    if route_power_via_zones:
        compass_dirs = [
            (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
            (0.7071, 0.7071), (-0.7071, 0.7071), (0.7071, -0.7071), (-0.7071, -0.7071),
        ]
        bga_diags = [
            (0.60, 0.60), (-0.60, 0.60), (0.60, -0.60), (-0.60, -0.60),
            (0.50, 0.50), (-0.50, 0.50), (0.50, -0.50), (-0.50, -0.50),
            (0.635, 0.635), (-0.635, 0.635), (0.635, -0.635), (-0.635, -0.635),
        ]
        for znet, zlist in sorted(space.zones_by_net.items()):
            w_p = trace_width_for(znet, "F.Cu")
            for pbox, pnet, players, _, _, ccenter in space.pad_list:
                if pnet != znet:
                    continue
                px, py = pbox.center
                direct = False
                for zl, zbox, zpoly in zlist:
                    if zl in players and zbox.dist_to_point(px, py) <= 0.015:
                        if _point_in_zone_copper(px, py, zpoly, zl, space.keepout_zones, space.air_slots):
                            direct = True
                            break
                if direct:
                    continue
                pad_layer = players[0]
                odx, ody = px - ccenter[0], py - ccenter[1]
                onorm = math.hypot(odx, ody)
                ordered_dirs = list(compass_dirs)
                ordered_bga = list(bga_diags)
                if onorm > 1e-4:
                    ux, uy = odx / onorm, ody / onorm
                    ordered_dirs.sort(key=lambda d: -(d[0] * ux + d[1] * uy))
                    ordered_bga.sort(key=lambda d: -(d[0] * ux + d[1] * uy))
                # Candidate: (vx, vy, vd, vdr)
                candidates: list[tuple[float, float, float, float]] = [(round(px, 4), round(py, 4), v_diam, v_drill)]
                for dx, dy in ordered_bga:
                    candidates.append((round(px + dx, 4), round(py + dy, 4), v_diam_esc, v_drill_esc))
                for rad in (0.65, 1.0, 1.4, 1.9, 2.5, 3.2, 4.0):
                    for dx, dy in ordered_dirs:
                        candidates.append((round(px + rad * dx, 4), round(py + rad * dy, 4), v_diam_esc, v_drill_esc))
                for vx, vy, vd, vdr in candidates:
                    in_zone = False
                    for zl, zbox, zpoly in zlist:
                        if zbox.dist_to_point(vx, vy) <= 0.01:
                            if _point_in_zone_copper(vx, vy, zpoly, zl, space.keepout_zones, space.air_slots, tol=-0.10):
                                in_zone = True
                                break
                    if not in_zone:
                        continue
                    if not space.via_ok(vx, vy, vd, thru_span, znet):
                        continue
                    if math.hypot(vx - px, vy - py) > 0.01:
                        if not space.segment_ok(px, py, vx, vy, w_p, pad_layer, znet):
                            continue
                        commit_trace(TraceSpec(znet, pad_layer, ((px, py), (vx, vy)), w_p))
                    commit_via(ViaSpec(znet, vx, vy, diameter_mm=vd, drill_mm=vdr, layers=thru_layers))
                    break

    # Helper: try direct 1-seg / L-shape / Z-shape connection on a shared routing layer
    def _try_direct(
        nname: str,
        t0: tuple[float, float, tuple[str, ...], tuple[float, float], bool],
        t1: tuple[float, float, tuple[str, ...], tuple[float, float], bool],
    ) -> bool:
        x0, y0, l0, _, _ = t0
        x1, y1, l1, _, _ = t1
        shared = [l for l in route_layers if l in l0 and l in l1]
        for layer in shared:
            w = trace_width_for(nname, layer)
            cand_paths: list[list[tuple[float, float]]] = []
            if abs(x0 - x1) < 1e-4 or abs(y0 - y1) < 1e-4:
                cand_paths.append([(x0, y0), (x1, y1)])
            else:
                cand_paths.append([(x0, y0), (x1, y0), (x1, y1)])
                cand_paths.append([(x0, y0), (x0, y1), (x1, y1)])
                mx = round(0.5 * (x0 + x1), 4)
                my = round(0.5 * (y0 + y1), 4)
                cand_paths.append([(x0, y0), (mx, y0), (mx, y1), (x1, y1)])
                cand_paths.append([(x0, y0), (x0, my), (x1, my), (x1, y1)])
            for pts in cand_paths:
                ok = True
                for i in range(len(pts) - 1):
                    if not space.segment_ok(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], w, layer, nname):
                        ok = False
                        break
                if ok:
                    commit_trace(TraceSpec(nname, layer, tuple(pts), w))
                    return True
        return False

    # Helper: generate grid-aligned escape stubs (incl. 45° BGA dogbone & staggered pin-axis via-drops!)
    # Escape record: (li, gx, gy, pad_stub, pad_layer, via_xy, post_via_stub_on_li)
    def _escape_nodes(
        nname: str,
        term: tuple[float, float, tuple[str, ...], tuple[float, float], bool],
        g: float,
    ) -> list[tuple[int, int, int, list[tuple[float, float]], str, tuple[float, float] | None, list[tuple[float, float]]]]:
        px, py, layers, ccenter, _ = term
        nx_max = int(math.floor(board_spec.width_mm / g))
        ny_max = int(math.floor(board_spec.height_mm / g))
        out: list[tuple[int, int, int, list[tuple[float, float]], str, tuple[float, float] | None, list[tuple[float, float]]]] = []
        seen_state: set[tuple[int, int, int]] = set()

        # Special case: internal zone-access point (layers == (zone_layer,) not in route_layers)
        if len(layers) == 1 and layers[0] not in route_layers:
            if space.via_ok(px, py, v_diam_esc, thru_span, nname):
                gx = max(1, min(nx_max - 1, int(round(px / g))))
                gy = max(1, min(ny_max - 1, int(round(py / g))))
                tx, ty = round(gx * g, 4), round(gy * g, 4)
                for li_r, l_r in enumerate(route_layers):
                    w_r = trace_width_for(nname, l_r)
                    pstub = list(_simplify_polyline([(px, py), (tx, py), (tx, ty)]))
                    if len(pstub) == 1 or all(
                        space.segment_ok(pstub[k][0], pstub[k][1], pstub[k + 1][0], pstub[k + 1][1], w_r, l_r, nname)
                        for k in range(len(pstub) - 1)
                    ):
                        seen_state.add((li_r, gx, gy))
                        out.append((li_r, gx, gy, [], layers[0], (px, py), pstub))
            return out

        odx, ody = px - ccenter[0], py - ccenter[1]
        if abs(odx) >= abs(ody):
            primary_axes = [((1.0 if odx >= 0 else -1.0), 0.0), (0.0, 1.0), (0.0, -1.0), ((-1.0 if odx >= 0 else 1.0), 0.0)]
        else:
            primary_axes = [(0.0, (1.0 if ody >= 0 else -1.0)), (1.0, 0.0), (-1.0, 0.0), (0.0, (-1.0 if ody >= 0 else 1.0))]

        avail_layers = [l for l in route_layers if l in layers]
        if not avail_layers:
            avail_layers = [layers[0]]

        # 1) Direct snap on each available pad layer (zero via)
        for pl in avail_layers:
            if pl not in route_layers:
                continue
            li = route_layers.index(pl)
            w = trace_width_for(nname, pl)
            bx, by = int(round(px / g)), int(round(py / g))
            for r in (0, 1, 2):
                for dx in range(-r, r + 1):
                    for dy in range(-r, r + 1):
                        if r > 0 and max(abs(dx), abs(dy)) != r:
                            continue
                        gx, gy = bx + dx, by + dy
                        if not (1 <= gx < nx_max and 1 <= gy < ny_max):
                            continue
                        if (li, gx, gy) in seen_state:
                            continue
                        tx, ty = round(gx * g, 4), round(gy * g, 4)
                        for stub in ([(px, py), (tx, py), (tx, ty)], [(px, py), (px, ty), (tx, ty)]):
                            s_clean = list(_simplify_polyline(stub))
                            if len(s_clean) == 1:
                                seen_state.add((li, gx, gy))
                                out.append((li, gx, gy, [(px, py)], pl, None, []))
                                break
                            if all(space.segment_ok(s_clean[k][0], s_clean[k][1], s_clean[k + 1][0], s_clean[k + 1][1], w, pl, nname) for k in range(len(s_clean) - 1)):
                                seen_state.add((li, gx, gy))
                                out.append((li, gx, gy, s_clean, pl, None, []))
                                break
                if len(out) >= 4:
                    break

        pl0 = avail_layers[0]
        w0 = trace_width_for(nname, pl0)

        # 1b) 45° BGA/FMC diagonal dogbone via-drop (1.20 mm, 1.00 mm & 1.27 mm grid pitches!)
        bga_offsets = [
            (0.60, 0.60), (-0.60, 0.60), (0.60, -0.60), (-0.60, -0.60),
            (0.50, 0.50), (-0.50, 0.50), (0.50, -0.50), (-0.50, -0.50),
            (0.635, 0.635), (-0.635, 0.635), (0.635, -0.635), (-0.635, -0.635),
        ]
        if abs(odx) + abs(ody) > 1e-4:
            bga_offsets.sort(key=lambda d: -(d[0] * odx + d[1] * ody))
        for ddx, ddy in bga_offsets:
            ex, ey = round(px + ddx, 4), round(py + ddy, 4)
            if not space.via_ok(ex, ey, v_diam_esc, thru_span, nname):
                continue
            if not space.segment_ok(px, py, ex, ey, w0, pl0, nname):
                continue
            gx = max(1, min(nx_max - 1, int(round(ex / g))))
            gy = max(1, min(ny_max - 1, int(round(ey / g))))
            tx, ty = round(gx * g, 4), round(gy * g, 4)
            dogbone_stub = [(px, py), (ex, ey)]
            for li_alt, l_alt in enumerate(route_layers):
                if l_alt == pl0:
                    continue
                w_alt = trace_width_for(nname, l_alt)
                for pstub_raw in ([(ex, ey), (tx, ey), (tx, ty)], [(ex, ey), (ex, ty), (tx, ty)]):
                    pstub = list(_simplify_polyline(pstub_raw))
                    if len(pstub) == 1 or all(
                        space.segment_ok(pstub[k][0], pstub[k][1], pstub[k + 1][0], pstub[k + 1][1], w_alt, l_alt, nname)
                        for k in range(len(pstub) - 1)
                    ):
                        if (li_alt, gx, gy) not in seen_state:
                            seen_state.add((li_alt, gx, gy))
                            out.append((li_alt, gx, gy, dogbone_stub, pl0, (ex, ey), pstub))
                        break
            if len(out) >= 12:
                break

        # 2) Staggered outward pin-axis dogbone fanout (ZERO sideways shift on pad layer before via drop!)
        for ux, uy in primary_axes:
            for dist in (0.9, 1.4, 2.0, 2.7, 3.5, 4.5, 5.6, 7.0):
                ex = round(px + dist * ux, 4)
                ey = round(py + dist * uy, 4)
                if not space.segment_ok(px, py, ex, ey, w0, pl0, nname):
                    continue
                gx = max(1, min(nx_max - 1, int(round(ex / g))))
                gy = max(1, min(ny_max - 1, int(round(ey / g))))
                tx, ty = round(gx * g, 4), round(gy * g, 4)

                # (2a) Direct via drop RIGHT AT (ex, ey) — never shifts sideways into sibling QFN/TSSOP pins!
                if space.via_ok(ex, ey, v_diam_esc, thru_span, nname):
                    dogbone_stub = [(px, py), (ex, ey)]
                    for li_alt, l_alt in enumerate(route_layers):
                        if l_alt == pl0:
                            continue
                        w_alt = trace_width_for(nname, l_alt)
                        for pstub_raw in ([(ex, ey), (tx, ey), (tx, ty)], [(ex, ey), (ex, ty), (tx, ty)]):
                            pstub = list(_simplify_polyline(pstub_raw))
                            if len(pstub) == 1 or all(
                                space.segment_ok(pstub[k][0], pstub[k][1], pstub[k + 1][0], pstub[k + 1][1], w_alt, l_alt, nname)
                                for k in range(len(pstub) - 1)
                            ):
                                if (li_alt, gx, gy) not in seen_state:
                                    seen_state.add((li_alt, gx, gy))
                                    out.append((li_alt, gx, gy, dogbone_stub, pl0, (ex, ey), pstub))
                                break

                # (2b) Same-layer snap onto grid on pl0
                if pl0 in route_layers:
                    li0 = route_layers.index(pl0)
                    if (li0, gx, gy) not in seen_state:
                        for stub_raw in ([(px, py), (ex, ey), (tx, ey), (tx, ty)], [(px, py), (ex, ey), (ex, ty), (tx, ty)]):
                            stub = list(_simplify_polyline(stub_raw))
                            if all(
                                space.segment_ok(stub[k][0], stub[k][1], stub[k + 1][0], stub[k + 1][1], w0, pl0, nname)
                                for k in range(len(stub) - 1)
                            ):
                                seen_state.add((li0, gx, gy))
                                out.append((li0, gx, gy, stub, pl0, None, []))
                                break
                if len(out) >= 24:
                    return out
        return out

    # Helper: weighted multi-layer lazy-oracle A* between two islands
    def _astar_connect(
        nname: str,
        island_a: list[tuple[float, float, tuple[str, ...], tuple[float, float], bool]],
        island_b: list[tuple[float, float, tuple[str, ...], tuple[float, float], bool]],
        g: float,
        max_expansions: int = 20000,
        heuristic_weight: float = 1.4,
    ) -> bool:
        pairs: list[tuple[float, int, int]] = []
        for ia, ta in enumerate(island_a):
            for ib, tb in enumerate(island_b):
                pairs.append((math.hypot(ta[0] - tb[0], ta[1] - tb[1]), ia, ib))
        pairs.sort(key=lambda t: t[0])

        for _, ia, ib in pairs[:6]:
            if _try_direct(nname, island_a[ia], island_b[ib]):
                return True

        used_a: list[int] = []
        used_b: list[int] = []
        for _, ia, ib in pairs:
            if ia not in used_a and len(used_a) < 6:
                used_a.append(ia)
            if ib not in used_b and len(used_b) < 6:
                used_b.append(ib)
            if len(used_a) >= 6 and len(used_b) >= 6:
                break

        starts: dict[tuple[int, int, int], tuple[list[tuple[float, float]], str, tuple[float, float] | None, list[tuple[float, float]]]] = {}
        goals: dict[tuple[int, int, int], tuple[list[tuple[float, float]], str, tuple[float, float] | None, list[tuple[float, float]]]] = {}
        for ia in used_a:
            for li, gx, gy, stub, pl, vxy, pstub in _escape_nodes(nname, island_a[ia], g):
                starts.setdefault((li, gx, gy), (stub, pl, vxy, pstub))
        for ib in used_b:
            for li, gx, gy, stub, pl, vxy, pstub in _escape_nodes(nname, island_b[ib], g):
                goals.setdefault((li, gx, gy), (stub, pl, vxy, pstub))
        if not starts or not goals:
            return False

        goal_pts = [(gx, gy) for _, gx, gy in goals.keys()]

        def h_fn(gx: int, gy: int) -> float:
            return min(abs(gx - tx) + abs(gy - ty) for tx, ty in goal_pts)

        nx_max = int(math.floor(board_spec.width_mm / g))
        ny_max = int(math.floor(board_spec.height_mm / g))
        n_layers = len(route_layers)
        layer_w = [trace_width_for(nname, l) for l in route_layers]

        edge_cache: dict[tuple[int, int, int, int, int], bool] = {}
        via_cache: dict[tuple[int, int], bool] = {}

        def edge_clear(li: int, x0i: int, y0i: int, x1i: int, y1i: int) -> bool:
            key = (li, x0i, y0i, x1i, y1i) if (x0i, y0i) <= (x1i, y1i) else (li, x1i, y1i, x0i, y0i)
            res = edge_cache.get(key)
            if res is None:
                res = space.segment_ok(
                    round(x0i * g, 4), round(y0i * g, 4),
                    round(x1i * g, 4), round(y1i * g, 4),
                    layer_w[li], route_layers[li], nname,
                )
                edge_cache[key] = res
            return res

        def via_clear(gxi: int, gyi: int) -> bool:
            key = (gxi, gyi)
            res = via_cache.get(key)
            if res is None:
                res = space.via_ok(round(gxi * g, 4), round(gyi * g, 4), v_diam, thru_span, nname)
                via_cache[key] = res
            return res

        heap: list[tuple[float, float, int, int, int, int]] = []
        g_cost: dict[tuple[int, int, int], float] = {}
        came_from: dict[tuple[int, int, int], tuple[int, int, int] | None] = {}
        for (li, gx, gy), (_, _, vxy, _) in starts.items():
            c0 = 2.0 if vxy is not None else 0.0
            st = (li, gx, gy)
            if c0 < g_cost.get(st, 1e18):
                g_cost[st] = c0
                came_from[st] = None
                heapq.heappush(heap, (c0 + heuristic_weight * h_fn(gx, gy), c0, li, gx, gy, 0))

        found_goal: tuple[int, int, int] | None = None
        expansions = 0
        while heap and expansions < max_expansions:
            _, cur_g, li, gx, gy, pdir = heapq.heappop(heap)
            st = (li, gx, gy)
            if cur_g > g_cost.get(st, 1e18) + 1e-9:
                continue
            if st in goals:
                found_goal = st
                break
            expansions += 1

            h_step = 1.0 if (li % 2 == 0) else 1.25
            v_step = 1.25 if (li % 2 == 0) else 1.0
            for dx, dy, ndir, scost in ((1, 0, 1, h_step), (-1, 0, 1, h_step), (0, 1, 2, v_step), (0, -1, 2, v_step)):
                nx, ny = gx + dx, gy + dy
                if not (1 <= nx < nx_max and 1 <= ny < ny_max):
                    continue
                nst = (li, nx, ny)
                bend = 0.25 if (pdir != 0 and pdir != ndir) else 0.0
                ng = cur_g + scost + bend
                if ng >= g_cost.get(nst, 1e18):
                    continue
                if not edge_clear(li, gx, gy, nx, ny):
                    continue
                g_cost[nst] = ng
                came_from[nst] = st
                heapq.heappush(heap, (ng + heuristic_weight * h_fn(nx, ny), ng, li, nx, ny, ndir))

            if n_layers > 1 and via_clear(gx, gy):
                for li2 in range(n_layers):
                    if li2 == li:
                        continue
                    nst = (li2, gx, gy)
                    ng = cur_g + 5.0
                    if ng < g_cost.get(nst, 1e18):
                        g_cost[nst] = ng
                        came_from[nst] = st
                        heapq.heappush(heap, (ng + heuristic_weight * h_fn(gx, gy), ng, li2, gx, gy, 0))

        if found_goal is None:
            return False

        path_states: list[tuple[int, int, int]] = []
        cur: tuple[int, int, int] | None = found_goal
        while cur is not None:
            path_states.append(cur)
            cur = came_from[cur]
        path_states.reverse()

        # Commit start escape stub + via + post-via grid snap
        st_li = path_states[0][0]
        st_stub, st_pl, st_vxy, st_pstub = starts[path_states[0]]
        if len(st_stub) >= 2:
            commit_trace(TraceSpec(nname, st_pl, tuple(st_stub), trace_width_for(nname, st_pl)))
        if st_vxy is not None:
            commit_via(ViaSpec(nname, st_vxy[0], st_vxy[1], diameter_mm=v_diam_esc, drill_mm=v_drill_esc, layers=thru_layers))
        if len(st_pstub) >= 2:
            commit_trace(TraceSpec(nname, route_layers[st_li], tuple(st_pstub), layer_w[st_li]))

        # Commit A* grid segments & intermediate layer-change vias
        seg_pts: list[tuple[float, float]] = [(round(path_states[0][1] * g, 4), round(path_states[0][2] * g, 4))]
        cur_li = st_li
        for k in range(1, len(path_states)):
            li_k, gx_k, gy_k = path_states[k]
            pt_k = (round(gx_k * g, 4), round(gy_k * g, 4))
            if li_k != cur_li:
                if len(seg_pts) >= 2:
                    commit_trace(TraceSpec(nname, route_layers[cur_li], tuple(seg_pts), layer_w[cur_li]))
                commit_via(ViaSpec(nname, pt_k[0], pt_k[1], diameter_mm=v_diam, drill_mm=v_drill, layers=thru_layers))
                cur_li = li_k
                seg_pts = [pt_k]
            else:
                seg_pts.append(pt_k)
        if len(seg_pts) >= 2:
            commit_trace(TraceSpec(nname, route_layers[cur_li], tuple(seg_pts), layer_w[cur_li]))

        # Commit goal post-via snap + via + pad escape stub
        gl_li = found_goal[0]
        gl_stub, gl_pl, gl_vxy, gl_pstub = goals[found_goal]
        if len(gl_pstub) >= 2:
            commit_trace(TraceSpec(nname, route_layers[gl_li], tuple(reversed(gl_pstub)), layer_w[gl_li]))
        if gl_vxy is not None:
            commit_via(ViaSpec(nname, gl_vxy[0], gl_vxy[1], diameter_mm=v_diam_esc, drill_mm=v_drill_esc, layers=thru_layers))
        if len(gl_stub) >= 2:
            commit_trace(TraceSpec(nname, gl_pl, tuple(reversed(gl_stub)), trace_width_for(nname, gl_pl)))
        return True

    # Phase 3A: Coupled Differential Pair Routing (100 Ohm LVDS/DDR4/ETH pairs)
    # Supports direct coupled L/Z trunks + coupled center-line A* + BGA/SMD pair dogbone vias!
    def _pair_escape_end(
        pname: str,
        nname: str,
        ppad: tuple[float, float],
        players: tuple[str, ...],
        pcc: tuple[float, float],
        npad: tuple[float, float],
        nlayers: tuple[str, ...],
        ncc: tuple[float, float],
        layer: str,
        w_d: float,
    ) -> list[tuple[tuple[float, float], tuple[float, float], list[TraceSpec], list[ViaSpec]]]:
        """Return candidate (p_anchor, n_anchor, breakout_traces, breakout_vias) on ``layer``."""
        cands: list[tuple[tuple[float, float], tuple[float, float], list[TraceSpec], list[ViaSpec]]] = []
        if layer in players and layer in nlayers:
            cands.append((ppad, npad, [], []))
        else:
            # Drop a pair of compact BGA/SMD dogbone vias onto ``layer``
            pl_e, nl_e = players[0], nlayers[0]
            w_p = trace_width_for(pname, pl_e)
            w_n = trace_width_for(nname, nl_e)
            odx = 0.5 * (ppad[0] + npad[0]) - 0.5 * (pcc[0] + ncc[0])
            ody = 0.5 * (ppad[1] + npad[1]) - 0.5 * (pcc[1] + ncc[1])
            offsets = [
                (0.0, 0.0),
                (0.60, 0.60), (0.60, -0.60), (-0.60, 0.60), (-0.60, -0.60),
                (0.50, 0.50), (0.50, -0.50), (-0.50, 0.50), (-0.50, -0.50),
                (0.635, 0.635), (0.635, -0.635), (-0.635, 0.635), (-0.635, -0.635),
                (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
                (1.6, 0.0), (-1.6, 0.0), (0.0, 1.6), (0.0, -1.6),
            ]
            if abs(odx) + abs(ody) > 1e-4:
                offsets = [offsets[0]] + sorted(offsets[1:], key=lambda d: -(d[0] * odx + d[1] * ody))
            p_vias: list[tuple[tuple[float, float], list[TraceSpec], list[ViaSpec]]] = []
            n_vias: list[tuple[tuple[float, float], list[TraceSpec], list[ViaSpec]]] = []
            for dx, dy in offsets:
                vx, vy = round(ppad[0] + dx, 4), round(ppad[1] + dy, 4)
                if len(p_vias) < 6 and space.via_ok(vx, vy, v_diam_esc, thru_span, pname, ignore_nets={nname}):
                    if math.hypot(dx, dy) < 0.01 or space.segment_ok(ppad[0], ppad[1], vx, vy, w_p, pl_e, pname, ignore_nets={nname}):
                        trs = [TraceSpec(pname, pl_e, (ppad, (vx, vy)), w_p)] if math.hypot(dx, dy) >= 0.01 else []
                        p_vias.append(((vx, vy), trs, [ViaSpec(pname, vx, vy, v_diam_esc, v_drill_esc, thru_layers)]))
                nx, ny = round(npad[0] + dx, 4), round(npad[1] + dy, 4)
                if len(n_vias) < 6 and space.via_ok(nx, ny, v_diam_esc, thru_span, nname, ignore_nets={pname}):
                    if math.hypot(dx, dy) < 0.01 or space.segment_ok(npad[0], npad[1], nx, ny, w_n, nl_e, nname, ignore_nets={pname}):
                        trs = [TraceSpec(nname, nl_e, (npad, (nx, ny)), w_n)] if math.hypot(dx, dy) >= 0.01 else []
                        n_vias.append(((nx, ny), trs, [ViaSpec(nname, nx, ny, v_diam_esc, v_drill_esc, thru_layers)]))
            for pv, ptrs, pvs in p_vias:
                for nv, ntrs, nvs in n_vias:
                    if math.hypot(pv[0] - nv[0], pv[1] - nv[1]) - v_diam_esc < rules.min_clearance_mm + 0.02:
                        continue
                    # Ensure breakout stubs on pad layer don't short each other
                    ok_pair = True
                    for t1 in ptrs:
                        for t2 in ntrs:
                            if t1.layer == t2.layer:
                                if _dist_seg_to_seg(t1.points_mm[0][0], t1.points_mm[0][1], t1.points_mm[1][0], t1.points_mm[1][1],
                                                    t2.points_mm[0][0], t2.points_mm[0][1], t2.points_mm[1][0], t2.points_mm[1][1]) - 0.5 * (t1.width_mm + t2.width_mm) < rules.min_clearance_mm + 0.02:
                                    ok_pair = False
                                    break
                    if ok_pair:
                        cands.append((pv, nv, ptrs + ntrs, pvs + nvs))
            # Ensure both P-above-N and P-below-N / P-left-N and P-right-N polarities appear early!
            if len(cands) > 4:
                pos_y = [c for c in cands if c[0][1] > c[1][1] + 0.05]
                neg_y = [c for c in cands if c[0][1] < c[1][1] - 0.05]
                pos_x = [c for c in cands if c[0][0] > c[1][0] + 0.05]
                neg_x = [c for c in cands if c[0][0] < c[1][0] - 0.05]
                interleaved: list[tuple[tuple[float, float], tuple[float, float], list[TraceSpec], list[ViaSpec]]] = []
                seen_k: set[tuple[tuple[float, float], tuple[float, float]]] = set()
                for bucket in (pos_y[:3], neg_y[:3], pos_x[:3], neg_x[:3], cands):
                    for item in bucket:
                        k = (item[0], item[1])
                        if k not in seen_k:
                            seen_k.add(k)
                            interleaved.append(item)
                cands = interleaved[:12]
        return cands

    def _validate_and_commit_diff_plan(
        pname: str,
        nname: str,
        layer: str,
        w_d: float,
        s_gap: float,
        center_pts: Sequence[tuple[float, float]],
        pa0: tuple[float, float],
        na0: tuple[float, float],
        pa1: tuple[float, float],
        na1: tuple[float, float],
        end_traces: list[TraceSpec],
        end_vias: list[ViaSpec],
    ) -> bool:
        half_p = 0.5 * (w_d + s_gap)
        c_clean = list(_simplify_polyline(center_pts))
        if len(c_clean) < 2:
            return False
        # Verify every center-line segment has length >= pitch so parallel corners never invert
        for i in range(len(c_clean) - 1):
            if math.hypot(c_clean[i + 1][0] - c_clean[i][0], c_clean[i + 1][1] - c_clean[i][1]) < (w_d + s_gap) + 0.05:
                return False

        # Choose orientation (flip=False vs True) minimizing end-stub crossover
        best_rails: tuple[list[tuple[float, float]], list[tuple[float, float]]] | None = None
        best_cost = 1e18
        for flip in (False, True):
            pr, nr = _offset_ortho_polyline(c_clean, half_p, flip=flip)
            if not pr or not nr:
                continue
            c_dist = (
                math.hypot(pa0[0] - pr[0][0], pa0[1] - pr[0][1])
                + math.hypot(na0[0] - nr[0][0], na0[1] - nr[0][1])
                + math.hypot(pa1[0] - pr[-1][0], pa1[1] - pr[-1][1])
                + math.hypot(na1[0] - nr[-1][0], na1[1] - nr[-1][1])
            )
            if c_dist < best_cost:
                best_cost = c_dist
                best_rails = (pr, nr)
        if best_rails is None:
            return False
        p_rail, n_rail = best_rails

        # Validate both coupled rails against existing copper
        for i in range(len(p_rail) - 1):
            if not space.segment_ok(p_rail[i][0], p_rail[i][1], p_rail[i + 1][0], p_rail[i + 1][1], w_d, layer, pname):
                return False
        for i in range(len(n_rail) - 1):
            if not space.segment_ok(n_rail[i][0], n_rail[i][1], n_rail[i + 1][0], n_rail[i + 1][1], w_d, layer, nname):
                return False

        # Connect anchors (pa0, na0) -> (p_rail[0], n_rail[0]) and (p_rail[-1], n_rail[-1]) -> (pa1, na1)
        plan_traces: list[TraceSpec] = list(end_traces)
        plan_traces.append(TraceSpec(pname, layer, tuple(p_rail), w_d, diff_spacing_mm=s_gap))
        plan_traces.append(TraceSpec(nname, layer, tuple(n_rail), w_d, diff_spacing_mm=s_gap))
        for ename, anchor, target in (
            (pname, pa0, p_rail[0]),
            (nname, na0, n_rail[0]),
            (pname, pa1, p_rail[-1]),
            (nname, na1, n_rail[-1]),
        ):
            d_stub = math.hypot(anchor[0] - target[0], anchor[1] - target[1])
            if d_stub <= 0.01:
                continue
            # Keep breakout stubs short (< 1.95 mm) so DRC diff-pair body check passes strictly!
            if d_stub > 1.92:
                return False
            if space.segment_ok(anchor[0], anchor[1], target[0], target[1], w_d, layer, ename):
                plan_traces.append(TraceSpec(ename, layer, (anchor, target), w_d, diff_spacing_mm=s_gap))
            else:
                return False

        # Verify P vs N intra-pair clearance >= min_clearance AND >= s_gap - 0.005 on body layer
        p_segs = [
            (tr.points_mm[i], tr.points_mm[i + 1], tr.layer, tr.width_mm)
            for tr in plan_traces if tr.net == pname
            for i in range(len(tr.points_mm) - 1)
        ]
        n_segs = [
            (tr.points_mm[i], tr.points_mm[i + 1], tr.layer, tr.width_mm)
            for tr in plan_traces if tr.net == nname
            for i in range(len(tr.points_mm) - 1)
        ]
        for a0, a1, la, wa in p_segs:
            for b0, b1, lb, wb in n_segs:
                if la == lb:
                    d_e = _dist_seg_to_seg(a0[0], a0[1], a1[0], a1[1], b0[0], b0[1], b1[0], b1[1]) - 0.5 * (wa + wb)
                    req_d = (s_gap - 0.006) if la == layer else (rules.min_clearance_mm + 0.015)
                    if d_e < max(rules.min_clearance_mm + 0.015, req_d):
                        return False
        for vi_a in range(len(end_vias)):
            va = end_vias[vi_a]
            for vi_b in range(vi_a + 1, len(end_vias)):
                vb = end_vias[vi_b]
                if va.net != vb.net and math.hypot(va.x_mm - vb.x_mm, va.y_mm - vb.y_mm) - 0.5 * (va.diameter_mm + vb.diameter_mm) < rules.min_clearance_mm + 0.015:
                    return False
            opp_segs = n_segs if va.net == pname else p_segs
            for a0, a1, la, wa in opp_segs:
                if _dist_point_to_seg(va.x_mm, va.y_mm, a0[0], a0[1], a1[0], a1[1]) - 0.5 * (va.diameter_mm + wa) < rules.min_clearance_mm + 0.015:
                    return False

        for tr in plan_traces:
            commit_trace(tr)
        for pv in end_vias:
            commit_via(pv)
        return True

    def _astar_coupled_centerline(
        pname: str,
        nname: str,
        layer: str,
        w_d: float,
        s_gap: float,
        c_start: tuple[float, float],
        c_goal: tuple[float, float],
        g_d: float,
        max_expansions: int = 8000,
    ) -> list[tuple[float, float]] | None:
        """Coupled center-line A* keeping BOTH P and N rails clear at ±0.5*(w_d+s_gap)."""
        nx_max = int(math.floor(board_spec.width_mm / g_d))
        ny_max = int(math.floor(board_spec.height_mm / g_d))
        sx = max(2, min(nx_max - 2, int(round(c_start[0] / g_d))))
        sy = max(2, min(ny_max - 2, int(round(c_start[1] / g_d))))
        gx_t = max(2, min(nx_max - 2, int(round(c_goal[0] / g_d))))
        gy_t = max(2, min(ny_max - 2, int(round(c_goal[1] / g_d))))
        if (sx, sy) == (gx_t, gy_t):
            return None
        half_p = 0.5 * (w_d + s_gap)
        pair_w = w_d + (w_d + s_gap)  # Envelope width of coupled pair (2*w_d + s_gap)
        edge_cache: dict[tuple[int, int, int, int], bool] = {}

        def pair_edge_ok(x0i: int, y0i: int, x1i: int, y1i: int) -> bool:
            key = (x0i, y0i, x1i, y1i) if (x0i, y0i) <= (x1i, y1i) else (x1i, y1i, x0i, y0i)
            res = edge_cache.get(key)
            if res is None:
                ax, ay = round(x0i * g_d, 4), round(y0i * g_d, 4)
                bx, by = round(x1i * g_d, 4), round(y1i * g_d, 4)
                # Conservative envelope check with both P and N clearance + HV rules
                res = (
                    space.segment_ok(ax, ay, bx, by, pair_w + 0.04, layer, pname)
                    and space.segment_ok(ax, ay, bx, by, pair_w + 0.04, layer, nname)
                )
                edge_cache[key] = res
            return res

        heap: list[tuple[float, float, int, int, int]] = [(1.4 * (abs(sx - gx_t) + abs(sy - gy_t)), 0.0, sx, sy, 0)]
        g_cost: dict[tuple[int, int], float] = {(sx, sy): 0.0}
        came: dict[tuple[int, int], tuple[int, int] | None] = {(sx, sy): None}
        found = False
        exp = 0
        while heap and exp < max_expansions:
            _, cg, cx, cy, pdir = heapq.heappop(heap)
            if cg > g_cost.get((cx, cy), 1e18) + 1e-9:
                continue
            if (cx, cy) == (gx_t, gy_t):
                found = True
                break
            exp += 1
            for dx, dy, ndir in ((1, 0, 1), (-1, 0, 1), (0, 1, 2), (0, -1, 2)):
                nx, ny = cx + dx, cy + dy
                if not (2 <= nx < nx_max - 1 and 2 <= ny < ny_max - 1):
                    continue
                bend = 0.6 if (pdir != 0 and pdir != ndir) else 0.0
                ng = cg + 1.0 + bend
                if ng >= g_cost.get((nx, ny), 1e18):
                    continue
                if not pair_edge_ok(cx, cy, nx, ny):
                    continue
                g_cost[(nx, ny)] = ng
                came[(nx, ny)] = (cx, cy)
                heapq.heappush(heap, (ng + 1.4 * (abs(nx - gx_t) + abs(ny - gy_t)), ng, nx, ny, ndir))
        if not found:
            return None
        pts_g: list[tuple[float, float]] = []
        cur: tuple[int, int] | None = (gx_t, gy_t)
        while cur is not None:
            pts_g.append((round(cur[0] * g_d, 4), round(cur[1] * g_d, 4)))
            cur = came[cur]
        pts_g.reverse()
        return list(_simplify_polyline(pts_g))

    routed_diff_nets: set[str] = set()
    for ns in board_spec.nets:
        if not ns.diff_pair_with or ns.name in routed_diff_nets or ns.target_z0_ohm is None:
            continue
        partner = net_map.get(ns.diff_pair_with)
        if partner is None:
            continue
        routed_diff_nets.add(ns.name)
        routed_diff_nets.add(partner.name)

        p_pads = [(pbox.center, players, ccenter) for pbox, pnet, players, _, _, ccenter in space.pad_list if pnet == ns.name]
        n_pads = [(pbox.center, players, ccenter) for pbox, pnet, players, _, _, ccenter in space.pad_list if pnet == partner.name]
        if len(p_pads) != 2 or len(n_pads) != 2:
            continue
        if math.hypot(p_pads[0][0][0] - n_pads[0][0][0], p_pads[0][0][1] - n_pads[0][0][1]) <= math.hypot(
            p_pads[0][0][0] - n_pads[1][0][0], p_pads[0][0][1] - n_pads[1][0][1]
        ):
            (p0, pl0, pcc0), (p1, pl1, pcc1) = p_pads[0], p_pads[1]
            (n0, nl0, ncc0), (n1, nl1, ncc1) = n_pads[0], n_pads[1]
        else:
            (p0, pl0, pcc0), (p1, pl1, pcc1) = p_pads[0], p_pads[1]
            (n0, nl0, ncc0), (n1, nl1, ncc1) = n_pads[1], n_pads[0]

        s_gap = max(0.20, rules.min_clearance_mm + 0.05)
        # Prefer inner stripline signal layers first if available (clear of F.Cu BGAs), then F.Cu / B.Cu
        inner_sig = [l for l in route_layers if l not in ("F.Cu", "B.Cu")]
        layer_order = inner_sig + [l for l in ("F.Cu", "B.Cu") if l in route_layers]

        coupled_ok = False
        for layer in layer_order:
            w_d = trace_width_for(ns.name, layer)
            g_d = max(0.75, round(grid_mm, 2), round(w_d + s_gap + 0.20, 2))
            esc0 = _pair_escape_end(ns.name, partner.name, p0, pl0, pcc0, n0, nl0, ncc0, layer, w_d)
            esc1 = _pair_escape_end(ns.name, partner.name, p1, pl1, pcc1, n1, nl1, ncc1, layer, w_d)
            if not esc0 or not esc1:
                continue
            for pa0, na0, tr0, v0 in esc0[:6]:
                for pa1, na1, tr1, v1 in esc1[:6]:
                    m0 = (round(0.5 * (pa0[0] + na0[0]), 4), round(0.5 * (pa0[1] + na0[1]), 4))
                    m1 = (round(0.5 * (pa1[0] + na1[0]), 4), round(0.5 * (pa1[1] + na1[1]), 4))
                    dx_pair, dy_pair = m1[0] - m0[0], m1[1] - m0[1]
                    # Step coupled trunk start/end slightly ahead of both anchors so neither stub doubles back!
                    if abs(dx_pair) >= abs(dy_pair):
                        sx_dir = 1.0 if dx_pair >= 0 else -1.0
                        c0 = (round((max(pa0[0], na0[0]) + 0.55) if sx_dir > 0 else (min(pa0[0], na0[0]) - 0.55), 4), m0[1])
                        c1 = (round((min(pa1[0], na1[0]) - 0.55) if sx_dir > 0 else (max(pa1[0], na1[0]) + 0.55), 4), m1[1])
                    else:
                        sy_dir = 1.0 if dy_pair >= 0 else -1.0
                        c0 = (m0[0], round((max(pa0[1], na0[1]) + 0.55) if sy_dir > 0 else (min(pa0[1], na0[1]) - 0.55), 4))
                        c1 = (m1[0], round((min(pa1[1], na1[1]) - 0.55) if sy_dir > 0 else (max(pa1[1], na1[1]) + 0.55), 4))
                    # 1) Fast direct straight / L / Z / U coupled center-line candidates
                    direct_cands: list[list[tuple[float, float]]] = []
                    for s_pt, e_pt in ((c0, c1), (m0, m1)):
                        mx = round(0.5 * (s_pt[0] + e_pt[0]), 4)
                        my = round(0.5 * (s_pt[1] + e_pt[1]), 4)
                        if abs(dx_pair) >= abs(dy_pair):
                            # Straight horizontal trunk at midpoint Y absorbs small <1 mm pad Y-mismatch cleanly!
                            direct_cands.append([(s_pt[0], my), (e_pt[0], my)])
                            direct_cands.append([(s_pt[0], s_pt[1]), (e_pt[0], s_pt[1])])
                            direct_cands.append([(s_pt[0], e_pt[1]), (e_pt[0], e_pt[1])])
                        else:
                            direct_cands.append([(mx, s_pt[1]), (mx, e_pt[1])])
                            direct_cands.append([(s_pt[0], s_pt[1]), (s_pt[0], e_pt[1])])
                            direct_cands.append([(e_pt[0], s_pt[1]), (e_pt[0], e_pt[1])])
                        direct_cands.extend([
                            [s_pt, (e_pt[0], s_pt[1]), e_pt],
                            [s_pt, (s_pt[0], e_pt[1]), e_pt],
                            [s_pt, (mx, s_pt[1]), (mx, e_pt[1]), e_pt],
                            [s_pt, (s_pt[0], my), (e_pt[0], my), e_pt],
                            # Detour jog (U-turn) when s_pt.y ~ e_pt.y and straight line is blocked
                            [s_pt, (s_pt[0], round(my + 2.5, 4)), (e_pt[0], round(my + 2.5, 4)), e_pt],
                            [s_pt, (s_pt[0], round(my - 2.5, 4)), (e_pt[0], round(my - 2.5, 4)), e_pt],
                        ])
                    for cpath in direct_cands:
                        if _validate_and_commit_diff_plan(ns.name, partner.name, layer, w_d, s_gap, cpath, pa0, na0, pa1, na1, tr0 + tr1, v0 + v1):
                            coupled_ok = True
                            break
                    if coupled_ok:
                        break
                    # 2) Coupled center-line A* routing around pads, air-slots, and other pairs!
                    c_astar = _astar_coupled_centerline(ns.name, partner.name, layer, w_d, s_gap, c0, c1, g_d=g_d, max_expansions=6000)
                    if c_astar and _validate_and_commit_diff_plan(ns.name, partner.name, layer, w_d, s_gap, c_astar, pa0, na0, pa1, na1, tr0 + tr1, v0 + v1):
                        coupled_ok = True
                        break
                if coupled_ok:
                    break
            if coupled_ok:
                break

    # Phase 3B: Route ALL remaining multi-pin & guard-ring nets to 100% Union-Find connectivity!
    def _net_priority(ns: NetSpec) -> tuple[int, float, str]:
        if ns.name in priority_boost:
            tier = -1
        elif ns.target_z0_ohm is not None:
            tier = 0
        elif ns.name in space.hv_rules_for_net:
            tier = 1
        elif not ns.is_power:
            tier = 2
        else:
            tier = 3
        pts = [pbox.center for pbox, pnet, _, _, _, _ in space.pad_list if pnet == ns.name]
        if len(pts) >= 2:
            span = (max(p[0] for p in pts) - min(p[0] for p in pts)) + (max(p[1] for p in pts) - min(p[1] for p in pts))
        else:
            span = 0.0
        return (tier, span, ns.name)

    failed_nets: set[str] = set()
    ordered_nets = sorted(board_spec.nets, key=_net_priority)
    for ns in ordered_nets:
        nname = ns.name
        for _step in range(max(4, len(ns.nodes) + 16)):
            islands, _ = _net_islands(nname)
            if len(islands) <= 1:
                break
            pair_list: list[tuple[float, int, int]] = []
            for i in range(len(islands)):
                for j in range(i + 1, len(islands)):
                    d_min = min(
                        math.hypot(a[0] - b[0], a[1] - b[1])
                        for a in islands[i][:12]
                        for b in islands[j][:12]
                    )
                    pair_list.append((d_min, i, j))
            pair_list.sort(key=lambda t: t[0])
            _, idx_a, idx_b = pair_list[0]
            routed = _astar_connect(nname, islands[idx_a], islands[idx_b], g=grid_mm, max_expansions=18000, heuristic_weight=1.4)
            if not routed and grid_mm > 0.28:
                routed = _astar_connect(nname, islands[idx_a], islands[idx_b], g=round(grid_mm * 0.5, 4), max_expansions=22000, heuristic_weight=1.5)
            if not routed:
                # Try at most 2 next-closest island pairs to prevent O(K^2) stalls
                for _, ia_alt, ib_alt in pair_list[1:3]:
                    if _astar_connect(nname, islands[ia_alt], islands[ib_alt], g=grid_mm, max_expansions=15000, heuristic_weight=1.5):
                        routed = True
                        break
            if not routed:
                failed_nets.add(nname)
                break

    routed_spec = BoardSpec(
        name=board_spec.name,
        title=board_spec.title,
        rev=board_spec.rev,
        bom_ids=board_spec.bom_ids,
        width_mm=board_spec.width_mm,
        height_mm=board_spec.height_mm,
        stackup=board_spec.stackup,
        components=board_spec.components,
        nets=board_spec.nets,
        traces=tuple(out_traces),
        vias=tuple(out_vias),
        zones=board_spec.zones,
        keepouts=board_spec.keepouts,
        creepage_rules=board_spec.creepage_rules,
        rules=board_spec.rules,
        epistemic_meta=dict(board_spec.epistemic_meta),
        notes=board_spec.notes,
    )
    return routed_spec, failed_nets


def auto_route_board(
    board_spec: BoardSpec,
    *,
    grid_mm: float = 0.50,
    default_trace_width_mm: float = 0.16,
    via_diameter_mm: float = 0.48,
    via_drill_mm: float = 0.24,
    preserve_existing: bool = True,
    route_power_via_zones: bool = True,
    max_passes: int = 3,
) -> BoardSpec:
    """Deterministically route 100% of multi-pin nets pad-to-pad across layers, vias & zones.

    Uses staggered dogbone pin escapes, internal power/ground zone via-fanout, coupled
    differential-pair trunk routing, weighted multi-layer A* with exact continuous clearance
    & HV dielectric checks, and priority-bump rip-up/reroute passes until ``0`` unconnected nets.
    """
    boost: set[str] = set()
    best_spec = board_spec
    best_fail_cnt = 10**9
    for _pass in range(max(1, max_passes)):
        spec_out, failed = _auto_route_once(
            board_spec,
            grid_mm=grid_mm,
            default_trace_width_mm=default_trace_width_mm,
            via_diameter_mm=via_diameter_mm,
            via_drill_mm=via_drill_mm,
            preserve_existing=preserve_existing,
            route_power_via_zones=route_power_via_zones,
            priority_boost=boost,
        )
        if len(failed) < best_fail_cnt:
            best_spec = spec_out
            best_fail_cnt = len(failed)
        if not failed:
            return spec_out
        if failed.issubset(boost):
            break
        boost.update(failed)
    return best_spec


# ---------------------------------------------------------------------------
# 11. Convenience Bundle Helper (Write + S-expr + ERC + DRC in One Call)
# ---------------------------------------------------------------------------

def verify_board_bundle(
    board_spec: BoardSpec,
    out_dir: str | Path,
) -> dict[str, Any]:
    """Write .kicad_sch & .kicad_pcb for a BoardSpec, parse S-expr, and run strict ERC + DRC."""
    od = Path(out_dir)
    od.mkdir(parents=True, exist_ok=True)
    sch_path = write_kicad_sch(board_spec, od / f"{board_spec.name}.kicad_sch")
    pcb_path = write_kicad_pcb(board_spec, od / f"{board_spec.name}.kicad_pcb")

    # Independent S-expr parse check on both files
    sch_tree = parse_sexpr(sch_path.read_text(encoding="utf-8"))
    pcb_tree = parse_sexpr(pcb_path.read_text(encoding="utf-8"))
    erc = run_erc(sch_path, board_spec, pcb_path=pcb_path)
    drc = run_drc(pcb_path, board_spec)
    return {
        "board_name": board_spec.name,
        "bom_ids": list(board_spec.bom_ids),
        "sch_file": sch_path.name,
        "pcb_file": pcb_path.name,
        "sexpr_valid": bool(sch_tree and pcb_tree and sch_tree[0] == "kicad_sch" and pcb_tree[0] == "kicad_pcb"),
        "erc": erc.to_dict(),
        "drc": drc.to_dict(),
        "passed": bool(erc.passed and drc.passed),
        "epistemic_meta": dict(board_spec.epistemic_meta),
    }
