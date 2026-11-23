"""Generate GitHub README v4.0 hero cover dashboard `00_v4_overview_dashboard.png` (2400x1400).

Reads verified live metrics directly from:
  - results/exp124_ion_column_optics/exp124.json
  - results/exp125_cryo_magnet_readout/exp125.json
  - results/exp126_atom_cell_programming/exp126.json
  - results/exp127_detector_frontend_sim/exp127.json
  - results/exp128_bom_sensitivity/exp128.json
  - results/exp129_valley_orbital_hyperfine/exp129.json
  - results/exp130_flash_anneal_diffusion/exp130.json
  - results/exp131_scalable_m4_architecture/exp131.json
  - results/exp132_bayesian_spectroscopy_cellisa3/exp132.json
  - results/exp133_coupled_vibration_thermal/exp133.json
  - results/exp134_fab_economics_tco/exp134.json
  - results/exp135_v4_digital_twin/exp135.json
  - research/atom_lithography_machine/cad/cad_verification.json
  - research/atom_lithography_machine/BOM_DETAILED.csv

Runs under `/usr/bin/python3 -B` (PyCairo + Pillow, zero numpy/matplotlib).
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
OUT_PNG = CAD_DIR / "drawings" / "00_v4_overview_dashboard.png"
W, H = 2400, 1400

# Palette — Executive Dark-Navy / Crisp White Technical Dashboard
BG = (0.955, 0.967, 0.982)
WHITE = (1.0, 1.0, 1.0)
NAVY_TOP = (0.047, 0.106, 0.196)
NAVY_BOT = (0.094, 0.196, 0.322)
NAVY_TXT = (0.075, 0.145, 0.235)
SLATE_TXT = (0.26, 0.33, 0.42)
MUTED_TXT = (0.45, 0.52, 0.60)
BORDER = (0.82, 0.86, 0.91)
GRID = (0.90, 0.93, 0.96)

C_BLUE = (0.11, 0.44, 0.74)
C_PURPLE = (0.44, 0.27, 0.71)
C_GREEN = (0.08, 0.55, 0.37)
C_AMBER = (0.84, 0.50, 0.06)
C_TEAL = (0.06, 0.54, 0.60)
C_CRIMSON = (0.74, 0.17, 0.23)
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
    def rj(rel: str) -> dict:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    bom_rows = 0
    bom_m3_sum = 0.0
    with open(ROOT / "research/atom_lithography_machine/BOM_DETAILED.csv", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            bom_rows += 1
            bom_m3_sum += float(row["usd_nom"])

    return {
        "exp124": rj("results/exp124_ion_column_optics/exp124.json"),
        "exp125": rj("results/exp125_cryo_magnet_readout/exp125.json"),
        "exp126": rj("results/exp126_atom_cell_programming/exp126.json"),
        "exp127": rj("results/exp127_detector_frontend_sim/exp127.json"),
        "exp128": rj("results/exp128_bom_sensitivity/exp128.json"),
        "exp129": rj("results/exp129_valley_orbital_hyperfine/exp129.json"),
        "exp130": rj("results/exp130_flash_anneal_diffusion/exp130.json"),
        "exp131": rj("results/exp131_scalable_m4_architecture/exp131.json"),
        "exp132": rj("results/exp132_bayesian_spectroscopy_cellisa3/exp132.json"),
        "exp133": rj("results/exp133_coupled_vibration_thermal/exp133.json"),
        "exp134": rj("results/exp134_fab_economics_tco/exp134.json"),
        "exp135": rj("results/exp135_v4_digital_twin/exp135.json"),
        "cad": json.loads((CAD_DIR / "cad_verification.json").read_text(encoding="utf-8")),
        "bom_rows": bom_rows,
        "bom_m3_sum": bom_m3_sum,
    }


def draw_kpi_card(
    ctx: cairo.Context, x: float, y: float, w: float, h: float,
    tag: str, title: str, hero: str, lines: list[str], accent,
) -> None:
    rounded_rect(ctx, x + 3, y + 5, w, h, 14)
    ctx.set_source_rgba(0.05, 0.12, 0.22, 0.07)
    ctx.fill()

    rounded_rect(ctx, x, y, w, h, 14)
    ctx.set_source_rgb(*WHITE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.4)
    ctx.stroke()

    ctx.save()
    rounded_rect(ctx, x, y, w, h, 14)
    ctx.clip()
    ctx.set_source_rgb(*accent)
    ctx.rectangle(x, y, 8, h)
    ctx.fill()
    ctx.restore()

    pw = draw_pill(ctx, x + 24, y + 17, tag, accent, WHITE, size=11.0, pad_x=10, h=24)
    # Auto-fit title if needed
    t_sz = 15.6
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(t_sz)
    avail_tw = w - (24 + pw + 12) - 18
    while ctx.text_extents(title).width > avail_tw and t_sz > 11.5:
        t_sz -= 0.4
        ctx.set_font_size(t_sz)
    draw_text(ctx, x + 24 + pw + 11, y + 35, title, t_sz, bold=True, color=NAVY_TXT)

    # Auto-fit hero text
    h_sz = 23.5
    ctx.set_font_size(h_sz)
    while ctx.text_extents(hero).width > (w - 46) and h_sz > 17.0:
        h_sz -= 0.5
        ctx.set_font_size(h_sz)
    draw_text(ctx, x + 24, y + 83, hero, h_sz, bold=True, color=accent)

    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.2)
    ctx.move_to(x + 24, y + 98)
    ctx.line_to(x + w - 22, y + 98)
    ctx.stroke()

    ly = y + 127
    for ln in lines:
        ctx.set_source_rgb(*accent)
        ctx.arc(x + 30, ly - 5, 3.2, 0, 2 * math.pi)
        ctx.fill()
        l_sz = 12.6
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(l_sz)
        while ctx.text_extents(ln).width > (w - 60) and l_sz > 10.5:
            l_sz -= 0.3
            ctx.set_font_size(l_sz)
        draw_text(ctx, x + 42, ly, ln, l_sz, color=SLATE_TXT)
        ly += 33


# ---------------------------------------------------------------------------
# Bottom Left Panel: v3.0 vs v4.0 Speedup, Unit Cost & VOKL-6 R1 Resilience
# ---------------------------------------------------------------------------
def draw_left_speedup_cost_panel(
    ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict
) -> None:
    rounded_rect(ctx, x + 3, y + 5, w, h, 14)
    ctx.set_source_rgba(0.05, 0.12, 0.22, 0.07)
    ctx.fill()
    rounded_rect(ctx, x, y, w, h, 14)
    ctx.set_source_rgb(*WHITE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.5)
    ctx.stroke()

    d135 = data["exp135"]
    sc = d135["layer7_unit_economics"]["scenarios"]
    red_pct = d135["layer7_unit_economics"]["unit_cost_reduction_pct"]
    l4 = d135["layer4_boed_throughput"]["regimes"]

    pw_p = draw_pill(ctx, x + 24, y + 18, "Exp129+132+135", C_GREEN, WHITE, size=11.0, h=24)
    draw_text(ctx, x + 24 + pw_p + 12, y + 36, "v3.0 vs v4.0 Hızlanma, Birim Maliyet (µUSD/reg) & VOKL-6 R1", 16.0, bold=True, color=NAVY_TXT)
    draw_text(
        ctx, x + 24, y + 63,
        "Sol çubuk: Günlük sertifikalı yazmaç (10⁹/gün, yazma tavanı)  |  Sağ çubuk: 5-yıllık Fab TCO birim maliyeti (µUSD/reg, düşük=iyi)",
        11.6, color=MUTED_TXT,
    )

    # 4 Scenarios compared side-by-side in clean horizontal twin tracks
    rows = [
        (
            "v3.0 Baz (KL %51, 15 ms)",
            sc["v300_KL_15ms"]["reg_per_day"] / 1e9,
            sc["v300_KL_15ms"]["uUSD_per_register"],
            "1,0× baz",
            MUTED_TXT,
            C_CRIMSON,
        ),
        (
            "v4.0 VOKL-6 R1 (%33,3, 15 ms)",
            sc["v400_VOKL6_HM5962_15ms"]["reg_per_day"] / 1e9,
            sc["v400_VOKL6_HM5962_15ms"]["uUSD_per_register"],
            f"-{tr_f(red_pct['v4_HM5962_15ms_vs_v3_KL'], 1)}%",
            C_AMBER,
            C_AMBER,
        ),
        (
            "v4.0 Kanonik (KL %51, 15 ms)",
            sc["v400_KL_15ms"]["reg_per_day"] / 1e9,
            sc["v400_KL_15ms"]["uUSD_per_register"],
            f"-{tr_f(red_pct['v4_KL_15ms_vs_v3_KL'], 1)}%",
            C_BLUE,
            C_BLUE,
        ),
        (
            "v4.0 Hızlı Atış (KL %51, 10 ms)",
            sc["v400_KL_10ms"]["reg_per_day"] / 1e9,
            sc["v400_KL_10ms"]["uUSD_per_register"],
            f"-{tr_f(red_pct['v4_KL_10ms_vs_v3_KL'], 1)}%",
            C_GREEN,
            C_GREEN,
        ),
    ]

    # Two sub-charts side-by-side inside the left card
    lbl_w = 238.0
    sub1_x = x + lbl_w + 10.0
    sub1_w = 345.0
    sub2_x = sub1_x + sub1_w + 88.0
    sub2_w = (x + w - 95.0) - sub2_x
    gy0 = y + 108.0
    row_step = 74.0
    bar_h = 34.0

    # Column sub-headers
    draw_text(ctx, sub1_x + sub1_w / 2.0, gy0 - 16, "Üretim Kapasitesi [10⁹ reg / gün]", 12.2, bold=True, color=NAVY_TXT, align="center")
    draw_text(ctx, sub2_x + sub2_w / 2.0, gy0 - 16, "Makine Birim Maliyeti [µUSD / reg]", 12.2, bold=True, color=NAVY_TXT, align="center")

    # Grid lines sub-chart 1 (0 .. 2.5e9)
    max_reg = 2.50
    for tk in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5):
        tx = sub1_x + (tk / max_reg) * sub1_w
        ctx.set_source_rgb(*GRID if tk > 0 else BORDER)
        ctx.set_line_width(1.0 if tk > 0 else 1.4)
        ctx.move_to(tx, gy0 - 6)
        ctx.line_to(tx, gy0 + len(rows) * row_step - 24)
        ctx.stroke()
        draw_text(ctx, tx, gy0 + len(rows) * row_step - 6, tr_f(tk, 1), 10.6, color=MUTED_TXT, align="center")

    # Grid lines sub-chart 2 (0 .. 60 uUSD/reg)
    max_cost = 60.0
    for tk in (0.0, 15.0, 30.0, 45.0, 60.0):
        tx = sub2_x + (tk / max_cost) * sub2_w
        ctx.set_source_rgb(*GRID if tk > 0 else BORDER)
        ctx.set_line_width(1.0 if tk > 0 else 1.4)
        ctx.move_to(tx, gy0 - 6)
        ctx.line_to(tx, gy0 + len(rows) * row_step - 24)
        ctx.stroke()
        draw_text(ctx, tx, gy0 + len(rows) * row_step - 6, f"${tk:.0f}", 10.6, color=MUTED_TXT, align="center")

    for i, (rlbl, reg_b, cost_u, delta_s, col_r, col_c) in enumerate(rows):
        ry = gy0 + i * row_step
        draw_text(ctx, sub1_x - 14, ry + bar_h * 0.65, rlbl, 12.2, bold=True, color=NAVY_TXT, align="right")

        # Track 1 (throughput)
        rounded_rect(ctx, sub1_x, ry, sub1_w, bar_h, 6)
        ctx.set_source_rgb(0.945, 0.960, 0.978)
        ctx.fill()
        bw1 = max(8.0, (reg_b / max_reg) * sub1_w)
        rounded_rect(ctx, sub1_x, ry, bw1, bar_h, 6)
        ctx.set_source_rgb(*col_r)
        ctx.fill()
        draw_text(ctx, sub1_x + bw1 + 8, ry + bar_h * 0.65, f"{tr_f(reg_b, 2)}G", 12.0, bold=True, mono=True, color=col_r)

        # Track 2 (unit cost)
        rounded_rect(ctx, sub2_x, ry, sub2_w, bar_h, 6)
        ctx.set_source_rgb(0.945, 0.960, 0.978)
        ctx.fill()
        bw2 = max(8.0, (cost_u / max_cost) * sub2_w)
        rounded_rect(ctx, sub2_x, ry, bw2, bar_h, 6)
        ctx.set_source_rgb(*col_c)
        ctx.fill()
        draw_text(ctx, sub2_x + bw2 + 8, ry + bar_h * 0.45, f"${tr_f(cost_u, 2)}", 12.0, bold=True, mono=True, color=col_c)
        draw_text(ctx, sub2_x + bw2 + 8, ry + bar_h * 0.88, delta_s, 10.5, bold=True, color=col_c)

    # Bottom Risk R1 (Exp129 VOKL-6) honest resilience callout box
    by = y + h - 148.0
    bx0, bw_box, bh_box = x + 24, w - 48, 126
    rounded_rect(ctx, bx0, by, bw_box, bh_box, 10)
    ctx.set_source_rgb(0.992, 0.962, 0.920)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_AMBER)
    ctx.set_line_width(1.4)
    ctx.stroke()

    r1_kl = l4["KL_canonical_f1"]
    r1_hm = l4["VOKL6_HM5962_f1"]
    r1_nw = l4["VOKL6_norm_f1_worst"]
    draw_text(ctx, bx0 + 18, by + 26, "Risk R1 (Exp129 VOKL-6) Aşağı-Yönlü Verim Zarfında BOED Dayanıklılığı (Dürüst Kayıt)", 12.8, bold=True, color=NAVY_TXT)
    draw_pill(ctx, bx0 + bw_box - 16, by + 8, "Tüm Rejimlerde Yazma-Sınırlı (7,6× / 11,4×)", C_GREEN, WHITE, size=11.5, h=25, align="right")

    u_kl15 = tr_f(sc["v400_KL_15ms"]["uUSD_per_register"], 2)
    u_hm15 = tr_f(sc["v400_VOKL6_HM5962_15ms"]["uUSD_per_register"], 2)
    u_nw15 = tr_f(sc["v400_VOKL6_norm_15ms"]["uUSD_per_register"], 1)
    d17_kl = tr_f(sc["v400_KL_15ms"]["usd_per_d17_logical_1overpB"], 4)
    notes_r1 = [
        f"• Kanonik KL (f=%1, p_B=%51,0): t_BOED = {tr_f(r1_kl['boed_t_spec_factory_ms'],1)} ms → {tr_f(r1_kl['v400_net_15ms_per_day']/1e9,2)}G/gün (${u_kl15} µUSD/reg; d=17 mantıksal ${d17_kl}).",
        f"• VOKL-6 HM5962 (f=%1, p_B=%33,3): Erken iptal t_BOED'yi {tr_f(r1_hm['boed_t_spec_factory_ms'],1)} ms'ye kısaltır → {tr_f(r1_hm['v400_net_15ms_per_day']/1e9,2)}G/gün (v3 bazının 5,0× üstü, ${u_hm15} µUSD).",
        f"• En-Kötü VOKL-6 norm (p_B=%4,75): t_BOED = {tr_f(r1_nw['boed_t_spec_factory_ms'],1)} ms, 0,14G/gün (${u_nw15} µUSD) — M1 ENDOR go/no-go kapısı & f=%2 izotop kaldıracı (%54,5) zorunlu!",
    ]
    for idx_n, ln in enumerate(notes_r1):
        draw_text(ctx, bx0 + 18, by + 54 + idx_n * 24, ln, 11.4, color=SLATE_TXT)


# ---------------------------------------------------------------------------
# Bottom Right Panel: M4 2D Surface-Code Percolation & 16-Cell Quantum Fidelity
# ---------------------------------------------------------------------------
def draw_right_percolation_quantum_panel(
    ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict
) -> None:
    rounded_rect(ctx, x + 3, y + 5, w, h, 14)
    ctx.set_source_rgba(0.05, 0.12, 0.22, 0.07)
    ctx.fill()
    rounded_rect(ctx, x, y, w, h, 14)
    ctx.set_source_rgb(*WHITE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.5)
    ctx.stroke()

    d135 = data["exp135"]
    l6 = d135["layer6_m4_percolation_collision"]["regimes"]
    l5 = d135["layer5_quantum_and_bus"]

    pw_p = draw_pill(ctx, x + 24, y + 18, "Exp126+131+135", C_PURPLE, WHITE, size=11.0, h=24)
    draw_text(ctx, x + 24 + pw_p + 12, y + 36, "M4 2B Yüzey Kodu Perkolasyonu (L=11 FT) & 16-Hücre Kuantum", 16.0, bold=True, color=NAVY_TXT)
    draw_text(
        ctx, x + 24, y + 63,
        "Üst: 121 düğüm (≤%5 ölü) FT yonga verimi Y_FT(N_cand) · Δz_cap*=8 nm (%95,2)  |  Alt: Exp126 32B & Exp131 3 kΩ NbTiN sadakatleri",
        11.5, color=MUTED_TXT,
    )

    # Top plot: Percolation curves Y_FT_5pct_exact vs N_cand (1..14)
    px0, px1 = x + 78, x + w - 34
    py0, py1 = y + 96, y + 356
    pw_g = px1 - px0
    ph_g = py1 - py0

    def mx(nc: float) -> float:
        return px0 + (nc - 1.0) / 13.0 * pw_g

    def my(yv: float) -> float:
        return py1 - yv * ph_g

    # Grid lines
    for yv in (0.0, 0.25, 0.50, 0.75, 0.99, 1.00):
        gy = my(yv)
        is_99 = abs(yv - 0.99) < 1e-6
        ctx.save()
        if is_99:
            ctx.set_dash([7.0, 4.0])
            ctx.set_source_rgb(*C_GREEN)
            ctx.set_line_width(1.8)
        else:
            ctx.set_source_rgb(*GRID if yv > 0 else BORDER)
            ctx.set_line_width(1.0 if yv > 0 else 1.4)
        ctx.move_to(px0, gy); ctx.line_to(px1, gy); ctx.stroke()
        ctx.restore()
        if not is_99:
            draw_text(ctx, px0 - 10, gy + 4, f"%{yv*100:.0f}", 10.8, color=MUTED_TXT, align="right")
    draw_text(ctx, px0 + 8, my(0.99) + 15, "%99 FT Eşiği", 10.6, bold=True, color=C_GREEN)

    for nc in range(1, 15):
        gx = mx(nc)
        ctx.set_source_rgb(*GRID)
        ctx.set_line_width(0.8)
        ctx.move_to(gx, py0); ctx.line_to(gx, py1); ctx.stroke()
        draw_text(ctx, gx, py1 + 17, str(nc), 10.8, bold=(nc in (6, 11)), color=(NAVY_TXT if nc in (6, 11) else MUTED_TXT), align="center")
    draw_text(ctx, px0 + pw_g / 2.0, py1 + 36, "Düğüm Başına Aday Yuva Sayısı N_cand", 11.8, bold=True, color=NAVY_TXT, align="center")

    curves = [
        ("VOKL6_HM5962_f2_lever", "VOKL-6 f=%2,0 (p_B=%54,5) → N*=6", C_TEAL, [8.0, 4.0]),
        ("KL_canonical_f1",       "Kanonik KL f=%1,0 (p_B=%51,0) → N*=6", C_BLUE, None),
        ("VOKL6_HM5962_f1",       "VOKL-6 R1 f=%1,0 (p_B=%33,3) → N*=11", C_CRIMSON, None),
    ]
    for rkey, _, col, dash in curves:
        pts = l6[rkey]["L11_sweep"]
        ctx.save()
        if dash:
            ctx.set_dash(dash)
        ctx.set_source_rgb(*col)
        ctx.set_line_width(3.0)
        for j, pt in enumerate(pts):
            cx_p, cy_p = mx(pt["N_cand"]), my(pt["Y_FT_5pct_exact"])
            if j == 0:
                ctx.move_to(cx_p, cy_p)
            else:
                ctx.line_to(cx_p, cy_p)
        ctx.stroke()
        ctx.restore()
        # Dots
        for pt in pts:
            cx_p, cy_p = mx(pt["N_cand"]), my(pt["Y_FT_5pct_exact"])
            ctx.set_source_rgb(*col)
            ctx.arc(cx_p, cy_p, 4.0, 0, 2 * math.pi)
            ctx.fill()

    # Crisp annotations at N*=6 (KL) and N*=11 (VOKL-6 R1) — placed strictly in clear whitespace
    x6, y6_kl = mx(6), my(l6["KL_canonical_f1"]["L11_Y_FT_at_Ncand6"])
    ctx.set_source_rgb(*C_BLUE); ctx.arc(x6, y6_kl, 6.5, 0, 2 * math.pi); ctx.fill()
    draw_pill(ctx, mx(2.7), y6_kl + 34, "KL & f=%2: N*=6 (%99,2–99,9)", C_BLUE, WHITE, size=10.8, pad_x=10, h=23, align="center")

    x11, y11_v = mx(11), my(l6["VOKL6_HM5962_f1"]["L11_Y_FT_at_Ncand11"])
    ctx.set_source_rgb(*C_CRIMSON); ctx.arc(x11, y11_v, 6.5, 0, 2 * math.pi); ctx.fill()
    draw_pill(ctx, mx(11.8), y11_v + 24, "VOKL-6 R1: N*=11 (%99,7)", C_CRIMSON, WHITE, size=10.8, pad_x=10, h=23, align="center")

    x6_v, y6_v = mx(6), my(l6["VOKL6_HM5962_f1"]["L11_Y_FT_at_Ncand6"])
    draw_text(ctx, x6_v + 18, y6_v - 3, "N=6'da %3,1", 10.6, bold=True, color=C_CRIMSON)

    # Legend inside bottom-right empty area of percolation chart
    lgx, lgy = px0 + pw_g - 320, py1 - 86
    rounded_rect(ctx, lgx, lgy, 310, 76, 7)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.94)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER); ctx.set_line_width(1.1); ctx.stroke()
    for j, (_, clbl, ccol, cdash) in enumerate(curves):
        ly_i = lgy + 18 + j * 21
        ctx.save()
        if cdash:
            ctx.set_dash(cdash)
        ctx.set_source_rgb(*ccol); ctx.set_line_width(2.8)
        ctx.move_to(lgx + 12, ly_i - 4); ctx.line_to(lgx + 36, ly_i - 4); ctx.stroke()
        ctx.restore()
        draw_text(ctx, lgx + 44, ly_i, clbl, 10.5, bold=True, color=NAVY_TXT)

    # Bottom Quantum Fidelity & M4 Bus Summary Box
    qby = y + h - 178.0
    qbx, qbw, qbh = x + 24, w - 48, 156
    rounded_rect(ctx, qbx, qby, qbw, qbh, 10)
    ctx.set_source_rgb(0.950, 0.945, 0.988)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_PURPLE); ctx.set_line_width(1.4); ctx.stroke()

    e126_s = l5["exp126_32d_448spec"]
    e131_b = l5["exp131_m4_cavity_bus"]
    live_f = d135["layer8_live_integration"]["wafer_4x4_live"]["multicell_cert"]["joint_state_fidelity"]

    draw_text(ctx, qbx + 18, qby + 26, "16-Hücre 32B Kuantum Programlama (Exp126) & M4 Kavite-QED Veri Yolu (Exp131)", 12.6, bold=True, color=NAVY_TXT)
    draw_pill(ctx, qbx + qbw - 16, qby + 8, f"4×4 Canlı CellISA v3.0: F={tr_f(live_f*100,1)}%", C_PURPLE, WHITE, size=11.0, h=24, align="right")

    # 5 crisp horizontal mini-bars in 2 columns inside bottom box
    q_items = [
        ("Bell (16 hücre, α=2)", e126_s["16cell_bell_mean_a2"], C_TEAL),
        ("GHZ-4 (16 hücre, α=2)", e126_s["16cell_ghz4_mean_a2"], C_BLUE),
        ("BitFlip-3 (16 hücre)", e126_s["16cell_bitflip3_mean_a2"], C_PURPLE),
        ("M4 3 kΩ NbTiN (Bell)", e131_b["nbtin_3kohm_mean_F_bell"], C_GREEN),
        ("50 Ω CPW (Kıyas)", e131_b["cpw_50ohm_mean_F_bell"], C_CRIMSON),
        ("32B XY8 N=32 (α=2)", e126_s["N32_sweetspot_Q32D_alpha2"], C_AMBER),
    ]
    col_w = (qbw - 56) / 2.0
    for idx_q, (qlbl, qval, qcol) in enumerate(q_items):
        col_i = idx_q // 3
        row_i = idx_q % 3
        qx = qbx + 18 + col_i * (col_w + 20)
        qy = qby + 48 + row_i * 34
        draw_text(ctx, qx, qy + 15, qlbl, 11.2, bold=True, color=NAVY_TXT)
        bx_q = qx + 172
        bw_q = col_w - 234
        rounded_rect(ctx, bx_q, qy + 2, bw_q, 18, 4)
        ctx.set_source_rgb(0.88, 0.89, 0.94)
        ctx.fill()
        frac = max(0.0, min(1.0, (qval - 0.60) / 0.40))
        rounded_rect(ctx, bx_q, qy + 2, bw_q * frac, 18, 4)
        ctx.set_source_rgb(*qcol)
        ctx.fill()
        draw_text(ctx, bx_q + bw_q + 8, qy + 15, f"%{tr_f(qval*100, 1)}", 11.6, bold=True, mono=True, color=qcol)


def main() -> None:
    data = load_data()
    d125 = data["exp125"]
    d126 = data["exp126"]
    d128 = data["exp128"]
    d135 = data["exp135"]
    cad = data["cad"]

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)

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
    ctx.set_source_rgb(*C_TEAL)
    ctx.rectangle(0, 134, W, 5)
    ctx.fill()

    draw_text(ctx, 60, 60, "ATOM LİTOGRAFİ MAKİNESİ v4.0 — M0 Fizik, M4 Ölçekleme & Dijital İkiz Özeti", 31.0, bold=True, color=WHITE)
    draw_text(
        ctx, 60, 100,
        "Mod B (²⁹Si Banyo + ³¹P Donor, K=8) · s=0,5 Altın Zarf · BOED + S5.5 Flaş + PT420 Ayrıştırma + M4 3 kΩ NbTiN · Exp0–Exp135",
        15.0, color=(0.76, 0.86, 0.95),
    )

    draw_pill(ctx, W - 60, 24, "MODEL / SİMÜLASYON — LAB ÖLÇÜMÜ & TAPE-OUT YOKTUR", C_GOLD_BG, NAVY_TOP, size=12.2, pad_x=15, h=33, align="right")
    clr_ok = sum(1 for v in cad["critical_clearances"].values() if v["pass"])
    clr_tot = len(cad["critical_clearances"])
    draw_pill(
        ctx, W - 60, 72,
        f"v4.0 Dijital İkiz (7/7 DT PASS) · 0/{tr_i(cad['interference_audit']['pairs_checked'])} Çakışma · {clr_ok}/{clr_tot} Boşluk",
        (0.10, 0.45, 0.36), WHITE, size=11.8, pad_x=14, h=29, align="right",
    )

    # Live KPI values from JSONs & BOM_DETAILED.csv
    l1 = d135["layer1_placement_budget"]
    l2 = d135["layer2_write_activation"]
    l4_cls = d135["layer4_boed_throughput"]["exp132_class_times_ms"]
    l4_kl = d135["layer4_boed_throughput"]["regimes"]["KL_canonical_f1"]
    l5_q = d135["layer5_quantum_and_bus"]["exp126_32d_448spec"]
    l5_b = d135["layer5_quantum_and_bus"]["exp131_m4_cavity_bus"]
    l7 = d135["layer7_unit_economics"]
    ma = cad["master_assembly"]
    b_sum = d128["bom_detailed_summary"]
    ex_p = d128["monte_carlo_model_a_detailed"]["exceedance_probabilities"]
    rfq7_var = d128["rfq_coverage"]["rfq7_variance_share_mc"] * 100.0
    b_res_uT = d125["magnet_r7"]["resonator_zone"]["shielded_max_B_mT"] * 1000.0

    cards = [
        (
            "Exp124+130+133", "Yerleştirme & Flaş-Tavlama",
            f"σ_tot = {tr_f(l1['v400_coupled_10ms_nm'],2)}–{tr_f(l1['v400_coupled_15ms_nm'],2)} nm",
            [
                f"808 nm/1 ms flaş (1440 K): f_act = %{tr_f(l2['f_act_bulk']*100,2)} · σ_ann = {tr_f(l1['components_v4_nm']['sigma_anneal_808nm_1ms'],3)} nm",
                f"PT420 ayrık (VC-E): σ_stage = {tr_f(l1['components_v4_nm']['sigma_stage_CFG4_VCE'],3)} nm · σ_ptg = {tr_f(l1['components_v4_nm']['sigma_pointing_CFG4_VCE'],3)} nm",
                f"Zerodur+Invar+20 mK: σ_th = {tr_f(l1['components_v4_nm']['sigma_thermal_Zerodur_Invar'],3)} nm · Rijit CFG1: {tr_i(int(round(l1['rigid_CFG1_15ms_nm'])))} nm",
            ],
            C_BLUE,
        ),
        (
            "Exp125+127", "Kriyo-Mıknatıs & 100 K IBIC",
            f"1,500000 T ± 17,8 ppm  |  {tr_f(b_res_uT,1)} µT",
            [
                f"8-bobin (Ø150 bore, 36 mm yarık, Ø352 OD) · Nb + Cryoperm kalkan",
                f"100 K LTC6268 IBIC: η = %{tr_f(l2['eta_ibic']*100,2)} · ENC = {tr_f(l2['ibic_enc_e'],1)} e⁻ · birleşik %{tr_f(l2['combined_implant_activation_survival']*100,2)}",
                "5-kademe DR: 4 K = 0,33–0,65 W (<1 W) · MXC 20 mK = 3,94 µW",
            ],
            C_PURPLE,
        ),
        (
            "Exp132+135", "BOED Spektroskopi Hızlanması",
            f"{tr_f(l4_kl['realized_speedup_15ms_vs_same_v3'],1)}×–{tr_f(l4_kl['realized_speedup_10ms_vs_same_v3'],1)}× Hız ($0 Ek HW)",
            [
                f"BOED tarama: 1.000 ms → {tr_f(l4_cls['exp132_N2000_mean'],1)} ms (24,4× ham okuma hızı)",
                f"Yazma tavanı: {tr_f(l4_kl['v400_net_15ms_per_day']/1e9,2)}G (15 ms) / {tr_f(l4_kl['v400_net_10ms_per_day']/1e9,2)}G reg/gün (10 ms)",
                f"RMS = {tr_f(l4_cls['rms_freq_error_Hz'],1)} Hz (2,75× keskin) · FNR %{tr_f(l4_cls['fnr']*100,2)} · FPR %0,00",
            ],
            C_GREEN,
        ),
        (
            "Exp126+131", "32B Kuantum & M4 Veri Yolu",
            f"Q_32D = {tr_f(l5_q['N32_sweetspot_Q32D_alpha2'],3)}  |  F_Bell = {tr_f(l5_b['nbtin_3kohm_mean_F_bell'],3)}",
            [
                f"16 hücre (448 seyirci): Bell %{tr_f(l5_q['16cell_bell_mean_a2']*100,1)} · GHZ-4 %{tr_f(l5_q['16cell_ghz4_mean_a2']*100,1)} · BF-3 %{tr_f(l5_q['16cell_bitflip3_mean_a2']*100,1)}",
                f"M4 3 kΩ NbTiN (L_res=300 µm, B=0,1785 T): {tr_f(l5_b['nbtin_3kohm_mean_F_bell'],3)} vs 50 Ω {tr_f(l5_b['cpw_50ohm_mean_F_bell'],3)}",
                f"Δz_cap* = {l5_b['optimal_capping_nm']:.0f}±1 nm ²⁸Si (%{tr_f(l5_b['p_flipflop_C_ge_100']*100,1)} verim) · 4K 968-kapı anahtar",
            ],
            C_AMBER,
        ),
        (
            "CAD v4.0", "3B Parametrik CAD & STL",
            f"{ma['part_count']} Parça  |  {tr_f(ma['total_mass_kg'],1)} kg",
            [
                f"8 su-geçirmez STL ({tr_i(ma['stl']['triangles'])} üçgen) · 0/{tr_i(cad['interference_audit']['pairs_checked'])} çakışma",
                f"{clr_ok}/{clr_tot} boşluk PASS · S5.5 flaş + 4K M4 kart + PT420 ayrık paket",
                "CF63 körük (2 kN/m) + 4× OFHC örgü (52,7 N/m) + 500 mm uzak valf",
            ],
            C_TEAL,
        ),
        (
            "Exp128+134", "BOM v4.0, TCO & Birim Maliyet",
            f"M3 ${tr_f(b_sum['m3_nom_usd']/1e6,2)}M  |  -%{tr_f(l7['unit_cost_reduction_pct']['v4_KL_15ms_vs_v3_KL'],1)} / reg",
            [
                f"{data['bom_rows']} parça (M1 ${tr_f(b_sum['m1_nom_usd']/1e6,2)}M, v4 +$420k) · 7-RFQ varyansın %{tr_f(rfq7_var,1)}'sı",
                f"P(BOM > $50M) = %{tr_f(ex_p['P_BOM_gt_50M']*100,3)} · P(Prog > $100M) = %{tr_f(ex_p['P_Program_stoch_gt_100M']*100,2)} (<%5)",
                f"5y TCO ${tr_f(l7['tco_5yr_p50_usd']['v4_fab_n1']/1e6,2)}M: $52,88 → ${tr_f(l7['scenarios']['v400_KL_15ms']['uUSD_per_register'],2)} µUSD/reg (${tr_f(l7['scenarios']['v400_KL_10ms']['uUSD_per_register'],2)} @10ms)",
            ],
            C_CRIMSON,
        ),
    ]

    pad_x = 60.0
    gap_x = 28.0
    gap_y = 22.0
    card_w = (W - 2 * pad_x - 2 * gap_x) / 3.0
    card_h = 236.0
    grid_y0 = 158.0
    for idx, (tag, title, hero, lines, col) in enumerate(cards):
        r, c = divmod(idx, 3)
        cx = pad_x + c * (card_w + gap_x)
        cy = grid_y0 + r * (card_h + gap_y)
        draw_kpi_card(ctx, cx, cy, card_w, card_h, tag, title, hero, lines, col)

    bot_y0 = grid_y0 + 2 * card_h + gap_y + 22.0
    bot_h = H - bot_y0 - 44.0
    panel_w = (W - 2 * pad_x - 30.0) / 2.0
    draw_left_speedup_cost_panel(ctx, pad_x, bot_y0, panel_w, bot_h, data)
    draw_right_percolation_quantum_panel(ctx, pad_x + panel_w + 30.0, bot_y0, panel_w, bot_h, data)

    draw_text(
        ctx, 60, H - 16,
        "Canlı Veri Kaynakları: exp124..exp135.json (12 deney) · cad_verification.json (v4.0) · BOM_DETAILED.csv (159 parça) · no_lab_measurement=true",
        11.2, color=MUTED_TXT,
    )
    draw_text(
        ctx, W - 60, H - 16,
        "Atom-Lithography v4.0 (M0 Fizik + M4 Ölçekleme + Dijital İkiz) · 2026-11-23",
        11.2, bold=True, color=SLATE_TXT, align="right",
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    surf.write_to_png(str(OUT_PNG))
    with Image.open(OUT_PNG) as im:
        assert im.size == (W, H), f"Expected {W}x{H}, got {im.size}"
    print(f"DASHBOARD_V4_OK {OUT_PNG.relative_to(ROOT)} ({W}x{H}, {OUT_PNG.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
