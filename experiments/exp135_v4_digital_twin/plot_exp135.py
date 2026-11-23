"""Generate 2000x1200 PyCairo summary figure for Exp135 (H153) v4.0 Full-Machine Digital Twin.

Portable execution (stdlib + cairo only, zero numpy, zero hardcoded host paths):
    /usr/bin/python3 -B experiments/exp135_v4_digital_twin/plot_exp135.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp135_v4_digital_twin"
DATA_PATH = OUT_DIR / "exp135_plot_data.json"

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
    size: float = 13.0,
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
    size: float = 13.0,
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
    _text(ctx, x + 20, y + 31, title, size=17.5, color=C_TEXT, bold=True)
    _text(ctx, x + w - 20, y + 30, tag, size=12.5, color=C_GREEN, bold=True, align="right")
    ctx.set_source_rgb(*C_GRID)
    ctx.set_line_width(1.2)
    ctx.move_to(x + 16, y + 44)
    ctx.line_to(x + w - 16, y + 44)
    ctx.stroke()


def plot_digital_twin(data: dict) -> Path:
    W, H = 2000, 1200
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*C_BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    l1 = data["layer1"]
    l2 = data["layer2"]
    l4 = data["layer4"]["regimes"]
    l5 = data["layer5"]
    l6 = data["layer6"]["regimes"]
    l7 = data["layer7"]
    wf = data["wafer_live"]
    mc = data["master_cert"]

    # Header band
    ctx.set_source_rgb(*C_HEADER)
    ctx.rectangle(0, 0, W, 88)
    ctx.fill()
    _text(ctx, 36, 40, "Exp135 (H153) — Atom Lithography Machine v4.0 End-to-End 8-Layer Digital Twin", size=25.5, color=(1.0, 1.0, 1.0), bold=True)
    _text(
        ctx,
        36,
        69,
        (
            f"Coupled Exp124-Exp134 Physics + Live src/machine_control/ (BOED + CellISA v3.0)   |   "
            f"7/7 Pre-Registered Verdicts PASS   |   Master SHA-256: {mc['sha256'][:16]}...   |   no_lab_measurement=true   |   {{Model}}"
        ),
        size=13.5,
        color=(0.76, 0.84, 0.96),
    )

    # =========================================================================
    # PANEL A (Top-Left): L1 Placement RSS + L4 BOED Throughput across Risk R1
    # =========================================================================
    ax, ay, aw, ah = 32, 108, 956, 514
    _draw_card(ctx, ax, ay, aw, ah, "A. L1 Placement Budget & L4 Adaptive BOED Throughput Across Risk R1", "DT1 & DT2 PASS")

    # Left sub-chart: Placement RSS (nm) [3.30 .. 3.90]
    px0, px1 = ax + 56, ax + 345
    py0, py1 = ay + 84, ay + ah - 110
    _text(ctx, (px0 + px1) / 2.0, ay + 68, "Compound Placement Error (nm)", size=13.0, color=C_TEXT, bold=True, align="center")

    ymin_p, ymax_p = 3.30, 3.90

    def _yp(v: float) -> float:
        return py1 - ((v - ymin_p) / (ymax_p - ymin_p)) * (py1 - py0)

    for tv in (3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9):
        gy = _yp(tv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, gy)
        ctx.line_to(px1, gy)
        ctx.stroke()
        _text(ctx, px0 - 7, gy + 4, f"{tv:.1f}", size=11.0, color=C_MUTED, align="right")

    # 3.80 nm ceiling line
    y38 = _yp(3.80)
    ctx.save()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.8)
    ctx.set_dash([5.0, 4.0])
    ctx.move_to(px0, y38)
    ctx.line_to(px1, y38)
    ctx.stroke()
    ctx.restore()
    _text(ctx, px1 - 2, y38 - 6, "Exp124 Ceiling 3.80 nm", size=10.8, color=C_RED, bold=True, align="right")

    p_bars = [
        ("v3.0\n15 ms", l1["v300_orig_15ms_nm"], (0.50, 0.56, 0.66)),
        ("v4.0\n15 ms", l1["v400_coupled_15ms_nm"], C_BLUE),
        ("v4.0\n10 ms", l1["v400_coupled_10ms_nm"], C_TEAL),
    ]
    pbw = 64
    for i, (lbl, val, col) in enumerate(p_bars):
        bx_b = px0 + 22 + i * 92
        bt = _yp(val)
        _round_rect(ctx, bx_b, bt, pbw, py1 - bt, 5)
        ctx.set_source_rgb(*col)
        ctx.fill()
        _text(ctx, bx_b + pbw / 2.0, bt + 22, f"{val:.3f}", size=12.0, color=(1.0, 1.0, 1.0), bold=True, align="center")
        lines_lbl = lbl.split("\n")
        _text(ctx, bx_b + pbw / 2.0, py1 + 19, lines_lbl[0], size=11.8, color=C_TEXT, bold=True, align="center")
        _text(ctx, bx_b + pbw / 2.0, py1 + 35, lines_lbl[1], size=11.0, color=C_MUTED, align="center")

    # Rigid CFG1 failure callout + L2 survival strip under left sub-chart
    _round_rect(ctx, ax + 24, ay + ah - 62, 336, 46, 7)
    ctx.set_source_rgb(0.99, 0.94, 0.94)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.2)
    ctx.stroke()
    _text(ctx, ax + 192, ay + ah - 42, f"Rigid PT420 CFG1: {l1['rigid_CFG1_15ms_nm']:,.0f} nm (FAIL)", size=11.5, color=C_RED, bold=True, align="center")
    _text(ctx, ax + 192, ay + ah - 24, f"L2 Survival: IBIC x 808nm = {l2['combined_implant_activation_survival']*100:.3f}%", size=11.0, color=C_TEXT, align="center")

    # Right sub-chart: Log-scale Certified Registers/Day across 3 Exp129 regimes
    tx0, tx1 = ax + 432, ax + aw - 26
    ty0, ty1 = ay + 84, ay + ah - 110
    _text(ctx, (tx0 + tx1) / 2.0, ay + 68, "Certified Registers / Day Across Exp129 Risk R1 (log scale)", size=13.0, color=C_TEXT, bold=True, align="center")

    lymin, lymax = math.log10(1.0e7), math.log10(4.5e9)

    def _yt(r: float) -> float:
        return ty1 - ((math.log10(max(r, 1e7)) - lymin) / (lymax - lymin)) * (ty1 - ty0)

    for rv, rlbl in ((2e7, "2e7"), (1e8, "1e8"), (5e8, "5e8"), (1e9, "1e9"), (2.25e9, "2.25e9")):
        gy = _yt(rv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(tx0, gy)
        ctx.line_to(tx1, gy)
        ctx.stroke()
        _text(ctx, tx0 - 7, gy + 4, rlbl, size=10.8, color=C_MUTED, align="right")

    reg_groups = [
        ("KL Canonical\n(p_B = 51.0%)", l4["KL_canonical_f1"]),
        ("VOKL-6 HM5962\n(p_B = 33.25%)", l4["VOKL6_HM5962_f1"]),
        ("VOKL-6 norm\n(p_B = 4.75%)", l4["VOKL6_norm_f1_worst"]),
    ]
    gw = (tx1 - tx0) / 3.0
    sbw = 34
    for g_idx, (glbl, rdata) in enumerate(reg_groups):
        gx_c = tx0 + (g_idx + 0.5) * gw
        vals = [
            (rdata["v300_net_15ms_per_day"], (0.60, 0.65, 0.72)),
            (rdata["v400_net_15ms_per_day"], C_BLUE),
            (rdata["v400_net_10ms_per_day"], C_GREEN),
        ]
        for b_idx, (v, col) in enumerate(vals):
            bx_b = gx_c - 1.5 * sbw - 4 + b_idx * (sbw + 4)
            bt = _yt(v)
            _round_rect(ctx, bx_b, bt, sbw, ty1 - bt, 4)
            ctx.set_source_rgb(*col)
            ctx.fill()
            if b_idx == 1:
                # Label v4 15ms value clearly above middle bar
                lbl_v = f"{v/1e9:.2f}B" if v >= 1e9 else f"{v/1e6:.0f}M"
                _text(ctx, bx_b + sbw / 2.0, bt - 6, lbl_v, size=10.5, color=C_BLUE, bold=True, align="center")
        glines = glbl.split("\n")
        _text(ctx, gx_c, ty1 + 19, glines[0], size=11.5, color=C_TEXT, bold=True, align="center")
        _text(ctx, gx_c, ty1 + 35, glines[1], size=10.8, color=C_MUTED, align="center")
        _text(ctx, gx_c, ty1 + 52, f"t_BOED = {rdata['boed_t_spec_factory_ms']:.1f} ms", size=10.8, color=C_TEAL, bold=True, align="center")

    # Compact legend strip under right sub-chart
    lx = tx0 + 10
    ly = ay + ah - 32
    for col, txt in (
        ((0.60, 0.65, 0.72), "v3.0 Fixed 1s"),
        (C_BLUE, "v4.0 BOED 15ms (7.61x)"),
        (C_GREEN, "v4.0 BOED 10ms (11.42x)"),
    ):
        _round_rect(ctx, lx, ly - 11, 13, 13, 3)
        ctx.set_source_rgb(*col)
        ctx.fill()
        tw = _text(ctx, lx + 18, ly, txt, size=11.2, color=C_TEXT, bold=True)
        lx += tw + 30

    # =========================================================================
    # PANEL B (Top-Right): L6 Exp131 x Exp129 Collision — M4 L=11 Percolation
    # =========================================================================
    bx, by, bw, bh = 1012, 108, 956, 514
    _draw_card(ctx, bx, by, bw, bh, "B. L6 M4 Percolation Collision: L=11 FT Yield (<=5% Dead) vs N_cand", "DT3 PASS")

    mx0, mx1 = bx + 78, bx + bw - 34
    my0, my1 = by + 76, by + bh - 82

    def _xm(nc: float) -> float:
        return mx0 + ((nc - 1.0) / 13.0) * (mx1 - mx0)

    def _ym(y_pct: float) -> float:
        return my1 - (y_pct / 105.0) * (my1 - my0)

    for yp in (0, 25, 50, 75, 99, 100):
        gy = _ym(yp)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(mx0, gy)
        ctx.line_to(mx1, gy)
        ctx.stroke()
        if yp != 99:
            _text(ctx, mx0 - 9, gy + 4, f"{yp}%", size=11.5, color=C_MUTED, align="right")

    for nc in range(1, 15):
        gx = _xm(nc)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(gx, my0)
        ctx.line_to(gx, my1)
        ctx.stroke()
        _text(ctx, gx, my1 + 20, f"{nc}", size=11.8, color=C_TEXT if nc in (6, 11) else C_MUTED, bold=(nc in (6, 11)), align="center")

    _text(ctx, (mx0 + mx1) / 2.0, my1 + 48, "Candidate Donor Slots per Resonator Node, N_cand (L=11, 121 nodes, max 6 dead)", size=13.0, color=C_TEXT, bold=True, align="center")
    _text_rot90(ctx, bx + 24, (my0 + my1) / 2.0, "FT Surface-Code Wafer Yield (%)", size=13.0, color=C_TEXT, bold=True)

    # 99% FT target horizontal line
    y99 = _ym(99.0)
    ctx.save()
    ctx.set_source_rgb(*C_RED)
    ctx.set_line_width(1.8)
    ctx.set_dash([6.0, 4.0])
    ctx.move_to(mx0, y99)
    ctx.line_to(mx1, y99)
    ctx.stroke()
    ctx.restore()
    _text(ctx, mx0 + 8, y99 - 6, "FT Target >= 99.0%", size=11.5, color=C_RED, bold=True)

    # Plot curves from exact binomial sweep + MC markers
    curves_b = [
        ("KL_canonical_f1", C_GREEN, [], 3.2, "KL Canonical f=1% (p_M4=0.486) -> N_cand* = 6"),
        ("VOKL6_HM5962_f2_lever", C_TEAL, [7.0, 4.0], 2.6, "VOKL-6 HM5962 f=2% Lever (p_M4=0.519) -> N_cand* = 6"),
        ("VOKL6_HM5962_f1", C_AMBER, [], 3.4, "VOKL-6 HM5962 f=1% Risk R1 (p_M4=0.317) -> N_cand* = 11"),
        ("VOKL6_norm_f1_worst", C_RED, [3.0, 3.0], 2.5, "VOKL-6 norm f=1% Floor (p_M4=0.045) -> N_cand* = 86 (RED-LINE)"),
    ]
    for rkey, col, dash, lw, _lbl in curves_b:
        sw = l6[rkey]["L11_sweep"]
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        for i, pt in enumerate(sw):
            px, py = _xm(pt["N_cand"]), _ym(pt["Y_FT_5pct_exact"] * 100.0)
            if i == 0:
                ctx.move_to(px, py)
            else:
                ctx.line_to(px, py)
        ctx.stroke()
        ctx.restore()
        # Draw MC validation circles where present
        for pt in sw:
            if "Y_FT_5pct_mc" in pt:
                px, py = _xm(pt["N_cand"]), _ym(pt["Y_FT_5pct_mc"] * 100.0)
                ctx.set_source_rgb(*col)
                ctx.arc(px, py, 4.8, 0, 2.0 * math.pi)
                ctx.fill()

    # Key callout dots: N=6 collapse on HM5962 (3.1%) & N=11 recovery (99.7%)
    hm_sw = l6["VOKL6_HM5962_f1"]
    x6, y6_kl = _xm(6), _ym(l6["KL_canonical_f1"]["L11_Y_FT_at_Ncand6"] * 100.0)
    y6_hm = _ym(hm_sw["L11_Y_FT_at_Ncand6"] * 100.0)
    x11, y11_hm = _xm(11), _ym(hm_sw["L11_Y_FT_at_Ncand11"] * 100.0)

    # Vertical collapse arrow at N_cand = 6
    ctx.save()
    ctx.set_source_rgb(*C_AMBER)
    ctx.set_line_width(1.8)
    ctx.set_dash([3.0, 3.0])
    ctx.move_to(x6, y6_kl + 8)
    ctx.line_to(x6, y6_hm - 8)
    ctx.stroke()
    ctx.restore()
    _text(ctx, x6 + 8, y6_kl + 44, "R1 Collapse at N=6:", size=11.5, color=C_AMBER, bold=True)
    _text(ctx, x6 + 8, y6_kl + 61, "99.2% -> 3.1%!", size=12.0, color=C_RED, bold=True)

    # N_cand* = 11 recovery badge (placed cleanly below-right of N=11 dot)
    ctx.set_source_rgb(*C_AMBER)
    ctx.arc(x11, y11_hm, 7.5, 0, 2.0 * math.pi)
    ctx.fill_preserve()
    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.set_line_width(2.0)
    ctx.stroke()
    _text(ctx, x11 + 8, y11_hm + 24, "N_cand* = 11", size=12.2, color=C_AMBER, bold=True)
    _text(ctx, x11 + 8, y11_hm + 40, "(99.74% FT)", size=11.5, color=C_TEXT)

    # Legend box (bottom-right, open space cleanly below amber/green curves)
    lgx, lgy = mx0 + 365, my1 - 122
    _round_rect(ctx, lgx, lgy, 470, 108, 8)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BORDER)
    ctx.set_line_width(1.2)
    ctx.stroke()
    for i, (_k, col, dash, _lw, lbl) in enumerate(curves_b):
        yy = lgy + 22 + i * 24
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.8)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(lgx + 12, yy - 4)
        ctx.line_to(lgx + 36, yy - 4)
        ctx.stroke()
        ctx.restore()
        _text(ctx, lgx + 44, yy, lbl, size=11.3, color=C_TEXT, bold=(i == 2))

    # Axes frame Panel B
    ctx.set_source_rgb(0.45, 0.50, 0.58)
    ctx.set_line_width(1.4)
    ctx.move_to(mx0, my0)
    ctx.line_to(mx0, my1)
    ctx.line_to(mx1, my1)
    ctx.stroke()

    # =========================================================================
    # PANEL C (Bottom-Left): L7 Unit Cost Collapse (uUSD/reg & $/d=17 Logical)
    # =========================================================================
    cx, cy, cw, ch = 32, 646, 956, 522
    _draw_card(ctx, cx, cy, cw, ch, "C. L7 Unit Cost Collapse (5-yr Fab N=1 TCO: v3 $15.23M vs v4 $16.07M)", "DT4 PASS")

    sc = l7["scenarios"]
    bc = l7["bom_and_budget_caps"]

    ux0, ux1 = cx + 235, cx + cw - 285
    uy0, uy1 = cy + 72, cy + ch - 118
    max_u = 60.0

    def _xu(v: float) -> float:
        return ux0 + (min(v, max_u) / max_u) * (ux1 - ux0)

    for tv in (0, 10, 20, 30, 40, 50, 60):
        gx = _xu(tv)
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(gx, uy0)
        ctx.line_to(gx, uy1)
        ctx.stroke()
        _text(ctx, gx, uy1 + 20, f"${tv}", size=11.5, color=C_MUTED, align="center")
    _text(ctx, (ux0 + ux1) / 2.0, uy1 + 45, "Machine Cost per Certified Register (uUSD / register, 80% uptime)", size=12.8, color=C_TEXT, bold=True, align="center")

    c_rows = [
        ("v3.0 @ KL (51%, 15 ms)", sc["v300_KL_15ms"], (0.64, 0.25, 0.25), "Baseline"),
        ("v4.0 @ HM5962 (33.3%, 15 ms)", sc["v400_VOKL6_HM5962_15ms"], C_AMBER, "-78.8% vs v3 KL"),
        ("v4.0 @ HM5962 (33.3%, 10 ms)", sc["v400_VOKL6_HM5962_10ms"], C_BLUE, "-85.8% vs v3 KL"),
        ("v4.0 @ KL (51%, 15 ms)", sc["v400_KL_15ms"], C_TEAL, "-86.2% (Write-Cap)"),
        ("v4.0 @ KL (51%, 10 ms)", sc["v400_KL_10ms"], C_GREEN, "-90.8% (Write-Cap)"),
    ]
    bh_c = 42
    bg_c = (uy1 - uy0 - len(c_rows) * bh_c) / (len(c_rows) + 1)
    for i, (lbl, srow, col, note) in enumerate(c_rows):
        ry = uy0 + bg_c + i * (bh_c + bg_c)
        _text(ctx, ux0 - 12, ry + bh_c * 0.63, lbl, size=12.4, color=C_TEXT, bold=(i in (0, 3)), align="right")
        val_u = srow["uUSD_per_register"]
        ex = _xu(val_u)
        _round_rect(ctx, ux0, ry, max(ex - ux0, 6.0), bh_c, 5)
        ctx.set_source_rgb(*col)
        ctx.fill()
        d17 = srow["usd_per_d17_logical_1overpB"]
        _text(ctx, ex + 10, ry + bh_c * 0.45, f"${val_u:.2f} uUSD/reg  ({note})", size=11.8, color=col, bold=True)
        _text(ctx, ex + 10, ry + bh_c * 0.84, f"d=17 logical: ${d17:.4f} (1/p_B)  |  K=8 phys: ${srow['uUSD_per_phys_qubit_K8']:.2f} uUSD", size=10.8, color=C_MUTED)

    # Bottom Budget Cap Survival Strip
    _round_rect(ctx, cx + 22, cy + ch - 56, cw - 44, 42, 8)
    ctx.set_source_rgb(0.93, 0.99, 0.96)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_GREEN)
    ctx.set_line_width(1.3)
    ctx.stroke()
    _text(
        ctx,
        cx + cw / 2.0,
        cy + ch - 30,
        (
            f"Budget Caps (Exp134 50k MC):  v4 HW +$420k (+10%)  |  BOM P50 = ${bc['v4_hw_p50_usd']/1e6:.2f}M  |  "
            f"P(BOM > $50M) = {bc['P_v4_BOM_gt_50M']*100:.2f}%  |  P(Prog > $100M) = {bc['P_v4_Prog_stoch_gt_100M']*100:.2f}% (<5%)"
        ),
        size=10.8,
        color=C_TEXT,
        bold=True,
        align="center",
    )

    # =========================================================================
    # PANEL D (Bottom-Right): L5 & L8 Live 4x4 Wafer + v3->v4 Scorecard
    # =========================================================================
    dx, dy, dw, dh = 1012, 646, 956, 522
    _draw_card(ctx, dx, dy, dw, dh, "D. L5/L8 Live 4x4 Wafer Execution & v3.0 -> v4.0 Master Scorecard", "DT5, DT6, DT7 PASS")

    # Left half of Panel D: Mini 4x4 live routed wafer map
    wx0, wy0 = dx + 26, dy + 80
    tsz, tgap = 78, 12
    _text(ctx, wx0 + 2 * tsz + 1.5 * tgap, dy + 68, f"Live 4x4 Wafer ({wf['working_sites']} OK / {wf['dead_sites']} Dead)", size=12.5, color=C_TEXT, bold=True, align="center")

    routed_map = {tuple(rc): i + 1 for i, rc in enumerate(wf["routed_coords"])}
    id_rc = {s["cell_id"]: (s["row"], s["col"]) for s in wf["sites"]}

    def _wctr(r: int, c: int) -> tuple[float, float]:
        return wx0 + c * (tsz + tgap) + tsz / 2.0, wy0 + r * (tsz + tgap) + tsz / 2.0

    for s in wf["sites"]:
        r, c = s["row"], s["col"]
        tx, ty = wx0 + c * (tsz + tgap), wy0 + r * (tsz + tgap)
        rnum = routed_map.get((r, c))
        if rnum is not None:
            fill, bdr, lw = (0.90, 0.99, 0.94), C_GREEN, 3.0
        elif s["status"] == "working":
            fill, bdr, lw = (0.94, 0.97, 1.0), (0.48, 0.58, 0.72), 1.4
        elif s["status"] == "crowded":
            fill, bdr, lw = (1.0, 0.96, 0.90), C_AMBER, 1.4
        else:
            fill, bdr, lw = (0.99, 0.93, 0.93), C_RED, 1.4
        _round_rect(ctx, tx, ty, tsz, tsz, 7)
        ctx.set_source_rgb(*fill)
        ctx.fill_preserve()
        ctx.set_source_rgb(*bdr)
        ctx.set_line_width(lw)
        ctx.stroke()

        top_lbl = f"M4 #{rnum}" if rnum else ("SPARE" if s["status"] == "working" else s["status"].upper())
        _text(ctx, tx + tsz / 2.0, ty + 20, top_lbl, size=10.2, color=bdr, bold=True, align="center")
        _text(ctx, tx + tsz / 2.0, ty + 42, f"R{r}C{c}", size=12.0, color=C_TEXT, bold=True, align="center")
        _text(ctx, tx + tsz / 2.0, ty + 62, f"{s['boed_ms']:.1f}ms", size=10.5, color=C_MUTED, align="center")

    # Draw purple BUS_CZ edges between routed tile borders
    for ca, cb, _h in wf["bus_edges"]:
        xa, ya = _wctr(*id_rc[ca])
        xb, yb = _wctr(*id_rc[cb])
        ux, uy = (xb - xa) / max(math.hypot(xb - xa, yb - ya), 1e-6), (yb - ya) / max(math.hypot(xb - xa, yb - ya), 1e-6)
        ctx.set_source_rgb(*C_PURPLE)
        ctx.set_line_width(5.0)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(xa + ux * (tsz * 0.44), ya + uy * (tsz * 0.44))
        ctx.line_to(xb - ux * (tsz * 0.44), yb - uy * (tsz * 0.44))
        ctx.stroke()

    # Live wafer metrics box below mini-grid
    mcert = wf["multicell_cert"]
    _round_rect(ctx, wx0, wy0 + 4 * tsz + 3 * tgap + 14, 4 * tsz + 3 * tgap, 62, 8)
    ctx.set_source_rgb(0.96, 0.95, 1.0)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_PURPLE)
    ctx.set_line_width(1.3)
    ctx.stroke()
    _text(ctx, wx0 + 174, wy0 + 4 * tsz + 3 * tgap + 36, f"CellISA v3.0 Live: F_joint = {mcert['joint_state_fidelity']:.4f}", size=12.0, color=C_PURPLE, bold=True, align="center")
    _text(ctx, wx0 + 174, wy0 + 4 * tsz + 3 * tgap + 58, f"min BUS_CZ = {mcert['min_bus_cz_fidelity']:.4f} | mean scan = {wf['mean_boed_scan_ms']:.1f} ms", size=11.0, color=C_TEXT, align="center")

    # Right half of Panel D: End-to-End v3.0 -> v4.0 Master Scorecard Table
    sx = dx + 398
    sw = dw - 418
    sy = dy + 62
    ctx.set_source_rgb(0.94, 0.96, 0.99)
    ctx.rectangle(sx, sy, sw, 28)
    ctx.fill()
    _text(ctx, sx + 10, sy + 19, "Digital Twin Layer / Metric", size=11.8, color=C_TEXT, bold=True)
    _text(ctx, sx + 250, sy + 19, "v3.0", size=11.8, color=C_MUTED, bold=True)
    _text(ctx, sx + 360, sy + 19, "v4.0 Coupled", size=11.8, color=C_TEAL, bold=True)

    e126 = l5["exp126_32d_448spec"]
    e131 = l5["exp131_m4_cavity_bus"]
    score_rows = [
        ("L1 Placement (15ms/10ms)", f"{l1['v300_orig_15ms_nm']:.2f}/{l1['v300_orig_10ms_nm']:.2f} nm", f"{l1['v400_coupled_15ms_nm']:.2f}/{l1['v400_coupled_10ms_nm']:.2f} nm"),
        ("L2 IBIC x 808nm Survival", "99.94% (base)", f"{l2['combined_implant_activation_survival']*100:.3f}% (1440K)"),
        ("L4 Mean BOED Time (KL)", "1,000.0 ms", f"{l4['KL_canonical_f1']['boed_t_spec_factory_ms']:.1f} ms (24x RO)"),
        ("L4 Throughput KL (15/10ms)", "1.97e8 / day", "1.50e9 / 2.25e9 /d"),
        ("L4 Throughput HM5962", "1.29e8 / day", "9.79e8 / 1.47e9 /d"),
        ("L5 32D Q_a2 / NbTiN Bell", "50 Ohm: 0.791", f"{e126['N32_sweetspot_Q32D_alpha2']:.3f} / {e131['nbtin_3kohm_mean_F_bell']:.3f}"),
        ("L6 M4 L=11 N_cand* (99%)", "N=6 (KL only)", "6 (KL) | 11 (HM5962)"),
        ("L7 Machine Cost (KL 15ms)", "$52.88 uUSD/reg", "$7.33 (-86.2%)"),
        ("L7 d=17 Logical (KL / HM)", "$0.0598 / d=17", "$0.0083 / $0.0195"),
    ]
    for i, (k_t, v3_t, v4_t) in enumerate(score_rows):
        ry = sy + 48 + i * 38
        if i % 2 == 1:
            ctx.set_source_rgb(0.985, 0.990, 0.996)
            ctx.rectangle(sx, ry - 20, sw, 34)
            ctx.fill()
        ctx.set_source_rgb(*C_GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(sx, ry + 14)
        ctx.line_to(sx + sw, ry + 14)
        ctx.stroke()
        _text(ctx, sx + 10, ry + 2, k_t, size=11.3, color=C_TEXT, bold=True)
        _text(ctx, sx + 250, ry + 2, v3_t, size=11.2, color=C_MUTED)
        _text(ctx, sx + 360, ry + 2, v4_t, size=11.3, color=C_GREEN if i in (3, 4, 7, 8) else C_TEAL, bold=True)

    # Master SHA-256 Seal at bottom-right of Panel D
    _round_rect(ctx, sx, dy + dh - 56, sw, 42, 8)
    ctx.set_source_rgb(0.06, 0.09, 0.16)
    ctx.fill()
    _text(
        ctx,
        sx + sw / 2.0,
        dy + dh - 38,
        "v4.0 DIGITAL TWIN MASTER CERT: 7/7 PASS  |  11 LEDGERS SHA-256 LINKED",
        size=10.2,
        color=(0.45, 0.96, 0.78),
        bold=True,
        align="center",
    )
    _text(
        ctx,
        sx + sw / 2.0,
        dy + dh - 21,
        f"SHA-256: {mc['sha256']}",
        size=9.0,
        color=(0.82, 0.88, 0.96),
        align="center",
        family="DejaVu Sans Mono",
    )

    out_path = OUT_DIR / "fig_exp135_v4_digital_twin.png"
    surf.write_to_png(str(out_path))
    return out_path


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    p = plot_digital_twin(data)
    print(f"Wrote {p.name}")


if __name__ == "__main__":
    main()
