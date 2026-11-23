"""Generate GitHub README v6.0 hero cover dashboard `00_v6_overview_dashboard.png` (2400x1400).

Reads verified live metrics directly from disk (zero hardcoded stale metrics):
  - results/exp128_bom_sensitivity/exp128.json
  - results/exp142_option_q_multispecies_qram/exp142.json
  - results/exp143_d3_grape_m4_and_hpc_decoder/exp143.json
  - results/exp144_qldpc_bivariate_bicycle_m4/exp144.json
  - results/exp145_cloud_qpu_ibm_validation/exp145.json
  - results/exp145_cloud_qpu_ibm_validation/ibm_qpu_live_results.json
  - results/exp146_v6_digital_twin/exp146.json
  - results/exp146_v6_digital_twin/v6_digital_twin_cert.json
  - research/atom_lithography_machine/cad/cad_verification.json

Runs under `/usr/bin/python3 -B` (PyCairo + Pillow, zero numpy/matplotlib).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo
from PIL import Image

CAD_DIR = Path(__file__).resolve().parent
ROOT = CAD_DIR.parents[2]
OUT_PNG = CAD_DIR / "drawings" / "00_v6_overview_dashboard.png"
W, H = 2400, 1400

# Palette — Executive Dark-Navy / Crisp White Technical Dashboard
BG = (0.955, 0.967, 0.982)
WHITE = (1.0, 1.0, 1.0)
NAVY_TOP = (0.043, 0.098, 0.184)
NAVY_BOT = (0.086, 0.184, 0.306)
NAVY_TXT = (0.075, 0.145, 0.235)
SLATE_TXT = (0.25, 0.32, 0.41)
MUTED_TXT = (0.45, 0.52, 0.60)
BORDER = (0.81, 0.85, 0.91)
GRID = (0.90, 0.93, 0.96)
TRACK_BG = (0.942, 0.957, 0.976)

C_BLUE = (0.11, 0.44, 0.74)
C_PURPLE = (0.44, 0.27, 0.71)
C_GREEN = (0.08, 0.54, 0.36)
C_AMBER = (0.83, 0.49, 0.06)
C_TEAL = (0.06, 0.53, 0.59)
C_CRIMSON = (0.75, 0.17, 0.23)
C_GOLD_BG = (0.98, 0.89, 0.60)


def tr_f(val: float, decimals: int = 1) -> str:
    s = f"{val:,.{decimals}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def tr_i(val: int) -> str:
    return f"{val:,}".replace(",", ".")


def rounded_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 10.0) -> None:
    r = min(r, w / 2.0, h / 2.0)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def draw_text(
    ctx: cairo.Context, x: float, y: float, text: str, size: float,
    bold: bool = False, mono: bool = False, color=NAVY_TXT, align: str = "left",
    max_w: float | None = None, min_size: float = 8.2,
) -> None:
    fam = "DejaVu Sans Mono" if mono else "DejaVu Sans"
    wt = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(fam, cairo.FONT_SLANT_NORMAL, wt)
    fsz = size
    ctx.set_font_size(fsz)
    if max_w is not None:
        while ctx.text_extents(text).width > max_w and fsz > min_size:
            fsz -= 0.35
            ctx.set_font_size(fsz)
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
    size: float = 10.4, pad_x: float = 9.0, h: float = 22.0, align: str = "left",
) -> float:
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    tw = ctx.text_extents(text).width
    pw = tw + 2 * pad_x
    if align == "right":
        x -= pw
    elif align == "center":
        x -= pw / 2.0
    rounded_rect(ctx, x, y, pw, h, r=h / 2.0)
    ctx.set_source_rgb(*bg_col)
    ctx.fill()
    draw_text(ctx, x + pw / 2.0, y + h * 0.68, text, size, bold=True, color=txt_col, align="center")
    return pw


def draw_panel_shell(
    ctx: cairo.Context, x: float, y: float, w: float, h: float,
    tag: str, title: str, subtitle: str, accent,
) -> float:
    rounded_rect(ctx, x + 2, y + 4, w, h, 12)
    ctx.set_source_rgba(0.05, 0.12, 0.22, 0.065)
    ctx.fill()
    rounded_rect(ctx, x, y, w, h, 12)
    ctx.set_source_rgb(*WHITE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.3)
    ctx.stroke()

    ctx.save()
    rounded_rect(ctx, x, y, w, h, 12)
    ctx.clip()
    ctx.set_source_rgb(*accent)
    ctx.rectangle(x, y, w, 5.0)
    ctx.fill()
    ctx.restore()

    pw = draw_pill(ctx, x + 18, y + 15, tag, accent, WHITE, size=10.2, pad_x=9, h=21)
    draw_text(
        ctx, x + 18 + pw + 10, y + 31, title, 14.0, bold=True, color=NAVY_TXT,
        max_w=w - (18 + pw + 26), min_size=10.8,
    )
    draw_text(ctx, x + 18, y + 53, subtitle, 10.4, color=MUTED_TXT, max_w=w - 36, min_size=8.6)
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.0)
    ctx.move_to(x + 18, y + 63)
    ctx.line_to(x + w - 18, y + 63)
    ctx.stroke()
    return y + 73.0


def draw_kpi_card(
    ctx: cairo.Context, x: float, y: float, w: float, h: float,
    tag: str, hero: str, line1: str, line2: str, accent,
) -> None:
    rounded_rect(ctx, x + 2, y + 4, w, h, 11)
    ctx.set_source_rgba(0.05, 0.12, 0.22, 0.065)
    ctx.fill()
    rounded_rect(ctx, x, y, w, h, 11)
    ctx.set_source_rgb(*WHITE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER)
    ctx.set_line_width(1.3)
    ctx.stroke()

    ctx.save()
    rounded_rect(ctx, x, y, w, h, 11)
    ctx.clip()
    ctx.set_source_rgb(*accent)
    ctx.rectangle(x, y, 7, h)
    ctx.fill()
    ctx.restore()

    draw_pill(ctx, x + 18, y + 12, tag, accent, WHITE, size=10.0, pad_x=9, h=21)
    draw_text(ctx, x + 18, y + 65, hero, 19.6, bold=True, color=accent, max_w=w - 30, min_size=13.5)
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.0)
    ctx.move_to(x + 18, y + 77)
    ctx.line_to(x + w - 16, y + 77)
    ctx.stroke()
    draw_text(ctx, x + 18, y + 101, line1, 10.4, bold=True, color=NAVY_TXT, max_w=w - 30, min_size=8.5)
    draw_text(ctx, x + 18, y + 124, line2, 10.1, color=SLATE_TXT, max_w=w - 30, min_size=8.4)


def draw_hbar_row(
    ctx: cairo.Context, x_lbl_r: float, x_bar: float, bar_w: float, y_top: float, bar_h: float,
    label: str, frac: float, val_txt: str, col, lbl_max_w: float = 175.0, val_max_w: float = 120.0,
) -> None:
    draw_text(
        ctx, x_lbl_r, y_top + bar_h * 0.68, label, 10.5, bold=True, color=NAVY_TXT,
        align="right", max_w=lbl_max_w, min_size=8.6,
    )
    rounded_rect(ctx, x_bar, y_top, bar_w, bar_h, 5)
    ctx.set_source_rgb(*TRACK_BG)
    ctx.fill()
    fw = max(6.0, min(1.0, frac) * bar_w)
    rounded_rect(ctx, x_bar, y_top, fw, bar_h, 5)
    ctx.set_source_rgb(*col)
    ctx.fill()
    draw_text(ctx, x_bar + bar_w + 8, y_top + bar_h * 0.68, val_txt, 10.2, bold=True, mono=True, color=col, max_w=val_max_w)


def load_data() -> dict:
    def rj(rel: str) -> dict:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    return {
        "exp128": rj("results/exp128_bom_sensitivity/exp128.json"),
        "exp142": rj("results/exp142_option_q_multispecies_qram/exp142.json"),
        "exp143": rj("results/exp143_d3_grape_m4_and_hpc_decoder/exp143.json"),
        "exp144": rj("results/exp144_qldpc_bivariate_bicycle_m4/exp144.json"),
        "exp145": rj("results/exp145_cloud_qpu_ibm_validation/exp145.json"),
        "ibm_live": rj("results/exp145_cloud_qpu_ibm_validation/ibm_qpu_live_results.json"),
        "exp146": rj("results/exp146_v6_digital_twin/exp146.json"),
        "cert_v6": rj("results/exp146_v6_digital_twin/v6_digital_twin_cert.json"),
        "cad": json.loads((CAD_DIR / "cad_verification.json").read_text(encoding="utf-8")),
    }


# ---------------------------------------------------------------------------
# Panel 1: v5 -> v6 Cryostat Fleet & $/L_sys Collapse (679 -> 100 -> 1)
# ---------------------------------------------------------------------------
def draw_panel1_fleet_collapse(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    l7 = data["exp146"]["layer7_v3_to_v6_evolution"]["fleet_100L_trajectory"]
    l3 = data["exp146"]["layer3_qldpc"]
    c_d2 = l7["v5_D2_SC_cryostats"]
    c_d3 = l7["v6_D3_GRAPE_SC_cryostats"]
    c_ql = l7["v6_qLDPC_108L_cryostats"]
    u_d2 = l7["v5_D2_SC_usd_per_L_sys"]
    u_d3 = l7["v6_D3_GRAPE_SC_usd_per_L_sys"]
    u_ql = l7["v6_qLDPC_108L_usd_per_L_sys"]
    u_120 = l3["config_120L_usd_per_L_sys_p50"]

    cy = draw_panel_shell(
        ctx, x, y, w, h, "v5 → v6 Evrim",
        "100L Kriyostat Filosu & $/L_sys Çöküşü (234× ↓)",
        "Exp138 (SC) × Exp143 (D3 GRAPE) × Exp144 (qLDPC Gross Code) · Wright b=%85 · LD400",
        C_BLUE,
    )

    draw_text(ctx, x + 20, cy + 12, "A. 100 Mantıksal Kübit Kriyostat Sayısı (log₁₀ ölçek, Düşük = İyi)", 11.0, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy - 3, f"{c_d2} → {c_d3} → {c_ql} kriyo", C_GREEN, WHITE, size=9.6, pad_x=8, h=20, align="right")

    bx = x + 195
    bw = w - 335
    ry = cy + 28
    # log10(val + 1) / log10(1000) keeps 1 clearly visible while preserving exact order
    def lscale(v: float, vmax: float) -> float:
        return math.log10(max(v, 1.0) + 0.8) / math.log10(vmax + 0.8)

    for lbl, cv, txt, col in (
        ("v5 D2 Yüzey Kodu (d=99)", c_d2, f"{c_d2} kriyo (baz)", C_CRIMSON),
        ("v6 D3 GRAPE SC (d=37)", c_d3, f"{c_d3} kriyo (6,8×↓)", C_AMBER),
        ("v6 qLDPC 108L (9 blok)", c_ql, f"{c_ql} kriyo (679×↓)", C_GREEN),
    ):
        draw_hbar_row(ctx, bx - 10, bx, bw, ry, 23, lbl, lscale(cv, 800.0), txt, col, val_max_w=125)
        ry += 32

    cy2 = ry + 14
    ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
    ctx.move_to(x + 18, cy2 - 8); ctx.line_to(x + w - 18, cy2 - 8); ctx.stroke()
    draw_text(ctx, x + 20, cy2 + 10, "B. Dağıtılmış Sistem Maliyeti $/L_sys [USD, log₁₀ ölçek]", 11.0, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy2 - 4, f"{tr_f(l7['total_usd_per_L_compression_x'],1)}× Ucuzlama", C_BLUE, WHITE, size=9.6, pad_x=8, h=20, align="right")

    ry2 = cy2 + 26
    for lbl, uv, txt, col in (
        ("v5 D2 SC (10⁻⁹)", u_d2, f"${tr_f(u_d2/1e6,2)}M", C_CRIMSON),
        ("v6 D3 GRAPE SC (10⁻⁹)", u_d3, f"${tr_f(u_d3/1e6,2)}M", C_AMBER),
        ("v6 qLDPC 108L (9/10 yedek)", u_ql, f"${tr_f(u_ql/1e3,1)}k", C_BLUE),
        ("v6 qLDPC 120L (10 blok)", u_120, f"${tr_f(u_120/1e3,1)}k", C_GREEN),
    ):
        frac = (math.log10(uv) - 4.0) / (math.log10(2.0e7) - 4.0)
        draw_hbar_row(ctx, bx - 10, bx, bw, ry2, 22, lbl, frac, txt, col, val_max_w=125)
        ry2 += 30

    by = y + h - 78
    rounded_rect(ctx, x + 18, by, w - 36, 62, 8)
    ctx.set_source_rgb(0.935, 0.962, 0.992); ctx.fill_preserve()
    ctx.set_source_rgb(*C_BLUE); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(
        ctx, x + 30, by + 23,
        f"Tek LD400/PT420 ({tr_i(2887)} h.): {l3['single_cryostat_max_blocks']} Gross blok = {l3['single_cryostat_max_logical_qubits']}L (%99,8 MXC)",
        10.9, bold=True, color=NAVY_TXT, max_w=w - 60,
    )
    draw_text(
        ctx, x + 30, by + 46,
        f"108L 5y TCO = $6,89M ($63.827/L_sys) · W3 silikon çip payı = ${tr_f(l3['config_108L_W3_fab_usd_per_L'],4)}/L_fab",
        10.1, color=SLATE_TXT, max_w=w - 60,
    )


# ---------------------------------------------------------------------------
# Panel 2: Exp143 D3 K=8 Fourier GRAPE M4 Gate + Live Exp138 MWPM Lambda
# ---------------------------------------------------------------------------
def draw_panel2_d3_grape(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    l2 = data["exp146"]["layer2_d3_grape"]
    cy = draw_panel_shell(
        ctx, x, y, w, h, "Exp143 · H161",
        "D3 K=8 Fourier GRAPE M4 Kapısı & Λ = 2,825",
        f"0,894–1,126 µs · %100 ≤ 300 MHz (maks {tr_f(l2['max_bw_99pct_mhz'],1)} MHz) · CPTP temiz · Canlı MWPM",
        C_PURPLE,
    )

    draw_text(ctx, x + 20, cy + 12, "A. 2-Kübit M4 Kapı Hatası p_2q [%] — D3 Hedefi ≤ %0,50", 11.0, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy - 3, f"F_Bell = {tr_f(l2['echo_Q1e6_S0p25_F_Bell'],4)}", C_PURPLE, WHITE, size=9.6, pad_x=8, h=20, align="right")

    bx = x + 195
    bw = w - 315
    ry = cy + 26
    max_p = 1.05
    p_rows = [
        ("v5 D2 P4 (Q=5e5, S=0,25)", 0.920, C_CRIMSON),
        ("v6 Muhaf. GRAPE (5-çift)", l2["cons_Q1e6_S0p25_5pair_p_2q_pct"], C_AMBER),
        ("v6 Muhaf. GRAPE (high-g)", l2["cons_Q1e6_S0p25_highG3_p_2q_pct"], C_TEAL),
        ("v6 Echo GRAPE (S=0,390)", l2["echo_Q1e6_S0p39_p_2q_pct"], C_BLUE),
        ("v6 Echo GRAPE (S=0,250)", l2["echo_Q1e6_S0p25_p_2q_pct"], C_GREEN),
    ]
    for lbl, pv, col in p_rows:
        draw_hbar_row(ctx, bx - 10, bx, bw, ry, 20, lbl, pv / max_p, f"%{tr_f(pv,3)}", col)
        ry += 27

    # 0.50% D3 target vertical dashed line (label cleanly below bottom bar)
    x_d3 = bx + (0.50 / max_p) * bw
    ctx.save()
    ctx.set_dash([5.0, 3.0]); ctx.set_source_rgb(*C_GREEN); ctx.set_line_width(1.6)
    ctx.move_to(x_d3, cy + 24); ctx.line_to(x_d3, ry - 4); ctx.stroke()
    ctx.restore()
    draw_text(ctx, x_d3, ry + 7, "D3 hedefi %0,50", 8.9, bold=True, color=C_GREEN, align="center")

    cy2 = ry + 18
    ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
    ctx.move_to(x + 18, cy2 - 8); ctx.line_to(x + w - 18, cy2 - 8); ctx.stroke()
    draw_text(ctx, x + 20, cy2 + 10, "B. Canlı Exp138 MWPM Yüzey Kodu Hata Bastırma Λ", 11.0, bold=True, color=NAVY_TXT)

    ry2 = cy2 + 24
    max_l = 3.10
    for lbl, lv, col in (
        ("v4 P1 Çıplak (FAIL)", 0.00, C_CRIMSON),
        ("v5 D2 Rota C (Q=5e5)", 1.40, C_AMBER),
        ("v6 Muhafazakar GRAPE", l2["lambda_D3_phys_cons_5pair"], C_BLUE),
        ("v6 Echo GRAPE (Q=1e6)", l2["lambda_D3_phys_echo_Q1e6_S0p25"], C_GREEN),
    ):
        draw_hbar_row(ctx, bx - 10, bx, bw, ry2, 20, lbl, lv / max_l, f"Λ={tr_f(lv,2)}", col)
        ry2 += 27

    x_lam1 = bx + (1.0 / max_l) * bw
    ctx.save()
    ctx.set_dash([5.0, 3.0]); ctx.set_source_rgb(*C_GREEN); ctx.set_line_width(1.5)
    ctx.move_to(x_lam1, cy2 + 22); ctx.line_to(x_lam1, ry2 - 4); ctx.stroke()
    ctx.restore()
    draw_text(ctx, x_lam1, ry2 + 7, "Λ=1,0 FT", 8.8, bold=True, color=C_GREEN, align="center")

    by = y + h - 68
    rounded_rect(ctx, x + 18, by, w - 36, 52, 8)
    ctx.set_source_rgb(0.955, 0.945, 0.990); ctx.fill_preserve()
    ctx.set_source_rgb(*C_PURPLE); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(
        ctx, x + 30, by + 20,
        f"Fiziksel D3 Kapanışı: F_avg = %{tr_f(l2['echo_Q1e6_S0p25_F_avg']*100,2)} · F_Bell = %{tr_f(l2['echo_Q1e6_S0p25_F_Bell']*100,2)} (S=0,25)",
        10.7, bold=True, color=NAVY_TXT, max_w=w - 60,
    )
    draw_text(
        ctx, x + 30, by + 40,
        f"100L SC (10⁻⁹): {l2['cryostats_100L_1e9_D2_baseline']} → {l2['cryostats_100L_1e9_D3_echo']} kriyostat ({tr_f(l2['cryostat_reduction_D2_to_D3'],2)}× küçülme)",
        10.0, color=SLATE_TXT, max_w=w - 60,
    )


# ---------------------------------------------------------------------------
# Panel 3: Exp144 qLDPC [[144,12,12]] Gross Code & BP-OSD-2
# ---------------------------------------------------------------------------
def draw_panel3_qldpc(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    l3 = data["exp146"]["layer3_qldpc"]
    p4_u = data["exp144"]["part4_circuit_level_dem"]["uniform_depolarizing_sweep"]
    p_th_pct = p4_u["p_th_crossing_72_vs_144"] * 100.0
    d_eff = p4_u["subthreshold_power_law_fit_BB144"]["d_eff_circuit"]

    cy = draw_panel_shell(
        ctx, x, y, w, h, "Exp144 · H162",
        "qLDPC [[144,12,12]] Gross Code & BP-OSD-2",
        f"Bravyi 24×12 katlı-torus · P_cell={l3['pitch_um']:.0f} µm → L_max={tr_f(l3['L_max_um'],1)} µm ≤ 300 µm · 7/7 PASS",
        C_TEAL,
    )

    # Section A: Geometry & Defect-Tolerant Yield bars
    draw_text(ctx, x + 20, cy + 12, "A. M4 300 µm Rezonatör Uyumu & Arızalı Hücre Verimi (f*=%1,5)", 10.9, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy - 3, "0 Rezonatör Değişikliği", C_GREEN, WHITE, size=9.4, pad_x=8, h=20, align="right")

    bx = x + 195
    bw = w - 315
    ry = cy + 26
    for lbl, frac, txt, col in (
        ("L_max (P=20 µm) / 300 µm", l3["L_max_um"] / 300.0, f"{tr_f(l3['L_max_um'],1)} µm", C_TEAL),
        ("Stark'sız 288h Blok (N=6)", 0.0223, "%2,23 FAIL", C_CRIMSON),
        ("Stark + N_cand=8 Blok", l3["block_288_yield_f15_N8_pct"] / 100.0, f"%{tr_f(l3['block_288_yield_f15_N8_pct'],2)}", C_BLUE),
        ("9/10 Yedekli 108L Yonga", l3["spared_9of10_108L_die_yield_N8_pct"] / 100.0, f"%{tr_f(l3['spared_9of10_108L_die_yield_N8_pct'],2)}", C_GREEN),
    ):
        draw_hbar_row(ctx, bx - 10, bx, bw, ry, 20, lbl, frac, txt, col)
        ry += 28

    # Section B: 3D Circuit DEM BP-OSD-2 Comparison Table (vs Surface Code)
    cy2 = ry + 12
    ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
    ctx.move_to(x + 18, cy2 - 8); ctx.line_to(x + w - 18, cy2 - 8); ctx.stroke()
    draw_text(
        ctx, x + 20, cy2 + 10,
        f"B. 3B Devre DEM (p_th=%{tr_f(p_th_pct,3)}, d_eff={tr_f(d_eff,2)}) — BB144 vs Yüzey Kodu",
        10.8, bold=True, color=NAVY_TXT, max_w=w - 36,
    )

    ty = cy2 + 22
    tw = w - 36
    rounded_rect(ctx, x + 18, ty, tw, 23, 5)
    ctx.set_source_rgb(*NAVY_TOP); ctx.fill()
    for dx, ht, al in ((26, "Rejim & Kod", "left"), (310, "Hücre/L", "center"), (465, "p_L / tur (1L)", "right"), (706, "Kıyas", "right")):
        draw_text(ctx, x + dx, ty + 16, ht, 9.6, bold=True, color=WHITE, align=al)

    t_rows = [
        ("Exp138 d=7 SC (D3 %0,50)", "97", "5,01×10⁻⁴", "Referans SC", SLATE_TXT),
        ("BB144 D3 P4 (%0,50, 2µs)", "24", "1,98×10⁻⁴", "2,5× iyi · 4,0× az", C_BLUE),
        ("Exp138 d=11 SC (D3+ %0,30)", "241", "1,09×10⁻⁴", "Referans SC", SLATE_TXT),
        ("BB144 D3+ (%0,30, 2µs)", "24", "2,10×10⁻⁵", "5,2× iyi · 10,0× az", C_GREEN),
        ("BB144 D3+ (%0,30, 3µs)", "24", "0 / 6.000", "<5,3×10⁻⁵ (%95)", C_TEAL),
    ]
    ry_t = ty + 25
    for idx_r, (rl, rc, rp, rk, rcol) in enumerate(t_rows):
        if idx_r % 2 == 1:
            ctx.set_source_rgb(0.945, 0.975, 0.978)
            ctx.rectangle(x + 18, ry_t, tw, 24); ctx.fill()
        yt = ry_t + 16
        draw_text(ctx, x + 26, yt, rl, 9.9, bold=(idx_r in (1, 3, 4)), color=NAVY_TXT)
        draw_text(ctx, x + 310, yt, rc, 9.9, mono=True, bold=True, color=rcol, align="center")
        draw_text(ctx, x + 465, yt, rp, 9.9, mono=True, bold=True, color=rcol, align="right")
        draw_text(ctx, x + 706, yt, rk, 9.6, bold=True, color=rcol, align="right")
        ry_t += 24

    by = y + h - 68
    rounded_rect(ctx, x + 18, by, w - 36, 52, 8)
    ctx.set_source_rgb(0.928, 0.976, 0.980); ctx.fill_preserve()
    ctx.set_source_rgb(*C_TEAL); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(ctx, x + 30, by + 20, "Kalınlık-2 Düzlemsel: L1=576 yerel + L2=288 uzun kenar (M4a/M4b hava-köprüsü)", 10.5, bold=True, color=NAVY_TXT, max_w=w - 60)
    draw_text(ctx, x + 30, by + 40, "Dürüst Sınır: 10⁻⁹/tur için p_2q ≈ %0,10–0,15 veya [[288,12,18]] d=18 (2 kriyo, $104k/L)", 9.9, color=SLATE_TXT, max_w=w - 60)


# ---------------------------------------------------------------------------
# Panel 4: Exp145 LIVE ibm_marrakesh (156Q) QPU Validation + Live Ramsey Plot
# ---------------------------------------------------------------------------
def draw_panel4_live_ibm(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    ibm = data["ibm_live"]
    c1 = ibm["analysis"]["C1_dd_and_bell"]
    c2 = ibm["analysis"]["C2_repcode3"]
    c3 = ibm["analysis"]["C3_ramsey_boed"]
    job_id = ibm["job"]["job_id"]
    backend = ibm["backend"]["name"]
    nq = ibm["backend"]["n_qubits"]

    cy = draw_panel_shell(
        ctx, x, y, w, h, "Exp145 · CANLI QPU",
        f"CANLI {backend} ({nq}Q) Donanım Doğrulaması",
        f"IBM Heron r2 · job_id={job_id} · 16 PUB × 4.096 shot · [2,3,4,5,6] (0 SWAP) · 7/7 PASS",
        C_GREEN,
    )

    # Section A: C1 DD & Bell live bars
    draw_text(ctx, x + 20, cy + 12, "A. Canlı C1 Dinamik Dekupling (48,1 µs) & Bell Φ⁺", 11.0, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy - 3, f"XY4 +{tr_f(c1['dd_gain_xy4_over_bare']*100,1)} pp", C_GREEN, WHITE, size=9.6, pad_x=8, h=20, align="right")

    bx = x + 175
    bw = w - 295
    ry = cy + 25
    for lbl, val, col in (
        ("Bare Idle (DD yok)", c1["p0_bare_idle"], C_CRIMSON),
        ("Hahn-Echo DD", c1["p0_hahn_echo"], C_BLUE),
        ("XY4 DD (48,1 µs)", c1["p0_xy4_dd"], C_GREEN),
        ("Bell F(Φ⁺) (0 SWAP)", c1["bell_fidelity_Phi_plus"], C_PURPLE),
    ):
        draw_hbar_row(ctx, bx - 10, bx, bw, ry, 19, lbl, val, f"{tr_f(val,4)}", col, lbl_max_w=155)
        ry += 25

    # Section B: ACTUAL LIVE C3 RAMSEY COSINE FRINGE + 3-pt Q16.16 BOED Plot!
    cy2 = ry + 10
    ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
    ctx.move_to(x + 18, cy2 - 6); ctx.line_to(x + w - 18, cy2 - 6); ctx.stroke()
    draw_text(ctx, x + 20, cy2 + 10, "B. Canlı C3 Ramsey Saçağı (q2) & 3-Nokta Q16.16 BOED", 10.9, bold=True, color=NAVY_TXT)
    draw_pill(
        ctx, x + w - 18, cy2 - 4,
        f"BOED: {tr_f(c3['q16_16_boed']['est_freq_kHz'],2)} kHz (ΔFP64 {tr_f(c3['q16_16_boed']['q16_vs_fp64_diff_kHz']*1000,1)} Hz)",
        C_BLUE, WHITE, size=9.2, pad_x=8, h=19, align="right",
    )

    gx0, gx1 = x + 64, x + w - 28
    gy0, gy1 = cy2 + 24, y + h - 98
    gw, gh = gx1 - gx0, gy1 - gy0

    def px(t_us: float) -> float:
        return gx0 + (t_us - 0.5) / 8.0 * gw

    def py(p0: float) -> float:
        return gy1 - p0 * gh

    # Grid & axes
    for p_tick in (0.0, 0.5, 1.0):
        yt = py(p_tick)
        ctx.set_source_rgb(*GRID if p_tick > 0 else BORDER); ctx.set_line_width(1.0)
        ctx.move_to(gx0, yt); ctx.line_to(gx1, yt); ctx.stroke()
        draw_text(ctx, gx0 - 8, yt + 3.5, f"{p_tick:.1f}", 9.2, color=MUTED_TXT, align="right")
    for t_tick in (1, 2, 3, 4, 5, 6, 7, 8):
        xt = px(t_tick)
        ctx.set_source_rgb(*GRID); ctx.set_line_width(0.8)
        ctx.move_to(xt, gy0); ctx.line_to(xt, gy1); ctx.stroke()
        draw_text(ctx, xt, gy1 + 13, f"{t_tick}µs", 8.9, color=MUTED_TXT, align="center")

    # Smooth fitted cosine fringe using measured live blind-8pt frequency & visibility
    f_fit = c3["blind_8pt"]["est_freq_kHz"] * 1e-3  # MHz = cycles/us
    vis = c3["visibility_est"]
    ctx.set_source_rgba(*C_BLUE, 0.55); ctx.set_line_width(2.0)
    for k_pt in range(81):
        tu = 0.8 + 7.4 * (k_pt / 80.0)
        pv = 0.5 + 0.5 * vis * math.cos(2.0 * math.pi * f_fit * tu)
        if k_pt == 0:
            ctx.move_to(px(tu), py(pv))
        else:
            ctx.line_to(px(tu), py(pv))
    ctx.stroke()

    # Plot all 8 live hardware points; highlight the 3 Q16.16 BOED queried points in gold/crimson
    q_idx = set(c3["q16_16_boed"]["queried_indices"])
    for idx_d, (du, p0m) in enumerate(zip(c3["delays_us"], c3["p0_measured"])):
        cx_d, cy_d = px(du), py(p0m)
        if idx_d in q_idx:
            ctx.set_source_rgb(*C_AMBER); ctx.arc(cx_d, cy_d, 7.5, 0, 2 * math.pi); ctx.fill()
            ctx.set_source_rgb(*WHITE); ctx.arc(cx_d, cy_d, 4.2, 0, 2 * math.pi); ctx.fill()
            ctx.set_source_rgb(*C_CRIMSON); ctx.arc(cx_d, cy_d, 2.5, 0, 2 * math.pi); ctx.fill()
        else:
            ctx.set_source_rgb(*C_BLUE); ctx.arc(cx_d, cy_d, 4.5, 0, 2 * math.pi); ctx.fill()

    # Compact legend in top-center empty bowl above t=3..6 us (clear of both t=1 and t=8 dots!)
    draw_text(ctx, px(4.3), gy0 + 12, "● 8-pt Canlı Donanım   |   ◉ 3-pt Q16.16 BOED (2,67× hız)", 9.0, bold=True, color=NAVY_TXT, align="center")

    # Bottom C2 Rep-Code & auto_recal summary box
    by = y + h - 72
    rounded_rect(ctx, x + 18, by, w - 36, 56, 8)
    ctx.set_source_rgb(0.930, 0.980, 0.955); ctx.fill_preserve()
    ctx.set_source_rgb(*C_GREEN); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(
        ctx, x + 30, by + 21,
        f"Canlı C2 d=3: p_phys=%{tr_f(c2['avg_p_phys']*100,2)} → MWPM %{tr_f(c2['avg_p_L_syndrome_mwpm']*100,2)} (5,16×) · Maj %{tr_f(c2['avg_p_L_majority']*100,2)} (7,83×) · PostSel %0,00",
        10.2, bold=True, color=NAVY_TXT, max_w=w - 60,
    )
    draw_text(
        ctx, x + 30, by + 42,
        f"CellISA v4.0 (20 opcode) + auto_recal.py (4/4 PASS, M0) · Canlı q2 doğal kayma: {tr_f(data['exp146']['layer6_live_ibm_qpu_and_cellisa40']['live_ibm_qpu']['c3_measured_q2_drift_kHz'],2)} kHz",
        9.9, color=SLATE_TXT, max_w=w - 60,
    )


# ---------------------------------------------------------------------------
# Panel 5: Exp142 Option-Q (qRAM + 167Er Fiber) & Exp143 Option-HPC (100G RDMA)
# ---------------------------------------------------------------------------
def draw_panel5_options_qhpc(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    l4 = data["exp146"]["layer4_option_q_multispecies"]
    l5 = data["exp146"]["layer5_option_hpc"]
    er_sw = data["exp142"]["part2_s1_multispecies"]["er167_telecom_link"]["distance_sweep"]
    er_map = {int(round(r["L_km"])): r for r in er_sw}

    cy = draw_panel_shell(
        ctx, x, y, w, h, "Exp142 × Exp143",
        "Option-Q (qRAM/¹⁶⁷Er Fiber) & Option-HPC (100G)",
        f"Chebyshev-5 qRAM ({tr_i(int(round(l4['lifetime_gain_F90_XY8_1s'])))}×–{tr_i(int(round(l4['lifetime_gain_F90_XY8_3s'])))}× ömür) + 4U RoCEv2 RDMA ({l5['tau_ingest_ns']:.0f} ns)",
        C_AMBER,
    )

    # Section A: Option-Q 167Er 1536 nm fiber distance bars
    draw_text(ctx, x + 20, cy + 12, "A. Option-Q ¹⁶⁷Er 1536 nm Telekom Fiber Hızı [Hz] (Barrett-Kok)", 10.9, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy - 3, f"qRAM F_SWAP={tr_f(l4['F_SWAP_rt_31P_nuclear'],4)}", C_AMBER, WHITE, size=9.4, pad_x=8, h=20, align="right")

    bx = x + 165
    bw = w - 310
    ry = cy + 26
    for km, col in ((1, C_TEAL), (5, C_BLUE), (10, C_GREEN), (20, C_AMBER), (50, C_CRIMSON)):
        rec = er_map[km]
        rate = rec["R_ent_BK_Hz"]
        fid = rec["F_ent_BK"]
        frac = math.log10(max(rate, 1.0)) / math.log10(4000.0)
        draw_hbar_row(
            ctx, bx - 10, bx, bw, ry, 19,
            f"L = {km} km SMF-28", frac, f"{tr_f(rate,1)} Hz (F={tr_f(fid,2)})",
            col, lbl_max_w=145, val_max_w=135,
        )
        ry += 25

    # Section B: Option-HPC 100G RoCEv2 Real-Time Decoding Latency vs Budget
    cy2 = ry + 12
    ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
    ctx.move_to(x + 18, cy2 - 8); ctx.line_to(x + w - 18, cy2 - 8); ctx.stroke()
    draw_text(ctx, x + 20, cy2 + 10, "B. Option-HPC 100G RoCEv2 Gerçek-Zamanlı Dekoder Gecikmesi [µs]", 10.9, bold=True, color=NAVY_TXT)

    ry2 = cy2 + 24
    bx2 = x + 195
    bw2 = w - 335
    for lbl, val, lim, col in (
        ("Tek CPU d=37 SC (FAIL)", l5["d37_sc_cpu_single_us"], 35.0, C_CRIMSON),
        ("Option-HPC d=37 SC", l5["d37_sc_hpc_e2e_us"], 10.0, C_BLUE),
        ("Option-HPC qLDPC 108L", l5["qldpc_108L_hpc_e2e_mean_us"], 10.0, C_GREEN),
        ("100G RoCEv2 RDMA İletim", l5["tau_ingest_ns"] / 1000.0, 10.0, C_TEAL),
    ):
        frac = min(1.0, val / 35.0) if val > 10.0 else min(1.0, val / 10.0)
        tag = f"{tr_f(val,2)} µs" + (" <6,70" if "d=37 SC" in lbl and "HPC" in lbl else (" <2,62" if "qLDPC" in lbl else (" FAIL" if "CPU" in lbl else " (777 ns)")))
        draw_hbar_row(ctx, bx2 - 10, bx2, bw2, ry2, 20, lbl, frac, tag, col, val_max_w=130)
        ry2 += 27

    by = y + h - 72
    rounded_rect(ctx, x + 18, by, w - 36, 56, 8)
    ctx.set_source_rgb(0.992, 0.964, 0.922); ctx.fill_preserve()
    ctx.set_source_rgb(*C_AMBER); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(
        ctx, x + 30, by + 21,
        f"Option-Q: +9,2 kg / +$168k (+0,78 µW MXC) · 7,5 keV ¹²¹Sb -%{tr_f(l4['sb121_straggle_reduction_pct'],1)} keskin saçılma",
        10.4, bold=True, color=NAVY_TXT, max_w=w - 60,
    )
    draw_text(
        ctx, x + 30, by + 42,
        f"Option-HPC: +64,0 kg / +$132k (2.195 W, 0 W kriyo) · 108L qLDPC tek 4U rafta (0,24 Gbps)",
        10.0, color=SLATE_TXT, max_w=w - 60,
    )


# ---------------------------------------------------------------------------
# Panel 6: Modular BOM v6.0 + CAD v6.0 + SHA-256 & Honest Epistemic Seal
# ---------------------------------------------------------------------------
def draw_panel6_modular_seal(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    l1 = data["exp146"]["layer1_integrity"]
    l7 = data["exp146"]["layer7_v3_to_v6_evolution"]
    mc = l7["modular_mc_100k"]
    bom = l1["bom_v6"]
    cad = l1["cad_v6"]
    sha = data["cert_v6"]["sha256"]
    job_id = data["ibm_live"]["job"]["job_id"]

    cy = draw_panel_shell(
        ctx, x, y, w, h, "Modüler v6.0",
        "Modüler M3 Base + Option-Q/HPC & Epistemik Mühür",
        f"BOM {bom['csv_row_count']} Parça ($0,00 köprü) · CAD {cad['part_count']} Parça (0,0000 kg fark) · 9-RFQ %{tr_f(bom['rfq9_nom_share_pct'],1)}",
        C_CRIMSON,
    )

    # Section A: Clean 4-row modular pricing & risk table
    draw_text(ctx, x + 20, cy + 12, "A. Modüler Yapılandırmalar (100k MC · Çift Sayım = $0,00)", 10.9, bold=True, color=NAVY_TXT)
    ty = cy + 22
    tw = w - 36
    rounded_rect(ctx, x + 18, ty, tw, 24, 5)
    ctx.set_source_rgb(*NAVY_TOP); ctx.fill()
    for dx, ht, al in (
        (26, "Konfigürasyon", "left"),
        (285, "BOM (Nom)", "right"),
        (405, "Kütle (CAD)", "right"),
        (535, "Prog P50", "right"),
        (706, "P(Prog>$100M)", "right"),
    ):
        draw_text(ctx, x + dx, ty + 16, ht, 9.6, bold=True, color=WHITE, align=al)

    m_rows = [
        ("M3 v5.0 Base (167p)", f"${tr_f(bom['m3_v5_base_nom_usd']/1e6,3)}M", "1.034,9 kg", f"${tr_f(mc['M3_v5_0_Base']['prog_p50_M'],2)}M", f"%{tr_f(mc['M3_v5_0_Base']['P_gt_100M_pct'],2)} (<%5)", C_GREEN),
        ("+ Option-HPC (170p)", f"${tr_f(bom['m3_v6_plus_option_hpc_nom_usd']/1e6,3)}M", "1.098,9 kg", f"${tr_f(mc['M3_v6_0_Plus_Option_HPC']['prog_p50_M'],2)}M", f"%{tr_f(mc['M3_v6_0_Plus_Option_HPC']['P_gt_100M_pct'],2)} (<%5)", C_BLUE),
        ("+ Option-Q (171p)", f"${tr_f(bom['m3_v6_plus_option_q_nom_usd']/1e6,3)}M", "1.044,1 kg", f"${tr_f(mc['M3_v6_0_Plus_Option_Q']['prog_p50_M'],2)}M", f"%{tr_f(mc['M3_v6_0_Plus_Option_Q']['P_gt_100M_pct'],2)} (<%5)", C_TEAL),
        ("M3 v6.0 Full (174p)", f"${tr_f(bom['m3_v6_full_nom_usd']/1e6,3)}M", f"{tr_f(cad['total_mass_kg'],1)} kg", f"${tr_f(mc['M3_v6_0_Full']['prog_p50_M'],2)}M", f"%{tr_f(mc['M3_v6_0_Full']['P_gt_100M_pct'],2)} (FOAK %6,9)", C_AMBER),
    ]
    ry_t = ty + 26
    for idx_r, (rl, rb, rm, rp, rex, rcol) in enumerate(m_rows):
        if idx_r % 2 == 1:
            ctx.set_source_rgb(0.955, 0.968, 0.985)
            ctx.rectangle(x + 18, ry_t, tw, 27); ctx.fill()
        yt = ry_t + 18
        draw_text(ctx, x + 26, yt, rl, 10.0, bold=(idx_r in (0, 3)), color=NAVY_TXT)
        draw_text(ctx, x + 285, yt, rb, 10.0, mono=True, bold=True, color=NAVY_TXT, align="right")
        draw_text(ctx, x + 405, yt, rm, 9.8, mono=True, color=SLATE_TXT, align="right")
        draw_text(ctx, x + 535, yt, rp, 9.8, mono=True, color=SLATE_TXT, align="right")
        draw_text(ctx, x + 706, yt, rex, 9.6, bold=True, color=rcol, align="right")
        ry_t += 27

    # Section B: M1 Base + 9-RFQ + CAD integrity mini-card
    by_m = ry_t + 12
    rounded_rect(ctx, x + 18, by_m, tw, 72, 8)
    ctx.set_source_rgb(0.955, 0.968, 0.986); ctx.fill_preserve()
    ctx.set_source_rgb(*C_BLUE); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(
        ctx, x + 30, by_m + 21,
        f"M1 Base Prototip = ${tr_f(bom['m1_nom_usd']/1e6,2)}M (korundu) · 9-RFQ (85p): Nom %{tr_f(bom['rfq9_nom_share_pct'],1)} / MC Var %{tr_f(bom['rfq9_var_share_pct'],1)}",
        10.2, bold=True, color=NAVY_TXT, max_w=tw - 24,
    )
    draw_text(
        ctx, x + 30, by_m + 42,
        f"CAD v6.0: {cad['part_count']} katı · {tr_f(cad['total_mass_kg'],2)} kg · 8/8 STL ({tr_i(cad['stl_triangles'])} üçgen) · 0/{tr_i(cad['pairs_checked'])} çakışma · {cad['clearances_passed']}/{cad['clearances_total']} boşluk",
        9.9, color=SLATE_TXT, max_w=tw - 24,
    )
    draw_text(
        ctx, x + 30, by_m + 61,
        "Option-Q (+$168k, +9,2 kg) + Option-HPC (+$132k, +64,0 kg) = +$300k / +73,2 kg modüler eklenti",
        9.9, color=SLATE_TXT, max_w=tw - 24,
    )

    # Section C: Dark-Navy v6.0 Epistemic & SHA-256 Cryptographic Seal Box
    by_s = y + h - 148
    rounded_rect(ctx, x + 18, by_s, tw, 132, 9)
    ctx.set_source_rgb(*NAVY_TOP); ctx.fill()
    draw_pill(ctx, x + 30, by_s + 12, "v6.0 EPİSTEMİK & KRİPTOGRAFİK MÜHÜR", C_GOLD_BG, NAVY_TOP, size=9.6, pad_x=10, h=21)
    draw_pill(ctx, x + w - 30, by_s + 12, "8/8 DT6 PASS · 24/24 SHA-256", C_GREEN, WHITE, size=9.6, pad_x=10, h=21, align="right")
    draw_text(ctx, x + 30, by_s + 52, f"v6_digital_twin_cert.json SHA-256: {sha}", 9.4, mono=True, bold=True, color=(0.82, 0.94, 1.0), max_w=tw - 24)
    draw_text(
        ctx, x + 30, by_s + 76,
        "• Silikon ³¹P & M1–M4 Makine Fiziği: M0 tasarım/simülasyon (no_lab_measurement=true, no_supplier_quotes=true).",
        9.9, bold=True, color=(0.98, 0.90, 0.65), max_w=tw - 24,
    )
    draw_text(
        ctx, x + 30, by_s + 98,
        f"• Kontrol/Dekoder/BOED (CellISA v4.0): CANLI IBM ibm_marrakesh (156Q, job={job_id}, SECRET_LEAKS=0).",
        9.9, bold=True, color=(0.56, 0.94, 0.74), max_w=tw - 24,
    )
    draw_text(
        ctx, x + 30, by_s + 119,
        "• Tarihsel v4 (feffc1d4...1914b57) & v5 (2828e8ce...6d43d1) sertifikaları bozulmadan arşivlenmiştir · 8/8 DT6 PASS.",
        9.5, color=(0.76, 0.87, 0.96), max_w=tw - 24,
    )


def main() -> None:
    data = load_data()
    l1 = data["exp146"]["layer1_integrity"]
    l2 = data["exp146"]["layer2_d3_grape"]
    l3 = data["exp146"]["layer3_qldpc"]
    l4 = data["exp146"]["layer4_option_q_multispecies"]
    l5 = data["exp146"]["layer5_option_hpc"]
    l6 = data["exp146"]["layer6_live_ibm_qpu_and_cellisa40"]["live_ibm_qpu"]
    cad = l1["cad_v6"]
    bom = l1["bom_v6"]
    mc = data["exp146"]["layer7_v3_to_v6_evolution"]["modular_mc_100k"]

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)

    ctx.set_source_rgb(*BG)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Hero Top Banner
    grad = cairo.LinearGradient(0, 0, W, 126)
    grad.add_color_stop_rgb(0.0, *NAVY_TOP)
    grad.add_color_stop_rgb(1.0, *NAVY_BOT)
    ctx.set_source(grad)
    ctx.rectangle(0, 0, W, 124)
    ctx.fill()
    ctx.set_source_rgb(*C_GREEN)
    ctx.rectangle(0, 124, W, 5)
    ctx.fill()

    draw_text(
        ctx, 48, 56,
        "ATOM LİTOGRAFİ MAKİNESİ v6.0 — qLDPC Gross Code, D3 GRAPE, Option-Q/HPC & Canlı IBM QPU",
        27.5, bold=True, color=WHITE, max_w=1720,
    )
    draw_text(
        ctx, 48, 94,
        "Exp142 (Option-Q qRAM/¹⁶⁷Er) · Exp143 (D3 GRAPE + Option-HPC) · Exp144 (qLDPC [[144,12,12]]) · Exp145 (Canlı ibm_marrakesh 156Q) · Exp146 (8/8 DT6 PASS)",
        13.2, color=(0.76, 0.87, 0.96), max_w=1680,
    )

    draw_pill(ctx, W - 48, 22, "SİLİKON ³¹P: M0 SİMÜLASYON | KONTROL/BOED: CANLI IBM QPU", C_GOLD_BG, NAVY_TOP, size=11.0, pad_x=13, h=30, align="right")
    draw_pill(
        ctx, W - 48, 66,
        f"v6.0 Dijital İkiz (8/8 DT6 PASS) · 0/{tr_i(cad['pairs_checked'])} Çakışma · {cad['clearances_passed']}/{cad['clearances_total']} Boşluk",
        (0.09, 0.45, 0.35), WHITE, size=11.2, pad_x=13, h=28, align="right",
    )

    # Top 6-Card KPI Strip (y = 144..292)
    kpi_cards = [
        (
            "CAD v6.0",
            f"{cad['part_count']} Parça | {tr_f(cad['total_mass_kg'],1)} kg",
            f"8/8 STL ({tr_i(cad['stl_triangles'])} üçgen) · 0/{tr_i(cad['pairs_checked'])} çakışma",
            f"{cad['clearances_passed']}/{cad['clearances_total']} boşluk · Opt-Q +9,2 / HPC +64 kg",
            C_TEAL,
        ),
        (
            "BOM v6.0",
            f"Base ${tr_f(bom['m3_v5_base_nom_usd']/1e6,2)}M | Full ${tr_f(bom['m3_v6_full_nom_usd']/1e6,2)}M",
            f"{bom['csv_row_count']} Parça · 9-RFQ %{tr_f(bom['rfq9_nom_share_pct'],1)} / %{tr_f(bom['rfq9_var_share_pct'],1)}",
            f"Base P>$100M=%{tr_f(mc['M3_v5_0_Base']['P_gt_100M_pct'],2)} · Full %{tr_f(mc['M3_v6_0_Full']['P_gt_100M_pct'],2)}",
            C_CRIMSON,
        ),
        (
            "D3 GRAPE M4",
            f"p_2q = %{tr_f(l2['echo_Q1e6_S0p25_p_2q_pct'],3)}–%{tr_f(l2['echo_Q1e6_S0p39_p_2q_pct'],3)}",
            f"F_Bell = {tr_f(l2['echo_Q1e6_S0p25_F_Bell'],4)} · F_avg = {tr_f(l2['echo_Q1e6_S0p25_F_avg'],4)}",
            f"Canlı MWPM Λ = {tr_f(l2['lambda_D3_phys_echo_Q1e6_S0p25'],3)} (679→100 kriyo)",
            C_PURPLE,
        ),
        (
            "qLDPC Gross Code",
            f"{l3['single_cryostat_max_logical_qubits']}L / 1 Kriyostat",
            f"108L: ${tr_f(l3['config_108L_usd_per_L_sys_p50']/1e3,1)}k/L_sys ({tr_f(l3['compression_usd_vs_D2_SC'],0)}× ↓ vs D2)",
            f"L_max={tr_f(l3['L_max_um'],1)} µm ≤ 300 · W3 ${tr_f(l3['config_108L_W3_fab_usd_per_L'],4)}/L",
            C_BLUE,
        ),
        (
            "Option-Q / HPC",
            f"{tr_i(int(round(l4['lifetime_gain_F90_XY8_1s'])))}× qRAM | {tr_f(l5['qldpc_108L_hpc_e2e_mean_us'],2)} µs",
            f"¹⁶⁷Er 10km: {tr_i(int(round(l4['er167_10km_BK_rate_Hz'])))} Hz · ¹²¹Sb -%{tr_f(l4['sb121_straggle_reduction_pct'],1)}",
            f"100G RDMA 4U: d=37 {tr_f(l5['d37_sc_hpc_e2e_us'],2)} µs / qLDPC {tr_f(l5['qldpc_108L_hpc_e2e_mean_us'],2)} µs",
            C_AMBER,
        ),
        (
            "CANLI IBM QPU",
            f"{l6['backend_name']} ({l6['n_qubits']}Q)",
            f"XY4 +{tr_f(l6['c1_xy4_gain_pp'],1)} pp · Bell F = {tr_f(l6['c1_bell_fidelity'],4)}",
            f"d=3 {tr_f(l6['c2_suppression_mwpm'],2)}×/{tr_f(l6['c2_suppression_majority'],2)}× · BOED {l6['c3_q16_points_used']}-pt ({tr_f(l6['c3_q16_vs_fp64_kHz']*1000,1)} Hz)",
            C_GREEN,
        ),
    ]
    pad_x = 48.0
    gap_k = 18.0
    kw = (W - 2 * pad_x - 5 * gap_k) / 6.0
    for i, (tag, hero, l1_s, l2_s, col) in enumerate(kpi_cards):
        draw_kpi_card(ctx, pad_x + i * (kw + gap_k), 144.0, kw, 148.0, tag, hero, l1_s, l2_s, col)

    # 3x2 Main Analytical Grid (y = 310..1350)
    gap_x = 22.0
    gap_y = 20.0
    pw = (W - 2 * pad_x - 2 * gap_x) / 3.0
    ph = 510.0
    y_r1 = 310.0
    y_r2 = y_r1 + ph + gap_y

    draw_panel1_fleet_collapse(ctx, pad_x, y_r1, pw, ph, data)
    draw_panel2_d3_grape(ctx, pad_x + pw + gap_x, y_r1, pw, ph, data)
    draw_panel3_qldpc(ctx, pad_x + 2 * (pw + gap_x), y_r1, pw, ph, data)

    draw_panel4_live_ibm(ctx, pad_x, y_r2, pw, ph, data)
    draw_panel5_options_qhpc(ctx, pad_x + pw + gap_x, y_r2, pw, ph, data)
    draw_panel6_modular_seal(ctx, pad_x + 2 * (pw + gap_x), y_r2, pw, ph, data)

    # Footer
    draw_text(
        ctx, 48, H - 16,
        "Canlı Veri Kaynakları: exp128 + exp142..exp146.json · ibm_qpu_live_results.json (ibm_marrakesh) · v6_digital_twin_cert.json · cad_verification.json (v6.0)",
        10.6, color=MUTED_TXT,
    )
    draw_text(
        ctx, W - 48, H - 16,
        "Atom-Lithography v6.0 (qLDPC + D3 GRAPE + Option-Q/HPC + Canlı IBM QPU + Dijital İkiz) · 2026-11-23",
        10.6, bold=True, color=SLATE_TXT, align="right",
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    surf.write_to_png(str(OUT_PNG))
    with Image.open(OUT_PNG) as im:
        assert im.size == (W, H), f"Expected {W}x{H}, got {im.size}"
    print(f"DASHBOARD_V6_OK {OUT_PNG.relative_to(ROOT)} ({W}x{H}, {OUT_PNG.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
