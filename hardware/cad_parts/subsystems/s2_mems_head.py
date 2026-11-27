"""Subsystem S2 — Arch-B 32x32 MEMS Multi-Beam Write Head, Blanker, Mini-Lens & Metrology.

Designs, verifies, and exports all 15 physical solid BOM parts of ``S2``
(``S2.1-01`` through ``S2.5-03``, excluding the 3 non-solid fab NRE rows
``S2.1-02``, ``S2.2-02``, ``S2.3-02``: 11 ``CUSTOM_FULL`` + 4 ``COTS_ENV_ICD``)
using the pure-Python CAD kernel in ``hardware.cad_parts.core``.

Locked Exp124 / Exp84 Arch-B Optical & Mechanical Anchors:
- Global ``Z = 0.000 mm``: Wafer active top surface (``0 V``).
- Working Distance ``WD = 0.250 mm`` (``S2.3-01`` bottom surface at ``Z = +0.250 mm``).
- Co-pitched ``32 x 32 = 1,024`` beamlets at ``0.50 mm`` pitch (``16.0 x 16.0 mm`` active
  square, diagonal ``22.627 mm``, clear bore ``Ø28.0 mm`` -> ``2.686 mm`` radial margin).
- ``S2.3-01`` 3-wafer anodically bonded Arch-B mini-lens: ``h = 1.760 mm`` (``Z ∈ [0.250, 2.010]``),
  ``D = 0.30 mm``, ``E_gap = 10.60 MV/m``, ``C_c = 2.660 mm``, ``σ_spot = 1.428 nm``.
- ``S2.2-01`` + ``S2.2-04`` co-pitched blanker & separate graphite-Mo beam-stop (``f1 = 2.59 MHz``).
- ``S2.1-01`` true ``30 um`` SOI ``32 x 32`` aperture plate at ``Z = 7.660 mm`` + ``S2.1-04``
  kinematic cassette reaching exact Exp124 ``Z = 31.660 mm``.
- ``S2.5-02`` Invar-36 3-DOF piezo mount bridges ``Z ∈ [31.910, 39.410]`` below ``S1.3-02``
  (``Z = 39.660 mm``).
- All in-bore head components stay strictly inside ``R <= 68.0 mm < 75.0 mm`` (``Ø150 mm``
  Exp125 cryo-magnet clear bore).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from hardware.cad_parts.core import (
    DESIGN_MATURITY,
    IEC61508_CERTIFIED,
    NO_LAB_MEASUREMENT,
    REPO_ROOT,
    SEMI_S2_CERTIFIED,
    DimensionCallout,
    GDTFrame,
    PartArtifactResult,
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
    make_mems_grid_plate,
    make_part_design_from_bom,
    make_plate_with_holes,
    make_ring_with_bolt_circle,
    make_swept_tube,
    make_tube,
    merge_solids,
    transform_mesh,
)
from hardware.cad_parts.subsystems.s1_ion_column import (
    RACK_BAY1_FRONT_Y,
    BuiltPart,
    make_rack_unit_chassis,
)

S2_OUT_DIR: Path = REPO_ROOT / "hardware" / "cad_parts" / "out" / "S2"


def _arc_sector_polygon_2d(
    r_in: float,
    r_out: float,
    deg_start: float,
    deg_end: float,
    n_arc: int = 16,
) -> list[tuple[float, float]]:
    """Build CCW 2D annular sector polygon from ``deg_start`` to ``deg_end``."""
    pts: list[tuple[float, float]] = []
    for i in range(n_arc + 1):
        a = math.radians(deg_start + (deg_end - deg_start) * i / n_arc)
        pts.append((r_out * math.cos(a), r_out * math.sin(a)))
    for i in range(n_arc, -1, -1):
        a = math.radians(deg_start + (deg_end - deg_start) * i / n_arc)
        pts.append((r_in * math.cos(a), r_in * math.sin(a)))
    return pts


# ---------------------------------------------------------------------------
# Engineering Thermal & GD&T Verification Suite for S2
# ---------------------------------------------------------------------------
def compute_s2_engineering_checks() -> dict[str, Any]:
    """Compute NIST bakeout/cold-radiative clearances & Arch-B WD/registration stackups."""
    # 1. 150 C UHV bakeout (423.15 K): S2.1-04 AlN cassette pocket (ID 54.5 mm) vs S2.1-03 Mo guard frame (OD 54.0 mm)
    bake_aln_mo = check_cold_clearance(
        "AlN",
        "Mo",
        nominal_outer_id_mm=54.50,
        nominal_inner_od_mm=54.00,
        t_cold_k=423.15,
        min_required_radial_clearance_mm=0.15,
        outer_id_tol_mm=0.02,
        inner_od_tol_mm=0.02,
    )
    # 2. 100 K cold-radiative soak above 20 mK chuck: AlN cassette vs Mo guard frame (CTE matched!)
    cold_aln_mo = check_cold_clearance(
        "AlN",
        "Mo",
        nominal_outer_id_mm=54.50,
        nominal_inner_od_mm=54.00,
        t_cold_k=100.0,
        min_required_radial_clearance_mm=0.15,
        outer_id_tol_mm=0.02,
        inner_od_tol_mm=0.02,
    )
    # 3. 150 C bakeout (423.15 K): S2.4-02 Rogers RO4350B UHV PCB ring (ID 67.0, OD 128.0) vs Si blanker & S6.2-02 bridge
    #    Uses actual Rogers RO4350B in-plane CTE (12.0 ppm/K, Tg > 280 C >> 150 C bakeout), replacing legacy Invar-36 proxy.
    dt_bake_k = 423.15 - 293.15  # +130.0 K
    rogers_cte_ppm_k = 12.0      # Rogers RO4350B conservative in-plane CTE (10-12 ppm/K datasheet)
    rogers_strain_423k = rogers_cte_ppm_k * 1e-6 * dt_bake_k  # +1.560e-3
    si_strain_423k = 0.380e-3    # NIST/Swenson Si integrated strain at 423.15 K
    rogers_id_423k = 67.00 * (1.0 + rogers_strain_423k)
    si_od_423k = 60.00 * (1.0 + si_strain_423k)
    inner_nom_clr = 0.5 * (rogers_id_423k - si_od_423k)
    inner_wc_clr = inner_nom_clr - 0.5 * (0.10 + 0.05)
    rogers_outer_r_423k = 64.00 * (1.0 + rogers_strain_423k)
    outer_exp_um = (rogers_outer_r_423k - 64.00) * 1000.0  # +99.84 um
    bridge_gap_423k_mm = 66.00 - rogers_outer_r_423k       # 1.900 mm clear to S6.2-02 @ X=-66.0
    tg_rogers_c = 280.0
    bakeout_c = 150.0
    bake_pcb_rogers = {
        "outer_material": "Rogers RO4350B",
        "inner_material": "Si",
        "t_cold_k": 423.15,
        "t_ref_k": 293.15,
        "rogers_cte_xy_ppm_k": rogers_cte_ppm_k,
        "rogers_tg_c": tg_rogers_c,
        "bakeout_temp_c": bakeout_c,
        "tg_margin_c": tg_rogers_c - bakeout_c,
        "outer_strain": round(rogers_strain_423k, 6),
        "inner_strain": si_strain_423k,
        "warm_outer_id_mm": 67.00,
        "warm_inner_od_mm": 60.00,
        "cold_outer_id_mm": round(rogers_id_423k, 5),
        "cold_inner_od_mm": round(si_od_423k, 5),
        "cold_nominal_radial_clearance_mm": round(inner_nom_clr, 5),
        "cold_worst_case_radial_clearance_mm": round(inner_wc_clr, 5),
        "min_required_radial_clearance_mm": 3.0,
        "outer_radial_expansion_um": round(outer_exp_um, 2),
        "cold_bridge_gap_423k_mm": round(bridge_gap_423k_mm, 4),
        "interference_risk": (inner_wc_clr <= 0.0) or (bridge_gap_423k_mm <= 0.5),
        "passed": (inner_wc_clr >= 3.0) and (bridge_gap_423k_mm >= 1.5) and (tg_rogers_c - bakeout_c >= 100.0),
    }
    # 4. UHV conductive thermal closure for -5 kV blanker deck (0.50 W nom / 4.43 W 50 kHz burst)
    #    4x HV-isolated AlN blocks (k=180 W/mK, 4 mm thick -> >10 kV) + 4x OFHC Cu straps (k=400 W/mK)
    r_th_aln = 0.004 / (180.0 * 4.0 * 48.0e-6)  # 0.116 K/W
    r_th_cu = 0.035 / (400.0 * 4.0 * 12.0e-6)   # 1.823 K/W
    r_th_iface = 0.261                          # Dry-indium / Au-clamp contact resistance
    r_th_total = r_th_aln + r_th_cu + r_th_iface  # 2.20 K/W
    dt_nom_k = 0.50 * r_th_total                # 1.10 K @ 0.50 W
    dt_burst_k = 4.43 * r_th_total              # 9.75 K @ 4.43 W burst
    si_pitch_drift_um = 2.6e-6 * dt_nom_k * 500.0  # 0.00143 um << 0.20 um spec
    blanker_thermal_closure = {
        "r_th_aln_k_per_w": round(r_th_aln, 4),
        "r_th_cu_k_per_w": round(r_th_cu, 4),
        "r_th_total_k_per_w": round(r_th_total, 3),
        "hv_isolation_rating_kV": 15.0,
        "p_nom_W": 0.50,
        "p_burst_50khz_W": 4.43,
        "delta_t_nom_K": round(dt_nom_k, 2),
        "delta_t_burst_K": round(dt_burst_k, 2),
        "si_pitch_drift_nom_um": round(si_pitch_drift_um, 5),
        "passed": (dt_burst_k < 15.0) and (si_pitch_drift_um < 0.05),
    }
    # 5. Arch-B Working Distance WD = 0.250 mm pre-servo mechanical stackup vs ±100 um S2.5-02 piezo Z stroke
    wd_stack = check_tolerance_stack(
        [
            ToleranceContributor("S2.5-02_piezo_mount_datum", 31.910, 0.005, -0.005, sign=+1.0),
            ToleranceContributor("S2.1-04_aln_cassette_seat", 21.270, 0.005, -0.005, sign=-1.0),
            ToleranceContributor("S2.3-03_sapphire_spacer_ring", 8.630, 0.0005, -0.0005, sign=-1.0),
            ToleranceContributor("S2.3-01_archB_minilens_h", 1.760, 0.002, -0.002, sign=-1.0),
        ],
        target_min_mm=0.220,
        target_max_mm=0.280,
    )
    # 6. Co-pitched 32x32 lateral optical registration stackup (aperture <-> blanker <-> mini-lens)
    lateral_reg_stack = check_tolerance_stack(
        [
            ToleranceContributor("S2.1-01_soi_cd_error", 0.0, 0.00005, -0.00005),
            ToleranceContributor("S2.2-01_blanker_elec_pitch", 0.0, 0.00020, -0.00020),
            ToleranceContributor("S2.3-01_minilens_roundness", 0.0, 0.00005, -0.00005),
            ToleranceContributor("S2.3-03_dowel_pin_reg", 0.0, 0.00050, -0.00050),
        ],
        target_min_mm=-0.005,
        target_max_mm=+0.005,
    )
    return {
        "bakeout_aln_mo_clearance": bake_aln_mo.to_dict(),
        "cold100k_aln_mo_clearance": cold_aln_mo.to_dict(),
        "bakeout_pcb_blanker_clearance": bake_pcb_rogers,
        "blanker_uhv_thermal_closure": blanker_thermal_closure,
        "archB_wd_tolerance_stack": wd_stack.to_dict(),
        "mems_32x32_lateral_registration": lateral_reg_stack.to_dict(),
    }


# ---------------------------------------------------------------------------
# Master S2 Builder: All 15 Physical BOM Parts (S2.1-01 .. S2.5-03)
# ---------------------------------------------------------------------------
def build_s2_parts() -> dict[str, BuiltPart]:
    """Construct all 15 physical solid CAD parts of Subsystem S2 in global coordinates."""
    checks = compute_s2_engineering_checks()
    parts: dict[str, BuiltPart] = {}

    # -----------------------------------------------------------------------
    # S2.1-01: True 32x32 @ 0.50 mm 30 um SOI MEMS Aperture Plate (Ø10.5 um, Z=[7.660, 7.690])
    # -----------------------------------------------------------------------
    m_s2101 = make_mems_grid_plate(
        width_x=24.0,
        width_y=24.0,
        thickness=0.030,
        nx=32,
        ny=32,
        pitch_x=0.50,
        pitch_y=0.50,
        hole_diameter=0.0105,  # Exact 10.5 um beam-defining aperture (r=5.25 um -> alpha=6.40 mrad, sigma_s=0.50 nm!)
        hole_sub_per_side=2,
        outer_diameter=36.0,
        axis="z",
        center=(0.0, 0.0, 7.675),
        name="S2.1-01",
        material="Si",
    )
    d_s2101 = make_part_design_from_bom(
        "S2.1-01",
        design_tier="CUSTOM_FULL",
        material="Si",
        surface_finish_ra_um=0.05,
        world_origin_mm=(0.0, 0.0, 7.675),
        ports=(
            PortInterface("beamlet_array_in", "vacuum", (0.0, 0.0, 7.690), (0.0, 0.0, 1.0), "32x32 Ø10.5 um @ 0.50 mm SOI", mating_part_id="S2.1-03", bore_mm=22.627, od_mm=36.0, frame="global"),
            PortInterface("beamlet_array_out", "vacuum", (0.0, 0.0, 7.660), (0.0, 0.0, -1.0), "32x32 Ø10.5 um @ 0.50 mm SOI", mating_part_id="S2.2-03", bore_mm=22.627, od_mm=36.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("WAFER_OD", 36.0, 0.02, -0.02, prefix="Ø"),
            DimensionCallout("APERTURE_D", 0.0105, 0.0002, -0.0002, prefix="Ø", decimals=4),
            DimensionCallout("SOI_THICK", 0.030, 0.002, -0.002, decimals=3),
            DimensionCallout("PITCH_32X32", 0.500, 0.00005, -0.00005, decimals=4),
            DimensionCallout("ACTIVE_SPAN", 16.00, 0.005, -0.005),
        ),
        gdt_frames=(
            GDTFrame("position", 0.0001, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="1024 Ø10.5 UM APERTURES"),
            GDTFrame("flatness", 0.002, datum_primary="", feature_note="30 UM SOI MEMBRANE"),
        ),
        scad_params=(("nx", 32), ("ny", 32), ("pitch_mm", 0.50), ("hole_d_mm", 0.0105), ("alpha_land_mrad", 6.40), ("sigma_s_nm", 0.50), ("soi_t_mm", 0.030), ("wafer_od", 36.0)),
        notes=(
            "True 32x32 = 1,024 beamlet 30 um SOI wafer with optical-spec Ø10.5 um (r=5.25 um) apertures (alpha=6.40 mrad, sigma_s=0.50 nm at f_img=0.82 mm); Euler genus = 1,024",
        ),
        target_mass_kg=0.00007,
    )
    f_s2101 = (
        ScadFeature("add_cylinder", {"d": 36.0, "h": 0.030}, comment="30 um highly-doped SOI aperture membrane"),
        ScadFeature("cut_grid_holes", {"nx": 32, "ny": 32, "pitch_x": 0.50, "pitch_y": 0.50, "hole_d": 0.0105, "h": 0.10}, comment="32x32 = 1,024 Arch-B Ø10.5 um beam-defining apertures"),
    )
    parts["S2.1-01"] = BuiltPart(d_s2101, m_s2101, f_s2101, {"lateral_registration": checks["mems_32x32_lateral_registration"]})

    # -----------------------------------------------------------------------
    # S2.1-03: Anti-Charge Au/Ti Conductive Guard Frame (Mo, Z=[7.940, 10.140])
    # -----------------------------------------------------------------------
    guard_ring = make_ring_with_bolt_circle(
        14.0, 27.0, 2.20, pcd=46.0, n_bolts=6, bolt_diameter=2.4, sub_per_side=2,
        axis="z", center=(0.0, 0.0, 9.040), name="S2.1-03_mo_guard_ring", material="Mo",
    )
    s2103_parts: list[SolidMesh] = [guard_ring]
    # 3x Au/Ti thermal grounding tabs cleanly seated on top perimeter (Z ∈ [9.20, 10.14], R ∈ [21.0, 26.5])
    # Actually place 3x stepped inner anti-charge shield boss lips at R ∈ [14.0, 16.5], Z ∈ [7.94, 8.60]?
    # Ring already fills R ∈ [14.0, 27.0] cleanly; add 3 radial grounding ear tabs outside R=27.2..30.0 (zero overlap!)
    for k in range(3):
        ang = math.radians(k * 120.0 + 30.0)
        tab = transform_mesh(
            make_chamfered_box(3.2, 6.0, 1.80, chamfer=0.3, name=f"S2.1-03_tab_{k}", material="Au"),
            rotation_deg=(0.0, 0.0, k * 120.0 + 30.0),
            translation=(28.9 * math.cos(ang), 28.9 * math.sin(ang), 9.040),
        )
        s2103_parts.append(tab)
    m_s2103 = merge_solids(s2103_parts, name="S2.1-03", material="Mo")
    d_s2103 = make_part_design_from_bom(
        "S2.1-03",
        design_tier="CUSTOM_FULL",
        material="Mo",
        surface_finish_ra_um=0.2,
        world_origin_mm=(0.0, 0.0, 9.040),
        ports=(
            PortInterface("aperture_clamp_bot", "mechanical", (0.0, 0.0, 7.940), (0.0, 0.0, -1.0), "Ø28.0 mm Guard Lip", mating_part_id="S2.1-01", bore_mm=28.0, od_mm=54.0, pcd_mm=46.0, bolt_count=6, bolt_hole_mm=2.4, frame="global"),
            PortInterface("cassette_seat_top", "mechanical", (0.0, 0.0, 10.140), (0.0, 0.0, 1.0), "6xM2 PCD 46", mating_part_id="S2.1-04", bore_mm=28.0, od_mm=54.0, pcd_mm=46.0, bolt_count=6, bolt_hole_mm=2.4, frame="global"),
        ),
        dimensions=(
            DimensionCallout("CLEAR_BORE", 28.0, 0.01, -0.01, prefix="Ø"),
            DimensionCallout("FRAME_OD", 54.0, 0.02, -0.02, prefix="Ø"),
            DimensionCallout("THICK", 2.20, 0.01, -0.01),
            DimensionCallout("PCD_6XM2", 46.0, 0.02, -0.02, prefix="Ø"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.005, datum_primary="", feature_note="SOI CLAMP FACE"),
            GDTFrame("concentricity", 0.010, diameter_zone=True, datum_primary="B", feature_note="Ø28 GUARD BORE"),
        ),
        scad_params=(("bore_id", 28.0), ("frame_od", 54.0), ("thickness", 2.20), ("au_ti_coat_nm", 50.0)),
        notes=("50 nm Au/Ti anti-charge conductive coating (<1 Ohm/sq) on Mo precision clamping frame; 2.686 mm radial margin to beam diagonal",),
        target_mass_kg=0.039,
    )
    f_s2103 = (
        ScadFeature("add_tube", {"od": 54.0, "id": 28.0, "h": 2.20}, comment="Au/Ti-coated Mo anti-charge guard frame"),
        ScadFeature("cut_bolt_circle", {"pcd": 46.0, "bolt_d": 2.4, "count": 6, "h": 5.0}, comment="6xM2 clamping bolt holes"),
    )
    parts["S2.1-03"] = BuiltPart(
        d_s2103, m_s2103, f_s2103,
        {"bakeout_aln_mo": checks["bakeout_aln_mo_clearance"], "cold100k_aln_mo": checks["cold100k_aln_mo_clearance"]},
    )

    # -----------------------------------------------------------------------
    # S2.1-04: Precision AlN Ceramic / Ti-6Al-4V Kinematic Aperture Cassette (Z=[10.390, 31.660])
    # -----------------------------------------------------------------------
    # Inner CTE-matched AlN cassette core (ID=28.0, OD=64.0, Z ∈ [10.39, 25.00])
    aln_core = make_ring_with_bolt_circle(
        14.0, 32.0, 14.61, pcd=46.0, n_bolts=6, bolt_diameter=2.4, sub_per_side=2,
        axis="z", center=(0.0, 0.0, 17.695), name="S2.1-04_aln_core", material="AlN",
    )
    # Outer Ti-6Al-4V kinematic flange ring (ID=64.6, OD=100.0, Z ∈ [10.39, 31.66], exact Exp124 top 31.660!)
    ti_cassette = make_ring_with_bolt_circle(
        32.3, 50.0, 21.27, pcd=88.0, n_bolts=12, bolt_diameter=4.5, sub_per_side=2,
        axis="z", center=(0.0, 0.0, 21.025), name="S2.1-04_ti_outer_ring", material="Ti-6Al-4V",
    )
    s2104_parts: list[SolidMesh] = [aln_core, ti_cassette]
    # 3x Maxwell V-groove kinematic coupling seat pads atop AlN core (Z ∈ [25.25, 31.66], R ∈ [18..31])
    for k in range(3):
        ang = math.radians(k * 120.0)
        pad = transform_mesh(
            make_chamfered_box(12.0, 8.0, 6.40, chamfer=1.0, name=f"S2.1-04_vgroove_{k}", material="Ti-6Al-4V"),
            rotation_deg=(0.0, 0.0, k * 120.0),
            translation=(24.5 * math.cos(ang), 24.5 * math.sin(ang), 28.45),
        )
        s2104_parts.append(pad)
    m_s2104 = merge_solids(s2104_parts, name="S2.1-04", material="AlN")
    d_s2104 = make_part_design_from_bom(
        "S2.1-04",
        design_tier="CUSTOM_FULL",
        material="AlN",
        surface_finish_ra_um=0.2,
        world_origin_mm=(0.0, 0.0, 21.025),
        ports=(
            PortInterface("guard_mount_bot", "mechanical", (0.0, 0.0, 10.390), (0.0, 0.0, -1.0), "Ø28.0 mm Bore", mating_part_id="S2.1-03", bore_mm=28.0, od_mm=100.0, pcd_mm=46.0, bolt_count=6, bolt_hole_mm=2.4, frame="global"),
            PortInterface("kinematic_top", "mechanical", (0.0, 0.0, 31.660), (0.0, 0.0, 1.0), "Maxwell 3-V / 12xM4 PCD 88", mating_part_id="S2.5-02", bore_mm=28.0, od_mm=100.0, pcd_mm=88.0, bolt_count=12, bolt_hole_mm=4.5, frame="global"),
        ),
        dimensions=(
            DimensionCallout("OD", 100.0, 0.02, -0.02, prefix="Ø"),
            DimensionCallout("CLEAR_BORE", 28.0, 0.01, -0.01, prefix="Ø"),
            DimensionCallout("HEIGHT", 21.27, 0.005, -0.005),
            DimensionCallout("Z_TOP_REF", 31.66, 0.01, -0.01),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.005, datum_primary="", feature_note="KINEMATIC DATUM A"),
            GDTFrame("parallelism", 0.005, datum_primary="A", feature_note="TOP/BOT FACES"),
            GDTFrame("concentricity", 0.005, diameter_zone=True, datum_primary="B", feature_note="OPTICAL BORE"),
        ),
        scad_params=(("od", 100.0), ("bore_id", 28.0), ("height", 21.27), ("cte_ppm_K", 4.5)),
        notes=("Exp124 kinematic aperture sub-carrier cassette (top at Z=31.660 mm); AlN core (4.5 ppm/K) + Ti-6Al-4V Maxwell 3-V outer ring",),
        target_mass_kg=0.72,
    )
    f_s2104 = (
        ScadFeature("add_tube", {"od": 100.0, "id": 64.6, "h": 21.27}, comment="Ti-6Al-4V kinematic cassette outer ring"),
        ScadFeature("add_tube", {"od": 64.0, "id": 28.0, "h": 14.61}, translate=(0.0, 0.0, -3.33), comment="AlN CTE-matched inner core"),
        ScadFeature("cut_bolt_circle", {"pcd": 88.0, "bolt_d": 4.5, "count": 12, "h": 26.0}, comment="12xM4 kinematic flange bolts"),
    )
    parts["S2.1-04"] = BuiltPart(
        d_s2104, m_s2104, f_s2104,
        {"bakeout_aln_mo": checks["bakeout_aln_mo_clearance"], "wd_stack": checks["archB_wd_tolerance_stack"]},
    )

    # -----------------------------------------------------------------------
    # S2.2-01: Coaxially Shielded 32x32 @ 0.50 mm Differential MEMS Blanker Plate (Z=[4.460, 5.860])
    # -----------------------------------------------------------------------
    # 0.160 mm coaxial bore inside 0.500 mm pitch leaves 340 um inter-channel Si web containing
    # >=80 um grounded coaxial Si septum partition walls (eliminating 95.9-99.7 nm crosstalk -> 4.08e-7 nm!)
    blanker_grid = make_mems_grid_plate(
        width_x=24.0,
        width_y=24.0,
        thickness=0.80,
        nx=32,
        ny=32,
        pitch_x=0.50,
        pitch_y=0.50,
        hole_diameter=0.160,
        hole_sub_per_side=2,
        outer_diameter=50.0,
        axis="z",
        center=(0.0, 0.0, 5.160),
        name="S2.2-01_coax_shielded_blanker_mems",
        material="Si",
    )
    # Stepped perimeter stiffening bezel (R=26.2..30.0, sub_per_side=3 -> inner apothem 25.80 > 25.0, Exp84 membrane f1=2.591 MHz)
    blanker_rim = make_ring_with_bolt_circle(
        26.2, 30.0, 1.40, pcd=56.2, n_bolts=6, bolt_diameter=1.8, sub_per_side=3,
        axis="z", center=(0.0, 0.0, 5.160), name="S2.2-01_stiff_rim", material="Si",
    )
    m_s2201 = merge_solids([blanker_grid, blanker_rim], name="S2.2-01", material="Si")
    d_s2201 = make_part_design_from_bom(
        "S2.2-01",
        design_tier="CUSTOM_FULL",
        material="Si",
        surface_finish_ra_um=0.05,
        world_origin_mm=(0.0, 0.0, 5.160),
        ports=(
            PortInterface("blanker_inlet", "vacuum", (0.0, 0.0, 5.860), (0.0, 0.0, 1.0), "32x32 Coax-Shielded @ 0.50 mm", mating_part_id="S2.2-03", bore_mm=22.627, od_mm=60.0, frame="global"),
            PortInterface("blanker_outlet", "vacuum", (0.0, 0.0, 4.460), (0.0, 0.0, -1.0), "32x32 Coax-Shielded @ 0.50 mm", mating_part_id="S2.2-04", bore_mm=22.627, od_mm=60.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("OD", 60.0, 0.01, -0.01, prefix="Ø"),
            DimensionCallout("COAX_BORE", 0.160, 0.002, -0.002, prefix="Ø", decimals=3),
            DimensionCallout("SEPTUM_WALL", 0.080, 0.002, -0.002, decimals=3),
            DimensionCallout("MEMS_THICK", 0.800, 0.005, -0.005, decimals=3),
            DimensionCallout("RIM_H", 1.400, 0.005, -0.005, decimals=3),
            DimensionCallout("PITCH_32X32", 0.500, 0.0002, -0.0002, decimals=4),
        ),
        gdt_frames=(
            GDTFrame("position", 0.0002, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="1024 COAX-SHIELDED DEFLECTORS"),
            GDTFrame("flatness", 0.001, datum_primary="", feature_note="SI MEMS WAFER"),
        ),
        scad_params=(
            ("nx", 32),
            ("ny", 32),
            ("pitch_mm", 0.50),
            ("hole_d_mm", 0.160),
            ("coaxial_shield_septum_um", 80.0),
            ("v_blank_diff_10keV_Vpp", 106.6),
            ("v_blank_per_plate_V", 53.3),
            ("crosstalk_shielded_nm", 4.08e-7),
            ("membrane_f1_MHz", 2.591),
        ),
        notes=(
            "Arch-B co-pitched 32x32 = 1,024-ch coaxially shielded differential MEMS blanker (±53.3 V / 106.6 Vpp @ 10 keV; 80 um grounded Si septum walls suppress neighbor crosstalk from 95.9-99.7 nm to 4.08e-7 nm)",
            "Exp84 single Si membrane f1=2.591 MHz; deterministic single-ion windowing gates switching edges (2.1 ns HV / 10 ns clk) outside ion transit (3.2-7.9 ns)",
        ),
        target_mass_kg=0.006,
    )
    f_s2201 = (
        ScadFeature("add_cylinder", {"d": 50.0, "h": 0.80}, comment="Doped-Si 1024-ch coaxially shielded differential blanker wafer"),
        ScadFeature("add_tube", {"od": 60.0, "id": 52.4, "h": 1.40}, comment="Stiffening perimeter bezel (membrane f1=2.591 MHz)"),
        ScadFeature("cut_grid_holes", {"nx": 32, "ny": 32, "pitch_x": 0.50, "pitch_y": 0.50, "hole_d": 0.160, "h": 1.20}, comment="32x32 = 1,024 coaxial blanker channels w/ 80 um grounded Si septa"),
    )
    parts["S2.2-01"] = BuiltPart(d_s2201, m_s2201, f_s2201, {"lateral_registration": checks["mems_32x32_lateral_registration"]})

    # -----------------------------------------------------------------------
    # S2.2-03: Multilayer LTCC / AlN 1,024-ch Ceramic Interposer (Z=[6.110, 7.450])
    #          Thickness increased 1.15->1.34 mm closing 0.40 mm air gap to 0.21 mm mate clearance;
    #          includes 3x Ø2.5 mm pass-through bores at R=31.2 mm for S2.3-03 structural tie-rods!
    # -----------------------------------------------------------------------
    inter_holes = [circle_2d(14.0, segments=48, ccw=False)]
    for k in range(8):
        ang = math.radians(k * 45.0 + 22.5)
        inter_holes.append(circle_2d(1.1, cx=37.0 * math.cos(ang), cy=37.0 * math.sin(ang), segments=14, ccw=False))
    for deg in (0.0, 120.0, 240.0):
        ar = math.radians(deg)
        inter_holes.append(circle_2d(1.25, cx=31.2 * math.cos(ar), cy=31.2 * math.sin(ar), segments=14, ccw=False))
    inter_ring = make_plate_with_holes(
        circle_2d(41.0, segments=64, ccw=True),
        holes_2d=inter_holes,
        thickness=1.34,
        axis="z",
        center=(0.0, 0.0, 6.780),
        name="S2.2-03_ltcc_substrate",
        material="AlN",
    )
    m_s2203 = inter_ring
    d_s2203 = make_part_design_from_bom(
        "S2.2-03",
        design_tier="CUSTOM_FULL",
        material="AlN",
        surface_finish_ra_um=0.2,
        world_origin_mm=(0.0, 0.0, 6.780),
        ports=(
            PortInterface("microbump_to_blanker", "electrical", (0.0, 0.0, 6.110), (0.0, 0.0, -1.0), "1024-ch Micro-Bump", mating_part_id="S2.2-01", bore_mm=28.0, od_mm=82.0, frame="global"),
            PortInterface("fanout_to_tiles", "electrical", (41.0, 0.0, 6.780), (1.0, 0.0, 0.0), "16x64 Wire-Bond Fanout", mating_part_id="S2.4-01", od_mm=82.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("OD", 82.0, 0.02, -0.02, prefix="Ø"),
            DimensionCallout("BORE_ID", 28.0, 0.01, -0.01, prefix="Ø"),
            DimensionCallout("THICK", 1.34, 0.015, -0.015),
            DimensionCallout("PAD_PITCH", 0.50, 0.015, -0.015),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.010, datum_primary="", feature_note="LTCC MICRO-BUMP FACE"),
            GDTFrame("position", 0.015, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="16X64 FAN-OUT PADS"),
        ),
        scad_params=(("od", 82.0), ("bore_id", 28.0), ("thickness", 1.34), ("channels", 1024), ("tie_rod_pcd_mm", 62.4)),
        notes=("Multilayer UHV LTCC/AlN 1,024-ch fan-out interposer (t=1.34 mm closing 0.40 mm gap) with 3x Ø2.5 mm tie-rod bores @ R=31.2 mm",),
        target_mass_kg=0.020,
    )
    f_s2203 = (
        ScadFeature("add_tube", {"od": 82.0, "id": 28.0, "h": 1.34}, comment="Multilayer LTCC/AlN 1024-ch ceramic interposer"),
        ScadFeature("cut_bolt_circle", {"pcd": 74.0, "bolt_d": 2.2, "count": 8, "h": 4.0}, comment="8x precision alignment dowel bores"),
        ScadFeature("cut_bolt_circle", {"pcd": 62.4, "bolt_d": 2.5, "count": 3, "h": 4.0}, comment="3x S2.3-03 stack tie-rod pass-through bores"),
    )
    parts["S2.2-03"] = BuiltPart(d_s2203, m_s2203, f_s2203, {})

    # -----------------------------------------------------------------------
    # S2.2-04: Separate Graphite-Coated Mo Deflected-Ion Beam-Stop Diaphragm (Ø12.0 um, Z=[3.010, 4.210])
    # -----------------------------------------------------------------------
    stop_grid = make_mems_grid_plate(
        width_x=24.0,
        width_y=24.0,
        thickness=0.50,
        nx=32,
        ny=32,
        pitch_x=0.50,
        pitch_y=0.50,
        hole_diameter=0.012,  # Exact 12.0 um beam-stop (r=6.0 um > r_beam=5.25 um open; 0% blanked leak @ dx=25.4 um!)
        hole_sub_per_side=2,
        outer_diameter=50.0,
        axis="z",
        center=(0.0, 0.0, 3.610),
        name="S2.2-04_graphite_mo_stop",
        material="Mo",
    )
    stop_rim = make_ring_with_bolt_circle(
        26.2, 30.0, 1.20, pcd=56.2, n_bolts=6, bolt_diameter=2.0, sub_per_side=3,
        axis="z", center=(0.0, 0.0, 3.610), name="S2.2-04_ofhc_sink_rim", material="OFHC Cu",
    )
    m_s2204 = merge_solids([stop_grid, stop_rim], name="S2.2-04", material="Mo")
    d_s2204 = make_part_design_from_bom(
        "S2.2-04",
        design_tier="CUSTOM_FULL",
        material="Mo",
        surface_finish_ra_um=0.4,
        world_origin_mm=(0.0, 0.0, 3.610),
        ports=(
            PortInterface("beamstop_inlet", "vacuum", (0.0, 0.0, 4.210), (0.0, 0.0, 1.0), "32x32 Ø12.0 um Stop", mating_part_id="S2.2-01", bore_mm=22.627, od_mm=60.0, frame="global"),
            PortInterface("beamstop_outlet", "vacuum", (0.0, 0.0, 3.010), (0.0, 0.0, -1.0), "32x32 Ø12.0 um Stop", mating_part_id="S2.3-03", bore_mm=22.627, od_mm=60.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("OD", 60.0, 0.02, -0.02, prefix="Ø"),
            DimensionCallout("STOP_HOLE", 0.0120, 0.0005, -0.0005, prefix="Ø", decimals=4),
            DimensionCallout("RIM_H", 1.20, 0.01, -0.01),
        ),
        gdt_frames=(
            GDTFrame("position", 0.001, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="1024 Ø12 UM BEAM-STOP HOLES"),
            GDTFrame("flatness", 0.005, datum_primary="", feature_note="FARADAY DIAPHRAGM"),
        ),
        scad_params=(("nx", 32), ("ny", 32), ("pitch_mm", 0.50), ("stop_hole_mm", 0.012), ("blanked_leak_frac", 0.0), ("backscatter_max", 0.0001)),
        notes=("Separate solid graphite-coated Mo Faraday beam-stop (Ø12.0 um bores: 100% open pass for Ø10.5 um beam, 0.0% leak when blanked by 25.4 um @ ±53.3 V / 10 keV)",),
        target_mass_kg=0.019,
    )
    f_s2204 = (
        ScadFeature("add_cylinder", {"d": 50.0, "h": 0.50}, comment="Graphite-coated Mo beam-stop diaphragm"),
        ScadFeature("add_tube", {"od": 60.0, "id": 52.4, "h": 1.20}, comment="OFHC Cu thermal sink mounting rim"),
        ScadFeature("cut_grid_holes", {"nx": 32, "ny": 32, "pitch_x": 0.50, "pitch_y": 0.50, "hole_d": 0.012, "h": 1.00}, comment="32x32 Ø12.0 um pass-through beam-stop apertures"),
    )
    parts["S2.2-04"] = BuiltPart(d_s2204, m_s2204, f_s2204, {})

    # -----------------------------------------------------------------------
    # S2.3-01: 3-Wafer Anodically Bonded Arch-B Mini-Lens (Exp124: E_gap=9.71 MV/m < 10 MV/m, 0.005 um defocus)
    #          Z_nat=[0.250, 2.010], WD=0.250, E3=0.100, gap23=0.400, E2=0.160, gap12=0.900, E1=0.100 + 0.100 rim
    # -----------------------------------------------------------------------
    # Wafer 1 (E3 bottom 0 V ground electrode, Z ∈ [0.250, 0.350], t=0.100 mm)
    w1 = make_mems_grid_plate(
        24.0, 24.0, 0.100, nx=32, ny=32, pitch_x=0.50, pitch_y=0.50, hole_diameter=0.30,
        hole_sub_per_side=2, outer_diameter=60.0, axis="z", center=(0.0, 0.0, 0.300),
        name="S2.3-01_wafer1_ground_E3", material="Si",
    )
    # Bond Spacer 1 (gap23=0.400 mm nominal electrode-to-electrode, Z ∈ [0.352, 0.748], t=0.396 mm -> E_gap23=9.34 MV/m)
    b1 = make_tube(14.0, 29.0, 0.396, segments=48, axis="z", center=(0.0, 0.0, 0.550), name="S2.3-01_sio2_bond1_g23", material="Fused Silica")
    # Wafer 2 (E2 center focus electrode +3734.6 V wrt wafer / 1265.4 V kin, Z ∈ [0.750, 0.910], t=0.160 mm)
    w2 = make_mems_grid_plate(
        24.0, 24.0, 0.160, nx=32, ny=32, pitch_x=0.50, pitch_y=0.50, hole_diameter=0.30,
        hole_sub_per_side=2, outer_diameter=60.0, axis="z", center=(0.0, 0.0, 0.830),
        name="S2.3-01_wafer2_focus_E2", material="Si",
    )
    # Bond Spacer 2 (gap12=0.900 mm nominal electrode-to-electrode, Z ∈ [0.912, 1.808], t=0.896 mm -> E_gap12=9.71 MV/m < 10 MV/m!)
    b2 = make_tube(14.0, 29.0, 0.896, segments=48, axis="z", center=(0.0, 0.0, 1.360), name="S2.3-01_sio2_bond2_g12", material="Fused Silica")
    # Wafer 3 (E1 upper -5000 V / 10 keV entrance electrode, Z ∈ [1.810, 1.910], t=0.100 mm)
    w3 = make_mems_grid_plate(
        24.0, 24.0, 0.100, nx=32, ny=32, pitch_x=0.50, pitch_y=0.50, hole_diameter=0.30,
        hole_sub_per_side=2, outer_diameter=60.0, axis="z", center=(0.0, 0.0, 1.860),
        name="S2.3-01_wafer3_upper_E1", material="Si",
    )
    # Upper field-free entrance seating rim (R=14..30 mm, Z ∈ [1.912, 2.010], preserving exact TOTAL_H=1.760 mm!)
    e1_rim = make_tube(14.0, 30.0, 0.098, segments=48, axis="z", center=(0.0, 0.0, 1.961), name="S2.3-01_e1_entrance_rim", material="Si")
    m_s2301 = merge_solids([w1, b1, w2, b2, w3, e1_rim], name="S2.3-01", material="Si")
    d_s2301 = make_part_design_from_bom(
        "S2.3-01",
        design_tier="CUSTOM_FULL",
        material="Si",
        surface_finish_ra_um=0.05,
        world_origin_mm=(0.0, 0.0, 1.130),
        ports=(
            PortInterface("wafer_facing_wd", "vacuum", (0.0, 0.0, 0.250), (0.0, 0.0, -1.0), "Arch-B WD=0.250 mm", bore_mm=22.627, od_mm=60.0, frame="global"),
            PortInterface("minilens_top", "vacuum", (0.0, 0.0, 2.010), (0.0, 0.0, 1.0), "32x32 D=0.30 mm", mating_part_id="S2.3-03", bore_mm=22.627, od_mm=60.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("WAFER_OD", 60.0, 0.01, -0.01, prefix="Ø"),
            DimensionCallout("TOTAL_H", 1.760, 0.002, -0.002, decimals=3),
            DimensionCallout("GAP_12", 0.900, 0.002, -0.002, decimals=3),
            DimensionCallout("GAP_23", 0.400, 0.002, -0.002, decimals=3),
            DimensionCallout("ARCHB_WD", 0.250, 0.005, -0.005, decimals=3),
            DimensionCallout("LENS_BORE_D", 0.300, 0.00005, -0.00005, prefix="Ø", decimals=4),
            DimensionCallout("PITCH", 0.500, 0.0001, -0.0001, decimals=4),
        ),
        gdt_frames=(
            GDTFrame("circularity", 0.00005, datum_primary="", feature_note="3072 LENS APERTURES"),
            GDTFrame("concentricity", 0.0005, diameter_zone=True, datum_primary="B", feature_note="3-WAFER BOND STACK"),
            GDTFrame("parallelism", 0.001, datum_primary="A", feature_note="WAFER FACES"),
        ),
        scad_params=(
            ("nx", 32),
            ("ny", 32),
            ("pitch_mm", 0.50),
            ("hole_d_mm", 0.30),
            ("e1_t_mm", 0.100),
            ("gap12_mm", 0.900),
            ("e2_t_mm", 0.160),
            ("gap23_mm", 0.400),
            ("e3_t_mm", 0.100),
            ("stack_h_mm", 1.760),
            ("wd_mm", 0.250),
            ("v_e1_V", -5000.0),
            ("v_e2_focus_V", 3734.61),
            ("v_e3_V", 0.0),
            ("e_gap_MV_m", 9.71),
            ("focus_error_um", 0.005),
        ),
        notes=(
            "Exp124 Arch-B breakdown-safe 3-wafer retarding mini-lens (E1=0.10, gap12=0.90, E2=0.16, gap23=0.40, E3=0.10, WD=0.250 mm; E_gap=9.71 MV/m < 10 MV/m, focus_error=0.005 um @ V_E2=+3734.6 V)",
        ),
        target_mass_kg=0.011,
    )
    f_s2301 = (
        ScadFeature("add_cylinder", {"d": 60.0, "h": 0.100}, translate=(0.0, 0.0, -0.830), comment="Wafer 1 (E3): 0 V ground immersion electrode (t=0.100 mm)"),
        ScadFeature("add_tube", {"od": 58.0, "id": 28.0, "h": 0.396}, translate=(0.0, 0.0, -0.580), comment="Pyrex/SiO2 anodic bond spacer 1 (gap23=0.400 mm, 9.34 MV/m)"),
        ScadFeature("add_cylinder", {"d": 60.0, "h": 0.160}, translate=(0.0, 0.0, -0.300), comment="Wafer 2 (E2): +3734.6 V focus electrode (t=0.160 mm)"),
        ScadFeature("add_tube", {"od": 58.0, "id": 28.0, "h": 0.896}, translate=(0.0, 0.0, 0.230), comment="Pyrex/SiO2 anodic bond spacer 2 (gap12=0.900 mm, 9.71 MV/m < 10 MV/m)"),
        ScadFeature("add_cylinder", {"d": 60.0, "h": 0.100}, translate=(0.0, 0.0, 0.730), comment="Wafer 3 (E1): -5000 V entrance electrode (t=0.100 mm)"),
        ScadFeature("add_tube", {"od": 60.0, "id": 28.0, "h": 0.098}, translate=(0.0, 0.0, 0.831), comment="Upper field-free entrance seating rim"),
        ScadFeature("cut_grid_holes", {"nx": 32, "ny": 32, "pitch_x": 0.50, "pitch_y": 0.50, "hole_d": 0.30, "h": 2.20}, comment="32x32 = 1,024 D=0.30 mm Arch-B lens bores"),
    )
    parts["S2.3-01"] = BuiltPart(
        d_s2301, m_s2301, f_s2301,
        {"wd_stack": checks["archB_wd_tolerance_stack"], "lateral_registration": checks["mems_32x32_lateral_registration"]},
    )

    # -----------------------------------------------------------------------
    # S2.3-03: Precision Sapphire/AlN/Zerodur Spacer Rings, Dowel Pins & Full-Stack Tie-Rods
    #          Bridges S2.3-01..S2.1-03 mechanically to S2.1-04 (Z=[0.250, 10.180] @ R=31.2 mm)!
    # -----------------------------------------------------------------------
    dowel_holes = [circle_2d(24.0, segments=64, ccw=False)]
    for k in range(6):
        ang = math.radians(k * 60.0)
        dowel_holes.append(
            circle_2d(1.1, cx=26.75 * math.cos(ang), cy=26.75 * math.sin(ang), segments=20, ccw=False)
        )
    sp_ring = make_plate_with_holes(
        circle_2d(29.5, segments=64, ccw=True),
        holes_2d=dowel_holes,
        thickness=0.500,
        axis="z",
        center=(0.0, 0.0, 2.510),
        name="S2.3-03_sapphire_spacer",
        material="Sapphire",
    )
    s2303_parts: list[SolidMesh] = [sp_ring]
    # 3x precision lapped Zerodur optical-axis dowel alignment pins cleanly seated inside alternating bores
    for k in range(3):
        ang = math.radians(k * 120.0)
        s2303_parts.append(
            make_cylinder(
                0.85, 0.480, segments=16, axis="z",
                center=(26.75 * math.cos(ang), 26.75 * math.sin(ang), 2.510),
                name=f"S2.3-03_dowel_pin_{k}", material="Zerodur",
            )
        )
    # 3x full-stack kinematic Sapphire/Ti structural standoff tie-rods @ R=31.2 mm (0/120/240 deg, Z=[0.250, 10.180])
    # Ø1.10 mm (r=0.55 mm) provides >=0.65 mm radial clearance to S2.3-01 (R=30.0) & >=0.21 mm clearance to S3.1-04 (R_in=32.0).
    # Anchors S2.3-01/S2.2-04/S2.2-01/S2.2-03/S2.1-01/S2.1-03 directly to S2.1-04 cassette (eliminating floating S2 stack!)
    for k in range(3):
        ang = math.radians(k * 120.0)
        tx, ty = 31.2 * math.cos(ang), 31.2 * math.sin(ang)
        s2303_parts.append(
            make_cylinder(
                0.55, 9.930, segments=16, axis="z",
                center=(tx, ty, 5.215),
                name=f"S2.3-03_stack_tierod_{k}", material="Sapphire",
            )
        )
    m_s2303 = merge_solids(s2303_parts, name="S2.3-03", material="Sapphire")
    d_s2303 = make_part_design_from_bom(
        "S2.3-03",
        design_tier="CUSTOM_FULL",
        material="Sapphire",
        surface_finish_ra_um=0.05,
        world_origin_mm=(0.0, 0.0, 5.215),
        ports=(
            PortInterface("spacer_bot_to_lens", "mechanical", (0.0, 0.0, 2.260), (0.0, 0.0, -1.0), "6 kV Lapped Sapphire", mating_part_id="S2.3-01", bore_mm=48.0, od_mm=59.0, pcd_mm=53.5, bolt_count=6, bolt_hole_mm=2.2, frame="global"),
            PortInterface("spacer_top_to_stop", "mechanical", (0.0, 0.0, 2.760), (0.0, 0.0, 1.0), "6 kV Lapped Sapphire", mating_part_id="S2.2-04", bore_mm=48.0, od_mm=59.0, pcd_mm=53.5, bolt_count=6, bolt_hole_mm=2.2, frame="global"),
            PortInterface("stack_tierods_to_cassette", "mechanical", (0.0, 0.0, 10.180), (0.0, 0.0, 1.0), "3x Sapphire Tie-Rods @ PCD 62.4", mating_part_id="S2.1-04", pcd_mm=62.4, bolt_count=3, bolt_hole_mm=1.1, frame="global"),
        ),
        dimensions=(
            DimensionCallout("OD", 59.0, 0.01, -0.01, prefix="Ø"),
            DimensionCallout("ID", 48.0, 0.01, -0.01, prefix="Ø"),
            DimensionCallout("THICK", 0.500, 0.0005, -0.0005, decimals=4),
            DimensionCallout("DOWEL_PCD", 53.5, 0.002, -0.002, prefix="Ø", decimals=3),
            DimensionCallout("TIEROD_L", 9.930, 0.01, -0.01, decimals=3),
        ),
        gdt_frames=(
            GDTFrame("parallelism", 0.0005, datum_primary="A", feature_note="LAPPED SPACER FACES"),
            GDTFrame("flatness", 0.0003, datum_primary="", feature_note="SAPPHIRE DATUM A"),
            GDTFrame("position", 0.0005, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="OPTICAL DOWEL PINS & TIE-RODS"),
        ),
        scad_params=(("od", 59.0), ("id", 48.0), ("thickness", 0.500), ("tierod_pcd", 62.4), ("tierod_d", 1.1), ("tierod_h", 9.930), ("hv_standoff_kV", 6.0)),
        notes=("Precision-lapped sapphire 6 kV HV spacer ring + 3x Zerodur dowel pins + 3x full-stack kinematic Ø1.10 mm sapphire tie-rods (R=31.2 mm, Z=[0.25, 10.18] mm, clearing S3.1-04 R_in=32.0 mm) mechanically anchoring the S2 optical stack to S2.1-04",),
        target_mass_kg=0.003,
    )
    f_s2303 = (
        ScadFeature("add_tube", {"od": 59.0, "id": 48.0, "h": 0.500}, translate=(0.0, 0.0, -2.705), comment="Lapped sapphire 6 kV insulator ring"),
        ScadFeature("cut_bolt_circle", {"pcd": 53.5, "bolt_d": 2.2, "count": 6, "h": 2.0}, translate=(0.0, 0.0, -2.705), comment="6x precision dowel registration bores"),
        ScadFeature("add_cylinder", {"d": 1.1, "h": 9.930}, translate=(31.2, 0.0, 0.0), comment="Full-stack sapphire structural tie-rod #1"),
        ScadFeature("add_cylinder", {"d": 1.1, "h": 9.930}, translate=(-15.6, 27.02, 0.0), comment="Full-stack sapphire structural tie-rod #2"),
        ScadFeature("add_cylinder", {"d": 1.1, "h": 9.930}, translate=(-15.6, -27.02, 0.0), comment="Full-stack sapphire structural tie-rod #3"),
    )
    parts["S2.3-03"] = BuiltPart(
        d_s2303, m_s2303, f_s2303,
        {"wd_stack": checks["archB_wd_tolerance_stack"], "lateral_registration": checks["mems_32x32_lateral_registration"]},
    )

    # -----------------------------------------------------------------------
    # S2.3-04: Multi-Channel Ultra-Stable Mini-Lens HV Focus PSU (±6.0 kV, 1U Rack Bay 1, U30)
    # -----------------------------------------------------------------------
    m_s2304, f_s2304, o_s2304 = make_rack_unit_chassis(
        u_start=30,
        u_height=1,
        rear_boss_count=3,
        internal_modules=3,
        material="Al 6061",
        name="S2.3-04",
    )
    d_s2304 = make_part_design_from_bom(
        "S2.3-04",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        surface_finish_ra_um=1.6,
        world_origin_mm=o_s2304,
        ports=(
            PortInterface("hv_rail1_out", "electrical", (o_s2304[0] - 70.0, RACK_BAY1_FRONT_Y + 442.5, o_s2304[2]), (0.0, 1.0, 0.0), "SHV-10 ±6 kV Liner (-5.000 kV E1)", mating_part_id="S2.3-01", od_mm=14.0, frame="global"),
            PortInterface("hv_rail2_out", "electrical", (o_s2304[0], RACK_BAY1_FRONT_Y + 442.5, o_s2304[2]), (0.0, 1.0, 0.0), "SHV-10 ±6 kV Focus (+3.735 kV E2)", mating_part_id="S2.3-01", od_mm=14.0, frame="global"),
            PortInterface("hv_rail3_out", "electrical", (o_s2304[0] + 70.0, RACK_BAY1_FRONT_Y + 442.5, o_s2304[2]), (0.0, 1.0, 0.0), "SHV-10 ±6 kV Guard (0 V E3)", mating_part_id="S2.3-01", od_mm=14.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("RACK_W_X", 482.6, 0.3, -0.3),
            DimensionCallout("HEIGHT_1U", 42.45, 0.3, -0.3),
            DimensionCallout("V_RANGE", 6.0, 0.0, 0.0, unit="kV", prefix="±", suffix=" kV"),
            DimensionCallout("STABILITY", 5.0, 0.0, -5.0, unit="ppm", suffix=" ppm"),
        ),
        gdt_frames=(GDTFrame("perpendicularity", 0.25, datum_primary="A", feature_note="19-IN EARS"),),
        scad_params=(("rack_u", 1), ("u_slot", "U30"), ("rails", 3), ("v_rail_kV", 6.0), ("v_e1_nom_kV", -5.000), ("v_e2_nom_kV", 3.7346), ("ripple_mVpp", 2.0)),
        notes=("19-in Rack Bay 1 slot U30 (X=1480.0, front -Y @ -438.0, Z_nat=[880.05, 922.50]); upgraded 3-rail ±6.0 kV (>=±5 kV) <5 ppm <2 mVpp Arch-B mini-lens HV focus PSU",),
        target_mass_kg=5.40,
    )
    parts["S2.3-04"] = BuiltPart(d_s2304, m_s2304, tuple(f_s2304), {})

    # -----------------------------------------------------------------------
    # S2.4-01: 16x SKY130 64-ch Blanker Driver ASIC Die Packages (R=48.0 mm ring, Z=[5.40, 6.25])
    # -----------------------------------------------------------------------
    s2401_parts: list[SolidMesh] = []
    r_tiles = 48.0
    for k in range(16):
        ang_deg = k * 22.5 + 11.25
        ang = math.radians(ang_deg)
        tx, ty = r_tiles * math.cos(ang), r_tiles * math.sin(ang)
        # AlN micro-QFN substrate + SKY130 CMOS die package (6.0 x 6.0 x 0.85 mm -> R ∈ [43.75, 52.25])
        pkg = transform_mesh(
            make_chamfered_box(6.0, 6.0, 0.85, chamfer=0.15, name=f"S2.4-01_tile_{k + 1:02d}", material="Si"),
            rotation_deg=(0.0, 0.0, ang_deg),
            translation=(tx, ty, 5.825),
        )
        s2401_parts.append(pkg)
    m_s2401 = merge_solids(s2401_parts, name="S2.4-01", material="Si")
    d_s2401 = make_part_design_from_bom(
        "S2.4-01",
        design_tier="CUSTOM_FULL",
        material="Si",
        temp_k=300.0,
        surface_finish_ra_um=0.1,
        world_origin_mm=(0.0, 0.0, 5.825),
        ports=(
            PortInterface("tile_solder_pad_ring", "electrical", (0.0, 0.0, 5.400), (0.0, 0.0, -1.0), "16x64-ch SKY130 BGA", mating_part_id="S2.4-02", bore_mm=87.5, od_mm=104.5, pcd_mm=96.0, bolt_count=16, frame="global"),
        ),
        dimensions=(
            DimensionCallout("TILE_PCD", 96.0, 0.05, -0.05, prefix="Ø"),
            DimensionCallout("PKG_XY", 6.00, 0.05, -0.05),
            DimensionCallout("PKG_H", 0.85, 0.03, -0.03),
        ),
        gdt_frames=(
            GDTFrame("position", 0.050, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="16 ACTIVE ASIC TILES"),
            GDTFrame("flatness", 0.015, datum_primary="", feature_note="BGA COPLANARITY"),
        ),
        scad_params=(("active_tiles", 16), ("spare_tiles", 8), ("ch_per_tile", 64), ("tile_pcd", 96.0), ("pkg_xy", 6.0)),
        notes=("16 active 64-ch SKY130 130 nm CMOS blanker_tile ASIC packages (1,024 ch total; +8 spares in BOM); WNS +7.21 ns, DRC=0, LVS=MATCH",),
        target_mass_kg=0.0012,
    )
    f_s2401 = tuple(
        ScadFeature(
            "add_box",
            {"dx": 6.0, "dy": 6.0, "dz": 0.85},
            translate=(r_tiles * math.cos(math.radians(k * 22.5 + 11.25)), r_tiles * math.sin(math.radians(k * 22.5 + 11.25)), 0.0),
            rotate=(0.0, 0.0, k * 22.5 + 11.25),
            comment=f"SKY130 tile #{k + 1}" if k == 0 else "",
        )
        for k in range(16)
    )
    parts["S2.4-01"] = BuiltPart(d_s2401, m_s2401, f_s2401, {})

    # -----------------------------------------------------------------------
    # S2.4-02: 4-Quadrant Modular UHV Carrier PCB Motherboard + HV-Isolated AlN/OFHC Cu Thermal Straps
    #          (R=[33.5, 64.0], Z=[2.75, 5.15] PCB; 4x AlN/OFHC thermal straps @ 45/135/225/315 deg, Z=[5.25, 9.25])
    # -----------------------------------------------------------------------
    s2402_parts: list[SolidMesh] = []
    for q in range(4):
        d0 = q * 90.0 + 3.0
        d1 = (q + 1) * 90.0 - 3.0
        outer_poly = _arc_sector_polygon_2d(33.5, 64.0, d0, d1, n_arc=16)
        # 3 mounting holes per quadrant at R=59.0 mm (PCD=118.0 mm)
        holes = []
        for deg in (d0 + 14.0, 0.5 * (d0 + d1), d1 - 14.0):
            ar = math.radians(deg)
            holes.append(circle_2d(1.6, cx=59.0 * math.cos(ar), cy=59.0 * math.sin(ar), segments=12, ccw=False))
        q_mesh = make_plate_with_holes(
            outer_poly, holes_2d=holes, thickness=2.40, axis="z", center=(0.0, 0.0, 3.950),
            name=f"S2.4-02_pcb_quad_{q + 1}", material="Rogers",
        )
        s2402_parts.append(q_mesh)
        # HV-isolated (>15 kV) AlN ceramic thermal block + OFHC Cu UHV heat-spreader strap clearing 0.5-4.43 W blanker heat
        ang_mid = q * 90.0 + 45.0
        ar_mid = math.radians(ang_mid)
        aln_blk = transform_mesh(
            make_chamfered_box(6.0, 8.0, 1.80, chamfer=0.25, name=f"S2.4-02_aln_hv_isolator_{q + 1}", material="AlN"),
            rotation_deg=(0.0, 0.0, ang_mid),
            translation=(58.5 * math.cos(ar_mid), 58.5 * math.sin(ar_mid), 6.15),
        )
        cu_strap = transform_mesh(
            make_chamfered_box(6.0, 8.0, 2.00, chamfer=0.25, name=f"S2.4-02_ofhc_thermal_strap_{q + 1}", material="OFHC Cu"),
            rotation_deg=(0.0, 0.0, ang_mid),
            translation=(58.5 * math.cos(ar_mid), 58.5 * math.sin(ar_mid), 8.20),
        )
        s2402_parts.extend([aln_blk, cu_strap])
    m_s2402 = merge_solids(s2402_parts, name="S2.4-02", material="Rogers")
    d_s2402 = make_part_design_from_bom(
        "S2.4-02",
        design_tier="CUSTOM_FULL",
        material="Rogers",
        surface_finish_ra_um=0.8,
        world_origin_mm=(0.0, 0.0, 3.950),
        ports=(
            PortInterface("asic_mount_top", "electrical", (0.0, 0.0, 5.150), (0.0, 0.0, 1.0), "4x4 SKY130 Tile Sites", mating_part_id="S2.4-01", bore_mm=67.0, od_mm=128.0, pcd_mm=118.0, bolt_count=12, bolt_hole_mm=3.2, frame="global"),
            PortInterface("kapton_flex_edge", "electrical", (64.0, 0.0, 3.950), (1.0, 0.0, 0.0), "50 Ohm UHV Flex Header", mating_part_id="S2.4-03", od_mm=128.0, frame="global"),
            PortInterface("uhv_aln_cu_thermal_strap", "thermal", (58.5 * math.cos(math.radians(45.0)), 58.5 * math.sin(math.radians(45.0)), 9.20), (0.0, 0.0, 1.0), "4x AlN/OFHC Cu 15 kV Thermal Straps (2.2 K/W)", mating_part_id="S2.1-04", frame="global"),
        ),
        dimensions=(
            DimensionCallout("PCB_OD", 128.0, 0.10, -0.10, prefix="Ø"),
            DimensionCallout("PCB_ID", 67.0, 0.10, -0.10, prefix="Ø"),
            DimensionCallout("THICK", 2.40, 0.05, -0.05),
            DimensionCallout("QUADRANTS", 4.0, 0.0, 0.0, unit="pcs", decimals=0),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.050, datum_primary="", feature_note="UHV ROGERS RO4350B PCB"),
            GDTFrame("position", 0.050, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="12X MOUNT HOLES"),
        ),
        scad_params=(
            ("pcb_od", 128.0),
            ("pcb_id", 67.0),
            ("thickness", 2.40),
            ("quadrants", 4),
            ("z0_ohm", 50.0),
            ("rogers_cte_ppm_k", 12.0),
            ("rogers_tg_c", 280.0),
            ("r_th_strap_k_per_w", 2.20),
            ("hv_strap_rating_kV", 15.0),
        ),
        notes=(
            "4-quadrant modular UHV Rogers RO4350B carrier PCB (CTE=12 ppm/K, Tg=280 C >> 150 C bakeout; +99.8 um outer exp -> 1.90 mm clear of S6.2-02 bridge)",
            "Includes 4x HV-isolated AlN (180 W/mK, 15 kV) + OFHC Cu UHV thermal straps (R_th=2.20 K/W -> dT=1.1 K @ 0.5 W nom, 9.7 K @ 4.43 W burst)",
        ),
        target_mass_kg=0.052,
    )
    f_s2402 = (
        ScadFeature("add_tube", {"od": 128.0, "id": 67.0, "h": 2.40}, comment="4-quadrant modular UHV Rogers RO4350B blanker PCB"),
        ScadFeature("cut_slot", {"length": 132.0, "width": 3.5, "h": 5.0}, comment="X-axis inter-quadrant thermal split"),
        ScadFeature("cut_slot", {"length": 132.0, "width": 3.5, "h": 5.0}, rotate=(0.0, 0.0, 90.0), comment="Y-axis inter-quadrant thermal split"),
        ScadFeature("cut_bolt_circle", {"pcd": 118.0, "bolt_d": 3.2, "count": 12, "h": 5.0}, comment="12xM3 quadrant mounting holes"),
        ScadFeature("add_box", {"dx": 6.0, "dy": 8.0, "dz": 3.8}, translate=(41.37, 41.37, 3.25), rotate=(0.0, 0.0, 45.0), comment="Q1 AlN/OFHC Cu UHV HV-isolated thermal strap"),
    )
    parts["S2.4-02"] = BuiltPart(
        d_s2402,
        m_s2402,
        f_s2402,
        {
            "bakeout_pcb_clearance": checks["bakeout_pcb_blanker_clearance"],
            "uhv_thermal_closure": checks["blanker_uhv_thermal_closure"],
        },
    )

    # -----------------------------------------------------------------------
    # S2.4-03: 2x CF100 High-Pin Hermetic Feedthroughs & Kapton Flex Looms ((±235, +235, 175))
    # -----------------------------------------------------------------------
    s2403_parts: list[SolidMesh] = []
    for sgn in (-1.0, 1.0):
        fx, fy, fz = sgn * 235.0, 235.0, 175.0
        tag = "pos_x" if sgn > 0 else "neg_x"
        # True ISO 3669 CF100 feedthrough flange (OD=152 mm, 16xØ8.4 @ PCD 130.2, knife-edge -Z)
        cf100 = make_cf_flange(
            "CF100", bore_id=88.0, axis="-z", center=(fx, fy, fz),
            name=f"S2.4-03_cf100_{tag}", material="316LN",
        )
        # Solid vacuum seal weld plate spanning bore (Z ∈ [174.5, 184.5], R=43.8 -> zero overlap w/ bore=44.0!)
        seal_disk = make_cylinder(
            43.6, 8.0, segments=40, axis="z", center=(fx, fy, fz + 5.5),
            name=f"S2.4-03_seal_plate_{tag}", material="316LN",
        )
        s2403_parts.extend([cf100, seal_disk])
        # 4x high-density hermetic ceramic-pin 68-pin D-sub connector barrels atop seal plate (Z ∈ [190, 215])
        for dx_o, dy_o in ((-18.0, -16.0), (18.0, -16.0), (18.0, 16.0), (-18.0, 16.0)):
            s2403_parts.append(
                make_chamfered_box(
                    26.0, 14.0, 24.5, chamfer=1.0,
                    center=(fx + dx_o, fy + dy_o, fz + 27.5),
                    name=f"S2.4-03_dsub_{tag}", material="Al2O3",
                )
            )
        # 2x swept UHV Kapton flex ribbon conduits routing cleanly downward inside CF100 bore shadow (Z ∈ [115, 164.5])
        for dy_r in (-14.0, 14.0):
            spine = [
                [fx, fy + dy_r, fz - 10.5],
                [fx - sgn * 8.0, fy + dy_r, fz - 34.0],
                [fx - sgn * 18.0, fy + dy_r - 6.0, fz - 60.0],
            ]
            s2403_parts.append(
                make_swept_tube(spine, r_out=5.2, r_in=0.0, segments=16, name=f"S2.4-03_kapton_loom_{tag}", material="Vespel SP-22")
            )
    m_s2403 = merge_solids(s2403_parts, name="S2.4-03", material="316LN")
    d_s2403 = make_part_design_from_bom(
        "S2.4-03",
        design_tier="COTS_ENV_ICD",
        material="316LN",
        surface_finish_ra_um=0.8,
        world_origin_mm=(0.0, 235.0, 175.0),
        ports=(
            make_cf_port_interface("CF100", "feedthrough_ne_cf100", (235.0, 235.0, 165.10), (0.0, 0.0, -1.0), bore_override_mm=88.0, frame="global"),
            make_cf_port_interface("CF100", "feedthrough_nw_cf100", (-235.0, 235.0, 165.10), (0.0, 0.0, -1.0), bore_override_mm=88.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("FLANGE_CF100", 152.0, 0.10, -0.10, prefix="Ø"),
            DimensionCallout("PORT_SPAN_X", 470.0, 0.5, -0.5),
            DimensionCallout("SIGNAL_LINES", 256.0, 0.0, 0.0, unit="ch", decimals=0),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.050, datum_primary="A", feature_note="CF100 KNIFE-EDGE"),
            GDTFrame("flatness", 0.025, datum_primary="", feature_note="HERMETIC SEAL FACE"),
        ),
        scad_params=(("cf_size", "CF100"), ("qty_flanges", 2), ("signal_pins", 256), ("bakeout_C", 150.0)),
        notes=("2x ISO 3669 CF100 high-pin hermetic ceramic feedthroughs (256+ lines, He<=1e-9, 150 C bakeout) + Kapton UHV flex looms at (±235, +235, 175)",),
        target_mass_kg=5.60,
    )
    f_s2403 = (
        ScadFeature("add_cf_flange", {"size": "CF100", "bore_id": 88.0}, translate=(235.0, 0.0, 0.0), rotate=(180.0, 0.0, 0.0), comment="+X CF100 128-pin hermetic feedthrough"),
        ScadFeature("add_cf_flange", {"size": "CF100", "bore_id": 88.0}, translate=(-235.0, 0.0, 0.0), rotate=(180.0, 0.0, 0.0), comment="-X CF100 128-pin hermetic feedthrough"),
        ScadFeature("add_box", {"dx": 64.0, "dy": 48.0, "dz": 24.5}, translate=(235.0, 0.0, 27.5), comment="+X 4x68-pin ceramic D-sub cluster"),
        ScadFeature("add_box", {"dx": 64.0, "dy": 48.0, "dz": 24.5}, translate=(-235.0, 0.0, 27.5), comment="-X 4x68-pin ceramic D-sub cluster"),
    )
    parts["S2.4-03"] = BuiltPart(d_s2403, m_s2403, f_s2403, {})

    # -----------------------------------------------------------------------
    # S2.5-01: 3-Axis Head-to-Stage Capacitive Position Sensors (R=57.5, 60°/180°/300°, Z=[12, 28])
    # -----------------------------------------------------------------------
    s2501_parts: list[SolidMesh] = []
    for idx, deg in enumerate((60.0, 180.0, 300.0)):
        ar = math.radians(deg)
        px, py = 57.5 * math.cos(ar), 57.5 * math.sin(ar)
        # Cylindrical Invar-36 probe barrel (Ø9.0 x 13.0 mm, Z ∈ [14.0, 27.0])
        s2501_parts.append(
            make_cylinder(4.5, 13.0, segments=24, axis="z", center=(px, py, 20.5), name=f"S2.5-01_probe_{idx + 1}", material="Invar-36")
        )
        # Gold capacitive sensing guard tip facing wafer/stage below (Z ∈ [12.0, 13.8])
        s2501_parts.append(
            make_cylinder(4.0, 1.8, segments=24, axis="z", center=(px, py, 12.9), name=f"S2.5-01_au_tip_{idx + 1}", material="Au")
        )
        # Clamping bracket collar atop probe (Z ∈ [27.2, 28.0])
        s2501_parts.append(
            make_tube(2.2, 5.0, 0.8, segments=20, axis="z", center=(px, py, 27.6), name=f"S2.5-01_clamp_{idx + 1}", material="Invar-36")
        )
    m_s2501 = merge_solids(s2501_parts, name="S2.5-01", material="Invar-36")
    d_s2501 = make_part_design_from_bom(
        "S2.5-01",
        design_tier="COTS_ENV_ICD",
        material="Invar-36",
        surface_finish_ra_um=0.2,
        world_origin_mm=(0.0, 0.0, 20.0),
        ports=(
            PortInterface("cap_probe_1", "electrical", (57.5 * math.cos(math.radians(60.0)), 57.5 * math.sin(math.radians(60.0)), 28.0), (0.0, 0.0, 1.0), "Triax Cap Probe #1", od_mm=9.0, frame="global"),
            PortInterface("cap_probe_2", "electrical", (-57.5, 0.0, 28.0), (0.0, 0.0, 1.0), "Triax Cap Probe #2", od_mm=9.0, frame="global"),
            PortInterface("cap_probe_3", "electrical", (57.5 * math.cos(math.radians(300.0)), 57.5 * math.sin(math.radians(300.0)), 28.0), (0.0, 0.0, 1.0), "Triax Cap Probe #3", od_mm=9.0, frame="global"),
        ),
        dimensions=(
            DimensionCallout("PROBE_PCD", 115.0, 0.02, -0.02, prefix="Ø"),
            DimensionCallout("PROBE_OD", 9.0, 0.01, -0.01, prefix="Ø"),
            DimensionCallout("PROBE_L", 16.0, 0.05, -0.05),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.005, datum_primary="A", feature_note="AU ELECTRODE FACE"),
            GDTFrame("position", 0.020, diameter_zone=True, datum_primary="A", datum_secondary="B", feature_note="3X 120 DEG PROBES"),
        ),
        scad_params=(("probe_pcd", 115.0), ("probe_od", 9.0), ("rms_res_nm", 0.1), ("bw_kHz", 10.0)),
        notes=("3-axis head-to-stage relative capacitive sensors (PI/Lion class, <=0.1 nm RMS, 10 kHz) at R=57.5 mm (60/180/300 deg); clears 0/90/270 deg interferometer axes",),
        target_mass_kg=0.024,
    )
    f_s2501 = tuple(
        ScadFeature(
            "add_cylinder",
            {"d": 9.0, "h": 16.0},
            translate=(57.5 * math.cos(math.radians(deg)), 57.5 * math.sin(math.radians(deg)), 0.0),
            comment=f"Capacitive sensor probe #{i + 1} ({int(deg)} deg)",
        )
        for i, deg in enumerate((60.0, 180.0, 300.0))
    )
    parts["S2.5-01"] = BuiltPart(d_s2501, m_s2501, f_s2501, {})

    # -----------------------------------------------------------------------
    # S2.5-02: Invar-36 3-DOF Kinematic Piezo Tip/Tilt/Z Head Mount (Z=[31.910, 39.410])
    # -----------------------------------------------------------------------
    fl_bot = make_ring_with_bolt_circle(
        14.0, 52.0, 2.20, pcd=92.0, n_bolts=12, bolt_diameter=4.5, sub_per_side=2,
        axis="z", center=(0.0, 0.0, 33.010), name="S2.5-02_invar_lower", material="Invar-36",
    )
    fl_top = make_ring_with_bolt_circle(
        14.0, 52.0, 2.20, pcd=92.0, n_bolts=12, bolt_diameter=4.5, sub_per_side=2,
        axis="z", center=(0.0, 0.0, 38.310), name="S2.5-02_invar_upper", material="Invar-36",
    )
    s2502_parts: list[SolidMesh] = [fl_bot, fl_top]
    # 3x UHV piezo-stack actuators at 60/180/300 deg (R=38.0 mm, Z ∈ [34.12, 37.20], closed contact to flanges)
    for idx, deg in enumerate((60.0, 180.0, 300.0)):
        ar = math.radians(deg)
        s2502_parts.append(
            make_cylinder(5.5, 3.08, segments=24, axis="z", center=(38.0 * math.cos(ar), 38.0 * math.sin(ar), 35.660), name=f"S2.5-02_piezo_act_{idx + 1}", material="Al2O3")
        )
    # 3x Ti-6Al-4V stiff preload flexure struts at 0/120/240 deg (R=38.0 mm, Z ∈ [34.12, 37.20])
    for idx, deg in enumerate((0.0, 120.0, 240.0)):
        ar = math.radians(deg)
        s2502_parts.append(
            make_cylinder(3.2, 3.08, segments=18, axis="z", center=(38.0 * math.cos(ar), 38.0 * math.sin(ar), 35.660), name=f"S2.5-02_flex_strut_{idx + 1}", material="Ti-6Al-4V")
        )
    m_s2502 = merge_solids(s2502_parts, name="S2.5-02", material="Invar-36")
    d_s2502 = make_part_design_from_bom(
        "S2.5-02",
        design_tier="CUSTOM_FULL",
        material="Invar-36",
        surface_finish_ra_um=0.2,
        world_origin_mm=(0.0, 0.0, 35.660),
        ports=(
            PortInterface("head_mate_bot", "mechanical", (0.0, 0.0, 31.910), (0.0, 0.0, -1.0), "12xM4 PCD 92", mating_part_id="S2.1-04", bore_mm=28.0, od_mm=104.0, pcd_mm=92.0, bolt_count=12, bolt_hole_mm=4.5, frame="global"),
            PortInterface("column_mate_top", "mechanical", (0.0, 0.0, 39.410), (0.0, 0.0, 1.0), "12xM4 PCD 92", mating_part_id="S1.3-02", bore_mm=28.0, od_mm=104.0, pcd_mm=92.0, bolt_count=12, bolt_hole_mm=4.5, frame="global"),
        ),
        dimensions=(
            DimensionCallout("OD", 104.0, 0.02, -0.02, prefix="Ø"),
            DimensionCallout("CLEAR_BORE", 28.0, 0.01, -0.01, prefix="Ø"),
            DimensionCallout("STACK_H", 7.50, 0.005, -0.005),
            DimensionCallout("Z_STROKE", 0.100, 0.001, -0.001, prefix="±", decimals=3),
        ),
        gdt_frames=(
            GDTFrame("parallelism", 0.002, datum_primary="A", feature_note="KINEMATIC PLANES"),
            GDTFrame("flatness", 0.002, datum_primary="", feature_note="INVAR-36 DATUM A"),
            GDTFrame("concentricity", 0.005, diameter_zone=True, datum_primary="B", feature_note="Ø28 OPTICAL AXIS"),
        ),
        scad_params=(("od", 104.0), ("bore_id", 28.0), ("height", 7.50), ("tip_tilt_mrad", 1.0), ("z_stroke_um", 100.0), ("f1_axial_kHz", 18.34), ("f1_lateral_kHz", 51.87)),
        notes=(
            "Invar-36 3-DOF kinematic piezo tip/tilt/Z head alignment mount (tip/tilt ±1 mrad, Z ±100 um; macro head-mount modal f1_axial=18.34 kHz, f1_lateral=51.87 kHz for m_head=0.73 kg — distinct from S2.2-01 single Si membrane mode 2.591 MHz)",
        ),
        target_mass_kg=0.28,
    )
    f_s2502 = (
        ScadFeature("add_tube", {"od": 104.0, "id": 28.0, "h": 2.20}, translate=(0.0, 0.0, -2.65), comment="Lower Invar-36 kinematic flange"),
        ScadFeature("add_tube", {"od": 104.0, "id": 28.0, "h": 2.20}, translate=(0.0, 0.0, 2.65), comment="Upper Invar-36 column interface flange"),
        ScadFeature("cut_bolt_circle", {"pcd": 92.0, "bolt_d": 4.5, "count": 12, "h": 12.0}, comment="12xM4 mounting bolt circle"),
    )
    parts["S2.5-02"] = BuiltPart(d_s2502, m_s2502, f_s2502, {"wd_stack": checks["archB_wd_tolerance_stack"]})

    # -----------------------------------------------------------------------
    # S2.5-03: Head Frame Zerodur Reference Optical Mirrors (R=58.0, 0/90/270 deg, Z_nat=[11.0, 17.6])
    #          Aligned directly inside Z_canon=[482, 518] mm split gap facing S4.4-02 periscope heads!
    # -----------------------------------------------------------------------
    s2503_parts: list[SolidMesh] = []
    for idx, deg in enumerate((0.0, 90.0, 270.0)):
        ar = math.radians(deg)
        mx, my = 58.0 * math.cos(ar), 58.0 * math.sin(ar)
        # Zerodur λ/20 vertical reference mirror bar (8.0 radial x 14.0 tangential x 6.6 Z -> Z_nat=[11.0, 17.6])
        mirror = transform_mesh(
            make_chamfered_box(8.0, 14.0, 6.6, chamfer=0.4, name=f"S2.5-03_zerodur_mirror_{idx + 1}", material="Zerodur"),
            rotation_deg=(0.0, 0.0, deg),
            translation=(mx, my, 14.3),
        )
        s2503_parts.append(mirror)
    m_s2503 = merge_solids(s2503_parts, name="S2.5-03", material="Zerodur")
    d_s2503 = make_part_design_from_bom(
        "S2.5-03",
        design_tier="COTS_ENV_ICD",
        material="Zerodur",
        surface_finish_ra_um=0.02,
        world_origin_mm=(0.0, 0.0, 14.3),
        ports=(
            PortInterface("interf_mirror_x", "optical", (62.0, 0.0, 14.3), (1.0, 0.0, 0.0), "λ/20 @ 632.8 nm", mating_part_id="S4.4-02", frame="global"),
            PortInterface("interf_mirror_y", "optical", (0.0, 62.0, 14.3), (0.0, 1.0, 0.0), "λ/20 @ 632.8 nm", mating_part_id="S4.4-02", frame="global"),
            PortInterface("interf_mirror_z", "optical", (0.0, -62.0, 14.3), (0.0, -1.0, 0.0), "λ/20 @ 632.8 nm", mating_part_id="S4.4-02", frame="global"),
        ),
        dimensions=(
            DimensionCallout("MIRROR_PCD", 116.0, 0.02, -0.02, prefix="Ø"),
            DimensionCallout("MIRROR_W", 14.0, 0.05, -0.05),
            DimensionCallout("MIRROR_H", 6.6, 0.05, -0.05),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.00003, datum_primary="", feature_note="LAMBDA/20 @ 632.8 NM"),
            GDTFrame("perpendicularity", 0.001, datum_primary="A", feature_note="±2 ARCSEC MIRROR FACE"),
        ),
        scad_params=(("mirror_pcd", 116.0), ("mirror_t", 8.0), ("mirror_w", 14.0), ("mirror_h", 6.6), ("z_nat_center_mm", 14.3), ("flatness_nm", 31.6)),
        notes=("3x Zerodur Al-SiO2 coated reference mirrors (λ/20 @ 632.8 nm) at R=58.0 mm (0/90/270 deg, Z_nat=[11.0, 17.6] / Z_canon=[511.0, 517.6] inside split gap) with clear normal-incidence LOS to S4.4-02",),
        target_mass_kg=0.008,
    )
    f_s2503 = tuple(
        ScadFeature(
            "add_box",
            {"dx": 8.0, "dy": 14.0, "dz": 6.6},
            translate=(58.0 * math.cos(math.radians(deg)), 58.0 * math.sin(math.radians(deg)), 0.0),
            rotate=(0.0, 0.0, deg),
            comment=f"Zerodur λ/20 reference mirror #{i + 1} ({int(deg)} deg, split-gap Z=514.3 mm)",
        )
        for i, deg in enumerate((0.0, 90.0, 270.0))
    )
    parts["S2.5-03"] = BuiltPart(d_s2503, m_s2503, f_s2503, {})

    # Verify exact 15/15 S2 physical BOM coverage (excluding non-solid fab NRE S2.1-02/S2.2-02/S2.3-02)
    expected = list_physical_part_ids("S2")
    if set(parts.keys()) != set(expected):
        missing = sorted(set(expected) - set(parts.keys()))
        extra = sorted(set(parts.keys()) - set(expected))
        raise RuntimeError(f"S2 part coverage mismatch! missing={missing}, extra={extra}")

    return {pid: parts[pid] for pid in expected}


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def export_all(out_dir: Path | str | None = None) -> dict[str, PartArtifactResult]:
    """Build and export all 15 physical S2 parts (.stl, .step, .scad, .dxf, .svg + .json manifest)."""
    dest = Path(out_dir) if out_dir is not None else S2_OUT_DIR
    dest.mkdir(parents=True, exist_ok=True)

    built = build_s2_parts()
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
        from hardware.cad_parts.core import verify_watertight as _vw
        _vr = _vw(bp.mesh)
        part_payload = {
            "part_id": pid,
            "subsystem": "S2",
            "design": bp.design.to_dict(),
            "artifact": res.to_dict(),
            "engineering_checks": bp.checks,
            "shell_mate_metadata": {
                "n_shells": _vr.n_shells,
                "fea_bonding_mode": "SINGLE_MONOLITHIC_SOLID" if _vr.n_shells == 1 else "TIED_SUBASSEMBLY_CONTACTS",
                "watertight": _vr.watertight,
            },
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
            "mass_kg": round(res.mass_kg, 6),
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
        "subsystem": "S2",
        "part_count": len(results),
        "custom_full_count": sum(1 for bp in built.values() if bp.design.design_tier == "CUSTOM_FULL"),
        "cots_env_icd_count": sum(1 for bp in built.values() if bp.design.design_tier == "COTS_ENV_ICD"),
        "all_watertight": all(r.watertight for r in results.values()),
        "all_valid": all(r.all_valid for r in results.values()),
        "total_computed_mass_kg": round(sum(r.mass_kg for r in results.values()), 5),
        "engineering_checks": compute_s2_engineering_checks(),
        "epistemic": {
            "design_maturity": DESIGN_MATURITY,
            "no_lab_measurement": NO_LAB_MEASUREMENT,
            "iec61508_certified": IEC61508_CERTIFIED,
            "semi_s2_certified": SEMI_S2_CERTIFIED,
        },
        "parts": manifest_parts,
    }
    (dest / "S2_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return results


if __name__ == "__main__":
    res = export_all()
    tot_kg = sum(r.mass_kg for r in res.values())
    ok = sum(1 for r in res.values() if r.all_valid)
    print(f"S2 exported {ok}/{len(res)} valid parts, total mass={tot_kg:.4f} kg")
