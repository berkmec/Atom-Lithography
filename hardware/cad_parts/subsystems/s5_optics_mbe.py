"""S5 Flash Anneal, 808 nm Laser Optics & In-Situ 28Si LT-MBE CAD (WP-M3).

Implements the remaining 12 of the 23 physical S5 BOM parts using the pure-Python
watertight CAD kernel (``hardware.cad_parts.core``):
- ``S5.3-01``: Backup Xe flash-lamp / RTA rapid thermal anneal head & elliptical reflector.
- ``S5.3-02``: CF100 UV-IR fused-silica optical anneal viewport & focusing mirror barrel.
- ``S5.3-03``: High-speed backup dual-band optical pyrometer & closed-loop anneal controller.
- ``S5.3-04``: Water-cooled OFHC Cu / Mo S2-head thermal shutter blade & bellows actuator.
- ``S5.5-01``: 808 nm qCW diode bar-stack + micro-channel water-cooled homogenizer head
  (84x88x84 mm core + rear fiber collimator, Exp130/139).
- ``S5.5-02``: CF63 +Y equatorial (Z=500 mm) AR-coated sapphire laser viewport
  (Dia 50x8 mm window, Dia 44 mm clear aperture, real ISO 3669 CF63 bolt circle).
- ``S5.5-03``: 45 deg dichroic beam-splitter turret + 10 us 2-color InGaAs/Si pyrometer head.
- ``S5.5-04``: Dual-coil fail-safe beam shutter (<3.2 ms, MXC <1 K & UHV interlock) at +Y
  (cleanly enclosed with >=35 mm margin inside S7.SAFETY-02 280x260x220 mm shroud).
- ``S5.6-01``: CF100 crucible-free DC 28Si rod sublimation MBE source + water/LN2 cryoshroud
  + pneumatic shutter (Exp139, 11.8 kg class, mounted on Load-Lock +Z CF100 Z=585..865 mm).
- ``S5.6-02``: Enriched 28Si feedstock rod (<50 ppm 29Si) + 6 MHz UHV QCM crystal thickness
  monitor on CF40 + isolation valve (Exp139, 3.4 kg class).
- ``S5.6-03``: Load-lock 345 C pyrolytic-BN radiative heater + 5% H2/N2 forming-gas
  sapphire-seat leak-valve passivation manifold (Exp139, 4.2 kg class).
- ``S5.6-04``: Dedicated 80 L/s compact MBE differential TMP + ZrVFe NEG cartridge package
  (Exp139, 3.0 kg class; combined S5.6 = 22.4 kg class, 0.00 uW 20 mK cryo leak).
"""
from __future__ import annotations

import math

from hardware.cad_parts.core import (
    DimensionCallout,
    GDTFrame,
    PortInterface,
    ScadFeature,
    SolidMesh,
    make_bellows,
    make_box,
    make_cf_flange,
    make_cf_port_interface,
    make_cf_viewport,
    make_cf_weld_neck,
    make_chamfered_box,
    make_cylinder,
    make_part_design_from_bom,
    make_rect_plate_with_features,
    make_revolved_profile,
    make_tube,
    merge_solids,
    transform_mesh,
)
from hardware.cad_parts.subsystems.s5_uhv_pumps import (
    LOADLOCK_CENTER_X_MM,
    LOADLOCK_OPT_ELEV_DEG,
    LOADLOCK_S53_PYRO_AZ_DEG,
    LOADLOCK_S53_PYRO_T_FACE_MM,
    LOADLOCK_S53_RTA_AZ_DEG,
    LOADLOCK_S53_RTA_T_FACE_MM,
    LOADLOCK_S55_T_FACE_MM,
    LOADLOCK_SHUTTER_AZ_DEG,
    LOADLOCK_SHUTTER_R_FACE_MM,
    LOADLOCK_SHUTTER_Z_LOC_MM,
    Z_WAFER_MM,
    S5PartBuild,
    build_s5_parts,
    export_all,
    inclined_pos,
    inclined_vec,
    make_arc_sector_solid,
    make_hollow_enclosure,
    radial_pos,
    radial_vec,
)

S56_PBN_AZ_DEG: float = 228.0
S56_PBN_Z_LOC_MM: float = 148.0

S5_OPTICS_MBE_PART_IDS: tuple[str, ...] = (
    "S5.3-01",
    "S5.3-02",
    "S5.3-03",
    "S5.3-04",
    "S5.5-01",
    "S5.5-02",
    "S5.5-03",
    "S5.5-04",
    "S5.6-01",
    "S5.6-02",
    "S5.6-03",
    "S5.6-04",
)


# ---------------------------------------------------------------------------
# S5.3 Backup Xe Flash-Lamp / RTA Anneal Optics & S2 Thermal Shutter
# ---------------------------------------------------------------------------
def _build_s5_3_01() -> S5PartBuild:
    """S5.3-01: Backup Xe Flash-Lamp / RTA Rapid Thermal Optical Anneal Head & Reflector."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # Mounts coaxially behind S5.3-02 CF100 viewport barrel along 140 deg (R = 354.5..502.5 mm)
    # Local +X extends radially outward along 140 deg!
    housing = make_hollow_enclosure(
        128.0, 126.0, 126.0, wall=8.0, open_faces=("-x",), center=(64.0, 0.0, 0.0),
        name="rta_lamp_housing", material="Al 6061",
    )
    # Cooling fins along +/-Y sides of lamp housing
    for k in range(5):
        xk = 20.0 + k * 22.0
        shells.append(make_box(6.0, 10.0, 118.0, center=(xk, -68.5, 0.0), material="Al 6061"))
        shells.append(make_box(6.0, 10.0, 118.0, center=(xk, 68.5, 0.0), material="Al 6061"))
    # Internal gold-coated parabolic/elliptical reflector shell (revolved dish facing -X)
    refl_prof = [
        (16.0, 102.0), (22.0, 102.0), (54.0, 32.0), (54.0, 12.0), (49.0, 12.0),
        (49.0, 30.0), (16.0, 96.0),
    ]
    reflector = make_revolved_profile(refl_prof, segments=32, axis="+x", name="xe_elliptical_reflector", material="Au")
    # Twin quartz Xe flash-lamp arc tubes seated inside reflector focus
    lamp_1 = make_cylinder(7.0, 92.0, segments=20, axis="z", center=(46.0, -16.0, 0.0), name="xe_flash_tube_1", material="Fused Silica")
    lamp_2 = make_cylinder(7.0, 92.0, segments=20, axis="z", center=(46.0, 16.0, 0.0), name="xe_flash_tube_2", material="Fused Silica")
    # Rear forced-air blower shroud + top HV trigger transformer box + water barbs
    fan_shroud = make_cylinder(52.0, 20.0, segments=24, axis="x", center=(138.2, 0.0, 0.0), material="Al 6061")
    hv_trigger = make_chamfered_box(68.0, 56.0, 36.0, chamfer=2.5, center=(74.0, 0.0, 81.5), name="xe_hv_trigger_box", material="Al 6061")
    cool_in = make_cylinder(6.0, 22.0, segments=12, axis="-z", center=(52.0, -28.0, -74.5), material="OFHC Cu")
    cool_out = make_cylinder(6.0, 22.0, segments=12, axis="-z", center=(52.0, 28.0, -74.5), material="OFHC Cu")

    shells.extend([housing, reflector, lamp_1, lamp_2, fan_shroud, hv_trigger, cool_in, cool_out])
    step_shells.extend([
        make_box(128.0, 147.0, 126.0, center=(64.0, 0.0, 0.0)),
        make_cylinder(52.0, 20.0, segments=16, axis="x", center=(138.2, 0.0, 0.0)),
        make_box(68.0, 56.0, 36.0, center=(74.0, 0.0, 81.5)),
    ])

    scad_feats.extend([
        ScadFeature("add_box", {"dx": 128.0, "dy": 126.0, "dz": 126.0}, translate=(64.0, 0.0, 0.0), comment="Finned Al-6061 Xe flash/RTA lamp housing"),
        ScadFeature("add_cylinder", {"d": 104.0, "h": 20.0}, translate=(138.2, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="Rear cooling blower shroud"),
        ScadFeature("add_box", {"dx": 68.0, "dy": 56.0, "dz": 36.0}, translate=(74.0, 0.0, 81.5), comment="HV Xe flash trigger transformer block"),
        ScadFeature("cut_hole", {"d": 96.0, "h": 110.0}, translate=(50.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="Elliptical optical reflector cavity"),
    ])

    mesh = merge_solids(shells, name="S5.3-01", material="Al 6061")
    step_mesh = merge_solids(step_shells, name="S5.3-01_step", material="Al 6061")
    ix, iy, iz = inclined_pos(LOADLOCK_S53_RTA_T_FACE_MM + 79.0, LOADLOCK_S53_RTA_AZ_DEG, LOADLOCK_OPT_ELEV_DEG)
    design = make_part_design_from_bom(
        "S5.3-01",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        temp_k=300.0,
        surface_finish_ra_um=1.6,
        world_origin_mm=(round(LOADLOCK_CENTER_X_MM + ix, 4), round(iy, 4), round(Z_WAFER_MM + iz, 4)),
        world_rotation_deg=(0.0, -LOADLOCK_OPT_ELEV_DEG, LOADLOCK_S53_RTA_AZ_DEG),
        ports=(
            PortInterface("optical_exit_aperture", "optical", (0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), "Dia 96 mm RTA Exit", mating_part_id="S5.3-02", bore_mm=96.0),
            PortInterface("coolant_in", "cooling", (52.0, -28.0, -85.5), (0.0, 0.0, -1.0), "1/4 in Swagelok DI Water"),
            PortInterface("hv_pulse_bus", "electrical", (74.0, 0.0, 99.5), (0.0, 0.0, 1.0), "3 kV Flash Pulse Bus", mating_part_id="S7.4-01"),
        ),
        dimensions=(
            DimensionCallout("HEAD_L", 148.2, 0.5, -0.5, view="top"),
            DimensionCallout("HEAD_W", 147.0, 0.5, -0.5, view="top"),
            DimensionCallout("HEAD_H", 185.0, 0.5, -0.5, view="front"),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.25, diameter_zone=True, datum_primary="B", feature_note="Elliptical reflector axis to S5.3-02 viewport"),
        ),
        notes=(
            "Backup Xe flash-lamp / RTA optical anneal head (Exp66/91, sigma_anneal <= 0.5 nm backup to S5.5 808 nm).",
            "OBS-001 fix: Relocated to 36-deg inclined 140-deg optical port on S5.1-03 load-lock aimed directly at wafer S5.4-01 (420, 0, 500) with clear Moller-Trumbore LOS.",
        ),
        scad_params=(("head_l", 148.2), ("aperture_d", 96.0), ("pulse_ms", 1.0), ("elev_deg", LOADLOCK_OPT_ELEV_DEG)),
        target_mass_kg=7.8,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=3200.0,
    )


def _build_s5_3_02() -> S5PartBuild:
    """S5.3-02: CF100 UV-IR Fused-Silica Optical Anneal Viewport & Focusing Mirror Barrel."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # Mates S5.1-01 140 deg CF100 flange (R_face=275.0 -> origin R=275.5 mm, rot_z=140 deg)
    # Local +X extends radially outward; knife-edge on -X faces chamber vacuum!
    vp = make_cf_viewport(
        "CF100", clear_aperture=88.0, window_diameter=96.0, window_thickness=10.0,
        sub_per_side=1, axis="-x", center=(9.9, 0.0, 0.0),
        name="rta_cf100_quartz_viewport", material="316LN", window_material="Fused Silica",
    )
    # External focusing mirror barrel + 3 kinematic tip-tilt micrometer adjusters (x = 20.0..78.0)
    barrel = make_tube(44.0, 58.0, 58.0, segments=36, axis="x", center=(49.0, 0.0, 0.0), name="rta_focus_barrel", material="Al 6061")
    rear_ring = make_tube(46.0, 64.0, 10.0, segments=36, axis="x", center=(73.0, 0.0, 0.0), material="Al 6061")
    shells.extend([vp, barrel, rear_ring])
    for ang_deg in (0.0, 120.0, 240.0):
        mic = transform_mesh(
            make_cylinder(5.5, 22.0, segments=12, axis="z", center=(0.0, 0.0, 65.0), material="316LN"),
            rotation_deg=(ang_deg, 0.0, 0.0),
            translation=(58.0, 0.0, 0.0),
        )
        shells.append(mic)

    step_shells.extend([
        make_cylinder(76.0, 19.8, segments=16, axis="x", center=(9.9, 0.0, 0.0)),
        make_tube(44.0, 64.0, 58.0, segments=16, axis="x", center=(49.0, 0.0, 0.0)),
    ])

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF100", "bore_id": 88.0}, translate=(9.9, 0.0, 0.0), rotate=(0.0, -90.0, 0.0), comment="ISO 3669 CF100 UV-IR fused-silica viewport flange"),
        ScadFeature("add_cylinder", {"d": 96.0, "h": 10.0}, translate=(14.9, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="UV-IR fused-silica optical window (>10 J/cm^2)"),
        ScadFeature("add_tube", {"od": 116.0, "id": 88.0, "h": 58.0}, translate=(49.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="Focusing mirror barrel & baffle"),
    ])

    mesh = merge_solids(shells, name="S5.3-02", material="316LN")
    step_mesh = merge_solids(step_shells, name="S5.3-02_step", material="316LN")
    ix, iy, iz = inclined_pos(LOADLOCK_S53_RTA_T_FACE_MM + 0.5, LOADLOCK_S53_RTA_AZ_DEG, LOADLOCK_OPT_ELEV_DEG)
    design = make_part_design_from_bom(
        "S5.3-02",
        design_tier="COTS_ENV_ICD",
        material="316LN",
        temp_k=300.0,
        surface_finish_ra_um=0.4,
        world_origin_mm=(round(LOADLOCK_CENTER_X_MM + ix, 4), round(iy, 4), round(Z_WAFER_MM + iz, 4)),
        world_rotation_deg=(0.0, -LOADLOCK_OPT_ELEV_DEG, LOADLOCK_S53_RTA_AZ_DEG),
        ports=(
            make_cf_port_interface("CF100", "chamber_cf100_mate", (0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), mating_part_id="S5.1-03", bore_override_mm=88.0),
            PortInterface("lamp_head_mount", "optical", (78.0, 0.0, 0.0), (1.0, 0.0, 0.0), "Dia 128 mm Kinematic Barrel", mating_part_id="S5.3-01", bore_mm=88.0, od_mm=128.0),
        ),
        dimensions=(
            DimensionCallout("CF100_OD", 152.0, 0.15, -0.15, prefix="Ø", view="right"),
            DimensionCallout("CLEAR_AP", 88.0, 0.10, -0.10, prefix="Ø", view="right"),
            DimensionCallout("ASSY_LEN", 78.0, 0.25, -0.25, view="top"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.015, datum_primary="", feature_note="Quartz optical window seat (lambda/4)"),
            GDTFrame("concentricity", 0.08, diameter_zone=True, datum_primary="B", feature_note="Focusing barrel to CF100 bore"),
        ),
        notes=(
            "CF100 UV-IR fused-silica optical viewport (Dia 88 mm CA, >10 J/cm^2 LIDT, lambda/4) + focusing barrel.",
            "OBS-001 fix: Mates S5.1-03 36-deg inclined 140-deg optical port with 0.5 mm Cu gasket gap and clear LOS to wafer S5.4-01.",
        ),
        scad_params=(("clear_aperture_mm", 88.0), ("window_d_mm", 96.0), ("barrel_l_mm", 58.0), ("elev_deg", LOADLOCK_OPT_ELEV_DEG)),
        target_mass_kg=3.2,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=5400.0,
    )


def _build_s5_3_03() -> S5PartBuild:
    """S5.3-03: High-Speed Backup Optical Pyrometer Head & Closed-Loop Anneal Controller."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # Mates S5.1-01 325 deg (-35 deg) Z=500 CF40 port (R_face=250.0 -> origin R=250.5 mm)
    vp_40 = make_cf_viewport(
        "CF40", clear_aperture=28.0, window_diameter=34.0, window_thickness=4.0,
        sub_per_side=1, axis="-x", center=(6.35, 0.0, 0.0),
        name="pyro_cf40_viewport", material="316LN", window_material="Fused Silica",
    )
    lens_barrel = make_tube(16.0, 23.0, 52.0, segments=24, axis="x", center=(39.0, 0.0, 0.0), name="pyro_lens_barrel", material="Al 6061")
    sensor_head = make_chamfered_box(54.0, 50.0, 52.0, chamfer=2.5, center=(92.5, 0.0, 0.0), name="pyro_ingaas_si_head", material="Al 6061")
    ctrl_pack = make_chamfered_box(22.0, 48.0, 48.0, chamfer=2.0, center=(131.0, 0.0, 0.0), name="pyro_pid_module", material="Al 6061")
    bnc_conn = make_cylinder(6.0, 14.0, segments=12, axis="z", center=(92.5, 0.0, 33.2), material="316LN")

    shells.extend([vp_40, lens_barrel, sensor_head, ctrl_pack, bnc_conn])
    step_shells.extend([
        make_cylinder(34.75, 12.7, segments=12, axis="x", center=(6.35, 0.0, 0.0)),
        make_cylinder(23.0, 52.0, segments=12, axis="x", center=(39.0, 0.0, 0.0)),
        make_box(76.5, 50.0, 52.0, center=(103.8, 0.0, 0.0)),
    ])

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF40", "bore_id": 28.0}, translate=(6.35, 0.0, 0.0), rotate=(0.0, -90.0, 0.0), comment="CF40 optical sight viewport flange"),
        ScadFeature("add_tube", {"od": 46.0, "id": 32.0, "h": 52.0}, translate=(39.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="IR collection optics barrel"),
        ScadFeature("add_box", {"dx": 54.0, "dy": 50.0, "dz": 52.0}, translate=(92.5, 0.0, 0.0), comment="Dual-wavelength InGaAs/Si pyrometer head"),
        ScadFeature("add_box", {"dx": 22.0, "dy": 48.0, "dz": 48.0}, translate=(131.0, 0.0, 0.0), comment="Closed-loop <100 us anneal controller module"),
    ])

    mesh = merge_solids(shells, name="S5.3-03", material="Al 6061")
    step_mesh = merge_solids(step_shells, name="S5.3-03_step", material="Al 6061")
    ix, iy, iz = inclined_pos(LOADLOCK_S53_PYRO_T_FACE_MM + 0.5, LOADLOCK_S53_PYRO_AZ_DEG, LOADLOCK_OPT_ELEV_DEG)
    design = make_part_design_from_bom(
        "S5.3-03",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        temp_k=300.0,
        surface_finish_ra_um=0.8,
        world_origin_mm=(round(LOADLOCK_CENTER_X_MM + ix, 4), round(iy, 4), round(Z_WAFER_MM + iz, 4)),
        world_rotation_deg=(0.0, -LOADLOCK_OPT_ELEV_DEG, LOADLOCK_S53_PYRO_AZ_DEG),
        ports=(
            make_cf_port_interface("CF40", "chamber_cf40_mate", (0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), mating_part_id="S5.1-03", bore_override_mm=28.0),
            PortInterface("pyro_daq_out", "electrical", (92.5, 0.0, 40.2), (0.0, 0.0, 1.0), "SMA + 100 us Analog/SPI", mating_part_id="S7.3-01"),
        ),
        dimensions=(
            DimensionCallout("TOTAL_LEN", 142.0, 0.5, -0.5, view="top"),
            DimensionCallout("CF40_OD", 69.5, 0.1, -0.1, prefix="Ø", view="right"),
            DimensionCallout("HEAD_W", 50.0, 0.2, -0.2, view="top"),
        ),
        gdt_frames=(
            GDTFrame("concentricity", 0.10, diameter_zone=True, datum_primary="B", feature_note="Lens barrel optical axis to CF40 flange"),
        ),
        notes=(
            "High-speed backup dual-wavelength InGaAs/Si optical pyrometer (300-1200 C, +/-3 C, <100 us).",
            "OBS-001 fix: Relocated to S5.1-03 36-deg inclined 225-deg CF40 port with unobstructed top-surface view of wafer S5.4-01.",
        ),
        scad_params=(("response_us", 100), ("temp_min_C", 300), ("temp_max_C", 1200), ("elev_deg", LOADLOCK_OPT_ELEV_DEG)),
        target_mass_kg=1.4,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=3800.0,
    )


def _build_s5_3_04() -> S5PartBuild:
    """S5.3-04: Water-Cooled OFHC Cu / Mo S2-Head Thermal Shutter Blade & Pneumatic Bellows Actuator."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # Mates S5.1-01 212 deg Z=510.0 CF40 port (R_face=250.0 -> origin R=250.5 mm, rot_z=212 deg)
    # Retracted write-beam-open parked state: blade sits cleanly inside CF40 retraction bonnet (0 clash!)
    fl_in = make_cf_flange("CF40", sub_per_side=1, axis="-x", center=(6.35, 0.0, 0.0), material="316LN")
    bonnet = make_tube(20.0, 24.5, 51.0, segments=28, axis="x", center=(38.3, 0.0, 0.0), name="shutter_park_bonnet", material="316LN")
    # Water-cooled OFHC Cu thermal absorber core + Mo high-reflectivity front radiation shield blade
    cu_core = make_chamfered_box(42.0, 26.0, 3.0, chamfer=0.5, center=(38.0, 0.0, 0.0), name="shutter_ofhc_core", material="OFHC Cu")
    mo_plate = make_box(40.0, 24.0, 1.2, center=(38.0, 0.0, -2.2), name="shutter_mo_reflector", material="Mo")
    # Twin coaxial water-cooling push-rods connecting blade to actuator
    rod_a = make_cylinder(2.5, 84.0, segments=12, axis="x", center=(101.0, -5.0, 0.0), material="OFHC Cu")
    rod_b = make_cylinder(2.5, 84.0, segments=12, axis="x", center=(101.0, 5.0, 0.0), material="OFHC Cu")
    fl_mid = make_cf_flange("CF40", sub_per_side=1, axis="+x", center=(70.3, 0.0, 0.0), material="316LN")
    # 16-convolution edge-welded 316L UHV linear feedthrough bellows (x = 77.0..139.0)
    bellows = make_bellows(
        r_in=11.0, r_out=18.5, length=62.0, n_convolutions=16, wall_thickness=0.18,
        end_cuff_mm=3.0, segments=24, axis="x", center=(108.0, 0.0, 0.0),
        name="shutter_uhv_bellows", material="316L",
    )
    # Double-acting pneumatic actuator barrel + rotary water-cooling union at rear (x = 139.5..198.0)
    pneu_cyl = make_cylinder(18.0, 52.0, segments=24, axis="x", center=(165.5, 0.0, 0.0), name="shutter_pneumatic_cyl", material="Al 6061")
    cool_union = make_chamfered_box(16.0, 26.0, 24.0, chamfer=2.0, center=(200.0, 0.0, 0.0), name="shutter_water_union", material="OFHC Cu")
    air_fit_1 = make_cylinder(4.5, 14.0, segments=12, axis="z", center=(150.0, 0.0, 24.5), material="316LN")
    air_fit_2 = make_cylinder(4.5, 14.0, segments=12, axis="z", center=(180.0, 0.0, 24.5), material="316LN")

    shells.extend([
        fl_in, bonnet, cu_core, mo_plate, rod_a, rod_b,
        fl_mid, bellows, pneu_cyl, cool_union, air_fit_1, air_fit_2,
    ])
    step_shells.extend([
        make_cylinder(34.75, 12.7, segments=12, axis="x", center=(6.35, 0.0, 0.0)),
        make_tube(20.0, 24.5, 51.0, segments=12, axis="x", center=(38.3, 0.0, 0.0)),
        make_cylinder(34.75, 12.7, segments=12, axis="x", center=(70.3, 0.0, 0.0)),
        make_cylinder(18.5, 130.0, segments=12, axis="x", center=(142.0, 0.0, 0.0)),
    ])

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(6.35, 0.0, 0.0), rotate=(0.0, -90.0, 0.0), comment="Chamber-mating CF40 flange (212 deg, Z=510 mm)"),
        ScadFeature("add_tube", {"od": 49.0, "id": 40.0, "h": 51.0}, translate=(38.3, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="Retracted shutter blade parking spool"),
        ScadFeature("add_box", {"dx": 42.0, "dy": 26.0, "dz": 3.0}, translate=(38.0, 0.0, 0.0), comment="Water-cooled OFHC Cu + Mo S2-head thermal shutter blade"),
        ScadFeature("add_tube", {"od": 37.0, "id": 22.0, "h": 62.0}, translate=(108.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="16-conv UHV linear bellows"),
        ScadFeature("add_cylinder", {"d": 36.0, "h": 52.0}, translate=(165.5, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="Pneumatic linear actuator"),
    ])

    mesh = merge_solids(shells, name="S5.3-04", material="OFHC Cu")
    step_mesh = merge_solids(step_shells, name="S5.3-04_step", material="OFHC Cu")
    sx, sy, _ = radial_pos(LOADLOCK_SHUTTER_R_FACE_MM + 0.5, LOADLOCK_SHUTTER_AZ_DEG, 0.0)
    design = make_part_design_from_bom(
        "S5.3-04",
        design_tier="CUSTOM_FULL",
        material="OFHC Cu",
        temp_k=300.0,
        surface_finish_ra_um=0.4,
        world_origin_mm=(round(LOADLOCK_CENTER_X_MM + sx, 4), round(sy, 4), Z_WAFER_MM + LOADLOCK_SHUTTER_Z_LOC_MM),
        world_rotation_deg=(0.0, 0.0, LOADLOCK_SHUTTER_AZ_DEG),
        ports=(
            make_cf_port_interface("CF40", "chamber_cf40_mate", (0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), mating_part_id="S5.1-03"),
            PortInterface("di_water_loop", "cooling", (208.0, 0.0, 0.0), (1.0, 0.0, 0.0), "Dual 1/8 in VCR Cooling"),
            PortInterface("pneumatic_6bar", "gas", (165.0, 0.0, 31.5), (0.0, 0.0, 1.0), "6 bar Dry N2 Actuator"),
        ),
        dimensions=(
            DimensionCallout("ASSY_LEN", 208.0, 0.5, -0.5, view="top"),
            DimensionCallout("BLADE_W", 26.0, 0.1, -0.1, view="top"),
            DimensionCallout("BLADE_T", 4.2, 0.1, -0.1, view="front"),
            DimensionCallout("CF40_OD", 69.5, 0.1, -0.1, prefix="Ø", view="right"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.05, datum_primary="", feature_note="Mo reflective heat-shield face"),
            GDTFrame("parallelism", 0.15, datum_primary="A", feature_note="Blade travel plane inside load-lock Z=545 mm clear gap"),
        ),
        notes=(
            "Water-cooled OFHC Cu core + Mo reflective thermal/MBE shutter protecting load-lock optics/MBE during flash anneal.",
            "OBS-001 fix: Relocated to S5.1-03 load-lock 320 deg Z=545.0 mm clear gap (45 mm above wafer, 40 mm below MBE flange, >420 mm clear of S2.1-03!).",
        ),
        scad_params=(("blade_l", 42.0), ("blade_w", 26.0), ("stroke_mm", 175.0), ("bellows_conv", 16)),
        target_mass_kg=2.6,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=7200.0,
    )


# ---------------------------------------------------------------------------
# S5.5 808 nm qCW Flash Annealing Optical Head, Sapphire Viewport & Shutter (+Y)
# ---------------------------------------------------------------------------
def _build_s5_5_02() -> S5PartBuild:
    """S5.5-02: CF63 +Y Equatorial (Z=500 mm) AR-Coated Sapphire Laser Viewport (Dia 44 mm CA)."""
    # Mates S5.1-01 +Y CF63 flange (Y=295.0 -> origin Y=295.5 mm, +0.5 mm Cu gasket clearance)
    # axis="-y" puts knife-edge on -Y (facing vacuum chamber) and stepped sapphire seat on +Y!
    vp = make_cf_viewport(
        "CF63", clear_aperture=44.0, window_diameter=50.0, window_thickness=8.0,
        sub_per_side=1, axis="-y", center=(0.0, 8.75, 0.0),
        name="S5.5-02", material="316LN", window_material="Sapphire",
    )
    scad_feats = (
        ScadFeature("add_cf_flange", {"size": "CF63", "bore_id": 44.0}, translate=(0.0, 8.75, 0.0), rotate=(90.0, 0.0, 0.0), comment="ISO 3669 CF63 316LN optical viewport flange (8xM8 @ PCD 92.1)"),
        ScadFeature("add_cylinder", {"d": 50.0, "h": 8.0}, translate=(0.0, 13.5, 0.0), rotate=(90.0, 0.0, 0.0), comment="Single-crystal AR sapphire window (Dia 50x8 mm, Dia 44 mm CA)"),
    )
    s55_02_x, s55_02_y, s55_02_z = inclined_pos(LOADLOCK_S55_T_FACE_MM + 0.5, 90.0, LOADLOCK_OPT_ELEV_DEG)
    design = make_part_design_from_bom(
        "S5.5-02",
        design_tier="COTS_ENV_ICD",
        material="316LN",
        temp_k=300.0,
        surface_finish_ra_um=0.1,
        world_origin_mm=(round(LOADLOCK_CENTER_X_MM + s55_02_x, 4), round(s55_02_y, 4), round(Z_WAFER_MM + s55_02_z, 4)),
        world_rotation_deg=(LOADLOCK_OPT_ELEV_DEG, 0.0, 0.0),
        ports=(
            make_cf_port_interface("CF63", "chamber_pos_y_cf63", (0.0, 0.0, 0.0), (0.0, -1.0, 0.0), mating_part_id="S5.1-03", bore_override_mm=44.0),
            PortInterface("optical_808nm_in", "optical", (0.0, 17.5, 0.0), (0.0, 1.0, 0.0), "Dia 44 mm CA AR@808nm", mating_part_id="S5.5-04", bore_mm=44.0, od_mm=50.0),
        ),
        dimensions=(
            DimensionCallout("CF63_OD", 113.5, 0.10, -0.10, prefix="Ø", view="front"),
            DimensionCallout("CF63_PCD", 92.1, 0.10, -0.10, prefix="Ø", view="front", is_basic=True),
            DimensionCallout("CLEAR_AP", 44.0, 0.05, -0.05, prefix="Ø", view="front"),
            DimensionCallout("WIN_OD", 50.0, 0.05, -0.05, prefix="Ø", view="front"),
            DimensionCallout("FLANGE_T", 17.5, 0.10, -0.10, view="right"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.005, datum_primary="", feature_note="Sapphire optical face (lambda/10 @ 808 nm)"),
            GDTFrame("perpendicularity", 0.02, diameter_zone=True, datum_primary="A", feature_note="Dia 44 mm clear aperture to CF63 sealing face"),
            GDTFrame("concentricity", 0.05, diameter_zone=True, datum_primary="B", feature_note="Window counterbore seat to CF63 PCD"),
        ),
        notes=(
            "OBS-001 fix: Relocated to S5.1-03 load-lock 36-deg inclined +Y CF63 AR sapphire viewport aimed at wafer S5.4-01 (420, 0, 500) with unobstructed LOS (sin 36 deg = 0.588 normal flux coupling).",
            "Dia 50x8 mm window, Dia 44 mm CA (4.0 mm radial margin to Dia 36 mm beam), n(808nm)=1.760, T_AR=98.0%, He leak <= 1e-10 mbar*L/s.",
            "Enclosed cleanly inside relocated S7.SAFETY-02 OD8 + 3 mm 316L interlock shroud.",
        ),
        scad_params=(("cf63_od", 113.5), ("clear_aperture_mm", 44.0), ("sapphire_d", 50.0), ("sapphire_t", 8.0), ("elev_deg", LOADLOCK_OPT_ELEV_DEG)),
        target_mass_kg=1.1,
    )
    # 760-ish faces with sub_per_side=1 -> exact full-mesh STEP directly!
    return S5PartBuild(
        design=design, mesh=vp, scad_features=scad_feats,
        step_mesh=None, density_kg_m3=7500.0,
    )


def _build_s5_5_04() -> S5PartBuild:
    """S5.5-04: Dual-Coil Fail-Safe Laser Beam Shutter (<3.2 ms, MXC <1 K & UHV Interlock)."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # World origin = (0.0, 327.0, 500.0) -> coils Y=[314.5, 339.5], body Y=[317.0, 337.0] (+1.5 mm clear of S5.5-02 at 313.0)
    body = make_rect_plate_with_features(
        74.0, 74.0, 20.0, circular_holes=((0.0, 0.0, 46.0),),
        hole_segments=28, axis="y", center=(0.0, 0.0, 0.0),
        name="shutter_316ln_body", material="316LN",
    )
    # Internal OFHC Cu beam-dump absorber blade (parked upper pocket above beam aperture)
    blade = make_box(50.0, 4.0, 12.0, center=(0.0, 0.0, 30.0), name="shutter_cu_absorber_blade", material="OFHC Cu")
    # Dual redundant 1oo2D fail-safe return-spring solenoid coil pods (+/-X)
    coil_l = make_cylinder(12.5, 48.0, segments=20, axis="z", center=(-49.8, 0.0, 0.0), name="shutter_coil_chA", material="316LN")
    coil_r = make_cylinder(12.5, 48.0, segments=20, axis="z", center=(49.8, 0.0, 0.0), name="shutter_coil_chB", material="316LN")
    # Mounting ear lugs linking coils to shutter body + bottom SIL-3 interlock connector block
    lug_l = make_box(12.0, 14.0, 18.0, center=(-43.2, 0.0, 0.0), material="316LN")
    lug_r = make_box(12.0, 14.0, 18.0, center=(43.2, 0.0, 0.0), material="316LN")
    interlock_box = make_chamfered_box(36.0, 18.0, 16.0, chamfer=1.5, center=(0.0, 0.0, -45.2), name="shutter_sil3_interlock", material="Al 6061")

    shells.extend([body, blade, coil_l, coil_r, lug_l, lug_r, interlock_box])
    step_shells.extend([
        make_box(74.0, 20.0, 74.0, center=(0.0, 0.0, 0.0)),
        make_cylinder(12.5, 48.0, segments=12, axis="z", center=(-49.8, 0.0, 0.0)),
        make_cylinder(12.5, 48.0, segments=12, axis="z", center=(49.8, 0.0, 0.0)),
        make_box(36.0, 18.0, 16.0, center=(0.0, 0.0, -45.2)),
    ])

    scad_feats.extend([
        ScadFeature("add_box", {"dx": 74.0, "dy": 20.0, "dz": 74.0}, comment="316LN fail-safe shutter housing (74x20x74 mm)"),
        ScadFeature("add_cylinder", {"d": 25.0, "h": 48.0}, translate=(-49.8, 0.0, 0.0), comment="Redundant fail-safe solenoid coil Ch-A"),
        ScadFeature("add_cylinder", {"d": 25.0, "h": 48.0}, translate=(49.8, 0.0, 0.0), comment="Redundant fail-safe solenoid coil Ch-B"),
        ScadFeature("add_box", {"dx": 36.0, "dy": 18.0, "dz": 16.0}, translate=(0.0, 0.0, -45.2), comment="MXC<1 K & SIL-3 PLC interlock connector"),
        ScadFeature("cut_hole", {"d": 46.0, "h": 24.0}, rotate=(90.0, 0.0, 0.0), comment="Dia 46 mm clear 808 nm beam aperture"),
    ])

    mesh = merge_solids(shells, name="S5.5-04", material="316LN")
    step_mesh = merge_solids(step_shells, name="S5.5-04_step", material="316LN")
    s55_04_x, s55_04_y, s55_04_z = inclined_pos(LOADLOCK_S55_T_FACE_MM + 32.0, 90.0, LOADLOCK_OPT_ELEV_DEG)
    design = make_part_design_from_bom(
        "S5.5-04",
        design_tier="CUSTOM_FULL",
        material="316LN",
        temp_k=300.0,
        surface_finish_ra_um=0.8,
        world_origin_mm=(round(LOADLOCK_CENTER_X_MM + s55_04_x, 4), round(s55_04_y, 4), round(Z_WAFER_MM + s55_04_z, 4)),
        world_rotation_deg=(LOADLOCK_OPT_ELEV_DEG, 0.0, 0.0),
        ports=(
            PortInterface("viewport_side_ap", "optical", (0.0, -10.0, 0.0), (0.0, -1.0, 0.0), "Dia 46 mm Beam Aperture", mating_part_id="S5.5-02", bore_mm=46.0),
            PortInterface("laser_side_ap", "optical", (0.0, 10.0, 0.0), (0.0, 1.0, 0.0), "Dia 46 mm Beam Aperture", mating_part_id="S5.5-01", bore_mm=46.0),
            PortInterface("sil3_interlock_bus", "electrical", (0.0, 0.0, -53.2), (0.0, 0.0, -1.0), "1oo2D Dual-Coil Interlock", mating_part_id="S7.SAFETY-03"),
        ),
        dimensions=(
            DimensionCallout("BODY_W", 74.0, 0.1, -0.1, view="front"),
            DimensionCallout("BODY_T", 20.0, 0.1, -0.1, view="right"),
            DimensionCallout("APERTURE", 46.0, 0.1, -0.1, prefix="Ø", view="front"),
            DimensionCallout("COIL_SPAN", 124.6, 0.3, -0.3, view="front"),
        ),
        gdt_frames=(
            GDTFrame("parallelism", 0.05, datum_primary="A", feature_note="Front & rear optical mounting faces"),
            GDTFrame("concentricity", 0.10, diameter_zone=True, datum_primary="B", feature_note="Dia 46 aperture to S5.5-02 sapphire axis"),
        ),
        notes=(
            "Dual-coil 1oo2D fail-safe laser beam shutter (<3.2 ms mechanical closure, OFHC Cu absorber blade).",
            "Interlocked to MXC <1 K thermal latch, UHV gate valve & S7.SAFETY-03 PLC; fits cleanly inside S7.SAFETY-02 shroud.",
        ),
        scad_params=(("body_xy", 74.0), ("body_t", 20.0), ("aperture_d", 46.0), ("close_time_ms", 3.2)),
        target_mass_kg=0.78,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=5500.0,
    )


def _build_s5_5_01() -> S5PartBuild:
    """S5.5-01: 808 nm qCW Diode Bar-Stack + Micro-Channel Water-Cooled Homogenizer Head (84x88x84 mm)."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # World origin = (0.0, 385.0, 500.0) -> core Y=[341.0, 429.0] (+1.5 mm clear of S5.5-04 coils at 339.5)
    # Exact Exp130 84x88x84 mm core homogenizer housing: middle sleeve cleanly between front/rear aperture plates
    core_shell = make_hollow_enclosure(
        84.0, 71.8, 84.0, wall=8.0, open_faces=("-y", "+y"), center=(0.0, 0.0, 0.0),
        name="homog_core_body", material="Al 6061",
    )
    front_plate = make_rect_plate_with_features(
        84.0, 84.0, 8.0, circular_holes=((0.0, 0.0, 44.0),),
        hole_segments=28, axis="y", center=(0.0, -40.0, 0.0), material="Al 6061",
    )
    rear_plate = make_rect_plate_with_features(
        84.0, 84.0, 8.0, circular_holes=((0.0, 0.0, 32.0),),
        hole_segments=24, axis="y", center=(0.0, 40.0, 0.0), material="Al 6061",
    )
    # Internal fused-silica flat-top homogenizer light-pipe & microlens array barrel
    light_pipe = make_tube(17.5, 22.0, 68.0, segments=24, axis="y", center=(0.0, 0.0, 0.0), name="fused_silica_homogenizer", material="Fused Silica")
    # Micro-channel OFHC Cu water-cooling side manifold blocks (+/-X) + coolant barbs
    mc_l = make_chamfered_box(10.0, 68.0, 56.0, chamfer=1.5, center=(-47.2, 0.0, 0.0), name="microchannel_cooler_l", material="OFHC Cu")
    mc_r = make_chamfered_box(10.0, 68.0, 56.0, chamfer=1.5, center=(47.2, 0.0, 0.0), name="microchannel_cooler_r", material="OFHC Cu")
    barb_l = make_cylinder(4.5, 16.0, segments=12, axis="-z", center=(-47.2, 18.0, -36.2), material="OFHC Cu")
    barb_r = make_cylinder(4.5, 16.0, segments=12, axis="-z", center=(47.2, 18.0, -36.2), material="OFHC Cu")
    # Top diagnostic optical collar (z_loc = +42.0..+44.5 -> Z = 542.0..544.5, feeds S5.5-03 dichroic turret!)
    top_collar = make_tube(14.0, 19.0, 2.5, segments=24, axis="z", center=(0.0, 0.0, 43.3), material="Al 6061")
    # Rear 808 nm qCW diode bar-stack & fiber-bundle collimator barrel (y_loc = +44.2..+82.0 -> Y = 423.2..461.0)
    collimator = make_tube(11.0, 18.0, 37.8, segments=24, axis="y", center=(0.0, 63.1, 0.0), name="fiber_collimator_808nm", material="316LN")

    shells.extend([
        core_shell, front_plate, rear_plate, light_pipe,
        mc_l, mc_r, barb_l, barb_r, top_collar, collimator,
    ])
    step_shells.extend([
        make_box(84.0, 88.0, 84.0, center=(0.0, 0.0, 0.0)),
        make_box(10.0, 68.0, 56.0, center=(-47.2, 0.0, 0.0)),
        make_box(10.0, 68.0, 56.0, center=(47.2, 0.0, 0.0)),
        make_cylinder(18.0, 37.8, segments=16, axis="y", center=(0.0, 63.1, 0.0)),
    ])

    scad_feats.extend([
        ScadFeature("add_box", {"dx": 84.0, "dy": 88.0, "dz": 84.0}, comment="84x88x84 mm flat-top 808 nm homogenizer housing"),
        ScadFeature("add_box", {"dx": 10.0, "dy": 68.0, "dz": 56.0}, translate=(-47.2, 0.0, 0.0), comment="OFHC Cu micro-channel water cooler (-X)"),
        ScadFeature("add_box", {"dx": 10.0, "dy": 68.0, "dz": 56.0}, translate=(47.2, 0.0, 0.0), comment="OFHC Cu micro-channel water cooler (+X)"),
        ScadFeature("add_cylinder", {"d": 36.0, "h": 37.8}, translate=(0.0, 63.1, 0.0), rotate=(90.0, 0.0, 0.0), comment="808 nm qCW fiber-bundle collimator"),
        ScadFeature("cut_hole", {"d": 44.0, "h": 92.0}, rotate=(90.0, 0.0, 0.0), comment="Dia 44 mm 808 nm optical bore"),
    ])

    mesh = merge_solids(shells, name="S5.5-01", material="Al 6061")
    step_mesh = merge_solids(step_shells, name="S5.5-01_step", material="Al 6061")
    s55_01_x, s55_01_y, s55_01_z = inclined_pos(LOADLOCK_S55_T_FACE_MM + 90.0, 90.0, LOADLOCK_OPT_ELEV_DEG)
    design = make_part_design_from_bom(
        "S5.5-01",
        design_tier="CUSTOM_FULL",
        material="Al 6061",
        temp_k=300.0,
        surface_finish_ra_um=0.4,
        world_origin_mm=(round(LOADLOCK_CENTER_X_MM + s55_01_x, 4), round(s55_01_y, 4), round(Z_WAFER_MM + s55_01_z, 4)),
        world_rotation_deg=(LOADLOCK_OPT_ELEV_DEG, 0.0, 0.0),
        ports=(
            PortInterface("homogenized_808nm_out", "optical", (0.0, -44.0, 0.0), (0.0, -1.0, 0.0), "Dia 36 mm Flat-Top 808 nm", mating_part_id="S5.5-04", bore_mm=44.0),
            PortInterface("dichroic_diag_top", "optical", (0.0, 0.0, 44.55), (0.0, 0.0, 1.0), "Dia 28 mm Pyrometer Tap", mating_part_id="S5.5-03", bore_mm=28.0),
            PortInterface("fiber_bundle_in", "optical", (0.0, 82.0, 0.0), (0.0, 1.0, 0.0), "808 nm qCW Diode Fiber Bundle", bore_mm=22.0, od_mm=36.0),
            PortInterface("microchannel_water", "cooling", (-47.2, 18.0, -44.2), (0.0, 0.0, -1.0), "DI Water 1.5 L/min"),
        ),
        dimensions=(
            DimensionCallout("CORE_X", 84.0, 0.1, -0.1, view="front"),
            DimensionCallout("CORE_Y", 88.0, 0.1, -0.1, view="right"),
            DimensionCallout("CORE_Z", 84.0, 0.1, -0.1, view="front"),
            DimensionCallout("TOTAL_Y", 126.0, 0.3, -0.3, view="right"),
            DimensionCallout("OUT_BORE", 44.0, 0.05, -0.05, prefix="Ø", view="front"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.05, diameter_zone=True, datum_primary="A", feature_note="808 nm optical exit bore to front face"),
            GDTFrame("concentricity", 0.08, diameter_zone=True, datum_primary="B", feature_note="Fiber collimator to homogenizer axis"),
        ),
        notes=(
            "Exp130/139 808 nm qCW diode bar-stack + micro-channel water-cooled flat-top homogenizer (+/-2% uniformity).",
            "Delivers 43.49 J/cm^2 in 1.0 ms (T_peak=1530.1 K, 99.99% {311} dissolution, sigma_anneal=0.430 nm).",
            "Entire +Y assembly fits cleanly inside S7.SAFETY-02 (280x260x220 mm) OD8 + 3 mm steel interlock shroud.",
        ),
        scad_params=(("core_x", 84.0), ("core_y", 88.0), ("core_z", 84.0), ("wavelength_nm", 808.0)),
        target_mass_kg=2.07,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=4100.0,
    )


def _build_s5_5_03() -> S5PartBuild:
    """S5.5-03: 45 deg Dichroic Beam-Splitter Turret + 10 us Two-Color InGaAs/Si Pyrometer Head."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # World origin = (0.0, 385.0, 568.5) -> Z=[545.5, 591.5] (+1.0 mm clear above S5.5-01 collar at 544.5)
    turret = make_hollow_enclosure(
        56.0, 58.0, 46.0, wall=5.0, open_faces=("-z",), center=(0.0, 0.0, 0.0),
        name="dichroic_turret_cube", material="Al 6061",
    )
    # Internal 45-deg tilted dichroic beam-splitter mirror disk (808 nm reflect / 0.95-1.6 um pass)
    dichroic = transform_mesh(
        make_cylinder(15.0, 3.0, segments=24, axis="z", name="dichroic_45deg_mirror", material="Fused Silica"),
        rotation_deg=(0.0, 45.0, 0.0),
        translation=(0.0, 0.0, 0.0),
    )
    # Dual fast 10 us photodiode sensor barrels: -X = InGaAs (1.55 um), +X = Si (0.95 um)
    ingaas_det = make_cylinder(11.0, 22.0, segments=20, axis="-x", center=(-39.2, 0.0, 0.0), name="pyro_ingaas_10us", material="Al 6061")
    si_det = make_cylinder(11.0, 22.0, segments=20, axis="+x", center=(39.2, 0.0, 0.0), name="pyro_si_10us", material="Al 6061")
    # Top FPGA pulse-energy integrator cap (z_loc = +23.2..+33.2 -> Z_max = 601.7, well inside S7.SAFETY-02!)
    fpga_cap = make_chamfered_box(50.0, 50.0, 10.0, chamfer=1.5, center=(0.0, 0.0, 28.2), name="pyro_energy_integrator", material="Al 6061")

    shells.extend([turret, dichroic, ingaas_det, si_det, fpga_cap])
    step_shells.extend([
        make_box(56.0, 58.0, 46.0, center=(0.0, 0.0, 0.0)),
        make_cylinder(11.0, 100.4, segments=12, axis="x", center=(0.0, 0.0, 0.0)),
        make_box(50.0, 50.0, 10.0, center=(0.0, 0.0, 28.2)),
    ])

    scad_feats.extend([
        ScadFeature("add_box", {"dx": 56.0, "dy": 58.0, "dz": 46.0}, comment="45 deg dichroic beam-splitter turret cube"),
        ScadFeature("add_cylinder", {"d": 30.0, "h": 3.0}, rotate=(0.0, 45.0, 0.0), comment="45 deg dichroic mirror element"),
        ScadFeature("add_cylinder", {"d": 22.0, "h": 22.0}, translate=(-39.2, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="InGaAs 10 us fast photodiode barrel"),
        ScadFeature("add_cylinder", {"d": 22.0, "h": 22.0}, translate=(39.2, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="Si 10 us fast photodiode barrel"),
        ScadFeature("add_box", {"dx": 50.0, "dy": 50.0, "dz": 10.0}, translate=(0.0, 0.0, 28.2), comment="Closed-loop +/-1.5% energy integrator FPGA"),
    ])

    mesh = merge_solids(shells, name="S5.5-03", material="Al 6061")
    step_mesh = merge_solids(step_shells, name="S5.5-03_step", material="Al 6061")
    s55_01_x, s55_01_y, s55_01_z = inclined_pos(LOADLOCK_S55_T_FACE_MM + 90.0, 90.0, LOADLOCK_OPT_ELEV_DEG)
    el_rad = math.radians(LOADLOCK_OPT_ELEV_DEG)
    s55_03_y = s55_01_y - 68.5 * math.sin(el_rad)
    s55_03_z = s55_01_z + 68.5 * math.cos(el_rad)
    design = make_part_design_from_bom(
        "S5.5-03",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        temp_k=300.0,
        surface_finish_ra_um=0.8,
        world_origin_mm=(round(LOADLOCK_CENTER_X_MM + s55_01_x, 4), round(s55_03_y, 4), round(Z_WAFER_MM + s55_03_z, 4)),
        world_rotation_deg=(LOADLOCK_OPT_ELEV_DEG, 0.0, 0.0),
        ports=(
            PortInterface("optical_tap_in", "optical", (0.0, 0.0, -23.0), (0.0, 0.0, -1.0), "Dia 28 mm Thermal IR Tap", mating_part_id="S5.5-01", bore_mm=28.0),
            PortInterface("integrator_fpga_bus", "electrical", (0.0, 0.0, 33.2), (0.0, 0.0, 1.0), "LVDS / 10 us Pyrometer Telemetry", mating_part_id="S7.3-01"),
        ),
        dimensions=(
            DimensionCallout("TURRET_W", 56.0, 0.15, -0.15, view="front"),
            DimensionCallout("DET_SPAN", 100.4, 0.30, -0.30, view="front"),
            DimensionCallout("TURRET_H", 56.2, 0.20, -0.20, view="right"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.05, diameter_zone=True, datum_primary="A", feature_note="InGaAs/Si detector barrels to optical cube datum A"),
            GDTFrame("angularity", 0.05, datum_primary="A", feature_note="45.0 deg dichroic mirror carrier seat"),
        ),
        notes=(
            "Exp130 45 deg dichroic + 10 us two-color InGaAs/Si pyrometer (900-1700 K, +/-1.5% closed-loop energy).",
            "Mounts on top diagnostic port of S5.5-01; fits well inside S7.SAFETY-02 (280x260x220 mm) shroud.",
        ),
        scad_params=(("dt_us", 10.0), ("dichroic_deg", 45.0), ("energy_tol_pct", 1.5)),
        target_mass_kg=0.38,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=3200.0,
    )


# ---------------------------------------------------------------------------
# S5.6 In-Situ 28Si UHV LT-MBE Capper & Forming-Gas Passivation (Exp139)
# ---------------------------------------------------------------------------
def _build_s5_6_01() -> S5PartBuild:
    """S5.6-01: CF100 Crucible-Free DC 28Si Rod Sublimation MBE Source + Fully-Bored Cryoshroud (OBS-001)."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # World origin = (420.0, 0.0, 585.5) -> +0.5 mm Cu gasket clearance above S5.1-03 +Z CF100 (Z=585.0)
    # Total height = 279.5 mm -> exact Exp139 top Z = 865.0 mm!
    fl_bot = make_cf_flange("CF100", sub_per_side=1, axis="-z", center=(0.0, 0.0, 9.9), material="316LN")
    # OBS-001 fix: Perforate BOTH outer_barrel (R=63..68) & cryoshroud (R=46..51) across port belt z=[68, 194]
    # so S5.6-02 QCM (-Y, 270 deg), S5.6-03 PBN+FGA (228 deg), and S5.6-04 80 L/s TMP+NEG (+X, 0 deg) have
    # 100% open bores right through to the 28Si rod evaporation axis!
    barrel_lo = make_tube(63.0, 68.0, 48.0, segments=48, axis="z", center=(0.0, 0.0, 43.9), name="mbe_outer_barrel_lo", material="316LN")
    barrel_mid_a = make_arc_sector_solid(63.0, 68.0, 126.0, 34.0, 204.0, arc_segments=28, center_z=131.0, name="mbe_outer_barrel_n", material="316LN")
    barrel_mid_b = make_arc_sector_solid(63.0, 68.0, 126.0, 294.0, 326.0, arc_segments=10, center_z=131.0, name="mbe_outer_barrel_se", material="316LN")
    barrel_hi = make_tube(63.0, 68.0, 15.8, segments=48, axis="z", center=(0.0, 0.0, 202.0), name="mbe_outer_barrel_hi", material="316LN")
    # Internal double-walled OFHC Cu water/LN2 cryoshroud (similarly bored open for 0, 228, 270 deg; 0.2 mm seam prevents STL merge!)
    shroud_lo = make_tube(46.0, 51.0, 42.8, segments=36, axis="z", center=(0.0, 0.0, 46.4), name="mbe_cryoshroud_lo", material="OFHC Cu")
    shroud_mid_a = make_arc_sector_solid(46.0, 51.0, 126.0, 44.0, 198.0, arc_segments=22, center_z=131.0, name="mbe_cryoshroud_n", material="OFHC Cu")
    shroud_mid_b = make_arc_sector_solid(46.0, 51.0, 126.0, 300.0, 320.0, arc_segments=8, center_z=131.0, name="mbe_cryoshroud_se", material="OFHC Cu")
    shroud_hi = make_tube(46.0, 51.0, 10.0, segments=36, axis="z", center=(0.0, 0.0, 199.2), name="mbe_cryoshroud_hi", material="OFHC Cu")

    mo_holder = make_tube(8.0, 18.0, 32.0, segments=24, axis="z", center=(0.0, 0.0, 178.0), name="mbe_mo_collet", material="Mo")
    si28_rod = make_cylinder(6.5, 68.0, segments=20, axis="z", center=(0.0, 0.0, 128.0), name="mbe_28si_rod", material="Si")

    # 3 Welded Radial Auxiliary CF Ports on MBE barrel (R_out = 68.0 mm):
    # -Y (270 deg) CF40 at z_loc=119.5 (Z=705.0, face at y=-88.0) -> mates S5.6-02 QCM/Valve
    # 310 deg (+X/-Y) CF40 at z_loc=105.0 (Z=690.5, face at r=88.0) -> mates S5.6-03 PBN Heater/FG (clears +Y S5.5!)
    # +X (0 deg) CF63 at z_loc=124.5 (Z=710.0, face at x=+94.0, X=514.0) -> mates S5.6-04 80 L/s TMP+NEG
    p_qcm = make_cf_weld_neck("CF40", neck_length=7.1, sub_per_side=1, axis="-y", center=(0.0, -81.65, 119.5), name="mbe_port_qcm", material="316LN")
    pux, puy, _ = radial_vec(S56_PBN_AZ_DEG)
    p_pbn = make_cf_weld_neck("CF40", neck_length=7.1, sub_per_side=1, axis=(pux, puy, 0.0), center=(81.65 * pux, 81.65 * puy, S56_PBN_Z_LOC_MM), name="mbe_port_pbn", material="316LN")
    p_tmp = make_cf_weld_neck("CF63", neck_length=8.3, sub_per_side=1, axis="+x", center=(85.25, 0.0, 124.5), name="mbe_port_tmp", material="316LN")

    # Top CF100 flange (z=210.0..229.8) + DC power feedthrough turret & pneumatic rotary MBE shutter cap (z=230..279.5)
    fl_top = make_cf_flange("CF100", sub_per_side=1, axis="+z", center=(0.0, 0.0, 219.9), material="316LN")
    top_turret = make_cylinder(52.0, 36.0, segments=32, axis="z", center=(0.0, 0.0, 248.0), name="mbe_dc_shutter_head", material="316LN")
    shutter_act = make_cylinder(24.0, 13.3, segments=20, axis="z", center=(0.0, 0.0, 272.85), name="mbe_pneumatic_shutter_cap", material="Al 6061")
    dc_pin_1 = make_cylinder(7.0, 16.0, segments=12, axis="z", center=(-34.0, 0.0, 271.5), material="Al2O3")
    dc_pin_2 = make_cylinder(7.0, 16.0, segments=12, axis="z", center=(34.0, 0.0, 271.5), material="Al2O3")

    shells.extend([
        fl_bot, barrel_lo, barrel_mid_a, barrel_mid_b, barrel_hi,
        shroud_lo, shroud_mid_a, shroud_mid_b, shroud_hi,
        mo_holder, si28_rod, p_qcm, p_pbn, p_tmp, fl_top, top_turret, shutter_act, dc_pin_1, dc_pin_2,
    ])
    step_shells.extend([
        make_cylinder(76.0, 19.8, segments=16, axis="z", center=(0.0, 0.0, 9.9)),
        make_tube(63.0, 68.0, 190.0, segments=20, axis="z", center=(0.0, 0.0, 114.9)),
        make_cylinder(76.0, 19.8, segments=16, axis="z", center=(0.0, 0.0, 219.9)),
        make_cylinder(52.0, 49.5, segments=16, axis="z", center=(0.0, 0.0, 254.75)),
        make_cylinder(34.75, 12.7, segments=12, axis="y", center=(0.0, -81.65, 119.5)),
        make_cylinder(34.75, 12.7, segments=12, axis=(pux, puy, 0.0), center=(81.65 * pux, 81.65 * puy, S56_PBN_Z_LOC_MM)),
        make_cylinder(56.75, 17.5, segments=12, axis="x", center=(85.25, 0.0, 124.5)),
    ])

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF100"}, translate=(0.0, 0.0, 9.9), rotate=(180.0, 0.0, 0.0), comment="Bottom CF100 flange mating Load-Lock +Z (Z=585.5 mm)"),
        ScadFeature("add_tube", {"od": 136.0, "id": 126.0, "h": 190.0}, translate=(0.0, 0.0, 114.9), comment="316LN MBE source barrel (bored for radial CF ports)"),
        ScadFeature("add_tube", {"od": 102.0, "id": 92.0, "h": 174.0}, translate=(0.0, 0.0, 112.0), comment="OFHC Cu water/LN2 cryoshroud (bored for radial CF ports)"),
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(0.0, -81.65, 119.5), rotate=(90.0, 0.0, 0.0), comment="-Y CF40 port for S5.6-02 QCM"),
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(round(81.65 * pux, 3), round(81.65 * puy, 3), S56_PBN_Z_LOC_MM), rotate=(0.0, 90.0, S56_PBN_AZ_DEG), comment="310 deg CF40 port for S5.6-03 PBN heater"),
        ScadFeature("add_cf_flange", {"size": "CF63"}, translate=(85.25, 0.0, 124.5), rotate=(0.0, 90.0, 0.0), comment="+X CF63 port for S5.6-04 80 L/s TMP+NEG"),
        ScadFeature("add_cf_flange", {"size": "CF100"}, translate=(0.0, 0.0, 219.9), comment="Top CF100 DC sublimation & pneumatic shutter flange"),
    ])

    mesh = merge_solids(shells, name="S5.6-01", material="316LN")
    step_mesh = merge_solids(step_shells, name="S5.6-01_step", material="316LN")
    design = make_part_design_from_bom(
        "S5.6-01",
        design_tier="CUSTOM_FULL",
        material="316LN",
        temp_k=300.0,
        surface_finish_ra_um=0.4,
        world_origin_mm=(LOADLOCK_CENTER_X_MM, 0.0, 585.5),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            make_cf_port_interface("CF100", "loadlock_cf100_base", (0.0, 0.0, 0.0), (0.0, 0.0, -1.0), mating_part_id="S5.1-03"),
            make_cf_port_interface("CF40", "qcm_neg_y_cf40", (0.0, -88.0, 119.5), (0.0, -1.0, 0.0), mating_part_id="S5.6-02"),
            make_cf_port_interface("CF40", "pbn_pos_y_cf40", (round(88.0 * pux, 4), round(88.0 * puy, 4), S56_PBN_Z_LOC_MM), (pux, puy, 0.0), mating_part_id="S5.6-03"),
            make_cf_port_interface("CF63", "mbe_tmp_pos_x_cf63", (94.0, 0.0, 124.5), (1.0, 0.0, 0.0), mating_part_id="S5.6-04"),
            PortInterface("dc_400w_feed", "electrical", (-34.0, 0.0, 279.5), (0.0, 0.0, 1.0), "400 W DC Sublimation PSU", mating_part_id="S7.4-01"),
        ),
        dimensions=(
            DimensionCallout("CF100_OD", 152.0, 0.15, -0.15, prefix="Ø", view="top"),
            DimensionCallout("BARREL_OD", 136.0, 0.20, -0.20, prefix="Ø", view="top"),
            DimensionCallout("TOTAL_H", 279.5, 0.30, -0.30, view="front"),
            DimensionCallout("SHROUD_ID", 92.0, 0.20, -0.20, prefix="Ø", view="top"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.08, diameter_zone=True, datum_primary="A", feature_note="28Si rod sublimation axis to CF100 base"),
            GDTFrame("concentricity", 0.10, diameter_zone=True, datum_primary="B", feature_note="OFHC cryoshroud to CF100 bore"),
        ),
        notes=(
            "Exp139 S5.6 crucible-free DC 28Si rod sublimation MBE source + OFHC water/LN2 cryoshroud + pneumatic shutter.",
            "Mounts directly on S5.1-03 Load-Lock +Z CF100 (Z=585.5..865.0 mm); 0.10 nm/s -> 8.0 +/-0.3 nm cap in 80 s.",
            "Target mass 11.8 kg (Exp139 s56_hardware_spec.json); 0.00 uW thermal leak to 20 mK DR.",
        ),
        scad_params=(("cf100_od", 152.0), ("barrel_od", 136.0), ("height_mm", 279.5), ("growth_rate_nm_s", 0.10)),
        target_mass_kg=11.8,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=7800.0,
    )


def _build_s5_6_02() -> S5PartBuild:
    """S5.6-02: Enriched 28Si Rod (<50 ppm 29Si) + 6 MHz UHV QCM Monitor on CF40 + Isolation Valve."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # World origin = (420.0, -88.5, 705.0) -> -Y outward from S5.6-01 -Y CF40 port (Y=-88.0, 0.5 mm gap!)
    fl_in = make_cf_flange("CF40", sub_per_side=1, axis="+y", center=(0.0, -6.35, 0.0), material="316LN")
    # All-metal UHV QCM isolation valve body + micrometer bonnet (y = -13..-52)
    valve_body = make_chamfered_box(50.0, 38.0, 68.0, chamfer=2.5, center=(0.0, -32.0, 0.0), name="qcm_uhv_valve", material="316LN")
    valve_wheel = make_cylinder(16.0, 18.0, segments=20, axis="z", center=(0.0, -32.0, 43.5), material="Al 6061")
    # 6 MHz Gold-Electrode Quartz Crystal Microbalance (QCM) Sensor Head + Oscillator Box (y = -52..-116)
    fl_qcm = make_cf_flange("CF40", sub_per_side=1, axis="-y", center=(0.0, -57.6, 0.0), material="316LN")
    qcm_tube = make_tube(11.0, 15.0, 34.0, segments=24, axis="y", center=(0.0, -81.0, 0.0), name="qcm_6mhz_barrel", material="316LN")
    qcm_osc = make_chamfered_box(36.0, 22.0, 36.0, chamfer=2.0, center=(0.0, -109.2, 0.0), name="qcm_oscillator_box", material="Al 6061")
    # Sealed companion <50 ppm 29Si enriched 28Si spare rod storage canister on +X clip bracket (OBS-121 tied!)
    rod_clip = make_box(5.8, 16.0, 18.0, center=(28.0, -32.0, 0.0), name="si28_rod_clip_bracket", material="316LN")
    rod_can = make_cylinder(9.0, 62.0, segments=20, axis="z", center=(40.0, -32.0, 0.0), name="si28_spare_rod_canister", material="316LN")

    shells.extend([fl_in, valve_body, valve_wheel, fl_qcm, qcm_tube, qcm_osc, rod_clip, rod_can])
    step_shells.extend([
        make_cylinder(34.75, 12.7, segments=12, axis="y", center=(0.0, -6.35, 0.0)),
        make_box(50.0, 38.0, 68.0, center=(0.0, -32.0, 0.0)),
        make_cylinder(18.0, 56.0, segments=12, axis="y", center=(0.0, -92.0, 0.0)),
    ])

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(0.0, -6.35, 0.0), rotate=(-90.0, 0.0, 0.0), comment="Mating CF40 flange on S5.6-01 -Y port"),
        ScadFeature("add_box", {"dx": 50.0, "dy": 38.0, "dz": 68.0}, translate=(0.0, -32.0, 0.0), comment="All-metal UHV QCM isolation valve"),
        ScadFeature("add_tube", {"od": 30.0, "id": 22.0, "h": 34.0}, translate=(0.0, -81.0, 0.0), rotate=(90.0, 0.0, 0.0), comment="6 MHz QCM water-cooled sensor head"),
        ScadFeature("add_cylinder", {"d": 18.0, "h": 62.0}, translate=(36.0, -32.0, 0.0), comment="Enriched 28Si (<50 ppm 29Si) feedstock rod canister"),
    ])

    mesh = merge_solids(shells, name="S5.6-02", material="316LN")
    step_mesh = merge_solids(step_shells, name="S5.6-02_step", material="316LN")
    design = make_part_design_from_bom(
        "S5.6-02",
        design_tier="CUSTOM_FULL",
        material="316LN",
        temp_k=300.0,
        surface_finish_ra_um=0.4,
        world_origin_mm=(LOADLOCK_CENTER_X_MM, -88.5, 705.0),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            make_cf_port_interface("CF40", "mbe_qcm_cf40_mate", (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), mating_part_id="S5.6-01"),
            PortInterface("qcm_6mhz_bnc", "rf", (0.0, -120.2, 0.0), (0.0, -1.0, 0.0), "BNC 6 MHz Oscillator", mating_part_id="S7.3-01"),
        ),
        dimensions=(
            DimensionCallout("ASSY_LEN", 120.2, 0.4, -0.4, view="right"),
            DimensionCallout("VALVE_H", 86.5, 0.3, -0.3, view="front"),
            DimensionCallout("CF40_OD", 69.5, 0.1, -0.1, prefix="Ø", view="front"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.08, diameter_zone=True, datum_primary="A", feature_note="QCM sensor head axis to CF40 flange"),
        ),
        notes=(
            "Exp139 S5.6-02: 6 MHz gold-electrode QCM real-time thickness monitor (+/-0.3 nm @ 8.0 nm) + UHV isolation valve.",
            "Includes enriched 28Si (<50 ppm 29Si, ~5 g -> >1,000 wafers) feedstock rod; Exp139 target mass 3.4 kg.",
        ),
        scad_params=(("qcm_freq_MHz", 6.0), ("cap_tol_nm", 0.3), ("si29_ppm_max", 50)),
        target_mass_kg=3.4,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=7800.0,
    )


def _build_s5_6_03() -> S5PartBuild:
    """S5.6-03: Load-Lock 345 C Pyrolytic-BN Radiative Heater & 5% H2/N2 Forming-Gas Leak-Valve Manifold."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # World origin = (420.0, +88.5, 675.0) -> +Y outward from S5.6-01 +Y CF40 port (Y=+88.0, 0.5 mm gap!)
    fl_in = make_cf_flange("CF40", sub_per_side=1, axis="-y", center=(0.0, 6.35, 0.0), material="316LN")
    # 316L VAR cross-manifold body housing PBN radiative heater feedthrough & forming-gas injection
    mani_body = make_chamfered_box(54.0, 50.0, 68.0, chamfer=2.5, center=(0.0, 38.0, 0.0), name="pbn_fg_manifold_body", material="316L")
    # Pyrolytic-BN (PBN) radiative heater ceramic high-current + Type-K TC top feedthrough turret
    pbn_collar = make_cf_flange("CF40", sub_per_side=1, axis="+z", center=(0.0, 38.0, 40.5), material="316L")
    pbn_ins_1 = make_cylinder(6.5, 22.0, segments=16, axis="z", center=(-10.0, 38.0, 58.0), material="PBN")
    pbn_ins_2 = make_cylinder(6.5, 22.0, segments=16, axis="z", center=(10.0, 38.0, 58.0), material="PBN")
    # Precision all-metal sapphire-seat UHV leak valve (+Y end, y = 63..122) with vernier micrometer dial
    leak_body = make_cylinder(22.0, 32.0, segments=24, axis="y", center=(0.0, 79.2, 0.0), name="fg_sapphire_leak_valve", material="316L")
    vernier_dial = make_cylinder(25.0, 24.0, segments=24, axis="y", center=(0.0, 108.0, 0.0), name="fg_leak_vernier", material="Al 6061")
    # 5% H2/N2 Forming-Gas 1/4" VCR inlet stub + ISO 10156 flow-limiting orifice block (-X local -> +X/+Y world)
    vcr_inlet = make_cylinder(9.5, 32.0, segments=16, axis="-x", center=(-43.2, 38.0, -10.0), name="fg_h2_n2_vcr_orifice", material="316L")

    shells.extend([fl_in, mani_body, pbn_collar, pbn_ins_1, pbn_ins_2, leak_body, vernier_dial, vcr_inlet])
    step_shells.extend([
        make_cylinder(34.75, 12.7, segments=12, axis="y", center=(0.0, 6.35, 0.0)),
        make_box(54.0, 50.0, 68.0, center=(0.0, 38.0, 0.0)),
        make_cylinder(25.0, 56.0, segments=12, axis="y", center=(0.0, 92.0, 0.0)),
        make_cylinder(34.75, 28.0, segments=12, axis="z", center=(0.0, 38.0, 52.0)),
    ])

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(0.0, 6.35, 0.0), rotate=(90.0, 0.0, 0.0), comment="Mating CF40 flange on S5.6-01 310 deg port"),
        ScadFeature("add_box", {"dx": 54.0, "dy": 50.0, "dz": 68.0}, translate=(0.0, 38.0, 0.0), comment="316L VAR PBN heater & forming-gas manifold"),
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(0.0, 38.0, 40.5), comment="Top CF40 345 C PBN heater power/TC feedthrough"),
        ScadFeature("add_cylinder", {"d": 50.0, "h": 56.0}, translate=(0.0, 92.0, 0.0), rotate=(90.0, 0.0, 0.0), comment="Precision sapphire-seat 5% H2/N2 leak valve"),
    ])

    mesh = merge_solids(shells, name="S5.6-03", material="316L")
    step_mesh = merge_solids(step_shells, name="S5.6-03_step", material="316L")
    pux, puy, _ = radial_vec(S56_PBN_AZ_DEG)
    design = make_part_design_from_bom(
        "S5.6-03",
        design_tier="CUSTOM_FULL",
        material="316L",
        temp_k=618.15,
        surface_finish_ra_um=0.4,
        world_origin_mm=(round(LOADLOCK_CENTER_X_MM + 88.5 * pux, 4), round(88.5 * puy, 4), 585.5 + S56_PBN_Z_LOC_MM),
        world_rotation_deg=(0.0, 0.0, S56_PBN_AZ_DEG - 90.0),
        ports=(
            make_cf_port_interface("CF40", "mbe_pbn_cf40_mate", (0.0, 0.0, 0.0), (0.0, -1.0, 0.0), mating_part_id="S5.6-01"),
            PortInterface("forming_gas_5pct_in", "gas", (-59.2, 38.0, -10.0), (-1.0, 0.0, 0.0), "1/4 in VCR 5% H2/N2 ISO 10156", mating_part_id="S7.SAFETY-06"),
            PortInterface("pbn_150w_power_tc", "electrical", (0.0, 38.0, 69.0), (0.0, 0.0, 1.0), "150 W PBN + Type-K PID (+/-2 C)", mating_part_id="S7.4-01"),
        ),
        dimensions=(
            DimensionCallout("ASSY_Y", 120.0, 0.4, -0.4, view="right"),
            DimensionCallout("ASSY_Z", 103.0, 0.4, -0.4, view="front"),
            DimensionCallout("CF40_OD", 69.5, 0.1, -0.1, prefix="Ø", view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.03, datum_primary="", feature_note="CF40 VAR vacuum manifold knife-edge"),
        ),
        notes=(
            "Exp139 S5.6-03: 345 C +/-2 C (150 W) pyrolytic-BN radiative substrate heater + 350 C / 15 min 5% H2/N2 FG/H manifold.",
            "Route C passivation achieves S_eps=0.390 ueV/rtHz (F_ff=97.70%); ISO 10156 non-flammable gas orifice; target mass 4.2 kg.",
        ),
        scad_params=(("t_epi_C", 345.0), ("t_fg_C", 350.0), ("heater_power_W", 150.0)),
        target_mass_kg=4.2,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=7800.0,
    )


def _build_s5_6_04() -> S5PartBuild:
    """S5.6-04: Dedicated 80 L/s Compact MBE Differential TMP + ZrVFe NEG Cartridge Package."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # World origin = (514.5, 0.0, 710.0) -> +X outward from S5.6-01 +X CF63 port (X=514.0, 0.5 mm gap!)
    # Clears S5.1-04 transfer arm (Z_max=576.0) by >= 36 mm (S5.6-04 Z_min = 612.0)!
    fl_in = make_cf_flange("CF63", sub_per_side=1, axis="-x", center=(8.75, 0.0, 0.0), material="316LN")
    tee_x = make_tube(31.5, 34.5, 76.0, segments=28, axis="x", center=(55.6, 0.0, 0.0), material="316LN")
    tee_z = make_tube(31.5, 34.5, 58.0, segments=28, axis="z", center=(72.0, 0.0, 0.0), material="316LN")
    # Upper ZrVFe St172 NEG Cartridge Module (z_loc = +29..+112 -> Z = [739, 822])
    fl_neg = make_cf_flange("CF63", sub_per_side=1, axis="+z", center=(72.0, 0.0, 38.0), material="316LN")
    neg_body = make_tube(31.0, 38.0, 56.0, segments=28, axis="z", center=(72.0, 0.0, 75.0), name="mbe_zrvfe_neg_cartridge", material="316LN")
    neg_cap = make_cylinder(24.0, 12.0, segments=20, axis="z", center=(72.0, 0.0, 109.2), name="mbe_neg_heater_cap", material="Al 6061")
    # Lower 80 L/s Compact HiPace-80 Class Differential TMP (z_loc = -98..-29 -> Z = [612, 681])
    fl_tmp = make_cf_flange("CF63", sub_per_side=1, axis="-z", center=(72.0, 0.0, -38.0), material="316LN")
    tmp80_prof = [
        (0.0, -98.0), (38.0, -98.0), (41.0, -90.0), (41.0, -76.0), (37.0, -74.0),
        (41.0, -68.0), (41.0, -56.0), (38.0, -47.0), (31.5, -47.0), (31.5, -62.0),
        (14.0, -68.0), (14.0, -88.0), (0.0, -88.0),
    ]
    tmp80_body = make_revolved_profile(tmp80_prof, segments=28, axis="z", center=(72.0, 0.0, 0.0), name="mbe_hipace80_tmp", material="Al 6061")
    kf16_stub = make_cylinder(12.0, 22.0, segments=16, axis="+x", center=(122.0, 0.0, -82.0), material="316LN")

    shells.extend([fl_in, tee_x, tee_z, fl_neg, neg_body, neg_cap, fl_tmp, tmp80_body, kf16_stub])
    step_shells.extend([
        make_cylinder(56.75, 17.5, segments=16, axis="x", center=(8.75, 0.0, 0.0)),
        make_cylinder(34.5, 76.0, segments=12, axis="x", center=(55.6, 0.0, 0.0)),
        make_cylinder(56.75, 108.0, segments=16, axis="z", center=(72.0, 0.0, 58.0)),
        make_cylinder(41.0, 69.0, segments=16, axis="z", center=(72.0, 0.0, -63.5)),
    ])

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF63"}, translate=(8.75, 0.0, 0.0), rotate=(0.0, -90.0, 0.0), comment="Mating CF63 flange on S5.6-01 +X port"),
        ScadFeature("add_tube", {"od": 69.0, "id": 63.0, "h": 76.0}, translate=(55.6, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="CF63 MBE differential pumping tee"),
        ScadFeature("add_tube", {"od": 76.0, "id": 62.0, "h": 56.0}, translate=(72.0, 0.0, 75.0), comment="ZrVFe St172 NEG cartridge chamber"),
        ScadFeature("add_cylinder", {"d": 82.0, "h": 51.0}, translate=(72.0, 0.0, -72.5), comment="80 L/s compact HiPace-80 class TMP"),
    ])

    mesh = merge_solids(shells, name="S5.6-04", material="Al 6061")
    step_mesh = merge_solids(step_shells, name="S5.6-04_step", material="Al 6061")
    design = make_part_design_from_bom(
        "S5.6-04",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        temp_k=300.0,
        surface_finish_ra_um=1.6,
        world_origin_mm=(514.5, 0.0, 710.0),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            make_cf_port_interface("CF63", "mbe_cf63_inlet", (0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), mating_part_id="S5.6-01"),
            PortInterface("kf16_backing_out", "vacuum", (133.0, 0.0, -82.0), (1.0, 0.0, 0.0), "ISO-KF16 Foreline", mating_part_id="S5.2-03", bore_mm=16.0),
            PortInterface("neg_activation_pwr", "electrical", (72.0, 0.0, 115.2), (0.0, 0.0, 1.0), "NEG Activation Heater", mating_part_id="S7.4-01"),
        ),
        dimensions=(
            DimensionCallout("OVERALL_X", 133.0, 0.5, -0.5, view="front"),
            DimensionCallout("OVERALL_Z", 213.2, 0.5, -0.5, view="front"),
            DimensionCallout("TMP80_OD", 82.0, 0.3, -0.3, prefix="Ø", view="top"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.12, diameter_zone=True, datum_primary="A", feature_note="TMP/NEG vertical axis to CF63 inlet flange"),
        ),
        notes=(
            "Exp139 S5.6-04: Dedicated 80 L/s compact differential TMP + ZrVFe NEG cartridge (1.5e-10 Torr recovery after FG/H).",
            "Isolated from 20 mK DR chamber via all-metal VAT gate valve (0.00 uW cryo leak); Exp139 target mass 3.0 kg.",
        ),
        scad_params=(("tmp_speed_L_s", 80.0), ("p_base_torr", 1.5e-10), ("tmp_od_mm", 82.0)),
        target_mass_kg=3.0,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=3600.0,
    )


def build_s5_optics_mbe_parts() -> dict[str, S5PartBuild]:
    """Build all 12 flash anneal, 808 nm laser optics & 28Si LT-MBE S5 parts."""
    builders = (
        ("S5.3-01", _build_s5_3_01),
        ("S5.3-02", _build_s5_3_02),
        ("S5.3-03", _build_s5_3_03),
        ("S5.3-04", _build_s5_3_04),
        ("S5.5-01", _build_s5_5_01),
        ("S5.5-02", _build_s5_5_02),
        ("S5.5-03", _build_s5_5_03),
        ("S5.5-04", _build_s5_5_04),
        ("S5.6-01", _build_s5_6_01),
        ("S5.6-02", _build_s5_6_02),
        ("S5.6-03", _build_s5_6_03),
        ("S5.6-04", _build_s5_6_04),
    )
    return {pid: fn() for pid, fn in builders}


__all__ = [
    "S5_OPTICS_MBE_PART_IDS",
    "build_s5_optics_mbe_parts",
    "build_s5_parts",
    "export_all",
]


if __name__ == "__main__":
    summary = export_all()
    print(
        f"S5 exported: {summary['physical_part_count']}/23 parts | "
        f"watertight={summary['all_watertight']} | valid={summary['all_artifacts_valid']} | "
        f"clashes={summary['intra_subsystem_clash_audit']['solid_clashes']} | "
        f"mass={summary['total_mass_kg']:.2f} kg"
    )
