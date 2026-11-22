"""Exp124 Publication-Grade PyCairo + PIL Figure Generator.

Run with system Python (has cairo + PIL 12.3):
    /usr/bin/python3 -B experiments/exp124_ion_column_optics/plot_exp124.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp124_ion_column_optics"


# Clean colorblind-safe engineering palette (RGB in 0..1)
C_BG = (0.985, 0.988, 0.994)
C_PANEL = (1.0, 1.0, 1.0)
C_BORDER = (0.78, 0.82, 0.88)
C_GRID = (0.91, 0.93, 0.96)
C_TEXT = (0.11, 0.14, 0.20)
C_MUTED = (0.40, 0.45, 0.54)
C_BLUE = (0.11, 0.39, 0.72)
C_TEAL = (0.04, 0.56, 0.52)
C_GREEN = (0.13, 0.58, 0.28)
C_ORANGE = (0.85, 0.44, 0.08)
C_RED = (0.78, 0.17, 0.18)
C_PURPLE = (0.48, 0.24, 0.68)
C_GRAY = (0.45, 0.49, 0.56)


def set_font(ctx: cairo.Context, size: float, bold: bool = False) -> None:
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)


def draw_text(ctx: cairo.Context, text: str, x: float, y: float, size: float = 12,
              color=C_TEXT, bold: bool = False, align: str = "left", angle: float = 0.0) -> None:
    ctx.save()
    set_font(ctx, size, bold)
    ctx.set_source_rgb(*color)
    ext = ctx.text_extents(text)
    ctx.translate(x, y)
    if angle != 0.0:
        ctx.rotate(angle)
    dx = 0.0
    if align == "center":
        dx = -ext.width / 2.0 - ext.x_bearing
    elif align == "right":
        dx = -ext.width - ext.x_bearing
    ctx.move_to(dx, 0.0)
    ctx.show_text(text)
    ctx.restore()


def draw_panel_box(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str) -> None:
    ctx.save()
    ctx.set_source_rgb(*C_PANEL)
    ctx.rectangle(x, y, w, h)
    ctx.fill()
    ctx.set_source_rgb(*C_BORDER)
    ctx.set_line_width(1.3)
    ctx.rectangle(x, y, w, h)
    ctx.stroke()
    draw_text(ctx, title, x + 14, y + 24, size=14.5, color=C_TEXT, bold=True)
    ctx.restore()


def map_x(val: float, vmin: float, vmax: float, px0: float, pw: float) -> float:
    return px0 + (val - vmin) / max(vmax - vmin, 1e-12) * pw


def map_y(val: float, vmin: float, vmax: float, py0: float, ph: float) -> float:
    return py0 + ph - (val - vmin) / max(vmax - vmin, 1e-12) * ph


def draw_axes_and_grid(
    ctx: cairo.Context, px0: float, py0: float, pw: float, ph: float,
    xmin: float, xmax: float, xticks: list[float],
    ymin: float, ymax: float, yticks: list[float],
    xlabel: str, ylabel: str, xfmt: str = "{:.1f}", yfmt: str = "{:.1f}",
) -> None:
    ctx.save()
    # Grid lines
    ctx.set_line_width(1.0)
    ctx.set_source_rgb(*C_GRID)
    for xt in xticks:
        xx = map_x(xt, xmin, xmax, px0, pw)
        ctx.move_to(xx, py0)
        ctx.line_to(xx, py0 + ph)
        ctx.stroke()
    for yt in yticks:
        yy = map_y(yt, ymin, ymax, py0, ph)
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()

    # Axes frame
    ctx.set_source_rgb(*C_TEXT)
    ctx.set_line_width(1.5)
    ctx.rectangle(px0, py0, pw, ph)
    ctx.stroke()

    # Ticks & labels
    for xt in xticks:
        xx = map_x(xt, xmin, xmax, px0, pw)
        ctx.move_to(xx, py0 + ph)
        ctx.line_to(xx, py0 + ph + 5)
        ctx.stroke()
        draw_text(ctx, xfmt.format(xt), xx, py0 + ph + 19, size=11, color=C_MUTED, align="center")
    for yt in yticks:
        yy = map_y(yt, ymin, ymax, py0, ph)
        ctx.move_to(px0 - 5, yy)
        ctx.line_to(px0, yy)
        ctx.stroke()
        draw_text(ctx, yfmt.format(yt), px0 - 9, yy + 4, size=11, color=C_MUTED, align="right")

    draw_text(ctx, xlabel, px0 + pw / 2.0, py0 + ph + 39, size=12, color=C_TEXT, bold=True, align="center")
    draw_text(ctx, ylabel, px0 - 52, py0 + ph / 2.0, size=12, color=C_TEXT, bold=True, align="center", angle=-math.pi / 2.0)
    ctx.restore()


def draw_polyline(ctx: cairo.Context, xs: list[float], ys: list[float],
                  xmin: float, xmax: float, ymin: float, ymax: float,
                  px0: float, py0: float, pw: float, ph: float,
                  color, width: float = 2.4, dash: list[float] | None = None,
                  markers: bool = False) -> None:
    ctx.save()
    ctx.rectangle(px0, py0, pw, ph)
    ctx.clip()
    ctx.set_source_rgb(*color)
    ctx.set_line_width(width)
    if dash:
        ctx.set_dash(dash)
    started = False
    for xv, yv in zip(xs, ys):
        xx = map_x(xv, xmin, xmax, px0, pw)
        yy = map_y(yv, ymin, ymax, py0, ph)
        if not started:
            ctx.move_to(xx, yy)
            started = True
        else:
            ctx.line_to(xx, yy)
    ctx.stroke()
    if markers:
        ctx.set_dash([])
        for xv, yv in zip(xs, ys):
            xx = map_x(xv, xmin, xmax, px0, pw)
            yy = map_y(yv, ymin, ymax, py0, ph)
            ctx.arc(xx, yy, 4.0, 0, 2 * math.pi)
            ctx.fill()
    ctx.restore()


def make_optics_figure(data: dict) -> None:
    W, H = 1800, 1080
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*C_BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Header banner
    draw_text(ctx, "Exp124 — 10->5 keV Yavaslatmali Iyon Kolonu Optigi, Liouville Kapanisi & Calisma Penceresi",
              28, 34, size=20, color=C_TEXT, bold=True)
    draw_text(ctx, "2B Eksenel-Simetrik Laplace (spsolve) + DOP853 Isin Izleme + Exp72 IBIC + Exp92 BCA  |  no_lab_measurement=True {Model/Sayisal-Simulasyon}",
              28, 56, size=12, color=C_MUTED)

    # 2x2 Panel grid
    pad = 24
    top = 74
    pw_box = (W - 3 * pad) / 2.0
    ph_box = (H - top - 2 * pad) / 2.0

    # =========================================================================
    # PANEL A (Top-Left): Arch-B Axial Potential Phi0(z) & Retarding Field |Ez(z)|
    # =========================================================================
    ax, ay = pad, top
    draw_panel_box(ctx, ax, ay, pw_box, ph_box, "A) Arch-B (0.5 mm Adim, 10->5 keV) Eksenel Potansiyel & Alan")
    px0, py0, pw, ph = ax + 76, ay + 46, pw_box - 148, ph_box - 102
    lp = data["lens_profiles"]["ArchB"]
    zs = lp["z_mm"]
    phis = lp["phi0_kV"]
    ezs = lp["Ez_MV_m"]
    zmax = max(zs)
    draw_axes_and_grid(ctx, px0, py0, pw, ph, 0.0, zmax, [0.0, 0.4, 0.8, 1.2, 1.6, 2.0],
                       0.0, 12.0, [0, 2, 4, 6, 8, 10, 12],
                       "Eksenel Konum z (mm)  [Wafer z = 2.0 mm]", "Potansiyel Phi_0 (kV)",
                       xfmt="{:.1f}", yfmt="{:.0f}")

    # Shade electrode z-bands (Arch-B: E1=0.20-0.30, E2=1.12-1.28, E3=1.66-1.76 mm)
    ctx.save()
    ctx.set_source_rgba(0.55, 0.62, 0.72, 0.22)
    for (z0, z1) in [(0.20, 0.30), (1.12, 1.28), (1.66, 1.76)]:
        x0 = map_x(z0, 0.0, zmax, px0, pw)
        x1 = map_x(z1, 0.0, zmax, px0, pw)
        ctx.rectangle(x0, py0, x1 - x0, ph)
        ctx.fill()
    ctx.restore()

    # Right axis for |Ez| (0..18 MV/m)
    ez_max_axis = 18.0
    for yt in [0, 3, 6, 9, 12, 15, 18]:
        yy = map_y(yt, 0.0, ez_max_axis, py0, ph)
        ctx.set_source_rgb(*C_ORANGE)
        ctx.set_line_width(1.2)
        ctx.move_to(px0 + pw, yy)
        ctx.line_to(px0 + pw + 5, yy)
        ctx.stroke()
        draw_text(ctx, f"{yt}", px0 + pw + 9, yy + 4, size=11, color=C_ORANGE)
    draw_text(ctx, "|E_z| Eksenel Alan (MV/m)", px0 + pw + 48, py0 + ph / 2.0,
              size=12, color=C_ORANGE, bold=True, align="center", angle=math.pi / 2.0)

    # UHV safe limit line at 12 MV/m on right axis
    y_uhv = map_y(12.0, 0.0, ez_max_axis, py0, ph)
    ctx.save()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.5)
    ctx.set_dash([6, 4])
    ctx.move_to(px0, y_uhv)
    ctx.line_to(px0 + pw, y_uhv)
    ctx.stroke()
    draw_text(ctx, "UHV guvenli sinir (12 MV/m)", px0 + 8, y_uhv - 6, size=10.5, color=C_RED, bold=True)
    ctx.restore()

    draw_polyline(ctx, zs, phis, 0.0, zmax, 0.0, 12.0, px0, py0, pw, ph, C_BLUE, width=2.8)
    draw_polyline(ctx, zs, ezs, 0.0, zmax, 0.0, ez_max_axis, px0, py0, pw, ph, C_ORANGE, width=2.2)

    # Legend / metrics inset
    draw_text(ctx, f"Phi_0(z) [kV]   (10 -> 5 keV)", px0 + 10, py0 + 20, size=11, color=C_BLUE, bold=True)
    draw_text(ctx, f"|E_z(z)| [MV/m] (E_gap={lp['E_gap_MV_m']:.2f} MV/m)", px0 + 10, py0 + 36, size=11, color=C_ORANGE, bold=True)
    draw_text(ctx, f"Cc={lp['Cc_mm']:.3f} mm | Cs={lp['Cs_mm']:.2f} mm | WD={lp['WD_mm']:.2f} mm",
              px0 + 10, py0 + ph - 12, size=11, color=C_TEXT, bold=True)

    # =========================================================================
    # PANEL B (Top-Right): Spot Size vs Landing Semi-Angle alpha_land (5 keV)
    # =========================================================================
    bx, by = 2 * pad + pw_box, top
    draw_panel_box(ctx, bx, by, pw_box, ph_box, "B) 5 keV Liouville-Tam Nokta Boyutu vs. Inis Yarim-Acisi (Arch-B, 10.6 MV/m)")
    px0, py0, pw, ph = bx + 76, by + 46, pw_box - 104, ph_box - 102
    ac = data["alpha_curves"]
    als = ac["alpha_mrad"]
    draw_axes_and_grid(ctx, px0, py0, pw, ph, 3.0, 20.0, [3, 5, 7, 9, 11, 13, 15, 17, 19],
                       0.0, 6.0, [0.0, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0],
                       "Inis Yarim-Acisi alpha_land (mrad)", "Nokta Yaricapi sigma_spot (nm)",
                       xfmt="{:.0f}", yfmt="{:.1f}")

    # Target 1.5 nm line
    y_15 = map_y(1.5, 0.0, 6.0, py0, ph)
    ctx.save()
    ctx.set_source_rgb(*C_GREEN)
    ctx.set_line_width(1.6)
    ctx.set_dash([6, 4])
    ctx.move_to(px0, y_15)
    ctx.line_to(px0 + pw, y_15)
    ctx.stroke()
    draw_text(ctx, "P91 hedefi: sigma_spot <= 1.50 nm", px0 + pw - 8, y_15 - 6, size=10.5, color=C_GREEN, bold=True, align="right")
    ctx.restore()

    draw_polyline(ctx, als, [r["sigma_spot_nm"] for r in ac["ArchB_naive_2eV_1ms"]], 3.0, 20.0, 0.0, 6.0, px0, py0, pw, ph, C_RED, width=2.4)
    draw_polyline(ctx, als, [r["sigma_spot_nm"] for r in ac["ArchB_Ti1_25ms"]], 3.0, 20.0, 0.0, 6.0, px0, py0, pw, ph, C_BLUE, width=2.5)
    draw_polyline(ctx, als, [r["sigma_spot_nm"] for r in ac["ArchB_canonical"]], 3.0, 20.0, 0.0, 6.0, px0, py0, pw, ph, C_TEAL, width=2.8)
    # Component curves for canonical (geom, chrom, sph)
    draw_polyline(ctx, als, [r["sigma_geom_nm"] for r in ac["ArchB_canonical"]], 3.0, 20.0, 0.0, 6.0, px0, py0, pw, ph, C_GRAY, width=1.4, dash=[4, 3])
    draw_polyline(ctx, als, [r["sigma_c_nm"] for r in ac["ArchB_canonical"]], 3.0, 20.0, 0.0, 6.0, px0, py0, pw, ph, C_ORANGE, width=1.4, dash=[4, 3])
    draw_polyline(ctx, als, [r["sigma_s_nm"] for r in ac["ArchB_canonical"]], 3.0, 20.0, 0.0, 6.0, px0, py0, pw, ph, C_PURPLE, width=1.4, dash=[2, 3])

    op_n = data["op_points"]["ArchB_naive_2eV_Ti1_1ms"]
    op_t1 = data["op_points"]["ArchB_HiRes_Ti1_25ms"]
    op_can = data["op_points"]["ArchB_HiRes_Ti0p5_15ms"]
    for op, col in [(op_n, C_RED), (op_t1, C_BLUE), (op_can, C_TEAL)]:
        xx = map_x(op["alpha_land_mrad"], 3.0, 20.0, px0, pw)
        yy = map_y(min(op["sigma_spot_nm"], 5.95), 0.0, 6.0, py0, ph)
        ctx.set_source_rgb(*col)
        ctx.arc(xx, yy, 5.2, 0, 2 * math.pi)
        ctx.fill()

    lx, ly = px0 + pw - 335, py0 + 12
    ctx.set_source_rgba(1, 1, 1, 0.93)
    ctx.rectangle(lx, ly, 326, 114)
    ctx.fill()
    ctx.set_source_rgb(*C_BORDER)
    ctx.set_line_width(1.0)
    ctx.rectangle(lx, ly, 326, 114)
    ctx.stroke()
    leg_items = [
        (C_TEAL,  f"Kanonik (0.45eV, Ti=0.5, 15ms): {op_can['sigma_spot_nm']:.2f}nm @{op_can['alpha_land_mrad']:.1f}mrad"),
        (C_BLUE,  f"Tutucu (0.45eV, Ti=1.0, 25ms): {op_t1['sigma_spot_nm']:.2f}nm @{op_t1['alpha_land_mrad']:.1f}mrad"),
        (C_RED,   f"Naif (2.0eV, Ti=1.0, 1ms): {op_n['sigma_spot_nm']:.2f}nm (FAIL)"),
        (C_GRAY,  "Kesikli: Kanonik geom (gri) / Cc (tur.) / Cs (mor)"),
    ]
    for idx, (col, txt) in enumerate(leg_items):
        yy = ly + 20 + idx * 24
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.5)
        ctx.move_to(lx + 10, yy - 4)
        ctx.line_to(lx + 28, yy - 4)
        ctx.stroke()
        draw_text(ctx, txt, lx + 34, yy, size=10.2, color=C_TEXT, bold=(idx < 3))

    # =========================================================================
    # PANEL C (Bottom-Left): Landing Energy Sweep (sigma_tot vs IBIC eta)
    # =========================================================================
    cx, cy = pad, top + ph_box + pad
    draw_panel_box(ctx, cx, cy, pw_box, ph_box, "C) Inis Enerjisi Taramasi (3-10 keV): sigma_toplam vs. Exp72 IBIC Verimi")
    px0, py0, pw, ph = cx + 76, cy + 46, pw_box - 148, ph_box - 102
    es = data["energy_sweep"]
    energies = [3.0, 4.0, 5.0, 6.0, 7.5, 10.0]
    ekeys = [f"E{e:g}" for e in energies]
    draw_axes_and_grid(ctx, px0, py0, pw, ph, 2.5, 10.5, [3, 4, 5, 6, 7, 8, 9, 10],
                       2.5, 7.0, [2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0],
                       "Inis Enerjisi E_land (keV)", "Toplam Yanal Hata sigma_toplam (nm)",
                       xfmt="{:.0f}", yfmt="{:.1f}")

    for yt in [0, 20, 40, 60, 80, 100]:
        yy = map_y(yt, 0.0, 105.0, py0, ph)
        ctx.set_source_rgb(*C_PURPLE)
        ctx.set_line_width(1.2)
        ctx.move_to(px0 + pw, yy)
        ctx.line_to(px0 + pw + 5, yy)
        ctx.stroke()
        draw_text(ctx, f"{yt}%", px0 + pw + 9, yy + 4, size=11, color=C_PURPLE)
    draw_text(ctx, "IBIC Tek-Iyon Verimi eta (C=0.5 pF)", px0 + pw + 52, py0 + ph / 2.0,
              size=12, color=C_PURPLE, bold=True, align="center", angle=math.pi / 2.0)

    ctx.save()
    ctx.set_source_rgba(0.13, 0.58, 0.28, 0.12)
    x5a = map_x(4.75, 2.5, 10.5, px0, pw)
    x5b = map_x(5.25, 2.5, 10.5, px0, pw)
    ctx.rectangle(x5a, py0, x5b - x5a, ph)
    ctx.fill()
    ctx.restore()
    draw_text(ctx, "5 keV optimum", map_x(5.0, 2.5, 10.5, px0, pw), py0 + 16, size=10.5, color=C_GREEN, bold=True, align="center")

    y_38 = map_y(3.80, 2.5, 7.0, py0, ph)
    ctx.save()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.4)
    ctx.set_dash([5, 4])
    ctx.move_to(px0, y_38)
    ctx.line_to(px0 + pw, y_38)
    ctx.stroke()
    draw_text(ctx, "3.80 nm (P91 BCA)", px0 + pw - 6, y_38 - 6, size=10.5, color=C_RED, bold=True, align="right")
    ctx.restore()

    draw_polyline(ctx, energies, [es[k]["ArchB_canonical"]["sigma_total_nm"] for k in ekeys],
                  2.5, 10.5, 2.5, 7.0, px0, py0, pw, ph, C_TEAL, width=2.8, markers=True)
    draw_polyline(ctx, energies, [es[k]["ArchB_Ti1_25ms"]["sigma_total_nm"] for k in ekeys],
                  2.5, 10.5, 2.5, 7.0, px0, py0, pw, ph, C_BLUE, width=2.4, markers=True)
    draw_polyline(ctx, energies, [es[k]["ArchB_naive_2eV_1ms"]["sigma_total_nm"] for k in ekeys],
                  2.5, 10.5, 2.5, 7.0, px0, py0, pw, ph, C_RED, width=2.2, dash=[6, 3], markers=True)
    draw_polyline(ctx, energies, [es[k]["ArchB_canonical"]["eta_ibic"] * 100.0 for k in ekeys],
                  2.5, 10.5, 0.0, 105.0, px0, py0, pw, ph, C_PURPLE, width=2.6, dash=[4, 3], markers=True)

    draw_text(ctx, "Teal: Arch-B Kanonik (0.45eV, 15ms) | Mavi: Ti=1eV, 25ms", px0 + 10, py0 + ph - 28, size=10.5, color=C_TEXT, bold=True)
    draw_text(ctx, "Kirmizi: Naif 2eV/1ms | Mor (sag eksen): IBIC eta (%)", px0 + 10, py0 + ph - 12, size=10.5, color=C_PURPLE, bold=True)

    # =========================================================================
    # PANEL D (Bottom-Right): 5 keV Operating Points Bar Chart & Liouville Closure
    # =========================================================================
    dx, dy = 2 * pad + pw_box, top + ph_box + pad
    draw_panel_box(ctx, dx, dy, pw_box, ph_box, "D) 5 keV Calisma Noktalari Ozeti (Gercek 2B Laplace Cc & Cs ile)")
    px0, py0, pw, ph = dx + 255, dy + 48, pw_box - 285, ph_box - 92

    bar_keys = [
        ("ArchB_HiRes_LMIS_1ms",        "Arch-B + LMIS 10x (0.45eV, 1ms)"),
        ("ArchB_HiRes_Ti0p25_10ms",     "Arch-B 0.5mm (Ti=0.25, 10ms)"),
        ("ArchB_HiRes_Ti0p5_15ms",      "Arch-B Kanonik (Ti=0.5, 15ms)"),
        ("ArchB15_HiRes_Ti0p5_15ms",    "Arch-B15 15->5keV (Ti=0.5, 15ms)"),
        ("ArchB_HiRes_Ti1_25ms",        "Arch-B Tutucu (Ti=1.0, 25ms)"),
        ("ArchD_MEMS35_HiRes_Ti0p5_5ms","Arch-D MEMS 35MV/m (Ti=0.5, 5ms)"),
        ("ArchC_32um_HiRes_Ti0p5_15ms", "Arch-C 32um 10MV/m (Cs=57.7mm)"),
        ("ArchB_naive_2eV_Ti1_1ms",     "Arch-B Naif (2.0eV, Ti=1.0, 1ms)"),
    ]
    n_bars = len(bar_keys)
    xmax_b = 6.6
    for xt in [0.0, 1.0, 1.5, 2.0, 3.0, 3.8, 4.5, 5.5, 6.5]:
        xx = map_x(xt, 0.0, xmax_b, px0, pw)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(xx, py0)
        ctx.line_to(xx, py0 + ph)
        ctx.stroke()
        draw_text(ctx, f"{xt:.1f}", xx, py0 + ph + 16, size=10.5, color=C_MUTED, align="center")
    draw_text(ctx, "1-sigma Deger (nm)  [Koyu: sigma_spot, Acik: sigma_toplam]", px0 + pw / 2.0, py0 + ph + 34,
              size=11.5, color=C_TEXT, bold=True, align="center")

    for ref_v, col, lbl in [(1.50, C_GREEN, "1.50"), (3.80, C_RED, "3.80")]:
        xx = map_x(ref_v, 0.0, xmax_b, px0, pw)
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(1.5)
        ctx.set_dash([5, 3])
        ctx.move_to(xx, py0 - 8)
        ctx.line_to(xx, py0 + ph)
        ctx.stroke()
        draw_text(ctx, lbl, xx, py0 - 11, size=10, color=col, bold=True, align="center")
        ctx.restore()

    row_h = ph / n_bars
    for i, (k, lbl) in enumerate(bar_keys):
        op = data["op_points"][k]
        yc = py0 + (i + 0.5) * row_h
        sp = op["sigma_spot_nm"]
        st = op["sigma_total_nm"]
        ok = (sp <= 1.50 and st <= 3.80 and op["E_gap_nom_MV_m"] <= 12.0)
        col_tot = (0.68, 0.84, 0.80) if ok else (0.93, 0.80, 0.78)
        col_spot = C_TEAL if ok else C_RED

        w_tot = map_x(min(st, xmax_b - 0.1), 0.0, xmax_b, px0, pw) - px0
        ctx.set_source_rgb(*col_tot)
        ctx.rectangle(px0, yc - row_h * 0.34, w_tot, row_h * 0.68)
        ctx.fill()
        w_sp = map_x(min(sp, xmax_b - 0.1), 0.0, xmax_b, px0, pw) - px0
        ctx.set_source_rgb(*col_spot)
        ctx.rectangle(px0, yc - row_h * 0.26, w_sp, row_h * 0.52)
        ctx.fill()

        draw_text(ctx, lbl, px0 - 8, yc + 4, size=10.5, color=C_TEXT, bold=ok, align="right")
        draw_text(ctx, f"{sp:.2f} / {st:.2f} nm", px0 + w_tot + 6, yc + 4, size=10.2,
                  color=C_GREEN if ok else C_RED, bold=True)

    surf.write_to_png(str(OUT_DIR / "fig_exp124_optics_envelope.png"))


def make_anisotropic_yield_figure(data: dict) -> None:
    W, H = 1800, 920
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*C_BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    draw_text(ctx, "Exp124 — Gercek 3B Anizotropik BCA Sacilmasi, Yuzey Kesmesi (z>0) & Stokastik 31P Donor Verim Analizi",
              28, 34, size=19.5, color=C_TEXT, bold=True)
    draw_text(ctx, "Exp42/44/48/57/105 Birebir Cekirdek (N=1024, 400 gercekleme/hucre, %95 Wilson CI)  |  no_lab_measurement=True {Model/Sayisal-Simulasyon}",
              28, 56, size=12, color=C_MUTED)

    pad = 24
    top = 74
    ph_box = H - top - pad
    w_left = 1040
    w_right = W - 3 * pad - w_left

    # =========================================================================
    # PANEL A (Left): Yield Bar Chart with 95% Wilson CI
    # =========================================================================
    draw_panel_box(ctx, pad, top, w_left, ph_box, "A) Mod A Secim Verimi (N=1024): Izotropik Exp105 (%69.25) vs. 3B Anizotropik & Stokastik Donor")
    px0, py0, pw, ph = pad + 335, top + 52, w_left - 410, ph_box - 104
    yc_map = data["yield_cells"]

    rows = [
        ("ANISO_BCA_PURE_N1024",       "Saf BCA (3.25x3.25x2.88, z>0)",       C_GREEN),
        ("ANISO_EXP124_BCA_N1024",     "Exp124 Kolon + BCA (sz=2.88, z>0)",   C_TEAL),
        ("ANISO_P91_BCA_NOSURF_N1024", "P91 + BCA Yuzeysiz (3.80x2.88)",      C_TEAL),
        ("ANISO_P91_BCA_N1024",        "P91 + BCA Yuzeyli (3.80x2.88, z>0)",  C_BLUE),
        ("AUDIT_EXP105_ISO3p8_N1024",  "Exp105 Izotropik Denetim (3.80 iso)", C_GRAY),
        ("ANISO_BCA_HOLMES_N1024",     "Saf BCA xy + Holmes sz=5.27 (z>0)",   C_ORANGE),
        ("ANISO_P91_HOLMES_RP9_N1024", "P91 + Holmes sz=5.27, Rp=9nm (z>0)",  C_ORANGE),
        ("ANISO_P91_HOLMES_NOSURF_N1024", "P91 + Holmes Yuzeysiz (3.80x5.27)", C_ORANGE),
        ("ANISO_P91_HOLMES_N1024",     "P91 + Holmes sz=5.27, Rp=6.5 (z>0)",  C_ORANGE),
        ("AUDIT_EXP57_S5_N1024",       "Exp57 Izotropik Denetim (5.0 iso)",   C_GRAY),
        ("ANISO_EXP124_BCA_DONOR_N1024", "Exp124 + BCA + Stokastik 31P Donor", C_RED),
        ("ANISO_P91_BCA_DONOR_N1024",  "P91 + BCA + Stokastik 31P Donor",     C_RED),
        ("ANISO_P91_HOLMES_DONOR_N1024", "P91 + Holmes + Stokastik 31P Donor", C_RED),
    ]

    for xt in [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        xx = map_x(xt, 0.0, 100.0, px0, pw)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(xx, py0)
        ctx.line_to(xx, py0 + ph)
        ctx.stroke()
        draw_text(ctx, f"{xt}%", xx, py0 + ph + 18, size=11, color=C_MUTED, align="center")
    draw_text(ctx, "Sertifikali Yazmac Secim Verimi (%)  [Hata cubuklari: %95 Wilson guven araligi]",
              px0 + pw / 2.0, py0 + ph + 38, size=12, color=C_TEXT, bold=True, align="center")

    # Exp105 69.25% vertical reference line
    y_ref = yc_map["AUDIT_EXP105_ISO3p8_N1024"]["yield_frac"] * 100.0
    x_ref = map_x(y_ref, 0.0, 100.0, px0, pw)
    ctx.save()
    ctx.set_source_rgb(*C_TEXT)
    ctx.set_line_width(1.6)
    ctx.set_dash([6, 4])
    ctx.move_to(x_ref, py0 - 8)
    ctx.line_to(x_ref, py0 + ph)
    ctx.stroke()
    draw_text(ctx, f"Exp105 Baz: {y_ref:.2f}%", x_ref, py0 - 12, size=11, color=C_TEXT, bold=True, align="center")
    ctx.restore()

    rh = ph / len(rows)
    for i, (key, lbl, col) in enumerate(rows):
        c = yc_map[key]
        val = c["yield_frac"] * 100.0
        lo = c["ci95_lo"] * 100.0
        hi = c["ci95_hi"] * 100.0
        yc = py0 + (i + 0.5) * rh

        bw = map_x(val, 0.0, 100.0, px0, pw) - px0
        ctx.set_source_rgba(col[0], col[1], col[2], 0.85)
        ctx.rectangle(px0, yc - rh * 0.34, bw, rh * 0.68)
        ctx.fill()

        # Wilson 95% CI whisker
        x_lo = map_x(lo, 0.0, 100.0, px0, pw)
        x_hi = map_x(hi, 0.0, 100.0, px0, pw)
        ctx.set_source_rgb(*C_TEXT)
        ctx.set_line_width(1.8)
        ctx.move_to(x_lo, yc)
        ctx.line_to(x_hi, yc)
        ctx.move_to(x_lo, yc - 5)
        ctx.line_to(x_lo, yc + 5)
        ctx.move_to(x_hi, yc - 5)
        ctx.line_to(x_hi, yc + 5)
        ctx.stroke()

        draw_text(ctx, lbl, px0 - 10, yc + 4, size=11.5, color=C_TEXT, bold=("AUDIT" in key or "DONOR" in key), align="right")
        draw_text(ctx, f"{val:.1f}%", x_hi + 8, yc + 4, size=11, color=col, bold=True)

    # =========================================================================
    # PANEL B (Right): Yield vs Effective 3D Straggle & Surface Loss Diagnostics
    # =========================================================================
    rx = 2 * pad + w_left
    draw_panel_box(ctx, rx, top, w_right, ph_box, "B) Etkin 3B Hacim Olcegi (sx*sy*sz)^(1/3) & Yuzey Kaybi")
    px0, py0, pw, ph = rx + 74, top + 52, w_right - 102, ph_box * 0.50

    draw_axes_and_grid(ctx, px0, py0, pw, ph, 2.8, 5.4, [3.0, 3.5, 4.0, 4.5, 5.0],
                       15.0, 95.0, [20, 30, 40, 50, 60, 70, 80, 90],
                       "Geometrik Ortalama 3B Sacilma (sx*sy*sz)^(1/3) (nm)", "Secim Verimi (%)",
                       xfmt="{:.1f}", yfmt="{:.0f}")

    # Plot fixed-donor points vs stochastic-donor points
    fixed_keys = [
        ("ANISO_BCA_PURE_N1024", C_GREEN, "BCA saf"),
        ("ANISO_EXP124_BCA_N1024", C_TEAL, "Exp124+BCA"),
        ("ANISO_P91_BCA_N1024", C_BLUE, "P91+BCA"),
        ("AUDIT_EXP105_ISO3p8_N1024", C_GRAY, "Exp105 iso"),
        ("ANISO_BCA_HOLMES_N1024", C_ORANGE, "BCA+Holmes"),
        ("ANISO_P91_HOLMES_N1024", C_ORANGE, "P91+Holmes"),
        ("AUDIT_EXP57_S5_N1024", C_GRAY, "Exp57 5nm"),
    ]
    donor_keys = [
        ("ANISO_EXP124_BCA_DONOR_N1024", C_RED, "Exp124+Donor"),
        ("ANISO_P91_BCA_DONOR_N1024", C_RED, "P91+BCA+Donor"),
        ("ANISO_P91_HOLMES_DONOR_N1024", C_RED, "P91+Holmes+Donor"),
    ]

    # Sort fixed keys by sigma_geom_3d for smooth visual trend
    f_pts = sorted([(yc_map[k]["sigma_geom_3d_nm"], yc_map[k]["yield_frac"] * 100.0, col, lbl) for k, col, lbl in fixed_keys])
    draw_polyline(ctx, [p[0] for p in f_pts], [p[1] for p in f_pts], 2.8, 5.4, 15.0, 95.0, px0, py0, pw, ph, C_BLUE, width=1.8, dash=[4, 3])
    for sx3, yv, col, lbl in f_pts:
        xx = map_x(sx3, 2.8, 5.4, px0, pw)
        yy = map_y(yv, 15.0, 95.0, py0, ph)
        ctx.set_source_rgb(*col)
        ctx.arc(xx, yy, 5.5, 0, 2 * math.pi)
        ctx.fill()
        dy_lbl = -9 if lbl not in ("Exp105 iso", "P91+BCA") else 14
        draw_text(ctx, lbl, xx + 7, yy + dy_lbl, size=10, color=col, bold=True)

    for k, col, lbl in donor_keys:
        c = yc_map[k]
        xx = map_x(c["sigma_geom_3d_nm"], 2.8, 5.4, px0, pw)
        yy = map_y(c["yield_frac"] * 100.0, 15.0, 95.0, py0, ph)
        ctx.set_source_rgb(*col)
        ctx.rectangle(xx - 5.5, yy - 5.5, 11.0, 11.0)
        ctx.fill()
        dy_lbl = -8 if "P91+BCA" in lbl else 14
        draw_text(ctx, lbl, xx + 9, yy + dy_lbl, size=10, color=col, bold=True)

    # Bottom summary table card inside Panel B
    ty = py0 + ph + 62
    th = ph_box - (ty - top) - 18
    ctx.set_source_rgb(0.965, 0.972, 0.985)
    ctx.rectangle(rx + 18, ty, w_right - 36, th)
    ctx.fill()
    ctx.set_source_rgb(*C_BORDER)
    ctx.set_line_width(1.1)
    ctx.rectangle(rx + 18, ty, w_right - 36, th)
    ctx.stroke()

    draw_text(ctx, "Yuzey Kesmesi (z>0) & Stokastik 31P Donor Tanilari", rx + 30, ty + 24, size=12.5, color=C_TEXT, bold=True)
    diag_lines = [
        f"• Exp57 Denetim (5.0 iso): {yc_map['AUDIT_EXP57_S5_N1024']['successes']}/100 = {yc_map['AUDIT_EXP57_S5_N1024']['yield_frac']*100:.1f}% (birebir)",
        f"• Exp105 Denetim (3.8 iso): {yc_map['AUDIT_EXP105_ISO3p8_N1024']['successes']}/400 = {yc_map['AUDIT_EXP105_ISO3p8_N1024']['yield_frac']*100:.2f}% (birebir)",
        f"• Exp92 BCA (sz=2.88 nm, Rp=6.46): yuzey kaybi %{yc_map['ANISO_P91_BCA_N1024']['lost_surface_frac_mean']*100:.2f} -> verim %{yc_map['ANISO_P91_BCA_N1024']['yield_frac']*100:.1f} ({(yc_map['ANISO_P91_BCA_N1024']['yield_frac']-yc_map['AUDIT_EXP105_ISO3p8_N1024']['yield_frac'])*100:+.1f} pp)",
        f"• Exp91 Holmes (sz=5.27 nm, Rp=6.46): yuzey kaybi %{yc_map['ANISO_P91_HOLMES_N1024']['lost_surface_frac_mean']*100:.1f} -> verim %{yc_map['ANISO_P91_HOLMES_N1024']['yield_frac']*100:.1f} ({(yc_map['ANISO_P91_HOLMES_N1024']['yield_frac']-yc_map['AUDIT_EXP105_ISO3p8_N1024']['yield_frac'])*100:+.1f} pp; yuzeysiz %63.2)",
        f"• Stokastik 31P donor (P91+BCA): verim %{yc_map['ANISO_P91_BCA_DONOR_N1024']['yield_frac']*100:.1f} | geri-sacilim %{yc_map['ANISO_P91_BCA_DONOR_N1024']['donor_backscatter_frac']*100:.1f} | sig(<2nm) %{yc_map['ANISO_P91_BCA_DONOR_N1024']['donor_shallow_lt2nm_frac']*100:.1f}",
        f"• Stokastik 31P donor (P91+Holmes): verim %{yc_map['ANISO_P91_HOLMES_DONOR_N1024']['yield_frac']*100:.1f} | geri-sacilim %{yc_map['ANISO_P91_HOLMES_DONOR_N1024']['donor_backscatter_frac']*100:.1f} | sig(<2nm) %{yc_map['ANISO_P91_HOLMES_DONOR_N1024']['donor_shallow_lt2nm_frac']*100:.1f}",
        f"• Sonuc: Mod A'da asil sinirlayici anizotropiden cok 31P donor sacilmasidir; Mod B etkilenmez.",
    ]
    for i, line in enumerate(diag_lines):
        draw_text(ctx, line, rx + 30, ty + 50 + i * 24, size=11, color=C_TEXT if i < 4 else (C_RED if i < 6 else C_BLUE), bold=(i == 6))

    surf.write_to_png(str(OUT_DIR / "fig_exp124_anisotropic_yield.png"))


def main() -> None:
    data = json.loads((OUT_DIR / "plot_data_exp124.json").read_text(encoding="utf-8"))
    make_optics_figure(data)
    make_anisotropic_yield_figure(data)
    print("PLOTS_OK:", OUT_DIR / "fig_exp124_optics_envelope.png", OUT_DIR / "fig_exp124_anisotropic_yield.png")


if __name__ == "__main__":
    main()
