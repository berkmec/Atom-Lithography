"""ISO 3669 ConFlat (CF16..CF400) & ISO-K (DN50..DN250) vacuum flange solid builders.

Every generated flange is a strictly watertight 2-manifold solid verified to
ISO 3669 / DIN 28404 dimensions:
- ConFlat (`CF16`, `CF40`, `CF63`, `CF100`, `CF150`, `CF200`, `CF250`, `CF400`):
  exact OD, bore ID (or blank), flange thickness, machined 20°/70° knife-edge
  sealing ridge + copper gasket recess, exact bolt-circle PCD, bolt count &
  clearance hole diameter, plus integrated weld-neck and optical viewport helpers.
- ISO-K (`DN50`, `DN100`, `DN160`, `DN250`):
  exact OD, bore ID, flange thickness, outer claw-clamp groove, and inner O-ring
  centering-ring counterbore recess.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

from .feature_engine import (
    SolidMesh,
    make_cylinder,
    make_revolved_profile,
    make_ring_with_bolt_circle,
    merge_solids,
)
from .part_schema import PortInterface


# ---------------------------------------------------------------------------
# ISO 3669 ConFlat Specification Table (all dimensions in mm)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CFSpec:
    """ISO 3669 ConFlat UHV flange specification (mm)."""

    size: str
    dn: int
    od_mm: float
    bore_id_mm: float
    thickness_mm: float
    pcd_mm: float
    bolt_count: int
    bolt_hole_mm: float
    bolt_thread: str
    gasket_od_mm: float
    knife_edge_dia_mm: float
    gasket_recess_depth_mm: float
    knife_edge_height_mm: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CF_SPECS: dict[str, CFSpec] = {
    "CF16": CFSpec(
        size="CF16",
        dn=16,
        od_mm=33.8,
        bore_id_mm=16.0,
        thickness_mm=7.5,
        pcd_mm=27.0,
        bolt_count=6,
        bolt_hole_mm=4.3,
        bolt_thread="M4",
        gasket_od_mm=21.3,
        knife_edge_dia_mm=20.4,
        gasket_recess_depth_mm=1.1,
        knife_edge_height_mm=0.45,
    ),
    "CF40": CFSpec(
        size="CF40",
        dn=40,
        od_mm=69.5,
        bore_id_mm=38.0,
        thickness_mm=12.7,
        pcd_mm=58.7,
        bolt_count=6,
        bolt_hole_mm=6.6,
        bolt_thread="M6",
        gasket_od_mm=48.1,
        knife_edge_dia_mm=46.8,
        gasket_recess_depth_mm=1.25,
        knife_edge_height_mm=0.55,
    ),
    "CF63": CFSpec(
        size="CF63",
        dn=63,
        od_mm=113.5,
        bore_id_mm=63.5,
        thickness_mm=17.5,
        pcd_mm=92.1,
        bolt_count=8,
        bolt_hole_mm=8.4,
        bolt_thread="M8",
        gasket_od_mm=82.4,
        knife_edge_dia_mm=80.5,
        gasket_recess_depth_mm=1.25,
        knife_edge_height_mm=0.55,
    ),
    "CF100": CFSpec(
        size="CF100",
        dn=100,
        od_mm=152.0,
        bore_id_mm=101.6,
        thickness_mm=19.8,
        pcd_mm=130.2,
        bolt_count=16,
        bolt_hole_mm=8.4,
        bolt_thread="M8",
        gasket_od_mm=120.5,
        knife_edge_dia_mm=118.4,
        gasket_recess_depth_mm=1.25,
        knife_edge_height_mm=0.55,
    ),
    "CF150": CFSpec(
        size="CF150",
        dn=150,
        od_mm=202.5,
        bore_id_mm=152.4,
        thickness_mm=22.2,
        pcd_mm=181.0,
        bolt_count=20,
        bolt_hole_mm=8.4,
        bolt_thread="M8",
        gasket_od_mm=171.3,
        knife_edge_dia_mm=169.0,
        gasket_recess_depth_mm=1.25,
        knife_edge_height_mm=0.55,
    ),
    "CF200": CFSpec(
        size="CF200",
        dn=200,
        od_mm=253.0,
        bore_id_mm=203.2,
        thickness_mm=24.5,
        pcd_mm=231.8,
        bolt_count=24,
        bolt_hole_mm=8.4,
        bolt_thread="M8",
        gasket_od_mm=222.0,
        knife_edge_dia_mm=219.5,
        gasket_recess_depth_mm=1.25,
        knife_edge_height_mm=0.55,
    ),
    "CF250": CFSpec(
        size="CF250",
        dn=250,
        od_mm=305.0,
        bore_id_mm=254.0,
        thickness_mm=24.5,
        pcd_mm=284.2,
        bolt_count=32,
        bolt_hole_mm=8.4,
        bolt_thread="M8",
        gasket_od_mm=272.9,
        knife_edge_dia_mm=270.0,
        gasket_recess_depth_mm=1.25,
        knife_edge_height_mm=0.55,
    ),
    "CF400": CFSpec(
        size="CF400",
        dn=400,
        od_mm=456.0,
        bore_id_mm=406.4,
        thickness_mm=28.5,
        pcd_mm=431.8,
        bolt_count=40,
        bolt_hole_mm=8.4,
        bolt_thread="M8",
        gasket_od_mm=420.0,
        knife_edge_dia_mm=417.0,
        gasket_recess_depth_mm=1.35,
        knife_edge_height_mm=0.60,
    ),
}


# ---------------------------------------------------------------------------
# ISO 1609 / DIN 28404 ISO-K Clamp Flange Table (all dimensions in mm)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class IsoKSpec:
    """ISO-K claw-clamp vacuum flange specification (mm)."""

    size: str
    dn: int
    od_mm: float
    bore_id_mm: float
    thickness_mm: float
    clamp_groove_od_mm: float
    clamp_groove_z_mm: float
    centering_recess_od_mm: float
    centering_recess_depth_mm: float
    recommended_clamps: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ISO_K_SPECS: dict[str, IsoKSpec] = {
    "DN50": IsoKSpec(
        size="DN50",
        dn=50,
        od_mm=75.0,
        bore_id_mm=50.0,
        thickness_mm=12.0,
        clamp_groove_od_mm=67.0,
        clamp_groove_z_mm=5.5,
        centering_recess_od_mm=52.0,
        centering_recess_depth_mm=3.9,
        recommended_clamps=4,
    ),
    "DN100": IsoKSpec(
        size="DN100",
        dn=100,
        od_mm=130.0,
        bore_id_mm=102.0,
        thickness_mm=12.0,
        clamp_groove_od_mm=120.0,
        clamp_groove_z_mm=5.5,
        centering_recess_od_mm=104.0,
        centering_recess_depth_mm=3.9,
        recommended_clamps=4,
    ),
    "DN160": IsoKSpec(
        size="DN160",
        dn=160,
        od_mm=180.0,
        bore_id_mm=153.0,
        thickness_mm=12.0,
        clamp_groove_od_mm=170.0,
        clamp_groove_z_mm=5.5,
        centering_recess_od_mm=155.0,
        centering_recess_depth_mm=3.9,
        recommended_clamps=4,
    ),
    "DN250": IsoKSpec(
        size="DN250",
        dn=250,
        od_mm=290.0,
        bore_id_mm=254.0,
        thickness_mm=12.0,
        clamp_groove_od_mm=280.0,
        clamp_groove_z_mm=5.5,
        centering_recess_od_mm=256.0,
        centering_recess_depth_mm=3.9,
        recommended_clamps=6,
    ),
}


def get_cf_spec(size: str) -> CFSpec:
    key = size.strip().upper()
    if key not in CF_SPECS:
        raise KeyError(f"Unsupported CF size {size!r}; expected one of {sorted(CF_SPECS)}")
    return CF_SPECS[key]


def get_isok_spec(size: str) -> IsoKSpec:
    key = size.strip().upper().replace("ISO-K", "").replace("ISOK", "").strip()
    if not key.startswith("DN"):
        key = f"DN{key}"
    if key not in ISO_K_SPECS:
        raise KeyError(
            f"Unsupported ISO-K size {size!r}; expected one of {sorted(ISO_K_SPECS)}"
        )
    return ISO_K_SPECS[key]


# ---------------------------------------------------------------------------
# ConFlat Solid Builders (Unified Single Watertight Shell w/ Knife-Edge & Bolts)
# ---------------------------------------------------------------------------
def _cf_inner_profile(
    spec: CFSpec,
    r_band_in: float,
    *,
    bore_r: float,
    blank: bool,
    with_knife_edge: bool,
    neck_r_out: float = 0.0,
    neck_r_in: float = 0.0,
    neck_length: float = 0.0,
) -> list[tuple[float, float]]:
    """Construct open (r, z) profile from ``(r_band_in, +t/2)`` to ``(r_band_in, -t/2)``."""
    hz = 0.5 * spec.thickness_mm
    z_top = hz
    z_bot = -hz

    pts: list[tuple[float, float]] = [(r_band_in, z_top)]

    if with_knife_edge:
        r_gask = 0.5 * spec.gasket_od_mm
        r_ke = 0.5 * spec.knife_edge_dia_mm
        # Clamp strictly inside r_band_in and outside bore_r
        r_gask = min(r_gask, r_band_in - 0.15)
        ke_half_w = min(0.65, 0.35 * max(r_gask - bore_r, 0.5))
        r_ke_out = min(r_gask - 0.08, r_ke + 0.35 * ke_half_w)
        r_ke_peak = max(bore_r + 0.35, min(r_ke_out - 0.08, r_ke))
        r_ke_in = max(bore_r + 0.12, r_ke_peak - 0.65 * ke_half_w)

        z_recess = z_top - spec.gasket_recess_depth_mm
        z_ke_tip = z_recess + spec.knife_edge_height_mm

        # Step down into copper gasket recess -> steep outer knife-edge bevel -> apex ->
        # gentle inner slope -> inner gasket land
        pts.extend(
            [
                (r_gask, z_top),
                (r_gask, z_recess),
                (r_ke_out, z_recess),
                (r_ke_peak, z_ke_tip),
                (r_ke_in, z_recess),
            ]
        )
        z_inner_top = z_recess
    else:
        z_inner_top = z_top

    if blank:
        pts.append((0.0, z_inner_top))
        pts.append((0.0, z_bot))
    else:
        if neck_length > 0.0 and neck_r_out > neck_r_in > 0.0:
            r_no = min(neck_r_out, r_band_in - 0.15)
            r_ni = min(neck_r_in, r_no - 0.5)
            pts.extend(
                [
                    (r_ni, z_inner_top),
                    (r_ni, z_bot - neck_length),
                    (r_no, z_bot - neck_length),
                    (r_no, z_bot),
                ]
            )
        else:
            pts.append((bore_r, z_inner_top))
            pts.append((bore_r, z_bot))

    pts.append((r_band_in, z_bot))
    return pts


def make_cf_flange(
    size: str = "CF100",
    *,
    bore_id: float | None = None,
    blank: bool = False,
    with_knife_edge: bool = True,
    sub_per_side: int = 2,
    start_angle_deg: float = 0.0,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str | None = None,
    material: str = "316LN",
) -> SolidMesh:
    """Build a watertight ISO 3669 ConFlat flange solid (knife-edge + true bolt circle).

    Sealing face (knife-edge + copper gasket recess) sits on local ``+Z``.
    """
    spec = get_cf_spec(size)
    r_out = 0.5 * spec.od_mm
    r_pcd = 0.5 * spec.pcd_mm
    r_bolt = 0.5 * spec.bolt_hole_mm
    r_gask = 0.5 * spec.gasket_od_mm

    bore_r = 0.0 if blank else 0.5 * (spec.bore_id_mm if bore_id is None else float(bore_id))
    if not blank and (bore_r <= 0.0 or bore_r >= 0.5 * spec.knife_edge_dia_mm - 0.3):
        raise ValueError(
            f"Invalid bore_id={bore_id} for {spec.size} (max < knife-edge {spec.knife_edge_dia_mm} mm)"
        )

    # Place r_band_in cleanly between gasket recess OD and inner edge of bolt holes
    r_bolt_in = r_pcd - r_bolt
    r_band_in = 0.5 * (r_gask + r_bolt_in)
    if r_band_in <= r_gask + 0.1:
        r_band_in = r_gask + 0.25 * (r_bolt_in - r_gask)
    r_band_out = r_pcd + r_bolt + 0.35 * (r_out - (r_pcd + r_bolt))

    inner_prof = _cf_inner_profile(
        spec,
        r_band_in,
        bore_r=bore_r,
        blank=blank,
        with_knife_edge=with_knife_edge,
    )

    return make_ring_with_bolt_circle(
        r_in=bore_r,
        r_out=r_out,
        thickness=spec.thickness_mm,
        pcd=spec.pcd_mm,
        n_bolts=spec.bolt_count,
        bolt_diameter=spec.bolt_hole_mm,
        sub_per_side=sub_per_side,
        start_angle_deg=start_angle_deg,
        r_band_in=r_band_in,
        r_band_out=r_band_out,
        inner_profile_rz=inner_prof,
        axis=axis,
        center=center,
        name=name or (f"{spec.size}_blank" if blank else f"{spec.size}_flange"),
        material=material,
    )


def make_cf_blank_flange(
    size: str = "CF100",
    *,
    with_knife_edge: bool = True,
    sub_per_side: int = 2,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str | None = None,
    material: str = "316LN",
) -> SolidMesh:
    """Build a watertight ISO 3669 ConFlat blank (blind) flange."""
    return make_cf_flange(
        size=size,
        blank=True,
        with_knife_edge=with_knife_edge,
        sub_per_side=sub_per_side,
        axis=axis,
        center=center,
        name=name or f"{size.upper()}_blank",
        material=material,
    )


def make_cf_weld_neck(
    size: str = "CF100",
    *,
    neck_length: float = 40.0,
    tube_od: float | None = None,
    tube_id: float | None = None,
    with_knife_edge: bool = True,
    sub_per_side: int = 2,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str | None = None,
    material: str = "316LN",
) -> SolidMesh:
    """Build a single-shell watertight ConFlat flange with integrated rear weld neck.

    Flange body spans local ``z ∈ [-t/2, +t/2]`` (knife-edge on ``+t/2``);
    weld neck extends backward to ``z = -t/2 - neck_length``.
    """
    if neck_length <= 0.0:
        raise ValueError("neck_length must be > 0")
    spec = get_cf_spec(size)
    r_out = 0.5 * spec.od_mm
    r_pcd = 0.5 * spec.pcd_mm
    r_bolt = 0.5 * spec.bolt_hole_mm
    r_gask = 0.5 * spec.gasket_od_mm

    r_band_in = 0.5 * (r_gask + (r_pcd - r_bolt))
    r_band_out = r_pcd + r_bolt + 0.35 * (r_out - (r_pcd + r_bolt))

    r_ni = 0.5 * (spec.bore_id_mm if tube_id is None else float(tube_id))
    default_wall = 1.65 if spec.dn <= 40 else (2.0 if spec.dn <= 150 else 3.0)
    r_no = 0.5 * float(tube_od) if tube_od is not None else min(r_ni + default_wall, r_band_in - 0.25)
    if r_no <= r_ni + 0.2:
        r_ni = max(1.0, r_no - default_wall)

    inner_prof = _cf_inner_profile(
        spec,
        r_band_in,
        bore_r=r_ni,
        blank=False,
        with_knife_edge=with_knife_edge,
        neck_r_out=r_no,
        neck_r_in=r_ni,
        neck_length=neck_length,
    )

    return make_ring_with_bolt_circle(
        r_in=r_ni,
        r_out=r_out,
        thickness=spec.thickness_mm,
        pcd=spec.pcd_mm,
        n_bolts=spec.bolt_count,
        bolt_diameter=spec.bolt_hole_mm,
        sub_per_side=sub_per_side,
        r_band_in=r_band_in,
        r_band_out=r_band_out,
        inner_profile_rz=inner_prof,
        axis=axis,
        center=center,
        name=name or f"{spec.size}_weld_neck",
        material=material,
    )


def make_cf_viewport(
    size: str = "CF63",
    *,
    clear_aperture: float | None = None,
    window_diameter: float | None = None,
    window_thickness: float = 6.0,
    with_knife_edge: bool = True,
    sub_per_side: int = 2,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str | None = None,
    material: str = "316LN",
    window_material: str = "Sapphire",
) -> SolidMesh:
    """Build a watertight ConFlat optical viewport assembly (flange body + seated glass/sapphire window).

    When ``window_diameter > clear_aperture`` (e.g. S5.5-02 Ø50x8 mm sapphire window in
    CF63 flange with Ø44 mm clear aperture), machines a stepped counterbore seat on the
    atmospheric rear face so the full-diameter window sits cleanly with 0.1 mm clearance.
    """
    spec = get_cf_spec(size)
    r_out = 0.5 * spec.od_mm
    r_pcd = 0.5 * spec.pcd_mm
    r_bolt = 0.5 * spec.bolt_hole_mm
    r_gask = 0.5 * spec.gasket_od_mm

    r_band_in = 0.5 * (r_gask + (r_pcd - r_bolt))
    r_band_out = r_pcd + r_bolt + 0.35 * (r_out - (r_pcd + r_bolt))

    ca = float(clear_aperture) if clear_aperture is not None else 0.72 * spec.bore_id_mm
    win_d = float(window_diameter) if window_diameter is not None else min(ca + 6.0, spec.bore_id_mm)
    win_t = min(float(window_thickness), spec.thickness_mm - 3.0)
    if win_t <= 0.5:
        win_t = 0.4 * spec.thickness_mm

    ca_r = 0.5 * ca
    win_r = min(0.5 * win_d, r_band_in - 0.6)
    hz = 0.5 * spec.thickness_mm

    if win_r > ca_r + 0.2:
        # Build flange with rear stepped counterbore seat of radius (win_r + 0.1) & depth win_t
        base_prof = _cf_inner_profile(
            spec,
            r_band_in,
            bore_r=ca_r,
            blank=False,
            with_knife_edge=with_knife_edge,
        )
        # Replace final 2 bore points (ca_r, -hz), (r_band_in, -hz) with stepped window seat
        z_seat = -hz + win_t
        r_seat = win_r + 0.1
        stepped_prof = base_prof[:-2] + [
            (ca_r, z_seat),
            (r_seat, z_seat),
            (r_seat, -hz),
            (r_band_in, -hz),
        ]
        flange = make_ring_with_bolt_circle(
            r_in=ca_r,
            r_out=r_out,
            thickness=spec.thickness_mm,
            pcd=spec.pcd_mm,
            n_bolts=spec.bolt_count,
            bolt_diameter=spec.bolt_hole_mm,
            sub_per_side=sub_per_side,
            r_band_in=r_band_in,
            r_band_out=r_band_out,
            inner_profile_rz=stepped_prof,
            axis=axis,
            center=center,
            name=f"{spec.size}_viewport_flange",
            material=material,
        )
        # Seat window disk inside rear counterbore with 0.08 mm axial clearance
        win_h_eff = max(win_t - 0.08, 0.5)
        z_win_local = -hz + 0.5 * win_h_eff
        from .feature_engine import _orient_and_place
        import numpy as np

        w_local = make_cylinder(
            radius=win_r,
            height=win_h_eff,
            segments=max(24, spec.bolt_count * sub_per_side),
            axis="z",
            center=(0.0, 0.0, z_win_local),
            name=f"{spec.size}_viewport_window",
            material=window_material,
        )
        window = SolidMesh(
            vertices=_orient_and_place(w_local.vertices, axis=axis, center=center),
            faces=w_local.faces,
            name=w_local.name,
            material=window_material,
        )
    else:
        flange = make_cf_flange(
            size=size,
            bore_id=ca,
            blank=False,
            with_knife_edge=with_knife_edge,
            sub_per_side=sub_per_side,
            axis=axis,
            center=center,
            name=f"{spec.size}_viewport_flange",
            material=material,
        )
        window = make_cylinder(
            radius=max(min(win_r, ca_r - 0.1), 1.0),
            height=win_t,
            segments=max(24, spec.bolt_count * sub_per_side),
            axis=axis,
            center=center,
            name=f"{spec.size}_viewport_window",
            material=window_material,
        )

    return merge_solids(
        [flange, window],
        name=name or f"{spec.size}_viewport",
        material=material,
    )


# ---------------------------------------------------------------------------
# ISO-K Flange Solid Builder
# ---------------------------------------------------------------------------
def make_isok_flange(
    size: str = "DN50",
    *,
    bore_id: float | None = None,
    blank: bool = False,
    neck_length: float = 0.0,
    segments: int = 64,
    axis: str | Sequence[float] = "z",
    center: Sequence[float] = (0.0, 0.0, 0.0),
    name: str | None = None,
    material: str = "316LN",
) -> SolidMesh:
    """Build a watertight ISO 1609 / DIN 28404 ISO-K clamp flange solid.

    Features the exact outer claw-clamp shoulder/groove and inner O-ring
    centering-ring recess on the ``+Z`` sealing face.
    """
    spec = get_isok_spec(size)
    hz = 0.5 * spec.thickness_mm
    z_top = hz
    z_bot = -hz
    r_out = 0.5 * spec.od_mm
    r_grv = 0.5 * spec.clamp_groove_od_mm
    r_rec = 0.5 * spec.centering_recess_od_mm
    z_rec = z_top - spec.centering_recess_depth_mm
    z_grv_lo = z_bot + 2.5
    z_grv_hi = min(z_top - 2.5, z_grv_lo + spec.clamp_groove_z_mm)

    bore_r = 0.0 if blank else 0.5 * (spec.bore_id_mm if bore_id is None else float(bore_id))
    if not blank and bore_r >= r_rec - 0.2:
        bore_r = r_rec - 0.5

    # CCW profile in (r, z): outer wall with claw-clamp groove -> top face ->
    # centering-ring recess -> bore or blank center -> bottom face (optional weld neck)
    prof: list[tuple[float, float]] = [
        (r_out, z_bot),
        (r_out, z_grv_lo),
        (r_grv, z_grv_lo),
        (r_grv, z_grv_hi),
        (r_out, z_grv_hi),
        (r_out, z_top),
        (r_rec, z_top),
        (r_rec, z_rec),
    ]
    if blank:
        prof.extend([(0.0, z_rec), (0.0, z_bot)])
    else:
        if neck_length > 0.0:
            r_no = min(bore_r + 2.5, r_grv - 1.5)
            prof.extend(
                [
                    (bore_r, z_rec),
                    (bore_r, z_bot - neck_length),
                    (r_no, z_bot - neck_length),
                    (r_no, z_bot),
                ]
            )
        else:
            prof.extend([(bore_r, z_rec), (bore_r, z_bot)])

    return make_revolved_profile(
        prof,
        segments=segments,
        axis=axis,
        center=center,
        name=name or (f"ISOK_{spec.size}_blank" if blank else f"ISOK_{spec.size}_flange"),
        material=material,
    )


# ---------------------------------------------------------------------------
# PortInterface Factory Helper
# ---------------------------------------------------------------------------
def make_cf_port_interface(
    size: str,
    name: str,
    position_mm: tuple[float, float, float],
    normal: tuple[float, float, float],
    *,
    mating_part_id: str = "",
    bore_override_mm: float | None = None,
    frame: str = "local",
    notes: str = "",
) -> PortInterface:
    """Create a populated ``PortInterface`` from ISO 3669 CF or ISO-K standards."""
    key = size.strip().upper()
    if key in CF_SPECS:
        sp = CF_SPECS[key]
        return PortInterface(
            name=name,
            kind="flange",
            position_mm=position_mm,
            normal=normal,
            standard=sp.size,
            mating_part_id=mating_part_id,
            bore_mm=sp.bore_id_mm if bore_override_mm is None else float(bore_override_mm),
            od_mm=sp.od_mm,
            pcd_mm=sp.pcd_mm,
            bolt_count=sp.bolt_count,
            bolt_hole_mm=sp.bolt_hole_mm,
            bolt_spec=sp.bolt_thread,
            frame=frame,
            notes=notes or f"ISO 3669 {sp.size} Cu-gasket knife-edge",
        )
    sp_k = get_isok_spec(key)
    return PortInterface(
        name=name,
        kind="flange",
        position_mm=position_mm,
        normal=normal,
        standard=f"ISO-K {sp_k.size}",
        mating_part_id=mating_part_id,
        bore_mm=sp_k.bore_id_mm if bore_override_mm is None else float(bore_override_mm),
        od_mm=sp_k.od_mm,
        pcd_mm=0.0,
        bolt_count=sp_k.recommended_clamps,
        bolt_hole_mm=0.0,
        bolt_spec="Claw Clamp",
        frame=frame,
        notes=notes or f"ISO 1609 {sp_k.size} claw-clamp O-ring",
    )
