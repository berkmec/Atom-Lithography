"""S5 UHV Main Chamber, Bakeout Jacket, Load-Lock, Pumps & Wafer Handling CAD (WP-M3).

Implements 11 of the 23 physical S5 BOM parts using the pure-Python watertight
CAD kernel (``hardware.cad_parts.core``):
- ``S5.1-01``: 316LN electropolished UHV main chamber (R_in=182/R_out=192 mm, V=34.91 L)
  with 16 welded ISO 3669 CF400/CF250/CF100/CF63/CF40 knife-edge ports & bolt circles.
- ``S5.1-02``: Upper CF250 ion-column adapter flange & 4-zone 150 C removable
  fiberglass/silicone UHV bakeout thermal jacket shells.
- ``S5.1-03``: Quick-access CF100 load-lock pre-chamber (+X), VAT all-metal CF100 gate
  valve body, operator -Y viewport door, N2 vent port & decoupled floor stand.
- ``S5.1-04``: True 500 mm-stroke magnetically coupled UHV linear/rotary transfer arm
  with Ti-6Al-4V two-prong wafer fork (reconciling legacy CAD v6.0 200 mm stub).
- ``S5.1-05``: UHV service hardware kit tray with representative OFHC Cu CF100/CF63/CF40
  knife-edge gaskets, silver-plated 12-point bolt rack, CF40 angle valves & viewport.
- ``S5.2-01``: 300 L/s mag-lev turbomolecular pump (HiPace 300 class) + CF100 18-conv
  edge-welded vibration isolation bellows + pumping tee & floor frame (-Y).
- ``S5.2-02``: 75 L/s VacIon StarCell ion pump + integrated TSP cartridge flange (-Y top).
- ``S5.2-03``: Oil-free dry scroll roughing/backing pump (15 m^3/h) + KF25 backstream trap.
- ``S5.2-04``: Full-range Pirani/cold-cathode gauges, 200 amu quadrupole RGA, all-metal
  angle valve & CF40 gauge cross manifold (225 deg lower port).
- ``S5.4-01``: Isotopically enriched 28Si/29Si (f=1%) epitaxial working wafer (Dia 50 mm
  SEMI M1 flats + scribe frame, diced from Dia 100 mm BOM stock to fit Dia 150 mm bore).
- ``S5.4-03``: N2-purged FOUP/SMIF wafer transfer pod & dry cleanroom storage cabinet.

Global Machine Coordinate System (locked to ``research/atom_lithography_machine/cad/params.py``):
- Floor: ``Z = 0.0 mm``
- Wafer active top plane: ``Z_WAFER = 500.0 mm`` (``z_loc = Z - 500.0``)
- ``+Z``: S1/S2 ion column; ``-Z``: S4 active table / granite base
- ``+Y``: S5.5 808 nm flash annealing CF63 sapphire viewport (clear space for S7.SAFETY-02)
- ``+X``: S5.1-03 load-lock + S5.1-04 500 mm transfer arm + S5.6 +Z MBE capper
- ``-Y``: S5.2-01/02/03 main UHV pumping station
- ``-X``: S6 cryo-bridge CF63 bellows & 20 mK DR tower (kept strictly clear)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

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
    cold_dimension_mm,
    export_part_artifacts,
    integrated_thermal_contraction,
    list_physical_part_ids,
    make_bellows,
    make_box,
    make_cf_flange,
    make_cf_port_interface,
    make_cf_viewport,
    make_cf_weld_neck,
    make_chamfered_box,
    make_cylinder,
    make_frustum,
    make_part_design_from_bom,
    make_plate_with_holes,
    make_rect_plate_with_features,
    make_revolved_profile,
    make_tube,
    merge_solids,
    split_shells,
    transform_mesh,
    verify_watertight,
)

# ---------------------------------------------------------------------------
# Locked Machine Constants & Explicit BOM-vs-CAD Reconciliation Ledger
# ---------------------------------------------------------------------------
Z_WAFER_MM: float = 500.0
CHAMBER_R_IN_MM: float = 182.0
CHAMBER_R_OUT_MM: float = 192.0
CHAMBER_WALL_MM: float = 10.0
MAGNET_FORMER_OD_MM: float = 352.0
MAGNET_BORE_ID_MM: float = 150.0
LOADLOCK_CENTER_X_MM: float = 420.0
PUMP_STATION_Y_MM: float = -425.0
LOADLOCK_OPT_ELEV_DEG: float = 36.0
LOADLOCK_S55_T_FACE_MM: float = 185.0
LOADLOCK_S53_RTA_AZ_DEG: float = 316.0
LOADLOCK_S53_RTA_T_FACE_MM: float = 220.0
LOADLOCK_S53_PYRO_AZ_DEG: float = 238.0
LOADLOCK_S53_PYRO_T_FACE_MM: float = 190.0
LOADLOCK_SHUTTER_AZ_DEG: float = 56.0
LOADLOCK_SHUTTER_Z_LOC_MM: float = -40.0
LOADLOCK_SHUTTER_R_FACE_MM: float = 155.0
DEFAULT_S5_OUT_DIR: Path = REPO_ROOT / "hardware" / "cad_parts" / "out" / "S5"

S5_UHV_PUMPS_PART_IDS: tuple[str, ...] = (
    "S5.1-01",
    "S5.1-02",
    "S5.1-03",
    "S5.1-04",
    "S5.1-05",
    "S5.2-01",
    "S5.2-02",
    "S5.2-03",
    "S5.2-04",
    "S5.4-01",
    "S5.4-03",
)

S5_RECONCILIATIONS: dict[str, dict[str, Any]] = {
    "S5.1-01": {
        "field": "UHV main chamber inner radius & volume",
        "bom_v7_spec": "r = 175 mm (~34 L, Exp80 s=0.5 envelope)",
        "cad_v8_adopted": "R_in = 182.0 mm, R_out = 192.0 mm, H_in = 335.5 mm, V_in = 34.91 L",
        "engineering_rationale": (
            "Exp125 8-coil cryo-magnet outer former has OD = 352.0 mm (R = 176.0 mm). "
            "A BOM r = 175 mm wall would interfere by 1.0 mm; R_in = 182.0 mm provides "
            "6.0 mm radial vacuum clearance (182 - 176 = 6.0 mm) while keeping "
            "V_in / V_ref = 34.91 / 269.39 = 0.1296 within Exp80 BC4 (1/8 +/- 5%)."
        ),
    },
    "S5.1-04": {
        "field": "Magnetically coupled UHV transfer arm linear stroke",
        "bom_v7_spec": "500 mm linear stroke + 360 deg rotary with Ti-6Al-4V wafer fork",
        "cad_v8_adopted": (
            "Full 518.0 mm active stroke (570 mm magnetic guide tube, CF100 fork parking spool "
            "ID=98 mm clearing 68 mm Ti-6Al-4V yoke, X=510.5..1158.5 mm reaching X=-11.5 mm past "
            "wafer center X=0) replacing legacy CAD v6.0 200 mm stub."
        ),
        "engineering_rationale": (
            "Load-lock center (X=420 mm) to main chamber wafer chuck (X=0 mm) requires "
            "506.5 mm travel from parked fork center (X=506.5 mm); 518.0 mm unobstructed shuttle "
            "stroke reaches X=-11.5 mm (11.5 mm past wafer center) while staying <=1158.5 mm "
            "(>=21.5 mm clear of Rack Bay 1 at X=1180 mm)."
        ),
    },
    "S5.4-01": {
        "field": "28Si/29Si epitaxial wafer diameter",
        "bom_v7_spec": "25x Dia 100 mm stock epitaxial wafers (100 nm epi, f=1.0% 29Si)",
        "cad_v8_adopted": (
            "Dia 50.0 mm x 0.775 mm laser-diced working wafer (SEMI M1 primary/secondary "
            "flats) seated at Z_WAFER = 500.00 mm on 80x80 mm AlN carrier."
        ),
        "engineering_rationale": (
            "An undiced Dia 100 mm wafer with carrier frame cannot fit inside the "
            "Dia 150.0 mm Exp125 magnet clear bore or pass through the CF100 load-lock "
            "gate valve bore (Dia 101.6 mm). Laser-dicing Dia 100 mm CVD stock to "
            "Dia 50.0 mm working wafers yields 80x80 mm carrier diagonal = 113.14 mm "
            "(18.43 mm radial clearance to Dia 150 mm bore)."
        ),
    },
}


# ---------------------------------------------------------------------------
# Shared Part Build Container & Geometry Helpers
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class S5PartBuild:
    """Complete mechanical definition and verified watertight geometry for one S5 part."""

    design: PartDesign
    mesh: SolidMesh
    scad_features: tuple[ScadFeature, ...]
    step_mesh: SolidMesh | None = None
    density_kg_m3: float | None = None
    reconciliation: dict[str, Any] | None = None


def inclined_vec(az_deg: float, elev_deg: float) -> tuple[float, float, float]:
    """Return unit 3D ray vector at azimuth ``az_deg`` and elevation ``elev_deg`` above XY."""
    az = math.radians(az_deg)
    el = math.radians(elev_deg)
    ce = math.cos(el)
    return (ce * math.cos(az), ce * math.sin(az), math.sin(el))


def inclined_pos(dist_mm: float, az_deg: float, elev_deg: float) -> tuple[float, float, float]:
    """Return 3D point along ``inclined_vec(az_deg, elev_deg)`` at distance ``dist_mm``."""
    ux, uy, uz = inclined_vec(az_deg, elev_deg)
    return (round(dist_mm * ux, 4), round(dist_mm * uy, 4), round(dist_mm * uz, 4))


def radial_vec(az_deg: float) -> tuple[float, float, float]:
    """Return unit XY radial direction vector at azimuth ``az_deg`` (0=+X, 90=+Y)."""
    rad = math.radians(az_deg)
    return (math.cos(rad), math.sin(rad), 0.0)


def radial_pos(r_mm: float, az_deg: float, z_mm: float = 0.0) -> tuple[float, float, float]:
    """Return 3D cylindrical point ``(r cos(az), r sin(az), z)``."""
    ux, uy, _ = radial_vec(az_deg)
    return (round(r_mm * ux, 4), round(r_mm * uy, 4), round(z_mm, 4))


def make_arc_sector_solid(
    r_in: float,
    r_out: float,
    height: float,
    deg0: float,
    deg1: float,
    *,
    arc_segments: int = 16,
    center_z: float = 0.0,
    name: str = "arc_sector",
    material: str = "316LN",
) -> SolidMesh:
    """Build a watertight extruded circular-sector curved wall shell."""
    if deg1 <= deg0:
        raise ValueError(f"deg1 ({deg1}) must be > deg0 ({deg0})")
    n = max(4, int(arc_segments))
    angles = [math.radians(deg0 + (deg1 - deg0) * i / n) for i in range(n + 1)]
    outer_pts = [(r_out * math.cos(a), r_out * math.sin(a)) for a in angles]
    inner_pts = [(r_in * math.cos(a), r_in * math.sin(a)) for a in reversed(angles)]
    poly = outer_pts + inner_pts
    return make_plate_with_holes(
        outer_poly_2d=poly,
        holes_2d=(),
        thickness=height,
        axis="z",
        center=(0.0, 0.0, center_z),
        name=name,
        material=material,
    )


def make_hollow_enclosure(
    dx: float,
    dy: float,
    dz: float,
    wall: float,
    *,
    open_faces: Sequence[str] = (),
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str = "enclosure",
    material: str = "316LN",
) -> SolidMesh:
    """Build a watertight hollow box from non-overlapping rectangular wall slabs."""
    cx, cy, cz = float(center[0]), float(center[1]), float(center[2])
    opens = {f.lower() for f in open_faces}
    w = min(wall, 0.35 * min(dx, dy, dz))
    gap = 0.04  # micro-clearance between separate wall shells (clean non-overlapping shells)
    slabs: list[SolidMesh] = []

    if "-z" not in opens:
        slabs.append(make_box(dx, dy, w, center=(cx, cy, cz - 0.5 * dz + 0.5 * w), material=material))
    if "+z" not in opens:
        slabs.append(make_box(dx, dy, w, center=(cx, cy, cz + 0.5 * dz - 0.5 * w), material=material))

    z_lo = cz - 0.5 * dz + (0.0 if "-z" in opens else w + gap)
    z_hi = cz + 0.5 * dz - (0.0 if "+z" in opens else w + gap)
    hz = max(z_hi - z_lo, 0.5)
    zc = 0.5 * (z_lo + z_hi)

    if "-x" not in opens:
        slabs.append(make_box(w, dy, hz, center=(cx - 0.5 * dx + 0.5 * w, cy, zc), material=material))
    if "+x" not in opens:
        slabs.append(make_box(w, dy, hz, center=(cx + 0.5 * dx - 0.5 * w, cy, zc), material=material))

    x_lo = cx - 0.5 * dx + (0.0 if "-x" in opens else w + gap)
    x_hi = cx + 0.5 * dx - (0.0 if "+x" in opens else w + gap)
    hx = max(x_hi - x_lo, 0.5)
    xc = 0.5 * (x_lo + x_hi)

    if "-y" not in opens:
        slabs.append(make_box(hx, w, hz, center=(xc, cy - 0.5 * dy + 0.5 * w, zc), material=material))
    if "+y" not in opens:
        slabs.append(make_box(hx, w, hz, center=(xc, cy + 0.5 * dy - 0.5 * w, zc), material=material))

    return merge_solids(slabs, name=name, material=material)


def make_bolt_solid(
    shank_d: float,
    shank_l: float,
    head_d: float,
    head_h: float,
    *,
    center: Sequence[float] = (0.0, 0.0, 0.0),
    axis: str = "z",
    name: str = "bolt",
    material: str = "316LN",
) -> SolidMesh:
    """Build a watertight 12-point flange bolt solid (revolved stepped head + shank)."""
    r_sh = 0.5 * shank_d
    r_hd = 0.5 * head_d
    r_fl = 1.18 * r_hd
    h_fl = 0.28 * head_h
    z0 = -0.5 * (shank_l + head_h)
    z_split = z0 + shank_l
    z_top = z_split + head_h
    prof = [
        (0.0, z0),
        (0.85 * r_sh, z0),
        (r_sh, z0 + 0.8),
        (r_sh, z_split),
        (r_fl, z_split),
        (r_fl, z_split + h_fl),
        (r_hd, z_split + h_fl),
        (r_hd, z_top - 0.6),
        (0.85 * r_hd, z_top),
        (0.0, z_top),
    ]
    return make_revolved_profile(
        prof, segments=12, axis=axis, center=center, name=name, material=material
    )


# ---------------------------------------------------------------------------
# Chamber Port Schedule (Single Source of Truth shared with s5_optics_mbe.py)
# ---------------------------------------------------------------------------
# Each entry: (name, cf_size, az_deg, z_loc_mm, r_face_mm, mating_part_id, bore_override, note)
CHAMBER_RADIAL_PORTS: tuple[tuple[str, str, float, float, float, str, float | None, str], ...] = (
    ("port_loadlock_pos_x", "CF100", 0.0, 0.0, 250.0, "S5.1-03", None, "+X Load-Lock transfer gate port"),
    ("port_pump_neg_y", "CF150", 270.0, 8.0, 260.0, "S5.2-01", None, "-Y CF150 high-conductance TMP & VacIon pumping port (S_eff >= 206 L/s N2)"),
    ("port_cryo_bridge_neg_x", "CF100", 180.0, -6.5, 289.0, "S6.9-02", 76.0, "-X Exp133 OVC CF100 bellows cryo bridge (ID 76 mm for Ø46/52 4K tube & Ø30 rod, clears S3.2-05)"),
    ("port_ibic_ft_45", "CF63", 45.0, -105.0, 245.0, "S3.2-05", None, "45 deg Z=395 IBIC 32-coax feedthrough port"),
    ("port_ibic_ft_315", "CF63", 315.0, -105.0, 245.0, "S3.2-05", None, "315 deg Z=395 IBIC 32-coax feedthrough port"),
    ("port_interf_x_0", "CF40", 0.0, -133.0, 240.0, "S4.4-04", 28.0, "0 deg Z=367 X-axis 632.8 nm interferometer AR CF40 viewport"),
    ("port_interf_y_90", "CF40", 90.0, -133.0, 240.0, "S4.4-04", 28.0, "90 deg Z=367 Y-axis 632.8 nm interferometer AR CF40 viewport"),
    ("port_interf_z_270", "CF40", 270.0, -133.0, 240.0, "S4.4-04", 28.0, "270 deg Z=367 Z-axis 632.8 nm interferometer AR CF40 viewport"),
    ("port_gauge_rga_225", "CF40", 225.0, -105.0, 245.0, "S5.2-04", None, "225 deg Z=395 Pirani/CC/RGA manifold port"),
    ("port_fiducial_50", "CF40", 50.0, 9.0, 240.0, "S4.5-02", 32.0, "50 deg Z=509 dark-field fiducial microscope CF40 optical viewport (mating S4.5-02 R=240.5)"),
)


# ---------------------------------------------------------------------------
# Part Builders (11 parts in s5_uhv_pumps.py)
# ---------------------------------------------------------------------------
def _build_s5_1_01() -> S5PartBuild:
    """S5.1-01: 316LN Electropolished UHV Main Chamber with 13 Fully-Bored ISO 3669 CF Flanges."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []
    ports: list[PortInterface] = []

    # 1. Bottom CF400 main flange (z_loc = [-240.0, -211.5]) + stepped vacuum baseplate
    fl_bot = make_cf_flange(
        "CF400", bore_id=364.0, sub_per_side=1, axis="-z", center=(0.0, 0.0, -225.75),
        name="s5_cf400_bot", material="316LN",
    )
    shells.append(fl_bot)
    step_shells.append(make_tube(182.0, 228.0, 28.5, segments=24, axis="z", center=(0.0, 0.0, -225.75)))
    ports.append(make_cf_port_interface(
        "CF400", "bottom_cf400_base", (0.0, 0.0, -240.0), (0.0, 0.0, -1.0),
        mating_part_id="S4.2-01", bore_override_mm=364.0,
        notes="Bottom CF400 base seated on S4.2 active isolation table at Z=260 mm",
    ))

    # Stepped internal vacuum baseplate closure (z_loc = [-240.0, -215.5], R=0..181.6)
    base_prof = [
        (0.0, -240.0), (181.6, -240.0), (181.6, -220.0), (168.0, -215.5),
        (68.0, -215.5), (68.0, -219.0), (44.0, -219.0), (44.0, -215.5), (0.0, -215.5),
    ]
    shells.append(make_revolved_profile(base_prof, segments=48, axis="z", name="s5_baseplate", material="316LN"))
    step_shells.append(make_cylinder(181.6, 24.5, segments=20, axis="z", center=(0.0, 0.0, -227.75)))

    # 2. Lower 316LN cylindrical wall — TRUE open port cutouts at Z=367 (-133) & Z=395 (-105) & -Y CF150!
    # 2a. Bottom solid ring below lower CF40/CF63 ports (z_loc = [-211.4, -155.0])
    shells.append(make_tube(
        CHAMBER_R_IN_MM, CHAMBER_R_OUT_MM, 56.4, segments=64, axis="z",
        center=(0.0, 0.0, -183.2), name="s5_wall_bot_ring", material="316LN",
    ))
    # 2b. Lower port-belt curved structural pillars (z_loc = [-154.9, -71.5])
    # Leaves open bores for: 0 deg (interf X), 45 deg (IBIC), 90 deg (interf Y),
    # 225 deg (gauge/RGA), 270 deg (interf Z + CF150 pump), 315 deg (IBIC)
    lower_pillar_arcs = (
        ("lo_ene", 10.0, 32.0),
        ("lo_nne", 58.0, 80.0),
        ("lo_nw", 100.0, 215.0),
        ("lo_ssw", 235.0, 242.0),
        ("lo_sse", 298.0, 302.0),
        ("lo_ese", 328.0, 350.0),
    )
    for tag, d0, d1 in lower_pillar_arcs:
        n_seg = max(4, int((d1 - d0) / 4.0))
        shells.append(make_arc_sector_solid(
            CHAMBER_R_IN_MM, CHAMBER_R_OUT_MM, 83.4, d0, d1,
            arc_segments=n_seg, center_z=-113.2, name=f"s5_pillar_{tag}", material="316LN",
        ))
    # 2c. Lower transition ring (z_loc = [-71.4, -60.0], open at 242..298 deg for -Y CF150 pump bore!)
    shells.append(make_arc_sector_solid(
        CHAMBER_R_IN_MM, CHAMBER_R_OUT_MM, 11.4, -62.0, 242.0,
        arc_segments=48, center_z=-65.7, name="s5_wall_lo_trans", material="316LN",
    ))
    step_shells.append(make_tube(
        CHAMBER_R_IN_MM, CHAMBER_R_OUT_MM, 311.4, segments=24, axis="z",
        center=(0.0, 0.0, -55.7), name="s5_wall_step", material="316LN",
    ))

    # 3. Equatorial port-belt structural curved pillars (z_loc = [-59.9, +59.9]) — TRUE open port belt!
    # Open arcs: 0 deg (-19..+19 CF100 LL), 50 deg (38..62 CF40 fiducial),
    # 180 deg (161..199 CF100 cryo-bridge), 270 deg (242..298 CF150 pump)
    pillar_arcs = (
        ("ene", 19.0, 38.0),
        ("nw", 62.0, 161.0),
        ("sw", 199.0, 242.0),
        ("ese", 298.0, 341.0),
    )
    for tag, d0, d1 in pillar_arcs:
        n_seg = max(6, int((d1 - d0) / 4.0))
        shells.append(make_arc_sector_solid(
            CHAMBER_R_IN_MM, CHAMBER_R_OUT_MM, 119.8, d0, d1,
            arc_segments=n_seg, center_z=0.0, name=f"s5_pillar_{tag}", material="316LN",
        ))

    # 4. Upper cylindrical wall (z_loc = [+60.0, +99.9]) — open at 38..62 deg (fiducial) & 242..298 deg (CF150 pump)!
    upper_pillar_arcs = (
        ("up_nw", 62.0, 242.0),
        ("up_se", 298.0, 398.0),
    )
    for tag, d0, d1 in upper_pillar_arcs:
        n_seg = max(12, int((d1 - d0) / 4.0))
        shells.append(make_arc_sector_solid(
            CHAMBER_R_IN_MM, CHAMBER_R_OUT_MM, 39.9, d0, d1,
            arc_segments=n_seg, center_z=79.95, name=f"s5_wall_{tag}", material="316LN",
        ))

    # 5. Top CF400 main service flange (z_loc = [+100.0, +128.5]) + conical reducer + CF250 top port
    fl_top_400 = make_cf_flange(
        "CF400", bore_id=364.0, sub_per_side=1, axis="+z", center=(0.0, 0.0, 114.25),
        name="s5_cf400_top", material="316LN",
    )
    shells.append(fl_top_400)
    step_shells.append(make_tube(182.0, 228.0, 28.5, segments=24, axis="z", center=(0.0, 0.0, 114.25)))
    ports.append(make_cf_port_interface(
        "CF400", "top_cf400_service", (0.0, 0.0, 128.5), (0.0, 0.0, 1.0),
        mating_part_id="S5.1-02", bore_override_mm=364.0,
        notes="Top CF400 split service flange for internal magnet/stage installation",
    ))

    dome_prof = [
        (182.0, 128.6), (192.0, 128.6), (136.0, 143.9), (127.0, 143.9),
    ]
    shells.append(make_revolved_profile(dome_prof, segments=48, axis="z", name="s5_dome_reducer", material="316LN"))
    fl_top_250 = make_cf_flange(
        "CF250", bore_id=254.0, sub_per_side=1, axis="+z", center=(0.0, 0.0, 156.25),
        name="s5_cf250_top", material="316LN",
    )
    shells.append(fl_top_250)
    step_shells.append(make_tube(127.0, 152.5, 24.5, segments=20, axis="z", center=(0.0, 0.0, 156.25)))
    ports.append(make_cf_port_interface(
        "CF250", "top_cf250_column", (0.0, 0.0, 168.5), (0.0, 0.0, 1.0),
        mating_part_id="S5.1-02",
        notes="Top CF250 port mating S5.1-02 ion-column mounting adapter flange at Z=668.5 mm",
    ))

    # SCAD main vessel body + axial flanges
    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF400", "bore_id": 364.0}, translate=(0.0, 0.0, -225.75), rotate=(180.0, 0.0, 0.0), comment="Bottom CF400 main flange"),
        ScadFeature("add_cylinder", {"d": 363.2, "h": 24.5}, translate=(0.0, 0.0, -227.75), comment="Stepped vacuum baseplate"),
        ScadFeature("add_tube", {"od": 384.0, "id": 364.0, "h": 311.4}, translate=(0.0, 0.0, -55.7), comment="316LN main vessel shell (R_in=182, R_out=192 mm)"),
        ScadFeature("add_cf_flange", {"size": "CF400", "bore_id": 364.0}, translate=(0.0, 0.0, 114.25), comment="Top CF400 service flange"),
        ScadFeature("add_cf_flange", {"size": "CF250", "bore_id": 254.0}, translate=(0.0, 0.0, 156.25), comment="Top CF250 column adapter flange"),
    ])

    # 6. 13 Welded Radial ISO 3669 CF Port Nozzles (real knife-edge + bolt circles!)
    for pname, sz, az, z_loc, r_face, mate_id, bore_ov, note in CHAMBER_RADIAL_PORTS:
        sp = CF_SPECS[sz]
        ux, uy, _ = radial_vec(az)
        r_fl_center = r_face - 0.5 * sp.thickness_mm
        neck_len = r_face - sp.thickness_mm - (CHAMBER_R_OUT_MM + 0.2)
        c_pt = (r_fl_center * ux, r_fl_center * uy, z_loc)
        sub = 1 if sp.dn >= 63 else 2
        nozzle = make_cf_weld_neck(
            sz, neck_length=neck_len, tube_id=bore_ov, sub_per_side=sub,
            axis=(ux, uy, 0.0), center=c_pt, name=f"s5_{pname}", material="316LN",
        )
        shells.append(nozzle)
        # Compact low-poly STEP shell preserving exact flange OD & face position
        step_shells.append(make_cylinder(
            0.5 * sp.od_mm, sp.thickness_mm, segments=12, axis=(ux, uy, 0.0), center=c_pt,
        ))
        face_pt = (round(r_face * ux, 3), round(r_face * uy, 3), round(z_loc, 3))
        ports.append(make_cf_port_interface(
            sz, pname, face_pt, (ux, uy, 0.0),
            mating_part_id=mate_id, bore_override_mm=bore_ov, notes=note,
        ))
        # OpenSCAD flange + bore cutout
        scad_feats.append(ScadFeature(
            "add_cf_flange", {"size": sz, "bore_id": bore_ov or sp.bore_id_mm},
            translate=(round(c_pt[0], 3), round(c_pt[1], 3), round(z_loc, 3)),
            rotate=(0.0, 90.0, az),
            comment=f"Welded {sz} radial port {pname} ({az:.0f} deg, z_loc={z_loc:.1f})",
        ))
        scad_feats.append(ScadFeature(
            "cut_hole", {"d": bore_ov or sp.bore_id_mm, "h": r_face - CHAMBER_R_IN_MM + 4.0},
            translate=(round(0.5 * (CHAMBER_R_IN_MM + r_face) * ux, 3), round(0.5 * (CHAMBER_R_IN_MM + r_face) * uy, 3), round(z_loc, 3)),
            rotate=(0.0, 90.0, az),
            comment=f"Port bore {pname}",
        ))

    mesh = merge_solids(shells, name="S5.1-01", material="316LN")
    step_mesh = merge_solids(step_shells, name="S5.1-01_step", material="316LN")
    rec = S5_RECONCILIATIONS["S5.1-01"]
    design = make_part_design_from_bom(
        "S5.1-01",
        design_tier="CUSTOM_FULL",
        material="316LN",
        temp_k=300.0,
        surface_finish_ra_um=0.2,
        world_origin_mm=(0.0, 0.0, Z_WAFER_MM),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=tuple(ports),
        dimensions=(
            DimensionCallout("ID_CHAMBER", 364.0, 0.20, -0.20, prefix="Ø", view="top"),
            DimensionCallout("OD_SHELL", 384.0, 0.20, -0.20, prefix="Ø", view="top"),
            DimensionCallout("CF400_OD", 456.0, 0.15, -0.15, prefix="Ø", view="top"),
            DimensionCallout("H_TOTAL", 408.5, 0.25, -0.25, view="front"),
            DimensionCallout("CF250_TOP_Z", 168.5, 0.10, -0.10, view="front", datum_ref="A"),
            DimensionCallout("FLASH_Y_FACE", 295.0, 0.10, -0.10, view="right", datum_ref="B"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.05, datum_primary="", feature_note="CF400/CF250 knife-edge sealing faces"),
            GDTFrame("perpendicularity", 0.10, diameter_zone=True, datum_primary="A", feature_note="Vessel axis B to bottom CF400 datum A"),
            GDTFrame("concentricity", 0.10, diameter_zone=True, datum_primary="B", feature_note="Top CF250 column port to chamber axis"),
            GDTFrame("position", 0.15, diameter_zone=True, datum_primary="A", datum_secondary="B", datum_tertiary="C", feature_note="13x radial CF port axes"),
        ),
        datums=(
            ("A", "BOTTOM CF400 MOUNTING FACE (Z=260.0 MM)"),
            ("B", "MAIN CYLINDER INNER BORE AXIS (Ø364.0 MM)"),
            ("C", "+X LOAD-LOCK CF100 PORT AXIS (AZ=0 DEG)"),
        ),
        notes=(
            "RECONCILIATION: BOM lists r=175 mm (~34 L); adopted CAD R_in=182.0 / R_out=192.0 mm "
            "(V_in=34.91 L, 6.0 mm radial clearance to Exp125 Ø352 mm magnet former, Exp80 BC4 PASS).",
            "Electropolished non-magnetic 316LN (mu_r < 1.005), Ra <= 0.2 um interior, 150 C Stage-1 bakeable.",
            "13 fully-bored ISO 3669 ConFlat flanges (2x CF400, 1x CF250, 1x CF150, 2x CF100, 2x CF63, 5x CF40) with zero occluded radial walls.",
        ),
        scad_params=(
            ("chamber_r_in_mm", CHAMBER_R_IN_MM),
            ("chamber_r_out_mm", CHAMBER_R_OUT_MM),
            ("inner_vol_L", 34.91),
            ("z_wafer_mm", Z_WAFER_MM),
            ("n_cf_ports", 13),
        ),
        target_mass_kg=85.0,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=8000.0, reconciliation=rec,
    )


def _build_s5_1_02() -> S5PartBuild:
    """S5.1-02: Upper CF250->CF100 Column Isolation Gate Valve Adapter (Z=705 mm) & 4-Zone Bakeout Jacket."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # 1. Upper CF250->CF100 Inline All-Metal Column Isolation Gate Valve Assembly (OBS-004 & OBS-005!)
    # Mates S5.1-01 top CF250 at z_loc=+169.0 (Z=669.0 mm) and terminates cleanly in an ISO 3669 CF100
    # sealing flange at z_loc=+205.0 (Z=705.00 mm) mating S1.3-01:lower_cf100 (bore Ø88.0 mm)!
    # Outer CF250 flange bore_id=154.0 mm coaxially seats the inner CF100 (OD=152.0 mm) with 1.0 mm clearance!
    cf250_adapt = make_cf_flange(
        "CF250", bore_id=154.0, sub_per_side=1, axis="-z", center=(0.0, 0.0, 181.25),
        name="s5_cf250_col_adapter", material="316LN",
    )
    # Stepped counterbored CF100 top sealing flange (OD=152, bore=112 at Z=705.00 mm mating S1.3-01;
    # lower counterbore R_in=63.0 mm for Z=[685.2, 704.65] cleanly clears S1.3-04 mu-metal R<=62.0 & S1.5-01 R<=55.0!)
    cf100_col_top = make_revolved_profile(
        [(63.0, 185.2), (76.0, 185.2), (76.0, 205.0), (56.0, 205.0), (56.0, 204.65), (63.0, 204.65)],
        segments=48, axis="z", name="s5_cf100_col_gate_top", material="316LN",
    )
    # Lateral inline column gate-valve blade housing & fail-close pneumatic bonnet along 135 deg (-X/+Y)
    # Positioned strictly within Z=[680, 704.8] <= 705.00 mm (canonical datum!) and outside CF100 OD (R=76)!
    gv_az = 135.0
    gux, guy, _ = radial_vec(gv_az)
    gv_housing = transform_mesh(
        make_chamfered_box(50.0, 96.0, 11.0, chamfer=1.5, name="s5_col_gate_valve_body", material="316LN"),
        rotation_deg=(0.0, 0.0, gv_az),
        translation=(104.0 * gux, 104.0 * guy, 199.3),
    )
    gv_actuator = make_cylinder(
        11.0, 44.0, segments=20, axis=(gux, guy, 0.0),
        center=(176.0 * gux, 176.0 * guy, 193.5),
        name="s5_col_gate_pneumatic_bonnet", material="Al 6061",
    )
    shells.extend([cf250_adapt, cf100_col_top, gv_housing, gv_actuator])
    step_shells.append(make_tube(77.0, 152.5, 24.5, segments=20, axis="z", center=(0.0, 0.0, 181.25)))
    step_shells.append(make_tube(44.0, 76.0, 19.8, segments=16, axis="z", center=(0.0, 0.0, 195.1)))
    step_shells.append(transform_mesh(
        make_box(50.0, 96.0, 11.0), rotation_deg=(0.0, 0.0, gv_az), translation=(104.0 * gux, 104.0 * guy, 199.3),
    ))

    # 2. 4-Zone 150 C Removable Silicone/Fiberglass Bakeout Jacket Clamshell Arcs (R = 195..213 mm)
    # Staged Bakeout Protocol (OBS-122): Stage-1 bare-vessel 150 C bakeout with S3.2/S4.3/S6.3 cryo-PCB
    # cartridge withdrawn via CF400 top service flange; Stage-2 <=80 C mild bakeout with active N2 shield!
    r_jin, r_jout = 195.0, 213.0
    # Zone 1: Lower continuous belt split into two 176 deg clamshells (z_loc = [-207.0, -172.0])
    for tag, d0, d1 in (("z1_a", 2.0, 178.0), ("z1_b", 182.0, 358.0)):
        shells.append(make_arc_sector_solid(
            r_jin, r_jout, 35.0, d0, d1, arc_segments=24, center_z=-189.5,
            name=f"s5_jacket_{tag}", material="PTFE",
        ))
    step_shells.append(make_tube(r_jin, r_jout, 35.0, segments=20, axis="z", center=(0.0, 0.0, -189.5)))

    # Zone 2: Upper removable heater arcs (z_loc = [+80.0, +96.5]), notched cleanly around 50 deg fiducial & -Y CF150 pump!
    for tag, d0, d1 in (("z2_a", 65.0, 236.0), ("z2_b", 304.0, 395.0)):
        shells.append(make_arc_sector_solid(
            r_jin, r_jout, 16.5, d0, d1, arc_segments=20, center_z=88.25,
            name=f"s5_jacket_{tag}", material="PTFE",
        ))
    step_shells.append(make_arc_sector_solid(r_jin, r_jout, 16.5, 65.0, 236.0, arc_segments=12, center_z=88.25))

    # Zone 3: Mid-chamber 3 removable insulated heater panels strictly in port-free azimuths (clears 50 deg fiducial!)
    for tag, d0, d1 in (("z3_nw", 70.0, 154.0), ("z3_sw", 204.0, 236.0), ("z3_ese", 304.0, 336.0)):
        shells.append(make_arc_sector_solid(
            r_jin, r_jout, 114.0, d0, d1, arc_segments=12, center_z=0.0,
            name=f"s5_jacket_{tag}", material="PTFE",
        ))
        step_shells.append(make_arc_sector_solid(
            r_jin, r_jout, 114.0, d0, d1, arc_segments=6, center_z=0.0,
            name=f"s5_jacket_step_{tag}", material="PTFE",
        ))

    # Zone 4: Upper dome thermal collar heater (z_loc = [+130.0, +142.5], R=195..213)
    for tag, d0, d1 in (("z4_a", 2.0, 178.0), ("z4_b", 182.0, 358.0)):
        shells.append(make_arc_sector_solid(
            r_jin, r_jout, 12.5, d0, d1, arc_segments=24, center_z=136.25,
            name=f"s5_jacket_{tag}", material="PTFE",
        ))

    # 4-Zone PID Thermocouple & Heater Power Junction Box mounted on Zone 1 at 315 deg
    jx, jy, _ = radial_pos(229.0, 315.0, -190.0)
    jbox = transform_mesh(
        make_chamfered_box(30.0, 48.0, 32.0, chamfer=2.0, name="s5_bake_pid_box", material="Al 6061"),
        rotation_deg=(0.0, 0.0, 315.0),
        translation=(jx, jy, -190.0),
    )
    shells.append(jbox)
    step_shells.append(transform_mesh(
        make_box(30.0, 48.0, 32.0), rotation_deg=(0.0, 0.0, 315.0), translation=(jx, jy, -190.0),
    ))

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF250", "bore_id": 88.0}, translate=(0.0, 0.0, 177.25), rotate=(180.0, 0.0, 0.0), comment="Upper CF250 column adapter flange (Dia 88 bore)"),
        ScadFeature("add_cf_flange", {"size": "CF100", "bore_id": 88.0}, translate=(0.0, 0.0, 195.1), comment="Top CF100 inline column isolation gate valve flange (Z=705.0 mm)"),
        ScadFeature("add_box", {"dx": 54.0, "dy": 108.0, "dz": 28.0}, translate=(round(106.0 * gux, 3), round(106.0 * guy, 3), 190.0), rotate=(0.0, 0.0, gv_az), comment="Inline UHV column isolation gate valve housing"),
        ScadFeature("add_tube", {"od": 426.0, "id": 390.0, "h": 35.0}, translate=(0.0, 0.0, -189.5), comment="Zone 1 lower 150 C bakeout jacket ring"),
        ScadFeature("add_tube", {"od": 426.0, "id": 390.0, "h": 12.5}, translate=(0.0, 0.0, 136.25), comment="Zone 4 top dome bakeout collar"),
        ScadFeature("add_box", {"dx": 30.0, "dy": 48.0, "dz": 32.0}, translate=(round(jx, 3), round(jy, 3), -190.0), rotate=(0.0, 0.0, 315.0), comment="4-zone PID thermocouple & heater junction box"),
    ])

    mesh = merge_solids(shells, name="S5.1-02", material="316LN")
    step_mesh = merge_solids(step_shells, name="S5.1-02_step", material="316LN")
    design = make_part_design_from_bom(
        "S5.1-02",
        design_tier="CUSTOM_FULL",
        material="316LN",
        temp_k=423.15,
        surface_finish_ra_um=0.8,
        world_origin_mm=(0.0, 0.0, Z_WAFER_MM),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            make_cf_port_interface("CF250", "chamber_top_cf250_mate", (0.0, 0.0, 169.0), (0.0, 0.0, -1.0), mating_part_id="S5.1-01", bore_override_mm=88.0),
            make_cf_port_interface("CF100", "column_iso_gate_cf100", (0.0, 0.0, 205.0), (0.0, 0.0, 1.0), mating_part_id="S1.3-01", bore_override_mm=88.0, notes="Inline all-metal CF100 column isolation gate valve (C_closed <= 1e-7 L/s) mating S1.3-01 at Z=705.0 mm"),
            PortInterface("pid_power_4zone", "electrical", (round(jx, 2), round(jy, 2), -190.0), radial_vec(315.0), "4x Type-K + 230VAC PID", mating_part_id="S7.4-01"),
        ),
        dimensions=(
            DimensionCallout("CF250_OD", 305.0, 0.15, -0.15, prefix="Ø", view="top"),
            DimensionCallout("CF100_TOP_OD", 152.0, 0.15, -0.15, prefix="Ø", view="top"),
            DimensionCallout("COL_BORE", 88.0, 0.05, -0.05, prefix="Ø", view="top"),
            DimensionCallout("JACKET_ID", 390.0, 1.0, -1.0, prefix="Ø", view="top"),
            DimensionCallout("JACKET_OD", 426.0, 1.5, -1.5, prefix="Ø", view="top"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.03, datum_primary="", feature_note="CF250 & CF100 knife-edge sealing faces"),
            GDTFrame("concentricity", 0.05, diameter_zone=True, datum_primary="B", feature_note="Top CF100 gate valve bore to CF250 PCD"),
        ),
        notes=(
            "Integrated CF250-to-CF100 inline all-metal UHV column isolation gate valve (C_closed <= 1e-7 L/s, <80 ms fail-close) terminating at Z=705.0 mm.",
            "STAGED BAKEOUT PROTOCOL (OBS-122): Stage-1 150 C bare-vessel bakeout runs with removable S3.2/S4.3/S6.3 cryo/PCB cartridge withdrawn via CF400 top flange; Stage-2 installed-cartridge bakeout capped at <=80 C with active N2 shield cooling (preserving PZT/Rogers/Cryoperm ratings).",
            "3.0 mm cold / >2.5 mm hot radial clearance to S5.1-01 R_out=192.0 mm at 423.15 K; notched clear of 50 deg fiducial & -Y CF150 pump.",
        ),
        scad_params=(
            ("jacket_r_in", r_jin),
            ("jacket_r_out", r_jout),
            ("col_cf100_z_mm", 705.0),
            ("col_bore_mm", 88.0),
            ("gate_c_closed_L_s", 1e-7),
            ("stage1_bake_temp_C", 150),
            ("stage2_installed_max_C", 80),
        ),
        target_mass_kg=22.5,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=3600.0,
    )


def _build_s5_1_03() -> S5PartBuild:
    """S5.1-03: Fully-Perforated CF100 Load-Lock, VAT Gate Valve, 36-deg Optical Anneal Ports & CF40-KF25 Tee."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # Local origin = (420.0, 0.0, 500.0). Mates S5.1-01 +X CF100 face at X=250.0 -> x_loc=-169.5 (0.5 mm gap)
    # 1. VAT All-Metal CF100 Gate Valve (x_loc = [-169.5, -90.2]) with TRUE Ø101.6 mm open bore (OBS-064!)
    fl_in = make_cf_flange(
        "CF100", sub_per_side=1, axis="-x", center=(-159.6, 0.0, 0.0),
        name="ll_vat_flange_in", material="316LN",
    )
    vat_body = make_rect_plate_with_features(
        172.0, 172.0, 39.0, circular_holes=((0.0, 0.0, 101.6),),
        hole_segments=32, axis="x", center=(-130.0, 0.0, 0.0),
        name="ll_vat_body", material="316LN",
    )
    # Top CF100 actuator bonnet adapter neck (offset x_loc=-148 -> X=272, Z=[643.4, 663.2] clearing S5.6-01, S5.1-01 & S5.1-02 z4!)
    vat_bonnet = make_tube(
        34.0, 42.0, 57.0, segments=28, axis="z", center=(-148.0, 0.0, 114.7),
        name="ll_vat_bonnet_neck", material="316LN",
    )
    vat_bonnet_fl = make_cf_flange(
        "CF100", bore_id=68.0, sub_per_side=1, axis="+z", center=(-148.0, 0.0, 153.3),
        name="ll_vat_bonnet_cf100", material="316LN",
    )
    spool = make_tube(50.8, 54.0, 20.0, segments=32, axis="x", center=(-100.3, 0.0, 0.0), material="316LN")
    shells.extend([fl_in, vat_body, vat_bonnet, vat_bonnet_fl, spool])
    step_shells.extend([
        make_cylinder(76.0, 19.8, segments=16, axis="x", center=(-159.6, 0.0, 0.0)),
        make_box(39.0, 172.0, 172.0, center=(-130.0, 0.0, 0.0)),
        make_cylinder(76.0, 72.0, segments=12, axis="z", center=(-130.0, 0.0, 122.2)),
    ])

    # 2. Perforated 316LN Load-Lock Chamber (x=[-90,90], y=[-90,90], z=[-84.8, +65.2]) — ZERO blind walls!
    # Floor plate (solid) at z_loc = [-84.8, -74.8]
    ll_bot = make_box(180.0, 180.0, 10.0, center=(0.0, 0.0, -79.8), name="ll_floor", material="316LN")
    # Top MBE collar plate (z_loc = [+55.2, +65.2], R_in=50.8 -> Ø101.6 open MBE bore!, R_out=75.5 so 36-deg
    # inclined optical beams passing at r >= 80 mm clear top plate & fl_top_mbe with ZERO occlusion!)
    ll_top_ring = make_tube(
        50.8, 75.5, 10.0, segments=48, axis="z", center=(0.0, 0.0, 60.2),
        name="ll_top_mbe_ring", material="316LN",
    )
    # -X wall (x = [-90, -80], z = [-74.6, +55.0]) with Ø101.6 wafer transfer bore centered at (y=0, z=0)
    # 36-deg inclined 140/225 deg beams pass at z > +80 mm at x=-85, well above z=+55.0!
    ll_wall_nx = make_rect_plate_with_features(
        180.0, 129.6, 10.0, circular_holes=((0.0, 9.8, 101.6),),
        hole_segments=32, axis="x", center=(-85.0, 0.0, -9.8),
        name="ll_wall_neg_x", material="316LN",
    )
    # +X wall (x = [+80, +90], z = [-74.6, +55.0]) with Ø101.6 transfer arm bore at (y=0, z=0)
    ll_wall_px = make_rect_plate_with_features(
        180.0, 129.6, 10.0, circular_holes=((0.0, 9.8, 101.6),),
        hole_segments=32, axis="x", center=(85.0, 0.0, -9.8),
        name="ll_wall_pos_x", material="316LN",
    )
    # -Y wall (y = [-90, -80], x = [-79.8, +79.8], z = [-74.6, +55.0]) with Ø80 door bore + Ø16 N2 vent bore
    ll_wall_ny = make_rect_plate_with_features(
        159.6, 129.6, 10.0, circular_holes=((0.0, 9.8, 80.0), (-48.0, -46.2, 16.0)),
        hole_segments=28, axis="y", center=(0.0, -85.0, -9.8),
        name="ll_wall_neg_y", material="316LN",
    )
    # +Y wall (y = [+80, +90], x = [-79.8, +79.8], z = [-74.6, +32.0]) with Ø38 roughing bore at (x=0, z=-20)
    # Stops at z=+32.0 leaving upper +Y 36-deg optical window (S5.5 808 nm flash anneal) 100% open!
    ll_wall_py = make_rect_plate_with_features(
        159.6, 106.6, 10.0, circular_holes=((0.0, 1.3, 38.0),),
        hole_segments=24, axis="y", center=(0.0, 85.0, -21.3),
        name="ll_wall_pos_y", material="316LN",
    )
    # +Y upper corner cheek posts connecting +Y wall to z=+55.0 leaving x=[-64, +64] open for 808 nm beam
    for g_idx, gx in enumerate((-72.0, 72.0), start=1):
        shells.append(make_box(15.0, 10.0, 22.6, center=(gx, 85.0, 43.5), name=f"ll_corner_post_{g_idx}", material="316LN"))

    # Top +Z CF100 port flange (sealing face at z_loc = +85.0 -> Z = 585.0 mm, mating S5.6-01!)
    fl_top_mbe = make_cf_flange(
        "CF100", sub_per_side=1, axis="+z", center=(0.0, 0.0, 75.1),
        name="ll_top_cf100_mbe", material="316LN",
    )
    # +X CF100 transfer arm port flange (sealing face at x_loc = +90.0 -> X = 510.0 mm, mating S5.1-04!)
    fl_arm_out = make_cf_flange(
        "CF100", sub_per_side=1, axis="+x", center=(80.1, 0.0, 0.0),
        name="ll_arm_cf100", material="316LN",
    )
    shells.extend([ll_bot, ll_top_ring, ll_wall_nx, ll_wall_px, ll_wall_ny, ll_wall_py, fl_top_mbe, fl_arm_out])
    step_shells.append(make_box(180.0, 180.0, 170.0, center=(0.0, 0.0, 0.0)))

    # 3. 3x 36-deg Inclined Optical Anneal/Pyrometer CF Weld-Neck Ports + Clear Thermal Shutter Port (OBS-001!)
    # Every port is aimed directly at load-lock wafer S5.4-01 (0, 0, 0) with 100% clear Moller-Trumbore LOS!
    opt_port_specs = (
        ("port_808nm_flash_inclined_90", "CF63", 90.0, LOADLOCK_OPT_ELEV_DEG, LOADLOCK_S55_T_FACE_MM, "S5.5-02", 44.0, 32.0, "+Y 36-deg inclined 808 nm flash sapphire viewport"),
        ("port_rta_flash_inclined_42", "CF100", LOADLOCK_S53_RTA_AZ_DEG, LOADLOCK_OPT_ELEV_DEG, LOADLOCK_S53_RTA_T_FACE_MM, "S5.3-02", 88.0, 30.0, "42-deg 36-deg inclined backup Xe flash/RTA viewport"),
        ("port_pyro_inclined_238", "CF40", LOADLOCK_S53_PYRO_AZ_DEG, LOADLOCK_OPT_ELEV_DEG, LOADLOCK_S53_PYRO_T_FACE_MM, "S5.3-03", 28.0, 26.0, "238-deg 36-deg inclined backup dual-band pyrometer port"),
    )
    inclined_ports: list[PortInterface] = []
    for pname, sz, az, el, t_face, mate_id, bore_ov, nlen, pnote in opt_port_specs:
        sp = CF_SPECS[sz]
        ux, uy, uz = inclined_vec(az, el)
        t_fl_c = t_face - 0.5 * sp.thickness_mm
        c_pt = (t_fl_c * ux, t_fl_c * uy, t_fl_c * uz)
        shells.append(make_cf_weld_neck(
            sz, neck_length=nlen, tube_id=bore_ov, sub_per_side=1,
            axis=(ux, uy, uz), center=c_pt, name=f"ll_{pname}", material="316LN",
        ))
        f_pt = (round(t_face * ux, 4), round(t_face * uy, 4), round(t_face * uz, 4))
        inclined_ports.append(make_cf_port_interface(
            sz, pname, f_pt, (ux, uy, uz), mating_part_id=mate_id, bore_override_mm=bore_ov, notes=pnote,
        ))
    # Clear horizontal CF40 thermal shutter port at az=320 deg, z_loc=+45.0 (Z=545 mm, well clear of S2.1-03!)
    sux, suy, _ = radial_vec(LOADLOCK_SHUTTER_AZ_DEG)
    sp40 = CF_SPECS["CF40"]
    s_fl_c = LOADLOCK_SHUTTER_R_FACE_MM - 0.5 * sp40.thickness_mm
    shells.append(make_cf_weld_neck(
        "CF40", neck_length=22.0, sub_per_side=1, axis=(sux, suy, 0.0),
        center=(s_fl_c * sux, s_fl_c * suy, LOADLOCK_SHUTTER_Z_LOC_MM),
        name="ll_port_shutter_320", material="316LN",
    ))
    inclined_ports.append(make_cf_port_interface(
        "CF40", "port_shutter_320",
        (round(LOADLOCK_SHUTTER_R_FACE_MM * sux, 4), round(LOADLOCK_SHUTTER_R_FACE_MM * suy, 4), LOADLOCK_SHUTTER_Z_LOC_MM),
        (sux, suy, 0.0), mating_part_id="S5.3-04",
        notes="320 deg Z=545 mm load-lock thermal shutter port (420 mm clear of S2.1-03)",
    ))

    # 4. Operator -Y Quick-Access Hinged CF100 Viewport Door + Latch Handle + N2 Vent Valve
    door_vp = make_cf_viewport(
        "CF100", clear_aperture=80.0, window_diameter=88.0, window_thickness=8.0,
        sub_per_side=1, axis="+y", center=(0.0, -100.2, 0.0),
        name="ll_quick_access_door", material="316LN", window_material="Fused Silica",
    )
    door_hinge = make_cylinder(8.0, 110.0, segments=16, axis="z", center=(-78.0, -102.0, 0.0), material="316LN")
    door_handle = make_chamfered_box(14.0, 26.0, 72.0, chamfer=2.0, center=(60.0, -118.0, 0.0), material="316LN")
    n2_vent_port = make_cf_weld_neck(
        "CF16", neck_length=18.0, sub_per_side=1, axis="-y", center=(-48.0, -112.0, -56.0),
        name="ll_n2_vent_cf16", material="316LN",
    )
    # +Y Service CF40 roughing port + Conical CF40-to-ISO-KF25 Roughing Adapter & Foreline Valve Tee (OBS-066!)
    rough_port = make_cf_weld_neck(
        "CF40", neck_length=14.0, sub_per_side=1, axis="+y", center=(0.0, 110.5, -20.0),
        name="ll_rough_cf40", material="316LN",
    )
    rough_cf40_mate = make_cf_flange(
        "CF40", bore_id=25.0, sub_per_side=1, axis="-y", center=(0.0, 123.7, -20.0),
        name="ll_rough_cf40_adapt_fl", material="316LN",
    )
    rough_kf25_cone = make_revolved_profile(
        [(12.5, 130.1), (19.0, 130.1), (19.0, 150.0), (14.5, 150.0), (14.5, 156.0), (20.0, 156.0), (20.0, 162.0), (12.5, 162.0)],
        segments=24, axis="+y", center=(0.0, 0.0, -20.0),
        name="ll_cf40_to_kf25_adapter", material="316LN",
    )
    shells.extend([door_vp, door_hinge, door_handle, n2_vent_port, rough_port, rough_cf40_mate, rough_kf25_cone])
    step_shells.append(make_cylinder(76.0, 22.0, segments=12, axis="y", center=(0.0, -101.0, 0.0)))

    # 5. Internal Wafer Cassette Parking Rail (clear of center Z=0 transfer path)
    rail_l = make_box(110.0, 8.0, 6.0, center=(0.0, -48.0, -12.0), material="Ti-6Al-4V")
    rail_r = make_box(110.0, 8.0, 6.0, center=(0.0, 48.0, -12.0), material="Ti-6Al-4V")
    shells.extend([rail_l, rail_r])

    # 6. Vibration-Decoupled Floor Support Pedestal (X=[465, 505], x_loc=[45, 85], Z=[0, 414.5])
    stand_col_l = make_box(40.0, 32.0, 396.0, center=(65.0, -52.0, -284.0), material="Steel")
    stand_col_r = make_box(40.0, 32.0, 396.0, center=(65.0, 52.0, -284.0), material="Steel")
    stand_base = make_box(50.0, 150.0, 18.0, center=(65.0, 0.0, -491.0), material="Steel")
    stand_top = make_box(46.0, 140.0, 12.0, center=(65.0, 0.0, -91.5), material="Steel")
    shells.extend([stand_col_l, stand_col_r, stand_base, stand_top])
    step_shells.append(make_box(50.0, 150.0, 414.5, center=(65.0, 0.0, -292.75)))

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF100"}, translate=(-159.6, 0.0, 0.0), rotate=(0.0, -90.0, 0.0), comment="Inlet CF100 flange mating S5.1-01"),
        ScadFeature("add_box", {"dx": 39.0, "dy": 172.0, "dz": 172.0}, translate=(-130.0, 0.0, 0.0), comment="VAT CF100 all-metal gate valve body (bored Ø101.6)"),
        ScadFeature("add_cf_flange", {"size": "CF100"}, translate=(-130.0, 0.0, 148.3), comment="Top CF100 VAT bonnet flange mating S7.SAFETY-06 (Z=658.2 mm)"),
        ScadFeature("add_box", {"dx": 180.0, "dy": 180.0, "dz": 150.0}, translate=(0.0, 0.0, -9.8), comment="Perforated load-lock chamber cube"),
        ScadFeature("add_cf_flange", {"size": "CF100"}, translate=(0.0, 0.0, 75.1), comment="+Z CF100 MBE capper port (Z=585.0 mm)"),
        ScadFeature("add_cf_flange", {"size": "CF100"}, translate=(80.1, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="+X CF100 transfer arm port"),
        ScadFeature("add_cf_flange", {"size": "CF100", "bore_id": 80.0}, translate=(0.0, -100.2, 0.0), rotate=(90.0, 0.0, 0.0), comment="-Y quick-access viewport door"),
        ScadFeature("add_box", {"dx": 50.0, "dy": 150.0, "dz": 414.5}, translate=(65.0, 0.0, -292.75), comment="Decoupled floor support stand"),
        ScadFeature("cut_hole", {"d": 101.6, "h": 260.0}, translate=(-40.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="Wafer transfer through-bore"),
        ScadFeature("cut_hole", {"d": 101.6, "h": 40.0}, translate=(0.0, 0.0, 70.0), comment="Open +Z MBE evaporant beam bore"),
    ])

    mesh = merge_solids(shells, name="S5.1-03", material="316LN")
    step_mesh = merge_solids(step_shells, name="S5.1-03_step", material="316LN")
    design = make_part_design_from_bom(
        "S5.1-03",
        design_tier="COTS_ENV_ICD",
        material="316LN",
        temp_k=300.0,
        surface_finish_ra_um=0.4,
        world_origin_mm=(LOADLOCK_CENTER_X_MM, 0.0, Z_WAFER_MM),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            make_cf_port_interface("CF100", "main_chamber_gate_in", (-169.5, 0.0, 0.0), (-1.0, 0.0, 0.0), mating_part_id="S5.1-01"),
            make_cf_port_interface("CF100", "vat_bonnet_top_cf100", (-148.0, 0.0, 163.2), (0.0, 0.0, 1.0), mating_part_id="S7.SAFETY-06", bore_override_mm=68.0, notes="Top CF100 VAT gate valve bonnet mating S7.SAFETY-06 fail-close actuator at (272, 0, 663.2)"),
            make_cf_port_interface("CF100", "mbe_top_cf100", (0.0, 0.0, 85.0), (0.0, 0.0, 1.0), mating_part_id="S5.6-01", notes="Exp139 S5.6 host port at Z=585.0 mm (fully perforated Ø101.6 mm bore)"),
            make_cf_port_interface("CF100", "transfer_arm_pos_x", (90.0, 0.0, 0.0), (1.0, 0.0, 0.0), mating_part_id="S5.1-04"),
            make_cf_port_interface("CF100", "operator_door_neg_y", (0.0, -110.1, 0.0), (0.0, -1.0, 0.0), bore_override_mm=80.0, notes="-Y quick-access hinged viewport door"),
            make_cf_port_interface("CF16", "n2_vent_neg_y", (-48.0, -115.8, -56.0), (0.0, -1.0, 0.0), notes="Dry N2 purge/vent valve port"),
            PortInterface("roughing_kf25_pos_y", "vacuum", (0.0, 162.0, -20.0), (0.0, 1.0, 0.0), "ISO-KF25 (via CF40-to-KF25 adapter)", mating_part_id="S5.2-03", bore_mm=25.0, od_mm=40.0, notes="CF40-to-KF25 conical roughing adapter for valved foreline tee to S5.2-03"),
            *inclined_ports,
        ),
        dimensions=(
            DimensionCallout("CHAMBER_W", 180.0, 0.2, -0.2, view="top"),
            DimensionCallout("CHAMBER_H", 170.0, 0.2, -0.2, view="front"),
            DimensionCallout("MBE_PORT_Z", 85.0, 0.1, -0.1, view="front", datum_ref="A"),
            DimensionCallout("GATE_FACE_X", -169.5, 0.15, -0.15, view="top", datum_ref="B"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.10, diameter_zone=True, datum_primary="A", feature_note="Top CF100 MBE port to wafer plane"),
            GDTFrame("concentricity", 0.15, diameter_zone=True, datum_primary="B", feature_note="Gate valve & transfer arm CF100 axes"),
        ),
        notes=(
            "Fully-perforated 316LN load-lock (OBS-001/064): all CF100 (-X/+X/+Z), CF40, CF16, and 36-deg optical bores open.",
            "VAT CF100 all-metal gate valve (bored Ø101.6 mm) + top CF100 bonnet at (290, 0, 658.2) mating S7.SAFETY-06 (OBS-066).",
            "Hosts 36-deg inclined optical anneal/pyrometer ports (S5.5 808 nm, S5.3 RTA, S5.3-03 pyrometer) + clear S5.3-04 shutter + CF40-to-KF25 roughing adapter.",
        ),
        scad_params=(("cube_x", 180.0), ("cube_y", 180.0), ("cube_z", 170.0), ("opt_elev_deg", LOADLOCK_OPT_ELEV_DEG), ("stand_clear_granite", 15.0)),
        target_mass_kg=54.0,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=5200.0,
    )


def _build_s5_1_04() -> S5PartBuild:
    """S5.1-04: True 518 mm-Stroke Magnetically Coupled UHV Transfer Arm & Clear CF100-Parked Ti-6Al-4V Fork."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # Local x = 0 at mating CF100 flange face (global X = 510.5 mm, +0.5 mm gap from S5.1-03 at 510.0)
    # OBS-064 fix: CF100 fork parking spool (ID=98 mm, x=[19.8, 46.0]) houses entire 68 mm fork yoke
    # with 15 mm radial clearance (ZERO clash with cone or Ø34 guide tube!).
    # Compact 48 mm SmCo shuttle (x=[586, 634]) has 518.0 mm unobstructed stroke to x=68.0 cone shoulder,
    # moving fork center from X=506.5 to X=-11.5 mm (11.5 mm PAST wafer center X=0!) while X_max=1158.5 < 1160.5!
    fl_mate = make_cf_flange(
        "CF100", sub_per_side=1, axis="-x", center=(9.9, 0.0, 0.0),
        name="arm_cf100_flange", material="316LN",
    )
    # Dedicated CF100 fork-parking spool (x = 19.9..46.0, ID = 98 mm, OD = 104 mm)
    park_spool = make_tube(49.0, 52.0, 26.1, segments=32, axis="x", center=(32.95, 0.0, 0.0), name="arm_fork_park_spool", material="316LN")
    # Conical CF100 -> Ø34 guide tube welded reducer (x = 46.1..68.0)
    cone_prof = [
        (49.0, 46.1), (52.0, 46.1), (19.0, 68.0), (17.0, 68.0),
    ]
    cone = make_revolved_profile(cone_prof, segments=32, axis="+x", name="arm_reducer", material="316LN")
    # 570 mm seamless non-magnetic 316LN guide tube (x = 68.1..638.1 -> supports 518.0 mm free stroke!)
    guide_tube = make_tube(17.0, 19.0, 570.0, segments=32, axis="x", center=(353.1, 0.0, 0.0), name="arm_518mm_tube", material="316LN")
    end_cap = make_cylinder(20.5, 9.8, segments=24, axis="x", center=(643.1, 0.0, 0.0), name="arm_end_cap", material="316LN")
    # Compact high-field rare-earth SmCo magnetic linear/rotary shuttle sleeve (parked at x=586..634, L=48 mm)
    shuttle = make_tube(20.2, 34.0, 48.0, segments=32, axis="x", center=(610.0, 0.0, 0.0), name="arm_mag_shuttle", material="Al 6061")
    rot_collar = make_tube(34.2, 39.0, 18.0, segments=24, axis="x", center=(622.0, 0.0, 0.0), name="arm_rotary_knob", material="316LN")
    # Internal stainless push-rod (x = 42.2..620.0, Ø14 mm strictly inside Ø34 mm guide tube!)
    push_rod = make_cylinder(7.0, 577.8, segments=20, axis="x", center=(331.1, 0.0, 0.0), name="arm_push_rod", material="316LN")
    # Precision CNC Ti-6Al-4V two-prong wafer fork parked strictly inside CF100 spool & clear load-lock bore!
    # fork_yoke (x=[28.0, 42.0], width 68 mm) sits cleanly inside ID=98 mm park_spool (15 mm radial margin!)
    # prongs (x=[-36.0, +28.0], world X=[474.5, 538.5]) sit 29.5 mm clear of S5.4-01 wafer (X_max=445.0)!
    fork_yoke = make_chamfered_box(14.0, 68.0, 8.0, chamfer=1.0, center=(35.0, 0.0, 0.0), name="arm_fork_yoke", material="Ti-6Al-4V")
    prong_l = make_box(63.8, 10.0, 5.0, center=(-4.0, -29.0, 0.0), name="arm_fork_prong_l", material="Ti-6Al-4V")
    prong_r = make_box(63.8, 10.0, 5.0, center=(-4.0, 29.0, 0.0), name="arm_fork_prong_r", material="Ti-6Al-4V")
    # Cantilever support floor stanchion at x = 612 mm (foot X=[1087.5, 1157.5] < 1160.5 mm!)
    stanchion_clamp = make_tube(19.5, 29.0, 24.0, segments=24, axis="x", center=(568.0, 0.0, 0.0), material="Al 6061")
    stanchion_post = make_cylinder(14.0, 456.0, segments=20, axis="z", center=(568.0, 0.0, -258.0), material="Steel")
    stanchion_foot = make_box(96.0, 96.0, 14.0, center=(568.0, 0.0, -493.0), material="Steel")

    shells.extend([
        fl_mate, park_spool, cone, guide_tube, end_cap, shuttle, rot_collar,
        push_rod, fork_yoke, prong_l, prong_r, stanchion_clamp, stanchion_post, stanchion_foot,
    ])
    step_shells.extend([
        make_cylinder(76.0, 19.8, segments=16, axis="x", center=(9.9, 0.0, 0.0)),
        make_cylinder(52.0, 26.1, segments=16, axis="x", center=(32.95, 0.0, 0.0)),
        make_cylinder(19.0, 570.0, segments=16, axis="x", center=(353.1, 0.0, 0.0)),
        make_cylinder(39.0, 48.0, segments=16, axis="x", center=(610.0, 0.0, 0.0)),
        make_box(96.0, 96.0, 493.0, center=(568.0, 0.0, -253.5)),
    ])

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF100"}, translate=(9.9, 0.0, 0.0), rotate=(0.0, -90.0, 0.0), comment="Mating CF100 flange"),
        ScadFeature("add_tube", {"od": 104.0, "id": 98.0, "h": 26.1}, translate=(32.95, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="CF100 fork parking spool (clears 68 mm yoke)"),
        ScadFeature("add_tube", {"od": 38.0, "id": 34.0, "h": 570.0}, translate=(353.1, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="518 mm stroke 316LN magnetic guide tube"),
        ScadFeature("add_tube", {"od": 68.0, "id": 40.4, "h": 48.0}, translate=(610.0, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="External SmCo magnetic linear/rotary shuttle"),
        ScadFeature("add_box", {"dx": 63.8, "dy": 10.0, "dz": 5.0}, translate=(-4.0, -29.0, 0.0), comment="Ti-6Al-4V wafer fork left prong"),
        ScadFeature("add_box", {"dx": 63.8, "dy": 10.0, "dz": 5.0}, translate=(-4.0, 29.0, 0.0), comment="Ti-6Al-4V wafer fork right prong"),
        ScadFeature("add_cylinder", {"d": 28.0, "h": 456.0}, translate=(568.0, 0.0, -258.0), comment="End support floor stanchion"),
    ])

    mesh = merge_solids(shells, name="S5.1-04", material="316LN")
    step_mesh = merge_solids(step_shells, name="S5.1-04_step", material="316LN")
    rec = S5_RECONCILIATIONS["S5.1-04"]
    design = make_part_design_from_bom(
        "S5.1-04",
        design_tier="COTS_ENV_ICD",
        material="316LN",
        temp_k=300.0,
        surface_finish_ra_um=0.4,
        world_origin_mm=(510.5, 0.0, Z_WAFER_MM),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            make_cf_port_interface("CF100", "loadlock_cf100_mate", (0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), mating_part_id="S5.1-03"),
            PortInterface("ti_wafer_fork", "mechanical", (-4.0, 0.0, 0.0), (-1.0, 0.0, 0.0), "80x80 mm AlN carrier fork", mating_part_id="S5.4-01", notes="518.0 mm active stroke reaches X=-11.5 mm (11.5 mm past wafer center X=0); 68 mm yoke parked inside ID=98 mm CF100 spool"),
        ),
        dimensions=(
            DimensionCallout("STROKE_ACTIVE", 518.0, 0.5, -0.5, view="front"),
            DimensionCallout("OVERALL_LEN", 684.0, 1.0, -1.0, view="front"),
            DimensionCallout("GUIDE_OD", 38.0, 0.1, -0.1, prefix="Ø", view="right"),
            DimensionCallout("FORK_SPAN", 68.0, 0.1, -0.1, view="top"),
        ),
        gdt_frames=(
            GDTFrame("straightness", 0.20, diameter_zone=True, datum_primary="B", feature_note="518 mm linear guide rail runout"),
            GDTFrame("parallelism", 0.15, datum_primary="A", feature_note="Ti-6Al-4V fork prongs to wafer plane"),
        ),
        notes=(
            "RECONCILIATION: Replaces legacy CAD v6.0 200 mm stub with true 518.0 mm-stroke "
            "magnetically coupled linear/rotary UHV transfer arm (500 mm BOM min exceeded; reaches X=-11.5 mm past X=0 wafer center).",
            "OBS-064 fix: 68 mm Ti-6Al-4V fork yoke parked inside dedicated Ø98 mm ID CF100 spool ahead of Ø34 mm guide tube (15 mm radial clearance, zero collision).",
        ),
        scad_params=(("stroke_mm", 518.0), ("tube_len_mm", 570.0), ("tube_od_mm", 38.0), ("park_spool_id_mm", 98.0), ("fork_span_mm", 68.0)),
        target_mass_kg=12.8,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=7200.0, reconciliation=rec,
    )


def _build_s5_1_05() -> S5PartBuild:
    """S5.1-05: OFHC Cu ConFlat Gasket Kit, 12-Point Bolt Hardware Rack, Angle Valves & Viewport Tray."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # Cleanroom anodized Al/316L service kit tray (360 x 260 x 36 mm) seated at floor/service bench
    tray = make_hollow_enclosure(
        360.0, 260.0, 34.0, wall=6.0, open_faces=("+z",), center=(0.0, 0.0, 17.0),
        name="kit_service_tray", material="Al 6061",
    )
    handle_l = make_box(12.0, 90.0, 12.0, center=(-186.5, 0.0, 24.0), material="316LN")
    handle_r = make_box(12.0, 90.0, 12.0, center=(186.5, 0.0, 24.0), material="316LN")
    shells.extend([tray, handle_l, handle_r])
    step_shells.append(make_box(360.0, 260.0, 34.0, center=(0.0, 0.0, 17.0)))

    # 1. Representative stacked OFHC Cu ConFlat knife-edge gaskets (CF100, CF63, CF40)
    gasket_stacks = (
        ("CF100", -102.0, 48.0, 5),
        ("CF63", 18.0, 62.0, 5),
        ("CF40", 118.0, 72.0, 6),
    )
    for sz, gx, gy, count in gasket_stacks:
        sp = CF_SPECS[sz]
        r_in = 0.5 * sp.bore_id_mm
        r_out = 0.5 * sp.gasket_od_mm
        for k in range(count):
            zk = 8.0 + k * 2.4
            shells.append(make_tube(
                r_in, r_out, 2.0, segments=32, axis="z", center=(gx, gy, zk),
                name=f"gasket_{sz}_{k+1}", material="OFHC Cu",
            ))
        step_shells.append(make_tube(r_in, r_out, count * 2.4, segments=16, axis="z", center=(gx, gy, 7.0 + 0.5 * count * 2.4)))

    # 2. Silver-plated 12-point M8 & M6 UHV bolt hardware organizer block (12 bolts)
    bolt_block = make_rect_plate_with_features(
        130.0, 68.0, 14.0,
        circular_holes=tuple((-48.0 + 19.2 * ix, -16.0 + 32.0 * iy, 8.8) for ix in range(6) for iy in range(2)),
        hole_segments=12, axis="z", center=(-92.0, -76.0, 14.0),
        name="bolt_rack_base", material="Al 6061",
    )
    shells.append(bolt_block)
    for ix in range(6):
        for iy in range(2):
            bx = -92.0 - 48.0 + 19.2 * ix
            by = -76.0 - 16.0 + 32.0 * iy
            d_sh = 8.0 if iy == 0 else 6.0
            shells.append(make_bolt_solid(
                d_sh, 26.0, 1.55 * d_sh, 7.5, center=(bx, by, 38.0), axis="z",
                name=f"bolt_12pt_{ix}_{iy}", material="316LN",
            ))
    step_shells.append(make_box(130.0, 68.0, 48.0, center=(-92.0, -76.0, 31.0)))

    # 3. Two Spare Bakeable All-Metal CF40 Angle Valves + Spare CF40 Viewport seated in tray
    for idx, vx in enumerate((25.0, 118.0), start=1):
        vy = -66.0
        v_fl_bot = make_cf_flange("CF40", sub_per_side=1, axis="-z", center=(vx, vy, 14.0), material="316LN")
        v_body = make_cylinder(22.0, 46.0, segments=20, axis="z", center=(vx, vy, 44.0), material="316LN")
        v_fl_side = make_cf_flange("CF40", sub_per_side=1, axis="+y", center=(vx, vy + 30.0, 44.0), material="316LN")
        v_wheel = make_tube(18.0, 26.0, 10.0, segments=20, axis="z", center=(vx, vy, 82.0), material="Al 6061")
        v_stem = make_cylinder(6.0, 16.0, segments=12, axis="z", center=(vx, vy, 74.0), material="316LN")
        shells.extend([v_fl_bot, v_body, v_fl_side, v_wheel, v_stem])
        step_shells.append(make_cylinder(34.75, 80.0, segments=12, axis="z", center=(vx, vy, 47.0)))

    # Spare CF40 Viewport in tray pocket
    spare_vp = make_cf_viewport(
        "CF40", clear_aperture=32.0, window_diameter=36.0, window_thickness=4.0,
        sub_per_side=1, axis="+z", center=(122.0, 2.0, 14.0),
        name="spare_cf40_viewport", material="316LN", window_material="Fused Silica",
    )
    shells.append(spare_vp)

    scad_feats.extend([
        ScadFeature("add_box", {"dx": 360.0, "dy": 260.0, "dz": 34.0}, translate=(0.0, 0.0, 17.0), comment="UHV CF hardware & gasket kit tray"),
        ScadFeature("add_tube", {"od": 120.5, "id": 101.6, "h": 12.0}, translate=(-102.0, 48.0, 13.0), comment="OFHC Cu CF100 gasket stack"),
        ScadFeature("add_tube", {"od": 82.4, "id": 63.5, "h": 12.0}, translate=(18.0, 62.0, 13.0), comment="OFHC Cu CF63 gasket stack"),
        ScadFeature("add_tube", {"od": 48.1, "id": 38.0, "h": 14.0}, translate=(118.0, 72.0, 14.0), comment="OFHC Cu CF40 gasket stack"),
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(25.0, -66.0, 14.0), comment="All-metal bakeable CF40 angle valve #1"),
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(118.0, -66.0, 14.0), comment="All-metal bakeable CF40 angle valve #2"),
        ScadFeature("cut_hole", {"d": 101.6, "h": 16.0}, translate=(-102.0, 48.0, 13.0), comment="CF100 gasket ID bore"),
    ])

    mesh = merge_solids(shells, name="S5.1-05", material="316LN")
    step_mesh = merge_solids(step_shells, name="S5.1-05_step", material="316LN")
    design = make_part_design_from_bom(
        "S5.1-05",
        design_tier="COTS_ENV_ICD",
        material="OFHC Cu",
        temp_k=300.0,
        surface_finish_ra_um=0.8,
        world_origin_mm=(780.0, -480.0, 0.0),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            PortInterface("gasket_cf100_spare", "mechanical", (-102.0, 48.0, 20.0), (0.0, 0.0, 1.0), "OFHC Cu CF100 Spare Gasket Stack", notes="Unmounted cleanroom spare tray (OBS-122); fits CF100 ports e.g. S5.1-01:port_loadlock_pos_x"),
            PortInterface("gasket_cf63_spare", "mechanical", (18.0, 62.0, 20.0), (0.0, 0.0, 1.0), "OFHC Cu CF63 Spare Gasket Stack", notes="Unmounted cleanroom spare tray; fits CF63 ports e.g. S5.5-02"),
            PortInterface("angle_valve_cf40_spare", "mechanical", (25.0, -66.0, 7.65), (0.0, 0.0, -1.0), "Bakeable All-Metal CF40 Spare Angle Valve", notes="Unmounted cleanroom spare tray; fits CF40 ports"),
        ),
        dimensions=(
            DimensionCallout("TRAY_L", 360.0, 0.5, -0.5, view="top"),
            DimensionCallout("TRAY_W", 260.0, 0.5, -0.5, view="top"),
            DimensionCallout("CF100_GASK_OD", 120.5, 0.08, -0.08, prefix="Ø", view="top"),
            DimensionCallout("CF63_GASK_OD", 82.4, 0.08, -0.08, prefix="Ø", view="top"),
            DimensionCallout("CF40_GASK_OD", 48.1, 0.08, -0.08, prefix="Ø", view="top"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.025, datum_primary="", feature_note="OFHC Cu gasket sealing faces"),
            GDTFrame("parallelism", 0.03, datum_primary="A", feature_note="Gasket top/bottom faces"),
        ),
        notes=(
            "Complete UHV hardware kit: OFHC Cu ConFlat gaskets (CF400/250/100/63/40), Ag-plated 12-pt M8/M6 bolts,",
            "2x bakeable all-metal CF40 angle valves (250 C) & spare CF40 viewport in cleanroom service tray.",
        ),
        scad_params=(("tray_x", 360.0), ("tray_y", 260.0), ("cf100_gask_od", 120.5), ("cf63_gask_od", 82.4)),
        target_mass_kg=14.0,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=6500.0,
    )


def _build_s5_2_01() -> S5PartBuild:
    """S5.2-01: 300 L/s Mag-Lev TMP + High-Conductance Short CF150 Bellows & Open-Bore Tee (S_eff >= 206 L/s N2)."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # World origin = (0.0, -425.0, 508.0). Chamber -Y CF150 face is at Y = -260.0, Z = 508.0 -> y_loc = +164.5 (0.5 mm gap!)
    # OBS-107 fix: Upgraded from narrow 469 mm CF100 duct (S_eff=111 L/s) to short high-conductance CF150
    # (ID=152.4 mm, L_eff=232.5 mm, Clausing W=0.466 -> C_duct=1000 L/s -> S_eff=206.3 L/s N2 >= 169 L/s!).
    # 1. Short CF150 Edge-Welded Vibration Isolation Bellows (y_loc = +81.0 .. +164.5)
    fl_bel_front = make_cf_flange("CF150", sub_per_side=1, axis="+y", center=(0.0, 153.4, 0.0), material="316LN")
    bellows = make_bellows(
        r_in=75.5, r_out=88.0, length=38.7, n_convolutions=10, wall_thickness=0.22,
        end_cuff_mm=2.5, segments=36, axis="y", center=(0.0, 122.75, 0.0),
        name="tmp_cf150_bellows", material="316L",
    )
    fl_bel_rear = make_cf_flange("CF150", sub_per_side=1, axis="-y", center=(0.0, 92.1, 0.0), material="316LN")
    shells.extend([fl_bel_front, bellows, fl_bel_rear])
    step_shells.extend([
        make_cylinder(101.25, 22.2, segments=16, axis="y", center=(0.0, 153.4, 0.0)),
        make_tube(75.5, 88.0, 38.7, segments=16, axis="y", center=(0.0, 122.75, 0.0)),
        make_cylinder(101.25, 22.2, segments=16, axis="y", center=(0.0, 92.1, 0.0)),
    ])

    # 2. High-Conductance CF150 Open-Side 3-Way Pumping Tee (z_loc = [-99.8, +99.8] -> Z = [408.2, 607.8])
    # Arc sector leaves +Y (+35..+145 deg) 100% open to CF150 bellows bore with zero sub-shell overlap!
    tee_vert = make_arc_sector_solid(76.2, 79.0, 159.6, 130.0, 410.0, arc_segments=28, center_z=0.0, name="tmp_tee_vert", material="316LN")
    fl_tee_top = make_cf_flange("CF100", sub_per_side=1, axis="+z", center=(0.0, 0.0, 89.9), material="316LN")
    fl_tee_bot = make_cf_flange("CF100", sub_per_side=1, axis="-z", center=(0.0, 0.0, -89.9), material="316LN")
    shells.extend([tee_vert, fl_tee_top, fl_tee_bot])
    step_shells.append(make_cylinder(79.0, 199.6, segments=16, axis="z", center=(0.0, 0.0, 0.0)))

    # 3. 300 L/s Mag-Lev Turbomolecular Pump (HiPace 300 Class, z_loc = [-288.0, -100.3], Z = [220.0, 407.7])
    tmp_fl = make_cf_flange("CF100", sub_per_side=1, axis="+z", center=(0.0, 0.0, -110.2), material="316LN")
    tmp_prof = [
        (0.0, -288.0), (58.0, -288.0), (62.0, -278.0), (62.0, -243.0),
        (68.0, -239.0), (68.0, -229.0), (64.0, -227.0), (68.0, -219.0),
        (68.0, -209.0), (64.0, -207.0), (68.0, -199.0), (68.0, -189.0),
        (64.0, -187.0), (68.0, -179.0), (68.0, -169.0), (65.0, -165.0),
        (65.0, -120.2), (50.8, -120.2), (50.8, -150.0), (20.0, -160.0),
        (20.0, -271.0), (0.0, -271.0),
    ]
    tmp_body = make_revolved_profile(tmp_prof, segments=36, axis="z", name="tmp_hipace300_body", material="Al 6061")
    # KF25 foreline outlet port facing -Y toward S5.2-03 scroll pump + integrated drive electronics box on +X
    kf25_port = make_cylinder(20.0, 32.0, segments=20, axis="-y", center=(0.0, -76.0, -258.0), material="316LN")
    tc_box = make_chamfered_box(32.0, 74.0, 96.0, chamfer=3.0, center=(76.0, 0.0, -228.0), name="tmp_maglev_drive", material="Al 6061")
    shells.extend([tmp_fl, tmp_body, kf25_port, tc_box])
    step_shells.append(make_cylinder(68.0, 187.5, segments=16, axis="z", center=(0.0, 0.0, -194.2)))

    # 4. Vibration-Damped Pump Station Floor Frame (z_loc = [-508.0, -288.5], Z = [0.0, 219.5], Y=[-495,-355] -> 5 mm clear of S4 granite Y_min=-350!)
    for sx in (-56.0, 56.0):
        for sy in (-56.0, 56.0):
            shells.append(make_box(22.0, 22.0, 201.0, center=(sx, sy, -399.5), material="Steel"))
    frame_top = make_rect_plate_with_features(140.0, 140.0, 12.0, circular_holes=((0.0, 0.0, 44.0),), axis="z", center=(0.0, 0.0, -294.5), material="Steel")
    frame_bot = make_box(140.0, 140.0, 10.0, center=(0.0, 0.0, -503.0), material="Steel")
    shells.extend([frame_top, frame_bot])
    step_shells.append(make_box(140.0, 140.0, 219.5, center=(0.0, 0.0, -398.25)))

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF150"}, translate=(0.0, 153.4, 0.0), rotate=(-90.0, 0.0, 0.0), comment="Chamber-side CF150 high-conductance bellows flange"),
        ScadFeature("add_tube", {"od": 176.0, "id": 151.0, "h": 38.7}, translate=(0.0, 122.75, 0.0), rotate=(90.0, 0.0, 0.0), comment="10-conv short CF150 vibration isolation bellows"),
        ScadFeature("add_cf_flange", {"size": "CF100"}, translate=(0.0, 0.0, 89.9), comment="Top CF100 tee flange for S5.2-02 VacIon/TSP (Z=607.8 mm)"),
        ScadFeature("add_cylinder", {"d": 136.0, "h": 187.5}, translate=(0.0, 0.0, -194.2), comment="300 L/s mag-lev turbomolecular pump body"),
        ScadFeature("add_box", {"dx": 32.0, "dy": 74.0, "dz": 96.0}, translate=(76.0, 0.0, -228.0), comment="Mag-lev drive electronics module"),
        ScadFeature("add_box", {"dx": 140.0, "dy": 140.0, "dz": 219.5}, translate=(0.0, 0.0, -398.25), comment="Pump station floor frame"),
    ])

    mesh = merge_solids(shells, name="S5.2-01", material="Al 6061")
    step_mesh = merge_solids(step_shells, name="S5.2-01_step", material="Al 6061")
    design = make_part_design_from_bom(
        "S5.2-01",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        temp_k=300.0,
        surface_finish_ra_um=1.6,
        world_origin_mm=(0.0, PUMP_STATION_Y_MM, Z_WAFER_MM + 8.0),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            make_cf_port_interface("CF150", "chamber_cf150_inlet", (0.0, 164.5, 0.0), (0.0, 1.0, 0.0), mating_part_id="S5.1-01"),
            make_cf_port_interface("CF100", "vacion_top_tee_port", (0.0, 0.0, 99.8), (0.0, 0.0, 1.0), mating_part_id="S5.2-02"),
            PortInterface("kf25_foreline_out", "vacuum", (0.0, -92.0, -258.0), (0.0, -1.0, 0.0), "ISO-KF25", mating_part_id="S5.2-03", bore_mm=25.0, od_mm=40.0),
        ),
        dimensions=(
            DimensionCallout("BELLOWS_ID", 151.0, 0.2, -0.2, prefix="Ø", view="right"),
            DimensionCallout("BELLOWS_L", 38.7, 1.0, -1.0, view="right"),
            DimensionCallout("TMP_OD", 136.0, 0.5, -0.5, prefix="Ø", view="top"),
            DimensionCallout("STATION_H", 607.8, 1.0, -1.0, view="front"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.15, diameter_zone=True, datum_primary="A", feature_note="CF150/CF100 tee flange alignment"),
        ),
        notes=(
            "300 L/s (260 L/s N2) magnetically levitated TMP (HiPace 300 class, <0.01 um vibration).",
            "OBS-107 fix: Upgraded to short CF150 duct (ID=152.4 mm, L_eff=232.5 mm, C_duct=1000 L/s N2) + clear -Y magnet channel -> S_eff=206.3 L/s N2 >= 169 L/s.",
            "Pump frame at Y=[-495,-355] clears S4 granite base (Y_min=-350 mm) by 5.0 mm.",
        ),
        scad_params=(("speed_N2_L_s", 260), ("s_eff_N2_L_s", 206.3), ("duct_id_mm", 152.4), ("bellows_conv", 10), ("tmp_od_mm", 136.0)),
        target_mass_kg=18.2,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=3600.0,
    )


def _build_s5_2_02() -> S5PartBuild:
    """S5.2-02: 75 L/s VacIon StarCell Ion Pump + Titanium Sublimation Pump (TSP) Cartridge Flange."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # World origin = (0.0, -450.0, 600.3) -> +0.5 mm Cu gasket gap above S5.2-01 top CF100 at Z=599.8
    fl_bot = make_cf_flange("CF100", sub_per_side=1, axis="-z", center=(0.0, 0.0, 9.9), material="316LN")
    # Dual-pocket VacIon StarCell stainless body (hollowed box, z = 20..146)
    ion_body = make_hollow_enclosure(136.0, 116.0, 126.0, wall=8.0, center=(0.0, 0.0, 83.0), name="vacion_body", material="316LN")
    # Dual ferrite permanent magnet packs & mu-metal outer shields on +-X sides
    mag_l = make_chamfered_box(20.0, 108.0, 118.0, chamfer=2.5, center=(-79.0, 0.0, 83.0), name="vacion_magnet_l", material="Mu-metal")
    mag_r = make_chamfered_box(20.0, 108.0, 118.0, chamfer=2.5, center=(79.0, 0.0, 83.0), name="vacion_magnet_r", material="Mu-metal")
    hv_boot = make_cylinder(14.0, 34.0, segments=16, axis="-y", center=(0.0, -75.5, 83.0), name="vacion_hv_feed", material="Al2O3")
    # Upper TSP water-cooled sublimation shroud (z = 146.5..220.0) + CF40 3-filament Ti cartridge flange
    tsp_shroud = make_tube(42.0, 52.0, 73.5, segments=32, axis="z", center=(0.0, 0.0, 183.25), name="tsp_shroud", material="316LN")
    tsp_flange = make_cf_flange("CF40", sub_per_side=1, axis="+z", center=(0.0, 0.0, 226.4), name="tsp_cf40_flange", material="316LN")
    # 3 high-current Ti sublimation filament feedthrough posts inside/above CF40
    for idx, ang in enumerate((0.0, 120.0, 240.0), start=1):
        px, py, _ = radial_pos(11.0, ang, 0.0)
        shells.append(make_cylinder(3.2, 24.0, segments=12, axis="z", center=(px, py, 244.8), name=f"tsp_pin_{idx}", material="OFHC Cu"))

    shells.extend([fl_bot, ion_body, mag_l, mag_r, hv_boot, tsp_shroud, tsp_flange])
    step_shells.extend([
        make_cylinder(76.0, 19.8, segments=16, axis="z", center=(0.0, 0.0, 9.9)),
        make_box(178.0, 116.0, 126.0, center=(0.0, 0.0, 83.0)),
        make_cylinder(52.0, 86.5, segments=16, axis="z", center=(0.0, 0.0, 189.5)),
    ])

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF100"}, translate=(0.0, 0.0, 9.9), rotate=(180.0, 0.0, 0.0), comment="Bottom CF100 flange mating pump tee"),
        ScadFeature("add_box", {"dx": 136.0, "dy": 116.0, "dz": 126.0}, translate=(0.0, 0.0, 83.0), comment="75 L/s VacIon StarCell pump body"),
        ScadFeature("add_box", {"dx": 20.0, "dy": 108.0, "dz": 118.0}, translate=(-79.0, 0.0, 83.0), comment="Ferrite magnet + mu-metal shield (-X)"),
        ScadFeature("add_box", {"dx": 20.0, "dy": 108.0, "dz": 118.0}, translate=(79.0, 0.0, 83.0), comment="Ferrite magnet + mu-metal shield (+X)"),
        ScadFeature("add_tube", {"od": 104.0, "id": 84.0, "h": 73.5}, translate=(0.0, 0.0, 183.25), comment="TSP sublimation shroud"),
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(0.0, 0.0, 226.4), comment="Top CF40 3-filament TSP cartridge flange"),
    ])

    mesh = merge_solids(shells, name="S5.2-02", material="316LN")
    step_mesh = merge_solids(step_shells, name="S5.2-02_step", material="316LN")
    design = make_part_design_from_bom(
        "S5.2-02",
        design_tier="COTS_ENV_ICD",
        material="316LN",
        temp_k=300.0,
        surface_finish_ra_um=0.8,
        world_origin_mm=(0.0, PUMP_STATION_Y_MM, 608.3),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            make_cf_port_interface("CF100", "tee_cf100_inlet", (0.0, 0.0, 0.0), (0.0, 0.0, -1.0), mating_part_id="S5.2-01"),
            make_cf_port_interface("CF40", "tsp_cartridge_top", (0.0, 0.0, 232.75), (0.0, 0.0, 1.0), notes="3-filament Ti sublimation cartridge feedthrough"),
            PortInterface("hv_7kv_shv", "electrical", (0.0, -92.5, 83.0), (0.0, -1.0, 0.0), "7 kV SHV-10", mating_part_id="S7.4-01"),
        ),
        dimensions=(
            DimensionCallout("OVERALL_W", 178.0, 1.0, -1.0, view="front"),
            DimensionCallout("OVERALL_H", 256.8, 1.0, -1.0, view="front"),
            DimensionCallout("TSP_OD", 104.0, 0.3, -0.3, prefix="Ø", view="top"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.05, datum_primary="", feature_note="CF100 inlet knife-edge flange"),
        ),
        notes=(
            "75 L/s VacIon StarCell ion pump + integrated 3-filament TSP cartridge (zero-vibration write mode).",
            "Dual mu-metal outer shields keep stray B-field negligible at wafer (distance > 450 mm).",
        ),
        scad_params=(("ion_speed_L_s", 75), ("tsp_od_mm", 104.0), ("total_h_mm", 256.8)),
        target_mass_kg=18.5,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=7800.0,
    )


def _build_s5_2_03() -> S5PartBuild:
    """S5.2-03: Oil-Free Dry Scroll Roughing/Backing Pump (15 m^3/h) + KF25 Foreline Backstream Trap."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # Floor mounted at (0.0, -780.0, 0.0), Y_max = -590 (64 mm clear of TMP frame at Y=-526)
    for fx in (-110.0, 110.0):
        for fy in (-145.0, 145.0):
            shells.append(make_cylinder(20.0, 24.0, segments=16, axis="z", center=(fx, fy, 12.0), material="PTFE"))
    base = make_chamfered_box(270.0, 350.0, 18.0, chamfer=3.0, center=(0.0, 0.0, 33.2), name="scroll_base", material="Al 6061")
    # Finned scroll compression head (+Y end, y = +45..+145)
    head_prof = [
        (0.0, 45.0), (102.0, 45.0), (105.0, 52.0), (105.0, 66.0), (96.0, 68.0),
        (105.0, 74.0), (105.0, 88.0), (96.0, 90.0), (105.0, 96.0), (105.0, 112.0),
        (96.0, 114.0), (105.0, 120.0), (105.0, 142.0), (96.0, 148.0), (0.0, 148.0),
    ]
    scroll_head = make_revolved_profile(head_prof, segments=32, axis="+y", center=(0.0, 0.0, 148.0), name="scroll_head", material="Al 6061")
    # TEFC drive motor barrel (-Y end, y = -140..+42)
    motor = make_cylinder(82.0, 180.0, segments=28, axis="y", center=(0.0, -49.0, 148.0), name="scroll_motor", material="Al 6061")
    jbox_top = make_chamfered_box(92.0, 108.0, 48.0, chamfer=3.0, center=(0.0, -55.0, 254.0), name="scroll_inverter", material="Al 6061")
    # Vertical KF25 molecular-sieve foreline backstream trap (+Y top, z = 250..345)
    trap_body = make_tube(26.0, 34.0, 88.0, segments=24, axis="z", center=(0.0, 102.0, 296.0), name="foreline_trap", material="316LN")
    trap_cap = make_cylinder(36.0, 10.0, segments=24, axis="z", center=(0.0, 102.0, 345.2), material="316LN")
    trap_inlet = make_cylinder(20.0, 28.0, segments=16, axis="+y", center=(0.0, 150.0, 305.0), material="316LN")
    exhaust_muff = make_cylinder(18.0, 46.0, segments=16, axis="-y", center=(75.0, -162.0, 148.0), material="316LN")

    shells.extend([base, scroll_head, motor, jbox_top, trap_body, trap_cap, trap_inlet, exhaust_muff])
    step_shells.extend([
        make_box(270.0, 350.0, 42.0, center=(0.0, 0.0, 21.0)),
        make_cylinder(105.0, 103.0, segments=16, axis="y", center=(0.0, 96.5, 148.0)),
        make_cylinder(82.0, 180.0, segments=16, axis="y", center=(0.0, -49.0, 148.0)),
        make_cylinder(36.0, 98.0, segments=12, axis="z", center=(0.0, 102.0, 301.0)),
    ])

    scad_feats.extend([
        ScadFeature("add_box", {"dx": 270.0, "dy": 350.0, "dz": 18.0}, translate=(0.0, 0.0, 33.2), comment="Vibration-isolated cast Al baseplate"),
        ScadFeature("add_cylinder", {"d": 210.0, "h": 103.0}, translate=(0.0, 96.5, 148.0), rotate=(90.0, 0.0, 0.0), comment="Finned dry-scroll compression head"),
        ScadFeature("add_cylinder", {"d": 164.0, "h": 180.0}, translate=(0.0, -49.0, 148.0), rotate=(90.0, 0.0, 0.0), comment="15 m^3/h oil-free TEFC drive motor"),
        ScadFeature("add_tube", {"od": 68.0, "id": 52.0, "h": 88.0}, translate=(0.0, 102.0, 296.0), comment="KF25 molecular-sieve foreline backstream trap"),
    ])

    mesh = merge_solids(shells, name="S5.2-03", material="Al 6061")
    step_mesh = merge_solids(step_shells, name="S5.2-03_step", material="Al 6061")
    design = make_part_design_from_bom(
        "S5.2-03",
        design_tier="COTS_ENV_ICD",
        material="Al 6061",
        temp_k=300.0,
        surface_finish_ra_um=3.2,
        world_origin_mm=(0.0, -780.0, 0.0),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            PortInterface("kf25_inlet", "vacuum", (0.0, 164.0, 305.0), (0.0, 1.0, 0.0), "ISO-KF25", mating_part_id="S5.2-01", bore_mm=25.0, od_mm=40.0),
            PortInterface("kf25_exhaust", "gas", (75.0, -185.0, 148.0), (0.0, -1.0, 0.0), "ISO-KF25 Exhaust", mating_part_id="S7.SAFETY-01", bore_mm=25.0),
        ),
        dimensions=(
            DimensionCallout("FOOTPRINT_X", 270.0, 1.0, -1.0, view="top"),
            DimensionCallout("FOOTPRINT_Y", 360.0, 1.0, -1.0, view="right"),
            DimensionCallout("OVERALL_H", 350.2, 1.0, -1.0, view="front"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.50, datum_primary="", feature_note="Floor vibration mount datum plane"),
        ),
        notes=(
            "Oil-free 15 m^3/h dry scroll roughing/backing pump (nXDS15i class, 1e-2 mbar base, PTFE tip-seal).",
            "Floor mounted behind -Y TMP station (64 mm foreline flex-hose clearance) with KF25 backstream trap.",
        ),
        scad_params=(("speed_m3_h", 15.0), ("base_mbar", 0.01), ("head_od_mm", 210.0)),
        target_mass_kg=26.0,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=2750.0,
    )


def _build_s5_2_04() -> S5PartBuild:
    """S5.2-04: Full-Range Pirani/Cold-Cathode Gauges, 200 amu Quadrupole RGA & Angle Valve Manifold."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # Mates S5.1-01 225 deg Z=395 CF40 port (R_face=245.0 -> R_origin=245.5 mm, rot_z=225 deg)
    # Local +X extends radially outward along 225 deg!
    fl_in = make_cf_flange("CF40", sub_per_side=1, axis="-x", center=(6.35, 0.0, 0.0), material="316LN")
    # 4-way CF40 UHV cross manifold (x = 12.8..92.8)
    cross_x = make_tube(19.0, 21.5, 80.0, segments=24, axis="x", center=(52.8, 0.0, 0.0), material="316LN")
    cross_y = make_tube(19.0, 21.5, 80.0, segments=24, axis="y", center=(52.8, 0.0, 0.0), material="316LN")
    # +Y branch: Full-range Pirani + Cold-Cathode inverted magnetron gauge head
    fl_gauge = make_cf_flange("CF40", sub_per_side=1, axis="+y", center=(52.8, 46.4, 0.0), material="316LN")
    gauge_body = make_cylinder(22.0, 68.0, segments=24, axis="y", center=(52.8, 87.0, 0.0), name="pirani_cc_gauge", material="316LN")
    gauge_cap = make_chamfered_box(42.0, 26.0, 42.0, chamfer=2.0, center=(52.8, 134.2, 0.0), material="Al 6061")
    # -Y branch: Bakeable all-metal CF40 angle valve with knurled handwheel
    fl_valve = make_cf_flange("CF40", sub_per_side=1, axis="-y", center=(52.8, -46.4, 0.0), material="316LN")
    valve_bonnet = make_cylinder(18.0, 40.0, segments=20, axis="-y", center=(52.8, -73.0, 0.0), material="316LN")
    valve_wheel = make_tube(16.0, 24.0, 10.0, segments=20, axis="-y", center=(52.8, -98.5, 0.0), material="Al 6061")
    # +X axial branch: 200 amu Quadrupole RGA Sensor + RF/DC Electronics Head
    fl_rga = make_cf_flange("CF40", sub_per_side=1, axis="+x", center=(99.2, 0.0, 0.0), material="316LN")
    rga_barrel = make_tube(16.0, 19.0, 52.0, segments=24, axis="x", center=(131.6, 0.0, 0.0), name="rga_quadrupole_tube", material="316LN")
    rga_head = make_chamfered_box(68.0, 56.0, 62.0, chamfer=3.0, center=(191.8, 0.0, 0.0), name="rga_200amu_ecu", material="Al 6061")

    shells.extend([
        fl_in, cross_x, cross_y, fl_gauge, gauge_body, gauge_cap,
        fl_valve, valve_bonnet, valve_wheel, fl_rga, rga_barrel, rga_head,
    ])
    step_shells.extend([
        make_cylinder(34.75, 12.7, segments=12, axis="x", center=(6.35, 0.0, 0.0)),
        make_cylinder(21.5, 145.0, segments=12, axis="x", center=(85.0, 0.0, 0.0)),
        make_cylinder(22.0, 236.0, segments=12, axis="y", center=(52.8, 18.0, 0.0)),
        make_box(68.0, 56.0, 62.0, center=(191.8, 0.0, 0.0)),
    ])

    scad_feats.extend([
        ScadFeature("add_cf_flange", {"size": "CF40"}, translate=(6.35, 0.0, 0.0), rotate=(0.0, -90.0, 0.0), comment="Chamber-mating CF40 flange"),
        ScadFeature("add_tube", {"od": 43.0, "id": 38.0, "h": 80.0}, translate=(52.8, 0.0, 0.0), rotate=(0.0, 90.0, 0.0), comment="CF40 gauge cross X-run"),
        ScadFeature("add_cylinder", {"d": 44.0, "h": 68.0}, translate=(52.8, 87.0, 0.0), rotate=(90.0, 0.0, 0.0), comment="Full-range Pirani / Cold-Cathode gauge"),
        ScadFeature("add_box", {"dx": 68.0, "dy": 56.0, "dz": 62.0}, translate=(191.8, 0.0, 0.0), comment="200 amu Quadrupole RGA electronics head"),
    ])

    mesh = merge_solids(shells, name="S5.2-04", material="316LN")
    step_mesh = merge_solids(step_shells, name="S5.2-04_step", material="316LN")
    wx, wy, _ = radial_pos(245.5, 225.0, 0.0)
    design = make_part_design_from_bom(
        "S5.2-04",
        design_tier="COTS_ENV_ICD",
        material="316LN",
        temp_k=300.0,
        surface_finish_ra_um=0.8,
        world_origin_mm=(wx, wy, 395.0),
        world_rotation_deg=(0.0, 0.0, 225.0),
        ports=(
            make_cf_port_interface("CF40", "chamber_cf40_mate", (0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), mating_part_id="S5.1-01"),
            PortInterface("rga_eth_rs485", "electrical", (225.8, 0.0, 0.0), (1.0, 0.0, 0.0), "RJ45 + 24VDC", mating_part_id="S7.1-01"),
            PortInterface("gauge_ctrl_link", "electrical", (52.8, 147.2, 0.0), (0.0, 1.0, 0.0), "FCC68 Gauge Bus", mating_part_id="S7.4-01"),
        ),
        dimensions=(
            DimensionCallout("RGA_LEN", 225.8, 0.5, -0.5, view="top"),
            DimensionCallout("CROSS_SPAN", 250.7, 0.5, -0.5, view="top"),
            DimensionCallout("CF40_OD", 69.5, 0.1, -0.1, prefix="Ø", view="right"),
        ),
        gdt_frames=(
            GDTFrame("perpendicularity", 0.10, diameter_zone=True, datum_primary="A", feature_note="CF40 RGA quadrupole axis to mounting flange"),
        ),
        notes=(
            "Full-range Pirani/Cold-Cathode (1000..1e-11 mbar) + 200 amu Quadrupole RGA (H2O/PH3/He monitoring).",
            "Mounts on S5.1-01 225 deg Z=395.0 mm CF40 port; includes all-metal bakeable isolation angle valve.",
        ),
        scad_params=(("rga_max_amu", 200), ("p_min_mbar", 1e-11), ("len_mm", 225.8)),
        target_mass_kg=4.6,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=5400.0,
    )


def _build_s5_4_01() -> S5PartBuild:
    """S5.4-01: Isotopically Enriched 28Si/29Si (f=1%) Epitaxial Working Wafer (Dia 50 mm SEMI M1)."""
    # SEMI M1 Dia 50.0 mm working wafer with 16.0 mm primary flat (-Y) & 8.0 mm secondary flat (+X)
    r_w = 25.0
    t_sub = 0.725
    y_flat = -math.sqrt(r_w**2 - 8.0**2)  # -23.685 mm (16 mm chord)
    x_sec = math.sqrt(r_w**2 - 4.0**2)    # +24.678 mm (8 mm chord)

    pts_2d: list[tuple[float, float]] = []
    n_seg = 72
    for i in range(n_seg):
        a = 2.0 * math.pi * i / n_seg
        px = r_w * math.cos(a)
        py = r_w * math.sin(a)
        if py < y_flat:
            py = y_flat
        if px > x_sec:
            px = x_sec
        pts_2d.append((px, py))

    # Deduplicate any consecutive near-identical vertices on clipped flats
    clean_poly: list[tuple[float, float]] = []
    for pt in pts_2d:
        if not clean_poly or math.hypot(pt[0] - clean_poly[-1][0], pt[1] - clean_poly[-1][1]) > 0.05:
            clean_poly.append(pt)
    if math.hypot(clean_poly[0][0] - clean_poly[-1][0], clean_poly[0][1] - clean_poly[-1][1]) <= 0.05:
        clean_poly.pop()

    wafer_body = make_plate_with_holes(
        outer_poly_2d=clean_poly, holes_2d=(), thickness=t_sub,
        axis="z", center=(0.0, 0.0, -0.025), name="wafer_28si_substrate", material="Si",
    )
    # 0.050 mm CAD-visible active epitaxial mesa & 16x16 mm Arch-B write-field scribe border
    # Top surface sits at z_loc = +0.3875 -> global Z = 499.6125 + 0.3875 = 500.000 mm (exact Z_WAFER!)
    epi_ring = make_plate_with_holes(
        outer_poly_2d=circle_2d(22.0, segments=48),
        holes_2d=(circle_2d(18.0, segments=40, ccw=False),),
        thickness=0.050, axis="z", center=(0.0, 0.0, 0.3625),
        name="wafer_epi_guard_ring", material="Si",
    )
    write_field_die = make_box(16.0, 16.0, 0.050, center=(0.0, 0.0, 0.3625), name="wafer_16x16_write_field", material="Si")
    # 4 corner fiducial alignment cross pads for S4.5-02 dark-field microscope
    fid_pads = [
        make_box(1.5, 1.5, 0.050, center=(sx, sy, 0.3625), name=f"fiducial_{idx}", material="Au")
        for idx, (sx, sy) in enumerate(((-12.0, -12.0), (12.0, -12.0), (12.0, 12.0), (-12.0, 12.0)), start=1)
    ]

    mesh = merge_solids([wafer_body, epi_ring, write_field_die, *fid_pads], name="S5.4-01", material="Si")
    step_mesh = make_cylinder(25.0, 0.775, segments=32, axis="z", center=(0.0, 0.0, 0.0), name="S5.4-01_step", material="Si")
    scad_feats = (
        ScadFeature("add_cylinder", {"d": 50.0, "h": 0.725}, translate=(0.0, 0.0, -0.025), comment="Dia 50 mm 28Si/29Si (f=1%) working wafer substrate"),
        ScadFeature("add_box", {"dx": 16.0, "dy": 16.0, "dz": 0.050}, translate=(0.0, 0.0, 0.3625), comment="Active 16x16 mm Arch-B write-field epi mesa (100 nm epi + 8 nm 28Si cap)"),
        ScadFeature("cut_slot", {"length": 20.0, "width": 3.0, "h": 1.5}, translate=(0.0, -25.185, 0.0), comment="SEMI M1 16.0 mm primary orientation flat"),
    )
    rec = S5_RECONCILIATIONS["S5.4-01"]
    design = make_part_design_from_bom(
        "S5.4-01",
        design_tier="CUSTOM_FULL",
        material="Si",
        temp_k=0.02,
        surface_finish_ra_um=0.01,
        world_origin_mm=(LOADLOCK_CENTER_X_MM, 0.0, Z_WAFER_MM - 0.3875),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            PortInterface("active_epi_top", "optical", (0.0, 0.0, 0.3875), (0.0, 0.0, 1.0), "Z_WAFER=500.000 mm MBE/Implant Datum", mating_part_id="S5.6-01", bore_mm=16.0, od_mm=50.0, notes="Staged at Load-Lock (X=420, Y=0, Z=500.000) under S5.6-01 28Si MBE capper; transfers to (0,0,500) WD=0.250 mm"),
            PortInterface("carrier_backside", "thermal", (0.0, 0.0, -0.3875), (0.0, 0.0, -1.0), "80x80 mm AlN pocket / Load-Lock rails", mating_part_id="S5.1-03", od_mm=50.0),
        ),
        dimensions=(
            DimensionCallout("WAFER_OD", 50.0, 0.10, -0.10, prefix="Ø", view="top"),
            DimensionCallout("THICKNESS", 0.775, 0.015, -0.015, view="front", decimals=3),
            DimensionCallout("PRI_FLAT", 16.0, 0.5, -0.5, view="top"),
            DimensionCallout("WRITE_FIELD", 16.0, 0.01, -0.01, view="top"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.002, datum_primary="", feature_note="TTV <= 2 um epi-polished top face (Ra < 0.2 nm)"),
            GDTFrame("parallelism", 0.003, datum_primary="A", feature_note="Top epi plane to backside carrier datum A"),
        ),
        datums=(
            ("A", "BACKSIDE WAFER SEATING PLANE"),
            ("B", "CIRCULAR WAFER AXIS (Ø50.0 MM)"),
            ("C", "SEMI M1 PRIMARY <110> ORIENTATION FLAT"),
        ),
        notes=(
            "RECONCILIATION: BOM procures 25x Dia 100 mm CVD 28Si/29Si (f=1.0% +/-0.1%) stock wafers; "
            "CAD models Dia 50.0 mm laser-diced working wafer seated on 80x80 mm AlN carrier (diag 113.14 < Dia 150 mm bore).",
            "Staged inside S5.1-03 Load-Lock at (420.0, 0.0, Z=[499.225, 500.000]) directly beneath S5.6-01 28Si MBE capper, "
            "leaving (0, 0, 500) clear for active IBIC wafer S3.1-01/02.",
            "100 nm epitaxial Mod-B nuclear bath layer; receives 8.0 +/-0.3 nm 28Si MBE cap in S5.6.",
        ),
        scad_params=(("wafer_od_mm", 50.0), ("bom_stock_od_mm", 100.0), ("thickness_mm", 0.775), ("write_field_mm", 16.0)),
        target_mass_kg=0.0036,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=scad_feats,
        step_mesh=step_mesh, density_kg_m3=2329.0, reconciliation=rec,
    )


def _build_s5_4_03() -> S5PartBuild:
    """S5.4-03: N2-Purged FOUP/SMIF Wafer Transfer Pod & Dry Cleanroom Storage Cabinet."""
    shells: list[SolidMesh] = []
    step_shells: list[SolidMesh] = []
    scad_feats: list[ScadFeature] = []

    # World origin = (780.0, -900.0, 0.0), completely clear of service tray, pumps & transfer arm
    # 1. Leveling feet (z = 0..24) + 304 SS Dry-N2 Desiccator Cabinet (380x340x516 mm, z = 24..540)
    for fx in (-160.0, 160.0):
        for fy in (-140.0, 140.0):
            shells.append(make_cylinder(16.0, 24.0, segments=16, axis="z", center=(fx, fy, 12.0), material="304 SS"))
    cabinet = make_hollow_enclosure(
        380.0, 340.0, 516.0, wall=12.0, open_faces=("-y",), center=(0.0, 0.0, 282.0),
        name="n2_desiccator_cabinet", material="304 SS",
    )
    # Front -Y framed viewing door + stainless latch + digital hygrometer/O2 ppm readout bezel
    door_frame = make_rect_plate_with_features(
        368.0, 496.0, 14.0, rect_slots=((0.0, -25.0, 290.0, 340.0, 0.0),),
        axis="y", center=(0.0, -172.0, 282.0), name="n2_door_frame", material="304 SS",
    )
    door_window = make_box(286.0, 6.0, 336.0, center=(0.0, -172.0, 257.0), name="n2_door_window", material="Fused Silica")
    o2_bezel = make_chamfered_box(110.0, 14.0, 42.0, chamfer=2.0, center=(0.0, -182.0, 492.0), material="Al 6061")
    # Internal perforated shelf + rear N2 purge flowmeter ports
    shelf = make_box(348.0, 300.0, 6.0, center=(0.0, 5.0, 275.0), material="304 SS")
    n2_in = make_cylinder(10.0, 24.0, segments=16, axis="+y", center=(-110.0, 182.0, 460.0), material="316LN")
    n2_out = make_cylinder(10.0, 24.0, segments=16, axis="+y", center=(110.0, 182.0, 460.0), material="316LN")

    # 2. Removable PFA FOUP Wafer Storage Pod docked on cabinet top nest (z = 540.5..690.5)
    foup_shell = make_hollow_enclosure(
        180.0, 170.0, 138.0, wall=8.0, center=(0.0, 0.0, 609.5),
        name="foup_pfa_pod", material="PTFE",
    )
    foup_flange = make_chamfered_box(68.0, 68.0, 12.0, chamfer=3.0, center=(0.0, 0.0, 684.8), name="foup_semi_e47_flange", material="PTFE")
    foup_hdl_l = make_box(12.0, 90.0, 14.0, center=(-96.5, 0.0, 615.0), material="PTFE")
    foup_hdl_r = make_box(12.0, 90.0, 14.0, center=(96.5, 0.0, 615.0), material="PTFE")

    shells.extend([cabinet, door_frame, door_window, o2_bezel, shelf, n2_in, n2_out, foup_shell, foup_flange, foup_hdl_l, foup_hdl_r])
    step_shells.extend([
        make_box(380.0, 360.0, 540.0, center=(0.0, -5.0, 270.0)),
        make_box(205.0, 170.0, 150.0, center=(0.0, 0.0, 615.5)),
    ])

    scad_feats.extend([
        ScadFeature("add_box", {"dx": 380.0, "dy": 340.0, "dz": 516.0}, translate=(0.0, 0.0, 282.0), comment="304 SS dry-N2 wafer storage cabinet"),
        ScadFeature("add_box", {"dx": 180.0, "dy": 170.0, "dz": 138.0}, translate=(0.0, 0.0, 609.5), comment="PFA N2-purged FOUP transfer pod"),
        ScadFeature("add_box", {"dx": 68.0, "dy": 68.0, "dz": 12.0}, translate=(0.0, 0.0, 684.8), comment="SEMI E47.1 top robotic grip flange"),
        ScadFeature("cut_hole", {"d": 12.0, "h": 40.0}, translate=(-110.0, 170.0, 460.0), rotate=(90.0, 0.0, 0.0), comment="N2 purge gas inlet"),
    ])

    mesh = merge_solids(shells, name="S5.4-03", material="304 SS")
    step_mesh = merge_solids(step_shells, name="S5.4-03_step", material="304 SS")
    design = make_part_design_from_bom(
        "S5.4-03",
        design_tier="COTS_ENV_ICD",
        material="304 SS",
        temp_k=300.0,
        surface_finish_ra_um=1.6,
        world_origin_mm=(780.0, -900.0, 0.0),
        world_rotation_deg=(0.0, 0.0, 0.0),
        ports=(
            PortInterface("n2_purge_in", "gas", (-110.0, 194.0, 460.0), (0.0, 1.0, 0.0), "1/4 in VCR Dry N2", notes="<1 ppm O2/H2O continuous N2 purge"),
            PortInterface("foup_dock_nest", "mechanical", (0.0, 0.0, 540.5), (0.0, 0.0, 1.0), "SEMI E47.1 Kinematic", mating_part_id="S5.4-01"),
        ),
        dimensions=(
            DimensionCallout("CAB_W", 380.0, 1.0, -1.0, view="front"),
            DimensionCallout("CAB_D", 356.0, 1.0, -1.0, view="right"),
            DimensionCallout("TOTAL_H", 690.8, 1.5, -1.5, view="front"),
            DimensionCallout("FOUP_W", 180.0, 0.5, -0.5, view="top"),
        ),
        gdt_frames=(
            GDTFrame("flatness", 0.50, datum_primary="", feature_note="Cabinet top FOUP kinematic dock surface"),
        ),
        notes=(
            "N2-purged (<1 ppm O2/H2O) 304 SS dry storage cabinet + PFA FOUP wafer transport pod.",
            "Prevents native SiO2 regrowth on 28Si/29Si epi wafers before UHV load-lock insertion.",
        ),
        scad_params=(("cab_w", 380.0), ("cab_d", 340.0), ("cab_h", 516.0), ("foup_w", 180.0)),
        target_mass_kg=34.0,
    )
    return S5PartBuild(
        design=design, mesh=mesh, scad_features=tuple(scad_feats),
        step_mesh=step_mesh, density_kg_m3=3200.0,
    )


def build_s5_uhv_pumps_parts() -> dict[str, S5PartBuild]:
    """Build all 11 UHV vessel, load-lock, pumping & wafer-handling S5 parts."""
    builders = (
        ("S5.1-01", _build_s5_1_01),
        ("S5.1-02", _build_s5_1_02),
        ("S5.1-03", _build_s5_1_03),
        ("S5.1-04", _build_s5_1_04),
        ("S5.1-05", _build_s5_1_05),
        ("S5.2-01", _build_s5_2_01),
        ("S5.2-02", _build_s5_2_02),
        ("S5.2-03", _build_s5_2_03),
        ("S5.2-04", _build_s5_2_04),
        ("S5.4-01", _build_s5_4_01),
        ("S5.4-03", _build_s5_4_03),
    )
    return {pid: fn() for pid, fn in builders}


# ---------------------------------------------------------------------------
# Exact 3D Solid-Solid Intra-Subsystem Clash Checker (Triangle + Containment)
# ---------------------------------------------------------------------------
def _aabb_overlap(
    mn_a: np.ndarray, mx_a: np.ndarray, mn_b: np.ndarray, mx_b: np.ndarray, tol: float = 0.0
) -> bool:
    return bool(np.all(mx_a >= mn_b - tol) and np.all(mx_b >= mn_a - tol))


def _segment_triangle_intersect(
    p0: np.ndarray, p1: np.ndarray, v0: np.ndarray, v1: np.ndarray, v2: np.ndarray, eps: float = 1e-8
) -> bool:
    """Strict interior segment-triangle intersection test (excludes mere boundary touch)."""
    d = p1 - p0
    e1 = v1 - v0
    e2 = v2 - v0
    h = np.cross(d, e2)
    a = float(np.dot(e1, h))
    if abs(a) < eps:
        return False
    f = 1.0 / a
    s = p0 - v0
    u = f * float(np.dot(s, h))
    if u <= eps or u >= 1.0 - eps:
        return False
    q = np.cross(s, e1)
    v = f * float(np.dot(d, q))
    if v <= eps or u + v >= 1.0 - eps:
        return False
    t = f * float(np.dot(e2, q))
    return eps < t < 1.0 - eps


def _tri_tri_intersect(tri_a: np.ndarray, tri_b: np.ndarray) -> bool:
    """Return True iff closed 3D triangles ``tri_a`` and ``tri_b`` strictly intersect."""
    # Quick AABB reject
    if np.any(tri_a.max(axis=0) < tri_b.min(axis=0) - 1e-7) or np.any(tri_b.max(axis=0) < tri_a.min(axis=0) - 1e-7):
        return False
    a0, a1, a2 = tri_a[0], tri_a[1], tri_a[2]
    b0, b1, b2 = tri_b[0], tri_b[1], tri_b[2]
    # Check each edge of A against triangle B, and each edge of B against triangle A
    for p, q in ((a0, a1), (a1, a2), (a2, a0)):
        if _segment_triangle_intersect(p, q, b0, b1, b2):
            return True
    for p, q in ((b0, b1), (b1, b2), (b2, b0)):
        if _segment_triangle_intersect(p, q, a0, a1, a2):
            return True
    return False


def _point_inside_shell(pt: np.ndarray, shell: SolidMesh) -> bool:
    """Exact ray-casting parity test (irrational ray avoids vertex/edge grazing)."""
    v = shell.vertices
    f = shell.faces
    v0 = v[f[:, 0]]
    v1 = v[f[:, 1]]
    v2 = v[f[:, 2]]
    ray_dir = np.array([1.0, 0.37192341, 0.21738917], dtype=np.float64)
    ray_dir /= np.linalg.norm(ray_dir)

    e1 = v1 - v0
    e2 = v2 - v0
    h = np.cross(ray_dir, e2)
    a = np.einsum("ij,ij->i", e1, h)
    valid = np.abs(a) > 1e-10
    if not np.any(valid):
        return False
    inv_a = np.where(valid, 1.0 / np.where(valid, a, 1.0), 0.0)
    s = pt - v0
    u = inv_a * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, e1)
    vv = inv_a * np.einsum("j,ij->i", ray_dir, q)
    t = inv_a * np.einsum("ij,ij->i", e2, q)
    hits = valid & (u >= 0.0) & (vv >= 0.0) & (u + vv <= 1.0) & (t > 1e-7)
    return bool(int(np.sum(hits)) % 2 == 1)


def _shells_intersect(sa: SolidMesh, sb: SolidMesh) -> bool:
    """Return True iff two watertight single shells intersect or one contains the other."""
    va, fa = sa.vertices, sa.faces
    vb, fb = sb.vertices, sb.faces
    mn_a, mx_a = va.min(axis=0), va.max(axis=0)
    mn_b, mx_b = vb.min(axis=0), vb.max(axis=0)
    if not _aabb_overlap(mn_a, mx_a, mn_b, mx_b, tol=-1e-5):
        return False

    # Restrict to triangles intersecting the overlap box
    ov_mn = np.maximum(mn_a, mn_b) - 1e-5
    ov_mx = np.minimum(mx_a, mx_b) + 1e-5

    ta = va[fa]  # (Na, 3, 3)
    ta_mn = ta.min(axis=1)
    ta_mx = ta.max(axis=1)
    mask_a = np.all(ta_mx >= ov_mn, axis=1) & np.all(ta_mn <= ov_mx, axis=1)

    tb = vb[fb]
    tb_mn = tb.min(axis=1)
    tb_mx = tb.max(axis=1)
    mask_b = np.all(tb_mx >= ov_mn, axis=1) & np.all(tb_mn <= ov_mx, axis=1)

    if np.any(mask_a) and np.any(mask_b):
        sub_a = ta[mask_a]
        sub_a_mn = ta_mn[mask_a]
        sub_a_mx = ta_mx[mask_a]
        sub_b = tb[mask_b]
        sub_b_mn = tb_mn[mask_b]
        sub_b_mx = tb_mx[mask_b]
        for ia in range(len(sub_a)):
            cand = np.all(sub_b_mx >= sub_a_mn[ia] - 1e-6, axis=1) & np.all(
                sub_b_mn <= sub_a_mx[ia] + 1e-6, axis=1
            )
            for ib in np.flatnonzero(cand):
                if _tri_tri_intersect(sub_a[ia], sub_b[ib]):
                    return True

    # Containment test (only if one shell's bbox fits inside the other)
    if np.all(mn_a >= mn_b - 1e-5) and np.all(mx_a <= mx_b + 1e-5):
        if _point_inside_shell(va[0], sb):
            return True
    if np.all(mn_b >= mn_a - 1e-5) and np.all(mx_b <= mx_a + 1e-5):
        if _point_inside_shell(vb[0], sa):
            return True
    return False


def check_s5_intra_clashes(parts: dict[str, S5PartBuild]) -> dict[str, Any]:
    """Verify exact 3D solid-solid collision freedom across all S5 parts in global frame."""
    world_shells: dict[str, list[tuple[SolidMesh, np.ndarray, np.ndarray]]] = {}
    world_bboxes: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for pid, build in parts.items():
        wm = transform_mesh(
            build.mesh,
            translation=build.design.world_origin_mm,
            rotation_deg=build.design.world_rotation_deg,
            name=pid,
        )
        mn, mx = wm.vertices.min(axis=0), wm.vertices.max(axis=0)
        world_bboxes[pid] = (mn, mx)
        sh_list: list[tuple[SolidMesh, np.ndarray, np.ndarray]] = []
        for sh in split_shells(wm):
            sh_list.append((sh, sh.vertices.min(axis=0), sh.vertices.max(axis=0)))
        world_shells[pid] = sh_list

    pids = sorted(parts.keys())
    clashes: list[dict[str, Any]] = []
    pairs_checked = 0
    for i in range(len(pids)):
        pa = pids[i]
        mna, mxa = world_bboxes[pa]
        for j in range(i + 1, len(pids)):
            pb = pids[j]
            pairs_checked += 1
            mnb, mxb = world_bboxes[pb]
            if not _aabb_overlap(mna, mxa, mnb, mxb, tol=-1e-5):
                continue
            hit = False
            for sa, smna, smxa in world_shells[pa]:
                if hit:
                    break
                for sb, smnb, smxb in world_shells[pb]:
                    if not _aabb_overlap(smna, smxa, smnb, smxb, tol=-1e-5):
                        continue
                    if _shells_intersect(sa, sb):
                        clashes.append({"part_a": pa, "part_b": pb})
                        hit = True
                        break

    return {
        "parts_checked": len(pids),
        "pairs_checked": pairs_checked,
        "solid_clashes": len(clashes),
        "clashes": clashes,
        "passed": len(clashes) == 0,
    }


def compute_s5_thermal_and_stackup_audits() -> dict[str, Any]:
    """Compute NIST bakeout/cryo clearance & GD&T alignment stackups for S5."""
    # 1. 150 C (423.15 K) UHV bakeout radial expansion of S5.1-01 inside S5.1-02 jacket
    eps_316_bake = integrated_thermal_contraction("316LN", 423.15)
    r_out_hot = cold_dimension_mm(CHAMBER_R_OUT_MM, "316LN", 423.15)
    jacket_hot_radial_clr = round(195.0 - r_out_hot, 4)

    # 2. Exp125 Ti-6Al-4V magnet former (OD=352 mm @ 4 K) inside 316LN chamber (ID=364 mm)
    mag_clr = check_cold_clearance(
        "316LN", "Ti-6Al-4V",
        nominal_outer_id_mm=364.0, nominal_inner_od_mm=352.0,
        t_cold_k=4.0, min_required_radial_clearance_mm=5.0,
        outer_id_tol_mm=0.20, inner_od_tol_mm=0.20,
    )

    # 3. +Y 808 nm Flash beam radial margin to CF63 sapphire viewport clear aperture (4.00 mm nom)
    flash_stack = check_tolerance_stack(
        [
            ToleranceContributor("cf63_ca_radius", 22.00, 0.05, -0.05, sign=+1.0),
            ToleranceContributor("beam_808_radius", 18.00, 0.15, -0.15, sign=-1.0),
            ToleranceContributor("chamber_port_axis", 0.00, 0.10, -0.10, sign=-1.0),
            ToleranceContributor("shutter_homogenizer_align", 0.00, 0.25, -0.25, sign=-1.0),
        ],
        target_min_mm=3.0,
        target_max_mm=5.0,
    )

    # 4. +X Load-Lock transfer lateral clearance (80 mm carrier inside CF100 101.6 mm bore)
    transfer_stack = check_tolerance_stack(
        [
            ToleranceContributor("cf100_bore_half", 50.80, 0.10, -0.10, sign=+1.0),
            ToleranceContributor("carrier_half_width", 40.00, 0.05, -0.05, sign=-1.0),
            ToleranceContributor("transfer_arm_runout_500mm", 0.00, 0.20, -0.20, sign=-1.0),
            ToleranceContributor("gate_valve_coaxiality", 0.00, 0.15, -0.15, sign=-1.0),
        ],
        target_min_mm=9.5,
        target_max_mm=12.0,
    )

    return {
        "bakeout_150C_316LN_strain": round(eps_316_bake, 6),
        "chamber_r_out_423K_mm": round(r_out_hot, 4),
        "jacket_radial_clearance_423K_mm": jacket_hot_radial_clr,
        "bakeout_clearance_pass": jacket_hot_radial_clr >= 2.0,
        "magnet_former_cold_clearance": mag_clr.to_dict(),
        "flash_808nm_optical_stackup": flash_stack.to_dict(),
        "loadlock_transfer_stackup": transfer_stack.to_dict(),
    }


def build_s5_parts() -> dict[str, S5PartBuild]:
    """Build all 23/23 physical parts of S5 (UHV vessel/pumps + flash/808nm/MBE)."""
    from hardware.cad_parts.subsystems.s5_optics_mbe import build_s5_optics_mbe_parts

    parts = build_s5_uhv_pumps_parts()
    parts.update(build_s5_optics_mbe_parts())
    expected = set(list_physical_part_ids("S5"))
    if set(parts.keys()) != expected:
        raise RuntimeError(
            f"S5 part coverage mismatch: missing={sorted(expected - set(parts.keys()))}, "
            f"extra={sorted(set(parts.keys()) - expected)}"
        )
    return {pid: parts[pid] for pid in list_physical_part_ids("S5")}


def export_all(out_dir: Path | str | None = None) -> dict[str, Any]:
    """Export all 23/23 S5 physical parts (.stl/.step/.dxf/.svg/.scad + .json manifests)."""
    target_dir = Path(out_dir) if out_dir is not None else DEFAULT_S5_OUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    parts = build_s5_parts()
    clash_report = check_s5_intra_clashes(parts)
    thermal_audits = compute_s5_thermal_and_stackup_audits()

    results: dict[str, PartArtifactResult] = {}
    total_mass_kg = 0.0
    total_triangles = 0

    for pid, build in parts.items():
        res = export_part_artifacts(
            build.design,
            build.mesh,
            target_dir,
            scad_features=build.scad_features,
            step_mesh=build.step_mesh,
            density_kg_m3=build.density_kg_m3,
            flat=True,
        )
        results[pid] = res
        total_mass_kg += res.mass_kg
        total_triangles += res.triangle_count

        shell_list = split_shells(build.mesh)
        shell_ties = [
            {
                "shell_index": idx,
                "bbox_min_mm": [round(float(v), 4) for v in sh.bbox()[0]],
                "bbox_max_mm": [round(float(v), 4) for v in sh.bbox()[1]],
                "fea_tie_constraint": "BONDED_WELD_OR_BOLT_ASSEMBLY" if len(shell_list) > 1 else "MONOLITHIC_SOLID",
            }
            for idx, sh in enumerate(shell_list)
        ]
        part_manifest: dict[str, Any] = {
            "part_id": pid,
            "subsystem": "S5",
            "design": build.design.to_dict(),
            "artifacts": res.to_dict(),
            "shell_tie_manifest": shell_ties,
            "epistemic": {
                "design_maturity": DESIGN_MATURITY,
                "no_lab_measurement": NO_LAB_MEASUREMENT,
                "iec61508_certified": IEC61508_CERTIFIED,
                "semi_s2_certified": SEMI_S2_CERTIFIED,
            },
        }
        if build.reconciliation is not None:
            part_manifest["reconciliation"] = build.reconciliation
        (target_dir / f"{pid}.json").write_text(
            json.dumps(part_manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # Check S7.SAFETY-02 inclined +Y load-lock shroud keepout envelope around relocated S5.5 assembly
    s55_ids = {"S5.5-01", "S5.5-02", "S5.5-03", "S5.5-04"}
    s55_mins = []
    s55_maxs = []
    for pid in s55_ids:
        wm = transform_mesh(
            parts[pid].mesh,
            translation=parts[pid].design.world_origin_mm,
            rotation_deg=parts[pid].design.world_rotation_deg,
        )
        mn, mx = wm.bbox()
        s55_mins.append(mn)
        s55_maxs.append(mx)
    s55_env_min = [round(min(v[k] for v in s55_mins), 3) for k in range(3)]
    s55_env_max = [round(max(v[k] for v in s55_maxs), 3) for k in range(3)]
    s55_extents = [round(s55_env_max[k] - s55_env_min[k], 3) for k in range(3)]
    shroud_fits = (
        s55_extents[0] <= 240.0 and s55_extents[1] <= 260.0 and s55_extents[2] <= 250.0
    )

    summary_manifest = {
        "subsystem": "S5",
        "title": "UHV Process Chamber, Vacuum Pumps, Flash/808 nm Laser Optics & 28Si LT-MBE",
        "physical_part_count": len(results),
        "excluded_non_solid_part_ids": ["S5.4-02"],
        "all_watertight": all(r.watertight for r in results.values()),
        "all_artifacts_valid": all(r.all_valid for r in results.values()),
        "total_mass_kg": round(total_mass_kg, 4),
        "total_triangles": total_triangles,
        "intra_subsystem_clash_audit": clash_report,
        "s7_safety_02_shroud_fit": {
            "shroud_envelope_mm": [280.0, 260.0, 220.0],
            "s55_external_bbox_min_mm": s55_env_min,
            "s55_external_bbox_max_mm": s55_env_max,
            "s55_external_extents_mm": s55_extents,
            "fits_inside_shroud_with_margin": shroud_fits,
        },
        "thermal_and_tolerance_audits": thermal_audits,
        "reconciliations": S5_RECONCILIATIONS,
        "epistemic": {
            "design_maturity": DESIGN_MATURITY,
            "no_lab_measurement": NO_LAB_MEASUREMENT,
            "iec61508_certified": IEC61508_CERTIFIED,
            "semi_s2_certified": SEMI_S2_CERTIFIED,
        },
        "parts": {pid: res.to_dict() for pid, res in results.items()},
    }
    (target_dir / "S5_manifest.json").write_text(
        json.dumps(summary_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary_manifest


if __name__ == "__main__":
    summary = export_all()
    print(
        f"S5 exported: {summary['physical_part_count']}/23 parts | "
        f"watertight={summary['all_watertight']} | valid={summary['all_artifacts_valid']} | "
        f"clashes={summary['intra_subsystem_clash_audit']['solid_clashes']} | "
        f"mass={summary['total_mass_kg']:.2f} kg"
    )
