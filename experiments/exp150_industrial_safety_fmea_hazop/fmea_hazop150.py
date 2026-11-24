"""Preliminary M0 Uncertified 25-Row FMEA, 10-Node HAZOP & S7.SAFETY Kit Target Spec (Exp150 / H168).

References IEC 61508 and SEMI S2 as design-screening targets ONLY.
NOT certified: iec61508_certified=False, semi_s2_certified=False, requires_third_party_assessment=True.
"""
from __future__ import annotations

from typing import Any


def build_fmea_25_rows() -> list[dict[str, Any]]:
    """Return preliminary M0 25-row FMEA covering S1-S9 + Facility (S x O x D = RPN, pre vs post mitigation)."""
    # Scale: S (Severity 1-10, 10=fatality/permanent disability), O (Occurrence 1-10),
    # D (Detection 1-10, 1=automatic SIL-3 target interlock). All SIL labels are uncertified M0 design targets.
    raw_rows = [
        # --- S1: Ion Source, PH3, Multi-Species, HV (5 rows) ---
        ("FM-01", "S1.1", "PH3 silindir / pigtail kopması (basınçlı silindir vs SDS)",
         "Zehirli/piroforik PH3 salınımı (>IDLH 50 ppm, ölümcül)",
         10, 4, 7, "Sub-atm SDS (<650 Torr, 10 g) + vakum ceket + 250 CFM scrubber + 0,02 ppm SIL-3 hedef vana", 10, 1, 2, "SIL-3"),
        ("FM-02", "S1.1", "PH3 MFC/vana iç sızıntısı (1 sccm sürekli kaçak)",
         "Gaz dolabında PH3 birikimi, bakım sırasında maruziyet",
         9, 5, 6, "Çift elektrokimyasal sensör (0,02/0,05 ppm) + 250 CFM negatif basınç + otomatik N2 süpürme", 9, 2, 2, "SIL-3"),
        ("FM-03", "S1.3", "10–22 kV HV kablo/yalıtkan arkı veya panel açılması",
         "Elektrik çarpması / ark yanığı / HV güç kaynağı hasarı",
         10, 4, 6, "SIL-2 hedef kilitli HV muhafaza + 2 MOhm aktif crowbar (18,3 ms <50 V, <0,37 J)", 10, 1, 2, "SIL-2"),
        ("FM-04", "S1.1-S1.5", "14–22 keV geri-saçılan elektron Bremsstrahlung X-ışını",
         "Operatör iyonlaştırıcı radyasyon maruziyeti (özellikle S5.5 safir port)",
         8, 5, 7, "6–10 mm 316L duvar (<1,1e-43 uSv/h) + S5.5 3 mm çelik OD8 kılıf (1,2e-23 uSv/h) + yıllık ölçüm", 8, 2, 2, "SIL-2"),
        ("FM-05", "S1.6", "Option-Q 121Sb (450 °C) / 167Er fırın aşırı ısınması",
         "Termal kaçak, ağır metal (Sb) buhar kontaminasyonu, conta hasarı",
         7, 4, 6, "Çift K-tipi termokupl + bağımsız donanımsal 500 °C aşırı-sıcaklık rölesi + HEPA bakım", 7, 2, 2, "SIL-2"),

        # --- S2-S4: MEMS Blanker, IBIC, Piezo Stage & Interferometry (4 rows) ---
        ("FM-06", "S2.3", "Arch-B 0,250 mm WD çökmesi / piezo Z-kaçması yongaya çarpma",
         "32x32 MEMS lens kırılması ve HV kısa devre",
         7, 5, 6, "Kapasitif Z-yaklaşma sensörü + donanımsal piezo HV sınırlayıcı + yazılım/FPGA sert durdurma", 7, 2, 3, "SIL-2"),
        ("FM-07", "S2.2", "SKY130 16-karo blanker kilidi açık kalması (aşırı doz)",
         "Yonga aşırı implantasyon hasarı, HV besleme aşırı yükü",
         6, 5, 5, "Donanımsal watchdog (blanker_tile_formal.v) + Faraday kupası akım kilidi", 6, 2, 2, "SIL-1"),
        ("FM-08", "S3.2", "100 K LTC6268 IBIC ön-uç HV/bias arızası",
         "CSA doyumu / yonga kaçak akım ısınması",
         5, 5, 5, "Seri 10 MOhm akım sınırlayıcı direnç + TVS koruma + otomatik bias kesici", 5, 2, 2, "SIL-1"),
        ("FM-09", "S4.1", "4x pnömatik hava yayı basınç kaybı / deprem sarsıntısı",
         "900x700 granit bloğun ani çökmesi, körük yırtılması",
         8, 3, 6, "Mekanik sert durdurma tamponları (2 mm strok) + sismik ankraj + basınç anahtarı", 8, 2, 2, "SIL-2"),

        # --- S5 / S5.5 / S5.6: UHV, Class-4 Laser, MBE & Forming Gas (6 rows) ---
        ("FM-10", "S5.5", "808 nm Sınıf-4 flaş lazer (43,49 J/cm^2) açık kapak ateşlemesi",
         "Anında kalıcı retina körlüğü (NOHD > 1.400 m, NHZ_diff = 14,6 m)",
         10, 4, 7, "OD>=8 ışık-geçirmez muhafaza hedefi + 1oo2D SIL-3 hedef mekanik perde (3,2 ms) + diyot kesici (nominal PFD=2,34e-5; sertifikasız)", 10, 1, 2, "SIL-3"),
        ("FM-11", "S5.5", "CF63 safir pencere termal şok / lazer kaynaklı çatlama",
         "UHV ani atmosfer girişi + lazer demet kaçağı",
         9, 3, 6, "8,96x LIDT marjı (11,16 vs 100 J/cm^2) + 10 us pirometre + çift vakum/basınç kilidi", 9, 1, 3, "SIL-3"),
        ("FM-12", "S5.5", "MXC 20 mK soğukken yanlışlıkla flaş tavlama tetiklenmesi",
         "DR 20 mK kademesinde şiddetli ısınma ve vakum basınç sıçraması",
         7, 4, 6, "Donanımsal MXC < 1 K & UHV sürgülü vana durum kilidi (Exp130 / SIL-2 hedefi)", 7, 1, 2, "SIL-2"),
        ("FM-13", "S5.6", "S5.6 5% H2/N2 pasivasyon hattı sızıntısı",
         "H2 yangın/patlama riski kaygısı",
         8, 4, 5, "ISO 10156 <=%5,7 N2 karışımı (havada doğal alevlenmez) + akış sınırlayıcı orifis + egzoz", 8, 1, 2, "SIL-2"),
        ("FM-14", "S5.6", "S5.6 345 °C PBN ısıtıcı / 28Si süblimasyon soğutma suyu kesilmesi",
         "CF100 conta aşırı ısınması, vakum kaçağı",
         7, 4, 5, "Soğutma akış anahtarı + gövde RTD (>80 °C) sert güç kesici + otomatik deklanşör", 7, 2, 2, "SIL-2"),
        ("FM-15", "S5.2", "300 L/s Mag-Lev turbo pompa rotor arızası / ani hava girişi",
         "Mekanik parça fırlaması, UHV oda kontaminasyonu",
         8, 3, 6, "ISO-27892 rotor muhafaza hedefi + <80 ms yay-dönüşlü sürgülü vana + titreşim sensörü", 8, 2, 2, "SIL-2"),

        # --- S6 / S6.5 / S9.1: Cryo DR, He ODH, Magnet Quench & qRAM (5 rows) ---
        ("FM-16", "S6.8", "PT420 + LD400 kapalı-çevrim Helyum envanteri temizodaya salınımı",
         "Kapalı küçük hacimde oksijen eksikliği (ODH < %19,5)",
         9, 3, 7, "Kuru kapalı-çevrim (1,10 m^3 STP -> 60 m^3 odada O2=%20,57) + duvar O2 monitörü (%19,5)", 9, 1, 2, "SIL-2"),
        ("FM-17", "S6.8", "Kriyo iç hat patlaması / OVC ani aşırı basınçlanması",
         "DR dış vakum kabı (OVC) mekanik patlaması",
         9, 3, 6, "ASME 0,5 barg yaylı tahliye + yedekli DN50 patlama diski (16,4x He / 25,7x N2 akış marjı)", 9, 1, 2, "SIL-3"),
        ("FM-18", "S6.3", "Exp125 8-bobinli 1,50 T mıknatıs ani quench (18,94 kJ)",
         "Bobin sıcak nokta hasarı, >400 V ark veya boşaltma direnci yangını",
         8, 4, 5, "30 ms quench dedektörü + 1,563 Ohm hava-soğutmalı direnç (T_hot=64,6 K, direnç 38,2 °C)", 8, 2, 2, "SIL-2"),
        ("FM-19", "S6.3", "1,50 T mıknatıs kaçak alanı (kalp pili / ferromanyetik fırlama)",
         "5 Gauss (0,5 mT) aşımında tıbbi cihaz / alet fırlama tehlikesi",
         8, 4, 5, "Exp125 aktif kalkan bobinleri (0,5 mT < 0,62 m) + zemin sınır çizgisi + ferromanyetik yasak", 8, 2, 2, "SIL-1"),
        ("FM-20", "S9.1", "Option-Q 1550 nm SMF-28 optik fiber kopması / konnektör açılması",
         "Görünmez kızılötesi (<10 mW Sınıf 1M/3R) göz maruziyeti",
         6, 4, 6, "Otomatik optik güç kesme (ALS) + APC kapaklı konnektör + düşük güç (<2 mW)", 6, 2, 2, "SIL-1"),

        # --- S7 / S9.HPC / Facility: Power, EPO, Safety PLC, Cooling, Cyber (5 rows) ---
        ("FM-21", "S7.SAFETY", "Plansız şebeke elektrik kesintisi (tam tesis kararması)",
         "UHV geri-akış, yonga oksitlenmesi, DR ısınma aşırı basıncı, kontrol kaybı",
         8, 5, 5, "15 kVA / 10 kWh online UPS (0 ms) + <80 ms UHV vana (<0,001 ML) + 180 dk Tier-1", 8, 2, 2, "SIL-2"),
        ("FM-22", "S7.SAFETY", "Acil Durdurma (EPO) basımında tek-kanal röle yapışması",
         "HV veya lazerin acil durumda kesilememesi",
         10, 3, 7, "1oo2D çift-kanallı SIL-3 hedef emniyet PLC + zorlamalı-kılavuzlu (force-guided) kontaktörler (sertifikasız M0)", 10, 1, 2, "SIL-3"),
        ("FM-23", "S9.HPC", "Option-HPC 4U 100G RDMA rafı (2.195 W) fan/soğutma arızası",
         "Sunucu aşırı ısınması, duman/yangın riski",
         7, 4, 5, "Yedekli 2,6 kW Titanium PSU + BMC 85 °C termal kesici + raf duman dedektörü", 7, 2, 2, "SIL-2"),
        ("FM-24", "S7.3", "Yazılım/FPGA bozuk komut gönderimi (yanlış lazer/HV tetiği)",
         "Otonom yazılımla emniyet sınırlarının aşılması",
         9, 4, 6, "Yazılımdan bağımsız donanımsal SIL-3 hedef emniyet PLC kilitleme katmanı (sertifikasız M0)", 9, 1, 2, "SIL-3"),
        ("FM-25", "Facility", "Temizoda HVAC/sıcaklık kayması veya su soğutma kaçağı",
         "Optik hizalama kayması, elektrik panosunda su kısa devresi",
         6, 5, 5, "Zemin su kaçağı sensörü + solenoid su kesici + ±10 mK HVAC alarmı (Exp133)", 6, 2, 2, "SIL-1"),
    ]
    rows: list[dict[str, Any]] = []
    for fid, sub, mode, eff, s0, o0, d0, mit, s1, o1, d1, sil in raw_rows:
        rpn_pre = s0 * o0 * d0
        rpn_post = s1 * o1 * d1
        rows.append({
            "id": fid,
            "subsystem": sub,
            "failure_mode": mode,
            "effect": eff,
            "S_pre": s0, "O_pre": o0, "D_pre": d0, "RPN_pre": rpn_pre,
            "mitigation": mit,
            "S_post": s1, "O_post": o1, "D_post": d1, "RPN_post": rpn_post,
            "rpn_reduction_pct": round((1.0 - rpn_post / rpn_pre) * 100.0, 1),
            "target_sil": sil,
            "sil_certification_status": "DESIGN_TARGET_ONLY_NOT_CERTIFIED",
        })
    return rows


def build_hazop_10_nodes() -> list[dict[str, Any]]:
    """Return preliminary M0 10-node HAZOP guideword screening referencing SEMI S2 & IEC 61882 (uncertified)."""
    nodes = [
        {"node": "HZ-01", "system": "S5.5 808 nm Flaş Lazer", "guideword": "OTHER THAN (Kapak açık)",
         "deviation": "Sınıf-4 43,49 J/cm^2 demetin dış ortama kaçışı",
         "safeguard": "OD>=8 muhafaza hedefi + 1oo2D SIL-3 hedef 3,2 ms perde + diyot kesici", "sil": "SIL-3"},
        {"node": "HZ-02", "system": "S1.1 PH3 Gaz Besleme", "guideword": "MORE (Sızıntı/Basınç)",
         "deviation": "Zehirli/piroforik PH3 salınımı (>0,05 ppm TLV / 50 ppm IDLH)",
         "safeguard": "<650 Torr SDS + vakum ceket + 250 CFM scrubber + 0,02 ppm SIL-3 hedef vana", "sil": "SIL-3"},
        {"node": "HZ-03", "system": "S1-S2 HV Kolon (10-22 kV)", "guideword": "MORE (Voltaj/Ark)",
         "deviation": "HV elektrik çarpması & 22 keV Bremsstrahlung X-ışını",
         "safeguard": "6-10 mm 316L + S5.5 çelik kılıf (<1,2e-23 uSv/h) + 2 MOhm crowbar (18,3 ms)", "sil": "SIL-2"},
        {"node": "HZ-04", "system": "S5.6 28Si MBE & %5 H2/N2", "guideword": "MORE (Sıcaklık/Akış)",
         "deviation": "PBN 345 °C kaçak veya H2 pasivasyon sızıntısı",
         "safeguard": "ISO 10156 alevlenmez %5 H2/N2 (<%5,7) + 80 °C RTD + su akış kilidi", "sil": "SIL-2"},
        {"node": "HZ-05", "system": "S6.8 DR & PT420 He Devresi", "guideword": "MORE (OVC Basınç / He Kaçağı)",
         "deviation": "OVC aşırı basınçlanması veya temizoda O2 düşüşü",
         "safeguard": "Kuru 1,10 m^3 He (60 m^3 O2=%20,57) + ASME DN50 0,5 barg disk + O2 monitör", "sil": "SIL-3"},
        {"node": "HZ-06", "system": "S6.3 8-Bobin 1,50 T Mıknatıs", "guideword": "NO (Soğutma) -> QUENCH",
         "deviation": "18,94 kJ manyetik enerjinin ani boşalımı",
         "safeguard": "30 ms quench dedektörü + 1,563 Ohm direnç (38,2 °C, T_hot=64,6 K)", "sil": "SIL-2"},
        {"node": "HZ-07", "system": "S5 Ana UHV Oda & Pompalar", "guideword": "REVERSE (Geri Akış)",
         "deviation": "Güç kesintisi veya turbo arızasında atmosfer girişi",
         "safeguard": "<80 ms yay-dönüşlü all-metal UHV sürgülü vanalar (<0,001 ML oksit)", "sil": "SIL-2"},
        {"node": "HZ-08", "system": "S7.SAFETY Şebeke / EPO", "guideword": "NO (Şebeke Gücü)",
         "deviation": "Plansız elektrik kesintisi veya EPO aktivasyonu",
         "safeguard": "15 kVA / 10 kWh online UPS (0 ms) + 40 dk tam / 213 dk Tier-1 + 1oo2D EPO hedefi", "sil": "SIL-3"},
        {"node": "HZ-09", "system": "S9.HPC 100G RDMA Rafı", "guideword": "MORE (Termal Yük)",
         "deviation": "2.195 W soğutma kaybı & aşırı ısınma",
         "safeguard": "Yedekli 2,6 kW Titanium PSU + 85 °C BMC kesici + raf duman sensörü", "sil": "SIL-2"},
        {"node": "HZ-10", "system": "S1.6 Option-Q (Sb/Er) & S9.1", "guideword": "OTHER THAN (Bakım/Fiber)",
         "deviation": "450 °C Sb fırını termal kaçağı veya 1550 nm fiber açılması",
         "safeguard": "500 °C donanım kesici + ALS otomatik optik güç kesme + HEPA bakım", "sil": "SIL-2"},
    ]
    for n in nodes:
        n["sil_certification_status"] = "DESIGN_TARGET_ONLY_NOT_CERTIFIED"
    return nodes


def build_safety_hardware_spec(m3_v6_full_usd: float) -> dict[str, Any]:
    """Build preliminary M0 S7.SAFETY hardware target specification JSON for BOM v7.0 / CAD v7.0."""
    items = [
        {
            "part_id": "S7.SAFETY-01",
            "name": "Sub-Atmospheric SDS PH3 Micro-Cylinder Gas Cabinet (<650 Torr, 10 g), Vacuum-Jacket Line, 250 CFM Dry Scrubber & Dual 0.02 ppm Sensors",
            "qty": 1,
            "location": "Facility gas bay adjacent to S1/S7",
            "envelope_mm": [600.0, 500.0, 1800.0],
            "mass_kg_total": 118.0,
            "power_W_total": 480.0,
            "cryo_load_W": 0.0,
            "cost_usd_low": 28000,
            "cost_usd_nom": 42000,
            "cost_usd_high": 62000,
            "sil_level": "SIL-3",
            "sil_certification_status": "DESIGN_TARGET_ONLY_NOT_CERTIFIED",
            "epistemic_tag": "Varsayim",
        },
        {
            "part_id": "S7.SAFETY-02",
            "name": "ANSI Z136.1 OD>=8 (808 nm) Interlocked Class-1 Target Laser/X-Ray Steel Shroud & Dual-Channel SIL-3 Target Mechanical Shutter (<5 ms)",
            "qty": 1,
            "location": "S5.5 +Y viewport perimeter",
            "envelope_mm": [280.0, 260.0, 220.0],
            "mass_kg_total": 38.0,
            "power_W_total": 45.0,
            "cryo_load_W": 0.0,
            "cost_usd_low": 14000,
            "cost_usd_nom": 22000,
            "cost_usd_high": 34000,
            "sil_level": "SIL-3",
            "sil_certification_status": "DESIGN_TARGET_ONLY_NOT_CERTIFIED",
            "epistemic_tag": "Varsayim",
        },
        {
            "part_id": "S7.SAFETY-03",
            "name": "IEC 61508 SIL-3 Target 1oo2D Hardwired Safety PLC, 4x E-Stop Mushrooms, Guard Switches & 2 MOhm HV Crowbar Module",
            "qty": 1,
            "location": "S7 rack top / perimeter E-Stop loop",
            "envelope_mm": [482.6, 350.0, 133.4],
            "mass_kg_total": 18.0,
            "power_W_total": 120.0,
            "cryo_load_W": 0.0,
            "cost_usd_low": 18000,
            "cost_usd_nom": 28000,
            "cost_usd_high": 42000,
            "sil_level": "SIL-3",
            "sil_certification_status": "DESIGN_TARGET_ONLY_NOT_CERTIFIED",
            "epistemic_tag": "Varsayim",
        },
        {
            "part_id": "S7.SAFETY-04",
            "name": "15 kVA / 10 kWh Online Double-Conversion LFP UPS (0 ms Transfer) & Tiered Load-Shed PDU",
            "qty": 1,
            "location": "Facility power bay adjacent to S7/S9.HPC",
            "envelope_mm": [440.0, 720.0, 780.0],
            "mass_kg_total": 145.0,
            "power_W_total": 350.0,
            "cryo_load_W": 0.0,
            "cost_usd_low": 15000,
            "cost_usd_nom": 24000,
            "cost_usd_high": 36000,
            "sil_level": "SIL-2",
            "sil_certification_status": "DESIGN_TARGET_ONLY_NOT_CERTIFIED",
            "epistemic_tag": "Liste-Capasi",
        },
        {
            "part_id": "S7.SAFETY-05",
            "name": "Cleanroom O2 Deficiency Monitor (19.5% Alarm), ASME DN50 0.5 barg OVC Burst Disk/Relief & 1.563 Ohm Quench Dump Bank",
            "qty": 1,
            "location": "S6 DR OVC + Cleanroom wall + S7 dump bay",
            "envelope_mm": [380.0, 260.0, 240.0],
            "mass_kg_total": 24.0,
            "power_W_total": 35.0,
            "cryo_load_W": 0.0,
            "cost_usd_low": 8000,
            "cost_usd_nom": 14000,
            "cost_usd_high": 22000,
            "sil_level": "SIL-3",
            "sil_certification_status": "DESIGN_TARGET_ONLY_NOT_CERTIFIED",
            "epistemic_tag": "Liste-Capasi",
        },
        {
            "part_id": "S7.SAFETY-06",
            "name": "Fast Spring-Return UHV Isolation Gate Valve Actuators (<80 ms), ISO 10156 5% H2/N2 Orifice & X-Ray Survey Meter",
            "qty": 1,
            "location": "S5.2/S5.3/S5.6 vacuum manifolds & cleanroom",
            "envelope_mm": [220.0, 180.0, 160.0],
            "mass_kg_total": 12.0,
            "power_W_total": 60.0,
            "cryo_load_W": 0.0,
            "cost_usd_low": 9000,
            "cost_usd_nom": 15000,
            "cost_usd_high": 24000,
            "sil_level": "SIL-2",
            "sil_certification_status": "DESIGN_TARGET_ONLY_NOT_CERTIFIED",
            "epistemic_tag": "Varsayim",
        },
    ]
    tot_mass = round(sum(x["mass_kg_total"] for x in items), 2)
    tot_pow = round(sum(x["power_W_total"] for x in items), 2)
    c_low = sum(x["cost_usd_low"] for x in items)
    c_nom = sum(x["cost_usd_nom"] for x in items)
    c_high = sum(x["cost_usd_high"] for x in items)
    return {
        "source_experiment": "exp150_industrial_safety_fmea_hazop",
        "hypothesis_id": "H168",
        "subsystem_id": "S7.SAFETY",
        "title": "Preliminary Parametric Safety Kit Design Target (S7.SAFETY, Uncertified M0; SEMI S2 / IEC 61508 Reference Only)",
        "no_lab_measurement": True,
        "no_supplier_quotes": True,
        "iec61508_certified": False,
        "semi_s2_certified": False,
        "certification_status": "PRELIMINARY_PARAMETRIC_CALCULATION_NOT_CERTIFIED",
        "requires_third_party_assessment": True,
        "epistemic_tags": ["{Model}", "{Liste-Capasi}", "{Varsayım}"],
        "totals": {
            "n_items": len(items),
            "total_mass_kg": tot_mass,
            "cryo_cold_mass_kg": 0.0,
            "steady_electrical_power_W": tot_pow,
            "cryo_load_W": 0.0,
            "cost_usd_low": c_low,
            "cost_usd_nom": c_nom,
            "cost_usd_high": c_high,
            "pct_of_m3_v6_full_bom": round((c_nom / m3_v6_full_usd) * 100.0, 2),
        },
        "items": items,
    }
