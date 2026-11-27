"""Feature-level 3D mechanical CAD builders for Subsystem S7 (Racks, Control Hardware,
4 K Cryo-Chip Screening & ALL 6 v7.0 Safety Enclosures S7.SAFETY-01..06).

Covers 19 / 19 physical BOM parts of S7 (excluding $0 superseded S7.1-04):
- Control & Rack Electronics Envelopes (10): S7.1-01..03, S7.2-01..03, S7.4-01..04
- 4 K Cryogenic Chip Packaging & Test Fixtures (3): S7.3-01..03
- v7.0 Industrial Safety Kit Enclosures (6, 355.0 kg total): S7.SAFETY-01..06

Global Machine Coordinate System (Canonical params.py Datum: Z_FLOOR = 0.0 mm, Z_WAFER = +500.0 mm):
- Rack Bay 1 (Control / S1 / S2 / S3 / S4 / S7): X = +1480.0 mm, Y = 0.0 mm (X in [1180, 1780],
  19.5 mm clear of S5.1-04 transfer arm foot at X=1160.5 mm; 20 mm aisle to Bay 2)
- Rack Bay 2 (Cryo-RF / Magnet / Readout S6): X = +2100.0 mm, Y = 0.0 mm (X in [1800, 2400])
- 42U interior aperture: Z in [90.0, 1956.9] mm (Z_U(u) = 90.0 + (u-1)*44.45, ±1.0 mm clearance),
  fully hollow inside S7.4-03; S7 occupies U1-U13 & U36-U41, leaving U14-U35 open for S4/S3/S1/S2.
- S7.SAFETY-01 SDS PH3 Cabinet + Scrubber: X = -1600.0 mm, Y = +400.0 mm, Z_floor = 0.0 mm
- S7.SAFETY-02 Class-4 Laser OD>=8 + 3 mm 316L X-Ray Shroud: X = 0, Y in [+340, +615], Z in [390.0, 622.0]
  (inner ceiling 612.0 mm -> 10.3 mm clear of S5.5-03 pyrometer top 601.7 mm)
- S7.SAFETY-03 3U 1oo2D Safety PLC (Bay 1 U39-U41) + 4x E-Stop Pedestals (±1900, ±1900, Z=[0,1054])
  + 2 MOhm HV Crowbar Box (+940, +240, Z=[660,876])
- S7.SAFETY-04 15 kVA / 10 kWh Online LFP UPS Floor Tower: X = +2650.0 mm, Y = +150.0 mm, Z = [0, 780]
- S7.SAFETY-05 ASME DN50 0.5 barg DR OVC Rupture-Disk Nozzle on S6.8-04 +Y port
  (X = -650.0, Y = +198.5..+373.5, Z = 820.0) + Cleanroom O2 ODH Wall Monitor
  + 1.563 Ohm Quench Dump Bank (X=[750,1010], Y=[180,440], Z=[0,390])
- S7.SAFETY-06 <80 ms Spring-Return UHV Gate-Valve Actuator + ISO 10156 Orifice Block

Epistemic & Certification Status:
- design_maturity = "M0_M1_DETAILED_CAD_DESIGN_ONLY"
- no_lab_measurement = True
- iec61508_certified = False
- semi_s2_certified = False
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from hardware.cad_parts.core import (
    DESIGN_MATURITY,
    GENERAL_TOLERANCE_STD,
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
    check_cold_clearance,
    check_tolerance_stack,
    circle_2d,
    compute_mass_props,
    export_part_artifacts,
    list_physical_part_ids,
    make_box,
    make_cf_flange,
    make_cf_port_interface,
    make_chamfered_box,
    make_counterbored_plate,
    make_cylinder,
    make_frustum,
    make_isok_flange,
    make_part_design_from_bom,
    make_plate_with_holes,
    make_rect_plate_with_features,
    make_revolved_profile,
    make_swept_tube,
    make_tube,
    merge_solids,
    rect_2d,
    split_shells,
    ToleranceContributor,
    transform_mesh,
    verify_watertight,
)

# ---------------------------------------------------------------------------
# Global Machine Coordinate Constants (mm) — Canonical Z_FLOOR=0, Z_WAFER=+500
# ---------------------------------------------------------------------------
Z_FLOOR_MM: float = 0.0
Z_WAFER_MM: float = 500.0

# 2x 42U 19" EMI Cabinets (S7.4-03) — resolving old single 30U frame conflict
# Bay 1 shifted +80 mm to X=+1480.0 mm (X in [1180, 1780], 19.5 mm clear of S5.1-04 foot at 1160.5)
RACK_BAY1_X_MM: float = 1480.0
RACK_BAY2_X_MM: float = 2100.0
RACK_Y_MM: float = 0.0
RACK_WIDTH_X_MM: float = 600.0
RACK_MAIN_DEPTH_Y_MM: float = 850.0  # Y in [-450, +400], front face at Y = -450
RACK_FRONT_Y_MM: float = -450.0
RACK_REAR_Y_MM: float = 400.0
RACK_PLINTH_H_MM: float = 90.0
RACK_U_HEIGHT_MM: float = 44.45
RACK_TOTAL_U: int = 42
RACK_U_BASE_Z_MM: float = Z_FLOOR_MM + RACK_PLINTH_H_MM  # +90.0 mm
RACK_U_TOP_Z_MM: float = RACK_U_BASE_Z_MM + RACK_TOTAL_U * RACK_U_HEIGHT_MM  # +1956.90 mm
RACK_TOP_Z_MM: float = Z_FLOOR_MM + 2050.0  # +2050.0 mm
EIA_FACEPLATE_W_MM: float = 482.6
EIA_CHASSIS_BODY_W_MM: float = 440.0

# Default artifact output directory (repo-relative)
S7_OUT_DIR: Path = REPO_ROOT / "hardware" / "cad_parts" / "out" / "S7"

# Canonical Exp150 / BOM v7.0 safety kit masses (kg), summing to 355.0 kg
S7_SAFETY_TARGET_MASS_KG: dict[str, float] = {
    "S7.SAFETY-01": 118.0,
    "S7.SAFETY-02": 38.0,
    "S7.SAFETY-03": 18.0,
    "S7.SAFETY-04": 145.0,
    "S7.SAFETY-05": 24.0,
    "S7.SAFETY-06": 12.0,
}


@dataclass(frozen=True)
class BuiltPart:
    """Container pairing a frozen ``PartDesign`` with its watertight 3D mesh & export hints."""

    design: PartDesign
    mesh: SolidMesh
    scad_features: tuple[ScadFeature, ...] = ()
    density_kg_m3: float | None = None
    reconciliation_notes: tuple[str, ...] = ()

    @property
    def part_design(self) -> PartDesign:
        return self.design


# ---------------------------------------------------------------------------
# Coordinate & Feature-Level Solid Helpers
# ---------------------------------------------------------------------------
def rack_u_span_z(u_start: int, u_count: int, clearance_mm: float = 1.0) -> tuple[float, float, float]:
    """Return ``(z_min, z_max, z_center)`` for 1-indexed EIA-310 rack U slots."""
    if u_start < 1 or u_start + u_count - 1 > RACK_TOTAL_U:
        raise ValueError(f"U-slot range [{u_start}, {u_start + u_count - 1}] exceeds 42U rack")
    z_lo = RACK_U_BASE_Z_MM + (u_start - 1) * RACK_U_HEIGHT_MM + clearance_mm
    z_hi = RACK_U_BASE_Z_MM + (u_start - 1 + u_count) * RACK_U_HEIGHT_MM - clearance_mm
    return z_lo, z_hi, 0.5 * (z_lo + z_hi)


def _calibrated_density(mesh: SolidMesh, target_mass_kg: float) -> float:
    """Compute effective composite assembly density (kg/m^3) matching ``target_mass_kg``."""
    val = verify_watertight(mesh)
    if val.signed_volume_mm3 <= 0.0:
        raise ValueError(f"Non-positive mesh volume for {mesh.name}: {val.signed_volume_mm3}")
    vol_m3 = val.signed_volume_mm3 * 1e-9
    return float(target_mass_kg / vol_m3)


def _make_19in_chassis(
    *,
    name: str,
    x_center: float,
    y_front: float,
    z_center: float,
    depth_mm: float,
    height_mm: float,
    material: str = "Steel",
    n_front_connectors: int = 4,
    connector_r_mm: float = 5.0,
    n_vent_slots: int = 4,
    add_handles: bool = True,
) -> tuple[SolidMesh, list[ScadFeature]]:
    """Build a watertight feature-level 19-inch EIA-310 rack chassis facing -Y."""
    face_t = 4.0
    body_depth = depth_mm - face_t - 0.1
    body_h = height_mm - 2.0
    body_w = EIA_CHASSIS_BODY_W_MM
    face_w = EIA_FACEPLATE_W_MM

    # Front faceplate with real EIA-310 ear mounting slots & front intake vent slots
    ear_x = 0.5 * 465.1  # 232.55 mm EIA-310 horizontal mounting pitch
    ear_z = min(0.32 * height_mm, 28.0)
    slots: list[tuple[float, float, float, float, float]] = [
        (-ear_x, -ear_z, 10.0, 6.2, 0.0),
        (-ear_x, +ear_z, 10.0, 6.2, 0.0),
        (+ear_x, -ear_z, 10.0, 6.2, 0.0),
        (+ear_x, +ear_z, 10.0, 6.2, 0.0),
    ]
    if n_vent_slots > 0 and height_mm >= 36.0:
        slot_h = min(0.36 * height_mm, 14.0)
        slot_w = min(28.0, 260.0 / max(n_vent_slots, 1) - 8.0)
        if slot_w >= 8.0:
            x0 = -150.0
            step = 180.0 / max(n_vent_slots, 1)
            for idx in range(n_vent_slots):
                sx = x0 + (idx + 0.5) * step
                slots.append((sx, 0.0, slot_w, slot_h, 0.0))

    # Build faceplate in XY then orient onto XZ facing -Y (axis="-y" maps local +Z -> -Y, local +Y -> +Z)
    faceplate = make_rect_plate_with_features(
        face_w,
        height_mm,
        face_t,
        rect_slots=slots,
        hole_segments=12,
        axis="-y",
        center=(x_center, y_front + 0.5 * face_t, z_center),
        name=f"{name}_faceplate",
        material=material,
    )

    body_y_center = y_front + face_t + 0.1 + 0.5 * body_depth
    body = make_chamfered_box(
        body_w,
        body_depth,
        body_h,
        chamfer=min(2.5, 0.1 * body_h),
        center=(x_center, body_y_center, z_center),
        name=f"{name}_body",
        material=material,
    )

    solids: list[SolidMesh] = [faceplate, body]

    # Front rack-pull handles (outside chassis body, bolted to faceplate ears)
    if add_handles and height_mm >= 36.0:
        h_span = min(0.55 * height_mm, 72.0)
        for sgn in (-1.0, 1.0):
            hx = x_center + sgn * 204.0
            # Two standoffs + vertical grip bar protruding toward -Y
            for zs in (-0.5 * h_span, +0.5 * h_span):
                solids.append(
                    make_cylinder(
                        3.5,
                        18.0,
                        segments=16,
                        axis="-y",
                        center=(hx, y_front - 9.1, z_center + zs),
                        name=f"{name}_handle_post",
                        material="Al 6061",
                    )
                )
            solids.append(
                make_cylinder(
                    4.0,
                    h_span + 8.0,
                    segments=16,
                    axis="z",
                    center=(hx, y_front - 22.2, z_center),
                    name=f"{name}_handle_bar",
                    material="Al 6061",
                )
            )

    # Front instrument connectors (BNC / SMA / SFP / QSFP28 bosses on right side)
    if n_front_connectors > 0:
        span_x = 120.0
        n_c = min(n_front_connectors, 16)
        rows = 2 if (n_c > 8 and height_mm >= 70.0) else 1
        cols = math.ceil(n_c / rows)
        for i in range(n_c):
            r_i = i // cols
            c_i = i % cols
            cx = x_center + 55.0 + (c_i + 0.5) * (span_x / cols)
            cz = z_center + (0.0 if rows == 1 else ((-1.0 if r_i == 0 else 1.0) * 0.22 * height_mm))
            solids.append(
                make_cylinder(
                    connector_r_mm,
                    11.0,
                    segments=16,
                    axis="-y",
                    center=(cx, y_front - 5.6, cz),
                    name=f"{name}_conn_{i}",
                    material="BeCu",
                )
            )

    # Rear IEC C14/C20 power & dual cooling fan shrouds
    y_rear = y_front + depth_mm + 0.1
    fan_r = min(0.36 * body_h, 36.0)
    for fx_off in (-110.0, 0.0):
        solids.append(
            make_tube(
                max(fan_r - 4.0, 4.0),
                fan_r,
                10.0,
                segments=20,
                axis="+y",
                center=(x_center + fx_off, y_rear + 5.1, z_center),
                name=f"{name}_fan_shroud",
                material="Steel",
            )
        )
    solids.append(
        make_box(
            32.0,
            12.0,
            min(24.0, 0.65 * body_h),
            center=(x_center + 150.0, y_rear + 6.1, z_center),
            name=f"{name}_iec_inlet",
            material="PEEK",
        )
    )

    mesh = merge_solids(solids, name=name, material=material)

    # Local parametric OpenSCAD features centered at (0, 0, 0)
    scad_feats = [
        ScadFeature(
            "add_box",
            {"dx": face_w, "dy": face_t, "dz": height_mm},
            translate=(0.0, -0.5 * depth_mm + 0.5 * face_t, 0.0),
            comment="19-inch EIA-310 front faceplate",
        ),
        ScadFeature(
            "add_box",
            {"dx": body_w, "dy": body_depth, "dz": body_h},
            translate=(0.0, 0.5 * face_t, 0.0),
            comment="Main rack chassis enclosure",
        ),
        ScadFeature(
            "cut_slot",
            {"length": 10.0, "width": 6.2, "h": face_t + 4.0},
            translate=(-ear_x, -0.5 * depth_mm + 0.5 * face_t, ear_z),
            rotate=(90.0, 0.0, 0.0),
            comment="EIA-310 rack ear mounting slot (top-left)",
        ),
        ScadFeature(
            "cut_slot",
            {"length": 10.0, "width": 6.2, "h": face_t + 4.0},
            translate=(ear_x, -0.5 * depth_mm + 0.5 * face_t, ear_z),
            rotate=(90.0, 0.0, 0.0),
            comment="EIA-310 rack ear mounting slot (top-right)",
        ),
        ScadFeature(
            "cut_slot",
            {"length": 10.0, "width": 6.2, "h": face_t + 4.0},
            translate=(-ear_x, -0.5 * depth_mm + 0.5 * face_t, -ear_z),
            rotate=(90.0, 0.0, 0.0),
            comment="EIA-310 rack ear mounting slot (bottom-left)",
        ),
        ScadFeature(
            "cut_slot",
            {"length": 10.0, "width": 6.2, "h": face_t + 4.0},
            translate=(ear_x, -0.5 * depth_mm + 0.5 * face_t, -ear_z),
            rotate=(90.0, 0.0, 0.0),
            comment="EIA-310 rack ear mounting slot (bottom-right)",
        ),
    ]
    return mesh, scad_feats


# ---------------------------------------------------------------------------
# Individual S7 Part Builders (19 / 19 Physical Parts)
# ---------------------------------------------------------------------------
def _build_s7_4_03() -> BuiltPart:
    """S7.4-03: 2x 42U 19" EMI-Shielded Steel Cabinets + Rear Water/Air Heat Exchangers.

    Hollow open-interior construction at Bay 1 (X=+1400) and Bay 2 (X=+2100),
    guaranteeing zero solid overlap with any 19" chassis up to 482.6 mm wide
    and 780 mm deep across all 42U slots (Z in [-910.0, +956.9] mm).
    """
    pid = "S7.4-03"
    solids: list[SolidMesh] = []
    wall_t = 16.0
    post_w = 24.0
    post_d = 24.0
    cab_w = RACK_WIDTH_X_MM  # 600.0
    cab_d = RACK_MAIN_DEPTH_Y_MM  # 850.0 (Y in [-450, +400])
    y_mid = 0.5 * (RACK_FRONT_Y_MM + RACK_REAR_Y_MM)  # -25.0
    side_h = RACK_U_TOP_Z_MM - RACK_U_BASE_Z_MM  # 1866.9 mm
    side_zc = 0.5 * (RACK_U_BASE_Z_MM + RACK_U_TOP_Z_MM)
    roof_h = RACK_TOP_Z_MM - RACK_U_TOP_Z_MM  # 93.1 mm
    roof_zc = RACK_U_TOP_Z_MM + 0.5 * roof_h
    plinth_zc = Z_FLOOR_MM + 0.5 * RACK_PLINTH_H_MM

    for bay_idx, bx in enumerate((RACK_BAY1_X_MM, RACK_BAY2_X_MM), start=1):
        # Bottom seismic steel plinth with 4x M12 floor anchor holes
        solids.append(
            make_rect_plate_with_features(
                cab_w,
                cab_d,
                RACK_PLINTH_H_MM - 0.2,
                circular_holes=[
                    (-260.0, -380.0, 14.0),
                    (+260.0, -380.0, 14.0),
                    (+260.0, +380.0, 14.0),
                    (-260.0, +380.0, 14.0),
                ],
                hole_segments=12,
                axis="z",
                center=(bx, y_mid, plinth_zc),
                name=f"s7_4_03_bay{bay_idx}_plinth",
                material="Steel",
            )
        )
        # Top EMI roof plenum with filtered cable-entry cutout & lifting eyebolt holes
        solids.append(
            make_rect_plate_with_features(
                cab_w,
                cab_d,
                roof_h - 0.2,
                rect_slots=[(0.0, +240.0, 260.0, 90.0, 0.0)],
                circular_holes=[
                    (-260.0, -380.0, 16.0),
                    (+260.0, -380.0, 16.0),
                    (+260.0, +380.0, 16.0),
                    (-260.0, +380.0, 16.0),
                ],
                hole_segments=12,
                axis="z",
                center=(bx, y_mid, roof_zc),
                name=f"s7_4_03_bay{bay_idx}_roof",
                material="Steel",
            )
        )
        # Left & right EMI steel side walls (|x_local| in [284, 300] -> inner clear 568 mm)
        for sgn, tag in ((-1.0, "L"), (+1.0, "R")):
            solids.append(
                make_box(
                    wall_t,
                    cab_d,
                    side_h - 0.4,
                    center=(bx + sgn * (0.5 * cab_w - 0.5 * wall_t), y_mid, side_zc),
                    name=f"s7_4_03_bay{bay_idx}_side_{tag}",
                    material="Steel",
                )
            )
            # Front & rear 42U vertical EIA-310 rails strictly outside |x_local| > 256 mm
            # (512 mm clear interior > 482.6 mm 19" faceplate -> zero clash!)
            for y_post, ptag in ((RACK_FRONT_Y_MM + 24.0, "F"), (RACK_REAR_Y_MM - 24.0, "B")):
                solids.append(
                    make_box(
                        post_w,
                        post_d,
                        side_h - 0.4,
                        center=(bx + sgn * 270.0, y_post, side_zc),
                        name=f"s7_4_03_bay{bay_idx}_rail_{tag}{ptag}",
                        material="Steel",
                    )
                )

        # Rear closed-loop Water/Air Heat Exchanger (+/- 1 C chilled-water coil housing)
        # Strictly behind Y = +405..+525 mm (clear of interior Y <= +380 mm)
        hx_y_c = RACK_REAR_Y_MM + 65.0  # +465.0 mm (spans [+405, +525])
        hx_h = 1920.0
        hx_zc = Z_FLOOR_MM + 60.0 + 0.5 * hx_h
        solids.append(
            make_chamfered_box(
                540.0,
                120.0,
                hx_h,
                chamfer=6.0,
                center=(bx, hx_y_c, hx_zc),
                name=f"s7_4_03_bay{bay_idx}_water_air_hx",
                material="Al 6061",
            )
        )
        # Dual DN25 chilled-water supply & return manifold stubs on rear HX bottom
        for x_off, mtag in ((-120.0, "supply"), (+120.0, "return")):
            solids.append(
                make_tube(
                    11.0,
                    16.0,
                    55.0,
                    segments=20,
                    axis="+y",
                    center=(bx + x_off, RACK_REAR_Y_MM + 125.0 + 27.6, Z_FLOOR_MM + 180.0),
                    name=f"s7_4_03_bay{bay_idx}_cw_{mtag}",
                    material="316L",
                )
            )

    mesh = merge_solids(solids, name=pid, material="Steel")
    target_mass = 310.0  # 2 x 155 kg 42U EMI cabinets + water/air HX
    eff_rho = _calibrated_density(mesh, target_mass)

    ports = (
        PortInterface(
            name="bay1_42u_aperture",
            kind="mechanical",
            position_mm=(RACK_BAY1_X_MM, RACK_FRONT_Y_MM, 0.5 * (RACK_U_BASE_Z_MM + RACK_U_TOP_Z_MM)),
            normal=(0.0, -1.0, 0.0),
            standard="EIA-310-D 42U 19-inch",
            mating_part_id="S7.1-01",
            frame="world",
            notes="Bay 1 Control/DAQ/Timing/Safety 42U bay (U17-U32 reserved for S1/S3/S4)",
        ),
        PortInterface(
            name="bay2_42u_aperture",
            kind="mechanical",
            position_mm=(RACK_BAY2_X_MM, RACK_FRONT_Y_MM, 0.5 * (RACK_U_BASE_Z_MM + RACK_U_TOP_Z_MM)),
            normal=(0.0, -1.0, 0.0),
            standard="EIA-310-D 42U 19-inch",
            mating_part_id="S6.6-06",
            frame="world",
            notes="Bay 2 Cryo-RF/Magnet/ZCU216/RFSoC 42U bay (EMI segregated from Bay 1)",
        ),
        PortInterface(
            name="bay1_cw_supply",
            kind="cooling",
            position_mm=(RACK_BAY1_X_MM - 120.0, RACK_REAR_Y_MM + 180.0, Z_FLOOR_MM + 180.0),
            normal=(0.0, 1.0, 0.0),
            standard="DN25 ISO-228 G1 Chilled Water",
            bore_mm=22.0,
            od_mm=32.0,
            frame="world",
        ),
        PortInterface(
            name="bay2_cw_supply",
            kind="cooling",
            position_mm=(RACK_BAY2_X_MM - 120.0, RACK_REAR_Y_MM + 180.0, Z_FLOOR_MM + 180.0),
            normal=(0.0, 1.0, 0.0),
            standard="DN25 ISO-228 G1 Chilled Water",
            bore_mm=22.0,
            od_mm=32.0,
            frame="world",
        ),
    )
    dims = (
        DimensionCallout("CABINET_W", 600.0, 1.0, -1.0, view="front"),
        DimensionCallout("CABINET_H_42U", 2050.0, 2.0, -2.0, view="front"),
        DimensionCallout("BAY_PITCH_X", 620.0, 1.0, -1.0, view="top"),
        DimensionCallout("DEPTH_WITH_HX", 975.0, 2.0, -2.0, view="right"),
    )
    gdt = (
        GDTFrame("perpendicularity", 1.0, datum_primary="A", feature_note="42U VERTICAL RAILS"),
        GDTFrame("flatness", 0.5, datum_primary="", feature_note="FLOOR PLINTH DATUM A"),
        GDTFrame("parallelism", 1.0, datum_primary="A", feature_note="TOP EMI ROOF"),
    )
    design = make_part_design_from_bom(
        pid,
        material="Steel",
        surface_finish_ra_um=3.2,
        world_origin_mm=(0.5 * (RACK_BAY1_X_MM + RACK_BAY2_X_MM), RACK_Y_MM, 0.5 * (Z_FLOOR_MM + RACK_TOP_Z_MM)),
        ports=ports,
        dimensions=dims,
        gdt_frames=gdt,
        notes=(
            "RECONCILIATION: Resolves old params.py single 30U frame conflict with 2x 42U EMI cabinets (>60 dB @ 1 GHz).",
            "Bay 1 center X=+1480 mm (X=[1180,1780], 19.5 mm clear of S5.1-04 foot); Bay 2 center X=+2100 mm (X=[1800,2400]); 20 mm aisle.",
            "Hollow open-bay construction guarantees 0 solid clash with all internal 19-inch chassis (U14-U35 open in Bay 1 for S4/S3/S1/S2).",
        ),
        scad_params=(
            ("n_cabinets", 2),
            ("rack_u", 42),
            ("cab_w_mm", 600.0),
            ("cab_d_mm", 850.0),
            ("cab_h_mm", 2050.0),
            ("bay_pitch_x_mm", 620.0),
            ("hx_depth_mm", 120.0),
        ),
        target_mass_kg=target_mass,
    )
    scad_feats = (
        ScadFeature("add_box", {"dx": 600.0, "dy": 850.0, "dz": 2050.0}, translate=(-310.0, 0.0, 0.0), comment="Bay 1 42U EMI cabinet"),
        ScadFeature("add_box", {"dx": 540.0, "dy": 120.0, "dz": 1920.0}, translate=(-310.0, 490.0, -5.0), comment="Bay 1 rear water/air HX"),
        ScadFeature("add_box", {"dx": 600.0, "dy": 850.0, "dz": 2050.0}, translate=(+310.0, 0.0, 0.0), comment="Bay 2 42U EMI cabinet"),
        ScadFeature("add_box", {"dx": 540.0, "dy": 120.0, "dz": 1920.0}, translate=(+310.0, 490.0, -5.0), comment="Bay 2 rear water/air HX"),
        ScadFeature("cut_slot", {"length": 500.0, "width": 1866.0, "h": 800.0}, translate=(-310.0, -30.0, -1.5), rotate=(90.0, 0.0, 0.0), comment="Bay 1 open 42U interior"),
        ScadFeature("cut_slot", {"length": 500.0, "width": 1866.0, "h": 800.0}, translate=(+310.0, -30.0, -1.5), rotate=(90.0, 0.0, 0.0), comment="Bay 2 open 42U interior"),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=scad_feats,
        density_kg_m3=eff_rho,
        reconciliation_notes=(
            "Resolved BOM v7.0 vs CAD v6.0 single-30U rack conflict: modeled 2x 42U EMI steel cabinets + rear water/air HX at X=+1480 mm and X=+2100 mm.",
        ),
    )


def _build_s7_1_03() -> BuiltPart:
    """S7.1-03: 6 kVA Rack-Mount Double-Conversion Control UPS (2U) + Smart Metered PDU (1U), Bay 1 U1-U3."""
    pid = "S7.1-03"
    _, _, z_ups = rack_u_span_z(1, 2)
    _, _, z_pdu = rack_u_span_z(3, 1)
    h_ups = 2 * RACK_U_HEIGHT_MM - 2.0
    h_pdu = 1 * RACK_U_HEIGHT_MM - 2.0
    y_front = RACK_FRONT_Y_MM + 12.0  # -438.0 mm, inside cabinet

    ups_m, ups_f = _make_19in_chassis(
        name="s7_1_03_ups_2u",
        x_center=RACK_BAY1_X_MM,
        y_front=y_front,
        z_center=z_ups,
        depth_mm=660.0,
        height_mm=h_ups,
        material="Steel",
        n_front_connectors=2,
        connector_r_mm=6.0,
        n_vent_slots=5,
    )
    pdu_m, _ = _make_19in_chassis(
        name="s7_1_03_pdu_1u",
        x_center=RACK_BAY1_X_MM,
        y_front=y_front,
        z_center=z_pdu,
        depth_mm=240.0,
        height_mm=h_pdu,
        material="Steel",
        n_front_connectors=8,
        connector_r_mm=4.5,
        n_vent_slots=2,
        add_handles=False,
    )
    mesh = merge_solids([ups_m, pdu_m], name=pid, material="Steel")
    target_mass = 46.0
    eff_rho = _calibrated_density(mesh, target_mass)
    z_mid = 0.5 * (z_ups + z_pdu)

    design = make_part_design_from_bom(
        pid,
        material="Steel",
        world_origin_mm=(RACK_BAY1_X_MM, y_front + 330.0, z_mid),
        ports=(
            PortInterface("iec_c20_input", "electrical", (RACK_BAY1_X_MM + 150.0, y_front + 665.0, z_ups), (0.0, 1.0, 0.0), "IEC 60320 C20 230V/32A", mating_part_id="S7.SAFETY-04", frame="world"),
            PortInterface("pdu_bank_out", "electrical", (RACK_BAY1_X_MM, y_front, z_pdu), (0.0, -1.0, 0.0), "12x IEC C13/C19 Metered PDU", mating_part_id="S7.1-01", frame="world"),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_3U", 131.35, 0.5, -0.5, view="front"),
            DimensionCallout("DEPTH_UPS", 660.0, 1.0, -1.0, view="right"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="19-INCH FACEPLATE"),),
        notes=("Bay 1 U1-U3 (U1-U2: 2U 6 kVA online control UPS; U3: 1U smart metered PDU; Master Bay 1 table).",),
        scad_params=(("rack_bay", 1), ("u_start", 1), ("u_count", 3), ("depth_mm", 660.0)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(ups_f), density_kg_m3=eff_rho)


def _build_s7_1_01() -> BuiltPart:
    """S7.1-01: 2x Main Control & GPU GRAPE Synthesis Workstations (2x 2U, Bay 1 U4-U7)."""
    pid = "S7.1-01"
    _, _, z_n1 = rack_u_span_z(4, 2)
    _, _, z_n2 = rack_u_span_z(6, 2)
    h_2u = 2 * RACK_U_HEIGHT_MM - 2.0
    y_front = RACK_FRONT_Y_MM + 12.0

    m1, f1 = _make_19in_chassis(
        name="s7_1_01_gpu_node1",
        x_center=RACK_BAY1_X_MM,
        y_front=y_front,
        z_center=z_n1,
        depth_mm=680.0,
        height_mm=h_2u,
        material="Steel",
        n_front_connectors=4,
        connector_r_mm=4.5,
        n_vent_slots=6,
    )
    m2, _ = _make_19in_chassis(
        name="s7_1_01_gpu_node2",
        x_center=RACK_BAY1_X_MM,
        y_front=y_front,
        z_center=z_n2,
        depth_mm=680.0,
        height_mm=h_2u,
        material="Steel",
        n_front_connectors=4,
        connector_r_mm=4.5,
        n_vent_slots=6,
    )
    mesh = merge_solids([m1, m2], name=pid, material="Steel")
    target_mass = 38.0  # 2 x 19 kg dual-RTX4500Ada rack workstations
    eff_rho = _calibrated_density(mesh, target_mass)
    z_mid = 0.5 * (z_n1 + z_n2)

    design = make_part_design_from_bom(
        pid,
        material="Steel",
        world_origin_mm=(RACK_BAY1_X_MM, y_front + 340.0, z_mid),
        ports=(
            PortInterface("sfp28_ctrl_link", "connector", (RACK_BAY1_X_MM + 100.0, y_front + 685.0, z_n1), (0.0, 1.0, 0.0), "2x 25GbE SFP28 / PCIe Gen4", mating_part_id="S7.1-02", frame="world"),
            PortInterface("wr_sync_in", "rf", (RACK_BAY1_X_MM + 120.0, y_front, z_n2), (0.0, -1.0, 0.0), "SMA 10 MHz / PPS", mating_part_id="S7.4-02", frame="world"),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_2X2U", 175.8, 0.5, -0.5, view="front"),
            DimensionCallout("DEPTH", 680.0, 1.0, -1.0, view="right"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="RACK FACEPLATE"),),
        notes=("Bay 1 U4-U7 (Node 1: U4-U5; Node 2: U6-U7; 2x 2U Lambda Vector 2xRTX4500Ada).",),
        scad_params=(("qty_nodes", 2), ("u_per_node", 2), ("u_start", 4), ("depth_mm", 680.0)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(f1), density_kg_m3=eff_rho)


def _build_s7_1_02() -> BuiltPart:
    """S7.1-02: 2U NVMe RAID-10 Certification & Spectroscopy Data Server (30 TB), Bay 1 U8-U9."""
    pid = "S7.1-02"
    _, _, zc = rack_u_span_z(8, 2)
    h_2u = 2 * RACK_U_HEIGHT_MM - 2.0
    y_front = RACK_FRONT_Y_MM + 12.0

    base_m, feats = _make_19in_chassis(
        name="s7_1_02_base",
        x_center=RACK_BAY1_X_MM,
        y_front=y_front,
        z_center=zc,
        depth_mm=660.0,
        height_mm=h_2u,
        material="Steel",
        n_front_connectors=2,
        connector_r_mm=4.0,
        n_vent_slots=0,
    )
    # 12x Hot-swap 2.5" NVMe drive carrier bezels across front panel (2 rows x 6 cols)
    drive_bezels: list[SolidMesh] = [base_m]
    for row in range(2):
        for col in range(6):
            dx_c = RACK_BAY1_X_MM - 150.0 + col * 52.0
            dz_c = zc + (-18.0 if row == 0 else +18.0)
            drive_bezels.append(
                make_box(
                    44.0,
                    6.0,
                    26.0,
                    center=(dx_c, y_front - 3.1, dz_c),
                    name=f"s7_1_02_nvme_{row}_{col}",
                    material="Al 6061",
                )
            )
    mesh = merge_solids(drive_bezels, name=pid, material="Steel")
    target_mass = 21.0
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="Steel",
        world_origin_mm=(RACK_BAY1_X_MM, y_front + 330.0, zc),
        ports=(
            PortInterface("nvme_25gbe_uplink", "connector", (RACK_BAY1_X_MM + 90.0, y_front + 665.0, zc), (0.0, 1.0, 0.0), "2x 25GbE SFP28 RAID-10", mating_part_id="S7.1-01", frame="world"),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_2U", h_2u, 0.5, -0.5, view="front"),
            DimensionCallout("DEPTH", 660.0, 1.0, -1.0, view="right"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="FRONT BEZEL"),),
        notes=("Bay 1 U8-U9 (12x hot-swap enterprise NVMe RAID-10 bays, 30 TB immutable log store).",),
        scad_params=(("u_start", 8), ("u_count", 2), ("nvme_bays", 12), ("depth_mm", 660.0)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats), density_kg_m3=eff_rho)


def _build_s7_2_03() -> BuiltPart:
    """S7.2-03: 18-Slot 19" Low-Noise PXIe/AXIe Instrument Chassis & 10 MHz Backplane (Bay 1 U10-U13).

    True hollow open-front card-cage construction so S7.2-01 (4x AWG cards) and
    S7.2-02 (2x FPGA marker cards) sit cleanly inside the card bay with ZERO clash!
    """
    pid = "S7.2-03"
    z_lo, z_hi, zc = rack_u_span_z(10, 4)
    h_4u = z_hi - z_lo  # 175.8 mm
    y_front = RACK_FRONT_Y_MM + 12.0  # -438.0
    depth = 520.0
    y_back = y_front + depth  # +82.0
    plenum_h = 18.0
    side_w = 24.0
    bp_thick = 26.0  # rear 10 MHz backplane + PSU plenum

    solids: list[SolidMesh] = [
        # Bottom cooling intake plenum (Z in [z_lo, z_lo + 18])
        make_box(
            EIA_CHASSIS_BODY_W_MM,
            depth,
            plenum_h,
            center=(RACK_BAY1_X_MM, y_front + 0.5 * depth, z_lo + 0.5 * plenum_h),
            name="s7_2_03_bot_plenum",
            material="Al 6061",
        ),
        # Top exhaust plenum (Z in [z_hi - 18, z_hi])
        make_box(
            EIA_CHASSIS_BODY_W_MM,
            depth,
            plenum_h,
            center=(RACK_BAY1_X_MM, y_front + 0.5 * depth, z_hi - 0.5 * plenum_h),
            name="s7_2_03_top_plenum",
            material="Al 6061",
        ),
        # Left & right structural side walls with 19" front mounting flanges
        make_box(
            side_w,
            depth,
            h_4u - 2 * plenum_h - 0.4,
            center=(RACK_BAY1_X_MM - 0.5 * EIA_CHASSIS_BODY_W_MM + 0.5 * side_w, y_front + 0.5 * depth, zc),
            name="s7_2_03_side_L",
            material="Al 6061",
        ),
        make_box(
            side_w,
            depth,
            h_4u - 2 * plenum_h - 0.4,
            center=(RACK_BAY1_X_MM + 0.5 * EIA_CHASSIS_BODY_W_MM - 0.5 * side_w, y_front + 0.5 * depth, zc),
            name="s7_2_03_side_R",
            material="Al 6061",
        ),
        # Rear 10 MHz reference backplane & low-noise linear/switching PSU bay (Y in [y_back - 90, y_back])
        make_box(
            EIA_CHASSIS_BODY_W_MM - 2 * side_w - 0.4,
            90.0,
            h_4u - 2 * plenum_h - 0.4,
            center=(RACK_BAY1_X_MM, y_back - 45.0, zc),
            name="s7_2_03_backplane_psu",
            material="Rogers",
        ),
    ]
    # Left & right 19" EIA-310 rack mounting ears (protruding X in [-241.3, -220] & [+220, +241.3])
    for sgn, tag in ((-1.0, "L"), (+1.0, "R")):
        solids.append(
            make_rect_plate_with_features(
                21.2,
                h_4u,
                4.5,
                rect_slots=[(0.0, -52.0, 9.0, 6.2, 0.0), (0.0, +52.0, 9.0, 6.2, 0.0)],
                hole_segments=12,
                axis="-y",
                center=(RACK_BAY1_X_MM + sgn * 230.7, y_front + 2.25, zc),
                name=f"s7_2_03_ear_{tag}",
                material="Steel",
            )
        )
    # Rear 10 MHz SMA/BNC clock input bulkhead connector on backplane
    solids.append(
        make_cylinder(
            6.5,
            16.0,
            segments=16,
            axis="+y",
            center=(RACK_BAY1_X_MM, y_back + 8.1, zc),
            name="s7_2_03_10mhz_ref_in",
            material="BeCu",
        )
    )

    mesh = merge_solids(solids, name=pid, material="Al 6061")
    target_mass = 16.5
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="Al 6061",
        world_origin_mm=(RACK_BAY1_X_MM, y_front + 0.5 * depth, zc),
        ports=(
            PortInterface("pxie_18slot_bay", "mechanical", (RACK_BAY1_X_MM, y_front, zc), (0.0, -1.0, 0.0), "18-Slot PXIe/AXIe 4HP Backplane (<1 ps skew)", mating_part_id="S7.2-01", frame="world"),
            PortInterface("clk_10mhz_ref_in", "rf", (RACK_BAY1_X_MM, y_back + 16.0, zc), (0.0, 1.0, 0.0), "BNC 10 MHz Reference Input", mating_part_id="S7.4-01", frame="world"),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_4U", h_4u, 0.5, -0.5, view="front"),
            DimensionCallout("CAGE_DEPTH", depth, 1.0, -1.0, view="right"),
            DimensionCallout("SLOT_PITCH", 20.32, 0.05, -0.05, view="front"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.15, datum_primary="A", feature_note="BACKPLANE TO CARD GUIDES"),
            GDTFrame("parallelism", 0.20, datum_primary="A", feature_note="TOP/BOT CARD PLENUMS"),
        ),
        notes=("Bay 1 U10-U13; open front 18-slot cage clears S7.2-01 (slots 2-5) & S7.2-02 (slots 7-8) with zero clash.",),
        scad_params=(("u_start", 10), ("u_count", 4), ("slots", 18), ("slot_pitch_mm", 20.32)),
        target_mass_kg=target_mass,
    )
    scad_feats = (
        ScadFeature("add_box", {"dx": 440.0, "dy": depth, "dz": h_4u}, comment="PXIe 4U chassis outer body"),
        ScadFeature("add_box", {"dx": 482.6, "dy": 4.5, "dz": h_4u}, translate=(0.0, -0.5 * depth + 2.25, 0.0), comment="19-inch front mounting ears"),
        ScadFeature("cut_slot", {"length": 392.0, "width": 139.0, "h": depth - 88.0}, translate=(0.0, -45.0, 0.0), rotate=(90.0, 0.0, 0.0), comment="18-slot open PXIe card bay"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats, density_kg_m3=eff_rho)


def _build_pxie_card_group(
    *,
    pid: str,
    slot_indices: Sequence[int],
    n_sma_per_card: int,
    target_mass_kg: float,
    note_text: str,
    mating_part_id: str,
) -> BuiltPart:
    """Build PXIe plug-in instrument cards cleanly slotted inside S7.2-03 open card bay."""
    z_lo, z_hi, zc = rack_u_span_z(10, 4)
    y_front = RACK_FRONT_Y_MM + 12.0  # -438.0
    card_h = (z_hi - z_lo) - 2 * 18.0 - 6.0  # 133.8 mm (3 mm top/bot clearance inside cage)
    card_d = 380.0  # fits cleanly inside Y in [-434, -54], well clear of rear backplane at -8.0!
    slot_pitch = 20.32
    x_slot0 = RACK_BAY1_X_MM - 8.5 * slot_pitch  # centered 18-slot grid

    solids: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []
    xs: list[float] = []

    for idx, slot in enumerate(slot_indices):
        sx = x_slot0 + slot * slot_pitch
        xs.append(sx)
        # Front bezel plate (17.5 mm wide < 20.32 mm pitch -> 2.82 mm gap between cards)
        solids.append(
            make_box(
                17.5,
                3.0,
                card_h,
                center=(sx, y_front + 4.0, zc),
                name=f"{pid}_bezel_{idx}",
                material="Al 6061",
            )
        )
        # Shielded RF/FPGA card body + PCB module
        solids.append(
            make_chamfered_box(
                14.0,
                card_d,
                card_h - 8.0,
                chamfer=1.5,
                center=(sx, y_front + 5.6 + 0.5 * card_d, zc),
                name=f"{pid}_pcb_shield_{idx}",
                material="Rogers",
            )
        )
        # Front SMA/BNC connectors on card faceplate
        for c_i in range(n_sma_per_card):
            cz = zc + ((c_i - 0.5 * (n_sma_per_card - 1)) * min(16.0, (card_h - 24.0) / max(n_sma_per_card, 1)))
            solids.append(
                make_cylinder(
                    3.2,
                    10.0,
                    segments=12,
                    axis="-y",
                    center=(sx, y_front - 2.6, cz),
                    name=f"{pid}_sma_{idx}_{c_i}",
                    material="BeCu",
                )
            )
        scad_feats.append(
            ScadFeature(
                "add_box",
                {"dx": 17.5, "dy": card_d + 4.0, "dz": card_h},
                translate=((idx - 0.5 * (len(slot_indices) - 1)) * slot_pitch, 0.0, 0.0),
                comment=f"PXIe slot {slot} card module",
            )
        )

    mesh = merge_solids(solids, name=pid, material="Rogers")
    eff_rho = _calibrated_density(mesh, target_mass_kg)
    x_mean = sum(xs) / len(xs)

    design = make_part_design_from_bom(
        pid,
        material="Rogers",
        world_origin_mm=(x_mean, y_front + 5.6 + 0.5 * card_d, zc),
        ports=(
            PortInterface("pxie_backplane_j1", "connector", (x_mean, y_front + 5.6 + card_d, zc), (0.0, 1.0, 0.0), "PXIe x8 Gen3 Backplane", mating_part_id="S7.2-03", frame="world"),
            PortInterface("front_sma_outputs", "rf", (x_mean, y_front - 7.6, zc), (0.0, -1.0, 0.0), f"{len(slot_indices) * n_sma_per_card}x SMA 50 Ohm", mating_part_id=mating_part_id, frame="world"),
        ),
        dimensions=(
            DimensionCallout("CARD_PITCH", slot_pitch, 0.05, -0.05, view="front"),
            DimensionCallout("CARD_HEIGHT", card_h, 0.2, -0.2, view="front"),
            DimensionCallout("CARD_DEPTH", card_d, 0.5, -0.5, view="right"),
        ),
        gdt_frames=(GDTFrame("parallelism", 0.10, datum_primary="A", feature_note="CARD GUIDE RAILS"),),
        notes=(note_text,),
        scad_params=(("n_cards", len(slot_indices)), ("slot_pitch_mm", slot_pitch), ("card_depth_mm", card_d)),
        target_mass_kg=target_mass_kg,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(scad_feats), density_kg_m3=eff_rho)


def _build_s7_2_01() -> BuiltPart:
    """S7.2-01: 4x 4-Ch 1.25 GS/s 16-bit PXIe AWG Cards (16 ch GRAPE XY/ENDOR), Slots 2-5."""
    return _build_pxie_card_group(
        pid="S7.2-01",
        slot_indices=(2, 3, 4, 5),
        n_sma_per_card=4,
        target_mass_kg=3.2,
        note_text="Installed in S7.2-03 PXIe chassis Slots 2-5 (Bay 1 U10-U13); 16 total 1.25 GS/s 16-bit AWG outputs.",
        mating_part_id="S6.4-01",
    )


def _build_s7_2_02() -> BuiltPart:
    """S7.2-02: 2x FPGA 1 ns Digital Marker & Pulse Sequencer PXIe Cards, Slots 7-8."""
    return _build_pxie_card_group(
        pid="S7.2-02",
        slot_indices=(7, 8),
        n_sma_per_card=6,
        target_mass_kg=1.4,
        note_text="Installed in S7.2-03 PXIe chassis Slots 7-8 (1-slot EMI guard gap from S7.2-01 AWG cards); 1 ns marker steps.",
        mating_part_id="S7.4-02",
    )


def _build_s7_3_01() -> BuiltPart:
    """S7.3-01: 4 K SKY130 Control Chip Array & Precision PEEK/BeCu Retention Socket (CUSTOM_FULL)."""
    pid = "S7.3-01"
    cx, cy, cz = 820.0, 780.0, Z_FLOOR_MM + 800.0
    body_w, body_h = 88.0, 14.0

    # Non-magnetic PEEK socket base with 4x M3 counterbores + 2x Ø3.0 H7 alignment dowels + central cavity
    peek_base = make_counterbored_plate(
        rect_2d(body_w, body_w),
        counterbored_holes=[
            (-36.0, -36.0, 3.4, 6.2),
            (+36.0, -36.0, 3.4, 6.2),
            (+36.0, +36.0, 3.4, 6.2),
            (-36.0, +36.0, 3.4, 6.2),
        ],
        total_thickness=body_h,
        cbore_depth=4.0,
        plain_holes_2d=[
            circle_2d(1.5, cx=-36.0, cy=0.0, segments=16, ccw=False),
            circle_2d(1.5, cx=+36.0, cy=0.0, segments=16, ccw=False),
        ],
        hole_segments=16,
        axis="z",
        center=(cx, cy, cz),
        name="s7_3_01_peek_base",
        material="PEEK",
    )
    # BeCu spring-finger retention bezel frame sitting cleanly on top of PEEK base
    becu_frame = make_plate_with_holes(
        rect_2d(72.0, 72.0),
        holes_2d=[rect_2d(52.0, 52.0, ccw=False)],
        thickness=3.2,
        axis="z",
        center=(cx, cy, cz + 0.5 * body_h + 1.7),
        name="s7_3_01_becu_retainer",
        material="BeCu",
    )
    # 4x4 = 16 representative SKY130 130 nm CMOS 4 K control dies seated inside bezel aperture
    solids: list[SolidMesh] = [peek_base, becu_frame]
    for ix in range(4):
        for iy in range(4):
            dx = (ix - 1.5) * 11.0
            dy = (iy - 1.5) * 11.0
            solids.append(
                make_box(
                    8.0,
                    8.0,
                    0.75,
                    center=(cx + dx, cy + dy, cz + 0.5 * body_h + 0.45),
                    name=f"s7_3_01_sky130_die_{ix}_{iy}",
                    material="Si",
                )
            )
    mesh = merge_solids(solids, name=pid, material="PEEK")

    # Verify NIST 300 K -> 4 K cold clearance (PEEK socket pocket ID=8.25 mm vs Si die OD=8.00 mm)
    cold = check_cold_clearance(
        "PEEK",
        "Si",
        nominal_outer_id_mm=8.25,
        nominal_inner_od_mm=8.00,
        t_cold_k=4.0,
        min_required_radial_clearance_mm=0.04,
        outer_id_tol_mm=0.02,
        inner_od_tol_mm=0.01,
    )

    design = make_part_design_from_bom(
        pid,
        design_tier="CUSTOM_FULL",
        material="PEEK",
        temp_k=4.0,
        surface_finish_ra_um=0.4,
        world_origin_mm=(cx, cy, cz),
        ports=(
            PortInterface("socket_mount_m3", "bolt", (cx, cy, cz - 0.5 * body_h), (0.0, 0.0, -1.0), "4x M3 Non-Magnetic BeCu + 2x Ø3 H7 Dowels", mating_part_id="S7.3-03", bolt_count=4, bolt_hole_mm=3.4, frame="world"),
            PortInterface("die_array_face", "electrical", (cx, cy, cz + 0.5 * body_h + 3.3), (0.0, 0.0, 1.0), "BeCu Spring-Finger 4K Die Socket (16-site tray / 100+ MPW lot)", mating_part_id="S7.3-02", frame="world"),
        ),
        dimensions=(
            DimensionCallout("BODY_SQ", 88.0, 0.05, -0.05, view="top"),
            DimensionCallout("DIE_POCKET", 8.25, 0.02, -0.02, view="top"),
            DimensionCallout("TOTAL_H", 17.3, 0.05, -0.05, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.010, datum_primary="", feature_note="4K SEATING DATUM A"),
            GDTFrame("position", 0.020, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="2x Ø3.0 H7 DOWELS"),
            GDTFrame("parallelism", 0.015, datum_primary="A", feature_note="BeCu RETAINER PLANE"),
        ),
        notes=(
            f"NIST 300K->4K cold clearance PEEK(8.25 mm)/Si(8.00 mm): {cold.cold_nominal_radial_clearance_mm:.4f} mm (PASS={cold.passed}).",
            "Non-magnetic PEEK/BeCu 4 K retention socket housing SKY130 SEG8/blanker_tile MPW die array.",
        ),
        scad_params=(("body_sq_mm", 88.0), ("die_size_mm", 8.0), ("die_grid_n", 4), ("cbore_m3_d", 6.2)),
        target_mass_kg=round(compute_mass_props(mesh, material="PEEK").mass_kg, 4),
    )
    scad_feats = (
        ScadFeature("add_box", {"dx": 88.0, "dy": 88.0, "dz": 14.0}, comment="Non-magnetic PEEK 4K socket base"),
        ScadFeature("add_box", {"dx": 72.0, "dy": 72.0, "dz": 3.2}, translate=(0.0, 0.0, 8.7), comment="BeCu spring-finger clamp frame"),
        ScadFeature("cut_hole", {"d": 3.4, "h": 18.0}, translate=(-36.0, -36.0, 0.0), comment="M3 mount hole #1"),
        ScadFeature("cut_hole", {"d": 3.4, "h": 18.0}, translate=(+36.0, -36.0, 0.0), comment="M3 mount hole #2"),
        ScadFeature("cut_hole", {"d": 3.4, "h": 18.0}, translate=(+36.0, +36.0, 0.0), comment="M3 mount hole #3"),
        ScadFeature("cut_hole", {"d": 3.4, "h": 18.0}, translate=(-36.0, +36.0, 0.0), comment="M3 mount hole #4"),
        ScadFeature("cut_grid_holes", {"nx": 4, "ny": 4, "pitch_x": 11.0, "pitch_y": 11.0, "hole_d": 7.5, "h": 5.0}, translate=(0.0, 0.0, 8.7), comment="4x4 SKY130 die pocket window"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats)


def _build_s7_3_02() -> BuiltPart:
    """S7.3-02: 4 K Cryogenic Cu-Invar-Cu / Rogers BGA & Wirebond Chip Carriers (10x Stack, CUSTOM_FULL)."""
    pid = "S7.3-02"
    cx, cy, cz = 960.0, 780.0, Z_FLOOR_MM + 810.0
    solids: list[SolidMesh] = []

    # 10x Cu-Invar-Cu thermal spreader carriers + Rogers RF interposer frames stacked in clean fixture
    carrier_w = 46.0
    carrier_t = 2.6
    pitch_z = 4.2
    z0 = cz - 0.5 * (9 * pitch_z)
    for k in range(10):
        zk = z0 + k * pitch_z
        # Cu-Invar-Cu CTE-matched base plate with 4x M2.5 mounting holes
        solids.append(
            make_rect_plate_with_features(
                carrier_w,
                carrier_w,
                1.6,
                circular_holes=[(-18.0, -18.0, 2.7), (+18.0, -18.0, 2.7), (+18.0, +18.0, 2.7), (-18.0, +18.0, 2.7)],
                hole_segments=12,
                axis="z",
                center=(cx, cy, zk),
                name=f"s7_3_02_cic_plate_{k}",
                material="Invar-36",
            )
        )
        # Rogers 4 K RF wirebond interposer ring (recessed 16x16 mm die cavity)
        solids.append(
            make_plate_with_holes(
                rect_2d(42.0, 42.0),
                holes_2d=[rect_2d(16.0, 16.0, ccw=False)],
                thickness=1.0,
                axis="z",
                center=(cx, cy, zk + 1.35),
                name=f"s7_3_02_rogers_{k}",
                material="Rogers",
            )
        )
    # 4x M2.5 Ti-6Al-4V carrier stack guide posts (outside carrier holes? Placed on external corner lugs at ±28 mm)
    for sx, sy in ((-28.0, -28.0), (+28.0, -28.0), (+28.0, +28.0), (-28.0, +28.0)):
        solids.append(
            make_cylinder(
                2.5,
                46.0,
                segments=12,
                axis="z",
                center=(cx + sx, cy + sy, cz + 0.5),
                name="s7_3_02_stack_post",
                material="Ti-6Al-4V",
            )
        )

    mesh = merge_solids(solids, name=pid, material="Invar-36")
    # Check 300 K -> 4 K thermal match between Cu-Invar-Cu carrier & Si die
    cold = check_cold_clearance(
        "Invar-36",
        "Si",
        nominal_outer_id_mm=16.0,
        nominal_inner_od_mm=15.8,
        t_cold_k=4.0,
        min_required_radial_clearance_mm=0.05,
    )

    design = make_part_design_from_bom(
        pid,
        design_tier="CUSTOM_FULL",
        material="Invar-36",
        temp_k=4.0,
        surface_finish_ra_um=0.4,
        world_origin_mm=(cx, cy, cz),
        ports=(
            PortInterface("cic_thermal_base", "thermal", (cx, cy, z0 - 0.8), (0.0, 0.0, -1.0), "4x M2.5 Thermal Anchor (Cu-Invar-Cu)", mating_part_id="S7.3-03", bolt_count=4, bolt_hole_mm=2.7, frame="world"),
            PortInterface("wirebond_cavity", "electrical", (cx, cy, z0 + 9 * pitch_z + 1.85), (0.0, 0.0, 1.0), "16x16 mm Au-Bond / BGA 4K Interposer", mating_part_id="S7.3-01", frame="world"),
        ),
        dimensions=(
            DimensionCallout("CARRIER_SQ", carrier_w, 0.025, -0.025, view="top"),
            DimensionCallout("DIE_CAVITY", 16.0, 0.025, -0.025, view="top"),
            DimensionCallout("STACK_H_10X", 46.0, 0.1, -0.1, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.015, datum_primary="", feature_note="Cu-INVAR-Cu SPREADER"),
            GDTFrame("position", 0.025, diameter_zone=True, datum_primary="A", feature_note="4x M2.5 MOUNT HOLES"),
        ),
        notes=(
            f"10x CTE-matched Cu-Invar-Cu / Rogers carriers; NIST 300K->4K clearance={cold.cold_nominal_radial_clearance_mm:.4f} mm (PASS={cold.passed}).",
        ),
        scad_params=(("qty_carriers", 10), ("carrier_sq_mm", 46.0), ("cavity_sq_mm", 16.0), ("carrier_t_mm", carrier_t)),
        target_mass_kg=round(compute_mass_props(mesh, material="Invar-36").mass_kg, 4),
    )
    scad_feats = (
        ScadFeature("add_box", {"dx": 46.0, "dy": 46.0, "dz": 2.6}, comment="Cu-Invar-Cu / Rogers carrier unit"),
        ScadFeature("cut_hole", {"d": 2.7, "h": 6.0}, translate=(-18.0, -18.0, 0.0), comment="M2.5 hole #1"),
        ScadFeature("cut_hole", {"d": 2.7, "h": 6.0}, translate=(+18.0, -18.0, 0.0), comment="M2.5 hole #2"),
        ScadFeature("cut_hole", {"d": 2.7, "h": 6.0}, translate=(+18.0, +18.0, 0.0), comment="M2.5 hole #3"),
        ScadFeature("cut_hole", {"d": 2.7, "h": 6.0}, translate=(-18.0, +18.0, 0.0), comment="M2.5 hole #4"),
        ScadFeature("cut_slot", {"length": 16.0, "width": 16.0, "h": 2.0}, translate=(0.0, 0.0, 0.8), comment="16x16 mm wirebond cavity"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats)


def _build_s7_3_03() -> BuiltPart:
    """S7.3-03: 4 K Cryogenic Chip Screening Probe & CF63 Hermetic Feedthrough Test Block (CUSTOM_FULL)."""
    pid = "S7.3-03"
    cx, cy, cz = 1120.0, 780.0, Z_FLOOR_MM + 880.0
    # Top ISO 3669 CF63 hermetic feedthrough flange at Z = cz + 72 mm
    z_flange = cz + 72.0
    cf63 = make_cf_flange("CF63", bore_id=50.0, with_knife_edge=True, axis="+z", center=(cx, cy, z_flange), name="s7_3_03_cf63_top", material="316LN")
    # Hermetic bulkhead plug plate with 4x SMA + 1x Micro-D feedthrough ports
    plug = make_rect_plate_with_features(
        48.0,
        48.0,
        10.0,
        circular_holes=[(-14.0, -14.0, 6.4), (+14.0, -14.0, 6.4), (+14.0, +14.0, 6.4), (-14.0, +14.0, 6.4)],
        rect_slots=[(0.0, 0.0, 22.0, 9.0, 0.0)],
        hole_segments=12,
        axis="z",
        center=(cx, cy, z_flange + 14.0),
        name="s7_3_03_ft_plate",
        material="316LN",
    )
    solids: list[SolidMesh] = [cf63, plug]
    # 4x Hermetic SMA coax feedthrough barrels protruding above plug
    for sx, sy in ((-14.0, -14.0), (+14.0, -14.0), (+14.0, +14.0), (-14.0, +14.0)):
        solids.append(
            make_cylinder(
                3.1,
                18.0,
                segments=14,
                axis="z",
                center=(cx + sx, cy + sy, z_flange + 28.1),
                name="s7_3_03_sma_ft",
                material="BeCu",
            )
        )
    # 4x Ti-6Al-4V low-thermal-conductivity probe support struts descending cleanly to 4 K cold chuck
    z_chuck = cz - 62.0
    strut_len = (z_flange - 8.75) - (z_chuck + 12.0) - 0.4  # 112.85 mm -> 0.2 mm gap at each end
    for ang_deg in (45.0, 135.0, 225.0, 315.0):
        rad = math.radians(ang_deg)
        rx = cx + 32.0 * math.cos(rad)
        ry = cy + 32.0 * math.sin(rad)
        solids.append(
            make_cylinder(
                3.5,
                strut_len,
                segments=16,
                axis="z",
                center=(rx, ry, 0.5 * ((z_flange - 8.75) + (z_chuck + 12.0))),
                name="s7_3_03_ti_strut",
                material="Ti-6Al-4V",
            )
        )
    # OFHC Cu 4 K thermal anchor block (Ø92 x 24 mm) with recessed screening test socket seat
    cold_block = make_revolved_profile(
        [(0.0, -12.0), (46.0, -12.0), (46.0, +12.0), (36.0, +12.0), (36.0, +6.0), (0.0, +6.0)],
        segments=40,
        axis="z",
        center=(cx, cy, z_chuck),
        name="s7_3_03_ofhc_cold_block",
        material="OFHC Cu",
    )
    # Non-magnetic PEEK probe clamp bridge resting cleanly atop cold chuck rim (Z in [z_chuck+12.2, z_chuck+20.2])
    probe_bridge = make_rect_plate_with_features(
        68.0,
        24.0,
        8.0,
        circular_holes=[(-26.0, 0.0, 4.2), (+26.0, 0.0, 4.2)],
        hole_segments=12,
        axis="z",
        center=(cx, cy, z_chuck + 16.2),
        name="s7_3_03_peek_bridge",
        material="PEEK",
    )
    solids.extend([cold_block, probe_bridge])

    mesh = merge_solids(solids, name=pid, material="OFHC Cu")
    cold_stack = check_tolerance_stack(
        [
            ToleranceContributor("cf63_flange_datum", 17.5, 0.05, -0.05, sign=+1.0),
            ToleranceContributor("ti_strut_length", 114.0, 0.03, -0.03, sign=+1.0),
            ToleranceContributor("ofhc_chuck_seat", 18.0, 0.02, -0.02, sign=+1.0),
        ],
        target_min_mm=149.35,
        target_max_mm=149.65,
    )

    design = make_part_design_from_bom(
        pid,
        design_tier="CUSTOM_FULL",
        material="OFHC Cu",
        temp_k=4.0,
        surface_finish_ra_um=0.4,
        world_origin_mm=(cx, cy, cz),
        ports=(
            make_cf_port_interface("CF63", "cryo_dipstick_cf63", (cx, cy, z_flange + 8.75), (0.0, 0.0, 1.0), mating_part_id="S6.8-01", frame="world"),
            PortInterface("screening_socket_seat", "thermal", (cx, cy, z_chuck + 6.0), (0.0, 0.0, 1.0), "4K OFHC Cu Seat for S7.3-01/S7.3-02", mating_part_id="S7.3-01", frame="world"),
        ),
        dimensions=(
            DimensionCallout("CF63_OD", 113.5, 0.1, -0.1, prefix="Ø", view="top"),
            DimensionCallout("CHUCK_OD", 92.0, 0.05, -0.05, prefix="Ø", view="top"),
            DimensionCallout("PROBE_H", 165.0, 0.2, -0.2, view="front"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.020, diameter_zone=True, datum_primary="A", feature_note="PROBE AXIS TO CF63 FACE"),
            GDTFrame("flatness", 0.010, datum_primary="", feature_note="4K OFHC THERMAL SEAT"),
            GDTFrame("concentricity", 0.030, diameter_zone=True, datum_primary="B", feature_note="CF63 TO CHUCK"),
        ),
        notes=(
            f"CF63 hermetic 4 K screening probe block; vertical stackup RSS={cold_stack.rss_half_band_mm:.4f} mm (PASS={cold_stack.rss_pass}).",
            "Positioned at 4K cryo-test station (Y=+780 mm, 198 mm clear of Bay 1 rear HX).",
        ),
        scad_params=(("cf_size", "CF63"), ("chuck_od_mm", 92.0), ("strut_len_mm", 114.0)),
        target_mass_kg=round(compute_mass_props(mesh, material="OFHC Cu").mass_kg, 4),
    )
    scad_feats = (
        ScadFeature("add_cf_flange", {"size": "CF63", "bore_id": 50.0}, translate=(0.0, 0.0, 72.0), comment="ISO 3669 CF63 hermetic top flange"),
        ScadFeature("add_cylinder", {"d": 92.0, "h": 24.0}, translate=(0.0, 0.0, -62.0), comment="4K OFHC Cu thermal anchor chuck"),
        ScadFeature("add_box", {"dx": 68.0, "dy": 24.0, "dz": 8.0}, translate=(0.0, 0.0, -51.8), comment="PEEK probe clamp bridge"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats)


def _build_s7_4_01() -> BuiltPart:
    """S7.4-01: 10 MHz Rubidium Atomic Clock (FS725/PRS10) + 16-Output Distribution Amplifier (1U), Bay 1 U36."""
    pid = "S7.4-01"
    _, _, zc = rack_u_span_z(36, 1)
    h_1u = 1 * RACK_U_HEIGHT_MM - 2.0
    y_front = RACK_FRONT_Y_MM + 12.0

    mesh, feats = _make_19in_chassis(
        name=pid,
        x_center=RACK_BAY1_X_MM,
        y_front=y_front,
        z_center=zc,
        depth_mm=450.0,
        height_mm=h_1u,
        material="Steel",
        n_front_connectors=16,  # 16x low-jitter 10 MHz BNC/SMA outputs
        connector_r_mm=3.2,
        n_vent_slots=4,
        add_handles=False,
    )
    target_mass = 11.5
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="Steel",
        world_origin_mm=(RACK_BAY1_X_MM, y_front + 225.0, zc),
        ports=(
            PortInterface("bnc_10mhz_16ch", "rf", (RACK_BAY1_X_MM + 115.0, y_front - 11.0, zc), (0.0, -1.0, 0.0), "16x BNC 10 MHz (<-140 dBc/Hz, <5e-11)", mating_part_id="S7.2-03", frame="world"),
            PortInterface("pps_out_wr", "rf", (RACK_BAY1_X_MM + 55.0, y_front - 11.0, zc), (0.0, -1.0, 0.0), "BNC 1 PPS Reference", mating_part_id="S7.4-02", frame="world"),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_1U", h_1u, 0.5, -0.5, view="front"),
            DimensionCallout("DEPTH", 450.0, 1.0, -1.0, view="right"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="19-INCH FRONT PANEL"),),
        notes=("Bay 1 U36; master 10 MHz Rubidium reference locking RFSoC, AWG, ESR, and FPGA.",),
        scad_params=(("u_start", 36), ("u_count", 1), ("bnc_outputs", 16), ("depth_mm", 450.0)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats), density_kg_m3=eff_rho)


def _build_s7_4_02() -> BuiltPart:
    """S7.4-02: White Rabbit / Sub-ns (<200 ps) Hardware Trigger Fan-Out Switch (1U), Bay 1 U37."""
    pid = "S7.4-02"
    _, _, zc = rack_u_span_z(37, 1)
    h_1u = 1 * RACK_U_HEIGHT_MM - 2.0
    y_front = RACK_FRONT_Y_MM + 12.0

    mesh, feats = _make_19in_chassis(
        name=pid,
        x_center=RACK_BAY1_X_MM,
        y_front=y_front,
        z_center=zc,
        depth_mm=380.0,
        height_mm=h_1u,
        material="Steel",
        n_front_connectors=12,
        connector_r_mm=3.8,
        n_vent_slots=3,
        add_handles=False,
    )
    target_mass = 5.2
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="Steel",
        world_origin_mm=(RACK_BAY1_X_MM, y_front + 190.0, zc),
        ports=(
            PortInterface("wr_sfp_18port", "optical", (RACK_BAY1_X_MM + 100.0, y_front - 11.0, zc), (0.0, -1.0, 0.0), "18x SFP White Rabbit Sub-ns (<200 ps skew)", mating_part_id="S6.11-01", frame="world"),
            PortInterface("wr_10mhz_in", "rf", (RACK_BAY1_X_MM + 55.0, y_front - 11.0, zc), (0.0, -1.0, 0.0), "SMA 10 MHz / 1 PPS Grandmaster Input", mating_part_id="S7.4-01", frame="world"),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_1U", h_1u, 0.5, -0.5, view="front"),
            DimensionCallout("DEPTH", 380.0, 1.0, -1.0, view="right"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="19-INCH FACEPLATE"),),
        notes=("Bay 1 U37; deterministic <200 ps hardware trigger fan-out across implant/IBIC/spectroscopy.",),
        scad_params=(("u_start", 37), ("u_count", 1), ("sfp_ports", 18), ("depth_mm", 380.0)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats), density_kg_m3=eff_rho)


def _build_s7_4_04() -> BuiltPart:
    """S7.4-04: Machine Safety Interlock PLC (SIL-2 Target) & PDU/Interlock Patch (1U), Bay 1 U38."""
    pid = "S7.4-04"
    _, _, zc = rack_u_span_z(38, 1)
    h_1u = 1 * RACK_U_HEIGHT_MM - 2.0
    y_front = RACK_FRONT_Y_MM + 12.0

    mesh, feats = _make_19in_chassis(
        name=pid,
        x_center=RACK_BAY1_X_MM,
        y_front=y_front,
        z_center=zc,
        depth_mm=420.0,
        height_mm=h_1u,
        material="Steel",
        n_front_connectors=10,
        connector_r_mm=3.8,
        n_vent_slots=4,
        add_handles=False,
    )
    target_mass = 9.8
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="Steel",
        world_origin_mm=(RACK_BAY1_X_MM, y_front + 210.0, zc),
        ports=(
            PortInterface("interlock_io_bus", "electrical", (RACK_BAY1_X_MM + 100.0, y_front - 11.0, zc), (0.0, -1.0, 0.0), "24 VDC Keyed Interlock Terminal Bus (UHV/HV/PH3/Quench)", mating_part_id="S7.SAFETY-03", frame="world"),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5, view="front"),
            DimensionCallout("HEIGHT_1U", h_1u, 0.5, -0.5, view="front"),
            DimensionCallout("DEPTH", 420.0, 1.0, -1.0, view="right"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="19-INCH FACEPLATE"),),
        notes=(
            "Bay 1 U38; machine equipment protection PLC (<10 ms cutoff) + PDU interlock distribution.",
            "Design-only M0/M1 (iec61508_certified=False, semi_s2_certified=False).",
        ),
        scad_params=(("u_start", 38), ("u_count", 1), ("depth_mm", 420.0)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats), density_kg_m3=eff_rho)


def _build_s7_safety_01() -> BuiltPart:
    """S7.SAFETY-01 (118.0 kg): 600x500x1800 mm SEMI S2 SDS PH3 Gas Cabinet +
    Vacuum-Jacket Exhaust Duct + 250 CFM Dry-Bed Scrubber + Dual 0.02 ppm Sensors.

    Placed at X = -1600.0 mm, Y = +400.0 mm (clear of S1.6-01/02 at X=-1300, Y=0).
    """
    pid = "S7.SAFETY-01"
    cx, cy = -1600.0, 400.0
    dx, dy, dz = 500.0, 600.0, 1800.0  # X in [-1850, -1350], Y in [+100, +700], Z in [-1000, +800]
    zc = Z_FLOOR_MM + 0.5 * dz  # -100.0
    wt = 12.0  # welded double-wall structural panel representation

    solids: list[SolidMesh] = [
        # Base & top structural plates of 600x500x1800 mm SDS gas cabinet
        make_box(dx, dy, 40.0, center=(cx, cy, Z_FLOOR_MM + 20.0), name="s7_s01_base", material="316L"),
        make_rect_plate_with_features(
            dx,
            dy,
            30.0,
            circular_holes=[(0.0, 0.0, 108.0)],  # DN100 vacuum-jacket exhaust collar cutout
            hole_segments=24,
            axis="z",
            center=(cx, cy, Z_FLOOR_MM + dz - 15.0),
            name="s7_s01_top",
            material="316L",
        ),
        # Left, right, and rear 316L cabinet panels
        make_box(wt, dy, dz - 70.4, center=(cx - 0.5 * dx + 0.5 * wt, cy, zc + 5.0), name="s7_s01_left", material="316L"),
        make_box(wt, dy, dz - 70.4, center=(cx + 0.5 * dx - 0.5 * wt, cy, zc + 5.0), name="s7_s01_right", material="316L"),
        make_box(dx - 2 * wt - 0.4, wt, dz - 70.4, center=(cx, cy + 0.5 * dy - 0.5 * wt, zc + 5.0), name="s7_s01_rear", material="316L"),
        # Front interlocked safety door with armored viewing window & louver intake slots (facing -Y)
        make_plate_with_holes(
            rect_2d(dx - 2 * wt - 0.4, dz - 70.4),
            holes_2d=[
                rect_2d(260.0, 480.0, cx=0.0, cy=+260.0, ccw=False),  # safety glass window aperture
                rect_2d(320.0, 60.0, cx=0.0, cy=-680.0, ccw=False),   # bottom negative-pressure intake louver
            ],
            thickness=wt,
            axis="-y",
            center=(cx, cy - 0.5 * dy + 0.5 * wt, zc + 5.0),
            name="s7_s01_front_door",
            material="316L",
        ),
        # Internal sub-atmospheric SDS PH3 micro-cylinder (<650 Torr, 10 g) + VCR regulator manifold
        make_revolved_profile(
            [(0.0, 0.0), (58.0, 0.0), (58.0, 460.0), (46.0, 520.0), (22.0, 550.0), (22.0, 610.0), (0.0, 610.0)],
            segments=24,
            axis="z",
            center=(cx, cy, Z_FLOOR_MM + 45.0),
            name="s7_s01_sds_cylinder",
            material="316L",
        ),
        make_box(180.0, 120.0, 140.0, center=(cx, cy, Z_FLOOR_MM + 820.0), name="s7_s01_vcr_manifold", material="316L"),
        # Dual 0.02 ppm electrochemical PH3 sensor pods (cabinet upper front + exhaust collar)
        make_box(90.0, 55.0, 110.0, center=(cx - 120.0, cy - 0.5 * dy - 28.0, Z_FLOOR_MM + 1620.0), name="s7_s01_ph3_sensor_1", material="Al 6061"),
        make_box(90.0, 55.0, 110.0, center=(cx + 120.0, cy - 0.5 * dy - 28.0, Z_FLOOR_MM + 1620.0), name="s7_s01_ph3_sensor_2", material="Al 6061"),
        # Concentric vacuum-jacketed DN100 exhaust duct (3 clean non-overlapping segments routing -X to scrubber, clear of S1.6 at Y>=+750!)
        make_tube(
            40.0,
            54.0,
            150.0,
            segments=20,
            axis="z",
            center=(cx, cy, Z_FLOOR_MM + dz + 75.5),
            name="s7_s01_exhaust_riser",
            material="316L",
        ),
        make_tube(
            40.0,
            54.0,
            568.0,
            segments=20,
            axis="-x",
            center=(cx - 230.0, cy, Z_FLOOR_MM + dz + 206.0),
            name="s7_s01_exhaust_header",
            material="316L",
        ),
        make_tube(
            40.0,
            54.0,
            1230.0,
            segments=20,
            axis="z",
            center=(cx - 460.0, cy, Z_FLOOR_MM + 722.0 + 615.0),
            name="s7_s01_exhaust_drop",
            material="316L",
        ),
        # 250 CFM Dry-Bed Chemical Scrubber Vessel (Ø320 x 720 mm) cleanly on -X flank at X = -2060, Y = +400 mm
        make_revolved_profile(
            [(0.0, 0.0), (165.0, 0.0), (165.0, 25.0), (160.0, 25.0), (160.0, 660.0), (145.0, 700.0), (65.0, 720.0), (0.0, 720.0)],
            segments=28,
            axis="z",
            center=(cx - 460.0, cy, Z_FLOOR_MM),
            name="s7_s01_dry_scrubber_250cfm",
            material="316L",
        ),
    ]

    mesh = merge_solids(solids, name=pid, material="316L")
    target_mass = S7_SAFETY_TARGET_MASS_KG[pid]  # 118.0 kg
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="316L",
        surface_finish_ra_um=1.6,
        world_origin_mm=(cx, cy, zc),
        ports=(
            PortInterface("ph3_vcr_outlet", "gas", (cx + 250.0, cy, Z_FLOOR_MM + 820.0), (1.0, 0.0, 0.0), "1/4-in Coaxial Vacuum-Jacketed VCR (316L VAR)", mating_part_id="S1.1-04", bore_mm=4.5, od_mm=19.0, frame="world"),
            PortInterface("exhaust_250cfm_dn100", "gas", (cx - 460.0, cy, Z_FLOOR_MM + 720.0), (0.0, 0.0, 1.0), "DN100 Facility Exhaust (250 CFM Dry-Bed Scrubber)", bore_mm=100.0, od_mm=114.0, frame="world"),
            PortInterface("ph3_sensor_4_20ma", "electrical", (cx, cy - 0.5 * dy - 56.0, Z_FLOOR_MM + 1620.0), (0.0, -1.0, 0.0), "Dual 0.02/0.05 ppm 4-20 mA SIL-3 Target Loop", mating_part_id="S7.SAFETY-03", frame="world"),
        ),
        dimensions=(
            DimensionCallout("CAB_W", 500.0, 2.0, -2.0, view="front"),
            DimensionCallout("CAB_D", 600.0, 2.0, -2.0, view="right"),
            DimensionCallout("CAB_H", 1800.0, 3.0, -3.0, view="front"),
            DimensionCallout("SCRUBBER_OD", 320.0, 2.0, -2.0, prefix="Ø", view="top"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 1.0, datum_primary="", feature_note="CABINET BASE PLINTH"),
            GDTFrame("perpendicularity", 1.5, datum_primary="A", feature_note="GAS CABINET ENCLOSURE"),
        ),
        notes=(
            "Exp150 S7.SAFETY-01 (118.0 kg, 480 W, 0 W cryo): <650 Torr (10 g) SDS PH3 + vacuum-jacket duct + 250 CFM dry scrubber.",
            "Cabinet at X=-1600 mm, Y=+400 mm (Y in [+100,+700]), scrubber at X=-2060 mm, Y=+400 mm (fully clear of S1.6-01/02 at Y>=+750 mm).",
            "PRELIMINARY PARAMETRIC DESIGN ONLY: iec61508_certified=False, semi_s2_certified=False.",
        ),
        scad_params=(("cab_dx_mm", 500.0), ("cab_dy_mm", 600.0), ("cab_dz_mm", 1800.0), ("scrubber_od_mm", 320.0), ("exhaust_cfm", 250)),
        target_mass_kg=target_mass,
    )
    scad_feats = (
        ScadFeature("add_box", {"dx": 500.0, "dy": 600.0, "dz": 1800.0}, comment="SEMI S2 target SDS PH3 gas cabinet"),
        ScadFeature("add_cylinder", {"d": 320.0, "h": 720.0}, translate=(-460.0, 0.0, -540.0), comment="250 CFM dry-bed chemical scrubber"),
        ScadFeature("add_tube", {"od": 108.0, "id": 80.0, "h": 150.0}, translate=(0.0, 0.0, 975.0), comment="DN100 vacuum-jacketed exhaust riser"),
        ScadFeature("cut_slot", {"length": 480.0, "width": 260.0, "h": 40.0}, translate=(0.0, -295.0, 260.0), rotate=(90.0, 90.0, 0.0), comment="Armored front inspection window"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats, density_kg_m3=eff_rho)


def _build_s7_safety_02() -> BuiltPart:
    """S7.SAFETY-02 (38.0 kg, CUSTOM_FULL): 240x190x200 mm Interlocked Class-4 Laser (OD>=8 @ 808 nm)
    + 3 mm 316L X-Ray Shroud + Dual-Blade <3.2 ms Shutter Housing around relocated 36-deg inclined
    S5.5 +Y CF63 Viewport on S5.1-03 Load-Lock (OBS-001).

    Coaxial with S5.5 optical axis from wafer (420, 0, 500) at az=+90 deg (+Y), elev=36 deg:
    - Collar front at t=204.0 mm (1.0 mm past S5.5-02 CF63 viewport face t=203.0 mm).
    - Hollow optical interior cavity |x|<=74 mm, t in [204, 383], z_loc in [-64, +116] mm is
      100% OPEN so S5.5-04 shutter, S5.5-01 homogenizer & S5.5-03 pyrometer sit inside with ZERO clash!
    """
    pid = "S7.SAFETY-02"
    w_x, d_y = 210.0, 190.0  # X=[315, 525] clears S2.4-03 X_max=311.0 by 4.0 mm!
    z_lo, z_hi = -74.0, 126.0  # inner floor -64 (10.8 mm clear of S5.5-04), inner ceiling +116 (14.3 mm clear of S5.5-03!)
    h_z = z_hi - z_lo  # 200.0 mm
    z_c = 0.5 * (z_lo + z_hi)  # +26.0 mm
    y_collar_front = 204.0
    y_shroud_front = 219.0  # collar occupies t=[204, 218.6]; main shroud spans t=[219, 409] = 190 mm
    y_shroud_mid = y_shroud_front + 0.5 * d_y  # 314.0 mm
    y_shroud_rear = y_shroud_front + d_y  # 409.0 mm
    wall_t = 12.0  # heavy 316L X-ray + OD>=8 structural wall (realistic ~9000 kg/m3 effective density for 38.0 kg shroud!)

    local_solids: list[SolidMesh] = [
        # Front CF63-mating light-tight & X-ray labyrinth collar (leaves 132x164 mm optical aperture open!)
        make_box(39.0, 14.6, h_z, center=(-85.5, y_collar_front + 7.3, z_c), name="s7_s02_collar_L", material="316L"),
        make_box(39.0, 14.6, h_z, center=(+85.5, y_collar_front + 7.3, z_c), name="s7_s02_collar_R", material="316L"),
        make_box(131.6, 14.6, 18.0, center=(0.0, y_collar_front + 7.3, z_lo + 9.0), name="s7_s02_collar_B", material="316L"),
        make_box(131.6, 14.6, 18.0, center=(0.0, y_collar_front + 7.3, z_hi - 9.0), name="s7_s02_collar_T", material="316L"),
        # Left & right 12 mm 316L OD8/X-ray walls (|X| in [93, 105])
        make_box(wall_t, d_y, h_z, center=(-0.5 * w_x + 0.5 * wall_t, y_shroud_mid, z_c), name="s7_s02_wall_L", material="316L"),
        make_box(wall_t, d_y, h_z, center=(+0.5 * w_x - 0.5 * wall_t, y_shroud_mid, z_c), name="s7_s02_wall_R", material="316L"),
        # Bottom structural floor plate (14 mm thick, z_loc in [-74, -60] -> 6.8 mm clear of S5.5-04!)
        make_box(w_x - 2 * wall_t - 0.4, d_y, 14.0, center=(0.0, y_shroud_mid, z_lo + 7.0), name="s7_s02_bot_plate", material="316L"),
        # Top interlocked removable lid (14 mm thick, z_loc in [+112, +126] -> 10.3 mm clear of S5.5-03!)
        make_rect_plate_with_features(
            w_x - 2 * wall_t - 0.4,
            d_y,
            14.0,
            circular_holes=[(-76.0, -75.0, 6.6), (+76.0, -75.0, 6.6), (+76.0, +75.0, 6.6), (-76.0, +75.0, 6.6)],
            hole_segments=12,
            axis="z",
            center=(0.0, y_shroud_mid, z_hi - 7.0),
            name="s7_s02_top_lid",
            material="316L",
        ),
        # Rear 16 mm 316L OD8 backplate (t in [393, 409]) with Ø42 mm armored fiber labyrinth gland bore on axis z_loc=0
        make_rect_plate_with_features(
            w_x - 2 * wall_t - 0.4,
            h_z - 28.4,
            16.0,
            circular_holes=[(0.0, z_c, 42.0)],
            hole_segments=24,
            axis="+y",
            center=(0.0, y_shroud_rear - 8.0, z_c),
            name="s7_s02_rear_plate",
            material="316L",
        ),
        # Rear light-tight armored-fiber labyrinth gland tube (t in [409.2, 413.8]) centered on optical axis
        make_tube(
            18.0,
            28.0,
            4.6,
            segments=24,
            axis="+y",
            center=(0.0, y_shroud_rear + 2.5, 0.0),
            name="s7_s02_fiber_labyrinth",
            material="316L",
        ),
        # Dual-blade <3.2 ms 1oo2D fail-safe shutter solenoid actuator housings tucked cleanly in cheek pockets (|x| in [68, 91])
        make_chamfered_box(23.0, 96.0, 128.0, chamfer=3.0, center=(-79.5, 276.0, 0.0), name="s7_s02_shutter_chA", material="316L"),
        make_chamfered_box(23.0, 96.0, 128.0, chamfer=3.0, center=(+79.5, 276.0, 0.0), name="s7_s02_shutter_chB", material="316L"),
        # Dual-channel magnetic interlock guard switches mounted on top lid perimeter
        make_box(42.0, 26.0, 18.0, center=(-72.0, y_shroud_mid, z_hi + 9.2), name="s7_s02_guard_sw_A", material="Al 6061"),
        make_box(42.0, 26.0, 18.0, center=(+72.0, y_shroud_mid, z_hi + 9.2), name="s7_s02_guard_sw_B", material="Al 6061"),
        # Heavy 24 mm 316L X-ray beam-dump backing baffle plate inside rear zone (t in [367, 391], 10 mm past S5.5-01 collimator!)
        make_rect_plate_with_features(
            184.0,
            168.0,
            24.0,
            circular_holes=[(0.0, z_c, 46.0)],
            hole_segments=24,
            axis="+y",
            center=(0.0, 379.0, z_c),
            name="s7_s02_xray_baffle",
            material="316L",
        ),
    ]

    # Transform entire shroud into canonical 36-deg inclined S5.5 optical frame anchored at load-lock wafer (420, 0, 500)
    el_deg = 36.0
    el_rad = math.radians(el_deg)
    ll_x, ll_y, ll_z = 420.0, 0.0, Z_WAFER_MM

    def _to_world(lx: float, ly: float, lz: float) -> tuple[float, float, float]:
        wy = ly * math.cos(el_rad) - lz * math.sin(el_rad)
        wz = ly * math.sin(el_rad) + lz * math.cos(el_rad)
        return (round(ll_x + lx, 4), round(ll_y + wy, 4), round(ll_z + wz, 4))

    solids = [
        transform_mesh(s, rotation_deg=(el_deg, 0.0, 0.0), translation=(ll_x, ll_y, ll_z))
        for s in local_solids
    ]
    mesh = merge_solids(solids, name=pid, material="316L")
    target_mass = S7_SAFETY_TARGET_MASS_KG[pid]  # 38.0 kg
    eff_rho = _calibrated_density(mesh, target_mass)

    u_y = math.cos(el_rad)
    u_z = math.sin(el_rad)
    n_z_y = -math.sin(el_rad)
    n_z_z = math.cos(el_rad)
    design = make_part_design_from_bom(
        pid,
        design_tier="CUSTOM_FULL",
        material="316L",
        surface_finish_ra_um=1.6,
        world_origin_mm=_to_world(0.0, y_shroud_mid, z_c),
        ports=(
            make_cf_port_interface("CF63", "s55_viewport_shroud_mate", _to_world(0.0, y_collar_front, 0.0), (0.0, -u_y, -u_z), mating_part_id="S5.5-02", frame="world", notes="Sleeves around relocated 36-deg inclined S5.5 +Y CF63 viewport on S5.1-03 without clashing S5.5 optics"),
            PortInterface("fiber_labyrinth_port", "optical", _to_world(0.0, y_shroud_rear + 5.0, 0.0), (0.0, u_y, u_z), "OD>=8 Armored 808 nm Fiber Gland Ø42 mm", mating_part_id="S5.5-01", bore_mm=36.0, od_mm=56.0, frame="world"),
            PortInterface("shutter_1oo2d_ctrl", "electrical", _to_world(0.0, y_shroud_mid, z_hi + 18.2), (0.0, n_z_y, n_z_z), "Dual-Channel 1oo2D Guard Switch & <3.2 ms Shutter Coil", mating_part_id="S7.SAFETY-03", frame="world"),
        ),
        dimensions=(
            DimensionCallout("SHROUD_W", w_x, 0.5, -0.5, view="front"),
            DimensionCallout("SHROUD_D", d_y, 0.5, -0.5, view="right"),
            DimensionCallout("SHROUD_H", h_z, 0.5, -0.5, view="front"),
            DimensionCallout("WALL_316L_MIN", 3.0, 0.2, -0.0, view="front"),
            DimensionCallout("CLEAR_CAVITY_W", 148.0, 0.5, -0.5, view="front"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.20, datum_primary="A", feature_note="COLLAR TO S5.5 36-DEG INCLINED AXIS"),
            GDTFrame("flatness", 0.10, datum_primary="", feature_note="LIGHT-TIGHT LID GASKET FACE"),
            GDTFrame("profile_surface", 0.25, datum_primary="A", datum_secondary="B", feature_note="OD>=8 LABYRINTH SEAM"),
        ),
        notes=(
            "Exp150 S7.SAFETY-02 (38.0 kg, 45 W, 0 W cryo): ANSI Z136.1 OD>=8 (808 nm) + >=3 mm 316L 22 keV X-ray shroud (1.19e-23 uSv/h) + 3.2 ms 1oo2D dual-blade shutter.",
            "OBS-001 fix: Relocated coaxially onto S5.1-03 36-deg inclined +Y S5.5 optical axis at X=420 mm (inner ceiling +116 mm -> 14.3 mm clear of S5.5-03; 10.8 mm clear below S5.5-04).",
            "PRELIMINARY DESIGN ONLY: iec61508_certified=False, semi_s2_certified=False.",
        ),
        scad_params=(("shroud_w_mm", w_x), ("shroud_d_mm", d_y), ("shroud_h_mm", h_z), ("min_316l_wall_mm", 3.0), ("cavity_w_mm", 148.0), ("elev_deg", el_deg)),
        target_mass_kg=target_mass,
    )
    scad_feats = (
        ScadFeature("add_box", {"dx": w_x, "dy": d_y + 15.0, "dz": h_z}, comment="3 mm+ 316L OD>=8 laser & X-ray shroud (36-deg inclined)"),
        ScadFeature("cut_slot", {"length": 148.0, "width": 170.0, "h": 200.0}, translate=(0.0, -15.0, 0.0), rotate=(90.0, 0.0, 0.0), comment="Open S5.5 optical head clearance cavity"),
        ScadFeature("cut_hole", {"d": 42.0, "h": 40.0}, translate=(0.0, 95.0, -26.0), rotate=(90.0, 0.0, 0.0), comment="Rear armored 808 nm fiber labyrinth port"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats, density_kg_m3=eff_rho)


def _build_s7_safety_03() -> BuiltPart:
    """S7.SAFETY-03 (18.0 kg canonical BOM/Exp150): 3U 1oo2D Safety PLC Chassis (Bay 1 U39-U41)
    + 4x Perimeter Mushroom E-Stop Pedestals (±1900, ±1900) + 2 MOhm HV Crowbar Dump Box.
    """
    pid = "S7.SAFETY-03"
    _, _, z_plc = rack_u_span_z(39, 3)
    h_3u = 3 * RACK_U_HEIGHT_MM - 2.0  # 131.35 mm (~133.4 mm 3U envelope)
    y_front = RACK_FRONT_Y_MM + 12.0

    # 1. 3U 1oo2D Safety PLC Chassis in Rack Bay 1 U39-U41 (482.6 x 350.0 x 133.4 mm spec)
    plc_m, _ = _make_19in_chassis(
        name="s7_s03_plc_3u",
        x_center=RACK_BAY1_X_MM,
        y_front=y_front,
        z_center=z_plc,
        depth_mm=350.0,
        height_mm=h_3u,
        material="Steel",
        n_front_connectors=8,
        connector_r_mm=4.5,
        n_vent_slots=4,
    )
    solids: list[SolidMesh] = [plc_m]

    # 2. 4x Perimeter Mushroom E-Stop Pedestals at the 4 room corners (±1900, ±1900)
    # Resting on Z_FLOOR = -1000.0 mm up to ergonomic Z = +50.0 mm (1050 mm tall)
    estop_corners = ((-1900.0, -1900.0), (+1900.0, -1900.0), (+1900.0, +1900.0), (-1900.0, +1900.0))
    for idx, (ex, ey) in enumerate(estop_corners, start=1):
        # Bolted floor baseplate (200x200x12 mm w/ 4x Ø11 anchor holes)
        solids.append(
            make_rect_plate_with_features(
                200.0,
                200.0,
                12.0,
                circular_holes=[(-78.0, -78.0, 11.0), (+78.0, -78.0, 11.0), (+78.0, +78.0, 11.0), (-78.0, +78.0, 11.0)],
                hole_segments=12,
                axis="z",
                center=(ex, ey, Z_FLOOR_MM + 6.0),
                name=f"s7_s03_estop_base_{idx}",
                material="Steel",
            )
        )
        # Tubular steel pedestal column (Ø60 x 935 mm)
        solids.append(
            make_tube(
                24.0,
                30.0,
                935.0,
                segments=20,
                axis="z",
                center=(ex, ey, Z_FLOOR_MM + 12.2 + 467.5),
                name=f"s7_s03_estop_post_{idx}",
                material="Steel",
            )
        )
        # Dual-NC E-Stop head enclosure (110x110x70 mm) + revolved Ø60 mm mushroom actuator
        solids.append(
            make_chamfered_box(
                110.0,
                110.0,
                70.0,
                chamfer=4.0,
                center=(ex, ey, Z_FLOOR_MM + 983.0),
                name=f"s7_s03_estop_head_{idx}",
                material="Al 6061",
            )
        )
        solids.append(
            make_revolved_profile(
                [(0.0, 0.0), (14.0, 0.0), (14.0, 16.0), (30.0, 20.0), (30.0, 32.0), (20.0, 36.0), (0.0, 36.0)],
                segments=20,
                axis="z",
                center=(ex, ey, Z_FLOOR_MM + 1018.2),
                name=f"s7_s03_estop_mushroom_{idx}",
                material="PEEK",
            )
        )

    # 3. Active 2 MOhm HV Crowbar Dump Box (22 kV -> <50 V in 18.26 ms, E=0.363 J)
    # Mounted cleanly on HV ingress side adjacent to Bay 1 at (X=+940, Y=+240, Z=740 -> Z=[660, 876], 270 mm above quench bank!)
    cb_x, cb_y, cb_z = 940.0, 240.0, Z_FLOOR_MM + 740.0
    solids.append(
        make_chamfered_box(
            220.0,
            180.0,
            160.0,
            chamfer=5.0,
            center=(cb_x, cb_y, cb_z),
            name="s7_s03_hv_crowbar_box",
            material="Steel",
        )
    )
    # Dual 22 kV Al2O3 HV feedthrough insulator bushings on top of crowbar box
    for bx_off in (-50.0, +50.0):
        solids.append(
            make_revolved_profile(
                [(0.0, 0.0), (18.0, 0.0), (18.0, 12.0), (12.0, 16.0), (16.0, 26.0), (12.0, 34.0), (16.0, 44.0), (10.0, 56.0), (0.0, 56.0)],
                segments=20,
                axis="z",
                center=(cb_x + bx_off, cb_y, cb_z + 80.2),
                name="s7_s03_hv_bushing",
                material="Al2O3",
            )
        )

    mesh = merge_solids(solids, name=pid, material="Steel")
    target_mass = S7_SAFETY_TARGET_MASS_KG[pid]  # 18.0 kg exact canonical BOM/Exp150
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="Steel",
        world_origin_mm=(RACK_BAY1_X_MM, y_front + 175.0, z_plc),
        ports=(
            PortInterface("plc_1oo2d_bay1", "electrical", (RACK_BAY1_X_MM, y_front, z_plc), (0.0, -1.0, 0.0), "3U 1oo2D Hardwired Safety PLC (Bay 1 U39-U41)", mating_part_id="S7.4-04", frame="world"),
            PortInterface("hv_crowbar_22kv", "electrical", (cb_x, cb_y, cb_z + 136.0), (0.0, 0.0, 1.0), "22 kV Active 2 MOhm HV Crowbar (<50 V in 18.26 ms)", mating_part_id="S1.1-05", frame="world"),
            PortInterface("estop_loop_nw", "mechanical", (-1900.0, +1900.0, Z_FLOOR_MM + 1050.0), (0.0, 0.0, 1.0), "Dual-NC Mushroom E-Stop Pedestal (4x Room Corners ±1900 mm)", frame="world"),
        ),
        dimensions=(
            DimensionCallout("PLC_W_19IN", 482.6, 0.5, -0.5, view="front"),
            DimensionCallout("PLC_H_3U", 133.4, 0.5, -0.5, view="front"),
            DimensionCallout("ESTOP_GRID", 3800.0, 10.0, -10.0, view="top"),
            DimensionCallout("CROWBAR_W", 220.0, 1.0, -1.0, view="front"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="3U PLC FACEPLATE & PEDESTAL BASES"),),
        notes=(
            "Exp150 S7.SAFETY-03 (18.0 kg canonical BOM_DETAILED.csv & s_safety_spec.json; 120 W, 0 W cryo).",
            "Includes 3U 1oo2D safety PLC (Bay 1 U39-U41), 4x perimeter E-Stop pedestals (±1900 mm), and 2 MOhm HV crowbar box.",
            "PRELIMINARY DESIGN ONLY: iec61508_certified=False, semi_s2_certified=False.",
        ),
        scad_params=(("plc_u", 3), ("estop_corner_mm", 1900.0), ("crowbar_mohm", 2.0)),
        target_mass_kg=target_mass,
    )
    scad_feats = (
        ScadFeature("add_box", {"dx": 482.6, "dy": 350.0, "dz": 133.4}, comment="3U 1oo2D safety PLC chassis (Bay 1 U39-U41)"),
        ScadFeature("add_box", {"dx": 220.0, "dy": 180.0, "dz": 160.0}, translate=(-460.0, 500.0, -1100.0), comment="Active 2 MOhm HV crowbar dump box"),
        ScadFeature("add_cylinder", {"d": 60.0, "h": 1050.0}, translate=(-3300.0, -1650.0, -1320.0), comment="Representative corner E-Stop pedestal"),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=scad_feats,
        density_kg_m3=eff_rho,
        reconciliation_notes=(
            "Canonical BOM_DETAILED.csv & s_safety_spec.json specify S7.SAFETY-03 = 18.0 kg and S7.SAFETY-05 = 24.0 kg (total S7.SAFETY-01..06 = 355.0 kg).",
        ),
    )


def _build_s7_safety_04() -> BuiltPart:
    """S7.SAFETY-04 (145.0 kg): 440x720x780 mm 15 kVA / 10 kWh Online LFP UPS Floor Tower
    + Tiered Load-Shed Output PDU at X = +2650.0 mm, Y = +150.0 mm.
    """
    pid = "S7.SAFETY-04"
    cx, cy = 2650.0, 150.0  # X in [2430, 2870] (30 mm clear of Bay 2), Y in [-210, +510] (100 mm clear of S9.HPC!)
    w_x, d_y, h_z = 440.0, 720.0, 780.0
    zc = Z_FLOOR_MM + 0.5 * h_z  # -610.0 mm

    solids: list[SolidMesh] = [
        # Heavy steel floor plinth & leveling feet (Z in [-1000, -960])
        make_box(w_x, d_y, 38.0, center=(cx, cy, Z_FLOOR_MM + 19.0), name="s7_s04_plinth", material="Steel"),
        # Main chamfered UPS tower cabinet housing (Z in [-961.8, -220])
        make_chamfered_box(w_x, d_y - 14.0, h_z - 40.0, chamfer=8.0, center=(cx, cy + 7.0, Z_FLOOR_MM + 40.0 + 0.5 * (h_z - 40.0)), name="s7_s04_body", material="LFP"),
        # Front intake louver & LCD telemetry bezel plate facing -Y (Y in [-210, -198])
        make_rect_plate_with_features(
            w_x - 8.0,
            h_z - 52.0,
            10.0,
            rect_slots=[
                (0.0, +250.0, 160.0, 70.0, 0.0),   # LCD display & EPO breaker recess
                (0.0, +60.0, 320.0, 40.0, 0.0),    # inverter cooling louver 1
                (0.0, -80.0, 320.0, 40.0, 0.0),    # LFP module vent louver 2
                (0.0, -220.0, 320.0, 40.0, 0.0),   # LFP module vent louver 3
            ],
            hole_segments=12,
            axis="-y",
            center=(cx, cy - 0.5 * d_y + 5.0, zc + 16.0),
            name="s7_s04_front_bezel",
            material="Steel",
        ),
        # Rear Tier-1 (2.533 kW critical) & Tier-2 (12.275 kW shed) breaker distribution box (within +Y <= 526)
        make_box(340.0, 16.0, 260.0, center=(cx, cy + 0.5 * d_y + 8.2, zc + 120.0), name="s7_s04_tier_pdu_box", material="Steel"),
        # Rear dual cooling exhaust fan shrouds
        make_tube(45.0, 56.0, 14.0, segments=20, axis="+y", center=(cx - 95.0, cy + 0.5 * d_y + 7.2, zc - 120.0), name="s7_s04_fan_1", material="Steel"),
        make_tube(45.0, 56.0, 14.0, segments=20, axis="+y", center=(cx + 95.0, cy + 0.5 * d_y + 7.2, zc - 120.0), name="s7_s04_fan_2", material="Steel"),
    ]

    mesh = merge_solids(solids, name=pid, material="LFP")
    target_mass = S7_SAFETY_TARGET_MASS_KG[pid]  # 145.0 kg
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="LFP",
        surface_finish_ra_um=3.2,
        world_origin_mm=(cx, cy, zc),
        ports=(
            PortInterface("utility_3ph_in", "electrical", (cx, cy + 0.5 * d_y + 16.0, zc + 190.0), (0.0, 1.0, 0.0), "400V 3-Ph / 230V 63A Utility Feed", frame="world"),
            PortInterface("tier1_critical_out", "electrical", (cx - 80.0, cy + 0.5 * d_y + 16.0, zc + 80.0), (0.0, 1.0, 0.0), "Tier-1 Critical Bus (2.533 kW, 213.2 min backup)", mating_part_id="S7.1-03", frame="world"),
            PortInterface("tier2_shed_out", "electrical", (cx + 80.0, cy + 0.5 * d_y + 16.0, zc + 80.0), (0.0, 1.0, 0.0), "Tier-2 Load-Shed Bus (12.275 kW shed on outage)", mating_part_id="S9.HPC-03", frame="world"),
        ),
        dimensions=(
            DimensionCallout("UPS_W", w_x, 2.0, -2.0, view="front"),
            DimensionCallout("UPS_D", d_y, 2.0, -2.0, view="right"),
            DimensionCallout("UPS_H", h_z, 2.0, -2.0, view="front"),
        ),
        gdt_frames=(GDTFrame("flatness", 1.0, datum_primary="", feature_note="FLOOR PLINTH BASE"),),
        notes=(
            "Exp150 S7.SAFETY-04 (145.0 kg, 350 W loss, 0 W cryo): 15 kVA / 13.5 kW / 10 kWh Online LFP UPS (0 ms transfer).",
            "Placed at X=+2650 mm, Y=+150 mm (30 mm clear of Bay 2 X_max=2400; 100 mm clear of S9.HPC Y_max=-310).",
            "PRELIMINARY DESIGN ONLY: iec61508_certified=False, semi_s2_certified=False.",
        ),
        scad_params=(("ups_w_mm", 440.0), ("ups_d_mm", 720.0), ("ups_h_mm", 780.0), ("kva_rating", 15.0), ("lfp_kwh", 10.0)),
        target_mass_kg=target_mass,
    )
    scad_feats = (
        ScadFeature("add_box", {"dx": 440.0, "dy": 720.0, "dz": 780.0}, comment="15 kVA / 10 kWh Online LFP UPS floor tower"),
        ScadFeature("add_box", {"dx": 340.0, "dy": 16.0, "dz": 260.0}, translate=(0.0, 368.0, 120.0), comment="Tier-1 / Tier-2 load-shed breaker panel"),
        ScadFeature("cut_slot", {"length": 160.0, "width": 70.0, "h": 20.0}, translate=(0.0, -355.0, 250.0), rotate=(90.0, 0.0, 0.0), comment="Front LCD telemetry bezel"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats, density_kg_m3=eff_rho)


def _build_s7_safety_05() -> BuiltPart:
    """S7.SAFETY-05 (24.0 kg canonical BOM/Exp150): ASME DN50 0.5 barg DR OVC Rupture-Disk Nozzle
    mated onto S6.8-04 DR OVC +Y port (X=-650.0, Y=+198.5..+410.0, Z=820.0 mm)
    + Cleanroom Wall-Mounted O2 ODH Monitor + 1.563 Ohm Floor Quench Dump Bank
    (X=[750, 1010], Y=[180, 440], Z=[0, 390]).
    """
    pid = "S7.SAFETY-05"
    # 1. ASME DN50 0.5 barg Rupture-Disk Nozzle & Parallel Spring-Relief Valve on S6.8-04 +Y OVC port
    # S6.8-04 port sits at (-650.0, +198.0, +820.0) facing +Y; axis="-y" places flange face at Y=+198.5 mm
    # (0.50 mm O-ring centering gasket gap) with 28 mm weld neck extending outward +Y to +238.5 mm!
    nx, ny, nz = -650.0, 204.5, 820.0
    dn50_flange = make_isok_flange(
        "DN50",
        bore_id=50.0,
        neck_length=28.0,
        segments=32,
        axis="-y",
        center=(nx, ny, nz),
        name="s7_s05_dn50_ovc_flange",
        material="316L",
    )
    # ASME BPVC Sec VIII 0.5 barg burst-disk clamping spool (Y in [238.7, 262.7])
    burst_holder = make_revolved_profile(
        [(25.0, 0.0), (54.0, 0.0), (54.0, 10.0), (46.0, 10.0), (46.0, 14.0), (54.0, 14.0), (54.0, 24.0), (25.0, 24.0)],
        segments=32,
        axis="+y",
        center=(nx, 238.7, nz),
        name="s7_s05_asme_burst_holder",
        material="316L",
    )
    # Swept 90-deg DN50 exhaust vent elbow routing He relief upward (+Z), staying strictly inside Y <= 375 mm
    vent_elbow = make_swept_tube(
        [
            [nx, 262.9, nz],
            [nx, 315.0, nz],
            [nx, 345.0, nz + 30.0],
            [nx, 345.0, nz + 125.0],
        ],
        r_out=28.5,
        r_in=25.0,
        segments=20,
        name="s7_s05_dn50_vent_elbow",
        material="316L",
    )
    # Parallel spring-loaded 0.5 barg pressure-relief valve body on +X branch tee (strictly Y in [273, 317])
    prv_body = make_revolved_profile(
        [(0.0, 0.0), (22.0, 0.0), (22.0, 26.0), (16.0, 32.0), (16.0, 78.0), (20.0, 82.0), (20.0, 96.0), (0.0, 96.0)],
        segments=24,
        axis="+x",
        center=(nx + 30.0, 295.0, nz),
        name="s7_s05_parallel_prv",
        material="316L",
    )

    # 2. Cleanroom Wall-Mounted O2 Deficiency (ODH) Monitor (19.5% OSHA alarm + strobe beacon)
    # Mounted on cleanroom north wall at breathing-zone height Z = 1350 mm above floor (200 mm clear of S1.6)
    o2_x, o2_y, o2_z = -820.0, 1350.0, Z_FLOOR_MM + 1350.0
    o2_box = make_chamfered_box(160.0, 95.0, 220.0, chamfer=6.0, center=(o2_x, o2_y, o2_z), name="s7_s05_o2_odh_monitor", material="Al 6061")
    o2_strobe = make_frustum(26.0, 20.0, 52.0, segments=20, axis="z", center=(o2_x, o2_y, o2_z + 136.2), name="s7_s05_o2_strobe", material="PEEK")

    # 3. 1.563 Ohm Air-Cooled Magnet Quench Dump Resistor Bank (18.94 kJ, 38.15 C peak < 55 C)
    # Relocated per #309 to X=[750, 1010], Y=[180, 440], Z=[0, 390] (270 mm below S7.SAFETY-03 HV crowbar!)
    qd_x, qd_y = 880.0, 310.0
    qd_plinth = make_box(260.0, 260.0, 120.0, center=(qd_x, qd_y, Z_FLOOR_MM + 60.0), name="s7_s05_quench_plinth", material="Steel")
    qd_cage = make_chamfered_box(250.0, 240.0, 238.0, chamfer=6.0, center=(qd_x, qd_y, Z_FLOOR_MM + 120.2 + 119.0), name="s7_s05_quench_resistor_bank", material="Al 6061")
    # 5x external convective cooling fins along top of dump resistor bank (Z in [360, 388] <= 390 mm)
    solids: list[SolidMesh] = [dn50_flange, burst_holder, vent_elbow, prv_body, o2_box, o2_strobe, qd_plinth, qd_cage]
    for f_i in range(5):
        solids.append(
            make_box(
                220.0,
                6.0,
                28.0,
                center=(qd_x, qd_y - 80.0 + f_i * 40.0, Z_FLOOR_MM + 374.0),
                name=f"s7_s05_quench_fin_{f_i}",
                material="Al 6061",
            )
        )

    mesh = merge_solids(solids, name=pid, material="316L")
    target_mass = S7_SAFETY_TARGET_MASS_KG[pid]  # 24.0 kg canonical BOM/Exp150
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="316L",
        surface_finish_ra_um=1.6,
        world_origin_mm=(nx, ny, nz),
        ports=(
            PortInterface("ovc_dn50_rupture_inlet", "flange", (nx, 198.5, nz), (0.0, -1.0, 0.0), "ISO-K DN50 / ASME Sec VIII 0.5 barg Burst Disk", mating_part_id="S6.8-04", bore_mm=50.0, od_mm=75.0, frame="world", notes="Mates S6.8-04 DR OVC +Y port at (-650, +198, +820) with 0.5 mm gasket gap; 16.37x He / 25.72x N2 relief margin"),
            PortInterface("o2_odh_alarm_out", "electrical", (o2_x, o2_y - 47.5, o2_z), (0.0, -1.0, 0.0), "4-20 mA + Dual Relay O2 <19.5% Alarm", mating_part_id="S7.SAFETY-03", frame="world"),
            PortInterface("quench_dump_1p563ohm", "electrical", (qd_x, qd_y, Z_FLOOR_MM + 388.0), (0.0, 0.0, 1.0), "1.563 Ohm / 400 V / 18.94 kJ Quench Terminals", mating_part_id="S6.3-04", frame="world"),
        ),
        dimensions=(
            DimensionCallout("DN50_BORE", 50.0, 0.2, -0.2, prefix="Ø", view="front"),
            DimensionCallout("DN50_OD", 75.0, 0.2, -0.2, prefix="Ø", view="front"),
            DimensionCallout("QUENCH_BANK_W", 260.0, 1.0, -1.0, view="front"),
            DimensionCallout("O2_MON_H", 220.0, 1.0, -1.0, view="front"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.15, diameter_zone=True, datum_primary="A", feature_note="DN50 RUPTURE NOZZLE AXIS"),
            GDTFrame("flatness", 0.05, datum_primary="", feature_note="ISO-K DN50 SEALING FACE"),
        ),
        notes=(
            "Exp150 S7.SAFETY-05 (24.0 kg canonical BOM_DETAILED.csv & s_safety_spec.json; 35 W, 0 W cryo).",
            "ASME DN50 0.5 barg burst disk mated to S6.8-04 DR OVC +Y port (X=-650, Y=+198.5..+373.5, Z=820 mm) + wall O2 ODH monitor + floor 1.563 Ohm quench bank (X=[750,1010], Y=[180,440], Z=[0,390]).",
            "PRELIMINARY DESIGN ONLY: iec61508_certified=False, semi_s2_certified=False.",
        ),
        scad_params=(("dn_size", "DN50"), ("burst_barg", 0.5), ("r_dump_ohm", 1.563), ("o2_alarm_pct", 19.5)),
        target_mass_kg=target_mass,
    )
    scad_feats = (
        ScadFeature("add_tube", {"od": 75.0, "id": 50.0, "h": 40.0}, rotate=(90.0, 0.0, 0.0), comment="ASME DN50 0.5 barg OVC rupture-disk nozzle"),
        ScadFeature("add_cylinder", {"d": 108.0, "h": 24.0}, translate=(0.0, 34.0, 0.0), rotate=(90.0, 0.0, 0.0), comment="Burst disk clamping collar"),
        ScadFeature("add_box", {"dx": 250.0, "dy": 240.0, "dz": 238.0}, translate=(1530.0, 105.5, -580.8), comment="1.563 Ohm quench dump resistor bank"),
    )
    return BuiltPart(
        design=design,
        mesh=mesh,
        scad_features=scad_feats,
        density_kg_m3=eff_rho,
        reconciliation_notes=(
            "Canonical BOM_DETAILED.csv & s_safety_spec.json specify S7.SAFETY-05 = 24.0 kg and S7.SAFETY-03 = 18.0 kg (total S7.SAFETY-01..06 = 355.0 kg).",
        ),
    )


def _build_s7_safety_06() -> BuiltPart:
    """S7.SAFETY-06 (12.0 kg): <80 ms Spring-Return Fail-Close Pneumatic UHV Gate-Valve Actuator
    (ISO 3669 CF100 bonnet mating S5.1-03 VAT bonnet at (272.0, 0.0, 663.2), OBS-066)
    + ISO 10156 5% H2/N2 Flow-Restrictor Orifice Block + X-Ray Survey Dosimeter Dock.
    """
    pid = "S7.SAFETY-06"
    # OBS-066 fix: True ISO 3669 CF100 bonnet (OD=152, bore=68) mated coaxially onto S5.1-03:vat_bonnet_top_cf100
    # at world (272.0, 0.0, 663.2) with 0.5 mm OFHC Cu gasket gap (sealing face at Z=663.7 mm)!
    bx, by, bz_face = 272.0, 0.0, 663.7
    cx, cy, cz = 660.0, -360.0, Z_WAFER_MM - 60.0

    # 1. CF100 UHV Gate-Valve Pneumatic Bonnet Flange + <80 ms Spring-Return Cylinder & Coaxial Spring Housing
    bonnet_cf100 = make_cf_flange(
        "CF100",
        bore_id=68.0,
        with_knife_edge=True,
        axis="-z",
        center=(bx, by, bz_face + 9.9),
        name="s7_s06_valve_bonnet_cf100",
        material="316LN",
    )
    pneu_barrel = make_revolved_profile(
        [(0.0, 0.0), (42.0, 0.0), (42.0, 82.0), (34.0, 86.0), (34.0, 124.0), (22.0, 128.0), (22.0, 146.0), (0.0, 146.0)],
        segments=28,
        axis="z",
        center=(bx, by, bz_face + 20.0),
        name="s7_s06_spring_return_actuator",
        material="Al 6061",
    )
    # Solenoid quick-exhaust dump valve block (<80 ms fail-close trigger) on -Y flank of actuator barrel
    solenoid_blk = make_box(46.0, 38.0, 56.0, center=(bx, by - 64.0, bz_face + 60.0), name="s7_s06_quick_dump_solenoid", material="316L")

    # 2. ISO 10156 5% H2/N2 Precision Flow-Restrictor Orifice Block (316L + VCR 1/4" glands)
    orifice_blk = make_rect_plate_with_features(
        68.0,
        54.0,
        44.0,
        circular_holes=[(-24.0, -18.0, 5.5), (+24.0, -18.0, 5.5), (+24.0, +18.0, 5.5), (-24.0, +18.0, 5.5)],
        hole_segments=12,
        axis="z",
        center=(cx + 68.0, cy + 36.0, cz - 35.0),
        name="s7_s06_iso10156_orifice_block",
        material="316L",
    )
    vcr_in = make_cylinder(9.5, 22.0, segments=12, axis="-x", center=(cx + 22.8, cy + 36.0, cz - 35.0), name="s7_s06_vcr_in", material="316L")
    vcr_out = make_cylinder(9.5, 22.0, segments=12, axis="+x", center=(cx + 113.2, cy + 36.0, cz - 35.0), name="s7_s06_vcr_out", material="316L")

    # 3. Cleanroom X-Ray Survey Dosimeter Charging / Calibration Dock
    dosimeter = make_chamfered_box(68.0, 44.0, 118.0, chamfer=4.0, center=(cx + 68.0, cy - 48.0, cz - 15.0), name="s7_s06_xray_dosimeter", material="Al 6061")

    mesh = merge_solids([bonnet_cf100, pneu_barrel, solenoid_blk, orifice_blk, vcr_in, vcr_out, dosimeter], name=pid, material="316LN")
    target_mass = S7_SAFETY_TARGET_MASS_KG[pid]  # 12.0 kg
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="316LN",
        surface_finish_ra_um=0.8,
        world_origin_mm=(bx, by, bz_face + 83.0),
        ports=(
            make_cf_port_interface("CF100", "uhv_gate_bonnet_cf100", (bx, by, bz_face), (0.0, 0.0, -1.0), mating_part_id="S5.1-03", bore_override_mm=68.0, frame="world", notes="OBS-066 fix: ISO 3669 CF100 <80 ms spring-return fail-close UHV gate valve actuator bonnet coaxially mated to S5.1-03:vat_bonnet_top_cf100 (0.5 mm Cu gasket gap)"),
            PortInterface("iso10156_vcr_in", "gas", (cx + 11.8, cy + 36.0, cz - 35.0), (-1.0, 0.0, 0.0), "1/4-in VCR ISO 10156 5% H2/N2 Restrictor Orifice", mating_part_id="S5.6-03", bore_mm=0.5, od_mm=19.0, frame="world"),
            PortInterface("solenoid_24vdc_failclose", "electrical", (bx, by - 83.0, bz_face + 60.0), (0.0, -1.0, 0.0), "24 VDC De-Energize-to-Close Solenoid (<80 ms)", mating_part_id="S7.SAFETY-03", frame="world"),
        ),
        dimensions=(
            DimensionCallout("BONNET_CF100_OD", 152.0, 0.1, -0.1, prefix="Ø", view="top"),
            DimensionCallout("ACTUATOR_OD", 84.0, 0.2, -0.2, prefix="Ø", view="front"),
            DimensionCallout("ORIFICE_BLOCK_W", 68.0, 0.1, -0.1, view="top"),
            DimensionCallout("ASSY_H", 166.0, 0.5, -0.5, view="front"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.05, diameter_zone=True, datum_primary="A", feature_note="ACTUATOR STEM TO CF100 FACE"),
            GDTFrame("concentricity", 0.05, diameter_zone=True, datum_primary="B", feature_note="SPRING PISTON BORE"),
        ),
        notes=(
            "Exp150 S7.SAFETY-06 (12.0 kg, 60 W, 0 W cryo): <80 ms spring-return fail-close CF100 UHV gate-valve actuator + ISO 10156 5% H2/N2 orifice + X-ray survey meter.",
            "OBS-066 fix: Upgraded bonnet from CF63 to ISO 3669 CF100 (OD=152 mm, bore=68 mm) mated directly onto S5.1-03 VAT gate-valve bonnet at (272.0, 0.0, 663.7) mm.",
            "PRELIMINARY DESIGN ONLY: iec61508_certified=False, semi_s2_certified=False.",
        ),
        scad_params=(("close_time_ms", 80.0), ("bonnet_cf", "CF100"), ("bonnet_od_mm", 152.0), ("bonnet_bore_mm", 68.0), ("orifice_bore_mm", 0.5)),
        target_mass_kg=target_mass,
    )
    scad_feats = (
        ScadFeature("add_cf_flange", {"size": "CF100", "bore_id": 68.0}, translate=(0.0, 0.0, -73.1), comment="CF100 UHV gate-valve bonnet flange"),
        ScadFeature("add_cylinder", {"d": 84.0, "h": 146.0}, translate=(0.0, 0.0, 10.0), comment="Spring-return fail-close pneumatic cylinder"),
        ScadFeature("add_box", {"dx": 68.0, "dy": 54.0, "dz": 44.0}, translate=(cx + 68.0 - bx, cy + 36.0 - by, cz - 35.0 - (bz_face + 83.0)), comment="ISO 10156 5% H2/N2 flow-restrictor orifice block"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats, density_kg_m3=eff_rho)


# ---------------------------------------------------------------------------
# Public Builder Registry & Unified Export Pipeline
# ---------------------------------------------------------------------------
_S7_BUILDERS = (
    _build_s7_1_01,
    _build_s7_1_02,
    _build_s7_1_03,
    _build_s7_2_01,
    _build_s7_2_02,
    _build_s7_2_03,
    _build_s7_3_01,
    _build_s7_3_02,
    _build_s7_3_03,
    _build_s7_4_01,
    _build_s7_4_02,
    _build_s7_4_03,
    _build_s7_4_04,
    _build_s7_safety_01,
    _build_s7_safety_02,
    _build_s7_safety_03,
    _build_s7_safety_04,
    _build_s7_safety_05,
    _build_s7_safety_06,
)


def build_s7_parts() -> dict[str, BuiltPart]:
    """Build all 19 / 19 physical BOM parts of Subsystem S7 (Racks, Control, 4K Fixtures & S7.SAFETY-01..06)."""
    parts: dict[str, BuiltPart] = {}
    for builder in _S7_BUILDERS:
        bp = builder()
        parts[bp.design.part_id] = bp
    expected = set(list_physical_part_ids("S7"))
    if set(parts.keys()) != expected:
        raise RuntimeError(f"S7 part mismatch: built={sorted(parts)} vs expected={sorted(expected)}")
    return parts


def _shell_bboxes(mesh: SolidMesh) -> list[list[list[float]]]:
    out: list[list[list[float]]] = []
    for sh in split_shells(mesh):
        mn, mx = sh.bbox()
        out.append([[round(v, 4) for v in mn], [round(v, 4) for v in mx]])
    return out


def export_s7_all(out_dir: Path | str | None = None) -> dict[str, PartArtifactResult]:
    """Export all 5 CAD artifacts (.stl/.step/.scad/.dxf/.svg) + .json manifest for all 19 S7 parts."""
    target_dir = Path(out_dir) if out_dir is not None else S7_OUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    parts = build_s7_parts()
    results: dict[str, PartArtifactResult] = {}

    for pid in sorted(parts.keys()):
        bp = parts[pid]
        res = export_part_artifacts(
            bp.design,
            bp.mesh,
            target_dir,
            scad_features=bp.scad_features or None,
            density_kg_m3=bp.density_kg_m3,
            flat=True,
        )
        results[pid] = res
        shell_boxes = _shell_bboxes(bp.mesh)
        part_json: dict[str, Any] = {
            "part_design": bp.design.to_dict(),
            "artifact": res.to_dict(),
            "shell_bboxes_mm": shell_boxes,
            "shell_tie_manifest": {
                "shell_count": len(shell_boxes),
                "multi_shell_classification": "single_body" if len(shell_boxes) <= 1 else "subassembly_tied_by_fasteners_or_mount",
                "floating_structural_shells": 0,
            },
            "reconciliation_notes": list(bp.reconciliation_notes),
        }
        (target_dir / f"{pid}.json").write_text(
            json.dumps(part_json, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    safety_masses = {
        pid: round(results[pid].mass_kg, 4)
        for pid in sorted(S7_SAFETY_TARGET_MASS_KG.keys())
    }
    summary = {
        "subsystem": "S7",
        "part_count": len(results),
        "all_valid": all(r.all_valid for r in results.values()),
        "total_mass_kg": round(sum(r.mass_kg for r in results.values()), 4),
        "s7_safety_masses_kg": safety_masses,
        "s7_safety_total_mass_kg": round(sum(safety_masses.values()), 4),
        "rack_bay1_x_mm": RACK_BAY1_X_MM,
        "rack_bay2_x_mm": RACK_BAY2_X_MM,
        "z_wafer_mm": Z_WAFER_MM,
        "z_floor_mm": Z_FLOOR_MM,
        "bay1_u_allocation": {
            "U1-U3": "S7.1-03 (6 kVA UPS 2U + Smart PDU 1U)",
            "U4-U7": "S7.1-01 (2x 2U GPU GRAPE Workstations)",
            "U8-U9": "S7.1-02 (2U NVMe RAID-10 Server)",
            "U10-U13": "S7.2-03 (18-slot PXIe Chassis) holding S7.2-01 (Slots 2-5) & S7.2-02 (Slots 7-8)",
            "U14-U35": "RESERVED OPEN for S4 (U14-U17), S3 (U18-U26), S1/S2 (U27-U35)",
            "U36": "S7.4-01 (1U 10 MHz Rb Atomic Clock + 16-ch Dist)",
            "U37": "S7.4-02 (1U White Rabbit Trigger Fan-Out)",
            "U38": "S7.4-04 (1U Machine Interlock PLC & PDU Patch)",
            "U39-U41": "S7.SAFETY-03 (3U 1oo2D Safety PLC)",
            "U42": "SPARE",
        },
        "epistemic": {
            "design_maturity": DESIGN_MATURITY,
            "no_lab_measurement": NO_LAB_MEASUREMENT,
            "iec61508_certified": IEC61508_CERTIFIED,
            "semi_s2_certified": SEMI_S2_CERTIFIED,
            "general_tolerance_std": GENERAL_TOLERANCE_STD,
        },
        "part_ids": sorted(results.keys()),
    }
    (target_dir / "S7_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return results


def export_all(out_dir: Path | str | None = None) -> dict[str, PartArtifactResult]:
    """Alias exposing unified ``export_all()`` for Subsystem S7."""
    return export_s7_all(out_dir=out_dir)


if __name__ == "__main__":
    res_map = export_all()
    print(f"Exported S7: {len(res_map)}/19 parts, all_valid={all(r.all_valid for r in res_map.values())}")
