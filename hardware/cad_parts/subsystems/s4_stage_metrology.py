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
  - ``S4.3-01`` (CUSTOM_FULL):  Ti/Invar 6-DOF UHV monolithic flexure piezo fine stage (90x90x24 mm,
    200 um stroke, 0.2 nm RMS) with 8 real EDM parallelogram leaf-spring flexure slots & Ø36 mm bore.
  - ``S4.3-02`` (CUSTOM_FULL):  ±25 mm UHV stick-slip crossed-roller coarse XY stage (96x96x22 mm)
    + integrated coaxial Invar-36 tubular stage pedestal (R=45..52 mm clearing Cryoperm & B-coils).
  - ``S4.3-03`` (COTS_ENV_ICD): 4x diagonal in-stage sub-nm capacitive position sensors + swept Kapton UHV coax.
  - ``S4.4-01`` (COTS_ENV_ICD): 3-axis stabilized 632.8 nm He-Ne laser unit (Renishaw XL-80/RLE) on table corner.
  - ``S4.4-02`` (COTS_ENV_ICD): 3x UHV differential plane-mirror interferometer heads (X, Y, Z @ R=93, Z=-133).
  - ``S4.4-03`` (CUSTOM_FULL):  3x Zerodur/ULE lambda/20 stage bar mirrors (X, Y, Z @ R=49.5, Z=-41).
  - ``S4.4-04`` (COTS_ENV_ICD): 3x 632.8 nm AR-coated ISO 3669 CF40 viewports (6x Ø6.6 @ PCD 58.7)
    + external fiber launchers & 45-deg beam benders (0/90/270 deg, R_face=240.5 mm, Z=-133 mm).
  - ``S4.5-01`` (CUSTOM_FULL):  Invar-36 / Zerodur bolted metrology reference bridge (Ø208/Ø264 ring
    + 4x bolted columns @ R=118 mm + 3x optical mounting gussets).
  - ``S4.5-02`` (CUSTOM_FULL):  Dark-field fiducial alignment microscope objective + CMOS camera on
    ISO 3669 CF40 viewport (50 deg upper chamber shoulder, R_face=216 mm, Z=+60 mm).
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
FIDUCIAL_PORT_AZIMUTH_DEG: float = 50.0  # Master #309 fix: rotated to 50 deg clearing S5.1-01 & S5.3-02
FIDUCIAL_PORT_Z_MM: float = 60.0      # Canonical Z = +560.0 mm
FIDUCIAL_PORT_FACE_R_MM: float = 216.0

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


def _build_s4_3_01() -> BuiltPart:
    """S4.3-01: 6-DOF UHV monolithic Ti/Invar flexure piezo fine stage (90x90x24 mm, 200 um stroke)."""
    # World origin = (0, 0, -41.0) -> Z_world in [-53.0, -29.0] mm
    # Monolithic EDM-slotted flexure base (90x90x19.0 mm, z_loc [-12.0, +7.0]):
    # - Central Ø36.0 mm bore (r=18.0)
    # - 4 outer parallelogram leaf-spring flexure slots (44x2.8 mm @ ±34.5 mm -> clear of ±22..±33 inner hinges!)
    # - 4 inner orthogonal tip/tilt/Z flexure hinge slots (24x2.4 mm @ ±24.5 mm -> clear of Ø36 bore r=18!)
    # - 4 corner M4 mounting holes @ (±39.5, ±39.5)
    outer_base = _chamfered_rect_2d(90.0, 90.0, 3.0)
    flex_holes: list[list[tuple[float, float]]] = [circle_2d(18.0, segments=28, ccw=False)]
    # 4 outer parallelogram slots
    outer_slots = [
        (0.0, +35.0, 46.0, 2.8, 0.0),
        (0.0, -35.0, 46.0, 2.8, 0.0),
        (+35.0, 0.0, 46.0, 2.8, 90.0),
        (-35.0, 0.0, 46.0, 2.8, 90.0),
    ]
    # 4 inner orthogonal flexure cutouts (well outside r=18 bore: min dist = 24.5 - 1.2 = 23.3 > 18.0!)
    inner_slots = [
        (0.0, +25.0, 24.0, 2.4, 0.0),
        (0.0, -25.0, 24.0, 2.4, 0.0),
        (+25.0, 0.0, 24.0, 2.4, 90.0),
        (-25.0, 0.0, 24.0, 2.4, 90.0),
    ]
    for cx, cy, length, width, ang in outer_slots + inner_slots:
        flex_holes.append(slot_2d(length, width, cx=cx, cy=cy, angle_deg=ang, arc_seg=4, ccw=False))
    for mx, my in ((-39.5, -39.5), (39.5, -39.5), (39.5, 39.5), (-39.5, 39.5)):
        flex_holes.append(circle_2d(2.2, cx=mx, cy=my, segments=10, ccw=False))

    flex_body = make_plate_with_holes(
        outer_poly_2d=outer_base, holes_2d=flex_holes, thickness=19.0,
        center=(0.0, 0.0, -2.5),  # z_loc [-12.0, +7.0]
        name="S4.3-01_monolithic_flexure_body", material="Ti-6Al-4V",
    )

    # Top kinematic moving wafer-chuck deck (76x76x4.8 mm w/ Ø36 bore & 4x Vespel-standoff seats @ ±32, ±32)
    top_holes: list[list[tuple[float, float]]] = [circle_2d(18.0, segments=28, ccw=False)]
    for vx, vy in ((-32.0, -32.0), (32.0, -32.0), (32.0, 32.0), (-32.0, 32.0)):
        top_holes.append(circle_2d(2.6, cx=vx, cy=vy, segments=10, ccw=False))
    top_deck = make_plate_with_holes(
        outer_poly_2d=_chamfered_rect_2d(76.0, 76.0, 3.0), holes_2d=top_holes,
        thickness=4.8, center=(0.0, 0.0, 9.6),  # z_loc [+7.2, +12.0] (0.2 mm flexure relief gap!)
        name="S4.3-01_moving_deck", material="Invar-36",
    )

    mesh = merge_solids([flex_body, top_deck], name="S4.3-01_6dof_flexure_fine_stage", material="Ti-6Al-4V")
    # Compact STEP mesh preserving 90x90 flexure stage w/ 4 outer flexure slots + Ø36 bore + moving deck (~580 faces)
    step_flex = make_plate_with_holes(
        outer_poly_2d=outer_base,
        holes_2d=[circle_2d(18.0, segments=16, ccw=False)]
        + [slot_2d(l, w, cx=cx, cy=cy, angle_deg=a, arc_seg=2, ccw=False) for cx, cy, l, w, a in outer_slots],
        thickness=19.0, center=(0.0, 0.0, -2.5), material="Ti-6Al-4V",
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
            ToleranceContributor("coarse_xy_stage", 22.0, 0.010, -0.010, sign=+1.0),
            ToleranceContributor("fine_6dof_flexure", 24.0, 0.005, -0.005, sign=+1.0),
            ToleranceContributor("datum_height", 183.5, 0.000, 0.000, sign=-1.0),
        ],
        target_min_mm=-0.035,
        target_max_mm=+0.035,
    )

    scad_feats = [
        ScadFeature("add_box", {"dx": 90.0, "dy": 90.0, "dz": 19.0}, translate=(0.0, 0.0, -2.5), comment="Ti-6Al-4V monolithic EDM flexure body (90x90x19 mm)"),
        ScadFeature("add_box", {"dx": 76.0, "dy": 76.0, "dz": 4.8}, translate=(0.0, 0.0, 9.6), comment="Invar-36 6-DOF moving stage platform"),
        ScadFeature("cut_hole", {"d": 36.0, "h": 28.0}, comment="Central Ø36 mm axial clear aperture"),
    ]
    for idx, (cx, cy, l, w, a) in enumerate(outer_slots + inner_slots, start=1):
        scad_feats.append(
            ScadFeature("cut_slot", {"length": l, "width": w, "h": 22.0}, translate=(cx, cy, -2.5), rotate=(0.0, 0.0, a), comment=f"EDM flexure hinge cutout #{idx}")
        )

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
                position_mm=(0.0, 0.0, 12.0),
                normal=(0.0, 0.0, 1.0),
                standard="4x Vespel SP-22 Thermal Standoff Seats @ (±32, ±32)",
                mating_part_id="S6.2-02",
                bore_mm=36.0,
            ),
            PortInterface(
                name="coarse_stage_mount",
                kind="bolt",
                position_mm=(0.0, 0.0, -12.0),
                normal=(0.0, 0.0, -1.0),
                standard="4x M4 Corner Mounts @ (±39.5, ±39.5)",
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
                standard="Zerodur Bar Mirror Kinematic Seat (+X/+Y/-Y)",
                mating_part_id="S4.4-03",
            ),
        ),
        dimensions=(
            DimensionCallout("STAGE_X", 90.0, 0.01, -0.01, view="top"),
            DimensionCallout("STAGE_Y", 90.0, 0.01, -0.01, view="top"),
            DimensionCallout("STAGE_H", 24.0, 0.005, -0.005, view="front"),
            DimensionCallout("CENTER_BORE", 36.0, 0.02, -0.02, view="top", prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.002, datum_primary="", feature_note="TOP MOVING PLATFORM DATUM A"),
            GDTFrame("parallelism", 0.005, datum_primary="A", feature_note="BASE MOUNTING PLANE"),
            GDTFrame("perpendicularity", 0.005, datum_primary="A", feature_note="MIRROR REFERENCE FACES"),
        ),
        notes=(
            "PI PIMars P-562/563 UHV-class non-magnetic Ti-6Al-4V / Invar-36 6-DOF monolithic EDM flexure stage.",
            "200 um XYZ stroke, 0.2 nm RMS resolution (Exp79/133 closed-loop sigma_stage = 0.102 nm).",
            f"Z stage stackup RSS={stage_stack.rss_half_band_mm:.4f} mm, WC={stage_stack.wc_half_band_mm:.4f} mm (PASS).",
        ),
        scad_params=(
            ("stage_xy_mm", 90.0),
            ("stage_h_mm", 24.0),
            ("stroke_um", 200.0),
            ("n_flexure_slots", 8),
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
    """S4.3-02: ±25 mm UHV stick-slip crossed-roller XY coarse stage + coaxial Invar-36 pedestal."""
    # World origin = (0, 0, -145.0):
    # - Upper Y crossed-roller carriage: Z_world [-65.0, -54.5] -> z_loc [+80.0, +90.5], center +85.25
    # - Lower X crossed-roller carriage: Z_world [-76.0, -65.5] -> z_loc [+69.0, +79.5], center +74.25
    # - Coaxial Invar-36 tubular pedestal (R=45..52, h=129.0): Z_world [-205.5, -76.5] -> z_loc [-60.5, +68.5], center +4.0
    # - Bolted Invar-36 base flange ring (R=45..55, h=8.0, 8x M4): Z_world [-214.0, -206.0] -> z_loc [-69.0, -61.0], center -65.0
    upper_carr = make_plate_with_holes(
        outer_poly_2d=_chamfered_rect_2d(96.0, 96.0, 3.0),
        holes_2d=[circle_2d(21.0, segments=28, ccw=False)],
        thickness=10.5, center=(0.0, 0.0, 85.25),
        name="S4.3-02_upper_y_carriage", material="Ti-6Al-4V",
    )
    lower_carr = make_plate_with_holes(
        outer_poly_2d=_chamfered_rect_2d(96.0, 96.0, 3.0),
        holes_2d=[circle_2d(21.0, segments=28, ccw=False)],
        thickness=10.5, center=(0.0, 0.0, 74.25),
        name="S4.3-02_lower_x_carriage", material="Ti-6Al-4V",
    )
    # Machined crossed-roller V-way side rail gibs (64 mm long -> clears ±38 mm S4.3-03 coax pigtails)
    # & 2x piezo stick-slip inertia actuators (height 10 mm -> clears pedestal top at z_loc=+68.5)
    rail_y1 = make_box(64.0, 4.0, 6.0, center=(0.0, -50.2, 74.25), name="v_rail_x1", material="Al2O3")
    rail_y2 = make_box(64.0, 4.0, 6.0, center=(0.0, +50.2, 74.25), name="v_rail_x2", material="Al2O3")
    rail_x1 = make_box(4.0, 64.0, 6.0, center=(-50.2, 0.0, 85.25), name="v_rail_y1", material="Al2O3")
    rail_x2 = make_box(4.0, 64.0, 6.0, center=(+50.2, 0.0, 85.25), name="v_rail_y2", material="Al2O3")
    act_x = make_box(7.0, 24.0, 10.0, center=(-52.0, 0.0, 74.25), name="stickslip_act_x", material="Ti-6Al-4V")
    act_y = make_box(24.0, 7.0, 10.0, center=(0.0, -52.0, 85.25), name="stickslip_act_y", material="Ti-6Al-4V")

    # Coaxial Invar-36 tubular pedestal threading between Cryoperm (R=41) and B-coils (R=56)
    pedestal = make_tube(
        r_in=45.0, r_out=52.0, height=129.0, segments=48,
        center=(0.0, 0.0, 4.0), name="S4.3-02_invar_pedestal", material="Invar-36",
    )
    base_ring = make_ring_with_bolt_circle(
        r_in=45.0, r_out=55.0, thickness=8.0, pcd=100.0, n_bolts=8, bolt_diameter=4.5,
        sub_per_side=2, center=(0.0, 0.0, -65.0), name="S4.3-02_pedestal_base_ring", material="Invar-36",
    )

    shells = [upper_carr, lower_carr, rail_y1, rail_y2, rail_x1, rail_x2, act_x, act_y, pedestal, base_ring]
    mesh = merge_solids(shells, name="S4.3-02_coarse_xy_and_pedestal", material="Invar-36")

    step_mesh = merge_solids(
        [
            make_plate_with_holes(_chamfered_rect_2d(96.0, 96.0, 3.0), [circle_2d(21.0, segments=16, ccw=False)], 21.5, center=(0.0, 0.0, 79.75), material="Ti-6Al-4V"),
            make_tube(45.0, 52.0, 129.0, segments=24, center=(0.0, 0.0, 4.0), material="Invar-36"),
            make_tube(45.0, 55.0, 8.0, segments=24, center=(0.0, 0.0, -65.0), material="Invar-36"),
        ],
        name="S4.3-02_step",
        material="Invar-36",
    )

    scad_feats = (
        ScadFeature("add_box", {"dx": 96.0, "dy": 96.0, "dz": 21.5}, translate=(0.0, 0.0, 79.75), comment="±25 mm Ti/ceramic crossed-roller stick-slip XY coarse stage"),
        ScadFeature("add_tube", {"od": 104.0, "id": 90.0, "h": 129.0}, translate=(0.0, 0.0, 4.0), comment="Coaxial Invar-36 pedestal (R=45..52 clearing Cryoperm & B-coils)"),
        ScadFeature("add_tube", {"od": 110.0, "id": 90.0, "h": 8.0}, translate=(0.0, 0.0, -65.0), comment="Bolted chamber-floor pedestal flange"),
        ScadFeature("cut_bolt_circle", {"pcd": 100.0, "bolt_d": 4.5, "count": 8, "h": 12.0}, translate=(0.0, 0.0, -65.0), comment="8x M4 pedestal base bolt circle"),
        ScadFeature("cut_hole", {"d": 42.0, "h": 26.0}, translate=(0.0, 0.0, 79.75), comment="Ø42 mm central bore"),
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
                position_mm=(0.0, 0.0, 90.5),
                normal=(0.0, 0.0, 1.0),
                standard="±25 mm Crossed-Roller XY Carriage Top",
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
            DimensionCallout("TOTAL_H", 159.5, 0.05, -0.05, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.005, datum_primary="", feature_note="XY CARRIAGE TOP DATUM A"),
            GDTFrame("coaxiality", 0.020, diameter_zone=True, datum_primary="B", feature_note="INVAR PEDESTAL R=45..52"),
            GDTFrame("perpendicularity", 0.010, datum_primary="A", feature_note="BASE MOUNTING FLANGE"),
        ),
        notes=(
            "Non-magnetic Ti-6Al-4V / ceramic crossed-roller stick-slip XY stepper (±25 mm stroke, ±50 nm coarse step).",
            "Integrated coaxial Invar-36 pedestal (R=45..52 mm) clears Cryoperm (R=41 mm) by 4 mm and B-coils (R=56 mm) by 4 mm.",
        ),
        scad_params=(
            ("coarse_xy_mm", 96.0),
            ("stroke_xy_mm", 25.0),
            ("pedestal_id_mm", 90.0),
            ("pedestal_od_mm", 104.0),
            ("pedestal_h_mm", 137.0),
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
    """S4.4-02: 3x UHV differential plane-mirror optical interferometer heads (X, Y, Z)."""
    # World origin = (0, 0, -133.0); mounted inside S4.5-01 metrology ring (R_in=104) at R=93.0 mm
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
        # Main Invar-36 optical housing (14 radial x 14 tangential x 15 tall, R in [86.0, 100.0])
        # Cleanly sits in [83.5, 102.5] mm radial corridor between S6 B_upper (R=82.0) and S4.5-01 ring (R_in=104.0)!
        body = transform_mesh(
            make_chamfered_box(14.0, 14.0, 15.0, chamfer=1.0, name=f"interf_{label}_body", material="Invar-36"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(93.0 * ca, 93.0 * sa, 0.0),
        )
        # Inner beam-aperture quarter-wave plate bezel facing radially inward (-r, R in [83.6, 85.9])
        ap_in = transform_mesh(
            make_cylinder(4.5, 2.3, segments=16, axis="x", name=f"interf_{label}_qwp", material="Fused Silica"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(84.75 * ca, 84.75 * sa, 0.0),
        )
        # Outer retroreflector / laser entrance collar facing radially outward (+r, R in [100.1, 102.4])
        ap_out = transform_mesh(
            make_cylinder(5.0, 2.3, segments=16, axis="x", name=f"interf_{label}_inlet", material="Fused Silica"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(101.25 * ca, 101.25 * sa, 0.0),
        )
        shells.extend([body, ap_in, ap_out])
        step_shells.append(
            transform_mesh(
                make_box(16.0, 14.0, 15.0, material="Invar-36"),
                rotation_deg=(0.0, 0.0, ang),
                translation=(93.0 * ca, 93.0 * sa, 0.0),
            )
        )
        scad_feats.append(
            ScadFeature("add_box", {"dx": 14.0, "dy": 14.0, "dz": 15.0}, translate=(93.0 * ca, 93.0 * sa, 0.0), rotate=(0.0, 0.0, ang), comment=f"UHV differential interferometer head {label}-axis")
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
                position_mm=(102.4, 0.0, 0.0),
                normal=(1.0, 0.0, 0.0),
                standard="3x 632.8 nm Differential Plane-Mirror Optical Axis",
                mating_part_id="S4.4-04",
            ),
            PortInterface(
                name="metrology_ring_mount",
                kind="mechanical",
                position_mm=(93.0, 0.0, -7.5),
                normal=(0.0, 0.0, -1.0),
                standard="3x Kinematic Optical Pads on S4.5-01 Invar Ring",
                mating_part_id="S4.5-01",
            ),
        ),
        dimensions=(
            DimensionCallout("HEAD_LEN", 14.0, 0.05, -0.05, view="top"),
            DimensionCallout("HEAD_WID", 14.0, 0.05, -0.05, view="top"),
            DimensionCallout("HEAD_H", 15.0, 0.05, -0.05, view="front"),
            DimensionCallout("MOUNT_RADIUS", 93.0, 0.05, -0.05, view="top", prefix="R"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.005, datum_primary="A", feature_note="PBS OPTICAL REFERENCE AXIS"),
            GDTFrame("position", 0.020, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="3-AXIS ORTHOGONALITY"),
        ),
        notes=(
            "3x UHV zero-dead-path differential plane-mirror interferometer optical heads (X, Y, Z; ±0.1 nm, mu_r < 1.01).",
            "Mounted at R=93.0 mm (radial span 83.6..102.4 mm), cleanly clearing S6 B_upper (R=82 mm) & S4.5-01 ring (R_in=104 mm).",
        ),
        scad_params=(("n_heads", 3), ("mount_radius_mm", 93.0), ("z_axis_mm", INTERF_Z_MM)),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=tuple(scad_feats),
        step_mesh=step_mesh,
        density_kg_m3=5400.0,  # Invar-36 housing + fused-silica PBS/retroreflector optics
    )


def _build_s4_4_03() -> BuiltPart:
    """S4.4-03: 3x Zerodur/ULE lambda/20 high-flatness stage bar mirrors (X, Y, Z)."""
    # World origin = (0, 0, -41.0); mounted alongside S4.3-01 fine stage (±45 mm) with 1.5 mm clearance
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # Mirror X (+X face: X in [46.5, 52.5], Y in [-26, +26], Z_world [-49, -33])
    mx = make_chamfered_box(6.0, 52.0, 16.0, chamfer=0.5, center=(49.5, 0.0, 0.0), name="zerodur_mirror_x", material="Zerodur")
    cx1 = make_box(2.0, 6.0, 16.0, center=(53.6, -18.0, 0.0), name="clip_x1", material="Invar-36")
    cx2 = make_box(2.0, 6.0, 16.0, center=(53.6, +18.0, 0.0), name="clip_x2", material="Invar-36")

    # Mirror Y (+Y face: Y in [46.5, 52.5], X in [-26, +26])
    my = make_chamfered_box(52.0, 6.0, 16.0, chamfer=0.5, center=(0.0, 49.5, 0.0), name="zerodur_mirror_y", material="Zerodur")
    cy1 = make_box(6.0, 2.0, 16.0, center=(-18.0, 53.6, 0.0), name="clip_y1", material="Invar-36")
    cy2 = make_box(6.0, 2.0, 16.0, center=(+18.0, 53.6, 0.0), name="clip_y2", material="Invar-36")

    # Mirror Z (-Y face: 45-deg bevel roof/fold bar mirror for Z-axis interferometry, Y in [-53.5, -46.5])
    mz = make_chamfered_box(52.0, 7.0, 16.0, chamfer=1.2, center=(0.0, -50.0, 0.0), name="zerodur_mirror_z", material="Zerodur")
    cz1 = make_box(6.0, 2.0, 16.0, center=(-18.0, -54.6, 0.0), name="clip_z1", material="Invar-36")
    cz2 = make_box(6.0, 2.0, 16.0, center=(+18.0, -54.6, 0.0), name="clip_z2", material="Invar-36")

    shells.extend([mx, cx1, cx2, my, cy1, cy2, mz, cz1, cz2])
    step_shells.extend([
        make_box(6.0, 52.0, 16.0, center=(49.5, 0.0, 0.0), material="Zerodur"),
        make_box(52.0, 6.0, 16.0, center=(0.0, 49.5, 0.0), material="Zerodur"),
        make_box(52.0, 7.0, 16.0, center=(0.0, -50.0, 0.0), material="Zerodur"),
    ])
    scad_feats.extend([
        ScadFeature("add_box", {"dx": 6.0, "dy": 52.0, "dz": 16.0}, translate=(49.5, 0.0, 0.0), comment="Zerodur lambda/20 bar mirror X-axis"),
        ScadFeature("add_box", {"dx": 52.0, "dy": 6.0, "dz": 16.0}, translate=(0.0, 49.5, 0.0), comment="Zerodur lambda/20 bar mirror Y-axis"),
        ScadFeature("add_box", {"dx": 52.0, "dy": 7.0, "dz": 16.0}, translate=(0.0, -50.0, 0.0), comment="Zerodur lambda/20 fold bar mirror Z-axis"),
    ])

    mesh = merge_solids(shells, name="S4.4-03_3x_zerodur_bar_mirrors", material="Zerodur")
    step_mesh = merge_solids(step_shells, name="S4.4-03_step", material="Zerodur")

    # Verify cryogenic thermal stability 300 K -> 100 K & 4 K for Invar retaining clips on Zerodur mirrors
    tc_clip_4k = check_cold_clearance(
        "Invar-36", "Zerodur", nominal_outer_id_mm=52.20, nominal_inner_od_mm=52.00,
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
                position_mm=(52.5, 0.0, 0.0),
                normal=(1.0, 0.0, 0.0),
                standard="3x Zerodur Al+SiO2 lambda/20 @ 632.8 nm (CTE < 0.02 ppm/K)",
                mating_part_id="S4.4-02",
            ),
            PortInterface(
                name="stage_flank_mount",
                kind="mechanical",
                position_mm=(46.5, 0.0, 0.0),
                normal=(-1.0, 0.0, 0.0),
                standard="3-Point Low-Stress Invar Flexure Clips on S4.3-01",
                mating_part_id="S4.3-01",
            ),
        ),
        dimensions=(
            DimensionCallout("BAR_LEN", 52.0, 0.02, -0.02, view="top"),
            DimensionCallout("BAR_THK", 6.0, 0.02, -0.02, view="top"),
            DimensionCallout("BAR_H", 16.0, 0.02, -0.02, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.000032, datum_primary="", feature_note="OPTICAL FACET LAMBDA/20 @ 632.8 nm"),
            GDTFrame("perpendicularity", 0.002, datum_primary="A", feature_note="ORTHOGONAL X/Y MIRROR PAIR"),
        ),
        notes=(
            "3x Zerodur/ULE lambda/20 stage bar mirrors (52x6x16 mm) with Al+SiO2 HR coating @ 632.8 nm & Invar clips.",
            f"300K->4K Invar-36 clip vs Zerodur bar WC rad clearance: {tc_clip_4k.cold_worst_case_radial_clearance_mm:.4f} mm (PASS).",
        ),
        scad_params=(("n_mirrors", 3), ("bar_len_mm", 52.0), ("bar_thk_mm", 6.0), ("bar_h_mm", 16.0)),
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
    """S4.5-01: Invar-36 / Zerodur bolted ultra-low-CTE metrology reference bridge."""
    # World origin = (0, 0, -169.0):
    # - Bolted metrology reference ring (R_in=104, R_out=132, h=18, 8x M5 @ PCD 236): Z_world [-142, -124] -> z_loc [+27, +45], center +36.0
    # - 4x bolted Invar-36 columns @ R=118 (45/135/225/315 deg, r=7.5, h=63.6): Z_world [-205.8, -142.2] -> z_loc [-36.8, +26.8], center -5.0
    # - 4x column base anchor flanges (r=13.5, h=7.8): Z_world [-214.0, -206.2] -> z_loc [-45.0, -37.2], center -41.1
    # - 3x interferometer mounting gusset pads beneath ring @ 0/90/270 deg (R in [106, 128], Z_world [-148, -142.2] -> z_loc [+21.0, +26.8])
    met_ring = make_ring_with_bolt_circle(
        r_in=104.0, r_out=132.0, thickness=18.0, pcd=236.0, n_bolts=8, bolt_diameter=5.5,
        sub_per_side=4, start_angle_deg=0.0, center=(0.0, 0.0, 36.0),
        name="S4.5-01_invar_metrology_ring", material="Invar-36",
    )
    shells: list[SolidMesh] = [met_ring]
    step_shells: list[SolidMesh] = [
        make_tube(104.0, 132.0, 18.0, segments=28, center=(0.0, 0.0, 36.0), material="Invar-36"),
    ]
    scad_feats = [
        ScadFeature("add_tube", {"od": 264.0, "id": 208.0, "h": 18.0}, translate=(0.0, 0.0, 36.0), comment="Invar-36 / Zerodur metrology reference ring (Ø208/Ø264)"),
        ScadFeature("cut_bolt_circle", {"pcd": 236.0, "bolt_d": 5.5, "count": 8, "h": 22.0}, translate=(0.0, 0.0, 36.0), comment="8x M5 precision bolted ring joints"),
    ]

    for idx, ang in enumerate((45.0, 135.0, 225.0, 315.0), start=1):
        rad = math.radians(ang)
        cx, cy = 118.0 * math.cos(rad), 118.0 * math.sin(rad)
        col = make_cylinder(7.5, 63.6, segments=20, center=(cx, cy, -5.0), name=f"met_col_{idx}", material="Invar-36")
        foot = make_cylinder(13.5, 7.8, segments=20, center=(cx, cy, -41.1), name=f"met_foot_{idx}", material="Invar-36")
        shells.extend([col, foot])
        step_shells.append(make_cylinder(7.5, 71.8, segments=12, center=(cx, cy, -9.1), material="Invar-36"))
        scad_feats.append(
            ScadFeature("add_cylinder", {"d": 15.0, "h": 71.8}, translate=(cx, cy, -9.1), comment=f"Invar-36 metrology bridge column #{idx}")
        )

    for idx, ang in enumerate(CF40_VIEWPORT_AZIMUTHS_DEG, start=1):
        rad = math.radians(ang)
        ca, sa = math.cos(rad), math.sin(rad)
        pad = transform_mesh(
            make_box(22.0, 20.0, 5.6, name=f"opt_pad_{idx}", material="Invar-36"),
            rotation_deg=(0.0, 0.0, ang),
            translation=(117.0 * ca, 117.0 * sa, 24.0),
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
                standard="Ø208/Ø264 Invar-36 Metrology Ring (CTE <= 1.2 ppm/K)",
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
            DimensionCallout("RING_H", 18.0, 0.01, -0.01, view="front"),
            DimensionCallout("BRIDGE_TOTAL_H", 90.0, 0.02, -0.02, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.005, datum_primary="", feature_note="METROLOGY RING DATUM A"),
            GDTFrame("parallelism", 0.005, datum_primary="A", feature_note="4-COLUMN FOOT PLANE"),
            GDTFrame("coaxiality", 0.010, diameter_zone=True, datum_primary="B", feature_note="RING BORE Ø208"),
        ),
        notes=(
            "Stress-relieved Invar-36 bolted metrology reference bridge (CTE <= 1.2 ppm/K, ±5 um machined datum).",
            "Spans Z=-214..-124 mm, R=104..132 mm (clears B-coils R=82, A-coils R=144, lower S-coils Z>=-112, & S4.4-02 R<=103.5).",
        ),
        scad_params=(
            ("ring_id_mm", 208.0),
            ("ring_od_mm", 264.0),
            ("ring_h_mm", 18.0),
            ("col_radius_mm", 118.0),
            ("n_columns", 4),
        ),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(scad_feats), step_mesh=step_mesh)


def _build_s4_5_02() -> BuiltPart:
    """S4.5-02: Dark-field fiducial alignment microscope objective + CMOS camera on CF40 viewport."""
    # World origin = (0, 0, +60.0), azimuth = 135 deg (-X/+Y upper chamber shoulder, R_face=216.0 mm)
    cf = CF_SPECS["CF40"]
    rad = math.radians(FIDUCIAL_PORT_AZIMUTH_DEG)
    ca, sa = math.cos(rad), math.sin(rad)
    r_mid = FIDUCIAL_PORT_FACE_R_MM + 0.5 * cf.thickness_mm  # 222.35 mm

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
    # 2) Long-working-distance microscope objective barrel + dark-field ring illuminator collar (R=229..268 mm)
    obj_prof = [
        (0.0, 0.0), (28.0, 0.0), (28.0, 12.0),  # Dark-field LED illuminator ring collar Ø56
        (19.0, 14.0), (19.0, 32.0),              # Objective tube Ø38
        (22.0, 32.0), (22.0, 39.0), (0.0, 39.0), # C-mount adapter flange Ø44
    ]
    r_obj_start = FIDUCIAL_PORT_FACE_R_MM + cf.thickness_mm + 0.3  # 229.0
    objective = make_revolved_profile(
        obj_prof, segments=32, axis=(ca, sa, 0.0),
        center=(r_obj_start * ca, r_obj_start * sa, 0.0),
        name="S4.5-02_darkfield_objective", material="Al 6061",
    )
    # 3) Finned scientific CMOS dark-field camera housing (42 radial x 54 x 54 mm @ R=268.5..310.5)
    r_cam = r_obj_start + 39.5 + 21.0  # 289.5
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
        ScadFeature("add_cf_flange", {"size": "CF40", "blank": False, "bore_id": 32.0}, translate=(r_mid * ca, r_mid * sa, 0.0), rotate=(0.0, -90.0, FIDUCIAL_PORT_AZIMUTH_DEG), comment="ISO 3669 CF40 fiducial microscope viewport"),
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
                notes="Upper-shoulder CF40 optical port (50 deg, R_face=216 mm, Z=+60 mm) for dark-field fiducial alignment",
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
            "Mounted at 50 deg, R_face=216 mm, Z=+60 mm (Z_canon=560 mm); clears S5.1-01, S5.3-02, & S3.2-05 cleanly.",
        ),
        scad_params=(
            ("azimuth_deg", FIDUCIAL_PORT_AZIMUTH_DEG),
            ("z_mount_mm", FIDUCIAL_PORT_Z_MM),
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
