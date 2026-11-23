"""
Exp138 (H156) — Publication-Grade 2400x1400 4-Panel Figure Generator (PyCairo).

Run with system Python (has pycairo):
  /usr/bin/python3 -B experiments/exp138_defective_surface_code_ft/fig_exp138.py

Reads:  results/exp138_defective_surface_code_ft/exp138.json
Writes: results/exp138_defective_surface_code_ft/fig_exp138_surface_code_ft.png
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cairo


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "exp138_defective_surface_code_ft"
JSON_PATH = RESULTS_DIR / "exp138.json"
OUT_PNG = RESULTS_DIR / "fig_exp138_surface_code_ft.png"

W, H = 2400, 1400


# Color palette (clean high-contrast academic light theme)
BG = (0.985, 0.988, 0.992)
CARD = (1.0, 1.0, 1.0)
BORDER = (0.82, 0.85, 0.89)
GRID = (0.90, 0.92, 0.95)
DARK = (0.10, 0.14, 0.21)
MUTED = (0.36, 0.42, 0.50)
HEADER_BG = (0.09, 0.13, 0.21)

C_RED = (0.84, 0.19, 0.19)
C_ORANGE = (0.90, 0.46, 0.10)
C_AMBER = (0.82, 0.62, 0.06)
C_TEAL = (0.06, 0.58, 0.54)
C_BLUE = (0.14, 0.40, 0.82)
C_NAVY = (0.12, 0.24, 0.54)
C_GREEN = (0.09, 0.60, 0.30)
C_PURPLE = (0.49, 0.25, 0.72)


def _set_font(ctx: cairo.Context, size: float, bold: bool = False) -> None:
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)


def _draw_text(
    ctx: cairo.Context,
    x: float,
    y: float,
    text: str,
    size: float = 14.0,
    color: Tuple[float, float, float] = DARK,
    bold: bool = False,
    align: str = "left",
) -> None:
    _set_font(ctx, size, bold)
    ctx.set_source_rgb(*color)
    ext = ctx.text_extents(text)
    if align == "center":
        x -= ext.width / 2.0 + ext.x_bearing
    elif align == "right":
        x -= ext.width + ext.x_bearing
    ctx.move_to(x, y)
    ctx.show_text(text)


def _draw_rotated_text(
    ctx: cairo.Context,
    x: float,
    y: float,
    text: str,
    size: float = 15.0,
    color: Tuple[float, float, float] = DARK,
    bold: bool = True,
) -> None:
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(-math.pi / 2.0)
    _draw_text(ctx, 0.0, 0.0, text, size=size, color=color, bold=bold, align="center")
    ctx.restore()


def _round_rect(
    ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 10.0
) -> None:
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def _draw_panel_card(
    ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, subtitle: str
) -> None:
    _round_rect(ctx, x, y, w, h, 10.0)
    ctx.set_source_rgb(*CARD)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.6)
    ctx.stroke()
    _draw_text(ctx, x + 20, y + 30, title, size=18.5, color=DARK, bold=True)
    _draw_text(ctx, x + 20, y + 51, subtitle, size=12.8, color=MUTED, bold=False)


def _draw_marker(
    ctx: cairo.Context, x: float, y: float, shape: str, color: Tuple[float, float, float], r: float = 5.5
) -> None:
    ctx.set_source_rgb(*color)
    if shape == "o":
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.fill()
    elif shape == "s":
        ctx.rectangle(x - r, y - r, 2 * r, 2 * r)
        ctx.fill()
    elif shape == "^":
        ctx.move_to(x, y - r * 1.2)
        ctx.line_to(x + r * 1.1, y + r * 0.9)
        ctx.line_to(x - r * 1.1, y + r * 0.9)
        ctx.close_path()
        ctx.fill()
    elif shape == "D":
        ctx.move_to(x, y - r * 1.2)
        ctx.line_to(x + r * 1.1, y)
        ctx.line_to(x, y + r * 1.2)
        ctx.line_to(x - r * 1.1, y)
        ctx.close_path()
        ctx.fill()
    # Crisp white outline
    ctx.set_source_rgb(1, 1, 1)
    ctx.set_line_width(1.1)
    if shape == "o":
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.stroke()


def _log_y_map(val: float, y_min_exp: float, y_max_exp: float, py0: float, py1: float) -> float:
    lv = math.log10(max(val, 10 ** y_min_exp))
    lv = min(max(lv, y_min_exp), y_max_exp)
    frac = (lv - y_min_exp) / (y_max_exp - y_min_exp)
    return py1 - frac * (py1 - py0)


def draw_panel_a(ctx: cairo.Context, data: Dict[str, Any]) -> None:
    """Panel A: Circuit-Level Threshold Crossing eps_L_round vs p_2q."""
    cx, cy, cw, ch = 36, 108, 1146, 618
    p1 = data["part1_algebra_and_threshold"]
    p_th = p1["threshold_combined_per_round"]["p_2q_th"]
    p_th_str = f"{p_th * 100:.2f}%" if p_th is not None else "N/A"
    _draw_panel_card(
        ctx, cx, cy, cw, ch,
        "A. Circuit-Level Threshold Crossing (Exact Exp137 P4 Pauli-16 + Exp140 RO)",
        f"Combined X+Z per-round logical error vs 2Q infidelity p_2q | Measured p_2q,th = {p_th_str} (p_meas=0.386%, p_1q=0.083%)"
    )

    px0, px1 = cx + 92, cx + cw - 34
    py0, py1 = cy + 78, cy + ch - 68
    xmin, xmax = 0.003, 0.0255
    ymin_e, ymax_e = -3.8, -0.7  # ~1.6e-4 to 0.20

    def mx(v: float) -> float:
        return px0 + (v - xmin) / (xmax - xmin) * (px1 - px0)

    def my(v: float) -> float:
        return _log_y_map(v, ymin_e, ymax_e, py0, py1)

    # Shaded sub-threshold FT region
    if p_th is not None:
        x_th = mx(p_th)
        ctx.set_source_rgba(0.09, 0.60, 0.30, 0.075)
        ctx.rectangle(px0, py0, max(0.0, x_th - px0), py1 - py0)
        ctx.fill()
        ctx.set_source_rgba(0.84, 0.19, 0.19, 0.05)
        ctx.rectangle(x_th, py0, max(0.0, px1 - x_th), py1 - py0)
        ctx.fill()

    # Grid lines
    ctx.set_line_width(1.0)
    for exp_v in (-3.5, -3.0, -2.5, -2.0, -1.5, -1.0):
        yy = my(10 ** exp_v)
        ctx.set_source_rgb(*GRID)
        ctx.move_to(px0, yy)
        ctx.line_to(px1, yy)
        ctx.stroke()
        if abs(exp_v - round(exp_v)) < 1e-6:
            lbl = f"10^{int(round(exp_v))}"
        else:
            lbl = f"{10**exp_v:.1e}".replace("e-0", "e-")
        _draw_text(ctx, px0 - 10, yy + 4, lbl, size=11.5, color=MUTED, align="right")

    for xv in (0.004, 0.008, 0.012, 0.016, 0.020, 0.024):
        xx = mx(xv)
        ctx.set_source_rgb(*GRID)
        ctx.move_to(xx, py0)
        ctx.line_to(xx, py1)
        ctx.stroke()
        _draw_text(ctx, xx, py1 + 22, f"{xv*100:.1f}%", size=12.0, color=MUTED, align="center")

    # Axes border
    ctx.set_source_rgb(*DARK)
    ctx.set_line_width(1.6)
    ctx.rectangle(px0, py0, px1 - px0, py1 - py0)
    ctx.stroke()

    # Threshold vertical dashed line
    if p_th is not None:
        x_th = mx(p_th)
        ctx.save()
        ctx.set_dash([7.0, 5.0])
        ctx.set_source_rgb(*C_GREEN)
        ctx.set_line_width(2.2)
        ctx.move_to(x_th, py0)
        ctx.line_to(x_th, py1)
        ctx.stroke()
        ctx.restore()
        _draw_text(ctx, x_th - 8, py0 + 18, f"p_2q,th = {p_th*100:.2f}%", size=12.5, color=C_GREEN, bold=True, align="right")
        _draw_text(ctx, x_th - 8, py0 + 35, "Sub-threshold (Lambda > 1)", size=11.0, color=C_GREEN, align="right")

    # Operating-point vertical callouts from Part 2
    p2 = data["part2_scenarios"]
    markers = [
        ("D3", p2["D3_Target_FT_P4_p0p005"]["p_2q"], C_GREEN, py1 - 12, "left"),
        ("D2", p2["D2_v5_RotaC_P4_S0p25_fast_Q5e5"]["p_2q"], C_BLUE, py1 - 30, "right"),
        ("D1", p2["D1_v5_RotaC_P4_S0p39_fast_Q5e5"]["p_2q"], C_TEAL, py1 - 12, "left"),
        ("C2", p2["C2_v5_RotaC_P4_S0p39_fast_Q2e5"]["p_2q"], C_AMBER, py1 - 30, "left"),
        ("C1", p2["C1_v5_RotaC_P4_S0p50_6pair_Q2e5"]["p_2q"], C_ORANGE, py1 - 12, "right"),
    ]
    for lbl, pv, col, ly, al in markers:
        if xmin <= pv <= xmax:
            xx = mx(pv)
            ctx.save()
            ctx.set_dash([3.0, 3.0])
            ctx.set_source_rgba(col[0], col[1], col[2], 0.55)
            ctx.set_line_width(1.3)
            ctx.move_to(xx, py0 + 44)
            ctx.line_to(xx, py1)
            ctx.stroke()
            ctx.restore()
            off = 4 if al == "left" else -4
            _draw_text(ctx, xx + off, ly, f"{lbl} ({pv*100:.2f}%)", size=10.8, color=col, bold=True, align=al)

    # Plot distance curves d=3,5,7,9 with Wilson 95% CI bars
    d_styles = [
        (3, C_RED, "o", "d = 3 (17 qubits)"),
        (5, C_ORANGE, "s", "d = 5 (49 qubits)"),
        (7, C_BLUE, "^", "d = 7 (97 qubits)"),
        (9, C_NAVY, "D", "d = 9 (161 qubits)"),
    ]
    pts = p1["points"]
    for d, col, shp, _ in d_styles:
        coords = []
        for pt in pts:
            pv = pt["p_2q"]
            comb = pt["by_d"][f"d{d}"]["combined"]
            ev = max(comb["eps_L_round"], 10 ** ymin_e)
            lo = max(comb["ci95_round"][0], 10 ** ymin_e)
            hi = max(comb["ci95_round"][1], 10 ** ymin_e)
            xx = mx(pv)
            yy = my(ev)
            coords.append((xx, yy, my(lo), my(hi)))
        # Line
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.4)
        for i, (xx, yy, _, _) in enumerate(coords):
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        # Error bars + markers
        for xx, yy, ylo, yhi in coords:
            ctx.set_source_rgba(col[0], col[1], col[2], 0.55)
            ctx.set_line_width(1.3)
            ctx.move_to(xx, ylo)
            ctx.line_to(xx, yhi)
            ctx.stroke()
            _draw_marker(ctx, xx, yy, shp, col, r=5.2)

    # Legend box (top-left inside plot, clean white bg)
    lx, ly, lw, lh = px0 + 12, py0 + 10, 198, 108
    _round_rect(ctx, lx, ly, lw, lh, 6.0)
    ctx.set_source_rgba(1, 1, 1, 0.93)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.2)
    ctx.stroke()
    for idx, (_, col, shp, lbl) in enumerate(d_styles):
        ry = ly + 22 + idx * 23
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.4)
        ctx.move_to(lx + 12, ry)
        ctx.line_to(lx + 38, ry)
        ctx.stroke()
        _draw_marker(ctx, lx + 25, ry, shp, col, r=4.8)
        _draw_text(ctx, lx + 48, ry + 4.5, lbl, size=12.0, color=DARK, bold=True)

    # Above-threshold callout note on far right
    _draw_text(
        ctx, px1 - 8, py0 + 18,
        "A (39.3%), B1 (6.65%), B2 (2.79%) ->",
        size=11.0, color=C_RED, bold=True, align="right"
    )
    _draw_text(
        ctx, px1 - 8, py0 + 34,
        "strictly above threshold (Lambda < 1)",
        size=10.5, color=C_RED, align="right"
    )

    _draw_text(ctx, (px0 + px1) / 2.0, py1 + 48, "Two-Qubit Bus CZ Infidelity p_2q = 1 - F_ent (Exp137 P4 Pauli-16 Profile)", size=13.5, color=DARK, bold=True, align="center")
    _draw_rotated_text(ctx, cx + 24, (py0 + py1) / 2.0, "Per-Round Logical Error Rate  eps_L,round", size=13.5, color=DARK, bold=True)


def draw_panel_b(ctx: cairo.Context, data: Dict[str, Any]) -> None:
    """Panel B: Waterfall eps_L_round(d) for d=3..11 across Scenarios A, B, C, D, D_target."""
    cx, cy, cw, ch = 1218, 108, 1146, 618
    _draw_panel_card(
        ctx, cx, cy, cw, ch,
        "B. Fault-Tolerant Error Suppression Waterfall: v4.0 Bare -> v5.0 Rota C -> Deep-FT",
        "Exact Blossom MWPM combined (X+Z) per-round logical error eps_L,round(d) with weighted fit eps = A * Lambda^(-(d+1)/2)"
    )

    px0, px1 = cx + 92, cx + cw - 332  # leave right margin for crisp non-overlapping legend
    py0, py1 = cy + 78, cy + ch - 68
    ymin_e, ymax_e = -4.5, -0.02  # ~3e-5 to 0.95 (keeps 0.75 saturated red curve cleanly inside!)
    ds_all = [3, 5, 7, 9, 11]

    def mx(d: int) -> float:
        return px0 + (d - 2.3) / (11.7 - 2.3) * (px1 - px0)

    def my(v: float) -> float:
        return _log_y_map(v, ymin_e, ymax_e, py0, py1)

    # Grid lines
    for exp_v in (-4, -3, -2, -1):
        yy = my(10 ** exp_v)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px1, yy)
        ctx.stroke()
        _draw_text(ctx, px0 - 10, yy + 4, f"10^{exp_v}", size=12.0, color=MUTED, align="right")

    for d in ds_all:
        xx = mx(d)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(xx, py0)
        ctx.line_to(xx, py1)
        ctx.stroke()
        _draw_text(ctx, xx, py1 + 22, f"d={d}", size=12.5, color=DARK, bold=True, align="center")
        _draw_text(ctx, xx, py1 + 38, f"({2*d*d-1}q)", size=10.5, color=MUTED, align="center")

    ctx.set_source_rgb(*DARK)
    ctx.set_line_width(1.6)
    ctx.rectangle(px0, py0, px1 - px0, py1 - py0)
    ctx.stroke()

    p2 = data["part2_scenarios"]
    series = [
        ("A_v4_Bare_P1_S1p0_Q2e5", f"A: v4.0 Bare P1 ({p2['A_v4_Bare_P1_S1p0_Q2e5']['p_2q']*100:.1f}%)", C_RED, "o", False),
        ("B2_v5_Unpass_P4_S1p0_fast_Q2e5", f"B2: Unpass P4 S=1.0 ({p2['B2_v5_Unpass_P4_S1p0_fast_Q2e5']['p_2q']*100:.2f}%)", C_ORANGE, "s", False),
        ("C2_v5_RotaC_P4_S0p39_fast_Q2e5", f"C2: RotaC Q=2e5 S=0.39 ({p2['C2_v5_RotaC_P4_S0p39_fast_Q2e5']['p_2q']*100:.2f}%)", C_AMBER, "^", True),
        ("D1_v5_RotaC_P4_S0p39_fast_Q5e5", f"D1: RotaC Q=5e5 S=0.39 ({p2['D1_v5_RotaC_P4_S0p39_fast_Q5e5']['p_2q']*100:.2f}%)", C_TEAL, "D", True),
        ("D2_v5_RotaC_P4_S0p25_fast_Q5e5", f"D2: RotaC Q=5e5 S=0.25 ({p2['D2_v5_RotaC_P4_S0p25_fast_Q5e5']['p_2q']*100:.2f}%)", C_BLUE, "o", True),
        ("D3_Target_FT_P4_p0p005", f"D3: Target Deep-FT ({p2['D3_Target_FT_P4_p0p005']['p_2q']*100:.2f}%)", C_GREEN, "s", True),
    ]

    # Right legend panel (zero overlap with curves!)
    lx, ly, lw, lh = px1 + 16, py0, 302, py1 - py0
    _round_rect(ctx, lx, ly, lw, lh, 8.0)
    ctx.set_source_rgb(0.975, 0.980, 0.990)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.2)
    ctx.stroke()
    _draw_text(ctx, lx + 14, ly + 24, "Scenarios & Fitted Lambda", size=13.5, color=DARK, bold=True)

    for idx, (sc_key, title_short, col, shp, draw_fit) in enumerate(series):
        sc = p2[sc_key]
        fit = sc["fit_per_round"]
        lam = fit["Lambda"]
        A = fit["A"]
        pts_d = sorted(int(k[1:]) for k in sc["by_d"].keys())
        coords = []
        for d in pts_d:
            comb = sc["by_d"][f"d{d}"]["combined"]
            ev = comb["eps_L_round"]
            # Display zero-failure high-d points at Jeffreys upper mark with hollow marker
            ev_plot = max(ev, 10 ** (ymin_e + 0.08))
            lo = max(comb["ci95_round"][0], 10 ** ymin_e)
            hi = max(comb["ci95_round"][1], 10 ** ymin_e)
            coords.append((mx(d), my(ev_plot), my(lo), my(hi), ev == 0.0))

        # Fitted dashed exponential line
        if draw_fit and lam > 1.0:
            ctx.save()
            ctx.set_dash([5.0, 4.0])
            ctx.set_source_rgba(col[0], col[1], col[2], 0.55)
            ctx.set_line_width(1.6)
            for j, d in enumerate(ds_all):
                pred = A * (lam ** (-(d + 1.0) / 2.0))
                if j == 0:
                    ctx.move_to(mx(d), my(pred))
                else:
                    ctx.line_to(mx(d), my(pred))
            ctx.stroke()
            ctx.restore()

        # Solid empirical line
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.5)
        for j, (xx, yy, _, _, _) in enumerate(coords):
            if j == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()

        for xx, yy, ylo, yhi, _ in coords:
            ctx.set_source_rgba(col[0], col[1], col[2], 0.50)
            ctx.set_line_width(1.3)
            ctx.move_to(xx, ylo)
            ctx.line_to(xx, yhi)
            ctx.stroke()
            _draw_marker(ctx, xx, yy, shp, col, r=5.4)

        # Legend entry
        ry = ly + 56 + idx * 66
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.8)
        ctx.move_to(lx + 14, ry)
        ctx.line_to(lx + 42, ry)
        ctx.stroke()
        _draw_marker(ctx, lx + 28, ry, shp, col, r=5.0)
        _draw_text(ctx, lx + 50, ry + 4, title_short, size=11.6, color=DARK, bold=True)
        status = "FT (Lambda > 1)" if lam > 1.0 else "ABOVE TH"
        st_col = C_GREEN if lam >= 1.4 else (C_AMBER if lam > 1.0 else C_RED)
        _draw_text(
            ctx, lx + 50, ry + 22,
            f"Lambda = {lam:.2f}  [{status}]",
            size=11.2, color=st_col, bold=True
        )

    # Sensitivity note at bottom of legend box
    d2_lru = p2["D2_LRU_sensitivity_Q5e5_S0p25"]["fit_per_round"]["Lambda"]
    d2_ro3 = p2["D2_RO3us_sensitivity_Q5e5_S0p25"]["fit_per_round"]["Lambda"]
    _draw_text(ctx, lx + 14, ly + lh - 40, "D2 Sensitivity Checks:", size=11.2, color=DARK, bold=True)
    _draw_text(ctx, lx + 14, ly + lh - 23, f"+LRU leak penalty: Lambda = {d2_lru:.2f}", size=10.8, color=MUTED)
    _draw_text(ctx, lx + 14, ly + lh - 8, f"Exp140 3us opt RO: Lambda = {d2_ro3:.2f}", size=10.8, color=C_BLUE)

    _draw_text(ctx, (px0 + px1) / 2.0, py1 + 56, "Rotated Surface Code Distance d (Active Qubits = 2d^2 - 1)", size=13.0, color=DARK, bold=True, align="center")
    _draw_rotated_text(ctx, cx + 24, (py0 + py1) / 2.0, "Per-Round Logical Error Rate  eps_L,round", size=13.5, color=DARK, bold=True)


def draw_panel_c(ctx: cairo.Context, data: Dict[str, Any]) -> None:
    """Panel C: Missing-Cell Super-Stabilizer Degradation + Real d=7 Defective Patch Diagram."""
    cx, cy, cw, ch = 36, 750, 1146, 616
    p3 = data["part3_defective_superstabilizers"]
    _draw_panel_card(
        ctx, cx, cy, cw, ch,
        "C. Missing-Cell Super-Stabilizer Gauge Deformation & BOED FNR Impact",
        "Combined Exp136 x Exp139 x Exp132 dropout p_drop(N_cand) on d=7 | 100% H_X_def H_Z_def^T = 0 (mod 2) verified"
    )

    # Left sub-chart: Grouped bar chart of mean d_eff / d vs N_cand = 1, 3, 6, 8
    bx0, bx1 = cx + 82, cx + 688
    by0, by1 = cy + 88, cy + ch - 84
    y_max_bar = 1.13  # clean headroom above 100%

    def my_bar(yv: float) -> float:
        return by1 - (yv / y_max_bar) * (by1 - by0)

    for yv in (0.0, 0.25, 0.50, 0.75, 1.0):
        yy = my_bar(yv)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(bx0, yy)
        ctx.line_to(bx1, yy)
        ctx.stroke()
        _draw_text(ctx, bx0 - 10, yy + 4, f"{yv*100:.0f}%", size=11.5, color=MUTED, align="right")

    # 85% FT preservation dashed reference line
    y85 = my_bar(0.85)
    ctx.save()
    ctx.set_dash([6.0, 4.0])
    ctx.set_source_rgb(*C_GREEN)
    ctx.set_line_width(1.8)
    ctx.move_to(bx0, y85)
    ctx.line_to(bx1, y85)
    ctx.stroke()
    ctx.restore()
    _draw_text(ctx, bx0 + 8, y85 - 7, "85% pre-reg retention target", size=10.8, color=C_GREEN, bold=True)

    ctx.set_source_rgb(*DARK)
    ctx.set_line_width(1.5)
    ctx.rectangle(bx0, by0, bx1 - bx0, by1 - by0)
    ctx.stroke()

    ncands = [1, 3, 6, 8]
    r_f1 = p3["regimes"]["f1p0_Ez0"]["by_N_cand"]
    r_f15 = p3["regimes"]["f1p5_Stark2MVm"]["by_N_cand"]
    group_w = (bx1 - bx0) / len(ncands)
    bar_w = group_w * 0.35

    def _fmt_pdrop(p: float) -> str:
        if p < 0.002:
            return f"({p*100:.3f}%)"
        if p < 0.05:
            return f"({p*100:.2f}%)"
        return f"({p*100:.1f}%)"

    for idx, nc in enumerate(ncands):
        gx = bx0 + (idx + 0.5) * group_w
        v1 = r_f1[f"N{nc}"]["by_d"]["d7"]["mean_d_eff_over_d"]
        p1_drop = r_f1[f"N{nc}"]["p_drop_with_boed"]
        v15 = r_f15[f"N{nc}"]["by_d"]["d7"]["mean_d_eff_over_d"]
        p15_drop = r_f15[f"N{nc}"]["p_drop_with_boed"]

        for bar_x, val, pdp, col in (
            (gx - bar_w - 4, v1, p1_drop, C_BLUE),
            (gx + 4, v15, p15_drop, C_TEAL),
        ):
            y_top = my_bar(val)
            h_bar = by1 - y_top
            ctx.set_source_rgb(*col)
            ctx.rectangle(bar_x, y_top, bar_w, h_bar)
            ctx.fill()
            xc = bar_x + bar_w / 2.0
            if val >= 0.70:
                # Crisp white bold inside top of bar -> zero collision with 85% line or top border!
                _draw_text(ctx, xc, y_top + 18, f"{val*100:.1f}%", size=11.0, color=(1, 1, 1), bold=True, align="center")
                _draw_text(ctx, xc, y_top + 32, _fmt_pdrop(pdp), size=9.4, color=(0.92, 0.96, 1.0), align="center")
            else:
                _draw_text(ctx, xc, y_top - 18, f"{val*100:.1f}%", size=11.0, color=col, bold=True, align="center")
                _draw_text(ctx, xc, y_top - 5, _fmt_pdrop(pdp), size=9.4, color=MUTED, align="center")

        _draw_text(ctx, gx, by1 + 21, f"N_cand = {nc}", size=12.2, color=DARK, bold=True, align="center")

    # Legend + BOED FNR callout under x-axis
    ctx.set_source_rgb(*C_BLUE)
    ctx.rectangle(bx0, by1 + 36, 16, 12)
    ctx.fill()
    _draw_text(ctx, bx0 + 22, by1 + 47, "f=1.0% (P_yield=52.8%, p_slot=51.4%)", size=11.0, color=DARK, bold=True)

    ctx.set_source_rgb(*C_TEAL)
    ctx.rectangle(bx0 + 300, by1 + 36, 16, 12)
    ctx.fill()
    _draw_text(ctx, bx0 + 322, by1 + 47, "f*=1.5%+2MV/m (P_yield=77.5%, p_slot=75.6%)", size=11.0, color=DARK, bold=True)

    boed_d = p3["regimes"]["f1p0_Ez0"]["boed_fnr_audit_N6_d7"]
    _draw_text(
        ctx, bx0, by1 + 68,
        f"Exp132 BOED FNR=0.201% impact @ N_cand=6: Delta p_drop = +{boed_d['delta_p_drop']*100:.3f}% (negligible) | (p_drop shown in parens)",
        size=10.8, color=MUTED
    )
    _draw_rotated_text(ctx, cx + 24, (by0 + by1) / 2.0, "Effective Distance Ratio  d_eff / d  (d=7)", size=13.0, color=DARK, bold=True)

    # Right sub-area: Authentic data-driven d=7 defective rotated surface code super-stabilizer diagram
    sx0, sy0, sw, sh = cx + 726, cy + 84, 396, 494
    _round_rect(ctx, sx0, sy0, sw, sh, 8.0)
    ctx.set_source_rgb(0.975, 0.980, 0.988)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.2)
    ctx.stroke()

    patch = p3.get("representative_d7_patch")
    d_vis = 7
    grid_pad = 42
    grid_size = 312
    gx0 = sx0 + (sw - grid_size) / 2.0
    gy0 = sy0 + 56
    step = grid_size / (d_vis - 1)

    _draw_text(ctx, sx0 + sw / 2.0, sy0 + 24, "Live d=7 Defective Patch (N_cand=6, f=1.0%)", size=13.0, color=DARK, bold=True, align="center")
    if patch:
        _draw_text(
            ctx, sx0 + sw / 2.0, sy0 + 42,
            f"d_eff = {patch['d_eff']} (d_X={patch['d_eff_X']}, d_Z={patch['d_eff_Z']}) | H_X H_Z^T = 0 exact",
            size=11.0, color=C_GREEN, bold=True, align="center"
        )

    # Draw regular checkerboard bulk plaquettes
    for pr in range(d_vis - 1):
        for pc in range(d_vis - 1):
            is_z = ((pr + pc) % 2 == 0)
            px = gx0 + pc * step
            py = gy0 + pr * step
            if is_z:
                ctx.set_source_rgba(0.14, 0.40, 0.82, 0.14)
            else:
                ctx.set_source_rgba(0.06, 0.58, 0.54, 0.14)
            ctx.rectangle(px, py, step, step)
            ctx.fill()
            ctx.set_source_rgba(0.55, 0.62, 0.72, 0.35)
            ctx.set_line_width(0.9)
            ctx.rectangle(px, py, step, step)
            ctx.stroke()

    # Highlight super-stabilizer supports from real deformed patch
    dead_data_set = set()
    if patch:
        dead_data_set = {tuple(rc) for rc in patch["dead_data_coords"]}
        for ss in patch["z_super_stabs"]:
            pts_rc = ss["qubits"]
            if len(pts_rc) >= 3:
                cx_m = sum(c for _, c in pts_rc) / len(pts_rc)
                cy_m = sum(r for r, _ in pts_rc) / len(pts_rc)
                pts_sorted = sorted(pts_rc, key=lambda rc: math.atan2(rc[0] - cy_m, rc[1] - cx_m))
                ctx.set_source_rgba(0.14, 0.40, 0.82, 0.38)
                for k, (r, c) in enumerate(pts_sorted):
                    xx, yy = gx0 + c * step, gy0 + r * step
                    if k == 0:
                        ctx.move_to(xx, yy)
                    else:
                        ctx.line_to(xx, yy)
                ctx.close_path()
                ctx.fill_preserve()
                ctx.set_source_rgb(*C_BLUE)
                ctx.set_line_width(2.4)
                ctx.stroke()
        for ss in patch["x_super_stabs"]:
            pts_rc = ss["qubits"]
            if len(pts_rc) >= 3:
                cx_m = sum(c for _, c in pts_rc) / len(pts_rc)
                cy_m = sum(r for r, _ in pts_rc) / len(pts_rc)
                pts_sorted = sorted(pts_rc, key=lambda rc: math.atan2(rc[0] - cy_m, rc[1] - cx_m))
                ctx.set_source_rgba(0.82, 0.62, 0.06, 0.34)
                for k, (r, c) in enumerate(pts_sorted):
                    xx, yy = gx0 + c * step, gy0 + r * step
                    if k == 0:
                        ctx.move_to(xx, yy)
                    else:
                        ctx.line_to(xx, yy)
                ctx.close_path()
                ctx.fill_preserve()
                ctx.set_source_rgb(*C_AMBER)
                ctx.set_line_width(2.4)
                ctx.stroke()

    # Draw all 7x7 data qubits (live = crisp dark dots, dead = red X)
    for r in range(d_vis):
        for c in range(d_vis):
            xx = gx0 + c * step
            yy = gy0 + r * step
            if (r, c) in dead_data_set:
                ctx.set_source_rgb(*C_RED)
                ctx.set_line_width(3.0)
                ctx.move_to(xx - 7, yy - 7)
                ctx.line_to(xx + 7, yy + 7)
                ctx.move_to(xx + 7, yy - 7)
                ctx.line_to(xx - 7, yy + 7)
                ctx.stroke()
            else:
                ctx.set_source_rgb(*DARK)
                ctx.arc(xx, yy, 4.2, 0, 2 * math.pi)
                ctx.fill()

    # Draw dead ancillas (if any) as red hollow diamonds at plaquette centers
    if patch:
        for pr, pc in patch["dead_z_anc_coords"] + patch["dead_x_anc_coords"]:
            xx = gx0 + (pc + 0.5) * step
            yy = gy0 + (pr + 0.5) * step
            ctx.set_source_rgb(*C_RED)
            ctx.set_line_width(2.4)
            ctx.move_to(xx, yy - 8)
            ctx.line_to(xx + 8, yy)
            ctx.line_to(xx, yy + 8)
            ctx.line_to(xx - 8, yy)
            ctx.close_path()
            ctx.stroke()

    # Mini legend at bottom of right sub-area
    ly_b = gy0 + grid_size + 26
    ctx.set_source_rgb(*DARK)
    ctx.arc(sx0 + 26, ly_b, 4.2, 0, 2 * math.pi)
    ctx.fill()
    _draw_text(ctx, sx0 + 38, ly_b + 4, "Live data qubit (49 total)", size=11.0, color=DARK)

    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(2.4)
    ctx.move_to(sx0 + 216, ly_b - 5)
    ctx.line_to(sx0 + 226, ly_b + 5)
    ctx.move_to(sx0 + 226, ly_b - 5)
    ctx.line_to(sx0 + 216, ly_b + 5)
    ctx.stroke()
    _draw_text(ctx, sx0 + 236, ly_b + 4, "Dead site (dropout)", size=11.0, color=C_RED, bold=True)

    ctx.set_source_rgba(0.14, 0.40, 0.82, 0.38)
    ctx.rectangle(sx0 + 20, ly_b + 18, 16, 12)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BLUE)
    ctx.set_line_width(1.6)
    ctx.stroke()
    _draw_text(ctx, sx0 + 42, ly_b + 28, "Merged Z super-stab", size=10.8, color=C_BLUE, bold=True)

    ctx.set_source_rgba(0.82, 0.62, 0.06, 0.34)
    ctx.rectangle(sx0 + 204, ly_b + 18, 16, 12)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_AMBER)
    ctx.set_line_width(1.6)
    ctx.stroke()
    _draw_text(ctx, sx0 + 226, ly_b + 28, "Merged X super-stab", size=10.8, color=C_AMBER, bold=True)

    # Defective threshold shift note at very bottom of schematic box
    def_th = p3["defective_threshold_shift_f1_N6"]
    p_th_d = def_th["threshold_per_round"]["p_2q_th"]
    p_th_i = def_th["ideal_threshold_per_round"]
    if p_th_d is not None and p_th_i is not None:
        _draw_text(
            ctx, sx0 + sw / 2.0, sy0 + sh - 16,
            f"p_drop=1.31% (N=6, f=1%): p_th {p_th_i*100:.2f}% -> {p_th_d*100:.2f}%",
            size=10.8, color=MUTED, bold=True, align="center"
        )


def draw_panel_d(ctx: cairo.Context, data: Dict[str, Any]) -> None:
    """Panel D: Exp141 Machine Scaling & Modular LD400/PT420 Cryostat Budget (100L)."""
    cx, cy, cw, ch = 1218, 750, 1146, 616
    _draw_panel_card(
        ctx, cx, cy, cw, ch,
        "D. Exp141 Physical-to-Logical Scaling & 100-Logical-Qubit LD400/PT420 Cryostat Budget",
        "Exp140 20 mK MXC thermal ceiling = 2,887 cells/cryostat (1,024 nominal module) | Unsplit logical patch allocation"
    )

    sc_all = data["part4_machine_scaling_scenarios"]
    d2_n6 = sc_all["D2_v5_RotaC_P4_S0p25_fast_Q5e5"]["ideal_N6_f1p5"]
    d2_n3 = sc_all["D2_v5_RotaC_P4_S0p25_fast_Q5e5"]["compact_N3_f1p5"]
    d1_n6 = sc_all["D1_v5_RotaC_P4_S0p39_fast_Q5e5"]["ideal_N6_f1p5"]
    d3_n6 = sc_all["D3_Target_FT_P4_p0p005"]["ideal_N6_f1p5"]
    d3_n3 = sc_all["D3_Target_FT_P4_p0p005"]["compact_N3_f1p5"]

    # Top half: Clean horizontal log-scale comparison of N_active vs N_phys_per_logical for eps_L = 1e-9
    bx0, bx1 = cx + 266, cx + cw - 28
    by0, by1 = cy + 80, cy + 286
    _draw_text(ctx, cx + 24, by0 + 14, "Target eps_L = 10^-9 Footprint per Logical Qubit (Solid = Active, Shaded = Placed Candidates)", size=12.8, color=DARK, bold=True)
    by0_plot = by0 + 28

    rows_bar = [
        ("D1 (Q=5e5, S=0.39) N=6", d1_n6, C_TEAL),
        ("D2 (Q=5e5, S=0.25) N=6", d2_n6, C_BLUE),
        ("D2 (Q=5e5, S=0.25) N=3", d2_n3, C_NAVY),
        ("D3 Target (0.50%) N=6", d3_n6, C_GREEN),
        ("D3 Target (0.50%) N=3", d3_n3, C_PURPLE),
    ]
    min_e, max_e = 1.8, 7.2  # 63 to 15.8M -> leaves generous room inside box for text labels!

    def mx_log(val: float) -> float:
        lv = min(max(math.log10(max(val, 10.0)), min_e), max_e)
        return bx0 + (lv - min_e) / (max_e - min_e) * (bx1 - bx0)

    # Vertical grid lines
    for ev, lbl in ((2, "100"), (3, "1k"), (4, "10k"), (5, "100k"), (6, "1M")):
        xx = mx_log(10 ** ev)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(xx, by0_plot)
        ctx.line_to(xx, by1)
        ctx.stroke()
        _draw_text(ctx, xx, by1 + 16, lbl, size=10.8, color=MUTED, align="center")

    # 2,887-cell single LD400/PT420 cryostat thermal ceiling marker
    x_2887 = mx_log(2887)
    ctx.save()
    ctx.set_dash([5.0, 4.0])
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.7)
    ctx.move_to(x_2887, by0_plot)
    ctx.line_to(x_2887, by1)
    ctx.stroke()
    ctx.restore()
    _draw_text(ctx, x_2887, by1 + 27, "^ 2,887 MXC limit", size=10.0, color=C_RED, bold=True, align="center")

    ctx.set_source_rgb(*DARK)
    ctx.set_line_width(1.2)
    ctx.rectangle(bx0, by0_plot, bx1 - bx0, by1 - by0_plot)
    ctx.stroke()

    row_h = (by1 - by0_plot) / len(rows_bar)
    for idx, (lbl, sc_tab, col) in enumerate(rows_bar):
        ry = by0_plot + idx * row_h + 6
        bh = row_h - 12
        _draw_text(ctx, bx0 - 10, ry + bh * 0.72, lbl, size=11.4, color=DARK, bold=True, align="right")
        if sc_tab.get("feasible") and "1e-9" in sc_tab["targets"]:
            t9 = sc_tab["targets"]["1e-9"]
            n_act = t9["N_active"]
            n_phy = t9["N_phys_per_logical"]
            d_st = t9["d_star"]
            w_phy = max(4.0, mx_log(n_phy) - bx0)
            ctx.set_source_rgba(col[0], col[1], col[2], 0.28)
            ctx.rectangle(bx0, ry, w_phy, bh)
            ctx.fill()
            w_act = max(4.0, mx_log(n_act) - bx0)
            ctx.set_source_rgb(*col)
            ctx.rectangle(bx0, ry + 3, w_act, bh - 6)
            ctx.fill()
            _draw_text(
                ctx, bx0 + w_phy + 8, ry + bh * 0.72,
                f"d*={d_st} | {n_act:,} act / {n_phy:,} phys",
                size=10.6, color=DARK, bold=True
            )
        else:
            _draw_text(ctx, bx0 + 10, ry + bh * 0.72, "Not sub-threshold", size=10.8, color=C_RED)

    # Bottom half: Crisp structured Exp141 Machine Scaling Table
    tx0, ty0, tw, th = cx + 22, cy + 318, cw - 44, ch - 336
    _round_rect(ctx, tx0, ty0, tw, th, 8.0)
    ctx.set_source_rgb(0.980, 0.984, 0.992)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.2)
    ctx.stroke()

    cols_x = [tx0 + 14, tx0 + 258, tx0 + 344, tx0 + 414, tx0 + 516, tx0 + 640, tx0 + 786, tx0 + 936]
    headers = [
        "Operating Point (N_cand)",
        "Target",
        "d*",
        "N_active",
        "N_phys / L",
        "L / Fridge (2887)",
        "100L Cryos (2887)",
        "100L Active Cells",
    ]
    ctx.set_source_rgb(*HEADER_BG)
    ctx.rectangle(tx0, ty0, tw, 32)
    ctx.fill()
    for hx, htxt in zip(cols_x, headers):
        _draw_text(ctx, hx, ty0 + 21, htxt, size=11.4, color=(1, 1, 1), bold=True)

    table_rows = [
        ("D2: Q=5e5, S=0.25 (N=6)", d2_n6, "1e-6", C_BLUE),
        ("D2: Q=5e5, S=0.25 (N=6) [Exp141]", d2_n6, "1e-9", C_BLUE),
        ("D2: Q=5e5, S=0.25 (N=6)", d2_n6, "1e-12", C_BLUE),
        ("D2: Q=5e5, S=0.25 (N=3, f*=1.5%)", d2_n3, "1e-9", C_NAVY),
        ("D1: Q=5e5, S=0.39 (N=6, nom)", d1_n6, "1e-9", C_TEAL),
        ("D3: Deep-FT p=0.50% (N=6)", d3_n6, "1e-6", C_GREEN),
        ("D3: Deep-FT p=0.50% (N=6)", d3_n6, "1e-9", C_GREEN),
        ("D3: Deep-FT p=0.50% (N=6)", d3_n6, "1e-12", C_GREEN),
    ]
    rh = (th - 38) / len(table_rows)
    for r_i, (r_lbl, sc_tab, tk, col) in enumerate(table_rows):
        ry = ty0 + 34 + r_i * rh
        if r_i % 2 == 1:
            ctx.set_source_rgba(0.14, 0.40, 0.82, 0.045)
            ctx.rectangle(tx0 + 1, ry, tw - 2, rh)
            ctx.fill()
        if "[Exp141]" in r_lbl:
            ctx.set_source_rgba(0.14, 0.40, 0.82, 0.11)
            ctx.rectangle(tx0 + 1, ry, tw - 2, rh)
            ctx.fill()
        ty_text = ry + rh * 0.68
        _draw_text(ctx, cols_x[0], ty_text, r_lbl, size=11.0, color=col, bold=True)
        _draw_text(ctx, cols_x[1], ty_text, tk, size=11.2, color=DARK, bold=True)
        if sc_tab.get("feasible") and tk in sc_tab["targets"]:
            t = sc_tab["targets"][tk]
            vals = [
                f"{t['d_star']}",
                f"{t['N_active']:,}",
                f"{t['N_phys_per_logical']:,}",
                f"{t['logical_per_cryo_2887_max']}",
                f"{t['cryostats_100L_unsplit_2887']}",
                f"{t['total_active_cells_100L']:,}",
            ]
            for vx, vtxt in zip(cols_x[2:], vals):
                _draw_text(ctx, vx, ty_text, vtxt, size=11.2, color=DARK, bold=("[Exp141]" in r_lbl))
        else:
            _draw_text(ctx, cols_x[2], ty_text, "Above threshold", size=11.0, color=C_RED)


def render_figure() -> None:
    data = json.loads(JSON_PATH.read_text())
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    # Background
    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Header banner
    ctx.set_source_rgb(*HEADER_BG)
    ctx.rectangle(0, 0, W, 92)
    ctx.fill()
    _draw_text(
        ctx, 36, 40,
        "Exp138 (H156): Defective Rotated Surface Code Fault-Tolerant Threshold & v5.0 Machine Scaling",
        size=25.0, color=(1, 1, 1), bold=True
    )
    n_pass = data["n_passed"]
    n_tot = data["n_total"]
    p_th = data["part1_algebra_and_threshold"]["threshold_combined_per_round"]["p_2q_th"]
    p_th_s = f"{p_th*100:.2f}%" if p_th else "N/A"
    _draw_text(
        ctx, 36, 70,
        f"Exact Edmonds Blossom MWPM | Exp137 P4 Pauli-16 + Exp140 N_mux*=32 RO (0.386%) + Exp136 XY8 T2e + Exp139 Rota C + Exp132 BOED | p_2q,th={p_th_s}",
        size=13.6, color=(0.78, 0.85, 0.94)
    )
    # Epistemic & verdict badge on header right
    _round_rect(ctx, W - 404, 18, 368, 56, 8.0)
    ctx.set_source_rgba(1, 1, 1, 0.11)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.30)
    ctx.set_line_width(1.2)
    ctx.stroke()
    _draw_text(ctx, W - 220, 41, f"Pre-Registered Verdicts: {n_pass}/{n_tot} PASS", size=14.0, color=(0.55, 0.95, 0.72), bold=True, align="center")
    _draw_text(ctx, W - 220, 62, "{Sayisal-Simulasyon} | no_lab_measurement = True", size=11.5, color=(0.86, 0.90, 0.96), align="center")

    draw_panel_a(ctx, data)
    draw_panel_b(ctx, data)
    draw_panel_c(ctx, data)
    draw_panel_d(ctx, data)

    surf.write_to_png(str(OUT_PNG))
    print(f"[fig_exp138] Wrote {OUT_PNG.relative_to(REPO_ROOT)} ({W}x{H})")


if __name__ == "__main__":
    render_figure()
