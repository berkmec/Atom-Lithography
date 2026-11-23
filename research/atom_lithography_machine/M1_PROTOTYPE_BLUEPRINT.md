# `M1` Fiziksel Laboratuvar Prototipi Tasarım ve Kurulum Planı (`M1_PROTOTYPE_BLUEPRINT`)

**Sürüm:** `v5.0` (Tam `v5.0` Hata-Toleranslı Kilit — `Exp124–141`, `CAD v5.0`, `Q16.16` BOED-FPGA & `CellISA v3.5`, `S5.5` `1530,1 K` + `S5.6` LT-MBE Rota C, `S6.11/S6.5` Cryo-MUX/TWPA, `BOM_DETAILED v5.0`, `8-RFQ`, `198/198` `pytest` — 2026-11-23; `v3.0` [`v4.0`]: 2026-11-23; `v1.0` taslak: 2026-11-22).  
**Dayanak:** [DESIGN.md](DESIGN.md) (`v5.0`), [MODULAR.md](MODULAR.md) (`v5.0-ICD`), [BOM_DETAILED.csv](BOM_DETAILED.csv) (`v5.0`, `167` parça), [BOM_ENGINEERING.md](BOM_ENGINEERING.md) (`v5.0`), [RFQ_SPECIFICATIONS.md](RFQ_SPECIFICATIONS.md) (`8-RFQ`), [LITERATURE.md](LITERATURE.md), [TECHNICAL_MANUAL.md](TECHNICAL_MANUAL.md) (`v5.0`), `research/atom_lithography_machine/cad/cad_verification.json` (`CAD v5.0`: `189` parça, `1.034,94 kg`, `0/17.766` çakışma, `32/32` boşluk), `results/exp124..141*`.

> **Epistemik Sınır ve Amaç:** Bu belge, `M0` (teori/model/EDA — `198/198` `pytest` [`23/23` dosya]) aşamasından ilk fiziksel laboratuvar gösterimine (**`M1 v5.0` — tek-demet sayılmış implantasyon + `S5.5` `1530,1 K` küme-temizleyici flaş tavlama + `S5.6` yerinde `8 nm` LT-MBE kapak ve `FG/H₂` Rota C pasivasyonu + `S6.9` `PT420` titreşim yalıtımı + `S6.11/S6.5` `Q16.16` BOED-FPGA & tek-zincir TWPA/Purcell kriyo testi + `CellISA v3.5` + `G6b` `ENDOR` Risk `R1` doğrulama kapısı**) geçişin eksiksiz mühendislik planıdır. **Projede henüz laboratuvar ölçümü, tedarikçi teklifi veya üretilmiş donanım yoktur (`no_lab_measurement=true`, `no_supplier_quotes=true`, `tapeout_done=false`).** `Exp124`–`Exp141` sayısal hedefleri ve dürüst `FAIL` sınırları (`Exp124/126/127/129/131/134/136/137/138/139`) aşağıda mühürlenmiştir.

---

## 1. `M1 v5.0` Görev Tanımı, Bütçe Özeti ve Çıkış Ölçütü
- **Tek Cümlelik Hedef:** Seyreltik epitaksiyel `²⁹Si` banyosu (`f = %1,0` baz ve **`f* = %1,5 + 2 MV/m`** Stark-destekli hedef, Mod B — donör saçılmasından etkilenmeyen baz mod, `Exp124 CD8` & `Exp136`) taşıyan `²⁸Si` test kuponları üzerinde, tek-demet `10→5 keV` sayılmış `³¹P⁺` implantasyonu + `100 K` soğuk-ada IBIC tek-iyon algılaması + **`S5.5` `808 nm / 1,0 ms / 1530,1 K` (`43,49 J/cm²`) küme-temizleyici flaş tavlama** (`Exp139`) + **`S5.6` `8 nm` LT-MBE (`345 °C`) + `350 °C` `FG/H₂` Rota C pasivasyonu** (`S_ε = 0,390 µeV/√Hz`, `Exp139`) + **`S6.9` ayrıştırılmış `PT420`** (`σ_stage = 0,1024 nm`, `Exp133`) + `MXC` (`~20 mK`, `1,500000 T`) **`Q16.16` BOED-FPGA & TWPA/Purcell** tek-donor ESR/ENDOR (`Exp132/140`) + yazmaç-özgü `XY8`-GRAPE senteziyle:
  1. **En az bir (hedef: `≥ 3`) sertifikalı `K=8` (veya evrensel `K=4` altküme) çekirdek-spin yazmacını fiziksel olarak doğrulamak ve `CellISA v3.5` (`17` komut: `+ ECHO_CZ, MUX_READOUT, SYNDROME_CYCLE`) üzerinden `Bell`/`GHZ-4`/`BitFlip-3`/`QFT-3` ile tek-zincir `MUX_READOUT` / sendrom döngüsü ön-doğrulamasını koşturmak** `[DESIGN.md v5.0 §10 | M1]`,
  2. **`G6b` (`Exp129/136` Risk `R1`) deneysel `ENDOR` ölçümüyle `f = %1,0` ve `f* = %1,5 + 2 MV/m` kuponlarında gerçek çalışma verimini (`Exp136` `sp³d⁵s*` tahmini: `f = %1,0 → %52,75`, `f* = %1,5 + 2 MV/m → %77,50` / DDRF `%54,00` → `M4 %99,88`, `d_eff/d = %99,5 @ N=6`) ve `S5.6` Rota C yük-gürültüsü düşüşünü (`S_ε ≤ 0,40 µeV/√Hz`) laboratuvarda kanıtlayarak `M4` ölçek kararını kilitlemek.**
- **Finansal ve Stratejik Mantık (`Exp128 v5.0` + `Exp134/141` / `BOM_ENGINEERING.md v5.0`):**
  - `M1 v5.0` nominal donanım maliyeti: **`$2.466.120`** (`$1.454.520–$4.400.540`; **`M3 v5.0` `$5.247.800`** [`256`-hücre pilot `$4.790.400`] toplamının **`%47,0`'ı**; `M1 v4.0` `$2.336.270`'den net `+$129.850` artış: **`S5.6` tam yerinde LT-MBE `+$95.000`** + **`S6.11/S6.5` `1× ZU48DR` + `1` test TWPA/Purcell/HEMT/koaksiyel zinciri `+$46.850`** − `S7.1-04` ayrık BOED GPU ikame kredisi **`−$12.000`**).
  - `Exp128 v5.0` `100k` MC Program Bütçesi: `P50 = $34,59M ≤ $50M`, `P95 = $94,75M`, **`P(Prog > $100M) = %4,23 < %5`** *(dürüst not: `FOAK` 5 yıllık TCO kuyruğu `P(>$100M) = %5,91`)*. `M1` tahmini program bedeli (`×3–×5,5`): `$7,4M – $13,6M` (`Exp134` `v4.0` `M1` 5y Lab TCO referansı `$8,62M` + `v5.0` `+$130k` donanım).
  - **Yüksek Yatırım Koruması:** `M1 v5.0` donanım bedelinin yaklaşık **`%84`'ü (`~$2,08M`)** (`20 mK` DR `$720k`, `PT420` + `S6.9` ayrıştırma, `8`-bobinli `1,50 T` mıknatıs `$185k`, UHV oda/pompalar, `S5.5` flaş tavlama optiği, **`S5.6` LT-MBE kapak modülü `$95k`**, **`S6.11` `ZU48DR` + test TWPA zinciri**, `PH₃` gaz kabini/scrubber, `6-DOF` piezo, lazer interferometre, `HDA-HiRes`, `10→5 keV` kolon) doğrudan `M3 v5.0` altın ölçek makinesinin çekirdek gövdesine taşınır — **`M1 v5.0`, modüler (`MODULAR.md v5.0-ICD`, `CAD v5.0`) yükseltilebilir ana platformdur.**
  - **Kaldırılan Birincil Riskler:** `M1 v5.0`, `M3`'teki en ağır `R&D`/tedarik risklerini (`S2.1–S2.3` çok-demet MEMS NRE `$661k`, `S6.6` `56`-zincir `B/C` duvarı `%70,6` varyans, `S6.10` tam `M4` `3 kΩ NbTiN` çapraz-çubuk + `S6.11` tam `32`-hat Cryo-MUX yığını) ve SKY130 çip tape-out bağımlılığını (`R5/Exp123`) dışarıda bırakır.

---

## 2. `M3 v5.0` (Altın Ölçek) → `M1 v5.0` (Tek-Demet Prototip) Alt-Sistem İndirgeme Tablosu (`Exp128 v5.0` Kilitli)

| Alt Sistem | `M3 v5.0` Altın Ölçek (`$5.247.800` Nom) | `M1 v5.0` Tek-Demet Prototipi (`$2.466.120` Nom) | `M1` Payı | Kilitli Fizik / Mühendislik Şartnamesi (`Exp124–141` & `CAD v5.0`) |
|---|---|---|---:|---|
| **`S1` Kaynak & Kolon** | Çift hat (`³¹P⁺/²⁹Si⁺`), `22` parça, `$416.000` | **Tek hat (`³¹P⁺`, Mod B)** duoplazmatron + `PH₃` kabini/scrubber + Wien + `HDA-HiRes` + `10→5 keV` kolon (**`$319.750`**) | `%76,9` | Kolon `562,66 mm / Ø110 mm / 25,92 kg` (`CAD S1: 25,98 kg`); Wien `0,45 T, 150 mm, R_m=120,6`; **`HDA-HiRes`** (`R₀=40 mm, ΔE_FWHM=0,453 eV`); wafer `0 V`, üst gömlek `−5 kV`, anot `+5 kV` (`Exp124`) |
| **`S2` Yazma Kafası** | **`32×32 = 1.024` eş-adımlı `0,50 mm`** MEMS apertür/blanker/`Arch-B` (`16×16 mm < Ø28 mm`), `18` parça, `$775.500` | **Tek-delikli mikro-apertür + tek kanal blanker + tek eksenli `Arch-B` yavaşlatıcı lens** (**`$147.750`**) | `%19,1` | **`Arch-B`**: `WD = 0,250 mm`, `E_gap = 10,60 MV/m`, `C_c = 2,660 mm`, `C_s = 10,786 mm`, `σ_spot = 1,428–1,532 nm`; `Exp133/139/141` `v5.0` birleşik **`σ_tot = 3,588 nm (10 ms) / 3,631 nm (15 ms)`** (`Exp139: 3,665 nm ≤ 3,80 nm`) |
| **`S3` Soğuk-Ada IBIC** | `16×8` kanal vakum-içi CSA + çok-karolu FPGA, `14` parça, `$224.000` | **`1–2` adet 8-kanallı `100 K` soğuk-ada IBIC kartı (`src/board/`) + 1 adet FPGA kartı (`blanker_gate.v`)** (**`$88.550`**) | `%39,5` | **KRİTİK `Exp127` KİLİDİ:** RT `200 ns` `5 keV`'de `η=0,097` FAIL! **`100 K` soğuk adada `LTC6268` CSA (`Cf=0,25 pF, Rf=1 GΩ`) + `ADA4817-1` (`τ=1,2 µs, ×50`) + `DAC8568` + `TLV3501` (`204` parça, `0` ERC):** **`ENC = 24,1 e⁻`**, **`η(5 keV, 0,5 pF) = 0,99936`**, `C_det ≤ 1,5 pF`, `P_false = 2,59×10⁻⁴ / 1 ms` |
| **`S4` Konum & İnterf.** | Granit + aktif tabla + `VC-E` (`VC-G` ops.) + `6-DOF` piezo + 3-eksen interferometre (`Zerodur/Invar-36`), `17` parça, `$253.000` | Aynı yalıtım & `6-DOF` UHV piezo + 2/3-eksen `pm` interferometre + `Zerodur/Invar-36` kaide (**`$233.920`**) | `%92,5` | **`Exp133` kilitli:** `43,57 Hz` PID (`PM = 55,23°, GM = 8,69 dB`) + `25 dB` harmonik FF → **`σ_stage = 0,1024 nm`**, **`σ_pointing = 0,1473 nm`**, **`σ_thermal = 0,0283 nm`** (`20 mK` termal kararlılık; çıplak `316LN` `1,935 nm` RED) |
| **`S5` UHV, `S5.5` `1530,1 K` & **`S5.6` MBE**** | `s=0,5` UHV (`34,86 L`) + `S5.5` `1530,1 K` flaş (`$95k`) + **`S5.6` LT-MBE (`$95k`, `22,4 kg`)** + `25`-yonga epi, `24` parça, **`$433.000`** | Aynı UHV oda + `S5.5` `1530,1 K` flaş (`$66,5k`) + **`S5.6` tam yerinde `8 nm` LT-MBE + `FG/H₂` (`+$95,0k`)** + `f=%1,0` & **`f*=%1,5`** deneme lotu (**`$358.300`**) | `%82,7` | **`Exp130/139` (`R6` kapalı):** `v4` `1440 K` reçetesi `Exp139 EP5`'te `+1,318 nm` gizli TED ürettiği için yasaklandı! Kilitli **`S5.5` `808 nm / 1,0 ms / 1530,1 K` (`43,49 J/cm² ± %5`, `$0` HW, `%99,99` `{311}` temizliği, `σ_anneal = 0,430 nm`)** + **`S5.6` `345 °C` MBE + `350 °C` `FG/H₂` Rota C (`S_ε = 0,390 µeV/√Hz`, `p_ff = %97,70`)** |
| **`S6` Kriyo, `S6.9`, Mıknatıs, `M4` & **`S6.11/S6.5` MUX**** | `20 mK` DR + `PT420` + `S6.9` (`$68k`) + `8`-bobin `1,5 T` + `56` zincir + `S6.10` (`$171k` net) + **`S6.11/S6.5` `32`-hat TWPA/ZU48DR (`$629,2k`)**, `42` parça, **`$2.794.100`** | **Aynı `20 mK` DR (`$720k`) + `PT420` + `S6.9` (`$68k`, ZORUNLU) + `1,50 T` mıknatıs (`$185k`) + `2` RF zinciri + `S6.11` `1× ZU48DR` + `1` test TWPA/Purcell/HEMT zinciri (`+$46,85k`)** (**`$1.171.150`**) | `%41,9` | **`Exp133` `S6.9` `CFG4`** (rijit `PT420` `2.052 nm` RED). **`Exp125`:** `1,500000 T ± 17,8 ppm`, `B_res = 22,3 µT`, `T_quench = 64,6 K`. **`Exp140` `S6.11/S6.5`:** **`Q16.16` `2,336 µs/adım`**, `abs(ΔRMS) = 0,0502 Hz`, `%10,49` DSP48E2; **`N_mux* = 32` (`F_RO = %99,61`, `625×` Purcell)**, tek kriyo `2.887` hücre |
| **`S7–S8` Kontrol & **`CellISA v3.5`**** | `2×` GPU + çok-şase AWG + SKY130 MPW (`S7.1-04` GPU `$0` ikame), `14+9` parça, **`$204.200`** | `1×` GPU iş istasyonu + `1×` AWG + `1×` EMI kabin + **`machine_control` v3.5 (`fpga_boed_dsp.py` + `CellISA v3.5` `17` komut)** (`S7.1-04` `−$12k` `ZU48DR`'ye taşındı) (**`$104.450`**) | `%51,1` | **`Exp132/140/141`:** `Q16.16` FPGA `BOED` (`41,03 ms` yuva / `2,336 µs` adım), **`CellISA v3.5`** (`17` opcode: `+ ECHO_CZ, MUX_READOUT, SYNDROME_CYCLE`; canlı `ECHO_CZ = 0,9818`, `F_syn = 0,9427`, `T_cyc = 2,620 µs`, **`198/198` `pytest`**) |
| **`S9` Sarf & Yedek** | Tam yedek MEMS/LNA + 1 yıllık gaz, `7` parça, `$148.000` | Kalibrasyon kuponları + `PH₃` sarfı + tek-eksen yedekleri (**`$42.250`**) | `%28,5` | Çok-demet MEMS ve tam `32`-hat TWPA/`M4` yedekleri `M2–M4`'e bırakılır (`256`-hücre pilot: `$4.790.400`) |

---

## 3. `M1 v5.0` Fiziksel Mimari ve Sinyal Akışı (`Exp124–141` & `CAD v5.0` Kilitli)

```text
[S1.6: PH3 Negatif Basınçlı Gaz Kabini (SDS/Seyreltik) + Kuru/Islak Scrubber]
        │ (çift-cidarlı 316L VCR, 4x dedektör, <5 s pnömatik kesme)
        ▼
[S1.1: Duoplazmatron (+5,0 kV anot; üst kolon gömleği −5,0 kV yüzer)]
        │ (10 keV çıkarım; toplam kolon 562,66 mm [z_CAD 500,25..1062,66 mm], max OD 110 mm, 25,92 kg)
        ▼
[S1.4 Kondansör (45 mm)] → [S1.2 Wien (0,45 T, 150 mm, R_m=120,6)]
        │
        ▼
[S1.5 HDA-HiRes Enerji Süzgeci (R0=40 mm, E_pass=100 eV, slit=0,35 mm → ΔE_FWHM=0,453 eV)]
        │
        ▼
[S1.6 Transfer (65 mm)] → [S2.1 Tek Mikro-Apertür] → [S2.2 Blanker (100 MHz FPGA)]
        │ ◄── blanker_open (src/rtl/blanker_gate.v, 1 ms watchdog)
        ▼
[S2.3 Arch-B Yavaşlatıcı Mini-Lens (WD=0,250 mm, E_gap=10,60 MV/m, Cc=2,660 mm, Cs=10,786 mm)]
        │ (5,000 keV 31P+ tek iyon → alansız 0 V wafer, σ_spot=1,428–1,532 nm, v5 σ_tot=3,588–3,631 nm)
        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ S5.1: s=0,5 UHV Ana Oda (R_iç=182 mm, 34,86 L, ≤10⁻⁸ mbar) — VC-E Masa     │
│  • S4.3: 6-DOF UHV Piezo (43,57 Hz PID + 25 dB FF → σ_stage=0,1024 nm)     │
│          + Zerodur/Invar-36 Kaide (σ_thermal=0,0283 nm @ 20 mK, Exp133)    │
│  • Test Kuponu (f=%1,0 & f*=%1,5 29Si/28Si Epi, 0 V) + BeCu/Au IBIC Halka  │
│  • S3.2 Soğuk-Ada (100 K) 8-Kanallı IBIC Ön-Uç (204 bileşen, 0 ERC):       │
│      LTC6268 (Cf=0,25 pF, Rf=1 GΩ) → ADA4817-1 (1,2 µs, ×50)               │
│      → DAC8568 (16-bit/ch) + TLV3501 → 49,9 Ω JFPGA → count_hit            │
│      [ENC=24,1 e⁻, η(5 keV, 0,5 pF)=0,99936, C_det≤1,5 pF marjı, Exp127]  │
│  • +Y CF63 S5.5 Flaş Tavlama Portu (Ø44 mm AR safir, 808 nm / 1,0 ms,      │
│      T_peak=1530,1 K, F=43,49 J/cm² ± %5, %99,99 {311} temizliği, Exp139)  │
│  • Üst CF100 S5.6 LT-MBE Kapak Modülü (22,4 kg, 0 µW kriyo, %0 akış kaybı) │
│      8 nm 28Si @ 345 °C + 350 °C FG/H2 Rota C → S_ε=0,390 µeV/√Hz, %97,7  │
└───────┬────────────────────────────────────────────────────────────────────┘
        │ (In-line RT load-lock 1530,1 K flaş + S5.6 MBE Rota C [σ_anneal=0,430 nm, f_act=%99,92])
        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ S6.8/S6.1/S6.9/S6.11: Seyreltme Kriyostatı (MXC ~20 mK) + Ayrış. PT420     │
│  • S6.9 PT420 Ayrıştırma (ZORUNLU, Exp133 CFG4): 500 mm uzak döner valf +  │
│      600 mm esnek He + 2.000 N/m körük + 4× OFHC Cu örgü (ΔT=3,7 mK)      │
│  • S6.3: 8-Bobinli Aktif Karşı-Sargılı NbTi Mıknatıs (Ø150/36/Ø352 mm):    │
│      Örnekte 1,500000 T ± 17,8 ppm; Quench T_hotspot = 64,6 K (Exp125)     │
│  • z_loc = −155 mm Ø50 mm NbTiN Rezonatör Diski:                           │
│      Nb (RRR>300) Meissner Kabı + Cryoperm-10 → B_res = 22,3 µT (≪0,4 T)   │
│  • 2 RF Okuma Zinciri + S6.11 Test TWPA/Purcell/HEMT Zinciri (Exp140):     │
│      Purcell 625×, N_mux* = 32 mimari testi (F_RO = %99,61 @ 2 µs)         │
│  • MW (ESR) + RF (ENDOR) + E_z = 2 MV/m Stark Kapısı ◄── ZU48DR + AWG     │
│  • [Yan Soket: Exp33 4 K SKY130 İleri-VB Karakterizasyon Testi]            │
└───────┬────────────────────────────────────────────────────────────────────┘
        ▼ (Q16.16 BOED-FPGA 2,336 µs/adım + G6b ENDOR R1 & Rota C S_ε ölçümü)
[M8: src/machine_control v3.5 (fpga_boed_dsp.py + BayesianSpectroscopy + AtlasSelector + CellISA v3.5)]
```

> **Kritik Mühendislik Notları (`Exp127` + `Exp133` + `Exp139` + `Exp140`):**
> 1. **`100 K` Soğuk-Ada IBIC Şartı (`Exp127`):** RT `200 ns / 100 MΩ` CSA `5 keV` Lindhard yükünde (`351 e⁻`) `η = 0,097` ile çöker. IBIC taşıyıcı/CSA modülünün **`~100 K` soğuk-parmak üzerinde `1,2 µs / 1 GΩ`** ile çalıştırılması zorunludur (`ENC = 24,1 e⁻`, `η = 0,99936`).
> 2. **`S6.9` `PT420` Mekanik + Aktif Ayrıştırma Şartı (`Exp133`):** Rijit `PT420` bağlantısı (`CFG1`) **`σ_stage = 2.051,97 nm`** ile sistemi tamamen bozar; **`S6.9` `CFG4` `M1` gün-1 zorunluluğudur (`σ_stage = 0,1024 nm`).**
> 3. **Gizli TED Keşfi & `1530,1 K` Flaş Zorunluluğu (`Exp139 EP5`):** Eski `v4.0` `1440 K` flaş reçetesi `{311}` hasar kümelerinin `%13,6`'sını çözmeden bıraktığı için arka-uç `S5.6` MBE + `FG/H₂` sırasında **`+1,318 nm` gizli TED** (`σ_anneal = 1,646 nm`, `σ_tot = 3,995 nm > 3,80 nm` FAIL!) doğurmuştur. **`S5.5` donanımını değiştirmeden (`$0` HW) uygulanan `v5.0` `1530,1 K / 43,49 J/cm²` reçetesi** kümelerin **`%99,99`'unu** temizleyerek `σ_anneal = 0,430 nm` ve `σ_tot = 3,588–3,631 nm` (`Exp139: 3,665 nm ≤ 3,80 nm`) kilidini geri kazanır.

---

## 4. Adım-Adım Kurulum, Hizalama ve Kalibrasyon Prosedürü (`Faz A` – `Faz G`)

### Faz A — Temel Altyapı, UHV (`CAD v5.0`) ve `S6.9` `PT420` Titreşim + Termal Ayrıştırma (`Exp133`)
1. **Zemin & `S6.9` `PT420` Kurulumu:** `VC-E` (tercihen `VC-G`, `3,76×` ek pay) tabanlı aktif optik masa, `Zerodur` optik köprü + `Invar-36` kaide (`20 mK` termal kontrol → `σ_thermal = 0,0283 nm`; çıplak `316LN` yasak) ve `6-DOF` UHV piezo (`S4.3`) kurulur. `PT420` soğuk başlığı **`500 mm` uzak döner valf + `600 mm` esnek He hattı + `2.000 N/m` 316L CF63 körük + `4×` S-halka OFHC Cu termal örgü (`52,7 N/m`, `ΔT = 3,7 mK`)** üzerinden ayrıştırılır.
2. **Kapalı-Çevrim Servo & Harmonik FF Doğrulaması:** 3-eksen `pm` lazer interferometre (`S4.4`) ile `PT420` çalışırken **`43,57 Hz` PID** (`PM ≥ 45°` [`55,23°`], `GM ≥ 6 dB` [`8,69 dB`], `||S||_∞ ≤ 1,8` [`1,676`]) + `25 dB` senkron harmonik FF devredeyken **`σ_stage ≤ 0,25 nm` (`0,1024 nm`)** ve **`σ_pointing ≤ 0,25 nm` (`0,1473 nm`)** kanıtlanır.
3. **UHV, `S5.5` & `S5.6` LT-MBE Montajı (`CAD v5.0` `189` parça, `1.034,94 kg`, `0/17.766` çakışma, `32/32` boşluk):** `s=0,5` UHV ana oda (`34,86 L`), `+Y` CF63 `S5.5` AR safir pencere ve üst CF100 `S5.6` LT-MBE kapak modülü (`22,4 kg`, boşluklar `119,0 / 70,1 / 186,0 mm`) `He` kaçak testinden (`≤ 10⁻¹⁰ mbar·L/s`) geçirilir; `150 °C` bakeout sonrası **`≤ 10⁻⁸ mbar`** (`MBE` `< 5×10⁻¹⁰ mbar`) taban basıncı alınır.

### Faz B — `PH₃` Devreye Alma, Kaynak, Wien ve `HDA-HiRes` Süzgeç Kalibrasyonu
1. **EHS İmzalı Ön Koşul:** §5.1 `PH₃` güvenlik testleri (4 dedektör, `< 5 s` otomatik kesme, scrubber) imzalanmadan `PH₃` hattı açılmaz.
2. **İnert Gaz & Kütle Ayrımı:** Önce `Ar/N₂` plazmasıyla `+5 kV / −5 kV` HV kararlılığı (`ΔV/V ≤ 10⁻⁴`) sınanır; ardından `PH₃` ile Wien filtresi (`0,45 T, V_p = 1.348 V`) taranarak `m/q = 31` (`³¹P⁺`) / `32` (`³²PH⁺`, `dx = 0,785 mm = 3,92×` yarık, `R_m = 120,6`) ayrımı doğrulanır.
3. **`HDA-HiRes` Enerji Süzgeci:** `R₀ = 40 mm, E_pass = 100 eV, slit = 0,35 mm` ayarında RFA ile **`ΔE_FWHM ≤ 0,50 eV`** (hedef **`0,453 eV`**) ve Faraday çift-apertürle `B_r` doğrulanır (`Exp124`).

### Faz C — `Arch-B` `10→5 keV` Yavaşlatma Lensi, Blanker ve Demet Nokta Metrolojisi
1. **Blanker Hız Testi:** FPGA `blanker_gate.v` (`100 MHz`) üzerinden `1 µs–1 ms` kare darbelerle sönüm oranı (`> 10⁴`) ve anahtarlama süresi (`< 100 ns`) ölçülür.
2. **`Arch-B` Çalışma Mesafesi & Bıçak-Kenarı Profili:** Wafer `0 V` toprak potansiyelinde, **`WD = 0,250 mm`** (`E_gap = 10,60 MV/m ≤ 12 MV/m`) `S9.1` bıçak-kenarı hedefiyle **`σ_spot ≤ 1,50 nm`** (`1,428 nm @ 10 ms`; `1,532 nm @ 15 ms`) doğrulanır (`Exp124`).
3. **Kafa–Kademe Matrisi:** Fiducial işaretlerle piezo–interferometre–blanker kalıntısı `< 0,25 nm` altına çekilir (`Exp141` `v5.0` birleşik **`σ_tot = 3,588–3,631 nm ≤ 3,80 nm`**).

### Faz D — `100 K` Soğuk-Ada IBIC Kalibrasyonu ve Sayılmış Tek-İyon İmplantasyonu
1. **`100 K` Soğuk-Ada CSA Kalibrasyonu:** `src/board/` 8-kanallı kartı `100 K` soğuk adaya bağla (`< 5 cm` PTFE mikro-koaksiyel, `C_par < 0,15 pF`); `τ = 1,2 µs`, `R_f = 1 GΩ`, kazanç `×50,0`, **`ENC ≤ 25–30 e⁻`** (`24,1 e⁻ @ 0,5 pF`), `DAC8568` `5,5σ` eşiklerinde `P_false < 10⁻³ / 1 ms` (`2,59×10⁻⁴`) doğrula (`Exp127`).
2. **`5 keV ³¹P⁺` Tek-İyon Sayımı:** Gerçek Lindhard `341,7 e⁻` pikiyle hizala; `blanker_gate.v` (`1 ms` watchdog) kapalı çevriminde **`η ≥ 0,99`** (model **`0,99936 @ 0,5 pF`**, `0,9906 @ 1,5 pF`) kanıtla.

### Faz E — Mod B Kupon İmplantasyonu, `S5.5` `1530,1 K` Flaş Tavlama & `S5.6` LT-MBE Rota C (`Exp130/139`)
1. **Kupon Yazımı:** `f = %1,0` (baz) ve **`f* = %1,5`** (`Exp136` Pareto optimumu) `²⁹Si / ²⁸Si` epitaksiyel kuponlarına (`S5.4`) referans ızgarasında `≥ 64` (tercihen `128`) aday yuva (`N = 1` sayılmış `³¹P⁺`/yuva) yaz; tüm atışları `ShotRecord` JSONL veritabanına aktar.
2. **`S5.5` `808 nm / 1,0 ms / 1530,1 K` Küme-Temizleyici Flaş Tavlama (`Exp139`, `$0` HW):** Fırın (`600 °C/10 dk`), RTA (`1000 °C/10 s`) ve eski `v4.0` `1440 K` reçetesi (`Exp139 EP5` `+1,318 nm` gizli TED!) **yasaktır**. İn-line RT load-lock konumunda (`0,00 dk / 0 J` kriyo kayıp; `MXC < 1 K` kilit + UHV emniyet perdesi kapalıyken) `+Y` CF63 AR safir pencereden (`Ø44 mm CA`, `T_AR = %98`, `1530,1 K` LIDT marjı **`8,96×`** [`11,16 J/cm²`]) **`808 nm` diyot lazer / `1,0 ms` darbe / `F = 43,49 J/cm² ± %5`** (**`T_peak = 1530,1 K`**, arka yüz `608,3 K`) uygula ve `10 µs` çift-renkli pirometreyle profili kaydet (`%99,99` `{311}` küme temizliği).
3. **`S5.6` Yerinde `8 nm` LT-MBE Kapak & `FG/H₂` Pasivasyonu (Rota C, `Exp139`):** Vakumu kırmadan kuponu üst CF100 `S5.6` MBE haznesine aktar (`0 µW` kriyo yükü, `%0` akış cezası); **`T_epi* = 345 °C`** altında **`8,0 ± 1,0 nm`** `²⁸Si` epitaksiyel kapak büyüt (`R_q = 0,091 nm ≤ 0,20 nm`, `L_seg = 2,08 nm ≤ 3,5 nm`), ardından **`350 °C` `FG/H₂` pasivasyonu** uygula. İkiz kuponda SIMS / `4 K` iletim / yük-gürültüsü ölçümüyle **`f_act ≥ %85`** (model **`%99,92`**), **`σ_anneal ≤ 0,50 nm`** (Rota C tam zincir modeli **`0,430 nm`**), yüzey+vakum kaybı `< %1` (`%0,079`), `σ_iso < 0,1 nm` (`0,0515 nm`) ve **`S_ε ≤ 0,40 µeV/√Hz`** (Rota C model **`0,390 µeV/√Hz`**, `2,57×` düşüş; `p_ff = %97,70`) doğrula.

### Faz F — `MXC` Soğutma, `8`-Bobinli Mıknatıs (`1,50 T / 22,3 µT`) & `S6.11/S6.5` TWPA/Purcell Zinciri
1. **Manyetik Harita (`R7` Fiziksel Doğrulama):** `8`-bobinli `S6.3` mıknatısını `1,500000 T`'ye rampa et (`I/I_c ≤ 0,212`); NMR/Hall ile yonga merkezinde **`ΔB/B ≤ 100 ppm`** (`17,81 ppm`), `z_loc = −155 mm` `Nb (RRR>300)` + `Cryoperm-10` kabı içinde **`B_res ≤ 0,40 T`** (**`22,3 µT`**, `B_perp ≤ 10 mT`) ve kontrollü quench (`≤ 100 K`, `64,6 K`) doğrula (`Exp125`).
2. **Kriyo, `2`-Zincirli RF & `S6.11` Tek-Zincir TWPA/Purcell Testi (`Exp125/140`):** `MXC ≤ 20–25 mK`, `4 K` yükü `< 0,25 W`, `S6.9` Cu örgü `ΔT ≤ 10 mK` (`3,7 mK`), `NbTiN` `Q_l = 800–1200`, `ton ≤ −100 dBm/kanal`, `SNR = 10 ≤ 0,1 ms` (`0,0627 ms`). Tek `S6.11` test TWPA/Purcell zincirinde (`CAD v5.0` boşluklar `17,98 / 10,0 / 8,0 / 20,0 mm`) `4–8 GHz` kazanç, `P_1dB ≥ −98 dBm`, `Purcell ≥ 100×` (`625×`) ve `τ_RO = 2,0 µs` tek-atış okuma sadakati **`F_RO ≥ %99,0`** (`%99,61`, `N_mux* = 32` mimari kanıtı) ölçülür.
3. **İsteğe Bağlı `Exp33` Yan Kuponu:** `4 K` plakasındaki yan sokette SKY130 ileri-`V_B` ve çift-yönlü histerezis ölçümü (`C33-2/C33-5`).

### Faz G — Kapalı Çevrim II: `Q16.16` BOED-FPGA, **`G6b` `ENDOR` (`f* = %1,5 + 2 MV/m`)** & `CellISA v3.5` (`Exp126/132/136/140/141`)
1. **`Q16.16` BOED-FPGA Uyarlamalı Ölç & Seç (`Exp132/140`):** Aday yuvalarda `ZU48DR` (`src/machine_control/fpga_boed_dsp.py`) üzerinde sabit-noktalı `Q16.16` BOED çalıştır; FPGA adım gecikmesinin **`< 25 µs`** (**`2,336 µs`**, `%10,49` DSP48E2), FP64'e göre paritenin **`abs(ΔRMS) < 1,0 Hz`** (`0,0502 Hz`), ortalama yuva süresinin **`≤ 80 ms`** (`41,03 ms`), **`RMS ≤ 150 Hz`** (`72,67–73,38 Hz`), `FNR ≤ %1` (`%0,20`) ve `FPR ≤ %0,5` (`%0,00`) olduğunu kanıtla. `AtlasSelector` ile en az `1` (hedef `≥ 3`) `K=8` / `K=4` yazmaç seç (`min_spacing ≥ 5 kHz`, Vandermonde `8/8`, `D0 ≤ 10⁻⁶`).
2. **`G6b` — Kritik Risk `R1` (`Exp129/136`) `ENDOR` & `E_z = 2 MV/m` Stark Verim Kapısı:** `Exp136` atomistik `160k`-orbital `sp³d⁵s*` TB çözücüsü `Exp129 VOKL-6` `R331` sapmasını `%64,73 → %21,1` (`log10-RMS = 0,2426`) indirerek `f = %1,0` Mod B verimini `%52,75` (`M4 %99,74`), **`f* = %1,5 + 2 MV/m` Stark** ile **`%77,50`** (DDRF `≥ 6,893 kHz` `%54,00` → **`M4 %99,88`**, kusurlu `d=7` yüzey kodu **`d_eff/d = %99,5 @ N=6`**) olarak öngörmüştür. `M1` kuponlarında `≥ 64` donorda ölçülen gerçek `ENDOR` spektrumuyla:
   - **`p_work(f*=%1,5 + 2 MV/m) ≥ %50` ve `p_work(f=%1,0) ≥ %30`:** `Exp136/138` atomistik ve yüzey-kodu (`d_eff/d = %99,5`) zinciri laboratuvarda kilitlenir; `M4` `N_cand = 6` ile devam edilir.
   - **`p_work(f=%1,0) < %15` veya `p_work(f*=%1,5) < %35`:** `M2/M4` dondurulur; **`f* = %2,0`** (`Exp136` ab-initio güvenceli nokta `%52,50 → %99,69`, `XY8 T₂e = 10,8 ms`) veya `K=4` yazmaç revizyonu zorunlu olur.
3. **Kalibre Et & `CellISA v3.5` Koştur (`Exp126/137/140/141`):** RF NMR bobininde **`10–15 kHz` Rabi payı (`B₁ ≈ 1,2–1,8 mT`)** doğrulandıktan sonra 9-köşeli (`±400 Hz × ±%2`) iki-aşamalı 32B **`XY8`-GRAPE** sentezle (**`CPMG` yasak**; **`N_total = 32–64`**, **`N = 32` optimum `0,9260 / 0,9648`**, **`N = 128` DDRF duvarı yasak**; `ε ≤ 10⁻³`); **`CellISA v3.5`** (`17` komut: `+ ECHO_CZ, MUX_READOUT, SYNDROME_CYCLE`) ile `Bell` (`0,9501`), `GHZ-4` (`0,9401`), `Grover-2` (`P(\|11⟩) = 0,9237`), `BitFlip-3` (`0,8878`), `QFT-3` (`0,8377`) ve tek-zincir `MUX_READOUT` / yankılı `P4` testini koşturup tomografiyle **`Q_32D ≥ 0,85`** ve **`D0(17,5 s) ≤ 10⁻⁶`** (`≤ 7,76×10⁻⁹`) doğrulayarak ilk fiziksel SHA-256 `ProgramCertificate` kaydını mühürle.

---

## 5. Zorunlu EHS ve Laboratuvar Güvenlik Protokolleri

### 5.1 `PH₃` (Fosfin) Toksik ve Piroforik Gaz Güvenliği — **KRİTİK ÖNCELİK**
Fosfin (`PH₃`) renksiz, solunumla hızla ölümcül ve saf hâlde piroforik bir gazdır (`OSHA PEL = 0,3 ppm` 8 saat TWA; `ACGIH TLV-STEL = 1,0 ppm`; `NIOSH IDLH = 50 ppm`) `{Literatür}`:
1. **Düşük Riskli Kaynak:** Sertifikalı seyreltik karışım (`%1–%5 PH₃` in `H₂`/`Ar`) veya sub-atmospheric adsorban tüp (**SDS/SAGE**) zorunludur.
2. **Muhafaza & Borulama:** SEMI S2 / NFPA 318 negatif basınçlı sürekli egzozlu çift-tüplü gaz kabini (`S1.6`), elektro-parlatılmış çift-cidarlı `316L VAR` metal VCR borulama (pirinç/elastomer yasak), otomatik `N₂` süpürme manifoldu.
3. **4-Nokta Sürekli Dedektör & SIL-2 PLC (`S7.4-04`):** Kabin, egzoz, kaynak başlığı ve solunum bölgesi dedektörleri (Alarm-1 `0,15 ppm` uyarı; Alarm-2 `0,30 ppm` `< 5 s` otomatik pnömatik silindir kapama + HV/plazma kesme + tahliye sireni; tümü UPS destekli).
4. **Arıtım (Scrubber):** Yağsız kuru ön-pompa çıkışı doğrudan sertifikalı kuru-reçine/ıslak scrubber'a (`< 50 ppb` çıkış) bağlanır; iki kişilik (buddy) çalışma ve erişilebilir SCBA zorunludur.

### 5.2 Yüksek Gerilim (`±5 kV`), `S5.5` Sınıf-4 Lazer, `S5.6` `FG/H₂` & MBE, Kriyo, `1,50 T` Mıknatıs ve ESD
- **HV & X-Işını:** `+5 kV` anot ve `−5 kV` üst kolon gömleği akım sınırlı (`≤ 5 mA` kaynak, `≤ 1 mA` lensler), kapı interlock'lu ve LOTO + topraklama kancalıdır; devreye almada `< 0,5 µSv/h` Bremsstrahlung taraması yapılır.
- **`S5.5` Sınıf-4 `808 nm` `1530,1 K` Flaş Lazeri (`Exp130/139`):** Tam kapalı ışın tüpü, kapı/port interlock'u, `OD ≥ 7 @ 808 nm` koruyucu gözlük, `MXC < 1 K` kriyo kilidi + pnömatik UHV emniyet perdesi, `10 µs` pirometre aşırı-sıcaklık kesmesi (**`T > 1580 K` anlık kesme** — `1530,1 K` hedefinin `+50 K` üstünde, Si ergime `1687 K`'nin `−107 K` altında güvenlik penceresi).
- **`S5.6` LT-MBE & `FG/H₂` Pasivasyon (`Exp139`):** `%5 H₂ / %95 N₂` yanıcı-olmayan oluşturma gazı (forming gas, `< %4` LEL altı sertifikalı karışım), egzoz seyreltmesi ve `345–350 °C` ısıtıcı aşırı-sıcaklık termokupl kilidi.
- **Kriyo ODH & Quench:** Sürekli `O₂` monitörü (`< %19,5` uyarı, `< %18,0` tahliye), çift kademeli basınç tahliyesi, dış atmosfere yönlendirilmiş quench egzoz hattı (`T_hotspot = 64,6 K`, `R_dump = 1,563 Ω`).
- **Manyetik Alan (`1,50 T`):** `0,5 mT` (`5 Gauss`) hattı işaretli; kalp pili yasak bölgesi; yalnız `Ti`/`BeCu`/pirinç aletler.
- **İnterferometre & ESD:** İnterferometre kapalı ışın tüpü; `< 50 V` HBM hassas IBIC/`NbTiN`/TWPA/SET cihazları için ANSI/ESD S20.20 topraklı istasyon ve iyonlaştırıcı.

---

## 6. `M1 v5.0` Go/No-Go Çıkış Kapıları (`G1`–`G8`, `G6b` Dahil — `Exp124–141` Kilitli)

> Aşağıdaki 9 kapının tamamı geçilmeden `M2` (`10²–10³` demetcikli MEMS prototip) ve `M4` tam hata-toleranslı (`32`-hat Cryo-MUX + `100L` kriyo filosu) yatırımına geçilmez.

| Kapı | Alt Sistem / Faz | Kilitli Kabul Eşiği (`v5.0` Go Kriteri) | Doğrulama Yöntemi | No-Go / Düzeltme Kuralı |
|---|---|---|---|---|
| **`G1`** | EHS, UHV & `S6.9` `PT420` (`Faz A–B`, `Exp133`, `CAD v5.0`) | Tüm `PH₃`/Sınıf-4 lazer/`FG/H₂`/HV/O₂/PLC interlock `%100` PASS; UHV `≤ 10⁻⁸ mbar`; `CAD v5.0` `0/17.766` çakışma (`32/32`); `PT420` açıkken `CFG4` ile **`σ_stage ≤ 0,25 nm`** (`0,1024 nm`), **`σ_pointing ≤ 0,25 nm`** (`0,1473 nm`), **`σ_thermal ≤ 0,10 nm`** (`0,0283 nm`) | EHS tutanağı, RGA, interferometre PSD, PID Bode (`PM≥45°`) | Güvenlik kilidi geçmeden gaz/lazer/HV açılamaz; `σ_stage > 0,25 nm` ise `k_bellows`/Cu örgü/FF harmonikleri sıkılaştırılır (`VC-G` ops.) |
| **`G2`** | İyon Kolonu (`Faz B–C`, `Exp124`) | Wien `m/q=31` ayrımı (`R_m ≥ 60`, hedef `120,6`); `HDA-HiRes` **`ΔE_FWHM ≤ 0,50 eV`** (`0,453 eV`); `Arch-B` `WD = 0,250 mm`, `E_gap ≤ 12 MV/m` (`10,60 MV/m`), **`σ_spot ≤ 1,50 nm` @ `5 keV`** (`1,428 nm`) | Wien taraması, RFA, Faraday `B_r`, bıçak-kenarı profili | `σ_spot > 1,6 nm` ise `HDA` yarık daraltılır veya `LMIS` opsiyonu değerlendirilir |
| **`G3`** | Soğuk-Ada IBIC (`Faz D`, `Exp127`) | `100 K` soğuk adada `LTC6268` CSA (`1,2 µs / 1 GΩ`): `C_det ≤ 1,5 pF` (`0,5 pF`), **`ENC ≤ 30 e⁻`** (`24,1 e⁻`), `P_false < 10⁻³ / 1 ms`, **`η ≥ 0,99` @ `5 keV`** (`0,99936`), `blanker_gate` `1 ms` watchdog PASS | Test pulser, Lindhard `341,7 e⁻` PHA piki, FPGA sayım logu | RT'de çalıştırma yasak; `η < 0,99` ise kablo `< 5 cm` / `100 K` temas kontrol edilir (acil yedek `10 keV` `η=0,9998`) |
| **`G4`** | **`S5.5` `1530,1 K` + `S5.6` MBE Rota C** (`Faz E`, `Exp130/139`, `R6`) | `808 nm / 1,0 ms / F = 43,49 J/cm² ± %5` (**`T_peak = 1530,1 K`**, `%99,99` `{311}` temizliği) + `S5.6` `8 nm` `345 °C` MBE + `350 °C` `FG/H₂` Rota C: **`f_act ≥ %85`** (`%99,92`), **`σ_anneal ≤ 0,50 nm`** (`0,430 nm`), kayıp `< %1` (`%0,079`), `σ_iso < 0,1 nm` (`0,0515 nm`), **`S_ε ≤ 0,40 µeV/√Hz`** (`0,390 µeV/√Hz`) | `10 µs` pirometre logu, SIMS / `4 K` Hall-iletim, RHEED/AFM (`R_q ≤ 0,2 nm`), SET/yük-gürültüsü PSD | Eski `v4.0` `1440 K` reçetesi (`+1,318 nm` gizli TED!) ve fırın/RTA yasak; `S_ε > 0,50 µeV/√Hz` ise `FG/H₂` tavlama/oksit arayüzü yenilenir |
| **`G5`** | Mıknatıs, Kriyo & **`S6.11` TWPA/Purcell** (`Faz F`, `Exp125/133/140`) | `MXC ≤ 25 mK`, `B_z = 1,500000 T ± 100 ppm` (`17,8 ppm`), `z_loc = −155 mm` **`\|B_res\| ≤ 0,40 T`** (`22,3 µT`), quench `≤ 100 K` (`64,6 K`), Cu örgü `ΔT ≤ 10 mK` (`3,7 mK`), tek-zincir `S6.11` TWPA/Purcell **`Purcell ≥ 100×`** (`625×`), **`F_RO(2 µs) ≥ %99,0`** (`%99,61`) | Termometri, NMR/Hall 3B harita, VNA `S21`, FAT quench, `ZU48DR` tek-atış histogramı | `\|B_res\| > 0,40 T` ise karşı-sargı/kalkan ayarlanır; `F_RO < %99` ise TWPA pompa/`P_1dB` ve Purcell filtre eşleşmesi ayarlanır |
| **`G6a`** | **`Q16.16` BOED-FPGA** (`Faz G`, `Exp132/140`) | `ZU48DR` `Q16.16` BOED adım **`< 25 µs`** (`2,336 µs`), **`abs(ΔRMS) < 1,0 Hz`** (`0,0502 Hz`), ortalama yuva **`≤ 80 ms`** (`41,03 ms`), **`RMS ≤ 150 Hz`** (`72,67–73,38 Hz`), `FNR ≤ %1`, `FPR ≤ %0,5`, `≥ 1` (`≥ 3`) sertifikalı `K=8`/`K=4` yazmaç | `fpga_boed_dsp.py` + `BayesianSpectroscopy` (`--preset v400`) + `AtlasSelector` | `RMS > 200 Hz` ise `BOED` durdurma eşiği sıkılaştırılır veya klasik `1 s` taramaya düşülür |
| **`G6b`** | **Risk `R1` `ENDOR` & `f* = %1,5 + 2 MV/m`** (`Faz G`, `Exp129/136/138`) | `≥ 64` donorda ölçülen gerçek çalışma verimi **`p_work(f*=%1,5 + 2 MV/m) ≥ %50`** (`Exp136`: `%77,50` / DDRF `%54,00` → `M4 %99,88`, `d_eff/d = %99,5 @ N=6`) ve **`p_work(f=%1,0) ≥ %30`** (`Exp136`: `%52,75`) | `≥ 64`-yuva deneysel `ENDOR` + Stark istatistiği & `Exp136/138` yeniden kalibrasyonu | `p_work(f*=%1,5) < %35` veya `p_work(f=%1) < %15` çıkarsa `M2/M4` dondurulur; **`f* = %2,0`** (`XY8 T₂e = 10,8 ms`) veya `K=4` revizyonu zorunludur |
| **`G7`** | `XY8`-GRAPE & **`CellISA v3.5`** (`Faz G`, `Exp126/137/140/141`) | RF payı **`10–15 kHz`**, zorunlu **`XY8` `N_total = 32–64`** (`N=32` `0,9260/0,9648`, `N=128` ve `CPMG` yasak), `ε ≤ 10⁻³`, **`D0(17,5 s) ≤ 10⁻⁶`**, **`Q_32D ≥ 0,85`**, `CellISA v3.5` (`17` komut, `ECHO_CZ/MUX_READOUT/SYNDROME_CYCLE`) SHA-256 sertifikası + **`198/198` `pytest`** | 32B durum tomografisi + `ProgramCertificate` JSONL + `XY8` eksen testi | `Q < 0,85` ise **`N = 128`'e çıkılmaz** (`sp_ovl=0,0972` DDRF duvarı!); `N = 32` optimumuna dönülür, `10–15 kHz` RF payı sıkılaştırılır |
| **`G8`** | Maliyet, **`8-RFQ`** & `CX4` SOI Kapısı (`Exp128 v5.0` + `Exp141`) | `M1 v5.0` faturaları (`~$2,466M` ref.) + **`8-RFQ`** (`RFQ-01..08`, `%76,4` nom / `%92,6` MC var) bağlayıcı teklifleriyle güncellenen `Exp128 v5.0` `M3` Program `P50 ≤ $50M` (`$34,59M`), **`P(Prog > $100M) < %5`** (`%4,23`; `FOAK 5y TCO %5,91` izlenir), `W2/W3` `30 nm` SOI tedarik doğrulaması | `8-RFQ` uzlaştırması + `run_exp128.py` + `run_exp141.py` + `BUTCE_DURUMU.md` | `> $50M` ise gerekçe `BUTCE_DURUMU.md`'ye işlenir; `> $100M` ise `256`-hücre pilot (`$4,79M`) / `D2→D3` önceliklendirmesi zorunludur |
