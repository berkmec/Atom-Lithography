"""Subsystem S4 — Vibration Isolation, 6-DOF UHV Piezo Stage & Laser Metrology.

Designs, verifies, and exports all 17 / 17 physical BOM parts of Subsystem S4
(``S4.1-01`` through ``S4.5-03``) using the pure-Python CAD kernel in
``hardware.cad_parts.core``:

- **Floor-to-Chamber Vibration Isolation Stack (``Z ∈ [-660, -240] mm``, central ``R=210 mm`` DR clear bore):**
  - ``S4.1-03`` (COTS_ENV_ICD): Sand-filled welded steel sub-frame (920x720x157 mm, >=1000 kg, f1>80 Hz)
    with 640x480 mm central clear bay (>R=210 mm DR bore) & 4x M24 damped leveling feet.
  - ``S4.1-02`` (COTS_ENV_ICD): 4x pneumatic air-spring isolators (1.0-2.0 Hz) at (±350, ±250) with
    real convoluted bellows, 3x mechanical auto-leveling valves, and 4x perimeter tie-bars.
  - ``S4.1-01`` (COTS_ENV_ICD): DIN 876/00 precision black diabase granite base plate
    (**reconciled 900x700x120 mm** vs early BOM 600x450x150 mm) with central Ø420 mm (R=210 mm)
    DR clear bore & 44x real M6 threaded stainless insert holes on 100 mm optical grid.
  - ``S4.2-01`` (COTS_ENV_ICD): Active 6-DOF piezo vibration isolation table (820x620x60 mm, 0.5-100 Hz)
    with central Ø420 mm (R=210 mm) DR clear bore & 6x corner/side piezo actuator cartridges.
  - ``S4.2-02`` (COTS_ENV_ICD): 3x triaxial seismic geophone pods (4.5 Hz, <1 ng/sqrt(Hz)) + junction box.
- **In-Vacuum 6-DOF Piezo Stage & Optical Metrology (``Z ∈ [-214, +95] mm``):**
  - ``S4.3-01`` (CUSTOM_FULL):  Ti/Invar 6-DOF UHV monolithic double-compound serpentine EDM flexure
    piezo fine stage (90x90x24.5 mm, 200 um stroke, k_eff~2.17 MN/m, embedded 6-DOF PZT stacks & Ø36 mm bore).
  - ``S4.3-02`` (CUSTOM_FULL):  ±25 mm UHV stick-slip crossed-roller coarse XY stage (96x96x23 mm)
    + integrated coaxial Invar-36 tubular stage pedestal mated flush to S4.3-01 (0 mm Z-gap).
  - ``S4.3-03`` (COTS_ENV_ICD): 4x diagonal in-stage sub-nm capacitive position sensors + swept Kapton UHV coax.
  - ``S4.4-01`` (COTS_ENV_ICD): 3-axis stabilized 632.8 nm He-Ne laser unit (Renishaw XL-80/RLE) on table corner.
  - ``S4.4-02`` (COTS_ENV_ICD): 3x UHV differential plane-mirror interferometer periscope relay heads
    (X, Y, Z @ R=128 mm, routing from Z=-133 mm viewports into the Z=[-18, +18] mm split gap).
  - ``S4.4-03`` (CUSTOM_FULL):  3x Zerodur/ULE lambda/20 stage bar mirrors on Invar risers inside the
    split gap (X, Y, Z @ R=65 mm, Z=-9 mm, normal-incidence clear LOS to S4.4-02).
  - ``S4.4-04`` (COTS_ENV_ICD): 3x 632.8 nm AR-coated ISO 3669 CF40 viewports (6x Ø6.6 @ PCD 58.7)
    + external fiber launchers & 45-deg beam benders (0/90/270 deg, R_face=240.5 mm, Z=-133 mm).
  - ``S4.5-01`` (CUSTOM_FULL):  Invar-36 / Zerodur bolted metrology reference bridge (Ø208/Ø264 ring
    with 3 carved radial optical pass-through windows @ 0/90/270 deg + 4x bolted columns @ R=118 mm).
  - ``S4.5-02`` (CUSTOM_FULL):  Dark-field fiducial alignment microscope objective + CMOS camera on
    ISO 3669 CF40 viewport (50.0 deg split-gap optical port, R_face=240.5 mm, Z=+9.0 mm / Z_canon=509.0 mm).
- **19" Rack Bay 1 Controllers (``X = +1480 mm, 482.6 mm along X, front -Y @ Y=-410..-434 mm, U14..U17``):**
  - ``S4.2-03`` (COTS_ENV_ICD, U14,     1U): Active 6-DOF vibration damping DSP controller & amplifier.
  - ``S4.3-04`` (COTS_ENV_ICD, U15-U16, 2U): 6-ch piezo servo controller & HV driver (E-712 class).
  - ``S4.5-03`` (CUSTOM_FULL,  U17,     1U): Fast <5 us interferometer-to-deflector real-time DSP chassis.

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
    make_bellows,
    make_box,
    make_cf_port_interface,
    make_cf_viewport,
    make_chamfered_box,
    make_cylinder,
    make_part_design_from_bom,
    make_plate_with_holes,
    make_rect_plate_with_features,
    make_revolved_profile,
    make_ring_with_bolt_circle,
    make_swept_tube,
    make_tube,
    merge_solids,
    rect_2d,
    slot_2d,
    transform_mesh,
)

# ---------------------------------------------------------------------------
# Global Machine Coordinate Constants (Z = 0.0 mm = Wafer Active Top Plane)
# ---------------------------------------------------------------------------
Z_WAFER_TOP_MM: float = 0.0
Z_FLOOR_MM: float = -660.0
DR_CLEAR_BORE_R_MM: float = 210.0     # Ø420 mm central bore clearing lower DR OVC / cryo access
RACK_BAY1_X_MM: float = 1480.0        # Master Bay 1 center X (X in [1180, 1780], 482.6 mm along X)
RACK_BAY1_FRONT_Y_MM: float = -410.0  # Front bezel face Y (handles reach -434.1 >= -438.0 rail plane)
RACK_U1_BOTTOM_Z_MM: float = -410.0   # Canonical Z_U(1) = +90.0 mm after +500.0 wafer shift
RACK_U_PITCH_MM: float = 44.45
RACK_WIDTH_MM: float = 482.6

INTERF_Z_MM: float = -133.0           # Canonical Z = +367.0 mm
CF40_VIEWPORT_FACE_R_MM: float = 240.5  # Master #309 fix: +28.5 mm outward (0.5 mm gap to S5.1-01 R=240.0)
CF40_VIEWPORT_AZIMUTHS_DEG: tuple[float, ...] = (0.0, 90.0, 270.0)
FIDUCIAL_PORT_AZIMUTH_DEG: float = 50.0  # Clear NE sector (19..77 deg) optical window to S3.1-01 wafer
FIDUCIAL_PORT_Z_MM: float = 9.0       # Canonical Z = +509.0 mm (strictly inside Z=[482, 518] mm split gap!)
FIDUCIAL_PORT_FACE_R_MM: float = 240.5

DEFAULT_S4_OUT_DIR: Path = REPO_ROOT / "hardware" / "cad_parts" / "out" / "S4"


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


def _chamfered_rect_2d(dx: float, dy: float, c: float) -> list[tuple[float, float]]:
    hx, hy = 0.5 * dx, 0.5 * dy
    return [
        (-hx + c, -hy), (hx - c, -hy),
        (hx, -hy + c), (hx, hy - c),
        (hx - c, hy), (-hx + c, hy),
        (-hx, hy - c), (-hx, -hy + c),
    ]


def _make_rack_chassis_shell(
    u_count: int,
    depth_mm: float = 380.0,
    *,
    wall_mm: float = 2.5,
    front_thickness_mm: float = 4.0,
    rear_heatsink_fins: int = 0,
    front_connectors: list[tuple[float, float, float, float]] | None = None,
    rear_connectors: list[tuple[float, float, float, float]] | None = None,
    internal_solids: list[SolidMesh] | None = None,
    name: str = "rack_chassis",
    material: str = "Al 6061",
) -> tuple[SolidMesh, SolidMesh, list[ScadFeature]]:
    """Build a hollow 19" EIA-310 rack chassis facing ``-Y`` with width 482.6 mm along ``X``."""
    h = rack_u_height_mm(u_count)
    body_w = 438.0
    body_h = h - 1.5
    body_d = depth_mm - front_thickness_mm - 6.0
    y_front = -0.5 * depth_mm + 0.5 * front_thickness_mm
    y_body = y_front + 0.5 * front_thickness_mm + 0.1 + 0.5 * body_d
    y_rear = y_body + 0.5 * body_d + 0.1 + 0.5 * wall_mm

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
        dx=RACK_WIDTH_MM, dy=h, thickness=front_thickness_mm, rect_slots=slots,
        axis="-y", center=(0.0, y_front, 0.0), name=f"{name}_front", material=material,
    )
    body_sleeve = make_plate_with_holes(
        outer_poly_2d=rect_2d(body_w, body_h, ccw=True),
        holes_2d=[rect_2d(body_w - 2.0 * wall_mm, body_h - 2.0 * wall_mm, ccw=False)],
        thickness=body_d, axis="-y", center=(0.0, y_body, 0.0),
        name=f"{name}_sleeve", material=material,
    )
    rear_plate = make_box(
        body_w, wall_mm, body_h, center=(0.0, y_rear, 0.0), name=f"{name}_rear", material=material,
    )

    shells: list[SolidMesh] = [front_plate, body_sleeve, rear_plate]
    step_shells: list[SolidMesh] = [
        make_box(RACK_WIDTH_MM, front_thickness_mm, h, center=(0.0, y_front, 0.0), material=material),
        body_sleeve,
        rear_plate,
    ]

    handle_h = min(0.68 * h, 68.0)
    handle_y = y_front - 0.5 * front_thickness_mm - 0.1
    for sx in (-1.0, 1.0):
        hx = sx * 212.0
        for sz in (-0.5 * handle_h + 4.0, 0.5 * handle_h - 4.0):
            shells.append(make_box(8.0, 16.0, 8.0, center=(hx, handle_y - 8.0, sz), material=material))
        shells.append(make_box(8.0, 8.0, handle_h, center=(hx, handle_y - 20.1, 0.0), material=material))

    if rear_heatsink_fins > 0:
        fin_y = y_rear + 0.5 * wall_mm + 0.1 + 11.0
        rconn_xs = [(cx, cr) for cx, _, cr, _ in (rear_connectors or ())]
        for idx, fx in enumerate(np.linspace(-180.0, 180.0, rear_heatsink_fins)):
            if any(abs(float(fx) - cx) < (cr + 4.0) for cx, cr in rconn_xs):
                continue
            fin = make_box(3.0, 22.0, body_h - 8.0, center=(float(fx), fin_y, 0.0), material=material)
            shells.append(fin)
            if idx % 2 == 0:
                step_shells.append(fin)

    if front_connectors:
        cy_base = y_front - 0.5 * front_thickness_mm - 0.1
        for idx, (cx, cz, cr, clen) in enumerate(front_connectors):
            shells.append(
                make_cylinder(cr, clen, segments=12, axis="-y", center=(cx, cy_base - 0.5 * clen, cz), material="BeCu")
            )
    if rear_connectors:
        cy_base = y_rear + 0.5 * wall_mm + 0.1
        for idx, (cx, cz, cr, clen) in enumerate(rear_connectors):
            shells.append(
                make_cylinder(cr, clen, segments=12, axis="+y", center=(cx, cy_base + 0.5 * clen, cz), material="316LN")
            )
    if internal_solids:
        shells.extend(internal_solids)

    scad_feats = [
        ScadFeature("add_box", {"dx": RACK_WIDTH_MM, "dy": front_thickness_mm, "dz": h}, translate=(0.0, y_front, 0.0), comment=f"19-inch EIA-310 {u_count}U front bezel (facing -Y)"),
        ScadFeature("add_box", {"dx": body_w, "dy": body_d + wall_mm, "dz": body_h}, translate=(0.0, y_body + 0.5 * wall_mm, 0.0), comment="Hollow EMI rack body"),
        ScadFeature("cut_slot", {"length": 10.0, "width": 6.4, "h": front_thickness_mm + 4.0}, translate=(-232.5, y_front, slot_z), rotate=(90.0, 0.0, 0.0), comment="EIA-310 upper-left ear slot"),
        ScadFeature("cut_slot", {"length": 10.0, "width": 6.4, "h": front_thickness_mm + 4.0}, translate=(232.5, y_front, slot_z), rotate=(90.0, 0.0, 0.0), comment="EIA-310 upper-right ear slot"),
        ScadFeature("cut_slot", {"length": 10.0, "width": 6.4, "h": front_thickness_mm + 4.0}, translate=(-232.5, y_front, -slot_z), rotate=(90.0, 0.0, 0.0), comment="EIA-310 lower-left ear slot"),
        ScadFeature("cut_slot", {"length": 10.0, "width": 6.4, "h": front_thickness_mm + 4.0}, translate=(232.5, y_front, -slot_z), rotate=(90.0, 0.0, 0.0), comment="EIA-310 lower-right ear slot"),
    ]
    return merge_solids(shells, name=name, material=material), merge_solids(step_shells, name=f"{name}_step", material=material), scad_feats


# ---------------------------------------------------------------------------
# Individual Part Builders (17 / 17 Physical Parts of S4)
# ---------------------------------------------------------------------------
def _build_s4_1_01() -> BuiltPart:
    """S4.1-01: DIN 876/00 precision granite base plate (reconciled 900x700x120 mm, Ø420 bore, M6 grid)."""
    # Reconciled dimensions: 900 x 700 x 120 mm (vs early BOM 600x450x150 mm)
    # Central Ø420.0 mm (R=210.0 mm) through-bore for lower DR OVC / cryo access
    # Real 100 mm pitch M6 threaded insert hole grid (44 holes outside R >= 240 mm)
    outer = _chamfered_rect_2d(900.0, 700.0, 12.0)
    holes: list[list[tuple[float, float]]] = [circle_2d(DR_CLEAR_BORE_R_MM, segments=36, ccw=False)]
    m6_coords: list[tuple[float, float]] = []
    for gx in range(-400, 401, 100):
        for gy in range(-300, 301, 100):
            if math.hypot(gx, gy) >= 240.0:
                m6_coords.append((float(gx), float(gy)))
                holes.append(circle_2d(4.0, cx=float(gx), cy=float(gy), segments=8, ccw=False))

    mesh = make_plate_with_holes(
        outer_poly_2d=outer,
        holes_2d=holes,
        thickness=120.0,
        name="S4.1-01_granite_base_900x700x120",
        material="Granite",
    )
    # Compact STEP mesh preserving exact 900x700x120 chamfered slab + Ø420 central DR bore (~140 faces)
    step_mesh = make_plate_with_holes(
        outer_poly_2d=outer,
        holes_2d=[circle_2d(DR_CLEAR_BORE_R_MM, segments=24, ccw=False)],
        thickness=120.0,
        name="S4.1-01_step",
        material="Granite",
    )

    reconciliation = {
        "part_id": "S4.1-01",
        "conflict": "BOM_DETAILED.csv v7.0 specifies 600x450x150 mm (~120 kg) whereas canonical CAD params.py v6.0 specifies 900x700x120 mm (223 kg solid).",
        "bom_dims_mm": [600.0, 450.0, 150.0],
        "selected_cad_dims_mm": [900.0, 700.0, 120.0],
        "central_dr_bore_mm": 420.0,
        "m6_insert_hole_count": len(m6_coords),
        "decision": "SELECTED 900x700x120 mm DIN 876/00 granite base plate with Ø420 mm (R=210 mm) central DR clear bore and 44x M6 threaded stainless inserts (~174 kg).",
        "justification": "A 600x450 mm block cannot structurally support the Ø456 mm CF400 UHV bottom flange, the 820x620 mm S4.2-01 active 6-DOF isolation table, the metrology bridge footprint, and the S4.4-01 He-Ne laser shelf while preserving a clear R=210 mm bore. 900x700x120 mm spans all supports cleanly and clears the -X DR OVC (x_min=-450 mm > -475 mm).",
    }

    scad_feats = [
        ScadFeature("add_box", {"dx": 900.0, "dy": 700.0, "dz": 120.0}, comment="Reconciled 900x700x120 mm DIN 876/00 black diabase granite block"),
        ScadFeature("cut_hole", {"d": 420.0, "h": 124.0}, comment="Central Ø420 mm (R=210 mm) clear bore for lower DR OVC / cryo access"),
    ]
    for mx, my in m6_coords[:12]:
        scad_feats.append(
            ScadFeature("cut_hole", {"d": 8.0, "h": 124.0}, translate=(mx, my, 0.0), comment=f"M6 stainless insert grid ({mx:.0f}, {my:.0f})")
        )

    design = make_part_design_from_bom(
        "S4.1-01",
        design_tier="COTS_ENV_ICD",
        material="Granite",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, -361.0),
        ports=(
            PortInterface(
                name="top_active_table_deck",
                kind="mechanical",
                position_mm=(0.0, 0.0, 60.0),
                normal=(0.0, 0.0, 1.0),
                standard="DIN 876/00 Flatness ±2 um + 44x M6 Insert Grid (100 mm pitch)",
                mating_part_id="S4.2-01",
                bore_mm=420.0,
            ),
            PortInterface(
                name="dr_central_clear_bore",
                kind="mechanical",
                position_mm=(0.0, 0.0, 0.0),
                normal=(0.0, 0.0, -1.0),
                standard="Ø420.0 mm (R=210.0 mm) Clear Bore for Lower DR OVC",
                mating_part_id="S6.8-04",
                bore_mm=420.0,
            ),
            PortInterface(
                name="air_isolator_pads",
                kind="mechanical",
                position_mm=(0.0, 0.0, -60.0),
                normal=(0.0, 0.0, -1.0),
                standard="4x Air-Spring Seats @ (±350, ±250) mm",
                mating_part_id="S4.1-02",
            ),
        ),
        dimensions=(
            DimensionCallout("LEN_X", 900.0, 0.5, -0.5, view="top"),
            DimensionCallout("WID_Y", 700.0, 0.5, -0.5, view="top"),
            DimensionCallout("THK_Z", 120.0, 0.2, -0.2, view="front"),
            DimensionCallout("DR_CLEAR_BORE", 420.0, 0.5, -0.5, view="top", prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.002, datum_primary="", feature_note="DIN 876/00 TOP OPTICAL SURFACE"),
            GDTFrame("parallelism", 0.020, datum_primary="A", feature_note="BOTTOM ISOLATOR MOUNT FACE"),
            GDTFrame("position", 0.15, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="44x M6 THREADED INSERTS"),
        ),
        notes=(
            "RECONCILIATION: BOM listed 600x450x150 mm (~120 kg) vs CAD params.py 900x700x120 mm; selected structurally valid 900x700x120 mm.",
            f"Includes central Ø420 mm (R=210 mm) clear bore for lower DR OVC + {len(m6_coords)}x real M6 insert grid holes (100 mm pitch).",
            "Clears -X DR tower OVC (x_min=-450 mm > -475 mm) and supports 820x620 mm S4.2-01 active 6-DOF isolation table.",
        ),
        scad_params=(
            ("granite_x_mm", 900.0),
            ("granite_y_mm", 700.0),
            ("granite_z_mm", 120.0),
            ("dr_clear_bore_d_mm", 420.0),
            ("m6_insert_count", len(m6_coords)),
            ("m6_grid_pitch_mm", 100.0),
            ("bom_reconciled_from", "600x450x150"),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        reconciliation=reconciliation,
    )


def _build_s4_1_02() -> BuiltPart:
    """S4.1-02: 4x Pneumatic low-frequency air-spring isolators w/ bellows, leveling valves & tie-bars."""
    # World origin = (0, 0, -462.0) -> Z_world in [-502.0, -422.0] mm (height = 80.0 mm)
    corners = ((-350.0, -250.0), (350.0, -250.0), (350.0, 250.0), (-350.0, 250.0))
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    for idx, (ix, iy) in enumerate(corners, start=1):
        # Bottom mounting flange (Ø112 x 10 mm, z_loc [-40, -30])
        bot = make_cylinder(56.0, 10.0, segments=28, center=(ix, iy, -35.0), name=f"iso{idx}_bot", material="304 SS")
        # Convoluted air-spring elastomer/steel bellows (z_loc [-29.8, +24.2], h=54)
        bel = make_bellows(
            r_in=34.0, r_out=52.0, length=54.0, n_convolutions=5, wall_thickness=2.5,
            end_cuff_mm=3.5, segments=24, center=(ix, iy, -2.8), name=f"iso{idx}_bellows", material="304 SS",
        )
        # Top piston cap (Ø108 x 15.6 mm, z_loc [+24.4, +40.0])
        top = make_cylinder(54.0, 15.6, segments=28, center=(ix, iy, 32.2), name=f"iso{idx}_top", material="304 SS")
        shells.extend([bot, bel, top])

        # Compact STEP proxy per isolator (1 cylinder = 64 faces x 4 = 256 faces)
        step_shells.append(make_cylinder(54.0, 80.0, segments=16, center=(ix, iy, 0.0), material="304 SS"))
        scad_feats.append(
            ScadFeature("add_cylinder", {"d": 108.0, "h": 80.0}, translate=(ix, iy, 0.0), comment=f"Pneumatic air-spring isolator #{idx} (1.0-2.0 Hz)")
        )

    # 3x mechanical auto-leveling valves (3-point kinematic leveling on outer ±X sides of isolators 1, 2, 3)
    valve_locs = ((-418.0, -250.0), (+418.0, -250.0), (+418.0, +250.0))
    for v_idx, (vx, vy) in enumerate(valve_locs, start=1):
        vbody = make_chamfered_box(22.0, 32.0, 36.0, chamfer=2.0, center=(vx, vy, 0.0), name=f"level_valve_{v_idx}", material="Al 6061")
        shells.append(vbody)
        step_shells.append(make_box(22.0, 32.0, 36.0, center=(vx, vy, 0.0), material="Al 6061"))
        scad_feats.append(
            ScadFeature("add_box", {"dx": 22.0, "dy": 32.0, "dz": 36.0}, translate=(vx, vy, 0.0), comment=f"Auto-leveling pneumatic valve #{v_idx}")
        )

    # 4x horizontal perimeter tie-bars (Ø20 mm along Y=±250 and X=±350 at z_loc=-24 -> Z_world [-496,-476],
    # strictly above S4.1-03 top -503 mm & preserving R >= 240 mm > 210 mm DR bore!)
    tb_specs = [
        ("x", (0.0, -250.0, -24.0), 584.0),
        ("x", (0.0, +250.0, -24.0), 584.0),
        ("y", (-350.0, 0.0, -24.0), 384.0),
        ("y", (+350.0, 0.0, -24.0), 384.0),
    ]
    for t_idx, (ax, ctr, length) in enumerate(tb_specs, start=1):
        tb = make_cylinder(10.0, length, segments=12, axis=ax, center=ctr, name=f"tie_bar_{t_idx}", material="304 SS")
        shells.append(tb)
        step_shells.append(make_cylinder(10.0, length, segments=8, axis=ax, center=ctr, material="304 SS"))
        rot = (0.0, 90.0, 0.0) if ax == "x" else (90.0, 0.0, 0.0)
        scad_feats.append(
            ScadFeature("add_cylinder", {"d": 20.0, "h": length}, translate=ctr, rotate=rot, comment=f"Perimeter structural tie-bar #{t_idx}")
        )

    mesh = merge_solids(shells, name="S4.1-02_4x_air_isolators", material="304 SS")
    step_mesh = merge_solids(step_shells, name="S4.1-02_step", material="304 SS")

    design = make_part_design_from_bom(
        "S4.1-02",
        design_tier="COTS_ENV_ICD",
        material="304 SS",
        surface_finish_ra_um=1.6,
        world_origin_mm=(0.0, 0.0, -462.0),
        ports=(
            PortInterface(
                name="granite_support_plane",
                kind="mechanical",
                position_mm=(0.0, 0.0, 40.0),
                normal=(0.0, 0.0, 1.0),
                standard="4x Pneumatic Piston Pads @ (±350, ±250) mm",
                mating_part_id="S4.1-01",
            ),
            PortInterface(
                name="subframe_mount_plane",
                kind="mechanical",
                position_mm=(0.0, 0.0, -40.0),
                normal=(0.0, 0.0, -1.0),
                standard="4x Flanged Feet + Perimeter Tie-Bars (R_clear >= 240 mm)",
                mating_part_id="S4.1-03",
            ),
            PortInterface(
                name="cda_air_supply",
                kind="gas",
                position_mm=(-429.0, -250.0, 0.0),
                normal=(-1.0, 0.0, 0.0),
                standard="6 bar Clean Dry Air / N2 Auto-Leveling Manifold",
                mating_part_id="S7.4-04",
            ),
        ),
        dimensions=(
            DimensionCallout("SPAN_X", 700.0, 0.5, -0.5, view="top"),
            DimensionCallout("SPAN_Y", 500.0, 0.5, -0.5, view="top"),
            DimensionCallout("ISOLATOR_OD", 112.0, 0.5, -0.5, view="top", prefix="Ø"),
            DimensionCallout("HEIGHT", 80.0, 0.2, -0.2, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.10, datum_primary="", feature_note="COPLANAR 4-PISTON LEVELING PLANE"),
        ),
        notes=(
            "4x Newport/TMC-class 1.0-2.0 Hz pneumatic air-spring isolators with 3-point auto-leveling valves & perimeter tie-bars.",
            "Tie-bars run at |X|=350 / |Y|=250 mm, preserving >240 mm central clear radius for lower DR OVC (R=210 mm).",
        ),
        scad_params=(
            ("n_isolators", 4),
            ("span_x_mm", 700.0),
            ("span_y_mm", 500.0),
            ("isolator_h_mm", 80.0),
            ("corner_freq_hz", 1.5),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=3600.0,  # Composite 304 SS flanges/tie-bars + pressurized air-spring bellows cavity
    )


def _build_s4_1_03() -> BuiltPart:
    """S4.1-03: Sand-filled welded structural steel sub-frame (>=1000 kg, f1>80 Hz) & leveling feet."""
    # World origin = (0, 0, -581.5) -> Z_world in [-660.0, -503.0] mm (height = 157.0 mm)
    # Outer 920 x 720 mm (X in [-460, +460] clears -X DR OVC at -475 mm by 15 mm!)
    # Open central bay 640 x 480 mm (clears R=210 mm DR bore by 30 mm!)
    frame_box = make_plate_with_holes(
        outer_poly_2d=_chamfered_rect_2d(920.0, 720.0, 8.0),
        holes_2d=[rect_2d(640.0, 480.0, ccw=False)],
        thickness=116.0,
        center=(0.0, 0.0, 20.5),  # Z_world in [-619.0, -503.0]
        name="S4.1-03_welded_sand_frame",
        material="Steel",
    )
    shells: list[SolidMesh] = [frame_box]
    step_shells: list[SolidMesh] = [frame_box]
    scad_feats = [
        ScadFeature("add_box", {"dx": 920.0, "dy": 720.0, "dz": 116.0}, translate=(0.0, 0.0, 20.5), comment="Sand-filled welded 140x116 mm RHS structural steel sub-frame"),
        ScadFeature("cut_slot", {"length": 640.0, "width": 480.0, "h": 122.0}, translate=(0.0, 0.0, 20.5), comment="Open 640x480 mm central bay clearing R=210 mm DR OVC bore"),
    ]

    # 4x M24 vibration-damped leveling feet/soleplates resting on lab floor Z=-660.0 mm (z_loc in [-78.5, -37.7])
    foot_pts = ((-380.0, -280.0), (380.0, -280.0), (380.0, 280.0), (-380.0, 280.0))
    for f_idx, (fx, fy) in enumerate(foot_pts, start=1):
        # Stepped leveling foot: Ø92 soleplate + Ø30 M24 threaded jack spindle
        prof = [
            (0.0, -20.4), (46.0, -20.4), (46.0, -6.0),
            (15.0, -4.0), (15.0, +20.4), (0.0, +20.4),
        ]
        foot = make_revolved_profile(prof, segments=24, center=(fx, fy, -58.1), name=f"foot_{f_idx}", material="Steel")
        shells.append(foot)
        step_shells.append(make_cylinder(46.0, 40.8, segments=12, center=(fx, fy, -58.1), material="Steel"))
        scad_feats.append(
            ScadFeature("add_cylinder", {"d": 92.0, "h": 40.8}, translate=(fx, fy, -58.1), comment=f"M24 vibration-damped leveling soleplate #{f_idx}")
        )

    # 4x sand-fill / inspection port plugs along ±X side walls (keep X <= 466 < 475 mm DR OVC)
    for sx in (-1.0, 1.0):
        for sy in (-160.0, 160.0):
            shells.append(
                make_cylinder(14.0, 6.0, segments=12, axis="x", center=(sx * 463.1, sy, 20.5), name="sand_fill_plug", material="Steel")
            )

    mesh = merge_solids(shells, name="S4.1-03_sand_filled_subframe", material="Steel")
    step_mesh = merge_solids(step_shells, name="S4.1-03_step", material="Steel")

    design = make_part_design_from_bom(
        "S4.1-03",
        design_tier="COTS_ENV_ICD",
        material="Steel",
        surface_finish_ra_um=3.2,
        world_origin_mm=(0.0, 0.0, -581.5),
        ports=(
            PortInterface(
                name="isolator_top_deck",
                kind="mechanical",
                position_mm=(0.0, 0.0, 78.5),
                normal=(0.0, 0.0, 1.0),
                standard="4x Isolator Pads @ (±350, ±250) mm",
                mating_part_id="S4.1-02",
            ),
            PortInterface(
                name="lab_floor_anchor",
                kind="mechanical",
                position_mm=(0.0, 0.0, -78.5),
                normal=(0.0, 0.0, -1.0),
                standard="4x M24 Leveling Soleplates (Z_floor = -660.0 mm)",
                mating_part_id="S7.4-04",
            ),
        ),
        dimensions=(
            DimensionCallout("OUTER_X", 920.0, 0.5, -0.5, view="top"),
            DimensionCallout("OUTER_Y", 720.0, 0.5, -0.5, view="top"),
            DimensionCallout("CLEAR_BAY_X", 640.0, 1.0, -1.0, view="top"),
            DimensionCallout("CLEAR_BAY_Y", 480.0, 1.0, -1.0, view="top"),
            DimensionCallout("TOTAL_H", 157.0, 0.5, -0.5, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.50, datum_primary="", feature_note="TOP MACHINED PAD PLANE"),
            GDTFrame("parallelism", 0.50, datum_primary="A", feature_note="FLOOR SOLEPLATE PLANE"),
        ),
        notes=(
            "Welded 140x116 mm RHS structural steel sub-frame filled with dry silica sand (>=1000 kg capacity, f1 > 80 Hz).",
            "Open 640x480 mm central bay clears R=210 mm lower DR bore by >=30 mm; outer X=±460 mm clears -X DR OVC (-475 mm).",
        ),
        scad_params=(
            ("frame_x_mm", 920.0),
            ("frame_y_mm", 720.0),
            ("bay_x_mm", 640.0),
            ("bay_y_mm", 480.0),
            ("load_capacity_kg", 1000),
            ("min_f1_hz", 80.0),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=4800.0,  # Composite 8 mm steel RHS walls + dry compacted quartz sand fill
    )


def _build_s4_2_01() -> BuiltPart:
    """S4.2-01: Active 6-DOF piezo vibration isolation table (820x620x60 mm, Ø420 DR bore)."""
    # World origin = (0, 0, -270.0) -> Z_world in [-300.0, -240.0] mm
    outer = _chamfered_rect_2d(820.0, 620.0, 10.0)
    holes: list[list[tuple[float, float]]] = [circle_2d(DR_CLEAR_BORE_R_MM, segments=36, ccw=False)]
    # 16 perimeter M6 optical mounting inserts around top honeycomb deck
    for gx in (-360.0, -260.0, 260.0, 360.0):
        for gy in (-260.0, -100.0, 100.0, 260.0):
            if math.hypot(gx, gy) >= 245.0:
                holes.append(circle_2d(3.5, cx=gx, cy=gy, segments=8, ccw=False))

    top_deck = make_plate_with_holes(
        outer_poly_2d=outer, holes_2d=holes, thickness=42.0,
        center=(0.0, 0.0, 9.0),  # Z_world in [-282.0, -240.0]
        name="S4.2-01_active_honeycomb_deck", material="Al 6061",
    )
    step_deck = make_plate_with_holes(
        outer_poly_2d=outer, holes_2d=[circle_2d(DR_CLEAR_BORE_R_MM, segments=24, ccw=False)],
        thickness=42.0, center=(0.0, 0.0, 9.0), name="S4.2-01_step_deck", material="Al 6061",
    )

    # 6x active 6-DOF piezo actuator cartridges beneath deck (Z_world in [-300.0, -282.2], all R >= 340 mm)
    pod_pts = (
        (-330.0, -230.0), (330.0, -230.0),
        (330.0, 230.0), (-330.0, 230.0),
        (-340.0, 0.0), (340.0, 0.0),
    )
    shells: list[SolidMesh] = [top_deck]
    step_shells: list[SolidMesh] = [step_deck]
    scad_feats = [
        ScadFeature("add_box", {"dx": 820.0, "dy": 620.0, "dz": 42.0}, translate=(0.0, 0.0, 9.0), comment="Active 6-DOF Al-honeycomb top table (820x620x42 mm)"),
        ScadFeature("cut_hole", {"d": 420.0, "h": 46.0}, translate=(0.0, 0.0, 9.0), comment="Central Ø420 mm (R=210 mm) DR clear bore"),
    ]
    for p_idx, (px, py) in enumerate(pod_pts, start=1):
        pod = make_cylinder(36.0, 17.8, segments=20, center=(px, py, -21.1), name=f"piezo_pod_{p_idx}", material="316LN")
        shells.append(pod)
        step_shells.append(make_cylinder(36.0, 17.8, segments=12, center=(px, py, -21.1), material="316LN"))
        scad_feats.append(
            ScadFeature("add_cylinder", {"d": 72.0, "h": 17.8}, translate=(px, py, -21.1), comment=f"6-DOF active piezo actuator cartridge #{p_idx}")
        )

    mesh = merge_solids(shells, name="S4.2-01_active_6dof_table", material="Al 6061")
    step_mesh = merge_solids(step_shells, name="S4.2-01_step", material="Al 6061")

    design = make_part_design_from_bom(
        "S4.2-01",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=0.8,
        world_origin_mm=(0.0, 0.0, -270.0),
        ports=(
            PortInterface(
                name="uhv_chamber_cf400_seat",
                kind="mechanical",
                position_mm=(0.0, 0.0, 30.0),
                normal=(0.0, 0.0, 1.0),
                standard="CF400 Chamber Bottom Support Deck (Ø420 clear bore)",
                mating_part_id="S5.1-01",
                bore_mm=420.0,
                od_mm=456.0,
            ),
            PortInterface(
                name="granite_base_seat",
                kind="mechanical",
                position_mm=(0.0, 0.0, -30.0),
                normal=(0.0, 0.0, -1.0),
                standard="6x Active Piezo Isolator Feet on S4.1-01 Granite",
                mating_part_id="S4.1-01",
            ),
        ),
        dimensions=(
            DimensionCallout("TABLE_X", 820.0, 0.5, -0.5, view="top"),
            DimensionCallout("TABLE_Y", 620.0, 0.5, -0.5, view="top"),
            DimensionCallout("TOTAL_H", 60.0, 0.2, -0.2, view="front"),
            DimensionCallout("DR_BORE", 420.0, 0.5, -0.5, view="top", prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.050, datum_primary="", feature_note="ACTIVE ISOLATED TOP DECK"),
            GDTFrame("parallelism", 0.050, datum_primary="A", feature_note="6-POD ACTUATOR BASE PLANE"),
        ),
        notes=(
            "Herzan/Accurion-class 6-DOF active piezo isolation table (0.5-100 Hz, >30 dB @ 10 Hz, VC-E+ floor).",
            "Central Ø420 mm (R=210 mm) bore aligns with S4.1-01 granite & clears lower DR OVC while supporting CF400 UHV flange.",
        ),
        scad_params=(
            ("table_x_mm", 820.0),
            ("table_y_mm", 620.0),
            ("table_h_mm", 60.0),
            ("n_piezo_pods", 6),
            ("dr_bore_d_mm", 420.0),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=2200.0,  # Honeycomb steel/Al damped optical deck + piezo actuators
    )


def _build_s4_2_02() -> BuiltPart:
    """S4.2-02: 3-axis low-noise seismic geophone / accelerometer sensor package (3 pods + junction box)."""
    # World origin = (0, 0, -216.0); pods sit at Z_world in [-239.0, -193.0] (1 mm above S4.2-01 top -240)
    pod_coords = ((-340.0, -245.0), (340.0, -245.0), (-340.0, 245.0))
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    for idx, (px, py) in enumerate(pod_coords, start=1):
        # Stepped triaxial geophone cylinder: base flange Ø60x6 + body Ø50x34 + LEMO neck Ø14x6 (total h=46)
        prof = [
            (0.0, -23.0), (30.0, -23.0), (30.0, -17.0),
            (25.0, -17.0), (25.0, 17.0), (7.0, 17.0),
            (7.0, 23.0), (0.0, 23.0),
        ]
        pod = make_revolved_profile(prof, segments=28, center=(px, py, 0.0), name=f"geophone_pod_{idx}", material="Al 6061")
        shells.append(pod)
        step_shells.append(make_cylinder(28.0, 46.0, segments=16, center=(px, py, 0.0), material="Al 6061"))
        scad_feats.append(
            ScadFeature("add_cylinder", {"d": 56.0, "h": 46.0}, translate=(px, py, 0.0), comment=f"3-axis 4.5 Hz seismic geophone pod #{idx}")
        )

    # Shielded triaxial signal combiner / junction box on -X edge of active table (clear of DR bridge at Z=-7)
    jbox = make_chamfered_box(54.0, 84.0, 26.0, chamfer=2.0, center=(-345.0, 0.0, -9.5), name="geophone_jbox", material="Al 6061")
    shells.append(jbox)
    step_shells.append(make_box(54.0, 84.0, 26.0, center=(-345.0, 0.0, -9.5), material="Al 6061"))
    scad_feats.append(
        ScadFeature("add_box", {"dx": 54.0, "dy": 84.0, "dz": 26.0}, translate=(-345.0, 0.0, -9.5), comment="Low-noise triaxial geophone junction box")
    )

    mesh = merge_solids(shells, name="S4.2-02_seismic_geophone_pods", material="Al 6061")
    step_mesh = merge_solids(step_shells, name="S4.2-02_step", material="Al 6061")

    design = make_part_design_from_bom(
        "S4.2-02",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=(0.0, 0.0, -216.0),
        ports=(
            PortInterface(
                name="table_sensor_mount",
                kind="mechanical",
                position_mm=(-340.0, -245.0, -23.0),
                normal=(0.0, 0.0, -1.0),
                standard="3x Triaxial Geophone Kinematic Bases on S4.2-01",
                mating_part_id="S4.2-01",
                od_mm=60.0,
            ),
            PortInterface(
                name="lemo_dsp_link",
                kind="electrical",
                position_mm=(-345.0, 0.0, 3.5),
                normal=(0.0, 0.0, 1.0),
                standard="Shielded 9-ch Differential LEMO to S4.2-03 DSP",
                mating_part_id="S4.2-03",
            ),
        ),
        dimensions=(
            DimensionCallout("POD_FLANGE_OD", 60.0, 0.2, -0.2, view="top", prefix="Ø"),
            DimensionCallout("POD_HEIGHT", 46.0, 0.2, -0.2, view="front"),
            DimensionCallout("ARRAY_SPAN_X", 680.0, 0.5, -0.5, view="top"),
            DimensionCallout("ARRAY_SPAN_Y", 490.0, 0.5, -0.5, view="top"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.05, datum_primary="A", feature_note="ORTHOGONAL 3-AXIS GEOPHONE AXES"),
        ),
        notes=(
            "3x triaxial 4.5 Hz seismic geophone pods (<1 ng/sqrt(Hz) @ 10 Hz) spanning full 6-DOF active table modes.",
            "Mounted on 3 corners of S4.2-01 leaving (+330,+245) free for S4.4-01 stabilized He-Ne laser unit.",
        ),
        scad_params=(
            ("n_geophone_pods", 3),
            ("pod_od_mm", 60.0),
            ("pod_h_mm", 46.0),
            ("resonant_freq_hz", 4.5),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=3400.0,  # Al housing + internal moving-coil magnet/spring seismic mass
    )


def _build_s4_2_03() -> BuiltPart:
    """S4.2-03: Active 6-DOF vibration damping DSP controller & piezo amplifier (1U, Bay 1 U14)."""
    u_start, u_count = 14, 1
    depth_mm = 380.0
    internals = [
        make_box(360.0, 220.0, 2.4, center=(0.0, -60.0, -10.0), name="mimo_dsp_pcb", material="FR4"),
        make_box(340.0, 100.0, 22.0, center=(0.0, +110.0, 0.0), name="piezo_amp_bank", material="Al 6061"),
    ]
    fconns = [(-160.0, 0.0, 5.5, 11.0), (-130.0, 0.0, 5.5, 11.0), (-100.0, 0.0, 5.5, 11.0), (140.0, 0.0, 5.5, 11.0)]
    rconns = [(float(x), 0.0, 6.0, 14.0) for x in np.linspace(-140.0, 140.0, 6)]

    mesh, step_mesh, scad_feats = _make_rack_chassis_shell(
        u_count=u_count,
        depth_mm=depth_mm,
        rear_heatsink_fins=9,
        front_connectors=fconns,
        rear_connectors=rconns,
        internal_solids=internals,
        name="S4.2-03_active_iso_dsp_ctrl",
        material="Al 6061",
    )
    design = make_part_design_from_bom(
        "S4.2-03",
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
                standard="EIA-310 19-inch 1U (Bay 1 U14, X=1480 mm)",
                mating_part_id="S7.4-03",
            ),
            PortInterface(
                name="piezo_drive_6ch",
                kind="electrical",
                position_mm=(0.0, 0.5 * depth_mm, 0.0),
                normal=(0.0, 1.0, 0.0),
                standard="6-DOF MIMO 10 kHz Piezo Drive + Geophone Rx",
                mating_part_id="S4.2-01",
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
            "6-DOF MIMO active vibration damping DSP controller & HV piezo amplifier (10 kHz control loop).",
            "Rack Bay 1 (X=+1480 mm, 482.6 mm along X, front -Y), U14 (1U, Master #309 table).",
        ),
        scad_params=(("rack_u_height", 1), ("depth_mm", depth_mm), ("loop_khz", 10.0)),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=2600.0,
    )


def _poly_cw(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Ensure a 2D hole polygon has clockwise winding for ``make_plate_with_holes``."""
    area2 = sum(
        pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
        for i in range(len(pts))
    )
    return list(reversed(pts)) if area2 > 0.0 else list(pts)


def _make_arc_sector_solid(
    r_in: float,
    r_out: float,
    thickness: float,
    deg_start: float,
    deg_end: float,
    *,
    arc_steps: int = 16,
    center: tuple[float, float, float] = (0.0, 0.0, 0.0),
    name: str = "arc_sector",
    material: str = "Invar-36",
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


def _build_s4_3_01() -> BuiltPart:
    """S4.3-01: 6-DOF UHV monolithic double-compound serpentine EDM flexure stage (k_eff~2.17 MN/m)."""
    # World origin = (0, 0, -41.0) -> Z_world in [-53.0, -28.5] mm (flush contact with S4.3-02 & S6.2-01!)
    # Monolithic Ti-6Al-4V double-compound serpentine EDM flexure body (90x90x19.2 mm, z_loc [-12.0, +7.2]):
    # - Central Ø36.0 mm bore (r=18.0) + 4 M4 corner clamp holes @ (±39.5, ±39.5)
    # - 8 connected EDM serpentine wire-cut slots completely severing bulk diagonal corner load paths:
    #   * 4 outer vertical X-flexure leaf blades (t_x=1.96 mm, L_x=30.5 mm, h=19.2 mm -> k_x ~ 2.17 MN/m, vM < 130 MPa @ 200 um)
    #   * 4 inner horizontal Y-flexure leaf blades (t_y=1.29 mm, L_y=21.0 mm, h=19.2 mm -> k_y ~ 2.17 MN/m, vM < 170 MPa @ 200 um)
    # - ZERO 0.200 mm air gap: flex_body [-12.0, +7.2] mates flush with top_deck [+7.2, +12.0] + 4x Vespel seat bosses [+12.0, +12.5]!
    # - Embedded 6-DOF UHV PZT piezo actuator stacks seated inside machined EDM pockets & Z-actuator bores!
    outer_base = _chamfered_rect_2d(90.0, 90.0, 3.0)
    flex_holes: list[list[tuple[float, float]]] = [circle_2d(18.0, segments=28, ccw=False)]
    for mx, my in ((-39.5, -39.5), (39.5, -39.5), (39.5, 39.5), (-39.5, 39.5)):
        flex_holes.append(circle_2d(2.2, cx=mx, cy=my, segments=10, ccw=False))

    tx = 1.96  # Outer X-flexure EDM leaf blade thickness (mm) -> CalculiX C3D10 k_x ~ 2.17 MN/m
    ty = 1.29  # Inner Y-flexure EDM leaf blade thickness (mm) -> CalculiX C3D10 k_y ~ 2.17 MN/m
    xb_out = 34.0
    xb_in = xb_out - tx
    x_mid = 30.0
    y_bridge = 4.0
    y_top_in = 31.0
    y_top_out = 35.5
    # 2 outer vertical side relief slots + 2 outer top/bottom U-slots (4 outer serpentine cutouts)
    flex_holes.append(_poly_cw([(-35.5, -34.5), (-xb_out, -34.5), (-xb_out, 34.5), (-35.5, 34.5)]))
    flex_holes.append(_poly_cw([(xb_out, -34.5), (35.5, -34.5), (35.5, 34.5), (xb_out, 34.5)]))
    top_u = [
        (-xb_in, y_bridge), (-x_mid, y_bridge), (-x_mid, y_top_in),
        (x_mid, y_top_in), (x_mid, y_bridge), (xb_in, y_bridge),
        (xb_in, y_top_out), (-xb_in, y_top_out),
    ]
    flex_holes.append(_poly_cw(top_u))
    flex_holes.append(_poly_cw([(x, -y) for x, y in top_u]))

    # 2 inner horizontal relief slots + 2 inner left/right C-slots (4 inner serpentine cutouts)
    yb_out = 25.0
    yb_in = yb_out - ty
    y_plat = 21.0
    x_bridge = 4.0
    x_int_in = 22.0
    x_int_out = 27.0
    flex_holes.append(_poly_cw([(-25.5, yb_out), (25.5, yb_out), (25.5, 27.0), (-25.5, 27.0)]))
    flex_holes.append(_poly_cw([(-25.5, -27.0), (25.5, -27.0), (25.5, -yb_out), (-25.5, -yb_out)]))
    right_c = [
        (x_bridge, -yb_in), (x_int_out, -yb_in), (x_int_out, yb_in), (x_bridge, yb_in),
        (x_bridge, y_plat), (x_int_in, y_plat), (x_int_in, -y_plat), (x_bridge, -y_plat),
    ]
    flex_holes.append(_poly_cw(right_c))
    flex_holes.append(_poly_cw([(-x, y) for x, y in right_c]))

    flex_body = make_plate_with_holes(
        outer_poly_2d=outer_base, holes_2d=flex_holes, thickness=19.195,
        center=(0.0, 0.0, -2.4025),  # z_loc [-12.0, +7.195] (5 um STL-manifold precision seam to top_deck @ +7.200!)
        name="S4.3-01_monolithic_flexure_body", material="Ti-6Al-4V",
    )

    # Top kinematic moving wafer-chuck deck (76x76x4.8 mm, z_loc [+7.2, +12.0], flush on flex_body!)
    # Includes 4x machined Z/tip/tilt PZT actuator pockets @ (±25.0, ±25.0) + 4x Vespel seat holes @ (±32.0, ±32.0)
    top_holes: list[list[tuple[float, float]]] = [circle_2d(18.0, segments=28, ccw=False)]
    for vx, vy in ((-32.0, -32.0), (32.0, -32.0), (32.0, 32.0), (-32.0, 32.0)):
        top_holes.append(circle_2d(2.6, cx=vx, cy=vy, segments=10, ccw=False))
    z_piezo_pts = ((-25.0, -25.0), (25.0, -25.0), (25.0, 25.0), (-25.0, 25.0))
    for px, py in z_piezo_pts:
        top_holes.append(circle_2d(3.2, cx=px, cy=py, segments=12, ccw=False))
    top_deck = make_plate_with_holes(
        outer_poly_2d=_chamfered_rect_2d(76.0, 76.0, 3.0), holes_2d=top_holes,
        thickness=4.8, center=(0.0, 0.0, 9.6),  # z_loc [+7.2, +12.0] (eliminates legacy 0.200 mm air gap!)
        name="S4.3-01_moving_deck", material="Invar-36",
    )

    # 4x integral raised Vespel-standoff seat bosses (+0.495 mm to z_loc=+12.50 -> Z_world=-28.50 mm, closing 0.50 mm gap to S6.2-01!)
    vespel_bosses: list[SolidMesh] = []
    for idx, (vx, vy) in enumerate(((-32.0, -32.0), (32.0, -32.0), (32.0, 32.0), (-32.0, 32.0)), start=1):
        vespel_bosses.append(
            make_tube(2.6, 5.2, 0.495, segments=16, center=(vx, vy, 12.2525), name=f"S4.3-01_vespel_boss_{idx}", material="Invar-36")
        )

    # Embedded 6-DOF UHV PZT multilayer piezo actuator stacks (2x X-pocket, 2x Y-pocket, 4x Z/tip/tilt pocket)
    piezo_stacks: list[SolidMesh] = [
        make_box(16.0, 3.2, 14.0, center=(0.0, +33.25, -2.4), name="S4.3-01_pzt_x_pos", material="Al2O3"),
        make_box(16.0, 3.2, 14.0, center=(0.0, -33.25, -2.4), name="S4.3-01_pzt_x_neg", material="Al2O3"),
        make_box(3.2, 16.0, 14.0, center=(+24.5, 0.0, -2.4), name="S4.3-01_pzt_y_pos", material="Al2O3"),
        make_box(3.2, 16.0, 14.0, center=(-24.5, 0.0, -2.4), name="S4.3-01_pzt_y_neg", material="Al2O3"),
    ]
    for idx, (px, py) in enumerate(z_piezo_pts, start=1):
        piezo_stacks.append(
            make_cylinder(2.8, 4.79, segments=14, center=(px, py, 9.6), name=f"S4.3-01_pzt_z_{idx}", material="Al2O3")
        )

    mesh = merge_solids([flex_body, top_deck, *vespel_bosses, *piezo_stacks], name="S4.3-01_6dof_flexure_fine_stage", material="Ti-6Al-4V")
    # Compact STEP mesh preserving 90x90 serpentine EDM flexure body + flush moving deck (~680 faces)
    step_flex = make_plate_with_holes(
        outer_poly_2d=outer_base,
        holes_2d=[circle_2d(18.0, segments=16, ccw=False)] + flex_holes[5:9],
        thickness=19.195, center=(0.0, 0.0, -2.4025), material="Ti-6Al-4V",
    )
    step_top = make_plate_with_holes(
        outer_poly_2d=_chamfered_rect_2d(76.0, 76.0, 3.0),
        holes_2d=[circle_2d(18.0, segments=16, ccw=False)],
        thickness=4.8, center=(0.0, 0.0, 9.6), material="Invar-36",
    )
    step_mesh = merge_solids([step_flex, step_top], name="S4.3-01_step", material="Ti-6Al-4V")

    # Stage Z positioning stackup check (fine stage + coarse stage + pedestal -> wafer chuck height)
    stage_stack = check_tolerance_stack(
        [
            ToleranceContributor("invar_pedestal", 137.5, 0.015, -0.015, sign=+1.0),
            ToleranceContributor("coarse_xy_stage", 23.0, 0.010, -0.010, sign=+1.0),
            ToleranceContributor("fine_6dof_flexure", 24.5, 0.005, -0.005, sign=+1.0),
            ToleranceContributor("datum_height", 185.0, 0.000, 0.000, sign=-1.0),
        ],
        target_min_mm=-0.035,
        target_max_mm=+0.035,
    )

    scad_feats = [
        ScadFeature("add_box", {"dx": 90.0, "dy": 90.0, "dz": 19.2}, translate=(0.0, 0.0, -2.4), comment="Ti-6Al-4V monolithic double-compound serpentine EDM flexure body (k_eff~2.17 MN/m)"),
        ScadFeature("add_box", {"dx": 76.0, "dy": 76.0, "dz": 4.8}, translate=(0.0, 0.0, 9.6), comment="Invar-36 6-DOF moving stage platform (0.000 mm flush mate)"),
        ScadFeature("cut_hole", {"d": 36.0, "h": 28.0}, comment="Central Ø36 mm axial clear aperture"),
        ScadFeature("add_box", {"dx": 16.0, "dy": 3.2, "dz": 14.0}, translate=(0.0, 33.25, -2.4), comment="Embedded UHV PZT X-axis actuator stack"),
        ScadFeature("add_box", {"dx": 3.2, "dy": 16.0, "dz": 14.0}, translate=(24.5, 0.0, -2.4), comment="Embedded UHV PZT Y-axis actuator stack"),
    ]

    design = make_part_design_from_bom(
        "S4.3-01",
        design_tier="CUSTOM_FULL",
        material="Ti-6Al-4V",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, -41.0),
        ports=(
            PortInterface(
                name="vespel_standoff_deck",
                kind="mechanical",
                position_mm=(0.0, 0.0, 12.5),
                normal=(0.0, 0.0, 1.0),
                standard="4x Raised Vespel SP-22 Thermal Standoff Bosses @ (±32, ±32), Z_world=-28.50 mm",
                mating_part_id="S6.2-01",
                bore_mm=36.0,
            ),
            PortInterface(
                name="coarse_stage_mount",
                kind="bolt",
                position_mm=(0.0, 0.0, -12.0),
                normal=(0.0, 0.0, -1.0),
                standard="4x M4 Corner Mounts @ (±39.5, ±39.5) flush on S4.3-02",
                mating_part_id="S4.3-02",
                bolt_count=4,
                bolt_hole_mm=4.4,
                bolt_spec="M4",
            ),
            PortInterface(
                name="mirror_x_face",
                kind="optical",
                position_mm=(45.0, 0.0, 0.0),
                normal=(1.0, 0.0, 0.0),
                standard="Zerodur Bar Mirror Riser Bracket Seat (+X/+Y/-Y)",
                mating_part_id="S4.4-03",
            ),
        ),
        dimensions=(
            DimensionCallout("STAGE_X", 90.0, 0.01, -0.01, view="top"),
            DimensionCallout("STAGE_Y", 90.0, 0.01, -0.01, view="top"),
            DimensionCallout("STAGE_H", 24.5, 0.005, -0.005, view="front"),
            DimensionCallout("BLADE_TX", tx, 0.005, -0.005, view="top"),
            DimensionCallout("BLADE_TY", ty, 0.005, -0.005, view="top"),
            DimensionCallout("CENTER_BORE", 36.0, 0.02, -0.02, view="top", prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.002, datum_primary="", feature_note="TOP MOVING PLATFORM DATUM A"),
            GDTFrame("parallelism", 0.005, datum_primary="A", feature_note="BASE MOUNTING PLANE"),
            GDTFrame("perpendicularity", 0.005, datum_primary="A", feature_note="MIRROR REFERENCE FACES"),
        ),
        notes=(
            "Monolithic double-compound serpentine EDM Ti-6Al-4V flexure stage (t_x=1.96 mm, t_y=1.29 mm, k_eff~2.17 MN/m matching Exp133 k_piezo=2.174 MN/m, ~16,354x reduction from legacy 35.5 GN/m, peak vM < 200 MPa << 880 MPa yield at 200 um stroke).",
            "Eliminated 0.200 mm top-deck air gap and 0.50-1.50 mm stack Z-gaps; embedded 8x UHV PZT multilayer actuator stacks (2X + 2Y + 4Z/tip/tilt).",
            f"Z stage stackup RSS={stage_stack.rss_half_band_mm:.4f} mm, WC={stage_stack.wc_half_band_mm:.4f} mm (PASS).",
        ),
        scad_params=(
            ("stage_xy_mm", 90.0),
            ("stage_h_mm", 24.5),
            ("stroke_um", 200.0),
            ("blade_tx_mm", tx),
            ("blade_ty_mm", ty),
            ("k_eff_target_MN_m", 2.174),
            ("n_flexure_slots", 8),
            ("n_pzt_stacks", 8),
            ("top_deck_gap_mm", 0.0),
            ("bore_d_mm", 36.0),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        tolerance_checks=(stage_stack.to_dict(),),
    )


def _build_s4_3_02() -> BuiltPart:
    """S4.3-02: ±25 mm UHV stick-slip crossed-roller XY coarse stage + coaxial Invar-36 pedestal (flush Z-stack)."""
    # World origin = (0, 0, -145.0):
    # - Upper Y crossed-roller carriage: Z_world [-65.0, -53.0] -> z_loc [+80.0, +92.0], center +86.0 (0.0 mm gap to S4.3-01!)
    # - Lower X crossed-roller carriage: Z_world [-76.0, -65.0] -> z_loc [+69.0, +80.0], center +74.5 (flush!)
    # - Coaxial Invar-36 tubular pedestal (R=45..52, h=130.0): Z_world [-206.0, -76.0] -> z_loc [-61.0, +69.0], center +4.0 (flush!)
    # - Bolted Invar-36 base flange ring (R=45..55, h=8.0, 8x M4): Z_world [-214.0, -206.0] -> z_loc [-69.0, -61.0], center -65.0
    upper_carr = make_plate_with_holes(
        outer_poly_2d=_chamfered_rect_2d(96.0, 96.0, 3.0),
        holes_2d=[circle_2d(21.0, segments=28, ccw=False)],
        thickness=11.995, center=(0.0, 0.0, 86.0025),
        name="S4.3-02_upper_y_carriage", material="Ti-6Al-4V",
    )
    lower_carr = make_plate_with_holes(
        outer_poly_2d=_chamfered_rect_2d(96.0, 96.0, 3.0),
        holes_2d=[circle_2d(21.0, segments=28, ccw=False)],
        thickness=10.995, center=(0.0, 0.0, 74.5025),
        name="S4.3-02_lower_x_carriage", material="Ti-6Al-4V",
    )
    # Machined crossed-roller V-way side rail gibs (64 mm long -> clears ±38 mm S4.3-03 coax pigtails)
    # & 2x piezo stick-slip inertia actuators (height 10 mm -> clears pedestal top at z_loc=+69.0)
    rail_y1 = make_box(64.0, 4.0, 6.0, center=(0.0, -50.2, 74.5), name="v_rail_x1", material="Al2O3")
    rail_y2 = make_box(64.0, 4.0, 6.0, center=(0.0, +50.2, 74.5), name="v_rail_x2", material="Al2O3")
    rail_x1 = make_box(4.0, 64.0, 6.0, center=(-50.2, 0.0, 86.0), name="v_rail_y1", material="Al2O3")
    rail_x2 = make_box(4.0, 64.0, 6.0, center=(+50.2, 0.0, 86.0), name="v_rail_y2", material="Al2O3")
    act_x = make_box(7.0, 24.0, 10.0, center=(-52.0, 0.0, 74.5), name="stickslip_act_x", material="Ti-6Al-4V")
    act_y = make_box(24.0, 7.0, 10.0, center=(0.0, -52.0, 86.0), name="stickslip_act_y", material="Ti-6Al-4V")

    # Coaxial Invar-36 tubular pedestal threading between Cryoperm (R=41) and B-coils (R=56)
    pedestal = make_tube(
        r_in=45.0, r_out=52.0, height=129.995, segments=48,
        center=(0.0, 0.0, 4.0025), name="S4.3-02_invar_pedestal", material="Invar-36",
    )
    base_ring = make_ring_with_bolt_circle(
        r_in=45.0, r_out=55.0, thickness=8.0, pcd=100.0, n_bolts=8, bolt_diameter=4.5,
        sub_per_side=2, center=(0.0, 0.0, -65.0), name="S4.3-02_pedestal_base_ring", material="Invar-36",
    )

    shells = [upper_carr, lower_carr, rail_y1, rail_y2, rail_x1, rail_x2, act_x, act_y, pedestal, base_ring]
    mesh = merge_solids(shells, name="S4.3-02_coarse_xy_and_pedestal", material="Invar-36")

    step_mesh = merge_solids(
        [
            make_plate_with_holes(_chamfered_rect_2d(96.0, 96.0, 3.0), [circle_2d(21.0, segments=16, ccw=False)], 22.995, center=(0.0, 0.0, 80.5025), material="Ti-6Al-4V"),
            make_tube(45.0, 52.0, 129.995, segments=24, center=(0.0, 0.0, 4.0025), material="Invar-36"),
            make_tube(45.0, 55.0, 8.0, segments=24, center=(0.0, 0.0, -65.0), material="Invar-36"),
        ],
        name="S4.3-02_step",
        material="Invar-36",
    )

    scad_feats = (
        ScadFeature("add_box", {"dx": 96.0, "dy": 96.0, "dz": 23.0}, translate=(0.0, 0.0, 80.5), comment="±25 mm Ti/ceramic crossed-roller stick-slip XY coarse stage"),
        ScadFeature("add_tube", {"od": 104.0, "id": 90.0, "h": 130.0}, translate=(0.0, 0.0, 4.0), comment="Coaxial Invar-36 pedestal (R=45..52 clearing Cryoperm & B-coils)"),
        ScadFeature("add_tube", {"od": 110.0, "id": 90.0, "h": 8.0}, translate=(0.0, 0.0, -65.0), comment="Bolted chamber-floor pedestal flange"),
        ScadFeature("cut_bolt_circle", {"pcd": 100.0, "bolt_d": 4.5, "count": 8, "h": 12.0}, translate=(0.0, 0.0, -65.0), comment="8x M4 pedestal base bolt circle"),
        ScadFeature("cut_hole", {"d": 42.0, "h": 26.0}, translate=(0.0, 0.0, 80.5), comment="Ø42 mm central bore"),
    )
    design = make_part_design_from_bom(
        "S4.3-02",
        design_tier="CUSTOM_FULL",  # BOM COTS/CUS + custom coaxial Invar-36 pedestal clearing Cryoperm/B-coils
        material="Invar-36",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, -145.0),
        ports=(
            PortInterface(
                name="fine_stage_top_mount",
                kind="mechanical",
                position_mm=(0.0, 0.0, 92.0),
                normal=(0.0, 0.0, 1.0),
                standard="±25 mm Crossed-Roller XY Carriage Top (flush Z_world=-53.0 mm)",
                mating_part_id="S4.3-01",
                bore_mm=42.0,
            ),
            PortInterface(
                name="chamber_bottom_bolt_ring",
                kind="bolt",
                position_mm=(0.0, 0.0, -69.0),
                normal=(0.0, 0.0, -1.0),
                standard="8x M4 @ PCD 100.0 mm on UHV Bottom Flange",
                mating_part_id="S5.1-01",
                bore_mm=90.0,
                od_mm=110.0,
                pcd_mm=100.0,
                bolt_count=8,
                bolt_hole_mm=4.5,
                bolt_spec="M4",
            ),
        ),
        dimensions=(
            DimensionCallout("STAGE_XY", 96.0, 0.05, -0.05, view="top"),
            DimensionCallout("PEDESTAL_OD", 104.0, 0.02, -0.02, view="front", prefix="Ø"),
            DimensionCallout("PEDESTAL_ID", 90.0, 0.02, -0.02, view="front", prefix="Ø"),
            DimensionCallout("TOTAL_H", 161.0, 0.05, -0.05, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.005, datum_primary="", feature_note="XY CARRIAGE TOP DATUM A"),
            GDTFrame("coaxiality", 0.020, diameter_zone=True, datum_primary="B", feature_note="INVAR PEDESTAL R=45..52"),
            GDTFrame("perpendicularity", 0.010, datum_primary="A", feature_note="BASE MOUNTING FLANGE"),
        ),
        notes=(
            "Non-magnetic Ti-6Al-4V / ceramic crossed-roller stick-slip XY stepper (±25 mm stroke, ±50 nm coarse step), mated flush to S4.3-01 at Z_world=-53.0 mm (0.00 mm Z-gap).",
            "Integrated coaxial Invar-36 pedestal (R=45..52 mm) clears Cryoperm (R=41 mm) by 4 mm and B-coils (R=56 mm) by 4 mm.",
        ),
        scad_params=(
            ("coarse_xy_mm", 96.0),
            ("stroke_xy_mm", 25.0),
            ("pedestal_id_mm", 90.0),
            ("pedestal_od_mm", 104.0),
            ("pedestal_h_mm", 138.0),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=scad_feats,
        step_mesh=step_mesh,
        density_kg_m3=6600.0,  # Composite Ti-6Al-4V crossed-roller stage + Invar-36 tubular pedestal
    )


def _build_s4_3_03() -> BuiltPart:
    """S4.3-03: In-stage sub-nm capacitive position sensors (4 diagonal pods) + swept Kapton UHV coax."""
    # World origin = (0, 0, -41.0)
    # 4 diagonal pods at (±51.0, ±38.0), size 8.5 x 8.5 x 14.0 mm (Z_world [-48, -34], clears S4.3-01 ±45,
    # clears S4.4-03 mirrors ±26, max corner R = hypot(55.25, 42.25) = 69.6 < 75.0 mm magnet bore!)
    pod_xy = ((51.0, 38.0), (-51.0, 38.0), (-51.0, -38.0), (51.0, -38.0))
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    for idx, (px, py) in enumerate(pod_xy, start=1):
        # Gold-plated capacitive sensor body + inner guard electrode face
        body = make_chamfered_box(8.5, 8.5, 14.0, chamfer=0.8, center=(px, py, 0.0), name=f"cap_sensor_{idx}", material="Au")
        # Swept Kapton UHV coax pigtail dropping cleanly from z_loc=-7.2 down to z_loc=-33.0 (Z_world=-74.0)
        sx = 1.0 if px > 0 else -1.0
        spine = [
            [px, py, -7.2],
            [px + sx * 1.5, py, -15.0],
            [px + sx * 2.5, py, -24.0],
            [px + sx * 2.5, py, -33.0],
        ]
        coax = make_swept_tube(spine, r_out=1.0, r_in=0.0, segments=10, name=f"cap_coax_{idx}", material="Vespel SP-22")
        shells.extend([body, coax])

        step_shells.append(make_box(8.5, 8.5, 14.0, center=(px, py, 0.0), material="Au"))
        step_shells.append(make_cylinder(1.0, 25.8, segments=8, center=(px + sx * 1.5, py, -20.1), material="Vespel SP-22"))
        scad_feats.append(
            ScadFeature("add_box", {"dx": 8.5, "dy": 8.5, "dz": 14.0}, translate=(px, py, 0.0), comment=f"Sub-nm capacitive feedback sensor pod #{idx}")
        )

    mesh = merge_solids(shells, name="S4.3-03_capacitive_sensors", material="Au")
    step_mesh = merge_solids(step_shells, name="S4.3-03_step", material="Au")

    design = make_part_design_from_bom(
        "S4.3-03",
        design_tier="COTS_ENV_ICD",
        material="Au",
        surface_finish_ra_um=0.2,
        world_origin_mm=(0.0, 0.0, -41.0),
        ports=(
            PortInterface(
                name="capacitive_gap_sense",
                kind="electrical",
                position_mm=(46.75, 38.0, 0.0),
                normal=(-1.0, 0.0, 0.0),
                standard="4x Sub-nm Au Capacitive Electrodes (<0.02% Linearity)",
                mating_part_id="S4.3-01",
            ),
            PortInterface(
                name="kapton_uhv_coax",
                kind="rf",
                position_mm=(53.5, 38.0, -33.0),
                normal=(0.0, 0.0, -1.0),
                standard="UHV Kapton Coax Harness to S4.3-04 Servo Controller",
                mating_part_id="S4.3-04",
            ),
        ),
        dimensions=(
            DimensionCallout("POD_SIZE", 8.5, 0.05, -0.05, view="top"),
            DimensionCallout("POD_H", 14.0, 0.05, -0.05, view="front"),
            DimensionCallout("SPAN_X", 110.5, 0.1, -0.1, view="top"),
            DimensionCallout("SPAN_Y", 84.5, 0.1, -0.1, view="top"),
        ),
        gdt_frames=(
            GDTFrame("parallelism", 0.005, datum_primary="A", feature_note="CAPACITIVE ELECTRODE FACES"),
        ),
        notes=(
            "4x UHV gold-electrode capacitive position feedback pods (±0.2 nm, <0.02% linearity) + Kapton UHV coax pigtails.",
            "Diagonal layout (±51, ±38 mm, R_max=69.6 < 75 mm bore) clears S4.3-01 stage & S4.4-03 bar mirrors cleanly.",
        ),
        scad_params=(("n_sensor_pods", 4), ("pod_x_mm", 51.0), ("pod_y_mm", 38.0)),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=5200.0,  # Composite Au-plated Ti sensor heads + Kapton coax
    )


def _build_s4_3_04() -> BuiltPart:
    """S4.3-04: 6-channel low-noise piezo servo controller & HV driver (E-712 class, 2U, Bay 1 U15-U16)."""
    u_start, u_count = 15, 2
    depth_mm = 420.0
    internals: list[SolidMesh] = [
        make_box(380.0, 280.0, 2.4, center=(0.0, -20.0, -32.0), name="e712_servo_mainboard", material="FR4"),
    ]
    for idx, cx in enumerate(np.linspace(-150.0, 150.0, 6), start=1):
        internals.append(
            make_box(34.0, 220.0, 56.0, center=(float(cx), 20.0, 2.0), name=f"hv_amp_card_{idx}", material="Al 6061")
        )
    fconns = [(float(x), 14.0, 6.0, 12.0) for x in np.linspace(-150.0, 150.0, 6)]
    fconns.extend([(float(x), -16.0, 5.0, 11.0) for x in np.linspace(-150.0, 150.0, 6)])
    rconns = [(-140.0, 0.0, 8.0, 14.0), (0.0, 0.0, 7.0, 12.0), (140.0, 0.0, 8.0, 14.0)]

    mesh, step_mesh, scad_feats = _make_rack_chassis_shell(
        u_count=u_count,
        depth_mm=depth_mm,
        rear_heatsink_fins=11,
        front_connectors=fconns,
        rear_connectors=rconns,
        internal_solids=internals,
        name="S4.3-04_6ch_piezo_servo_ctrl",
        material="Al 6061",
    )
    design = make_part_design_from_bom(
        "S4.3-04",
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
                standard="EIA-310 19-inch 2U (Bay 1 U15-U16, X=1480 mm)",
                mating_part_id="S7.4-03",
            ),
            PortInterface(
                name="hv_piezo_6ch_out",
                kind="electrical",
                position_mm=(0.0, -0.5 * depth_mm, 14.0),
                normal=(0.0, -1.0, 0.0),
                standard="6x LEMO HV Piezo Drive + 6x Cap Sensor + EtherCAT/SPI",
                mating_part_id="S4.3-01",
            ),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", RACK_WIDTH_MM, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_2U", rack_u_height_mm(u_count), 0.3, -0.3, view="front"),
            DimensionCallout("DEPTH", depth_mm, 0.5, -0.5, view="top"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-INCH FRONT FLANGE"),
        ),
        notes=(
            "PI E-712 class 6-channel 24-bit DAC piezo servo controller & HV driver (<0.1 nm noise, EtherCAT/SPI).",
            "Synchronizes S4.3-02 ±25 mm coarse stage with S4.3-01 200 um fine stage. Rack Bay 1 (X=+1480 mm) U15-U16 (2U).",
        ),
        scad_params=(("rack_u_height", 2), ("n_piezo_channels", 6), ("dac_bits", 24), ("depth_mm", depth_mm)),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=2500.0,
    )


def _build_s4_4_01() -> BuiltPart:
    """S4.4-01: 3-axis frequency-stabilized 632.8 nm He-Ne laser unit (Renishaw XL-80/RLE)."""
    # World origin = (330.0, 245.0, -205.0) -> X in [260, 400], Y in [202, 288], Z_world in [-239, -173]
    # Sits cleanly on +X/+Y corner of S4.2-01 active table (top at Z=-240 mm) via 3 kinematic feet!
    main_body = make_chamfered_box(136.0, 84.0, 52.0, chamfer=3.0, center=(0.0, 0.0, 0.0), name="hene_housing", material="Al 6061")
    # Internal/protruding stabilized He-Ne resonator tube sleeve on +X side & 3x FC/APC fiber launch barrels on -X face
    laser_barrel = make_cylinder(16.0, 12.0, segments=20, axis="x", center=(74.1, 0.0, 0.0), name="hene_tube_cap", material="316LN")
    shells: list[SolidMesh] = [main_body, laser_barrel]
    step_shells: list[SolidMesh] = [make_box(136.0, 84.0, 52.0, material="Al 6061"), laser_barrel]

    for idx, fy in enumerate((-22.0, 0.0, 22.0), start=1):
        fc = make_cylinder(5.5, 14.0, segments=14, axis="-x", center=(-75.1, fy, 0.0), name=f"fc_apc_port_{idx}", material="316LN")
        shells.append(fc)
        step_shells.append(make_cylinder(5.5, 14.0, segments=8, axis="-x", center=(-75.1, fy, 0.0), material="316LN"))

    # Top convection cooling fins (6 fins, z_loc [+26.1, +32.0])
    for idx, fx in enumerate(np.linspace(-50.0, 50.0, 6)):
        shells.append(make_box(4.0, 76.0, 5.8, center=(float(fx), 0.0, 29.0), name=f"hene_fin_{idx}", material="Al 6061"))

    # 3 kinematic leveling feet beneath housing (z_loc [-34.0, -26.1] -> Z_world [-239.0, -231.1], 1 mm above S4.2-01!)
    for idx, (kx, ky) in enumerate(((-52.0, -28.0), (52.0, -28.0), (0.0, 28.0)), start=1):
        foot = make_cylinder(8.0, 7.8, segments=14, center=(kx, ky, -30.0), name=f"hene_foot_{idx}", material="316LN")
        shells.append(foot)
        step_shells.append(make_cylinder(8.0, 7.8, segments=8, center=(kx, ky, -30.0), material="316LN"))

    mesh = merge_solids(shells, name="S4.4-01_hene_laser_unit", material="Al 6061")
    step_mesh = merge_solids(step_shells, name="S4.4-01_step", material="Al 6061")

    scad_feats = (
        ScadFeature("add_box", {"dx": 136.0, "dy": 84.0, "dz": 52.0}, comment="Stabilized 632.8 nm He-Ne laser unit (Renishaw XL-80/RLE)"),
        ScadFeature("add_cylinder", {"d": 11.0, "h": 14.0}, translate=(-75.1, -22.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="FC/APC Fiber Launch X"),
        ScadFeature("add_cylinder", {"d": 11.0, "h": 14.0}, translate=(-75.1, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="FC/APC Fiber Launch Y"),
        ScadFeature("add_cylinder", {"d": 11.0, "h": 14.0}, translate=(-75.1, 22.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="FC/APC Fiber Launch Z"),
    )
    design = make_part_design_from_bom(
        "S4.4-01",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=0.8,
        world_origin_mm=(330.0, 245.0, -205.0),
        ports=(
            PortInterface(
                name="pm_fiber_3axis_out",
                kind="optical",
                position_mm=(-82.0, 0.0, 0.0),
                normal=(-1.0, 0.0, 0.0),
                standard="3x FC/APC PM Fiber @ 632.8 nm (±0.05 ppm)",
                mating_part_id="S4.4-04",
            ),
            PortInterface(
                name="kinematic_table_mount",
                kind="mechanical",
                position_mm=(0.0, 0.0, -34.0),
                normal=(0.0, 0.0, -1.0),
                standard="3-Point Kinematic Mount on S4.2-01 Active Table",
                mating_part_id="S4.2-01",
            ),
        ),
        dimensions=(
            DimensionCallout("BODY_X", 136.0, 0.5, -0.5, view="top"),
            DimensionCallout("BODY_Y", 84.0, 0.5, -0.5, view="top"),
            DimensionCallout("TOTAL_H", 66.0, 0.5, -0.5, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.05, datum_primary="", feature_note="3-POINT KINEMATIC FOOT PLANE"),
        ),
        notes=(
            "Renishaw XL-80/RLE-class frequency-stabilized 632.8 nm He-Ne heterodyne laser (±0.05 ppm, <=0.05 nm res).",
            "Mounted on +X/+Y corner of S4.2-01 active table (330, 245, -205 mm), clear of UHV chamber & CF63/CF40 ports.",
        ),
        scad_params=(("wavelength_nm", 632.8), ("freq_stab_ppm", 0.05), ("n_fiber_axes", 3)),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=scad_feats,
        step_mesh=step_mesh,
        density_kg_m3=2100.0,  # Hollow CNC Al laser enclosure + glass He-Ne plasma tube & optics
    )


def _build_s4_4_02() -> BuiltPart:
    """S4.4-02: 3x UHV differential plane-mirror interferometer periscope relay heads (split-gap Z=[-18, +18])."""
    # World origin = (0, 0, -133.0):
    # Routes 632.8 nm beams from S4.4-04 CF40 viewports (R=240.5, Z=-133) through carved S4.5-01 optical windows
    # to lower 45-deg fold-up mirrors @ R=128.0, Z=-133.0, straight UP the unobstructed vertical corridor
    # (R=128.0 between S6_coil_s R=116 and S6_coil_a R=144!) into upper differential PBS heads strictly inside
    # the 36 mm split gap (Z_nat=[-15.0, +17.5] / Z_canon=[485.0, 517.5]) targeting:
    #   - Measurement mirror S4.4-03 @ R=65.0, Z_nat=-9.0 (Z_canon=491.0)
    #   - Reference mirror   S2.5-03 @ R=62.0, Z_nat=+14.3 (Z_canon=514.3)
    head_specs = (
        ("X", 0.0),
        ("Y", 90.0),
        ("Z", 270.0),
    )
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    for label, ang in head_specs:
        rad = math.radians(ang)
        ca, sa = math.cos(rad), math.sin(rad)
        tx, ty = -sa, ca  # tangential unit vector
        # 1) Lower 45-deg Zerodur fold-up mirror mount seated behind R=128.0 beam axis (R in [122.0, 126.5], z_loc=[-5.5, +5.5])
        #    Leaves the radial entry ray (R=240.5 -> 128.0, Z=-133.0) and vertical relay ray (R=128.0, Z=-133 -> +14.3) 100% unoccluded!
        lower_fold = transform_mesh(
            make_chamfered_box(4.5, 11.0, 11.0, chamfer=0.8, name=f"interf_{label}_lower_fold", material="Invar-36"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(124.25 * ca, 124.25 * sa, 0.0),
        )
        # 2) Slim tangentially-offset Invar-36 vertical periscope relay mast (offset +9.5 mm tangentially at R=128.0,
        #    z_loc=[-5.5, +117.8] -> clears lower_fold tangentially, upper_head vertically & tangentially, and R=128 beam!)
        mast = transform_mesh(
            make_box(4.5, 4.0, 123.3, name=f"interf_{label}_periscope_mast", material="Invar-36"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(128.0 * ca + 9.5 * tx, 128.0 * sa + 9.5 * ty, 56.15),
        )
        # 3) Upper split-gap differential PBS & dual-beam fold head seated behind R=128.0 (R in [129.5, 137.5],
        #    z_loc=[+118.0, +150.5] -> Z_nat=[-15.0, +17.5] / Z_canon=[485.0, 517.5])
        #    Leaves radial inward measurement ray (R=128->65, Z=-9.0) and reference ray (R=128->62, Z=+14.3) 100% clear!
        upper_head = transform_mesh(
            make_chamfered_box(8.0, 14.0, 32.5, chamfer=1.0, name=f"interf_{label}_splitgap_pbs", material="Invar-36"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(133.5 * ca, 133.5 * sa, 134.25),
        )
        shells.extend([lower_fold, mast, upper_head])
        step_shells.extend([
            transform_mesh(make_box(4.5, 11.0, 11.0, material="Invar-36"), rotation_deg=(0.0, 0.0, ang), translation=(124.25 * ca, 124.25 * sa, 0.0)),
            transform_mesh(make_box(4.5, 4.0, 123.3, material="Invar-36"), rotation_deg=(0.0, 0.0, ang), translation=(128.0 * ca + 9.5 * tx, 128.0 * sa + 9.5 * ty, 56.15)),
            transform_mesh(make_box(8.0, 14.0, 32.5, material="Invar-36"), rotation_deg=(0.0, 0.0, ang), translation=(133.5 * ca, 133.5 * sa, 134.25)),
        ])
        scad_feats.append(
            ScadFeature("add_box", {"dx": 8.0, "dy": 14.0, "dz": 32.5}, translate=(133.5 * ca, 133.5 * sa, 134.25), rotate=(0.0, 0.0, ang), comment=f"Split-gap differential PBS head {label}-axis (Z_canon=[485, 517.5])")
        )
        scad_feats.append(
            ScadFeature("add_box", {"dx": 4.5, "dy": 4.0, "dz": 123.3}, translate=(128.0 * ca + 9.5 * tx, 128.0 * sa + 9.5 * ty, 56.15), rotate=(0.0, 0.0, ang), comment=f"Periscope optical relay mast {label}-axis")
        )

    mesh = merge_solids(shells, name="S4.4-02_3x_uhv_interf_heads", material="Invar-36")
    step_mesh = merge_solids(step_shells, name="S4.4-02_step", material="Invar-36")

    design = make_part_design_from_bom(
        "S4.4-02",
        design_tier="COTS_ENV_ICD",
        material="Invar-36",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, INTERF_Z_MM),
        ports=(
            PortInterface(
                name="optical_viewport_beam_in",
                kind="optical",
                position_mm=(128.0, 0.0, 0.0),
                normal=(1.0, 0.0, 0.0),
                standard="3x 632.8 nm Lower Periscope Entry @ Z=-133 mm (Z_canon=367 mm)",
                mating_part_id="S4.4-04",
            ),
            PortInterface(
                name="splitgap_stage_beam_out",
                kind="optical",
                position_mm=(128.0, 0.0, 124.0),
                normal=(-1.0, 0.0, 0.0),
                standard="3x 632.8 nm Split-Gap Measurement Beam @ Z_nat=-9.0 mm (Z_canon=491 mm)",
                mating_part_id="S4.4-03",
            ),
            PortInterface(
                name="splitgap_ref_beam_out",
                kind="optical",
                position_mm=(128.0, 0.0, 147.3),
                normal=(-1.0, 0.0, 0.0),
                standard="3x 632.8 nm Split-Gap Reference Beam @ Z_nat=+14.3 mm (Z_canon=514.3 mm)",
                mating_part_id="S2.5-03",
            ),
        ),
        dimensions=(
            DimensionCallout("RELAY_RADIUS", 128.0, 0.05, -0.05, view="top", prefix="R"),
            DimensionCallout("PERISCOPE_H", 156.0, 0.05, -0.05, view="front"),
            DimensionCallout("PBS_HEAD_H", 32.5, 0.05, -0.05, view="front"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.005, datum_primary="A", feature_note="PERISCOPE & PBS OPTICAL AXES"),
            GDTFrame("position", 0.020, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="3-AXIS SPLIT-GAP RELAY"),
        ),
        notes=(
            "3x UHV zero-dead-path differential plane-mirror interferometer periscope relay assemblies (X:0, Y:90, Z:270 deg) @ R=128.0 mm.",
            "Routes beams unobstructed from S4.4-04 viewports (Z_canon=367) through carved S4.5-01 windows up the R=128 mm inter-coil corridor into the Z_canon=[482, 518] mm split gap to S4.4-03 (Z=491) & S2.5-03 (Z=514.3).",
        ),
        scad_params=(("n_heads", 3), ("relay_radius_mm", 128.0), ("z_entry_mm", INTERF_Z_MM), ("z_meas_mm", -9.0), ("z_ref_mm", 14.3)),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=5400.0,  # Invar-36 housing + fused-silica PBS/fold optics
    )


def _build_s4_4_03() -> BuiltPart:
    """S4.4-03: 3x Zerodur/ULE lambda/20 split-gap stage bar mirrors on Invar-36 riser brackets (X, Y, Z)."""
    # World origin = (0, 0, -41.0); mirrors raised into the unoccluded Z_nat=[-14.0, -4.0] (Z_canon=[486, 496]) split gap
    # at R_face=65.0 mm (R in [59.5, 65.0], tangential width 26 mm -> ±11.5 deg, clearing S3.2-01 CSA >=22 deg & S6.2-01 R=58.0!)
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    for label, ang in (("x", 0.0), ("y", 90.0), ("z", 270.0)):
        rad = math.radians(ang)
        ca, sa = math.cos(rad), math.sin(rad)
        # Zerodur lambda/20 mirror bar inside split gap: R in [59.5, 65.0], z_loc in [+27.0, +37.0] (Z_nat=[-14.0, -4.0])
        mbar = transform_mesh(
            make_chamfered_box(5.5, 26.0, 10.0, chamfer=0.4, name=f"zerodur_mirror_{label}", material="Zerodur"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(62.25 * ca, 62.25 * sa, 32.0),
        )
        # Rigid Invar-36 vertical optical riser stalk (R in [59.5, 64.0], z_loc in [-3.995, +26.995], 5 um STL seam)
        riser = transform_mesh(
            make_box(4.5, 16.0, 30.99, name=f"invar_riser_{label}", material="Invar-36"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(61.75 * ca, 61.75 * sa, 11.5),
        )
        # Lower Invar-36 stage-flank mounting foot connecting riser to S4.3-01 flank (R in [45.0, 59.495], z_loc in [-4.0, +2.0])
        foot = transform_mesh(
            make_box(14.495, 16.0, 6.0, name=f"invar_foot_{label}", material="Invar-36"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(52.2475 * ca, 52.2475 * sa, -1.0),
        )
        shells.extend([mbar, riser, foot])
        step_shells.extend([
            transform_mesh(make_box(5.5, 26.0, 10.0, material="Zerodur"), rotation_deg=(0.0, 0.0, ang), translation=(62.25 * ca, 62.25 * sa, 32.0)),
            transform_mesh(make_box(4.5, 16.0, 30.99, material="Invar-36"), rotation_deg=(0.0, 0.0, ang), translation=(61.75 * ca, 61.75 * sa, 11.5)),
        ])
        scad_feats.append(
            ScadFeature("add_box", {"dx": 5.5, "dy": 26.0, "dz": 10.0}, translate=(62.25 * ca, 62.25 * sa, 32.0), rotate=(0.0, 0.0, ang), comment=f"Split-gap Zerodur lambda/20 bar mirror {label.upper()}-axis (Z_canon=491 mm)")
        )

    mesh = merge_solids(shells, name="S4.4-03_3x_zerodur_bar_mirrors", material="Zerodur")
    step_mesh = merge_solids(step_shells, name="S4.4-03_step", material="Zerodur")

    # Verify cryogenic thermal stability 300 K -> 100 K & 4 K for Invar retaining clips on Zerodur mirrors
    tc_clip_4k = check_cold_clearance(
        "Invar-36", "Zerodur", nominal_outer_id_mm=26.20, nominal_inner_od_mm=26.00,
        t_cold_k=4.0, outer_id_tol_mm=0.02, inner_od_tol_mm=0.01,
        min_required_radial_clearance_mm=0.05,
    )

    design = make_part_design_from_bom(
        "S4.4-03",
        design_tier="CUSTOM_FULL",
        material="Zerodur",
        temp_k=4.0,
        surface_finish_ra_um=0.05,
        world_origin_mm=(0.0, 0.0, -41.0),
        ports=(
            PortInterface(
                name="mirror_reflective_facets",
                kind="optical",
                position_mm=(65.0, 0.0, 32.0),
                normal=(1.0, 0.0, 0.0),
                standard="3x Zerodur Al+SiO2 lambda/20 @ 632.8 nm inside Z_canon=[486, 496] mm split gap",
                mating_part_id="S4.4-02",
            ),
            PortInterface(
                name="stage_flank_mount",
                kind="mechanical",
                position_mm=(45.0, 0.0, -1.0),
                normal=(-1.0, 0.0, 0.0),
                standard="3x Rigid Invar-36 Optical Riser Brackets on S4.3-01",
                mating_part_id="S4.3-01",
            ),
        ),
        dimensions=(
            DimensionCallout("BAR_LEN", 26.0, 0.02, -0.02, view="top"),
            DimensionCallout("BAR_THK", 5.5, 0.02, -0.02, view="top"),
            DimensionCallout("BAR_H", 10.0, 0.02, -0.02, view="front"),
            DimensionCallout("OPTICAL_R", 65.0, 0.02, -0.02, view="top", prefix="R"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.000032, datum_primary="", feature_note="OPTICAL FACET LAMBDA/20 @ 632.8 nm"),
            GDTFrame("perpendicularity", 0.002, datum_primary="A", feature_note="ORTHOGONAL X/Y MIRROR PAIR"),
        ),
        notes=(
            "3x Zerodur/ULE lambda/20 stage bar mirrors (26x5.5x10 mm) raised on Invar-36 riser stalks into Z_nat=[-14, -4] mm (Z_canon=[486, 496] mm) split gap with clear normal-incidence LOS to S4.4-02 and minimized 9 mm Abbe offset.",
            f"300K->4K Invar-36 clip vs Zerodur bar WC rad clearance: {tc_clip_4k.cold_worst_case_radial_clearance_mm:.4f} mm (PASS).",
        ),
        scad_params=(("n_mirrors", 3), ("bar_len_mm", 26.0), ("bar_thk_mm", 5.5), ("bar_h_mm", 10.0), ("mirror_r_face_mm", 65.0), ("mirror_z_nat_mm", -9.0)),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        thermal_checks=(tc_clip_4k.to_dict(),),
    )


def _build_s4_4_04() -> BuiltPart:
    """S4.4-04: 3x 632.8 nm AR-coated ISO 3669 CF40 viewports + external fiber launchers & beam benders."""
    # World origin = (0, 0, -133.0); at 0 (+X), 90 (+Y), 270 (-Y) deg, R_face = 212.0 mm
    cf = CF_SPECS["CF40"]
    r_mid = CF40_VIEWPORT_FACE_R_MM + 0.5 * cf.thickness_mm  # 218.35 mm
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    ports: list[PortInterface] = []
    scad_feats: list[ScadFeature] = []

    for idx, (label, ang) in enumerate(zip(("X", "Y", "Z"), CF40_VIEWPORT_AZIMUTHS_DEG), start=1):
        rad = math.radians(ang)
        ca, sa = math.cos(rad), math.sin(rad)
        # Real ISO 3669 CF40 optical viewport (6x Ø6.6 @ PCD 58.7, knife-edge facing inward -r!)
        vp = make_cf_viewport(
            "CF40",
            clear_aperture=28.0,
            window_diameter=33.0,
            window_thickness=6.0,
            with_knife_edge=True,
            sub_per_side=4,
            axis=(-ca, -sa, 0.0),
            center=(r_mid * ca, r_mid * sa, 0.0),
            name=f"S4.4-04_cf40_vp_{label}",
            material="316LN",
            window_material="Fused Silica",
        )
        # External 45-deg beam-bender housing (28x28x28 mm @ R = 239.0 mm)
        r_bender = CF40_VIEWPORT_FACE_R_MM + cf.thickness_mm + 14.5
        bender = transform_mesh(
            make_chamfered_box(26.0, 26.0, 26.0, chamfer=2.0, name=f"bender_{label}", material="Al 6061"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(r_bender * ca, r_bender * sa, 0.0),
        )
        # Tangential FC/APC fiber collimator launcher barrel protruding perpendicular to beam axis
        tx, ty = -sa, ca
        launcher = make_cylinder(
            7.0, 24.0, segments=16, axis=(tx, ty, 0.0),
            center=(r_bender * ca + 25.2 * tx, r_bender * sa + 25.2 * ty, 0.0),
            name=f"fiber_launcher_{label}", material="316LN",
        )
        shells.extend([vp, bender, launcher])

        # Compact STEP proxy (flange cylinder + bender + launcher per axis, 3 x ~120 = ~360 faces)
        step_shells.append(
            make_cylinder(0.5 * cf.od_mm, cf.thickness_mm, segments=18, axis=(-ca, -sa, 0.0), center=(r_mid * ca, r_mid * sa, 0.0), material="316LN")
        )
        step_shells.append(
            transform_mesh(make_box(26.0, 26.0, 26.0, material="Al 6061"), rotation_deg=(0.0, 0.0, ang), translation=(r_bender * ca, r_bender * sa, 0.0))
        )
        step_shells.append(
            make_cylinder(7.0, 24.0, segments=10, axis=(tx, ty, 0.0), center=(r_bender * ca + 25.2 * tx, r_bender * sa + 25.2 * ty, 0.0), material="316LN")
        )

        ports.append(
            make_cf_port_interface(
                "CF40",
                name=f"cf40_ar_viewport_{label}",
                position_mm=(CF40_VIEWPORT_FACE_R_MM * ca, CF40_VIEWPORT_FACE_R_MM * sa, 0.0),
                normal=(-ca, -sa, 0.0),
                mating_part_id="S5.1-01",
                bore_override_mm=28.0,
                notes=f"632.8 nm AR <0.2% CF40 optical viewport ({label}-axis, {ang:.0f} deg)",
            )
        )
        scad_feats.append(
            ScadFeature("add_cf_flange", {"size": "CF40", "blank": False, "bore_id": 28.0}, translate=(r_mid * ca, r_mid * sa, 0.0), rotate=(0.0, -90.0, ang), comment=f"ISO 3669 CF40 632.8 nm AR viewport ({label}-axis)")
        )
        scad_feats.append(
            ScadFeature("add_box", {"dx": 26.0, "dy": 26.0, "dz": 26.0}, translate=(r_bender * ca, r_bender * sa, 0.0), rotate=(0.0, 0.0, ang), comment=f"External 45-deg beam bender & fiber launcher ({label}-axis)")
        )

    mesh = merge_solids(shells, name="S4.4-04_3x_cf40_ar_viewports", material="316LN")
    step_mesh = merge_solids(step_shells, name="S4.4-04_step", material="316LN")

    design = make_part_design_from_bom(
        "S4.4-04",
        design_tier="COTS_ENV_ICD",
        material="316LN",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, INTERF_Z_MM),
        ports=tuple(ports),
        dimensions=(
            DimensionCallout("CF40_OD", cf.od_mm, 0.15, -0.15, view="front", prefix="Ø"),
            DimensionCallout("CF40_PCD", cf.pcd_mm, 0.10, -0.10, view="front", prefix="Ø"),
            DimensionCallout("CLEAR_APERTURE", 28.0, 0.10, -0.10, view="front", prefix="Ø"),
            DimensionCallout("PORT_RADIUS", CF40_VIEWPORT_FACE_R_MM, 0.25, -0.25, view="top", prefix="R"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.015, datum_primary="", feature_note="CF40 KNIFE-EDGE SEALING FACE"),
            GDTFrame("position", 0.12, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="6x Ø6.6 BOLTS @ PCD 58.7"),
        ),
        notes=(
            "3x ISO 3669 CF40 fused-silica AR viewports (R < 0.2% @ 632.8 nm, lambda/10, low birefringence) + fiber launchers & beam benders.",
            "Aligned at 0/90/270 deg, R_face=240.5 mm (0.5 mm Cu gasket gap to S5.1-01 CF40 necks), Z=-133 mm (Z_canon=367 mm).",
        ),
        scad_params=(
            ("n_viewports", 3),
            ("cf40_od_mm", cf.od_mm),
            ("cf40_pcd_mm", cf.pcd_mm),
            ("cf40_bolts", cf.bolt_count),
            ("clear_aperture_mm", 28.0),
        ),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(scad_feats), step_mesh=step_mesh)


def _build_s4_5_01() -> BuiltPart:
    """S4.5-01: Invar-36 / Zerodur bolted ultra-low-CTE metrology reference bridge w/ carved 0/90/270 deg optical windows."""
    # World origin = (0, 0, -169.0):
    # - Lower continuous ring (R_in=104, R_out=132, h=2.5, 8x M5 @ PCD 236): Z_world [-142.0, -139.5] -> z_loc [+27.0, +29.5]
    # - Mid-height structural arc webs (R=104..132, h=13.0) spanning [10..80], [100..260], [280..350] deg:
    #   Carves 3 explicit wide-open 20-deg (36x13 mm) optical pass-through windows @ 0/90/270 deg, Z_nat=-133.0!
    # - Upper continuous inner structural ring (R=104..119, h=2.5): Z_world [-126.5, -124.0] -> z_loc [+42.5, +45.0]
    #   (clears S4.4-02 vertical periscope relay beams & masts @ R=128.0 mm completely!)
    # - 4x bolted Invar-36 columns @ R=118 (45/135/225/315 deg, r=7.5, h=64.0): z_loc [-37.0, +27.0] (flush!)
    # - 4x column base anchor flanges (r=13.5, h=8.0): z_loc [-45.0, -37.0] (flush!)
    # - 3x interferometer mounting gusset pads beneath ring @ 0/90/270 deg (R in [106, 128], z_loc [+21.0, +27.0], flush!)
    lower_ring = make_ring_with_bolt_circle(
        r_in=104.0, r_out=132.0, thickness=2.5, pcd=236.0, n_bolts=8, bolt_diameter=5.5,
        sub_per_side=4, start_angle_deg=22.5, center=(0.0, 0.0, 28.25),
        name="S4.5-01_invar_lower_ring", material="Invar-36",
    )
    upper_ring = make_tube(
        r_in=104.0, r_out=119.0, height=2.5, segments=48,
        center=(0.0, 0.0, 43.75), name="S4.5-01_invar_upper_ring", material="Invar-36",
    )
    shells: list[SolidMesh] = [lower_ring, upper_ring]
    step_shells: list[SolidMesh] = [
        make_tube(104.0, 132.0, 2.5, segments=28, center=(0.0, 0.0, 28.25), material="Invar-36"),
        make_tube(104.0, 119.0, 2.5, segments=28, center=(0.0, 0.0, 43.75), material="Invar-36"),
    ]
    # 3 curved mid-height structural webs leaving wide-open 20-deg optical windows centered on 0/90/270 deg!
    web_arcs = ((10.0, 80.0), (100.0, 260.0), (280.0, 350.0))
    for w_idx, (d0, d1) in enumerate(web_arcs, start=1):
        web = _make_arc_sector_solid(
            104.0, 132.0, 12.99, d0, d1, arc_steps=max(10, int((d1 - d0) / 8.0)),
            center=(0.0, 0.0, 36.0), name=f"S4.5-01_ring_web_{w_idx}", material="Invar-36",
        )
        shells.append(web)
        step_shells.append(
            _make_arc_sector_solid(104.0, 132.0, 12.99, d0, d1, arc_steps=6, center=(0.0, 0.0, 36.0), material="Invar-36")
        )

    scad_feats = [
        ScadFeature("add_tube", {"od": 264.0, "id": 208.0, "h": 18.0}, translate=(0.0, 0.0, 36.0), comment="Invar-36 / Zerodur metrology reference ring (Ø208/Ø264)"),
        ScadFeature("cut_bolt_circle", {"pcd": 236.0, "bolt_d": 5.5, "count": 8, "h": 22.0}, translate=(0.0, 0.0, 36.0), comment="8x M5 precision bolted ring joints"),
        ScadFeature("cut_slot", {"length": 36.0, "width": 13.0, "h": 36.0}, translate=(118.0, 0.0, 36.0), rotate=(0.0, 90.0, 0.0), comment="0-deg X interferometer optical pass-through bore"),
        ScadFeature("cut_slot", {"length": 36.0, "width": 13.0, "h": 36.0}, translate=(0.0, 118.0, 36.0), rotate=(90.0, 0.0, 0.0), comment="90-deg Y interferometer optical pass-through bore"),
        ScadFeature("cut_slot", {"length": 36.0, "width": 13.0, "h": 36.0}, translate=(0.0, -118.0, 36.0), rotate=(90.0, 0.0, 0.0), comment="270-deg Z interferometer optical pass-through bore"),
    ]

    for idx, ang in enumerate((45.0, 135.0, 225.0, 315.0), start=1):
        rad = math.radians(ang)
        cx, cy = 118.0 * math.cos(rad), 118.0 * math.sin(rad)
        col = make_cylinder(7.5, 63.99, segments=20, center=(cx, cy, -5.0), name=f"met_col_{idx}", material="Invar-36")
        foot = make_cylinder(13.5, 8.0, segments=20, center=(cx, cy, -41.0), name=f"met_foot_{idx}", material="Invar-36")
        shells.extend([col, foot])
        step_shells.append(make_cylinder(7.5, 71.99, segments=12, center=(cx, cy, -9.005), material="Invar-36"))
        scad_feats.append(
            ScadFeature("add_cylinder", {"d": 15.0, "h": 72.0}, translate=(cx, cy, -9.0), comment=f"Invar-36 metrology bridge column #{idx}")
        )

    for idx, ang in enumerate(CF40_VIEWPORT_AZIMUTHS_DEG, start=1):
        rad = math.radians(ang)
        ca, sa = math.cos(rad), math.sin(rad)
        pad = transform_mesh(
            make_box(22.0, 20.0, 5.995, name=f"opt_pad_{idx}", material="Invar-36"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(117.0 * ca, 117.0 * sa, 23.9975),
        )
        shells.append(pad)
        step_shells.append(pad)

    mesh = merge_solids(shells, name="S4.5-01_invar_metrology_bridge", material="Invar-36")
    step_mesh = merge_solids(step_shells, name="S4.5-01_step", material="Invar-36")

    design = make_part_design_from_bom(
        "S4.5-01",
        design_tier="CUSTOM_FULL",
        material="Invar-36",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, -169.0),
        ports=(
            PortInterface(
                name="interf_head_ring",
                kind="optical",
                position_mm=(0.0, 0.0, 36.0),
                normal=(0.0, 0.0, 1.0),
                standard="Ø208/Ø264 Invar-36 Metrology Ring w/ 3x Carved Optical Pass-Through Windows (0/90/270 deg)",
                mating_part_id="S4.4-02",
                bore_mm=208.0,
                od_mm=264.0,
                pcd_mm=236.0,
                bolt_count=8,
                bolt_hole_mm=5.5,
                bolt_spec="M5",
            ),
            PortInterface(
                name="chamber_floor_columns",
                kind="bolt",
                position_mm=(0.0, 0.0, -45.0),
                normal=(0.0, 0.0, -1.0),
                standard="4x Bolted Invar-36 Columns @ R=118 mm (45/135/225/315 deg)",
                mating_part_id="S5.1-01",
            ),
        ),
        dimensions=(
            DimensionCallout("RING_OD", 264.0, 0.02, -0.02, view="top", prefix="Ø"),
            DimensionCallout("RING_ID", 208.0, 0.02, -0.02, view="top", prefix="Ø"),
            DimensionCallout("OPT_WIN_H", 13.0, 0.05, -0.05, view="front"),
            DimensionCallout("RING_H", 18.0, 0.01, -0.01, view="front"),
            DimensionCallout("BRIDGE_TOTAL_H", 90.0, 0.02, -0.02, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.005, datum_primary="", feature_note="METROLOGY RING DATUM A"),
            GDTFrame("parallelism", 0.005, datum_primary="A", feature_note="4-COLUMN FOOT PLANE"),
            GDTFrame("coaxiality", 0.010, diameter_zone=True, datum_primary="B", feature_note="RING BORE Ø208"),
        ),
        notes=(
            "Stress-relieved Invar-36 bolted metrology reference bridge (CTE <= 1.2 ppm/K) with 3 carved 20-deg (36x13 mm) optical pass-through windows @ 0/90/270 deg clearing S4.4-04 -> S4.4-02 interferometer beams & R=128 mm periscopes.",
            "Spans Z=-214..-124 mm, R=104..132 mm (clears B-coils R=82, A-coils R=144, lower S-coils Z>=-112).",
        ),
        scad_params=(
            ("ring_id_mm", 208.0),
            ("ring_od_mm", 264.0),
            ("ring_h_mm", 18.0),
            ("optical_window_deg", 20.0),
            ("optical_window_h_mm", 13.0),
            ("col_radius_mm", 118.0),
            ("n_columns", 4),
        ),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(scad_feats), step_mesh=step_mesh)


def _build_s4_5_02() -> BuiltPart:
    """S4.5-02: Dark-field fiducial alignment microscope objective + CMOS camera on CF40 split-gap viewport."""
    # World origin = (0, 0, +9.0), azimuth = 50.0 deg (NE split-gap optical port, R_face=240.5 mm, Z_canon=509.0 mm)
    # Dark-field optical cone aims along 50.0 deg strictly through the unoccluded Z_canon=[482, 518] mm split gap
    # and S3.1-04 [44..56 deg] optical window directly onto S3.1-01 wafer fiducial ring (R=24.5 mm, Z=0.0 mm)!
    cf = CF_SPECS["CF40"]
    rad = math.radians(FIDUCIAL_PORT_AZIMUTH_DEG)
    ca, sa = math.cos(rad), math.sin(rad)
    r_mid = FIDUCIAL_PORT_FACE_R_MM + 0.5 * cf.thickness_mm  # 246.85 mm

    # 1) Real ISO 3669 CF40 optical viewport (knife-edge facing inward -r)
    vp = make_cf_viewport(
        "CF40",
        clear_aperture=32.0,
        window_diameter=35.0,
        window_thickness=5.0,
        with_knife_edge=True,
        sub_per_side=4,
        axis=(-ca, -sa, 0.0),
        center=(r_mid * ca, r_mid * sa, 0.0),
        name="S4.5-02_cf40_fiducial_vp",
        material="316LN",
        window_material="Fused Silica",
    )
    # 2) Long-working-distance microscope objective barrel + dark-field ring illuminator collar (R=253.5..292.5 mm)
    obj_prof = [
        (0.0, 0.0), (28.0, 0.0), (28.0, 12.0),  # Dark-field LED illuminator ring collar Ø56
        (19.0, 14.0), (19.0, 32.0),              # Objective tube Ø38
        (22.0, 32.0), (22.0, 39.0), (0.0, 39.0), # C-mount adapter flange Ø44
    ]
    r_obj_start = FIDUCIAL_PORT_FACE_R_MM + cf.thickness_mm + 0.3  # 253.5
    objective = make_revolved_profile(
        obj_prof, segments=32, axis=(ca, sa, 0.0),
        center=(r_obj_start * ca, r_obj_start * sa, 0.0),
        name="S4.5-02_darkfield_objective", material="Al 6061",
    )
    # 3) Finned scientific CMOS dark-field camera housing (42 radial x 54 x 54 mm @ R=293.0..335.0)
    r_cam = r_obj_start + 39.5 + 21.0  # 314.0
    cmos = transform_mesh(
        make_chamfered_box(42.0, 54.0, 54.0, chamfer=3.0, name="S4.5-02_cmos_camera", material="Al 6061"),
        rotation_deg=(0.0, 0.0, FIDUCIAL_PORT_AZIMUTH_DEG),
        translation=(r_cam * ca, r_cam * sa, 0.0),
    )

    mesh = merge_solids([vp, objective, cmos], name="S4.5-02_fiducial_microscope_cmos", material="316LN")
    step_mesh = merge_solids(
        [
            make_cylinder(0.5 * cf.od_mm, cf.thickness_mm, segments=20, axis=(-ca, -sa, 0.0), center=(r_mid * ca, r_mid * sa, 0.0), material="316LN"),
            make_cylinder(22.0, 39.0, segments=16, axis=(ca, sa, 0.0), center=((r_obj_start + 19.5) * ca, (r_obj_start + 19.5) * sa, 0.0), material="Al 6061"),
            transform_mesh(make_box(42.0, 54.0, 54.0, material="Al 6061"), rotation_deg=(0.0, 0.0, FIDUCIAL_PORT_AZIMUTH_DEG), translation=(r_cam * ca, r_cam * sa, 0.0)),
        ],
        name="S4.5-02_step",
        material="316LN",
    )

    scad_feats = (
        ScadFeature("add_cf_flange", {"size": "CF40", "blank": False, "bore_id": 32.0}, translate=(r_mid * ca, r_mid * sa, 0.0), rotate=(0.0, -90.0, FIDUCIAL_PORT_AZIMUTH_DEG), comment="ISO 3669 CF40 fiducial microscope split-gap viewport"),
        ScadFeature("add_cylinder", {"d": 44.0, "h": 39.0}, translate=((r_obj_start + 19.5) * ca, (r_obj_start + 19.5) * sa, 0.0), rotate=(0.0, 90.0, FIDUCIAL_PORT_AZIMUTH_DEG), comment="Long-WD objective & dark-field ring illuminator"),
        ScadFeature("add_box", {"dx": 42.0, "dy": 54.0, "dz": 54.0}, translate=(r_cam * ca, r_cam * sa, 0.0), rotate=(0.0, 0.0, FIDUCIAL_PORT_AZIMUTH_DEG), comment="Scientific CMOS dark-field camera head"),
    )
    design = make_part_design_from_bom(
        "S4.5-02",
        design_tier="CUSTOM_FULL",
        material="316LN",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, FIDUCIAL_PORT_Z_MM),
        ports=(
            make_cf_port_interface(
                "CF40",
                name="fiducial_cf40_viewport",
                position_mm=(FIDUCIAL_PORT_FACE_R_MM * ca, FIDUCIAL_PORT_FACE_R_MM * sa, 0.0),
                normal=(-ca, -sa, 0.0),
                mating_part_id="S5.1-01",
                bore_override_mm=32.0,
                notes="Split-gap CF40 optical port (50.0 deg, R_face=240.5 mm, Z=+9.0 mm / Z_canon=509.0 mm) with clear Moller-Trumbore LOS to S3.1-01",
            ),
            PortInterface(
                name="cmos_gige_telemetry",
                kind="electrical",
                position_mm=((r_cam + 21.0) * ca, (r_cam + 21.0) * sa, 0.0),
                normal=(ca, sa, 0.0),
                standard="GigE Vision / CoaXPress CMOS Output",
                mating_part_id="S7.1-01",
            ),
        ),
        dimensions=(
            DimensionCallout("CF40_OD", cf.od_mm, 0.15, -0.15, view="front", prefix="Ø"),
            DimensionCallout("CLEAR_APERTURE", 32.0, 0.10, -0.10, view="front", prefix="Ø"),
            DimensionCallout("CMOS_BODY", 54.0, 0.25, -0.25, view="front"),
            DimensionCallout("ASSEMBLY_LEN", 94.5, 0.5, -0.5, view="top"),
        ),
        gdt_frames=(
            GDTFrame("coaxiality", 0.020, diameter_zone=True, datum_primary="B", feature_note="OBJECTIVE TO CF40 AXIS"),
            GDTFrame("flatness", 0.015, datum_primary="", feature_note="CF40 KNIFE-EDGE FACE"),
        ),
        notes=(
            "Dark-field wafer fiducial alignment microscope objective + CMOS camera (<=1 nm centroiding repeatability).",
            "Mounted at 50.0 deg, R_face=240.5 mm, Z=+9.0 mm (Z_canon=509.0 mm strictly inside Z=[482, 518] mm split gap); clear grazing dark-field LOS onto S3.1-01 wafer fiducial ring through S3.1-04 [44..56 deg] window.",
        ),
        scad_params=(
            ("azimuth_deg", FIDUCIAL_PORT_AZIMUTH_DEG),
            ("z_mount_mm", FIDUCIAL_PORT_Z_MM),
            ("r_face_mm", FIDUCIAL_PORT_FACE_R_MM),
            ("cf40_od_mm", cf.od_mm),
            ("clear_aperture_mm", 32.0),
        ),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=scad_feats,
        step_mesh=step_mesh,
        density_kg_m3=4200.0,  # Composite 316LN CF40 flange + Al objective barrel + CMOS camera
    )


def _build_s4_5_03() -> BuiltPart:
    """S4.5-03: Fast <5 us interferometer-to-deflector real-time DSP compensation card/chassis (1U, Bay 1 U17)."""
    u_start, u_count = 17, 1
    depth_mm = 340.0
    internals = [
        make_box(340.0, 200.0, 2.4, center=(0.0, -10.0, -11.0), name="S4.5-03_rt_dsp_pcb", material="FR4"),
        make_box(68.0, 68.0, 12.0, center=(-40.0, -30.0, -1.0), name="S4.5-03_dsp_fpga_hs", material="Al 6061"),
        make_box(75.0, 90.0, 12.0, center=(90.0, 60.0, -1.0), name="S4.5-03_dac_driver_can", material="Al 6061"),
    ]
    # 3x optical interferometer quadrature Rx ports + 6x differential beam-deflector Tx SMA ports
    fconns = [(-155.0, 0.0, 5.0, 11.0), (-130.0, 0.0, 5.0, 11.0), (-105.0, 0.0, 5.0, 11.0)]
    fconns.extend([(float(x), 0.0, 3.8, 10.0) for x in np.linspace(40.0, 165.0, 6)])
    rconns = [(-100.0, 0.0, 6.0, 12.0), (100.0, 0.0, 6.0, 12.0)]

    mesh, step_mesh, scad_feats = _make_rack_chassis_shell(
        u_count=u_count,
        depth_mm=depth_mm,
        front_connectors=fconns,
        rear_connectors=rconns,
        internal_solids=internals,
        name="S4.5-03_fast_dsp_comp_1u",
        material="Al 6061",
    )
    design = make_part_design_from_bom(
        "S4.5-03",
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
                standard="EIA-310 19-inch 1U (Bay 1 U17, X=1480 mm)",
                mating_part_id="S7.4-03",
            ),
            PortInterface(
                name="interf_quadrature_in",
                kind="optical",
                position_mm=(-130.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="3-Axis He-Ne Interferometer Quadrature Rx (<=0.05 nm)",
                mating_part_id="S4.4-01",
            ),
            PortInterface(
                name="beam_deflector_comp_out",
                kind="electrical",
                position_mm=(100.0, -0.5 * depth_mm, 0.0),
                normal=(0.0, -1.0, 0.0),
                standard="Real-Time <5 us Beam Deflector Offset Correction (±0.1 nm)",
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
            "DESIGN §5.4 real-time <5 us interferometer-to-beam-deflector closed-loop compensation FPGA/DSP unit (±0.1 nm).",
            "Rack Bay 1 (X=+1480 mm, 482.6 mm along X, front -Y), U17 (1U, Master #309 table).",
        ),
        scad_params=(("rack_u_height", 1), ("depth_mm", depth_mm), ("max_latency_us", 5.0)),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=2400.0,
    )


# ---------------------------------------------------------------------------
# Public Subsystem API: build_s4_parts(), export_s4(), export_all()
# ---------------------------------------------------------------------------
_S4_BUILDERS = {
    "S4.1-01": _build_s4_1_01,
    "S4.1-02": _build_s4_1_02,
    "S4.1-03": _build_s4_1_03,
    "S4.2-01": _build_s4_2_01,
    "S4.2-02": _build_s4_2_02,
    "S4.2-03": _build_s4_2_03,
    "S4.3-01": _build_s4_3_01,
    "S4.3-02": _build_s4_3_02,
    "S4.3-03": _build_s4_3_03,
    "S4.3-04": _build_s4_3_04,
    "S4.4-01": _build_s4_4_01,
    "S4.4-02": _build_s4_4_02,
    "S4.4-03": _build_s4_4_03,
    "S4.4-04": _build_s4_4_04,
    "S4.5-01": _build_s4_5_01,
    "S4.5-02": _build_s4_5_02,
    "S4.5-03": _build_s4_5_03,
}


def build_s4_parts() -> dict[str, BuiltPart]:
    """Build all 17 / 17 physical BOM parts of Subsystem S4 (exact part_id keyed)."""
    expected = list_physical_part_ids("S4")
    if set(expected) != set(_S4_BUILDERS):
        raise RuntimeError(
            f"S4 builder mismatch vs BOM: missing={set(expected) - set(_S4_BUILDERS)}, "
            f"extra={set(_S4_BUILDERS) - set(expected)}"
        )
    return {pid: _S4_BUILDERS[pid]() for pid in expected}


def export_s4(out_dir: Path | str | None = None) -> dict[str, PartArtifactResult]:
    """Export all 17 S4 parts (.stl/.step/.dxf/.svg/.scad + per-part .json & S4_manifest.json)."""
    dest = Path(out_dir) if out_dir is not None else DEFAULT_S4_OUT_DIR
    dest.mkdir(parents=True, exist_ok=True)

    parts = build_s4_parts()
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
        from hardware.cad_parts.core import verify_watertight as _vw
        _vr = _vw(bp.mesh)
        part_json = {
            "part_id": pid,
            "subsystem": "S4",
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
            "json_path": f"hardware/cad_parts/out/S4/{pid}.json",
        }

    summary = {
        "subsystem": "S4",
        "part_count": len(results),
        "custom_full_count": sum(1 for r in results.values() if r.design_tier == "CUSTOM_FULL"),
        "cots_env_icd_count": sum(1 for r in results.values() if r.design_tier == "COTS_ENV_ICD"),
        "all_watertight": all(r.watertight for r in results.values()),
        "all_valid": all(r.all_valid for r in results.values()),
        "total_mass_kg": round(total_mass_kg, 4),
        "coordinate_frame": {
            "z_wafer_top_mm": Z_WAFER_TOP_MM,
            "z_floor_mm": Z_FLOOR_MM,
            "dr_clear_bore_r_mm": DR_CLEAR_BORE_R_MM,
            "rack_bay1_x_mm": RACK_BAY1_X_MM,
            "rack_bay1_front_y_mm": RACK_BAY1_FRONT_Y_MM,
            "rack_u_range": "U14-U17",
        },
        "reconciliations": {
            "S4.1-01": parts["S4.1-01"].reconciliation,
        },
        "epistemic": {
            "design_maturity": DESIGN_MATURITY,
            "no_lab_measurement": NO_LAB_MEASUREMENT,
            "iec61508_certified": IEC61508_CERTIFIED,
            "semi_s2_certified": SEMI_S2_CERTIFIED,
        },
        "parts": manifest_parts,
    }
    (dest / "S4_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return results


def export_all(out_dir: Path | str | None = None) -> dict[str, PartArtifactResult]:
    """Export all S4 mechanical CAD artifacts (entry point for subsystem export)."""
    return export_s4(out_dir=out_dir)


if __name__ == "__main__":
    res = export_all()
    tot = sum(r.mass_kg for r in res.values())
    ok = sum(1 for r in res.values() if r.all_valid)
    print(f"S4 export complete: {ok}/{len(res)} valid, total mass = {tot:.3f} kg")
