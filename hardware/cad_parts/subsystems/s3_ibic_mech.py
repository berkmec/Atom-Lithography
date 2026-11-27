"""Subsystem S3 — IBIC Pixelated Detector, 100 K Cold-Island CSA & Counting Mechanics.

Designs, verifies, and exports all 14 / 14 physical BOM parts of Subsystem S3
(``S3.1-01`` through ``S3.3-04``) using the pure-Python CAD kernel in
``hardware.cad_parts.core``:

- **In-Vacuum Wafer & Detector Stack (``Z = 0.0 mm`` wafer active top plane, ``R < 180 mm``):**
  - ``S3.1-01`` (CUSTOM_FULL): Pixelated p-i-n IBIC detector wafer (Ø50.0 x 0.525 mm Si)
    with stepped 16x16 mm active implant field, concentric guard-ring keepout moat, and flat.
  - ``S3.1-02`` (CUSTOM_FULL): Cryo Al/Ti/Au 3-ring guard-ring metallization, rear ohmic
    contact disk, and 16 radially fanned peripheral wire-bond bridge tabs.
  - ``S3.1-03`` (CUSTOM_FULL): 80x80 mm AlN/Sapphire wafer carrier (Exp80 BC1) with machined
    Ø50.4 mm stepped wafer pocket, rear Ø34 mm thermal boss, 3x Ø3 H7 alignment pin bosses,
    and 4x M3 corner counterbores (verified 300 K -> 100 K -> 20 mK via NIST thermal tables).
  - ``S3.1-04`` (CUSTOM_FULL): Non-magnetic Au-plated BeCu load-lock cantilever spring
    contact ring (Ø64/Ø80 mm, 16 inward spring fingers, 6x M2.5 bolt circle) + outer Faraday
    bias shield collar.
  - ``S3.2-01`` (CUSTOM_FULL): All 16x 100 K cold-island 8-ch LTC6268 CSA modules (4 quadrants
    x 4 modules @ R=86..118 mm inside 36 mm magnet split gap) + 16x OFHC Cu S-braid thermal
    straps + 4x 100 K OFHC Cu quadrant thermal bus arcs (R=134..142 mm).
  - ``S3.2-04`` (CUSTOM_FULL): All 16x <5 cm (44.8 mm arc length) in-vacuum PTFE/Ag-Cu
    micro-coax IBIC looms (C_par < 0.15 pF) swept from contact ring to cold-island CSA inputs.
- **UHV Chamber Feedthroughs (``R = 230..278 mm, Z = -105 mm``):**
  - ``S3.2-05`` (COTS_ENV_ICD): All 4x ISO 3669 CF63 32-coax hermetic UHV analog feedthrough
    flanges (128 channels total) at azimuths 45/115/162/315 deg, R_face=245.5 mm, Z=-105.0 mm,
    with true 8x Ø8.4 @ PCD 92.1 mm bolt circles & knife-edges.
- **19" Rack Bay 1 Electronics (``X = +1480 mm, 482.6 mm along X, front -Y @ Y=-410..-434 mm, U18..U26``):**
  - ``S3.2-06`` (COTS_ENV_ICD, U18-U19, 2U): 2x ultra-low-noise linear PSU dual-bay rack chassis.
  - ``S3.2-02`` (CUSTOM_FULL,  U20-U21, 2U): 16x CR-RC2 shaper/comparator/trim-DAC EMI
    cassettes (2x8 horizontal stack of 185x135 mm ``ibic_warm_shaper_300k`` PCBs) in 19" subrack.
  - ``S3.2-03`` (CUSTOM_FULL,  U22,     1U): 4x HV bias filter & guard-ring modules
    (matching 110x75 mm ``ibic_hv_bias_guard`` PCB with 2.5x54 mm HV creepage air-slot).
  - ``S3.3-04`` (COTS_ENV_ICD, U23,     1U): 1U EMI counting chassis & 10 MHz sync interface.
  - ``S3.3-01`` (COTS_ENV_ICD, U24,     1U): 2x redundant FPGA counting-gate processing bay.
  - ``S3.3-03`` (COTS_ENV_ICD, U25,     1U): 12-bit 50 MS/s FMC pulse-height ADC shelf.
  - ``S3.3-02`` (COTS_ENV_ICD, U26,     1U): Galvanic-isolated fiber/LVDS blanker transceiver.

Epistemic status: ``M0_M1_DETAILED_CAD_DESIGN_ONLY``, ``no_lab_measurement=True``,
``iec61508_certified=False``, ``semi_s2_certified=False``.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from hardware.cad_parts.core import (
    CF_SPECS,
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
    export_part_artifacts,
    list_physical_part_ids,
    make_box,
    make_cf_flange,
    make_cf_port_interface,
    make_chamfered_box,
    make_cylinder,
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
    transform_mesh,
    verify_watertight,
)

# ---------------------------------------------------------------------------
# Global Machine Coordinate Constants (Z = 0.0 mm = Wafer Active Top Plane)
# ---------------------------------------------------------------------------
Z_WAFER_TOP_MM: float = 0.0
RACK_BAY1_X_MM: float = 1480.0       # Master Bay 1 center X (X in [1180, 1780], 482.6 mm along X)
RACK_BAY1_FRONT_Y_MM: float = -410.0  # Front bezel face Y (handles reach -434.1 >= -438.0 rail plane)
RACK_U1_BOTTOM_Z_MM: float = -410.0   # Canonical Z_U(1) = +90.0 mm after +500.0 wafer shift
RACK_U_PITCH_MM: float = 44.45
RACK_WIDTH_MM: float = 482.6

# 16 circumferential azimuths (4 quadrants x 4 modules, avoiding 0/90/180/270 deg UHV ports
# and preserving a clear [36..58 deg] optical sight window for S4.5-02 fiducial microscope @ 50 deg!)
CSA_AZIMUTHS_DEG: tuple[float, ...] = (
    22.0, 35.0, 58.0, 70.0,
    114.0, 128.0, 142.0, 156.0,
    204.0, 218.0, 232.0, 246.0,
    294.0, 308.0, 322.0, 336.0,
)
# Master #309 verified CF63 analog feedthrough ports (clearing S5.1-01 R=245 & S5.2-04 @ 225 deg)
CF63_PORT_AZIMUTHS_DEG: tuple[float, ...] = (45.0, 115.0, 162.0, 315.0)
CF63_PORT_Z_MM: float = -105.0        # Canonical Z = +395.0 mm
CF63_FLANGE_FACE_R_MM: float = 245.5  # 0.5 mm Cu gasket gap outside S5.1-01 CF63 nozzle (R=245.0)

DEFAULT_S3_OUT_DIR: Path = REPO_ROOT / "hardware" / "cad_parts" / "out" / "S3"


def rack_u_center_z(u_start: int, u_count: int) -> float:
    """Return natural-frame Z center (mm) for ``u_count``-U chassis in ``U[u_start..u_start+u_count-1]``."""
    z_bot = RACK_U1_BOTTOM_Z_MM + (u_start - 1) * RACK_U_PITCH_MM
    return z_bot + 0.5 * u_count * RACK_U_PITCH_MM


def rack_center_y(depth_mm: float) -> float:
    """Return global Y center (mm) so front bezel sits at ``RACK_BAY1_FRONT_Y_MM`` (facing -Y)."""
    return RACK_BAY1_FRONT_Y_MM + 0.5 * depth_mm


def rack_u_height_mm(u_count: int, clearance_mm: float = 2.0) -> float:
    """Return physical chassis height (mm) with ±1.0 mm vertical clearance."""
    return u_count * RACK_U_PITCH_MM - clearance_mm


@dataclass(frozen=True)
class BuiltPart:
    """Self-contained mechanical part record pairing frozen ``PartDesign`` with watertight mesh."""

    design: PartDesign
    mesh: SolidMesh
    scad_features: tuple[ScadFeature, ...] = ()
    step_mesh: SolidMesh | None = None
    density_kg_m3: float | None = None
    reconciliation: dict[str, Any] | None = None
    thermal_checks: tuple[dict[str, Any], ...] = ()
    tolerance_checks: tuple[dict[str, Any], ...] = ()

    def world_mesh(self) -> SolidMesh:
        """Return the watertight solid transformed into global machine coordinates."""
        return transform_mesh(
            self.mesh,
            translation=self.design.world_origin_mm,
            rotation_deg=self.design.world_rotation_deg,
            name=f"{self.design.part_id}_world",
        )


# ---------------------------------------------------------------------------
# Reusable Mechanical Feature Builders (19" EIA-310 Rack Chassis & Arc Plates)
# ---------------------------------------------------------------------------
def _make_arc_plate(
    r_in: float,
    r_out: float,
    thickness: float,
    deg_start: float,
    deg_end: float,
    *,
    arc_steps: int = 16,
    center: tuple[float, float, float] = (0.0, 0.0, 0.0),
    name: str = "arc_plate",
    material: str = "OFHC Cu",
) -> SolidMesh:
    """Create a watertight extruded annular arc sector spanning ``[deg_start, deg_end]``."""
    ang_out = np.linspace(math.radians(deg_start), math.radians(deg_end), arc_steps + 1)
    ang_in = ang_out[::-1]
    poly: list[tuple[float, float]] = [
        (r_out * float(math.cos(a)), r_out * float(math.sin(a))) for a in ang_out
    ]
    poly.extend(
        (r_in * float(math.cos(a)), r_in * float(math.sin(a))) for a in ang_in
    )
    return make_plate_with_holes(
        outer_poly_2d=poly,
        holes_2d=[],
        thickness=thickness,
        center=center,
        name=name,
        material=material,
    )


def _make_rack_chassis_shell(
    u_count: int,
    depth_mm: float = 380.0,
    *,
    wall_mm: float = 2.5,
    front_thickness_mm: float = 4.0,
    front_handles: bool = True,
    rear_heatsink_fins: int = 0,
    front_connectors: list[tuple[float, float, float, float]] | None = None,  # (x, z, r, len)
    rear_connectors: list[tuple[float, float, float, float]] | None = None,
    internal_solids: list[SolidMesh] | None = None,
    name: str = "rack_chassis",
    material: str = "Al 6061",
) -> tuple[SolidMesh, SolidMesh, list[ScadFeature]]:
    """Build a genuine hollow 19" EIA-310 rack chassis facing ``-Y`` with width 482.6 mm along ``X``.

    Returns ``(full_mesh, compact_step_mesh, scad_features)`` with zero overlapping sub-shells.
    Local coordinates: ``X ∈ [-241.3, +241.3]`` (19" width = 482.6 mm),
    ``Y ∈ [-depth/2, +depth/2]`` (front bezel at ``-depth/2`` facing ``-Y``), ``Z ∈ [-H/2, +H/2]``.
    """
    h = rack_u_height_mm(u_count)
    body_w = 438.0  # Clears standard 450 mm 19" rack rail opening
    body_h = h - 1.5
    body_d = depth_mm - front_thickness_mm - 6.0
    y_front = -0.5 * depth_mm + 0.5 * front_thickness_mm
    y_body = y_front + 0.5 * front_thickness_mm + 0.1 + 0.5 * body_d
    y_rear = y_body + 0.5 * body_d + 0.1 + 0.5 * wall_mm

    # 1. Slotted EIA-310 front panel (axis="-y": local X -> +X, local Y -> +Z, local Z -> -Y)
    slot_z = max(8.0, 0.5 * h - 10.0)
    slots: list[tuple[float, float, float, float, float]] = [
        (-232.5, -slot_z, 10.0, 6.4, 0.0),
        (-232.5, slot_z, 10.0, 6.4, 0.0),
        (232.5, -slot_z, 10.0, 6.4, 0.0),
        (232.5, slot_z, 10.0, 6.4, 0.0),
    ]
    if u_count >= 3:
        slots.extend([(-232.5, 0.0, 10.0, 6.4, 0.0), (232.5, 0.0, 10.0, 6.4, 0.0)])

    front_plate = make_rect_plate_with_features(
        dx=RACK_WIDTH_MM,
        dy=h,
        thickness=front_thickness_mm,
        rect_slots=slots,
        axis="-y",
        center=(0.0, y_front, 0.0),
        name=f"{name}_front_panel",
        material=material,
    )

    # 2. Hollow rectangular extruded sleeve (single watertight shell, zero overlap!)
    outer_sleeve = rect_2d(body_w, body_h, ccw=True)
    inner_cavity = rect_2d(body_w - 2.0 * wall_mm, body_h - 2.0 * wall_mm, ccw=False)
    body_sleeve = make_plate_with_holes(
        outer_poly_2d=outer_sleeve,
        holes_2d=[inner_cavity],
        thickness=body_d,
        axis="-y",
        center=(0.0, y_body, 0.0),
        name=f"{name}_body_sleeve",
        material=material,
    )

    # 3. Rear bulkhead plate
    rear_plate = make_box(
        body_w,
        wall_mm,
        body_h,
        center=(0.0, y_rear, 0.0),
        name=f"{name}_rear_plate",
        material=material,
    )

    shells: list[SolidMesh] = [front_plate, body_sleeve, rear_plate]
    step_shells: list[SolidMesh] = [
        make_box(RACK_WIDTH_MM, front_thickness_mm, h, center=(0.0, y_front, 0.0), name=f"{name}_step_fp", material=material),
        body_sleeve,
        rear_plate,
    ]

    # 4. Front pull handles (protruding -Y <= 24.1 mm -> Y_min >= -434.1 > -438.0 rail plane)
    if front_handles:
        handle_h = min(0.68 * h, 68.0)
        handle_y = y_front - 0.5 * front_thickness_mm - 0.1
        for sx in (-1.0, 1.0):
            hx = sx * 212.0
            for sz in (-0.5 * handle_h + 4.0, 0.5 * handle_h - 4.0):
                shells.append(
                    make_box(
                        8.0, 16.0, 8.0,
                        center=(hx, handle_y - 8.0, sz),
                        name=f"{name}_handle_post",
                        material=material,
                    )
                )
            shells.append(
                make_box(
                    8.0, 8.0, handle_h,
                    center=(hx, handle_y - 20.1, 0.0),
                    name=f"{name}_handle_bar",
                    material=material,
                )
            )

    # 5. Optional rear extruded heatsink fins (protruding +Y, clearing rear connectors)
    if rear_heatsink_fins > 0:
        fin_y = y_rear + 0.5 * wall_mm + 0.1 + 11.0
        xs = np.linspace(-180.0, 180.0, rear_heatsink_fins)
        rconn_xs = [(cx, cr) for cx, _, cr, _ in (rear_connectors or ())]
        for idx, fx in enumerate(xs):
            if any(abs(float(fx) - cx) < (cr + 4.0) for cx, cr in rconn_xs):
                continue
            fin = make_box(
                3.0, 22.0, body_h - 8.0,
                center=(float(fx), fin_y, 0.0),
                name=f"{name}_fin_{idx}",
                material=material,
            )
            shells.append(fin)
            if idx % 2 == 0:
                step_shells.append(fin)

    # 6. Front/rear connector barrels
    if front_connectors:
        cy_base = y_front - 0.5 * front_thickness_mm - 0.1
        for idx, (cx, cz, cr, clen) in enumerate(front_connectors):
            shells.append(
                make_cylinder(
                    radius=cr,
                    height=clen,
                    segments=12,
                    axis="-y",
                    center=(cx, cy_base - 0.5 * clen, cz),
                    name=f"{name}_fconn_{idx}",
                    material="BeCu",
                )
            )
    if rear_connectors:
        cy_base = y_rear + 0.5 * wall_mm + 0.1
        for idx, (cx, cz, cr, clen) in enumerate(rear_connectors):
            shells.append(
                make_cylinder(
                    radius=cr,
                    height=clen,
                    segments=12,
                    axis="+y",
                    center=(cx, cy_base + 0.5 * clen, cz),
                    name=f"{name}_rconn_{idx}",
                    material="316LN",
                )
            )

    if internal_solids:
        shells.extend(internal_solids)

    scad_feats = [
        ScadFeature(
            "add_box",
            {"dx": RACK_WIDTH_MM, "dy": front_thickness_mm, "dz": h},
            translate=(0.0, y_front, 0.0),
            comment=f"19-inch EIA-310 {u_count}U front faceplate (482.6 x {h:.1f} mm, facing -Y)",
        ),
        ScadFeature(
            "add_box",
            {"dx": body_w, "dy": body_d + wall_mm, "dz": body_h},
            translate=(0.0, y_body + 0.5 * wall_mm, 0.0),
            comment="Hollow EMI-shielded chassis body",
        ),
        ScadFeature(
            "cut_slot",
            {"length": 10.0, "width": 6.4, "h": front_thickness_mm + 4.0},
            translate=(-232.5, y_front, slot_z),
            rotate=(90.0, 0.0, 0.0),
            comment="EIA-310 upper-left rack ear slot",
        ),
        ScadFeature(
            "cut_slot",
            {"length": 10.0, "width": 6.4, "h": front_thickness_mm + 4.0},
            translate=(232.5, y_front, slot_z),
            rotate=(90.0, 0.0, 0.0),
            comment="EIA-310 upper-right rack ear slot",
        ),
        ScadFeature(
            "cut_slot",
            {"length": 10.0, "width": 6.4, "h": front_thickness_mm + 4.0},
            translate=(-232.5, y_front, -slot_z),
            rotate=(90.0, 0.0, 0.0),
            comment="EIA-310 lower-left rack ear slot",
        ),
        ScadFeature(
            "cut_slot",
            {"length": 10.0, "width": 6.4, "h": front_thickness_mm + 4.0},
            translate=(232.5, y_front, -slot_z),
            rotate=(90.0, 0.0, 0.0),
            comment="EIA-310 lower-right rack ear slot",
        ),
    ]

    full_mesh = merge_solids(shells, name=name, material=material)
    compact_step = merge_solids(step_shells, name=f"{name}_step", material=material)
    return full_mesh, compact_step, scad_feats


# ---------------------------------------------------------------------------
# Individual Part Builders (14 / 14 Physical Parts of S3)
# ---------------------------------------------------------------------------
def _build_s3_1_01() -> BuiltPart:
    """S3.1-01: Pixelated p-i-n IBIC detector wafer (Ø50.0 x 0.525 mm Si) w/ guard-ring keepout."""
    # Single-shell revolved wafer with recessed annular guard-ring moat (R=20.0..22.6 mm, depth 0.08 mm)
    # Local z in [-0.2625, +0.2625]; world_origin z = -0.2625 -> active top plane at Z = 0.000 mm!
    hz = 0.2625
    z_moat = hz - 0.080
    profile = [
        (0.0, -hz),
        (25.0, -hz),
        (25.0, hz),
        (22.6, hz),
        (22.6, z_moat),
        (20.0, z_moat),
        (20.0, hz),
        (0.0, hz),
    ]
    mesh = make_revolved_profile(
        profile, segments=64, axis="z", name="S3.1-01_pin_ibic_wafer", material="Si"
    )
    scad_feats = (
        ScadFeature("add_revolve", {"points": profile}, comment="Ø50x0.525 mm high-res Si p-i-n IBIC wafer w/ guard-ring moat"),
    )
    design = make_part_design_from_bom(
        "S3.1-01",
        design_tier="CUSTOM_FULL",
        material="Si",
        surface_finish_ra_um=0.05,
        world_origin_mm=(0.0, 0.0, -0.2625),
        ports=(
            PortInterface(
                name="active_implant_plane",
                kind="optical",
                position_mm=(0.0, 0.0, 0.2625),
                normal=(0.0, 0.0, 1.0),
                standard="Arch-B 16x16 mm Write Field",
                mating_part_id="S2.3-01",
                od_mm=50.0,
                notes="Global Z=0.000 mm wafer active top plane; WD=0.250 mm to S2.3-01",
            ),
            PortInterface(
                name="wafer_pocket_seat",
                kind="mechanical",
                position_mm=(0.0, 0.0, -0.2625),
                normal=(0.0, 0.0, -1.0),
                standard="Ø50.0 mm Wafer in Ø50.4 mm AlN Pocket",
                mating_part_id="S3.1-03",
                od_mm=50.0,
            ),
        ),
        dimensions=(
            DimensionCallout("OD", 50.0, 0.02, -0.02, view="top", prefix="Ø"),
            DimensionCallout("THK", 0.525, 0.010, -0.010, view="front", decimals=3),
            DimensionCallout("GUARD_MOAT_ID", 40.0, 0.02, -0.02, view="top", prefix="Ø"),
            DimensionCallout("GUARD_MOAT_OD", 45.2, 0.02, -0.02, view="top", prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.002, datum_primary="", feature_note="ACTIVE TOP FACE Z=0"),
            GDTFrame("parallelism", 0.005, datum_primary="A", feature_note="REAR OHMIC SURFACE"),
            GDTFrame("concentricity", 0.010, diameter_zone=True, datum_primary="B", feature_note="GUARD-RING MOAT"),
        ),
        notes=(
            "Global Z=0.000 mm active wafer top plane; 16x16 mm central 32x32 Arch-B write zone.",
            "Concentric guard-ring keepout moat R=20.0..22.6 mm suppresses edge leakage <10 pA @ 20 V.",
            "Exp72/91/127: high-resistivity >10 kOhm*cm Si p-i-n, C_det<=0.5 pF/pixel, eta=0.99936 @ 100 K.",
        ),
        scad_params=(
            ("wafer_od_mm", 50.0),
            ("wafer_thickness_mm", 0.525),
            ("active_field_mm", 16.0),
            ("guard_moat_r_in_mm", 20.0),
            ("guard_moat_r_out_mm", 22.6),
        ),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats)


def _build_s3_1_02() -> BuiltPart:
    """S3.1-02: Cryo Al/Ti/Au 3-ring guard metallization, rear ohmic disk & 16 wire-bond tabs."""
    shells: list[SolidMesh] = []
    # 3 concentric Al/Ti/Au guard rings seated inside S3.1-01 moat (Z in [-0.060, +0.020], clearing -0.080 moat floor)
    for idx, (ri, ro) in enumerate(((20.3, 20.7), (21.1, 21.5), (21.9, 22.3)), start=1):
        shells.append(
            make_tube(
                r_in=ri, r_out=ro, height=0.080, segments=48,
                center=(0.0, 0.0, -0.020), name=f"S3.1-02_guard_ring_{idx}", material="Au",
            )
        )
    # Rear ohmic bias metallization disk (Z in [-0.640, -0.560], clears S3.1-01 bottom -0.525 & carrier floor -0.850)
    shells.append(
        make_cylinder(
            radius=23.0, height=0.080, segments=48,
            center=(0.0, 0.0, -0.600), name="S3.1-02_rear_ohmic", material="Au",
        )
    )
    # 16 peripheral wire-bond bridge tabs at CSA azimuths (R=25.3..28.4 mm, Z in [-0.060, +0.080])
    for idx, ang in enumerate(CSA_AZIMUTHS_DEG):
        rad = math.radians(ang)
        r_mid = 26.85
        tab = make_box(3.1, 1.4, 0.14, name=f"S3.1-02_wirebond_{idx}", material="Au")
        tab = transform_mesh(
            tab,
            rotation_deg=(0.0, 0.0, ang),
            translation=(r_mid * math.cos(rad), r_mid * math.sin(rad), 0.010),
        )
        shells.append(tab)

    mesh = merge_solids(shells, name="S3.1-02_guard_metallization", material="Au")
    # Compact STEP mesh preserving 3 guard rings + rear ohmic + 16 tabs
    step_shells = [
        make_tube(20.3, 22.3, 0.080, segments=24, center=(0.0, 0.0, -0.020), name="guard_band", material="Au"),
        make_cylinder(23.0, 0.080, segments=24, center=(0.0, 0.0, -0.600), name="rear_ohmic", material="Au"),
    ]
    for idx, ang in enumerate(CSA_AZIMUTHS_DEG):
        rad = math.radians(ang)
        t = transform_mesh(
            make_box(3.1, 1.4, 0.14, material="Au"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(26.85 * math.cos(rad), 26.85 * math.sin(rad), 0.010),
        )
        step_shells.append(t)
    step_mesh = merge_solids(step_shells, name="S3.1-02_step", material="Au")

    scad_feats = (
        ScadFeature("add_tube", {"od": 41.4, "id": 40.6, "h": 0.08}, translate=(0.0, 0.0, -0.02), comment="Inner Al/Ti/Au guard ring #1"),
        ScadFeature("add_tube", {"od": 43.0, "id": 42.2, "h": 0.08}, translate=(0.0, 0.0, -0.02), comment="Middle Al/Ti/Au guard ring #2"),
        ScadFeature("add_tube", {"od": 44.6, "id": 43.8, "h": 0.08}, translate=(0.0, 0.0, -0.02), comment="Outer Al/Ti/Au guard ring #3"),
        ScadFeature("add_cylinder", {"d": 46.0, "h": 0.08}, translate=(0.0, 0.0, -0.60), comment="Rear ohmic bias metallization"),
    )
    design = make_part_design_from_bom(
        "S3.1-02",
        design_tier="CUSTOM_FULL",
        material="Au",
        surface_finish_ra_um=0.1,
        world_origin_mm=(0.0, 0.0, 0.0),
        ports=(
            PortInterface(
                name="wirebond_pad_ring",
                kind="electrical",
                position_mm=(0.0, 0.0, 0.01),
                normal=(0.0, 0.0, 1.0),
                standard="16x Cryo Au Wire-Bond Tabs",
                mating_part_id="S3.1-04",
                od_mm=56.8,
                bore_mm=50.6,
            ),
            PortInterface(
                name="rear_ohmic_bias",
                kind="electrical",
                position_mm=(0.0, 0.0, -0.60),
                normal=(0.0, 0.0, -1.0),
                standard="0-100 V Reverse Bias Ohmic Plane",
                mating_part_id="S3.1-01",
                od_mm=46.0,
            ),
        ),
        dimensions=(
            DimensionCallout("GUARD_OD", 44.6, 0.02, -0.02, view="top", prefix="Ø"),
            DimensionCallout("OHMIC_OD", 46.0, 0.05, -0.05, view="top", prefix="Ø"),
            DimensionCallout("PAD_SPAN_OD", 56.8, 0.05, -0.05, view="top", prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.010, diameter_zone=True, datum_primary="B", feature_note="3-RING GUARD STACK"),
            GDTFrame("profile_surface", 0.015, datum_primary="A", feature_note="WIREBOND MAX HEIGHT < WD"),
        ),
        notes=(
            "3 concentric Al/Ti/Au cryo-compatible guard rings (<10 pA leakage @ 20 V) + rear ohmic contact.",
            "Maximum Z height +0.080 mm maintains >=0.170 mm clearance below S2.3-01 Arch-B WD=0.250 mm.",
        ),
        scad_params=(
            ("n_guard_rings", 3),
            ("n_wirebond_tabs", 16),
            ("ohmic_od_mm", 46.0),
        ),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats, step_mesh=step_mesh)


def _build_s3_1_03() -> BuiltPart:
    """S3.1-03: 80x80 mm AlN/Sapphire wafer carrier w/ Ø50.4 pocket, thermal boss & alignment pins."""
    # Import slot_2d locally for radial kinematic thermal-relief slots
    from hardware.cad_parts.core import slot_2d

    # World origin at (0, 0, -3.000):
    # - Upper pocket collar (80x80 w/ Ø50.4 wafer pocket + 4x M3 radial slots @ PCD 96.0 mm + 3x Ø3.0 pin holes):
    #   Z_world [-0.85, -0.15] -> z_loc [+2.15, +2.85]
    # - Main ceramic floor (80x80 chamfered w/ 4x M3 radial slots @ PCD 96.0 mm + 3x Ø3.0 pin holes + Ø10 vent):
    #   Z_world [-5.00, -0.86] -> z_loc [-2.00, +2.14]
    # - Rear central AlN thermal boss (Ø34 / Ø10 bore) extending to Z_world=-6.38 mm (closing 0.55 mm gap into S6.2-01 Ø34.5 pocket!):
    #   Z_world [-6.38, -5.01] -> z_loc [-3.38, -2.01]
    # - 4x spring-loaded kinematic Ti-6Al-4V Belleville clamp washers seated atop radial slots @ PCD 96.0 mm (45/135/225/315 deg)
    # - 3x kinematic alignment pin bosses (Ø2.90 @ R=33 mm, 30/150/270 deg): Z_world [-6.38, -5.01]
    cham = 2.5
    hx, hy = 40.0, 40.0
    outer_sq = [
        (-hx + cham, -hy), (hx - cham, -hy),
        (hx, -hy + cham), (hx, hy - cham),
        (hx - cham, hy), (-hx + cham, hy),
        (-hx, hy - cham), (-hx, -hy + cham),
    ]
    # Exact PCD = 96.0 mm (R = 48.0 mm) mating S6.2-01 OFHC Cu chuck!
    # 48.0 * cos(45 deg) = 33.941125 mm; radial slots (±0.5 mm radial freedom >> 0.126 mm Cu-AlN cooldown slip!)
    m3_angles = (45.0, 135.0, 225.0, 315.0)
    m3_r = 48.0
    m3_pts = [(m3_r * math.cos(math.radians(a)), m3_r * math.sin(math.radians(a))) for a in m3_angles]
    pin_angles = (30.0, 150.0, 270.0)
    pin_pts = [(33.0 * math.cos(math.radians(a)), 33.0 * math.sin(math.radians(a))) for a in pin_angles]

    upper_holes = [circle_2d(25.2, segments=36, ccw=False)]
    upper_holes.extend(
        slot_2d(4.4, 3.4, cx=x, cy=y, angle_deg=a, arc_seg=4, ccw=False)
        for (x, y), a in zip(m3_pts, m3_angles)
    )
    upper_holes.extend(circle_2d(1.5, cx=x, cy=y, segments=12, ccw=False) for x, y in pin_pts)
    upper_collar = make_plate_with_holes(
        outer_sq, upper_holes, thickness=0.70, center=(0.0, 0.0, 2.50),
        name="S3.1-03_pocket_collar", material="AlN",
    )

    lower_holes = [circle_2d(5.0, segments=20, ccw=False)]
    lower_holes.extend(
        slot_2d(4.4, 3.4, cx=x, cy=y, angle_deg=a, arc_seg=4, ccw=False)
        for (x, y), a in zip(m3_pts, m3_angles)
    )
    lower_holes.extend(circle_2d(1.5, cx=x, cy=y, segments=12, ccw=False) for x, y in pin_pts)
    main_plate = make_plate_with_holes(
        outer_sq, lower_holes, thickness=4.14, center=(0.0, 0.0, 0.07),
        name="S3.1-03_aln_base", material="AlN",
    )

    thermal_boss = make_tube(
        r_in=5.0, r_out=17.0, height=1.37, segments=36,
        center=(0.0, 0.0, -2.695), name="S3.1-03_thermal_boss", material="AlN",
    )

    pins: list[SolidMesh] = []
    for idx, (px, py) in enumerate(pin_pts, start=1):
        pins.append(
            make_cylinder(
                radius=1.45, height=1.37, segments=16,
                center=(px, py, -2.695), name=f"S3.1-03_align_pin_{idx}", material="Ti-6Al-4V",
            )
        )

    # 4x spring-loaded kinematic Ti-6Al-4V Belleville clamp washers @ PCD=96.0 mm (Z_world=[-0.14, +0.16])
    # Relieves 126.0 um Cu-AlN differential cooldown contraction with zero radial shear!
    ti_clamps: list[SolidMesh] = []
    for idx, (cx, cy) in enumerate(m3_pts, start=1):
        ti_clamps.append(
            make_tube(
                r_in=1.75, r_out=4.0, height=0.30, segments=18,
                center=(cx, cy, 3.01), name=f"S3.1-03_ti_spring_clamp_{idx}", material="Ti-6Al-4V",
            )
        )

    mesh = merge_solids([upper_collar, main_plate, thermal_boss, *pins, *ti_clamps], name="S3.1-03_aln_carrier", material="AlN")

    # Compact STEP mesh preserving 80x80 chamfered pocket plate + thermal boss + Ti clamps
    step_collar = make_plate_with_holes(
        outer_sq, [circle_2d(25.2, segments=24, ccw=False)], thickness=0.70,
        center=(0.0, 0.0, 2.50), name="S3.1-03_step_collar", material="AlN",
    )
    step_base = make_plate_with_holes(
        outer_sq, [circle_2d(5.0, segments=16, ccw=False)], thickness=4.14,
        center=(0.0, 0.0, 0.07), name="S3.1-03_step_base", material="AlN",
    )
    step_boss = make_tube(5.0, 17.0, 1.37, segments=20, center=(0.0, 0.0, -2.695), name="S3.1-03_step_boss", material="AlN")
    step_mesh = merge_solids([step_collar, step_base, step_boss], name="S3.1-03_step", material="AlN")

    # Cryogenic differential thermal contraction checks: 300 K -> 100 K and 300 K -> 20 mK
    tc_wafer_100k = check_cold_clearance(
        "AlN", "Si", nominal_outer_id_mm=50.40, nominal_inner_od_mm=50.00,
        t_cold_k=100.0, outer_id_tol_mm=0.02, inner_od_tol_mm=0.02,
        min_required_radial_clearance_mm=0.10,
    )
    tc_wafer_20mk = check_cold_clearance(
        "AlN", "Si", nominal_outer_id_mm=50.40, nominal_inner_od_mm=50.00,
        t_cold_k=0.02, outer_id_tol_mm=0.02, inner_od_tol_mm=0.02,
        min_required_radial_clearance_mm=0.10,
    )
    tc_boss_100k = check_cold_clearance(
        "OFHC Cu", "AlN", nominal_outer_id_mm=34.50, nominal_inner_od_mm=34.00,
        t_cold_k=100.0, outer_id_tol_mm=0.03, inner_od_tol_mm=0.02,
        min_required_radial_clearance_mm=0.10,
    )
    tc_boss_20mk = check_cold_clearance(
        "OFHC Cu", "AlN", nominal_outer_id_mm=34.50, nominal_inner_od_mm=34.00,
        t_cold_k=0.02, outer_id_tol_mm=0.03, inner_od_tol_mm=0.02,
        min_required_radial_clearance_mm=0.10,
    )
    # Z stackup from carrier bottom datum to wafer active top surface (target Z = 0.000 ± 0.025 mm)
    z_stack = check_tolerance_stack(
        [
            ToleranceContributor("aln_carrier_floor", 4.150, 0.005, -0.005, sign=+1.0),
            ToleranceContributor("ohmic_gap_nominal", 0.325, 0.010, -0.010, sign=+1.0),
            ToleranceContributor("si_wafer_thickness", 0.525, 0.010, -0.010, sign=+1.0),
            ToleranceContributor("datum_offset", 5.000, 0.000, 0.000, sign=-1.0),
        ],
        target_min_mm=-0.025,
        target_max_mm=+0.025,
    )

    scad_feats = (
        ScadFeature("add_box", {"dx": 80.0, "dy": 80.0, "dz": 4.85}, translate=(0.0, 0.0, 0.425), comment="80x80 mm AlN/Sapphire carrier plate (Exp80 BC1)"),
        ScadFeature("add_tube", {"od": 34.0, "id": 10.0, "h": 1.37}, translate=(0.0, 0.0, -2.695), comment="Rear central thermal boss Ø34 mm mating S6.2-01 Ø34.5 pocket"),
        ScadFeature("cut_hole", {"d": 50.4, "h": 1.0}, translate=(0.0, 0.0, 2.50), comment="Ø50.4 mm stepped wafer pocket"),
        ScadFeature("cut_bolt_circle", {"pcd": 66.0, "bolt_d": 3.0, "count": 3, "h": 7.0}, comment="3x Ø3.0 H7 kinematic alignment pin holes"),
        ScadFeature("cut_slot", {"length": 4.4, "width": 3.4, "h": 7.0}, translate=(m3_pts[0][0], m3_pts[0][1], 0.0), rotate=(0.0, 0.0, 45.0), comment="Radial M3 kinematic slot #1 @ PCD 96.0 mm"),
        ScadFeature("cut_slot", {"length": 4.4, "width": 3.4, "h": 7.0}, translate=(m3_pts[1][0], m3_pts[1][1], 0.0), rotate=(0.0, 0.0, 135.0), comment="Radial M3 kinematic slot #2 @ PCD 96.0 mm"),
        ScadFeature("cut_slot", {"length": 4.4, "width": 3.4, "h": 7.0}, translate=(m3_pts[2][0], m3_pts[2][1], 0.0), rotate=(0.0, 0.0, 225.0), comment="Radial M3 kinematic slot #3 @ PCD 96.0 mm"),
        ScadFeature("cut_slot", {"length": 4.4, "width": 3.4, "h": 7.0}, translate=(m3_pts[3][0], m3_pts[3][1], 0.0), rotate=(0.0, 0.0, 315.0), comment="Radial M3 kinematic slot #4 @ PCD 96.0 mm"),
    )

    design = make_part_design_from_bom(
        "S3.1-03",
        design_tier="CUSTOM_FULL",
        material="AlN",
        surface_finish_ra_um=0.2,
        world_origin_mm=(0.0, 0.0, -3.000),
        ports=(
            PortInterface(
                name="wafer_pocket",
                kind="mechanical",
                position_mm=(0.0, 0.0, 2.15),
                normal=(0.0, 0.0, 1.0),
                standard="Ø50.40 mm Stepped Pocket",
                mating_part_id="S3.1-01",
                bore_mm=50.4,
            ),
            PortInterface(
                name="rear_thermal_boss",
                kind="thermal",
                position_mm=(0.0, 0.0, -3.38),
                normal=(0.0, 0.0, -1.0),
                standard="Ø34.0 mm Cryo Thermal Boss + 4x M3 Radial-Slot Ti Clamps @ PCD 96.0 mm",
                mating_part_id="S6.2-01",
                od_mm=34.0,
                pcd_mm=96.0,
                bolt_count=4,
                bolt_hole_mm=3.4,
                bolt_spec="M3",
            ),
        ),
        dimensions=(
            DimensionCallout("WIDTH_X", 80.0, 0.02, -0.02, view="top"),
            DimensionCallout("WIDTH_Y", 80.0, 0.02, -0.02, view="top"),
            DimensionCallout("POCKET_ID", 50.40, 0.02, -0.02, view="top", prefix="Ø"),
            DimensionCallout("CHUCK_PCD", 96.00, 0.02, -0.02, view="top", prefix="Ø"),
            DimensionCallout("THERMAL_BOSS_OD", 34.00, 0.02, -0.02, view="front", prefix="Ø"),
            DimensionCallout("TOTAL_H", 6.54, 0.02, -0.02, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.005, datum_primary="", feature_note="POCKET FLOOR DATUM A"),
            GDTFrame("parallelism", 0.005, datum_primary="A", feature_note="THERMAL BOSS SEAT"),
            GDTFrame("position", 0.010, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="4x M3 RADIAL SLOTS @ PCD 96.0 MM"),
        ),
        notes=(
            "Exp80 BC1 80x80 mm AlN/Sapphire carrier aligned to S6.2-01 bolt circle PCD=96.0 mm (45/135/225/315 deg) via 4x radial kinematic slots + Ti-6Al-4V Belleville spring clamps (0 N cooldown radial shear vs 355.6 N/strut rigid).",
            "Rear Ø34.0 mm central AlN thermal boss seats directly into S6.2-01 Ø34.5 mm pocket at Z_world=-6.38 mm (0.02 mm In foil interface, eliminating 0.55 mm floating Z-gap).",
            f"300K->100K AlN pocket vs Si wafer WC rad clearance: {tc_wafer_100k.cold_worst_case_radial_clearance_mm:.4f} mm (PASS).",
            f"300K->20mK AlN pocket vs Si wafer WC rad clearance: {tc_wafer_20mk.cold_worst_case_radial_clearance_mm:.4f} mm (PASS).",
            f"300K->20mK OFHC Cu chuck Ø34.5 pocket vs Ø34 AlN boss WC rad clearance: {tc_boss_20mk.cold_worst_case_radial_clearance_mm:.4f} mm (PASS).",
        ),
        scad_params=(
            ("carrier_size_mm", 80.0),
            ("wafer_pocket_id_mm", 50.4),
            ("chuck_bolt_pcd_mm", 96.0),
            ("radial_slot_length_mm", 4.4),
            ("thermal_boss_od_mm", 34.0),
            ("thermal_boss_z_bot_mm", -6.38),
            ("align_pin_pcd_mm", 66.0),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=scad_feats,
        step_mesh=step_mesh,
        thermal_checks=(tc_wafer_100k.to_dict(), tc_wafer_20mk.to_dict(), tc_boss_100k.to_dict(), tc_boss_20mk.to_dict()),
        tolerance_checks=(z_stack.to_dict(),),
    )


def _build_s3_1_04() -> BuiltPart:
    """S3.1-04: Non-magnetic Au-plated BeCu cantilever spring contact ring + Faraday shield shroud w/ 50 deg optical sight window."""
    # World origin = (0, 0, +1.000) -> local z = z_world - 1.000
    # Slotted 346-deg arc (56..404 deg) opens a clean 12-deg dark-field optical sight window (44..56 deg)
    # centered on FIDUCIAL_PORT_AZIMUTH_DEG=50.0 deg for unoccluded S4.5-02 -> S3.1-01 fiducial LOS!
    ang_out = np.linspace(math.radians(56.0), math.radians(404.0), 65)
    ang_in = ang_out[::-1]
    main_poly: list[tuple[float, float]] = [(39.2 * float(math.cos(a)), 39.2 * float(math.sin(a))) for a in ang_out]
    main_poly.extend((32.0 * float(math.cos(a)), 32.0 * float(math.sin(a))) for a in ang_in)
    bolt_holes = [
        circle_2d(1.35, cx=35.6 * math.cos(math.radians(a)), cy=35.6 * math.sin(math.radians(a)), segments=12, ccw=False)
        for a in (0.0, 60.0, 120.0, 180.0, 240.0, 300.0)
    ]
    main_ring = make_plate_with_holes(
        outer_poly_2d=main_poly, holes_2d=bolt_holes, thickness=1.80,
        center=(0.0, 0.0, 0.10), name="S3.1-04_contact_ring", material="BeCu",
    )
    # Outer Faraday bias shield shroud collar with matching [44..56 deg] optical window
    shield_collar = _make_arc_plate(
        r_in=39.35, r_out=41.0, thickness=2.40, deg_start=56.0, deg_end=404.0,
        arc_steps=48, center=(0.0, 0.0, 0.20), name="S3.1-04_faraday_shield", material="BeCu",
    )
    # 16 inward BeCu/Au load-lock cantilever spring fingers (R=28.8..31.9, Z_world in [-0.04, +0.18] -> z_loc [-1.04, -0.82])
    fingers: list[SolidMesh] = []
    for idx, ang in enumerate(CSA_AZIMUTHS_DEG):
        rad = math.radians(ang)
        r_mid = 30.35
        finger = make_box(3.0, 1.8, 0.20, name=f"S3.1-04_cantilever_{idx}", material="BeCu")
        finger = transform_mesh(
            finger,
            rotation_deg=(0.0, 0.0, ang),
            translation=(r_mid * math.cos(rad), r_mid * math.sin(rad), -0.93),
        )
        fingers.append(finger)

    mesh = merge_solids([main_ring, shield_collar, *fingers], name="S3.1-04_becu_contact_ring", material="BeCu")
    step_mesh = merge_solids(
        [
            _make_arc_plate(32.0, 39.2, 1.80, 56.0, 404.0, arc_steps=28, center=(0.0, 0.0, 0.10), material="BeCu"),
            _make_arc_plate(39.35, 41.0, 2.40, 56.0, 404.0, arc_steps=28, center=(0.0, 0.0, 0.20), material="BeCu"),
            *fingers,
        ],
        name="S3.1-04_step",
        material="BeCu",
    )
    tc_becu_100k = check_cold_clearance(
        "BeCu", "Si", nominal_outer_id_mm=64.0, nominal_inner_od_mm=50.0,
        t_cold_k=100.0, outer_id_tol_mm=0.05, inner_od_tol_mm=0.02,
        min_required_radial_clearance_mm=5.0,
    )
    scad_feats = (
        ScadFeature("add_tube", {"od": 78.4, "id": 64.0, "h": 1.8}, translate=(0.0, 0.0, 0.10), comment="BeCu/Au cantilever spring base ring (Ø64/Ø78.4)"),
        ScadFeature("add_tube", {"od": 82.0, "id": 78.7, "h": 2.4}, translate=(0.0, 0.0, 0.20), comment="Integrated outer Faraday bias shield shroud"),
        ScadFeature("cut_bolt_circle", {"pcd": 71.2, "bolt_d": 2.7, "count": 6, "h": 4.0}, translate=(0.0, 0.0, 0.10), comment="6x M2.5 mounting bolt circle"),
    )
    design = make_part_design_from_bom(
        "S3.1-04",
        design_tier="CUSTOM_FULL",
        material="BeCu",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, 1.000),
        ports=(
            PortInterface(
                name="cantilever_contacts",
                kind="electrical",
                position_mm=(0.0, 0.0, -0.93),
                normal=(0.0, 0.0, -1.0),
                standard="16x Au-Plated BeCu Cantilever Springs (<50 mOhm)",
                mating_part_id="S3.1-02",
                bore_mm=57.6,
                od_mm=64.0,
            ),
            PortInterface(
                name="coax_terminal_ring",
                kind="rf",
                position_mm=(0.0, 0.0, 0.35),
                normal=(1.0, 0.0, 0.0),
                standard="16x Radial Micro-Coax Launches",
                mating_part_id="S3.2-04",
                od_mm=82.0,
            ),
            PortInterface(
                name="mount_bolts",
                kind="bolt",
                position_mm=(0.0, 0.0, 0.10),
                normal=(0.0, 0.0, -1.0),
                standard="6x M2.5 @ PCD 71.2 mm",
                mating_part_id="S3.1-03",
                pcd_mm=71.2,
                bolt_count=6,
                bolt_hole_mm=2.7,
                bolt_spec="M2.5",
            ),
        ),
        dimensions=(
            DimensionCallout("RING_ID", 64.0, 0.02, -0.02, view="top", prefix="Ø"),
            DimensionCallout("SHIELD_OD", 82.0, 0.05, -0.05, view="top", prefix="Ø"),
            DimensionCallout("BOLT_PCD", 71.2, 0.02, -0.02, view="top", prefix="Ø"),
            DimensionCallout("RING_H", 2.40, 0.02, -0.02, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.010, datum_primary="", feature_note="SPRING CONTACT PLANE"),
            GDTFrame("position", 0.010, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="16x CANTILEVER TIPS"),
        ),
        notes=(
            "Load-lock wafer-exchange compatible non-magnetic BeCu + 2 um Au spring contact ring (<50 mOhm).",
            "Clears S2.3-01 Arch-B mini-lens (OD 60 mm, WD 0.25 mm) by 2.0 mm radially and S2.4-02 by 0.6 mm vertically.",
            f"300K->100K BeCu ring vs Si wafer WC rad clearance: {tc_becu_100k.cold_worst_case_radial_clearance_mm:.3f} mm (PASS).",
        ),
        scad_params=(
            ("ring_id_mm", 64.0),
            ("shield_od_mm", 82.0),
            ("n_spring_fingers", 16),
            ("bolt_pcd_mm", 71.2),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=scad_feats,
        step_mesh=step_mesh,
        thermal_checks=(tc_becu_100k.to_dict(),),
    )


def _build_s3_2_01() -> BuiltPart:
    """S3.2-01: All 16x 100 K cold-island LTC6268 8-ch CSA modules + OFHC thermal straps."""
    # World origin = (0, 0, -8.500) -> local z = z_world + 8.500
    # Modules span R in [86.0, 118.0] mm, Z_world in [-14.0, -3.2] mm -> z_loc in [-5.5, +5.3]
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []

    for idx, ang in enumerate(CSA_AZIMUTHS_DEG):
        rad = math.radians(ang)
        ca, sa = math.cos(rad), math.sin(rad)
        r_mod = 102.0  # radial span [86.0, 118.0]

        # 1) OFHC Cu cold-clamp baseplate (32 x 14.5 x 2.5 mm, z_loc [-5.5, -3.0])
        base = transform_mesh(
            make_box(32.0, 14.5, 2.5, name=f"csa_{idx}_cu_base", material="OFHC Cu"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(r_mod * ca, r_mod * sa, -4.25),
        )
        # 2) Rogers RO4350B / Al2O3 8-ch LTC6268 PCB (30 x 13.5 x 1.6 mm, z_loc [-2.9, -1.3])
        pcb = transform_mesh(
            make_box(30.0, 13.5, 1.6, name=f"csa_{idx}_rogers_pcb", material="Rogers"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(r_mod * ca, r_mod * sa, -2.10),
        )
        # 3) CNC EMI shield cover (30 x 13.5 x 6.4 mm, z_loc [-1.2, +5.2])
        lid = transform_mesh(
            make_chamfered_box(30.0, 13.5, 6.4, chamfer=1.0, name=f"csa_{idx}_emi_lid", material="Al 6061"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(r_mod * ca, r_mod * sa, 2.00),
        )
        # 4) Flexible OFHC Cu S-braid thermal strap (R=118.4..133.6 mm -> length 15.2 mm, z_loc=-3.8)
        strap = make_s_braid(
            length_mm=15.0, s_amplitude_mm=2.4, width_mm=7.0, thickness_mm=1.2,
            n_steps=14, lug_length_mm=0.0, axis="+x",
            name=f"csa_{idx}_strap", material="OFHC Cu",
        )
        strap = transform_mesh(
            strap,
            rotation_deg=(0.0, 0.0, ang),
            translation=(126.0 * ca, 126.0 * sa, -3.80),
        )
        shells.extend([base, pcb, lid, strap])

        # Compact STEP proxy for each of the 16 modules (16 x 12 = 192 faces)
        step_shells.append(
            transform_mesh(
                make_box(32.0, 14.5, 10.8, material="OFHC Cu"),
                rotation_deg=(0.0, 0.0, ang),
                translation=(r_mod * ca, r_mod * sa, -0.10),
            )
        )

    # 4 quadrant 100 K OFHC Cu thermal-bus manifold arcs (R=134..142 mm, Z_world [-14.0, -9.0] -> z_loc [-5.5, -0.5])
    quad_spans = ((19.0, 73.0), (110.0, 160.0), (200.0, 250.0), (290.0, 340.0))
    for q_idx, (d0, d1) in enumerate(quad_spans, start=1):
        arc = _make_arc_plate(
            r_in=134.0, r_out=142.0, thickness=5.0, deg_start=d0, deg_end=d1,
            arc_steps=12, center=(0.0, 0.0, -3.0),
            name=f"S3.2-01_100k_bus_q{q_idx}", material="OFHC Cu",
        )
        shells.append(arc)
        step_shells.append(
            _make_arc_plate(
                r_in=134.0, r_out=142.0, thickness=5.0, deg_start=d0, deg_end=d1,
                arc_steps=6, center=(0.0, 0.0, -3.0),
                name=f"S3.2-01_step_bus_q{q_idx}", material="OFHC Cu",
            )
        )

    mesh = merge_solids(shells, name="S3.2-01_16x_cold_island_csa", material="OFHC Cu")
    step_mesh = merge_solids(step_shells, name="S3.2-01_step", material="OFHC Cu")

    # Thermal contraction verification 300 K -> 100 K: 100 K OFHC Cu cold-island inner bore vs 80x80 AlN carrier diagonal
    tc_ring_vs_aln = check_cold_clearance(
        "OFHC Cu", "AlN", nominal_outer_id_mm=172.0, nominal_inner_od_mm=113.14,
        t_cold_k=100.0, outer_id_tol_mm=0.20, inner_od_tol_mm=0.05,
        min_required_radial_clearance_mm=25.0,
    )
    tc_clamp_vs_pcb = check_cold_clearance(
        "OFHC Cu", "Al2O3", nominal_outer_id_mm=32.0, nominal_inner_od_mm=30.0,
        t_cold_k=100.0, outer_id_tol_mm=0.05, inner_od_tol_mm=0.05,
        min_required_radial_clearance_mm=0.80,
    )

    scad_feats = tuple(
        [
            ScadFeature(
                "add_box",
                {"dx": 32.0, "dy": 14.5, "dz": 10.8},
                translate=(102.0 * math.cos(math.radians(a)), 102.0 * math.sin(math.radians(a)), -0.10),
                rotate=(0.0, 0.0, a),
                comment=f"100 K Cold-Island 8-ch LTC6268 CSA Module #{i + 1} ({a:.0f} deg)",
            )
            for i, a in enumerate(CSA_AZIMUTHS_DEG)
        ]
    )

    reconciliation = {
        "issue": "Legacy params.py CAD lumped 16x 8-ch LTC6268 CSA modules into 2 placeholder boxes at +-Y; bench KiCad prototype ibic_cold_csa_100k is 125x105 mm.",
        "bom_spec": "16 modules x 8-ch LTC6268 @ 100 K cold island (128 ch total, Cf=0.25 pF, Rf=1 GOhm, tau=1.2 us, ENC=24.1 e-, eta=0.99936).",
        "cad_resolution": "Instantiated all 16 distinct 100 K cryo-hybrid CSA modules (32x14.5x10.8 mm each) in 4x4 radial quadrants (R=86..118 mm, Z=-14..-3.2 mm inside 36 mm Exp125 split gap) with 16 OFHC Cu thermal straps + 4 quadrant 100 K bus arcs (R=134..142 mm), clearing all 4 cardinal UHV ports & <5 cm coax limit.",
    }

    design = make_part_design_from_bom(
        "S3.2-01",
        design_tier="CUSTOM_FULL",
        material="OFHC Cu",
        temp_k=100.0,
        surface_finish_ra_um=0.8,
        world_origin_mm=(0.0, 0.0, -8.500),
        ports=(
            PortInterface(
                name="csa_16x_coax_in",
                kind="rf",
                position_mm=(86.0, 0.0, 0.0),
                normal=(-1.0, 0.0, 0.0),
                standard="16x Ultra-Low-C Micro-Coax Inputs (128 ch)",
                mating_part_id="S3.2-04",
                bore_mm=172.0,
            ),
            PortInterface(
                name="cold_island_100k_bus",
                kind="thermal",
                position_mm=(138.0, 0.0, -3.0),
                normal=(0.0, 0.0, -1.0),
                standard="4x Quadrant 100 K OFHC Cu Thermal Bus",
                mating_part_id="S6.2-01",
                od_mm=284.0,
                bore_mm=268.0,
            ),
        ),
        dimensions=(
            DimensionCallout("INNER_BORE", 172.0, 0.20, -0.20, view="top", prefix="Ø"),
            DimensionCallout("BUS_ARC_OD", 284.0, 0.20, -0.20, view="top", prefix="Ø"),
            DimensionCallout("MODULE_H", 10.8, 0.10, -0.10, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.050, datum_primary="", feature_note="100 K THERMAL BUS PLANE"),
            GDTFrame("position", 0.20, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="16x CSA QUADRANT ARRAY"),
        ),
        notes=(
            "All 16x 8-ch 100 K LTC6268 CSA modules instantiated around wafer perimeter (4x4 quadrants, R=86..118 mm).",
            "Fits cleanly inside 36 mm Exp125 magnet split gap (Z=-14.0..-3.2 mm) & UHV bore (R_max=142 < 180 mm).",
            f"300K->100K OFHC Cu cold-island bore vs AlN carrier WC rad clearance: {tc_ring_vs_aln.cold_worst_case_radial_clearance_mm:.3f} mm (PASS).",
            f"300K->100K OFHC Cu clamp vs Al2O3/Rogers substrate WC rad clearance: {tc_clamp_vs_pcb.cold_worst_case_radial_clearance_mm:.3f} mm (PASS).",
        ),
        scad_params=(
            ("n_csa_modules", 16),
            ("channels_total", 128),
            ("module_r_in_mm", 86.0),
            ("module_r_out_mm", 118.0),
            ("bus_r_out_mm", 142.0),
            ("operating_temp_k", 100.0),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=scad_feats,
        step_mesh=step_mesh,
        density_kg_m3=5200.0,  # Composite OFHC Cu clamps + Rogers RO4350B PCBs + Al EMI shields
        reconciliation=reconciliation,
        thermal_checks=(tc_ring_vs_aln.to_dict(), tc_clamp_vs_pcb.to_dict()),
    )


def _build_s3_2_02() -> BuiltPart:
    """S3.2-02: 16x Ex-vacuum CR-RC2 shaper/comparator/trim-DAC EMI cassettes in 2U 19" subrack (Bay 1 U20-U21)."""
    # Exact ibic_warm_shaper_300k PCB size = 185 x 135 mm (4L FR408HR), housed as 2 side-by-side bays x 8 horizontal
    # EMI shield cassettes inside a 2U (86.9 mm) 19" rack chassis facing -Y (Bay 1 U20-U21)!
    u_start, u_count = 20, 2
    depth_mm = 380.0
    internal_cards: list[SolidMesh] = []
    front_conns: list[tuple[float, float, float, float]] = []
    zs = np.linspace(-31.5, 31.5, 8)  # 9.0 mm vertical pitch (5.0 mm cassette + 4.0 mm airflow clearance)
    for b_idx, bx in enumerate((-95.0, +95.0)):
        for c_idx, cz in enumerate(zs):
            internal_cards.append(
                make_box(
                    135.0, 185.0, 5.0,
                    center=(bx, -65.0, float(cz)),
                    name=f"S3.2-02_shaper_cassette_{b_idx * 8 + c_idx + 1}",
                    material="FR4",
                )
            )
    # 16 front SMA monitor taps (2 rows x 8 across front bezel)
    for fx in np.linspace(-175.0, 175.0, 8):
        front_conns.append((float(fx), 18.0, 3.8, 10.0))
        front_conns.append((float(fx), -18.0, 3.8, 10.0))

    # Rear coax/power backplane PCB
    internal_cards.append(
        make_box(400.0, 4.0, 72.0, center=(0.0, 95.0, 0.0), name="S3.2-02_backplane", material="FR4")
    )

    mesh, step_mesh, scad_feats = _make_rack_chassis_shell(
        u_count=u_count,
        depth_mm=depth_mm,
        front_connectors=front_conns,
        internal_solids=internal_cards,
        name="S3.2-02_16x_shaper_cage",
        material="Al 6061",
    )
    design = make_part_design_from_bom(
        "S3.2-02",
        design_tier="CUSTOM_FULL",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=(RACK_BAY1_X_MM, rack_center_y(depth_mm), rack_u_center_z(u_start, u_count)),
        ports=(
            PortInterface(
                name="rack_front_2u",
                kind="mechanical",
                position_mm=(0.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="EIA-310 19-inch 2U (Bay 1 U20-U21, X=1480 mm)",
                mating_part_id="S7.4-03",
            ),
            PortInterface(
                name="coax_from_cf63",
                kind="rf",
                position_mm=(0.0, 0.5 * depth_mm, 0.0),
                normal=(0.0, 1.0, 0.0),
                standard="128-ch 50 Ohm SMA/SMB Rear Backplane",
                mating_part_id="S3.2-05",
            ),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", RACK_WIDTH_MM, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_2U", rack_u_height_mm(u_count), 0.3, -0.3, view="front"),
            DimensionCallout("DEPTH", depth_mm, 0.5, -0.5, view="top"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-INCH FRONT FLANGE"),
            GDTFrame("flatness", 0.20, datum_primary="", feature_note="CARD GUIDE RAIL PLANE"),
        ),
        notes=(
            "Houses all 16x 185x135 mm ibic_warm_shaper_300k boards (2x8 horizontal EMI cassettes, 1.2 us CR-RC2, TLV3501, DAC8568).",
            "Rack Bay 1 (X=+1480 mm, 482.6 mm along X, front -Y), U20-U21 (2U, Master #309 table).",
        ),
        scad_params=(
            ("n_shaper_cards", 16),
            ("card_length_mm", 185.0),
            ("card_width_mm", 135.0),
            ("rack_u_height", 2),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=2300.0,  # Composite Al-6061 EMI subrack + 16x FR408HR cards
    )


def _build_s3_2_03() -> BuiltPart:
    """S3.2-03: 4x Detector reverse-bias HV filter & guard-ring distribution box (1U, Bay 1 U22)."""
    u_start, u_count = 22, 1
    depth_mm = 300.0
    # 4 distinct 75x110 mm ibic_hv_bias_guard boards side-by-side with REAL 2.5x54 mm milled HV creepage air-slots!
    mod_xs = (-144.0, -48.0, 48.0, 144.0)
    internals: list[SolidMesh] = []
    front_conns: list[tuple[float, float, float, float]] = []
    rear_conns: list[tuple[float, float, float, float]] = []
    for idx, mx in enumerate(mod_xs):
        # Milled Rogers RO4350B board (75 along X, 110 along Y) with true 2.5x54 mm HV air-slot cutout
        hv_pcb = make_rect_plate_with_features(
            dx=75.0, dy=110.0, thickness=1.6,
            rect_slots=[(0.0, 15.0, 54.0, 2.5, 0.0)],
            center=(mx, 0.0, -4.0),
            name=f"S3.2-03_hv_pcb_{idx + 1}",
            material="Rogers",
        )
        # PTFE isolation tray beneath HV board (Z in [-12.0, -8.0])
        ptfe_tray = make_box(82.0, 116.0, 4.0, center=(mx, 0.0, -10.0), name=f"S3.2-03_ptfe_{idx + 1}", material="PTFE")
        internals.extend([hv_pcb, ptfe_tray])
        if idx < 3:
            internals.append(
                make_box(2.0, 220.0, 32.0, center=(mx + 48.0, 0.0, 0.0), name=f"S3.2-03_divider_{idx + 1}", material="Al 6061")
            )
        # Front SHV + Guard Triax barrels
        front_conns.append((mx - 14.0, 0.0, 6.0, 14.0))
        front_conns.append((mx + 14.0, 0.0, 5.0, 12.0))
        rear_conns.append((mx, 0.0, 6.0, 14.0))

    mesh, step_mesh, scad_feats = _make_rack_chassis_shell(
        u_count=u_count,
        depth_mm=depth_mm,
        front_connectors=front_conns,
        rear_connectors=rear_conns,
        internal_solids=internals,
        name="S3.2-03_hv_bias_guard_box",
        material="Al 6061",
    )
    design = make_part_design_from_bom(
        "S3.2-03",
        design_tier="CUSTOM_FULL",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=(RACK_BAY1_X_MM, rack_center_y(depth_mm), rack_u_center_z(u_start, u_count)),
        ports=(
            PortInterface(
                name="rack_front_1u",
                kind="mechanical",
                position_mm=(0.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="EIA-310 19-inch 1U (Bay 1 U22, X=1480 mm)",
                mating_part_id="S7.4-03",
            ),
            PortInterface(
                name="shv_guard_out",
                kind="electrical",
                position_mm=(0.0, 0.5 * depth_mm, 0.0),
                normal=(0.0, 1.0, 0.0),
                standard="4x SHV 0-100 V + Driven Guard Triax (<10 uVrms)",
                mating_part_id="S3.2-05",
            ),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", RACK_WIDTH_MM, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_1U", rack_u_height_mm(u_count), 0.3, -0.3, view="front"),
            DimensionCallout("DEPTH", depth_mm, 0.5, -0.5, view="top"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-INCH FRONT FLANGE"),
            GDTFrame("flatness", 0.15, datum_primary="", feature_note="PTFE HV ISOLATION FLOOR"),
        ),
        notes=(
            "4x isolated 110x75 mm ibic_hv_bias_guard boards with real 2.5x54 mm HV creepage air-slots on PTFE trays.",
            "3-stage RC filter (0-100 V, <10 uVrms noise, -227.9 dB @ 100 kHz). Rack Bay 1 (X=+1480 mm) U22 (1U).",
        ),
        scad_params=(
            ("n_hv_modules", 4),
            ("hv_pcb_x_mm", 75.0),
            ("hv_pcb_y_mm", 110.0),
            ("hv_air_slot_mm", 54.0),
            ("rack_u_height", 1),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=2400.0,
    )


def _build_s3_2_04() -> BuiltPart:
    """S3.2-04: All 16x <5 cm (44.8 mm) in-vacuum micro-coax IBIC signal looms (C_par < 0.15 pF)."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    path_lengths: list[float] = []

    # 6-point 3D spine per loom: R=42.2 -> 61.5 at Z=+1.35 (clears S3.1-03 carrier top -0.15 & S2.4 bottom +3.01),
    # then sweeps cleanly down outside carrier corner (R_corner=56.57) to CSA input at R=84.8, Z=-8.5 mm.
    rz_spine = [
        (42.2, 1.35),
        (50.0, 1.35),
        (61.5, 1.35),
        (68.0, -1.20),
        (76.0, -6.00),
        (84.8, -8.50),
    ]
    seg_len = sum(
        math.hypot(rz_spine[i + 1][0] - rz_spine[i][0], rz_spine[i + 1][1] - rz_spine[i][1])
        for i in range(len(rz_spine) - 1)
    )

    for idx, ang in enumerate(CSA_AZIMUTHS_DEG):
        rad = math.radians(ang)
        ca, sa = math.cos(rad), math.sin(rad)
        pts3d = [[r * ca, r * sa, z] for r, z in rz_spine]
        loom = make_swept_tube(
            pts3d, r_out=0.85, r_in=0.0, segments=10,
            name=f"S3.2-04_microcoax_{idx + 1}", material="PTFE",
        )
        # Compact 6-segment swept tube for STEP (<800 faces across all 16?) -> use 3-segment swept rod (16 x 36 = 576 faces!)
        pts_coarse = [pts3d[0], pts3d[2], pts3d[-1]]
        step_loom = make_swept_tube(
            pts_coarse, r_out=0.85, r_in=0.0, segments=6,
            name=f"S3.2-04_step_{idx + 1}", material="PTFE",
        )
        shells.append(loom)
        step_shells.append(step_loom)
        path_lengths.append(seg_len)

    mesh = merge_solids(shells, name="S3.2-04_16x_microcoax_looms", material="PTFE")
    step_mesh = merge_solids(step_shells, name="S3.2-04_step", material="PTFE")

    scad_feats = tuple(
        [
            ScadFeature(
                "add_cylinder",
                {"d": 1.7, "h": round(seg_len, 2)},
                translate=(63.5 * math.cos(math.radians(a)), 63.5 * math.sin(math.radians(a)), -3.5),
                rotate=(0.0, 77.0, a),
                comment=f"Micro-coax IBIC loom #{i + 1} (L={seg_len:.2f} mm < 50 mm, C_par<0.15 pF)",
            )
            for i, a in enumerate(CSA_AZIMUTHS_DEG)
        ]
    )
    design = make_part_design_from_bom(
        "S3.2-04",
        design_tier="CUSTOM_FULL",
        material="PTFE",
        temp_k=100.0,
        surface_finish_ra_um=1.6,
        world_origin_mm=(0.0, 0.0, 0.0),
        ports=(
            PortInterface(
                name="wafer_ring_launch",
                kind="rf",
                position_mm=(42.2, 0.0, 1.35),
                normal=(-1.0, 0.0, 0.0),
                standard="16x 8-ch PTFE/Ag-Cu Micro-Coax",
                mating_part_id="S3.1-04",
                bore_mm=84.4,
            ),
            PortInterface(
                name="csa_100k_input",
                kind="rf",
                position_mm=(84.8, 0.0, -8.50),
                normal=(1.0, 0.0, 0.0),
                standard="16x Cold-Island CSA Input Boots",
                mating_part_id="S3.2-01",
                od_mm=169.6,
            ),
        ),
        dimensions=(
            DimensionCallout("LOOM_ARC_LEN", round(seg_len, 2), 1.5, -1.5, view="front"),
            DimensionCallout("BUNDLE_OD", 1.70, 0.15, -0.15, view="right", prefix="Ø"),
            DimensionCallout("INNER_LAUNCH_DIA", 84.4, 0.5, -0.5, view="top", prefix="Ø"),
            DimensionCallout("OUTER_TERM_DIA", 169.6, 0.5, -0.5, view="top", prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("profile_surface", 0.50, datum_primary="A", feature_note="SWEPT PATH CLEARANCE > 0.5 mm"),
        ),
        notes=(
            f"All 16x micro-coax looms routed with exact arc length {seg_len:.2f} mm (< 50.0 mm / < 5 cm BOM spec).",
            "Preserves total stray capacitance C_par < 0.15 pF (C_tot <= 0.5 pF) per Exp127.",
            "Clears S3.1-03 carrier top (-0.15 mm) by 0.65 mm and S2.4-02 bottom (+3.01 mm) by 0.81 mm.",
        ),
        scad_params=(
            ("n_looms", 16),
            ("arc_length_mm", round(seg_len, 2)),
            ("bundle_od_mm", 1.7),
            ("max_stray_pf", 0.15),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=scad_feats,
        step_mesh=step_mesh,
        density_kg_m3=3600.0,  # Composite PTFE dielectric + silver-plated Cu conductors/braid
    )


def _build_s3_2_05() -> BuiltPart:
    """S3.2-05: All 4x ISO 3669 CF63 32-coax hermetic UHV analog feedthrough flanges (128 ch)."""
    # World origin = (0, 0, -85.0) -> 4 radial CF63 ports at 45, 135, 225, 315 deg,
    # knife-edge sealing face at R = 225.0 mm facing inward (-r), flange body R = [225.0, 242.5].
    cf = CF_SPECS["CF63"]
    r_mid = CF63_FLANGE_FACE_R_MM + 0.5 * cf.thickness_mm  # 233.75 mm
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    ports: list[PortInterface] = []

    # 32 coax pin local (u, v) offsets inside Ø58 mm clear feedthrough disk (4 + 12 + 16 = 32 pins)
    pin_uvs: list[tuple[float, float]] = []
    for ring_r, count in ((6.5, 4), (14.5, 12), (23.0, 16)):
        for k in range(count):
            a = 2.0 * math.pi * k / count
            pin_uvs.append((ring_r * math.cos(a), ring_r * math.sin(a)))

    for p_idx, ang in enumerate(CF63_PORT_AZIMUTHS_DEG, start=1):
        rad = math.radians(ang)
        ca, sa = math.cos(rad), math.sin(rad)
        # Flange sealing face (+Z in local CF) points INWARD (-ca, -sa, 0) to mate chamber nozzle!
        flange = make_cf_flange(
            "CF63",
            blank=True,
            with_knife_edge=True,
            sub_per_side=2,
            axis=(-ca, -sa, 0.0),
            center=(r_mid * ca, r_mid * sa, 0.0),
            name=f"S3.2-05_cf63_flange_{p_idx}",
            material="316LN",
        )
        shells.append(flange)

        # Compact STEP shell for each CF63 flange + rear connector boss (4 x ~120 = ~480 faces)
        step_shells.append(
            make_cylinder(
                radius=0.5 * cf.od_mm, height=cf.thickness_mm, segments=20,
                axis=(-ca, -sa, 0.0), center=(r_mid * ca, r_mid * sa, 0.0),
                name=f"S3.2-05_step_flange_{p_idx}", material="316LN",
            )
        )
        step_shells.append(
            make_cylinder(
                radius=28.0, height=16.0, segments=16,
                axis=(ca, sa, 0.0), center=((r_mid + 0.5 * cf.thickness_mm + 8.1) * ca, (r_mid + 0.5 * cf.thickness_mm + 8.1) * sa, 0.0),
                name=f"S3.2-05_step_pins_{p_idx}", material="Al2O3",
            )
        )

        # Build 32 atmospheric SMA/SMB barrels + 32 vacuum Al2O3/Cu pins along local +r/-r
        # Local tangent vector t = (-sa, ca, 0), vertical vector e_z = (0, 0, 1)
        r_atm = r_mid + 0.5 * cf.thickness_mm + 7.2
        r_vac = CF63_FLANGE_FACE_R_MM - 8.2
        for k, (pu, pv) in enumerate(pin_uvs):
            px_a = r_atm * ca + pu * (-sa)
            py_a = r_atm * sa + pu * ca
            shells.append(
                make_cylinder(
                    radius=1.8, height=14.0, segments=8,
                    axis=(ca, sa, 0.0), center=(px_a, py_a, pv),
                    name=f"S3.2-05_f{p_idx}_atm_pin_{k}", material="BeCu",
                )
            )
            px_v = r_vac * ca + pu * (-sa)
            py_v = r_vac * sa + pu * ca
            shells.append(
                make_cylinder(
                    radius=1.4, height=14.0, segments=8,
                    axis=(-ca, -sa, 0.0), center=(px_v, py_v, pv),
                    name=f"S3.2-05_f{p_idx}_vac_pin_{k}", material="Al2O3",
                )
            )

        ports.append(
            make_cf_port_interface(
                "CF63",
                name=f"cf63_feedthrough_{p_idx}",
                position_mm=(CF63_FLANGE_FACE_R_MM * ca, CF63_FLANGE_FACE_R_MM * sa, 0.0),
                normal=(-ca, -sa, 0.0),
                mating_part_id="S5.1-01",
                notes=f"32-coax hermetic CF63 analog feedthrough #{p_idx} ({ang:.0f} deg, 150 C bakeable)",
            )
        )

    mesh = merge_solids(shells, name="S3.2-05_4x_cf63_32coax", material="316LN")
    step_mesh = merge_solids(step_shells, name="S3.2-05_step", material="316LN")

    scad_feats = tuple(
        [
            ScadFeature(
                "add_cf_flange",
                {"size": "CF63", "blank": True},
                translate=(r_mid * math.cos(math.radians(a)), r_mid * math.sin(math.radians(a)), 0.0),
                rotate=(0.0, -90.0, a),
                comment=f"ISO 3669 CF63 32-coax hermetic feedthrough #{i + 1} ({a:.0f} deg)",
            )
            for i, a in enumerate(CF63_PORT_AZIMUTHS_DEG)
        ]
    )
    design = make_part_design_from_bom(
        "S3.2-05",
        design_tier="COTS_ENV_ICD",
        material="316LN",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, CF63_PORT_Z_MM),
        ports=tuple(ports),
        dimensions=(
            DimensionCallout("CF63_OD", cf.od_mm, 0.15, -0.15, view="front", prefix="Ø"),
            DimensionCallout("CF63_PCD", cf.pcd_mm, 0.10, -0.10, view="front", prefix="Ø"),
            DimensionCallout("FLANGE_THK", cf.thickness_mm, 0.15, -0.15, view="top"),
            DimensionCallout("PORT_RADIUS", CF63_FLANGE_FACE_R_MM, 0.25, -0.25, view="top", prefix="R"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.020, datum_primary="", feature_note="CF63 KNIFE-EDGE FACE"),
            GDTFrame("position", 0.15, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="8x Ø8.4 BOLT CIRCLE @ PCD 92.1"),
        ),
        notes=(
            "4x ISO 3669 CF63 hermetic 32-coax feedthrough flanges (128 analog channels total, He leak <=1e-9 mbar*L/s).",
            "Positioned at 45/115/162/315 deg, R_face=245.5 mm (0.5 mm gasket gap to S5.1-01), Z=-105 mm (Z_canon=395 mm).",
        ),
        scad_params=(
            ("n_flanges", 4),
            ("coax_per_flange", 32),
            ("cf63_od_mm", cf.od_mm),
            ("cf63_pcd_mm", cf.pcd_mm),
            ("cf63_bolts", cf.bolt_count),
            ("cf63_bolt_d_mm", cf.bolt_hole_mm),
        ),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats, step_mesh=step_mesh)


def _build_s3_2_06() -> BuiltPart:
    """S3.2-06: 2x EMI-shielded ultra-low-noise linear PSU rack chassis (dual-bay 2U in Bay 1 U18-U19)."""
    u_start, u_count = 18, 2
    depth_mm = 420.0
    # Dual side-by-side linear PSU bays separated by central CNC EMI partition inside 2U chassis (Bay 1 U18-U19)
    internals = [
        make_box(4.0, 370.0, 74.0, center=(0.0, 0.0, 0.0), name="S3.2-06_emi_center_wall", material="Al 6061"),
        make_tube(20.0, 54.0, 54.0, segments=24, center=(-105.0, -55.0, 0.0), name="psu1_toroid", material="OFHC Cu"),
        make_tube(20.0, 54.0, 54.0, segments=24, center=(+105.0, -55.0, 0.0), name="psu2_toroid", material="OFHC Cu"),
        make_box(170.0, 120.0, 4.0, center=(-105.0, +95.0, -24.0), name="psu1_reg_pcb", material="FR4"),
        make_box(170.0, 120.0, 4.0, center=(+105.0, +95.0, -24.0), name="psu2_reg_pcb", material="FR4"),
    ]
    fconns = [(-130.0, 0.0, 8.0, 12.0), (-80.0, 0.0, 8.0, 12.0), (80.0, 0.0, 8.0, 12.0), (130.0, 0.0, 8.0, 12.0)]
    rconns = [(-140.0, 0.0, 10.0, 16.0), (140.0, 0.0, 10.0, 16.0)]

    mesh, step_mesh, scad_feats = _make_rack_chassis_shell(
        u_count=u_count,
        depth_mm=depth_mm,
        rear_heatsink_fins=11,
        front_connectors=fconns,
        rear_connectors=rconns,
        internal_solids=internals,
        name="S3.2-06_2x_linear_psu",
        material="Al 6061",
    )

    design = make_part_design_from_bom(
        "S3.2-06",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=(RACK_BAY1_X_MM, rack_center_y(depth_mm), rack_u_center_z(u_start, u_count)),
        ports=(
            PortInterface(
                name="rack_front_2u",
                kind="mechanical",
                position_mm=(0.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="EIA-310 19-inch 2U Dual-Bay (Bay 1 U18-U19, X=1480 mm)",
                mating_part_id="S7.4-03",
            ),
            PortInterface(
                name="linear_dc_out",
                kind="electrical",
                position_mm=(0.0, 0.5 * depth_mm, 0.0),
                normal=(0.0, 1.0, 0.0),
                standard="+/-5 V, +/-12 V Linear (<100 uVrms)",
                mating_part_id="S3.2-02",
            ),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", RACK_WIDTH_MM, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_2U", rack_u_height_mm(u_count), 0.3, -0.3, view="front"),
            DimensionCallout("DEPTH", depth_mm, 0.5, -0.5, view="top"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.30, datum_primary="A", feature_note="19-INCH FRONT FLANGE"),
        ),
        notes=(
            "2x non-switching ultra-low-noise linear PSU rails (+/-5 V, +/-12 V, <100 uVrms) in EMI-partitioned 2U rack chassis.",
            "Dual toroidal transformers + rear extruded heatsinks. Rack Bay 1 (X=+1480 mm, front -Y) U18-U19 (2U).",
        ),
        scad_params=(
            ("n_psu_bays", 2),
            ("rack_u_height", 2),
            ("depth_mm", depth_mm),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=3800.0,  # Effective Al chassis + Cu toroidal transformers
    )


def _build_s3_3_01() -> BuiltPart:
    """S3.3-01: 2x Redundant FPGA counting-gate processing cards in 1U carrier bay (Bay 1 U24)."""
    u_start, u_count = 24, 1
    depth_mm = 380.0
    internals: list[SolidMesh] = []
    # 2 redundant Kintex/Artix FPGA boards (side-by-side bays) with low-profile finned heatsinks
    for idx, cx in enumerate((-102.0, +102.0), start=1):
        internals.append(
            make_box(185.0, 240.0, 2.4, center=(cx, 0.0, -11.0), name=f"fpga_pcb_{idx}", material="FR4")
        )
        internals.append(
            make_box(65.0, 65.0, 14.0, center=(cx, -15.0, 0.0), name=f"fpga_heatsink_{idx}", material="Al 6061")
        )
        internals.append(
            make_box(69.0, 76.0, 8.0, center=(cx, -100.0, -3.0), name=f"fpga_fmc_site_{idx}", material="Al 6061")
        )
    fconns = [(-150.0, 0.0, 5.0, 10.0), (-110.0, 0.0, 5.0, 10.0), (110.0, 0.0, 5.0, 10.0), (150.0, 0.0, 5.0, 10.0)]
    rconns = [(-120.0, 0.0, 8.0, 12.0), (120.0, 0.0, 8.0, 12.0)]

    mesh, step_mesh, scad_feats = _make_rack_chassis_shell(
        u_count=u_count,
        depth_mm=depth_mm,
        front_connectors=fconns,
        rear_connectors=rconns,
        internal_solids=internals,
        name="S3.3-01_2x_fpga_gate_bay",
        material="Al 6061",
    )
    design = make_part_design_from_bom(
        "S3.3-01",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=(RACK_BAY1_X_MM, rack_center_y(depth_mm), rack_u_center_z(u_start, u_count)),
        ports=(
            PortInterface(
                name="rack_front_1u",
                kind="mechanical",
                position_mm=(0.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="EIA-310 19-inch 1U (Bay 1 U24, X=1480 mm)",
                mating_part_id="S7.4-03",
            ),
            PortInterface(
                name="blanker_gate_link",
                kind="optical",
                position_mm=(0.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="100 MHz blanker_gate RTL (<100 ns latency)",
                mating_part_id="S3.3-02",
            ),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", RACK_WIDTH_MM, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_1U", rack_u_height_mm(u_count), 0.3, -0.3, view="front"),
            DimensionCallout("DEPTH", depth_mm, 0.5, -0.5, view="top"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-INCH FRONT FLANGE"),
        ),
        notes=(
            "2x redundant Xilinx/AMD Kintex/Artix FPGA counting-gate cards running blanker_gate 100 MHz RTL.",
            "Latency <100 ns, 100k-cycle hardware watchdog (Exp73/88). Rack Bay 1 (X=+1480 mm, front -Y) U24 (1U).",
        ),
        scad_params=(
            ("n_fpga_cards", 2),
            ("rack_u_height", 1),
            ("depth_mm", depth_mm),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=2500.0,
    )


def _build_s3_3_02() -> BuiltPart:
    """S3.3-02: High-speed LVDS / optical galvanic-isolated blanker feedback transceiver (1U, Bay 1 U26)."""
    u_start, u_count = 26, 1
    depth_mm = 300.0
    # Split galvanic-isolation EMI partition separating analog IBIC side from digital blanker driver side
    internals = [
        make_box(175.0, 220.0, 2.0, center=(-105.0, 0.0, -8.0), name="S3.3-02_rx_pcb", material="FR4"),
        make_box(175.0, 220.0, 2.0, center=(+105.0, 0.0, -8.0), name="S3.3-02_tx_pcb", material="FR4"),
        make_box(4.0, 260.0, 32.0, center=(0.0, 0.0, 0.0), name="S3.3-02_galvanic_wall", material="Al 6061"),
    ]
    # 16 duplex fiber LC/MPO transceiver ports along front panel
    fconns = [(float(x), 0.0, 4.0, 11.0) for x in np.linspace(-180.0, 180.0, 16)]
    rconns = [(-120.0, 0.0, 6.0, 12.0), (120.0, 0.0, 6.0, 12.0)]

    mesh, step_mesh, scad_feats = _make_rack_chassis_shell(
        u_count=u_count,
        depth_mm=depth_mm,
        front_connectors=fconns,
        rear_connectors=rconns,
        internal_solids=internals,
        name="S3.3-02_fiber_iso_transceiver",
        material="Al 6061",
    )
    design = make_part_design_from_bom(
        "S3.3-02",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=(RACK_BAY1_X_MM, rack_center_y(depth_mm), rack_u_center_z(u_start, u_count)),
        ports=(
            PortInterface(
                name="rack_front_1u",
                kind="mechanical",
                position_mm=(0.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="EIA-310 19-inch 1U (Bay 1 U26, X=1480 mm)",
                mating_part_id="S7.4-03",
            ),
            PortInterface(
                name="optical_blanker_fb",
                kind="optical",
                position_mm=(0.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="16x MPO/LC Optical + LVDS (<20 ns, <1 ns jitter)",
                mating_part_id="S2.4-03",
            ),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", RACK_WIDTH_MM, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_1U", rack_u_height_mm(u_count), 0.3, -0.3, view="front"),
            DimensionCallout("DEPTH", depth_mm, 0.5, -0.5, view="top"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-INCH FRONT FLANGE"),
        ),
        notes=(
            "128+ parallel hit->blanker_open fiber/LVDS galvanic isolation enclosure (<20 ns latency, <1 ns jitter).",
            "Internal galvanic EMI partition isolates analog IBIC ground from digital blanker switching noise. Bay 1 U26.",
        ),
        scad_params=(
            ("n_optical_ports", 16),
            ("rack_u_height", 1),
            ("depth_mm", depth_mm),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=2400.0,
    )


def _build_s3_3_03() -> BuiltPart:
    """S3.3-03: Multi-channel 12-bit 50 MS/s FMC pulse-height ADC digitizer enclosure (1U, Bay 1 U25)."""
    u_start, u_count = 25, 1
    depth_mm = 320.0
    # VITA 57.1 FMC HPC mezzanine card (69 x 76.5 mm) + carrier board + RF ADC shield can
    internals = [
        make_box(360.0, 220.0, 2.0, center=(0.0, 0.0, -11.0), name="S3.3-03_fmc_carrier_pcb", material="FR4"),
        make_box(69.0, 76.5, 2.0, center=(0.0, -65.0, -3.0), name="S3.3-03_fmc_adc_mezzanine", material="FR4"),
        make_box(54.0, 54.0, 8.0, center=(0.0, -65.0, 5.0), name="S3.3-03_adc_rf_can", material="Al 6061"),
    ]
    fconns = [(float(x), 0.0, 3.8, 10.0) for x in np.linspace(-180.0, 180.0, 16)]
    rconns = [(0.0, 0.0, 6.0, 12.0)]

    mesh, step_mesh, scad_feats = _make_rack_chassis_shell(
        u_count=u_count,
        depth_mm=depth_mm,
        front_connectors=fconns,
        rear_connectors=rconns,
        internal_solids=internals,
        name="S3.3-03_fmc_adc_50msps",
        material="Al 6061",
    )
    design = make_part_design_from_bom(
        "S3.3-03",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=(RACK_BAY1_X_MM, rack_center_y(depth_mm), rack_u_center_z(u_start, u_count)),
        ports=(
            PortInterface(
                name="rack_front_1u",
                kind="mechanical",
                position_mm=(0.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="EIA-310 19-inch 1U + VITA 57.1 FMC HPC (Bay 1 U25, X=1480 mm)",
                mating_part_id="S7.4-03",
            ),
            PortInterface(
                name="pha_analog_inputs",
                kind="rf",
                position_mm=(0.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="16x SMA 50 MS/s 12-bit PHA ADC Tap",
                mating_part_id="S3.2-02",
            ),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", RACK_WIDTH_MM, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_1U", rack_u_height_mm(u_count), 0.3, -0.3, view="front"),
            DimensionCallout("FMC_W", 69.0, 0.2, -0.2, view="top"),
            DimensionCallout("FMC_L", 76.5, 0.2, -0.2, view="top"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-INCH FRONT FLANGE"),
        ),
        notes=(
            "VITA 57.1 FMC 50 MS/s 12-bit pulse-height ADC digitizer recording per-shot IBIC energy for JSONL certificate.",
            "Coupled to buffered S3.2-02 warm shaper PHA tap (26.5 MHz anti-alias). Rack Bay 1 (X=+1480 mm) U25 (1U).",
        ),
        scad_params=(
            ("fmc_width_mm", 69.0),
            ("fmc_length_mm", 76.5),
            ("sample_rate_msps", 50),
            ("adc_bits", 12),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=2400.0,
    )


def _build_s3_3_04() -> BuiltPart:
    """S3.3-04: 1U EMI-shielded IBIC counting chassis & 10 MHz/trigger/PCIe-GbE host interface (Bay 1 U23)."""
    u_start, u_count = 23, 1
    depth_mm = 380.0
    internals = [
        make_box(380.0, 280.0, 2.0, center=(0.0, 0.0, -11.0), name="S3.3-04_sync_mainboard", material="FR4"),
        make_box(111.0, 168.0, 12.0, center=(-100.0, 40.0, 1.0), name="S3.3-04_pcie_gbe_card", material="FR4"),
        make_box(90.0, 120.0, 20.0, center=(+110.0, 90.0, 4.0), name="S3.3-04_psu_brick", material="Al 6061"),
    ]
    fconns = [(-150.0, 0.0, 5.5, 12.0), (-125.0, 0.0, 5.5, 12.0), (-100.0, 0.0, 5.5, 12.0), (150.0, 0.0, 5.5, 12.0)]
    rconns = [(-140.0, 0.0, 6.0, 12.0), (-80.0, 0.0, 6.0, 12.0), (140.0, 0.0, 8.0, 14.0)]

    mesh, step_mesh, scad_feats = _make_rack_chassis_shell(
        u_count=u_count,
        depth_mm=depth_mm,
        front_connectors=fconns,
        rear_connectors=rconns,
        internal_solids=internals,
        name="S3.3-04_1u_counting_chassis",
        material="Al 6061",
    )
    design = make_part_design_from_bom(
        "S3.3-04",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=(RACK_BAY1_X_MM, rack_center_y(depth_mm), rack_u_center_z(u_start, u_count)),
        ports=(
            PortInterface(
                name="rack_front_1u",
                kind="mechanical",
                position_mm=(0.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="EIA-310 19-inch 1U (Bay 1 U23, X=1480 mm)",
                mating_part_id="S7.4-03",
            ),
            PortInterface(
                name="clock_10mhz_sync",
                kind="rf",
                position_mm=(-150.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="10 MHz Rb Reference + Trigger BNC/SMA",
                mating_part_id="S7.4-01",
            ),
            PortInterface(
                name="host_pcie_gbe",
                kind="electrical",
                position_mm=(-110.0, 0.5 * depth_mm, 0.0),
                normal=(0.0, 1.0, 0.0),
                standard="PCIe Gen3 / 10GbE Host Interface",
                mating_part_id="S7.1-01",
            ),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", RACK_WIDTH_MM, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_1U", rack_u_height_mm(u_count), 0.3, -0.3, view="front"),
            DimensionCallout("DEPTH", depth_mm, 0.5, -0.5, view="top"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-INCH FRONT FLANGE"),
        ),
        notes=(
            "1U EMI-shielded IBIC counting chassis locked to S7.4 10 MHz Rb clock & trigger distribution.",
            "Integrates PCIe/GbE host telemetry interface card envelope (168x111 mm). Rack Bay 1 (X=+1480 mm) U23 (1U).",
        ),
        scad_params=(
            ("rack_u_height", 1),
            ("depth_mm", depth_mm),
            ("sync_freq_mhz", 10),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=2400.0,
    )


# ---------------------------------------------------------------------------
# Public Subsystem API: build_s3_parts(), export_s3(), export_all()
# ---------------------------------------------------------------------------
_S3_BUILDERS = {
    "S3.1-01": _build_s3_1_01,
    "S3.1-02": _build_s3_1_02,
    "S3.1-03": _build_s3_1_03,
    "S3.1-04": _build_s3_1_04,
    "S3.2-01": _build_s3_2_01,
    "S3.2-02": _build_s3_2_02,
    "S3.2-03": _build_s3_2_03,
    "S3.2-04": _build_s3_2_04,
    "S3.2-05": _build_s3_2_05,
    "S3.2-06": _build_s3_2_06,
    "S3.3-01": _build_s3_3_01,
    "S3.3-02": _build_s3_3_02,
    "S3.3-03": _build_s3_3_03,
    "S3.3-04": _build_s3_3_04,
}


def build_s3_parts() -> dict[str, BuiltPart]:
    """Build all 14 / 14 physical BOM parts of Subsystem S3 (exact part_id keyed)."""
    expected = list_physical_part_ids("S3")
    if set(expected) != set(_S3_BUILDERS):
        raise RuntimeError(
            f"S3 builder mismatch vs BOM: missing={set(expected) - set(_S3_BUILDERS)}, "
            f"extra={set(_S3_BUILDERS) - set(expected)}"
        )
    return {pid: _S3_BUILDERS[pid]() for pid in expected}


def export_s3(out_dir: Path | str | None = None) -> dict[str, PartArtifactResult]:
    """Export all 14 S3 parts (.stl/.step/.dxf/.svg/.scad + per-part .json & S3_manifest.json)."""
    dest = Path(out_dir) if out_dir is not None else DEFAULT_S3_OUT_DIR
    dest.mkdir(parents=True, exist_ok=True)

    parts = build_s3_parts()
    results: dict[str, PartArtifactResult] = {}
    manifest_parts: dict[str, Any] = {}
    total_mass_kg = 0.0

    for pid, bp in parts.items():
        art = export_part_artifacts(
            bp.design,
            bp.mesh,
            dest,
            scad_features=bp.scad_features,
            step_mesh=bp.step_mesh,
            density_kg_m3=bp.density_kg_m3,
            flat=True,
        )
        results[pid] = art
        total_mass_kg += art.mass_kg

        w_min, w_max = bp.world_mesh().bbox()
        _vr = verify_watertight(bp.mesh)
        part_json = {
            "part_id": pid,
            "subsystem": "S3",
            "part_design": bp.design.to_dict(),
            "artifact": art.to_dict(),
            "world_bbox_min_mm": list(w_min),
            "world_bbox_max_mm": list(w_max),
            "reconciliation": bp.reconciliation,
            "thermal_contraction_checks": list(bp.thermal_checks),
            "tolerance_stack_checks": list(bp.tolerance_checks),
            "shell_mate_metadata": {
                "n_shells": _vr.n_shells,
                "fea_bonding_mode": "SINGLE_MONOLITHIC_SOLID" if _vr.n_shells == 1 else "TIED_SUBASSEMBLY_CONTACTS",
                "watertight": _vr.watertight,
            },
        }
        (dest / f"{pid}.json").write_text(
            json.dumps(part_json, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        manifest_parts[pid] = {
            "design_tier": art.design_tier,
            "mass_kg": round(art.mass_kg, 6),
            "watertight": art.watertight,
            "all_valid": art.all_valid,
            "triangle_count": art.triangle_count,
            "world_origin_mm": list(bp.design.world_origin_mm),
            "world_bbox_min_mm": [round(v, 4) for v in w_min],
            "world_bbox_max_mm": [round(v, 4) for v in w_max],
            "json_path": f"hardware/cad_parts/out/S3/{pid}.json",
        }

    summary = {
        "subsystem": "S3",
        "part_count": len(results),
        "custom_full_count": sum(1 for r in results.values() if r.design_tier == "CUSTOM_FULL"),
        "cots_env_icd_count": sum(1 for r in results.values() if r.design_tier == "COTS_ENV_ICD"),
        "all_watertight": all(r.watertight for r in results.values()),
        "all_valid": all(r.all_valid for r in results.values()),
        "total_mass_kg": round(total_mass_kg, 4),
        "coordinate_frame": {
            "z_wafer_top_mm": Z_WAFER_TOP_MM,
            "rack_bay1_x_mm": RACK_BAY1_X_MM,
            "rack_bay1_front_y_mm": RACK_BAY1_FRONT_Y_MM,
            "rack_u_range": "U18-U26",
        },
        "epistemic": {
            "design_maturity": DESIGN_MATURITY,
            "no_lab_measurement": NO_LAB_MEASUREMENT,
            "iec61508_certified": IEC61508_CERTIFIED,
            "semi_s2_certified": SEMI_S2_CERTIFIED,
        },
        "parts": manifest_parts,
    }
    (dest / "S3_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return results


def export_all(out_dir: Path | str | None = None) -> dict[str, PartArtifactResult]:
    """Export all S3 mechanical CAD artifacts (entry point for subsystem export)."""
    return export_s3(out_dir=out_dir)


if __name__ == "__main__":
    res = export_all()
    tot = sum(r.mass_kg for r in res.values())
    ok = sum(1 for r in res.values() if r.all_valid)
    print(f"S3 export complete: {ok}/{len(res)} valid, total mass = {tot:.3f} kg")
