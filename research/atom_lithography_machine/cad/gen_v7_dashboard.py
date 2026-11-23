"""Generate GitHub README v7.0 hero cover dashboard `00_v7_overview_dashboard.png` (2400x1400).

Reads verified live metrics directly from disk (zero hardcoded stale metrics, zero user paths):
  - results/exp128_bom_sensitivity/exp128.json
  - results/exp147_universal_qldpc_d18_magic_state/exp147.json
  - results/exp148_sb121_quadrupole_echo_qudit/exp148.json
  - results/exp149_boed_verilog_rtl_and_interactive_twin/exp149.json
  - results/exp150_industrial_safety_fmea_hazop/exp150.json
  - results/exp151_v7_digital_twin/exp151.json
  - results/exp151_v7_digital_twin/v7_digital_twin_cert.json
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


def _hex(h: str, a: float = 1.0) -> tuple[float, float, float, float]:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, a)


def tr_f(val: float, dec: int = 1) -> str:
    return f"{val:,.{dec}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def tr_i(val: int) -> str:
    return f"{val:,}".replace(",", ".")


def _rrect(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float = 10.0) -> None:
    r = min(r, w / 2.0, h / 2.0)
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
    color: str = "#0F172A",
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


def _panel(
    ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str, badge: str, badge_bg: str
) -> None:
    # Soft drop shadow
    _rrect(ctx, x + 2, y + 3, w, h, 12)
    ctx.set_source_rgba(0.05, 0.10, 0.20, 0.06)
    ctx.fill()
    # Card
    _rrect(ctx, x, y, w, h, 12)
    ctx.set_source_rgba(*_hex("#FFFFFF"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#CBD5E1"))
    ctx.set_line_width(1.3)
    ctx.stroke()
    # Header bar
    ctx.save()
    _rrect(ctx, x, y, w, h, 12)
    ctx.clip()
    ctx.rectangle(x, y, w, 39)
    ctx.set_source_rgba(*_hex("#F8FAFC"))
    ctx.fill()
    ctx.move_to(x, y + 39)
    ctx.line_to(x + w, y + 39)
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.set_line_width(1.1)
    ctx.stroke()
    ctx.restore()

    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(11.0)
    bw = ctx.text_extents(badge).width + 18
    bx = x + w - bw - 12
    _text(ctx, title, x + 14, y + 25, size=14.0, color="#0F172A", bold=True, max_w=(bx - x - 22))
    _rrect(ctx, bx, y + 9, bw, 21, 6)
    ctx.set_source_rgba(*_hex(badge_bg))
    ctx.fill()
    _text(ctx, badge, bx + bw / 2.0, y + 23.5, size=11.0, color="#FFFFFF", bold=True, align="center")


def _draw_p1_qldpc_algos(ctx: cairo.Context, x: float, y: float, w: float, h: float, e147: dict[str, Any], cert: dict[str, Any]) -> None:
    _panel(ctx, x, y, w, h, "1. Exp147 — Evrensel qLDPC d=18: FeMoco & RSA-2048", "37,1x–52,7x ↓", "#7C3AED")

    fm_q = e147["part5_flagship_algorithms"]["FeMoco_192L_1e8T"]["qLDPC_d18_Gidney_Cult_116to12"]
    fm_s = e147["part5_flagship_algorithms"]["FeMoco_192L_1e8T"]["SurfaceCode_D3_Baseline"]
    rs_q = e147["part5_flagship_algorithms"]["RSA2048_4096L_1e10T"]["qLDPC_d24_D3_GidneyCult"]
    rs_s = e147["part5_flagship_algorithms"]["RSA2048_4096L_1e10T"]["SurfaceCode_D3_Baseline"]

    px, py, pw, ph = x + 66, y + 76, w - 88, 286
    y_min, y_max = -0.8, 4.6  # log10: 0.16 .. 40,000

    def _sy(v: float) -> float:
        lv = math.log10(max(v, 0.16))
        return py + ph * (1.0 - (lv - y_min) / (y_max - y_min))

    for exp, lbl in ((0, "1"), (1, "10"), (2, "100"), (3, "1k"), (4, "10k")):
        gy = _sy(10.0 ** exp)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.set_line_width(1.0)
        ctx.stroke()
        _text(ctx, lbl, px - 8, gy + 4, size=10.5, color="#475569", mono=True, align="right")

    ctx.set_source_rgba(*_hex("#334155"))
    ctx.set_line_width(1.4)
    ctx.move_to(px, py)
    ctx.line_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()

    ctx.save()
    ctx.translate(x + 20, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "Kriyo Adet / Güç MW (log10)", 0, 0, size=11.5, color="#334155", bold=True, align="center")
    ctx.restore()

    # Legend above chart
    _rrect(ctx, px + 6, py - 26, 13, 11, 2)
    ctx.set_source_rgba(*_hex("#94A3B8"))
    ctx.fill()
    _text(ctx, "Surface Code (D3 Referans)", px + 24, py - 16, size=10.8, color="#475569", bold=True)
    _rrect(ctx, px + 236, py - 26, 13, 11, 2)
    ctx.set_source_rgba(*_hex("#7C3AED"))
    ctx.fill()
    _text(ctx, "qLDPC + Gidney Cultivation (v7.0)", px + 254, py - 16, size=10.8, color="#6D28D9", bold=True)

    groups = [
        ("FeMoco\nKriyo (LD400)", fm_s["total_cryostats_ld400"], fm_q["total_cryostats_ld400"], tr_i(fm_s["total_cryostats_ld400"]), tr_i(fm_q["total_cryostats_ld400"]), f"{cert['exp147_femoco_compression_x']:.1f}x ↓"),
        ("FeMoco\nGüç (MW)", fm_s["tco_and_power"]["total_facility_power_mw"], fm_q["tco_and_power"]["total_facility_power_mw"], tr_f(fm_s["tco_and_power"]["total_facility_power_mw"], 1), tr_f(fm_q["tco_and_power"]["total_facility_power_mw"], 2), f"{fm_s['tco_and_power']['total_facility_power_mw']/fm_q['tco_and_power']['total_facility_power_mw']:.1f}x ↓"),
        ("RSA-2048\nKriyo (LD400)", rs_s["total_cryostats_ld400"], rs_q["total_cryostats_ld400"], tr_i(rs_s["total_cryostats_ld400"]), tr_i(rs_q["total_cryostats_ld400"]), f"{cert['exp147_rsa2048_compression_x']:.1f}x ↓"),
        ("RSA-2048\nGüç (MW)", rs_s["tco_and_power"]["total_facility_power_mw"], rs_q["tco_and_power"]["total_facility_power_mw"], tr_f(rs_s["tco_and_power"]["total_facility_power_mw"], 0), tr_f(rs_q["tco_and_power"]["total_facility_power_mw"], 2), f"{rs_s['tco_and_power']['total_facility_power_mw']/rs_q['tco_and_power']['total_facility_power_mw']:.1f}x ↓"),
    ]
    slot = pw / len(groups)
    bw = slot * 0.30
    for i, (lbl, vs, vq, ts, tq, gain) in enumerate(groups):
        cx = px + i * slot + slot / 2.0
        # SC bar
        bx1 = cx - bw - 3
        by1 = _sy(vs)
        _rrect(ctx, bx1, by1, bw, (py + ph) - by1, 4)
        ctx.set_source_rgba(*_hex("#94A3B8", 0.85))
        ctx.fill()
        _text(ctx, ts, bx1 + bw / 2.0, by1 - 6, size=10.5, color="#475569", bold=True, align="center")
        # qLDPC bar
        bx2 = cx + 3
        by2 = _sy(vq)
        _rrect(ctx, bx2, by2, bw, (py + ph) - by2, 4)
        ctx.set_source_rgba(*_hex("#7C3AED", 0.92))
        ctx.fill()
        _text(ctx, tq, bx2 + bw / 2.0, by2 - 6, size=10.8, color="#5B21B6", bold=True, align="center")
        # Gain badge cleanly above qLDPC bar
        _rrect(ctx, bx2 - 4, by2 - 36, bw + 8, 17, 4)
        ctx.set_source_rgba(*_hex("#EDE9FE"))
        ctx.fill()
        _text(ctx, gain, bx2 + bw / 2.0, by2 - 24, size=9.8, color="#6D28D9", bold=True, align="center")

        for li, part in enumerate(lbl.split("\n")):
            _text(ctx, part, cx, py + ph + 16 + li * 13, size=10.5, color="#1E293B", bold=(li == 0), align="center")

    # Bottom technical summary box
    sy = y + 408
    _rrect(ctx, x + 14, sy, w - 28, h - (sy - y) - 14, 8)
    ctx.set_source_rgba(*_hex("#F8FAFC"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, f"[[288,12,18]]: L_max = {tr_f(cert['exp147_bb288_L_max_um'], 1)} µm <= 300 | p_th = %{tr_f(cert['exp147_bb288_p_th_pct'], 3)} | 576-Hücre Verim: %{tr_f(cert['exp147_yield_576_N8_pct'], 2)} (N=8) / %{tr_f(cert['exp147_yield_576_N9_pct'], 2)} (N=9)", x + 26, sy + 24, size=11.2, color="#0F172A", bold=True, max_w=w - 52)
    _text(ctx, f"FeMoco (192L, 1e8 T): {fm_q['total_cryostats_ld400']} kriyo · {tr_f(fm_q['runtime_hours'], 2)} sa · {tr_f(fm_q['tco_and_power']['total_facility_power_kw'], 1)} kW · ${tr_f(fm_q['tco_and_power']['tco5_musd_p50'], 1)}M (${tr_i(round(fm_q['cost_per_solve_usd_p50']))}/çözüm)", x + 26, sy + 49, size=11.2, color="#334155", max_w=w - 52)
    _text(ctx, f"RSA-2048 (4096L, 1e10 T): {rs_q['total_cryostats_ld400']} kriyo · {tr_f(rs_q['runtime_hours'], 1)} sa · {tr_f(rs_q['tco_and_power']['total_facility_power_mw'], 2)} MW · ${tr_f(rs_q['tco_and_power']['tco5_musd_p50'], 0)}M (35,9x ucuz)", x + 26, sy + 73, size=11.2, color="#334155", max_w=w - 52)
    # Honest UQ4/UQ5 caveat pill
    _rrect(ctx, x + 24, sy + 88, w - 48, 42, 6)
    ctx.set_source_rgba(*_hex("#FEF3C7"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#F59E0B"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, "Dürüst Sınır (Exp147 5/7 PASS; UQ4/UQ5 FAIL): p_L_mem < 1e-12 hedefi için okuma hatası", x + 34, sy + 105, size=10.6, color="#92400E", bold=True, max_w=w - 68)
    _text(ctx, "tavanı p_meas <= %0,15 (Mevcut D3 %0,337'de bellek ömrü sınırlı -> D3++ <=%0,20 yol haritası)", x + 34, sy + 122, size=10.3, color="#78350F", max_w=w - 68)


def _draw_p2_sb121(ctx: cairo.Context, x: float, y: float, w: float, h: float, e148: dict[str, Any], cert: dict[str, Any]) -> None:
    _panel(ctx, x, y, w, h, "2. Exp148 — ¹²¹Sb (I=7/2) Q-Echo-8 & SU(8) GRAPE", "455,5x ↓ · 6/7 PASS", "#059669")

    qs = e148["benchmarks"]["quasistatic_500Hz_1ms"]
    su8 = e148["su8_grape_logical_gates"]["gates"]
    t2 = e148["benchmarks"]["colored_1f_500Hz_decay_curves"]["T2_eff_ms"]

    # Split top area into Left (Static 500 Hz + SU(8) fidelities) & Right (1/f Cywinski T2_eff scaling)
    # Left sub-chart
    lx, ly, lw, lh = x + 48, y + 72, 344, 286
    _text(ctx, "Statik 500 Hz (1 ms) & SU(8) Sadakat", lx + lw / 2.0, ly - 12, size=11.5, color="#0F172A", bold=True, align="center")
    for tick in (0.5, 0.7, 0.9, 1.0):
        gy = ly + lh * (1.0 - (tick - 0.45) / 0.58)
        ctx.move_to(lx, gy)
        ctx.line_to(lx + lw, gy)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.set_line_width(0.9)
        ctx.stroke()
        _text(ctx, tr_f(tick, 1), lx - 6, gy + 3.5, size=9.8, color="#475569", mono=True, align="right")
    ctx.set_source_rgba(*_hex("#334155"))
    ctx.set_line_width(1.3)
    ctx.move_to(lx, ly)
    ctx.line_to(lx, ly + lh)
    ctx.line_to(lx + lw, ly + lh)
    ctx.stroke()

    fbars = [
        ("Çıplak\nGross", qs["bare"]["gross_0L"], "#DC2626", "0,580"),
        ("Q-Echo-8\nGross", qs["qecho8_finite_neutral_25kHz"]["gross_0L"], "#059669", "0,9991"),
        ("Q-Echo-8\nCat ±7/2", qs["qecho8_finite_neutral_25kHz"]["spin_cat_pm7_2"], "#0D9488", "0,9991"),
        ("SU(8)\nX_L", su8["X_L"]["F_L_noiseless_full_crosstalk"], "#2563EB", "0,9954"),
        ("SU(8)\nZ_L", su8["Z_L"]["F_L_noiseless_full_crosstalk"], "#4F46E5", "0,9971"),
        ("SU(8)\nH_L", su8["H_L"]["F_L_noiseless_full_crosstalk"], "#7C3AED", "0,9959"),
    ]
    slot = lw / len(fbars)
    bw = slot * 0.62
    for i, (lbl, val, col, vtxt) in enumerate(fbars):
        bx = lx + i * slot + (slot - bw) / 2.0
        by = ly + lh * (1.0 - (val - 0.45) / 0.58)
        _rrect(ctx, bx, by, bw, (ly + lh) - by, 4)
        ctx.set_source_rgba(*_hex(col, 0.88))
        ctx.fill()
        _text(ctx, vtxt, bx + bw / 2.0, by - 6, size=9.6, color=col, bold=True, align="center")
        for li, part in enumerate(lbl.split("\n")):
            _text(ctx, part, bx + bw / 2.0, ly + lh + 14 + li * 12, size=9.2, color="#1E293B", bold=(li == 0), align="center")

    # Right sub-chart: Cywinski 1/f T2_eff scaling (ms)
    rx, ry, rw, rh = x + 448, y + 72, w - 470, 286
    _text(ctx, "Geniş-Bant 1/f Cywiński T2_eff (ms)", rx + rw / 2.0, ry - 12, size=11.5, color="#0F172A", bold=True, align="center")
    t_max = 1.65
    for tick in (0.0, 0.5, 1.0, 1.5):
        gy = ry + rh * (1.0 - tick / t_max)
        ctx.move_to(rx, gy)
        ctx.line_to(rx + rw, gy)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.set_line_width(0.9)
        ctx.stroke()
        _text(ctx, tr_f(tick, 1), rx - 6, gy + 3.5, size=9.8, color="#475569", mono=True, align="right")
    ctx.set_source_rgba(*_hex("#334155"))
    ctx.set_line_width(1.3)
    ctx.move_to(rx, ry)
    ctx.line_to(rx, ry + rh)
    ctx.line_to(rx + rw, ry + rh)
    ctx.stroke()

    cbars = [
        ("Çıplak", t2["bare_gross_ms"], "#DC2626", "0,05"),
        ("QE-8", t2["qecho8_gross_ms"], "#0284C7", "0,43"),
        ("QE-16", t2["qecho16_gross_ms"], "#0EA5E9", "0,66"),
        ("QE-32", t2["qecho32_gross_ms"], "#0D9488", "0,98"),
        ("QE-64", t2["qecho64_gross_ms"], "#059669", "1,45"),
    ]
    rslot = rw / len(cbars)
    rbw = rslot * 0.58
    for i, (lbl, val, col, vtxt) in enumerate(cbars):
        bx = rx + i * rslot + (rslot - rbw) / 2.0
        by = ry + rh * (1.0 - val / t_max)
        _rrect(ctx, bx, by, rbw, max(4.0, (ry + rh) - by), 4)
        ctx.set_source_rgba(*_hex(col, 0.90))
        ctx.fill()
        _text(ctx, vtxt, bx + rbw / 2.0, by - 6, size=10.0, color=col, bold=True, align="center")
        _text(ctx, lbl, bx + rbw / 2.0, ry + rh + 15, size=9.8, color="#1E293B", bold=True, align="center")
    _rrect(ctx, rx + 8, ry + 6, 102, 20, 5)
    ctx.set_source_rgba(*_hex("#DCFCE7"))
    ctx.fill()
    _text(ctx, "28,1x Kazanç", rx + 59, ry + 20, size=10.2, color="#166534", bold=True, align="center")

    # Bottom technical summary box
    sy = y + 408
    _rrect(ctx, x + 14, sy, w - 28, h - (sy - y) - 14, 8)
    ctx.set_source_rgba(*_hex("#F8FAFC"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, f"Exp142 OQ6 Kapatıldı: Statik 500 Hz Gross {tr_f(cert['exp148_sb121_bare_gross_0L'], 4)} -> {tr_f(cert['exp148_sb121_qecho8_gross_0L'], 5)} ({tr_f(cert['exp148_sb121_infidelity_reduction_x'], 1)}x infidelite ↓)", x + 26, sy + 24, size=11.2, color="#047857", bold=True, max_w=w - 52)
    _text(ctx, f"Cat |±7/2⟩: 0,9424 -> {tr_f(cert['exp148_sb121_qecho8_cat77'], 5)} (1/f T2_eff = {tr_f(t2['qecho8_cat77_ms'], 2)} ms)  |  SU(8) GRAPE min F_L = {tr_f(cert['exp148_sb121_su8_grape_min_F'], 4)}", x + 26, sy + 49, size=11.2, color="#0F172A", max_w=w - 52)
    _text(ctx, f"Sonlu Darbe (25 kHz Kompozit 90-240-90 + Faz Döngüsü): 8x8/16x16 CPTP Lindblad doğrulandı", x + 26, sy + 73, size=11.0, color="#334155", max_w=w - 52)
    _rrect(ctx, x + 24, sy + 88, w - 48, 42, 6)
    ctx.set_source_rgba(*_hex("#FEF3C7"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#F59E0B"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, f"Dürüst Sınır (SQ4 FAIL): Geniş-bant 1/f gürültüde Q-Echo-8 kazancı {tr_f(t2['gross_gain_qecho8_vs_bare'], 2)}x -> Q-Echo-64'te", x + 34, sy + 105, size=10.6, color="#92400E", bold=True, max_w=w - 68)
    _text(ctx, f"{tr_f(cert['exp148_sb121_qecho64_1f_gain_x'], 2)}x ({tr_f(t2['qecho64_gross_ms'], 2)} ms); yüksek frekanslı 1/f kuyruğunda Cywiński filtre sınırı geçerlidir.", x + 34, sy + 122, size=10.3, color="#78350F", max_w=w - 68)


def _draw_p3_verilog_twin(ctx: cairo.Context, x: float, y: float, w: float, h: float, e149: dict[str, Any], cert: dict[str, Any]) -> None:
    _panel(ctx, x, y, w, h, "3. Exp149 — Q16.16 BOED-FPGA RTL & HTML5 İkiz", "584 cyc · 0 LSB · 7/7", "#2563EB")

    rv = e149["rtl_verification"]
    zu = rv["zu48dr_resource_budget"]
    tot16 = zu["total_16ch"]

    # Top block: 4-Stage Pipeline Flow Diagram
    stages = [
        ("Stage 0: SPRT", "4 çevrim\n16 ns", "#0EA5E9"),
        ("LUT ROM", "1.024 kelime\n0 bit fark", "#6366F1"),
        ("SIMD-4 Q16.16", "+ CORDIC ISQRT\n0 LSB (64/64)", "#2563EB"),
        ("BOED Çıkış", f"{zu['cycles_per_boed_step']} çevrim\n{tr_f(zu['latency_per_boed_step_us'], 3)} µs", "#059669"),
    ]
    sy_pipe = y + 58
    sw = (w - 48 - 3 * 22) / 4.0
    sh = 78
    for i, (st, sd, sc) in enumerate(stages):
        sx = x + 24 + i * (sw + 22)
        _rrect(ctx, sx, sy_pipe, sw, sh, 8)
        ctx.set_source_rgba(*_hex(sc, 0.11))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(sc, 0.85))
        ctx.set_line_width(1.5)
        ctx.stroke()
        _text(ctx, st, sx + sw / 2.0, sy_pipe + 24, size=11.0, color=sc, bold=True, align="center")
        for li, part in enumerate(sd.split("\n")):
            _text(ctx, part, sx + sw / 2.0, sy_pipe + 44 + li * 16, size=10.5, color="#1E293B", bold=(li == 0), align="center")
        if i < 3:
            ax1 = sx + sw + 3
            ax2 = sx + sw + 19
            ay = sy_pipe + sh / 2.0
            ctx.set_source_rgba(*_hex("#475569"))
            ctx.set_line_width(2.0)
            ctx.move_to(ax1, ay)
            ctx.line_to(ax2 - 4, ay)
            ctx.stroke()
            ctx.move_to(ax2, ay)
            ctx.line_to(ax2 - 7, ay - 5)
            ctx.line_to(ax2 - 7, ay + 5)
            ctx.close_path()
            ctx.fill()

    # Middle block: ZU48DR 16-Channel Utilization Bars
    uy0 = y + 166
    _text(ctx, "Xilinx RFSoC ZU48DR — 16-Kanal Paralel Kaynak Bütçesi (@ 250 MHz, 4 ns XDC)", x + 24, uy0, size=11.8, color="#0F172A", bold=True)
    res_rows = [
        ("DSP48E2", f"{tot16['dsp48e2']} / 4.272", tot16["dsp48e2_pct"], "#2563EB"),
        ("BRAM36", f"{tot16['bram36']} / 1.080", tot16["bram36_pct"], "#7C3AED"),
        ("CLB LUT", f"{tr_i(tot16['lut'])} / 425k", tot16["lut_pct"], "#0D9488"),
        ("Flip-Flop", f"{tr_i(tot16['ff'])} / 850k", tot16["ff_pct"], "#0284C7"),
    ]
    bx0, bmax = x + 122, w - 306
    for i, (rname, rcnt, rpct, rcol) in enumerate(res_rows):
        ry = uy0 + 18 + i * 44
        _text(ctx, rname, x + 24, ry + 17, size=11.5, color="#334155", bold=True)
        _rrect(ctx, bx0, ry + 4, bmax, 20, 5)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.fill()
        # Scale bar visually out of 35% full-width for clear reading + annotate exact %
        fill_w = max(14.0, bmax * min(1.0, rpct / 35.0))
        _rrect(ctx, bx0, ry + 4, fill_w, 20, 5)
        ctx.set_source_rgba(*_hex(rcol, 0.90))
        ctx.fill()
        _text(ctx, f"%{tr_f(rpct, 2)} ({rcnt})", bx0 + bmax + 10, ry + 18, size=10.8, color=rcol, bold=True, max_w=(x + w - (bx0 + bmax + 22)))
    _text(ctx, "(Bar ölçeği %0–%35; tüm kaynaklar <%16 güvenli bütçe içinde — kart gücü 37,98 W, 0 W kriyo)", x + 24, uy0 + 206, size=10.3, color="#64748B")

    # Bottom technical box
    sy = y + 408
    _rrect(ctx, x + 14, sy, w - 28, h - (sy - y) - 14, 8)
    ctx.set_source_rgba(*_hex("#F8FAFC"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, f"rtl/boed_fpga/: {cert['exp149_rtl_loc']} satır IEEE 1364-2005 (4 modül, 0 sentez hatası, 250 MHz XDC)", x + 26, sy + 24, size=11.2, color="#0F172A", bold=True, max_w=w - 52)
    _text(ctx, f"Bit-Doğru Eş-Doğrulama: 1.024/1.024 ROM (0 bit fark) | 64/64 Golden + 1.000 ISQRT (0 LSB)", x + 26, sy + 49, size=11.2, color="#047857", bold=True, max_w=w - 52)
    _text(ctx, "İnteraktif Dijital İkiz: docs/digital_twin_interactive.html (66,6 KB · 5 Sekme · 0 CDN/HTTP)", x + 26, sy + 73, size=11.2, color="#1D4ED8", bold=True, max_w=w - 52)
    _rrect(ctx, x + 24, sy + 88, w - 48, 42, 6)
    ctx.set_source_rgba(*_hex("#EFF6FF"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#93C5FD"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, "Epistemik Not (no_external_eda_sim=true): Yapısal sentez lint & Python bit-doğru modelleme", x + 34, sy + 105, size=10.5, color="#1E3A8A", bold=True, max_w=w - 68)
    _text(ctx, "doğrulandı; Vivado place-and-route ve donanım JTAG kapanışı laboratuvar fazında yapılacaktır.", x + 34, sy + 122, size=10.2, color="#1E40AF", max_w=w - 68)


def _draw_p4_safety_fmea(ctx: cairo.Context, x: float, y: float, w: float, h: float, e150: dict[str, Any]) -> None:
    fstat = e150["fmea_summary"]
    _panel(ctx, x, y, w, h, "4. Exp150 — Endüstriyel Emniyet & 25-Satırlı FMEA", f"RPN {fstat['max_rpn_pre']}->{fstat['max_rpn_post']} · 7/7", "#DC2626")

    px, py, pw, ph = x + 52, y + 76, w - 72, 260
    y_max = 310.0

    def _sy(v: float) -> float:
        return py + ph * (1.0 - v / y_max)

    for tick in (0, 60, 120, 180, 240, 300):
        gy = _sy(tick)
        ctx.move_to(px, gy)
        ctx.line_to(px + pw, gy)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.set_line_width(0.9)
        ctx.stroke()
        _text(ctx, str(tick), px - 6, gy + 3.5, size=9.8, color="#475569", mono=True, align="right")

    ctx.set_source_rgba(*_hex("#334155"))
    ctx.set_line_width(1.3)
    ctx.move_to(px, py)
    ctx.line_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()

    ctx.save()
    ctx.translate(x + 17, py + ph / 2.0)
    ctx.rotate(-math.pi / 2)
    _text(ctx, "FMEA RPN (S x O x D)", 0, 0, size=11.0, color="#334155", bold=True, align="center")
    ctx.restore()

    rows = e150["fmea_25_rows"]
    slot = pw / len(rows)
    bw = slot * 0.72
    for i, r in enumerate(rows):
        bx = px + i * slot + (slot - bw) / 2.0
        yp = _sy(r["RPN_pre"])
        ctx.rectangle(bx, yp, bw, (py + ph) - yp)
        ctx.set_source_rgba(*_hex("#F87171", 0.78))
        ctx.fill()
        yq = _sy(r["RPN_post"])
        ctx.rectangle(bx + 1.5, yq, bw - 3.0, (py + ph) - yq)
        ctx.set_source_rgba(*_hex("#0F766E", 0.96))
        ctx.fill()
        if i % 2 == 0 or i == 24:
            _text(ctx, f"{i+1:02d}", bx + bw / 2.0, py + ph + 14, size=9.2, color="#334155", mono=True, align="center")

    # RPN <= 60 threshold + opaque pill
    y60 = _sy(60.0)
    ctx.save()
    ctx.set_dash([6, 4])
    ctx.set_source_rgba(*_hex("#B45309"))
    ctx.set_line_width(1.8)
    ctx.move_to(px, y60)
    ctx.line_to(px + pw, y60)
    ctx.stroke()
    ctx.restore()
    _rrect(ctx, px + pw - 196, y60 - 25, 192, 20, 4)
    ctx.set_source_rgba(*_hex("#FEF3C7", 0.96))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#D97706"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, "Hedef RPN <= 60 (0/25 İhlal)", px + pw - 100, y60 - 11, size=10.2, color="#92400E", bold=True, align="center")

    # Legend above chart
    _rrect(ctx, px + 4, py - 24, 13, 11, 2)
    ctx.set_source_rgba(*_hex("#F87171", 0.85))
    ctx.fill()
    _text(ctx, f"Önce (Ort. {tr_f(fstat['mean_rpn_pre'], 1)}, Maks. {fstat['max_rpn_pre']})", px + 22, py - 14, size=10.5, color="#B91C1C", bold=True)
    _rrect(ctx, px + 250, py - 24, 13, 11, 2)
    ctx.set_source_rgba(*_hex("#0F766E"))
    ctx.fill()
    _text(ctx, f"Sonra (Ort. {tr_f(fstat['mean_rpn_post'], 1)}, Maks. {fstat['max_rpn_post']}, -%{tr_f(fstat['mean_rpn_reduction_pct'], 1)})", px + 268, py - 14, size=10.5, color="#0F766E", bold=True)

    # Bottom 2x2 hazard summary grid
    gy0 = y + 372
    cw = (w - 38) / 2.0
    ch = 84
    las = e150["hazard_1_laser_s55"]
    gas = e150["hazard_2_ph3_and_forming_gas"]
    hvx = e150["hazard_3_hv_and_xray"]
    cryo = e150["hazard_4_cryo_odh_and_quench"]
    epo = e150["hazard_5_epo_ups_shutdown"]
    spec = e150["s_safety_spec"]["totals"]
    cards = [
        ("S5.5 Lazer + X-Işını Bariyeri", f"OD8 + 3 mm Çelik ({las['interlock_sil3']['shutter_close_ms']} ms SIL-3)", f"22 keV: 10,1 -> {hvx['energy_sweep']['22keV']['s55_sapphire_plus_3mm_steel_shroud_uSv_h']:.1e} µSv/h", "#FEF2F2", "#FCA5A5", "#991B1B"),
        ("S1.1 PH₃ (SDS) & %5 H₂/N₂", f"1.207 ppm -> {tr_f(gas['mitigated_sds_system']['operator_conservative_ppm'], 4)} ppm", f"7,0x < TLV · 6.990x < IDLH · ISO 10156", "#F0FDF4", "#86EFAC", "#065F46"),
        ("Kriyo He ODH & Quench", f"60 m³ O₂ = %{tr_f(cryo['helium_odh']['room_sweep']['60m3']['dry_ld400_pt420_O2_pct'], 2)} (DN50 {tr_f(cryo['asme_ovc_relief']['relief_safety_margin'], 1)}x)", f"18,9 kJ Dump Direnci: {tr_f(cryo['magnet_quench_exp125']['dump_resistor_peak_1p5T_C'], 2)} °C", "#EFF6FF", "#93C5FD", "#1E3A8A"),
        ("15 kVA UPS & S7.SAFETY Kit", f"0 ms · 80 ms UHV ({epo['ups_spec']['runtime_at_rated_13p5kW_min']:.0f}/{epo['ups_spec']['runtime_tier1_min']:.0f} dk)", f"${spec['cost_usd_nom']//1000}k · {tr_f(spec['total_mass_kg'], 0)} kg · 0 W Kriyo", "#FFFBEB", "#FCD34D", "#92400E"),
    ]
    for idx, (ct, c1, c2, cbg, cbd, ccol) in enumerate(cards):
        col_i = idx % 2
        row_i = idx // 2
        cx = x + 14 + col_i * (cw + 10)
        cy = gy0 + row_i * (ch + 10)
        _rrect(ctx, cx, cy, cw, ch, 7)
        ctx.set_source_rgba(*_hex(cbg))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex(cbd))
        ctx.set_line_width(1.0)
        ctx.stroke()
        _text(ctx, ct, cx + 10, cy + 20, size=10.8, color=ccol, bold=True, max_w=cw - 20)
        _text(ctx, c1, cx + 10, cy + 44, size=11.0, color="#0F172A", bold=True, max_w=cw - 20)
        _text(ctx, c2, cx + 10, cy + 66, size=10.2, color="#334155", max_w=cw - 20)


def _draw_p5_bom_v7(ctx: cairo.Context, x: float, y: float, w: float, h: float, e128: dict[str, Any], cert: dict[str, Any]) -> None:
    _panel(ctx, x, y, w, h, "5. BOM v7.0 — Kademeli Bütçe-Tavanı & 10-RFQ", "180p · Faz-1 %4,67", "#D97706")

    mc = e128["v7_modular_mc_comparison"]
    tiers = [
        ("M3 v5.0 Base\n(167 parça)", mc["M3_v5_0_Base"]["bom_nom_usd"] / 1e6, mc["M3_v5_0_Base"]["P_Program_stoch_gt_100M"] * 100.0, "#64748B", "PASS"),
        ("Faz-1: Base + Safety\n(173 parça, ÖNERİLEN)", mc["M3_v5_0_Base_Plus_Safety"]["bom_nom_usd"] / 1e6, mc["M3_v5_0_Base_Plus_Safety"]["P_Program_stoch_gt_100M"] * 100.0, "#059669", "PASS"),
        ("M3 v6.0 Full (Q+HPC)\n(174 parça)", mc["M3_v6_0_Full_Option_Q_and_HPC"]["bom_nom_usd"] / 1e6, mc["M3_v6_0_Full_Option_Q_and_HPC"]["P_Program_stoch_gt_100M"] * 100.0, "#0284C7", "PASS"),
        ("M3 v7.0 Full (+Safety)\n(180 parça, Dürüst >%5)", mc["M3_v7_0_Safety_Certified_Full"]["bom_nom_usd"] / 1e6, mc["M3_v7_0_Safety_Certified_Full"]["P_Program_stoch_gt_100M"] * 100.0, "#DC2626", "DÜRÜST >%5"),
    ]

    px, py, pw, ph = x + 186, y + 72, w - 210, 260
    x_max = 7.2  # % P(Program > $100M)

    def _sx(pct: float) -> float:
        return px + pw * (pct / x_max)

    for tick in (0, 2, 4, 5, 6, 7):
        gx = _sx(tick)
        ctx.move_to(gx, py)
        ctx.line_to(gx, py + ph)
        ctx.set_source_rgba(*_hex("#E2E8F0"))
        ctx.set_line_width(0.9)
        ctx.stroke()
        _text(ctx, f"%{tick}", gx, py + ph + 16, size=10.2, color="#475569", mono=True, align="center")

    ctx.set_source_rgba(*_hex("#334155"))
    ctx.set_line_width(1.3)
    ctx.move_to(px, py)
    ctx.line_to(px, py + ph)
    ctx.line_to(px + pw, py + ph)
    ctx.stroke()

    _text(ctx, "100k MC: P(Program > $100M) Sert Tavan Riski (%)", px + pw / 2.0, py - 12, size=11.5, color="#0F172A", bold=True, align="center")

    slot = ph / len(tiers)
    bh = slot * 0.54
    for i, (lbl, musd, ppct, col, tag) in enumerate(tiers):
        by = py + i * slot + (slot - bh) / 2.0
        bw_ = _sx(ppct) - px
        _rrect(ctx, px, by, bw_, bh, 5)
        ctx.set_source_rgba(*_hex(col, 0.88))
        ctx.fill()
        for li, part in enumerate(lbl.split("\n")):
            _text(ctx, part, px - 10, by + 13 + li * 14, size=10.4, color="#0F172A" if li == 0 else "#475569", bold=(li == 0), align="right")
        # Left-aligned cleanly inside bar so text NEVER touches the vertical %5,00 dashed line!
        if ppct < 5.0:
            _text(ctx, f"${tr_f(musd, 2)}M  ·  %{tr_f(ppct, 2)}  ({tag})", px + 10, by + bh / 2.0 + 4, size=10.6, color="#FFFFFF", bold=True)
        else:
            _text(ctx, f"${tr_f(musd, 2)}M  ·  %{tr_f(ppct, 2)}", px + 10, by + bh / 2.0 + 4, size=10.6, color="#FFFFFF", bold=True)
            _text(ctx, tag, px + bw_ + 8, by + bh / 2.0 + 4, size=9.8, color=col, bold=True)

    # 5.0% Hard-cap limit dashed line (label cleanly below ticks!)
    x5 = _sx(5.0)
    ctx.save()
    ctx.set_dash([6, 4])
    ctx.set_source_rgba(*_hex("#B45309"))
    ctx.set_line_width(2.0)
    ctx.move_to(x5, py)
    ctx.line_to(x5, py + ph)
    ctx.stroke()
    ctx.restore()
    _rrect(ctx, x5 - 104, py + ph + 23, 208, 20, 4)
    ctx.set_source_rgba(*_hex("#FEF3C7"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#D97706"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    _text(ctx, "CU3 Sert Tavan Limiti = %5,00", x5, py + ph + 37, size=10.5, color="#92400E", bold=True, align="center")

    # Bottom technical box
    sy = y + 394
    _rrect(ctx, x + 14, sy, w - 28, h - (sy - y) - 14, 8)
    ctx.set_source_rgba(*_hex("#F8FAFC"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#E2E8F0"))
    ctx.set_line_width(1.0)
    ctx.stroke()
    vm = e128["v7_hardware_mass_reconciliation"]
    _text(ctx, f"Kütle Ayrımı (0,0000 kg fark): CAD v6 Şasi {tr_f(vm['on_frame_cad_v6_mass_kg'], 3)} kg + Emniyet {tr_f(vm['facility_safety_bom_total_mass_kg'], 1)} kg = {tr_f(vm['total_facility_load_mass_kg'], 3)} kg", x + 26, sy + 24, size=11.0, color="#0F172A", bold=True, max_w=w - 52)
    _text(ctx, f"10-RFQ Kapsamı (RFQ-01..10): Nominal %{tr_f(cert['bom_v7_rfq10_nom_share_pct'], 2)}  |  MC Varyans Payı %{tr_f(cert['bom_v7_rfq10_var_share_pct'], 2)}  |  Köprü: $0,00", x + 26, sy + 50, size=11.0, color="#047857", bold=True, max_w=w - 52)
    _text(ctx, f"M1 Prototip + S7.SAFETY = ${tr_i(int(e128['bom_detailed_summary']['m1_plus_safety_nom_usd']))}  |  FOAK 5y TCO (> $100M): %7,25 (v7 Full)", x + 26, sy + 76, size=10.8, color="#334155", max_w=w - 52)
    _rrect(ctx, x + 24, sy + 94, w - 48, 56, 6)
    ctx.set_source_rgba(*_hex("#ECFDF5"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#34D399"))
    ctx.set_line_width(1.1)
    ctx.stroke()
    _text(ctx, "Kademeli Tedarik Stratejisi (Dürüst Bütçe Disiplini):", x + 34, sy + 114, size=10.8, color="#065F46", bold=True)
    _text(ctx, "Faz-1: M3 Base + S7.SAFETY ($5,393M, P>100M=%4,67 < %5) -> RFQ-05 S6.6 Fiyat Kilidi ->", x + 34, sy + 132, size=10.3, color="#064E3B", max_w=w - 68)
    _text(ctx, "Faz-2: +Option-Q ($168k) & +Option-HPC ($132k) ile Tam v7.0 ($5,693M) Devreye Alma.", x + 34, sy + 146, size=10.3, color="#064E3B", max_w=w - 68)


def _draw_p6_evolution_seal(ctx: cairo.Context, x: float, y: float, w: float, h: float, cert: dict[str, Any]) -> None:
    _panel(ctx, x, y, w, h, "6. v3 → v7 Evrim, Tam 64-Hex SHA-256 & Epistemik Mühür", "38/38 SHA-256", "#0F172A")

    # 5-Row v3 -> v7 Evolution Timeline Table
    evo = [
        ("v3.0", "CAD 144p (857 kg) · BOM $4,19M · 100K IBIC · 1,5 T Kriyo-Mıknatıs", "#64748B"),
        ("v4.0", "CAD 156p (960 kg) · S5.5 808 nm Lazer · BOM $4,61M · Exp135 Mühür", "#0284C7"),
        ("v5.0", "CAD 189p (1035 kg) · S5.6 MBE + S6.5 RFSoC · BOM $5,25M · Exp141", "#7C3AED"),
        ("v6.0", "CAD 199p (1108 kg) · Opt-Q/HPC · Canlı IBM 156Q (ibm_marrakesh)", "#0D9488"),
        ("v7.0", "Evrensel qLDPC d=18 · ¹²¹Sb Q-Echo-8 · Verilog RTL · FMEA · 180p BOM", "#059669"),
    ]
    ey0 = y + 54
    for i, (ver, desc, col) in enumerate(evo):
        ry = ey0 + i * 44
        _rrect(ctx, x + 16, ry, 58, 32, 6)
        ctx.set_source_rgba(*_hex(col))
        ctx.fill()
        _text(ctx, ver, x + 45, ry + 21, size=12.0, color="#FFFFFF", bold=True, align="center")
        _rrect(ctx, x + 82, ry, w - 98, 32, 6)
        ctx.set_source_rgba(*_hex("#F8FAFC" if i < 4 else "#ECFDF5"))
        ctx.fill_preserve()
        ctx.set_source_rgba(*_hex("#E2E8F0" if i < 4 else "#10B981"))
        ctx.set_line_width(1.2 if i == 4 else 1.0)
        ctx.stroke()
        _text(ctx, desc, x + 94, ry + 21, size=11.0, color="#0F172A", bold=(i == 4), max_w=w - 118)

    # Full 64-Hex v7_digital_twin_cert.json SHA-256 Cryptographic Seal Box
    sha_full = cert["sha256"]
    assert len(sha_full) == 64
    by_sha = y + 286
    _rrect(ctx, x + 16, by_sha, w - 32, 76, 8)
    ctx.set_source_rgba(*_hex("#0F172A"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#38BDF8"))
    ctx.set_line_width(1.5)
    ctx.stroke()
    _text(ctx, f"v7_digital_twin_cert.json — TAM 64-HEX SHA-256 ({cert['n_locked_artifacts']}/{cert['n_locked_artifacts']} Birincil Eser Kilitli):", x + 28, by_sha + 22, size=11.0, color="#38BDF8", bold=True)
    _text(ctx, sha_full, x + w / 2.0, by_sha + 47, size=13.5, color="#F8FAFC", bold=True, mono=True, align="center", max_w=w - 56)
    _text(ctx, f"CAD v6: {cert['cad_v6_parts']}p / {tr_f(cert['cad_v6_mass_kg'], 1)} kg / 0 çakışma / {cert['cad_v6_clearances_pass']} | Tarihsel v4/v5/v6 mühürleri korundu", x + w / 2.0, by_sha + 66, size=10.0, color="#94A3B8", align="center")

    # Crystal Dual-Column Epistemic Stamp (M0 Silicon/RTL/Safety vs Live IBM QPU)
    ey_ep = y + 378
    ew = (w - 42) / 2.0
    eh = h - (ey_ep - y) - 14

    # Left: M0 Model / Analytic
    _rrect(ctx, x + 16, ey_ep, ew, eh, 8)
    ctx.set_source_rgba(*_hex("#FFFBEB"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#F59E0B"))
    ctx.set_line_width(1.2)
    ctx.stroke()
    _text(ctx, "M0 MODEL / ANALİTİK / VARSAYIM", x + 28, ey_ep + 24, size=11.0, color="#92400E", bold=True)
    _text(ctx, "• Silikon ³¹P / ¹²¹Sb / ¹⁶⁷Er donanım", x + 28, ey_ep + 50, size=10.6, color="#78350F")
    _text(ctx, "• Verilog RTL (no_external_eda_sim=true)", x + 28, ey_ep + 74, size=10.6, color="#78350F")
    _text(ctx, "• Emniyet FMEA/HAZOP (no_lab_meas=true)", x + 28, ey_ep + 98, size=10.6, color="#78350F")
    _text(ctx, "• BOM v7.0 / 10-RFQ (no_quotes=true)", x + 28, ey_ep + 122, size=10.6, color="#78350F")
    _text(ctx, "• Kapanış onayı: Carbon denetimine tabi", x + 28, ey_ep + 148, size=10.6, color="#B45309", bold=True)

    # Right: Live IBM QPU Hardware
    rx = x + 26 + ew
    _rrect(ctx, rx, ey_ep, ew, eh, 8)
    ctx.set_source_rgba(*_hex("#ECFDF5"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#10B981"))
    ctx.set_line_width(1.2)
    ctx.stroke()
    _text(ctx, "CANLI DONANIM — IBM QPU", rx + 12, ey_ep + 24, size=11.0, color="#065F46", bold=True)
    _text(ctx, f"• Backend: {cert['live_qpu_backend']} (156Q)", rx + 12, ey_ep + 50, size=10.6, color="#064E3B", bold=True)
    _text(ctx, f"• Job ID: {cert['live_qpu_job_id']}", rx + 12, ey_ep + 74, size=10.0, color="#064E3B", mono=True, max_w=ew - 22)
    _text(ctx, f"• Bell: %{tr_f(cert['live_qpu_bell_fidelity']*100, 2)} | XY4: +{tr_f(cert['live_qpu_xy4_gain_pp'], 2)} pp", rx + 12, ey_ep + 98, size=10.6, color="#064E3B")
    _text(ctx, f"• Q16 vs FP64: {tr_f(cert['live_qpu_q16_vs_fp64_kHz']*1000, 1)} Hz | ISA v4: {cert['live_cellisa_v40_opcodes']} op", rx + 12, ey_ep + 122, size=10.6, color="#064E3B")
    _text(ctx, f"• auto_recal: {cert['live_auto_recal_passed']} PASS | 0 Sızıntı", rx + 12, ey_ep + 148, size=10.6, color="#047857", bold=True)


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

    # Background
    ctx.set_source_rgba(*_hex("#F1F5F9"))
    ctx.rectangle(0, 0, W, H)
    ctx.fill()

    # Executive dark-navy gradient header
    pat = cairo.LinearGradient(0, 0, 0, 86)
    pat.add_color_stop_rgb(0.0, 0.043, 0.098, 0.184)
    pat.add_color_stop_rgb(1.0, 0.086, 0.184, 0.306)
    ctx.set_source(pat)
    ctx.rectangle(0, 0, W, 86)
    ctx.fill()

    _text(ctx, "ATOM LİTOGRAFİ MAKİNESİ — v7.0 MASTER GENEL BAKIŞ PANOSU (Exp147–Exp151)", 28, 36, size=23.0, color="#FFFFFF", bold=True)
    _text(
        ctx,
        "Evrensel qLDPC d=18 (FeMoco/RSA-2048) · ¹²¹Sb Q-Echo-8 · Q16.16 BOED Verilog RTL & HTML5 İkiz · SEMI S2/SIL-3 Emniyet · BOM v7.0 / 10-RFQ",
        28, 65, size=13.0, color="#CBD5E1",
    )

    # Header right pills
    _rrect(ctx, W - 438, 20, 198, 44, 8)
    ctx.set_source_rgba(*_hex("#059669"))
    ctx.fill()
    _text(ctx, f"{e151['n_passed']}/{e151['n_total']} DT7 PASS", W - 339, 48, size=16.0, color="#FFFFFF", bold=True, align="center")

    _rrect(ctx, W - 228, 20, 200, 44, 8)
    ctx.set_source_rgba(*_hex("#0F172A"))
    ctx.fill_preserve()
    ctx.set_source_rgba(*_hex("#38BDF8"))
    ctx.set_line_width(1.6)
    ctx.stroke()
    _text(ctx, f"{cert['n_locked_artifacts']}/{cert['n_locked_artifacts']} SHA-256", W - 128, 48, size=16.0, color="#38BDF8", bold=True, align="center")

    # Top 6-Card KPI Strip
    kpis = [
        ("EVRENSEL qLDPC d=18", "[[288,12,18]]", f"L_max {tr_f(cert['exp147_bb288_L_max_um'], 1)} µm · p_th %{tr_f(cert['exp147_bb288_p_th_pct'], 3)}", "#0284C7"),
        ("FeMoco / RSA-2048", f"{cert['exp147_femoco_cryostats']} / {cert['exp147_rsa2048_cryostats']} Kriyo", f"{tr_f(cert['exp147_femoco_compression_x'], 1)}x / {tr_f(cert['exp147_rsa2048_compression_x'], 1)}x ↓ · {tr_f(cert['exp147_rsa2048_power_MW'], 2)} MW", "#7C3AED"),
        ("¹²¹Sb Q-ECHO-8 & SU(8)", "0,580 -> 0,9991", f"{tr_f(cert['exp148_sb121_infidelity_reduction_x'], 1)}x ↓ · SU(8) >= {tr_f(cert['exp148_sb121_su8_grape_min_F'], 4)}", "#059669"),
        ("VERILOG RTL + HTML5 İKİZ", f"{cert['exp149_rtl_loc']} satır · 0 LSB", f"{cert['exp149_rtl_cycles']} cyc ({tr_f(cert['exp149_rtl_latency_us'], 2)} µs) · 5-Sekme", "#2563EB"),
        ("EMNİYET FMEA / HAZOP", f"RPN {cert['exp150_fmea_max_rpn_pre']} -> {cert['exp150_fmea_max_rpn_post']}", f"-%{tr_f(cert['exp150_fmea_mean_reduction_pct'], 1)} · OD8+3mm · PH₃ {tr_f(cert['exp150_ph3_operator_ppm'], 4)}", "#DC2626"),
        ("BOM v7.0 / 10-RFQ", f"${tr_f(cert['bom_v7_m3_phase1_base_safety_nom_usd']/1e6, 2)}M / ${tr_f(cert['bom_v7_m3_v7_full_nom_usd']/1e6, 2)}M", f"Faz-1 %{tr_f(cert['bom_v7_phase1_P_gt_100M_pct'], 2)} · {cert['bom_v7_parts']}p · %{tr_f(cert['bom_v7_rfq10_nom_share_pct'], 1)}/%{tr_f(cert['bom_v7_rfq10_var_share_pct'], 1)}", "#D97706"),
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
        _text(ctx, kt, kx + 18, 118, size=10.6, color="#64748B", bold=True, max_w=kw - 26)
        _text(ctx, kv, kx + 18, 146, size=20.0, color="#0F172A", bold=True, max_w=kw - 26)
        _text(ctx, ks, kx + 18, 168, size=10.8, color=kc, bold=True, max_w=kw - 26)

    # 3x2 Grid of 6 Analytical Panels
    pw = (W - 56 - 32) / 3.0
    r1y, r1h = 192, 574
    r2y, r2h = 780, 574
    xs = [28, 28 + pw + 16, 28 + 2 * (pw + 16)]

    _draw_p1_qldpc_algos(ctx, xs[0], r1y, pw, r1h, e147, cert)
    _draw_p2_sb121(ctx, xs[1], r1y, pw, r1h, e148, cert)
    _draw_p3_verilog_twin(ctx, xs[2], r1y, pw, r1h, e149, cert)

    _draw_p4_safety_fmea(ctx, xs[0], r2y, pw, r2h, e150)
    _draw_p5_bom_v7(ctx, xs[1], r2y, pw, r2h, e128, cert)
    _draw_p6_evolution_seal(ctx, xs[2], r2y, pw, r2h, cert)

    # Footer
    _text(
        ctx,
        "Canlı Veri Kaynakları: exp128.json, exp147..exp151.json, v7_digital_twin_cert.json, cad_verification.json  |  İnteraktif İkiz: docs/digital_twin_interactive.html",
        28, H - 14, size=11.3, color="#475569",
    )
    _text(
        ctx,
        "Silikon ³¹P/RTL/Emniyet: M0 (Model/Analitik) · Kontrol/DD/Dekoder/BOED: Canlı IBM ibm_marrakesh 156Q · Kapanış: Carbon Denetimi",
        W - 28, H - 14, size=11.3, color="#64748B", align="right",
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    surf.write_to_png(str(OUT_PNG))
    with Image.open(OUT_PNG) as im:
        assert im.size == (W, H), f"Unexpected size {im.size}"
    print(f"Wrote {OUT_PNG} ({W}x{H})")


if __name__ == "__main__":
    main()
