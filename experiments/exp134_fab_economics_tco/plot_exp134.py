#!/usr/bin/env python3
"""Generate publication-grade PyCairo/PIL figures for Exp134 (Fab Economics & 5-Yr TCO).

100% portable: uses Path(__file__).resolve().parents[2].
Run with /usr/bin/python3 -B (system Python with cairo + PIL).
Outputs:
  - results/exp134_fab_economics_tco/fig_exp134_tco_cost_per_qubit.png (2200x1260)
  - results/exp134_fab_economics_tco/fig_exp134_v3_vs_v4_scaling.png (2200x1260)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp134_fab_economics_tco"
EXP_JSON = OUT_DIR / "exp134.json"
FONT = "DejaVu Sans"


def set_rgb(ctx: cairo.Context, hex_col: str, alpha: float = 1.0) -> None:
    h = hex_col.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0
    ctx.set_source_rgba(r, g, b, alpha)


def draw_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 15.0,
    color: str = "#0F172A",
    bold: bool = False,
    align: str = "left",
    valign: str = "baseline",
    angle: float = 0.0,
) -> None:
    ctx.save()
    ctx.select_font_face(
        FONT,
        cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
    )
    ctx.set_font_size(size)
    ext = ctx.text_extents(text)
    ctx.translate(x, y)
    if angle != 0.0:
        ctx.rotate(angle)
    dx = 0.0
    if align == "center":
        dx = -(ext.x_bearing + ext.width / 2.0)
    elif align == "right":
        dx = -(ext.x_bearing + ext.width)
    dy = 0.0
    if valign == "middle":
        dy = -(ext.y_bearing + ext.height / 2.0)
    elif valign == "top":
        dy = -ext.y_bearing
    set_rgb(ctx, color)
    ctx.move_to(dx, dy)
    ctx.show_text(text)
    ctx.restore()


def round_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 10.0) -> None:
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def make_fig1_tco_cost_per_qubit(data: dict) -> Path:
    W, H = 2200, 1260
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    set_rgb(ctx, "#F8FAFC")
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Header
    set_rgb(ctx, "#0F172A")
    ctx.rectangle(0, 0, W, 94)
    ctx.fill()
    draw_text(
        ctx,
        "Exp134 (H152) — 5-Yıllık Fab TCO (CAPEX + OPEX) & Sertifikalı / Mantıksal Kübit Birim Ekonomisi",
        40,
        42,
        size=27,
        color="#FFFFFF",
        bold=True,
    )
    draw_text(
        ctx,
        "50.000 Örneklemli Korelasyonlu MC | v3.0 (1,97e8 reg/gün) vs v4.0 Bayesyen 5×/10× | 200 mm ²⁸Si/²⁹Si Yonga Zemin Analizi | Teklif Yok {Model/Varsayım}",
        40,
        74,
        size=15.5,
        color="#CBD5E1",
    )

    # =========================================================================
    # PANEL A (LEFT): 5-YEAR TCO STACKED BREAKDOWN (M1, M3 Fab-Tool, M3 FOAK)
    # =========================================================================
    pa_x, pa_y, pa_w, pa_h = 34, 118, 1052, 1068
    round_rect(ctx, pa_x, pa_y, pa_w, pa_h, 12)
    set_rgb(ctx, "#FFFFFF")
    ctx.fill_preserve()
    set_rgb(ctx, "#CBD5E1")
    ctx.set_line_width(1.6)
    ctx.stroke()

    draw_text(
        ctx,
        "A. 5-Yıllık Makine TCO Kırılımı (Sabit CAPEX + OPEX, Yongalar Hariç)",
        pa_x + 24,
        pa_y + 38,
        size=19.5,
        color="#0F172A",
        bold=True,
    )
    draw_text(
        ctx,
        "Medyan (P50) Milyon USD | M1 Lab vs M3 Ticari Fab Aracı (N=1) vs M3 İlk-Tür (FOAK Program ×3–10)",
        pa_x + 24,
        pa_y + 66,
        size=14,
        color="#475569",
    )

    ax0, ax1 = pa_x + 92, pa_x + pa_w - 36
    ay0, ay1 = pa_y + 114, pa_y + 735
    ymax = 48.0

    def map_ay(v: float) -> float:
        return ay1 - (v / ymax) * (ay1 - ay0)

    for tk in [0, 10, 20, 30, 40]:
        gy = map_ay(tk)
        set_rgb(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(ax0, gy)
        ctx.line_to(ax1, gy)
        ctx.stroke()
        draw_text(ctx, f"${tk}M", ax0 - 12, gy, size=14, color="#334155", align="right", valign="middle")

    draw_text(
        ctx,
        "5-Yıllık Toplam Sahip Olma Maliyeti — TCO (Milyon USD)",
        pa_x + 28,
        (ay0 + ay1) / 2.0,
        size=15,
        color="#0F172A",
        bold=True,
        align="center",
        valign="middle",
        angle=-math.pi / 2.0,
    )

    tco = data["tco_5yr_summary_no_wafers"]
    opex = data["opex_annual_breakdown_usd"]
    bc = data["budget_cap_v3_vs_v4"]

    cln_m = opex["cleanroom_setup_capex"]["p50"] / 1e6
    op5_v3 = 5.0 * opex["total_fixed_opex_yr_v3"]["p50"] / 1e6
    op5_v4 = 5.0 * opex["total_fixed_opex_yr_v4"]["p50"] / 1e6

    # Build 5 stacked bars (CAPEX remainder = total P50 - cleanroom - 5yr OPEX for clean P50 reconciliation)
    m1_tot = tco["m1_lab_5yr_tco_usd"]["p50"] / 1e6
    v3_fab_tot = tco["v3_fab_tool_n1_5yr_tco_usd"]["p50"] / 1e6
    v4_fab_tot = tco["v4_fab_tool_n1_5yr_tco_usd"]["p50"] / 1e6
    v3_foak_tot = tco["v3_foak_program_5yr_tco_usd"]["p50"] / 1e6
    v4_foak_tot = tco["v4_foak_program_5yr_tco_usd"]["p50"] / 1e6

    bars = [
        ("M1 Lab\nPrototip", m1_tot - 0.5 * cln_m - 0.65 * op5_v3, 0.5 * cln_m, 0.65 * op5_v3, m1_tot,
         tco["m1_lab_5yr_tco_usd"]["p10"] / 1e6, tco["m1_lab_5yr_tco_usd"]["p90"] / 1e6),
        ("M3 v3.0\nFab (N=1)", v3_fab_tot - cln_m - op5_v3, cln_m, op5_v3, v3_fab_tot,
         tco["v3_fab_tool_n1_5yr_tco_usd"]["p10"] / 1e6, tco["v3_fab_tool_n1_5yr_tco_usd"]["p90"] / 1e6),
        ("M3 v4.0\nFab (N=1)", v4_fab_tot - cln_m - op5_v4, cln_m, op5_v4, v4_fab_tot,
         tco["v4_fab_tool_n1_5yr_tco_usd"]["p10"] / 1e6, tco["v4_fab_tool_n1_5yr_tco_usd"]["p90"] / 1e6),
        ("M3 v3.0\nFOAK Prog", v3_foak_tot - cln_m - op5_v3, cln_m, op5_v3, v3_foak_tot,
         tco["v3_foak_program_5yr_tco_usd"]["p10"] / 1e6, tco["v3_foak_program_5yr_tco_usd"]["p90"] / 1e6),
        ("M3 v4.0\nFOAK Prog", v4_foak_tot - cln_m - op5_v4, cln_m, op5_v4, v4_foak_tot,
         tco["v4_foak_program_5yr_tco_usd"]["p10"] / 1e6, tco["v4_foak_program_5yr_tco_usd"]["p90"] / 1e6),
    ]

    seg_cols = [
        ("#1D4ED8", "Makine / Program CAPEX"),
        ("#0D9488", "Temizoda ISO-5/6 Kurulumu (5y)"),
        ("#EA580C", "5-Yıllık Sabit OPEX (FTE+Bakım+HVAC+PH₃+Güç)"),
    ]
    n_b = len(bars)
    slot_w = (ax1 - ax0) / n_b
    bw = 104
    for i, (lbl, c_cap, c_cln, c_op, tot, p10, p90) in enumerate(bars):
        cx = ax0 + (i + 0.5) * slot_w
        cum = 0.0
        for val, (col, _) in zip((c_cap, c_cln, c_op), seg_cols):
            yb, yt = map_ay(cum), map_ay(cum + val)
            set_rgb(ctx, col, 0.90)
            ctx.rectangle(cx - bw / 2.0, yt, bw, yb - yt)
            ctx.fill()
            set_rgb(ctx, "#FFFFFF", 0.65)
            ctx.set_line_width(1.0)
            ctx.rectangle(cx - bw / 2.0, yt, bw, yb - yt)
            ctx.stroke()
            if val >= 3.2:
                draw_text(ctx, f"${val:.1f}M", cx, (yt + yb) / 2.0, size=12.5, color="#FFFFFF", bold=True, align="center", valign="middle")
            cum += val
        draw_text(ctx, f"${tot:.2f}M", cx, map_ay(tot) - 10, size=15.5, color="#0F172A", bold=True, align="center")
        draw_text(ctx, f"[${p10:.1f}–${p90:.1f}M]", cx, map_ay(tot) - 30, size=11.8, color="#475569", align="center")
        for li, line in enumerate(lbl.split("\n")):
            draw_text(ctx, line, cx, ay1 + 22 + li * 19, size=13.5, color="#0F172A", bold=(li == 0), align="center")

    set_rgb(ctx, "#334155")
    ctx.set_line_width(1.6)
    ctx.move_to(ax0, ay0)
    ctx.line_to(ax0, ay1)
    ctx.line_to(ax1, ay1)
    ctx.stroke()

    # Legend inside Panel A top-left (empty space above M1/M3 Fab bars)
    lg_x, lg_y, lg_w, lg_h = ax0 + 14, ay0 + 12, 465, 114
    round_rect(ctx, lg_x, lg_y, lg_w, lg_h, 8)
    set_rgb(ctx, "#FFFFFF", 0.95)
    ctx.fill_preserve()
    set_rgb(ctx, "#94A3B8")
    ctx.set_line_width(1.2)
    ctx.stroke()
    for idx, (col, desc) in enumerate(seg_cols):
        yy = lg_y + 24 + idx * 31
        set_rgb(ctx, col)
        ctx.rectangle(lg_x + 14, yy - 9, 20, 16)
        ctx.fill()
        draw_text(ctx, desc, lg_x + 44, yy, size=13.2, color="#0F172A", valign="middle")

    # Annual OPEX & v4.0 Delta breakdown card at bottom of Panel A
    round_rect(ctx, pa_x + 24, ay1 + 66, pa_w - 48, 224, 8)
    set_rgb(ctx, "#F8FAFC")
    ctx.fill_preserve()
    set_rgb(ctx, "#94A3B8")
    ctx.set_line_width(1.2)
    ctx.stroke()

    draw_text(ctx, "Yıllık Sabit OPEX Kırılımı (v4.0 P50 = $1.162k/yıl)", pa_x + 42, ay1 + 94, size=14.5, color="#0F172A", bold=True)
    op_lines = [
        f"• Operatör & Kriyo/Süreç Mühendisi (3,0 FTE):  ${opex['fte_operators_engineers']['p50']/1e3:,.1f}k/yıl (%41)",
        f"• Bakım & Yedek Parça (%8 HW, S9 çapalı):      ${opex['maintenance_spares_8pct_v4']['p50']/1e3:,.1f}k/yıl (%38)",
        f"• Temizoda ISO-5/6 HVAC & Altyapı:              ${opex['cleanroom_hvac']['p50']/1e3:,.1f}k/yıl (%10)",
        f"• PH₃ Toksik Gaz & Yıkayıcı EHS Bakımı:         ${opex['ph3_gas_ehs']['p50']/1e3:,.1f}k/yıl (%4)",
        f"• Elektrik Gücü (15–25 kW, PT420+DR+RF):       ${opex['power_15_25kw']['p50']/1e3:,.1f}k/yıl (%2)",
    ]
    for i, ln in enumerate(op_lines):
        draw_text(ctx, ln, pa_x + 42, ay1 + 124 + i * 28, size=12.8, color="#334155")

    # Right sub-column inside bottom card: v4.0 Hardware Delta + Leverage
    v4d = data["v4_hardware_deltas"]
    lev = data["v3_to_v4_value_leverage"]
    vx = pa_x + 562
    set_rgb(ctx, "#CBD5E1")
    ctx.set_line_width(1.2)
    ctx.move_to(vx - 18, ay1 + 80)
    ctx.line_to(vx - 18, ay1 + 276)
    ctx.stroke()
    draw_text(ctx, f"v4.0 Donanım Deltası (+${v4d['total_nom_usd']/1e3:.0f}k, +%10,0)", vx, ay1 + 94, size=14.5, color="#1E3A8A", bold=True)
    v4_lines = [
        f"• M4 Kavite Veri Yolu & Kapı Elektroniği:  $245k [$135–460k]",
        f"• S5.5 Flaş-Tavlama Optik Yükseltmesi:     $95k  [$55–175k]",
        f"• PT420 Dekuplaj & 1,4 Hz Feedforward:     $68k  [$38–125k]",
        f"• S8 Bayesyen Gerçek-Zamanlı GPU Düğümü:   $12k  [$7–22k]",
        f"→ 5× Kapasitede Kaldıraç: {lev['hw_capex_leverage_ratio_5x']:.1f}× HW | {lev['tco5_leverage_ratio_5x']:.1f}× TCO!",
    ]
    for i, ln in enumerate(v4_lines):
        draw_text(ctx, ln, vx, ay1 + 124 + i * 28, size=12.8, color="#065F46" if i == 4 else "#334155", bold=(i == 4))

    # =========================================================================
    # PANEL B (RIGHT): UNIT ECONOMICS LADDER (LOG SCALE, REGIME I vs REGIME II)
    # =========================================================================
    pb_x, pb_y, pb_w, pb_h = 1114, 118, 1052, 1068
    round_rect(ctx, pb_x, pb_y, pb_w, pb_h, 12)
    set_rgb(ctx, "#FFFFFF")
    ctx.fill_preserve()
    set_rgb(ctx, "#CBD5E1")
    ctx.set_line_width(1.6)
    ctx.stroke()

    draw_text(
        ctx,
        "B. Birim Ekonomi Karşılaştırması: Kapasite Limiti vs 200 mm Yonga Fabı",
        pb_x + 24,
        pb_y + 38,
        size=19.5,
        color="#0F172A",
        bold=True,
    )
    draw_text(
        ctx,
        "Medyan (P50) Birim Maliyet (USD, Log Ölçek) | v3.0 vs v4.0-5× vs v4.0-10× (@10 ms) — N=1 Fab Aracı",
        pb_x + 24,
        pb_y + 66,
        size=14,
        color="#475569",
    )

    bx0, bx1 = pb_x + 310, pb_x + pb_w - 42
    by0, by1 = pb_y + 114, pb_y + 735
    lmin, lmax = math.log10(1e-4), math.log10(300.0)

    def map_bx(val: float) -> float:
        lv = math.log10(max(1e-4, min(300.0, val)))
        return bx0 + (lv - lmin) / (lmax - lmin) * (bx1 - bx0)

    for tk, tlbl in [(1e-4, "$0.0001"), (1e-3, "$0.001"), (1e-2, "$0.01"), (0.1, "$0.10"), (1.0, "$1"), (10.0, "$10"), (100.0, "$100")]:
        gx = map_bx(tk)
        set_rgb(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(gx, by0)
        ctx.line_to(gx, by1)
        ctx.stroke()
        draw_text(ctx, tlbl, gx, by1 + 24, size=13.5, color="#334155", align="center")

    draw_text(
        ctx,
        "Birim Maliyet (USD, Logaritmik Ölçek)",
        (bx0 + bx1) / 2.0,
        by1 + 52,
        size=15,
        color="#0F172A",
        bold=True,
        align="center",
    )

    r1 = data["regime1_steady_state_capacity"]
    r2 = data["regime2_wafer_batch_amdahl"]
    metrics = [
        (
            "Rejim II-Std: 10k-Hücre Yonga\n(2e6 reg/w, 8 saat, $12k yonga)",
            r2["standard_2e6_8h"]["v3_0"]["wafer_price_sweep"]["usd_12000"]["usd_per_chip_10k_p50"],
            r2["standard_2e6_8h"]["v4_0_5x"]["wafer_price_sweep"]["usd_12000"]["usd_per_chip_10k_p50"],
            r2["standard_2e6_8h"]["v4_0_10x_10ms"]["wafer_price_sweep"]["usd_12000"]["usd_per_chip_10k_p50"],
            60.0,
        ),
        (
            "Rejim II-Std: d=17 Mantıksal Kübit\n(577/0.51=1131 hücre, 8 saat)",
            r2["standard_2e6_8h"]["v3_0"]["fab_tool_n1_stoch_wafer"]["logical_qubit_m4"]["d17"]["usd_modb_p50"],
            r2["standard_2e6_8h"]["v4_0_5x"]["fab_tool_n1_stoch_wafer"]["logical_qubit_m4"]["d17"]["usd_modb_p50"],
            r2["standard_2e6_8h"]["v4_0_10x_10ms"]["fab_tool_n1_stoch_wafer"]["logical_qubit_m4"]["d17"]["usd_modb_p50"],
            None,
        ),
        (
            "Rejim II-Yoğun: 10k-Hücre Yonga\n(5e7 reg/w, 1 saat mekik, $12k)",
            r2["dense_5e7_1h"]["v3_0"]["wafer_price_sweep"]["usd_12000"]["usd_per_chip_10k_p50"],
            r2["dense_5e7_1h"]["v4_0_5x"]["wafer_price_sweep"]["usd_12000"]["usd_per_chip_10k_p50"],
            r2["dense_5e7_1h"]["v4_0_10x_10ms"]["wafer_price_sweep"]["usd_12000"]["usd_per_chip_10k_p50"],
            2.40,
        ),
        (
            "Rejim II-Yoğun: d=17 Mantıksal Kübit\n(5e7 reg/w, 1 saat mekik, Mod B)",
            r2["dense_5e7_1h"]["v3_0"]["fab_tool_n1_stoch_wafer"]["logical_qubit_m4"]["d17"]["usd_modb_p50"],
            r2["dense_5e7_1h"]["v4_0_5x"]["fab_tool_n1_stoch_wafer"]["logical_qubit_m4"]["d17"]["usd_modb_p50"],
            r2["dense_5e7_1h"]["v4_0_10x_10ms"]["fab_tool_n1_stoch_wafer"]["logical_qubit_m4"]["d17"]["usd_modb_p50"],
            None,
        ),
        (
            "Rejim I (Kapasite): 10k-Hücre Yonga\n(Yonga hariç saf makine işleme)",
            r1["v3_0_baseline"]["fab_tool_n1_5yr"]["usd_per_chip_10k"]["p50"],
            r1["v4_0_bayes5x_15ms"]["fab_tool_n1_5yr"]["usd_per_chip_10k"]["p50"],
            r1["v4_0_bayes10x_10ms"]["fab_tool_n1_5yr"]["usd_per_chip_10k"]["p50"],
            None,
        ),
        (
            "Rejim I (Kapasite): d=17 Mantıksal\n(577/0.51 hücre, yonga hariç)",
            r1["v3_0_baseline"]["fab_tool_n1_5yr"]["logical_qubit_m4"]["d17"]["usd_modb_p50"],
            r1["v4_0_bayes5x_15ms"]["fab_tool_n1_5yr"]["logical_qubit_m4"]["d17"]["usd_modb_p50"],
            r1["v4_0_bayes10x_10ms"]["fab_tool_n1_5yr"]["logical_qubit_m4"]["d17"]["usd_modb_p50"],
            None,
        ),
        (
            "Rejim I (Kapasite): d=7 Mantıksal\n(97/0.51=190 hücre, yonga hariç)",
            r1["v3_0_baseline"]["fab_tool_n1_5yr"]["logical_qubit_m4"]["d7"]["usd_modb_p50"],
            r1["v4_0_bayes5x_15ms"]["fab_tool_n1_5yr"]["logical_qubit_m4"]["d7"]["usd_modb_p50"],
            r1["v4_0_bayes10x_10ms"]["fab_tool_n1_5yr"]["logical_qubit_m4"]["d7"]["usd_modb_p50"],
            None,
        ),
    ]

    row_h = (by1 - by0) / len(metrics)
    for i, (mlbl, v3v, v45v, v410v, floor_v) in enumerate(metrics):
        cy = by0 + (i + 0.5) * row_h
        if i % 2 == 0:
            set_rgb(ctx, "#F8FAFC")
            ctx.rectangle(pb_x + 14, cy - row_h / 2.0, pb_w - 28, row_h)
            ctx.fill()

        # Left two-line label
        lines = mlbl.split("\n")
        draw_text(ctx, lines[0], bx0 - 14, cy - 8, size=13.2, color="#0F172A", bold=True, align="right", valign="middle")
        draw_text(ctx, lines[1], bx0 - 14, cy + 12, size=11.5, color="#64748B", align="right", valign="middle")

        # 3 grouped horizontal thin bars
        bh = 14
        for off, val, col in [(-18, v3v, "#64748B"), (0, v45v, "#1D4ED8"), (18, v410v, "#059669")]:
            xw = max(4.0, map_bx(val) - bx0)
            set_rgb(ctx, col, 0.90)
            ctx.rectangle(bx0, cy + off - bh / 2.0, xw, bh)
            ctx.fill()
            val_txt = f"${val:.2f}" if val >= 0.1 else f"${val:.4f}"
            draw_text(ctx, val_txt, bx0 + xw + 8, cy + off, size=11.5, color=col, bold=(off != -18), valign="middle")

        # Optional epitaxial silicon wafer floor tick
        if floor_v is not None:
            fx = map_bx(floor_v)
            ctx.save()
            set_rgb(ctx, "#DC2626")
            ctx.set_line_width(2.2)
            ctx.set_dash([4, 3])
            ctx.move_to(fx, cy - row_h * 0.42)
            ctx.line_to(fx, cy + row_h * 0.42)
            ctx.stroke()
            ctx.restore()

    # Legend for Panel B at bottom of Panel B
    round_rect(ctx, pb_x + 24, ay1 + 66, pb_w - 48, 224, 8)
    set_rgb(ctx, "#EFF6FF")
    ctx.fill_preserve()
    set_rgb(ctx, "#2563EB")
    ctx.set_line_width(1.3)
    ctx.stroke()

    leg_items = [
        ("#64748B", "v3.0 Baz (1,97e8 reg/gün)"),
        ("#1D4ED8", "v4.0 Bayesyen 5× (9,86e8 reg/gün)"),
        ("#059669", "v4.0 Bayesyen 10× @10 ms (1,97e9 reg/gün)"),
        ("#DC2626", "²⁸Si/²⁹Si Yonga Maliyet Zemini ($60 / $2.40)"),
    ]
    for idx, (col, txt) in enumerate(leg_items):
        lx = pb_x + 42 + (idx % 2) * 485
        ly = ay1 + 94 + (idx // 2) * 28
        if idx == 3:
            ctx.save()
            set_rgb(ctx, col)
            ctx.set_line_width(2.6)
            ctx.set_dash([4, 3])
            ctx.move_to(lx + 10, ly - 10)
            ctx.line_to(lx + 10, ly + 8)
            ctx.stroke()
            ctx.restore()
        else:
            set_rgb(ctx, col)
            ctx.rectangle(lx, ly - 8, 20, 14)
            ctx.fill()
        draw_text(ctx, txt, lx + 28, ly, size=13, color="#0F172A", bold=(idx >= 1), valign="middle")

    takeaways = [
        "1. Saf Makine Kapasitesi (Rejim I): v4.0 5× maliyeti −%78,9 ($52,9 → $11,2 µUSD/yazmaç), 10×@10ms −%89,5 ($5,6 µUSD) indirir.",
        "2. 15 ms Yazma Duvarı Keşfi: 1.024 demetcik @15 ms'de 10× Bayesyen 7,62×'te yazma tavanına çarpar (10 ms atış gerekir).",
        "3. Amdahl & Yonga Zemini (Rejim II, CX4): Standart (2e6/w, 8s) rejimde 8 saatlik kriyo-değişim + $60/çip silisyum zemini hızı yutar.",
        "4. Yoğun M4 Yonga (5e7/w, 1s mekik): Makine bedeli $0,616 → $0,203/çip (−%67,0) iner; toplam $2,60/çip'in %92'si ham ²⁸Si epi yongadır!",
    ]
    for ti, tt in enumerate(takeaways):
        draw_text(ctx, tt, pb_x + 42, ay1 + 162 + ti * 29, size=12.6, color="#1E293B")

    draw_text(
        ctx,
        "Kaynak: results/exp134_fab_economics_tco/exp134.json (seed=2026134, N=50.000) | Kanonik BOM.csv değişmedi | Teklif/lab ölçümü yoktur.",
        40,
        H - 22,
        size=14,
        color="#64748B",
    )

    out_path = OUT_DIR / "fig_exp134_tco_cost_per_qubit.png"
    surf.write_to_png(str(out_path))
    assert Image.open(out_path).size == (W, H)
    return out_path


def make_fig2_v3_vs_v4_scaling(data: dict) -> Path:
    W, H = 2200, 1260
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    set_rgb(ctx, "#F8FAFC")
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    set_rgb(ctx, "#0F172A")
    ctx.rectangle(0, 0, W, 94)
    ctx.fill()
    draw_text(
        ctx,
        "Exp134 (H152) — Wright Öğrenme Eğrisi (N=1 → 100 Makine) & v4.0 Bütçe Tavanı ($50M / $100M) Marjı",
        40,
        42,
        size=27,
        color="#FFFFFF",
        bold=True,
    )
    draw_text(
        ctx,
        "b = %82–%88 Öğrenme Bandı | d=7/11/17 Mantıksal Kübit Ölçeklenmesi | v3.0 → v4.0 (+$420k HW) Aşım Olasılığı Karşılaştırması",
        40,
        74,
        size=15.5,
        color="#CBD5E1",
    )

    # =========================================================================
    # PANEL A (LEFT): WRIGHT LEARNING CURVE (N = 1 .. 100)
    # =========================================================================
    pa_x, pa_y, pa_w, pa_h = 34, 118, 1052, 1068
    round_rect(ctx, pa_x, pa_y, pa_w, pa_h, 12)
    set_rgb(ctx, "#FFFFFF")
    ctx.fill_preserve()
    set_rgb(ctx, "#CBD5E1")
    ctx.set_line_width(1.6)
    ctx.stroke()

    draw_text(
        ctx,
        "A. Wright Öğrenme Eğrisi: Filo Ölçeğinde Makine CAPEX & 5-Yıllık Fab TCO",
        pa_x + 24,
        pa_y + 38,
        size=19.5,
        color="#0F172A",
        bold=True,
    )
    draw_text(
        ctx,
        "C(N) = C(1) · N^(log₂ b), b ∈ [%82, %85, %88] | N = 1 → 10 → 100 v4.0 Makine (Log-Log Eksen)",
        pa_x + 24,
        pa_y + 66,
        size=14,
        color="#475569",
    )

    ax0, ax1 = pa_x + 92, pa_x + pa_w - 38
    ay0, ay1 = pa_y + 114, pa_y + 735
    lx_min, lx_max = math.log10(1.0), math.log10(100.0)
    ly_min, ly_max = math.log10(0.8), math.log10(25.0)

    def map_wx(n_val: float) -> float:
        return ax0 + (math.log10(n_val) - lx_min) / (lx_max - lx_min) * (ax1 - ax0)

    def map_wy(usd_m: float) -> float:
        return ay1 - (math.log10(max(0.8, min(25.0, usd_m))) - ly_min) / (ly_max - ly_min) * (ay1 - ay0)

    for nt in [1, 2, 5, 10, 25, 50, 100]:
        gx = map_wx(nt)
        set_rgb(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(gx, ay0)
        ctx.line_to(gx, ay1)
        ctx.stroke()
        draw_text(ctx, f"N={nt}", gx, ay1 + 24, size=14, color="#334155", bold=(nt in (1, 10, 100)), align="center")

    for yt in [1, 2, 5, 10, 20]:
        gy = map_wy(yt)
        set_rgb(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(ax0, gy)
        ctx.line_to(ax1, gy)
        ctx.stroke()
        draw_text(ctx, f"${yt}M", ax0 - 12, gy, size=14, color="#334155", align="right", valign="middle")

    draw_text(ctx, "Kümülatif Üretilen Makine Sayısı (N, Log Ölçek)", (ax0 + ax1) / 2.0, ay1 + 54, size=15, color="#0F172A", bold=True, align="center")
    draw_text(ctx, "Makine Başına Maliyet (Milyon USD, Log)", pa_x + 28, (ay0 + ay1) / 2.0, size=15, color="#0F172A", bold=True, align="center", valign="middle", angle=-math.pi / 2.0)

    wc = data["wright_learning_curves"]
    ns = [1, 5, 10, 25, 50, 100]

    # Shaded band for HW CAPEX (b=82%..88%)
    ctx.new_path()
    for i, nt in enumerate(ns):
        px, py = map_wx(nt), map_wy(wc["b_88"][str(nt)]["hw_v4_nom_usd"] / 1e6)
        ctx.move_to(px, py) if i == 0 else ctx.line_to(px, py)
    for nt in reversed(ns):
        ctx.line_to(map_wx(nt), map_wy(wc["b_82"][str(nt)]["hw_v4_nom_usd"] / 1e6))
    ctx.close_path()
    set_rgb(ctx, "#DBEAFE", 0.75)
    ctx.fill()

    # Shaded band for 5-Yr Fab TCO (b=82%..88%)
    ctx.new_path()
    for i, nt in enumerate(ns):
        px, py = map_wx(nt), map_wy(wc["b_88"][str(nt)]["tco5_no_wafer_p50_usd"] / 1e6)
        ctx.move_to(px, py) if i == 0 else ctx.line_to(px, py)
    for nt in reversed(ns):
        ctx.line_to(map_wx(nt), map_wy(wc["b_82"][str(nt)]["tco5_no_wafer_p50_usd"] / 1e6))
    ctx.close_path()
    set_rgb(ctx, "#FEF3C7", 0.75)
    ctx.fill()

    # Plot curves: b=85% bold + b=82/88 dashed
    for key, col_hw, col_tco, lw, dash in [
        ("b_85", "#1D4ED8", "#D97706", 4.0, []),
        ("b_82", "#3B82F6", "#F59E0B", 1.8, [6, 4]),
        ("b_88", "#3B82F6", "#F59E0B", 1.8, [6, 4]),
    ]:
        for field, col in [("hw_v4_nom_usd", col_hw), ("tco5_no_wafer_p50_usd", col_tco)]:
            ctx.save()
            set_rgb(ctx, col)
            ctx.set_line_width(lw)
            if dash:
                ctx.set_dash(dash)
            for i, nt in enumerate(ns):
                px, py = map_wx(nt), map_wy(wc[key][str(nt)][field] / 1e6)
                ctx.move_to(px, py) if i == 0 else ctx.line_to(px, py)
            ctx.stroke()
            ctx.restore()

    # Annotate key points on b=85%
    for nt in [1, 10, 100]:
        hw_v = wc["b_85"][str(nt)]["hw_v4_nom_usd"] / 1e6
        tc_v = wc["b_85"][str(nt)]["tco5_no_wafer_p50_usd"] / 1e6
        al = "left" if nt == 1 else ("right" if nt == 100 else "center")
        dx = 10 if nt == 1 else (-12 if nt == 100 else 0)
        dy_hw = -14 if nt == 1 else (-28 if nt == 10 else -26)
        dy_tc = -14 if nt == 1 else (-24 if nt == 10 else -30)
        for val, col, dy in [(hw_v, "#1E3A8A", dy_hw), (tc_v, "#92400E", dy_tc)]:
            px, py = map_wx(nt), map_wy(val)
            set_rgb(ctx, col)
            ctx.arc(px, py, 6.0, 0, 2 * math.pi)
            ctx.fill()
            draw_text(ctx, f"${val:.2f}M", px + dx, py + dy, size=13.5, color=col, bold=True, align=al)

    # Legend inside Panel A top-right open white space (cleanly right of N=6 green dashed line & above orange band)
    wlg_x, wlg_y, wlg_w, wlg_h = ax1 - 392, ay0 + 44, 376, 74
    round_rect(ctx, wlg_x, wlg_y, wlg_w, wlg_h, 7)
    set_rgb(ctx, "#FFFFFF", 0.95)
    ctx.fill_preserve()
    set_rgb(ctx, "#94A3B8")
    ctx.set_line_width(1.1)
    ctx.stroke()
    for l_i, (l_col, b_col, l_txt) in enumerate([
        ("#D97706", "#FEF3C7", "5-Yıllık Ticari Fab TCO (P50, b=%82–%88)"),
        ("#1D4ED8", "#DBEAFE", "v4.0 Donanım CAPEX (Nom, b=%82–%88)"),
    ]):
        ly = wlg_y + 22 + l_i * 28
        set_rgb(ctx, b_col)
        ctx.rectangle(wlg_x + 12, ly - 8, 30, 16)
        ctx.fill()
        set_rgb(ctx, l_col)
        ctx.set_line_width(3.4)
        ctx.move_to(wlg_x + 12, ly)
        ctx.line_to(wlg_x + 42, ly)
        ctx.stroke()
        draw_text(ctx, l_txt, wlg_x + 52, ly, size=12.4, color="#0F172A", bold=True, valign="middle")

    # Vertical dashed marker at N=6 (Exp128 1 K Hot-Readout EVPI Break-Even!)
    x_n6 = map_wx(6.03)
    ctx.save()
    set_rgb(ctx, "#059669")
    ctx.set_line_width(2.2)
    ctx.set_dash([7, 5])
    ctx.move_to(x_n6, ay0)
    ctx.line_to(x_n6, ay1)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, "N ≥ 6: 1 K Sıcak-Okuma EVPI Başa-Baş (Exp128)", x_n6 + 8, ay0 + 22, size=12.8, color="#065F46", bold=True)

    set_rgb(ctx, "#334155")
    ctx.set_line_width(1.6)
    ctx.rectangle(ax0, ay0, ax1 - ax0, ay1 - ay0)
    ctx.stroke()

    # Bottom Wright summary table inside Panel A (driven dynamically from exp134.json)
    round_rect(ctx, pa_x + 24, ay1 + 68, pa_w - 48, 222, 8)
    set_rgb(ctx, "#F8FAFC")
    ctx.fill_preserve()
    set_rgb(ctx, "#94A3B8")
    ctx.set_line_width(1.2)
    ctx.stroke()
    draw_text(ctx, "Wright Öğrenme Tablosu (b = %85, Yoğun M4 Fabı 5e7 reg/w, 1 saat mekik)", pa_x + 42, ay1 + 96, size=14.5, color="#0F172A", bold=True)
    w_rows = [("Filo (N)", "HW Çarpan", "v4.0 HW", "5y Fab TCO", "10k-Çip ($)", "d=7 Lojik", "d=11 Lojik", "d=17 Lojik")]
    for n_key in ("1", "10", "100"):
        wn = wc["b_85"][n_key]
        w_rows.append((
            f"N = {n_key}",
            f"{wn['wright_hw_multiplier']:.3f}×".replace(".", ","),
            f"${wn['hw_v4_nom_usd']/1e6:.2f}M".replace(".", ","),
            f"${wn['tco5_no_wafer_p50_usd']/1e6:.2f}M".replace(".", ","),
            f"${wn['dense_fab_usd_per_chip_10k_p50']:.2f}".replace(".", ","),
            f"${wn['dense_fab_d7_modb_logical_p50']:.3f}".replace(".", ","),
            f"${wn['dense_fab_d11_modb_logical_p50']:.3f}".replace(".", ","),
            f"${wn['dense_fab_d17_modb_logical_p50']:.3f}".replace(".", ","),
        ))
    cxs = [pa_x + 44, pa_x + 150, pa_x + 275, pa_x + 390, pa_x + 520, pa_x + 645, pa_x + 765, pa_x + 890]
    for ri, rvals in enumerate(w_rows):
        ry = ay1 + 132 + ri * 34
        if ri == 0:
            set_rgb(ctx, "#E2E8F0")
            ctx.rectangle(pa_x + 36, ry - 16, pa_w - 72, 26)
            ctx.fill()
        for ci, txt in enumerate(rvals):
            clr = "#065F46" if (ri == 3 and ci >= 1) else "#0F172A"
            draw_text(ctx, txt, cxs[ci], ry, size=13.2, color=clr, bold=(ri in (0, 3)))
    draw_text(
        ctx,
        "Not: b=%82–%88 aralığında N=100 HW çarpanı 0,268×–0,428× ($1,23M–$1,97M); saf kapasite rejiminde N=100 d=17 mantıksal kübit = $0,0057.",
        pa_x + 42,
        ay1 + 272,
        size=12.5,
        color="#475569",
    )

    # =========================================================================
    # PANEL B (RIGHT): v3.0 vs v4.0 BUDGET-CAP CDF ($50M / $100M)
    # =========================================================================
    pb_x, pb_y, pb_w, pb_h = 1114, 118, 1052, 1068
    round_rect(ctx, pb_x, pb_y, pb_w, pb_h, 12)
    set_rgb(ctx, "#FFFFFF")
    ctx.fill_preserve()
    set_rgb(ctx, "#CBD5E1")
    ctx.set_line_width(1.6)
    ctx.stroke()

    draw_text(
        ctx,
        "B. $50M / $100M Bütçe Tavanı Marj Analizi: v3.0 vs v4.0 (+$420k Donanım)",
        pb_x + 24,
        pb_y + 38,
        size=19.5,
        color="#0F172A",
        bold=True,
    )
    draw_text(
        ctx,
        "50.000 Örneklemli Korelasyonlu MC Ampirik CDF | Program Stokastik (×3–×10) & 5-Yıllık FOAK/Fab TCO",
        pb_x + 24,
        pb_y + 66,
        size=14,
        color="#475569",
    )

    bx0, bx1 = pb_x + 88, pb_x + pb_w - 38
    by0, by1 = pb_y + 114, pb_y + 735
    lmin, lmax = math.log10(5.0), math.log10(250.0)

    def map_cx(val_m: float) -> float:
        return bx0 + (math.log10(max(5.0, min(250.0, val_m))) - lmin) / (lmax - lmin) * (bx1 - bx0)

    def map_cy(p: float) -> float:
        return by1 - p * (by1 - by0)

    x50, x100 = map_cx(50.0), map_cx(100.0)
    set_rgb(ctx, "#ECFDF5", 0.65)
    ctx.rectangle(bx0, by0, x50 - bx0, by1 - by0)
    ctx.fill()
    set_rgb(ctx, "#FFFBEB", 0.85)
    ctx.rectangle(x50, by0, x100 - x50, by1 - by0)
    ctx.fill()
    set_rgb(ctx, "#FEF2F2", 0.85)
    ctx.rectangle(x100, by0, bx1 - x100, by1 - by0)
    ctx.fill()

    draw_text(ctx, "NORMAL BÖLGE (≤$50M)", (bx0 + x50) / 2.0, by0 + 22, size=13, color="#065F46", bold=True, align="center")
    draw_text(ctx, "GEREKÇELİ", (x50 + x100) / 2.0, by1 - 44, size=12.5, color="#92400E", bold=True, align="center")
    draw_text(ctx, "$50M–$100M", (x50 + x100) / 2.0, by1 - 24, size=12, color="#92400E", align="center")
    draw_text(ctx, "YASAK", (x100 + bx1) / 2.0, by1 - 44, size=12.5, color="#991B1B", bold=True, align="center")
    draw_text(ctx, ">$100M", (x100 + bx1) / 2.0, by1 - 24, size=12, color="#991B1B", align="center")

    for tk in [5, 10, 20, 50, 100, 200]:
        gx = map_cx(tk)
        set_rgb(ctx, "#CBD5E1", 0.7)
        ctx.set_line_width(1.0)
        ctx.move_to(gx, by0)
        ctx.line_to(gx, by1)
        ctx.stroke()
        draw_text(ctx, f"${tk}M", gx, by1 + 24, size=14, color="#334155", bold=(tk in (50, 100)), align="center")

    for yp in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        gy = map_cy(yp)
        set_rgb(ctx, "#CBD5E1", 0.7)
        ctx.set_line_width(1.0)
        ctx.move_to(bx0, gy)
        ctx.line_to(bx1, gy)
        ctx.stroke()
        draw_text(ctx, f"%{int(yp*100)}", bx0 - 12, gy, size=14, color="#334155", align="right", valign="middle")

    draw_text(ctx, "Toplam Program CAPEX / 5-Yıllık TCO (Milyon USD, Log)", (bx0 + bx1) / 2.0, by1 + 54, size=15, color="#0F172A", bold=True, align="center")
    draw_text(ctx, "Kümülatif Olasılık P(Maliyet ≤ X)", pb_x + 28, (by0 + by1) / 2.0, size=15, color="#0F172A", bold=True, align="center", valign="middle", angle=-math.pi / 2.0)

    for xv, col, lbl, al, dx in [
        (x50, "#D97706", "$50M Yumuşak Çizgi", "right", -6),
        (x100, "#DC2626", "$100M Sert Sınır", "left", 6),
    ]:
        ctx.save()
        set_rgb(ctx, col)
        ctx.set_line_width(2.6)
        ctx.set_dash([9, 5])
        ctx.move_to(xv, by0)
        ctx.line_to(xv, by1)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, lbl, xv + dx, by0 - 14, size=13.5, color=col, bold=True, align=al)

    cdf = data["cdf_curves"]
    probs = cdf["probs"]
    c_specs = [
        ("v4_fab_tco5_usd", "#059669", 3.2, [], "v4.0 Ticari Fab 5y TCO (N=1, P50=$16,1M)"),
        ("v3_prog_stoch_usd", "#64748B", 2.8, [7, 4], "v3.0 Program CAPEX (P50=$28,2M, P>100M=%2,75)"),
        ("v4_prog_stoch_usd", "#1D4ED8", 4.2, [], "v4.0 Program CAPEX (P50=$31,0M, P>100M=%3,19)"),
        ("v4_foak_tco5_usd", "#DC2626", 2.8, [4, 4], "v4.0 FOAK 5y TCO (CAPEX+Tesis+5y OPEX, P50=$39,7M)"),
    ]
    for key, col, lw, dash, _lbl in c_specs:
        ctx.save()
        set_rgb(ctx, col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        started = False
        for v, p in zip(cdf[key], probs):
            vm = v / 1e6
            if vm < 5.0:
                continue
            px, py = map_cx(vm), map_cy(p)
            if not started:
                ctx.move_to(px, py)
                started = True
            else:
                ctx.line_to(px, py)
            if vm >= 250.0:
                break
        ctx.stroke()
        ctx.restore()

    set_rgb(ctx, "#334155")
    ctx.set_line_width(1.6)
    ctx.rectangle(bx0, by0, bx1 - bx0, by1 - by0)
    ctx.stroke()

    # Legend box (bottom-right of Panel B) -> wait, top-left has wide empty space above curve!
    lg_x, lg_y, lg_w, lg_h = bx0 + 14, by0 + 52, 466, 144
    round_rect(ctx, lg_x, lg_y, lg_w, lg_h, 8)
    set_rgb(ctx, "#FFFFFF", 0.95)
    ctx.fill_preserve()
    set_rgb(ctx, "#94A3B8")
    ctx.set_line_width(1.2)
    ctx.stroke()
    for idx, (_k, col, lw, dash, lbl) in enumerate(c_specs):
        yy = lg_y + 24 + idx * 31
        ctx.save()
        set_rgb(ctx, col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(lg_x + 12, yy)
        ctx.line_to(lg_x + 48, yy)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, lbl, lg_x + 56, yy, size=12.4, color="#0F172A", bold=(idx == 2), valign="middle")

    # Bottom Budget-Cap Verdict & Margin Card in Panel B (100% driven by exp134.json)
    bc2 = data["budget_cap_v3_vs_v4"]
    tco2 = data["tco_5yr_summary_no_wafers"]
    v4d2 = data["v4_hardware_deltas"]
    ep = bc2["exceedance_probabilities"]
    conv = bc2["convergence_25k_vs_50k"]
    round_rect(ctx, pb_x + 24, ay1 + 68, pb_w - 48, 222, 8)
    set_rgb(ctx, "#EFF6FF")
    ctx.fill_preserve()
    set_rgb(ctx, "#2563EB")
    ctx.set_line_width(1.4)
    ctx.stroke()

    v4_hw_nom_m = v4d2["v4_m3_hw_nom_usd"] / 1e6
    v4_hw_p50_m = bc2["v4_hw_mc_usd"]["p50"] / 1e6
    v3_pr_p50_m = bc2["v3_prog_stoch_usd"]["p50"] / 1e6
    v4_pr_p50_m = bc2["v4_prog_stoch_usd"]["p50"] / 1e6
    v4_foak_p50_m = tco2["v4_foak_program_5yr_tco_usd"]["p50"] / 1e6
    v4_foak_p95_m = tco2["v4_foak_program_5yr_tco_usd"]["p95"] / 1e6

    draw_text(ctx, "v3.0 → v4.0 Bütçe Tavanı Marj Özeti (H140 Kuralı: ≤$50M / ≤$100M)", pb_x + 42, ay1 + 96, size=14.5, color="#1E3A8A", bold=True)
    def fmt_tr(v: float, dec: int = 2) -> str:
        return f"{v:.{dec}f}".replace(".", ",")

    cap_lines = [
        f"• v4.0 Donanım BOM (${fmt_tr(v4_hw_nom_m)}M nom, P50=${fmt_tr(v4_hw_p50_m)}M):  P(BOM > $50M) = %{fmt_tr(ep['P_v4_BOM_gt_50M']*100)} (10×+ marj).",
        f"• v3.0 → v4.0 Program CAPEX (Stokastik ×3–10):  P50 ${fmt_tr(v3_pr_p50_m, 1)}M → ${fmt_tr(v4_pr_p50_m, 1)}M (+${fmt_tr(v4_pr_p50_m - v3_pr_p50_m, 1)}M); P(>50M) %{fmt_tr(ep['P_v3_Prog_stoch_gt_50M']*100, 1)} → %{fmt_tr(ep['P_v4_Prog_stoch_gt_50M']*100, 1)}.",
        f"• Sert Sınır Riski P(Program > $100M):          v3.0 %{fmt_tr(ep['P_v3_Prog_stoch_gt_100M']*100)} → v4.0 %{fmt_tr(ep['P_v4_Prog_stoch_gt_100M']*100)} ± %{fmt_tr(ep['SE_P_v4_Prog_gt_100M']*100)} (<%5, CX2 PASS).",
        f"• FOAK 5-Yıllık TCO (Program+Tesis+5y OPEX):    v4.0 P50 = ${fmt_tr(v4_foak_p50_m)}M, P95 = ${fmt_tr(v4_foak_p95_m)}M (<$100M sert sınır!).",
        f"• Yakınsama (25k vs 50k MC, CX6 PASS):          ΔP50 = %{fmt_tr(conv['rel_diff_p50']*100)}, ΔP95 = %{fmt_tr(conv['rel_diff_p95']*100)}.",
    ]
    for ci, cl in enumerate(cap_lines):
        draw_text(ctx, cl, pb_x + 42, ay1 + 128 + ci * 30, size=13.0, color="#0F172A", bold=(ci == 2))

    draw_text(
        ctx,
        "Kaynak: results/exp134_fab_economics_tco/exp134.json | Tüm USD değerleri {Model}/{Varsayım}/{Liste-Çapası}; gerçek teklif yoktur.",
        40,
        H - 22,
        size=14,
        color="#64748B",
    )

    out_path = OUT_DIR / "fig_exp134_v3_vs_v4_scaling.png"
    surf.write_to_png(str(out_path))
    assert Image.open(out_path).size == (W, H)
    return out_path


def main() -> None:
    data = json.loads(EXP_JSON.read_text(encoding="utf-8"))
    p1 = make_fig1_tco_cost_per_qubit(data)
    p2 = make_fig2_v3_vs_v4_scaling(data)
    print("Generated:", p1, p2)


if __name__ == "__main__":
    main()
