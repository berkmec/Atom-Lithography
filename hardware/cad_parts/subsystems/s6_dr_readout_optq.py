"""Subsystem S6 (Part 2/2) & Option-Q: 20 mK Dilution Refrigerator, Cryo-Readout & S9.4.

Wave 2B / WP-M4 — Atom Lithography Machine Full 180-Part Hardware Blueprint.
Designs the remaining 22 / 43 physical parts assigned to WP-M4:
- S6.6-01..07: 56x 4 K InP HEMT ring, 56x cryo-isolator plate, 56x input/output cryo coax looms,
               56x RT LNA bank (Bay 2 U19-U21), 14x ZCU216 RFSoC enclosures (Bay 2 U25-U38),
               9000-ch NbTiN spiral multiplexed resonator chip package (in Nb Meissner quiet zone)
- S6.7-01..02: 56x rf-SET LC tank modules (20 mK), 8x 4 K cryo-CMOS bias/control card cage
- S6.8-01/02/04: 20 mK dry DR insert tower (50K/4K/Still/CP/MXC plates, Ag-sinter HX, rods),
                 3He/4He GHS floor cabinet (X=-1300, Y=-800 mm),
                 DR OVC w/ ISO-K flanges, ASME DN50 rupture-disk nozzle clearance (S7.SAFETY-05) & frame
- S6.10-01/03/04: 3 kOhm NbTiN M4 cavity-QED bus chip package (20 mK),
                  4 K SKY130 968-gate crossbar carrier (fixing old S6.6 alias),
                  M4 20-bit DC gate DAC & RC/Eccosorb filter rack unit (Bay 2 U7-U8)
- S6.11-01..04: 2U ZU48DR RFSoC Q16.16 BOED-FPGA chassis (Bay 2 U22-U23, 11.50 kg, fixing old S6.5 alias),
                32x 20 mK TWPA + Purcell + dual-isolator magnetic shield box (2.72 kg),
                32x 4 K InP HEMT bank (1.02 kg),
                96-line CuNi/NbTi cryo-coax loom & stepped attenuator/Eccosorb clamps (4.03 kg)
- S9.4-01..03 (Option-Q, fixing old S9.1 alias):
                OVC -X CF63 4xSMA + 1550 nm SMF-28 vacuum feedthrough (3.20 kg),
                20 mK shielded NbTiN 5-stage Chebyshev 50 Ohm <-> 3 kOhm qRAM box (0.38 kg),
                Option-Q 4x NbTi cryo-coax + 1550 nm SMF-28 cryo-fiber loom & clamps (0.82 kg)

Exposes public Wave 2B/2C integration API:
- ``build_s6_parts() -> dict[str, BuiltPart]`` (ALL 40 physical parts of S6)
- ``build_s9_optq_parts() -> dict[str, BuiltPart]`` (ALL 3 physical parts of S9.4)
- ``export_all(out_s6_dir=..., out_s9_optq_dir=...) -> dict[str, Any]``

Epistemic Status: M0_M1_DETAILED_CAD_DESIGN_ONLY, no_lab_measurement=True,
iec61508_certified=False, semi_s2_certified=False.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from hardware.cad_parts.core import (
    DESIGN_MATURITY,
    IEC61508_CERTIFIED,
    NO_LAB_MEASUREMENT,
    REPO_ROOT,
    SEMI_S2_CERTIFIED,
    DimensionCallout,
    GDTFrame,
    PortInterface,
    ScadFeature,
    SolidMesh,
    list_physical_part_ids,
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
    make_tube,
    merge_solids,
    rect_2d,
    transform_mesh,
)
from hardware.cad_parts.subsystems.s6_magnet_shields import (
    DEFAULT_OUT_S6_DIR,
    DEFAULT_OUT_S9_OPTQ_DIR,
    DR_X_MM,
    DR_Y_MM,
    RACK_BAY2_X_MM,
    RACK_BAY2_Y_MM,
    Z_CRYO_BRIDGE_MM,
    BuiltPart,
    build_s6_magnet_shields_parts,
    check_assembly_clashes,
    export_part_with_json,
    make_arc_tube,
    make_hollow_frame,
    make_rack_chassis_19in,
    make_staged_coax_loom,
    rack_u_center_and_height,
    run_cryo_thermal_checks,
)

S6_DR_READOUT_PART_IDS: tuple[str, ...] = (
    "S6.6-01",
    "S6.6-02",
    "S6.6-03",
    "S6.6-04",
    "S6.6-05",
    "S6.6-06",
    "S6.6-07",
    "S6.7-01",
    "S6.7-02",
    "S6.8-01",
    "S6.8-02",
    "S6.8-04",
    "S6.10-01",
    "S6.10-03",
    "S6.10-04",
    "S6.11-01",
    "S6.11-02",
    "S6.11-03",
    "S6.11-04",
)

S9_OPTQ_PART_IDS: tuple[str, ...] = (
    "S9.4-01",
    "S9.4-02",
    "S9.4-03",
)


# ---------------------------------------------------------------------------
# S6.6 Multiplexed Cryo-Readout Builders (7 parts)
# ---------------------------------------------------------------------------
def _build_s6_6_01() -> BuiltPart:
    """S6.6-01: 56x 4 K ultra-low-power InP HEMT LNA annular mounting ring."""
    # World origin: (-650, 0, 700.0) -> z_global = [682.0, 718.0] (2 mm below 4K plate z=720)
    # R_in = 98.0, R_out = 126.0 mm (clears inner coax/rods R<=92 and 4K shield R_in=132!)
    parts: list[SolidMesh] = []
    ring = make_ring_with_bolt_circle(
        r_in=98.0,
        r_out=126.0,
        thickness=6.0,
        pcd=224.0,
        n_bolts=16,
        bolt_diameter=3.2,
        sub_per_side=2,
        center=(0.0, 0.0, 15.0),
        name="hemt56_mount_ring",
        material="OFHC Cu",
    )
    parts.append(ring)
    # 56 distinct gold-plated OFHC Cu InP HEMT module housings arrayed cleanly around the ring
    # Outer tier (32 modules @ R=118.5) + Inner tier (24 modules @ R=105.0) = 56 exact modules!
    for tier_n, r_pos, z_c in ((32, 118.5, -3.0), (24, 105.0, -3.0)):
        for k in range(tier_n):
            ang = 360.0 * k / tier_n
            rad = math.radians(ang)
            cx, cy = r_pos * math.cos(rad), r_pos * math.sin(rad)
            mod = make_box(8.0, 6.2, 28.0, name=f"hemt56_{tier_n}_{k}", material="OFHC Cu")
            parts.append(transform_mesh(mod, rotation_deg=(0.0, 0.0, ang), translation=(cx, cy, z_c)))

    mesh = merge_solids(parts, name="S6.6-01", material="OFHC Cu")
    ports = (
        PortInterface("ring_4k_mount", "thermal", (0.0, 0.0, 18.0), (0.0, 0.0, 1.0), "16x M3 Au-OFHC 4K Mount", mating_part_id="S6.8-01", bore_mm=196.0, od_mm=252.0, pcd_mm=224.0, bolt_count=16, bolt_hole_mm=3.2, bolt_spec="M3"),
        PortInterface("sma_56ch_in", "rf", (0.0, 0.0, -17.0), (0.0, 0.0, -1.0), "56x Cryo SMA InP HEMT Ports", mating_part_id="S6.6-04"),
    )
    design = make_part_design_from_bom(
        "S6.6-01",
        material="OFHC Cu",
        world_origin_mm=(DR_X_MM, DR_Y_MM, 700.0),
        ports=ports,
        dimensions=(
            DimensionCallout("RING_OD", 252.0, 0.1, -0.1, prefix="Ø"),
            DimensionCallout("RING_ID", 196.0, 0.1, -0.1, prefix="Ø"),
            DimensionCallout("RING_H", 36.0, 0.1, -0.1),
        ),
        gdt_frames=(GDTFrame("flatness", 0.02, datum_primary="A", feature_note="4 K thermal clamp ring face"),),
        scad_params=(("n_hemt", 56), ("ring_id", 196.0), ("ring_od", 252.0), ("p_dc_mw_per_ch", 2.1)),
        target_mass_kg=1.85,
    )
    feats = (
        ScadFeature("add_tube", {"od": 252.0, "id": 196.0, "h": 6.0}, translate=(0.0, 0.0, 15.0), comment="4 K OFHC HEMT ring"),
        ScadFeature("cut_bolt_circle", {"pcd": 224.0, "bolt_d": 3.2, "count": 16, "h": 8.0}, translate=(0.0, 0.0, 15.0), comment="16x M3 thermal clamp bolts"),
        ScadFeature("add_tube", {"od": 248.0, "id": 200.0, "h": 28.0}, translate=(0.0, 0.0, -3.0), comment="56x InP HEMT module array envelope"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=5800.0)


def _build_s6_6_02() -> BuiltPart:
    """S6.6-02: 56x Cryogenic isolator / circulator shielded mounting plate (20 mK)."""
    # World origin: (-650, 0, 366.0) -> z_global = [348.0, 384.0], R_out = 98.0 (inside Still shield R_in=116!)
    parts: list[SolidMesh] = []
    plate = make_ring_with_bolt_circle(
        r_in=14.0,
        r_out=98.0,
        thickness=6.0,
        pcd=180.0,
        n_bolts=12,
        bolt_diameter=3.2,
        sub_per_side=2,
        center=(0.0, 0.0, 15.0),
        name="iso56_carrier_plate",
        material="OFHC Cu",
    )
    parts.append(plate)
    # 56 magnetically shielded cryogenic circulator/isolator modules: 20 inner @ R=48 + 36 outer @ R=78
    for tier_n, r_pos in ((20, 48.0), (36, 78.0)):
        for k in range(tier_n):
            ang = 360.0 * k / tier_n
            rad = math.radians(ang)
            cx, cy = r_pos * math.cos(rad), r_pos * math.sin(rad)
            parts.append(
                make_cylinder(
                    radius=5.4,
                    height=28.0,
                    segments=12,
                    center=(cx, cy, -3.0),
                    name=f"cryo_iso_{tier_n}_{k}",
                    material="Mu-metal",
                )
            )

    mesh = merge_solids(parts, name="S6.6-02", material="OFHC Cu")
    ports = (
        PortInterface("mxc_hang_bolts", "thermal", (0.0, 0.0, 18.0), (0.0, 0.0, 1.0), "12x M3 Au-OFHC Plate", mating_part_id="S6.8-01", od_mm=196.0, pcd_mm=180.0, bolt_count=12, bolt_hole_mm=3.2, bolt_spec="M3"),
        PortInterface("iso_56ch_rf", "rf", (0.0, 0.0, -17.0), (0.0, 0.0, -1.0), "56x Dual-Junction >=20 dB Isolators", mating_part_id="S6.6-04"),
    )
    design = make_part_design_from_bom(
        "S6.6-02",
        material="OFHC Cu",
        world_origin_mm=(DR_X_MM, DR_Y_MM, 366.0),
        ports=ports,
        dimensions=(
            DimensionCallout("PLATE_OD", 196.0, 0.1, -0.1, prefix="Ø"),
            DimensionCallout("ASSY_H", 36.0, 0.1, -0.1),
        ),
        gdt_frames=(GDTFrame("flatness", 0.02, datum_primary="A", feature_note="20 mK thermalization plate"),),
        scad_params=(("n_isolators", 56), ("plate_od", 196.0), ("isolation_db", 20.0)),
        target_mass_kg=2.6,
    )
    feats = (
        ScadFeature("add_tube", {"od": 196.0, "id": 28.0, "h": 6.0}, translate=(0.0, 0.0, 15.0), comment="OFHC 56-ch isolator thermal plate"),
        ScadFeature("cut_bolt_circle", {"pcd": 180.0, "bolt_d": 3.2, "count": 12, "h": 8.0}, translate=(0.0, 0.0, 15.0), comment="12x M3 mounting bolt circle"),
        ScadFeature("add_tube", {"od": 170.0, "id": 82.0, "h": 28.0}, translate=(0.0, 0.0, -3.0), comment="56x magnetically shielded cryo isolators"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=5400.0)


def _build_s6_6_03() -> BuiltPart:
    """S6.6-03: 56x Input SS304 cryo coax lines + 3x stepped attenuator thermal clamps (300K->20mK)."""
    z_orig = 669.0
    spans = (
        ("50k_4k", 752.0, 836.0),
        ("4k_still", 618.0, 718.0),
        ("still_cp", 554.0, 602.0),
        ("cp_mxc", 502.0, 540.0),
    )
    mesh, feats = make_staged_coax_loom(18, 44.0, 22.0, spans, z_orig, attenuator_r=4.2, material="304 SS", name="S6.6-03")
    ports = (
        PortInterface("in56_top_50k", "rf", (0.0, 0.0, 836.0 - z_orig), (0.0, 0.0, 1.0), "56x SS304 0.086-in Input Loom", mating_part_id="S6.8-04"),
        PortInterface("in56_bot_mxc", "rf", (0.0, 0.0, 502.0 - z_orig), (0.0, 0.0, -1.0), "56x 3-Stage Attenuated MXC Feed", mating_part_id="S6.8-01"),
    )
    design = make_part_design_from_bom(
        "S6.6-03",
        material="304 SS",
        world_origin_mm=(DR_X_MM, 76.0, z_orig),
        ports=ports,
        dimensions=(
            DimensionCallout("CLAMP_W", 44.0, 0.2, -0.2),
            DimensionCallout("CLAMP_D", 22.0, 0.2, -0.2),
            DimensionCallout("SPAN_Z", 334.0, 0.5, -0.5),
        ),
        scad_params=(("n_chains", 56), ("coax_od_mm", 2.19), ("att_stages", 3)),
        target_mass_kg=2.4,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_6_04() -> BuiltPart:
    """S6.6-04: 56x Output superconducting NbTi (MXC->4K) + SS304 (4K->300K) coax lines & thermal clamps."""
    z_orig = 669.0
    spans = (
        ("50k_4k", 752.0, 836.0),
        ("4k_still", 618.0, 718.0),
        ("still_cp", 554.0, 602.0),
        ("cp_mxc", 502.0, 540.0),
    )
    mesh, feats = make_staged_coax_loom(18, 44.0, 22.0, spans, z_orig, attenuator_r=0.0, material="NbTi", name="S6.6-04")
    ports = (
        PortInterface("out56_top_50k", "rf", (0.0, 0.0, 836.0 - z_orig), (0.0, 0.0, 1.0), "56x SS304 Output to RT LNA", mating_part_id="S6.6-05"),
        PortInterface("out56_bot_mxc", "rf", (0.0, 0.0, 502.0 - z_orig), (0.0, 0.0, -1.0), "56x NbTi Lossless MXC->4K Loom", mating_part_id="S6.6-02"),
    )
    design = make_part_design_from_bom(
        "S6.6-04",
        material="NbTi",
        world_origin_mm=(DR_X_MM, -76.0, z_orig),
        ports=ports,
        dimensions=(
            DimensionCallout("CLAMP_W", 44.0, 0.2, -0.2),
            DimensionCallout("CLAMP_D", 22.0, 0.2, -0.2),
            DimensionCallout("SPAN_Z", 334.0, 0.5, -0.5),
        ),
        scad_params=(("n_chains", 56), ("loss_db_per_m", 0.1), ("superconducting_span", "MXC_to_4K")),
        target_mass_kg=2.2,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_6_05() -> BuiltPart:
    """S6.6-05: 56x Room-temp low-noise RF amplifier bank (Mini-Circuits ZX60 class, 3U, Bay 2 U19..U21)."""
    zc, dz = rack_u_center_and_height(19, 3)
    mesh, feats = make_rack_chassis_19in(420.0, dz, n_subunits=3, n_front_ports=14, material="Al 6061", name="S6.6-05")
    ports = (
        PortInterface("rt_lna_56ch_in", "rf", (0.0, 210.0, 0.0), (0.0, 1.0, 0.0), "56x SMA Rear Input", mating_part_id="S6.6-04"),
        PortInterface("rt_lna_56ch_out", "rf", (0.0, -217.0, 0.0), (0.0, -1.0, 0.0), "56x SMA +20 dB Front Out", mating_part_id="S6.6-06"),
    )
    design = make_part_design_from_bom(
        "S6.6-05",
        material="Al 6061",
        world_origin_mm=(RACK_BAY2_X_MM, RACK_BAY2_Y_MM, zc),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5),
            DimensionCallout("DEPTH", 420.0, 1.0, -1.0),
            DimensionCallout("HEIGHT_3U", dz, 0.3, -0.3),
        ),
        scad_params=(("rack_u", 3), ("u_start", 19), ("n_lna", 56), ("gain_db", 20.0)),
        target_mass_kg=13.5,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_6_06() -> BuiltPart:
    """S6.6-06: 14x AMD ZCU216 RFSoC digitizer/AWG rack enclosures (7x 2U dual-board = 14U, Bay 2 U25..U38)."""
    zc, dz = rack_u_center_and_height(25, 14)
    mesh, feats = make_rack_chassis_19in(540.0, dz, n_subunits=7, n_front_ports=14, material="Al 6061", name="S6.6-06")
    ports = (
        PortInterface("rfsoc_56ch_rf", "rf", (0.0, -277.0, 0.0), (0.0, -1.0, 0.0), "14x ZCU216 XM655 56-ch RF", mating_part_id="S6.6-05"),
        PortInterface("rack_bay2_u25_u38", "mechanical", (0.0, -270.0, 0.0), (0.0, -1.0, 0.0), '19" EIA-310 14U (7x2U, U25-U38)', mating_part_id="S7.4-03"),
    )
    design = make_part_design_from_bom(
        "S6.6-06",
        material="Al 6061",
        world_origin_mm=(RACK_BAY2_X_MM, RACK_BAY2_Y_MM, zc),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5),
            DimensionCallout("DEPTH", 540.0, 1.0, -1.0),
            DimensionCallout("HEIGHT_14U", dz, 0.5, -0.5),
        ),
        notes=("Reconciled 42U Rack Bay 2 U-allocation: 14x ZCU216 housed in 7x 2U dual-card 19-in EMI enclosures (U25-U38), resolving legacy single-30U lumping.",),
        scad_params=(("rack_u", 14), ("u_start", 25), ("n_zcu216_cards", 14), ("n_2u_enclosures", 7)),
        target_mass_kg=78.0,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_6_07() -> BuiltPart:
    """S6.6-07: 9000-ch NbTiN superconducting spiral multiplexed resonator chip & OFHC/Nb package (20 mK)."""
    # World origin: (0.0, 0.0, 345.0) — seated cleanly inside S6.3-03 Nb Meissner quiet zone (R_in=32, z_loc=[-16.5, +16.5])!
    # Package OD = 50.0 mm (R=25.0 -> 7.0 mm radial clearance to Nb cup!), local z = [-14.5, +9.0]
    parts: list[SolidMesh] = []
    # Main Ø50 mm gold-plated OFHC Cu resonator carrier housing with 4x M2 clamp bolt holes
    carrier = make_ring_with_bolt_circle(
        r_in=11.5,
        r_out=25.0,
        thickness=6.0,
        pcd=40.0,
        n_bolts=4,
        bolt_diameter=2.2,
        sub_per_side=2,
        center=(0.0, 0.0, 0.0),
        name="nbtin_pkg_ring",
        material="OFHC Cu",
    )
    parts.append(carrier)
    # Recessed OFHC basefloor under chip pocket (z_local = [-5.0, -3.1])
    parts.append(make_cylinder(25.0, 1.9, segments=36, center=(0.0, 0.0, -4.05), name="nbtin_pkg_floor", material="OFHC Cu"))
    # High-R 28Si / NbTiN 9000-ch spiral resonator die (16x16x0.8 mm seated inside Ø23 mm pocket!)
    parts.append(make_box(16.0, 16.0, 0.8, center=(0.0, 0.0, -2.5), name="nbtin_9000ch_die", material="Si"))
    # 4x SMP cryogenic RF launch barrels on top rim (z_local = [+3.1, +8.5])
    for idx, ang_deg in enumerate((45.0, 135.0, 225.0, 315.0), start=1):
        rad = math.radians(ang_deg)
        lx, ly = 16.0 * math.cos(rad), 16.0 * math.sin(rad)
        parts.append(make_cylinder(2.2, 5.4, segments=12, center=(lx, ly, 5.8), name=f"nbtin_smp_{idx}", material="BeCu"))
    # Bottom OFHC Cu 20 mK thermal stem (R=8.0, z_local = [-14.5, -5.1], 2.0 mm above Nb cup interior z=-16.5!)
    parts.append(make_cylinder(8.0, 9.4, segments=24, center=(0.0, 0.0, -9.8), name="nbtin_thermal_stem", material="OFHC Cu"))

    mesh = merge_solids(parts, name="S6.6-07", material="OFHC Cu")
    ports = (
        PortInterface("smp_4port_top", "rf", (0.0, 0.0, 8.5), (0.0, 0.0, 1.0), "4x Cryo SMP Feedthrough Launch", mating_part_id="S6.3-03", od_mm=36.0),
        PortInterface("thermal_20mk_stem", "thermal", (0.0, 0.0, -14.5), (0.0, 0.0, -1.0), "Ø16 mm Au-OFHC 20 mK Stem", mating_part_id="S6.3-03", od_mm=16.0),
    )
    design = make_part_design_from_bom(
        "S6.6-07",
        material="OFHC Cu",
        world_origin_mm=(0.0, 0.0, 345.0),
        ports=ports,
        dimensions=(
            DimensionCallout("PKG_OD", 50.0, 0.03, -0.03, prefix="Ø"),
            DimensionCallout("DIE_SIZE", 16.0, 0.02, -0.02),
            DimensionCallout("TOTAL_H", 23.0, 0.05, -0.05),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.005, datum_primary="A", feature_note="Si/NbTiN die seating floor"),
            GDTFrame("concentricity", 0.020, diameter_zone=True, datum_primary="B", feature_note="Quiet-zone centering OD"),
        ),
        scad_params=(("pkg_od", 50.0), ("n_resonators", 9000), ("b_max_ut", 22.3), ("ql_nom", 1000)),
        target_mass_kg=0.14,
    )
    feats = (
        ScadFeature("add_cylinder", {"d": 50.0, "h": 7.9}, translate=(0.0, 0.0, -1.05), comment="Ø50 mm OFHC resonator carrier"),
        ScadFeature("cut_bolt_circle", {"pcd": 40.0, "bolt_d": 2.2, "count": 4, "h": 8.0}, comment="4x M2 package clamp bolts"),
        ScadFeature("add_cylinder", {"d": 16.0, "h": 9.4}, translate=(0.0, 0.0, -9.8), comment="20 mK thermal stem"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


# ---------------------------------------------------------------------------
# S6.7 rf-SET & 4 K Cryo-CMOS Bias Modules (2 parts)
# ---------------------------------------------------------------------------
def _build_s6_7_01() -> BuiltPart:
    """S6.7-01: 56x SET / rf-SET cryogenic LC tank-circuit front-ends & bias-tee plate (20 mK)."""
    # World origin: (-650, 0, 310.0) -> z_global = [292.0, 328.0] (20 mm below S6.6-02, 16 mm above Still bottom cap!)
    parts: list[SolidMesh] = []
    plate = make_ring_with_bolt_circle(
        r_in=12.0,
        r_out=94.0,
        thickness=5.5,
        pcd=172.0,
        n_bolts=12,
        bolt_diameter=3.2,
        sub_per_side=2,
        center=(0.0, 0.0, 15.0),
        name="rfset56_baseplate",
        material="OFHC Cu",
    )
    parts.append(plate)
    # 56 shielded LC tank + bias-tee pockets: 20 inner @ R=44 + 36 outer @ R=74
    for tier_n, r_pos in ((20, 44.0), (36, 74.0)):
        for k in range(tier_n):
            ang = 360.0 * k / tier_n
            rad = math.radians(ang)
            cx, cy = r_pos * math.cos(rad), r_pos * math.sin(rad)
            mod = make_box(11.0, 7.5, 26.0, name=f"rfset_tank_{tier_n}_{k}", material="OFHC Cu")
            parts.append(transform_mesh(mod, rotation_deg=(0.0, 0.0, ang), translation=(cx, cy, -2.5)))

    mesh = merge_solids(parts, name="S6.7-01", material="OFHC Cu")
    ports = (
        PortInterface("rfset_20mk_mount", "thermal", (0.0, 0.0, 17.75), (0.0, 0.0, 1.0), "12x M3 Au-OFHC 20 mK Mount", mating_part_id="S6.8-01", od_mm=188.0, pcd_mm=172.0, bolt_count=12, bolt_hole_mm=3.2, bolt_spec="M3"),
        PortInterface("rfset_56ch_smp", "rf", (0.0, 0.0, -15.5), (0.0, 0.0, -1.0), "56x SMP rf-SET LC Tank + Bias-Tee", mating_part_id="S6.7-02"),
    )
    design = make_part_design_from_bom(
        "S6.7-01",
        material="OFHC Cu",
        world_origin_mm=(DR_X_MM, DR_Y_MM, 310.0),
        ports=ports,
        dimensions=(
            DimensionCallout("PLATE_OD", 188.0, 0.1, -0.1, prefix="Ø"),
            DimensionCallout("ASSY_H", 33.5, 0.1, -0.1),
        ),
        scad_params=(("n_rfset_modules", 56), ("plate_od", 188.0), ("f_tank_mhz", 320.0)),
        target_mass_kg=1.95,
    )
    feats = (
        ScadFeature("add_tube", {"od": 188.0, "id": 24.0, "h": 5.5}, translate=(0.0, 0.0, 15.0), comment="20 mK rf-SET OFHC carrier"),
        ScadFeature("cut_bolt_circle", {"pcd": 172.0, "bolt_d": 3.2, "count": 12, "h": 8.0}, translate=(0.0, 0.0, 15.0), comment="12x M3 clamp bolts"),
        ScadFeature("add_tube", {"od": 162.0, "id": 74.0, "h": 26.0}, translate=(0.0, 0.0, -2.5), comment="56x shielded rf-SET LC tank modules"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=4600.0)


def _build_s6_7_02() -> BuiltPart:
    """S6.7-02: 8x Cryo-CMOS / DC gate-voltage mux distribution card cage (4 K)."""
    # World origin: (-650, 0, 656.0) -> z_global = [632.0, 680.0], 76 x 58 x 48 mm
    # Clears S6.10-03 (z>=690) by 10 mm, Still plate (z<=616) by 16 mm, HEMT ring (R>=98) by 50 mm!
    dx, dy, dz = 76.0, 58.0, 48.0
    parts: list[SolidMesh] = []
    # Gold-plated OFHC Cu open-sided 8-slot card cage (top/bottom thermal clamp plates + side guide rails)
    parts.append(
        make_rect_plate_with_features(
            dx, dy, 4.0,
            circular_holes=((-32.0, -23.0, 3.2), (32.0, -23.0, 3.2), (32.0, 23.0, 3.2), (-32.0, 23.0, 3.2)),
            hole_segments=10,
            center=(0.0, 0.0, 0.5 * dz - 2.0),
            name="cmos_cage_top",
            material="OFHC Cu",
        )
    )
    parts.append(make_box(dx, dy, 4.0, center=(0.0, 0.0, -0.5 * dz + 2.0), name="cmos_cage_bot", material="OFHC Cu"))
    for sgn in (-1.0, 1.0):
        parts.append(make_box(4.0, dy, dz - 8.4, center=(sgn * (0.5 * dx - 2.0), 0.0, 0.0), name=f"cmos_side_{int(sgn>0)}", material="OFHC Cu"))
    # 8x parallel Rogers/Cu DC gate-mux cards inside cage (spaced along X)
    xs = np.linspace(-28.0, 28.0, 8)
    for idx, cx in enumerate(xs):
        parts.append(make_box(2.0, dy - 6.0, dz - 10.0, center=(float(cx), 0.0, 0.0), name=f"cmos_card_{idx}", material="Rogers"))

    mesh = merge_solids(parts, name="S6.7-02", material="OFHC Cu")
    ports = (
        PortInterface("cage_4k_thermal", "thermal", (0.0, 0.0, 24.0), (0.0, 0.0, 1.0), "4x M3 Au-OFHC 4K Thermal Bus", mating_part_id="S6.10-03", bolt_count=4, bolt_hole_mm=3.2, bolt_spec="M3"),
        PortInterface("dc_mux_microd", "connector", (0.0, 29.0, 0.0), (0.0, 1.0, 0.0), "8x 37-pin Micro-D DC Bias", mating_part_id="S6.7-01"),
    )
    design = make_part_design_from_bom(
        "S6.7-02",
        material="OFHC Cu",
        world_origin_mm=(DR_X_MM, DR_Y_MM, 656.0),
        ports=ports,
        dimensions=(
            DimensionCallout("CAGE_X", dx, 0.1, -0.1),
            DimensionCallout("CAGE_Y", dy, 0.1, -0.1),
            DimensionCallout("CAGE_Z", dz, 0.1, -0.1),
        ),
        scad_params=(("n_cards", 8), ("cage_dx", dx), ("cage_dy", dy), ("cage_dz", dz)),
        target_mass_kg=0.78,
    )
    feats = (
        ScadFeature("add_box", {"dx": dx, "dy": dy, "dz": dz}, comment="4 K 8-card cryo-CMOS DC gate mux cage"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=5200.0)


# ---------------------------------------------------------------------------
# S6.8 20 mK Dry Dilution Refrigerator Insert, GHS Cabinet & OVC (3 parts)
# ---------------------------------------------------------------------------
def _build_s6_8_01() -> BuiltPart:
    """S6.8-01: 20 mK dry dilution refrigerator insert tower (50K/4K/Still/CP/MXC plates, Ag-sinter HX & support rods)."""
    # World origin: (-650.0, 0.0, 720.0) (4 K stage bottom face is z_local=0!)
    # Exact stage plate elevations (all non-overlapping with every coax loom & PT420 bore):
    # - 50 K plate (Al 6061): R_in=46.0 (PT420 1st stage bore!), R_out=148.0, z_global=[840, 854]
    # - 4 K plate  (OFHC Cu): R_in=14.0, R_out=130.0, z_global=[720, 736]
    # - Still 0.8K (OFHC Cu): R_in=14.0, R_out=112.0, z_global=[604, 616]
    # - Cold Plate (OFHC Cu): R_in=14.0, R_out=102.0, z_global=[542, 552]
    # - MXC 20 mK  (OFHC Cu): R_in=12.0, R_out=95.0,  z_global=[484, 500]
    # Plus 3x segmented G10/316LN cryogenic stage support rods @ R=88 mm (0, 128, 232 deg)
    # Plus 3x Ag-sinter step heat-exchanger cans @ R=26 mm (0, 120, 240 deg) between Still and MXC!
    z0 = 720.0
    parts: list[SolidMesh] = []
    stage_specs = [
        ("plate_50k", 46.0, 148.0, 14.0, 847.0, 276.0, 16, "Al 6061"),
        ("plate_4k", 14.0, 130.0, 16.0, 728.0, 244.0, 16, "OFHC Cu"),
        ("plate_still", 14.0, 112.0, 12.0, 610.0, 208.0, 12, "OFHC Cu"),
        ("plate_cp", 14.0, 102.0, 10.0, 547.0, 188.0, 12, "OFHC Cu"),
        ("plate_mxc", 12.0, 95.0, 16.0, 492.0, 174.0, 12, "OFHC Cu"),
    ]
    for pname, ri, ro, thk, zg, pcd, nb, mat in stage_specs:
        parts.append(
            make_ring_with_bolt_circle(
                r_in=ri,
                r_out=ro,
                thickness=thk,
                pcd=pcd,
                n_bolts=nb,
                bolt_diameter=4.5,
                sub_per_side=2,
                center=(0.0, 0.0, zg - z0),
                name=pname,
                material=mat,
            )
        )

    # 3x segmented support rods at R=88.0 mm (angles 0, 128, 232 deg — clear of ALL coax looms, braids & HEMTs!)
    rod_spans = (
        ("300k_50k", 854.3, 959.5),
        ("50k_4k", 736.3, 839.7),
        ("4k_still", 616.3, 719.7),
        ("still_cp", 552.3, 603.7),
        ("cp_mxc", 500.3, 541.7),
    )
    for r_idx, ang_deg in enumerate((0.0, 128.0, 232.0), start=1):
        rad = math.radians(ang_deg)
        rx, ry = 88.0 * math.cos(rad), 88.0 * math.sin(rad)
        for s_tag, za, zb in rod_spans:
            parts.append(
                make_cylinder(
                    radius=4.0,
                    height=zb - za,
                    segments=12,
                    center=(rx, ry, 0.5 * (za + zb) - z0),
                    name=f"dr_rod_{r_idx}_{s_tag}",
                    material="316LN",
                )
            )

    # 3x Ag-sinter step heat exchangers (Still -> CP -> MXC) at R=26 mm (0, 120, 240 deg)
    for h_idx, ang_deg in enumerate((0.0, 120.0, 240.0), start=1):
        rad = math.radians(ang_deg)
        hx, hy = 26.0 * math.cos(rad), 26.0 * math.sin(rad)
        # Upper HX can (Still -> CP: z=[552.4, 603.6])
        parts.append(make_cylinder(9.0, 51.2, segments=16, center=(hx, hy, 578.0 - z0), name=f"ag_sinter_hi_{h_idx}", material="OFHC Cu"))
        # Lower HX can (CP -> MXC: z=[500.4, 541.6])
        parts.append(make_cylinder(9.0, 41.2, segments=16, center=(hx, hy, 521.0 - z0), name=f"ag_sinter_lo_{h_idx}", material="OFHC Cu"))

    mesh = merge_solids(parts, name="S6.8-01", material="OFHC Cu")
    ports = (
        PortInterface("mxc_20mk_face", "thermal", (0.0, 0.0, 484.0 - z0), (0.0, 0.0, -1.0), "20 mK Au-OFHC MXC Payload Plate", mating_part_id="S6.11-02", bore_mm=24.0, od_mm=190.0),
        PortInterface("mxc_bridge_east", "thermal", (95.0, 0.0, 492.0 - z0), (1.0, 0.0, 0.0), "20 mK Horizontal Busbar Clamp", mating_part_id="S6.9-03"),
        PortInterface("pt420_50k_bore", "mechanical", (0.0, 0.0, 854.0 - z0), (0.0, 0.0, 1.0), "Ø92 mm PT420 Cold-Head Pass-Through", mating_part_id="S6.1-01", bore_mm=92.0, od_mm=296.0),
        PortInterface("stage_4k_mount", "thermal", (0.0, 0.0, 720.0 - z0), (0.0, 0.0, -1.0), "4 K Au-OFHC Readout Flange", mating_part_id="S6.6-01", bore_mm=28.0, od_mm=260.0),
    )
    design = make_part_design_from_bom(
        "S6.8-01",
        material="OFHC Cu",
        world_origin_mm=(DR_X_MM, DR_Y_MM, z0),
        ports=ports,
        dimensions=(
            DimensionCallout("PLATE_50K_OD", 296.0, 0.15, -0.15, prefix="Ø"),
            DimensionCallout("PLATE_4K_OD", 260.0, 0.15, -0.15, prefix="Ø"),
            DimensionCallout("PLATE_MXC_OD", 190.0, 0.10, -0.10, prefix="Ø"),
            DimensionCallout("TOWER_H", 475.5, 0.50, -0.50),
        ),
        gdt_frames=(
            GDTFrame("parallelism", 0.05, datum_primary="A", feature_note="50K/4K/Still/CP/MXC plates"),
            GDTFrame("concentricity", 0.10, diameter_zone=True, datum_primary="B", feature_note="Stage stack axis"),
        ),
        scad_params=(("t_mxc_mk", 20.0), ("p_cool_100mk_uw", 400.0), ("n_stages", 5), ("n_ag_hx", 3)),
        target_mass_kg=34.0,
    )
    feats = (
        ScadFeature("add_tube", {"od": 296.0, "id": 92.0, "h": 14.0}, translate=(0.0, 0.0, 127.0), comment="50 K Al-6061 plate"),
        ScadFeature("add_tube", {"od": 260.0, "id": 28.0, "h": 16.0}, translate=(0.0, 0.0, 8.0), comment="4 K OFHC plate"),
        ScadFeature("add_tube", {"od": 224.0, "id": 28.0, "h": 12.0}, translate=(0.0, 0.0, -110.0), comment="Still 0.8 K plate"),
        ScadFeature("add_tube", {"od": 204.0, "id": 28.0, "h": 10.0}, translate=(0.0, 0.0, -173.0), comment="Cold Plate 100 mK"),
        ScadFeature("add_tube", {"od": 190.0, "id": 24.0, "h": 16.0}, translate=(0.0, 0.0, -228.0), comment="MXC 20 mK plate"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_8_02() -> BuiltPart:
    """S6.8-02: Closed-loop 3He/4He Gas Handling System (GHS) cabinet (floor mounted at X=-1300, Y=-800 mm)."""
    # World origin: (-1300.0, -800.0, 825.0) -> x=[-1600,-1000], y=[-1080,-520], z=[0, 1650]
    dx, dy, dz = 600.0, 560.0, 1650.0
    wall = 3.0
    parts: list[SolidMesh] = []
    # Hollow welded 316L/steel instrument cabinet frame (clean non-overlapping seams to base & roof)
    parts.append(make_hollow_frame(dx, dy, dx - 2 * wall, dy - 2 * wall, dz - 43.0, center=(0.0, 0.0, 11.0), name="ghs_cabinet_shell", material="Steel"))
    parts.append(make_box(dx, dy, 10.0, center=(0.0, 0.0, 0.5 * dz - 5.0), name="ghs_top_roof", material="Steel"))
    parts.append(make_box(dx, dy, 12.0, center=(0.0, 0.0, -0.5 * dz + 26.0), name="ghs_base_deck", material="Steel"))
    for sx in (-250.0, 250.0):
        for sy in (-230.0, 230.0):
            parts.append(make_cylinder(24.0, 19.5, segments=16, center=(sx, sy, -0.5 * dz + 9.75), name="ghs_foot", material="Steel"))
    # Internal 3He/4He stainless dump tank (left bay) + dry scroll/turbo circulation stack (right bay) + LN2 cold trap
    parts.append(make_cylinder(135.0, 520.0, segments=24, center=(-135.0, 0.0, -480.0), name="ghs_he3_dump_tank", material="316L"))
    parts.append(make_cylinder(100.0, 320.0, segments=20, center=(140.0, 0.0, -560.0), name="ghs_scroll_pump", material="Al 6061"))
    parts.append(make_cylinder(75.0, 420.0, segments=20, center=(140.0, 0.0, 120.0), name="ghs_cold_trap", material="316L"))
    # Top ISO-K DN50 3He circulation return + backing manifold ports
    parts.append(make_isok_flange("DN50", center=(-120.0, 0.0, 0.5 * dz + 6.2), name="ghs_still_pump_dn50", material="316L"))
    parts.append(make_isok_flange("DN50", center=(120.0, 0.0, 0.5 * dz + 6.2), name="ghs_condense_dn50", material="316L"))

    mesh = merge_solids(parts, name="S6.8-02", material="316L")
    ports = (
        make_cf_port_interface("DN50", "still_pumping_line", (-120.0, 0.0, 0.5 * dz + 12.2), (0.0, 0.0, 1.0), mating_part_id="S6.8-04"),
        make_cf_port_interface("DN50", "condensing_return_line", (120.0, 0.0, 0.5 * dz + 12.2), (0.0, 0.0, 1.0), mating_part_id="S6.8-04"),
    )
    design = make_part_design_from_bom(
        "S6.8-02",
        material="316L",
        world_origin_mm=(-1300.0, -800.0, 825.0),
        ports=ports,
        dimensions=(
            DimensionCallout("CAB_W", dx, 2.0, -2.0),
            DimensionCallout("CAB_D", dy, 2.0, -2.0),
            DimensionCallout("CAB_H", dz + 12.2, 2.0, -2.0),
        ),
        scad_params=(("ghs_w", dx), ("ghs_d", dy), ("ghs_h", dz), ("he3_stp_l", 20.0)),
        target_mass_kg=240.0,
    )
    feats = (
        ScadFeature("add_box", {"dx": dx, "dy": dy, "dz": dz}, comment="Closed-loop 3He/4He GHS cabinet"),
        ScadFeature("add_cylinder", {"d": 75.0, "h": 12.0}, translate=(-120.0, 0.0, 0.5 * dz + 6.2), comment="ISO-K DN50 still pump port"),
        ScadFeature("add_cylinder", {"d": 75.0, "h": 12.0}, translate=(120.0, 0.0, 0.5 * dz + 6.2), comment="ISO-K DN50 condense return port"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=2600.0)


def _build_s6_8_04() -> BuiltPart:
    """S6.8-04: DR Outer Vacuum Chamber (OVC), ISO-K flanges, ASME DN50 rupture-disk nozzle boss & support frame."""
    # World origin: (-650.0, 0.0, 500.0)
    # - Welded steel support frame: 340x340 outer, 260x260 inner, z_global=[0, 159.5]
    # - Bottom OVC blind plate + ISO-K DN250 pump flange: z_global=[160.0, 175.0], R=178.0
    # - Lower OVC 316LN shell: R_in=167, R_out=175, z_global=[175.5, 454.5]
    # - Bridge port arc (+X open): z_global=[455.0, 535.0], deg0=24, deg1=336
    # - Mid OVC shell: z_global=[535.5, 639.5]
    # - Option-Q -X port arc (-X open for S9.4-01 CF63!): z_global=[640.0, 740.0], deg0=-158, deg1=+158
    # - Upper OVC shell: z_global=[740.5, 959.5]
    # - +Y ASME DN50 ISO-K rupture-disk nozzle stub at (-650, +186, 820) leaving clean wall clearance for S7.SAFETY-05!
    # - Top 300 K main vacuum flange: R_in=46.0 (PT420 pass-through!), R_out=195.0, z_global=[960.0, 985.0], 24x M8 bolts @ PCD 368
    z0 = 500.0
    parts: list[SolidMesh] = []
    # Vibration-isolated DR support frame (floor z=0..159.5, 296x296 inner opening cleanly clears Ø290 ISO-K DN250!)
    parts.append(make_hollow_frame(340.0, 340.0, 296.0, 296.0, 159.0, center=(0.0, 0.0, 79.5 - z0), name="dr_support_frame", material="Steel"))
    # OVC bottom cap + ISO-K DN250 flange profile
    parts.append(make_cylinder(178.0, 15.0, segments=48, center=(0.0, 0.0, 167.5 - z0), name="dr_ovc_bottom", material="316LN"))
    parts.append(make_isok_flange("DN250", blank=True, center=(0.0, 0.0, 153.0 - z0), name="dr_ovc_isok_dn250_bot", material="316LN"))
    # Lower, bridge-port, mid, Option-Q-port, and upper OVC walls (R=167..175 mm)
    parts.append(make_tube(167.0, 175.0, 279.0, segments=48, center=(0.0, 0.0, 315.0 - z0), name="dr_ovc_lower", material="316LN"))
    parts.append(make_arc_tube(167.0, 175.0, 79.5, 24.0, 336.0, center=(0.0, 0.0, 495.0 - z0), name="dr_ovc_bridge_arc", material="316LN"))
    parts.append(make_tube(167.0, 175.0, 104.0, segments=48, center=(0.0, 0.0, 587.5 - z0), name="dr_ovc_mid", material="316LN"))
    parts.append(make_arc_tube(167.0, 175.0, 99.5, -158.0, 158.0, center=(0.0, 0.0, 690.0 - z0), name="dr_ovc_optq_arc", material="316LN"))
    parts.append(make_tube(167.0, 175.0, 219.0, segments=48, center=(0.0, 0.0, 850.0 - z0), name="dr_ovc_upper", material="316LN"))
    # Top 300 K main vacuum flange with 24x M8 bolt circle & central Ø92 mm PT420 bore
    parts.append(
        make_ring_with_bolt_circle(
            r_in=46.0,
            r_out=195.0,
            thickness=25.0,
            pcd=368.0,
            n_bolts=24,
            bolt_diameter=8.4,
            sub_per_side=2,
            center=(0.0, 0.0, 972.5 - z0),
            name="dr_ovc_top_flange",
            material="316LN",
        )
    )
    # Dedicated +Y ASME DN50 ISO-K rupture-disk relief nozzle stub for S7.SAFETY-05 (0.5 barg)
    parts.append(
        make_isok_flange(
            "DN50",
            bore_id=50.0,
            neck_length=11.0,
            segments=32,
            axis="y",
            center=(0.0, 192.0, 820.0 - z0),
            name="ovc_asme_dn50_relief_nozzle",
            material="316LN",
        )
    )

    mesh = merge_solids(parts, name="S6.8-04", material="316LN")
    ports = (
        make_cf_port_interface("DN50", "asme_rupture_disk_port", (0.0, 198.0, 320.0), (0.0, 1.0, 0.0), mating_part_id="S7.SAFETY-05", notes="ASME Sec VIII Div 1 DN50 0.5 barg rupture-disk clearance"),
        make_cf_port_interface("CF63", "bridge_bellows_east", (175.0, 0.0, Z_CRYO_BRIDGE_MM - z0), (1.0, 0.0, 0.0), mating_part_id="S6.9-02", bore_override_mm=44.0),
        make_cf_port_interface("CF63", "option_q_west", (-175.0, 0.0, 190.0), (-1.0, 0.0, 0.0), mating_part_id="S9.4-01"),
        make_cf_port_interface("DN160", "pt420_top_port", (0.0, 0.0, 485.0), (0.0, 0.0, 1.0), mating_part_id="S6.1-01", bore_override_mm=92.0),
    )
    design = make_part_design_from_bom(
        "S6.8-04",
        material="316LN",
        world_origin_mm=(DR_X_MM, DR_Y_MM, z0),
        ports=ports,
        dimensions=(
            DimensionCallout("OVC_OD", 350.0, 0.25, -0.25, prefix="Ø"),
            DimensionCallout("OVC_ID", 334.0, 0.25, -0.25, prefix="Ø"),
            DimensionCallout("TOP_FLANGE_OD", 390.0, 0.20, -0.20, prefix="Ø"),
            DimensionCallout("TOTAL_H", 985.0, 0.50, -0.50),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.10, diameter_zone=True, datum_primary="A", feature_note="OVC cylinder axis"),
            GDTFrame("flatness", 0.05, datum_primary="A", feature_note="Top 300 K O-ring flange face"),
        ),
        notes=("Includes dedicated +Y ASME DN50 ISO-K relief nozzle at (-650, +198, 820) mm leaving clean clearance for S7.SAFETY-05 rupture disk.",),
        scad_params=(("ovc_id", 334.0), ("ovc_od", 350.0), ("top_flange_od", 390.0), ("relief_dn", 50)),
        target_mass_kg=112.0,
    )
    feats = (
        ScadFeature("add_box", {"dx": 340.0, "dy": 340.0, "dz": 159.0}, translate=(0.0, 0.0, -420.5), comment="DR vibration-isolated support frame"),
        ScadFeature("add_tube", {"od": 350.0, "id": 334.0, "h": 785.0}, translate=(0.0, 0.0, 67.5), comment="316LN DR OVC vessel"),
        ScadFeature("add_tube", {"od": 390.0, "id": 92.0, "h": 25.0}, translate=(0.0, 0.0, 472.5), comment="Top 300 K main flange"),
        ScadFeature("cut_bolt_circle", {"pcd": 368.0, "bolt_d": 8.4, "count": 24, "h": 28.0}, translate=(0.0, 0.0, 472.5), comment="24x M8 top flange bolts"),
        ScadFeature("add_cylinder", {"d": 75.0, "h": 24.0}, translate=(0.0, 186.0, 320.0), rotate=(-90.0, 0.0, 0.0), comment="ASME DN50 ISO-K rupture-disk nozzle for S7.SAFETY-05"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


# ---------------------------------------------------------------------------
# S6.10 M4 Cavity-QED Bus, 4 K SKY130 968-Gate Crossbar & DC Gate Filter (3 parts)
# ---------------------------------------------------------------------------
def _build_s6_10_01() -> BuiltPart:
    """S6.10-01: High-impedance 3 kOhm NbTiN M4 cavity-QED bus chip package & Eccosorb coax clamps (20 mK)."""
    # World origin: (-650.0, +58.0, 408.0) -> x=[-676,-624], y=[+40,+76], z=[399, 417]
    # Clears S9.4-02 (y<=+15) by 25 mm, S6.11-02 TWPA (z>=424.5) by 7.5 mm, S6.6-02 (z<=384) by 15 mm!
    dx, dy, dz = 52.0, 36.0, 18.0
    parts: list[SolidMesh] = []
    # Gold-plated OFHC/Nb shielded chip cavity housing with 4x M2.5 mounting holes
    parts.append(
        make_rect_plate_with_features(
            dx, dy, 4.5,
            circular_holes=((-21.0, -13.0, 2.7), (21.0, -13.0, 2.7), (21.0, 13.0, 2.7), (-21.0, 13.0, 2.7)),
            hole_segments=10,
            center=(0.0, 0.0, -6.75),
            name="m4_bus_base",
            material="OFHC Cu",
        )
    )
    parts.append(make_hollow_frame(dx, dy, 32.0, 20.0, 9.0, center=(0.0, 0.0, 0.1), name="m4_bus_wall", material="Nb"))
    parts.append(make_box(dx, dy, 4.2, center=(0.0, 0.0, 6.8), name="m4_bus_lid", material="Nb"))
    # High-R 28Si / 3 kOhm NbTiN cavity-QED bus die inside pocket
    parts.append(make_box(24.0, 14.0, 1.0, center=(0.0, 0.0, -3.5), name="m4_3kohm_nbtin_die", material="Si"))
    # 4x Eccosorb-filtered cryo coax launch clamps on +-X faces
    for sgn in (-1.0, 1.0):
        for cy in (-7.0, 7.0):
            parts.append(make_cylinder(2.6, 5.0, segments=12, axis="x", center=(sgn * (0.5 * dx + 2.6), cy, 0.0), name="m4_coax_clamp", material="BeCu"))

    mesh = merge_solids(parts, name="S6.10-01", material="OFHC Cu")
    ports = (
        PortInterface("m4_rf_east", "rf", (0.5 * dx + 5.1, 0.0, 0.0), (1.0, 0.0, 0.0), "2x Cryo SMP 5 GHz + Eccosorb Clamp", mating_part_id="S6.11-02"),
        PortInterface("m4_rf_west", "rf", (-0.5 * dx - 5.1, 0.0, 0.0), (-1.0, 0.0, 0.0), "2x Cryo SMP 3 kOhm Bus Launch", mating_part_id="S9.4-02"),
    )
    design = make_part_design_from_bom(
        "S6.10-01",
        material="OFHC Cu",
        world_origin_mm=(DR_X_MM, 58.0, 408.0),
        ports=ports,
        dimensions=(
            DimensionCallout("PKG_X", dx, 0.05, -0.05),
            DimensionCallout("PKG_Y", dy, 0.05, -0.05),
            DimensionCallout("PKG_Z", dz, 0.05, -0.05),
        ),
        gdt_frames=(GDTFrame("flatness", 0.005, datum_primary="A", feature_note="28Si M4 bus seating face"),),
        scad_params=(("z_bus_ohm", 3000.0), ("f_res_ghz", 5.0), ("l_res_um", 300.0), ("b_m4_t", 0.1785)),
        target_mass_kg=0.21,
    )
    feats = (
        ScadFeature("add_box", {"dx": dx, "dy": dy, "dz": dz}, comment="20 mK 3 kOhm NbTiN M4 cavity-QED bus package"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s6_10_03() -> BuiltPart:
    """S6.10-03: 4 K SKY130 968-gate crossbar multiplexer carrier & M4 DC gate module (Exp131, fixing old S6.6 alias!)."""
    # World origin: (-650.0, 0.0, 703.0) -> z_global = [690.0, 716.0], 76 x 58 x 26 mm
    # Clears 4 K plate (z=720) by 4 mm, S6.7-02 (z<=680) by 10 mm, S6.6-01 HEMT ring (R>=98) by 50 mm!
    dx, dy, dz = 76.0, 58.0, 26.0
    parts: list[SolidMesh] = []
    # Top gold-plated OFHC Cu thermal spreader carrier plate (6 mm thick, 4x M3 mounting bolts)
    parts.append(
        make_rect_plate_with_features(
            dx, dy, 6.0,
            circular_holes=((-32.0, -23.0, 3.2), (32.0, -23.0, 3.2), (32.0, 23.0, 3.2), (-32.0, 23.0, 3.2)),
            hole_segments=10,
            center=(0.0, 0.0, 10.0),
            name="m4_crossbar_ofhc_carrier",
            material="OFHC Cu",
        )
    )
    # Dual-set 4-layer Rogers/AlN cryo-CMOS 968-gate crossbar PCBs + SKY130 ASIC die pockets (2 sets per BOM!)
    for idx, zc in enumerate((2.0, -7.5), start=1):
        parts.append(make_box(72.0, 54.0, 2.4, center=(0.0, 0.0, zc), name=f"sky130_crossbar_pcb_{idx}", material="Rogers"))
        parts.append(make_box(24.0, 24.0, 2.8, center=(0.0, 0.0, zc - 2.8), name=f"sky130_968gate_asic_{idx}", material="Si"))
        # Side Micro-D cryo-loom connectors
        for sgn in (-1.0, 1.0):
            parts.append(make_box(6.0, 36.0, 4.5, center=(sgn * 31.0, 0.0, zc - 3.6), name=f"crossbar_microd_{idx}_{int(sgn>0)}", material="Al 6061"))

    mesh = merge_solids(parts, name="S6.10-03", material="OFHC Cu")
    ports = (
        PortInterface("thermal_4k_top", "thermal", (0.0, 0.0, 13.0), (0.0, 0.0, 1.0), "4x M3 Au-OFHC 4K Clamp (<=15.4 mW)", mating_part_id="S6.8-01", bolt_count=4, bolt_hole_mm=3.2, bolt_spec="M3"),
        PortInterface("gates_968_microd", "connector", (34.0, 0.0, -2.0), (1.0, 0.0, 0.0), "4x 51-pin Micro-D 968-Gate Mux", mating_part_id="S6.7-02"),
    )
    design = make_part_design_from_bom(
        "S6.10-03",
        material="OFHC Cu",
        world_origin_mm=(DR_X_MM, DR_Y_MM, 703.0),
        ports=ports,
        dimensions=(
            DimensionCallout("CARRIER_X", dx, 0.05, -0.05),
            DimensionCallout("CARRIER_Y", dy, 0.05, -0.05),
            DimensionCallout("STACK_Z", dz, 0.10, -0.10),
        ),
        gdt_frames=(GDTFrame("flatness", 0.015, datum_primary="A", feature_note="4 K OFHC thermal interface"),),
        notes=("Exact BOM part_id S6.10-03 (resolves legacy cad/params.py S6.6 aliasing bug). Dual-set SKY130 968-gate 4 K crossbar (15.4 mW).",),
        scad_params=(("n_gates", 968), ("p_4k_mw", 15.4), ("qty_sets", 2), ("carrier_dx", dx), ("carrier_dy", dy)),
        target_mass_kg=0.42,
    )
    feats = (
        ScadFeature("add_box", {"dx": dx, "dy": dy, "dz": 6.0}, translate=(0.0, 0.0, 10.0), comment="4 K OFHC thermal carrier"),
        ScadFeature("add_box", {"dx": 72.0, "dy": 54.0, "dz": 16.0}, translate=(0.0, 0.0, -2.0), comment="Dual SKY130 968-gate crossbar PCB stack"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=4800.0)


def _build_s6_10_04() -> BuiltPart:
    """S6.10-04: M4 low-noise 20-bit DC dipole gate DAC & RC/Eccosorb filter rack enclosure (2U, Bay 2 U7..U8)."""
    zc, dz = rack_u_center_and_height(7, 2)
    mesh, feats = make_rack_chassis_19in(440.0, dz, n_subunits=1, n_front_ports=12, material="Al 6061", name="S6.10-04")
    ports = (
        PortInterface("dc_dac_20bit_out", "connector", (0.0, 220.0, 0.0), (0.0, 1.0, 0.0), "4x DB25 Filtered <0.5 uV/sqrt(Hz)", mating_part_id="S6.10-03"),
        PortInterface("rack_bay2_u7_u8", "mechanical", (0.0, -220.0, 0.0), (0.0, -1.0, 0.0), '19" EIA-310 2U (U7-U8)', mating_part_id="S7.4-03"),
    )
    design = make_part_design_from_bom(
        "S6.10-04",
        material="Al 6061",
        world_origin_mm=(RACK_BAY2_X_MM, RACK_BAY2_Y_MM, zc),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.5, -0.5),
            DimensionCallout("DEPTH", 440.0, 1.0, -1.0),
            DimensionCallout("HEIGHT_2U", dz, 0.3, -0.3),
        ),
        scad_params=(("rack_u", 2), ("u_start", 7), ("dac_bits", 20), ("noise_uv_rthz", 0.5)),
        target_mass_kg=9.4,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


# ---------------------------------------------------------------------------
# S6.11 Exp140 1,024-Cell Cryo-MUX & ZU48DR RFSoC (4 parts, fixing old S6.5 alias!)
# ---------------------------------------------------------------------------
def _build_s6_11_01() -> BuiltPart:
    """S6.11-01: 2U 19-in ZU48DR RFSoC Q16.16 BOED-FPGA chassis (482.6x520x88.9 mm, 11.50 kg, Bay 2 U22..U23)."""
    # Exact BOM dims: 482.6 x 520.0 x 88.9 mm, 11.50 kg!
    # U21 top = 90 + 21*44.45 - 1.0 = 1022.45; U24 starts at 1112.35; place centered at z=1069.0 -> [1024.55, 1113.45]
    # Note U25 starts at 90 + 24*44.45 + 1.0 = 1157.80 -> 44.35 mm baffle clearance above U23!
    zc = 1069.0
    dz = 88.9
    base_mesh, feats = make_rack_chassis_19in(520.0, dz, n_subunits=1, n_front_ports=14, wall_mm=2.4, material="Al 6061", name="S6.11-01_body")
    # Add internal 2x ZU48DR RFSoC Cu-heatsink blocks & redundant PSU brick inside upper hollow bay
    internals = [
        base_mesh,
        make_box(160.0, 180.0, 26.0, center=(-105.0, -60.0, 14.0), name="zu48dr_card1_heatsink", material="OFHC Cu"),
        make_box(160.0, 180.0, 26.0, center=(105.0, -60.0, 14.0), name="zu48dr_card2_heatsink", material="OFHC Cu"),
        make_box(220.0, 160.0, 32.0, center=(0.0, 140.0, 14.0), name="zu48dr_redundant_psu", material="Steel"),
    ]
    mesh = merge_solids(internals, name="S6.11-01", material="Al 6061")
    ports = (
        PortInterface("direct_rf_32ch", "rf", (0.0, -267.0, 0.0), (0.0, -1.0, 0.0), "32x Direct-RF SMA (2x ZU48DR)", mating_part_id="S6.11-04"),
        PortInterface("qsfp28_100g_rdma", "optical", (0.0, 260.0, 0.0), (0.0, 1.0, 0.0), "4x QSFP28 100GbE to S9.HPC", mating_part_id="S9.HPC-02"),
        PortInterface("rack_bay2_u22_u23", "mechanical", (0.0, -260.0, 0.0), (0.0, -1.0, 0.0), '19" EIA-310 2U (U22-U23)', mating_part_id="S7.4-03"),
    )
    design = make_part_design_from_bom(
        "S6.11-01",
        material="Al 6061",
        world_origin_mm=(RACK_BAY2_X_MM, RACK_BAY2_Y_MM, zc),
        ports=ports,
        dimensions=(
            DimensionCallout("WIDTH_19IN", 482.6, 0.3, -0.3),
            DimensionCallout("DEPTH", 520.0, 0.5, -0.5),
            DimensionCallout("HEIGHT_2U", 88.9, 0.2, -0.2),
        ),
        notes=("Exact BOM part_id S6.11-01 (resolves legacy cad/params.py S6.5 aliasing bug). 2x ZU48DR BOED-FPGA RFSoC, 87.96 W, 11.50 kg (Exp140).",),
        scad_params=(("rack_u", 2), ("u_start", 22), ("rf_chains", 32), ("power_w", 87.96), ("mass_kg", 11.5)),
        target_mass_kg=11.50,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=2300.0)


def _build_s6_11_02() -> BuiltPart:
    """S6.11-02: 32x 20 mK Josephson TWPA + bandpass Purcell + dual cryo-isolator magnetic shield box (180x140x55 mm, 2.72 kg)."""
    # World origin: (-650.0, 0.0, 452.0) -> z_global = [424.5, 479.5] (4.5 mm below MXC plate z=484.0!)
    # Exact BOM envelope 180 x 140 x 55 mm with 10 mm corner chamfers so max corner R = 107.0 mm << 116.0 mm Still shield ID!
    dx, dy, dz = 180.0, 140.0, 55.0
    parts: list[SolidMesh] = []
    # Chamfered outer Nb/Cryoperm magnetic shield enclosure (180x140x55 mm)
    outer_box = make_chamfered_box(dx, dy, dz - 8.0, chamfer=10.0, center=(0.0, 0.0, 0.0), name="twpa_shield_shell", material="Nb")
    parts.append(outer_box)
    # Bolted top OFHC Cu thermalization cover plate (164x124x3.8 mm, 4x M3 MXC mount holes)
    parts.append(
        make_rect_plate_with_features(
            dx - 16.0, dy - 16.0, 3.8,
            circular_holes=((-72.0, -52.0, 3.4), (72.0, -52.0, 3.4), (72.0, 52.0, 3.4), (-72.0, 52.0, 3.4)),
            hole_segments=12,
            center=(0.0, 0.0, 0.5 * dz - 2.0),
            name="twpa_top_mxc_plate",
            material="OFHC Cu",
        )
    )
    # Bottom Cryoperm-10 base closure plate (164x124x3.8 mm)
    parts.append(make_box(dx - 16.0, dy - 16.0, 3.8, center=(0.0, 0.0, -0.5 * dz + 2.0), name="twpa_bot_shield", material="Cryoperm"))

    mesh = merge_solids(parts, name="S6.11-02", material="Nb")
    ports = (
        PortInterface("mxc_20mk_mount", "thermal", (0.0, 0.0, 27.5), (0.0, 0.0, 1.0), "4x M3 Au-OFHC MXC Mount (2.144 uW)", mating_part_id="S6.8-01", bolt_count=4, bolt_hole_mm=3.4, bolt_spec="M3"),
        PortInterface("twpa_32ch_smp", "rf", (-90.0, 0.0, 0.0), (-1.0, 0.0, 0.0), "32x TWPA + 625x Purcell SMP", mating_part_id="S6.11-04"),
    )
    design = make_part_design_from_bom(
        "S6.11-02",
        material="Nb",
        world_origin_mm=(DR_X_MM, DR_Y_MM, 452.0),
        ports=ports,
        dimensions=(
            DimensionCallout("BOX_X", dx, 0.10, -0.10),
            DimensionCallout("BOX_Y", dy, 0.10, -0.10),
            DimensionCallout("BOX_Z", dz, 0.10, -0.10),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.015, datum_primary="A", feature_note="20 mK MXC thermal contact face"),
            GDTFrame("parallelism", 0.030, datum_primary="A", feature_note="Bottom clearance face to S9.4-02"),
        ),
        notes=("Exact BOM part_id S6.11-02 (resolves legacy cad/params.py S6.5 aliasing bug). 32x 20 mK Josephson TWPA + Purcell + dual isolators, 10 mm corner chamfers clear Still shield R_in=116 mm by 9.0 mm (Exp140).",),
        scad_params=(("n_twpa", 32), ("box_dx", dx), ("box_dy", dy), ("box_dz", dz), ("p_20mk_uw", 2.144)),
        target_mass_kg=2.72,
    )
    feats = (
        ScadFeature("add_box", {"dx": dx, "dy": dy, "dz": dz}, comment="32x 20 mK TWPA + Purcell Nb/Cryoperm magnetic shield box"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=2150.0)


def _build_s6_11_03() -> BuiltPart:
    """S6.11-03: 32x 4 K ultra-low-noise InP HEMT bank (LNF-LNC4_8C class, Exp140, 1.02 kg)."""
    # World origin: (-650.0, 0.0, 654.0) -> z_global = [634.0, 674.0] (8 mm below S6.6-01, 18 mm above Still plate!)
    # Annular 32-bay ring R_in = 98.0, R_out = 126.0 (clears S6.7-02 central cage R<=48 and 4K shield R_in=132!)
    parts: list[SolidMesh] = []
    ring = make_ring_with_bolt_circle(
        r_in=98.0,
        r_out=126.0,
        thickness=5.5,
        pcd=224.0,
        n_bolts=12,
        bolt_diameter=3.2,
        sub_per_side=2,
        center=(0.0, 0.0, 17.0),
        name="hemt32_ring",
        material="OFHC Cu",
    )
    parts.append(ring)
    for k in range(32):
        ang = 360.0 * k / 32.0
        rad = math.radians(ang)
        cx, cy = 112.0 * math.cos(rad), 112.0 * math.sin(rad)
        mod = make_box(12.0, 8.0, 32.0, name=f"lnf_hemt32_{k}", material="Al 6061")
        parts.append(transform_mesh(mod, rotation_deg=(0.0, 0.0, ang), translation=(cx, cy, -2.5)))

    mesh = merge_solids(parts, name="S6.11-03", material="OFHC Cu")
    ports = (
        PortInterface("hemt32_4k_thermal", "thermal", (0.0, 0.0, 19.75), (0.0, 0.0, 1.0), "12x M3 Au-OFHC 4K Mount (0.250 W)", mating_part_id="S6.8-01", bore_mm=196.0, od_mm=252.0, pcd_mm=224.0, bolt_count=12, bolt_hole_mm=3.2, bolt_spec="M3"),
        PortInterface("hemt32_sma", "rf", (0.0, 0.0, -18.5), (0.0, 0.0, -1.0), "32x LNF-LNC4_8C 4-8 GHz SMA", mating_part_id="S6.11-04"),
    )
    design = make_part_design_from_bom(
        "S6.11-03",
        material="OFHC Cu",
        world_origin_mm=(DR_X_MM, DR_Y_MM, 654.0),
        ports=ports,
        dimensions=(
            DimensionCallout("RING_OD", 252.0, 0.1, -0.1, prefix="Ø"),
            DimensionCallout("RING_ID", 196.0, 0.1, -0.1, prefix="Ø"),
            DimensionCallout("ASSY_H", 40.0, 0.1, -0.1),
        ),
        notes=("Exact BOM part_id S6.11-03 (resolves legacy cad/params.py S6.5 aliasing bug). 32x 4 K InP HEMT bank, 7.8 mW/ch = 0.2496 W @ 4 K, 1.02 kg (Exp140).",),
        scad_params=(("n_hemt", 32), ("p_4k_w", 0.2496), ("tn_k", 2.0), ("mass_kg", 1.02)),
        target_mass_kg=1.02,
    )
    feats = (
        ScadFeature("add_tube", {"od": 252.0, "id": 196.0, "h": 40.0}, comment="32x 4 K LNF-LNC4_8C HEMT ring"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats, density_kg_m3=3600.0)


def _build_s6_11_04() -> BuiltPart:
    """S6.11-04: 96-line CuNi/NbTi 0.86 mm cryo-coax loom & stepped attenuators/Eccosorb filters (Exp140, 4.03 kg)."""
    # World origin: (-716.0, 0.0, 730.0) — two parallel 48-line looms at y_local = +-24.0 mm!
    # Cleanly segmented across all 5 DR stages (top segment starts at z=872.0, clearing S6.1-03 50K braids z<=868.5!):
    z_orig = 730.0
    spans = (
        ("300k_50k", 872.0, 958.0),
        ("50k_4k", 752.0, 836.0),
        ("4k_still", 618.0, 718.0),
        ("still_cp", 554.0, 602.0),
        ("cp_mxc", 502.0, 540.0),
    )
    parts: list[SolidMesh] = []
    feats: list[ScadFeature] = []
    for sgn, btag in ((-1.0, "south48"), (1.0, "north48")):
        sub_mesh, _ = make_staged_coax_loom(12, 20.0, 20.0, spans, z_orig, attenuator_r=3.8, material="CuNi", name=f"S6.11-04_{btag}")
        parts.append(transform_mesh(sub_mesh, translation=(0.0, sgn * 24.0, 0.0)))
        feats.append(
            ScadFeature("add_box", {"dx": 20.0, "dy": 20.0, "dz": 456.0}, translate=(0.0, sgn * 24.0, 0.0), comment=f"48-line CuNi/NbTi cryo coax & Eccosorb bundle ({btag})")
        )

    mesh = merge_solids(parts, name="S6.11-04", material="CuNi")
    ports = (
        PortInterface("coax96_top_300k", "rf", (0.0, 0.0, 958.0 - z_orig), (0.0, 0.0, 1.0), "96x Hermetic SMP/SMA 300 K Bulkhead", mating_part_id="S6.11-01"),
        PortInterface("coax96_bot_mxc", "rf", (0.0, 0.0, 502.0 - z_orig), (0.0, 0.0, -1.0), "96x Thermalized + Eccosorb MXC Loom", mating_part_id="S6.11-02"),
    )
    design = make_part_design_from_bom(
        "S6.11-04",
        material="CuNi",
        world_origin_mm=(DR_X_MM - 66.0, 0.0, z_orig),
        ports=ports,
        dimensions=(
            DimensionCallout("BUNDLE_X", 20.0, 0.2, -0.2),
            DimensionCallout("BUNDLE_Y", 68.0, 0.2, -0.2),
            DimensionCallout("SPAN_Z", 456.0, 0.5, -0.5),
        ),
        notes=("Exact BOM part_id S6.11-04 (resolves legacy cad/params.py S6.5 aliasing bug). 96-line (32 RO in + 32 RO out + 32 XY) CuNi/NbTi cryo-coax + stepped attenuators & Eccosorb LPF, 4.03 kg (Exp140).",),
        scad_params=(("n_lines", 96), ("coax_od_mm", 0.86), ("mass_kg", 4.03)),
        target_mass_kg=4.03,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats))


# ---------------------------------------------------------------------------
# S9.4 Option-Q Cryo-qRAM & 1550 nm Optical Bridge (3 parts, fixing old S9.1 alias!)
# ---------------------------------------------------------------------------
def _build_s9_4_01() -> BuiltPart:
    """S9.4-01: Option-Q OVC -X CF63 4xSMA (4-8 GHz) + 1550 nm SMF-28 vacuum feedthrough (100x120x120 mm, 3.20 kg)."""
    # World origin: (-876.0, 0.0, 690.0) -> x_global = [-926.0, -826.0], clearing DR OVC -X wall (-825.0) by 1.0 mm!
    parts: list[SolidMesh] = []
    # True ISO 3669 CF63 flange facing +X toward DR OVC -X port (x_local = [+32.5, +50.0], OD=113.5, 8x M8 bolts)
    fl = make_cf_flange("CF63", bore_id=50.0, with_knife_edge=True, sub_per_side=2, axis="+x", center=(41.25, 0.0, 0.0), name="optq_cf63_flange", material="316LN")
    parts.append(fl)
    # 316LN cylindrical vacuum spool body (x_local = [-30.0, +32.3], R_in=25, R_out=38)
    parts.append(make_tube(25.0, 38.0, 62.3, segments=36, axis="x", center=(1.15, 0.0, 0.0), name="optq_spool", material="316LN"))
    # Rear hermetic bulkhead plate (x_local = [-38.0, -30.1], 120x120 mm EMI housing face with 4x SMA + 1x fiber cutouts)
    bulk = make_rect_plate_with_features(
        120.0, 120.0, 7.9,
        circular_holes=((-26.0, -26.0, 8.0), (26.0, -26.0, 8.0), (26.0, 26.0, 8.0), (-26.0, 26.0, 8.0), (0.0, 0.0, 10.0)),
        hole_segments=12,
        axis="x",
        center=(-34.05, 0.0, 0.0),
        name="optq_bulkhead_plate",
        material="316LN",
    )
    parts.append(bulk)
    # 4x hermetic 4-8 GHz SMA RF feedthrough barrels + 1x central 1550 nm SMF-28 FC/APC optical feedthrough collar
    for idx, (cy, cz) in enumerate(((-26.0, -26.0), (26.0, -26.0), (26.0, 26.0), (-26.0, 26.0)), start=1):
        parts.append(make_cylinder(3.8, 12.0, segments=16, axis="x", center=(-44.0, cy, cz), name=f"optq_sma_{idx}", material="BeCu"))
    parts.append(make_cylinder(4.8, 12.0, segments=16, axis="x", center=(-44.0, 0.0, 0.0), name="optq_smf28_fiber_port", material="316LN"))

    mesh = merge_solids(parts, name="S9.4-01", material="316LN")
    ports = (
        make_cf_port_interface("CF63", "ovc_west_cf63", (50.0, 0.0, 0.0), (1.0, 0.0, 0.0), mating_part_id="S6.8-04", bore_override_mm=50.0),
        PortInterface("sma_4port_4_8ghz", "rf", (-50.0, 0.0, 0.0), (-1.0, 0.0, 0.0), "4x Hermetic SMA 4-8 GHz", mating_part_id="S9.4-03"),
        PortInterface("fiber_1550nm_smf28", "optical", (-50.0, 0.0, 0.0), (-1.0, 0.0, 0.0), "1550 nm SMF-28 Vacuum Feedthrough", mating_part_id="S9.4-03", bore_mm=9.6),
    )
    design = make_part_design_from_bom(
        "S9.4-01",
        material="316LN",
        world_origin_mm=(-876.0, 0.0, 690.0),
        ports=ports,
        dimensions=(
            DimensionCallout("LEN_X", 100.0, 0.2, -0.2),
            DimensionCallout("BULK_Y", 120.0, 0.2, -0.2),
            DimensionCallout("BULK_Z", 120.0, 0.2, -0.2),
            DimensionCallout("CF63_OD", 113.5, 0.1, -0.1, prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.05, diameter_zone=True, datum_primary="A", feature_note="CF63 knife-edge axis"),
            GDTFrame("flatness", 0.02, datum_primary="A", feature_note="Hermetic bulkhead plate"),
        ),
        notes=("Exact BOM part_id S9.4-01 (resolves legacy cad/params.py S9.1 aliasing bug). Option-Q OVC -X CF63 4xSMA + 1550 nm SMF-28 vacuum feedthrough, 3.20 kg (Exp142).",),
        scad_params=(("cf_size", "CF63"), ("n_sma", 4), ("fiber_nm", 1550.0), ("mass_kg", 3.20)),
        target_mass_kg=3.20,
    )
    feats = (
        ScadFeature("add_cf_flange", {"size": "CF63", "bore_id": 50.0}, translate=(41.25, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="ISO 3669 CF63 vacuum flange"),
        ScadFeature("add_tube", {"od": 76.0, "id": 50.0, "h": 62.3}, translate=(1.15, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="316LN vacuum spool"),
        ScadFeature("add_box", {"dx": 7.9, "dy": 120.0, "dz": 120.0}, translate=(-34.05, 0.0, 0.0), comment="4x SMA + 1550 nm SMF-28 bulkhead"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s9_4_02() -> BuiltPart:
    """S9.4-02: Option-Q 20 mK shielded NbTiN 5-stage Chebyshev 50 Ohm <-> 3 kOhm qRAM transformer box (60x30x16 mm, 0.38 kg)."""
    # World origin: (-650.0, 0.0, 408.0) -> z_global = [400.0, 416.0] (exact 8.5 mm clearance below S6.11-02 TWPA z=424.5!)
    dx, dy, dz = 60.0, 30.0, 16.0
    parts: list[SolidMesh] = []
    # Gold-plated OFHC/Nb shielded enclosure with 4x M2 mounting holes (thick walls for magnetic & RF shielding)
    parts.append(
        make_rect_plate_with_features(
            dx, dy, 4.5,
            circular_holes=((-25.0, -10.5, 2.2), (25.0, -10.5, 2.2), (25.0, 10.5, 2.2), (-25.0, 10.5, 2.2)),
            hole_segments=10,
            center=(0.0, 0.0, -5.75),
            name="qram_base_ofhc",
            material="OFHC Cu",
        )
    )
    parts.append(make_hollow_frame(dx, dy, 44.0, 16.0, 6.8, center=(0.0, 0.0, 0.0), name="qram_nb_shield_wall", material="Nb"))
    parts.append(make_box(dx, dy, 4.5, center=(0.0, 0.0, 5.75), name="qram_nb_lid", material="Nb"))
    # Internal 5-stage Chebyshev / Klopfenstein NbTiN-on-Si chip (42x14x0.8 mm)
    parts.append(make_box(42.0, 14.0, 0.8, center=(0.0, 0.0, -2.9), name="qram_chebyshev_die", material="Si"))
    # 4x SMP cryogenic RF connectors on -X and +X faces
    for sgn in (-1.0, 1.0):
        for cy in (-6.0, 6.0):
            parts.append(make_cylinder(2.2, 4.0, segments=12, axis="x", center=(sgn * (0.5 * dx + 2.05), cy, 0.0), name="qram_smp", material="BeCu"))

    mesh = merge_solids(parts, name="S9.4-02", material="Nb")
    ports = (
        PortInterface("qram_50ohm_in", "rf", (-34.05, 0.0, 0.0), (-1.0, 0.0, 0.0), "2x 50 Ohm Cryo SMP (4-8 GHz)", mating_part_id="S9.4-03"),
        PortInterface("qram_3kohm_out", "rf", (34.05, 0.0, 0.0), (1.0, 0.0, 0.0), "2x 3 kOhm Bus Coupling SMP", mating_part_id="S6.10-01"),
    )
    design = make_part_design_from_bom(
        "S9.4-02",
        material="Nb",
        world_origin_mm=(DR_X_MM, DR_Y_MM, 408.0),
        ports=ports,
        dimensions=(
            DimensionCallout("BOX_X", dx, 0.05, -0.05),
            DimensionCallout("BOX_Y", dy, 0.05, -0.05),
            DimensionCallout("BOX_Z", dz, 0.05, -0.05),
        ),
        gdt_frames=(GDTFrame("flatness", 0.005, datum_primary="A", feature_note="Chebyshev die thermal seat"),),
        notes=("Exact BOM part_id S9.4-02 (resolves legacy cad/params.py S9.1 aliasing bug). 20 mK 5-stage Chebyshev 50 Ohm<->3 kOhm qRAM bridge (S11=-39.56 dB, 0.78 uW @ 20 mK, 8.5 mm clear below S6.11-02 TWPA, Exp142).",),
        scad_params=(("box_dx", dx), ("box_dy", dy), ("box_dz", dz), ("z_in_ohm", 50.0), ("z_out_ohm", 3000.0), ("stages", 5)),
        target_mass_kg=0.38,
    )
    feats = (
        ScadFeature("add_box", {"dx": dx, "dy": dy, "dz": dz}, comment="20 mK shielded 5-stage Chebyshev qRAM transformer box"),
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=feats)


def _build_s9_4_03() -> BuiltPart:
    """S9.4-03: Option-Q 4x NbTi cryo-coax + 1x 1550 nm SMF-28 cryo-fiber loom & thermal anchor clamps (0.82 kg)."""
    # World origin: (-793.0, 0.0, 560.0) -> x_global = [-798.0, -788.0], y = [-15, +15], z = [405.0, 715.0]
    # Threads strictly inside the 14.0 mm radial vacuum annulus between 50 K shield (R_in=150) & 4 K shield (R_out=136)!
    parts: list[SolidMesh] = []
    # 4x superconducting NbTi cryo-coax lines (r=1.1 mm) + 1x central jacketed 1550 nm SMF-28 fiber (r=1.6 mm), h=308 mm
    for idx, cy in enumerate((-10.5, -5.5, 5.5, 10.5), start=1):
        parts.append(make_cylinder(1.1, 308.0, segments=12, center=(0.0, cy, 0.0), name=f"optq_nbti_coax_{idx}", material="NbTi"))
    parts.append(make_cylinder(1.6, 308.0, segments=12, center=(0.0, 0.0, 0.0), name="optq_smf28_cryo_fiber", material="BeCu"))
    # 4x gold-plated OFHC Cu thermalization clamp blocks (10 x 30 x 10 mm) at 300K/50K/4K/MXC anchor heights
    feats: list[ScadFeature] = [
        ScadFeature("add_cylinder", {"d": 3.2, "h": 308.0}, comment="1550 nm SMF-28 cryo-fiber jacket"),
    ]
    for c_idx, cz in enumerate((-148.0, -50.0, 50.0, 148.0), start=1):
        # Split clamp bars cleanly on +X and -X sides of the 5 lines so zero shell self-overlap
        parts.append(make_box(2.6, 30.0, 10.0, center=(-3.7, 0.0, cz), name=f"optq_clamp_l_{c_idx}", material="OFHC Cu"))
        parts.append(make_box(2.6, 30.0, 10.0, center=(3.7, 0.0, cz), name=f"optq_clamp_r_{c_idx}", material="OFHC Cu"))
        feats.append(
            ScadFeature("add_box", {"dx": 10.0, "dy": 30.0, "dz": 10.0}, translate=(0.0, 0.0, cz), comment=f"Cryo-fiber thermal anchor clamp #{c_idx}")
        )

    mesh = merge_solids(parts, name="S9.4-03", material="OFHC Cu")
    ports = (
        PortInterface("optq_loom_top", "optical", (0.0, 0.0, 154.0), (0.0, 0.0, 1.0), "4x NbTi SMA + SMF-28 to S9.4-01", mating_part_id="S9.4-01"),
        PortInterface("optq_loom_mxc", "optical", (0.0, 0.0, -154.0), (0.0, 0.0, -1.0), "4x NbTi SMP + Fiber to S9.4-02", mating_part_id="S9.4-02"),
    )
    design = make_part_design_from_bom(
        "S9.4-03",
        material="OFHC Cu",
        world_origin_mm=(-793.0, 0.0, 560.0),
        ports=ports,
        dimensions=(
            DimensionCallout("LOOM_X", 10.0, 0.1, -0.1),
            DimensionCallout("LOOM_Y", 30.0, 0.1, -0.1),
            DimensionCallout("LOOM_Z", 308.0, 0.5, -0.5),
        ),
        notes=("Exact BOM part_id S9.4-03 (resolves legacy cad/params.py S9.1 aliasing bug). Routed cleanly in 14 mm radial annulus between 50 K shield (R_in=150) & 4 K shield (R_out=136), 0.82 kg (Exp142).",),
        scad_params=(("n_nbti_coax", 4), ("n_smf28_fiber", 1), ("n_clamps", 4), ("mass_kg", 0.82)),
        target_mass_kg=0.82,
    )
    return BuiltPart(design=design, mesh=mesh, scad_features=tuple(feats))


# ---------------------------------------------------------------------------
# Public Subsystem Builders & Unified 43/43 Exporter
# ---------------------------------------------------------------------------
def build_s6_dr_readout_parts() -> dict[str, BuiltPart]:
    """Build the 19 DR, multiplexed cryo-readout, M4 & Exp140 parts owned by this module."""
    builders = (
        _build_s6_6_01,
        _build_s6_6_02,
        _build_s6_6_03,
        _build_s6_6_04,
        _build_s6_6_05,
        _build_s6_6_06,
        _build_s6_6_07,
        _build_s6_7_01,
        _build_s6_7_02,
        _build_s6_8_01,
        _build_s6_8_02,
        _build_s6_8_04,
        _build_s6_10_01,
        _build_s6_10_03,
        _build_s6_10_04,
        _build_s6_11_01,
        _build_s6_11_02,
        _build_s6_11_03,
        _build_s6_11_04,
    )
    out: dict[str, BuiltPart] = {}
    for fn in builders:
        bp = fn()
        out[bp.part_id] = bp
    return out


def build_s6_parts() -> dict[str, BuiltPart]:
    """Build ALL 40 physical parts of Subsystem S6 in canonical BOM_DETAILED.csv order."""
    combined = {}
    combined.update(build_s6_magnet_shields_parts())
    combined.update(build_s6_dr_readout_parts())
    expected = list_physical_part_ids("S6")
    missing = [pid for pid in expected if pid not in combined]
    extra = [pid for pid in combined if pid not in expected]
    if missing or extra:
        raise RuntimeError(f"S6 physical part mismatch: missing={missing}, extra={extra}")
    return {pid: combined[pid] for pid in expected}


def build_s9_optq_parts() -> dict[str, BuiltPart]:
    """Build ALL 3 Option-Q parts (S9.4-01, S9.4-02, S9.4-03)."""
    builders = (_build_s9_4_01, _build_s9_4_02, _build_s9_4_03)
    out: dict[str, BuiltPart] = {}
    for fn in builders:
        bp = fn()
        out[bp.part_id] = bp
    return out


def export_all(
    out_s6_dir: Path | str = DEFAULT_OUT_S6_DIR,
    out_s9_optq_dir: Path | str = DEFAULT_OUT_S9_OPTQ_DIR,
) -> dict[str, Any]:
    """Build, verify, and export ALL 43 physical parts (40 S6 + 3 Option-Q) with 0 clashes & cryo checks."""
    s6_parts = build_s6_parts()
    s9_parts = build_s9_optq_parts()
    all_parts: dict[str, BuiltPart] = {}
    all_parts.update(s6_parts)
    all_parts.update(s9_parts)

    clash_report = check_assembly_clashes(all_parts)
    thermal_report = run_cryo_thermal_checks()

    s6_out = Path(out_s6_dir)
    s9_out = Path(out_s9_optq_dir)
    s6_out.mkdir(parents=True, exist_ok=True)
    s9_out.mkdir(parents=True, exist_ok=True)

    s6_results: dict[str, dict[str, Any]] = {}
    s9_results: dict[str, dict[str, Any]] = {}
    total_mass_s6 = 0.0
    total_mass_s9 = 0.0
    all_valid = True

    for pid, bp in s6_parts.items():
        extra = thermal_report if pid in {"S6.3-01", "S6.3-03", "S6.2-02", "S6.9-02"} else None
        res, _ = export_part_with_json(bp, s6_out, extra_metadata=extra)
        s6_results[pid] = res.to_dict()
        total_mass_s6 += res.mass_kg
        if not res.all_valid:
            all_valid = False

    for pid, bp in s9_parts.items():
        res, _ = export_part_with_json(bp, s9_out)
        s9_results[pid] = res.to_dict()
        total_mass_s9 += res.mass_kg
        if not res.all_valid:
            all_valid = False

    s6_manifest = {
        "subsystem": "S6",
        "work_package": "WP-M4",
        "part_count": len(s6_results),
        "total_computed_mass_kg": round(total_mass_s6, 4),
        "all_parts_valid": all(v["all_valid"] for v in s6_results.values()),
        "clash_report": clash_report,
        "cryo_thermal_report": thermal_report,
        "parts": s6_results,
        "epistemic": {
            "design_maturity": DESIGN_MATURITY,
            "no_lab_measurement": NO_LAB_MEASUREMENT,
            "iec61508_certified": IEC61508_CERTIFIED,
            "semi_s2_certified": SEMI_S2_CERTIFIED,
        },
    }
    s9_manifest = {
        "subsystem": "S9_optq",
        "work_package": "WP-M4",
        "part_count": len(s9_results),
        "total_computed_mass_kg": round(total_mass_s9, 4),
        "all_parts_valid": all(v["all_valid"] for v in s9_results.values()),
        "clash_report": clash_report,
        "parts": s9_results,
        "epistemic": {
            "design_maturity": DESIGN_MATURITY,
            "no_lab_measurement": NO_LAB_MEASUREMENT,
            "iec61508_certified": IEC61508_CERTIFIED,
            "semi_s2_certified": SEMI_S2_CERTIFIED,
        },
    }
    (s6_out / "s6_manifest.json").write_text(json.dumps(s6_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (s9_out / "s9_optq_manifest.json").write_text(json.dumps(s9_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "total_parts": len(all_parts),
        "s6_part_count": len(s6_results),
        "s9_optq_part_count": len(s9_results),
        "s6_mass_kg": round(total_mass_s6, 4),
        "s9_optq_mass_kg": round(total_mass_s9, 4),
        "total_mass_kg": round(total_mass_s6 + total_mass_s9, 4),
        "all_valid": bool(all_valid and clash_report["passed"] and thermal_report["all_passed"]),
        "clash_report": clash_report,
        "cryo_thermal_report": thermal_report,
        "s6_results": s6_results,
        "s9_optq_results": s9_results,
    }


if __name__ == "__main__":
    summary = export_all()
    print(
        f"Exported {summary['total_parts']} parts "
        f"(S6={summary['s6_part_count']}, S9_optq={summary['s9_optq_part_count']}), "
        f"mass={summary['total_mass_kg']:.2f} kg, "
        f"clashes={summary['clash_report']['clash_count']}, "
        f"thermal_pass={summary['cryo_thermal_report']['all_passed']}, "
        f"all_valid={summary['all_valid']}"
    )
