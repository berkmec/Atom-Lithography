"""Exp148 (H166) Publication Figure Generator (2400x1400 PyCairo).

Reads results/exp148_sb121_quadrupole_echo_qudit/plot_data_exp148.json and renders
results/exp148_sb121_quadrupole_echo_qudit/fig_exp148_sb121_qudit_echo.png.

Run with system python having PyCairo: /usr/bin/python3 -B plot_exp148.py
Zero hardcoded host paths.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
RESULTS_DIR = REPO_ROOT / "results" / "exp148_sb121_quadrupole_echo_qudit"
DATA_PATH = RESULTS_DIR / "plot_data_exp148.json"
OUT_PNG = RESULTS_DIR / "fig_exp148_sb121_qudit_echo.png"

W, H = 2400, 1400


def hex_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


C_BG = hex_rgb("#FAFBFD")
C_PANEL = hex_rgb("#FFFFFF")
C_BORDER = hex_rgb("#CBD5E1")
C_GRID = hex_rgb("#E2E8F0")
C_INK = hex_rgb("#0F172A")
C_MUTED = hex_rgb("#475569")
C_RED = hex_rgb("#C0392B")
C_ORANGE = hex_rgb("#D97706")
C_BLUE = hex_rgb("#2563EB")
C_TEAL = hex_rgb("#0D9488")
C_PURPLE = hex_rgb("#7C3AED")
C_DARK = hex_rgb("#1E293B")
C_GREEN = hex_rgb("#15803D")


def set_font(ctx: cairo.Context, size: float, bold: bool = False) -> None:
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)


def draw_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 16.0,
    color: tuple[float, float, float] = C_INK,
    bold: bool = False,
    align: str = "left",
    valign: str = "baseline",
) -> None:
    set_font(ctx, size, bold)
    ext = ctx.text_extents(text)
    dx = 0.0
    if align == "center":
        dx = -ext.width / 2.0 - ext.x_bearing
    elif align == "right":
        dx = -ext.width - ext.x_bearing
    dy = 0.0
    if valign == "middle":
        dy = -ext.height / 2.0 - ext.y_bearing
    elif valign == "top":
        dy = -ext.y_bearing
    ctx.set_source_rgb(*color)
    ctx.move_to(x + dx, y + dy)
    ctx.show_text(text)


def draw_text_rot(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    angle_deg: float,
    size: float = 15.0,
    color: tuple[float, float, float] = C_INK,
    bold: bool = False,
) -> None:
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(angle_deg))
    draw_text(ctx, text, 0.0, 0.0, size=size, color=color, bold=bold, align="center", valign="middle")
    ctx.restore()


def round_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 10.0) -> None:
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def draw_panel_box(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, subtitle: str) -> None:
    round_rect(ctx, x, y, w, h, 10.0)
    ctx.set_source_rgb(*C_PANEL)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BORDER)
    ctx.set_line_width(1.6)
    ctx.stroke()

    # Header accent bar
    ctx.set_source_rgb(*C_DARK)
    ctx.rectangle(x + 16, y + 14, 6, 36)
    ctx.fill()
    draw_text(ctx, title, x + 32, y + 32, size=19.5, color=C_INK, bold=True)
    draw_text(ctx, subtitle, x + 32, y + 53, size=13.5, color=C_MUTED, bold=False)


def draw_panel_a(ctx: cairo.Context, data: dict, bx: float, by: float, bw: float, bh: float) -> None:
    draw_panel_box(
        ctx,
        bx,
        by,
        bw,
        bh,
        "A. Exp142 OQ6 Closure @ δf_Q = 500 Hz, t = 1 ms (Neutral ¹²¹Sb)",
        "Finite-pulse Ω_peak = 25 kHz multi-tone brickwork tiers (all 7-transition beat crosstalk retained)",
    )
    pa = data["panel_a_oq6_closure"]

    px0, py0 = bx + 84, by + 114
    pw, ph = bw - 114, bh - 188
    ymin, ymax = 0.50, 1.03

    def ymap(v: float) -> float:
        return py0 + ph * (1.0 - (v - ymin) / (ymax - ymin))

    # Grid & Y ticks
    for yt in (0.50, 0.60, 0.70, 0.80, 0.90, 0.98, 1.00):
        yy = ymap(yt)
        ctx.set_source_rgb(*(C_GREEN if abs(yt - 0.98) < 1e-6 else C_GRID))
        ctx.set_line_width(1.4 if abs(yt - 0.98) < 1e-6 else 1.0)
        if abs(yt - 0.98) < 1e-6:
            ctx.set_dash([6, 4])
        else:
            ctx.set_dash([])
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()
        ctx.set_dash([])
        draw_text(
            ctx,
            f"{yt:.2f}",
            px0 - 10,
            yy,
            size=13.5,
            color=C_GREEN if abs(yt - 0.98) < 1e-6 else C_MUTED,
            bold=abs(yt - 0.98) < 1e-6,
            align="right",
            valign="middle",
        )

    draw_text_rot(ctx, "State Fidelity F (t = 1 ms)", bx + 24, py0 + ph / 2, -90, size=14.5, color=C_INK, bold=True)

    states = [
        ("gross_0L", "Gross |0_L⟩\n(Exp142 FAIL)"),
        ("spin_cat_pm7_2", "|±7/2⟩ Cat\n(Exp142 0.94)"),
        ("edge_7_2_5_2", "|+7/2,+5/2⟩\n(Edge Pair)"),
        ("clock_pm1_2", "|±1/2⟩ Clock\n(Quad-Free)"),
    ]
    series = [
        ("bare", "Bare (No DD)", C_RED),
        ("qecho8_fp_hann", "Q-Echo-8 Hann (No Cycle)", C_ORANGE),
        ("qecho8_fp_tukey", "Q-Echo-8 Tukey + Quad", C_BLUE),
        ("qecho8_fp_composite", "Q-Echo-8 90-240-90 + Quad", C_TEAL),
        ("qecho8_ideal", "Q-Echo-8 Ideal", C_DARK),
    ]

    n_grp = len(states)
    n_ser = len(series)
    grp_w = pw / n_grp
    bar_w = (grp_w * 0.78) / n_ser

    for gi, (skey, slabel) in enumerate(states):
        gx0 = px0 + gi * grp_w + grp_w * 0.11
        for si, (pkey, _, col) in enumerate(series):
            val = float(pa[pkey][skey])
            x_bar = gx0 + si * bar_w + 1.5
            y_top = ymap(min(val, 1.0))
            y_bot = ymap(ymin)
            ctx.set_source_rgb(*col)
            ctx.rectangle(x_bar, y_top, bar_w - 3.0, max(1.0, y_bot - y_top))
            ctx.fill()
            # Value annotation on Bare, Hann, Tukey, and Composite (skip Ideal to avoid crowding)
            if si in (0, 1, 2, 3):
                lbl = f"{val:.3f}" if val < 0.995 else f"{val:.4f}"
                y_lbl = y_top - 8.0 if si != 2 else y_top - 22.0
                if si == 3:
                    y_lbl = y_top - 10.0
                if skey == "clock_pm1_2" and si in (0, 3):
                    y_lbl = y_top - (24.0 if si == 0 else 10.0)
                if not (skey == "clock_pm1_2" and si == 2):
                    draw_text(ctx, lbl, x_bar + (bar_w - 3.0) / 2.0, y_lbl, size=11.0, color=col, bold=True, align="center")

        lines = slabel.split("\n")
        xc = px0 + (gi + 0.5) * grp_w
        draw_text(ctx, lines[0], xc, py0 + ph + 22, size=14.0, color=C_INK, bold=True, align="center")
        draw_text(ctx, lines[1], xc, py0 + ph + 40, size=12.0, color=C_MUTED, align="center")

    # Axes frame
    ctx.set_source_rgb(*C_INK)
    ctx.set_line_width(1.6)
    ctx.move_to(px0, py0)
    ctx.line_to(px0, py0 + ph)
    ctx.line_to(px0 + pw, py0 + ph)
    ctx.stroke()

    # Horizontal legend cleanly placed in top header zone (y = by + 72..102)
    lx = px0
    ly = by + 84
    for _, lname, col in series:
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx, ly - 10, 14, 12)
        ctx.fill()
        draw_text(ctx, lname, lx + 19, ly, size=12.5, color=C_INK, bold=False)
        set_font(ctx, 12.5, False)
        lx += 28 + ctx.text_extents(lname).width + 14


def draw_panel_b(ctx: cairo.Context, data: dict, bx: float, by: float, bw: float, bh: float) -> None:
    draw_panel_box(
        ctx,
        bx,
        by,
        bw,
        bh,
        "B. Broadband 1/f Strain Decay (500 Hz rms, 1 Hz–100 kHz, Exact Multi-OU)",
        "Cywiński N_cyc^{1/2} scaling: Q-Echo-8 gives 8.4× (SQ4 honest FAIL); Q-Echo-64 reaches 28.1× (1.45 ms)",
    )
    dec = data["panel_b_colored_1f"]["decay_500Hz"]
    ts = dec["t_ms"]
    curves = dec["curves"]
    t2 = dec["T2_eff_ms"]

    px0, py0 = bx + 86, by + 114
    pw, ph = bw - 120, bh - 184
    xmin_l, xmax_l = math.log10(0.02), math.log10(20.0)
    ymin, ymax = 0.50, 1.02

    def xmap(t: float) -> float:
        return px0 + pw * (math.log10(t) - xmin_l) / (xmax_l - xmin_l)

    def ymap(v: float) -> float:
        return py0 + ph * (1.0 - (v - ymin) / (ymax - ymin))

    # Grid lines
    for yt in (0.50, 0.58, 0.70, 0.80, 0.90, 1.00):
        yy = ymap(yt)
        ctx.set_source_rgb(*(C_MUTED if abs(yt - 0.58) < 1e-6 else C_GRID))
        ctx.set_line_width(1.2 if abs(yt - 0.58) < 1e-6 else 1.0)
        ctx.set_dash([5, 5] if abs(yt - 0.58) < 1e-6 else [])
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()
        ctx.set_dash([])
        draw_text(ctx, f"{yt:.2f}", px0 - 10, yy, size=13.5, color=C_MUTED, align="right", valign="middle")

    for xt in (0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0):
        xx = xmap(xt)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(xx, py0)
        ctx.line_to(xx, py0 + ph)
        ctx.stroke()
        lbl = f"{xt:g}"
        draw_text(ctx, lbl, xx, py0 + ph + 22, size=13.0, color=C_MUTED, align="center")

    # 1/e Gross visibility line: 0.58 + 0.42/e = 0.7345
    f_1e = 0.58 + 0.42 * math.exp(-1.0)
    yy_1e = ymap(f_1e)
    ctx.set_source_rgb(*C_PURPLE)
    ctx.set_line_width(1.2)
    ctx.set_dash([4, 4])
    ctx.move_to(px0, yy_1e)
    ctx.line_to(px0 + pw, yy_1e)
    ctx.stroke()
    ctx.set_dash([])
    draw_text(ctx, "Gross 1/e visibility (0.735)", xmap(4.2), yy_1e - 8, size=11.5, color=C_PURPLE, bold=True, align="center")
    draw_text(ctx, "Gross dephased floor (0.580)", px0 + pw - 8, ymap(0.58) - 8, size=11.5, color=C_MUTED, align="right")

    draw_text_rot(ctx, "Exact Gaussian Fidelity F(t)", bx + 24, py0 + ph / 2, -90, size=14.5, color=C_INK, bold=True)
    draw_text(ctx, "Evolution Time t (ms, log scale)", px0 + pw / 2, py0 + ph + 48, size=14.5, color=C_INK, bold=True, align="center")

    lines_spec = [
        ("bare_gross", f"Bare Gross (T2*={t2['bare_gross_ms']*1e3:.1f} µs)", C_RED, []),
        ("qecho8_gross", f"Q-Echo-8 1× (T2={t2['qecho8_gross_ms']:.3f} ms, {t2['gross_gain_qecho8_vs_bare']:.1f}×)", C_ORANGE, []),
        ("qecho16_gross", f"Q-Echo-16 2× (T2={t2['qecho16_gross_ms']:.3f} ms, {t2['gross_gain_qecho16_vs_bare']:.1f}×)", C_PURPLE, []),
        ("qecho32_gross", f"Q-Echo-32 4× (T2={t2['qecho32_gross_ms']:.3f} ms, {t2['gross_gain_qecho32_vs_bare']:.1f}×)", C_BLUE, []),
        ("qecho64_gross", f"Q-Echo-64 8× (T2={t2['qecho64_gross_ms']:.3f} ms, {t2['gross_gain_qecho64_vs_bare']:.1f}×)", C_TEAL, []),
        ("qecho8_cat77", f"Q-Echo-8 |±7/2⟩ Cat (T2={t2['qecho8_cat77_ms']:.1f} ms)", C_DARK, [8, 4]),
    ]

    for ckey, _, col, dash in lines_spec:
        vals = curves[ckey]
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.8)
        ctx.set_dash(dash)
        for i, (t, v) in enumerate(zip(ts, vals)):
            xx, yy = xmap(t), ymap(v)
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        ctx.set_dash([])
        for t, v in zip(ts, vals):
            ctx.arc(xmap(t), ymap(v), 3.6, 0, 2 * math.pi)
            ctx.fill()

    # Axes
    ctx.set_source_rgb(*C_INK)
    ctx.set_line_width(1.6)
    ctx.move_to(px0, py0)
    ctx.line_to(px0, py0 + ph)
    ctx.line_to(px0 + pw, py0 + ph)
    ctx.stroke()

    # Clean inset legend box at bottom-left/mid-right? Wait: curves are high on top-left and low on bottom-right,
    # while bottom-left (t=0.02..0.25, F=0.52..0.72) is completely open white space! Let's put legend bottom-left!
    lg_x, lg_y, lg_w, lg_h = px0 + 14, py0 + ph - 178, 355, 166
    round_rect(ctx, lg_x, lg_y, lg_w, lg_h, 7.0)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.94)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BORDER)
    ctx.set_line_width(1.2)
    ctx.stroke()

    for idx, (_, lbl, col, dash) in enumerate(lines_spec):
        yy = lg_y + 20 + idx * 25
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.8)
        ctx.set_dash(dash)
        ctx.move_to(lg_x + 12, yy)
        ctx.line_to(lg_x + 38, yy)
        ctx.stroke()
        ctx.set_dash([])
        draw_text(ctx, lbl, lg_x + 46, yy + 4, size=12.5, color=C_INK, bold=(idx in (1, 4)))


def draw_panel_c(ctx: cairo.Context, data: dict, bx: float, by: float, bw: float, bh: float) -> None:
    draw_panel_box(
        ctx,
        bx,
        by,
        bw,
        bh,
        "C. Finite-Pulse RF Crosstalk Wall: Neutral ¹²¹Sb vs Ionized ¹²¹Sb⁺",
        "Exact time-ordered 8-cycle brickwork across Ω_peak ∈ [5, 25] kHz (473.9 kHz vs 70.0 kHz spacing)",
    )
    rows = data["panel_c_rf_crosstalk"]

    px0, py0 = bx + 86, by + 104
    pw, ph = bw - 120, bh - 176
    xmin, xmax = 3.0, 27.0
    ymin, ymax = 0.0, 1.06

    def xmap(om: float) -> float:
        return px0 + pw * (om - xmin) / (xmax - xmin)

    def ymap(v: float) -> float:
        return py0 + ph * (1.0 - (v - ymin) / (ymax - ymin))

    # Shaded Ionized Crosstalk Danger Zone (Omega > 12 kHz)
    x_warn = xmap(12.0)
    ctx.set_source_rgba(0.75, 0.22, 0.17, 0.08)
    ctx.rectangle(x_warn, py0, px0 + pw - x_warn, ph)
    ctx.fill()
    draw_text(ctx, "Ionized ¹²¹Sb⁺ (70 kHz)", xmap(22.2), ymap(0.91), size=13.0, color=C_RED, bold=True, align="center")
    draw_text(ctx, "RF Crosstalk Collapse Zone", xmap(22.2), ymap(0.85), size=12.5, color=C_RED, align="center")

    # Grid
    for yt in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        yy = ymap(yt)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()
        draw_text(ctx, f"{yt:.1f}", px0 - 10, yy, size=13.5, color=C_MUTED, align="right", valign="middle")

    for om in (5.0, 10.0, 15.0, 20.0, 25.0):
        xx = xmap(om)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(xx, py0)
        ctx.line_to(xx, py0 + ph)
        ctx.stroke()
        draw_text(ctx, f"{int(om)}", xx, py0 + ph + 22, size=13.5, color=C_MUTED, align="center")

    draw_text_rot(ctx, "Noiseless 8-Cycle Process Fidelity F_proc", bx + 24, py0 + ph / 2, -90, size=14.5, color=C_INK, bold=True)
    draw_text(ctx, "Peak RF Rabi Frequency Ω_peak per Tone (kHz)", px0 + pw / 2, py0 + ph + 48, size=14.5, color=C_INK, bold=True, align="center")

    curves = [
        ("neutral_composite_process_fidelity", "Neutral ¹²¹Sb (473.9 kHz) — Comp 90-240-90", C_TEAL, []),
        ("neutral_hann_process_fidelity", "Neutral ¹²¹Sb (473.9 kHz) — Hann π", C_BLUE, [7, 4]),
        ("ionized_hann_process_fidelity", "Ionized ¹²¹Sb⁺ (70.0 kHz) — Hann π", C_ORANGE, []),
        ("ionized_composite_process_fidelity", "Ionized ¹²¹Sb⁺ (70.0 kHz) — Comp 90-240-90", C_RED, []),
    ]

    for key, _, col, dash in curves:
        ctx.set_source_rgb(*col)
        ctx.set_line_width(3.0)
        ctx.set_dash(dash)
        for i, r in enumerate(rows):
            xx, yy = xmap(r["omega_peak_kHz"]), ymap(r[key])
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        ctx.set_dash([])
        for r in rows:
            xx, yy = xmap(r["omega_peak_kHz"]), ymap(r[key])
            ctx.arc(xx, yy, 5.2, 0, 2 * math.pi)
            ctx.fill()

    # Exact clean callout labels (zero overlap with curves!)
    r25 = rows[-1]
    draw_text(ctx, "0.9998", xmap(25.0) - 4, ymap(r25["neutral_composite_process_fidelity"]) - 12, size=12.5, color=C_TEAL, bold=True, align="right")
    draw_text(ctx, "0.573", xmap(25.0) - 4, ymap(r25["ionized_hann_process_fidelity"]) + 22, size=12.5, color=C_ORANGE, bold=True, align="right")
    draw_text(ctx, "0.109", xmap(25.0) - 4, ymap(r25["ionized_composite_process_fidelity"]) - 14, size=12.5, color=C_RED, bold=True, align="right")
    r5 = rows[0]
    draw_text(ctx, "0.996", xmap(5.0) - 2, ymap(r5["ionized_hann_process_fidelity"]) - 12, size=12.5, color=C_ORANGE, bold=True, align="center")
    r10 = rows[1]
    draw_text(ctx, "0.986", xmap(10.0), ymap(r10["ionized_hann_process_fidelity"]) + 20, size=12.0, color=C_ORANGE, bold=True, align="center")
    draw_text(ctx, "0.389", xmap(10.0) + 10, ymap(r10["ionized_composite_process_fidelity"]) - 12, size=12.0, color=C_RED, bold=True)
    r15 = rows[2]
    draw_text(ctx, "0.966", xmap(15.0) - 6, ymap(r15["ionized_hann_process_fidelity"]) + 22, size=12.0, color=C_ORANGE, bold=True, align="right")
    draw_text(ctx, "0.334", xmap(15.0) + 6, ymap(r15["ionized_composite_process_fidelity"]) - 12, size=12.0, color=C_RED, bold=True)

    # Axes
    ctx.set_source_rgb(*C_INK)
    ctx.set_line_width(1.6)
    ctx.move_to(px0, py0)
    ctx.line_to(px0, py0 + ph)
    ctx.line_to(px0 + pw, py0 + ph)
    ctx.stroke()

    # Legend box in open bottom-left quadrant!
    lg_x, lg_y, lg_w, lg_h = px0 + 16, py0 + ph - 134, 415, 118
    round_rect(ctx, lg_x, lg_y, lg_w, lg_h, 7.0)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.94)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BORDER)
    ctx.set_line_width(1.2)
    ctx.stroke()
    for idx, (_, lbl, col, dash) in enumerate(curves):
        yy = lg_y + 22 + idx * 25
        ctx.set_source_rgb(*col)
        ctx.set_line_width(3.0)
        ctx.set_dash(dash)
        ctx.move_to(lg_x + 12, yy)
        ctx.line_to(lg_x + 40, yy)
        ctx.stroke()
        ctx.set_dash([])
        draw_text(ctx, lbl, lg_x + 48, yy + 4, size=12.5, color=C_INK, bold=(idx == 0))


def draw_panel_d(ctx: cairo.Context, data: dict, bx: float, by: float, bw: float, bh: float) -> None:
    draw_panel_box(
        ctx,
        bx,
        by,
        bw,
        bh,
        "D. Multi-Tone SU(8) GRAPE Logical Gates & ¹²¹Sb vs ³¹P Trade-Off",
        "AC-Stark-compensated smooth-Fourier GRAPE (RF ≤ 40 kHz) on Gross binomial code + architecture matrix",
    )
    gr = data["panel_d_su8_grape"]
    gates = gr["gates"]
    comp = data["sb121_vs_p31"]

    # Top half: bar chart for X_L, Z_L, H_L
    px0, py0 = bx + 86, by + 104
    pw, ph = bw - 120, 224
    ymin, ymax = 0.975, 1.003

    def ymap(v: float) -> float:
        return py0 + ph * (1.0 - (v - ymin) / (ymax - ymin))

    for yt in (0.975, 0.980, 0.985, 0.990, 0.995, 1.000):
        yy = ymap(yt)
        is_tgt = abs(yt - 0.995) < 1e-6 or abs(yt - 0.985) < 1e-6
        col_l = C_TEAL if abs(yt - 0.995) < 1e-6 else (C_ORANGE if abs(yt - 0.985) < 1e-6 else C_GRID)
        ctx.set_source_rgb(*col_l)
        ctx.set_line_width(1.3 if is_tgt else 1.0)
        ctx.set_dash([5, 4] if is_tgt else [])
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()
        ctx.set_dash([])
        draw_text(ctx, f"{yt:.3f}", px0 - 10, yy, size=12.5, color=col_l if is_tgt else C_MUTED, bold=is_tgt, align="right", valign="middle")

    draw_text_rot(ctx, "Logical F_L", bx + 24, py0 + ph / 2, -90, size=14.0, color=C_INK, bold=True)

    gnames = ["X_L", "Z_L", "H_L"]
    bars = [
        ("F_L_noiseless_rwa", "Noiseless RWA", C_DARK),
        ("F_L_noiseless_full_crosstalk", "Noiseless Full Crosstalk", C_TEAL),
        ("F_L_noisy_500Hz_strain_mean", "Noisy 500 Hz + Crosstalk", C_BLUE),
    ]
    grp_w = pw / len(gnames)
    bar_w = (grp_w * 0.72) / len(bars)

    for gi, gn in enumerate(gnames):
        gd = gates[gn]
        gx0 = px0 + gi * grp_w + grp_w * 0.14
        for bi, (bk, _, col) in enumerate(bars):
            val = float(gd[bk])
            xb = gx0 + bi * bar_w + 3
            yt = ymap(max(ymin, min(ymax, val)))
            yb = ymap(ymin)
            ctx.set_source_rgb(*col)
            ctx.rectangle(xb, yt, bar_w - 6, max(1.0, yb - yt))
            ctx.fill()
            draw_text(ctx, f"{val:.4f}", xb + (bar_w - 6) / 2.0, yt - 7, size=11.5, color=col, bold=True, align="center")
        xc = px0 + (gi + 0.5) * grp_w
        lbl_bot = f"{gn}  (RF {gd['peak_rabi_used_kHz']:.1f} kHz, leak {gd['p_leak_noiseless_full_crosstalk']*1e3:.2f}e-3)"
        draw_text(ctx, lbl_bot, xc, py0 + ph + 20, size=12.5, color=C_INK, bold=True, align="center")

    ctx.set_source_rgb(*C_INK)
    ctx.set_line_width(1.6)
    ctx.move_to(px0, py0)
    ctx.line_to(px0, py0 + ph)
    ctx.line_to(px0 + pw, py0 + ph)
    ctx.stroke()

    # Legend strip for Panel D bars
    lx = px0
    ly = by + 84
    for _, bname, col in bars:
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx, ly - 9, 14, 11)
        ctx.fill()
        draw_text(ctx, bname, lx + 19, ly, size=12.5, color=C_INK)
        set_font(ctx, 12.5, False)
        lx += 34 + ctx.text_extents(bname).width + 18

    # Bottom half: Clean structured comparison table (121Sb + Q-Echo-8 vs 31P Baseline)
    tx, ty, tw, th = bx + 28, by + 372, bw - 56, 200
    round_rect(ctx, tx, ty, tw, th, 8.0)
    ctx.set_source_rgb(0.965, 0.975, 0.99)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BORDER)
    ctx.set_line_width(1.3)
    ctx.stroke()

    sb = comp["sb121_with_qecho8_exp148"]
    p31 = comp["p31_reference_exp136_exp142"]
    cols = [tx + 16, tx + 345, tx + 695]
    headers = ["Metric (Single Atom in ²⁸Si)", "³¹P Baseline (Exp136/142)", "¹²¹Sb + Q-Echo-8 (Exp148)"]
    ctx.set_source_rgb(*C_DARK)
    ctx.rectangle(tx + 1, ty + 1, tw - 2, 32)
    ctx.fill()
    for cx, htxt in zip(cols, headers):
        draw_text(ctx, htxt, cx, ty + 22, size=13.5, color=(1.0, 1.0, 1.0), bold=True)

    trows = [
        ("Hilbert Dim / Qubits per Atom", "2D (I=1/2) — 1 bare qubit", "8D (I=7/2) — 3 bare or 1 QEC logical"),
        ("Implant Lateral Straggle σ_lat", f"{p31['lateral_straggle_sigma_nm']:.2f} nm (@ 5.0 keV)", f"{sb['lateral_straggle_sigma_nm']:.2f} nm (@ 7.5 keV, -{sb['straggle_improvement_vs_p31_pct']:.1f}%)"),
        ("1 ms @ 500 Hz Static Quad Strain", "Quadrupole-free (Q = 0)", f"0.580 → {sb['qecho8_finite_gross_F_1ms_500Hz_exp148']:.4f} (Comp Q-Echo-8)"),
        ("1 ms Broadband 1/f (500 Hz, 100 kHz)", "Immune (T2n,DD ≈ 1.0 s)", f"T2_eff: 52 µs → 0.43 ms (8×) / 1.45 ms (64×)"),
        ("Control / System Architecture Role", "1 RF tone — Primary Memory Spine", "7 RF tones — Neutral-Only S1-Multi Upgrade"),
    ]
    for ri, (m_lbl, v_p, v_s) in enumerate(trows):
        ry = ty + 54 + ri * 30
        if ri % 2 == 1:
            ctx.set_source_rgba(0.90, 0.93, 0.97, 0.45)
            ctx.rectangle(tx + 2, ry - 18, tw - 4, 28)
            ctx.fill()
        draw_text(ctx, m_lbl, cols[0], ry, size=12.5, color=C_INK, bold=True)
        draw_text(ctx, v_p, cols[1], ry, size=12.5, color=C_MUTED)
        draw_text(ctx, v_s, cols[2], ry, size=12.5, color=C_TEAL if ri in (1, 2) else C_INK, bold=(ri in (1, 2)))


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    ctx.set_source_rgb(*C_BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Top Banner
    ctx.set_source_rgb(*C_DARK)
    ctx.rectangle(0, 0, W, 86)
    ctx.fill()
    draw_text(
        ctx,
        "Exp148 (H166): ¹²¹Sb (I = 7/2) Dynamic Quadrupole Echo & Multi-Tone SU(8) GRAPE Optimal Control",
        56,
        38,
        size=25.0,
        color=(1.0, 1.0, 1.0),
        bold=True,
    )
    verdicts = data["verdicts_sq1_to_sq6"]
    n_p = sum(1 for v in verdicts.values() if v == "PASS")
    sub = (
        f"Exp142 OQ6 Static 500 Hz Wall CLOSED (0.580 → 0.9991 finite-pulse Gross)  |  "
        f"Core SQ1–SQ6: {n_p}/6 PASS (SQ4 Honest Cywiński 1/f Limit)  |  no_lab_measurement=true"
    )
    draw_text(ctx, sub, 56, 68, size=15.0, color=(0.82, 0.89, 0.96))

    # 2x2 Panels
    draw_panel_a(ctx, data, 50, 102, 1126, 600)
    draw_panel_b(ctx, data, 1224, 102, 1126, 600)
    draw_panel_c(ctx, data, 50, 730, 1126, 606)
    draw_panel_d(ctx, data, 1224, 730, 1126, 606)

    # Footer
    draw_text(
        ctx,
        "Atom Lithography Machine v7.0 — Exp148 (H166) | Epistemic: {Literatür}/{Analitik}/{Model}/{Sayısal-Simülasyon} | Exact 8×8 & 16×16 CPTP Lindblad + Anti-Aliased Multi-Tone RF",
        56,
        1376,
        size=13.0,
        color=C_MUTED,
    )
    draw_text(ctx, "2400 × 1400 PyCairo", W - 56, 1376, size=13.0, color=C_MUTED, align="right")

    surf.write_to_png(str(OUT_PNG))
    print(f"[plot_exp148] Wrote {OUT_PNG} ({W}x{H})")


if __name__ == "__main__":
    main()
