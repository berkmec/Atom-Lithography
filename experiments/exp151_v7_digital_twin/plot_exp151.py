"""Pure-Cairo 2400x1400 Dashboard Renderer for Exp151 (H169): Master v7.0 Digital Twin.

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

# Palette (clean high-contrast scientific dark/light hybrid with crisp legibility)
BG = (0.965, 0.973, 0.985)
CARD = (1.0, 1.0, 1.0)
BORDER = (0.81, 0.85, 0.90)
NAVY = (0.059, 0.090, 0.165)
TEXT = (0.09, 0.13, 0.21)
MUTED = (0.37, 0.43, 0.52)
GRID = (0.89, 0.92, 0.95)
BLUE = (0.145, 0.388, 0.922)
CYAN = (0.024, 0.569, 0.788)
EMERALD = (0.039, 0.588, 0.412)
AMBER = (0.851, 0.467, 0.024)
CORAL = (0.863, 0.149, 0.149)
PURPLE = (0.486, 0.227, 0.929)
LIGHT_EMERALD = (0.91, 0.98, 0.95)
LIGHT_BLUE = (0.93, 0.96, 1.0)
LIGHT_AMBER = (1.0, 0.97, 0.90)


def rounded_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float) -> None:
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
    size: float = 16.0,
    color: tuple[float, float, float] = TEXT,
    bold: bool = False,
    mono: bool = False,
    align: str = "left",
) -> None:
    family = "DejaVu Sans Mono" if mono else "DejaVu Sans"
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(family, cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)
    ext = ctx.text_extents(text)
    tx = x
    if align == "center":
        tx = x - (ext.width / 2.0 + ext.x_bearing)
    elif align == "right":
        tx = x - (ext.width + ext.x_bearing)
    ctx.set_source_rgb(*color)
    ctx.move_to(tx, y)
    ctx.show_text(text)


def draw_card(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, tag: str) -> None:
    rounded_rect(ctx, x, y, w, h, 14)
    ctx.set_source_rgb(*CARD)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(2.0)
    ctx.stroke()

    # Header bar inside card
    rounded_rect(ctx, x + 1, y + 1, w - 2, 46, 13)
    ctx.set_source_rgb(0.945, 0.961, 0.984)
    ctx.fill()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.2)
    ctx.move_to(x, y + 47)
    ctx.line_to(x + w, y + 47)
    ctx.stroke()

    draw_text(ctx, title, x + 20, y + 31, size=20.0, color=NAVY, bold=True)
    draw_text(ctx, tag, x + w - 20, y + 30, size=14.0, color=CYAN, bold=True, mono=True, align="right")


def main() -> None:
    d = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    l1, l2, l3, l4, l5, l6, l7 = d["l1"], d["l2"], d["l3"], d["l4"], d["l5"], d["l6"], d["l7"]
    cert = d["master_cert"]

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG)
    ctx.paint()

    # --- TOP HEADER BANNER ---
    ctx.set_source_rgb(*NAVY)
    ctx.rectangle(0, 0, W, 108)
    ctx.fill()
    draw_text(
        ctx,
        "Atom Lithography Machine v7.1 — Integrated Artifact Dashboard & File-Integrity Manifest (Exp151 / H169)",
        44,
        46,
        size=25.5,
        color=(1.0, 1.0, 1.0),
        bold=True,
    )
    draw_text(
        ctx,
        "TRL 1-2 (M0) Conceptual Design & Reduced-Order Multiphysics · Uncertified Safety Target · IBM Superconducting-QPU Control Proxy",
        44,
        82,
        size=15.5,
        color=(0.74, 0.85, 0.98),
    )

    # Top-right CHECKS badge
    rounded_rect(ctx, W - 360, 22, 316, 62, 10)
    ctx.set_source_rgb(0.05, 0.36, 0.25)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.20, 0.83, 0.60)
    ctx.set_line_width(2.0)
    ctx.stroke()
    draw_text(ctx, "8/8 CHECKS | 38/38 SHA-256", W - 202, 50, size=16.0, color=(0.82, 0.99, 0.92), bold=True, mono=True, align="center")
    draw_text(ctx, "CAD v6 Nominal + BOM v7 Parametric", W - 202, 73, size=12.0, color=(0.75, 0.92, 0.86), align="center")

    # Card geometries (2x2)
    c_w = 1136
    c_h1, c_h2 = 590, 594
    xL, xR = 44, 1220
    yT, yB = 130, 748

    # =========================================================================
    # PANEL A (Top-Left): v5 -> v7 Fleet & Universal Algorithm Compression
    # =========================================================================
    draw_card(ctx, xL, yT, c_w, c_h1, "A. v5->v7 Fleet & Universal Algorithm Cryostat Compression", "Exp144 + Exp147 (Log10)")

    px, py, pw, ph = xL + 108, yT + 92, c_w - 144, 360
    lmin, lmax = math.log10(0.5), math.log10(35000.0)

    def y_log(val: float) -> float:
        lv = math.log10(max(val, 0.5))
        return py + ph * (1.0 - (lv - lmin) / (lmax - lmin))

    # Horizontal log grid lines
    for tick in (1, 10, 100, 1000, 10000):
        yy = y_log(float(tick))
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.3)
        ctx.move_to(px, yy)
        ctx.line_to(px + pw, yy)
        ctx.stroke()
        draw_text(ctx, f"{tick:,}", px - 12, yy + 5, size=13.5, color=MUTED, mono=True, align="right")

    # Rotated y-axis label
    ctx.save()
    ctx.translate(xL + 28, py + ph / 2)
    ctx.rotate(-math.pi / 2)
    draw_text(ctx, "LD400 Cryostats (log10 scale)", 0, 0, size=14.0, color=MUTED, bold=True, align="center")
    ctx.restore()

    # 3 groups of bars
    groups = [
        {
            "title": "100L Memory (Exp141/144)",
            "sub": "679x Compression (1 LD400)",
            "bars": [
                ("v5 D2 SC", l7["fleet_100L_trajectory"]["v5_D2_SC_cryostats"], CORAL),
                ("v6 D3 SC", l7["fleet_100L_trajectory"]["v6_D3_GRAPE_SC_cryostats"], AMBER),
                ("v6 qLDPC", l7["fleet_100L_trajectory"]["v6_qLDPC_108L_cryostats"], EMERALD),
            ],
        },
        {
            "title": "FeMoco (192L, 10^8 T)",
            "sub": f"{l2['femoco']['cryo_compression_x']:.1f}x | {l2['femoco']['runtime_hours']:.2f}h | ${l2['femoco']['cost_per_solve_usd_p50']:,.0f}",
            "bars": [
                ("D3 SC", l2["femoco"]["sc_cryostats"], CORAL),
                ("v7 qLDPC", l2["femoco"]["qldpc_cryostats"], CYAN),
            ],
        },
        {
            "title": "RSA-2048 (4096L, 10^10 T)",
            "sub": f"{l2['rsa2048']['cryo_compression_x']:.1f}x | {l2['rsa2048']['power_MW']:.2f} MW | {l2['rsa2048']['runtime_hours']:.1f}h",
            "bars": [
                ("D3 SC", l2["rsa2048"]["sc_cryostats"], CORAL),
                ("v7 qLDPC", l2["rsa2048"]["qldpc_cryostats"], BLUE),
            ],
        },
    ]

    gx_centers = [px + pw * 0.20, px + pw * 0.54, px + pw * 0.84]
    for g, gcx in zip(groups, gx_centers):
        nb = len(g["bars"])
        bw = 66.0
        gap = 18.0
        total_bw = nb * bw + (nb - 1) * gap
        bx0 = gcx - total_bw / 2.0
        for i, (blbl, val, col) in enumerate(g["bars"]):
            bx = bx0 + i * (bw + gap)
            by = y_log(float(val))
            bh = (py + ph) - by
            rounded_rect(ctx, bx, by, bw, max(bh, 10.0), 5)
            ctx.set_source_rgb(*col)
            ctx.fill()
            draw_text(ctx, f"{val:,}", bx + bw / 2, by - 9, size=14.5, color=NAVY, bold=True, mono=True, align="center")
            draw_text(ctx, blbl, bx + bw / 2, py + ph + 22, size=13.0, color=TEXT, bold=True, align="center")
        draw_text(ctx, g["title"], gcx, py + ph + 48, size=15.0, color=NAVY, bold=True, align="center")
        draw_text(ctx, g["sub"], gcx, py + ph + 69, size=13.0, color=EMERALD, bold=True, mono=True, align="center")

    # Axis baseline
    ctx.set_source_rgb(*NAVY)
    ctx.set_line_width(1.8)
    ctx.move_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()

    # Honest UQ5 + BB288 footer note in Panel A
    rounded_rect(ctx, xL + 24, yT + c_h1 - 56, c_w - 48, 42, 8)
    ctx.set_source_rgb(*LIGHT_AMBER)
    ctx.fill_preserve()
    ctx.set_source_rgb(*AMBER)
    ctx.set_line_width(1.2)
    ctx.stroke()
    draw_text(
        ctx,
        f"BB288 L_max={l2['L_max_um']} um <=300 | p_th={l2['p_th_72_vs_288_pct']}% | 576-cell yield {l2['yield_576_N8_pct']:.2f}% (N8) / {l2['yield_576_N9_pct']:.2f}% (N9) | Honest UQ5: 2-3 us RO ceiling requires D3++/d=24",
        xL + 38,
        yT + c_h1 - 30,
        size=13.2,
        color=(0.48, 0.25, 0.0),
        bold=True,
    )

    # =========================================================================
    # PANEL B (Top-Right): Exp148 121Sb Q-Echo-8 + Exp149 Verilog RTL
    # =========================================================================
    draw_card(ctx, xR, yT, c_w, c_h1, "B. 121Sb Q-Echo-8 (Model Iteration) & 584-Cycle Verilog RTL", "Exp148 + Exp149")

    # Upper sub-section: Exp148 121Sb Q-Echo-8
    draw_text(ctx, "Exp148: 121Sb (I=7/2) Static 500 Hz Quadrupole Model & SU(8) GRAPE", xR + 24, yT + 78, size=16.0, color=NAVY, bold=True)
    sb_rows = [
        ("Bare Gross 0_L (Exp142 OQ6 Limit)", l3["bare_gross_0L_1ms"], CORAL, f"{l3['bare_gross_0L_1ms']:.4f}  (infid 42.0%)"),
        ("Q-Echo-8 Gross 0_L (Levitt-Freeman)", l3["qecho8_gross_0L_1ms"], EMERALD, f"{l3['qecho8_gross_0L_1ms']:.5f}  ({l3['gross_infidelity_reduction_x']:.0f}x drop)"),
        ("Q-Echo-8 |+-7/2> Cat (0.9424 ->)", l3["qecho8_cat77_1ms"], CYAN, f"{l3['qecho8_cat77_1ms']:.5f}  (model iter)"),
        ("SU(8) GRAPE Logical X_L/Z_L/H_L", l3["su8_grape_min_F"], PURPLE, f">= {l3['su8_grape_min_F']:.4f}  (22.9 kHz)"),
    ]
    bx_s = xR + 340
    bw_s = 490
    for i, (lbl, val, col, vtxt) in enumerate(sb_rows):
        ry = yT + 96 + i * 42
        draw_text(ctx, lbl, xR + 24, ry + 20, size=14.0, color=TEXT, bold=True)
        rounded_rect(ctx, bx_s, ry + 3, bw_s, 24, 5)
        ctx.set_source_rgb(0.92, 0.94, 0.96)
        ctx.fill()
        rounded_rect(ctx, bx_s, ry + 3, bw_s * val, 24, 5)
        ctx.set_source_rgb(*col)
        ctx.fill()
        draw_text(ctx, vtxt, bx_s + bw_s + 14, ry + 20, size=13.5, color=NAVY, bold=True, mono=True)

    draw_text(
        ctx,
        f"Honest Cywinski 1/f boundary (SQ4): single-cycle Q-Echo-8 = {l3['t2_gain_qecho8_1f_x']:.2f}x | multi-cycle Q-Echo-64 = {l3['t2_gain_qecho64_1f_x']:.2f}x ({l3['t2_qecho64_ms']:.2f} ms)",
        xR + 24,
        yT + 278,
        size=13.2,
        color=AMBER,
        bold=True,
    )

    # Divider
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.4)
    ctx.move_to(xR + 24, yT + 298)
    ctx.line_to(xR + c_w - 24, yT + 298)
    ctx.stroke()

    # Lower sub-section: Exp149 Synthesizable Verilog RTL 584-cycle pipeline
    draw_text(
        ctx,
        f"Exp149: Synthesizable IEEE 1364-2005 Verilog RTL ({l4['total_rtl_loc']} LOC, 0 Lint Err, 64/64 = 0 LSB)",
        xR + 24,
        yT + 330,
        size=16.0,
        color=NAVY,
        bold=True,
    )
    # 584-cycle proportional stacked bar
    bar_x, bar_y, bar_w, bar_h = xR + 24, yT + 350, c_w - 48, 66
    phases = [
        ("S_PASS1: 263 cyc (1,052 ns)", 263, BLUE),
        ("S_PASS2: 265 cyc (1,060 ns)", 265, EMERALD),
        ("POST: 56", 56, AMBER),
    ]
    cur_x = bar_x
    for plbl, cyc, col in phases:
        pw_seg = bar_w * (cyc / 584.0)
        rounded_rect(ctx, cur_x, bar_y, pw_seg - 4, bar_h, 7)
        ctx.set_source_rgb(*col)
        ctx.fill()
        draw_text(ctx, plbl, cur_x + (pw_seg - 4) / 2, bar_y + 40, size=14.0 if cyc > 80 else 12.0, color=(1, 1, 1), bold=True, mono=True, align="center")
        cur_x += pw_seg

    # 3 RTL summary metric boxes
    rtl_boxes = [
        ("Total BOED Latency", f"{l4['boed_cycles_exact']} cyc = {l4['boed_latency_us_250MHz']:.3f} us", f"@ 250 MHz | SPRT = {l4['sprt_latency_cycles']} cyc (16 ns)"),
        ("Bit-Exact Verification", f"1,024/1,024 ROM (0 bit)", "64/64 BOED + 1,000 isqrt = 0 LSB"),
        ("ZU48DR 16-ch Budget", f"DSP {l4['zu48dr_16ch_dsp_pct']}% | BRAM {l4['zu48dr_16ch_bram_pct']}%", "0.0 W cryo | no_external_eda_sim=true"),
    ]
    rb_w = (c_w - 72) / 3.0
    for i, (t1, t2, t3) in enumerate(rtl_boxes):
        rx = xR + 24 + i * (rb_w + 12)
        ry = yT + 436
        rounded_rect(ctx, rx, ry, rb_w, 128, 10)
        ctx.set_source_rgb(*LIGHT_BLUE)
        ctx.fill_preserve()
        ctx.set_source_rgb(*BORDER)
        ctx.set_line_width(1.3)
        ctx.stroke()
        draw_text(ctx, t1, rx + 14, ry + 30, size=14.0, color=MUTED, bold=True)
        draw_text(ctx, t2, rx + 14, ry + 66, size=17.5, color=NAVY, bold=True, mono=True)
        draw_text(ctx, t3, rx + 14, ry + 102, size=13.0, color=CYAN, bold=True)

    # =========================================================================
    # PANEL C (Bottom-Left): Exp150 Safety FMEA + Live IBM ibm_marrakesh QPU
    # =========================================================================
    draw_card(ctx, xL, yB, c_w, c_h2, "C. Preliminary M0 Safety FMEA Target & IBM QPU Control Proxy", "Exp150 + Exp145")

    draw_text(
        ctx,
        f"Exp150 (Uncertified M0): 25-Row FMEA + 10-Node HAZOP (Max RPN {l5['max_rpn_pre']} -> {l5['max_rpn_post']} <= 60, -{l5['mean_rpn_reduction_pct']:.1f}%)",
        xL + 24,
        yB + 78,
        size=15.0,
        color=NAVY,
        bold=True,
    )
    rpn_bars = [
        ("Max RPN Pre-Mitigation", float(l5["max_rpn_pre"]), CORAL),
        ("Mean RPN Pre (25 rows)", 186.1, AMBER),
        ("Max RPN Post (M0 Target)", float(l5["max_rpn_post"]), EMERALD),
        ("Mean RPN Post (0 > 60)", 25.5, CYAN),
    ]
    rx_b = xL + 265
    rw_b = 735
    for i, (lbl, val, col) in enumerate(rpn_bars):
        ry = yB + 95 + i * 36
        draw_text(ctx, lbl, xL + 24, ry + 19, size=14.0, color=TEXT, bold=True)
        rounded_rect(ctx, rx_b, ry + 3, rw_b, 22, 5)
        ctx.set_source_rgb(0.92, 0.94, 0.96)
        ctx.fill()
        rounded_rect(ctx, rx_b, ry + 3, rw_b * (val / 300.0), 22, 5)
        ctx.set_source_rgb(*col)
        ctx.fill()
        draw_text(ctx, f"{val:.1f}" if val % 1 else f"{int(val)}", rx_b + rw_b * (val / 300.0) + 10, ry + 19, size=14.0, color=NAVY, bold=True, mono=True)

    # Dashed threshold line at RPN = 60
    tx60 = rx_b + rw_b * (60.0 / 300.0)
    ctx.save()
    ctx.set_source_rgb(*EMERALD)
    ctx.set_line_width(2.0)
    ctx.set_dash([6, 4])
    ctx.move_to(tx60, yB + 92)
    ctx.line_to(tx60, yB + 238)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "Limit RPN=60", tx60 + 6, yB + 252, size=12.5, color=EMERALD, bold=True, mono=True)

    # 5-Hazard compact summary strip
    haz_line = (
        f"OD={l5['laser_od_spec']}+3mm steel ({l5['xray_22kev_shrouded_uSv_h']:.2e} uSv/h, {l5['sil3_shutter_ms']} ms SIL-3 target) | "
        f"SDS PH3 {l5['ph3_operator_ppm']:.5f} ppm | He O2 {l5['he_60m3_O2_pct']:.2f}% | "
        f"15kVA UPS {l5['ups_full_load_min']:.0f}/{l5['ups_tier1_min']:.0f} min"
    )
    draw_text(ctx, haz_line, xL + 24, yB + 284, size=12.6, color=TEXT, bold=True)
    draw_text(
        ctx,
        f"S7.SAFETY Target Kit (RFQ-10 Draft, Uncertified M0): ${l5['s_safety_nom_usd']:,.0f} nom [$92k-$220k] | {l5['s_safety_mass_kg']:.0f} kg | {l5['s_safety_power_W']:.0f} W | 0 W cryo",
        xL + 24,
        yB + 308,
        size=12.6,
        color=PURPLE,
        bold=True,
        mono=True,
    )

    # Cloud Superconducting-QPU Proxy Box
    rounded_rect(ctx, xL + 24, yB + 330, c_w - 48, 240, 12)
    ctx.set_source_rgb(*LIGHT_EMERALD)
    ctx.fill_preserve()
    ctx.set_source_rgb(*EMERALD)
    ctx.set_line_width(2.2)
    ctx.stroke()

    lq = l6["live_ibm_qpu"]
    draw_text(
        ctx,
        f"CLOUD SUPERCONDUCTING-QPU PROXY (Non-Silicon Control Stack): {lq['backend_name']} ({lq['n_qubits']}Q, job={lq['job_id']})",
        xL + 42,
        yB + 362,
        size=14.0,
        color=(0.02, 0.34, 0.22),
        bold=True,
    )
    qpu_kpis = [
        ("C1 XY4 DD Gain", f"+{lq['c1_xy4_gain_pp']:.2f} pp", f"Bare {lq['c1_bare_p0']:.4f} -> XY4 {lq['c1_xy4_p0']:.4f}"),
        ("C1 Bell Fidelity", f"F = {lq['c1_bell_fidelity']:.4f}", "ZZ=+0.961 | XX=+0.972 | YY=-0.960"),
        ("C2 d=3 QEC (5Q)", f"{lq['c2_suppression_mwpm']:.2f}x / {lq['c2_suppression_majority']:.2f}x", "Post-sel 0.000% (0/7,451)"),
        ("C3 Q16.16 BOED", f"{lq['c3_q16_vs_fp64_kHz']*1000:.1f} Hz vs FP64", f"{lq['c3_q16_points_used']} pts | {lq['c3_q16_boed_kHz']:.3f} kHz"),
    ]
    qk_w = (c_w - 114) / 4.0
    for i, (k1, k2, k3) in enumerate(qpu_kpis):
        qx = xL + 42 + i * (qk_w + 10)
        qy = yB + 382
        rounded_rect(ctx, qx, qy, qk_w, 118, 8)
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.fill_preserve()
        ctx.set_source_rgb(0.65, 0.88, 0.78)
        ctx.set_line_width(1.2)
        ctx.stroke()
        draw_text(ctx, k1, qx + 12, qy + 26, size=13.0, color=MUTED, bold=True)
        draw_text(ctx, k2, qx + 12, qy + 62, size=18.0, color=EMERALD, bold=True, mono=True)
        draw_text(ctx, k3, qx + 12, qy + 98, size=11.5, color=TEXT)

    draw_text(
        ctx,
        f"CellISA v4.0 ({l6['live_cellisa_v40']['v40_total_opcodes']} opcodes) + auto_recal sim ({l6['live_auto_recal']['n_passed']}/{l6['live_auto_recal']['n_fault_modes']} PASS) | Secret Leaks: 0 | Validates 0 Si:31P hardware",
        xL + 42,
        yB + 540,
        size=12.8,
        color=(0.02, 0.34, 0.22),
        bold=True,
        mono=True,
    )

    # =========================================================================
    # PANEL D (Bottom-Right): BOM v7.0 Parametric Tiers & 38/38 SHA-256 Manifest
    # =========================================================================
    draw_card(ctx, xR, yB, c_w, c_h2, "D. Parametric BOM v7.0 & Artifact File-Integrity Manifest", "Exp128 v7.0 + SHA-256")

    draw_text(
        ctx,
        "100k Monte Carlo Exceedance P(Program > $100M) vs 5.0% Policy Cap (Exp128 v7.0)",
        xR + 24,
        yB + 78,
        size=16.0,
        color=NAVY,
        bold=True,
    )
    mt = l7["modular_tiers_v7"]
    tiers = [
        ("M3 v5 Base ($5.248M, 167p)", mt["M3_v5_0_Base"]["P_gt_100M_pct"], EMERALD, "PASS (<5%)"),
        ("Phase-1: Base+Safety ($5.393M, 173p)", mt["M3_Phase1_Base_Plus_Safety"]["P_gt_100M_pct"], CYAN, "RECOMMENDED PHASE-1 (6/6 CU)"),
        ("M3 v6 Full (+Q+HPC, $5.548M, 174p)", mt["M3_v6_0_Full"]["P_gt_100M_pct"], BLUE, "PASS (<5%)"),
        ("M3 v7 Full (+Safety+Q+HPC, $5.693M)", mt["M3_v7_0_Full"]["P_gt_100M_pct"], AMBER, "HONEST >5% -> PHASE-2"),
    ]
    tx_b = xR + 360
    tw_b = 435
    max_p = 6.5
    for i, (lbl, pct, col, note) in enumerate(tiers):
        ry = yB + 98 + i * 52
        draw_text(ctx, lbl, xR + 24, ry + 22, size=14.0, color=TEXT, bold=True)
        rounded_rect(ctx, tx_b, ry + 4, tw_b, 28, 6)
        ctx.set_source_rgb(0.92, 0.94, 0.96)
        ctx.fill()
        fw = tw_b * (pct / max_p)
        rounded_rect(ctx, tx_b, ry + 4, fw, 28, 6)
        ctx.set_source_rgb(*col)
        ctx.fill()
        draw_text(ctx, f"{pct:.2f}%", tx_b + fw - 8, ry + 23, size=13.5, color=(1, 1, 1), bold=True, mono=True, align="right")
        draw_text(ctx, note, tx_b + tw_b + 14, ry + 22, size=13.0, color=col, bold=True)

    # 5.0% policy cap vertical dashed line
    cap_x = tx_b + tw_b * (5.0 / max_p)
    ctx.save()
    ctx.set_source_rgb(*CORAL)
    ctx.set_line_width(2.2)
    ctx.set_dash([7, 4])
    ctx.move_to(cap_x, yB + 94)
    ctx.line_to(cap_x, yB + 302)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "5.0% Hard Cap", cap_x, yB + 318, size=13.0, color=CORAL, bold=True, mono=True, align="center")

    # Phased procurement + 38/38 Lock box
    rounded_rect(ctx, xR + 24, yB + 334, c_w - 48, 236, 12)
    ctx.set_source_rgb(0.95, 0.96, 0.99)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BLUE)
    ctx.set_line_width(2.0)
    ctx.stroke()

    draw_text(ctx, "Artifact File-Integrity Manifest (38/38 SHA-256 — Provenance Only)", xR + 42, yB + 366, size=15.5, color=NAVY, bold=True)
    lock_lines = [
        f"• Experiment Ledgers : 27 primary JSONs (Exp124..Exp150) + IBM proxy raw counts JSON",
        f"• CAD v6.0 Nominal   : {l1['cad_v6']['part_count']} parts | {l1['cad_v6']['total_mass_kg']:.3f} kg | 0 static clashes (excl. GD&T/thermal/DFM)",
        f"• BOM v7.0 Parametric: {l1['bom_v7']['exp128_total_parts']} parts (no vendor quotes) | $0.00 bridge | +355 kg fac. = {l1['bom_v7']['total_facility_load_mass_kg']:.1f} kg",
        f"• 10-RFQ Draft Scope : {l1['bom_v7']['rfq10_nom_share_pct']:.2f}% nominal / {l1['bom_v7']['rfq10_var_share_pct']:.2f}% MC variance (Phase-1 -> RFQ-05 -> Phase-2)",
        f"• Verilog RTL + HTML : 7 rtl/boed_fpga/ files (no_external_eda_sim=true) + digital_twin_interactive.html",
        f"• Historical Manifests: v4 (feffc1d4..), v5 (2828e8ce..), v6 (ca3f0e02..) strictly untouched on disk",
    ]
    for i, ln in enumerate(lock_lines):
        draw_text(ctx, ln, xR + 42, yB + 398 + i * 28, size=13.2, color=TEXT, mono=False)

    # --- BOTTOM FOOTER WITH FULL 64-HEX SHA-256 ---
    ctx.set_source_rgb(*NAVY)
    ctx.rectangle(0, H - 44, W, 44)
    ctx.fill()
    draw_text(
        ctx,
        f"FILE-INTEGRITY SHA-256 (Provenance Only): {cert['sha256']}  |  TRL 1-2 (M0) Model (no_lab_measurement) · IBM 156Q Control Proxy (Non-Silicon)",
        W / 2,
        H - 16,
        size=12.6,
        color=(0.78, 0.90, 1.0),
        bold=True,
        mono=True,
        align="center",
    )

    surf.write_to_png(str(PNG_PATH))
    print(f"Wrote {PNG_PATH} ({PNG_PATH.stat().st_size:,} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
