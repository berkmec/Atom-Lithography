"""Exp147 Publication Figure Generator (PyCairo, 2400x1400 PNG).

Run with system Python that has pycairo:
  /usr/bin/python3 -B experiments/exp147_universal_qldpc_d18_magic_state/plot_exp147.py

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
RESULTS_DIR = REPO_ROOT / "results" / "exp147_universal_qldpc_d18_magic_state"
PLOT_JSON = RESULTS_DIR / "plot_data_exp147.json"
OUT_PNG = RESULTS_DIR / "fig_exp147_universal_qldpc_magic.png"

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
    size: float = 13.5,
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
    size: float = 13.0,
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

    _draw_text(ctx, title, x + 14, y + 25, size=14.6, color="#0F172A", bold=True)
    _draw_text(ctx, tag, x + w - 14, y + 24, size=11.8, color="#475569", bold=True, align="right")


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
    ctx.set_line_width(1.5)
    ctx.stroke()
    ctx.restore()


# =============================================================================
# Panels A..F
# =============================================================================
def _panel_a_4code_dem(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(A) 4-Code Bravyi 3D Circuit DEM (d=6..18)", "BP+OSD-2 | R=3")
    px, py, pw, ph = x + 84, y + 60, w - 112, h - 128

    p_grid = data["p_grid"]
    xmin, xmax = 0.0037, 0.0083
    ymin_log, ymax_log = -3.8, -0.35

    def tx(v: float) -> float:
        return px + (v - xmin) / (xmax - xmin) * pw

    def ty(v: float) -> float:
        lv = math.log10(max(v, 10 ** ymin_log))
        return py + (ymax_log - lv) / (ymax_log - ymin_log) * ph

    for exp_y in (-3, -2, -1):
        gy = ty(10 ** exp_y)
        _set_col(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        _draw_text(ctx, f"1e{exp_y}", px - 8, gy + 4, size=11.8, color="#475569", align="right")

    for xv in (0.004, 0.005, 0.006, 0.007, 0.008):
        gx = tx(xv)
        _set_col(ctx, "#F1F5F9")
        ctx.set_line_width(1.0)
        ctx.move_to(gx, py)
        ctx.line_to(gx, py + ph)
        ctx.stroke()
        _draw_text(ctx, f"{xv*100:.1f}%", gx, py + ph + 20, size=11.8, color="#475569", align="center")

    _set_col(ctx, "#64748B")
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

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
        _draw_text(ctx, f"p_th = {p_th*100:.2f}%", gx_th - 8, py + 18, size=11.8, color="#B91C1C", bold=True, align="right")

    series = [
        ("BB_72", "[[72,12,6]] (d=6)", "#D97706", [5, 3], "square"),
        ("BB_90", "[[90,8,10]] (d=10)", "#0D9488", [3, 3], "triangle"),
        ("BB_144", "[[144,12,12]] (d=12)", "#2563EB", [], "circle"),
        ("BB_288", "[[288,12,18]] (d=18)", "#BE123C", [], "diamond"),
    ]
    for skey, slbl, col, dash, shp in series:
        vals = data[skey]
        pts = [(tx(pv), ty(vv)) for pv, vv in zip(p_grid, vals) if vv > 0]
        ctx.save()
        if dash:
            ctx.set_dash(dash)
        _set_col(ctx, col)
        ctx.set_line_width(3.0 if skey == "BB_288" else 2.2)
        for i, (cx, cy) in enumerate(pts):
            if i == 0:
                ctx.move_to(cx, cy)
            else:
                ctx.line_to(cx, cy)
        ctx.stroke()
        ctx.restore()
        for cx, cy in pts:
            _draw_marker(ctx, cx, cy, shp, 5.4 if skey == "BB_288" else 4.6, col)

    # Legend top-left
    lx, ly = px + 12, py + 12
    _rounded_rect(ctx, lx, ly, 214, 92, 6)
    _set_col(ctx, "#FFFFFF", 0.94)
    ctx.fill_preserve()
    _set_col(ctx, "#CBD5E1")
    ctx.set_line_width(1.0)
    ctx.stroke()
    for i, (_, slbl, col, dash, shp) in enumerate(series):
        ry = ly + 17 + i * 20
        ctx.save()
        if dash:
            ctx.set_dash(dash)
        _set_col(ctx, col)
        ctx.set_line_width(2.4)
        ctx.move_to(lx + 10, ry)
        ctx.line_to(lx + 30, ry)
        ctx.stroke()
        ctx.restore()
        _draw_marker(ctx, lx + 20, ry, shp, 4.0, col)
        _draw_text(ctx, slbl, lx + 38, ry + 4, size=11.2, color="#0F172A", bold=(i == 3))

    _draw_text(ctx, "Uniform Circuit Depolarizing Rate p", px + pw / 2, py + ph + 44, size=13.0, color="#334155", bold=True, align="center")
    _draw_rotated_text(ctx, "Block Logical Error / Round p_L,rnd (log)", x + 22, py + ph / 2)


def _panel_b_bb288_1e9(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(B) [[288,12,18]] Silicon D3 Scaling & 1e-9 Boundary", "Exp143 GRAPE Pauli-16")
    px, py, pw, ph = x + 84, y + 60, w - 112, h - 128

    xmin, xmax = 0.0014, 0.0105
    ymin_log, ymax_log = -14.5, -1.0

    def tx(v: float) -> float:
        return px + (v - xmin) / (xmax - xmin) * pw

    def ty(v: float) -> float:
        lv = math.log10(max(v, 10 ** ymin_log))
        return py + (ymax_log - lv) / (ymax_log - ymin_log) * ph

    for exp_y in (-14, -12, -10, -8, -6, -4, -2):
        gy = ty(10 ** exp_y)
        _set_col(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        _draw_text(ctx, f"1e{exp_y}", px - 8, gy + 4, size=11.5, color="#475569", align="right")

    for xv in (0.002, 0.00337, 0.006, 0.008, 0.010):
        gx = tx(xv)
        _set_col(ctx, "#F1F5F9")
        ctx.set_line_width(1.0)
        ctx.move_to(gx, py)
        ctx.line_to(gx, py + ph)
        ctx.stroke()
        lbl = "D3" if abs(xv - 0.00337) < 1e-4 else f"{xv*100:.1f}%"
        _draw_text(ctx, lbl, gx, py + ph + 20, size=11.5, color="#047857" if lbl == "D3" else "#475569", bold=(lbl == "D3"), align="center")

    _set_col(ctx, "#64748B")
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

    # Horizontal 1e-9 and 4.3e-14 target lines
    for yv, col, txt in ((1e-9, "#15803D", "1e-9 / L / round Target"), (4.3e-14, "#7C3AED", "4.3e-14 FeMoco 1% Mem")):
        gy = ty(yv)
        ctx.save()
        ctx.set_dash([5, 4])
        _set_col(ctx, col, 0.85)
        ctx.set_line_width(1.5)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        ctx.restore()
        _draw_text(ctx, txt, px + pw - 8, gy - 5, size=10.8, color=col, bold=True, align="right")

    # Vertical D3 (0.337%) and D3++ (0.20%) reference lines
    for pv, col, txt, al in ((0.003369, "#059669", "Exp143 D3 (0.337%)", "left"), (0.0020, "#2563EB", "D3++ (0.20%)", "left")):
        gx = tx(pv)
        ctx.save()
        ctx.set_dash([3, 3])
        _set_col(ctx, col, 0.7)
        ctx.set_line_width(1.4)
        ctx.move_to(gx, py)
        ctx.line_to(gx, py + ph)
        ctx.stroke()
        ctx.restore()
        _draw_text(ctx, txt, gx + 4, py + (18 if pv > 0.003 else 36), size=10.8, color=col, bold=True, align=al)

    # Plot empirical calibration points + power-law extrapolation curves
    for grid_k, vals_k, fit_k, col, shp, lbl in (
        ("depol_p_grid", "depol_1L", "depol_fit", "#D97706", "square", "Si Depol 2Q"),
        ("grape_p_grid", "grape_1L", "grape_fit", "#2563EB", "circle", "Exp143 GRAPE P16"),
    ):
        p_cal = data[grid_k]
        fit = data[fit_k]
        if fit.get("valid"):
            b0, a0 = fit["eval_fn_params"]
            p_line = [0.0016 + i * (0.0102 - 0.0016) / 60.0 for i in range(61)]
            pts_l = [(tx(pv), ty(math.exp(b0 + a0 * math.log(pv)))) for pv in p_line]
            pts_l = [(cx, cy) for cx, cy in pts_l if px <= cx <= px + pw and py <= cy <= py + ph]
            ctx.save()
            ctx.set_dash([5, 3])
            _set_col(ctx, col, 0.85)
            ctx.set_line_width(2.2)
            for i, (cx, cy) in enumerate(pts_l):
                if i == 0:
                    ctx.move_to(cx, cy)
                else:
                    ctx.line_to(cx, cy)
            ctx.stroke()
            ctx.restore()
        vals = data[vals_k]
        for pv, vv in zip(p_cal, vals):
            if vv > 0 and px <= tx(pv) <= px + pw:
                _draw_marker(ctx, tx(pv), ty(vv), shp, 5.4, col)

    # Legend top-right for Depol vs GRAPE P16
    lx, ly = px + pw - 196, py + 8
    _rounded_rect(ctx, lx, ly, 188, 52, 6)
    _set_col(ctx, "#FFFFFF", 0.94)
    ctx.fill_preserve()
    _set_col(ctx, "#CBD5E1")
    ctx.set_line_width(1.0)
    ctx.stroke()
    for idx, (col, shp, lbl) in enumerate((("#D97706", "square", "Si Depol 2Q (a=7.81)"), ("#2563EB", "circle", "Exp143 GRAPE (a=5.59)"))):
        ry = ly + 17 + idx * 20
        _draw_marker(ctx, lx + 16, ry, shp, 4.2, col)
        _draw_text(ctx, lbl, lx + 28, ry + 4, size=10.5, color="#0F172A", bold=(idx == 1))

    # Summary callout box placed cleanly ABOVE the 4.3e-14 purple line (open white space!)
    gf = data["grape_fit"]
    df = data["depol_fit"]
    if gf.get("valid") and df.get("valid"):
        bx, by, bw, bh = px + pw - 298, py + ph - 162, 288, 78
        _rounded_rect(ctx, bx, by, bw, bh, 6)
        _set_col(ctx, "#F8FAFC", 0.96)
        ctx.fill_preserve()
        _set_col(ctx, "#94A3B8")
        ctx.set_line_width(1.0)
        ctx.stroke()
        _draw_text(ctx, f"Depol: p*(1e-9)={df['p_for_1e-9']*100:.3f}% (d_eff={df['d_eff_circuit']:.1f})", bx + 10, by + 18, size=10.5, color="#B45309", bold=True)
        _draw_text(ctx, f"GRAPE P16: p*(1e-9)={gf['p_for_1e-9']*100:.3f}% (RO-limited)", bx + 10, by + 38, size=10.5, color="#1D4ED8", bold=True)
        _draw_text(ctx, f"@D3 0.337%: {df['pred_at_0p337pct']:.1e} (depol) | {gf['pred_at_0p337pct']:.1e} (P16)", bx + 10, by + 58, size=10.0, color="#334155", bold=True)

    _draw_text(ctx, "Two-Qubit Gate Error Rate p_2q (Silicon Machine)", px + pw / 2, py + ph + 44, size=13.0, color="#334155", bold=True, align="center")
    _draw_rotated_text(ctx, "Per-Logical Error / Round p_L,1L (log)", x + 22, py + ph / 2)


def _panel_c_yield_layout(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(C) 576-Cell Yield & 24x24 M4 Layout Check", "Z_12 Automorphism")
    px, py, pw, ph = x + 78, y + 60, w - 106, h - 128

    ns = data["N_cand"]
    y10 = data["y576_f10"]
    y15 = data["y576_f15"]
    y16 = data["y16of18_f15"]

    xmin, xmax = 5.7, 11.3
    ymin, ymax = -3.0, 107.0

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
        _draw_text(ctx, f"{yv}%", px - 8, gy + 4, size=11.8, color="#475569", align="right")

    for nv in ns:
        gx = tx(nv)
        _set_col(ctx, "#F1F5F9")
        ctx.set_line_width(1.0)
        ctx.move_to(gx, py)
        ctx.line_to(gx, py + ph)
        ctx.stroke()
        _draw_text(ctx, f"{nv}", gx, py + ph + 20, size=11.8, color="#475569", align="center")

    _set_col(ctx, "#64748B")
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

    curves = [
        (y10, "f=1.0% No-Stark (576-cell)", "#DC2626", [6, 4], "square"),
        (y15, "f*=1.5%+2MV/m (576-cell)", "#16A34A", [], "circle"),
        (y16, "FeMoco 16/18 Spared (192L)", "#1E3A8A", [], "triangle"),
    ]
    for vals, lbl, col, dash, shp in curves:
        ctx.save()
        if dash:
            ctx.set_dash(dash)
        _set_col(ctx, col)
        ctx.set_line_width(2.6)
        for i, (nv, yv) in enumerate(zip(ns, vals)):
            if i == 0:
                ctx.move_to(tx(nv), ty(yv))
            else:
                ctx.line_to(tx(nv), ty(yv))
        ctx.stroke()
        ctx.restore()
        for nv, yv in zip(ns, vals):
            _draw_marker(ctx, tx(nv), ty(yv), shp, 5.0, col)

    _draw_text(ctx, "0.05% (collapse!)", tx(6.05), ty(11.0), size=11.0, color="#B91C1C", bold=True)
    _draw_text(ctx, f"N=8: {y15[2]:.2f}%", tx(8.0), ty(y15[2]) - 14, size=11.0, color="#15803D", bold=True, align="center")
    _draw_text(ctx, f"N=9: {y15[3]:.2f}%", tx(9.35), ty(y15[3]) - 14, size=11.0, color="#15803D", bold=True, align="center")

    # Legend middle-left
    lx, ly = px + 10, py + 112
    _rounded_rect(ctx, lx, ly, 232, 74, 6)
    _set_col(ctx, "#FFFFFF", 0.94)
    ctx.fill_preserve()
    _set_col(ctx, "#CBD5E1")
    ctx.set_line_width(1.0)
    ctx.stroke()
    for i, (_, lbl, col, dash, shp) in enumerate(curves):
        ry = ly + 17 + i * 20
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
        _draw_text(ctx, lbl, lx + 38, ry + 4, size=10.8, color="#0F172A", bold=(i != 0))

    # Layout pitch summary pill bottom-right
    bx, by, bw, bh = px + pw - 270, py + ph - 88, 260, 78
    _rounded_rect(ctx, bx, by, bw, bh, 6)
    _set_col(ctx, "#ECFDF5", 0.96)
    ctx.fill_preserve()
    _set_col(ctx, "#10B981")
    ctx.set_line_width(1.2)
    ctx.stroke()
    _draw_text(ctx, "24x24 Folded Torus (b'=5b mod 12)", bx + 10, by + 18, size=10.8, color="#065F46", bold=True)
    _draw_text(ctx, "L1=1,152 (dist=1.0) | L2=576 (x^3,y^3)", bx + 10, by + 37, size=10.5, color="#064E3B")
    _draw_text(ctx, f"P=15um: L_max={data['L_max_um'][0]:.0f}um <= 300um", bx + 10, by + 54, size=10.5, color="#065F46", bold=True)
    _draw_text(ctx, f"P=20um: L_max={data['L_max_um'][2]:.0f}um <= 300um (0 red.)", bx + 10, by + 70, size=10.5, color="#065F46", bold=True)

    _draw_text(ctx, "Candidate Donor Sites per Cell (N_cand)", px + pw / 2, py + ph + 44, size=13.0, color="#334155", bold=True, align="center")
    _draw_rotated_text(ctx, "Defect-Free Yield (%)", x + 22, py + ph / 2)


def _panel_d_factories(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(D) Universal Magic State Factories (p_T <= 1e-10)", "Exp143 D3 vs D3++")
    px, py, pw, ph = x + 76, y + 64, w - 102, h - 144

    labels = data["labels"]
    pts = data["p_T"]
    cryos = data["cryos"]
    rates = data["rate_khz"]
    n_cat = len(labels)

    # Left bar (Indigo): -log10(p_T) in [0 .. 14]; Right bar (Emerald): Cryostats in [0 .. 38]
    y_max_log = 14.0
    y_max_c = 38.0

    def ty_p(p_val: float) -> float:
        v = min(y_max_log, max(0.0, -math.log10(max(p_val, 1e-16))))
        return py + (y_max_log - v) / y_max_log * ph

    def ty_c(c_val: float) -> float:
        v = min(y_max_c, max(0.0, c_val))
        return py + (y_max_c - v) / y_max_c * ph

    for lv in (0, 2, 4, 6, 8, 10, 12, 14):
        gy = py + (y_max_log - lv) / y_max_log * ph
        _set_col(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        _draw_text(ctx, f"1e-{lv}" if lv > 0 else "1", px - 8, gy + 4, size=11.0, color="#3730A3", align="right")

    _set_col(ctx, "#64748B")
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

    # 1e-10 target dashed line (label on LEFT above short 1-Stage bar -> zero bar overlap!)
    gy10 = ty_p(1e-10)
    ctx.save()
    ctx.set_dash([6, 4])
    _set_col(ctx, "#DC2626", 0.85)
    ctx.set_line_width(1.8)
    ctx.move_to(px, gy10)
    ctx.line_to(px + pw, gy10)
    ctx.stroke()
    ctx.restore()
    _draw_text(ctx, "p_T = 1e-10 Target", px + 10, gy10 - 7, size=11.0, color="#B91C1C", bold=True, align="left")

    slot_w = pw / n_cat
    bar_w = slot_w * 0.34
    base_y = py + ph

    for i in range(n_cat):
        cx = px + (i + 0.5) * slot_w
        # Left bar: -log10(p_T)
        yt_p = ty_p(pts[i])
        col_p = "#EF4444" if pts[i] > 1e-10 else "#4F46E5"
        _set_col(ctx, col_p)
        ctx.rectangle(cx - bar_w - 2, yt_p, bar_w, base_y - yt_p)
        ctx.fill()
        _draw_text(ctx, f"{pts[i]:.1e}", cx - bar_w / 2 - 2, yt_p - 6, size=9.8, color=col_p, bold=True, align="center")

        # Right bar: Cryostats
        yt_c = ty_c(cryos[i])
        _set_col(ctx, "#059669")
        ctx.rectangle(cx + 2, yt_c, bar_w, base_y - yt_c)
        ctx.fill()
        _draw_text(ctx, f"{cryos[i]}c", cx + bar_w / 2 + 2, yt_c - 6, size=10.5, color="#065F46", bold=True, align="center")

        # X labels + R_T kHz
        parts = labels[i].split("\n")
        for pi, pt_txt in enumerate(parts):
            _draw_text(ctx, pt_txt, cx, base_y + 17 + pi * 14, size=10.8, color="#0F172A", bold=(i == 3), align="center")
        _draw_text(ctx, f"{rates[i]:.1f} kHz", cx, base_y + 47, size=10.2, color="#047857", bold=True, align="center")

    # Legend top-left
    lx, ly = px + 10, py + 8
    _rounded_rect(ctx, lx, ly, 260, 30, 5)
    _set_col(ctx, "#FFFFFF", 0.94)
    ctx.fill_preserve()
    _set_col(ctx, "#CBD5E1")
    ctx.set_line_width(1.0)
    ctx.stroke()
    _set_col(ctx, "#4F46E5")
    ctx.rectangle(lx + 10, ly + 9, 13, 11)
    ctx.fill()
    _draw_text(ctx, "-log10(p_T)", lx + 28, ly + 19, size=10.8, color="#1E1B4B", bold=True)
    _set_col(ctx, "#059669")
    ctx.rectangle(lx + 126, ly + 9, 13, 11)
    ctx.fill()
    _draw_text(ctx, "LD400 Cryos", lx + 144, ly + 19, size=10.8, color="#065F46", bold=True)

    _draw_rotated_text(ctx, "Output Error p_T (-log10) / Cryostats", x + 22, py + ph / 2, color="#312E81")


def _panel_e_femoco(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(E) FeMoco Catalyst (192L, 1e8 T) Compression", "Exp140 MXC + Exp141 TCO")
    px, py, pw, ph = x + 76, y + 66, w - 102, h - 144

    labels = data["labels"]
    cryos = data["cryos"]
    costs_k = data["cost_per_solve_k"]
    rts = data["runtime_h"]
    comp = data["compression"]
    n_cat = len(labels)

    ymin_log, ymax_log = 0.4, 3.1  # 2.5 to 1250 (covers both cryos 16..593 AND $k 6.5..231!)

    def ty(v: float) -> float:
        lv = math.log10(max(v, 10 ** ymin_log))
        return py + (ymax_log - lv) / (ymax_log - ymin_log) * ph

    for cv in (5, 10, 50, 100, 500, 1000):
        gy = ty(cv)
        _set_col(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        _draw_text(ctx, f"{cv}", px - 8, gy + 4, size=11.5, color="#475569", align="right")

    _set_col(ctx, "#64748B")
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

    slot_w = pw / n_cat
    bar_w = slot_w * 0.32
    base_y = py + ph

    for i in range(n_cat):
        cx = px + (i + 0.5) * slot_w
        yc = ty(cryos[i])
        _set_col(ctx, "#4F46E5")
        ctx.rectangle(cx - bar_w - 3, yc, bar_w, base_y - yc)
        ctx.fill()
        _draw_text(ctx, f"{cryos[i]} cryos", cx - bar_w / 2 - 3, yc - 6, size=11.0, color="#312E81", bold=True, align="center")

        yd = ty(costs_k[i])
        _set_col(ctx, "#059669")
        ctx.rectangle(cx + 3, yd, bar_w, base_y - yd)
        ctx.fill()
        _draw_text(ctx, f"${costs_k[i]:.1f}k", cx + bar_w / 2 + 3, yd - 6, size=11.0, color="#065F46", bold=True, align="center")

        parts = labels[i].split("\n")
        for pi, pt_txt in enumerate(parts):
            _draw_text(ctx, pt_txt, cx, base_y + 18 + pi * 15, size=11.2, color="#0F172A", bold=(i == 2), align="center")
        _draw_text(ctx, f"t = {rts[i]:.1f} h", cx, base_y + 50, size=10.5, color="#475569", bold=True, align="center")

    # Callout top-right
    bx, by, bw, bh = px + pw - 292, py + 10, 282, 82
    _rounded_rect(ctx, bx, by, bw, bh, 6)
    _set_col(ctx, "#ECFDF5", 0.96)
    ctx.fill_preserve()
    _set_col(ctx, "#10B981")
    ctx.set_line_width(1.2)
    ctx.stroke()
    _set_col(ctx, "#4F46E5")
    ctx.rectangle(bx + 12, by + 12, 13, 11)
    ctx.fill()
    _draw_text(ctx, "LD400 Cryos", bx + 30, by + 22, size=10.8, color="#1E1B4B", bold=True)
    _set_col(ctx, "#059669")
    ctx.rectangle(bx + 142, by + 12, 13, 11)
    ctx.fill()
    _draw_text(ctx, "$/Solve ($k)", bx + 160, by + 22, size=10.8, color="#065F46", bold=True)
    _draw_text(ctx, f"Cryostat Compression: {comp['cryostats_x']:.1f}x", bx + 12, by + 46, size=11.4, color="#064E3B", bold=True)
    _draw_text(ctx, f"$/Solve Reduction:    {comp['cost_per_solve_x']:.1f}x", bx + 12, by + 67, size=11.4, color="#064E3B", bold=True)

    _draw_rotated_text(ctx, "LD400 Cryostats / Cost per Solve ($k, log)", x + 22, py + ph / 2, color="#312E81")


def _panel_f_rsa2048(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: Dict[str, Any]) -> None:
    _draw_panel_card(ctx, x, y, w, h, "(F) RSA-2048 Shor (4,096L, 1e10 T) Fleet & Power", "MW-to-Single-Building")
    px, py, pw, ph = x + 76, y + 66, w - 102, h - 144

    labels = data["labels"]
    cryos = data["cryos"]
    powers = data["power_mw"]
    rts = data["runtime_h"]
    comp = data["compression"]
    n_cat = len(labels)

    ymin_log, ymax_log = 0.5, 4.5  # 3.16 to 31,600 (covers power 7.4..384 MW AND cryos 291..15,327!)

    def ty(v: float) -> float:
        lv = math.log10(max(v, 10 ** ymin_log))
        return py + (ymax_log - lv) / (ymax_log - ymin_log) * ph

    for cv in (10, 100, 1000, 10000):
        gy = ty(cv)
        _set_col(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        _draw_text(ctx, f"{cv}", px - 8, gy + 4, size=11.5, color="#475569", align="right")

    _set_col(ctx, "#64748B")
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

    # 10 MW building ceiling line (label cleanly on right above 7.4 MW bar -> zero bar collision!)
    gy10 = ty(10.0)
    ctx.save()
    ctx.set_dash([5, 4])
    _set_col(ctx, "#D97706", 0.85)
    ctx.set_line_width(1.6)
    ctx.move_to(px, gy10)
    ctx.line_to(px + pw, gy10)
    ctx.stroke()
    ctx.restore()
    _draw_text(ctx, "10 MW Limit", px + pw - 10, gy10 - 24, size=10.6, color="#B45309", bold=True, align="right")

    slot_w = pw / n_cat
    bar_w = slot_w * 0.32
    base_y = py + ph

    for i in range(n_cat):
        cx = px + (i + 0.5) * slot_w
        yc = ty(cryos[i])
        _set_col(ctx, "#4F46E5")
        ctx.rectangle(cx - bar_w - 3, yc, bar_w, base_y - yc)
        ctx.fill()
        _draw_text(ctx, f"{cryos[i]:,}", cx - bar_w / 2 - 3, yc - 6, size=10.8, color="#312E81", bold=True, align="center")

        yp = ty(powers[i])
        _set_col(ctx, "#E11D48")
        ctx.rectangle(cx + 3, yp, bar_w, base_y - yp)
        ctx.fill()
        _draw_text(ctx, f"{powers[i]:.1f} MW", cx + bar_w / 2 + 3, yp - 6, size=10.8, color="#9F1239", bold=True, align="center")

        parts = labels[i].split("\n")
        for pi, pt_txt in enumerate(parts):
            _draw_text(ctx, pt_txt, cx, base_y + 18 + pi * 15, size=11.2, color="#0F172A", bold=(i == 2), align="center")
        _draw_text(ctx, f"t = {rts[i]:.1f} h", cx, base_y + 50, size=10.5, color="#475569", bold=True, align="center")

    # Callout top-right
    bx, by, bw, bh = px + pw - 294, py + 10, 284, 82
    _rounded_rect(ctx, bx, by, bw, bh, 6)
    _set_col(ctx, "#FFF1F2", 0.96)
    ctx.fill_preserve()
    _set_col(ctx, "#F43F5E")
    ctx.set_line_width(1.2)
    ctx.stroke()
    _set_col(ctx, "#4F46E5")
    ctx.rectangle(bx + 12, by + 12, 13, 11)
    ctx.fill()
    _draw_text(ctx, "LD400 Cryos", bx + 30, by + 22, size=10.8, color="#1E1B4B", bold=True)
    _set_col(ctx, "#E11D48")
    ctx.rectangle(bx + 142, by + 12, 13, 11)
    ctx.fill()
    _draw_text(ctx, "Power (MW)", bx + 160, by + 22, size=10.8, color="#9F1239", bold=True)
    _draw_text(ctx, f"Cryostat Compression: {comp['cryostats_x']:.1f}x", bx + 12, by + 46, size=11.4, color="#881337", bold=True)
    _draw_text(ctx, f"Power Cut: {comp['power_x']:.1f}x | TCO: {comp['tco_x']:.1f}x", bx + 12, by + 67, size=11.2, color="#881337", bold=True)

    _draw_rotated_text(ctx, "LD400 Cryostats / Facility Power (MW, log)", x + 22, py + ph / 2, color="#312E81")


def main() -> None:
    data = json.loads(PLOT_JSON.read_text())
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)

    _set_col(ctx, "#F8FAFC")
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Header Banner
    _set_col(ctx, "#0F172A")
    ctx.rectangle(0, 0, W, 86)
    ctx.fill()
    _draw_text(
        ctx,
        "Exp147 (H165): Universal [[288,12,18]] d=18 qLDPC + Magic State Factories & Algorithm Budgets",
        44,
        38,
        size=23.0,
        color="#FFFFFF",
        bold=True,
    )
    _draw_text(
        ctx,
        "Exact GF(2) BB-288 & Z_12 Layout | 4-Code 3D BP+OSD-2 DEM | Litinski & Gidney Factories | FeMoco & RSA-2048  [Model / Sayisal-Simulasyon]",
        44,
        66,
        size=13.5,
        color="#CBD5E1",
    )

    n_p, n_t = data["n_passed"], data["n_total"]
    badge_col = "#059669" if n_p >= 6 else "#D97706"
    _rounded_rect(ctx, W - 310, 18, 266, 50, 8)
    _set_col(ctx, badge_col)
    ctx.fill()
    _draw_text(ctx, f"UQ Verdicts: {n_p}/{n_t} PASS", W - 177, 41, size=16.5, color="#FFFFFF", bold=True, align="center")
    _draw_text(ctx, "no_lab_measurement=True | v7.0", W - 177, 59, size=11.0, color="#ECFDF5", align="center")

    pw, ph = 748, 606
    xs = [44, 826, 1608]
    ys = [106, 744]

    _panel_a_4code_dem(ctx, xs[0], ys[0], pw, ph, data["panelA_4code_uniform_dem"])
    _panel_b_bb288_1e9(ctx, xs[1], ys[0], pw, ph, data["panelB_bb288_silicon_1e9"])
    _panel_c_yield_layout(ctx, xs[2], ys[0], pw, ph, data["panelC_layout_24x24"])
    _panel_d_factories(ctx, xs[0], ys[1], pw, ph, data["panelD_magic_factories"])
    _panel_e_femoco(ctx, xs[1], ys[1], pw, ph, data["panelE_femoco"])
    _panel_f_rsa2048(ctx, xs[2], ys[1], pw, ph, data["panelF_rsa2048"])

    _draw_text(
        ctx,
        "Epistemic Scope: {Model} / {Sayisal-Simulasyon} / {Literatur} / {Varsayim} | Anchors: Bravyi (Nature 2024), Litinski (Quantum 2019), Gidney (2021/2024), Exp136..144 | Zero lab quotes.",
        W / 2,
        H - 16,
        size=11.8,
        color="#64748B",
        align="center",
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    surface.write_to_png(str(OUT_PNG))
    print(f"Saved {OUT_PNG.name} ({W}x{H})")


if __name__ == "__main__":
    main()
