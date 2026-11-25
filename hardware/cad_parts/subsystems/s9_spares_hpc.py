"""Feature-level 3D mechanical CAD builders for Subsystem S9 non-OptQ Parts
(Calibration Wafers/Targets, Process Gas & Service Spare Kits, and Option-HPC QEC Decoder Stack).

Covers 10 / 10 non-OptQ physical BOM parts of S9:
- Calibration Metrology Kits (2): S9.1-01, S9.1-02 (clean bench at X=-900 mm, Y=-1180 mm)
- Process Gas Rack & Spare Maintenance Kits (5): S9.2-01, S9.2-02, S9.3-01, S9.3-02, S9.3-03
- Option-HPC 100 Gbps RoCEv2 QEC Decoder Stack (3, 64.00 kg total per Exp143):
  S9.HPC-01 (56.00 kg), S9.HPC-02 (4.20 kg), S9.HPC-03 (3.80 kg) at X=+2750 mm, Y=-700 mm

Global Machine Coordinate System (Canonical params.py Datum: Z_FLOOR = 0.0 mm, Z_WAFER = +500.0 mm):
- Cleanly segregated from S7 Bay 1/2 (X in [1180, 2400]), S7.SAFETY-04 UPS (X in [2430, 2870],
  Y in [-210, +510]), S6.8-02 GHS (X=-1300, Y=-800), and S7.SAFETY-03 E-Stop pedestals (±1900).

Epistemic Status:
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
from typing import Any

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
    compute_mass_props,
    export_part_artifacts,
    list_physical_part_ids,
    make_box,
    make_chamfered_box,
    make_cylinder,
    make_part_design_from_bom,
    make_plate_with_holes,
    make_rect_plate_with_features,
    make_revolved_profile,
    make_swept_tube,
    make_tube,
    merge_solids,
    rect_2d,
    split_shells,
    verify_watertight,
)
from hardware.cad_parts.subsystems.s7_racks_safety import (
    BuiltPart,
    EIA_CHASSIS_BODY_W_MM,
    EIA_FACEPLATE_W_MM,
    Z_FLOOR_MM,
    Z_WAFER_MM,
    _calibrated_density,
    _make_19in_chassis,
    _shell_bboxes,
)

# ---------------------------------------------------------------------------
# Coordinate Constants & Canonical Exp143 Option-HPC Mass Targets
# ---------------------------------------------------------------------------
S9_OUT_DIR: Path = REPO_ROOT / "hardware" / "cad_parts" / "out" / "S9_spares_hpc"

HPC_STACK_X_MM: float = 2750.0
HPC_STACK_Y_MM: float = -700.0  # Y spans [-1090, -310] -> 100 mm clear of S7.SAFETY-04 (Y_min=-210)!

S9_HPC_TARGET_MASS_KG: dict[str, float] = {
    "S9.HPC-01": 56.00,
    "S9.HPC-02": 4.20,
    "S9.HPC-03": 3.80,
}


# ---------------------------------------------------------------------------
# Feature-Level Cleanroom Storage Chest Helper
# ---------------------------------------------------------------------------
def _make_cleanroom_kit_case(
    *,
    name: str,
    cx: float,
    cy: float,
    dx: float,
    dy: float,
    dz: float,
    material: str = "Al 6061",
    n_compartments: int = 3,
    interior_solids: list[SolidMesh] | None = None,
) -> tuple[SolidMesh, list[ScadFeature]]:
    """Build a watertight cleanroom ESD service kit case with recessed walls, handles & latches."""
    wt = 8.0
    base_h = 12.0
    lid_h = 18.0
    z_bot = Z_FLOOR_MM
    wall_h = dz - base_h - lid_h - 0.6
    z_wall_c = z_bot + base_h + 0.2 + 0.5 * wall_h

    solids: list[SolidMesh] = [
        # Bottom skid plate
        make_chamfered_box(dx, dy, base_h, chamfer=2.5, center=(cx, cy, z_bot + 0.5 * base_h), name=f"{name}_base", material=material),
        # 4 side walls forming open interior tray
        make_box(wt, dy, wall_h, center=(cx - 0.5 * dx + 0.5 * wt, cy, z_wall_c), name=f"{name}_wall_L", material=material),
        make_box(wt, dy, wall_h, center=(cx + 0.5 * dx - 0.5 * wt, cy, z_wall_c), name=f"{name}_wall_R", material=material),
        make_box(dx - 2 * wt - 0.4, wt, wall_h, center=(cx, cy - 0.5 * dy + 0.5 * wt, z_wall_c), name=f"{name}_wall_F", material=material),
        make_box(dx - 2 * wt - 0.4, wt, wall_h, center=(cx, cy + 0.5 * dy - 0.5 * wt, z_wall_c), name=f"{name}_wall_B", material=material),
        # Gasketed top lid resting cleanly above rim
        make_chamfered_box(dx + 4.0, dy + 4.0, lid_h, chamfer=3.0, center=(cx, cy, z_bot + dz - 0.5 * lid_h), name=f"{name}_lid", material=material),
    ]
    # Dual front toggle-latch bosses (facing -Y) + side carry handles (strictly outside lid overhang!)
    for sgn in (-1.0, +1.0):
        solids.append(
            make_box(24.0, 12.0, 34.0, center=(cx + sgn * 0.28 * dx, cy - 0.5 * dy - 8.4, z_bot + dz - lid_h - 8.0), name=f"{name}_latch", material="316L")
        )
        solids.append(
            make_box(12.0, 90.0, 22.0, center=(cx + sgn * (0.5 * dx + 8.4), cy, z_wall_c), name=f"{name}_handle", material="Steel")
        )
    # Internal divider ribs
    if n_compartments > 1 and not interior_solids:
        inner_w = dx - 2 * wt - 4.0
        inner_d = dy - 2 * wt - 4.0
        for d_i in range(1, n_compartments):
            rx = cx - 0.5 * inner_w + d_i * (inner_w / n_compartments)
            solids.append(
                make_box(4.0, inner_d, 0.65 * wall_h, center=(rx, cy, z_bot + base_h + 0.4 + 0.325 * wall_h), name=f"{name}_div_{d_i}", material="PEEK")
            )
    if interior_solids:
        solids.extend(interior_solids)

    mesh = merge_solids(solids, name=name, material=material)
    scad_feats = [
        ScadFeature("add_box", {"dx": dx, "dy": dy, "dz": dz}, comment="Cleanroom ESD storage case outer envelope"),
        ScadFeature("cut_slot", {"length": dx - 16.0, "width": dy - 16.0, "h": wall_h}, translate=(0.0, 0.0, 0.0), comment="Internal padded kit tray cavity"),
    ]
    return mesh, scad_feats


# ---------------------------------------------------------------------------
# Individual S9 Non-OptQ Part Builders (10 / 10 Physical Parts)
# ---------------------------------------------------------------------------
def _build_s9_1_01() -> BuiltPart:
    """S9.1-01: 5x Reference 31P-Implanted 28Si Calibration Wafers (Ø50 mm) in Cleanroom Carrier Box."""
    pid = "S9.1-01"
    cx, cy = -900.0, -1180.0
    dx, dy, dz = 160.0, 120.0, 92.0
    # 5x Ø50 x 1.0 mm 28Si reference wafers seated vertically inside cleanroom cassette (Z in [-985, -935])
    wafers = [
        make_cylinder(
            25.0,
            1.2,
            segments=28,
            axis="x",
            center=(cx - 32.0 + i * 16.0, cy, Z_FLOOR_MM + 40.0),
            name=f"s9_1_01_cal_wafer_{i + 1}",
            material="Si",
        )
        for i in range(5)
    ]
    mesh, feats = _make_cleanroom_kit_case(
        name=pid,
        cx=cx,
        cy=cy,
        dx=dx,
        dy=dy,
        dz=dz,
        material="PEEK",
        interior_solids=wafers,
    )
    target_mass = 1.45
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        design_tier="KIT_OR_ALIAS",
        material="Si",
        temp_k=300.0,
        surface_finish_ra_um=0.4,
        world_origin_mm=(cx, cy, Z_FLOOR_MM + 0.5 * dz),
        ports=(
            PortInterface("wafer_carrier_slot", "mechanical", (cx, cy, Z_FLOOR_MM + 40.0), (0.0, 0.0, 1.0), "5x Ø50 mm 28Si Reference Calibration Wafers (±2% Dose)", mating_part_id="S5.4-01", bore_mm=50.0, frame="world"),
            PortInterface("n2_purge_port", "gas", (cx + 0.5 * dx, cy, Z_FLOOR_MM + 35.0), (1.0, 0.0, 0.0), "Quick-Connect N2 Dry-Box Purge", frame="world"),
        ),
        dimensions=(
            DimensionCallout("CASE_W", dx, 0.5, -0.5, view="front"),
            DimensionCallout("CASE_D", dy, 0.5, -0.5, view="right"),
            DimensionCallout("WAFER_OD", 50.0, 0.05, -0.05, prefix="Ø", view="top"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.005, datum_primary="", feature_note="28Si CALIBRATION WAFERS"),),
        notes=("5x known-dose 31P/28Si FAT/SAT IBIC & ESR/ENDOR calibration wafers in clean PEEK carrier at (-900, -1180).",),
        scad_params=(("qty_wafers", 5), ("wafer_od_mm", 50.0), ("case_dx_mm", dx), ("case_dy_mm", dy)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats), density_kg_m3=eff_rho)


def _build_s9_1_02() -> BuiltPart:
    """S9.1-02: 4x 10 nm Au/W Knife-Edge & Lithographic Fiducial Calibration Target Coupons."""
    pid = "S9.1-02"
    cx, cy = -710.0, -1180.0
    dx, dy, dz = 140.0, 100.0, 52.0
    # 4x 25x25x1.5 mm Si/Au-W knife-edge fiducial target coupons in 2x2 array inside carrier box
    coupons: list[SolidMesh] = []
    for idx, (ox, oy) in enumerate(((-24.0, -18.0), (+24.0, -18.0), (+24.0, +18.0), (-24.0, +18.0)), start=1):
        coupons.append(
            make_box(
                25.0,
                25.0,
                1.5,
                center=(cx + ox, cy + oy, Z_FLOOR_MM + 16.0),
                name=f"s9_1_02_knife_edge_coupon_{idx}",
                material="Si",
            )
        )
        # Raised Au/W knife-edge metrology reference bar on coupon face
        coupons.append(
            make_box(
                14.0,
                3.0,
                0.8,
                center=(cx + ox, cy + oy, Z_FLOOR_MM + 17.25),
                name=f"s9_1_02_au_w_edge_{idx}",
                material="Au",
            )
        )
    mesh, feats = _make_cleanroom_kit_case(
        name=pid,
        cx=cx,
        cy=cy,
        dx=dx,
        dy=dy,
        dz=dz,
        material="Al 6061",
        interior_solids=coupons,
    )
    target_mass = 1.15
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        design_tier="KIT_OR_ALIAS",
        material="Si",
        surface_finish_ra_um=0.1,
        world_origin_mm=(cx, cy, Z_FLOOR_MM + 0.5 * dz),
        ports=(
            PortInterface("fiducial_target_coupons", "optical", (cx, cy, Z_FLOOR_MM + 17.5), (0.0, 0.0, 1.0), "4x 25x25 mm Au/W 10 nm Knife-Edge Targets (±1 nm edge)", mating_part_id="S4.5-02", frame="world"),
        ),
        dimensions=(
            DimensionCallout("CASE_W", dx, 0.5, -0.5, view="front"),
            DimensionCallout("COUPON_SQ", 25.0, 0.05, -0.05, view="top"),
            DimensionCallout("CASE_H", dz, 0.5, -0.5, view="front"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.002, datum_primary="", feature_note="10 nm KNIFE-EDGE SURFACE"),),
        notes=("4x 10 nm Au/W knife-edge & fiducial calibration targets (sigma_spot <= 1.5 nm metrology) at (-710, -1180).",),
        scad_params=(("qty_targets", 4), ("coupon_sq_mm", 25.0), ("edge_nm", 10.0)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats), density_kg_m3=eff_rho)


def _build_s9_2_01() -> BuiltPart:
    """S9.2-01: High-Purity Process Gas Cylinder Safety Rack (4x Cylinders: PH3, 29SiF4, 28SiF4, Ar/N2)."""
    pid = "S9.2-01"
    cx, cy = -1350.0, -1520.0
    rack_w, rack_d, rack_h = 840.0, 320.0, 1420.0

    solids: list[SolidMesh] = [
        # Heavy bolted steel floor baseplate with 4x M12 seismic anchor holes
        make_rect_plate_with_features(
            rack_w,
            rack_d,
            16.0,
            circular_holes=[(-380.0, -125.0, 14.0), (+380.0, -125.0, 14.0), (+380.0, +125.0, 14.0), (-380.0, +125.0, 14.0)],
            hole_segments=12,
            axis="z",
            center=(cx, cy, Z_FLOOR_MM + 8.0),
            name="s9_2_01_baseplate",
            material="Steel",
        ),
        # Rear vertical structural back-frame posts (left, center, right) at Y = cy + 135 mm
        make_box(40.0, 40.0, 1180.0, center=(cx - 395.0, cy + 135.0, Z_FLOOR_MM + 16.2 + 590.0), name="s9_2_01_post_L", material="Steel"),
        make_box(40.0, 40.0, 1180.0, center=(cx, cy + 135.0, Z_FLOOR_MM + 16.2 + 590.0), name="s9_2_01_post_C", material="Steel"),
        make_box(40.0, 40.0, 1180.0, center=(cx + 395.0, cy + 135.0, Z_FLOOR_MM + 16.2 + 590.0), name="s9_2_01_post_R", material="Steel"),
        # Upper & lower horizontal steel cylinder restraint bars (SEMI S2 dual-height seismic restraint)
        make_box(rack_w - 10.0, 26.0, 45.0, center=(cx, cy + 100.0, Z_FLOOR_MM + 460.0), name="s9_2_01_rail_lower", material="Steel"),
        make_box(rack_w - 10.0, 26.0, 45.0, center=(cx, cy + 100.0, Z_FLOOR_MM + 920.0), name="s9_2_01_rail_upper", material="Steel"),
    ]
    # 4x Electronic-grade (99.999%) revolved gas cylinders (Ø164 x 1340 mm) with domed shoulders & safety valve caps
    for c_idx, gas_tag in enumerate(("PH3_5pct", "29SiF4", "28SiF4", "Ar_N2")):
        gx = cx - 292.5 + c_idx * 195.0
        solids.append(
            make_revolved_profile(
                [
                    (0.0, 0.0),
                    (82.0, 0.0),
                    (82.0, 1080.0),
                    (74.0, 1150.0),
                    (46.0, 1215.0),
                    (32.0, 1240.0),
                    (32.0, 1345.0),
                    (22.0, 1365.0),
                    (0.0, 1365.0),
                ],
                segments=24,
                axis="z",
                center=(gx, cy - 20.0, Z_FLOOR_MM + 16.5),
                name=f"s9_2_01_cyl_{gas_tag}",
                material="316L",
            )
        )

    mesh = merge_solids(solids, name=pid, material="Steel")
    target_mass = 168.0  # 4 x ~34 kg steel cylinders + 32 kg seismic rack
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        design_tier="KIT_OR_ALIAS",
        material="316L",
        surface_finish_ra_um=3.2,
        world_origin_mm=(cx, cy, Z_FLOOR_MM + 0.5 * rack_h),
        ports=(
            PortInterface("cga_vcr_cyl_valves", "gas", (cx, cy - 20.0, Z_FLOOR_MM + 1382.0), (0.0, 0.0, 1.0), "4x CGA-350/660/580 Electronic-Grade 99.999% Cylinders", mating_part_id="S7.SAFETY-01", frame="world"),
        ),
        dimensions=(
            DimensionCallout("RACK_W", rack_w, 2.0, -2.0, view="front"),
            DimensionCallout("RACK_D", rack_d, 2.0, -2.0, view="right"),
            DimensionCallout("CYL_H", 1382.0, 3.0, -3.0, view="front"),
            DimensionCallout("CYL_OD", 164.0, 1.0, -1.0, prefix="Ø", view="top"),
        ),
        gdt_frames=(GDTFrame("flatness", 1.0, datum_primary="", feature_note="SEISMIC ANCHOR BASEPLATE"),),
        notes=("4x 99.999% process gas cylinder stand (PH3 5% H2/Ar, 29SiF4, 28SiF4, Ar/N2) with dual-height seismic restraints.",),
        scad_params=(("qty_cylinders", 4), ("cyl_od_mm", 164.0), ("rack_w_mm", rack_w)),
        target_mass_kg=target_mass,
    )
    scad_feats = (
        ScadFeature("add_box", {"dx": rack_w, "dy": rack_d, "dz": 16.0}, translate=(0.0, 0.0, -702.0), comment="Seismic floor baseplate"),
        ScadFeature("add_cylinder", {"d": 164.0, "h": 1340.0}, translate=(-292.5, -20.0, -20.0), comment="Cylinder #1 (PH3)"),
        ScadFeature("add_cylinder", {"d": 164.0, "h": 1340.0}, translate=(-97.5, -20.0, -20.0), comment="Cylinder #2 (29SiF4)"),
        ScadFeature("add_cylinder", {"d": 164.0, "h": 1340.0}, translate=(+97.5, -20.0, -20.0), comment="Cylinder #3 (28SiF4)"),
        ScadFeature("add_cylinder", {"d": 164.0, "h": 1340.0}, translate=(+292.5, -20.0, -20.0), comment="Cylinder #4 (Ar/N2)"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats, density_kg_m3=eff_rho)


def _build_s9_2_02() -> BuiltPart:
    """S9.2-02: Spare Duoplasmatron Cathode/Filament, Ti TSP Cartridge & OFHC CF Copper Gasket Service Chest."""
    pid = "S9.2-02"
    cx, cy = -620.0, -1520.0
    dx, dy, dz = 460.0, 340.0, 240.0
    # Representative internal CF100 & CF63 OFHC copper gasket stacks + W/LaB6 cathode tray
    interior = [
        make_tube(50.0, 60.0, 32.0, segments=28, axis="z", center=(cx - 120.0, cy, Z_FLOOR_MM + 32.0), name="s9_2_02_cf100_cu_gaskets", material="OFHC Cu"),
        make_tube(31.0, 41.0, 32.0, segments=28, axis="z", center=(cx, cy, Z_FLOOR_MM + 32.0), name="s9_2_02_cf63_cu_gaskets", material="OFHC Cu"),
        make_box(110.0, 220.0, 50.0, center=(cx + 125.0, cy, Z_FLOOR_MM + 42.0), name="s9_2_02_cathode_tsp_tray", material="W"),
    ]
    mesh, feats = _make_cleanroom_kit_case(
        name=pid,
        cx=cx,
        cy=cy,
        dx=dx,
        dy=dy,
        dz=dz,
        material="Al 6061",
        interior_solids=interior,
    )
    target_mass = 14.5
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        design_tier="KIT_OR_ALIAS",
        material="OFHC Cu",
        world_origin_mm=(cx, cy, Z_FLOOR_MM + 0.5 * dz),
        ports=(
            PortInterface("uhv_service_spares_tray", "mechanical", (cx, cy, Z_FLOOR_MM + dz), (0.0, 0.0, 1.0), "1-Yr UHV Source Cathode/TSP/OFHC CF Gasket Kit", mating_part_id="S5.1-05", frame="world"),
        ),
        dimensions=(
            DimensionCallout("CHEST_W", dx, 1.0, -1.0, view="front"),
            DimensionCallout("CHEST_D", dy, 1.0, -1.0, view="right"),
            DimensionCallout("CHEST_H", dz, 1.0, -1.0, view="front"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="GASKETED LID RIM"),),
        notes=("Annual UHV/source maintenance chest: W/LaB6 cathodes, Ti TSP filaments, OFHC CF gaskets & sensors.",),
        scad_params=(("chest_dx_mm", dx), ("chest_dy_mm", dy), ("chest_dz_mm", dz)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats), density_kg_m3=eff_rho)


def _build_s9_3_01() -> BuiltPart:
    """S9.3-01: Spare MEMS Aperture & Blanker Plate Kit Case (2x Matched 32x32 Sets)."""
    pid = "S9.3-01"
    cx, cy = -160.0, -1520.0
    dx, dy, dz = 340.0, 280.0, 140.0
    # 2x matched spare S2.1/S2.2 circular Ø100 mm cassette cradles inside clean ESD case
    cassettes = [
        make_tube(14.0, 50.0, 24.0, segments=28, axis="z", center=(cx - 72.0, cy, Z_FLOOR_MM + 32.0), name="s9_3_01_mems_set_1", material="Si"),
        make_tube(14.0, 50.0, 24.0, segments=28, axis="z", center=(cx + 72.0, cy, Z_FLOOR_MM + 32.0), name="s9_3_01_mems_set_2", material="Si"),
    ]
    mesh, feats = _make_cleanroom_kit_case(
        name=pid,
        cx=cx,
        cy=cy,
        dx=dx,
        dy=dy,
        dz=dz,
        material="Al 6061",
        interior_solids=cassettes,
    )
    target_mass = 6.8
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        design_tier="KIT_OR_ALIAS",
        material="Si",
        world_origin_mm=(cx, cy, Z_FLOOR_MM + 0.5 * dz),
        ports=(
            PortInterface("mems_spare_cassette_bay", "mechanical", (cx, cy, Z_FLOOR_MM + dz), (0.0, 0.0, 1.0), "2x Matched 32x32 Spare Aperture & Blanker Plates (±50 nm CD)", mating_part_id="S2.1-01", frame="world"),
        ),
        dimensions=(
            DimensionCallout("CASE_W", dx, 1.0, -1.0, view="front"),
            DimensionCallout("CASE_D", dy, 1.0, -1.0, view="right"),
            DimensionCallout("CASE_H", dz, 1.0, -1.0, view="front"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="ESD CASE BASE"),),
        notes=("2x matched spare 32x32 Si MEMS aperture & blanker plate sets from foundry shuttle lot.",),
        scad_params=(("qty_sets", 2), ("case_dx_mm", dx), ("case_dy_mm", dy), ("case_dz_mm", dz)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats), density_kg_m3=eff_rho)


def _build_s9_3_02() -> BuiltPart:
    """S9.3-02: Spare 4 K Cryo-LNA (InP HEMT), Isolator, Coax & Attenuator Field-Service Kit (4 Chains)."""
    pid = "S9.3-02"
    cx, cy = 280.0, -1520.0
    dx, dy, dz = 420.0, 320.0, 180.0
    # 4x spare cryo readout chain modules (4K HEMT + 20 mK isolator + cryo attenuator blocks)
    chains: list[SolidMesh] = []
    for i in range(4):
        bx = cx - 126.0 + i * 84.0
        chains.append(
            make_chamfered_box(58.0, 180.0, 36.0, chamfer=3.0, center=(bx, cy, Z_FLOOR_MM + 38.0), name=f"s9_3_02_cryo_chain_{i + 1}", material="OFHC Cu")
        )
    mesh, feats = _make_cleanroom_kit_case(
        name=pid,
        cx=cx,
        cy=cy,
        dx=dx,
        dy=dy,
        dz=dz,
        material="Al 6061",
        interior_solids=chains,
    )
    target_mass = 9.2
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        design_tier="KIT_OR_ALIAS",
        material="OFHC Cu",
        temp_k=4.0,
        world_origin_mm=(cx, cy, Z_FLOOR_MM + 0.5 * dz),
        ports=(
            PortInterface("cryo_chain_spare_kit", "rf", (cx, cy, Z_FLOOR_MM + dz), (0.0, 0.0, 1.0), "4x Spare 4K InP HEMT + Dual Isolator + Coax/Attenuator Chains", mating_part_id="S6.6-01", frame="world"),
        ),
        dimensions=(
            DimensionCallout("CASE_W", dx, 1.0, -1.0, view="front"),
            DimensionCallout("CASE_D", dy, 1.0, -1.0, view="right"),
            DimensionCallout("CASE_H", dz, 1.0, -1.0, view="front"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="ESD CASE RIM"),),
        notes=("4x spare 4K InP HEMT LNA + cryo isolator + attenuator/coax service kit (7% redundancy over 56 chains).",),
        scad_params=(("qty_chains", 4), ("case_dx_mm", dx), ("case_dy_mm", dy), ("case_dz_mm", dz)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats), density_kg_m3=eff_rho)


def _build_s9_3_03() -> BuiltPart:
    """S9.3-03: 10,000-Hr Pulse-Tube Adsorber, Scroll Tip-Seal & Cryo/Board Preventive Maintenance Kit Chest."""
    pid = "S9.3-03"
    cx, cy = 780.0, -1520.0
    dx, dy, dz = 460.0, 340.0, 260.0
    # Internal PT420 activated-carbon adsorber canister + scroll tip-seal & spare board/indium seal tray
    interior = [
        make_cylinder(54.0, 175.0, segments=24, axis="x", center=(cx - 95.0, cy, Z_FLOOR_MM + 80.0), name="s9_3_03_pt420_adsorber", material="316L"),
        make_box(160.0, 220.0, 75.0, center=(cx + 115.0, cy, Z_FLOOR_MM + 58.0), name="s9_3_03_seals_spares_tray", material="PTFE"),
    ]
    mesh, feats = _make_cleanroom_kit_case(
        name=pid,
        cx=cx,
        cy=cy,
        dx=dx,
        dy=dy,
        dz=dz,
        material="Steel",
        interior_solids=interior,
    )
    target_mass = 18.0
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        design_tier="KIT_OR_ALIAS",
        material="PTFE",
        world_origin_mm=(cx, cy, Z_FLOOR_MM + 0.5 * dz),
        ports=(
            PortInterface("pm_10khr_service_kit", "mechanical", (cx, cy, Z_FLOOR_MM + dz), (0.0, 0.0, 1.0), "10,000-hr PT420 Adsorber, Scroll Tip-Seal & Indium/Cryo Gasket Kit", mating_part_id="S6.1-02", frame="world"),
        ),
        dimensions=(
            DimensionCallout("CHEST_W", dx, 1.0, -1.0, view="front"),
            DimensionCallout("CHEST_D", dy, 1.0, -1.0, view="right"),
            DimensionCallout("CHEST_H", dz, 1.0, -1.0, view="front"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="SERVICE CHEST BASE"),),
        notes=("10,000-hr preventive maintenance kit: PT420 activated-carbon adsorber, scroll tip-seals, PTFE/Indium cryo seals.",),
        scad_params=(("chest_dx_mm", dx), ("chest_dy_mm", dy), ("chest_dz_mm", dz)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats), density_kg_m3=eff_rho)


def _build_s9_hpc_03() -> BuiltPart:
    """S9.HPC-03 (3.80 kg exact Exp143): 2.6 kW Redundant 80+ Titanium PSU Base Tray,
    Heavy-Duty 19" Sliding Rack Frame/Rails & Swept OM4 Fiber Bend-Radius Cable Duct (R>=40 mm).

    Open-interior rail stack at X = +2750.0 mm, Y = -700.0 mm, leaving X_local in [-246, +246],
    Y_local in [-390, +390], Z in [-918, -630] 100% OPEN so S9.HPC-01 & S9.HPC-02 sit inside with 0 clash!
    """
    pid = "S9.HPC-03"
    cx, cy = HPC_STACK_X_MM, HPC_STACK_Y_MM
    depth_y = 780.0
    y_front = cy - 0.5 * depth_y  # -1090.0 mm
    y_rear = cy + 0.5 * depth_y   # -310.0 mm
    base_h = 80.0  # Z in [-1000, -920]

    solids: list[SolidMesh] = [
        # Open-frame bottom plinth rails + dual hot-swap 2.6 kW 80+ Titanium PSU bricks (realistic hollow tray!)
        make_box(520.0, 48.0, 26.0, center=(cx, y_front + 24.0, Z_FLOOR_MM + 13.0), name="s9_hpc_03_front_skid", material="Steel"),
        make_box(520.0, 48.0, 26.0, center=(cx, y_rear - 24.0, Z_FLOOR_MM + 13.0), name="s9_hpc_03_rear_skid", material="Steel"),
        make_box(28.0, depth_y - 96.8, 26.0, center=(cx - 246.0, cy, Z_FLOOR_MM + 13.0), name="s9_hpc_03_skid_L", material="Steel"),
        make_box(28.0, depth_y - 96.8, 26.0, center=(cx + 246.0, cy, Z_FLOOR_MM + 13.0), name="s9_hpc_03_skid_R", material="Steel"),
        # Dual redundant 2.6 kW 80+ Titanium hot-swap PSU modules seated cleanly on plinth
        make_chamfered_box(110.0, 260.0, 52.0, chamfer=3.0, center=(cx - 95.0, y_front + 190.0, Z_FLOOR_MM + 52.4), name="s9_hpc_03_psu_a", material="Al 6061"),
        make_chamfered_box(110.0, 260.0, 52.0, chamfer=3.0, center=(cx + 95.0, y_front + 190.0, Z_FLOOR_MM + 52.4), name="s9_hpc_03_psu_b", material="Al 6061"),
    ]
    # 4x Heavy-duty 19" vertical sliding-rail rack posts strictly OUTSIDE |x_local| >= 248 mm (> 241.3 mm!)
    rail_h = 285.0  # rises from Z_FLOOR + 80.2 up to Z_FLOOR + 365.2 (clears S9.HPC-01 & S9.HPC-02!)
    rail_zc = Z_FLOOR_MM + base_h + 0.2 + 0.5 * rail_h
    for sgn_x in (-1.0, +1.0):
        for y_p in (y_front + 20.0, y_rear - 20.0):
            solids.append(
                make_box(16.0, 28.0, rail_h, center=(cx + sgn_x * 256.0, y_p, rail_zc), name="s9_hpc_03_rail_post", material="Steel")
            )
        # Side horizontal steel slide-rail channels linking front & rear posts outside |x_local| >= 248 mm
        for z_r in (Z_FLOOR_MM + 130.0, Z_FLOOR_MM + 220.0, Z_FLOOR_MM + 290.0):
            solids.append(
                make_box(14.0, depth_y - 68.4, 24.0, center=(cx + sgn_x * 256.0, cy, z_r), name="s9_hpc_03_slide_rail", material="Steel")
            )

    # OM4 MPO-12 optical fiber bend-radius management duct (R_bend = 45 mm >> 30 mm min bend radius)
    # Routed cleanly along +X outer flank (X_local = +278 mm, zero clash with nodes or switch!)
    om4_duct = make_swept_tube(
        [
            [cx + 278.0, y_front + 20.0, Z_FLOOR_MM + 290.0],
            [cx + 278.0, y_front + 65.0, Z_FLOOR_MM + 290.0],
            [cx + 278.0, y_front + 110.0, Z_FLOOR_MM + 245.0],
            [cx + 278.0, y_front + 110.0, Z_FLOOR_MM + 130.0],
            [cx + 278.0, y_rear - 40.0, Z_FLOOR_MM + 130.0],
        ],
        r_out=14.0,
        r_in=9.0,
        segments=18,
        name="s9_hpc_03_om4_bend_duct",
        material="Al 6061",
    )
    solids.append(om4_duct)

    mesh = merge_solids(solids, name=pid, material="Steel")
    target_mass = S9_HPC_TARGET_MASS_KG[pid]  # 3.80 kg exact Exp143
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="Steel",
        surface_finish_ra_um=1.6,
        world_origin_mm=(cx, cy, Z_FLOOR_MM + 0.5 * (base_h + rail_h)),
        ports=(
            PortInterface("psu_2p6kw_dual_in", "electrical", (cx, y_rear, Z_FLOOR_MM + 40.0), (0.0, 1.0, 0.0), "2x IEC C20 2.6 kW 80+ Titanium Redundant PSU", mating_part_id="S7.SAFETY-04", frame="world"),
            PortInterface("om4_fiber_duct_entry", "optical", (cx + 278.0, y_front + 20.0, Z_FLOOR_MM + 290.0), (0.0, -1.0, 0.0), "OM4 MPO-12 Bend-Radius Fiber Duct (R>=45 mm)", mating_part_id="S9.HPC-02", bore_mm=18.0, od_mm=28.0, frame="world"),
            PortInterface("hpc_4u_rail_bay", "mechanical", (cx, y_front, Z_FLOOR_MM + 175.0), (0.0, -1.0, 0.0), "EIA-310 Heavy-Duty Ball-Bearing Sliding Rails (5U Open Stack)", mating_part_id="S9.HPC-01", frame="world"),
        ),
        dimensions=(
            DimensionCallout("FRAME_W", 528.0, 1.0, -1.0, view="front"),
            DimensionCallout("RAIL_DEPTH", depth_y, 1.0, -1.0, view="right"),
            DimensionCallout("PSU_BASE_H", base_h, 0.5, -0.5, view="front"),
            DimensionCallout("OM4_R_BEND", 45.0, 1.0, -1.0, prefix="R", view="right"),
        ),
        gdt_frames=(GDTFrame("parallelism", 0.30, datum_primary="A", feature_note="SLIDING RACK RAILS"),),
        notes=(
            "Exp143 S9.HPC-03 (3.80 kg, 0 W extra load): redundant 2.6 kW 80+ Titanium PSU pack + sliding rails + OM4 bend-radius duct.",
            "Option-HPC stack centered at X=+2750 mm, Y=-700 mm (90 mm clear of Bay 2, 100 mm clear of S7.SAFETY-04 UPS).",
        ),
        scad_params=(("psu_kw", 2.6), ("rail_depth_mm", depth_y), ("om4_bend_r_mm", 45.0)),
        target_mass_kg=target_mass,
    )
    scad_feats = (
        ScadFeature("add_box", {"dx": 520.0, "dy": depth_y, "dz": base_h}, translate=(0.0, 0.0, -142.5), comment="2.6 kW redundant Titanium PSU plinth"),
        ScadFeature("add_box", {"dx": 16.0, "dy": depth_y, "dz": rail_h}, translate=(-256.0, 0.0, 40.0), comment="Left sliding rail assembly"),
        ScadFeature("add_box", {"dx": 16.0, "dy": depth_y, "dz": rail_h}, translate=(+256.0, 0.0, 40.0), comment="Right sliding rail assembly"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=scad_feats, density_kg_m3=eff_rho)


def _build_s9_hpc_01() -> BuiltPart:
    """S9.HPC-01 (56.00 kg exact Exp143): 2x 2U Dual-Accelerator QEC Decoder Compute Nodes
    (482.6 x 780.0 x 177.8 mm total 4U, 2x H100/Alveo-U280 + Dual-100G ConnectX-7 RoCEv2).
    """
    pid = "S9.HPC-01"
    cx, cy = HPC_STACK_X_MM, HPC_STACK_Y_MM
    depth_y = 780.0
    y_front = cy - 0.5 * depth_y  # -1090.0 mm
    h_2u = 86.9  # 88.9 mm 2U nominal minus 2.0 mm clearance
    z_n1 = Z_FLOOR_MM + 128.75  # spans [85.3, 172.2] -> 5.3 mm above PSU plinth Z=80!
    z_n2 = Z_FLOOR_MM + 219.75  # spans [176.3, 263.2] -> 4.1 mm airflow gap above Node #1!

    n1_m, n1_f = _make_19in_chassis(
        name="s9_hpc_01_node1",
        x_center=cx,
        y_front=y_front,
        z_center=z_n1,
        depth_mm=depth_y,
        height_mm=h_2u,
        material="Steel",
        n_front_connectors=4,  # Dual 100G QSFP28 ConnectX-7 + BMC/sync
        connector_r_mm=5.5,
        n_vent_slots=6,
    )
    n2_m, _ = _make_19in_chassis(
        name="s9_hpc_01_node2",
        x_center=cx,
        y_front=y_front,
        z_center=z_n2,
        depth_mm=depth_y,
        height_mm=h_2u,
        material="Steel",
        n_front_connectors=4,
        connector_r_mm=5.5,
        n_vent_slots=6,
    )
    mesh = merge_solids([n1_m, n2_m], name=pid, material="Steel")
    target_mass = S9_HPC_TARGET_MASS_KG[pid]  # 56.00 kg (28.0 kg x 2)
    eff_rho = _calibrated_density(mesh, target_mass)
    z_mid = 0.5 * (z_n1 + z_n2)

    design = make_part_design_from_bom(
        pid,
        material="Steel",
        world_origin_mm=(cx, cy, z_mid),
        ports=(
            PortInterface("connectx7_100g_node1", "optical", (cx + 100.0, y_front - 11.0, z_n1), (0.0, -1.0, 0.0), "2x 100GbE QSFP28 ConnectX-7 RoCEv2 RDMA (Node 1)", mating_part_id="S9.HPC-02", frame="world"),
            PortInterface("connectx7_100g_node2", "optical", (cx + 100.0, y_front - 11.0, z_n2), (0.0, -1.0, 0.0), "2x 100GbE QSFP28 ConnectX-7 RoCEv2 RDMA (Node 2)", mating_part_id="S9.HPC-02", frame="world"),
            PortInterface("hpc_psu_feed", "electrical", (cx + 150.0, y_front + depth_y + 12.0, z_mid), (0.0, 1.0, 0.0), "2100 W Dual-Redundant 230 VAC Feed", mating_part_id="S9.HPC-03", frame="world"),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5, view="front"),
            DimensionCallout("DEPTH_NODE", 780.0, 1.0, -1.0, view="right"),
            DimensionCallout("HEIGHT_4U_STACK", 177.8, 0.5, -0.5, view="front"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="2U FRONT EARS & RAILS"),),
        notes=(
            "Exp143 S9.HPC-01 (56.00 kg, 2100 W, 0 W cryo): 2x 2U QEC decoder GPU/FPGA compute nodes (d=37 e2e=6.34 us; qLDPC 2.32 us).",
            "Mounted inside S9.HPC-03 open rail stack at X=+2750 mm, Y=-700 mm.",
        ),
        scad_params=(("qty_nodes", 2), ("u_per_node", 2), ("depth_mm", 780.0), ("power_W", 2100)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(n1_f), density_kg_m3=eff_rho)


def _build_s9_hpc_02() -> BuiltPart:
    """S9.HPC-02 (4.20 kg exact Exp143): 1U Ultra-Low-Latency Cut-Through 100 GbE RoCEv2 Optical Switch
    + 4x QSFP28-100G-SR4 Transceivers + MPO-12 OM4 Optical Bridge (482.6 x 380.0 x 44.5 mm).
    """
    pid = "S9.HPC-02"
    cx, cy = HPC_STACK_X_MM, HPC_STACK_Y_MM
    depth_sw = 380.0
    y_front = cy - 390.0  # -1090.0 mm, flush with Node 1/2 front face
    h_1u = 42.5  # 44.5 mm nominal minus 2.0 mm clearance
    z_sw = Z_FLOOR_MM + 290.0  # spans [268.75, 311.25] -> 5.55 mm above Node #2 top Z=263.2!

    sw_m, sw_f = _make_19in_chassis(
        name="s9_hpc_02_switch",
        x_center=cx,
        y_front=y_front,
        z_center=z_sw,
        depth_mm=depth_sw,
        height_mm=h_1u,
        material="Al 6061",
        n_front_connectors=0,
        n_vent_slots=3,
        add_handles=False,
    )
    # 4x protruding QSFP28-100G-SR4 optical transceivers + MPO-12 latch blocks along front bezel
    solids: list[SolidMesh] = [sw_m]
    for q_i in range(4):
        qx = cx + 35.0 + q_i * 34.0
        solids.append(
            make_box(
                18.5,
                28.0,
                13.5,
                center=(qx, y_front - 14.2, z_sw),
                name=f"s9_hpc_02_qsfp28_{q_i + 1}",
                material="Al 6061",
            )
        )
    mesh = merge_solids(solids, name=pid, material="Al 6061")
    target_mass = S9_HPC_TARGET_MASS_KG[pid]  # 4.20 kg exact Exp143
    eff_rho = _calibrated_density(mesh, target_mass)

    design = make_part_design_from_bom(
        pid,
        material="Al 6061",
        world_origin_mm=(cx, y_front + 0.5 * depth_sw, z_sw),
        ports=(
            PortInterface("qsfp28_100g_4port", "optical", (cx + 86.0, y_front - 28.2, z_sw), (0.0, -1.0, 0.0), "4x QSFP28-100G-SR4 + 20 m OM4 MPO-12 (0.777 us ingest)", mating_part_id="S6.11-01", frame="world"),
            PortInterface("switch_downlink_nodes", "optical", (cx + 52.0, y_front - 28.2, z_sw), (0.0, -1.0, 0.0), "Cut-Through 100GbE RoCEv2 to S9.HPC-01", mating_part_id="S9.HPC-01", frame="world"),
        ),
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5, view="front"),
            DimensionCallout("DEPTH_1U_SW", 380.0, 1.0, -1.0, view="right"),
            DimensionCallout("HEIGHT_1U", 44.5, 0.5, -0.5, view="front"),
        ),
        gdt_frames=(GDTFrame("flatness", 0.5, datum_primary="", feature_note="1U SWITCH FACEPLATE"),),
        notes=(
            "Exp143 S9.HPC-02 (4.20 kg, 95 W, 0 W cryo): 1U cut-through 100GbE RoCEv2 optical switch + 4x QSFP28-100G-SR4.",
            "Stacked cleanly above S9.HPC-01 at Z=+290 mm (5.55 mm clearance).",
        ),
        scad_params=(("u_count", 1), ("depth_mm", 380.0), ("qsfp28_ports", 4), ("ingest_us", 0.777)),
        target_mass_kg=target_mass,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(sw_f), density_kg_m3=eff_rho)


# ---------------------------------------------------------------------------
# Public Builder Registry & Unified Export Pipeline
# ---------------------------------------------------------------------------
_S9_SPARES_HPC_BUILDERS = (
    _build_s9_1_01,
    _build_s9_1_02,
    _build_s9_2_01,
    _build_s9_2_02,
    _build_s9_3_01,
    _build_s9_3_02,
    _build_s9_3_03,
    _build_s9_hpc_01,
    _build_s9_hpc_02,
    _build_s9_hpc_03,
)


def build_s9_spares_hpc_parts() -> dict[str, BuiltPart]:
    """Build all 10 / 10 non-OptQ physical BOM parts of Subsystem S9 (Cal/Spares + Option-HPC)."""
    parts: dict[str, BuiltPart] = {}
    for builder in _S9_SPARES_HPC_BUILDERS:
        bp = builder()
        parts[bp.design.part_id] = bp
    expected = {p for p in list_physical_part_ids("S9") if not p.startswith("S9.4-")}
    if set(parts.keys()) != expected:
        raise RuntimeError(
            f"S9 non-OptQ part mismatch: built={sorted(parts)} vs expected={sorted(expected)}"
        )
    return parts


def export_s9_spares_hpc_all(out_dir: Path | str | None = None) -> dict[str, PartArtifactResult]:
    """Export all 5 CAD artifacts (.stl/.step/.scad/.dxf/.svg) + .json manifest for all 10 S9 non-OptQ parts."""
    target_dir = Path(out_dir) if out_dir is not None else S9_OUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    parts = build_s9_spares_hpc_parts()
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
        part_json: dict[str, Any] = {
            "part_design": bp.design.to_dict(),
            "artifact": res.to_dict(),
            "shell_bboxes_mm": _shell_bboxes(bp.mesh),
            "reconciliation_notes": list(bp.reconciliation_notes),
        }
        (target_dir / f"{pid}.json").write_text(
            json.dumps(part_json, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    hpc_masses = {
        pid: round(results[pid].mass_kg, 4)
        for pid in sorted(S9_HPC_TARGET_MASS_KG.keys())
    }
    summary = {
        "subsystem": "S9_spares_hpc",
        "part_count": len(results),
        "all_valid": all(r.all_valid for r in results.values()),
        "total_mass_kg": round(sum(r.mass_kg for r in results.values()), 4),
        "option_hpc_masses_kg": hpc_masses,
        "option_hpc_total_mass_kg": round(sum(hpc_masses.values()), 4),
        "hpc_stack_center_xy_mm": [HPC_STACK_X_MM, HPC_STACK_Y_MM],
        "z_wafer_mm": Z_WAFER_MM,
        "z_floor_mm": Z_FLOOR_MM,
        "epistemic": {
            "design_maturity": DESIGN_MATURITY,
            "no_lab_measurement": NO_LAB_MEASUREMENT,
            "iec61508_certified": IEC61508_CERTIFIED,
            "semi_s2_certified": SEMI_S2_CERTIFIED,
            "general_tolerance_std": GENERAL_TOLERANCE_STD,
        },
        "part_ids": sorted(results.keys()),
    }
    (target_dir / "S9_spares_hpc_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return results


def export_all(out_dir: Path | str | None = None) -> dict[str, PartArtifactResult]:
    """Alias exposing unified ``export_all()`` for S9 non-OptQ parts."""
    return export_s9_spares_hpc_all(out_dir=out_dir)


if __name__ == "__main__":
    res_map = export_all()
    print(f"Exported S9_spares_hpc: {len(res_map)}/10 parts, all_valid={all(r.all_valid for r in res_map.values())}")
