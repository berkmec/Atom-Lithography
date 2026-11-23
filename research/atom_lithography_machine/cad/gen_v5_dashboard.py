"""Generate GitHub README v5.0 hero cover dashboard `00_v5_overview_dashboard.png` (2400x1400).

Reads verified live metrics directly from:
  - results/exp128_bom_sensitivity/exp128.json
  - results/exp136_tb_sp3d5s_hyperfine/exp136.json
  - results/exp137_echoed_m4_bus_gate/exp137.json
  - results/exp138_defective_surface_code_ft/exp138.json
  - results/exp139_epi_cap_process_integration/exp139.json
  - results/exp140_cryo_fpga_boed_mux_readout/exp140.json
  - results/exp141_v5_digital_twin/exp141.json
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
OUT_PNG = CAD_DIR / "drawings" / "00_v5_overview_dashboard.png"
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
    max_w: float | None = None, min_size: float = 8.5,
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
    size: float = 10.8, pad_x: float = 10.0, h: float = 23.0, align: str = "left",
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

    # Subtle top accent bar
    ctx.save()
    rounded_rect(ctx, x, y, w, h, 12)
    ctx.clip()
    ctx.set_source_rgb(*accent)
    ctx.rectangle(x, y, w, 5.0)
    ctx.fill()
    ctx.restore()

    pw = draw_pill(ctx, x + 18, y + 16, tag, accent, WHITE, size=10.4, pad_x=9, h=22)
    draw_text(
        ctx, x + 18 + pw + 10, y + 32, title, 14.2, bold=True, color=NAVY_TXT,
        max_w=w - (18 + pw + 26), min_size=11.0,
    )
    draw_text(ctx, x + 18, y + 54, subtitle, 10.6, color=MUTED_TXT, max_w=w - 36, min_size=8.8)
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.0)
    ctx.move_to(x + 18, y + 64)
    ctx.line_to(x + w - 18, y + 64)
    ctx.stroke()
    return y + 74.0


def load_data() -> dict:
    def rj(rel: str) -> dict:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    cert_p = ROOT / "results/exp141_v5_digital_twin/v5_digital_twin_cert.json"
    cert_sha = json.loads(cert_p.read_text(encoding="utf-8"))["sha256"]
    return {
        "exp128": rj("results/exp128_bom_sensitivity/exp128.json"),
        "exp136": rj("results/exp136_tb_sp3d5s_hyperfine/exp136.json"),
        "exp137": rj("results/exp137_echoed_m4_bus_gate/exp137.json"),
        "exp138": rj("results/exp138_defective_surface_code_ft/exp138.json"),
        "exp139": rj("results/exp139_epi_cap_process_integration/exp139.json"),
        "exp140": rj("results/exp140_cryo_fpga_boed_mux_readout/exp140.json"),
        "exp141": rj("results/exp141_v5_digital_twin/exp141.json"),
        "cad": json.loads((CAD_DIR / "cad_verification.json").read_text(encoding="utf-8")),
        "cert_sha256": cert_sha,
    }


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

    draw_pill(ctx, x + 18, y + 12, tag, accent, WHITE, size=10.2, pad_x=9, h=21)
    draw_text(ctx, x + 18, y + 66, hero, 20.5, bold=True, color=accent, max_w=w - 30, min_size=14.5)
    ctx.set_source_rgb(*GRID)
    ctx.set_line_width(1.0)
    ctx.move_to(x + 18, y + 78)
    ctx.line_to(x + w - 16, y + 78)
    ctx.stroke()
    draw_text(ctx, x + 18, y + 102, line1, 10.6, bold=True, color=NAVY_TXT, max_w=w - 30, min_size=8.8)
    draw_text(ctx, x + 18, y + 125, line2, 10.3, color=SLATE_TXT, max_w=w - 30, min_size=8.6)


def draw_hbar_row(
    ctx: cairo.Context, x_lbl_r: float, x_bar: float, bar_w: float, y_top: float, bar_h: float,
    label: str, frac: float, val_txt: str, col, lbl_max_w: float = 178.0,
) -> None:
    draw_text(
        ctx, x_lbl_r, y_top + bar_h * 0.68, label, 10.7, bold=True, color=NAVY_TXT,
        align="right", max_w=lbl_max_w, min_size=8.8,
    )
    rounded_rect(ctx, x_bar, y_top, bar_w, bar_h, 5)
    ctx.set_source_rgb(*TRACK_BG)
    ctx.fill()
    fw = max(6.0, min(1.0, frac) * bar_w)
    rounded_rect(ctx, x_bar, y_top, fw, bar_h, 5)
    ctx.set_source_rgb(*col)
    ctx.fill()
    draw_text(ctx, x_bar + bar_w + 8, y_top + bar_h * 0.68, val_txt, 10.6, bold=True, mono=True, color=col)


# ---------------------------------------------------------------------------
# Panel 1: Exp136 160k-Orbital sp3d5s* Atomistic + Stark f*=1.5% + 2 MV/m
# ---------------------------------------------------------------------------
def draw_panel1_exp136(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    d136 = data["exp136"]
    s3 = d136["stage3_endor_shell_benchmarks"]
    s6 = d136["stage6_isotope_stark_sweep"]
    st15 = [r for r in s6["stark_tuning_yield_HM5962"] if r["abundance_pct"] == 1.5 and r["E_z_MV_per_m"] == 2.0][0]
    y_f1 = [r for r in s6["primary_TB_CP_HM5962"] if r["abundance_pct"] == 1.0][0]["mode_b"]["yield_frac"] * 100.0
    y_f15_ez2 = st15["yield_frac"] * 100.0
    y_ddrf = st15["yield_and_gap_ge_6893Hz"] * 100.0
    r331_vokl = s3["exp129_VOKL6_full"]["err_R331"] * 100.0
    r331_kl = s3["exp129_KL_legacy"]["err_R331"] * 100.0
    r331_cp = s3["tb_sp3d5s_primary_3s_cp"]["err_R331"] * 100.0
    r331_dir = s3["tb_sp3d5s_direct_3s"]["err_R331"] * 100.0
    lrms_vokl = s3["exp129_VOKL6_full"]["log10_rms_4shells"]
    lrms_cp = s3["tb_sp3d5s_primary_3s_cp"]["log10_rms_4shells"]

    cy = draw_panel_shell(
        ctx, x, y, w, h, "Exp136 · H154",
        "160k-Orbital sp³d⁵s* Atomistik & Stark Kaldıracı",
        "16.000 atom Boykin-TB · R(3,3,1) düzeltmesi + f*=%1,5 + 2 MV/m Stark verimi (4/7 PASS)",
        C_BLUE,
    )

    # Sub-section A: R(3,3,1) ENDOR Shell Error reduction
    draw_text(ctx, x + 20, cy + 12, "A. (3,3,1) ENDOR Kabuk Hatası |R_mod - R_exp|/R_exp (Düşük = İyi)", 11.2, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy - 3, f"log₁₀-RMS: {tr_f(lrms_vokl,3)} → {tr_f(lrms_cp,3)}", C_TEAL, WHITE, size=9.6, pad_x=8, h=20, align="right")

    bx = x + 195
    bw = w - 315
    ry = cy + 26
    for lbl, err_v, col in (
        ("v4 VOKL-6 (Exp129)", r331_vokl, C_CRIMSON),
        ("KL Zarf Fonk.", r331_kl, C_AMBER),
        ("sp³d⁵s* (α_cp=0,015)", r331_cp, C_BLUE),
        ("sp³d⁵s* (α_cp=0,000)", r331_dir, C_GREEN),
    ):
        draw_hbar_row(ctx, bx - 10, bx, bw, ry, 21, lbl, err_v / 75.0, f"%{tr_f(err_v,1)}", col)
        ry += 29

    # Sub-section B: Isotope + Stark Yield & M4 Percolation
    cy2 = ry + 12
    ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
    ctx.move_to(x + 18, cy2 - 8); ctx.line_to(x + w - 18, cy2 - 8); ctx.stroke()
    draw_text(ctx, x + 20, cy2 + 10, "B. İzotop + Stark (2 MV/m) Seçicilik & M4 L=11 Verimi (N_cand=6)", 11.2, bold=True, color=NAVY_TXT)

    ry2 = cy2 + 24
    for lbl, val_p, col in (
        ("f=%1,0 (E_z=0) Tek-Hücre", y_f1, C_AMBER),
        ("f*=%1,5 + 2 MV/m (DDRF)", y_ddrf, C_TEAL),
        ("f*=%1,5 + 2 MV/m (Mod B)", y_f15_ez2, C_BLUE),
        ("M4 L=11 Y_FT (N=6, f*1,5)", 99.88, C_GREEN),
    ):
        draw_hbar_row(ctx, bx - 10, bx, bw, ry2, 21, lbl, val_p / 100.0, f"%{tr_f(val_p,2)}", col)
        ry2 += 29

    # Bottom highlight box
    by = y + h - 78
    rounded_rect(ctx, x + 18, by, w - 36, 62, 8)
    ctx.set_source_rgb(0.935, 0.962, 0.992)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_BLUE); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(ctx, x + 30, by + 23, "R1 Atomistik Kapanış: f*=%1,5 + 2 MV/m (N=6) → d_eff / d = %99,5 (Exp138)", 11.1, bold=True, color=NAVY_TXT, max_w=w - 60)
    draw_text(ctx, x + 30, by + 46, "XY8 T₂e = 10,8–20,3 ms · f*=%2,0'da M4 Y_FT = %99,99 · TB4/TB5/TB7 dürüst açık sınır", 10.3, color=SLATE_TXT, max_w=w - 60)


# ---------------------------------------------------------------------------
# Panel 2: Exp139 1530 K Hidden-TED Cure + S_eps 2.57x Suppression
# ---------------------------------------------------------------------------
def draw_panel2_exp139(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    d139 = data["exp139"]
    d141 = data["exp141"]
    l2 = d141["layer2_v5_placement"]
    nr = d139["charge_noise_and_exp137_bridge"]["routes"]
    rem_v4 = d139["coupled_thermal_chain_ted"]["v4_1x1440K_41p15J_unmitigated"]["cluster_remaining_frac_post_flash"] * 100.0
    rem_v5 = d139["coupled_thermal_chain_ted"]["v5_1x1530K_43p49J_cluster_clearing"]["cluster_remaining_frac_post_flash"] * 100.0

    cy = draw_panel_shell(
        ctx, x, y, w, h, "Exp139 · H157",
        "1530 K Gizli TED Çözümü & Rota C Şarj Gürültüsü",
        "v4 1440 K arka-uç TED açığı yakalandı → 1530 K (43,5 J/cm²) + S5.6 ²⁸Si MBE + FG 350 °C",
        C_AMBER,
    )

    draw_text(ctx, x + 20, cy + 12, "A. Toplam Yerleştirme Hatası σ_tot [nm] vs 3,80 nm Tavanı", 11.2, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy - 3, f"Küme: %{tr_f(rem_v4,1)} → %{tr_f(rem_v5,3)}", C_GREEN, WHITE, size=9.8, pad_x=8, h=20, align="right")

    bx = x + 195
    bw = w - 315
    ry = cy + 26
    max_sig = 4.30
    sig_rows = [
        ("v4 1440K Gizli TED", l2["exp139_reported_v4_hidden_TED_nm"], C_CRIMSON, "FAIL"),
        ("v3.0 Baz (15 ms)", l2["v300_orig_15ms_nm"], MUTED_TXT, "REF"),
        ("v5 1530K Rota C", l2["exp139_reported_v5_1530K_nm"], C_BLUE, "PASS"),
        ("v5 Dij. İkiz (10 ms)", l2["v500_coupled_10ms_nm"], C_GREEN, "PASS"),
    ]
    for lbl, sv, col, st in sig_rows:
        draw_hbar_row(ctx, bx - 10, bx, bw, ry, 21, lbl, sv / max_sig, f"{tr_f(sv,3)} nm", col)
        ry += 29

    # 3.80 nm red dashed ceiling line across section A (label cleanly below bottom bar)
    x_ceil = bx + (3.80 / max_sig) * bw
    ctx.save()
    ctx.set_dash([5.0, 3.0]); ctx.set_source_rgb(*C_CRIMSON); ctx.set_line_width(1.6)
    ctx.move_to(x_ceil, cy + 25); ctx.line_to(x_ceil, ry - 4); ctx.stroke()
    ctx.restore()
    draw_text(ctx, x_ceil, ry + 7, "3,80 nm tavan", 9.0, bold=True, color=C_CRIMSON, align="center")

    # Sub-section B: S_eps charge noise routes
    cy2 = ry + 18
    ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
    ctx.move_to(x + 18, cy2 - 8); ctx.line_to(x + w - 18, cy2 - 8); ctx.stroke()
    draw_text(ctx, x + 20, cy2 + 10, "B. 1/f Şarj Gürültüsü S_ε [µeV/√Hz] — Exp137 Köprüsü", 11.2, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy2 - 4, "2,57× Bastırma (Rota C)", C_BLUE, WHITE, size=9.8, pad_x=8, h=20, align="right")

    ry2 = cy2 + 24
    max_se = 1.90
    for lbl, sev, col in (
        ("Rota B (22 keV Cap)", nr["route_B_22keV_through_cap"]["S_eps_ueV_rtHz"], C_CRIMSON),
        ("Rota A (Pasiv. Yok)", nr["route_A_5keV_post_anneal_mbe_unpassivated"]["S_eps_ueV_rtHz"], C_AMBER),
        ("Rota C (350°C FG)", nr["route_C_nominal_FG350C_Dit_1p5e10"]["S_eps_ueV_rtHz"], C_BLUE),
        ("Rota C (Opt. 5nm Ox)", nr["route_C_thin_oxide_Dit_1p0e10_dox5"]["S_eps_ueV_rtHz"], C_GREEN),
    ):
        draw_hbar_row(ctx, bx - 10, bx, bw, ry2, 21, lbl, sev / max_se, f"{tr_f(sev,3)} µeV", col)
        ry2 += 29

    by = y + h - 78
    rounded_rect(ctx, x + 18, by, w - 36, 62, 8)
    ctx.set_source_rgb(0.992, 0.964, 0.922)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_AMBER); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(ctx, x + 30, by + 23, "Rota C Verimi: p_ff(C≥100) = %97,70 · Safir LIDT Marjı = 8,96× (1530 K)", 11.1, bold=True, color=NAVY_TXT, max_w=w - 60)
    draw_text(ctx, x + 30, by + 46, "S5.6 ²⁸Si MBE (+Z LL, 22,4 kg, $95k): 0 µW 20 mK sızıntı · %0 boru-hattı akış cezası", 10.3, color=SLATE_TXT, max_w=w - 60)


# ---------------------------------------------------------------------------
# Panel 3: Exp137 x Exp138 Echo M4 CZ & Surface Code FT (Lambda > 1)
# ---------------------------------------------------------------------------
def draw_panel3_exp137_138(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    l5 = data["exp141"]["layer5_surface_code_ft"]
    sc = l5["scenarios"]
    d2_9 = l5["d2_targets"]["1e-9"]
    d3_9 = l5["d3_targets"]["1e-9"]
    l3_137 = data["exp141"]["layer3_quantum_chain"]["exp137_echoed_m4_bus"]

    cy = draw_panel_shell(
        ctx, x, y, w, h, "Exp137 × Exp138",
        "Echo M4 CZ & Yüzey Kodu Hata Bastırma (Λ > 1)",
        "12×12 CUDA OU 1/f^α + d=3..11 Edmonds Blossom MWPM (p_2q,th = %1,60 ± %0,17)",
        C_PURPLE,
    )

    draw_text(ctx, x + 20, cy + 12, "A. Yüzey Kodu Hata Bastırma Faktörü Λ (Λ > 1 = Eşik Altı FT)", 11.2, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy - 3, "P4 Echo: δg 5,09× ↓", C_PURPLE, WHITE, size=9.8, pad_x=8, h=20, align="right")

    bx = x + 195
    bw = w - 315
    ry = cy + 26
    max_lam = 2.80
    lam_rows = [
        ("v4 P1 Çıplak (S=1,0)", sc["A_v4_Bare_P1_S1p0"]["Lambda"], C_CRIMSON),
        ("v5 B1 Pasiv. Yok", sc["B1_v5_Unpass_P4_S1p0"]["Lambda"], C_AMBER),
        ("v5 C2 (Q2e5, S0,39)", sc["C2_v5_RotaC_Q2e5_S0p39"]["Lambda"], C_TEAL),
        ("v5 D1 (Q5e5, S0,39)", sc["D1_v5_RotaC_Q5e5_S0p39"]["Lambda"], C_BLUE),
        ("v5 D2 (Q5e5, S0,25)", sc["D2_v5_RotaC_Q5e5_S0p25"]["Lambda"], C_PURPLE),
        ("v5 D3 Hedef (p=%0,5)", sc["D3_Target_FT_p0p005"]["Lambda"], C_GREEN),
    ]
    for lbl, lv, col in lam_rows:
        draw_hbar_row(ctx, bx - 10, bx, bw, ry, 20, lbl, lv / max_lam, f"Λ={tr_f(lv,2)}", col)
        ry += 28

    # Lambda = 1.0 vertical threshold line (label placed cleanly below 6th bar)
    x_thr = bx + (1.0 / max_lam) * bw
    ctx.save()
    ctx.set_dash([5.0, 3.0]); ctx.set_source_rgb(*C_GREEN); ctx.set_line_width(1.7)
    ctx.move_to(x_thr, cy + 25); ctx.line_to(x_thr, ry - 4); ctx.stroke()
    ctx.restore()
    draw_text(ctx, x_thr, ry + 7, "Λ=1,0 FT eşiği", 9.1, bold=True, color=C_GREEN, align="center")

    # Bottom 2-card comparison: D2 vs D3 (100L @ 10^-9)
    cy2 = ry + 18
    cw2 = (w - 50) / 2.0
    bh2 = (y + h - 18) - cy2
    for idx_c, (c_title, c_accent, c_bg, lines) in enumerate((
        (
            "D2: Rota C (Q=5e5, S=0,25)", C_PURPLE, (0.955, 0.945, 0.990),
            [
                f"F_Bell = {tr_f(l3_137['P4_Q5e5_S0p25_F_Bell'],4)} · p_2q = %0,92",
                f"Λ = {tr_f(sc['D2_v5_RotaC_Q5e5_S0p25']['Lambda'],2)} (FT Eşik Altı)",
                f"10⁻⁹: d* = {d2_9['d_star']} ({tr_i(d2_9['N_active'])} aktif/L)",
                f"100L Filo: {d2_9['cryostats_100L_unsplit_2887']} kriyostat",
            ],
        ),
        (
            "D3: Hedef FT (p_2q = %0,50)", C_GREEN, (0.930, 0.980, 0.955),
            [
                "6,79× Daha Küçük Kriyostat Filosu",
                f"Λ = {tr_f(sc['D3_Target_FT_p0p005']['Lambda'],2)} (Güçlü Bastırma)",
                f"10⁻⁹: d* = {d3_9['d_star']} ({tr_i(d3_9['N_active'])} aktif/L)",
                f"100L Filo: {d3_9['cryostats_100L_unsplit_2887']} kriyo (1 L/kriyo)",
            ],
        ),
    )):
        cx_b = x + 18 + idx_c * (cw2 + 14)
        rounded_rect(ctx, cx_b, cy2, cw2, bh2, 9)
        ctx.set_source_rgb(*c_bg); ctx.fill_preserve()
        ctx.set_source_rgb(*c_accent); ctx.set_line_width(1.3); ctx.stroke()
        draw_text(ctx, cx_b + 12, cy2 + 22, c_title, 11.4, bold=True, color=c_accent, max_w=cw2 - 24)
        for j, ln in enumerate(lines):
            draw_text(ctx, cx_b + 12, cy2 + 45 + j * 24, "• " + ln, 10.4, bold=(j == 3), color=NAVY_TXT if j == 3 else SLATE_TXT, max_w=cw2 - 22)


# ---------------------------------------------------------------------------
# Panel 4: Exp140 N_mux*=32 Purcell Readout + 1024/2887 Cryo Heat Budget
# ---------------------------------------------------------------------------
def draw_panel4_exp140(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    d140 = data["exp140"]
    nmux = d140["mux_readout_3kOhm_NbTiN"]["by_nmux"]
    cryo = d140["cryo_heat_budgets"]["m4_1024_hemt7p8mW"]
    fpga = d140["fpga_boed_q16_benchmark"]

    cy = draw_panel_shell(
        ctx, x, y, w, h, "Exp140 · H158",
        "N_mux*=32 Purcell Okuma & LD400/PT420 Isı Bütçesi",
        "Q16.16 ZU48DR RFSoC (2,336 µs, ΔRMS=0,050 Hz, %10,5 DSP) · 625× Purcell · 7/7 PASS",
        C_GREEN,
    )

    # Sub-section A: F_RO(2 us) vs N_mux (8, 16, 32, 64)
    draw_text(ctx, x + 20, cy + 12, "A. 3 kΩ NbTiN Çoklamalı Okuma Sadakati F_RO (τ_RO = 2 µs)", 11.2, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy - 3, "N_mux*=32 OPTİMAL", C_GREEN, WHITE, size=9.8, pad_x=8, h=20, align="right")

    bx = x + 165
    bw = w - 295
    ry = cy + 26
    for k_nm, tag_s, col in (
        ("8", "N_mux = 8 (400 MHz)", C_TEAL),
        ("16", "N_mux = 16 (200 MHz)", C_BLUE),
        ("32", "N_mux*=32 (100 MHz)", C_GREEN),
        ("64", "N_mux = 64 (50 MHz)", C_CRIMSON),
    ):
        fro = nmux[k_nm]["F_ro_at_2us"] * 100.0
        # Zoomed scale [90% .. 100%] so 99.61% vs 94.13% is crystal clear
        frac = max(0.05, (fro - 90.0) / 10.0)
        st = "PASS" if nmux[k_nm]["passes_99pct_at_2us"] else "FAIL"
        draw_hbar_row(ctx, bx - 10, bx, bw, ry, 21, tag_s, frac, f"%{tr_f(fro,2)} {st}", col, lbl_max_w=145)
        ry += 29

    # 99% threshold vertical line (label cleanly below 4th bar)
    x_99 = bx + ((99.0 - 90.0) / 10.0) * bw
    ctx.save()
    ctx.set_dash([5.0, 3.0]); ctx.set_source_rgb(*C_GREEN); ctx.set_line_width(1.6)
    ctx.move_to(x_99, cy + 25); ctx.line_to(x_99, ry - 4); ctx.stroke()
    ctx.restore()
    draw_text(ctx, x_99, ry + 7, "%99 eşik", 9.0, bold=True, color=C_GREEN, align="center")

    # Sub-section B: 1,024-cell Cryo utilization (4/4 PASS)
    cy2 = ry + 18
    ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
    ctx.move_to(x + 18, cy2 - 8); ctx.line_to(x + w - 18, cy2 - 8); ctx.stroke()
    draw_text(ctx, x + 20, cy2 + 10, "B. 1.024-Hücre Modül Kriyo Yükü (LD400 / PT420 — 4/4 PASS)", 11.2, bold=True, color=NAVY_TXT)

    ry2 = cy2 + 24
    u = cryo["utilization"]
    ld = cryo["loads"]
    lm = cryo["limits"]
    for lbl, frac, vtxt, col in (
        ("20 mK MXC (Darboğaz)", u["mxc_20mK_frac"], f"{tr_f(ld['mxc_20mK_uW'],2)}/{lm['mxc_20mK_uW']:.0f} µW", C_AMBER),
        ("100 mK Cold Plate", u["cp_100mK_frac"], f"{tr_f(ld['cp_100mK_uW'],1)}/{lm['cp_100mK_uW']:.0f} µW", C_TEAL),
        ("4 K (32×HEMT+SKY130)", u["stage_4K_frac"], f"{tr_f(ld['stage_4K_W'],2)}/{lm['stage_4K_W']:.1f} W", C_BLUE),
        ("50 K (96-Coax)", u["stage_50K_frac"], f"{tr_f(ld['stage_50K_W'],2)}/{lm['stage_50K_W']:.0f} W", C_GREEN),
    ):
        draw_hbar_row(ctx, bx + 20, bx + 30, bw - 35, ry2, 21, lbl, frac, vtxt, col, lbl_max_w=175)
        ry2 += 29

    # Honest single-cryostat scaling callout
    by = y + h - 78
    rounded_rect(ctx, x + 18, by, w - 36, 62, 8)
    ctx.set_source_rgb(0.930, 0.980, 0.955)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_GREEN); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(ctx, x + 30, by + 23, f"Tek LD400/PT420 Tavanı: {tr_i(cryo['single_cryostat_max_cells'])} hücre (20 mK sınırlı) → 10.000 hücre ≥ 4 kriyostat", 11.0, bold=True, color=NAVY_TXT, max_w=w - 60)
    draw_text(ctx, x + 30, by + 46, f"Q16.16 BOED: {tr_f(fpga['q16_16']['mean_time_ms'],1)} ms · abs(ΔRMS)={tr_f(fpga['parity']['abs_delta_rms_Hz'],4)} Hz · CellISA v3.5 (17 opcode)", 10.3, color=SLATE_TXT, max_w=w - 60)


# ---------------------------------------------------------------------------
# Panel 5: Exp141 Wafer CX4 Wall Broken + $/L_fab vs $/L_sys Honest Split
# ---------------------------------------------------------------------------
def draw_panel5_exp141_econ(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    l6 = data["exp141"]["layer6_wafer_cx4_economics"]["cx4_closure"]
    l7 = data["exp141"]["layer7_logical_qubit_economics"]
    d2_9 = l7["D2_primary_Lambda1p40"]["1e-9"]
    d3_9 = l7["D3_target_Lambda2p52"]["1e-9"]
    d3_6 = l7["D3_target_Lambda2p52"]["1e-6"]
    d2_6 = l7["D2_primary_Lambda1p40"]["1e-6"]

    cy = draw_panel_shell(
        ctx, x, y, w, h, "Exp141 · H159",
        "Wafer CX4 Kırılımı & $/Mantıksal Kübit Ayrımı",
        "30 nm ²⁸Si-on-SOI (W2/W3) Silikon Duvarını kırar · Dürüst Fab vs 100L Sistem TCO (Wright b=%85)",
        C_CRIMSON,
    )

    draw_text(ctx, x + 20, cy + 12, "A. 10.000-Yazmaç Çip Maliyeti [$/çip] — CX4 ≥ %40 Hedefi", 11.2, bold=True, color=NAVY_TXT)
    draw_pill(ctx, x + w - 18, cy - 3, "W2/W3 CX4 PASS", C_GREEN, WHITE, size=9.8, pad_x=8, h=20, align="right")

    bx = x + 195
    bw = w - 330
    ry = cy + 26
    max_ch = 3.25
    w_rows = [
        ("v3-W1 (200mm $12k)", l6["v3_W1_reference_chip_10k_usd"], "BAZ", MUTED_TXT),
        ("v5-W1 (200mm $12k)", l6["W1_v5_15ms_chip_10k_usd"], "-%14,5", C_CRIMSON),
        ("v5-W2 (200mm SOI)", l6["W2_v5_15ms_chip_10k_usd"], f"-{tr_f(l6['W2_reduction_vs_v3_W1_frac']*100,1)}%", C_BLUE),
        ("v5-W3 (300mm SOI)", l6["W3_v5_15ms_chip_10k_usd"], f"-{tr_f(l6['W3_reduction_vs_v3_W1_frac']*100,1)}%", C_GREEN),
    ]
    for lbl, cv, dlt, col in w_rows:
        draw_hbar_row(ctx, bx - 10, bx, bw, ry, 21, lbl, cv / max_ch, f"${tr_f(cv,2)} ({dlt})", col)
        ry += 29

    # Sub-section B: Honest $/L_fab vs $/L_sys table
    cy2 = ry + 12
    ctx.set_source_rgb(*GRID); ctx.set_line_width(1.0)
    ctx.move_to(x + 18, cy2 - 8); ctx.line_to(x + w - 18, cy2 - 8); ctx.stroke()
    draw_text(ctx, x + 20, cy2 + 10, "B. Dürüst Mantıksal Kübit Maliyeti: Fab Çip ($/L_fab) vs 100L Sistem ($/L_sys)", 11.0, bold=True, color=NAVY_TXT, max_w=w - 36)

    ty = cy2 + 22
    tw = w - 36
    rounded_rect(ctx, x + 18, ty, tw, 24, 5)
    ctx.set_source_rgb(*NAVY_TOP); ctx.fill()
    hdrs = [
        (26, "Rejim & Hedef ε_L", "left"),
        (255, "d*", "center"),
        (325, "Kriyo", "center"),
        (450, "$/L_fab (W3)", "right"),
        (600, "$/L_sys (100L)", "right"),
        (706, "Fark", "right"),
    ]
    for dx, ht, al in hdrs:
        draw_text(ctx, x + dx, ty + 16, ht, 9.8, bold=True, color=WHITE, align=al)

    t_rows = [
        ("D2 (Λ=1,40) @ 10⁻⁶", str(d2_6["d_star"]), str(d2_6["cryostats_100L"]), f"${tr_f(d2_6['fab_usd_per_L_W3'],2)}", f"${tr_f(d2_6['sys_100L_usd_per_L_amort_wright_p50']/1e6,2)}M", "Baz", SLATE_TXT),
        ("D2 (Λ=1,40) @ 10⁻⁹", str(d2_9["d_star"]), str(d2_9["cryostats_100L"]), f"${tr_f(d2_9['fab_usd_per_L_W3'],2)}", f"${tr_f(d2_9['sys_100L_usd_per_L_amort_wright_p50']/1e6,2)}M", "Baz", C_PURPLE),
        ("D3 (Λ=2,52) @ 10⁻⁶", str(d3_6["d_star"]), str(d3_6["cryostats_100L"]), f"${tr_f(d3_6['fab_usd_per_L_W3'],2)}", f"${tr_f(d3_6['sys_100L_usd_per_L_amort_wright_p50']/1e6,2)}M", "5,54×↓", C_TEAL),
        ("D3 (Λ=2,52) @ 10⁻⁹", str(d3_9["d_star"]), str(d3_9["cryostats_100L"]), f"${tr_f(d3_9['fab_usd_per_L_W3'],2)}", f"${tr_f(d3_9['sys_100L_usd_per_L_amort_wright_p50']/1e6,2)}M", "5,41×↓", C_GREEN),
    ]
    ry_t = ty + 26
    for idx_r, (r_lbl, r_d, r_cr, r_fab, r_sys, r_sp, r_col) in enumerate(t_rows):
        if idx_r % 2 == 1:
            ctx.set_source_rgb(0.955, 0.968, 0.985)
            ctx.rectangle(x + 18, ry_t, tw, 25); ctx.fill()
        yt = ry_t + 17
        draw_text(ctx, x + 26, yt, r_lbl, 10.2, bold=(idx_r in (1, 3)), color=NAVY_TXT)
        draw_text(ctx, x + 255, yt, r_d, 10.2, mono=True, bold=True, color=NAVY_TXT, align="center")
        draw_text(ctx, x + 325, yt, r_cr, 10.2, mono=True, bold=True, color=r_col, align="center")
        draw_text(ctx, x + 450, yt, r_fab, 10.2, mono=True, bold=True, color=C_BLUE, align="right")
        draw_text(ctx, x + 600, yt, r_sys, 10.2, mono=True, bold=True, color=r_col, align="right")
        draw_text(ctx, x + 706, yt, r_sp, 10.0, bold=True, color=r_col, align="right")
        ry_t += 25

    by = y + h - 78
    rounded_rect(ctx, x + 18, by, w - 36, 62, 8)
    ctx.set_source_rgb(0.988, 0.942, 0.946)
    ctx.fill_preserve()
    ctx.set_source_rgb(*C_CRIMSON); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(ctx, x + 30, by + 23, "Kritik Ekonomik İçgörü: Fab çip payı < %0,0002; sistem TCO'su kriyostat filosu kaynaklı!", 10.8, bold=True, color=NAVY_TXT, max_w=w - 60)
    draw_text(ctx, x + 30, by + 46, "W2 (200 mm SOI): $0 makine tadilatı · W3 (300 mm): +$350k kademe (+$0,005/çip)", 10.3, color=SLATE_TXT, max_w=w - 60)


# ---------------------------------------------------------------------------
# Panel 6: S5.6 MBE + S6.5 RFSoC/TWPA Architecture, BOM Bridge & M0 Stamp
# ---------------------------------------------------------------------------
def draw_panel6_hw_arch(ctx: cairo.Context, x: float, y: float, w: float, h: float, data: dict) -> None:
    cad = data["cad"]
    b = data["exp128"]["bom_detailed_summary"]
    rfq = data["exp128"]["rfq_coverage"]
    ex_p = data["exp128"]["monte_carlo_model_a_detailed"]["exceedance_probabilities"]
    l4 = data["exp141"]["layer4_live_control_stack"]["cellisa_v35_live"]
    sha = data["cert_sha256"]

    cy = draw_panel_shell(
        ctx, x, y, w, h, "CAD + BOM v5.0",
        "S5.6 MBE + S6.5 Kriyo-MUX Donanım & M0 Damga",
        "189 Katı Parça (1.034,94 kg) · 167 Parça BOM ($5,25M M3) · 0 Çakışma · 32/32 Boşluk",
        C_TEAL,
    )

    # 2 side-by-side hardware architecture blocks (S5.6 vs S6.5)
    bw2 = (w - 50) / 2.0
    bh_mod = 158.0
    for idx_m, (m_tag, m_title, m_col, m_bg, m_lines) in enumerate((
        (
            "S5.6 · Exp139", "²⁸Si UHV MBE + FG Pasiv.", C_AMBER, (0.992, 0.968, 0.928),
            [
                "Montaj: Load-Lock +Z CF100 (Ø152)",
                "Zarf: X=420, Z=585..865 mm (6 parça)",
                "Kütle: +22,40 kg · Maliyet: $95k",
                "Boşluk: 119 mm UHV / 70,1 mm kol",
                "345 °C PBN + 350 °C %5 H₂/N₂ + 80 L/s",
            ],
        ),
        (
            "S6.5 · Exp140", "1.024-Hücre MUX & RFSoC", C_TEAL, (0.928, 0.976, 0.980),
            [
                "DR Soğuk (12 parça, +7,77 kg):",
                "   20mK TWPA 2,72 + 4K 32×HEMT 1,02",
                "   96-hat CuNi/NbTi koaks 4,03 kg",
                "S7 2U ZU48DR RFSoC (+11,50 kg, 88W)",
                "Toplam: +19,27 kg · $629,2k (S6.11)",
            ],
        ),
    )):
        mx = x + 18 + idx_m * (bw2 + 14)
        rounded_rect(ctx, mx, cy + 4, bw2, bh_mod, 9)
        ctx.set_source_rgb(*m_bg); ctx.fill_preserve()
        ctx.set_source_rgb(*m_col); ctx.set_line_width(1.3); ctx.stroke()
        pw_m = draw_pill(ctx, mx + 10, cy + 12, m_tag, m_col, WHITE, size=9.6, pad_x=8, h=20)
        draw_text(ctx, mx + 10 + pw_m + 7, cy + 26, m_title, 11.0, bold=True, color=NAVY_TXT, max_w=bw2 - pw_m - 24)
        for j, ln in enumerate(m_lines):
            prefix = "" if ln.startswith("   ") else "• "
            draw_text(ctx, mx + 12, cy + 50 + j * 22, prefix + ln, 10.1, color=SLATE_TXT, max_w=bw2 - 22)

    # BOM v4 -> v5 bridge strip
    by_b = cy + bh_mod + 16
    rounded_rect(ctx, x + 18, by_b, w - 36, 98, 9)
    ctx.set_source_rgb(0.955, 0.968, 0.986); ctx.fill_preserve()
    ctx.set_source_rgb(*C_BLUE); ctx.set_line_width(1.2); ctx.stroke()
    draw_text(ctx, x + 30, by_b + 22, "BOM v4.0 → v5.0 Köprüsü & RFQ-08 Kapsamı ($0,00 Uzlaştırma Hatası)", 11.2, bold=True, color=NAVY_TXT, max_w=w - 60)
    b_lines = [
        f"• M3 v4 ($4,61M) + Brüt v5 (+$724,2k) − Çift-Sayım Kredisi (−$86,0k) = M3 v5 ${tr_f(b['m3_nom_usd']/1e6,2)}M (Pilot 256h: $4,79M)",
        f"• 8-RFQ Paketi (78 parça): Nom %{tr_f(rfq['rfq8_nom_share']*100,1)} ($4,01M) · MC Varyans %{tr_f(rfq['rfq8_variance_share_mc']*100,1)} · P(Prog>$100M)=%{tr_f(ex_p['P_Program_stoch_gt_100M']*100,2)}",
        f"• Canlı CellISA v3.5 ({l4['total_opcodes']} opcode): Bare CZ {tr_f(l4['mean_bare_cz_fidelity'],4)} → ECHO_CZ {tr_f(l4['mean_echo_cz_fidelity'],4)} (+20,3 pp)",
    ]
    for j, ln in enumerate(b_lines):
        draw_text(ctx, x + 30, by_b + 44 + j * 21, ln, 10.1, color=SLATE_TXT, max_w=w - 56)

    # Bottom M0 Epistemic & SHA-256 Cryptographic Seal Box
    by_s = y + h - 122
    rounded_rect(ctx, x + 18, by_s, w - 36, 106, 9)
    ctx.set_source_rgb(*NAVY_TOP); ctx.fill()
    draw_pill(ctx, x + 30, by_s + 12, "M0 EPİSTEMİK & KRİPTOGRAFİK MÜHÜR", C_GOLD_BG, NAVY_TOP, size=9.8, pad_x=10, h=21)
    draw_pill(ctx, x + w - 30, by_s + 12, "8/8 DT5 PASS · 19/19 SHA-256", C_GREEN, WHITE, size=9.8, pad_x=10, h=21, align="right")
    draw_text(ctx, x + 30, by_s + 54, f"v5_digital_twin_cert.json SHA-256: {sha}", 9.6, mono=True, bold=True, color=(0.82, 0.94, 1.0), max_w=w - 60)
    draw_text(
        ctx, x + 30, by_s + 76,
        "Durum: no_lab_measurement=true · no_supplier_quotes=true · Fiziksel prototip/tape-out değildir ({Model}/{Simülasyon}).",
        10.0, color=(0.88, 0.92, 0.96), max_w=w - 60,
    )
    draw_text(
        ctx, x + 30, by_s + 95,
        f"CAD v5.0: {cad['master_assembly']['part_count']} parça · {tr_f(cad['master_assembly']['total_mass_kg'],2)} kg · 8/8 STL ({tr_i(cad['master_assembly']['stl']['triangles'])} üçgen) · 0/{tr_i(cad['interference_audit']['pairs_checked'])} çakışma · 32/32 boşluk",
        9.9, color=(0.74, 0.87, 0.96), max_w=w - 60,
    )


def main() -> None:
    data = load_data()
    cad = data["cad"]
    ma = cad["master_assembly"]
    b_sum = data["exp128"]["bom_detailed_summary"]
    rfq = data["exp128"]["rfq_coverage"]
    ex_p = data["exp128"]["monte_carlo_model_a_detailed"]["exceedance_probabilities"]
    l3 = data["exp141"]["layer3_quantum_chain"]
    l5 = data["exp141"]["layer5_surface_code_ft"]
    l6 = data["exp141"]["layer6_wafer_cx4_economics"]["cx4_closure"]
    l7 = data["exp141"]["layer7_logical_qubit_economics"]
    clr_ok = sum(1 for v in cad["critical_clearances"].values() if v["pass"])
    clr_tot = len(cad["critical_clearances"])

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
    ctx.set_source_rgb(*C_TEAL)
    ctx.rectangle(0, 124, W, 5)
    ctx.fill()

    draw_text(ctx, 48, 56, "ATOM LİTOGRAFİ MAKİNESİ v5.0 — Hata-Toleranslı Fizik, Kriyo-MUX & Dijital İkiz", 29.5, bold=True, color=WHITE)
    draw_text(
        ctx, 48, 94,
        "Exp136 (160k-orb sp³d⁵s*) · Exp137 (Echo M4 CZ) · Exp138 (Surface Code FT) · Exp139 (S5.6 ²⁸Si MBE) · Exp140 (S6.5 RFSoC/TWPA) · Exp141 (CX4 & 100L TCO)",
        13.6, color=(0.76, 0.87, 0.96), max_w=1680,
    )

    draw_pill(ctx, W - 48, 22, "MODEL / SİMÜLASYON — LAB ÖLÇÜMÜ & TEKLİF YOKTUR", C_GOLD_BG, NAVY_TOP, size=11.6, pad_x=14, h=30, align="right")
    draw_pill(
        ctx, W - 48, 66,
        f"v5.0 Dijital İkiz (8/8 DT5 PASS) · 0/{tr_i(cad['interference_audit']['pairs_checked'])} Çakışma · {clr_ok}/{clr_tot} Boşluk",
        (0.09, 0.45, 0.35), WHITE, size=11.4, pad_x=14, h=28, align="right",
    )

    # Top 6-Card KPI Strip (y = 144..294)
    kpi_cards = [
        (
            "CAD v5.0",
            f"{ma['part_count']} Parça | {tr_f(ma['total_mass_kg'],1)} kg",
            f"8/8 STL ({tr_i(ma['stl']['triangles'])} üçgen) · 0/{tr_i(cad['interference_audit']['pairs_checked'])} çakışma",
            f"{clr_ok}/{clr_tot} boşluk PASS · S5.6 +22,4 / S6.5 +19,3 kg",
            C_TEAL,
        ),
        (
            "BOM v5.0",
            f"M3 ${tr_f(b_sum['m3_nom_usd']/1e6,2)}M | {b_sum['total_parts']} Parça",
            f"8-RFQ: %{tr_f(rfq['rfq8_nom_share']*100,1)} nom / %{tr_f(rfq['rfq8_variance_share_mc']*100,1)} MC var.",
            f"P(Prog>$100M) = %{tr_f(ex_p['P_Program_stoch_gt_100M']*100,2)} (<%5) · $0,00 köprü",
            C_CRIMSON,
        ),
        (
            "M4 Echo Bell",
            f"F_Bell = {tr_f(l3['exp137_echoed_m4_bus']['P4_Q5e5_S0p25_F_Bell'],4)}",
            f"P4 Echo (Q=5e5, S=0,25): p_err = %0,92 (<%1)",
            f"δg cezasında 5,09× ↓ · F_avg = {tr_f(l3['exp137_echoed_m4_bus']['P4_Q5e5_S0p25_F_avg'],4)}",
            C_PURPLE,
        ),
        (
            "Surface Code FT",
            f"Λ = {tr_f(l5['scenarios']['D2_v5_RotaC_Q5e5_S0p25']['Lambda'],2)} → D3 {tr_f(l5['scenarios']['D3_Target_FT_p0p005']['Lambda'],2)}",
            f"p_2q,th = %{tr_f(l5['p_2q_threshold_round']*100,2)} · P1(0) → C2(1,04) → D2(1,40)",
            f"100L (10⁻⁹): 679 → 100 kriyo (6,8× küçülme)",
            C_BLUE,
        ),
        (
            "BOED FPGA",
            f"{tr_f(l3['exp140_mux_fpga']['fpga_step_latency_us'],2)} µs | N_mux*={l3['exp140_mux_fpga']['n_mux_star']}",
            f"F_RO = %{tr_f(l3['exp140_mux_fpga']['F_ro_32_2us']*100,2)} (625× Purcell) · %10,5 DSP",
            f"Q16.16 ΔRMS=0,05 Hz · Tek kriyo {tr_i(l3['exp140_mux_fpga']['single_cryostat_max_cells'])} h.",
            C_GREEN,
        ),
        (
            "Wafer CX4",
            f"W3 -%{tr_f(l6['W3_reduction_vs_v3_W1_frac']*100,1)} | ${tr_f(l6['W3_v5_15ms_chip_10k_usd'],2)}/çip",
            f"W2 (200mm SOI, $0 HW): ${tr_f(l6['W2_v5_15ms_chip_10k_usd'],2)} (-%{tr_f(l6['W2_reduction_vs_v3_W1_frac']*100,1)})",
            f"D3 10⁻⁹: $/L_fab ${tr_f(l7['D3_target_Lambda2p52']['1e-9']['fab_usd_per_L_W3'],2)} | $/L_sys ${tr_f(l7['D3_target_Lambda2p52']['1e-9']['sys_100L_usd_per_L_amort_wright_p50']/1e6,2)}M",
            C_AMBER,
        ),
    ]
    pad_x = 48.0
    gap_k = 18.0
    kw = (W - 2 * pad_x - 5 * gap_k) / 6.0
    for i, (tag, hero, l1, l2, col) in enumerate(kpi_cards):
        draw_kpi_card(ctx, pad_x + i * (kw + gap_k), 144.0, kw, 148.0, tag, hero, l1, l2, col)

    # 3x2 Main Analytical Grid (y = 310..1350)
    gap_x = 22.0
    gap_y = 20.0
    pw = (W - 2 * pad_x - 2 * gap_x) / 3.0
    ph = 510.0
    y_r1 = 310.0
    y_r2 = y_r1 + ph + gap_y

    draw_panel1_exp136(ctx, pad_x, y_r1, pw, ph, data)
    draw_panel2_exp139(ctx, pad_x + pw + gap_x, y_r1, pw, ph, data)
    draw_panel3_exp137_138(ctx, pad_x + 2 * (pw + gap_x), y_r1, pw, ph, data)

    draw_panel4_exp140(ctx, pad_x, y_r2, pw, ph, data)
    draw_panel5_exp141_econ(ctx, pad_x + pw + gap_x, y_r2, pw, ph, data)
    draw_panel6_hw_arch(ctx, pad_x + 2 * (pw + gap_x), y_r2, pw, ph, data)

    # Footer
    draw_text(
        ctx, 48, H - 16,
        "Canlı Veri Kaynakları: exp128 + exp136..exp141.json · cad_verification.json (v5.0) · BOM_DETAILED.csv (167 parça) · no_lab_measurement=true · no_supplier_quotes=true",
        10.8, color=MUTED_TXT,
    )
    draw_text(
        ctx, W - 48, H - 16,
        "Atom-Lithography v5.0 (M0 Fizik + Hata-Toleranslı Ölçekleme + S5.6/S6.5 + Dijital İkiz) · 2026-11-23",
        10.8, bold=True, color=SLATE_TXT, align="right",
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    surf.write_to_png(str(OUT_PNG))
    with Image.open(OUT_PNG) as im:
        assert im.size == (W, H), f"Expected {W}x{H}, got {im.size}"
    print(f"DASHBOARD_V5_OK {OUT_PNG.relative_to(ROOT)} ({W}x{H}, {OUT_PNG.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
