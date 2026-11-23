"""Single-source parametric CAD specification (mm) — Atom Lithography Machine v4.0.

FULLY LOCKED to:
- Exp124 (562.66 mm 10->5 keV decelerating ion column + Arch-B retarding mini-lens + HDA-HiRes dE=0.453 eV)
- Exp125 (8-coil active-bucking 1.5 T / 22.3 uT cryo-magnet + Nb RRR>300 Meissner cup + Cryoperm-10 + 20 mK DR)
- Exp127 (100 K LTC6268 IBIC CSA frontend, ENC=24.1 e-, eta=0.99936)
- Exp130 (S5.5 808 nm qCW ms-flash anneal head 84x88x84 mm + dichroic 10 us pyrometer + safety shutter, Ø44 mm CA)
- Exp131 (M4 cavity-QED 3 kOhm NbTiN bus L_res=300 um, B_M4=0.1785 T, dz_cap*=8±1 nm 28Si cap, 4K 968-gate SKY130 crossbar)
- Exp133 (PT420 500 mm remote rotary valve + 600 mm flex He line + CF63 edge-welded bellows k=2000 N/m + 4x OFHC Cu braids k=52.7 N/m)

Coordinate Reference:
- Floor: z = 0.0 mm
- Wafer active top plane (z_loc = 0.0 mm): z_wafer = 500.00 mm
- Exp124 column: z = 500.25 -> 1062.66 mm (height = 562.66 mm, OD_max = 110.0 mm, mass = 25.92 kg)
- Exp125 8-coil magnet: z = 316.0 -> 612.0 mm (z_loc = -184 -> +112 mm, bore Ø150 mm,
  split gap 36 mm z=[482, 518], former OD Ø352 mm, in-vacuum inside s=0.5 UHV vessel)
- Exp125 NbTiN resonator disk: z = 345.0 mm (z_loc = -155.0 mm, Ø50 mm, |B|=22.3 uT)

Status: Concept / preliminary engineering parametric model (no_lab_measurement=true).
"""
from __future__ import annotations

import math

CAD_VERSION = "4.0-exp130-exp131-exp133-locked"
UNITS = "mm"
GOLDEN_SCALE_S = 0.5
GENERAL_TOLERANCE_STD = "ISO 2768-mK"
NO_LAB_MEASUREMENT = True

Z_WAFER = 500.0  # Global Z (mm) of wafer top surface (Exp125 z_loc = 0.0)

# ---------------------------------------------------------------------------
# Locked physics/design anchor dictionary (Exp80/84/124/125/127)
# ---------------------------------------------------------------------------
DESIGN_SPECS = {
    "envelope_scale_s": GOLDEN_SCALE_S,
    "z_wafer_mm": Z_WAFER,
    # Exp124 locked ion-column & Arch-B mini-lens specs
    "exp124_synced": True,
    "column_total_height_mm": 562.66,      # z=500.00 -> 1062.66 mm
    "column_max_od_mm": 110.0,
    "column_est_mass_kg": 25.92,
    "working_distance_mm": 0.250,          # Arch-B retarding immersion mini-lens WD
    "lens_arch": "Arch-B (0.50 mm pitch, D=0.30 mm, E_gap=10.60 MV/m, Cc=2.660 mm, Cs=10.786 mm)",
    "hv_grounding": "Wafer/Cryo/IBIC 0 V; üst kolon gömleği -5,0 kV; kaynak anodu +5,0 kV",
    "ion_extract_keV": 10.0,
    "ion_landing_keV": 5.0,
    "energy_filter_type": "HDA-HiRes (R0=40 mm, E_pass=100 eV, slit=0.35 mm)",
    "energy_filter_dE_eV": 0.453,          # Exp124 HDA-HiRes FWHM
    "spot_sigma_nm": 1.428,                # ArchB_HiRes_Ti0p25_10ms <= 1.50 nm
    "total_sigma_nm": 3.674,               # <= 3.80 nm Liouville-consistent
    "write_field_mm": 16.0,                # Active Arch-B 32x32 @ 0.50 mm pitch = 16.0x16.0 mm
    "write_field_diagonal_mm": round(16.0 * math.sqrt(2.0), 3),  # 22.627 mm
    "beamlet_pitch_mm": 0.50,              # Co-pitched S2.1 aperture + S2.2 blanker + S2.3 Arch-B
    "beamlet_pitch_um": 500.0,
    "beamlet_array_grid": "32x32",
    "beamlet_count": 1024,                 # 32x32 = 1,024 beamlets
    "blanker_tile_count": 16,              # 16 x 64-ch SKY130 tiles = 1,024 ch
    "column_beam_bore_mm": 28.0,           # S1.6 & S2.1 bore Ø28.0 mm -> 2.686 mm radial clearance to 22.627 mm diag
    # Exp125 locked 8-coil cryo-magnet, Meissner cup & DR specs
    "exp125_synced": True,
    "magnet_coil_count": 8,                # M/S/A/B upper & lower
    "magnet_clear_bore_mm": 150.0,         # Exp125 r_bore = 75.0 mm
    "magnet_split_gap_mm": 36.0,           # z_loc = [-18, +18] -> z = [482, 518]
    "magnet_former_od_mm": 352.0,          # Exp125 r_out = 176.0 mm
    "magnet_B_sample_T": 1.50,             # 17.8 ppm homogeneity over r<=2.3 mm
    "magnet_B_res_limit_T": 0.40,
    "magnet_B_res_shielded_uT": 22.3,      # Exp125 shielded NbTiN disk max |B|
    "resonator_plane_dz_mm": -155.0,       # z_loc = -155.0 ± 3.0 mm -> z = 345.0 mm
    "resonator_disk_od_mm": 50.0,          # r = 25.0 mm
    "nb_meissner_r_mm": (32.0, 34.5),      # z_loc = [-174, -136], chimney r=8, h=11
    "cryoperm_r_mm": (39.0, 41.0),         # z_loc = [-180, -124]
    "dr_mxc_temp_mK": 20.0,                # S6.8 dilution refrigerator MXC
    "readout_chains_band": (56, 82),       # NL=110-160, Ql=800-1200
    "readout_NL_band": (110, 160),
    # Exp127 locked IBIC frontend specs
    "exp127_synced": True,
    "ibic_csa_ic": "LTC6268 @ 100 K (1,2 µs / 1 GΩ, ENC=24,1 e⁻, η=0,99936)",
    # Exp130 locked S5.5 ms-flash annealing optical head specs
    "exp130_synced": True,
    "flash_laser_wavelength_nm": 808.0,
    "flash_pulse_ms": 1.0,
    "flash_fluence_J_cm2": 41.15,
    "flash_window_ca_mm": 44.0,            # CF63 sapphire Ø50x8 mm, clear aperture Ø44 mm
    "flash_beam_od_mm": 36.0,              # 4.0 mm radial margin to Ø44 mm duct
    "flash_pyrometer_dt_us": 10.0,         # 2-color InGaAs/Si dichroic pyrometer
    "flash_sigma_anneal_nm": 0.328,        # Exp130 f_act=99.98%, sigma_iso=0.0314 nm
    # Exp131 locked M4 scalable cavity-QED bus & 4K crossbar specs
    "exp131_synced": True,
    "m4_epi_cap_nm": 8.0,                  # Optimal 28Si epi cap Δz_cap* = 8 ± 1 nm
    "m4_bus_impedance_ohm": 3000.0,        # 3 kOhm high-Z NbTiN resonator (t=9 nm, w=100 nm)
    "m4_bus_L_res_um": 300.0,              # L_res = 300 um (0.300 mm) @ f_r = 5.0 GHz
    "m4_B_field_T": 0.1785,                # 40.5% below 0.30 T NbTiN limit (M4 mode)
    "m4_crossbar_gates_4k": 968,           # L=11 surface code, SKY130 4K multiplexed crossbar
    # Exp133 locked PT420 mechanical decoupling & closed-loop control specs
    "exp133_synced": True,
    "pt420_remote_valve": True,
    "pt420_valve_offset_mm": 500.0,        # Decoupled floor valve box at x = -1150 mm
    "pt420_flex_he_length_mm": 600.0,      # Braided flexible He U-loop line
    "ovc_bellows_id_mm": 44.0,             # Edge-welded 316L CF63 bellows
    "ovc_bellows_od_mm": 68.0,
    "ovc_bellows_active_L_mm": 120.0,
    "ovc_bellows_k_N_m": 2000.0,           # <= 6281.6 N/m bound (3.14x safety)
    "ovc_bellows_k_max_N_m": 6281.6,
    "mxc_braid_count": 4,                  # 4x parallel S-loop OFHC Cu braids (2550xØ50 um, L=100 mm)
    "mxc_braid_k_N_m": 52.7,               # <= 4197.0 N/m bound (70x safety vs 60 N/m rating)
    "mxc_braid_k_max_N_m": 4197.0,
    "mxc_braid_dT_mK": 3.7,                # G_total(20 mK) = 0.675 mW/K @ 2.5 uW load
    "exp133_sigma_stage_nm": 0.102,
    "exp133_sigma_pointing_nm": 0.147,
    "exp133_sigma_thermal_nm": 0.028,
    "exp133_min_vc_grade": "VC-E",
    # Exp80 s=0.5 & Exp84 modal specs
    "wafer_diameter_mm": 50.0,
    "carrier_size_mm": 80.0,               # Exp80 BC1: >= 25 mm (diag 113.1 < 150 bore)
    "chamber_r_out_mm": 192.0,             # Compact s=0.5 UHV vessel enclosing Ø352 mm magnet
    "chamber_r_in_mm": 182.0,              # 6 mm radial vacuum clearance to Ø352 former
    "chamber_inner_height_mm": 335.0,      # z=[285, 620] -> V = 34.86 L (ratio 0.1294, within ±5% of 1/8)
    "chamber_ref_volume_L": 269.3916,
    "blanker_f1_fea_hz": 2591027.0,        # Exp84 CalculiX modal
    "blanker_f1_analytic_hz": 2679466.6,
}

# ---------------------------------------------------------------------------
# Engineering Materials Library (density in kg/m^3, RGB hex)
# ---------------------------------------------------------------------------
MATERIALS = {
    "ss316ln":         {"name": "316LN Paslanmaz Çelik (UHV)",         "density": 8000.0, "color": "#8FA3B5"},
    "ti6al4v":         {"name": "Ti-6Al-4V Titanyum Alaşımı",          "density": 4430.0, "color": "#7B8FA1"},
    "invar36":         {"name": "Invar-36 (Düşük CTE)",                "density": 8050.0, "color": "#64748B"},
    "zerodur":         {"name": "Zerodur Cam-Seramik",                 "density": 2530.0, "color": "#DDD5C4"},
    "granite":         {"name": "Siyah Optik Granit",                  "density": 2950.0, "color": "#474D56"},
    "honeycomb_steel": {"name": "Aktif Sönümleme Tablası (Çelik)",     "density": 2200.0, "color": "#6B7280"},
    "ofhc_cu":         {"name": "Altın Kaplı OFHC Bakır (Kriyo)",      "density": 8960.0, "color": "#D48844"},
    "al6061":          {"name": "Al-6061-T6 Alüminyum",                "density": 2700.0, "color": "#B6C6D4"},
    "si_mems":         {"name": "Tek-Kristal Silikon (MEMS/Yonga)",    "density": 2330.0, "color": "#2C4960"},
    "aln_ceramic":     {"name": "AlN Seramik Yonga Taşıyıcı",          "density": 3260.0, "color": "#C4D1CB"},
    "alumina":         {"name": "Al₂O₃ HV Seramik Yalıtkan",           "density": 3950.0, "color": "#EFECE2"},
    "vespel":          {"name": "Vespel SP-22 Termal İzolatör",        "density": 1430.0, "color": "#8F5C38"},
    "becu":            {"name": "Altın Kaplı BeCu Kontak",             "density": 8250.0, "color": "#C99A2E"},
    "nbti_coil":       {"name": "NbTi/Cu Süperiletken Bobin (4,2 K)",  "density": 7900.0, "color": "#6B4C9A"},
    "nbti_shim":       {"name": "NbTi/Cu Şim Bobini (4,2 K)",          "density": 7900.0, "color": "#583D87"},
    "nbti_shield":     {"name": "NbTi/Cu Aktif Kalkan Bobini",         "density": 7900.0, "color": "#805AD5"},
    "nbti_buck":       {"name": "NbTi/Cu Karşı-Sargı (Bucking) Bobin", "density": 7900.0, "color": "#9B59B6"},
    "nb_meissner":     {"name": "Nb RRR>300 Meissner Kabı",            "density": 8570.0, "color": "#3B5998"},
    "cryoperm10":      {"name": "Cryoperm-10 (4 K Tavlı Dış Kılıf)",   "density": 8700.0, "color": "#4A607A"},
    "nbtin_si":        {"name": "NbTiN / Si Rezonatör Diski",          "density": 2850.0, "color": "#2980B9"},
    "fr4_rogers":      {"name": "Rogers / Alümina Kriyo-RF PCB",       "density": 2400.0, "color": "#2E7D52"},
    "rack_steel":      {"name": "19\" Sunucu/Kontrol Modülü (Efektif)","density": 460.0,  "color": "#4E5D6C"},
    "rack_psu":        {"name": "19\" HV/Mıknatıs Güç Modülü",         "density": 680.0,  "color": "#42505E"},
    "rack_fpga":       {"name": "19\" FPGA/DSP Şasisi",                "density": 420.0,  "color": "#2E7D52"},
    "rack_awg":        {"name": "19\" AWG/RF Sentez Şasisi",           "density": 500.0,  "color": "#2980B9"},
    "rack_clock":      {"name": "19\" Rb Saat/Termometri",             "density": 380.0,  "color": "#B58900"},
    "rack_chassis":    {"name": "Yapısal Çelik Profil Şasi",           "density": 2400.0, "color": "#374151"},
    "sapphire":        {"name": "Optik Safir UHV Pencere",             "density": 3980.0, "color": "#7CC8F8"},
    "rubber_air":      {"name": "Hava Yaylı Pnömatik İzolatör",        "density": 1800.0, "color": "#3B3F46"},
    "iron_yoke":       {"name": "SmCo/FeCo Wien Manyetik Boyunduruk",  "density": 4840.0, "color": "#B58900"},
    "hda_mu_al":       {"name": "Mu-Metal / Al-Mo HDA Süzgeç Gövdesi", "density": 5880.0, "color": "#7A8FA6"},
    "col_cu_ss":       {"name": "316L/Cu/Mo İyon Kolonu (Efektif)",    "density": 8418.0, "color": "#8E9FAD"},
}

# ---------------------------------------------------------------------------
# Subsystem Metadata (S1..S7)
# ---------------------------------------------------------------------------
SUBSYSTEMS = {
    "s1_ion_source_column": {
        "code": "S1",
        "title_tr": "Exp124 İyon Kaynağı & 10→5 keV Yavaşlatmalı Kolon",
        "drawing_no": "ALM-400-S1",
        "explode_vec": (0.0, 0.0, 250.0),
        "notes": [
            "Exp124 kilitli kolon: toplam 562,66 mm (S1+S2), maks. OD=110 mm, 25,92 kg",
            "S1.1 Duoplazmatron (+5 kV, h=140, OD=90) + S1.4 Kondansör (h=45, OD=84)",
            "S1.2 Wien (h=150, OD=110, B=0,45 T) + S1.5 HDA-HiRes (h=95, R₀=40, ΔE=0,453 eV)",
            "S1.6 Transfer (h=65, OD=84, bore=Ø28 mm); HV: wafer 0 V, üst gömlek −5 kV, kaynak +5 kV",
        ],
    },
    "s2_mems_write_head": {
        "code": "S2",
        "title_tr": "Exp124 Arch-B Mini-Lens, Blanker & MEMS Yazma Kafası (32×32)",
        "drawing_no": "ALM-400-S2",
        "explode_vec": (0.0, 0.0, 120.0),
        "notes": [
            "Aktif Arch-B: 32×32=1.024 demetcik, eş-adımlı 0,50 mm (16,0×16,0 mm, köşegen 22,63 mm)",
            "S2.3 Arch-B yavaşlatıcı mini-lens: h=1,76, OD=60, WD=0,250 mm, E_gap=10,60 MV/m, C_c=2,660 mm",
            "S2.2 Eş-adımlı 0,50 mm SKY130/MEMS Blanker + stop (h=4,0, OD=60, Exp84 f₁=2,591 MHz)",
            "S2.1 Apertür/tutucu (h=24, Ø28/Ø100 → 2,69 mm marj) + S2.4 16× 64-ch karo halkası",
        ],
    },
    "s3_ibic_detector_assembly": {
        "code": "S3",
        "title_tr": "IBIC Yonga Algılama, 100 K CSA (Exp127) & M4 Veri Yolu (Exp131)",
        "drawing_no": "ALM-400-S3",
        "explode_vec": (0.0, 0.0, 48.0),
        "notes": [
            "Exp127: 100 K soğuk adada LTC6268 CSA (1,2 µs / 1 GΩ, ENC=24,1 e⁻, η=0,99936)",
            "S5.4 Ø50 mm ²⁸Si/²⁹Si yonga + 80×80 AlN taşıyıcı (Exp131 M4: Δz_cap*=8±1 nm ²⁸Si kaplama)",
            "Exp131 M4 çip-üstü 3 kΩ NbTiN veri yolu (L_res=300 µm, f_r=5 GHz, B_M4=0,1785 T)",
            "S3.1 BeCu/Au IBIC halka (Ø64/Ø78, 2 mm pay) & yan Faraday kalkanları (+X/−X açık)",
        ],
    },
    "s4_piezo_stage_interferometry": {
        "code": "S4",
        "title_tr": "6-DOF Piezo Kademe, Titreşim İzolasyonu & İnterferometri",
        "drawing_no": "ALM-400-S4",
        "explode_vec": (0.0, 0.0, -140.0),
        "notes": [
            "S4.1 Optik granit (900×700×120) + 4× 1,5 Hz hava yayı; S4.2 0,5–100 Hz aktif tabla (VC-E)",
            "Exp133 kapalı çevrim: σ_stage=0,102 nm, σ_pointing=0,147 nm, σ_thermal=0,028 nm (PM=55,2°)",
            "Invar tüp kaide (R=45..52 mm) Cryoperm (R=41) ile B-bobin (R=56) arasından 4 mm payla geçer",
            "S4.4/S4.5 Zerodur halka (R=104..132) + 3-eksen interferometre (t_fid≤300 s, ±10 mK HVAC)",
        ],
    },
    "s5_uhv_chamber_loadlock": {
        "code": "S5",
        "title_tr": "s=0,5 UHV Ana Oda (Ø384/Ø364), Pompalar, LL & Exp130 S5.5 Flaş",
        "drawing_no": "ALM-400-S5",
        "explode_vec": (220.0, 0.0, 0.0),
        "notes": [
            "S5.1 UHV oda: R_dış=192/R_iç=182 mm (Ø352 mıknatısa 6 mm pay), V_iç=34,86 L (Exp80 BC4)",
            "Exp130 S5.5 (+Y, CF63 Ø44 CA, Ø36 demet): 808 nm qCW 84×88×84 homojenleştirici (41,2 J/cm²)",
            "S5.5 dikroik 10 µs iki-renkli pirometre + MXC<1 K / UHV vana kilitli mekanik deklanşör",
            "S5.2 Mag-lev turbo (300 L/s) + İyon/TSP (−Y); S5.3 Titreşim-ayrık load-lock & kol (+X)",
        ],
    },
    "s6_cryo_dr_magnet_readout": {
        "code": "S6",
        "title_tr": "Exp125 8-Bobin, Exp131 M4 4K Anahtar & Exp133 PT420 Ayrıştırma",
        "drawing_no": "ALM-400-S6",
        "explode_vec": (-260.0, 0.0, 0.0),
        "notes": [
            "Exp125 8 bobin (Ø150 bore, 36 mm yarık, Ø352 OD, 1,50 T) + z=−155 NbTiN (22,3 µT) + Nb/Cryoperm",
            "Exp131 M4: 4 K kademesinde SKY130 968-kapılı çapraz-anahtar kartı (3 kΩ NbTiN, B_M4=0,1785 T)",
            "Exp133 OVC CF63 kenar-kaynaklı körük (Ø44/Ø68, L=120, k=2000 N/m) + 4× OFHC Cu örgü (52,7 N/m)",
            "Exp133 PT420 500 mm uzak döner valf kutusu (x=−1150) + 600 mm esnek He hattı (ΔT=3,7 mK)",
        ],
    },
    "s7_electronics_rack_interconnect": {
        "code": "S7",
        "title_tr": "19\" Kontrol, RF/AWG, FPGA Kabini & Kriyo/UHV Geçiş Paneli",
        "drawing_no": "ALM-400-S7",
        "explode_vec": (340.0, 0.0, 0.0),
        "notes": [
            "30U 19\" EMI korumalı kabin (500×600×1400 mm, transfer koluna 34 mm servis boşluğu)",
            "S7.1 GRAPE/CellISA GPU sunucu; S7.2 Çok-kanallı AWG & 56–82 RF/MW sentezi",
            "S7.3 FPGA sayım-kapısı / blanker denetleyici; S7.4 Rb saat + ±5 kV / 8-bobin PSU",
            "Yan duvar Kriyo/UHV/RF çok-kanallı yama paneli (S7.4)",
        ],
    },
}


def _polar_xy(r: float, deg: float) -> tuple[float, float]:
    rad = math.radians(deg)
    return (round(r * math.cos(rad), 3), round(r * math.sin(rad), 3))


def _build_parts() -> dict[str, dict]:
    p: dict[str, dict] = {}
    zw = Z_WAFER  # 500.00 mm

    def add(
        name: str,
        subsystem: str,
        bom_id: str,
        label_tr: str,
        shape: str,
        dims: tuple,
        center: tuple[float, float, float],
        material: str,
        tol_mm: float = 0.05,
        alpha: float = 1.0,
        cutaway_mode: str = "keep",
        mass_override_kg: float | None = None,
    ) -> None:
        rec = {
            "subsystem": subsystem,
            "bom_id": bom_id,
            "label_tr": label_tr,
            "shape": shape,
            "dims": dims,
            "center": tuple(round(float(v), 4) for v in center),
            "material": material,
            "tol_mm": float(tol_mm),
            "alpha": float(alpha),
            "cutaway_mode": cutaway_mode,
        }
        if mass_override_kg is not None:
            rec["mass_override_kg"] = float(mass_override_kg)
        p[name] = rec

    # ==================== S1: EXP124 LOCKED ION COLUMN (562.66 mm total w/ S2) ====================
    # Stage z_loc exact from exp124.json:
    # S1.6 transfer_lens:     z_loc = [39.66, 104.66]  (h=65,  OD=84,  bore=28, 2.60 kg)
    # S1.5 energy_filter_HDA: z_loc = [114.66, 209.66] (h=95,  OD=110, bore=16, 5.20 kg)
    # S1.2 wien_mass_filter:  z_loc = [217.66, 367.66] (h=150, OD=110, bore=12, 6.80 kg)
    # S1.4 condenser_lens:    z_loc = [373.66, 418.66] (h=45,  OD=84,  bore=20, 2.10 kg)
    # S1.1 duoplasmatron:     z_loc = [422.66, 562.66] (h=140, OD=90,  bore=0.1, 7.50 kg)
    add("s1_transfer_lens", "s1_ion_source_column", "S1.6",
        "Telecentric Transfer Lensi (Einzel, Ø28/Ø84)", "tube", (14.0, 42.0, 65.0, "z"), (0, 0, zw + 72.16),
        "col_cu_ss", 0.02, cutaway_mode="section", mass_override_kg=2.60)
    add("s1_hv_iso_16_15", "s1_ion_source_column", "S1.3",
        "HV Al₂O₃ Ara Yalıtkan (Transfer↔HDA, 10 mm)", "tube", (36.0, 41.0, 9.90, "z"), (0, 0, zw + 109.66),
        "alumina", 0.02, cutaway_mode="section")
    add("s1_energy_filter", "s1_ion_source_column", "S1.5",
        "HDA-HiRes Enerji Süzgeci (R₀=40, ΔE=0,453 eV)", "tube", (8.0, 55.0, 95.0, "z"), (0, 0, zw + 162.16),
        "hda_mu_al", 0.02, cutaway_mode="section", mass_override_kg=5.20)
    add("s1_hv_iso_15_12", "s1_ion_source_column", "S1.3",
        "HV Al₂O₃ Ara Yalıtkan (HDA↔Wien, 8 mm)", "tube", (46.0, 53.0, 7.90, "z"), (0, 0, zw + 213.66),
        "alumina", 0.02, cutaway_mode="section")
    add("s1_wien_filter", "s1_ion_source_column", "S1.2",
        "ExB Wien Kütle Filtresi (h=150, OD=110, 0,45 T)", "tube", (6.0, 55.0, 150.0, "z"), (0, 0, zw + 292.66),
        "iron_yoke", 0.02, cutaway_mode="section", mass_override_kg=6.80)
    add("s1_hv_iso_12_14", "s1_ion_source_column", "S1.3",
        "HV Al₂O₃ Ara Yalıtkan (Wien↔Kondansör, 6 mm)", "tube", (36.0, 41.0, 5.90, "z"), (0, 0, zw + 370.66),
        "alumina", 0.02, cutaway_mode="section")
    add("s1_condenser_lens", "s1_ion_source_column", "S1.4",
        "Çıkarım & Kondansör Einzel Lensi (10 keV)", "tube", (10.0, 42.0, 45.0, "z"), (0, 0, zw + 396.16),
        "col_cu_ss", 0.02, cutaway_mode="section", mass_override_kg=2.10)
    add("s1_hv_iso_14_11", "s1_ion_source_column", "S1.3",
        "HV Seramik Kırıcı (+5 kV↔−5 kV, 4 mm)", "tube", (36.0, 41.0, 3.90, "z"), (0, 0, zw + 420.66),
        "alumina", 0.02, cutaway_mode="section")
    add("s1_duoplasmatron", "s1_ion_source_column", "S1.1",
        "Duoplazmatron İyon Kaynağı (+5 kV, h=140, OD=90)", "cyl", (45.0, 140.0, "z"), (0, 0, zw + 492.66),
        "ss316ln", 0.05, cutaway_mode="section", mass_override_kg=7.50)
    add("s1_ph3_manifold", "s1_ion_source_column", "S1.1",
        "PH₃ Toksik Gaz Besleme Manifoldu", "box", (56.0, 48.0, 74.0), (0, -88.0, zw + 492.66),
        "ss316ln", 0.20)
    add("s1_ph3_feed_pipe", "s1_ion_source_column", "S1.1",
        "PH₃ Koaksiyel Besleme Borusu", "cyl", (7.0, 19.0, "y"), (0, -54.5, zw + 492.66),
        "ss316ln", 0.10)

    # ==================== S2: EXP124 LOCKED ARCH-B (32x32 @ 0.50 mm, 16x16 mm) ==============
    # S2.3 retarding_minilens: z_loc = [0.25, 2.01]   (h=1.76, OD=60, WD=0.250 mm, 0.20 kg)
    # S2.2 blanker_and_stop:   z_loc = [3.01, 7.01]   (h=4.00, OD=60, gap=1.00,    0.12 kg)
    # S2.1 aperture_and_frame: z_loc = [7.66, 31.66]  (h=24.0, OD=100, bore=28,    1.40 kg)
    add("s2_mini_lens_plate", "s2_mems_write_head", "S2.3",
        "Arch-B Yavaşlatıcı Mini-Lens (32×32, 0,50 mm)", "cyl", (30.0, 1.76, "z"), (0, 0, zw + 1.13),
        "si_mems", 0.005, mass_override_kg=0.20)
    add("s2_spacer_lower", "s2_mems_write_head", "S2.3",
        "Alt HV Al₂O₃ Ara Halkası (1,0 mm)", "tube", (24.0, 29.0, 0.96, "z"), (0, 0, zw + 2.51),
        "alumina", 0.005)
    add("s2_blanker_plate", "s2_mems_write_head", "S2.2",
        "Eş-Adımlı 0,50 mm Blanker + Stop (32×32, h=4)", "cyl", (30.0, 4.00, "z"), (0, 0, zw + 5.01),
        "si_mems", 0.005, mass_override_kg=0.12)
    add("s2_tile_carrier", "s2_mems_write_head", "S2.4",
        "16× 64-Kanallı SKY130 Karo Halkası (1.024 ch)", "tube", (32.0, 66.0, 4.00, "z"), (0, 0, zw + 5.01),
        "fr4_rogers", 0.02, cutaway_mode="section")
    add("s2_spacer_upper", "s2_mems_write_head", "S2.1",
        "Üst HV Al₂O₃ Ara Halkası (0,65 mm)", "tube", (24.0, 29.0, 0.61, "z"), (0, 0, zw + 7.335),
        "alumina", 0.005)
    add("s2_aperture_plate", "s2_mems_write_head", "S2.1",
        "MEMS Apertür & Tutucu (h=24, Ø28/Ø100)", "tube", (14.0, 50.0, 24.00, "z"), (0, 0, zw + 19.66),
        "invar36", 0.01, cutaway_mode="section", mass_override_kg=1.40)
    for idx, ang in enumerate((60.0, 180.0, 300.0), start=1):
        sx, sy = _polar_xy(36.0, ang)
        add(f"s2_mount_strut_{idx}", "s2_mems_write_head", "S2.5",
            f"Kinematik Kolon Bağlantı Dikmesi #{idx} (8 mm)", "cyl", (4.5, 7.90, "z"), (sx, sy, zw + 35.66),
            "ti6al4v", 0.01)

    # ==================== S3: IBIC DETECTOR & 100 K LTC6268 CSA (EXP127) ====================
    add("s3_wafer_carrier", "s3_ibic_detector_assembly", "S3.1",
        "AlN Yonga Taşıyıcı (80×80×5 mm, Exp80 BC1)", "box", (80.0, 80.0, 5.0), (0, 0, zw - 3.5),
        "aln_ceramic", 0.02)
    add("s3_silicon_wafer", "s3_ibic_detector_assembly", "S5.4",
        "Ø50 ²⁸Si/²⁹Si Yonga (0 V, M4 Δz_cap*=8±1 nm)", "cyl", (25.0, 1.0, "z"), (0, 0, zw - 0.5),
        "si_mems", 0.01)
    add("s3_ibic_contact_ring", "s3_ibic_detector_assembly", "S3.1",
        "BeCu/Au IBIC Kontak Halkası (Ø64/Ø78, WD paylı)", "tube", (32.0, 39.0, 2.0, "z"), (0, 0, zw),
        "becu", 0.02, cutaway_mode="section")
    add("s3_ibic_csa_pos", "s3_ibic_detector_assembly", "S3.2",
        "100 K LTC6268 CSA (+Y, ENC=24,1 e⁻, η=0,99936)", "box", (30.0, 8.0, 4.0), (0, 46.0, zw - 4.0),
        "fr4_rogers", 0.05)
    add("s3_ibic_csa_neg", "s3_ibic_detector_assembly", "S3.2",
        "100 K LTC6268 CSA (−Y, 1,2 µs / 1 GΩ, Exp127)", "box", (30.0, 8.0, 4.0), (0, -46.0, zw - 4.0),
        "fr4_rogers", 0.05)
    add("s3_hv_bias_shield_pos", "s3_ibic_detector_assembly", "S3.3",
        "HV Besleme & Faraday Koruma Kalkanı (+Y)", "box", (34.0, 3.0, 8.0), (0, 53.5, zw - 2.0),
        "becu", 0.05)
    add("s3_hv_bias_shield_neg", "s3_ibic_detector_assembly", "S3.3",
        "HV Besleme & Faraday Koruma Kalkanı (−Y)", "box", (34.0, 3.0, 8.0), (0, -53.5, zw - 2.0),
        "becu", 0.05)

    # ==================== S4: 6-DOF PIEZO STAGE, GRANITE & INTERFEROMETRY ===================
    for idx, (ix, iy) in enumerate(((-350, -250), (350, -250), (350, 250), (-350, 250)), start=1):
        add(f"s4_air_isolator_{idx}", "s4_piezo_stage_interferometry", "S4.1",
            f"Hava Yaylı Pnömatik İzolatör #{idx} (1–2 Hz)", "cyl", (52.0, 80.0, "z"), (ix, iy, 40.0),
            "rubber_air", 0.50)
    add("s4_granite_base", "s4_piezo_stage_interferometry", "S4.1",
        "Optik Granit Taban Bloğu (900×700×120)", "box", (900.0, 700.0, 120.0), (0, 0, 140.0),
        "granite", 0.05)
    add("s4_active_table", "s4_piezo_stage_interferometry", "S4.2",
        "Aktif Sönümleme Tablası (0,5–100 Hz)", "box", (820.0, 620.0, 60.0), (0, 0, 230.0),
        "honeycomb_steel", 0.05)
    # Coaxial Invar stage pedestal threading cleanly between Cryoperm (r=41) and B-coils (r=56)
    add("s4_stage_pedestal", "s4_piezo_stage_interferometry", "S4.3",
        "Invar Tüp Kademe Kaidesi (R=45..52 mm)", "tube", (45.0, 52.0, 138.0, "z"), (0, 0, 354.0),
        "invar36", 0.02, cutaway_mode="section")
    add("s4_piezo_coarse_xy", "s4_piezo_stage_interferometry", "S4.3",
        "Kaba Stick-Slip XY Piezo Kademe (96×96, 26 mm)", "box", (96.0, 96.0, 24.0), (0, 0, zw - 65.0),
        "ti6al4v", 0.01)
    add("s4_piezo_fine_6dof", "s4_piezo_stage_interferometry", "S4.3",
        "6-DOF İnce Piezo Kademe (PI PIMars, ≤0,5 nm)", "box", (90.0, 90.0, 24.0), (0, 0, zw - 41.0),
        "invar36", 0.005)
    for idx, ang in enumerate((45.0, 135.0, 225.0, 315.0), start=1):
        mx, my = _polar_xy(118.0, ang)
        add(f"s4_met_col_{idx}", "s4_piezo_stage_interferometry", "S4.5",
            f"Invar Metroloji Çerçeve Sütunu #{idx}", "cyl", (6.0, 73.0, "z"), (mx, my, 321.5),
            "invar36", 0.02)
    add("s4_metrology_frame", "s4_piezo_stage_interferometry", "S4.5",
        "Zerodur Metroloji Referans Halkası (Ø208/Ø264)", "tube", (104.0, 132.0, 18.0, "z"), (0, 0, 367.0),
        "zerodur", 0.005, cutaway_mode="section")
    add("s4_interferometer_x", "s4_piezo_stage_interferometry", "S4.4",
        "Lazer İnterferometre Başlığı (X Ekseni)", "box", (16.0, 14.0, 14.0), (94.0, 0, 367.0),
        "invar36", 0.01)
    add("s4_interferometer_y", "s4_piezo_stage_interferometry", "S4.4",
        "Lazer İnterferometre Başlığı (Y Ekseni)", "box", (14.0, 16.0, 14.0), (0, 94.0, 367.0),
        "invar36", 0.01)
    add("s4_interferometer_z", "s4_piezo_stage_interferometry", "S4.4",
        "Lazer İnterferometre Başlığı (Z Ekseni)", "box", (14.0, 16.0, 14.0), (0, -94.0, 367.0),
        "invar36", 0.01)
    add("s4_laser_head", "s4_piezo_stage_interferometry", "S4.4",
        "3-Eksen Stabilize Heterodin Lazer Ünitesi", "box", (110.0, 70.0, 55.0), (305.0, 235.0, 287.5),
        "al6061", 0.10)

    # ==================== S5: UHV CHAMBER (V=34.86 L, Exp80 BC4 PASS), PUMPS, LL, FLASH ====
    add("s5_chamber_bottom_flange", "s5_uhv_chamber_loadlock", "S5.1",
        "UHV Oda Taban Flanşı (CF400)", "cyl", (225.0, 25.0, "z"), (0, 0, 272.5),
        "ss316ln", 0.05, cutaway_mode="section")
    add("s5_chamber_wall_lower", "s5_uhv_chamber_loadlock", "S5.1",
        "UHV Ana Oda Alt Gövde (R=192/182)", "tube", (182.0, 192.0, 195.0, "z"), (0, 0, 382.5),
        "ss316ln", 0.05, alpha=0.28, cutaway_mode="section")
    for tag, d0, d1 in (("ne", 28.0, 62.0), ("nw", 118.0, 152.0),
                        ("sw", 208.0, 242.0), ("se", 298.0, 332.0)):
        add(f"s5_chamber_pillar_{tag}", "s5_uhv_chamber_loadlock", "S5.1",
            f"UHV Ekvatoryal Port Sütunu ({tag.upper()})", "arc_tube",
            (182.0, 192.0, 59.90, d0, d1), (0, 0, 510.0),
            "ss316ln", 0.05, alpha=0.45, cutaway_mode="hide_front" if tag in ("sw", "se") else "keep")
    add("s5_chamber_wall_upper", "s5_uhv_chamber_loadlock", "S5.1",
        "UHV Ana Oda Üst Gövde (V_iç=34,86 L)", "tube", (182.0, 192.0, 80.0, "z"), (0, 0, 580.0),
        "ss316ln", 0.05, alpha=0.28, cutaway_mode="section")
    add("s5_chamber_top_flange", "s5_uhv_chamber_loadlock", "S5.1",
        "UHV Oda Üst Flanşı (Ø128 Kolon Geçişi)", "tube", (64.0, 225.0, 25.0, "z"), (0, 0, 632.5),
        "ss316ln", 0.05, cutaway_mode="section")
    add("s5_loadlock_duct", "s5_uhv_chamber_loadlock", "S5.3",
        "Load-Lock Transfer Tüneli & Sürgülü Vana (+X)", "tube", (22.0, 28.0, 138.0, "x"), (261.0, 0, zw),
        "ss316ln", 0.10, cutaway_mode="section")
    add("s5_loadlock_chamber", "s5_uhv_chamber_loadlock", "S5.3",
        "UHV Yük Kilidi (Load-Lock) Odası", "box", (180.0, 180.0, 170.0), (420.0, 0, zw),
        "ss316ln", 0.10)
    add("s5_loadlock_stand", "s5_uhv_chamber_loadlock", "S5.3",
        "Titreşim-Ayrık Load-Lock Zemin Sehpası", "box", (40.0, 140.0, 415.0), (485.0, 0, 207.5),
        "rack_chassis", 0.50)
    add("s5_transfer_arm", "s5_uhv_chamber_loadlock", "S5.3",
        "Manyetik Yonga Transfer Kolu", "cyl", (15.0, 200.0, "x"), (610.0, 0, zw),
        "ss316ln", 0.10)
    add("s5_pump_duct", "s5_uhv_chamber_loadlock", "S5.2",
        "UHV Vakum Pompa Boğazı (−Y)", "tube", (24.0, 30.0, 198.0, "y"), (0, -291.0, zw),
        "ss316ln", 0.10)
    add("s5_pump_tee", "s5_uhv_chamber_loadlock", "S5.2",
        "UHV Pompa T-Manifoldu", "box", (80.0, 80.0, 80.0), (0, -430.0, zw),
        "ss316ln", 0.10)
    add("s5_turbo_pump", "s5_uhv_chamber_loadlock", "S5.2",
        "Mag-Lev Turbomoleküler Pompa (300 L/s)", "cyl", (56.0, 175.0, "z"), (0, -430.0, 372.5),
        "al6061", 0.20)
    add("s5_ion_tsp_pump", "s5_uhv_chamber_loadlock", "S5.2",
        "İyon + Titanyum Süblimasyon (TSP) Pompası", "cyl", (44.0, 135.0, "z"), (0, -430.0, 607.5),
        "ss316ln", 0.20)
    add("s5_pump_stand", "s5_uhv_chamber_loadlock", "S5.2",
        "Pompa İstasyonu Zemin Şasisi", "box", (120.0, 120.0, 285.0), (0, -430.0, 142.5),
        "rack_chassis", 0.50)
    add("s5_flash_anneal_duct", "s5_uhv_chamber_loadlock", "S5.5",
        "Flaş Tavlama Optik Port Boğazı (+Y, Ø44 CA)", "tube", (22.0, 27.0, 103.0, "y"), (0, 243.5, zw),
        "ss316ln", 0.10)
    add("s5_flash_window", "s5_uhv_chamber_loadlock", "S5.5",
        "CF63 Optik Safir Flaş Penceresi (Ø50×8, AR)", "cyl", (25.0, 8.0, "y"), (0, 299.0, zw),
        "sapphire", 0.05)
    add("s5_flash_safety_shutter", "s5_uhv_chamber_loadlock", "S5.5",
        "MXC<1 K & UHV Kilitli Mekanik Deklanşör", "box", (74.0, 20.0, 74.0), (0, 313.1, zw),
        "ss316ln", 0.10, mass_override_kg=0.78)
    add("s5_flash_anneal_head", "s5_uhv_chamber_loadlock", "S5.5",
        "808 nm qCW Homojenleştirici Kafa (84×88×84)", "box", (84.0, 88.0, 84.0), (0, 367.2, zw),
        "al6061", 0.10, mass_override_kg=1.85)
    add("s5_flash_dichroic_pyrometer", "s5_uhv_chamber_loadlock", "S5.5",
        "Dikroik & 10 µs İki-Renkli Pirometre Modülü", "box", (52.0, 56.0, 44.0), (0, 367.2, zw + 64.1),
        "al6061", 0.10, mass_override_kg=0.38)
    add("s5_flash_fiber_collimator", "s5_uhv_chamber_loadlock", "S5.5",
        "808 nm Fiber Demet Kolimatör Girişi", "cyl", (16.0, 36.0, "y"), (0, 429.3, zw),
        "ss316ln", 0.10, mass_override_kg=0.22)

    # ==================== S6: EXP125 LOCKED 8-COIL CRYO-MAGNET, SHIELDS & 20 mK DR ==========
    # Exact 8 coils relative to z_loc = 0 at zw = 500.0 mm
    add("s6_coil_m_upper", "s6_cryo_dr_magnet_readout", "S6.3",
        "Exp125 Ana Bobin M_upper (1600T, 40,2 A)", "tube", (78.0, 112.0, 54.0, "z"), (0, 0, zw + 45.0),
        "nbti_coil", 0.05, alpha=0.88, cutaway_mode="section")
    add("s6_coil_m_lower", "s6_cryo_dr_magnet_readout", "S6.3",
        "Exp125 Ana Bobin M_lower (1600T, 216,5 A)", "tube", (78.0, 112.0, 54.0, "z"), (0, 0, zw - 45.0),
        "nbti_coil", 0.05, alpha=0.88, cutaway_mode="section")
    add("s6_coil_s_upper", "s6_cryo_dr_magnet_readout", "S6.3",
        "Exp125 Şim Bobini S_upper (1100T, 255,9 A)", "tube", (78.0, 116.0, 36.0, "z"), (0, 0, zw + 94.0),
        "nbti_shim", 0.05, alpha=0.88, cutaway_mode="section")
    add("s6_coil_s_lower", "s6_cryo_dr_magnet_readout", "S6.3",
        "Exp125 Şim Bobini S_lower (1100T, −195,3 A)", "tube", (78.0, 116.0, 36.0, "z"), (0, 0, zw - 94.0),
        "nbti_shim", 0.05, alpha=0.88, cutaway_mode="section")
    add("s6_coil_a_upper", "s6_cryo_dr_magnet_readout", "S6.3",
        "Exp125 Aktif Kalkan A_upper (960T, −168,0 A)", "tube", (144.0, 168.0, 84.0, "z"), (0, 0, zw + 62.0),
        "nbti_shield", 0.05, alpha=0.82, cutaway_mode="section")
    add("s6_coil_a_lower", "s6_cryo_dr_magnet_readout", "S6.3",
        "Exp125 Aktif Kalkan A_lower (960T, −57,2 A)", "tube", (144.0, 168.0, 84.0, "z"), (0, 0, zw - 62.0),
        "nbti_shield", 0.05, alpha=0.82, cutaway_mode="section")
    add("s6_coil_b_upper", "s6_cryo_dr_magnet_readout", "S6.3",
        "Exp125 Karşı-Sargı B_upper (400T, 83,9 A)", "tube", (56.0, 82.0, 24.0, "z"), (0, 0, zw - 133.0),
        "nbti_buck", 0.05, alpha=0.90, cutaway_mode="section")
    add("s6_coil_b_lower", "s6_cryo_dr_magnet_readout", "S6.3",
        "Exp125 Karşı-Sargı B_lower (400T, 22,5 A)", "tube", (56.0, 82.0, 24.0, "z"), (0, 0, zw - 172.0),
        "nbti_buck", 0.05, alpha=0.90, cutaway_mode="section")

    # Outer Ø352 mm cryo-magnet former + Lorentz tie rods & floor feet
    add("s6_magnet_former_lower", "s6_cryo_dr_magnet_readout", "S6.3",
        "Kriyo-Mıknatıs Karkası Alt (OD=352 mm)", "tube", (169.0, 176.0, 84.0, "z"), (0, 0, zw - 62.0),
        "ti6al4v", 0.05, alpha=0.65, cutaway_mode="section")
    add("s6_magnet_former_upper", "s6_cryo_dr_magnet_readout", "S6.3",
        "Kriyo-Mıknatıs Karkası Üst (OD=352 mm)", "tube", (169.0, 176.0, 84.0, "z"), (0, 0, zw + 62.0),
        "ti6al4v", 0.05, alpha=0.65, cutaway_mode="section")
    for idx, ang in enumerate((45.0, 135.0, 225.0, 315.0), start=1):
        fx, fy = _polar_xy(156.0, ang)
        add(f"s6_magnet_foot_{idx}", "s6_cryo_dr_magnet_readout", "S6.3",
            f"Mıknatıs Taşıyıcı Titanyum Ayak #{idx}", "cyl", (9.0, 111.0, "z"), (fx, fy, 340.5),
            "ti6al4v", 0.10)
        tx, ty = _polar_xy(172.5, ang)
        add(f"s6_magnet_tie_rod_{idx}", "s6_cryo_dr_magnet_readout", "S6.3",
            f"36 mm Yarık Lorentz Gergi Çubuğu #{idx}", "cyl", (3.5, 39.90, "z"), (tx, ty, zw),
            "ti6al4v", 0.05)
        bx, by = _polar_xy(69.0, ang)
        add(f"s6_buck_foot_{idx}", "s6_cryo_dr_magnet_readout", "S6.3",
            f"B-Bobin Alt Destek Dikmesi #{idx}", "cyl", (4.5, 31.0, "z"), (bx, by, 300.5),
            "ti6al4v", 0.05)

    # Exp125 Resonator Quiet Zone at z_loc = -155.0 mm (z = 345.0 mm)
    add("s6_nbtin_resonator_carrier", "s6_cryo_dr_magnet_readout", "S6.6",
        "NbTiN Rezonatör Diski (Ø50, z=−155, 22,3 µT)", "cyl", (25.0, 6.0, "z"), (0, 0, zw - 155.0),
        "nbtin_si", 0.02)
    add("s6_meissner_cup_bot", "s6_cryo_dr_magnet_readout", "S6.3",
        "Nb RRR>300 Meissner Kabı Tabanı (R=34,5)", "cyl", (34.5, 2.5, "z"), (0, 0, zw - 172.75),
        "nb_meissner", 0.02, cutaway_mode="section")
    add("s6_meissner_cup_wall", "s6_cryo_dr_magnet_readout", "S6.3",
        "Nb RRR>300 Meissner Duvarı (R=32..34,5)", "tube", (32.0, 34.5, 32.90, "z"), (0, 0, zw - 155.0),
        "nb_meissner", 0.02, cutaway_mode="section")
    add("s6_meissner_cup_top", "s6_cryo_dr_magnet_readout", "S6.3",
        "Nb RRR>300 Meissner Kapağı (r=8 Baca Deliği)", "tube", (8.0, 34.5, 2.5, "z"), (0, 0, zw - 137.25),
        "nb_meissner", 0.02, cutaway_mode="section")
    add("s6_meissner_chimney", "s6_cryo_dr_magnet_readout", "S6.3",
        "Nb Meissner Koaksiyel Bacası (r=8, h=11 mm)", "tube", (6.0, 8.0, 10.90, "z"), (0, 0, zw - 130.5),
        "nb_meissner", 0.02, cutaway_mode="section")
    add("s6_cryoperm_sleeve", "s6_cryo_dr_magnet_readout", "S6.3",
        "Cryoperm-10 Dış Kılıf (R=39..41, z=−180..−124)", "tube", (39.0, 41.0, 56.0, "z"), (0, 0, zw - 152.0),
        "cryoperm10", 0.02, cutaway_mode="section")
    add("s6_res_mxc_post", "s6_cryo_dr_magnet_readout", "S6.2",
        "Rezonatör Kabı 20 mK Termal Destek Ayağı", "cyl", (12.0, 41.0, "z"), (0, 0, 305.5),
        "ofhc_cu", 0.05)

    # Local 20 mK Cold Island & Horizontal Cryo Bridge through 36 mm Magnet Split Gap
    for idx, (tx, ty) in enumerate(((-32, -32), (32, -32), (32, 32), (-32, 32)), start=1):
        add(f"s6_thermal_iso_{idx}", "s6_cryo_dr_magnet_readout", "S6.2",
            f"Vespel SP-22 Termal İzolasyon Dikmesi #{idx}", "cyl", (5.0, 15.0, "z"), (tx, ty, zw - 21.5),
            "vespel", 0.02)
    add("s6_mxc_cold_chuck", "s6_cryo_dr_magnet_readout", "S6.2",
        "20 mK MXC Lokal Soğuk Ada (OFHC Cu, Ø116)", "cyl", (58.0, 8.0, "z"), (0, 0, zw - 10.0),
        "ofhc_cu", 0.02)
    # Exp133 v4.0 Decoupled 20 mK Thermal Link: Ø12x397 mm DR OFHC busbar + 4x S-loop braids (L=100 mm, k=52.7 N/m)
    z_cryo = zw - 7.0  # 493.0 mm (coaxial inside 36 mm magnet split gap z=[482, 518])
    add("s6_mxc_cold_finger", "s6_cryo_dr_magnet_readout", "S6.2",
        "20 mK DR OFHC Bakır Bara (Ø12×397 mm, Exp133)", "cyl", (6.0, 397.0, "x"), (-356.5, 0, z_cryo),
        "ofhc_cu", 0.05)
    for b_idx, (by_o, bz_o) in enumerate(((-3.2, -2.0), (3.2, -2.0), (-3.2, 0.2), (3.2, 0.2)), start=1):
        add(f"s6_mxc_braid_{b_idx}", "s6_cryo_dr_magnet_readout", "S6.2",
            f"20 mK OFHC Cu S-İlmek Örgü #{b_idx} (2550×Ø50 µm)", "box", (99.8, 3.6, 1.4), (-108.0, by_o, z_cryo + bz_o),
            "ofhc_cu", 0.05, mass_override_kg=0.0045)
    add("s6_cryo_bridge_4k_shield", "s6_cryo_dr_magnet_readout", "S6.2",
        "4 K Radyasyon Kalkan Tüpü (Ø18/Ø21, 36 mm Yarık)", "tube", (9.0, 10.5, 443.0, "x"), (-290.5, 0, z_cryo),
        "ofhc_cu", 0.05, cutaway_mode="section")
    # Exp133 v4.0 Edge-Welded 316L CF63 UHV Bellows Bridge (ID=44/OD=68/L_aktif=120 mm, k=2000 N/m)
    add("s6_cryo_bridge_ovc", "s6_cryo_dr_magnet_readout", "S6.2",
        "Kriyo Köprü UHV Tarafı CF63 Geçiş Boğazı", "tube", (22.0, 28.0, 81.4, "x"), (-232.7, 0, z_cryo),
        "ss316ln", 0.10, alpha=0.55, cutaway_mode="section")
    add("s6_ovc_bellows_flange_uhv", "s6_cryo_dr_magnet_readout", "S6.2",
        "CF63 Körük Bağlantı Flanşı (UHV Tarafı)", "tube", (22.0, 42.0, 8.0, "x"), (-277.5, 0, z_cryo),
        "ss316ln", 0.05, cutaway_mode="section")
    add("s6_ovc_bellows_cf63", "s6_cryo_dr_magnet_readout", "S6.2",
        "Kenar-Kaynaklı 316L CF63 Körük (Ø44/Ø68, k=2000 N/m)", "tube", (22.0, 25.0, 103.8, "x"), (-333.5, 0, z_cryo),
        "ss316ln", 0.05, cutaway_mode="section", mass_override_kg=0.62)
    for r_idx in range(7):
        rx_rib = -288.5 - r_idx * 15.0
        add(f"s6_ovc_bellows_rib_{r_idx + 1}", "s6_cryo_dr_magnet_readout", "S6.2",
            f"CF63 Körük Boğum Halkası #{r_idx + 1} (OD=68)", "tube", (25.1, 34.0, 5.0, "x"), (rx_rib, 0, z_cryo),
            "ss316ln", 0.05, cutaway_mode="section", mass_override_kg=0.04)
    add("s6_ovc_bellows_flange_dr", "s6_cryo_dr_magnet_readout", "S6.2",
        "CF63 Körük Bağlantı Flanşı (DR Tarafı)", "tube", (22.0, 42.0, 8.0, "x"), (-389.5, 0, z_cryo),
        "ss316ln", 0.05, cutaway_mode="section")
    add("s6_ovc_bridge_dr_stub", "s6_cryo_dr_magnet_readout", "S6.2",
        "Kriyo Köprü DR Tarafı CF63 Geçiş Boğazı", "tube", (22.0, 28.0, 81.4, "x"), (-434.3, 0, z_cryo),
        "ss316ln", 0.10, alpha=0.55, cutaway_mode="section")

    # Dilution Refrigerator Tower (S6.8 — 50K/4K/Still/CP/MXC 20 mK) at x = -650, y = 0
    drx = -650.0
    add("s6_dr_support_frame", "s6_cryo_dr_magnet_readout", "S6.8",
        "Seyreltme Kriyostatı (DR) Taşıyıcı Şasisi", "frame", (340.0, 340.0, 260.0, 260.0, 160.0), (drx, 0, 80.0),
        "rack_chassis", 0.50)
    add("s6_dr_ovc_bottom", "s6_cryo_dr_magnet_readout", "S6.8",
        "DR Dış Vakum Kabı (OVC) Tabanı", "cyl", (178.0, 15.0, "z"), (drx, 0, 167.5),
        "ss316ln", 0.20, cutaway_mode="section")
    add("s6_dr_ovc_lower", "s6_cryo_dr_magnet_readout", "S6.8",
        "DR OVC Alt Gövde", "tube", (167.0, 175.0, 280.0, "z"), (drx, 0, 315.0),
        "ss316ln", 0.20, alpha=0.25, cutaway_mode="section")
    add("s6_dr_ovc_port_arc", "s6_cryo_dr_magnet_readout", "S6.8",
        "DR OVC Köprü Geçiş Kemeri", "arc_tube", (167.0, 175.0, 79.90, 24.0, 336.0), (drx, 0, 495.0),
        "ss316ln", 0.20, alpha=0.25, cutaway_mode="section")
    add("s6_dr_ovc_upper", "s6_cryo_dr_magnet_readout", "S6.8",
        "DR OVC Üst Gövde", "tube", (167.0, 175.0, 425.0, "z"), (drx, 0, 747.5),
        "ss316ln", 0.20, alpha=0.25, cutaway_mode="section")
    add("s6_dr_top_flange", "s6_cryo_dr_magnet_readout", "S6.8",
        "DR 300 K Üst Ana Flanş", "cyl", (195.0, 25.0, "z"), (drx, 0, 972.5),
        "ss316ln", 0.10, cutaway_mode="section")
    add("s6_pt420_coldhead", "s6_cryo_dr_magnet_readout", "S6.1",
        "Cryomech PT420 Darbeli-Tüp Soğutucu (Uzak Valf)", "cyl", (64.0, 235.0, "z"), (drx, 0, 1102.5),
        "al6061", 0.20)
    # Exp133 v4.0 PT420 Remote Rotary Valve Box (500 mm offset @ x=-1150) + 600 mm Flex He U-Loop
    rvx = drx - 500.0  # -1150.0 mm
    add("s6_pt420_valve_stand", "s6_cryo_dr_magnet_readout", "S6.1",
        "PT420 Uzak Döner Valf Akustik Zemin Sehpası", "frame", (160.0, 160.0, 128.0, 128.0, 1009.8), (rvx, 0, 504.9),
        "rack_chassis", 0.50)
    add("s6_pt420_remote_valve_box", "s6_cryo_dr_magnet_readout", "S6.1",
        "PT420 Uzak Döner Valf Kutusu (500 mm Ofset)", "box", (180.0, 160.0, 180.0), (rvx, 0, 1100.0),
        "al6061", 0.20, mass_override_kg=9.50)
    add("s6_pt420_flex_he_upper_l", "s6_cryo_dr_magnet_readout", "S6.1",
        "PT420 Esnek He Hattı Sol Üst (L_top=600 mm)", "cyl", (11.0, 99.0, "x"), (-1010.0, 0, 1130.0),
        "ss316ln", 0.20, mass_override_kg=0.25)
    add("s6_pt420_flex_he_drop_l", "s6_cryo_dr_magnet_readout", "S6.1",
        "PT420 Esnek He Hattı Sol İniş (U-İlmek)", "cyl", (11.0, 116.5, "z"), (-960.0, 0, 1060.25),
        "ss316ln", 0.20, mass_override_kg=0.30)
    add("s6_pt420_flex_he_bottom", "s6_cryo_dr_magnet_readout", "S6.1",
        "PT420 Esnek He Hattı Alt U-İlmek (600 mm)", "cyl", (11.0, 122.0, "x"), (-887.5, 0, 1002.0),
        "ss316ln", 0.20, mass_override_kg=0.32)
    add("s6_pt420_flex_he_rise_r", "s6_cryo_dr_magnet_readout", "S6.1",
        "PT420 Esnek He Hattı Sağ Çıkış (U-İlmek)", "cyl", (11.0, 116.5, "z"), (-815.0, 0, 1071.75),
        "ss316ln", 0.20, mass_override_kg=0.30)
    add("s6_pt420_flex_he_upper_r", "s6_cryo_dr_magnet_readout", "S6.1",
        "PT420 Esnek He Hattı Sağ Üst (PT420 Girişi)", "cyl", (11.0, 89.0, "x"), (-759.0, 0, 1130.0),
        "ss316ln", 0.20, mass_override_kg=0.23)
    add("s6_dr_flange_50k", "s6_cryo_dr_magnet_readout", "S6.8",
        "DR 50 K Radyasyon Kademesi Flanşı", "cyl", (156.0, 14.0, "z"), (drx, 0, 847.0),
        "al6061", 0.10)
    add("s6_shield_50k_lower", "s6_cryo_dr_magnet_readout", "S6.2",
        "50 K Alüminyum Termal Kalkan (Alt)", "tube", (150.0, 154.0, 235.0, "z"), (drx, 0, 337.5),
        "al6061", 0.20, alpha=0.28, cutaway_mode="section")
    add("s6_shield_50k_port", "s6_cryo_dr_magnet_readout", "S6.2",
        "50 K Termal Kalkan (Port Kemeri)", "arc_tube", (150.0, 154.0, 79.90, 24.0, 336.0), (drx, 0, 495.0),
        "al6061", 0.20, alpha=0.28, cutaway_mode="section")
    add("s6_shield_50k_upper", "s6_cryo_dr_magnet_readout", "S6.2",
        "50 K Alüminyum Termal Kalkan (Üst)", "tube", (150.0, 154.0, 305.0, "z"), (drx, 0, 687.5),
        "al6061", 0.20, alpha=0.28, cutaway_mode="section")
    add("s6_dr_flange_4k", "s6_cryo_dr_magnet_readout", "S6.8",
        "DR 4 K Kademesi Flanşı (OFHC Cu)", "cyl", (138.0, 16.0, "z"), (drx, 0, 728.0),
        "ofhc_cu", 0.10)
    add("s6_shield_4k_lower", "s6_cryo_dr_magnet_readout", "S6.2",
        "4 K OFHC Bakır Termal Kalkan (Alt)", "tube", (132.0, 136.0, 205.0, "z"), (drx, 0, 352.5),
        "ofhc_cu", 0.20, alpha=0.32, cutaway_mode="section")
    add("s6_shield_4k_port", "s6_cryo_dr_magnet_readout", "S6.2",
        "4 K Termal Kalkan (Port Kemeri)", "arc_tube", (132.0, 136.0, 79.90, 24.0, 336.0), (drx, 0, 495.0),
        "ofhc_cu", 0.20, alpha=0.32, cutaway_mode="section")
    add("s6_shield_4k_upper", "s6_cryo_dr_magnet_readout", "S6.2",
        "4 K OFHC Bakır Termal Kalkan (Üst)", "tube", (132.0, 136.0, 185.0, "z"), (drx, 0, 627.5),
        "ofhc_cu", 0.20, alpha=0.32, cutaway_mode="section")
    add("s6_hemt_rack_4k", "s6_cryo_dr_magnet_readout", "S6.6",
        "4 K InP HEMT LNA Rafı (56–82 Kanal, ≤1,0 W)", "tube", (88.0, 122.0, 46.0, "z"), (drx, 0, 697.0),
        "fr4_rogers", 0.10, cutaway_mode="section")
    # Exp131 v4.0 M4 4K SKY130 968-Gate Crossbar Multiplexer (central bay inside HEMT ring, clear of coax)
    add("s6_m4_crossbar_4k_mount", "s6_cryo_dr_magnet_readout", "S6.6",
        "4 K M4 Çapraz-Anahtar OFHC Termal Taşıyıcı", "box", (100.0, 72.0, 8.0), (drx, 0, 715.9),
        "ofhc_cu", 0.05)
    add("s6_m4_crossbar_4k_pcb", "s6_cryo_dr_magnet_readout", "S6.6",
        "4 K SKY130 968-Kapı M4 Çapraz-Anahtar Kartı", "box", (96.0, 68.0, 16.0), (drx, 0, 703.8),
        "fr4_rogers", 0.05)
    add("s6_dr_flange_still", "s6_cryo_dr_magnet_readout", "S6.8",
        "DR Still (~800 mK) Kademesi Flanşı", "cyl", (116.0, 12.0, "z"), (drx, 0, 616.0),
        "ofhc_cu", 0.10)
    add("s6_dr_flange_cp", "s6_cryo_dr_magnet_readout", "S6.8",
        "DR Cold Plate (~100 mK) Flanşı", "cyl", (104.0, 10.0, "z"), (drx, 0, 550.0),
        "ofhc_cu", 0.10)
    add("s6_dr_flange_mxc", "s6_cryo_dr_magnet_readout", "S6.8",
        "DR MXC (~20 mK) Karıştırma Odası Flanşı", "cyl", (95.0, 16.0, "z"), (drx, 0, zw - 10.0),
        "ofhc_cu", 0.05)

    stage_spans = [
        ("300k_50k", 854.0, 960.0),
        ("50k_4k",   736.0, 840.0),
        ("4k_still", 622.0, 720.0),
        ("still_cp", 555.0, 610.0),
        ("cp_mxc",   498.0, 545.0),
    ]
    for st_name, z0, z1 in stage_spans:
        h = z1 - z0
        zc = 0.5 * (z0 + z1)
        for sgn, stag in ((1.0, "pos"), (-1.0, "neg")):
            add(f"s6_coax_{st_name}_{stag}", "s6_cryo_dr_magnet_readout", "S6.4",
                f"56–82 Koaksiyel Demet ({st_name})", "cyl", (9.0, h, "z"), (drx, sgn * 62.0, zc),
                "nbtin_si", 0.10)

    # ==================== S7: 19" ELECTRONICS RACK & INTERCONNECT ===========================
    rx0 = 1030.0
    add("s7_rack_base", "s7_electronics_rack_interconnect", "S7.1",
        "19\" Kabin Taban Şasisi", "box", (500.0, 600.0, 50.0), (rx0, 0, 25.0),
        "rack_chassis", 0.50)
    add("s7_rack_top", "s7_electronics_rack_interconnect", "S7.1",
        "19\" Kabin Üst Tavan & Fan Ünitesi", "box", (500.0, 600.0, 40.0), (rx0, 0, 1380.0),
        "rack_chassis", 0.50)
    for idx, (px, py) in enumerate(((795, -285), (1265, -285), (1265, 285), (795, 285)), start=1):
        add(f"s7_rack_post_{idx}", "s7_electronics_rack_interconnect", "S7.1",
            f"19\" Kabin Köşe Dikmesi #{idx}", "box", (30.0, 30.0, 1310.0), (px, py, 705.0),
            "rack_chassis", 0.50)
    add("s7_psu_hv_bay", "s7_electronics_rack_interconnect", "S7.4",
        "±5 kV Kolon HV & 8-Bobin Mıknatıs PSU", "box", (430.0, 482.0, 220.0), (rx0, 0, 170.0),
        "rack_psu", 0.50)
    add("s7_host_gpu_server", "s7_electronics_rack_interconnect", "S7.1",
        "Ana Kontrol Sunucusu & GRAPE/CellISA GPU", "box", (430.0, 482.0, 240.0), (rx0, 0, 420.0),
        "rack_steel", 0.50)
    add("s7_fpga_blanker_bay", "s7_electronics_rack_interconnect", "S7.3",
        "FPGA Blanker/IBIC Sayım Kapısı & Servo DSP", "box", (430.0, 482.0, 220.0), (rx0, 0, 670.0),
        "rack_fpga", 0.20)
    add("s7_awg_rf_mw_bay", "s7_electronics_rack_interconnect", "S7.2",
        "Çok-Kanallı AWG & 56–82 Zincir RF/MW Sentezi", "box", (430.0, 482.0, 300.0), (rx0, 0, 950.0),
        "rack_awg", 0.20)
    add("s7_clock_sync_bay", "s7_electronics_rack_interconnect", "S7.4",
        "10 MHz Rb Saat Dağıtımı & Kriyo Termometri", "box", (430.0, 482.0, 210.0), (rx0, 0, 1225.0),
        "rack_clock", 0.20)
    add("s7_feedthrough_panel", "s7_electronics_rack_interconnect", "S7.4",
        "Kriyo / UHV / RF Geçiş Yama Paneli", "box", (36.0, 460.0, 480.0), (762.0, 0, 950.0),
        "al6061", 0.20)

    return p


PARTS = _build_parts()

# Ion beam axis marker (not a solid): from duoplasmatron exit (z=922.66) to wafer top (z=500.00)
BEAM = ((0.0, 0.0, Z_WAFER + 422.66), (0.0, 0.0, Z_WAFER))

# Overall machine envelope (mm)
ENVELOPE = dict(x=(-1260.0, 1320.0), y=(-520.0, 470.0), z=(0.0, 1440.0))


def subsystem_parts(sub_key: str) -> dict[str, dict]:
    return {k: v for k, v in PARTS.items() if v["subsystem"] == sub_key}


def part_color(spec: dict) -> str:
    return MATERIALS[spec["material"]]["color"]


def part_density(spec: dict) -> float:
    return MATERIALS[spec["material"]]["density"]
