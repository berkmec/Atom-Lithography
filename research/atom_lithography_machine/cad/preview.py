"""Executive 2-panel CAD preview (`preview_machine.png`) via PyCairo + Pillow.

Runs under `/usr/bin/python3 -B` (zero matplotlib/numpy dependency).
"""
from __future__ import annotations

from pathlib import Path

import cairo
from PIL import Image

import gen_drawings as gd
import params

OUT = Path(__file__).resolve().parent
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
        f"{ma['part_count']} Katı Parça (S1–S7) | Exp124..140 + Option-Q (S1.6/S9.1 +9,2 kg) + Option-HPC (S9.HPC +64,0 kg) | Kütle: {ma['total_mass_kg']:.1f} kg | 8/8 STL | 0 Çakışma",
        10.8, color=(0.86, 0.92, 0.98),
    )

    # Left panel: 3D Shaded Isometric (full assembly)
    gd.draw_iso_panel(
        ctx, (24, 80, 960, 916), params.PARTS,
        "3B GÖLGELİ İZOMETRİK MONTAJ v6.0 (S1–S7 + OPTION-Q & OPTION-HPC, UHV & DR YARI-SAYDAM)",
        azim_deg=-58.0, elev_deg=22.0, show_beam=True, n_seg=22,
    )

    # Right panel: X-Z Full Core Cross-Section (Y=0 Cutaway)
    core_parts = {k: v for k, v in params.PARTS.items() if v["subsystem"] != "s7_electronics_rack_interconnect"}
    gd.draw_ortho_panel(
        ctx, (1012, 80, 964, 916), core_parts, "xz",
        "MERKEZ KESİT A–A (X–Z) — v6.0: S1.6 + S5.6 MBE + S6.5 MUX + S9.1 OPTION-Q qRAM",
        section_mode=True,
        callouts=[
            ("s1_duoplasmatron", "[S1+S1.6] Kolon+Çok-Tür"),
            ("s6_pt420_remote_valve_box", "[S6.1] PT420 Uzak Valf"),
            ("s5_mbe_source_body", "[S5.6] ²⁸Si MBE (22,4kg)"),
            ("s6_s91_ovc_feedthrough", "[S9.1] −X OVC Fiber/RF"),
            ("s6_m4_crossbar_4k_pcb", "[S6.6] 4K M4 968-Kapı"),
            ("s6_s65_hemt_bank_32ch", "[S6.5] 4K 32× HEMT"),
            ("s6_coil_s_upper", "[S6.3] 8-Bobin Ø150 Bore"),
            ("s2_aperture_plate", "[S2] Arch-B WD=0,25mm"),
            ("s6_ovc_bellows_cf63", "[S6.2] CF63 Körük 2kN/m"),
            ("s6_s65_twpa_purcell_pack", "[S6.5] 20mK TWPA/Purcell"),
            ("s6_s91_qram_bridge_20mk", "[S9.1] 20mK qRAM (8,5mm)"),
            ("s6_nbtin_resonator_carrier", "[S6.6] NbTiN z=−155 22µT"),
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
