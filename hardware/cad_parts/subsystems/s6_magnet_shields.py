"""Subsystem S6 (Part 1/2): Cryocooler, Cold Island, 8-Coil Magnet, Shields & Isolation.

Wave 2B / WP-M4 — Atom Lithography Machine Full 180-Part Hardware Blueprint.
Designs 21 / 43 physical parts assigned to WP-M4:
- S6.1-01..03: PT420 2-stage cold head, floor-mounted CPA He compressor, 50K/4K Cu braids
- S6.2-01..03: OFHC Cu cold island + Vespel SP-22 truss, nested 50K/4K/Still shields + MLI + shutter,
               LakeShore 372/336 thermometry rack unit
- S6.3-01..05: 8-coil (M/S) NbTi magnet former & Lorentz tie-rods, A/B active bucking bobbins,
               bolted Nb (RRR>300) Meissner cup + Cryoperm-10 shield w/ vent holes,
               persistent switch + cold diodes + 1.563 Ohm quench box, +/-100 A magnet PSU + HTS leads
- S6.4-01..03: ESR microwave synthesizers (4x), I/Q modulators/amps (4x), cryo MW coax + XMA attenuators (8x)
- S6.5-01..03: ENDOR RF DDS sources (4x), 10 W class-A RF amps (4x), cryo RF coax + Eccosorb LPF (8x)
- S6.9-01..04: PT420 500 mm offset acoustic remote valve + 600 mm flex He U-loop (Exp133),
               28-convolution edge-welded 316L CF63 OVC bellows (k=2000 N/m),
               DR OFHC Cu busbar + 4x S-loop vibration-decoupling braids (k=52.7 N/m),
               PT420 harmonic feedforward DSP/FPGA rack unit

Coordinate System (locked to research/atom_lithography_machine/cad/params.py):
- Global floor plane: Z = 0.0 mm
- Wafer active top plane (z_loc = 0.0 mm): Z_WAFER = 500.0 mm
- Main UHV chamber & 8-coil magnet centerline: X = 0.0, Y = 0.0
- Horizontal Exp133 cryo bridge centerline: Y = 0.0, Z = 493.5 mm (inside 36 mm split gap)
- Dilution Refrigerator (DR) tower centerline: X = -650.0, Y = 0.0
- PT420 remote rotary valve stand: X = -1150.0, Y = 0.0 (500 mm offset)
- 42U 19-inch EMI Rack Bay 2 (S6 electronics): X = +2100.0, Y = 0.0, U1 bottom Z = 90.0 mm
- Every part mesh & PortInterface is built in clean local datum coordinates (0, 0, 0)
  with exact global placement in PartDesign.world_origin_mm / world_rotation_deg.

Epistemic Status: M0_M1_DETAILED_CAD_DESIGN_ONLY, no_lab_measurement=True,
iec61508_certified=False, semi_s2_certified=False.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from hardware.cad_parts.core import (
    DESIGN_MATURITY,
    IEC61508_CERTIFIED,
    NO_LAB_MEASUREMENT,
    REPO_ROOT,
    SEMI_S2_CERTIFIED,
    DimensionCallout,
    GDTFrame,
    PartArtifactResult,
    PartDesign,
    PortInterface,
    ScadFeature,
    SolidMesh,
    ToleranceContributor,
    check_cold_clearance,
    check_tolerance_stack,
    circle_2d,
    compute_mass_props,
    export_part_artifacts,
    make_bellows,
    make_box,
    make_cf_flange,
    make_cf_port_interface,
    make_chamfered_box,
    make_cylinder,
    make_isok_flange,
    make_part_design_from_bom,
    make_plate_with_holes,
    make_rect_plate_with_features,
    make_revolved_profile,
    make_ring_with_bolt_circle,
    make_s_braid,
    make_swept_tube,
    make_tube,
    merge_solids,
    rect_2d,
    split_shells,
    transform_mesh,
    verify_watertight,
)

# ---------------------------------------------------------------------------
# Global Machine Anchors (mm) — locked to cad/params.py v6.0 & Wave 2B Map
# ---------------------------------------------------------------------------
Z_WAFER_MM: float = 500.0
Z_CRYO_BRIDGE_MM: float = 493.5
DR_X_MM: float = -650.0
DR_Y_MM: float = 0.0
RV_X_MM: float = -1150.0  # 500 mm offset from DR_X_MM
RACK_BAY2_X_MM: float = 2100.0
RACK_BAY2_Y_MM: float = 0.0
RACK_U_PITCH_MM: float = 44.45
RACK_U1_BOTTOM_Z_MM: float = 90.0

DEFAULT_OUT_S6_DIR: Path = REPO_ROOT / "hardware" / "cad_parts" / "out" / "S6"
DEFAULT_OUT_S9_OPTQ_DIR: Path = REPO_ROOT / "hardware" / "cad_parts" / "out" / "S9_optq"

S6_MAGNET_SHIELDS_PART_IDS: tuple[str, ...] = (
    "S6.1-01",
    "S6.1-02",
    "S6.1-03",
    "S6.2-01",
    "S6.2-02",
    "S6.2-03",
    "S6.3-01",
    "S6.3-02",
    "S6.3-03",
    "S6.3-04",
    "S6.3-05",
    "S6.4-01",
    "S6.4-02",
    "S6.4-03",
    "S6.5-01",
    "S6.5-02",
    "S6.5-03",
    "S6.9-01",
    "S6.9-02",
    "S6.9-03",
    "S6.9-04",
)


# ---------------------------------------------------------------------------
# Shared Data Container & Geometric Helpers (imported by s6_dr_readout_optq)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BuiltPart:
    """Bundled frozen design specification, local watertight mesh, and CSG features."""

    design: PartDesign
    mesh: SolidMesh
    scad_features: tuple[ScadFeature, ...] = ()
    density_kg_m3: float | None = None

    @property
    def part_id(self) -> str:
        return self.design.part_id

    def world_mesh(self) -> SolidMesh:
        """Return watertight mesh placed in global machine coordinates (mm)."""
        return transform_mesh(
            self.mesh,
            translation=self.design.world_origin_mm,
            rotation_deg=self.design.world_rotation_deg,
            name=f"{self.part_id}_world",
        )


def rack_u_center_and_height(u_start: int, n_u: int, gap_mm: float = 2.0) -> tuple[float, float]:
    """Compute world Z center and chassis height (mm) for 1-indexed Rack Bay 2 U-slots."""
    z_bot = RACK_U1_BOTTOM_Z_MM + (u_start - 1) * RACK_U_PITCH_MM + 0.5 * gap_mm
    dz = n_u * RACK_U_PITCH_MM - gap_mm
    return (z_bot + 0.5 * dz, dz)


def make_arc_tube(
    r_in: float,
    r_out: float,
    height: float,
    deg0: float,
    deg1: float,
    *,
    n_per_360: int = 48,
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "arc_tube",
    material: str = "316LN",
) -> SolidMesh:
    """Create a strictly watertight hollow angular-sector tube along local Z."""
    span = float(deg1) - float(deg0)
    if span <= 0.0 or span >= 360.0:
        raise ValueError(f"make_arc_tube requires 0 < deg1 - deg0 < 360, got {span}")
    if r_in <= 0.0 or r_out <= r_in or height <= 0.0:
        raise ValueError("Invalid radii or height for make_arc_tube")
    n = max(8, int(round(n_per_360 * span / 360.0)))
    hz = 0.5 * float(height)
    th = np.linspace(math.radians(deg0), math.radians(deg1), n + 1)
    c, s = np.cos(th), np.sin(th)
    m = n + 1
    bo = np.column_stack([r_out * c, r_out * s, np.full(m, -hz)])
    to = np.column_stack([r_out * c, r_out * s, np.full(m, hz)])
    bi = np.column_stack([r_in * c, r_in * s, np.full(m, -hz)])
    ti = np.column_stack([r_in * c, r_in * s, np.full(m, hz)])
    v = np.vstack([bo, to, bi, ti]).astype(np.float64)
    v += np.asarray(center, dtype=np.float64)
    faces: list[list[int]] = []
    for i in range(n):
        j = i + 1
        faces.append([i, j, m + j])
        faces.append([i, m + j, m + i])
        faces.append([2 * m + j, 2 * m + i, 3 * m + i])
        faces.append([2 * m + j, 3 * m + i, 3 * m + j])
        faces.append([m + i, m + j, 3 * m + j])
        faces.append([m + i, 3 * m + j, 3 * m + i])
        faces.append([j, i, 2 * m + i])
        faces.append([j, 2 * m + i, 2 * m + j])
    faces.append([0, m, 3 * m])
    faces.append([0, 3 * m, 2 * m])
    faces.append([n, 2 * m + n, 3 * m + n])
    faces.append([n, 3 * m + n, m + n])
    return SolidMesh(
        vertices=v,
        faces=np.asarray(faces, dtype=np.int32),
        name=name,
        material=material,
    )


def make_hollow_frame(
    outer_x: float,
    outer_y: float,
    inner_x: float,
    inner_y: float,
    height: float,
    *,
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "frame",
    material: str = "Steel",
) -> SolidMesh:
    """Create a watertight hollow rectangular structural frame extruded along Z."""
    outer = rect_2d(outer_x, outer_y, ccw=True)
    inner = rect_2d(inner_x, inner_y, ccw=False)
    return make_plate_with_holes(
        outer,
        [inner],
        thickness=height,
        axis="z",
        center=center,
        name=name,
        material=material,
    )


def make_rack_chassis_19in(
    depth_mm: float,
    height_mm: float,
    *,
    n_subunits: int = 1,
    n_front_ports: int = 4,
    wall_mm: float = 2.5,
    material: str = "Al 6061",
    name: str = "rack_chassis",
) -> tuple[SolidMesh, tuple[ScadFeature, ...]]:
    """Build a feature-level watertight 19-inch EIA-310 rack-mount chassis.

    Width along X = 482.6 mm (front panel ears), body width = 440.0 mm,
    Depth along Y = depth_mm (front bezel at -Y/2, rear I/O at +Y/2),
    Height along Z = height_mm (centered at local Z = 0).
    """
    panel_w = 482.6
    body_w = 440.0
    front_t = 4.0
    body_d = depth_mm - front_t - 0.1
    y_front = -0.5 * depth_mm + 0.5 * front_t
    y_body = 0.5 * front_t + 0.05

    parts: list[SolidMesh] = []
    feats: list[ScadFeature] = []

    # 1. Front 19" EIA-310 bezel panel with 4 machined rack-ear mounting slots (oriented along Y)
    ear_x = 232.6  # EIA-310 standard 465.1 mm horizontal pitch -> +-232.55 mm
    ear_z = max(0.32 * height_mm, min(height_mm * 0.5 - 8.0, 15.875))
    slots: list[tuple[float, float, float, float, float]] = [
        (-ear_x, -ear_z, 10.0, 6.5, 0.0),
        (-ear_x, +ear_z, 10.0, 6.5, 0.0),
        (+ear_x, -ear_z, 10.0, 6.5, 0.0),
        (+ear_x, +ear_z, 10.0, 6.5, 0.0),
    ]
    if height_mm >= 120.0:
        slots.extend(
            [
                (-ear_x, 0.0, 10.0, 6.5, 0.0),
                (+ear_x, 0.0, 10.0, 6.5, 0.0),
            ]
        )
    front_plate = make_rect_plate_with_features(
        panel_w,
        height_mm,
        front_t,
        rect_slots=slots,
        axis="y",
        center=(0.0, y_front, 0.0),
        name=f"{name}_front_bezel",
        material=material,
    )
    parts.append(front_plate)
    feats.append(
        ScadFeature(
            "add_box",
            {"dx": panel_w, "dy": front_t, "dz": height_mm},
            translate=(0.0, y_front, 0.0),
            comment='19" EIA-310 front bezel panel',
        )
    )
    for sx, sz, sl, sw, _ in slots:
        feats.append(
            ScadFeature(
                "cut_slot",
                {"length": sl, "width": sw, "h": front_t + 2.0},
                translate=(sx, y_front, sz),
                rotate=(90.0, 0.0, 0.0),
                comment="EIA-310 rack ear slot",
            )
        )

    # 2. Hollow sheet-metal enclosure sleeve (non-overlapping top/bot/sides/rear)
    sub_h = (height_mm - 2.0 * (n_subunits - 1)) / float(n_subunits)
    for s_idx in range(n_subunits):
        zc = -0.5 * height_mm + (s_idx + 0.5) * sub_h + s_idx * 2.0
        sh = sub_h - 0.1
        # Hollow outer shell along Y
        outer_xz = rect_2d(body_w, sh, ccw=True)
        inner_xz = rect_2d(body_w - 2.0 * wall_mm, max(sh - 2.0 * wall_mm, 4.0), ccw=False)
        sleeve = make_plate_with_holes(
            outer_xz,
            [inner_xz],
            thickness=body_d - wall_mm - 0.1,
            axis="y",
            center=(0.0, y_body - 0.5 * wall_mm - 0.05, zc),
            name=f"{name}_sleeve_{s_idx}",
            material=material,
        )
        parts.append(sleeve)
        # Rear panel with circular fan/exhaust vents
        rear_y = 0.5 * depth_mm - 0.5 * wall_mm
        fan_d = min(0.65 * sh, 60.0)
        rear_holes = [(-120.0, 0.0, fan_d), (120.0, 0.0, fan_d)] if fan_d >= 18.0 else []
        rear = make_rect_plate_with_features(
            body_w,
            sh,
            wall_mm,
            circular_holes=rear_holes,
            hole_segments=12,
            axis="y",
            center=(0.0, rear_y, zc),
            name=f"{name}_rear_{s_idx}",
            material=material,
        )
        parts.append(rear)
        # Internal mid-plane PCB/heatsink deck for realistic thermal & mechanical inertia
        deck = make_box(
            body_w - 2.0 * wall_mm - 2.0,
            body_d - 2.0 * wall_mm - 8.0,
            max(2.0, min(4.0, 0.06 * sh)),
            center=(0.0, y_body, zc - 0.2 * sh),
            name=f"{name}_deck_{s_idx}",
            material="FR4",
        )
        parts.append(deck)

    feats.append(
        ScadFeature(
            "add_box",
            {"dx": body_w, "dy": body_d, "dz": height_mm - 1.0},
            translate=(0.0, y_body, 0.0),
            comment="Hollow EMI shielded chassis body",
        )
    )

    # 3. Front grab handles (left & right) + connector bosses protruding slightly forward (-Y)
    handle_d = 12.0
    for sgn in (-1.0, 1.0):
        hx = sgn * 206.0
        parts.append(
            make_box(
                6.0,
                handle_d,
                min(height_mm * 0.72, max(24.0, height_mm - 14.0)),
                center=(hx, -0.5 * depth_mm - 0.5 * handle_d - 0.05, 0.0),
                name=f"{name}_handle_{int(sgn > 0)}",
                material="316LN",
            )
        )
    # Front RF/SMA or control connector bosses
    n_boss = max(2, min(n_front_ports, 14))
    xs = np.linspace(-155.0, 155.0, n_boss)
    for b_idx, bx in enumerate(xs):
        parts.append(
            make_cylinder(
                radius=4.5,
                height=7.0,
                segments=12,
                axis="y",
                center=(float(bx), -0.5 * depth_mm - 3.55, 0.0),
                name=f"{name}_port_{b_idx}",
                material="BeCu",
            )
        )

    mesh = merge_solids(parts, name=name, material=material)
    return mesh, tuple(feats)


def make_staged_coax_loom(
    n_lines_repr: int,
    bundle_w: float,
    bundle_d: float,
    stage_spans_global_z: Sequence[tuple[str, float, float]],
    world_z_origin: float,
    *,
    attenuator_r: float = 3.2,
    clamp_thickness: float = 5.0,
    material: str = "CuNi",
    name: str = "coax_loom",
    coax_od_mm: float | None = None,
) -> tuple[SolidMesh, tuple[ScadFeature, ...]]:
    """Build a segmented multi-stage cryo coax loom with OFHC thermalization clamps & full-count coax lines.

    Each stage span sits strictly between DR plates so zero plate-to-coax intersection occurs.
    OBS-122 fix: Renders exact full coax count (e.g. 56 lines for S6.6-03/04, 48x2=96 lines for S6.11-04)
    without sub-sampling, using lightweight 6-sided cylinders for low triangle count & fast clash audit.
    """
    parts: list[SolidMesh] = []
    feats: list[ScadFeature] = []
    # Arrange ALL n_lines_repr coaxial conductors in a clean grid inside (bundle_w, bundle_d)
    nx = max(2, int(round(math.sqrt(n_lines_repr * (bundle_w / max(bundle_d, 1.0))))))
    ny = max(2, int(math.ceil(n_lines_repr / nx)))
    # Ensure grid has enough slots even after skipping central attenuator footprint
    while nx * ny < n_lines_repr + (4 if attenuator_r > 0.0 else 0):
        if bundle_w / nx >= bundle_d / ny:
            nx += 1
        else:
            ny += 1
    xs = np.linspace(-0.42 * bundle_w, 0.42 * bundle_w, nx)
    ys = np.linspace(-0.40 * bundle_d, 0.40 * bundle_d, ny)
    pitch_x = (0.84 * bundle_w) / max(nx - 1, 1)
    pitch_y = (0.80 * bundle_d) / max(ny - 1, 1)
    r_max_fit = 0.40 * min(pitch_x, pitch_y)
    r_line = min(0.5 * coax_od_mm, r_max_fit) if coax_od_mm is not None else min(1.1, r_max_fit)
    cyl_segs = 6 if n_lines_repr >= 32 else 8

    for st_name, z0_g, z1_g in stage_spans_global_z:
        z0 = z0_g - world_z_origin
        z1 = z1_g - world_z_origin
        h_span = z1 - z0
        zc = 0.5 * (z0 + z1)
        clamp_z_bot = z0 + 0.5 * clamp_thickness
        clamp_z_top = z1 - 0.5 * clamp_thickness
        hole_specs = [(-0.44 * bundle_w, 0.0, 2.2), (0.44 * bundle_w, 0.0, 2.2)]
        for c_tag, cz in (("bot", clamp_z_bot), ("top", clamp_z_top)):
            parts.append(
                make_rect_plate_with_features(
                    bundle_w,
                    bundle_d,
                    clamp_thickness,
                    circular_holes=hole_specs,
                    hole_segments=8,
                    axis="z",
                    center=(0.0, 0.0, cz),
                    name=f"{name}_{st_name}_clamp_{c_tag}",
                    material="OFHC Cu",
                )
            )
        h_wire = h_span - 2.0 * clamp_thickness - 0.2
        att_r_eff = (
            min(attenuator_r, 0.24 * min(bundle_w, bundle_d))
            if (attenuator_r > 0.0 and h_wire > 16.0)
            else 0.0
        )
        if h_wire > 2.0:
            count = 0
            for gx in xs:
                for gy in ys:
                    if count >= n_lines_repr:
                        break
                    if att_r_eff > 0.0 and math.hypot(float(gx), float(gy)) < att_r_eff + r_line + 0.25:
                        continue
                    parts.append(
                        make_cylinder(
                            radius=r_line,
                            height=h_wire,
                            segments=cyl_segs,
                            axis="z",
                            center=(float(gx), float(gy), zc),
                            name=f"{name}_{st_name}_c{count}",
                            material=material,
                        )
                    )
                    count += 1
            if att_r_eff > 0.0:
                parts.append(
                    make_cylinder(
                        radius=att_r_eff,
                        height=min(16.0, 0.45 * h_wire),
                        segments=12,
                        axis="z",
                        center=(0.0, 0.0, zc),
                        name=f"{name}_{st_name}_att",
                        material="OFHC Cu",
                    )
                )
        feats.append(
            ScadFeature(
                "add_box",
                {"dx": bundle_w, "dy": bundle_d, "dz": h_span},
                translate=(0.0, 0.0, zc),
                comment=f"Stage {st_name} thermalized cryo coax loom ({n_lines_repr} lines)",
            )
        )

    return merge_solids(parts, name=name, material=material), tuple(feats)


# ---------------------------------------------------------------------------
# Part Builders (21 parts in s6_magnet_shields.py)
# ---------------------------------------------------------------------------
def _build_s6_1_01() -> BuiltPart:
    """S6.1-01: Cryomech PT420 2-stage (45 K / 4.2 K) pulse-tube cold head."""
    # World origin: (-650, 0, 985) so local z=0 sits at DR top flange top plane (z_global=985)
    # Upper 300 K motor/reservoir head: z_local = [1.0, 235.0] -> z_global = [986.0, 1220.0]
    # Lower 1st stage (45 K): z_local = [-142.0, -0.5] -> z_global = [843.0, 984.5], R=38 mm (clears R_in=46 bores)
    # Lower 2nd stage (4.2 K): z_local = [-243.0, -142.5] -> z_global = [742.0, 842.5], R=22 mm (clears 4K plate z=736)
    parts: list[SolidMesh] = []
    # ISO-K DN160 mounting flange at z_local = +7.0 (z_local = [1.0, 13.0])
    fl = make_isok_flange("DN160", bore_id=126.0, center=(0.0, 0.0, 7.0), name="pt420_dn160", material="316LN")
    parts.append(fl)
    # Stepped 300 K pulse-tube head & buffer reservoir (revolved profile)
    head_prof = [
        (0.0, 13.1),
        (64.0, 13.1),
        (64.0, 110.0),
        (56.0, 118.0),
        (56.0, 225.0),
        (48.0, 235.0),
        (0.0, 235.0),
    ]
    parts.append(make_revolved_profile(head_prof, segments=36, name="pt420_300k_head", material="Al 6061"))
    # -X He inlet/outlet manifold boss facing S6.9-01 U-loop at z_global=1130 (z_local=+145), clearing R=56 wall
    parts.append(
        make_cylinder(
            radius=14.0,
            height=16.8,
            segments=20,
            axis="x",
            center=(-64.6, 0.0, 145.0),
            name="pt420_he_boss",
            material="316LN",
        )
    )
    # 1st stage (45 K) stainless regenerator + OFHC Cu 45 K heat station
    st1_prof = [
        (0.0, -142.0),
        (40.0, -142.0),
        (40.0, -128.0),
        (34.0, -128.0),
        (34.0, -0.5),
        (0.0, -0.5),
    ]
    parts.append(make_revolved_profile(st1_prof, segments=32, name="pt420_stage1_45k", material="OFHC Cu"))
    # 2nd stage (4.2 K) rare-earth regenerator + OFHC Cu 4.2 K cold tip
    st2_prof = [
        (0.0, -243.0),
        (24.0, -243.0),
        (24.0, -229.0),
        (19.0, -229.0),
        (19.0, -142.5),
        (0.0, -142.5),
    ]
    parts.append(make_revolved_profile(st2_prof, segments=32, name="pt420_stage2_4k", material="OFHC Cu"))

    mesh = merge_solids(parts, name="S6.1-01", material="316LN")
    ports = (
        make_cf_port_interface("DN160", "dr_top_isok", (0.0, 0.0, 1.0), (0.0, 0.0, -1.0), mating_part_id="S6.8-04"),
        PortInterface("he_flex_inlet", "gas", (-73.0, 0.0, 145.0), (-1.0, 0.0, 0.0), "Aeroquip 1/2-in He", mating_part_id="S6.9-01", bore_mm=16.0, od_mm=28.0),
        PortInterface("thermal_45k", "thermal", (40.0, 0.0, -135.0), (1.0, 0.0, 0.0), "OFHC M6 Strap Pad", mating_part_id="S6.1-03", od_mm=80.0),
        PortInterface("thermal_4k", "thermal", (24.0, 0.0, -236.0), (1.0, 0.0, 0.0), "OFHC M6 Strap Pad", mating_part_id="S6.1-03", od_mm=48.0),
    )
    design = make_part_design_from_bom(
        "S6.1-01",
        material="316LN",
        world_origin_mm=(DR_X_MM, DR_Y_MM, 985.0),
        ports=ports,
        dimensions=(
            DimensionCallout("HEAD_OD", 128.0, 0.2, -0.2, prefix="Ø"),
            DimensionCallout("TOTAL_H", 478.0, 0.5, -0.5),
            DimensionCallout("STG1_OD", 80.0, 0.1, -0.1, prefix="Ø"),
            DimensionCallout("STG2_OD", 48.0, 0.1, -0.1, prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.05, diameter_zone=True, datum_primary="A", feature_note="2nd stage axis"),
            GDTFrame("flatness", 0.02, datum_primary="A", feature_note="4.2 K cold tip face"),
        ),
        scad_params=(("head_od", 128.0), ("stage1_od", 80.0), ("stage2_od", 48.0), ("cooling_4k_w", 2.0)),
        target_mass_kg=24.0,
    )
    feats = (
        ScadFeature("add_cylinder", {"d": 180.0, "h": 12.0}, translate=(0.0, 0.0, 7.0), comment="ISO-K DN160 flange"),
        ScadFeature("add_cylinder", {"d": 128.0, "h": 222.0}, translate=(0.0, 0.0, 124.0), comment="PT420 300K reservoir"),
        ScadFeature("add_cylinder", {"d": 80.0, "h": 141.5}, translate=(0.0, 0.0, -71.25), comment="45 K 1st stage"),
        ScadFeature("add_cylinder", {"d": 48.0, "h": 100.5}, translate=(0.0, 0.0, -192.75), comment="4.2 K 2nd stage"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=3200.0)


def _build_s6_1_02() -> BuiltPart:
    """S6.1-02: Floor-mounted water-cooled Cryomech CPA He compressor package."""
    # World origin: (-1950, -800, 340) -> x=[-2190,-1710], y=[-1060,-540], z=[0,680]
    dx, dy, dz = 480.0, 520.0, 680.0
    wall = 4.0
    parts: list[SolidMesh] = []
    # Hollow welded steel cabinet walls (0.4 mm clean non-welding seam to base & top)
    parts.append(make_hollow_frame(dx, dy, dx - 2 * wall, dy - 2 * wall, dz - 52.6, center=(0.0, 0.0, 6.1), name="cpa_shell", material="Steel"))
    # Top deck (z=[+320.2, +328.2]) + bottom baseplate (z=[-320.0, -308.0])
    parts.append(make_box(dx, dy, 8.0, center=(0.0, 0.0, 0.5 * dz - 15.8), name="cpa_top", material="Steel"))
    parts.append(make_box(dx, dy, 12.0, center=(0.0, 0.0, -0.5 * dz + 26.0), name="cpa_base", material="Steel"))
    # 4x heavy-duty vibration-damping floor feet (z_local = [-340, -320])
    for sx in (-190.0, 190.0):
        for sy in (-210.0, 210.0):
            parts.append(make_cylinder(26.0, 19.5, segments=16, center=(sx, sy, -0.5 * dz + 9.75), name="cpa_foot", material="Steel"))
    # Internal scroll compressor core + water heat exchanger cylinder
    parts.append(make_cylinder(110.0, 380.0, segments=24, center=(-60.0, 0.0, -40.0), name="cpa_motor_core", material="Steel"))
    parts.append(make_cylinder(65.0, 340.0, segments=20, center=(120.0, 0.0, -40.0), name="cpa_oil_sep", material="316LN"))
    # Top Aeroquip He supply/return + cooling water inlet/outlet fittings (z_local = [+328, +340])
    for fx, fname in ((-120.0, "he_sup"), (-60.0, "he_ret"), (60.0, "h2o_in"), (120.0, "h2o_out")):
        parts.append(make_cylinder(14.0, 11.5, segments=16, center=(fx, 0.0, 0.5 * dz - 5.75), name=fname, material="316LN"))

    mesh = merge_solids(parts, name="S6.1-02", material="Steel")
    ports = (
        PortInterface("he_supply", "gas", (-120.0, 0.0, 340.0), (0.0, 0.0, 1.0), "Aeroquip 1/2-in 20 bar He", mating_part_id="S6.9-01", bore_mm=16.0, od_mm=28.0),
        PortInterface("he_return", "gas", (-60.0, 0.0, 340.0), (0.0, 0.0, 1.0), "Aeroquip 1/2-in LP He", mating_part_id="S6.9-01", bore_mm=16.0, od_mm=28.0),
        PortInterface("chilled_water_in", "cooling", (60.0, 0.0, 340.0), (0.0, 0.0, 1.0), "1/2-in BSPP Chilled Water", bore_mm=12.7, od_mm=28.0),
        PortInterface("chilled_water_out", "cooling", (120.0, 0.0, 340.0), (0.0, 0.0, 1.0), "1/2-in BSPP Chilled Water", bore_mm=12.7, od_mm=28.0),
    )
    design = make_part_design_from_bom(
        "S6.1-02",
        material="Steel",
        world_origin_mm=(-1950.0, -800.0, 340.0),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH", dx, 2.0, -2.0),
            DimensionCallout("DEPTH", dy, 2.0, -2.0),
            DimensionCallout("HEIGHT", dz, 2.0, -2.0),
        ),
        gdt_frames=(GDTFrame("flatness", 0.50, datum_primary="A", feature_note="Floor leveling plane"),),
        scad_params=(("cpa_w", dx), ("cpa_d", dy), ("cpa_h", dz), ("he_pressure_bar", 20.0)),
        target_mass_kg=165.0,
    )
    feats = (
        ScadFeature("add_box", {"dx": dx, "dy": dy, "dz": dz - 20.0}, translate=(0.0, 0.0, 10.0), comment="CPA water-cooled He compressor cabinet"),
        ScadFeature("add_cylinder", {"d": 28.0, "h": 12.0}, translate=(-120.0, 0.0, 334.0), comment="He HP supply coupling"),
        ScadFeature("add_cylinder", {"d": 28.0, "h": 12.0}, translate=(-60.0, 0.0, 334.0), comment="He LP return coupling"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=5200.0)


def _build_s6_1_03() -> BuiltPart:
    """S6.1-03: 50 K / 4 K vibration-decoupled braided OFHC Cu thermal links."""
    # World origin: (-650, 0, 802.0)
    # 50K straps: z_global = [855.5, 868.5] -> z_local = [+53.5, +66.5], radially from R=42 to R=84 (4x at 25,115,205,295 deg)
    # 4K straps:  z_global = [737.0, 749.0] -> z_local = [-65.0, -53.0], radially from R=26 to R=68 (4x at 45,135,225,315 deg)
    parts: list[SolidMesh] = []
    feats: list[ScadFeature] = []
    for idx, ang_deg in enumerate((25.0, 115.0, 205.0, 295.0)):
        rad = math.radians(ang_deg)
        br = make_s_braid(
            length_mm=34.0, s_amplitude_mm=3.5, width_mm=10.0, thickness_mm=2.2,
            n_steps=20, lug_length_mm=0.0, axis="x", name=f"braid_50k_{idx}", material="OFHC Cu"
        )
        lug_i = make_box(5.8, 12.5, 4.8, center=(-20.1, 0.0, 0.0), name=f"lug50i_{idx}", material="OFHC Cu")
        lug_o = make_box(5.8, 12.5, 4.8, center=(+20.1, 0.0, 0.0), name=f"lug50o_{idx}", material="OFHC Cu")
        cx, cy = 63.0 * math.cos(rad), 63.0 * math.sin(rad)
        for piece in (br, lug_i, lug_o):
            parts.append(transform_mesh(piece, rotation_deg=(0.0, 0.0, ang_deg), translation=(cx, cy, 60.0)))
        feats.append(
            ScadFeature("add_box", {"dx": 46.0, "dy": 12.5, "dz": 9.5}, translate=(cx, cy, 60.0), rotate=(0.0, 0.0, ang_deg), comment=f"50K OFHC thermal braid #{idx+1}")
        )
    for idx, ang_deg in enumerate((45.0, 135.0, 225.0, 315.0)):
        rad = math.radians(ang_deg)
        br = make_s_braid(
            length_mm=32.0, s_amplitude_mm=3.2, width_mm=9.0, thickness_mm=2.0,
            n_steps=20, lug_length_mm=0.0, axis="x", name=f"braid_4k_{idx}", material="OFHC Cu"
        )
        lug_i = make_box(5.8, 11.2, 4.4, center=(-19.1, 0.0, 0.0), name=f"lug4i_{idx}", material="OFHC Cu")
        lug_o = make_box(5.8, 11.2, 4.4, center=(+19.1, 0.0, 0.0), name=f"lug4o_{idx}", material="OFHC Cu")
        cx, cy = 47.0 * math.cos(rad), 47.0 * math.sin(rad)
        for piece in (br, lug_i, lug_o):
            parts.append(transform_mesh(piece, rotation_deg=(0.0, 0.0, ang_deg), translation=(cx, cy, -59.0)))
        feats.append(
            ScadFeature("add_box", {"dx": 44.0, "dy": 11.2, "dz": 8.8}, translate=(cx, cy, -59.0), rotate=(0.0, 0.0, ang_deg), comment=f"4K OFHC thermal braid #{idx+1}")
        )

    mesh = merge_solids(parts, name="S6.1-03", material="OFHC Cu")
    ports = (
        PortInterface("pt420_45k_ring", "thermal", (0.0, 0.0, 60.0), (0.0, 0.0, -1.0), "4x Au-OFHC M6 Clamp", mating_part_id="S6.1-01", od_mm=170.0),
        PortInterface("pt420_4k_ring", "thermal", (0.0, 0.0, -59.0), (0.0, 0.0, -1.0), "4x Au-OFHC M6 Clamp", mating_part_id="S6.8-01", od_mm=138.0),
    )
    design = make_part_design_from_bom(
        "S6.1-03",
        material="OFHC Cu",
        world_origin_mm=(DR_X_MM, DR_Y_MM, 802.0),
        ports=ports,
        dimensions=(
            DimensionCallout("SPAN_50K", 46.0, 0.5, -0.5),
            DimensionCallout("SPAN_4K", 44.0, 0.5, -0.5),
            DimensionCallout("STG_DZ", 119.0, 0.5, -0.5),
        ),
        gdt_frames=(GDTFrame("flatness", 0.02, datum_primary="A", feature_note="Au-plated clamp lug faces"),),
        scad_params=(("n_braids_50k", 4), ("n_braids_4k", 4), ("rrr_min", 200)),
        target_mass_kg=0.85,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_2_01() -> BuiltPart:
    """S6.2-01: Local 20 mK OFHC Cu cold island chuck (PCD=96 mm, Ø34.5 boss pocket) + staged radial-flexure Vespel truss."""
    # World origin: (0, 0, 483.0)
    # OBS-017 & OBS-010 & OBS-041 fix:
    # - Recessed Ø34.5 mm central thermal boss pocket (r_in=17.25 mm, depth 2.0 mm) mating S3.1-03 Ø34.0 mm AlN boss!
    # - Canonical PCD=96.0 mm (8x M3) + 4x radial-slot Ti-6Al-4V kinematic flexure washers relieving 126 um Cu-AlN shear!
    # - Monolithic e-beam-welded -X braid interface boss mating S6.9-03 8x parallel Cu braids (zero bolted Kapitza joint!).
    # - 4x thin-walled (OD=4.0/ID=3.2 mm) thermally-intercepted Vespel SP-22 tubular struts on radial Ti blade flexures:
    #   cuts 300K->20mK strut heat leak from 1317 mW to <0.2-4 uW & Cu-Invar cooldown shear from 355.6 N to <15 N!
    parts: list[SolidMesh] = []
    # Lower main OFHC Cu chuck base ring (z_local=[+3.0, +8.55], R=8.0..58.0, 8x M3 @ PCD 96.0 mm)
    chuck_base = make_ring_with_bolt_circle(
        r_in=8.0,
        r_out=58.0,
        thickness=5.55,
        pcd=96.0,
        n_bolts=8,
        bolt_diameter=3.4,
        sub_per_side=2,
        axis="z",
        center=(0.0, 0.0, 5.775),
        name="cold_island_chuck_base",
        material="OFHC Cu",
    )
    # Upper stepped rim forming recessed Ø34.5 mm (r_in=17.25 mm) AlN thermal boss pocket (z_local=[+8.6, +10.6])
    chuck_pocket_rim = make_ring_with_bolt_circle(
        r_in=17.25,
        r_out=58.0,
        thickness=2.0,
        pcd=96.0,
        n_bolts=8,
        bolt_diameter=3.4,
        sub_per_side=2,
        axis="z",
        center=(0.0, 0.0, 9.6),
        name="cold_island_boss_pocket_rim",
        material="OFHC Cu",
    )
    parts.extend([chuck_base, chuck_pocket_rim])
    # -X monolithic electron-beam-welded OFHC Cu braid lug facing S6.9-03 (x_global=[-61.0, -58.1], z_global=[486.5, 493.5])
    parts.append(
        make_rect_plate_with_features(
            2.9,
            26.0,
            7.0,
            circular_holes=(),
            axis="z",
            center=(-59.55, 0.0, 7.0),
            name="cold_island_ebw_braid_lug",
            material="OFHC Cu",
        )
    )
    # 4x thin-walled thermally-intercepted Vespel SP-22 tubular struts + 4K/Still intercept collars + radial Ti blade flexures
    feats: list[ScadFeature] = [
        ScadFeature("add_tube", {"od": 116.0, "id": 16.0, "h": 5.55}, translate=(0.0, 0.0, 5.775), comment="20 mK Au-OFHC cold island base"),
        ScadFeature("add_tube", {"od": 116.0, "id": 34.5, "h": 2.0}, translate=(0.0, 0.0, 9.6), comment="Recessed Ø34.5 mm AlN thermal boss pocket"),
        ScadFeature("cut_bolt_circle", {"pcd": 96.0, "bolt_d": 3.4, "count": 8, "h": 10.0}, translate=(0.0, 0.0, 6.8), comment="8x M3 kinematic clamp bolts @ PCD=96.0 mm"),
    ]
    for idx, (tx, ty) in enumerate(((-32.0, -32.0), (32.0, -32.0), (32.0, 32.0), (-32.0, 32.0)), start=1):
        # Thin-walled Vespel SP-22 tube (r_in=1.6, r_out=2.0 -> 0.4 mm wall, A_tot=18.1 mm^2, 14x lower A than solid Ø9!)
        parts.append(
            make_tube(
                r_in=1.6,
                r_out=2.0,
                height=14.3,
                segments=20,
                axis="z",
                center=(tx, ty, -4.35),
                name=f"vespel_thinwall_strut_{idx}",
                material="Vespel SP-22",
            )
        )
        # Mid-height 4 K / 0.8 K thermal intercept collar ring on each strut
        parts.append(
            make_tube(
                r_in=2.1,
                r_out=3.8,
                height=2.4,
                segments=16,
                axis="z",
                center=(tx, ty, -4.35),
                name=f"strut_thermal_intercept_{idx}",
                material="OFHC Cu",
            )
        )
        # Radial-compliance Ti-6Al-4V flexure hinge collar at top & bottom (relieves 129 um Cu-Invar cooldown strain!)
        parts.append(
            make_tube(
                r_in=2.1,
                r_out=4.5,
                height=2.2,
                segments=16,
                axis="z",
                center=(tx, ty, 1.7),
                name=f"ti_flexure_top_{idx}",
                material="Ti-6Al-4V",
            )
        )
        parts.append(
            make_tube(
                r_in=2.1,
                r_out=4.5,
                height=2.2,
                segments=16,
                axis="z",
                center=(tx, ty, -10.4),
                name=f"ti_flexure_bot_{idx}",
                material="Ti-6Al-4V",
            )
        )
        feats.append(
            ScadFeature("add_tube", {"od": 4.0, "id": 3.2, "h": 14.3}, translate=(tx, ty, -4.35), comment=f"Thin-walled Vespel SP-22 flexure strut #{idx}")
        )

    mesh = merge_solids(parts, name="S6.2-01", material="OFHC Cu")
    ports = (
        PortInterface("wafer_carrier_seat", "thermal", (0.0, 0.0, 10.6), (0.0, 0.0, 1.0), "8x M3 Kinematic Au-OFHC Seat + Ø34.5 Boss Pocket", mating_part_id="S3.1-03", bore_mm=34.5, od_mm=116.0, pcd_mm=96.0, bolt_count=8, bolt_hole_mm=3.4, bolt_spec="M3"),
        PortInterface("braid_clamp_west", "thermal", (-61.0, 0.0, 7.0), (-1.0, 0.0, 0.0), "Monolithic E-Beam-Welded OFHC Braid Lug", mating_part_id="S6.9-03", od_mm=26.0),
        PortInterface("stage_kinematic_base", "mechanical", (0.0, 0.0, -11.5), (0.0, 0.0, -1.0), "4x Radial-Flexure Staged Vespel Struts", mating_part_id="S4.3-01", pcd_mm=90.51, bolt_count=4),
    )
    design = make_part_design_from_bom(
        "S6.2-01",
        material="OFHC Cu",
        world_origin_mm=(0.0, 0.0, 483.0),
        ports=ports,
        dimensions=(
            DimensionCallout("CHUCK_OD", 116.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("BOSS_POCKET_ID", 34.5, 0.03, -0.00, prefix="Ø"),
            DimensionCallout("CHUCK_H", 7.6, 0.02, -0.02),
            DimensionCallout("TRUSS_H", 14.3, 0.05, -0.05),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.005, datum_primary="A", feature_note="Top thermal seating plane & Ø34.5 pocket"),
            GDTFrame("parallelism", 0.010, datum_primary="A", feature_note="Radial-flexure Vespel mounting plane"),
        ),
        notes=(
            "OBS-017 fix: Canonical PCD=96.0 mm mating S3.1-03 + recessed Ø34.5 mm AlN boss pocket + radial Ti flexures (<15 N cooldown force, <8 MPa vs 70 MPa Cu yield).",
            "OBS-010/041 fix: Thin-walled thermally-intercepted Vespel SP-22 tubular struts (OD=4.0/ID=3.2 mm, 4K/0.8K intercept -> <4 uW @ 20 mK) + monolithic e-beam-welded -X braid boss.",
        ),
        scad_params=(("chuck_od", 116.0), ("boss_pocket_id", 34.5), ("bolt_pcd", 96.0), ("chuck_h", 7.6), ("vespel_od", 4.0), ("vespel_id", 3.2), ("vespel_h", 14.3)),
        target_mass_kg=0.72,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_2_02() -> BuiltPart:
    """S6.2-02: Nested 50 K / 4 K / Still DR & In-Chamber UHV Radiation/Cryopump Shields + Ø46/52 4 K Bridge Tube."""
    # World origin: (-650.0, 0.0, 535.0)
    # OBS-010, OBS-040, OBS-046, OBS-065 fixes:
    # 1. Enlarged horizontal 4 K bridge radiation-shield tube: ID=46.0 mm (>=45 mm!), OD=52.0 mm, plus twin 4 K OFHC
    #    thermal bus straps (>1020 mm^2 total 4 K cross-section feeding S6.3-01 magnet & 4 K chamber shroud!).
    # 2. Extended nested 50 K (Au-Al6061, R=177.5..179.5) & 4 K (Au-OFHC Cu, R=66..68 upper/lower + R=135.5..137.5
    #    equatorial shroud + Ø20 mm cold ion-beam shutter trap) UHV shields around the wafer/chuck & 4.2 K magnet
    #    inside S5.1-01 -> slashes 20 mK radiation from 1.8 W to <0.3 uW, 4.2 K magnet rad from 28 W to 0.004 W,
    #    and cryo-pumps condensables (<0.05 ML/8h wafer frost)!
    z0 = 535.0
    parts: list[SolidMesh] = []

    def _add_shield(r_in: float, r_out: float, z_bot_g: float, z_top_g: float, tag: str, mat: str, cut_optq: bool = False) -> None:
        parts.append(make_cylinder(r_out, 4.5, segments=48, center=(0.0, 0.0, z_bot_g - 2.5 - z0), name=f"{tag}_bot_cap", material=mat))
        # Lower cylinder up to widened CF100 bridge port (z_global = 436.0)
        h_lo = 435.5 - z_bot_g
        parts.append(make_tube(r_in, r_out, h_lo, segments=48, center=(0.0, 0.0, z_bot_g + 0.5 * h_lo - z0), name=f"{tag}_lower", material=mat))
        # Widened bridge port arc (z_global = [436.0, 551.0], open on +X for Ø52 4K tube + CF100 bridge)
        parts.append(make_arc_tube(r_in, r_out, 114.5, 28.0, 332.0, center=(0.0, 0.0, 493.5 - z0), name=f"{tag}_port_arc", material=mat))
        if cut_optq and z_top_g > 730.0:
            parts.append(make_tube(r_in, r_out, 98.0, segments=48, center=(0.0, 0.0, 600.5 - z0), name=f"{tag}_mid", material=mat))
            parts.append(make_arc_tube(r_in, r_out, 79.5, -155.0, 155.0, center=(0.0, 0.0, 690.0 - z0), name=f"{tag}_optq_arc", material=mat))
            h_hi = z_top_g - 730.5
            parts.append(make_tube(r_in, r_out, h_hi, segments=48, center=(0.0, 0.0, 730.5 + 0.5 * h_hi - z0), name=f"{tag}_upper", material=mat))
        else:
            h_hi = z_top_g - 551.5
            parts.append(make_tube(r_in, r_out, h_hi, segments=48, center=(0.0, 0.0, 551.5 + 0.5 * h_hi - z0), name=f"{tag}_upper", material=mat))

    _add_shield(150.0, 154.0, 220.0, 839.0, "shield_50k", "Al 6061", cut_optq=True)
    parts.append(make_tube(155.5, 158.0, 200.0, segments=48, center=(0.0, 0.0, 330.0 - z0), name="mli_50k_lower", material="PTFE"))
    parts.append(make_tube(155.5, 158.0, 88.0, segments=48, center=(0.0, 0.0, 600.0 - z0), name="mli_50k_mid", material="PTFE"))
    parts.append(make_tube(155.5, 158.0, 96.0, segments=48, center=(0.0, 0.0, 785.0 - z0), name="mli_50k_upper", material="PTFE"))
    _add_shield(132.0, 136.0, 250.0, 719.0, "shield_4k", "OFHC Cu", cut_optq=False)
    _add_shield(116.0, 119.0, 276.0, 603.0, "shield_still", "OFHC Cu", cut_optq=False)

    # Enlarged horizontal 4 K radiation-shield thermal-bridge tube (ID=46.0 mm >= 45 mm, OD=52.0 mm!)
    # x_global = [-513.0, -76.0] -> x_local = [+137.0, +574.0] (1.5 mm clear of ch_4k_lower_cryoshroud at 575.5!), length = 437.0, center x_local = +355.5
    parts.append(
        make_tube(
            r_in=23.0,
            r_out=26.0,
            height=437.0,
            segments=36,
            axis="x",
            center=(355.5, 0.0, Z_CRYO_BRIDGE_MM - z0),
            name="bridge_4k_shield_tube",
            material="OFHC Cu",
        )
    )
    # Twin parallel 4 K OFHC Cu thermal busbar rails (2 x 280 mm^2 + 462 mm^2 tube = 1022 mm^2 to 4.2 K magnet & shroud!)
    # Positioned inside CF100 bellows (R_in=38 mm) starting at x_local=151.0 (2.0 mm clear of shutter ring at 149.0!)
    for sgn, btag in ((-1.0, "bot"), (1.0, "top")):
        parts.append(
            make_box(
                351.5, 20.0, 7.0,
                center=(326.75, 0.0, Z_CRYO_BRIDGE_MM - z0 + sgn * 30.5),
                name=f"busbar_4k_magnet_{btag}",
                material="OFHC Cu",
            )
        )
    # Beam-port thermal shutter ring mounted cleanly at 4 K shield +X port throat (x_global = -504.0, R=27.5..36.0 mm -> 0.97 mm chord clearance!)
    parts.append(
        make_ring_with_bolt_circle(
            r_in=27.5,
            r_out=36.0,
            thickness=6.0,
            pcd=63.5,
            n_bolts=8,
            bolt_diameter=3.2,
            sub_per_side=2,
            axis="x",
            center=(146.0, 0.0, Z_CRYO_BRIDGE_MM - z0),
            name="beam_port_thermal_shutter",
            material="OFHC Cu",
        )
    )

    # --- IN-CHAMBER NESTED 50 K & 4 K RADIATION & CRYOPUMPING SHIELDS (centered at chamber X=0 -> x_local=+650.0) ---
    cx_ch = -DR_X_MM  # +650.0 mm
    # A) Outer 50 K Au-Al6061 chamber radiation shield (R=177.5..179.5 mm -> 2.5 mm inside S5.1-01, 1.5 mm outside S6.3-01!)
    # Lower 50 K baffle ring (Z=[292, 336])
    parts.append(make_tube(177.5, 179.5, 44.0, segments=48, center=(cx_ch, 0.0, 314.0 - z0), name="ch_50k_lower_ring", material="Al 6061"))
    # Lower port-belt 50 K shield arcs (Z=[337, 412]) clearing 0/45/90/225/270/315 deg optical/IBIC/gauge ports
    for tag, d0, d1 in (("ene", 11.0, 31.0), ("nne", 59.0, 79.0), ("nw", 101.0, 214.0), ("ese", 329.0, 349.0)):
        parts.append(make_arc_tube(177.5, 179.5, 75.0, d0, d1, center=(cx_ch, 0.0, 374.5 - z0), name=f"ch_50k_lo_{tag}", material="Al 6061"))
    # Equatorial & upper 50 K shield arcs (Z=[413, 620]) clearing 0 deg LL, 50 deg fiducial, 180 deg bridge, 270 deg -Y CF150 pump
    for tag, d0, d1 in (("ene", 20.0, 37.0), ("nw", 63.0, 159.0), ("sw", 201.0, 240.0), ("ese", 300.0, 340.0)):
        parts.append(make_arc_tube(177.5, 179.5, 207.0, d0, d1, center=(cx_ch, 0.0, 516.5 - z0), name=f"ch_50k_eq_{tag}", material="Al 6061"))
    # Top 50 K chamber radiation baffle collar (Z=[621, 624], R=[64, 179.5], open for ion beam & column!)
    parts.append(make_tube(64.0, 179.5, 3.0, segments=48, center=(cx_ch, 0.0, 622.5 - z0), name="ch_50k_top_baffle", material="Al 6061"))
    # 4x low-k G10-CR 50 K chamber shield standoffs (R=178.5, Z=[286.5, 291.5])
    for idx, ang_deg in enumerate((25.0, 115.0, 205.0, 325.0), start=1):
        rad = math.radians(ang_deg)
        parts.append(make_cylinder(2.5, 4.8, segments=10, center=(cx_ch + 178.5 * math.cos(rad), 178.5 * math.sin(rad), 289.0 - z0), name=f"ch_50k_g10_foot_{idx}", material="G10"))

    # B) Inner 4 K Au-OFHC Cu wafer/head radiation & cryopumping shroud (OBS-010 & OBS-046!)
    # Upper 4 K cryo-shroud around S2 write head (R=66.0..68.0, Z=[505.5, 579.5] -> >2.1 mm outside S2, >2.5 mm above S3.2-04!)
    # Open at 36..64 deg for 50 deg fiducial optical cone AND 240..300 deg for -Y CF150 pump throat (OBS-107)!
    parts.append(make_arc_tube(66.0, 68.0, 74.0, 64.0, 240.0, center=(cx_ch, 0.0, 542.5 - z0), name="ch_4k_upper_cryoshroud_nw", material="OFHC Cu"))
    parts.append(make_arc_tube(66.0, 68.0, 74.0, 300.0, 396.0, center=(cx_ch, 0.0, 542.5 - z0), name="ch_4k_upper_cryoshroud_e", material="OFHC Cu"))
    # Top 4 K cold-shutter ion-beam trap collar (Z=[580.0, 582.5], R=[56.0, 68.0] -> seals annulus around S1.3-04 R<=54 with 2.0 mm clearance!)
    parts.append(make_tube(56.0, 68.0, 2.5, segments=48, center=(cx_ch, 0.0, 581.25 - z0), name="ch_4k_top_cold_trap_lid", material="OFHC Cu"))
    # Lower 4 K cryo-shroud below S3.2-01 (R=72.5..74.5, Z=[452.0, 480.5] -> 3.0 mm outside S4.3-03 R=69.5, >2.2 mm below S3.2-01!)
    parts.append(make_tube(72.5, 74.5, 28.5, segments=48, center=(cx_ch, 0.0, 466.25 - z0), name="ch_4k_lower_cryoshroud", material="OFHC Cu"))
    # Equatorial 4 K CSA-enclosing cryopump baffle arcs (R=148.0..150.0, Z=[472.0, 514.0] -> 7 mm clear of S3.2-01 & S4.4-02 & S6.3-01!)
    for tag, d0, d1 in (("ne", 64.0, 82.0), ("nw", 98.0, 146.0), ("sw", 214.0, 234.0), ("se", 306.0, 326.0)):
        parts.append(make_arc_tube(148.0, 150.0, 42.0, d0, d1, center=(cx_ch, 0.0, 493.0 - z0), name=f"ch_4k_eq_baffle_{tag}", material="OFHC Cu"))

    mesh = merge_solids(parts, name="S6.2-02", material="OFHC Cu")
    ports = (
        PortInterface("shield_50k_mount", "thermal", (0.0, 0.0, 304.0), (0.0, 0.0, 1.0), "12x M5 Al-6061 Flange", mating_part_id="S6.8-01", bore_mm=300.0, od_mm=308.0),
        PortInterface("shield_4k_mount", "thermal", (0.0, 0.0, 184.0), (0.0, 0.0, 1.0), "12x M4 Au-OFHC Flange", mating_part_id="S6.8-01", bore_mm=264.0, od_mm=272.0),
        PortInterface("shield_still_mount", "thermal", (0.0, 0.0, 68.0), (0.0, 0.0, 1.0), "8x M4 Au-OFHC Flange", mating_part_id="S6.8-01", bore_mm=232.0, od_mm=238.0),
        PortInterface("bridge_4k_shroud", "thermal", (580.0, 0.0, Z_CRYO_BRIDGE_MM - z0), (1.0, 0.0, 0.0), "Ø46/Ø52 4K Bridge Tube + 1022 mm^2 4K Bus", mating_part_id="S6.9-02", bore_mm=46.0, od_mm=52.0),
        PortInterface("chamber_4k_cold_trap_ap", "vacuum", (cx_ch, 0.0, 582.5 - z0), (0.0, 0.0, 1.0), "Ø20 mm 4 K Ion-Beam Cold Trap Aperture", mating_part_id="S5.1-01", bore_mm=20.0, od_mm=136.0),
    )
    design = make_part_design_from_bom(
        "S6.2-02",
        material="OFHC Cu",
        world_origin_mm=(DR_X_MM, DR_Y_MM, z0),
        ports=ports,
        dimensions=(
            DimensionCallout("SHIELD50K_OD", 308.0, 0.2, -0.2, prefix="Ø"),
            DimensionCallout("SHIELD4K_OD", 272.0, 0.2, -0.2, prefix="Ø"),
            DimensionCallout("STILL_OD", 238.0, 0.2, -0.2, prefix="Ø"),
            DimensionCallout("BRIDGE_4K_ID", 46.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("BRIDGE_4K_OD", 52.0, 0.05, -0.05, prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.20, diameter_zone=True, datum_primary="B", feature_note="50K/4K/Still nested DR & in-chamber shields"),
            GDTFrame("perpendicularity", 0.10, diameter_zone=True, datum_primary="A", feature_note="Top bolt flange face"),
        ),
        notes=(
            "OBS-010/040/046 fix: Nested in-chamber 50 K (R=177.5..179.5) and 4 K (R=66..68 + R=135.5..137 + Ø20 cold trap) radiation & cryopumping shields reduce 20 mK rad load to <0.3 uW, 4.2 K magnet rad load to 0.004 W, and wafer cryo-frost to <0.05 ML/8h.",
            "OBS-065 fix: Enlarged 4 K bridge tube ID=46.0 mm (>=45 mm), OD=52.0 mm + twin 4 K OFHC bus straps (1022 mm^2 total to PT420 4 K stage), clearing Ø30 mm S6.9-03 rod + 88 mm^2 braids by >=4.5 mm.",
        ),
        scad_params=(
            ("r50_in", 150.0), ("r50_out", 154.0), ("r4_in", 132.0), ("r4_out", 136.0),
            ("rstill_in", 116.0), ("rstill_out", 119.0), ("bridge_4k_id", 46.0), ("bridge_4k_od", 52.0),
            ("ch_50k_r_out", 179.5), ("ch_4k_r_in", 66.0), ("ch_4k_cold_ap_mm", 20.0),
        ),
        target_mass_kg=24.5,
    )
    feats = (
        ScadFeature("add_tube", {"od": 308.0, "id": 300.0, "h": 619.0}, translate=(0.0, 0.0, -5.5), comment="50 K Al-6061 DR shield"),
        ScadFeature("add_tube", {"od": 272.0, "id": 264.0, "h": 469.0}, translate=(0.0, 0.0, -50.5), comment="4 K Au-OFHC DR shield"),
        ScadFeature("add_tube", {"od": 238.0, "id": 232.0, "h": 327.0}, translate=(0.0, 0.0, -95.5), comment="Still 0.8 K Au-OFHC DR shield"),
        ScadFeature("add_tube", {"od": 52.0, "id": 46.0, "h": 443.0}, translate=(358.5, 0.0, Z_CRYO_BRIDGE_MM - z0), rotate=(0.0, 90.0, 0.0), comment="Enlarged Ø46/52 4 K cryo-bridge shield tube"),
        ScadFeature("add_tube", {"od": 359.0, "id": 355.0, "h": 328.0}, translate=(cx_ch, 0.0, 456.0 - z0), comment="In-chamber 50 K radiation shield"),
        ScadFeature("add_tube", {"od": 136.0, "id": 132.0, "h": 74.0}, translate=(cx_ch, 0.0, 542.5 - z0), comment="In-chamber 4 K wafer/head cryopumping shroud"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=3600.0)


def _build_s6_2_03() -> BuiltPart:
    """S6.2-03: Lake Shore 372/336 cryogenic thermometry & PID heater controller (2U, Bay 2 U4..U5)."""
    zc, dz = rack_u_center_and_height(4, 2)
    mesh, feats = make_rack_chassis_19in(420.0, dz, n_subunits=1, n_front_ports=8, material="Al 6061", name="S6.2-03")
    ports = (
        PortInterface("sensor_inputs_8ch", "connector", (0.0, 210.0, 0.0), (0.0, 1.0, 0.0), "8x 6-pin DIN Cernox/RuO2", mating_part_id="S6.8-04"),
        PortInterface("rack_bay2_u4_u5", "mechanical", (0.0, -210.0, 0.0), (0.0, -1.0, 0.0), '19" EIA-310 2U (U4-U5)', mating_part_id="S7.4-03"),
    )
    design = make_part_design_from_bom(
        "S6.2-03",
        material="Al 6061",
        world_origin_mm=(RACK_BAY2_X_MM, RACK_BAY2_Y_MM, zc),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5),
            DimensionCallout("DEPTH", 420.0, 1.0, -1.0),
            DimensionCallout("HEIGHT_2U", dz, 0.3, -0.3),
        ),
        scad_params=(("rack_u", 2), ("bay", 2), ("u_start", 4), ("channels", 8)),
        target_mass_kg=7.2,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_3_01() -> BuiltPart:
    """S6.3-01: Horizontal Split-Helmholtz In-Plane NbTi Magnet (B_|| <= 0.30 T), Clear -Y Pump Throat & 50 K-Staged Legs."""
    # World origin: (0, 0, 500.0) (wafer top plane Z_WAFER)
    # OBS-008, OBS-040, OBS-072, OBS-107 fixes:
    # 1. Re-oriented from vertical +Z solenoid (B_perp causing Abrikosov vortex collapse in on-chip NbTiN M4
    #    resonators) to HORIZONTAL SPLIT-HELMHOLTZ IN-PLANE PAIR along +-X (B_x = B_|| <= 0.30 T, M4 nom 0.1785 T,
    #    |B_perp| < 0.05 mT << 0.853 mT vortex threshold!).
    # 2. Horizontal split-Helmholtz coils at x = +-[138.0, 160.0], R_yz = [52.0, 72.0] (Ø104 mm clear X-bore for
    #    both -X Ø52 mm 4K bridge tube AND +X wafer transfer!; max radial envelope sqrt(160^2+72^2)=175.45 <= 176 mm!).
    # 3. Leaves -Y CF150 pump port throat (|X| <= 76 mm) & 50 deg fiducial cone 100% UNOCCLUDED (0% vs 63.2%!).
    # 4. Upper/lower Ø352 mm Ti-6Al-4V structural former & in-plane saddle-shim rings at z_loc = +-[76.0, 108.0]
    #    (notched open at 236..304 deg for -Y pump & 38..62 deg for 50 deg fiducial) + 4x heavy Lorentz tie-rods!
    # 5. 4x two-stage 50 K-intercepted thin-walled G10-CR tubular support legs (OD=16/ID=14 mm, wall=1.0 mm)
    #    slashing 4.2 K conductive load from 12.51 W to 0.034 W (total 4.2 K load ~0.2 W << 2.0 W PT420!).
    parts: list[SolidMesh] = []

    # 1. Primary Horizontal Split-Helmholtz In-Plane NbTi Coil Pair along +-X (B_|| <= 0.30 T across wafer!)
    for sgn, tag in ((-1.0, "west"), (1.0, "east")):
        # Machined Ti-6Al-4V bobbin + NbTi winding pack (x_loc = +-[138.0, 160.0], R_yz = [52.0, 72.0])
        h_prof = [
            (52.0, 0.0), (72.0, 0.0), (72.0, 2.5), (70.0, 2.5),
            (70.0, 19.5), (72.0, 19.5), (72.0, 22.0), (52.0, 22.0),
        ]
        x_start = 138.0 if sgn > 0 else -160.0
        parts.append(
            make_revolved_profile(
                h_prof, segments=48, axis="+x", center=(x_start, 0.0, 0.0),
                name=f"helmholtz_inplane_coil_{tag}", material="NbTi",
            )
        )
        # Rigid structural Ti-6Al-4V cheek tie-flanges anchoring each Helmholtz coil to upper/lower Ø352 former rings (0.2-0.3 mm clean seam!)
        for zsgn, ztag in ((-1.0, "bot"), (1.0, "top")):
            parts.append(
                make_box(
                    18.0, 26.0, 6.0,
                    center=(sgn * 149.0, 0.0, zsgn * 75.3),
                    name=f"helmholtz_tie_gusset_{tag}_{ztag}",
                    material="Ti-6Al-4V",
                )
            )

    # 2. Upper & Lower Symmetric Homogeneity Trim / Saddle-Shim Rings & Ø352 Structural Former (z_loc = +-[78.5, 108.5])
    # Open on -Y pump arc (236..304 deg) and 50 deg fiducial arc (38..62 deg) so ZERO optical or pump occlusion!
    for sgn, utag in ((1.0, "u"), (-1.0, "l")):
        # Inner homogeneity saddle-shim + B_perp trim coil arcs (R=76..114, z=+-[78.5, 104.5], clear of S2 R<=64!)
        parts.append(make_arc_tube(76.0, 114.0, 26.0, 62.0, 236.0, center=(0.0, 0.0, sgn * 91.5), name=f"inplane_shim_w_{utag}", material="NbTi"))
        parts.append(make_arc_tube(76.0, 114.0, 26.0, 304.0, 398.0, center=(0.0, 0.0, sgn * 91.5), name=f"inplane_shim_e_{utag}", material="NbTi"))
        # Outer Ø352 mm Ti-6Al-4V structural former rings (R=170..176 mm, z=+-[78.5, 108.5], clears S6.3-02 keys!)
        parts.append(make_arc_tube(170.0, 176.0, 30.0, 62.0, 236.0, center=(0.0, 0.0, sgn * 93.5), name=f"magnet_former_w_{utag}", material="Ti-6Al-4V"))
        parts.append(make_arc_tube(170.0, 176.0, 30.0, 304.0, 398.0, center=(0.0, 0.0, sgn * 93.5), name=f"magnet_former_e_{utag}", material="Ti-6Al-4V"))
        # Continuous bolted Lorentz structural crown rings above/below port zones (z=+-[109.0, 116.0], R=76..120 & R=169..176)
        parts.append(
            make_ring_with_bolt_circle(
                r_in=76.0, r_out=120.0, thickness=7.0, pcd=208.0, n_bolts=12, bolt_diameter=6.4,
                sub_per_side=2, axis="z", center=(0.0, 0.0, sgn * 112.5),
                name=f"lorentz_endcap_{utag}", material="Ti-6Al-4V",
            )
        )

    # 3. 4x heavy Ti-6Al-4V Lorentz tie-rods + 4x two-stage 50 K-intercepted thin-walled G10-CR support legs
    for idx, ang_deg in enumerate((32.0, 148.0, 212.0, 328.0), start=1):
        rad = math.radians(ang_deg)
        tx, ty = 172.5 * math.cos(rad), 172.5 * math.sin(rad)
        parts.append(make_cylinder(3.5, 156.0, segments=16, center=(tx, ty, 0.0), name=f"lorentz_tie_rod_{idx}", material="Ti-6Al-4V"))
    for idx, ang_deg in enumerate((45.0, 135.0, 225.0, 315.0), start=1):
        rad = math.radians(ang_deg)
        fx, fy = 156.0 * math.cos(rad), 156.0 * math.sin(rad)
        # Thin-walled G10-CR tubular legs (r_in=7.0, r_out=8.0 -> 1.0 mm wall, A_tot=188.5 mm^2)
        parts.append(make_tube(7.0, 8.0, 105.0, segments=20, center=(fx, fy, -161.5), name=f"magnet_g10_leg_{idx}", material="G10"))
        # Mid-height 50 K OFHC thermal intercept collar (slashes 4.2 K conduction to 0.034 W!)
        parts.append(make_tube(8.2, 11.5, 8.0, segments=20, center=(fx, fy, -161.5), name=f"magnet_50k_intercept_{idx}", material="OFHC Cu"))

    mesh = merge_solids(parts, name="S6.3-01", material="NbTi")
    ports = (
        PortInterface("inplane_x_bore", "mechanical", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), "Ø104 mm Horizontal In-Plane Bore (B_|| <= 0.30 T)", bore_mm=104.0, od_mm=352.0),
        PortInterface("vertical_z_bore", "mechanical", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), "Ø152 mm Vertical Write/Wafer Bore (16x16 mm <=15 ppm)", bore_mm=152.0, od_mm=352.0),
        PortInterface("pump_slot_neg_y", "vacuum", (0.0, -176.0, 0.0), (0.0, -1.0, 0.0), "100% Unoccluded -Y CF150 Pumping Channel", bore_mm=152.4),
        PortInterface("chamber_mount_feet", "bolt", (0.0, 0.0, -214.0), (0.0, 0.0, -1.0), "4x 50K-Intercepted G10-CR Tubular Legs @ R=156", mating_part_id="S5.1-01", pcd_mm=312.0, bolt_count=4, bolt_hole_mm=8.4, bolt_spec="M8"),
    )
    design = make_part_design_from_bom(
        "S6.3-01",
        material="NbTi",
        world_origin_mm=(0.0, 0.0, Z_WAFER_MM),
        ports=ports,
        dimensions=(
            DimensionCallout("BORE_Z_ID", 152.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("BORE_X_ID", 104.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("FORMER_OD", 352.0, 0.10, -0.10, prefix="Ø"),
            DimensionCallout("STACK_H", 232.0, 0.10, -0.10),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.020, diameter_zone=True, datum_primary="B", feature_note="Horizontal +-X split-Helmholtz in-plane coils"),
            GDTFrame("parallelism", 0.015, datum_primary="A", feature_note="In-plane B_|| alignment (<0.05 deg to wafer XY)"),
        ),
        notes=(
            "OBS-008 fix: Horizontal split-Helmholtz in-plane NbTi magnet (B_|| along +-X, 0.1785 T M4 / <=0.30 T max, |B_perp| < 0.05 mT << 0.853 mT vortex threshold), eliminating 90-deg Abrikosov vortex collapse in on-chip NbTiN resonators.",
            "OBS-040/072/107 fix: 50 K-intercepted thin-walled G10-CR legs (0.034 W @ 4.2 K vs 12.5 W; <0.25 W total << 2.0 W PT420), <=15 ppm homogeneity across 16x16 mm write field (50 mm working wafer fits Ø152 mm bore; 200 mm wafers explicitly excluded), and 0% -Y CF150 pump occlusion.",
        ),
        scad_params=(
            ("bore_id", 152.0), ("x_bore_id", 104.0), ("former_od", 352.0),
            ("b_inplane_max_t", 0.30), ("b_m4_inplane_t", 0.1785), ("b_perp_max_mt", 0.05),
            ("orientation", "HORIZONTAL_SPLIT_HELMHOLTZ_IN_PLANE_X"),
            ("homogeneous_field_mm", 16.0),
        ),
        target_mass_kg=38.5,
    )
    feats = (
        ScadFeature("add_tube", {"od": 144.0, "id": 104.0, "h": 22.0}, translate=(-149.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="-X horizontal split-Helmholtz in-plane coil"),
        ScadFeature("add_tube", {"od": 144.0, "id": 104.0, "h": 22.0}, translate=(+149.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="+X horizontal split-Helmholtz in-plane coil"),
        ScadFeature("add_tube", {"od": 228.0, "id": 152.0, "h": 26.0}, translate=(0.0, 0.0, 91.5), comment="Upper in-plane homogeneity saddle shim"),
        ScadFeature("add_tube", {"od": 228.0, "id": 152.0, "h": 26.0}, translate=(0.0, 0.0, -91.5), comment="Lower in-plane homogeneity saddle shim"),
        ScadFeature("add_tube", {"od": 352.0, "id": 338.0, "h": 30.0}, translate=(0.0, 0.0, 93.5), comment="Upper Ø352 structural former"),
        ScadFeature("add_tube", {"od": 352.0, "id": 338.0, "h": 30.0}, translate=(0.0, 0.0, -93.5), comment="Lower Ø352 structural former"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_3_02() -> BuiltPart:
    """S6.3-02: Structurally-Anchored Active Shield/Bucking Coils (A/B) with >200 kN Lorentz Tie-Flanges (ZERO floating coils)."""
    # World origin: (0, 0, 500.0)
    # OBS-072 & OBS-121 fix:
    # - A_upper/A_lower active shield bobbins at R=144..167.5, z_loc=+-[78.5, 108.5] (open at -Y 236..304 deg & 50 deg
    #   fiducial 38..62 deg!) rigidly anchored to S6.3-01 Ø352 former via 8x machined Al-Bronze Lorentz tie-flanges
    #   and radial shear brackets (rated >200 kN Lorentz load — ZERO floating coils!).
    # - B_upper/B_lower quiet-zone bucking coils at R=56..82, z_loc=[-145,-121] & [-184,-160] with 4x spacers & feet.
    parts: list[SolidMesh] = []
    for sgn, utag in ((1.0, "u"), (-1.0, "l")):
        zc = sgn * 93.5
        # Arc-slotted active shield bobbins matching S6.3-01 clear pump & fiducial windows
        parts.append(make_arc_tube(144.0, 167.5, 29.0, 62.0, 236.0, center=(0.0, 0.0, zc), name=f"a_shield_w_{utag}", material="Al-Bronze"))
        parts.append(make_arc_tube(144.0, 167.5, 29.0, 304.0, 398.0, center=(0.0, 0.0, zc), name=f"a_shield_e_{utag}", material="Al-Bronze"))
        # 4x rigid Al-Bronze Lorentz tie-flange gussets anchoring A-coil to S6.3-01 former & inner shim (0.5+ mm chord-safe seam!)
        for g_idx, ang_deg in enumerate((110.0, 165.0, 205.0, 345.0), start=1):
            rad = math.radians(ang_deg)
            gx, gy = 128.5 * math.cos(rad), 128.5 * math.sin(rad)
            gusset = make_box(28.0, 12.0, 20.0, name=f"a_lorentz_tie_bar_{utag}_{g_idx}", material="Al-Bronze")
            parts.append(transform_mesh(gusset, rotation_deg=(0.0, 0.0, ang_deg), translation=(gx, gy, zc)))
            # Outer shear-pin flange engaging S6.3-01 Ø352 former R_in=169.0 (max corner R=168.724 < 169.0 mm!)
            px, py = 168.15 * math.cos(rad), 168.15 * math.sin(rad)
            pin = make_box(1.0, 10.0, 24.0, name=f"a_outer_shear_key_{utag}_{g_idx}", material="Ti-6Al-4V")
            parts.append(transform_mesh(pin, rotation_deg=(0.0, 0.0, ang_deg), translation=(px, py, zc)))

    for tag, z_lo, z_hi in (("b_upper", -145.0, -121.0), ("b_lower", -184.0, -160.0)):
        prof_b = [
            (56.0, z_lo), (82.0, z_lo), (82.0, z_lo + 3.0), (79.5, z_lo + 3.0),
            (79.5, z_hi - 3.0), (82.0, z_hi - 3.0), (82.0, z_hi), (56.0, z_hi),
        ]
        parts.append(make_revolved_profile(prof_b, segments=48, name=f"{tag}_bobbin", material="Al-Bronze"))

    # 4x B-coil inter-coil spacers (z=[-159.5, -145.5]) & staged G10/Ti bottom feet (z=[-214.0, -184.5])
    for idx, ang_deg in enumerate((45.0, 135.0, 225.0, 315.0), start=1):
        rad = math.radians(ang_deg)
        bx, by = 69.0 * math.cos(rad), 69.0 * math.sin(rad)
        parts.append(make_cylinder(4.5, 13.8, segments=16, center=(bx, by, -152.5), name=f"b_spacer_{idx}", material="Al-Bronze"))
        parts.append(make_tube(3.2, 4.5, 29.2, segments=16, center=(bx, by, -199.3), name=f"b_foot_{idx}", material="G10"))

    mesh = merge_solids(parts, name="S6.3-02", material="Al-Bronze")
    ports = (
        PortInterface("a_former_fit", "mechanical", (0.0, 0.0, 93.5), (0.0, 0.0, 1.0), "8x Bolted Al-Bronze Lorentz Tie-Flanges (>200 kN)", mating_part_id="S6.3-01", bore_mm=288.0, od_mm=335.0),
        PortInterface("b_resonator_bore", "mechanical", (0.0, 0.0, -155.0), (0.0, 0.0, 1.0), "Ø112 mm Quiet-Zone Bore", mating_part_id="S6.3-03", bore_mm=112.0, od_mm=164.0),
    )
    design = make_part_design_from_bom(
        "S6.3-02",
        material="Al-Bronze",
        world_origin_mm=(0.0, 0.0, Z_WAFER_MM),
        ports=ports,
        dimensions=(
            DimensionCallout("A_COIL_OD", 335.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("A_COIL_ID", 288.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("B_COIL_ID", 112.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("B_COIL_OD", 164.0, 0.05, -0.05, prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.025, diameter_zone=True, datum_primary="B", feature_note="A/B bucking axis"),
            GDTFrame("perpendicularity", 0.020, diameter_zone=True, datum_primary="A", feature_note="Lorentz tie-flange shear seats"),
        ),
        notes=(
            "OBS-072 fix: 8x machined Al-Bronze radial tie-bars + Ti-6Al-4V shear keys rigidly anchor A_upper/A_lower active shield bobbins to S6.3-01 former against 15-176 kN Lorentz forces (ZERO floating coils!).",
            "Arc-slotted to preserve 0% -Y CF150 pump occlusion and 50 deg fiducial optical cone.",
        ),
        scad_params=(("a_r_in", 144.0), ("a_r_out", 167.5), ("b_r_in", 56.0), ("b_r_out", 82.0), ("n_lorentz_ties", 8), ("lorentz_rating_kn", 200.0)),
        target_mass_kg=24.0,
    )
    feats = (
        ScadFeature("add_tube", {"od": 335.0, "id": 288.0, "h": 29.0}, translate=(0.0, 0.0, 93.5), comment="Anchored A_upper active shield coil"),
        ScadFeature("add_tube", {"od": 335.0, "id": 288.0, "h": 29.0}, translate=(0.0, 0.0, -93.5), comment="Anchored A_lower active shield coil"),
        ScadFeature("add_tube", {"od": 164.0, "id": 112.0, "h": 24.0}, translate=(0.0, 0.0, -133.0), comment="B_upper bucking coil"),
        ScadFeature("add_tube", {"od": 164.0, "id": 112.0, "h": 24.0}, translate=(0.0, 0.0, -172.0), comment="B_lower bucking coil"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_3_03() -> BuiltPart:
    """S6.3-03: RF-Partitioned Nb (RRR>300) Meissner Cup + Dual-Layer 5 mm Cryoperm-10 Shield (Non-Saturating, f1 > 10.5 GHz)."""
    # World origin: (0, 0, 345.0) (Exp125 resonator quiet-zone plane z_loc = -155.0 mm)
    # OBS-072 & OBS-108 fixes:
    # 1. Dual-layer thickened Cryoperm-10 shield (t_tot = 5.0 mm: inner R=35.5..38.0 + outer R=38.5..41.0, OD=82.0 mm):
    #    2.5x wall thickness + 5x lower stray field from in-plane B_|| <= 0.30 T -> wall flux <0.20 T << 0.75 T saturation!
    # 2. Stepped superconducting Nb RF-partitioning ceiling collar + Eccosorb CR-124 absorber ring inside the Ø64 mm
    #    Nb cup (R=25.5..31.8, z=[+8.8, +16.2]) eliminating the 5.31/6.43/7.30 GHz box modes from the 4-8 GHz band!
    parts: list[SolidMesh] = []
    cup_prof = [
        (0.0, -19.0),
        (34.5, -19.0),
        (34.5, 16.5),
        (32.0, 16.5),
        (32.0, -16.5),
        (0.0, -16.5),
    ]
    parts.append(make_revolved_profile(cup_prof, segments=48, name="nb_meissner_cup", material="Nb"))
    # Stepped internal Nb RF-mode-suppressor baffle + Eccosorb CR-124 collar (clears S6.6-07 OD=50 -> R=25.0 & z<=8.5!)
    parts.append(make_tube(25.8, 31.8, 7.2, segments=48, center=(0.0, 0.0, 12.6), name="nb_rf_mode_baffle", material="Nb"))
    parts.append(make_tube(26.0, 31.8, 12.0, segments=48, center=(0.0, 0.0, -9.8), name="eccosorb_rf_damper_ring", material="Eccosorb"))
    # Bolted Nb top lid with 6x M2.5 bolt/vent holes
    parts.append(
        make_ring_with_bolt_circle(
            r_in=8.0, r_out=34.5, thickness=2.5, pcd=60.0, n_bolts=6, bolt_diameter=2.7,
            sub_per_side=2, axis="z", center=(0.0, 0.0, 17.85),
            name="nb_meissner_lid", material="Nb",
        )
    )
    parts.append(make_tube(6.0, 8.0, 10.9, segments=32, center=(0.0, 0.0, 24.65), name="nb_chimney", material="Nb"))
    # Dual-layer 5.0 mm total thickness Cryoperm-10 cylindrical sleeves (inner R=35.5..38.0 + outer R=38.5..41.0, OD=82.0!)
    parts.append(make_tube(35.5, 38.0, 56.0, segments=48, center=(0.0, 0.0, 3.0), name="cryoperm10_inner_sleeve", material="Cryoperm"))
    parts.append(make_tube(38.5, 41.0, 56.0, segments=48, center=(0.0, 0.0, 3.0), name="cryoperm10_outer_sleeve", material="Cryoperm"))
    # Cryoperm-10 vented bottom base ring with 6x Ø3.5 mm UHV pump-out vent holes
    parts.append(
        make_ring_with_bolt_circle(
            r_in=14.0, r_out=41.0, thickness=2.5, pcd=54.0, n_bolts=6, bolt_diameter=3.5,
            sub_per_side=2, axis="z", center=(0.0, 0.0, -26.35),
            name="cryoperm10_vented_base", material="Cryoperm",
        )
    )
    # 4x radial Vespel SP-22 centering spacers between Nb (R=34.5) and inner Cryoperm (R=35.5)
    for idx, ang_deg in enumerate((0.0, 90.0, 180.0, 270.0), start=1):
        rad = math.radians(ang_deg)
        sx, sy = 35.0 * math.cos(rad), 35.0 * math.sin(rad)
        parts.append(make_cylinder(0.42, 4.0, segments=10, axis="z", center=(sx, sy, -10.0), name=f"shield_spacer_{idx}", material="Vespel SP-22"))

    mesh = merge_solids(parts, name="S6.3-03", material="Nb")
    ports = (
        PortInterface("chimney_coax_port", "rf", (0.0, 0.0, 30.1), (0.0, 0.0, 1.0), "Ø12 mm Attenuating Chimney", bore_mm=12.0, od_mm=16.0),
        PortInterface("resonator_cavity", "mechanical", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), "Ø64 mm RF-Damped Quiet Zone (<5 uT)", mating_part_id="S6.6-07", bore_mm=64.0, od_mm=69.0),
        PortInterface("cryoperm_vent_base", "vacuum", (0.0, 0.0, -27.6), (0.0, 0.0, -1.0), "6x Ø3.5 mm UHV Vent Circle", bore_mm=28.0, od_mm=82.0, pcd_mm=54.0, bolt_count=6, bolt_hole_mm=3.5),
    )
    design = make_part_design_from_bom(
        "S6.3-03",
        material="Nb",
        world_origin_mm=(0.0, 0.0, 345.0),
        ports=ports,
        dimensions=(
            DimensionCallout("NB_CUP_ID", 64.0, 0.03, -0.03, prefix="Ø"),
            DimensionCallout("NB_CUP_OD", 69.0, 0.03, -0.03, prefix="Ø"),
            DimensionCallout("CRYOPERM_ID", 71.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("CRYOPERM_OD", 82.0, 0.05, -0.05, prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.025, diameter_zone=True, datum_primary="B", feature_note="Nb cup to dual Cryoperm-10"),
            GDTFrame("flatness", 0.010, datum_primary="A", feature_note="Bolted Meissner lid seam"),
        ),
        notes=(
            "OBS-072 fix: Dual-layer 5.0 mm Cryoperm-10 shield (inner R=35.5..38 + outer R=38.5..41) under in-plane B_|| <= 0.30 T keeps peak wall flux <0.20 T << 0.75 T saturation (>3.7x nonlinear margin).",
            "OBS-108 fix: Stepped Nb RF-partitioning ceiling collar + Eccosorb CR-124 absorber ring damp/push parasitic S6.3-03 cavity modes out of the 4-8 GHz readout band (f1_eff > 10.5 GHz).",
        ),
        scad_params=(("nb_r_in", 32.0), ("nb_r_out", 34.5), ("cp_r_in", 35.5), ("cp_r_out", 41.0), ("cp_t_total", 5.0), ("n_vents", 6), ("rf_mode_f1_ghz", 10.5)),
        target_mass_kg=1.45,
    )
    feats = (
        ScadFeature("add_tube", {"od": 69.0, "id": 64.0, "h": 35.5}, translate=(0.0, 0.0, -1.25), comment="Nb RRR>300 Meissner cup w/ RF baffle"),
        ScadFeature("add_tube", {"od": 16.0, "id": 12.0, "h": 10.9}, translate=(0.0, 0.0, 24.65), comment="Nb attenuating chimney"),
        ScadFeature("add_tube", {"od": 82.0, "id": 71.0, "h": 56.0}, translate=(0.0, 0.0, 3.0), comment="Dual-layer 5.0 mm Cryoperm-10 outer shield"),
        ScadFeature("cut_bolt_circle", {"pcd": 60.0, "bolt_d": 2.7, "count": 6, "h": 4.0}, translate=(0.0, 0.0, 17.85), comment="6x M2.5 lid bolt circle"),
        ScadFeature("cut_bolt_circle", {"pcd": 54.0, "bolt_d": 3.5, "count": 6, "h": 4.0}, translate=(0.0, 0.0, -26.35), comment="6x Ø3.5 mm vacuum vent holes"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_3_04() -> BuiltPart:
    """S6.3-04: 4-Channel Persistent-Mode Superconducting Switch Bank + Cold Diodes + 1.563 Ohm Quench Box (OBS-072)."""
    dx, dy, dz = 36.0, 46.0, 54.0
    parts: list[SolidMesh] = []
    parts.append(make_hollow_frame(dx, dy, dx - 6.0, dy - 6.0, dz - 8.4, center=(0.0, 0.0, 0.0), name="quench_box_body", material="OFHC Cu"))
    parts.append(make_rect_plate_with_features(dx, dy, 4.0, circular_holes=((-13.0, -18.0, 3.2), (13.0, -18.0, 3.2), (13.0, 18.0, 3.2), (-13.0, 18.0, 3.2)), hole_segments=10, center=(0.0, 0.0, -0.5 * dz + 2.0), name="quench_base", material="OFHC Cu"))
    parts.append(make_box(dx, dy, 3.8, center=(0.0, 0.0, 0.5 * dz - 2.0), name="quench_lid", material="OFHC Cu"))
    # 4 independent NbTi persistent switch bobbins (Main Helmholtz, Shim, Active-Shield A, Quiet-Zone Bucking B)
    for sw_i, (sx, sy) in enumerate(((-6.5, -10.5), (6.5, -10.5), (-6.5, 2.5), (6.5, 2.5)), start=1):
        parts.append(make_cylinder(5.0, 32.0, segments=16, center=(sx, sy, 0.0), name=f"persistent_switch_ch{sw_i}", material="NbTi"))
    parts.append(make_cylinder(5.5, 10.0, segments=14, center=(-6.5, 13.5, -8.0), name="cold_diode_a", material="OFHC Cu"))
    parts.append(make_cylinder(5.5, 10.0, segments=14, center=(6.5, 13.5, 8.0), name="cold_diode_b", material="OFHC Cu"))

    mesh = merge_solids(parts, name="S6.3-04", material="OFHC Cu")
    ports = (
        PortInterface("base_4k_mount", "thermal", (0.0, 0.0, -27.0), (0.0, 0.0, -1.0), "4x M3 OFHC 4K Mount", mating_part_id="S6.8-01", bolt_count=4, bolt_hole_mm=3.2, bolt_spec="M3"),
        PortInterface("quench_dump_tap", "electrical", (18.0, 0.0, 0.0), (1.0, 0.0, 0.0), "4-Ch Persistent Switch + 1.563 Ohm Quench Bus", mating_part_id="S6.3-05"),
    )
    design = make_part_design_from_bom(
        "S6.3-04",
        material="OFHC Cu",
        world_origin_mm=(-598.0, 0.0, 792.5),
        ports=ports,
        dimensions=(
            DimensionCallout("BOX_X", dx, 0.1, -0.1),
            DimensionCallout("BOX_Y", dy, 0.1, -0.1),
            DimensionCallout("BOX_Z", dz, 0.1, -0.1),
        ),
        notes=("OBS-072 fix: 4-channel matched persistent switch bank (Helmholtz pair, Shim pair, A-shield pair, B-bucking pair) matching 4-pair S6.3-05 HTS leads.",),
        scad_params=(("n_switches", 4), ("r_dump_ohm", 1.563), ("e_mag_kj", 18.9), ("t_quench_peak_k", 64.6)),
        target_mass_kg=0.52,
    )
    feats = (
        ScadFeature("add_box", {"dx": dx, "dy": dy, "dz": dz}, comment="4.2 K 4-channel persistent switch & cold-diode quench box"),
        ScadFeature("add_cylinder", {"d": 10.0, "h": 32.0}, translate=(-6.5, -10.5, 0.0), comment="NbTi persistent switch ch1"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_3_05() -> BuiltPart:
    """S6.3-05: 4-Channel >=300 A (320 A Rated) Bipolar Magnet PSU (3U, Bay 2 U1..U3) + 4-Pair Bi-2223 HTS Terminals (OBS-072)."""
    zc, dz = rack_u_center_and_height(1, 3)
    base_mesh, base_feats = make_rack_chassis_19in(540.0, dz, n_subunits=1, n_front_ports=8, material="Steel", name="S6.3-05_psu")
    # 4-pair (8 terminals) Bi-2223 HTS current-lead terminal lugs & Al2O3 insulators protruding +20 mm at rear (+Y)
    hts_parts: list[SolidMesh] = [base_mesh]
    for idx, sx in enumerate((-157.5, -112.5, -67.5, -22.5, 22.5, 67.5, 112.5, 157.5), start=1):
        hts_parts.append(make_tube(6.0, 12.0, 18.0, segments=16, axis="y", center=(sx, 279.5, 0.0), name=f"hts_ins_{idx}", material="Al2O3"))
        hts_parts.append(make_cylinder(5.5, 22.0, segments=16, axis="y", center=(sx, 281.5, 0.0), name=f"hts_lead_{idx}", material="OFHC Cu"))
    mesh = merge_solids(hts_parts, name="S6.3-05", material="Steel")
    ports = (
        PortInterface("hts_320a_4pair_out", "electrical", (0.0, 292.5, 0.0), (0.0, 1.0, 0.0), "4-Pair (8x) >=300 A (320 A) Bi-2223 HTS Leads", mating_part_id="S6.3-04"),
        PortInterface("rack_bay2_u1_u3", "mechanical", (0.0, -270.0, 0.0), (0.0, -1.0, 0.0), '19" EIA-310 3U (U1-U3)', mating_part_id="S7.4-03"),
    )
    design = make_part_design_from_bom(
        "S6.3-05",
        material="Steel",
        world_origin_mm=(RACK_BAY2_X_MM, RACK_BAY2_Y_MM, zc),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5),
            DimensionCallout("DEPTH", 562.5, 1.0, -1.0),
            DimensionCallout("HEIGHT_3U", dz, 0.3, -0.3),
        ),
        notes=("OBS-072 fix: 4-channel bipolar magnet PSU rated >=300 A (320 A peak) with 4-pair Bi-2223 HTS leads (50K->4K heat load <=0.15 W total across all 4 pairs in persistent-retracted mode).",),
        scad_params=(("rack_u", 3), ("bay", 2), ("u_start", 1), ("n_hts_pairs", 4), ("i_max_a", 320.0)),
        target_mass_kg=24.0,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=base_feats)


def _build_s6_4_01() -> BuiltPart:
    """S6.4-01: 4x Microwave ESR vector signal generators (10-45 GHz, 4x1U = 4U, Bay 2 U13..U16)."""
    zc, dz = rack_u_center_and_height(13, 4)
    mesh, feats = make_rack_chassis_19in(500.0, dz, n_subunits=4, n_front_ports=8, material="Al 6061", name="S6.4-01")
    ports = (
        PortInterface("esr_mw_out_4ch", "rf", (0.0, -257.0, 0.0), (0.0, -1.0, 0.0), "4x 2.92mm K-Conn 45 GHz", mating_part_id="S6.4-02"),
        PortInterface("rack_bay2_u13_u16", "mechanical", (0.0, -250.0, 0.0), (0.0, -1.0, 0.0), '19" EIA-310 4U (U13-U16)', mating_part_id="S7.4-03"),
    )
    design = make_part_design_from_bom(
        "S6.4-01",
        material="Al 6061",
        world_origin_mm=(RACK_BAY2_X_MM, RACK_BAY2_Y_MM, zc),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5),
            DimensionCallout("DEPTH", 500.0, 1.0, -1.0),
            DimensionCallout("HEIGHT_4U", dz, 0.4, -0.4),
        ),
        scad_params=(("rack_u", 4), ("qty_units", 4), ("f_max_ghz", 45.0)),
        target_mass_kg=26.0,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_4_02() -> BuiltPart:
    """S6.4-02: 4x Broadband I/Q modulators, fast switches & RT driver amps (2U, Bay 2 U17..U18)."""
    zc, dz = rack_u_center_and_height(17, 2)
    mesh, feats = make_rack_chassis_19in(460.0, dz, n_subunits=2, n_front_ports=12, material="Al 6061", name="S6.4-02")
    ports = (
        PortInterface("iq_drive_out", "rf", (0.0, -237.0, 0.0), (0.0, -1.0, 0.0), "8x 2.92mm MW Drive Out", mating_part_id="S6.4-03"),
        PortInterface("rack_bay2_u17_u18", "mechanical", (0.0, -230.0, 0.0), (0.0, -1.0, 0.0), '19" EIA-310 2U (U17-U18)', mating_part_id="S7.4-03"),
    )
    design = make_part_design_from_bom(
        "S6.4-02",
        material="Al 6061",
        world_origin_mm=(RACK_BAY2_X_MM, RACK_BAY2_Y_MM, zc),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5),
            DimensionCallout("DEPTH", 460.0, 1.0, -1.0),
            DimensionCallout("HEIGHT_2U", dz, 0.3, -0.3),
        ),
        scad_params=(("rack_u", 2), ("qty_sets", 4), ("if_bw_mhz", 200.0)),
        target_mass_kg=10.5,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_4_03() -> BuiltPart:
    """S6.4-03: 8x Cryogenic microwave drive coax lines & stepped XMA attenuators (-60 dB)."""
    z_orig = 669.0
    spans = (
        ("50k_4k", 752.0, 836.0),
        ("4k_still", 618.0, 718.0),
        ("still_cp", 554.0, 602.0),
        ("cp_mxc", 502.0, 540.0),
    )
    mesh, feats = make_staged_coax_loom(8, 20.0, 18.0, spans, z_orig, attenuator_r=3.5, material="CuNi", name="S6.4-03")
    ports = (
        PortInterface("mw_top_50k", "rf", (0.0, 0.0, 836.0 - z_orig), (0.0, 0.0, 1.0), "8x 2.92mm / 0.086-in CuNi", mating_part_id="S6.4-02"),
        PortInterface("mw_bot_mxc", "rf", (0.0, 0.0, 502.0 - z_orig), (0.0, 0.0, -1.0), "8x XMA -60 dB MXC Out", mating_part_id="S6.8-01"),
    )
    design = make_part_design_from_bom(
        "S6.4-03",
        material="CuNi",
        world_origin_mm=(DR_X_MM + 62.0, 40.0, z_orig),
        ports=ports,
        dimensions=(
            DimensionCallout("LOOM_W", 20.0, 0.2, -0.2),
            DimensionCallout("LOOM_D", 18.0, 0.2, -0.2),
            DimensionCallout("SPAN_Z", 334.0, 0.5, -0.5),
        ),
        scad_params=(("n_lines", 8), ("atten_db", 60.0), ("f_max_ghz", 40.0)),
        target_mass_kg=0.58,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_5_01() -> BuiltPart:
    """S6.5-01: 4x RF/ENDOR nuclear addressing DDS sources (1-200 MHz, 2U, Bay 2 U9..U10)."""
    zc, dz = rack_u_center_and_height(9, 2)
    mesh, feats = make_rack_chassis_19in(420.0, dz, n_subunits=2, n_front_ports=8, material="Al 6061", name="S6.5-01")
    ports = (
        PortInterface("endor_dds_out", "rf", (0.0, -217.0, 0.0), (0.0, -1.0, 0.0), "4x SMA 1-200 MHz DDS", mating_part_id="S6.5-02"),
        PortInterface("rack_bay2_u9_u10", "mechanical", (0.0, -210.0, 0.0), (0.0, -1.0, 0.0), '19" EIA-310 2U (U9-U10)', mating_part_id="S7.4-03"),
    )
    design = make_part_design_from_bom(
        "S6.5-01",
        material="Al 6061",
        world_origin_mm=(RACK_BAY2_X_MM, RACK_BAY2_Y_MM, zc),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5),
            DimensionCallout("DEPTH", 420.0, 1.0, -1.0),
            DimensionCallout("HEIGHT_2U", dz, 0.3, -0.3),
        ),
        scad_params=(("rack_u", 2), ("qty_units", 4), ("f_max_mhz", 200.0)),
        target_mass_kg=8.8,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_5_02() -> BuiltPart:
    """S6.5-02: 4x Broadband 10 W class-A RF power amplifiers & couplers (2U, Bay 2 U11..U12)."""
    zc, dz = rack_u_center_and_height(11, 2)
    mesh, feats = make_rack_chassis_19in(480.0, dz, n_subunits=2, n_front_ports=8, material="Al 6061", name="S6.5-02")
    ports = (
        PortInterface("rf_amp_10w_out", "rf", (0.0, -247.0, 0.0), (0.0, -1.0, 0.0), "4x Type-N 10 W Class-A", mating_part_id="S6.5-03"),
        PortInterface("rack_bay2_u11_u12", "mechanical", (0.0, -240.0, 0.0), (0.0, -1.0, 0.0), '19" EIA-310 2U (U11-U12)', mating_part_id="S7.4-03"),
    )
    design = make_part_design_from_bom(
        "S6.5-02",
        material="Al 6061",
        world_origin_mm=(RACK_BAY2_X_MM, RACK_BAY2_Y_MM, zc),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5),
            DimensionCallout("DEPTH", 480.0, 1.0, -1.0),
            DimensionCallout("HEIGHT_2U", dz, 0.3, -0.3),
        ),
        scad_params=(("rack_u", 2), ("p_out_w", 10.0), ("f_max_mhz", 200.0)),
        target_mass_kg=12.4,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_5_03() -> BuiltPart:
    """S6.5-03: 8x Cryogenic RF coax lines, bias-tee & Eccosorb CR-124 LPF clamps."""
    z_orig = 669.0
    spans = (
        ("50k_4k", 752.0, 836.0),
        ("4k_still", 618.0, 718.0),
        ("still_cp", 554.0, 602.0),
        ("cp_mxc", 502.0, 540.0),
    )
    mesh, feats = make_staged_coax_loom(8, 20.0, 18.0, spans, z_orig, attenuator_r=4.0, material="CuNi", name="S6.5-03")
    ports = (
        PortInterface("rf_top_50k", "rf", (0.0, 0.0, 836.0 - z_orig), (0.0, 0.0, 1.0), "8x SMA CuNi Coax", mating_part_id="S6.5-02"),
        PortInterface("rf_bot_mxc", "rf", (0.0, 0.0, 502.0 - z_orig), (0.0, 0.0, -1.0), "8x Eccosorb CR-124 LPF", mating_part_id="S6.8-01"),
    )
    design = make_part_design_from_bom(
        "S6.5-03",
        material="CuNi",
        world_origin_mm=(DR_X_MM + 62.0, -40.0, z_orig),
        ports=ports,
        dimensions=(
            DimensionCallout("LOOM_W", 20.0, 0.2, -0.2),
            DimensionCallout("LOOM_D", 18.0, 0.2, -0.2),
            DimensionCallout("SPAN_Z", 334.0, 0.5, -0.5),
        ),
        scad_params=(("n_lines", 8), ("eccosorb_grade", "CR-124"), ("ir_atten_db", 40.0)),
        target_mass_kg=0.62,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_9_01() -> BuiltPart:
    """S6.9-01: PT420 500 mm offset acoustic remote rotary valve enclosure, floor stand & 600 mm flex He U-loop (Exp133)."""
    # World origin: (-1150.0, 0.0, 610.0) (exact 500 mm offset from DR_X_MM=-650!)
    # Floor stand: z_global = [0.0, 1009.0] -> z_local = [-610.0, +399.0]
    # Acoustic valve box: 180 x 160 x 180 mm at z_global = [1010.0, 1190.0] -> z_local = [+400.0, +580.0]
    # Swept 3D 600 mm flex He U-loop: exits box +X at x_local=+90.5, z_local=+520 (z_global=1130),
    # drops cleanly to z_global=1004 (z_local=+394) at x_global=-895, rises to (-726, 0, 1130) (x_local=+424, clearing PT420 boss at -723!)
    z0 = 610.0
    parts: list[SolidMesh] = []
    # Welded floor baseplate with 4x M12 anchor holes (z_global=[0, 12])
    parts.append(
        make_rect_plate_with_features(
            220.0,
            220.0,
            12.0,
            circular_holes=((-90.0, -90.0, 13.0), (90.0, -90.0, 13.0), (90.0, 90.0, 13.0), (-90.0, 90.0, 13.0)),
            hole_segments=12,
            center=(0.0, 0.0, 6.0 - z0),
            name="rv_floor_plate",
            material="Steel",
        )
    )
    # Hollow welded acoustic stand tower (z_global=[12.5, 1008.5])
    parts.append(make_hollow_frame(160.0, 160.0, 128.0, 128.0, 996.0, center=(0.0, 0.0, 510.5 - z0), name="rv_stand_column", material="Steel"))
    # Acoustic-lined Al 6061 remote rotary valve enclosure (180x160x180 mm, 0.3 mm acoustic gasket seam)
    parts.append(make_hollow_frame(180.0, 160.0, 164.0, 144.0, 163.4, center=(0.0, 0.0, 1100.0 - z0), name="rv_acoustic_wall", material="Al 6061"))
    parts.append(make_box(180.0, 160.0, 8.0, center=(0.0, 0.0, 1014.0 - z0), name="rv_acoustic_bot", material="Al 6061"))
    parts.append(
        make_rect_plate_with_features(
            180.0,
            160.0,
            8.0,
            circular_holes=((-76.0, -66.0, 5.5), (76.0, -66.0, 5.5), (76.0, 66.0, 5.5), (-76.0, 66.0, 5.5)),
            hole_segments=10,
            center=(0.0, 0.0, 1186.0 - z0),
            name="rv_acoustic_lid",
            material="Al 6061",
        )
    )
    # Internal rotary-valve stepper motor cylinder inside acoustic box
    parts.append(make_cylinder(44.0, 110.0, segments=24, center=(0.0, 0.0, 1095.0 - z0), name="rv_motor_core", material="Steel"))

    # Smooth 3D swept 600 mm braided He flexible U-loop line (R_bend = 36 mm >> r_out=10.5 mm)
    def _arc_pts(cx: float, cz: float, r: float, a0: float, a1: float, n: int = 7) -> list[tuple[float, float, float]]:
        return [
            (cx + r * math.cos(math.radians(a)), 0.0, cz + r * math.sin(math.radians(a)))
            for a in np.linspace(a0, a1, n)
        ]

    # Spine in local coords: start (+91, 0, +520) -> bend down at x=+160 -> bottom z=+396 -> bend up at x=+350 -> end (+423, 0, +520)
    # Path arc length: 69 + 56.5 + 52 + 56.5 + 118 + 56.5 + 52 + 56.5 + 73 = ~590..600 mm!
    rb = 36.0
    spine: list[tuple[float, float, float]] = [(91.0, 0.0, 520.0)]
    spine.extend(_arc_pts(154.0, 520.0 - rb, rb, 90.0, 0.0, 7))
    spine.extend(_arc_pts(190.0 + rb, 396.0 + rb, rb, 180.0, 270.0, 7))
    spine.extend(_arc_pts(354.0 - rb, 396.0 + rb, rb, 270.0, 360.0, 7))
    spine.extend(_arc_pts(354.0 + rb, 520.0 - rb, rb, 180.0, 90.0, 7))
    spine.append((423.0, 0.0, 520.0))
    # Deduplicate consecutive close points
    clean_spine: list[tuple[float, float, float]] = [spine[0]]
    for pt in spine[1:]:
        if math.dist(pt, clean_spine[-1]) > 0.5:
            clean_spine.append(pt)
    parts.append(make_swept_tube(clean_spine, r_out=10.5, r_in=7.5, segments=16, name="pt420_flex_he_uloop", material="316L"))

    mesh = merge_solids(parts, name="S6.9-01", material="Al 6061")
    ports = (
        PortInterface("he_uloop_to_pt420", "gas", (423.0, 0.0, 520.0), (1.0, 0.0, 0.0), "L=600 mm Braided 316L He U-Loop", mating_part_id="S6.1-01", bore_mm=15.0, od_mm=21.0),
        PortInterface("floor_anchor_base", "bolt", (0.0, 0.0, -610.0), (0.0, 0.0, -1.0), "4x M12 Vibration-Isolated Anchor", bolt_count=4, bolt_hole_mm=13.0, bolt_spec="M12"),
    )
    design = make_part_design_from_bom(
        "S6.9-01",
        material="Al 6061",
        world_origin_mm=(RV_X_MM, 0.0, z0),
        ports=ports,
        dimensions=(
            DimensionCallout("VALVE_OFFSET", 500.0, 1.0, -1.0),
            DimensionCallout("FLEX_HE_LEN", 600.0, 5.0, -5.0),
            DimensionCallout("BOX_W", 180.0, 0.5, -0.5),
            DimensionCallout("STAND_H", 1190.0, 1.0, -1.0),
        ),
        gdt_frames=(GDTFrame("flatness", 0.20, datum_primary="A", feature_note="Floor isolation anchor plate"),),
        scad_params=(("valve_offset_mm", 500.0), ("flex_he_length_mm", 600.0), ("box_dx", 180.0), ("box_dy", 160.0), ("box_dz", 180.0)),
        target_mass_kg=29.5,
    )
    feats = (
        ScadFeature("add_box", {"dx": 160.0, "dy": 160.0, "dz": 996.0}, translate=(0.0, 0.0, -99.5), comment="Acoustic floor stand"),
        ScadFeature("add_box", {"dx": 180.0, "dy": 160.0, "dz": 180.0}, translate=(0.0, 0.0, 490.0), comment="PT420 500 mm offset acoustic valve box"),
        ScadFeature("add_cylinder", {"d": 21.0, "h": 332.0}, translate=(257.0, 0.0, 458.0), rotate=(0.0, 90.0, 0.0), comment="600 mm braided He U-loop envelope"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=3600.0)


def _build_s6_9_02() -> BuiltPart:
    """S6.9-02: True 28-convolution edge-welded 316L CF100 OVC/UHV vibration-decoupling bellows (ID=76 mm, k=2000 N/m, OBS-065)."""
    # World origin: (-352.0, 0.0, 493.5) — upgraded from CF63 (ID=44) to CF100 (ID=76 mm) so enlarged Ø46/52 mm
    # S6.2-02 4 K bridge tube + twin 4 K bus straps fit with >=12 mm radial clearance!
    # World X span preserved strictly at [-474.5, -274.0]:
    # - 28-conv bellows:        local [-58.0, +58.0]  (L_active=116.0 mm, r_in=38.0, r_out=49.0)
    # - Right UHV CF100 flange: local [+58.2, +78.0]  -> world X = [-293.8, -274.0] (0.50 mm gap to S5.1-01 at -273.5!)
    # - Left DR CF100 flange:   local [-78.0, -58.2]  -> world X = [-430.0, -410.2]
    # - Left DR weld-neck:      local [-122.5, -78.2] -> world X = [-474.5, -430.2] (0.50 mm gap to S6.8-04 at -475.0!)
    bellows = make_bellows(
        r_in=38.0,
        r_out=49.0,
        length=116.0,
        n_convolutions=28,
        wall_thickness=0.15,
        end_cuff_mm=3.0,
        segments=36,
        axis="x",
        center=(0.0, 0.0, 0.0),
        name="bellows_28conv_cf100_316l",
        material="316L",
    )
    fl_dr = make_cf_flange(
        "CF100",
        bore_id=76.0,
        with_knife_edge=True,
        sub_per_side=2,
        axis="-x",
        center=(-68.1, 0.0, 0.0),
        name="cf100_flange_dr",
        material="316L",
    )
    fl_uhv = make_cf_flange(
        "CF100",
        bore_id=76.0,
        with_knife_edge=True,
        sub_per_side=2,
        axis="+x",
        center=(68.1, 0.0, 0.0),
        name="cf100_flange_uhv",
        material="316L",
    )
    stub_dr = make_tube(38.0, 42.0, 28.8, segments=32, axis="x", center=(-92.6, 0.0, 0.0), name="stub_dr", material="316L")

    mesh = merge_solids([bellows, fl_dr, fl_uhv, stub_dr], name="S6.9-02", material="316L")
    ports = (
        make_cf_port_interface("CF100", "ovc_dr_cf100", (-78.0, 0.0, 0.0), (-1.0, 0.0, 0.0), mating_part_id="S6.8-04", bore_override_mm=76.0),
        make_cf_port_interface("CF100", "uhv_chamber_cf100", (78.0, 0.0, 0.0), (1.0, 0.0, 0.0), mating_part_id="S5.1-01", bore_override_mm=76.0),
    )
    design = make_part_design_from_bom(
        "S6.9-02",
        material="316L",
        world_origin_mm=(-367.5, 0.0, Z_CRYO_BRIDGE_MM),
        ports=ports,
        dimensions=(
            DimensionCallout("BELLOWS_ID", 76.0, 0.10, -0.10, prefix="Ø"),
            DimensionCallout("BELLOWS_OD", 98.0, 0.10, -0.10, prefix="Ø"),
            DimensionCallout("L_ACTIVE", 116.0, 0.50, -0.50),
            DimensionCallout("FLANGE_OD", 152.0, 0.10, -0.10, prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.05, diameter_zone=True, datum_primary="B", feature_note="CF100 sealing faces"),
            GDTFrame("parallelism", 0.05, datum_primary="A", feature_note="End flange parallelism"),
        ),
        notes=(
            "OBS-065 fix: Upgraded to CF100 (ID=76.0 mm, OD=98.0 mm, flange OD=152.0 mm, 28-conv 0.15 mm 316L, k=2000 N/m) clearing Ø52 mm 4K bridge tube by 12.0 mm radially.",
            "Right CF100 sealing face terminates at world X=-289.5 mm (0.50 mm Cu-gasket gap to S5.1-01 -X CF100 weld-neck at X=-289.0 mm, clearing S3.2-05); left neck ends at X=-474.5 mm.",
        ),
        scad_params=(("bellows_id", 76.0), ("bellows_od", 98.0), ("l_active", 116.0), ("n_convolutions", 28), ("sheet_mm", 0.15), ("k_n_per_m", 2000.0)),
        target_mass_kg=5.2,
    )
    feats = (
        ScadFeature("add_tube", {"od": 98.0, "id": 76.0, "h": 116.0}, rotate=(0.0, 90.0, 0.0), comment="28-convolution 316L CF100 bellows envelope"),
        ScadFeature("add_cf_flange", {"size": "CF100", "bore_id": 76.0}, translate=(-68.1, 0.0, 0.0), rotate=(0.0, -90.0, 0.0), comment="DR-side ISO 3669 CF100 flange"),
        ScadFeature("add_cf_flange", {"size": "CF100", "bore_id": 76.0}, translate=(68.1, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="UHV-side ISO 3669 CF100 flange (X=-289.5 mm)"),
        ScadFeature("add_tube", {"od": 84.0, "id": 76.0, "h": 28.8}, translate=(-92.6, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="DR-side CF100 weld-neck spool"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_9_03() -> BuiltPart:
    """S6.9-03: Annealed RRR>=200 Ø30x397 mm OFHC Cu Busbar + 8x Electron-Beam-Welded Parallel Cu Braids (88 mm^2, <=23.4 mK!)."""
    # World origin: (-308.0, 0.0, 493.5)
    # OBS-041 & OBS-065 fix:
    # - Enlarged annealed RRR>=200 OFHC Cu busbar to Ø30.0 mm (R=15.0 mm, A=706.9 mm^2, L=397 mm) fitting cleanly
    #   inside S6.2-02 Ø46.0 mm ID 4 K bridge tube with 8.0 mm radial vacuum clearance!
    # - 8x parallel electron-beam-welded multi-leaf OFHC Cu S-braids (each 5.5x2.0 mm = 11.0 mm^2 -> 88.0 mm^2 >= 80 mm^2!),
    #   max radial excursion = 13.38 mm << 23.0 mm 4 K tube ID (9.62 mm clearance!), k_braid ~ 240 N/m << 4197 N/m!
    # - Monolithic electron-beam-welded collars eliminate bolted-joint Kapitza bottleneck -> T_chuck = 21.75 mK @ 7.04 uW,
    #   23.36 mK @ 14.0 uW (<= 25 mK target!).
    parts: list[SolidMesh] = []
    # Main DR-side Ø30.0 x 390 mm annealed RRR>=200 OFHC Cu busbar (x_local = [-239.8, +150.2])
    parts.append(make_cylinder(15.0, 390.0, segments=36, axis="x", center=(-44.8, 0.0, 0.0), name="mxc_cu_busbar_d30_397", material="OFHC Cu"))
    # Monolithic e-beam-welded DR MXC interface collar (x_local = [-246.5, -240.0])
    parts.append(
        make_rect_plate_with_features(
            34.0, 34.0, 6.4,
            circular_holes=((-12.0, -12.0, 3.2), (12.0, -12.0, 3.2), (12.0, 12.0, 3.2), (-12.0, 12.0, 3.2)),
            hole_segments=10, axis="x", center=(-243.25, 0.0, 0.0),
            name="busbar_mxc_ebw_collar", material="OFHC Cu",
        )
    )
    # Monolithic e-beam-welded braid-to-rod transition collar (x_local = [+150.4, +157.0]) & chuck collar ([+240.2, +246.8])
    # East collar Z=[-10.8, +6.8] -> world Z=[482.7, 500.3] cleanly clears S2.4-02 Z_min=502.8 by 2.5 mm!
    parts.append(make_box(6.6, 26.0, 17.6, center=(153.7, 0.0, -2.0), name="ebw_braid_collar_west", material="OFHC Cu"))
    parts.append(make_box(6.6, 26.0, 17.6, center=(243.5, 0.0, -2.0), name="ebw_braid_collar_east", material="OFHC Cu"))

    feats: list[ScadFeature] = [
        ScadFeature("add_cylinder", {"d": 30.0, "h": 397.0}, translate=(-48.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="DR-side Ø30x397 mm RRR>=200 OFHC Cu busbar"),
    ]
    # 8x parallel multi-leaf OFHC Cu S-braids (4x2 array, each 5.5 x 2.0 mm = 11.0 mm^2 -> 88.0 mm^2 total, zero overlap!)
    braid_coords = (
        (-10.0, -4.8), (-3.5, -4.8), (3.5, -4.8), (10.0, -4.8),
        (-10.0, 1.8), (-3.5, 1.8), (3.5, 1.8), (10.0, 1.8),
    )
    for b_idx, (by, bz) in enumerate(braid_coords, start=1):
        br = make_s_braid(
            length_mm=82.8,
            s_amplitude_mm=1.2,
            width_mm=5.5,
            thickness_mm=2.0,
            n_steps=24,
            lug_length_mm=0.0,
            axis="x",
            center=(198.6, by, bz),
            name=f"mxc_ebw_s_braid_{b_idx}",
            material="OFHC Cu",
        )
        parts.append(br)
        feats.append(
            ScadFeature("add_box", {"dx": 82.8, "dy": 5.5, "dz": 4.4}, translate=(198.6, by, bz), comment=f"E-beam-welded OFHC Cu multi-leaf S-braid #{b_idx} (11 mm^2)")
        )

    mesh = merge_solids(parts, name="S6.9-03", material="OFHC Cu")
    ports = (
        PortInterface("mxc_dr_clamp", "thermal", (-246.5, 0.0, 0.0), (-1.0, 0.0, 0.0), "E-Beam-Welded Au-OFHC MXC Interface", mating_part_id="S6.8-01", od_mm=34.0, bolt_count=4, bolt_hole_mm=3.2, bolt_spec="M3"),
        PortInterface("cold_island_braid_end", "thermal", (246.8, 0.0, 0.0), (1.0, 0.0, 0.0), "E-Beam-Welded 88 mm^2 OFHC Braid Block", mating_part_id="S6.2-01", od_mm=26.0),
    )
    design = make_part_design_from_bom(
        "S6.9-03",
        material="OFHC Cu",
        world_origin_mm=(-308.0, 0.0, Z_CRYO_BRIDGE_MM),
        ports=ports,
        dimensions=(
            DimensionCallout("BUSBAR_OD", 30.0, 0.03, -0.03, prefix="Ø"),
            DimensionCallout("BUSBAR_L", 397.0, 0.20, -0.20),
            DimensionCallout("BRAID_L", 96.4, 0.50, -0.50),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.015, datum_primary="A", feature_note="E-beam-welded thermal interface collars"),
            GDTFrame("straightness", 0.10, datum_primary="B", feature_note="Ø30 RRR>=200 OFHC Cu busbar"),
        ),
        notes=(
            "OBS-041/065 fix: Ø30.0 mm annealed RRR>=200 OFHC Cu rod + 8x electron-beam-welded parallel multi-leaf Cu braids (88.0 mm^2 >= 80 mm^2, k_braid=240 N/m << 4197 N/m).",
            "Nonlinear Wiedemann-Franz T^2 conduction (0 bolted joints): T_chuck = 20.64 mK @ 2.5 uW, 21.75 mK @ 7.04 uW, 23.36 mK @ 14.0 uW (<=25 mK target!).",
        ),
        scad_params=(("busbar_d", 30.0), ("busbar_l", 397.0), ("n_braids", 8), ("a_braid_mm2", 88.0), ("rrr_min", 200), ("k_braid_n_per_m", 240.0), ("t_chuck_7uw_mk", 21.75), ("t_chuck_14uw_mk", 23.36)),
        target_mass_kg=2.85,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_9_04() -> BuiltPart:
    """S6.9-04: PT420 rotary-valve phase encoder & n=1..15 harmonic feedforward DSP/FPGA 1U unit (Bay 2 U6)."""
    zc, dz = rack_u_center_and_height(6, 1)
    mesh, feats = make_rack_chassis_19in(380.0, dz, n_subunits=1, n_front_ports=6, material="Al 6061", name="S6.9-04")
    ports = (
        PortInterface("encoder_ff_in", "connector", (0.0, 190.0, 0.0), (0.0, 1.0, 0.0), "LEMO Optical Phase Encoder", mating_part_id="S6.9-01"),
        PortInterface("rack_bay2_u6", "mechanical", (0.0, -190.0, 0.0), (0.0, -1.0, 0.0), '19" EIA-310 1U (U6)', mating_part_id="S7.4-03"),
    )
    design = make_part_design_from_bom(
        "S6.9-04",
        material="Al 6061",
        world_origin_mm=(RACK_BAY2_X_MM, RACK_BAY2_Y_MM, zc),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5),
            DimensionCallout("DEPTH", 380.0, 1.0, -1.0),
            DimensionCallout("HEIGHT_1U", dz, 0.3, -0.3),
        ),
        scad_params=(("rack_u", 1), ("u_start", 6), ("harmonics_n", 15), ("ff_suppression_db", 25.0)),
        target_mass_kg=4.2,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


# ---------------------------------------------------------------------------
# Cryogenic Differential Thermal Contraction & Axial Stackup Verifier
# ---------------------------------------------------------------------------
def run_cryo_thermal_checks() -> dict[str, Any]:
    """Verify all concentric S6/Option-Q cryo interfaces from 300 K -> 50 K -> 4 K -> 20 mK."""
    clearance_specs = [
        ("uhv_chamber_vs_50k_chamber_shield_50k", "316LN", "Al 6061", 364.0, 359.0, 50.0, 2.0, 0.10, 0.10),
        ("50k_chamber_shield_vs_magnet_former_4k", "Al 6061", "Ti-6Al-4V", 355.0, 352.0, 4.2, 1.0, 0.05, 0.05),
        ("magnet_former_vs_a_coil_4k", "Ti-6Al-4V", "NbTi", 338.0, 335.0, 4.2, 1.0, 0.05, 0.05),
        ("b_bucking_coil_vs_invar_pedestal_4k", "NbTi", "Invar-36", 112.0, 104.0, 4.2, 3.5, 0.05, 0.05),
        ("invar_pedestal_vs_cryoperm10_4k", "Invar-36", "Mu-metal", 90.0, 82.0, 4.0, 3.5, 0.05, 0.05),
        ("cryoperm10_vs_nb_meissner_20mk", "Mu-metal", "Nb", 71.0, 69.0, 0.02, 0.8, 0.05, 0.05),
        ("nb_meissner_vs_nbtin_resonator_20mk", "Nb", "OFHC Cu", 64.0, 50.0, 0.02, 6.5, 0.05, 0.05),
        ("dr_ovc_vs_50k_shield_50k", "316LN", "Al 6061", 334.0, 308.0, 50.0, 10.0, 0.20, 0.20),
        ("50k_shield_vs_4k_shield_4k", "Al 6061", "OFHC Cu", 300.0, 272.0, 4.0, 12.0, 0.20, 0.20),
        ("4k_shield_vs_still_shield_0p8k", "OFHC Cu", "OFHC Cu", 264.0, 238.0, 0.8, 11.0, 0.20, 0.20),
        ("cf100_bellows_vs_4k_bridge_tube_4k", "316LN", "OFHC Cu", 76.0, 52.0, 4.0, 10.0, 0.10, 0.10),
        ("4k_bridge_tube_vs_20mk_cu_busbar_20mk", "OFHC Cu", "OFHC Cu", 46.0, 30.0, 0.02, 7.5, 0.05, 0.05),
    ]
    clearances: dict[str, dict[str, Any]] = {}
    all_clear_pass = True
    for key, mat_o, mat_i, id_o, od_i, tc, min_req, tol_o, tol_i in clearance_specs:
        res = check_cold_clearance(
            mat_o,
            mat_i,
            nominal_outer_id_mm=id_o,
            nominal_inner_od_mm=od_i,
            t_cold_k=tc,
            min_required_radial_clearance_mm=min_req,
            outer_id_tol_mm=tol_o,
            inner_od_tol_mm=tol_i,
        )
        clearances[key] = res.to_dict()
        if not res.passed or res.interference_risk:
            all_clear_pass = False

    # Axial tolerance stacks
    split_gap_stack = check_tolerance_stack(
        [
            ToleranceContributor("helmholtz_x_bore_id", 104.0, 0.05, -0.05, sign=+1.0),
            ToleranceContributor("bridge_4k_tube_od", 52.0, 0.05, -0.05, sign=-1.0),
            ToleranceContributor("thermal_z_shift_4k", 0.0, 0.12, -0.12, sign=+1.0),
        ],
        target_min_mm=50.0,
        target_max_mm=54.0,
    )
    qram_gap_stack = check_tolerance_stack(
        [
            ToleranceContributor("twpa_bottom_z", 424.5, 0.10, -0.10, sign=+1.0),
            ToleranceContributor("qram_top_z", 416.0, 0.10, -0.10, sign=-1.0),
            ToleranceContributor("mxc_standoff_tol", 0.0, 0.05, -0.05, sign=+1.0),
        ],
        target_min_mm=7.5,
        target_max_mm=9.5,
    )
    stacks = {
        "magnet_split_gap_vs_4k_bridge_tube": split_gap_stack.to_dict(),
        "twpa_vs_option_q_qram_z_clearance": qram_gap_stack.to_dict(),
    }
    all_stacks_pass = split_gap_stack.wc_pass and qram_gap_stack.wc_pass

    return {
        "all_passed": bool(all_clear_pass and all_stacks_pass),
        "cold_clearance_count": len(clearances),
        "cold_clearances": clearances,
        "tolerance_stacks": stacks,
        "design_maturity": DESIGN_MATURITY,
        "no_lab_measurement": NO_LAB_MEASUREMENT,
    }


# ---------------------------------------------------------------------------
# Exact 3D Solid Clash Verifier (Shell AABB + Triangle-Triangle + Containment)
# ---------------------------------------------------------------------------
def _aabb_overlap(bmin_a: np.ndarray, bmax_a: np.ndarray, bmin_b: np.ndarray, bmax_b: np.ndarray, eps: float = 1e-4) -> bool:
    return bool(
        (bmin_a[0] < bmax_b[0] - eps) and (bmax_a[0] > bmin_b[0] + eps)
        and (bmin_a[1] < bmax_b[1] - eps) and (bmax_a[1] > bmin_b[1] + eps)
        and (bmin_a[2] < bmax_b[2] - eps) and (bmax_a[2] > bmin_b[2] + eps)
    )


def _segments_intersect_triangles(
    p0: np.ndarray,
    p1: np.ndarray,
    tri_v0: np.ndarray,
    tri_v1: np.ndarray,
    tri_v2: np.ndarray,
    eps: float = 1e-6,
) -> bool:
    """Vectorized Moller-Trumbore check: does any open segment (p0,p1) pierce any triangle?"""
    if len(p0) == 0 or len(tri_v0) == 0:
        return False
    # Filter triangles against overall segment cloud AABB first
    s_min = np.minimum(p0, p1).min(axis=0) - eps
    s_max = np.maximum(p0, p1).max(axis=0) + eps
    t_min = np.minimum(np.minimum(tri_v0, tri_v1), tri_v2)
    t_max = np.maximum(np.maximum(tri_v0, tri_v1), tri_v2)
    t_keep = np.all((t_min <= s_max) & (t_max >= s_min), axis=1)
    if not np.any(t_keep):
        return False
    v0 = tri_v0[t_keep]
    e1 = tri_v1[t_keep] - v0
    e2 = tri_v2[t_keep] - v0
    t_min = t_min[t_keep]
    t_max = t_max[t_keep]

    # Chunk segments for low memory footprint
    seg_min = np.minimum(p0, p1)
    seg_max = np.maximum(p0, p1)
    s_d = p1 - p0
    n_t = len(v0)
    for i in range(len(p0)):
        cand = np.all((t_min <= seg_max[i] + eps) & (t_max >= seg_min[i] - eps), axis=1)
        if not np.any(cand):
            continue
        d = s_d[i]
        o = p0[i]
        e1c = e1[cand]
        e2c = e2[cand]
        v0c = v0[cand]
        h = np.cross(d, e2c)
        a = np.einsum("ij,ij->i", e1c, h)
        valid = np.abs(a) > 1e-10
        if not np.any(valid):
            continue
        f_inv = 1.0 / a[valid]
        s_vec = o - v0c[valid]
        u = f_inv * np.einsum("ij,ij->i", s_vec, h[valid])
        q = np.cross(s_vec, e1c[valid])
        v = f_inv * np.einsum("j,ij->i", d, q)
        t = f_inv * np.einsum("ij,ij->i", e2c[valid], q)
        hit = (u > eps) & (v > eps) & (u + v < 1.0 - eps) & (t > eps) & (t < 1.0 - eps)
        if np.any(hit):
            return True
    return False


def _point_inside_closed_shell(pt: np.ndarray, shell: SolidMesh) -> bool:
    """Deterministic odd-parity ray-casting containment test with skew irrational direction."""
    v = shell.vertices
    f = shell.faces
    v0 = v[f[:, 0]]
    e1 = v[f[:, 1]] - v0
    e2 = v[f[:, 2]] - v0
    # Skew direction avoids hitting triangle edges/vertices identically
    d = np.array([0.8191520442889918, 0.42261826174069944, 0.3885729805591295], dtype=np.float64)
    h = np.cross(d, e2)
    a = np.einsum("ij,ij->i", e1, h)
    valid = np.abs(a) > 1e-12
    f_inv = 1.0 / a[valid]
    s_vec = pt - v0[valid]
    u = f_inv * np.einsum("ij,ij->i", s_vec, h[valid])
    q = np.cross(s_vec, e1[valid])
    v_bary = f_inv * np.einsum("j,ij->i", d, q)
    t = f_inv * np.einsum("ij,ij->i", e2[valid], q)
    hits = (u >= 0.0) & (v_bary >= 0.0) & (u + v_bary <= 1.0) & (t > 1e-7)
    return bool(int(np.count_nonzero(hits)) % 2 == 1)


def _shells_clash(sa: SolidMesh, sb: SolidMesh) -> bool:
    """Exact 3D intersection + strict containment test between two watertight single shells."""
    bmin_a, bmax_a = sa.bbox()
    bmin_b, bmax_b = sb.bbox()
    if not _aabb_overlap(bmin_a, bmax_a, bmin_b, bmax_b, eps=1e-4):
        return False

    ov_min = np.maximum(bmin_a, bmin_b) - 1e-4
    ov_max = np.minimum(bmax_a, bmax_b) + 1e-4

    def _filtered_tris(s: SolidMesh) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        v = s.vertices
        f = s.faces
        v0, v1, v2 = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
        tmin = np.minimum(np.minimum(v0, v1), v2)
        tmax = np.maximum(np.maximum(v0, v1), v2)
        keep = np.all((tmin <= ov_max) & (tmax >= ov_min), axis=1)
        return v0[keep], v1[keep], v2[keep]

    a0, a1, a2 = _filtered_tris(sa)
    b0, b1, b2 = _filtered_tris(sb)

    # 1. Check unique edges of A piercing triangles of B
    if len(a0) > 0 and len(b0) > 0:
        p0_a = np.vstack([a0, a1, a2])
        p1_a = np.vstack([a1, a2, a0])
        if _segments_intersect_triangles(p0_a, p1_a, b0, b1, b2):
            return True
        p0_b = np.vstack([b0, b1, b2])
        p1_b = np.vstack([b1, b2, b0])
        if _segments_intersect_triangles(p0_b, p1_b, a0, a1, a2):
            return True

    # 2. Check strict containment (one shell completely inside another solid shell)
    # Test vertex pulled slightly inward along face centroid to avoid grazing boundary
    pt_a = sa.vertices[sa.faces[0]].mean(axis=0)
    if _point_inside_closed_shell(pt_a, sb):
        return True
    pt_b = sb.vertices[sb.faces[0]].mean(axis=0)
    if _point_inside_closed_shell(pt_b, sa):
        return True

    return False


def check_assembly_clashes(built_parts: Mapping[str, BuiltPart]) -> dict[str, Any]:
    """Run exact 3D solid-to-solid clash verification across all parts in global machine coords."""
    pids = sorted(built_parts.keys())
    world_shells: dict[str, list[tuple[SolidMesh, np.ndarray, np.ndarray]]] = {}
    part_bboxes: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    for pid in pids:
        wm = built_parts[pid].world_mesh()
        part_bboxes[pid] = wm.bbox()
        shells = split_shells(wm)
        world_shells[pid] = [(sh, *sh.bbox()) for sh in shells]

    clashes: list[dict[str, Any]] = []
    broadphase_pairs = 0
    for i in range(len(pids)):
        pa = pids[i]
        amin, amax = part_bboxes[pa]
        for j in range(i + 1, len(pids)):
            pb = pids[j]
            bmin, bmax = part_bboxes[pb]
            if not _aabb_overlap(amin, amax, bmin, bmax, eps=1e-4):
                continue
            broadphase_pairs += 1
            hit = False
            for sa, samin, samax in world_shells[pa]:
                for sb, sbmin, sbmax in world_shells[pb]:
                    if _aabb_overlap(samin, samax, sbmin, sbmax, eps=1e-4):
                        if _shells_clash(sa, sb):
                            clashes.append({"part_a": pa, "part_b": pb})
                            hit = True
                            break
                if hit:
                    break

    return {
        "parts_checked": len(pids),
        "broadphase_aabb_pairs": broadphase_pairs,
        "clash_count": len(clashes),
        "clashes": clashes,
        "passed": (len(clashes) == 0),
    }


def export_part_with_json(
    bp: BuiltPart,
    out_dir: Path | str,
    *,
    extra_metadata: dict[str, Any] | None = None,
) -> tuple[PartArtifactResult, Path]:
    """Export all 5 CAD artifacts via core kernel + companion per-part .json metadata."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    res = export_part_artifacts(
        bp.design,
        bp.mesh,
        out_path,
        scad_features=bp.scad_features or None,
        density_kg_m3=bp.density_kg_m3,
        flat=True,
    )
    wm = bp.world_mesh()
    wbmin, wbmax = wm.bbox()
    wmp = compute_mass_props(wm, material=bp.design.material, density_kg_m3=bp.density_kg_m3)

    json_path = out_path / f"{bp.part_id}.json"
    try:
        json_rel = json_path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        json_rel = json_path.as_posix()

    shell_list = split_shells(bp.mesh)
    shell_ties = [
        {
            "shell_index": idx,
            "bbox_min_mm": [round(float(v), 4) for v in sh.bbox()[0]],
            "bbox_max_mm": [round(float(v), 4) for v in sh.bbox()[1]],
            "fea_tie_constraint": "BONDED_WELD_OR_BOLT_ASSEMBLY" if len(shell_list) > 1 else "MONOLITHIC_SOLID",
        }
        for idx, sh in enumerate(shell_list)
    ]
    payload: dict[str, Any] = {
        "part_design": bp.design.to_dict(),
        "artifact_result": res.to_dict(),
        "json_path": json_rel,
        "world_bbox_min_mm": [round(float(v), 4) for v in wbmin],
        "world_bbox_max_mm": [round(float(v), 4) for v in wbmax],
        "world_cg_mm": [round(float(v), 4) for v in wmp.cg_mm],
        "shell_tie_manifest": shell_ties,
        "epistemic": {
            "design_maturity": DESIGN_MATURITY,
            "no_lab_measurement": NO_LAB_MEASUREMENT,
            "iec61508_certified": IEC61508_CERTIFIED,
            "semi_s2_certified": SEMI_S2_CERTIFIED,
        },
    }
    if extra_metadata:
        payload["analysis"] = extra_metadata
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return res, json_path


# ---------------------------------------------------------------------------
# Public Builder & Convenience Re-Exports
# ---------------------------------------------------------------------------
def build_s6_magnet_shields_parts() -> dict[str, BuiltPart]:
    """Build all 21 cryocooler, cold-island, 8-coil magnet, shield & isolation parts."""
    builders = (
        _build_s6_1_01,
        _build_s6_1_02,
        _build_s6_1_03,
        _build_s6_2_01,
        _build_s6_2_02,
        _build_s6_2_03,
        _build_s6_3_01,
        _build_s6_3_02,
        _build_s6_3_03,
        _build_s6_3_04,
        _build_s6_3_05,
        _build_s6_4_01,
        _build_s6_4_02,
        _build_s6_4_03,
        _build_s6_5_01,
        _build_s6_5_02,
        _build_s6_5_03,
        _build_s6_9_01,
        _build_s6_9_02,
        _build_s6_9_03,
        _build_s6_9_04,
    )
    out: dict[str, BuiltPart] = {}
    for fn in builders:
        bp = fn()
        out[bp.part_id] = bp
    return out


def build_s6_parts() -> dict[str, BuiltPart]:
    """Build ALL 40 physical parts of Subsystem S6 (delegates DR/readout to s6_dr_readout_optq)."""
    from hardware.cad_parts.subsystems.s6_dr_readout_optq import build_s6_parts as _build_all_s6

    return _build_all_s6()


def build_s9_optq_parts() -> dict[str, BuiltPart]:
    """Build ALL 3 Option-Q parts (S9.4-01, S9.4-02, S9.4-03)."""
    from hardware.cad_parts.subsystems.s6_dr_readout_optq import build_s9_optq_parts as _build_optq

    return _build_optq()


def export_all(
    out_s6_dir: Path | str = DEFAULT_OUT_S6_DIR,
    out_s9_optq_dir: Path | str = DEFAULT_OUT_S9_OPTQ_DIR,
) -> dict[str, Any]:
    """Build, verify, and export ALL 43 S6 + Option-Q parts."""
    from hardware.cad_parts.subsystems.s6_dr_readout_optq import export_all as _export_all

    return _export_all(out_s6_dir=out_s6_dir, out_s9_optq_dir=out_s9_optq_dir)
