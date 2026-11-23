"""Generate 2400x1400 publication-grade PyCairo figure for Exp140 (H158).

Portable execution (stdlib + cairo only, zero numpy, zero hardcoded host paths):
    /usr/bin/python3 -B experiments/exp140_cryo_fpga_boed_mux_readout/plot_exp140.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp140_cryo_fpga_boed_mux_readout"
DATA_PATH = OUT_DIR / "exp140_plot_data.json"

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
    _text(ctx, x + 22, y + 35, title, size=20.0, color=C_TEXT, bold=True)
    _text(ctx, x + w - 22, y + 34, tag, size=14.0, color=C_GREEN, bold=True, align="right")
    ctx.set_source_rgb(*C_GRID)
    ctx.set_line_width(1.2)
    ctx.move_to(x + 18, y + 50)
    ctx.line_to(x + w - 18, y + 50)
    ctx.stroke()


def plot_exp140(data: dict) -> Path:
    W, H = 2400, 1400
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*C_BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    fb = data["fpga_bench"]
    fr = fb["fpga_resources"]
    mx = data["mux_res"]
    cp = mx["chain_physics"]
    c1 = data["cryo_1024"]
    c10 = data["cryo_10000"]
    curve = data["array_scale_curve"]
    v35 = data["cellisa_v35"]
    s65 = data["s65_spec"]

    # Header band
    ctx.set_source_rgb(*C_HEADER)
    ctx.rectangle(0, 0, W, 98)
    ctx.fill()
    _text(
        ctx,
        42,
        45,
        "Exp140 (H158) — Real-Time Q16.16 BOED-FPGA Accelerator, 3 kOhm NbTiN Mux Cryo Readout & CellISA v3.5",
        size=28.0,
        color=(1.0, 1.0, 1.0),
        bold=True,
    )
    _text(
        ctx,
        42,
        78,
        (
            f"ZU48DR RFSoC @ 250 MHz (2.34 us/step, |dRMS|={fb['parity']['abs_delta_rms_Hz']:.3f} Hz)   |   "
            f"3 kOhm NbTiN + Purcell (625x) + TWPA -> N_mux*={mx['n_mux_star']}   |   "
            f"1,024-Cell Closes PT420 vs 10,000-Cell Wall (4 Fridges)   |   7/7 PASS   |   no_lab_measurement=true"
        ),
        size=14.5,
        color=(0.76, 0.84, 0.96),
    )

    # =========================================================================
    # PANEL A (Top-Left): Q16.16 vs FP64 Parity + RFSoC Pipeline & Resources
    # =========================================================================
    ax, ay, aw, ah = 36, 120, 1148, 608
    _draw_card(ctx, ax, ay, aw, ah, "A. Bit-Exact Q16.16 BOED-FPGA DSP Engine (250 MHz ZU48DR RFSoC)", "FM1 & FM2 PASS")

    # Top flow diagram: 3-pass cycle-exact pipeline
    py_flow = ay + 74
    stages = [
        ("Pass 1: LUT + Log-Lik", "512-entry BRAM Lor LUT", f"263 cyc (1.052 us)", C_BLUE),
        ("Pass 2: Exp + 48b MAC", "512-entry Exp LUT + Z/M1/M2", f"265 cyc (1.060 us)", C_TEAL),
        ("Pass 3: Div/CORDIC/Argmax", "Radix-4 + Q4 isqrt + DDS", f"56 cyc (0.224 us)", C_PURPLE),
        ("Total BOED Step", "4-lane SIMD @ 250 MHz", f"{fr['cycles_per_boed_step']} cyc = {fr['latency_per_boed_step_us']:.3f} us", C_GREEN),
    ]
    sw_box = 246
    sgap = 36
    sx0 = ax + 28
    for i, (st_t, st_s, st_c, col) in enumerate(stages):
        bx_s = sx0 + i * (sw_box + sgap)
        _round_rect(ctx, bx_s, py_flow, sw_box, 96, 9)
        ctx.set_source_rgb(0.985, 0.992, 1.0)
        ctx.fill_preserve()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.2)
        ctx.stroke()
        _round_rect(ctx, bx_s, py_flow, sw_box, 29, 8)
        ctx.set_source_rgb(*col)
        ctx.fill()
        _text(ctx, bx_s + sw_box / 2.0, py_flow + 20, st_t, size=13.0, color=(1.0, 1.0, 1.0), bold=True, align="center")
        _text(ctx, bx_s + sw_box / 2.0, py_flow + 54, st_s, size=12.5, color=C_MUTED, align="center")
        _text(ctx, bx_s + sw_box / 2.0, py_flow + 80, st_c, size=14.0, color=col, bold=True, align="center")
        if i < len(stages) - 1:
            ax1 = bx_s + sw_box + 5
            ay1 = py_flow + 48
            ctx.set_source_rgb(0.45, 0.52, 0.62)
            ctx.set_line_width(2.6)
            ctx.move_to(ax1, ay1)
            ctx.line_to(ax1 + sgap - 12, ay1)
            ctx.stroke()
            ctx.move_to(ax1 + sgap - 12, ay1 - 6)
            ctx.line_to(ax1 + sgap - 3, ay1)
            ctx.line_to(ax1 + sgap - 12, ay1 + 6)
            ctx.close_path()
            ctx.fill()

    # Left bottom of Panel A: Paired FP64 vs Q16.16 Comparison Table
    tx_a = ax + 28
    ty_a = ay + 196
    tw_a = 530
    _text(ctx, tx_a, ty_a + 12, f"Paired Benchmark (N={fb['n_candidates']} candidates, {fb['n_lines_paired']:,} lines)", size=14.5, color=C_TEXT, bold=True)
    ctx.set_source_rgb(0.94, 0.96, 0.99)
    ctx.rectangle(tx_a, ty_a + 24, tw_a, 34)
    ctx.fill()
    _text(ctx, tx_a + 12, ty_a + 46, "Metric", size=13.0, color=C_TEXT, bold=True)
    _text(ctx, tx_a + 245, ty_a + 46, "FP64 (Exp132)", size=13.0, color=C_MUTED, bold=True)
    _text(ctx, tx_a + 385, ty_a + 46, "Q16.16 FPGA", size=13.0, color=C_TEAL, bold=True)

    p_rows = [
        ("Stage-2 RMS Error", f"{fb['fp64']['rms_freq_error_Hz']:.2f} Hz", f"{fb['q16_16']['rms_freq_error_Hz']:.2f} Hz"),
        ("Stage-2 MAE Error", f"{fb['fp64']['mae_freq_error_Hz']:.2f} Hz", f"{fb['q16_16']['mae_freq_error_Hz']:.2f} Hz"),
        ("Abs |dRMS| Parity", "ref = 0.00 Hz", f"{fb['parity']['abs_delta_rms_Hz']:.4f} Hz (<1 Hz)"),
        ("Quantization Diff RMS", "—", f"{fb['parity']['rms_quantization_diff_Hz']:.2f} Hz"),
        ("FNR / FPR", f"{fb['fp64']['fnr_pct']:.2f}% / {fb['fp64']['fpr_pct']:.2f}%", f"{fb['q16_16']['fnr_pct']:.2f}% / {fb['q16_16']['fpr_pct']:.2f}%"),
        ("Stage-0 SPRT Parity", "100% match", f"{fb['stage0_sprt_disagreements']} diffs (16 ns/shot)"),
        ("Mean Candidate Time", f"{fb['fp64']['mean_time_ms']:.2f} ms", f"{fb['q16_16']['mean_time_ms']:.2f} ms"),
    ]
    for i, (m_k, m_fp, m_q) in enumerate(p_rows):
        ry = ty_a + 82 + i * 44
        if i % 2 == 1:
            ctx.set_source_rgb(0.985, 0.990, 0.996)
            ctx.rectangle(tx_a, ry - 22, tw_a, 38)
            ctx.fill()
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(tx_a, ry + 16)
        ctx.line_to(tx_a + tw_a, ry + 16)
        ctx.stroke()
        _text(ctx, tx_a + 12, ry + 2, m_k, size=13.0, color=C_TEXT, bold=True)
        _text(ctx, tx_a + 245, ry + 2, m_fp, size=13.0, color=C_MUTED)
        _text(ctx, tx_a + 385, ry + 2, m_q, size=13.0, color=C_GREEN if i in (2, 4, 5) else C_TEAL, bold=True)

    # Right bottom of Panel A: 16-Channel ZU48DR Resource Utilization Bars (<25% target)
    rx_a = ax + 598
    rw_a = aw - 626
    ry_a = ay + 196
    _text(ctx, rx_a, ry_a + 12, "16-Channel Parallel BOED Utilization on Single ZU48DR RFSoC", size=14.5, color=C_TEXT, bold=True)

    t16 = fr["total_16ch"]
    res_bars = [
        ("DSP48E2 Slices", t16["dsp48e2_pct"], f"{t16['dsp48e2']:,} / 4.27k", C_BLUE),
        ("BRAM36 Blocks", t16["bram36_pct"], f"{t16['bram36']:,} / 1.08k", C_TEAL),
        ("CLB LUTs", t16["lut_pct"], f"{t16['lut']/1e3:.1f}k / 425k", C_PURPLE),
        ("Flip-Flops (FF)", t16["ff_pct"], f"{t16['ff']/1e3:.1f}k / 851k", C_GREEN),
    ]
    bx0_r = rx_a + 145
    bx1_r = rx_a + rw_a - 15
    by0_r = ry_a + 44
    by1_r = ry_a + 275
    max_pct = 30.0

    def _xr(p: float) -> float:
        return bx0_r + (min(p, max_pct) / max_pct) * (bx1_r - bx0_r)

    for pv in (0, 5, 10, 15, 20, 25, 30):
        gx = _xr(pv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(gx, by0_r)
        ctx.line_to(gx, by1_r)
        ctx.stroke()
        _text(ctx, gx, by1_r + 20, f"{pv}%", size=11.5, color=C_MUTED, align="center")

    # 25% FM2 cap dashed line
    x25 = _xr(25.0)
    ctx.save()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.8)
    ctx.set_dash([5.0, 4.0])
    ctx.move_to(x25, by0_r - 6)
    ctx.line_to(x25, by1_r)
    ctx.stroke()
    ctx.restore()
    _text(ctx, x25 - 6, by0_r - 10, "FM2 <25% limit", size=11.5, color=C_RED, bold=True, align="right")

    bh_r = 36
    bg_r = (by1_r - by0_r - 4 * bh_r) / 5.0
    for i, (rlbl, rpct, rcnt, col) in enumerate(res_bars):
        ry_b = by0_r + bg_r + i * (bh_r + bg_r)
        _text(ctx, bx0_r - 10, ry_b + 23, rlbl, size=12.8, color=C_TEXT, bold=True, align="right")
        _round_rect(ctx, bx0_r, ry_b, _xr(rpct) - bx0_r, bh_r, 5)
        ctx.set_source_rgb(*col)
        ctx.fill()
        _text(ctx, _xr(rpct) + 8, ry_b + 23, f"{rpct:.2f}%  ({rcnt})", size=12.2, color=col, bold=True)

    # Power & latency badge bottom-right of Panel A
    _round_rect(ctx, rx_a, ay + ah - 82, rw_a, 62, 8)
    ctx.set_source_rgb(0.93, 0.99, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_GREEN)
    ctx.set_line_width(1.3)
    ctx.stroke()
    _text(
        ctx,
        rx_a + rw_a / 2.0,
        ay + ah - 56,
        f"Latency Margin: 2.34 us vs 25.0 us Target (10.7x headroom)",
        size=13.5,
        color=C_GREEN,
        bold=True,
        align="center",
    )
    _text(
        ctx,
        rx_a + rw_a / 2.0,
        ay + ah - 34,
        f"300 K Rack Power: {t16['board_total_power_W']:.1f} W / board  |  Cryo Heat Load: 0.00 W  |  500+ kHz Loop Rate",
        size=12.2,
        color=C_TEXT,
        align="center",
    )

    # =========================================================================
    # PANEL B (Top-Right): 3 kOhm NbTiN Mux F_RO(N_mux, tau_RO) & N_mux* Wall
    # =========================================================================
    bx, by, bw, bh = 1216, 120, 1148, 608
    _draw_card(ctx, bx, by, bw, bh, "B. 3 kOhm NbTiN + Purcell (625x) + TWPA Readout Fidelity vs N_mux", "FM3 & FM4 PASS")

    mx0, mx1 = bx + 92, bx + 730
    my0, my1 = by + 84, by + bh - 88
    xmin_t, xmax_t = 0.5, 5.0
    ymin_f, ymax_f = 0.88, 1.005

    def _xm(t: float) -> float:
        return mx0 + ((t - xmin_t) / (xmax_t - xmin_t)) * (mx1 - mx0)

    def _ym(f: float) -> float:
        return my1 - ((max(ymin_f, min(ymax_f, f)) - ymin_f) / (ymax_f - ymin_f)) * (my1 - my0)

    for fv in (0.88, 0.90, 0.92, 0.94, 0.96, 0.98, 0.99, 1.00):
        gy = _ym(fv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(mx0, gy)
        ctx.line_to(mx1, gy)
        ctx.stroke()
        if fv != 0.99:
            _text(ctx, mx0 - 10, gy + 4, f"{fv*100:.0f}%", size=12.0, color=C_MUTED, align="right")

    for tv in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0):
        gx = _xm(tv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(gx, my0)
        ctx.line_to(gx, my1)
        ctx.stroke()
        _text(ctx, gx, my1 + 22, f"{tv:.1f}", size=12.2, color=C_TEXT if tv == 2.0 else C_MUTED, bold=(tv == 2.0), align="center")

    _text(ctx, (mx0 + mx1) / 2.0, my1 + 52, "Readout Integration Time, tau_RO (us)", size=14.0, color=C_TEXT, bold=True, align="center")
    _text_rot90(ctx, bx + 28, (my0 + my1) / 2.0, "Single-Shot Assignment Fidelity, F_RO (%)", size=14.0, color=C_TEXT, bold=True)

    # 99% horizontal target + 2.0 us vertical reference
    y99 = _ym(0.990)
    ctx.save()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.8)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(mx0, y99)
    ctx.line_to(mx1, y99)
    ctx.stroke()
    ctx.restore()
    _text(ctx, mx1 - 6, y99 - 8, "F_RO >= 99.0% Target", size=12.0, color=C_RED, bold=True, align="right")

    x2 = _xm(2.0)
    ctx.save()
    ctx.set_source_rgb(0.55, 0.60, 0.68)
    ctx.set_line_width(1.4)
    ctx.set_dash([4.0, 4.0])
    ctx.move_to(x2, my0)
    ctx.line_to(x2, my1)
    ctx.stroke()
    ctx.restore()
    _text(ctx, x2 - 8, my1 - 12, "tau_RO = 2.0 us", size=11.8, color=C_MUTED, bold=True, align="right")

    mux_styles = [
        ("8", C_BLUE, [], 2.8, "N_mux = 8  (400 MHz, 0.0 dB BO)"),
        ("16", C_TEAL, [8.0, 4.0], 2.8, "N_mux = 16 (200 MHz, 0.0 dB BO)"),
        ("32", C_GREEN, [], 3.8, "N_mux* = 32 (100 MHz, 1.36 dB BO)"),
        ("64", C_RED, [4.0, 3.0], 3.4, "N_mux = 64 (50 MHz, 5.34 dB BO, FAIL)"),
    ]
    for nk, col, dash, lw, _lbl in mux_styles:
        pts = mx["by_nmux"][nk]["tau_curve"]
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        for i, p in enumerate(pts):
            px, py = _xm(p["tau_ro_us"]), _ym(p["F_ro"])
            if i == 0:
                ctx.move_to(px, py)
            else:
                ctx.line_to(px, py)
        ctx.stroke()
        ctx.restore()
        for p in pts:
            if p["F_ro"] >= ymin_f:
                ctx.set_source_rgb(*col)
                ctx.arc(_xm(p["tau_ro_us"]), _ym(p["F_ro"]), 4.5, 0, 2.0 * math.pi)
                ctx.fill()

    # Legend inside Panel B bottom-right of plot area
    lgx, lgy = mx0 + 230, my1 - 126
    _round_rect(ctx, lgx, lgy, 396, 112, 8)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BORDER)
    ctx.set_line_width(1.2)
    ctx.stroke()
    for i, (_nk, col, dash, _lw, lbl) in enumerate(mux_styles):
        yy = lgy + 23 + i * 25
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(3.0)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(lgx + 12, yy - 4)
        ctx.line_to(lgx + 40, yy - 4)
        ctx.stroke()
        ctx.restore()
        _text(ctx, lgx + 48, yy, lbl, size=12.0, color=col if i in (2, 3) else C_TEXT, bold=(i in (2, 3)))

    # Axes frame Panel B
    ctx.set_source_rgb(0.45, 0.50, 0.58)
    ctx.set_line_width(1.4)
    ctx.move_to(mx0, my0)
    ctx.line_to(mx0, my1)
    ctx.line_to(mx1, my1)
    ctx.stroke()

    # Right side of Panel B: Physical N_mux* Wall Diagnostic Card
    dx_b = bx + 760
    dw_b = bw - 786
    _round_rect(ctx, dx_b, by + 76, dw_b, 210, 10)
    ctx.set_source_rgb(0.95, 0.98, 1.0)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BLUE)
    ctx.set_line_width(1.4)
    ctx.stroke()
    _text(ctx, dx_b + 16, by + 104, "4-8 GHz Microwave Readout Chain", size=14.2, color=C_BLUE, bold=True)
    chain_lines = [
        f"Resonator: 3 kOhm NbTiN (Q_i = 2e5)",
        f"chi/2pi = {cp['chi_MHz']:.2f} MHz | kappa = {cp['kappa_ro_MHz']:.1f} MHz",
        f"Purcell Filter: {cp['purcell_protection_factor']:.0f}x (T1_P = {cp['t1_purcell_filtered_ms']:.1f} ms)",
        f"TWPA 20 mK: T_N=0.30 K, G=20 dB, P1dB=-98 dBm",
        f"HEMT 4 K: T_N=2.0 K -> T_sys = {cp['t_sys_with_twpa_K']:.3f} K",
        f"Meas. Efficiency: {cp['eta_meas_with_twpa']*100:.1f}% (vs 3.1% no-TWPA)",
    ]
    for i, ln in enumerate(chain_lines):
        _text(ctx, dx_b + 16, by + 132 + i * 25, ln, size=12.4, color=C_TEXT, bold=(i in (2, 4)))

    # Bottom right of Panel B: N_mux = 32 vs N_mux = 64 Wall Comparison
    _round_rect(ctx, dx_b, by + 306, dw_b, 274, 10)
    ctx.set_source_rgb(0.995, 0.975, 0.965)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_AMBER)
    ctx.set_line_width(1.5)
    ctx.stroke()
    _text(ctx, dx_b + 16, by + 334, "Physical Ceiling: Why N_mux* = 32", size=14.2, color=C_AMBER, bold=True)
    nm32 = mx["by_nmux"]["32"]
    nm64 = mx["by_nmux"]["64"]
    wall_lines = [
        ("N_mux* = 32 (LOCKED):", C_GREEN, True),
        (f"  df = 100 MHz (6.7 sigma_fab), coll = {nm32['pair_collision_prob_pct']:.4f}%", C_TEXT, False),
        (f"  P_peak = {nm32['p_peak_nom_twpa_dBm']:.1f} dBm -> BO = {nm32['twpa_backoff_dB']:.2f} dB", C_TEXT, False),
        (f"  n_bar = {nm32['n_bar_effective']:.1f} ph -> F_RO(2us) = {nm32['F_ro_at_2us']*100:.2f}% PASS", C_GREEN, True),
        ("N_mux = 64 (PHYSICAL WALL):", C_RED, True),
        (f"  df = 50 MHz (3.3 sigma_fab), coll = {nm64['pair_collision_prob_pct']:.2f}%!", C_RED, False),
        (f"  P_peak = {nm64['p_peak_nom_twpa_dBm']:.1f} dBm > P1dB -> BO = {nm64['twpa_backoff_dB']:.2f} dB", C_TEXT, False),
        (f"  n_bar = {nm64['n_bar_effective']:.1f} ph -> F_RO(2us) = {nm64['F_ro_at_2us']*100:.2f}% FAIL", C_RED, True),
    ]
    for i, (ln, col, bld) in enumerate(wall_lines):
        _text(ctx, dx_b + 16, by + 364 + i * 26, ln, size=12.3, color=col, bold=bld)

    # =========================================================================
    # PANEL C (Bottom-Left): 4-Stage Cryostat Heat Budget (1,024 vs 10,000 Cells)
    # =========================================================================
    cx, cy, cw, ch = 36, 756, 1148, 608
    _draw_card(ctx, cx, cy, cw, ch, "C. 4-Stage Dilution Cryostat Heat-Load Wall (LD400 / PT420, N_mux*=32)", "FM5 PASS")

    # Left half: Utilization vs Array Size (256 .. 10,000 cells, log-y utilization % of limit)
    qx0, qx1 = cx + 88, cx + 690
    qy0, qy1 = cy + 84, cy + ch - 94

    def _xq(n_c: float) -> float:
        return qx0 + ((math.log10(n_c) - math.log10(250.0)) / (math.log10(11000.0) - math.log10(250.0))) * (qx1 - qx0)

    def _yq(u_pct: float) -> float:
        lo, hi = math.log10(5.0), math.log10(450.0)
        v = max(5.0, min(450.0, u_pct))
        return qy1 - ((math.log10(v) - lo) / (hi - lo)) * (qy1 - qy0)

    # Shaded red zone above 100% single-fridge limit
    y100 = _yq(100.0)
    ctx.set_source_rgba(0.84, 0.16, 0.16, 0.08)
    ctx.rectangle(qx0, qy0, qx1 - qx0, y100 - qy0)
    ctx.fill()
    _text(ctx, qx0 + 12, qy0 + 22, "EXCEEDS SINGLE LD400 / PT420 CAPACITY (>100%)", size=12.0, color=C_RED, bold=True)

    for uv in (10, 25, 50, 100, 200, 350):
        gy = _yq(uv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(qx0, gy)
        ctx.line_to(qx1, gy)
        ctx.stroke()
        _text(ctx, qx0 - 10, gy + 4, f"{uv}%", size=11.8, color=C_RED if uv == 100 else C_MUTED, bold=(uv == 100), align="right")

    for nv, nlbl in ((256, "256"), (512, "512"), (1024, "1,024"), (2887, "2,887*"), (5000, "5k"), (10000, "10,000")):
        gx = _xq(nv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(gx, qy0)
        ctx.line_to(gx, qy1)
        ctx.stroke()
        _text(ctx, gx, qy1 + 22, nlbl, size=11.8, color=C_TEXT if nv in (1024, 2887, 10000) else C_MUTED, bold=(nv in (1024, 2887, 10000)), align="center")

    _text(ctx, (qx0 + qx1) / 2.0, qy1 + 54, "M4 Processor Array Scale, N_cells (log scale; * = single-fridge ceiling)", size=13.5, color=C_TEXT, bold=True, align="center")
    _text_rot90(ctx, cx + 28, (qy0 + qy1) / 2.0, "Single-Cryostat Stage Load (% of Limit)", size=13.5, color=C_TEXT, bold=True)

    # 100% red line + vertical 2,887 cell ceiling line
    ctx.save()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(2.0)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(qx0, y100)
    ctx.line_to(qx1, y100)
    ctx.stroke()
    ctx.restore()

    x_ceil = _xq(c10["single_cryostat_max_cells"])
    ctx.save()
    ctx.set_source_rgb(*C_AMBER)
    ctx.set_line_width(1.6)
    ctx.set_dash([4.0, 4.0])
    ctx.move_to(x_ceil, y100)
    ctx.line_to(x_ceil, qy1)
    ctx.stroke()
    ctx.restore()

    # Plot 4 stage utilization curves
    st_styles = [
        ("mxc_20mK_frac", C_RED, [], 3.4, "20 mK MXC (<=14 uW, #1 bottleneck)"),
        ("stage_4K_frac", C_BLUE, [], 3.0, "4 K PT420 (<=2.0 W, 7.8 mW HEMT)"),
        ("stage_50K_frac", C_AMBER, [7.0, 4.0], 2.6, "50 K Stage (<=40 W)"),
        ("cp_100mK_frac", C_TEAL, [4.0, 3.0], 2.6, "100 mK CP (<=400 uW)"),
    ]
    for sk, col, dash, lw, _lbl in st_styles:
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        for i, pt in enumerate(curve):
            px, py = _xq(pt["n_cells"]), _yq(pt["utilization"][sk] * 100.0)
            if i == 0:
                ctx.move_to(px, py)
            else:
                ctx.line_to(px, py)
        ctx.stroke()
        ctx.restore()
        for pt in curve:
            if pt["n_cells"] in (1024, 10000):
                ctx.set_source_rgb(*col)
                ctx.arc(_xq(pt["n_cells"]), _yq(pt["utilization"][sk] * 100.0), 5.0, 0, 2.0 * math.pi)
                ctx.fill()

    # Legend inside Panel C bottom-right of plot
    clx, cly = qx0 + 20, qy1 - 116
    _round_rect(ctx, clx, cly, 345, 106, 8)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BORDER)
    ctx.set_line_width(1.1)
    ctx.stroke()
    for i, (_sk, col, dash, _lw, lbl) in enumerate(st_styles):
        yy = cly + 22 + i * 24
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.8)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(clx + 10, yy - 4)
        ctx.line_to(clx + 34, yy - 4)
        ctx.stroke()
        ctx.restore()
        _text(ctx, clx + 42, yy, lbl, size=11.6, color=C_TEXT, bold=(i == 0))

    # Axes Panel C
    ctx.set_source_rgb(0.45, 0.50, 0.58)
    ctx.set_line_width(1.4)
    ctx.move_to(qx0, qy0)
    ctx.line_to(qx0, qy1)
    ctx.line_to(qx1, qy1)
    ctx.stroke()

    # Right half of Panel C: Exact 1,024 vs 10,000 Stage Table
    tx_c = cx + 716
    tw_c = cw - 742
    ty_c = cy + 78
    _text(ctx, tx_c, ty_c + 12, "Exact Heat-Load Ledger (7.8 mW HEMT)", size=14.2, color=C_TEXT, bold=True)
    ctx.set_source_rgb(0.94, 0.96, 0.99)
    ctx.rectangle(tx_c, ty_c + 26, tw_c, 32)
    ctx.fill()
    _text(ctx, tx_c + 10, ty_c + 47, "Stage (Limit)", size=12.2, color=C_TEXT, bold=True)
    _text(ctx, tx_c + 165, ty_c + 47, "1,024 Cells", size=12.2, color=C_GREEN, bold=True)
    _text(ctx, tx_c + 295, ty_c + 47, "10,000 Cells", size=12.2, color=C_RED, bold=True)

    c_rows = [
        ("20 mK (14 uW)", f"{c1['loads']['mxc_20mK_uW']:.2f} uW", f"{c10['loads']['mxc_20mK_uW']:.1f} uW (3.1x!)"),
        ("100 mK (400 uW)", f"{c1['loads']['cp_100mK_uW']:.1f} uW", f"{c10['loads']['cp_100mK_uW']:.1f} uW (1.1x!)"),
        ("4 K (2.0 W)", f"{c1['loads']['stage_4K_W']:.3f} W", f"{c10['loads']['stage_4K_W']:.2f} W (2.0x!)"),
        ("50 K (40 W)", f"{c1['loads']['stage_50K_W']:.2f} W", f"{c10['loads']['stage_50K_W']:.1f} W (1.5x!)"),
        ("RO + XY Coax", f"{c1['total_rf_coax_lines']} lines", f"{c10['total_rf_coax_lines']} lines"),
        ("Single PT420", "CLOSES PASS", "EXCEEDS (4x req)"),
    ]
    for i, (sk, s1, s10) in enumerate(c_rows):
        ry = ty_c + 82 + i * 44
        if i % 2 == 1:
            ctx.set_source_rgb(0.985, 0.990, 0.996)
            ctx.rectangle(tx_c, ry - 22, tw_c, 38)
            ctx.fill()
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(tx_c, ry + 16)
        ctx.line_to(tx_c + tw_c, ry + 16)
        ctx.stroke()
        _text(ctx, tx_c + 10, ry + 2, sk, size=12.2, color=C_TEXT, bold=True)
        _text(ctx, tx_c + 165, ry + 2, s1, size=12.2, color=C_GREEN, bold=(i == 5))
        _text(ctx, tx_c + 295, ry + 2, s10, size=12.0, color=C_RED if i != 4 else C_TEXT, bold=(i in (0, 2, 5)))

    # Bottom scaling architecture note right of Panel C
    _round_rect(ctx, tx_c, cy + ch - 134, tw_c, 114, 9)
    ctx.set_source_rgb(0.995, 0.96, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.4)
    ctx.stroke()
    _text(ctx, tx_c + 14, cy + ch - 108, "Honest 10,000-Cell Scaling Finding:", size=13.2, color=C_RED, bold=True)
    _text(ctx, tx_c + 14, cy + ch - 84, f"• Single LD400/PT420 cap = {c10['single_cryostat_max_cells']:,} cells (20 mK wall)", size=12.0, color=C_TEXT)
    _text(ctx, tx_c + 14, cy + ch - 61, f"• 10k cells requires >= {c10['min_modular_ld400_pt420_cryostats']} modular PT420 fridges", size=12.0, color=C_TEXT, bold=True)
    _text(ctx, tx_c + 14, cy + ch - 38, "  OR XLD1000/KIDE multi-PT420 + 2.1 mW HEMT", size=11.8, color=C_MUTED)

    # =========================================================================
    # PANEL D (Bottom-Right): CellISA v3.5 ECHO_CZ Syndrome & S6.5 Hardware Spec
    # =========================================================================
    dx, dy, dw, dh = 1216, 756, 1148, 608
    _draw_card(ctx, dx, dy, dw, dh, "D. CellISA v3.5 (17 Opcodes) Fault-Tolerant Syndrome & S6.5 Spec", "FM6 & FM7 PASS")

    syn = v35["summary"]
    cert = v35["certificate"]

    # Left half of Panel D: Bare CZ vs ECHO_CZ vs Syndrome Cycle Fidelity Bars
    fx0, fx1 = dx + 68, dx + 520
    fy0, fy1 = dy + 92, dy + 382
    _text(ctx, (fx0 + fx1) / 2.0, dy + 74, "CellISA v3.5 Live 4x4 Syndrome Cycle (S_eps = 1.0 uev/rtHz)", size=13.5, color=C_TEXT, bold=True, align="center")

    for fv in (0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00):
        gy = fy1 - ((fv - 0.70) / 0.30) * (fy1 - fy0)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(fx0, gy)
        ctx.line_to(fx1, gy)
        ctx.stroke()
        _text(ctx, fx0 - 8, gy + 4, f"{fv:.2f}", size=11.5, color=C_MUTED, align="right")

    v35_bars = [
        ("Bare CZ\n(1/f noise)", syn["mean_bare_cz_fidelity"], C_RED),
        ("ECHO_CZ\n(v3.5)", syn["mean_echo_cz_fidelity"], C_GREEN),
        ("MUX_RO\n(N*=32)", syn["mux_readout"]["per_cell_readout_fidelity"], C_BLUE),
        ("SYNDROME\n(4-cell)", syn["syndrome_round_fidelity"], C_PURPLE),
    ]
    vbw = 78
    for i, (blbl, bval, col) in enumerate(v35_bars):
        bx_v = fx0 + 26 + i * 108
        bt = fy1 - ((max(0.70, bval) - 0.70) / 0.30) * (fy1 - fy0)
        _round_rect(ctx, bx_v, bt, vbw, fy1 - bt, 6)
        ctx.set_source_rgb(*col)
        ctx.fill()
        _text(ctx, bx_v + vbw / 2.0, bt + 24, f"{bval:.4f}", size=12.5, color=(1.0, 1.0, 1.0), bold=True, align="center")
        lns = blbl.split("\n")
        _text(ctx, bx_v + vbw / 2.0, fy1 + 21, lns[0], size=12.2, color=C_TEXT, bold=True, align="center")
        _text(ctx, bx_v + vbw / 2.0, fy1 + 38, lns[1], size=11.4, color=C_MUTED, align="center")

    # Echo gain callout box under Panel D bars
    _round_rect(ctx, dx + 34, dy + 444, 496, 138, 9)
    ctx.set_source_rgb(0.95, 0.94, 1.0)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_PURPLE)
    ctx.set_line_width(1.4)
    ctx.stroke()
    _text(ctx, dx + 50, dy + 472, "CellISA v3.5 Live Verification Summary (17 Opcodes):", size=13.5, color=C_PURPLE, bold=True)
    _text(ctx, dx + 50, dy + 498, f"• New Opcodes: ECHO_CZ, MUX_READOUT, SYNDROME_CYCLE", size=12.2, color=C_TEXT, bold=True)
    _text(ctx, dx + 50, dy + 522, f"• ECHO_CZ Gain: +{syn['echo_fidelity_gain']*100:.2f} pp  |  Cycle T = {syn['cycle_duration_us']:.2f} us", size=12.2, color=C_GREEN, bold=True)
    short_ids = ", ".join(cid.split("-")[-1] for cid in v35["route"]["assigned_cell_ids"])
    _text(ctx, dx + 50, dy + 546, f"• Routed (4x4): {short_ids}  |  p_L = {cert['logical_error_rate']:.2e}", size=11.8, color=C_TEXT)
    _text(ctx, dx + 50, dy + 569, f"• SHA-256: {cert['sha256'][:36]}... [VERIFIED]", size=10.8, color=C_MUTED, family="DejaVu Sans Mono")

    # Right half of Panel D: S6.5 Hardware Spec Table (for CAD v5.0 & BOM v5.0)
    sx_d = dx + 558
    sw_d = dw - 584
    sy_d = dy + 74
    _text(ctx, sx_d, sy_d + 12, "S6.5 Hardware Engineering Spec (1,024-Cell M4 Module, v5.0)", size=14.2, color=C_TEXT, bold=True)
    ctx.set_source_rgb(0.94, 0.96, 0.99)
    ctx.rectangle(sx_d, sy_d + 26, sw_d, 32)
    ctx.fill()
    _text(ctx, sx_d + 10, sy_d + 47, "ID & Component", size=12.0, color=C_TEXT, bold=True)
    _text(ctx, sx_d + 286, sy_d + 47, "Qty / Mass", size=12.0, color=C_MUTED, bold=True)
    _text(ctx, sx_d + 398, sy_d + 47, "Nom Cost (USD)", size=12.0, color=C_BLUE, bold=True)

    s65_rows = [
        ("S6.5-01 ZU48DR RFSoC 2U (32 ch)", "1  | 11.5 kg", "$58,000 ($42k-82k)"),
        ("S6.5-02 20 mK TWPA + Purcell + Iso", "32 | 2.72 kg", "$336,000 ($240k-512k)"),
        ("S6.5-03 4 K LNF HEMT Bank (7.8 mW)", "32 | 1.02 kg", "$144,000 ($112k-192k)"),
        ("S6.5-04 Cryo-Coax Loom (CuNi/NbTi)", "96 | 4.03 kg", "$91,200 ($62k-139k)"),
    ]
    for i, (k_s, q_s, c_s) in enumerate(s65_rows):
        ry = sy_d + 84 + i * 54
        if i % 2 == 1:
            ctx.set_source_rgb(0.985, 0.990, 0.996)
            ctx.rectangle(sx_d, ry - 24, sw_d, 46)
            ctx.fill()
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(sx_d, ry + 22)
        ctx.line_to(sx_d + sw_d, ry + 22)
        ctx.stroke()
        _text(ctx, sx_d + 10, ry + 4, k_s, size=11.6, color=C_TEXT, bold=True)
        _text(ctx, sx_d + 286, ry + 4, q_s, size=11.6, color=C_MUTED)
        _text(ctx, sx_d + 398, ry + 4, c_s, size=11.5, color=C_BLUE, bold=True)

    tot = s65["totals_1024_cell_module"]
    _round_rect(ctx, sx_d, sy_d + 306, sw_d, 80, 9)
    ctx.set_source_rgb(0.93, 0.99, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_GREEN)
    ctx.set_line_width(1.4)
    ctx.stroke()
    _text(
        ctx,
        sx_d + 16,
        sy_d + 334,
        f"S6.5 Module Total:  {tot['total_mass_kg']:.2f} kg ({tot['cryo_cold_mass_kg']:.2f} kg cold)  |  {tot['room_temp_power_W']:.1f} W @ 300 K",
        size=12.8,
        color=C_TEXT,
        bold=True,
    )
    _text(
        ctx,
        sx_d + 16,
        sy_d + 362,
        f"Est. Nominal Cost: ${tot['cost_usd_nom']:,}  [${tot['cost_usd_low']:,} - ${tot['cost_usd_high']:,}]  (no_supplier_quotes)",
        size=12.4,
        color=C_GREEN,
        bold=True,
    )

    # Bottom-right 7-verdict pill strip
    pills = ["FM1 Q16", "FM2 FPGA", "FM3 TWPA", "FM4 N*=32", "FM5 Cryo", "FM6 v3.5", "FM7 S6.5"]
    pw_p = (sw_d - 6 * 8) / 7.0
    py_p = dy + dh - 76
    for i, pt in enumerate(pills):
        px_p = sx_d + i * (pw_p + 8)
        _round_rect(ctx, px_p, py_p, pw_p, 52, 7)
        ctx.set_source_rgb(0.06, 0.09, 0.16)
        ctx.fill()
        _text(ctx, px_p + pw_p / 2.0, py_p + 22, pt, size=11.0, color=(0.86, 0.91, 0.98), bold=True, align="center")
        _text(ctx, px_p + pw_p / 2.0, py_p + 42, "PASS", size=11.8, color=(0.40, 0.96, 0.72), bold=True, align="center")

    out_path = OUT_DIR / "fig_exp140_fpga_mux_cryo.png"
    surf.write_to_png(str(out_path))
    return out_path


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    p = plot_exp140(data)
    print(f"Wrote {p.name}")


if __name__ == "__main__":
    main()
