"""Pure-Cairo 2400x1400 IEEE/Nature Academic Publication Figure for Exp151 (H169): Master v7.2 Digital Twin.

Strict academic publication design system:
  - Canvas: #FFFFFF white paper (subtle note/table tint #F8F9FA)
  - Primary / Secondary ink: #111827 / #4B5563
  - Hairline borders & grids: #D1D5DB / #E5E7EB
  - Primary data accent: muted academic navy #1B365D
  - Secondary series: muted slate #64748B / #94A3B8 / #CBD5E1
  - Threshold / limit / uncertified accent: muted burgundy #8B2635 (sparingly)
  - Restrained PASS accent: muted forest #2D5A3D (text/markers only)

Runs under system Python (/usr/bin/python3 -B) using cairo + stdlib only (no numpy required).
Reads results/exp151_v7_digital_twin/exp151_plot_data.json and outputs:
    results/exp151_v7_digital_twin/fig_exp151_v7_digital_twin.png
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp151_v7_digital_twin"
DATA_PATH = OUT_DIR / "exp151_plot_data.json"
PNG_PATH = OUT_DIR / "fig_exp151_v7_digital_twin.png"

W, H = 2400, 1400

# Strict Academic Journal Palette (IEEE Transactions / Nature / Physical Review)
BG_PAPER = "#FFFFFF"
BG_SUBTLE = "#F8F9FA"
INK_PRIMARY = "#111827"
INK_SECONDARY = "#4B5563"
INK_MUTED = "#6B7280"
RULE_BORDER = "#D1D5DB"
RULE_GRID = "#E5E7EB"
ACCENT_NAVY = "#1B365D"
ACCENT_SLATE = "#64748B"
ACCENT_LIGHT_SLATE = "#94A3B8"
ACCENT_PALE_SLATE = "#CBD5E1"
ACCENT_BURGUNDY = "#8B2635"
ACCENT_FOREST = "#2D5A3D"


def _hex(h: str, a: float = 1.0) -> tuple[float, float, float, float]:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, a)


def _rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 2.0) -> None:
    r = min(r, w / 2.0, h / 2.0)
    if r <= 0.5:
        ctx.rectangle(x, y, w, h)
        return
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def draw_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 14.0,
    color: str = INK_PRIMARY,
    bold: bool = False,
    mono: bool = False,
    align: str = "left",
    max_w: float | None = None,
    min_size: float = 8.5,
) -> None:
    family = "DejaVu Sans Mono" if mono else "DejaVu Sans"
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(family, cairo.FONT_SLANT_NORMAL, weight)
    fsz = size
    ctx.set_font_size(fsz)
    if max_w is not None:
        while ctx.text_extents(text).width > max_w and fsz > min_size:
            fsz -= 0.3
            ctx.set_font_size(fsz)
    ext = ctx.text_extents(text)
    tx = x
    if align == "center":
        tx = x - (ext.width / 2.0 + ext.x_bearing)
    elif align == "right":
        tx = x - (ext.width + ext.x_bearing)
    ctx.set_source_rgba(*_hex(color))
    ctx.move_to(tx, y)
    ctx.show_text(text)


def draw_panel_frame(
    ctx: cairo.Context,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    title: str,
    tag: str,
) -> None:
    """Flat IEEE/Nature academic panel frame with hairline rule (zero shadow, zero colored bar)."""
    ctx.rectangle(x, y, w, h)
    ctx.set_source_rgba(*_hex(BG_PAPER))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.9)
    ctx.stroke()

    ctx.move_to(x + 18, y + 40)
    ctx.line_to(x + w - 18, y + 40)
    ctx.set_source_rgba(*_hex(RULE_GRID))
    ctx.set_line_width(0.9)
    ctx.stroke()

    draw_text(ctx, label, x + 18, y + 27, size=16.5, color=ACCENT_NAVY, bold=True)
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(16.5)
    lw = ctx.text_extents(label).width

    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(11.5)
    tw = ctx.text_extents(tag).width
    draw_text(ctx, tag, x + w - 18, y + 26, size=11.5, color=INK_SECONDARY, bold=True, mono=True, align="right")
    draw_text(ctx, title, x + 18 + lw + 10, y + 27, size=16.0, color=INK_PRIMARY, bold=True, max_w=(w - 46 - lw - tw))


def draw_axes_open(ctx: cairo.Context, px: float, py: float, pw: float, ph: float) -> None:
    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(1.0)
    ctx.move_to(px, py)
    ctx.line_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()


def draw_note_strip(
    ctx: cairo.Context,
    x: float,
    y: float,
    w: float,
    h: float,
    accent: str = ACCENT_NAVY,
) -> None:
    _rect(ctx, x, y, w, h, 2.0)
    ctx.set_source_rgba(*_hex(BG_SUBTLE))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.8)
    ctx.stroke()
    ctx.rectangle(x, y, 3.5, h)
    ctx.set_source_rgba(*_hex(accent))
    ctx.fill()


def main() -> None:
    d = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    l1, l2, l3, l4, l5, l6, l7 = d["l1"], d["l2"], d["l3"], d["l4"], d["l5"], d["l6"], d["l7"]
    cert = d["master_cert"]
    n_locked = cert["n_locked_artifacts"]

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgba(*_hex(BG_PAPER))
    ctx.paint()

    # --- ACADEMIC WHITE MASTHEAD WITH NAVY TOP RULE ---
    ctx.rectangle(0, 0, W, 5)
    ctx.set_source_rgba(*_hex(ACCENT_NAVY))
    ctx.fill()

    draw_text(
        ctx,
        "Atom Lithography Machine v7.2 — Integrated Artifact Summary & File-Integrity Manifest (Exp151 / H169)",
        36,
        42,
        size=22.5,
        color=INK_PRIMARY,
        bold=True,
        max_w=W - 560,
    )
    draw_text(
        ctx,
        "TRL 1–2 (M0) Multiphysics · Open-Source EDA RTL (Verilator/Icarus/Yosys) · 1% 29Si Lattice Bath · Uncertified M0 Safety · IBM QPU Control Proxy",
        36,
        69,
        size=12.6,
        color=INK_SECONDARY,
        max_w=W - 560,
    )

    # Restrained plain-bordered header stamps
    stamps = [
        (W - 498, 152, f"DT7: {d.get('n_passed', 8)}/{d.get('n_total', 8)} PASS", ACCENT_FOREST),
        (W - 334, 154, f"{n_locked}/{n_locked} SHA-256", ACCENT_NAVY),
        (W - 168, 132, "TRL 1–2 / M0", ACCENT_BURGUNDY),
    ]
    for sx, sw, stxt, scol in stamps:
        _rect(ctx, sx, 22, sw, 36, 2.0)
        ctx.set_source_rgba(*_hex(BG_SUBTLE))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(RULE_BORDER))
        ctx.set_line_width(0.9)
        ctx.stroke()
        draw_text(ctx, stxt, sx + sw / 2.0, 44.5, size=12.5, color=scol, bold=True, mono=True, align="center")

    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(1.5)
    ctx.move_to(36, 86)
    ctx.line_to(W - 36, 86)
    ctx.stroke()

    # 2x2 Academic Panel Grid
    c_w = 1152
    c_h1, c_h2 = 608, 616
    xL, xR = 36, 1212
    yT, yB = 104, 728

    # =========================================================================
    # PANEL (a) (Top-Left): v5 -> v7 Fleet & Universal Algorithm Compression
    # =========================================================================
    draw_panel_frame(ctx, xL, yT, c_w, c_h1, "(a)", "v5 → v7 Fleet & Universal Algorithm Cryostat Compression", "Exp144 + Exp147 (log10)")

    px, py, pw, ph = xL + 104, yT + 86, c_w - 138, 362
    lmin, lmax = math.log10(0.5), math.log10(35000.0)

    def y_log(val: float) -> float:
        lv = math.log10(max(val, 0.5))
        return py + ph * (1.0 - (lv - lmin) / (lmax - lmin))

    for tick in (1, 10, 100, 1000, 10000):
        yy = y_log(float(tick))
        ctx.save()
        ctx.set_dash([3.0, 3.0])
        ctx.set_source_rgba(*_hex(RULE_GRID))
        ctx.set_line_width(0.85)
        ctx.move_to(px, yy)
        ctx.line_to(px + pw, yy)
        ctx.stroke()
        ctx.restore()
        ctx.set_source_rgba(*_hex(INK_PRIMARY))
        ctx.set_line_width(0.9)
        ctx.move_to(px - 4.5, yy)
        ctx.line_to(px, yy)
        ctx.stroke()
        draw_text(ctx, f"{tick:,}", px - 10, yy + 4.5, size=12.0, color=INK_SECONDARY, mono=True, align="right")

    draw_axes_open(ctx, px, py, pw, ph)

    ctx.save()
    ctx.translate(xL + 28, py + ph / 2)
    ctx.rotate(-math.pi / 2)
    draw_text(ctx, "LD400 Cryostats (log10 scale)", 0, 0, size=13.0, color=INK_PRIMARY, bold=True, align="center")
    ctx.restore()

    # Compact legend top-left above bars
    ctx.rectangle(px + 12, py - 24, 13, 11)
    ctx.set_source_rgba(*_hex(ACCENT_PALE_SLATE))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(ACCENT_LIGHT_SLATE))
    ctx.set_line_width(0.7)
    ctx.stroke()
    draw_text(ctx, "Surface Code Baseline (D2 / D3)", px + 32, py - 14, size=11.8, color=INK_SECONDARY, bold=True)

    ctx.rectangle(px + 292, py - 24, 13, 11)
    ctx.set_source_rgba(*_hex(ACCENT_NAVY))
    ctx.fill()
    draw_text(ctx, "Bivariate Bicycle qLDPC (v6 / v7)", px + 312, py - 14, size=11.8, color=ACCENT_NAVY, bold=True)

    groups = [
        {
            "title": "100L Memory (Exp141/144)",
            "sub": "679× compression (1 LD400)",
            "bars": [
                ("v5 D2 SC", l7["fleet_100L_trajectory"]["v5_D2_SC_cryostats"], ACCENT_PALE_SLATE, ACCENT_LIGHT_SLATE),
                ("v6 D3 SC", l7["fleet_100L_trajectory"]["v6_D3_GRAPE_SC_cryostats"], ACCENT_LIGHT_SLATE, None),
                ("v6 qLDPC", l7["fleet_100L_trajectory"]["v6_qLDPC_108L_cryostats"], ACCENT_NAVY, None),
            ],
        },
        {
            "title": "FeMoco (192L, 10^8 T)",
            "sub": f"{l2['femoco']['cryo_compression_x']:.1f}× | {l2['femoco']['runtime_hours']:.2f} h | ${l2['femoco']['cost_per_solve_usd_p50']:,.0f}",
            "bars": [
                ("D3 SC", l2["femoco"]["sc_cryostats"], ACCENT_PALE_SLATE, ACCENT_LIGHT_SLATE),
                ("v7 qLDPC", l2["femoco"]["qldpc_cryostats"], ACCENT_NAVY, None),
            ],
        },
        {
            "title": "RSA-2048 (4096L, 10^10 T)",
            "sub": f"{l2['rsa2048']['cryo_compression_x']:.1f}× | {l2['rsa2048']['power_MW']:.2f} MW | {l2['rsa2048']['runtime_hours']:.1f} h",
            "bars": [
                ("D3 SC", l2["rsa2048"]["sc_cryostats"], ACCENT_PALE_SLATE, ACCENT_LIGHT_SLATE),
                ("v7 qLDPC", l2["rsa2048"]["qldpc_cryostats"], ACCENT_NAVY, None),
            ],
        },
    ]

    gx_centers = [px + pw * 0.20, px + pw * 0.54, px + pw * 0.84]
    for g, gcx in zip(groups, gx_centers):
        nb = len(g["bars"])
        bw = 62.0
        gap = 16.0
        total_bw = nb * bw + (nb - 1) * gap
        bx0 = gcx - total_bw / 2.0
        for i, (blbl, val, col, outline) in enumerate(g["bars"]):
            bx = bx0 + i * (bw + gap)
            by = y_log(float(val))
            bh = max((py + ph) - by, 8.0)
            ctx.rectangle(bx, by, bw, bh)
            ctx.set_source_rgba(*_hex(col, 0.95))
            if outline:
                ctx.fill_preserve()
                ctx.set_source_rgba(*_hex(outline))
                ctx.set_line_width(0.8)
                ctx.stroke()
            else:
                ctx.fill()
            draw_text(
                ctx,
                f"{val:,}",
                bx + bw / 2,
                by - 8,
                size=13.2,
                color=ACCENT_NAVY if col == ACCENT_NAVY else INK_PRIMARY,
                bold=True,
                mono=True,
                align="center",
            )
            draw_text(ctx, blbl, bx + bw / 2, py + ph + 20, size=12.0, color=INK_PRIMARY if col == ACCENT_NAVY else INK_SECONDARY, bold=(col == ACCENT_NAVY), align="center")
        draw_text(ctx, g["title"], gcx, py + ph + 44, size=13.8, color=INK_PRIMARY, bold=True, align="center")
        draw_text(ctx, g["sub"], gcx, py + ph + 64, size=12.0, color=ACCENT_NAVY, bold=True, mono=True, align="center")

    # Honest UQ5 + BB288 note strip (clean #F8F9FA + 3.5px burgundy rule)
    draw_note_strip(ctx, xL + 22, yT + c_h1 - 60, c_w - 44, 44, accent=ACCENT_BURGUNDY)
    draw_text(
        ctx,
        f"BB288 L_max={l2['L_max_um']} µm <= 300 | p_th={l2['p_th_72_vs_288_pct']}% | 576-cell yield {l2['yield_576_N8_pct']:.2f}% (N8) / {l2['yield_576_N9_pct']:.2f}% (N9) | Honest UQ5: 2–3 µs RO ceiling requires D3++ / d=24",
        xL + 36,
        yT + c_h1 - 34,
        size=12.2,
        color=INK_PRIMARY,
        bold=True,
        max_w=c_w - 72,
    )

    # =========================================================================
    # PANEL (b) (Top-Right): Exp148 121Sb Q-Echo-8 + Exp149 Real-EDA Verilog RTL
    # =========================================================================
    draw_panel_frame(ctx, xR, yT, c_w, c_h1, "(b)", "¹²¹Sb Q-Echo-8 (Model Iteration) & Real-EDA 584-Cycle RTL", "Exp148 + Exp149")

    draw_text(ctx, "Exp148: ¹²¹Sb (I=7/2) Static 500 Hz Quadrupole Model & SU(8) GRAPE", xR + 22, yT + 70, size=14.2, color=INK_PRIMARY, bold=True)
    sb_rows = [
        ("Bare Gross 0_L (Exp142 OQ6 Limit)", l3["bare_gross_0L_1ms"], ACCENT_BURGUNDY, 0.80, f"{l3['bare_gross_0L_1ms']:.4f}  (infid 42.0%)"),
        ("Q-Echo-8 Gross 0_L (Levitt-Freeman)", l3["qecho8_gross_0L_1ms"], ACCENT_NAVY, 0.95, f"{l3['qecho8_gross_0L_1ms']:.5f}  ({l3['gross_infidelity_reduction_x']:.0f}× drop)"),
        ("Q-Echo-8 |±7/2> Cat (0.9424 ->)", l3["qecho8_cat77_1ms"], ACCENT_SLATE, 0.90, f"{l3['qecho8_cat77_1ms']:.5f}  (model iter)"),
        ("SU(8) GRAPE Logical X_L/Z_L/H_L", l3["su8_grape_min_F"], ACCENT_NAVY, 0.72, f">= {l3['su8_grape_min_F']:.4f}  (22.9 kHz)"),
    ]
    bx_s = xR + 332
    bw_s = 524
    for i, (lbl, val, col, alpha, vtxt) in enumerate(sb_rows):
        ry = yT + 86 + i * 40
        draw_text(ctx, lbl, xR + 22, ry + 18, size=12.8, color=INK_PRIMARY if i != 0 else ACCENT_BURGUNDY, bold=(i in (0, 1)))
        ctx.rectangle(bx_s, ry + 4, bw_s, 20)
        ctx.set_source_rgba(*_hex(RULE_GRID))
        ctx.fill()
        ctx.rectangle(bx_s, ry + 4, bw_s * val, 20)
        ctx.set_source_rgba(*_hex(col, alpha))
        ctx.fill()
        draw_text(ctx, vtxt, bx_s + bw_s + 14, ry + 18, size=12.4, color=INK_PRIMARY if col != ACCENT_BURGUNDY else ACCENT_BURGUNDY, bold=True, mono=True)

    draw_text(
        ctx,
        f"Honest Cywinski 1/f boundary (SQ4 FAIL): single-cycle Q-Echo-8 = {l3['t2_gain_qecho8_1f_x']:.2f}×  |  multi-cycle Q-Echo-64 = {l3['t2_gain_qecho64_1f_x']:.2f}× ({l3['t2_qecho64_ms']:.2f} ms)",
        xR + 22,
        yT + 264,
        size=12.0,
        color=ACCENT_BURGUNDY,
        bold=True,
        max_w=c_w - 44,
    )

    # Hairline section divider
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.9)
    ctx.move_to(xR + 22, yT + 286)
    ctx.line_to(xR + c_w - 22, yT + 286)
    ctx.stroke()

    # Lower sub-section: Exp149 Real-EDA Verified Verilog RTL 584-cycle pipeline
    draw_text(
        ctx,
        f"Exp149: Open-Source EDA Verified Verilog RTL ({l4['total_rtl_loc']:,} LOC · Verilator 0 Warn · Icarus 64/64 + 4ch = 0 LSB)",
        xR + 22,
        yT + 318,
        size=14.0,
        color=INK_PRIMARY,
        bold=True,
        max_w=c_w - 44,
    )
    bar_x, bar_y, bar_w, bar_h = xR + 22, yT + 338, c_w - 44, 58
    phases = [
        ("S_PASS1: 263 cyc (1,052 ns)", 263, ACCENT_NAVY),
        ("S_PASS2: 265 cyc (1,060 ns)", 265, ACCENT_SLATE),
        ("POST: 56", 56, ACCENT_LIGHT_SLATE),
    ]
    cur_x = bar_x
    for plbl, cyc, col in phases:
        pw_seg = bar_w * (cyc / 584.0)
        ctx.rectangle(cur_x, bar_y, pw_seg - 3, bar_h)
        ctx.set_source_rgba(*_hex(col, 0.95))
        ctx.fill()
        draw_text(ctx, plbl, cur_x + (pw_seg - 3) / 2, bar_y + 34, size=13.0 if cyc > 80 else 11.2, color=BG_PAPER, bold=True, mono=True, align="center")
        cur_x += pw_seg

    # 3-column academic booktabs metric band for Real-EDA Yosys xcup_top16
    y16 = l4["yosys_measured_pre_pnr"]["targets"]["xcup_top16"]
    rtl_cols = [
        ("Real EDA (Icarus / Verilator)", f"{l4['boed_cycles_exact']} cyc = {l4['boed_latency_us_250MHz']:.3f} µs", "64/64 + 4-ch AXI4-S = 0 LSB · 0 '/' ops · 0 Warn"),
        ("Yosys xcup_top16 (Pre-P&R)", f"DSP {y16['dsp_total']:,} ({y16['zu48dr_pct']['dsp48e2_pct']}%)", f"LUT {y16['lut_total']:,} ({y16['zu48dr_pct']['lut_pct']}%) · FF {y16['ff_total']:,} · 96 BRAM36"),
        ("Multi-Target & Epistemic", "xcup / xc7 / ecp5 PASS", "no_external_eda_sim=false · no_vendor_vivado_pnr=true"),
    ]
    band_y, band_h = yT + 426, 152
    ctx.rectangle(xR + 22, band_y, c_w - 44, band_h)
    ctx.set_source_rgba(*_hex(BG_SUBTLE))
    ctx.fill()
    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(1.2)
    ctx.move_to(xR + 22, band_y)
    ctx.line_to(xR + c_w - 22, band_y)
    ctx.move_to(xR + 22, band_y + band_h)
    ctx.line_to(xR + c_w - 22, band_y + band_h)
    ctx.stroke()

    col_w = (c_w - 44) / 3.0
    for i, (t1, t2, t3) in enumerate(rtl_cols):
        rx = xR + 22 + i * col_w
        if i > 0:
            ctx.move_to(rx, band_y + 14)
            ctx.line_to(rx, band_y + band_h - 14)
            ctx.set_source_rgba(*_hex(RULE_BORDER))
            ctx.set_line_width(0.8)
            ctx.stroke()
        draw_text(ctx, t1, rx + 16, band_y + 34, size=12.4, color=INK_SECONDARY, bold=True, max_w=col_w - 28)
        draw_text(ctx, t2, rx + 16, band_y + 78, size=16.5, color=ACCENT_NAVY if i < 2 else ACCENT_FOREST, bold=True, mono=True, max_w=col_w - 28)
        draw_text(ctx, t3, rx + 16, band_y + 122, size=11.4, color=INK_SECONDARY, mono=True, max_w=col_w - 28)

    # =========================================================================
    # PANEL (c) (Bottom-Left): Exp150 Safety FMEA + IBM QPU Control Proxy
    # =========================================================================
    draw_panel_frame(ctx, xL, yB, c_w, c_h2, "(c)", "Preliminary M0 Safety FMEA Target & IBM QPU Control Proxy", "Exp150 + Exp145")

    draw_text(
        ctx,
        f"Exp150 (Uncertified M0): 25-Row FMEA + 10-Node HAZOP (Max RPN {l5['max_rpn_pre']} -> {l5['max_rpn_post']} <= 60, -{l5['mean_rpn_reduction_pct']:.1f}%)",
        xL + 22,
        yB + 70,
        size=13.8,
        color=INK_PRIMARY,
        bold=True,
        max_w=c_w - 44,
    )
    rpn_bars = [
        ("Max RPN Pre-Mitigation", float(l5["max_rpn_pre"]), ACCENT_PALE_SLATE, ACCENT_LIGHT_SLATE),
        ("Mean RPN Pre (25 rows)", 186.1, ACCENT_PALE_SLATE, ACCENT_LIGHT_SLATE),
        ("Max RPN Post (M0 Target)", float(l5["max_rpn_post"]), ACCENT_NAVY, None),
        ("Mean RPN Post (0 > 60)", 25.5, ACCENT_SLATE, None),
    ]
    rx_b = xL + 260
    rw_b = 768
    for i, (lbl, val, col, outline) in enumerate(rpn_bars):
        ry = yB + 88 + i * 36
        draw_text(ctx, lbl, xL + 22, ry + 17, size=12.6, color=INK_PRIMARY if i >= 2 else INK_SECONDARY, bold=(i >= 2))
        ctx.rectangle(rx_b, ry + 3, rw_b, 20)
        ctx.set_source_rgba(*_hex(RULE_GRID))
        ctx.fill()
        ctx.rectangle(rx_b, ry + 3, rw_b * (val / 300.0), 20)
        ctx.set_source_rgba(*_hex(col, 0.95))
        if outline:
            ctx.fill_preserve()
            ctx.set_source_rgba(*_hex(outline))
            ctx.set_line_width(0.8)
            ctx.stroke()
        else:
            ctx.fill()
        draw_text(
            ctx,
            f"{val:.1f}" if val % 1 else f"{int(val)}",
            rx_b + rw_b * (val / 300.0) + 10,
            ry + 17,
            size=12.6,
            color=ACCENT_NAVY if i >= 2 else INK_SECONDARY,
            bold=True,
            mono=True,
        )

    # Dashed threshold line at RPN = 60 (muted burgundy)
    tx60 = rx_b + rw_b * (60.0 / 300.0)
    ctx.save()
    ctx.set_source_rgba(*_hex(ACCENT_BURGUNDY))
    ctx.set_line_width(1.5)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(tx60, yB + 84)
    ctx.line_to(tx60, yB + 234)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "Limit RPN = 60", tx60 + 8, yB + 247, size=11.5, color=ACCENT_BURGUNDY, bold=True, mono=True)

    pfd_sw = l5["pfd_sensitivity_sweep"]
    haz_line = (
        f"OD={l5['laser_od_spec']}+3 mm steel ({l5['xray_22kev_shrouded_uSv_h']:.1e} µSv/h) | "
        f"1oo2D PFD {l5['pfd_avg_1oo2d_nominal']:.2e} (10×/β10% -> {pfd_sw['pfd_10x_lambda_du_beta10pct']:.2e} SIL-2) | "
        f"PH3 {l5['ph3_operator_ppm']:.4f} ppm | O2 {l5['he_60m3_O2_pct']:.2f}%"
    )
    draw_text(ctx, haz_line, xL + 22, yB + 278, size=11.8, color=INK_PRIMARY, bold=True, max_w=c_w - 44)
    draw_text(
        ctx,
        f"Uncertified M0 (iec61508=false, semi_s2=false): S7.SAFETY ${l5['s_safety_nom_usd']:,.0f} nom | {l5['s_safety_mass_kg']:.0f} kg | {l5['s_safety_power_W']:.0f} W | 0 W cryo",
        xL + 22,
        yB + 302,
        size=11.6,
        color=ACCENT_BURGUNDY,
        bold=True,
        mono=True,
        max_w=c_w - 44,
    )

    # Cloud Superconducting-QPU Proxy + 1% 29Si Bath Panel (clean flat academic container)
    qbox_y, qbox_h = yB + 324, 272
    _rect(ctx, xL + 22, qbox_y, c_w - 44, qbox_h, 2.0)
    ctx.set_source_rgba(*_hex(BG_SUBTLE))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.9)
    ctx.stroke()
    ctx.rectangle(xL + 22, qbox_y, 3.5, qbox_h)
    ctx.set_source_rgba(*_hex(ACCENT_NAVY))
    ctx.fill()

    lq = l6["live_ibm_qpu"]
    draw_text(
        ctx,
        f"CLOUD SUPERCONDUCTING-QPU CONTROL PROXY (Non-Silicon): {lq['backend_name']} ({lq['n_qubits']}Q · job={lq['job_id']})",
        xL + 40,
        qbox_y + 28,
        size=13.0,
        color=ACCENT_NAVY,
        bold=True,
        max_w=c_w - 84,
    )

    # Booktabs 4-column metric grid inside proxy box
    qpu_kpis = [
        ("C1 XY4 DD Gain", f"+{lq['c1_xy4_gain_pp']:.2f} pp", f"Bare {lq['c1_bare_p0']:.4f} -> XY4 {lq['c1_xy4_p0']:.4f}"),
        ("C1 Bell Fidelity", f"F = {lq['c1_bell_fidelity']:.4f}", "ZZ=+0.961 | XX=+0.972 | YY=-0.960"),
        ("C2 d=3 QEC (5Q)", f"{lq['c2_suppression_mwpm']:.2f}× / {lq['c2_suppression_majority']:.2f}×", "Post-sel 0.000% (0 / 7,451)"),
        ("C3 Q16.16 BOED", f"{lq['c3_q16_vs_fp64_kHz']*1000:.1f} Hz vs FP64", f"{lq['c3_q16_points_used']} pts | {lq['c3_q16_boed_kHz']:.3f} kHz"),
    ]
    grid_y, grid_h = qbox_y + 44, 130
    ctx.rectangle(xL + 40, grid_y, c_w - 80, grid_h)
    ctx.set_source_rgba(*_hex(BG_PAPER))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.8)
    ctx.stroke()

    qcol_w = (c_w - 80) / 4.0
    for i, (k1, k2, k3) in enumerate(qpu_kpis):
        qx = xL + 40 + i * qcol_w
        if i > 0:
            ctx.move_to(qx, grid_y + 10)
            ctx.line_to(qx, grid_y + grid_h - 10)
            ctx.set_source_rgba(*_hex(RULE_GRID))
            ctx.set_line_width(0.8)
            ctx.stroke()
        draw_text(ctx, k1, qx + 14, grid_y + 28, size=11.8, color=INK_SECONDARY, bold=True, max_w=qcol_w - 24)
        draw_text(ctx, k2, qx + 14, grid_y + 68, size=16.5, color=ACCENT_NAVY, bold=True, mono=True, max_w=qcol_w - 24)
        draw_text(ctx, k3, qx + 14, grid_y + 106, size=10.8, color=INK_SECONDARY, max_w=qcol_w - 24)

    bath = l6["real_si29_bath_boed"]
    rec = l6["live_auto_recal"]
    draw_text(
        ctx,
        f"1% 29Si Lattice-Bath BOED: {bath['boed_identification_accuracy']*100:.2f}% acc ({bath['probe_speedup_vs_uniform_raw']:.2f}× probe, A_par RMSE {bath['boed_a_par_rmse_Hz']:.1f} Hz)",
        xL + 40,
        qbox_y + 208,
        size=12.0,
        color=INK_PRIMARY,
        bold=True,
        mono=True,
        max_w=c_w - 84,
    )
    draw_text(
        ctx,
        f"Physical auto_recal (4/4 PASS): honest step-and-stitch {rec['blanker_step_and_stitch']['throughput_after_recal_pct']:.2f}% throughput (100% coverage) | Does NOT validate Si fab",
        xL + 40,
        qbox_y + 238,
        size=11.4,
        color=INK_SECONDARY,
        mono=True,
        max_w=c_w - 84,
    )

    # =========================================================================
    # PANEL (d) (Bottom-Right): BOM v7.0 Parametric Tiers & 39/39 SHA-256 Manifest
    # =========================================================================
    draw_panel_frame(ctx, xR, yB, c_w, c_h2, "(d)", "Parametric BOM v7.0 & Artifact File-Integrity Manifest", "Exp128 v7.0 + SHA-256")

    draw_text(
        ctx,
        "100k Monte Carlo Exceedance P(Program > $100M) vs. 5.0% Policy Cap (Exp128 v7.0)",
        xR + 22,
        yB + 70,
        size=14.0,
        color=INK_PRIMARY,
        bold=True,
    )
    mt = l7["modular_tiers_v7"]
    tiers = [
        ("M3 v5 Base ($5.248M, 167p)", mt["M3_v5_0_Base"]["P_gt_100M_pct"], ACCENT_SLATE, ACCENT_FOREST, "PASS (< 5%)"),
        ("Phase-1: Base+Safety ($5.393M, 173p)", mt["M3_Phase1_Base_Plus_Safety"]["P_gt_100M_pct"], ACCENT_NAVY, ACCENT_NAVY, "RECOMMENDED PHASE-1 (6/6 CU)"),
        ("M3 v6 Full (+Q+HPC, $5.548M, 174p)", mt["M3_v6_0_Full"]["P_gt_100M_pct"], ACCENT_SLATE, ACCENT_FOREST, "PASS (< 5%)"),
        ("M3 v7 Full (+Safety+Q+HPC, $5.693M)", mt["M3_v7_0_Full"]["P_gt_100M_pct"], ACCENT_BURGUNDY, ACCENT_BURGUNDY, "HONEST >5% -> PHASE-2"),
    ]
    tx_b = xR + 346
    tw_b = 452
    max_p = 6.5
    for i, (lbl, pct, col, note_col, note) in enumerate(tiers):
        ry = yB + 90 + i * 50
        draw_text(ctx, lbl, xR + 22, ry + 20, size=12.8, color=INK_PRIMARY if i in (1, 3) else INK_SECONDARY, bold=(i in (1, 3)))
        ctx.rectangle(tx_b, ry + 4, tw_b, 24)
        ctx.set_source_rgba(*_hex(RULE_GRID))
        ctx.fill()
        fw = tw_b * (pct / max_p)
        ctx.rectangle(tx_b, ry + 4, fw, 24)
        ctx.set_source_rgba(*_hex(col, 0.92))
        ctx.fill()
        draw_text(ctx, f"{pct:.2f}%", tx_b + fw - 8, ry + 20.5, size=12.4, color=BG_PAPER, bold=True, mono=True, align="right")
        draw_text(ctx, note, tx_b + tw_b + 14, ry + 20, size=12.0, color=note_col, bold=True, max_w=(xR + c_w - (tx_b + tw_b + 26)))

    # 5.0% policy cap vertical dashed line (muted burgundy)
    cap_x = tx_b + tw_b * (5.0 / max_p)
    ctx.save()
    ctx.set_source_rgba(*_hex(ACCENT_BURGUNDY))
    ctx.set_line_width(1.6)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(cap_x, yB + 86)
    ctx.line_to(cap_x, yB + 292)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "5.0% Hard Cap", cap_x, yB + 308, size=11.8, color=ACCENT_BURGUNDY, bold=True, mono=True, align="center")

    # Booktabs Artifact File-Integrity Manifest Table (39/39 Lock)
    tb_x, tb_y, tb_w = xR + 22, yB + 328, c_w - 44
    # Header tint
    ctx.rectangle(tb_x, tb_y, tb_w, 32)
    ctx.set_source_rgba(*_hex(BG_SUBTLE))
    ctx.fill()
    # Top booktabs heavy rule
    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(1.3)
    ctx.move_to(tb_x, tb_y)
    ctx.line_to(tb_x + tb_w, tb_y)
    ctx.stroke()
    # Midrule below table header
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.9)
    ctx.move_to(tb_x, tb_y + 32)
    ctx.line_to(tb_x + tb_w, tb_y + 32)
    ctx.stroke()

    draw_text(ctx, f"Table 1 — Artifact File-Integrity Manifest ({n_locked}/{n_locked} SHA-256 · Provenance Only)", tb_x + 10, tb_y + 21, size=12.6, color=ACCENT_NAVY, bold=True)
    draw_text(ctx, "Scope / Locked Invariants", tb_x + tb_w - 10, tb_y + 21, size=11.2, color=INK_SECONDARY, bold=True, align="right")

    html_bytes = (ROOT / "docs/digital_twin_interactive.html").stat().st_size
    html_kb = html_bytes / 1000.0
    table_rows = [
        ("Experiment Ledgers", "27 JSONs (Exp124..150) + IBM proxy counts + 1% 29Si lattice-bath BOED JSON"),
        ("CAD v6.0 Nominal", f"{l1['cad_v6']['part_count']} parts | {l1['cad_v6']['total_mass_kg']:.1f} kg on-frame | 0/19,701 static clashes (excl. GD&T/thermal/DFM)"),
        ("BOM v7.0 Parametric", f"{l1['bom_v7']['exp128_total_parts']} parts (no quotes) | $0.00 bridge | +355.0 kg fac. = {l1['bom_v7']['total_facility_load_mass_kg']:.1f} kg total"),
        ("10-RFQ Draft Scope", f"{l1['bom_v7']['rfq10_nom_share_pct']:.2f}% nominal / {l1['bom_v7']['rfq10_var_share_pct']:.2f}% MC variance (Phase-1 -> RFQ-05 -> Phase-2)"),
        ("Real-EDA RTL + HTML", f"7 rtl/boed_fpga/ (no_external_eda_sim=false; Yosys pre-P&R) + HTML5 ({html_kb:.1f} KB, 0 CDN)"),
        ("Historical Manifests", "v4 (feffc1d4..), v5 (2828e8ce..), v6 (ca3f0e02..) strictly untouched on disk"),
    ]
    row_h = 38.0
    for i, (k_col, v_col) in enumerate(table_rows):
        ry = tb_y + 32 + i * row_h
        if i % 2 == 1:
            ctx.rectangle(tb_x, ry, tb_w, row_h)
            ctx.set_source_rgba(*_hex(BG_SUBTLE, 0.55))
            ctx.fill()
        if i > 0:
            ctx.move_to(tb_x, ry)
            ctx.line_to(tb_x + tb_w, ry)
            ctx.set_source_rgba(*_hex(RULE_GRID))
            ctx.set_line_width(0.7)
            ctx.stroke()
        draw_text(ctx, k_col, tb_x + 10, ry + 24, size=12.0, color=INK_PRIMARY, bold=True)
        draw_text(ctx, v_col, tb_x + 210, ry + 24, size=11.8, color=INK_SECONDARY, max_w=tb_w - 220)

    # Bottom booktabs heavy rule
    tb_bot = tb_y + 32 + len(table_rows) * row_h
    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(1.3)
    ctx.move_to(tb_x, tb_bot)
    ctx.line_to(tb_x + tb_w, tb_bot)
    ctx.stroke()

    # --- CLEAN WHITE PAPER FOOTER WITH FULL 64-HEX SHA-256 ---
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.9)
    ctx.move_to(36, H - 38)
    ctx.line_to(W - 36, H - 38)
    ctx.stroke()
    draw_text(
        ctx,
        f"FILE-INTEGRITY SHA-256 ({n_locked}/{n_locked}, Provenance Only): {cert['sha256']}",
        36,
        H - 15,
        size=11.4,
        color=INK_PRIMARY,
        bold=True,
        mono=True,
    )
    draw_text(
        ctx,
        "TRL 1–2 (M0) · no_lab_measurement=true · no_vendor_vivado_pnr=true · IBM 156Q Proxy (Non-Silicon)",
        W - 36,
        H - 15,
        size=10.8,
        color=INK_MUTED,
        mono=True,
        align="right",
    )

    surf.write_to_png(str(PNG_PATH))
    print(f"Wrote {PNG_PATH} ({PNG_PATH.stat().st_size:,} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
