"""
Exp143 (H161) — Publication-Grade 2400x1400 4-Panel Figure Generator (PyCairo).

Run with system Python (has pycairo):
  /usr/bin/python3 -B experiments/exp143_d3_grape_m4_and_hpc_decoder/fig_exp143.py

Reads:  results/exp143_d3_grape_m4_and_hpc_decoder/exp143.json
        results/exp143_d3_grape_m4_and_hpc_decoder/s9hpc_hardware_spec.json
        results/exp138_defective_surface_code_ft/exp138.json (read-only D2 reference)
Writes: results/exp143_d3_grape_m4_and_hpc_decoder/fig_exp143_d3_grape_hpc.png
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cairo


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results" / "exp143_d3_grape_m4_and_hpc_decoder"
JSON_PATH = RESULTS_DIR / "exp143.json"
S9HPC_PATH = RESULTS_DIR / "s9hpc_hardware_spec.json"
EXP138_PATH = REPO_ROOT / "results" / "exp138_defective_surface_code_ft" / "exp138.json"
OUT_PNG = RESULTS_DIR / "fig_exp143_d3_grape_hpc.png"

W, H = 2400, 1400

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
    size: float = 13.5,
    color: Tuple[float, float, float] = DARK,
    bold: bool = True,
) -> None:
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(-math.pi / 2.0)
    _draw_text(ctx, 0.0, 0.0, text, size=size, color=color, bold=bold, align="center")
    ctx.restore()


def _round_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 10.0) -> None:
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
    _draw_text(ctx, x + 20, y + 30, title, size=18.2, color=DARK, bold=True)
    _draw_text(ctx, x + 20, y + 51, subtitle, size=12.5, color=MUTED)


def _draw_marker(
    ctx: cairo.Context, x: float, y: float, shape: str, color: Tuple[float, float, float], r: float = 5.4
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
    ctx.set_source_rgb(1, 1, 1)
    ctx.set_line_width(1.0)
    if shape == "o":
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.stroke()


def _log_y_map(val: float, y_min_exp: float, y_max_exp: float, py0: float, py1: float) -> float:
    lv = math.log10(max(val, 10 ** y_min_exp))
    lv = min(max(lv, y_min_exp), y_max_exp)
    frac = (lv - y_min_exp) / (y_max_exp - y_min_exp)
    return py1 - frac * (py1 - py0)


def draw_panel_a(ctx: cairo.Context, data: Dict[str, Any]) -> None:
    """Panel A: K=8 Fourier GRAPE Control Envelopes & Detuning Chirps (<=300 MHz AWG)."""
    cx, cy, cw, ch = 36, 108, 1146, 618
    p1 = data["part1_grape_optimization"]
    wf = p1["representative_waveform"]
    _draw_panel_card(
        ctx, cx, cy, cw, ch,
        f"A. K=8 Fourier GRAPE M4 Bus Pulse ({wf['pair_label']}: g={wf['g1_mhz']:.2f}/{wf['g2_mhz']:.2f} MHz)",
        f"Hard dipole cap |s(t)|<=1.0 | AWG <=300 MHz energy = {p1['min_bw_300mhz_energy_frac']*100:.2f}% (f99 = {p1['max_bw_99pct_mhz']:.1f} MHz) | 4-slice XY4 t_gate = {p1['noiseless_cons_library']['t_gate_us']:.3f} us"
    )

    t_ns = wf["t_grid_ns"]
    t_max = wf["t_slice_us"] * 1e3

    # Top subplot: Coupling envelopes Re/Im s_1(t), s_2(t)
    px0, px1 = cx + 88, cx + cw - 36
    py0_top, py1_top = cy + 98, cy + 322
    ymin_s, ymax_s = -1.18, 1.18

    def mx(t: float) -> float:
        return px0 + (t / max(t_max, 1e-6)) * (px1 - px0)

    def my_s(v: float) -> float:
        return py1_top - (v - ymin_s) / (ymax_s - ymin_s) * (py1_top - py0_top)

    for yv in (-1.0, -0.5, 0.0, 0.5, 1.0):
        yy = my_s(yv)
        ctx.set_source_rgb(*GRID if yv != 0.0 else (0.75, 0.78, 0.83))
        ctx.set_line_width(1.2 if yv == 0.0 else 0.9)
        ctx.move_to(px0, yy)
        ctx.line_to(px1, yy)
        ctx.stroke()
        _draw_text(ctx, px0 - 10, yy + 4, f"{yv:+.1f}", size=11.0, color=MUTED, align="right")

    # +/-1.0 hard physical ceiling dashed lines
    for yv in (-1.0, 1.0):
        ctx.save()
        ctx.set_dash([5.0, 4.0])
        ctx.set_source_rgba(0.84, 0.19, 0.19, 0.55)
        ctx.set_line_width(1.3)
        ctx.move_to(px0, my_s(yv))
        ctx.line_to(px1, my_s(yv))
        ctx.stroke()
        ctx.restore()

    ctx.set_source_rgb(*DARK)
    ctx.set_line_width(1.4)
    ctx.rectangle(px0, py0_top, px1 - px0, py1_top - py0_top)
    ctx.stroke()

    env_curves = [
        (wf["s1_re"], C_BLUE, False, "Re s_1(t) [Q1 in-phase]"),
        (wf["s1_im"], C_TEAL, True, "Im s_1(t) [Q1 DRAG quad]"),
        (wf["s2_re"], C_ORANGE, False, "Re s_2(t) [Q2 in-phase]"),
        (wf["s2_im"], C_PURPLE, True, "Im s_2(t) [Q2 DRAG quad]"),
    ]
    for arr, col, dashed, _ in env_curves:
        ctx.save()
        if dashed:
            ctx.set_dash([6.0, 4.0])
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.4 if not dashed else 1.9)
        for i, (tx, val) in enumerate(zip(t_ns, arr)):
            xx, yy = mx(tx), my_s(val)
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        ctx.restore()

    # Clean legend strip ABOVE subplot A1 (zero overlap with +1.0 curves!)
    lx = px0 + 4
    for idx, (_, col, dashed, lbl) in enumerate(env_curves):
        ex = lx + idx * 252
        ctx.save()
        if dashed:
            ctx.set_dash([5.0, 3.0])
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.4)
        ctx.move_to(ex, py0_top - 12)
        ctx.line_to(ex + 26, py0_top - 12)
        ctx.stroke()
        ctx.restore()
        _draw_text(ctx, ex + 32, py0_top - 8, lbl, size=11.0, color=DARK, bold=True)

    _draw_rotated_text(ctx, cx + 24, (py0_top + py1_top) / 2.0, "Norm. Coupling s_k(t)", size=12.5, color=DARK, bold=True)

    # Bottom subplot: Detuning chirps Delta_1(t), Delta_2(t) in MHz
    py0_bot, py1_bot = cy + 346, cy + ch - 68
    d_all = wf["delta1_mhz"] + wf["delta2_mhz"]
    d_min = math.floor(min(d_all) - 1.5)
    d_max = math.ceil(max(d_all) + 1.5)

    def my_d(v: float) -> float:
        return py1_bot - (v - d_min) / max(d_max - d_min, 1e-6) * (py1_bot - py0_bot)

    for k in range(5):
        yv = d_min + k * (d_max - d_min) / 4.0
        yy = my_d(yv)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px1, yy)
        ctx.stroke()
        _draw_text(ctx, px0 - 10, yy + 4, f"{yv:.1f}", size=11.0, color=MUTED, align="right")

    for k in range(6):
        tv = k * t_max / 5.0
        xx = mx(tv)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(xx, py0_bot)
        ctx.line_to(xx, py1_bot)
        ctx.stroke()
        _draw_text(ctx, xx, py1_bot + 20, f"{tv:.0f} ns", size=11.5, color=MUTED, align="center")

    ctx.set_source_rgb(*DARK)
    ctx.set_line_width(1.4)
    ctx.rectangle(px0, py0_bot, px1 - px0, py1_bot - py0_bot)
    ctx.stroke()

    for arr, col, lbl in (
        (wf["delta1_mhz"], C_BLUE, "Delta_1(t) / 2pi (Q1 detuning chirp, MHz)"),
        (wf["delta2_mhz"], C_ORANGE, "Delta_2(t) / 2pi (Q2 detuning chirp, MHz)"),
    ):
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.5)
        for i, (tx, val) in enumerate(zip(t_ns, arr)):
            xx, yy = mx(tx), my_d(val)
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()

    # Legend for detuning chirps
    ctx.set_source_rgb(*C_BLUE)
    ctx.set_line_width(2.5)
    ctx.move_to(px0 + 14, py0_bot + 16)
    ctx.line_to(px0 + 42, py0_bot + 16)
    ctx.stroke()
    _draw_text(ctx, px0 + 48, py0_bot + 20, "Delta_1(t) / 2pi [Q1]", size=11.2, color=C_BLUE, bold=True)

    ctx.set_source_rgb(*C_ORANGE)
    ctx.move_to(px0 + 230, py0_bot + 16)
    ctx.line_to(px0 + 258, py0_bot + 16)
    ctx.stroke()
    _draw_text(ctx, px0 + 264, py0_bot + 20, "Delta_2(t) / 2pi [Q2]", size=11.2, color=C_ORANGE, bold=True)

    # Clean audit badge in bottom-right of subplot
    _draw_text(
        ctx, px1 - 10, py1_bot - 12,
        f"Noiseless 4-slice: p_err={p1['noiseless_cons_library']['p_total_err']*100:.3f}%, p_leak={p1['noiseless_cons_library']['p_leak']:.1e}",
        size=11.0, color=C_GREEN, bold=True, align="right"
    )
    _draw_text(ctx, (px0 + px1) / 2.0, py1_bot + 46, "Single XY4 Slice Time t (ns)  [Full CZ = 4 GRAPE Slices + 4x 15 ns XY4 Echo Pulses]", size=12.8, color=DARK, bold=True, align="center")
    _draw_rotated_text(ctx, cx + 24, (py0_bot + py1_bot) / 2.0, "Detuning Delta_k / 2pi (MHz)", size=12.5, color=DARK, bold=True)


def draw_panel_b(ctx: cairo.Context, data: Dict[str, Any]) -> None:
    """Panel B: 12x12 CUDA 1/f Gate Infidelity p_2q: Exp137 P4 vs Exp143 GRAPE."""
    cx, cy, cw, ch = 1218, 108, 1146, 618
    p2 = data["part2_noisy_1f_sweep"]
    _draw_panel_card(
        ctx, cx, cy, cw, ch,
        "B. 12x12 CUDA Strang-Lindblad + M=40 1/f^alpha OU Infidelity (N_traj=512/pair)",
        "5 certified fast Exp131 pairs (g_min>=1.16 MHz): Exp137 P4 vs Exp143 GRAPE (Cons 0.5 kHz vs Echoed Exp136 0.0225 kHz)"
    )

    px0, px1 = cx + 88, cx + cw - 34
    py0, py1 = cy + 88, cy + ch - 96
    ymax = 0.0135  # 1.35%

    def my(v: float) -> float:
        return py1 - min(v, ymax) / ymax * (py1 - py0)

    for yv in (0.0, 0.0025, 0.0050, 0.0075, 0.0100, 0.0125):
        yy = my(yv)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px1, yy)
        ctx.stroke()
        _draw_text(ctx, px0 - 10, yy + 4, f"{yv*100:.2f}%", size=11.5, color=MUTED, align="right")

    # D3 Target horizontal dashed lines (0.50% and 0.45%) — clean lines, pill legend in empty top-right!
    for tv, col in ((0.0050, C_GREEN), (0.0045, C_TEAL)):
        yy = my(tv)
        ctx.save()
        ctx.set_dash([6.0, 4.0])
        ctx.set_source_rgb(*col)
        ctx.set_line_width(1.9 if tv == 0.0050 else 1.3)
        ctx.move_to(px0, yy)
        ctx.line_to(px1, yy)
        ctx.stroke()
        ctx.restore()

    # Clean white legend badge in empty top-right corner of Panel B
    blx, bly, blw, blh = px1 - 294, py0 + 8, 284, 52
    _round_rect(ctx, blx, bly, blw, blh, 6.0)
    ctx.set_source_rgba(1, 1, 1, 0.94)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.1)
    ctx.stroke()
    for idx_t, (col_t, txt_t) in enumerate((
        (C_GREEN, "0.50% D3 Target (F_avg = 99.60%)"),
        (C_TEAL, "0.45% Stretch Target (F_avg = 99.64%)"),
    )):
        ry_t = bly + 18 + idx_t * 20
        ctx.save()
        ctx.set_dash([5.0, 3.0])
        ctx.set_source_rgb(*col_t)
        ctx.set_line_width(2.0)
        ctx.move_to(blx + 10, ry_t)
        ctx.line_to(blx + 34, ry_t)
        ctx.stroke()
        ctx.restore()
        _draw_text(ctx, blx + 42, ry_t + 4, txt_t, size=10.6, color=col_t, bold=True)

    ctx.set_source_rgb(*DARK)
    ctx.set_line_width(1.5)
    ctx.rectangle(px0, py0, px1 - px0, py1 - py0)
    ctx.stroke()

    # 4 operating-point groups on x-axis: (Q=5e5, S=0.39), (Q=5e5, S=0.25), (Q=1e6, S=0.39), (Q=1e6, S=0.25)
    groups = [
        ("Q=5e5\nS=0.39 (nom)", "P4_Q5e5_S0p39", "Q5e5_S0p39"),
        ("Q=5e5\nS=0.25", "P4_Q5e5_S0p25", "Q5e5_S0p25"),
        ("Q=1e6\nS=0.39 (nom)", "P4_Q10e5_S0p39", "Q10e5_S0p39"),
        ("Q=1e6\nS=0.25", "P4_Q10e5_S0p25", "Q10e5_S0p25"),
    ]
    p4_b = p2["p4_baselines_5pair"]
    g_cons = p2["grape_conservative_0p5kHz_nuc"]
    g_echo = p2["grape_echoed_exp136_0p0225kHz_nuc"]

    gw = (px1 - px0) / len(groups)
    bw = gw * 0.20

    for gi, (glbl, p4k, gk) in enumerate(groups):
        gx = px0 + (gi + 0.5) * gw
        vals = [
            (p4_b[p4k]["p_total_err"], C_RED, "P4"),
            (g_cons[gk]["p_total_err"], C_ORANGE, "Cons"),
            (g_cons[gk]["high_g_3pair_subset"]["p_total_err"], C_BLUE, "HiG"),
            (g_echo[gk]["p_total_err"], C_GREEN, "Echo"),
        ]
        start_x = gx - 2.0 * bw - 6
        for bi, (val, col, _) in enumerate(vals):
            bx = start_x + bi * (bw + 4)
            yt = my(val)
            ctx.set_source_rgb(*col)
            ctx.rectangle(bx, yt, bw, py1 - yt)
            ctx.fill()
            _draw_text(
                ctx, bx + bw / 2.0, yt - 6,
                f"{val*100:.2f}%", size=10.0, color=col, bold=True, align="center"
            )
        lines = glbl.split("\n")
        _draw_text(ctx, gx, py1 + 20, lines[0], size=12.0, color=DARK, bold=True, align="center")
        _draw_text(ctx, gx, py1 + 36, lines[1], size=11.0, color=MUTED, align="center")

    # Legend row cleanly below x-axis
    leg_items = [
        (C_RED, "Exp137 P4 Baseline (1.74 us)"),
        (C_ORANGE, "Exp143 GRAPE Cons 0.5kHz (5-pair)"),
        (C_BLUE, "Exp143 GRAPE Cons (high-g >=2MHz)"),
        (C_GREEN, "Exp143 GRAPE Echo Exp136 (0.0225kHz)"),
    ]
    for i, (col, txt) in enumerate(leg_items):
        row = i // 2
        col_i = i % 2
        lx = px0 + col_i * 490
        ly = py1 + 58 + row * 22
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx, ly - 10, 16, 12)
        ctx.fill()
        _draw_text(ctx, lx + 22, ly, txt, size=11.2, color=DARK, bold=True)

    _draw_rotated_text(ctx, cx + 24, (py0 + py1) / 2.0, "2Q Bus CZ Infidelity  p_2q = 1 - F_ent", size=13.2, color=DARK, bold=True)


def draw_panel_c(ctx: cairo.Context, data: Dict[str, Any], e138: Dict[str, Any]) -> None:
    """Panel C: Live Exp138 Edmonds Blossom MWPM Waterfall (D2 vs Exp143 GRAPE D3)."""
    cx, cy, cw, ch = 36, 750, 1146, 616
    _draw_panel_card(
        ctx, cx, cy, cw, ch,
        "C. Live Exp138 Edmonds Blossom MWPM Surface-Code Verification (d = 3..9)",
        "Real extracted Exp143 16-Pauli GRAPE channels fed directly into Exp138 MWPM (p_meas=0.386%, p_1q=0.083%)"
    )

    px0, px1 = cx + 92, cx + cw - 360
    py0, py1 = cy + 78, cy + ch - 68
    ymin_e, ymax_e = -5.0, -1.5  # 1e-5 to 3.16e-2
    ds_plot = [3, 5, 7, 9]

    def mx(d: int) -> float:
        return px0 + (d - 2.4) / (9.6 - 2.4) * (px1 - px0)

    def my(v: float) -> float:
        return _log_y_map(v, ymin_e, ymax_e, py0, py1)

    for exp_v in (-5, -4, -3, -2):
        yy = my(10 ** exp_v)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px1, yy)
        ctx.stroke()
        _draw_text(ctx, px0 - 10, yy + 4, f"10^{exp_v}", size=11.8, color=MUTED, align="right")

    for d in ds_plot:
        xx = mx(d)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(xx, py0)
        ctx.line_to(xx, py1)
        ctx.stroke()
        _draw_text(ctx, xx, py1 + 22, f"d = {d}", size=12.4, color=DARK, bold=True, align="center")
        _draw_text(ctx, xx, py1 + 38, f"({2*d*d-1}q)", size=10.5, color=MUTED, align="center")

    ctx.set_source_rgb(*DARK)
    ctx.set_line_width(1.6)
    ctx.rectangle(px0, py0, px1 - px0, py1 - py0)
    ctx.stroke()

    p3 = data["part3_live_exp138_mwpm_verification"]
    d2_ref = e138["part2_scenarios"]["D2_v5_RotaC_P4_S0p25_fast_Q5e5"]
    d2_cryo = e138["target_logical_error_rates"]["1e-9"]["cryostats_100L_unsplit_2887"]

    curves = [
        ("Exp138 D2 Baseline (P4, 0.92%)", d2_ref, d2_cryo, C_RED, "o", True),
        ("Exp143 Cons 0.5kHz (Q=1e6, S=0.25)", p3["D3_phys_cons_Q1e6_S0p25_5pair"], None, C_ORANGE, "s", False),
        ("Exp143 Cons High-g (>=2 MHz)", p3["D3_phys_cons_Q1e6_S0p25_highG3"], None, C_BLUE, "^", False),
        ("Exp143 Echo Q=5e5 S=0.39 (nom)", p3["D3_phys_echo_Q5e5_S0p39_5pair"], None, C_TEAL, "D", False),
        ("Exp143 Echo Q=1e6 S=0.25 (D3+)", p3["D3_phys_echo_Q1e6_S0p25_5pair"], None, C_GREEN, "o", False),
    ]

    # Right-side clean legend card (zero overlap!)
    lx, ly, lw, lh = px1 + 16, py0, 326, py1 - py0
    _round_rect(ctx, lx, ly, lw, lh, 8.0)
    ctx.set_source_rgb(0.975, 0.980, 0.990)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.2)
    ctx.stroke()
    _draw_text(ctx, lx + 14, ly + 24, "Live MWPM Lambda & 100L Fleet", size=13.2, color=DARK, bold=True)

    for idx, (lbl, sc, cryo_override, col, shp, is_ref) in enumerate(curves):
        fit = sc["fit_per_round"]
        lam = fit["Lambda"]
        A = fit["A"]
        cryo_n = cryo_override if cryo_override is not None else sc["scaling_N6_f1p5"]["targets"]["1e-9"]["cryostats_100L_unsplit_2887"]
        d9_st = (
            e138["target_logical_error_rates"]["1e-9"]["d_star"]
            if is_ref
            else sc["scaling_N6_f1p5"]["targets"]["1e-9"]["d_star"]
        )

        # Fitted dashed exponential slope
        if lam > 1.0:
            ctx.save()
            ctx.set_dash([5.0, 4.0])
            ctx.set_source_rgba(col[0], col[1], col[2], 0.50)
            ctx.set_line_width(1.6)
            for j, d in enumerate(ds_plot):
                pred = A * (lam ** (-(d + 1.0) / 2.0))
                if j == 0:
                    ctx.move_to(mx(d), my(pred))
                else:
                    ctx.line_to(mx(d), my(pred))
            ctx.stroke()
            ctx.restore()

        # Empirical curve with Wilson 95% error bars
        pts_xy = []
        for d in ds_plot:
            comb = sc["by_d"][f"d{d}"]["combined"]
            ev = comb["eps_L_round"]
            ev_p = max(ev, 10 ** (ymin_e + 0.08))
            lo = max(comb["ci95_round"][0], 10 ** ymin_e)
            hi = max(comb["ci95_round"][1], 10 ** ymin_e)
            pts_xy.append((mx(d), my(ev_p), my(lo), my(hi)))

        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.5)
        for j, (xx, yy, _, _) in enumerate(pts_xy):
            if j == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        for xx, yy, ylo, yhi in pts_xy:
            ctx.set_source_rgba(col[0], col[1], col[2], 0.48)
            ctx.set_line_width(1.3)
            ctx.move_to(xx, ylo)
            ctx.line_to(xx, yhi)
            ctx.stroke()
            _draw_marker(ctx, xx, yy, shp, col, r=5.2)

        # Legend entry
        ry = ly + 56 + idx * 80
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.6)
        ctx.move_to(lx + 14, ry)
        ctx.line_to(lx + 40, ry)
        ctx.stroke()
        _draw_marker(ctx, lx + 27, ry, shp, col, r=4.8)
        _draw_text(ctx, lx + 48, ry + 4, lbl, size=11.4, color=DARK, bold=True)
        _draw_text(
            ctx, lx + 48, ry + 22,
            f"Lambda = {lam:.2f} | d*(10^-9) = {d9_st}",
            size=11.2, color=col, bold=True
        )
        red_str = f" ({d2_cryo / max(cryo_n, 1):.1f}x cut)" if not is_ref else " (v5.0 base)"
        _draw_text(
            ctx, lx + 48, ry + 39,
            f"100L fleet: {cryo_n} cryos{red_str}",
            size=10.6, color=MUTED
        )

    _draw_text(ctx, (px0 + px1) / 2.0, py1 + 56, "Rotated Surface Code Distance d (Active Qubits = 2d^2 - 1)", size=12.8, color=DARK, bold=True, align="center")
    _draw_rotated_text(ctx, cx + 24, (py0 + py1) / 2.0, "Per-Round Logical Error Rate  eps_L,round", size=13.2, color=DARK, bold=True)


def draw_panel_d(ctx: cairo.Context, data: Dict[str, Any], s9hpc: Dict[str, Any]) -> None:
    """Panel D: Option-HPC 100G RoCEv2 RDMA Real-Time Decoder Wall & 100L Resource Budget."""
    cx, cy, cw, ch = 1218, 750, 1146, 616
    hpc = data["part4_option_hpc_decoder_wall"]
    cycs = hpc["cycle_times_us"]
    _draw_panel_card(
        ctx, cx, cy, cw, ch,
        "D. Option-HPC 100 Gbps RoCEv2 RDMA Real-Time Decoder Backlog Wall & S9.HPC Budget",
        f"Ingest = {hpc['tau_ingest_us']*1e3:.0f} ns (RFSoC 320 ns + 100G RoCEv2 450 ns) | Backlog-free requires tau_eff < T_cyc"
    )

    # Top half: Log-Y grouped bars comparing Single-Core CPU vs Option-HPC Parallel E2E latency
    bx0, bx1 = cx + 88, cx + cw - 34
    by0, by1 = cy + 80, cy + 324
    ymin_e, ymax_e = -0.35, 1.88  # 0.45 us to 76 us -> 34.07us bar fits cleanly with headroom!

    def my(v: float) -> float:
        return _log_y_map(v, ymin_e, ymax_e, by0, by1)

    for yv, lbl in ((0.5, "0.5 us"), (1.0, "1 us"), (2.0, "2 us"), (5.0, "5 us"), (10.0, "10 us"), (20.0, "20 us"), (50.0, "50 us")):
        yy = my(yv)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(bx0, yy)
        ctx.line_to(bx1, yy)
        ctx.stroke()
        _draw_text(ctx, bx0 - 10, yy + 4, lbl, size=10.8, color=MUTED, align="right")

    # Horizontal backlog-wall lines: T_cyc = 2.62 us (fast), T_cyc(D3), 8.93 us (v5 4-CZ)
    walls = [
        (cycs["T_cyc_fast_exp140_demo_us"], C_RED, f"2.62 us (Exp140 fast RO)", -5),
        (cycs["T_cyc_4cz_d3_grape_us"], C_ORANGE, f"{cycs['T_cyc_4cz_d3_grape_us']:.2f} us (v6 D3 4-CZ)", 12),
        (cycs["T_cyc_4cz_v5_exp138_us"], C_GREEN, f"8.93 us (v5 4-CZ)", -5),
    ]
    for tv, col, lbl, dy in walls:
        yy = my(tv)
        ctx.save()
        ctx.set_dash([6.0, 4.0])
        ctx.set_source_rgb(*col)
        ctx.set_line_width(1.6)
        ctx.move_to(bx0, yy)
        ctx.line_to(bx1, yy)
        ctx.stroke()
        ctx.restore()
        _draw_text(ctx, bx0 + 8, yy + dy, lbl, size=10.0, color=col, bold=True)

    ctx.set_source_rgb(*DARK)
    ctx.set_line_width(1.4)
    ctx.rectangle(bx0, by0, bx1 - bx0, by1 - by0)
    ctx.stroke()

    surf = hpc["surface_code_scaling"]
    qldpc = hpc["qldpc_gross_144_12_12"]
    bar_items = [
        ("Surf d=7", surf[0]["tau_cpu_single_us"], surf[0]["tau_hpc_e2e_stream_us"]),
        ("Surf d=11", surf[1]["tau_cpu_single_us"], surf[1]["tau_hpc_e2e_stream_us"]),
        ("Surf d=21", surf[2]["tau_cpu_single_us"], surf[2]["tau_hpc_e2e_stream_us"]),
        ("Surf d=37", surf[3]["tau_cpu_single_us"], surf[3]["tau_hpc_e2e_stream_us"]),
        ("qLDPC 144", qldpc["tau_cpu_mean_us"], qldpc["tau_hpc_e2e_mean_us"]),
    ]
    gw = (bx1 - bx0) / len(bar_items)
    bw = gw * 0.30
    for idx, (lbl, t_cpu, t_hpc) in enumerate(bar_items):
        gx = bx0 + (idx + 0.5) * gw
        # Bar 1: Single-core CPU
        x1 = gx - bw - 4
        y1 = my(t_cpu)
        ctx.set_source_rgb(*C_RED if t_cpu >= cycs["T_cyc_4cz_v5_exp138_us"] else C_ORANGE)
        ctx.rectangle(x1, y1, bw, by1 - y1)
        ctx.fill()
        _draw_text(ctx, x1 + bw / 2.0, y1 - 5, f"{t_cpu:.2f}us", size=10.0, color=DARK, bold=True, align="center")

        # Bar 2: Option-HPC Parallel E2E
        x2 = gx + 4
        y2 = my(t_hpc)
        ctx.set_source_rgb(*C_BLUE if idx < 4 else C_GREEN)
        ctx.rectangle(x2, y2, bw, by1 - y2)
        ctx.fill()
        if idx == 4:
            # Place qLDPC 2.32us label cleanly inside green bar so it never touches the 2.62us dashed line!
            _draw_text(ctx, x2 + bw / 2.0, y2 + 15, f"{t_hpc:.2f}us", size=10.0, color=(1, 1, 1), bold=True, align="center")
        else:
            _draw_text(ctx, x2 + bw / 2.0, y2 - 5, f"{t_hpc:.2f}us", size=10.0, color=C_BLUE, bold=True, align="center")

        _draw_text(ctx, gx, by1 + 18, lbl, size=11.6, color=DARK, bold=True, align="center")

    # Clean top-left legend in empty area above Surf d=7 / d=11
    ctx.set_source_rgb(*C_ORANGE)
    ctx.rectangle(bx0 + 10, by0 + 10, 14, 11)
    ctx.fill()
    _draw_text(ctx, bx0 + 29, by0 + 20, "Single-Core CPU (Red > 8.93us wall)", size=10.4, color=DARK, bold=True)
    ctx.set_source_rgb(*C_BLUE)
    ctx.rectangle(bx0 + 265, by0 + 10, 14, 11)
    ctx.fill()
    _draw_text(ctx, bx0 + 284, by0 + 20, "Option-HPC 100G E2E (Green = qLDPC)", size=10.4, color=C_BLUE, bold=True)

    _draw_rotated_text(ctx, cx + 24, (by0 + by1) / 2.0, "Decode Latency / Round (us)", size=12.5, color=DARK, bold=True)

    # Bottom half: Clean Engineering Table for 100L Scaling & S9.HPC Hardware Spec
    tx0, ty0, tw, th = cx + 22, cy + 356, cw - 44, ch - 374
    _round_rect(ctx, tx0, ty0, tw, th, 8.0)
    ctx.set_source_rgb(0.980, 0.984, 0.992)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.2)
    ctx.stroke()

    cols_x = [tx0 + 14, tx0 + 216, tx0 + 344, tx0 + 476, tx0 + 610, tx0 + 738, tx0 + 868, tx0 + 986]
    headers = ["QEC Code (100L)", "CPU 1-Core", "HPC E2E", "100L BW (v5/D3)", "100G Fibers", "HPC Nodes", "Power (kW)", "Backlog"]
    ctx.set_source_rgb(*HEADER_BG)
    ctx.rectangle(tx0, ty0, tw, 30)
    ctx.fill()
    for hx, htxt in zip(cols_x, headers):
        _draw_text(ctx, hx, ty0 + 20, htxt, size=11.0, color=(1, 1, 1), bold=True)

    t_rows = []
    for r in surf:
        t_rows.append((
            f"Surface d={r['d']} ({r['n_checks']} chk)",
            f"{r['tau_cpu_single_us']:.2f} us",
            f"{r['tau_hpc_e2e_stream_us']:.2f} us",
            f"{r['bw_100L_hard_v5_gbps']:.1f} / {r['bw_100L_hard_d3_gbps']:.1f} G",
            f"{r['fibers_100g_100L_hard_d3']}x 100G",
            f"{r['hpc_nodes_100L']} ({r['option_hpc_4u_modules_100L']}x 4U)",
            f"{r['hpc_power_kw_100L']:.1f} kW",
            "FREE (8.93us)" if r["backlog_free_hpc_8p93us"] else "STALL",
            C_BLUE if r["d"] == 37 else DARK,
        ))
    t_rows.append((
        "qLDPC [[144,12,12]] (108L)",
        f"{qldpc['tau_cpu_mean_us']:.2f} us",
        f"{qldpc['tau_hpc_e2e_mean_us']:.2f} us",
        f"{qldpc['bw_108L_hard_v5_gbps']:.2f} / {qldpc['bw_108L_hard_d3_gbps']:.2f} G",
        f"{qldpc['fibers_100g_108L_hard']}x 100G",
        f"{qldpc['hpc_nodes_108L']} (1x 4U!)",
        f"{qldpc['hpc_power_kw_108L']:.2f} kW",
        "FREE (2.62us!)",
        C_GREEN,
    ))

    rh = (th - 64) / len(t_rows)
    for ri, row in enumerate(t_rows):
        ry = ty0 + 32 + ri * rh
        if ri % 2 == 1:
            ctx.set_source_rgba(0.14, 0.40, 0.82, 0.045)
            ctx.rectangle(tx0 + 1, ry, tw - 2, rh)
            ctx.fill()
        if ri == len(t_rows) - 1:
            ctx.set_source_rgba(0.09, 0.60, 0.30, 0.10)
            ctx.rectangle(tx0 + 1, ry, tw - 2, rh)
            ctx.fill()
        ty_t = ry + rh * 0.68
        col_r = row[-1]
        for ci, val in enumerate(row[:-1]):
            _draw_text(ctx, cols_x[ci], ty_t, val, size=10.8, color=col_r if ci in (0, 2, 7) else DARK, bold=(ci in (0, 7)))

    # S9.HPC hardware spec footer strip inside Panel D
    tot = s9hpc["totals_base_4u_option_hpc_module"]
    _draw_text(
        ctx, tx0 + 14, ty0 + th - 10,
        f"S9.HPC Base 4U Option-HPC Module (CAD/BOM v6.0): {tot['total_mass_kg']:.1f} kg | {tot['room_temp_power_W']:.0f} W (0 W cryo) | 4x 100G QSFP28 | Est. ${tot['cost_usd_nom']:,} (${tot['cost_usd_low']//1000}k-${tot['cost_usd_high']//1000}k, {{Varsayim}})",
        size=10.6, color=C_NAVY, bold=True
    )


def render_figure() -> None:
    data = json.loads(JSON_PATH.read_text())
    s9hpc = json.loads(S9HPC_PATH.read_text())
    e138 = json.loads(EXP138_PATH.read_text())

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Header banner
    ctx.set_source_rgb(*HEADER_BG)
    ctx.rectangle(0, 0, W, 92)
    ctx.fill()
    _draw_text(
        ctx, 36, 40,
        "Exp143 (H161): D3 Multi-Harmonic Fourier GRAPE M4 Bus Gate & Option-HPC 100G RDMA Real-Time Decoder",
        size=24.2, color=(1, 1, 1), bold=True
    )
    e10 = data["part2_noisy_1f_sweep"]["grape_echoed_exp136_0p0225kHz_nuc"]["Q10e5_S0p25"]
    c10 = data["part2_noisy_1f_sweep"]["grape_conservative_0p5kHz_nuc"]["Q10e5_S0p25"]
    _draw_text(
        ctx, 36, 70,
        f"12x12 CUDA Strang-Lindblad + M=40 1/f OU | Cons 0.5kHz p_2q={c10['p_total_err']*100:.2f}% (hi-g {c10['high_g_3pair_subset']['p_total_err']*100:.2f}%) | Echo Exp136 p_2q={e10['p_total_err']*100:.2f}% (F_avg={e10['F_avg']*100:.2f}%) | 100G RoCEv2 Option-HPC",
        size=13.2, color=(0.78, 0.85, 0.94)
    )

    _round_rect(ctx, W - 404, 18, 368, 56, 8.0)
    ctx.set_source_rgba(1, 1, 1, 0.11)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.30)
    ctx.set_line_width(1.2)
    ctx.stroke()
    _draw_text(ctx, W - 220, 41, f"Pre-Registered Verdicts: {data['n_passed']}/{data['n_total']} PASS", size=14.0, color=(0.55, 0.95, 0.72), bold=True, align="center")
    _draw_text(ctx, W - 220, 62, "{Sayisal-Simulasyon} | no_lab_measurement = True", size=11.5, color=(0.86, 0.90, 0.96), align="center")

    draw_panel_a(ctx, data)
    draw_panel_b(ctx, data)
    draw_panel_c(ctx, data, e138)
    draw_panel_d(ctx, data, s9hpc)

    surf.write_to_png(str(OUT_PNG))
    print(f"[fig_exp143] Wrote {OUT_PNG.relative_to(REPO_ROOT)} ({W}x{H})")


if __name__ == "__main__":
    render_figure()
