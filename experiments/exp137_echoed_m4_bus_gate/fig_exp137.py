"""Generate publication-grade 2400x1400 PyCairo/PIL figure for Exp137 (H155).

Run with system Python having PyCairo + PIL (/usr/bin/python3 -B):
  results/exp137_echoed_m4_bus_gate/fig_exp137_echoed_m4_bus.png

All numbers are read dynamically from results/exp137_echoed_m4_bus_gate/exp137.json.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cairo

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "exp137_echoed_m4_bus_gate"
EXP137_JSON = RESULTS_DIR / "exp137.json"
FIG_PATH = RESULTS_DIR / "fig_exp137_echoed_m4_bus.png"

# Scientific light palette
BG = (0.985, 0.988, 0.992)
PANEL_BG = (1.0, 1.0, 1.0)
HEADER_BG = (0.067, 0.118, 0.204)
INK = (0.10, 0.14, 0.20)
MUTED = (0.38, 0.44, 0.52)
GRID = (0.88, 0.90, 0.93)
BORDER = (0.78, 0.82, 0.87)

TEAL = (0.055, 0.478, 0.455)
NAVY = (0.11, 0.25, 0.52)
BLUE = (0.15, 0.45, 0.82)
AMBER = (0.85, 0.52, 0.05)
CORAL = (0.82, 0.24, 0.22)
PURPLE = (0.48, 0.22, 0.68)
GREEN = (0.10, 0.58, 0.30)
SLATE = (0.45, 0.52, 0.60)


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
    color: tuple[float, float, float] = INK,
    bold: bool = False,
    align: str = "left",
    valign: str = "baseline",
    angle: float = 0.0,
) -> None:
    ctx.save()
    set_font(ctx, size, bold=bold)
    ctx.set_source_rgb(*color)
    ext = ctx.text_extents(text)
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
    ctx.move_to(dx, dy)
    ctx.show_text(text)
    ctx.restore()


def round_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 10.0) -> None:
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2.0, 0.0)
    ctx.arc(x + w - r, y + h - r, r, 0.0, math.pi / 2.0)
    ctx.arc(x + r, y + h - r, r, math.pi / 2.0, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def draw_panel_box(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, tag: str) -> None:
    round_rect(ctx, x, y, w, h, r=12)
    ctx.set_source_rgb(*PANEL_BG)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.8)
    ctx.stroke()
    round_rect(ctx, x + 16, y + 12, 34, 28, r=6)
    ctx.set_source_rgb(*NAVY)
    ctx.fill()
    draw_text(ctx, tag, x + 33, y + 26, size=16.5, color=(1, 1, 1), bold=True, align="center", valign="middle")
    draw_text(ctx, title, x + 60, y + 27, size=18.0, color=INK, bold=True, valign="middle")


def heatmap_color(val: float, vmin: float = 0.85, vmax: float = 0.998) -> tuple[float, float, float]:
    t = max(0.0, min(1.0, (val - vmin) / max(1e-9, vmax - vmin)))
    stops = [
        (0.00, (0.78, 0.22, 0.22)),
        (0.35, (0.91, 0.54, 0.18)),
        (0.65, (0.95, 0.85, 0.36)),
        (0.85, (0.26, 0.72, 0.56)),
        (1.00, (0.04, 0.42, 0.38)),
    ]
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t <= t1:
            u = (t - t0) / max(1e-9, t1 - t0)
            return (c0[0] + u * (c1[0] - c0[0]), c0[1] + u * (c1[1] - c0[1]), c0[2] + u * (c1[2] - c0[2]))
    return stops[-1][1]


def build_figure(data: dict[str, Any]) -> None:
    W, H = 2400, 1400
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    p1 = data["part1_noise_and_unitary"]
    p2 = data["part2_protocol_comparison"]
    p3 = data["part3_2d_phase_map"]
    p4 = data["part4_exp138_pauli_channels"]
    ev = data["prediction_evaluation"]
    cptp = data["global_cptp_audit"]

    # Header banner
    ctx.set_source_rgb(*HEADER_BG)
    ctx.rectangle(0, 0, W, 106)
    ctx.fill()
    draw_text(ctx, "Exp137 (H155): Echoed M4 Cavity-QED Bus CZ Gate under Colored 1/f^alpha Charge Noise", 40, 44, size=28, color=(1, 1, 1), bold=True)
    draw_text(ctx, "CUDA 12x12 Strang-Split Lindblad + Multi-OU 1/f^alpha (N_traj=512/pair) | 3 kOhm NbTiN (L_res=300 um, B_M4=0.1785 T)", 40, 80, size=16.5, color=(0.78, 0.86, 0.96))

    bw, bh = 500, 42
    bx_h, by_h = W - bw - 36, 32
    round_rect(ctx, bx_h, by_h, bw, bh, r=8)
    ctx.set_source_rgb(0.14, 0.24, 0.38); ctx.fill_preserve()
    ctx.set_source_rgb(0.35, 0.65, 0.85); ctx.set_line_width(1.6); ctx.stroke()
    draw_text(
        ctx,
        f"SIMULATION ONLY (no_lab_measurement=true) | {ev['n_pass']}/{ev['n_total']} EC PASS",
        bx_h + bw / 2.0, by_h + bh / 2.0, size=13.5, color=(0.90, 0.96, 1.0), bold=True, align="center", valign="middle",
    )

    pad_x, top_y, gap_x, gap_y = 34, 126, 26, 26
    pw = (W - 2 * pad_x - gap_x) / 2.0
    ph = (H - top_y - 32 - gap_y) / 2.0

    # --- PANEL A: Protocol Fidelity Ladder (Exp131 Markov -> P1 -> P2 -> P3 -> P4) ---
    ax, ay = pad_x, top_y
    draw_panel_box(ctx, ax, ay, pw, ph, "CZ Protocol Ladder at Nominal M4 (S_eps=1.0 ueV/rtHz, Q_r=2e5, alpha=1.0)", "A")
    px0, py0, px1, py1 = ax + 92, ay + 74, ax + pw - 36, ay + ph - 82
    plot_w, plot_h = px1 - px0, py1 - py0
    ymin_a, ymax_a = 0.65, 1.015

    def map_ay(v: float) -> float:
        return py1 - ((max(ymin_a, min(ymax_a, v)) - ymin_a) / (ymax_a - ymin_a)) * plot_h

    for yv in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99]:
        yy = map_ay(yv)
        ctx.set_source_rgb(*GRID); ctx.set_line_width(1.1)
        ctx.move_to(px0, yy); ctx.line_to(px1, yy); ctx.stroke()
        draw_text(ctx, f"{yv:.2f}", px0 - 12, yy, size=14, color=MUTED, align="right", valign="middle")

    # Threshold lines: 0.99 SC & Exp131 0.777 baseline
    yy99 = map_ay(0.99)
    ctx.save(); ctx.set_source_rgb(*GREEN); ctx.set_dash([7, 5]); ctx.set_line_width(1.7)
    ctx.move_to(px0, yy99); ctx.line_to(px1, yy99); ctx.stroke(); ctx.restore()
    draw_text(ctx, "0.99 Surface-Code Target", px0 + 10, yy99 - 8, size=12.5, color=GREEN, bold=True)

    f131 = p1["exp131_cz_anchor_ref"]
    yy131 = map_ay(f131)
    ctx.save(); ctx.set_source_rgb(*CORAL); ctx.set_dash([6, 4]); ctx.set_line_width(1.6)
    ctx.move_to(px0, yy131); ctx.line_to(px1, yy131); ctx.stroke(); ctx.restore()
    draw_text(ctx, f"Exp131 Bare Markov ({f131:.3f})", px0 + 10, yy131 - 9, size=12.5, color=CORAL, bold=True, align="left")

    groups_a = [
        ("Markov\nAnchor", p2["markov_anchor_P1"]["F_avg"], None, p2["markov_anchor_P1"]["F_Bell"]),
        ("P1 Bare\n(1/f)", p2["nominal_S1p0_dw_only"]["P1"]["F_avg"], p2["nominal_S1p0_full_dw_dg"]["P1"]["F_avg"], p2["nominal_S1p0_full_dw_dg"]["P1"]["F_Bell"]),
        ("P2 FF-Echo\n(XX)", p2["nominal_S1p0_dw_only"]["P2"]["F_avg"], p2["nominal_S1p0_full_dw_dg"]["P2"]["F_avg"], p2["nominal_S1p0_full_dw_dg"]["P2"]["F_Bell"]),
        ("P3 XY4\nDRAG", p2["nominal_S1p0_dw_only"]["P3"]["F_avg"], p2["nominal_S1p0_full_dw_dg"]["P3"]["F_avg"], p2["nominal_S1p0_full_dw_dg"]["P3"]["F_Bell"]),
        ("P4 Sweet-Spot\nParam Echo", p2["nominal_S1p0_dw_only"]["P4"]["F_avg"], p2["nominal_S1p0_full_dw_dg"]["P4"]["F_avg"], p2["nominal_S1p0_full_dw_dg"]["P4"]["F_Bell"]),
    ]
    slot_w = plot_w / len(groups_a)
    bar_w = slot_w * 0.28

    for idx, (lbl, f_dw, f_dg, f_bell) in enumerate(groups_a):
        cx = px0 + (idx + 0.5) * slot_w
        if idx == 4:
            ctx.set_source_rgba(0.055, 0.478, 0.455, 0.08)
            ctx.rectangle(cx - slot_w * 0.44, py0, slot_w * 0.88, plot_h); ctx.fill()

        if f_dg is None:
            # Single Markov anchor bar centered
            ytop = map_ay(f_dw)
            ctx.set_source_rgb(*CORAL)
            ctx.rectangle(cx - bar_w * 0.7, ytop, bar_w * 1.4, py1 - ytop); ctx.fill()
            draw_text(ctx, f"{f_dw:.3f}", cx, ytop - 8, size=13, color=CORAL, bold=True, align="center")
        else:
            # Left bar: dw-only (teal)
            yt1 = map_ay(f_dw)
            ctx.set_source_rgb(*TEAL)
            ctx.rectangle(cx - bar_w - 3, yt1, bar_w, py1 - yt1); ctx.fill()
            draw_text(ctx, f"{f_dw:.3f}", cx - bar_w / 2.0 - 3, yt1 - 7, size=12, color=TEAL, bold=True, align="center")

            # Right bar: full dw+dg (navy)
            yt2 = map_ay(f_dg)
            ctx.set_source_rgb(*NAVY)
            ctx.rectangle(cx + 3, yt2, bar_w, py1 - yt2); ctx.fill()
            draw_text(ctx, f"{f_dg:.3f}", cx + bar_w / 2.0 + 3, yt2 - 7, size=12, color=NAVY, bold=True, align="center")

            # Diamond: full F_Bell (green/amber)
            yb = map_ay(f_bell)
            ctx.set_source_rgb(*GREEN)
            ctx.move_to(cx + bar_w + 13, yb - 6); ctx.line_to(cx + bar_w + 19, yb)
            ctx.line_to(cx + bar_w + 13, yb + 6); ctx.line_to(cx + bar_w + 7, yb); ctx.close_path(); ctx.fill()

        lines = lbl.split("\n")
        draw_text(ctx, lines[0], cx, py1 + 22, size=13.5, color=INK, bold=(idx == 4), align="center")
        if len(lines) > 1:
            draw_text(ctx, lines[1], cx, py1 + 40, size=12.5, color=MUTED, align="center")

    ctx.set_source_rgb(*INK); ctx.set_line_width(1.8)
    ctx.move_to(px0, py0); ctx.line_to(px0, py1); ctx.line_to(px1, py1); ctx.stroke()
    draw_text(ctx, "Universal CZ Fidelity (F_avg / F_Bell)", ax + 26, (py0 + py1) / 2.0, size=15.5, color=INK, bold=True, align="center", valign="middle", angle=-math.pi / 2.0)
    draw_text(ctx, "6 Heterogeneous Exp131 Best-of-6 Pairs (3,072 Trajectories/Protocol; t_pi=15 ns, eps_rot=1.5%)", (px0 + px1) / 2.0, ay + ph - 14, size=12.8, color=MUTED, align="center")

    # Legend in Panel A bottom-left (inside clear zone above 0.65)
    lx_a, ly_a = px0 + 12, py0 + 26
    round_rect(ctx, lx_a, ly_a, 295, 76, r=7)
    ctx.set_source_rgba(1, 1, 1, 0.94); ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER); ctx.set_line_width(1.2); ctx.stroke()
    ctx.set_source_rgb(*TEAL); ctx.rectangle(lx_a + 10, ly_a + 11, 16, 12); ctx.fill()
    draw_text(ctx, "F_avg: 1/f Freq. Noise (dw only)", lx_a + 34, ly_a + 21, size=12.5, color=INK)
    ctx.set_source_rgb(*NAVY); ctx.rectangle(lx_a + 10, ly_a + 32, 16, 12); ctx.fill()
    draw_text(ctx, "F_avg: Full 1/f (dw + dg jitter)", lx_a + 34, ly_a + 42, size=12.5, color=INK, bold=True)
    ctx.set_source_rgb(*GREEN)
    ctx.move_to(lx_a + 18, ly_a + 54); ctx.line_to(lx_a + 24, ly_a + 60); ctx.line_to(lx_a + 18, ly_a + 66); ctx.line_to(lx_a + 12, ly_a + 60); ctx.close_path(); ctx.fill()
    draw_text(ctx, "F_Bell (CZ|++>, Full dw + dg)", lx_a + 34, ly_a + 64, size=12.5, color=GREEN, bold=True)

    # --- PANEL B: 5x4 (S_eps, Q_r) 2D Fault-Tolerance Phase Map (P4) ---
    bx, by = pad_x + pw + gap_x, top_y
    draw_panel_box(ctx, bx, by, pw, ph, "2D Fault-Tolerance Phase Map: S_eps vs Q_r (P4 Echo CZ, Full dw+dg)", "B")
    hm_x0, hm_y0, hm_x1, hm_y1 = bx + 110, by + 80, bx + pw - 102, by + ph - 82
    hm_w, hm_h = hm_x1 - hm_x0, hm_y1 - hm_y0

    s_grid = p3["s_eps_uev_grid"]
    q_grid = p3["q_r_grid"]
    pm_lk = {(pt["s_eps_uev"], pt["q_r"]): pt for pt in p3["points"]}
    nx_g, ny_g = len(s_grid), len(q_grid)
    cw, ch = hm_w / nx_g, hm_h / ny_g

    for j, qr in enumerate(q_grid):
        row_y = hm_y1 - (j + 1) * ch
        for i, sv in enumerate(s_grid):
            col_x = hm_x0 + i * cw
            pt = pm_lk[(sv, qr)]
            fb = pt["F_Bell"]
            fa = pt["F_avg"]
            col = heatmap_color(fb, vmin=0.84, vmax=0.998)
            ctx.set_source_rgb(*col)
            ctx.rectangle(col_x + 2, row_y + 2, cw - 4, ch - 4); ctx.fill()

            if fb >= 0.990:
                ctx.set_source_rgb(1.0, 0.86, 0.18)
                ctx.set_line_width(3.4)
                ctx.rectangle(col_x + 3.5, row_y + 3.5, cw - 7, ch - 7); ctx.stroke()
            elif sv >= 5.0 and qr <= 5e4:
                ctx.set_source_rgb(*CORAL)
                ctx.set_line_width(3.2)
                ctx.rectangle(col_x + 3.5, row_y + 3.5, cw - 7, ch - 7); ctx.stroke()

            txt_c = (1, 1, 1) if (fb >= 0.968 or fb < 0.89) else INK
            draw_text(ctx, f"{fb:.4f}", col_x + cw / 2.0, row_y + ch / 2.0 - 14, size=16, color=txt_c, bold=True, align="center", valign="middle")
            draw_text(ctx, f"F_avg={fa:.3f}", col_x + cw / 2.0, row_y + ch / 2.0 + 10, size=12, color=txt_c, align="center", valign="middle")
            if fb >= 0.990:
                draw_text(ctx, ">=99% SC", col_x + cw / 2.0, row_y + ch / 2.0 + 28, size=11.5, color=(1.0, 0.93, 0.35), bold=True, align="center", valign="middle")

        q_lbl = f"{qr/1e5:.1f}e5" if qr >= 1e5 else f"{qr/1e4:.0f}e4"
        draw_text(ctx, q_lbl, hm_x0 - 12, row_y + ch / 2.0, size=14.5, color=INK, bold=True, align="right", valign="middle")

    for i, sv in enumerate(s_grid):
        s_lbl = f"{sv:.2f}" if sv < 0.5 else f"{sv:.1f}"
        draw_text(ctx, s_lbl, hm_x0 + (i + 0.5) * cw, hm_y1 + 24, size=14.5, color=INK, bold=True, align="center")

    # Colorbar
    cb_x, cb_w = hm_x1 + 20, 22
    for s in range(120):
        frac = s / 119.0
        val = 0.84 + frac * (0.998 - 0.84)
        ctx.set_source_rgb(*heatmap_color(val, 0.84, 0.998))
        yy = hm_y1 - frac * hm_h
        ctx.rectangle(cb_x, yy - hm_h / 119.0, cb_w, hm_h / 119.0 + 1); ctx.fill()
    ctx.set_source_rgb(*INK); ctx.set_line_width(1.2); ctx.rectangle(cb_x, hm_y0, cb_w, hm_h); ctx.stroke()
    for tick in [0.85, 0.90, 0.95, 0.99]:
        yy = hm_y1 - ((tick - 0.84) / (0.998 - 0.84)) * hm_h
        draw_text(ctx, f"{tick:.2f}", cb_x + cb_w + 8, yy, size=13, color=INK, bold=(tick == 0.99), valign="middle")

    draw_text(ctx, "Resonator Loaded Q_r", bx + 28, (hm_y0 + hm_y1) / 2.0, size=15.5, color=INK, bold=True, align="center", valign="middle", angle=-math.pi / 2.0)
    draw_text(ctx, "1/f Charge Noise Amplitude S_eps(1 Hz) [ueV / sqrt(Hz)] (Cell top: F_Bell, bottom: F_avg)", (hm_x0 + hm_x1) / 2.0, by + ph - 16, size=13, color=MUTED, align="center")

    # --- PANEL C: Noise Color alpha in {0.8, 1.0, 1.2} Scaling + Cywinski Filter Verification ---
    cx, cy = pad_x, top_y + ph + gap_y
    draw_panel_box(ctx, cx, cy, pw, ph, "Noise Color Exponent Scaling: F_avg(alpha) for 1/f^alpha (S_eps=1.0, Q_r=2e5)", "C")
    cx0, cy0, cx1, cy1 = cx + 92, cy + 74, cx + pw - 36, cy + ph - 80
    cw_p, ch_p = cx1 - cx0, cy1 - cy0
    alphas = [0.8, 1.0, 1.2]
    asw = p2["alpha_sweep_P3_and_P4"]
    all_vals_c = [asw[f"alpha_{a:.1f}"][pr]["F_avg"] for a in alphas for pr in ("P1", "P2", "P3", "P4")]
    ymin_c = max(0.30, math.floor(min(all_vals_c) * 20.0) / 20.0 - 0.05)
    ymax_c = 1.02

    def map_cx(av: float) -> float:
        return cx0 + ((av - 0.72) / (1.28 - 0.72)) * cw_p

    def map_cy(fv: float) -> float:
        return cy1 - ((fv - ymin_c) / (ymax_c - ymin_c)) * ch_p

    step_y = 0.10 if (ymax_c - ymin_c) > 0.45 else 0.05
    yv = math.ceil(ymin_c / step_y) * step_y
    while yv <= 0.995:
        yy = map_cy(yv)
        ctx.set_source_rgb(*GRID); ctx.set_line_width(1.1)
        ctx.move_to(cx0, yy); ctx.line_to(cx1, yy); ctx.stroke()
        draw_text(ctx, f"{yv:.2f}", cx0 - 12, yy, size=14, color=MUTED, align="right", valign="middle")
        yv += step_y

    # 0.99 line
    yy99_c = map_cy(0.99)
    ctx.save(); ctx.set_source_rgb(*GREEN); ctx.set_dash([7, 5]); ctx.set_line_width(1.6)
    ctx.move_to(cx0, yy99_c); ctx.line_to(cx1, yy99_c); ctx.stroke(); ctx.restore()
    draw_text(ctx, "0.99 Target", cx1 - 8, yy99_c - 8, size=12.5, color=GREEN, bold=True, align="right")

    series_c = [
        ("P4", TEAL, False, "P4 Sweet-Spot Param. Echo"),
        ("P3", BLUE, False, "P3 XY4-Embedded DRAG-CZ"),
        ("P2", AMBER, True, "P2 FF-Echo-CZ (XX)"),
        ("P1", CORAL, True, "P1 Bare Dispersive CZ (1/f)"),
    ]
    for pr, col, dashed, lbl in series_c:
        pts = [(map_cx(a), map_cy(asw[f"alpha_{a:.1f}"][pr]["F_avg"])) for a in alphas]
        ctx.save(); ctx.set_source_rgb(*col); ctx.set_line_width(3.0 if pr in ("P4", "P3") else 2.5)
        if dashed: ctx.set_dash([8, 5])
        ctx.move_to(*pts[0])
        for pt in pts[1:]:
            ctx.line_to(*pt)
        ctx.stroke(); ctx.restore()
        for (px, py), a in zip(pts, alphas):
            ctx.set_source_rgb(*col); ctx.arc(px, py, 5.8, 0, 2 * math.pi); ctx.fill()
            ctx.set_source_rgb(1, 1, 1); ctx.arc(px, py, 2.4, 0, 2 * math.pi); ctx.fill()
            if pr in ("P4", "P1"):
                dy_lbl = -12 if pr == "P4" else 18
                draw_text(ctx, f"{asw[f'alpha_{a:.1f}'][pr]['F_avg']:.3f}", px, py + dy_lbl, size=12.5, color=col, bold=True, align="center")

    for a in alphas:
        px = map_cx(a)
        ctx.set_source_rgb(*INK); ctx.set_line_width(1.4)
        ctx.move_to(px, cy1); ctx.line_to(px, cy1 + 6); ctx.stroke()
        tag_a = "whiter" if a < 0.9 else ("pink 1/f" if a < 1.1 else "redder")
        draw_text(ctx, f"alpha = {a:.1f} ({tag_a})", px, cy1 + 24, size=14, color=INK, bold=(abs(a - 1.0) < 1e-6), align="center")

    ctx.set_source_rgb(*INK); ctx.set_line_width(1.8)
    ctx.move_to(cx0, cy0); ctx.line_to(cx0, cy1); ctx.line_to(cx1, cy1); ctx.stroke()
    draw_text(ctx, "Average Gate Fidelity F_avg(CZ)", cx + 26, (cy0 + cy1) / 2.0, size=15.5, color=INK, bold=True, align="center", valign="middle", angle=-math.pi / 2.0)
    draw_text(ctx, "1/f^alpha Spectral Exponent (Band [1 Hz, 100 MHz], M=40 OU Fluctuators)", (cx0 + cx1) / 2.0, cy + ph - 14, size=13, color=MUTED, align="center")

    # Legend + Cywinski box bottom-right inside Panel C
    cyw = p1["cywinski_filter_theory"]
    ou = p1["ou_psd_audit"]
    lx_c, ly_c = cx1 - 340, cy1 - 164
    round_rect(ctx, lx_c, ly_c, 328, 152, r=7)
    ctx.set_source_rgba(1, 1, 1, 0.94); ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER); ctx.set_line_width(1.2); ctx.stroke()
    for idx, (_, col, dashed, lbl) in enumerate(series_c):
        yy = ly_c + 16 + idx * 22
        ctx.save(); ctx.set_source_rgb(*col); ctx.set_line_width(2.8)
        if dashed: ctx.set_dash([6, 4])
        ctx.move_to(lx_c + 10, yy); ctx.line_to(lx_c + 36, yy); ctx.stroke(); ctx.restore()
        draw_text(ctx, lbl, lx_c + 44, yy + 4, size=12.5, color=INK, bold=(idx == 0))
    draw_text(ctx, f"Cywinski XY4 Gain (a=0.8/1.0/1.2): {cyw['alpha_0.8']['suppression_xy4_x']:.0f}x / {cyw['alpha_1.0']['suppression_xy4_x']:.0f}x / {cyw['alpha_1.2']['suppression_xy4_x']:.0f}x", lx_c + 10, ly_c + 114, size=11.8, color=NAVY, bold=True)
    draw_text(ctx, f"Multi-OU PSD err: {ou['worst_psd_rel_err']*100:.1f}% | RMS err: {ou['worst_rms_rel_err']*100:.1f}%", lx_c + 10, ly_c + 136, size=11.8, color=MUTED)

    # --- PANEL D: Exact 16-Pauli Error Channel Breakdown for Exp138 Decoder ---
    dx, dy = pad_x + pw + gap_x, top_y + ph + gap_y
    draw_panel_box(ctx, dx, dy, pw, ph, "Exact 16-Pauli Error Channel Budget for Exp138 Surface-Code Decoder", "D")
    dx0, dy0, dx1, dy1 = dx + 92, dy + 74, dx + pw - 36, dy + ph - 84
    dw_p, dh_p = dx1 - dx0, dy1 - dy0

    ch_items = [
        ("P1 Bare\n(S=1.0)", p4["P1_Bare_1f_S1p0"]),
        ("P3 XY4-DRAG\n(S=1.0)", p4["P3_XY4_DRAG_S1p0"]),
        ("P4 Best\n(S=1.0)", p4["best_protocol_S1p0"]),
        ("P4 Best\n(S=0.5)", p4["best_protocol_S0p5"]),
        ("P4 Best\n(S=0.25)", p4["best_protocol_S0p25"]),
    ]
    max_err_pct = max(item[1]["p_total_err"] * 100.0 for item in ch_items)
    ymax_d = max(5.0, math.ceil(max_err_pct * 1.18))

    def map_dy(pct: float) -> float:
        return dy1 - (pct / ymax_d) * dh_p

    # Horizontal grid lines (5 clean steps)
    step_d = max(1.0, round(ymax_d / 5.0))
    yv_d = 0.0
    while yv_d <= ymax_d + 1e-9:
        yy = map_dy(yv_d)
        ctx.set_source_rgb(*GRID); ctx.set_line_width(1.1)
        ctx.move_to(dx0, yy); ctx.line_to(dx1, yy); ctx.stroke()
        draw_text(ctx, f"{yv_d:.0f}%", dx0 - 12, yy, size=14, color=MUTED, align="right", valign="middle")
        yv_d += step_d

    # 1% surface-code threshold dashed line (labeled cleanly inside Panel D legend box)
    if 1.0 < ymax_d:
        yy1 = map_dy(1.0)
        ctx.save(); ctx.set_source_rgb(*GREEN); ctx.set_dash([7, 5]); ctx.set_line_width(1.6)
        ctx.move_to(dx0, yy1); ctx.line_to(dx1, yy1); ctx.stroke(); ctx.restore()

    comp_colors = [
        ("p_Z", BLUE, "p_Z (Dephasing)"),
        ("p_ZZ", NAVY, "p_ZZ (Correlated ZZ)"),
        ("p_X", CORAL, "p_X (Bit-Flip)"),
        ("p_Y", AMBER, "p_Y (Y-Error)"),
        ("p_leak", PURPLE, "p_leak (Cavity)"),
    ]
    slot_wd = dw_p / len(ch_items)
    bar_wd = slot_wd * 0.48

    for idx, (lbl, ch) in enumerate(ch_items):
        cx_d = dx0 + (idx + 0.5) * slot_wd
        acc_pct = 0.0
        for key, col, _ in comp_colors:
            if key == "p_leak":
                continue  # draw leak as small separate cap or note so stacked bar == p_total_err!
            val_pct = max(0.0, ch[key] * 100.0)
            y_bot = map_dy(acc_pct)
            y_top = map_dy(acc_pct + val_pct)
            ctx.set_source_rgb(*col)
            ctx.rectangle(cx_d - bar_wd / 2.0, y_top, bar_wd, max(0.0, y_bot - y_top)); ctx.fill()
            acc_pct += val_pct

        tot_pct = ch["p_total_err"] * 100.0
        draw_text(ctx, f"{tot_pct:.2f}%", cx_d, map_dy(tot_pct) - 18, size=13, color=INK, bold=True, align="center")
        draw_text(ctx, f"eta_Z={ch['z_bias_ratio']:.1f}", cx_d, map_dy(tot_pct) - 4, size=11.5, color=NAVY, align="center")

        lines = lbl.split("\n")
        draw_text(ctx, lines[0], cx_d, dy1 + 22, size=13.5, color=INK, bold=(idx >= 2), align="center")
        draw_text(ctx, lines[1], cx_d, dy1 + 40, size=12.5, color=MUTED, align="center")

    ctx.set_source_rgb(*INK); ctx.set_line_width(1.8)
    ctx.move_to(dx0, dy0); ctx.line_to(dx0, dy1); ctx.line_to(dx1, dy1); ctx.stroke()
    draw_text(ctx, "Total 2-Qubit Pauli Error p_total_err [%]", dx + 26, (dy0 + dy1) / 2.0, size=15.5, color=INK, bold=True, align="center", valign="middle", angle=-math.pi / 2.0)
    draw_text(ctx, "Exact 16-Element Choi / PTM Projection (Q_r = 2e5, 6 Best-of-6 Pairs, 3,072 Traj/Bar)", (dx0 + dx1) / 2.0, dy + ph - 14, size=12.8, color=MUTED, align="center")

    # Legend & CPTP/Exp138 summary card in top-right of Panel D
    lx_d, ly_d = dx1 - 344, dy0 + 10
    round_rect(ctx, lx_d, ly_d, 332, 174, r=8)
    ctx.set_source_rgba(1, 1, 1, 0.95); ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER); ctx.set_line_width(1.3); ctx.stroke()
    for idx, (_, col, lbl) in enumerate(comp_colors[:4]):
        yy = ly_d + 14 + idx * 21
        ctx.set_source_rgb(*col); ctx.rectangle(lx_d + 12, yy - 6, 15, 12); ctx.fill()
        draw_text(ctx, lbl, lx_d + 35, yy + 4, size=12.5, color=INK, bold=(idx == 0))
    # Green dashed 1% SC threshold entry
    yy_g = ly_d + 14 + 4 * 21
    ctx.save(); ctx.set_source_rgb(*GREEN); ctx.set_dash([5, 3]); ctx.set_line_width(2.0)
    ctx.move_to(lx_d + 10, yy_g); ctx.line_to(lx_d + 29, yy_g); ctx.stroke(); ctx.restore()
    draw_text(ctx, "1.0% Surface-Code Error Threshold", lx_d + 35, yy_g + 4, size=12.2, color=GREEN, bold=True)

    ch1 = p4["best_protocol_S1p0"]
    ch05 = p4["best_protocol_S0p5"]
    draw_text(ctx, f"P4 (S=1.0): p_err={ch1['p_total_err']*100:.2f}%, leak={ch1['p_leak']*100:.3f}%", lx_d + 12, ly_d + 126, size=12, color=TEAL, bold=True)
    draw_text(ctx, f"P4 (S=0.5): p_err={ch05['p_total_err']*100:.2f}%, leak={ch05['p_leak']*100:.3f}%", lx_d + 12, ly_d + 145, size=12, color=TEAL, bold=True)
    draw_text(ctx, f"CPTP max|Tr-1|={cptp['max_trace_err']:.1e} | sum_err={abs(ch1['pauli_sum']-1):.1e}", lx_d + 12, ly_d + 163, size=11.3, color=MUTED)

    surf.write_to_png(str(FIG_PATH))


def main() -> None:
    data = json.loads(EXP137_JSON.read_text(encoding="utf-8"))
    build_figure(data)
    print(f"[fig_exp137] Wrote {FIG_PATH.name} (2400x1400)")


if __name__ == "__main__":
    main()
