"""Exp142 (H160) PyCairo Publication Figure Generator (2400x1400 PNG).

Runs under system Python (/usr/bin/python3 -B) with pycairo.
Reads results/exp142_option_q_multispecies_qram/plot_data_exp142.json via Path(__file__).resolve()
(zero hardcoded host paths) and produces:
  results/exp142_option_q_multispecies_qram/fig_exp142_option_q_multispecies.png

Panels:
  A. Option-Q 50 Ohm <-> 3 kOhm (60:1) Impedance Transformers (N=1 vs N=3 vs N=5 Chebyshev vs
     Klopfenstein Taper, |S11| dB across 2-10 GHz with 4-8 GHz band shading).
  B. Exact 12x12 Lindblad qRAM Storage Fidelity F(t_store) across 10 us - 10 s: Bare Transmon Idle
     vs 31P qRAM (T2n*=17.7 ms, XY8-DD 1 s & 3 s) & 29Si K=8 Bank (>8,400x lifetime gain).
  C. 167Er (1536 nm) Silicon Photonic Crystal Cavity Telecom Link over 1-50 km SMF-28 Fiber:
     Barrett-Kok (2-ph) vs Cabrillo (1-ph) Entanglement Rate R_ent(L) & Fidelity F_ent(L).
  D. S1-Multi Heavy-Ion ZBL-BCA Straggle Advantage (31P vs 121Sb vs 167Er) & 121Sb I=7/2 8-Level
     Qudit Encodings under 500 Hz Quadrupole Strain Noise (Clock vs Spin-Cat vs Gross Binomial).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cairo

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp142_option_q_multispecies_qram"
DATA_PATH = OUT_DIR / "plot_data_exp142.json"
OUT_PNG = OUT_DIR / "fig_exp142_option_q_multispecies.png"

BG = (0.980, 0.985, 0.992)
PANEL_BG = (1.0, 1.0, 1.0)
BORDER = (0.78, 0.83, 0.89)
GRID = (0.90, 0.92, 0.95)
TEXT = (0.10, 0.13, 0.18)
MUTED = (0.37, 0.43, 0.52)

C_BLUE = (0.16, 0.44, 0.74)
C_RED = (0.82, 0.20, 0.22)
C_GREEN = (0.09, 0.56, 0.42)
C_AMBER = (0.90, 0.55, 0.12)
C_PURP = (0.52, 0.30, 0.72)
C_TEAL = (0.08, 0.52, 0.68)
C_SLATE = (0.45, 0.51, 0.59)


def set_font(ctx: cairo.Context, size: float, bold: bool = False) -> None:
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)


def draw_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 13.5,
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


def draw_rot_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 13.5,
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


def draw_card(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, badge: str, bcol: tuple[float, float, float]) -> None:
    draw_rounded_rect(ctx, x, y, w, h, 10.0)
    ctx.set_source_rgb(*PANEL_BG)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.6)
    ctx.stroke()

    ctx.set_source_rgb(0.955, 0.968, 0.985)
    ctx.rectangle(x + 1, y + 1, w - 2, 44)
    ctx.fill()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.move_to(x, y + 45)
    ctx.line_to(x + w, y + 45)
    ctx.stroke()

    draw_text(ctx, title, x + 16, y + 29, size=16.0, color=TEXT, bold=True)
    set_font(ctx, 12.2, bold=True)
    bw = ctx.text_extents(badge).width + 20
    bx, by = x + w - bw - 14, y + 10
    draw_rounded_rect(ctx, bx, by, bw, 26, 6.0)
    ctx.set_source_rgb(*bcol)
    ctx.fill()
    draw_text(ctx, badge, bx + bw / 2.0, by + 17.5, size=12.2, color=(1.0, 1.0, 1.0), bold=True, align="center")


def draw_frame(ctx: cairo.Context, px: float, py: float, pw: float, ph: float) -> None:
    ctx.set_source_rgb(0.28, 0.34, 0.42)
    ctx.set_line_width(1.4)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()


def draw_panel_a(ctx: cairo.Context, d: dict[str, Any], cx: float, cy: float, cw: float, ch: float) -> None:
    pa = d["panel_a_xfmr"]
    badge = f"N=5 BW: {pa['N5_bw15']:.2f} GHz | IL: {pa['N5_IL6']:.4f} dB"
    draw_card(ctx, cx, cy, cw, ch, "A. Option-Q 50 Ohm <-> 3 kOhm Impedance Transformers (Exact ABCD, Q=1e5)", badge, C_GREEN)

    px, py, pw, ph = cx + 82, cy + 72, cw - 110, ch - 172
    f_min, f_max = 2.0, 10.0
    y_min, y_max = -50.0, 0.0

    def xm(f: float) -> float:
        return px + pw * ((f - f_min) / (f_max - f_min))

    def ym(db: float) -> float:
        v = max(y_min, min(y_max, db))
        return py + ph * (1.0 - (v - y_min) / (y_max - y_min))

    # Shaded 4-8 GHz superconducting operating octave
    ctx.set_source_rgba(0.09, 0.56, 0.42, 0.08)
    ctx.rectangle(xm(4.0), py, xm(8.0) - xm(4.0), ph)
    ctx.fill()
    draw_text(ctx, "4-8 GHz Operating Band", xm(6.0), py + 18, size=11.8, color=C_GREEN, bold=True, align="center")

    for db in [0, -10, -15, -20, -30, -40, -50]:
        yy = ym(float(db))
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px, yy); ctx.line_to(px + pw, yy); ctx.stroke()
        draw_text(ctx, f"{db} dB", px - 8, yy + 4.5, size=11.8, color=MUTED, align="right")

    for fv in [2, 3, 4, 5, 6, 7, 8, 9, 10]:
        xx = xm(float(fv))
        ctx.set_source_rgb(*GRID)
        ctx.move_to(xx, py); ctx.line_to(xx, py + ph); ctx.stroke()
        draw_text(ctx, f"{fv}", xx, py + ph + 20, size=12.0, color=TEXT, align="center")

    # -15 dB spec line
    y15 = ym(-15.0)
    ctx.save(); ctx.set_dash([6.0, 4.0]); ctx.set_source_rgb(*C_RED); ctx.set_line_width(1.4)
    ctx.move_to(px, y15); ctx.line_to(px + pw, y15); ctx.stroke(); ctx.restore()
    draw_text(ctx, "-15 dB Return-Loss Gate", px + pw - 8, y15 - 6, size=11.0, color=C_RED, bold=True, align="right")

    draw_frame(ctx, px, py, pw, ph)
    draw_text(ctx, "Microwave Frequency (GHz)", px + pw / 2.0, py + ph + 42, size=13.0, color=TEXT, bold=True, align="center")
    draw_rot_text(ctx, "Reflection Coefficient |S11| (dB)", cx + 22, py + ph / 2.0, size=13.0, color=TEXT, bold=True)

    freqs = pa["freqs_GHz"]
    curves = [
        ("Single lambda/4 (N=1, BW=0.36 GHz)", pa["N1_s11_dB"], C_SLATE, True, 2.0),
        ("Chebyshev 3-Sec (N=3, BW=4.10 GHz)", pa["N3_s11_dB"], C_BLUE, False, 2.4),
        ("Chebyshev 5-Sec (N=5, BW=5.20 GHz)", pa["N5_s11_dB"], C_GREEN, False, 3.0),
        ("Klopfenstein Taper (BW=6.02 GHz)", pa["Klop_s11_dB"], C_PURP, True, 2.5),
    ]
    for _lbl, vals, col, dashed, lw in curves:
        ctx.save()
        if dashed:
            ctx.set_dash([7.0, 4.0])
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        for i, (f, v) in enumerate(zip(freqs, vals)):
            xx, yy = xm(float(f)), ym(float(v))
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        ctx.restore()

    # Legend (2x2 below x-axis)
    for idx, (lbl, _v, col, _d, _lw) in enumerate(curves):
        row, col_i = idx // 2, idx % 2
        lx = px + col_i * 485
        ly = py + ph + 66 + row * 22
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx, ly - 9, 14, 10); ctx.fill()
        draw_text(ctx, lbl, lx + 20, ly, size=11.8, color=TEXT, bold=(idx == 2))


def draw_panel_b(ctx: cairo.Context, d: dict[str, Any], cx: float, cy: float, cw: float, ch: float) -> None:
    pb = d["panel_b_qram"]
    badge = f"F_rt={pb['F_swap_rt']:.4f} | Gain: {pb['gain_1s']:.0f}x"
    draw_card(ctx, cx, cy, cw, ch, "B. 12x12 Lindblad qRAM Storage Fidelity (Transmon <-> 31P Nuclear Memory)", badge, C_BLUE)

    px, py, pw, ph = cx + 82, cy + 72, cw - 110, ch - 172
    t_min_l, t_max_l = -5.0, 1.0  # 10 us to 10 s
    y_min, y_max = 0.45, 1.02

    def xm(t_s: float) -> float:
        lt = max(t_min_l, min(t_max_l, math.log10(max(t_s, 1e-6))))
        return px + pw * ((lt - t_min_l) / (t_max_l - t_min_l))

    def ym(f: float) -> float:
        return py + ph * (1.0 - (f - y_min) / (y_max - y_min))

    for fv in [0.50, 0.60, 0.70, 0.80, 0.90, 1.00]:
        yy = ym(fv)
        ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
        ctx.move_to(px, yy); ctx.line_to(px + pw, yy); ctx.stroke()
        draw_text(ctx, f"{fv:.2f}", px - 8, yy + 4.5, size=11.8, color=MUTED, align="right")

    for tp, lbl in [(1e-5, "10 us"), (1e-4, "100 us"), (1e-3, "1 ms"), (1e-2, "10 ms"), (1e-1, "100 ms"), (1.0, "1 s"), (10.0, "10 s")]:
        xx = xm(tp)
        ctx.set_source_rgb(*GRID)
        ctx.move_to(xx, py); ctx.line_to(xx, py + ph); ctx.stroke()
        draw_text(ctx, lbl, xx, py + ph + 20, size=11.8, color=TEXT, align="center")

    # F=0.90 threshold line
    y90 = ym(0.90)
    ctx.save(); ctx.set_dash([6.0, 4.0]); ctx.set_source_rgb(*C_RED); ctx.set_line_width(1.4)
    ctx.move_to(px, y90); ctx.line_to(px + pw, y90); ctx.stroke(); ctx.restore()
    draw_text(ctx, "F = 0.90 Memory Threshold", px + pw - 8, y90 - 7, size=11.2, color=C_RED, bold=True, align="right")

    draw_frame(ctx, px, py, pw, ph)
    draw_text(ctx, "Quantum Memory Storage Time t_store [log scale]", px + pw / 2.0, py + ph + 42, size=13.0, color=TEXT, bold=True, align="center")
    draw_rot_text(ctx, "Average State Fidelity F_avg", cx + 22, py + ph / 2.0, size=13.0, color=TEXT, bold=True)

    ts = pb["t_store_s"]
    curves = [
        ("Bare Transmon Idle (T1=200us, T2=150us)", pb["F_bare"], C_RED, False, 2.8),
        ("Option-Q 31P qRAM (T2n*=17.7 ms, no DD)", pb["F_star"], C_AMBER, True, 2.4),
        ("Option-Q 31P qRAM (XY8-DD, T2n=1.0 s)", pb["F_dd1s"], C_GREEN, False, 3.0),
        ("Option-Q 31P qRAM (XY8-DD, T2n=3.0 s)", pb["F_dd3s"], C_PURP, True, 2.4),
        ("Option-Q 29Si K=8 Bank (XY8-DD, 1.0 s)", pb["F_29si"], C_TEAL, False, 2.1),
    ]
    for _lbl, vals, col, dashed, lw in curves:
        ctx.save()
        if dashed:
            ctx.set_dash([7.0, 4.0])
        ctx.set_source_rgb(*col); ctx.set_line_width(lw)
        for i, (t, f) in enumerate(zip(ts, vals)):
            xx, yy = xm(float(t)), ym(float(f))
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke(); ctx.restore()

    # Callout box in clean lower-left whitespace (t ~ 1 ms .. 100 ms, y ~ 0.55 .. 0.72)
    bx, by, bw, bh = xm(2.2e-3), ym(0.75), 340, 74
    draw_rounded_rect(ctx, bx, by, bw, bh, 6.0)
    ctx.set_source_rgba(0.96, 0.99, 0.97, 0.96); ctx.fill_preserve()
    ctx.set_source_rgb(*C_GREEN); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(ctx, "12x12 Lindblad CPTP (|Tr-1|=4.4e-16):", bx + 10, by + 20, size=11.5, color=TEXT, bold=True)
    draw_text(ctx, f"Breakeven vs Transmon: {pb['t_breakeven_us']:.1f} us", bx + 10, by + 39, size=11.3, color=MUTED)
    draw_text(ctx, f"F=0.90 Lifetime Gain: {pb['gain_1s']:.0f}x (1 s DD)", bx + 10, by + 58, size=11.5, color=C_GREEN, bold=True)

    for idx, (lbl, _v, col, _d, _lw) in enumerate(curves):
        row, col_i = idx // 2, idx % 2
        lx = px + col_i * 485
        ly = py + ph + 62 + row * 19
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx, ly - 8, 13, 9); ctx.fill()
        draw_text(ctx, lbl, lx + 18, ly, size=11.2, color=TEXT, bold=(idx in (0, 2)))


def draw_panel_c(ctx: cairo.Context, d: dict[str, Any], cx: float, cy: float, cw: float, ch: float) -> None:
    pc = d["panel_c_er167"]
    badge = f"F_P,eff={pc['F_P_eff']:.0f} | tau={pc['tau_cav_us']:.1f} us"
    draw_card(ctx, cx, cy, cw, ch, "C. S1-Multi 167Er (1536 nm) Si-Photonic Cavity & 1-50 km SMF-28 Quantum Link", badge, C_TEAL)

    px, py, pw, ph = cx + 82, cy + 72, cw - 155, ch - 172
    l_min, l_max = 0.0, 52.0
    r_min_l, r_max_l = 1.0, 4.5  # 10 Hz to 31,600 Hz

    def xm(L: float) -> float:
        return px + pw * ((L - l_min) / (l_max - l_min))

    def ym_rate(hz: float) -> float:
        lv = max(r_min_l, min(r_max_l, math.log10(max(hz, 10.0))))
        return py + ph * (1.0 - (lv - r_min_l) / (r_max_l - r_min_l))

    def ym_fid(f: float) -> float:
        return py + ph * (1.0 - (f - 0.70) / (1.00 - 0.70))

    for rv, lbl in [(10, "10"), (30, "30"), (100, "100"), (300, "300"), (1000, "1k"), (3000, "3k"), (10000, "10k"), (30000, "30k")]:
        yy = ym_rate(float(rv))
        ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
        ctx.move_to(px, yy); ctx.line_to(px + pw, yy); ctx.stroke()
        draw_text(ctx, lbl, px - 8, yy + 4.5, size=11.8, color=MUTED, align="right")

    for lv in [0, 10, 20, 30, 40, 50]:
        xx = xm(float(lv))
        ctx.set_source_rgb(*GRID)
        ctx.move_to(xx, py); ctx.line_to(xx, py + ph); ctx.stroke()
        draw_text(ctx, f"{lv} km", xx, py + ph + 20, size=12.0, color=TEXT, align="center")

    for fv in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]:
        yy = ym_fid(fv)
        draw_text(ctx, f"{fv:.2f}", px + pw + 10, yy + 4.5, size=11.5, color=C_GREEN, align="left")

    draw_frame(ctx, px, py, pw, ph)
    draw_text(ctx, "SMF-28 Telecom Fiber Distance L (km)  [0.20 dB/km @ 1536 nm]", px + pw / 2.0, py + ph + 42, size=13.0, color=TEXT, bold=True, align="center")
    draw_rot_text(ctx, "Entanglement Rate R_ent (Hz)  [log]", cx + 22, py + ph / 2.0, size=13.0, color=C_BLUE, bold=True)
    draw_rot_text(ctx, "Heralded Entanglement Fidelity F_ent", cx + cw - 20, py + ph / 2.0, size=13.0, color=C_GREEN, bold=True)

    Ls = pc["distances_km"]
    # Rate curves (left axis)
    for vals, col, dashed, lw in [
        (pc["R_BK_Hz"], C_BLUE, False, 2.8),
        (pc["R_1ph_Hz"], C_PURP, True, 2.6),
    ]:
        ctx.save()
        if dashed:
            ctx.set_dash([7.0, 4.0])
        ctx.set_source_rgb(*col); ctx.set_line_width(lw)
        for i, (L, r) in enumerate(zip(Ls, vals)):
            xx, yy = xm(float(L)), ym_rate(float(r))
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke(); ctx.restore()
        for L, r in zip(Ls, vals):
            ctx.set_source_rgb(*col)
            ctx.arc(xm(float(L)), ym_rate(float(r)), 4.2, 0.0, 2.0 * math.pi); ctx.fill()

    # Fidelity curves (right axis)
    for vals, col, dashed, lw in [
        (pc["F_BK"], C_GREEN, False, 2.6),
        (pc["F_1ph"], C_AMBER, True, 2.4),
    ]:
        ctx.save()
        if dashed:
            ctx.set_dash([5.0, 4.0])
        ctx.set_source_rgb(*col); ctx.set_line_width(lw)
        for i, (L, f) in enumerate(zip(Ls, vals)):
            xx, yy = xm(float(L)), ym_fid(float(f))
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke(); ctx.restore()
        for L, f in zip(Ls, vals):
            ctx.set_source_rgb(*col)
            ctx.arc(xm(float(L)), ym_fid(float(f)), 3.8, 0.0, 2.0 * math.pi); ctx.fill()

    # 10 km vertical marker
    x10 = xm(10.0)
    ctx.save(); ctx.set_dash([4.0, 4.0]); ctx.set_source_rgb(*MUTED); ctx.set_line_width(1.2)
    ctx.move_to(x10, py); ctx.line_to(x10, py + ph); ctx.stroke(); ctx.restore()
    draw_text(ctx, "10 km Anchor", x10 + 6, py + ph - 10, size=11.2, color=MUTED, bold=True)

    legs = [
        ("Barrett-Kok Rate R_ent (L)", C_BLUE),
        ("Cabrillo 1-ph Rate R_ent (L)", C_PURP),
        ("Barrett-Kok Fidelity F_ent (R)", C_GREEN),
        ("Cabrillo 1-ph Fidelity F_ent (R)", C_AMBER),
    ]
    for idx, (lbl, col) in enumerate(legs):
        row, col_i = idx // 2, idx % 2
        lx = px + col_i * 440
        ly = py + ph + 66 + row * 22
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx, ly - 9, 14, 10); ctx.fill()
        draw_text(ctx, lbl, lx + 20, ly, size=11.5, color=TEXT, bold=(idx in (0, 2)))


def draw_panel_d(ctx: cairo.Context, d: dict[str, Any], cx: float, cy: float, cw: float, ch: float) -> None:
    pd = d["panel_d_sb121"]
    badge = f"Sb NMR sep: {pd['min_nmr_spacing_kHz']:.0f} kHz | OQ6: Strain Wall"
    draw_card(ctx, cx, cy, cw, ch, "D. S1-Multi Heavy-Ion ZBL-BCA Straggle & 121Sb I=7/2 Qudit Strain Wall", badge, C_AMBER)

    gap_m = 74
    sub_w = (cw - 140 - gap_m) / 2.0
    py, ph = cy + 78, ch - 172

    # --- Left sub-plot: ZBL-BCA R_p & sigma_lat bars ---
    lx = cx + 76
    bars = pd["bca_bars"]
    y_max_l = 14.0

    def ym_l(v: float) -> float:
        return py + ph * (1.0 - v / y_max_l)

    for nm in [0, 2, 4, 6, 8, 10, 12, 14]:
        yy = ym_l(float(nm))
        ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
        ctx.move_to(lx, yy); ctx.line_to(lx + sub_w, yy); ctx.stroke()
        draw_text(ctx, f"{nm}", lx - 8, yy + 4.0, size=11.2, color=MUTED, align="right")

    draw_frame(ctx, lx, py, sub_w, ph)
    draw_rot_text(ctx, "Depth R_p & Lateral sigma_lat (nm)", cx + 22, py + ph / 2.0, size=12.5, color=TEXT, bold=True)
    draw_text(ctx, "ZBL-BCA Implantation Species (N=4,000)", lx + sub_w / 2.0, py + ph + 44, size=12.0, color=TEXT, bold=True, align="center")

    gw = sub_w / len(bars)
    bw = gw * 0.34
    for i, b in enumerate(bars):
        x0 = lx + i * gw + gw * 0.16
        # R_p bar
        y_rp = ym_l(b["R_p"])
        ctx.set_source_rgb(*C_BLUE)
        ctx.rectangle(x0, y_rp, bw - 2, (py + ph) - y_rp); ctx.fill()
        draw_text(ctx, f"{b['R_p']:.1f}", x0 + bw / 2.0 - 1, y_rp - 5, size=10.5, color=C_BLUE, bold=True, align="center")
        # sigma_lat bar
        y_sl = ym_l(b["sigma_lat"])
        ctx.set_source_rgb(*C_GREEN)
        ctx.rectangle(x0 + bw + 2, y_sl, bw - 2, (py + ph) - y_sl); ctx.fill()
        draw_text(ctx, f"{b['sigma_lat']:.2f}", x0 + 1.5 * bw + 1, y_sl - 5, size=10.5, color=C_GREEN, bold=True, align="center")
        draw_text(ctx, b["label"], lx + (i + 0.5) * gw, py + ph + 20, size=10.5, color=TEXT, bold=True, align="center")

    # Left legend
    ctx.set_source_rgb(*C_BLUE); ctx.rectangle(lx, py + ph + 62, 13, 10); ctx.fill()
    draw_text(ctx, "Projected Depth R_p (nm)", lx + 18, py + ph + 71, size=11.0, color=TEXT)
    ctx.set_source_rgb(*C_GREEN); ctx.rectangle(lx + 220, py + ph + 62, 13, 10); ctx.fill()
    draw_text(ctx, "Lateral Straggle sigma_lat", lx + 238, py + ph + 71, size=11.0, color=TEXT, bold=True)

    # --- Right sub-plot: 121Sb I=7/2 1 ms Fidelity under 500 Hz Quadrupole Strain Noise ---
    rx = lx + sub_w + gap_m
    encs = pd["sb_encodings"]

    def ym_r(f: float) -> float:
        return py + ph * (1.0 - (f - 0.40) / (1.05 - 0.40))

    for fv in [0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]:
        yy = ym_r(fv)
        ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
        ctx.move_to(rx, yy); ctx.line_to(rx + sub_w, yy); ctx.stroke()
        draw_text(ctx, f"{fv:.2f}", rx - 8, yy + 4.0, size=11.2, color=MUTED, align="right")

    draw_frame(ctx, rx, py, sub_w, ph)
    draw_rot_text(ctx, "121Sb Fidelity @ t=1 ms (500 Hz Strain)", rx - 46, py + ph / 2.0, size=12.2, color=TEXT, bold=True)
    draw_text(ctx, "121Sb I=7/2 Qudit Encoding (B0=1.5 T)", rx + sub_w / 2.0, py + ph + 44, size=12.0, color=TEXT, bold=True, align="center")

    e_cols = [C_GREEN, C_PURP, C_AMBER, C_RED]
    egw = sub_w / len(encs)
    ebw = egw * 0.56
    for i, e in enumerate(encs):
        bx = rx + i * egw + (egw - ebw) / 2.0
        by = ym_r(e["F_1ms"])
        ctx.set_source_rgb(*e_cols[i])
        ctx.rectangle(bx, by, ebw, (py + ph) - by); ctx.fill()
        draw_text(ctx, f"{e['F_1ms']:.3f}", bx + ebw / 2.0, by - 6, size=10.8, color=e_cols[i], bold=True, align="center")
        t2_lbl = f"T2*={e['T2_ms']:.1f}ms" if e["T2_ms"] >= 1.0 else f"T2*={e['T2_ms']*1e3:.0f}us"
        draw_text(ctx, t2_lbl, bx + ebw / 2.0, by - 21, size=9.8, color=MUTED, align="center")
        draw_text(ctx, e["label"], rx + (i + 0.5) * egw, py + ph + 20, size=10.2, color=TEXT, bold=(i == 0), align="center")

    draw_text(ctx, "I_z^2 strain kills Gross/Edge without echo; |+-1/2> clock is strain-immune", rx + sub_w / 2.0, py + ph + 71, size=10.5, color=C_RED, bold=True, align="center")


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    W, H = 2400, 1400
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H); ctx.fill()

    ctx.set_source_rgb(0.10, 0.16, 0.25)
    ctx.rectangle(0, 0, W, 86); ctx.fill()
    vc = data["verdict_counts"]
    draw_text(
        ctx,
        "Exp142 (H160): Option-Q 4-8 GHz Superconducting qRAM Bridge & S1-Multi Platform (167Er Telecom + 121Sb Qudit)",
        34, 38, size=24.0, color=(1.0, 1.0, 1.0), bold=True,
    )
    draw_text(
        ctx,
        f"50 <-> 3 kOhm ABCD  |  12x12 Lindblad CPTP SWAP  |  ZBL-BCA (N=4,000)  |  1536 nm Er Link  |  8x8 121Sb Qudit  |  Verdicts: {vc['passed']}/{vc['total']} PASS (no_lab_measurement=true)",
        34, 67, size=14.2, color=(0.82, 0.88, 0.96),
    )

    margin, gap = 26, 22
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
        "Atom Lithography Machine v6.0  |  Exp142 (H160)  |  S9.1 Option-Q + S1-Multi Spec Exported  |  Epistemic: {Literatur}/{Analitik}/{Model}/{Sayisal-Simulasyon}/{Varsayim}",
        W / 2.0, H - 10, size=12.0, color=MUTED, align="center",
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    surf.write_to_png(str(OUT_PNG))
    print(f"Generated {OUT_PNG} ({W}x{H})", flush=True)


if __name__ == "__main__":
    main()
