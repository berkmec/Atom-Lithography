"""Exp125 PyCairo + PIL High-Resolution Engineering Figure Generator.

Run with: /usr/bin/python3 -B experiments/exp125_cryo_magnet_readout/plot_exp125.py
Produces:
  - results/exp125_cryo_magnet_readout/fig_exp125_bfield_map.png
  - results/exp125_cryo_magnet_readout/fig_exp125_thermal_snr.png
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Tuple

import cairo
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "exp125_cryo_magnet_readout"


# ---------------------------------------------------------------------------
# Color helpers (smooth perceptually-inspired inferno/viridis hybrid colormap)
# ---------------------------------------------------------------------------
CMAP_STOPS = [
    (0.00, (12, 16, 42)),
    (0.18, (28, 42, 105)),
    (0.36, (20, 108, 148)),
    (0.55, (42, 168, 138)),
    (0.74, (224, 186, 52)),
    (0.88, (238, 102, 42)),
    (1.00, (186, 22, 44)),
]


def cmap_rgb(val01: float) -> Tuple[int, int, int]:
    v = max(0.0, min(1.0, val01))
    for i in range(len(CMAP_STOPS) - 1):
        t0, c0 = CMAP_STOPS[i]
        t1, c1 = CMAP_STOPS[i + 1]
        if v <= t1:
            f = (v - t0) / max(t1 - t0, 1e-12)
            return (
                int(round(c0[0] + f * (c1[0] - c0[0]))),
                int(round(c0[1] + f * (c1[1] - c0[1]))),
                int(round(c0[2] + f * (c1[2] - c0[2]))),
            )
    return CMAP_STOPS[-1][1]


def set_rgb(ctx: cairo.Context, r: float, g: float, b: float, a: float = 1.0):
    ctx.set_source_rgba(r, g, b, a)


def draw_text(
    ctx: cairo.Context,
    x: float,
    y: float,
    text: str,
    size: float = 13.0,
    bold: bool = False,
    color=(0.12, 0.14, 0.18, 1.0),
    align: str = "left",
    valign: str = "baseline",
    angle: float = 0.0,
):
    ctx.save()
    ctx.select_font_face(
        "DejaVu Sans",
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
        dx = -(ext.width / 2.0 + ext.x_bearing)
    elif align == "right":
        dx = -(ext.width + ext.x_bearing)
    dy = 0.0
    if valign == "middle":
        dy = -(ext.height / 2.0 + ext.y_bearing)
    elif valign == "top":
        dy = -ext.y_bearing
    ctx.set_source_rgba(*color)
    ctx.move_to(dx, dy)
    ctx.show_text(text)
    ctx.restore()


def draw_panel_box(ctx: cairo.Context, x: float, y: float, w: float, h: float, title: str = ""):
    ctx.save()
    set_rgb(ctx, 1.0, 1.0, 1.0, 1.0)
    ctx.rectangle(x, y, w, h)
    ctx.fill()
    set_rgb(ctx, 0.78, 0.81, 0.86, 1.0)
    ctx.set_line_width(1.2)
    ctx.rectangle(x, y, w, h)
    ctx.stroke()
    ctx.restore()
    if title:
        draw_text(ctx, x + 10, y - 8, title, size=14.0, bold=True, color=(0.10, 0.13, 0.20, 1.0))


# ---------------------------------------------------------------------------
# FIGURE 1: 2D Magnetic Field Map + Axial/Sample/Resonator Profiles
# ---------------------------------------------------------------------------
def make_bfield_figure(data: dict, out_path: Path):
    W, H = 1800, 1080
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)

    # Background
    set_rgb(ctx, 0.97, 0.975, 0.985)
    ctx.paint()

    # Main title banner
    draw_text(
        ctx, 32, 36,
        "Exp125 — Risk R7 Kapanışı: 1,50 T Aktif Karşı-Sargılı Kriyo-Mıknatıs + Nb Meissner Kalkan (Biot-Savart + BEM)",
        size=19.5, bold=True, color=(0.08, 0.11, 0.18, 1.0)
    )
    sam = data["sample"]
    rz = data["resonator_zone"]
    nb = data["nb_shield_check"]
    draw_text(
        ctx, 32, 58,
        (
            f"Örnek (r<=2,3 mm): Bz = {sam['Bz_center_T']:.4f} T ± {sam['homogeneity_ppm_Bz']:.1f} ppm  |  "
            f"Rezonatör (z={rz['z_res_loc_mm']:.0f} mm, r<=25 mm): kalkanlı |B| <= {rz['shielded_max_B_mT']:.3f} mT "
            f"(|Bz|<={rz['shielded_max_Bz_mT']:.3f} mT, |Br|<={rz['shielded_max_Br_mT']:.3f} mT)  |  "
            f"Nb yüzey max B_surf = {nb['screened_max_B_surf_mT']:.1f} mT < Bc1(4,2K) = {nb['Bc1_Nb_4p2K_mT']:.1f} mT"
        ),
        size=12.5, color=(0.24, 0.28, 0.36, 1.0)
    )

    fm = data["field_map"]
    cad = data["cad_geometry_mm"]
    r_mm = fm["r_mm"]
    z_mm = fm["z_mm"]
    Bmag = fm["Bmag_T"]
    nr, nz = len(r_mm), len(z_mm)
    r_min, r_max = r_mm[0], r_mm[-1]
    z_min, z_max = z_mm[0], z_mm[-1]

    # --- LEFT PANEL: 2D (r, z) log10|B| map ---
    px, py, pw, ph = 85, 102, 760, 905
    draw_panel_box(ctx, px, py, pw, ph, "A. Eksenel Simetrik 2B Manyetik Alan Haritası log10(|B|/T) & Bobin/Kalkan Geometrisi")

    # Build PIL image for colormap (width=nr, height=nz, y flipped so z_max at top)
    log_lo, log_hi = -5.0, 0.65  # 10 uT to 4.5 T
    img = Image.new("RGB", (nr, nz))
    pix = img.load()
    for ir in range(nr):
        col = Bmag[ir]
        for iz in range(nz):
            b = max(col[iz], 1e-6)
            t = (math.log10(b) - log_lo) / (log_hi - log_lo)
            pix[ir, nz - 1 - iz] = cmap_rgb(t)
    img_scaled = img.resize((int(pw), int(ph)), Image.Resampling.BILINEAR).convert("RGBA")
    # Convert RGBA -> Cairo BGRA
    rgba_bytes = img_scaled.tobytes("raw", "BGRA")
    map_surf = cairo.ImageSurface.create_for_data(
        bytearray(rgba_bytes), cairo.FORMAT_ARGB32, int(pw), int(ph), int(pw) * 4
    )
    ctx.save()
    ctx.set_source_surface(map_surf, px, py)
    ctx.paint()
    ctx.restore()

    def map_rz(r_val: float, z_val: float) -> Tuple[float, float]:
        ux = px + (r_val - r_min) / (r_max - r_min) * pw
        uy = py + (z_max - z_val) / (z_max - z_min) * ph
        return ux, uy

    # Grid lines & ticks on 2D map
    ctx.save()
    ctx.set_dash([3, 4])
    set_rgb(ctx, 1.0, 1.0, 1.0, 0.28)
    ctx.set_line_width(0.8)
    for rv in (0, 25, 50, 75, 100, 125, 150, 175):
        ux, _ = map_rz(rv, z_min)
        ctx.move_to(ux, py); ctx.line_to(ux, py + ph); ctx.stroke()
        draw_text(ctx, ux, py + ph + 18, str(rv), size=11.5, align="center")
    for zv in (-200, -150, -100, -50, 0, 50, 100, 150):
        _, uy = map_rz(0, zv)
        ctx.move_to(px, uy); ctx.line_to(px + pw, uy); ctx.stroke()
        draw_text(ctx, px - 8, uy, str(zv), size=11.5, align="right", valign="middle")
    ctx.restore()
    draw_text(ctx, px + pw / 2, py + ph + 40, "Yarıçap r (mm)", size=13.0, bold=True, align="center")
    draw_text(ctx, px - 56, py + ph / 2, "Eksenel konum z_loc (mm)  [z_makine = z_loc + 500 mm (CAD v3.0)]", size=12.5, bold=True, align="center", angle=-math.pi / 2)

    # Draw 8 coils
    role_colors = {
        "main": (0.98, 0.98, 0.98, 0.92),
        "shim": (0.98, 0.88, 0.35, 0.92),
        "active_shield": (0.65, 0.88, 1.0, 0.92),
        "bucking": (0.45, 1.0, 0.65, 0.92),
    }
    for cm in cad["coils"]:
        x0, y0 = map_rz(cm["r_in_mm"], cm["z_max_loc_mm"])
        x1, y1 = map_rz(cm["r_out_mm"], cm["z_min_loc_mm"])
        col = role_colors.get(cm["role"], (1, 1, 1, 0.9))
        ctx.save()
        ctx.set_source_rgba(col[0], col[1], col[2], 0.25)
        ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
        ctx.fill()
        ctx.set_source_rgba(*col)
        ctx.set_line_width(2.0)
        ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
        ctx.stroke()
        # Cross-hatch lines inside coil
        ctx.set_line_width(0.8)
        ctx.move_to(x0, y0); ctx.line_to(x1, y1)
        ctx.move_to(x1, y0); ctx.line_to(x0, y1)
        ctx.stroke()
        ctx.restore()
        lbl = f"{cm['name']} ({cm['current_A']:+.0f}A)"
        draw_text(ctx, (x0 + x1) / 2, (y0 + y1) / 2, lbl, size=10.0, bold=True,
                  color=(1.0, 1.0, 1.0, 0.98), align="center", valign="middle")

    # Draw Nb Meissner cup + chimney
    nb_c = cad["nb_meissner_cup"]
    ctx.save()
    set_rgb(ctx, 0.15, 0.95, 1.0, 1.0)
    ctx.set_line_width(3.0)
    pts = [
        (0.0, nb_c["z_bot_loc_mm"]),
        (nb_c["r_outer_mm"], nb_c["z_bot_loc_mm"]),
        (nb_c["r_outer_mm"], nb_c["z_top_loc_mm"]),
        (nb_c["coax_port_radius_mm"], nb_c["z_top_loc_mm"]),
        (nb_c["coax_port_radius_mm"], nb_c["coax_chimney_top_loc_mm"]),
    ]
    for i, (rv, zv) in enumerate(pts):
        ux, uy = map_rz(rv, zv)
        if i == 0:
            ctx.move_to(ux, uy)
        else:
            ctx.line_to(ux, uy)
    ctx.stroke()
    ctx.restore()

    # Draw Cryoperm-10 outer sleeve (dashed white)
    cp_c = cad["cryoperm_outer_sleeve"]
    ctx.save()
    set_rgb(ctx, 0.95, 0.95, 0.98, 0.9)
    ctx.set_dash([6, 4])
    ctx.set_line_width(2.0)
    ux0, uy0 = map_rz(cp_c["r_outer_mm"], cp_c["z_top_loc_mm"])
    ux1, uy1 = map_rz(cp_c["r_outer_mm"], cp_c["z_bot_loc_mm"])
    ctx.move_to(ux0, uy0); ctx.line_to(ux1, uy1); ctx.stroke()
    ctx.restore()

    # Sample active zone & Resonator carrier markers
    sx0, sy0 = map_rz(0.0, +0.5)
    sx1, sy1 = map_rz(2.3, -0.5)
    ctx.save()
    set_rgb(ctx, 1.0, 1.0, 1.0, 1.0)
    ctx.set_line_width(2.5)
    ctx.rectangle(sx0 - 1, sy0 - 3, max(sx1 - sx0 + 4, 12), max(sy1 - sy0 + 6, 8))
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, sx1 + 10, sy0 + 2, "Örnek (1,5000 T ± 17,8 ppm)", size=11.0, bold=True, color=(1, 1, 1, 1))

    rx0, ry0 = map_rz(0.0, rz["z_res_loc_mm"] + 3.0)
    rx1, ry1 = map_rz(25.0, rz["z_res_loc_mm"] - 3.0)
    ctx.save()
    set_rgb(ctx, 0.4, 1.0, 0.5, 1.0)
    ctx.set_line_width(2.0)
    ctx.rectangle(rx0, ry0, rx1 - rx0, ry1 - ry0)
    ctx.stroke()
    ctx.restore()
    draw_text(ctx, rx0 + 4, ry1 + 14, "NbTiN Rezonatör", size=9.8, bold=True, color=(0.75, 1.0, 0.85, 1.0))
    draw_text(ctx, rx0 + 4, ry1 + 26, "(<=0,022 mT)", size=9.5, bold=True, color=(0.75, 1.0, 0.85, 1.0))
    draw_text(ctx, rx1 + 52, ry0 - 52, "Nb Kalkan + Cryoperm", size=10.5, bold=True, color=(0.65, 0.98, 1.0, 1.0))

    # Colorbar to the right of Panel A
    cbx, cby, cbw, cbh = px + pw + 18, py, 22, ph
    for iy in range(int(cbh)):
        t = 1.0 - iy / max(cbh - 1, 1)
        rr, gg, bb = cmap_rgb(t)
        set_rgb(ctx, rr / 255.0, gg / 255.0, bb / 255.0)
        ctx.rectangle(cbx, cby + iy, cbw, 1.5)
        ctx.fill()
    set_rgb(ctx, 0.4, 0.44, 0.5)
    ctx.set_line_width(1.0)
    ctx.rectangle(cbx, cby, cbw, cbh); ctx.stroke()
    for lv, lbl in [(-5, "10 µT"), (-4, "0,1 mT"), (-3, "1 mT"), (-2, "10 mT"), (-1, "0,1 T"), (0, "1 T"), (0.6, "4 T")]:
        ty = cby + (1.0 - (lv - log_lo) / (log_hi - log_lo)) * cbh
        draw_text(ctx, cbx + cbw + 6, ty, lbl, size=10.5, valign="middle")

    # --- RIGHT TOP PANEL (B): Axial Bz(0, z) Profile ---
    bx, by, bw, bh = 975, 102, 790, 245
    draw_panel_box(ctx, bx, by, bw, bh, "B. Eksenel Alan Profili Bz(r=0, z): Örnek 1,50 T Düzlüğü ve Rezonatör Sıfır Bölgesi")
    z_ax = fm["axial_z_mm"]
    bz_u = fm["axial_Bz_unshielded_T"]
    bz_s = fm["axial_Bz_shielded_T"]
    zx0, zx1 = -220.0, 280.0
    by0, by1 = -0.35, 1.85

    def map_b(zv, bv):
        return bx + (zv - zx0) / (zx1 - zx0) * bw, by + (by1 - bv) / (by1 - by0) * bh

    # Grid & zero/threshold lines
    ctx.save()
    set_rgb(ctx, 0.88, 0.90, 0.93)
    ctx.set_line_width(0.8)
    for zv in (-200, -150, -100, -50, 0, 50, 100, 150, 200, 250):
        ux, _ = map_b(zv, 0)
        ctx.move_to(ux, by); ctx.line_to(ux, by + bh); ctx.stroke()
        draw_text(ctx, ux, by + bh + 14, str(zv), size=10.5, align="center")
    for bv in (0.0, 0.4, 1.0, 1.5):
        _, uy = map_b(0, bv)
        ctx.move_to(bx, uy); ctx.line_to(bx + bw, uy); ctx.stroke()
        draw_text(ctx, bx - 6, uy, f"{bv:.1f}", size=10.5, align="right", valign="middle")
    # 0.4 T Exp109 limit line
    ctx.set_dash([5, 4])
    set_rgb(ctx, 0.85, 0.25, 0.2, 0.85)
    ctx.set_line_width(1.4)
    _, uy_04 = map_b(0, 0.4)
    ctx.move_to(bx, uy_04); ctx.line_to(bx + bw, uy_04); ctx.stroke()
    # Resonator plane vertical marker
    set_rgb(ctx, 0.1, 0.65, 0.35, 0.8)
    ux_r, _ = map_b(-155.0, 0)
    ctx.move_to(ux_r, by); ctx.line_to(ux_r, by + bh); ctx.stroke()
    # Sample plane vertical marker
    set_rgb(ctx, 0.2, 0.3, 0.75, 0.7)
    ux_s, _ = map_b(0.0, 0)
    ctx.move_to(ux_s, by); ctx.line_to(ux_s, by + bh); ctx.stroke()
    ctx.restore()

    # Plot unshielded (dashed orange) and shielded (solid deep blue)
    for arr, col, dash, lw in [
        (bz_u, (0.90, 0.48, 0.12, 0.9), [6, 4], 2.0),
        (bz_s, (0.10, 0.32, 0.72, 1.0), [], 2.6),
    ]:
        ctx.save()
        ctx.set_source_rgba(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        for i, (zv, bv) in enumerate(zip(z_ax, arr)):
            ux, uy = map_b(zv, max(by0, min(by1, bv)))
            if i == 0:
                ctx.move_to(ux, uy)
            else:
                ctx.line_to(ux, uy)
        ctx.stroke()
        ctx.restore()

    draw_text(ctx, bx + bw / 2, by + bh + 30, "Eksenel konum z_loc (mm)", size=11.0, bold=True, align="center")
    draw_text(ctx, bx - 40, by + bh / 2, "Bz (T)", size=11.5, bold=True, align="center", angle=-math.pi / 2)
    # Clean legend box top-right (well right of curve peak)
    ctx.save()
    set_rgb(ctx, 1.0, 1.0, 1.0, 0.92)
    ctx.rectangle(bx + bw - 220, by + 10, 210, 42); ctx.fill()
    set_rgb(ctx, 0.76, 0.80, 0.86); ctx.set_line_width(0.9)
    ctx.rectangle(bx + bw - 220, by + 10, 210, 42); ctx.stroke()
    set_rgb(ctx, 0.10, 0.32, 0.72, 1.0); ctx.set_line_width(2.5)
    ctx.move_to(bx + bw - 210, by + 23); ctx.line_to(bx + bw - 186, by + 23); ctx.stroke()
    set_rgb(ctx, 0.90, 0.48, 0.12, 0.95); ctx.set_dash([5, 3]); ctx.set_line_width(2.0)
    ctx.move_to(bx + bw - 210, by + 40); ctx.line_to(bx + bw - 186, by + 40); ctx.stroke()
    ctx.restore()
    draw_text(ctx, bx + bw - 180, by + 23, "Kalkanlı (Nb BEM)", size=10.2, bold=True, valign="middle", color=(0.10, 0.30, 0.68, 1.0))
    draw_text(ctx, bx + bw - 180, by + 40, "Kalkansız (Karşı-Sargı)", size=10.2, valign="middle", color=(0.75, 0.36, 0.08, 1.0))

    draw_text(ctx, bx + bw - 10, uy_04 - 8, "Exp109 NbTiN sınırı (0,40 T)", size=10.0, color=(0.8, 0.2, 0.15, 1.0), align="right")
    draw_text(ctx, ux_r + 6, by + 24, "Rezonatör (-155 mm)", size=10.0, bold=True, color=(0.08, 0.55, 0.28, 1.0))
    draw_text(ctx, ux_s - 6, by + 24, "Örnek (1,50 T)", size=10.2, bold=True, color=(0.15, 0.25, 0.65, 1.0), align="right")

    # --- RIGHT MIDDLE PANEL (C): Sample Homogeneity (ppm) ---
    cx, cy, cw, ch = 975, 412, 790, 232
    draw_panel_box(ctx, cx, cy, cw, ch, "C. Örnek Aktif Alan Homojenliği ΔBz/B0 (ppm) — 3,2×3,2 mm (r <= 2,3 mm)")
    r_sp = fm["sample_r_mm"]
    db_ppm = fm["sample_dB_ppm"]
    cx0, cx1 = 0.0, 3.0
    cy0, cy1 = -120.0, 120.0

    def map_c(rv, pv):
        return cx + (rv - cx0) / (cx1 - cx0) * cw, cy + (cy1 - pv) / (cy1 - cy0) * ch

    # Shaded +-100 ppm spec band
    ctx.save()
    _, u_p100 = map_c(0, 100.0)
    _, u_m100 = map_c(0, -100.0)
    set_rgb(ctx, 0.85, 0.96, 0.88, 0.6)
    ctx.rectangle(cx, u_p100, cw, u_m100 - u_p100)
    ctx.fill()
    # Active chip radius shading r <= 2.3 mm
    u_r23, _ = map_c(2.3, 0)
    set_rgb(ctx, 0.2, 0.5, 0.9, 0.08)
    ctx.rectangle(cx, cy, u_r23 - cx, ch)
    ctx.fill()
    set_rgb(ctx, 0.82, 0.86, 0.90)
    ctx.set_line_width(0.8)
    for pv in (-100, -50, 0, 50, 100):
        _, uy = map_c(0, pv)
        ctx.move_to(cx, uy); ctx.line_to(cx + cw, uy); ctx.stroke()
        draw_text(ctx, cx - 6, uy, str(pv), size=10.5, align="right", valign="middle")
    for rv in (0.0, 0.5, 1.0, 1.5, 2.0, 2.3, 3.0):
        ux, _ = map_c(rv, 0)
        ctx.move_to(ux, cy); ctx.line_to(ux, cy + ch); ctx.stroke()
        draw_text(ctx, ux, cy + ch + 15, f"{rv:.1f}", size=10.5, align="center")
    # +-100 ppm dashed borders
    ctx.set_dash([5, 4])
    set_rgb(ctx, 0.82, 0.22, 0.18, 0.9)
    ctx.set_line_width(1.4)
    ctx.move_to(cx, u_p100); ctx.line_to(cx + cw, u_p100); ctx.stroke()
    ctx.move_to(cx, u_m100); ctx.line_to(cx + cw, u_m100); ctx.stroke()
    # r=2.3 mm vertical boundary
    set_rgb(ctx, 0.12, 0.35, 0.72, 0.85)
    ctx.move_to(u_r23, cy); ctx.line_to(u_r23, cy + ch); ctx.stroke()
    ctx.restore()

    ctx.save()
    set_rgb(ctx, 0.12, 0.30, 0.75, 1.0)
    ctx.set_line_width(2.6)
    for i, (rv, pv) in enumerate(zip(r_sp, db_ppm)):
        ux, uy = map_c(rv, max(cy0, min(cy1, pv)))
        if i == 0:
            ctx.move_to(ux, uy)
        else:
            ctx.line_to(ux, uy)
    ctx.stroke()
    ctx.restore()

    draw_text(ctx, cx + cw / 2, cy + ch + 32, "Örnek düzlemi yarıçapı r (mm)", size=11.5, bold=True, align="center")
    draw_text(ctx, cx - 44, cy + ch / 2, "ΔBz/B0 (ppm)", size=11.5, bold=True, align="center", angle=-math.pi / 2)
    draw_text(ctx, u_r23 - 8, cy + 28, f"Aktif yonga (r<=2,3 mm, |z|<=0,5 mm): max {sam['homogeneity_ppm_Bz']:.1f} ppm (<100 ppm)",
              size=11.0, bold=True, color=(0.08, 0.40, 0.22, 1.0), align="right")

    # --- RIGHT BOTTOM PANEL (D): Resonator Plane Radial Field (log mT) ---
    dx, dy, dw, dh = 975, 720, 790, 287
    draw_panel_box(ctx, dx, dy, dw, dh, "D. Rezonatör Düzlemi (z = -155 mm) Alan Bileşenleri (log mT): Kalkansız vs Nb Meissner Kalkan")
    r_rp = fm["res_r_mm"]
    l_lo, l_hi = -3.0, 2.6  # 0.001 mT (1 uT) to 400 mT

    def map_d(rv, mt_val):
        lv = math.log10(max(abs(mt_val), 10 ** l_lo))
        return dx + (rv / 28.0) * dw, dy + (l_hi - lv) / (l_hi - l_lo) * dh

    ctx.save()
    set_rgb(ctx, 0.88, 0.90, 0.93)
    ctx.set_line_width(0.8)
    for lv, lbl in [(-3, "1 µT"), (-2, "0,01"), (-1, "0,1"), (0, "1"), (1, "10"), (2, "100"), (2.4, "250 mT")]:
        _, uy = map_d(0, 10 ** lv)
        ctx.move_to(dx, uy); ctx.line_to(dx + dw, uy); ctx.stroke()
        draw_text(ctx, dx - 6, uy, lbl, size=10.0, align="right", valign="middle")
    for rv in (0, 5, 10, 15, 20, 25):
        ux, _ = map_d(rv, 1.0)
        ctx.move_to(ux, dy); ctx.line_to(ux, dy + dh); ctx.stroke()
        draw_text(ctx, ux, dy + dh + 15, str(rv), size=10.5, align="center")
    # Threshold lines: 250 mT (|B_res|) and 10 mT (|B_perp|)
    ctx.set_dash([6, 4])
    set_rgb(ctx, 0.85, 0.18, 0.18, 0.9)
    ctx.set_line_width(1.6)
    _, uy_250 = map_d(0, 250.0)
    ctx.move_to(dx, uy_250); ctx.line_to(dx + dw, uy_250); ctx.stroke()
    set_rgb(ctx, 0.88, 0.45, 0.08, 0.9)
    _, uy_10 = map_d(0, 10.0)
    ctx.move_to(dx, uy_10); ctx.line_to(dx + dw, uy_10); ctx.stroke()
    # Carrier radius r=25 mm
    set_rgb(ctx, 0.25, 0.28, 0.35, 0.7)
    ux_25, _ = map_d(25.0, 1.0)
    ctx.move_to(ux_25, dy); ctx.line_to(ux_25, dy + dh); ctx.stroke()
    ctx.restore()

    series_d = [
        (fm["res_Bz_unshielded_mT"], (0.90, 0.45, 0.12, 0.95), [5, 3], 2.0, "|Bz| kalkansız (aktif karşı-sargı)"),
        (fm["res_Br_unshielded_mT"], (0.72, 0.22, 0.55, 0.85), [3, 3], 1.8, "|Br| kalkansız"),
        (fm["res_Bz_shielded_mT"], (0.08, 0.38, 0.78, 1.0), [], 2.6, "|Bz| Nb kalkanlı (<=0,022 mT)"),
        (fm["res_Br_shielded_mT"], (0.06, 0.65, 0.42, 1.0), [], 2.4, "|Br| Nb kalkanlı (<=0,008 mT)"),
    ]
    for arr, col, dash, lw, _lbl in series_d:
        ctx.save()
        ctx.set_source_rgba(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        for i, (rv, mv) in enumerate(zip(r_rp, arr)):
            ux, uy = map_d(rv, mv)
            if i == 0:
                ctx.move_to(ux, uy)
            else:
                ctx.line_to(ux, uy)
        ctx.stroke()
        ctx.restore()

    draw_text(ctx, dx + dw / 2, dy + dh + 32, "Rezonatör taşıyıcı yarıçapı r (mm)  [Taşıyıcı sınırı r = 25 mm]", size=11.5, bold=True, align="center")
    draw_text(ctx, dx - 44, dy + dh / 2, "|B| (mT, log)", size=11.5, bold=True, align="center", angle=-math.pi / 2)
    draw_text(ctx, dx + 10, uy_250 + 13, "Hedef |B_res| <= 250 mT (0,25 T)", size=10.0, bold=True, color=(0.82, 0.15, 0.15, 1.0))
    draw_text(ctx, dx + 10, uy_10 - 6, "Hedef |B_perp| <= 10 mT (hem |Bz| hem |Br| >450x altında!)", size=10.0, bold=True, color=(0.82, 0.40, 0.05, 1.0))
    # Compact legend in clean upper-right open area below 10 mT line
    ctx.save()
    set_rgb(ctx, 1.0, 1.0, 1.0, 0.92)
    ctx.rectangle(dx + dw - 275, dy + 16, 265, 72); ctx.fill()
    set_rgb(ctx, 0.76, 0.80, 0.86); ctx.set_line_width(0.9)
    ctx.rectangle(dx + dw - 275, dy + 16, 265, 72); ctx.stroke()
    ctx.restore()
    for idx, (_a, col, dash, _lw, lbl) in enumerate(series_d):
        ly = dy + 28 + idx * 16
        ctx.save()
        ctx.set_source_rgba(*col)
        ctx.set_line_width(2.4)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(dx + dw - 266, ly); ctx.line_to(dx + dw - 241, ly); ctx.stroke()
        ctx.restore()
        draw_text(ctx, dx + dw - 235, ly, lbl, size=9.8, valign="middle", color=(0.15, 0.18, 0.24, 1.0))

    surface.write_to_png(str(out_path))
    print("Wrote:", out_path)


# ---------------------------------------------------------------------------
# FIGURE 2: 5-Stage Thermal Budget + 4K Scaling + Risk R8 Valley & Break-Even
# ---------------------------------------------------------------------------
def make_thermal_r8_figure(data: dict, out_path: Path):
    W, H = 1800, 1080
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)

    set_rgb(ctx, 0.97, 0.975, 0.985)
    ctx.paint()

    draw_text(
        ctx, 32, 36,
        "Exp125 — Birleşik 5-Kademe Kriyo Termal Bütçe, RF SNR Marjı ve Risk R8 Faz-Duyarlı Vadi Girişimi",
        size=19.5, bold=True, color=(0.08, 0.11, 0.18, 1.0)
    )
    be = data["r8_breakeven"]
    snr20 = data["rf_snr"]["20mK_LNA1p4K_dG0p05"]
    snr1k = data["rf_snr"]["1p5K_LNA3p0K_dG0p05"]
    draw_text(
        ctx, 32, 58,
        (
            f"Altın ölçek 9000 kanal (56-82 zincir, -100 dBm/ton + mıknatıs/CMOS yükleri dahil)  |  "
            f"RF SNR=10 süresi: {snr20['tau_for_SNR10_ms']:.3f} ms (20 mK) / {snr1k['tau_for_SNR10_ms']:.3f} ms (1,5 K) << t_eff = 1445 ms  |  "
            f"1 K maliyet başa-baş verimi p_crit = {be['p_crit_golden_cost_parity']:.3f}"
        ),
        size=12.5, color=(0.24, 0.28, 0.36, 1.0)
    )

    th20 = data["thermal_20mk"]
    th1k = data["thermal_1k"]

    # --- PANEL A (Top-Left): 5-Stage Utilization (% of PT410/DR capacity) ---
    ax, ay, aw, ah = 82, 105, 795, 420
    draw_panel_box(ctx, ax, ay, aw, ah, "A. 5-Kademe Kriyojenik Kapasite Kullanımı (% PT410 + DR Bütçesi, 9000 Kanal)")
    stages = [
        ("50 K\n(40 W)", "50K_frac"),
        ("4 K\n(1,0 W PT410)", "4K_frac"),
        ("Still\n(40 mW)", "Still_frac"),
        ("CP\n(200 µW)", "CP_frac"),
        ("MXC 20 mK\n(19 µW)", "MXC_20mK_frac"),
    ]
    bars = [
        ("NL163 (56 hat), 2,1 mW HEMT", th20["NL163_H2.1"]["utilization_pt410"], (0.12, 0.56, 0.42, 0.92)),
        ("NL160 (57 hat), 7,8 mW HEMT", th20["NL160_H7.8"]["utilization_pt410"], (0.16, 0.42, 0.78, 0.92)),
        ("NL110 (82 hat), 7,8 mW HEMT", th20["NL110_H7.8"]["utilization_pt410"], (0.90, 0.56, 0.14, 0.92)),
        ("NL110 (82 hat), 10,5 mW (PT415+)", th20["NL110_H10.5"]["utilization_pt410"], (0.82, 0.22, 0.24, 0.92)),
    ]
    ymax_a = 125.0

    def map_ay(pct):
        return ay + (ymax_a - pct) / ymax_a * ah

    ctx.save()
    set_rgb(ctx, 0.88, 0.90, 0.93)
    ctx.set_line_width(0.8)
    for pv in (0, 25, 50, 75, 100, 120):
        uy = map_ay(pv)
        ctx.move_to(ax, uy); ctx.line_to(ax + aw, uy); ctx.stroke()
        draw_text(ctx, ax - 8, uy, f"{pv}%", size=10.5, align="right", valign="middle")
    # 100% PT410 wall
    ctx.set_dash([6, 4])
    set_rgb(ctx, 0.85, 0.15, 0.15, 0.9)
    ctx.set_line_width(1.8)
    uy100 = map_ay(100.0)
    ctx.move_to(ax, uy100); ctx.line_to(ax + aw, uy100); ctx.stroke()
    ctx.restore()

    group_w = aw / len(stages)
    bw_bar = group_w * 0.17
    for si, (slbl, skey) in enumerate(stages):
        gx = ax + (si + 0.5) * group_w
        # Draw 2-line stage label
        lines_lbl = slbl.split("\n")
        draw_text(ctx, gx, ay + ah + 16, lines_lbl[0], size=11.0, bold=True, align="center")
        draw_text(ctx, gx, ay + ah + 31, lines_lbl[1], size=9.8, color=(0.32, 0.36, 0.42, 1.0), align="center")
        for bi, (_blbl, udict, col) in enumerate(bars):
            pct = udict[skey] * 100.0
            bx0 = gx + (bi - 1.5) * (bw_bar + 3) - bw_bar / 2
            by_top = map_ay(min(pct, ymax_a))
            by_bot = map_ay(0.0)
            ctx.save()
            ctx.set_source_rgba(*col)
            ctx.rectangle(bx0, by_top, bw_bar, by_bot - by_top)
            ctx.fill()
            ctx.restore()
            if pct >= 18.0:
                draw_text(ctx, bx0 + bw_bar / 2, by_top - 4, f"{pct:.0f}%", size=9.2, bold=True, align="center")

    draw_text(ctx, ax - 48, ay + ah / 2, "Kademe Kullanımı (%)", size=12.0, bold=True, align="center", angle=-math.pi / 2)
    draw_text(ctx, ax + aw - 10, uy100 + 15, "Tek PT410 / 20 mK Sınırı (%100)", size=10.5, bold=True, color=(0.82, 0.14, 0.14, 1.0), align="right")
    # Clean boxed legend top-right above 100% line
    ctx.save()
    set_rgb(ctx, 1.0, 1.0, 1.0, 0.94)
    ctx.rectangle(ax + aw - 270, ay + 6, 262, 76); ctx.fill()
    set_rgb(ctx, 0.78, 0.82, 0.88); ctx.set_line_width(0.9)
    ctx.rectangle(ax + aw - 270, ay + 6, 262, 76); ctx.stroke()
    ctx.restore()
    for bi, (blbl, _u, col) in enumerate(bars):
        ly = ay + 18 + bi * 17
        ctx.set_source_rgba(*col)
        ctx.rectangle(ax + aw - 260, ly - 5, 14, 10); ctx.fill()
        draw_text(ctx, ax + aw - 240, ly, blbl, size=10.0, valign="middle")

    # --- PANEL B (Top-Right): 4 K Stage Load vs Chain Count (56..82) & 1K Comparison ---
    bx, by, bw, bh = 975, 105, 790, 420
    draw_panel_box(ctx, bx, by, bw, bh, "B. 4 K Yükü vs Okuma Zinciri Sayısı (NL 110–163) & 1 K Sıcak-Okuma Karşılaştırması")
    nls = [163, 160, 126, 110]
    chains_x = [th20[f"NL{nl}_H2.1"]["lines"] for nl in nls]  # 56, 57, 72, 82
    x0_b, x1_b = 52.0, 86.0
    y0_b, y1_b = 0.0, 2.20

    def map_b2(ch, wv):
        return bx + (ch - x0_b) / (x1_b - x0_b) * bw, by + (y1_b - wv) / (y1_b - y0_b) * bh

    ctx.save()
    set_rgb(ctx, 0.88, 0.90, 0.93)
    ctx.set_line_width(0.8)
    for wv in (0.0, 0.5, 1.0, 1.5, 2.0):
        _, uy = map_b2(x0_b, wv)
        ctx.move_to(bx, uy); ctx.line_to(bx + bw, uy); ctx.stroke()
        draw_text(ctx, bx - 8, uy, f"{wv:.1f} W", size=10.5, align="right", valign="middle")
    for ch in (56, 60, 65, 70, 75, 80, 82):
        ux, _ = map_b2(ch, 0)
        ctx.move_to(ux, by); ctx.line_to(ux, by + bh); ctx.stroke()
        draw_text(ctx, ux, by + bh + 15, str(ch), size=10.5, align="center")
    # PT410 / PT415 / PT420 lines
    for cap_w, lbl, col in [
        (1.0, "PT410 (1,0 W @4,2 K)", (0.85, 0.18, 0.18, 0.9)),
        (1.5, "PT415 (1,5 W @4,2 K)", (0.85, 0.50, 0.12, 0.85)),
        (2.0, "PT420 (2,0 W @4,2 K)", (0.12, 0.55, 0.35, 0.85)),
    ]:
        ctx.set_dash([6, 4])
        ctx.set_source_rgba(*col)
        ctx.set_line_width(1.6)
        _, uy = map_b2(x0_b, cap_w)
        ctx.move_to(bx, uy); ctx.line_to(bx + bw, uy); ctx.stroke()
        draw_text(ctx, bx + 10, uy - 6, lbl, size=10.5, bold=True, color=col)
    ctx.restore()

    hemt_series = [
        (2.1, (0.12, 0.56, 0.42, 1.0), "HEMT 2,1 mW (Rebelo 2026 InP)"),
        (7.8, (0.16, 0.42, 0.78, 1.0), "HEMT 7,8 mW (tipik LNA)"),
        (10.5, (0.82, 0.22, 0.24, 1.0), "HEMT 10,5 mW (LNF-LNC4_8C nom.)"),
    ]
    for hemt, col, lbl in hemt_series:
        ctx.save()
        ctx.set_source_rgba(*col)
        ctx.set_line_width(2.8)
        for i, nl in enumerate(nls):
            ch = th20[f"NL{nl}_H{hemt}"]["lines"]
            wv = th20[f"NL{nl}_H{hemt}"]["total"]["4K_W"]
            ux, uy = map_b2(ch, wv)
            if i == 0:
                ctx.move_to(ux, uy)
            else:
                ctx.line_to(ux, uy)
        ctx.stroke()
        for nl in nls:
            ch = th20[f"NL{nl}_H{hemt}"]["lines"]
            wv = th20[f"NL{nl}_H{hemt}"]["total"]["4K_W"]
            ux, uy = map_b2(ch, wv)
            ctx.arc(ux, uy, 4.5, 0, 2 * math.pi); ctx.fill()
            if nl != 160:  # avoid colliding with NL=163 right next to it (56 vs 57 lines)
                draw_text(ctx, ux, uy - 10, f"{wv:.2f}W", size=9.5, bold=True, color=col, align="center")
        ctx.restore()

    # Compact HEMT curve legend bottom-right of Panel B
    ctx.save()
    set_rgb(ctx, 1.0, 1.0, 1.0, 0.94)
    ctx.rectangle(bx + bw - 255, by + bh - 68, 245, 58); ctx.fill()
    set_rgb(ctx, 0.76, 0.80, 0.86); ctx.set_line_width(0.9)
    ctx.rectangle(bx + bw - 255, by + bh - 68, 245, 58); ctx.stroke()
    ctx.restore()
    for idx, (_h, col, lbl) in enumerate(hemt_series):
        ly = by + bh - 55 + idx * 17
        ctx.save()
        ctx.set_source_rgba(*col); ctx.set_line_width(2.8)
        ctx.move_to(bx + bw - 245, ly); ctx.line_to(bx + bw - 222, ly); ctx.stroke()
        ctx.restore()
        draw_text(ctx, bx + bw - 216, ly, lbl, size=9.8, valign="middle")

    # Info callout box comparing 20 mK vs 1 K at NL=160, 7.8 mW
    c20 = th20["NL160_H7.8"]["total"]
    c1k = th1k["NL160_H7.8"]["total"]
    ctx.save()
    set_rgb(ctx, 0.94, 0.96, 0.99, 0.96)
    ctx.rectangle(bx + bw - 355, by + 52, 342, 124)
    ctx.fill()
    set_rgb(ctx, 0.65, 0.72, 0.85)
    ctx.set_line_width(1.1)
    ctx.rectangle(bx + bw - 355, by + 52, 342, 124); ctx.stroke()
    ctx.restore()
    tx = bx + bw - 344
    draw_text(ctx, tx, by + 72, "NL=160 (57 hat), HEMT=7,8 mW (Sistem Dahil):", size=10.8, bold=True)
    draw_text(ctx, tx, by + 92, f"• Baz 20 mK (S6.8=D): 4K={c20['4K_W']:.2f} W, MXC={c20['MXC_uW']:.2f} µW (<19)", size=10.2, color=(0.10, 0.34, 0.68, 1.0))
    draw_text(ctx, tx, by + 110, f"• 1 K Alternatif (S6.8=C): 4K={c1k['4K_W']:.2f} W, 1K={c1k['stage1K_mW']:.1f} mW (<100)", size=10.2, color=(0.10, 0.52, 0.34, 1.0))
    draw_text(ctx, tx, by + 130, f"• RF SNR=10 süresi: {snr20['tau_for_SNR10_ms']:.3f} ms (20mK) / {snr1k['tau_for_SNR10_ms']:.3f} ms (1,5K)", size=10.0)
    draw_text(ctx, tx, by + 148, f"• 200-nokta tarama: {snr20['sweep_200pt_SNR10_ms']:.1f} ms / {snr1k['sweep_200pt_SNR10_ms']:.1f} ms << 1445 ms", size=10.0)
    draw_text(ctx, tx, by + 166, "  (Okuma -100 dBm/ton'da RF foton sınırlı değildir)", size=9.8, bold=True, color=(0.25, 0.30, 0.38, 1.0))

    draw_text(ctx, bx + bw / 2, by + bh + 32, "Okuma Zinciri Sayısı (ceil(9000 / NL)) — [NL=163 -> 56, NL=110 -> 82]", size=11.5, bold=True, align="center")
    draw_text(ctx, bx - 48, by + bh / 2, "4 K Toplam Yük (W)", size=12.0, bold=True, align="center", angle=-math.pi / 2)

    # --- PANEL C (Bottom-Left): Risk R8 Valley Interference Yield vs Gate Tunability G ---
    cx, cy, cw, ch = 82, 598, 795, 415
    draw_panel_box(ctx, cx, cy, cw, ch, "C. Risk R8: Faz-Duyarlı Silikon Vadi Girişimi (cos(k0·R)) & Dar tc Penceresi Verimi")
    g_list = [1, 3, 10, 30, 100]
    g_logs = [math.log10(g) for g in g_list]

    def map_c2(gval, pval):
        ux = cx + (math.log10(gval) / 2.0) * (cw - 30) + 15
        uy = cy + (1.05 - pval) / 0.85 * ch
        return ux, uy

    ctx.save()
    set_rgb(ctx, 0.88, 0.90, 0.93)
    ctx.set_line_width(0.8)
    for pv in (0.2, 0.4, 0.6, 0.8, 1.0):
        _, uy = map_c2(1, pv)
        ctx.move_to(cx, uy); ctx.line_to(cx + cw, uy); ctx.stroke()
        draw_text(ctx, cx - 8, uy, f"{pv:.1f}", size=10.5, align="right", valign="middle")
    for gv in g_list:
        ux, _ = map_c2(gv, 0.2)
        ctx.move_to(ux, cy); ctx.line_to(ux, cy + ch); ctx.stroke()
        draw_text(ctx, ux, cy + ch + 16, f"G = {gv}×", size=11.0, bold=True, align="center")
    # p_crit horizontal red line
    p_crit = be["p_crit_golden_cost_parity"]
    ctx.set_dash([6, 4])
    set_rgb(ctx, 0.85, 0.16, 0.16, 0.95)
    ctx.set_line_width(1.8)
    _, uy_pc = map_c2(1, p_crit)
    ctx.move_to(cx, uy_pc); ctx.line_to(cx + cw, uy_pc); ctx.stroke()
    ctx.restore()

    w4, w2, w1 = data["r8_sweep_W4"], data["r8_sweep_W2"], data["r8_sweep_W1"]
    curves_r8 = [
        ("W4 (Exp118 4 onluk) + V2 Koiller 6-vadi", w4["V2_koiller_6valley"], (0.35, 0.38, 0.44, 0.85), [5, 3], 2.0),
        ("W2 (2 onluk, 100M-10G) — Vadisiz", w2["none"], (0.12, 0.62, 0.42, 0.85), [4, 3], 2.0),
        ("W2 (2 onluk, 100M-10G) + V1 Arayüz 2-vadi", w2["V1_interface_2valley"], (0.14, 0.42, 0.82, 1.0), [], 2.6),
        ("W2 (2 onluk, 100M-10G) + V2 Koiller 6-vadi", w2["V2_koiller_6valley"], (0.55, 0.20, 0.72, 1.0), [], 2.8),
        ("W1 (Dar 1 onluk, 316M-3,16G) + V1 2-vadi", w1["V1_interface_2valley"], (0.92, 0.52, 0.10, 1.0), [], 2.4),
        ("W1 (Dar 1 onluk, 316M-3,16G) + V2 Koiller 6-vadi", w1["V2_koiller_6valley"], (0.82, 0.14, 0.22, 1.0), [], 2.8),
    ]
    for lbl, mdict, col, dash, lw in curves_r8:
        ctx.save()
        ctx.set_source_rgba(*col)
        ctx.set_line_width(lw)
        if dash:
            ctx.set_dash(dash)
        for i, gv in enumerate(g_list):
            pv = mdict[f"G{gv}"]["p_yield"]
            ux, uy = map_c2(gv, pv)
            if i == 0:
                ctx.move_to(ux, uy)
            else:
                ctx.line_to(ux, uy)
        ctx.stroke()
        ctx.set_dash([])
        for gv in g_list:
            pv = mdict[f"G{gv}"]["p_yield"]
            ux, uy = map_c2(gv, pv)
            ctx.arc(ux, uy, 4.0, 0, 2 * math.pi); ctx.fill()
        ctx.restore()

    draw_text(ctx, cx + cw - 10, uy_pc - 7, f"Maliyet başa-baş sınırı p_crit = {p_crit:.3f} (altında 1K avantajı biter)",
              size=10.5, bold=True, color=(0.82, 0.14, 0.14, 1.0), align="right")
    draw_text(ctx, cx + cw / 2, cy + ch + 35, "Kapı Ayarlanabilirlik Faktörü G (House vd. 2015 çapası: G <= 100×)", size=11.5, bold=True, align="center")
    draw_text(ctx, cx - 46, cy + ch / 2, "Kullanılabilir Bağlaşım Verimi p", size=12.0, bold=True, align="center", angle=-math.pi / 2)

    # Legend bottom-right inside panel C
    ctx.save()
    set_rgb(ctx, 1.0, 1.0, 1.0, 0.92)
    ctx.rectangle(cx + cw - 335, cy + ch - 122, 326, 114)
    ctx.fill()
    set_rgb(ctx, 0.76, 0.80, 0.86)
    ctx.set_line_width(0.9)
    ctx.rectangle(cx + cw - 335, cy + ch - 122, 326, 114); ctx.stroke()
    ctx.restore()
    for idx, (lbl, _m, col, dash, _lw) in enumerate(curves_r8):
        ly = cy + ch - 109 + idx * 18
        ctx.save()
        ctx.set_source_rgba(*col)
        ctx.set_line_width(2.4)
        if dash:
            ctx.set_dash(dash)
        ctx.move_to(cx + cw - 325, ly); ctx.line_to(cx + cw - 300, ly); ctx.stroke()
        ctx.restore()
        draw_text(ctx, cx + cw - 294, ly, lbl, size=9.6, valign="middle")

    # --- PANEL D (Bottom-Right): 1 K Golden Fraction vs Ancilla Yield p & Break-Even ---
    dx, dy, dw, dh = 975, 598, 790, 415
    draw_panel_box(ctx, dx, dy, dw, dh, "D. 1 K Alternatifi (S6.8=C) Altın Oranı vs Yardımcı Verimi p — Baz 20 mK DR (0,5215) Karşılaştırması")
    p_lo, p_hi = 0.28, 1.02
    f_lo, f_hi = 0.42, 0.62

    def map_d2(pv, fv):
        return dx + (pv - p_lo) / (p_hi - p_lo) * dw, dy + (f_hi - fv) / (f_hi - f_lo) * dh

    ctx.save()
    set_rgb(ctx, 0.88, 0.90, 0.93)
    ctx.set_line_width(0.8)
    for fv in (0.44, 0.48, 0.52, 0.56, 0.60):
        _, uy = map_d2(p_lo, fv)
        ctx.move_to(dx, uy); ctx.line_to(dx + dw, uy); ctx.stroke()
        draw_text(ctx, dx - 8, uy, f"{fv:.2f}", size=10.5, align="right", valign="middle")
    for pv in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        ux, _ = map_d2(pv, f_lo)
        ctx.move_to(ux, dy); ctx.line_to(ux, dy + dh); ctx.stroke()
        draw_text(ctx, ux, dy + dh + 16, f"{pv:.1f}", size=10.5, align="center")

    # 20 mK DR baseline line (golden = 0.5215)
    f_dr = be["DR_D_golden_frac"]
    ctx.set_dash([6, 4])
    set_rgb(ctx, 0.12, 0.30, 0.72, 0.95)
    ctx.set_line_width(2.0)
    _, uy_dr = map_d2(p_lo, f_dr)
    ctx.move_to(dx, uy_dr); ctx.line_to(dx + dw, uy_dr); ctx.stroke()

    # Vertical parity line p_crit_frac = 0.481
    p_cf = be["p_crit_golden_frac_parity"]
    ux_cf, _ = map_d2(p_cf, f_lo)
    set_rgb(ctx, 0.85, 0.16, 0.16, 0.85)
    ctx.set_line_width(1.6)
    ctx.move_to(ux_cf, dy); ctx.line_to(ux_cf, dy + dh); ctx.stroke()
    ctx.restore()

    # Smooth oversampling curve from p=0.30 to 1.00
    chains_g = be["chains_golden_base"]
    chains_r = math.ceil(10000 / be["nl"])
    cc = be["chain_class"]
    g_c0, r_c0 = 2615.6171756283857, 5841.25
    ctx.save()
    set_rgb(ctx, 0.10, 0.58, 0.36, 1.0)
    ctx.set_line_width(3.0)
    for i in range(71):
        pv = 0.30 + i * 0.01
        u = 1.0 / pv - 1.0
        fv = (g_c0 + chains_g * u * cc) / (r_c0 + chains_r * u * cc)
        ux, uy = map_d2(pv, max(f_lo, min(f_hi, fv)))
        if i == 0:
            ctx.move_to(ux, uy)
        else:
            ctx.line_to(ux, uy)
    ctx.stroke()
    ctx.restore()

    # Annotate key operating points on the curve
    pts_ann = [
        (w2["V2_koiller_6valley"]["G10"]["p_yield"], "W2/G10 Koiller\n(p=0,933)", (0.55, 0.20, 0.72, 1.0), -18, -32),
        (w1["V2_koiller_6valley"]["G3"]["p_yield"], "W1/G3 Dar\n(p=0,611)", (0.85, 0.45, 0.08, 1.0), 8, -28),
        (w1["V2_koiller_6valley"]["G1"]["p_yield"], "W1/G1 Ayarsız\n(p=0,334)", (0.82, 0.14, 0.22, 1.0), 10, 12),
    ]
    for pv, lbl, col, ox, oy in pts_ann:
        u = 1.0 / pv - 1.0
        fv = (g_c0 + chains_g * u * cc) / (r_c0 + chains_r * u * cc)
        ux, uy = map_d2(pv, fv)
        ctx.save()
        ctx.set_source_rgba(*col)
        ctx.arc(ux, uy, 6.0, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        for li, line in enumerate(lbl.split("\n")):
            draw_text(ctx, ux + ox, uy + oy + li * 13, line, size=10.0, bold=True, color=col)

    draw_text(ctx, dx + dw - 10, uy_dr - 8, f"Baz 20 mK Seyreltme (S6.8=D, Exp121): altın oran = {f_dr:.4f}",
              size=10.8, bold=True, color=(0.12, 0.30, 0.72, 1.0), align="right")
    draw_text(ctx, ux_cf + 8, dy + 22, f"Oran eşitliği p_crit = {p_cf:.3f}",
              size=10.2, bold=True, color=(0.82, 0.14, 0.14, 1.0))
    draw_text(ctx, ux_cf + 8, dy + 37, f"(Altın maliyet eşitliği p = {be['p_crit_golden_cost_parity']:.3f})",
              size=10.0, color=(0.82, 0.14, 0.14, 1.0))
    draw_text(ctx, dx + dw / 2, dy + dh + 35, "Yardımcı-Nokta Tünel Bağlaşım Verimi p (Risk R8)", size=11.5, bold=True, align="center")
    draw_text(ctx, dx - 48, dy + dh / 2, "Altın Oran (NL=163, Merkez Zincir)", size=12.0, bold=True, align="center", angle=-math.pi / 2)

    surface.write_to_png(str(out_path))
    print("Wrote:", out_path)


def main():
    payload = json.loads((OUT / "plot_data_exp125.json").read_text(encoding="utf-8"))
    make_bfield_figure(payload, OUT / "fig_exp125_bfield_map.png")
    make_thermal_r8_figure(payload, OUT / "fig_exp125_thermal_snr.png")


if __name__ == "__main__":
    main()
