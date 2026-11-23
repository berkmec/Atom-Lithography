"""Publication-grade 2400x1400 4-panel figure for Exp149 (Q16.16 BOED Verilog RTL & Interactive Twin).

Usage:
    /usr/bin/python3 -B experiments/exp149_boed_verilog_rtl_and_interactive_twin/plot_exp149.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "results" / "exp149_boed_verilog_rtl_and_interactive_twin"
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
PURPLE = (0.486, 0.227, 0.929)
SLATE = (0.459, 0.525, 0.608)
SOFT_BLUE = (0.937, 0.965, 1.000)
SOFT_GREEN = (0.925, 0.992, 0.961)
SOFT_AMBER = (1.000, 0.984, 0.922)
SOFT_PURPLE = (0.961, 0.953, 1.000)


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
    size: float = 16.0,
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


def _arrow(ctx: cairo.Context, x1: float, y1: float, x2: float, y2: float, col: tuple[float, float, float] = SLATE) -> None:
    ctx.set_source_rgb(*col)
    ctx.set_line_width(2.2)
    ctx.move_to(x1, y1)
    ctx.line_to(x2, y2)
    ctx.stroke()
    ang = math.atan2(y2 - y1, x2 - x1)
    ctx.move_to(x2, y2)
    ctx.line_to(x2 - 10 * math.cos(ang - 0.45), y2 - 10 * math.sin(ang - 0.45))
    ctx.line_to(x2 - 10 * math.cos(ang + 0.45), y2 - 10 * math.sin(ang + 0.45))
    ctx.close_path()
    ctx.fill()


def _draw_panel_a(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    _card(
        ctx, x, y, w, h,
        "(A) Synthesizable IEEE 1364-2005 Verilog RTL Block Architecture",
        "boed_top_16ch.v -> 16x boed_q16_core.v (64 total SIMD lanes) + Dual-Port BRAM ROM + 16-Stage isqrt",
    )

    # Outer 16-channel AXI4-Stream Wrapper box
    ox, oy, ow, oh = x + 28, y + 84, w - 56, h - 126
    _rrect(ctx, ox, oy, ow, oh, 12)
    ctx.set_source_rgb(0.976, 0.986, 0.996)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BLUE)
    ctx.set_line_width(2.0)
    ctx.stroke()
    _text(ctx, ox + 16, oy + 26, "boed_top_16ch.v  (Xilinx ZU48DR RFSoC @ 250 MHz, 4.000 ns XDC)", size=15.0, color=BLUE, bold=True)

    # Left AXI4-Stream Slave box
    bx1, by1, bw1, bh1 = ox + 16, oy + 52, 168, 352
    _rrect(ctx, bx1, by1, bw1, bh1, 9)
    ctx.set_source_rgb(*SOFT_BLUE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BLUE)
    ctx.set_line_width(1.6)
    ctx.stroke()
    _text(ctx, bx1 + bw1 / 2, by1 + 28, "AXI4-Stream IN", size=13.5, color=NAVY, bold=True, align="center")
    _text(ctx, bx1 + bw1 / 2, by1 + 48, "s_axis_tdata[127:0]", size=11.5, color=BLUE, align="center")
    _text(ctx, bx1 + bw1 / 2, by1 + 66, "s_axis_tid[3:0]", size=11.5, color=BLUE, align="center")
    for idx, txt in enumerate([
        "[31:0]  f_probe_hz",
        "[63:32] y_meas_q16",
        "[95:64] f_init_hz",
        "[103:96] step_idx",
        "[104]   sprt_mode",
        "[105]   sprt_reset",
        "",
        "Channel Demux",
        "0 .. 15 Parallel",
    ]):
        _text(ctx, bx1 + 12, by1 + 104 + idx * 25, txt, size=11.5, color=TEXT if idx < 6 else MUTED, bold=(idx >= 7))

    # Center boed_q16_core.v (x16) block
    cx, cy, cw, ch = bx1 + bw1 + 32, oy + 46, 614, 366
    _rrect(ctx, cx, cy, cw, ch, 10)
    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.fill_preserve()
    ctx.set_source_rgb(*EMERALD)
    ctx.set_line_width(2.0)
    ctx.stroke()
    _text(ctx, cx + 16, cy + 26, "16x boed_q16_core.v  (4-Lane SIMD DSP48E2 Engine / Ch)", size=14.5, color=EMERALD, bold=True)

    # Sub-block 1: Stage-0 SPRT
    _rrect(ctx, cx + 16, cy + 42, cw - 32, 62, 8)
    ctx.set_source_rgb(*SOFT_AMBER)
    ctx.fill_preserve()
    ctx.set_source_rgb(*AMBER)
    ctx.set_line_width(1.4)
    ctx.stroke()
    _text(ctx, cx + 28, cy + 66, "Stage-0 SPRT Fast-Abort Unit (4 Cycles = 16.0 ns)", size=13.5, color=NAVY, bold=True)
    _text(ctx, cx + 28, cy + 88, "Q16.16 LLR += ((y - 0.5*mu1) * scale + 32768) >>> 16  ->  Blank-Site Reject", size=11.5, color=MUTED)

    # Sub-block 2: Pass-1 Lorentzian ROM + LP Bank
    sub_bw = (cw - 48) / 2.0
    _rrect(ctx, cx + 16, cy + 118, sub_bw, 110, 8)
    ctx.set_source_rgb(*SOFT_BLUE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BLUE)
    ctx.set_line_width(1.4)
    ctx.stroke()
    _text(ctx, cx + 28, cy + 142, "Pass 1: 4x boed_lut_rom.v", size=13.5, color=NAVY, bold=True)
    _text(ctx, cx + 28, cy + 164, "rom_loglik_p0.hex (512w Lor)", size=12.0, color=BLUE)
    _text(ctx, cx + 28, cy + 184, "resid^2 * inv_2var -> sat int32", size=12.0, color=TEXT)
    _text(ctx, cx + 28, cy + 206, "251 beats + 12 pipe = 263 cyc", size=12.0, color=EMERALD, bold=True)

    # Sub-block 3: Pass-2 Exp ROM + 48b MAC
    p2x = cx + 32 + sub_bw
    _rrect(ctx, p2x, cy + 118, sub_bw, 110, 8)
    ctx.set_source_rgb(*SOFT_GREEN)
    ctx.fill_preserve()
    ctx.set_source_rgb(*EMERALD)
    ctx.set_line_width(1.4)
    ctx.stroke()
    _text(ctx, p2x + 12, cy + 142, "Pass 2: 4x boed_lut_rom.v", size=13.5, color=NAVY, bold=True)
    _text(ctx, p2x + 12, cy + 164, "rom_loglik_p1.hex (512w exp)", size=12.0, color=EMERALD)
    _text(ctx, p2x + 12, cy + 184, "48-bit DSP48E2 MAC: Z, M1, M2", size=12.0, color=TEXT)
    _text(ctx, p2x + 12, cy + 206, "251 beats + 14 pipe = 265 cyc", size=12.0, color=EMERALD, bold=True)

    # Sub-block 4: Pass-3 Post + 16-stage isqrt
    _rrect(ctx, cx + 16, cy + 242, cw - 32, 108, 8)
    ctx.set_source_rgb(*SOFT_PURPLE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*PURPLE)
    ctx.set_line_width(1.4)
    ctx.stroke()
    _text(ctx, cx + 28, cy + 266, "Pass 3: Floor-Div + boed_isqrt_cordic.v (16-Stage) + Fisher Argmax", size=13.0, color=NAVY, bold=True)
    _text(ctx, cx + 28, cy + 289, "floor_div_s48 (0-LSB vs Python //) + 16-stage restoring isqrt (0-LSB vs math.isqrt)", size=11.5, color=TEXT)
    _text(ctx, cx + 28, cy + 311, "Outputs: mu_off_q8, std_q4, next_probe_off_q8, cycle_count = 584 (56 cyc)", size=11.5, color=PURPLE, bold=True)
    _text(ctx, cx + 28, cy + 333, "4-Bank Ping-Pong Posterior BRAM36 (4 x 256 x 32b = 1,001 bins @ 10 Hz)", size=11.5, color=MUTED)

    # Right AXI4-Stream Master box
    bx2 = cx + cw + 32
    bw2 = ox + ow - bx2 - 16
    _rrect(ctx, bx2, by1, bw2, bh1, 9)
    ctx.set_source_rgb(*SOFT_GREEN)
    ctx.fill_preserve()
    ctx.set_source_rgb(*EMERALD)
    ctx.set_line_width(1.6)
    ctx.stroke()
    _text(ctx, bx2 + bw2 / 2, by1 + 28, "AXI4-Stream OUT", size=13.5, color=NAVY, bold=True, align="center")
    _text(ctx, bx2 + bw2 / 2, by1 + 48, "m_axis_tdata[95:0]", size=11.5, color=EMERALD, align="center")
    _text(ctx, bx2 + bw2 / 2, by1 + 66, "m_axis_tid[3:0]", size=11.5, color=EMERALD, align="center")
    for idx, txt in enumerate([
        "[31:0]  mu_off_q8",
        "[47:32] std_q4",
        "[79:48] next_probe",
        "[95:80] cycles=584",
        "",
        "Priority Arbiter",
        "16 -> 1 AXI TX",
        "0 W Cryo Load",
    ]):
        _text(ctx, bx2 + 12, by1 + 104 + idx * 25, txt, size=11.5, color=TEXT if idx < 4 else MUTED, bold=(idx >= 5))

    _arrow(ctx, bx1 + bw1, by1 + 176, cx, by1 + 176, BLUE)
    _arrow(ctx, cx + cw, by1 + 176, bx2, by1 + 176, EMERALD)

    _text(
        ctx, x + w / 2, y + h - 16,
        f"IEEE 1364-2005 RTL: {data['rtl_verification']['structural_lint']['total_rtl_loc']} LOC across 4 synthesizable modules | 0 forbidden constructs | 0 port/width errors",
        size=13.0, color=NAVY, bold=True, align="center",
    )


def _draw_panel_b(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    _card(
        ctx, x, y, w, h,
        "(B) Deterministic 584-Cycle Pipeline (2.336 us @ 250 MHz) & Timing Budget",
        "Exact Cycle-for-Cycle Match to Exp140 fpga_boed_dsp.py + Vivado zu48dr_boed_250mhz.xdc (4.000 ns)",
    )

    # Top timeline: Stage-0 SPRT (4 cyc = 16 ns)
    tx, ty, tw = x + 44, y + 102, w - 88
    _text(ctx, tx, ty - 10, "Stage-0 SPRT Fast-Abort (4 Clock Cycles = 16.0 ns @ 250 MHz)", size=14.5, color=NAVY, bold=True)
    sprt_steps = [
        ("C1: Sub", "y - 0.5*mu1", BLUE),
        ("C2: DSP48 Mul", "diff * scale", TEAL),
        ("C3: Q16 Shift", "(p+32768)>>>16", EMERALD),
        ("C4: Acc & Cmp", "|LLR| >= thr", AMBER),
    ]
    sw = tw / 4.0
    for i, (t1, t2, col) in enumerate(sprt_steps):
        sx = tx + i * sw
        _rrect(ctx, sx, ty + 4, sw - 10, 58, 7)
        ctx.set_source_rgb(*col)
        ctx.fill()
        _text(ctx, sx + (sw - 10) / 2, ty + 28, t1, size=14.0, color=(1, 1, 1), bold=True, align="center")
        _text(ctx, sx + (sw - 10) / 2, ty + 49, t2, size=12.0, color=(0.94, 0.97, 1.0), align="center")

    # Middle timeline: Stage-2 584-cycle proportional Gantt
    gy = ty + 114
    _text(ctx, tx, gy - 10, "Stage-2 BOED 1,001-Bin Update (Total = 584 Cycles = 2.336 us; 0.9% of 260 us RF Probe Overhead)", size=14.5, color=NAVY, bold=True)
    phases = [
        ("S_PASS1 (Lorentzian LUT + LP)", 263, "251 beats + 12 pipe = 1,052 ns", BLUE),
        ("S_PASS2 (exp LUT + 48b MAC)", 265, "251 beats + 14 pipe = 1,060 ns", EMERALD),
        ("S_POST", 56, "224 ns", AMBER),
    ]
    cx = tx
    for nm, cyc, sub, col in phases:
        pw = tw * (cyc / 584.0)
        _rrect(ctx, cx, gy + 4, pw - 5, 84, 8)
        ctx.set_source_rgb(*col)
        ctx.fill()
        _text(ctx, cx + (pw - 5) / 2, gy + 32, nm, size=13.5 if cyc > 100 else 12.5, color=(1, 1, 1), bold=True, align="center")
        _text(ctx, cx + (pw - 5) / 2, gy + 54, f"{cyc} cyc", size=16.0, color=(1, 1, 1), bold=True, align="center")
        _text(ctx, cx + (pw - 5) / 2, gy + 74, sub, size=11.5, color=(0.95, 0.97, 1.0), align="center")
        cx += pw

    # Bottom timing comparison bars (log scale: 16 ns SPRT -> 2.336 us FPGA -> 130 us RO -> 260 us Step)
    by = gy + 132
    _text(ctx, tx, by - 8, "System Latency Hierarchy (Log Scale: ns -> us)", size=14.5, color=NAVY, bold=True)
    litems = [
        ("Stage-0 SPRT (4 cyc)", 0.016, AMBER, "16.0 ns"),
        ("Stage-2 BOED FPGA (584 cyc)", 2.336, BLUE, "2.336 us (0.9% overhead)"),
        ("3 kOhm Cryo-MUX Readout (Exp140)", 2.000, TEAL, "2.000 us (N_mux*=32)"),
        ("RF Fine Probe + Wait Budget", 260.0, SLATE, "260.0 us / probe"),
    ]
    lmin, lmax = math.log10(0.01), math.log10(500.0)
    for i, (lbl, val_us, col, rtxt) in enumerate(litems):
        ry = by + 10 + i * 44
        _text(ctx, tx, ry + 18, lbl, size=13.5, color=TEXT, bold=True)
        bx = tx + 290
        bw = tw - 485
        _rrect(ctx, bx, ry + 2, bw, 24, 5)
        ctx.set_source_rgb(0.915, 0.935, 0.960)
        ctx.fill()
        frac = (math.log10(val_us) - lmin) / (lmax - lmin)
        _rrect(ctx, bx, ry + 2, bw * max(0.04, frac), 24, 5)
        ctx.set_source_rgb(*col)
        ctx.fill()
        _text(ctx, bx + bw + 14, ry + 19, rtxt, size=13.0, color=col, bold=True)

    _text(
        ctx, x + w / 2, y + h - 16,
        "XDC Constraints (zu48dr_boed_250mhz.xdc): create_clock 4.000 ns | setup unc. 0.080 ns | 16-cyc multi-cycle divider",
        size=13.0, color=NAVY, bold=True, align="center",
    )


def _draw_panel_c(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    rtl = data["rtl_verification"]
    res16 = rtl["zu48dr_resource_budget"]["total_16ch"]
    co = rtl["bit_exact_co_verification"]
    rom = rtl["rom_verification"]
    lint = rtl["structural_lint"]

    _card(
        ctx, x, y, w, h,
        "(C) ZU48DR RFSoC 16-Channel Utilization & Bit-Exact Verification Scorecard",
        "RV1-RV5: 0-Bit ROM Parity (1,024 words) + 0-LSB Golden Vectors (N=64) + 1,000 isqrt Tests",
    )

    # Top half: 4 resource bars on Xilinx ZU48DR
    tx, ty, tw = x + 44, y + 96, w - 88
    _text(ctx, tx, ty - 8, "Xilinx ZU48DR RFSoC Resource Utilization (16 Parallel Channels = 64 SIMD Lanes)", size=14.5, color=NAVY, bold=True)
    res_rows = [
        ("DSP48E2 Slices", f"{res16['dsp48e2']} / 4,272", res16["dsp48e2_pct"], BLUE),
        ("BRAM36K Blocks", f"{res16['bram36']} / 1,080", res16["bram36_pct"], EMERALD),
        ("CLB LUTs", f"{res16['lut']:,} / 425,280", res16["lut_pct"], PURPLE),
        ("Flip-Flops (FF)", f"{res16['ff']:,} / 850,560", res16["ff_pct"], AMBER),
    ]
    for i, (lbl, cnt, pct, col) in enumerate(res_rows):
        ry = ty + 10 + i * 44
        _text(ctx, tx, ry + 18, lbl, size=13.5, color=TEXT, bold=True)
        bx = tx + 178
        bw = tw - 390
        _rrect(ctx, bx, ry + 2, bw, 22, 5)
        ctx.set_source_rgb(0.915, 0.935, 0.960)
        ctx.fill()
        # Scale bar to 25% ceiling so utilization is readable with clear headroom marker at 20%
        _rrect(ctx, bx, ry + 2, bw * min(1.0, pct / 25.0), 22, 5)
        ctx.set_source_rgb(*col)
        ctx.fill()
        x20 = bx + bw * (20.0 / 25.0)
        ctx.set_source_rgb(0.863, 0.149, 0.149)
        ctx.set_line_width(1.6)
        ctx.move_to(x20, ry - 2)
        ctx.line_to(x20, ry + 26)
        ctx.stroke()
        _text(ctx, bx + bw + 14, ry + 18, f"{cnt}  ({pct:.2f}%)", size=13.0, color=col, bold=True)

    # Bottom half: 2x3 Verification Scorecard Grid
    gy = ty + 206
    cw = (tw - 28) / 3.0
    ch = 114
    cards = [
        ("Structural Lint", f"{lint['forbidden_construct_count']} Forbidden", f"4 files ({lint['total_rtl_loc']} LOC), 0 bal. err", EMERALD, SOFT_GREEN),
        ("Port & Width Match", f"{lint['port_error_count']} / {lint['width_mismatch_count']} Err", f"{lint['instantiations_checked']} module instances verified", EMERALD, SOFT_GREEN),
        ("BRAM ROM .hex", "0 Bit Diff", f"{rom['rom_p0_entries']}+{rom['rom_p1_entries']} = 1,024 words exact", BLUE, SOFT_BLUE),
        ("Golden Vectors", "0 LSB Err", f"N={co['n_golden_vectors']} (mu, std, next_probe)", BLUE, SOFT_BLUE),
        ("16-Stage isqrt", "0 LSB Err", f"N={co['isqrt_vectors_tested']:,} random+boundary", PURPLE, SOFT_PURPLE),
        ("Board Power / Cryo", f"{res16['board_total_power_W']} W / 0 W", "300 K RFSoC rack, 0.0 W cryo", AMBER, SOFT_AMBER),
    ]
    for idx, (ttl, big, sub, col, fill_c) in enumerate(cards):
        r, c = divmod(idx, 3)
        cx = tx + c * (cw + 14)
        cy = gy + r * (ch + 14)
        _rrect(ctx, cx, cy, cw, ch, 9)
        ctx.set_source_rgb(*fill_c)
        ctx.fill_preserve()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(1.4)
        ctx.stroke()
        _text(ctx, cx + 14, cy + 26, ttl, size=13.5, color=NAVY, bold=True)
        _text(ctx, cx + 14, cy + 62, big, size=22.0, color=col, bold=True)
        _text(ctx, cx + 14, cy + 92, sub, size=12.0, color=MUTED)

    _text(
        ctx, x + w / 2, y + h - 16,
        "Epistemic disclosure: no_external_eda_sim=true (host lacks iverilog/vivado; verified by Python linter + bit-exact co-sim).",
        size=12.8, color=NAVY, bold=True, align="center",
    )


def _draw_panel_d(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    tw = data["interactive_twin"]
    _card(
        ctx, x, y, w, h,
        "(D) Zero-Dependency Live Interactive HTML5 Digital Twin (docs/)",
        f"RV6: Single-file offline web app ({tw['size_bytes']/1024:.1f} KB, 0 external CDN/HTTP) embedding live v6/v7 JSONs",
    )

    # 4 Interactive App Tab Feature Cards (2x2)
    px, py, pw = x + 36, y + 88, w - 72
    cw = (pw - 18) / 2.0
    ch = 186
    tabs = [
        (
            "Tab 1: Live Parameter Explorer",
            BLUE, SOFT_BLUE,
            [
                "Sliders: S_eps (0.15-1.00), Q_r (5e5/1e6), f* Stark",
                "Selectors: N_mux (8..64), Wafer (W1/W2/W3)",
                "QEC Switch: Surface Code vs BB144 vs BB288",
                "Modular Toggles: +Option-Q & +Option-HPC",
                "Live KPIs + Log-Scale HTML5 Canvas Chart",
            ],
        ),
        (
            "Tab 2: Clickable S1-S9 Schematic",
            PURPLE, SOFT_PURPLE,
            [
                "Interactive SVG flow of all 9 subsystems",
                "Live CAD v6.0 masses (199p, 1,108.137 kg)",
                "Live BOM v6.0 costs (174p, Base $5.25M / Full $5.55M)",
                "RFQ-01..RFQ-09 scope & safety/interlock notes",
                "Zero clashes (0/19,701) & 40/40 clearances",
            ],
        ),
        (
            "Tab 3: Live 156Q ibm_marrakesh QPU",
            EMERALD, SOFT_GREEN,
            [
                "Real hardware counts: job_id=dc1tdo2nj2vs73dfrfl0",
                "C1 DD Canvas: Bare 0.333 -> Echo 0.922 -> XY4 0.928",
                "C1 Bell Fidelity: 0.9733 | C2 d=3: 7.83x / 0% postsel",
                "C3 8-pt Ramsey fringe + 3 Q16.16 BOED points (1.6 Hz)",
                "Explicit {Canli-Donanim-IBM-QPU} badge, 0 secrets",
            ],
        ),
        (
            "Tab 4: Verilog RTL & FPGA Pipeline",
            AMBER, SOFT_AMBER,
            [
                "Interactive 4-cyc SPRT + 584-cyc FSM Gantt",
                "ZU48DR resource gauges (DSP/BRAM/LUT/FF)",
                "Live lint (0 err), ROM (0 bit), N=64 (0 LSB) table",
                "Auto-rebuilt from disk JSONs via Python script",
                "100% offline capable (file:// or GitHub Pages)",
            ],
        ),
    ]
    for idx, (ttl, col, fill_c, lines) in enumerate(tabs):
        r, c = divmod(idx, 2)
        cx = px + c * (cw + 18)
        cy = py + r * (ch + 18)
        _rrect(ctx, cx, cy, cw, ch, 10)
        ctx.set_source_rgb(*fill_c)
        ctx.fill_preserve()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(1.6)
        ctx.stroke()
        _text(ctx, cx + 16, cy + 28, ttl, size=15.0, color=NAVY, bold=True)
        ctx.set_source_rgb(*BORDER)
        ctx.set_line_width(1.0)
        ctx.move_to(cx + 12, cy + 38)
        ctx.line_to(cx + cw - 12, cy + 38)
        ctx.stroke()
        for j, ln in enumerate(lines):
            _text(ctx, cx + 16, cy + 62 + j * 25, "* " + ln, size=12.5, color=TEXT)

    # Bottom verification badge bar
    by = py + 2 * (ch + 18) + 2
    _rrect(ctx, px, by, pw, 54, 9)
    ctx.set_source_rgb(*NAVY)
    ctx.fill()
    _text(
        ctx, px + pw / 2, by + 23,
        f"Artifact: {tw['html_path']}  |  Zero External CDN: {tw['zero_external_cdn']}  |  9 Subsystems + Live {tw['embedded_live_qpu_backend']}",
        size=13.5, color=(1, 1, 1), bold=True, align="center",
    )
    _text(
        ctx, px + pw / 2, by + 43,
        f"Anchored v6.0 Cert SHA-256: {tw['embedded_v6_sha256']}",
        size=12.0, color=(0.56, 0.78, 0.96), align="center",
    )


def render_figure() -> Path:
    data = json.loads((OUT_DIR / "exp149.json").read_text(encoding="utf-8"))
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
        "Exp149 (H167): Synthesizable Q16.16 BOED-FPGA Verilog RTL & Zero-Dependency Interactive HTML5 Digital Twin",
        size=26.0, color=(1.0, 1.0, 1.0), bold=True,
    )
    _text(
        ctx, 48, 79,
        "IEEE 1364-2005 RTL (rtl/boed_fpga/) | 584 Cycles (2.336 us @ 250 MHz) | 0-Bit ROM & 0-LSB Golden Parity | 7/7 RV PASS | no_external_eda_sim=true",
        size=16.0, color=(0.745, 0.824, 0.914),
    )

    _draw_panel_a(ctx, 48, 130, 1130, 598, data)
    _draw_panel_b(ctx, 1222, 130, 1130, 598, data)
    _draw_panel_c(ctx, 48, 754, 1130, 598, data)
    _draw_panel_d(ctx, 1222, 754, 1130, 598, data)

    _text(
        ctx, W / 2.0, H - 16,
        "Epistemic scope: Verilog RTL & FPGA budget are {Model}/{RTL-Structural-Verified} (no_external_eda_sim=true); "
        "embedded ibm_marrakesh tab is {Canli-Donanim-IBM-QPU}. Zero secrets / zero hardcoded paths.",
        size=13.5, color=MUTED, align="center",
    )

    out_path = OUT_DIR / "fig_exp149_rtl_fpga_arch.png"
    surf.write_to_png(str(out_path))
    return out_path


if __name__ == "__main__":
    p = render_figure()
    print(f"Rendered {p.relative_to(REPO_ROOT)} ({W}x{H})")
