"""Pure-Python PyCairo/PIL figure generator for Exp133 (H151).

Runs under /usr/bin/python3 -B (uses ONLY Python stdlib + cairo + PIL; no numpy/matplotlib).
Generates:
  1. results/exp133_coupled_vibration_thermal/fig_exp133_psd_jitter.png (2200x1260)
  2. results/exp133_coupled_vibration_thermal/fig_exp133_isolation_budget.png (2200x1260)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cairo

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "results" / "exp133_coupled_vibration_thermal"
IN_JSON = RESULTS_DIR / "exp133.json"
FIG1_PATH = RESULTS_DIR / "fig_exp133_psd_jitter.png"
FIG2_PATH = RESULTS_DIR / "fig_exp133_isolation_budget.png"

FONT_SANS = "DejaVu Sans"
FONT_MONO = "DejaVu Sans Mono"

# Palette (high-contrast publication theme)
BG_PAGE = (0.976, 0.980, 0.988)
BG_CARD = (1.000, 1.000, 1.000)
BG_HEADER = (0.082, 0.125, 0.196)
BORDER_COL = (0.816, 0.847, 0.894)
GRID_COL = (0.898, 0.918, 0.945)
AXIS_COL = (0.200, 0.255, 0.333)
TEXT_DARK = (0.090, 0.130, 0.195)
TEXT_MID = (0.310, 0.365, 0.445)
TEXT_LIGHT = (0.945, 0.960, 0.985)

COL_RED = (0.835, 0.180, 0.215)
COL_ORANGE = (0.890, 0.470, 0.085)
COL_BLUE = (0.118, 0.435, 0.785)
COL_GREEN = (0.065, 0.565, 0.345)
COL_PURPLE = (0.460, 0.285, 0.720)
COL_TEAL = (0.060, 0.520, 0.620)
COL_SLATE = (0.410, 0.465, 0.545)


def set_font(ctx: cairo.Context, size: float, bold: bool = False, mono: bool = False) -> None:
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(FONT_MONO if mono else FONT_SANS, cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)


def draw_text(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    size: float = 14.0,
    color: tuple[float, float, float] = TEXT_DARK,
    bold: bool = False,
    mono: bool = False,
    align: str = "left",
    valign: str = "baseline",
) -> None:
    set_font(ctx, size, bold=bold, mono=mono)
    ext = ctx.text_extents(text)
    dx = 0.0
    if align == "center":
        dx = -(ext.width / 2.0 + ext.x_bearing)
    elif align == "right":
        dx = -(ext.width + ext.x_bearing)
    dy = 0.0
    if valign == "middle":
        dy = -(ext.height / 2.0 + ext.y_bearing)
    elif valign == "top":
        dy = -ext.y_bearing
    ctx.set_source_rgb(*color)
    ctx.move_to(x + dx, y + dy)
    ctx.show_text(text)


def draw_text_rot(
    ctx: cairo.Context,
    text: str,
    x: float,
    y: float,
    angle_deg: float = -90.0,
    size: float = 14.0,
    color: tuple[float, float, float] = TEXT_DARK,
    bold: bool = False,
) -> None:
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(angle_deg))
    draw_text(ctx, text, 0.0, 0.0, size=size, color=color, bold=bold, align="center", valign="middle")
    ctx.restore()


def round_rect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 10.0) -> None:
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2.0, 0.0)
    ctx.arc(x + w - r, y + h - r, r, 0.0, math.pi / 2.0)
    ctx.arc(x + r, y + h - r, r, math.pi / 2.0, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def draw_header(ctx: cairo.Context, W: int, title: str, subtitle: str, badge: str) -> None:
    ctx.set_source_rgb(*BG_HEADER)
    ctx.rectangle(0, 0, W, 98)
    ctx.fill()
    # Accent bottom stripe
    ctx.set_source_rgb(*COL_TEAL)
    ctx.rectangle(0, 94, W, 4)
    ctx.fill()

    draw_text(ctx, title, 34, 42, size=24, color=TEXT_LIGHT, bold=True)
    draw_text(ctx, subtitle, 34, 74, size=14.5, color=(0.74, 0.82, 0.92))

    # Epistemic pill on right
    set_font(ctx, 13.0, bold=True, mono=True)
    bw = ctx.text_extents(badge).width + 32
    bx = W - bw - 30
    round_rect(ctx, bx, 28, bw, 36, 8)
    ctx.set_source_rgb(0.14, 0.22, 0.34)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.35, 0.65, 0.85)
    ctx.set_line_width(1.4)
    ctx.stroke()
    draw_text(ctx, badge, bx + bw / 2.0, 46, size=13.0, color=(0.86, 0.94, 1.0), bold=True, mono=True, align="center", valign="middle")


def draw_card(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str) -> None:
    round_rect(ctx, x, y, w, h, 10)
    ctx.set_source_rgb(*BG_CARD)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER_COL)
    ctx.set_line_width(1.5)
    ctx.stroke()

    # Subtle header band inside card
    ctx.save()
    round_rect(ctx, x, y, w, h, 10)
    ctx.clip()
    ctx.set_source_rgb(0.945, 0.960, 0.982)
    ctx.rectangle(x, y, w, 40)
    ctx.fill()
    ctx.set_source_rgb(*BORDER_COL)
    ctx.set_line_width(1.0)
    ctx.move_to(x, y + 40)
    ctx.line_to(x + w, y + 40)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, title, x + 16, y + 21, size=15.5, color=TEXT_DARK, bold=True, valign="middle")


def fmt_dec(val: float, digits: int = 3) -> str:
    return f"{val:.{digits}f}".replace(".", ",")


def fmt_pow10(exp: int) -> str:
    sup_map = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
    return "10" + str(exp).translate(sup_map)


# ---------------------------------------------------------------------------
# Figure 1: Spectral ASD & Cumulative RMS Jitter (2x2 Panel Grid)
# ---------------------------------------------------------------------------
def draw_loglog_panel(
    ctx: cairo.Context,
    px: float,
    py: float,
    pw: float,
    ph: float,
    series: list[dict],
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    xlabel: str,
    ylabel: str,
    v_markers: list[tuple[float, str, tuple[float, float, float]]],
    h_spec: tuple[float, str] | None = None,
    right_tags: list[tuple[float, str, tuple[float, float, float]]] | None = None,
) -> None:
    lx0, lx1 = math.log10(x_min), math.log10(x_max)
    ly0, ly1 = math.log10(y_min), math.log10(y_max)

    def map_x(val: float) -> float:
        lv = math.log10(max(val, x_min * 0.5))
        return px + (lv - lx0) / (lx1 - lx0) * pw

    def map_y(val: float) -> float:
        lv = math.log10(max(val, y_min * 0.25))
        return py + ph - (lv - ly0) / (ly1 - ly0) * ph

    # Grid & ticks (X decades)
    for dec in range(int(math.floor(lx0)), int(math.ceil(lx1)) + 1):
        for mult in (1, 2, 5):
            fv = mult * (10.0 ** dec)
            if x_min <= fv <= x_max:
                gx = map_x(fv)
                ctx.set_source_rgb(*(GRID_COL if mult == 1 else (0.945, 0.955, 0.970)))
                ctx.set_line_width(1.1 if mult == 1 else 0.7)
                ctx.move_to(gx, py)
                ctx.line_to(gx, py + ph)
                ctx.stroke()
                if mult in (1, 2, 5) and fv in (0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0):
                    lbl = f"{fv:g}".replace(".", ",")
                    draw_text(ctx, lbl, gx, py + ph + 18, size=12.0, color=TEXT_MID, align="center")

    # Grid & ticks (Y decades)
    for dec in range(int(math.floor(ly0)), int(math.ceil(ly1)) + 1):
        yv = 10.0 ** dec
        if y_min * 0.99 <= yv <= y_max * 1.01:
            gy = map_y(yv)
            ctx.set_source_rgb(*GRID_COL)
            ctx.set_line_width(1.1)
            ctx.move_to(px, gy)
            ctx.line_to(px + pw, gy)
            ctx.stroke()
            draw_text(ctx, fmt_pow10(dec), px - 10, gy, size=12.5, color=TEXT_MID, align="right", valign="middle")

    # Vertical structural / PT420 markers
    for idx_m, (mf, mlbl, mcol) in enumerate(v_markers):
        if x_min <= mf <= x_max:
            gx = map_x(mf)
            ctx.save()
            ctx.set_dash([5.0, 4.0])
            ctx.set_source_rgba(mcol[0], mcol[1], mcol[2], 0.55)
            ctx.set_line_width(1.2)
            ctx.move_to(gx, py)
            ctx.line_to(gx, py + ph)
            ctx.stroke()
            ctx.restore()
            # Alternate vertical offset so adjacent labels never collide
            y_off = py + 15 + (idx_m % 2) * 16
            draw_text(ctx, mlbl, gx + 4, y_off, size=11.0, color=mcol, bold=True)

    # Horizontal 0.50 nm spec line
    if h_spec is not None:
        sy_val, slbl = h_spec
        if y_min <= sy_val <= y_max:
            gy = map_y(sy_val)
            ctx.save()
            ctx.set_dash([9.0, 5.0])
            ctx.set_source_rgb(*COL_GREEN)
            ctx.set_line_width(2.2)
            ctx.move_to(px, gy)
            ctx.line_to(px + pw, gy)
            ctx.stroke()
            ctx.restore()
            # Clean pill label placed below the 0.50 nm line in Panel B (or above in Panel D)
            lx_spec = px + pw * 0.52
            set_font(ctx, 12.0, bold=True)
            tw = ctx.text_extents(slbl).width + 14
            if "σ_stage" in ylabel:
                round_rect(ctx, lx_spec - tw / 2.0, gy + 6, tw, 18, 4)
                ctx.set_source_rgba(1.0, 1.0, 1.0, 0.92)
                ctx.fill()
                draw_text(ctx, slbl, lx_spec, gy + 19, size=12.0, color=COL_GREEN, bold=True, align="center")
            else:
                round_rect(ctx, lx_spec - tw / 2.0, gy - 23, tw, 18, 4)
                ctx.set_source_rgba(1.0, 1.0, 1.0, 0.92)
                ctx.fill()
                draw_text(ctx, slbl, lx_spec, gy - 9, size=12.0, color=COL_GREEN, bold=True, align="center")

    # Plot curves clipped to plot box
    ctx.save()
    ctx.rectangle(px, py, pw, ph)
    ctx.clip()
    for s_item in series:
        xs = s_item["x"]
        ys = s_item["y"]
        col = s_item["color"]
        lw = s_item.get("lw", 2.4)
        dash = s_item.get("dash", None)
        ctx.save()
        if dash:
            ctx.set_dash(dash)
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        started = False
        for xv, yv in zip(xs, ys):
            if xv < x_min or xv > x_max or yv <= 0.0:
                continue
            cx = map_x(xv)
            cy = max(py - 5.0, min(py + ph + 5.0, map_y(yv)))
            if not started:
                ctx.move_to(cx, cy)
                started = True
            else:
                ctx.line_to(cx, cy)
        ctx.stroke()
        ctx.restore()
    ctx.restore()

    # Right-edge non-overlapping value tags (sorted top to bottom with minimum spacing)
    if right_tags:
        placed = []
        for yv, tlbl, tcol in sorted(right_tags, key=lambda item: -item[0]):
            gy = max(py + 12.0, min(py + ph - 12.0, map_y(yv)))
            for prev_y in placed:
                if abs(gy - prev_y) < 22.0:
                    gy = prev_y + 22.0
            gy = min(py + ph - 10.0, gy)
            placed.append(gy)
            # Dot on right axis
            ctx.set_source_rgb(*tcol)
            ctx.arc(px + pw, max(py + 4, min(py + ph - 4, map_y(yv))), 4.0, 0.0, 2.0 * math.pi)
            ctx.fill()
            draw_text(ctx, tlbl, px + pw + 8, gy, size=12.0, color=tcol, bold=True, mono=True, valign="middle")

    # Axis border
    ctx.set_source_rgb(*AXIS_COL)
    ctx.set_line_width(1.6)
    ctx.rectangle(px, py, pw, ph)
    ctx.stroke()

    # Axis labels
    draw_text(ctx, xlabel, px + pw / 2.0, py + ph + 40, size=13.5, color=TEXT_DARK, bold=True, align="center")
    draw_text_rot(ctx, ylabel, px - 56, py + ph / 2.0, angle_deg=-90.0, size=13.5, color=TEXT_DARK, bold=True)


def make_figure_1(data: dict) -> None:
    W, H = 2200, 1260
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG_PAGE)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    draw_header(
        ctx, W,
        "Exp133 (H151): Kuple Titreşim Spektral Yoğunluğu (ASD) & Kümülatif RMS Titreme (VC-E)",
        "CAD v3.0 (956,90 kg, 143 parça) · Cryomech PT420 (1,4 Hz + 20 harmonik) · 40-Elemanlı Kolon FEM (f₁=118,2 Hz) · 6-DOF Kapalı Çevrim",
        "{Model} · {Sayısal-Simülasyon} · no_lab_measurement=true",
    )

    # Top legend strip
    ly = 114
    legend_items = [
        ("CFG1: CAD v3.0 Rijit PT420 + Açık Çevrim", COL_RED, None),
        ("CFG2: Mekanik Ayrık PT420 + Pasif İzolasyon", COL_ORANGE, [8.0, 4.0]),
        ("CFG3: Ayrık + Aktif Tabla + Piezo PID", COL_BLUE, None),
        ("CFG4: CAD v4.0 Tam (Aktif + PID + 1,4 Hz FF)", COL_GREEN, None),
    ]
    round_rect(ctx, 30, ly, W - 60, 42, 8)
    ctx.set_source_rgb(*BG_CARD)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER_COL)
    ctx.set_line_width(1.2)
    ctx.stroke()

    lx_cur = 52
    for lbl, col, dash in legend_items:
        ctx.save()
        if dash:
            ctx.set_dash(dash)
        ctx.set_source_rgb(*col)
        ctx.set_line_width(3.4)
        ctx.move_to(lx_cur, ly + 21)
        ctx.line_to(lx_cur + 38, ly + 21)
        ctx.stroke()
        ctx.restore()
        draw_text(ctx, lbl, lx_cur + 48, ly + 21, size=13.5, color=TEXT_DARK, bold=True, valign="middle")
        lx_cur += 528

    sp = data["plot_spectra"]
    cfgs = data["configurations_vce"]

    # 2x2 Cards
    margin_x = 30
    gap_x = 26
    gap_y = 22
    top_y = 172
    bot_y = H - 46
    card_w = (W - 2 * margin_x - gap_x) / 2.0
    card_h = (bot_y - top_y - gap_y) / 2.0

    v_markers = [
        (1.4, "1,4 Hz PT420", COL_RED),
        (16.0, "16 Hz DR", COL_PURPLE),
        (118.2, "118 Hz Kolon", COL_TEAL),
        (180.0, "180 Hz Piezo", COL_SLATE),
    ]

    # Panel A (Top-Left): Stage ASD
    c1x, c1y = margin_x, top_y
    draw_card(ctx, c1x, c1y, card_w, card_h, "A) Yonga Kademesi Yer Değiştirme ASD — σ_stage Spektrumu (VC-E)")
    s_asd_stage = [
        {"x": sp["CFG1_RIGID_OPEN"]["stage"]["freq_hz"], "y": sp["CFG1_RIGID_OPEN"]["stage"]["asd_nm_per_rtHz"], "color": COL_RED, "lw": 2.3},
        {"x": sp["CFG2_DECOUPLED_OPEN"]["stage"]["freq_hz"], "y": sp["CFG2_DECOUPLED_OPEN"]["stage"]["asd_nm_per_rtHz"], "color": COL_ORANGE, "lw": 2.3, "dash": [7.0, 4.0]},
        {"x": sp["CFG3_ACTIVE_ISO_PID"]["stage"]["freq_hz"], "y": sp["CFG3_ACTIVE_ISO_PID"]["stage"]["asd_nm_per_rtHz"], "color": COL_BLUE, "lw": 2.1},
        {"x": sp["CFG4_V4_FULL_CTRL"]["stage"]["freq_hz"], "y": sp["CFG4_V4_FULL_CTRL"]["stage"]["asd_nm_per_rtHz"], "color": COL_GREEN, "lw": 2.6},
    ]
    draw_loglog_panel(
        ctx, c1x + 86, c1y + 56, card_w - 114, card_h - 112,
        s_asd_stage, 0.2, 500.0, 1e-4, 1e5,
        "Frekans f [Hz]", "Kademe ASD [nm / √Hz]", v_markers,
    )

    # Panel B (Top-Right): Stage Cumulative RMS
    c2x, c2y = margin_x + card_w + gap_x, top_y
    draw_card(ctx, c2x, c2y, card_w, card_h, "B) Kümülatif Kademe RMS Titremesi — σ_stage(f) ≤ 0,50 nm Hedefi")
    s_cum_stage = [
        {"x": sp["CFG1_RIGID_OPEN"]["stage"]["freq_hz"], "y": sp["CFG1_RIGID_OPEN"]["stage"]["cum_rms_nm"], "color": COL_RED, "lw": 2.6},
        {"x": sp["CFG2_DECOUPLED_OPEN"]["stage"]["freq_hz"], "y": sp["CFG2_DECOUPLED_OPEN"]["stage"]["cum_rms_nm"], "color": COL_ORANGE, "lw": 2.5, "dash": [7.0, 4.0]},
        {"x": sp["CFG3_ACTIVE_ISO_PID"]["stage"]["freq_hz"], "y": sp["CFG3_ACTIVE_ISO_PID"]["stage"]["cum_rms_nm"], "color": COL_BLUE, "lw": 2.2},
        {"x": sp["CFG4_V4_FULL_CTRL"]["stage"]["freq_hz"], "y": sp["CFG4_V4_FULL_CTRL"]["stage"]["cum_rms_nm"], "color": COL_GREEN, "lw": 2.8},
    ]
    rtags_stage = [
        (cfgs["CFG1_RIGID_OPEN"]["sigma_stage_nm"], f"{fmt_dec(cfgs['CFG1_RIGID_OPEN']['sigma_stage_nm'], 0)} nm", COL_RED),
        (cfgs["CFG2_DECOUPLED_OPEN"]["sigma_stage_nm"], f"{fmt_dec(cfgs['CFG2_DECOUPLED_OPEN']['sigma_stage_nm'], 3)} nm", COL_ORANGE),
        (cfgs["CFG3_ACTIVE_ISO_PID"]["sigma_stage_nm"], f"{fmt_dec(cfgs['CFG3_ACTIVE_ISO_PID']['sigma_stage_nm'], 3)} nm", COL_BLUE),
        (cfgs["CFG4_V4_FULL_CTRL"]["sigma_stage_nm"], f"{fmt_dec(cfgs['CFG4_V4_FULL_CTRL']['sigma_stage_nm'], 3)} nm", COL_GREEN),
    ]
    draw_loglog_panel(
        ctx, c2x + 86, c2y + 56, card_w - 208, card_h - 112,
        s_cum_stage, 0.2, 500.0, 1e-3, 1e4,
        "Üst İntegrasyon Frekansı f [Hz]", "Kümülatif σ_stage [nm]", v_markers[:2],
        h_spec=(0.50, "Exp66/124 Sınırı: 0,50 nm"),
        right_tags=rtags_stage,
    )

    # Panel C (Bottom-Left): Pointing ASD (outside wafer servo!)
    c3x, c3y = margin_x, top_y + card_h + gap_y
    draw_card(ctx, c3x, c3y, card_w, card_h, "C) İyon Kolonu Işın Yönelim Hatası ASD — σ_pointing (Servo Döngüsü Dışı)")
    s_asd_ptg = [
        {"x": sp["CFG1_RIGID_OPEN"]["pointing"]["freq_hz"], "y": sp["CFG1_RIGID_OPEN"]["pointing"]["asd_nm_per_rtHz"], "color": COL_RED, "lw": 2.3},
        {"x": sp["CFG2_DECOUPLED_OPEN"]["pointing"]["freq_hz"], "y": sp["CFG2_DECOUPLED_OPEN"]["pointing"]["asd_nm_per_rtHz"], "color": COL_ORANGE, "lw": 2.3, "dash": [7.0, 4.0]},
        {"x": sp["CFG3_ACTIVE_ISO_PID"]["pointing"]["freq_hz"], "y": sp["CFG3_ACTIVE_ISO_PID"]["pointing"]["asd_nm_per_rtHz"], "color": COL_BLUE, "lw": 2.2},
        {"x": sp["CFG4_V4_FULL_CTRL"]["pointing"]["freq_hz"], "y": sp["CFG4_V4_FULL_CTRL"]["pointing"]["asd_nm_per_rtHz"], "color": COL_GREEN, "lw": 2.6},
    ]
    draw_loglog_panel(
        ctx, c3x + 86, c3y + 56, card_w - 114, card_h - 112,
        s_asd_ptg, 0.2, 500.0, 1e-4, 1e4,
        "Frekans f [Hz]", "Yönelim ASD [nm / √Hz]", v_markers,
    )

    # Panel D (Bottom-Right): Pointing Cumulative RMS + Control Stability Summary Box
    c4x, c4y = margin_x + card_w + gap_x, top_y + card_h + gap_y
    draw_card(ctx, c4x, c4y, card_w, card_h, "D) Kümülatif Işın Yönelim RMS — σ_pointing(f) ≤ 0,50 nm & Kararlılık")
    s_cum_ptg = [
        {"x": sp["CFG1_RIGID_OPEN"]["pointing"]["freq_hz"], "y": sp["CFG1_RIGID_OPEN"]["pointing"]["cum_rms_nm"], "color": COL_RED, "lw": 2.6},
        {"x": sp["CFG2_DECOUPLED_OPEN"]["pointing"]["freq_hz"], "y": sp["CFG2_DECOUPLED_OPEN"]["pointing"]["cum_rms_nm"], "color": COL_ORANGE, "lw": 2.5, "dash": [7.0, 4.0]},
        {"x": sp["CFG3_ACTIVE_ISO_PID"]["pointing"]["freq_hz"], "y": sp["CFG3_ACTIVE_ISO_PID"]["pointing"]["cum_rms_nm"], "color": COL_BLUE, "lw": 2.3},
        {"x": sp["CFG4_V4_FULL_CTRL"]["pointing"]["freq_hz"], "y": sp["CFG4_V4_FULL_CTRL"]["pointing"]["cum_rms_nm"], "color": COL_GREEN, "lw": 2.8},
    ]
    rtags_ptg = [
        (cfgs["CFG1_RIGID_OPEN"]["sigma_pointing_nm"], f"{fmt_dec(cfgs['CFG1_RIGID_OPEN']['sigma_pointing_nm'], 1)} nm", COL_RED),
        (cfgs["CFG2_DECOUPLED_OPEN"]["sigma_pointing_nm"], f"{fmt_dec(cfgs['CFG2_DECOUPLED_OPEN']['sigma_pointing_nm'], 2)} nm", COL_ORANGE),
        (cfgs["CFG3_ACTIVE_ISO_PID"]["sigma_pointing_nm"], f"{fmt_dec(cfgs['CFG3_ACTIVE_ISO_PID']['sigma_pointing_nm'], 3)} nm", COL_BLUE),
        (cfgs["CFG4_V4_FULL_CTRL"]["sigma_pointing_nm"], f"{fmt_dec(cfgs['CFG4_V4_FULL_CTRL']['sigma_pointing_nm'], 3)} nm", COL_GREEN),
    ]
    draw_loglog_panel(
        ctx, c4x + 86, c4y + 56, card_w - 208, card_h - 112,
        s_cum_ptg, 0.2, 500.0, 1e-3, 1e3,
        "Üst İntegrasyon Frekansı f [Hz]", "Kümülatif σ_pointing [nm]", v_markers[:2],
        h_spec=(0.50, "Exp66/124 Sınırı: 0,50 nm"),
        right_tags=rtags_ptg,
    )

    # Compact inset stability box in bottom-right corner of Panel D (empty log region y in [1e-3, 3e-2], x in [10, 450])
    cm = cfgs["CFG4_V4_FULL_CTRL"]["control_margins"]
    pv = cfgs["CFG4_V4_FULL_CTRL"]["parseval"]
    bx, by, bw, bh = c4x + card_w - 432, c4y + card_h - 178, 294, 114
    round_rect(ctx, bx, by, bw, bh, 7)
    ctx.set_source_rgba(0.965, 0.985, 0.975, 0.95)
    ctx.fill_preserve()
    ctx.set_source_rgb(*COL_GREEN)
    ctx.set_line_width(1.3)
    ctx.stroke()
    draw_text(ctx, "CFG4 Servo Kararlılık & Doğrulama", bx + 12, by + 20, size=12.0, color=COL_GREEN, bold=True)
    lines = [
        f"f_c={fmt_dec(cm['f_crossover_hz'],1)} Hz · PM={fmt_dec(cm['phase_margin_deg'],1)}° (>=45°)",
        f"GM={fmt_dec(cm['gain_margin_db'],2)} dB (>=6) · ||S||inf={fmt_dec(cm['sensitivity_peak_S_inf'],2)} (<=2)",
        f"Parseval (N=128k): {fmt_dec(pv['max_rel_err']*100,3)}% (<%1)",
        f"Piezo F_pik (5σ): {fmt_dec(cfgs['CFG4_V4_FULL_CTRL']['piezo_force_peak_5sigma_N']*1e3,1)} mN (<< 20 N)",
    ]
    for i, ln in enumerate(lines):
        draw_text(ctx, ln, bx + 12, by + 40 + i * 19, size=11.2, color=TEXT_DARK, mono=True)

    # Footer
    draw_text(
        ctx,
        "Kaynak: Exp133 sayısal çözücü · Kütleler CAD v3.0 (956,90 kg) · Zemin IEST-RP-CC012.2 VC-E (3,1 µm/s) · PT420 Tomaru(2004)/Olivieri(2017) · Laboratuvar ölçümü yoktur.",
        34, H - 18, size=12.0, color=TEXT_MID,
    )

    surf.write_to_png(str(FIG1_PATH))


# ---------------------------------------------------------------------------
# Figure 2: 2D (k_bellows, k_braid) Envelope + VC/Thermal + Exp124 Closure
# ---------------------------------------------------------------------------
def heatmap_rgb(val_nm: float) -> tuple[float, float, float]:
    """Smooth perceptually clear log10 colormap from 0.08 nm (deep teal-green) to 300 nm (crimson)."""
    lv = math.log10(max(val_nm, 0.08))
    # Map [-1.1, +2.5] -> [0, 1]
    t = max(0.0, min(1.0, (lv - (-1.05)) / (2.55 - (-1.05))))
    # 5-stop palette: 0.0=deep green-teal (safe), 0.22=mint-blue (0.50 nm border), 0.45=gold, 0.72=orange-red, 1.0=dark crimson
    stops = [
        (0.00, (0.055, 0.420, 0.340)),
        (0.22, (0.145, 0.655, 0.525)),
        (0.32, (0.945, 0.855, 0.355)),
        (0.62, (0.915, 0.425, 0.145)),
        (1.00, (0.580, 0.075, 0.145)),
    ]
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0)
            return (
                c0[0] + u * (c1[0] - c0[0]),
                c0[1] + u * (c1[1] - c0[1]),
                c0[2] + u * (c1[2] - c0[2]),
            )
    return stops[-1][1]


def make_figure_2(data: dict) -> None:
    W, H = 2200, 1260
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*BG_PAGE)
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    draw_header(
        ctx, W,
        "Exp133 (H151): CAD v4.0 Mekanik Ayrıştırma Zarfı, Zemin/Termal Duyarlılık & Exp124 Bütçe Kapanışı",
        "2B (k_bellows, k_braid) Sertlik Zarfı (VC-E) · OFHC Bakır Örgü 20 mK Termal Dengesi · VC-C/E/G & ±10–100 mK Termal · Exp124 5 keV RSS",
        "{Model} · {Sayısal-Simülasyon} · no_lab_measurement=true",
    )

    margin_x = 30
    gap_x = 26
    top_y = 118
    bot_y = H - 46
    left_w = 1040
    right_w = W - 2 * margin_x - gap_x - left_w
    full_h = bot_y - top_y

    # ==================== LEFT CARD: 2D (k_bellows, k_braid) Heatmap ====================
    draw_card(ctx, margin_x, top_y, left_w, full_h, "A) 2B Mekanik Ayrıştırma Zarfı: maks(σ_stage, σ_pointing) [nm] (VC-E, CFG4, uzak vana)")

    sw = data["stiffness_sweep_2d"]
    kb_grid = sw["k_braid_grid_N_m"]    # 13 rows (10^1 .. 10^7)
    kbl_grid = sw["k_bellows_grid_N_m"] # 13 cols (10^2 .. 10^7)
    z_grid = sw["sigma_max_grid_nm"]    # [row=kb][col=kbl]
    lims = sw["exact_limits_vce"]

    hx = margin_x + 96
    hy = top_y + 66
    hw = left_w - 235
    hh = full_h - 275

    nrows = len(kb_grid)
    ncols = len(kbl_grid)
    cw = hw / ncols
    ch = hh / nrows

    # Draw heatmap cells (row 0 = lowest k_braid at bottom)
    for r in range(nrows):
        for c in range(ncols):
            val = z_grid[r][c]
            col = heatmap_rgb(val)
            x0 = hx + c * cw
            y0 = hy + hh - (r + 1) * ch
            ctx.set_source_rgb(*col)
            ctx.rectangle(x0, y0, cw + 0.6, ch + 0.6)
            ctx.fill()
            # Subtle value text in alternating cells for quantitative precision
            if (r % 2 == 0) and (c % 2 == 0):
                t_col = (1.0, 1.0, 1.0) if (val > 2.5 or val < 0.25) else TEXT_DARK
                lbl = f"{val:.2f}" if val < 10.0 else (f"{val:.0f}" if val < 1000 else f"{val/1000:.1f}k")
                draw_text(ctx, lbl, x0 + cw / 2.0, y0 + ch / 2.0, size=10.5, color=t_col, bold=True, mono=True, align="center", valign="middle")

    # Helper to map continuous (k_bellows, k_braid) -> pixel on heatmap
    # Note: cell centers correspond to linspace(2, 7, 13) and linspace(1, 7, 13)
    def map_hx(kbl_val: float) -> float:
        t = (math.log10(kbl_val) - 2.0) / 5.0
        return hx + (t * (ncols - 1) + 0.5) * cw

    def map_hy(kb_val: float) -> float:
        t = (math.log10(kb_val) - 1.0) / 6.0
        return hy + hh - (t * (nrows - 1) + 0.5) * ch

    # Draw exact 0.50 nm pass box boundary (k_bellows <= k_bellows_max AND k_braid <= k_braid_max)
    kbl_max = lims["k_bellows_max_at_kbraid60"]["k_max_N_m"]
    kb_max = lims["k_braid_max_at_kbel2000"]["k_max_N_m"]
    xb_lim = map_hx(kbl_max)
    yb_lim = map_hy(kb_max)

    ctx.save()
    ctx.set_dash([10.0, 5.0])
    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.set_line_width(3.2)
    ctx.move_to(hx, yb_lim)
    ctx.line_to(xb_lim, yb_lim)
    ctx.line_to(xb_lim, hy + hh)
    ctx.stroke()
    ctx.restore()

    # Pass-zone label inside lower-left safe box
    round_rect(ctx, hx + 12, yb_lim + 14, 245, 50, 6)
    ctx.set_source_rgba(0.05, 0.25, 0.20, 0.85)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.65, 1.0, 0.82)
    ctx.set_line_width(1.3)
    ctx.stroke()
    draw_text(ctx, "GEÇERLİ BÖLGE (≤ 0,50 nm)", hx + 22, yb_lim + 33, size=12.5, color=(0.82, 1.0, 0.90), bold=True)
    draw_text(ctx, f"k_bel≤{kbl_max:,.0f} · k_örgü≤{kb_max:,.0f} N/m".replace(",", "."), hx + 22, yb_lim + 53, size=11.0, color=(0.94, 0.99, 0.96), mono=True)

    # Mark CAD v4.0 Recommended operating point (2000 N/m, 52.7 N/m)
    vx4 = map_hx(2000.0)
    vy4 = map_hy(data["ofhc_braid_physics"]["k_braid_N_m"])
    ctx.set_source_rgb(0.05, 0.95, 0.45)
    ctx.arc(vx4, vy4, 9.5, 0, 2 * math.pi)
    ctx.fill()
    ctx.set_source_rgb(0.02, 0.20, 0.10)
    ctx.set_line_width(2.2)
    ctx.arc(vx4, vy4, 9.5, 0, 2 * math.pi)
    ctx.stroke()
    # Callout right of star
    round_rect(ctx, vx4 + 16, vy4 - 24, 248, 48, 6)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.94)
    ctx.fill_preserve()
    ctx.set_source_rgb(*COL_GREEN)
    ctx.set_line_width(1.8)
    ctx.stroke()
    draw_text(ctx, "CAD v4.0 Hedef (2000 / 53 N/m)", vx4 + 25, vy4 - 6, size=11.5, color=COL_GREEN, bold=True)
    draw_text(ctx, "σ_stg=0,102 · σ_ptg=0,147 nm", vx4 + 25, vy4 + 13, size=11.0, color=TEXT_DARK, mono=True)

    # Mark CAD v3.0 Rigid operating point (4.96 MN/m, 9.06 MN/m)
    vx3 = map_hx(data["cad_anchors"]["k_ovc_rigid_eff_N_m"])
    vy3 = map_hy(data["cad_anchors"]["k_cold_finger_rigid_N_m"])
    ctx.set_source_rgb(1.0, 0.96, 0.30)
    ctx.set_line_width(3.6)
    ctx.move_to(vx3 - 9, vy3 - 9); ctx.line_to(vx3 + 9, vy3 + 9)
    ctx.move_to(vx3 + 9, vy3 - 9); ctx.line_to(vx3 - 9, vy3 + 9)
    ctx.stroke()
    round_rect(ctx, vx3 - 266, vy3 - 20, 248, 48, 6)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.94)
    ctx.fill_preserve()
    ctx.set_source_rgb(*COL_RED)
    ctx.set_line_width(1.8)
    ctx.stroke()
    draw_text(ctx, "CAD v3.0 Rijit (5,0 / 9,1 MN/m)", vx3 - 257, vy3 - 2, size=11.5, color=COL_RED, bold=True)
    draw_text(ctx, "Açık: 2052 nm · Ctrl: 145,6 nm", vx3 - 257, vy3 + 17, size=11.0, color=TEXT_DARK, mono=True)

    # Heatmap border & ticks
    ctx.set_source_rgb(*AXIS_COL)
    ctx.set_line_width(1.6)
    ctx.rectangle(hx, hy, hw, hh)
    ctx.stroke()
    for exp_x in range(2, 8):
        tx = map_hx(10.0 ** exp_x)
        draw_text(ctx, fmt_pow10(exp_x), tx, hy + hh + 20, size=12.5, color=TEXT_MID, align="center")
    for exp_y in range(1, 8):
        ty = map_hy(10.0 ** exp_y)
        draw_text(ctx, fmt_pow10(exp_y), hx - 10, ty, size=12.5, color=TEXT_MID, align="right", valign="middle")

    draw_text(ctx, "OVC Körük Sertliği k_bellows [N/m]", hx + hw / 2.0, hy + hh + 44, size=13.5, color=TEXT_DARK, bold=True, align="center")
    draw_text_rot(ctx, "20 mK Soğuk Parmak / Örgü Sertliği k_braid [N/m]", hx - 60, hy + hh / 2.0, angle_deg=-90.0, size=13.5, color=TEXT_DARK, bold=True)

    # Colorbar on right of heatmap
    cbx, cby, cbw, cbh = hx + hw + 22, hy, 24, hh
    n_cb = 160
    for i in range(n_cb):
        u = i / (n_cb - 1)
        lv = -1.05 + u * (2.55 - (-1.05))
        col = heatmap_rgb(10.0 ** lv)
        y_seg = cby + cbh - (i + 1) * (cbh / n_cb)
        ctx.set_source_rgb(*col)
        ctx.rectangle(cbx, y_seg, cbw, cbh / n_cb + 0.8)
        ctx.fill()
    ctx.set_source_rgb(*AXIS_COL)
    ctx.set_line_width(1.2)
    ctx.rectangle(cbx, cby, cbw, cbh)
    ctx.stroke()
    for cv, clbl in [(0.1, "0,1"), (0.5, "0,5*"), (1.0, "1"), (10.0, "10"), (100.0, "100"), (300.0, "300")]:
        u = (math.log10(cv) - (-1.05)) / (2.55 - (-1.05))
        yc = cby + cbh - u * cbh
        ctx.set_source_rgb(*AXIS_COL)
        ctx.move_to(cbx + cbw, yc); ctx.line_to(cbx + cbw + 5, yc); ctx.stroke()
        draw_text(ctx, clbl, cbx + cbw + 9, yc, size=11.5, color=(COL_GREEN if cv == 0.5 else TEXT_MID), bold=(cv == 0.5), valign="middle")
    draw_text(ctx, "nm", cbx + cbw / 2.0, cby - 12, size=12.0, color=TEXT_DARK, bold=True, align="center")

    # Bottom Engineering Spec Strip inside Left Card (OFHC Braid & Bellows Summary)
    br = data["ofhc_braid_physics"]
    sx, sy, sw_box, sh_box = margin_x + 22, hy + hh + 66, left_w - 44, 122
    round_rect(ctx, sx, sy, sw_box, sh_box, 8)
    ctx.set_source_rgb(0.955, 0.972, 0.990)
    ctx.fill_preserve()
    ctx.set_source_rgb(*BORDER_COL)
    ctx.set_line_width(1.2)
    ctx.stroke()
    draw_text(ctx, "CAD v4.0 Mekanik Ayrıştırma Özeti (Wiedemann–Franz 20 mK + 6-DOF Kontrol Zarfı)", sx + 16, sy + 24, size=13.0, color=COL_BLUE, bold=True)
    spec_lines = [
        f"• OFHC Cu Örgü (S6.2): 4× 2.550 adet Ø50 µm tel (L=100 mm, A=20,0 mm², RRR≥200) → k={fmt_dec(br['k_braid_N_m'],1)} N/m (70× emniyet)",
        f"• 20 mK Termal İletkenlik: G_örgü={fmt_dec(br['G_braid_20mK_mW_K'],2)} mW/K · G_hat={fmt_dec(br['G_total_link_20mK_mW_K'],2)} mW/K → ΔT={fmt_dec(br['dT_at_2p5uW_mK'],1)} mK @ 2,5 µW",
        f"• OVC UHV Körük (S6.2): Kenar-kaynaklı 316L CF63 (Ø44/Ø68, L=120 mm, 28 boğum) → k=2.000 N/m (sınır 6.282 N/m, 3,1× emniyet)",
        f"• PT420 Uzak Döner Vana: 600 mm esnek He hattı (HF >12×, 1,4 Hz ~3,6× azalma) · k_braid/k_bellows kademe duyarlılığı: {lims['braid_over_bellows_stage_sensitivity_ratio']:.0f}×",
    ]
    for i, ln in enumerate(spec_lines):
        draw_text(ctx, ln, sx + 16, sy + 48 + i * 21, size=11.6, color=TEXT_DARK)

    # ==================== RIGHT TOP CARD: VC Floor & Thermal Drift ====================
    rx = margin_x + left_w + gap_x
    r_gap = 22
    rt_h = (full_h - r_gap) * 0.52
    rb_h = full_h - r_gap - rt_h

    draw_card(ctx, rx, top_y, right_w, rt_h, "B) Temiz Oda Zemin Sınıfı (VC-C/E/G) & Termal Sürüklenme (σ_thermal)")

    vc_sw = data["vc_floor_sweep"]
    th_comp = data["thermal_drift"]["material_comparison"]

    # Sub-panel B1 (Left half of right card): VC-C / VC-E / VC-G bars
    b1x, b1y, b1w, b1h = rx + 68, top_y + 72, right_w * 0.44 - 50, rt_h - 148
    draw_text(ctx, "Temiz Oda Zemin (CFG4)", b1x + b1w / 2.0, b1y - 14, size=13.0, color=TEXT_DARK, bold=True, align="center")

    vc_bars = [
        ("VC-C\n12,5 µm/s", vc_sw["VC-C"]["cfg4_pointing_nm"], COL_RED, "RED"),
        ("VC-E\n3,1 µm/s", vc_sw["VC-E"]["cfg4_pointing_nm"], COL_GREEN, "PASS"),
        ("VC-G\n0,78 µm/s", vc_sw["VC-G"]["cfg4_pointing_nm"], COL_TEAL, "PASS"),
    ]
    y_max_b1 = 0.72
    # Y-grid B1
    for yv in (0.0, 0.2, 0.4, 0.5, 0.6, 0.7):
        gy = b1y + b1h - (yv / y_max_b1) * b1h
        ctx.set_source_rgb(*(COL_GREEN if abs(yv - 0.5) < 1e-6 else GRID_COL))
        ctx.set_line_width(1.8 if abs(yv - 0.5) < 1e-6 else 0.9)
        if abs(yv - 0.5) < 1e-6:
            ctx.save(); ctx.set_dash([7.0, 4.0])
            ctx.move_to(b1x, gy); ctx.line_to(b1x + b1w, gy); ctx.stroke()
            ctx.restore()
        else:
            ctx.move_to(b1x, gy); ctx.line_to(b1x + b1w, gy); ctx.stroke()
        draw_text(ctx, fmt_dec(yv, 1), b1x - 8, gy, size=11.5, color=(COL_GREEN if abs(yv - 0.5) < 1e-6 else TEXT_MID), bold=(abs(yv - 0.5) < 1e-6), align="right", valign="middle")

    bar_slot = b1w / len(vc_bars)
    for i, (blbl, bval, bcol, status) in enumerate(vc_bars):
        bw_i = bar_slot * 0.56
        bx_i = b1x + i * bar_slot + (bar_slot - bw_i) / 2.0
        bh_i = (bval / y_max_b1) * b1h
        by_i = b1y + b1h - bh_i
        round_rect(ctx, bx_i, by_i, bw_i, bh_i, 4)
        ctx.set_source_rgb(*bcol)
        ctx.fill()
        draw_text(ctx, f"{fmt_dec(bval, 3)}", bx_i + bw_i / 2.0, by_i - 18, size=11.8, color=bcol, bold=True, mono=True, align="center")
        draw_text(ctx, status, bx_i + bw_i / 2.0, by_i - 4, size=10.5, color=bcol, bold=True, align="center")
        l0, l1 = blbl.split("\n")
        draw_text(ctx, l0, bx_i + bw_i / 2.0, b1y + b1h + 18, size=12.0, color=TEXT_DARK, bold=True, align="center")
        draw_text(ctx, l1, bx_i + bw_i / 2.0, b1y + b1h + 34, size=10.8, color=TEXT_MID, align="center")

    ctx.set_source_rgb(*AXIS_COL)
    ctx.set_line_width(1.5)
    ctx.move_to(b1x, b1y); ctx.line_to(b1x, b1y + b1h); ctx.line_to(b1x + b1w, b1y + b1h); ctx.stroke()
    draw_text_rot(ctx, "σ_pointing [nm]", b1x - 46, b1y + b1h / 2.0, angle_deg=-90.0, size=12.5, color=TEXT_DARK, bold=True)

    # Sub-panel B2 (Right half of right card): Thermal Drift comparison (log-Y for 0.028 vs 1.935 nm!)
    b2x, b2y, b2w, b2h = rx + right_w * 0.51 + 26, top_y + 72, right_w * 0.49 - 52, rt_h - 148
    draw_text(ctx, "Termal Sürüklenme σ_thermal (T=900 s, t_fid=300 s)", b2x + b2w / 2.0, b2y - 14, size=13.0, color=TEXT_DARK, bold=True, align="center")

    th_bars = [
        ("316LN SS\n±10 mK", th_comp["naive_ss316_uncompensated"]["dT_10mK"]["sigma_thermal_nm"], COL_RED),
        ("v3/v4\n±10 mK", th_comp["v3_zerodur_invar_cryo"]["dT_10mK"]["sigma_thermal_nm"], COL_GREEN),
        ("v3/v4\n±50 mK", th_comp["v3_zerodur_invar_cryo"]["dT_50mK"]["sigma_thermal_nm"], COL_TEAL),
        ("v3/v4\n±100 mK", th_comp["v3_zerodur_invar_cryo"]["dT_100mK"]["sigma_thermal_nm"], COL_BLUE),
    ]
    ly_th0, ly_th1 = math.log10(0.01), math.log10(5.0)

    def map_th_y(v: float) -> float:
        return b2y + b2h - (math.log10(max(v, 0.01)) - ly_th0) / (ly_th1 - ly_th0) * b2h

    for yv in (0.01, 0.03, 0.1, 0.3, 1.0, 3.0):
        gy = map_th_y(yv)
        is_lim = abs(yv - 0.3) < 1e-6
        ctx.set_source_rgb(*(COL_GREEN if is_lim else GRID_COL))
        ctx.set_line_width(1.9 if is_lim else 0.9)
        if is_lim:
            ctx.save(); ctx.set_dash([7.0, 4.0])
            ctx.move_to(b2x, gy); ctx.line_to(b2x + b2w, gy); ctx.stroke()
            ctx.restore()
        else:
            ctx.move_to(b2x, gy); ctx.line_to(b2x + b2w, gy); ctx.stroke()
        draw_text(ctx, f"{yv:g}".replace(".", ","), b2x - 8, gy, size=11.5, color=(COL_GREEN if is_lim else TEXT_MID), bold=is_lim, align="right", valign="middle")

    tslot = b2w / len(th_bars)
    for i, (tlbl, tval, tcol) in enumerate(th_bars):
        bw_i = tslot * 0.56
        bx_i = b2x + i * tslot + (tslot - bw_i) / 2.0
        by_i = map_th_y(tval)
        bh_i = (b2y + b2h) - by_i
        round_rect(ctx, bx_i, by_i, bw_i, bh_i, 4)
        ctx.set_source_rgb(*tcol)
        ctx.fill()
        draw_text(ctx, fmt_dec(tval, 3), bx_i + bw_i / 2.0, by_i - 8, size=11.5, color=tcol, bold=True, mono=True, align="center")
        l0, l1 = tlbl.split("\n")
        draw_text(ctx, l0, bx_i + bw_i / 2.0, b2y + b2h + 18, size=11.5, color=TEXT_DARK, bold=True, align="center")
        draw_text(ctx, l1, bx_i + bw_i / 2.0, b2y + b2h + 34, size=10.8, color=TEXT_MID, align="center")

    ctx.set_source_rgb(*AXIS_COL)
    ctx.set_line_width(1.5)
    ctx.move_to(b2x, b2y); ctx.line_to(b2x, b2y + b2h); ctx.line_to(b2x + b2w, b2y + b2h); ctx.stroke()
    draw_text_rot(ctx, "σ_thermal [nm] (log)", b2x - 46, b2y + b2h / 2.0, angle_deg=-90.0, size=12.0, color=TEXT_DARK, bold=True)

    # Bottom note in card B
    draw_text(
        ctx,
        "Sınırlar: σ_pointing ≤ 0,50 nm (VC-E en düşük geçerli sınıf; VC-G 3,76× ek marj) · σ_thermal ≤ 0,30 nm (Zerodur+Invar+20 mK kriyo ada)",
        rx + 18, top_y + rt_h - 16, size=11.5, color=TEXT_MID,
    )

    # ==================== RIGHT BOTTOM CARD: Exp124 Total RSS Closure ====================
    rby = top_y + rt_h + r_gap
    draw_card(ctx, rx, rby, right_w, rb_h, "C) Exp124 5 keV Toplam Yerleştirme Bütçesi Kapanışı (σ_total ≤ 3,80 nm)")

    cl = data["exp124_budget_closure"]["CFG4_V4_FULL_CTRL_VCE"]
    hr = cl["ArchB_HiRes_Ti0p25_10ms"]
    cn = cl["ArchB_HiRes_Ti0p5_15ms"]
    # Variance-share breakdown horizontal bars (visually intuitive RSS contributions proportional to sigma^2 / sigma_tot)
    rows_rss = [
        {
            "label": "Exp124 Varsayılan (HiRes)",
            "total": hr["sigma_total_exp124_orig_nm"],
            "parts": [
                ("Straggle", hr["sigma_straggle_nm"] ** 2, COL_SLATE),
                ("Spot", hr["sigma_spot_nm"] ** 2, COL_BLUE),
                ("Mek.+Termal", 0.50**2 + 0.50**2 + 0.30**2, COL_ORANGE),
                ("Tavlama", 0.50**2, COL_PURPLE),
            ],
        },
        {
            "label": "Exp133 v4.0 (HiRes, 10 ms)",
            "total": hr["sigma_total_exp133_nm"],
            "parts": [
                ("Straggle", hr["sigma_straggle_nm"] ** 2, COL_SLATE),
                ("Spot", hr["sigma_spot_nm"] ** 2, COL_BLUE),
                ("Mek.+Termal", hr["sigma_stage_nm"] ** 2 + hr["sigma_pointing_nm"] ** 2 + hr["sigma_thermal_nm"] ** 2, COL_GREEN),
                ("Tavlama", hr["sigma_anneal_nm"] ** 2, COL_PURPLE),
            ],
        },
        {
            "label": "Exp133 v4.0 (Kanonik, 15 ms)",
            "total": cn["sigma_total_exp133_nm"],
            "parts": [
                ("Straggle", cn["sigma_straggle_nm"] ** 2, COL_SLATE),
                ("Spot", cn["sigma_spot_nm"] ** 2, COL_BLUE),
                ("Mek.+Termal", cn["sigma_stage_nm"] ** 2 + cn["sigma_pointing_nm"] ** 2 + cn["sigma_thermal_nm"] ** 2, COL_GREEN),
                ("Tavlama", cn["sigma_anneal_nm"] ** 2, COL_PURPLE),
            ],
        },
    ]

    px_c = rx + 238
    pw_c = right_w - 378
    py_c = rby + 72
    bar_h = 42
    bar_gap = 24
    x_max_c = 4.05

    # Column header for right-aligned σ_total values (cleanly right of 3.80 nm line!)
    val_col_x = rx + right_w - 22
    draw_text(ctx, "σ_total", val_col_x, py_c - 18, size=12.0, color=TEXT_DARK, bold=True, align="right")

    # Vertical grid & 3.80 nm spec limit
    for xv in (0.0, 1.0, 2.0, 3.0, 3.8):
        gx = px_c + (xv / x_max_c) * pw_c
        is_lim = abs(xv - 3.8) < 1e-6
        ctx.set_source_rgb(*(COL_RED if is_lim else GRID_COL))
        ctx.set_line_width(2.0 if is_lim else 0.9)
        if is_lim:
            ctx.save(); ctx.set_dash([8.0, 4.0])
            ctx.move_to(gx, py_c - 12); ctx.line_to(gx, py_c + 3 * bar_h + 2 * bar_gap + 8); ctx.stroke()
            ctx.restore()
            draw_text(ctx, "3,80 nm Sınırı", gx, py_c - 18, size=11.5, color=COL_RED, bold=True, align="center")
        else:
            ctx.move_to(gx, py_c - 6); ctx.line_to(gx, py_c + 3 * bar_h + 2 * bar_gap + 8); ctx.stroke()
        draw_text(ctx, fmt_dec(xv, 1), gx, py_c + 3 * bar_h + 2 * bar_gap + 24, size=11.5, color=(COL_RED if is_lim else TEXT_MID), bold=is_lim, align="center")

    for i, row in enumerate(rows_rss):
        ry_i = py_c + i * (bar_h + bar_gap)
        tot = row["total"]
        var_tot = sum(v for _, v, _ in row["parts"])
        tot_w = (tot / x_max_c) * pw_c
        draw_text(ctx, row["label"], px_c - 12, ry_i + bar_h / 2.0, size=12.2, color=TEXT_DARK, bold=True, align="right", valign="middle")

        cx_bar = px_c
        for pname, pvar, pcol in row["parts"]:
            seg_w = tot_w * (pvar / var_tot)
            ctx.set_source_rgb(*pcol)
            ctx.rectangle(cx_bar, ry_i, seg_w, bar_h)
            ctx.fill()
            if seg_w > 64:
                draw_text(ctx, f"{pname}", cx_bar + seg_w / 2.0, ry_i + bar_h / 2.0, size=11.0, color=(1.0, 1.0, 1.0), bold=True, align="center", valign="middle")
            cx_bar += seg_w

        ctx.set_source_rgb(*AXIS_COL)
        ctx.set_line_width(1.2)
        ctx.rectangle(px_c, ry_i, tot_w, bar_h)
        ctx.stroke()
        draw_text(ctx, f"{fmt_dec(tot, 3)} nm", val_col_x, ry_i + bar_h / 2.0, size=13.0, color=(COL_GREEN if i > 0 else TEXT_DARK), bold=True, mono=True, align="right", valign="middle")

    # Clean 2-row legend for Panel C segments (zero crowding!)
    lg_y1 = py_c + 3 * bar_h + 2 * bar_gap + 48
    lg_y2 = lg_y1 + 24
    seg_leg_r1 = [
        ("BCA Straggle (3,259 nm)", COL_SLATE),
        ("Optik Spot (1,428–1,532 nm)", COL_BLUE),
        ("Mek.+Termal (v4: 0,182 nm)", COL_GREEN),
    ]
    seg_leg_r2 = [
        ("Exp124 Varsayılan Mek.+Th (0,768 nm)", COL_ORANGE),
        ("Tavlama Bütçesi (0,50 nm)", COL_PURPLE),
    ]
    for row_y, items, step in ((lg_y1, seg_leg_r1, 330), (lg_y2, seg_leg_r2, 390)):
        lx_c = rx + 36
        for slbl, scol in items:
            ctx.set_source_rgb(*scol)
            ctx.rectangle(lx_c, row_y - 6, 13, 13)
            ctx.fill()
            draw_text(ctx, slbl, lx_c + 19, row_y, size=11.5, color=TEXT_DARK, valign="middle")
            lx_c += step

    # CY1-CY8 Verdict Strip at bottom of Panel C
    vy_strip = rby + rb_h - 46
    round_rect(ctx, rx + 20, vy_strip, right_w - 40, 32, 6)
    ctx.set_source_rgb(0.920, 0.978, 0.948)
    ctx.fill_preserve()
    ctx.set_source_rgb(*COL_GREEN)
    ctx.set_line_width(1.3)
    ctx.stroke()
    v_count = sum(1 for v in data["verdicts"].values() if v)
    v_tot = len(data["verdicts"])
    draw_text(
        ctx,
        f"Ön-Kayıtlı Hipotez Kararları (CY1–CY8): {v_count}/{v_tot} PASS  |  CFG1 Rijit σ_total = 2.077 nm (RED) → CAD v4.0 σ_total = 3,597 nm (PASS)",
        rx + right_w / 2.0, vy_strip + 16, size=12.2, color=COL_GREEN, bold=True, align="center", valign="middle",
    )

    draw_text(
        ctx,
        "Kaynak: Exp133 (H151) · Varyans payı çubukları σ_i²/Σσ_j² oranında toplam σ_total uzunluğuna ölçeklenmiştir · no_lab_measurement=true.",
        34, H - 18, size=12.0, color=TEXT_MID,
    )

    surf.write_to_png(str(FIG2_PATH))


def main() -> None:
    data = json.loads(IN_JSON.read_text(encoding="utf-8"))
    make_figure_1(data)
    make_figure_2(data)
    print(f"Generated {FIG1_PATH.relative_to(ROOT)} and {FIG2_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
