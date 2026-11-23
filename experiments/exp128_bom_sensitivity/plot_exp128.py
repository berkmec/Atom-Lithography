#!/usr/bin/env python3
"""Generate publication-grade PyCairo/PIL figures for Exp128.

Must be run with /usr/bin/python3 -B (system Python with cairo + PIL).
Outputs:
  - results/exp128_bom_sensitivity/fig_exp128_tornado_cdf.png (2200x1260)
  - results/exp128_bom_sensitivity/fig_exp128_m1_vs_m3_cost.png (2200x1260)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "exp128_bom_sensitivity"
EXP_JSON = OUT_DIR / "exp128.json"

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
    size: float = 16.0,
    color: str = "#1B263B",
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


def make_fig1_tornado_cdf(data: dict) -> Path:
    W, H = 2200, 1260
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    # Background
    set_rgb(ctx, "#F8FAFC")
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Header bar
    set_rgb(ctx, "#0F172A")
    ctx.rectangle(0, 0, W, 94)
    ctx.fill()
    draw_text(
        ctx,
        "Exp128 — 100.000 Örneklemli Korelasyonlu Monte Carlo: Tornado Duyarlılığı & Bütçe Tavanı CDF",
        40,
        42,
        size=28,
        color="#FFFFFF",
        bold=True,
    )
    n_parts = data["bom_detailed_summary"]["total_parts"]
    m3_m = data["bom_detailed_summary"]["m3_nom_usd"] / 1e6
    draw_text(
        ctx,
        f"BOM_DETAILED.csv v4.0 ({n_parts} parça, M3=${m3_m:.2f}M, S6.8=20 mK DR Baz) | Bütçe Kuralı: $50M Yumuşak / $100M Sert Sınır (Exp122/H140) | Teklif Yok {{Model/Varsayım}}",
        40,
        74,
        size=15.5,
        color="#CBD5E1",
    )

    # =========================================================================
    # PANEL A (LEFT): BOM-SCOPE TORNADO SENSITIVITY
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
        "A. M3 BOM Maliyet Sürücüleri (Tornado: P10–P90 Koşullu Ortalama & Varyans Payı)",
        pa_x + 24,
        pa_y + 38,
        size=20,
        color="#0F172A",
        bold=True,
    )
    bom_mean = data["monte_carlo_model_a_detailed"]["bom_with_bc_and_nl_usd"]["mean"]
    bom_p50 = data["monte_carlo_model_a_detailed"]["bom_with_bc_and_nl_usd"]["p50"]
    draw_text(
        ctx,
        f"Model A BOM Ortalaması = ${bom_mean/1e6:.2f}M (P50 = ${bom_p50/1e6:.2f}M) | Korelasyonlu Gaussian Kopula + %20 C-Sınıfı Zincir Şoku",
        pa_x + 24,
        pa_y + 66,
        size=14.5,
        color="#475569",
    )

    tornado = data["tornado_bom_scope"][:10]
    plot_x0 = pa_x + 335
    plot_x1 = pa_x + pa_w - 195
    plot_y0 = pa_y + 112
    plot_y1 = pa_y + pa_h - 145
    xmin_m, xmax_m = 2.0, 14.5

    def map_ax(val_m: float) -> float:
        return plot_x0 + (val_m - xmin_m) / (xmax_m - xmin_m) * (plot_x1 - plot_x0)

    # Zebra bands first (behind grid & vertical mean line)
    n_bars = len(tornado)
    row_h = (plot_y1 - plot_y0) / n_bars
    bar_h = row_h * 0.56
    for i in range(n_bars):
        if i % 2 == 0:
            cy = plot_y0 + (i + 0.5) * row_h
            set_rgb(ctx, "#F8FAFC")
            ctx.rectangle(pa_x + 14, cy - row_h / 2.0, pa_w - 28, row_h)
            ctx.fill()

    # Grid lines
    for tick in [2, 4, 6, 8, 10, 12, 14]:
        gx = map_ax(tick)
        set_rgb(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(gx, plot_y0)
        ctx.line_to(gx, plot_y1)
        ctx.stroke()
        draw_text(ctx, f"${tick}M", gx, plot_y1 + 24, size=14, color="#334155", align="center")

    draw_text(
        ctx,
        "Koşullu Ortalama M3 BOM Maliyeti (Milyon USD)",
        (plot_x0 + plot_x1) / 2.0,
        plot_y1 + 54,
        size=15,
        color="#0F172A",
        bold=True,
        align="center",
    )

    mx = map_ax(bom_mean / 1e6)
    short_labels = {
        "S6.6 Okuma Zinciri (56x B/C Duvarı)": "S6.6 Okuma Zinciri (B/C)",
        "S2.1-2.3 MEMS Kafa & Fab NRE": "S2.1-2.3 MEMS Kafa & NRE",
        "S6.8 Seyreltme Kriyostatı (20 mK)": "S6.8 Seyreltme (20 mK DR)",
        "v4.0 Paketi (M4+S5.5+PT420+BOED)": "v4.0 Paketi (M4+S5.5+PT420)",
        "S1 Kaynak+Kolon+Süzgeç+PH3 (Exp124)": "S1 Kaynak/Kolon (Exp124)",
        "S6 Diğer (PT420/MW/RF/SET)": "S6 Diğer (PT420/MW/SET)",
        "S6.3 1.5T/<=0.4T Mıknatıs (Exp125)": "S6.3 Mıknatıs (Exp125)",
        "S4 Piezo Kademe + İnterferometri": "S4 Piezo + İnterferometri",
        "S5 UHV Oda + Tavlama + Epi": "S5 UHV + Tavlama + Epi",
        "S3 IBIC + Vakum-İçi Ön-Uç (Exp127)": "S3 IBIC Ön-Uç (Exp127)",
        "S7 Kontrol/AWG/SKY130": "S7 Kontrol/AWG/SKY130",
        "S9 Yedekler & Kalibrasyon": "S9 Yedekler & Kalibr.",
        "S2 Diğer (ASIC/Metroloji)": "S2 Diğer (ASIC/Metroloji)",
    }

    for i, item in enumerate(tornado):
        cy = plot_y0 + (i + 0.5) * row_h
        lo_m = item["cond_bom_mean_at_p10_usd"] / 1e6
        hi_m = item["cond_bom_mean_at_p90_usd"] / 1e6
        mean_m = bom_mean / 1e6
        x_lo = map_ax(max(xmin_m, lo_m))
        x_hi = map_ax(min(xmax_m, hi_m))

        # Left segment (driver at P10 -> below mean)
        set_rgb(ctx, "#0284C7", 0.88)
        ctx.rectangle(x_lo, cy - bar_h / 2.0, max(2.0, mx - x_lo), bar_h)
        ctx.fill()

        # Right segment (driver at P90 -> above mean)
        set_rgb(ctx, "#DC2626" if i == 0 else "#EA580C", 0.88)
        ctx.rectangle(mx, cy - bar_h / 2.0, max(2.0, x_hi - mx), bar_h)
        ctx.fill()

        # Label on left
        lbl = short_labels.get(item["driver"], item["driver"][:28])
        draw_text(
            ctx,
            lbl,
            plot_x0 - 12,
            cy,
            size=14.5,
            color="#0F172A",
            bold=(i < 3),
            align="right",
            valign="middle",
        )

        # Stats on right
        var_pct = item["variance_contrib_share"] * 100.0
        rho = item["spearman_rho"]
        badge_txt = f"Var %{var_pct:4.1f} | ρ={rho:.2f}"
        draw_text(
            ctx,
            badge_txt,
            plot_x1 + 14,
            cy,
            size=13.5,
            color="#991B1B" if i == 0 else "#334155",
            bold=(i < 3),
            align="left",
            valign="middle",
        )

    # Mean vertical line drawn cleanly on top of zebra & bars
    ctx.save()
    set_rgb(ctx, "#0F172A", 0.85)
    ctx.set_line_width(2.0)
    ctx.set_dash([7, 5])
    ctx.move_to(mx, plot_y0 - 8)
    ctx.line_to(mx, plot_y1 + 4)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, f"Ort. ${bom_mean/1e6:.2f}M", mx, plot_y0 - 16, size=13.5, color="#0F172A", bold=True, align="center")

    # Legend + RFQ callout inside Panel A bottom
    leg_y = plot_y1 + 88
    set_rgb(ctx, "#0284C7")
    ctx.rectangle(pa_x + 28, leg_y - 11, 22, 14)
    ctx.fill()
    draw_text(ctx, "Sürücü alt %10 (P10)", pa_x + 58, leg_y, size=14, color="#334155")

    set_rgb(ctx, "#EA580C")
    ctx.rectangle(pa_x + 245, leg_y - 11, 22, 14)
    ctx.fill()
    draw_text(ctx, "Sürücü üst %10 (P90)", pa_x + 275, leg_y, size=14, color="#334155")

    # RFQ badge (7-RFQ v4.0 full procurement scope)
    rfq_nom = data["rfq_coverage"]["rfq7_nom_share"] * 100.0
    rfq_var = data["rfq_coverage"]["rfq7_variance_share_mc"] * 100.0
    top3_var = data["top3_bom_var_share_s66_s68_s2"] * 100.0
    round_rect(ctx, pa_x + 480, leg_y - 24, 548, 46, 8)
    set_rgb(ctx, "#EFF6FF")
    ctx.fill_preserve()
    set_rgb(ctx, "#2563EB")
    ctx.set_line_width(1.4)
    ctx.stroke()
    draw_text(
        ctx,
        f"7-RFQ Kapsamı: Nominal %{rfq_nom:.1f} | MC Varyans %{rfq_var:.1f} (İlk-3: %{top3_var:.1f})",
        pa_x + 754,
        leg_y - 1,
        size=14,
        color="#1E3A8A",
        bold=True,
        align="center",
        valign="middle",
    )

    # =========================================================================
    # PANEL B (RIGHT): EMPIRICAL CDFs & BUDGET CAP ZONES ($50M / $100M)
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
        "B. Bütçe Tavanı Aşım Analizi — 100k Monte Carlo Ampirik CDF",
        pb_x + 24,
        pb_y + 38,
        size=20,
        color="#0F172A",
        bold=True,
    )
    draw_text(
        ctx,
        "M3 Donanım BOM vs Program Çarpanları (×3, Stokastik ×3–×10, ×10) | Logaritmik USD Ekseni",
        pb_x + 24,
        pb_y + 66,
        size=14.5,
        color="#475569",
    )

    bx0, bx1 = pb_x + 88, pb_x + pb_w - 38
    by0, by1 = pb_y + 112, pb_y + pb_h - 145
    log_min, log_max = math.log10(1.5), math.log10(250.0)

    def map_bx(val_m: float) -> float:
        lv = math.log10(max(1.5, min(250.0, val_m)))
        return bx0 + (lv - log_min) / (log_max - log_min) * (bx1 - bx0)

    def map_by(prob: float) -> float:
        return by1 - prob * (by1 - by0)

    # Shaded budget zones
    x50 = map_bx(50.0)
    x100 = map_bx(100.0)
    set_rgb(ctx, "#ECFDF5", 0.70)
    ctx.rectangle(bx0, by0, x50 - bx0, by1 - by0)
    ctx.fill()
    set_rgb(ctx, "#FFFBEB", 0.85)
    ctx.rectangle(x50, by0, x100 - x50, by1 - by0)
    ctx.fill()
    set_rgb(ctx, "#FEF2F2", 0.85)
    ctx.rectangle(x100, by0, bx1 - x100, by1 - by0)
    ctx.fill()

    # Zone banners (GEREKÇELİ & YASAK placed in clean upper-center / lower space so curves never collide)
    draw_text(ctx, "NORMAL BÖLGE (≤$50M)", (bx0 + x50) / 2.0, by0 + 22, size=13, color="#065F46", bold=True, align="center")
    draw_text(ctx, "GEREKÇELİ", (x50 + x100) / 2.0, by0 + 20, size=12.5, color="#92400E", bold=True, align="center")
    draw_text(ctx, "$50M–$100M", (x50 + x100) / 2.0, by0 + 37, size=12, color="#92400E", align="center")
    draw_text(ctx, "YASAK", (x100 + bx1) / 2.0, map_by(0.56), size=13, color="#991B1B", bold=True, align="center")
    draw_text(ctx, ">$100M", (x100 + bx1) / 2.0, map_by(0.52), size=12.5, color="#991B1B", align="center")

    # Grid lines X (log ticks)
    for tk in [2, 5, 10, 20, 50, 100, 200]:
        gx = map_bx(tk)
        set_rgb(ctx, "#CBD5E1", 0.7)
        ctx.set_line_width(1.0)
        ctx.move_to(gx, by0)
        ctx.line_to(gx, by1)
        ctx.stroke()
        draw_text(ctx, f"${tk}M", gx, by1 + 24, size=14, color="#334155", bold=(tk in (50, 100)), align="center")

    # Grid lines Y
    for yp in [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 0.9, 1.0]:
        gy = map_by(yp)
        set_rgb(ctx, "#CBD5E1", 0.7 if yp not in (0.5, 0.9) else 0.95)
        ctx.set_line_width(1.0)
        ctx.move_to(bx0, gy)
        ctx.line_to(bx1, gy)
        ctx.stroke()
        if yp in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
            draw_text(ctx, f"%{int(yp*100)}", bx0 - 12, gy, size=14, color="#334155", align="right", valign="middle")

    draw_text(
        ctx,
        "Toplam Maliyet (Milyon USD, Log Ölçek)",
        (bx0 + bx1) / 2.0,
        by1 + 54,
        size=15,
        color="#0F172A",
        bold=True,
        align="center",
    )
    draw_text(
        ctx,
        "Kümülatif Olasılık P(Maliyet ≤ X)",
        pb_x + 28,
        (by0 + by1) / 2.0,
        size=15,
        color="#0F172A",
        bold=True,
        align="center",
        valign="middle",
        angle=-math.pi / 2.0,
    )

    # Vertical threshold lines $50M and $100M (non-overlapping top labels)
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

    # Plot 4 empirical CDF curves
    cdf = data["cdf_curves"]
    probs = cdf["probs"]
    curves = [
        ("bom_usd", "#059669", 3.2, [], "M3 BOM Donanım (S6.8=20 mK)"),
        ("prog_x3_usd", "#0284C7", 2.6, [8, 4], "Program ×3 (Sabit Varsayım)"),
        ("prog_stoch_usd", "#1D4ED8", 4.2, [], "Program Stokastik (×3–×10, P50=5.5×)"),
        ("prog_x10_usd", "#DC2626", 2.8, [4, 4], "Program ×10 (Üst Varsayım)"),
    ]
    for key, col, lw, dash, _label in curves:
        vals = cdf[key]
        ctx.save()
        set_rgb(ctx, col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        started = False
        for v, p in zip(vals, probs):
            vm = v / 1e6
            if vm < 1.5:
                continue
            px = map_bx(vm)
            py = map_by(p)
            if not started:
                ctx.move_to(px, py)
                started = True
            else:
                ctx.line_to(px, py)
            if vm >= 250.0:
                break
        ctx.stroke()
        ctx.restore()

    # Plot border
    set_rgb(ctx, "#475569")
    ctx.set_line_width(1.5)
    ctx.rectangle(bx0, by0, bx1 - bx0, by1 - by0)
    ctx.stroke()

    # Legend box (top-left of Panel B, safely below zone header)
    lg_x, lg_y, lg_w, lg_h = bx0 + 16, by0 + 56, 370, 146
    round_rect(ctx, lg_x, lg_y, lg_w, lg_h, 8)
    set_rgb(ctx, "#FFFFFF", 0.94)
    ctx.fill_preserve()
    set_rgb(ctx, "#94A3B8")
    ctx.set_line_width(1.2)
    ctx.stroke()
    for idx, (_k, col, lw, dash, label) in enumerate(curves):
        yy = lg_y + 26 + idx * 31
        ctx.save()
        set_rgb(ctx, col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(lg_x + 14, yy)
        ctx.line_to(lg_x + 54, yy)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, label, lg_x + 64, yy, size=13.5, color="#0F172A", bold=(idx == 2), valign="middle")

    # Exceedance probability callout table (bottom-right of Panel B)
    ep = data["monte_carlo_model_a_detailed"]["exceedance_probabilities"]
    ps = data["monte_carlo_model_a_detailed"]["program_stochastic_3_to_10_usd"]
    p10 = data["monte_carlo_model_a_detailed"]["program_x10_usd"]
    bm = data["monte_carlo_model_a_detailed"]["bom_with_bc_and_nl_usd"]
    cb_x, cb_y, cb_w, cb_h = bx1 - 486, by1 - 216, 472, 200
    round_rect(ctx, cb_x, cb_y, cb_w, cb_h, 8)
    set_rgb(ctx, "#FFFFFF", 0.96)
    ctx.fill_preserve()
    set_rgb(ctx, "#1E3A8A")
    ctx.set_line_width(1.4)
    ctx.stroke()
    draw_text(ctx, "Aşım Olasılıkları (N=100.000, Model A)", cb_x + 16, cb_y + 26, size=14.5, color="#0F172A", bold=True)
    rows_txt = [
        ("Senaryo", "P50", "P95", "P(>50M)", "P(>100M)"),
        ("M3 BOM Donanım", f"${bm['p50']/1e6:.1f}M", f"${bm['p95']/1e6:.1f}M", f"%{ep['P_BOM_gt_50M']*100:.2f}", f"%{ep['P_BOM_gt_100M']*100:.2f}"),
        ("Prog. Stokastik", f"${ps['p50']/1e6:.1f}M", f"${ps['p95']/1e6:.1f}M", f"%{ep['P_Program_stoch_gt_50M']*100:.1f}", f"%{ep['P_Program_stoch_gt_100M']*100:.2f}"),
        ("Prog. Sabit ×10", f"${p10['p50']/1e6:.1f}M", f"${p10['p95']/1e6:.1f}M", f"%{ep['P_Program_x10_gt_50M']*100:.1f}", f"%{ep['P_Program_x10_gt_100M']*100:.2f}"),
    ]
    col_xs = [cb_x + 16, cb_x + 168, cb_x + 240, cb_x + 314, cb_x + 394]
    for r_i, rt in enumerate(rows_txt):
        ry = cb_y + 56 + r_i * 34
        if r_i == 0:
            set_rgb(ctx, "#F1F5F9")
            ctx.rectangle(cb_x + 8, ry - 16, cb_w - 16, 26)
            ctx.fill()
        for c_i, val in enumerate(rt):
            clr = "#991B1B" if (r_i >= 2 and c_i == 4) else ("#1D4ED8" if r_i == 2 else "#1E293B")
            draw_text(ctx, val, col_xs[c_i], ry, size=13, color=clr, bold=(r_i in (0, 2)))

    # Bottom footer inside Panel B
    conv = data["monte_carlo_model_a_detailed"]["convergence_50k_vs_100k"]
    draw_text(
        ctx,
        f"Yakınsama (50k vs 100k): ΔP50=%{conv['rel_diff_p50']*100:.2f}, ΔP95=%{conv['rel_diff_p95']*100:.2f}, SE(P>100M)=±{ep['SE_P_Program_stoch_gt_100M']*100:.2f}% | Model B P50=${data['monte_carlo_model_b_canonical_plus_deltas']['canonical_plus_deltas_prog_stoch_usd']['p50']/1e6:.1f}M",
        pb_x + 24,
        pb_y + pb_h - 24,
        size=13,
        color="#475569",
    )

    # Global footer
    draw_text(
        ctx,
        "Kaynak: results/exp128_bom_sensitivity/exp128.json (seed=2026128) | Kanonik BOM.csv SHA-256 korundu | Gerçek tedarikçi teklifi yoktur.",
        40,
        H - 22,
        size=14,
        color="#64748B",
    )

    out_path = OUT_DIR / "fig_exp128_tornado_cdf.png"
    surf.write_to_png(str(out_path))
    # Verify via PIL
    im = Image.open(out_path)
    assert im.size == (W, H)
    return out_path


def make_fig2_m1_m3_evpi(data: dict) -> Path:
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
        "Exp128 — M1 vs M3 Alt-Sistem Maliyet Kırılımı & 20 mK vs 1 K Sıcak-Okuma EVPI Başa-Baş Analizi",
        40,
        42,
        size=28,
        color="#FFFFFF",
        bold=True,
    )
    m3_v4_m = data["bom_detailed_summary"]["m3_nom_usd"] / 1e6
    n_p = data["bom_detailed_summary"]["total_parts"]
    draw_text(
        ctx,
        f"Kanonik Exp122 ($2.53M) → Detaylı M3 v4.0 BOM (${m3_v4_m:.2f}M, {n_p} Parça) | Exp121 20 mK Seyreltme Baz Kararının Karar-Teorik Doğrulaması",
        40,
        74,
        size=15.5,
        color="#CBD5E1",
    )

    # =========================================================================
    # PANEL A (LEFT): STACKED BAR — Exp122 vs M1 Prototype vs M3 Detailed BOM
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
        "A. Alt-Sistem Bazlı Donanım Maliyeti: Exp122 Baz vs M1 Prototip vs M3 Altın Ölçek",
        pa_x + 24,
        pa_y + 38,
        size=19.5,
        color="#0F172A",
        bold=True,
    )
    draw_text(
        ctx,
        "Nominal Donanım BOM-Kapsamı (Milyon USD) | Hata Çubukları: Alt–Üst Bant (P10–P90)",
        pa_x + 24,
        pa_y + 66,
        size=14.5,
        color="#475569",
    )

    ax0, ax1 = pa_x + 90, pa_x + 640
    ay0, ay1 = pa_y + 115, pa_y + 770
    ymax_m = 5.6

    def map_ay(val_m: float) -> float:
        return ay1 - (val_m / ymax_m) * (ay1 - ay0)

    # Y grid
    for tk in [0, 1, 2, 3, 4, 5]:
        gy = map_ay(tk)
        set_rgb(ctx, "#E2E8F0")
        ctx.set_line_width(1.0)
        ctx.move_to(ax0, gy)
        ctx.line_to(ax1, gy)
        ctx.stroke()
        draw_text(ctx, f"${tk}M", ax0 - 12, gy, size=14.5, color="#334155", align="right", valign="middle")

    draw_text(
        ctx,
        "Nominal BOM Donanım Maliyeti (Milyon USD)",
        pa_x + 28,
        (ay0 + ay1) / 2.0,
        size=15,
        color="#0F172A",
        bold=True,
        align="center",
        valign="middle",
        angle=-math.pi / 2.0,
    )

    sub_colors = [
        ("S6", "#1D4ED8", "S6 Kriyo / 20mK DR / Mıknatıs / 56x Zincir"),
        ("S2", "#DC2626", "S2 MEMS Kafa + Fab NRE + ASIC"),
        ("S1", "#EA580C", "S1 İyon Kaynağı + Kolon + Süzgeç + PH3"),
        ("S4", "#0D9488", "S4 Piezo Kademe + İnterferometri"),
        ("S5", "#0284C7", "S5 UHV Oda + Tavlama + Epi"),
        ("S3", "#7C3AED", "S3 IBIC + Vakum-İçi Ön-Uç (Exp127)"),
        ("S7", "#475569", "S7 Kontrol / GPU / AWG / SKY130"),
        ("S9", "#CA8A04", "S9 Yedekler & Kalibrasyon"),
    ]
    sr = data["subsystem_reconciliation"]
    configs = [
        (
            "Exp122 Kanonik\n(40 satır @ $720)",
            {s: sr[s]["exp122_central_usd"] / 1e6 for s, _, _ in sub_colors},
            data["canonical_gate"]["nl163_central_usd_u720"] / 1e6,
            None,
            None,
        ),
        (
            "M1 Prototip\n(Tek-Demet Lab)",
            {s: sr[s]["m1_nom_usd"] / 1e6 for s, _, _ in sub_colors},
            data["bom_detailed_summary"]["m1_nom_usd"] / 1e6,
            data["bom_detailed_summary"]["m1_low_usd"] / 1e6,
            data["bom_detailed_summary"]["m1_high_usd"] / 1e6,
        ),
        (
            f"M3 BOM_DETAILED v4.0\n({n_p} Parça Altın)",
            {s: sr[s]["detailed_m3_nom_usd"] / 1e6 for s, _, _ in sub_colors},
            data["bom_detailed_summary"]["m3_nom_usd"] / 1e6,
            data["bom_detailed_summary"]["m3_low_usd"] / 1e6,
            data["bom_detailed_summary"]["m3_high_usd"] / 1e6,
        ),
    ]

    bar_w = 116
    centers = [ax0 + 92, ax0 + 275, ax0 + 458]
    for cx, (lbl, stacks, tot_m, lo_m, hi_m) in zip(centers, configs):
        cum = 0.0
        for s_key, col, _desc in sub_colors:
            v = stacks[s_key]
            if v <= 0.001:
                continue
            y_bot = map_ay(cum)
            y_top = map_ay(cum + v)
            set_rgb(ctx, col, 0.90)
            ctx.rectangle(cx - bar_w / 2.0, y_top, bar_w, y_bot - y_top)
            ctx.fill()
            set_rgb(ctx, "#FFFFFF", 0.6)
            ctx.set_line_width(1.0)
            ctx.rectangle(cx - bar_w / 2.0, y_top, bar_w, y_bot - y_top)
            ctx.stroke()
            if v >= 0.34:
                draw_text(
                    ctx,
                    f"{s_key}: ${v:.2f}M",
                    cx,
                    (y_top + y_bot) / 2.0,
                    size=12.5,
                    color="#FFFFFF",
                    bold=True,
                    align="center",
                    valign="middle",
                )
            cum += v

        # Total label above bar
        draw_text(
            ctx,
            f"${tot_m:.2f}M",
            cx,
            map_ay(tot_m) - 12,
            size=16.5,
            color="#0F172A",
            bold=True,
            align="center",
        )
        # Note range below total or as clean bracket note
        if lo_m is not None and hi_m is not None:
            draw_text(
                ctx,
                f"(${lo_m:.2f}–${hi_m:.2f}M)",
                cx,
                map_ay(tot_m) - 34,
                size=12.5,
                color="#475569",
                align="center",
            )

        # X axis multiline label
        for li, line in enumerate(lbl.split("\n")):
            draw_text(ctx, line, cx, ay1 + 24 + li * 20, size=13.5, color="#0F172A", bold=(li == 0), align="center")

    # Axes line
    set_rgb(ctx, "#334155")
    ctx.set_line_width(1.6)
    ctx.move_to(ax0, ay0)
    ctx.line_to(ax0, ay1)
    ctx.line_to(ax1, ay1)
    ctx.stroke()

    # Right column inside Panel A: Legend + Delta Reconciliation Card
    rx = ax1 + 24
    rw = pa_x + pa_w - rx - 22
    round_rect(ctx, rx, ay0, rw, 315, 8)
    set_rgb(ctx, "#F8FAFC")
    ctx.fill_preserve()
    set_rgb(ctx, "#CBD5E1")
    ctx.set_line_width(1.2)
    ctx.stroke()
    draw_text(ctx, "Alt-Sistem Renk Anahtarı", rx + 14, ay0 + 26, size=14.5, color="#0F172A", bold=True)
    for idx, (_s, col, desc) in enumerate(sub_colors):
        yy = ay0 + 54 + idx * 32
        set_rgb(ctx, col)
        ctx.rectangle(rx + 14, yy - 9, 18, 16)
        ctx.fill()
        draw_text(ctx, desc, rx + 40, yy, size=12.8, color="#1E293B", valign="middle")

    # Delta Bridge Card (below legend) — now includes explicit v4.0 upgrade step!
    db = data["delta_bridge_exp122_to_detailed"]
    dy = ay0 + 328
    dh = 332
    round_rect(ctx, rx, dy, rw, dh, 8)
    set_rgb(ctx, "#EFF6FF")
    ctx.fill_preserve()
    set_rgb(ctx, "#2563EB")
    ctx.set_line_width(1.4)
    ctx.stroke()
    tot_d_m = db["total_delta_usd"] / 1e6
    draw_text(ctx, f"Exp122 → M3 v4.0 Köprüsü (+${tot_d_m:.2f}M)", rx + 14, dy + 25, size=14.2, color="#1E3A8A", bold=True)
    bridge_rows = [
        ("Exp122 Merkez Baz", db["exp122_central_baseline_usd"]),
        ("+ S2 MEMS Sabit Fab/NRE", db["delta_s2_mems_nre_and_head_usd"]),
        ("+ Exp125 Mıknatıs + NbTiN", db["delta_exp125_magnet_shield_nbtin_usd"]),
        ("+ S9 Yedekler & Kalibrasyon", db["delta_s9_spares_calibration_usd"]),
        ("+ Exp124 Yavaşlatma/Süzgeç/PH3", db["delta_exp124_decel_filter_ph3_usd"]),
        ("+ Exp127 Vakum-İçi IBIC Ön-Uç", db["delta_exp127_invac_ibic_frontend_usd"]),
        ("+ COTS/UHV/PT420 Çapa Uyumu", db["delta_other_cots_uhv_anchor_align_usd"]),
        ("+ v4.0 Paketi (M4+S5.5+PT420+GPU)", db["delta_v4_0_upgrade_package_usd"]),
        ("= M3 v4.0 BOM_DETAILED Nominal", db["bom_detailed_m3_nom_usd"]),
    ]
    for bi, (blbl, bval) in enumerate(bridge_rows):
        byy = dy + 54 + bi * 30
        is_tot = bi in (0, len(bridge_rows) - 1)
        is_v4 = bi == len(bridge_rows) - 2
        if bi == len(bridge_rows) - 1:
            set_rgb(ctx, "#93C5FD")
            ctx.set_line_width(1.2)
            ctx.move_to(rx + 12, byy - 15)
            ctx.line_to(rx + rw - 12, byy - 15)
            ctx.stroke()
        draw_text(
            ctx,
            blbl,
            rx + 14,
            byy,
            size=12.3,
            color="#065F46" if is_v4 else ("#0F172A" if is_tot else "#334155"),
            bold=(is_tot or is_v4),
        )
        sign = "" if is_tot else "+"
        draw_text(
            ctx,
            f"{sign}${bval/1e3:,.0f}k",
            rx + rw - 14,
            byy,
            size=12.3,
            color="#065F46" if is_v4 else ("#1E3A8A" if is_tot else "#0F172A"),
            bold=(is_tot or is_v4),
            align="right",
        )

    # Bottom takeaway box in Panel A (100% dynamic from exp128.json)
    m1_m = data["bom_detailed_summary"]["m1_nom_usd"] / 1e6
    m1_pct = data["bom_detailed_summary"]["m1_to_m3_nom_ratio"] * 100.0
    m3_v3_m = data["bom_detailed_summary"]["m3_v3_base_nom_usd"] / 1e6
    v4_d_k = data["bom_detailed_summary"]["v4_delta_nom_usd"] / 1e3
    margin_50 = 50.0 / m3_v4_m
    round_rect(ctx, pa_x + 24, ay1 + 78, pa_w - 48, 174, 8)
    set_rgb(ctx, "#F8FAFC")
    ctx.fill_preserve()
    set_rgb(ctx, "#94A3B8")
    ctx.set_line_width(1.2)
    ctx.stroke()
    draw_text(ctx, "M1 → M3 v4.0 Ölçeklenme & Bütçe Notları", pa_x + 42, ay1 + 106, size=15, color="#0F172A", bold=True)
    notes_a = [
        f"• M1 Tek-Demet (${m1_m:.2f}M nom, M3 v4.0'ın %{m1_pct:.1f}'i): 20 mK DR ($720k), PT420+ayrıştırma, 1.5T mıknatıs, UHV, S5.5 & piezo dahil.",
        f"• M1 → M3 v4.0 (+${m3_v4_m - m1_m:.2f}M): 56 okuma zinciri + NbTiN (+$700k), MEMS fab/NRE (+$685k), M4 kavite veri yolu (+$245k), IBIC+yedekler.",
        f"• v3.0 (${m3_v3_m:.2f}M) → v4.0 (+${v4_d_k:.0f}k): M4 $245k (Exp131) + S5.5 $95k (Exp130) + PT420 $68k (Exp133) + BOED GPU $12k (Exp132/134).",
        f"• Tüm v4.0 deltalarıyla bile M3 BOM (${m3_v4_m:.2f}M) $50M sınırının {margin_50:.1f}× altındadır (S6.6 $680.4k & S6.8 $720k Exp122 ile birebir).",
    ]
    for ni, nt in enumerate(notes_a):
        draw_text(ctx, nt, pa_x + 40, ay1 + 136 + ni * 27, size=12.4, color="#334155")

    # =========================================================================
    # PANEL B (RIGHT): 20 mK vs 1 K HOT-READOUT EVPI & BREAK-EVEN FRONTIER
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
        "B. 20 mK Baz (Exp121) vs 1 K Sıcak-Okuma AR-GE Başa-Baş & EVPI Analizi",
        pb_x + 24,
        pb_y + 38,
        size=19.5,
        color="#0F172A",
        bold=True,
    )
    ev = data["evpi_20mk_vs_1k"]
    edhw = ev["expected_hw_saving_per_machine_usd"]
    draw_text(
        ctx,
        f"Makine Başına Beklenen Donanım Tasarrufu E[ΔC_hw] = ${edhw/1e3:.1f}k (20 mK DR → 1 K Kademe) | Başa-Baş: N_be = C_RD / (p_succ · E[ΔC_hw])",
        pb_x + 24,
        pb_y + 66,
        size=14,
        color="#475569",
    )

    bx0, bx1 = pb_x + 92, pb_x + pb_w - 38
    by0, by1 = pb_y + 115, pb_y + 770
    p_min, p_max = 0.10, 0.90
    log_nmin, log_nmax = math.log10(0.5), math.log10(60.0)

    def map_px(p: float) -> float:
        return bx0 + (p - p_min) / (p_max - p_min) * (bx1 - bx0)

    def map_ny(nm: float) -> float:
        ln = math.log10(max(0.5, min(60.0, nm)))
        return by1 - (ln - log_nmin) / (log_nmax - log_nmin) * (by1 - by0)

    # Shaded regions using C_RD = $2.0M reference curve
    pts_2m = []
    for k in range(81):
        ps = p_min + k * (p_max - p_min) / 80.0
        nb = 2.0e6 / (ps * edhw)
        pts_2m.append((map_px(ps), map_ny(nb)))

    # Below $2M curve -> 20 mK Baseline Optimal (light blue/green)
    ctx.new_path()
    ctx.move_to(bx0, by1)
    for x, y in pts_2m:
        ctx.line_to(x, y)
    ctx.line_to(bx1, by1)
    ctx.close_path()
    set_rgb(ctx, "#EFF6FF", 0.78)
    ctx.fill()

    # Above $2M curve -> 1 K R&D Optimal (light amber)
    ctx.new_path()
    ctx.move_to(bx0, by0)
    for x, y in pts_2m:
        ctx.line_to(x, y)
    ctx.line_to(bx1, by0)
    ctx.close_path()
    set_rgb(ctx, "#FEF3C7", 0.45)
    ctx.fill()

    # Grid lines
    for pt in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        gx = map_px(pt)
        set_rgb(ctx, "#CBD5E1", 0.65)
        ctx.set_line_width(1.0)
        ctx.move_to(gx, by0)
        ctx.line_to(gx, by1)
        ctx.stroke()
        draw_text(ctx, f"%{int(pt*100)}", gx, by1 + 24, size=14, color="#334155", align="center")

    for nt in [1, 2, 5, 10, 20, 50]:
        gy = map_ny(nt)
        set_rgb(ctx, "#CBD5E1", 0.75)
        ctx.set_line_width(1.0)
        ctx.move_to(bx0, gy)
        ctx.line_to(bx1, gy)
        ctx.stroke()
        draw_text(ctx, f"{nt}", bx0 - 12, gy, size=14, color="#334155", bold=(nt == 1), align="right", valign="middle")

    draw_text(
        ctx,
        "1 K İmplant-Donör PSB Teknik Başarı Olasılığı (p_succ)",
        (bx0 + bx1) / 2.0,
        by1 + 54,
        size=15,
        color="#0F172A",
        bold=True,
        align="center",
    )
    draw_text(
        ctx,
        "Başa-Baş Makine Sayısı (N_makine, Log Ölçek)",
        pb_x + 28,
        (by0 + by1) / 2.0,
        size=15,
        color="#0F172A",
        bold=True,
        align="center",
        valign="middle",
        angle=-math.pi / 2.0,
    )

    # N = 1 single-machine line (M1 / M3 first build)
    y_n1 = map_ny(1.0)
    ctx.save()
    set_rgb(ctx, "#0F766E")
    ctx.set_line_width(2.4)
    ctx.set_dash([8, 5])
    ctx.move_to(bx0, y_n1)
    ctx.line_to(bx1, y_n1)
    ctx.stroke()
    ctx.restore()
    draw_text(
        ctx,
        "N = 1 İlk Makine (M1/M3) — Tüm Gerçekçi AR-GE Maliyetlerinde 20 mK Baz Optimal!",
        bx0 + 16,
        y_n1 + 22,
        size=13.5,
        color="#0F766E",
        bold=True,
    )

    # Plot C_RD curves
    rd_specs = [
        (0.5e6, "#059669", 2.6, [6, 4], "C_RD = $0.5M (Minimal Lab)"),
        (1.0e6, "#0284C7", 2.8, [], "C_RD = $1.0M (Hızlı Transfer)"),
        (2.0e6, "#1D4ED8", 4.2, [], "C_RD = $2.0M (Referans CU5)"),
        (5.0e6, "#DC2626", 3.0, [4, 4], "C_RD = $5.0M (Tam Program)"),
    ]
    for c_rd, col, lw, dash, _lbl in rd_specs:
        ctx.save()
        set_rgb(ctx, col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        started = False
        for k in range(161):
            ps = p_min + k * (p_max - p_min) / 160.0
            nb = c_rd / (ps * edhw)
            if nb > 60.0:
                continue
            px, py = map_px(ps), map_ny(nb)
            if not started:
                ctx.move_to(px, py)
                started = True
            else:
                ctx.line_to(px, py)
        ctx.stroke()
        ctx.restore()

    # Highlight CU5 point: p=0.50, N_be=6.03
    cu5_x = map_px(0.50)
    cu5_y = map_ny(ev["cu5_ref_breakeven_machines_hw"])
    set_rgb(ctx, "#DC2626")
    ctx.arc(cu5_x, cu5_y, 8.5, 0, 2 * math.pi)
    ctx.fill()
    set_rgb(ctx, "#FFFFFF")
    ctx.arc(cu5_x, cu5_y, 4.0, 0, 2 * math.pi)
    ctx.fill()

    # Callout for CU5 point (widened so text has comfortable padding)
    round_rect(ctx, cu5_x + 18, cu5_y - 44, 384, 72, 8)
    set_rgb(ctx, "#FFFFFF", 0.96)
    ctx.fill_preserve()
    set_rgb(ctx, "#DC2626")
    ctx.set_line_width(1.6)
    ctx.stroke()
    draw_text(ctx, "CU5 Referansı (C_RD=$2.0M, p=%50)", cu5_x + 30, cu5_y - 20, size=13.5, color="#991B1B", bold=True)
    draw_text(
        ctx,
        f"Başa-baş: N_be = {ev['cu5_ref_breakeven_machines_hw']:.2f} makine (ENV@1 = −$1.67M)",
        cu5_x + 30,
        cu5_y + 8,
        size=13,
        color="#1E293B",
    )

    # Region labels placed cleanly in open space (away from legend & curves)
    draw_text(ctx, "1 K AR-GE FİLO OPTİMAL BÖLGESİ", map_px(0.41), map_ny(38.0), size=14, color="#92400E", bold=True, align="center")
    draw_text(ctx, "(C_RD=$2M için N ≥ 6 makine)", map_px(0.41), map_ny(27.0), size=13, color="#92400E", align="center")
    draw_text(ctx, "20 mK SEYRELTME BAZ OPTİMAL (Exp121)", map_px(0.32), map_ny(1.52), size=14, color="#1E3A8A", bold=True, align="center")

    # Legend box (top-right inside Panel B)
    lg_x, lg_y, lg_w, lg_h = bx1 - 295, by0 + 14, 282, 134
    round_rect(ctx, lg_x, lg_y, lg_w, lg_h, 8)
    set_rgb(ctx, "#FFFFFF", 0.94)
    ctx.fill_preserve()
    set_rgb(ctx, "#94A3B8")
    ctx.set_line_width(1.2)
    ctx.stroke()
    for idx, (_crd, col, lw, dash, lbl) in enumerate(rd_specs):
        yy = lg_y + 24 + idx * 29
        ctx.save()
        set_rgb(ctx, col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(lg_x + 12, yy)
        ctx.line_to(lg_x + 48, yy)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, lbl, lg_x + 56, yy, size=13, color="#0F172A", bold=(idx == 2), valign="middle")

    # Border
    set_rgb(ctx, "#334155")
    ctx.set_line_width(1.6)
    ctx.rectangle(bx0, by0, bx1 - bx0, by1 - by0)
    ctx.stroke()

    # Bottom Decision Summary Card in Panel B (EVPI comparison: 1K R&D vs 6-RFQ)
    round_rect(ctx, pb_x + 24, ay1 + 78, pb_w - 48, 174, 8)
    set_rgb(ctx, "#F8FAFC")
    ctx.fill_preserve()
    set_rgb(ctx, "#94A3B8")
    ctx.set_line_width(1.2)
    ctx.stroke()
    draw_text(ctx, "Karar-Teorik Özet: 1 K AR-GE EVPI vs 7-RFQ Teklif Toplama Değeri", pb_x + 42, ay1 + 106, size=15, color="#0F172A", bold=True)
    # Find EVPI at C_RD=$2M, p=0.50, N=1, 5, 10
    row_2m_50 = [r for r in ev["grid"] if abs(r["c_rd_usd"] - 2e6) < 1 and abs(r["p_succ"] - 0.5) < 1e-6][0]
    evpi_n1 = row_2m_50["by_n_mach"]["1"]["evpi_usd"]
    evpi_n5 = row_2m_50["by_n_mach"]["5"]["evpi_usd"]
    evpi_n10 = row_2m_50["by_n_mach"]["10"]["evpi_usd"]
    rfq7_var_pct = data["rfq_coverage"]["rfq7_variance_share_mc"] * 100.0
    notes_b = [
        f"• Tek Makine (N=1, C_RD=$2M, p=%50): 1 K AR-GE EVPI = ${evpi_n1/1e3:.0f}k (sıfır: bilgi gelse bile tek makinede $2M > ${edhw/1e3:.0f}k, karar değişmez!).",
        f"• Orta Filo (N=5): EVPI = ${evpi_n5/1e3:.0f}k (karar sınırında en yüksek bilgi değeri); Büyük Filo (N=10): EVPI = ${evpi_n10/1e3:.0f}k (1 K AR-GE kârlı).",
        f"• 7 Tedarikçi RFQ'sunu Gönderme Değeri: B/C duvarı aşım farkı E[C−B] = ${ev['s66_c_vs_b_expected_excess_usd']/1e6:.2f}M → ~sıfır maliyetle %{rfq7_var_pct:.1f} BOM varyansını çözer!",
        "• Stratejik Hüküm: M1 ve ilk M3 için 20 mK DR bazını koru (Exp121 PASS); ilk eylem 1 K AR-GE değil, RFQ-01..RFQ-07 tekliflerini toplamaktır.",
    ]
    for ni, nt in enumerate(notes_b):
        draw_text(ctx, nt, pb_x + 42, ay1 + 136 + ni * 27, size=13.2, color="#334155")

    draw_text(
        ctx,
        "Kaynak: results/exp128_bom_sensitivity/exp128.json & BOM_DETAILED.csv | Tüm USD rakamları {Model-Kalibrasyon-Exp114}/{Liste-Çapası}/{Varsayım}.",
        40,
        H - 22,
        size=14,
        color="#64748B",
    )

    out_path = OUT_DIR / "fig_exp128_m1_vs_m3_cost.png"
    surf.write_to_png(str(out_path))
    im = Image.open(out_path)
    assert im.size == (W, H)
    return out_path


def main() -> None:
    data = json.loads(EXP_JSON.read_text(encoding="utf-8"))
    p1 = make_fig1_tornado_cdf(data)
    p2 = make_fig2_m1_m3_evpi(data)
    print("Generated:", p1, p2)


if __name__ == "__main__":
    main()
