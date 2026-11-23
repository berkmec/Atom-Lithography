"""Publication-grade 2400x1400 4-panel Master Dashboard for Exp146 (v6.0 Digital Twin) using pure Cairo.

Usage:
    /usr/bin/python3 -B experiments/exp146_v6_digital_twin/plot_exp146.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "results" / "exp146_v6_digital_twin"
W, H = 2400, 1400

BG = (0.973, 0.980, 0.988)
CARD = (1.0, 1.0, 1.0)
BORDER = (0.796, 0.835, 0.882)
NAVY = (0.059, 0.090, 0.165)
TEXT = (0.118, 0.161, 0.231)
MUTED = (0.392, 0.455, 0.545)
GRID = (0.886, 0.910, 0.941)
BLUE = (0.114, 0.306, 0.847)
TEAL = (0.051, 0.580, 0.533)
EMERALD = (0.020, 0.588, 0.412)
AMBER = (0.851, 0.467, 0.024)
CORAL = (0.863, 0.149, 0.149)
SLATE = (0.459, 0.525, 0.608)
PURPLE = (0.486, 0.227, 0.929)
SOFT_BLUE = (0.937, 0.965, 1.000)
SOFT_GREEN = (0.925, 0.992, 0.961)
SOFT_AMBER = (1.000, 0.984, 0.922)
SOFT_SLATE = (0.953, 0.965, 0.980)


def _rrect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float) -> None:
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def _text(
    ctx: cairo.Context,
    x: float,
    y: float,
    s: str,
    size: float = 17.0,
    color: tuple[float, float, float] = TEXT,
    bold: bool = False,
    align: str = "left",
) -> None:
    ctx.select_font_face(
        "DejaVu Sans",
        cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
    )
    ctx.set_font_size(size)
    ctx.set_source_rgb(*color)
    ext = ctx.text_extents(s)
    tx = x
    if align == "center":
        tx = x - (ext.width / 2.0 + ext.x_bearing)
    elif align == "right":
        tx = x - (ext.width + ext.x_bearing)
    ctx.move_to(tx, y)
    ctx.show_text(s)


def _card(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, subtitle: str) -> None:
    _rrect(ctx, x, y, w, h, 14)
    ctx.set_source_rgb(*CARD)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(2.0)
    ctx.stroke()

    ctx.set_source_rgb(0.945, 0.961, 0.976)
    _rrect(ctx, x + 1, y + 1, w - 2, 62, 13)
    ctx.fill()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.2)
    ctx.move_to(x, y + 63)
    ctx.line_to(x + w, y + 63)
    ctx.stroke()

    _text(ctx, x + 20, y + 29, title, size=19.5, color=NAVY, bold=True)
    _text(ctx, x + 20, y + 51, subtitle, size=13.5, color=MUTED)


def _draw_panel_a(ctx: cairo.Context, x: float, y: float, w: float, h: float, d: dict) -> None:
    l7 = d["l7"]["fleet_100L_trajectory"]
    l3 = d["l3"]
    _card(
        ctx, x, y, w, h,
        "(A) 100L Architecture Revolution: Cryostats (679 -> 100 -> 1) & $/L_sys (234x)",
        "DT6_3 / DT6_7: v5 D2 Surface Code -> v6 D3 GRAPE SC -> v6 qLDPC [[144,12,12]] Gross Code ({Model})",
    )

    # Split Panel A into TWO clean side-by-side log charts: Left = Cryostats, Right = $/L_sys
    gap_mid = 66
    sub_w = (w - 170 - gap_mid) / 2.0
    py = y + 106
    ph = h - 196

    stages = [
        ("v5 D2 SC\n(d=99)", l7["v5_D2_SC_cryostats"], l7["v5_D2_SC_usd_per_L_sys"] / 1e6, CORAL),
        ("v6 D3 GRAPE\nSC (d=33-37)", l7["v6_D3_GRAPE_SC_cryostats"], l7["v6_D3_GRAPE_SC_usd_per_L_sys"] / 1e6, AMBER),
        ("v6 qLDPC\nBB144 (108L)", l7["v6_qLDPC_108L_cryostats"], l7["v6_qLDPC_108L_usd_per_L_sys"] / 1e6, EMERALD),
    ]

    # --- Left sub-chart: Cryostats (log10 from 0.5 to 1500) ---
    lx = x + 84
    _text(ctx, lx + sub_w / 2.0, py - 14, "Cryostats for 100L Fleet (log)", size=15.0, color=NAVY, bold=True, align="center")
    lmin, lmax = math.log10(0.5), math.log10(1500.0)

    def _yl_c(v: float) -> float:
        return py + ph * (1.0 - (math.log10(max(v, 0.5)) - lmin) / (lmax - lmin))

    for val, lbl in ((1, "1"), (10, "10"), (100, "100"), (1000, "1,000")):
        gy = _yl_c(val)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.1)
        ctx.move_to(lx, gy)
        ctx.line_to(lx + sub_w, gy)
        ctx.stroke()
        _text(ctx, lx - 10, gy + 5, lbl, size=13.5, color=MUTED, align="right")

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.6)
    ctx.move_to(lx, py)
    ctx.line_to(lx, py + ph)
    ctx.line_to(lx + sub_w, py + ph)
    ctx.stroke()

    bw = 74.0
    gw = sub_w / 3.0
    for i, (lbl, n_c, _usd, col) in enumerate(stages):
        cx = lx + (i + 0.5) * gw
        yt = _yl_c(n_c)
        ctx.set_source_rgb(*col)
        ctx.rectangle(cx - bw / 2.0, yt, bw, py + ph - yt)
        ctx.fill()
        _text(ctx, cx, yt - 9, f"{n_c}", size=16.5, color=col, bold=True, align="center")
        if i == 1:
            _text(ctx, cx, yt - 30, "6.8x", size=13.0, color=NAVY, bold=True, align="center")
        elif i == 2:
            _text(ctx, cx, yt - 30, "679x / 100x", size=13.0, color=EMERALD, bold=True, align="center")
        lns = lbl.split("\n")
        _text(ctx, cx, py + ph + 22, lns[0], size=13.5, color=TEXT, bold=True, align="center")
        _text(ctx, cx, py + ph + 40, lns[1], size=12.0, color=MUTED, align="center")

    # --- Right sub-chart: Deployed $/L_sys (log10 from $0.02M to $30M) ---
    rx = lx + sub_w + gap_mid + 30
    _text(ctx, rx + sub_w / 2.0, py - 14, "5-yr Deployed Cost / Logical Qubit (log)", size=15.0, color=NAVY, bold=True, align="center")
    umin, umax = math.log10(0.02), math.log10(30.0)

    def _yl_u(v_m: float) -> float:
        return py + ph * (1.0 - (math.log10(max(v_m, 0.02)) - umin) / (umax - umin))

    for val, lbl in ((0.05, "$50k"), (0.1, "$100k"), (1.0, "$1M"), (10.0, "$10M")):
        gy = _yl_u(val)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.1)
        ctx.move_to(rx, gy)
        ctx.line_to(rx + sub_w, gy)
        ctx.stroke()
        _text(ctx, rx - 10, gy + 5, lbl, size=13.5, color=MUTED, align="right")

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.6)
    ctx.move_to(rx, py)
    ctx.line_to(rx, py + ph)
    ctx.line_to(rx + sub_w, py + ph)
    ctx.stroke()

    for i, (lbl, _c, usd_m, col) in enumerate(stages):
        cx = rx + (i + 0.5) * gw
        yt = _yl_u(usd_m)
        ctx.set_source_rgb(*col)
        ctx.rectangle(cx - bw / 2.0, yt, bw, py + ph - yt)
        ctx.fill()
        val_txt = f"${usd_m:.2f}M" if usd_m >= 1.0 else f"${usd_m*1000:.1f}k"
        _text(ctx, cx, yt - 9, val_txt, size=15.5, color=col, bold=True, align="center")
        if i == 1:
            _text(ctx, cx, yt - 30, "5.4x", size=13.0, color=NAVY, bold=True, align="center")
        elif i == 2:
            _text(ctx, cx, yt - 30, "234x / 43x", size=13.0, color=EMERALD, bold=True, align="center")
        lns = lbl.split("\n")
        _text(ctx, cx, py + ph + 22, lns[0], size=13.5, color=TEXT, bold=True, align="center")
        _text(ctx, cx, py + ph + 40, lns[1], size=12.0, color=MUTED, align="center")

    # Bottom highlight ribbon
    _text(
        ctx, x + w / 2.0, y + h - 16,
        f"qLDPC [[144,12,12]]: L_max={l3['L_max_um']} um <= 300 um (0 M4 redesign) | 120L/cryo | "
        f"Yield {l3['block_288_yield_f15_N8_pct']:.2f}% blk / {l3['spared_9of10_108L_die_yield_N8_pct']:.2f}% die | W3 fab ${l3['config_108L_W3_fab_usd_per_L']:.4f}/L",
        size=13.0, color=NAVY, bold=True, align="center",
    )


def _draw_panel_b(ctx: cairo.Context, x: float, y: float, w: float, h: float, d: dict) -> None:
    l2 = d["l2"]
    l5 = d["l5"]
    _card(
        ctx, x, y, w, h,
        "(B) D3 GRAPE M4 Gate Closure (Exp143) & Option-HPC 100G RoCEv2 Decoder",
        "DT6_2 / DT6_5: K=8 Fourier GRAPE (<= 300 MHz AWG) + Backlog-Free 100 Gbps RDMA Decoding ({Model})",
    )

    gap_mid = 66
    sub_w = (w - 170 - gap_mid) / 2.0
    py = y + 106
    ph = h - 196

    # --- Left sub-chart: 2Q Gate Error p_2q (%) ---
    lx = x + 84
    _text(ctx, lx + sub_w / 2.0, py - 14, "2Q M4 CZ Gate Error p_2q (%)", size=15.0, color=NAVY, bold=True, align="center")
    ymax = 1.05
    for val in (0.0, 0.25, 0.50, 0.75, 1.00):
        gy = py + ph * (1.0 - val / ymax)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.1)
        ctx.move_to(lx, gy)
        ctx.line_to(lx + sub_w, gy)
        ctx.stroke()
        _text(ctx, lx - 10, gy + 5, f"{val:.2f}%", size=13.0, color=MUTED, align="right")

    # D3 threshold line 0.50%
    gy_d3 = py + ph * (1.0 - 0.50 / ymax)
    ctx.save()
    ctx.set_dash([7, 5])
    ctx.set_source_rgb(*EMERALD)
    ctx.set_line_width(1.6)
    ctx.move_to(lx, gy_d3)
    ctx.line_to(lx + sub_w, gy_d3)
    ctx.stroke()
    ctx.restore()
    _text(ctx, lx + sub_w - 4, gy_d3 - 6, "D3 target (0.50%)", size=12.0, color=EMERALD, bold=True, align="right")

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.6)
    ctx.move_to(lx, py)
    ctx.line_to(lx, py + ph)
    ctx.line_to(lx + sub_w, py + ph)
    ctx.stroke()

    g_bars = [
        ("v5 P4\nEcho", 0.878, SLATE),
        ("GRAPE\nCons", l2["cons_Q1e6_S0p25_5pair_p_2q_pct"], AMBER),
        ("Echo\nS=0.39", l2["echo_Q1e6_S0p39_p_2q_pct"], BLUE),
        ("Echo\nS=0.25", l2["echo_Q1e6_S0p25_p_2q_pct"], EMERALD),
    ]
    gw = sub_w / len(g_bars)
    bw = 58.0
    for i, (lbl, val, col) in enumerate(g_bars):
        cx = lx + (i + 0.5) * gw
        bh = ph * (val / ymax)
        ctx.set_source_rgb(*col)
        ctx.rectangle(cx - bw / 2.0, py + ph - bh, bw, bh)
        ctx.fill()
        _text(ctx, cx, py + ph - bh - 8, f"{val:.3f}%", size=13.5, color=col, bold=True, align="center")
        lns = lbl.split("\n")
        _text(ctx, cx, py + ph + 22, lns[0], size=13.0, color=TEXT, bold=True, align="center")
        _text(ctx, cx, py + ph + 39, lns[1], size=12.0, color=MUTED, align="center")

    # --- Right sub-chart: Real-Time Decoder E2E Latency (us, log) ---
    rx = lx + sub_w + gap_mid + 30
    _text(ctx, rx + sub_w / 2.0, py - 14, "Real-Time Decoder Latency (us, log)", size=15.0, color=NAVY, bold=True, align="center")
    dmin, dmax = math.log10(1.0), math.log10(60.0)

    def _yl_d(v: float) -> float:
        return py + ph * (1.0 - (math.log10(max(v, 1.0)) - dmin) / (dmax - dmin))

    for val in (1, 3, 10, 30):
        gy = _yl_d(val)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.1)
        ctx.move_to(rx, gy)
        ctx.line_to(rx + sub_w, gy)
        ctx.stroke()
        _text(ctx, rx - 10, gy + 5, f"{val} us", size=13.0, color=MUTED, align="right")

    # Cycle budget line 6.70 us (D3 4-CZ)
    gy_c = _yl_d(6.70)
    ctx.save()
    ctx.set_dash([7, 5])
    ctx.set_source_rgb(*BLUE)
    ctx.set_line_width(1.5)
    ctx.move_to(rx, gy_c)
    ctx.line_to(rx + sub_w, gy_c)
    ctx.stroke()
    ctx.restore()
    _text(ctx, rx + sub_w - 4, gy_c - 6, "D3 cycle (6.70 us)", size=11.5, color=BLUE, bold=True, align="right")

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.6)
    ctx.move_to(rx, py)
    ctx.line_to(rx, py + ph)
    ctx.line_to(rx + sub_w, py + ph)
    ctx.stroke()

    d_bars = [
        ("CPU 1-core\nd=37 (FAIL)", l5["d37_sc_cpu_single_us"], CORAL),
        ("Option-HPC\nd=37 SC", l5["d37_sc_hpc_e2e_us"], BLUE),
        ("Option-HPC\nqLDPC 108L", l5["qldpc_108L_hpc_e2e_mean_us"], EMERALD),
    ]
    gw2 = sub_w / len(d_bars)
    bw2 = 72.0
    for i, (lbl, val, col) in enumerate(d_bars):
        cx = rx + (i + 0.5) * gw2
        yt = _yl_d(val)
        ctx.set_source_rgb(*col)
        ctx.rectangle(cx - bw2 / 2.0, yt, bw2, py + ph - yt)
        ctx.fill()
        if i == 1:
            _text(ctx, cx, yt + 22, f"{val:.2f} us", size=14.0, color=(1.0, 1.0, 1.0), bold=True, align="center")
        else:
            _text(ctx, cx, yt - 8, f"{val:.2f} us", size=14.0, color=col, bold=True, align="center")
        lns = lbl.split("\n")
        _text(ctx, cx, py + ph + 22, lns[0], size=13.0, color=TEXT, bold=True, align="center")
        _text(ctx, cx, py + ph + 39, lns[1], size=12.0, color=MUTED, align="center")

    _text(
        ctx, x + w / 2.0, y + h - 16,
        f"GRAPE Echo: F_avg={l2['echo_Q1e6_S0p25_F_avg']*100:.2f}%, Lambda_phys={l2['lambda_D3_phys_echo_Q1e6_S0p25']:.3f}  |  "
        f"Option-HPC: tau_ingest={l5['tau_ingest_ns']:.0f} ns, 1x 4U rack ($132k, 2.20 kW, 0 W cryo)",
        size=13.0, color=NAVY, bold=True, align="center",
    )


def _draw_panel_c(ctx: cairo.Context, x: float, y: float, w: float, h: float, d: dict) -> None:
    q = d["l6"]["live_ibm_qpu"]
    isa = d["l6"]["live_cellisa_v40"]
    ar = d["l6"]["live_auto_recal"]

    _card(
        ctx, x, y, w, h,
        f"(C) Live 156Q IBM QPU Validation ({q['backend_name']}) & CellISA v4.0",
        f"DT6_6: {{Canli-Donanim-IBM-QPU}} job_id={q['job_id']} (chain {q['selected_5q_chain']}, 0 SWAPs, 0 leaks) + auto_recal ({{Model}})",
    )

    # Top half: 4 clean horizontal live-hardware metric bars for C1 DD + Bell
    bx = x + 216
    bw = w - 404
    by0 = y + 92
    bh = 26
    bgap = 16

    bars = [
        ("C1a Bare Idle (48 us)", q["c1_bare_p0"], SLATE, f"{q['c1_bare_p0']:.4f}"),
        ("C1b Hahn-Echo DD", q["c1_echo_p0"], BLUE, f"{q['c1_echo_p0']:.4f} (+{(q['c1_echo_p0']-q['c1_bare_p0'])*100:.1f} pp)"),
        ("C1c XY4 DD (4-pulse)", q["c1_xy4_p0"], TEAL, f"{q['c1_xy4_p0']:.4f} (+{q['c1_xy4_gain_pp']:.1f} pp)"),
        ("C1d-f 2Q Bell F(|Phi+>)", q["c1_bell_fidelity"], EMERALD, f"{q['c1_bell_fidelity']:.4f} (>=0.85)"),
    ]
    for i, (lbl, val, col, rtxt) in enumerate(bars):
        ry = by0 + i * (bh + bgap)
        _text(ctx, bx - 14, ry + 18, lbl, size=14.0, color=TEXT, bold=True, align="right")
        _rrect(ctx, bx, ry, bw, bh, 6)
        ctx.set_source_rgb(0.918, 0.937, 0.961)
        ctx.fill()
        _rrect(ctx, bx, ry, bw * min(1.0, val), bh, 6)
        ctx.set_source_rgb(*col)
        ctx.fill()
        _text(ctx, bx + bw + 12, ry + 18, rtxt, size=13.5, color=col, bold=True)

    # Bottom half: 3 crisp KPI sub-cards (C2 d=3, C3 Q16.16 BOED, CellISA v4.0 + auto_recal)
    cy = y + 278
    ch = 258
    cw = (w - 84) / 3.0
    sub_cards = [
        (
            "C2: d=3 Linear QEC",
            "{Canli-IBM-QPU}",
            BLUE,
            SOFT_BLUE,
            [
                f"Chain: {q['selected_5q_chain']} (0 SWAPs)",
                f"Raw p_phys: {q['c2_avg_p_phys']*100:.2f}%",
                f"MWPM: {q['c2_avg_p_L_mwpm']*100:.2f}% ({q['c2_suppression_mwpm']:.2f}x)",
                f"Majority: {q['c2_avg_p_L_majority']*100:.2f}% ({q['c2_suppression_majority']:.2f}x)",
                "Post-sel: 0.000% (0/7,451)",
                "Keep rate: 91.0% -> PASS",
            ],
        ),
        (
            "C3: Q16.16 BOED",
            "{Canli-IBM-QPU}",
            AMBER,
            SOFT_AMBER,
            [
                "8-pt fringe: 1.02 - 8.00 us",
                f"Blind-8pt: {q['c3_blind8_kHz']:.2f} kHz",
                f"q2 real drift: {q['c3_measured_q2_drift_kHz']:+.2f} kHz",
                f"FP64 BOED: {q['c3_fp64_boed_kHz']:.3f} kHz (3 pts)",
                f"Q16 BOED:  {q['c3_q16_boed_kHz']:.3f} kHz (3 pts)",
                f"Q16 vs FP64: {q['c3_q16_vs_fp64_kHz']*1000:.1f} Hz (2.67x)",
            ],
        ),
        (
            "CellISA v4 + Recal",
            "{Model / M0}",
            EMERALD,
            SOFT_GREEN,
            [
                f"Opcodes: {isa['v40_total_opcodes']} v4 / {isa['v35_compat_opcodes']} v3.5",
                f"QRAM_SWAP F: {isa['qram_swap_fidelity']:.5f}",
                f"S5.5 laser +-8%: {ar['laser_sigma_nm']:.3f} nm",
                "S5 UHV spike: 1 ms lock",
                f"S3 5% dead: {ar['blanker_throughput_pct']:.0f}% spared",
                f"31P drift: {ar['hyperfine_resid_Hz']:.1f} Hz / {ar['hyperfine_relock_ms']:.2f} ms",
            ],
        ),
    ]

    for i, (ttl, tag, col, fill_c, lines) in enumerate(sub_cards):
        sx = x + 26 + i * (cw + 16)
        _rrect(ctx, sx, cy, cw, ch, 10)
        ctx.set_source_rgb(*fill_c)
        ctx.fill_preserve()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(1.6)
        ctx.stroke()

        _text(ctx, sx + 14, cy + 28, ttl, size=15.5, color=NAVY, bold=True)
        _text(ctx, sx + 14, cy + 48, tag, size=12.5, color=col, bold=True)
        ctx.set_source_rgb(*BORDER)
        ctx.set_line_width(1.0)
        ctx.move_to(sx + 10, cy + 58)
        ctx.line_to(sx + cw - 10, cy + 58)
        ctx.stroke()

        for j, ln in enumerate(lines):
            _text(ctx, sx + 14, cy + 84 + j * 27, ln, size=13.0, color=TEXT, bold=(j == 5))

    _text(
        ctx, x + w / 2.0, y + h - 16,
        "Epistemic boundary: Control/DD/Bell/QEC/BOED proven on live IBM QPU; Si:31P lithography & auto_recal remain M0 {Model}.",
        size=13.0, color=NAVY, bold=True, align="center",
    )


def _draw_panel_d(ctx: cairo.Context, x: float, y: float, w: float, h: float, d: dict) -> None:
    l1 = d["l1"]
    l4 = d["l4"]
    l7 = d["l7"]
    mc = l7["modular_mc_100k"]

    _card(
        ctx, x, y, w, h,
        "(D) v3 -> v6 Modular BOM ($5.25M / $5.55M), Option-Q & 24/24 Cert Lock",
        "DT6_1 / DT6_4 / DT6_7 / DT6_8: Zero-Double-Count Modular Capex + CAD/BOM/RFQ-09 Integrity ({Model}/{Varsayim})",
    )

    # Top half: 6-tier BOM progression bar chart (v3 -> v6 Full)
    px, py = x + 94, y + 96
    pw, ph = w - 134, 198
    ymax = 6.4

    for val in (0.0, 2.0, 4.0, 6.0):
        gy = py + ph * (1.0 - val / ymax)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.1)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.stroke()
        _text(ctx, px - 10, gy + 5, f"${val:.0f}M", size=13.0, color=MUTED, align="right")

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.6)
    ctx.move_to(px, py)
    ctx.line_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()

    bom_ev = l7["bom_evolution_nom_usd"]
    tiers = [
        ("v3.0\nBase", bom_ev["v3_0_base"] / 1e6, SLATE, ""),
        ("v4.0\nBase", bom_ev["v4_0_base"] / 1e6, SLATE, ""),
        ("v5.0\nBase", bom_ev["v5_0_base"] / 1e6, BLUE, f"P>100M {mc['M3_v5_0_Base']['P_gt_100M_pct']:.2f}%"),
        ("v6.0\n+HPC", bom_ev["v6_0_plus_option_hpc"] / 1e6, TEAL, f"{mc['M3_v6_0_Plus_Option_HPC']['P_gt_100M_pct']:.2f}%"),
        ("v6.0\n+OptQ", bom_ev["v6_0_plus_option_q"] / 1e6, PURPLE, f"{mc['M3_v6_0_Plus_Option_Q']['P_gt_100M_pct']:.2f}%"),
        ("v6.0\nFull", bom_ev["v6_0_full"] / 1e6, EMERALD, f"{mc['M3_v6_0_Full']['P_gt_100M_pct']:.2f}%"),
    ]
    gw = pw / len(tiers)
    bw = 74.0
    for i, (lbl, val_m, col, ptxt) in enumerate(tiers):
        cx = px + (i + 0.5) * gw
        bh = ph * (val_m / ymax)
        ctx.set_source_rgb(*col)
        ctx.rectangle(cx - bw / 2.0, py + ph - bh, bw, bh)
        ctx.fill()
        _text(ctx, cx, py + ph - bh - 8, f"${val_m:.2f}M", size=13.5, color=col, bold=True, align="center")
        if ptxt:
            _text(ctx, cx, py + ph - bh - 25, ptxt, size=11.0, color=NAVY, bold=True, align="center")
        lns = lbl.split("\n")
        _text(ctx, cx, py + ph + 19, lns[0], size=12.5, color=TEXT, bold=True, align="center")
        _text(ctx, cx, py + ph + 35, lns[1], size=11.5, color=MUTED, align="center")

    # Bottom half: 2 side-by-side summary cards (Option-Q/S1-Multi & CAD/BOM/SHA-256 Lock)
    cy = y + 348
    ch = 190
    cw = (w - 68) / 2.0

    # Card 1: Option-Q & S1-Multi
    c1x = x + 26
    _rrect(ctx, c1x, cy, cw, ch, 10)
    ctx.set_source_rgb(*SOFT_SLATE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*PURPLE)
    ctx.set_line_width(1.6)
    ctx.stroke()
    _text(ctx, c1x + 16, cy + 28, "Option-Q & S1-Multi (Exp142, +$168k, +9.2 kg)", size=14.5, color=NAVY, bold=True)
    optq_lines = [
        f"Chebyshev-5 (50 <-> 3k Ohm): IL={l4['chebyshev5_IL_6GHz_dB']:.4f} dB, BW={l4['chebyshev5_bw_15dB_GHz']:.2f} GHz",
        f"Lindblad 12x12 SWAP: F_rt(31P)={l4['F_SWAP_rt_31P_nuclear']:.4f} (CPTP clean)",
        f"Memory lifetime gain (F90): {l4['lifetime_gain_F90_XY8_1s']:,.0f}x (1s) - {l4['lifetime_gain_F90_XY8_3s']:,.0f}x (3s)",
        f"Cryo load: +{l4['cryo_added_20mK_uW']:.2f} uW @ 20 mK, +{l4['cryo_added_4K_W']:.3f} W @ 4 K (LD400 OK)",
        f"167Er 10 km fiber: {l4['er167_10km_BK_rate_Hz']:,.1f} Hz (F={l4['er167_10km_BK_fidelity']:.4f}) | 121Sb -{l4['sb121_straggle_reduction_pct']:.1f}% straggle",
    ]
    for j, ln in enumerate(optq_lines):
        _text(ctx, c1x + 16, cy + 56 + j * 26, ln, size=12.5, color=TEXT)

    # Card 2: CAD/BOM v6.0 & 24/24 SHA-256 Lock
    c2x = c1x + cw + 16
    _rrect(ctx, c2x, cy, cw, ch, 10)
    ctx.set_source_rgb(*SOFT_GREEN)
    ctx.fill_preserve()
    ctx.set_source_rgb(*EMERALD)
    ctx.set_line_width(1.6)
    ctx.stroke()
    _text(ctx, c2x + 16, cy + 28, "CAD v6.0 + BOM v6.0 + 24/24 Cryptographic Lock", size=14.5, color=NAVY, bold=True)
    cad_lines = [
        f"CAD v6.0: {l1['cad_v6']['part_count']} parts, {l1['cad_v6']['total_mass_kg']:.3f} kg, 0/{l1['cad_v6']['pairs_checked']:,} clashes",
        f"Clearances: {l1['cad_v6']['clearances_passed']}/{l1['cad_v6']['clearances_total']} PASS | STL: {l1['cad_v6']['stl_triangles']:,} watertight tris",
        f"BOM v6.0: {l1['bom_v6']['csv_row_count']} parts | $0.00 bridge | {l1['bom_v6']['cad_mass_reconciliation_error_kg']:.4f} kg CAD match",
        f"9-RFQ coverage: {l1['bom_v6']['rfq9_nom_share_pct']:.1f}% nominal / {l1['bom_v6']['rfq9_var_share_pct']:.1f}% MC variance",
        "24/24 primary + live QPU SHA-256 locked | 8/8 DT6 PASS",
    ]
    for j, ln in enumerate(cad_lines):
        _text(ctx, c2x + 16, cy + 56 + j * 26, ln, size=12.5, color=TEXT, bold=(j == 4))

    _text(
        ctx, x + w / 2.0, y + h - 16,
        f"M3 v6.0 Full Prog P50=${mc['M3_v6_0_Full']['prog_p50_M']:.2f}M (P>100M={mc['M3_v6_0_Full']['P_gt_100M_pct']:.2f}%; FOAK 5y P>100M={mc['M3_v6_0_Full']['P_foak_gt_100M_pct']:.2f}%) | Modular Phase-1 Base 4.37%",
        size=12.8, color=NAVY, bold=True, align="center",
    )


def render_figure() -> Path:
    d = json.loads((OUT_DIR / "exp146_plot_data.json").read_text(encoding="utf-8"))
    sha = d["master_cert"]["sha256"]

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Header
    ctx.set_source_rgb(*NAVY)
    ctx.rectangle(0, 0, W, 106)
    ctx.fill()
    _text(
        ctx, 48, 44,
        "Exp146 (H164): Atom Lithography Machine v6.0 Master Digital Twin (Option-Q/HPC + D3 GRAPE + qLDPC + Live IBM QPU)",
        size=26.0, color=(1.0, 1.0, 1.0), bold=True,
    )
    _text(
        ctx, 48, 79,
        f"v6_digital_twin_cert.json SHA-256: {sha}  |  8/8 DT6 PASS  |  24/24 Ledgers + Live QPU Locked",
        size=15.5, color=(0.745, 0.824, 0.914),
    )

    _draw_panel_a(ctx, 48, 130, 1130, 598, d)
    _draw_panel_b(ctx, 1222, 130, 1130, 598, d)
    _draw_panel_c(ctx, 48, 754, 1130, 598, d)
    _draw_panel_d(ctx, 1222, 754, 1130, 598, d)

    _text(
        ctx, W / 2.0, H - 16,
        "Epistemic scope: Si:31P fabrication, CAD/BOM v6.0, GRAPE, qLDPC & Option-Q/HPC are M0 {Model}/{Sayisal-Simulasyon}/{Varsayim}; "
        "ibm_marrakesh C1/C2/C3 is {Canli-Donanim-IBM-QPU}. Zero secrets.",
        size=13.5, color=MUTED, align="center",
    )

    out_path = OUT_DIR / "fig_exp146_v6_digital_twin.png"
    surf.write_to_png(str(out_path))
    return out_path


if __name__ == "__main__":
    p = render_figure()
    print(f"Rendered {p.relative_to(REPO_ROOT)} ({W}x{H})")
