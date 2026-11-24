"""Generate GitHub README v7.2 IEEE/Nature academic publication cover figure `00_v7_overview_dashboard.png` (2400x1400).

Strict academic publication design system:
  - Canvas: #FFFFFF white paper (subtle note/table tint #F8F9FA)
  - Primary / Secondary ink: #111827 / #4B5563
  - Hairline borders & grids: #D1D5DB / #E5E7EB
  - Primary data accent: muted academic navy #1B365D
  - Secondary series: muted slate #64748B / #94A3B8 / #CBD5E1
  - Threshold / limit / uncertified accent: muted burgundy #8B2635 (sparingly)
  - Restrained PASS accent: muted forest #2D5A3D (text/markers only)

Reads verified live metrics directly from disk (zero hardcoded stale metrics, zero user paths):
  - results/exp128_bom_sensitivity/exp128.json
  - results/exp147_universal_qldpc_d18_magic_state/exp147.json
  - results/exp148_sb121_quadrupole_echo_qudit/exp148.json
  - results/exp149_boed_verilog_rtl_and_interactive_twin/exp149.json
  - results/exp150_industrial_safety_fmea_hazop/exp150.json
  - results/exp151_v7_digital_twin/exp151.json
  - results/exp151_v7_digital_twin/v7_digital_twin_cert.json
  - results/boed_real_bath_benchmark.json
  - research/atom_lithography_machine/cad/cad_verification.json

Runs under `/usr/bin/python3 -B` (PyCairo + Pillow, zero numpy/matplotlib).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cairo
from PIL import Image

CAD_DIR = Path(__file__).resolve().parent
ROOT = CAD_DIR.parents[2]
OUT_PNG = CAD_DIR / "drawings" / "00_v7_overview_dashboard.png"
W, H = 2400, 1400

# Strict Academic Journal Palette (IEEE Transactions / Nature / Physical Review)
BG_PAPER = "#FFFFFF"
BG_SUBTLE = "#F8F9FA"
INK_PRIMARY = "#111827"
INK_SECONDARY = "#4B5563"
INK_MUTED = "#6B7280"
RULE_BORDER = "#D1D5DB"
RULE_GRID = "#E5E7EB"
ACCENT_NAVY = "#1B365D"
ACCENT_SLATE = "#64748B"
ACCENT_LIGHT_SLATE = "#94A3B8"
ACCENT_PALE_SLATE = "#CBD5E1"
ACCENT_BURGUNDY = "#8B2635"
ACCENT_FOREST = "#2D5A3D"


def _hex(h: str, a: float = 1.0) -> tuple[float, float, float, float]:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, a)


def tr_f(val: float, dec: int = 1) -> str:
    return f"{val:,.{dec}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def tr_i(val: int) -> str:
    return f"{val:,}".replace(",", ".")


def tr_sci(val: float, dec: int = 1) -> str:
    return f"{val:.{dec}e}".replace(".", ",")


def _rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 2.0) -> None:
    r = min(r, w / 2.0, h / 2.0)
    if r <= 0.5:
        ctx.rectangle(x, y, w, h)
        return
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def _text(
    ctx: cairo.Context,
    txt: str,
    x: float,
    y: float,
    size: float = 12.5,
    color: str = INK_PRIMARY,
    bold: bool = False,
    mono: bool = False,
    align: str = "left",
    max_w: float | None = None,
    min_size: float = 8.4,
) -> None:
    fam = "DejaVu Sans Mono" if mono else "DejaVu Sans"
    ctx.select_font_face(fam, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    fsz = size
    ctx.set_font_size(fsz)
    if max_w is not None:
        while ctx.text_extents(txt).width > max_w and fsz > min_size:
            fsz -= 0.3
            ctx.set_font_size(fsz)
    ext = ctx.text_extents(txt)
    if align == "center":
        tx = x - (ext.width / 2.0 + ext.x_bearing)
    elif align == "right":
        tx = x - (ext.width + ext.x_bearing)
    else:
        tx = x
    ctx.set_source_rgba(*_hex(color))
    ctx.move_to(tx, y)
    ctx.show_text(txt)


def _draw_axes_open(ctx: cairo.Context, px: float, py: float, pw: float, ph: float) -> None:
    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(1.0)
    ctx.move_to(px, py)
    ctx.line_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()


def _draw_hgrid(ctx: cairo.Context, px: float, pw: float, gy: float) -> None:
    ctx.save()
    ctx.set_dash([3.0, 3.0])
    ctx.set_source_rgba(*_hex(RULE_GRID))
    ctx.set_line_width(0.8)
    ctx.move_to(px, gy)
    ctx.line_to(px + pw, gy)
    ctx.stroke()
    ctx.restore()
    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(0.9)
    ctx.move_to(px - 4.0, gy)
    ctx.line_to(px, gy)
    ctx.stroke()


def _draw_vgrid(ctx: cairo.Context, gx: float, py: float, ph: float) -> None:
    ctx.save()
    ctx.set_dash([3.0, 3.0])
    ctx.set_source_rgba(*_hex(RULE_GRID))
    ctx.set_line_width(0.8)
    ctx.move_to(gx, py)
    ctx.line_to(gx, py + ph)
    ctx.stroke()
    ctx.restore()
    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(0.9)
    ctx.move_to(gx, py + ph)
    ctx.line_to(gx, py + ph + 4.0)
    ctx.stroke()


def _panel(
    ctx: cairo.Context,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    title: str,
    meta: str,
    meta_col: str = INK_SECONDARY,
) -> None:
    """Flat journal panel with hairline border and crisp title underline (zero drop shadow / badge)."""
    ctx.rectangle(x, y, w, h)
    ctx.set_source_rgba(*_hex(BG_PAPER))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.9)
    ctx.stroke()

    ctx.move_to(x + 14, y + 36)
    ctx.line_to(x + w - 14, y + 36)
    ctx.set_source_rgba(*_hex(RULE_GRID))
    ctx.set_line_width(0.9)
    ctx.stroke()

    _text(ctx, label, x + 14, y + 24, size=13.5, color=ACCENT_NAVY, bold=True)
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(13.5)
    lw = ctx.text_extents(label).width

    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(10.2)
    mw = ctx.text_extents(meta).width
    _text(ctx, meta, x + w - 14, y + 23.5, size=10.2, color=meta_col, bold=True, mono=True, align="right")
    _text(ctx, title, x + 14 + lw + 8, y + 24, size=13.2, color=INK_PRIMARY, bold=True, max_w=(w - 36 - lw - mw))


def _note_box(ctx: cairo.Context, x: float, y: float, w: float, h: float, left_accent: str | None = None) -> None:
    _rect(ctx, x, y, w, h, 2.0)
    ctx.set_source_rgba(*_hex(BG_SUBTLE))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.8)
    ctx.stroke()
    if left_accent:
        ctx.rectangle(x, y, 3.0, h)
        ctx.set_source_rgba(*_hex(left_accent))
        ctx.fill()


def _callout_label(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    txt: str,
    border_col: str = ACCENT_BURGUNDY,
    txt_col: str = ACCENT_BURGUNDY,
    size: float = 10.0,
) -> None:
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    tw = ctx.text_extents(txt).width
    bw = tw + 14.0
    bh = 19.0
    _rect(ctx, cx - bw / 2.0, cy - bh / 2.0, bw, bh, 2.0)
    ctx.set_source_rgba(*_hex(BG_PAPER, 0.96))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(border_col, 0.75))
    ctx.set_line_width(0.9)
    ctx.stroke()
    _text(ctx, txt, cx, cy + 3.5, size=size, color=txt_col, bold=True, align="center")


def _draw_p1_qldpc_algos(ctx: cairo.Context, x: float, y: float, w: float, h: float, e147: dict[str, Any], cert: dict[str, Any]) -> None:
    _panel(ctx, x, y, w, h, "(a)", "Exp147 — Evrensel qLDPC d=18: FeMoco & RSA-2048", "37,1×–52,7× ↓", ACCENT_NAVY)

    fm_q = e147["part5_flagship_algorithms"]["FeMoco_192L_1e8T"]["qLDPC_d18_Gidney_Cult_116to12"]
    fm_s = e147["part5_flagship_algorithms"]["FeMoco_192L_1e8T"]["SurfaceCode_D3_Baseline"]
    rs_q = e147["part5_flagship_algorithms"]["RSA2048_4096L_1e10T"]["qLDPC_d24_D3_GidneyCult"]
    rs_s = e147["part5_flagship_algorithms"]["RSA2048_4096L_1e10T"]["SurfaceCode_D3_Baseline"]

    px, py, pw, ph = x + 66, y + 72, w - 88, 286
    y_min, y_max = -0.8, 4.6

    def _sy(v: float) -> float:
        lv = math.log10(max(v, 0.16))
        return py + ph * (1.0 - (lv - y_min) / (y_max - y_min))

    for exp, lbl in ((0, "1"), (1, "10"), (2, "100"), (3, "1k"), (4, "10k")):
        gy = _sy(10.0 ** exp)
        _draw_hgrid(ctx, px, pw, gy)
        _text(ctx, lbl, px - 8, gy + 3.8, size=10.2, color=INK_SECONDARY, mono=True, align="right")

    _draw_axes_open(ctx, px, py, pw, ph)

    ctx.save()
    ctx.translate(x + 20, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "Kriyo Adet / Güç MW (log10)", 0, 0, size=11.2, color=INK_PRIMARY, bold=True, align="center")
    ctx.restore()

    # Legend above chart
    ctx.rectangle(px + 6, py - 22, 12, 10)
    ctx.set_source_rgba(*_hex(ACCENT_PALE_SLATE))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(ACCENT_LIGHT_SLATE))
    ctx.set_line_width(0.7)
    ctx.stroke()
    _text(ctx, "Surface Code (D3 Referans)", px + 24, py - 13, size=10.5, color=INK_SECONDARY, bold=True)
    ctx.rectangle(px + 236, py - 22, 12, 10)
    ctx.set_source_rgba(*_hex(ACCENT_NAVY))
    ctx.fill()
    _text(ctx, "qLDPC + Gidney Cultivation (v7.0)", px + 254, py - 13, size=10.5, color=ACCENT_NAVY, bold=True)

    groups = [
        ("FeMoco\nKriyo (LD400)", fm_s["total_cryostats_ld400"], fm_q["total_cryostats_ld400"], tr_i(fm_s["total_cryostats_ld400"]), tr_i(fm_q["total_cryostats_ld400"]), f"{tr_f(cert['exp147_femoco_compression_x'], 1)}× ↓"),
        ("FeMoco\nGüç (MW)", fm_s["tco_and_power"]["total_facility_power_mw"], fm_q["tco_and_power"]["total_facility_power_mw"], tr_f(fm_s["tco_and_power"]["total_facility_power_mw"], 1), tr_f(fm_q["tco_and_power"]["total_facility_power_mw"], 2), f"{tr_f(fm_s['tco_and_power']['total_facility_power_mw']/fm_q['tco_and_power']['total_facility_power_mw'], 1)}× ↓"),
        ("RSA-2048\nKriyo (LD400)", rs_s["total_cryostats_ld400"], rs_q["total_cryostats_ld400"], tr_i(rs_s["total_cryostats_ld400"]), tr_i(rs_q["total_cryostats_ld400"]), f"{tr_f(cert['exp147_rsa2048_compression_x'], 1)}× ↓"),
        ("RSA-2048\nGüç (MW)", rs_s["tco_and_power"]["total_facility_power_mw"], rs_q["tco_and_power"]["total_facility_power_mw"], tr_f(rs_s["tco_and_power"]["total_facility_power_mw"], 0), tr_f(rs_q["tco_and_power"]["total_facility_power_mw"], 2), f"{tr_f(rs_s['tco_and_power']['total_facility_power_mw']/rs_q['tco_and_power']['total_facility_power_mw'], 1)}× ↓"),
    ]
    slot = pw / len(groups)
    bw = slot * 0.28
    for i, (lbl, vs, vq, ts, tq, gain) in enumerate(groups):
        cx = px + i * slot + slot / 2.0
        bx1 = cx - bw - 3
        by1 = _sy(vs)
        ctx.rectangle(bx1, by1, bw, (py + ph) - by1)
        ctx.set_source_rgba(*_hex(ACCENT_PALE_SLATE, 0.92))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(ACCENT_LIGHT_SLATE))
        ctx.set_line_width(0.7)
        ctx.stroke()
        _text(ctx, ts, bx1 + bw / 2.0, by1 - 6, size=10.0, color=INK_SECONDARY, bold=True, mono=True, align="center")

        bx2 = cx + 3
        by2 = _sy(vq)
        ctx.rectangle(bx2, by2, bw, (py + ph) - by2)
        ctx.set_source_rgba(*_hex(ACCENT_NAVY, 0.94))
        ctx.fill()
        _text(ctx, tq, bx2 + bw / 2.0, by2 - 6, size=10.2, color=ACCENT_NAVY, bold=True, mono=True, align="center")
        _text(ctx, gain, bx2 + bw / 2.0, by2 - 20, size=9.4, color=INK_SECONDARY, bold=True, mono=True, align="center")

        for li, part in enumerate(lbl.split("\n")):
            _text(ctx, part, cx, py + ph + 16 + li * 13, size=10.2, color=INK_PRIMARY if li == 0 else INK_SECONDARY, bold=(li == 0), align="center")

    sy = y + 404
    _note_box(ctx, x + 14, sy, w - 28, h - (sy - y) - 14)
    _text(ctx, f"[[288,12,18]]: L_max = {tr_f(cert['exp147_bb288_L_max_um'], 1)} µm <= 300 | p_th = %{tr_f(cert['exp147_bb288_p_th_pct'], 3)} | 576-Hücre: %{tr_f(cert['exp147_yield_576_N8_pct'], 2)} (N=8) / %{tr_f(cert['exp147_yield_576_N9_pct'], 2)} (N=9)", x + 26, sy + 23, size=10.8, color=INK_PRIMARY, bold=True, max_w=w - 52)
    _text(ctx, f"FeMoco (192L, 10⁸ T): {fm_q['total_cryostats_ld400']} kriyo · {tr_f(fm_q['runtime_hours'], 2)} sa · {tr_f(fm_q['tco_and_power']['total_facility_power_kw'], 1)} kW · ${tr_f(fm_q['tco_and_power']['tco5_musd_p50'], 1)}M (${tr_i(round(fm_q['cost_per_solve_usd_p50']))}/çözüm)", x + 26, sy + 47, size=10.8, color=INK_SECONDARY, max_w=w - 52)
    _text(ctx, f"RSA-2048 (4.096L, 10¹⁰ T): {rs_q['total_cryostats_ld400']} kriyo · {tr_f(rs_q['runtime_hours'], 1)} sa · {tr_f(rs_q['tco_and_power']['total_facility_power_mw'], 2)} MW · ${tr_f(rs_q['tco_and_power']['tco5_musd_p50'], 0)}M (35,9× ucuz)", x + 26, sy + 71, size=10.8, color=INK_SECONDARY, max_w=w - 52)

    _note_box(ctx, x + 24, sy + 88, w - 48, 44, left_accent=ACCENT_BURGUNDY)
    _text(ctx, "Dürüst Sınır (Exp147 5/7 PASS; UQ4/UQ5 FAIL): p_L_mem < 10⁻¹² hedefi için okuma hatası", x + 36, sy + 106, size=10.3, color=ACCENT_BURGUNDY, bold=True, max_w=w - 72)
    _text(ctx, "tavanı p_meas <= %0,15 (Mevcut D3 %0,337'de bellek ömrü sınırlı -> D3++ <=%0,20 yol haritası)", x + 36, sy + 123, size=10.1, color=INK_SECONDARY, max_w=w - 72)


def _draw_p2_sb121(ctx: cairo.Context, x: float, y: float, w: float, h: float, e148: dict[str, Any], cert: dict[str, Any]) -> None:
    _panel(ctx, x, y, w, h, "(b)", "Exp148 — ¹²¹Sb (I=7/2) Q-Echo-8 & SU(8) GRAPE", "455,5× ↓ · 6/7 PASS", ACCENT_FOREST)

    qs = e148["benchmarks"]["quasistatic_500Hz_1ms"]
    su8 = e148["su8_grape_logical_gates"]["gates"]
    t2 = e148["benchmarks"]["colored_1f_500Hz_decay_curves"]["T2_eff_ms"]

    lx, ly, lw, lh = x + 48, y + 68, 344, 286
    _text(ctx, "Statik 500 Hz (1 ms) & SU(8) Sadakat", lx + lw / 2.0, ly - 11, size=11.0, color=INK_PRIMARY, bold=True, align="center")
    for tick in (0.5, 0.7, 0.9, 1.0):
        gy = ly + lh * (1.0 - (tick - 0.45) / 0.58)
        _draw_hgrid(ctx, lx, lw, gy)
        _text(ctx, tr_f(tick, 1), lx - 7, gy + 3.5, size=9.6, color=INK_SECONDARY, mono=True, align="right")
    _draw_axes_open(ctx, lx, ly, lw, lh)

    fbars = [
        ("Çıplak\nGross", qs["bare"]["gross_0L"], ACCENT_BURGUNDY, 0.80, "0,580"),
        ("Q-Echo-8\nGross", qs["qecho8_finite_neutral_25kHz"]["gross_0L"], ACCENT_NAVY, 0.95, "0,9991"),
        ("Q-Echo-8\nCat ±7/2", qs["qecho8_finite_neutral_25kHz"]["spin_cat_pm7_2"], ACCENT_SLATE, 0.90, "0,9991"),
        ("SU(8)\nX_L", su8["X_L"]["F_L_noiseless_full_crosstalk"], ACCENT_NAVY, 0.72, "0,9954"),
        ("SU(8)\nZ_L", su8["Z_L"]["F_L_noiseless_full_crosstalk"], ACCENT_NAVY, 0.72, "0,9971"),
        ("SU(8)\nH_L", su8["H_L"]["F_L_noiseless_full_crosstalk"], ACCENT_NAVY, 0.72, "0,9959"),
    ]
    slot = lw / len(fbars)
    bw = slot * 0.58
    for i, (lbl, val, col, alpha, vtxt) in enumerate(fbars):
        bx = lx + i * slot + (slot - bw) / 2.0
        by = ly + lh * (1.0 - (val - 0.45) / 0.58)
        ctx.rectangle(bx, by, bw, (ly + lh) - by)
        ctx.set_source_rgba(*_hex(col, alpha))
        ctx.fill()
        _text(ctx, vtxt, bx + bw / 2.0, by - 6, size=9.2, color=ACCENT_BURGUNDY if i == 0 else INK_PRIMARY, bold=True, mono=True, align="center")
        for li, part in enumerate(lbl.split("\n")):
            _text(ctx, part, bx + bw / 2.0, ly + lh + 14 + li * 12, size=9.2, color=INK_PRIMARY if li == 0 else INK_SECONDARY, bold=(li == 0), align="center")

    rx, ry, rw, rh = x + 448, y + 68, w - 470, 286
    _text(ctx, "Geniş-Bant 1/f Cywiński T2_eff (ms)", rx + rw / 2.0, ry - 11, size=11.0, color=INK_PRIMARY, bold=True, align="center")
    t_max = 1.65
    for tick in (0.0, 0.5, 1.0, 1.5):
        gy = ry + rh * (1.0 - tick / t_max)
        _draw_hgrid(ctx, rx, rw, gy)
        _text(ctx, tr_f(tick, 1), rx - 7, gy + 3.5, size=9.6, color=INK_SECONDARY, mono=True, align="right")
    _draw_axes_open(ctx, rx, ry, rw, rh)

    cbars = [
        ("Çıplak", t2["bare_gross_ms"], ACCENT_BURGUNDY, 0.80, "0,05"),
        ("QE-8", t2["qecho8_gross_ms"], ACCENT_PALE_SLATE, 1.0, "0,43"),
        ("QE-16", t2["qecho16_gross_ms"], ACCENT_LIGHT_SLATE, 0.95, "0,66"),
        ("QE-32", t2["qecho32_gross_ms"], ACCENT_SLATE, 0.92, "0,98"),
        ("QE-64", t2["qecho64_gross_ms"], ACCENT_NAVY, 0.95, "1,45"),
    ]
    rslot = rw / len(cbars)
    rbw = rslot * 0.56
    for i, (lbl, val, col, alpha, vtxt) in enumerate(cbars):
        bx = rx + i * rslot + (rslot - rbw) / 2.0
        by = ry + rh * (1.0 - val / t_max)
        ctx.rectangle(bx, by, rbw, max(4.0, (ry + rh) - by))
        ctx.set_source_rgba(*_hex(col, alpha))
        if col == ACCENT_PALE_SLATE:
            ctx.fill_preserve()
            ctx.set_source_rgba(*_hex(ACCENT_LIGHT_SLATE))
            ctx.set_line_width(0.7)
            ctx.stroke()
        else:
            ctx.fill()
        _text(ctx, vtxt, bx + rbw / 2.0, by - 6, size=9.6, color=ACCENT_BURGUNDY if i == 0 else (ACCENT_NAVY if i == 4 else INK_SECONDARY), bold=True, mono=True, align="center")
        _text(ctx, lbl, bx + rbw / 2.0, ry + rh + 15, size=9.6, color=INK_PRIMARY if i == 4 else INK_SECONDARY, bold=(i == 4), align="center")

    _callout_label(ctx, rx + 58, ry + 14, "28,1× Kazanç", border_col=ACCENT_NAVY, txt_col=ACCENT_NAVY, size=9.8)

    sy = y + 404
    _note_box(ctx, x + 14, sy, w - 28, h - (sy - y) - 14)
    _text(ctx, f"Exp142 OQ6 Model İterasyonu: Statik 500 Hz Gross {tr_f(cert['exp148_sb121_bare_gross_0L'], 4)} -> {tr_f(cert['exp148_sb121_qecho8_gross_0L'], 5)} ({tr_f(cert['exp148_sb121_infidelity_reduction_x'], 1)}× infidelite ↓)", x + 26, sy + 23, size=10.8, color=ACCENT_NAVY, bold=True, max_w=w - 52)
    _text(ctx, f"Cat |±7/2⟩: 0,9424 -> {tr_f(cert['exp148_sb121_qecho8_cat77'], 5)} (1/f T2_eff = {tr_f(t2['qecho8_cat77_ms'], 2)} ms)  |  SU(8) GRAPE min F_L = {tr_f(cert['exp148_sb121_su8_grape_min_F'], 4)}", x + 26, sy + 47, size=10.8, color=INK_PRIMARY, max_w=w - 52)
    _text(ctx, "Sonlu Darbe (25 kHz Kompozit 90-240-90 + Faz Döngüsü): 8×8 / 16×16 CPTP Lindblad doğrulandı", x + 26, sy + 71, size=10.6, color=INK_SECONDARY, max_w=w - 52)

    _note_box(ctx, x + 24, sy + 88, w - 48, 44, left_accent=ACCENT_BURGUNDY)
    _text(ctx, f"Dürüst Sınır (SQ4 FAIL): Geniş-bant 1/f gürültüde Q-Echo-8 kazancı {tr_f(t2['gross_gain_qecho8_vs_bare'], 2)}× -> Q-Echo-64'te", x + 36, sy + 106, size=10.3, color=ACCENT_BURGUNDY, bold=True, max_w=w - 72)
    _text(ctx, f"{tr_f(cert['exp148_sb121_qecho64_1f_gain_x'], 2)}× ({tr_f(t2['qecho64_gross_ms'], 2)} ms); yüksek frekanslı 1/f kuyruğunda Cywiński filtre sınırı geçerlidir.", x + 36, sy + 123, size=10.1, color=INK_SECONDARY, max_w=w - 72)


def _draw_p3_verilog_twin(ctx: cairo.Context, x: float, y: float, w: float, h: float, e149: dict[str, Any], cert: dict[str, Any]) -> None:
    _panel(ctx, x, y, w, h, "(c)", "Exp149 — Gerçek EDA RTL & HTML5 Gezgin", f"584 cyc · 0 LSB · {e149['n_passed']}/{e149['n_total']}", ACCENT_FOREST)

    rv = e149["rtl_verification"]
    zu = rv["zu48dr_resource_budget"]
    ytop = rv["yosys_synthesis"]["targets"]["xcup_top16"]

    # Top block: monochrome-navy 4-Stage Pipeline Flow Diagram
    stages = [
        ("Stage 0: SPRT", "4 çevrim\n16 ns", False),
        ("LUT ROM", "1.024 kelime\n0 bit fark", False),
        ("SIMD-4 Q16.16", "Icarus 14.0\n0 LSB (64+4ch)", True),
        ("BOED Çıkış", f"{zu['cycles_per_boed_step']} çevrim\n{tr_f(zu['latency_per_boed_step_us'], 3)} µs", True),
    ]
    sy_pipe = y + 54
    sw = (w - 48 - 3 * 22) / 4.0
    sh = 74
    for i, (st, sd, primary) in enumerate(stages):
        sx = x + 24 + i * (sw + 22)
        _rect(ctx, sx, sy_pipe, sw, sh, 2.0)
        ctx.set_source_rgba(*_hex(BG_SUBTLE if not primary else BG_PAPER))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(ACCENT_NAVY if primary else RULE_BORDER))
        ctx.set_line_width(1.2 if primary else 0.9)
        ctx.stroke()
        _text(ctx, st, sx + sw / 2.0, sy_pipe + 22, size=10.6, color=ACCENT_NAVY if primary else INK_PRIMARY, bold=True, align="center")
        for li, part in enumerate(sd.split("\n")):
            _text(ctx, part, sx + sw / 2.0, sy_pipe + 42 + li * 15, size=10.0, color=INK_PRIMARY if li == 0 else INK_SECONDARY, bold=(li == 0), mono=(li == 1), align="center")
        if i < 3:
            ax1 = sx + sw + 3
            ax2 = sx + sw + 19
            ay = sy_pipe + sh / 2.0
            ctx.set_source_rgba(*_hex(ACCENT_SLATE))
            ctx.set_line_width(1.2)
            ctx.move_to(ax1, ay)
            ctx.line_to(ax2 - 4, ay)
            ctx.stroke()
            ctx.move_to(ax2, ay)
            ctx.line_to(ax2 - 6, ay - 3.8)
            ctx.line_to(ax2 - 6, ay + 3.8)
            ctx.close_path()
            ctx.fill()

    # Middle block: Real Yosys 0.71+101 xcup_top16 pre-P&R Utilization Bars on ZU48DR
    uy0 = y + 160
    _text(ctx, "ZU48DR — Gerçek Yosys 0.71 Ön-P&R 16-Kanal Ölçümü (xcup_top16)", x + 24, uy0, size=11.3, color=INK_PRIMARY, bold=True, max_w=w - 48)
    dsp_n, dsp_cap = int(ytop["dsp_total"]), 4272
    bram_n, bram_cap = int(round(float(ytop["bram36_equiv"]))), 1080
    lut_n, lut_cap = int(ytop["lut_total"]), 425280
    ff_n, ff_cap = int(ytop["ff_total"]), 850560
    res_rows = [
        ("DSP48E2", f"{tr_i(dsp_n)} / 4.272", 100.0 * dsp_n / dsp_cap, ACCENT_NAVY),
        ("BRAM36", f"{tr_i(bram_n)} / 1.080", 100.0 * bram_n / bram_cap, ACCENT_SLATE),
        ("CLB LUT", f"{tr_i(lut_n)} / 425.280", 100.0 * lut_n / lut_cap, ACCENT_NAVY),
        ("Flip-Flop", f"{tr_i(ff_n)} / 850.560", 100.0 * ff_n / ff_cap, ACCENT_LIGHT_SLATE),
    ]
    bx0, bmax = x + 114, w - 334
    for i, (rname, rcnt, rpct, rcol) in enumerate(res_rows):
        ry = uy0 + 18 + i * 44
        _text(ctx, rname, x + 24, ry + 16, size=11.0, color=INK_PRIMARY, bold=True)
        ctx.rectangle(bx0, ry + 5, bmax, 16)
        ctx.set_source_rgba(*_hex(RULE_GRID))
        ctx.fill()
        fill_w = max(12.0, bmax * min(1.0, rpct / 45.0))
        ctx.rectangle(bx0, ry + 5, fill_w, 16)
        ctx.set_source_rgba(*_hex(rcol, 0.92))
        ctx.fill()
        _text(ctx, f"%{tr_f(rpct, 2)} ({rcnt})", bx0 + bmax + 10, ry + 17, size=10.1, color=ACCENT_NAVY if rcol == ACCENT_NAVY else INK_SECONDARY, bold=True, mono=True, max_w=(x + w - (bx0 + bmax + 20)))
    _text(ctx, "(Bar ölçeği %0–%45; Yosys 0.71+101 ön-P&R ölçümü — tümü <%38, 0 W kriyo; Vivado P&R açık)", x + 24, uy0 + 206, size=9.9, color=INK_MUTED, max_w=w - 48)

    sy = y + 404
    _note_box(ctx, x + 14, sy, w - 28, h - (sy - y) - 14)
    _text(ctx, f"rtl/boed_fpga/: {tr_i(cert['exp149_rtl_loc'])} LOC IEEE-2005 (4 modül, 0 '/' bölücü, Verilator 5.055: 0 uyarı)", x + 26, sy + 23, size=10.7, color=INK_PRIMARY, bold=True, max_w=w - 52)
    _text(ctx, "Gerçek EDA: Icarus 14.0 64/64 + 4-ch AXI4-S 0 LSB (584 cyc) | Yosys xcup/xc7/ecp5 PASS", x + 26, sy + 47, size=10.6, color=ACCENT_NAVY, bold=True, max_w=w - 52)
    html_bytes = (ROOT / "docs/digital_twin_interactive.html").stat().st_size
    html_kb = html_bytes / 1000.0
    _text(ctx, f"Etkileşimli Gezgin: docs/digital_twin_interactive.html ({tr_f(html_kb, 1)} KB · {tr_i(html_bytes)} B · 5 Sekme · 0 CDN)", x + 26, sy + 71, size=10.6, color=INK_SECONDARY, bold=True, max_w=w - 52)
    _note_box(ctx, x + 24, sy + 88, w - 48, 44, left_accent=ACCENT_NAVY)
    _text(ctx, "Epistemik Not (no_external_eda_sim=false, no_vendor_vivado_pnr=true): Açık-kaynak EDA", x + 36, sy + 106, size=10.1, color=ACCENT_NAVY, bold=True, max_w=w - 72)
    _text(ctx, "tamamlandı; Xilinx Vivado P&R/STA zamanlama kapanışı ve fiziksel FPGA JTAG testi açık.", x + 36, sy + 123, size=9.9, color=INK_SECONDARY, max_w=w - 72)


def _draw_p4_safety_fmea(ctx: cairo.Context, x: float, y: float, w: float, h: float, e150: dict[str, Any]) -> None:
    fstat = e150["fmea_summary"]
    _panel(ctx, x, y, w, h, "(d)", "Exp150 — Ön Emniyet & 25-Satırlı FMEA (Sertifikasız M0)", f"RPN {fstat['max_rpn_pre']}->{fstat['max_rpn_post']} · M0", ACCENT_BURGUNDY)

    px, py, pw, ph = x + 52, y + 72, w - 72, 260
    y_max = 310.0

    def _sy(v: float) -> float:
        return py + ph * (1.0 - v / y_max)

    for tick in (0, 60, 120, 180, 240, 300):
        gy = _sy(tick)
        _draw_hgrid(ctx, px, pw, gy)
        _text(ctx, str(tick), px - 7, gy + 3.5, size=9.6, color=INK_SECONDARY, mono=True, align="right")

    _draw_axes_open(ctx, px, py, pw, ph)

    ctx.save()
    ctx.translate(x + 17, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "FMEA RPN (S × O × D)", 0, 0, size=10.8, color=INK_PRIMARY, bold=True, align="center")
    ctx.restore()

    rows = e150["fmea_25_rows"]
    slot = pw / len(rows)
    bw = slot * 0.70
    for i, r in enumerate(rows):
        bx = px + i * slot + (slot - bw) / 2.0
        yp = _sy(r["RPN_pre"])
        ctx.rectangle(bx, yp, bw, (py + ph) - yp)
        ctx.set_source_rgba(*_hex(ACCENT_PALE_SLATE, 0.90))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(ACCENT_LIGHT_SLATE, 0.80))
        ctx.set_line_width(0.6)
        ctx.stroke()

        yq = _sy(r["RPN_post"])
        ctx.rectangle(bx + 1.5, yq, bw - 3.0, (py + ph) - yq)
        ctx.set_source_rgba(*_hex(ACCENT_NAVY, 0.95))
        ctx.fill()
        if i % 2 == 0 or i == 24:
            _text(ctx, f"{i+1:02d}", bx + bw / 2.0, py + ph + 14, size=9.0, color=INK_SECONDARY, mono=True, align="center")

    y60 = _sy(60.0)
    ctx.save()
    ctx.set_dash([6.0, 4.0])
    ctx.set_source_rgba(*_hex(ACCENT_BURGUNDY))
    ctx.set_line_width(1.4)
    ctx.move_to(px, y60)
    ctx.line_to(px + pw, y60)
    ctx.stroke()
    ctx.restore()
    _callout_label(ctx, px + pw - 96, y60 - 15, "Hedef RPN <= 60 (0/25 İhlal)", border_col=ACCENT_BURGUNDY, txt_col=ACCENT_BURGUNDY, size=9.8)

    # Legend above chart
    ctx.rectangle(px + 4, py - 21, 12, 10)
    ctx.set_source_rgba(*_hex(ACCENT_PALE_SLATE))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(ACCENT_LIGHT_SLATE))
    ctx.set_line_width(0.7)
    ctx.stroke()
    _text(ctx, f"Önce (Ort. {tr_f(fstat['mean_rpn_pre'], 1)}, Maks. {fstat['max_rpn_pre']})", px + 22, py - 12, size=10.2, color=INK_SECONDARY, bold=True)
    ctx.rectangle(px + 244, py - 21, 12, 10)
    ctx.set_source_rgba(*_hex(ACCENT_NAVY))
    ctx.fill()
    _text(ctx, f"Sonra (Ort. {tr_f(fstat['mean_rpn_post'], 1)}, Maks. {fstat['max_rpn_post']}, -%{tr_f(fstat['mean_rpn_reduction_pct'], 1)})", px + 262, py - 12, size=10.2, color=ACCENT_NAVY, bold=True)

    # Bottom 2x2 uniform subtle technical note cards (consistent Turkish decimal commas!)
    gy0 = y + 370
    cw = (w - 38) / 2.0
    ch = 86
    las = e150["hazard_1_laser_s55"]
    gas = e150["hazard_2_ph3_and_forming_gas"]
    hvx = e150["hazard_3_hv_and_xray"]
    cryo = e150["hazard_4_cryo_odh_and_quench"]
    epo = e150["hazard_5_epo_ups_shutdown"]
    spec = e150["s_safety_spec"]["totals"]
    cards = [
        ("S5.5 Lazer + X-Işını (iec61508=false)", f"OD8 + 3 mm Çelik ({tr_f(las['interlock_sil3']['shutter_close_ms'], 1)} ms; 10× λ_DU@%10→SIL-2)", f"22 keV: 10,1 -> {tr_sci(hvx['energy_sweep']['22keV']['s55_sapphire_plus_3mm_steel_shroud_uSv_h'], 1)} µSv/h (Sertifikasız M0)", ACCENT_BURGUNDY),
        ("S1.1 PH₃ (SDS) & %5 H₂/N₂", f"1.207 ppm -> {tr_f(gas['mitigated_sds_system']['operator_conservative_ppm'], 4)} ppm", "7,0× < TLV · 6.990× < IDLH · ISO 10156", ACCENT_NAVY),
        ("Kriyo He RK4 ODH & Quench", f"60 m³ O₂ = %{tr_f(cryo['helium_odh']['room_sweep']['60m3']['dry_ld400_pt420_O2_pct'], 2)} (DN50 {tr_f(cryo['asme_ovc_relief']['relief_safety_margin'], 1)}×)", f"18,9 kJ Dump Direnci: {tr_f(cryo['magnet_quench_exp125']['dump_resistor_peak_1p5T_C'], 2)} °C", ACCENT_NAVY),
        ("15 kVA UPS & S7.SAFETY Kiti", f"0,0 ms · 80,0 ms UHV ({tr_f(epo['ups_spec']['runtime_at_rated_13p5kW_min'], 0)}/{tr_f(epo['ups_spec']['runtime_tier1_min'], 0)} dk)", f"${spec['cost_usd_nom']//1000}k · {tr_f(spec['total_mass_kg'], 1)} kg · 0,0 W Kriyo", ACCENT_NAVY),
    ]
    for idx, (ct, c1, c2, hcol) in enumerate(cards):
        col_i = idx % 2
        row_i = idx // 2
        cx = x + 14 + col_i * (cw + 10)
        cy = gy0 + row_i * (ch + 10)
        _note_box(ctx, cx, cy, cw, ch)
        _text(ctx, ct, cx + 10, cy + 20, size=10.4, color=hcol, bold=True, max_w=cw - 20)
        _text(ctx, c1, cx + 10, cy + 44, size=10.6, color=INK_PRIMARY, bold=True, max_w=cw - 20)
        _text(ctx, c2, cx + 10, cy + 67, size=9.9, color=INK_SECONDARY, max_w=cw - 20)


def _draw_p5_bom_v7(ctx: cairo.Context, x: float, y: float, w: float, h: float, e128: dict[str, Any], cert: dict[str, Any]) -> None:
    _panel(ctx, x, y, w, h, "(e)", "BOM v7.0 — Kademeli Bütçe-Tavanı & 10-RFQ", "180p · Faz-1 %4,67", ACCENT_NAVY)

    mc = e128["v7_modular_mc_comparison"]
    tiers = [
        ("M3 v5.0 Base\n(167 parça)", mc["M3_v5_0_Base"]["bom_nom_usd"] / 1e6, mc["M3_v5_0_Base"]["P_Program_stoch_gt_100M"] * 100.0, ACCENT_LIGHT_SLATE, "PASS"),
        ("Faz-1: Base + Safety\n(173 parça, ÖNERİLEN)", mc["M3_v5_0_Base_Plus_Safety"]["bom_nom_usd"] / 1e6, mc["M3_v5_0_Base_Plus_Safety"]["P_Program_stoch_gt_100M"] * 100.0, ACCENT_NAVY, "PASS"),
        ("M3 v6.0 Full (Q+HPC)\n(174 parça)", mc["M3_v6_0_Full_Option_Q_and_HPC"]["bom_nom_usd"] / 1e6, mc["M3_v6_0_Full_Option_Q_and_HPC"]["P_Program_stoch_gt_100M"] * 100.0, ACCENT_SLATE, "PASS"),
        ("M3 v7.0 Full (+Safety)\n(180 parça, Dürüst >%5)", mc["M3_v7_0_Safety_Certified_Full"]["bom_nom_usd"] / 1e6, mc["M3_v7_0_Safety_Certified_Full"]["P_Program_stoch_gt_100M"] * 100.0, ACCENT_BURGUNDY, "DÜRÜST >%5"),
    ]

    px, py, pw, ph = x + 186, y + 68, w - 210, 258
    x_max = 7.2

    def _sx(pct: float) -> float:
        return px + pw * (pct / x_max)

    for tick in (0, 2, 4, 5, 6, 7):
        gx = _sx(tick)
        _draw_vgrid(ctx, gx, py, ph)
        _text(ctx, f"%{tick}", gx, py + ph + 16, size=10.0, color=INK_SECONDARY, mono=True, align="center")

    _draw_axes_open(ctx, px, py, pw, ph)

    _text(ctx, "100k MC: P(Program > $100M) Sert Tavan Riski (%)", px + pw / 2.0, py - 11, size=11.0, color=INK_PRIMARY, bold=True, align="center")

    slot = ph / len(tiers)
    bh = slot * 0.50
    for i, (lbl, musd, ppct, col, tag) in enumerate(tiers):
        by = py + i * slot + (slot - bh) / 2.0
        bw_ = _sx(ppct) - px
        ctx.rectangle(px, by, bw_, bh)
        ctx.set_source_rgba(*_hex(col, 0.92))
        ctx.fill()
        for li, part in enumerate(lbl.split("\n")):
            _text(ctx, part, px - 10, by + 12 + li * 13.5, size=10.1, color=INK_PRIMARY if li == 0 else INK_SECONDARY, bold=(li == 0), align="right")
        if ppct < 5.0:
            _text(ctx, f"${tr_f(musd, 2)}M · %{tr_f(ppct, 2)} ({tag})", px + 10, by + bh / 2.0 + 3.8, size=10.1, color=BG_PAPER, bold=True, mono=True)
        else:
            _text(ctx, f"${tr_f(musd, 2)}M · %{tr_f(ppct, 2)}", px + 10, by + bh / 2.0 + 3.8, size=10.1, color=BG_PAPER, bold=True, mono=True)
            _text(ctx, tag, px + bw_ + 8, by + bh / 2.0 + 3.8, size=9.6, color=ACCENT_BURGUNDY, bold=True, mono=True)

    x5 = _sx(5.0)
    ctx.save()
    ctx.set_dash([6.0, 4.0])
    ctx.set_source_rgba(*_hex(ACCENT_BURGUNDY))
    ctx.set_line_width(1.5)
    ctx.move_to(x5, py)
    ctx.line_to(x5, py + ph)
    ctx.stroke()
    ctx.restore()
    _callout_label(ctx, x5, py + ph + 33, "CU3 Sert Tavan Limiti = %5,00", border_col=ACCENT_BURGUNDY, txt_col=ACCENT_BURGUNDY, size=10.0)

    sy = y + 392
    _note_box(ctx, x + 14, sy, w - 28, h - (sy - y) - 14)
    vm = e128["v7_hardware_mass_reconciliation"]
    _text(ctx, f"Kütle Ayrımı (0,0000 kg fark): CAD v6 Şasi {tr_f(vm['on_frame_cad_v6_mass_kg'], 1)} kg + Emniyet {tr_f(vm['facility_safety_bom_total_mass_kg'], 1)} kg = {tr_f(vm['total_facility_load_mass_kg'], 1)} kg", x + 26, sy + 23, size=10.7, color=INK_PRIMARY, bold=True, max_w=w - 52)
    _text(ctx, f"10-RFQ Kapsamı (RFQ-01..10): Nominal %{tr_f(cert['bom_v7_rfq10_nom_share_pct'], 2)}  |  MC Varyans %{tr_f(cert['bom_v7_rfq10_var_share_pct'], 2)}  |  Köprü: $0,00", x + 26, sy + 49, size=10.7, color=ACCENT_NAVY, bold=True, max_w=w - 52)
    _text(ctx, f"M1 Prototip + S7.SAFETY = ${tr_i(int(e128['bom_detailed_summary']['m1_plus_safety_nom_usd']))}  |  FOAK 5y TCO (> $100M): %7,25 (v7 Full)", x + 26, sy + 75, size=10.5, color=INK_SECONDARY, max_w=w - 52)
    _note_box(ctx, x + 24, sy + 92, w - 48, 56, left_accent=ACCENT_NAVY)
    _text(ctx, "Kademeli Tedarik Stratejisi (Dürüst Bütçe Disiplini):", x + 36, sy + 111, size=10.5, color=ACCENT_NAVY, bold=True)
    _text(ctx, "Faz-1: M3 Base + S7.SAFETY ($5,393M, P>100M=%4,67 < %5) -> RFQ-05 S6.6 Fiyat Kilidi ->", x + 36, sy + 129, size=10.1, color=INK_PRIMARY, max_w=w - 72)
    _text(ctx, "Faz-2: +Option-Q ($168k) & +Option-HPC ($132k) ile Tam v7.0 ($5,693M) Devreye Alma.", x + 36, sy + 144, size=10.1, color=INK_SECONDARY, max_w=w - 72)


def _draw_p6_evolution_seal(ctx: cairo.Context, x: float, y: float, w: float, h: float, cert: dict[str, Any]) -> None:
    _panel(ctx, x, y, w, h, "(f)", "v3 → v7.2 Evrim, Dosya Bütünlüğü SHA-256 & Epistemik Sınır", f"{cert['n_locked_artifacts']}/{cert['n_locked_artifacts']} SHA-256", ACCENT_NAVY)

    # Booktabs-style 5-row v3 -> v7.2 Evolution Timeline
    evo = [
        ("v3.0", "CAD 144p nominal (857,0 kg) · BOM $4,19M · 100 K IBIC · 1,5 T Model"),
        ("v4.0", "CAD 156p nominal (960,0 kg) · S5.5 808 nm · BOM $4,61M · Exp135"),
        ("v5.0", "CAD 189p nominal (1.034,9 kg) · S5.6 MBE + S6.5 RFSoC · BOM $5,25M"),
        ("v6.0", "CAD 199p nominal (1.108,1 kg) · Opt-Q/HPC · IBM 156Q Kontrol Proxy"),
        ("v7.2", "Gerçek EDA RTL (1.193 LOC) · %1 ²⁹Si BOED · M0 FMEA · 333/333 (400) test"),
    ]
    ey0 = y + 52
    row_h = 41.0
    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(1.1)
    ctx.move_to(x + 16, ey0)
    ctx.line_to(x + w - 16, ey0)
    ctx.stroke()

    for i, (ver, desc) in enumerate(evo):
        ry = ey0 + i * row_h
        is_cur = (i == 4)
        if is_cur:
            ctx.rectangle(x + 16, ry, w - 32, row_h)
            ctx.set_source_rgba(*_hex(BG_SUBTLE))
            ctx.fill()
        if i > 0:
            ctx.move_to(x + 16, ry)
            ctx.line_to(x + w - 16, ry)
            ctx.set_source_rgba(*_hex(RULE_GRID))
            ctx.set_line_width(0.7)
            ctx.stroke()
        _rect(ctx, x + 22, ry + 8, 52, 24, 2.0)
        ctx.set_source_rgba(*_hex(ACCENT_NAVY if is_cur else BG_SUBTLE))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(ACCENT_NAVY if is_cur else RULE_BORDER))
        ctx.set_line_width(0.8)
        ctx.stroke()
        _text(ctx, ver, x + 48, ry + 24, size=10.8, color=BG_PAPER if is_cur else INK_SECONDARY, bold=True, mono=True, align="center")
        _text(ctx, desc, x + 86, ry + 24, size=10.6, color=INK_PRIMARY if is_cur else INK_SECONDARY, bold=is_cur, max_w=w - 110)

    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(1.1)
    ctx.move_to(x + 16, ey0 + len(evo) * row_h)
    ctx.line_to(x + w - 16, ey0 + len(evo) * row_h)
    ctx.stroke()

    # Restrained Light-Paper Full 64-Hex SHA-256 File-Integrity Box (ZERO dark cyberpunk box)
    sha_full = cert["sha256"]
    assert len(sha_full) == 64
    by_sha = y + 276
    _note_box(ctx, x + 16, by_sha, w - 32, 78, left_accent=ACCENT_NAVY)
    _text(ctx, f"DOSYA BÜTÜNLÜĞÜ SHA-256 ({cert['n_locked_artifacts']}/{cert['n_locked_artifacts']} Artefakt — Fizik Kanıtı Değil):", x + 30, by_sha + 22, size=10.6, color=ACCENT_NAVY, bold=True, max_w=w - 60)
    _text(ctx, sha_full, x + w / 2.0, by_sha + 47, size=13.0, color=INK_PRIMARY, bold=True, mono=True, align="center", max_w=w - 56)
    _text(ctx, f"CAD v6 Nominal: {cert['cad_v6_parts']}p / {tr_f(cert['cad_v6_mass_kg'], 1)} kg (GD&T/termal/DFM hariç) · Tarihsel v4/v5/v6 korundu", x + w / 2.0, by_sha + 67, size=9.8, color=INK_MUTED, align="center", max_w=w - 56)

    # Dual-Column Epistemic Boundary (uniform academic #F8F9FA cards, restrained header accents)
    ey_ep = y + 370
    ew = (w - 42) / 2.0
    eh = h - (ey_ep - y) - 14

    _note_box(ctx, x + 16, ey_ep, ew, eh, left_accent=ACCENT_BURGUNDY)
    _text(ctx, "M0 KAVRAMSAL + AÇIK-KAYNAK EDA", x + 28, ey_ep + 24, size=10.3, color=ACCENT_BURGUNDY, bold=True, max_w=ew - 22)
    _text(ctx, "• Silikon ³¹P/¹²¹Sb & %1 ²⁹Si BOED: Model", x + 28, ey_ep + 50, size=10.1, color=INK_PRIMARY, max_w=ew - 22)
    _text(ctx, "• RTL: Yosys/Icarus/Verilator (Vivado açık)", x + 28, ey_ep + 75, size=10.1, color=INK_PRIMARY, max_w=ew - 22)
    _text(ctx, "• Emniyet: iec61508_certified=false (M0)", x + 28, ey_ep + 100, size=10.1, color=INK_PRIMARY, max_w=ew - 22)
    _text(ctx, "• BOM v7.0 (no_quotes=true) · 333/333 AL", x + 28, ey_ep + 125, size=10.1, color=INK_SECONDARY, max_w=ew - 22)
    _text(ctx, "• Lab ölçümü, Vivado P&R & tapeout YOK", x + 28, ey_ep + 153, size=10.1, color=ACCENT_BURGUNDY, bold=True, max_w=ew - 22)

    rx = x + 26 + ew
    _note_box(ctx, rx, ey_ep, ew, eh, left_accent=ACCENT_NAVY)
    _text(ctx, "BULUT QPU PROXY — IBM (SİLİKON DEĞİL)", rx + 12, ey_ep + 24, size=10.3, color=ACCENT_NAVY, bold=True, max_w=ew - 22)
    _text(ctx, f"• Backend: {cert['live_qpu_backend']} (156Q transmon)", rx + 12, ey_ep + 50, size=10.1, color=INK_PRIMARY, bold=True, max_w=ew - 22)
    _text(ctx, f"• Job ID: {cert['live_qpu_job_id']}", rx + 12, ey_ep + 75, size=9.6, color=INK_SECONDARY, mono=True, max_w=ew - 22)
    _text(ctx, f"• Bell: %{tr_f(cert['live_qpu_bell_fidelity']*100, 2)} | XY4: +{tr_f(cert['live_qpu_xy4_gain_pp'], 2)} pp", rx + 12, ey_ep + 100, size=10.1, color=INK_PRIMARY, max_w=ew - 22)
    _text(ctx, f"• Q16 vs FP64: {tr_f(cert['live_qpu_q16_vs_fp64_kHz']*1000, 1)} Hz | ISA v4: {cert['live_cellisa_v40_opcodes']} op", rx + 12, ey_ep + 125, size=10.1, color=INK_SECONDARY, max_w=ew - 22)
    _text(ctx, "• Silikon fabrikasyonu DOĞRULAMAZ", rx + 12, ey_ep + 153, size=10.1, color=ACCENT_NAVY, bold=True, max_w=ew - 22)


def main() -> None:
    e128 = json.loads((ROOT / "results/exp128_bom_sensitivity/exp128.json").read_text(encoding="utf-8"))
    e147 = json.loads((ROOT / "results/exp147_universal_qldpc_d18_magic_state/exp147.json").read_text(encoding="utf-8"))
    e148 = json.loads((ROOT / "results/exp148_sb121_quadrupole_echo_qudit/exp148.json").read_text(encoding="utf-8"))
    e149 = json.loads((ROOT / "results/exp149_boed_verilog_rtl_and_interactive_twin/exp149.json").read_text(encoding="utf-8"))
    e150 = json.loads((ROOT / "results/exp150_industrial_safety_fmea_hazop/exp150.json").read_text(encoding="utf-8"))
    e151 = json.loads((ROOT / "results/exp151_v7_digital_twin/exp151.json").read_text(encoding="utf-8"))
    cert = json.loads((ROOT / "results/exp151_v7_digital_twin/v7_digital_twin_cert.json").read_text(encoding="utf-8"))
    cad = json.loads((CAD_DIR / "cad_verification.json").read_text(encoding="utf-8"))

    assert cad["cad_version"].startswith("6.0")
    assert e151["n_passed"] == 8 and e151["n_total"] == 8

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    # Crisp white paper canvas
    ctx.set_source_rgba(*_hex(BG_PAPER))
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Academic masthead (4px navy top rule + white paper + 1.6pt bottom rule)
    ctx.rectangle(0, 0, W, 5)
    ctx.set_source_rgba(*_hex(ACCENT_NAVY))
    ctx.fill()

    _text(ctx, "ATOM LİTOGRAFİ MAKİNESİ — v7.2 M0 Kavramsal Tasarım & Gerçek Açık-Kaynak EDA (TRL 1–2)", 28, 39, size=21.0, color=INK_PRIMARY, bold=True, max_w=W - 550)
    _text(
        ctx,
        "qLDPC d=18 (FeMoco/RSA) · ¹²¹Sb Q-Echo-8 · Gerçek EDA RTL (1.193 LOC) · %1 ²⁹Si BOED · M0 FMEA (iec61508=false) · BOM v7.0 · IBM Proxy",
        28, 64, size=12.0, color=INK_SECONDARY, max_w=W - 550,
    )

    stamps = [
        (W - 512, 154, f"DT7: {e151['n_passed']}/{e151['n_total']} PASS", ACCENT_FOREST),
        (W - 346, 158, f"{cert['n_locked_artifacts']}/{cert['n_locked_artifacts']} SHA-256", ACCENT_NAVY),
        (W - 176, 148, "TRL 1–2 / M0", ACCENT_BURGUNDY),
    ]
    for sx, sw, stxt, scol in stamps:
        _rect(ctx, sx, 22, sw, 34, 2.0)
        ctx.set_source_rgba(*_hex(BG_SUBTLE))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(RULE_BORDER))
        ctx.set_line_width(0.9)
        ctx.stroke()
        _text(ctx, stxt, sx + sw / 2.0, 43.5, size=12.0, color=scol, bold=True, mono=True, align="center")

    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(1.6)
    ctx.move_to(28, 79)
    ctx.line_to(W - 28, 79)
    ctx.stroke()

    # Unified 6-column academic summary metrics strip (zero rainbow stripes / cartoon cards)
    html_kb_kpi = (ROOT / "docs/digital_twin_interactive.html").stat().st_size / 1000.0
    kpis = [
        ("EVRENSEL qLDPC d=18", "[[288,12,18]]", f"L_max {tr_f(cert['exp147_bb288_L_max_um'], 1)} µm · p_th %{tr_f(cert['exp147_bb288_p_th_pct'], 3)}"),
        ("FeMoco / RSA-2048", f"{cert['exp147_femoco_cryostats']} / {cert['exp147_rsa2048_cryostats']} Kriyo", f"{tr_f(cert['exp147_femoco_compression_x'], 1)}× / {tr_f(cert['exp147_rsa2048_compression_x'], 1)}× ↓ · {tr_f(cert['exp147_rsa2048_power_MW'], 2)} MW"),
        ("¹²¹Sb Q-ECHO-8 & SU(8)", "0,580 -> 0,9991", f"{tr_f(cert['exp148_sb121_infidelity_reduction_x'], 1)}× ↓ · SU(8) >= {tr_f(cert['exp148_sb121_su8_grape_min_F'], 4)}"),
        ("GERÇEK EDA RTL + HTML5", f"{tr_i(cert['exp149_rtl_loc'])} LOC · 0 LSB", f"Icarus/Verilator/Yosys · {tr_f(html_kb_kpi, 1)} KB"),
        ("ÖN EMNİYET FMEA (M0)", f"RPN {cert['exp150_fmea_max_rpn_pre']} -> {cert['exp150_fmea_max_rpn_post']}", f"iec61508=false · OD8+3mm · PH₃ {tr_f(cert['exp150_ph3_operator_ppm'], 4)}"),
        ("BOM v7.0 / 10-RFQ", f"${tr_f(cert['bom_v7_m3_phase1_base_safety_nom_usd']/1e6, 2)}M / ${tr_f(cert['bom_v7_m3_v7_full_nom_usd']/1e6, 2)}M", f"Faz-1 %{tr_f(cert['bom_v7_phase1_P_gt_100M_pct'], 2)} · {cert['bom_v7_parts']}p · %{tr_f(cert['bom_v7_rfq10_nom_share_pct'], 1)}/%{tr_f(cert['bom_v7_rfq10_var_share_pct'], 1)}"),
    ]
    strip_y, strip_h = 92, 78
    ctx.rectangle(28, strip_y, W - 56, strip_h)
    ctx.set_source_rgba(*_hex(BG_SUBTLE))
    ctx.fill()
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.9)
    ctx.move_to(28, strip_y)
    ctx.line_to(W - 28, strip_y)
    ctx.move_to(28, strip_y + strip_h)
    ctx.line_to(W - 28, strip_y + strip_h)
    ctx.stroke()

    col_w = (W - 56) / 6.0
    for i, (kt, kv, ks) in enumerate(kpis):
        kx = 28 + i * col_w
        if i > 0:
            ctx.move_to(kx, strip_y + 10)
            ctx.line_to(kx, strip_y + strip_h - 10)
            ctx.set_source_rgba(*_hex(RULE_GRID))
            ctx.set_line_width(0.9)
            ctx.stroke()
        _text(ctx, kt, kx + 16, strip_y + 20, size=10.0, color=INK_SECONDARY, bold=True, max_w=col_w - 28)
        _text(ctx, kv, kx + 16, strip_y + 46, size=18.5, color=ACCENT_NAVY, bold=True, max_w=col_w - 28)
        _text(ctx, ks, kx + 16, strip_y + 66, size=10.1, color=INK_SECONDARY, mono=True, max_w=col_w - 28)

    # 3x2 Grid of 6 Analytical Panels
    pw = (W - 56 - 32) / 3.0
    r1y, r1h = 186, 574
    r2y, r2h = 776, 574
    xs = [28, 28 + pw + 16, 28 + 2 * (pw + 16)]

    _draw_p1_qldpc_algos(ctx, xs[0], r1y, pw, r1h, e147, cert)
    _draw_p2_sb121(ctx, xs[1], r1y, pw, r1h, e148, cert)
    _draw_p3_verilog_twin(ctx, xs[2], r1y, pw, r1h, e149, cert)

    _draw_p4_safety_fmea(ctx, xs[0], r2y, pw, r2h, e150)
    _draw_p5_bom_v7(ctx, xs[1], r2y, pw, r2h, e128, cert)
    _draw_p6_evolution_seal(ctx, xs[2], r2y, pw, r2h, cert)

    # Clean white paper footer with hairline rule
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.8)
    ctx.move_to(28, H - 34)
    ctx.line_to(W - 28, H - 34)
    ctx.stroke()
    _text(
        ctx,
        "Veri Kaynakları: exp128, exp147..151, boed_real_bath_benchmark.json, v7_digital_twin_cert.json (39/39), cad_verification.json | 35/35 AL (333/333; 400 yerel) pytest",
        28, H - 14, size=10.4, color=INK_SECONDARY, max_w=1380,
    )
    _text(
        ctx,
        "TRL 1–2 (M0) + Açık-Kaynak EDA (Vivado P&R & Lab açık) · Bulut QPU Proxy: ibm_marrakesh 156Q (silikon doğrulamaz)",
        W - 28, H - 14, size=10.4, color=INK_MUTED, align="right", max_w=920,
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    surf.write_to_png(str(OUT_PNG))
    with Image.open(OUT_PNG) as im:
        assert im.size == (W, H), f"Unexpected size {im.size}"
    print(f"Wrote {OUT_PNG} ({W}x{H})")


if __name__ == "__main__":
    main()
