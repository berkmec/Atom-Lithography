"""Generate 2400x1400 IEEE/Nature academic publication figure for Exp150 (H168).

Strict academic publication design system:
  - Canvas: #FFFFFF white paper (subtle technical note tint #F8F9FA)
  - Primary / Secondary ink: #111827 / #4B5563
  - Hairline borders & grids: #D1D5DB / #E5E7EB
  - Primary data accent: muted academic navy #1B365D
  - Secondary series: muted slate #64748B / #94A3B8
  - Threshold / limit / uncertified accent: muted burgundy #8B2635 (sparingly)
  - Restrained PASS accent: muted forest #2D5A3D (text/markers only)

Runs under system /usr/bin/python3 -B (PyCairo; zero numpy/matplotlib dependencies).
Reads live JSON outputs from results/exp150_industrial_safety_fmea_hazop/.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cairo

ROOT = Path(__file__).resolve().parents[2]
RES_DIR = ROOT / "results/exp150_industrial_safety_fmea_hazop"
OUT_PNG = RES_DIR / "fig_exp150_safety_fmea_hazop.png"

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
    size: float = 13.0,
    color: str = INK_PRIMARY,
    bold: bool = False,
    italic: bool = False,
    align: str = "left",
    family: str = "DejaVu Sans",
    max_w: float | None = None,
    min_size: float = 8.5,
) -> None:
    slant = cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(family, slant, weight)
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
    """Clean IEEE/Nature open L-shaped axes (top and right spines removed, 0.9pt)."""
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
    # Outward left tick mark
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
    # Outward bottom tick mark
    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(0.9)
    ctx.move_to(gx, py + ph)
    ctx.line_to(gx, py + ph + 4.0)
    ctx.stroke()


def _panel_frame(
    ctx: cairo.Context,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    title: str,
    meta: str,
    meta_color: str = INK_SECONDARY,
) -> None:
    """Crisp flat journal panel frame with hairline rule (zero drop shadow, zero neon badge)."""
    ctx.rectangle(x, y, w, h)
    ctx.set_source_rgba(*_hex(BG_PAPER))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.9)
    ctx.stroke()

    # Subtle bottom rule under panel title line
    ctx.move_to(x + 14, y + 36)
    ctx.line_to(x + w - 14, y + 36)
    ctx.set_source_rgba(*_hex(RULE_GRID))
    ctx.set_line_width(0.9)
    ctx.stroke()

    _text(ctx, label, x + 14, y + 24, size=14.0, color=ACCENT_NAVY, bold=True)
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(14.0)
    lbl_w = ctx.text_extents(label).width

    ctx.select_font_face("DejaVu Sans Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(10.5)
    meta_w = ctx.text_extents(meta).width
    _text(ctx, meta, x + w - 14, y + 23.5, size=10.5, color=meta_color, bold=True, align="right", family="DejaVu Sans Mono")
    _text(
        ctx,
        title,
        x + 14 + lbl_w + 8,
        y + 24,
        size=13.5,
        color=INK_PRIMARY,
        bold=True,
        max_w=(w - 36 - lbl_w - meta_w),
    )


def _note_box(ctx: cairo.Context, x: float, y: float, w: float, h: float) -> None:
    _rect(ctx, x, y, w, h, 2.0)
    ctx.set_source_rgba(*_hex(BG_SUBTLE))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.8)
    ctx.stroke()


def _callout_label(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    txt: str,
    border_col: str = ACCENT_BURGUNDY,
    txt_col: str = ACCENT_BURGUNDY,
    size: float = 10.2,
) -> None:
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    tw = ctx.text_extents(txt).width
    bw = tw + 16.0
    bh = 20.0
    _rect(ctx, cx - bw / 2.0, cy - bh / 2.0, bw, bh, 2.0)
    ctx.set_source_rgba(*_hex(BG_PAPER, 0.96))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(border_col, 0.75))
    ctx.set_line_width(0.9)
    ctx.stroke()
    _text(ctx, txt, cx, cy + 3.6, size=size, color=txt_col, bold=True, align="center")


def _draw_panel1_laser(ctx: cairo.Context, x: float, y: float, w: float, h: float, las: dict[str, Any]) -> None:
    _panel_frame(
        ctx, x, y, w, h,
        "(a)", "S5.5 Sınıf-4 808 nm Lazer (ANSI Z136.1 & 1oo2D Hedefi)",
        "OD8 · 3,2 ms · M0", INK_SECONDARY,
    )

    px, py, pw, ph = x + 78, y + 60, w - 102, 326
    y_min, y_max = -7.5, 2.5

    def _sy(val: float) -> float:
        lv = math.log10(max(val, 1e-8))
        return py + ph * (1.0 - (lv - y_min) / (y_max - y_min))

    for exp in (-7, -5, -3, -1, 1):
        gy = _sy(10.0 ** exp)
        _draw_hgrid(ctx, px, pw, gy)
        _text(ctx, f"1e{exp}", px - 9, gy + 3.8, size=10.5, color=INK_SECONDARY, align="right", family="DejaVu Sans Mono")

    _draw_axes_open(ctx, px, py, pw, ph)

    ctx.save()
    ctx.translate(x + 22, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "Fluans (J/cm², log10)", 0, 0, size=11.5, color=INK_PRIMARY, bold=True, align="center")
    ctx.restore()

    bars = [
        ("Yonga\nDirekt", las["wafer_fluence_J_cm2"], ACCENT_BURGUNDY, 0.85, f"{las['wafer_fluence_J_cm2']:.1f}"),
        ("Safir AR\nPencere", las["window_fluence_AR_J_cm2"], ACCENT_LIGHT_SLATE, 0.90, f"{las['window_fluence_AR_J_cm2']:.1f}"),
        ("OD6\n(FAIL)", las["od_sweep"]["OD6"]["residual_wafer_J_cm2"], ACCENT_BURGUNDY, 0.68, "4,3e-5"),
        ("OD7\n(Min)", las["od_sweep"]["OD7"]["residual_wafer_J_cm2"], ACCENT_SLATE, 0.88, "4,3e-6"),
        ("OD8\n(Tasarım)", las["od_sweep"]["OD8"]["residual_wafer_J_cm2"], ACCENT_NAVY, 0.95, "4,4e-7"),
    ]
    n = len(bars)
    slot = pw / n
    bw = slot * 0.52
    for i, (lbl, val, col, alpha, vtxt) in enumerate(bars):
        bx = px + i * slot + (slot - bw) / 2.0
        by = _sy(val)
        ctx.rectangle(bx, by, bw, (py + ph) - by)
        ctx.set_source_rgba(*_hex(col, alpha))
        ctx.fill()
        if lbl.startswith("OD7"):
            _text(ctx, vtxt, bx + bw / 2.0, by + 16, size=10.5, color=BG_PAPER, bold=True, align="center", family="DejaVu Sans Mono")
        else:
            _text(ctx, vtxt, bx + bw / 2.0, by - 7, size=10.5, color=INK_PRIMARY if col != ACCENT_BURGUNDY else ACCENT_BURGUNDY, bold=True, align="center", family="DejaVu Sans Mono")
        for li, part in enumerate(lbl.split("\n")):
            _text(ctx, part, bx + bw / 2.0, py + ph + 16 + li * 13.5, size=10.5, color=INK_PRIMARY if li == 0 else INK_SECONDARY, bold=(li == 0), align="center")

    # MPE horizontal dashed line (4-pulse eye MPE = 1.177e-5 J/cm^2)
    mpe4 = las["mpe_eye_4pulse_uJ_cm2"] * 1e-6
    ym = _sy(mpe4)
    ctx.save()
    ctx.set_dash([6.0, 4.0])
    ctx.set_source_rgba(*_hex(ACCENT_BURGUNDY))
    ctx.set_line_width(1.4)
    ctx.move_to(px, ym)
    ctx.line_to(px + pw, ym)
    ctx.stroke()
    ctx.restore()
    _callout_label(
        ctx,
        px + pw - 146,
        ym - 19,
        f"4-Darbe Göz MPE = {las['mpe_eye_4pulse_uJ_cm2']:.2f} µJ/cm²",
        border_col=ACCENT_BURGUNDY,
        txt_col=ACCENT_BURGUNDY,
        size=10.2,
    )

    # Bottom technical note box
    sy = y + 440
    _note_box(ctx, x + 16, sy, w - 32, h - (sy - y) - 14)
    il = las["interlock_sil3"]
    b10_10x = next(
        c for c in il["pfd_sensitivity_sweep"]["by_beta"]["beta_10pct"]
        if abs(c["lambda_du_multiplier"] - 10.0) < 1e-9
    )
    _text(ctx, f"NOHD (20 mrad): {las['nohd_collimated_20mrad_m']:.1f} m   |   Fiber (150 mrad): {las['nohd_fiber_150mrad_m']:.1f} m   |   NHZ_diff: {las['nhz_diffuse_m']:.2f} m", x + 28, sy + 24, size=11.4, color=INK_PRIMARY, bold=True, max_w=w - 56)
    _text(ctx, f"Gerekli OD (1 / 4 darbe): {las['od_required_1pulse_wafer']:.2f} / {las['od_required_4pulse_wafer']:.2f}  ->  OD8 Artık Oran: {las['od_sweep']['OD8']['ratio_to_4pulse_MPE_at_wafer']:.4f}× MPE (<< 1)", x + 28, sy + 49, size=11.3, color=INK_SECONDARY, max_w=w - 56)
    _text(ctx, f"1oo2D Nominal PFD = {il['pfd_avg_1oo2d']:.2e} (< 1e-3, iec61508_certified=false)  |  Perde: {il['shutter_close_ms']} ms", x + 28, sy + 74, size=11.2, color=ACCENT_NAVY, bold=True, max_w=w - 56)
    _text(ctx, f"λ_DU × β Duyarlılık: 10× λ_DU & β = %10 -> PFD = {b10_10x['pfd_avg_1oo2d']:.2e} (SIL-2 bandına bozulur)", x + 28, sy + 99, size=11.2, color=ACCENT_BURGUNDY, bold=True, max_w=w - 56)


def _draw_panel2_ph3(ctx: cairo.Context, x: float, y: float, w: float, h: float, gas: dict[str, Any]) -> None:
    _panel_frame(
        ctx, x, y, w, h,
        "(b)", "PH₃ Dağılımı (40 bar vs. SDS) & S5.6 %5 H₂/N₂",
        "0,0072 ppm · PASS", ACCENT_FOREST,
    )

    px, py, pw, ph = x + 78, y + 60, w - 102, 336
    y_min, y_max = -6.0, 3.6
    t_max = 600.0

    def _sx(t: float) -> float:
        return px + pw * (t / t_max)

    def _sy(c: float) -> float:
        lv = math.log10(max(c, 1e-6))
        lv = max(y_min, min(y_max, lv))
        return py + ph * (1.0 - (lv - y_min) / (y_max - y_min))

    for exp in (-5, -3, -1, 1, 3):
        gy = _sy(10.0 ** exp)
        _draw_hgrid(ctx, px, pw, gy)
        _text(ctx, f"1e{exp}", px - 9, gy + 3.8, size=10.5, color=INK_SECONDARY, align="right", family="DejaVu Sans Mono")
    for tv in (0, 150, 300, 450, 600):
        gx = _sx(tv)
        _draw_vgrid(ctx, gx, py, ph)
        _text(ctx, f"{tv} s", gx, py + ph + 17, size=10.5, color=INK_SECONDARY, align="center", family="DejaVu Sans Mono")

    _draw_axes_open(ctx, px, py, pw, ph)

    ctx.save()
    ctx.translate(x + 22, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "60 m³ Oda PH₃ (ppm, log10)", 0, 0, size=11.5, color=INK_PRIMARY, bold=True, align="center")
    ctx.restore()

    refs = [
        (50.0, ACCENT_BURGUNDY, [6.0, 4.0], "NIOSH IDLH = 50 ppm", 14),
        (0.05, ACCENT_SLATE, [4.0, 4.0], "ACGIH TLV-TWA = 0,05 ppm", -6),
        (gas["mitigated_sds_system"]["operator_conservative_ppm"], ACCENT_NAVY, [2.0, 3.0], "SDS Doğrudan Difüzyon = 0,0072 ppm", 14),
    ]
    for rval, rcol, dash, rlbl, dy in refs:
        ry = _sy(rval)
        ctx.save()
        ctx.set_dash(dash)
        ctx.set_source_rgba(*_hex(rcol, 0.85))
        ctx.set_line_width(1.2)
        ctx.move_to(px, ry)
        ctx.line_to(px + pw, ry)
        ctx.stroke()
        ctx.restore()
        _text(ctx, rlbl, px + pw - 6, ry + dy, size=10.2, color=rcol, bold=True, align="right")

    ts = gas["time_series"]["t_s"]
    c_hp = gas["time_series"]["hp_unmitigated_ppm"]
    c_sds = gas["time_series"]["sds_mitigated_room_ppm"]

    # Unmitigated HP cylinder curve (muted burgundy)
    ctx.set_source_rgba(*_hex(ACCENT_BURGUNDY))
    ctx.set_line_width(2.0)
    started = False
    for t, c in zip(ts, c_hp):
        if c <= 1e-6:
            continue
        sx, sy_ = _sx(t), _sy(c)
        if not started:
            ctx.move_to(sx, sy_)
            started = True
        else:
            ctx.line_to(sx, sy_)
    ctx.stroke()

    # SDS mitigated ODE curve (academic navy)
    ctx.set_source_rgba(*_hex(ACCENT_NAVY))
    ctx.set_line_width(2.0)
    started = False
    for t, c in zip(ts, c_sds):
        if c <= 1e-6:
            continue
        sx, sy_ = _sx(t), _sy(c)
        if not started:
            ctx.move_to(sx, sy_)
            started = True
        else:
            ctx.line_to(sx, sy_)
    ctx.stroke()

    _text(ctx, "40 bar / 100 g: Tepe 1.207 ppm (24,1× IDLH)", _sx(28), _sy(1207.0) - 8, size=10.8, color=ACCENT_BURGUNDY, bold=True)
    _text(ctx, "SDS + 250 CFM Scrubber + 1oo2D (12 s): Tepe 6,9e-5 ppm", _sx(24), _sy(6.9e-5) - 9, size=10.2, color=ACCENT_NAVY, bold=True)

    sy = y + 440
    _note_box(ctx, x + 16, sy, w - 32, h - (sy - y) - 14)
    sds = gas["mitigated_sds_system"]
    _text(ctx, f"SDS (<650 Torr, 10 g): Kopmada Dış Akış = 0  |  Saf Fick Difüzyonu = {sds['sds_fickian_diff_sccm']:.3f} sccm", x + 28, sy + 24, size=11.4, color=INK_PRIMARY, bold=True, max_w=w - 56)
    _text(ctx, f"Operatör Maruziyeti <= {sds['operator_conservative_ppm']:.4f} ppm  ({sds['margin_below_tlv_twa']:.1f}× < TLV-TWA, {int(sds['margin_below_idlh'])}× < IDLH)", x + 28, sy + 49, size=11.3, color=ACCENT_NAVY, bold=True, max_w=w - 56)
    _text(ctx, "Gaz Dolabı Hedefi: 250 CFM Egzoz + %99,9 Kuru Scrubber + 0,02/0,05 ppm kesme (M0 hedef)", x + 28, sy + 74, size=11.1, color=INK_SECONDARY, max_w=w - 56)
    _text(ctx, "S5.6 %5,0 H₂ / %95,0 N₂ Pasivasyon: ISO 10156 (%5,7) Altı -> Havada Doğal Alevlenmez", x + 28, sy + 99, size=11.2, color=INK_PRIMARY, max_w=w - 56)


def _draw_panel3_hv_xray(ctx: cairo.Context, x: float, y: float, w: float, h: float, hvx: dict[str, Any]) -> None:
    _panel_frame(
        ctx, x, y, w, h,
        "(c)", "10–22 keV Bremsstrahlung X-Işını & HV Crowbar",
        "< 0,01 µSv/h · PASS", ACCENT_FOREST,
    )

    e22 = hvx["energy_sweep"]["22keV"]
    crow = hvx["hv_crowbar"]
    px, py, pw, ph = x + 186, y + 60, w - 210, 290
    x_min, x_max = -25.0, 8.0

    def _sx(val: float) -> float:
        lv = math.log10(max(val, 1e-25))
        lv = max(x_min, min(x_max, lv))
        return px + pw * ((lv - x_min) / (x_max - x_min))

    for exp in (-20, -10, 0, 6):
        gx = _sx(10.0 ** exp)
        _draw_vgrid(ctx, gx, py, ph)
        _text(ctx, f"1e{exp}", gx, py + ph + 17, size=10.5, color=INK_SECONDARY, align="center", family="DejaVu Sans Mono")

    _draw_axes_open(ctx, px, py, pw, ph)

    rows = [
        ("Kalkan Yok\n(30 cm, 22 keV)", e22["unshielded_30cm_uSv_h"], ACCENT_BURGUNDY, 0.85, "8,22e6 µSv/h"),
        ("Çıplak 8 mm\nSafir (S5.5)", e22["s55_bare_sapphire_8mm_uSv_h"], ACCENT_BURGUNDY, 0.58, "10,11 µSv/h (FAIL)"),
        ("S5.5 Safir +\n3 mm Çelik Kılıf", e22["s55_sapphire_plus_3mm_steel_shroud_uSv_h"], ACCENT_NAVY, 0.95, "1,19e-23 µSv/h"),
        ("6 mm / 10 mm\n316L Oda Duvarı", 1e-25, ACCENT_SLATE, 0.90, "1,06e-43 / 2,2e-73"),
    ]
    slot = ph / len(rows)
    bh = slot * 0.46
    for i, (lbl, val, col, alpha, vtxt) in enumerate(rows):
        by = py + i * slot + (slot - bh) / 2.0
        bx_end = _sx(val)
        bar_w = max(8.0, bx_end - px)
        ctx.rectangle(px, by, bar_w, bh)
        ctx.set_source_rgba(*_hex(col, alpha))
        ctx.fill()
        for li, part in enumerate(lbl.split("\n")):
            _text(ctx, part, px - 10, by + 12 + li * 13.5, size=10.5, color=INK_PRIMARY if li == 0 else INK_SECONDARY, bold=(li == 0), align="right")
        if bar_w > 180:
            tx_in = min(px + bar_w - 8, _sx(1.0) - 10) if i == 1 else px + bar_w - 8
            _text(ctx, vtxt, tx_in, by + bh / 2.0 + 3.8, size=10.4, color=BG_PAPER, bold=True, align="right", family="DejaVu Sans Mono")
        else:
            _text(ctx, vtxt, px + bar_w + 8, by + bh / 2.0 + 3.8, size=10.4, color=ACCENT_NAVY if col == ACCENT_NAVY else INK_PRIMARY, bold=True, align="left", family="DejaVu Sans Mono")

    # ICRP 103 1.0 uSv/h vertical dashed limit line
    x_lim = _sx(1.0)
    ctx.save()
    ctx.set_dash([6.0, 4.0])
    ctx.set_source_rgba(*_hex(ACCENT_BURGUNDY))
    ctx.set_line_width(1.4)
    ctx.move_to(x_lim, py)
    ctx.line_to(x_lim, py + ph)
    ctx.stroke()
    ctx.restore()
    _callout_label(ctx, x_lim, py + ph + 36, "ICRP 103 Halk Limiti = 1,0 µSv/h", border_col=ACCENT_BURGUNDY, txt_col=ACCENT_BURGUNDY, size=10.2)

    sy = y + 432
    _note_box(ctx, x + 16, sy, w - 32, h - (sy - y) - 14)
    _text(ctx, "Kritik Bulgu: Çıplak 8 mm safir 22 keV'de 10,1 µSv/h sızdırır (>10× halk limiti).", x + 28, sy + 24, size=11.4, color=ACCENT_BURGUNDY, bold=True, max_w=w - 56)
    _text(ctx, "Çözüm: S5.5 dışına 3 mm çelik OD8 kılıf -> Çift-amaçlı Lazer + X-Işını kalkanı (1,2e-23 µSv/h)", x + 28, sy + 49, size=11.3, color=ACCENT_NAVY, bold=True, max_w=w - 56)
    _text(ctx, f"HV Crowbar (IEC 61010-1, 1,5 nF, 2 MΩ): E(10 kV)={crow['stored_energy_10kV_J']:.3f} J, E(22 kV)={crow['stored_energy_22kV_J']:.3f} J (< 0,5 J)", x + 28, sy + 75, size=11.2, color=INK_PRIMARY, max_w=w - 56)
    _text(ctx, f"Boşalım Süresi (<50 V güvenli dokunma): 10 kV -> {crow['discharge_to_50V_10kV_ms']:.1f} ms  |  22 kV -> {crow['discharge_to_50V_22kV_ms']:.1f} ms (< 50 ms)", x + 28, sy + 100, size=11.2, color=INK_SECONDARY, max_w=w - 56)


def _draw_panel4_cryo(ctx: cairo.Context, x: float, y: float, w: float, h: float, cryo: dict[str, Any]) -> None:
    _panel_frame(
        ctx, x, y, w, h,
        "(d)", "Kriyo He ODH (RK4 Kutu-ODE), ASME DN50 & Quench",
        "O₂ %20,57 · 16,4× · PASS", ACCENT_FOREST,
    )

    px, py, pw, ph = x + 68, y + 70, w - 92, 286
    y_min, y_max = 0.0, 23.5

    def _sy(v: float) -> float:
        return py + ph * (1.0 - (v - y_min) / (y_max - y_min))

    for tick in (0, 5, 10, 15, 20):
        gy = _sy(tick)
        _draw_hgrid(ctx, px, pw, gy)
        _text(ctx, f"{tick}%", px - 9, gy + 3.8, size=10.5, color=INK_SECONDARY, align="right", family="DejaVu Sans Mono")

    _draw_axes_open(ctx, px, py, pw, ph)

    ctx.save()
    ctx.translate(x + 20, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "Oda Oksijen Oranı O₂ (%)", 0, 0, size=11.5, color=INK_PRIMARY, bold=True, align="center")
    ctx.restore()

    rooms = ("15m3", "30m3", "60m3", "120m3")
    rlabels = ("15 m³\n(Servis)", "30 m³\n(Küçük)", "60 m³\n(Temizoda)", "120 m³\n(Büyük Lab)")
    sweep = cryo["helium_odh"]["room_sweep"]
    slot = pw / len(rooms)
    bw = slot * 0.28
    for i, (rk, rlbl) in enumerate(zip(rooms, rlabels)):
        rv = sweep[rk]
        cx_ = px + i * slot + slot / 2.0
        # Dry bar (academic navy; sub-OSHA 15 m^3 muted slate)
        d_val = rv["dry_ld400_pt420_O2_pct"]
        d_ok = rv["dry_passes_osha_19p5pct"]
        d_col = ACCENT_NAVY if d_ok else ACCENT_SLATE
        bx1 = cx_ - bw - 3
        by1 = _sy(d_val)
        ctx.rectangle(bx1, by1, bw, (py + ph) - by1)
        ctx.set_source_rgba(*_hex(d_col, 0.92))
        ctx.fill()
        _text(ctx, f"{d_val:.1f}%", bx1 + bw / 2.0, by1 - 6, size=10.2, color=d_col if d_ok else ACCENT_BURGUNDY, bold=True, align="center", family="DejaVu Sans Mono")
        # Wet 100 L LHe comparison bar (muted burgundy at restrained opacity)
        w_val = rv["wet_100L_LHe_comparison_O2_pct"]
        bx2 = cx_ + 3
        by2 = _sy(w_val)
        ctx.rectangle(bx2, by2, bw, max(3.0, (py + ph) - by2))
        ctx.set_source_rgba(*_hex(ACCENT_BURGUNDY, 0.65))
        ctx.fill()
        _text(ctx, f"{w_val:.1f}%", bx2 + bw / 2.0, by2 - 6, size=10.2, color=ACCENT_BURGUNDY, bold=True, align="center", family="DejaVu Sans Mono")
        for li, part in enumerate(rlbl.split("\n")):
            _text(ctx, part, cx_, py + ph + 16 + li * 13.5, size=10.5, color=INK_PRIMARY if li == 0 else INK_SECONDARY, bold=(li == 0), align="center")

    # OSHA 19.5% dashed line + restrained white-backed callout
    yo = _sy(19.5)
    ctx.save()
    ctx.set_dash([6.0, 4.0])
    ctx.set_source_rgba(*_hex(ACCENT_BURGUNDY))
    ctx.set_line_width(1.4)
    ctx.move_to(px, yo)
    ctx.line_to(px + pw, yo)
    ctx.stroke()
    ctx.restore()
    pill_cx = px + 2.5 * slot + 4.0 + (slot - bw - 8.0) / 2.0
    _callout_label(ctx, pill_cx, yo + 18, "OSHA %19,5", border_col=ACCENT_BURGUNDY, txt_col=ACCENT_BURGUNDY, size=10.0)

    # Compact legend above chart
    ctx.rectangle(px + 6, py - 21, 12, 10)
    ctx.set_source_rgba(*_hex(ACCENT_NAVY, 0.92))
    ctx.fill()
    _text(ctx, "Kuru LD400+PT420 (1,10 m³ He)", px + 24, py - 12, size=10.5, color=INK_PRIMARY, bold=True)
    ctx.rectangle(px + 258, py - 21, 12, 10)
    ctx.set_source_rgba(*_hex(ACCENT_BURGUNDY, 0.65))
    ctx.fill()
    _text(ctx, "Karşılaştırma: 100 L Islak LHe", px + 276, py - 12, size=10.5, color=INK_SECONDARY, bold=True)

    # Bottom 2 uniform subtle technical note boxes (NO pastel green/blue fills)
    sy = y + 414
    cw = (w - 44) / 2.0
    ch = h - (sy - y) - 14
    rel = cryo["asme_ovc_relief"]
    qch = cryo["magnet_quench_exp125"]

    _note_box(ctx, x + 16, sy, cw, ch)
    _text(ctx, "ASME Sec VIII OVC Tahliye (0,5 barg)", x + 28, sy + 24, size=11.4, color=ACCENT_NAVY, bold=True, max_w=cw - 24)
    _text(ctx, f"DN50 Patlama Diski: {rel['dn50_relief_capacity_he_kg_s']:.3f} kg/s He", x + 28, sy + 49, size=11.1, color=INK_PRIMARY, max_w=cw - 24)
    _text(ctx, f"En Kötü He Girişi: {rel['worst_case_he_inflow_kg_s']:.4f} kg/s", x + 28, sy + 73, size=11.1, color=INK_SECONDARY, max_w=cw - 24)
    _text(ctx, f"He Marjı: {rel['relief_safety_margin_he']:.1f}×  |  N₂ Marjı: {rel['relief_safety_margin_n2']:.1f}×", x + 28, sy + 99, size=11.3, color=ACCENT_NAVY, bold=True, max_w=cw - 24)
    _text(ctx, "(Tam Saint-Venant subsonik + paralel PRV)", x + 28, sy + 123, size=10.2, color=INK_MUTED, max_w=cw - 24)

    rx = x + 28 + cw
    _note_box(ctx, rx, sy, cw, ch)
    _text(ctx, "Exp125 8-Bobin Mıknatıs Quench", rx + 12, sy + 24, size=11.4, color=ACCENT_NAVY, bold=True, max_w=cw - 24)
    _text(ctx, f"1,50 T: {qch['E_mag_1p5T_kJ']:.2f} kJ  |  M4: {qch['E_mag_M4_0p1785T_kJ']:.3f} kJ", rx + 12, sy + 49, size=11.1, color=INK_PRIMARY, max_w=cw - 24)
    _text(ctx, f"R_dump = {qch['R_dump_ohm']:.3f} Ω  |  T_hot = {qch['T_hotspot_K']:.1f} K", rx + 12, sy + 73, size=11.1, color=INK_SECONDARY, max_w=cw - 24)
    _text(ctx, f"Direnç Tepe Sıcaklığı: {qch['dump_resistor_peak_1p5T_C']:.2f} °C (< 55 °C)", rx + 12, sy + 99, size=11.3, color=ACCENT_NAVY, bold=True, max_w=cw - 24)
    _text(ctx, f"5 Gauss (0,5 mT) Sınırı: r < {qch['pacemaker_5gauss_radius_m']:.2f} m", rx + 12, sy + 123, size=10.2, color=INK_MUTED, max_w=cw - 24)


def _draw_panel5_epo_ups(ctx: cairo.Context, x: float, y: float, w: float, h: float, epo: dict[str, Any]) -> None:
    _panel_frame(
        ctx, x, y, w, h,
        "(e)", "15 kVA Online UPS & Güvenli Kapanma Sırası",
        "0 ms · 80 ms UHV · PASS", ACCENT_FOREST,
    )

    ups = epo["ups_spec"]
    uhv = epo["uhv_isolation"]

    # Monochrome-navy academic timeline (zero rainbow bars)
    steps = [
        ("0,0 ms", "S7.SAFETY", "15 kVA LFP Online UPS kesintisiz barayı devralır (0 ms)", ACCENT_NAVY, 0.05),
        ("3,2 ms", "S5.5", "1oo2D hedef PLC 808 nm lazer sürücüsünü keser, perde kapanır", ACCENT_BURGUNDY, 0.16),
        ("18,3 ms", "S1/S2", "22 kV HV kesilir; 2 MΩ crowbar gerilimi < 50 V'a indirir", ACCENT_NAVY, 0.30),
        ("45,0 ms", "S5.6/S1", "MBE deklanşörü + 400 W PBN + SDS PH₃ hedef vana kapanır", ACCENT_NAVY, 0.44),
        ("80,0 ms", "S5 UHV", "Yay-dönüşlü all-metal UHV sürgülü vanalar mühürlenir", ACCENT_NAVY, 0.58),
        ("60 s", "S6/HPC", "Exp125 mıknatıs kontrollü inişi + Option-HPC güvenli duruş", ACCENT_SLATE, 0.78),
        ("300 s", "S6.8", "LD400 ³He/⁴He karışımı oda sıcaklığı tankına geri alınır", ACCENT_SLATE, 0.96),
    ]

    tx0, tw = x + 178, w - 200
    ty0 = y + 60
    _text(ctx, "Kapanma Aşaması (Log-Zaman İlerlemesi)", tx0, ty0 - 4, size=11.0, color=INK_SECONDARY, bold=True)

    row_h = 46
    for i, (tstr, sub, desc, col, frac) in enumerate(steps):
        ry = ty0 + 10 + i * row_h
        # Clean monochrome time stamp box
        _rect(ctx, x + 16, ry + 3, 68, 22, 2.0)
        ctx.set_source_rgba(*_hex(BG_SUBTLE))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(RULE_BORDER))
        ctx.set_line_width(0.8)
        ctx.stroke()
        _text(ctx, tstr, x + 50, ry + 18, size=10.4, color=INK_PRIMARY if col != ACCENT_BURGUNDY else ACCENT_BURGUNDY, bold=True, align="center", family="DejaVu Sans Mono")

        _text(ctx, sub, x + 92, ry + 18, size=10.5, color=INK_SECONDARY, bold=True)

        # Clean hairline track + solid bar
        bar_y = ry + 10
        ctx.rectangle(tx0, bar_y, tw, 7)
        ctx.set_source_rgba(*_hex(RULE_GRID))
        ctx.fill()
        ctx.rectangle(tx0, bar_y, max(10.0, tw * frac), 7)
        ctx.set_source_rgba(*_hex(col, 0.88))
        ctx.fill()

        _text(ctx, desc, tx0, ry + 34, size=10.6, color=INK_PRIMARY, max_w=tw)

    # Bottom UPS runtime & wafer oxidation box
    sy = y + 414
    _note_box(ctx, x + 16, sy, w - 32, h - (sy - y) - 14)

    _text(ctx, "15 kVA / 10 kWh LFP UPS Özerklik Süreleri (Verim %90):", x + 28, sy + 24, size=11.5, color=INK_PRIMARY, bold=True)
    bx, bw_max = x + 228, w - 278

    _text(ctx, "Tam Yük (13,5 kW):", x + 28, sy + 52, size=11.1, color=INK_SECONDARY)
    ctx.rectangle(bx, sy + 40, bw_max, 15)
    ctx.set_source_rgba(*_hex(RULE_GRID))
    ctx.fill()
    w1 = bw_max * (ups["runtime_at_rated_13p5kW_min"] / 240.0)
    ctx.rectangle(bx, sy + 40, w1, 15)
    ctx.set_source_rgba(*_hex(ACCENT_SLATE))
    ctx.fill()
    _text(ctx, f"{ups['runtime_at_rated_13p5kW_min']:.1f} dk (>= 30 dk)", bx + w1 + 10, sy + 51.5, size=10.8, color=INK_PRIMARY, bold=True, family="DejaVu Sans Mono")

    _text(ctx, "Tier-1 Güvenlik (2,53 kW):", x + 28, sy + 82, size=11.1, color=INK_SECONDARY)
    ctx.rectangle(bx, sy + 70, bw_max, 15)
    ctx.set_source_rgba(*_hex(RULE_GRID))
    ctx.fill()
    w2 = bw_max * min(1.0, ups["runtime_tier1_min"] / 240.0)
    ctx.rectangle(bx, sy + 70, w2, 15)
    ctx.set_source_rgba(*_hex(ACCENT_NAVY))
    ctx.fill()
    _text(ctx, f"{ups['runtime_tier1_min']:.1f} dk (>= 180 dk)", bx + 10, sy + 81.5, size=10.8, color=BG_PAPER, bold=True, family="DejaVu Sans Mono")

    _text(ctx, f"UHV Yonga Koruması: 80 ms Vana Kapanışı @ 5e-8 Torr  ->  Si(100) Oksitlenme = {uhv['wafer_oxidation_ML']:.1e} ML (<< 0,01 ML)", x + 28, sy + 116, size=11.1, color=ACCENT_NAVY, bold=True, max_w=w - 56)


def _draw_panel6_fmea(
    ctx: cairo.Context, x: float, y: float, w: float, h: float, fmea: list[dict[str, Any]], fstat: dict[str, Any], spec: dict[str, Any]
) -> None:
    _panel_frame(
        ctx, x, y, w, h,
        "(f)", "25-Satırlı FMEA (RPN Önce/Sonra) & S7.SAFETY",
        f"Max {fstat['max_rpn_pre']}->{fstat['max_rpn_post']} · PASS", ACCENT_FOREST,
    )

    px, py, pw, ph = x + 56, y + 70, w - 76, 290
    y_max = 310.0

    def _sy(v: float) -> float:
        return py + ph * (1.0 - v / y_max)

    for tick in (0, 60, 120, 180, 240, 300):
        gy = _sy(tick)
        _draw_hgrid(ctx, px, pw, gy)
        _text(ctx, str(tick), px - 8, gy + 3.8, size=10.2, color=INK_SECONDARY, align="right", family="DejaVu Sans Mono")

    _draw_axes_open(ctx, px, py, pw, ph)

    ctx.save()
    ctx.translate(x + 18, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "Risk Öncelik Puanı (RPN)", 0, 0, size=11.2, color=INK_PRIMARY, bold=True, align="center")
    ctx.restore()

    n = len(fmea)
    slot = pw / n
    bw = slot * 0.70
    for i, r in enumerate(fmea):
        bx = px + i * slot + (slot - bw) / 2.0
        # Pre-mitigation bar (muted pale slate with subtle slate hairline outline)
        y_pre = _sy(r["RPN_pre"])
        ctx.rectangle(bx, y_pre, bw, (py + ph) - y_pre)
        ctx.set_source_rgba(*_hex(ACCENT_PALE_SLATE, 0.90))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(ACCENT_LIGHT_SLATE, 0.80))
        ctx.set_line_width(0.6)
        ctx.stroke()
        # Post-mitigation overlaid bar (crisp academic navy)
        y_post = _sy(r["RPN_post"])
        ctx.rectangle(bx + 1.5, y_post, bw - 3.0, (py + ph) - y_post)
        ctx.set_source_rgba(*_hex(ACCENT_NAVY, 0.95))
        ctx.fill()
        lbl = f"{i+1:02d}"
        if i % 2 == 0 or i == 24:
            _text(ctx, lbl, bx + bw / 2.0, py + ph + 15, size=9.6, color=INK_SECONDARY, align="center", family="DejaVu Sans Mono")

    _text(ctx, "FMEA Hata Modu İndeksi (FM-01 .. FM-25: S1–S9 + Tesis)", px + pw / 2.0, py + ph + 31, size=10.6, color=INK_SECONDARY, align="center")

    # RPN <= 60 threshold dashed line (muted burgundy) + white-backed label
    y60 = _sy(60.0)
    ctx.save()
    ctx.set_dash([6.0, 4.0])
    ctx.set_source_rgba(*_hex(ACCENT_BURGUNDY))
    ctx.set_line_width(1.4)
    ctx.move_to(px, y60)
    ctx.line_to(px + pw, y60)
    ctx.stroke()
    ctx.restore()
    _callout_label(ctx, px + pw - 102, y60 - 16, "Hedef RPN <= 60 (0/25 İhlal)", border_col=ACCENT_BURGUNDY, txt_col=ACCENT_BURGUNDY, size=10.2)

    # Legend above chart
    ctx.rectangle(px + 6, py - 21, 12, 10)
    ctx.set_source_rgba(*_hex(ACCENT_PALE_SLATE))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex(ACCENT_LIGHT_SLATE))
    ctx.set_line_width(0.7)
    ctx.stroke()
    _text(ctx, f"Önce (Ort. {fstat['mean_rpn_pre']}, Maks. {fstat['max_rpn_pre']})", px + 24, py - 12, size=10.5, color=INK_SECONDARY, bold=True)
    ctx.rectangle(px + 258, py - 21, 12, 10)
    ctx.set_source_rgba(*_hex(ACCENT_NAVY))
    ctx.fill()
    _text(ctx, f"Sonra (Ort. {fstat['mean_rpn_post']}, Maks. {fstat['max_rpn_post']}, -%{fstat['mean_rpn_reduction_pct']})", px + 276, py - 12, size=10.5, color=ACCENT_NAVY, bold=True)

    # Bottom S7.SAFETY BOM v7.0 summary box
    sy = y + 414
    _note_box(ctx, x + 16, sy, w - 32, h - (sy - y) - 14)
    tot = spec["totals"]
    sc = fstat["sil_counts"]
    _text(ctx, "S7.SAFETY-01..06 Ön Emniyet Kiti Tasarım Hedefi (BOM v7.0, iec61508_certified=false):", x + 28, sy + 24, size=11.2, color=INK_PRIMARY, bold=True, max_w=w - 56)
    _text(ctx, f"Kütle: {tot['total_mass_kg']:.1f} kg  |  Güç: {tot['steady_electrical_power_W']:.0f} W  |  Kriyo Yükü: {tot['cryo_load_W']:.1f} W", x + 28, sy + 48, size=11.2, color=INK_SECONDARY, max_w=w - 56)
    _text(ctx, f"Parametrik Bütçe: ${tot['cost_usd_low']:,} – ${tot['cost_usd_nom']:,} – ${tot['cost_usd_high']:,} (M3 v6.0 BOM'un %{tot['pct_of_m3_v6_full_bom']:.2f}'i)", x + 28, sy + 72, size=11.1, color=ACCENT_NAVY, bold=True, max_w=w - 56)
    _text(ctx, f"SIL Hedef Dağılımı (Sertifikasız M0): {sc['SIL-3']}× SIL-3 hedefi | {sc['SIL-2']}× SIL-2 hedefi | {sc['SIL-1']}× SIL-1 hedefi", x + 28, sy + 96, size=10.6, color=INK_PRIMARY, max_w=w - 56)
    _text(ctx, "01: SDS PH₃ ($42k) · 02: OD8 Perde ($22k) · 03: 1oo2D PLC ($28k) · 04: UPS ($24k) · 05: O₂/DN50 ($14k) · 06: UHV ($15k)", x + 28, sy + 122, size=9.9, color=INK_MUTED, max_w=w - 56)


def main() -> None:
    data = json.loads((RES_DIR / "exp150.json").read_text(encoding="utf-8"))
    spec = json.loads((RES_DIR / "s_safety_spec.json").read_text(encoding="utf-8"))

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    # Crisp white paper canvas
    ctx.set_source_rgba(*_hex(BG_PAPER))
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Academic publication header (clean white paper + crisp bottom rule — zero dark banner)
    _text(
        ctx,
        "EXP150 (H168) — Ön Emniyet Tasarım Hedefi, HAZOP ve 25-Satırlı FMEA Analizi",
        28, 38, size=21.5, color=INK_PRIMARY, bold=True, max_w=W - 560,
    )
    _text(
        ctx,
        "Sertifikasız M0 Ön Tasarım Taraması (SEMI S2 sertifikası vermez; bağımsız IEC 61508 SIL değerlendirmesi yoktur)  ·  Referans: ANSI Z136.1 / OSHA / ICRP 103 / ASME VIII",
        28, 63, size=12.0, color=INK_SECONDARY, max_w=W - 560,
    )

    # Restrained plain-bordered header stamps on top right
    fstat = data["fmea_summary"]
    stamps = [
        (W - 524, 152, f"SF1–SF7: {data['criteria_passed']} PASS", ACCENT_FOREST),
        (W - 360, 166, f"RPN: {fstat['max_rpn_pre']} -> {fstat['max_rpn_post']}", ACCENT_NAVY),
        (W - 182, 154, "SERTİFİKASIZ M0", ACCENT_BURGUNDY),
    ]
    for sx, sw, stxt, scol in stamps:
        _rect(ctx, sx, 22, sw, 34, 2.0)
        ctx.set_source_rgba(*_hex(BG_SUBTLE))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(RULE_BORDER))
        ctx.set_line_width(0.9)
        ctx.stroke()
        _text(ctx, stxt, sx + sw / 2.0, 43.5, size=12.0, color=scol, bold=True, align="center", family="DejaVu Sans Mono")

    # Crisp IEEE/Nature top header rule
    ctx.set_source_rgba(*_hex(INK_PRIMARY))
    ctx.set_line_width(1.6)
    ctx.move_to(28, 78)
    ctx.line_to(W - 28, 78)
    ctx.stroke()

    # Unified 6-column academic summary metrics strip (NO cartoon rainbow KPI cards)
    las = data["hazard_1_laser_s55"]
    gas = data["hazard_2_ph3_and_forming_gas"]
    hvx = data["hazard_3_hv_and_xray"]
    cryo = data["hazard_4_cryo_odh_and_quench"]
    epo = data["hazard_5_epo_ups_shutdown"]
    tot = spec["totals"]
    kpis = [
        ("S5.5 SINIF-4 LAZER", f"OD8 · {las['interlock_sil3']['shutter_close_ms']} ms", f"NOHD {las['nohd_collimated_20mrad_m']:.0f} m  |  PFD {las['interlock_sil3']['pfd_avg_1oo2d']:.1e}"),
        ("S1.1 PH₃ FOSFİN (SDS)", f"{gas['mitigated_sds_system']['operator_conservative_ppm']:.4f} ppm", f"{gas['mitigated_sds_system']['margin_below_tlv_twa']:.0f}× < TLV  |  6990× < IDLH"),
        ("22 keV X-IŞINI & HV", "1,2e-23 µSv/h", f"Crowbar {hvx['hv_crowbar']['discharge_to_50V_22kV_ms']:.1f} ms  |  {hvx['hv_crowbar']['stored_energy_22kV_J']:.2f} J"),
        ("KRİYO He ODH & QUENCH", f"O₂ %{cryo['helium_odh']['room_sweep']['60m3']['dry_ld400_pt420_O2_pct']:.2f}", f"DN50 {cryo['asme_ovc_relief']['relief_safety_margin']:.1f}×  |  Dump {cryo['magnet_quench_exp125']['dump_resistor_peak_1p5T_C']:.2f} °C"),
        ("15 kVA UPS & UHV", "0 ms · 80 ms", f"40 / 213 dk  |  {epo['uhv_isolation']['wafer_oxidation_ML']:.0e} ML"),
        ("S7.SAFETY KİTİ (v7.0)", f"${tot['cost_usd_nom']//1000}k (%{tot['pct_of_m3_v6_full_bom']:.2f})", f"{tot['total_mass_kg']:.0f} kg  |  {tot['steady_electrical_power_W']:.0f} W  |  0 W Kriyo"),
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
        _text(ctx, kt, kx + 16, strip_y + 20, size=10.2, color=INK_SECONDARY, bold=True, max_w=col_w - 28)
        _text(ctx, kv, kx + 16, strip_y + 46, size=19.0, color=ACCENT_NAVY, bold=True, max_w=col_w - 28)
        _text(ctx, ks, kx + 16, strip_y + 66, size=10.3, color=INK_SECONDARY, family="DejaVu Sans Mono", max_w=col_w - 28)

    # 2x3 Grid of 6 academic panels
    pw = (W - 56 - 32) / 3.0
    r1y, r1h = 186, 574
    r2y, r2h = 776, 574
    xs = [28, 28 + pw + 16, 28 + 2 * (pw + 16)]

    _draw_panel1_laser(ctx, xs[0], r1y, pw, r1h, las)
    _draw_panel2_ph3(ctx, xs[1], r1y, pw, r1h, gas)
    _draw_panel3_hv_xray(ctx, xs[2], r1y, pw, r1h, hvx)

    _draw_panel4_cryo(ctx, xs[0], r2y, pw, r2h, cryo)
    _draw_panel5_epo_ups(ctx, xs[1], r2y, pw, r2h, epo)
    _draw_panel6_fmea(ctx, xs[2], r2y, pw, r2h, data["fmea_25_rows"], fstat, spec)

    # Crisp footer hairline + caption metadata
    ctx.set_source_rgba(*_hex(RULE_BORDER))
    ctx.set_line_width(0.8)
    ctx.move_to(28, H - 34)
    ctx.line_to(W - 28, H - 34)
    ctx.stroke()
    _text(
        ctx,
        "Kaynak: results/exp150_industrial_safety_fmea_hazop/exp150.json & s_safety_spec.json  |  Çapalar: CAD v6.0, Exp125, Exp128, Exp130, Exp139",
        28, H - 14, size=10.8, color=INK_SECONDARY,
    )
    _text(
        ctx,
        "Epistemik (TRL 1–2 / M0): iec61508_certified=false · semi_s2_certified=false · requires_third_party_assessment=true · no_lab_measurement=true",
        W - 28, H - 14, size=10.5, color=INK_MUTED, align="right", family="DejaVu Sans Mono",
    )

    surf.write_to_png(str(OUT_PNG))
    print(f"Wrote {OUT_PNG} ({W}x{H})")


if __name__ == "__main__":
    main()
