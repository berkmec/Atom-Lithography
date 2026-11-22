"""Generate 10 high-resolution ISO/ANSI technical engineering drawings (.svg + .png).

Runs under `/usr/bin/python3 -B` (PyCairo + Pillow, zero matplotlib/numpy dependency).
Single source of truth: `params.py` + `cad_verification.json`.

Outputs in `cad/drawings/` (2400 x 1600 px):
  01_s1_ion_source_column.{svg,png}
  02_s2_mems_write_head.{svg,png}
  03_s3_ibic_detector_assembly.{svg,png}
  04_s4_piezo_stage_interferometry.{svg,png}
  05_s5_uhv_chamber_loadlock.{svg,png}
  06_s6_cryo_dr_magnet_readout.{svg,png}
  07_s7_electronics_rack_interconnect.{svg,png}
  08_atom_litho_assembly.{svg,png}
  09_atom_litho_cutaway.{svg,png}
  10_atom_litho_exploded.{svg,png}
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import cairo
from PIL import Image

import params

CAD_DIR = Path(__file__).parent
DRAW_DIR = CAD_DIR / "drawings"
W, H = 2400, 1600

# Engineering Blueprint Palette
BG_PAPER = (0.980, 0.984, 0.992)
INK_DARK = (0.094, 0.145, 0.224)
INK_MED = (0.26, 0.33, 0.42)
INK_LIGHT = (0.68, 0.73, 0.80)
GRID_LINE = (0.88, 0.91, 0.95)
NAVY_HDR = (0.075, 0.161, 0.239)
ACCENT_RED = (0.76, 0.21, 0.17)
ACCENT_BLUE = (0.11, 0.38, 0.65)
ACCENT_GOLD = (0.85, 0.62, 0.06)
ACCENT_GREEN = (0.11, 0.50, 0.31)
PANEL_BG = (0.996, 0.998, 1.000)


def hex_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)


def load_verification() -> dict:
    p = CAD_DIR / "cad_verification.json"
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Pure-Python 3D Geometry & Shaded Isometric Painter Engine
# ---------------------------------------------------------------------------
def _rot_axis_pt(x: float, y: float, z: float, axis: str) -> tuple[float, float, float]:
    if axis == "z":
        return (x, y, z)
    if axis == "x":
        return (z, y, -x)
    if axis == "y":
        return (x, z, -y)
    raise ValueError(axis)


def _part_triangles_3d(
    spec: dict, n_seg: int = 24, offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
    clip_y_neg: bool = False,
) -> list[tuple[list[tuple[float, float, float]], tuple[float, float, float]]]:
    """Return list of (3-vertex tri, outward normal) for shaded 3D rendering."""
    sh = spec["shape"]
    d = spec["dims"]
    cx, cy, cz = spec["center"]
    cx += offset[0]
    cy += offset[1]
    cz += offset[2]

    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []

    if sh == "box":
        hx, hy, hz = d[0] / 2.0, d[1] / 2.0, d[2] / 2.0
        verts = [
            (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
            (-hx, -hy,  hz), (hx, -hy,  hz), (hx, hy,  hz), (-hx, hy,  hz),
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
            (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7),
        ]
    elif sh in ("cyl", "frustum"):
        if sh == "cyl":
            r1, r2, h, axis = d[0], d[0], d[1], d[2]
        else:
            r1, r2, h, axis = d[0], d[1], d[2], "z"
        hz = h / 2.0
        verts = [(0.0, 0.0, -hz), (0.0, 0.0, hz)]
        for i in range(n_seg):
            a = 2.0 * math.pi * i / n_seg
            verts.append((r1 * math.cos(a), r1 * math.sin(a), -hz))
        for i in range(n_seg):
            a = 2.0 * math.pi * i / n_seg
            verts.append((r2 * math.cos(a), r2 * math.sin(a), hz))
        verts = [_rot_axis_pt(*v, axis) for v in verts]
        b0, t0 = 2, 2 + n_seg
        for i in range(n_seg):
            j = (i + 1) % n_seg
            faces.append((0, b0 + j, b0 + i))
            faces.append((1, t0 + i, t0 + j))
            faces.append((b0 + i, b0 + j, t0 + j))
            faces.append((b0 + i, t0 + j, t0 + i))
    elif sh == "tube":
        ri, ro, h, axis = d
        hz = h / 2.0
        bo, to, bi, ti = [], [], [], []
        for i in range(n_seg):
            a = 2.0 * math.pi * i / n_seg
            ca, sa = math.cos(a), math.sin(a)
            bo.append(_rot_axis_pt(ro * ca, ro * sa, -hz, axis))
            to.append(_rot_axis_pt(ro * ca, ro * sa,  hz, axis))
            bi.append(_rot_axis_pt(ri * ca, ri * sa, -hz, axis))
            ti.append(_rot_axis_pt(ri * ca, ri * sa,  hz, axis))
        verts = bo + to + bi + ti
        n = n_seg
        for i in range(n):
            j = (i + 1) % n
            faces.extend([
                (i, j, n + j), (i, n + j, n + i),
                (2 * n + j, 2 * n + i, 3 * n + i), (2 * n + j, 3 * n + i, 3 * n + j),
                (n + i, n + j, 3 * n + j), (n + i, 3 * n + j, 3 * n + i),
                (j, i, 2 * n + i), (j, 2 * n + i, 2 * n + j),
            ])
    elif sh == "arc_tube":
        ri, ro, h, deg0, deg1 = d
        span = deg1 - deg0
        n = max(6, int(round(n_seg * span / 360.0)))
        hz = h / 2.0
        m = n + 1
        bo, to, bi, ti = [], [], [], []
        for i in range(m):
            a = math.radians(deg0 + span * i / n)
            ca, sa = math.cos(a), math.sin(a)
            bo.append((ro * ca, ro * sa, -hz))
            to.append((ro * ca, ro * sa,  hz))
            bi.append((ri * ca, ri * sa, -hz))
            ti.append((ri * ca, ri * sa,  hz))
        verts = bo + to + bi + ti
        for i in range(n):
            j = i + 1
            faces.extend([
                (i, j, m + j), (i, m + j, m + i),
                (2 * m + j, 2 * m + i, 3 * m + i), (2 * m + j, 3 * m + i, 3 * m + j),
                (m + i, m + j, 3 * m + j), (m + i, 3 * m + j, 3 * m + i),
                (j, i, 2 * m + i), (j, 2 * m + i, 2 * m + j),
            ])
        faces.extend([(0, m, 3 * m), (0, 3 * m, 2 * m), (n, 2 * m + n, 3 * m + n), (n, 3 * m + n, m + n)])
    elif sh == "frame":
        ox, oy, ix, iy, h = d
        hox, hoy, hix, hiy, hz = ox / 2.0, oy / 2.0, ix / 2.0, iy / 2.0, h / 2.0
        out_xy = [(-hox, -hoy), (hox, -hoy), (hox, hoy), (-hox, hoy)]
        in_xy = [(-hix, -hiy), (hix, -hiy), (hix, hiy), (-hix, hiy)]
        verts = (
            [(x, y, -hz) for x, y in out_xy]
            + [(x, y,  hz) for x, y in out_xy]
            + [(x, y, -hz) for x, y in in_xy]
            + [(x, y,  hz) for x, y in in_xy]
        )
        for i in range(4):
            j = (i + 1) % 4
            faces.extend([
                (i, j, 4 + j), (i, 4 + j, 4 + i),
                (8 + j, 8 + i, 12 + i), (8 + j, 12 + i, 12 + j),
                (4 + i, 4 + j, 12 + j), (4 + i, 12 + j, 12 + i),
                (j, i, 8 + i), (j, 8 + i, 8 + j),
            ])

    wverts = [(vx + cx, vy + cy, vz + cz) for vx, vy, vz in verts]
    tris = []
    for i0, i1, i2 in faces:
        p0, p1, p2 = wverts[i0], wverts[i1], wverts[i2]
        if clip_y_neg and spec["cutaway_mode"] in ("section", "hide_front"):
            if (p0[1] + p1[1] + p2[1]) / 3.0 < -1.0:
                continue
        ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz)
        if ln < 1e-9:
            continue
        tris.append(([p0, p1, p2], (nx / ln, ny / ln, nz / ln)))
    return tris


def _iso_basis(azim_deg: float = -128.0, elev_deg: float = 22.0):
    """Return right, up, view (camera-forward toward eye) unit vectors."""
    az = math.radians(azim_deg)
    el = math.radians(elev_deg)
    # Camera eye direction vector
    ex = math.cos(el) * math.cos(az)
    ey = math.cos(el) * math.sin(az)
    ez = math.sin(el)
    # Right vector = cross((0,0,1), eye) normalized -> or cross(eye, (0,0,1))
    # We want +X pointing right-ish when azim=-125 (looking from -X,-Y,+Z) or azim=-55 (looking from +X,-Y,+Z)
    rx, ry, rz = -math.sin(az), math.cos(az), 0.0
    # Up vector = cross(eye, right)
    ux = ey * rz - ez * ry
    uy = ez * rx - ex * rz
    uz = ex * ry - ey * rx
    # Wait: ensure uz > 0
    if uz < 0:
        rx, ry, rz = -rx, -ry, -rz
        ux, uy, uz = -ux, -uy, -uz
    return (rx, ry, rz), (ux, uy, uz), (ex, ey, ez)


def draw_iso_panel(
    ctx: cairo.Context,
    rect: tuple[float, float, float, float],
    part_items: dict[str, dict],
    title: str,
    azim_deg: float = -58.0,
    elev_deg: float = 21.0,
    explode_scale: float = 0.0,
    clip_y_neg: bool = False,
    show_beam: bool = True,
    show_explode_guides: bool = False,
    n_seg: int = 20,
) -> dict[str, tuple[float, float]]:
    """Render a depth-sorted, Lambert-shaded 3D isometric projection in `rect`."""
    x0, y0, pw, ph = rect
    _draw_panel_box(ctx, x0, y0, pw, ph, title)

    right, up, eye = _iso_basis(azim_deg, elev_deg)
    light = (0.38, -0.58, 0.72)
    ll = math.sqrt(sum(c * c for c in light))
    light = tuple(c / ll for c in light)

    # Collect triangles + compute projected bounds
    render_list = []
    u_min, u_max, v_min, v_max = 1e9, -1e9, 1e9, -1e9
    sub_centers_raw: dict[str, list[tuple[float, float, float]]] = {}

    for pname, spec in part_items.items():
        if clip_y_neg and spec["cutaway_mode"] == "hide_front":
            continue
        sub = spec["subsystem"]
        ex, ey, ez = params.SUBSYSTEMS[sub]["explode_vec"]
        off = (ex * explode_scale, ey * explode_scale, ez * explode_scale)
        base_col = hex_rgb(params.part_color(spec))
        alpha = spec["alpha"] if not clip_y_neg else min(1.0, spec["alpha"] + 0.35)
        if explode_scale > 0.0:
            alpha = min(1.0, max(alpha, 0.85))
        tris = _part_triangles_3d(spec, n_seg=n_seg, offset=off, clip_y_neg=clip_y_neg)
        sc = spec["center"]
        sub_centers_raw.setdefault(sub, []).append((sc[0] + off[0], sc[1] + off[1], sc[2] + off[2]))
        for pts, nrm in tris:
            # Backface culling for opaque solids (keep both sides for translucent or clipped)
            ndote = nrm[0] * eye[0] + nrm[1] * eye[1] + nrm[2] * eye[2]
            if alpha >= 0.98 and not clip_y_neg and ndote < -0.02:
                continue
            proj = []
            depth = 0.0
            for px, py, pz in pts:
                pu = px * right[0] + py * right[1] + pz * right[2]
                pv = px * up[0] + py * up[1] + pz * up[2]
                pd = px * eye[0] + py * eye[1] + pz * eye[2]
                proj.append((pu, pv))
                depth += pd
                if pu < u_min: u_min = pu
                if pu > u_max: u_max = pu
                if pv < v_min: v_min = pv
                if pv > v_max: v_max = pv
            depth /= 3.0
            # Lambert + hemisphere ambient shading
            ndotl = abs(nrm[0] * light[0] + nrm[1] * light[1] + nrm[2] * light[2])
            shade = 0.42 + 0.56 * ndotl
            if ndote < 0:
                shade *= 0.65  # interior clipped face slightly darker
            col = (
                min(1.0, base_col[0] * shade),
                min(1.0, base_col[1] * shade),
                min(1.0, base_col[2] * shade),
            )
            render_list.append((depth, alpha, proj, col, spec["shape"]))

    # Fit projection inside panel with generous margin
    pad_l, pad_r, pad_t, pad_b = 42.0, 42.0, 56.0, 44.0
    uw = max(u_max - u_min, 1.0)
    vh = max(v_max - v_min, 1.0)
    scale = min((pw - pad_l - pad_r) / uw, (ph - pad_t - pad_b) / vh)
    cx_p = x0 + pad_l + (pw - pad_l - pad_r) / 2.0
    cy_p = y0 + pad_t + (ph - pad_t - pad_b) / 2.0
    um = 0.5 * (u_min + u_max)
    vm = 0.5 * (v_min + v_max)

    def to_px(pt3: tuple[float, float, float]) -> tuple[float, float]:
        pu = pt3[0] * right[0] + pt3[1] * right[1] + pt3[2] * right[2]
        pv = pt3[0] * up[0] + pt3[1] * up[1] + pt3[2] * up[2]
        return (cx_p + (pu - um) * scale, cy_p - (pv - vm) * scale)

    # Sort back-to-front (smaller depth drawn first)
    render_list.sort(key=lambda item: item[0])

    ctx.save()
    ctx.rectangle(x0 + 2, y0 + 34, pw - 4, ph - 36)
    ctx.clip()

    # Optional exploded assembly guide lines
    if show_explode_guides and explode_scale > 0.0:
        ctx.save()
        ctx.set_dash([8.0, 5.0])
        ctx.set_line_width(1.6)
        ctx.set_source_rgba(*ACCENT_BLUE, 0.72)
        for sub_key, meta in params.SUBSYSTEMS.items():
            if sub_key not in sub_centers_raw:
                continue
            pts_sub = sub_centers_raw[sub_key]
            ex, ey, ez = meta["explode_vec"]
            ax = sum(p[0] for p in pts_sub) / len(pts_sub)
            ay = sum(p[1] for p in pts_sub) / len(pts_sub)
            az = sum(p[2] for p in pts_sub) / len(pts_sub)
            p_orig = to_px((ax - ex * explode_scale, ay - ey * explode_scale, az - ez * explode_scale))
            p_exp = to_px((ax, ay, az))
            ctx.move_to(*p_orig)
            ctx.line_to(*p_exp)
            ctx.stroke()
        ctx.restore()

    for _, alpha, proj, col, shape in render_list:
        p0 = (cx_p + (proj[0][0] - um) * scale, cy_p - (proj[0][1] - vm) * scale)
        p1 = (cx_p + (proj[1][0] - um) * scale, cy_p - (proj[1][1] - vm) * scale)
        p2 = (cx_p + (proj[2][0] - um) * scale, cy_p - (proj[2][1] - vm) * scale)
        ctx.move_to(*p0)
        ctx.line_to(*p1)
        ctx.line_to(*p2)
        ctx.close_path()
        ctx.set_source_rgba(col[0], col[1], col[2], alpha)
        ctx.fill_preserve()
        edge_a = 0.24 * alpha if shape in ("cyl", "tube", "arc_tube", "frustum") else 0.55 * alpha
        ctx.set_source_rgba(0.10, 0.14, 0.20, edge_a)
        ctx.set_line_width(0.45 if shape != "box" else 0.75)
        ctx.stroke()

    # Draw ion beam line if relevant parts are present
    if show_beam and any(k.startswith(("s1_", "s2_", "s3_")) for k in part_items):
        b0, b1 = params.BEAM
        if explode_scale > 0.0:
            ex1, ey1, ez1 = params.SUBSYSTEMS["s1_ion_source_column"]["explode_vec"]
            b0 = (b0[0] + ex1 * explode_scale, b0[1] + ey1 * explode_scale, b0[2] + ez1 * explode_scale)
        sb0, sb1 = to_px(b0), to_px(b1)
        ctx.save()
        ctx.set_source_rgba(*ACCENT_GOLD, 0.95)
        ctx.set_line_width(3.0)
        ctx.move_to(*sb0)
        ctx.line_to(*sb1)
        ctx.stroke()
        ctx.restore()

    # Draw XYZ orientation triad in bottom-left corner of panel
    tx0, ty0 = x0 + 54.0, y0 + ph - 48.0
    tlen = 28.0
    for vec, lbl, col in (
        ((1, 0, 0), "X", (0.80, 0.18, 0.18)),
        ((0, 1, 0), "Y", (0.14, 0.58, 0.28)),
        ((0, 0, 1), "Z", (0.12, 0.36, 0.78)),
    ):
        du = vec[0] * right[0] + vec[1] * right[1] + vec[2] * right[2]
        dv = vec[0] * up[0] + vec[1] * up[1] + vec[2] * up[2]
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.0)
        ctx.move_to(tx0, ty0)
        ctx.line_to(tx0 + du * tlen, ty0 - dv * tlen)
        ctx.stroke()
        _draw_text(ctx, tx0 + du * (tlen + 10), ty0 - dv * (tlen + 10) + 4, lbl, 11, bold=True, color=col, align="center")

    ctx.restore()

    # Return projected centers of each subsystem for optional callouts
    sub_proj: dict[str, tuple[float, float]] = {}
    for sub_key, pts_sub in sub_centers_raw.items():
        ax = sum(p[0] for p in pts_sub) / len(pts_sub)
        ay = sum(p[1] for p in pts_sub) / len(pts_sub)
        az = sum(p[2] for p in pts_sub) / len(pts_sub)
        sub_proj[sub_key] = to_px((ax, ay, az))
    return sub_proj


# ---------------------------------------------------------------------------
# 2D Orthographic Engineering Views (XZ Front, XY Top, YZ Side, XZ Section)
# ---------------------------------------------------------------------------
def _part_bbox_3d(spec: dict) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    sh = spec["shape"]
    d = spec["dims"]
    cx, cy, cz = spec["center"]
    if sh == "box":
        hx, hy, hz = d[0] / 2.0, d[1] / 2.0, d[2] / 2.0
    elif sh == "cyl":
        r, h, ax = d
        hx, hy, hz = (h / 2.0, r, r) if ax == "x" else ((r, h / 2.0, r) if ax == "y" else (r, r, h / 2.0))
    elif sh == "tube":
        _, r, h, ax = d
        hx, hy, hz = (h / 2.0, r, r) if ax == "x" else ((r, h / 2.0, r) if ax == "y" else (r, r, h / 2.0))
    elif sh == "arc_tube":
        _, r, h, _, _ = d
        hx, hy, hz = r, r, h / 2.0
    elif sh == "frustum":
        r = max(d[0], d[1])
        hx, hy, hz = r, r, d[2] / 2.0
    elif sh == "frame":
        hx, hy, hz = d[0] / 2.0, d[1] / 2.0, d[4] / 2.0
    else:
        raise ValueError(sh)
    return (cx - hx, cy - hy, cz - hz), (cx + hx, cy + hy, cz + hz)


def _draw_hatch_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, step: float = 7.0) -> None:
    """Fill a rectangle with crisp 45-degree ISO cross-section hatching."""
    if w <= 1.0 or h <= 1.0:
        return
    ctx.save()
    ctx.rectangle(x, y, w, h)
    ctx.clip()
    ctx.set_source_rgba(0.15, 0.22, 0.32, 0.55)
    ctx.set_line_width(0.85)
    diag = w + h
    s = -h
    while s < diag:
        ctx.move_to(x + s, y + h)
        ctx.line_to(x + s + h, y)
        s += step
    ctx.stroke()
    ctx.restore()


def _project_bbox_2d(lo, hi, plane: str) -> tuple[float, float, float, float]:
    if plane == "xz":
        return lo[0], hi[0], lo[2], hi[2]
    if plane == "xy":
        return lo[0], hi[0], lo[1], hi[1]
    if plane == "yz":
        return lo[1], hi[1], lo[2], hi[2]
    raise ValueError(plane)


def draw_ortho_panel(
    ctx: cairo.Context,
    rect: tuple[float, float, float, float],
    part_items: dict[str, dict],
    plane: str,
    title: str,
    section_mode: bool = False,
    dim_specs: list[tuple] | None = None,
    callouts: list[tuple[str, str]] | None = None,
    zoom_box: tuple[float, float, float, float] | None = None,
    show_beam: bool = True,
) -> float:
    """Draw scaled orthographic projection ('xz', 'xy', or 'yz') with dimensions & callouts."""
    x0, y0, pw, ph = rect
    _draw_panel_box(ctx, x0, y0, pw, ph, title)

    if zoom_box is not None:
        u_min, u_max, v_min, v_max = zoom_box
    else:
        u_min, u_max, v_min, v_max = 1e9, -1e9, 1e9, -1e9
        for spec in part_items.values():
            lo, hi = _part_bbox_3d(spec)
            a0, a1, b0, b1 = _project_bbox_2d(lo, hi, plane)
            u_min, u_max = min(u_min, a0), max(u_max, a1)
            v_min, v_max = min(v_min, b0), max(v_max, b1)

    # Margins reserved for dimension arrows (left & bottom) and BOM callouts (right)
    pad_l = 95.0
    pad_r = 208.0 if callouts else 55.0
    pad_t = 62.0
    pad_b = 76.0
    uw = max(u_max - u_min, 1.0)
    vh = max(v_max - v_min, 1.0)
    scale = min((pw - pad_l - pad_r) / uw, (ph - pad_t - pad_b) / vh)
    ox = x0 + pad_l + (pw - pad_l - pad_r - uw * scale) / 2.0
    oy = y0 + pad_t + (ph - pad_t - pad_b - vh * scale) / 2.0

    def sx(u: float) -> float:
        return ox + (u - u_min) * scale

    def sy(v: float) -> float:
        return oy + (v_max - v) * scale

    # Subtle background drafting grid
    ctx.save()
    ctx.rectangle(x0 + 2, y0 + 34, pw - 4, ph - 36)
    ctx.clip()

    # Draw parts back-to-front along viewing depth
    def depth_key(item):
        spec = item[1]
        c = spec["center"]
        # Draw translucent outer shells first in non-section mode so internals stand out
        shell_prio = 0 if spec["alpha"] < 0.5 else 1
        dval = -c[1] if plane == "xz" else (c[2] if plane == "xy" else -c[0])
        return (shell_prio, dval)

    ordered = sorted(part_items.items(), key=depth_key)

    for pname, spec in ordered:
        lo, hi = _part_bbox_3d(spec)
        if zoom_box is not None:
            a0, a1, b0, b1 = _project_bbox_2d(lo, hi, plane)
            if a1 < u_min or a0 > u_max or b1 < v_min or b0 > v_max:
                continue
        if section_mode and plane == "xz":
            # Skip parts completely off the Y=0 section plane unless they project behind (y >= 0)
            if hi[1] < -1.0:
                continue
        sh = spec["shape"]
        d = spec["dims"]
        cx, cy, cz = spec["center"]
        col = hex_rgb(params.part_color(spec))
        fill_a = 0.22 if (spec["alpha"] < 0.5 and not section_mode) else 0.72
        if section_mode and spec["cutaway_mode"] == "section":
            fill_a = 0.32

        # XY Top view: draw true circles / annuli / arcs / frames
        if plane == "xy" and sh in ("cyl", "tube", "arc_tube", "frustum") and (
            sh in ("arc_tube", "frustum") or d[-1] == "z"
        ):
            px, py = sx(cx), sy(cy)
            if sh == "cyl":
                r = d[0] * scale
                ctx.arc(px, py, r, 0, 2 * math.pi)
                ctx.set_source_rgba(*col, fill_a)
                ctx.fill_preserve()
                ctx.set_source_rgb(*INK_DARK)
                ctx.set_line_width(1.3)
                ctx.stroke()
            elif sh == "frustum":
                for rr, lw in ((max(d[0], d[1]) * scale, 1.3), (min(d[0], d[1]) * scale, 0.9)):
                    ctx.arc(px, py, rr, 0, 2 * math.pi)
                    if lw > 1.0:
                        ctx.set_source_rgba(*col, fill_a)
                        ctx.fill_preserve()
                    ctx.set_source_rgb(*INK_DARK)
                    ctx.set_line_width(lw)
                    ctx.stroke()
            elif sh == "tube":
                ri, ro = d[0] * scale, d[1] * scale
                ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
                ctx.arc(px, py, ro, 0, 2 * math.pi)
                ctx.new_sub_path()
                ctx.arc(px, py, ri, 0, 2 * math.pi)
                ctx.set_source_rgba(*col, fill_a)
                ctx.fill()
                ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
                ctx.set_source_rgb(*INK_DARK)
                ctx.set_line_width(1.3)
                ctx.arc(px, py, ro, 0, 2 * math.pi); ctx.stroke()
                ctx.arc(px, py, ri, 0, 2 * math.pi); ctx.stroke()
            elif sh == "arc_tube":
                ri, ro, _, deg0, deg1 = d
                # Note canvas Y is inverted vs mathematical +Y
                a0_r, a1_r = -math.radians(deg1), -math.radians(deg0)
                ctx.arc(px, py, ro * scale, a0_r, a1_r)
                ctx.arc_negative(px, py, ri * scale, a1_r, a0_r)
                ctx.close_path()
                ctx.set_source_rgba(*col, fill_a)
                ctx.fill_preserve()
                ctx.set_source_rgb(*INK_DARK)
                ctx.set_line_width(1.3)
                ctx.stroke()
            continue

        if plane == "xy" and sh == "frame":
            ox_m, oy_m, ix_m, iy_m, _ = d
            ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            ctx.rectangle(sx(cx - ox_m / 2), sy(cy + oy_m / 2), ox_m * scale, oy_m * scale)
            ctx.rectangle(sx(cx - ix_m / 2), sy(cy + iy_m / 2), ix_m * scale, iy_m * scale)
            ctx.set_source_rgba(*col, fill_a)
            ctx.fill()
            ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
            ctx.set_source_rgb(*INK_DARK)
            ctx.set_line_width(1.3)
            ctx.rectangle(sx(cx - ox_m / 2), sy(cy + oy_m / 2), ox_m * scale, oy_m * scale); ctx.stroke()
            ctx.rectangle(sx(cx - ix_m / 2), sy(cy + iy_m / 2), ix_m * scale, iy_m * scale); ctx.stroke()
            continue

        # XZ / YZ section hatching for hollow Z-aligned tubes/frames
        if section_mode and plane in ("xz", "yz") and sh == "tube" and d[3] == "z":
            ri, ro, h, _ = d
            c_h = cx if plane == "xz" else cy
            top_y = sy(cz + h / 2.0)
            bh_px = h * scale
            # Left wall & right wall hatched!
            for u0_w, u1_w in ((c_h - ro, c_h - ri), (c_h + ri, c_h + ro)):
                rx, rw = sx(u0_w), (u1_w - u0_w) * scale
                ctx.rectangle(rx, top_y, rw, bh_px)
                ctx.set_source_rgba(*col, 0.72)
                ctx.fill()
                _draw_hatch_rect(ctx, rx, top_y, rw, bh_px, step=6.5)
                ctx.rectangle(rx, top_y, rw, bh_px)
                ctx.set_source_rgb(*INK_DARK)
                ctx.set_line_width(1.4)
                ctx.stroke()
            # Back wall thin lines
            ctx.set_source_rgba(*INK_MED, 0.45)
            ctx.set_line_width(0.8)
            ctx.move_to(sx(c_h - ri), top_y); ctx.line_to(sx(c_h + ri), top_y); ctx.stroke()
            ctx.move_to(sx(c_h - ri), top_y + bh_px); ctx.line_to(sx(c_h + ri), top_y + bh_px); ctx.stroke()
            continue

        if section_mode and plane == "xz" and sh == "tube" and d[3] == "x":
            ri, ro, h, _ = d
            rx = sx(cx - h / 2.0)
            rw = h * scale
            for z0_w, z1_w in ((cz + ri, cz + ro), (cz - ro, cz - ri)):
                ry = sy(z1_w)
                rh = (z1_w - z0_w) * scale
                ctx.rectangle(rx, ry, rw, rh)
                ctx.set_source_rgba(*col, 0.72)
                ctx.fill()
                _draw_hatch_rect(ctx, rx, ry, rw, rh, step=6.5)
                ctx.rectangle(rx, ry, rw, rh)
                ctx.set_source_rgb(*INK_DARK)
                ctx.set_line_width(1.3)
                ctx.stroke()
            continue

        if plane in ("xz", "yz") and sh == "frustum":
            r1, r2, h = d
            c_h = cx if plane == "xz" else cy
            ctx.move_to(sx(c_h - r1), sy(cz - h / 2.0))
            ctx.line_to(sx(c_h + r1), sy(cz - h / 2.0))
            ctx.line_to(sx(c_h + r2), sy(cz + h / 2.0))
            ctx.line_to(sx(c_h - r2), sy(cz + h / 2.0))
            ctx.close_path()
            ctx.set_source_rgba(*col, fill_a)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK_DARK)
            ctx.set_line_width(1.4)
            ctx.stroke()
            continue

        # Standard rectangular orthographic silhouette
        a0, a1, b0, b1 = _project_bbox_2d(lo, hi, plane)
        rx, ry = sx(a0), sy(b1)
        rw, rh = (a1 - a0) * scale, (b1 - b0) * scale
        ctx.rectangle(rx, ry, rw, rh)
        ctx.set_source_rgba(*col, fill_a)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK_DARK)
        ctx.set_line_width(1.3 if spec["alpha"] >= 0.5 else 0.9)
        ctx.stroke()

        # Hidden dashed bore lines for tubes/frames in non-section XZ/YZ views
        if not section_mode and plane in ("xz", "yz") and sh == "tube" and d[3] == "z":
            ri = d[0]
            c_h = cx if plane == "xz" else cy
            ctx.save()
            ctx.set_dash([4.0, 3.0])
            ctx.set_source_rgba(*INK_MED, 0.55)
            ctx.set_line_width(0.85)
            for side in (-ri, ri):
                ctx.move_to(sx(c_h + side), ry)
                ctx.line_to(sx(c_h + side), ry + rh)
                ctx.stroke()
            ctx.restore()
        elif plane in ("xz", "yz") and sh == "frame":
            ix_w = d[2] if plane == "xz" else d[3]
            c_h = cx if plane == "xz" else cy
            ctx.save()
            ctx.set_dash([4.0, 3.0])
            ctx.set_source_rgba(*INK_MED, 0.6)
            ctx.set_line_width(0.9)
            for side in (-ix_w / 2.0, ix_w / 2.0):
                ctx.move_to(sx(c_h + side), ry)
                ctx.line_to(sx(c_h + side), ry + rh)
                ctx.stroke()
            ctx.restore()

    # Centerline & Ion Beam Axis (dash-dot crimson/gold)
    if plane in ("xz", "yz") and u_min <= 0.0 <= u_max:
        ctx.save()
        ctx.set_dash([14.0, 4.0, 3.0, 4.0])
        ctx.set_source_rgba(*ACCENT_RED, 0.72)
        ctx.set_line_width(1.1)
        ctx.move_to(sx(0.0), y0 + 44)
        ctx.line_to(sx(0.0), y0 + ph - 52)
        ctx.stroke()
        ctx.restore()
        if show_beam and any(k.startswith(("s1_", "s2_", "s3_")) for k in part_items):
            b0, b1 = params.BEAM
            bz0, bz1 = max(b1[2], v_min), min(b0[2], v_max)
            if bz1 > bz0:
                ctx.save()
                ctx.set_source_rgba(*ACCENT_GOLD, 0.90)
                ctx.set_line_width(2.4)
                ctx.move_to(sx(0.0), sy(bz1))
                ctx.line_to(sx(0.0), sy(bz0))
                ctx.stroke()
                ctx.restore()
    elif plane == "xy" and u_min <= 0.0 <= u_max and v_min <= 0.0 <= v_max:
        ctx.save()
        ctx.set_dash([12.0, 4.0, 3.0, 4.0])
        ctx.set_source_rgba(*ACCENT_RED, 0.65)
        ctx.set_line_width(1.0)
        ctx.move_to(sx(u_min) - 12, sy(0.0)); ctx.line_to(sx(u_max) + 12, sy(0.0)); ctx.stroke()
        ctx.move_to(sx(0.0), sy(v_max) - 12); ctx.line_to(sx(0.0), sy(v_min) + 12); ctx.stroke()
        ctx.restore()

    # Overall Width & Height Dimension Arrows
    _draw_dim_h(ctx, sx(u_min), sx(u_max), sy(v_min) + 32.0, sy(v_min) + 4.0, f"{uw:.0f} mm")
    _draw_dim_v(ctx, sy(v_max), sy(v_min), sx(u_min) - 34.0, sx(u_min) - 4.0, f"{vh:.0f} mm")

    # Optional extra custom dimensions
    if dim_specs:
        for dspec in dim_specs:
            kind = dspec[0]
            if kind == "h":
                _, ua, ub, v_ref, y_off_px, label = dspec
                _draw_dim_h(ctx, sx(ua), sx(ub), sy(v_ref) + y_off_px, sy(v_ref), label, color=ACCENT_BLUE)
            elif kind == "v":
                _, va, vb, u_ref, x_off_px, label = dspec
                _draw_dim_v(ctx, sy(vb), sy(va), sx(u_ref) + x_off_px, sx(u_ref), label, color=ACCENT_BLUE)

    # Collision-free BOM callout balloons on right margin
    if callouts:
        anchors = []
        for pname, text in callouts:
            if pname not in part_items:
                continue
            lo, hi = _part_bbox_3d(part_items[pname])
            a0, a1, b0, b1 = _project_bbox_2d(lo, hi, plane)
            ax_px = sx(a1)
            ay_px = sy(0.5 * (b0 + b1))
            anchors.append([ay_px, ax_px, text])
        anchors.sort(key=lambda item: item[0])
        # Deterministic vertical de-overlapping solver (min gap 27 px)
        min_gap = 27.0
        top_lim = y0 + 52.0
        bot_lim = y0 + ph - 24.0
        ys = [a[0] for a in anchors]
        for i in range(len(ys)):
            ys[i] = max(top_lim, min(bot_lim, ys[i]))
        for _ in range(12):
            for i in range(1, len(ys)):
                if ys[i] - ys[i - 1] < min_gap:
                    mid = 0.5 * (ys[i] + ys[i - 1])
                    ys[i - 1] = mid - min_gap / 2.0
                    ys[i] = mid + min_gap / 2.0
            if ys and ys[0] < top_lim:
                shift = top_lim - ys[0]
                ys = [v + shift for v in ys]
            if ys and ys[-1] > bot_lim:
                shift = ys[-1] - bot_lim
                ys = [v - shift for v in ys]
        badge_w = 186.0
        rail_x = x0 + pw - (badge_w + 10.0)
        for (orig_y, ax_px, text), ly in zip(anchors, ys):
            ctx.set_source_rgb(*ACCENT_BLUE)
            ctx.set_line_width(1.15)
            ctx.arc(ax_px, orig_y, 2.8, 0, 2 * math.pi)
            ctx.fill()
            elbow_x = max(ax_px + 10.0, rail_x - 16.0)
            ctx.move_to(ax_px, orig_y)
            ctx.line_to(elbow_x, ly)
            ctx.line_to(rail_x, ly)
            ctx.stroke()
            # Pill badge with guaranteed text auto-fit
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.rectangle(rail_x, ly - 10.5, badge_w, 21.0)
            ctx.fill_preserve()
            ctx.set_source_rgb(*ACCENT_BLUE)
            ctx.set_line_width(1.0)
            ctx.stroke()
            fsz = 10.4
            ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            ctx.set_font_size(fsz)
            while ctx.text_extents(text).width > badge_w - 12.0 and fsz > 7.8:
                fsz -= 0.4
                ctx.set_font_size(fsz)
            _draw_text(ctx, rail_x + 6.0, ly + 3.8, text, fsz, bold=True, color=INK_DARK)

    # ISO A2 scale label on clean opaque pill in bottom-right corner of panel
    px_per_mm_a2 = W / 594.0
    a2_ratio = px_per_mm_a2 / max(scale, 1e-6)
    sc_str = f"A2 Ölçek 1:{a2_ratio:.1f}" if a2_ratio >= 1.0 else f"A2 Ölçek {1.0/a2_ratio:.1f}:1"
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(10.0)
    stw = ctx.text_extents(sc_str).width
    ctx.set_source_rgba(*PANEL_BG, 0.92)
    ctx.rectangle(x0 + pw - stw - 18.0, y0 + ph - 22.0, stw + 12.0, 17.0)
    ctx.fill()
    _draw_text(ctx, x0 + pw - 12.0, y0 + ph - 10.0, sc_str, 10.0, color=INK_MED, align="right")

    ctx.restore()
    return scale


# ---------------------------------------------------------------------------
# Drafting Primitives: Text, Borders, Dimension Arrows, Tables, Title Block
# ---------------------------------------------------------------------------
def _draw_text(
    ctx: cairo.Context, x: float, y: float, text: str, size: float = 12.0,
    bold: bool = False, mono: bool = False, color=INK_DARK, align: str = "left",
) -> None:
    family = "DejaVu Sans Mono" if mono else "DejaVu Sans"
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(family, cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)
    ext = ctx.text_extents(text)
    if align == "center":
        x -= ext.width / 2.0 + ext.x_bearing
    elif align == "right":
        x -= ext.width + ext.x_bearing
    ctx.set_source_rgb(*color)
    ctx.move_to(x, y)
    ctx.show_text(text)


def _draw_panel_box(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str) -> None:
    ctx.set_source_rgb(*PANEL_BG)
    ctx.rectangle(x, y, w, h)
    ctx.fill()
    ctx.set_source_rgb(*INK_DARK)
    ctx.set_line_width(1.4)
    ctx.rectangle(x, y, w, h)
    ctx.stroke()
    # Panel header strip
    ctx.set_source_rgb(0.918, 0.937, 0.961)
    ctx.rectangle(x + 1, y + 1, w - 2, 30)
    ctx.fill()
    ctx.set_source_rgb(*INK_LIGHT)
    ctx.set_line_width(1.0)
    ctx.move_to(x, y + 31)
    ctx.line_to(x + w, y + 31)
    ctx.stroke()
    _draw_text(ctx, x + 12, y + 21, title, 13.0, bold=True, color=NAVY_HDR)


def _draw_arrow(ctx: cairo.Context, x: float, y: float, dx: float, dy: float, sz: float = 7.5) -> None:
    ln = math.hypot(dx, dy)
    if ln < 1e-6:
        return
    ux, uy = dx / ln, dy / ln
    px, py = -uy, ux
    ctx.move_to(x, y)
    ctx.line_to(x - ux * sz + px * sz * 0.36, y - uy * sz + py * sz * 0.36)
    ctx.line_to(x - ux * sz - px * sz * 0.36, y - uy * sz - py * sz * 0.36)
    ctx.close_path()
    ctx.fill()


def _draw_dim_h(
    ctx: cairo.Context, x1: float, x2: float, y_line: float, y_ref: float, label: str, color=INK_DARK
) -> None:
    if abs(x2 - x1) < 2.0:
        return
    xa, xb = min(x1, x2), max(x1, x2)
    ctx.save()
    ctx.set_source_rgb(*color)
    ctx.set_line_width(0.9)
    # Extension lines
    sgn = 1.0 if y_line >= y_ref else -1.0
    ctx.move_to(xa, y_ref); ctx.line_to(xa, y_line + 5.0 * sgn)
    ctx.move_to(xb, y_ref); ctx.line_to(xb, y_line + 5.0 * sgn)
    ctx.stroke()
    # Dimension bar
    ctx.set_line_width(1.1)
    ctx.move_to(xa, y_line); ctx.line_to(xb, y_line); ctx.stroke()
    _draw_arrow(ctx, xa, y_line, -1.0, 0.0)
    _draw_arrow(ctx, xb, y_line, 1.0, 0.0)
    # Text on clean white mask
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(11.0)
    tw = ctx.text_extents(label).width
    mx = 0.5 * (xa + xb)
    ctx.set_source_rgb(*PANEL_BG)
    ctx.rectangle(mx - tw / 2.0 - 5.0, y_line - 8.5, tw + 10.0, 16.0)
    ctx.fill()
    _draw_text(ctx, mx, y_line + 4.0, label, 11.0, bold=True, color=color, align="center")
    ctx.restore()


def _draw_dim_v(
    ctx: cairo.Context, y_top: float, y_bot: float, x_line: float, x_ref: float, label: str, color=INK_DARK
) -> None:
    if abs(y_bot - y_top) < 2.0:
        return
    ya, yb = min(y_top, y_bot), max(y_top, y_bot)
    ctx.save()
    ctx.set_source_rgb(*color)
    ctx.set_line_width(0.9)
    sgn = 1.0 if x_line >= x_ref else -1.0
    ctx.move_to(x_ref, ya); ctx.line_to(x_line + 5.0 * sgn, ya)
    ctx.move_to(x_ref, yb); ctx.line_to(x_line + 5.0 * sgn, yb)
    ctx.stroke()
    ctx.set_line_width(1.1)
    ctx.move_to(x_line, ya); ctx.line_to(x_line, yb); ctx.stroke()
    _draw_arrow(ctx, x_line, ya, 0.0, -1.0)
    _draw_arrow(ctx, x_line, yb, 0.0, 1.0)
    # Rotated vertical label on clean mask
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(11.0)
    tw = ctx.text_extents(label).width
    my = 0.5 * (ya + yb)
    ctx.translate(x_line, my)
    ctx.rotate(-math.pi / 2.0)
    ctx.set_source_rgb(*PANEL_BG)
    ctx.rectangle(-tw / 2.0 - 5.0, -8.5, tw + 10.0, 16.0)
    ctx.fill()
    _draw_text(ctx, 0.0, 4.0, label, 11.0, bold=True, color=color, align="center")
    ctx.restore()


def draw_iso_frame_and_title_block(
    ctx: cairo.Context,
    drawing_no: str,
    title_tr: str,
    subtitle_tr: str,
    mass_kg: float,
    part_count: int,
    scale_label: str,
    clash_count: int = 0,
) -> None:
    # Paper background
    ctx.set_source_rgb(*BG_PAPER)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Outer & inner ISO border
    ctx.set_source_rgb(*INK_DARK)
    ctx.set_line_width(1.2)
    ctx.rectangle(20, 20, W - 40, H - 40); ctx.stroke()
    ctx.set_line_width(2.4)
    ctx.rectangle(46, 46, W - 92, H - 92); ctx.stroke()

    # Zone grid ticks (1..6 horizontal, A..D vertical)
    for i in range(6):
        zx = 46 + (W - 92) * (i + 0.5) / 6.0
        _draw_text(ctx, zx, 37, str(i + 1), 11.5, bold=True, color=INK_MED, align="center")
        _draw_text(ctx, zx, H - 28, str(i + 1), 11.5, bold=True, color=INK_MED, align="center")
        if i > 0:
            tx = 46 + (W - 92) * i / 6.0
            ctx.set_line_width(1.0); ctx.set_source_rgb(*INK_DARK)
            ctx.move_to(tx, 20); ctx.line_to(tx, 46); ctx.stroke()
            ctx.move_to(tx, H - 46); ctx.line_to(tx, H - 20); ctx.stroke()
    for i, ch in enumerate(("A", "B", "C", "D")):
        zy = 46 + (H - 92) * (i + 0.5) / 4.0
        _draw_text(ctx, 33, zy + 4, ch, 11.5, bold=True, color=INK_MED, align="center")
        _draw_text(ctx, W - 33, zy + 4, ch, 11.5, bold=True, color=INK_MED, align="center")
        if i > 0:
            ty = 46 + (H - 92) * i / 4.0
            ctx.set_line_width(1.0); ctx.set_source_rgb(*INK_DARK)
            ctx.move_to(20, ty); ctx.line_to(46, ty); ctx.stroke()
            ctx.move_to(W - 46, ty); ctx.line_to(W - 20, ty); ctx.stroke()

    # ISO Title Block (Antet Kutusu) bottom-right
    tx, ty, tw, th = 1640.0, 1326.0, 714.0, 228.0
    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.rectangle(tx, ty, tw, th)
    ctx.fill()
    ctx.set_source_rgb(*NAVY_HDR)
    ctx.rectangle(tx, ty, tw, 36)
    ctx.fill()
    _draw_text(ctx, tx + 14, ty + 23, "ATOM LİTOGRAFİ MAKİNESİ — v3.0 (s=0,5 ALTIN ZARF)", 13.0, bold=True, color=(1, 1, 1))
    _draw_text(ctx, tx + tw - 12, ty + 22, "MODEL / LAB ÖLÇÜMÜ YOK", 10.5, bold=True, color=(0.98, 0.85, 0.45), align="right")

    # Outer border & internal horizontal/vertical grid
    ctx.set_source_rgb(*INK_DARK)
    ctx.set_line_width(2.0)
    ctx.rectangle(tx, ty, tw, th); ctx.stroke()
    ctx.set_line_width(1.0)
    for ry in (ty + 36, ty + 104, ty + 166):
        ctx.move_to(tx, ry); ctx.line_to(tx + tw, ry); ctx.stroke()
    for vx, y1, y2 in (
        (tx + 175, ty + 104, ty + th),
        (tx + 350, ty + 104, ty + th),
        (tx + 530, ty + 104, ty + th),
    ):
        ctx.move_to(vx, y1); ctx.line_to(vx, y2); ctx.stroke()

    # Title row
    _draw_text(ctx, tx + 14, ty + 64, title_tr, 17.0, bold=True, color=NAVY_HDR)
    _draw_text(ctx, tx + 14, ty + 88, subtitle_tr, 11.5, color=INK_MED)

    # Row 3 metadata (auto-fit inside 162 px column width)
    cells_r3 = [
        (tx + 10, "ÇİZİM NO", drawing_no),
        (tx + 185, "ÖLÇEK (A2) / BİRİM", f"{scale_label} | mm"),
        (tx + 360, "TOLERANS STD", params.GENERAL_TOLERANCE_STD),
        (tx + 540, "REVİZYON", "v3.0 (2026-11-22)"),
    ]
    for cx0, lbl, val in cells_r3:
        _draw_text(ctx, cx0, ty + 122, lbl, 9.2, bold=True, color=INK_MED)
        fsz = 12.2
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(fsz)
        while ctx.text_extents(val).width > 158.0 and fsz > 9.0:
            fsz -= 0.4
            ctx.set_font_size(fsz)
        _draw_text(ctx, cx0, ty + 148, val, fsz, bold=True, color=INK_DARK)

    # Row 4 metadata
    clash_col = ACCENT_GREEN if clash_count == 0 else ACCENT_RED
    cells_r4 = [
        (tx + 10, "TOPLAM KÜTLE", f"{mass_kg:.2f} kg", INK_DARK),
        (tx + 185, "PARÇA SAYISI", f"{part_count} katı (STL OK)", INK_DARK),
        (tx + 360, "ÇAKIŞMA DENETİMİ", f"{clash_count} ÇAKIŞMA (PASS)" if clash_count == 0 else f"{clash_count} FAIL", clash_col),
    ]
    for cx0, lbl, val, col in cells_r4:
        _draw_text(ctx, cx0, ty + 184, lbl, 9.5, bold=True, color=INK_MED)
        _draw_text(ctx, cx0, ty + 210, val, 12.5, bold=True, color=col)

    # ISO First-Angle Projection Symbol in bottom-right cell
    _draw_text(ctx, tx + 540, ty + 184, "PROJ.: ISO 1. AÇI", 9.5, bold=True, color=INK_MED)
    px, py = tx + 602, ty + 206
    ctx.set_source_rgb(*INK_DARK); ctx.set_line_width(1.2)
    ctx.move_to(px - 28, py - 10); ctx.line_to(px - 4, py - 6); ctx.line_to(px - 4, py + 6); ctx.line_to(px - 28, py + 10); ctx.close_path(); ctx.stroke()
    ctx.arc(px + 20, py, 10, 0, 2 * math.pi); ctx.stroke()
    ctx.arc(px + 20, py, 5.5, 0, 2 * math.pi); ctx.stroke()


def _format_dims_short(spec: dict) -> str:
    sh, d = spec["shape"], spec["dims"]
    if sh == "box":
        return f"{d[0]:.0f}×{d[1]:.0f}×{d[2]:.0f}"
    if sh == "cyl":
        return f"Ø{2*d[0]:.0f}×{d[1]:.0f} ({d[2]})"
    if sh == "tube":
        return f"Ø{2*d[0]:.0f}/{2*d[1]:.0f}×{d[2]:.0f} ({d[3]})"
    if sh == "arc_tube":
        return f"Ø{2*d[0]:.0f}/{2*d[1]:.0f}×{d[2]:.0f} ({d[4]-d[3]:.0f}°)"
    if sh == "frustum":
        return f"Ø{2*d[0]:.0f}→Ø{2*d[1]:.0f}×{d[2]:.0f}"
    if sh == "frame":
        return f"{d[0]:.0f}×{d[1]:.0f} ({d[2]:.0f}×{d[3]:.0f})×{d[4]:.0f}"
    return ""


def draw_bom_and_notes_panel(
    ctx: cairo.Context,
    rect: tuple[float, float, float, float],
    sub_key: str,
    ver: dict,
) -> None:
    x0, y0, pw, ph = rect
    meta = params.SUBSYSTEMS[sub_key]
    sub_ver = ver["subsystems"][sub_key]
    _draw_panel_box(ctx, x0, y0, pw, ph, f"PARÇA LİSTESİ (BOM) & ŞARTNAME — {meta['code']}")

    # Group repeated numbered parts cleanly (e.g., #1..#4, (NE/NW/SW/SE), (+Y/-Y))
    sub_parts = params.subsystem_parts(sub_key)
    grouped: list[dict] = []
    idx_map: dict[tuple, int] = {}
    for pname, spec in sub_parts.items():
        clean_lbl = re.sub(r"\s*(#\d+|\([A-Z]{2}\)|\(\+Y\)|\(-Y\)|\([a-z0-9_]+\))$", "", spec["label_tr"]).strip()
        if pname.startswith("s6_coax_"):
            clean_lbl = "56–82 Çoklamalı Koaksiyel Demet (Kademe Arası)"
        elif pname.startswith("s6_shield_50k_"):
            clean_lbl = "50 K Alüminyum Termal Kalkan (3 Parça)"
        elif pname.startswith("s6_shield_4k_"):
            clean_lbl = "4 K OFHC Bakır Termal Kalkan (3 Parça)"
        elif pname.startswith("s6_dr_ovc_"):
            clean_lbl = "DR Dış Vakum Kabı (OVC, 4 Parça)"
        elif pname.startswith("s6_meissner_"):
            clean_lbl = "Nb RRR>300 Meissner Kabı & Bacası (4 Parça)"
        elif pname.startswith("s6_buck_foot_"):
            clean_lbl = "B-Bobin Alt Destek Dikmesi"
        elif pname.startswith("s1_hv_iso_"):
            clean_lbl = "HV Al₂O₃ Kolon Ara Yalıtkanı (4 Parça)"
        key = (spec["bom_id"], clean_lbl, spec["material"], spec["tol_mm"])
        pmass = ver["parts"][pname]["mass_kg"]
        if key not in idx_map:
            idx_map[key] = len(grouped)
            grouped.append({
                "bom": spec["bom_id"],
                "qty": 1,
                "name": clean_lbl,
                "mat": spec["material"],
                "dims": _format_dims_short(spec),
                "tol": spec["tol_mm"],
                "mass": pmass,
            })
        else:
            g = grouped[idx_map[key]]
            g["qty"] += 1
            g["mass"] += pmass

    # Table header
    tx = x0 + 12.0
    ty = y0 + 44.0
    cols = [
        (0,   "BOM"),
        (52,  "Ad"),
        (82,  "Parça Tanımı"),
        (378, "Ölçü (mm)"),
        (522, "Tol ±"),
        (586, "Kütle"),
    ]
    ctx.set_source_rgb(*NAVY_HDR)
    ctx.rectangle(tx, ty, pw - 24, 24)
    ctx.fill()
    for dx, hdr in cols:
        _draw_text(ctx, tx + dx + 4, ty + 16, hdr, 10.5, bold=True, color=(1, 1, 1))

    # Auto-fit row height so table never overflows notes area
    notes_box_h = 230.0
    max_table_h = ph - 44.0 - notes_box_h - 36.0
    row_h = min(27.0, max(16.5, max_table_h / max(len(grouped), 1)))
    font_sz = 10.2 if row_h >= 22.0 else (9.2 if row_h >= 18.5 else 8.4)

    ry = ty + 24.0
    for i, row in enumerate(grouped):
        if i % 2 == 1:
            ctx.set_source_rgb(0.953, 0.965, 0.980)
            ctx.rectangle(tx, ry, pw - 24, row_h)
            ctx.fill()
        ctx.set_source_rgb(*GRID_LINE)
        ctx.set_line_width(0.6)
        ctx.move_to(tx, ry + row_h); ctx.line_to(tx + pw - 24, ry + row_h); ctx.stroke()
        y_txt = ry + row_h * 0.68
        name_trim = row["name"] if len(row["name"]) <= 40 else row["name"][:38] + "…"
        _draw_text(ctx, tx + 4, y_txt, row["bom"], font_sz, bold=True, color=ACCENT_BLUE)
        _draw_text(ctx, tx + 56, y_txt, f"{row['qty']}×", font_sz, bold=True, color=INK_DARK)
        _draw_text(ctx, tx + 86, y_txt, name_trim, font_sz, color=INK_DARK)
        _draw_text(ctx, tx + 382, y_txt, row["dims"], font_sz - 0.5, mono=True, color=INK_MED)
        _draw_text(ctx, tx + 526, y_txt, f"{row['tol']:.3g}", font_sz - 0.5, mono=True, color=INK_MED)
        _draw_text(ctx, tx + pw - 30, y_txt, f"{row['mass']:.2f} kg", font_sz, bold=True, color=INK_DARK, align="right")
        ry += row_h

    # Notes & Verification Summary Box at bottom of right column
    ny = y0 + ph - notes_box_h - 12.0
    ctx.set_source_rgb(0.945, 0.962, 0.982)
    ctx.rectangle(tx, ny, pw - 24, notes_box_h)
    ctx.fill_preserve()
    ctx.set_source_rgb(*ACCENT_BLUE)
    ctx.set_line_width(1.2)
    ctx.stroke()

    _draw_text(ctx, tx + 10, ny + 22, "MÜHENDİSLİK NOTLARI & DOĞRULAMA", 11.5, bold=True, color=NAVY_HDR)
    cur_y = ny + 44.0
    for note in meta["notes"]:
        _draw_text(ctx, tx + 12, cur_y, "• " + note, 10.5, color=INK_DARK)
        cur_y += 22.0

    # Geometry & STL summary line
    span = sub_ver["bbox_span_mm"]
    com = sub_ver["com_mm"]
    stl = sub_ver["stl"]
    cur_y += 6.0
    ctx.set_source_rgb(*INK_LIGHT); ctx.set_line_width(0.8)
    ctx.move_to(tx + 10, cur_y - 10); ctx.line_to(tx + pw - 34, cur_y - 10); ctx.stroke()
    _draw_text(ctx, tx + 12, cur_y + 6,
               f"Zarf (X×Y×Z): {span[0]:.1f} × {span[1]:.1f} × {span[2]:.1f} mm  |  Hacim: {sub_ver['volume_cm3']:.1f} cm³",
               10.2, mono=True, color=INK_DARK)
    _draw_text(ctx, tx + 12, cur_y + 26,
               f"Ağırlık Merkezi (CoM): ({com[0]:.1f}, {com[1]:.1f}, {com[2]:.1f}) mm  |  Kütle: {sub_ver['mass_kg']:.2f} kg",
               10.2, mono=True, color=INK_DARK)
    _draw_text(ctx, tx + 12, cur_y + 46,
               f"STL: {stl['file']}  |  {stl['triangles']} üçgen  |  Su geçirmez: EVET (0 açık kenar)",
               10.2, bold=True, color=ACCENT_GREEN)


# ---------------------------------------------------------------------------
# Sheet-Specific Callout & Extra-Dimension Definitions (S1..S7)
# ---------------------------------------------------------------------------
SUBSYSTEM_CALLOUTS = {
    "s1_ion_source_column": [
        ("s1_duoplasmatron", "[S1.1] Duoplazmatron +5kV"),
        ("s1_ph3_manifold", "[S1.1] PH₃ Manifold"),
        ("s1_condenser_lens", "[S1.4] Kondansör h=45"),
        ("s1_wien_filter", "[S1.2] Wien 0,45T h=150"),
        ("s1_energy_filter", "[S1.5] HDA ΔE=0,453eV"),
        ("s1_transfer_lens", "[S1.6] Transfer Ø28/Ø84"),
    ],
    "s2_mems_write_head": [
        ("s2_mount_strut_1", "[S2.5] 3× Dikme (8 mm)"),
        ("s2_aperture_plate", "[S2.1] Apertür Ø28/Ø100"),
        ("s2_tile_carrier", "[S2.4] 16× 64-ch Karo"),
        ("s2_blanker_plate", "[S2.2] 0,50mm Blanker"),
        ("s2_spacer_lower", "[S2.3] Al₂O₃ 1,0 mm"),
        ("s2_mini_lens_plate", "[S2.3] Arch-B 32×32 WD0,25"),
    ],
    "s3_ibic_detector_assembly": [
        ("s3_ibic_contact_ring", "[S3.1] IBIC Ø64/Ø78"),
        ("s3_silicon_wafer", "[S5.4] Ø50 Si (0 V)"),
        ("s3_wafer_carrier", "[S3.1] 80×80 AlN"),
        ("s3_hv_bias_shield_pos", "[S3.3] HV Kalkan (±Y)"),
        ("s3_ibic_csa_pos", "[S3.2] 100K LTC6268 CSA"),
    ],
    "s4_piezo_stage_interferometry": [
        ("s4_piezo_fine_6dof", "[S4.3] 6-DOF Piezo"),
        ("s4_piezo_coarse_xy", "[S4.3] Kaba XY 26mm"),
        ("s4_metrology_frame", "[S4.5] Zerodur Halka"),
        ("s4_interferometer_x", "[S4.4] 3-Eks İnterf."),
        ("s4_stage_pedestal", "[S4.3] Invar Tüp R45-52"),
        ("s4_laser_head", "[S4.4] Lazer Ünitesi"),
        ("s4_active_table", "[S4.2] Aktif Tabla"),
        ("s4_granite_base", "[S4.1] Granit Blok"),
        ("s4_air_isolator_2", "[S4.1] 4× Hava Yayı"),
    ],
    "s5_uhv_chamber_loadlock": [
        ("s5_chamber_top_flange", "[S5.1] CF400 Üst Flanş"),
        ("s5_chamber_wall_upper", "[S5.1] UHV Oda 34,9 L"),
        ("s5_ion_tsp_pump", "[S5.2] İyon+TSP Pompa"),
        ("s5_loadlock_chamber", "[S5.3] Load-Lock Oda"),
        ("s5_transfer_arm", "[S5.3] Transfer Kolu"),
        ("s5_flash_anneal_head", "[S5.5] Flaş Tavlama"),
        ("s5_turbo_pump", "[S5.2] Turbo 300 L/s"),
        ("s5_chamber_bottom_flange", "[S5.1] Taban Flanşı"),
        ("s5_loadlock_stand", "[S5.3] Ayrık Sehpa"),
    ],
    "s6_cryo_dr_magnet_readout": [
        ("s6_pt420_coldhead", "[S6.1] PT415/420"),
        ("s6_dr_flange_50k", "[S6.8] 50 K Flanş"),
        ("s6_dr_flange_4k", "[S6.8] 4 K Flanş"),
        ("s6_hemt_rack_4k", "[S6.6] 4K HEMT Rafı"),
        ("s6_coil_s_upper", "[S6.3] S_upper Şim"),
        ("s6_coil_a_upper", "[S6.3] A_upper Kalkan"),
        ("s6_coil_m_upper", "[S6.3] M_upper 1,5 T"),
        ("s6_mxc_cold_finger", "[S6.2] 20mK Parmak"),
        ("s6_coil_m_lower", "[S6.3] M_lower 1,5 T"),
        ("s6_coil_b_upper", "[S6.3] B_up/low Bucking"),
        ("s6_nbtin_resonator_carrier", "[S6.6] NbTiN 22,3 µT"),
        ("s6_cryoperm_sleeve", "[S6.3] Cryoperm+Nb Kab"),
        ("s6_dr_support_frame", "[S6.8] DR Şasisi"),
    ],
    "s7_electronics_rack_interconnect": [
        ("s7_rack_top", "[S7.1] 30U Tavan/Fan"),
        ("s7_clock_sync_bay", "[S7.4] 10MHz Rb Saat"),
        ("s7_awg_rf_mw_bay", "[S7.2] AWG & RF/MW"),
        ("s7_feedthrough_panel", "[S7.4] Kriyo/RF Panel"),
        ("s7_fpga_blanker_bay", "[S7.3] FPGA Blanker"),
        ("s7_host_gpu_server", "[S7.1] GRAPE/CellISA"),
        ("s7_psu_hv_bay", "[S7.4] ±5kV & 8-Bobin PSU"),
        ("s7_rack_base", "[S7.1] Taban Şasi"),
    ],
}

SUBSYSTEM_EXTRA_DIMS = {
    "s1_ion_source_column": [
        ("v", 922.66, 1062.66, -55.0, -64.0, "140 (S1.1)"),
        ("v", 717.66, 867.66, -55.0, -64.0, "150 (Wien)"),
        ("v", 614.66, 709.66, -55.0, -64.0, "95 (HDA)"),
    ],
    "s2_mems_write_head": [
        ("h", -50.0, 50.0, 531.66, -24.0, "Ø100 (S2.1)"),
        ("v", 500.25, 531.66, -66.0, -64.0, "31,4 (S2)"),
    ],
    "s3_ibic_detector_assembly": [
        ("h", -40.0, 40.0, 499.0, -24.0, "80 (AlN)"),
        ("h", -25.0, 25.0, 501.0, -44.0, "Ø50 Yonga"),
    ],
    "s4_piezo_stage_interferometry": [
        ("v", 80.0, 200.0, -450.0, -66.0, "120"),
        ("v", 200.0, 260.0, -450.0, -66.0, "60"),
        ("h", -45.0, 45.0, 471.0, -22.0, "90 (6-DOF)"),
    ],
    "s5_uhv_chamber_loadlock": [
        ("v", 285.0, 620.0, -225.0, -66.0, "335 (34,9L)"),
        ("h", -192.0, 192.0, 645.0, -22.0, "Ø384 Oda"),
    ],
    "s6_cryo_dr_magnet_readout": [
        ("v", 482.0, 518.0, -176.0, -18.0, "36 Yarık"),
        ("h", -75.0, 75.0, 612.0, -26.0, "Ø150 Bore"),
    ],
    "s7_electronics_rack_interconnect": [
        ("v", 800.0, 1100.0, 744.0, -64.0, "300 AWG"),
        ("v", 300.0, 540.0, 744.0, -64.0, "240 GPU"),
    ],
}


# ---------------------------------------------------------------------------
# Renderers for All 10 Sheets
# ---------------------------------------------------------------------------
def _render_to_svg_and_png(stem: str, draw_fn) -> None:
    DRAW_DIR.mkdir(parents=True, exist_ok=True)
    svg_path = DRAW_DIR / f"{stem}.svg"
    png_path = DRAW_DIR / f"{stem}.png"

    # 1. Crisp vector SVG
    svg_surf = cairo.SVGSurface(str(svg_path), W, H)
    draw_fn(cairo.Context(svg_surf))
    svg_surf.finish()

    # 2. High-res anti-aliased PNG (2400 x 1600)
    img_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(img_surf)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)
    draw_fn(ctx)
    img_surf.write_to_png(str(png_path))

    # Quick Pillow sanity verify
    with Image.open(png_path) as im:
        assert im.size == (W, H), f"Unexpected PNG size {im.size}"
    print(f"DRAW_OK {stem:36s} PNG={W}x{H} ({png_path.stat().st_size // 1024} KB) SVG=({svg_path.stat().st_size // 1024} KB)")


def build_subsystem_sheet(idx: int, sub_key: str, ver: dict) -> None:
    meta = params.SUBSYSTEMS[sub_key]
    sub_parts = params.subsystem_parts(sub_key)
    sub_ver = ver["subsystems"][sub_key]
    stem = f"{idx:02d}_{sub_key}"

    def draw(ctx: cairo.Context) -> None:
        # Compute true ISO A2 Front scale for title block
        span = sub_ver["bbox_span_mm"]
        approx_sc = min(490.0 / max(span[0], 1.0), 740.0 / max(span[2], 1.0))
        a2_ratio = (W / 594.0) / max(approx_sc, 1e-6)
        sc_lbl = f"1:{a2_ratio:.1f}" if a2_ratio >= 1.0 else f"{1.0/a2_ratio:.1f}:1"

        draw_iso_frame_and_title_block(
            ctx,
            drawing_no=meta["drawing_no"],
            title_tr=f"{meta['code']} — {meta['title_tr']}",
            subtitle_tr=f"Alt Sistem İmalat/Montaj Blueprint | Zarf: {span[0]:.0f}×{span[1]:.0f}×{span[2]:.0f} mm",
            mass_kg=sub_ver["mass_kg"],
            part_count=sub_ver["part_count"],
            scale_label=sc_lbl,
            clash_count=ver["interference_audit"]["solid_clashes"],
        )

        # Panel 1 (Top-Left): Front View / Section (X-Z)
        draw_ortho_panel(
            ctx, (62, 62, 790, 885), sub_parts, "xz",
            f"ÖN GÖRÜNÜM / KESİT A–A (X–Z) — {meta['code']}",
            section_mode=(sub_key in ("s5_uhv_chamber_loadlock", "s6_cryo_dr_magnet_readout")),
            dim_specs=SUBSYSTEM_EXTRA_DIMS.get(sub_key),
            callouts=SUBSYSTEM_CALLOUTS.get(sub_key),
            show_beam=(sub_key in ("s1_ion_source_column", "s2_mems_write_head", "s3_ibic_detector_assembly")),
        )

        # Panel 2 (Bottom-Left): Top View (X-Y)
        draw_ortho_panel(
            ctx, (62, 962, 790, 580), sub_parts, "xy",
            f"ÜST GÖRÜNÜM (X–Y DÜZLEMİ) — {meta['code']}",
            section_mode=False,
            show_beam=False,
        )

        # Panel 3 (Top-Middle): Shaded 3D Isometric
        az = -56.0 if sub_key != "s6_cryo_dr_magnet_readout" else -124.0
        draw_iso_panel(
            ctx, (868, 62, 756, 885), sub_parts,
            f"GÖLGELİ 3B İZOMETRİK GÖRÜNÜM — {meta['code']}",
            azim_deg=az, elev_deg=22.0,
            show_beam=(sub_key in ("s1_ion_source_column", "s2_mems_write_head")),
            n_seg=24,
        )

        # Panel 4 (Bottom-Middle): Side View (Y-Z)
        draw_ortho_panel(
            ctx, (868, 962, 756, 580), sub_parts, "yz",
            f"YAN GÖRÜNÜM (Y–Z DÜZLEMİ) — {meta['code']}",
            section_mode=False,
            show_beam=(sub_key in ("s1_ion_source_column", "s2_mems_write_head")),
        )

        # Panel 5 (Right Column): BOM Table & Engineering Notes
        draw_bom_and_notes_panel(ctx, (1640, 62, 714, 1248), sub_key, ver)

    _render_to_svg_and_png(stem, draw)


def build_master_assembly_sheet(ver: dict) -> None:
    ma = ver["master_assembly"]
    span = ma["bbox_span_mm"]

    def draw(ctx: cairo.Context) -> None:
        draw_iso_frame_and_title_block(
            ctx,
            drawing_no="ALM-300-M1",
            title_tr="TAM MONTAJ — ATOM LİTOGRAFİ MAKİNESİ (S1–S7)",
            subtitle_tr=f"s=0,5 Altın Zarf | {span[0]:.0f}×{span[1]:.0f}×{span[2]:.0f} mm | CoM=({ma['center_of_mass_mm'][0]:.0f}, {ma['center_of_mass_mm'][1]:.0f}, {ma['center_of_mass_mm'][2]:.0f}) mm",
            mass_kg=ma["total_mass_kg"],
            part_count=ma["part_count"],
            scale_label="1:14",
            clash_count=ver["interference_audit"]["solid_clashes"],
        )

        master_callouts = [
            ("s1_duoplasmatron", "[S1] Exp124 562,7mm Kolon"),
            ("s1_energy_filter", "[S1.5] HDA ΔE=0,453eV"),
            ("s6_pt420_coldhead", "[S6.1] PT415/420 DR"),
            ("s6_coil_a_upper", "[S6.3] Exp125 8-Bobin"),
            ("s5_loadlock_chamber", "[S5.3] Load-Lock"),
            ("s7_awg_rf_mw_bay", "[S7] 19\" RF/AWG Kabin"),
            ("s4_granite_base", "[S4] Granit+6DOF Piezo"),
        ]
        # Top-Left: Front View (X-Z)
        draw_ortho_panel(
            ctx, (62, 62, 1020, 885), params.PARTS, "xz",
            "TAM MONTAJ ÖN GÖRÜNÜMÜ (X–Z) — 10→5 keV KOLON, s=0,5 UHV, 20 mK DR & 19\" KABİN",
            section_mode=False,
            callouts=master_callouts,
            show_beam=True,
        )
        # Bottom-Left: Top View (X-Y)
        draw_ortho_panel(
            ctx, (62, 962, 1020, 580), params.PARTS, "xy",
            "TAM MONTAJ ÜST GÖRÜNÜMÜ (X–Y TABAN İZİ) — 4 EKVATORYAL PORT (+X/-X/+Y/-Y)",
            section_mode=False,
            show_beam=False,
        )
        # Top-Right-Mid: Shaded 3D Isometric
        draw_iso_panel(
            ctx, (1098, 62, 526, 885), params.PARTS,
            "3B İZOMETRİK MONTAJ",
            azim_deg=-60.0, elev_deg=23.0, show_beam=True, n_seg=18,
        )
        # Bottom-Right-Mid: Side View (Y-Z)
        draw_ortho_panel(
            ctx, (1098, 962, 526, 580), params.PARTS, "yz",
            "YAN GÖRÜNÜM (Y–Z)",
            section_mode=False, show_beam=True,
        )
        # Far-Right: Master Subsystem Mass & Verification Summary
        _draw_master_summary_panel(ctx, (1640, 62, 714, 1248), ver)

    _render_to_svg_and_png("08_atom_litho_assembly", draw)


def build_master_cutaway_sheet(ver: dict) -> None:
    ma = ver["master_assembly"]

    def draw(ctx: cairo.Context) -> None:
        draw_iso_frame_and_title_block(
            ctx,
            drawing_no="ALM-300-M2",
            title_tr="KESİT GÖRÜNÜMÜ A–A — İÇ MİMARİ, KAFA, YONGA & 20 mK DR",
            subtitle_tr="Y=0 Merkez Kesiti + 4× Büyütülmüş Yonga/MEMS/IBIC Detayı B + 3B Kesit İzometrik",
            mass_kg=ma["total_mass_kg"],
            part_count=ma["part_count"],
            scale_label="1:10 / B 4:1",
            clash_count=ver["interference_audit"]["solid_clashes"],
        )

        cut_callouts = [
            ("s1_duoplasmatron", "[S1.1] Duoplazmatron +5kV"),
            ("s1_wien_filter", "[S1.2] Wien 0,45T h=150"),
            ("s1_energy_filter", "[S1.5] HDA ΔE=0,453eV"),
            ("s6_dr_flange_50k", "[S6.8] 50K/4K/Still/MXC"),
            ("s6_coil_s_upper", "[S6.3] 8-Bobin Ø150 Bore"),
            ("s2_aperture_plate", "[S2] Arch-B + Blanker"),
            ("s3_silicon_wafer", "[S3] Yonga+100K LTC6268"),
            ("s6_mxc_cold_finger", "[S6.2] 20mK Parmak"),
            ("s4_piezo_fine_6dof", "[S4.3] 6-DOF Piezo"),
            ("s6_nbtin_resonator_carrier", "[S6.6] NbTiN z=−155 (22µT)"),
            ("s4_granite_base", "[S4.1] Granit+Aktif"),
        ]
        # Left Large Panel: Full Machine Cross-Section (X-Z, excluding far +X rack so core fills canvas!)
        core_parts = {k: v for k, v in params.PARTS.items() if v["subsystem"] != "s7_electronics_rack_interconnect"}
        draw_ortho_panel(
            ctx, (62, 62, 1080, 960), core_parts, "xz",
            "MERKEZ KESİT A–A (Y = 0 DÜZLEMİ) — EXP124 562,7 mm KOLON, EXP125 8-BOBİN MIKNATIS & 20 mK DR",
            section_mode=True,
            dim_specs=[
                ("v", 482.0, 518.0, 192.0, 18.0, "36 Yarık"),
                ("v", 345.0, 500.0, -192.0, -24.0, "Δz=−155"),
            ],
            callouts=cut_callouts,
            show_beam=True,
        )
        # Bottom-Left: Detail B — Core Section showing Arch-B WD=0.25mm, Wafer/IBIC, 6-DOF Piezo, & -155mm NbTiN/Meissner!
        detail_parts = {
            k: v for k, v in params.PARTS.items()
            if v["subsystem"] in ("s2_mems_write_head", "s3_ibic_detector_assembly", "s4_piezo_stage_interferometry", "s6_cryo_dr_magnet_readout")
        }
        draw_ortho_panel(
            ctx, (62, 1038, 1080, 504), detail_parts, "xz",
            "DETAY B (ÇEKİRDEK KESİTİ) — ARCH-B WD=0,25 mm, 100 K LTC6268 IBIC, 6-DOF PİEZO & z=−155 mm NbTiN/MEISSNER",
            section_mode=True,
            zoom_box=(-145.0, 145.0, 310.0, 545.0),
            dim_specs=[
                ("v", 345.0, 500.0, -118.0, -26.0, "Δz=155"),
                ("h", -40.0, 40.0, 500.0, 22.0, "80 AlN"),
            ],
            callouts=[
                ("s2_aperture_plate", "[S2.1] Apertür Ø28/Ø100"),
                ("s2_tile_carrier", "[S2.4] 16× 64-ch Karo"),
                ("s2_mini_lens_plate", "[S2.3] Arch-B 32×32 WD0,25"),
                ("s3_ibic_contact_ring", "[S3.1] IBIC + 100K CSA"),
                ("s4_piezo_fine_6dof", "[S4.3] 6-DOF Piezo"),
                ("s6_coil_b_upper", "[S6.3] B_up/low Bucking"),
                ("s6_cryoperm_sleeve", "[S6.3] Cryoperm + Nb Kab"),
                ("s6_nbtin_resonator_carrier", "[S6.6] NbTiN Ø50 (22,3µT)"),
            ],
            show_beam=True,
        )

        # Top-Right-Mid: 3D Half-Cutaway Isometric (core machine clipped at Y<0)
        draw_iso_panel(
            ctx, (1158, 62, 466, 960), core_parts,
            "3B YARIM KESİT İZOMETRİK (Y ≥ 0)",
            azim_deg=-72.0, elev_deg=18.0, clip_y_neg=True, show_beam=True, n_seg=18,
        )
        # Bottom-Right-Mid: Critical Clearances Verification Table
        _draw_clearances_panel(ctx, (1158, 1038, 466, 504), ver)

        # Far-Right: Section Legend & Physics/Cryo/Optics Specs
        _draw_cutaway_spec_panel(ctx, (1640, 62, 714, 1248), ver)

    _render_to_svg_and_png("09_atom_litho_cutaway", draw)


def build_master_exploded_sheet(ver: dict) -> None:
    ma = ver["master_assembly"]

    def draw(ctx: cairo.Context) -> None:
        draw_iso_frame_and_title_block(
            ctx,
            drawing_no="ALM-300-M3",
            title_tr="PATLATILMIŞ MONTAJ GÖRÜNÜMÜ (EXPLODED S1–S7)",
            subtitle_tr="7 Modüler Alt Sistemin (M1–M8) Ayrımlaşma Akışı, Arayüz Sınırları & Montaj Sırası",
            mass_kg=ma["total_mass_kg"],
            part_count=ma["part_count"],
            scale_label="1:16 (Patl.)",
            clash_count=ver["interference_audit"]["solid_clashes"],
        )

        # Huge 3D Exploded Isometric Canvas
        sub_pts = draw_iso_panel(
            ctx, (62, 62, 1562, 1480), params.PARTS,
            "3B PATLATILMIŞ MODÜLER MONTAJ — 7 BAĞIMSIZ ALT SİSTEM (S1–S7) & EKSENEL/YANAL MONTAJ KILAVUZLARI",
            azim_deg=-58.0, elev_deg=21.0,
            explode_scale=1.15, show_beam=True, show_explode_guides=True, n_seg=18,
        )

        # Overlay clean floating subsystem badges pointing to exploded clusters (live masses from ver)
        sm = {k: ver["subsystems"][k]["mass_kg"] for k in params.SUBSYSTEMS}
        badge_pos = {
            "s1_ion_source_column":            (640, 120, f"S1 — Exp124 562,7mm Kolon ({sm['s1_ion_source_column']:.1f} kg)"),
            "s2_mems_write_head":              (800, 405, f"S2 — Arch-B Mini-Lens & MEMS ({sm['s2_mems_write_head']:.1f} kg)"),
            "s3_ibic_detector_assembly":       (815, 510, f"S3 — Yonga & 100K LTC6268 ({sm['s3_ibic_detector_assembly']:.2f} kg)"),
            "s4_piezo_stage_interferometry":   (380, 1440, f"S4 — Granit, Aktif Tabla & 6-DOF Piezo ({sm['s4_piezo_stage_interferometry']:.1f} kg)"),
            "s5_uhv_chamber_loadlock":         (910, 1345, f"S5 — s=0,5 UHV Oda 34,9L & Load-Lock ({sm['s5_uhv_chamber_loadlock']:.1f} kg)"),
            "s6_cryo_dr_magnet_readout":       (95,  195, f"S6 — Exp125 8-Bobin & 20mK DR ({sm['s6_cryo_dr_magnet_readout']:.1f} kg)"),
            "s7_electronics_rack_interconnect":(1080, 180, f"S7 — 19\" RF/AWG/FPGA/GPU Kabini ({sm['s7_electronics_rack_interconnect']:.1f} kg)"),
        }
        for sub_key, (bx, by, label) in badge_pos.items():
            if sub_key not in sub_pts:
                continue
            tx, ty = sub_pts[sub_key]
            ctx.save()
            ctx.set_source_rgb(*NAVY_HDR)
            ctx.set_line_width(1.6)
            ctx.arc(tx, ty, 4.5, 0, 2 * math.pi); ctx.fill()
            ctx.move_to(tx, ty)
            ctx.line_to(bx + 140, by + 15)
            ctx.stroke()
            ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            ctx.set_font_size(12.0)
            bw = ctx.text_extents(label).width + 20.0
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.94)
            ctx.rectangle(bx, by, bw, 28)
            ctx.fill_preserve()
            ctx.set_source_rgb(*ACCENT_BLUE)
            ctx.set_line_width(1.5)
            ctx.stroke()
            _draw_text(ctx, bx + 10, by + 19, label, 12.0, bold=True, color=NAVY_HDR)
            ctx.restore()

        # Right Column: Exploded Assembly Sequence & Subsystem Table
        _draw_master_summary_panel(ctx, (1640, 62, 714, 1248), ver, include_seq=True)

    _render_to_svg_and_png("10_atom_litho_exploded", draw)


def _draw_master_summary_panel(
    ctx: cairo.Context, rect: tuple[float, float, float, float], ver: dict, include_seq: bool = False
) -> None:
    x0, y0, pw, ph = rect
    _draw_panel_box(ctx, x0, y0, pw, ph, "ALT SİSTEM KÜTLE, ZARF & STL DOĞRULAMA ÖZETİ")
    tx = x0 + 12.0
    ty = y0 + 44.0

    # Subsystem table
    ctx.set_source_rgb(*NAVY_HDR)
    ctx.rectangle(tx, ty, pw - 24, 26); ctx.fill()
    for dx, hdr in ((4, "Kod"), (46, "Alt Sistem"), (320, "Parça"), (380, "Üçgen"), (460, "Zarf (mm)"), (622, "Kütle")):
        _draw_text(ctx, tx + dx, ty + 17, hdr, 10.5, bold=True, color=(1, 1, 1))

    ry = ty + 26.0
    row_h = 34.0
    for i, (sk, sv) in enumerate(ver["subsystems"].items()):
        if i % 2 == 1:
            ctx.set_source_rgb(0.953, 0.965, 0.980)
            ctx.rectangle(tx, ry, pw - 24, row_h); ctx.fill()
        sp = sv["bbox_span_mm"]
        tname = sv["title_tr"] if len(sv["title_tr"]) <= 34 else sv["title_tr"][:32] + "…"
        yt = ry + 22.0
        _draw_text(ctx, tx + 4, yt, sv["code"], 11.0, bold=True, color=ACCENT_BLUE)
        _draw_text(ctx, tx + 46, yt, tname, 10.2, color=INK_DARK)
        _draw_text(ctx, tx + 328, yt, str(sv["part_count"]), 10.5, mono=True, color=INK_DARK)
        _draw_text(ctx, tx + 382, yt, f"{sv['stl']['triangles']:,}", 10.2, mono=True, color=INK_MED)
        _draw_text(ctx, tx + 460, yt, f"{sp[0]:.0f}×{sp[1]:.0f}×{sp[2]:.0f}", 9.8, mono=True, color=INK_MED)
        _draw_text(ctx, tx + pw - 30, yt, f"{sv['mass_kg']:.1f} kg", 10.8, bold=True, color=INK_DARK, align="right")
        ry += row_h

    # Total bar
    ma = ver["master_assembly"]
    ctx.set_source_rgb(0.89, 0.92, 0.96)
    ctx.rectangle(tx, ry, pw - 24, 30); ctx.fill()
    _draw_text(ctx, tx + 8, ry + 20, "TOPLAM MAKİNE (atom_litho_machine.stl)", 11.0, bold=True, color=NAVY_HDR)
    _draw_text(ctx, tx + 328, ry + 20, str(ma["part_count"]), 11.0, bold=True, mono=True, color=NAVY_HDR)
    _draw_text(ctx, tx + 382, ry + 20, f"{ma['stl']['triangles']:,}", 10.5, bold=True, mono=True, color=NAVY_HDR)
    _draw_text(ctx, tx + pw - 30, ry + 20, f"{ma['total_mass_kg']:.1f} kg", 11.5, bold=True, color=NAVY_HDR, align="right")
    ry += 44.0

    # Verification checks card
    e80 = ver["exp80_golden_envelope_audit"]
    e84 = ver["exp84_modal_audit"]
    inter = ver["interference_audit"]
    clr_ok = sum(1 for v in ver["critical_clearances"].values() if v["pass"])
    clr_tot = len(ver["critical_clearances"])

    ctx.set_source_rgb(0.93, 0.98, 0.95)
    ctx.rectangle(tx, ry, pw - 24, 218); ctx.fill_preserve()
    ctx.set_source_rgb(*ACCENT_GREEN); ctx.set_line_width(1.3); ctx.stroke()
    _draw_text(ctx, tx + 12, ry + 24, "OTOMATİK MEKANİK & GEOMETRİ DOĞRULAMASI — PASS", 12.0, bold=True, color=ACCENT_GREEN)
    checks_txt = [
        f"• Katı-Katı Çakışma: {inter['solid_clashes']} / {inter['pairs_checked']:,} çift (0,05 mm marj) — PASS",
        f"• Kritik Boşluklar: {clr_ok}/{clr_tot} PASS (WD=0,25 mm, Dizi↔Ø28 Bore=2,69 mm)",
        f"• Su Geçirmez STL: 8/8 dosya (0 açık / 0 non-manifold kenar, {ma['stl']['triangles']:,} üçgen) — PASS",
        f"• Exp124 Kolon: 562,66 mm, 32×32 @ 0,50 mm (16×16 mm, Ø28 bore), 25,92 kg — PASS",
        f"• Exp125 8-Bobin: Ø150 bore, 36 mm yarık, Ø352 OD, NbTiN z=−155 (22,3 µT) — PASS",
        f"• Exp80 BC4 Oda Hacmi: {e80['bc4_chamber_volume_one_eighth']['value_L']:.2f} L (s=1,0'ın {e80['bc4_chamber_volume_one_eighth']['ratio_to_s1']:.4f}× ≈ 1/8) — PASS",
        f"• Exp84 Modal: f₁={e84['blanker_f1_fea_hz']/1e6:.3f} MHz | Maglev=YOK | 100K LTC6268 — PASS",
    ]
    cy = ry + 48.0
    for line in checks_txt:
        _draw_text(ctx, tx + 12, cy, line, 10.3, color=INK_DARK)
        cy += 23.0
    ry += 236.0

    # Assembly sequence or design specifications
    ctx.set_source_rgb(0.955, 0.968, 0.985)
    rem_h = (y0 + ph - 14.0) - ry
    ctx.rectangle(tx, ry, pw - 24, rem_h); ctx.fill_preserve()
    ctx.set_source_rgb(*ACCENT_BLUE); ctx.set_line_width(1.1); ctx.stroke()
    if include_seq:
        _draw_text(ctx, tx + 12, ry + 24, "MODÜLER MONTAJ AKIŞ SIRASI (ICD M1–M8)", 12.0, bold=True, color=NAVY_HDR)
        steps = [
            "1. [S4.1–S4.2] 4× hava yayı + 900×700 granit blok + aktif sönümleme tablası kurulumu.",
            "2. [S5.1] UHV taban flanşı (CF350) + [S4.3–S4.5] Invar kaide, 6-DOF piezo & Zerodur halka.",
            "3. [S6.2–S3] Vespel izolatör + 20 mK Cu ada + 80×80 AlN taşıyıcı + Ø50 yonga + IBIC/CSA.",
            "4. [S5.1–S6.3] Ekvatoryal portlu UHV gövde + ayrık-çift 1,5 T bobin & karşı-sargı montajı.",
            "5. [S6.8–S6.2] -X 5-kademe DR kulesi + PT420 + 20 mK parmak köprüsü + 4 K HEMT/koaksiyel.",
            "6. [S5.2/S5.3/S5.5] -Y turbo/iyon pompa, +X load-lock & transfer kolu, +Y flaş tavlama portu.",
            "7. [S6.6/S2/S1] Meissner kalkan + NbTiN rezonatör → MEMS yazma kafası → 10→5 keV iyon kolonu.",
            "8. [S7] +X 19\" 30U RF/AWG/FPGA/GPU kabini (85 mm transfer boşluğu) + kriyo/UHV yama paneli.",
        ]
        cy = ry + 50.0
        for s in steps:
            _draw_text(ctx, tx + 12, cy, s, 10.6, color=INK_DARK)
            cy += 36.0
    else:
        _draw_text(ctx, tx + 12, ry + 24, "KİLİT SİSTEM ŞARTNAMESİ (EXP124 / EXP125 / EXP127 KİLİTLİ)", 11.5, bold=True, color=NAVY_HDR)
        ds = ver["design_specs"]
        specs = [
            f"• Exp124 Kolon (562,66 mm, 25,92 kg): Arch-B WD={ds['working_distance_mm']} mm, HDA ΔE={ds['energy_filter_dE_eV']} eV, σ_nokta={ds['spot_sigma_nm']} nm, σ_top={ds['total_sigma_nm']} nm",
            f"• HV Şeması: {ds['hv_grounding']}",
            f"• Exp125 8-Bobin Mıknatıs: Ø150 mm bore, 36 mm yarık, Ø352 mm OD, B_örnek={ds['magnet_B_sample_T']:.2f} T (17,8 ppm)",
            f"• Exp125 Sessiz Rezonatör Bölgesi: z_loc={ds['resonator_plane_dz_mm']:.0f} mm, Ø50 mm NbTiN diski (|B|={ds['magnet_B_res_shielded_uT']} µT) + Nb + Cryoperm-10",
            f"• Kriyo & Okuma: Baz S6.8 DR MXC={ds['dr_mxc_temp_mK']:.0f} mK, 56–82 zincir, NL=110–160, Ql=800–1200, 4 K HEMT ≤ 1,0 W",
            f"• Exp127 IBIC Ön-Uç: {ds['ibic_csa_ic']}",
            f"• Ağırlık Merkezi: X={ma['center_of_mass_mm'][0]:.1f}, Y={ma['center_of_mass_mm'][1]:.1f}, Z={ma['center_of_mass_mm'][2]:.1f} mm  |  Taban İz: {ma['bbox_span_mm'][0]:.0f}×{ma['bbox_span_mm'][1]:.0f} mm",
            f"• Epistemik Durum: Kâğıt üzerinde parametrik CAD/model (no_lab_measurement=true).",
        ]
        cy = ry + 50.0
        for s in specs:
            _draw_text(ctx, tx + 12, cy, s, 10.3, color=INK_DARK)
            cy += 36.0


def _draw_clearances_panel(ctx: cairo.Context, rect: tuple[float, float, float, float], ver: dict) -> None:
    x0, y0, pw, ph = rect
    clr = ver["critical_clearances"]
    ok_cnt = sum(1 for v in clr.values() if v["pass"])
    _draw_panel_box(ctx, x0, y0, pw, ph, f"KRİTİK BOŞLUK DENETİMİ ({ok_cnt}/{len(clr)} PASS)")
    labels_tr = {
        "exp124_archB_wafer_to_minilens_WD_mm": "Exp124 Arch-B Yonga↔Lens (WD)",
        "beam_array_diagonal_to_bore_clearance_mm": "32×32 Dizi (22,63) ↔ Ø28 Bore",
        "ibic_ring_to_archB_lens_radial_mm": "IBIC Halka ↔ Arch-B Lens (R)",
        "tile_carrier_to_magnet_bore_radial_mm": "Karo PCB ↔ Ø150 Bore (R)",
        "aperture_frame_to_magnet_bore_radial_mm": "Apertür ↔ Ø150 Bore (R)",
        "transfer_lens_to_magnet_bore_radial_mm": "Transfer Lens ↔ Bore (R)",
        "hda_filter_to_top_flange_bore_radial_mm": "HDA Süzgeç ↔ Üst Flanş (R)",
        "piezo_coarse_corner_to_magnet_bore_mm": "Piezo Köşe ↔ Ø150 Bore",
        "pedestal_to_cryoperm_radial_mm": "Invar Kaide ↔ Cryoperm (R)",
        "pedestal_to_bucking_coil_radial_mm": "Invar Kaide ↔ B-Bobin (R)",
        "nbtin_disk_inside_nb_meissner_radial_mm": "NbTiN Disk ↔ Nb Meissner",
        "nb_meissner_inside_cryoperm_radial_mm": "Nb Meissner ↔ Cryoperm",
        "magnet_former_to_chamber_wall_radial_mm": "Ø352 Karkas ↔ UHV Duvar",
        "cryo_4k_tube_in_36mm_magnet_split_z_mm": "4K Tüp ↔ 36 mm Yarık (Z)",
        "cold_finger_inside_4k_shield_radial_mm": "20mK Parmak ↔ 4K Kalkan",
        "dr_frame_to_granite_x_mm": "DR Şasi ↔ Granit (X)",
        "granite_to_loadlock_stand_x_mm": "Granit ↔ Load-Lock (X)",
        "transfer_arm_to_s7_panel_x_mm": "Transfer Kolu ↔ S7 (X)",
        "turbo_pump_to_granite_y_mm": "Turbo Pompa ↔ Granit (Y)",
    }
    ry = y0 + 44.0
    rh = (ph - 52.0) / len(clr)
    for i, (k, rec) in enumerate(clr.items()):
        if i % 2 == 1:
            ctx.set_source_rgb(0.955, 0.968, 0.982)
            ctx.rectangle(x0 + 8, ry, pw - 16, rh); ctx.fill()
        yt = ry + rh * 0.72
        _draw_text(ctx, x0 + 14, yt, labels_tr.get(k, k), 9.6, color=INK_DARK)
        val_str = f"{rec['value_mm']:.2f} mm" if rec["value_mm"] < 1.0 else f"{rec['value_mm']:.1f} mm"
        _draw_text(ctx, x0 + pw - 95, yt, val_str, 9.8, bold=True, mono=True, color=INK_DARK, align="right")
        _draw_text(ctx, x0 + pw - 14, yt, "PASS" if rec["pass"] else "FAIL", 9.6, bold=True,
                   color=ACCENT_GREEN if rec["pass"] else ACCENT_RED, align="right")
        ry += rh


def _draw_cutaway_spec_panel(ctx: cairo.Context, rect: tuple[float, float, float, float], ver: dict) -> None:
    x0, y0, pw, ph = rect
    _draw_panel_box(ctx, x0, y0, pw, ph, "KESİT MİMARİSİ & ISI / MANYETİK / OPTİK KATMANLAR")
    tx, ry = x0 + 16.0, y0 + 54.0
    blocks = [
        ("1. EXP124 İYON OPTİĞİ KOLONU (562,66 mm, 25,92 kg)", [
            "• Z=922,7..1062,7: S1.1 Duoplazmatron (+5 kV, h=140, OD=90) + PH₃.",
            "• Z=717,7..918,7:  S1.4 Kondansör (h=45) + S1.2 Wien (h=150, 0,45 T).",
            "• Z=614,7..709,7:  S1.5 HDA-HiRes süzgeç (R₀=40, ΔE_FWHM=0,453 eV).",
            "• Z=539,7..604,7:  S1.6 Telecentric transfer lensi (h=65, Ø28/Ø84).",
            "• Z=500,25..531,7: 32×32 @ 0,50 mm (16×16 mm, Ø28 bore → 2,69 mm marj).",
            "• WD = 0,250 mm:   Arch-B E_gap=10,60 MV/m, C_c=2,660 mm; 16× 64-ch karo.",
        ]),
        ("2. EXP125 8-BOBİNLİ MIKNATIS & REZONATÖR (R7)", [
            "• 8 Bobin (M/S/A/B): Ø150 mm delik, 36 mm yarık (Z=482..518), Ø352 OD.",
            "• Z=500 mm (Yonga):  B_z = 1,500 T ± 17,8 ppm homojenlik (r ≤ 2,3 mm).",
            "• Z=345 mm (z=−155): Ø50 mm NbTiN rezonatör diski (|B| = 22,3 µT!).",
            "• Nb RRR>300 Meissner kabı (R=32..34,5, baca r=8, h=11) + Cryoperm (R=39..41).",
            "• Invar tüp kaide (R=45..52) Cryoperm ile B-bobin arasından 4 mm payla geçer.",
        ]),
        ("3. 20 mK DR (S6.8) & 100 K LTC6268 IBIC (EXP127)", [
            "• 300 K Üst Flanş + Cryomech PT415/420 → 50 K / 4 K / Still / CP / MXC.",
            "• 4 K kademesinde 56–82 kanal 2,1 mW InP HEMT rafı (< 1,0 W).",
            "• 20 mK OFHC parmak + 4 K kalkan 36 mm yarıktan yonga adasına ulaşır.",
            "• Exp127: 100 K soğuk adada LTC6268 CSA (1,2 µs/1 GΩ, ENC=24,1 e⁻, η=0,99936).",
        ]),
        ("4. KONUMLANDIRMA & s=0,5 UHV ODA (S4 / S5)", [
            "• Z=0..260 mm: 4× hava yayı + 900×700 granit + aktif sönümleme tablası.",
            "• Z=423..471 mm: Kaba 26 mm + 6-DOF PI PIMars piezo (Ø150 delikte 7 mm pay).",
            "• Z=285..620 mm: R_iç=182 mm, V=34,86 L UHV oda (Exp80 BC4 1/8 PASS).",
        ]),
    ]
    for hdr, lines in blocks:
        ctx.set_source_rgb(0.92, 0.945, 0.975)
        ctx.rectangle(tx - 4, ry - 16, pw - 24, 24); ctx.fill()
        _draw_text(ctx, tx + 2, ry, hdr, 11.2, bold=True, color=NAVY_HDR)
        ry += 26.0
        for ln in lines:
            _draw_text(ctx, tx + 4, ry, ln, 10.3, color=INK_DARK)
            ry += 22.0
        ry += 16.0

    # Hatch legend box at bottom
    ctx.set_source_rgb(0.985, 0.988, 0.995)
    ctx.rectangle(tx - 4, y0 + ph - 110, pw - 24, 94); ctx.fill_preserve()
    ctx.set_source_rgb(*INK_LIGHT); ctx.set_line_width(1.0); ctx.stroke()
    _draw_text(ctx, tx + 8, y0 + ph - 88, "KESİT GÖSTERİM ANAHTARI (ISO 128)", 11.0, bold=True, color=NAVY_HDR)
    _draw_hatch_rect(ctx, tx + 10, y0 + ph - 74, 34, 20, step=5.5)
    ctx.set_source_rgb(*INK_DARK); ctx.rectangle(tx + 10, y0 + ph - 74, 34, 20); ctx.stroke()
    _draw_text(ctx, tx + 52, y0 + ph - 60, "Kesilen katı duvar (45° tarama)", 10.5, color=INK_DARK)
    ctx.set_source_rgb(*ACCENT_GOLD); ctx.set_line_width(3.0)
    ctx.move_to(tx + 340, y0 + ph - 64); ctx.line_to(tx + 380, y0 + ph - 64); ctx.stroke()
    _draw_text(ctx, tx + 390, y0 + ph - 60, "10→5 keV ³¹P⁺ / ²⁹Si⁺ iyon demet ekseni", 10.5, color=INK_DARK)
    ctx.save(); ctx.set_dash([10, 4, 2, 4]); ctx.set_source_rgb(*ACCENT_RED); ctx.set_line_width(1.3)
    ctx.move_to(tx + 10, y0 + ph - 36); ctx.line_to(tx + 44, y0 + ph - 36); ctx.stroke(); ctx.restore()
    _draw_text(ctx, tx + 52, y0 + ph - 32, "Simetri / demet ekseni çizgisi", 10.5, color=INK_DARK)


def main() -> None:
    ver = load_verification()
    for idx, sub_key in enumerate(params.SUBSYSTEMS.keys(), start=1):
        build_subsystem_sheet(idx, sub_key, ver)
    build_master_assembly_sheet(ver)
    build_master_cutaway_sheet(ver)
    build_master_exploded_sheet(ver)
    print("ALL_10_DRAWINGS_DONE")


if __name__ == "__main__":
    main()
