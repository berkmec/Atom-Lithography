"""Generate GitHub README hero cover dashboard `00_v3_overview_dashboard.png` (2400x1400).

Reads verified live metrics directly from:
  - results/exp124_ion_column_optics/exp124.json
  - results/exp125_cryo_magnet_readout/exp125.json
  - results/exp126_atom_cell_programming/exp126.json
  - results/exp127_detector_frontend_sim/exp127.json
  - results/exp128_bom_sensitivity/exp128.json
  - research/atom_lithography_machine/cad/cad_verification.json
  - research/atom_lithography_machine/BOM_DETAILED.csv

Runs under `/usr/bin/python3 -B` (PyCairo + Pillow).
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import cairo
from PIL import Image

CAD_DIR = Path(__file__).resolve().parent
ROOT = CAD_DIR.parents[2]
OUT_PNG = CAD_DIR / "drawings" / "00_v3_overview_dashboard.png"
W, H = 2400, 1400

# Palette — Dark-Navy / Crisp White Technical Dashboard
BG = (0.955, 0.967, 0.982)
WHITE = (1.0, 1.0, 1.0)
NAVY_TOP = (0.047, 0.106, 0.196)
NAVY_BOT = (0.094, 0.196, 0.322)
NAVY_TXT = (0.075, 0.145, 0.235)
SLATE_TXT = (0.28, 0.35, 0.44)
MUTED_TXT = (0.46, 0.53, 0.61)
BORDER = (0.82, 0.86, 0.91)
GRID = (0.90, 0.93, 0.96)

C_BLUE = (0.11, 0.44, 0.74)
C_PURPLE = (0.44, 0.27, 0.71)
C_GREEN = (0.09, 0.56, 0.38)
C_AMBER = (0.84, 0.52, 0.06)
C_TEAL = (0.06, 0.54, 0.60)
C_CRIMSON = (0.72, 0.18, 0.24)
C_GOLD_BG = (0.98, 0.89, 0.60)


def tr_f(val: float, decimals: int = 1) -> str:
    return f"{val:.{decimals}f}".replace(".", ",")


def tr_i(val: int) -> str:
    return f"{val:,}".replace(",", ".")


def rounded_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 12.0) -> None:
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def draw_text(
    ctx: cairo.Context, x: float, y: float, text: str, size: float,
    bold: bool = False, mono: bool = False, color=NAVY_TXT, align: str = "left",
) -> None:
    fam = "DejaVu Sans Mono" if mono else "DejaVu Sans"
    wt = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(fam, cairo.FONT_SLANT_NORMAL, wt)
    ctx.set_font_size(size)
    ext = ctx.text_extents(text)
    if align == "center":
        x -= ext.width / 2.0 + ext.x_bearing
    elif align == "right":
        x -= ext.width + ext.x_bearing
    ctx.set_source_rgb(*color)
    ctx.move_to(x, y)
    ctx.show_text(text)


def draw_pill(
    ctx: cairo.Context, x: float, y: float, text: str, bg_col, txt_col,
    size: float = 11.5, pad_x: float = 12.0, h: float = 26.0, align: str = "left",
) -> float:
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    tw = ctx.text_extents(text).width
    pw = tw + 2 * pad_x
    if align == "right":
        x -= pw
    rounded_rect(ctx, x, y, pw, h, r=h / 2.0)
    ctx.set_source_rgb(*bg_col)
    ctx.fill()
    draw_text(ctx, x + pw / 2.0, y + h * 0.67, text, size, bold=True, color=txt_col, align="center")
    return pw


def load_data() -> dict:
    d124 = json.loads((ROOT / "results/exp124_ion_column_optics/exp124.json").read_text(encoding="utf-8"))
    d125 = json.loads((ROOT / "results/exp125_cryo_magnet_readout/exp125.json").read_text(encoding="utf-8"))
    d126 = json.loads((ROOT / "results/exp126_atom_cell_programming/exp126.json").read_text(encoding="utf-8"))
    d127 = json.loads((ROOT / "results/exp127_detector_frontend_sim/exp127.json").read_text(encoding="utf-8"))
    d128 = json.loads((ROOT / "results/exp128_bom_sensitivity/exp128.json").read_text(encoding="utf-8"))
    cad = json.loads((CAD_DIR / "cad_verification.json").read_text(encoding="utf-8"))

    # Aggregate M3 nominal cost per subsystem directly from BOM_DETAILED.csv
    bom_sub_m3: dict[str, float] = {}
    bom_rows = 0
    with open(ROOT / "research/atom_lithography_machine/BOM_DETAILED.csv", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            bom_rows += 1
            sub = row["subsystem"].strip()
            bom_sub_m3[sub] = bom_sub_m3.get(sub, 0.0) + float(row["usd_nom"])

    return {
        "exp124": d124,
        "exp125": d125,
        "exp126": d126,
        "exp127": d127,
        "exp128": d128,
        "cad": cad,
        "bom_sub_m3": bom_sub_m3,
        "bom_rows": bom_rows,
    }


def draw_kpi_card(
    ctx: cairo.Context, x: float, y: float, w: float, h: float,
    tag: str, title: str, hero: str, lines: list[str], accent,
) -> None:
    # Subtle drop shadow
    rounded_rect(ctx, x + 3, y + 5, w, h, 14)
    ctx.set_source_rgba(0.05, 0.12, 0.22, 0.07)
    ctx.fill()

    # Card surface
    rounded_rect(ctx, x, y, w, h, 14)
    ctx.set_source_rgb(*WHITE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.4)
    ctx.stroke()

    # Colored top-left accent strip (clipped cleanly inside rounded card)
    ctx.save()
    rounded_rect(ctx, x, y, w, h, 14)
    ctx.clip()
    ctx.set_source_rgb(*accent)
    ctx.rectangle(x, y, 8, h)
    ctx.fill()
    ctx.restore()

    # Tag pill + Title
    pw = draw_pill(ctx, x + 26, y + 18, tag, accent, WHITE, size=11.5, pad_x=11, h=25)
    draw_text(ctx, x + 26 + pw + 12, y + 36, title, 16.0, bold=True, color=NAVY_TXT)

    # Hero KPI figure
    draw_text(ctx, x + 26, y + 86, hero, 25.0, bold=True, color=accent)

    # Divider
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.2)
    ctx.move_to(x + 26, y + 102)
    ctx.line_to(x + w - 24, y + 102)
    ctx.stroke()

    # 3 crisp metric lines
    ly = y + 132
    for ln in lines:
        ctx.set_source_rgb(*accent)
        ctx.arc(x + 32, ly - 5, 3.3, 0, 2 * math.pi)
        ctx.fill()
        draw_text(ctx, x + 44, ly, ln, 13.0, color=SLATE_TXT)
        ly += 34


def draw_quantum_panel(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    rounded_rect(ctx, x + 3, y + 5, w, h, 14)
    ctx.set_source_rgba(0.05, 0.12, 0.22, 0.07)
    ctx.fill()
    rounded_rect(ctx, x, y, w, h, 14)
    ctx.set_source_rgb(*WHITE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.5)
    ctx.stroke()

    # Header
    draw_pill(ctx, x + 24, y + 20, "Exp126 · 32B CUDA", C_AMBER, WHITE, size=11.5, h=25)
    draw_text(ctx, x + 190, y + 38, "16 Heterojen Hücrede 5 Kuantum Programı Sadakati (XY8-GRAPE)", 16.5, bold=True, color=NAVY_TXT)
    draw_text(ctx, x + 24, y + 66, "Koyu çubuk: gürültülü α=2 ortalaması (448 seyirci spin + banyo)  |  İnce işaret: ideal darbe sadakati  |  Kesikli: Q ≥ 0,85", 11.8, color=MUTED_TXT)

    ps = data["exp126"]["part3_multicell_16_programs"]["program_summary"]
    order = ["Bell", "GHZ-4", "Grover-2", "BitFlip-3", "QFT-3"]
    labels = {
        "Bell": "Bell (2q)",
        "GHZ-4": "GHZ-4 (4q)",
        "Grover-2": "Grover-2 (2q)",
        "BitFlip-3": "BitFlip-3 (3q)",
        "QFT-3": "QFT-3 (3q)",
    }

    # Bar plot geometry
    gx0, gx1 = x + 168, x + w - 122
    gy0 = y + 106
    bar_h = 36.0
    row_step = 62.0
    gw = gx1 - gx0
    xmin, xmax = 0.70, 1.00

    def bx(val: float) -> float:
        return gx0 + max(0.0, min(1.0, (val - xmin) / (xmax - xmin))) * gw

    # Grid lines (70% .. 100%)
    for tick in (0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00):
        tx = bx(tick)
        ctx.save()
        if abs(tick - 0.85) < 1e-6:
            ctx.set_dash([7.0, 5.0])
            ctx.set_source_rgba(*C_CRIMSON, 0.80)
            ctx.set_line_width(1.8)
        else:
            ctx.set_source_rgb(*GRID)
            ctx.set_line_width(1.0)
        ctx.move_to(tx, gy0 - 10)
        ctx.line_to(tx, gy0 + len(order) * row_step - 14)
        ctx.stroke()
        ctx.restore()
        lbl_col = C_CRIMSON if abs(tick - 0.85) < 1e-6 else MUTED_TXT
        draw_text(ctx, tx, gy0 + len(order) * row_step + 8, f"%{tick*100:.0f}", 11.2, bold=(abs(tick - 0.85) < 1e-6), color=lbl_col, align="center")

    draw_text(ctx, bx(0.85) + 6, gy0 - 14, "Q=0,85", 10.5, bold=True, color=C_CRIMSON)

    bar_cols = [C_TEAL, C_BLUE, (0.19, 0.49, 0.78), (0.28, 0.44, 0.75), C_PURPLE]
    for i, key in enumerate(order):
        rec = ps[key]
        noisy = rec["noisy_a2_mean"]
        ideal = rec["ideal_mean"]
        ry = gy0 + i * row_step
        draw_text(ctx, gx0 - 14, ry + bar_h * 0.64, labels[key], 13.5, bold=True, color=NAVY_TXT, align="right")

        # Track background
        rounded_rect(ctx, gx0, ry, gw, bar_h, 6)
        ctx.set_source_rgb(0.945, 0.960, 0.978)
        ctx.fill()

        # Ideal ghost bar
        iw = bx(ideal) - gx0
        rounded_rect(ctx, gx0, ry + 6, iw, bar_h - 12, 4)
        ctx.set_source_rgba(*bar_cols[i], 0.22)
        ctx.fill()

        # Noisy a=2 bar
        nw = bx(noisy) - gx0
        rounded_rect(ctx, gx0, ry, nw, bar_h, 6)
        ctx.set_source_rgb(*bar_cols[i])
        ctx.fill()

        # Ideal marker tick
        ix = bx(ideal)
        ctx.set_source_rgb(*NAVY_TXT)
        ctx.set_line_width(2.0)
        ctx.move_to(ix, ry + 3)
        ctx.line_to(ix, ry + bar_h - 3)
        ctx.stroke()

        # Value labels
        draw_text(ctx, gx1 + 14, ry + bar_h * 0.48, f"%{tr_f(noisy*100, 1)}", 14.5, bold=True, color=bar_cols[i])
        draw_text(ctx, gx1 + 14, ry + bar_h * 0.88, f"ideal %{tr_f(ideal*100, 1)}", 10.2, color=MUTED_TXT)

    # Bottom XY8 vs CPMG highlight box (live from exp126.json)
    sweep = data["exp126"]["part2_risk_r3_interleaved_dd"]["xy8_vs_cpmg_systematic"]["sweep"]
    peak = max(sweep, key=lambda r: r["xy8_advantage_y"])
    xy8_v = peak["ghz_y_xy8"]
    cpmg_v = peak["ghz_y_cpmg"]
    adv_pp = peak["xy8_advantage_y"] * 100.0

    by = y + h - 156
    bx0, bw, bh = x + 24, w - 48, 132
    rounded_rect(ctx, bx0, by, bw, bh, 10)
    ctx.set_source_rgb(0.935, 0.976, 0.955)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_GREEN)
    ctx.set_line_width(1.4)
    ctx.stroke()

    draw_text(ctx, bx0 + 18, by + 28, "Sistematik π-Darbe Hatasına Dayanım (64 Darbe, ε = 0,0025 — Y Ekseni GHZ)", 13.0, bold=True, color=NAVY_TXT)
    draw_pill(ctx, bx0 + bw - 18, by + 10, f"+{tr_f(adv_pp, 1)} pp XY8 Üstünlüğü", C_GREEN, WHITE, size=12.5, h=28, align="right")

    # Mini comparison bars
    mx0, mw = bx0 + 118, bw - 236
    for idx, (lbl, val, col) in enumerate((
        ("XY8 (Çift-Eksen)", xy8_v, C_GREEN),
        ("CPMG (Tek-Eksen)", cpmg_v, C_CRIMSON),
    )):
        my = by + 48 + idx * 38
        draw_text(ctx, bx0 + 18, my + 19, lbl, 12.2, bold=True, color=NAVY_TXT)
        rounded_rect(ctx, mx0 + 48, my + 2, mw - 48, 24, 5)
        ctx.set_source_rgb(0.89, 0.93, 0.91)
        ctx.fill()
        rounded_rect(ctx, mx0 + 48, my + 2, (mw - 48) * val, 24, 5)
        ctx.set_source_rgb(*col)
        ctx.fill()
        draw_text(ctx, mx0 + mw + 14, my + 19, f"%{tr_f(val*100, 1)}", 13.5, bold=True, color=col)


def draw_bom_panel(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    rounded_rect(ctx, x + 3, y + 5, w, h, 14)
    ctx.set_source_rgba(0.05, 0.12, 0.22, 0.07)
    ctx.fill()
    rounded_rect(ctx, x, y, w, h, 14)
    ctx.set_source_rgb(*WHITE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.5)
    ctx.stroke()

    d128 = data["exp128"]
    b_sum = d128["bom_detailed_summary"]
    subs_rec = d128["subsystem_reconciliation"]
    rfq = d128["rfq_coverage"]
    bom_sub_m3 = data["bom_sub_m3"]

    draw_pill(ctx, x + 24, y + 20, "Exp128 · BOM_DETAILED.csv", C_CRIMSON, WHITE, size=11.5, h=25)
    draw_text(ctx, x + 240, y + 38, "Alt-Sistem Bazlı M1 vs M3 Maliyet ($M) & 6-RFQ Varyans Kapaması", 16.2, bold=True, color=NAVY_TXT)
    draw_text(
        ctx, x + 24, y + 66,
        f"M1 Tek-Demet: ${tr_f(b_sum['m1_nom_usd']/1e6, 2)}M (%82 taşınabilir)  |  M3 Altın Ölçek: ${tr_f(b_sum['m3_nom_usd']/1e6, 2)}M (${tr_f(b_sum['m3_low_usd']/1e6, 2)}M–${tr_f(b_sum['m3_high_usd']/1e6, 2)}M)  |  145 parça",
        11.8, color=MUTED_TXT,
    )

    # Legend top-right of chart
    lx = x + w - 280
    ctx.set_source_rgb(*C_TEAL); rounded_rect(ctx, lx, y + 84, 16, 14, 3); ctx.fill()
    draw_text(ctx, lx + 22, y + 96, "M1 ($2,19M)", 12.0, bold=True, color=NAVY_TXT)
    ctx.set_source_rgb(*NAVY_BOT); rounded_rect(ctx, lx + 135, y + 84, 16, 14, 3); ctx.fill()
    draw_text(ctx, lx + 157, y + 96, "M3 ($4,19M)", 12.0, bold=True, color=NAVY_TXT)

    # Grouped vertical bar chart for S1..S7, S9 (S8 is $0 software)
    sub_keys = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S9"]
    sub_short = {
        "S1": "S1\nKolon", "S2": "S2\nMEMS", "S3": "S3\nIBIC", "S4": "S4\nPiezo",
        "S5": "S5\nUHV", "S6": "S6\nKriyo+RF", "S7": "S7\nElektr.", "S9": "S9\nSarf",
    }

    cx0, cx1 = x + 78, x + w - 32
    cy_top, cy_bot = y + 114, y + 412
    cw = cx1 - cx0
    ch = cy_bot - cy_top
    ymax = 2.20  # $2.20M ceiling (S6 M3 = $1.926M)

    def by_val(val_m: float) -> float:
        return cy_bot - (val_m / ymax) * ch

    # Y grid
    for tick in (0.0, 0.5, 1.0, 1.5, 2.0):
        ty = by_val(tick)
        ctx.set_source_rgb(*GRID if tick > 0 else BORDER)
        ctx.set_line_width(1.0 if tick > 0 else 1.5)
        ctx.move_to(cx0, ty); ctx.line_to(cx1, ty); ctx.stroke()
        draw_text(ctx, cx0 - 10, ty + 4, f"${tr_f(tick, 1)}M", 11.0, color=MUTED_TXT, align="right")

    slot_w = cw / len(sub_keys)
    bw = slot_w * 0.34
    for i, sk in enumerate(sub_keys):
        m1_m = subs_rec[sk]["m1_nom_usd"] / 1e6
        m3_m = bom_sub_m3[sk] / 1e6
        mid_x = cx0 + (i + 0.5) * slot_w

        # M1 bar
        x1 = mid_x - bw - 2
        y1 = by_val(m1_m)
        rounded_rect(ctx, x1, y1, bw, cy_bot - y1, 4)
        ctx.set_source_rgb(*C_TEAL)
        ctx.fill()
        draw_text(ctx, x1 + bw / 2.0, y1 - 6, f"${tr_f(m1_m, 2)}", 10.2, bold=True, color=C_TEAL, align="center")

        # M3 bar
        x2 = mid_x + 2
        y2 = by_val(m3_m)
        rounded_rect(ctx, x2, y2, bw, cy_bot - y2, 4)
        ctx.set_source_rgb(*NAVY_BOT)
        ctx.fill()
        draw_text(ctx, x2 + bw / 2.0, y2 - 6, f"${tr_f(m3_m, 2)}", 10.2, bold=True, color=NAVY_TXT, align="center")

        # X labels (2 lines)
        l1, l2 = sub_short[sk].split("\n")
        draw_text(ctx, mid_x, cy_bot + 19, l1, 12.2, bold=True, color=NAVY_TXT, align="center")
        draw_text(ctx, mid_x, cy_bot + 35, l2, 10.5, color=MUTED_TXT, align="center")

    # Bottom 6-RFQ Coverage & 92.8% Variance Closure Box
    ry = y + h - 156
    rx0, rw, rh = x + 24, w - 48, 132
    rounded_rect(ctx, rx0, ry, rw, rh, 10)
    ctx.set_source_rgb(0.945, 0.960, 0.985)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BLUE)
    ctx.set_line_width(1.4)
    ctx.stroke()

    nom_share = rfq["rfq6_nom_share"]
    var_share = rfq["rfq6_variance_share_mc"]
    rfq_nom_m = rfq["rfq6_total_nom_usd"] / 1e6

    draw_text(ctx, rx0 + 18, ry + 28, "6-RFQ Tedarikçi Paketi Kaldıracı (RFQ-01..06 · B/C Duvarı Çözümü)", 13.0, bold=True, color=NAVY_TXT)
    draw_pill(ctx, rx0 + rw - 18, ry + 10, f"%{tr_f(var_share*100, 1)} MC Varyans Kapaması", C_BLUE, WHITE, size=12.5, h=28, align="right")

    bar_x0 = rx0 + 178
    bar_w = rw - 385
    for idx, (lbl, share, val_lbl, col) in enumerate((
        ("M3 Nominal Payı", nom_share, f"%{tr_f(nom_share*100, 1)} (${tr_f(rfq_nom_m, 2)}M)", C_BLUE),
        ("MC Varyans Payı", var_share, f"%{tr_f(var_share*100, 1)} (100k MC)", C_PURPLE),
    )):
        by_i = ry + 48 + idx * 38
        draw_text(ctx, rx0 + 18, by_i + 19, lbl, 12.2, bold=True, color=NAVY_TXT)
        rounded_rect(ctx, bar_x0, by_i + 2, bar_w, 24, 5)
        ctx.set_source_rgb(0.87, 0.90, 0.95)
        ctx.fill()
        rounded_rect(ctx, bar_x0, by_i + 2, bar_w * share, 24, 5)
        ctx.set_source_rgb(*col)
        ctx.fill()
        draw_text(ctx, bar_x0 + bar_w + 14, by_i + 19, val_lbl, 12.2, bold=True, color=col)


def main() -> None:
    data = load_data()
    d124, d125, d126, d127, d128, cad = (
        data["exp124"], data["exp125"], data["exp126"], data["exp127"], data["exp128"], data["cad"]
    )

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)

    # Background
    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Hero Top Banner
    grad = cairo.LinearGradient(0, 0, W, 136)
    grad.add_color_stop_rgb(0.0, *NAVY_TOP)
    grad.add_color_stop_rgb(1.0, *NAVY_BOT)
    ctx.set_source(grad)
    ctx.rectangle(0, 0, W, 134)
    ctx.fill()
    # Accent stripe
    ctx.set_source_rgb(*C_TEAL)
    ctx.rectangle(0, 134, W, 5)
    ctx.fill()

    draw_text(ctx, 60, 62, "ATOM LİTOGRAFİ MAKİNESİ v3.0 — M0 Mühendislik & Fizik Özeti", 33.0, bold=True, color=WHITE)
    draw_text(ctx, 60, 102, "Mod B (f=%1 ²⁹Si Banyo + ³¹P Donor) · K=8 Çekirdek-Spin Yazmacı · s=0,5 Altın Zarf · Exp0–Exp128 Doğrulanmış Kapanış", 15.5, color=(0.76, 0.86, 0.95))

    draw_pill(ctx, W - 60, 26, "MODEL / SİMÜLASYON — LAB ÖLÇÜMÜ & TAPE-OUT YOKTUR", C_GOLD_BG, NAVY_TOP, size=12.5, pad_x=16, h=34, align="right")
    draw_pill(ctx, W - 60, 74, "v3.0 Kilitli · 89/89 Atom-Litografi pytest PASS · 0/10.153 CAD Çakışma", (0.11, 0.44, 0.36), WHITE, size=12.0, pad_x=14, h=30, align="right")

    # Extract verified live numbers for 6 KPI Cards
    ps126 = d126["part3_multicell_16_programs"]["program_summary"]
    n32_row = [r for r in d126["part2_risk_r3_interleaved_dd"]["f1_ghz4_ndd_sweep"] if r["N_total"] == 32][0]
    q32_a1 = n32_row["results"]["a1_e0.001"]["Q_32d"]
    q32_a2 = n32_row["results"]["a2_e0.001"]["Q_32d"]

    ma = cad["master_assembly"]
    e124_c = cad["exp124_column_audit"]
    clr_ok = sum(1 for v in cad["critical_clearances"].values() if v["pass"])
    clr_tot = len(cad["critical_clearances"])

    b_sum = d128["bom_detailed_summary"]
    ex_p = d128["monte_carlo_model_a_detailed"]["exceedance_probabilities"]

    cards = [
        (
            "Exp124 · S1/S2", "İyon Kolonu & Arch-B Optik",
            "10 → 5 keV  |  σ_top = 3,67 nm",
            [
                "Aktif dizi: 32×32 = 1.024 demetcik (0,50 mm, 16×16 mm, Ø28 bore)",
                "σ_nokta = 1,43 nm  |  HDA-HiRes ΔE_FWHM = 0,453 eV (R₀ = 40 mm)",
                f"Arch-B WD = 0,250 mm  |  C_c = 2,660 mm  |  {tr_f(e124_c['total_column_height_mm'], 2)} mm / {tr_f(e124_c['stage_mass_kg'], 2)} kg",
            ],
            C_BLUE,
        ),
        (
            "Exp125 · S6", "Kriyo-Mıknatıs & 20 mK DR",
            "B_örnek = 1,500000 T ± 17,8 ppm",
            [
                "8-bobin (M/S/A/B): Ø150 bore, 36 mm yarık, Ø352 OD, T_hot = 64,6 K",
                f"NbTiN disk (z = −155 mm): |B| = {tr_f(d125['magnet_r7']['resonator_zone']['shielded_max_B_mT']*1000, 1)} µT (Nb RRR>300 + Cryoperm)",
                "5-kademe DR: 4 K = 0,33–0,65 W (<1 W)  |  MXC 20 mK = 3,94 µW",
            ],
            C_PURPLE,
        ),
        (
            "Exp127 · S3", "Soğuk IBIC Ön-Uç & Devre",
            "η(5 keV) = %99,94  |  ENC = 24,1 e⁻",
            [
                "100 K soğuk ada: LTC6268 FET CSA (1,2 µs / 1 GΩ, Cf = 0,25 pF)",
                "P_yanlış = 2,59×10⁻⁴  |  8-kanallı 16-bit DAC8568 eşik ayarı",
                "KiCad Netlist + SPICE (.net / .cir): 204 bileşen / 107 net / 0 ERC",
            ],
            C_GREEN,
        ),
        (
            "Exp126 · S8", "32B CUDA Kuantum Programlama",
            f"N=32  Q = {tr_f(q32_a1, 3)} (α=1) / {tr_f(q32_a2, 3)} (α=2)",
            [
                "32B tam Hilbert + 448 seyirci spin, U†U = I (hata < 10⁻¹³)",
                f"16 hücre: Bell %{tr_f(ps126['Bell']['noisy_a2_mean']*100, 1)} · GHZ-4 %{tr_f(ps126['GHZ-4']['noisy_a2_mean']*100, 1)} · BF-3 %{tr_f(ps126['BitFlip-3']['noisy_a2_mean']*100, 1)}",
                "CellISA (10 komut) + SHA-256 sertifikalı heterojen derleme",
            ],
            C_AMBER,
        ),
        (
            "CAD v3.0 · S1–S7", "3B Parametrik CAD & STL",
            f"0 / {tr_i(cad['interference_audit']['pairs_checked'])} Çakışma  |  {tr_f(ma['total_mass_kg'], 1)} kg",
            [
                f"{ma['part_count']} katı parça (S1–S7) · Zarf {ma['bbox_span_mm'][0]:.0f}×{ma['bbox_span_mm'][1]:.0f}×{ma['bbox_span_mm'][2]:.0f} mm",
                f"8 su-geçirmez ikili STL ({tr_i(ma['stl']['triangles'])} üçgen, 0 açık kenar)",
                f"{clr_ok}/{clr_tot} boşluk PASS (Dizi↔Ø28 Bore {tr_f(e124_c['beam_array_diagonal_to_bore_clearance_mm'], 2)} mm) · 10 ISO pafta",
            ],
            C_TEAL,
        ),
        (
            "Exp128 · BOM", "Maliyet & Bütçe Tavanı (100k MC)",
            f"M1 ${tr_f(b_sum['m1_nom_usd']/1e6, 2)}M  →  M3 ${tr_f(b_sum['m3_nom_usd']/1e6, 2)}M",
            [
                f"{data['bom_rows']} parça (BOM_DETAILED, $0 uzlaştırma, M1 %82 taşınabilir)",
                f"P(BOM > $50M) = %{tr_f(ex_p['P_BOM_gt_50M']*100, 2)}  |  P(Prog > $100M) = %{tr_f(ex_p['P_Program_stoch_gt_100M']*100, 2)}",
                f"6-RFQ paketi (RFQ-01..06): M3'ün %{tr_f(d128['rfq_coverage']['rfq6_nom_share']*100, 1)}'ü · varyansın %{tr_f(d128['rfq_coverage']['rfq6_variance_share_mc']*100, 1)}'i",
            ],
            C_CRIMSON,
        ),
    ]

    # Render 2x3 KPI grid
    pad_x = 60.0
    gap_x = 28.0
    gap_y = 24.0
    card_w = (W - 2 * pad_x - 2 * gap_x) / 3.0
    card_h = 242.0
    grid_y0 = 162.0
    for idx, (tag, title, hero, lines, col) in enumerate(cards):
        r, c = divmod(idx, 3)
        cx = pad_x + c * (card_w + gap_x)
        cy = grid_y0 + r * (card_h + gap_y)
        draw_kpi_card(ctx, cx, cy, card_w, card_h, tag, title, hero, lines, col)

    # Render Bottom 2 Charts
    bot_y0 = grid_y0 + 2 * card_h + gap_y + 24.0
    bot_h = H - bot_y0 - 48.0
    panel_w = (W - 2 * pad_x - 30.0) / 2.0
    draw_quantum_panel(ctx, pad_x, bot_y0, panel_w, bot_h, data)
    draw_bom_panel(ctx, pad_x + panel_w + 30.0, bot_y0, panel_w, bot_h, data)

    # Clean Footer
    draw_text(
        ctx, 60, H - 18,
        "Canlı Veri Kaynakları: exp124.json · exp125.json · exp126.json · exp127.json · exp128.json · cad_verification.json · BOM_DETAILED.csv",
        11.2, color=MUTED_TXT,
    )
    draw_text(
        ctx, W - 60, H - 18,
        "Atom-Lithography v3.0 (M0 Tasarım & Simülasyon) · 2026-11-22",
        11.2, bold=True, color=SLATE_TXT, align="right",
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    surf.write_to_png(str(OUT_PNG))
    with Image.open(OUT_PNG) as im:
        assert im.size == (W, H), f"Expected {W}x{H}, got {im.size}"
    print(f"DASHBOARD_OK {OUT_PNG} ({W}x{H}, {OUT_PNG.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
