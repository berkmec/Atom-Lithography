"""Academic publication-grade 2400x1400 4-panel figure for Exp149 (Q16.16 BOED Verilog RTL & Digital Twin).

Follows IEEE Transactions / Nature / Physical Review visual standards:
  - Crisp white paper canvas (#FFFFFF) with subtle #F8F9FA structural tints
  - Restrained monochrome-navy hierarchy (#111827 ink, #4B5563 secondary, #1B365D accent, #64748B/#94A3B8 slate)
  - Sparingly applied muted burgundy (#8B2635) for thresholds/warnings and forest (#2D5A3D) for subtle PASS markers
  - Thin axes with top/right spines removed, subtle dashed gridlines, zero rainbow or neon fills

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

# Strict Academic Publication Palette
WHITE = (1.000, 1.000, 1.000)      # #FFFFFF paper canvas
TINT = (0.973, 0.976, 0.980)       # #F8F9FA subtle structural tint
NAVY_TINT = (0.933, 0.949, 0.965)  # #EEF2F6 soft navy highlight
INK = (0.067, 0.094, 0.153)        # #111827 primary ink
MUTED = (0.294, 0.333, 0.388)      # #4B5563 secondary ink
BORDER = (0.820, 0.835, 0.859)     # #D1D5DB hairline border
GRID = (0.898, 0.906, 0.922)       # #E5E7EB dashed gridline
NAVY = (0.106, 0.212, 0.365)       # #1B365D primary data accent
SLATE_D = (0.278, 0.333, 0.412)    # #475569 dark slate
SLATE = (0.392, 0.455, 0.545)      # #64748B medium slate
SLATE_L = (0.580, 0.639, 0.722)    # #94A3B8 light slate
SLATE_P = (0.796, 0.835, 0.882)    # #CBD5E1 pale slate
BURGUNDY = (0.545, 0.149, 0.208)   # #8B2635 threshold / warning accent
FOREST = (0.176, 0.353, 0.239)     # #2D5A3D restrained PASS accent


def _rect(
    ctx: cairo.Context,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: tuple[float, float, float] | None = None,
    stroke: tuple[float, float, float] | None = None,
    lw: float = 1.0,
) -> None:
    ctx.rectangle(x, y, w, h)
    if fill is not None and stroke is not None:
        ctx.set_source_rgb(*fill)
        ctx.fill_preserve()
        ctx.set_source_rgb(*stroke)
        ctx.set_line_width(lw)
        ctx.stroke()
    elif fill is not None:
        ctx.set_source_rgb(*fill)
        ctx.fill()
    elif stroke is not None:
        ctx.set_source_rgb(*stroke)
        ctx.set_line_width(lw)
        ctx.stroke()


def _text(
    ctx: cairo.Context,
    x: float,
    y: float,
    s: str,
    size: float = 14.0,
    color: tuple[float, float, float] = INK,
    bold: bool = False,
    align: str = "left",
    family: str = "DejaVu Sans",
) -> None:
    ctx.select_font_face(
        family,
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


def _panel(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, subtitle: str) -> None:
    _rect(ctx, x, y, w, h, fill=WHITE, stroke=BORDER, lw=1.2)
    # Crisp publication panel title + hairline rule (zero heavy gray header bars)
    _text(ctx, x + 22, y + 31, title, size=18.5, color=INK, bold=True, family="DejaVu Serif")
    _text(ctx, x + 22, y + 53, subtitle, size=12.8, color=MUTED)
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.0)
    ctx.move_to(x + 22, y + 66)
    ctx.line_to(x + w - 22, y + 66)
    ctx.stroke()


def _arrow(ctx: cairo.Context, x1: float, y1: float, x2: float, y2: float, col: tuple[float, float, float] = NAVY) -> None:
    ctx.set_source_rgb(*col)
    ctx.set_line_width(1.6)
    ctx.move_to(x1, y1)
    ctx.line_to(x2, y2)
    ctx.stroke()
    ang = math.atan2(y2 - y1, x2 - x1)
    ctx.move_to(x2, y2)
    ctx.line_to(x2 - 9 * math.cos(ang - 0.42), y2 - 9 * math.sin(ang - 0.42))
    ctx.line_to(x2 - 9 * math.cos(ang + 0.42), y2 - 9 * math.sin(ang + 0.42))
    ctx.close_path()
    ctx.fill()


def _draw_panel_a(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    _panel(
        ctx, x, y, w, h,
        "(a) Synthesizable IEEE 1364-2005 Verilog RTL Block Architecture",
        "boed_top_16ch.v -> 16x boed_q16_core.v (64 SIMD lanes) + dual-port BRAM ROM + 16-stage restoring isqrt",
    )

    # Outer 16-channel AXI4-Stream Wrapper frame
    ox, oy, ow, oh = x + 26, y + 84, w - 52, h - 126
    _rect(ctx, ox, oy, ow, oh, fill=WHITE, stroke=NAVY, lw=1.4)
    _text(ctx, ox + 16, oy + 26, "boed_top_16ch.v  (Xilinx ZU48DR RFSoC @ 250 MHz, 4.000 ns single-cycle XDC)", size=14.0, color=NAVY, bold=True)

    # Left AXI4-Stream Slave box
    bx1, by1, bw1, bh1 = ox + 16, oy + 46, 172, 360
    _rect(ctx, bx1, by1, bw1, bh1, fill=TINT, stroke=SLATE_L, lw=1.1)
    _text(ctx, bx1 + bw1 / 2, by1 + 26, "AXI4-Stream IN", size=13.0, color=INK, bold=True, align="center")
    _text(ctx, bx1 + bw1 / 2, by1 + 46, "s_axis_tdata[127:0]", size=11.0, color=NAVY, align="center", family="DejaVu Sans Mono")
    _text(ctx, bx1 + bw1 / 2, by1 + 64, "s_axis_tid[3:0]", size=11.0, color=NAVY, align="center", family="DejaVu Sans Mono")
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(0.8)
    ctx.move_to(bx1 + 10, by1 + 76)
    ctx.line_to(bx1 + bw1 - 10, by1 + 76)
    ctx.stroke()
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
        _text(
            ctx, bx1 + 12, by1 + 102 + idx * 26, txt,
            size=11.0 if idx < 6 else 11.5,
            color=INK if idx < 6 else MUTED,
            bold=(idx >= 7),
            family="DejaVu Sans Mono" if idx < 6 else "DejaVu Sans",
        )

    # Center 16x boed_q16_core.v container
    cx, cy, cw, ch = bx1 + bw1 + 30, oy + 46, 614, 360
    _rect(ctx, cx, cy, cw, ch, fill=WHITE, stroke=NAVY, lw=1.4)
    _text(ctx, cx + 16, cy + 25, "16x boed_q16_core.v  (4-Lane SIMD DSP48E2 Engine / Channel)", size=13.8, color=NAVY, bold=True)

    # Sub-block 1: Stage-0 SPRT
    _rect(ctx, cx + 16, cy + 40, cw - 32, 62, fill=NAVY_TINT, stroke=NAVY, lw=1.0)
    _text(ctx, cx + 28, cy + 63, "Stage-0 SPRT Fast-Abort Unit  (4 cycles = 16.0 ns)", size=13.0, color=INK, bold=True)
    _text(ctx, cx + 28, cy + 86, "Q16.16 LLR += ((y - 0.5*mu1) * scale + 32768) >>> 16  ->  Blank-Site Reject", size=11.0, color=MUTED, family="DejaVu Sans Mono")

    # Sub-block 2: Pass-1 Lorentzian ROM + LP Bank
    sub_bw = (cw - 48) / 2.0
    _rect(ctx, cx + 16, cy + 116, sub_bw, 108, fill=TINT, stroke=SLATE, lw=1.0)
    _text(ctx, cx + 28, cy + 139, "Pass 1: 4x boed_lut_rom.v", size=13.0, color=INK, bold=True)
    _text(ctx, cx + 28, cy + 161, "rom_loglik_p0.hex (512w Lor)", size=11.2, color=NAVY, family="DejaVu Sans Mono")
    _text(ctx, cx + 28, cy + 182, "resid^2 * inv_2var -> sat int32 + 4-way max", size=11.2, color=MUTED)
    _text(ctx, cx + 28, cy + 205, "251 beats + 12 pipe = 263 cyc", size=11.8, color=NAVY, bold=True)

    # Sub-block 3: Pass-2 Exp ROM + Pipelined 48b MAC
    p2x = cx + 32 + sub_bw
    _rect(ctx, p2x, cy + 116, sub_bw, 108, fill=TINT, stroke=SLATE, lw=1.0)
    _text(ctx, p2x + 12, cy + 139, "Pass 2: 4x boed_lut_rom.v", size=13.0, color=INK, bold=True)
    _text(ctx, p2x + 12, cy + 161, "rom_loglik_p1.hex (512w exp)", size=11.2, color=NAVY, family="DejaVu Sans Mono")
    _text(ctx, p2x + 12, cy + 182, "1:1 BRAM align + pipelined 48b MAC", size=11.2, color=MUTED)
    _text(ctx, p2x + 12, cy + 205, "251 beats + 14 pipe = 265 cyc", size=11.8, color=NAVY, bold=True)

    # Sub-block 4: Pass-3 Restoring Dividers + 16-stage isqrt
    _rect(ctx, cx + 16, cy + 238, cw - 32, 108, fill=NAVY_TINT, stroke=NAVY, lw=1.0)
    _text(ctx, cx + 28, cy + 261, "Pass 3: 3x Bit-Serial Restoring Dividers + 16-Stage isqrt + Fisher Argmax", size=12.8, color=INK, bold=True)
    _text(ctx, cx + 28, cy + 284, "18/21/35-cyc shift-subtract (0 '/' operators) + 36b/44b var + restoring isqrt (0 LSB)", size=11.2, color=MUTED)
    _text(ctx, cx + 28, cy + 306, "Outputs: mu_off_q8, std_q4, next_probe_off_q8, cycle_count = 584  (56 cyc)", size=11.5, color=NAVY, bold=True)
    _text(ctx, cx + 28, cy + 328, "4-Bank Reset-Less Posterior BRAM (4x RAMB18E2 + 8x LUT ROM RAMB18E2 = 12/ch)", size=11.2, color=MUTED)

    # Right AXI4-Stream Master box
    bx2 = cx + cw + 30
    bw2 = ox + ow - bx2 - 16
    _rect(ctx, bx2, by1, bw2, bh1, fill=TINT, stroke=SLATE_L, lw=1.1)
    _text(ctx, bx2 + bw2 / 2, by1 + 26, "AXI4-Stream OUT", size=13.0, color=INK, bold=True, align="center")
    _text(ctx, bx2 + bw2 / 2, by1 + 46, "m_axis_tdata[95:0]", size=11.0, color=NAVY, align="center", family="DejaVu Sans Mono")
    _text(ctx, bx2 + bw2 / 2, by1 + 64, "m_axis_tid[3:0]", size=11.0, color=NAVY, align="center", family="DejaVu Sans Mono")
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(0.8)
    ctx.move_to(bx2 + 10, by1 + 76)
    ctx.line_to(bx2 + bw2 - 10, by1 + 76)
    ctx.stroke()
    for idx, txt in enumerate([
        "[31:0]  mu_off_q8",
        "[47:32] std_q4",
        "[79:48] next_probe",
        "[95:80] cycles=584",
        "",
        "Priority Arbiter",
        "16 -> 1 AXI TX",
        "0.0 W Cryo Load",
    ]):
        _text(
            ctx, bx2 + 12, by1 + 102 + idx * 26, txt,
            size=11.0 if idx < 4 else 11.5,
            color=INK if idx < 4 else MUTED,
            bold=(idx >= 5),
            family="DejaVu Sans Mono" if idx < 4 else "DejaVu Sans",
        )

    _arrow(ctx, bx1 + bw1, by1 + 180, cx, by1 + 180, NAVY)
    _arrow(ctx, cx + cw, by1 + 180, bx2, by1 + 180, NAVY)

    _text(
        ctx, x + w / 2, y + h - 16,
        f"IEEE 1364-2005 RTL: {data['rtl_verification']['structural_lint']['total_rtl_loc']} LOC across 4 synthesizable modules  |  0 forbidden constructs  |  0 port/width errors",
        size=12.2, color=MUTED, bold=True, align="center",
    )


def _draw_panel_b(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    _panel(
        ctx, x, y, w, h,
        "(b) Deterministic 584-Cycle Pipeline (2.336 us @ 250 MHz) & Timing Budget",
        "Cycle-for-cycle parity with fpga_boed_dsp.py + single-cycle zu48dr_boed_250mhz.xdc (4.000 ns)",
    )

    tx, ty, tw = x + 44, y + 100, w - 88
    _text(ctx, tx, ty - 8, "Stage-0 SPRT Fast-Abort Pipeline (4 Clock Cycles = 16.0 ns @ 250 MHz)", size=13.5, color=INK, bold=True)
    sprt_steps = [
        ("C1: Sub", "y - 0.5*mu1"),
        ("C2: DSP48 Mul", "diff * scale"),
        ("C3: Q16 Shift", "(p+32768)>>>16"),
        ("C4: Acc & Cmp", "|LLR| >= thr"),
    ]
    sw = tw / 4.0
    for i, (t1, t2) in enumerate(sprt_steps):
        sx = tx + i * sw
        _rect(ctx, sx, ty + 4, sw - 10, 52, fill=NAVY_TINT, stroke=NAVY, lw=1.1)
        _text(ctx, sx + (sw - 10) / 2, ty + 25, t1, size=13.0, color=INK, bold=True, align="center")
        _text(ctx, sx + (sw - 10) / 2, ty + 45, t2, size=11.0, color=MUTED, align="center", family="DejaVu Sans Mono")

    # Stage-2 584-cycle proportional Gantt (monochrome navy/slate tonal hierarchy)
    gy = ty + 96
    _text(ctx, tx, gy - 8, "Stage-2 BOED 1,001-Bin Update (584 Cycles = 2.336 us; 0.9% of 260 us RF Probe Budget)", size=13.5, color=INK, bold=True)
    phases = [
        ("S_PASS1 (Lorentzian LUT + LP)", 263, "251 beats + 12 pipe = 1,052 ns", NAVY, WHITE),
        ("S_PASS2 (exp LUT + 48b MAC)", 265, "251 beats + 14 pipe = 1,060 ns", SLATE_D, WHITE),
        ("S_POST", 56, "224 ns", SLATE_P, INK),
    ]
    cx = tx
    for nm, cyc, sub, col, tcol in phases:
        pw = tw * (cyc / 584.0)
        _rect(ctx, cx, gy + 4, pw - 5, 76, fill=col, stroke=NAVY if col == SLATE_P else None, lw=0.9)
        _text(ctx, cx + (pw - 5) / 2, gy + 28, nm, size=12.8 if cyc > 100 else 12.0, color=tcol, bold=True, align="center")
        _text(ctx, cx + (pw - 5) / 2, gy + 49, f"{cyc} cyc", size=14.8, color=tcol, bold=True, align="center", family="DejaVu Sans Mono")
        _text(ctx, cx + (pw - 5) / 2, gy + 69, sub, size=11.0, color=tcol, align="center")
        cx += pw

    # System Latency Hierarchy (log-scale chart with thin L-axes, top/right spines removed, dashed gridlines)
    by = gy + 118
    _text(ctx, tx, by - 8, "System Latency Hierarchy (Log Scale: ns to us)", size=13.5, color=INK, bold=True)
    bx = tx + 295
    bw = tw - 485
    plot_top = by + 8
    plot_h = 176
    lmin, lmax = math.log10(0.01), math.log10(500.0)

    # Subtle vertical dashed gridlines at log decades
    ticks = [(0.01, "10 ns"), (0.1, "100 ns"), (1.0, "1 us"), (10.0, "10 us"), (100.0, "100 us")]
    ctx.set_dash([3.0, 3.0])
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(0.8)
    for tv, tlbl in ticks:
        tx_pos = bx + bw * (math.log10(tv) - lmin) / (lmax - lmin)
        ctx.move_to(tx_pos, plot_top)
        ctx.line_to(tx_pos, plot_top + plot_h)
        ctx.stroke()
    ctx.set_dash([])

    # Left and bottom axes only (top/right spines removed)
    ctx.set_source_rgb(*MUTED)
    ctx.set_line_width(1.0)
    ctx.move_to(bx, plot_top)
    ctx.line_to(bx, plot_top + plot_h)
    ctx.line_to(bx + bw, plot_top + plot_h)
    ctx.stroke()

    for tv, tlbl in ticks:
        tx_pos = bx + bw * (math.log10(tv) - lmin) / (lmax - lmin)
        ctx.set_source_rgb(*MUTED)
        ctx.set_line_width(0.9)
        ctx.move_to(tx_pos, plot_top + plot_h)
        ctx.line_to(tx_pos, plot_top + plot_h + 5)
        ctx.stroke()
        _text(ctx, tx_pos, plot_top + plot_h + 20, tlbl, size=11.0, color=MUTED, align="center", family="DejaVu Sans Mono")

    litems = [
        ("Stage-0 SPRT (4 cyc)", 0.016, NAVY, "16.0 ns"),
        ("Stage-2 BOED FPGA (584 cyc)", 2.336, NAVY, "2.336 us (0.9% overhead)"),
        ("3 kOhm Cryo-MUX Readout (Exp140)", 2.000, SLATE, "2.000 us (N_mux*=32)"),
        ("RF Fine Probe + Wait Budget", 260.0, SLATE_L, "260.0 us / probe"),
    ]
    for i, (lbl, val_us, col, rtxt) in enumerate(litems):
        ry = plot_top + 12 + i * 42
        _text(ctx, bx - 12, ry + 16, lbl, size=12.4, color=INK, bold=(i < 2), align="right")
        frac = (math.log10(val_us) - lmin) / (lmax - lmin)
        _rect(ctx, bx + 1, ry + 2, bw * max(0.03, frac), 20, fill=col)
        _text(ctx, bx + bw + 12, ry + 16, rtxt, size=12.0, color=INK if i < 2 else MUTED, bold=(i < 2), family="DejaVu Sans Mono")

    _text(
        ctx, x + w / 2, y + h - 16,
        "XDC Constraints (zu48dr_boed_250mhz.xdc): create_clock 4.000 ns  |  setup unc. 0.080 ns  |  0 multicycle waivers (all single-cycle)",
        size=12.2, color=MUTED, bold=True, align="center",
    )


def _draw_panel_c(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    rtl = data["rtl_verification"]
    res16 = rtl["zu48dr_resource_budget"]["total_16ch"]
    yos_map = rtl["zu48dr_resource_budget"].get("yosys_measured_pre_pnr", {}).get("targets", {})
    yos_top16 = yos_map.get("xcup_top16", {})
    yos_raw = rtl.get("yosys_synthesis", {}).get("targets", {})
    rom = rtl["rom_verification"]
    lint = rtl["structural_lint"]
    veril = rtl.get("verilator_lint", {})
    iver = rtl.get("iverilog_simulation", {})

    _panel(
        ctx, x, y, w, h,
        "(c) ZU48DR 16-Channel Yosys Pre-P&R Utilization & Real-EDA Verification Ledger",
        "RV1-RV8: Verilator -Wall (0 warn) + Icarus Verilog vvp (64/64 0-LSB) + Yosys xcup / xc7 / ecp5",
    )

    tx, ty, tw = x + 40, y + 96, w - 80
    _text(
        ctx, tx, ty - 8,
        "Xilinx ZU48DR Pre-P&R Utilization — Real Yosys synth_xilinx -family xcup (16ch boed_top_16ch)",
        size=13.2, color=INK, bold=True,
    )

    if yos_top16:
        pcts = yos_top16["zu48dr_pct"]
        res_rows = [
            ("DSP48E2 Slices", f"{yos_top16['dsp_total']:,} / 4,272", pcts["dsp48e2_pct"], NAVY),
            ("BRAM36-eq (RAMB18)", f"{yos_top16['bram36_equiv']:.0f} / 1,080 ({yos_top16['bram_blocks']}x18K)", pcts["bram36_equiv_pct"], NAVY),
            ("CLB LUT + SRL16E", f"{yos_top16['lut_total']:,} / 425,280", pcts["lut_pct"], SLATE),
            ("Flip-Flops (FDRE/SE)", f"{yos_top16['ff_total']:,} / 850,560", pcts["ff_pct"], SLATE_L),
        ]
    else:
        res_rows = [
            ("DSP48E2 Slices", f"{res16['dsp48e2']} / 4,272", res16["dsp48e2_pct"], NAVY),
            ("BRAM36K Blocks", f"{res16['bram36']} / 1,080", res16["bram36_pct"], NAVY),
            ("CLB LUTs", f"{res16['lut']:,} / 425,280", res16["lut_pct"], SLATE),
            ("Flip-Flops (FF)", f"{res16['ff']:,} / 850,560", res16["ff_pct"], SLATE_L),
        ]

    bx = tx + 195
    bw = tw - 430
    plot_top = ty + 6
    plot_h = 152

    # Vertical dashed gridlines at 10% intervals up to 50%
    ctx.set_dash([3.0, 3.0])
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(0.8)
    for pct_tick in (10, 20, 30, 40, 50):
        px_t = bx + bw * (pct_tick / 50.0)
        ctx.move_to(px_t, plot_top)
        ctx.line_to(px_t, plot_top + plot_h)
        ctx.stroke()
    ctx.set_dash([])

    # Left & bottom spines only (top/right removed)
    ctx.set_source_rgb(*MUTED)
    ctx.set_line_width(1.0)
    ctx.move_to(bx, plot_top)
    ctx.line_to(bx, plot_top + plot_h)
    ctx.line_to(bx + bw, plot_top + plot_h)
    ctx.stroke()

    for pct_tick in (0, 10, 20, 30, 40, 50):
        px_t = bx + bw * (pct_tick / 50.0)
        ctx.set_source_rgb(*MUTED)
        ctx.set_line_width(0.9)
        ctx.move_to(px_t, plot_top + plot_h)
        ctx.line_to(px_t, plot_top + plot_h + 4)
        ctx.stroke()
        _text(ctx, px_t, plot_top + plot_h + 18, f"{pct_tick}%", size=10.8, color=MUTED, align="center", family="DejaVu Sans Mono")

    # Restrained muted burgundy 40% headroom marker
    x40 = bx + bw * (40.0 / 50.0)
    ctx.set_dash([5.0, 3.0])
    ctx.set_source_rgb(*BURGUNDY)
    ctx.set_line_width(1.3)
    ctx.move_to(x40, plot_top)
    ctx.line_to(x40, plot_top + plot_h)
    ctx.stroke()
    ctx.set_dash([])
    _text(ctx, x40 + 4, plot_top + 11, "40% ref.", size=10.0, color=BURGUNDY, align="left")

    for i, (lbl, cnt, pct, col) in enumerate(res_rows):
        ry = plot_top + 8 + i * 36
        _text(ctx, bx - 12, ry + 14, lbl, size=12.4, color=INK, bold=(i < 2), align="right")
        _rect(ctx, bx + 1, ry + 2, bw * min(1.0, pct / 50.0), 18, fill=col)
        _text(ctx, bx + bw + 12, ry + 15, f"{cnt} ({pct:.2f}%)", size=11.8, color=INK, bold=(i < 2), family="DejaVu Sans Mono")

    # Bottom half: Clean IEEE Booktabs Real-EDA Verification Table (generous breathing room below x-ticks)
    tbl_y = plot_top + plot_h + 52
    _text(ctx, tx, tbl_y - 6, "Table 1. Real Open-Source EDA Verification & Multi-Family Yosys Synthesis Summary", size=12.8, color=INK, bold=True)

    xcup_1 = yos_raw.get("xcup_core", {})
    xc7_1 = yos_raw.get("xc7_core", {})
    ecp5_1 = yos_raw.get("ecp5_core", {})
    iv_c = iver.get("boed_q16_core", {})

    col_x = [tx, tx + 245, tx + 520, tx + 870]
    row_h = 31
    hdr_y = tbl_y + 4

    # Top thick rule + header row + mid rule (academic booktabs)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(1.6)
    ctx.move_to(tx, hdr_y)
    ctx.line_to(tx + tw, hdr_y)
    ctx.stroke()

    _rect(ctx, tx, hdr_y + 1, tw, row_h - 1, fill=TINT)
    for cx_p, htxt, al in (
        (col_x[0] + 8, "Verification Gate", "left"),
        (col_x[1] + 8, "Measured Metric", "left"),
        (col_x[2] + 8, "Scope & Provenance", "left"),
        (tx + tw - 8, "Status", "right"),
    ):
        _text(ctx, cx_p, hdr_y + 22, htxt, size=11.5, color=INK, bold=True, align=al)

    ctx.set_source_rgb(*INK)
    ctx.set_line_width(1.0)
    ctx.move_to(tx, hdr_y + row_h)
    ctx.line_to(tx + tw, hdr_y + row_h)
    ctx.stroke()

    tbl_rows = [
        ("Verilator --lint-only -Wall", "0 Warnings / 0 Errors", f"boed_q16_core + boed_top_16ch ({lint['total_rtl_loc']} LOC, 0 '/')", "PASS" if veril.get("all_passed") else "FAIL", FOREST),
        ("Icarus Verilog + vvp", f"0 LSB / {iv_c.get('boed_cycles_max', 584)} cyc", "64 vectors (8 regimes) + 4ch AXI4-Stream + SPRT + isqrt", "PASS" if iver.get("all_passed") else "FAIL", FOREST),
        ("BRAM ROM .hex Parity", "0 Bit Diff (1,024/1,024)", "rom_loglik_p0.hex (512w) + rom_loglik_p1.hex (512w)", "PASS" if rom.get("all_zero_bit_diff") else "FAIL", FOREST),
        ("Yosys xcup (1ch core)", f"{xcup_1.get('dsp_total', 0)} DSP / {xcup_1.get('bram_blocks', 0)} RAMB18", f"{xcup_1.get('lut_total', 0):,} LUT (+SRL), {xcup_1.get('ff_total', 0):,} FF, {xcup_1.get('carry_cells', 0):,} CARRY4", "MEASURED", NAVY),
        ("Yosys xc7 / ecp5 (1ch)", f"{xc7_1.get('dsp_total', 0)} DSP / {ecp5_1.get('dsp_total', 0)} MULT18", f"xc7 {xc7_1.get('lut_total', 0):,} LUT | ecp5 {ecp5_1.get('lut_total', 0):,} LUT4, 12 BRAM each", "MEASURED", NAVY),
        ("Baseline Audit -> Fixed", "64/64 Fail -> 0 Fail", "5 real RTL/TB bugs proven before edits & resolved", "FIXED", BURGUNDY),
    ]

    for idx, (c0, c1, c2, st, st_col) in enumerate(tbl_rows):
        ry = hdr_y + row_h * (idx + 1)
        if idx % 2 == 1:
            _rect(ctx, tx, ry, tw, row_h, fill=TINT)
        _text(ctx, col_x[0] + 8, ry + 22, c0, size=11.5, color=INK, bold=True)
        _text(ctx, col_x[1] + 8, ry + 22, c1, size=11.3, color=NAVY, bold=True, family="DejaVu Sans Mono")
        _text(ctx, col_x[2] + 8, ry + 22, c2, size=11.2, color=MUTED)
        _text(ctx, tx + tw - 8, ry + 22, st, size=11.3, color=st_col, bold=True, align="right", family="DejaVu Sans Mono")
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(0.8)
        ctx.move_to(tx, ry + row_h)
        ctx.line_to(tx + tw, ry + row_h)
        ctx.stroke()

    # Bottom thick booktabs rule
    bot_y = hdr_y + row_h * (len(tbl_rows) + 1)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(1.6)
    ctx.move_to(tx, bot_y)
    ctx.line_to(tx + tw, bot_y)
    ctx.stroke()

    _text(
        ctx, x + w / 2, y + h - 16,
        "Real EDA verified (no_external_eda_sim=false): Yosys pre-P&R cell counts reported; vendor Vivado P&R & board tests pending (no_vendor_vivado_pnr=true).",
        size=11.8, color=MUTED, bold=True, align="center",
    )


def _draw_panel_d(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    tw = data["interactive_twin"]
    _panel(
        ctx, x, y, w, h,
        "(d) Zero-Dependency Live Interactive HTML5 Model Explorer (docs/)",
        f"RV6: Single-file offline 5-tab app ({tw['size_bytes']/1000:.1f} KB / {tw['size_bytes']:,} B, 0 CDN) embedding live v7.2 JSONs",
    )

    px, py, pw = x + 36, y + 86, w - 72
    cw = (pw - 20) / 2.0
    ch = 186
    tabs = [
        (
            "Tab 1: Live Parameter Explorer",
            [
                "Sliders: S_eps (0.15-1.00), Q_r (5e5/1e6), f* Stark",
                "Selectors: N_mux (8..64), Wafer (W1/W2/W3)",
                "QEC Switch: Surface Code vs BB144 vs BB288",
                "Modular Toggles: +S7.SAFETY, +Option-Q, +Option-HPC",
                "Live KPIs + Log-Scale HTML5 Canvas Chart",
            ],
        ),
        (
            "Tab 2: Clickable S1-S9 Schematic",
            [
                "Interactive SVG flow of all 9 subsystems",
                "Live CAD v6.0 masses (199p, 1,108.137 kg + 355 kg safe)",
                "Live BOM v7.0 (180p, Base+Safe $5.39M / Full $5.69M)",
                "RFQ-01..RFQ-10 scope & S7.SAFETY M0 target notes",
                "Zero clashes (0/19,701) & 40/40 clearances",
            ],
        ),
        (
            "Tab 3: Live 156Q ibm_marrakesh QPU Proxy",
            [
                "Real hardware counts: job_id=dc1tdo2nj2vs73dfrfl0",
                "C1 DD Canvas: Bare 0.333 -> Echo 0.922 -> XY4 0.928",
                "C1 Bell Fidelity: 0.9733  |  C2 d=3: 7.83x / 0% postsel",
                "C3 8-pt Ramsey fringe + 3 Q16.16 BOED points (1.6 Hz)",
                "Explicit {Canli-Donanim-IBM-QPU} proxy badge, 0 secrets",
            ],
        ),
        (
            "Tabs 4-5 (5 Tabs): Real-EDA RTL & v7.2 Suite",
            [
                "Tab 4: 4-cyc SPRT + 584-cyc FSM + Yosys xcup gauges",
                "Real Verilator -Wall (0 warn) + Icarus vvp (64/64 0-LSB)",
                "Tab 5: Exp147 FeMoco/RSA + Exp148 121Sb Q-Echo-8",
                "Tab 5: Exp150 FMEA (RPN 280->42, uncertified M0 target)",
                f"100% offline 5-tab app ({tw['size_bytes']/1000:.1f} KB, 0 external CDN/HTTP)",
            ],
        ),
    ]

    for idx, (ttl, lines) in enumerate(tabs):
        r, c = divmod(idx, 2)
        cx = px + c * (cw + 20)
        cy = py + r * (ch + 18)
        _rect(ctx, cx, cy, cw, ch, fill=TINT, stroke=BORDER, lw=1.0)
        # Restrained 2.5px academic navy top accent rule
        _rect(ctx, cx, cy, cw, 2.5, fill=NAVY)
        _text(ctx, cx + 16, cy + 28, ttl, size=14.0, color=INK, bold=True, family="DejaVu Serif")
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(0.9)
        ctx.move_to(cx + 14, cy + 38)
        ctx.line_to(cx + cw - 14, cy + 38)
        ctx.stroke()
        for j, ln in enumerate(lines):
            _text(ctx, cx + 16, cy + 62 + j * 25, "- " + ln, size=12.0, color=MUTED)

    # Bottom provenance bar (clean white-paper academic style, zero dark block)
    by = py + 2 * (ch + 18) + 4
    _rect(ctx, px, by, pw, 56, fill=NAVY_TINT, stroke=NAVY, lw=1.1)
    _text(
        ctx, px + pw / 2, by + 23,
        f"Artifact: {tw['html_path']}  |  Zero External CDN: {tw['zero_external_cdn']}  |  9 Subsystems + Cloud Proxy {tw['embedded_live_qpu_backend']}",
        size=12.8, color=INK, bold=True, align="center",
    )
    _text(
        ctx, px + pw / 2, by + 44,
        f"Anchored v6.0 Cert SHA-256: {tw['embedded_v6_sha256']}",
        size=11.5, color=NAVY, align="center", family="DejaVu Sans Mono",
    )


def render_figure() -> Path:
    data = json.loads((OUT_DIR / "exp149.json").read_text(encoding="utf-8"))
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    # Pure white paper canvas
    _rect(ctx, 0, 0, W, H, fill=WHITE)

    # Editorial journal masthead (white background, crisp top accent rule, bottom hairline)
    _rect(ctx, 0, 0, W, 5, fill=NAVY)
    _text(
        ctx, 48, 48,
        "Exp149 (H167): Synthesizable Q16.16 BOED-FPGA Verilog RTL & Zero-Dependency Interactive HTML5 Model Explorer",
        size=24.5, color=INK, bold=True, family="DejaVu Serif",
    )
    _text(
        ctx, 48, 82,
        f"IEEE 1364-2005 RTL (rtl/boed_fpga/)  |  584 Cycles (2.336 us @ 250 MHz)  |  Verilator -Wall + Icarus Verilog 0-LSB + Yosys xcup/xc7/ecp5  |  {data['n_passed']}/{data['n_total']} RV PASS",
        size=14.8, color=MUTED,
    )
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.2)
    ctx.move_to(48, 102)
    ctx.line_to(W - 48, 102)
    ctx.stroke()

    _draw_panel_a(ctx, 48, 124, 1134, 606, data)
    _draw_panel_b(ctx, 1218, 124, 1134, 606, data)
    _draw_panel_c(ctx, 48, 754, 1134, 602, data)
    _draw_panel_d(ctx, 1218, 754, 1134, 602, data)

    _text(
        ctx, W / 2.0, H - 15,
        "Epistemic scope: RTL verified via real Icarus Verilog + Verilator -Wall + Yosys pre-P&R (no_external_eda_sim=false, no_vendor_vivado_pnr=true, no_lab_measurement_rtl=true); "
        "ibm_marrakesh tab is {Canli-Donanim-IBM-QPU} control proxy.",
        size=12.0, color=MUTED, align="center",
    )

    out_path = OUT_DIR / "fig_exp149_rtl_fpga_arch.png"
    surf.write_to_png(str(out_path))
    return out_path


if __name__ == "__main__":
    p = render_figure()
    print(f"Rendered {p.relative_to(REPO_ROOT)} ({W}x{H})")
