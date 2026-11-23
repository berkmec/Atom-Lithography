"""Exp139 PyCairo Plotter (2400x1400 publication-grade 6-panel dashboard; /usr/bin/python3 -B).

Reads results/exp139_epi_cap_process_integration/{exp139.json, plot_data_exp139.json}
and generates results/exp139_epi_cap_process_integration/fig_exp139_epi_cap_integration.png.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Tuple

import cairo

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "exp139_epi_cap_process_integration"
EXP_JSON = RESULTS_DIR / "exp139.json"
PLOT_JSON = RESULTS_DIR / "plot_data_exp139.json"
OUT_PNG = RESULTS_DIR / "fig_exp139_epi_cap_integration.png"

# High-contrast, colorblind-safe palette
BG = (0.985, 0.988, 0.992)
PANEL_BG = (1.0, 1.0, 1.0)
INK = (0.10, 0.13, 0.18)
MUTED = (0.37, 0.42, 0.49)
GRID = (0.87, 0.89, 0.92)
BORDER = (0.24, 0.29, 0.35)

C_EMERALD = (0.05, 0.60, 0.40)
C_TEAL = (0.08, 0.58, 0.68)
C_NAVY = (0.10, 0.24, 0.54)
C_BLUE = (0.14, 0.44, 0.78)
C_AMBER = (0.85, 0.50, 0.06)
C_ORANGE = (0.88, 0.36, 0.10)
C_RED = (0.78, 0.14, 0.18)
C_PURPLE = (0.48, 0.20, 0.66)
C_GRAY = (0.48, 0.52, 0.58)


def set_font(ctx: cairo.Context, size: float, bold: bool = False) -> None:
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)


def draw_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 15.0,
    bold: bool = False,
    color: Tuple[float, float, float] = INK,
    align: str = "left",
    angle: float = 0.0,
) -> None:
    clean = text.replace("\n", " ")
    ctx.save()
    set_font(ctx, size, bold)
    ext = ctx.text_extents(clean)
    dx = 0.0
    if align == "center":
        dx = -(ext.width / 2.0 + ext.x_bearing)
    elif align == "right":
        dx = -(ext.width + ext.x_bearing)
    ctx.translate(x, y)
    if angle != 0.0:
        ctx.rotate(angle)
    ctx.set_source_rgb(*color)
    ctx.move_to(dx, 0.0)
    ctx.show_text(clean)
    ctx.restore()


def draw_panel(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str) -> None:
    ctx.save()
    ctx.set_source_rgb(*PANEL_BG)
    ctx.rectangle(x, y, w, h)
    ctx.fill()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.6)
    ctx.rectangle(x, y, w, h)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, title, x + 6, y - 12, size=17.5, bold=True, color=INK)


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


def render_dashboard(exp: dict, pdata: dict) -> None:
    W, H = 2400, 1400
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG)
    ctx.paint()

    # Header Banner
    draw_text(
        ctx,
        "Exp139 (H157): Integrated 8 nm 28Si Epi Cap + ms Flash Anneal + Si/SiO2 Charge-Noise Bridge & S5.6 Hardware",
        48, 52, size=29, bold=True, color=INK,
    )
    draw_text(
        ctx,
        "Coupled ZBL+LSS BCA + Recoil-O Knock-On + Exp130 Thermal/TED PDE + Low-T 28Si MBE Kinetics + 2D Image-Charge McWhorter + Exp131 4x4 Flip-Flop Yield  |  no_lab_measurement=True",
        48, 84, size=15.5, color=MUTED,
    )

    # Panel Geometry (2 rows x 3 columns, generous 170 px gutter between A/B for dual y-axes)
    r1_y, r1_h = 148.0, 520.0
    r2_y, r2_h = 778.0, 520.0
    c1_x, c1_w = 100.0, 635.0
    c2_x, c2_w = 905.0, 645.0
    c3_x, c3_w = 1665.0, 675.0

    # =========================================================================
    # PANEL A (Top-Left): Route A Low-T 28Si MBE Optimization (250..450 C)
    # =========================================================================
    draw_panel(ctx, c1_x, r1_y, c1_w, r1_h, "A. Route A Low-T 28Si MBE Window (8.0 nm @ 0.10 nm/s)")
    mbe = pdata["mbe_sweep"]
    mbe_opt = exp["route_A_mbe_optimization"]["optimal_point"]
    win_T = exp["route_A_mbe_optimization"]["passing_window_T_epi_C"]
    T_min, T_max = 250.0, 450.0
    ls_min, ls_max = 0.0, 7.5
    nd_min, nd_max = 12.5, 17.8  # log10(N_def)

    def ax_m(T: float) -> float:
        return c1_x + (T - T_min) / (T_max - T_min) * c1_w

    def ay_ls(ls: float) -> float:
        return r1_y + r1_h - (ls - ls_min) / (ls_max - ls_min) * r1_h

    def ay_nd(logn: float) -> float:
        return r1_y + r1_h - (logn - nd_min) / (nd_max - nd_min) * r1_h

    ctx.save()
    ctx.rectangle(c1_x + 1, r1_y + 1, c1_w - 2, r1_h - 2)
    ctx.clip()

    # Shaded passing T_epi window
    if len(win_T) == 2:
        ctx.set_source_rgba(0.05, 0.60, 0.40, 0.13)
        ctx.rectangle(ax_m(win_T[0]), r1_y, ax_m(win_T[1]) - ax_m(win_T[0]), r1_h)
        ctx.fill()
        draw_text(
            ctx,
            f"Feasible MBE Window ({win_T[0]:.0f}-{win_T[1]:.0f} C)",
            0.5 * (ax_m(win_T[0]) + ax_m(win_T[1])), r1_y + 24,
            size=13.0, bold=True, color=(0.03, 0.44, 0.28), align="center",
        )

    # Gridlines
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.0)
    for Tv in (275, 300, 325, 350, 375, 400, 425):
        ctx.move_to(ax_m(float(Tv)), r1_y)
        ctx.line_to(ax_m(float(Tv)), r1_y + r1_h)
        ctx.stroke()
    for lsv in (1, 2, 3, 4, 5, 6, 7):
        ctx.move_to(c1_x, ay_ls(float(lsv)))
        ctx.line_to(c1_x + c1_w, ay_ls(float(lsv)))
        ctx.stroke()

    # Threshold dashed lines: L_seg <= 3.5 nm (navy) and N_def <= 1e15 (orange)
    ctx.set_source_rgb(*C_NAVY)
    ctx.set_line_width(1.6)
    ctx.set_dash([7.0, 5.0])
    ctx.move_to(c1_x, ay_ls(3.5))
    ctx.line_to(c1_x + c1_w, ay_ls(3.5))
    ctx.stroke()
    ctx.set_source_rgb(*C_ORANGE)
    ctx.move_to(c1_x, ay_nd(15.0))
    ctx.line_to(c1_x + c1_w, ay_nd(15.0))
    ctx.stroke()
    ctx.set_dash([])

    draw_text(ctx, "L_seg limit 3.5 nm", c1_x + 12, ay_ls(3.5) - 7, size=12.5, bold=True, color=C_NAVY)
    draw_text(ctx, "N_def limit 1e15 cm-3", c1_x + c1_w - 10, ay_nd(15.0) - 7, size=12.5, bold=True, color=C_ORANGE, align="right")

    # Vertical line at T_epi*
    x_opt_mbe = ax_m(mbe_opt["T_epi_C"])
    ctx.set_source_rgb(*C_EMERALD)
    ctx.set_line_width(2.0)
    ctx.set_dash([5.0, 4.0])
    ctx.move_to(x_opt_mbe, r1_y + 34)
    ctx.line_to(x_opt_mbe, r1_y + r1_h)
    ctx.stroke()
    ctx.set_dash([])

    # Curve 1: L_seg (navy solid)
    ctx.set_source_rgb(*C_NAVY)
    ctx.set_line_width(3.2)
    for k, pt in enumerate(mbe):
        xx, yy = ax_m(pt["T_epi_C"]), ay_ls(pt["L_seg_nm"])
        if k == 0:
            ctx.move_to(xx, yy)
        else:
            ctx.line_to(xx, yy)
    ctx.stroke()

    # Curve 2: log10(N_def) (orange solid)
    ctx.set_source_rgb(*C_ORANGE)
    ctx.set_line_width(3.0)
    for k, pt in enumerate(mbe):
        xx, yy = ax_m(pt["T_epi_C"]), ay_nd(math.log10(pt["N_def_cm3"]))
        if k == 0:
            ctx.move_to(xx, yy)
        else:
            ctx.line_to(xx, yy)
    ctx.stroke()

    # Curve 3: R_q scaled (purple dotted, 10x nm on left axis -> 0.1 nm = 1.0)
    ctx.set_source_rgb(*C_PURPLE)
    ctx.set_line_width(2.4)
    ctx.set_dash([4.0, 4.0])
    for k, pt in enumerate(mbe):
        xx, yy = ax_m(pt["T_epi_C"]), ay_ls(pt["R_q_nm"] * 10.0)
        if k == 0:
            ctx.move_to(xx, yy)
        else:
            ctx.line_to(xx, yy)
    ctx.stroke()
    ctx.set_dash([])

    # Star at T_epi* on L_seg curve
    draw_star(ctx, x_opt_mbe, ay_ls(mbe_opt["L_seg_nm"]), 11.5, 5.2)
    ctx.set_source_rgb(0.98, 0.78, 0.12)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(1.6)
    ctx.stroke()

    # Clean optimum callout card in lower-left clear space
    bx_a, by_a = c1_x + 14, r1_y + r1_h - 134
    ctx.set_source_rgba(1, 1, 1, 0.94)
    ctx.rectangle(bx_a, by_a, 290, 120)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_EMERALD)
    ctx.set_line_width(1.8)
    ctx.stroke()
    draw_text(ctx, f"OPTIMAL T_epi* = {mbe_opt['T_epi_C']:.0f} C (80 s)", bx_a + 10, by_a + 22, size=13.5, bold=True, color=(0.03, 0.44, 0.28))
    draw_text(ctx, f"h_epi = {mbe_opt['h_epi_nm']:.1f} nm ({mbe_opt['epi_margin_ratio']:.1f}x cap)", bx_a + 10, by_a + 44, size=12.5, color=INK)
    draw_text(ctx, f"R_q = {mbe_opt['R_q_nm']:.3f} nm (0.68 ML)", bx_a + 10, by_a + 64, size=12.5, color=C_PURPLE)
    draw_text(ctx, f"N_def = {mbe_opt['N_def_cm3']:.2e} cm-3", bx_a + 10, by_a + 84, size=12.5, color=C_ORANGE)
    draw_text(ctx, f"L_seg = {mbe_opt['L_seg_nm']:.2f} nm | sig_iso = {exp['route_A_mbe_optimization']['combined_sigma_iso_flash_plus_mbe_nm']:.4f} nm", bx_a + 10, by_a + 104, size=12.2, color=C_NAVY)

    # Compact legend upper-right
    lgx, lgy = c1_x + c1_w - 220, r1_y + 42
    ctx.set_source_rgba(1, 1, 1, 0.93)
    ctx.rectangle(lgx, lgy, 210, 82)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.stroke()
    for idx_k, (col, dash, lbl) in enumerate([
        (C_NAVY, [], "L_seg (nm, left)"),
        (C_ORANGE, [], "log10 N_def (right)"),
        (C_PURPLE, [4.0, 4.0], "10x R_q (nm, left)"),
    ]):
        yy = lgy + 18 + idx_k * 23
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.6)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(lgx + 10, yy)
        ctx.line_to(lgx + 42, yy)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, lbl, lgx + 48, yy + 4, size=12.2, color=INK)
    ctx.restore()

    for Tv in (250, 300, 350, 400, 450):
        draw_text(ctx, f"{Tv}", ax_m(float(Tv)), r1_y + r1_h + 24, size=13.5, color=INK, align="center")
    draw_text(ctx, "MBE Substrate Temperature T_epi (C)", c1_x + c1_w / 2.0, r1_y + r1_h + 52, size=15.0, bold=True, color=INK, align="center")
    for lsv in (0, 1, 2, 3, 4, 5, 6, 7):
        draw_text(ctx, f"{lsv}", c1_x - 10, ay_ls(float(lsv)) + 5, size=13.0, color=C_NAVY, align="right")
    draw_text(ctx, "L_seg (nm)  &  10x R_q (nm)", 32, r1_y + r1_h / 2.0, size=14.5, bold=True, color=C_NAVY, align="center", angle=-math.pi / 2.0)
    for ndv in (13, 14, 15, 16, 17):
        draw_text(ctx, f"1e{ndv}", c1_x + c1_w + 8, ay_nd(float(ndv)) + 5, size=12.5, color=C_ORANGE, align="left")
    draw_text(ctx, "Vacancy Defect N_def (cm-3)", c1_x + c1_w + 62, r1_y + r1_h / 2.0, size=14.0, bold=True, color=C_ORANGE, align="center", angle=-math.pi / 2.0)

    # =========================================================================
    # PANEL B (Top-Mid): ZBL+LSS BCA Straggle & Route B Recoil-O Penalty
    # =========================================================================
    draw_panel(ctx, c2_x, r1_y, c2_w, r1_h, "B. ZBL+LSS BCA Straggle & Recoil-O Penalty (5-24 keV)")
    bca_list = pdata["bca_sweep"]
    e_min, e_max = 4.0, 25.0
    nm_min, nm_max = 0.0, 17.5

    def bx_m(Ek: float) -> float:
        return c2_x + (Ek - e_min) / (e_max - e_min) * c2_w

    def by_m(nm: float) -> float:
        return r1_y + r1_h - (nm - nm_min) / (nm_max - nm_min) * r1_h

    ctx.save()
    ctx.rectangle(c2_x + 1, r1_y + 1, c2_w - 2, r1_h - 2)
    ctx.clip()

    # Shaded green Exp124 lateral ceiling <= 3.80 nm
    ctx.set_source_rgba(0.05, 0.60, 0.40, 0.11)
    ctx.rectangle(c2_x, by_m(3.80), c2_w, by_m(0.0) - by_m(3.80))
    ctx.fill()

    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.0)
    for Ev in (5, 10, 15, 20, 24):
        ctx.move_to(bx_m(float(Ev)), r1_y)
        ctx.line_to(bx_m(float(Ev)), r1_y + r1_h)
        ctx.stroke()
    for nv in (2, 4, 6, 8, 10, 12, 14, 16):
        ctx.move_to(c2_x, by_m(float(nv)))
        ctx.line_to(c2_x + c2_w, by_m(float(nv)))
        ctx.stroke()

    # 3.80 nm Exp124 ceiling dashed line
    ctx.set_source_rgb(*C_EMERALD)
    ctx.set_line_width(1.8)
    ctx.set_dash([7.0, 5.0])
    ctx.move_to(c2_x, by_m(3.80))
    ctx.line_to(c2_x + c2_w, by_m(3.80))
    ctx.stroke()
    ctx.set_dash([])
    draw_text(ctx, "Exp124 sigma_tot ceiling = 3.80 nm", c2_x + c2_w - 10, by_m(3.80) + 18, size=12.5, bold=True, color=(0.03, 0.44, 0.28), align="right")

    # Plot curves: Rp, sigma_lat, sigma_z
    for fld, col, lw in [("Rp_nm", C_NAVY, 3.2), ("sigma_lat_nm", C_RED, 3.0), ("sigma_z_nm", C_AMBER, 2.8)]:
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        for k, pt in enumerate(bca_list):
            xx, yy = bx_m(pt["E_keV"]), by_m(pt[fld])
            if k == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        for pt in bca_list:
            ctx.arc(bx_m(pt["E_keV"]), by_m(pt[fld]), 4.2, 0, 2 * math.pi)
            ctx.fill()

    # Highlight 5 keV (Route A/C) and 22 keV (Route B)
    e5 = exp["bca_energy_sweep"]["E5"]
    e22 = exp["bca_energy_sweep"]["E22"]
    rec22 = exp["recoil_oxygen_route_B"]["E22_1p5nm_SiO2"]

    ctx.set_source_rgb(*C_EMERALD)
    ctx.set_line_width(2.0)
    ctx.set_dash([4.0, 4.0])
    ctx.move_to(bx_m(5.0), r1_y + 10)
    ctx.line_to(bx_m(5.0), r1_y + r1_h)
    ctx.stroke()
    ctx.set_source_rgb(*C_RED)
    ctx.move_to(bx_m(22.0), r1_y + 10)
    ctx.line_to(bx_m(22.0), r1_y + r1_h)
    ctx.stroke()
    ctx.set_dash([])

    # Route A/C 5 keV callout
    draw_text(ctx, "Route A/C (5 keV)", bx_m(5.0) + 8, r1_y + 34, size=13.0, bold=True, color=(0.03, 0.44, 0.28))
    draw_text(ctx, f"Rp={e5['Rp_nm']:.2f}, sig_x={e5['sigma_lat_nm']:.2f} nm", bx_m(5.0) + 8, r1_y + 52, size=12.0, color=INK)
    draw_text(ctx, f"Exp124 v5 sig_tot={exp['coupled_thermal_chain_ted']['exp124_sigma_tot_v5_1530K_chain_nm']:.2f} nm", bx_m(5.0) + 8, r1_y + 69, size=12.0, bold=True, color=(0.03, 0.44, 0.28))

    # Route B 22 keV callout box
    bxb, byb = c2_x + c2_w - 315, r1_y + 205
    ctx.set_source_rgba(1, 1, 1, 0.94)
    ctx.rectangle(bxb, byb, 300, 100)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.7)
    ctx.stroke()
    draw_text(ctx, "Route B Through-Cap (22 keV): FAIL", bxb + 10, byb + 21, size=12.8, bold=True, color=C_RED)
    draw_text(ctx, f"Rp={e22['Rp_nm']:.2f} nm (matches 5keV+8nm cap)", bxb + 10, byb + 41, size=11.8, color=INK)
    draw_text(ctx, f"sig_x={e22['sigma_lat_nm']:.2f} nm ({e22['sigma_lat_nm']/e5['sigma_lat_nm']:.2f}x!), sig_z={e22['sigma_z_nm']:.2f} nm", bxb + 10, byb + 60, size=11.8, bold=True, color=C_RED)
    draw_text(ctx, f"Recoil-O: {rec22['O_injected_into_Si_per_ion']:.2f} O/ion (p90={rec22['p90_O_depth_in_Si_nm']:.2f} nm)", bxb + 10, byb + 80, size=11.8, color=C_AMBER)

    # Legend top-left
    lx_b, ly_b = c2_x + 14, r1_y + 94
    ctx.set_source_rgba(1, 1, 1, 0.93)
    ctx.rectangle(lx_b, ly_b, 200, 78)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.stroke()
    for idx_k, (col, lbl) in enumerate([(C_NAVY, "Projected Range Rp"), (C_RED, "Lateral Straggle sig_x"), (C_AMBER, "Depth Straggle sig_z")]):
        yy = ly_b + 18 + idx_k * 22
        ctx.set_source_rgb(*col)
        ctx.set_line_width(3.0)
        ctx.move_to(lx_b + 10, yy)
        ctx.line_to(lx_b + 38, yy)
        ctx.stroke()
        draw_text(ctx, lbl, lx_b + 45, yy + 4, size=12.0, color=INK)
    ctx.restore()

    for Ev in (5, 10, 15, 20, 24):
        draw_text(ctx, f"{Ev}", bx_m(float(Ev)), r1_y + r1_h + 24, size=13.5, color=INK, align="center")
    draw_text(ctx, "31P+ Implant Energy E_0 (keV)", c2_x + c2_w / 2.0, r1_y + r1_h + 52, size=15.0, bold=True, color=INK, align="center")
    for nv in (0, 2, 4, 6, 8, 10, 12, 14, 16):
        draw_text(ctx, f"{nv}", c2_x - 10, by_m(float(nv)) + 5, size=13.0, color=INK, align="right")
    draw_text(ctx, "Range / Straggle (nm)", c2_x - 52, r1_y + r1_h / 2.0, size=14.5, bold=True, color=INK, align="center", angle=-math.pi / 2.0)

    # =========================================================================
    # PANEL C (Top-Right): Final Donor Depth Ensembles P(z_final)
    # =========================================================================
    draw_panel(ctx, c3_x, r1_y, c3_w, r1_h, "C. Final 31P Depth Distribution P(z_final) vs M4 Window")
    zc = pdata["z_hist_centers_nm"]
    z_min, z_max = 0.0, 35.0
    p_min, p_max = 0.0, 0.165

    def cx_m(z: float) -> float:
        return c3_x + (z - z_min) / (z_max - z_min) * c3_w

    def cy_m(p: float) -> float:
        return r1_y + r1_h - (p - p_min) / (p_max - p_min) * r1_h

    ctx.save()
    ctx.rectangle(c3_x + 1, r1_y + 1, c3_w - 2, r1_h - 2)
    ctx.clip()

    # No-barrier zone z < 8.5 nm (light red)
    ctx.set_source_rgba(0.78, 0.14, 0.18, 0.10)
    ctx.rectangle(c3_x, r1_y, cx_m(8.5) - c3_x, r1_h)
    ctx.fill()
    draw_text(ctx, "z < 8.5 nm", cx_m(4.25), r1_y + 24, size=12.2, bold=True, color=C_RED, align="center")
    draw_text(ctx, "(No Barrier)", cx_m(4.25), r1_y + 40, size=11.5, color=C_RED, align="center")

    # M4 Tosi Flip-Flop sweet spot 11.5..17.5 nm (light green)
    ctx.set_source_rgba(0.05, 0.60, 0.40, 0.12)
    ctx.rectangle(cx_m(11.5), r1_y, cx_m(17.5) - cx_m(11.5), r1_h)
    ctx.fill()
    draw_text(ctx, "M4 Sweet Spot", cx_m(14.5), r1_y + 24, size=12.5, bold=True, color=(0.03, 0.44, 0.28), align="center")
    draw_text(ctx, "(11.5-17.5 nm)", cx_m(14.5), r1_y + 40, size=11.5, color=(0.03, 0.44, 0.28), align="center")

    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.0)
    for zv in (5, 10, 15, 20, 25, 30):
        ctx.move_to(cx_m(float(zv)), r1_y)
        ctx.line_to(cx_m(float(zv)), r1_y + r1_h)
        ctx.stroke()
    for pv in (0.04, 0.08, 0.12, 0.16):
        ctx.move_to(c3_x, cy_m(pv))
        ctx.line_to(c3_x + c3_w, cy_m(pv))
        ctx.stroke()

    # Vertical dashed line at z = 8.5 nm
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.6)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(cx_m(8.5), r1_y)
    ctx.line_to(cx_m(8.5), r1_y + r1_h)
    ctx.stroke()
    ctx.set_dash([])

    y_all = exp["route_flipflop_yields_exp131"]
    hist_specs = [
        ("z_hist_bare_5keV", C_GRAY, 2.2, [6.0, 4.0], f"Bare 5 keV (z={y_all['bare_5keV_uncapped_ref']['mean_z_nm']:.1f} nm, {y_all['bare_5keV_uncapped_ref']['yield_C_ge_100']*100:.1f}%)"),
        ("z_hist_route_A_v5_5keV_8nm", C_EMERALD, 3.4, [], f"Route A/C v5 5keV+8nm (z={y_all['route_A_v5_1530K_5keV_8nm_mbe']['mean_z_nm']:.1f} nm, {y_all['route_C_v5_1530K_5keV_8nm_FG350C']['yield_C_ge_100']*100:.1f}%)"),
        ("z_hist_route_B_22keV", C_RED, 2.8, [], f"Route B 22keV thru-cap (sig_z={y_all['route_B_22keV_through_cap_flash']['std_z_nm']:.1f}, {y_all['route_B_22keV_through_cap_flash']['yield_C_ge_100']*100:.1f}%)"),
        ("z_hist_14keV_8nm", C_PURPLE, 2.6, [3.0, 3.0], f"14 keV+8nm (z={y_all['route_A_14keV_srim_15nm_plus_8nm_cap']['mean_z_nm']:.1f} nm, {y_all['route_A_14keV_srim_15nm_plus_8nm_cap']['yield_C_ge_100']*100:.1f}%)"),
    ]
    for key, col, lw, dash, _ in hist_specs:
        vals = pdata[key]
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        for k, (zv, pv) in enumerate(zip(zc, vals)):
            if zv > z_max:
                break
            xx, yy = cx_m(zv), cy_m(pv)
            if k == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        ctx.restore()

    # Legend top-right
    lx_c, ly_c = c3_x + c3_w - 318, r1_y + 52
    ctx.set_source_rgba(1, 1, 1, 0.94)
    ctx.rectangle(lx_c, ly_c, 308, 108)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.stroke()
    for idx_k, (_, col, lw, dash, lbl) in enumerate(hist_specs):
        yy = ly_c + 18 + idx_k * 24
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(lx_c + 10, yy)
        ctx.line_to(lx_c + 38, yy)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, lbl, lx_c + 44, yy + 4, size=11.4, color=INK)
    ctx.restore()

    for zv in (0, 5, 10, 15, 20, 25, 30, 35):
        draw_text(ctx, f"{zv}", cx_m(float(zv)), r1_y + r1_h + 24, size=13.5, color=INK, align="center")
    draw_text(ctx, "Final Donor Depth Below Si/SiO2 Interface z_final (nm)", c3_x + c3_w / 2.0, r1_y + r1_h + 52, size=15.0, bold=True, color=INK, align="center")
    for pv in (0.0, 0.04, 0.08, 0.12, 0.16):
        draw_text(ctx, f"{pv:.2f}", c3_x - 10, cy_m(pv) + 5, size=13.0, color=INK, align="right")
    draw_text(ctx, "Probability Density (1/nm)", c3_x - 56, r1_y + r1_h / 2.0, size=14.5, bold=True, color=INK, align="center", angle=-math.pi / 2.0)

    # =========================================================================
    # PANEL D (Bottom-Left): McWhorter 2D Image-Charge S_eps(D_it) -> Exp137 Bridge
    # =========================================================================
    draw_panel(ctx, c1_x, r2_y, c1_w, r2_h, "D. 2D Image-Charge McWhorter S_eps(D_it) — Bridge to Exp137")
    dcurve = pdata["dit_curve"]
    ld_min, ld_max = math.log10(5.0e9), math.log10(4.0e11)
    s_min, s_max = 0.0, 2.05

    def dx_m(dit: float) -> float:
        return c1_x + (math.log10(dit) - ld_min) / (ld_max - ld_min) * c1_w

    def dy_m(s: float) -> float:
        return r2_y + r2_h - (s - s_min) / (s_max - s_min) * r2_h

    ctx.save()
    ctx.rectangle(c1_x + 1, r2_y + 1, c1_w - 2, r2_h - 2)
    ctx.clip()

    # Shaded green Exp131/137 fault-tolerant low-noise band S_eps <= 0.45 ueV/rtHz
    ctx.set_source_rgba(0.05, 0.60, 0.40, 0.13)
    ctx.rectangle(c1_x, dy_m(0.45), c1_w, dy_m(0.0) - dy_m(0.45))
    ctx.fill()
    draw_text(ctx, "Exp131/137 Target Low-Noise Band (S_eps <= 0.45 ueV/rtHz)", c1_x + c1_w - 10, dy_m(0.10), size=12.2, bold=True, color=(0.03, 0.44, 0.28), align="right")

    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.0)
    for dtv in (1e10, 3e10, 1e11, 3e11):
        ctx.move_to(dx_m(dtv), r2_y)
        ctx.line_to(dx_m(dtv), r2_y + r2_h)
        ctx.stroke()
    for sv in (0.4, 0.8, 1.0, 1.2, 1.6, 2.0):
        ctx.move_to(c1_x, dy_m(sv))
        ctx.line_to(c1_x + c1_w, dy_m(sv))
        ctx.stroke()

    # Baseline 1.0 ueV/rtHz horizontal reference
    ctx.set_source_rgb(*MUTED)
    ctx.set_line_width(1.5)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(c1_x, dy_m(1.0))
    ctx.line_to(c1_x + c1_w, dy_m(1.0))
    ctx.stroke()
    ctx.set_dash([])
    draw_text(ctx, "Exp131 Baseline S_eps = 1.0 ueV/rtHz", c1_x + 12, dy_m(1.0) + 17, size=11.8, bold=True, color=MUTED)

    # Curve d_ox = 8 nm (navy) and d_ox = 5 nm (teal dashed)
    ctx.set_source_rgb(*C_NAVY)
    ctx.set_line_width(3.2)
    for k, pt in enumerate(dcurve):
        xx, yy = dx_m(pt["D_it_cm2_eV"]), dy_m(pt["S_eps_dox8_ueV"])
        if k == 0:
            ctx.move_to(xx, yy)
        else:
            ctx.line_to(xx, yy)
    ctx.stroke()

    ctx.set_source_rgb(*C_TEAL)
    ctx.set_line_width(2.5)
    ctx.set_dash([6.0, 4.0])
    for k, pt in enumerate(dcurve):
        xx, yy = dx_m(pt["D_it_cm2_eV"]), dy_m(pt["S_eps_dox5_ueV"])
        if k == 0:
            ctx.move_to(xx, yy)
        else:
            ctx.line_to(xx, yy)
    ctx.stroke()
    ctx.set_dash([])

    # Plot route points dynamically (clean non-overlapping labels)
    cnr = exp["charge_noise_and_exp137_bridge"]["routes"]
    pts_d = [
        (cnr["route_B_22keV_through_cap"]["D_it_eff_cm2_eV"], cnr["route_B_22keV_through_cap"]["S_eps_ueV_rtHz"], C_RED, "Route B (Thru-Cap)", (-14, -14), "right"),
        (cnr["route_A_5keV_post_anneal_mbe_unpassivated"]["D_it_eff_cm2_eV"], cnr["route_A_5keV_post_anneal_mbe_unpassivated"]["S_eps_ueV_rtHz"], C_AMBER, "Route A (Unpassiv.)", (-14, -16), "right"),
        (cnr["route_C_nominal_FG350C_Dit_1p5e10"]["D_it_eff_cm2_eV"], cnr["route_C_nominal_FG350C_Dit_1p5e10"]["S_eps_ueV_rtHz"], C_EMERALD, "Route C (FG 350C)", (-48, -68), "left"),
        (cnr["route_C_thin_oxide_Dit_1p0e10_dox5"]["D_it_eff_cm2_eV"], cnr["route_C_thin_oxide_Dit_1p0e10_dox5"]["S_eps_ueV_rtHz"], C_TEAL, "Route C (5nm ox)", (14, 18), "left"),
    ]
    for dit_v, s_v, col, lbl, (ox_t, oy_t), al in pts_d:
        px_d, py_d = dx_m(dit_v), dy_m(s_v)
        ctx.set_source_rgb(*col)
        ctx.arc(px_d, py_d, 7.5, 0, 2 * math.pi)
        ctx.fill_preserve()
        ctx.set_source_rgb(1, 1, 1)
        ctx.set_line_width(1.8)
        ctx.stroke()
        if "FG 350C" in lbl:
            ctx.set_source_rgb(*col)
            ctx.set_line_width(1.4)
            ctx.move_to(px_d, py_d - 9)
            ctx.line_to(px_d - 14, py_d - 58)
            ctx.stroke()
        draw_text(ctx, f"{lbl}: {s_v:.3f}", px_d + ox_t, py_d + oy_t, size=12.2, bold=True, color=col, align=al)

    # Legend top-left
    lx_d, ly_d = c1_x + 14, r2_y + 14
    ctx.set_source_rgba(1, 1, 1, 0.94)
    ctx.rectangle(lx_d, ly_d, 265, 58)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.stroke()
    ctx.set_source_rgb(*C_NAVY)
    ctx.set_line_width(3.0)
    ctx.move_to(lx_d + 10, ly_d + 18)
    ctx.line_to(lx_d + 40, ly_d + 18)
    ctx.stroke()
    draw_text(ctx, "d_ox = 8 nm (Nominal MOS)", lx_d + 46, ly_d + 22, size=12.0, color=INK)
    ctx.set_source_rgb(*C_TEAL)
    ctx.set_line_width(2.5)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(lx_d + 10, ly_d + 42)
    ctx.line_to(lx_d + 40, ly_d + 42)
    ctx.stroke()
    ctx.set_dash([])
    draw_text(ctx, "d_ox = 5 nm (Tight Screening)", lx_d + 46, ly_d + 46, size=12.0, color=INK)
    ctx.restore()

    for dtv, lbl in [(5e9, "5e9"), (1e10, "1e10"), (3e10, "3e10"), (1e11, "1e11"), (3e11, "3e11")]:
        draw_text(ctx, lbl, dx_m(dtv), r2_y + r2_h + 24, size=13.0, color=INK, align="center")
    draw_text(ctx, "Effective Si/SiO2 Interface Trap Density D_it,eff (cm-2 eV-1, log)", c1_x + c1_w / 2.0, r2_y + r2_h + 52, size=14.5, bold=True, color=INK, align="center")
    for sv in (0.0, 0.4, 0.8, 1.2, 1.6, 2.0):
        draw_text(ctx, f"{sv:.1f}", c1_x - 10, dy_m(sv) + 5, size=13.0, color=INK, align="right")
    draw_text(ctx, "1/f Charge Noise S_eps (ueV / rtHz)", 32, r2_y + r2_h / 2.0, size=14.5, bold=True, color=INK, align="center", angle=-math.pi / 2.0)

    # =========================================================================
    # PANEL E (Bottom-Mid): Head-to-Head Exp131 4x4 Flip-Flop Yield (N=2,000)
    # =========================================================================
    draw_panel(ctx, c2_x, r2_y, c2_w, r2_h, "E. Coupled Exp131 4x4 Tosi Flip-Flop Yield P(C >= 100)")
    e_rows = [
        ("Route C v5 (1530K+FG)", y_all["route_C_v5_1530K_5keV_8nm_FG350C"], C_EMERALD),
        ("Route A v5 (1530K MBE)", y_all["route_A_v5_1530K_5keV_8nm_mbe"], C_TEAL),
        ("Route A v4 (1440K TED!)", y_all["route_A_v4_1440K_5keV_8nm_mbe"], C_BLUE),
        ("Route B (20keV thru-cap)", y_all["route_B_20keV_through_cap_flash"], C_AMBER),
        ("Route B (22keV thru-cap)", y_all["route_B_22keV_through_cap_flash"], C_ORANGE),
        ("14 keV (15nm)+8nm Cap", y_all["route_A_14keV_srim_15nm_plus_8nm_cap"], C_PURPLE),
        ("Bare 5 keV (Uncapped)", y_all["bare_5keV_uncapped_ref"], C_RED),
    ]
    ex0 = c2_x + 190.0
    ew_b = c2_w - 208.0

    def ex_m(pct: float) -> float:
        return ex0 + (pct / 138.0) * ew_b

    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.0)
    for pv in (0, 25, 50, 75, 100):
        gx = ex_m(float(pv))
        ctx.move_to(gx, r2_y + 18)
        ctx.line_to(gx, r2_y + r2_h - 36)
        ctx.stroke()
        draw_text(ctx, f"{pv}%", gx, r2_y + r2_h - 14, size=12.8, color=INK, align="center")

    # 93% EP3 threshold dashed line
    x93 = ex_m(93.0)
    ctx.save()
    ctx.set_source_rgb(*C_EMERALD)
    ctx.set_line_width(1.8)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(x93, r2_y + 16)
    ctx.line_to(x93, r2_y + r2_h - 36)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "93% target", x93 + 6, r2_y + 30, size=11.8, bold=True, color=(0.03, 0.44, 0.28), align="left")

    rh_e = (r2_h - 72.0) / len(e_rows)
    for idx_r, (lbl, row, col) in enumerate(e_rows):
        ry = r2_y + 38.0 + idx_r * rh_e
        hb = rh_e - 22.0
        pct = row["yield_C_ge_100"] * 100.0
        wb = max(4.0, ex_m(pct) - ex0)
        ctx.set_source_rgb(*col)
        ctx.rectangle(ex0, ry, wb, hb)
        ctx.fill()
        draw_text(ctx, lbl, ex0 - 10, ry + hb / 2.0 + 4, size=12.0, bold=(idx_r <= 1), color=INK, align="right")
        medC = row["median_C_tuned"]
        gphi = row["certified_median_gamma_phi_khz"]
        txt_val = f"{pct:.1f}% (C={medC:,.0f}, g_phi={gphi:.1f}k)" if medC >= 10 else f"{pct:.1f}% (C={medC:.1f})"
        if pct > 75.0:
            draw_text(ctx, txt_val, ex0 + 10, ry + hb / 2.0 + 4, size=11.5, bold=True, color=(1, 1, 1))
        else:
            draw_text(ctx, txt_val, ex0 + wb + 8, ry + hb / 2.0 + 4, size=11.2, bold=True, color=INK)

    draw_text(ctx, "M4 Strong-Coupling Yield P(C >= 100)  (3 kOhm, Q_L=2e5, N=2k)", c2_x + c2_w / 2.0, r2_y + r2_h + 52, size=14.0, bold=True, color=INK, align="center")

    # =========================================================================
    # PANEL F (Bottom-Right): S5.6 Hardware Integration & CAD v5.0 / BOM v5.0 Card
    # =========================================================================
    draw_panel(ctx, c3_x, r2_y, c3_w, r2_h, "F. S5.6 In-Situ 28Si UHV MBE Capper (CAD v5.0 / BOM v5.0)")
    s56 = exp["s56_hardware_spec"]
    th_all = exp["coupled_thermal_chain_ted"]
    th_v4 = th_all["v4_1x1440K_41p15J_unmitigated"]
    th_v5 = th_all["v5_1x1530K_43p49J_cluster_clearing"]

    # Top half: clean engineering cross-section schematic (Main DR Chamber | Gate Valve | Load-Lock + S5.6 CF100)
    sy0 = r2_y + 18.0
    # Main 20 mK Chamber (left block)
    ctx.set_source_rgba(0.14, 0.44, 0.78, 0.14)
    ctx.rectangle(c3_x + 22, sy0 + 75, 165, 145)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_NAVY)
    ctx.set_line_width(1.8)
    ctx.stroke()
    draw_text(ctx, "S5.1 / S6 Main", c3_x + 104, sy0 + 132, size=13.0, bold=True, color=C_NAVY, align="center")
    draw_text(ctx, "20 mK DR Chamber", c3_x + 104, sy0 + 150, size=12.0, color=C_NAVY, align="center")
    draw_text(ctx, "(X=0, Z=500 mm)", c3_x + 104, sy0 + 168, size=11.2, color=MUTED, align="center")
    draw_text(ctx, "Cryo Leak = 0.00 uW", c3_x + 104, sy0 + 196, size=12.0, bold=True, color=C_EMERALD, align="center")

    # UHV Gate Valve duct between Main and Load-Lock
    ctx.set_source_rgb(0.84, 0.87, 0.90)
    ctx.rectangle(c3_x + 187, sy0 + 130, 95, 36)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.4)
    ctx.stroke()
    # Red vertical gate valve bar
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(4.0)
    ctx.move_to(c3_x + 234, sy0 + 118)
    ctx.line_to(c3_x + 234, sy0 + 178)
    ctx.stroke()
    draw_text(ctx, "Gate Valve", c3_x + 234, sy0 + 108, size=11.0, bold=True, color=C_RED, align="center")
    draw_text(ctx, "Clr=119 mm", c3_x + 234, sy0 + 198, size=10.8, color=MUTED, align="center")

    # S5.3 Load-Lock Chamber (right-center)
    ctx.set_source_rgba(0.05, 0.60, 0.40, 0.10)
    ctx.rectangle(c3_x + 282, sy0 + 95, 195, 125)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.8)
    ctx.stroke()
    draw_text(ctx, "S5.3 Load-Lock (X=420)", c3_x + 380, sy0 + 122, size=12.0, bold=True, color=INK, align="center")
    # Wafer + PBN heater platen inside Load-Lock
    ctx.set_source_rgb(*C_AMBER)
    ctx.rectangle(c3_x + 332, sy0 + 168, 96, 12)
    ctx.fill()
    draw_text(ctx, f"Wafer + PBN ({mbe_opt['T_epi_C']:.0f} C)", c3_x + 380, sy0 + 202, size=11.0, bold=True, color=C_AMBER, align="center")

    # S5.6 CF100 MBE Capper mounted on TOP (+Z) of Load-Lock!
    ctx.set_source_rgba(0.05, 0.60, 0.40, 0.25)
    ctx.rectangle(c3_x + 322, sy0 + 8, 116, 87)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_EMERALD)
    ctx.set_line_width(2.2)
    ctx.stroke()
    draw_text(ctx, "S5.6 CF100 MBE", c3_x + 380, sy0 + 34, size=12.5, bold=True, color=(0.03, 0.42, 0.28), align="center")
    draw_text(ctx, "28Si Subl. Source", c3_x + 380, sy0 + 52, size=11.5, color=INK, align="center")
    draw_text(ctx, "Z=585..865 mm", c3_x + 380, sy0 + 70, size=11.0, color=MUTED, align="center")
    # Deposition flux cone arrows
    ctx.set_source_rgba(0.05, 0.60, 0.40, 0.45)
    ctx.set_line_width(1.6)
    ctx.set_dash([4.0, 3.0])
    ctx.move_to(c3_x + 365, sy0 + 95)
    ctx.line_to(c3_x + 340, sy0 + 166)
    ctx.move_to(c3_x + 395, sy0 + 95)
    ctx.line_to(c3_x + 420, sy0 + 166)
    ctx.stroke()
    ctx.set_dash([])

    # Transfer arm (+X)
    ctx.set_source_rgb(0.82, 0.85, 0.88)
    ctx.rectangle(c3_x + 477, sy0 + 144, 175, 22)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.4)
    ctx.stroke()
    draw_text(ctx, "S5.3 Transfer Arm (+X)", c3_x + 564, sy0 + 136, size=11.2, bold=True, color=INK, align="center")
    draw_text(ctx, f"Vert. Clr = {s56['cad_v5_geometry']['clearances_vs_cad_v4_mm']['vs_s5_transfer_arm_mm']:.0f} mm", c3_x + 564, sy0 + 186, size=11.2, color=MUTED, align="center")

    # Bottom half: crisp structured specification table
    ty0 = r2_y + 258.0
    spec_rows = [
        ("CAD v5.0 Port & Clearance", f"CF100 +Z on Load-Lock (Ø152x280 mm), min clr = {s56['cad_v5_geometry']['clearances_vs_cad_v4_mm']['min_clearance_mm']:.1f} mm"),
        ("28Si Cap Process (Route C)", f"8.0 nm @ 0.10 nm/s (80 s), T_epi*={mbe_opt['T_epi_C']:.0f} C + 350 C / 15m FG/H"),
        ("UHV Vacuum & Purity", f"P_base={s56['vacuum_and_deposition']['base_pressure_torr']:.1e} Torr, P_growth={s56['vacuum_and_deposition']['growth_pressure_torr']:.1e} Torr (<50 ppm 29Si)"),
        ("Mass / Power / Cryo Leak", f"Mass = {s56['mass_power_cryo']['total_mass_kg']:.1f} kg | 400 W growth | Cryo 20 mK leak = 0.00 uW"),
        ("BOM v5.0 Cost ({Varsayim})", f"P50 = ${s56['bom_v5_cost_estimate_usd']['total_p50_usd']:,} (P10 $67k / P90 $145k; +{s56['bom_v5_cost_estimate_usd']['pct_of_v4_m3_hw_bom']:.2f}% of v4.0 M3)"),
        ("Exp134 Throughput Impact", f"Pipelined: 0.0% penalty (Route C {s56['wafer_throughput_impact_exp134']['route_C_loadlock_time_min']:.1f}m < 73m M4 cycle)"),
        ("v4 1440K Back-End TED (!)", f"{th_v4['cluster_remaining_frac_post_flash']*100:.1f}% {{311}} left -> sig_ann={th_v4['route_C_full_chain']['sigma_anneal_nm']:.2f} nm (EP5 FAIL!)"),
        ("v5 1530K Fix (43.5 J/cm2)", f"99.99% clear -> sig_ann={th_v5['route_C_full_chain']['sigma_anneal_nm']:.3f} nm | Exp124={th_all['exp124_sigma_tot_v5_1530K_chain_nm']:.3f} nm"),
    ]
    for idx_s, (k_txt, v_txt) in enumerate(spec_rows):
        yy = ty0 + idx_s * 31.0
        if idx_s % 2 == 0:
            ctx.set_source_rgba(0.92, 0.94, 0.97, 0.65)
            ctx.rectangle(c3_x + 14, yy - 17, c3_w - 28, 27)
            ctx.fill()
        k_col = C_RED if "FAIL" in v_txt else (C_EMERALD if "v5 1530K" in k_txt else C_NAVY)
        draw_text(ctx, k_txt, c3_x + 20, yy, size=12.0, bold=True, color=k_col)
        draw_text(ctx, v_txt, c3_x + 230, yy, size=11.8, color=INK)

    # Bottom footer strip
    verdict_str = f"PRE-REGISTERED: {exp['pre_registered_pass_count']}/{exp['pre_registered_total_count']} PASS (EP1,2,4,6 PASS; honest EP3,5 FAIL @ v4 1440K -> SOLVED by v5 1530K 43.5 J/cm2!)  |  Exp137 Bridge: S_eps 1.00 -> {cnr['route_C_nominal_FG350C_Dit_1p5e10']['S_eps_ueV_rtHz']:.3f} ueV/rtHz"
    draw_text(ctx, verdict_str, 48, H - 24, size=13.5, bold=True, color=MUTED)

    surf.write_to_png(str(OUT_PNG))
    print(f"Wrote {OUT_PNG.relative_to(REPO_ROOT)} ({W}x{H})")


def main() -> None:
    exp = json.loads(EXP_JSON.read_text(encoding="utf-8"))
    pdata = json.loads(PLOT_JSON.read_text(encoding="utf-8"))
    render_dashboard(exp, pdata)


if __name__ == "__main__":
    main()
