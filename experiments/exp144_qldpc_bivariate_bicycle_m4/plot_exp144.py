"""Exp144 Publication Figure Generator (PyCairo, 2400x1400 PNG).

Run with system Python that has pycairo + PIL:
  /usr/bin/python3 -B experiments/exp144_qldpc_bivariate_bicycle_m4/plot_exp144.py

Strictly portable (Path(__file__).resolve() only; zero hardcoded host paths).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cairo

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
RESULTS_DIR = REPO_ROOT / "results" / "exp144_qldpc_bivariate_bicycle_m4"
PLOT_JSON = RESULTS_DIR / "plot_data_exp144.json"
OUT_PNG = RESULTS_DIR / "fig_exp144_qldpc_m4.png"

W, H = 2400, 1400


def _hex_rgb(h: str) -> Tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _set_col(ctx: cairo.Context, h: str, a: float = 1.0) -> None:
    r, g, b = _hex_rgb(h)
    ctx.set_source_rgba(r, g, b, a)


def _rounded_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float) -> None:
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def _draw_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 14.0,
    color: str = "#0F172A",
    bold: bool = False,
    align: str = "left",
    alpha: float = 1.0,
) -> Tuple[float, float]:
    ctx.select_font_face(
        "DejaVu Sans",
        cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
    )
    ctx.set_font_size(size)
    ext = ctx.text_extents(text)
    tx = x
    if align == "center":
        tx = x - (ext.width / 2.0 + ext.x_bearing)
    elif align == "right":
        tx = x - (ext.width + ext.x_bearing)
    _set_col(ctx, color, alpha)
    ctx.move_to(tx, y)
    ctx.show_text(text)
    return ext.width, ext.height


def _draw_rotated_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    angle_rad: float = -math.pi / 2,
    size: float = 13.5,
    color: str = "#334155",
    bold: bool = True,
) -> None:
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(angle_rad)
    _draw_text(ctx, text, 0, 0, size=size, color=color, bold=bold, align="center")
    ctx.restore()


def _draw_panel_card(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, tag: str) -> None:
    _rounded_rect(ctx, x, y, w, h, 10)
    _set_col(ctx, "#FFFFFF")
    ctx.fill_preserve()
    _set_col(ctx, "#CBD5E1")
    ctx.set_line_width(1.5)
    ctx.stroke()

    # Header strip
    ctx.save()
    _rounded_rect(ctx, x, y, w, h, 10)
    ctx.clip()
    _set_col(ctx, "#F1F5F9")
    ctx.rectangle(x, y, w, 38)
    ctx.fill()
    _set_col(ctx, "#E2E8F0")
    ctx.set_line_width(1.0)
    ctx.move_to(x, y + 38)
    ctx.line_to(x + w, y + 38)
    ctx.stroke()
    ctx.restore()

    _draw_text(ctx, title, x + 14, y + 25, size=15.0, color="#0F172A", bold=True)
    _draw_text(ctx, tag, x + w - 14, y + 24, size=12.0, color="#475569", bold=True, align="right")


def _draw_marker(ctx: cairo.Context, x: float, y: float, shape: str, size: float, fill: str, stroke: str = "#FFFFFF") -> None:
    ctx.save()
    if shape == "circle":
        ctx.arc(x, y, size, 0, 2 * math.pi)
    elif shape == "square":
        ctx.rectangle(x - size, y - size, 2 * size, 2 * size)
    elif shape == "diamond":
        ctx.move_to(x, y - size * 1.25)
        ctx.line_to(x + size * 1.1, y)
        ctx.line_to(x, y + size * 1.25)
        ctx.line_to(x - size * 1.1, y)
        ctx.close_path()
    elif shape == "triangle":
        ctx.move_to(x, y - size * 1.2)
        ctx.line_to(x + size * 1.1, y + size)
        ctx.line_to(x - size * 1.1, y + size)
        ctx.close_path()
    elif shape == "star":
        for k in range(10):
            rad = size * 1.45 if k % 2 == 0 else size * 0.6
            ang = -math.pi / 2 + k * math.pi / 5
            px = x + rad * math.cos(ang)
            py = y + rad * math.sin(ang)
            if k == 0:
                ctx.move_to(px, py)
            else:
                ctx.line_to(px, py)
        ctx.close_path()
    _set_col(ctx, fill)
    ctx.fill_preserve()
    _set_col(ctx, stroke)
    ctx.set_line_width(1.6)
    ctx.stroke()
    ctx.restore()


# =============================================================================
# Individual Panels (A..F)
# =============================================================================
def _panel_a_code_capacity(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(A) Code-Capacity Scaling & BP+OSD-2 Gain", "N = 2,500 shots/pt")
    px, py, pw, ph = x + 84, y + 62, w - 114, h - 130

    p_grid = data["p_grid"]
    xmin, xmax = 0.018, 0.062
    ymin_log, ymax_log = -3.8, 0.0  # 1.6e-4 to 1.0

    def tx(v: float) -> float:
        return px + (v - xmin) / (xmax - xmin) * pw

    def ty(v: float) -> float:
        lv = math.log10(max(v, 10 ** ymin_log))
        return py + (ymax_log - lv) / (ymax_log - ymin_log) * ph

    # Grid
    for exp_y in (-3, -2, -1, 0):
        gy = ty(10 ** exp_y)
        _set_col(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        lbl = "1.0" if exp_y == 0 else f"1e{exp_y}"
        _draw_text(ctx, lbl, px - 8, gy + 4, size=12.0, color="#475569", align="right")

    for xv in (0.02, 0.03, 0.04, 0.05, 0.06):
        gx = tx(xv)
        _set_col(ctx, "#F1F5F9")
        ctx.set_line_width(1.0)
        ctx.move_to(gx, py)
        ctx.line_to(gx, py + ph)
        ctx.stroke()
        _draw_text(ctx, f"{xv*100:.0f}%", gx, py + ph + 20, size=12.0, color="#475569", align="center")

    # Axes box
    _set_col(ctx, "#64748B")
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

    # Highlight vertical p=0.04 reference
    gx4 = tx(0.04)
    ctx.save()
    ctx.set_dash([5, 4])
    _set_col(ctx, "#94A3B8")
    ctx.set_line_width(1.2)
    ctx.move_to(gx4, py)
    ctx.line_to(gx4, py + ph)
    ctx.stroke()
    ctx.restore()

    series = [
        ("BB_72_12_6", "[[72,12,6]] (d=6)", "#D97706", "square"),
        ("BB_90_8_10", "[[90,8,10]] (d=10)", "#0D9488", "triangle"),
        ("BB_144_12_12", "[[144,12,12]] Gross (d=12)", "#2563EB", "circle"),
    ]
    for skey, slbl, col, shp in series:
        vals = data[skey]
        pts = [(tx(pv), ty(max(vv, 10 ** ymin_log))) for pv, vv in zip(p_grid, vals)]
        _set_col(ctx, col)
        ctx.set_line_width(2.8)
        for i, (cx, cy) in enumerate(pts):
            if i == 0:
                ctx.move_to(cx, cy)
            else:
                ctx.line_to(cx, cy)
        ctx.stroke()
        for cx, cy in pts:
            _draw_marker(ctx, cx, cy, shp, 5.5, col)

    # Legend top-left
    lx, ly = px + 14, py + 14
    _rounded_rect(ctx, lx, ly, 236, 76, 6)
    _set_col(ctx, "#FFFFFF", 0.94)
    ctx.fill_preserve()
    _set_col(ctx, "#CBD5E1")
    ctx.set_line_width(1.0)
    ctx.stroke()
    for i, (_, slbl, col, shp) in enumerate(series):
        row_y = ly + 20 + i * 22
        _set_col(ctx, col)
        ctx.set_line_width(2.5)
        ctx.move_to(lx + 10, row_y)
        ctx.line_to(lx + 32, row_y)
        ctx.stroke()
        _draw_marker(ctx, lx + 21, row_y, shp, 4.5, col)
        _draw_text(ctx, slbl, lx + 40, row_y + 4, size=12.0, color="#0F172A", bold=(i == 2))

    # Inset Ablation Box bottom-right (p=0.04 on [[144,12,12]])
    ab = data["ablation_p04"]
    bx, by, bw, bh = px + pw - 284, py + ph - 114, 274, 104
    _rounded_rect(ctx, bx, by, bw, bh, 6)
    _set_col(ctx, "#F8FAFC", 0.96)
    ctx.fill_preserve()
    _set_col(ctx, "#94A3B8")
    ctx.set_line_width(1.1)
    ctx.stroke()
    _draw_text(
        ctx,
        f"[[144,12,12]] @ p=4% ({ab['osd2_gain']:.1f}x gain)",
        bx + 10,
        by + 18,
        size=11.4,
        color="#0F172A",
        bold=True,
    )
    bars = [
        ("BP only", ab["bp_only"], "#EF4444"),
        ("BP+OSD0", ab["bp_osd0"], "#F59E0B"),
        ("BP+OSD2", ab["bp_osd2"], "#2563EB"),
    ]
    bmax = max(ab["bp_only"], 0.01)
    for bi, (blbl, bval, bcol) in enumerate(bars):
        ry = by + 34 + bi * 22
        _draw_text(ctx, blbl, bx + 10, ry + 11, size=11.0, color="#334155", bold=(bi == 2))
        bar_w = max(4.0, (bval / bmax) * 116.0)
        _set_col(ctx, bcol)
        ctx.rectangle(bx + 76, ry + 1, bar_w, 13)
        ctx.fill()
        _draw_text(ctx, f"{bval*100:.2f}%", bx + 76 + bar_w + 6, ry + 11, size=11.0, color="#0F172A", bold=(bi == 2))

    _draw_text(ctx, "Physical Bit-Flip Error Rate p", px + pw / 2, py + ph + 44, size=13.5, color="#334155", bold=True, align="center")
    _draw_rotated_text(ctx, "Block Logical Error Rate p_L (log)", x + 24, py + ph / 2)


def _panel_b_circuit_dem(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(B) 3D Circuit-Level DEM & Silicon Regimes", "R=4 Bravyi Depth-7")
    px, py, pw, ph = x + 84, y + 62, w - 114, h - 130

    p_grid = data["p_grid"]
    xmin, xmax = 0.0015, 0.0105
    ymin_log, ymax_log = -5.0, -0.3  # 1e-5 to 0.5

    def tx(v: float) -> float:
        return px + (v - xmin) / (xmax - xmin) * pw

    def ty(v: float) -> float:
        lv = math.log10(max(v, 10 ** ymin_log))
        return py + (ymax_log - lv) / (ymax_log - ymin_log) * ph

    for exp_y in (-5, -4, -3, -2, -1):
        gy = ty(10 ** exp_y)
        _set_col(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        _draw_text(ctx, f"1e{exp_y}", px - 8, gy + 4, size=12.0, color="#475569", align="right")

    for xv in (0.002, 0.004, 0.006, 0.008, 0.010):
        gx = tx(xv)
        _set_col(ctx, "#F1F5F9")
        ctx.set_line_width(1.0)
        ctx.move_to(gx, py)
        ctx.line_to(gx, py + ph)
        ctx.stroke()
        _draw_text(ctx, f"{xv*100:.1f}%", gx, py + ph + 20, size=12.0, color="#475569", align="center")

    _set_col(ctx, "#64748B")
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

    # Threshold vertical line
    p_th = data.get("p_th")
    if p_th:
        gx_th = tx(p_th)
        ctx.save()
        ctx.set_dash([6, 4])
        _set_col(ctx, "#DC2626", 0.75)
        ctx.set_line_width(1.8)
        ctx.move_to(gx_th, py)
        ctx.line_to(gx_th, py + ph)
        ctx.stroke()
        ctx.restore()
        _draw_text(ctx, f"p_th = {p_th*100:.2f}%", gx_th + 5, py + 18, size=12.0, color="#B91C1C", bold=True)

    # Exp138 d=7 Surface Code reference line at D3 (5.0e-4)
    sc_d7 = data["exp138_sc_anchors"]["D3_p2q_0p50_d7_eps_round"]
    gy_sc = ty(sc_d7)
    ctx.save()
    ctx.set_dash([3, 3])
    _set_col(ctx, "#7C3AED", 0.8)
    ctx.set_line_width(1.6)
    ctx.move_to(px, gy_sc)
    ctx.line_to(px + pw, gy_sc)
    ctx.stroke()
    ctx.restore()
    _draw_text(ctx, f"Exp138 SC d=7 @ D3 ({sc_d7:.1e}, 97 cells/L)", px + pw - 8, gy_sc - 6, size=11.0, color="#6D28D9", bold=True, align="right")

    # Uniform circuit curves (block per-round)
    curves = [
        ("BB_72_12_6_pL_rnd", "[[72,12,6]] unif (Z)", "#D97706", [5, 3], "square"),
        ("BB_90_8_10_pL_rnd", "[[90,8,10]] unif (Z)", "#0D9488", [3, 3], "triangle"),
        ("BB_144_12_12_pL_rnd", "[[144,12,12]] unif (Z)", "#2563EB", [], "circle"),
    ]
    for ckey, clbl, col, dash, shp in curves:
        vals = data[ckey]
        pts = [(tx(pv), ty(vv)) for pv, vv in zip(p_grid, vals) if vv > 0]
        ctx.save()
        if dash:
            ctx.set_dash(dash)
        _set_col(ctx, col)
        ctx.set_line_width(2.6 if not dash else 2.0)
        for i, (cx, cy) in enumerate(pts):
            if i == 0:
                ctx.move_to(cx, cy)
            else:
                ctx.line_to(cx, cy)
        ctx.stroke()
        ctx.restore()
        for cx, cy in pts:
            _draw_marker(ctx, cx, cy, shp, 4.8, col)

    # Silicon machine markers on [[144,12,12]] (Z+X combined per-logical 1L!)
    mp = data["machine_points"]
    mach_plot = [
        ("D2_Exp138_p0p92_depol", "D2 (0.92%)", "#DC2626", -8, -14),
        ("D3_Exp138_p0p50_RO2us_depol", "D3 depol (4.6e-4)", "#059669", 10, 17),
        ("D3_Exp138_p0p50_RO2us_P4biased", "D3 P4 (2.0e-4)", "#0D9488", 10, 14),
        ("D3plus_p0p30_RO3us_depol", "D3+ (0.30%)", "#047857", 10, -8),
    ]
    for mk, mlbl, mcol, dx, dy in mach_plot:
        if mk not in mp:
            continue
        p2 = mp[mk]["p_2q"]
        val_1L = mp[mk]["p_L_round_per_logical"]
        if val_1L <= 0:
            # Plot upper 95% floor marker near bottom
            val_1L = 1.5e-5
            mlbl = mlbl + " (<2e-5)"
        mx, my = tx(p2), ty(val_1L)
        _draw_marker(ctx, mx, my, "star", 7.0, mcol, "#0F172A")
        al = "right" if dx < 0 else "left"
        _draw_text(ctx, mlbl, mx + dx, my + dy, size=11.5, color=mcol, bold=True, align=al)

    # Legend top-left
    lx, ly = px + 10, py + 10
    _rounded_rect(ctx, lx, ly, 232, 92, 6)
    _set_col(ctx, "#FFFFFF", 0.94)
    ctx.fill_preserve()
    _set_col(ctx, "#CBD5E1")
    ctx.set_line_width(1.0)
    ctx.stroke()
    for i, (_, clbl, col, dash, shp) in enumerate(curves):
        ry = ly + 18 + i * 20
        ctx.save()
        if dash:
            ctx.set_dash(dash)
        _set_col(ctx, col)
        ctx.set_line_width(2.2)
        ctx.move_to(lx + 10, ry)
        ctx.line_to(lx + 30, ry)
        ctx.stroke()
        ctx.restore()
        _draw_marker(ctx, lx + 20, ry, shp, 3.8, col)
        _draw_text(ctx, clbl, lx + 38, ry + 4, size=11.2, color="#0F172A", bold=(i == 2))
    # Star legend entry
    ry_s = ly + 18 + 3 * 20
    _draw_marker(ctx, lx + 20, ry_s, "star", 5.5, "#059669", "#0F172A")
    _draw_text(ctx, "Si Machine 1L (Z+X, 24c/L)", lx + 38, ry_s + 4, size=11.2, color="#065F46", bold=True)

    _draw_text(ctx, "Two-Qubit Gate Error Rate p (or p_2q)", px + pw / 2, py + ph + 44, size=13.5, color="#334155", bold=True, align="center")
    _draw_rotated_text(ctx, "Logical Error / Round p_L,rnd (log)", x + 24, py + ph / 2)


def _panel_c_m4_layout(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(C) [[144,12,12]] Thickness-2 M4 Layout (20 um)", "24x12 Folded Torus")
    px, py, pw, ph = x + 46, y + 62, w - 72, h - 148

    dw = data["die_width_um"]
    dh = data["die_height_um"]
    # Keep 2:1 aspect ratio cleanly centered
    scale = min(pw / (dw + 16.0), ph / (dh + 16.0))
    ox = px + (pw - (dw - 20.0) * scale) / 2.0
    oy = py + (ph - (dh - 20.0) * scale) / 2.0

    coords = data["coords_folded_um"]

    def pt(qid: int) -> Tuple[float, float]:
        cx, cy, _ = coords[str(qid)]
        return ox + cx * scale, oy + cy * scale

    # Subtle die background plate
    _rounded_rect(ctx, ox - 14, oy - 14, (dw - 20.0) * scale + 28, (dh - 20.0) * scale + 28, 8)
    _set_col(ctx, "#F8FAFC")
    ctx.fill_preserve()
    _set_col(ctx, "#94A3B8")
    ctx.set_line_width(1.2)
    ctx.stroke()

    # Layer 1: All 576 local planar grid edges
    _set_col(ctx, "#64748B", 0.30)
    ctx.set_line_width(1.0)
    for u, v in data["layer1_edges"]:
        x1, y1 = pt(u)
        x2, y2 = pt(v)
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
    ctx.stroke()

    # Layer 2: Long-range M4 buses (draw representative subset cleanly + highlight longest 268.3 um bus!)
    best_e = None
    best_len = -1.0
    l2_edges = data["layer2_edges"]
    for u, v in l2_edges:
        x1, y1, _ = coords[str(u)]
        x2, y2, _ = coords[str(v)]
        d_um = math.hypot(x2 - x1, y2 - y1)
        if d_um > best_len:
            best_len = d_um
            best_e = (u, v)

    # Draw every 6th L2 edge as curved arc in translucent rose so thickness-2 topology is legible without clutter
    _set_col(ctx, "#E11D48", 0.38)
    ctx.set_line_width(1.3)
    for idx, (u, v) in enumerate(l2_edges):
        if idx % 6 != 0:
            continue
        x1, y1 = pt(u)
        x2, y2 = pt(v)
        mx, my = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
        nx, ny = -(y2 - y1) * 0.14, (x2 - x1) * 0.14
        ctx.move_to(x1, y1)
        ctx.curve_to(mx + nx, my + ny, mx + nx, my + ny, x2, y2)
    ctx.stroke()

    # Highlight max-length L2 bus in bold crimson
    if best_e is not None:
        x1, y1 = pt(best_e[0])
        x2, y2 = pt(best_e[1])
        mx, my = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
        nx, ny = -(y2 - y1) * 0.18, (x2 - x1) * 0.18
        _set_col(ctx, "#BE123C", 0.95)
        ctx.set_line_width(3.0)
        ctx.move_to(x1, y1)
        ctx.curve_to(mx + nx, my + ny, mx + nx, my + ny, x2, y2)
        ctx.stroke()

    # Draw all 288 qubit cells color-coded by sublattice
    q_cols = {"L": "#2563EB", "R": "#0891B2", "X": "#16A34A", "Z": "#D97706"}
    for q_str, (cx, cy, qt) in coords.items():
        qx, qy = ox + cx * scale, oy + cy * scale
        ctx.arc(qx, qy, 4.2, 0, 2 * math.pi)
        _set_col(ctx, q_cols[qt])
        ctx.fill()

    # Dimension arrows
    dim_y = oy + (dh - 20.0) * scale + 28
    _set_col(ctx, "#334155")
    ctx.set_line_width(1.2)
    ctx.move_to(ox, dim_y)
    ctx.line_to(ox + (dw - 20.0) * scale, dim_y)
    ctx.stroke()
    _draw_text(ctx, f"480 um (24 cols @ 20 um)", ox + (dw - 20.0) * scale / 2, dim_y + 16, size=12.0, color="#334155", bold=True, align="center")
    _draw_rotated_text(ctx, "240 um (12 rows)", ox - 28, oy + (dh - 20.0) * scale / 2, size=12.0, color="#334155", bold=True)

    # Bottom Legend + Summary Box
    ly = y + h - 72
    _rounded_rect(ctx, x + 18, ly, w - 36, 58, 6)
    _set_col(ctx, "#F8FAFC")
    ctx.fill_preserve()
    _set_col(ctx, "#CBD5E1")
    ctx.set_line_width(1.0)
    ctx.stroke()

    leg_items = [
        ("L-Data (72)", "#2563EB"),
        ("R-Data (72)", "#0891B2"),
        ("X-Anc (72)", "#16A34A"),
        ("Z-Anc (72)", "#D97706"),
        ("L2 M4 Bus (288)", "#BE123C"),
    ]
    for i, (lt, lc) in enumerate(leg_items):
        ix = x + 32 + i * 138
        ctx.arc(ix, ly + 18, 5.0, 0, 2 * math.pi)
        _set_col(ctx, lc)
        ctx.fill()
        _draw_text(ctx, lt, ix + 10, ly + 22, size=11.5, color="#0F172A", bold=True)

    _draw_text(
        ctx,
        f"Die: 480x240 um (0.115 mm2) | L1=576 local | L2=288 long-range | L_max = {data['L_max_um']:.1f} um <= 300 um (0 redesign!)",
        x + w / 2,
        ly + 45,
        size=11.8,
        color="#047857",
        bold=True,
        align="center",
    )


def _panel_d_pitch_resonator(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(D) M4 Resonator Length & L_sq vs Cell Pitch", "Exp131 3 kOhm NbTiN")
    px, py, pw, ph = x + 78, y + 62, w - 154, h - 130

    pitches = data["pitches_um"]
    lmax = data["L_max_um"]
    l1max = data["L1_max_um"]
    lsq = data["Lsq_req_pH"]

    xmin, xmax = 17.0, 53.0
    y1min, y1max = 0.0, 750.0
    y2min, y2max = 0.0, 120.0

    def tx(v: float) -> float:
        return px + (v - xmin) / (xmax - xmin) * pw

    def ty1(v: float) -> float:
        return py + (y1max - v) / (y1max - y1min) * ph

    def ty2(v: float) -> float:
        return py + (y2max - v) / (y2max - y2min) * ph

    # Green shaded zero-redesign zone (L <= 300 um)
    _set_col(ctx, "#DCFCE7", 0.55)
    ctx.rectangle(px, ty1(300.0), pw, ty1(0.0) - ty1(300.0))
    ctx.fill()

    # Grid & left ticks
    for yv in (0, 150, 300, 450, 600, 750):
        gy = ty1(yv)
        _set_col(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        _draw_text(ctx, f"{yv}", px - 8, gy + 4, size=12.0, color="#1D4ED8", align="right")

    # Right ticks (L_sq pH/sq)
    for yv in (0, 30, 60, 90, 120):
        gy = ty2(yv)
        _draw_text(ctx, f"{yv}", px + pw + 8, gy + 4, size=12.0, color="#BE123C", align="left")

    for pv in pitches:
        gx = tx(pv)
        _draw_text(ctx, f"{int(pv)}", gx, py + ph + 20, size=12.0, color="#475569", align="center")

    _set_col(ctx, "#64748B")
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

    # 300 um and 500 um limits (right-aligned in open space -> zero overlap with curves!)
    for lim, lcol, ltxt in ((300.0, "#15803D", "300 um Exp131 lambda/2 @ 5 GHz"), (500.0, "#D97706", "500 um Extended Bus Ceiling")):
        gy = ty1(lim)
        ctx.save()
        ctx.set_dash([6, 4])
        _set_col(ctx, lcol)
        ctx.set_line_width(1.8)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        ctx.restore()
        _draw_text(ctx, ltxt, px + pw - 8, gy - 6, size=11.5, color=lcol, bold=True, align="right")

    # Plot L_max (blue), L1_max (slate dashed), and L_sq_req (crimson right-axis)
    _set_col(ctx, "#2563EB")
    ctx.set_line_width(2.8)
    for i, (pv, lv) in enumerate(zip(pitches, lmax)):
        if i == 0:
            ctx.move_to(tx(pv), ty1(lv))
        else:
            ctx.line_to(tx(pv), ty1(lv))
    ctx.stroke()
    for pv, lv in zip(pitches, lmax):
        _draw_marker(ctx, tx(pv), ty1(lv), "circle", 5.5, "#2563EB")
    _draw_text(ctx, "268 um", tx(20.0) + 10, ty1(268.3) + 16, size=11.5, color="#1D4ED8", bold=True)

    ctx.save()
    ctx.set_dash([4, 3])
    _set_col(ctx, "#64748B")
    ctx.set_line_width(2.0)
    for i, (pv, lv) in enumerate(zip(pitches, l1max)):
        if i == 0:
            ctx.move_to(tx(pv), ty1(lv))
        else:
            ctx.line_to(tx(pv), ty1(lv))
    ctx.stroke()
    ctx.restore()

    _set_col(ctx, "#BE123C")
    ctx.set_line_width(2.4)
    for i, (pv, qv) in enumerate(zip(pitches, lsq)):
        if i == 0:
            ctx.move_to(tx(pv), ty2(qv))
        else:
            ctx.line_to(tx(pv), ty2(qv))
    ctx.stroke()
    for pv, qv in zip(pitches, lsq):
        _draw_marker(ctx, tx(pv), ty2(qv), "diamond", 5.2, "#BE123C")

    # Legend top-left
    lx, ly = px + 12, py + 12
    _rounded_rect(ctx, lx, ly, 232, 70, 6)
    _set_col(ctx, "#FFFFFF", 0.94)
    ctx.fill_preserve()
    _set_col(ctx, "#CBD5E1")
    ctx.set_line_width(1.0)
    ctx.stroke()
    items = [
        ("L_max (L2 M4 Bus, um)", "#2563EB", "circle", []),
        ("L1_max (Local Grid, um)", "#64748B", None, [4, 3]),
        ("L_sq for 5 GHz (pH/sq, R)", "#BE123C", "diamond", []),
    ]
    for i, (tl, tc, ts, td) in enumerate(items):
        ry = ly + 17 + i * 20
        ctx.save()
        if td:
            ctx.set_dash(td)
        _set_col(ctx, tc)
        ctx.set_line_width(2.2)
        ctx.move_to(lx + 10, ry)
        ctx.line_to(lx + 30, ry)
        ctx.stroke()
        ctx.restore()
        if ts:
            _draw_marker(ctx, lx + 20, ry, ts, 4.0, tc)
        _draw_text(ctx, tl, lx + 38, ry + 4, size=11.0, color="#0F172A", bold=(i != 1))

    _draw_text(ctx, "Physical Qubit Cell Pitch P_cell (um)", px + pw / 2, py + ph + 44, size=13.5, color="#334155", bold=True, align="center")
    _draw_rotated_text(ctx, "Max Resonator Length L_max (um)", x + 22, py + ph / 2, color="#1D4ED8")
    _draw_rotated_text(ctx, "Required NbTiN L_sq for 5 GHz (pH/sq)", x + w - 18, py + ph / 2, angle_rad=math.pi / 2, color="#BE123C")


def _panel_e_defect_yield(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(E) Defect-Free 288-Cell Block & 120L Die Yield", "Exp136 Stark vs No-Stark")
    px, py, pw, ph = x + 78, y + 62, w - 108, h - 130

    ns = data["N_cand_grid"]
    f10 = data["f10_block_pct"]
    f15 = data["f15_block_pct"]
    f15_10 = data["f15_10blk_cryo_pct"]

    xmin, xmax = 3.7, 10.3
    ymin, ymax = -2.0, 106.0

    def tx(v: float) -> float:
        return px + (v - xmin) / (xmax - xmin) * pw

    def ty(v: float) -> float:
        return py + (ymax - v) / (ymax - ymin) * ph

    for yv in (0, 20, 40, 60, 80, 100):
        gy = ty(yv)
        _set_col(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        _draw_text(ctx, f"{yv}%", px - 8, gy + 4, size=12.0, color="#475569", align="right")

    for nv in ns:
        gx = tx(nv)
        _set_col(ctx, "#F1F5F9")
        ctx.set_line_width(1.0)
        ctx.move_to(gx, py)
        ctx.line_to(gx, py + ph)
        ctx.stroke()
        _draw_text(ctx, f"{nv}", gx, py + ph + 20, size=12.0, color="#475569", align="center")

    _set_col(ctx, "#64748B")
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

    # 95% target dashed line
    gy95 = ty(95.0)
    ctx.save()
    ctx.set_dash([5, 4])
    _set_col(ctx, "#94A3B8")
    ctx.set_line_width(1.2)
    ctx.move_to(px, gy95)
    ctx.line_to(px + pw, gy95)
    ctx.stroke()
    ctx.restore()

    curves = [
        (f10, "f=1.0% No-Stark (288-cell block)", "#DC2626", [6, 4], "square"),
        (f15, "f*=1.5%+2MV/m (288-cell block)", "#16A34A", [], "circle"),
        (f15_10, "f*=1.5%+2MV/m (10-blk = 120L die)", "#1E3A8A", [], "triangle"),
    ]
    for vals, lbl, col, dash, shp in curves:
        ctx.save()
        if dash:
            ctx.set_dash(dash)
        _set_col(ctx, col)
        ctx.set_line_width(2.7)
        for i, (nv, yv) in enumerate(zip(ns, vals)):
            if i == 0:
                ctx.move_to(tx(nv), ty(yv))
            else:
                ctx.line_to(tx(nv), ty(yv))
        ctx.stroke()
        ctx.restore()
        for nv, yv in zip(ns, vals):
            _draw_marker(ctx, tx(nv), ty(yv), shp, 5.2, col)

    # Key callout annotations (placed in open space with zero overlap!)
    _draw_text(ctx, "2.2% (collapse!)", tx(6.0), ty(f10[2]) + 16, size=11.2, color="#B91C1C", bold=True, align="center")
    _draw_text(ctx, "94.1%", tx(6.0) - 10, ty(f15[2]) - 8, size=11.4, color="#15803D", bold=True, align="right")
    _draw_text(ctx, "99.64% blk", tx(7.85), ty(f15[4]) - 11, size=11.4, color="#15803D", bold=True, align="right")
    _draw_text(ctx, "96.4% 10-blk", tx(8.05), ty(f15_10[4]) + 19, size=11.4, color="#1E3A8A", bold=True)

    # Star for 9-of-10 spared die at N=8 with clean leader arrow to open white space below
    sp_y = data["f15_9of10_spared_N8_pct"]
    sx, sy = tx(8.0), ty(sp_y)
    _draw_marker(ctx, sx, sy, "star", 6.5, "#7C3AED", "#FFFFFF")
    lbl_x, lbl_y = tx(8.35), ty(78.0)
    _set_col(ctx, "#7C3AED", 0.75)
    ctx.set_line_width(1.2)
    ctx.move_to(sx + 4, sy + 7)
    ctx.line_to(lbl_x, lbl_y - 12)
    ctx.stroke()
    _draw_text(ctx, f"9/10 spared (N=8): {sp_y:.2f}%", lbl_x, lbl_y, size=11.2, color="#6D28D9", bold=True, align="center")

    # Legend middle-right (open white space around y=25..62, x=7..10)
    lx, ly = px + pw - 270, py + ph - 108
    _rounded_rect(ctx, lx, ly, 258, 76, 6)
    _set_col(ctx, "#FFFFFF", 0.94)
    ctx.fill_preserve()
    _set_col(ctx, "#CBD5E1")
    ctx.set_line_width(1.0)
    ctx.stroke()
    for i, (_, lbl, col, dash, shp) in enumerate(curves):
        ry = ly + 18 + i * 21
        ctx.save()
        if dash:
            ctx.set_dash(dash)
        _set_col(ctx, col)
        ctx.set_line_width(2.2)
        ctx.move_to(lx + 10, ry)
        ctx.line_to(lx + 30, ry)
        ctx.stroke()
        ctx.restore()
        _draw_marker(ctx, lx + 20, ry, shp, 4.0, col)
        _draw_text(ctx, lbl, lx + 38, ry + 4, size=10.8, color="#0F172A", bold=(i != 0))

    _draw_text(ctx, "Candidate Donor Sites per Cell (N_cand)", px + pw / 2, py + ph + 44, size=13.5, color="#334155", bold=True, align="center")
    _draw_rotated_text(ctx, "Defect-Free Yield (%)", x + 24, py + ph / 2)


def _panel_f_cryo_tco(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(F) 100L Cryostat Fleet & $/L_sys Compression", "Exp140 MXC + Exp141 TCO")
    px, py, pw, ph = x + 76, y + 66, w - 104, h - 144

    labels = data["labels"]
    cryos = data["cryostats_100L"]
    costs_M = data["usd_per_L_sys_M"]
    comp = data["compression_ratios"]
    n_cat = len(labels)

    # Dual log scale normalized neatly:
    # Left bar (Indigo): Cryostats in [0.5 .. 1500] (log10: -0.3 .. 3.2)
    # Right bar (Emerald): $/L_sys in $k [20 .. 30,000] ($0.02M .. $30M, log10: 1.3 .. 4.5)
    c_min, c_max = -0.35, 3.25
    d_min, d_max = 1.15, 4.55  # in $k (so 10^1.15=$14k, 10^4.55=$35.5M)

    def ty_c(v: float) -> float:
        lv = math.log10(max(v, 0.5))
        return py + (c_max - lv) / (c_max - c_min) * ph

    def ty_d(v_M: float) -> float:
        lv = math.log10(max(v_M * 1000.0, 15.0))
        return py + (d_max - lv) / (d_max - d_min) * ph

    # Horizontal gridlines keyed to cryostat powers of 10
    for cv in (1, 10, 100, 1000):
        gy = ty_c(cv)
        _set_col(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        _draw_text(ctx, f"{cv}", px - 8, gy + 4, size=12.0, color="#4338CA", align="right")

    _set_col(ctx, "#64748B")
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

    slot_w = pw / n_cat
    bar_w = slot_w * 0.34
    base_y = py + ph

    for i in range(n_cat):
        cx = px + (i + 0.5) * slot_w
        # Left bar: Cryostats
        y_top_c = ty_c(cryos[i])
        _set_col(ctx, "#4F46E5")
        ctx.rectangle(cx - bar_w - 2, y_top_c, bar_w, base_y - y_top_c)
        ctx.fill()
        _draw_text(ctx, f"{cryos[i]}", cx - bar_w / 2 - 2, y_top_c - 6, size=11.5, color="#312E81", bold=True, align="center")

        # Right bar: $/L_sys ($M or $k)
        y_top_d = ty_d(costs_M[i])
        _set_col(ctx, "#059669")
        ctx.rectangle(cx + 2, y_top_d, bar_w, base_y - y_top_d)
        ctx.fill()
        clbl = f"${costs_M[i]:.2f}M" if costs_M[i] >= 1.0 else f"${costs_M[i]*1000:.0f}k"
        _draw_text(ctx, clbl, cx + bar_w / 2 + 2, y_top_d - 6, size=11.0, color="#065F46", bold=True, align="center")

        # Multi-line x-axis category label
        parts = labels[i].split("\n")
        for pi, pt_txt in enumerate(parts):
            _draw_text(ctx, pt_txt, cx, base_y + 18 + pi * 15, size=11.2, color="#0F172A", bold=(i == n_cat - 1), align="center")

    # Highlight box around BB-144 bar group
    cx_last = px + (n_cat - 0.5) * slot_w
    ctx.save()
    ctx.set_dash([4, 3])
    _set_col(ctx, "#059669")
    ctx.set_line_width(1.6)
    ctx.rectangle(cx_last - slot_w * 0.44, py + 4, slot_w * 0.88, ph - 8)
    ctx.stroke()
    ctx.restore()

    # Legend + Compression Callout top-right (generous width -> zero clipping!)
    bx, by, bw, bh = px + pw - 322, py + 10, 312, 86
    _rounded_rect(ctx, bx, by, bw, bh, 6)
    _set_col(ctx, "#ECFDF5", 0.96)
    ctx.fill_preserve()
    _set_col(ctx, "#10B981")
    ctx.set_line_width(1.3)
    ctx.stroke()

    _set_col(ctx, "#4F46E5")
    ctx.rectangle(bx + 12, by + 12, 14, 11)
    ctx.fill()
    _draw_text(ctx, "Cryostats (100L)", bx + 32, by + 22, size=11.0, color="#1E1B4B", bold=True)

    _set_col(ctx, "#059669")
    ctx.rectangle(bx + 162, by + 12, 14, 11)
    ctx.fill()
    _draw_text(ctx, "$/L_sys (5-yr)", bx + 182, by + 22, size=11.0, color="#065F46", bold=True)

    _draw_text(
        ctx,
        f"vs SC D3 (1e-9): {comp['cryostats_vs_D3_1e-9']:.0f}x Cryo | {comp['usd_per_L_sys_vs_D3_1e-9']:.1f}x $/L_sys",
        bx + 12,
        by + 48,
        size=11.0,
        color="#064E3B",
        bold=True,
    )
    _draw_text(
        ctx,
        f"vs SC D2 (1e-9): {comp['cryostats_vs_D2_1e-9']:.0f}x Cryo | {comp['usd_per_L_sys_vs_D2_1e-9']:.0f}x $/L_sys",
        bx + 12,
        by + 70,
        size=11.0,
        color="#064E3B",
        bold=True,
    )

    _draw_rotated_text(ctx, "Cryostats (log) / Deployed $/L_sys (log)", x + 22, py + ph / 2, color="#312E81")


def main() -> None:
    data = json.loads(PLOT_JSON.read_text())
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)

    # Background
    _set_col(ctx, "#F8FAFC")
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Header Banner
    _set_col(ctx, "#0F172A")
    ctx.rectangle(0, 0, W, 86)
    ctx.fill()
    _draw_text(
        ctx,
        "Exp144 (H162): qLDPC Bivariate Bicycle [[144,12,12]] Gross Code on 300 um M4 NbTiN Bus",
        44,
        38,
        size=24.0,
        color="#FFFFFF",
        bold=True,
    )
    _draw_text(
        ctx,
        "Exact GF(2) CSS & Depth-7 Schedule | Pure-NumPy BP+OSD-2 3D Circuit DEM | Exp140 MXC Packing & Exp141 100L TCO  [Model / Sayisal-Simulasyon]",
        44,
        66,
        size=14.0,
        color="#CBD5E1",
    )

    # Top-right status badge
    n_p, n_t = data["n_passed"], data["n_total"]
    badge_col = "#059669" if n_p >= 6 else "#D97706"
    _rounded_rect(ctx, W - 310, 18, 266, 50, 8)
    _set_col(ctx, badge_col)
    ctx.fill()
    _draw_text(ctx, f"QL Verdicts: {n_p}/{n_t} PASS", W - 177, 41, size=16.5, color="#FFFFFF", bold=True, align="center")
    _draw_text(ctx, "no_lab_measurement=True | v6.0", W - 177, 59, size=11.0, color="#ECFDF5", align="center")

    # 2x3 Panel Grid
    pw = 748
    ph = 606
    xs = [44, 826, 1608]
    ys = [106, 744]

    _panel_a_code_capacity(ctx, xs[0], ys[0], pw, ph, data["panelA_code_capacity"])
    _panel_b_circuit_dem(ctx, xs[1], ys[0], pw, ph, data["panelB_circuit_dem"])
    _panel_c_m4_layout(ctx, xs[2], ys[0], pw, ph, data["panelC_layout_20um"])
    _panel_d_pitch_resonator(ctx, xs[0], ys[1], pw, ph, data["panelD_pitch_resonator"])
    _panel_e_defect_yield(ctx, xs[1], ys[1], pw, ph, data["panelE_defect_yield"])
    _panel_f_cryo_tco(ctx, xs[2], ys[1], pw, ph, data["panelF_cryo_tco"])

    # Footer
    _draw_text(
        ctx,
        "Epistemic Scope: {Model} / {Sayisal-Simulasyon} / {Literatur} / {Varsayim} | Anchors: Bravyi et al. (Nature 2024), Exp131, Exp136, Exp137, Exp138, Exp139, Exp140, Exp141 | Zero lab measurements / supplier quotes.",
        W / 2,
        H - 16,
        size=12.0,
        color="#64748B",
        align="center",
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    surface.write_to_png(str(OUT_PNG))
    print(f"Saved {OUT_PNG.name} ({W}x{H})")


if __name__ == "__main__":
    main()
