"""Generate 2400x1400 PyCairo industrial safety, HAZOP & 25-row FMEA dashboard for Exp150 (H168).

Runs under system /usr/bin/python3 -B (PyCairo + Pillow; zero numpy/matplotlib dependencies).
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


def _hex(h: str, a: float = 1.0) -> tuple[float, float, float, float]:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, a)


def _rrect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 10.0) -> None:
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
    size: float = 14.0,
    color: str = "#0F172A",
    bold: bool = False,
    align: str = "left",
    family: str = "DejaVu Sans",
) -> None:
    ctx.select_font_face(
        family,
        cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
    )
    ctx.set_font_size(size)
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


def _panel_card(
    ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, badge: str, badge_bg: str
) -> None:
    _rrect(ctx, x, y, w, h, 12)
    ctx.set_source_rgba(*_hex("#FFFFFF"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#CBD5E1"))
    ctx.set_line_width(1.4)
    ctx.stroke()

    # Header bar
    ctx.save()
    _rrect(ctx, x, y, w, h, 12)
    ctx.clip()
    ctx.rectangle(x, y, w, 40)
    ctx.set_source_rgba(*_hex("#F8FAFC"))
    ctx.fill()
    ctx.move_to(x, y + 40)
    ctx.line_to(x + w, y + 40)
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.set_line_width(1.2)
    ctx.stroke()
    ctx.restore()

    _text(ctx, title, x + 14, y + 26, size=14.5, color="#0F172A", bold=True)

    # Right pill badge
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(11.5)
    bw = ctx.text_extents(badge).width + 18
    bx = x + w - bw - 12
    _rrect(ctx, bx, y + 9, bw, 22, 6)
    ctx.set_source_rgba(*_hex(badge_bg))
    ctx.fill()
    _text(ctx, badge, bx + bw / 2.0, y + 24, size=11.5, color="#FFFFFF", bold=True, align="center")


def _draw_panel1_laser(ctx: cairo.Context, x: float, y: float, w: float, h: float, las: dict[str, Any]) -> None:
    _panel_card(ctx, x, y, w, h, "1. S5.5 Sınıf-4 808 nm Lazer (ANSI Z136.1 & SIL-3)", "OD8 · 3,2 ms · PASS", "#059669")

    px, py, pw, ph = x + 78, y + 66, w - 104, 326
    y_min, y_max = -7.5, 2.5

    def _sy(val: float) -> float:
        lv = math.log10(max(val, 1e-8))
        return py + ph * (1.0 - (lv - y_min) / (y_max - y_min))

    # Grid lines
    for exp in (-7, -5, -3, -1, 1):
        gy = _sy(10.0 ** exp)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.set_line_width(1.0)
        ctx.stroke()
        _text(ctx, f"1e{exp}", px - 8, gy + 4, size=11.0, color="#475569", align="right", family="DejaVu Sans Mono")

    # Axes
    ctx.set_source_rgba(*_hex("#334155"))
    ctx.set_line_width(1.5)
    ctx.move_to(px, py)
    ctx.line_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()

    # Rotated Y label
    ctx.save()
    ctx.translate(x + 22, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "Fluans (J/cm², log10)", 0, 0, size=12.0, color="#334155", bold=True, align="center")
    ctx.restore()

    bars = [
        ("Yonga\nDirekt", las["wafer_fluence_J_cm2"], "#DC2626", f"{las['wafer_fluence_J_cm2']:.1f}"),
        ("Safir AR\nPencere", las["window_fluence_AR_J_cm2"], "#EA580C", f"{las['window_fluence_AR_J_cm2']:.1f}"),
        ("OD6\n(FAIL)", las["od_sweep"]["OD6"]["residual_wafer_J_cm2"], "#EF4444", "4,3e-5"),
        ("OD7\n(Min)", las["od_sweep"]["OD7"]["residual_wafer_J_cm2"], "#2563EB", "4,3e-6"),
        ("OD8\n(Tasarım)", las["od_sweep"]["OD8"]["residual_wafer_J_cm2"], "#059669", "4,4e-7"),
    ]
    n = len(bars)
    slot = pw / n
    bw = slot * 0.56
    for i, (lbl, val, col, vtxt) in enumerate(bars):
        bx = px + i * slot + (slot - bw) / 2.0
        by = _sy(val)
        _rrect(ctx, bx, by, bw, (py + ph) - by, 4)
        ctx.set_source_rgba(*_hex(col, 0.88))
        ctx.fill()
        if lbl.startswith("OD7"):
            _text(ctx, vtxt, bx + bw / 2.0, by + 16, size=11.2, color="#FFFFFF", bold=True, align="center")
        else:
            _text(ctx, vtxt, bx + bw / 2.0, by - 7, size=11.5, color=col, bold=True, align="center")
        for li, part in enumerate(lbl.split("\n")):
            _text(ctx, part, bx + bw / 2.0, py + ph + 16 + li * 14, size=11.0, color="#1E293B", bold=(li == 0), align="center")

    # MPE horizontal dashed line (4-pulse eye MPE = 1.177e-5 J/cm^2)
    mpe4 = las["mpe_eye_4pulse_uJ_cm2"] * 1e-6
    ym = _sy(mpe4)
    ctx.save()
    ctx.set_dash([7, 5])
    ctx.set_source_rgba(*_hex("#B45309"))
    ctx.set_line_width(2.0)
    ctx.move_to(px, ym)
    ctx.line_to(px + pw, ym)
    ctx.stroke()
    ctx.restore()
    # Badge right-aligned above MPE line in clean open area above OD7/OD8
    _rrect(ctx, px + pw - 276, ym - 30, 270, 22, 5)
    ctx.set_source_rgba(*_hex("#FEF3C7", 0.98))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#D97706"))
    ctx.set_line_width(1.1)
    ctx.stroke()
    _text(ctx, f"4-Darbe Göz MPE = {las['mpe_eye_4pulse_uJ_cm2']:.2f} µJ/cm²", px + pw - 141, ym - 15, size=11.0, color="#92400E", bold=True, align="center")

    # Bottom technical summary card
    sy = y + 444
    _rrect(ctx, x + 16, sy, w - 32, h - (sy - y) - 14, 8)
    ctx.set_source_rgba(*_hex("#F8FAFC"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, f"NOHD (20 mrad): {las['nohd_collimated_20mrad_m']:.1f} m   |   Fiber (150 mrad): {las['nohd_fiber_150mrad_m']:.1f} m   |   NHZ_diff: {las['nhz_diffuse_m']:.2f} m", x + 28, sy + 24, size=12.0, color="#0F172A", bold=True)
    _text(ctx, f"Gerekli OD (1 / 4 darbe): {las['od_required_1pulse_wafer']:.2f} / {las['od_required_4pulse_wafer']:.2f}  ->  OD8 Artık Oran: {las['od_sweep']['OD8']['ratio_to_4pulse_MPE_at_wafer']:.4f}x MPE (<< 1)", x + 28, sy + 48, size=12.0, color="#334155")
    _text(ctx, f"1oo2D SIL-3 Kilitleme: <0,1 ms Diyot Kesici + {las['interlock_sil3']['shutter_close_ms']} ms Perde  |  PFD_avg = {las['interlock_sil3']['pfd_avg_1oo2d']:.2e} (< 1e-3)", x + 28, sy + 72, size=12.0, color="#047857", bold=True)
    _text(ctx, "Sonuç: OD>=8 Kilitli Muhafaza ile Gömülü Sınıf-1 (Class 1) Temizoda İşletimi", x + 28, sy + 96, size=11.5, color="#475569")


def _draw_panel2_ph3(ctx: cairo.Context, x: float, y: float, w: float, h: float, gas: dict[str, Any]) -> None:
    _panel_card(ctx, x, y, w, h, "2. PH₃ Dağılımı (40 bar vs SDS) & S5.6 %5 H₂/N₂", "0,0072 ppm · PASS", "#059669")

    px, py, pw, ph = x + 80, y + 66, w - 106, 336
    y_min, y_max = -6.0, 3.6
    t_max = 600.0

    def _sx(t: float) -> float:
        return px + pw * (t / t_max)

    def _sy(c: float) -> float:
        lv = math.log10(max(c, 1e-6))
        lv = max(y_min, min(y_max, lv))
        return py + ph * (1.0 - (lv - y_min) / (y_max - y_min))

    # Grid
    for exp in (-5, -3, -1, 1, 3):
        gy = _sy(10.0 ** exp)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.set_line_width(1.0)
        ctx.stroke()
        _text(ctx, f"1e{exp}", px - 8, gy + 4, size=11.0, color="#475569", align="right", family="DejaVu Sans Mono")
    for tv in (0, 150, 300, 450, 600):
        gx = _sx(tv)
        ctx.move_to(gx, py)
        ctx.line_to(gx, py + ph)
        ctx.set_source_rgba(*_hex("#F1F5F9"))
        ctx.set_line_width(1.0)
        ctx.stroke()
        _text(ctx, f"{tv} s", gx, py + ph + 16, size=11.0, color="#475569", align="center")

    # Axes
    ctx.set_source_rgba(*_hex("#334155"))
    ctx.set_line_width(1.5)
    ctx.move_to(px, py)
    ctx.line_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()

    ctx.save()
    ctx.translate(x + 22, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "60 m³ Oda PH₃ (ppm, log10)", 0, 0, size=12.0, color="#334155", bold=True, align="center")
    ctx.restore()

    # Reference threshold lines
    refs = [
        (50.0, "#B91C1C", "NIOSH IDLH = 50 ppm", 14),
        (0.05, "#D97706", "ACGIH TLV-TWA = 0,05 ppm", -6),
        (gas["mitigated_sds_system"]["operator_conservative_ppm"], "#047857", "SDS Doğrudan Difüzyon = 0,0072 ppm", 14),
    ]
    for rval, rcol, rlbl, dy in refs:
        ry = _sy(rval)
        ctx.save()
        ctx.set_dash([6, 4])
        ctx.set_source_rgba(*_hex(rcol, 0.85))
        ctx.set_line_width(1.6)
        ctx.move_to(px, ry)
        ctx.line_to(px + pw, ry)
        ctx.stroke()
        ctx.restore()
        _text(ctx, rlbl, px + pw - 6, ry + dy, size=10.8, color=rcol, bold=True, align="right")

    # Curves from live time_series
    ts = gas["time_series"]["t_s"]
    c_hp = gas["time_series"]["hp_unmitigated_ppm"]
    c_sds = gas["time_series"]["sds_mitigated_room_ppm"]

    # HP cylinder curve
    ctx.set_source_rgba(*_hex("#DC2626"))
    ctx.set_line_width(2.6)
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

    # SDS mitigated cabinet-fugitive ODE curve
    ctx.set_source_rgba(*_hex("#0EA5E9"))
    ctx.set_line_width(2.5)
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

    # Peak annotation on HP curve
    _text(ctx, "40 bar / 100 g: Tepe 1.207 ppm (24,1x IDLH!)", _sx(32), _sy(1207.0) - 8, size=11.5, color="#B91C1C", bold=True)
    _text(ctx, "SDS + 250 CFM Scrubber + SIL-3 (12 s): Tepe 6,9e-5 ppm", _sx(28), _sy(6.9e-5) - 9, size=11.0, color="#0369A1", bold=True)

    # Bottom summary box
    sy = y + 444
    _rrect(ctx, x + 16, sy, w - 32, h - (sy - y) - 14, 8)
    ctx.set_source_rgba(*_hex("#F8FAFC"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    sds = gas["mitigated_sds_system"]
    _text(ctx, f"SDS (<650 Torr, 10 g): Kopmada Dış Akış = 0  |  Saf Fick Difüzyonu = {sds['sds_fickian_diff_sccm']:.3f} sccm", x + 28, sy + 24, size=12.0, color="#0F172A", bold=True)
    _text(ctx, f"Operatör Maruziyeti <= {sds['operator_conservative_ppm']:.4f} ppm  ({sds['margin_below_tlv_twa']:.1f}x < TLV-TWA, {int(sds['margin_below_idlh'])}x < IDLH)", x + 28, sy + 48, size=12.0, color="#047857", bold=True)
    _text(ctx, "Gaz Dolabı: 250 CFM Egzoz + %99,9 Kuru Scrubber + 0,02/0,05 ppm SIL-3 Kesme", x + 28, sy + 72, size=11.8, color="#334155")
    _text(ctx, "S5.6 %5,0 H₂ / %95,0 N₂ Pasivasyon: ISO 10156 (%5,7) Altı -> Havada Doğal Alevlenmez", x + 28, sy + 96, size=11.8, color="#0369A1", bold=True)


def _draw_panel3_hv_xray(ctx: cairo.Context, x: float, y: float, w: float, h: float, hvx: dict[str, Any]) -> None:
    _panel_card(ctx, x, y, w, h, "3. 10–22 keV Bremsstrahlung X-Işını & HV Crowbar", "< 0,01 µSv/h · PASS", "#059669")

    e22 = hvx["energy_sweep"]["22keV"]
    crow = hvx["hv_crowbar"]
    px, py, pw, ph = x + 190, y + 66, w - 216, 290
    # Log axis from 10^-25 to 10^+8 (deep barriers clamped to -25 with exact label!)
    x_min, x_max = -25.0, 8.0

    def _sx(val: float) -> float:
        lv = math.log10(max(val, 1e-25))
        lv = max(x_min, min(x_max, lv))
        return px + pw * ((lv - x_min) / (x_max - x_min))

    # Vertical grid
    for exp in (-20, -10, 0, 6):
        gx = _sx(10.0 ** exp)
        ctx.move_to(gx, py)
        ctx.line_to(gx, py + ph)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.set_line_width(1.0)
        ctx.stroke()
        _text(ctx, f"1e{exp}", gx, py + ph + 16, size=10.8, color="#475569", align="center", family="DejaVu Sans Mono")

    ctx.set_source_rgba(*_hex("#334155"))
    ctx.set_line_width(1.4)
    ctx.move_to(px, py)
    ctx.line_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()

    rows = [
        ("Kalkan Yok\n(30 cm, 22 keV)", e22["unshielded_30cm_uSv_h"], "#DC2626", "8,22e6 µSv/h"),
        ("Çıplak 8 mm\nSafir (S5.5!)", e22["s55_bare_sapphire_8mm_uSv_h"], "#EA580C", "10,11 µSv/h (FAIL!)"),
        ("S5.5 Safir +\n3 mm Çelik Kılıf", e22["s55_sapphire_plus_3mm_steel_shroud_uSv_h"], "#059669", "1,19e-23 µSv/h"),
        ("6 mm / 10 mm\n316L Oda Duvarı", 1e-25, "#047857", "1,06e-43 / 2,2e-73"),
    ]
    slot = ph / len(rows)
    bh = slot * 0.50
    for i, (lbl, val, col, vtxt) in enumerate(rows):
        by = py + i * slot + (slot - bh) / 2.0
        bx_end = _sx(val)
        bar_w = max(8.0, bx_end - px)
        _rrect(ctx, px, by, bar_w, bh, 4)
        ctx.set_source_rgba(*_hex(col, 0.86))
        ctx.fill()
        for li, part in enumerate(lbl.split("\n")):
            _text(ctx, part, px - 10, by + 13 + li * 14, size=11.0, color="#1E293B", bold=(li == 0), align="right")
        # Place value text cleanly inside or to the right of bar (avoiding 1e0 limit line)
        if bar_w > 180:
            tx_in = min(px + bar_w - 8, _sx(1.0) - 10) if i == 1 else px + bar_w - 8
            _text(ctx, vtxt, tx_in, by + bh / 2.0 + 4, size=11.0, color="#FFFFFF", bold=True, align="right")
        else:
            _text(ctx, vtxt, px + bar_w + 8, by + bh / 2.0 + 4, size=11.0, color=col, bold=True, align="left")

    # ICRP 103 1.0 uSv/h limit line (stops cleanly at axis; pill placed below tick labels!)
    x_lim = _sx(1.0)
    ctx.save()
    ctx.set_dash([6, 4])
    ctx.set_source_rgba(*_hex("#B91C1C"))
    ctx.set_line_width(2.0)
    ctx.move_to(x_lim, py)
    ctx.line_to(x_lim, py + ph)
    ctx.stroke()
    ctx.restore()
    _rrect(ctx, x_lim - 118, py + ph + 24, 236, 22, 5)
    ctx.set_source_rgba(*_hex("#FEE2E2", 0.96))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#DC2626"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, "ICRP 103 Halk Limiti = 1,0 µSv/h", x_lim, py + ph + 39, size=11.0, color="#991B1B", bold=True, align="center")

    # Bottom technical summary card
    sy = y + 434
    _rrect(ctx, x + 16, sy, w - 32, h - (sy - y) - 14, 8)
    ctx.set_source_rgba(*_hex("#F8FAFC"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, "Kritik Bulgu: Çıplak 8 mm safir 22 keV'de 10,1 µSv/h sızdırır (>10x limit)!", x + 28, sy + 24, size=12.0, color="#B91C1C", bold=True)
    _text(ctx, "Çözüm: S5.5 dışına 3 mm çelik OD8 kılıf -> Çift-amaçlı Lazer + X-Işını kalkanı (1,2e-23 µSv/h)", x + 28, sy + 48, size=11.8, color="#047857", bold=True)
    _text(ctx, f"HV Crowbar (IEC 61010-1, 1,5 nF, 2 MΩ): E(10 kV)={crow['stored_energy_10kV_J']:.3f} J, E(22 kV)={crow['stored_energy_22kV_J']:.3f} J (<0,5 J)", x + 28, sy + 74, size=11.8, color="#0F172A")
    _text(ctx, f"Boşalım Süresi (<50 V güvenli dokunma): 10 kV -> {crow['discharge_to_50V_10kV_ms']:.1f} ms  |  22 kV -> {crow['discharge_to_50V_22kV_ms']:.1f} ms (<50 ms)", x + 28, sy + 98, size=11.8, color="#334155")


def _draw_panel4_cryo(ctx: cairo.Context, x: float, y: float, w: float, h: float, cryo: dict[str, Any]) -> None:
    _panel_card(ctx, x, y, w, h, "4. Kriyo He ODH, ASME DN50 Tahliye & Quench", "O₂ %20,57 · 16,4x · PASS", "#059669")

    px, py, pw, ph = x + 68, y + 72, w - 92, 290
    y_min, y_max = 0.0, 23.0

    def _sy(v: float) -> float:
        return py + ph * (1.0 - (v - y_min) / (y_max - y_min))

    for tick in (0, 5, 10, 15, 20):
        gy = _sy(tick)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.set_line_width(1.0)
        ctx.stroke()
        _text(ctx, f"{tick}%", px - 8, gy + 4, size=11.0, color="#475569", align="right", family="DejaVu Sans Mono")

    ctx.set_source_rgba(*_hex("#334155"))
    ctx.set_line_width(1.5)
    ctx.move_to(px, py)
    ctx.line_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()

    ctx.save()
    ctx.translate(x + 20, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "Oda Oksijen Oranı O₂ (%)", 0, 0, size=12.0, color="#334155", bold=True, align="center")
    ctx.restore()

    rooms = ("15m3", "30m3", "60m3", "120m3")
    rlabels = ("15 m³\n(Servis)", "30 m³\n(Küçük)", "60 m³\n(Temizoda)", "120 m³\n(Büyük Lab)")
    sweep = cryo["helium_odh"]["room_sweep"]
    slot = pw / len(rooms)
    bw = slot * 0.30
    for i, (rk, rlbl) in enumerate(zip(rooms, rlabels)):
        rv = sweep[rk]
        cx_ = px + i * slot + slot / 2.0
        # Dry bar
        d_val = rv["dry_ld400_pt420_O2_pct"]
        d_col = "#059669" if rv["dry_passes_osha_19p5pct"] else "#D97706"
        bx1 = cx_ - bw - 4
        by1 = _sy(d_val)
        _rrect(ctx, bx1, by1, bw, (py + ph) - by1, 4)
        ctx.set_source_rgba(*_hex(d_col, 0.90))
        ctx.fill()
        _text(ctx, f"{d_val:.1f}%", bx1 + bw / 2.0, by1 - 6, size=11.0, color=d_col, bold=True, align="center")
        # Wet 100L LHe comparison bar
        w_val = rv["wet_100L_LHe_comparison_O2_pct"]
        bx2 = cx_ + 4
        by2 = _sy(w_val)
        _rrect(ctx, bx2, by2, bw, max(3.0, (py + ph) - by2), 4)
        ctx.set_source_rgba(*_hex("#DC2626", 0.80))
        ctx.fill()
        _text(ctx, f"{w_val:.1f}%", bx2 + bw / 2.0, by2 - 6, size=10.8, color="#B91C1C", bold=True, align="center")
        for li, part in enumerate(rlbl.split("\n")):
            _text(ctx, part, cx_, py + ph + 16 + li * 14, size=11.0, color="#1E293B", bold=(li == 0), align="center")

    # OSHA 19.5% dashed line + crisp pill centered cleanly in the open valley over red 60 m^3 bar
    yo = _sy(19.5)
    ctx.save()
    ctx.set_dash([6, 4])
    ctx.set_source_rgba(*_hex("#B45309"))
    ctx.set_line_width(1.8)
    ctx.move_to(px, yo)
    ctx.line_to(px + pw, yo)
    ctx.stroke()
    ctx.restore()
    pill_cx = px + 2.5 * slot + 4.0 + (slot - bw - 8.0) / 2.0
    pill_w = 104.0
    _rrect(ctx, pill_cx - pill_w / 2.0, yo + 8, pill_w, 20, 4)
    ctx.set_source_rgba(*_hex("#FEF3C7", 0.98))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#D97706"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, "OSHA %19,5", pill_cx, yo + 22, size=10.8, color="#92400E", bold=True, align="center")

    # Compact legend at top-left inside whitespace above wet bars
    _rrect(ctx, px + 8, py - 24, 14, 12, 2)
    ctx.set_source_rgba(*_hex("#059669"))
    ctx.fill()
    _text(ctx, "Kuru LD400+PT420 (1,10 m³ He)", px + 28, py - 14, size=11.0, color="#0F172A", bold=True)
    _rrect(ctx, px + 260, py - 24, 14, 12, 2)
    ctx.set_source_rgba(*_hex("#DC2626", 0.80))
    ctx.fill()
    _text(ctx, "Karşılaştırma: 100 L Islak LHe", px + 280, py - 14, size=11.0, color="#B91C1C", bold=True)

    # Bottom 2 split metric cards
    sy = y + 416
    cw = (w - 44) / 2.0
    ch = h - (sy - y) - 14
    rel = cryo["asme_ovc_relief"]
    qch = cryo["magnet_quench_exp125"]

    # Left: ASME DN50
    _rrect(ctx, x + 16, sy, cw, ch, 8)
    ctx.set_source_rgba(*_hex("#F0FDF4"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#86EFAC"))
    ctx.set_line_width(1.2)
    ctx.stroke()
    _text(ctx, "ASME Sec VIII OVC Tahliye (0,5 barg)", x + 28, sy + 24, size=12.0, color="#065F46", bold=True)
    _text(ctx, f"DN50 Patlama Diski: {rel['dn50_relief_capacity_he_kg_s']:.3f} kg/s He", x + 28, sy + 50, size=11.5, color="#0F172A")
    _text(ctx, f"En Kötü He Girişi: {rel['worst_case_he_inflow_kg_s']:.4f} kg/s", x + 28, sy + 74, size=11.5, color="#334155")
    _text(ctx, f"He Marjı: {rel['relief_safety_margin_he']:.1f}x  |  N₂ Marjı: {rel['relief_safety_margin_n2']:.1f}x", x + 28, sy + 100, size=12.0, color="#047857", bold=True)
    _text(ctx, "(Tam Saint-Venant subsonik + paralel PRV)", x + 28, sy + 124, size=10.5, color="#475569")

    # Right: Exp125 Quench
    rx = x + 28 + cw
    _rrect(ctx, rx, sy, cw, ch, 8)
    ctx.set_source_rgba(*_hex("#EFF6FF"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#93C5FD"))
    ctx.set_line_width(1.2)
    ctx.stroke()
    _text(ctx, "Exp125 8-Bobin Mıknatıs Quench", rx + 12, sy + 24, size=12.0, color="#1E3A8A", bold=True)
    _text(ctx, f"1,50 T: {qch['E_mag_1p5T_kJ']:.2f} kJ  |  M4: {qch['E_mag_M4_0p1785T_kJ']:.3f} kJ", rx + 12, sy + 50, size=11.5, color="#0F172A")
    _text(ctx, f"R_dump = {qch['R_dump_ohm']:.3f} Ω  |  T_hot = {qch['T_hotspot_K']:.1f} K", rx + 12, sy + 74, size=11.5, color="#334155")
    _text(ctx, f"Direnç Tepe Sıcaklığı: {qch['dump_resistor_peak_1p5T_C']:.2f} °C (< 55 °C)", rx + 12, sy + 100, size=12.0, color="#1D4ED8", bold=True)
    _text(ctx, f"5 Gauss (0,5 mT) Sınırı: r < {qch['pacemaker_5gauss_radius_m']:.2f} m", rx + 12, sy + 124, size=10.5, color="#475569")


def _draw_panel5_epo_ups(ctx: cairo.Context, x: float, y: float, w: float, h: float, epo: dict[str, Any]) -> None:
    _panel_card(ctx, x, y, w, h, "5. 15 kVA Online UPS & Güvenli Kapanma Sırası", "0 ms · 80 ms UHV · PASS", "#059669")

    ups = epo["ups_spec"]
    uhv = epo["uhv_isolation"]

    steps = [
        ("0,0 ms", "S7.SAFETY", "15 kVA LFP Online UPS kesintisiz barayı devralır (0 ms)", "#059669", 0.04),
        ("3,2 ms", "S5.5", "SIL-3 PLC 808 nm lazer sürücüsünü keser, perde kapanır", "#DC2626", 0.14),
        ("18,3 ms", "S1/S2", "22 kV HV kesilir; 2 MΩ crowbar gerilimi < 50 V'a indirir", "#EA580C", 0.28),
        ("45,0 ms", "S5.6/S1", "MBE deklanşörü + 400 W PBN + SDS PH₃ SIL-3 vana kapanır", "#D97706", 0.42),
        ("80,0 ms", "S5 UHV", "Yay-dönüşlü all-metal UHV sürgülü vanalar mühürlenir", "#2563EB", 0.56),
        ("60 s", "S6/HPC", "Exp125 mıknatıs kontrollü inişi + Option-HPC güvenli duruş", "#7C3AED", 0.78),
        ("300 s", "S6.8", "LD400 ³He/⁴He karışımı oda sıcaklığı tankına geri alınır", "#0D9488", 0.96),
    ]

    # Timeline axis header
    tx0, tw = x + 178, w - 202
    ty0 = y + 64
    _text(ctx, "Kapanma Aşaması (Log-Zaman İlerlemesi)", tx0, ty0 - 4, size=11.5, color="#475569", bold=True)

    row_h = 46
    for i, (tstr, sub, desc, col, frac) in enumerate(steps):
        ry = ty0 + 10 + i * row_h
        # Left time + subsystem pill
        _rrect(ctx, x + 16, ry + 4, 68, 24, 5)
        ctx.set_source_rgba(*_hex(col, 0.14))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(col, 0.65))
        ctx.set_line_width(1.0)
        ctx.stroke()
        _text(ctx, tstr, x + 50, ry + 20, size=11.0, color=col, bold=True, align="center", family="DejaVu Sans Mono")

        _text(ctx, sub, x + 92, ry + 20, size=11.0, color="#334155", bold=True)

        # Progress track + dot
        bar_y = ry + 11
        _rrect(ctx, tx0, bar_y, tw, 9, 4)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.fill()
        _rrect(ctx, tx0, bar_y, max(12.0, tw * frac), 9, 4)
        ctx.set_source_rgba(*_hex(col, 0.85))
        ctx.fill()

        # Action text underneath track
        _text(ctx, desc, tx0, ry + 36, size=11.0, color="#1E293B")

    # Bottom UPS runtime & wafer oxidation box
    sy = y + 416
    _rrect(ctx, x + 16, sy, w - 32, h - (sy - y) - 14, 8)
    ctx.set_source_rgba(*_hex("#F8FAFC"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.set_line_width(1.0)
    ctx.stroke()

    _text(ctx, f"15 kVA / 10 kWh LFP UPS Özerklik Süreleri (Verim %90):", x + 28, sy + 24, size=12.0, color="#0F172A", bold=True)
    # Bar 1: Full rated 13.5 kW -> 40 min
    bx, bw_max = x + 230, w - 280
    _text(ctx, "Tam Yük (13,5 kW):", x + 28, sy + 52, size=11.5, color="#334155")
    _rrect(ctx, bx, sy + 39, bw_max, 18, 4)
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.fill()
    _rrect(ctx, bx, sy + 39, bw_max * (ups["runtime_at_rated_13p5kW_min"] / 240.0), 18, 4)
    ctx.set_source_rgba(*_hex("#2563EB"))
    ctx.fill()
    _text(ctx, f"{ups['runtime_at_rated_13p5kW_min']:.1f} dk (>= 30 dk)", bx + bw_max * (40.0 / 240.0) + 10, sy + 52, size=11.5, color="#1D4ED8", bold=True)

    # Bar 2: Tier-1 2.53 kW -> 213.2 min
    _text(ctx, "Tier-1 Güvenlik (2,53 kW):", x + 28, sy + 82, size=11.5, color="#334155")
    _rrect(ctx, bx, sy + 69, bw_max, 18, 4)
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.fill()
    _rrect(ctx, bx, sy + 69, bw_max * min(1.0, ups["runtime_tier1_min"] / 240.0), 18, 4)
    ctx.set_source_rgba(*_hex("#059669"))
    ctx.fill()
    _text(ctx, f"{ups['runtime_tier1_min']:.1f} dk (>= 180 dk)", bx + 10, sy + 82, size=11.5, color="#FFFFFF", bold=True)

    # Wafer oxidation footer inside box
    _text(ctx, f"UHV Yonga Koruması: 80 ms Vana Kapanışı @ 5e-8 Torr  ->  Si(100) Oksitlenme = {uhv['wafer_oxidation_ML']:.1e} ML (<< 0,01 ML)", x + 28, sy + 116, size=11.5, color="#047857", bold=True)


def _draw_panel6_fmea(
    ctx: cairo.Context, x: float, y: float, w: float, h: float, fmea: list[dict[str, Any]], fstat: dict[str, Any], spec: dict[str, Any]
) -> None:
    _panel_card(ctx, x, y, w, h, "6. 25-Satırlı FMEA (RPN Önce/Sonra) & S7.SAFETY", f"Max {fstat['max_rpn_pre']}->{fstat['max_rpn_post']} · PASS", "#059669")

    px, py, pw, ph = x + 56, y + 72, w - 76, 294
    y_max = 310.0

    def _sy(v: float) -> float:
        return py + ph * (1.0 - v / y_max)

    for tick in (0, 60, 120, 180, 240, 300):
        gy = _sy(tick)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.set_line_width(1.0)
        ctx.stroke()
        _text(ctx, str(tick), px - 6, gy + 4, size=10.5, color="#475569", align="right", family="DejaVu Sans Mono")

    ctx.set_source_rgba(*_hex("#334155"))
    ctx.set_line_width(1.4)
    ctx.move_to(px, py)
    ctx.line_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()

    ctx.save()
    ctx.translate(x + 18, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "Risk Öncelik Puanı (RPN)", 0, 0, size=11.5, color="#334155", bold=True, align="center")
    ctx.restore()

    n = len(fmea)
    slot = pw / n
    bw = slot * 0.72
    for i, r in enumerate(fmea):
        bx = px + i * slot + (slot - bw) / 2.0
        # Pre bar (light red/coral)
        y_pre = _sy(r["RPN_pre"])
        ctx.rectangle(bx, y_pre, bw, (py + ph) - y_pre)
        ctx.set_source_rgba(*_hex("#F87171", 0.78))
        ctx.fill()
        # Post bar (crisp dark teal overlaid)
        y_post = _sy(r["RPN_post"])
        ctx.rectangle(bx + 1.5, y_post, bw - 3.0, (py + ph) - y_post)
        ctx.set_source_rgba(*_hex("#0F766E", 0.96))
        ctx.fill()
        # X-axis labels (1..25)
        lbl = f"{i+1:02d}"
        if i % 2 == 0 or i == 24:
            _text(ctx, lbl, bx + bw / 2.0, py + ph + 15, size=9.8, color="#334155", align="center", family="DejaVu Sans Mono")

    _text(ctx, "FMEA Hata Modu İndeksi (FM-01 .. FM-25: S1–S9 + Tesis)", px + pw / 2.0, py + ph + 31, size=11.0, color="#475569", align="center")

    # RPN <= 60 acceptance threshold line + crisp opaque pill
    y60 = _sy(60.0)
    ctx.save()
    ctx.set_dash([6, 4])
    ctx.set_source_rgba(*_hex("#B45309"))
    ctx.set_line_width(1.9)
    ctx.move_to(px, y60)
    ctx.line_to(px + pw, y60)
    ctx.stroke()
    ctx.restore()
    _rrect(ctx, px + pw - 196, y60 - 26, 192, 21, 5)
    ctx.set_source_rgba(*_hex("#FEF3C7", 0.96))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#D97706"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, "Hedef RPN <= 60 (0/25 İhlal)", px + pw - 100, y60 - 11, size=10.8, color="#92400E", bold=True, align="center")

    # Top legend strip
    _rrect(ctx, px + 6, py - 24, 14, 12, 2)
    ctx.set_source_rgba(*_hex("#F87171", 0.85))
    ctx.fill()
    _text(ctx, f"Önce (Ort. {fstat['mean_rpn_pre']}, Maks. {fstat['max_rpn_pre']})", px + 26, py - 14, size=11.0, color="#B91C1C", bold=True)
    _rrect(ctx, px + 268, py - 24, 14, 12, 2)
    ctx.set_source_rgba(*_hex("#0F766E"))
    ctx.fill()
    _text(ctx, f"Sonra (Ort. {fstat['mean_rpn_post']}, Maks. {fstat['max_rpn_post']}, -%{fstat['mean_rpn_reduction_pct']})", px + 288, py - 14, size=11.0, color="#0F766E", bold=True)

    # Bottom S7.SAFETY BOM v7.0 summary box
    sy = y + 416
    _rrect(ctx, x + 16, sy, w - 32, h - (sy - y) - 14, 8)
    ctx.set_source_rgba(*_hex("#F8FAFC"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#CBD5E1"))
    ctx.set_line_width(1.1)
    ctx.stroke()
    tot = spec["totals"]
    sc = fstat["sil_counts"]
    _text(ctx, f"S7.SAFETY-01..06 Laboratuvar Güvenlik Kiti (BOM v7.0 Paketi):", x + 28, sy + 24, size=12.0, color="#0F172A", bold=True)
    _text(ctx, f"Kütle: {tot['total_mass_kg']:.1f} kg  |  Güç: {tot['steady_electrical_power_W']:.0f} W  |  Kriyo Yükü: {tot['cryo_load_W']:.1f} W", x + 28, sy + 48, size=11.8, color="#334155")
    _text(ctx, f"Bütçe: ${tot['cost_usd_low']:,} – ${tot['cost_usd_nom']:,} – ${tot['cost_usd_high']:,} (M3 v6.0 BOM'un %{tot['pct_of_m3_v6_full_bom']:.2f}'i)", x + 28, sy + 72, size=11.8, color="#047857", bold=True)
    _text(ctx, f"SIL Dağılımı (25 FMEA + 10 HAZOP): {sc['SIL-3']}x SIL-3  |  {sc['SIL-2']}x SIL-2  |  {sc['SIL-1']}x SIL-1", x + 28, sy + 96, size=11.5, color="#1D4ED8", bold=True)
    _text(ctx, "01: SDS PH₃ ($42k) · 02: OD8 Perde ($22k) · 03: SIL-3 PLC ($28k) · 04: 15kVA UPS ($24k) · 05: O₂/DN50 ($14k) · 06: UHV ($15k)", x + 28, sy + 122, size=10.3, color="#475569")


def main() -> None:
    data = json.loads((RES_DIR / "exp150.json").read_text(encoding="utf-8"))
    spec = json.loads((RES_DIR / "s_safety_spec.json").read_text(encoding="utf-8"))

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)

    # Background
    ctx.set_source_rgba(*_hex("#F1F5F9"))
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Top dark header
    ctx.set_source_rgba(*_hex("#0F172A"))
    ctx.rectangle(0, 0, W, 86)
    ctx.fill()
    _text(
        ctx,
        "ATOM LİTOGRAFİ MAKİNESİ — EXP150 (H168): ENDÜSTRİYEL EMNİYET, HAZOP, 25-SATIRLI FMEA & SIL-3 KİTİ",
        28, 36, size=22.0, color="#FFFFFF", bold=True,
    )
    _text(
        ctx,
        "SEMI S2 · IEC 61508 (SIL-2/3) · ANSI Z136.1 · OSHA/NIOSH · ISO 10156 · ICRP 103 / NIST XCOM · ASME BPVC Sec VIII  |  {Model}/{Analitik} (no_lab_measurement=true)",
        28, 64, size=13.0, color="#CBD5E1",
    )

    # Header right pills
    _rrect(ctx, W - 436, 20, 200, 44, 8)
    ctx.set_source_rgba(*_hex("#059669"))
    ctx.fill()
    _text(ctx, f"{data['criteria_passed']} SF1–SF7 PASS", W - 336, 48, size=16.0, color="#FFFFFF", bold=True, align="center")

    _rrect(ctx, W - 224, 20, 196, 44, 8)
    ctx.set_source_rgba(*_hex("#1E293B"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#38BDF8"))
    ctx.set_line_width(1.6)
    ctx.stroke()
    fstat = data["fmea_summary"]
    _text(ctx, f"RPN: {fstat['max_rpn_pre']} -> {fstat['max_rpn_post']}", W - 126, 48, size=16.0, color="#38BDF8", bold=True, align="center")

    # Top KPI strip (6 cards)
    las = data["hazard_1_laser_s55"]
    gas = data["hazard_2_ph3_and_forming_gas"]
    hvx = data["hazard_3_hv_and_xray"]
    cryo = data["hazard_4_cryo_odh_and_quench"]
    epo = data["hazard_5_epo_ups_shutdown"]
    tot = spec["totals"]
    kpis = [
        ("S5.5 SINIF-4 LAZER", f"OD8 · {las['interlock_sil3']['shutter_close_ms']} ms", f"NOHD {las['nohd_collimated_20mrad_m']:.0f} m | PFD 2,3e-5", "#059669"),
        ("S1.1 PH₃ FOSFİN (SDS)", f"{gas['mitigated_sds_system']['operator_conservative_ppm']:.4f} ppm", f"{gas['mitigated_sds_system']['margin_below_tlv_twa']:.0f}x < TLV | 6990x < IDLH", "#0284C7"),
        ("22 keV X-IŞINI & HV", "1,2e-23 µSv/h", f"Crowbar {hvx['hv_crowbar']['discharge_to_50V_22kV_ms']:.1f} ms | {hvx['hv_crowbar']['stored_energy_22kV_J']:.2f} J", "#7C3AED"),
        ("KRİYO He ODH & QUENCH", f"O₂ %{cryo['helium_odh']['room_sweep']['60m3']['dry_ld400_pt420_O2_pct']:.2f}", f"DN50 {cryo['asme_ovc_relief']['relief_safety_margin']:.1f}x | Dump {cryo['magnet_quench_exp125']['dump_resistor_peak_1p5T_C']:.2f} °C", "#0D9488"),
        ("15 kVA UPS & UHV", "0 ms · 80 ms", f"40 / 213 dk | {epo['uhv_isolation']['wafer_oxidation_ML']:.0e} ML", "#2563EB"),
        ("S7.SAFETY KİTİ (v7.0)", f"${tot['cost_usd_nom']//1000}k (%{tot['pct_of_m3_v6_full_bom']:.2f})", f"{tot['total_mass_kg']:.0f} kg | {tot['steady_electrical_power_W']:.0f} W | 0 W Kriyo", "#D97706"),
    ]
    kw = (W - 56 - 5 * 14) / 6.0
    for i, (kt, kv, ks, kc) in enumerate(kpis):
        kx = 28 + i * (kw + 14)
        _rrect(ctx, kx, 98, kw, 80, 10)
        ctx.set_source_rgba(*_hex("#FFFFFF"))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex("#CBD5E1"))
        ctx.set_line_width(1.2)
        ctx.stroke()
        ctx.rectangle(kx, 98, 6, 80)
        ctx.set_source_rgba(*_hex(kc))
        ctx.fill()
        _text(ctx, kt, kx + 18, 118, size=10.8, color="#64748B", bold=True)
        _text(ctx, kv, kx + 18, 146, size=20.5, color="#0F172A", bold=True)
        _text(ctx, ks, kx + 18, 168, size=11.0, color=kc, bold=True)

    # 2x3 Grid of 6 panels
    pw = (W - 56 - 32) / 3.0
    r1y, r1h = 192, 574
    r2y, r2h = 780, 574
    xs = [28, 28 + pw + 16, 28 + 2 * (pw + 16)]

    _draw_panel1_laser(ctx, xs[0], r1y, pw, r1h, las)
    _draw_panel2_ph3(ctx, xs[1], r1y, pw, r1h, gas)
    _draw_panel3_hv_xray(ctx, xs[2], r1y, pw, r1h, hvx)

    _draw_panel4_cryo(ctx, xs[0], r2y, pw, r2h, cryo)
    _draw_panel5_epo_ups(ctx, xs[1], r2y, pw, r2h, epo)
    _draw_panel6_fmea(ctx, xs[2], r2y, pw, r2h, data["fmea_25_rows"], fstat, spec)

    # Footer
    _text(
        ctx,
        "Kaynak: results/exp150_industrial_safety_fmea_hazop/exp150.json & s_safety_spec.json  |  Çapalar: CAD v6.0, Exp125, Exp128, Exp130, Exp139",
        28, H - 14, size=11.5, color="#475569",
    )
    _text(
        ctx,
        "Epistemik: {Model}/{Analitik}/{Varsayım} · no_lab_measurement=true · no_supplier_quotes=true · Kapanış onayı Carbon denetimine tabidir",
        W - 28, H - 14, size=11.5, color="#64748B", align="right",
    )

    surf.write_to_png(str(OUT_PNG))
    print(f"Wrote {OUT_PNG} ({W}x{H})")


if __name__ == "__main__":
    main()
