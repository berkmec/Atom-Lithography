"""Exp130 PyCairo Plotter (no matplotlib required; runs under /usr/bin/python3 -B).

Generates two 1800x1080 publication-grade PNG figures:
  1. results/exp130_flash_anneal_diffusion/fig_exp130_anneal_window.png
     - 2D (t_pulse, T_peak) process phase diagram with marching-squares contours,
       808 nm fluence/T_back tradeoff curve, and Exp124 Arch-B sigma_tot bar comparison.
  2. results/exp130_flash_anneal_diffusion/fig_exp130_profiles_ted.png
     - 5-panel technical dashboard: (A) 1D Si thermal PDE waveforms, (B) Exp108 UHV anchor
       mass-fate validation, (C) 5 keV 31P depth profiles, (D) 28Si/29Si epitaxial bath
       interface profiles, and (E) Debye cryo cooldown to 20 mK.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Sequence, Tuple

import cairo

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "exp130_flash_anneal_diffusion"
EXP_JSON = RESULTS_DIR / "exp130.json"
PLOT_JSON = RESULTS_DIR / "plot_data_exp130.json"
FIG_WINDOW = RESULTS_DIR / "fig_exp130_anneal_window.png"
FIG_PROFILES = RESULTS_DIR / "fig_exp130_profiles_ted.png"

# Color palette (high-contrast, colorblind-friendly)
BG = (0.985, 0.988, 0.992)
PANEL_BG = (1.0, 1.0, 1.0)
INK = (0.11, 0.14, 0.19)
MUTED = (0.38, 0.43, 0.50)
GRID = (0.87, 0.89, 0.92)
BORDER = (0.25, 0.30, 0.36)

C_EMERALD = (0.06, 0.62, 0.42)
C_TEAL = (0.12, 0.65, 0.72)
C_NAVY = (0.10, 0.25, 0.55)
C_BLUE = (0.15, 0.45, 0.80)
C_AMBER = (0.86, 0.52, 0.08)
C_ORANGE = (0.90, 0.38, 0.10)
C_RED = (0.78, 0.14, 0.18)
C_PURPLE = (0.50, 0.22, 0.68)
C_MAGENTA = (0.75, 0.10, 0.52)
C_SLATE = (0.76, 0.80, 0.86)


def set_font(ctx: cairo.Context, size: float, bold: bool = False) -> None:
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)


def draw_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 14.0,
    bold: bool = False,
    color: Tuple[float, float, float] = INK,
    align: str = "left",
    valign: str = "baseline",
    angle: float = 0.0,
) -> None:
    """Draw single-line text cleanly (never passes newline to Cairo)."""
    clean = text.replace("\n", " ")
    ctx.save()
    set_font(ctx, size, bold)
    ext = ctx.text_extents(clean)
    dx = 0.0
    if align == "center":
        dx = -(ext.width / 2.0 + ext.x_bearing)
    elif align == "right":
        dx = -(ext.width + ext.x_bearing)
    dy = 0.0
    if valign == "middle":
        dy = -(ext.height / 2.0 + ext.y_bearing)
    elif valign == "top":
        dy = -ext.y_bearing
    ctx.translate(x, y)
    if angle != 0.0:
        ctx.rotate(angle)
    ctx.set_source_rgb(*color)
    ctx.move_to(dx, dy)
    ctx.show_text(clean)
    ctx.restore()


def draw_panel_box(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str) -> None:
    ctx.save()
    ctx.set_source_rgb(*PANEL_BG)
    ctx.rectangle(x, y, w, h)
    ctx.fill()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.4)
    ctx.rectangle(x, y, w, h)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, title, x + 6, y - 10, size=15.5, bold=True, color=INK)


def marching_squares_segments(
    xs: Sequence[float], ys: Sequence[float], Z: Sequence[Sequence[float]], level: float
) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """Compute exact linear-interpolated marching-squares contour segments for Z(y, x) == level."""
    ny = len(ys)
    nx = len(xs)
    segs: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

    def interp(x0: float, y0: float, v0: float, x1: float, y1: float, v1: float) -> Tuple[float, float]:
        dv = v1 - v0
        t = 0.5 if abs(dv) < 1e-15 else (level - v0) / dv
        t = max(0.0, min(1.0, t))
        return (x0 + t * (x1 - x0), y0 + t * (y1 - y0))

    for i in range(ny - 1):
        y0, y1 = ys[i], ys[i + 1]
        for j in range(nx - 1):
            x0, x1 = xs[j], xs[j + 1]
            v00 = Z[i][j]
            v10 = Z[i][j + 1]
            v11 = Z[i + 1][j + 1]
            v01 = Z[i + 1][j]
            pts: List[Tuple[float, float]] = []
            if (v00 < level) != (v10 < level):
                pts.append(interp(x0, y0, v00, x1, y0, v10))
            if (v10 < level) != (v11 < level):
                pts.append(interp(x1, y0, v10, x1, y1, v11))
            if (v11 < level) != (v01 < level):
                pts.append(interp(x1, y1, v11, x0, y1, v01))
            if (v01 < level) != (v00 < level):
                pts.append(interp(x0, y1, v01, x0, y0, v00))
            if len(pts) == 2:
                segs.append((pts[0], pts[1]))
            elif len(pts) == 4:
                segs.append((pts[0], pts[1]))
                segs.append((pts[2], pts[3]))
    return segs


def draw_star(ctx: cairo.Context, cx: float, cy: float, r_out: float, r_in: float) -> None:
    pts = []
    for k in range(10):
        ang = -math.pi / 2.0 + k * math.pi / 5.0
        r = r_out if k % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def draw_cross(ctx: cairo.Context, cx: float, cy: float, r: float, color: Tuple[float, float, float]) -> None:
    ctx.save()
    ctx.set_source_rgb(*color)
    ctx.set_line_width(3.0)
    ctx.move_to(cx - r, cy - r)
    ctx.line_to(cx + r, cy + r)
    ctx.move_to(cx - r, cy + r)
    ctx.line_to(cx + r, cy - r)
    ctx.stroke()
    ctx.restore()


# =============================================================================
# FIGURE 1: 2D Phase Diagram + 808 nm Fluence Curve + Exp124 sigma_tot Budget
# =============================================================================
def render_fig_anneal_window(exp: dict, pdata: dict) -> None:
    W, H = 1800, 1080
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG)
    ctx.paint()

    # Header
    draw_text(
        ctx,
        "Exp130 (H148 / Risk R6): 31P Millisecond Flash/Laser Anneal Phase Diagram & Process Window",
        40, 46, size=24, bold=True, color=INK,
    )
    draw_text(
        ctx,
        "Coupled 1D Nonlinear Si Thermal PDE + Non-Equilibrium TED/Kick-Out + Surface Escape + 28Si/29Si Mixing  |  no_lab_measurement=True",
        40, 74, size=14, color=MUTED,
    )

    # -------------------------------------------------------------------------
    # PANEL A (Left): 2D (t_pulse, T_peak) Phase Diagram
    # -------------------------------------------------------------------------
    px, py, pw, ph = 95.0, 128.0, 1010.0, 825.0
    draw_panel_box(ctx, px, py, pw, ph, "A. (t_pulse, T_peak) Process Window — 5 keV 31P+ Single Donor (Rp=6.46 nm, r_casc=2.5 nm)")

    tp_grid = pdata["tp_grid_s"]
    T_grid = pdata["T_grid_K"]
    log_tp = [math.log10(t) for t in tp_grid]
    x_min, x_max = -5.0, math.log10(600.0)  # 10 us .. 600 s
    y_min, y_max = 700.0, 1660.0

    def map_x(lt: float) -> float:
        return px + (lt - x_min) / (x_max - x_min) * pw

    def map_y(T: float) -> float:
        return py + ph - (T - y_min) / (y_max - y_min) * ph

    f_act = pdata["f_act_map"]
    sig_ann = pdata["sigma_ann_map"]
    loss = pdata["loss_map"]
    pass_05 = pdata["pass_05_map"]
    pass_10 = pdata["pass_10_map"]
    # Exact mass conservation (err < 1e-14) -> local SPE activation fraction = 1 - f_inact = f_act_bulk + loss
    spe_act = [[min(1.0, f_act[i][j] + loss[i][j]) for j in range(len(log_tp))] for i in range(len(T_grid))]

    # Cell edges for crisp filled regime map
    x_edges = [log_tp[0] - 0.5 * (log_tp[1] - log_tp[0])]
    for j in range(len(log_tp) - 1):
        x_edges.append(0.5 * (log_tp[j] + log_tp[j + 1]))
    x_edges.append(log_tp[-1] + 0.5 * (log_tp[-1] - log_tp[-2]))

    y_edges = [T_grid[0] - 0.5 * (T_grid[1] - T_grid[0])]
    for i in range(len(T_grid) - 1):
        y_edges.append(0.5 * (T_grid[i] + T_grid[i + 1]))
    y_edges.append(T_grid[-1] + 0.5 * (T_grid[-1] - T_grid[-2]))

    ctx.save()
    ctx.rectangle(px + 1, py + 1, pw - 2, ph - 2)
    ctx.clip()

    for i in range(len(T_grid)):
        y0_c = map_y(y_edges[i + 1])
        y1_c = map_y(y_edges[i])
        for j in range(len(log_tp)):
            x0_c = map_x(x_edges[j])
            x1_c = map_x(x_edges[j + 1])
            T_val = T_grid[i]
            if T_val >= 0.92 * 1687.0:
                col = (0.97, 0.80, 0.81)  # melting risk zone
            elif pass_05[i][j] == 1:
                col = (0.64, 0.91, 0.77)  # strict <= 0.50 nm window
            elif pass_10[i][j] == 1:
                col = (0.80, 0.94, 0.92)  # limit <= 1.00 nm window
            elif spe_act[i][j] < 0.95:
                col = (0.88, 0.91, 0.95)  # true incomplete SPE activation
            else:
                col = (0.98, 0.90, 0.78)  # excess TED diffusion or surface P loss
            ctx.set_source_rgb(*col)
            ctx.rectangle(x0_c - 0.4, y0_c - 0.4, (x1_c - x0_c) + 0.8, (y1_c - y0_c) + 0.8)
            ctx.fill()

    # Subtle gridlines
    ctx.set_source_rgba(0.3, 0.35, 0.42, 0.22)
    ctx.set_line_width(0.8)
    for exp_t in (-5, -4, -3, -2, -1, 0, 1, 2):
        gx = map_x(float(exp_t))
        ctx.move_to(gx, py)
        ctx.line_to(gx, py + ph)
        ctx.stroke()
    for Tv in range(800, 1700, 100):
        gy = map_y(float(Tv))
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()

    # Melting danger band hatching above 0.92*T_melt = 1552 K
    y_melt_lim = map_y(0.92 * 1687.0)
    ctx.set_source_rgba(0.78, 0.14, 0.18, 0.30)
    ctx.set_line_width(1.2)
    for xh in range(int(px) - 120, int(px + pw) + 120, 18):
        ctx.move_to(xh, py)
        ctx.line_to(xh + 95, y_melt_lim)
        ctx.stroke()

    # Horizontal limit line 0.92 * T_melt = 1552 K
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(2.2)
    ctx.set_dash([8.0, 5.0])
    ctx.move_to(px, y_melt_lim)
    ctx.line_to(px + pw, y_melt_lim)
    ctx.stroke()
    ctx.set_dash([])

    # Marching-squares physics contours
    def draw_contour(Z_mat: Sequence[Sequence[float]], lvl: float, col: Tuple[float, float, float], lw: float, dash: List[float] | None = None) -> None:
        segs = marching_squares_segments(log_tp, T_grid, Z_mat, lvl)
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        for (xa, ya), (xb, yb) in segs:
            ctx.move_to(map_x(xa), map_y(ya))
            ctx.line_to(map_x(xb), map_y(yb))
        ctx.stroke()
        ctx.restore()

    draw_contour(spe_act, 0.95, C_NAVY, 2.4)
    draw_contour(sig_ann, 0.50, C_EMERALD, 2.6)
    draw_contour(sig_ann, 1.00, C_AMBER, 2.2, [6.0, 4.0])
    draw_contour(loss, 0.02, C_MAGENTA, 2.1, [4.0, 4.0])

    # Contour annotations (carefully placed in clean open locations)
    draw_text(ctx, "0.92 T_melt = 1552 K (Non-melting ceiling; T_melt = 1687 K)", px + 14, y_melt_lim - 10, size=13, bold=True, color=C_RED)
    draw_text(ctx, "SPE act = 95%", map_x(-4.15), map_y(1510), size=12.5, bold=True, color=C_NAVY)
    draw_text(ctx, "sigma_anneal = 0.50 nm", map_x(-2.45), map_y(1495), size=12.5, bold=True, color=(0.03, 0.42, 0.28))
    draw_text(ctx, "sigma = 1.0 nm", map_x(-1.45), map_y(1318), size=12.2, bold=True, color=C_AMBER)
    draw_text(ctx, "Surface loss = 2%", map_x(0.05), map_y(1235), size=12.2, bold=True, color=C_MAGENTA)

    # Mark operating & conventional points with clean callouts
    # 1. Optimal 808 nm 1.0 ms / 1440 K
    ox, oy = map_x(-3.0), map_y(1440.0)
    ctx.save()
    draw_star(ctx, ox, oy, 13.0, 5.8)
    ctx.set_source_rgb(0.98, 0.78, 0.12)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(1.8)
    ctx.stroke()
    ctx.restore()
    # Callout box for optimal point (dynamically read from exp130.json)
    opt_b = exp["wavelength_and_pulse_benchmarks"]["808nm_diode_1.0ms_1440K"]
    opt_05 = exp["wavelength_and_pulse_benchmarks"]["808nm_diode_0.5ms_1440K"]
    exc_50 = exp["wavelength_and_pulse_benchmarks"]["308nm_excimer_50us_1440K"]
    conv_rta = exp["conventional_anneal_benchmarks"]["rta_1000C_10s"]
    conv_f8 = exp["conventional_anneal_benchmarks"]["furnace_800C_10min"]
    conv_f6 = exp["conventional_anneal_benchmarks"]["furnace_600C_10min"]

    bx, by = map_x(-4.50), map_y(1275.0)
    ctx.save()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(1.6)
    ctx.move_to(bx + 215, by - 4)
    ctx.line_to(ox - 12, oy + 8)
    ctx.stroke()
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
    ctx.rectangle(bx, by - 42, 286, 58)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_EMERALD)
    ctx.set_line_width(2.0)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "OPTIMAL 808 nm ms-FLASH (S5.5)", bx + 8, by - 24, size=12.2, bold=True, color=(0.03, 0.42, 0.28))
    draw_text(ctx, f"1.0 ms | {opt_b['T_peak_K']:.0f} K | {opt_b['fluence_J_per_cm2']:.2f} J/cm2", bx + 8, by - 7, size=11.8, bold=True, color=INK)
    draw_text(ctx, f"act={opt_b['f_act_bulk']*100:.2f}%, sig={opt_b['sigma_anneal_nm']:.3f} nm, loss={opt_b['f_total_surface_loss']*100:.2f}%", bx + 8, by + 9, size=11.1, color=MUTED)

    # 2. Compact 808 nm 0.5 ms / 1440 K (label centered cleanly above diamond)
    cx05, cy05 = map_x(math.log10(0.5e-3)), map_y(1440.0)
    ctx.save()
    ctx.move_to(cx05, cy05 - 8)
    ctx.line_to(cx05 + 8, cy05)
    ctx.line_to(cx05, cy05 + 8)
    ctx.line_to(cx05 - 8, cy05)
    ctx.close_path()
    ctx.set_source_rgb(*C_BLUE)
    ctx.fill_preserve()
    ctx.set_source_rgb(1, 1, 1)
    ctx.set_line_width(1.5)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, f"0.5 ms ({opt_05['fluence_J_per_cm2']:.1f} J/cm2)", cx05, cy05 - 16, size=11.5, bold=True, color=C_BLUE, align="center")

    # 3. 308 nm excimer 50 us / 1440 K (FAIL activation — label placed cleanly to the left)
    ex, ey = map_x(math.log10(50e-6)), map_y(1440.0)
    ctx.save()
    ctx.move_to(ex, ey - 9)
    ctx.line_to(ex + 8, ey + 7)
    ctx.line_to(ex - 8, ey + 7)
    ctx.close_path()
    ctx.set_source_rgb(*C_PURPLE)
    ctx.fill_preserve()
    ctx.set_source_rgb(1, 1, 1)
    ctx.set_line_width(1.3)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "308 nm 50 us", ex, ey + 22, size=11.0, bold=True, color=C_PURPLE, align="center")
    draw_text(ctx, f"(act={exc_50['f_act_bulk']*100:.0f}%, FAIL)", ex, ey + 36, size=10.4, color=C_PURPLE, align="center")

    def draw_fail_callout(cx_pt: float, cy_pt: float, title: str, detail: str, box_x: float, box_y: float) -> None:
        draw_cross(ctx, cx_pt, cy_pt, 8.5, C_RED)
        ctx.save()
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.90)
        ctx.rectangle(box_x, box_y, 206, 36)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.78, 0.14, 0.18, 0.55)
        ctx.set_line_width(1.0)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, title, box_x + 7, box_y + 14, size=11.5, bold=True, color=C_RED)
        draw_text(ctx, detail, box_x + 7, box_y + 29, size=10.5, color=INK)

    # 4. RTA 1000 C / 10 s (FAIL)
    rx, ry = map_x(1.0), map_y(1273.15)
    draw_fail_callout(
        rx, ry, "RTA 1000 C / 10 s",
        f"sig={conv_rta['sigma_anneal_nm']:.2f} nm, loss={conv_rta['f_total_surface_loss']*100:.1f}% (FAIL)",
        rx + 14, ry - 18,
    )

    # 5. Furnace 800 C / 10 min (FAIL)
    f8x, f8y = map_x(math.log10(600.0)) - 10, map_y(1073.15)
    draw_fail_callout(
        f8x, f8y, "Furnace 800 C / 10 min",
        f"sig={conv_f8['sigma_anneal_nm']:.2f} nm, loss={conv_f8['f_total_surface_loss']*100:.1f}% (FAIL)",
        f8x - 222, f8y - 18,
    )

    # 6. Furnace 600 C / 10 min (FAIL — Exp108 anchor)
    f6x, f6y = map_x(math.log10(600.0)) - 10, map_y(873.15)
    draw_fail_callout(
        f6x, f6y, "Furnace 600 C / 10 min",
        f"sig={conv_f6['sigma_anneal_nm']:.2f} nm, loss={conv_f6['f_total_surface_loss']*100:.1f}% (FAIL)",
        f6x - 222, f6y - 18,
    )

    # Legend box in clean bottom-left region
    lx, ly, lw_b, lh_b = px + 18, py + ph - 178, 345, 160
    ctx.save()
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.94)
    ctx.rectangle(lx, ly, lw_b, lh_b)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.2)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "Regime Key (Joint 4-Criteria Window)", lx + 12, ly + 22, size=12.5, bold=True, color=INK)
    leg_items = [
        ((0.64, 0.91, 0.77), "Strict PASS: act>=95%, sig<=0.50 nm, loss<2%"),
        ((0.80, 0.94, 0.92), "Limit PASS: sig in (0.50, 1.00] nm, loss<2%"),
        ((0.88, 0.91, 0.95), "FAIL: Incomplete activation (f_act < 95%)"),
        ((0.98, 0.90, 0.78), "FAIL: Excess TED diffusion or P surface loss"),
        ((0.97, 0.80, 0.81), "FAIL: T_peak >= 0.92 T_melt (1552 K)"),
    ]
    for idx_l, (lc, ltxt) in enumerate(leg_items):
        yy = ly + 36 + idx_l * 24
        ctx.set_source_rgb(*lc)
        ctx.rectangle(lx + 12, yy, 18, 14)
        ctx.fill_preserve()
        ctx.set_source_rgb(*BORDER)
        ctx.set_line_width(0.8)
        ctx.stroke()
        draw_text(ctx, ltxt, lx + 38, yy + 12, size=11.3, color=INK)

    ctx.restore()  # end panel A clip

    # Panel A axis ticks & labels
    xtick_specs = [
        (-5.0, "10 us"), (-4.0, "100 us"), (-3.0, "1 ms"), (-2.0, "10 ms"),
        (-1.0, "100 ms"), (0.0, "1 s"), (1.0, "10 s"), (2.0, "100 s"), (math.log10(600.0), "600 s"),
    ]
    for lt, lbl in xtick_specs:
        tx = map_x(lt)
        ctx.set_source_rgb(*BORDER)
        ctx.set_line_width(1.3)
        ctx.move_to(tx, py + ph)
        ctx.line_to(tx, py + ph + 7)
        ctx.stroke()
        draw_text(ctx, lbl, tx, py + ph + 24, size=12.5, color=INK, align="center")
    draw_text(ctx, "Optical / Thermal Pulse Duration  t_pulse  (log scale)", px + pw / 2.0, py + ph + 54, size=14.5, bold=True, color=INK, align="center")

    for Tv in range(700, 1700, 100):
        ty = map_y(float(Tv))
        ctx.set_source_rgb(*BORDER)
        ctx.set_line_width(1.3)
        ctx.move_to(px - 7, ty)
        ctx.line_to(px, ty)
        ctx.stroke()
        draw_text(ctx, f"{Tv}", px - 12, ty + 4, size=12.5, color=INK, align="right")
    draw_text(ctx, "Peak Surface Temperature  T_peak  (K)", 32, py + ph / 2.0, size=14.5, bold=True, color=INK, align="center", angle=-math.pi / 2.0)

    # -------------------------------------------------------------------------
    # PANEL B (Top-Right): 808 nm Fluence & Wafer Backside T vs t_pulse
    # -------------------------------------------------------------------------
    bx, by, bw, bh = 1200.0, 128.0, 545.0, 365.0
    draw_panel_box(ctx, bx, by, bw, bh, "B. 808 nm Thermal PDE Scaling (T_peak = 1440 K)")

    fcurve = pdata["fluence_curve"]
    lx_min, lx_max = math.log10(0.1), math.log10(5.0)
    f_min, f_max = 0.0, 100.0
    tb_min, tb_max = 300.0, 950.0

    def bx_map(tp_ms: float) -> float:
        return bx + (math.log10(tp_ms) - lx_min) / (lx_max - lx_min) * bw

    def bf_map(F: float) -> float:
        return by + bh - (F - f_min) / (f_max - f_min) * bh

    def bt_map(Tb: float) -> float:
        return by + bh - (Tb - tb_min) / (tb_max - tb_min) * bh

    # Shaded EA2 fluence band [10, 45] J/cm2
    ctx.save()
    ctx.set_source_rgba(0.06, 0.62, 0.42, 0.12)
    ctx.rectangle(bx + 1, bf_map(45.0), bw - 2, bf_map(10.0) - bf_map(45.0))
    ctx.fill()
    ctx.restore()
    draw_text(ctx, "EA2 Fluence Target [10, 45] J/cm2", bx + 10, bf_map(45.0) + 16, size=11.2, bold=True, color=(0.04, 0.45, 0.30))

    # Gridlines
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(0.9)
    for Fv in (20, 40, 60, 80):
        gy = bf_map(float(Fv))
        ctx.move_to(bx, gy)
        ctx.line_to(bx + bw, gy)
        ctx.stroke()

    # Backside limit 700 K (label cleanly on left clear zone)
    ctx.save()
    ctx.set_source_rgb(*C_ORANGE)
    ctx.set_line_width(1.5)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(bx, bt_map(700.0))
    ctx.line_to(bx + bw, bt_map(700.0))
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "T_back limit 700 K", bx + 10, bt_map(700.0) - 7, size=11.0, bold=True, color=C_ORANGE, align="left")

    # Vertical line at 1.0 ms optimal
    x1ms = bx_map(1.0)
    ctx.save()
    ctx.set_source_rgba(0.06, 0.62, 0.42, 0.75)
    ctx.set_line_width(1.8)
    ctx.set_dash([5.0, 4.0])
    ctx.move_to(x1ms, by)
    ctx.line_to(x1ms, by + bh)
    ctx.stroke()
    ctx.restore()

    # Plot Fluence curve (blue)
    ctx.save()
    ctx.set_source_rgb(*C_BLUE)
    ctx.set_line_width(2.8)
    for k, pt in enumerate(fcurve):
        xx, yy = bx_map(pt["t_pulse_ms"]), bf_map(pt["fluence_J_per_cm2"])
        if k == 0:
            ctx.move_to(xx, yy)
        else:
            ctx.line_to(xx, yy)
    ctx.stroke()
    for pt in fcurve:
        ctx.arc(bx_map(pt["t_pulse_ms"]), bf_map(pt["fluence_J_per_cm2"]), 4.0, 0, 2 * math.pi)
        ctx.fill()
    ctx.restore()

    # Plot T_back curve (orange)
    ctx.save()
    ctx.set_source_rgb(*C_ORANGE)
    ctx.set_line_width(2.5)
    for k, pt in enumerate(fcurve):
        xx, yy = bx_map(pt["t_pulse_ms"]), bt_map(pt["T_back_max_K"])
        if k == 0:
            ctx.move_to(xx, yy)
        else:
            ctx.line_to(xx, yy)
    ctx.stroke()
    for pt in fcurve:
        ctx.rectangle(bx_map(pt["t_pulse_ms"]) - 3.5, bt_map(pt["T_back_max_K"]) - 3.5, 7.0, 7.0)
        ctx.fill()
    ctx.restore()

    # Annotate 1.0 ms point cleanly (zero line overlap)
    draw_text(ctx, f"1.0 ms: {opt_b['fluence_J_per_cm2']:.2f} J/cm2", x1ms + 10, bf_map(41.2) + 34, size=11.3, bold=True, color=C_BLUE)
    draw_text(ctx, f"T_back = {opt_b['T_back_max_K']:.1f} K", x1ms - 8, bt_map(593.0) - 18, size=11.3, bold=True, color=C_ORANGE, align="right")

    # Panel B axes
    for tp_t in (0.1, 0.2, 0.5, 1.0, 2.0, 5.0):
        tx = bx_map(tp_t)
        ctx.set_source_rgb(*BORDER)
        ctx.set_line_width(1.2)
        ctx.move_to(tx, by + bh)
        ctx.line_to(tx, by + bh + 6)
        ctx.stroke()
        draw_text(ctx, f"{tp_t:g} ms", tx, by + bh + 21, size=11.5, color=INK, align="center")
    draw_text(ctx, "Pulse Duration t_pulse (ms)", bx + bw / 2.0, by + bh + 44, size=13.0, bold=True, color=INK, align="center")

    for Fv in (0, 20, 40, 60, 80, 100):
        ty = bf_map(float(Fv))
        draw_text(ctx, f"{Fv}", bx - 8, ty + 4, size=11.5, color=C_BLUE, align="right")
    draw_text(ctx, "Fluence F (J/cm2)", bx - 44, by + bh / 2.0, size=12.5, bold=True, color=C_BLUE, align="center", angle=-math.pi / 2.0)

    for Tbv in (300, 500, 700, 900):
        ty = bt_map(float(Tbv))
        draw_text(ctx, f"{Tbv}", bx + bw + 8, ty + 4, size=11.5, color=C_ORANGE, align="left")
    draw_text(ctx, "Backside T_max (K)", bx + bw + 44, by + bh / 2.0, size=12.5, bold=True, color=C_ORANGE, align="center", angle=-math.pi / 2.0)

    # -------------------------------------------------------------------------
    # PANEL C (Bottom-Right): Exp124 Arch-B Total Placement Uncertainty sigma_tot
    # -------------------------------------------------------------------------
    cx, cy, cw, ch = 1200.0, 588.0, 545.0, 365.0
    draw_panel_box(ctx, cx, cy, cw, ch, "C. Net Impact on Exp124 Arch-B Placement Budget (sigma_tot)")

    imp = exp["exp124_placement_budget_impact"]
    bars = [
        ("808 nm 0.5 ms", imp["compact_808nm_0.5ms_1440K_tot_nm"], C_EMERALD),
        ("808 nm 1.0 ms (Opt)", imp["optimal_808nm_1ms_1440K_tot_nm"], C_EMERALD),
        ("Exp124 Base (0.5 nm)", imp["baseline_sigma_anneal_0.50nm_tot_nm"], C_BLUE),
        ("3x Damage Stress", imp["damage_3x_stress_tot_nm"], C_TEAL),
        ("Furnace 800C/10m", exp["conventional_anneal_benchmarks"]["furnace_800C_10min"]["exp124_sigma_tot_nm"], C_AMBER),
        ("RTA 1000C / 10 s", imp["rta_1000C_10s_tot_nm"], C_RED),
        ("Furnace 600C/10m", imp["furnace_600C_10min_tot_nm"], C_RED),
    ]
    bar_x0 = cx + 158.0
    bar_w = cw - 178.0
    v_max = 8.2

    def cx_map(val: float) -> float:
        return bar_x0 + (val / v_max) * bar_w

    # Gridlines
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(0.9)
    for gv in (0, 2, 4, 6, 8):
        gx = cx_map(float(gv))
        ctx.move_to(gx, cy + 16)
        ctx.line_to(gx, cy + ch - 28)
        ctx.stroke()
        draw_text(ctx, f"{gv}", gx, cy + ch - 10, size=11.5, color=INK, align="center")

    # Bars
    row_h = (ch - 56.0) / len(bars)
    for idx_b, (lbl, val, col) in enumerate(bars):
        ry_top = cy + 20.0 + idx_b * row_h + 4.0
        bh_bar = row_h - 11.0
        ctx.set_source_rgb(*col)
        ctx.rectangle(bar_x0, ry_top, cx_map(val) - bar_x0, bh_bar)
        ctx.fill()
        draw_text(ctx, lbl, bar_x0 - 8, ry_top + bh_bar / 2.0 + 4, size=11.5, bold=(idx_b == 1), color=INK, align="right")
        draw_text(ctx, f"{val:.3f} nm", cx_map(val) + 6, ry_top + bh_bar / 2.0 + 4, size=11.3, bold=(idx_b == 1), color=INK)

    # Exp124 3.80 nm ceiling line
    x_ceil = cx_map(3.80)
    ctx.save()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(2.0)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(x_ceil, cy + 14)
    ctx.line_to(x_ceil, cy + ch - 28)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "3.80 nm ceiling", x_ceil + 5, cy + 28, size=11.2, bold=True, color=C_RED)
    draw_text(ctx, "Total 1D RSS Placement Uncertainty sigma_tot (nm)", bar_x0 + bar_w / 2.0, cy + ch + 22, size=13.0, bold=True, color=INK, align="center")

    # Footer summary strip (dynamically read from exp130.json)
    m1 = exp["s55_optical_hardware_spec"]["delivery_modes"]["mode1_single_shot_16x16mm"]
    draw_text(
        ctx,
        f"S5.5 Hardware Anchor (CAD v3.0): CF63 Sapphire Ø44 mm CA (Ø36 mm beam) | 808 nm 1.0 ms @ {opt_b['fluence_J_per_cm2']:.2f} J/cm2 | F_win = {m1['window_fluence_AR_J_per_cm2']:.2f} J/cm2 ({m1['lidt_safety_margin_vs_100J_floor_AR']:.2f}x < 100 J/cm2 LIDT) | Cryo 16x16 mm: {m1['cryo_recovery_to_20mK_min']:.2f} min",
        40, H - 22, size=12.2, bold=True, color=MUTED,
    )

    surf.write_to_png(str(FIG_WINDOW))


# =============================================================================
# FIGURE 2: 5-Panel Technical Dashboard (Thermal, Exp108, P(z), 29Si, Cryo)
# =============================================================================
def render_fig_profiles_ted(exp: dict, pdata: dict) -> None:
    W, H = 1800, 1080
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG)
    ctx.paint()

    draw_text(
        ctx,
        "Exp130 (H148): 1D Thermal Waveforms, Exp108 Anchor Validation, 31P & 29Si Profiles, and Cryo Recovery",
        40, 46, size=24, bold=True, color=INK,
    )
    draw_text(
        ctx,
        "Exact PDE Energy Balance (err < 1e-5) & Mass Conservation (err < 1e-14)  |  Anchored to doi:10.1063/1.331355, Fahey (1989), Bracht (1998), Olson-Roth (1988)",
        40, 74, size=14, color=MUTED,
    )

    # -------------------------------------------------------------------------
    # PANEL A (Top-Left): 1D Nonlinear Si Thermal Waveforms
    # -------------------------------------------------------------------------
    ax, ay, aw, ah = 88.0, 128.0, 795.0, 385.0
    draw_panel_box(ctx, ax, ay, aw, ah, "A. 1D Nonlinear Si Thermal PDE Waveforms (500 um Wafer, T_peak = 1440 K)")

    tx_max = 3.5  # ms
    ty_min, ty_max = 250.0, 1650.0

    def ax_m(t_ms: float) -> float:
        return ax + (t_ms / tx_max) * aw

    def ay_m(T: float) -> float:
        return ay + ah - (T - ty_min) / (ty_max - ty_min) * ah

    ctx.save()
    ctx.rectangle(ax + 1, ay + 1, aw - 2, ah - 2)
    ctx.clip()

    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(0.9)
    for Tv in (400, 600, 800, 1000, 1200, 1400, 1600):
        gy = ay_m(float(Tv))
        ctx.move_to(ax, gy)
        ctx.line_to(ax + aw, gy)
        ctx.stroke()
    for tm in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        gx = ax_m(tm)
        ctx.move_to(gx, ay)
        ctx.line_to(gx, ay + ah)
        ctx.stroke()

    # Reference lines: 0.92 T_melt = 1552 K and 900 K quench line
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.6)
    ctx.set_dash([7.0, 4.0])
    ctx.move_to(ax, ay_m(1552.0))
    ctx.line_to(ax + aw, ay_m(1552.0))
    ctx.stroke()
    ctx.set_source_rgb(*MUTED)
    ctx.set_line_width(1.3)
    ctx.set_dash([4.0, 4.0])
    ctx.move_to(ax, ay_m(900.0))
    ctx.line_to(ax + aw, ay_m(900.0))
    ctx.stroke()
    ctx.set_dash([])
    draw_text(ctx, "0.92 T_melt = 1552 K", ax + aw - 10, ay_m(1552.0) - 6, size=11.2, bold=True, color=C_RED, align="right")
    draw_text(ctx, "900 K self-quench marker (t_q = 0.33 ms)", ax + aw - 10, ay_m(900.0) - 6, size=11.0, color=MUTED, align="right")

    wf = pdata["thermal_waveforms"]
    wf_specs = [
        ("808nm_diode_1.0ms_1440K", "T_surf_K", C_NAVY, 3.0, [], "808 nm 1.0 ms T_surf (41.2 J/cm2)"),
        ("808nm_diode_1.0ms_1440K", "T_back_K", C_NAVY, 2.0, [6.0, 4.0], "808 nm 1.0 ms T_back (max 593 K)"),
        ("532nm_green_1ms_1440K", "T_surf_K", C_TEAL, 2.2, [3.0, 3.0], "532 nm 1.0 ms T_surf (43.7 J/cm2)"),
        ("808nm_diode_0.5ms_1440K", "T_surf_K", C_EMERALD, 2.4, [], "808 nm 0.5 ms T_surf (29.2 J/cm2)"),
        ("308nm_excimer_50us_1440K", "T_surf_K", C_PURPLE, 2.2, [], "308 nm 50 us T_surf (15.4 J/cm2)"),
    ]
    for key, fld, col, lw, dash, _ in wf_specs:
        ts = wf[key]["t_ms"]
        ys = wf[key][fld]
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        started = False
        for t_v, y_v in zip(ts, ys):
            if t_v > tx_max + 0.15:
                break
            xx, yy = ax_m(t_v), ay_m(y_v)
            if not started:
                ctx.move_to(xx, yy)
                started = True
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        ctx.restore()

    # Legend in upper-right clean area
    lgx, lgy = ax + aw - 305, ay + 48
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.94)
    ctx.rectangle(lgx, lgy, 294, 118)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.stroke()
    for idx_w, (_, _, col, lw, dash, lbl) in enumerate(wf_specs):
        yy = lgy + 16 + idx_w * 21
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(lgx + 10, yy)
        ctx.line_to(lgx + 38, yy)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, lbl, lgx + 46, yy + 4, size=11.0, color=INK)
    ctx.restore()

    for tm in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
        draw_text(ctx, f"{tm:.1f}", ax_m(tm), ay + ah + 20, size=11.8, color=INK, align="center")
    draw_text(ctx, "Time t (ms)", ax + aw / 2.0, ay + ah + 42, size=13.0, bold=True, color=INK, align="center")
    for Tv in (300, 600, 900, 1200, 1500):
        draw_text(ctx, f"{Tv}", ax - 10, ay_m(float(Tv)) + 4, size=11.8, color=INK, align="right")
    draw_text(ctx, "Temperature (K)", 30, ay + ah / 2.0, size=13.0, bold=True, color=INK, align="center", angle=-math.pi / 2.0)

    # -------------------------------------------------------------------------
    # PANEL B (Top-Right): Exp108 Anchor Mass-Fate Validation (doi:10.1063/1.331355)
    # -------------------------------------------------------------------------
    bx, by, bw, bh = 965.0, 128.0, 780.0, 385.0
    draw_panel_box(ctx, bx, by, bw, bh, "B. Exp108 Anchor Reproduction (doi:10.1063/1.331355) — Exact 31P Mass Fate (%)")

    a600 = exp["exp108_anchor_doi_10_1063_1_331355"]["600C_10min_uhv_blanket"]
    a800 = exp["exp108_anchor_doi_10_1063_1_331355"]["800C_10min_uhv_blanket"]
    opt_b = exp["wavelength_and_pulse_benchmarks"]["808nm_diode_1.0ms_1440K"]
    rta_b = exp["conventional_anneal_benchmarks"]["rta_1000C_10s"]

    fate_rows = [
        ("600 C / 10 min UHV (1D Blanket)", a600["f_act_bulk"] * 100, a600["f_surface_pileup"] * 100, a600["f_vacuum_escape"] * 100),
        ("800 C / 10 min UHV (1D Blanket)", a800["f_act_bulk"] * 100, a800["f_surface_pileup"] * 100, a800["f_vacuum_escape"] * 100),
        ("RTA 1000 C / 10 s (Single Donor)", rta_b["f_act_bulk"] * 100, rta_b["f_surface_pileup"] * 100, rta_b["f_vacuum_escape"] * 100),
        ("808 nm 1.0 ms / 1440 K (Machine)", opt_b["f_act_bulk"] * 100, opt_b["f_total_surface_loss"] * 100, 0.0),
    ]

    fx0 = bx + 235.0
    fw = bw - 265.0

    # Legend at top of Panel B
    leg_b = [
        (C_EMERALD, "Active Substitutional Bulk 31P"),
        (C_AMBER, "Front-Surface Pile-Up (Trapped)"),
        (C_RED, "UHV Vacuum Escape (Desorbed)"),
    ]
    lx_cur = bx + 16.0
    for col, ltxt in leg_b:
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx_cur, by + 16, 16, 13)
        ctx.fill()
        draw_text(ctx, ltxt, lx_cur + 22, by + 27, size=11.5, bold=True, color=INK)
        lx_cur += 248.0

    # Gridlines 0..100%
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(0.9)
    for pct in (0, 25, 50, 75, 100):
        gx = fx0 + (pct / 100.0) * fw
        ctx.move_to(gx, by + 44)
        ctx.line_to(gx, by + bh - 40)
        ctx.stroke()
        draw_text(ctx, f"{pct}%", gx, by + bh - 20, size=11.5, color=INK, align="center")

    rh = (bh - 95.0) / len(fate_rows)
    for idx_f, (lbl, p_act, p_pile, p_esc) in enumerate(fate_rows):
        ry = by + 52.0 + idx_f * rh
        hb = rh - 22.0
        draw_text(ctx, lbl, fx0 - 10, ry + hb / 2.0 + 4, size=11.5, bold=(idx_f == 3), color=INK, align="right")

        x_cur = fx0
        for frac, col, tag in [(p_act, C_EMERALD, f"{p_act:.1f}%"), (p_pile, C_AMBER, f"{p_pile:.1f}%"), (p_esc, C_RED, f"{p_esc:.1f}%")]:
            w_seg = max(0.0, (frac / 100.0) * fw)
            if w_seg > 0.5:
                ctx.set_source_rgb(*col)
                ctx.rectangle(x_cur, ry, w_seg, hb)
                ctx.fill()
                if w_seg > 42.0:
                    draw_text(ctx, tag, x_cur + w_seg / 2.0, ry + hb / 2.0 + 4, size=11.5, bold=True, color=(1, 1, 1), align="center")
                x_cur += w_seg
        # Border around full 100% bar
        ctx.set_source_rgb(*BORDER)
        ctx.set_line_width(1.0)
        ctx.rectangle(fx0, ry, fw, hb)
        ctx.stroke()

    draw_text(
        ctx,
        f"EA1 PASS: 600C gives {a600['f_surface_pileup']*100:.1f}% front-surface pile-up & {a600['f_vacuum_escape']*100:.2f}% escape; 800C gives {a800['f_vacuum_escape']*100:.1f}% vacuum escape (mass_err < 1e-14)",
        bx + bw / 2.0, by + bh + 22, size=11.5, bold=True, color=C_NAVY, align="center",
    )

    # -------------------------------------------------------------------------
    # PANEL C (Bottom-Left): 5 keV 31P Depth Profile P(z)
    # -------------------------------------------------------------------------
    cx, cy, cw, ch = 88.0, 598.0, 515.0, 365.0
    draw_panel_box(ctx, cx, cy, cw, ch, "C. 5 keV 31P+ Depth Profile P(z)")

    mp = pdata["machine_profiles"]
    zs = mp["z_nm"]
    zx_max = 25.0
    py_max = 0.165

    def cx_m(z: float) -> float:
        return cx + (z / zx_max) * cw

    def cy_m(p: float) -> float:
        return cy + ch - (p / py_max) * ch

    ctx.save()
    ctx.rectangle(cx + 1, cy + 1, cw - 2, ch - 2)
    ctx.clip()
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(0.8)
    for zv in (5, 10, 15, 20):
        ctx.move_to(cx_m(float(zv)), cy)
        ctx.line_to(cx_m(float(zv)), cy + ch)
        ctx.stroke()
    for pv in (0.04, 0.08, 0.12, 0.16):
        ctx.move_to(cx, cy_m(pv))
        ctx.line_to(cx + cw, cy_m(pv))
        ctx.stroke()

    conv_f6_p = exp["conventional_anneal_benchmarks"]["furnace_600C_10min"]
    # Draw emerald flash first, then dashed BCA on top so identical profile overlap is clearly visible
    p_curves = [
        ("P_flash_1ms_1440K", C_EMERALD, 3.6, [], f"808 nm 1.0 ms (sig={opt_b['sigma_anneal_nm']:.3f} nm)"),
        ("P_init", (0.12, 0.12, 0.15), 2.0, [5.0, 4.0], "As-implanted BCA (Rp=6.46 nm)"),
        ("P_furnace_600C_10min", C_AMBER, 2.2, [], f"Furnace 600C/10m (sig={conv_f6_p['sigma_anneal_nm']:.2f} nm)"),
        ("P_rta_1000C_10s", C_RED, 2.2, [], f"RTA 1000C/10s (loss={rta_b['f_total_surface_loss']*100:.1f}%)"),
    ]
    for key, col, lw, dash, _ in p_curves:
        vals = mp[key]
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        started = False
        for zv, pv in zip(zs, vals):
            if zv > zx_max + 0.5:
                break
            xx, yy = cx_m(zv), cy_m(pv)
            if not started:
                ctx.move_to(xx, yy)
                started = True
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        ctx.restore()

    # Legend
    lx_c, ly_c = cx + cw - 245, cy + 14
    ctx.set_source_rgba(1, 1, 1, 0.94)
    ctx.rectangle(lx_c, ly_c, 235, 96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.stroke()
    for idx_c, (_, col, lw, dash, lbl) in enumerate(p_curves):
        yy = ly_c + 16 + idx_c * 21
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(lx_c + 8, yy)
        ctx.line_to(lx_c + 32, yy)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, lbl, lx_c + 38, yy + 4, size=10.8, color=INK)
    ctx.restore()

    for zv in (0, 5, 10, 15, 20, 25):
        draw_text(ctx, f"{zv}", cx_m(float(zv)), cy + ch + 19, size=11.5, color=INK, align="center")
    draw_text(ctx, "Depth z from Si Surface (nm)", cx + cw / 2.0, cy + ch + 42, size=12.8, bold=True, color=INK, align="center")
    for pv in (0.0, 0.04, 0.08, 0.12, 0.16):
        draw_text(ctx, f"{pv:.2f}", cx - 8, cy_m(pv) + 4, size=11.3, color=INK, align="right")
    draw_text(ctx, "Normalized P(z) (1/nm)", 30, cy + ch / 2.0, size=12.8, bold=True, color=INK, align="center", angle=-math.pi / 2.0)

    # -------------------------------------------------------------------------
    # PANEL D (Bottom-Mid): 28Si/29Si Epitaxial Interface Preservation (z_epi = 20 nm)
    # -------------------------------------------------------------------------
    dx, dy, dw, dh = 678.0, 598.0, 480.0, 365.0
    draw_panel_box(ctx, dx, dy, dw, dh, "D. 28Si/29Si Bath Interface (z_epi = 20 nm)")

    zx0, zx1 = 15.0, 25.0
    cy_max = 1.15  # % 29Si

    def dx_m(z: float) -> float:
        return dx + (z - zx0) / (zx1 - zx0) * dw

    def dy_m(c_pct: float) -> float:
        return dy + dh - (c_pct / cy_max) * dh

    ctx.save()
    ctx.rectangle(dx + 1, dy + 1, dw - 2, dh - 2)
    ctx.clip()
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(0.8)
    for zv in (16, 18, 20, 22, 24):
        ctx.move_to(dx_m(float(zv)), dy)
        ctx.line_to(dx_m(float(zv)), dy + dh)
        ctx.stroke()
    for cv in (0.2, 0.4, 0.6, 0.8, 1.0):
        ctx.move_to(dx, dy_m(cv))
        ctx.line_to(dx + dw, dy_m(cv))
        ctx.stroke()

    # Exact initial step function at z_epi = 20 nm
    ctx.save()
    ctx.set_source_rgb(0.15, 0.15, 0.18)
    ctx.set_line_width(2.0)
    ctx.set_dash([5.0, 4.0])
    ctx.move_to(dx_m(15.0), dy_m(1.0))
    ctx.line_to(dx_m(20.0), dy_m(1.0))
    ctx.line_to(dx_m(20.0), dy_m(0.0))
    ctx.line_to(dx_m(25.0), dy_m(0.0))
    ctx.stroke()
    ctx.restore()

    c29_curves = [
        ("C29_flash_1ms_1440K", C_EMERALD, 3.0, f"808 nm 1.0 ms (sig_iso={opt_b['sigma_iso_nm']:.3f} nm)"),
        ("C29_rta_1000C_10s", C_RED, 2.3, f"RTA 1000C/10s (sig_iso={rta_b['sigma_iso_nm']:.3f} nm)"),
    ]
    for key, col, lw, _ in c29_curves:
        vals = mp[key]
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        started = False
        for zv, cv in zip(zs, vals):
            if zv < zx0 - 0.5 or zv > zx1 + 0.5:
                continue
            xx, yy = dx_m(zv), dy_m(cv * 100.0)
            if not started:
                ctx.move_to(xx, yy)
                started = True
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        ctx.restore()

    # Clean callout & legend in upper right
    lx_d, ly_d = dx + dw - 242, dy + 14
    ctx.set_source_rgba(1, 1, 1, 0.94)
    ctx.rectangle(lx_d, ly_d, 232, 86)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.stroke()
    ctx.save()
    ctx.set_source_rgb(0.15, 0.15, 0.18)
    ctx.set_line_width(2.0)
    ctx.set_dash([5.0, 4.0])
    ctx.move_to(lx_d + 8, ly_d + 16)
    ctx.line_to(lx_d + 30, ly_d + 16)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "Initial Mode-B Step (1% -> 0%)", lx_d + 36, ly_d + 20, size=10.6, color=INK)
    for idx_d, (_, col, lw, lbl) in enumerate(c29_curves):
        yy = ly_d + 39 + idx_d * 22
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        ctx.move_to(lx_d + 8, yy)
        ctx.line_to(lx_d + 30, yy)
        ctx.stroke()
        draw_text(ctx, lbl, lx_d + 36, yy + 4, size=10.6, color=INK)

    draw_text(ctx, "Mode-B 1% 29Si", dx + 16, dy + 160, size=11.8, bold=True, color=C_NAVY)
    draw_text(ctx, "epi bath (z <= 20 nm)", dx + 16, dy + 178, size=11.0, color=MUTED)
    draw_text(ctx, "28Si substrate", dx + dw - 14, dy + dh - 26, size=11.5, bold=True, color=C_NAVY, align="right")
    draw_text(ctx, "(0% 29Si, z > 20 nm)", dx + dw - 14, dy + dh - 10, size=10.8, color=MUTED, align="right")
    ctx.restore()

    for zv in (15, 17, 19, 20, 21, 23, 25):
        draw_text(ctx, f"{zv}", dx_m(float(zv)), dy + dh + 19, size=11.5, color=INK, align="center")
    draw_text(ctx, "Depth z (nm)", dx + dw / 2.0, dy + dh + 42, size=12.8, bold=True, color=INK, align="center")
    for cv in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        draw_text(ctx, f"{cv:.1f}%", dx - 8, dy_m(cv) + 4, size=11.3, color=INK, align="right")
    draw_text(ctx, "29Si Fraction (%)", dx - 52, dy + dh / 2.0, size=12.8, bold=True, color=INK, align="center", angle=-math.pi / 2.0)

    # -------------------------------------------------------------------------
    # PANEL E (Bottom-Right): Debye Cryo Cooldown to 20 mK
    # -------------------------------------------------------------------------
    ex, ey, ew, eh = 1230.0, 598.0, 515.0, 365.0
    draw_panel_box(ctx, ex, ey, ew, eh, "E. Cryo Recovery to 20 mK (Debye + PT410 Switch)")

    cs = pdata["cryo_scenarios"]
    c_bars = [
        ("Load-Lock RT", cs["in_line_loadlock_rt_baseline"]["t_cool_total_min"], "0 J (Prod. Base)", C_BLUE),
        ("4x4 mm Tile", cs["insitu_s55_4x4mm_single_tile"]["t_cool_total_min"], f"{cs['insitu_s55_4x4mm_single_tile']['E_absorbed_J']:.1f} J, {cs['insitu_s55_4x4mm_single_tile']['T_bulk_eq_post_flash_K']:.0f} K", C_TEAL),
        ("16x16 mm Field", cs["insitu_s55_16x16mm_active_field"]["t_cool_total_min"], f"{cs['insitu_s55_16x16mm_active_field']['E_absorbed_J']:.1f} J, {cs['insitu_s55_16x16mm_active_field']['T_bulk_eq_post_flash_K']:.0f} K", C_EMERALD),
        ("50 mm Wafer", cs["insitu_s55_50mm_full_wafer"]["t_cool_total_min"], f"{cs['insitu_s55_50mm_full_wafer']['E_absorbed_J']:.0f} J, {cs['insitu_s55_50mm_full_wafer']['T_bulk_eq_post_flash_K']:.0f} K", C_AMBER),
    ]
    ex0 = ex + 122.0
    ew_b = ew - 142.0
    tmax = 19.0  # min

    def ex_m(t_min: float) -> float:
        return ex0 + (t_min / tmax) * ew_b

    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(0.9)
    for tm in (0, 5, 10, 15):
        gx = ex_m(float(tm))
        ctx.move_to(gx, ey + 18)
        ctx.line_to(gx, ey + eh - 34)
        ctx.stroke()
        draw_text(ctx, f"{tm}", gx, ey + eh - 14, size=11.5, color=INK, align="center")

    rh_e = (eh - 64.0) / len(c_bars)
    for idx_e, (lbl, tmin, note, col) in enumerate(c_bars):
        ry = ey + 24.0 + idx_e * rh_e
        hb = rh_e - 26.0
        w_bar = max(4.0, ex_m(tmin) - ex0)
        ctx.set_source_rgb(*col)
        ctx.rectangle(ex0, ry, w_bar, hb)
        ctx.fill()
        draw_text(ctx, lbl, ex0 - 8, ry + hb / 2.0 + 4, size=11.5, bold=(idx_e in (0, 2)), color=INK, align="right")
        draw_text(ctx, f"{tmin:.2f} min", ex0 + w_bar + 7, ry + hb / 2.0 - 1, size=11.5, bold=True, color=INK)
        draw_text(ctx, note, ex0 + w_bar + 7, ry + hb / 2.0 + 13, size=10.2, color=MUTED)

    # 15 min EA5 budget line
    x15 = ex_m(15.0)
    ctx.save()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(2.0)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(x15, ey + 16)
    ctx.line_to(x15, ey + eh - 34)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "15 min limit", x15 - 5, ey + 30, size=11.0, bold=True, color=C_RED, align="right")
    draw_text(ctx, "Cooldown Time to 20 mK (min, incl. 120 s DR settling)", ex0 + ew_b / 2.0, ey + eh + 42, size=12.2, bold=True, color=INK, align="center")

    draw_text(
        ctx,
        "Epistemic Scope: {Model} / {Sayisal-Simulasyon} / {Literatur} — Physical lab confirmation of isolated 5 keV 31P ms-flash remains Gate M1 G4 (Risk R6 Theory Closed).",
        40, H - 22, size=12.5, bold=True, color=MUTED,
    )

    surf.write_to_png(str(FIG_PROFILES))


def main() -> None:
    exp = json.loads(EXP_JSON.read_text(encoding="utf-8"))
    pdata = json.loads(PLOT_JSON.read_text(encoding="utf-8"))
    render_fig_anneal_window(exp, pdata)
    render_fig_profiles_ted(exp, pdata)
    print(f"Wrote {FIG_WINDOW.relative_to(REPO_ROOT)} and {FIG_PROFILES.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
