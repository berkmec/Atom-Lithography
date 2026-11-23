"""Generate publication-grade PyCairo/PIL figures for Exp131 (H149).

Run with system Python having PyCairo + PIL (e.g. /usr/bin/python3 -B):
  - results/exp131_scalable_m4_architecture/fig_exp131_m4_bus_fidelity.png
  - results/exp131_scalable_m4_architecture/fig_exp131_2d_percolation.png

All numbers are read dynamically from results/exp131_scalable_m4_architecture/exp131.json.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cairo

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "exp131_scalable_m4_architecture"
EXP131_JSON = RESULTS_DIR / "exp131.json"
FIG1_PATH = RESULTS_DIR / "fig_exp131_m4_bus_fidelity.png"
FIG2_PATH = RESULTS_DIR / "fig_exp131_2d_percolation.png"

# Palette (clean scientific light theme)
BG = (0.985, 0.988, 0.992)
PANEL_BG = (1.0, 1.0, 1.0)
HEADER_BG = (0.067, 0.118, 0.204)
INK = (0.10, 0.14, 0.20)
MUTED = (0.38, 0.44, 0.52)
GRID = (0.88, 0.90, 0.93)
BORDER = (0.78, 0.82, 0.87)

TEAL = (0.055, 0.478, 0.455)
TEAL_LIGHT = (0.12, 0.67, 0.63)
NAVY = (0.11, 0.25, 0.52)
BLUE = (0.15, 0.45, 0.82)
AMBER = (0.85, 0.52, 0.05)
CORAL = (0.82, 0.24, 0.22)
PURPLE = (0.48, 0.22, 0.68)
GREEN = (0.10, 0.58, 0.30)
SLATE_DEAD = (0.80, 0.84, 0.88)


def set_font(ctx: cairo.Context, size: float, bold: bool = False, family: str = "DejaVu Sans") -> None:
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(family, cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)


def draw_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 16,
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


def draw_header(ctx: cairo.Context, width: int, title: str, subtitle: str, badge: str) -> None:
    ctx.set_source_rgb(*HEADER_BG)
    ctx.rectangle(0, 0, width, 112)
    ctx.fill()
    draw_text(ctx, title, 44, 48, size=30, color=(1.0, 1.0, 1.0), bold=True)
    draw_text(ctx, subtitle, 44, 84, size=17, color=(0.78, 0.86, 0.96), bold=False)

    # Epistemic badge on right
    bw, bh = 510, 44
    bx, by = width - bw - 36, 34
    round_rect(ctx, bx, by, bw, bh, r=8)
    ctx.set_source_rgb(0.14, 0.24, 0.38)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.35, 0.65, 0.85)
    ctx.set_line_width(1.6)
    ctx.stroke()
    draw_text(ctx, badge, bx + bw / 2.0, by + bh / 2.0, size=13.5, color=(0.90, 0.96, 1.0), bold=True, align="center", valign="middle")


def draw_panel_box(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, tag: str) -> None:
    round_rect(ctx, x, y, w, h, r=12)
    ctx.set_source_rgb(*PANEL_BG)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.8)
    ctx.stroke()
    # Panel letter tag pill
    round_rect(ctx, x + 16, y + 14, 34, 30, r=6)
    ctx.set_source_rgb(*NAVY)
    ctx.fill()
    draw_text(ctx, tag, x + 33, y + 29, size=17, color=(1, 1, 1), bold=True, align="center", valign="middle")
    draw_text(ctx, title, x + 62, y + 30, size=19, color=INK, bold=True, valign="middle")


def heatmap_color(val: float, vmin: float = 0.55, vmax: float = 0.995) -> tuple[float, float, float]:
    t = max(0.0, min(1.0, (val - vmin) / max(1e-9, vmax - vmin)))
    # Perceptually ordered coral -> amber -> pale yellow -> teal -> deep emerald
    stops = [
        (0.00, (0.78, 0.22, 0.22)),
        (0.35, (0.91, 0.52, 0.18)),
        (0.65, (0.95, 0.84, 0.36)),
        (0.85, (0.28, 0.72, 0.56)),
        (1.00, (0.04, 0.42, 0.38)),
    ]
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t <= t1:
            u = (t - t0) / max(1e-9, t1 - t0)
            return (c0[0] + u * (c1[0] - c0[0]), c0[1] + u * (c1[1] - c0[1]), c0[2] + u * (c1[2] - c0[2]))
    return stops[-1][1]


def build_fig1_bus_fidelity(data: dict[str, Any]) -> None:
    W, H = 2400, 1580
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    p1 = data["part1_flipflop_straggle"]
    p2 = data["part2_lindblad_bus"]
    ev = data["prediction_evaluation"]

    draw_header(
        ctx, W,
        "Exp131 (H149): M4 High-Impedance NbTiN Cavity-QED Bus & 31P Flip-Flop Qubit Fidelity",
        "Exact 4x4 Tosi Donor-Interface Hamiltonian + 12x12 Lindblad Master Equation (Exp109 NbTiN & Exp124 5 keV Straggle)",
        f"SIMULATION ONLY (no_lab_measurement=true) | {ev['n_pass']}/{ev['n_total']} CM PASS",
    )

    pad_x, top_y, gap_x, gap_y = 36, 134, 28, 28
    pw = (W - 2 * pad_x - gap_x) / 2.0
    ph = (H - top_y - 36 - gap_y) / 2.0

    # --- PANEL A: Delta_z_cap yield & sweet-spot tuning ---
    ax, ay = pad_x, top_y
    draw_panel_box(ctx, ax, ay, pw, ph, "Epitaxial Capping Delta_z_cap & DC Sweet-Spot Tuning (Exp124 Straggle)", "A")
    px0, py0, px1, py1 = ax + 96, ay + 84, ax + pw - 42, ay + ph - 90
    plot_w, plot_h = px1 - px0, py1 - py0

    # Grid lines y = 0..1.0
    for yv in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        yy = py1 - yv * plot_h
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.2)
        ctx.move_to(px0, yy); ctx.line_to(px1, yy); ctx.stroke()
        draw_text(ctx, f"{int(yv * 100)}%", px0 - 12, yy, size=15, color=MUTED, align="right", valign="middle")

    # 70% CM1 threshold dashed line
    y70 = py1 - 0.70 * plot_h
    ctx.save()
    ctx.set_source_rgb(*GREEN)
    ctx.set_dash([8, 6])
    ctx.set_line_width(1.8)
    ctx.move_to(px0, y70); ctx.line_to(px1, y70); ctx.stroke()
    ctx.restore()
    draw_text(ctx, "70% Yield Target", px1 - 8, y70 - 8, size=13.5, color=GREEN, bold=True, align="right")

    sweep = p1["sweep"]
    n_caps = len(sweep)
    slot_w = plot_w / n_caps
    bar_w = slot_w * 0.30
    opt_dz = p1["optimal_capping"]["delta_z_cap_nm"]

    for i, row in enumerate(sweep):
        cx = px0 + (i + 0.5) * slot_w
        yt = row["yield_C_ge_100_tuned"]
        y0 = row["yield_C_ge_100_fixed_eps0"]
        dz = row["delta_z_cap_nm"]

        # Highlight optimal cap background band
        if abs(dz - opt_dz) < 1e-6:
            ctx.set_source_rgba(0.055, 0.478, 0.455, 0.10)
            ctx.rectangle(cx - slot_w * 0.44, py0, slot_w * 0.88, plot_h)
            ctx.fill()

        # Fixed eps=0 bar (left, amber)
        h0 = y0 * plot_h
        ctx.set_source_rgb(*AMBER)
        ctx.rectangle(cx - bar_w - 3, py1 - h0, bar_w, h0)
        ctx.fill()
        draw_text(ctx, f"{y0*100:.0f}%", cx - bar_w / 2.0 - 3, py1 - h0 - 8, size=13, color=AMBER, bold=True, align="center")

        # Tuned eps* bar (right, teal)
        ht = yt * plot_h
        ctx.set_source_rgb(*TEAL)
        ctx.rectangle(cx + 3, py1 - ht, bar_w, ht)
        ctx.fill()
        draw_text(ctx, f"{yt*100:.1f}%", cx + bar_w / 2.0 + 3, py1 - ht - 8, size=13.5, color=TEAL, bold=True, align="center")

        # Median C pill below x-label
        draw_text(ctx, f"{dz:.0f} nm", cx, py1 + 26, size=15.5, color=INK, bold=(abs(dz - opt_dz) < 1e-6), align="center")
        med_c = row["median_C_tuned"]
        c_lbl = f"med C={med_c:,.0f}" if med_c >= 10 else "med C=0"
        draw_text(ctx, c_lbl, cx, py1 + 48, size=12.5, color=TEAL if med_c >= 100 else CORAL, bold=True, align="center")

    # Axes frame
    ctx.set_source_rgb(*INK); ctx.set_line_width(1.8)
    ctx.move_to(px0, py0); ctx.line_to(px0, py1); ctx.line_to(px1, py1); ctx.stroke()
    draw_text(ctx, "Strong-Coupling Yield P(C >= 100)", ax + 28, (py0 + py1) / 2.0, size=16, color=INK, bold=True, align="center", valign="middle", angle=-math.pi / 2.0)
    draw_text(ctx, "Epitaxial 28Si Capping Thickness Delta_z_cap (N = 2,000 donors/cap; Z_r=3 kOhm, Q_L=2e5, S_eps=1.0 ueV/rtHz)", (px0 + px1) / 2.0, ay + ph - 16, size=13.5, color=MUTED, align="center")

    # Legend inside Panel A top-left
    lx, ly = px0 + 18, py0 + 10
    round_rect(ctx, lx, ly, 315, 58, r=7)
    ctx.set_source_rgba(1, 1, 1, 0.94); ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER); ctx.set_line_width(1.2); ctx.stroke()
    ctx.set_source_rgb(*TEAL); ctx.rectangle(lx + 12, ly + 11, 18, 13); ctx.fill()
    draw_text(ctx, "Local DC Sweet-Spot eps*(x,y,z)", lx + 38, ly + 22, size=13.5, color=INK, bold=True)
    ctx.set_source_rgb(*AMBER); ctx.rectangle(lx + 12, ly + 35, 18, 13); ctx.fill()
    draw_text(ctx, "Fixed Untuned Bias (eps = 0)", lx + 38, ly + 46, size=13.5, color=INK)

    # --- PANEL B: 5x5 (Z_r, Q_L) Phase Map Heatmap at S_eps = 0.5 ueV/rtHz ---
    bx, by = pad_x + pw + gap_x, top_y
    draw_panel_box(ctx, bx, by, pw, ph, "2-Cell Bell Fidelity Phase Map: Z_r vs Q_L (Low-Noise S_eps = 0.5 ueV/rtHz)", "B")
    hm_x0, hm_y0, hm_x1, hm_y1 = bx + 118, by + 92, bx + pw - 110, by + ph - 92
    hm_w, hm_h = hm_x1 - hm_x0, hm_y1 - hm_y0

    pm = p2["phase_map_4d"]
    z_grid = pm["z_r_ohm_grid"]
    q_grid = pm["q_l_grid"]
    lookup = {(p["z_r_ohm"], p["q_l"], p["s_eps_uev"]): p["mean_F_bell"] for p in pm["points"]}
    nx_g, ny_g = len(z_grid), len(q_grid)
    cw, ch = hm_w / nx_g, hm_h / ny_g

    for j, ql in enumerate(q_grid):
        # y-axis: higher Q_L at top
        row_y = hm_y1 - (j + 1) * ch
        for i, zr in enumerate(z_grid):
            col_x = hm_x0 + i * cw
            val = lookup[(zr, ql, 0.5)]
            col = heatmap_color(val, vmin=0.58, vmax=0.995)
            ctx.set_source_rgb(*col)
            ctx.rectangle(col_x + 2, row_y + 2, cw - 4, ch - 4)
            ctx.fill()

            # Highlight >= 0.99 surface-code threshold cells with gold border + star
            if val >= 0.99:
                ctx.set_source_rgb(1.0, 0.85, 0.15)
                ctx.set_line_width(3.5)
                ctx.rectangle(col_x + 3.5, row_y + 3.5, cw - 7, ch - 7)
                ctx.stroke()

            txt_col = (1.0, 1.0, 1.0) if (val >= 0.93 or val < 0.72) else INK
            draw_text(ctx, f"{val:.4f}", col_x + cw / 2.0, row_y + ch / 2.0 - (6 if val >= 0.99 else 0), size=16.5, color=txt_col, bold=True, align="center", valign="middle")
            if val >= 0.99:
                draw_text(ctx, ">=99% SC", col_x + cw / 2.0, row_y + ch / 2.0 + 18, size=12.5, color=(1.0, 0.92, 0.35), bold=True, align="center", valign="middle")

        # Q_L y-tick label
        q_str = f"{ql/1e5:.1f}e5" if ql >= 1e5 else f"{ql/1e4:.0f}e4"
        draw_text(ctx, q_str, hm_x0 - 12, row_y + ch / 2.0, size=15.5, color=INK, bold=True, align="right", valign="middle")

    # Crimson box highlighting 50 Ohm failure column
    ctx.set_source_rgb(*CORAL)
    ctx.set_line_width(3.0)
    ctx.rectangle(hm_x0 + 1, hm_y0 + 1, cw - 2, hm_h - 2)
    ctx.stroke()
    draw_text(ctx, "50 Ohm Wall", hm_x0 + cw / 2.0, hm_y0 - 12, size=13.5, color=CORAL, bold=True, align="center")

    for i, zr in enumerate(z_grid):
        z_str = "50 Ohm" if zr < 500 else f"{zr/1000:.0f} kOhm"
        draw_text(ctx, z_str, hm_x0 + (i + 0.5) * cw, hm_y1 + 26, size=15.5, color=CORAL if zr < 500 else INK, bold=True, align="center")

    # Colorbar on right of Panel B
    cb_x, cb_w = hm_x1 + 24, 24
    for s in range(120):
        frac = s / 119.0
        val = 0.58 + frac * (0.995 - 0.58)
        ctx.set_source_rgb(*heatmap_color(val, 0.58, 0.995))
        yy = hm_y1 - frac * hm_h
        ctx.rectangle(cb_x, yy - hm_h / 119.0, cb_w, hm_h / 119.0 + 1)
        ctx.fill()
    ctx.set_source_rgb(*INK); ctx.set_line_width(1.2); ctx.rectangle(cb_x, hm_y0, cb_w, hm_h); ctx.stroke()
    for tick in [0.60, 0.75, 0.90, 0.99]:
        yy = hm_y1 - ((tick - 0.58) / (0.995 - 0.58)) * hm_h
        draw_text(ctx, f"{tick:.2f}", cb_x + cb_w + 8, yy, size=13.5, color=INK, bold=(tick == 0.99), valign="middle")

    draw_text(ctx, "Loaded Quality Factor Q_L", bx + 32, (hm_y0 + hm_y1) / 2.0, size=16, color=INK, bold=True, align="center", valign="middle", angle=-math.pi / 2.0)
    draw_text(ctx, "Resonator Characteristic Impedance Z_r (30 heterogeneous Exp124 pairs/cell, Delta_z_cap = 8 nm)", (hm_x0 + hm_x1) / 2.0, by + ph - 20, size=13.5, color=MUTED, align="center")

    # --- PANEL C: Charge Noise Failure Boundary S_eps & Universal CZ Overlay ---
    cx, cy = pad_x, top_y + ph + gap_y
    draw_panel_box(ctx, cx, cy, pw, ph, "Charge Noise Failure Boundary S_eps (1/f) & Full CZ Gate Comparison", "C")
    c_x0, c_y0, c_x1, c_y1 = cx + 96, cy + 84, cx + pw - 42, cy + ph - 86
    cw_p, ch_p = c_x1 - c_x0, c_y1 - c_y0
    s_grid = pm["s_eps_uev_grid"]  # [0.5, 1.0, 2.0, 5.0]
    y_min_c, y_max_c = 0.50, 1.01

    def map_cx(sv: float) -> float:
        # Log-spaced x spanning [0.22, 5.8] so Tosi 0.25 diagnostic + [0.5, 1.0, 2.0, 5.0] all fit cleanly
        lo, hi = math.log10(0.20), math.log10(6.2)
        return c_x0 + ((math.log10(sv) - lo) / (hi - lo)) * cw_p

    def map_cy(fv: float) -> float:
        return c_y1 - ((fv - y_min_c) / (y_max_c - y_min_c)) * ch_p

    for yv in [0.55, 0.65, 0.75, 0.85, 0.90, 0.95, 0.99]:
        yy = map_cy(yv)
        ctx.set_source_rgb(*GRID); ctx.set_line_width(1.1)
        ctx.move_to(c_x0, yy); ctx.line_to(c_x1, yy); ctx.stroke()
        draw_text(ctx, f"{yv:.2f}", c_x0 - 12, yy, size=14.5, color=MUTED, align="right", valign="middle")

    # Threshold dashed lines: 0.99 and 0.90 (placed in clean open regions)
    yy99 = map_cy(0.99)
    ctx.save(); ctx.set_source_rgb(*GREEN); ctx.set_dash([7, 5]); ctx.set_line_width(1.8)
    ctx.move_to(c_x0, yy99); ctx.line_to(c_x1, yy99); ctx.stroke(); ctx.restore()
    draw_text(ctx, "0.99 Surface-Code Threshold", c_x1 - 8, yy99 - 8, size=13, color=GREEN, bold=True, align="right")

    yy90 = map_cy(0.90)
    ctx.save(); ctx.set_source_rgb(*CORAL); ctx.set_dash([7, 5]); ctx.set_line_width(1.8)
    ctx.move_to(c_x0, yy90); ctx.line_to(c_x1, yy90); ctx.stroke(); ctx.restore()
    draw_text(ctx, "0.90 Minimum Gate Floor", c_x0 + 10, yy90 + 16, size=13, color=CORAL, bold=True, align="left")

    series_c = [
        (4000.0, 2e5, TEAL, "4 kOhm, Q=2e5 (Bell)", False),
        (3000.0, 2e5, BLUE, "3 kOhm, Q=2e5 (M4 Nominal Bell)", False),
        (1000.0, 2e5, PURPLE, "1 kOhm, Q=2e5 (Bell)", False),
        (3000.0, 5e4, AMBER, "3 kOhm, Q=5e4 (Low-Q Bell)", True),
        (50.0, 2e5, CORAL, "50 Ohm CPW, Q=2e5 (Fails <0.90)", False),
    ]
    for zr, ql, col, lbl, dashed in series_c:
        pts = [(map_cx(s), map_cy(lookup[(zr, ql, s)])) for s in s_grid]
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(3.0 if zr == 3000.0 and ql == 2e5 else 2.4)
        if dashed:
            ctx.set_dash([9, 5])
        ctx.move_to(*pts[0])
        for pt in pts[1:]:
            ctx.line_to(*pt)
        ctx.stroke()
        ctx.restore()
        for (px, py) in pts:
            ctx.set_source_rgb(*col)
            ctx.arc(px, py, 5.5, 0, 2 * math.pi); ctx.fill()
            ctx.set_source_rgb(1, 1, 1); ctx.arc(px, py, 2.3, 0, 2 * math.pi); ctx.fill()

    # Overlay full universal CZ average gate fidelity diamonds at S=0.25, 0.5, and 1.0
    cz_s1 = p2["universal_cz_gate"]["nominal_3kohm_Q2e5_S1"]["mean_F_avg_cz"]
    cz_s05 = p2["universal_cz_gate"]["low_noise_3kohm_Q2e5_S0p5"]["mean_F_avg_cz"]
    cz_s025 = p2["universal_cz_gate"].get("tosi_ultra_low_noise_3kohm_Q5e5_S0p25", {}).get("mean_F_avg_cz")
    cz_pts = [(0.5, cz_s05, "CZ(S=0.5)"), (1.0, cz_s1, "CZ(S=1.0)")]
    if cz_s025 is not None:
        cz_pts.insert(0, (0.25, cz_s025, "CZ(0.25,Q5e5)"))
    for sv, fcz, _tag in cz_pts:
        px, py = map_cx(sv), map_cy(fcz)
        ctx.set_source_rgb(*NAVY)
        ctx.move_to(px, py - 9); ctx.line_to(px + 9, py); ctx.line_to(px, py + 9); ctx.line_to(px - 9, py); ctx.close_path()
        ctx.fill()
        draw_text(ctx, f"CZ={fcz:.3f}", px + 12, py + 4, size=13, color=NAVY, bold=True)

    # Overlay Tosi S=0.25 diagnostic Bell star (4 kOhm, Q=5e5)
    tosi_diag = pm.get("tosi_100Vm_S0p25_diagnostic", [])
    if tosi_diag:
        best_tosi = max(tosi_diag, key=lambda d: d["mean_F_bell"])
        tx, ty = map_cx(0.25), map_cy(best_tosi["mean_F_bell"])
        ctx.set_source_rgb(*GREEN)
        ctx.arc(tx, ty, 7.0, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgb(1, 1, 1); ctx.arc(tx, ty, 3.0, 0, 2 * math.pi); ctx.fill()
        draw_text(ctx, f"4k,Q5e5: {best_tosi['mean_F_bell']:.4f}", tx + 11, ty - 6, size=12.8, color=GREEN, bold=True)

    for s in ([0.25] + s_grid):
        px = map_cx(s)
        ctx.set_source_rgb(*INK); ctx.set_line_width(1.4)
        ctx.move_to(px, c_y1); ctx.line_to(px, c_y1 + 6); ctx.stroke()
        lbl_s = "0.25" if abs(s - 0.25) < 1e-6 else f"{s:.1f}"
        draw_text(ctx, lbl_s, px, c_y1 + 24, size=14.5, color=GREEN if abs(s - 0.25) < 1e-6 else INK, bold=True, align="center")

    ctx.set_source_rgb(*INK); ctx.set_line_width(1.8)
    ctx.move_to(c_x0, c_y0); ctx.line_to(c_x0, c_y1); ctx.line_to(c_x1, c_y1); ctx.stroke()
    draw_text(ctx, "Mean 2-Cell Fidelity (Bell / CZ)", cx + 28, (c_y0 + c_y1) / 2.0, size=16, color=INK, bold=True, align="center", valign="middle", angle=-math.pi / 2.0)
    draw_text(ctx, "1/f Charge Noise Amplitude S_eps(1 Hz) [ueV / sqrt(Hz)] (log scale)", (c_x0 + c_x1) / 2.0, cy + ph - 18, size=14.5, color=MUTED, align="center")

    # Legend in Panel C bottom-left
    lx, ly = c_x0 + 14, c_y1 - 166
    round_rect(ctx, lx, ly, 315, 152, r=7)
    ctx.set_source_rgba(1, 1, 1, 0.94); ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER); ctx.set_line_width(1.2); ctx.stroke()
    for idx, (_, _, col, lbl, dashed) in enumerate(series_c):
        yy = ly + 18 + idx * 24
        ctx.save(); ctx.set_source_rgb(*col); ctx.set_line_width(2.8)
        if dashed: ctx.set_dash([6, 4])
        ctx.move_to(lx + 12, yy); ctx.line_to(lx + 40, yy); ctx.stroke(); ctx.restore()
        draw_text(ctx, lbl, lx + 48, yy + 4, size=13, color=INK)
    # Diamond entry for CZ
    yy = ly + 18 + 5 * 24
    ctx.set_source_rgb(*NAVY)
    ctx.move_to(lx + 26, yy - 6); ctx.line_to(lx + 32, yy); ctx.line_to(lx + 26, yy + 6); ctx.line_to(lx + 20, yy); ctx.close_path(); ctx.fill()
    draw_text(ctx, "Full 4-Basis CZ F_avg (3 kOhm, Q=2e5)", lx + 48, yy + 4, size=13, color=NAVY, bold=True)

    # --- PANEL D: Exact 12x12 Lindblad Bell-State Time Evolution ---
    dx, dy = pad_x + pw + gap_x, top_y + ph + gap_y
    draw_panel_box(ctx, dx, dy, pw, ph, "Exact 12x12 Lindblad Bell Evolution (3 kOhm Heterog. Pair vs 50 Ohm)", "D")
    d_x0, d_y0, d_x1, d_y1 = dx + 96, dy + 84, dx + pw - 42, dy + ph - 86
    dw_p, dh_p = d_x1 - d_x0, d_y1 - d_y0

    tr3 = p2["bell_trajectories"]["nbtin_3kohm"]
    tr50 = p2["bell_trajectories"]["cpw_50ohm"]
    t_max = tr3["t_total_us"] * 1.04

    def map_dx(tv: float) -> float:
        return d_x0 + (tv / t_max) * dw_p

    def map_dy(pv: float) -> float:
        return d_y1 - pv * dh_p

    for yv in [0.0, 0.25, 0.50, 0.75, 1.0]:
        yy = map_dy(yv)
        ctx.set_source_rgb(*GRID); ctx.set_line_width(1.1)
        ctx.move_to(d_x0, yy); ctx.line_to(d_x1, yy); ctx.stroke()
        draw_text(ctx, f"{yv:.2f}", d_x0 - 12, yy, size=14.5, color=MUTED, align="right", valign="middle")

    # Stage 1 -> Stage 2 vertical divider
    xt1 = map_dx(tr3["t1_us"])
    ctx.save(); ctx.set_source_rgb(*MUTED); ctx.set_dash([6, 5]); ctx.set_line_width(1.6)
    ctx.move_to(xt1, d_y0); ctx.line_to(xt1, d_y1); ctx.stroke(); ctx.restore()
    draw_text(ctx, "Stage 1: Q1 pi/2", (d_x0 + xt1) / 2.0, d_y0 + 18, size=13, color=MUTED, bold=True, align="center")
    draw_text(ctx, "Stage 2: Q2 pi Swap", (xt1 + d_x1) / 2.0, d_y0 + 18, size=13, color=MUTED, bold=True, align="center")

    ts = tr3["t_us"]
    curves_d = [
        (tr3["F_bell"], TEAL, 3.4, "F_Bell(t) [3 kOhm]", False),
        (tr3["P_10"], BLUE, 2.3, "P(|10>)", False),
        (tr3["P_01"], PURPLE, 2.3, "P(|01>)", False),
        (tr3["n_cav"], AMBER, 2.4, "<n_cav(t)>", True),
    ]
    for vals, col, lw, lbl, dashed in curves_d:
        ctx.save(); ctx.set_source_rgb(*col); ctx.set_line_width(lw)
        if dashed: ctx.set_dash([7, 4])
        ctx.move_to(map_dx(ts[0]), map_dy(vals[0]))
        for t_i, v_i in zip(ts[1:], vals[1:]):
            ctx.line_to(map_dx(t_i), map_dy(v_i))
        ctx.stroke(); ctx.restore()

    # Final F_Bell callout badge + 50 Ohm contrast summary box (clean open space mid-left above F_Bell)
    bx_in, by_in, bw_in, bh_in = d_x0 + 22, d_y0 + 175, 314, 122
    round_rect(ctx, bx_in, by_in, bw_in, bh_in, r=8)
    ctx.set_source_rgba(0.97, 0.99, 0.99, 0.95); ctx.fill_preserve()
    ctx.set_source_rgb(*TEAL); ctx.set_line_width(1.5); ctx.stroke()
    imp = p2["impedance_wall_comparison"]
    draw_text(ctx, f"Pair: g1={tr3['g1_mhz']:.2f}, g2={tr3['g2_mhz']:.2f} MHz", bx_in + 12, by_in + 22, size=13.2, color=INK, bold=True)
    draw_text(ctx, f"3 kOhm F_Bell: {tr3['final_F_bell']:.4f} ({tr3['t_total_us']*1e3:.0f} ns)", bx_in + 12, by_in + 44, size=13.2, color=TEAL, bold=True)
    draw_text(ctx, f"50 Ohm F_Bell: {tr50['final_F_bell']:.4f} ({tr50['t_total_us']*1e3:.0f} ns)", bx_in + 12, by_in + 66, size=13.2, color=CORAL, bold=True)
    draw_text(ctx, f"60-Pair: 3k={imp['nbtin_3kohm']['mean_F_bell']:.4f} vs 50={imp['cpw_50ohm']['mean_F_bell']:.4f}", bx_in + 12, by_in + 88, size=12.6, color=INK)
    cptp = p2["cptp_audit"]
    draw_text(ctx, f"CPTP max|Tr-1|={cptp['max_trace_err']:.1e}", bx_in + 12, by_in + 110, size=12.2, color=MUTED)

    # Legend bottom-right inside Panel D
    lx_d, ly_d = d_x0 + 14, d_y1 - 110
    round_rect(ctx, lx_d, ly_d, 190, 98, r=7)
    ctx.set_source_rgba(1, 1, 1, 0.93); ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER); ctx.set_line_width(1.2); ctx.stroke()
    for idx, (_, col, lw, lbl, dashed) in enumerate(curves_d):
        yy = ly_d + 16 + idx * 22
        ctx.save(); ctx.set_source_rgb(*col); ctx.set_line_width(lw)
        if dashed: ctx.set_dash([5, 3])
        ctx.move_to(lx_d + 10, yy); ctx.line_to(lx_d + 36, yy); ctx.stroke(); ctx.restore()
        draw_text(ctx, lbl, lx_d + 44, yy + 4, size=13, color=INK, bold=(idx == 0))

    # X ticks for Panel D
    for k in range(6):
        tv = (k / 5.0) * tr3["t_total_us"]
        px = map_dx(tv)
        ctx.set_source_rgb(*INK); ctx.set_line_width(1.4)
        ctx.move_to(px, d_y1); ctx.line_to(px, d_y1 + 6); ctx.stroke()
        draw_text(ctx, f"{tv*1e3:.0f}", px, d_y1 + 24, size=14.5, color=INK, align="center")

    ctx.set_source_rgb(*INK); ctx.set_line_width(1.8)
    ctx.move_to(d_x0, d_y0); ctx.line_to(d_x0, d_y1); ctx.line_to(d_x1, d_y1); ctx.stroke()
    draw_text(ctx, "Population / Fidelity / <n_cav>", dx + 28, (d_y0 + d_y1) / 2.0, size=16, color=INK, bold=True, align="center", valign="middle", angle=-math.pi / 2.0)
    draw_text(ctx, "Gate Time t [ns] (Q_L = 2e5, S_eps = 1.0 ueV/rtHz, T = 20 mK)", (d_x0 + d_x1) / 2.0, dy + ph - 18, size=14.5, color=MUTED, align="center")

    surf.write_to_png(str(FIG1_PATH))


def build_fig2_percolation_and_cad(data: dict[str, Any]) -> None:
    W, H = 2400, 1580
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    p3 = data["part3_percolation_and_cad"]
    yi = p3["yield_inputs"]
    cad = p3["cad_m4_bus_geometry"]

    draw_header(
        ctx, W,
        "Exp131 (H149): 2D Surface-Code vs Heavy-Hex Percolation & CAD v4.0 M4 Bus Geometry",
        f"Combined Yield p_M4 = p_spec({yi['p_spec_modB_1pct']:.2f}) x p_ff({yi['p_ff_opt']:.3f}) = {yi['p_m4_combined']:.4f} | N_mc = {yi['n_mc_per_point']:,} Lattices/Point",
        "ARCHITECTURE & LAYOUT SPEC (Model / MC)",
    )

    pad_x, top_y, gap_x, gap_y = 36, 134, 28, 28
    pw = (W - 2 * pad_x - gap_x) / 2.0
    ph = (H - top_y - 36 - gap_y) / 2.0

    # --- PANEL A: Spanning Percolation P_perc vs N_cand (Square vs Heavy-Hex) ---
    ax, ay = pad_x, top_y
    draw_panel_box(ctx, ax, ay, pw, ph, "Spanning Percolation P_perc vs Candidate Slots N_cand (Square vs Heavy-Hex)", "A")
    px0, py0, px1, py1 = ax + 96, ay + 84, ax + pw - 42, ay + ph - 86
    plot_w, plot_h = px1 - px0, py1 - py0
    nc_vals = yi["n_cand_grid"]  # [1, 2, 3, 4, 6, 8]

    def map_ax(nc: int) -> float:
        return px0 + ((nc - 0.6) / (8.4 - 0.6)) * plot_w

    def map_ay(val: float) -> float:
        return py1 - (val / 1.04) * plot_h

    for yv in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        yy = map_ay(yv)
        ctx.set_source_rgb(*GRID); ctx.set_line_width(1.1)
        ctx.move_to(px0, yy); ctx.line_to(px1, yy); ctx.stroke()
        draw_text(ctx, f"{int(yv * 100)}%", px0 - 12, yy, size=14.5, color=MUTED, align="right", valign="middle")

    # 99% target line
    y99 = map_ay(0.99)
    ctx.save(); ctx.set_source_rgb(*GREEN); ctx.set_dash([7, 5]); ctx.set_line_width(1.7)
    ctx.move_to(px0, y99); ctx.line_to(px1, y99); ctx.stroke(); ctx.restore()
    draw_text(ctx, "99% Spanning Target", px1 - 8, y99 - 8, size=13, color=GREEN, bold=True, align="right")

    # Highlight N_cand = 2 gap between Square and Heavy-Hex (text in wide-open center y~50%)
    x2 = map_ax(2)
    ctx.set_source_rgba(0.85, 0.52, 0.05, 0.12)
    ctx.rectangle(x2 - 42, py0, 84, plot_h)
    ctx.fill()
    ymid_a = map_ay(0.54)
    round_rect(ctx, x2 - 58, ymid_a - 28, 116, 56, r=6)
    ctx.set_source_rgba(1.0, 0.98, 0.92, 0.95); ctx.fill_preserve()
    ctx.set_source_rgb(*AMBER); ctx.set_line_width(1.3); ctx.stroke()
    draw_text(ctx, "N_cand=2 Gap", x2, ymid_a - 8, size=12.5, color=AMBER, bold=True, align="center")
    draw_text(ctx, "p_node = 0.74", x2, ymid_a + 12, size=12, color=INK, bold=True, align="center")

    curves_a = [
        (p3["square_m4"]["square_L5"]["sweep"], TEAL_LIGHT, False, "2D Square L=5 (25 nodes, deg=4)"),
        (p3["square_m4"]["square_L11"]["sweep"], BLUE, False, "2D Square L=11 (121 nodes, deg=4)"),
        (p3["square_m4"]["square_L21"]["sweep"], NAVY, False, "2D Square L=21 (441 nodes, deg=4)"),
        (p3["heavy_hex_m4"]["heavy_hex_d5"]["sweep"], AMBER, True, f"Heavy-Hex d=5 ({p3['heavy_hex_m4']['heavy_hex_d5']['n_nodes']} nodes, deg~2.4)"),
        (p3["heavy_hex_m4"]["heavy_hex_d7"]["sweep"], CORAL, True, f"Heavy-Hex d=7 ({p3['heavy_hex_m4']['heavy_hex_d7']['n_nodes']} nodes, deg~2.4)"),
    ]
    for sw, col, dashed, lbl in curves_a:
        pts = [(map_ax(r["N_cand"]), map_ay(r["P_perc"])) for r in sw]
        ctx.save(); ctx.set_source_rgb(*col); ctx.set_line_width(3.0 if not dashed else 2.8)
        if dashed: ctx.set_dash([9, 5])
        ctx.move_to(*pts[0])
        for pt in pts[1:]:
            ctx.line_to(*pt)
        ctx.stroke(); ctx.restore()
        for (px, py) in pts:
            ctx.set_source_rgb(*col); ctx.arc(px, py, 5.2, 0, 2 * math.pi); ctx.fill()
            ctx.set_source_rgb(1, 1, 1); ctx.arc(px, py, 2.2, 0, 2 * math.pi); ctx.fill()

    for nc in nc_vals:
        px = map_ax(nc)
        ctx.set_source_rgb(*INK); ctx.set_line_width(1.4)
        ctx.move_to(px, py1); ctx.line_to(px, py1 + 6); ctx.stroke()
        p_nd = 1.0 - (1.0 - yi["p_m4_combined"]) ** nc
        draw_text(ctx, f"{nc}", px, py1 + 24, size=15.5, color=INK, bold=True, align="center")
        draw_text(ctx, f"({p_nd*100:.0f}%)", px, py1 + 43, size=12, color=MUTED, align="center")

    ctx.set_source_rgb(*INK); ctx.set_line_width(1.8)
    ctx.move_to(px0, py0); ctx.line_to(px0, py1); ctx.line_to(px1, py1); ctx.stroke()
    draw_text(ctx, "Spanning Percolation Probability P_perc", ax + 28, (py0 + py1) / 2.0, size=16, color=INK, bold=True, align="center", valign="middle", angle=-math.pi / 2.0)
    draw_text(ctx, "Candidate Donor Slots per Logical Node N_cand (and effective node yield p_node)", (px0 + px1) / 2.0, ay + ph - 14, size=13.5, color=MUTED, align="center")

    # Legend bottom-right inside Panel A
    lx, ly = px1 - 355, py1 - 146
    round_rect(ctx, lx, ly, 344, 134, r=7)
    ctx.set_source_rgba(1, 1, 1, 0.94); ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER); ctx.set_line_width(1.2); ctx.stroke()
    for idx, (_, col, dashed, lbl) in enumerate(curves_a):
        yy = ly + 18 + idx * 24
        ctx.save(); ctx.set_source_rgb(*col); ctx.set_line_width(2.8)
        if dashed: ctx.set_dash([7, 4])
        ctx.move_to(lx + 12, yy); ctx.line_to(lx + 42, yy); ctx.stroke(); ctx.restore()
        draw_text(ctx, lbl, lx + 50, yy + 4, size=13, color=INK, bold=(idx in (2, 4)))

    # --- PANEL B: Defect-Free & Fault-Tolerant (<=5% Dead) Grid Yields vs N_cand ---
    bx, by = pad_x + pw + gap_x, top_y
    draw_panel_box(ctx, bx, by, pw, ph, "Defect-Free (0 Dead) & Fault-Tolerant (<=5% Dead) Array Yields", "B")
    bx0, by0, bx1, by1 = bx + 96, by + 84, bx + pw - 42, by + ph - 86
    bw_p, bh_p = bx1 - bx0, by1 - by0

    def map_bx(nc: int) -> float:
        return bx0 + ((nc - 0.6) / (8.4 - 0.6)) * bw_p

    def map_by(val: float) -> float:
        return by1 - (val / 1.04) * bh_p

    for yv in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        yy = map_by(yv)
        ctx.set_source_rgb(*GRID); ctx.set_line_width(1.1)
        ctx.move_to(bx0, yy); ctx.line_to(bx1, yy); ctx.stroke()
        draw_text(ctx, f"{int(yv * 100)}%", bx0 - 12, yy, size=14.5, color=MUTED, align="right", valign="middle")

    # 95% FT target & 60% Perfect target
    for thr, col, lbl in [(0.95, GREEN, "95% FT Target (L=11)"), (0.60, PURPLE, "60% Defect-Free Target (L=5)")]:
        yy = map_by(thr)
        ctx.save(); ctx.set_source_rgb(*col); ctx.set_dash([7, 5]); ctx.set_line_width(1.6)
        ctx.move_to(bx0, yy); ctx.line_to(bx1, yy); ctx.stroke(); ctx.restore()
        draw_text(ctx, lbl, bx0 + 10, yy - 7, size=13, color=col, bold=True)

    curves_b = [
        (p3["square_m4"]["square_L5"]["sweep"], "Y_perfect_mc", PURPLE, True, "Defect-Free L=5 (25/25 alive)"),
        (p3["square_m4"]["square_L11"]["sweep"], "Y_perfect_mc", CORAL, True, "Defect-Free L=11 (121/121 alive)"),
        (p3["square_m4"]["square_L5"]["sweep"], "Y_FT_5pct_mc", TEAL_LIGHT, False, "Fault-Tolerant L=5 (<=1 dead)"),
        (p3["square_m4"]["square_L11"]["sweep"], "Y_FT_5pct_mc", TEAL, False, "Fault-Tolerant L=11 (<=6 dead)"),
        (p3["square_m4"]["square_L21"]["sweep"], "Y_FT_5pct_mc", NAVY, False, "Fault-Tolerant L=21 (<=22 dead)"),
    ]
    for sw, field, col, dashed, lbl in curves_b:
        pts = [(map_bx(r["N_cand"]), map_by(r[field])) for r in sw]
        ctx.save(); ctx.set_source_rgb(*col); ctx.set_line_width(2.9)
        if dashed: ctx.set_dash([8, 5])
        ctx.move_to(*pts[0])
        for pt in pts[1:]:
            ctx.line_to(*pt)
        ctx.stroke(); ctx.restore()
        for (px, py) in pts:
            ctx.set_source_rgb(*col); ctx.arc(px, py, 5.0, 0, 2 * math.pi); ctx.fill()
            ctx.set_source_rgb(1, 1, 1); ctx.arc(px, py, 2.0, 0, 2 * math.pi); ctx.fill()

    # Exact callouts at N_cand=6 (clear of dashed lines)
    sq5_6 = next(r for r in p3["square_m4"]["square_L5"]["sweep"] if r["N_cand"] == 6)
    sq11_6 = next(r for r in p3["square_m4"]["square_L11"]["sweep"] if r["N_cand"] == 6)
    draw_text(ctx, f"L=5 Perf: {sq5_6['Y_perfect_mc']*100:.1f}%", map_bx(6) + 14, map_by(sq5_6["Y_perfect_mc"]) + 24, size=13, color=PURPLE, bold=True)
    draw_text(ctx, f"L=11 FT: {sq11_6['Y_FT_5pct_mc']*100:.1f}%", map_bx(6) - 10, map_by(sq11_6["Y_FT_5pct_mc"]) - 14, size=13, color=TEAL, bold=True, align="right")

    for nc in nc_vals:
        px = map_bx(nc)
        ctx.set_source_rgb(*INK); ctx.set_line_width(1.4)
        ctx.move_to(px, by1); ctx.line_to(px, by1 + 6); ctx.stroke()
        draw_text(ctx, f"{nc}", px, by1 + 24, size=15.5, color=INK, bold=True, align="center")

    ctx.set_source_rgb(*INK); ctx.set_line_width(1.8)
    ctx.move_to(bx0, by0); ctx.line_to(bx0, by1); ctx.line_to(bx1, by1); ctx.stroke()
    draw_text(ctx, "Array Fabrication Yield", bx + 28, (by0 + by1) / 2.0, size=16, color=INK, bold=True, align="center", valign="middle", angle=-math.pi / 2.0)
    draw_text(ctx, "Candidate Donor Slots per Logical Node N_cand (MC validated vs exact Binomial)", (bx0 + bx1) / 2.0, by + ph - 18, size=13.5, color=MUTED, align="center")

    # Legend top-left inside Panel B (below 95% dashed line)
    lx_b, ly_b = bx0 + 14, by0 + 54
    round_rect(ctx, lx_b, ly_b, 310, 134, r=7)
    ctx.set_source_rgba(1, 1, 1, 0.94); ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER); ctx.set_line_width(1.2); ctx.stroke()
    for idx, (_, _, col, dashed, lbl) in enumerate(curves_b):
        yy = ly_b + 18 + idx * 24
        ctx.save(); ctx.set_source_rgb(*col); ctx.set_line_width(2.8)
        if dashed: ctx.set_dash([7, 4])
        ctx.move_to(lx_b + 12, yy); ctx.line_to(lx_b + 42, yy); ctx.stroke(); ctx.restore()
        draw_text(ctx, lbl, lx_b + 50, yy + 4, size=13, color=INK, bold=(idx in (0, 3)))

    # --- PANEL C: Simulated 11x11 Logical Array Realizations (N_cand = 1, 2, 3, 6) ---
    cx, cy = pad_x, top_y + ph + gap_y
    draw_panel_box(ctx, cx, cy, pw, ph, "Simulated 11x11 (121-Node) Logical Array Realizations (Nested Draws)", "C")

    reals = p3["realizations_L11"]
    sub_keys = ["N_cand_1", "N_cand_2", "N_cand_3", "N_cand_6"]
    sub_gap = 26
    sub_w = (pw - 64 - 3 * sub_gap) / 4.0
    grid_size = min(sub_w - 8, ph - 210)
    cell_sz = grid_size / 11.0
    grid_top = cy + 125

    for idx, key in enumerate(sub_keys):
        rinfo = reals[key]
        sx = cx + 32 + idx * (sub_w + sub_gap) + (sub_w - grid_size) / 2.0
        sy = grid_top
        spans = rinfo["spans"]
        status_txt = "SPANS" if spans else "NO SPAN"
        status_col = GREEN if spans else CORAL

        draw_text(ctx, f"N_cand = {rinfo['N_cand']}", sx + grid_size / 2.0, sy - 42, size=17, color=INK, bold=True, align="center")
        draw_text(ctx, f"{status_txt} | Alive {rinfo['n_alive']}/121", sx + grid_size / 2.0, sy - 18, size=13.5, color=status_col, bold=True, align="center")

        # Draw 11x11 grid
        mat = rinfo["grid_11x11"]
        for r in range(11):
            for c in range(11):
                st = mat[r][c]
                col = SLATE_DEAD if st == 0 else (AMBER if st == 1 else TEAL)
                ctx.set_source_rgb(*col)
                ctx.rectangle(sx + c * cell_sz + 1.2, sy + r * cell_sz + 1.2, cell_sz - 2.4, cell_sz - 2.4)
                ctx.fill()

        ctx.set_source_rgb(*status_col); ctx.set_line_width(2.4)
        ctx.rectangle(sx - 2, sy - 2, grid_size + 4, grid_size + 4); ctx.stroke()
        draw_text(ctx, f"GC = {rinfo['gc_size']}/121 ({rinfo['gc_size']/121*100:.0f}%)", sx + grid_size / 2.0, sy + grid_size + 24, size=13.5, color=INK, bold=True, align="center")
        draw_text(ctx, f"Dead = {rinfo['n_dead']} ({rinfo['n_dead']/121*100:.1f}%)", sx + grid_size / 2.0, sy + grid_size + 44, size=13, color=MUTED, align="center")

    # Color key strip at bottom of Panel C
    ky = cy + ph - 44
    items_c = [(TEAL, "Giant Percolating Component (Routable)"), (AMBER, "Isolated Certified Node"), (SLATE_DEAD, "Dead Logical Node (0 Certified Slots)")]
    kx = cx + 48
    for col, txt in items_c:
        ctx.set_source_rgb(*col); ctx.rectangle(kx, ky - 11, 18, 18); ctx.fill()
        draw_text(ctx, txt, kx + 26, ky + 3, size=14, color=INK, bold=True)
        kx += 360

    # --- PANEL D: CAD v4.0 & BOM M4 NbTiN Bus & Node Layout Schematic ---
    dx, dy = pad_x + pw + gap_x, top_y + ph + gap_y
    draw_panel_box(ctx, dx, dy, pw, ph, "CAD v4.0 / BOM M4 On-Chip High-Impedance NbTiN Bus Schematic", "D")

    # Top-view schematic area
    sx0, sy0, sw, sh = dx + 42, dy + 72, pw - 84, 340
    round_rect(ctx, sx0, sy0, sw, sh, r=10)
    ctx.set_source_rgb(0.965, 0.978, 0.992); ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER); ctx.set_line_width(1.4); ctx.stroke()
    draw_text(ctx, "TOP VIEW: 2D Surface-Code Node Pair Linked by Compact Meandering lambda/2 NbTiN Bus", sx0 + 18, sy0 + 26, size=14.5, color=NAVY, bold=True)

    # Left Logical Node A & Right Logical Node B boxes
    nw, nh = 248, 226
    na_x, na_y = sx0 + 28, sy0 + 54
    nb_x, nb_y = sx0 + sw - 28 - nw, sy0 + 54

    for nx, ny, label, active_idx in [(na_x, na_y, "Logical Node A", 2), (nb_x, nb_y, "Logical Node B", 4)]:
        round_rect(ctx, nx, ny, nw, nh, r=10)
        ctx.set_source_rgb(1.0, 1.0, 1.0); ctx.fill_preserve()
        ctx.set_source_rgb(*NAVY); ctx.set_line_width(2.2); ctx.stroke()
        draw_text(ctx, label, nx + nw / 2.0, ny + 24, size=15.5, color=NAVY, bold=True, align="center")
        draw_text(ctx, "N_cand = 6 slots (p_cand = 200 nm)", nx + nw / 2.0, ny + 44, size=12.0, color=MUTED, align="center")

        # Shared NbTiN voltage-antinode coupler bar
        ctx.set_source_rgb(*BLUE)
        ctx.rectangle(nx + 18, ny + 62, nw - 36, 20); ctx.fill()
        draw_text(ctx, "NbTiN Antinode Pad (cos>0.999)", nx + nw / 2.0, ny + 72, size=10.5, color=(1, 1, 1), bold=True, align="center", valign="middle")

        # 6 Candidate donor pockets + individual DC tuning fingers
        for k in range(6):
            kx = nx + 36 + k * 35
            ky = ny + 126
            is_act = (k == active_idx)
            # DC gate finger line down to bottom
            ctx.set_source_rgb(*(TEAL if is_act else SLATE_DEAD))
            ctx.set_line_width(3.0 if is_act else 1.8)
            ctx.move_to(kx, ky + 14); ctx.line_to(kx, ny + nh - 28); ctx.stroke()
            # Donor pocket circle
            ctx.set_source_rgb(*(TEAL if is_act else (0.72, 0.77, 0.82)))
            ctx.arc(kx, ky, 11 if is_act else 8, 0, 2 * math.pi); ctx.fill()
            if is_act:
                ctx.set_source_rgb(1, 1, 1); ctx.arc(kx, ky, 4.5, 0, 2 * math.pi); ctx.fill()
        draw_text(ctx, "1 Active (eps*) | 5 Parked (+25 GHz)", nx + nw / 2.0, ny + nh - 12, size=11.2, color=TEAL, bold=True, align="center")

    # Meandering NbTiN lambda/2 nanowire between Node A & Node B coupler pads
    mx0, mx1 = na_x + nw, nb_x
    my_pad = na_y + 72
    my_center = na_y + 106
    ctx.set_source_rgb(*BLUE)
    ctx.set_line_width(3.2)
    ctx.move_to(mx0, my_pad)
    n_turns = 11
    step_x = (mx1 - mx0 - 24) / n_turns
    x_cur = mx0 + 12
    ctx.line_to(x_cur, my_pad)
    amp = 48
    for t in range(n_turns):
        y_hi = my_center - amp if t % 2 == 0 else my_center + amp
        ctx.line_to(x_cur, y_hi)
        x_cur += step_x
        ctx.line_to(x_cur, y_hi)
    ctx.line_to(x_cur, my_pad)
    ctx.line_to(mx1, my_pad)
    ctx.stroke()

    # Label under meander
    draw_text(ctx, f"NbTiN Meander: w={cad['nanowire_width_nm']:.0f} nm, L_sq={cad['L_sq_pH_per_sq']:.0f} pH/sq", (mx0 + mx1) / 2.0, na_y + 186, size=13.5, color=BLUE, bold=True, align="center")
    draw_text(ctx, f"Z_r={cad['Z_r_ohm']/1000:.0f} kOhm | L_res={cad['L_res_um']:.0f} um ({cad['L_res_mm']:.2f} mm)", (mx0 + mx1) / 2.0, na_y + 206, size=13.5, color=INK, bold=True, align="center")
    draw_text(ctx, f"f_r={cad['f_r_ghz']:.1f} GHz | v_ph={cad['v_ph_over_c']*100:.2f}% c | B_M4={cad['B_M4_T']:.4f} T", (mx0 + mx1) / 2.0, na_y + 226, size=13, color=TEAL, bold=True, align="center")

    # Pitch dimension arrow between Node A and Node B
    arr_y = sy0 + sh - 22
    ctx.set_source_rgb(*INK); ctx.set_line_width(1.8)
    ctx.move_to(na_x + nw / 2.0, arr_y); ctx.line_to(nb_x + nw / 2.0, arr_y); ctx.stroke()
    draw_text(ctx, f"<--- Inter-Node Logical Pitch P_node = {cad['inter_node_pitch_um']:.0f} um (<= 20 um target) --->", (na_x + nb_x + nw) / 2.0, arr_y - 8, size=13.5, color=INK, bold=True, align="center")

    # Bottom Cross-Section & Spec Summary Strip inside Panel D
    cs_x, cs_y, cs_w, cs_h = sx0, sy0 + sh + 18, sw * 0.50 - 10, ph - (sy0 - dy) - sh - 40
    round_rect(ctx, cs_x, cs_y, cs_w, cs_h, r=8)
    ctx.set_source_rgb(1.0, 1.0, 1.0); ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER); ctx.set_line_width(1.4); ctx.stroke()
    draw_text(ctx, "VERTICAL STACK (Capping Cross-Section)", cs_x + 14, cs_y + 24, size=13.5, color=NAVY, bold=True)

    # Layered stack rectangles
    ly_top = cs_y + 38
    layers = [
        (26, (0.20, 0.45, 0.78), "NbTiN Bus (9 nm) + Top DC Gates", (1, 1, 1)),
        (24, (0.85, 0.89, 0.94), "Gate Oxide SiO2 (5-7 nm)", INK),
        (34, (0.14, 0.64, 0.58), f"Epi 28Si Cap Delta_z_cap* = {cad['delta_z_cap_opt_nm']:.0f} +/- 1 nm", (1, 1, 1)),
        (46, (0.88, 0.94, 0.98), "5 keV 31P Donor Layer (z = 14.5 +/- 2.9 nm)", INK),
        (36, (0.76, 0.82, 0.88), "Isotopic 28Si/29Si (f=1% Mod B) Substrate", INK),
    ]
    for lh, lcol, ltxt, tcol in layers:
        ctx.set_source_rgb(*lcol)
        ctx.rectangle(cs_x + 14, ly_top, cs_w - 28, lh)
        ctx.fill()
        draw_text(ctx, ltxt, cs_x + cs_w / 2.0, ly_top + lh / 2.0, size=12.5, color=tcol, bold=True, align="center", valign="middle")
        ly_top += lh + 2

    # Right summary spec card inside Panel D
    sp_x, sp_y, sp_w, sp_h = cs_x + cs_w + 18, cs_y, sw - cs_w - 18, cs_h
    round_rect(ctx, sp_x, sp_y, sp_w, sp_h, r=8)
    ctx.set_source_rgb(0.96, 0.985, 0.98); ctx.fill_preserve()
    ctx.set_source_rgb(*TEAL); ctx.set_line_width(1.6); ctx.stroke()
    draw_text(ctx, "CAD v4.0 / BOM M4 KEY PARAMETERS", sp_x + 16, sp_y + 24, size=13.5, color=TEAL, bold=True)

    spec_lines = [
        f"B_M4 Field: {cad['B_M4_T']:.4f} T ({cad['B_margin_below_Exp109_pct']:.1f}% < Exp109 0.30 T)",
        f"Inductance / Cap: {cad['L_l_nH_per_um']:.2f} nH/um | {cad['C_l_pF_per_m']:.1f} pF/m",
        f"L_sq Sens. (50/100/150 pH): 0.60 / 0.30 / 0.20 mm",
        f"Slot Isolation: {cad['intra_node_slot_pitch_nm']:.0f} nm ({cad['lateral_straggle_isolation_sigma']:.1f} sigma_xy)",
        f"DC Gates / Node: {cad['dc_gates_per_node_Ncand3']} (N=3) | {cad['dc_gates_per_node_Ncand6']} (N=6 FT)",
        f"L=11 (121-node) Gates: {cad['total_dc_gates_L11_Ncand6']} (SKY130 4K MUX)",
        "Topology Verdict: 2D Square beats Heavy-Hex (3 vs 5 slots)",
    ]
    for i, line in enumerate(spec_lines):
        draw_text(ctx, "- " + line, sp_x + 14, sp_y + 52 + i * 24, size=12.8, color=INK, bold=(i in (0, 6)))

    surf.write_to_png(str(FIG2_PATH))


def main() -> None:
    data = json.loads(EXP131_JSON.read_text(encoding="utf-8"))
    build_fig1_bus_fidelity(data)
    build_fig2_percolation_and_cad(data)
    print(f"[fig_exp131] Wrote {FIG1_PATH.name} and {FIG2_PATH.name}")


if __name__ == "__main__":
    main()
