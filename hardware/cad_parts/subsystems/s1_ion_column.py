"""Subsystem S1 — Ion Source, Wien Mass Filter, Arch-B Decel Column, HDA-HiRes & PH3 Facility.

Designs, verifies, and exports all 23 physical solid BOM parts of ``S1``
(``S1.1-01`` through ``S1.7-01``: 15 ``CUSTOM_FULL`` + 8 ``COTS_ENV_ICD``) using
the pure-Python CAD kernel in ``hardware.cad_parts.core``.

Global Machine Coordinate System (Wave 2B locked convention):
- ``Z = 0.000 mm`` : Wafer active top surface (``0 V`` ground, Exp124/Exp125 ``z_loc = 0``).
- ``+Z``           : Vertically upward along the ion-column beam axis (``X = 0, Y = 0``).
- ``Z = -500.0 mm``: Cleanroom laboratory floor plane.
- 19" Rack Bay 1   : Centered at ``X = +1480.0 mm``, ``482.6 mm`` width along ``X`` (``X ∈ [1238.7, 1721.3]``), front face at ``Y = -438.0 mm``, rear ``Y <= +350 mm`` (S1/S2 in ``U27..U35``, ``Z_nat(u) = -410.0 + (u-1)*44.45``).
- Facility PH3 bay : Centered at ``X = -1350.0 mm`` (``X ∈ [-1600, -1100] mm``, ``Y ∈ [+750, +1870] mm``).

Zero-aliasing contract:
- Every part is keyed strictly by exact BOM ``part_id``.
- Option-Q multi-species cartridge is strictly ``S1.7-01`` (fixing legacy v6 ``S1.6`` alias).
- ``S1.6-01`` / ``S1.6-02`` remain strictly SEMI S2 PH3 toxic gas cabinet & dry-bed scrubber.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, NamedTuple, Sequence

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
    export_part_artifacts,
    list_physical_part_ids,
    make_bellows,
    make_box,
    make_cf_flange,
    make_cf_port_interface,
    make_cf_weld_neck,
    make_chamfered_box,
    make_cylinder,
    make_hemisphere_shell,
    make_part_design_from_bom,
    make_plate_with_holes,
    make_rect_plate_with_features,
    make_revolved_profile,
    make_ring_with_bolt_circle,
    make_sphere,
    make_swept_tube,
    make_tube,
    merge_solids,
    rect_2d,
    slot_2d,
    transform_mesh,
)

S1_OUT_DIR: Path = REPO_ROOT / "hardware" / "cad_parts" / "out" / "S1"
RACK_BAY1_X: float = 1480.0
RACK_BAY1_FRONT_Y: float = -438.0
RACK_BAY1_Z_NAT_BASE: float = -410.0  # Canonical Z_base = +90.0 mm after +500.0 Z_WAFER offset
FLOOR_Z: float = -500.0


def rack_bay1_slot_z(u_start: int, u_height: int) -> tuple[float, float]:
    """Return ``(z_center_nat, chassis_dz)`` in Z_WAFER=0 frame with ±1.0 mm slot clearance."""
    z_lo = RACK_BAY1_Z_NAT_BASE + (u_start - 1) * 44.45 + 1.0
    z_hi = RACK_BAY1_Z_NAT_BASE + (u_start - 1 + u_height) * 44.45 - 1.0
    return round(0.5 * (z_lo + z_hi), 4), round(z_hi - z_lo, 4)


class BuiltPart(NamedTuple):
    """Built CAD part pairing frozen design metadata, global watertight mesh & SCAD CSG."""

    design: PartDesign
    mesh: SolidMesh
    scad_features: tuple[ScadFeature, ...]
    checks: dict[str, Any]


# ---------------------------------------------------------------------------
# Reusable Feature-Level Mechanical Sub-Builders
# ---------------------------------------------------------------------------
def make_rack_unit_chassis(
    *,
    u_start: int,
    u_height: int,
    x_center: float = RACK_BAY1_X,
    front_y: float = RACK_BAY1_FRONT_Y,
    depth_y: float = 430.0,
    body_width_x: float = 440.0,
    face_width_x: float = 482.6,
    wall_t: float = 3.0,
    rear_boss_count: int = 4,
    internal_modules: int = 1,
    material: str = "Al 6061",
    name: str = "rack_unit",
) -> tuple[SolidMesh, list[ScadFeature], tuple[float, float, float]]:
    """Build a realistic hollow 19-inch EIA-310 rack chassis oriented per #309 Master Bay 1.

    19-inch width (``482.6 mm``) spans ``X`` centered at ``x_center`` (``1480.0 mm`` ->
    ``X ∈ [1238.7, 1721.3]``); front handles & panel start strictly at ``Y >= front_y``
    (``-438.0 mm``) with chassis depth along ``+Y`` (rear bosses ``Y <= +10 mm << +350 mm``);
    vertical height leaves ``±1.0 mm`` per-slot clearance (``2.0 mm`` between adjacent units).
    """
    cz, dz = rack_bay1_slot_z(u_start, u_height)
    cx = x_center
    # Reserve 14.0 mm at front_y for recessed pull handles so entire solid stays in Y >= front_y
    handle_d = 14.0
    bezel_t = 5.0
    bezel_y = front_y + handle_d + 0.5 + 0.5 * bezel_t
    y_rear_face = front_y + depth_y
    cy = front_y + 0.5 * depth_y

    ear_hole_x = 0.5 * 465.1  # Exact EIA-310 18.312" (465.1 mm) horizontal screw spacing
    slot_z_offsets = (-0.30 * dz, 0.30 * dz) if u_height >= 2 else (0.0,)

    # axis="y" maps local X -> +X, local Y -> -Z, local Z -> +Y
    ear_slots = []
    for sx in (-ear_hole_x, ear_hole_x):
        for sz in slot_z_offsets:
            ear_slots.append((sx, sz, 10.2, 6.4, 0.0))
    vent_slots = []
    n_vents = 5 if u_height >= 2 else 3
    for iv in range(n_vents):
        vx = 80.0 + iv * 22.0
        vent_slots.append((vx, 0.0, max(0.55 * dz, 10.0), 6.0, 90.0))

    bezel_plate = make_rect_plate_with_features(
        face_width_x,
        dz,
        bezel_t,
        rect_slots=ear_slots + vent_slots,
        axis="y",
        center=(cx, bezel_y, cz),
        name=f"{name}_front_bezel",
        material=material,
    )

    # Hollow sheet-metal enclosure behind bezel (4 walls + rear panel, zero intersection)
    y_shell_start = bezel_y + 0.5 * bezel_t + 0.5
    y_shell_end = y_rear_face - wall_t - 0.5
    shell_dy = y_shell_end - y_shell_start
    shell_cy = 0.5 * (y_shell_start + y_shell_end)
    side_dz = dz - 2.0 * wall_t - 0.6

    parts: list[SolidMesh] = [bezel_plate]
    # Top and bottom lids
    for sgn in (-1.0, 1.0):
        parts.append(
            make_box(
                body_width_x,
                shell_dy,
                wall_t,
                center=(cx, shell_cy, cz + sgn * (0.5 * dz - 0.5 * wall_t)),
                name=f"{name}_lid_{'top' if sgn > 0 else 'bot'}",
                material=material,
            )
        )
    # Left (-X) and right (+X) side walls
    for sgn in (-1.0, 1.0):
        parts.append(
            make_box(
                wall_t,
                shell_dy,
                side_dz,
                center=(cx + sgn * (0.5 * body_width_x - 0.5 * wall_t), shell_cy, cz),
                name=f"{name}_side_{'pos' if sgn > 0 else 'neg'}",
                material=material,
            )
        )
    # Rear bulkhead plate (strictly behind top/bottom/side walls with >=0.5 mm seam)
    rear_y = y_rear_face - 0.5 * wall_t
    parts.append(
        make_box(
            body_width_x - 0.4,
            wall_t,
            dz - 0.4,
            center=(cx, rear_y, cz),
            name=f"{name}_rear_panel",
            material=material,
        )
    )

    # Dual machined front pull handles seated flush within [front_y, front_y + handle_d]
    handle_h = min(0.65 * dz, 80.0)
    for hx in (-202.0, 202.0):
        parts.append(
            make_box(
                10.0,
                handle_d,
                handle_h,
                center=(cx + hx, front_y + 0.5 * handle_d, cz),
                name=f"{name}_handle_{'p' if hx > 0 else 'n'}",
                material="316LN",
            )
        )

    # Internal compact HV / PSU core module(s) sized for realistic rack mass (~4-14 kg)
    mod_wx = 0.58 * (body_width_x - 40.0 - (internal_modules - 1) * 18.0) / max(internal_modules, 1)
    mod_dy = 0.36 * shell_dy
    mod_dz = max(0.56 * side_dz, 10.0)
    span_x = body_width_x - 80.0
    for im in range(internal_modules):
        x0 = (im - 0.5 * (internal_modules - 1)) * (span_x / max(internal_modules, 1))
        parts.append(
            make_chamfered_box(
                mod_wx,
                mod_dy,
                mod_dz,
                chamfer=min(2.0, 0.15 * mod_dz),
                center=(cx + x0, shell_cy, cz),
                name=f"{name}_core_{im + 1}",
                material="Al 6061",
            )
        )

    # Rear SHV / triax / IEC connector bosses protruding +12 mm on +Y rear bulkhead (Y <= +5 mm << +350 mm)
    for ib in range(rear_boss_count):
        bx = (ib - 0.5 * (rear_boss_count - 1)) * (body_width_x * 0.65 / max(rear_boss_count, 1))
        parts.append(
            make_cylinder(
                radius=7.0,
                height=12.0,
                segments=16,
                axis="+y",
                center=(cx + bx, y_rear_face + 6.5, cz),
                name=f"{name}_conn_{ib + 1}",
                material="316LN",
            )
        )

    mesh = merge_solids(parts, name=name, material=material)
    scad_feats = [
        ScadFeature("add_box", {"dx": body_width_x, "dy": depth_y - handle_d - bezel_t, "dz": dz}, translate=(0.0, 0.5 * (handle_d + bezel_t), 0.0), comment=f"{u_height}U hollow 19-in chassis body (width along X)"),
        ScadFeature("add_box", {"dx": face_width_x, "dy": bezel_t, "dz": dz}, translate=(0.0, -0.5 * depth_y + handle_d + 0.5 * bezel_t, 0.0), comment="EIA-310 19-in front panel w/ mounting ears facing -Y"),
        ScadFeature("cut_slot", {"length": 10.2, "width": 6.4, "h": bezel_t + 4.0}, translate=(ear_hole_x, -0.5 * depth_y + handle_d + 0.5 * bezel_t, 0.0), rotate=(90.0, 0.0, 0.0), comment="EIA-310 +X rack slot"),
        ScadFeature("cut_slot", {"length": 10.2, "width": 6.4, "h": bezel_t + 4.0}, translate=(-ear_hole_x, -0.5 * depth_y + handle_d + 0.5 * bezel_t, 0.0), rotate=(90.0, 0.0, 0.0), comment="EIA-310 -X rack slot"),
    ]
    return mesh, scad_feats, (cx, cy, cz)


def _build_duoplasmatron_mesh(
    cx: float,
    cy: float,
    z_bot: float,
    *,
    name: str,
    with_side_cf40_neg_x: bool = False,
) -> tuple[SolidMesh, list[ScadFeature]]:
    """Build water-cooled duoplasmatron plasma chamber (h=140.0 mm, OD=90.0 mm + top CF63)."""
    z_top = z_bot + 140.0
    # 1. Stepped Molybdenum anode exit nose cone (z_bot .. z_bot + 18.8 mm)
    anode_prof = [
        (2.0, z_bot),
        (14.0, z_bot),
        (28.0, z_bot + 8.0),
        (34.0, z_bot + 18.8),
        (12.0, z_bot + 18.8),
        (6.0, z_bot + 7.0),
        (2.0, z_bot + 3.0),
    ]
    anode = make_revolved_profile(
        anode_prof, segments=48, axis="z", center=(cx, cy, 0.0), name=f"{name}_mo_anode", material="Mo"
    )

    # 2. Water-cooled 316LN plasma chamber outer jacket with 4 external cooling jacket ribs
    #    Spans z = z_bot + 19.2 .. z_bot + 122.0 (h = 102.8 mm, OD = 90.0 mm, ID = 44.0 mm)
    z0 = z_bot + 19.2
    z1 = z_bot + 122.0
    jacket_prof = [
        (22.0, z0),
        (45.0, z0),
        (45.0, z0 + 18.0),
        (41.5, z0 + 18.0),
        (41.5, z0 + 28.0),
        (45.0, z0 + 28.0),
        (45.0, z0 + 46.0),
        (41.5, z0 + 46.0),
        (41.5, z0 + 56.0),
        (45.0, z0 + 56.0),
        (45.0, z0 + 74.0),
        (41.5, z0 + 74.0),
        (41.5, z0 + 84.0),
        (45.0, z0 + 84.0),
        (45.0, z1),
        (22.0, z1),
    ]
    jacket = make_revolved_profile(
        jacket_prof, segments=48, axis="z", center=(cx, cy, 0.0), name=f"{name}_water_jacket", material="316LN"
    )

    # 3. Internal Al2O3 HV intermediate-electrode ceramic break sleeve (R=15..21, z=z_bot+46..z_bot+98)
    hv_ceramic = make_tube(
        15.0, 21.0, 52.0, segments=40, axis="z", center=(cx, cy, z_bot + 72.0),
        name=f"{name}_al2o3_hv_break", material="Al2O3",
    )

    # 4. Internal magnetized soft-iron intermediate electrode snout (R=6..14.2, z=z_bot+22..z_bot+45.5)
    inter_prof = [
        (6.0, z_bot + 22.0),
        (11.0, z_bot + 22.0),
        (14.2, z_bot + 30.0),
        (14.2, z_bot + 45.5),
        (9.5, z_bot + 45.5),
        (6.0, z_bot + 28.0),
    ]
    inter_elec = make_revolved_profile(
        inter_prof, segments=36, axis="z", center=(cx, cy, 0.0), name=f"{name}_inter_elec", material="Soft Iron"
    )

    # 5. Top ISO 3669 CF63 cathode/servicing flange (t=17.5 mm -> z_bot+122.5 .. z_bot+140.0)
    top_cf63 = make_cf_flange(
        "CF63",
        bore_id=40.0,
        axis="+z",
        center=(cx, cy, z_top - 8.75),
        name=f"{name}_top_cf63",
        material="316LN",
    )

    # 6. Cathode filament feedthrough cap sitting inside top CF63 bore (z_bot+102..z_bot+136)
    cathode_cap = make_tube(
        4.0, 14.0, 32.0, segments=32, axis="z", center=(cx, cy, z_bot + 118.0),
        name=f"{name}_cathode_feed", material="Al2O3",
    )

    parts = [anode, jacket, hv_ceramic, inter_elec, top_cf63, cathode_cap]

    if with_side_cf40_neg_x:
        # Lateral -X CF40 switchover weld-neck port for 2nd isotope line (X = cx-82 .. cx-45.5)
        cf40_sw = make_cf_weld_neck(
            "CF40",
            neck_length=24.0,
            tube_od=38.0,
            tube_id=32.0,
            axis="-x",
            center=(cx - 76.0, cy, z_bot + 70.0),
            name=f"{name}_switchover_cf40",
            material="316LN",
        )
        parts.append(cf40_sw)

    mesh = merge_solids(parts, name=name, material="316LN")
    scad_feats = [
        ScadFeature("add_tube", {"od": 90.0, "id": 44.0, "h": 102.8}, translate=(0.0, 0.0, 0.6), comment="316LN water-cooled plasma body"),
        ScadFeature("add_cylinder", {"d": 28.0, "d2": 68.0, "h": 18.8}, translate=(0.0, 0.0, -60.6), comment="Mo anode extraction cone"),
        ScadFeature("add_tube", {"od": 42.0, "id": 30.0, "h": 52.0}, translate=(0.0, 0.0, 2.0), comment="Al2O3 HV intermediate insulator"),
        ScadFeature("add_cf_flange", {"size": "CF63", "bore_id": 40.0}, translate=(0.0, 0.0, 61.25), comment="ISO 3669 CF63 cathode flange"),
    ]
    if with_side_cf40_neg_x:
        scad_feats.append(
            ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(-76.0, 0.0, 0.0), rotate=(0.0, -90.0, 0.0), comment="CF40 isotope switchover port")
        )
    return mesh, scad_feats


# ---------------------------------------------------------------------------
# Engineering Thermal & GD&T Verification Suite for S1
# ---------------------------------------------------------------------------
def compute_s1_engineering_checks() -> dict[str, Any]:
    """Compute NIST bakeout/operating thermal clearances & Exp124 GD&T stackups for S1."""
    # 1. 150 C UHV bakeout (423.15 K): S1.3-01 Ti-6Al-4V/Al2O3 bore (88 mm) vs S1.1-03 Mo/Ti stack (84 mm)
    bake_decel_clr = check_cold_clearance(
        "Ti-6Al-4V",
        "Mo",
        nominal_outer_id_mm=88.0,
        nominal_inner_od_mm=84.0,
        t_cold_k=423.15,
        min_required_radial_clearance_mm=1.5,
        outer_id_tol_mm=0.05,
        inner_od_tol_mm=0.02,
    )
    # 2. 150 C bakeout: S1.3-04 Mu-metal shield (ID 114 mm, R_in=57.0) vs S1.5-01 Ti-6Al-4V HDA (OD 110 mm)
    bake_mumetal_clr = check_cold_clearance(
        "Mu-metal",
        "Ti-6Al-4V",
        nominal_outer_id_mm=114.0,
        nominal_inner_od_mm=110.0,
        t_cold_k=423.15,
        min_required_radial_clearance_mm=1.5,
        outer_id_tol_mm=0.20,
        inner_od_tol_mm=0.05,
    )
    # 3. 450 C (723.15 K) S1.7-01 Sb PBN crucible (Al2O3 proxy OD 22 mm) inside 316LN CF40 housing (ID 38 mm)
    oven_clr = check_cold_clearance(
        "316LN",
        "Al2O3",
        nominal_outer_id_mm=38.0,
        nominal_inner_od_mm=22.0,
        t_cold_k=723.15,
        min_required_radial_clearance_mm=5.0,
        outer_id_tol_mm=0.10,
        inner_od_tol_mm=0.10,
    )
    # 4. Exp124 HDA-HiRes concentric hemisphere gap stackup (R2=44.000 - R1=36.000 = 8.000 mm, R0=40.000 mm)
    hda_gap_stack = check_tolerance_stack(
        [
            ToleranceContributor("outer_hemisphere_R2", 44.000, 0.005, -0.005, sign=+1.0),
            ToleranceContributor("inner_hemisphere_R1", 36.000, 0.005, -0.005, sign=-1.0),
            ToleranceContributor("sapphire_standoff_concentricity", 0.000, 0.003, -0.003, sign=+1.0),
        ],
        target_min_mm=7.985,
        target_max_mm=8.015,
    )
    # 5. Column beam-axis lateral coaxiality stackup vs 2.686 mm radial bore margin
    col_coax_stack = check_tolerance_stack(
        [
            ToleranceContributor("S1.1-03_extraction_coax", 0.0, 0.005, -0.005),
            ToleranceContributor("S1.2-01_wien_axis", 0.0, 0.010, -0.010),
            ToleranceContributor("S1.5-01_hda_axis", 0.0, 0.005, -0.005),
            ToleranceContributor("S1.3-02_archB_decel_coax", 0.0, 0.002, -0.002),
            ToleranceContributor("S1.3-01_cf100_column_runout", 0.0, 0.020, -0.020),
        ],
        target_min_mm=-0.050,
        target_max_mm=+0.050,
    )
    return {
        "bakeout_decel_clearance": bake_decel_clr.to_dict(),
        "bakeout_mumetal_clearance": bake_mumetal_clr.to_dict(),
        "s17_450c_oven_clearance": oven_clr.to_dict(),
        "hda_r0_gap_tolerance_stack": hda_gap_stack.to_dict(),
        "column_coaxiality_stack": col_coax_stack.to_dict(),
    }


# ---------------------------------------------------------------------------
# Master S1 Builder: All 23 Physical BOM Parts (S1.1-01 .. S1.7-01)
# ---------------------------------------------------------------------------
def build_s1_parts() -> dict[str, BuiltPart]:
    """Construct all 23 physical solid CAD parts of Subsystem S1 in global coordinates."""
    checks = compute_s1_engineering_checks()
    parts: dict[str, BuiltPart] = {}

    # -----------------------------------------------------------------------
    # S1.1-01: Duoplasmatron Plasma Chamber (31P+ Donor Line, +5 kV, Z=[422.66, 562.66])
    # -----------------------------------------------------------------------
    m_s1101, f_s1101 = _build_duoplasmatron_mesh(0.0, 0.0, 422.66, name="S1.1-01")
    d_s1101 = make_part_design_from_bom(
        "S1.1-01",
        design_tier="CUSTOM_FULL",
        material="316LN",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, 492.66),
        ports=(
            PortInterface("beam_exit_anode", "vacuum", (0.0, 0.0, 422.66), (0.0, 0.0, -1.0), "Mo Anode Ø0.10 mm", mating_part_id="S1.1-03", bore_mm=4.0, od_mm=28.0, frame="global"),
            make_cf_port_interface("CF63", "top_cathode_cf63", (0.0, 0.0, 562.66), (0.0, 0.0, 1.0), bore_override_mm=40.0, frame="global"),
            make_cf_port_interface("CF40", "multi_species_port_pos_y", (0.0, 45.0, 492.66), (0.0, 1.0, 0.0), mating_part_id="S1.7-01", frame="global"),
            PortInterface("ph3_vcr_inlet_neg_y", "gas", (0.0, -45.0, 492.66), (0.0, -1.0, 0.0), "1/4 VCR Male", mating_part_id="S1.1-04", bore_mm=4.6, od_mm=14.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("OD_BODY", 90.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("HEIGHT", 140.0, 0.05, -0.05),
            DimensionCallout("TOP_FLANGE", 113.5, 0.10, -0.10, prefix="CF63 Ø"),
            DimensionCallout("Z_TOP_COL", 562.66, 0.05, -0.05),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.050, diameter_zone=True, datum_primary="B", feature_note="MO ANODE AXIS"),
            GDTFrame("perpendicularity", 0.025, diameter_zone=True, datum_primary="A", feature_note="CF63 FACE"),
            GDTFrame("flatness", 0.015, datum_primary="", feature_note="ANODE SEAT"),
        ),
        scad_params=(("body_od", 90.0), ("height", 140.0), ("top_flange", "CF63"), ("hv_potential_kV", 5.0)),
        notes=("Exp124 locked total column top Z=562.66 mm above Z=0 wafer plane", "Water-cooled 316LN jacket + Mo anode + Al2O3 HV intermediate break"),
        target_mass_kg=7.50,
    )
    parts["S1.1-01"] = BuiltPart(d_s1101, m_s1101, tuple(f_s1101), {"coax_stack": checks["column_coaxiality_stack"]})

    # -----------------------------------------------------------------------
    # S1.1-02: 2nd Duoplasmatron Plasma Chamber (29Si+/28Si+ Isotope Line, +X=165 mm)
    # -----------------------------------------------------------------------
    m_s1102, f_s1102 = _build_duoplasmatron_mesh(165.0, 0.0, 422.66, name="S1.1-02", with_side_cf40_neg_x=True)
    d_s1102 = make_part_design_from_bom(
        "S1.1-02",
        design_tier="CUSTOM_FULL",
        material="316LN",
        surface_finish_ra_um=0.4,
        world_origin_mm=(165.0, 0.0, 492.66),
        ports=(
            make_cf_port_interface("CF63", "top_cathode_cf63", (165.0, 0.0, 562.66), (0.0, 0.0, 1.0), bore_override_mm=40.0, frame="global"),
            make_cf_port_interface("CF40", "switchover_cf40_neg_x", (82.65, 0.0, 492.66), (-1.0, 0.0, 0.0), mating_part_id="S1.1-01", frame="global"),
            PortInterface("sif4_vcr_inlet", "gas", (165.0, -45.0, 492.66), (0.0, -1.0, 0.0), "1/4 VCR Male", mating_part_id="S1.1-04", bore_mm=4.6, od_mm=14.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("OD_BODY", 90.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("HEIGHT", 140.0, 0.05, -0.05),
            DimensionCallout("OFFSET_X", 165.0, 0.10, -0.10),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.050, diameter_zone=True, datum_primary="B", feature_note="ISOTOPE LINE AXIS"),
            GDTFrame("perpendicularity", 0.025, diameter_zone=True, datum_primary="A", feature_note="CF40 SWITCH PORT"),
        ),
        scad_params=(("body_od", 90.0), ("height", 140.0), ("x_offset", 165.0), ("species", "29Si+/28Si+")),
        notes=("Dedicated 2nd SiF4 isotope duoplasmatron line parallel at X=+165 mm (resolves v6 under-instantiation)",),
        target_mass_kg=7.80,
    )
    parts["S1.1-02"] = BuiltPart(d_s1102, m_s1102, tuple(f_s1102), {})

    # -----------------------------------------------------------------------
    # S1.1-03: 3-Electrode 10-15 keV HV Extraction & Condenser Stack (Z=[373.66, 418.66])
    # -----------------------------------------------------------------------
    e_up = make_revolved_profile(
        [(10.0, 407.66), (22.0, 407.66), (42.0, 410.5), (42.0, 418.66), (14.0, 418.66), (10.0, 415.0)],
        segments=48, axis="z", name="S1.1-03_elec_pierce", material="Mo",
    )
    e_mid = make_revolved_profile(
        [(10.0, 389.66), (25.0, 389.66), (42.0, 392.0), (42.0, 400.3), (25.0, 402.66), (10.0, 402.66)],
        segments=48, axis="z", name="S1.1-03_elec_condenser", material="Ti-6Al-4V",
    )
    e_bot = make_revolved_profile(
        [(10.0, 373.66), (42.0, 373.66), (42.0, 381.8), (22.0, 384.66), (10.0, 384.66)],
        segments=48, axis="z", name="S1.1-03_elec_ground", material="Mo",
    )
    ring_lo = make_tube(25.0, 31.0, 4.0, segments=40, axis="z", center=(0.0, 0.0, 387.16), name="S1.1-03_sapphire_lo", material="Sapphire")
    ring_hi = make_tube(25.0, 31.0, 4.0, segments=40, axis="z", center=(0.0, 0.0, 405.16), name="S1.1-03_sapphire_hi", material="Sapphire")
    s1103_parts: list[SolidMesh] = [e_up, e_mid, e_bot, ring_lo, ring_hi]
    for z_ball in (387.16, 405.16):
        for k in range(3):
            ang = math.radians(k * 120.0 + (30.0 if z_ball > 400.0 else 0.0))
            bx, by = 35.5 * math.cos(ang), 35.5 * math.sin(ang)
            s1103_parts.append(
                make_sphere(1.85, u_seg=16, v_seg=10, center=(bx, by, z_ball), name=f"S1.1-03_ball_{int(z_ball)}_{k}", material="Sapphire")
            )
    m_s1103 = merge_solids(s1103_parts, name="S1.1-03", material="Mo")
    d_s1103 = make_part_design_from_bom(
        "S1.1-03",
        design_tier="CUSTOM_FULL",
        material="Mo",
        surface_finish_ra_um=0.2,
        world_origin_mm=(0.0, 0.0, 396.16),
        ports=(
            PortInterface("extract_inlet", "vacuum", (0.0, 0.0, 418.66), (0.0, 0.0, 1.0), "Ø20 mm Bore", mating_part_id="S1.1-01", bore_mm=20.0, od_mm=84.0, frame="global"),
            PortInterface("extract_outlet", "vacuum", (0.0, 0.0, 373.66), (0.0, 0.0, -1.0), "Ø20 mm Bore", mating_part_id="S1.2-01", bore_mm=20.0, od_mm=84.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("OD", 84.0, 0.01, -0.01, prefix="Ø"),
            DimensionCallout("BORE", 20.0, 0.005, -0.005, prefix="Ø"),
            DimensionCallout("STACK_H", 45.0, 0.01, -0.01),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.005, diameter_zone=True, datum_primary="B", feature_note="3-ELECTRODE COAX"),
            GDTFrame("parallelism", 0.005, datum_primary="A", feature_note="INTER-ELECTRODE FACES"),
            GDTFrame("flatness", 0.003, datum_primary="", feature_note="SAPPHIRE SEATS"),
        ),
        scad_params=(("od", 84.0), ("bore", 20.0), ("height", 45.0), ("v_extract_kV", 10.0)),
        notes=("Exp124 10-15 keV 3-electrode Pierce/condenser stack; replaces v6 mis-tagged S1.4 condenser", "6x sapphire centering balls enforce ±5 um coaxiality"),
        target_mass_kg=2.10,
    )
    f_s1103 = (
        ScadFeature("add_tube", {"od": 84.0, "id": 20.0, "h": 11.0}, translate=(0.0, 0.0, 17.0), comment="Upper Pierce extraction electrode"),
        ScadFeature("add_tube", {"od": 84.0, "id": 20.0, "h": 13.0}, translate=(0.0, 0.0, 0.0), comment="Middle Einzel condenser electrode"),
        ScadFeature("add_tube", {"od": 84.0, "id": 20.0, "h": 11.0}, translate=(0.0, 0.0, -17.0), comment="Lower collimator electrode"),
        ScadFeature("add_tube", {"od": 62.0, "id": 50.0, "h": 4.0}, translate=(0.0, 0.0, 9.0), comment="Upper sapphire centering ring"),
        ScadFeature("add_tube", {"od": 62.0, "id": 50.0, "h": 4.0}, translate=(0.0, 0.0, -9.0), comment="Lower sapphire centering ring"),
    )
    parts["S1.1-03"] = BuiltPart(d_s1103, m_s1103, f_s1103, {"bakeout_clearance": checks["bakeout_decel_clearance"]})

    # -----------------------------------------------------------------------
    # S1.1-04: UHV VCR MFC & Dual Gas Manifold (-Y side of Duoplasmatron)
    # -----------------------------------------------------------------------
    man_block = make_rect_plate_with_features(
        92.0, 40.0, 44.0,
        circular_holes=[(-34.0, -12.0, 5.5), (34.0, -12.0, 5.5), (-34.0, 12.0, 5.5), (34.0, 12.0, 5.5)],
        center=(0.0, -116.0, 492.66), name="S1.1-04_vcr_manifold", material="316L",
    )
    mfc1 = make_chamfered_box(36.0, 32.0, 20.0, chamfer=1.5, center=(-24.0, -116.0, 525.0), name="S1.1-04_mfc_ph3", material="316L")
    mfc2 = make_chamfered_box(36.0, 32.0, 20.0, chamfer=1.5, center=(24.0, -116.0, 525.0), name="S1.1-04_mfc_sif4", material="316L")
    vcr_nut = make_cylinder(10.0, 10.0, segments=6, axis="+y", center=(0.0, -90.5, 492.66), name="S1.1-04_vcr_nut", material="316L")
    feed_pipe = make_swept_tube(
        [[0.0, -85.0, 492.66], [0.0, -66.0, 492.66], [0.0, -47.5, 492.66]],
        r_out=6.35, r_in=4.5, segments=20, name="S1.1-04_vcr_feed_tube", material="316L",
    )
    inlet_pipe = make_swept_tube(
        [[-24.0, -136.5, 492.66], [-24.0, -148.0, 492.66], [-24.0, -148.0, 468.0]],
        r_out=4.75, r_in=3.2, segments=16, name="S1.1-04_ph3_inlet", material="316L",
    )
    m_s1104 = merge_solids([man_block, mfc1, mfc2, vcr_nut, feed_pipe, inlet_pipe], name="S1.1-04", material="316L")
    d_s1104 = make_part_design_from_bom(
        "S1.1-04",
        design_tier="COTS_ENV_ICD",
        material="316L",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, -102.0, 492.66),
        ports=(
            PortInterface("vcr_out_to_source", "gas", (0.0, -47.5, 492.66), (0.0, 1.0, 0.0), "1/4 VCR Female", mating_part_id="S1.1-01", bore_mm=9.0, od_mm=12.7, frame="global"),
            PortInterface("vcr_in_from_cabinet", "gas", (-24.0, -148.0, 468.0), (0.0, 0.0, -1.0), "1/4 VCR Double-Walled", mating_part_id="S1.6-01", bore_mm=6.4, od_mm=9.5, frame="global"),
        ),
        dimensions=(
            DimensionCallout("MANIFOLD_W", 92.0, 0.2, -0.2),
            DimensionCallout("VCR_FEED_OD", 12.7, 0.1, -0.1, prefix="Ø"),
            DimensionCallout("MFC_RANGE", 10.0, 0.1, -0.1, unit="sccm", suffix=" sccm"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.050, datum_primary="A", feature_note="VCR SEAL GLAND"),
            GDTFrame("flatness", 0.020, datum_primary="", feature_note="MFC MOUNT FACE"),
        ),
        scad_params=(("manifold_w", 92.0), ("manifold_d", 40.0), ("vcr_od", 12.7)),
        notes=("Electropolished 316L VAR metal-gasket VCR dual PH3/SiF4 manifold; He leak <=1e-10 mbar*L/s",),
        target_mass_kg=2.60,
    )
    f_s1104 = (
        ScadFeature("add_box", {"dx": 92.0, "dy": 40.0, "dz": 44.0}, translate=(0.0, -14.0, 0.0), comment="316L VAR VCR manifold block"),
        ScadFeature("add_box", {"dx": 36.0, "dy": 32.0, "dz": 20.0}, translate=(-24.0, -14.0, 32.5), comment="PH3 0.1-10 sccm MFC"),
        ScadFeature("add_box", {"dx": 36.0, "dy": 32.0, "dz": 20.0}, translate=(24.0, -14.0, 32.5), comment="SiF4 0.1-10 sccm MFC"),
        ScadFeature("add_tube", {"od": 12.7, "id": 9.0, "h": 38.0}, translate=(0.0, 35.0, 0.0), rotate=(90.0, 0.0, 0.0), comment="Coaxial VCR feed tube to S1.1-01"),
    )
    parts["S1.1-04"] = BuiltPart(d_s1104, m_s1104, f_s1104, {})

    # -----------------------------------------------------------------------
    # S1.1-05: Isolated 15 kV HV Arc/Cathode Power Platform (3U Rack Bay 1, U27-U29 per #309)
    # -----------------------------------------------------------------------
    m_s1105, f_s1105, o_s1105 = make_rack_unit_chassis(
        u_start=27,
        u_height=3,
        rear_boss_count=5,
        internal_modules=2,
        material="Al 6061",
        name="S1.1-05",
    )
    d_s1105 = make_part_design_from_bom(
        "S1.1-05",
        design_tier="CUSTOM_FULL",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=o_s1105,
        ports=(
            PortInterface("hv_15kv_out", "electrical", (o_s1105[0], RACK_BAY1_FRONT_Y + 442.5, o_s1105[2]), (0.0, 1.0, 0.0), "20 kV Coax HV", mating_part_id="S1.1-01", od_mm=14.0, frame="global"),
            PortInterface("fiber_ctrl", "optical", (o_s1105[0] - 90.0, RACK_BAY1_FRONT_Y + 442.5, o_s1105[2]), (0.0, 1.0, 0.0), "ST Multimode Fiber", mating_part_id="S1.4-03", od_mm=10.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("RACK_W_X", 482.6, 0.3, -0.3),
            DimensionCallout("HEIGHT_3U", 131.35, 0.3, -0.3),
            DimensionCallout("DEPTH_Y", 430.0, 0.5, -0.5),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-IN FRONT EARS"),
            GDTFrame("flatness", 0.20, datum_primary="", feature_note="RACK RAIL BASE"),
        ),
        scad_params=(("rack_u", 3), ("u_slots", "U27-U29"), ("v_max_kV", 15.0), ("sf6_free", "true")),
        notes=("19-in Rack Bay 1 slots U27-U29 (X=1480.0 mm, front -Y @ -438.0, Z_nat=[746.70, 878.05]); solid SF6-free 15 kV deck",),
        target_mass_kg=12.20,
    )
    parts["S1.1-05"] = BuiltPart(d_s1105, m_s1105, tuple(f_s1105), {})

    # -----------------------------------------------------------------------
    # S1.2-01: Wien ExB Magnetic Pole Shoes & Soft-Iron Return Yoke (Z=[252.66, 367.66])
    # -----------------------------------------------------------------------
    yoke_ring = make_tube(42.0, 55.0, 99.0, segments=48, axis="z", center=(0.0, 0.0, 310.16), name="S1.2-01_iron_yoke", material="Soft Iron")
    fl_bot = make_ring_with_bolt_circle(
        42.0, 55.0, 7.6, pcd=98.0, n_bolts=12, bolt_diameter=5.5, sub_per_side=2,
        axis="z", center=(0.0, 0.0, 256.46), name="S1.2-01_flange_bot", material="Soft Iron",
    )
    fl_top = make_ring_with_bolt_circle(
        42.0, 55.0, 7.6, pcd=98.0, n_bolts=12, bolt_diameter=5.5, sub_per_side=2,
        axis="z", center=(0.0, 0.0, 363.86), name="S1.2-01_flange_top", material="Soft Iron",
    )
    s1201_parts: list[SolidMesh] = [yoke_ring, fl_bot, fl_top]
    for sgn in (-1.0, 1.0):
        # SmCo permanent magnet energizing slab (|X| ∈ [30.2, 40.2], Y ∈ [-11, 11] -> R_corner=41.68 < 42.0!)
        s1201_parts.append(
            make_box(10.0, 22.0, 92.0, center=(sgn * 35.2, 0.0, 310.16), name=f"S1.2-01_smco_{'p' if sgn > 0 else 'n'}", material="SmCo")
        )
        # Tapered Rogowski soft-iron pole shoe (|X| ∈ [18.0, 29.8], Y ∈ [-15, 15], Z ∈ [268, 352])
        s1201_parts.append(
            make_chamfered_box(11.8, 30.0, 84.0, chamfer=2.5, center=(sgn * 23.9, 0.0, 310.16), name=f"S1.2-01_pole_{'p' if sgn > 0 else 'n'}", material="Soft Iron")
        )
    m_s1201 = merge_solids(s1201_parts, name="S1.2-01", material="Soft Iron")
    d_s1201 = make_part_design_from_bom(
        "S1.2-01",
        design_tier="CUSTOM_FULL",
        material="Soft Iron",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, 310.16),
        ports=(
            PortInterface("wien_inlet", "mechanical", (0.0, 0.0, 367.66), (0.0, 0.0, 1.0), "12xM5 PCD 98", mating_part_id="S1.3-01", bore_mm=84.0, od_mm=110.0, pcd_mm=98.0, bolt_count=12, bolt_hole_mm=5.5, frame="global"),
            PortInterface("wien_exit_drift", "mechanical", (0.0, 0.0, 252.66), (0.0, 0.0, -1.0), "12xM5 PCD 98", mating_part_id="S1.2-04", bore_mm=84.0, od_mm=110.0, pcd_mm=98.0, bolt_count=12, bolt_hole_mm=5.5, frame="global"),
        ),
        dimensions=(
            DimensionCallout("OD", 110.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("YOKE_H", 115.0, 0.05, -0.05),
            DimensionCallout("POLE_GAP", 36.0, 0.02, -0.02),
            DimensionCallout("B_FIELD", 0.45, 0.0005, -0.0005, unit="T", suffix=" T"),
        ),
        gdt_frames=(
            GDTFrame("parallelism", 0.010, datum_primary="A", feature_note="POLE SHOE FACES"),
            GDTFrame("concentricity", 0.020, diameter_zone=True, datum_primary="B", feature_note="RETURN YOKE"),
            GDTFrame("perpendicularity", 0.015, datum_primary="A", feature_note="MOUNT FLANGES"),
        ),
        scad_params=(("od", 110.0), ("yoke_h", 115.0), ("pole_gap", 36.0), ("b_tesla", 0.45)),
        notes=("Exp124 0.45 T dipole Wien yoke + SmCo magnets; paired with S1.2-04 drift/slit collar for exact 150 mm total Wien length",),
        target_mass_kg=5.40,
    )
    f_s1201 = (
        ScadFeature("add_tube", {"od": 110.0, "id": 84.0, "h": 115.0}, comment="Soft-iron magnetic return yoke"),
        ScadFeature("add_box", {"dx": 11.8, "dy": 34.0, "dz": 84.0}, translate=(23.9, 0.0, 0.0), comment="+X soft-iron pole shoe"),
        ScadFeature("add_box", {"dx": 11.8, "dy": 34.0, "dz": 84.0}, translate=(-23.9, 0.0, 0.0), comment="-X soft-iron pole shoe"),
        ScadFeature("cut_bolt_circle", {"pcd": 98.0, "bolt_d": 5.5, "count": 12, "h": 120.0}, comment="12xM5 flange bolt circle"),
    )
    parts["S1.2-01"] = BuiltPart(d_s1201, m_s1201, f_s1201, {})

    # -----------------------------------------------------------------------
    # S1.2-02: Wien Electrostatic Deflection Plates & Macor Standoffs (L_w=80.0 mm)
    # -----------------------------------------------------------------------
    s1202_parts: list[SolidMesh] = []
    for sgn in (-1.0, 1.0):
        # OFHC Cu / Mo Rogowski-chamfered E-plate (X ∈ [-14, 14], |Y| ∈ [10, 14], Z ∈ [270, 350])
        s1202_parts.append(
            make_chamfered_box(28.0, 4.0, 80.0, chamfer=0.9, center=(0.0, sgn * 12.0, 310.0), name=f"S1.2-02_eplate_{'p' if sgn > 0 else 'n'}", material="OFHC Cu")
        )
        # 2x Macor HV standoffs per plate (|Y| ∈ [14.2, 23.0], Z = 285 & 335, X = 0)
        for zs in (285.0, 335.0):
            s1202_parts.append(
                make_cylinder(3.2, 8.8, segments=20, axis="y", center=(0.0, sgn * 18.6, zs), name=f"S1.2-02_macor_{'p' if sgn > 0 else 'n'}_{int(zs)}", material="Macor")
            )
    m_s1202 = merge_solids(s1202_parts, name="S1.2-02", material="OFHC Cu")
    d_s1202 = make_part_design_from_bom(
        "S1.2-02",
        design_tier="CUSTOM_FULL",
        material="OFHC Cu",
        surface_finish_ra_um=0.2,
        world_origin_mm=(0.0, 0.0, 310.0),
        ports=(
            PortInterface("eplate_hv_pos", "electrical", (0.0, 23.0, 310.0), (0.0, 1.0, 0.0), "SHV +5 kV Pin", mating_part_id="S1.2-03", od_mm=6.4, frame="global"),
            PortInterface("eplate_hv_neg", "electrical", (0.0, -23.0, 310.0), (0.0, -1.0, 0.0), "SHV -5 kV Pin", mating_part_id="S1.2-03", od_mm=6.4, frame="global"),
        ),
        dimensions=(
            DimensionCallout("PLATE_L", 80.0, 0.02, -0.02),
            DimensionCallout("PLATE_W", 28.0, 0.02, -0.02),
            DimensionCallout("E_GAP", 20.0, 0.01, -0.01),
        ),
        gdt_frames=(
            GDTFrame("parallelism", 0.010, datum_primary="A", feature_note="E-PLATE FACES"),
            GDTFrame("flatness", 0.005, datum_primary="", feature_note="ACTIVE ELECTRODE"),
            GDTFrame("symmetry", 0.010, datum_primary="B", feature_note="BEAM AXIS CENTER"),
        ),
        scad_params=(("plate_l", 80.0), ("plate_w", 28.0), ("e_gap", 20.0), ("v_plate_nom_V", 1348.0)),
        notes=("Exp124 Wien E-field length L_w=80.0 mm orthogonal to 0.45 T B-field (V_plate=1348 V @ 10 keV)", "4.0 mm radial clearance to S1.2-01 pole shoes"),
        target_mass_kg=0.24,
    )
    f_s1202 = (
        ScadFeature("add_box", {"dx": 28.0, "dy": 4.0, "dz": 80.0}, translate=(0.0, 12.0, 0.0), comment="+Y E-field deflection plate"),
        ScadFeature("add_box", {"dx": 28.0, "dy": 4.0, "dz": 80.0}, translate=(0.0, -12.0, 0.0), comment="-Y E-field deflection plate"),
        ScadFeature("add_cylinder", {"d": 6.4, "h": 8.8}, translate=(0.0, 18.6, 25.0), rotate=(90.0, 0.0, 0.0), comment="Macor HV standoff"),
        ScadFeature("add_cylinder", {"d": 6.4, "h": 8.8}, translate=(0.0, -18.6, -25.0), rotate=(90.0, 0.0, 0.0), comment="Macor HV standoff"),
    )
    parts["S1.2-02"] = BuiltPart(d_s1202, m_s1202, f_s1202, {})

    # -----------------------------------------------------------------------
    # S1.2-03: Wien Bipolar Precision E-Field Power Supply (1U Rack Bay 1, U35 per #309)
    # -----------------------------------------------------------------------
    m_s1203, f_s1203, o_s1203 = make_rack_unit_chassis(
        u_start=35,
        u_height=1,
        rear_boss_count=4,
        internal_modules=2,
        material="Al 6061",
        name="S1.2-03",
    )
    d_s1203 = make_part_design_from_bom(
        "S1.2-03",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=o_s1203,
        ports=(
            PortInterface("shv_bipolar_ch1", "electrical", (o_s1203[0] - 40.0, RACK_BAY1_FRONT_Y + 442.5, o_s1203[2]), (0.0, 1.0, 0.0), "SHV-5 ±5 kV", mating_part_id="S1.2-02", od_mm=14.0, frame="global"),
            PortInterface("shv_bipolar_ch2", "electrical", (o_s1203[0] + 40.0, RACK_BAY1_FRONT_Y + 442.5, o_s1203[2]), (0.0, 1.0, 0.0), "SHV-5 ±5 kV", mating_part_id="S1.2-02", od_mm=14.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("RACK_W_X", 482.6, 0.3, -0.3),
            DimensionCallout("HEIGHT_1U", 42.45, 0.3, -0.3),
            DimensionCallout("DEPTH_Y", 430.0, 0.5, -0.5),
        ),
        gdt_frames=(GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-IN EARS"),),
        scad_params=(("rack_u", 1), ("u_slot", "U35"), ("v_bipolar_kV", 5.0), ("noise_mVpp", 5.0)),
        notes=("19-in Rack Bay 1 slot U35 (X=1480.0, front -Y @ -438.0, Z_nat=[1102.30, 1144.75]); dual ±5 kV <5 mVpp bipolar Wien PSU",),
        target_mass_kg=5.60,
    )
    parts["S1.2-03"] = BuiltPart(d_s1203, m_s1203, tuple(f_s1203), {})

    # -----------------------------------------------------------------------
    # S1.2-04: Micrometric Mass-Selection Exit Slits w/ UHV Bellows (Z=[217.66, 251.00])
    # -----------------------------------------------------------------------
    zc_slit = 234.33
    slit_collar = make_ring_with_bolt_circle(
        22.0, 42.0, 33.34, pcd=68.0, n_bolts=12, bolt_diameter=4.5, sub_per_side=2,
        axis="z", center=(0.0, 0.0, zc_slit), name="S1.2-04_drift_collar", material="316LN",
    )
    s1204_parts: list[SolidMesh] = [slit_collar]
    for sgn in (-1.0, 1.0):
        # Precision Mo knife-edge slit jaw inside collar (X ∈ [-10, 10], |Y| ∈ [0.5, 15.5] -> R_corner=18.45 < 22.0!)
        s1204_parts.append(
            make_chamfered_box(20.0, 15.0, 8.5, chamfer=1.2, center=(0.0, sgn * 8.0, zc_slit), name=f"S1.2-04_mo_jaw_{'p' if sgn > 0 else 'n'}", material="Mo")
        )
        # Slim UHV pushrod housing stub (|Y| ∈ [42.5, 70.0], R=8.0 -> Z ∈ [226.3, 242.3], clear of S1.3-04 & S1.2-01!)
        s1204_parts.append(
            make_tube(5.0, 8.0, 27.5, segments=24, axis="y", center=(0.0, sgn * 56.25, zc_slit), name=f"S1.2-04_stem_{'p' if sgn > 0 else 'n'}", material="316LN")
        )
        # ISO 3669 CF16 UHV flange (OD=33.8 mm, t=7.5 mm, |Y| ∈ [70.25, 77.75], Z ∈ [217.43, 251.23])
        s1204_parts.append(
            make_cf_flange(
                "CF16",
                bore_id=14.0,
                axis="+y" if sgn > 0 else "-y",
                center=(0.0, sgn * 74.0, zc_slit),
                name=f"S1.2-04_cf16_{'p' if sgn > 0 else 'n'}",
                material="316LN",
            )
        )
        # True 12-convolution edge-welded 316LN UHV bellows (|Y| ∈ [78.0, 120.0], R=8..13)
        s1204_parts.append(
            make_bellows(
                r_in=8.0, r_out=13.0, length=42.0, n_convolutions=12, wall_thickness=0.15, end_cuff_mm=2.5,
                segments=32, axis="y", center=(0.0, sgn * 99.0, zc_slit), name=f"S1.2-04_bellows_{'p' if sgn > 0 else 'n'}", material="316L",
            )
        )
        # Knurled differential micrometer thimble barrel (|Y| ∈ [120.5, 162.5], R=11.0)
        s1204_parts.append(
            make_cylinder(11.0, 42.0, segments=24, axis="y", center=(0.0, sgn * 141.5, zc_slit), name=f"S1.2-04_micrometer_{'p' if sgn > 0 else 'n'}", material="316LN")
        )
    m_s1204 = merge_solids(s1204_parts, name="S1.2-04", material="316LN")
    d_s1204 = make_part_design_from_bom(
        "S1.2-04",
        design_tier="COTS_ENV_ICD",
        material="316LN",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, zc_slit),
        ports=(
            make_cf_port_interface("CF16", "slit_drive_pos_y", (0.0, 77.75, zc_slit), (0.0, 1.0, 0.0), bore_override_mm=14.0, frame="global"),
            make_cf_port_interface("CF16", "slit_drive_neg_y", (0.0, -77.75, zc_slit), (0.0, -1.0, 0.0), bore_override_mm=14.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("COLLAR_OD", 84.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("COLLAR_H", 33.34, 0.05, -0.05),
            DimensionCallout("SLIT_SPAN", 325.0, 0.5, -0.5),
            DimensionCallout("BELLOWS_L", 42.0, 0.2, -0.2),
        ),
        gdt_frames=(
            GDTFrame("parallelism", 0.002, datum_primary="A", feature_note="MO SLIT BLADES"),
            GDTFrame("perpendicularity", 0.015, datum_primary="B", feature_note="ACTUATOR AXIS"),
        ),
        scad_params=(("collar_od", 84.0), ("bellows_conv", 12), ("slit_min_um", 20.0), ("slit_max_um", 500.0)),
        notes=("Wien lower drift exit mass-selection slit (20-500 um, ±2 um); dual CF16 12-conv edge-welded UHV bellows",),
        target_mass_kg=1.45,
    )
    f_s1204 = (
        ScadFeature("add_tube", {"od": 84.0, "id": 44.0, "h": 33.34}, comment="316LN Wien exit slit collar"),
        ScadFeature("add_cf_flange", {"size": "CF16", "bore_id": 14.0}, translate=(0.0, 74.0, 0.0), rotate=(-90.0, 0.0, 0.0), comment="+Y CF16 bellows drive flange"),
        ScadFeature("add_cf_flange", {"size": "CF16", "bore_id": 14.0}, translate=(0.0, -74.0, 0.0), rotate=(90.0, 0.0, 0.0), comment="-Y CF16 bellows drive flange"),
        ScadFeature("add_box", {"dx": 28.0, "dy": 20.0, "dz": 8.5}, translate=(0.0, 10.5, 0.0), comment="+Y Mo slit blade"),
        ScadFeature("add_box", {"dx": 28.0, "dy": 20.0, "dz": 8.5}, translate=(0.0, -10.5, 0.0), comment="-Y Mo slit blade"),
    )
    parts["S1.2-04"] = BuiltPart(d_s1204, m_s1204, f_s1204, {})

    # -----------------------------------------------------------------------
    # S1.3-01: Brazed Al2O3 / Ti-6Al-4V CF100 Main Decel Ceramic Column Tube (Z=[369.50, 421.30])
    # -----------------------------------------------------------------------
    cf100_bot = make_cf_flange(
        "CF100", bore_id=88.0, axis="-z", center=(0.0, 0.0, 379.40),
        name="S1.3-01_cf100_base", material="Ti-6Al-4V",
    )
    # 25 kV ribbed Al2O3 ceramic HV break cylinder (R_in=44.0, core R=52.0, 3 creepage sheds to R=60.5)
    cer_prof = [
        (44.0, 389.50),
        (52.0, 389.50),
        (60.5, 391.50),
        (60.5, 393.50),
        (52.0, 395.50),
        (60.5, 398.50),
        (60.5, 400.50),
        (52.0, 402.50),
        (60.5, 405.50),
        (60.5, 407.50),
        (52.0, 409.50),
        (52.0, 411.30),
        (44.0, 411.30),
    ]
    cer_break = make_revolved_profile(cer_prof, segments=56, axis="z", name="S1.3-01_al2o3_break", material="Al2O3")
    top_collar = make_ring_with_bolt_circle(
        44.0, 63.0, 9.70, pcd=112.0, n_bolts=12, bolt_diameter=6.6, sub_per_side=2,
        axis="z", center=(0.0, 0.0, 416.45), name="S1.3-01_ti_top_collar", material="Ti-6Al-4V",
    )
    m_s1301 = merge_solids([cf100_bot, cer_break, top_collar], name="S1.3-01", material="Al2O3")
    d_s1301 = make_part_design_from_bom(
        "S1.3-01",
        design_tier="CUSTOM_FULL",
        material="Al2O3",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, 395.40),
        ports=(
            make_cf_port_interface("CF100", "lower_cf100", (0.0, 0.0, 369.50), (0.0, 0.0, -1.0), mating_part_id="S1.2-01", bore_override_mm=88.0, frame="global"),
            PortInterface("upper_ti_collar", "flange", (0.0, 0.0, 421.30), (0.0, 0.0, 1.0), "12xM6 PCD 112", mating_part_id="S1.1-01", bore_mm=88.0, od_mm=126.0, pcd_mm=112.0, bolt_count=12, bolt_hole_mm=6.6, frame="global"),
        ),
        dimensions=(
            DimensionCallout("FLANGE_CF100", 152.0, 0.10, -0.10, prefix="Ø"),
            DimensionCallout("BORE_ID", 88.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("SHED_OD", 121.0, 0.10, -0.10, prefix="Ø"),
            DimensionCallout("HEIGHT", 51.80, 0.05, -0.05),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.020, diameter_zone=True, datum_primary="B", feature_note="CERAMIC BORE"),
            GDTFrame("perpendicularity", 0.020, datum_primary="A", feature_note="CF100 TO COLLAR"),
            GDTFrame("flatness", 0.015, datum_primary="", feature_note="BRAZE FLANGE"),
        ),
        scad_params=(("cf_size", "CF100"), ("bore_id", 88.0), ("hv_rating_kV", 25.0), ("bakeout_C", 150.0)),
        notes=("Brazed 99.7% Al2O3 25 kV ribbed insulator + ISO 3669 CF100 Ti-6Al-4V flange; encloses S1.1-03 w/ 2.0 mm radial vacuum gap",),
        target_mass_kg=3.15,
    )
    f_s1301 = (
        ScadFeature("add_cf_flange", {"size": "CF100", "bore_id": 88.0}, translate=(0.0, 0.0, -16.0), rotate=(180.0, 0.0, 0.0), comment="ISO 3669 CF100 Ti-6Al-4V base flange"),
        ScadFeature("add_tube", {"od": 121.0, "id": 88.0, "h": 21.8}, translate=(0.0, 0.0, 5.0), comment="Ribbed 25 kV Al2O3 HV ceramic break"),
        ScadFeature("add_tube", {"od": 126.0, "id": 88.0, "h": 9.7}, translate=(0.0, 0.0, 21.05), comment="Brazed Ti-6Al-4V upper collar"),
        ScadFeature("cut_bolt_circle", {"pcd": 112.0, "bolt_d": 6.6, "count": 12, "h": 14.0}, translate=(0.0, 0.0, 21.05), comment="12xM6 upper collar bolts"),
    )
    parts["S1.3-01"] = BuiltPart(d_s1301, m_s1301, f_s1301, {"bakeout_clearance": checks["bakeout_decel_clearance"]})

    # -----------------------------------------------------------------------
    # S1.3-02: 10->5 keV Arch-B Electrostatic Deceleration & Transfer Lens (Z=[39.66, 104.66])
    # -----------------------------------------------------------------------
    barrel = make_ring_with_bolt_circle(
        35.0, 42.0, 65.0, pcd=77.0, n_bolts=12, bolt_diameter=4.3, sub_per_side=2,
        axis="z", center=(0.0, 0.0, 72.16), name="S1.3-02_ti_barrel", material="Ti-6Al-4V",
    )
    lens_lo = make_revolved_profile(
        [(14.0, 41.0), (26.0, 41.0), (32.0, 44.0), (32.0, 56.0), (14.0, 56.0)],
        segments=48, axis="z", name="S1.3-02_decel_lo", material="Mo",
    )
    lens_mid = make_revolved_profile(
        [(14.0, 62.0), (32.0, 62.0), (32.0, 82.0), (14.0, 82.0)],
        segments=48, axis="z", name="S1.3-02_einzel_mid", material="Ti-6Al-4V",
    )
    lens_hi = make_revolved_profile(
        [(14.0, 88.0), (32.0, 88.0), (32.0, 100.0), (26.0, 103.0), (14.0, 103.0)],
        segments=48, axis="z", name="S1.3-02_transfer_hi", material="Mo",
    )
    s1302_parts: list[SolidMesh] = [barrel, lens_lo, lens_mid, lens_hi]
    for zb in (50.0, 94.0):
        for k in range(3):
            ang = math.radians(k * 120.0 + (60.0 if zb > 70.0 else 0.0))
            s1302_parts.append(
                make_sphere(1.45, u_seg=14, v_seg=10, center=(33.5 * math.cos(ang), 33.5 * math.sin(ang), zb), name=f"S1.3-02_sapphire_{int(zb)}_{k}", material="Sapphire")
            )
    m_s1302 = merge_solids(s1302_parts, name="S1.3-02", material="Ti-6Al-4V")
    d_s1302 = make_part_design_from_bom(
        "S1.3-02",
        design_tier="CUSTOM_FULL",
        material="Ti-6Al-4V",
        surface_finish_ra_um=0.2,
        world_origin_mm=(0.0, 0.0, 72.16),
        ports=(
            PortInterface("decel_outlet_to_s2", "vacuum", (0.0, 0.0, 39.66), (0.0, 0.0, -1.0), "Ø28.0 mm Clear Bore", mating_part_id="S2.5-02", bore_mm=28.0, od_mm=84.0, pcd_mm=77.0, bolt_count=12, bolt_hole_mm=4.3, frame="global"),
            PortInterface("transfer_inlet_from_hda", "vacuum", (0.0, 0.0, 104.66), (0.0, 0.0, 1.0), "Ø28.0 mm Clear Bore", mating_part_id="S1.5-02", bore_mm=28.0, od_mm=84.0, pcd_mm=77.0, bolt_count=12, bolt_hole_mm=4.3, frame="global"),
        ),
        dimensions=(
            DimensionCallout("OD", 84.0, 0.01, -0.01, prefix="Ø"),
            DimensionCallout("CLEAR_BORE", 28.0, 0.005, -0.005, prefix="Ø"),
            DimensionCallout("HEIGHT", 65.0, 0.01, -0.01),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.002, diameter_zone=True, datum_primary="B", feature_note="3-ELEMENT OPTIC BORE"),
            GDTFrame("perpendicularity", 0.005, datum_primary="A", feature_note="MOUNT FACES"),
            GDTFrame("cylindricity", 0.002, datum_primary="", feature_note="Ø28 BEAM BORE"),
        ),
        scad_params=(("od", 84.0), ("bore", 28.0), ("height", 65.0), ("e_land_keV", 5.0)),
        notes=("Exp124 Arch-B 10->5 keV telecentric deceleration & transfer lens (Ø28 mm bore -> 2.686 mm margin to 22.63 mm diag)", "Replaces legacy v6 S1.6 transfer-lens alias"),
        target_mass_kg=2.60,
    )
    f_s1302 = (
        ScadFeature("add_tube", {"od": 84.0, "id": 70.0, "h": 65.0}, comment="Ti-6Al-4V precision outer optical barrel"),
        ScadFeature("add_tube", {"od": 64.0, "id": 28.0, "h": 15.0}, translate=(0.0, 0.0, -23.66), comment="Lower Mo decel electrode"),
        ScadFeature("add_tube", {"od": 64.0, "id": 28.0, "h": 20.0}, translate=(0.0, 0.0, 0.0), comment="Middle Einzel focus electrode"),
        ScadFeature("add_tube", {"od": 64.0, "id": 28.0, "h": 15.0}, translate=(0.0, 0.0, 23.34), comment="Upper Mo transfer electrode"),
        ScadFeature("cut_bolt_circle", {"pcd": 77.0, "bolt_d": 4.3, "count": 12, "h": 68.0}, comment="12xM4 optical barrel mounting circle"),
    )
    parts["S1.3-02"] = BuiltPart(d_s1302, m_s1302, f_s1302, {"coax_stack": checks["column_coaxiality_stack"]})

    # -----------------------------------------------------------------------
    # S1.3-03: Precision Column HV Divider & Active Ripple Filter (1U Rack Bay 1, U34 per #309)
    # -----------------------------------------------------------------------
    m_s1303, f_s1303, o_s1303 = make_rack_unit_chassis(
        u_start=34,
        u_height=1,
        rear_boss_count=4,
        internal_modules=2,
        material="Al 6061",
        name="S1.3-03",
    )
    d_s1303 = make_part_design_from_bom(
        "S1.3-03",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=o_s1303,
        ports=(
            PortInterface("hv_divider_out", "electrical", (o_s1303[0], RACK_BAY1_FRONT_Y + 442.5, o_s1303[2]), (0.0, 1.0, 0.0), "SHV-10 5.000 kV", mating_part_id="S1.3-02", od_mm=14.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("RACK_W_X", 482.6, 0.3, -0.3),
            DimensionCallout("HEIGHT_1U", 42.45, 0.3, -0.3),
            DimensionCallout("V_LAND", 5.000, 0.0005, -0.0005, unit="kV", suffix=" kV", decimals=3),
        ),
        gdt_frames=(GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-IN EARS"),),
        scad_params=(("rack_u", 1), ("u_slot", "U34"), ("v_land_kV", 5.0), ("dE_over_E", 0.0001)),
        notes=("19-in Rack Bay 1 slot U34 (X=1480.0, front -Y @ -438.0, Z_nat=[1057.85, 1100.30]); oil-free Caddock/Vishay HV divider + active ripple filter",),
        target_mass_kg=5.60,
    )
    parts["S1.3-03"] = BuiltPart(d_s1303, m_s1303, tuple(f_s1303), {})

    # -----------------------------------------------------------------------
    # S1.3-04: Dual-Layer Annealed Mu-Metal Magnetic Column Shield (Lower & Upper per #309)
    # -----------------------------------------------------------------------
    # Lower dual-layer shield enclosing S1.3-02 (Z ∈ [42.0, 104.0], R1=45..47, R2=52..54)
    lo_in = make_tube(45.0, 47.0, 62.0, segments=48, axis="z", center=(0.0, 0.0, 73.0), name="S1.3-04_lo_inner", material="Mu-metal")
    lo_out = make_tube(52.0, 54.0, 62.0, segments=48, axis="z", center=(0.0, 0.0, 73.0), name="S1.3-04_lo_outer", material="Mu-metal")
    # Upper dual-layer shield enclosing S1.5-01 HDA (Z ∈ [150.0, 215.0], R1=57.0..58.5, R2=60.5..62.0 -> +2.0 mm clear of both S1.5-01 R=55 & S5.1-02 CF250 R_in=64!)
    hi_in = make_tube(57.0, 58.5, 65.0, segments=56, axis="z", center=(0.0, 0.0, 182.5), name="S1.3-04_hi_inner", material="Mu-metal")
    hi_out = make_tube(60.5, 62.0, 65.0, segments=56, axis="z", center=(0.0, 0.0, 182.5), name="S1.3-04_hi_outer", material="Mu-metal")
    s1304_parts: list[SolidMesh] = [lo_in, lo_out, hi_in, hi_out]
    # Non-magnetic Ti-6Al-4V inter-layer radial spacer lugs between inner & outer mu-metal shells
    for z_sp, r_mid, dr in ((46.0, 49.5, 4.6), (100.0, 49.5, 4.6), (154.0, 59.5, 1.6), (211.0, 59.5, 1.6)):
        for k in range(4):
            ang = math.radians(45.0 + k * 90.0)
            s1304_parts.append(
                make_cylinder(
                    2.0, dr, segments=12, axis=(math.cos(ang), math.sin(ang), 0.0),
                    center=(r_mid * math.cos(ang), r_mid * math.sin(ang), z_sp),
                    name=f"S1.3-04_sp_{int(z_sp)}_{k}", material="Ti-6Al-4V",
                )
            )
    m_s1304 = merge_solids(s1304_parts, name="S1.3-04", material="Mu-metal")
    d_s1304 = make_part_design_from_bom(
        "S1.3-04",
        design_tier="CUSTOM_FULL",
        material="Mu-metal",
        surface_finish_ra_um=0.8,
        world_origin_mm=(0.0, 0.0, 128.50),
        ports=(
            PortInterface("lower_shield_bore", "mechanical", (0.0, 0.0, 42.0), (0.0, 0.0, -1.0), "Dual-Wall Ø90/Ø108", mating_part_id="S1.3-02", bore_mm=90.0, od_mm=108.0, frame="global"),
            PortInterface("upper_shield_bore", "mechanical", (0.0, 0.0, 215.0), (0.0, 0.0, 1.0), "Dual-Wall Ø114/Ø124", mating_part_id="S1.5-01", bore_mm=114.0, od_mm=124.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("HI_OUTER_OD", 124.0, 0.2, -0.2, prefix="Ø"),
            DimensionCallout("HI_INNER_ID", 114.0, 0.2, -0.2, prefix="Ø"),
            DimensionCallout("LO_OUTER_OD", 108.0, 0.2, -0.2, prefix="Ø"),
            DimensionCallout("HI_AIR_GAP", 2.0, 0.1, -0.1),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.20, diameter_zone=True, datum_primary="B", feature_note="DUAL MU-METAL SHELLS"),
            GDTFrame("cylindricity", 0.15, datum_primary="", feature_note="H2 ANNEALED CYL"),
        ),
        scad_params=(("hi_od", 124.0), ("hi_id", 114.0), ("lo_od", 108.0), ("lo_id", 90.0), ("attenuation_dB", 40.0)),
        notes=("Hydrogen-annealed NiFe 80% dual-layer magnetic shield (>=40 dB, <1 uT); upper R=57.0..58.5 / 60.5..62.0 clears S1.5-01 (R=55) & S5.1-02 CF250 (R_in=64) by +2.0 mm",),
        target_mass_kg=2.10,
    )
    f_s1304 = (
        ScadFeature("add_tube", {"od": 108.0, "id": 104.0, "h": 62.0}, translate=(0.0, 0.0, -55.5), comment="Lower outer Mu-metal shield"),
        ScadFeature("add_tube", {"od": 94.0, "id": 90.0, "h": 62.0}, translate=(0.0, 0.0, -55.5), comment="Lower inner Mu-metal shield"),
        ScadFeature("add_tube", {"od": 124.0, "id": 121.0, "h": 65.0}, translate=(0.0, 0.0, 54.0), comment="Upper HDA outer Mu-metal shield (R=60.5..62.0)"),
        ScadFeature("add_tube", {"od": 117.0, "id": 114.0, "h": 65.0}, translate=(0.0, 0.0, 54.0), comment="Upper HDA inner Mu-metal shield (R=57.0..58.5)"),
    )
    parts["S1.3-04"] = BuiltPart(d_s1304, m_s1304, f_s1304, {"bakeout_clearance": checks["bakeout_mumetal_clearance"]})

    # -----------------------------------------------------------------------
    # S1.3-05: Differential Pumping Aperture Diaphragm & CF63 Intermediate Chamber (-X)
    # -----------------------------------------------------------------------
    z_dp = 482.0
    dp_body = make_tube(38.0, 43.0, 94.0, segments=48, axis="x", center=(-119.0, 0.0, z_dp), name="S1.3-05_chamber_body", material="316LN")
    dp_cf63 = make_cf_flange("CF63", bore_id=63.5, axis="-x", center=(-176.0, 0.0, z_dp), name="S1.3-05_cf63_pump", material="316LN")
    dp_cf40 = make_cf_flange("CF40", bore_id=38.0, axis="+x", center=(-64.65, 0.0, z_dp), name="S1.3-05_cf40_col", material="316LN")
    # Precision internal Molybdenum differential pumping diaphragm (Ø74 mm disc, Ø2.0 mm orifice)
    mo_diaph = make_revolved_profile(
        [(1.0, -3.0), (6.0, -3.0), (14.0, -1.5), (37.0, -1.5), (37.0, 1.5), (14.0, 1.5), (6.0, 3.0), (1.0, 3.0)],
        segments=40, axis="x", center=(-112.0, 0.0, z_dp), name="S1.3-05_mo_diaphragm", material="Mo",
    )
    # Top CF16 pressure-gauge port flange
    dp_cf16 = make_cf_flange("CF16", bore_id=14.0, axis="+z", center=(-119.0, 0.0, z_dp + 48.0), name="S1.3-05_cf16_gauge", material="316LN")
    m_s1305 = merge_solids([dp_body, dp_cf63, dp_cf40, mo_diaph, dp_cf16], name="S1.3-05", material="316LN")
    d_s1305 = make_part_design_from_bom(
        "S1.3-05",
        design_tier="CUSTOM_FULL",
        material="316LN",
        surface_finish_ra_um=0.4,
        world_origin_mm=(-121.0, 0.0, z_dp),
        ports=(
            make_cf_port_interface("CF63", "diff_pump_cf63_neg_x", (-184.75, 0.0, z_dp), (-1.0, 0.0, 0.0), frame="global"),
            make_cf_port_interface("CF40", "source_mate_cf40_pos_x", (-58.30, 0.0, z_dp), (1.0, 0.0, 0.0), mating_part_id="S1.1-01", frame="global"),
            make_cf_port_interface("CF16", "gauge_port_cf16_top", (-119.0, 0.0, z_dp + 51.75), (0.0, 0.0, 1.0), frame="global"),
        ),
        dimensions=(
            DimensionCallout("FLANGE_CF63", 113.5, 0.10, -0.10, prefix="Ø"),
            DimensionCallout("LENGTH_X", 126.45, 0.10, -0.10),
            DimensionCallout("DIAPH_ORIFICE", 2.00, 0.05, -0.05, prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.050, diameter_zone=True, datum_primary="B", feature_note="MO APERTURE ORIFICE"),
            GDTFrame("parallelism", 0.030, datum_primary="A", feature_note="CF63 TO CF40 FACES"),
        ),
        scad_params=(("chamber_od", 86.0), ("diaph_bore", 2.0), ("pressure_ratio", 1000.0)),
        notes=("1000x differential pumping stage (1e-6 mbar source -> 1e-9 mbar UHV column); Mo conductance diaphragm + CF63 pump port",),
        target_mass_kg=3.40,
    )
    f_s1305 = (
        ScadFeature("add_tube", {"od": 86.0, "id": 76.0, "h": 94.0}, translate=(2.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="316LN CF63 intermediate chamber"),
        ScadFeature("add_cf_flange", {"size": "CF63"}, translate=(-55.0, 0.0, 0.0), rotate=(0.0, -90.0, 0.0), comment="ISO 3669 CF63 differential pump flange"),
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(56.35, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="ISO 3669 CF40 source-side flange"),
        ScadFeature("add_tube", {"od": 74.0, "id": 2.0, "h": 3.0}, translate=(9.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="Mo Ø2.0 mm differential pumping diaphragm"),
    )
    parts["S1.3-05"] = BuiltPart(d_s1305, m_s1305, f_s1305, {})

    # -----------------------------------------------------------------------
    # S1.4-01: 2x Retractable UHV Faraday Cups w/ -100 V Suppressor & Bellows (±X, Z=255.0)
    # -----------------------------------------------------------------------
    z_fc = 255.0
    s1401_parts: list[SolidMesh] = []
    for sgn in (-1.0, 1.0):
        tag = "pos_x" if sgn > 0 else "neg_x"
        # Suppressor ring (-100 V secondary electron guard, |X| ∈ [58.0, 62.5], R=8.5..12.5)
        s1401_parts.append(
            make_tube(8.5, 12.5, 4.5, segments=32, axis="x", center=(sgn * 60.25, 0.0, z_fc), name=f"S1.4-01_supp_{tag}", material="OFHC Cu")
        )
        # Al2O3 HV suppressor insulator ring (|X| ∈ [63.0, 65.5], R=9.0..12.5)
        s1401_parts.append(
            make_tube(9.0, 12.5, 2.5, segments=28, axis="x", center=(sgn * 64.25, 0.0, z_fc), name=f"S1.4-01_insul_{tag}", material="Al2O3")
        )
        # Deep OFHC Faraday cup collector barrel (|X| ∈ [66.0, 86.0], closed rear end)
        cup_prof = [
            (8.0, -10.0), (11.5, -10.0), (11.5, 10.0), (0.0, 10.0), (0.0, 7.0), (8.0, 7.0),
        ]
        s1401_parts.append(
            make_revolved_profile(
                cup_prof, segments=32, axis="+x" if sgn > 0 else "-x",
                center=(sgn * 76.0, 0.0, z_fc), name=f"S1.4-01_cup_{tag}", material="OFHC Cu",
            )
        )
        # Internal conical pyrolytic graphite low-backscatter beam trap inside cup
        s1401_parts.append(
            make_cylinder(
                7.2, 8.0, r_top=1.5, segments=24, axis="-x" if sgn > 0 else "+x",
                center=(sgn * 78.0, 0.0, z_fc), name=f"S1.4-01_graphite_{tag}", material="Graphite",
            )
        )
        # ISO 3669 CF40 mounting flange (OD=69.5 mm -> Z ∈ [220.25, 289.75], |X| ∈ [88.0, 100.7])
        s1401_parts.append(
            make_cf_flange(
                "CF40", bore_id=26.0, axis="-x" if sgn > 0 else "+x",
                center=(sgn * 94.35, 0.0, z_fc), name=f"S1.4-01_cf40_{tag}", material="316LN",
            )
        )
        # 14-convolution edge-welded 316LN UHV linear bellows (|X| ∈ [101.2, 155.2])
        s1401_parts.append(
            make_bellows(
                r_in=10.0, r_out=16.0, length=54.0, n_convolutions=14, wall_thickness=0.15, end_cuff_mm=3.0,
                segments=32, axis="x", center=(sgn * 128.2, 0.0, z_fc), name=f"S1.4-01_bellows_{tag}", material="316L",
            )
        )
        # Pneumatic linear actuator cylinder + triax readout terminal (|X| ∈ [156.0, 226.0])
        s1401_parts.append(
            make_cylinder(19.0, 62.0, segments=32, axis="x", center=(sgn * 187.0, 0.0, z_fc), name=f"S1.4-01_pneumatic_{tag}", material="Al 6061")
        )
        s1401_parts.append(
            make_cylinder(6.0, 8.0, segments=16, axis="x", center=(sgn * 222.5, 0.0, z_fc), name=f"S1.4-01_triax_{tag}", material="316LN")
        )
    m_s1401 = merge_solids(s1401_parts, name="S1.4-01", material="OFHC Cu")
    d_s1401 = make_part_design_from_bom(
        "S1.4-01",
        design_tier="CUSTOM_FULL",
        material="OFHC Cu",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, z_fc),
        ports=(
            make_cf_port_interface("CF40", "fc1_cf40_pos_x", (88.0, 0.0, z_fc), (-1.0, 0.0, 0.0), bore_override_mm=26.0, frame="global"),
            make_cf_port_interface("CF40", "fc2_cf40_neg_x", (-88.0, 0.0, z_fc), (1.0, 0.0, 0.0), bore_override_mm=26.0, frame="global"),
            PortInterface("triax_out_pos_x", "electrical", (226.5, 0.0, z_fc), (1.0, 0.0, 0.0), "3-Lug Triax BNC", mating_part_id="S1.4-02", od_mm=12.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("CUP_OD", 23.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("FLANGE_CF40", 69.5, 0.10, -0.10, prefix="Ø"),
            DimensionCallout("STROKE", 50.0, 0.5, -0.5),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.050, diameter_zone=True, datum_primary="B", feature_note="CUP & SUPPRESSOR"),
            GDTFrame("perpendicularity", 0.025, datum_primary="A", feature_note="CF40 SEAL FACE"),
        ),
        scad_params=(("qty_cups", 2), ("suppressor_V", -100.0), ("bellows_conv", 14), ("cf_size", "CF40")),
        notes=("2x retractable UHV Faraday cups (1 fA-10 uA) w/ graphite traps, -100 V suppressors, CF40 14-conv bellows & pneumatic actuators",),
        target_mass_kg=2.90,
    )
    f_s1401 = (
        ScadFeature("add_cf_flange", {"size": "CF40", "bore_id": 26.0}, translate=(94.35, 0.0, 0.0), rotate=(0.0, -90.0, 0.0), comment="+X CF40 Faraday cup flange"),
        ScadFeature("add_cf_flange", {"size": "CF40", "bore_id": 26.0}, translate=(-94.35, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="-X CF40 Faraday cup flange"),
        ScadFeature("add_cylinder", {"d": 23.0, "h": 20.0}, translate=(76.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="+X OFHC Faraday cup"),
        ScadFeature("add_cylinder", {"d": 23.0, "h": 20.0}, translate=(-76.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="-X OFHC Faraday cup"),
    )
    parts["S1.4-01"] = BuiltPart(d_s1401, m_s1401, f_s1401, {})

    # -----------------------------------------------------------------------
    # S1.4-02: 2x Femtoamp / Picoammeter Electrometers (1U Rack Bay 1, U33 per #309)
    # -----------------------------------------------------------------------
    m_s1402, f_s1402, o_s1402 = make_rack_unit_chassis(
        u_start=33,
        u_height=1,
        rear_boss_count=4,
        internal_modules=2,
        material="Al 6061",
        name="S1.4-02",
    )
    d_s1402 = make_part_design_from_bom(
        "S1.4-02",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=o_s1402,
        ports=(
            PortInterface("triax_in_ch1", "electrical", (o_s1402[0] - 60.0, RACK_BAY1_FRONT_Y + 442.5, o_s1402[2]), (0.0, 1.0, 0.0), "3-Lug Triax 10 fA", mating_part_id="S1.4-01", od_mm=14.0, frame="global"),
            PortInterface("triax_in_ch2", "electrical", (o_s1402[0] + 60.0, RACK_BAY1_FRONT_Y + 442.5, o_s1402[2]), (0.0, 1.0, 0.0), "3-Lug Triax 10 fA", mating_part_id="S1.4-01", od_mm=14.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("RACK_W_X", 482.6, 0.3, -0.3),
            DimensionCallout("HEIGHT_1U", 42.45, 0.3, -0.3),
            DimensionCallout("DEPTH_Y", 430.0, 0.5, -0.5),
        ),
        gdt_frames=(GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-IN EARS"),),
        scad_params=(("rack_u", 1), ("u_slot", "U33"), ("qty_units", 2), ("resolution_fA", 10.0)),
        notes=("19-in Rack Bay 1 slot U33 (X=1480.0, front -Y @ -438.0, Z_nat=[1013.40, 1055.85]); dual half-rack Keithley 6485/6517-class electrometers",),
        target_mass_kg=5.60,
    )
    parts["S1.4-02"] = BuiltPart(d_s1402, m_s1402, tuple(f_s1402), {})

    # -----------------------------------------------------------------------
    # S1.4-03: Closed-Loop Beam Dose PID Controller & Fast Valve Driver (1U Rack Bay 1, U32 per #309)
    # -----------------------------------------------------------------------
    m_s1403, f_s1403, o_s1403 = make_rack_unit_chassis(
        u_start=32,
        u_height=1,
        rear_boss_count=4,
        internal_modules=1,
        material="Al 6061",
        name="S1.4-03",
    )
    d_s1403 = make_part_design_from_bom(
        "S1.4-03",
        design_tier="CUSTOM_FULL",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=o_s1403,
        ports=(
            PortInterface("pid_feedback_bus", "electrical", (o_s1403[0], RACK_BAY1_FRONT_Y + 442.5, o_s1403[2]), (0.0, 1.0, 0.0), "EtherCAT / BNC", mating_part_id="S1.1-05", od_mm=14.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("RACK_W_X", 482.6, 0.3, -0.3),
            DimensionCallout("HEIGHT_1U", 42.45, 0.3, -0.3),
            DimensionCallout("DEPTH_Y", 430.0, 0.5, -0.5),
        ),
        gdt_frames=(GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-IN EARS"),),
        scad_params=(("rack_u", 1), ("u_slot", "U32"), ("response_ms", 1.0), ("dose_rms_pct", 1.0)),
        notes=("19-in Rack Bay 1 slot U32 (X=1480.0, front -Y @ -438.0, Z_nat=[968.95, 1011.40]); FPGA/PLC closed-loop beam-dose PID controller",),
        target_mass_kg=5.60,
    )
    parts["S1.4-03"] = BuiltPart(d_s1403, m_s1403, tuple(f_s1403), {})

    # -----------------------------------------------------------------------
    # S1.5-01: True R0=40.000 mm Concentric HDA-HiRes Hemispheres + Jost Lenses (Z=[114.66, 209.66])
    # -----------------------------------------------------------------------
    zc_hda = 162.16
    cx_hda = -5.0
    # True concentric hemispheres: R1_outer = 36.000 mm, R2_inner = 44.000 mm -> exact R0 = 40.000 mm!
    hemi_in = make_hemisphere_shell(
        r_in=33.5, r_out=36.0, segments=56, lat_steps=18, axis="+x",
        center=(cx_hda, 0.0, zc_hda), name="S1.5-01_hemi_inner_R36", material="OFHC Cu",
    )
    hemi_out = make_hemisphere_shell(
        r_in=44.0, r_out=46.5, segments=56, lat_steps=18, axis="+x",
        center=(cx_hda, 0.0, zc_hda), name="S1.5-01_hemi_outer_R44", material="OFHC Cu",
    )
    # Equatorial Au-plated OFHC baseplate at X ∈ [-9.5, -5.5] with dual Ø6.0 mm entrance/exit beam apertures
    eq_plate = make_rect_plate_with_features(
        88.0, 88.0, 4.0,
        circular_holes=[(-40.0, 0.0, 6.0), (40.0, 0.0, 6.0)],
        axis="x", center=(-7.5, 0.0, zc_hda), name="S1.5-01_equatorial_plate", material="OFHC Cu",
    )
    # Entrance (top, Z=zc_hda+40=202.16) & Exit (bottom, Z=zc_hda-40=122.16) multi-element Jost lenses
    jost_in = make_tube(3.2, 5.8, 28.0, segments=28, axis="x", center=(-24.0, 0.0, zc_hda + 40.0), name="S1.5-01_jost_entrance", material="Ti-6Al-4V")
    jost_out = make_tube(3.2, 5.8, 28.0, segments=28, axis="x", center=(-24.0, 0.0, zc_hda - 40.0), name="S1.5-01_jost_exit", material="Ti-6Al-4V")
    # 4x Al2O3 HV standoff insulator posts cleanly connecting equatorial baseplate to outer housing rim
    s1501_parts: list[SolidMesh] = [hemi_in, hemi_out, eq_plate, jost_in, jost_out]
    for sy in (-32.0, 32.0):
        for sz in (-22.0, 22.0):
            s1501_parts.append(
                make_cylinder(2.5, 6.0, segments=16, axis="x", center=(-13.0, sy, zc_hda + sz), name=f"S1.5-01_hv_post_{int(sy)}_{int(sz)}", material="Al2O3")
            )
    # Precision Ti-6Al-4V UHV outer cylindrical analyzer housing (R=51..55 -> OD=110.0 mm, h=95.0 mm)
    hda_housing = make_ring_with_bolt_circle(
        51.0, 55.0, 95.0, pcd=106.0, n_bolts=16, bolt_diameter=3.2, sub_per_side=2,
        axis="z", center=(0.0, 0.0, zc_hda), name="S1.5-01_ti_housing", material="Ti-6Al-4V",
    )
    s1501_parts.append(hda_housing)
    m_s1501 = merge_solids(s1501_parts, name="S1.5-01", material="Ti-6Al-4V")
    d_s1501 = make_part_design_from_bom(
        "S1.5-01",
        design_tier="CUSTOM_FULL",
        material="Ti-6Al-4V",
        surface_finish_ra_um=0.1,
        world_origin_mm=(0.0, 0.0, zc_hda),
        ports=(
            PortInterface("hda_inlet_top", "vacuum", (0.0, 0.0, 209.66), (0.0, 0.0, 1.0), "Ø16 mm Pass Port", mating_part_id="S1.5-02", bore_mm=16.0, od_mm=110.0, pcd_mm=106.0, bolt_count=16, bolt_hole_mm=3.2, frame="global"),
            PortInterface("hda_outlet_bot", "vacuum", (0.0, 0.0, 114.66), (0.0, 0.0, -1.0), "Ø16 mm Pass Port", mating_part_id="S1.5-02", bore_mm=16.0, od_mm=110.0, pcd_mm=106.0, bolt_count=16, bolt_hole_mm=3.2, frame="global"),
        ),
        dimensions=(
            DimensionCallout("HDA_R0", 40.000, 0.005, -0.005, prefix="R", decimals=3),
            DimensionCallout("HEMI_R1", 36.000, 0.005, -0.005, prefix="R", decimals=3),
            DimensionCallout("HEMI_R2", 44.000, 0.005, -0.005, prefix="R", decimals=3),
            DimensionCallout("HOUSING_OD", 110.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("HEIGHT", 95.0, 0.05, -0.05),
        ),
        gdt_frames=(
            GDTFrame("profile_surface", 0.005, datum_primary="A", datum_secondary="B", feature_note="HEMISPHERES R36/R44"),
            GDTFrame("concentricity", 0.005, diameter_zone=True, datum_primary="B", feature_note="CONCENTRIC R0=40"),
            GDTFrame("perpendicularity", 0.010, datum_primary="A", feature_note="EQUATORIAL PLATE"),
        ),
        scad_params=(("r0_mm", 40.0), ("r_inner_mm", 36.0), ("r_outer_mm", 44.0), ("e_pass_eV", 100.0), ("dE_fwhm_eV", 0.453)),
        notes=("Exp124 HDA-HiRes true concentric hemispheres (R1=36, R2=44 -> R0=40.000 mm, dE_FWHM=0.453 eV) + Jost lenses",),
        target_mass_kg=5.20,
    )
    f_s1501 = (
        ScadFeature("add_tube", {"od": 110.0, "id": 102.0, "h": 95.0}, comment="Ti-6Al-4V UHV HDA outer housing"),
        ScadFeature("add_box", {"dx": 4.0, "dy": 88.0, "dz": 88.0}, translate=(-7.5, 0.0, 0.0), comment="Equatorial Au-OFHC Jost baseplate"),
        ScadFeature("add_cylinder", {"d": 11.6, "h": 28.0}, translate=(-24.0, 0.0, 40.0), rotate=(0.0, 90.0, 0.0), comment="Jost entrance deceleration lens"),
        ScadFeature("add_cylinder", {"d": 11.6, "h": 28.0}, translate=(-24.0, 0.0, -40.0), rotate=(0.0, 90.0, 0.0), comment="Jost exit acceleration lens"),
        ScadFeature("cut_bolt_circle", {"pcd": 106.0, "bolt_d": 3.2, "count": 16, "h": 98.0}, comment="16xM3 housing end-ring bolts"),
    )
    parts["S1.5-01"] = BuiltPart(
        d_s1501, m_s1501, f_s1501,
        {"hda_gap_stack": checks["hda_r0_gap_tolerance_stack"], "bakeout_mumetal": checks["bakeout_mumetal_clearance"]},
    )

    # -----------------------------------------------------------------------
    # S1.5-02: Piezo-Actuated HDA Entrance & Exit Energy Slits (Z=[106.16, 113.16] & [210.66, 216.66])
    # -----------------------------------------------------------------------
    s1502_parts: list[SolidMesh] = []
    for tag, z_mid, h_cas in (("exit_lo", 109.66, 7.0), ("entr_hi", 213.66, 6.0)):
        # Precision slotted flexure carrier ring (R=20..43 mm)
        ring = make_ring_with_bolt_circle(
            20.0, 43.0, h_cas, pcd=76.0, n_bolts=8, bolt_diameter=3.4, sub_per_side=2,
            axis="z", center=(0.0, 0.0, z_mid), name=f"S1.5-02_ring_{tag}", material="Invar-36",
        )
        s1502_parts.append(ring)
        # Dual Mo precision energy-defining slit blades (5-50 um aperture)
        for sgn in (-1.0, 1.0):
            s1502_parts.append(
                make_chamfered_box(
                    16.0, 14.0, h_cas - 2.0, chamfer=0.6,
                    center=(sgn * 8.4, 0.0, z_mid), name=f"S1.5-02_blade_{tag}_{'p' if sgn > 0 else 'n'}", material="Mo",
                )
            )
            # Compact UHV piezo stack actuator flanking blades along ±Y
            s1502_parts.append(
                make_box(
                    10.0, 6.0, h_cas - 2.2,
                    center=(0.0, sgn * 14.0, z_mid), name=f"S1.5-02_piezo_{tag}_{'p' if sgn > 0 else 'n'}", material="Al2O3",
                )
            )
    m_s1502 = merge_solids(s1502_parts, name="S1.5-02", material="Mo")
    d_s1502 = make_part_design_from_bom(
        "S1.5-02",
        design_tier="CUSTOM_FULL",
        material="Mo",
        surface_finish_ra_um=0.1,
        world_origin_mm=(0.0, 0.0, 161.66),
        ports=(
            PortInterface("exit_slit_plane", "vacuum", (0.0, 0.0, 109.66), (0.0, 0.0, -1.0), "5-50 um Piezo Slit", mating_part_id="S1.3-02", bore_mm=0.35, od_mm=86.0, frame="global"),
            PortInterface("entrance_slit_plane", "vacuum", (0.0, 0.0, 213.66), (0.0, 0.0, 1.0), "5-50 um Piezo Slit", mating_part_id="S1.2-04", bore_mm=0.35, od_mm=86.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("CASSETTE_OD", 86.0, 0.02, -0.02, prefix="Ø"),
            DimensionCallout("SLIT_W_NOM", 0.350, 0.0005, -0.0005, decimals=3),
            DimensionCallout("STEP_RES", 0.0005, 0.0001, -0.0001, decimals=4),
        ),
        gdt_frames=(
            GDTFrame("parallelism", 0.0005, datum_primary="A", feature_note="MO KNIFE EDGES"),
            GDTFrame("flatness", 0.002, datum_primary="", feature_note="FLEXURE CARRIER"),
        ),
        scad_params=(("cassette_od", 86.0), ("slit_nom_mm", 0.35), ("step_um", 0.5)),
        notes=("Dual HDA entrance/exit UHV piezo flexure slit cassettes (5-50 um adjustable, 0.35 mm Exp124 HDA-HiRes nominal)",),
        target_mass_kg=0.72,
    )
    f_s1502 = (
        ScadFeature("add_tube", {"od": 86.0, "id": 40.0, "h": 7.0}, translate=(0.0, 0.0, -52.0), comment="Lower HDA exit piezo slit cassette"),
        ScadFeature("add_tube", {"od": 86.0, "id": 40.0, "h": 6.0}, translate=(0.0, 0.0, 52.0), comment="Upper HDA entrance piezo slit cassette"),
        ScadFeature("cut_bolt_circle", {"pcd": 76.0, "bolt_d": 3.4, "count": 8, "h": 120.0}, comment="8xM3 cassette mounting bolts"),
    )
    parts["S1.5-02"] = BuiltPart(d_s1502, m_s1502, f_s1502, {})

    # -----------------------------------------------------------------------
    # S1.5-03: HDA Ultra-Low-Noise Bipolar Power Supply (1U Rack Bay 1, U31 per #309)
    # -----------------------------------------------------------------------
    m_s1503, f_s1503, o_s1503 = make_rack_unit_chassis(
        u_start=31,
        u_height=1,
        rear_boss_count=4,
        internal_modules=2,
        material="Al 6061",
        name="S1.5-03",
    )
    d_s1503 = make_part_design_from_bom(
        "S1.5-03",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=o_s1503,
        ports=(
            PortInterface("hda_hemi_bias_out", "electrical", (o_s1503[0], RACK_BAY1_FRONT_Y + 442.5, o_s1503[2]), (0.0, 1.0, 0.0), "SHV Bipolar HDA", mating_part_id="S1.5-01", od_mm=14.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("RACK_W_X", 482.6, 0.3, -0.3),
            DimensionCallout("HEIGHT_1U", 42.45, 0.3, -0.3),
            DimensionCallout("RIPPLE_MAX", 50.0, 0.0, -50.0, unit="mVpp", suffix=" mVpp"),
        ),
        gdt_frames=(GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-IN EARS"),),
        scad_params=(("rack_u", 1), ("u_slot", "U31"), ("ripple_mVpp", 50.0), ("stability_ppm", 10.0)),
        notes=("19-in Rack Bay 1 slot U31 (X=1480.0, front -Y @ -438.0, Z_nat=[924.50, 966.95]); bipolar ultra-low-noise HDA-HiRes pass-energy supply",),
        target_mass_kg=5.60,
    )
    parts["S1.5-03"] = BuiltPart(d_s1503, m_s1503, tuple(f_s1503), {})

    # -----------------------------------------------------------------------
    # S1.6-01: SEMI S2 Dual-Cylinder Exhausted PH3/SiF4 Toxic Gas Cabinet (Floor X=-1350, Y=+1050)
    # -----------------------------------------------------------------------
    cab_cx, cab_cy = -1350.0, 1050.0
    cab_dx, cab_dy, cab_h = 500.0, 600.0, 1680.0
    cab_wt = 2.5
    cab_z0 = FLOOR_Z + 40.0  # 40 mm leveling feet from floor Z=-500 -> Z=-460..+1220 + 80 mm exhaust collar -> +1300
    cab_cz = cab_z0 + 0.5 * cab_h
    cab_parts: list[SolidMesh] = []
    # 4 corner leveling feet on floor (Z ∈ [-500, -460.5])
    for fx in (-210.0, 210.0):
        for fy in (-260.0, 260.0):
            cab_parts.append(
                make_cylinder(22.0, 39.5, segments=16, axis="z", center=(cab_cx + fx, cab_cy + fy, FLOOR_Z + 19.75), name="S1.6-01_foot", material="Steel")
            )
    # Hollow epoxy-coated steel cabinet walls (top, bottom, back, left, right, front door w/ window cutout)
    cab_parts.append(make_box(cab_dx, cab_dy, cab_wt, center=(cab_cx, cab_cy, cab_z0 + 0.5 * cab_wt), name="S1.6-01_bot", material="Steel"))
    cab_parts.append(make_box(cab_dx, cab_dy, cab_wt, center=(cab_cx, cab_cy, cab_z0 + cab_h - 0.5 * cab_wt), name="S1.6-01_top", material="Steel"))
    cab_parts.append(make_box(cab_wt, cab_dy - 1.0, cab_h - 8.0, center=(cab_cx - 0.5 * cab_dx + 0.5 * cab_wt, cab_cy, cab_cz), name="S1.6-01_back", material="Steel"))
    for sgn in (-1.0, 1.0):
        cab_parts.append(
            make_box(cab_dx - 8.0, cab_wt, cab_h - 8.0, center=(cab_cx, cab_cy + sgn * (0.5 * cab_dy - 0.5 * cab_wt), cab_cz), name="S1.6-01_side", material="Steel")
        )
    # Front self-closing door with safety sight-glass window cutout (facing +X toward room)
    door = make_plate_with_holes(
        rect_2d(cab_h - 10.0, cab_dy - 10.0),
        holes_2d=[rect_2d(460.0, 320.0, cx=-220.0, cy=0.0, ccw=False)],
        thickness=cab_wt,
        axis="x",
        center=(cab_cx + 0.5 * cab_dx - 0.5 * cab_wt, cab_cy, cab_cz),
        name="S1.6-01_door_window",
        material="Steel",
    )
    cab_parts.append(door)
    # Top Ø150 mm negative-pressure exhaust collar (Z ∈ [1220.5, 1300.0])
    cab_parts.append(
        make_tube(73.0, 76.0, 79.5, segments=32, axis="z", center=(cab_cx, cab_cy, cab_z0 + cab_h + 40.0), name="S1.6-01_exhaust_collar", material="316L")
    )
    # 2x internal hollow seamless steel PH3 / SiF4 pressure gas cylinders (6 mm wall) + compact VCR purge header
    for sy in (-130.0, 130.0):
        cab_parts.append(
            make_tube(69.0, 75.0, 1050.0, segments=24, axis="z", center=(cab_cx - 20.0, cab_cy + sy, cab_z0 + 540.0), name="S1.6-01_cylinder", material="Steel")
        )
    cab_parts.append(
        make_box(80.0, 320.0, 60.0, center=(cab_cx - 40.0, cab_cy, cab_z0 + 1320.0), name="S1.6-01_purge_manifold", material="316L")
    )
    m_s1601 = merge_solids(cab_parts, name="S1.6-01", material="Steel")
    d_s1601 = make_part_design_from_bom(
        "S1.6-01",
        design_tier="COTS_ENV_ICD",
        material="Steel",
        surface_finish_ra_um=3.2,
        world_origin_mm=(cab_cx, cab_cy, 400.0),
        ports=(
            PortInterface("exhaust_duct_top", "gas", (cab_cx, cab_cy, 1300.0), (0.0, 0.0, 1.0), "DN150 Exhaust", mating_part_id="S1.6-02", bore_mm=146.0, od_mm=152.0, frame="global"),
            PortInterface("ph3_coax_outlet", "gas", (cab_cx + 250.0, cab_cy, 860.0), (1.0, 0.0, 0.0), "1/4 VCR Coax RFO", mating_part_id="S1.1-04", bore_mm=6.4, od_mm=12.7, frame="global"),
        ),
        dimensions=(
            DimensionCallout("CAB_W_Y", 600.0, 2.0, -2.0),
            DimensionCallout("CAB_D_X", 500.0, 2.0, -2.0),
            DimensionCallout("CAB_H_Z", 1800.0, 3.0, -3.0),
            DimensionCallout("EXHAUST_OD", 152.0, 1.0, -1.0, prefix="Ø"),
        ),
        gdt_frames=(GDTFrame("perpendicularity", 1.5, datum_primary="A", feature_note="FLOOR LEVELING PLANE"),),
        scad_params=(("cab_dx", 500.0), ("cab_dy", 600.0), ("cab_h", 1800.0), ("semi_s2_ref", "UNVERIFIED_M0_DESIGN")),
        notes=("Facility floor placement X=[-1600, -1100], Y=[+750, +1350], Z=[-500, +1300] (clear of PT420, DR, S6.8-02 GHS & S7.SAFETY-01); SEMI S2/NFPA 318 ref (semi_s2_certified=false)",),
        target_mass_kg=135.0,
    )
    f_s1601 = (
        ScadFeature("add_box", {"dx": 500.0, "dy": 600.0, "dz": 1680.0}, translate=(0.0, 0.0, -20.0), comment="SEMI S2 dual-cylinder steel cabinet shell"),
        ScadFeature("add_tube", {"od": 152.0, "id": 146.0, "h": 80.0}, translate=(0.0, 0.0, 860.0), comment="Top Ø150 mm negative-pressure exhaust collar"),
        ScadFeature("cut_slot", {"length": 460.0, "width": 320.0, "h": 20.0}, translate=(248.0, 0.0, 200.0), rotate=(0.0, 90.0, 0.0), comment="Self-closing door sight-glass cutout"),
    )
    parts["S1.6-01"] = BuiltPart(d_s1601, m_s1601, f_s1601, {})

    # -----------------------------------------------------------------------
    # S1.6-02: Dry-Bed PH3 Gas Scrubber Tower & 50 ppb Detector (Floor X=-1350, Y=+1650)
    # -----------------------------------------------------------------------
    scr_cx, scr_cy = -1350.0, 1650.0
    scr_skid = make_rect_plate_with_features(
        440.0, 440.0, 18.0,
        circular_holes=[(-185.0, -185.0, 14.0), (185.0, -185.0, 14.0), (185.0, 185.0, 14.0), (-185.0, 185.0, 14.0)],
        center=(scr_cx, scr_cy, FLOOR_Z + 81.0), name="S1.6-02_skid_deck", material="Steel",
    )
    scr_feet = [
        make_box(60.0, 60.0, 71.0, center=(scr_cx + fx, scr_cy + fy, FLOOR_Z + 35.5), name="S1.6-02_skid_foot", material="Steel")
        for fx in (-185.0, 185.0) for fy in (-185.0, 185.0)
    ]
    scr_col = make_tube(165.5, 170.0, 1280.0, segments=40, axis="z", center=(scr_cx - 20.0, scr_cy, FLOOR_Z + 92.0 + 640.0), name="S1.6-02_drybed_column", material="Steel")
    scr_cap = make_ring_with_bolt_circle(
        75.0, 185.0, 14.0, pcd=345.0, n_bolts=12, bolt_diameter=11.0, sub_per_side=2,
        axis="z", center=(scr_cx - 20.0, scr_cy, FLOOR_Z + 1381.0), name="S1.6-02_top_flange", material="Steel",
    )
    scr_duct = make_tube(72.0, 76.0, 126.0, segments=32, axis="z", center=(scr_cx - 20.0, scr_cy, FLOOR_Z + 1456.0), name="S1.6-02_exhaust_stack", material="316L")
    # Side-mounted 50 ppb electrochemical PH3 sensor & PLC interlock control panel (strictly inside X <= -1130)
    scr_ctrl = make_chamfered_box(55.0, 200.0, 280.0, chamfer=3.0, center=(scr_cx + 188.0, scr_cy, FLOOR_Z + 980.0), name="S1.6-02_50ppb_detector", material="Al 6061")
    m_s1602 = merge_solids([scr_skid, *scr_feet, scr_col, scr_cap, scr_duct, scr_ctrl], name="S1.6-02", material="Steel")
    d_s1602 = make_part_design_from_bom(
        "S1.6-02",
        design_tier="COTS_ENV_ICD",
        material="Steel",
        surface_finish_ra_um=3.2,
        world_origin_mm=(scr_cx, scr_cy, 260.0),
        ports=(
            PortInterface("scrubber_inlet", "gas", (scr_cx - 20.0, scr_cy - 170.0, 750.0), (0.0, -1.0, 0.0), "DN150 Inlet", mating_part_id="S1.6-01", bore_mm=144.0, od_mm=152.0, frame="global"),
            PortInterface("scrubber_exhaust", "gas", (scr_cx - 20.0, scr_cy, 1020.0), (0.0, 0.0, 1.0), "DN150 Facility Exhaust", bore_mm=144.0, od_mm=152.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("SKID_XY", 440.0, 2.0, -2.0),
            DimensionCallout("COLUMN_OD", 340.0, 1.5, -1.5, prefix="Ø"),
            DimensionCallout("TOTAL_H", 1520.0, 3.0, -3.0),
        ),
        gdt_frames=(GDTFrame("perpendicularity", 1.5, datum_primary="A", feature_note="ABSORBER COLUMN"),),
        scad_params=(("skid_xy", 440.0), ("col_od", 340.0), ("total_h", 1520.0), ("alarm_ppb", 50.0)),
        notes=("Facility floor placement X=[-1570, -1130], Y=[+1430, +1870], Z=[-500, +1020]; 80 mm service aisle to S1.6-01; <50 ppb outlet",),
        target_mass_kg=95.0,
    )
    f_s1602 = (
        ScadFeature("add_box", {"dx": 440.0, "dy": 440.0, "dz": 90.0}, translate=(0.0, 0.0, -715.0), comment="Welded steel scrubber skid"),
        ScadFeature("add_tube", {"od": 340.0, "id": 320.0, "h": 1280.0}, translate=(-20.0, 0.0, -28.0), comment="Dry-bed catalytic PH3 absorber tower"),
        ScadFeature("add_box", {"dx": 60.0, "dy": 220.0, "dz": 320.0}, translate=(188.0, 0.0, 220.0), comment="50 ppb electrochemical detector & PLC panel"),
    )
    parts["S1.6-02"] = BuiltPart(d_s1602, m_s1602, f_s1602, {})

    # -----------------------------------------------------------------------
    # S1.7-01: Option-Q S1-Multi 3-Species Source Cartridge Bay (+Y=110.0, Z=492.66, 4.80 kg)
    # Cleanly tagged S1.7-01 (resolves legacy v6 S1.6 alias bug!)
    # -----------------------------------------------------------------------
    yc_optq, zc_optq = 110.0, 492.66
    # CF40 throat weld-neck mating toward S1.1-01 (-Y): knife-edge at Y=47.0 mm (2.0 mm clearance to R=45 duoplasmatron)
    cf40_throat = make_cf_weld_neck(
        "CF40", neck_length=12.0, tube_od=38.0, tube_id=32.0,
        axis="-y", center=(0.0, 53.35, zc_optq), name="S1.7-01_cf40_throat", material="316LN",
    )
    # Hollow Ti-6Al-4V quick-swap 76x76x95 mm cartridge enclosure (Y ∈ [72.0, 148.0], exact 27.0 mm body clearance!)
    c_wt = 6.0
    s17_parts: list[SolidMesh] = [cf40_throat]
    # Front plate (Y=72..78) with Ø34 mm beam/vapor aperture hole
    s17_parts.append(
        make_plate_with_holes(
            rect_2d(76.0, 95.0), holes_2d=[circle_2d(17.0, segments=28, ccw=False)],
            thickness=c_wt, axis="y", center=(0.0, 75.0, zc_optq), name="S1.7-01_front_plate", material="Ti-6Al-4V",
        )
    )
    # Rear quick-swap cover plate (Y=142..148) with 4 corner latch bolts
    s17_parts.append(
        make_rect_plate_with_features(
            76.0, 95.0, c_wt,
            circular_holes=[(-28.0, -37.0, 5.5), (28.0, -37.0, 5.5), (28.0, 37.0, 5.5), (-28.0, 37.0, 5.5)],
            axis="y", center=(0.0, 145.0, zc_optq), name="S1.7-01_rear_cover", material="Ti-6Al-4V",
        )
    )
    # Top, bottom, left, right walls of cartridge box (Y ∈ [78.3, 141.7])
    for sgn in (-1.0, 1.0):
        s17_parts.append(
            make_box(76.0, 63.4, c_wt, center=(0.0, yc_optq, zc_optq + sgn * 44.5), name="S1.7-01_wall_z", material="Ti-6Al-4V")
        )
        s17_parts.append(
            make_box(c_wt, 63.4, 82.6, center=(sgn * 35.0, yc_optq, zc_optq), name="S1.7-01_wall_x", material="Ti-6Al-4V")
        )
    # Internal PBN 450 C 121Sb effusion oven crucible (Ø22 mm OD x 44 mm, Y ∈ [92, 136], Z_c = zc_optq - 16)
    s17_parts.append(
        make_tube(8.0, 11.0, 44.0, segments=32, axis="y", center=(0.0, 114.0, zc_optq - 16.0), name="S1.7-01_pbn_sb_oven", material="PBN")
    )
    # Internal 4-rod 167Er micro-Paul RF quadrupole ion trap (Y ∈ [90, 134], Z_c = zc_optq + 18)
    for k in range(4):
        ang = math.radians(45.0 + k * 90.0)
        rx = 5.5 * math.cos(ang)
        rz = 5.5 * math.sin(ang)
        s17_parts.append(
            make_cylinder(1.5, 44.0, segments=14, axis="y", center=(rx, 112.0, zc_optq + 18.0 + rz), name=f"S1.7-01_paul_rod_{k}", material="Mo")
        )
    m_s1701 = merge_solids(s17_parts, name="S1.7-01", material="Ti-6Al-4V")
    d_s1701 = make_part_design_from_bom(
        "S1.7-01",
        design_tier="CUSTOM_FULL",
        material="Ti-6Al-4V",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, yc_optq, zc_optq),
        ports=(
            make_cf_port_interface("CF40", "duoplasmatron_mate_cf40", (0.0, 47.0, zc_optq), (0.0, -1.0, 0.0), mating_part_id="S1.1-01", frame="global"),
            PortInterface("oven_heater_feed", "electrical", (0.0, 148.0, zc_optq - 16.0), (0.0, 1.0, 0.0), "180 W DC / RF Paul", od_mm=16.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("BAY_X", 76.0, 0.05, -0.05),
            DimensionCallout("BAY_Y", 76.0, 0.05, -0.05),
            DimensionCallout("BAY_Z", 95.0, 0.05, -0.05),
            DimensionCallout("FLANGE_CF40", 69.5, 0.10, -0.10, prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.050, diameter_zone=True, datum_primary="B", feature_note="CF40 TO OVEN AXIS"),
            GDTFrame("perpendicularity", 0.025, datum_primary="A", feature_note="CF40 SEAL FACE"),
        ),
        scad_params=(("bay_x", 76.0), ("bay_y", 76.0), ("bay_z", 95.0), ("sb_oven_C", 450.0), ("er_zpl_nm", 1536.0)),
        notes=(
            "Exp142 Option-Q S1-Multi cartridge (76x76x95 mm @ [0, +110, 492.66] in Z_wafer=0 frame, 27.0 mm body clearance to S1.1-01)",
            "STRICTLY tagged S1.7-01 — fixes legacy CAD v6 S1.6 aliasing bug; 31P gas / 121Sb 450 C PBN oven / 167Er micro-Paul",
        ),
        target_mass_kg=4.80,
    )
    f_s1701 = (
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(0.0, -56.65, 0.0), rotate=(90.0, 0.0, 0.0), comment="ISO 3669 CF40 mounting flange to S1.1-01"),
        ScadFeature("add_box", {"dx": 76.0, "dy": 76.0, "dz": 95.0}, comment="Ti-6Al-4V quick-swap 3-species cartridge bay"),
        ScadFeature("add_tube", {"od": 22.0, "id": 16.0, "h": 44.0}, translate=(0.0, 4.0, -16.0), rotate=(90.0, 0.0, 0.0), comment="PBN 450 C 121Sb effusion oven"),
        ScadFeature("cut_hole", {"d": 34.0, "h": 14.0}, translate=(0.0, -35.0, 0.0), rotate=(90.0, 0.0, 0.0), comment="Vapor/ion exit aperture"),
    )
    parts["S1.7-01"] = BuiltPart(d_s1701, m_s1701, f_s1701, {"oven_450c_clearance": checks["s17_450c_oven_clearance"]})

    # Verify exact 23/23 S1 BOM coverage
    expected = list_physical_part_ids("S1")
    if set(parts.keys()) != set(expected):
        missing = sorted(set(expected) - set(parts.keys()))
        extra = sorted(set(parts.keys()) - set(expected))
        raise RuntimeError(f"S1 part coverage mismatch! missing={missing}, extra={extra}")

    return {pid: parts[pid] for pid in expected}


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def export_all(out_dir: Path | str | None = None) -> dict[str, PartArtifactResult]:
    """Build and export all 23 S1 parts (.stl, .step, .scad, .dxf, .svg + .json manifest)."""
    dest = Path(out_dir) if out_dir is not None else S1_OUT_DIR
    dest.mkdir(parents=True, exist_ok=True)

    built = build_s1_parts()
    results: dict[str, PartArtifactResult] = {}
    manifest_parts: dict[str, Any] = {}

    for pid, bp in built.items():
        res = export_part_artifacts(
            bp.design,
            bp.mesh,
            dest,
            scad_features=bp.scad_features,
            flat=True,
        )
        results[pid] = res

        part_json_path = dest / f"{pid}.json"
        part_payload = {
            "part_id": pid,
            "subsystem": "S1",
            "design": bp.design.to_dict(),
            "artifact": res.to_dict(),
            "engineering_checks": bp.checks,
            "epistemic": {
                "design_maturity": DESIGN_MATURITY,
                "no_lab_measurement": NO_LAB_MEASUREMENT,
                "iec61508_certified": IEC61508_CERTIFIED,
                "semi_s2_certified": SEMI_S2_CERTIFIED,
            },
        }
        part_json_path.write_text(
            json.dumps(part_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        manifest_parts[pid] = {
            "design_tier": bp.design.design_tier,
            "material": bp.design.material,
            "mass_kg": round(res.mass_kg, 5),
            "watertight": res.watertight,
            "all_valid": res.all_valid,
            "bbox_min_mm": [round(v, 4) for v in res.bbox_min_mm],
            "bbox_max_mm": [round(v, 4) for v in res.bbox_max_mm],
            "json_path": _repo_rel(part_json_path),
            "stl_path": res.stl_path,
            "step_path": res.step_path,
            "scad_path": res.scad_path,
            "dxf_path": res.dxf_path,
            "svg_path": res.svg_path,
        }

    summary = {
        "subsystem": "S1",
        "part_count": len(results),
        "custom_full_count": sum(1 for bp in built.values() if bp.design.design_tier == "CUSTOM_FULL"),
        "cots_env_icd_count": sum(1 for bp in built.values() if bp.design.design_tier == "COTS_ENV_ICD"),
        "all_watertight": all(r.watertight for r in results.values()),
        "all_valid": all(r.all_valid for r in results.values()),
        "total_computed_mass_kg": round(sum(r.mass_kg for r in results.values()), 4),
        "engineering_checks": compute_s1_engineering_checks(),
        "epistemic": {
            "design_maturity": DESIGN_MATURITY,
            "no_lab_measurement": NO_LAB_MEASUREMENT,
            "iec61508_certified": IEC61508_CERTIFIED,
            "semi_s2_certified": SEMI_S2_CERTIFIED,
        },
        "parts": manifest_parts,
    }
    (dest / "S1_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return results


if __name__ == "__main__":
    res = export_all()
    tot_kg = sum(r.mass_kg for r in res.values())
    ok = sum(1 for r in res.values() if r.all_valid)
    print(f"S1 exported {ok}/{len(res)} valid parts, total mass={tot_kg:.3f} kg")
