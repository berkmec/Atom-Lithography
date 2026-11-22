"""Executive 2-panel CAD preview (`preview_machine.png`) via PyCairo + Pillow.

Runs under `/usr/bin/python3 -B` (zero matplotlib/numpy dependency).
"""
from __future__ import annotations

from pathlib import Path

import cairo
from PIL import Image

import gen_drawings as gd
import params

OUT = Path(__file__).parent
PW, PH = 2000, 1020


def main() -> None:
    ver = gd.load_verification()
    ma = ver["master_assembly"]
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, PW, PH)
    ctx = cairo.Context(surf)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)

    ctx.set_source_rgb(*gd.BG_PAPER)
    ctx.rectangle(0, 0, PW, PH)
    ctx.fill()

    # Header bar
    ctx.set_source_rgb(*gd.NAVY_HDR)
    ctx.rectangle(0, 0, PW, 62)
    ctx.fill()
    gd._draw_text(
        ctx, 26, 32,
        f"ATOM LİTOGRAFİ MAKİNESİ — PARAMETRİK CAD ÖNİZLEME ({params.CAD_VERSION}, s=0,5 ALTIN ZARF)",
        17.0, bold=True, color=(1, 1, 1),
    )
    gd._draw_text(
        ctx, 26, 52,
        f"{ma['part_count']} Katı Parça (S1–S7) | Exp124 562,66 mm Kolon & Exp125 8-Bobin Kilitli | Kütle: {ma['total_mass_kg']:.1f} kg | 8/8 STL | 0 Çakışma",
        11.5, color=(0.86, 0.92, 0.98),
    )

    # Left panel: 3D Shaded Isometric (full assembly)
    gd.draw_iso_panel(
        ctx, (24, 80, 960, 916), params.PARTS,
        "3B GÖLGELİ İZOMETRİK MONTAJ (S1–S7, UHV & DR YARI-SAYDAM)",
        azim_deg=-58.0, elev_deg=22.0, show_beam=True, n_seg=22,
    )

    # Right panel: X-Z Full Core Cross-Section (Y=0 Cutaway)
    core_parts = {k: v for k, v in params.PARTS.items() if v["subsystem"] != "s7_electronics_rack_interconnect"}
    gd.draw_ortho_panel(
        ctx, (1012, 80, 964, 916), core_parts, "xz",
        "MERKEZ KESİT A–A (X–Z) — EXP124 562,7 mm KOLON, EXP125 8-BOBİN MIKNATIS & 20 mK DR",
        section_mode=True,
        callouts=[
            ("s1_duoplasmatron", "[S1.1] Duoplazmatron +5kV"),
            ("s1_wien_filter", "[S1.2] Wien 0,45T h=150"),
            ("s1_energy_filter", "[S1.5] HDA ΔE=0,453eV"),
            ("s6_dr_flange_50k", "[S6.8] 50K/4K/Still/MXC"),
            ("s6_coil_s_upper", "[S6.3] 8-Bobin Ø150 Bore"),
            ("s2_aperture_plate", "[S2] Arch-B WD=0,25mm"),
            ("s3_silicon_wafer", "[S3] Yonga+100K LTC6268"),
            ("s6_mxc_cold_finger", "[S6.2] 20mK Parmak"),
            ("s4_piezo_fine_6dof", "[S4.3] 6-DOF Piezo"),
            ("s6_nbtin_resonator_carrier", "[S6.6] NbTiN z=−155 22µT"),
            ("s4_granite_base", "[S4.1] Granit & Aktif"),
        ],
        show_beam=True,
    )

    out_png = OUT / "preview_machine.png"
    surf.write_to_png(str(out_png))
    with Image.open(out_png) as im:
        assert im.size == (PW, PH)
    print(f"PREVIEW_DONE {out_png.name} ({PW}x{PH}, {out_png.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
