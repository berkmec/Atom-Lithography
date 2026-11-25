"""Pure-Python ASCII AutoCAD DXF (AC1009 / R12) 2D orthographic writer & validator.

Also provides the shared vectorized orthographic & isometric feature-edge
projection helpers consumed by ``svg_gdt_writer.py`` so DXF and SVG 2D drawings
stay geometrically identical.

DXF Layers emitted:
- ``OUTLINE``    (ACI 7, CONTINUOUS) — visible silhouette & crease feature edges
- ``HIDDEN``     (ACI 8, DASHED)     — occluded internal feature edges (bores/steps)
- ``CENTER``     (ACI 1, CENTER)     — symmetry axes & bolt-circle PCD centerlines
- ``DIMS``       (ACI 5, CONTINUOUS) — overall bounding & feature dimension callouts
- ``TITLEBLOCK`` (ACI 7, CONTINUOUS) — drawing frame & metadata/epistemic stamp
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .feature_engine import MassProperties, SolidMesh, compute_mass_props
from .part_schema import (
    DESIGN_MATURITY,
    IEC61508_CERTIFIED,
    NO_LAB_MEASUREMENT,
    PartDesign,
    PortInterface,
    SEMI_S2_CERTIFIED,
)

REQUIRED_DXF_LAYERS: tuple[str, ...] = (
    "OUTLINE",
    "HIDDEN",
    "CENTER",
    "DIMS",
    "TITLEBLOCK",
)

_DXF_TRANSLIT = str.maketrans(
    {
        "ı": "i",
        "İ": "I",
        "ş": "s",
        "Ş": "S",
        "ğ": "g",
        "Ğ": "G",
        "ü": "u",
        "Ü": "U",
        "ö": "o",
        "Ö": "O",
        "ç": "c",
        "Ç": "C",
        "µ": "u",
        "μ": "u",
        "Ø": "%%c",
        "±": "%%p",
        "°": "%%d",
        "×": "x",
        "–": "-",
        "—": "-",
        "≤": "<=",
        "≥": ">=",
        "→": "->",
    }
)


def _dxf_text(s: str, max_len: int = 120) -> str:
    t = (s or "").translate(_DXF_TRANSLIT)
    t = t.encode("ascii", errors="replace").decode("ascii")
    t = re.sub(r"[\r\n\t]+", " ", t).strip()
    return t[:max_len]


# ---------------------------------------------------------------------------
# Shared Vectorized Orthographic & Isometric Edge Projection Engine
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProjectedView:
    """2D projected visible/hidden line segments & centerlines for one view."""

    name: str
    visible_segments: np.ndarray  # (K, 4) float64: [u1, v1, u2, v2]
    hidden_segments: np.ndarray   # (L, 4) float64: [u1, v1, u2, v2]
    u_min: float
    u_max: float
    v_min: float
    v_max: float
    center_circles: tuple[tuple[float, float, float], ...] = ()  # (cu, cv, radius)

    @property
    def width(self) -> float:
        return max(self.u_max - self.u_min, 1e-6)

    @property
    def height(self) -> float:
        return max(self.v_max - self.v_min, 1e-6)


def _dedup_segments_2d(segs: np.ndarray, tol: float = 1e-3, max_keep: int = 12000) -> np.ndarray:
    """Drop zero-length and duplicate undirected 2D segments."""
    if segs.size == 0:
        return np.zeros((0, 4), dtype=np.float64)
    lens = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
    segs = segs[lens > 1e-4]
    if segs.size == 0:
        return np.zeros((0, 4), dtype=np.float64)

    # Canonicalize segment direction so (p1, p2) == (p2, p1)
    swap = (segs[:, 0] > segs[:, 2] + 1e-9) | (
        (np.abs(segs[:, 0] - segs[:, 2]) <= 1e-9) & (segs[:, 1] > segs[:, 3])
    )
    canon = segs.copy()
    canon[swap] = segs[swap][:, [2, 3, 0, 1]]

    quant = np.round(canon / tol).astype(np.int64)
    _, uniq_idx = np.unique(quant, axis=0, return_index=True)
    out = canon[np.sort(uniq_idx)]
    if len(out) > max_keep:
        # Keep longest segments preferentially (preserves outer silhouettes/large contours)
        seg_len = np.hypot(out[:, 2] - out[:, 0], out[:, 3] - out[:, 1])
        keep = np.argsort(seg_len)[-max_keep:]
        out = out[np.sort(keep)]
    return out


def _extract_projected_edges(
    mesh: SolidMesh,
    u_axis: np.ndarray,
    v_axis: np.ndarray,
    view_dir: np.ndarray,
    *,
    view_name: str,
    crease_deg: float = 22.0,
    ports: tuple[PortInterface, ...] = (),
    max_visible: int = 10000,
    max_hidden: int = 4000,
) -> ProjectedView:
    """Extract silhouette + crease visible/hidden edges projected onto ``(u_axis, v_axis)``."""
    verts = mesh.vertices
    faces = mesh.faces
    n_v = mesh.n_vertices
    n_f = mesh.n_faces

    v0 = verts[faces[:, 0]]
    v1 = verts[faces[:, 1]]
    v2 = verts[faces[:, 2]]
    fn = np.cross(v1 - v0, v2 - v0)
    fn_len = np.linalg.norm(fn, axis=1, keepdims=True)
    fn = np.divide(fn, np.maximum(fn_len, 1e-30))

    front = (fn @ view_dir) > 1e-6

    # Build undirected edge -> (f1, f2) pairing via vectorized sort
    e_u = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2]]).astype(np.int64)
    e_v = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0]]).astype(np.int64)
    e_f = np.concatenate([np.arange(n_f), np.arange(n_f), np.arange(n_f)]).astype(np.int32)
    lo = np.minimum(e_u, e_v)
    hi = np.maximum(e_u, e_v)
    stride = np.int64(n_v)
    keys = lo * stride + hi
    order = np.argsort(keys)
    keys_s = keys[order]
    lo_s = lo[order]
    hi_s = hi[order]
    f_s = e_f[order]

    # Paired manifold edges have keys_s[k] == keys_s[k+1]
    if len(keys_s) >= 2:
        pair_mask = keys_s[:-1] == keys_s[1:]
        # Avoid triple-counting if non-manifold input ever occurred
        if len(pair_mask) >= 2:
            pair_mask[1:] &= ~pair_mask[:-1]
        p_idx = np.nonzero(pair_mask)[0]
        f1 = f_s[p_idx]
        f2 = f_s[p_idx + 1]
        u_i = lo_s[p_idx]
        v_i = hi_s[p_idx]

        dot_n = np.einsum("ij,ij->i", fn[f1], fn[f2])
        cos_thresh = math.cos(math.radians(crease_deg))
        is_sil = front[f1] ^ front[f2]
        is_crease = dot_n < cos_thresh
        keep = is_sil | is_crease

        vis_mask = keep & (is_sil | front[f1] | front[f2])
        hid_mask = keep & (~vis_mask)

        pu = verts @ u_axis
        pv = verts @ v_axis

        def _to_segs(mask: np.ndarray) -> np.ndarray:
            if not np.any(mask):
                return np.zeros((0, 4), dtype=np.float64)
            ia = u_i[mask]
            ib = v_i[mask]
            return np.column_stack([pu[ia], pv[ia], pu[ib], pv[ib]])

        vis_segs = _dedup_segments_2d(_to_segs(vis_mask), max_keep=max_visible)
        hid_segs = _dedup_segments_2d(_to_segs(hid_mask), max_keep=max_hidden)
    else:
        pu = verts @ u_axis
        pv = verts @ v_axis
        vis_segs = np.zeros((0, 4), dtype=np.float64)
        hid_segs = np.zeros((0, 4), dtype=np.float64)

    # Extract projected bolt-circle PCD center circles for ports parallel to view_dir
    center_circles: list[tuple[float, float, float]] = []
    for port in ports:
        pn = np.asarray(port.normal, dtype=np.float64)
        if abs(float(np.dot(pn, view_dir))) > 0.95:
            pp = np.asarray(port.position_mm, dtype=np.float64)
            cu = float(np.dot(pp, u_axis))
            cv = float(np.dot(pp, v_axis))
            if port.pcd_mm > 0.0:
                center_circles.append((cu, cv, 0.5 * port.pcd_mm))
            elif port.bore_mm > 0.0:
                center_circles.append((cu, cv, 0.5 * port.bore_mm))

    return ProjectedView(
        name=view_name,
        visible_segments=vis_segs,
        hidden_segments=hid_segs,
        u_min=float(pu.min()),
        u_max=float(pu.max()),
        v_min=float(pv.min()),
        v_max=float(pv.max()),
        center_circles=tuple(center_circles),
    )


def extract_ortho_view(
    mesh: SolidMesh,
    view: str,
    *,
    ports: tuple[PortInterface, ...] = (),
    crease_deg: float = 22.0,
) -> ProjectedView:
    """Project ``mesh`` onto exact Front (XZ), Top (XY), or Right (YZ) orthographic plane."""
    key = view.strip().lower()
    if key == "front":
        return _extract_projected_edges(
            mesh,
            u_axis=np.array([1.0, 0.0, 0.0]),
            v_axis=np.array([0.0, 0.0, 1.0]),
            view_dir=np.array([0.0, -1.0, 0.0]),
            view_name="FRONT (XZ)",
            crease_deg=crease_deg,
            ports=ports,
        )
    if key == "top":
        return _extract_projected_edges(
            mesh,
            u_axis=np.array([1.0, 0.0, 0.0]),
            v_axis=np.array([0.0, 1.0, 0.0]),
            view_dir=np.array([0.0, 0.0, 1.0]),
            view_name="TOP (XY)",
            crease_deg=crease_deg,
            ports=ports,
        )
    if key == "right":
        return _extract_projected_edges(
            mesh,
            u_axis=np.array([0.0, 1.0, 0.0]),
            v_axis=np.array([0.0, 0.0, 1.0]),
            view_dir=np.array([1.0, 0.0, 0.0]),
            view_name="RIGHT (YZ)",
            crease_deg=crease_deg,
            ports=ports,
        )
    raise ValueError(f"Unsupported orthographic view: {view!r}")


def extract_iso_view(
    mesh: SolidMesh,
    *,
    azimuth_deg: float = 35.0,
    elevation_deg: float = 28.0,
    crease_deg: float = 22.0,
) -> ProjectedView:
    """Project ``mesh`` onto a clean isometric/trimetric engineering wireframe plane."""
    az = math.radians(azimuth_deg)
    el = math.radians(elevation_deg)
    # Viewing vector pointing from origin toward camera
    view_dir = np.array(
        [math.cos(el) * math.cos(az), -math.cos(el) * math.sin(az), math.sin(el)],
        dtype=np.float64,
    )
    view_dir /= np.linalg.norm(view_dir)
    z_world = np.array([0.0, 0.0, 1.0])
    u_axis = np.cross(z_world, view_dir)
    u_axis /= np.linalg.norm(u_axis)
    v_axis = np.cross(view_dir, u_axis)
    v_axis /= np.linalg.norm(v_axis)
    return _extract_projected_edges(
        mesh,
        u_axis=u_axis,
        v_axis=v_axis,
        view_dir=view_dir,
        view_name="ISOMETRIC",
        crease_deg=crease_deg,
        max_visible=7000,
        max_hidden=2500,
    )


# ---------------------------------------------------------------------------
# ASCII AutoCAD DXF R12 (AC1009) Writer
# ---------------------------------------------------------------------------
class _DxfBuilder:
    """Minimal strict AC1009 (AutoCAD R12) group-code emitter."""

    def __init__(self) -> None:
        self._pairs: list[tuple[int, str]] = []

    def add(self, code: int, value: Any) -> None:
        if isinstance(value, float):
            s = f"{value:.4f}"
        else:
            s = str(value)
        self._pairs.append((int(code), s))

    def line(self, layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
        self.add(0, "LINE")
        self.add(8, layer)
        self.add(10, float(x1))
        self.add(20, float(y1))
        self.add(30, 0.0)
        self.add(11, float(x2))
        self.add(21, float(y2))
        self.add(31, 0.0)

    def circle(self, layer: str, cx: float, cy: float, r: float) -> None:
        self.add(0, "CIRCLE")
        self.add(8, layer)
        self.add(10, float(cx))
        self.add(20, float(cy))
        self.add(30, 0.0)
        self.add(40, float(r))

    def rect(self, layer: str, x0: float, y0: float, x1: float, y1: float) -> None:
        self.line(layer, x0, y0, x1, y0)
        self.line(layer, x1, y0, x1, y1)
        self.line(layer, x1, y1, x0, y1)
        self.line(layer, x0, y1, x0, y0)

    def text(
        self,
        layer: str,
        x: float,
        y: float,
        height: float,
        content: str,
        rotation_deg: float = 0.0,
    ) -> None:
        self.add(0, "TEXT")
        self.add(8, layer)
        self.add(10, float(x))
        self.add(20, float(y))
        self.add(30, 0.0)
        self.add(40, max(float(height), 0.1))
        self.add(1, _dxf_text(content))
        if abs(rotation_deg) > 1e-6:
            self.add(50, float(rotation_deg))

    def dim_horizontal(
        self,
        x1: float,
        x2: float,
        y_ref: float,
        y_dim: float,
        label: str,
        text_h: float,
    ) -> None:
        sign = 1.0 if y_dim >= y_ref else -1.0
        ext_over = 0.35 * text_h
        self.line("DIMS", x1, y_ref + sign * 0.2 * text_h, x1, y_dim + sign * ext_over)
        self.line("DIMS", x2, y_ref + sign * 0.2 * text_h, x2, y_dim + sign * ext_over)
        self.line("DIMS", x1, y_dim, x2, y_dim)
        # Tick marks at endpoints
        tk = 0.3 * text_h
        self.line("DIMS", x1 - tk, y_dim - tk, x1 + tk, y_dim + tk)
        self.line("DIMS", x2 - tk, y_dim - tk, x2 + tk, y_dim + tk)
        self.text("DIMS", 0.5 * (x1 + x2) - 0.3 * len(label) * text_h, y_dim + 0.35 * text_h, text_h, label)

    def dim_vertical(
        self,
        x_ref: float,
        x_dim: float,
        y1: float,
        y2: float,
        label: str,
        text_h: float,
    ) -> None:
        sign = 1.0 if x_dim >= x_ref else -1.0
        ext_over = 0.35 * text_h
        self.line("DIMS", x_ref + sign * 0.2 * text_h, y1, x_dim + sign * ext_over, y1)
        self.line("DIMS", x_ref + sign * 0.2 * text_h, y2, x_dim + sign * ext_over, y2)
        self.line("DIMS", x_dim, y1, x_dim, y2)
        tk = 0.3 * text_h
        self.line("DIMS", x_dim - tk, y1 - tk, x_dim + tk, y1 + tk)
        self.line("DIMS", x_dim - tk, y2 - tk, x_dim + tk, y2 + tk)
        self.text("DIMS", x_dim + 0.4 * text_h, 0.5 * (y1 + y2), text_h, label, rotation_deg=90.0)

    def to_string(self) -> str:
        out: list[str] = []
        for code, val in self._pairs:
            out.append(f"{code:3d}")
            out.append(val)
        return "\n".join(out) + "\n"


def write_dxf(
    mesh: SolidMesh,
    path: Path | str,
    *,
    part_design: PartDesign | None = None,
    mass_props: MassProperties | None = None,
) -> Path:
    """Export 3-view orthographic DXF (AC1009 / R12) with 5 manufacturing layers."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ports = part_design.ports if part_design is not None else ()
    mp = mass_props if mass_props is not None else compute_mass_props(
        mesh, material=(part_design.material if part_design else mesh.material)
    )

    front = extract_ortho_view(mesh, "front", ports=ports)
    top = extract_ortho_view(mesh, "top", ports=ports)
    right = extract_ortho_view(mesh, "right", ports=ports)

    # Model-space layout in mm (aligned third-angle projection):
    # Front (XZ) at lower-left, Top (XY) directly above Front, Right (YZ) directly right of Front
    span = max(front.width, front.height, top.height, right.width, 10.0)
    gap = max(0.32 * span, 12.0)
    margin = max(0.22 * span, 10.0)
    text_h = max(0.035 * span, 1.5)
    dim_off = max(0.14 * span, 6.0)

    # Shift each view so local (u_min, v_min) sits at its placement origin
    fx0, fy0 = margin, margin + 4.5 * text_h
    tx0, ty0 = fx0, fy0 + front.height + gap
    rx0, ry0 = fx0 + front.width + gap, fy0

    sheet_w = max(rx0 + right.width + dim_off + margin, fx0 + 38.0 * text_h + margin)
    tb_h = max(9.0 * text_h, 0.25 * span)
    sheet_h = max(ty0 + top.height + dim_off + margin, fy0 + front.height + tb_h + margin)

    dxf = _DxfBuilder()

    # --- HEADER SECTION ---
    dxf.add(0, "SECTION")
    dxf.add(2, "HEADER")
    dxf.add(9, "$ACADVER")
    dxf.add(1, "AC1009")
    dxf.add(9, "$INSUNITS")
    dxf.add(70, 4)  # millimeters
    dxf.add(9, "$EXTMIN")
    dxf.add(10, 0.0)
    dxf.add(20, 0.0)
    dxf.add(30, 0.0)
    dxf.add(9, "$EXTMAX")
    dxf.add(10, sheet_w)
    dxf.add(20, sheet_h)
    dxf.add(30, 0.0)
    dxf.add(0, "ENDSEC")

    # --- TABLES SECTION (LTYPE + LAYER) ---
    dxf.add(0, "SECTION")
    dxf.add(2, "TABLES")

    # LTYPE table
    dxf.add(0, "TABLE")
    dxf.add(2, "LTYPE")
    dxf.add(70, 3)
    for lt_name, lt_desc, pattern in (
        ("CONTINUOUS", "Solid line", []),
        ("DASHED", "Hidden dashed __ __ __", [3.0, -1.5]),
        ("CENTER", "Center ____ _ ____", [6.0, -1.5, 1.5, -1.5]),
    ):
        dxf.add(0, "LTYPE")
        dxf.add(2, lt_name)
        dxf.add(70, 0)
        dxf.add(3, lt_desc)
        dxf.add(72, 65)
        dxf.add(73, len(pattern))
        dxf.add(40, sum(abs(x) for x in pattern))
        for p_val in pattern:
            dxf.add(49, p_val)
    dxf.add(0, "ENDTAB")

    # LAYER table (all 5 required layers)
    layer_defs = (
        ("OUTLINE", 7, "CONTINUOUS"),
        ("HIDDEN", 8, "DASHED"),
        ("CENTER", 1, "CENTER"),
        ("DIMS", 5, "CONTINUOUS"),
        ("TITLEBLOCK", 7, "CONTINUOUS"),
    )
    dxf.add(0, "TABLE")
    dxf.add(2, "LAYER")
    dxf.add(70, len(layer_defs))
    for lname, aci_color, ltype in layer_defs:
        dxf.add(0, "LAYER")
        dxf.add(2, lname)
        dxf.add(70, 0)
        dxf.add(62, aci_color)
        dxf.add(6, ltype)
    dxf.add(0, "ENDTAB")

    dxf.add(0, "ENDSEC")

    # --- ENTITIES SECTION ---
    dxf.add(0, "SECTION")
    dxf.add(2, "ENTITIES")

    def _emit_view(pv: ProjectedView, ox: float, oy: float) -> None:
        du = ox - pv.u_min
        dv = oy - pv.v_min
        for x1, y1, x2, y2 in pv.visible_segments:
            dxf.line("OUTLINE", x1 + du, y1 + dv, x2 + du, y2 + dv)
        for x1, y1, x2, y2 in pv.hidden_segments:
            dxf.line("HIDDEN", x1 + du, y1 + dv, x2 + du, y2 + dv)
        # Symmetry centerlines through view midpoint
        cu = ox + 0.5 * pv.width
        cv = oy + 0.5 * pv.height
        pad = 0.08 * max(pv.width, pv.height)
        dxf.line("CENTER", ox - pad, cv, ox + pv.width + pad, cv)
        dxf.line("CENTER", cu, oy - pad, cu, oy + pv.height + pad)
        # Projected bolt-circle / port center circles
        for pcu, pcv, pr in pv.center_circles:
            dxf.circle("CENTER", pcu + du, pcv + dv, pr)
        # View label
        dxf.text("DIMS", ox, oy - 1.6 * text_h, 0.85 * text_h, pv.name)

    _emit_view(front, fx0, fy0)
    _emit_view(top, tx0, ty0)
    _emit_view(right, rx0, ry0)

    # Bounding dimension annotations on DIMS layer
    ex, ey, ez = mp.extents_mm
    dxf.dim_horizontal(fx0, fx0 + front.width, fy0, fy0 - dim_off, f"X={ex:.2f}", text_h)
    dxf.dim_vertical(fx0, fx0 - dim_off * 0.7, fy0, fy0 + front.height, f"Z={ez:.2f}", text_h)
    dxf.dim_vertical(tx0, tx0 - dim_off * 0.7, ty0, ty0 + top.height, f"Y={ey:.2f}", text_h)
    dxf.dim_horizontal(rx0, rx0 + right.width, ry0, ry0 - dim_off, f"Y={ey:.2f}", text_h)

    # Additional callouts from PartDesign in upper-right notes block
    nx0 = rx0
    ny_cur = ty0 + top.height
    if part_design is not None and part_design.dimensions:
        dxf.text("DIMS", nx0, ny_cur, 0.9 * text_h, "KEY DIMENSIONS (mm):")
        ny_cur -= 1.4 * text_h
        for dc in part_design.dimensions[:8]:
            dxf.text("DIMS", nx0, ny_cur, 0.75 * text_h, f"{dc.label}: {dc.format_text()}")
            ny_cur -= 1.2 * text_h

    # --- TITLEBLOCK ---
    part_id = part_design.part_id if part_design else (mesh.name or out_path.stem)
    part_name = part_design.part_name if part_design else part_id
    mat = part_design.material if part_design else mesh.material
    temp = part_design.temp_stage if part_design else "300 K"
    vac = part_design.vacuum_grade if part_design else "UHV"
    tol = part_design.tolerance_spec if part_design else "ISO 2768-mK"
    maturity = part_design.design_maturity if part_design else DESIGN_MATURITY
    no_lab = part_design.no_lab_measurement if part_design else NO_LAB_MEASUREMENT
    iec = part_design.iec61508_certified if part_design else IEC61508_CERTIFIED
    semi = part_design.semi_s2_certified if part_design else SEMI_S2_CERTIFIED

    # Outer border
    dxf.rect("TITLEBLOCK", 0.0, 0.0, sheet_w, sheet_h)
    tb_w = min(sheet_w * 0.48, max(36.0 * text_h, 0.42 * sheet_w))
    tb_x0 = sheet_w - tb_w
    tb_y0 = 0.0
    tb_y1 = tb_h
    dxf.rect("TITLEBLOCK", tb_x0, tb_y0, sheet_w, tb_y1)
    dxf.line("TITLEBLOCK", tb_x0, tb_y1 - 2.2 * text_h, sheet_w, tb_y1 - 2.2 * text_h)
    dxf.line("TITLEBLOCK", tb_x0, tb_y0 + 2.2 * text_h, sheet_w, tb_y0 + 2.2 * text_h)

    dxf.text("TITLEBLOCK", tb_x0 + text_h, tb_y1 - 1.5 * text_h, 1.0 * text_h, f"PART: {part_id}")
    dxf.text("TITLEBLOCK", tb_x0 + text_h, tb_y1 - 3.6 * text_h, 0.72 * text_h, part_name[:64])
    dxf.text(
        "TITLEBLOCK",
        tb_x0 + text_h,
        tb_y1 - 5.1 * text_h,
        0.68 * text_h,
        f"MAT: {mat[:28]} | TEMP: {temp[:16]} | VAC: {vac[:18]}",
    )
    dxf.text(
        "TITLEBLOCK",
        tb_x0 + text_h,
        tb_y1 - 6.6 * text_h,
        0.68 * text_h,
        f"TOL: {tol[:24]} | MASS: {mp.mass_kg:.4f} kg | UNITS: mm",
    )
    dxf.text(
        "TITLEBLOCK",
        tb_x0 + text_h,
        tb_y0 + 0.8 * text_h,
        0.60 * text_h,
        f"{maturity} | no_lab={str(no_lab).lower()} iec61508={str(iec).lower()} semi_s2={str(semi).lower()}",
    )

    dxf.add(0, "ENDSEC")
    dxf.add(0, "EOF")

    out_path.write_text(dxf.to_string(), encoding="ascii")
    return out_path


# ---------------------------------------------------------------------------
# Strict Independent ASCII DXF Validator
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DxfValidationResult:
    """Validation report for an ASCII AutoCAD R12 (AC1009) DXF file."""

    valid: bool
    version: str
    layers_defined: tuple[str, ...]
    layers_used: tuple[str, ...]
    entity_counts: dict[str, int]
    total_entities: int
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_dxf_file(path: Path | str) -> DxfValidationResult:
    """Strictly parse and validate group-code pairs, sections, layers, and entities of a DXF."""
    errors: list[str] = []
    p = Path(path)
    if not p.is_file():
        return DxfValidationResult(
            valid=False,
            version="",
            layers_defined=(),
            layers_used=(),
            entity_counts={},
            total_entities=0,
            errors=(f"DXF file does not exist: {p}",),
        )

    raw_lines = p.read_text(encoding="ascii", errors="strict").splitlines()
    if len(raw_lines) < 10 or len(raw_lines) % 2 != 0:
        errors.append(f"DXF line count must be even and >= 10, got {len(raw_lines)}")
        return DxfValidationResult(
            valid=False,
            version="",
            layers_defined=(),
            layers_used=(),
            entity_counts={},
            total_entities=0,
            errors=tuple(errors),
        )

    pairs: list[tuple[int, str]] = []
    for i in range(0, len(raw_lines), 2):
        try:
            code = int(raw_lines[i].strip())
        except ValueError:
            errors.append(f"Non-integer group code at line {i + 1}: {raw_lines[i]!r}")
            break
        val = raw_lines[i + 1].strip()
        pairs.append((code, val))

    if not pairs or pairs[-1] != (0, "EOF"):
        errors.append("Missing terminating '0 / EOF' pair")

    # Walk sections
    version = ""
    sections_seen: list[str] = []
    layers_defined: list[str] = []
    layers_used: set[str] = set()
    entity_counts: dict[str, int] = {}

    cur_section: str | None = None
    in_layer_table = False
    cur_record_type = ""

    idx = 0
    n_p = len(pairs)
    while idx < n_p:
        code, val = pairs[idx]
        if code == 0 and val == "SECTION":
            if idx + 1 < n_p and pairs[idx + 1][0] == 2:
                cur_section = pairs[idx + 1][1]
                sections_seen.append(cur_section)
                idx += 2
                continue
            errors.append("SECTION without section name (group code 2)")
        elif code == 0 and val == "ENDSEC":
            cur_section = None
            in_layer_table = False
            cur_record_type = ""
        elif cur_section == "HEADER":
            if code == 9 and val == "$ACADVER" and idx + 1 < n_p:
                version = pairs[idx + 1][1]
        elif cur_section == "TABLES":
            if code == 0 and val == "TABLE" and idx + 1 < n_p and pairs[idx + 1][0] == 2:
                in_layer_table = (pairs[idx + 1][1] == "LAYER")
                cur_record_type = ""
            elif code == 0 and val == "ENDTAB":
                in_layer_table = False
                cur_record_type = ""
            elif in_layer_table and code == 0 and val == "LAYER":
                cur_record_type = "LAYER"
            elif in_layer_table and cur_record_type == "LAYER" and code == 2:
                layers_defined.append(val)
        elif cur_section == "ENTITIES":
            if code == 0:
                cur_record_type = val
                entity_counts[val] = entity_counts.get(val, 0) + 1
            elif code == 8:
                layers_used.add(val)
            elif code in {10, 20, 30, 11, 21, 31, 40, 50}:
                try:
                    fv = float(val)
                    if not math.isfinite(fv):
                        errors.append(f"Non-finite coordinate value {val!r}")
                except ValueError:
                    errors.append(f"Non-numeric coordinate value {val!r}")
        idx += 1

    if version != "AC1009":
        errors.append(f"Expected $ACADVER=AC1009, got {version!r}")
    for req_sec in ("HEADER", "TABLES", "ENTITIES"):
        if req_sec not in sections_seen:
            errors.append(f"Missing required DXF section: {req_sec}")
    for req_layer in REQUIRED_DXF_LAYERS:
        if req_layer not in layers_defined:
            errors.append(f"Missing required DXF layer in TABLES: {req_layer}")
    for must_use in ("OUTLINE", "CENTER", "DIMS", "TITLEBLOCK"):
        if must_use not in layers_used:
            errors.append(f"Required DXF layer {must_use} has zero entities")

    total_ent = sum(entity_counts.values())
    if total_ent == 0:
        errors.append("DXF ENTITIES section is empty")

    return DxfValidationResult(
        valid=(len(errors) == 0),
        version=version,
        layers_defined=tuple(layers_defined),
        layers_used=tuple(sorted(layers_used)),
        entity_counts=entity_counts,
        total_entities=total_ent,
        errors=tuple(errors),
    )
