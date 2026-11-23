"""Exp129 PyCairo Figure Generator (runs on system Python with cairo + PIL).

Generates two publication-grade PNG figures from results/exp129_valley_orbital_hyperfine/plot_data_exp129.json:
  1. fig_exp129_endor_shells.png — 31P Td valley-orbit spectrum, VOKL-6 radial envelope contraction,
     and out-of-sample 29Si ENDOR / LMTO-GF shell benchmark ablation.
  2. fig_exp129_vokl6_yield.png  — Mode B K=8 selection yield (N=400, 95% Wilson CI), min_gap CDF
     with Exp126 6.89 kHz DDRF threshold, and radial bath coupling breakdown.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cairo

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp129_valley_orbital_hyperfine"
DATA_PATH = OUT_DIR / "plot_data_exp129.json"

# Colorblind-safe Okabe-Ito / Slate scientific palette
BG = (0.985, 0.988, 0.994)
PANEL_BG = (1.0, 1.0, 1.0)
BORDER = (0.80, 0.84, 0.89)
GRID = (0.90, 0.92, 0.95)
TEXT = (0.11, 0.14, 0.19)
MUTED = (0.38, 0.44, 0.52)

C_KL = (0.16, 0.44, 0.72)       # Deep Blue — Legacy KL
C_EMT = (0.45, 0.52, 0.60)      # Slate — Bare EMT
C_ENV = (0.90, 0.56, 0.12)      # Amber — VOKL-6 envelope only
C_VOKL = (0.80, 0.19, 0.22)     # Crimson — Full VOKL-6 (primary)
C_ABINIT = (0.12, 0.58, 0.42)   # Emerald — VOKL-6 ab-initio / positive
C_PT = (0.55, 0.34, 0.72)       # Purple — VOKL-6 point-dipole
C_TGT = (0.12, 0.16, 0.22)      # Charcoal — Experimental/LMTO target
C_WARN = (0.85, 0.22, 0.18)     # Alert Red — 6.89 kHz threshold


def set_font(ctx: cairo.Context, size: float, bold: bool = False) -> None:
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)


def draw_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 13.0,
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
    size: float = 13.0,
    color: tuple[float, float, float] = TEXT,
    bold: bool = False,
) -> None:
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(-math.pi / 2.0)
    draw_text(ctx, text, 0.0, 0.0, size=size, color=color, bold=bold, align="center")
    ctx.restore()


def draw_panel_box(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str) -> None:
    ctx.set_source_rgb(*PANEL_BG)
    ctx.rectangle(x, y, w, h)
    ctx.fill()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.3)
    ctx.rectangle(x, y, w, h)
    ctx.stroke()
    draw_text(ctx, title, x + 14, y + 25, size=14.5, color=TEXT, bold=True)


def map_x(val: float, xmin: float, xmax: float, px0: float, pw: float) -> float:
    return px0 + (val - xmin) / (xmax - xmin) * pw


def map_y(val: float, ymin: float, ymax: float, py0: float, ph: float) -> float:
    return py0 + ph - (val - ymin) / (ymax - ymin) * ph


def draw_dashed_line(
    ctx: cairo.Context,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: tuple[float, float, float],
    width: float = 1.4,
    dash: tuple[float, float] = (6.0, 4.0),
) -> None:
    ctx.save()
    ctx.set_source_rgb(*color)
    ctx.set_line_width(width)
    ctx.set_dash(dash)
    ctx.move_to(x1, y1)
    ctx.line_to(x2, y2)
    ctx.stroke()
    ctx.restore()


# ---------------------------------------------------------------------------
# Figure 1: ENDOR Shells, 31P Td Spectrum, and Radial Envelope Contraction
# ---------------------------------------------------------------------------
def plot_endor_shells(data: dict[str, Any], out_path: Path) -> None:
    W, H = 1600, 960
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Header banner
    draw_text(
        ctx,
        "Exp129 (H147): VOKL-6 6-Vadi Merkez-Hücre Teorisi — ³¹P Spektrumu, Zarf Daralması & ²⁹Si ENDOR Kıyaslaması",
        28, 34, size=19.5, bold=True, color=TEXT,
    )
    draw_text(
        ctx,
        "Sıfır ²⁹Si uydurma (yalnız ³¹P A1=-45,59 meV, T2-A1=11,70 meV, E-A1=13,01 meV, A_P(0)=117,53 MHz) + 145-PW CB-EPM k-Bloch | no_lab_measurement=true",
        28, 57, size=12.5, color=MUTED,
    )

    # ---------------- Panel A (Top-Left): 31P 1s Valley-Orbit Multiplet ----------------
    ax, ay, aw, ah = 24, 76, 748, 392
    draw_panel_box(ctx, ax, ay, aw, ah, "A. ³¹P 1s Vadi-Yörünge Çoklusu (Td Simetrisi, H_6v 216×216)")
    px0, py0, pw, ph = ax + 82, ay + 52, aw - 110, ah - 96
    ymin, ymax = -50.0, -24.0

    # Grid & y-axis
    for e_val in (-50, -45, -40, -35, -30, -25):
        yy = map_y(e_val, ymin, ymax, py0, ph)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()
        draw_text(ctx, f"{e_val:d}", px0 - 10, yy + 4.5, size=11.5, color=MUTED, align="right")

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.2)
    ctx.move_to(px0, py0)
    ctx.line_to(px0, py0 + ph)
    ctx.line_to(px0 + pw, py0 + ph)
    ctx.stroke()
    draw_rot_text(ctx, "Bağlanma Enerjisi E (meV)", ax + 24, py0 + ph / 2.0, size=12.5, bold=True)

    # Column 1: Bare EMT (-31.26 meV, 6x degenerate)
    e_emt = data["bare_emt"]["E_emt_1s_meV"]
    y_emt = map_y(e_emt, ymin, ymax, py0, ph)
    x_emt0, x_emt1 = px0 + 40, px0 + 185
    ctx.set_source_rgb(*C_EMT)
    ctx.set_line_width(4.0)
    ctx.move_to(x_emt0, y_emt)
    ctx.line_to(x_emt1, y_emt)
    ctx.stroke()
    draw_text(ctx, f"Yalın EMT (6×): {e_emt:.2f} meV", (x_emt0 + x_emt1) / 2.0, y_emt - 11, size=11.5, color=C_EMT, bold=True, align="center")
    draw_text(ctx, "Faulkner 1969: -31,27 meV", (x_emt0 + x_emt1) / 2.0, y_emt + 18, size=10.5, color=MUTED, align="center")
    draw_text(ctx, "V_cc = 0 (Yalın EMT)", (x_emt0 + x_emt1) / 2.0, py0 + ph + 22, size=12.0, bold=True, align="center")

    # Column 2: VOKL-6 Td split states
    cal = data["calibration"]
    e_a1 = cal["E_1s_A1_meV"]
    e_t2 = cal["E_1s_T2_meV"]
    e_e = cal["E_1s_E_meV"]
    x_v0, x_v1 = px0 + 300, px0 + 465

    levels = [
        (e_e, "1s(E)  [2×]", C_ENV, -10),
        (e_t2, "1s(T2) [3×]", C_KL, 16),
        (e_a1, "1s(A1) [1×]", C_VOKL, -10),
    ]
    for ev, lbl, col, dy_lbl in levels:
        yy = map_y(ev, ymin, ymax, py0, ph)
        draw_dashed_line(ctx, x_emt1 + 6, y_emt, x_v0 - 6, yy, (0.72, 0.76, 0.82), width=1.1, dash=(4.0, 4.0))
        ctx.set_source_rgb(*col)
        ctx.set_line_width(4.2)
        ctx.move_to(x_v0, yy)
        ctx.line_to(x_v1, yy)
        ctx.stroke()
        draw_text(ctx, f"{lbl}: {ev:.2f} meV", x_v1 + 10, yy + 4.5, size=11.5, color=col, bold=True)

    draw_text(ctx, "VOKL-6 (H_6v Merkez-Hücre)", (x_v0 + x_v1) / 2.0, py0 + ph + 22, size=12.0, bold=True, align="center")

    # Splitting arrows between A1 and T2/E
    y_a1 = map_y(e_a1, ymin, ymax, py0, ph)
    y_t2 = map_y(e_t2, ymin, ymax, py0, ph)
    y_e = map_y(e_e, ymin, ymax, py0, ph)
    ctx.set_source_rgb(*C_KL)
    ctx.set_line_width(1.6)
    ctx.move_to(x_v0 + 30, y_a1 - 4)
    ctx.line_to(x_v0 + 30, y_t2 + 4)
    ctx.stroke()
    draw_text(ctx, "ΔT2 = 11,70 meV", x_v0 + 36, (y_a1 + y_t2) / 2.0 + 4, size=10.5, color=C_KL, bold=True)

    ctx.set_source_rgb(*C_ENV)
    ctx.move_to(x_v0 + 135, y_a1 - 4)
    ctx.line_to(x_v0 + 135, y_e + 4)
    ctx.stroke()
    draw_text(ctx, "ΔE = 13,01 meV", x_v0 + 142, (y_a1 + y_t2) / 2.0 + 4, size=10.5, color=C_ENV, bold=True)

    # Parameter callout box bottom-left inside Panel A
    bx, by_box, bw, bh = px0 + 16, py0 + ph - 76, 255, 66
    ctx.set_source_rgb(0.96, 0.97, 0.99)
    ctx.rectangle(bx, by_box, bw, bh)
    ctx.fill()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.rectangle(bx, by_box, bw, bh)
    ctx.stroke()
    p = cal["params"]
    draw_text(ctx, f"A_P(0) = {cal['A_P_0_MHz']:.2f} MHz (η_P = {p['eta_P_used']:.1f})", bx + 10, by_box + 19, size=11.0, bold=True, color=C_VOKL)
    draw_text(ctx, f"r_c = {p['r_c_nm']:.3f} nm | U_i = {p['U_intra_meV']:.0f} meV", bx + 10, by_box + 38, size=10.5, color=TEXT)
    draw_text(ctx, f"U_g = {p['U_g_meV']:.1f}, U_f = {p['U_f_meV']:.1f} meV (U_f > U_g)", bx + 10, by_box + 56, size=10.5, color=MUTED)

    # ---------------- Panel B (Top-Right): Radial Envelope Contraction ----------------
    bx_p, by_p, bw_p, bh_p = 796, 76, 780, 392
    draw_panel_box(ctx, bx_p, by_p, bw_p, bh_p, "B. Tek-Vadi Zarf Profili |F(r)| (Log) — Merkez-Hücre Cusp & Kuyruk Daralması")
    px0, py0, pw, ph = bx_p + 84, by_p + 52, bw_p - 114, bh_p - 96
    xmin, xmax = 0.0, 5.5
    lmin, lmax = -2.5, 0.0  # log10(|F(r)| in nm^-3/2)

    for lv in (-2.5, -2.0, -1.5, -1.0, -0.5, 0.0):
        yy = map_y(lv, lmin, lmax, py0, ph)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()
        lbl = f"10^{lv:.1f}" if lv % 1 != 0 else f"10^{int(lv)}"
        draw_text(ctx, lbl, px0 - 8, yy + 4.5, size=11.0, color=MUTED, align="right")

    for rv in (0, 1, 2, 3, 4, 5):
        xx = map_x(rv, xmin, xmax, px0, pw)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(xx, py0)
        ctx.line_to(xx, py0 + ph)
        ctx.stroke()
        draw_text(ctx, f"{rv}", xx, py0 + ph + 18, size=11.5, color=MUTED, align="center")

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.2)
    ctx.move_to(px0, py0)
    ctx.line_to(px0, py0 + ph)
    ctx.line_to(px0 + pw, py0 + ph)
    ctx.stroke()
    draw_text(ctx, "Yarıçap r (nm)", px0 + pw / 2.0, py0 + ph + 36, size=12.5, bold=True, align="center")
    draw_rot_text(ctx, "|F_1v(r)| (nm^-3/2)", bx_p + 24, py0 + ph / 2.0, size=12.5, bold=True)

    # Shaded inner ENDOR shell region (r <= 0.65 nm)
    x_sh = map_x(0.65, xmin, xmax, px0, pw)
    ctx.set_source_rgba(0.95, 0.85, 0.60, 0.22)
    ctx.rectangle(px0, py0, x_sh - px0, ph)
    ctx.fill()
    draw_text(ctx, "ENDOR", (px0 + x_sh) / 2.0, py0 + ph - 10, size=9.5, color=(0.65, 0.42, 0.08), bold=True, align="center")

    prof = data["profiles"]
    r_arr = prof["r_nm"]

    def draw_curve(vals: list[float], color: tuple[float, float, float], width: float, dashed: bool = False) -> None:
        ctx.save()
        ctx.set_source_rgb(*color)
        ctx.set_line_width(width)
        if dashed:
            ctx.set_dash((6.0, 4.0))
        started = False
        for rv, fv in zip(r_arr, vals):
            lv = math.log10(max(abs(fv), 1e-6))
            if lv < lmin:
                continue
            xx = map_x(rv, xmin, xmax, px0, pw)
            yy = map_y(min(lv, lmax), lmin, lmax, py0, ph)
            if not started:
                ctx.move_to(xx, yy)
                started = True
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        ctx.restore()

    draw_curve(prof["F_kl_perp"], C_KL, 2.4, dashed=False)
    draw_curve(prof["F_kl_par"], C_KL, 1.8, dashed=True)
    draw_curve(prof["F_emt_perp"], C_EMT, 1.8, dashed=False)
    draw_curve(prof["F_vokl6_perp"], C_VOKL, 2.8, dashed=False)
    draw_curve(prof["F_vokl6_par"], C_VOKL, 2.0, dashed=True)

    # Legend inside Panel B (top-right)
    lx, ly = px0 + pw - 295, py0 + 10
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.94)
    ctx.rectangle(lx, ly, 288, 108)
    ctx.fill()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.rectangle(lx, ly, 288, 108)
    ctx.stroke()
    leg_items = [
        (C_VOKL, False, "VOKL-6 dik (a_⊥=1,75 nm)"),
        (C_VOKL, True,  "VOKL-6 eksenel (a_∥=0,96 nm)"),
        (C_KL,   False, "Eski KL dik (a=2,50 nm)"),
        (C_KL,   True,  "Eski KL eksenel (b=1,40 nm)"),
        (C_EMT,  False, "Yalın EMT dik (2,42 nm)"),
    ]
    for idx, (col, dsh, lbl) in enumerate(leg_items):
        yy = ly + 18 + idx * 19
        if dsh:
            draw_dashed_line(ctx, lx + 10, yy - 4, lx + 38, yy - 4, col, width=2.2, dash=(5.0, 3.0))
        else:
            ctx.set_source_rgb(*col)
            ctx.set_line_width(2.6)
            ctx.move_to(lx + 10, yy - 4)
            ctx.line_to(lx + 38, yy - 4)
            ctx.stroke()
        draw_text(ctx, lbl, lx + 46, yy, size=11.0, color=TEXT)

    # ---------------- Panel C (Bottom Full-Width): ENDOR Shell Ratio Ablation ----------------
    cx, cy, cw, ch = 24, 492, 1552, 444
    draw_panel_box(ctx, cx, cy, cw, ch, "C. Örneklem-Dışı ²⁹Si ENDOR & LMTO-GF Kabuk Oranları R = A(kabuk) / A(0,0,4) [Log Ölçek — Sıfır Kabuk Uydurması]")
    px0, py0, pw, ph = cx + 88, cy + 56, cw - 120, ch - 134
    lmin, lmax = -3.8, 0.1  # 1.6e-4 to 1.26

    for lv in (-3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0):
        yy = map_y(lv, lmin, lmax, py0, ph)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()
        if abs(lv - round(lv)) < 1e-6:
            lbl = f"10^{int(round(lv))}" if lv != 0 else "1.0"
            draw_text(ctx, lbl, px0 - 10, yy + 4.5, size=11.5, color=MUTED, align="right")

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.2)
    ctx.move_to(px0, py0)
    ctx.line_to(px0, py0 + ph)
    ctx.line_to(px0 + pw, py0 + ph)
    ctx.stroke()
    draw_rot_text(ctx, "Kabuk Oranı R = A / A(0,0,4)", cx + 26, py0 + ph / 2.0, size=12.5, bold=True)

    shells_order = ["(1,1,1)", "(3,3,1)", "(2,2,0)", "(1,1,-3)", "(4,4,0)", "(0,0,8)"]
    shell_sub = [
        "1. komşu (B, Exp)",
        "[110] zincir (B, Exp)",
        "2. komşu (A, LMTO)",
        "Asimetrik (B, LMTO)",
        "İleri öngörü (A)",
        "İleri öngörü (A)",
    ]
    bm = data["benchmarks"]
    targets = bm["targets"]
    models = [
        ("KL_legacy", "Eski KL (Exp25)", C_KL),
        ("EMT_bare_k085", "Yalın EMT (k0=0,85)", C_EMT),
        ("VOKL6_envelope_only", "VOKL-6 Zarf (sabit k0)", C_ENV),
        ("VOKL6_full_k085", "Tam VOKL-6 + k-Bloch", C_VOKL),
    ]

    n_grp = len(shells_order)
    grp_w = pw / n_grp
    n_bars = 5  # Target + 4 models (for audited shells; 4 models for forward shells)
    bar_w = min(30.0, (grp_w - 34.0) / n_bars)

    for gi, sname in enumerate(shells_order):
        gx_center = px0 + (gi + 0.5) * grp_w
        has_tgt = sname in targets
        items_here = []
        if has_tgt:
            items_here.append((targets[sname]["target_ratio"], C_TGT, True))
        for mkey, _mlbl, mcol in models:
            items_here.append((bm[mkey]["ratios"][sname], mcol, False))

        tot_w = len(items_here) * (bar_w + 3.0) - 3.0
        x_start = gx_center - tot_w / 2.0

        # Vertical separator between audited (0..3) and forward (4..5)
        if gi == 4:
            x_sep = px0 + gi * grp_w
            draw_dashed_line(ctx, x_sep, py0, x_sep, py0 + ph, (0.55, 0.60, 0.68), width=1.4, dash=(6.0, 4.0))

        for bi, (val, col, is_tgt) in enumerate(items_here):
            bx_bar = x_start + bi * (bar_w + 3.0)
            lv = max(lmin + 0.05, math.log10(max(val, 1e-6)))
            y_top = map_y(min(lv, lmax), lmin, lmax, py0, ph)
            y_bot = py0 + ph
            ctx.set_source_rgb(*col)
            ctx.rectangle(bx_bar, y_top, bar_w, y_bot - y_top)
            ctx.fill()
            if is_tgt:
                ctx.set_source_rgb(1.0, 1.0, 1.0)
                ctx.set_line_width(1.2)
                ctx.rectangle(bx_bar + 1, y_top + 1, bar_w - 2, max(1.0, y_bot - y_top - 2))
                ctx.stroke()

            # Crisp label for key bars (Target, KL, Full VOKL-6)
            if is_tgt or bi == len(items_here) - 1 or (has_tgt and bi == 1):
                txt_v = f"{val:.3f}" if val >= 0.01 else f"{val:.4f}"
                draw_text(ctx, txt_v, bx_bar + bar_w / 2.0, y_top - 5, size=9.5, color=col, bold=is_tgt or (bi == len(items_here) - 1), align="center")

        draw_text(ctx, sname, gx_center, py0 + ph + 20, size=13.0, bold=True, color=TEXT, align="center")
        draw_text(ctx, shell_sub[gi], gx_center, py0 + ph + 37, size=10.5, color=MUTED, align="center")

    # Legend bar at bottom of Panel C
    leg_entries = [("Hedef (ENDOR / LMTO-GF)", C_TGT)] + [(lbl, col) for _, lbl, col in models]
    lx_cur = px0 + 10
    ly_leg = py0 + ph + 62
    for lbl, col in leg_entries:
        ctx.set_source_rgb(*col)
        ctx.rectangle(lx_cur, ly_leg - 10, 16, 11)
        ctx.fill()
        draw_text(ctx, lbl, lx_cur + 22, ly_leg, size=11.5, color=TEXT, bold=(col == C_VOKL or col == C_TGT))
        lx_cur += 215

    # Honest physical diagnostic callout in open upper-middle sky above (2,2,0) & (1,1,-3)
    dx_b, dy_b, dw_b, dh_b = px0 + int(0.345 * pw), py0 + 8, 435, 62
    ctx.set_source_rgba(1.0, 0.96, 0.95, 0.97)
    ctx.rectangle(dx_b, dy_b, dw_b, dh_b)
    ctx.fill()
    ctx.set_source_rgb(*C_VOKL)
    ctx.set_line_width(1.2)
    ctx.rectangle(dx_b, dy_b, dw_b, dh_b)
    ctx.stroke()
    draw_text(ctx, "Dürüst Fiziğin Sınırı (CE3/CE4 FAIL Kök-Nedeni):", dx_b + 10, dy_b + 19, size=11.0, bold=True, color=C_VOKL)
    draw_text(ctx, "k-Bloch (1,1,1)'i onarır ve (1,1,-3)'ü 3,1× artırır; ancak (3,3,1) [110]", dx_b + 10, dy_b + 37, size=10.3, color=TEXT)
    draw_text(ctx, "kovalent bağ zinciri tüm-elektron çekirdek-polarizasyon/3d DFT gerektirir.", dx_b + 10, dy_b + 53, size=10.3, color=MUTED)

    surf.write_to_png(str(out_path))


# ---------------------------------------------------------------------------
# Figure 2: Mode B K=8 Yield, 6.89 kHz Gap CDF, and Radial Bath Coupling
# ---------------------------------------------------------------------------
def plot_vokl6_yield(data: dict[str, Any], out_path: Path) -> None:
    W, H = 1600, 960
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    draw_text(
        ctx,
        "Exp129 (H147): Mod B Epitaksiyel Banyo K=8 Verimi (N=400/Hücre) & Exp126 6,89 kHz DDRF Boşluk Riski",
        28, 34, size=19.5, bold=True, color=TEXT,
    )
    draw_text(
        ctx,
        "Eski KL (Exp59/62) vs İlk-İlkeler VOKL-6 (normalize + genişletilmiş/nokta dipol & ab-initio) | B || [123], GAUSS500, K=8 | no_lab_measurement=true",
        28, 57, size=12.5, color=MUTED,
    )

    mb = data["mode_b_yield_n400"]

    # ---------------- Panel A (Top-Left): Mode B K=8 Yield with 95% Wilson CI ----------------
    ax, ay, aw, ah = 24, 76, 756, 405
    draw_panel_box(ctx, ax, ay, aw, ah, "A. Mod B K=8 Sertifikalı Verimi (% — 95% Wilson CI, N=400)")
    px0, py0, pw, ph = ax + 78, ay + 54, aw - 106, ah - 116
    ymin, ymax = 0.0, 95.0

    for yv in (0, 20, 40, 60, 80):
        yy = map_y(yv, ymin, ymax, py0, ph)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()
        draw_text(ctx, f"%{yv}", px0 - 10, yy + 4.5, size=11.5, color=MUTED, align="right")

    # 40% CE6 product floor line (label on open left side above f=0.5%)
    y40 = map_y(40.0, ymin, ymax, py0, ph)
    draw_dashed_line(ctx, px0, y40, px0 + pw, y40, (0.45, 0.50, 0.58), width=1.2, dash=(5.0, 4.0))
    draw_text(ctx, "CE6 f=%1 eşiği (%40)", px0 + 8, y40 - 6, size=10.0, color=MUTED, align="left")

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.2)
    ctx.move_to(px0, py0)
    ctx.line_to(px0, py0 + ph)
    ctx.line_to(px0 + pw, py0 + ph)
    ctx.stroke()
    draw_rot_text(ctx, "Sertifikalı K=8 Verimi (%)", ax + 24, py0 + ph / 2.0, size=12.5, bold=True)

    f_keys = [("F0.5", "f = %0,5\n(M=226)"), ("F1", "f = %1,0\n(M=452)"), ("F2", "f = %2,0\n(M=904)")]
    m_spec = [
        ("KL_legacy", "Eski KL (Exp59/62, 2,981 MHz)", C_KL),
        ("VOKL6_norm_ext", "VOKL-6 (repo 2,981 MHz)", C_VOKL),
        ("VOKL6_HM5962_ext", "VOKL-6 (HM 5,962 MHz H=a S·I)", C_ABINIT),
        ("VOKL6_abinit_ext", "VOKL-6 (ab-initio η=186, A/2)", C_PT),
    ]
    grp_w = pw / len(f_keys)
    bar_w = 34.0

    for gi, (fk, flbl) in enumerate(f_keys):
        gx_c = px0 + (gi + 0.5) * grp_w
        tot_w = len(m_spec) * (bar_w + 4.0) - 4.0
        x0 = gx_c - tot_w / 2.0

        for bi, (mk, _ml, col) in enumerate(m_spec):
            cell = mb[mk][fk]
            ypct = cell["yield_frac"] * 100.0
            ci_lo, ci_hi = cell["wilson_ci95"][0] * 100.0, cell["wilson_ci95"][1] * 100.0
            bx = x0 + bi * (bar_w + 4.0)
            y_top = map_y(ypct, ymin, ymax, py0, ph)
            y_bot = py0 + ph
            ctx.set_source_rgb(*col)
            ctx.rectangle(bx, y_top, bar_w, y_bot - y_top)
            ctx.fill()

            # Wilson 95% CI error bar
            y_lo = map_y(ci_lo, ymin, ymax, py0, ph)
            y_hi = map_y(ci_hi, ymin, ymax, py0, ph)
            xc = bx + bar_w / 2.0
            ctx.set_source_rgb(*TEXT)
            ctx.set_line_width(1.6)
            ctx.move_to(xc, y_lo)
            ctx.line_to(xc, y_hi)
            ctx.move_to(xc - 4.5, y_lo)
            ctx.line_to(xc + 4.5, y_lo)
            ctx.move_to(xc - 4.5, y_hi)
            ctx.line_to(xc + 4.5, y_hi)
            ctx.stroke()

            draw_text(ctx, f"{ypct:.1f}", xc, y_hi - 5, size=9.8, color=col, bold=(bi in (0, 1)), align="center")

        # Legacy Exp60 EXT_DIAG blow-up marker at f=0.5% (69%)
        if fk == "F0.5":
            y69 = map_y(69.0, ymin, ymax, py0, ph)
            draw_dashed_line(ctx, x0 - 4, y69, x0 + tot_w + 4, y69, C_ENV, width=1.8, dash=(4.0, 3.0))
            draw_text(ctx, "Exp60 EXT_DIAG: %69 (+43p)", gx_c, y69 - 6, size=9.8, color=(0.72, 0.42, 0.05), bold=True, align="center")

        l1, l2 = flbl.split("\n")
        draw_text(ctx, l1, gx_c, py0 + ph + 19, size=12.0, bold=True, align="center")
        draw_text(ctx, l2, gx_c, py0 + ph + 35, size=10.5, color=MUTED, align="center")

    # Legend under Panel A
    lx, ly = px0 - 10, py0 + ph + 54
    for idx, (_mk, mlbl, col) in enumerate(m_spec):
        xx = lx + (idx % 2) * 320
        yy = ly + (idx // 2) * 18
        ctx.set_source_rgb(*col)
        ctx.rectangle(xx, yy - 9, 14, 10)
        ctx.fill()
        draw_text(ctx, mlbl, xx + 20, yy, size=10.8, color=TEXT, bold=(idx <= 1))

    # ---------------- Panel B (Top-Right): F1 min_gap CDF & 6.89 kHz DDRF Risk ----------------
    bx_p, by_p, bw_p, bh_p = 804, 76, 772, 405
    draw_panel_box(ctx, bx_p, by_p, bw_p, bh_p, "B. Sertifikalı K=8 min_gap Kümülatif Dağılımı (f = %1,0, N=400)")
    px0, py0, pw, ph = bx_p + 78, by_p + 54, bw_p - 106, bh_p - 104
    xmin, xmax = 0.0, 26.0  # kHz
    ymin, ymax = 0.0, 1.02

    # Shaded Exp126 DDRF risk zone (< 6.893 kHz)
    x_689 = map_x(6.893, xmin, xmax, px0, pw)
    ctx.set_source_rgba(0.92, 0.25, 0.22, 0.11)
    ctx.rectangle(px0, py0, x_689 - px0, ph)
    ctx.fill()

    for yv in (0.0, 0.25, 0.50, 0.75, 1.0):
        yy = map_y(yv, ymin, ymax, py0, ph)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()
        draw_text(ctx, f"{int(yv*100)}%", px0 - 10, yy + 4.5, size=11.0, color=MUTED, align="right")

    for xv in (0, 5, 10, 15, 20, 25):
        xx = map_x(xv, xmin, xmax, px0, pw)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(xx, py0)
        ctx.line_to(xx, py0 + ph)
        ctx.stroke()
        draw_text(ctx, f"{xv}", xx, py0 + ph + 18, size=11.5, color=MUTED, align="center")

    # Vertical threshold lines (clean non-overlapping label placement)
    draw_dashed_line(ctx, x_689, py0, x_689, py0 + ph, C_WARN, width=2.0, dash=(6.0, 3.0))
    draw_text(ctx, "Exp126 F1 q3", x_689 - 6, py0 + 30, size=10.3, color=C_WARN, bold=True, align="right")
    draw_text(ctx, "6,89 kHz risk", x_689 - 6, py0 + 44, size=10.3, color=C_WARN, bold=True, align="right")

    x_10 = map_x(10.0, xmin, xmax, px0, pw)
    draw_dashed_line(ctx, x_10, py0, x_10, py0 + ph, MUTED, width=1.3, dash=(4.0, 4.0))
    draw_text(ctx, "10 kHz", x_10 + 5, py0 + ph - 12, size=10.0, color=MUTED, bold=True)

    x_16 = map_x(16.0, xmin, xmax, px0, pw)
    draw_dashed_line(ctx, x_16, py0, x_16, py0 + ph, MUTED, width=1.2, dash=(3.0, 4.0))
    draw_text(ctx, "16 kHz (N_dd=16)", x_16 + 5, py0 + 34, size=10.0, color=MUTED, bold=True)

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.2)
    ctx.move_to(px0, py0)
    ctx.line_to(px0, py0 + ph)
    ctx.line_to(px0 + pw, py0 + ph)
    ctx.stroke()
    draw_text(ctx, "En Küçük Geçiş Boşluğu min_gap (kHz)", px0 + pw / 2.0, py0 + ph + 38, size=12.5, bold=True, align="center")
    draw_rot_text(ctx, "Kümülatif Olasılık P(min_gap ≤ x)", bx_p + 24, py0 + ph / 2.0, size=12.5, bold=True)

    cdfs = data["gap_cdfs"]
    cdf_curves = [
        ("KL_legacy", "Eski KL", C_KL, 2.5, False),
        ("VOKL6_norm_ext", "VOKL-6 (2,981 MHz)", C_VOKL, 2.8, False),
        ("VOKL6_HM5962_ext", "VOKL-6 (HM 5,962)", C_ABINIT, 2.4, False),
        ("VOKL6_abinit_ext", "VOKL-6 (ab-initio)", C_PT, 1.8, True),
    ]
    for mk, _lbl, col, lw, dsh in cdf_curves:
        arr = cdfs[mk]["F1"]
        if not arr:
            continue
        ctx.save()
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        if dsh:
            ctx.set_dash((5.0, 3.0))
        n = len(arr)
        ctx.move_to(map_x(0.0, xmin, xmax, px0, pw), map_y(0.0, ymin, ymax, py0, ph))
        for i, g_hz in enumerate(arr):
            gx_khz = min(g_hz / 1000.0, xmax)
            xx = map_x(gx_khz, xmin, xmax, px0, pw)
            yy = map_y((i + 1) / n, ymin, ymax, py0, ph)
            ctx.line_to(xx, yy)
        ctx.line_to(map_x(xmax, xmin, xmax, px0, pw), map_y(1.0, ymin, ymax, py0, ph))
        ctx.stroke()
        ctx.restore()

    # Summary legend box bottom-right inside Panel B (aligned columns)
    lx, ly, lw_b, lh_b = px0 + pw - 338, py0 + ph - 110, 330, 102
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
    ctx.rectangle(lx, ly, lw_b, lh_b)
    ctx.fill()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.rectangle(lx, ly, lw_b, lh_b)
    ctx.stroke()
    draw_text(ctx, "f=%1,0 Model", lx + 36, ly + 18, size=10.0, bold=True, color=MUTED)
    draw_text(ctx, "Medyan", lx + 236, ly + 18, size=10.0, bold=True, color=MUTED, align="right")
    draw_text(ctx, "<6,89kHz", lx + 318, ly + 18, size=10.0, bold=True, color=MUTED, align="right")
    for idx, (mk, lbl, col, _lw, dsh) in enumerate(cdf_curves):
        gs = mb[mk]["F1"]["gap_stats"]
        yy = ly + 37 + idx * 19
        if dsh:
            draw_dashed_line(ctx, lx + 10, yy - 4, lx + 30, yy - 4, col, width=2.0, dash=(4.0, 2.0))
        else:
            ctx.set_source_rgb(*col)
            ctx.set_line_width(2.6)
            ctx.move_to(lx + 10, yy - 4)
            ctx.line_to(lx + 30, yy - 4)
            ctx.stroke()
        is_b = idx <= 2
        draw_text(ctx, lbl, lx + 36, yy, size=10.2, color=TEXT, bold=is_b)
        draw_text(ctx, f"{gs['median_Hz']/1e3:.2f} kHz", lx + 236, yy, size=10.2, color=TEXT, bold=is_b, align="right")
        draw_text(ctx, f"%{100*gs['frac_lt_6893Hz']:.1f}", lx + 318, yy, size=10.2, color=col if is_b else TEXT, bold=is_b, align="right")

    # ---------------- Panel C (Bottom-Left): Radial Bath Coupling Shift ----------------
    cx, cy, cw, ch = 24, 502, 756, 434
    draw_panel_box(ctx, cx, cy, cw, ch, "C. Radyal ²⁹Si Aşırı-İnce Bağ Medyanı |A(r)| (45.214 Örgü Noktası)")
    px0, py0, pw, ph = cx + 84, cy + 54, cw - 114, ch - 104
    xmin, xmax = 0.0, 6.0
    lmin, lmax = 1.0, 6.2  # 10 Hz to 1.6 MHz

    for lv in (1, 2, 3, 4, 5, 6):
        yy = map_y(lv, lmin, lmax, py0, ph)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()
        lbl_map = {1: "10 Hz", 2: "100 Hz", 3: "1 kHz", 4: "10 kHz", 5: "100 kHz", 6: "1 MHz"}
        draw_text(ctx, lbl_map[lv], px0 - 10, yy + 4.5, size=11.0, color=MUTED, align="right")

    # 10 kHz strong coupling line (label cleanly on bottom-left away from 4-5nm dot)
    y10k = map_y(4.0, lmin, lmax, py0, ph)
    draw_dashed_line(ctx, px0, y10k, px0 + pw, y10k, C_ABINIT, width=1.6, dash=(6.0, 4.0))
    draw_text(ctx, "Güçlü bağ eşiği (10 kHz)", px0 + 8, y10k + 15, size=10.3, color=C_ABINIT, bold=True, align="left")

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.2)
    ctx.move_to(px0, py0)
    ctx.line_to(px0, py0 + ph)
    ctx.line_to(px0 + pw, py0 + ph)
    ctx.stroke()
    draw_text(ctx, "Vericiye Uzaklık r (nm)", px0 + pw / 2.0, py0 + ph + 36, size=12.5, bold=True, align="center")
    draw_rot_text(ctx, "Medyan |A_dir(r)| (Hz)", cx + 22, py0 + ph / 2.0, size=12.5, bold=True)

    rb = data["radial_breakdown"]
    pts_kl, pts_vk = [], []
    for entry in rb:
        rmid = 0.5 * (entry["r_bin_nm"][0] + entry["r_bin_nm"][1])
        x_m = map_x(rmid, xmin, xmax, px0, pw)
        y_kl = map_y(math.log10(max(entry["kl_median_absA_Hz"], 10.0)), lmin, lmax, py0, ph)
        y_vk = map_y(math.log10(max(entry["vokl6_median_absA_Hz"], 10.0)), lmin, lmax, py0, ph)
        pts_kl.append((x_m, y_kl, entry["kl_median_absA_Hz"], rmid))
        pts_vk.append((x_m, y_vk, entry["vokl6_median_absA_Hz"], rmid))
        draw_text(ctx, f"{entry['r_bin_nm'][0]:.0f}–{entry['r_bin_nm'][1]:.0f}", x_m, py0 + ph + 18, size=11.0, color=MUTED, align="center")

    for pts, col, dy_t in ((pts_kl, C_KL, -11), (pts_vk, C_VOKL, 18)):
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.8)
        for i, (xx, yy, _, _) in enumerate(pts):
            if i == 0:
                ctx.move_to(xx, yy)
            else:
                ctx.line_to(xx, yy)
        ctx.stroke()
        for xx, yy, val, _ in pts:
            ctx.set_source_rgb(*col)
            ctx.arc(xx, yy, 5.0, 0, 2 * math.pi)
            ctx.fill()
            sval = f"{val/1e3:.1f}k" if val >= 1e3 else f"{val:.0f}"
            draw_text(ctx, sval, xx, yy + dy_t, size=9.8, color=col, bold=True, align="center")

    # Legend inside Panel C (top-right)
    lx, ly = px0 + pw - 235, py0 + 12
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.94)
    ctx.rectangle(lx, ly, 226, 52)
    ctx.fill()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.0)
    ctx.rectangle(lx, ly, 226, 52)
    ctx.stroke()
    for idx, (col, lbl) in enumerate([(C_KL, "Eski KL (a=2,50/1,40 nm)"), (C_VOKL, "VOKL-6 (a=1,75/0,96 nm)")]):
        yy = ly + 20 + idx * 21
        ctx.set_source_rgb(*col)
        ctx.set_line_width(2.8)
        ctx.move_to(lx + 10, yy - 4)
        ctx.line_to(lx + 34, yy - 4)
        ctx.stroke()
        draw_text(ctx, lbl, lx + 42, yy, size=11.0, color=TEXT, bold=True)

    # ---------------- Panel D (Bottom-Right): DDRF Gap-Safe Effective Yield Across f ----------------
    dx, dy, dw, dh = 804, 502, 772, 434
    draw_panel_box(ctx, dx, dy, dw, dh, "D. DDRF-Güvenli Etkin Verim (min_gap ≥ 6,89 kHz) & R1 Risk Kapanış Özeti")
    px0, py0, pw, ph = dx + 78, dy + 54, dw - 106, dh - 116
    ymin, ymax = 0.0, 80.0

    for yv in (0, 20, 40, 60, 80):
        yy = map_y(yv, ymin, ymax, py0, ph)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(1.0)
        ctx.move_to(px0, yy)
        ctx.line_to(px0 + pw, yy)
        ctx.stroke()
        draw_text(ctx, f"%{yv}", px0 - 10, yy + 4.5, size=11.5, color=MUTED, align="right")

    ctx.set_source_rgb(*TEXT)
    ctx.set_line_width(1.2)
    ctx.move_to(px0, py0)
    ctx.line_to(px0, py0 + ph)
    ctx.line_to(px0 + pw, py0 + ph)
    ctx.stroke()
    draw_rot_text(ctx, "Verim (%): Toplam vs ≥6,89 kHz", dx + 24, py0 + ph / 2.0, size=12.5, bold=True)

    grp_w = pw / 3.0
    bw_d = 34.0
    d_bars = [
        ("KL_legacy", "yield_frac", C_KL, 0.35),
        ("KL_legacy", "gap_safe", C_KL, 1.0),
        ("VOKL6_HM5962_ext", "yield_frac", C_ABINIT, 0.35),
        ("VOKL6_HM5962_ext", "gap_safe", C_ABINIT, 1.0),
        ("VOKL6_norm_ext", "yield_frac", C_VOKL, 0.35),
        ("VOKL6_norm_ext", "gap_safe", C_VOKL, 1.0),
    ]
    bw_d = 24.0
    for gi, (fk, flbl) in enumerate(f_keys):
        gx_c = px0 + (gi + 0.5) * grp_w
        tot_w = len(d_bars) * (bw_d + 3.0) - 3.0
        x0 = gx_c - tot_w / 2.0
        for bi, (mk, kind, col, alpha_c) in enumerate(d_bars):
            cell = mb[mk][fk]
            val = cell["yield_frac"] * 100.0 if kind == "yield_frac" else cell["gap_stats"]["yield_and_gap_ge_6893Hz"] * 100.0
            bx = x0 + bi * (bw_d + 3.0)
            y_top = map_y(val, ymin, ymax, py0, ph)
            ctx.set_source_rgba(col[0], col[1], col[2], alpha_c)
            ctx.rectangle(bx, y_top, bw_d, py0 + ph - y_top)
            ctx.fill()
            draw_text(ctx, f"{val:.1f}", bx + bw_d / 2.0, y_top - 5, size=8.8, color=col, bold=(alpha_c == 1.0), align="center")

        l1, _ = flbl.split("\n")
        draw_text(ctx, l1, gx_c, py0 + ph + 20, size=12.0, bold=True, align="center")
        risk_kl = mb["KL_legacy"][fk]["gap_stats"]["frac_lt_6893Hz"] * 100.0
        risk_hm = mb["VOKL6_HM5962_ext"][fk]["gap_stats"]["frac_lt_6893Hz"] * 100.0
        risk_vk = mb["VOKL6_norm_ext"][fk]["gap_stats"]["frac_lt_6893Hz"] * 100.0
        draw_text(ctx, f"<6,89k: KL %{risk_kl:.0f} | HM %{risk_hm:.0f} | N %{risk_vk:.0f}", gx_c, py0 + ph + 37, size=9.2, color=MUTED, align="center")

    # Legend under Panel D
    lx, ly = px0 - 14, py0 + ph + 56
    d_leg = [
        (C_KL, 0.35, "KL Toplam"),
        (C_KL, 1.0,  "KL ≥6,89kHz"),
        (C_ABINIT, 0.35, "VOKL-HM Toplam"),
        (C_ABINIT, 1.0,  "VOKL-HM ≥6,89kHz"),
        (C_VOKL, 0.35, "VOKL-Norm Toplam"),
        (C_VOKL, 1.0,  "VOKL-Norm ≥6,89kHz"),
    ]
    for idx, (col, alp, lbl) in enumerate(d_leg):
        xx = lx + (idx % 3) * 222
        yy = ly + (idx // 3) * 18
        ctx.set_source_rgba(col[0], col[1], col[2], alp)
        ctx.rectangle(xx, yy - 9, 13, 10)
        ctx.fill()
        draw_text(ctx, lbl, xx + 18, yy, size=10.0, color=TEXT, bold=(alp == 1.0))

    surf.write_to_png(str(out_path))


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    f1 = OUT_DIR / "fig_exp129_endor_shells.png"
    f2 = OUT_DIR / "fig_exp129_vokl6_yield.png"
    plot_endor_shells(data, f1)
    plot_vokl6_yield(data, f2)
    print(f"Generated {f1.name} ({f1.stat().st_size} bytes) and {f2.name} ({f2.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
