"""Exp136 (H154) PyCairo Publication Figure Generator (2400x1400 PNG).

Runs under system Python (/usr/bin/python3 -B) with pycairo.
Reads results/exp136_tb_sp3d5s_hyperfine/plot_data_exp136.json via Path(__file__).resolve()
(zero hardcoded host paths) and produces:
  results/exp136_tb_sp3d5s_hyperfine/fig_exp136_tb_hyperfine_f_opt.png

Panels:
  A. Atomistic 10-band sp3d5s* Out-of-Sample ENDOR Shell Benchmark (Target vs KL vs VOKL-6 vs
     sp3d5s* Direct vs sp3d5s* + CP) with R331 & log10-RMS callout.
  B. Direct Atomistic 31P Hyperfine Quadratic Stark Shift dA_P(E_z)/A_P(0) & Mode B P_yield(f, E_z)
     response across E_z in [0, 3.0] MV/m.
  C. Mode B K=8 Yield & Exact M4 L=11 FT Percolation (<=5% dead, N_cand=3, 6, 8, 10) vs 29Si
     isotope fraction f in [0.5%, 3.0%] with 99.5% target and Pareto f* marker.
  D. Pareto Frontier: M4 L=11 FT Percolation (N_cand=6) vs Electron T2e (Hahn & XY8-DD N=32/64)
     and Abragam Nuclear T2n*(f) across f in [0.5%, 3.0%].
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cairo

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp136_tb_sp3d5s_hyperfine"
DATA_PATH = OUT_DIR / "plot_data_exp136.json"
OUT_PNG = OUT_DIR / "fig_exp136_tb_hyperfine_f_opt.png"

# Colorblind-safe Okabe-Ito / Slate scientific palette
BG = (0.980, 0.985, 0.992)
PANEL_BG = (1.0, 1.0, 1.0)
BORDER = (0.78, 0.83, 0.89)
GRID = (0.90, 0.92, 0.95)
TEXT = (0.10, 0.13, 0.18)
MUTED = (0.37, 0.43, 0.52)

C_TGT = (0.12, 0.16, 0.22)      # Charcoal — Experiment / LMTO target
C_KL = (0.20, 0.46, 0.74)       # Deep Blue — Legacy KL
C_VOKL = (0.82, 0.20, 0.22)     # Crimson — Exp129 VOKL-6
C_DIR = (0.90, 0.55, 0.12)      # Amber — sp3d5s* Direct (alpha_cp=0)
C_TB = (0.09, 0.56, 0.42)       # Emerald — sp3d5s* + CP (Primary)
C_PURP = (0.52, 0.30, 0.72)     # Purple — XY8 / Stark / N_cand=8
C_TEAL = (0.08, 0.52, 0.68)     # Teal — T2n* / N_cand=10
C_SLATE = (0.45, 0.51, 0.59)    # Slate — N_cand=3 / secondary
C_WARN = (0.84, 0.22, 0.18)     # Red — threshold / 10 ms gate


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
    color: tuple[float, float, float] = TEXT,
    bold: bool = False,
    align: str = "left",
) -> None:
    set_font(ctx, size, bold)
    ext = ctx.text_extents(text)
    if align == "center":
        tx = x - (ext.width / 2.0 + ext.x_bearing)
    elif align == "right":
        tx = x - (ext.width + ext.x_bearing)
    else:
        tx = x
    ctx.set_source_rgb(*color)
    ctx.move_to(tx, y)
    ctx.show_text(text)


def draw_rotated_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 14.0,
    color: tuple[float, float, float] = TEXT,
    bold: bool = False,
) -> None:
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(-math.pi / 2.0)
    draw_text(ctx, text, 0.0, 0.0, size=size, color=color, bold=bold, align="center")
    ctx.restore()


def draw_rounded_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 10.0) -> None:
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2.0, 0.0)
    ctx.arc(x + w - r, y + h - r, r, 0.0, math.pi / 2.0)
    ctx.arc(x + r, y + h - r, r, math.pi / 2.0, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def draw_card(
    ctx: cairo.Context,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    badge: str,
    badge_color: tuple[float, float, float] = C_TB,
) -> None:
    draw_rounded_rect(ctx, x, y, w, h, 10.0)
    ctx.set_source_rgb(*PANEL_BG)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.6)
    ctx.stroke()

    # Header bar
    ctx.set_source_rgb(0.955, 0.968, 0.985)
    ctx.rectangle(x + 1, y + 1, w - 2, 44)
    ctx.fill()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.move_to(x, y + 45)
    ctx.line_to(x + w, y + 45)
    ctx.stroke()

    draw_text(ctx, title, x + 16, y + 29, size=16.5, color=TEXT, bold=True)

    # Right badge pill
    set_font(ctx, 12.5, bold=True)
    bw = ctx.text_extents(badge).width + 20
    bx = x + w - bw - 14
    by = y + 10
    draw_rounded_rect(ctx, bx, by, bw, 26, 6.0)
    ctx.set_source_rgb(*badge_color)
    ctx.fill()
    draw_text(ctx, badge, bx + bw / 2.0, by + 17.5, size=12.5, color=(1.0, 1.0, 1.0), bold=True, align="center")


def draw_axes_frame(ctx: cairo.Context, px: float, py: float, pw: float, ph: float) -> None:
    ctx.set_source_rgb(0.28, 0.34, 0.42)
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()


def draw_panel_a(ctx: cairo.Context, data: dict[str, Any], cx: float, cy: float, cw: float, ch: float) -> None:
    sc = data["shell_comparison"]
    err331_tb = sc["err_R331_pct"]["TB_CP"]
    lrms_tb = sc["logRMS"]["TB_CP"]
    badge = f"R331 err: {err331_tb:.1f}% | logRMS: {lrms_tb:.3f}"
    draw_card(ctx, cx, cy, cw, ch, "A. Atomistic 10-Band sp3d5s* Out-of-Sample ENDOR Shells (Zero 29Si Fit)", badge, C_TB)

    px, py, pw, ph = cx + 82, cy + 72, cw - 110, ch - 176
    # Log-scale y-axis from 1e-3 to 1.0
    y_min_log, y_max_log = -3.0, -0.15

    def y_map(val: float) -> float:
        lv = max(y_min_log, min(y_max_log, math.log10(max(val, 1e-4))))
        return py + ph * (1.0 - (lv - y_min_log) / (y_max_log - y_min_log))

    # Horizontal gridlines
    for pval, lbl in [(1e-3, "0.001"), (3e-3, "0.003"), (1e-2, "0.01"), (3e-2, "0.03"), (0.1, "0.10"), (0.3, "0.30"), (0.6, "0.60")]:
        yy = y_map(pval)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px, yy)
        ctx.line_to(px + pw, yy)
        ctx.stroke()
        draw_text(ctx, lbl, px - 10, yy + 5, size=12.5, color=MUTED, align="right")

    draw_axes_frame(ctx, px, py, pw, ph)
    draw_rotated_text(ctx, "Hyperfine Ratio a(R) / a(0,0,4)  [log scale]", cx + 24, py + ph / 2.0, size=14.0, color=TEXT, bold=True)

    shells = sc["shells"]
    series = [
        ("Target (ENDOR/LMTO)", sc["target"], C_TGT),
        ("Legacy KL (Exp25)", sc["KL_legacy"], C_KL),
        ("VOKL-6 (Exp129)", sc["VOKL6_full"], C_VOKL),
        ("sp3d5s* Direct (0 CP)", sc["TB_direct"], C_DIR),
        ("sp3d5s* + CP (0.015)", sc["TB_CP"], C_TB),
    ]
    n_groups = len(shells)
    n_bars = len(series)
    gw = pw / n_groups
    bar_w = (gw * 0.78) / n_bars

    for gi, sh_name in enumerate(shells):
        gx0 = px + gi * gw + gw * 0.11
        for bi, (_lbl, vals, col) in enumerate(series):
            val = float(vals[gi])
            bx = gx0 + bi * bar_w
            by = y_map(val)
            bh = (py + ph) - by
            ctx.set_source_rgb(*col)
            ctx.rectangle(bx + 1.5, by, bar_w - 3.0, max(bh, 2.0))
            ctx.fill()
            # Value annotation on top for (3,3,1) and (1,1,1) key bars
            if sh_name == "(3,3,1)" and bi in (0, 2, 4):
                draw_text(ctx, f"{val:.2f}", bx + bar_w / 2.0, by - 6, size=11.0, color=col, bold=True, align="center")
        sub_lbl = "(Exp)" if sh_name in ("(1,1,1)", "(3,3,1)") else "(LMTO-GF)"
        draw_text(ctx, sh_name, px + (gi + 0.5) * gw, py + ph + 22, size=14.0, color=TEXT, bold=True, align="center")
        draw_text(ctx, sub_lbl, px + (gi + 0.5) * gw, py + ph + 40, size=11.5, color=MUTED, align="center")

    # Legend strip at bottom of Panel A (2 rows x 3 cols, crisp no-overlap)
    lx0, ly0 = px, py + ph + 66
    for idx, (lbl, _v, col) in enumerate(series):
        row = idx // 3
        col_i = idx % 3
        lx = lx0 + col_i * 335
        ly = ly0 + row * 22
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx, ly - 10, 14, 12)
        ctx.fill()
        draw_text(ctx, lbl, lx + 20, ly, size=12.0, color=TEXT, bold=(idx in (0, 4)))

    # Summary callout box inside top-right corner of Panel A
    bx, by, bw, bh = px + pw - 335, py + 10, 323, 86
    draw_rounded_rect(ctx, bx, by, bw, bh, 6.0)
    ctx.set_source_rgba(0.96, 0.99, 0.97, 0.95)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_TB)
    ctx.set_line_width(1.3)
    ctx.stroke()
    draw_text(ctx, "4-Shell log10-RMS Benchmark:", bx + 12, by + 20, size=12.5, color=TEXT, bold=True)
    draw_text(
        ctx,
        f"VOKL-6: {sc['logRMS']['VOKL6']:.3f}  |  KL: {sc['logRMS']['KL']:.3f}",
        bx + 12, by + 40, size=12.0, color=MUTED,
    )
    draw_text(
        ctx,
        f"sp3d5s* + CP: {sc['logRMS']['TB_CP']:.3f}  (3.1x lower vs VOKL-6)",
        bx + 12, by + 60, size=12.0, color=C_TB, bold=True,
    )
    draw_text(
        ctx,
        f"R331 err: 64.7% -> {sc['err_R331_pct']['TB_direct']:.1f}% (0 CP) / {sc['err_R331_pct']['TB_CP']:.1f}% (CP)",
        bx + 12, by + 78, size=11.5, color=TEXT,
    )


def draw_panel_b(ctx: cairo.Context, data: dict[str, Any], cx: float, cy: float, cw: float, ch: float) -> None:
    eta_a = float(data["eta_A_fit_um2_per_V2"])
    badge = f"eta_A = {eta_a:.2e} um2/V2"
    draw_card(ctx, cx, cy, cw, ch, "B. Atomistic 31P Hyperfine Stark Shift & Mode B Yield vs E_z (N=20)", badge, C_PURP)

    # Split into left sub-plot (Stark shift dA/A0 vs E_z) and right sub-plot (Mode B P_yield vs E_z)
    gap_mid = 88
    sub_w = (cw - 150 - gap_mid) / 2.0
    py, ph = cy + 82, ch - 165

    # --- Left sub-plot: -Delta A_P / A_P(0) (%) vs E_z ---
    lx = cx + 82
    s_rows = data["stark_rows"]
    ez_vals = [float(r["E_z_MV_per_m"]) for r in s_rows]
    da_pct = [-100.0 * float(r["delta_A_over_A0"]) for r in s_rows]  # positive magnitude of negative shift (%)
    ymax_l = max(max(da_pct) * 1.45, 0.45)

    def lx_map(e: float) -> float:
        return lx + sub_w * (e / 3.0)

    def ly_map(v: float) -> float:
        return py + ph * (1.0 - v / ymax_l)

    for i in range(6):
        yv = ymax_l * i / 5.0
        yy = ly_map(yv)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(lx, yy)
        ctx.line_to(lx + sub_w, yy)
        ctx.stroke()
        draw_text(ctx, f"-{yv:.2f}%", lx - 8, yy + 4, size=11.5, color=MUTED, align="right")

    for ev in [0.0, 1.0, 2.0, 3.0]:
        xx = lx_map(ev)
        ctx.set_source_rgb(*GRID)
        ctx.move_to(xx, py)
        ctx.line_to(xx, py + ph)
        ctx.stroke()
        draw_text(ctx, f"{ev:.0f}", xx, py + ph + 20, size=12.5, color=TEXT, align="center")

    draw_axes_frame(ctx, lx, py, sub_w, ph)
    draw_text(ctx, "Electric Field E_z (MV/m)", lx + sub_w / 2.0, py + ph + 44, size=13.0, color=TEXT, bold=True, align="center")
    draw_rotated_text(ctx, "31P Stark Shift dA_P / A_P(0)", cx + 22, py + ph / 2.0, size=13.5, color=C_PURP, bold=True)

    # Smooth quadratic fit curve
    ctx.set_source_rgb(*C_PURP)
    ctx.set_line_width(2.6)
    for idx in range(61):
        ev = 3.0 * idx / 60.0
        yv = -100.0 * eta_a * (ev ** 2)
        xx, yy = lx_map(ev), ly_map(yv)
        if idx == 0:
            ctx.move_to(xx, yy)
        else:
            ctx.line_to(xx, yy)
    ctx.stroke()

    # Exact atomistic data points
    for ev, yv in zip(ez_vals, da_pct):
        ctx.set_source_rgb(*C_PURP)
        ctx.arc(lx_map(ev), ly_map(yv), 5.2, 0.0, 2.0 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(lx_map(ev), ly_map(yv), 2.2, 0.0, 2.0 * math.pi)
        ctx.fill()

    draw_text(ctx, "Exact N=20 sp3d5s* (R2=1.000)", lx + 12, py + 22, size=11.8, color=C_PURP, bold=True)
    draw_text(ctx, f"dA/A = {eta_a:.2e} E_z^2", lx + 12, py + 40, size=11.3, color=TEXT)
    draw_text(ctx, "Box scaling (2p0 conf.):", lx + 12, py + 58, size=10.8, color=MUTED)
    draw_text(ctx, "N16/20/24: -1.3/-3.7/-7.2e-4", lx + 12, py + 74, size=10.8, color=MUTED)

    # --- Right sub-plot: Mode B P_yield(f, E_z) vs E_z ---
    rx = lx + sub_w + gap_mid
    sy_rows = data["stark_yield_rows"]

    def rx_map(e: float) -> float:
        return rx + sub_w * (e / 3.0)

    def ry_map(y_pct: float) -> float:
        return py + ph * (1.0 - y_pct / 100.0)

    for yv in [0, 20, 40, 60, 80, 100]:
        yy = ry_map(float(yv))
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(rx, yy)
        ctx.line_to(rx + sub_w, yy)
        ctx.stroke()
        draw_text(ctx, f"{yv}%", rx - 8, yy + 4, size=11.5, color=MUTED, align="right")

    for ev in [0.0, 1.0, 2.0, 3.0]:
        xx = rx_map(ev)
        ctx.set_source_rgb(*GRID)
        ctx.move_to(xx, py)
        ctx.line_to(xx, py + ph)
        ctx.stroke()
        draw_text(ctx, f"{ev:.0f}", xx, py + ph + 20, size=12.5, color=TEXT, align="center")

    draw_axes_frame(ctx, rx, py, sub_w, ph)
    draw_text(ctx, "Electric Field E_z (MV/m)", rx + sub_w / 2.0, py + ph + 44, size=13.0, color=TEXT, bold=True, align="center")
    draw_rotated_text(ctx, "Mode B K=8 Yield P_yield (%)", rx - 46, py + ph / 2.0, size=13.5, color=TEXT, bold=True)

    f_styles = [
        (1.0, C_KL, "f = 1.0%"),
        (1.5, C_TB, "f = 1.5%"),
        (2.0, C_DIR, "f = 2.0%"),
    ]
    for idx_f, (fv, col, lbl) in enumerate(f_styles):
        pts = sorted([r for r in sy_rows if abs(r["abundance_pct"] - fv) < 1e-6], key=lambda r: r["E_z_MV_per_m"])
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.5)
        for pi, r in enumerate(pts):
            xx, yy = rx_map(r["E_z_MV_per_m"]), ry_map(100.0 * r["yield_frac"])
            if pi == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        for r in pts:
            xx = rx_map(r["E_z_MV_per_m"])
            yy = ry_map(100.0 * r["yield_frac"])
            y_lo = ry_map(100.0 * r["wilson_ci95"][0])
            y_hi = ry_map(100.0 * r["wilson_ci95"][1])
            ctx.set_source_rgba(col[0], col[1], col[2], 0.45)
            ctx.set_line_width(1.6)
            ctx.move_to(xx, y_lo)
            ctx.line_to(xx, y_hi)
            ctx.stroke()
            ctx.set_source_rgb(*col)
            ctx.arc(xx, yy, 4.5, 0.0, 2.0 * math.pi)
            ctx.fill()
        # Legend along bottom of right plot
        leg_x = rx + idx_f * 135
        leg_y = py + ph + 68
        ctx.set_source_rgb(*col)
        ctx.rectangle(leg_x, leg_y - 9, 14, 10)
        ctx.fill()
        draw_text(ctx, lbl, leg_x + 20, leg_y, size=12.0, color=TEXT, bold=True)

    draw_text(ctx, "Stark breaks shell degeneracy -> lifts K=8 yield!", rx + sub_w / 2.0, py + 22, size=11.5, color=C_TB, bold=True, align="center")


def draw_panel_c(ctx: cairo.Context, data: dict[str, Any], cx: float, cy: float, cw: float, ch: float) -> None:
    f_star = data["pareto_f_star_base_pct"]
    badge = f"Pareto f* = {f_star:.2f}% (N_cand=6 >= 99.5%)" if f_star is not None else "No f <= 3.0% meets 99.5%"
    draw_card(ctx, cx, cy, cw, ch, "C. Mode B K=8 Yield & M4 L=11 FT Percolation (<=5% Dead) vs 29Si Fraction f", badge, C_KL)

    px, py, pw, ph = cx + 82, cy + 78, cw - 110, ch - 170
    rows = data["f_sweep_hm5962"]
    f_min, f_max = 0.4, 3.1

    def x_map(f: float) -> float:
        return px + pw * ((f - f_min) / (f_max - f_min))

    def y_map(pct: float) -> float:
        return py + ph * (1.0 - pct / 100.0)

    # Gridlines
    for yv in [0, 20, 40, 60, 80, 100]:
        yy = y_map(float(yv))
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px, yy)
        ctx.line_to(px + pw, yy)
        ctx.stroke()
        draw_text(ctx, f"{yv}%", px - 10, yy + 4.5, size=12.5, color=MUTED, align="right")

    for fv in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        xx = x_map(fv)
        ctx.set_source_rgb(*GRID)
        ctx.move_to(xx, py)
        ctx.line_to(xx, py + ph)
        ctx.stroke()
        draw_text(ctx, f"{fv:.1f}%", xx, py + ph + 21, size=12.5, color=TEXT, align="center")

    # 99.5% FT target line
    y995 = y_map(99.5)
    ctx.save()
    ctx.set_dash([7.0, 5.0])
    ctx.set_source_rgb(*C_WARN)
    ctx.set_line_width(1.5)
    ctx.move_to(px, y995)
    ctx.line_to(px + pw, y995)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "99.5% M4 L=11 FT Target", px + pw - 8, y995 + 15, size=11.5, color=C_WARN, bold=True, align="right")

    # Vertical f* highlight line
    if f_star is not None:
        x_fs = x_map(float(f_star))
        ctx.save()
        ctx.set_dash([5.0, 4.0])
        ctx.set_source_rgb(*C_TB)
        ctx.set_line_width(2.0)
        ctx.move_to(x_fs, py)
        ctx.line_to(x_fs, py + ph)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, f"f* = {f_star:.2f}%", x_fs + 7, py + ph - 12, size=12.5, color=C_TB, bold=True)

    draw_axes_frame(ctx, px, py, pw, ph)
    draw_text(ctx, "29Si Epitaxial Isotope Fraction f (%)", px + pw / 2.0, py + ph + 44, size=13.5, color=TEXT, bold=True, align="center")
    draw_rotated_text(ctx, "Yield / M4 L=11 FT Percolation (%)", cx + 22, py + ph / 2.0, size=13.5, color=TEXT, bold=True)

    # Curves: M4 L=11 FT (N_cand = 3, 6, 8, 10) + Mode B base yield + Mode B gap>=6.89kHz
    curves = [
        ("M4 FT N_cand=10", "Y_FT_N10", C_TEAL, False, 2.2),
        ("M4 FT N_cand=8", "Y_FT_N8", C_PURP, False, 2.2),
        ("M4 FT N_cand=6 (Baseline)", "Y_FT_N6", C_TB, False, 3.2),
        ("M4 FT N_cand=3", "Y_FT_N3", C_SLATE, True, 2.0),
        ("Mode B Base Yield (K=8)", "yield_base", C_KL, False, 2.6),
        ("Mode B Gap >= 6.89 kHz", "yield_gap6p89", C_DIR, True, 2.2),
    ]
    for lbl, key, col, dashed, lw in curves:
        ctx.save()
        if dashed:
            ctx.set_dash([6.0, 4.0])
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        for i, r in enumerate(rows):
            xx = x_map(float(r["f_pct"]))
            yy = y_map(100.0 * float(r[key]))
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        ctx.restore()
        for r in rows:
            xx = x_map(float(r["f_pct"]))
            yy = y_map(100.0 * float(r[key]))
            ctx.set_source_rgb(*col)
            ctx.arc(xx, yy, 3.8 if lw < 3.0 else 5.0, 0.0, 2.0 * math.pi)
            ctx.fill()

    # Legend (2 rows x 3 cols below x-axis)
    for idx, (lbl, _k, col, _d, _lw) in enumerate(curves):
        row = idx // 3
        col_i = idx % 3
        lx = px + col_i * 335
        ly = py + ph + 66 + row * 22
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx, ly - 9, 14, 10)
        ctx.fill()
        draw_text(ctx, lbl, lx + 20, ly, size=11.8, color=TEXT, bold=(idx in (2, 4)))


def draw_panel_d(ctx: cairo.Context, data: dict[str, Any], cx: float, cy: float, cw: float, ch: float) -> None:
    tb7 = data["verdicts"]["TB7_SIMULTANEOUS_T2E_10MS_FEASIBILITY"]
    badge = "TB7: Raw Hahn FAIL (<10 ms) | XY8-64 PASS" if not tb7 else "TB7: PASS"
    draw_card(ctx, cx, cy, cw, ch, "D. Coherence vs Percolation Pareto Frontier (T2e Hahn/XY8 & Abragam T2n*)", badge, C_WARN)

    px, py, pw, ph = cx + 82, cy + 78, cw - 155, ch - 170
    rows = data["f_sweep_hm5962"]
    f_min, f_max = 0.4, 3.1

    def x_map(f: float) -> float:
        return px + pw * ((f - f_min) / (f_max - f_min))

    # Left log y-axis: Coherence time (ms) from 0.2 ms to 100 ms
    y_min_l, y_max_l = math.log10(0.2), math.log10(100.0)

    def y_coh_map(ms: float) -> float:
        lv = max(y_min_l, min(y_max_l, math.log10(max(ms, 0.2))))
        return py + ph * (1.0 - (lv - y_min_l) / (y_max_l - y_min_l))

    # Right linear y-axis: M4 L=11 N_cand=6 FT yield (0..100%)
    def y_ft_map(pct: float) -> float:
        return py + ph * (1.0 - pct / 100.0)

    for tv, lbl in [(0.3, "0.3"), (0.5, "0.5"), (1.0, "1.0"), (2.0, "2.0"), (5.0, "5.0"), (10.0, "10"), (20.0, "20"), (50.0, "50"), (100.0, "100")]:
        yy = y_coh_map(tv)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px, yy)
        ctx.line_to(px + pw, yy)
        ctx.stroke()
        draw_text(ctx, lbl, px - 10, yy + 4.5, size=12.0, color=MUTED, align="right")

    for fv in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        xx = x_map(fv)
        ctx.set_source_rgb(*GRID)
        ctx.move_to(xx, py)
        ctx.line_to(xx, py + ph)
        ctx.stroke()
        draw_text(ctx, f"{fv:.1f}%", xx, py + ph + 21, size=12.5, color=TEXT, align="center")

    # Right y-axis ticks
    for pct in [0, 25, 50, 75, 100]:
        yy = y_ft_map(float(pct))
        draw_text(ctx, f"{pct}%", px + pw + 10, yy + 4.5, size=12.0, color=C_TB, align="left")

    # 10 ms coherence target line + crisp zero-overlap callout pill in open upper-right whitespace
    y10 = y_coh_map(10.0)
    ctx.save()
    ctx.set_dash([7.0, 5.0])
    ctx.set_source_rgb(*C_WARN)
    ctx.set_line_width(1.8)
    ctx.move_to(px, y10)
    ctx.line_to(px + pw, y10)
    ctx.stroke()
    ctx.restore()
    lbl_10 = "10 ms Coherence Target (TB7)"
    set_font(ctx, 11.5, bold=True)
    tw10 = ctx.text_extents(lbl_10).width
    p10_x, p10_y = px + pw - tw10 - 22, y_coh_map(26.0) - 14
    draw_rounded_rect(ctx, p10_x, p10_y, tw10 + 16, 22, 4.0)
    ctx.set_source_rgba(1.0, 0.97, 0.97, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_WARN)
    ctx.set_line_width(1.1)
    ctx.stroke()
    draw_text(ctx, lbl_10, p10_x + 8, p10_y + 15, size=11.5, color=C_WARN, bold=True)
    # Thin leader line down to the 10 ms dashed line at f=2.95%
    x_lead = x_map(2.92)
    ctx.set_source_rgb(*C_WARN)
    ctx.set_line_width(1.1)
    ctx.move_to(x_lead, p10_y + 22)
    ctx.line_to(x_lead, y10 - 2)
    ctx.stroke()

    # Vertical Pareto f* band
    f_star = data["pareto_f_star_base_pct"]
    if f_star is not None:
        x_fs = x_map(float(f_star))
        ctx.save()
        ctx.set_dash([5.0, 4.0])
        ctx.set_source_rgb(*C_TB)
        ctx.set_line_width(2.0)
        ctx.move_to(x_fs, py)
        ctx.line_to(x_fs, py + ph)
        ctx.stroke()
        ctx.restore()

    draw_axes_frame(ctx, px, py, pw, ph)
    draw_text(ctx, "29Si Epitaxial Isotope Fraction f (%)", px + pw / 2.0, py + ph + 44, size=13.5, color=TEXT, bold=True, align="center")
    draw_rotated_text(ctx, "Coherence Time T2 (ms)  [log scale]", cx + 22, py + ph / 2.0, size=13.5, color=TEXT, bold=True)
    draw_rotated_text(ctx, "M4 L=11 FT Yield (N_cand=6, %)", cx + cw - 20, py + ph / 2.0, size=13.5, color=C_TB, bold=True)

    # Plot coherence curves (left axis)
    coh_curves = [
        ("T2e Raw Hahn-Echo (Exp62/126)", "T2e_hahn_ms", C_VOKL, False, 2.8),
        ("T2e XY8-DD N=32 (alpha=2)", "T2e_XY8_N32_ms", C_DIR, True, 2.4),
        ("T2e XY8-DD N=64 (alpha=2)", "T2e_XY8_N64_ms", C_PURP, False, 2.8),
        ("T2n* Nuclear Dipolar (Abragam)", "T2n_star_ms", C_TEAL, True, 2.4),
    ]
    for _lbl, key, col, dashed, lw in coh_curves:
        ctx.save()
        if dashed:
            ctx.set_dash([6.0, 4.0])
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        for i, r in enumerate(rows):
            xx = x_map(float(r["f_pct"]))
            yy = y_coh_map(float(r[key]))
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        ctx.restore()
        for r in rows:
            ctx.set_source_rgb(*col)
            ctx.arc(x_map(float(r["f_pct"])), y_coh_map(float(r[key])), 4.0, 0.0, 2.0 * math.pi)
            ctx.fill()

    # Overlay M4 L=11 N_cand=6 FT yield on right axis
    ctx.set_source_rgb(*C_TB)
    ctx.set_line_width(3.0)
    for i, r in enumerate(rows):
        xx = x_map(float(r["f_pct"]))
        yy = y_ft_map(100.0 * float(r["Y_FT_N6"]))
        if i == 0:
            ctx.move_to(xx, yy)
        else:
            ctx.line_to(xx, yy)
    ctx.stroke()
    for r in rows:
        ctx.set_source_rgb(*C_TB)
        ctx.arc(x_map(float(r["f_pct"])), y_ft_map(100.0 * float(r["Y_FT_N6"])), 4.8, 0.0, 2.0 * math.pi)
        ctx.fill()

    # Legend (2 rows x 3 cols)
    all_leg = [
        ("T2e Hahn (Raw <10 ms)", C_VOKL),
        ("T2e XY8 N=32 (a=2)", C_DIR),
        ("T2e XY8 N=64 (a=2)", C_PURP),
        ("T2n* Abragam (29Si)", C_TEAL),
        ("M4 L=11 FT N_cand=6 (R)", C_TB),
    ]
    for idx, (lbl, col) in enumerate(all_leg):
        row = idx // 3
        col_i = idx % 3
        lx = px + col_i * 315
        ly = py + ph + 66 + row * 22
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx, ly - 9, 14, 10)
        ctx.fill()
        draw_text(ctx, lbl, lx + 20, ly, size=11.8, color=TEXT, bold=(idx in (0, 2, 4)))


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    W, H = 2400, 1400
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Top title banner
    ctx.set_source_rgb(0.10, 0.16, 0.25)
    ctx.rectangle(0, 0, W, 86)
    ctx.fill()
    vc = data["verdict_counts"]
    draw_text(
        ctx,
        "Exp136 (H154): Atomistic 10-Band sp3d5s* Boykin-Klimeck Tight-Binding 31P Donor, R331 Core Polarization & Pareto 29Si f*",
        34, 38, size=24.0, color=(1.0, 1.0, 1.0), bold=True,
    )
    draw_text(
        ctx,
        f"N=20 FCC Supercell (16,000 atoms / 160,000 orbitals, zero 29Si fitting)  |  Mode B N_cell=400  |  M4 L=11 FT (<=5% dead, p_cap=0.952)  |  Verdicts: {vc['passed']}/{vc['total']} PASS (no_lab_measurement=true)",
        34, 67, size=14.5, color=(0.82, 0.88, 0.96),
    )

    margin = 26
    gap = 22
    cw = (W - 2 * margin - gap) / 2.0
    ch = (H - 86 - 2 * margin - gap - 22) / 2.0
    top_y = 86 + margin
    bot_y = top_y + ch + gap

    draw_panel_a(ctx, data, margin, top_y, cw, ch)
    draw_panel_b(ctx, data, margin + cw + gap, top_y, cw, ch)
    draw_panel_c(ctx, data, margin, bot_y, cw, ch)
    draw_panel_d(ctx, data, margin + cw + gap, bot_y, cw, ch)

    draw_text(
        ctx,
        "Atom Lithography Machine v5.0  |  Exp136 (H154, Risk R1 Closure)  |  Epistemic: {Literatur}/{Analitik}/{Model}/{Sayisal-Simulasyon}  |  Zero hardcoded paths",
        W / 2.0, H - 10, size=12.0, color=MUTED, align="center",
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    surf.write_to_png(str(OUT_PNG))
    print(f"Generated {OUT_PNG} ({W}x{H})", flush=True)


if __name__ == "__main__":
    main()
