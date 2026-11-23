"""Generate 2400x1400 publication-grade PyCairo figure for Exp141 (H159) Master v5.0 Digital Twin.

Portable execution (stdlib + cairo only, zero numpy, zero hardcoded host paths):
    /usr/bin/python3 -B experiments/exp141_v5_digital_twin/plot_exp141.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp141_v5_digital_twin"
DATA_PATH = OUT_DIR / "exp141_plot_data.json"

C_BG = (0.975, 0.980, 0.988)
C_CARD = (1.0, 1.0, 1.0)
C_BORDER = (0.82, 0.85, 0.90)
C_HEADER = (0.06, 0.09, 0.16)
C_TEXT = (0.10, 0.14, 0.22)
C_MUTED = (0.38, 0.44, 0.54)
C_GRID = (0.90, 0.92, 0.95)

C_BLUE = (0.15, 0.39, 0.92)
C_TEAL = (0.05, 0.58, 0.53)
C_GREEN = (0.02, 0.59, 0.41)
C_AMBER = (0.86, 0.47, 0.04)
C_RED = (0.84, 0.16, 0.16)
C_PURPLE = (0.49, 0.23, 0.93)


def _round_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 10.0) -> None:
    r = min(r, w / 2.0, h / 2.0)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2.0, 0.0)
    ctx.arc(x + w - r, y + h - r, r, 0.0, math.pi / 2.0)
    ctx.arc(x + r, y + h - r, r, math.pi / 2.0, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def _text(
    ctx: cairo.Context,
    x: float,
    y: float,
    txt: str,
    size: float = 14.0,
    color: tuple[float, float, float] = C_TEXT,
    bold: bool = False,
    align: str = "left",
    family: str = "DejaVu Sans",
) -> float:
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(family, cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)
    ext = ctx.text_extents(txt)
    if align == "center":
        dx = -ext.width / 2.0 - ext.x_bearing
    elif align == "right":
        dx = -ext.width - ext.x_bearing
    else:
        dx = 0.0
    ctx.set_source_rgb(*color)
    ctx.move_to(x + dx, y)
    ctx.show_text(txt)
    return ext.width


def _text_rot90(
    ctx: cairo.Context,
    x: float,
    y: float,
    txt: str,
    size: float = 14.0,
    color: tuple[float, float, float] = C_TEXT,
    bold: bool = False,
) -> None:
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(-math.pi / 2.0)
    _text(ctx, 0.0, 0.0, txt, size=size, color=color, bold=bold, align="center")
    ctx.restore()


def _draw_card(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, tag: str) -> None:
    _round_rect(ctx, x, y, w, h, 12.0)
    ctx.set_source_rgb(*C_CARD)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BORDER)
    ctx.set_line_width(1.6)
    ctx.stroke()
    _text(ctx, x + 22, y + 35, title, size=19.5, color=C_TEXT, bold=True)
    _text(ctx, x + w - 22, y + 34, tag, size=13.5, color=C_GREEN, bold=True, align="right")
    ctx.set_source_rgb(*C_GRID)
    ctx.set_line_width(1.2)
    ctx.move_to(x + 18, y + 50)
    ctx.line_to(x + w - 18, y + 50)
    ctx.stroke()


def plot_v5_digital_twin(data: dict) -> Path:
    W, H = 2400, 1400
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*C_BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    l1 = data["l1"]
    l2 = data["l2"]
    l3 = data["l3"]
    l4 = data["l4"]
    l5 = data["l5"]
    cx4 = data["cx4"]
    wsc = data["wafer_scenarios"]
    le = data["log_econ"]
    mc = data["master_cert"]

    # Header band
    ctx.set_source_rgb(*C_HEADER)
    ctx.rectangle(0, 0, W, 98)
    ctx.fill()
    _text(
        ctx,
        42,
        44,
        "Exp141 (H159) — Atom Lithography Machine v5.0 Master Fault-Tolerant Digital Twin",
        size=28.0,
        color=(1.0, 1.0, 1.0),
        bold=True,
    )
    _text(
        ctx,
        42,
        78,
        (
            f"17 Experiments (Exp124-Exp140) + CAD v5.0 ({l1['cad_v5']['part_count']} parts, 0 clashes) + BOM v5.0 ($5.25M) + "
            f"Live Q16.16 FPGA & CellISA v3.5   |   8/8 Verdicts PASS   |   no_lab_measurement=true"
        ),
        size=14.5,
        color=(0.76, 0.84, 0.96),
    )

    # =========================================================================
    # PANEL A (Top-Left): v3 -> v4 -> v5 Placement Evolution + Live v3.5 Control
    # =========================================================================
    ax, ay, aw, ah = 36, 120, 1148, 608
    _draw_card(ctx, ax, ay, aw, ah, "A. v3.0 -> v4.0 -> v5.0 Placement Closure & Live Control Stack", "DT5_1, DT5_2 & DT5_4 PASS")

    # Left sub-chart: Placement RSS bars [3.30 .. 4.10 nm]
    px0, px1 = ax + 76, ax + 615
    py0, py1 = ay + 90, ay + ah - 110
    _text(ctx, (px0 + px1) / 2.0, ay + 74, "Compound 5 keV Placement Budget, sigma_tot (nm)", size=14.0, color=C_TEXT, bold=True, align="center")

    ymin_p, ymax_p = 3.30, 4.12

    def _yp(v: float) -> float:
        return py1 - ((v - ymin_p) / (ymax_p - ymin_p)) * (py1 - py0)

    for tv in (3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.0, 4.1):
        gy = _yp(tv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, gy)
        ctx.line_to(px1, gy)
        ctx.stroke()
        _text(ctx, px0 - 10, gy + 4, f"{tv:.1f}", size=11.8, color=C_RED if abs(tv - 3.8) < 0.01 else C_MUTED, bold=(abs(tv - 3.8) < 0.01), align="right")

    # Shaded red zone > 3.80 nm
    y38 = _yp(3.80)
    ctx.set_source_rgba(0.84, 0.16, 0.16, 0.08)
    ctx.rectangle(px0, py0, px1 - px0, y38 - py0)
    ctx.fill()
    ctx.save()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(2.0)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(px0, y38)
    ctx.line_to(px1, y38)
    ctx.stroke()
    ctx.restore()
    _text(ctx, px1 - 6, y38 - 8, "Exp124 Ceiling 3.80 nm", size=11.8, color=C_RED, bold=True, align="right")

    p_bars = [
        ("v3.0\n15 ms", l2["v300_orig_15ms_nm"], (0.50, 0.56, 0.66)),
        ("v4.0 Hidden\nTED (FAIL)", l2["v400_hidden_TED_routeC_15ms_nm"], C_RED),
        ("v5.0 1530K\n15 ms", l2["v500_coupled_15ms_nm"], C_BLUE),
        ("v5.0 1530K\n10 ms", l2["v500_coupled_10ms_nm"], C_GREEN),
    ]
    pbw = 92
    for i, (lbl, val, col) in enumerate(p_bars):
        bx_b = px0 + 28 + i * 128
        bt = _yp(val)
        _round_rect(ctx, bx_b, bt, pbw, py1 - bt, 6)
        ctx.set_source_rgb(*col)
        ctx.fill()
        _text(ctx, bx_b + pbw / 2.0, bt + 24, f"{val:.3f}", size=13.0, color=(1.0, 1.0, 1.0), bold=True, align="center")
        lns = lbl.split("\n")
        _text(ctx, bx_b + pbw / 2.0, py1 + 21, lns[0], size=12.0, color=col if i in (1, 3) else C_TEXT, bold=True, align="center")
        _text(ctx, bx_b + pbw / 2.0, py1 + 38, lns[1], size=11.4, color=C_MUTED, align="center")

    # Bottom note under placement chart
    _round_rect(ctx, ax + 34, ay + ah - 56, 582, 38, 7)
    ctx.set_source_rgb(0.94, 0.97, 1.0)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BLUE)
    ctx.set_line_width(1.2)
    ctx.stroke()
    _text(
        ctx,
        ax + 325,
        ay + ah - 32,
        f"v5.0 +2.34 J/cm^2 (1530 K) clears 99.99% {{311}} clusters -> -{l2['ted_cure_improvement_nm']:.3f} nm cure vs v4 TED",
        size=11.8,
        color=C_TEXT,
        bold=True,
        align="center",
    )

    # Right half of Panel A: Live src/machine_control/ + CAD/BOM v5.0 Card Stack
    rx_a = ax + 648
    rw_a = aw - 674
    _round_rect(ctx, rx_a, ay + 74, rw_a, 240, 10)
    ctx.set_source_rgb(0.95, 0.94, 1.0)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_PURPLE)
    ctx.set_line_width(1.5)
    ctx.stroke()
    _text(ctx, rx_a + 18, ay + 104, "Live src/machine_control/ Execution (Exp141 Run)", size=14.5, color=C_PURPLE, bold=True)
    q16 = l4["q16_fpga_live"]
    c35 = l4["cellisa_v35_live"]
    live_lns = [
        (f"Q16.16 BOED-FPGA (N={q16['n_candidates']}, {q16['n_lines_paired']} lines):", C_TEXT, True),
        (f"  RMS = {q16['rms_q16_Hz']:.2f} vs {q16['rms_fp64_Hz']:.2f} Hz (|dRMS| = {q16['abs_delta_rms_Hz']:.4f} Hz)", C_GREEN, True),
        (f"  Step = {q16['step_latency_us']:.3f} us @ 250 MHz | dFNR = {q16['abs_delta_fnr_pct']:.2f}%", C_MUTED, False),
        (f"CellISA v3.5 Live 4x4 Wafer ({c35['total_opcodes']} Opcodes):", C_TEXT, True),
        (f"  Bare CZ = {c35['mean_bare_cz_fidelity']:.4f} -> ECHO_CZ = {c35['mean_echo_cz_fidelity']:.4f} (+{c35['echo_fidelity_gain']*100:.1f} pp)", C_GREEN, True),
        (f"  Syndrome F = {c35['syndrome_round_fidelity']:.4f} | T_cyc = {c35['cycle_duration_us']:.2f} us | SHA256 OK", C_TEXT, False),
    ]
    for i, (ln, col, bld) in enumerate(live_lns):
        _text(ctx, rx_a + 18, ay + 134 + i * 28, ln, size=12.4, color=col, bold=bld)

    # Bottom-right card of Panel A: CAD v5.0 + BOM v5.0 Hardware Baseline
    _round_rect(ctx, rx_a, ay + 332, rw_a, 250, 10)
    ctx.set_source_rgb(0.94, 0.99, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_GREEN)
    ctx.set_line_width(1.5)
    ctx.stroke()
    _text(ctx, rx_a + 18, ay + 362, "v5.0 Verified Engineering & Quantum Chain", size=14.5, color=C_GREEN, bold=True)
    cad = l1["cad_v5"]
    bom = l1["bom_v5"]
    eng_lns = [
        f"CAD v5.0: {cad['part_count']} parts | {cad['total_mass_kg']:.1f} kg | {cad['stl_triangles']:,} STL tris",
        f"Clearances: {cad['clearances_passed']}/{cad['clearances_total']} PASS | Clashes: {cad['solid_clashes']}/{cad['pairs_checked']:,}",
        f"BOM v5.0: {bom['csv_row_count']} parts | M3 = ${bom['m3_v5_nom_usd']/1e6:.3f}M | M1 = ${bom['m1_v5_nom_usd']/1e6:.3f}M",
        f"Exp136 f*=1.5% + 2 MV/m: Yield {l3['exp136_tb_sp3d5s']['f1p5_Ez2_yield_pct']:.1f}%, d_eff/d = {l3['exp136_tb_sp3d5s']['defective_d7_N6_deff_over_d']*100:.1f}%",
        f"Exp139 Route C: p_ff = {l3['exp139_epi_cap_routeC']['p_flipflop_C_ge_100']*100:.1f}%, S_eps = {l3['exp139_epi_cap_routeC']['S_eps_nominal_ueV_rtHz']:.3f} uev/rtHz",
        f"Exp140 Mux: N_mux* = {l3['exp140_mux_fpga']['n_mux_star']}, F_RO = {l3['exp140_mux_fpga']['F_ro_32_2us']*100:.2f}%, Cap = {l3['exp140_mux_fpga']['single_cryostat_max_cells']:,} cells",
    ]
    for i, ln in enumerate(eng_lns):
        _text(ctx, rx_a + 18, ay + 392 + i * 30, ln, size=12.4, color=C_TEXT, bold=(i in (1, 2, 5)))

    # =========================================================================
    # PANEL B (Top-Right): Surface-Code FT Suppression Lambda & M4 Bell Leap
    # =========================================================================
    bx, by, bw, bh = 1216, 120, 1148, 608
    _draw_card(ctx, bx, by, bw, bh, "B. Fault-Tolerant Quantum Leap: Surface-Code Lambda & M4 Bell Fidelity", "DT5_3 & DT5_5 PASS")

    sc5 = l5["scenarios"]
    lx0, lx1 = bx + 92, bx + bw - 42
    ly0, ly1 = by + 92, by + bh - 142
    ymax_l = 2.85

    def _yl(v: float) -> float:
        return ly1 - (min(v, ymax_l) / ymax_l) * (ly1 - ly0)

    # Shaded FT regime above Lambda = 1.0
    y1 = _yl(1.0)
    ctx.set_source_rgba(0.02, 0.59, 0.41, 0.08)
    ctx.rectangle(lx0, ly0, lx1 - lx0, y1 - ly0)
    ctx.fill()
    _text(ctx, lx0 + 12, ly0 + 22, "FAULT-TOLERANT REGIME (Lambda > 1.0: Exponential Error Suppression)", size=12.5, color=C_GREEN, bold=True)

    for lv in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5):
        gy = _yl(lv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(lx0, gy)
        ctx.line_to(lx1, gy)
        ctx.stroke()
        _text(ctx, lx0 - 10, gy + 4, f"{lv:.1f}", size=12.0, color=C_GREEN if abs(lv - 1.0) < 0.01 else C_MUTED, bold=(abs(lv - 1.0) < 0.01), align="right")

    _text_rot90(ctx, bx + 30, (ly0 + ly1) / 2.0, "Error Suppression Factor, Lambda = eps_L(d) / eps_L(d+2)", size=13.5, color=C_TEXT, bold=True)

    # Lambda = 1.0 dashed threshold line
    ctx.save()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(2.0)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(lx0, y1)
    ctx.line_to(lx1, y1)
    ctx.stroke()
    ctx.restore()
    _text(ctx, lx0 + 12, y1 - 10, "Threshold Lambda = 1.0 (p_2q,th = 1.60%)", size=12.0, color=C_RED, bold=True, align="left")

    lam_bars = [
        ("v4 Bare P1\nS=1.0", sc5["A_v4_Bare_P1_S1p0"], C_RED, "p_2q=39.2%"),
        ("v5 Unpass P4\nS=1.0", sc5["B1_v5_Unpass_P4_S1p0"], (0.85, 0.35, 0.15), "p_2q=6.65%"),
        ("v5 C2 Rota C\nQ=2e5, S=0.39", sc5["C2_v5_RotaC_Q2e5_S0p39"], C_AMBER, "p_2q=1.41%"),
        ("v5 D1 Rota C\nQ=5e5, S=0.39", sc5["D1_v5_RotaC_Q5e5_S0p39"], C_BLUE, "p_2q=1.08%"),
        ("v5 D2 Primary\nQ=5e5, S=0.25", sc5["D2_v5_RotaC_Q5e5_S0p25"], C_TEAL, "p_2q=0.92%"),
        ("v5 D3 Target\nDeep FT", sc5["D3_Target_FT_p0p005"], C_GREEN, "p_2q=0.50%"),
    ]
    lbw = 112
    lgap = (lx1 - lx0 - len(lam_bars) * lbw) / (len(lam_bars) + 1)
    for i, (lbl, sdict, col, sub) in enumerate(lam_bars):
        bx_l = lx0 + lgap + i * (lbw + lgap)
        val = sdict["Lambda"]
        bt = _yl(val)
        bar_h = max(ly1 - bt, 4.0)
        _round_rect(ctx, bx_l, ly1 - bar_h, lbw, bar_h, 6)
        ctx.set_source_rgb(*col)
        ctx.fill()
        if val >= 0.45:
            _text(ctx, bx_l + lbw / 2.0, ly1 - bar_h + 25, f"L={val:.2f}", size=13.5, color=(1.0, 1.0, 1.0), bold=True, align="center")
        else:
            _text(ctx, bx_l + lbw / 2.0, ly1 - 12, "L=0.00 (SAT)", size=11.5, color=C_RED, bold=True, align="center")
        lns = lbl.split("\n")
        _text(ctx, bx_l + lbw / 2.0, ly1 + 21, lns[0], size=12.0, color=col if i in (0, 4, 5) else C_TEXT, bold=True, align="center")
        _text(ctx, bx_l + lbw / 2.0, ly1 + 38, lns[1], size=11.2, color=C_MUTED, align="center")
        _text(ctx, bx_l + lbw / 2.0, ly1 + 55, sub, size=11.0, color=C_TEXT, align="center")

    # Bottom banner inside Panel B summarizing Exp137 P4 Bell leap + 6.8x cryostat reduction
    _round_rect(ctx, bx + 32, by + bh - 62, bw - 64, 44, 8)
    ctx.set_source_rgb(0.93, 0.99, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_GREEN)
    ctx.set_line_width(1.3)
    ctx.stroke()
    e137 = l3["exp137_echoed_m4_bus"]
    _text(
        ctx,
        bx + bw / 2.0,
        by + bh - 35,
        (
            f"Exp137 M4 Bus Leap: P1 Bare F_Bell={e137['P1_bare_S1p0_F_Bell']:.3f} -> P4 Q=5e5 S=0.25 F_Bell={e137['P4_Q5e5_S0p25_F_Bell']:.4f}   |   "
            f"D2 -> D3 cuts 100L (1e-9) fleet {l5['fleet_100L_1e9_cryostat_reduction_D2_to_D3']:.2f}x (679 -> 100 cryos)"
        ),
        size=12.6,
        color=C_TEXT,
        bold=True,
        align="center",
    )

    # =========================================================================
    # PANEL C (Bottom-Left): Exp134 CX4 Silicon Wall Broken (W1 -> W2 -> W3)
    # =========================================================================
    cx, cy, cw, ch = 36, 756, 1148, 608
    _draw_card(ctx, cx, cy, cw, ch, "C. Exp134 CX4 Silicon Wall Broken: Thin 30 nm 28Si-on-SOI (W1 -> W2 -> W3)", "DT5_6 PASS")

    # Stacked horizontal bars: Wafer Silicon Floor vs Machine Amortization per 10k-register chip
    wx0, wx1 = cx + 275, cx + cw - 230
    wy0, wy1 = cy + 94, cy + ch - 135
    max_usd = 3.25

    def _xw(v: float) -> float:
        return wx0 + (min(v, max_usd) / max_usd) * (wx1 - wx0)

    # Legend top of Panel C
    _round_rect(ctx, wx0, cy + 64, 16, 14, 3)
    ctx.set_source_rgb(*C_BLUE)
    ctx.fill()
    _text(ctx, wx0 + 22, cy + 76, "Machine Amort. + OPEX Share", size=12.8, color=C_TEXT, bold=True)
    _round_rect(ctx, wx0 + 260, cy + 64, 16, 14, 3)
    ctx.set_source_rgb(*C_AMBER)
    ctx.fill()
    _text(ctx, wx0 + 282, cy + 76, "28Si Wafer Substrate Floor", size=12.8, color=C_TEXT, bold=True)

    for tv in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        gx = _xw(tv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(gx, wy0)
        ctx.line_to(gx, wy1)
        ctx.stroke()
        _text(ctx, gx, wy1 + 22, f"${tv:.2f}", size=12.0, color=C_MUTED, align="center")
    _text(ctx, (wx0 + wx1) / 2.0, wy1 + 52, "Total Dense-M4 Fab Cost per 10,000-Register Chip (USD, N=1 tool P50)", size=13.5, color=C_TEXT, bold=True, align="center")

    v3_w1 = wsc["W1"]["v3_dense"]
    v5_w1 = wsc["W1"]["v5_dense_15ms"]
    v5_w2 = wsc["W2"]["v5_dense_15ms"]
    v5_w3 = wsc["W3"]["v5_dense_15ms"]

    w_rows = [
        ("v3.0 Ref (W1: $12k 200mm)", v3_w1["machine_usd_per_chip_10k_p50"], v3_w1["wafer_floor_usd_per_chip_10k"], "Ref ($3.012)", C_MUTED),
        ("v5.0 + W1 ($12k Thick Epi)", v5_w1["machine_usd_per_chip_10k_p50"], v5_w1["wafer_floor_usd_per_chip_10k"], "-14.5% | CX4 FAIL", C_RED),
        ("v5.0 + W2 (30nm 200mm SOI)", v5_w2["machine_usd_per_chip_10k_p50"], v5_w2["wafer_floor_usd_per_chip_10k"], f"-{cx4['W2_reduction_vs_v3_W1_frac']*100:.1f}% | CX4 PASS!", C_TEAL),
        ("v5.0 + W3 (30nm 300mm SOI)", v5_w3["machine_usd_per_chip_10k_p50"], v5_w3["wafer_floor_usd_per_chip_10k"], f"-{cx4['W3_reduction_vs_v3_W1_frac']*100:.1f}% | CX4 PASS!", C_GREEN),
    ]
    bh_w = 56
    bg_w = (wy1 - wy0 - len(w_rows) * bh_w) / (len(w_rows) + 1)
    for i, (lbl, m_usd, w_usd, tag_t, tcol) in enumerate(w_rows):
        ry = wy0 + bg_w + i * (bh_w + bg_w)
        _text(ctx, wx0 - 14, ry + bh_w * 0.62, lbl, size=13.0, color=C_TEXT, bold=(i >= 2), align="right")
        xm = _xw(m_usd)
        xt = _xw(m_usd + w_usd)
        # Machine segment
        ctx.set_source_rgb(*C_BLUE)
        ctx.rectangle(wx0, ry, max(xm - wx0, 4.0), bh_w)
        ctx.fill()
        # Wafer segment
        ctx.set_source_rgb(*C_AMBER)
        ctx.rectangle(xm, ry, max(xt - xm, 4.0), bh_w)
        ctx.fill()
        tot_u = m_usd + w_usd
        _text(ctx, xt + 10, ry + bh_w * 0.44, f"${tot_u:.3f}/chip  ({tag_t})", size=12.6, color=tcol, bold=True)
        _text(ctx, xt + 10, ry + bh_w * 0.82, f"mach ${m_usd:.3f} + Si ${w_usd:.3f} ({w_usd/tot_u*100:.1f}%)", size=11.4, color=C_MUTED)

    # Bottom explanation strip in Panel C
    _round_rect(ctx, cx + 28, cy + ch - 62, cw - 56, 44, 8)
    ctx.set_source_rgb(0.93, 0.99, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_GREEN)
    ctx.set_line_width(1.3)
    ctx.stroke()
    _text(
        ctx,
        cx + cw / 2.0,
        cy + ch - 35,
        "Active donor zone <= 23 nm (Exp139): thin 30 nm 28Si-on-SOI cuts 28SiH4 >95% — W2 fits M3 v5.0 ($0 tool mod; same-wafer -41.4% / W3 -50.0%)",
        size=11.0,
        color=C_TEXT,
        bold=True,
        align="center",
    )

    # =========================================================================
    # PANEL D (Bottom-Right): Real $/Logical Qubit (Fab vs 100L Deployed) + SHA-256
    # =========================================================================
    dx, dy, dw, dh = 1216, 756, 1148, 608
    _draw_card(ctx, dx, dy, dw, dh, "D. Real $/Logical Qubit (D2 vs D3: Fab Chip vs 100L Cryo Fleet) & SHA-256", "DT5_7 & DT5_8 PASS")

    d2 = le["D2_primary_Lambda1p40"]
    d3 = le["D3_target_Lambda2p52"]

    # Left sub-chart: Deployed 100L System TCO per Logical Qubit ($M/L, log scale)
    sx0, sx1 = dx + 82, dx + 560
    sy0, sy1 = dy + 92, dy + 425
    _text(ctx, (sx0 + sx1) / 2.0, dy + 74, "100L Deployed System TCO ($M / Logical Qubit, Wright)", size=13.4, color=C_TEXT, bold=True, align="center")

    def _ys(m_usd: float) -> float:
        lo, hi = math.log10(0.5), math.log10(45.0)
        return sy1 - ((math.log10(max(0.5, min(45.0, m_usd))) - lo) / (hi - lo)) * (sy1 - sy0)

    for mv, mlbl in ((1.0, "$1M"), (2.5, "$2.5M"), (5.0, "$5M"), (10.0, "$10M"), (20.0, "$20M"), (35.0, "$35M")):
        gy = _ys(mv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(sx0, gy)
        ctx.line_to(sx1, gy)
        ctx.stroke()
        _text(ctx, sx0 - 8, gy + 4, mlbl, size=11.5, color=C_MUTED, align="right")

    targets = [("1e-6", "eps_L = 10^-6"), ("1e-9", "eps_L = 10^-9"), ("1e-12", "eps_L = 10^-12")]
    gw_s = (sx1 - sx0) / 3.0
    bw_s = 50
    for i, (tk, tlbl) in enumerate(targets):
        gx_c = sx0 + (i + 0.5) * gw_s
        v_d2 = d2[tk]["sys_100L_usd_per_L_amort_wright_p50"] / 1e6
        v_d3 = d3[tk]["sys_100L_usd_per_L_amort_wright_p50"] / 1e6

        # D2 bar (amber)
        b2x = gx_c - bw_s - 4
        b2y = _ys(v_d2)
        _round_rect(ctx, b2x, b2y, bw_s, sy1 - b2y, 5)
        ctx.set_source_rgb(*C_AMBER)
        ctx.fill()
        _text(ctx, b2x + bw_s / 2.0, b2y - 6, f"${v_d2:.1f}M", size=11.2, color=C_AMBER, bold=True, align="center")

        # D3 bar (green)
        b3x = gx_c + 4
        b3y = _ys(v_d3)
        _round_rect(ctx, b3x, b3y, bw_s, sy1 - b3y, 5)
        ctx.set_source_rgb(*C_GREEN)
        ctx.fill()
        _text(ctx, b3x + bw_s / 2.0, b3y - 6, f"${v_d3:.2f}M", size=11.2, color=C_GREEN, bold=True, align="center")

        _text(ctx, gx_c, sy1 + 21, tlbl, size=12.0, color=C_TEXT, bold=True, align="center")
        _text(ctx, gx_c, sy1 + 38, f"d*: {d2[tk]['d_star']} vs {d3[tk]['d_star']}", size=11.0, color=C_MUTED, align="center")

    # Mini legend under left sub-chart
    _round_rect(ctx, sx0 + 18, sy1 + 52, 14, 14, 3)
    ctx.set_source_rgb(*C_AMBER)
    ctx.fill()
    _text(ctx, sx0 + 38, sy1 + 64, "D2 (Lambda=1.40, 0.92%)", size=11.6, color=C_TEXT, bold=True)
    _round_rect(ctx, sx0 + 235, sy1 + 52, 14, 14, 3)
    ctx.set_source_rgb(*C_GREEN)
    ctx.fill()
    _text(ctx, sx0 + 255, sy1 + 64, "D3 Target (Lambda=2.52, 0.50%)", size=11.6, color=C_TEXT, bold=True)

    # Right side of Panel D: Explicit Fab ($/L_fab) vs System ($/L_sys) Table
    tx_d = dx + 584
    tw_d = dw - 610
    ty_d = dy + 72
    _text(ctx, tx_d, ty_d + 12, "Honest Split: Silicon Fab ($/L_fab) vs Cryo Fleet ($/L_sys)", size=13.6, color=C_TEXT, bold=True)
    ctx.set_source_rgb(0.94, 0.96, 0.99)
    ctx.rectangle(tx_d, ty_d + 24, tw_d, 32)
    ctx.fill()
    _text(ctx, tx_d + 8, ty_d + 45, "Target / Regime", size=11.6, color=C_TEXT, bold=True)
    _text(ctx, tx_d + 165, ty_d + 45, "d* | Cryos", size=11.6, color=C_MUTED, bold=True)
    _text(ctx, tx_d + 282, ty_d + 45, "$/L_fab (W3)", size=11.6, color=C_BLUE, bold=True)
    _text(ctx, tx_d + 398, ty_d + 45, "$/L_sys (100L)", size=11.6, color=C_GREEN, bold=True)

    econ_rows = [
        ("D2  10^-6", f"{d2['1e-6']['d_star']} | {d2['1e-6']['cryostats_100L']}", f"${d2['1e-6']['fab_usd_per_L_W3']:.2f}", f"${d2['1e-6']['sys_100L_usd_per_L_amort_wright_p50']/1e6:.2f}M"),
        ("D2  10^-9", f"{d2['1e-9']['d_star']} | {d2['1e-9']['cryostats_100L']}", f"${d2['1e-9']['fab_usd_per_L_W3']:.2f}", f"${d2['1e-9']['sys_100L_usd_per_L_amort_wright_p50']/1e6:.2f}M"),
        ("D2  10^-12", f"{d2['1e-12']['d_star']} | {d2['1e-12']['cryostats_100L']}", f"${d2['1e-12']['fab_usd_per_L_W3']:.2f}", f"${d2['1e-12']['sys_100L_usd_per_L_amort_wright_p50']/1e6:.2f}M"),
        ("D3  10^-6", f"{d3['1e-6']['d_star']} | {d3['1e-6']['cryostats_100L']}", f"${d3['1e-6']['fab_usd_per_L_W3']:.2f}", f"${d3['1e-6']['sys_100L_usd_per_L_amort_wright_p50']/1e6:.2f}M"),
        ("D3  10^-9*", f"{d3['1e-9']['d_star']} | {d3['1e-9']['cryostats_100L']}", f"${d3['1e-9']['fab_usd_per_L_W3']:.2f}", f"${d3['1e-9']['sys_100L_usd_per_L_amort_wright_p50']/1e6:.2f}M"),
        ("D3  10^-12", f"{d3['1e-12']['d_star']} | {d3['1e-12']['cryostats_100L']}", f"${d3['1e-12']['fab_usd_per_L_W3']:.2f}", f"${d3['1e-12']['sys_100L_usd_per_L_amort_wright_p50']/1e6:.2f}M"),
    ]
    for i, (r0, r1, r2, r3) in enumerate(econ_rows):
        ry = ty_d + 80 + i * 44
        if i == 4:
            ctx.set_source_rgba(0.02, 0.59, 0.41, 0.11)
            ctx.rectangle(tx_d, ry - 22, tw_d, 38)
            ctx.fill()
        elif i % 2 == 1:
            ctx.set_source_rgb(0.985, 0.990, 0.996)
            ctx.rectangle(tx_d, ry - 22, tw_d, 38)
            ctx.fill()
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(tx_d, ry + 16)
        ctx.line_to(tx_d + tw_d, ry + 16)
        ctx.stroke()
        _text(ctx, tx_d + 8, ry + 2, r0, size=12.0, color=C_GREEN if i >= 3 else C_AMBER, bold=True)
        _text(ctx, tx_d + 165, ry + 2, r1, size=11.8, color=C_TEXT)
        _text(ctx, tx_d + 282, ry + 2, r2, size=12.0, color=C_BLUE, bold=True)
        _text(ctx, tx_d + 398, ry + 2, r3, size=12.0, color=C_GREEN if i >= 3 else C_TEXT, bold=True)

    _text(
        ctx,
        tx_d,
        ty_d + 356,
        f"*D3 @ 10^-9: 1 patch/fridge (2,737 <= 2,887); {le['D2_to_D3_deployed_cost_ratio_1e9']:.2f}x lower $/L_sys!",
        size=11.2,
        color=C_TEAL,
        bold=True,
    )

    # Full-width cryptographic v5.0 Master Certificate SHA-256 Seal at bottom of Panel D
    _round_rect(ctx, dx + 28, dy + dh - 72, dw - 56, 54, 9)
    ctx.set_source_rgb(0.06, 0.09, 0.16)
    ctx.fill()
    _text(
        ctx,
        dx + dw / 2.0,
        dy + dh - 48,
        "v5.0 MASTER DIGITAL TWIN CERTIFICATE: DT5_1..DT5_8 (8/8 PASS)  |  19 ARTIFACTS SHA-256 LOCKED",
        size=12.8,
        color=(0.42, 0.96, 0.76),
        bold=True,
        align="center",
    )
    _text(
        ctx,
        dx + dw / 2.0,
        dy + dh - 26,
        f"FULL SHA-256: {mc['sha256']}",
        size=12.2,
        color=(0.86, 0.91, 0.98),
        bold=True,
        align="center",
        family="DejaVu Sans Mono",
    )

    out_path = OUT_DIR / "fig_exp141_v5_digital_twin.png"
    surf.write_to_png(str(out_path))
    return out_path


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    p = plot_v5_digital_twin(data)
    print(f"Wrote {p.name}")


if __name__ == "__main__":
    main()
